from __future__ import annotations

"""FILL-001 / GEOM-001: isolated A-D offline strategy screening.

Uses the existing frozen FILL-001 masks, planner and OpenCV stroke model.
No generated strategy is executor-ready and no sampling proxy is exact CHALK.
The actual captured PNG quality gate is deliberately NOT evaluated here.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from chalk_fill_experiment import (
    FILL001_EXPECTED_MASK_SHA256,
    FILL001_SHAPES,
    build_fill_target_mask,
    fill_target_mask_sha256,
)
from chalk_fill_fixed_radius_planner import (
    FILL001_MIN_COVERAGE,
    FILL001_MAX_LEAKAGE_PIXELS,
    _draw_round_capped_stroke,
    build_fixed_radius_fill_plan,
)


def _render_segments(
    shape: tuple[int, int],
    strokes: list[dict[str, Any]],
) -> np.ndarray:
    raster = np.zeros(shape, dtype=np.uint8)
    for stroke in strokes:
        points = stroke["points"]
        brush = stroke["brush_value"]
        pairs = list(zip(points, points[1:]))
        if stroke.get("closed"):
            pairs.append((points[-1], points[0]))
        if not pairs:
            pairs = [(points[0], points[0])]
        for start, end in pairs:
            _draw_round_capped_stroke(
                raster, tuple(start), tuple(end), brush
            )
    return raster.astype(bool)


def _contour_stroke(mask: np.ndarray, inset: int, brush: int) -> dict[str, Any]:
    if isinstance(inset, bool) or not isinstance(inset, int) or inset < 1:
        raise ValueError("contour inset must be a positive integer")
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * inset + 1, 2 * inset + 1)
    )
    core = cv2.erode(mask.astype(np.uint8), kernel)
    contours, hierarchy = cv2.findContours(
        core, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )
    # Connected, hole-free frozen shapes only. Never silently lose a hole or island.
    if hierarchy is None or len(contours) != 1 or len(contours[0]) < 3:
        raise ValueError("inset contour is not a single connected closed boundary")
    if int(hierarchy[0, 0, 2]) != -1:
        raise ValueError("inset contour contains a hole")
    points = [tuple(int(v) for v in p[0]) for p in contours[0]]
    return {
        "points": points,
        "brush_value": brush,
        "closed": True,
        "role": "modeled_connected_contour",
    }


def _local_corrections(
    mask: np.ndarray,
    currently_painted: np.ndarray,
) -> list[dict[str, Any]]:
    """Oracle-based residual correction for comparison, NOT a live planner."""
    residual = mask & ~currently_painted
    strokes: list[dict[str, Any]] = []
    for y, row in enumerate(residual):
        xs = np.flatnonzero(row)
        if not xs.size:
            continue
        parts = np.split(xs, np.flatnonzero(np.diff(xs) > 1) + 1)
        for part in parts:
            a, b = int(part[0]), int(part[-1])
            strokes.append({
                "points": [(a, y), (b, y)],
                "brush_value": 1,
                "closed": False,
                "role": "oracle_residual_1px_correction",
            })
    return strokes


def _model_metrics(
    target: np.ndarray,
    painted: np.ndarray,
    strokes: list[dict[str, Any]],
    *,
    sampling_step: int,
) -> dict[str, Any]:
    target_area = int(np.count_nonzero(target))
    uncovered = target & ~painted
    leakage = painted & ~target
    path_length = 0.0
    points_proxy = 0
    for stroke in strokes:
        points = stroke["points"]
        segments = list(zip(points, points[1:]))
        if stroke.get("closed"):
            segments.append((points[-1], points[0]))
        lengths = [
            math.hypot(float(b[0] - a[0]), float(b[1] - a[1]))
            for a, b in segments
        ]
        path_length += sum(lengths)
        points_proxy += max(
            1,
            sum(int(math.ceil(length / sampling_step)) for length in lengths) + 1,
        )
    coverage = 1.0 - int(np.count_nonzero(uncovered)) / target_area
    leak_count = int(np.count_nonzero(leakage))
    return {
        "coverage_fraction": round(coverage, 9),
        "uncovered_logical_pixels": int(np.count_nonzero(uncovered)),
        "leakage_logical_pixels": leak_count,
        "stroke_count": len(strokes),
        "path_length_logical_px": round(path_length, 3),
        "sampling_points_proxy_not_chalk": points_proxy,
        "offline_quality_gate_passed": (
            coverage >= FILL001_MIN_COVERAGE
            and leak_count <= FILL001_MAX_LEAKAGE_PIXELS
        ),
    }


def compare_fill001_strategies(
    shape_id: str,
    *,
    brush_value: int = 10,
    sparse_row_step: int = 5,
    contour_inset: int = 6,
    sampling_step: int = 4,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """Compare dense, sparse, contour and oracle-corrected OpenCV footprints.

    This is intentionally restricted to the validated FILL-001 radius-10
    exploration rather than advertised as a generic game brush model.
    """
    if shape_id not in FILL001_SHAPES:
        raise ValueError("unknown frozen FILL-001 shape")
    if brush_value != 10:
        raise ValueError("this exploratory contour comparison is radius-10 only")
    for name, value in (
        ("sparse_row_step", sparse_row_step),
        ("sampling_step", sampling_step),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(name + " must be a positive integer")
    target = build_fill_target_mask(shape_id)
    target_hash = fill_target_mask_sha256(shape_id, target)
    if target_hash != FILL001_EXPECTED_MASK_SHA256[shape_id]:
        raise ValueError("frozen mask SHA-256 mismatch")

    dense = build_fixed_radius_fill_plan(shape_id, brush_value)
    sparse = build_fixed_radius_fill_plan(
        shape_id, brush_value, scanline_row_step=sparse_row_step
    )
    def original_strokes(plan: dict[str, Any]) -> list[dict[str, Any]]:
        return [{
            "points": [
                (int(p["x"]), int(p["y"])) for p in item["points"]
            ],
            "brush_value": brush_value,
            "closed": False,
            "role": item["role"],
        } for item in plan["strokes"]]

    a = original_strokes(dense)
    b = original_strokes(sparse)
    contour = _contour_stroke(target, contour_inset, brush_value)
    c = b + [contour]

    rasters = {
        "A_dense_scanline": _render_segments(target.shape, a),
        "B_sparse_scanline": _render_segments(target.shape, b),
        "C_sparse_plus_contour": _render_segments(target.shape, c),
    }
    corrections = _local_corrections(target, rasters["C_sparse_plus_contour"])
    d = c + corrections
    rasters["D_plus_oracle_local_correction"] = _render_segments(target.shape, d)
    strategies = {
        "A_dense_scanline": a,
        "B_sparse_scanline": b,
        "C_sparse_plus_contour": c,
        "D_plus_oracle_local_correction": d,
    }
    rows = {
        name: _model_metrics(target, rasters[name], strokes, sampling_step=sampling_step)
        for name, strokes in strategies.items()
    }
    result = {
        "schema_version": 1,
        "task_ids": ["FILL-001", "GEOM-001"],
        "status": "OFFLINE_EXPLORATORY_ONLY",
        "shape_id": shape_id,
        "frozen_mask_sha256": target_hash,
        "frozen_baseline_plan_signature": dense["plan_signature"],
        "sparse_plan_signature": sparse["plan_signature"],
        "brush_value": brush_value,
        "scanline_row_step": sparse_row_step,
        "contour_inset_logical_px": contour_inset,
        "sampling_step_proxy_px": sampling_step,
        "target_logical_pixels": int(np.count_nonzero(target)),
        "contour_vertex_count": len(contour["points"]),
        "correction_stroke_count": len(corrections),
        "strategies": rows,
        "measurement_scope": {
            "pixel_quality": "OpenCV logical-mask model, NOT live screenshot",
            "sampling_points_proxy": "geometric estimate, NOT pointCount",
            "measured_chalk": None,
            "runtime_validated": False,
            "executor_ready": False,
            "D_oracle_warning": "corrections use raster residual ground truth; not an executable prediction",
        },
    }
    return result, {"target": target, **rasters}


def save_exploratory_report(output_dir: Path, shapes: list[str]) -> Path:
    if output_dir.exists():
        raise FileExistsError("Refusing to replace prior experimental artifacts")
    output_dir.mkdir(parents=True)
    reports = []
    for shape in shapes:
        report, masks = compare_fill001_strategies(shape)
        reports.append(report)
        for name, pixels in masks.items():
            file = output_dir / (shape + "_" + name + ".png")
            if not cv2.imwrite(str(file), np.uint8(pixels) * 255):
                raise OSError("Cannot save diagnostic PNG")
    record = {
        "analysis_type": "fill001_frozen_A_D_offline_comparison",
        "reports": reports,
    }
    path = output_dir / "strategy_comparison.json"
    path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path



def compare_contour_first_overlap(
    shape_id: str,
    *,
    brush_value: int = 10,
    scanline_row_step: int = 5,
    contour_inset: int = 6,
    interior_insets: tuple[int, ...] = (7, 8, 9),
    sampling_step: int = 4,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """Controlled contour-first study on the original frozen FILL-001 masks.

    The contour-last and contour-first controls have exactly the same strokes
    and simulated footprint. Separate inset variants change ONLY the centerline
    endpoints of interior scanlines, not the target or contour. No game cost,
    native Egret raster equivalence, or executor readiness is implied.
    """
    if shape_id not in FILL001_SHAPES:
        raise ValueError("unknown frozen FILL-001 shape")
    if brush_value != 10:
        raise ValueError("contour-first exploratory study is radius-10 only")
    for label, value in (("scanline_row_step", scanline_row_step),
                         ("contour_inset", contour_inset),
                         ("sampling_step", sampling_step)):
        if type(value) is not int or value < 1:
            raise ValueError(f"{label} must be a positive integer")
    if (not isinstance(interior_insets, tuple) or not interior_insets
            or len(set(interior_insets)) != len(interior_insets)
            or any(type(inset) is not int or inset <= contour_inset
                   for inset in interior_insets)):
        raise ValueError("interior_insets must be unique integers beyond contour_inset")

    target = build_fill_target_mask(shape_id)
    mask_sha = fill_target_mask_sha256(shape_id, target)
    if mask_sha != FILL001_EXPECTED_MASK_SHA256[shape_id]:
        raise ValueError("frozen mask SHA-256 mismatch")
    baseline = build_fixed_radius_fill_plan(
        shape_id, brush_value, scanline_row_step=scanline_row_step,
    )
    baseline_strokes = [{
        "points": [(int(pt["x"]), int(pt["y"])) for pt in stroke["points"]],
        "brush_value": brush_value, "closed": False, "role": "baseline_scanline",
    } for stroke in baseline["strokes"]]
    contour = _contour_stroke(target, contour_inset, brush_value)
    strategies: dict[str, list[dict[str, Any]]] = {
        "B_sparse_scanline_control": baseline_strokes,
        "C_contour_last_control": [*baseline_strokes, contour],
        "E_contour_first_same_geometry": [contour, *baseline_strokes],
    }
    distance = cv2.distanceTransform(
        target.astype(np.uint8), cv2.DIST_L2, 5,
    )
    for inset in interior_insets:
        # Centerlines retain the SAME scanline rows and brush; only their
        # horizontal endpoints move inward. The contour is always first.
        safe_centers = distance >= (inset + 0.01)
        narrowed = []
        for baseline_stroke in baseline_strokes:
            row_y = baseline_stroke["points"][0][1]
            selected = np.flatnonzero(safe_centers[row_y])
            if selected.size == 0:
                continue
            chunks = np.split(selected, np.flatnonzero(np.diff(selected) > 1) + 1)
            for chunk in chunks:
                if chunk.size:
                    narrowed.append({
                        "points": [(int(chunk[0]), row_y),
                                   (int(chunk[-1]), row_y)],
                        "brush_value": brush_value, "closed": False,
                        "role": "inset_interior_scanline",
                    })
        strategies[f"F_contour_first_interior_inset_{inset}"] = [contour, *narrowed]

    rasters = {
        name: _render_segments(target.shape, strokes)
        for name, strokes in strategies.items()
    }
    contour_raster = _render_segments(target.shape, [contour])
    rows = {}
    for name, strokes in strategies.items():
        metrics = _model_metrics(
            target, rasters[name], strokes, sampling_step=sampling_step,
        )
        interior_raster = _render_segments(target.shape, [
            s for s in strokes if s["role"] != "modeled_connected_contour"
        ])
        metrics["contour_interior_overlap_logical_pixels"] = int(
            np.count_nonzero(contour_raster & interior_raster)
        ) if name != "B_sparse_scanline_control" else None
        metrics["contour_first"] = (name.startswith("E_") or name.startswith("F_"))
        metrics["interior_scanline_count"] = sum(
            s["role"] != "modeled_connected_contour" for s in strokes
        )
        rows[name] = metrics
    if not np.array_equal(
        rasters["C_contour_last_control"],
        rasters["E_contour_first_same_geometry"],
    ):
        raise AssertionError("Contour order must not change set-union OpenCV raster.")
    result = {
        "schema_version": 1,
        "protocol": "FILL001_CONTOUR_FIRST_OVERLAP_V1",
        "status": "OFFLINE_EXPLORATORY_ONLY",
        "shape_id": shape_id,
        "frozen_mask_sha256": mask_sha,
        "baseline_plan_signature": baseline["plan_signature"],
        "brush_value": brush_value,
        "contour_inset": contour_inset,
        "scanline_row_step": scanline_row_step,
        "sampling_step_proxy": sampling_step,
        "tested_interior_insets": list(interior_insets),
        "contour_vertex_count": len(contour["points"]),
        "strategies": rows,
        "measurement_scope": {
            "quality": "OpenCV logical footprint proxy, not game PNG",
            "measured_chalk": None,
            "native_egret_equivalence": False,
            "runtime_validated": False,
            "executor_ready": False,
            "order_only_control": "C and E contain identical geometry and raster; only sequence changes.",
            "inset_variants": "F changes interior endpoints only, retaining same contour and rows.",
        },
    }
    return result, {"target": target, **rasters}


def save_contour_first_report(
    output_dir: Path, shapes: list[str],
) -> Path:
    """Create a new independent evidence folder without overwriting A-D data."""
    if output_dir.exists():
        raise FileExistsError("Refusing to replace prior experimental artifacts")
    output_dir.mkdir(parents=True)
    reports = []
    for shape_id in shapes:
        report, masks = compare_contour_first_overlap(shape_id)
        reports.append(report)
        for name, mask in masks.items():
            dest = output_dir / f"{shape_id}_{name}.png"
            if not cv2.imwrite(str(dest), np.uint8(mask) * 255):
                raise OSError("Cannot save diagnostic PNG")
    path = output_dir / "contour_first_comparison.json"
    path.write_text(
        json.dumps({
            "analysis_type": "fill001_contour_first_overlap_v1",
            "reports": reports,
        }, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--shape", choices=FILL001_SHAPES, action="append")
    parser.add_argument("--contour-first", action="store_true",
                        help="Separate controlled contour-first/inset study.")
    args = parser.parse_args(argv)
    if args.contour_first:
        save_contour_first_report(args.output_dir, args.shape or list(FILL001_SHAPES))
    else:
        save_exploratory_report(args.output_dir, args.shape or list(FILL001_SHAPES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

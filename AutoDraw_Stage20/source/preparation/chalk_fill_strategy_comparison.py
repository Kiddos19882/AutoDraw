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



def compare_contour_edge_trims(
    shape_id: str,
    *,
    brush_value: int = 10,
    scanline_row_step: int = 5,
    contour_inset: int = 6,
    endpoint_trims: tuple[int, ...] = (1, 2, 3, 4),
    sampling_step: int = 4,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """V2 controlled candidate: trim X endpoints only, preserve every scanline Y.

    Unlike V1 inward distance-transform cropping, no row is removed. The
    contour is a single closed first stroke and the same brush/target is used.
    This only describes an OpenCV logical footprint, not real Egret behavior.
    """
    previous, _ = compare_contour_first_overlap(
        shape_id, brush_value=brush_value,
        scanline_row_step=scanline_row_step,
        contour_inset=contour_inset,
        sampling_step=sampling_step,
    )
    if (not isinstance(endpoint_trims, tuple) or not endpoint_trims
            or len(set(endpoint_trims)) != len(endpoint_trims)
            or any(type(t) is not int or not 1 <= t <= 4
                   for t in endpoint_trims)):
        raise ValueError("endpoint_trims must be unique positive integers from 1 to 4")
    target = build_fill_target_mask(shape_id)
    baseline = build_fixed_radius_fill_plan(
        shape_id, brush_value, scanline_row_step=scanline_row_step,
    )
    contour = _contour_stroke(target, contour_inset, brush_value)
    scanlines = [{
        "points": [(int(point["x"]), int(point["y"])) for point in stroke["points"]],
        "brush_value": brush_value, "closed": False,
        "role": "baseline_scanline",
    } for stroke in baseline["strokes"]]
    strategies: dict[str, list[dict[str, Any]]] = {
        "E_contour_first_same_geometry": [contour, *scanlines],
    }
    for trim in endpoint_trims:
        revised = []
        for stroke in scanlines:
            (x0, y0), (x1, y1) = stroke["points"]
            if x1 - x0 < trim * 2:
                raise ValueError("endpoint trim cannot fit within all frozen scanlines")
            revised.append({
                "points": [(x0 + trim, y0), (x1 - trim, y1)],
                "brush_value": brush_value, "closed": False,
                "role": "side_endpoint_trim_only",
            })
        strategies[f"G_contour_first_endpoints_trim_{trim}"] = [contour, *revised]
    masks = {
        name: _render_segments(target.shape, strokes)
        for name, strokes in strategies.items()
    }
    contour_pixels = _render_segments(target.shape, [contour])
    rows = {}
    for name, strokes in strategies.items():
        info = _model_metrics(target, masks[name], strokes, sampling_step=sampling_step)
        interior = _render_segments(target.shape, strokes[1:])
        info["contour_interior_overlap_logical_pixels"] = int(
            np.count_nonzero(contour_pixels & interior)
        )
        info["interior_scanline_count"] = len(strokes) - 1
        info["contour_first"] = True
        info["rows_preserved"] = (
            tuple(stroke["points"][0][1] for stroke in strokes[1:])
            == tuple(stroke["points"][0][1] for stroke in scanlines)
        )
        rows[name] = info
    result = {
        "schema_version": 1,
        "protocol": "FILL001_CONTOUR_EDGE_TRIMS_V2",
        "status": "OFFLINE_EXPLORATORY_ONLY",
        "predecessor_protocol": previous["protocol"],
        "shape_id": shape_id,
        "frozen_mask_sha256": previous["frozen_mask_sha256"],
        "baseline_plan_signature": baseline["plan_signature"],
        "brush_value": brush_value,
        "contour_inset": contour_inset,
        "scanline_row_step": scanline_row_step,
        "sampling_step_proxy": sampling_step,
        "tested_endpoint_trims": list(endpoint_trims),
        "strategies": rows,
        "measurement_scope": {
            "quality": "OpenCV logical mask model only",
            "measured_chalk": None,
            "native_egret_equivalence": False,
            "runtime_validated": False,
            "executor_ready": False,
            "changed_variable": "X endpoints only; frozen row locations and closed first contour unchanged.",
            "preceding_v1_negative": "7..9 distance-transform inward cropping failed coverage gate on three shapes",
        },
    }
    return result, {"target": target, **masks}


def save_contour_edge_trim_report(output_dir: Path, shapes: list[str]) -> Path:
    if output_dir.exists():
        raise FileExistsError("Refusing to replace prior experimental artifacts")
    output_dir.mkdir(parents=True)
    reports = []
    for shape_id in shapes:
        report, masks = compare_contour_edge_trims(shape_id)
        reports.append(report)
        for name, raster in masks.items():
            output = output_dir / f"{shape_id}_{name}.png"
            if not cv2.imwrite(str(output), np.uint8(raster) * 255):
                raise OSError("Cannot save diagnostic PNG")
    output = output_dir / "contour_edge_trims_comparison.json"
    output.write_text(json.dumps({
        "analysis_type": "fill001_contour_edge_trims_v2",
        "reports": reports,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output



def export_contour_first_native_fixture(path: Path) -> dict[str, Any]:
    """Prepare immutable-shape multi-stroke inputs for native BoardPane replay.

    Not an executor plan. The pinned original 27-row FILL-001 rectangle is
    retained, and only the stroke ordering is changed in the test control.
    """
    if path.exists():
        raise FileExistsError("Refusing to overwrite native fixture")
    mask = build_fill_target_mask("rectangle")
    digest = fill_target_mask_sha256("rectangle", mask)
    if digest != FILL001_EXPECTED_MASK_SHA256["rectangle"]:
        raise ValueError("Frozen rectangle hash changed")
    original = build_fixed_radius_fill_plan(
        "rectangle", 10, scanline_row_step=5, scanline_offset=0,
    )
    if len(original["strokes"]) != 27:
        raise ValueError("Expected 27 original FILL-001 scanlines")
    contour = _contour_stroke(mask, 6, 10)
    normal = [
        {"points": [{"x": p["x"], "y": p["y"]} for p in stroke["points"]],
         "width": 10, "mode": "normal"}
        for stroke in original["strokes"]
    ]
    boundary = {
        "points": [{"x": int(x), "y": int(y)}
                   for x, y in [*contour["points"], contour["points"][0]]],
        "width": 10, "mode": "normal",
    }
    fixture = {
        "schema": "FILL001_NATIVE_CONTOUR_FIRST_V1",
        "status": "OFFLINE_SYNTHETIC_INPUT_ONLY",
        "shape_id": "rectangle",
        "frozen_mask_sha256": digest,
        "baseline_plan_signature": original["plan_signature"],
        "brush": 10,
        "contour_inset": 6,
        "cases": {
            "B_sparse_only": normal,
            "C_contour_last": [*normal, boundary],
            "E_contour_first": [boundary, *normal],
        },
        "measured_chalk": None,
        "runtime_validated": False,
        "executor_ready": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return fixture



def export_contour_trim_native_fixture(path: Path) -> dict[str, Any]:
    """Versioned native input: contour first and 1..4px X endpoint trims.

    Uses one immutable frozen target, identical rows and contour across cases.
    This is synthetic geometry, not an executor plan or exact game CHALK.
    """
    if path.exists():
        raise FileExistsError("Refusing to replace V2 native fixture")
    baseline = export_contour_first_native_fixture(path)
    # Recreate as the independent V2 artifact, removing the intermediate V1
    # file only because it was created by this invocation at a new path.
    path.unlink()
    original = baseline["cases"]["E_contour_first"]
    cases = dict(baseline["cases"])
    contour = original[0]
    scanlines = original[1:]
    for trim in (1, 2, 3, 4):
        lines = []
        for stroke in scanlines:
            left, right = stroke["points"]
            if right["x"] - left["x"] <= 2 * trim:
                raise ValueError("V2 trim exceeds a frozen scanline")
            lines.append({
                "points": [
                    {"x": left["x"] + trim, "y": left["y"]},
                    {"x": right["x"] - trim, "y": right["y"]},
                ],
                "width": 10, "mode": "normal",
            })
        cases[f"G_trim_{trim}"] = [contour, *lines]
    fixture = {
        **baseline,
        "schema": "FILL001_NATIVE_CONTOUR_EDGE_TRIMS_V2",
        "status": "OFFLINE_SYNTHETIC_INPUT_ONLY",
        "tested_trim_px": [1, 2, 3, 4],
        "cases": cases,
        "analysis_scope": "same frozen 27-row rectangle, contour first, X endpoints only",
        "measured_chalk": None,
        "runtime_validated": False,
        "executor_ready": False,
    }
    path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return fixture


def export_native_bottom_repair_fixture(path: Path) -> dict[str, Any]:
    """V4 bounded native probe: preserved V2 G_trim_3 plus one bottom line.

    The 3 logical-pixel lateral margin is pinned before any native result:
    no screenshot-driven endpoint tuning, planner modification or execution.
    """
    if path.exists():
        raise FileExistsError("Refusing to overwrite frozen native V4 fixture")
    mask = build_fill_target_mask("rectangle")
    sha = fill_target_mask_sha256("rectangle", mask)
    if sha != FILL001_EXPECTED_MASK_SHA256["rectangle"]:
        raise ValueError("Frozen target changed")
    original = build_fixed_radius_fill_plan(
        "rectangle", 10, scanline_row_step=5, scanline_offset=0,
    )
    if len(original["strokes"]) != 27:
        raise ValueError("Native V4 requires the 27-row frozen baseline")
    contour = _contour_stroke(mask, 6, 10)
    outline = {
        "points": [{"x":int(x),"y":int(y)}
                   for x,y in [*contour["points"],contour["points"][0]]],
        "width":10,"mode":"normal",
    }
    rows = []
    for stroke in original["strokes"]:
        p,q = stroke["points"]
        if q["x"]-p["x"] <= 6:
            raise ValueError("Unexpected narrow frozen row")
        rows.append({
            "points":[{"x":p["x"]+3,"y":p["y"]},{"x":q["x"]-3,"y":q["y"]}],
            "width":10,"mode":"normal",
        })
    baseline = [outline,*rows]
    # Pin a row-specific interior line with both endpoints strictly inside
    # the narrowest bottom mask row, leaving 3 logical pixels per side.
    xs = np.flatnonzero(mask[190])
    if (len(xs) != 273 or int(xs[0]) != 94 or int(xs[-1]) != 366
            or not bool(mask[189, int(xs[0]+3):int(xs[-1]-3)+1].all())
            or not bool(mask[190, int(xs[0]+3):int(xs[-1]-3)+1].all())):
        raise ValueError("V4 bottom-row frozen geometry drift")
    start,end = int(xs[0]+3),int(xs[-1]-3)
    cases = {"G_trim_3_control":baseline}
    for width in (1,2,3):
        for y in (189,190):
            line={
                "points":[{"x":start,"y":y},{"x":end,"y":y}],
                "width":width,"mode":"normal",
            }
            cases[f"J_bottom_y{y}_w{width}"]=[*baseline,line]
    fixture={
        "schema":"FILL001_NATIVE_BOTTOM_REPAIR_V4",
        "status":"OFFLINE_SYNTHETIC_INPUT_ONLY",
        "shape_id":"rectangle",
        "frozen_mask_sha256":sha,
        "baseline_plan_signature":original["plan_signature"],
        "baseline_variant":"FILL001_NATIVE_CONTOUR_EDGE_TRIMS_V2/G_trim_3",
        "baseline_contour_width":10,
        "baseline_contour_inset":6,
        "baseline_endpoint_trim":3,
        "bottom_target_row":190,
        "bottom_line_endpoints":[start,end],
        "candidate_widths":[1,2,3],
        "candidate_y":[189,190],
        "cases":cases,
        "measured_chalk":None,
        "runtime_validated":False,
        "executor_ready":False,
    }
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(fixture,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return fixture


def export_mixed_contour_native_fixture(path: Path) -> dict[str, Any]:
    """V3 frozen mixed-width geometry: 5px inset outline, 10px inner scanlines.

    No executor, runtime brush switch, or actual game CHALK is implied.
    """
    if path.exists():
        raise FileExistsError("Refusing to overwrite V3 mixed-width native fixture")
    shape_id = "rectangle"
    mask = build_fill_target_mask(shape_id)
    signature = fill_target_mask_sha256(shape_id, mask)
    if signature != FILL001_EXPECTED_MASK_SHA256[shape_id]:
        raise ValueError("V3 frozen mask SHA mismatch")
    base = build_fixed_radius_fill_plan(
        shape_id, 10, scanline_row_step=5, scanline_offset=0,
    )
    if len(base["strokes"]) != 27:
        raise ValueError("V3 expected 27 stable inner scanline rows")
    scanlines = [
        {"points": [dict(p) for p in stroke["points"]],
         "width": 10, "mode": "normal"}
        for stroke in base["strokes"]
    ]
    legacy = _contour_stroke(mask, 6, 10)
    thin = _contour_stroke(mask, 3, 5)
    outline10 = {
        "points": [{"x": int(x), "y": int(y)}
                   for x, y in [*legacy["points"], legacy["points"][0]]],
        "width": 10, "mode": "normal",
    }
    outline5 = {
        "points": [{"x": int(x), "y": int(y)}
                   for x, y in [*thin["points"], thin["points"][0]]],
        "width": 5, "mode": "normal",
    }
    cases = {"E_contour_10": [outline10, *scanlines]}
    for trim in range(5):
        amended = []
        for stroke in scanlines:
            p, q = stroke["points"]
            if q["x"] - p["x"] <= 2*trim:
                raise ValueError("V3 requested trim exceeds row length")
            amended.append({
                "points": [
                    {"x": p["x"]+trim, "y": p["y"]},
                    {"x": q["x"]-trim, "y": q["y"]},
                ],
                "width": 10, "mode": "normal",
            })
        cases[f"H_mixed_trim_{trim}"] = [outline5, *amended]
    fixture = {
        "schema": "FILL001_NATIVE_MIXED_CONTOUR_V3",
        "status": "OFFLINE_SYNTHETIC_INPUT_ONLY",
        "shape_id": shape_id,
        "frozen_mask_sha256": signature,
        "baseline_plan_signature": base["plan_signature"],
        "contour_width": 5, "contour_inset": 3,
        "interior_width": 10, "row_step": 5,
        "tested_trim_px": [0, 1, 2, 3, 4],
        "cases": cases,
        "measured_chalk": None,
        "runtime_validated": False,
        "executor_ready": False,
        "limitations": "Two brush widths require additional game/runtime evidence.",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fixture, indent=2, ensure_ascii=False)+"\n",
                    encoding="utf-8")
    return fixture


def analyze_contour_native_pngs(render_dir: Path, report_path: Path) -> dict[str, Any]:
    """Read-only native BoardPane alpha screen; never a live PNG quality gate.

    Frozen logical pixels are expanded exactly 3x into local BoardPane backing
    pixels. No fitted translation, dilation, erosion or inferred screen ROI is
    permitted. Alpha cutoffs 1, 64, 128 and 254 are sensitivity diagnostics.
    """
    if report_path.exists():
        raise FileExistsError("Refusing to replace native contour audit")
    manifest_path = render_dir / "manifest.json"
    native_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    target = build_fill_target_mask("rectangle")
    frozen_sha = fill_target_mask_sha256("rectangle", target)
    cases = native_manifest.get("cases")
    is_v2 = native_manifest.get("schema") == "FILL001_NATIVE_CONTOUR_EDGE_TRIMS_V2"
    is_v3 = native_manifest.get("schema") == "FILL001_NATIVE_MIXED_CONTOUR_V3"
    names = (("E_contour_10",) + tuple(f"H_mixed_trim_{i}" for i in range(5))
             if is_v3 else ("B_sparse_only", "C_contour_last", "E_contour_first"))
    if is_v3:
        if native_manifest.get("testedTrimPx") != [0,1,2,3,4] or native_manifest.get("mixedBrushWidths") != [5,10]:
            raise ValueError("V3 mixed brush geometry parameter identity mismatch")
    if is_v2:
        names += tuple(f"G_trim_{i}" for i in range(1,5))
        if native_manifest.get("testedTrimPx") != [1, 2, 3, 4]:
            raise ValueError("V2 trim parameter identity mismatch")
    if (native_manifest.get("schema") not in ("FILL001_NATIVE_CONTOUR_FIRST_V1", "FILL001_NATIVE_CONTOUR_EDGE_TRIMS_V2", "FILL001_NATIVE_MIXED_CONTOUR_V3")
            or native_manifest.get("status") != "OFFLINE_NATIVE_EGRET_RENDERED"
            or native_manifest.get("sourceMaskSha256") != frozen_sha
            or set(cases or {}) != set(names)
            or native_manifest.get("measuredChalk") is not None
            or native_manifest.get("executorReady") is not False):
        raise ValueError("Untrusted native contour manifest identity")
    projected = np.repeat(np.repeat(target, 3, axis=0), 3, axis=1)
    alpha_by_case = {}
    sha_by_case = {}
    for name in names:
        png_name = f"fill001-native-{name}.png"
        if cases[name].get("pngName") != png_name:
            raise ValueError("Native PNG manifest name mismatch")
        source = render_dir / png_name
        raw = source.read_bytes()
        raster = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        if raster is None or raster.dtype != np.uint8 or raster.shape != (720, 1380, 4):
            raise ValueError("Native PNG must be RGBA 1380x720")
        alpha_by_case[name] = raster[:, :, 3]
        sha_by_case[name] = hashlib.sha256(raw).hexdigest()
    if not is_v3:
        b = alpha_by_case["B_sparse_only"]
        c = alpha_by_case["C_contour_last"]
        e = alpha_by_case["E_contour_first"]
        if not np.array_equal(c, e) or np.array_equal(b, e):
            raise ValueError("Native first-vs-last parity or added contour benefit failed")
        if (native_manifest.get("comparisons", {}).get("contourFirstVsLast", {})
                .get("differingPixels") != 0):
            raise ValueError("Native manifest and PNG pair disagree")
    else:
        e = alpha_by_case["E_contour_10"]
        for trim in range(5):
            if np.array_equal(e, alpha_by_case[f"H_mixed_trim_{trim}"]):
                raise ValueError("Native V3 mixed contour variant made no change")
            delta = native_manifest.get("comparisons", {}).get(f"contourFirstVsTrim{trim}", {})
            if not isinstance(delta.get("differingPixels"), int) or delta["differingPixels"] <= 0:
                raise ValueError("V3 native mix manifest PNG mismatch")
    metrics = {}
    for name in names:
        alpha = alpha_by_case[name]
        rows = {}
        for cutoff in (1, 64, 128, 254):
            painted = alpha >= cutoff
            covered = int(np.count_nonzero(painted & projected))
            missing = int(np.count_nonzero(~painted & projected))
            leak = int(np.count_nonzero(painted & ~projected))
            rows[str(cutoff)] = {
                "covered_target_backing_pixels": covered,
                "uncovered_target_backing_pixels": missing,
                "leakage_backing_pixels": leak,
                "coverage_fraction": covered / int(projected.sum()),
            }
        metrics[name] = {
            "native_png_sha256": sha_by_case[name],
            "stroke_count": cases[name]["strokeCount"],
            "accepted_synthetic_points_not_chalk": cases[name]["acceptedSyntheticPoints"],
            "alpha_threshold_diagnostics": rows,
        }
    if is_v2:
        for trim in range(1,5):
            case = alpha_by_case[f"G_trim_{trim}"]
            if np.array_equal(e, case):
                raise ValueError("V2 native endpoint trim rendered identical output")
            delta = native_manifest.get("comparisons", {}).get(f"contourFirstVsTrim{trim}", {})
            if not isinstance(delta.get("differingPixels"), int) or delta["differingPixels"] <= 0:
                raise ValueError("V2 native trim manifest mismatch")
    report = {
        "schema": ("FILL001_NATIVE_CONTOUR_ALPHA_AUDIT_V3" if is_v3
                   else "FILL001_NATIVE_CONTOUR_ALPHA_AUDIT_V2" if is_v2
                   else "FILL001_NATIVE_CONTOUR_ALPHA_AUDIT_V1"),
        "status": "OFFLINE_NATIVE_DIAGNOSTIC_ONLY",
        "source_native_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "frozen_mask_sha256": frozen_sha,
        "local_backing_canvas": {"width": 1380, "height": 720, "scale": 3},
        "projected_target_backing_pixels": int(projected.sum()),
        "projection": "nearest_3x_frozen_logical_mask_no_alignment",
        "alpha_cutoffs": [1, 64, 128, 254],
        "cases": metrics,
        "tested_trim_px": [0,1,2,3,4] if is_v3 else [1,2,3,4] if is_v2 else None,
        "native_comparisons": native_manifest.get("comparisons", {}),
        "order_parity_exact_rgba": None if is_v3 else True,
        "measured_chalk": None,
        "game_png_quality_gate": "NOT_EVALUATED",
        "native_to_live_stage_mapping": "NOT_EVALUATED",
        "limitations": [
            "Exact native local BoardPane alpha only, NOT same-run screen RGB.",
            "Nearest logical-to-native mask raster differs from V3 run-bound Screen Mask V2.",
            "Synthetic straight two-point scans, not the live 1461 accepted-point trajectories.",
            "Alpha cutoffs are diagnostic sensitivity, not a substitute for RGB threshold 8.",
            "No executed CHALK or live leak/coverage acceptance claimed.",
        ],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report



def analyze_native_brush_footprints(render_dir: Path, report_path: Path) -> dict[str, Any]:
    """Independent read-only native brush footprint analysis (FILL-001 A).

    No mask alignment, game-quality gate, CHALK inference or production defaults.
    Each alpha span is measured directly from real Egret WebGL RGBA PNGs,
    with the complete pinned case coordinates and source checksums verified.
    """
    if report_path.exists():
        raise FileExistsError("Footprint audit refuses to overwrite previous evidence")
    manifest_path = render_dir / "manifest.json"
    provenance_path = render_dir / "capture-provenance.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    expected_points = {
        "horizontal": [(130,120), (330,120)],
        "vertical": [(230,40), (230,200)],
        "diagonal": [(130,60), (330,180)],
        "corner": [(150,70), (300,70), (300,180)],
    }
    expected = {
        f"normal_{orientation}_w{width}": ("normal", width, locations)
        for width in (5,10)
        for orientation, locations in expected_points.items()
    }
    expected.update({
        f"smooth_horizontal_w{width}": ("smooth", width, expected_points["horizontal"])
        for width in (5,10)
    })
    entries = manifest.get("cases")
    if (manifest.get("schema") != "FILL001_NATIVE_FOOTPRINT_A_V1"
            or manifest.get("status") != "OFFLINE_NATIVE_EGRET_RENDERED"
            or manifest.get("engineVersion") != "5.4.1"
            or manifest.get("canvasSize") != {"width":1380, "height":720}
            or manifest.get("logicalBoard") != {"width":460, "height":240}
            or manifest.get("scale") != 3
            or manifest.get("alphaThresholds") != [1,64,128,254]
            or manifest.get("measuredChalk") is not None
            or manifest.get("originalGameCapture") is not None
            or manifest.get("executorReady") is not False
            or manifest.get("gameQualityGate") != "NOT_EVALUATED"
            or manifest.get("liveStageMapping") != "NOT_EVALUATED"
            or not isinstance(entries, list) or len(entries) != 10
            or {item.get("id") for item in entries if isinstance(item, dict)} != set(expected)
            or provenance.get("schema") != "FILL001_NATIVE_FOOTPRINT_CAPTURE_A_V1"
            or provenance.get("liveRunId") is not None
            or provenance.get("exactChalk") is not None
            or set(provenance.get("pngSha256") or {}) !=
               {f"fill001-footprint-{name}.png" for name in expected}):
        raise ValueError("Native footprint audit rejects unverified case inventory or provenance")
    cases = {}
    for item in entries:
        name = item["id"]
        mode, width, points = expected[name]
        filename = f"fill001-footprint-{name}.png"
        if (item.get("pngName") != filename
                or item.get("mode") != mode or item.get("width") != width
                or item.get("points") != [{"x":x,"y":y} for x,y in points]
                or item.get("acceptedSyntheticVerticesNotChalk") != len(points)
                or item.get("sceneDiagnostics", {}).get("boardRenderMode") != 3):
            raise ValueError("Native footprint audit rejects changed stroke coordinates or mode")
        raw = (render_dir / filename).read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        if sha != provenance["pngSha256"][filename]:
            raise ValueError("Native footprint PNG SHA-256 does not match capture provenance")
        rgba = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
        if rgba is None or rgba.dtype != np.uint8 or rgba.shape != (720,1380,4):
            raise ValueError("Native footprint PNG must be RGBA 1380x720")
        alpha = rgba[:,:,3]
        per_cutoff = {}
        for cutoff in (1,64,128,254):
            painted = alpha >= cutoff
            yy, xx = np.nonzero(painted)
            if len(xx) == 0:
                per_cutoff[str(cutoff)] = {
                    "painted_backing_pixels":0, "bounding_xyxy":None,
                    "midpoint_cross_section_backing_px":None,
                    "start_axial_extension_backing_px":None,
                    "end_axial_extension_backing_px":None,
                    "sample_cross_sections_backing_px":[],
                    "corner_joint_13x13_painted_pixels":None,
                }
                continue
            bbox = [int(xx.min()), int(yy.min()), int(xx.max()), int(yy.max())]
            orientation = name.split("_w",1)[0].split("_",1)[1]
            cross = None
            start_extension = None
            end_extension = None
            samples = []
            if orientation == "horizontal":
                cy = points[0][1] * 3
                for logical_x in (150,230,310):
                    col = np.flatnonzero(painted[:,logical_x * 3])
                    samples.append({
                        "logical_x": logical_x,
                        "vertical_span_backing_px": (int(col.max()-col.min()+1)
                                                     if len(col) else 0),
                        "y_minmax": [int(col.min()),int(col.max())] if len(col) else None,
                    })
                cross = samples[1]["vertical_span_backing_px"]
                start_extension = points[0][0]*3-bbox[0]
                end_extension = bbox[2]-points[-1][0]*3
            elif orientation == "vertical":
                for logical_y in (60,120,180):
                    row = np.flatnonzero(painted[logical_y * 3,:])
                    samples.append({
                        "logical_y": logical_y,
                        "horizontal_span_backing_px": (int(row.max()-row.min()+1)
                                                       if len(row) else 0),
                        "x_minmax": [int(row.min()),int(row.max())] if len(row) else None,
                    })
                cross = samples[1]["horizontal_span_backing_px"]
                start_extension = points[0][1]*3-bbox[1]
                end_extension = bbox[3]-points[-1][1]*3
            joint = None
            if orientation == "corner":
                jx,jy = points[1][0]*3, points[1][1]*3
                joint = int(np.count_nonzero(painted[jy-6:jy+7,jx-6:jx+7]))
            per_cutoff[str(cutoff)] = {
                "painted_backing_pixels":int(len(xx)),
                "bounding_xyxy":bbox,
                "midpoint_cross_section_backing_px":cross,
                "start_axial_extension_backing_px":start_extension,
                "end_axial_extension_backing_px":end_extension,
                "sample_cross_sections_backing_px":samples,
                "corner_joint_13x13_painted_pixels":joint,
            }
        cases[name] = {
            "mode":mode, "width":width,
            "input_points_logical": [{"x":x,"y":y} for x,y in points],
            "png_sha256":sha,
            "thresholds":per_cutoff,
        }
    # Long smooth paths normally omit the last half-segment when drawLast=false;
    # record the actual extent rather than assuming the raster's theoretical tip.
    deltas = {}
    for width in (5,10):
        normal = cases[f"normal_horizontal_w{width}"]["thresholds"]["128"]
        smooth = cases[f"smooth_horizontal_w{width}"]["thresholds"]["128"]
        deltas[str(width)] = {
            "normal_bbox_xmax":normal["bounding_xyxy"][2] if normal["bounding_xyxy"] else None,
            "smooth_bbox_xmax":smooth["bounding_xyxy"][2] if smooth["bounding_xyxy"] else None,
            "normal_minus_smooth_right_extent_backing_px":(
                normal["bounding_xyxy"][2]-smooth["bounding_xyxy"][2]
                if normal["bounding_xyxy"] and smooth["bounding_xyxy"] else None
            ),
        }
    report = {
        "schema":"FILL001_NATIVE_FOOTPRINT_ANALYSIS_A_V1",
        "status":"OFFLINE_NATIVE_DIAGNOSTIC_ONLY",
        "manifest_sha256":hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "capture_provenance_sha256":hashlib.sha256(provenance_path.read_bytes()).hexdigest(),
        "case_count":10,
        "native_backing":{"width":1380,"height":720,"scale":3},
        "alpha_thresholds":[1,64,128,254],
        "cases":cases,
        "smooth_vs_normal_right_extent":deltas,
        "measured_chalk":None,
        "game_quality_gate":"NOT_EVALUATED",
        "native_to_game_screen_equivalence":"NOT_EVALUATED",
        "executor_ready":False,
        "scope_note":(
            "Empirical WebGL local-BoardPane alpha footprints; no frozen target "
            "coverage/leakage acceptance, Stage screen projection, live timing or CHALK."
        ),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n",
                           encoding="utf-8")
    return report



def _spatial_partition_contour_residual(
    target: np.ndarray, painted: np.ndarray, *, edge_band: int = 18,
) -> dict[str, Any]:
    """Exhaustive, disjoint spatial zones for a 3x native frozen mask.

    Uses the pinned nearest-3x target, not image-dependent alignment or
    morphology. Top/bottom mean the first/last three target backing rows.
    Middle-row missing pixels are left/right edge-band or interior. Leakage
    is classified by the row's original target extents, not brush geometry.
    """
    if (target.shape != (720,1380) or painted.shape != target.shape or
            target.dtype != np.bool_ or painted.dtype != np.bool_ or
            type(edge_band) is not int or edge_band < 1):
        raise ValueError("Invalid fixed native spatial partition inputs")
    missing = target & ~painted
    leakage = ~target & painted
    yy = np.flatnonzero(target.any(axis=1))
    if not len(yy):
        raise ValueError("Empty native target")
    top, bottom = int(yy[0]), int(yy[-1])
    zones_missing = {k:0 for k in ("top", "bottom", "left", "right", "interior")}
    zones_leakage = {k:0 for k in ("above", "below", "left", "right", "other")}
    rows = []
    for y in range(target.shape[0]):
        xs = np.flatnonzero(target[y])
        miss_xs = np.flatnonzero(missing[y])
        leak_xs = np.flatnonzero(leakage[y])
        if not len(xs):
            if len(miss_xs):
                raise ValueError("Uncovered pixels cannot occur outside target rows")
            if len(leak_xs):
                zones_leakage["above" if y < top else "below"] += int(len(leak_xs))
            if len(leak_xs):
                rows.append({
                    "backing_y":y, "target_x_minmax":None,
                    "uncovered":0, "leakage":int(len(leak_xs)),
                    "uncovered_left":0, "uncovered_right":0,
                    "uncovered_interior":0,
                })
            continue
        left, right = int(xs[0]), int(xs[-1])
        if len(xs) != right-left+1:
            raise ValueError("Expected contiguous frozen rectangle target per row")
        is_top = y <= top+2
        is_bottom = y >= bottom-2
        if is_top:
            zones_missing["top"] += int(len(miss_xs))
            left_count = right_count = interior_count = 0
        elif is_bottom:
            zones_missing["bottom"] += int(len(miss_xs))
            left_count = right_count = interior_count = 0
        else:
            left_count = int(np.count_nonzero(miss_xs < left + edge_band))
            right_count = int(np.count_nonzero(miss_xs > right - edge_band))
            interior_count = int(len(miss_xs)) - left_count - right_count
            if interior_count < 0:
                raise ValueError("Native edge zones overlap")
            zones_missing["left"] += left_count
            zones_missing["right"] += right_count
            zones_missing["interior"] += interior_count
        if len(leak_xs):
            l = int(np.count_nonzero(leak_xs < left))
            r = int(np.count_nonzero(leak_xs > right))
            zones_leakage["left"] += l
            zones_leakage["right"] += r
            zones_leakage["other"] += int(len(leak_xs))-l-r
        if len(miss_xs) or len(leak_xs):
            rows.append({
                "backing_y":y, "target_x_minmax":[left,right],
                "uncovered":int(len(miss_xs)),
                "leakage":int(len(leak_xs)),
                "uncovered_left":left_count,
                "uncovered_right":right_count,
                "uncovered_interior":interior_count,
            })
    miss_n, leak_n = int(missing.sum()),int(leakage.sum())
    if sum(zones_missing.values()) != miss_n or sum(zones_leakage.values()) != leak_n:
        raise ValueError("Native spatial zones are not a full partition")
    labels_missing, components_missing = cv2.connectedComponents(
        missing.astype(np.uint8), connectivity=8,
    )
    labels_leak, components_leak = cv2.connectedComponents(
        leakage.astype(np.uint8), connectivity=8,
    )
    def groups(label_map: np.ndarray, count: int) -> list[dict[str, Any]]:
        result=[]
        for label in range(1,count):
            ys,xs=np.nonzero(label_map==label)
            if not len(xs): continue
            result.append({
                "pixels":int(len(xs)),
                "bounding_xyxy":[int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max())],
            })
        return sorted(result,key=lambda r:(-r["pixels"],r["bounding_xyxy"]))[:8]
    return {
        "target_backing_pixels":int(target.sum()),
        "uncovered_backing_pixels":miss_n,
        "leakage_backing_pixels":leak_n,
        "target_vertical_bounds_backing":[top,bottom],
        "edge_band_backing_pixels":edge_band,
        "uncovered_regions":zones_missing,
        "leakage_regions":zones_leakage,
        "uncovered_connected_component_count":int(labels_missing-1),
        "leakage_connected_component_count":int(labels_leak-1),
        "largest_uncovered_components":groups(components_missing,labels_missing),
        "largest_leakage_components":groups(components_leak,labels_leak),
        "worst_uncovered_rows":sorted(rows,key=lambda r:(-r["uncovered"],r["backing_y"]))[:10],
        "worst_leakage_rows":sorted(rows,key=lambda r:(-r["leakage"],r["backing_y"]))[:10],
        "row_residuals":rows,
    }


def analyze_native_contour_spatial_residual(render_dir: Path, report_path: Path) -> dict[str, Any]:
    """Independent fixed-geometry locality audit for a prior native V2/V3 run.

    Only verified, frozen mask + raw PNG + existing alpha report. Never invent
    repaired strokes or use source-unknown capture screenshots.
    """
    if report_path.exists():
        raise FileExistsError("Native spatial residual report already exists")
    manifest_path = render_dir/"manifest.json"
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    schema=manifest.get("schema")
    if schema not in ("FILL001_NATIVE_CONTOUR_EDGE_TRIMS_V2",
                      "FILL001_NATIVE_MIXED_CONTOUR_V3"):
        raise ValueError("Spatial audit requires pinned native V2 or V3 manifest")
    version="v2" if schema.endswith("_V2") else "v3"
    alpha_path=render_dir/f"native-alpha-audit-{version}.json"
    previous=json.loads(alpha_path.read_text(encoding="utf-8"))
    mask=build_fill_target_mask("rectangle")
    sha=fill_target_mask_sha256("rectangle",mask)
    if (sha != FILL001_EXPECTED_MASK_SHA256["rectangle"]
            or manifest.get("sourceMaskSha256") != sha
            or previous.get("frozen_mask_sha256") != sha
            or previous.get("source_native_manifest_sha256") != hashlib.sha256(manifest_raw).hexdigest()
            or previous.get("status") != "OFFLINE_NATIVE_DIAGNOSTIC_ONLY"
            or previous.get("game_png_quality_gate") != "NOT_EVALUATED"
            or previous.get("measured_chalk") is not None
            or manifest.get("measuredChalk") is not None
            or manifest.get("executorReady") is not False):
        raise ValueError("Native spatial residual provenance or quality scope invalid")
    expected=(
        ("B_sparse_only", "C_contour_last","E_contour_first")+
        tuple(f"G_trim_{i}" for i in range(1,5))
        if version=="v2" else
        ("E_contour_10",)+tuple(f"H_mixed_trim_{i}" for i in range(5))
    )
    if set(manifest.get("cases") or {}) != set(expected) or set(previous.get("cases") or {}) != set(expected):
        raise ValueError("Native spatial audit refuses changed case inventory")
    projected=np.repeat(np.repeat(mask,3,axis=0),3,axis=1)
    output={}
    for name in expected:
        png=f"fill001-native-{name}.png"
        if manifest["cases"][name].get("pngName") != png:
            raise ValueError("Native PNG name mismatch")
        raw=(render_dir/png).read_bytes()
        if hashlib.sha256(raw).hexdigest() != previous["cases"][name].get("native_png_sha256"):
            raise ValueError("Native PNG SHA differs from earlier independent alpha audit")
        rgba=cv2.imdecode(np.frombuffer(raw,dtype=np.uint8),cv2.IMREAD_UNCHANGED)
        if rgba is None or rgba.shape != (720,1380,4) or rgba.dtype != np.uint8:
            raise ValueError("Native source image is not 1380x720 RGBA")
        groups={}
        for cutoff in (1,128,254):
            painted=rgba[:,:,3]>=cutoff
            detail=_spatial_partition_contour_residual(projected,painted)
            previous_row=previous["cases"][name]["alpha_threshold_diagnostics"][str(cutoff)]
            if (detail["uncovered_backing_pixels"] != previous_row["uncovered_target_backing_pixels"]
                    or detail["leakage_backing_pixels"] != previous_row["leakage_backing_pixels"]):
                raise ValueError("Spatial residual disagrees with frozen earlier alpha audit")
            groups[str(cutoff)]=detail
        output[name]=groups
    report={
        "schema":"FILL001_NATIVE_CONTOUR_SPATIAL_AUDIT_V1",
        "status":"OFFLINE_NATIVE_DIAGNOSTIC_ONLY",
        "source_native_variant":version,
        "source_manifest_sha256":hashlib.sha256(manifest_raw).hexdigest(),
        "source_alpha_audit_sha256":hashlib.sha256(alpha_path.read_bytes()).hexdigest(),
        "frozen_mask_sha256":sha,
        "projection":"frozen_logical_to_native_backing_nearest3_no_alignment",
        "region_rule":"first/last 3 target backing rows, then 18px lateral bands, then interior",
        "thresholds":[1,128,254],
        "cases":output,
        "measured_chalk":None,
        "native_to_live_screen":"NOT_EVALUATED",
        "game_png_quality_gate":"NOT_EVALUATED",
        "repair_plan":"NOT_GENERATED",
        "executor_ready":False,
    }
    report_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--shape", choices=FILL001_SHAPES, action="append")
    parser.add_argument("--native-spatial-dir", type=Path,
                        help="Partition pinned native V2/V3 alpha residual by frozen boundary row/side.")
    parser.add_argument("--native-footprint-dir", type=Path,
                        help="Independently audit isolated native Egret footprint PNGs.")
    parser.add_argument("--native-render-dir", type=Path,
                        help="Recheck native contour RGBA against frozen 3x logical target, diagnostic only.")
    parser.add_argument("--native-bottom-fixture", action="store_true",
                        help="Export V4 thin bottom boundary repair on frozen V2 trim3.")
    parser.add_argument("--native-mixed-fixture", action="store_true",
                        help="Export V3 5px contour / 10px interior native study.")
    parser.add_argument("--native-trim-fixture", action="store_true",
                        help="Export isolated V2 contour-first X-endpoint native sweep.")
    parser.add_argument("--native-fixture", action="store_true",
                        help="Write a single multi-stroke native-browser input JSON.")
    parser.add_argument("--contour-first", action="store_true",
                        help="Separate controlled contour-first/inset study.")
    parser.add_argument("--contour-edge-trims", action="store_true",
                        help="Versioned V2 endpoint-only trimming study.")
    args = parser.parse_args(argv)
    if args.native_spatial_dir is not None:
        if (args.native_footprint_dir is not None or args.native_render_dir is not None
                or args.native_bottom_fixture or args.native_mixed_fixture or args.native_trim_fixture or args.native_fixture
                or args.contour_first or args.contour_edge_trims or args.shape):
            parser.error("--native-spatial-dir is an isolated read-only diagnostic.")
        analyze_native_contour_spatial_residual(args.native_spatial_dir,args.output_dir)
        return 0
    if args.native_footprint_dir is not None:
        if (args.native_render_dir is not None or args.native_spatial_dir is not None or args.native_mixed_fixture
                or args.native_trim_fixture or args.native_fixture or args.contour_first
                or args.contour_edge_trims or args.shape):
            parser.error("--native-footprint-dir is an isolated read-only diagnostic.")
        analyze_native_brush_footprints(args.native_footprint_dir, args.output_dir)
        return 0
    if args.native_render_dir is not None:
        if args.native_fixture or args.native_trim_fixture or args.native_mixed_fixture or args.native_spatial_dir is not None or args.contour_first or args.contour_edge_trims or args.shape:
            parser.error("--native-render-dir must be used alone.")
        analyze_contour_native_pngs(args.native_render_dir, args.output_dir)
        return 0
    if args.native_bottom_fixture:
        if (args.native_mixed_fixture or args.native_trim_fixture or args.native_fixture
                or args.native_render_dir is not None or args.native_spatial_dir is not None
                or args.native_footprint_dir is not None or args.contour_first
                or args.contour_edge_trims or args.shape):
            parser.error("--native-bottom-fixture must be used alone")
        export_native_bottom_repair_fixture(args.output_dir)
        return 0
    if args.native_mixed_fixture:
        if args.native_fixture or args.native_bottom_fixture or args.native_trim_fixture or args.contour_first or args.contour_edge_trims or args.shape:
            parser.error("--native-mixed-fixture must be used alone.")
        export_mixed_contour_native_fixture(args.output_dir)
        return 0
    if args.native_trim_fixture:
        if args.native_fixture or args.contour_first or args.contour_edge_trims or args.shape:
            parser.error("--native-trim-fixture must be used alone.")
        export_contour_trim_native_fixture(args.output_dir)
        return 0
    if args.native_fixture:
        if args.contour_first or args.contour_edge_trims or args.shape:
            parser.error("--native-fixture cannot be combined with other options.")
        export_contour_first_native_fixture(args.output_dir)
        return 0
    if args.contour_first and args.contour_edge_trims:
        parser.error("Choose only one contour experiment version.")
    if args.contour_edge_trims:
        save_contour_edge_trim_report(args.output_dir, args.shape or list(FILL001_SHAPES))
    elif args.contour_first:
        save_contour_first_report(args.output_dir, args.shape or list(FILL001_SHAPES))
    else:
        save_exploratory_report(args.output_dir, args.shape or list(FILL001_SHAPES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

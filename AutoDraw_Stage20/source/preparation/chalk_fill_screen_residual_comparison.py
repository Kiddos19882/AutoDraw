from __future__ import annotations

"""FILL-001: diagnostic counterfactual contour overlays on the committed live ROI.

The unchanged RGB before/after screenshots remain the only ACTUAL observed
paint. Candidate contour pixels are projected from the frozen logical OpenCV
model; set unions are hypothetical overlays, NOT new screen captures or live
acceptance. This module cannot validate a game's rendering of a new stroke.
"""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from chalk_fill_capture_adapter import (
    LOGICAL_BOARD_HEIGHT,
    LOGICAL_BOARD_WIDTH,
    PNG_CHANGE_THRESHOLD,
    _png_pixels,
    audit_fill001_png_pair,
)
from chalk_fill_experiment import (
    FILL001_EXPECTED_MASK_SHA256,
    build_fill_target_mask,
    fill_target_mask_sha256,
)
from chalk_fill_fixed_radius_planner import build_fixed_radius_fill_plan
from chalk_fill_strategy_comparison import _contour_stroke, _render_segments

TASK_ID = "fill001-rs-preflight-20261104-7.04-rectangle-r10-s5-o0-rep1"
CAPTURE_BASE = "fill001/captures/" + TASK_ID
EXPECTED_BEFORE_SHA256 = "ce5560ef85b8c63b2e2fc93056eae685bb0c6f8146f106c843daad7f97577576"
EXPECTED_AFTER_SHA256 = "a001c62264dac32c2331179ba6a4e39c609aaaf8749381cc6a967803dd338321"
EXPECTED_ATTEMPT_SHA256 = "79a42cf03756ea6f52b4327fc43d9338abc4ea7f004289d206f3455fd89b134b"
EXPECTED_PLAN_SHA256 = "430b79ad350b3ffd70183ca3da29c99b36f54d70079e482d6e553313c9355108"
EXPECTED_PLAN_SIGNATURE = "a0e422160f222276baafea73aa884e3407255d7b3da5ab47778a4d70f434e417"
EXPECTED_ROI = {"x": 566, "y": 253, "width": 581, "height": 304}
EXPECTED_ORIGINAL_UNCOVERED = 1116
EXPECTED_ORIGINAL_LEAKAGE = 11
CONTOUR_INSETS = (5, 6, 7, 8)


def _read_pinned(path: Path, digest: str) -> bytes:
    if not path.is_file():
        raise FileNotFoundError("Required committed evidence missing: " + str(path))
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != digest:
        raise ValueError(f"Committed evidence SHA-256 mismatch: {path.name}: {actual}")
    return raw


def _screen_mask(logical: np.ndarray, source_x: np.ndarray, source_y: np.ndarray) -> np.ndarray:
    return logical[np.ix_(source_y, source_x)]


def _zones(
    mask: np.ndarray, logical_x: np.ndarray, logical_y: np.ndarray
) -> dict[str, int]:
    xx, yy = np.meshgrid(logical_x, logical_y)
    group_masks = {
        "top_y_lt_75": mask & (yy < 75),
        "bottom_y_gt_165": mask & (yy > 165),
        "left_middle_x_le_94": mask & (xx <= 94) & (yy >= 75) & (yy <= 165),
        "right_middle_x_ge_366": mask & (xx >= 366) & (yy >= 75) & (yy <= 165),
    }
    classified = np.zeros_like(mask, dtype=bool)
    for value in group_masks.values():
        classified |= value
    group_masks["interior_or_other"] = mask & ~classified
    return {key: int(np.count_nonzero(value)) for key, value in group_masks.items()}


def _overlay(
    target: np.ndarray,
    actual: np.ndarray,
    *,
    candidate: np.ndarray | None = None,
) -> np.ndarray:
    """RGB diagnostic: gray painted, red misses, violet old leakage, green gains.

    New modeled leakage is orange. These colors are labels, NOT source pixels.
    """
    rgb = np.zeros((*target.shape, 3), dtype=np.uint8)
    rgb[target] = (55, 55, 55)
    rgb[target & actual] = (180, 180, 180)
    rgb[target & ~actual] = (220, 40, 45)
    rgb[~target & actual] = (155, 70, 205)
    if candidate is not None:
        rgb[target & ~actual & candidate] = (40, 210, 80)
        rgb[~target & ~actual & candidate] = (250, 165, 45)
    return rgb


def _candidate_metrics(
    target: np.ndarray,
    actual: np.ndarray,
    candidate: np.ndarray,
    logical_x: np.ndarray,
    logical_y: np.ndarray,
) -> dict[str, Any]:
    if target.shape != actual.shape or target.shape != candidate.shape:
        raise ValueError("Screen candidate dimensions do not match actual ROI")
    uncovered = target & ~actual
    recovered = uncovered & candidate
    new_leakage = ~target & ~actual & candidate
    updated = actual | candidate
    remaining = int(np.count_nonzero(target & ~updated))
    total_leakage = int(np.count_nonzero(~target & updated))
    target_area = int(np.count_nonzero(target))
    old_leakage = int(np.count_nonzero(~target & actual))
    assert total_leakage == old_leakage + int(np.count_nonzero(new_leakage))
    return {
        "candidate_screen_pixels": int(np.count_nonzero(candidate)),
        "actually_missing_screen_pixels_covered_by_model": int(np.count_nonzero(recovered)),
        "recovered_by_zone": _zones(recovered, logical_x, logical_y),
        "remaining_actual_uncovered_under_union": remaining,
        "hypothetical_union_coverage_fraction": round(1.0 - remaining / target_area, 9),
        "hypothetical_new_leakage_pixels": int(np.count_nonzero(new_leakage)),
        "hypothetical_union_leakage_pixels": total_leakage,
        "can_additive_union_pass_original_quality_gates": (
            remaining / target_area <= 0.01 and total_leakage == 0
        ),
    }


def analyze_committed_screen_residual(
    results_root: str | Path,
    *,
    insets: tuple[int, ...] = CONTOUR_INSETS,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    root = Path(results_root)
    before_path = root / (CAPTURE_BASE + "-before.png")
    after_path = root / (CAPTURE_BASE + "-after.png")
    attempt_path = root / "fill001" / "attempts" / (TASK_ID + ".json")
    plan_path = root / "fill001" / "plans" / (TASK_ID + ".json")

    before_raw = _read_pinned(before_path, EXPECTED_BEFORE_SHA256)
    after_raw = _read_pinned(after_path, EXPECTED_AFTER_SHA256)
    attempt = json.loads(_read_pinned(attempt_path, EXPECTED_ATTEMPT_SHA256))
    plan = json.loads(_read_pinned(plan_path, EXPECTED_PLAN_SHA256))
    task = attempt["task"]
    if (
        task.get("task_id") != TASK_ID
        or task.get("shape_id") != "rectangle"
        or task.get("target_mask_sha256") != FILL001_EXPECTED_MASK_SHA256["rectangle"]
        or task.get("plan_signature") != EXPECTED_PLAN_SIGNATURE
        or task.get("requested_radius") != 10
        or task.get("scanline_row_step") != 5
        or task.get("scanline_offset") != 0
        or task.get("expected_strokes") != 27
        or attempt.get("screen_roi") != EXPECTED_ROI
        or len(plan.get("strokes", [])) != 27
    ):
        raise ValueError("Committed task/plan/ROI provenance mismatch")

    frozen = build_fill_target_mask("rectangle")
    if fill_target_mask_sha256("rectangle", frozen) != FILL001_EXPECTED_MASK_SHA256["rectangle"]:
        raise ValueError("Frozen rectangle mask hash mismatch")
    modeled_scanlines = build_fixed_radius_fill_plan(
        "rectangle", 10, scanline_row_step=5, scanline_offset=0
    )
    if modeled_scanlines["plan_signature"] != EXPECTED_PLAN_SIGNATURE:
        raise ValueError("Recreated frozen scanline plan signature mismatch")
    for actual_stroke, model_stroke in zip(plan["strokes"], modeled_scanlines["strokes"]):
        try:
            actual_xy = [
                (float(point["x"]), float(point["y"])) for point in actual_stroke["points"]
            ]
            model_xy = [
                (float(point["x"]), float(point["y"])) for point in model_stroke["points"]
            ]
        except (KeyError, TypeError) as exc:
            raise ValueError("Malformed committed plan stroke") from exc
        if actual_xy != model_xy:
            raise ValueError("Committed plan endpoints do not match recreated baseline")

    before, before_sha = _png_pixels(before_path)
    after, after_sha = _png_pixels(after_path)
    if hashlib.sha256(before_raw).hexdigest() != before_sha or hashlib.sha256(after_raw).hexdigest() != after_sha:
        raise ValueError("PNG hash disagreement")
    screen_h, screen_w = before.shape[:2]
    if before.shape != after.shape or (screen_w, screen_h) != (
        EXPECTED_ROI["width"], EXPECTED_ROI["height"]
    ):
        raise ValueError("Committed PNG ROI dimensions do not match expected capture")
    audit = audit_fill001_png_pair(
        "rectangle", before_path, after_path, screen_roi=EXPECTED_ROI
    )
    scale_x = (screen_w - 1) / LOGICAL_BOARD_WIDTH
    scale_y = (screen_h - 1) / LOGICAL_BOARD_HEIGHT
    source_x = np.clip(
        np.rint(np.arange(screen_w, dtype=np.float64) / scale_x).astype(np.intp),
        0, LOGICAL_BOARD_WIDTH - 1,
    )
    source_y = np.clip(
        np.rint(np.arange(screen_h, dtype=np.float64) / scale_y).astype(np.intp),
        0, LOGICAL_BOARD_HEIGHT - 1,
    )
    target = _screen_mask(frozen, source_x, source_y)
    actual = np.any(np.abs(after - before) > PNG_CHANGE_THRESHOLD, axis=2)
    target_area = int(np.count_nonzero(target))
    uncovered = target & ~actual
    leakage = ~target & actual
    uncovered_count = int(np.count_nonzero(uncovered))
    leakage_count = int(np.count_nonzero(leakage))
    if (
        target_area != audit["target_pixels"]
        or int(np.count_nonzero(actual)) != audit["changed_pixels"]
        or uncovered_count != EXPECTED_ORIGINAL_UNCOVERED
        or leakage_count != EXPECTED_ORIGINAL_LEAKAGE
        or not np.isclose(
            (target_area - uncovered_count) / target_area, audit["coverage_fraction"],
            rtol=0, atol=1e-12,
        )
        or audit["png_audit_status"] != "failed"
    ):
        raise ValueError("Observed PNG residual audit does not match pinned evidence")

    baseline_strokes = [{
        "points": [(int(p["x"]), int(p["y"])) for p in stroke["points"]],
        "brush_value": 10,
        "closed": False,
    } for stroke in modeled_scanlines["strokes"]]
    baseline_model_screen = _screen_mask(
        _render_segments(frozen.shape, baseline_strokes), source_x, source_y
    )
    baseline_error = {
        "model_uncovered_on_target_screen_pixels": int(np.count_nonzero(target & ~baseline_model_screen)),
        "actual_uncovered_on_target_screen_pixels": uncovered_count,
        "model_only_on_target_screen_pixels": int(np.count_nonzero(target & baseline_model_screen & ~actual)),
        "actual_only_on_target_screen_pixels": int(np.count_nonzero(target & actual & ~baseline_model_screen)),
        "model_and_actual_on_target_screen_pixels": int(np.count_nonzero(target & actual & baseline_model_screen)),
        "model_leakage_screen_pixels": int(np.count_nonzero(~target & baseline_model_screen)),
        "actual_leakage_screen_pixels": leakage_count,
    }

    if not insets or any(
        isinstance(inset, bool) or not isinstance(inset, int) or inset < 1
        for inset in insets
    ) or len(insets) != len(set(insets)):
        raise ValueError("Insets must be distinct positive integers")
    overlays: dict[str, np.ndarray] = {
        "actual_residual": _overlay(target, actual),
        "baseline_model_disagreement": np.where(
            (target & baseline_model_screen & ~actual)[:, :, None],
            np.array([240, 205, 45], dtype=np.uint8),
            np.where(
                (target & actual & ~baseline_model_screen)[:, :, None],
                np.array([35, 205, 225], dtype=np.uint8),
                _overlay(target, actual),
            ),
        ).astype(np.uint8),
    }
    perturb_kernel = np.ones((3, 3), dtype=np.uint8)
    candidates = []
    for inset in insets:
        contour = _contour_stroke(frozen, inset, 10)
        contour_logical = _render_segments(frozen.shape, [contour])
        contour_screen = _screen_mask(contour_logical, source_x, source_y)
        nominal = _candidate_metrics(target, actual, contour_screen, source_x, source_y)
        eroded = cv2.erode(contour_screen.astype(np.uint8), perturb_kernel) != 0
        dilated = cv2.dilate(contour_screen.astype(np.uint8), perturb_kernel) != 0
        low = _candidate_metrics(target, actual, eroded, source_x, source_y)
        high = _candidate_metrics(target, actual, dilated, source_x, source_y)
        candidates.append({
            "inset_logical_px": inset,
            "contour_vertices": len(contour["points"]),
            "nominal_logical_contour_pixel_count": int(np.count_nonzero(contour_logical)),
            "nominal_projection": nominal,
            "one_screen_px_erosion_sensitivity": low,
            "one_screen_px_dilation_sensitivity": high,
        })
        overlays[f"model_contour_inset_{inset}"] = _overlay(
            target, actual, candidate=contour_screen
        )

    report = {
        "schema_version": 1,
        "experiment_id": "FILL-001-RS-SCREEN-RESIDUAL-CF-V1",
        "status": "DIAGNOSTIC_COUNTERFACTUAL_NOT_LIVE",
        "task_id": TASK_ID,
        "baseline_plan_signature": EXPECTED_PLAN_SIGNATURE,
        "frozen_mask_sha256": FILL001_EXPECTED_MASK_SHA256["rectangle"],
        "input_evidence_sha256": {
            "before_png": before_sha,
            "after_png": after_sha,
            "attempt": EXPECTED_ATTEMPT_SHA256,
            "plan": EXPECTED_PLAN_SHA256,
        },
        "screen_roi": dict(EXPECTED_ROI),
        "logical_to_screen_mapping": "same_inverse_affine_nearest_neighbor_as_committed_png_audit",
        "scale_x": scale_x,
        "scale_y": scale_y,
        "change_threshold_absolute_rgb": PNG_CHANGE_THRESHOLD,
        "observed_actual_png": {
            "target_screen_pixels": target_area,
            "changed_screen_pixels": int(np.count_nonzero(actual)),
            "uncovered_target_screen_pixels": uncovered_count,
            "uncovered_zones": _zones(uncovered, source_x, source_y),
            "leakage_screen_pixels": leakage_count,
            "leakage_xy": [
                [int(x), int(y)] for y, x in np.argwhere(leakage)
            ],
            "coverage_fraction": audit["coverage_fraction"],
            "png_audit_status": audit["png_audit_status"],
        },
        "baseline_model_vs_actual": baseline_error,
        "counterfactual_contours": candidates,
        "evidence_limitations": [
            "All proposed contour pixels come from the OpenCV logical model, not the live game.",
            "This is a hypothetical union with a PREVIOUS live screenshot, not a replayed contour stroke.",
            "Painting cannot erase already-observed leakage under the additive union model.",
            "One-screen-pixel erosion/dilation is a sensitivity test, not a physical renderer confidence interval.",
            "No live run or run-bound pointCount was measured. Exact CHALK is not predicted.",
            "An observed baseline-model mismatch prevents acceptance of the contour model as a validated game renderer.",
        ],
        "measured_chalk_for_new_contour": None,
        "new_runtime_capture": False,
        "executor_ready": False,
    }
    return report, overlays


def save_screen_residual_report(
    results_root: str | Path,
    output_dir: str | Path,
    *,
    insets: tuple[int, ...] = CONTOUR_INSETS,
) -> Path:
    destination = Path(output_dir)
    if destination.exists():
        raise FileExistsError("Refusing to overwrite prior screen-residual diagnostics")
    report, overlays = analyze_committed_screen_residual(results_root, insets=insets)
    destination.mkdir(parents=True)
    for name, rgb in overlays.items():
        output = destination / (name + ".png")
        if not cv2.imwrite(str(output), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)):
            raise OSError("Failed to write " + str(output))
    path = destination / "screen_residual_comparison.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    path = save_screen_residual_report(args.results_root, args.output_dir)
    summary = json.loads(path.read_text(encoding="utf-8"))
    print(json.dumps({
        "experiment_id": summary["experiment_id"],
        "actual_uncovered_screen_pixels": summary["observed_actual_png"]["uncovered_target_screen_pixels"],
        "actual_leakage_screen_pixels": summary["observed_actual_png"]["leakage_screen_pixels"],
        "contour_insets": [x["inset_logical_px"] for x in summary["counterfactual_contours"]],
        "report": str(path),
        "status": summary["status"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

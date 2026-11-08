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
EDGE_PROFILE_ID = "FILL001_RIGHT_EDGE_SPATIAL_V1"
ENDPOINT_REPORT_GIT_SHA = "6d2fe33c98ada4899311613f173b00e4afdad424"
ENDPOINT_MONITOR_SHA = "8eb04ad7331d1e56f4aeb7d0f625c59c1dc57c24"
ENDPOINT_RUN_ID = "6a17a297-ea14-4527-9527-bfd8de3bd335"


def _read_pinned(
    path: Path, digest: str, *, git_json: bool = False
) -> bytes:
    """Check Git-tracked JSON on LF canonical bytes, but PNG on exact bytes.

    GitHub stores the evidence JSON with LF endings; a Windows checkout may
    materialize the same tracked file as CRLF. Mixed endings and any content
    change are rejected. PNG never receives any normalization.
    """
    if not path.is_file():
        raise FileNotFoundError("Required committed evidence missing: " + str(path))
    raw = path.read_bytes()
    checked = raw
    if git_json:
        checked = raw.replace(b"\r\n", b"\n")
        if raw != checked and raw != checked.replace(b"\n", b"\r\n"):
            raise ValueError("Mixed JSON line endings are not accepted: " + path.name)
    actual = hashlib.sha256(checked).hexdigest()
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
    if not insets or any(
        isinstance(inset, bool) or not isinstance(inset, int) or inset < 1
        for inset in insets
    ) or len(insets) != len(set(insets)):
        raise ValueError("Insets must be distinct positive integers")

    root = Path(results_root)
    before_path = root / (CAPTURE_BASE + "-before.png")
    after_path = root / (CAPTURE_BASE + "-after.png")
    attempt_path = root / "fill001" / "attempts" / (TASK_ID + ".json")
    plan_path = root / "fill001" / "plans" / (TASK_ID + ".json")

    before_raw = _read_pinned(before_path, EXPECTED_BEFORE_SHA256)
    after_raw = _read_pinned(after_path, EXPECTED_AFTER_SHA256)
    attempt_raw = _read_pinned(attempt_path, EXPECTED_ATTEMPT_SHA256, git_json=True)
    plan_raw = _read_pinned(plan_path, EXPECTED_PLAN_SHA256, git_json=True)
    attempt = json.loads(attempt_raw)
    plan = json.loads(plan_raw)
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
            "attempt_git_lf_canonical": EXPECTED_ATTEMPT_SHA256,
            "plan_git_lf_canonical": EXPECTED_PLAN_SHA256,
        },
        "checkout_json_sha256": {
            "attempt_raw": hashlib.sha256(attempt_raw).hexdigest(),
            "plan_raw": hashlib.sha256(plan_raw).hexdigest(),
        },
        "json_line_ending_policy": "Git LF canonical SHA-256; allow only all-LF or all-CRLF checkout bytes",
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


def _edge_profile_from_pinned_overlay(
    root: Path, rgb: np.ndarray,
) -> dict[str, Any]:
    """Distinct E2 spatial profile; no new calibration or new gameplay."""
    path = root / "fill001" / "endpoint-analysis-6a17a297.json"
    raw = path.read_bytes()
    canonical = raw.replace(b"\r\n", b"\n")
    if raw != canonical and raw != canonical.replace(b"\n", b"\r\n"):
        raise ValueError("Mixed endpoint JSON line endings")
    git_sha = hashlib.sha1(
        b"blob " + str(len(canonical)).encode("ascii") + b"\0" + canonical
    ).hexdigest()
    if git_sha != ENDPOINT_REPORT_GIT_SHA:
        raise ValueError("Endpoint Git blob SHA mismatch")
    endpoint = json.loads(canonical)
    if (
        endpoint.get("source", {}).get("run_id") != ENDPOINT_RUN_ID
        or endpoint.get("source", {}).get("blob_sha") != ENDPOINT_MONITOR_SHA
        or endpoint.get("exact_chalk", {}).get("consumed_points") != 1260
        or endpoint.get("exact_chalk", {}).get("pre_point_count") != 1
        or endpoint.get("exact_chalk", {}).get("post_point_count") != 1261
        or endpoint.get("capture_completeness", {}).get("accepted_point_coordinates") != 1260
        or endpoint.get("geometry", {}).get("stroke_count") != 27
        or len(endpoint.get("geometry", {}).get("per_stroke", [])) != 27
    ):
        raise ValueError("Endpoint run binding or exact CHALK mismatch")
    if rgb.shape != (304, 581, 3):
        raise ValueError("Screen residual overlay size mismatch")
    painted = np.all(rgb == (180, 180, 180), axis=2)
    missing = np.all(rgb == (220, 40, 45), axis=2)
    leaked = np.all(rgb == (155, 70, 205), axis=2)
    target = painted | missing
    if (
        int(target.sum()) != 71110
        or int(missing.sum()) != 1116
        or int(leaked.sum()) != 11
        or int(painted.sum()) != 69994
    ):
        raise ValueError("Pinned screen residual masks disagree with E4 PNG audit")
    source_x = np.clip(
        np.rint(np.arange(581) / ((581 - 1) / LOGICAL_BOARD_WIDTH)).astype(int),
        0, LOGICAL_BOARD_WIDTH - 1,
    )
    source_y = np.clip(
        np.rint(np.arange(304) / ((304 - 1) / LOGICAL_BOARD_HEIGHT)).astype(int),
        0, LOGICAL_BOARD_HEIGHT - 1,
    )
    zone_counts = _zones(missing, source_x, source_y)
    if zone_counts != {
        "top_y_lt_75": 244,
        "bottom_y_gt_165": 239,
        "left_middle_x_le_94": 134,
        "right_middle_x_ge_366": 499,
        "interior_or_other": 0,
    }:
        raise ValueError("Pinned regional miss counts disagree")
    rows = []
    for y, ly in enumerate(source_y):
        if not 75 <= ly <= 165:
            continue
        target_x = np.flatnonzero(target[y])
        paint_x = np.flatnonzero(painted[y])
        if not len(target_x) or not len(paint_x):
            raise ValueError("Unexpected empty middle screen row")
        rows.append({
            "screen_y": int(y), "logical_y_nearest": int(ly),
            "right_gap_px": int(target_x[-1] - paint_x[-1]),
            "left_gap_px": int(paint_x[0] - target_x[0]),
            "right_missing_px": int((missing[y] & (source_x >= 366)).sum()),
            "left_missing_px": int((missing[y] & (source_x <= 94)).sum()),
            "target_right_x": int(target_x[-1]),
            "painted_right_x": int(paint_x[-1]),
        })
    r = [x["right_gap_px"] for x in rows]
    l = [x["left_gap_px"] for x in rows]
    if (
        len(rows) != 114
        or sum(x["right_missing_px"] for x in rows) != 499
        or sum(x["left_missing_px"] for x in rows) != 134
        or any(x <= 0 for x in r)
    ):
        raise ValueError("Pinned right-edge streak count disagrees")
    strokes = []
    for i, s in enumerate(endpoint["geometry"]["per_stroke"]):
        first, last, terminal = (
            s["first_accepted_point"], s["last_accepted_point"],
            s["smooth_path_terminal_point"],
        )
        if (
            first["y"] != last["y"] or last["y"] != terminal["y"]
            or s["accepted_point_count"] < 2
            or not np.isclose(
                last["x"] - terminal["x"],
                s["last_accepted_segment_length"] / 2.0,
                atol=1e-6, rtol=0,
            )
        ):
            raise ValueError("Smooth endpoint does not match accepted points")
        strokes.append({
            "index": i + 1, "accepted_y": last["y"],
            "first_x": first["x"], "last_x": last["x"],
            "smooth_terminal_x": terminal["x"],
            "smooth_retreat_logical_px": last["x"] - terminal["x"],
        })
    return {
        "schema_version": 1,
        "experiment_id": EDGE_PROFILE_ID,
        "status": "DIAGNOSTIC_NOT_CAUSAL_NO_NEW_LIVE",
        "source_monitor_run": ENDPOINT_RUN_ID,
        "source_monitor_blob_sha": ENDPOINT_MONITOR_SHA,
        "source_endpoint_blob_sha": ENDPOINT_REPORT_GIT_SHA,
        "source_endpoint_sha256": hashlib.sha256(canonical).hexdigest(),
        "before_png_sha256": EXPECTED_BEFORE_SHA256,
        "after_png_sha256": EXPECTED_AFTER_SHA256,
        "plan_signature": EXPECTED_PLAN_SIGNATURE,
        "old_capture_exact_chalk": 1260,
        "uncovered_by_zone": zone_counts,
        "leakage_pixels": 11,
        "right_over_left_middle_misses": 499 / 134,
        "middle": {
            "screen_rows": len(rows),
            "rows_with_right_gap": sum(x > 0 for x in r),
            "right_gap_min_px": int(min(r)),
            "right_gap_median_px": float(np.median(r)),
            "right_gap_p90_px": float(np.percentile(r, 90)),
            "right_gap_max_px": int(max(r)),
            "left_gap_median_px": float(np.median(l)),
            "left_gap_max_px": int(max(l)),
        },
        "rows": rows,
        "raw_monitor_endpoint_summary": strokes,
        "limitations": [
            "No same-run native CSS/Stage screen transform in old FILL-001 evidence",
            "Saved before/after RGB delta threshold=8; not a live alpha or temporal replay",
            "Right-edge streak does not establish which engine/planner/executor stage caused it",
            "Existing FILL-001 acceptance FAIL and old CHALK 1260 remain unchanged",
        ],
    }


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
    edge = _edge_profile_from_pinned_overlay(Path(results_root), overlays["actual_residual"])
    destination.mkdir(parents=True)
    for name, rgb in overlays.items():
        output = destination / (name + ".png")
        if not cv2.imwrite(str(output), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)):
            raise OSError("Failed to write " + str(output))
    path = destination / "screen_residual_comparison.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (destination / (EDGE_PROFILE_ID + ".json")).write_text(
        json.dumps(edge, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
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

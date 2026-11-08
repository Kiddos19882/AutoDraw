from __future__ import annotations

"""FILL001_SMOOTH_AB_V1: isolated two-task experiment and screen-RGB comparison.

Reuses frozen FILL001_RS_V1 geometry, existing Stage6, Monitor, Bridge, and
the original PNG quality thresholds. No production drawing behavior is changed.
Historical V1 audits and all previous captures are immutable.
"""

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from chalk_fill_capture_adapter import (
    PNG_CHANGE_THRESHOLD, audit_fill001_png_pair,
)
from chalk_fill_experiment import build_fill_target_mask
from chalk_fill_fixed_radius_planner import build_fixed_radius_fill_plan
from chalk_fill_matrix import (
    FILL001_PHASE_ID, FILL001_RS_PLAN_VARIANT, FILL001_RS_SELECTION_POLICY,
    FillMatrixError, _hash, build_fill001_rs_matrix,
)

PROTOCOL = "FILL001_SMOOTH_AB_V1"
MODES = ((True, "on"), (False, "off"))
SHAPE = "rectangle"
RADIUS = 10
ROW_STEP = 5
ROW_OFFSET = 0
STROKES = 27
SAMPLING = {"profile_id": "P1", "sampling_step": 4, "delay_ms": 5}
IDENTITY_FIELDS = (
    "schema_version", "phase_id", "series_id", "shapes", "radii", "repeats",
    "tasks", "plan_variant", "candidate_selection_policy", "experiment_protocol",
)


def build_fill001_smooth_ab_matrix(series_id: str) -> dict[str, Any]:
    """Two tasks with an identical frozen plan, not a 45-cell production matrix."""
    baseline = build_fill001_rs_matrix(series_id)
    source = next(
        task for task in baseline["tasks"]
        if (task["shape_id"], task["requested_radius"], task["repeat_index"])
        == (SHAPE, RADIUS, 1)
    )
    tasks = []
    for index, (smooth, label) in enumerate(MODES, start=1):
        task = dict(source)
        task.update({
            "task_id": f"{series_id}-rectangle-r10-s5-o0-smooth-{label}",
            "matrix_order_index": index,
            "planned_repeats": 1,
            "experiment_protocol": PROTOCOL,
            "expected_smooth": smooth,
        })
        tasks.append(task)
    identity = {
        "schema_version": baseline["schema_version"],
        "phase_id": FILL001_PHASE_ID, "series_id": series_id,
        "shapes": [SHAPE], "radii": [RADIUS], "repeats": [1],
        "tasks": tasks, "plan_variant": FILL001_RS_PLAN_VARIANT,
        "candidate_selection_policy": FILL001_RS_SELECTION_POLICY,
        "experiment_protocol": PROTOCOL,
    }
    matrix = {
        **identity, "matrix_signature": _hash(identity),
        "expected_task_count": 2,
        "created_at_utc": baseline["created_at_utc"],
        "execution_allowed": False, "status": "planned",
    }
    validate_smooth_ab_matrix(matrix)
    return matrix


def validate_smooth_ab_matrix(matrix: Any) -> None:
    """Fail closed: no mixed, extra, duplicate, altered, or unbound test tasks."""
    if not isinstance(matrix, dict) or matrix.get("experiment_protocol") != PROTOCOL:
        raise FillMatrixError("Wrong smooth A/B protocol.")
    if (matrix.get("phase_id") != FILL001_PHASE_ID
            or matrix.get("plan_variant") != FILL001_RS_PLAN_VARIANT
            or matrix.get("candidate_selection_policy") != FILL001_RS_SELECTION_POLICY
            or matrix.get("shapes") != [SHAPE] or matrix.get("radii") != [RADIUS]
            or matrix.get("repeats") != [1]
            or matrix.get("expected_task_count") != 2
            or matrix.get("execution_allowed") is not False
            or matrix.get("status") not in ("planned", "in_progress")):
        raise FillMatrixError("Smooth A/B frozen matrix fields disagree.")
    series = matrix.get("series_id")
    if (not isinstance(series, str) or not 1 <= len(series) <= 64
            or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
                   for ch in series) or not series[0].isalnum()):
        raise FillMatrixError("Invalid smooth A/B series_id.")
    tasks = matrix.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 2:
        raise FillMatrixError("Smooth A/B requires exactly two ordered tasks.")
    frozen = build_fixed_radius_fill_plan(
        SHAPE, RADIUS, scanline_row_step=ROW_STEP, scanline_offset=ROW_OFFSET
    )
    summary = frozen["summary"]
    if summary["stroke_count"] != STROKES or summary["quality_gate_passed"] is not True:
        raise FillMatrixError("Frozen 27-stroke RS plan unexpectedly changed.")
    seen = set()
    for index, (mode, label) in enumerate(MODES, start=1):
        task = tasks[index - 1]
        expected_id = f"{series}-rectangle-r10-s5-o0-smooth-{label}"
        if not isinstance(task, dict) or task.get("expected_smooth") is not mode:
            raise FillMatrixError("Smooth A/B mode missing, swapped or mixed.")
        checks = {
            "task_id": expected_id, "matrix_order_index": index,
            "phase_id": FILL001_PHASE_ID, "series_id": series,
            "shape_id": SHAPE, "requested_radius": RADIUS, "repeat_index": 1,
            "planned_repeats": 1, "plan_variant": FILL001_RS_PLAN_VARIANT,
            "planner_version": frozen["planner_version"],
            "scanline_row_step": ROW_STEP, "scanline_offset": ROW_OFFSET,
            "plan_signature": frozen["plan_signature"],
            "target_mask_sha256": frozen["target_mask_sha256"],
            "expected_strokes": STROKES,
            "planned_path_length": summary["path_length_logical_pixels"],
            "planned_coverage_fraction": summary["coverage_fraction"],
            "planned_leakage_pixels": 0,
            "quality_gate_passed": True, "unsupported": False,
            "sampling_profile": SAMPLING, "safe_to_execute": False,
            "experiment_protocol": PROTOCOL,
        }
        if any(task.get(key) != value for key, value in checks.items()):
            raise FillMatrixError("Smooth A/B task differs from frozen RS geometry/parameters.")
        if (task.get("capture_status") not in ("pending", "completed", "failed")
                or task["task_id"] in seen):
            raise FillMatrixError("Smooth A/B task state or identity invalid.")
        seen.add(task["task_id"])
    identity = {key: matrix[key] for key in IDENTITY_FIELDS}
    if matrix.get("matrix_signature") != _hash(identity):
        raise FillMatrixError("Smooth A/B manifest signature mismatch.")


def _screen_residual(before_png: str, after_png: str, png: dict) -> dict[str, Any]:
    """Exactly the FILL-001 nearest-neighbor mask + RGB threshold, with regions."""
    with Image.open(before_png) as image:
        before = np.asarray(image.convert("RGB"), dtype=np.int16)
    with Image.open(after_png) as image:
        after = np.asarray(image.convert("RGB"), dtype=np.int16)
    height, width = before.shape[:2]
    if before.shape != after.shape or width < 2 or height < 2:
        raise FillMatrixError("Incompatible A/B screenshot pair.")
    source_x = np.clip(np.rint(np.arange(width) * 460.0 / (width - 1)).astype(int), 0, 459)
    source_y = np.clip(np.rint(np.arange(height) * 240.0 / (height - 1)).astype(int), 0, 239)
    mask = build_fill_target_mask(SHAPE)[np.ix_(source_y, source_x)]
    changed = np.any(np.abs(after - before) > PNG_CHANGE_THRESHOLD, axis=2)
    missed = mask & ~changed
    leaked = ~mask & changed
    if (int(missed.sum()) != png["target_pixels"] - round(png["coverage_fraction"] * png["target_pixels"])
            or int(leaked.sum()) != png["leakage_pixels"]):
        raise FillMatrixError("Spatial metrics disagree with frozen FILL-001 PNG audit.")
    logical_y = np.arange(height) * 240.0 / (height - 1)
    middle_rows = (logical_y >= 80) & (logical_y < 160)
    right_gaps, left_gaps = [], []
    for y in np.flatnonzero(middle_rows):
        xs = np.flatnonzero(mask[y])
        if len(xs) == 0:
            continue
        left, right = int(xs[0]), int(xs[-1])
        rgap = lgap = 0
        while right - rgap >= left and missed[y, right - rgap]:
            rgap += 1
        while left + lgap <= right and missed[y, left + lgap]:
            lgap += 1
        right_gaps.append(rgap)
        left_gaps.append(lgap)
    leaks_by_row = leaked.sum(axis=1)
    top_leak_rows = sorted(
        ((int(y), int(v)) for y, v in enumerate(leaks_by_row) if v > 0),
        key=lambda item: (-item[1], item[0]),
    )[:10]
    return {
        "uncovered_pixels": int(missed.sum()),
        "leakage_pixels": int(leaked.sum()),
        "middle_row_count": len(right_gaps),
        "right_middle_miss_pixels": int(sum(right_gaps)),
        "left_middle_miss_pixels": int(sum(left_gaps)),
        "right_middle_gap_median_px": float(np.median(right_gaps)) if right_gaps else None,
        "left_middle_gap_median_px": float(np.median(left_gaps)) if left_gaps else None,
        "right_rows_with_gap": int(sum(value > 0 for value in right_gaps)),
        "leakage_top_rows": top_leak_rows,
    }


def analyze_smooth_ab_pair(matrix: dict, evidence: list[dict]) -> dict[str, Any]:
    """A/B E4 provenance and screen-RGB comparison. No quality-gate override."""
    validate_smooth_ab_matrix(matrix)
    if not isinstance(evidence, list) or len(evidence) != 2:
        raise FillMatrixError("Exactly two A/B evidence reports are required.")
    ordered = {item.get("task_id"): item for item in evidence if isinstance(item, dict)}
    if len(ordered) != 2:
        raise FillMatrixError("Missing or duplicate A/B task evidence.")
    rows = []
    for task in matrix["tasks"]:
        item = ordered.get(task["task_id"])
        if (not isinstance(item, dict) or item.get("protocol") != PROTOCOL
                or item.get("expected_smooth") is not task["expected_smooth"]
                or item.get("raw_e4_status") != "PASS_E4_RAW_CAPTURE"
                or item.get("plan_signature") != task["plan_signature"]
                or item.get("target_mask_sha256") != task["target_mask_sha256"]
                or not isinstance(item.get("run_id"), str) or not item["run_id"]
                or type(item.get("exact_chalk")) is not int or item["exact_chalk"] <= 0
                or not isinstance(item.get("renderer_geometry_sha256"), str)
                or len(item["renderer_geometry_sha256"]) != 64
                or item.get("screen_roi") is None):
            raise FillMatrixError("A/B evidence not valid or not bound to declared mode.")
        png = audit_fill001_png_pair(
            SHAPE, item["before_png"], item["after_png"], screen_roi=item["screen_roi"]
        )
        if (png["before_png_sha256"] != item["before_png_sha256"]
                or png["after_png_sha256"] != item["after_png_sha256"]
                or png["coverage_fraction"] != item["png_audit"]["coverage_fraction"]
                or png["leakage_pixels"] != item["png_audit"]["leakage_pixels"]):
            raise FillMatrixError("A/B PNG hashes or independent audit disagree.")
        rows.append({
            "task_id": task["task_id"], "run_id": item["run_id"],
            "session_id": item.get("session_id"),
            "smooth": task["expected_smooth"],
            "exact_chalk": item["exact_chalk"],
            "screen_roi": item["screen_roi"],
            "renderer_geometry_sha256": item["renderer_geometry_sha256"],
            "before_sha256": png["before_png_sha256"],
            "after_sha256": png["after_png_sha256"],
            "coverage_fraction": png["coverage_fraction"],
            "leakage_pixels": png["leakage_pixels"],
            "png_quality_gate": "PASS" if png["png_audit_status"] == "passed" else "FAIL",
            "spatial": _screen_residual(item["before_png"], item["after_png"], png),
        })
    on, off = rows
    if on["run_id"] == off["run_id"]:
        raise FillMatrixError("A/B requires two distinct Game Monitor runs.")
    compatible = (on["screen_roi"] == off["screen_roi"]
                  and on["renderer_geometry_sha256"] == off["renderer_geometry_sha256"]
                  and on["before_sha256"] == off["before_sha256"])
    return {
        "schema_version": 1, "protocol": PROTOCOL,
        "series_id": matrix["series_id"], "matrix_signature": matrix["matrix_signature"],
        "status": "ANALYZED_COMPARABLE" if compatible else "PARTIAL_BASELINE_ROI_OR_GEOMETRY_MISMATCH",
        "conditions": rows,
        "off_minus_on": {
            "exact_chalk": off["exact_chalk"] - on["exact_chalk"],
            "coverage_percentage_points": 100.0 * (
                off["coverage_fraction"] - on["coverage_fraction"]),
            "leakage_pixels": off["leakage_pixels"] - on["leakage_pixels"],
            "uncovered_pixels": (off["spatial"]["uncovered_pixels"]
                                 - on["spatial"]["uncovered_pixels"]),
            "right_middle_miss_pixels": (
                off["spatial"]["right_middle_miss_pixels"]
                - on["spatial"]["right_middle_miss_pixels"]),
        } if compatible else None,
        "limitations": [
            "The game smoothing toggle is operator-controlled; actual modes are verified from raw ENTER_FRAME telemetry.",
            "Stage/client-to-desktop projection is not independently proven by equal screen ROI alone.",
            "Two consecutive runs are exploratory, not independent proof of causality or a general model.",
            "RGB screenshot comparison cannot recover native alpha or full temporal render order.",
            "PNG quality remains >=99% coverage AND zero leakage for each run.",
        ],
    }

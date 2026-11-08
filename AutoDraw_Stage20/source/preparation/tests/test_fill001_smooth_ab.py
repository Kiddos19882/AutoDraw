from __future__ import annotations

import copy
import hashlib
import json

import numpy as np
from PIL import Image
import pytest

from chalk_fill_matrix import (
    FillMatrixError, _hash, load_fill001_matrix, write_fill001_matrix,
    build_fill001_rs_matrix,
)
from chalk_fill_execution import prepare_fill001_single_task_plan
from chalk_fill_capture_adapter import audit_fill001_png_pair
from chalk_fill_experiment import build_fill_target_mask
from fill001_smooth_ab import (
    PROTOCOL, build_fill001_smooth_ab_matrix, validate_smooth_ab_matrix,
    analyze_smooth_ab_pair,
)


def test_ab_matrix_is_two_separate_mode_locked_tasks_and_old_matrix_unchanged(tmp_path):
    matrix = build_fill001_smooth_ab_matrix("fill001-ab-new")
    assert len(matrix["tasks"]) == 2
    assert matrix["expected_task_count"] == 2
    assert matrix["execution_allowed"] is False
    assert [t["expected_smooth"] for t in matrix["tasks"]] == [True, False]
    assert len({t["task_id"] for t in matrix["tasks"]}) == 2
    assert len({t["plan_signature"] for t in matrix["tasks"]}) == 1
    assert {t["expected_strokes"] for t in matrix["tasks"]} == {27}
    assert {t["scanline_row_step"] for t in matrix["tasks"]} == {5}
    path = write_fill001_matrix(matrix, tmp_path / "new_ab.json")
    assert load_fill001_matrix(path) == matrix
    plans = [
        prepare_fill001_single_task_plan(
            matrix, task["task_id"], operator_approved_single_task_preflight=True
        )[0]
        for task in matrix["tasks"]
    ]
    assert [s["points"] for s in plans[0]["strokes"]] == [
        s["points"] for s in plans[1]["strokes"]
    ]
    assert plans[0]["generation"]["sampling_profile"] == {
        "profile_id": "P1", "sampling_step": 4, "delay_ms": 5
    }
    assert all(p["generation"]["matrix_batch_execution_allowed"] is False for p in plans)

    historical = build_fill001_rs_matrix("old-independent-series")
    assert len(historical["tasks"]) == 45
    assert "experiment_protocol" not in historical


def test_ab_matrix_rejects_renamed_mode_and_recomputed_signature():
    base = build_fill001_smooth_ab_matrix("smooth-ab-guard")
    for mutation in (
        lambda m: m["tasks"][1].update(expected_smooth=True),
        lambda m: m["tasks"][0].update(plan_signature="0" * 64),
        lambda m: m.update(execution_allowed=True),
        lambda m: m["tasks"].append(copy.deepcopy(m["tasks"][1])),
    ):
        other = copy.deepcopy(base)
        mutation(other)
        identity_keys = (
            "schema_version", "phase_id", "series_id", "shapes", "radii",
            "repeats", "tasks", "plan_variant", "candidate_selection_policy",
            "experiment_protocol",
        )
        other["matrix_signature"] = _hash({
            key: other[key] for key in identity_keys
        })
        with pytest.raises(FillMatrixError):
            validate_smooth_ab_matrix(other)


def _screen_mask():
    logical = build_fill_target_mask("rectangle")
    sx = np.clip(np.rint(np.arange(461) * 460.0 / 460).astype(int), 0, 459)
    sy = np.clip(np.rint(np.arange(241) * 240.0 / 240).astype(int), 0, 239)
    return logical[np.ix_(sy, sx)]


def _capture(path, draw, *, leak=False):
    image = np.full((241, 461, 3), 255, dtype=np.uint8)
    if draw:
        image[_screen_mask()] = 0
        if leak:
            image[0, 0] = 0
    Image.fromarray(image, "RGB").save(path)


def _evidence(task, run_id, before, after, chalk):
    png = audit_fill001_png_pair(
        "rectangle", before, after,
        screen_roi={"x": 0, "y": 0, "width": 461, "height": 241},
    )
    return {
        "protocol": PROTOCOL, "task_id": task["task_id"],
        "expected_smooth": task["expected_smooth"],
        "raw_e4_status": "PASS_E4_RAW_CAPTURE",
        "run_id": run_id, "session_id": "session-" + run_id,
        "exact_chalk": chalk, "plan_signature": task["plan_signature"],
        "target_mask_sha256": task["target_mask_sha256"],
        "raw_run_sha256": hashlib.sha256(run_id.encode()).hexdigest(),
        "renderer_geometry_sha256": "a" * 64,
        "screen_roi": {"x": 0, "y": 0, "width": 461, "height": 241},
        "before_png": str(before), "after_png": str(after),
        "before_png_sha256": png["before_png_sha256"],
        "after_png_sha256": png["after_png_sha256"],
        "png_audit": png,
    }


def test_ab_pair_retains_separate_quality_fails_and_spatial_delta(tmp_path):
    m = build_fill001_smooth_ab_matrix("smooth-ab-compare")
    before_on, before_off = tmp_path / "before-on.png", tmp_path / "before-off.png"
    after_on, after_off = tmp_path / "after-on.png", tmp_path / "after-off.png"
    _capture(before_on, False)
    _capture(before_off, False)
    _capture(after_on, True)
    _capture(after_off, True, leak=True)
    # Remove three pixels at the mask's right edge for a middle row.
    image = np.asarray(Image.open(after_off).convert("RGB")).copy()
    mask = _screen_mask()
    row = 120
    last = int(np.flatnonzero(mask[row])[-1])
    image[row, last - 2:last + 1] = 255
    Image.fromarray(image, "RGB").save(after_off)
    reports = [
        _evidence(m["tasks"][0], "run-on", before_on, after_on, 1455),
        _evidence(m["tasks"][1], "run-off", before_off, after_off, 1459),
    ]
    result = analyze_smooth_ab_pair(m, reports)
    assert result["status"] == "ANALYZED_COMPARABLE"
    assert result["off_minus_on"]["exact_chalk"] == 4
    assert result["off_minus_on"]["right_middle_miss_pixels"] == 3
    assert result["conditions"][0]["png_quality_gate"] == "PASS"
    assert result["conditions"][1]["png_quality_gate"] == "FAIL"
    assert result["conditions"][1]["leakage_pixels"] == 1

    modified = copy.deepcopy(reports)
    modified[1]["expected_smooth"] = True
    with pytest.raises(FillMatrixError, match="declared mode"):
        analyze_smooth_ab_pair(m, modified)
    modified = copy.deepcopy(reports)
    modified[1]["run_id"] = "run-on"
    with pytest.raises(FillMatrixError, match="distinct"):
        analyze_smooth_ab_pair(m, modified)
    modified = copy.deepcopy(reports)
    modified[1]["before_png_sha256"] = "0" * 64
    with pytest.raises(FillMatrixError, match="hashes"):
        analyze_smooth_ab_pair(m, modified)


def test_ab_refuses_to_compare_different_blank_board_images(tmp_path):
    m = build_fill001_smooth_ab_matrix("smooth-ab-baseline")
    before_on, before_off = tmp_path / "before-on.png", tmp_path / "before-off.png"
    after_on, after_off = tmp_path / "after-on.png", tmp_path / "after-off.png"
    _capture(before_on, False)
    _capture(before_off, False)
    image = np.asarray(Image.open(before_off).convert("RGB")).copy()
    image[0, 0] = 200
    Image.fromarray(image, "RGB").save(before_off)
    _capture(after_on, True)
    _capture(after_off, True)
    evidence = [
        _evidence(m["tasks"][0], "run-on", before_on, after_on, 1455),
        _evidence(m["tasks"][1], "run-off", before_off, after_off, 1459),
    ]
    comparison = analyze_smooth_ab_pair(m, evidence)
    assert comparison["status"] == "PARTIAL_BASELINE_ROI_OR_GEOMETRY_MISMATCH"
    assert comparison["off_minus_on"] is None
    # Same-looking blank screenshots are insufficient with changed BoardPane mapping.
    _capture(before_off, False)
    compatible_before = [
        _evidence(m["tasks"][0], "run-on", before_on, after_on, 1455),
        _evidence(m["tasks"][1], "run-off", before_off, after_off, 1459),
    ]
    compatible_before[1]["renderer_geometry_sha256"] = "b" * 64
    changed_geometry = analyze_smooth_ab_pair(m, compatible_before)
    assert changed_geometry["status"] == "PARTIAL_BASELINE_ROI_OR_GEOMETRY_MISMATCH"
    assert changed_geometry["off_minus_on"] is None

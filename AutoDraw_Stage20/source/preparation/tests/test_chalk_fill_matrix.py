from __future__ import annotations

import copy
import json

import pytest

from chalk_fill_matrix import (
    FILL001_TASK_COUNT,
    FillMatrixError,
    analyze_fill001_captures,
    build_fill001_matrix,
    load_fill001_matrix,
    validate_fill001_capture,
    validate_fill001_matrix,
    write_fill001_matrix,
)


@pytest.fixture(scope="module")
def matrix():
    return build_fill001_matrix("FILL001-REGRESSION")


def _capture(task):
    return {
        "task_id": task["task_id"],
        "run_id": f"run-{task['matrix_order_index']}",
        "plan_signature": task["plan_signature"],
        "target_mask_sha256": task["target_mask_sha256"],
        "requested_radius": task["requested_radius"],
        "observed_radius": task["requested_radius"],
        "pre_point_count": 1000,
        "post_point_count": 1100,
        "exact_chalk": 100,
        "coverage_fraction": 0.995,
        "leakage_pixels": 0,
        "completed_strokes": task["expected_strokes"],
        "expected_strokes": task["expected_strokes"],
        "dropped_events": 0,
        "monitor_errors": 0,
        "bridge_failures": 0,
        "sequence_gaps": 0,
    }


def test_matrix_contains_exactly_45_unique_cells_and_is_deterministic(matrix):
    assert len(matrix["tasks"]) == FILL001_TASK_COUNT == 45
    validate_fill001_matrix(matrix)
    second = build_fill001_matrix("FILL001-REGRESSION")
    assert matrix["matrix_signature"] == second["matrix_signature"]
    assert len({task["task_id"] for task in matrix["tasks"]}) == 45


def test_every_task_has_dynamic_stroke_count_mask_and_plan_identity(matrix):
    for task in matrix["tasks"]:
        assert task["expected_strokes"] > 0
        assert task["target_area_pixels"] > 0
        assert len(task["plan_signature"]) == 64
        assert len(task["target_mask_sha256"]) == 64
        assert task["safe_to_execute"] is False


def test_matrix_rejects_duplicate_or_missing_cell(matrix):
    altered = copy.deepcopy(matrix)
    altered["tasks"][1]["task_id"] = altered["tasks"][0]["task_id"]
    with pytest.raises(FillMatrixError):
        validate_fill001_matrix(altered)
    altered = copy.deepcopy(matrix)
    altered["tasks"].pop()
    with pytest.raises(FillMatrixError):
        validate_fill001_matrix(altered)


def test_matrix_rejects_signature_tampering_and_unsupported_cell(matrix):
    altered = copy.deepcopy(matrix)
    altered["tasks"][0]["requested_radius"] = 30
    with pytest.raises(FillMatrixError):
        validate_fill001_matrix(altered)
    altered = copy.deepcopy(matrix)
    altered["tasks"][0]["quality_gate_passed"] = False
    with pytest.raises(FillMatrixError):
        validate_fill001_matrix(altered)


def test_manifest_round_trip_is_atomic_and_validated(matrix, tmp_path):
    path = write_fill001_matrix(matrix, tmp_path / "fill001.json")
    loaded = load_fill001_matrix(path)
    assert loaded["matrix_signature"] == matrix["matrix_signature"]
    assert not (tmp_path / "fill001.json.tmp").exists()


def test_capture_acceptance_checks_exact_chalk_and_quality(matrix):
    task = matrix["tasks"][0]
    accepted = validate_fill001_capture(task, _capture(task))
    assert accepted["status"] == "accepted"
    invalid = _capture(task)
    invalid["post_point_count"] += 1
    with pytest.raises(FillMatrixError):
        validate_fill001_capture(task, invalid)
    invalid = _capture(task)
    invalid["observed_radius"] += 1
    with pytest.raises(FillMatrixError):
        validate_fill001_capture(task, invalid)
    invalid = _capture(task)
    invalid["coverage_fraction"] = 0.98
    with pytest.raises(FillMatrixError):
        validate_fill001_capture(task, invalid)


def test_analyzer_accepts_complete_45_capture_journal(matrix):
    captures = [_capture(task) for task in matrix["tasks"]]
    report = analyze_fill001_captures(matrix, captures)
    assert report["status"] == "complete"
    assert report["accepted_count"] == 45
    assert len(report["groups"]) == 15
    assert all(group["accepted_repeats"] == 3 for group in report["groups"])
    assert all(group["target_area_pixels"] > 0 for group in report["groups"])
    assert report["safety_margin_status"] == "not_established"


def test_analyzer_fails_closed_on_missing_duplicate_and_bad_capture(matrix):
    captures = [_capture(task) for task in matrix["tasks"]]
    captures.pop()
    report = analyze_fill001_captures(matrix, captures)
    assert report["status"] == "incomplete"
    assert report["accepted_count"] == 44
    assert len(report["missing_task_ids"]) == 1

    captures = [_capture(task) for task in matrix["tasks"]]
    captures.append(copy.deepcopy(captures[0]))
    report = analyze_fill001_captures(matrix, captures)
    assert report["status"] == "incomplete"
    assert report["rejected"][0]["reason"] == "duplicate_capture"

    captures = [_capture(task) for task in matrix["tasks"]]
    captures[0]["dropped_events"] = 1
    report = analyze_fill001_captures(matrix, captures)
    assert report["status"] == "incomplete"
    assert report["accepted_count"] == 44


def test_analyzer_rejects_reused_run_identity(matrix):
    captures = [_capture(task) for task in matrix["tasks"]]
    captures[1]["run_id"] = captures[0]["run_id"]
    report = analyze_fill001_captures(matrix, captures)
    assert report["status"] == "incomplete"
    assert any(item["reason"] == "duplicate_run_id" for item in report["rejected"])

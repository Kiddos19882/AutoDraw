from __future__ import annotations

from copy import deepcopy

import pytest

from chalk_fill_matrix import FillMatrixError, validate_fill001_matrix
from fill001_smooth_ab_v3 import (
    COORDINATE_PREFLIGHT, PROTOCOL, build_fill001_smooth_ab_v3_matrix,
    validate_smooth_ab_v3_matrix,
)


def test_v3_is_frozen_27_stroke_new_series_and_versioned_preflight():
    series = build_fill001_smooth_ab_v3_matrix("v3-safe-probe-001")
    assert series["experiment_protocol"] == PROTOCOL
    assert series["coordinate_preflight_protocol"] == COORDINATE_PREFLIGHT
    assert series["execution_allowed"] is False
    assert [t["expected_smooth"] for t in series["tasks"]] == [True, False]
    assert all(t["coordinate_preflight_protocol"] == COORDINATE_PREFLIGHT
               and t["expected_strokes"] == 27 and t["safe_to_execute"] is False
               and t["task_id"].find("-v3-smooth-") > 0 for t in series["tasks"])
    assert len({t["plan_signature"] for t in series["tasks"]}) == 1
    validate_fill001_matrix(series)
    assert series["matrix_signature"] != build_fill001_smooth_ab_v3_matrix("other-v3")["matrix_signature"]


def test_v3_rejects_mixed_coordinates_protocol_and_tampering():
    original = build_fill001_smooth_ab_v3_matrix("v3-proof")
    for field, bad in (
        ("experiment_protocol", "FILL001_SMOOTH_AB_V2"),
        ("coordinate_preflight_protocol", "legacy_roi"),
        ("matrix_signature", "0"*64),
    ):
        mutated = deepcopy(original)
        mutated[field] = bad
        with pytest.raises(FillMatrixError):
            validate_smooth_ab_v3_matrix(mutated)
    mutated = deepcopy(original)
    mutated["tasks"][1]["task_id"] = "legacy-task"
    with pytest.raises(FillMatrixError):
        validate_smooth_ab_v3_matrix(mutated)


def test_v3_rejects_old_v2_manifest_without_new_identity():
    from fill001_smooth_ab_v2 import build_fill001_smooth_ab_v2_matrix
    old = build_fill001_smooth_ab_v2_matrix("old-v2")
    with pytest.raises(FillMatrixError):
        validate_smooth_ab_v3_matrix(old)


def _v3_result(task, run_id):
    return {
        "protocol": PROTOCOL,
        "task_id": task["task_id"], "expected_smooth": task["expected_smooth"],
        "screen_mask_version": "FILL001_SCREEN_MASK_V2",
        "raw_e4_status": "PASS_E4_RAW_CAPTURE",
        "run_id": run_id, "session_id": "same-session", "exact_chalk": 1458,
        "renderer_geometry_sha256": "g"*64,
        "screen_roi": {"x":496,"y":265,"width":674,"height":355},
        "before_png": task["task_id"]+"-before.png",
        "after_png": task["task_id"]+"-after.png",
        "before_png_sha256": "a"*64, "after_png_sha256": run_id+"a"*32,
        "raw_run_sha256": "b"*64,
        "boardpane_preflight": {
            "schema": COORDINATE_PREFLIGHT, "session_id": "same-session",
            "renderer_geometry_sha256": "g"*64,
            "screen_roi": {"x":496,"y":265,"width":674,"height":355},
        },
        "v2_audit": {
            "schema": "FILL001_SCREEN_MASK_V2", "run_id": run_id,
            "acceptance_override": False,
            "frozen_target_mask_sha256": task["target_mask_sha256"],
            "before_png_sha256": "a"*64,
            "after_png_sha256": run_id+"a"*32,
            "geometry_evidence_sha256": "b"*64,
            "coverage_fraction": .993, "leakage_pixels": 100,
        },
        "v2_binding_provenance": {"raw_run_sha256": "b"*64},
    }


def test_v3_pair_accepts_only_matching_protocol_and_coordinate_provenance():
    from fill001_smooth_ab_v3 import analyze_smooth_ab_v3_pair
    matrix = build_fill001_smooth_ab_v3_matrix("v3-compare")
    rows = [_v3_result(matrix["tasks"][0], "run-on"),
            _v3_result(matrix["tasks"][1], "run-off")]
    report = analyze_smooth_ab_v3_pair(matrix, rows)
    assert report["status"] == "ANALYZED_COMPARABLE"
    assert report["acceptance_override"] is False
    damaged = deepcopy(rows)
    damaged[1]["boardpane_preflight"]["session_id"] = "another-session"
    with pytest.raises(FillMatrixError):
        analyze_smooth_ab_v3_pair(matrix, damaged)
    damaged = deepcopy(rows)
    damaged[1]["run_id"] = damaged[0]["run_id"]
    with pytest.raises(FillMatrixError):
        analyze_smooth_ab_v3_pair(matrix, damaged)
    damaged = deepcopy(rows)
    damaged[1]["screen_roi"]["x"] += 1
    assert analyze_smooth_ab_v3_pair(matrix, damaged)["status"].startswith("PARTIAL")

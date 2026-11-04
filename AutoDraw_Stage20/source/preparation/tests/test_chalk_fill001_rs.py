from __future__ import annotations

import copy

import pytest

from chalk_fill_execution import prepare_fill001_single_task_plan
from chalk_fill_matrix import (
    FILL001_RS_PLAN_VARIANT,
    FILL001_RS_SCANLINE_CONFIGS,
    FILL001_TASK_COUNT,
    FillMatrixError,
    build_fill001_matrix,
    build_fill001_rs_matrix,
    validate_fill001_matrix,
)


def test_rs_matrix_is_separate_versioned_45_task_manifest():
    matrix = build_fill001_rs_matrix("fill001-rs-regression")

    assert len(matrix["tasks"]) == FILL001_TASK_COUNT == 45
    assert matrix["plan_variant"] == FILL001_RS_PLAN_VARIANT
    assert matrix["execution_allowed"] is False
    validate_fill001_matrix(matrix)
    for task in matrix["tasks"]:
        key = (task["shape_id"], task["requested_radius"])
        assert (task["scanline_row_step"], task["scanline_offset"]) == FILL001_RS_SCANLINE_CONFIGS[key]
        assert task["plan_variant"] == FILL001_RS_PLAN_VARIANT
        assert task["planner_version"] in {1, 2}
        assert task["safe_to_execute"] is False
        assert task["quality_gate_passed"] is True
        assert task["planned_coverage_fraction"] >= 0.99
        assert task["planned_leakage_pixels"] == 0


def test_rs_matrix_rejects_tampered_spacing_and_selection_policy():
    matrix = build_fill001_rs_matrix("fill001-rs-signature")
    altered = copy.deepcopy(matrix)
    altered["tasks"][0]["scanline_offset"] = 1
    with pytest.raises(FillMatrixError):
        validate_fill001_matrix(altered)

    altered = copy.deepcopy(matrix)
    altered["candidate_selection_policy"] = "changed"
    with pytest.raises(FillMatrixError):
        validate_fill001_matrix(altered)


def test_legacy_matrix_keeps_its_original_plan_contract():
    matrix = build_fill001_matrix("FILL001-LEGACY-CONTRACT")

    assert "plan_variant" not in matrix
    assert all("scanline_row_step" not in task for task in matrix["tasks"])
    validate_fill001_matrix(matrix)


def test_single_task_handoff_preserves_rs_scanline_spacing():
    matrix = build_fill001_rs_matrix("fill001-rs-execution")
    task = next(
        item for item in matrix["tasks"]
        if item["shape_id"] == "rectangle"
        and item["requested_radius"] == 10
        and item["repeat_index"] == 1
    )

    plan, selected = prepare_fill001_single_task_plan(
        matrix,
        task["task_id"],
        operator_approved_single_task_preflight=True,
    )

    assert selected == task
    assert len(plan["strokes"]) == 27
    assert plan["generation"]["planner_version"] == 2
    assert plan["generation"]["plan_variant"] == FILL001_RS_PLAN_VARIANT
    assert plan["generation"]["scanline_spacing"] == {
        "scanline_row_step": 5,
        "scanline_offset": 0,
    }
    assert plan["generation"]["matrix_batch_execution_allowed"] is False
    assert matrix["execution_allowed"] is False

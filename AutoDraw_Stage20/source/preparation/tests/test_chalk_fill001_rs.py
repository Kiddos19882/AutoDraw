from __future__ import annotations

import copy

import pytest

from chalk_fill_execution import prepare_fill001_single_task_plan
from chalk_fill_runtime_binding import build_fill001_experiment_context
from chalk_fill_experiment import FILL001_RADII, FILL001_SHAPES
from chalk_fill_fixed_radius_planner import build_fixed_radius_fill_plan
from chalk_fill_matrix import (
    FILL001_RS_PLAN_VARIANT,
    FILL001_RS_SCANLINE_CONFIGS,
    FILL001_TASK_COUNT,
    FillMatrixError,
    build_fill001_matrix,
    build_fill001_rs_matrix,
    load_fill001_matrix,
    validate_fill001_matrix,
    write_fill001_matrix,
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


def test_rs_runtime_context_binds_spacing_parameters():
    matrix = build_fill001_rs_matrix("fill001-rs-context")
    task = next(
        item for item in matrix["tasks"]
        if item["shape_id"] == "rectangle"
        and item["requested_radius"] == 10
        and item["repeat_index"] == 1
    )
    context = build_fill001_experiment_context(task)
    assert context["plan_variant"] == FILL001_RS_PLAN_VARIANT
    assert context["planner_version"] == 2
    assert context["scanline_row_step"] == 5
    assert context["scanline_offset"] == 0


def test_rs_runtime_context_rejects_invalid_spacing():
    matrix = build_fill001_rs_matrix("fill001-rs-invalid-context")
    task = next(
        item for item in matrix["tasks"]
        if item["shape_id"] == "rectangle"
        and item["requested_radius"] == 10
        and item["repeat_index"] == 1
    )
    task["scanline_offset"] = task["scanline_row_step"]
    with pytest.raises(FillMatrixError):
        build_fill001_experiment_context(task)


def test_frozen_rs_spacing_map_matches_exhaustive_static_sweep():
    observed = {}
    candidate_count = 0
    accepted_count = 0

    for shape in FILL001_SHAPES:
        for radius in FILL001_RADII:
            candidates = []
            for step in range(1, radius + 1):
                for offset in range(step):
                    candidate_count += 1
                    plan = build_fixed_radius_fill_plan(
                        shape,
                        radius,
                        scanline_row_step=step,
                        scanline_offset=offset,
                    )
                    summary = plan["summary"]
                    if summary["coverage_fraction"] >= 0.99 and summary["leakage_pixels"] == 0:
                        accepted_count += 1
                        candidates.append({
                            "step": step,
                            "offset": offset,
                            "coverage": summary["coverage_fraction"],
                            "estimated_points": summary["estimated_sampling_points"],
                            "path": summary["path_length_logical_pixels"],
                            "strokes": summary["stroke_count"],
                        })
            assert candidates, f"No accepted static candidate for {shape}/r{radius}"
            max_step = max(item["step"] for item in candidates)
            finalists = [item for item in candidates if item["step"] == max_step]
            best = max(
                finalists,
                key=lambda item: (
                    item["coverage"],
                    -item["estimated_points"],
                    -item["path"],
                    -item["strokes"],
                ),
            )
            observed[(shape, radius)] = (best["step"], best["offset"])

    assert candidate_count == 2238
    assert accepted_count == 62
    assert observed == FILL001_RS_SCANLINE_CONFIGS


def test_legacy_single_task_handoff_keeps_legacy_generation_metadata():
    matrix = build_fill001_matrix("FILL001-LEGACY-HANDOFF")
    task = next(
        item for item in matrix["tasks"]
        if item["shape_id"] == "rectangle"
        and item["requested_radius"] == 10
        and item["repeat_index"] == 1
    )
    plan, _ = prepare_fill001_single_task_plan(
        matrix,
        task["task_id"],
        operator_approved_single_task_preflight=True,
    )
    assert plan["generation"]["planner_version"] == 1
    assert "plan_variant" not in plan["generation"]
    assert "scanline_spacing" not in plan["generation"]


def test_rs_manifest_round_trips_through_existing_loader(tmp_path):
    matrix = build_fill001_rs_matrix("fill001-rs-roundtrip")
    manifest_path = tmp_path / "fill001-rs-roundtrip.json"

    write_fill001_matrix(matrix, manifest_path)
    loaded = load_fill001_matrix(manifest_path)

    assert loaded["matrix_signature"] == matrix["matrix_signature"]
    assert loaded["plan_variant"] == FILL001_RS_PLAN_VARIANT
    assert loaded["execution_allowed"] is False

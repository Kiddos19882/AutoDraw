from __future__ import annotations

import copy

import pytest

from chalk_experiment_matrix import (
    GEOMETRY_EXECUTOR_CONFIG,
    EXPECTED_STROKES,
    PHASE_SCENARIOS,
    RADIUS_GEOMETRY_VALIDATION_PHASE,
    RADIUS_GEOMETRY_VALIDATION_PROFILE,
    RADIUS_GEOMETRY_VALIDATION_RADII,
    build_chalk_experiment_matrix_metadata,
)
from chalk_test_blocks import (
    build_chalk_test_block_plan,
    create_chalk_test_block_journal,
    load_chalk_test_block_journal,
)
from chalk_int006r_validation import analyze_int006r_validation


def _strokes(count: int) -> list[dict]:
    return [
        {"name": f"stroke-{index}", "points": [[10 + index, 10], [30 + index, 10]]}
        for index in range(count)
    ]


@pytest.mark.parametrize("radius", RADIUS_GEOMETRY_VALIDATION_RADII)
def test_int006r_matrix_metadata_accepts_only_declared_radius_values(radius):
    scenario_id = PHASE_SCENARIOS[RADIUS_GEOMETRY_VALIDATION_PHASE][0]
    parameters = dict(GEOMETRY_EXECUTOR_CONFIG)
    parameters.update({
        "point_step_px": RADIUS_GEOMETRY_VALIDATION_PROFILE[0],
        "point_delay_ms": RADIUS_GEOMETRY_VALIDATION_PROFILE[1],
    })
    metadata = build_chalk_experiment_matrix_metadata(
        series_id="int006r-series",
        scenario_id=scenario_id,
        repeat_index=1,
        requested_radius=radius,
        strokes=_strokes(EXPECTED_STROKES[scenario_id]),
        executor_parameters=parameters,
    )
    assert metadata["phase_id"] == RADIUS_GEOMETRY_VALIDATION_PHASE
    assert metadata["requested_radius"] == radius
    assert "prediction_id" not in metadata


@pytest.mark.parametrize("radius", [0, 5, 29, 31, True])
def test_int006r_matrix_metadata_rejects_undeclared_radius_values(radius):
    scenario_id = PHASE_SCENARIOS[RADIUS_GEOMETRY_VALIDATION_PHASE][0]
    parameters = dict(GEOMETRY_EXECUTOR_CONFIG)
    parameters.update({
        "point_step_px": RADIUS_GEOMETRY_VALIDATION_PROFILE[0],
        "point_delay_ms": RADIUS_GEOMETRY_VALIDATION_PROFILE[1],
    })
    with pytest.raises(ValueError):
        build_chalk_experiment_matrix_metadata(
            series_id="int006r-series",
            scenario_id=scenario_id,
            repeat_index=1,
            requested_radius=radius,
            strokes=_strokes(EXPECTED_STROKES[scenario_id]),
            executor_parameters=parameters,
        )


def test_int006r_rejects_sampling_profiles_other_than_p1():
    scenario_id = PHASE_SCENARIOS[RADIUS_GEOMETRY_VALIDATION_PHASE][0]
    parameters = dict(GEOMETRY_EXECUTOR_CONFIG)
    parameters.update({"point_step_px": 2, "point_delay_ms": 10})
    with pytest.raises(ValueError, match="P1"):
        build_chalk_experiment_matrix_metadata(
            series_id="int006r-series",
            scenario_id=scenario_id,
            repeat_index=1,
            requested_radius=10,
            strokes=_strokes(EXPECTED_STROKES[scenario_id]),
            executor_parameters=parameters,
        )


def test_int006r_block_plan_contains_all_45_radius_geometry_repeat_cells(tmp_path):
    plan = build_chalk_test_block_plan(
        series_id="int006r-series",
        phase_id=RADIUS_GEOMETRY_VALIDATION_PHASE,
        seed=42,
    )
    assert plan["expected_task_count"] == 45
    assert plan["requested_radii"] == list(RADIUS_GEOMETRY_VALIDATION_RADII)
    assert "prediction_artifact" not in plan
    expected = {
        (scenario, radius, repeat)
        for scenario in PHASE_SCENARIOS[RADIUS_GEOMETRY_VALIDATION_PHASE]
        for radius in RADIUS_GEOMETRY_VALIDATION_RADII
        for repeat in (1, 2, 3)
    }
    observed = {
        (task["scenario_id"], task["requested_radius"], task["repeat_index"])
        for task in plan["tasks"]
    }
    assert observed == expected
    assert len({task["task_id"] for task in plan["tasks"]}) == 45
    assert all(
        task["executor_parameters"]["point_step_px"] == 4
        and task["executor_parameters"]["point_delay_ms"] == 5
        and "prediction_id" not in task
        for task in plan["tasks"]
    )
    journal_path = tmp_path / "int006r.json"
    create_chalk_test_block_journal(journal_path, plan)
    loaded = load_chalk_test_block_journal(journal_path)
    assert loaded["phase_id"] == RADIUS_GEOMETRY_VALIDATION_PHASE
    assert len(loaded["tasks"]) == 45


def test_int006r_journal_rejects_tampered_radius_and_duplicate_cells(tmp_path):
    plan = build_chalk_test_block_plan(
        series_id="int006r-invalid",
        phase_id=RADIUS_GEOMETRY_VALIDATION_PHASE,
        seed=43,
    )
    tampered_radius = copy.deepcopy(plan)
    tampered_radius["tasks"][0]["requested_radius"] = 5
    path = tmp_path / "bad-radius.json"
    create_chalk_test_block_journal(path, tampered_radius)
    with pytest.raises(ValueError, match="INT006R"):
        load_chalk_test_block_journal(path)

    tampered_duplicate = copy.deepcopy(plan)
    first, second = tampered_duplicate["tasks"][:2]
    second["scenario_id"] = first["scenario_id"]
    second["requested_radius"] = first["requested_radius"]
    second["repeat_index"] = first["repeat_index"]
    second["task_id"] = "tampered-duplicate-cell"
    path = tmp_path / "duplicate.json"
    create_chalk_test_block_journal(path, tampered_duplicate)
    with pytest.raises(ValueError, match="INT006R"):
        load_chalk_test_block_journal(path)


def test_int006r_analyzer_keeps_unexecuted_block_incomplete(tmp_path):
    plan = build_chalk_test_block_plan(
        series_id="int006r-pending",
        phase_id=RADIUS_GEOMETRY_VALIDATION_PHASE,
        seed=44,
    )
    journal_path = tmp_path / "pending.json"
    results_dir = tmp_path / "results"
    create_chalk_test_block_journal(journal_path, plan)
    report = analyze_int006r_validation(journal_path, results_dir)
    assert report["status"] == "incomplete"
    assert report["accepted_count"] == 0
    assert report["missing_count"] == 45
    assert report["safety_margin_status"] == "not_established"
    assert report["production_eligibility"] == "not_validated"

from __future__ import annotations

import copy
import json

import pytest
from PIL import Image

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


def test_int006r_analyzer_accepts_complete_45_capture_set_with_png_and_monitor_evidence(tmp_path):
    plan = build_chalk_test_block_plan(
        series_id="int006r-complete",
        phase_id=RADIUS_GEOMETRY_VALIDATION_PHASE,
        seed=45,
    )
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    for index, task in enumerate(plan["tasks"], start=1):
        scenario_id = task["scenario_id"]
        radius = task["requested_radius"]
        repeat = task["repeat_index"]
        stroke_count = task["expected_strokes"]
        experiment_id = f"int006r-exp-{index:02d}"
        run_id = f"int006r-run-{index:02d}"
        experiment_dir = results_dir / f"experiment-{index:02d}"
        experiment_dir.mkdir()
        strokes = _strokes(stroke_count)
        parameters = dict(task["executor_parameters"])
        metadata = build_chalk_experiment_matrix_metadata(
            series_id=plan["series_id"],
            scenario_id=scenario_id,
            repeat_index=repeat,
            requested_radius=radius,
            strokes=strokes,
            matrix_order_index=task["matrix_order_index"],
            executor_parameters=parameters,
        )
        consumed = stroke_count * 2
        events = []
        for stroke_index in range(stroke_count):
            stroke_id = f"{experiment_id}-stroke-{stroke_index + 1}"
            events.extend([
                {"type": "POINTER_DOWN_CANDIDATE", "strokeId": stroke_id},
                {"type": "DRAW_SAMPLE", "strokeId": stroke_id, "pointDelta": 2},
                {"type": "POINTER_UP_CANDIDATE", "strokeId": stroke_id},
            ])
        (experiment_dir / "monitor_report.json").write_text(
            json.dumps({"events": events}), encoding="utf-8"
        )
        Image.new("RGB", (460, 240), "white").save(experiment_dir / "before_draw-board.png")
        Image.new("RGB", (460, 240), "white").save(experiment_dir / "after_draw-board.png")

        plan["tasks"][index - 1]["status"] = "completed"
        plan["tasks"][index - 1]["attempts"] = [{
            "attempt_id": f"int006r-attempt-{index:02d}",
            "status": "completed",
            "started_at_utc": "2026-11-03T00:00:00Z",
            "finished_at_utc": "2026-11-03T00:00:01Z",
            "experiment_id": experiment_id,
            "experiment_dir": str(experiment_dir),
            "reason": None,
        }]
        capture = {
            "status": "saved",
            "run_id": run_id,
            "experiment_id": experiment_id,
            "chalk_experiment_matrix": metadata,
            "stroke_count": stroke_count,
            "expected_stroke_count": stroke_count,
            "brush_radius_status": "single",
            "chalk_status": "exact",
            "chalk_counter_consistent": True,
            "point_delta_matches_chalk": True,
            "dropped_events": 0,
            "monitor_dropped_events": 0,
            "monitor_error_count_delta": 0,
            "bridge_send_failures_delta": 0,
            "collector_sequence_gap_count": 0,
        }
        summary = {
            "run_id": run_id,
            "autodraw_experiment_id": experiment_id,
            "chalk_experiment_matrix": metadata,
            "brush_radius_status": "single",
            "observed_brush_radii": [radius],
            "point_delta_matches_chalk": True,
            "stroke_count": stroke_count,
            "sampled_point_delta_total": consumed,
            "dropped_events": 0,
            "monitor_dropped_events": 0,
            "monitor_error_count_delta": 0,
            "bridge_send_failures_delta": 0,
            "collector_sequence_gap_count": 0,
            "chalk": {
                "status": "exact",
                "pre_point_count": 1000,
                "post_point_count": 1000 + consumed,
                "consumed_points": consumed,
            },
            "frame_probe": {"status": "measured", "visibility_interruption": False},
            "trajectory": {"accepted_sample_count": stroke_count},
        }
        manifest = {
            "experiment_id": experiment_id,
            "test_case": scenario_id,
            "brush_value_requested": radius,
            "chalk_experiment_matrix": metadata,
            "chalk_test_block": {
                "block_id": plan["block_id"],
                "task_id": task["task_id"],
                "phase_id": RADIUS_GEOMETRY_VALIDATION_PHASE,
            },
            "monitor_capture": capture,
            "game_monitor_summary": summary,
            "execution_report": {
                "status": "completed",
                "completed_strokes": stroke_count,
                "executor_config": parameters,
            },
            "phases": {
                "before_clear": {"status": "restored"},
                "before_draw": {
                    "captured_at_utc": "2026-11-03T00:00:00Z",
                    "files": {"board_roi": "before_draw-board.png"},
                },
                "after_draw": {
                    "status": "captured",
                    "files": {"board_roi": "after_draw-board.png"},
                },
                "postdraw_workflow": {"status": "completed"},
            },
        }
        (experiment_dir / "experiment.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )

    plan["status"] = "completed"
    journal_path = tmp_path / "completed-int006r.json"
    create_chalk_test_block_journal(journal_path, plan)
    report = analyze_int006r_validation(journal_path, results_dir)

    assert report["status"] == "complete"
    assert report["accepted_count"] == 45
    assert report["missing_count"] == 0
    assert report["rejected"] == []
    assert report["png_evidence_status"] == "complete"
    assert report["visual_quality_gate"] == "pending_manual_review"
    for scenario_id in PHASE_SCENARIOS[RADIUS_GEOMETRY_VALIDATION_PHASE]:
        for radius in RADIUS_GEOMETRY_VALIDATION_RADII:
            group = report["groups"][scenario_id][str(radius)]
            assert group["count"] == 3
            assert len(group["repeat_chalk"]) == 3
            assert len(group["per_stroke_chalk"]) == 3 * EXPECTED_STROKES[scenario_id]

from __future__ import annotations

import json
import sys
from pathlib import Path

PREPARATION_DIR = Path(__file__).resolve().parents[1]
if str(PREPARATION_DIR) not in sys.path:
    sys.path.insert(0, str(PREPARATION_DIR))

from chalk_experiment_matrix import GEOMETRY_EXECUTOR_CONFIG, build_chalk_experiment_matrix_metadata
from chalk_int006_validation import (
    DRAWING_PLANS,
    EXPECTED_TOTALS,
    MODEL_ID,
    PROFILES,
    analyze_int006_validation,
    build_int006_prediction_artifact,
    validate_int006_prediction_artifact,
)
from chalk_test_blocks import (
    build_chalk_test_block_plan,
    claim_next_chalk_block_task,
    create_chalk_test_block_journal,
    finish_chalk_block_task,
)


def _write_capture(results_dir: Path, journal: dict, task: dict, artifact: dict, actual: int) -> Path:
    scenario_id = task["scenario_id"]
    parameters = task["executor_parameters"]
    profile_id = next(
        name for name, profile in PROFILES.items()
        if (profile["point_step_px"], profile["point_delay_ms"])
        == (parameters["point_step_px"], parameters["point_delay_ms"])
    )
    prediction_id = f"{MODEL_ID}:{scenario_id}:{profile_id}"
    prediction = artifact["predictions"][prediction_id]
    # Match the runtime DrawingPlan serialization: logical coordinate arrays
    # become point objects and each stroke carries execution metadata.
    strokes = [
        {
            "closed": False,
            "metadata": {
                "line_extension_px_override": 0.0,
                "role": "brush_behavior_test",
                "test_case": scenario_id,
            },
            "name": stroke["name"],
            "points": [
                {"x": float(point[0]), "y": float(point[1])}
                for point in stroke["points"]
            ],
        }
        for stroke in prediction["planned_strokes"]
    ]
    experiment_id = f"exp-{task['task_id']}"
    run_id = f"run-{task['task_id']}"
    folder = results_dir / experiment_id
    folder.mkdir(parents=True)
    matrix = build_chalk_experiment_matrix_metadata(
        series_id=journal["series_id"],
        scenario_id=scenario_id,
        repeat_index=task["repeat_index"],
        requested_radius=10,
        strokes=strokes,
        matrix_order_index=task["matrix_order_index"],
        executor_parameters=parameters,
        prediction_id=prediction_id,
    )
    stroke_count = len(strokes)
    per_stroke = [actual // stroke_count] * stroke_count
    for index in range(actual % stroke_count):
        per_stroke[index] += 1
    events = []
    for index, consumed in enumerate(per_stroke):
        stroke_id = f"stroke-{index + 1}"
        events.extend([
            {"type": "POINTER_DOWN_CANDIDATE", "strokeId": stroke_id},
            {"type": "DRAW_SAMPLE", "strokeId": stroke_id, "pointDelta": consumed},
            {"type": "POINTER_UP_CANDIDATE", "strokeId": stroke_id},
        ])
    (folder / "monitor_report.json").write_text(json.dumps({"events": events}), encoding="utf-8")
    document = {
        "record_type": "autodraw_brush_paint_experiment",
        "experiment_id": experiment_id,
        "test_case": scenario_id,
        "brush_value_requested": 10,
        "chalk_experiment_matrix": matrix,
        "chalk_test_block": {
            "block_id": journal["block_id"],
            "task_id": task["task_id"],
            "phase_id": "INT006",
        },
        "monitor_capture": {
            "status": "saved",
            "experiment_id": experiment_id,
            "run_id": run_id,
            "chalk_experiment_matrix": matrix,
            "stroke_count": stroke_count,
            "expected_stroke_count": stroke_count,
            "brush_radius_status": "single",
            "chalk_status": "exact",
            "chalk_counter_consistent": True,
            "point_delta_matches_chalk": True,
            "dropped_events": 0,
            "monitor_error_count_delta": 0,
            "bridge_send_failures_delta": 0,
            "collector_sequence_gap_count": 0,
        },
        "game_monitor_summary": {
            "autodraw_experiment_id": experiment_id,
            "run_id": run_id,
            "chalk_experiment_matrix": matrix,
            "brush_radius_status": "single",
            "observed_brush_radii": [10],
            "stroke_count": stroke_count,
            "point_delta_matches_chalk": True,
            "dropped_events": 0,
            "monitor_error_count_delta": 0,
            "bridge_send_failures_delta": 0,
            "collector_sequence_gap_count": 0,
            "chalk": {
                "status": "exact",
                "pre_point_count": 1000,
                "post_point_count": 1000 + actual,
                "consumed_points": actual,
            },
            "sampled_point_delta_total": actual,
        },
        "execution_report": {
            "status": "completed",
            "completed_strokes": stroke_count,
            "executor_config": dict(parameters),
        },
    }
    manifest_path = folder / "experiment.json"
    manifest_path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


def test_prediction_artifact_contains_15_frozen_records_and_hash():
    artifact = build_int006_prediction_artifact("int006-test-series")
    artifact = json.loads(json.dumps(artifact, ensure_ascii=False))
    valid, reason = validate_int006_prediction_artifact(artifact, expected_series_id="int006-test-series")
    assert valid is True
    assert reason == "valid"
    assert len(artifact["predictions"]) == 15
    assert artifact["expected_cell_count"] == 45
    for scenario_id in DRAWING_PLANS:
        for profile_id in PROFILES:
            prediction = artifact["predictions"][f"{MODEL_ID}:{scenario_id}:{profile_id}"]
            assert prediction["predicted_chalk"] == EXPECTED_TOTALS[scenario_id][profile_id]
            assert prediction["radius"] == 10
            if scenario_id == "int006_validation_d4_short_details":
                assert all(item["rule"] == "exact_short_lookup" for item in prediction["stroke_predictions"])


def test_prediction_artifact_rejects_modified_prediction_without_resealing():
    artifact = build_int006_prediction_artifact("int006-test-series")
    artifact["predictions"][next(iter(artifact["predictions"]))]["predicted_chalk"] += 1
    valid, reason = validate_int006_prediction_artifact(artifact)
    assert valid is False
    assert reason == "prediction_artifact_hash_mismatch"


def test_analyzer_matches_all_45_cells_and_calculates_metrics(tmp_path):
    series_id = "int006-synthetic-series"
    plan = build_chalk_test_block_plan(series_id=series_id, phase_id="INT006", seed=123)
    journal_path = tmp_path / "int006-block.json"
    create_chalk_test_block_journal(journal_path, plan)
    results_dir = tmp_path / "results"
    results_dir.mkdir()

    for task in plan["tasks"]:
        actual = round(plan["prediction_artifact"]["predictions"][task["prediction_id"]]["predicted_chalk"])
        _write_capture(results_dir, plan, task, plan["prediction_artifact"], actual)

    # Mark each planned task complete in the durable journal, preserving task order.
    for index in range(len(plan["tasks"])):
        task = claim_next_chalk_block_task(journal_path)
        assert task is not None
        finish_chalk_block_task(
            journal_path,
            task["task_id"],
            accepted=True,
            experiment_id=f"exp-{task['task_id']}",
            experiment_dir=results_dir / f"exp-{task['task_id']}",
        )

    result = analyze_int006_validation(journal_path, results_dir)
    assert result["status"] == "complete"
    assert result["accepted_count"] == 45
    assert result["missing_cells"] == []
    assert result["rejected"] == []
    assert len(result["groups"]) == 15
    assert all(group["complete_repeats"] for group in result["groups"].values())
    assert all(group["mae"] is not None for group in result["groups"].values())
    assert result["safety_margin_status"] == "not_established"
    assert result["production_eligibility"] == "not_validated"


def test_analyzer_rejects_changed_geometry_prediction_binding(tmp_path):
    series_id = "int006-tamper-series"
    plan = build_chalk_test_block_plan(series_id=series_id, phase_id="INT006", seed=1)
    journal_path = tmp_path / "int006-block.json"
    create_chalk_test_block_journal(journal_path, plan)
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    task = plan["tasks"][0]
    actual = round(plan["prediction_artifact"]["predictions"][task["prediction_id"]]["predicted_chalk"])
    manifest_path = _write_capture(results_dir, plan, task, plan["prediction_artifact"], actual)
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    document["chalk_experiment_matrix"]["geometry_signature"] = "0" * 64
    document["monitor_capture"]["chalk_experiment_matrix"] = document["chalk_experiment_matrix"]
    document["game_monitor_summary"]["chalk_experiment_matrix"] = document["chalk_experiment_matrix"]
    manifest_path.write_text(json.dumps(document), encoding="utf-8")

    result = analyze_int006_validation(journal_path, results_dir)
    assert result["accepted_count"] == 0
    assert result["status"] == "incomplete"
    assert result["rejected"][0]["reason"] == "geometry_signature_mismatch"


def test_analyzer_accepts_original_windows_experiment_path_after_relocation(tmp_path):
    series_id = "int006-relocated-path-series"
    plan = build_chalk_test_block_plan(series_id=series_id, phase_id="INT006", seed=7)
    journal_path = tmp_path / "int006-block.json"
    create_chalk_test_block_journal(journal_path, plan)
    results_dir = tmp_path / "results"
    results_dir.mkdir()

    task = claim_next_chalk_block_task(journal_path)
    assert task is not None
    actual = round(plan["prediction_artifact"]["predictions"][task["prediction_id"]]["predicted_chalk"])
    manifest_path = _write_capture(results_dir, plan, task, plan["prediction_artifact"], actual)
    finish_chalk_block_task(
        journal_path,
        task["task_id"],
        accepted=True,
        experiment_id=f"exp-{task['task_id']}",
        experiment_dir=manifest_path.parent,
    )

    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    journal_task = next(item for item in journal["tasks"] if item["task_id"] == task["task_id"])
    slash = chr(92)
    journal_task["attempts"][0]["experiment_dir"] = slash.join([
        "C:", "Users", "Kiddos", "Desktop", "autodraw-g3-preflight-build",
        "data", "results", "brush_behavior_tests", manifest_path.parent.name,
    ])
    journal_path.write_text(json.dumps(journal, ensure_ascii=False, indent=2), encoding="utf-8")

    result = analyze_int006_validation(journal_path, results_dir)
    assert result["accepted_count"] == 1
    assert result["rejected"] == []
    assert len(result["missing_cells"]) == 44


def test_analyzer_rejects_journal_prediction_id_mismatch(tmp_path):
    series_id = "int006-journal-prediction-binding-series"
    plan = build_chalk_test_block_plan(series_id=series_id, phase_id="INT006", seed=11)
    journal_path = tmp_path / "int006-block.json"
    create_chalk_test_block_journal(journal_path, plan)
    results_dir = tmp_path / "results"
    results_dir.mkdir()

    task = claim_next_chalk_block_task(journal_path)
    assert task is not None
    actual = round(plan["prediction_artifact"]["predictions"][task["prediction_id"]]["predicted_chalk"])
    manifest_path = _write_capture(results_dir, plan, task, plan["prediction_artifact"], actual)
    finish_chalk_block_task(
        journal_path,
        task["task_id"],
        accepted=True,
        experiment_id=f"exp-{task['task_id']}",
        experiment_dir=manifest_path.parent,
    )

    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    journal_task = next(item for item in journal["tasks"] if item["task_id"] == task["task_id"])
    journal_task["prediction_id"] = "tampered-prediction-id"
    journal_path.write_text(json.dumps(journal, ensure_ascii=False, indent=2), encoding="utf-8")

    result = analyze_int006_validation(journal_path, results_dir)
    assert result["accepted_count"] == 0
    assert result["rejected"][0]["reason"] == "journal_prediction_id_mismatch"
    assert len(result["missing_cells"]) == 45

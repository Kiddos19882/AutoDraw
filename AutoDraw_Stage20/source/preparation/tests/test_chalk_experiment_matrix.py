from __future__ import annotations

import json

import pytest

from chalk_experiment_matrix import (
    GEOMETRY_EXECUTOR_CONFIG,
    PHASE_SCENARIOS,
    build_chalk_experiment_matrix_metadata,
    inspect_chalk_matrix_series,
    summarize_chalk_experiment_matrix,
)


def _strokes(count=5):
    return [
        {"name": f"line_{index}", "points": [{"x": 10.0, "y": float(index)}, {"x": 20.0, "y": float(index)}]}
        for index in range(count)
    ]


def _manifest(
    tmp_path,
    repeat=1,
    run_id="run-1",
    consumed=50,
    scenario="horizontal_lengths",
    executor_parameters=None,
    matrix_order_index=None,
    experiment_id=None,
):
    stroke_count = 6 if scenario == "paint_consumption_long_lines" else 5
    strokes = _strokes(stroke_count)
    parameters = dict(executor_parameters or GEOMETRY_EXECUTOR_CONFIG)
    metadata = build_chalk_experiment_matrix_metadata(
        series_id="geometry-series",
        scenario_id=scenario,
        repeat_index=repeat,
        requested_radius=10,
        strokes=strokes,
        matrix_order_index=matrix_order_index or repeat,
        executor_parameters=parameters,
    )
    experiment_id = experiment_id or f"exp-{repeat}"
    report_events = []
    for index in range(stroke_count):
        stroke_id = f"stroke-{index + 1}"
        report_events.extend([
            {"type": "POINTER_DOWN_CANDIDATE", "strokeId": stroke_id},
            {"type": "DRAW_SAMPLE", "strokeId": stroke_id, "pointDelta": consumed // stroke_count},
            {"type": "POINTER_UP_CANDIDATE", "strokeId": stroke_id},
        ])
    (tmp_path / "monitor_report.json").write_text(
        json.dumps({"events": report_events}), encoding="utf-8"
    )
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
        "monitor_error_count": 0,
    }
    summary = {
        "run_id": run_id,
        "autodraw_experiment_id": experiment_id,
        "chalk_experiment_matrix": metadata,
        "brush_radius_status": "single",
        "observed_brush_radii": [10],
        "point_delta_matches_chalk": True,
        "stroke_count": stroke_count,
        "sampled_point_delta_total": consumed,
        "dropped_events": 0,
        "monitor_dropped_events": 0,
        "monitor_error_count": 0,
        "chalk": {
            "status": "exact",
            "pre_point_count": 1,
            "post_point_count": consumed + 1,
            "consumed_points": consumed,
        },
    }
    return {
        "experiment_id": experiment_id,
        "test_case": scenario,
        "brush_value_requested": 10,
        "chalk_experiment_matrix": metadata,
        "monitor_capture": capture,
        "game_monitor_summary": summary,
        "execution_report": {
            "status": "completed",
            "completed_strokes": stroke_count,
            "executor_config": parameters,
        },
        "experiment_dir": str(tmp_path),
    }


def test_geometry_metadata_records_phase_repeat_stroke_count_and_signature():
    metadata = build_chalk_experiment_matrix_metadata(
        series_id="geometry-20261101",
        scenario_id="horizontal_lengths",
        repeat_index=2,
        requested_radius=10,
        strokes=_strokes(),
        matrix_order_index=7,
    )
    assert metadata["phase_id"] == "G1"
    assert metadata["repeat_index"] == 2
    assert metadata["matrix_order_index"] == 7
    assert metadata["expected_strokes"] == 5
    assert len(metadata["geometry_signature"]) == 64
    assert metadata["planned_strokes"] == _strokes()
    assert metadata["executor_parameters"] == GEOMETRY_EXECUTOR_CONFIG


@pytest.mark.parametrize(
    "kwargs",
    [
        {"series_id": "bad id", "scenario_id": "horizontal_lengths", "repeat_index": 1, "requested_radius": 10, "strokes": _strokes()},
        {"series_id": "series", "scenario_id": "horizontal_lengths", "repeat_index": 4, "requested_radius": 10, "strokes": _strokes()},
        {"series_id": "series", "scenario_id": "horizontal_lengths", "repeat_index": 1.0, "requested_radius": 10, "strokes": _strokes()},
        {"series_id": "series", "scenario_id": "unknown", "repeat_index": 1, "requested_radius": 10, "strokes": _strokes()},
        {"series_id": "series", "scenario_id": "horizontal_lengths", "repeat_index": 1, "requested_radius": 10, "strokes": _strokes(4)},
        {"series_id": "series", "scenario_id": "horizontal_lengths", "repeat_index": 1, "requested_radius": 5, "strokes": _strokes()},
    ],
)
def test_geometry_metadata_rejects_invalid_series_scenario_repeat_or_stroke_count(kwargs):
    with pytest.raises(ValueError):
        build_chalk_experiment_matrix_metadata(**kwargs)


def test_paired_renderer_metadata_uses_prr_phase_and_frozen_executor_profile():
    metadata = build_chalk_experiment_matrix_metadata(
        series_id="paired-renderer-series",
        scenario_id="paired_renderer_vertical_single_stroke",
        repeat_index=2,
        requested_radius=10,
        strokes=_strokes(1),
        matrix_order_index=1,
        executor_parameters=dict(GEOMETRY_EXECUTOR_CONFIG),
    )
    assert metadata["phase_id"] == "PRR"
    assert metadata["expected_strokes"] == 1
    assert metadata["repeat_index"] == 2
    assert metadata["planned_repeats"] == 3

    invalid = dict(GEOMETRY_EXECUTOR_CONFIG)
    invalid["point_step_px"] = 1
    with pytest.raises(ValueError):
        build_chalk_experiment_matrix_metadata(
            series_id="paired-renderer-series",
            scenario_id="paired_renderer_diagonal_single_stroke",
            repeat_index=3,
            requested_radius=10,
            strokes=_strokes(1),
            matrix_order_index=2,
            executor_parameters=invalid,
        )


def test_geometry_matrix_accepts_three_repeats_and_validates_per_stroke_sum(tmp_path):
    docs = []
    for repeat, consumed in ((1, 50), (2, 55), (3, 60)):
        folder = tmp_path / f"exp-{repeat}"
        folder.mkdir()
        docs.append(_manifest(folder, repeat=repeat, run_id=f"run-{repeat}", consumed=consumed))

    result = summarize_chalk_experiment_matrix(docs)
    scenario = result["scenarios"][0]
    assert result["valid_measurement_count"] == 3
    assert scenario["complete"] is True
    assert scenario["geometry_consistent"] is True
    assert scenario["mean"] == 55
    assert scenario["median"] == 55
    assert scenario["stroke_level_complete_repeat_count"] == 3
    assert [row["consumed_points"] for row in scenario["measurements"][0]["stroke_level"]["strokes"]] == [10] * 5


def test_geometry_matrix_keeps_total_valid_when_per_stroke_split_is_incomplete(tmp_path):
    folder = tmp_path / "exp"
    folder.mkdir()
    doc = _manifest(folder, consumed=50)
    report = {"events": [
        {"type": "POINTER_DOWN_CANDIDATE", "strokeId": "stroke-1"},
        {"type": "DRAW_SAMPLE", "strokeId": "stroke-1", "pointDelta": 50},
        {"type": "POINTER_UP_CANDIDATE", "strokeId": "stroke-1"},
    ]}
    (folder / "monitor_report.json").write_text(json.dumps(report), encoding="utf-8")

    result = summarize_chalk_experiment_matrix([doc])
    row = result["scenarios"][0]["measurements"][0]
    assert result["valid_measurement_count"] == 1
    assert row["stroke_level"]["status"] == "incomplete"
    assert row["stroke_level"]["reason"] == "stroke_id_count_mismatch"


def test_geometry_matrix_ignores_non_consuming_pointer_candidate_for_stroke_count(tmp_path):
    folder = tmp_path / "exp"
    folder.mkdir()
    doc = _manifest(folder, consumed=50)
    events = [
        {"type": "POINTER_DOWN_CANDIDATE", "strokeId": "empty-candidate"},
        {"type": "DRAW_SAMPLE", "strokeId": "empty-candidate", "pointDelta": 0},
        {"type": "POINTER_UP_CANDIDATE", "strokeId": "empty-candidate"},
    ]
    for index in range(5):
        stroke_id = f"accepted-{index}"
        events.extend([
            {"type": "POINTER_DOWN_CANDIDATE", "strokeId": stroke_id},
            {"type": "DRAW_SAMPLE", "strokeId": stroke_id, "pointDelta": 10},
            {"type": "POINTER_UP_CANDIDATE", "strokeId": stroke_id},
        ])
    (folder / "monitor_report.json").write_text(json.dumps({"events": events}), encoding="utf-8")

    result = summarize_chalk_experiment_matrix([doc])
    row = result["scenarios"][0]["measurements"][0]
    assert result["valid_measurement_count"] == 1
    assert row["stroke_level"]["status"] == "complete"
    assert row["stroke_level"]["observed_stroke_candidates"] == 6
    assert row["stroke_level"]["non_consuming_stroke_ids"] == ["empty-candidate"]
    assert [stroke["consumed_points"] for stroke in row["stroke_level"]["strokes"]] == [10] * 5


def test_geometry_matrix_ignores_cumulative_monitor_buffer_overflow(tmp_path):
    folder = tmp_path / "exp"
    folder.mkdir()
    doc = _manifest(folder, consumed=50)
    doc["monitor_capture"]["monitor_dropped_events"] = 434
    doc["monitor_capture"]["monitor_buffer_dropped_events_delta"] = 434
    doc["monitor_capture"]["monitor_error_count"] = 8
    doc["monitor_capture"]["monitor_error_count_delta"] = 0
    doc["game_monitor_summary"]["monitor_dropped_events"] = 434
    doc["game_monitor_summary"]["monitor_buffer_dropped_events_delta"] = 434
    doc["game_monitor_summary"]["monitor_error_count"] = 8
    doc["game_monitor_summary"]["monitor_error_count_delta"] = 0

    result = summarize_chalk_experiment_matrix([doc])
    assert result["valid_measurement_count"] == 1
    assert result["rejected"] == []


def test_geometry_matrix_rejects_actual_bridge_or_collector_loss(tmp_path):
    folder = tmp_path / "exp"
    folder.mkdir()
    doc = _manifest(folder, consumed=50)
    doc["monitor_capture"]["bridge_send_failures_delta"] = 1
    doc["game_monitor_summary"]["bridge_send_failures_delta"] = 1

    result = summarize_chalk_experiment_matrix([doc])
    assert result["valid_measurement_count"] == 0
    assert result["rejected"][0]["reason"] == "capture_has_dropped_events_or_errors"


def test_geometry_matrix_rejects_duplicate_run_and_repeat_cell(tmp_path):
    folder_a, folder_b = tmp_path / "a", tmp_path / "b"
    folder_a.mkdir()
    folder_b.mkdir()
    a = _manifest(folder_a, repeat=1, run_id="same-run")
    b = _manifest(folder_b, repeat=1, run_id="same-run")
    result = summarize_chalk_experiment_matrix([a, b])
    assert result["valid_measurement_count"] == 0
    assert {item["reason"] for item in result["rejected"]} == {"duplicate_monitor_run"}


def test_geometry_matrix_rejects_changed_geometry_signature(tmp_path):
    folder = tmp_path / "exp"
    folder.mkdir()
    doc = _manifest(folder)
    doc["chalk_experiment_matrix"]["planned_strokes"][0]["points"][1]["x"] = 99
    doc["monitor_capture"]["chalk_experiment_matrix"] = doc["chalk_experiment_matrix"]
    doc["game_monitor_summary"]["chalk_experiment_matrix"] = doc["chalk_experiment_matrix"]
    result = summarize_chalk_experiment_matrix([doc])
    assert result["valid_measurement_count"] == 0
    assert result["rejected"][0]["reason"] == "matrix_metadata_mismatch:geometry_signature"



def test_inspect_matrix_series_blocks_used_repeat_and_assigns_next_order(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    doc1 = _manifest(first, repeat=1, run_id="run-1")
    doc2 = _manifest(second, repeat=2, run_id="run-2")
    (first / "experiment.json").write_text(json.dumps(doc1), encoding="utf-8")
    (second / "experiment.json").write_text(json.dumps(doc2), encoding="utf-8")

    occupied = inspect_chalk_matrix_series(
        tmp_path,
        series_id="geometry-series",
        scenario_id="horizontal_lengths",
        repeat_index=1,
    )
    assert occupied["duplicate_manifest_path"] == str(first / "experiment.json")
    assert occupied["series_experiment_count"] == 2
    assert occupied["next_matrix_order_index"] == 3

    available = inspect_chalk_matrix_series(
        tmp_path,
        series_id="geometry-series",
        scenario_id="horizontal_lengths",
        repeat_index=3,
    )
    assert available["duplicate_manifest_path"] is None
    assert available["next_matrix_order_index"] == 3


def test_inspect_matrix_series_counts_legacy_manifests_without_order_index(tmp_path):
    folder = tmp_path / "legacy"
    folder.mkdir()
    doc = _manifest(folder, repeat=1, run_id="legacy-run")
    doc["chalk_experiment_matrix"].pop("matrix_order_index")
    (folder / "experiment.json").write_text(json.dumps(doc), encoding="utf-8")

    state = inspect_chalk_matrix_series(
        tmp_path,
        series_id="geometry-series",
        scenario_id="vertical_lengths",
        repeat_index=2,
    )
    assert state["series_experiment_count"] == 1
    assert state["next_matrix_order_index"] == 2
    assert state["duplicate_manifest_path"] is None

def test_g3_metadata_distinguishes_executor_parameter_cells_and_blocks_only_exact_duplicates(tmp_path):
    first_parameters = dict(GEOMETRY_EXECUTOR_CONFIG)
    first_parameters.update({"point_step_px": 1, "point_delay_ms": 5})
    second_parameters = dict(GEOMETRY_EXECUTOR_CONFIG)
    second_parameters.update({"point_step_px": 2, "point_delay_ms": 5})
    metadata = build_chalk_experiment_matrix_metadata(
        series_id="g3-series",
        scenario_id="paint_consumption_long_lines",
        repeat_index=1,
        requested_radius=10,
        strokes=_strokes(6),
        matrix_order_index=1,
        executor_parameters=first_parameters,
    )
    assert metadata["phase_id"] == "G3"
    assert metadata["expected_strokes"] == 6
    assert metadata["executor_parameters"] == first_parameters

    folder = tmp_path / "g3-run"
    folder.mkdir()
    (folder / "experiment.json").write_text(
        json.dumps({"chalk_experiment_matrix": metadata}), encoding="utf-8"
    )
    occupied = inspect_chalk_matrix_series(
        tmp_path,
        series_id="g3-series",
        scenario_id="paint_consumption_long_lines",
        repeat_index=1,
        executor_parameters=first_parameters,
    )
    assert occupied["duplicate_manifest_path"] == str(folder / "experiment.json")
    available = inspect_chalk_matrix_series(
        tmp_path,
        series_id="g3-series",
        scenario_id="paint_consumption_long_lines",
        repeat_index=1,
        executor_parameters=second_parameters,
    )
    assert available["duplicate_manifest_path"] is None


@pytest.mark.parametrize(
    "step, delay",
    [(0, 5), (3, 5), (1, 0), (1, 15), (1.0, 5)],
)
def test_g3_metadata_rejects_values_outside_the_experiment_matrix(step, delay):
    parameters = dict(GEOMETRY_EXECUTOR_CONFIG)
    parameters.update({"point_step_px": step, "point_delay_ms": delay})
    with pytest.raises(ValueError):
        build_chalk_experiment_matrix_metadata(
            series_id="g3-series",
            scenario_id="paint_consumption_long_lines",
            repeat_index=1,
            requested_radius=10,
            strokes=_strokes(6),
            executor_parameters=parameters,
        )

def test_g3_analyzer_keeps_nine_executor_configurations_separate_and_complete(tmp_path):
    documents = []
    order = 0
    for step in (1, 2, 4):
        for delay in (5, 10, 20):
            parameters = dict(GEOMETRY_EXECUTOR_CONFIG)
            parameters.update({"point_step_px": step, "point_delay_ms": delay})
            for repeat in (1, 2, 3):
                order += 1
                folder = tmp_path / f"g3-{step}-{delay}-{repeat}"
                folder.mkdir()
                consumed = 60 + 6 * (step + delay // 5 + repeat)
                documents.append(_manifest(
                    folder,
                    repeat=repeat,
                    run_id=f"g3-run-{order}",
                    consumed=consumed,
                    scenario="paint_consumption_long_lines",
                    executor_parameters=parameters,
                    matrix_order_index=order,
                    experiment_id=f"g3-exp-{order}",
                ))

    result = summarize_chalk_experiment_matrix(documents)
    assert result["valid_measurement_count"] == 27
    assert result["rejected_measurement_count"] == 0
    assert len(result["scenarios"]) == 9
    assert all(row["phase_id"] == "G3" and row["complete"] for row in result["scenarios"])
    assert {
        (row["point_step_px"], row["point_delay_ms"])
        for row in result["scenarios"]
    } == {(step, delay) for step in (1, 2, 4) for delay in (5, 10, 20)}
    assert all(row["valid_repeat_count"] == 3 for row in result["scenarios"])


@pytest.mark.parametrize(
    ("phase", "scenario", "count", "profile"),
    [
        ("V1", "int006_diagonals", 6, (2, 10)),
        ("V2", "int006_short_strokes_followup", 5, (4, 5)),
        ("V3", "int006_turns", 3, (4, 10)),
        ("V4", "int006_closed_contours", 3, (2, 10)),
        ("V5", "int006_intersections_spacing_sweep", 16, (4, 5)),
    ],
)
def test_int006_scenarios_accept_declared_sampling_profiles(phase, scenario, count, profile):
    parameters = dict(GEOMETRY_EXECUTOR_CONFIG)
    parameters.update({"point_step_px": profile[0], "point_delay_ms": profile[1]})
    metadata = build_chalk_experiment_matrix_metadata(
        series_id="int006-series", scenario_id=scenario, repeat_index=1,
        requested_radius=10, strokes=_strokes(count), executor_parameters=parameters,
    )
    assert metadata["phase_id"] == phase
    assert metadata["expected_strokes"] == count



@pytest.mark.parametrize(
    ("scenario", "stroke_count"),
    [
        ("int006_short_strokes", 6),
        ("int006_intersections_spacing", 10),
    ],
)
def test_legacy_int006_v2_v5_scenarios_remain_analyzable(scenario, stroke_count):
    metadata = build_chalk_experiment_matrix_metadata(
        series_id="int006-legacy-series", scenario_id=scenario, repeat_index=1,
        requested_radius=10, strokes=_strokes(stroke_count),
        executor_parameters=dict(GEOMETRY_EXECUTOR_CONFIG),
    )
    assert metadata["phase_id"] in {"V2", "V5"}
    assert metadata["expected_strokes"] == stroke_count
    assert scenario not in {item for scenarios in PHASE_SCENARIOS.values() for item in scenarios}


def test_int006_matrix_rejects_unplanned_sampling_profile():
    parameters = dict(GEOMETRY_EXECUTOR_CONFIG)
    parameters.update({"point_step_px": 1, "point_delay_ms": 5})
    with pytest.raises(ValueError, match="V1–V5"):
        build_chalk_experiment_matrix_metadata(
            series_id="int006-series", scenario_id="int006_diagonals",
            repeat_index=1, requested_radius=10, strokes=_strokes(6),
            executor_parameters=parameters,
        )


def test_int006_metadata_requires_a_frozen_prediction_id():
    strokes = _strokes(4)
    parameters = {
        **GEOMETRY_EXECUTOR_CONFIG,
        "point_step_px": 2,
        "point_delay_ms": 10,
    }
    with pytest.raises(ValueError, match="prediction_id"):
        build_chalk_experiment_matrix_metadata(
            series_id="int006-series",
            scenario_id="int006_validation_d1_mixed_lines",
            repeat_index=1,
            requested_radius=10,
            strokes=strokes,
            executor_parameters=parameters,
        )
    metadata = build_chalk_experiment_matrix_metadata(
        series_id="int006-series",
        scenario_id="int006_validation_d1_mixed_lines",
        repeat_index=1,
        requested_radius=10,
        strokes=strokes,
        executor_parameters=parameters,
        prediction_id="chalk-int006-frozen-2026-11-02:int006_validation_d1_mixed_lines:P0",
    )
    assert metadata["prediction_id"].endswith(":P0")

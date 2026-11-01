from __future__ import annotations

import json

import pytest

from chalk_experiment_matrix import (
    GEOMETRY_EXECUTOR_CONFIG,
    build_chalk_experiment_matrix_metadata,
    inspect_chalk_matrix_series,
    summarize_chalk_experiment_matrix,
)


def _strokes(count=5):
    return [
        {"name": f"line_{index}", "points": [{"x": 10.0, "y": float(index)}, {"x": 20.0, "y": float(index)}]}
        for index in range(count)
    ]


def _manifest(tmp_path, repeat=1, run_id="run-1", consumed=50, scenario="horizontal_lengths"):
    strokes = _strokes(5)
    metadata = build_chalk_experiment_matrix_metadata(
        series_id="geometry-series",
        scenario_id=scenario,
        repeat_index=repeat,
        requested_radius=10,
        strokes=strokes,
        matrix_order_index=repeat,
    )
    experiment_id = f"exp-{repeat}"
    report_events = []
    for index in range(5):
        stroke_id = f"stroke-{index + 1}"
        report_events.extend([
            {"type": "POINTER_DOWN_CANDIDATE", "strokeId": stroke_id},
            {"type": "DRAW_SAMPLE", "strokeId": stroke_id, "pointDelta": consumed // 5},
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
        "stroke_count": 5,
        "expected_stroke_count": 5,
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
        "stroke_count": 5,
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
        "execution_report": {"status": "completed", "completed_strokes": 5, "executor_config": dict(GEOMETRY_EXECUTOR_CONFIG)},
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
    doc["monitor_capture"]["chalk_experiment_matrix"].pop("matrix_order_index")
    doc["game_monitor_summary"]["chalk_experiment_matrix"].pop("matrix_order_index")
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

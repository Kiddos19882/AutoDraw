from __future__ import annotations

import json

import pytest

from chalk_radius_matrix import (
    MATRIX_BLOCKS,
    RADIUS_LEVELS,
    build_chalk_radius_matrix_metadata,
    is_monitor_run_claimed,
    summarize_chalk_radius_matrix,
)


def _manifest(radius=5, block=1, run_id="run-1", consumed=100):
    return {
        "experiment_id": f"exp-{block}-{radius}",
        "test_case": "paint_consumption_long_lines",
        "brush_value_requested": radius,
        "chalk_radius_matrix": build_chalk_radius_matrix_metadata(
            series_id="matrix-test", block=block, requested_radius=radius
        ),
        "execution_report": {"status": "completed", "completed_strokes": 6},
        "monitor_capture": {
            "status": "saved", "run_id": run_id, "stroke_count": 6,
            "expected_stroke_count": 6, "experiment_id": f"exp-{block}-{radius}",
            "brush_radius_status": "single", "chalk_status": "exact",
            "chalk_counter_consistent": True, "point_delta_matches_chalk": True,
            "dropped_events": 0, "monitor_dropped_events": 0, "monitor_error_count": 0,
            "chalk_radius_matrix": build_chalk_radius_matrix_metadata(
                series_id="matrix-test", block=block, requested_radius=radius
            ),
        },
        "game_monitor_summary": {
            "run_id": run_id,
            "autodraw_experiment_id": f"exp-{block}-{radius}",
            "chalk_radius_matrix": build_chalk_radius_matrix_metadata(
                series_id="matrix-test", block=block, requested_radius=radius
            ),
            "brush_radius_status": "single",
            "observed_brush_radii": [radius],
            "point_delta_matches_chalk": True,
            "stroke_count": 6,
            "frame_probe": {"status": "measured", "visibility_interruption": False},
            "trajectory": {"accepted_sample_count": 12},
            "dropped_events": 0, "monitor_dropped_events": 0, "monitor_error_count": 0,
            "chalk": {
                "status": "exact",
                "pre_point_count": 1,
                "post_point_count": consumed + 1,
                "consumed_points": consumed,
            },
        },
    }


def test_matrix_metadata_accepts_only_planned_radius_and_block():
    metadata = build_chalk_radius_matrix_metadata(
        series_id="series-20261031", block=2, requested_radius=15
    )
    assert metadata["planned_radii"] == list(RADIUS_LEVELS)
    assert metadata["block_order"] == list(MATRIX_BLOCKS[2])
    assert metadata["repeat_index"] == 2
    assert metadata["matrix_order_index"] == 4

    with pytest.raises(ValueError):
        build_chalk_radius_matrix_metadata(series_id="bad id", block=1, requested_radius=5)
    with pytest.raises(ValueError):
        build_chalk_radius_matrix_metadata(series_id="series", block=4, requested_radius=5)
    with pytest.raises(ValueError):
        build_chalk_radius_matrix_metadata(series_id="series", block=1, requested_radius=7)


def test_monitor_run_claim_is_detected_and_current_experiment_can_be_excluded(tmp_path):
    old = tmp_path / "experiment-old"
    old.mkdir()
    (old / "experiment.json").write_text(
        json.dumps({"monitor_capture": {"run_id": "run-1"}}), encoding="utf-8"
    )
    assert is_monitor_run_claimed(tmp_path, "run-1") is True
    assert is_monitor_run_claimed(tmp_path, "run-2") is False
    assert is_monitor_run_claimed(tmp_path, "run-1", exclude_experiment_dir=old) is False


def test_matrix_summary_accepts_valid_cells_and_calculates_repeat_statistics():
    docs = [
        _manifest(radius=5, block=1, run_id="r1", consumed=100),
        _manifest(radius=5, block=2, run_id="r2", consumed=110),
        _manifest(radius=5, block=3, run_id="r3", consumed=120),
    ]
    summary = summarize_chalk_radius_matrix(docs)
    radius = summary["series"][0]["radii"][1]
    assert summary["valid_measurement_count"] == 3
    assert radius["complete"] is True
    assert radius["mean"] == 110
    assert radius["median"] == 110
    assert radius["range"] == 20
    assert radius["missing_blocks"] == []


def test_matrix_summary_rejects_inexact_and_duplicate_monitor_runs():
    bad = _manifest(radius=5, block=1, run_id="same", consumed=100)
    bad["game_monitor_summary"]["chalk"]["post_point_count"] = 999
    duplicate_a = _manifest(radius=10, block=1, run_id="duplicate", consumed=200)
    duplicate_b = _manifest(radius=15, block=2, run_id="duplicate", consumed=300)

    summary = summarize_chalk_radius_matrix([bad, duplicate_a, duplicate_b])
    assert summary["valid_measurement_count"] == 0
    reasons = {item["reason"] for item in summary["rejected"]}
    assert "chalk_counter_inexact" in reasons
    assert "duplicate_monitor_run" in reasons


def test_matrix_summary_rejects_duplicate_radius_block_cell():
    docs = [
        _manifest(radius=20, block=1, run_id="r1"),
        _manifest(radius=20, block=1, run_id="r2"),
    ]
    summary = summarize_chalk_radius_matrix(docs)
    assert summary["valid_measurement_count"] == 0
    assert summary["rejected"][0]["reason"] == "duplicate_matrix_cell"
    assert summary["rejected"][1]["reason"] == "duplicate_matrix_cell"

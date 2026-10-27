from __future__ import annotations

import pytest

from game_point_calibration import GamePointCalibrationError, analyze_game_point_calibration


def _document():
    return {
        "schema_version": 1,
        "updated_at": "2026-10-27T10:00:00Z",
        "browser": {
            "label": "Test browser",
            "frame_probe": {
                "duration_ms": 10000,
                "average_fps": 48.0,
                "median_fps": 48.0,
                "p95_frame_interval_ms": 22.0,
                "document_visibility": "visible",
            },
        },
        "runs": [
            {"run_id": "650", "board_item_type": "BoardItem2", "board_point_limit": 6000, "point_step_px": 2.0, "point_delay_ms": 10, "scenario_id": "length_650", "stroke_length_px": 650, "planned_strokes": 40, "planned_path_length_px": 26000, "outcome": "partial", "last_visible_strokes": 39, "fresh_supply_confirmed": True},
            {"run_id": "200", "board_item_type": "BoardItem2", "board_point_limit": 6000, "point_step_px": 2.0, "point_delay_ms": 10, "scenario_id": "length_200", "stroke_length_px": 200, "planned_strokes": 130, "planned_path_length_px": 26000, "outcome": "partial", "last_visible_strokes": 124, "fresh_supply_confirmed": True},
            {"run_id": "50", "board_item_type": "BoardItem2", "board_point_limit": 6000, "point_step_px": 2.0, "point_delay_ms": 10, "scenario_id": "length_50", "stroke_length_px": 50, "planned_strokes": 520, "planned_path_length_px": 26000, "outcome": "partial", "last_visible_strokes": 454, "fresh_supply_confirmed": True},
            {"run_id": "10", "board_item_type": "BoardItem2", "board_point_limit": 6000, "point_step_px": 2.0, "point_delay_ms": 10, "scenario_id": "length_10", "stroke_length_px": 10, "planned_strokes": 2600, "planned_path_length_px": 26000, "outcome": "partial", "last_visible_strokes": 1537, "fresh_supply_confirmed": True},
        ],
    }


def test_historical_series_produces_finite_positive_point_model():
    report = analyze_game_point_calibration(_document())
    assert report["input_run_count"] == 4
    assert report["fit_eligible_run_count"] == 4
    assert len(report["models"]) == 1
    model = report["models"][0]
    assert model["fit_status"] in {"calibrated", "needs_repeat"}
    assert model["points_per_path_px"] > 0
    assert model["points_per_stroke"] > 0
    assert model["equivalent_path_overhead_px_per_stroke"] > 0
    assert model["theoretical_points_per_path_px_from_measured_fps"] == 0.24
    assert model["maximum_fit_error_percent_of_quota"] < 10


def test_all_visible_runs_are_not_used_as_exact_cutoff_observations():
    document = _document()
    document["runs"][0]["outcome"] = "all_visible"
    document["runs"][0]["last_visible_strokes"] = None
    report = analyze_game_point_calibration(document)
    assert report["fit_eligible_run_count"] == 3
    assert any(item["run_id"] == "650" for item in report["excluded_runs"])


def test_non_comparable_supply_is_excluded_from_fit():
    document = _document()
    document["runs"][0]["fresh_supply_confirmed"] = False
    report = analyze_game_point_calibration(document)
    assert report["fit_eligible_run_count"] == 3
    assert any("сопоставимый" in item["reason"] for item in report["excluded_runs"])


def test_hidden_tab_frame_probe_is_rejected():
    document = _document()
    document["browser"]["frame_probe"]["document_visibility"] = "hidden"
    with pytest.raises(GamePointCalibrationError, match="скрыта"):
        analyze_game_point_calibration(document)


def test_board_point_limit_must_match_engine_board_type():
    document = _document()
    document["runs"][0]["board_point_limit"] = 3000
    with pytest.raises(GamePointCalibrationError, match="не соответствует"):
        analyze_game_point_calibration(document)


def test_same_stroke_length_does_not_claim_a_calibrated_fit():
    document = _document()
    for run in document["runs"]:
        run["stroke_length_px"] = 50
        run["visible_path_length_px"] = run["last_visible_strokes"] * 50
    report = analyze_game_point_calibration(document)
    assert report["models"][0]["fit_status"] == "underdetermined"

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
                "schema_version": 2,
                "probe_status": "completed",
                "duration_ms": 10000,
                "wall_clock_elapsed_ms": 10004,
                "frame_count": 480,
                "average_fps": 48.0,
                "median_fps": 48.0,
                "median_frame_interval_ms": 20.833,
                "p95_frame_interval_ms": 22.0,
                "max_frame_interval_ms": 28.0,
                "document_visibility": "visible",
                "visibility_change_count": 0,
                "visibility_interrupted": False,
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
    assert report["schema_version"] == 2
    assert report["model_id"] == "browser-observed-game-point-calibration-v2-interval"
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
    assert model["fitting_method"] == "interval_constrained_least_squares_v1"
    assert model["interval_fit"]["status"] == "feasible"
    assert model["interval_fit"]["feasible_vertex_count"] > 0
    assert model["midpoint_reference_coefficients"]["points_per_path_px"] > 0
    assert model["all_cutoff_intervals_consistent"] is True
    assert model["cutoff_interval_consistent_run_count"] == 4
    assert all(run["cutoff_interval_contains_quota"] for run in model["per_run_fit"])


def test_all_visible_runs_are_not_used_as_exact_cutoff_observations():
    document = _document()
    document["runs"][0]["outcome"] = "all_visible"
    document["runs"][0]["last_visible_strokes"] = None
    document["runs"][0]["visible_path_length_px"] = document["runs"][0]["planned_path_length_px"]
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


def test_partial_result_cannot_report_zero_visible_strokes():
    document = _document()
    document["runs"][0]["last_visible_strokes"] = 0
    document["runs"][0]["visible_path_length_px"] = 0
    with pytest.raises(GamePointCalibrationError, match="не меньше 1"):
        analyze_game_point_calibration(document)


def test_visible_path_must_match_fully_visible_stroke_count():
    document = _document()
    document["runs"][0]["visible_path_length_px"] = 25200
    with pytest.raises(GamePointCalibrationError, match="не согласуется"):
        analyze_game_point_calibration(document)


def test_planned_path_must_match_stroke_count_and_length():
    document = _document()
    document["runs"][0]["planned_path_length_px"] = 25000
    with pytest.raises(GamePointCalibrationError, match="planned_strokes"):
        analyze_game_point_calibration(document)


def test_probe_that_was_hidden_then_shown_is_rejected():
    document = _document()
    document["browser"]["frame_probe"]["visibility_interrupted"] = True
    with pytest.raises(GamePointCalibrationError, match="прерван"):
        analyze_game_point_calibration(document)


def test_old_probe_schema_is_rejected():
    document = _document()
    document["browser"]["frame_probe"]["schema_version"] = 1
    with pytest.raises(GamePointCalibrationError, match="должна быть 2"):
        analyze_game_point_calibration(document)


def test_inconsistent_frame_metrics_are_rejected():
    document = _document()
    document["browser"]["frame_probe"]["frame_count"] = 100
    with pytest.raises(GamePointCalibrationError, match="не согласуются"):
        analyze_game_point_calibration(document)


def test_duplicate_run_ids_are_rejected():
    document = _document()
    document["runs"][1]["run_id"] = document["runs"][0]["run_id"]
    with pytest.raises(GamePointCalibrationError, match="Повторяется run_id"):
        analyze_game_point_calibration(document)


def test_fresh_supply_must_be_an_explicit_boolean():
    document = _document()
    document["runs"][0]["fresh_supply_confirmed"] = "true"
    with pytest.raises(GamePointCalibrationError, match="должен быть true/false"):
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
        run["planned_path_length_px"] = run["planned_strokes"] * 50
        run["visible_path_length_px"] = run["last_visible_strokes"] * 50
    report = analyze_game_point_calibration(document)
    assert report["models"][0]["fit_status"] == "underdetermined"

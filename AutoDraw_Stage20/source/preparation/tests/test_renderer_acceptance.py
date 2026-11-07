from __future__ import annotations

import pytest

from renderer_acceptance import (
    EXPECTED_EXECUTOR_CONFIG,
    EXPECTED_PAIRED_AXIS_SOURCES,
    evaluate_per_run_acceptance,
    summarize_multi_axis_series,
    validate_paired_capture,
    validate_renderer_comparison,
    validate_transform_geometry,
)


def _passing_transform(scenario):
    axes = EXPECTED_PAIRED_AXIS_SOURCES[scenario]
    origin = {"x": 100.0, "y": 200.0}
    scale = {"x": 1.5, "y": 1.5}
    fits = {"x": None, "y": None}
    cross = {}
    for axis in ("x", "y"):
        cross[f"inspect_{axis}_origin_difference_px"] = 0.1
        cross[f"inspect_{axis}_scale_relative_difference"] = 0.0001
        cross[f"monitor_{axis}_origin_difference_px"] = 0.1
        cross[f"monitor_{axis}_scale_relative_difference"] = 0.0001
        if axes[axis] == "same_run_monitor_fit":
            fits[axis] = {"origin": origin[axis], "scale": scale[axis], "max_abs_residual_px": 0.1}
    return {
        "axis_sources": axes,
        "validation_status": "both_axes_cross_checked_with_inspect_and_same_run_screenshot_bounds",
        "screen_offset_range_px": {"x": 0.0, "y": 0.0},
        "axis_max_abs_residual_px": {"x": 0.1, "y": 0.1},
        "inspect_origin": origin,
        "inspect_scale": scale,
        "screenshot_bounds_cross_check": cross,
        "horizontal_fit": fits["x"],
        "vertical_fit": fits["y"],
    }


@pytest.mark.parametrize("scenario", list(EXPECTED_PAIRED_AXIS_SOURCES))
def test_transform_gate_accepts_expected_axis_sources(scenario):
    result = validate_transform_geometry(_passing_transform(scenario), scenario)
    assert result["passed"] is True, result["failed_checks"]


def test_transform_gate_rejects_offset_range_over_threshold():
    geometry = _passing_transform("paired_renderer_diagonal_single_stroke")
    geometry["screen_offset_range_px"]["x"] = 0.02
    result = validate_transform_geometry(geometry, "paired_renderer_diagonal_single_stroke")
    assert result["passed"] is False
    assert "client_screen_offset_range_x" in result["failed_checks"]


def _renderer_metrics():
    return {
        "iou": 0.998,
        "precision": 0.998,
        "recall": 0.999,
        "symmetric_difference_pixels": 10,
        "observed_bbox_xywh": [20, 30, 100, 12],
        "expected_bbox_xywh": [20, 30, 100, 12],
    }


def test_renderer_gate_applies_92_percent_thresholds():
    accepted = validate_renderer_comparison(_renderer_metrics(), 10000)
    assert accepted["passed"] is True
    assert accepted["symmetric_difference_fraction"] == pytest.approx(0.001)
    assert accepted["thresholds"]["iou_min"] == 0.92
    assert accepted["thresholds"]["precision_min"] == 0.92
    assert accepted["thresholds"]["recall_min"] == 0.92
    assert accepted["thresholds"]["symmetric_difference_fraction_max"] == 0.087
    assert accepted["thresholds"]["bbox_edge_difference_fraction_max"] == 0.08

    # Consistent confusion matrix: TP=10,000, FP=0, FN=869.
    # Therefore precision=1, while IoU=recall=10,000/10,869.
    boundary_iou_recall = 10000 / 10869
    boundary = _renderer_metrics() | {
        "iou": boundary_iou_recall,
        "precision": 1.0,
        "recall": boundary_iou_recall,
        "symmetric_difference_pixels": 869,
    }
    boundary_result = validate_renderer_comparison(boundary, 10000)
    assert boundary_result["passed"] is True
    assert boundary_result["symmetric_difference_fraction"] == pytest.approx(0.0869)

    rejected = validate_renderer_comparison(_renderer_metrics() | {"iou": 0.919}, 10000)
    assert rejected["passed"] is False
    assert "iou_alpha_24" in rejected["failed_checks"]


def test_renderer_gate_uses_scaled_bbox_edge_tolerance():
    metrics = _renderer_metrics() | {
        "observed_bbox_xywh": [20, 30, 100, 12],
        "expected_bbox_xywh": [28, 30, 100, 12],
    }
    accepted = validate_renderer_comparison(metrics, 10000)
    assert accepted["passed"] is True
    assert accepted["bbox_edge_differences_px"] == [8, 0, 8, 0]
    assert accepted["bbox_edge_tolerances_px"] == [8, 1, 8, 1]

    rejected = validate_renderer_comparison(
        metrics | {"expected_bbox_xywh": [29, 30, 100, 12]}, 10000,
    )
    assert rejected["passed"] is False
    assert "bbox_edges_alpha_24" in rejected["failed_checks"]


def test_renderer_gate_rejects_missing_bbox_and_empty_live_mask():
    metrics = _renderer_metrics() | {"observed_bbox_xywh": None}
    result = validate_renderer_comparison(metrics, 1000)
    assert result["passed"] is False
    assert "bbox_edges_alpha_24" in result["failed_checks"]
    result = validate_renderer_comparison(_renderer_metrics(), 0)
    assert "symmetric_difference_fraction_alpha_24" in result["failed_checks"]


def _capture_fixture(scenario="paired_renderer_vertical_single_stroke"):
    experiment_id, run_id, session_id = "exp-1", "run-1", "session-1"
    stroke_id = "stroke-1"
    if scenario == "paired_renderer_vertical_single_stroke":
        points = [{"x": 230.0, "y": value} for value in (30, 40, 60, 80)]
        samples = [(230.0, value) for value in (30, 40, 60, 80)]
    elif scenario == "paired_renderer_diagonal_single_stroke":
        points = [{"x": value, "y": value / 2} for value in (30, 40, 60, 80)]
        samples = [(value, value / 2) for value in (30, 40, 60, 80)]
    else:
        points = [{"x": value, "y": 120.0} for value in (30, 40, 60, 80)]
        samples = [(value, 120.0) for value in (30, 40, 60, 80)]

    events = [
        {"type": "POINTER_DOWN_CANDIDATE", "strokeId": stroke_id},
        {"type": "DRAW_SAMPLE", "strokeId": stroke_id, "source": "onDrawStart", "pointDelta": 0},
    ]
    for point in points:
        events.extend([
            {"type": "POINT_QUOTA_UPDATE", "strokeId": stroke_id, "pointDelta": 1, "acceptedPoint": point},
            {"type": "DRAW_SAMPLE", "strokeId": stroke_id, "source": "onDrawing_wrapper",
             "pointDelta": 1, "acceptedPoint": point},
        ])
    for x, y in samples:
        events.append({"type": "MOUSE_MOVE_SAMPLE", "strokeId": stroke_id, "boardX": x, "boardY": y})
    events.append({"type": "POINTER_UP_CANDIDATE", "strokeId": stroke_id})

    pre = {"pointCount": 100, "validationStatus": "valid", "isExact": True,
           "logicalWidth": 460, "logicalHeight": 240, "currentRadius": 10}
    post = {"pointCount": 104, "validationStatus": "valid", "isExact": True,
            "logicalWidth": 460, "logicalHeight": 240, "currentRadius": 10}
    return {
        "experiment": {
            "experiment_id": experiment_id,
            "test_case": scenario,
            "brush_value_requested": 10,
            "game_monitor_summary": {
                "autodraw_experiment_id": experiment_id,
                "run_id": run_id, "session_id": session_id,
                "brush_radius": 10, "observed_brush_radii": [10], "brush_radius_status": "single",
                "chalk": {"status": "exact", "pre_point_count": 100, "post_point_count": 104,
                          "consumed_points": 4},
                "sampled_point_delta_total": 4, "point_delta_matches_chalk": True, "stroke_count": 1,
                "dropped_events": 0, "monitor_dropped_events": 0,
                "monitor_buffer_dropped_events_delta": 0, "monitor_error_count_delta": 0,
                "bridge_send_failures_delta": 0, "collector_sequence_gap_count": 0,
                "monitor_error_count": 0,
            },
            "execution_report": {
                "status": "completed", "completed_strokes": 1, "total_strokes": 1,
                "error": None, "stop_reason": None,
                "mouse_release": {"succeeded": True},
                "executor_config": dict(EXPECTED_EXECUTOR_CONFIG),
            },
            "monitor_capture": {
                "status": "saved", "experiment_id": experiment_id,
                "run_id": run_id, "session_id": session_id,
                "chalk_status": "exact", "chalk_counter_consistent": True,
                "point_delta_matches_chalk": True, "brush_radius_status": "single",
                "stroke_count": 1, "expected_stroke_count": 1,
            },
            "phases": {
                "before_clear": {"status": "restored_within_pixel_tolerance"},
                "before_draw": {"captured_at_utc": "2026-11-05T00:00:00Z",
                                "screen_size": {"width": 1920, "height": 1080},
                                "clear_check": {"status": "restored_within_pixel_tolerance"},
                                "files": {"full_screen": "before.png"}},
                "after_draw": {"captured_at_utc": "2026-11-05T00:00:01Z",
                               "screen_size": {"width": 1920, "height": 1080},
                               "files": {"full_screen": "after.png"}},
            },
        },
        "monitor": {
            "record_type": "autodraw_game_monitor_run",
            "autodraw_experiment_id": experiment_id,
            "run_id": run_id, "session_id": session_id,
            "pre_test_snapshot": pre, "post_test_snapshot": post,
            "brush_radius": 10, "events": events,
            "stroke_count": 1, "stroke_candidate_count": 1,
            "non_consuming_stroke_candidate_count": 0, "monitor_errors": [],
            "dropped_events": 0, "monitor_dropped_events": 0,
            "monitor_buffer_dropped_events_start": 0, "monitor_buffer_dropped_events_end": 0,
            "monitor_buffer_dropped_events_delta": 0, "monitor_error_count_start": 0,
            "monitor_error_count_end": 0, "monitor_error_count_delta": 0,
            "bridge_send_failures_start": 0, "bridge_send_failures_end": 0,
            "bridge_send_failures_delta": 0, "collector_sequence_gap_count": 0,
            "monitor_error_count": 0,
        },
        "plan": {
            "generation": {
                "experiment_id": experiment_id, "test_case": scenario,
                "requested_brush_value": 10,
                "paired_renderer_capture": {
                    "schema_version": 1, "scenario_id": scenario, "requested_radius": 10,
                    "expected_strokes": 1, "renderer_path_mode": "smooth",
                    "executor_parameters": dict(EXPECTED_EXECUTOR_CONFIG),
                },
            },
            "strokes": [{"points": [{"x": 230, "y": 30}, {"x": 230, "y": 80}]}],
        },
        "fixture": {"sourceRunId": run_id, "mode": "smooth", "lineWidth": 10, "points": points},
    }


@pytest.mark.parametrize("scenario", list(EXPECTED_PAIRED_AXIS_SOURCES))
def test_paired_capture_gate_accepts_complete_evidence(scenario):
    data = _capture_fixture(scenario)
    result = validate_paired_capture(
        data["experiment"], data["monitor"], data["plan"], data["fixture"],
    )
    assert result["passed"] is True, result["failed_checks"]


def test_paired_capture_gate_accepts_state_poll_fallback_sample_when_it_matches_quota():
    data = _capture_fixture()
    fallback = next(
        event for event in data["monitor"]["events"]
        if event["type"] == "DRAW_SAMPLE" and event.get("source") == "onDrawing_wrapper"
    )
    fallback["source"] = "state_poll"
    result = validate_paired_capture(
        data["experiment"], data["monitor"], data["plan"], data["fixture"],
    )
    assert result["passed"] is True, result["failed_checks"]


def test_paired_capture_gate_rejects_missing_accepted_point():
    data = _capture_fixture()
    data["monitor"]["events"] = [
        event for event in data["monitor"]["events"]
        if not (event["type"] == "DRAW_SAMPLE" and event.get("source") == "onDrawing_wrapper")
    ]
    result = validate_paired_capture(
        data["experiment"], data["monitor"], data["plan"], data["fixture"],
    )
    assert result["passed"] is False
    assert "complete_accepted_point_stream" in result["failed_checks"]


def test_paired_capture_gate_rejects_run_binding_mismatch():
    data = _capture_fixture()
    data["monitor"]["run_id"] = "different-run"
    result = validate_paired_capture(
        data["experiment"], data["monitor"], data["plan"], data["fixture"],
    )
    assert result["passed"] is False
    assert "run_session_binding" in result["failed_checks"]


def test_per_run_gate_and_series_gate_are_separate():
    passed = evaluate_per_run_acceptance({"passed": True}, {"passed": True}, {"passed": True})
    failed = evaluate_per_run_acceptance({"passed": True}, {"passed": False}, {"passed": True})
    assert passed["status"] == "PASS_PER_RUN"
    assert failed["status"] == "REJECTED_PER_RUN"


def _series_report(scenario, run_id, status="PASS_PER_RUN"):
    return {
        "scenario_id": scenario, "run_id": run_id, "experiment_id": f"exp-{run_id}",
        "formal_acceptance": {"status": status},
    }


def test_multi_axis_series_requires_three_unique_passes_per_orientation():
    vertical = "paired_renderer_vertical_single_stroke"
    diagonal = "paired_renderer_diagonal_single_stroke"
    reports = [
        _series_report(vertical, "v1"), _series_report(vertical, "v2"), _series_report(vertical, "v3"),
        _series_report(diagonal, "d1"), _series_report(diagonal, "d2"), _series_report(diagonal, "d3"),
    ]
    result = summarize_multi_axis_series(reports)
    assert result["status"] == "PASS"


def test_multi_axis_series_retains_rejects_and_ignores_duplicates():
    vertical = "paired_renderer_vertical_single_stroke"
    reports = [
        _series_report(vertical, "v1"), _series_report(vertical, "v1"),
        _series_report(vertical, "v2", "REJECTED_PER_RUN"),
    ]
    result = summarize_multi_axis_series(reports)
    assert result["status"] == "PENDING"
    assert result["orientations"][vertical]["duplicate_run_ids"] == ["v1"]
    assert result["orientations"][vertical]["rejected_runs"][0]["run_id"] == "v2"
    assert result["orientations"][vertical]["missing_valid_repeats"] == 2


def test_multi_axis_series_rejects_invalid_repeat_count():
    with pytest.raises(ValueError):
        summarize_multi_axis_series([], required_repeats=0)



def test_renderer_comparison_supports_explicit_screen_rgb_metric_names():
    metrics = {
        "iou": 0.998,
        "precision": 0.998,
        "recall": 0.999,
        "symmetric_difference_pixels": 10,
        "observed_bbox_xywh": [10, 20, 100, 10],
        "expected_bbox_xywh": [10, 20, 100, 10],
    }
    result = validate_renderer_comparison(
        metrics, 10000, metric_suffix="screen_rgb_delta_24",
    )
    assert result["status"] == "PASS"
    assert "iou_screen_rgb_delta_24" in result["checks"]
    assert "precision_screen_rgb_delta_24" in result["checks"]
    assert "recall_screen_rgb_delta_24" in result["checks"]
    assert "symmetric_difference_fraction_screen_rgb_delta_24" in result["checks"]
    assert "bbox_edges_screen_rgb_delta_24" in result["checks"]

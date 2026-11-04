from __future__ import annotations

from source.preparation.game_input_sampling_analysis import analyze_run


def _event(event_type: str, t: float, **values):
    return {"type": event_type, "t": t, "strokeId": "stroke-1", **values}


def test_correlates_accepted_points_with_latest_preceding_mousemove():
    run = {
        "run_id": "run-1",
        "session_id": "session-1",
        "events": [
            _event("POINTER_DOWN_CANDIDATE", 9),
            _event("MOUSE_MOVE_SAMPLE", 10, domEventTimeStamp=9.8, stageX=10, stageY=20, boardX=1, boardY=2),
            _event("MOUSE_MOVE_SAMPLE", 11, domEventTimeStamp=10.8, stageX=11, stageY=20, boardX=2, boardY=2),
            _event("POINT_QUOTA_UPDATE", 12, pointDelta=1, acceptedPoint={"x": 2, "y": 2},
                   stageX=11, stageY=20, boardX=2, boardY=2),
            _event("MOUSE_MOVE_SAMPLE", 14, domEventTimeStamp=13.8, stageX=12, stageY=20, boardX=3, boardY=2),
            _event("POINT_QUOTA_UPDATE", 16, pointDelta=1, acceptedPoint={"x": 3, "y": 2},
                   stageX=12, stageY=20, boardX=3, boardY=2),
            _event("POINTER_UP_CANDIDATE", 17),
        ],
        "frame_probes": [{"stroke_id": "stroke-1", "intervals": [16.6, 16.7]}],
        "sampled_point_delta_total": 2,
        "point_delta_matches_chalk": True,
    }
    session = {"monitor_status_at_connect": {"version": "0.2.2", "inputTelemetryEnabled": True}}

    report = analyze_run(run, session)
    stroke = report["per_stroke"][0]
    assert report["input_telemetry_status"] == "enabled"
    assert report["point_quota_delta_total"] == 2
    assert stroke["mouse_move_sample_count"] == 3
    assert stroke["positive_point_quota_update_count"] == 2
    assert stroke["unmatched_mousemoves_between_accepts"] == 1
    assert stroke["trailing_mousemove_count"] == 0
    assert stroke["input_to_accept_ms"]["median"] == 1.5
    assert stroke["matches"][0]["match"] == "latest_preceding_mousemove"
    assert stroke["matches"][0]["input_board"] == {"x": 2, "y": 2}
    assert report["browser_raf_interval_ms"]["count"] == 2


def test_marks_point_delta_above_one_as_missing_intermediate_coordinates():
    run = {
        "events": [
            _event("MOUSE_MOVE_SAMPLE", 10, stageX=10, stageY=20),
            _event("POINT_QUOTA_UPDATE", 12, pointDelta=3, acceptedPoint={"x": 12, "y": 20}),
        ]
    }
    report = analyze_run(run)
    stroke = report["per_stroke"][0]
    assert stroke["point_delta_gt_one_update_count"] == 1
    assert stroke["unobserved_intermediate_point_count"] == 2


def test_legacy_run_without_input_telemetry_is_not_misclassified_as_zero_input():
    run = {
        "events": [
            {"type": "DRAW_SAMPLE", "t": 10, "strokeId": "stroke-1", "pointDelta": 1}
        ]
    }
    session = {"monitor_status_at_connect": {"version": "0.2.1"}}
    report = analyze_run(run, session)
    assert report["input_telemetry_status"] == "unsupported_monitor_version"
    assert report["event_counts"]["MOUSE_MOVE_SAMPLE"] == 0


def test_explicitly_disabled_input_telemetry_is_reported():
    report = analyze_run(
        {"events": []},
        {"monitor_status_at_connect": {"version": "0.2.2", "inputTelemetryEnabled": False}}
    )
    assert report["input_telemetry_status"] == "disabled"


def test_rejects_missing_events_array():
    try:
        analyze_run({})
    except ValueError as error:
        assert "events array" in str(error)
    else:
        raise AssertionError("Expected ValueError for a missing events array.")



def test_reports_input_events_observed_even_if_connect_snapshot_was_disabled():
    run = {
        "events": [
            _event("MOUSE_MOVE_SAMPLE", 10, stageX=10, stageY=20),
        ]
    }
    session = {"monitor_status_at_connect": {"version": "0.2.2", "inputTelemetryEnabled": False}}
    report = analyze_run(run, session)
    assert report["input_telemetry_status"] == "observed_after_connect_or_status_conflict"


def test_enabled_telemetry_without_mouse_events_is_not_reported_as_observed():
    report = analyze_run(
        {"events": []},
        {"monitor_status_at_connect": {"version": "0.2.2", "inputTelemetryEnabled": True}}
    )
    assert report["input_telemetry_status"] == "enabled_no_samples"

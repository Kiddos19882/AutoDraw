from brush_radius_feedback import (
    calculate_radius_correction_target,
    monitor_radius_from_status,
    read_active_bridge_geometry,
)


def test_monitor_radius_prefers_current_radius_scalar():
    assert monitor_radius_from_status({
        "snapshot": {"currentRadius": 4, "radius": [30, 4]}
    }) == 4


def test_monitor_radius_supports_radius_array_fallback():
    assert monitor_radius_from_status({"snapshot": {"radius": [30, 5]}}) == 5


def test_monitor_radius_rejects_unavailable_and_invalid_values():
    assert monitor_radius_from_status({"snapshot": None}) is None
    assert monitor_radius_from_status({"snapshot": {"currentRadius": 0}}) is None
    assert monitor_radius_from_status({"snapshot": {"currentRadius": True}}) is None


def test_radius_feedback_moves_towards_30_when_observed_radius_is_too_small():
    target = calculate_radius_correction_target(
        high_point=(100, 500), high_radius=30,
        low_point=(390, 500), low_radius=4,
        requested_radius=5,
    )
    assert 100 < target[0] < 390
    assert target[0] < 390


def test_radius_feedback_moves_towards_1_when_observed_radius_is_too_large():
    target = calculate_radius_correction_target(
        high_point=(200, 500), high_radius=6,
        low_point=(390, 500), low_radius=1,
        requested_radius=5,
    )
    assert 200 < target[0] < 390


def test_radius_feedback_returns_known_endpoint_for_radius_one_or_thirty():
    assert calculate_radius_correction_target((100, 500), 30, (390, 500), 1, 30) == (100, 500)
    assert calculate_radius_correction_target((100, 500), 30, (390, 500), 1, 1) == (390, 500)


def test_radius_feedback_rejects_invalid_bracket():
    import pytest
    with pytest.raises(ValueError):
        calculate_radius_correction_target((100, 500), 4, (390, 500), 1, 5)


def test_active_bridge_geometry_returns_client_corners_without_claiming_screen_mapping(tmp_path):
    import json
    from datetime import datetime, timezone

    session_dir = tmp_path / "session-geometry"
    session_dir.mkdir()
    stamp = datetime.now(timezone.utc).isoformat()
    record = {
        "schema_version": 2,
        "session_id": "session-geometry",
        "renderer_geometry_updated_at_utc": stamp,
        "renderer_geometry": {
            "windowGeometry": {"screenWidth": 1920, "screenHeight": 1080},
            "players": [{
                "boardStageCorners": {"topLeft": {"x": 340, "y": 72}},
                "boardClientCorners": {"topLeft": {"x": 498, "y": 105}},
                "boardClientMappingMethod": "validated_axis_aligned_rect",
            }],
        },
        "bridge_diagnostics": {
            "connection_closed": False,
            "last_message_at_utc": stamp,
            "last_message_type": "heartbeat",
        },
    }
    (session_dir / "session.json").write_text(json.dumps(record), encoding="utf-8")

    result = read_active_bridge_geometry(tmp_path)
    assert result is not None
    assert result["session_id"] == "session-geometry"
    assert result["board_detected"] is True
    assert result["board_client_mapping_method"] == "validated_axis_aligned_rect"
    assert result["board_client_corners"]["topLeft"] == {"x": 498, "y": 105}
    assert result["coordinate_space"] == "css_client_pixels"
    assert result["desktop_screen_mapping_available"] is False
    assert result["executor_usable"] is False


def test_active_bridge_geometry_rejects_closed_or_stale_sessions(tmp_path):
    import json
    from datetime import datetime, timedelta, timezone

    session_dir = tmp_path / "session-stale"
    session_dir.mkdir()
    old_stamp = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
    record = {
        "session_id": "session-stale",
        "renderer_geometry": {"players": []},
        "bridge_diagnostics": {
            "connection_closed": False,
            "last_message_at_utc": old_stamp,
        },
    }
    path = session_dir / "session.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    assert read_active_bridge_geometry(tmp_path, max_age_seconds=4) is None

    record["bridge_diagnostics"]["connection_closed"] = True
    record["bridge_diagnostics"]["last_message_at_utc"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(record), encoding="utf-8")
    assert read_active_bridge_geometry(tmp_path, max_age_seconds=4) is None

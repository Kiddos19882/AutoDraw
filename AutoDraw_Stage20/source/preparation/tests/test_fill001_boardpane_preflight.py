from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json

import pytest

from fill001_boardpane_preflight import (
    PreflightGeometryError, boardpane_preflight_transform,
)

NOW = datetime(2026, 11, 8, 18, 0, 0, tzinfo=timezone.utc)
SESSION_ID = "preflight-new-session"


def fixture():
    board = {
        "engineVersion": "5.4.1", "renderMode": "webgl",
        "boardLogicalSize": {"width": 460, "height": 240},
        "players": [{
            "boardClientMappingMethod": "validated_axis_aligned_rect",
            "boardStageCorners": {
                "topLeft": {"x": 340.7916660308838, "y": 72},
                "topRight": {"x": 800.7916660308838, "y": 72},
                "bottomRight": {"x": 800.7916660308838, "y": 312},
                "bottomLeft": {"x": 340.7916660308838, "y": 312}},
            "boardClientCorners": {
                "topLeft": {"x": 497.9604252506065, "y": 104.86},
                "topRight": {"x": 1170.1065439720678, "y": 104.86},
                "bottomRight": {"x": 1170.1065439720678, "y": 456.06},
                "bottomLeft": {"x": 497.9604252506065, "y": 456.06}},
        }],
    }
    session = {
        "session_id": SESSION_ID, "renderer_geometry": board,
        "bridge_configuration": {"inputTelemetry": {"requested": True, "enabled": True}},
        "bridge_diagnostics": {
            "connection_closed": False,
            "last_heartbeat_at_utc": (NOW-timedelta(seconds=1)).isoformat(),
            "last_monitor_status": {
                "version": "0.2.4", "active": True, "boardDetected": True,
                "inputTelemetryEnabled": True, "engineFrameObserverConnected": True,
            },
        },
    }
    sha = hashlib.sha256(json.dumps(board, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False).encode()).hexdigest()
    samples = []
    for x,y in [(600.0,180.0),(800.0,245.0),(1000.0,350.0)]:
        samples.append({
            "type": "BOARD_SCREEN_PREFLIGHT_SAMPLE",
            "source": "window-bubble-after-egret-canvas",
            "session_id": SESSION_ID, "renderer_geometry_sha256": sha,
            "buttons": 0, "pre_drawing": True,
            "captured_at_utc": (NOW-timedelta(seconds=1)).isoformat(),
            "clientX": x, "clientY": y, "screenX": x, "screenY": y+163,
        })
    plan = {
        "coordinate_system": "logical_board_pixels",
        "canvas": {"width": 460, "height": 240},
        "strokes": [{
            "name": "first", "points": [{"x":94,"y":55},{"x":366,"y":55}],
            "closed": False, "metadata": {},
        }],
        "generation": {},
    }
    roi = {"x": 496, "y": 265, "width": 674, "height": 355}
    return plan, roi, session, samples


def call_with(plan=None, roi=None, session=None, samples=None, *, now=NOW, sid=SESSION_ID):
    a, b, c, d = fixture()
    return boardpane_preflight_transform(
        plan if plan is not None else a,
        roi if roi is not None else b,
        session if session is not None else c,
        samples if samples is not None else d,
        expected_session_id=sid, now_utc=now,
    )


def test_preflight_maps_to_actual_boardpane_not_roi_and_preserves_source():
    plan, roi, session, samples = fixture()
    original = deepcopy(plan)
    mapped, binding = call_with(plan, roi, session, samples)
    assert plan == original
    first, last = mapped["strokes"][0]["points"]
    assert first["y"] == pytest.approx(267.86 + 55*(351.2/240)-265)
    assert first["x"] == pytest.approx(497.9604252506065 + 94*((1170.1065439720678-497.9604252506065)/460)-496)
    assert last["x"] > first["x"]
    assert binding["no_fallback"] is True
    assert binding["client_to_desktop_offset"] == {"x":0, "y":163}
    assert binding["status"] == "validated_preflight_input_transform_not_live_draw"
    assert mapped["generation"]["screen_transform"] == binding


@pytest.mark.parametrize("fault,needle", [
    ("session", "session identity"), ("stale", "stale or future"),
    ("heartbeat", "stale or future"), ("no_samples", "three passive"),
    ("old_draw_sample", "type/source/run/geometry"),
    ("bad_source", "type/source/run/geometry"),
    ("wrong_sha", "type/source/run/geometry"),
    ("buttons", "type/source/run/geometry"),
    ("outside", "outside BoardPane"),
    ("nonuniform_offset", "mapping changed"),
    ("unverified_mapping", "unvalidated"), ("renderer_changed", "Egret version"),
    ("nonuniform_board", "type/source/run/geometry"), ("outside_roi", "outside executor ROI"),
])
def test_fail_closed_when_evidence_is_missing_stale_or_geometry_changed(fault, needle):
    plan, roi, session, samples = fixture()
    if fault == "session":
        session["session_id"] = "previous-session"
    elif fault == "stale":
        samples[0]["captured_at_utc"] = (NOW-timedelta(minutes=1)).isoformat()
    elif fault == "heartbeat":
        session["bridge_diagnostics"]["last_heartbeat_at_utc"] = (NOW-timedelta(minutes=1)).isoformat()
    elif fault == "no_samples":
        samples.pop()
    elif fault == "old_draw_sample":
        samples[0]["type"] = "MOUSE_MOVE_SAMPLE"
    elif fault == "bad_source":
        samples[0]["source"] = "plan_derived"
    elif fault == "wrong_sha":
        samples[0]["renderer_geometry_sha256"] = "0"*64
    elif fault == "buttons":
        samples[0]["buttons"] = 1
    elif fault == "outside":
        samples[0]["clientX"] = 100
    elif fault == "nonuniform_offset":
        samples[0]["screenY"] += 2
    elif fault == "unverified_mapping":
        session["renderer_geometry"]["players"][0]["boardClientMappingMethod"] = "guessed"
    elif fault == "renderer_changed":
        session["renderer_geometry"]["engineVersion"] = "5.4.0"
    elif fault == "nonuniform_board":
        session["renderer_geometry"]["players"][0]["boardClientCorners"]["bottomRight"]["y"] = 500
        session["renderer_geometry"]["players"][0]["boardClientCorners"]["bottomLeft"]["y"] = 500
    elif fault == "outside_roi":
        roi["x"] = 0
    with pytest.raises(PreflightGeometryError, match=needle):
        call_with(plan, roi, session, samples)


def test_never_reuses_past_monitor_mouse_samples_or_screen_offset():
    plan, roi, session, samples = fixture()
    for sample in samples:
        sample["type"] = "MOUSE_MOVE_SAMPLE"
        sample["pre_drawing"] = False
    with pytest.raises(PreflightGeometryError):
        call_with(plan, roi, session, samples)


def test_invalid_logical_coordinates_and_nonfinite_values_fail():
    plan, roi, session, samples = fixture()
    plan["strokes"][0]["points"][0]["y"] = float("nan")
    with pytest.raises(PreflightGeometryError, match="finite"):
        call_with(plan, roi, session, samples)
    plan["strokes"][0]["points"][0]["y"] = 241
    with pytest.raises(PreflightGeometryError, match="outside board"):
        call_with(plan, roi, session, samples)


def test_coherently_rehashed_nonuniform_board_still_fails_scale_gate():
    plan, roi, session, samples = fixture()
    corners = session["renderer_geometry"]["players"][0]["boardClientCorners"]
    corners["bottomRight"]["y"] = 500
    corners["bottomLeft"]["y"] = 500
    sha = hashlib.sha256(json.dumps(session["renderer_geometry"], sort_keys=True,
                                  separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    for sample in samples:
        sample["renderer_geometry_sha256"] = sha
    with pytest.raises(PreflightGeometryError, match="uniformly scaled"):
        call_with(plan, roi, session, samples)

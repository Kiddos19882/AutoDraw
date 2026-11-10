from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json

import pytest

from fill001_monitor_diagnostic import _boardpane_mapping_fingerprint
from fill001_boardpane_preflight import PreflightGeometryError
from fill001_v5_handoff import build_fill001_v5_source_plan
from fill001_v5_auto_roi import derive_v5_roi_from_verified_passive_moves

NOW = datetime(2026, 11, 10, 0, 0, tzinfo=timezone.utc)
SID = "single-current-v5-game-session"


def build_fixture():
    board = {
        "engineVersion": "5.4.1",
        "renderMode": "webgl",
        "boardLogicalSize": {"width": 460, "height": 240},
        "players": [{
            "boardClientMappingMethod": "validated_axis_aligned_rect",
            "boardStageCorners": {
                "topLeft": {"x": 340, "y": 72},
                "topRight": {"x": 800, "y": 72},
                "bottomRight": {"x": 800, "y": 312},
                "bottomLeft": {"x": 340, "y": 312},
            },
            "boardClientCorners": {
                "topLeft": {"x": 497.96, "y": 104.86},
                "topRight": {"x": 1170.10, "y": 104.86},
                "bottomRight": {"x": 1170.10, "y": 456.06},
                "bottomLeft": {"x": 497.96, "y": 456.06},
            },
        }],
    }
    digest = hashlib.sha256(json.dumps(
        board, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()).hexdigest()
    targets = [(600, 343), (800, 408), (1000, 513)]
    samples = []
    for sx, sy in targets:
        samples.append({
            "type": "BOARD_SCREEN_PREFLIGHT_SAMPLE",
            "source": "window-bubble-after-egret-canvas",
            "session_id": SID, "renderer_geometry_sha256": digest,
            "boardpane_mapping_sha256": _boardpane_mapping_fingerprint(board),
            "buttons": 0, "pre_drawing": True,
            "captured_at_utc": (NOW-timedelta(seconds=1)).isoformat(),
            "clientX": sx, "clientY": sy-163,
            "screenX": sx, "screenY": sy,
        })
    session = {
        "session_id": SID,
        "renderer_geometry": board,
        "passive_preflight_samples": samples,
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
    return session, samples, targets


@pytest.mark.parametrize("candidate", ["K_trim_0_y190_w2", "K_trim_0_y189_w3"])
def test_v5_auto_roi_uses_same_run_native_mouse_and_existing_validator(candidate):
    session, samples, targets = build_fixture()
    plan = build_fill001_v5_source_plan(candidate)
    immutable = deepcopy(plan)
    mapped, evidence, roi = derive_v5_roi_from_verified_passive_moves(
        plan, session, samples,
        expected_session_id=SID,
        desktop_width=1920, desktop_height=1080,
        native_mouse_targets=targets, now_utc=NOW,
    )
    assert roi == {"x": 497, "y": 267, "width": 674, "height": 353}
    assert mapped["coordinate_system"] == "local_canvas_pixels"
    assert mapped["canvas"] == {"width": 674, "height": 353}
    assert mapped["strokes"][-1]["metadata"]["brush_value"] in ("2", "3")
    assert evidence["no_fallback"] is True
    assert evidence["session_id"] == SID
    assert plan == immutable


@pytest.mark.parametrize("fault,needle", [
    ("mouse", "OS mouse"),
    ("sid", "session identity"),
    ("stale", "stale or future"),
    ("button", "type/source/run/geometry"),
    ("outside", "outside the physical"),
    ("duplicate", "distinct"),
])
def test_v5_auto_roi_fail_closed_on_bad_proof(fault, needle):
    session, samples, targets = build_fixture()
    if fault == "mouse":
        targets[0] = (601, 348)
    elif fault == "sid":
        session["session_id"] = "other"
    elif fault == "stale":
        session["bridge_diagnostics"]["last_heartbeat_at_utc"] = (
            NOW-timedelta(seconds=10)
        ).isoformat()
    elif fault == "button":
        samples[0]["buttons"] = 1
    elif fault == "outside":
        targets = [(x-2000, y) for x,y in targets]
        for sample in samples:
            sample["screenX"] -= 2000
    elif fault == "duplicate":
        targets[1] = targets[0]
    with pytest.raises(PreflightGeometryError, match=needle):
        derive_v5_roi_from_verified_passive_moves(
            build_fill001_v5_source_plan("K_trim_0_y190_w2"),
            session, samples, expected_session_id=SID,
            desktop_width=1920, desktop_height=1080,
            native_mouse_targets=targets, now_utc=NOW,
        )

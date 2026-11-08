from __future__ import annotations

import json

import pytest

from game_monitor_bridge_server import RunRecorder, render_bridge_snippet


TEMPLATE = (
    'const TOKEN = "__AUTODRAW_BRIDGE_TOKEN__";\n'
    'const ENDPOINT = "ws://127.0.0.1:8765";\n'
    'const ENABLE = "__AUTODRAW_INPUT_TELEMETRY_ENABLED__" === "true";\n'
)


@pytest.mark.parametrize("enabled,expected", [(False, "false"), (True, "true")])
def test_render_bridge_snippet_sets_telemetry_opt_in(enabled: bool, expected: str) -> None:
    result = render_bridge_snippet(
        TEMPLATE, "one-time-test-token", 8766,
        enable_input_telemetry=enabled,
    )
    assert "one-time-test-token" in result
    assert "ws://127.0.0.1:8766" in result
    assert f'const ENABLE = "{expected}" === "true";' in result
    assert "__AUTODRAW_BRIDGE_TOKEN__" not in result
    assert "__AUTODRAW_INPUT_TELEMETRY_ENABLED__" not in result


def test_render_bridge_snippet_fails_closed_on_unresolved_or_missing_placeholders() -> None:
    with pytest.raises(ValueError, match="token placeholder"):
        render_bridge_snippet(
            TEMPLATE.replace("__AUTODRAW_BRIDGE_TOKEN__", "already-replaced"),
            "token", 8765,
        )
    with pytest.raises(ValueError, match="telemetry placeholder"):
        render_bridge_snippet(
            TEMPLATE.replace("__AUTODRAW_INPUT_TELEMETRY_ENABLED__", "false"),
            "token", 8765,
        )


@pytest.mark.parametrize("port", [True, 0, 65536, "8765"])
def test_render_bridge_snippet_rejects_invalid_ports(port) -> None:
    with pytest.raises(ValueError):
        render_bridge_snippet(TEMPLATE, "token", port)


def test_render_bridge_snippet_rejects_non_boolean_telemetry_flag() -> None:
    with pytest.raises(TypeError, match="boolean"):
        render_bridge_snippet(TEMPLATE, "token", 8765, enable_input_telemetry=1)


def test_bridge_configuration_is_bound_to_the_run_record(tmp_path) -> None:
    recorder = RunRecorder(tmp_path, "session-bridge-config", 2.5)
    configuration = {
        "inputTelemetry": {
            "requested": True,
            "enabled": True,
            "previous": False,
            "changedByBridge": True,
            "restoreStatus": "not_required",
        }
    }
    recorder.set_bridge_configuration(configuration)
    before = {
        "maxPoints": 6000,
        "remainingPoints": 6000,
        "pointCount": 0,
        "isExact": True,
    }
    recorder.event({"type": "DRAW_START", "t": 1, "before": before}, 1.0)
    path = recorder.finalize("partial")
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["bridge_configuration_at_start"] == configuration


def test_native_engine_frame_samples_and_stroke_mode_are_saved_in_bridge_run(tmp_path):
    recorder = RunRecorder(tmp_path, "frame-session", 2.5)
    pre = {"maxPoints":6000, "remainingPoints":6000, "pointCount":0, "isExact":True}
    post = {"maxPoints":6000, "remainingPoints":5999, "pointCount":1, "isExact":True}
    recorder.event({"type":"DRAW_START","strokeId":"stroke-1","t":1.0,"before":pre},1.0)
    recorder.event({
        "type":"ENGINE_FRAME_SAMPLE","strokeId":"stroke-1","t":2.0,
        "board":post, "strokeOptionRaw":True, "observedPointDeltaSincePreviousFrame":1,
        "renderPathCount":2,
    },2.0)
    recorder.event({
        "type":"ENGINE_FRAME_SAMPLE","strokeId":"stroke-1","t":3.0,
        "board":post, "strokeOptionRaw":True, "observedPointDeltaSincePreviousFrame":0,
        "renderPathCount":3,
    },3.0)
    recorder.event({
        "type":"DRAW_SAMPLE","strokeId":"stroke-1","t":3.1,"board":post,
        "pointDelta":1,"acceptedPoint":{"x":20.0,"y":120.0},
    },3.1)
    recorder.event({"type":"DRAW_END","strokeId":"stroke-1","t":4.0,"after":post},4.0)
    file = recorder.finalize()
    report = json.loads(file.read_text(encoding="utf-8"))
    frames = report["engine_frame_samples"]
    assert frames["event_count"] == 2
    assert frames["by_stroke"][0]["frame_count"] == 2
    assert frames["by_stroke"][0]["observed_stationary_frames"] == 1
    assert report["observed_stroke_modes"] == [{
        "stroke_id":"stroke-1", "stroke_option_raw":True,
        "source":"BoardPane.atom.options[from_ENGINE_FRAME_SAMPLE]",
    }]
    assert frames["is_full_engine_render_timeline"] is False
    assert [event["renderPathCount"] for event in report["events"]
            if event["type"] == "ENGINE_FRAME_SAMPLE"] == [2,3]


def test_authenticated_passive_preflight_witness_is_bounded_to_boardpane():
    from game_monitor_bridge_server import normalize_passive_preflight_sample
    geometry = {
        "players": [{"boardClientCorners": {
            "topLeft": {"x": 498.0, "y": 104.0},
            "bottomRight": {"x": 1170.0, "y": 456.0},
        }}],
        "boardLogicalSize": {"width": 460, "height": 240},
    }
    session = {
        "session_id": "live-session", "renderer_geometry": geometry,
        "bridge_configuration": {"inputTelemetry": {"enabled": True}},
        "bridge_diagnostics": {"last_monitor_status": {
            "version": "0.2.4", "active": True, "boardDetected": True,
        }},
    }
    raw = {"source": "window-bubble-after-egret-canvas", "isTrusted": True,
           "buttons": 0, "clientX": 600, "clientY": 220,
           "screenX": 600, "screenY": 383}
    bound = normalize_passive_preflight_sample(raw, session)
    assert bound["type"] == "BOARD_SCREEN_PREFLIGHT_SAMPLE"
    assert bound["pre_drawing"] is True
    assert bound["session_id"] == "live-session"
    assert bound["screenY"] - bound["clientY"] == 163
    assert len(bound["renderer_geometry_sha256"]) == 64
    assert bound["captured_at_utc"]
    for changed in (
        {**raw, "buttons": 1},
        {**raw, "isTrusted": False},
        {**raw, "clientX": 0},
        {**raw, "screenX": float("nan")},
        {**raw, "source": "inferred"},
    ):
        with pytest.raises(ValueError):
            normalize_passive_preflight_sample(changed, session)

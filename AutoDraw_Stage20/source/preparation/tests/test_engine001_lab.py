from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from PIL import Image

from chalk_test_blocks import (
    build_chalk_test_block_plan, create_chalk_test_block_journal,
    load_chalk_test_block_journal, claim_next_chalk_block_task,
)
from engine001_lab import (
    ENGINE001_EXPECTED_TASKS, ENGINE001_SCENARIOS,
    inspect_ready_bridge, audit_single_capture,
)


def _session(tmp_path, *, age_seconds=1, frames=True, telemetry=True, suffix="a"):
    now = datetime.now(timezone.utc)
    directory = tmp_path / f"session-{suffix}"
    directory.mkdir(parents=True)
    payload = {
        "session_id": f"session-{suffix}",
        "bridge_diagnostics": {
            "connection_closed": False,
            "last_message_type": "heartbeat",
            "last_message_at_utc": (now-timedelta(seconds=age_seconds)).isoformat(),
            "last_monitor_status": {
                "active": True, "boardDetected": True,
                "inputTelemetryEnabled": telemetry,
                "engineFrameObserverConnected": frames, "version": "0.2.3",
            },
        },
        "bridge_configuration": {
            "inputTelemetry": {"requested": True, "enabled": telemetry}
        },
        "renderer_geometry": {"players": [{"boardStageCorners": {"topLeft": [0,0]}}]},
    }
    (directory / "session.json").write_text(json.dumps(payload), encoding="utf-8")
    return payload


def test_lab_block_nine_isolated_cells_and_recovery(tmp_path):
    plan = build_chalk_test_block_plan(
        series_id="engine-one-click", phase_id="ENGINE001", repeats=3, seed=7,
    )
    assert plan["expected_task_count"] == ENGINE001_EXPECTED_TASKS == 9
    assert {t["scenario_id"] for t in plan["tasks"]} == set(ENGINE001_SCENARIOS)
    assert sorted(t["repeat_index"] for t in plan["tasks"]) == [1,1,1,2,2,2,3,3,3]
    assert all(t["expected_strokes"] == 1 for t in plan["tasks"])
    assert all(t["requested_radius"] == 10 for t in plan["tasks"])
    assert all(t["executor_parameters"]["line_extension_px"] == 0 for t in plan["tasks"])
    journal_path = tmp_path / "engine-lab.json"
    create_chalk_test_block_journal(journal_path, plan)
    loaded = load_chalk_test_block_journal(journal_path)
    assert loaded["expected_task_count"] == 9
    claimed = claim_next_chalk_block_task(journal_path)
    assert claimed["status"] == "running"
    with pytest.raises(RuntimeError):
        claim_next_chalk_block_task(journal_path)


def test_bridge_ready_requires_one_exact_fresh_engine_observer(tmp_path):
    s = _session(tmp_path)
    ready = inspect_ready_bridge(tmp_path)
    assert ready["session_id"] == s["session_id"]
    assert ready["geometry_mapping_state"] == "RAW_CSS_ONLY_NOT_DESKTOP_CALIBRATED"
    _session(tmp_path, suffix="b")
    with pytest.raises(ValueError, match="ровно один"):
        inspect_ready_bridge(tmp_path)


@pytest.mark.parametrize("frames,telemetry,age", [
    (False,True,1), (True,False,1), (True,True,20)
])
def test_bridge_rejects_no_frames_no_telemetry_or_stale(tmp_path, frames, telemetry, age):
    _session(tmp_path, frames=frames, telemetry=telemetry, age_seconds=age)
    with pytest.raises(ValueError):
        inspect_ready_bridge(tmp_path)


def _capture(folder):
    folder.mkdir()
    before = Image.new("RGB", (24,12), "white")
    after = before.copy()
    for x in range(6,18):
        after.putpixel((x,6), (0,0,0))
    before.save(folder/"before-board.png")
    before.save(folder/"before-screen.png")
    after.save(folder/"after-board.png")
    after.save(folder/"after-screen.png")
    exp={
        "experiment_id": "exp-test",
        "chalk_experiment_matrix": {
            "phase_id":"ENGINE001", "scenario_id":"engine001_horizontal_endpoint",
            "expected_strokes":1, "repeat_index":1
        },
        "game_monitor_summary": {"run_id":"run-test","session_id":"session-test"},
        "phases": {
            "before_draw": {"files":{
                "full_screen":"before-screen.png", "board_roi":"before-board.png",
            }},
            "after_draw": {"files":{
                "full_screen":"after-screen.png","board_roi":"after-board.png",
            }},
        },
    }
    report={
        "autodraw_experiment_id": "exp-test",
        "run_id":"run-test","session_id":"session-test",
        "chalk":{"status":"exact","consumed_points":2},
        "pre_test_snapshot":{"pointCount":1},
        "post_test_snapshot":{"pointCount":3},
        "point_delta_matches_chalk":True, "stroke_count":1,
        "execution_status":"completed",
        "accepted_points":[
            {"stroke_id":"stroke-1","point_delta":1,"x":6.0,"y":6.0,"t":1.0},
            {"stroke_id":"stroke-1","point_delta":1,"x":17.0,"y":6.0,"t":2.0},
        ],
        "observed_stroke_modes":[{"stroke_id":"stroke-1","stroke_option_raw":True}],
        "engine_frame_samples":{"event_count":2,"by_stroke":[
            {"stroke_id":"stroke-1","frame_count":2}
        ]},
        "renderer_geometry_at_start":{"players":[{"boardClientCorners":None}]},
        "renderer_geometry_at_end":{"players":[{"boardClientCorners":None}]},
        "renderer_geometry_updates":[],
        "renderer_geometry_update_overflow_count":0,
        "dropped_events":0, "monitor_buffer_dropped_events_delta":0,
        "monitor_error_count_delta":0, "bridge_send_failures_delta":0,
        "collector_sequence_gap_count":0,
        "frame_probe":{"status":"measured"},
    }
    (folder/"experiment.json").write_text(json.dumps(exp),encoding="utf-8")
    (folder/"monitor_report.json").write_text(json.dumps(report),encoding="utf-8")
    return exp,report


def test_single_capture_audit_and_no_overwrite(tmp_path):
    exp,report=_capture(tmp_path/"one")
    result=audit_single_capture(tmp_path/"one")
    assert result["status"]=="PASS_E4_RAW_CAPTURE"
    assert result["board_roi_pixel_diff"]["changed_pixel_count"]==12
    assert result["exact_chalk"]==2
    assert result["renderer_geometry_binding"]["screen_projection"].startswith("UNCALIBRATED")
    assert result["last_accepted"]["x"]==17.0
    assert result["raw_sha256"]["monitor_report.json"]
    with pytest.raises(FileExistsError):
        audit_single_capture(tmp_path/"one")


def test_single_capture_missing_frame_is_partial_not_pass(tmp_path):
    _,report=_capture(tmp_path/"failed")
    report["engine_frame_samples"]={"event_count":0,"by_stroke":[]}
    (tmp_path/"failed"/"monitor_report.json").write_text(json.dumps(report),encoding="utf-8")
    result=audit_single_capture(tmp_path/"failed")
    assert result["status"]=="PARTIAL"
    assert "egret_enter_frame_telemetry_incomplete" in result["reasons"]


def test_single_capture_bad_run_identity_fails_closed(tmp_path):
    exp,_=_capture(tmp_path/"mismatch")
    exp["game_monitor_summary"]["session_id"]="another-session"
    (tmp_path/"mismatch"/"experiment.json").write_text(json.dumps(exp),encoding="utf-8")
    with pytest.raises(ValueError,match="run/session identity"):
        audit_single_capture(tmp_path/"mismatch")


def test_one_button_rejects_when_bridge_not_prepared(tmp_path, monkeypatch):
    import brush_behavior_test_ui as ui
    tab = ui.BrushBehaviorTestTab.__new__(ui.BrushBehaviorTestTab)
    tab.output_dir = tmp_path
    tab.root = object()
    tab._chalk_block_task = None
    tab._chalk_block_journal_path = None
    calls = []
    notices = []
    tab.start_chalk_test_block = lambda **kwargs: calls.append(kwargs)
    monkeypatch.setattr(ui.messagebox,"showwarning",
                        lambda *args, **kwargs: notices.append(args))
    tab.start_engine001_lab()
    assert not calls
    assert notices


def test_one_button_uses_existing_automation_only_after_bridge_gate(tmp_path, monkeypatch):
    import brush_behavior_test_ui as ui
    _session(tmp_path / "game_monitor_bridge")
    tab = ui.BrushBehaviorTestTab.__new__(ui.BrushBehaviorTestTab)
    tab.output_dir = tmp_path
    tab.root = object()
    tab._chalk_block_task = None
    tab._chalk_block_journal_path = None
    tab.chalk_block_progress_var = type("Var",(),{"set":lambda self,v:None})()
    calls = []
    tab.start_chalk_test_block = lambda **kwargs: calls.append(kwargs)
    tab.start_engine001_lab()
    assert calls == [{"lab_one_click":True}]
    assert tab._engine001_lab_session_id == "session-a"

"""V5 Stage6 gate tests; none move a real mouse or write game input."""
from __future__ import annotations

from datetime import datetime
import json
from types import SimpleNamespace

import pytest

import fill001_v5_stage6_execution as runtime
from fill001_boardpane_preflight import boardpane_preflight_transform
from fill001_monitor_diagnostic import _boardpane_mapping_fingerprint
from fill001_v5_handoff import Fill001V5Error, build_fill001_v5_source_plan
from test_fill001_v5_auto_roi import build_fixture, NOW, SID


def setup_case(tmp_path, monkeypatch, *, initial=10, points=1):
    session, samples, _ = build_fixture()
    session["page"] = {"origin":"https://eufbpet.hust.me"}
    diagnostics = session["bridge_diagnostics"]
    diagnostics["last_message_type"] = "heartbeat"
    diagnostics["collector_sequence_gap_count"] = 0
    diagnostics["last_monitor_status"]["snapshot"] = {
        "isExact":True, "pointCount":points, "remainingPoints":6000-points,
        "maxPoints":6000,"currentRadius":initial,
    }
    folder=tmp_path / SID
    folder.mkdir(exist_ok=True)
    (folder/"session.json").write_text(json.dumps(session),encoding="utf-8")
    source=build_fill001_v5_source_plan("K_trim_0_y190_w2")
    roi={"x":497,"y":267,"width":674,"height":353}
    mapped,mapping=boardpane_preflight_transform(
        source, roi, session, samples, expected_session_id=SID, now_utc=NOW,
    )
    slider={
        "x_at_min":100,"x_at_max":390,"y":100,
        "initial_value":initial,"screen_width":1920,
        "screen_height":1080,"confirmed":True,
    }
    monkeypatch.setattr(runtime, "firefox_foreground_witness", lambda driver: True)
    driver=SimpleNamespace(capabilities={"browserName":"firefox","moz:processID":5421})
    def prepare():
        return runtime.prepare_v5_run(
            source,mapped,mapping,roi,bridge_root=tmp_path,
            session_id=SID,driver=driver,
            slider_calibration=slider,screen_size=(1920,1080),now_utc=NOW,
        )
    return source,mapped,mapping,roi,slider,driver,prepare


def test_v5_29_stroke_stage6_request_is_single_run_not_accepted_result(tmp_path,monkeypatch):
    *_, prepare=setup_case(tmp_path,monkeypatch)
    request=prepare()
    assert request["protocol"]=="FILL001_V5_STAGE6_SINGLE_RUN_V1"
    assert request["brush_sequence"]==[10]*28+[2]
    assert request["initial_snapshot"]["pointCount"]==1
    assert request["actual_chalk"] is None
    assert request["final_validation"]=="PENDING"


def test_v5_disallows_dirty_board_before_slider_or_mouse(tmp_path,monkeypatch):
    *_, prepare=setup_case(tmp_path,monkeypatch,points=2)
    with pytest.raises(Fill001V5Error,match="not clean"):
        prepare()


def test_v5_requires_current_foreground_window(tmp_path,monkeypatch):
    *_,prepare=setup_case(tmp_path,monkeypatch)
    monkeypatch.setattr(runtime,"firefox_foreground_witness",lambda driver:False)
    with pytest.raises(Fill001V5Error,match="foreground"):
        prepare()


def test_v5_requires_calibrated_initial_radius_equal_to_game(tmp_path,monkeypatch):
    *_, prepare=setup_case(tmp_path,monkeypatch,initial=30)
    request=prepare()
    assert request["initial_snapshot"]["currentRadius"]==30
    source,mapped,mapping,roi,slider,driver,_=setup_case(tmp_path,monkeypatch,initial=10)
    slider["initial_value"]=30
    with pytest.raises(Fill001V5Error,match="initial calibration"):
        runtime.prepare_v5_run(
            source,mapped,mapping,roi,bridge_root=tmp_path,
            session_id=SID,driver=driver,
            slider_calibration=slider,screen_size=(1920,1080),now_utc=NOW,
        )


def test_v5_rejects_tampered_mapped_point_even_when_metadata_is_unchanged(tmp_path,monkeypatch):
    source,mapped,mapping,roi,slider,driver,_=setup_case(tmp_path,monkeypatch)
    mapped["strokes"][0]["points"][0]["x"] += 1
    with pytest.raises(Fill001V5Error,match="screen coordinates"):
        runtime.prepare_v5_run(
            source,mapped,mapping,roi,bridge_root=tmp_path,
            session_id=SID,driver=driver,
            slider_calibration=slider,screen_size=(1920,1080),now_utc=NOW,
        )


def test_v5_rejects_prior_session_mapping_and_stale_roi(tmp_path,monkeypatch):
    source,mapped,mapping,roi,slider,driver,_=setup_case(tmp_path,monkeypatch)
    mapping["session_id"]="old-session"
    with pytest.raises(Fill001V5Error,match="authenticated"):
        runtime.prepare_v5_run(
            source,mapped,mapping,roi,bridge_root=tmp_path,
            session_id=SID,driver=driver,
            slider_calibration=slider,screen_size=(1920,1080),now_utc=NOW,
        )


def test_v5_refuses_stale_loaded_finalizer_before_any_mouse_input(tmp_path, monkeypatch):
    """A current V5 worker must not draw using an old global-radii validator."""
    import sys
    import fill001_v5_finalization as finalizer
    source, mapped, mapping, roi, slider, driver, prepare = setup_case(
        tmp_path, monkeypatch, initial=10)
    request = prepare()
    monkeypatch.setitem(sys.modules, "pyautogui", SimpleNamespace())
    monkeypatch.setattr(finalizer, "V5_BINDING_CONTRACT", "OLD_GLOBAL_RADIUS_CHECK")
    class Mouse:
        def size(self):
            pytest.fail("Mouse queried before V5 finalizer preflight")
        def click(self, *args, **kwargs):
            pytest.fail("Mouse clicked with stale V5 finalizer")
    with pytest.raises(Fill001V5Error, match="finalizer contract is outdated"):
        runtime.execute_v5_with_stage6(
            request=request, source=source, mapped=mapped, mapping=mapping,
            bridge_root=tmp_path, driver=driver, slider_calibration=slider,
            stop_event=SimpleNamespace(), native_mouse=Mouse(), output_dir=tmp_path)

"""Controlled fakes for passive V5 Firefox + OS pointer probe; no browser or game."""
from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
import time
import json
import sys
import types
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from fill001_boardpane_preflight import PreflightGeometryError
from fill001_firefox_auto_probe import collect_verified_v5_firefox_roi, _recent_samples
from fill001_v5_handoff import build_fill001_v5_source_plan

from test_fill001_v5_auto_roi import build_fixture, NOW, SID


def test_no_browser_input_on_modified_v5_source(tmp_path):
    session,_,_ = build_fixture()
    plan = build_fill001_v5_source_plan("K_trim_0_y190_w2")
    plan["strokes"][0]["metadata"]["brush_value"] = "3"
    class Driver:
        def find_elements(self, *args):
            raise AssertionError("No cursor movement allowed for invalid plan")
    with pytest.raises(ValueError, match="differs"):
        collect_verified_v5_firefox_roi(
            Driver(),tmp_path,SID,plan,
            native_mouse=object(), now_utc=NOW,
        )


def test_rejects_wrong_iframe_before_any_native_mouse(tmp_path, monkeypatch):
    import firefox_monitor_session
    monkeypatch.setattr(firefox_monitor_session, "find_game_frame", lambda _: None)
    selenium = types.ModuleType("selenium")
    selenium_webdriver = types.ModuleType("selenium.webdriver")
    selenium_common = types.ModuleType("selenium.webdriver.common")
    selenium_by = types.ModuleType("selenium.webdriver.common.by")
    selenium_by.By = SimpleNamespace(CSS_SELECTOR="css")
    action_module = types.ModuleType("selenium.webdriver.common.action_chains")
    action_module.ActionChains = lambda driver: None
    with patch.dict(sys.modules, {
        "selenium": selenium,
        "selenium.webdriver": selenium_webdriver,
        "selenium.webdriver.common": selenium_common,
        "selenium.webdriver.common.by": selenium_by,
        "selenium.webdriver.common.action_chains": action_module,
    }):
        with pytest.raises(PreflightGeometryError, match="Wrong Firefox frame"):
            collect_verified_v5_firefox_roi(
                object(),tmp_path,SID,
                build_fill001_v5_source_plan("K_trim_0_y190_w2"),
                native_mouse=object(),now_utc=NOW,
            )


def test_verified_selenium_and_real_mouse_passive_sequence_uses_existing_gate(
    tmp_path, monkeypatch,
):
    import firefox_monitor_session
    monkeypatch.setattr(firefox_monitor_session, "find_game_frame",
                        lambda driver: {"egret": True, "canvasCount": 1})
    folder = tmp_path / SID
    folder.mkdir()
    session,_,_ = build_fixture()
    session_path = folder / "session.json"
    session_path.write_text(json.dumps(session),encoding="utf-8")

    emission_count = [0]
    def append(client_x,client_y,screen_x,screen_y):
        document = json.loads(session_path.read_text(encoding="utf-8"))
        sample = deepcopy(document["passive_preflight_samples"][-1])
        emission_count[0] += 1
        sample.update({"clientX":client_x,"clientY":client_y,
                       "screenX":screen_x,"screenY":screen_y,
                       "captured_at_utc": (
                           NOW-timedelta(milliseconds=900)
                           + timedelta(milliseconds=100*emission_count[0])
                       ).isoformat()})
        document["passive_preflight_samples"] = (
            document["passive_preflight_samples"] + [sample]
        )[-16:]

        session_path.write_text(json.dumps(document),encoding="utf-8")

    class Driver:
        def find_elements(self, *_args):
            return [object()]
        def execute_script(self, *_args):
            return {"x":0,"y":0,"width":1300,"height":900}

    class Actions:
        def __init__(self,driver):
            self.driver=driver
        def move_to_element_with_offset(self,canvas,dx,dy):
            self.dest=(round(650+dx),round(450+dy))
            return self
        def perform(self):
            x,y=self.dest
            append(x,y,x,y+163)

    class Native:
        def __init__(self):
            self.moves=[]
        def size(self):
            return SimpleNamespace(width=1920,height=1080)
        def moveTo(self,x,y,*,duration=0):
            assert duration==0
            self.moves.append((x,y))
            append(x,y-163,x,y)

    selenium = types.ModuleType("selenium")
    selenium_webdriver = types.ModuleType("selenium.webdriver")
    selenium_common = types.ModuleType("selenium.webdriver.common")
    selenium_by = types.ModuleType("selenium.webdriver.common.by")
    selenium_by.By = SimpleNamespace(CSS_SELECTOR="css")
    action_module = types.ModuleType("selenium.webdriver.common.action_chains")
    action_module.ActionChains = Actions
    native=Native()
    validation_clock_calls = []
    def completed_probe_clock():
        # Must be called once after all three REAL/native pointer witnesses.
        assert len(native.moves) == 3
        validation_clock_calls.append(True)
        return NOW
    with patch.dict(sys.modules,{
        "selenium":selenium,"selenium.webdriver":selenium_webdriver,
        "selenium.webdriver.common":selenium_common,
        "selenium.webdriver.common.by":selenium_by,
        "selenium.webdriver.common.action_chains":action_module,
    }):
        mapped,proof,roi=collect_verified_v5_firefox_roi(
            Driver(),tmp_path,SID,
            build_fill001_v5_source_plan("K_trim_0_y189_w3"),
            native_mouse=native,now_utc=completed_probe_clock,
            firefox_foreground_checker=lambda: True,
        )
    assert len(native.moves)==3
    assert validation_clock_calls == [True]
    assert roi=={"x":497,"y":267,"width":674,"height":353}
    assert mapped["coordinate_system"]=="local_canvas_pixels"
    assert mapped["strokes"][-1]["metadata"]["brush_value"]=="3"
    assert proof["no_fallback"] is True


def test_valid_v5_plan_without_optional_selenium_fails_closed_before_browser_access(
    tmp_path, monkeypatch,
):
    import builtins
    original_import = builtins.__import__
    def missing_selenium(name, *args, **kwargs):
        if name.startswith("selenium"):
            raise ModuleNotFoundError("No module named selenium")
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", missing_selenium)
    class NoBrowser:
        def find_elements(self, *_args):
            raise AssertionError("WebDriver must not be used without Selenium")
    with pytest.raises(PreflightGeometryError, match="Selenium is required"):
        collect_verified_v5_firefox_roi(
            NoBrowser(), tmp_path, SID,
            build_fill001_v5_source_plan("K_trim_0_y190_w2"),
            native_mouse=object(), now_utc=NOW,
        )


def test_missing_foreground_witness_blocks_before_any_selenium_move(tmp_path, monkeypatch):
    import firefox_monitor_session
    monkeypatch.setattr(
        firefox_monitor_session, "find_game_frame",
        lambda _driver: {"egret": True, "canvasCount": 1},
    )
    folder = tmp_path / SID
    folder.mkdir()
    session, _, _ = build_fixture()
    (folder / "session.json").write_text(
        json.dumps(session), encoding="utf-8"
    )
    class Driver:
        def find_elements(self, *_args):
            return [object()]
        def execute_script(self, *_args):
            return {"x": 0, "y": 0, "width": 1300, "height": 900}
    class Actions:
        def __init__(self, _driver):
            pass
        def move_to_element_with_offset(self, *_args):
            raise AssertionError("No mouse motion without foreground witness")
    selenium = types.ModuleType("selenium")
    webdriver = types.ModuleType("selenium.webdriver")
    common = types.ModuleType("selenium.webdriver.common")
    by = types.ModuleType("selenium.webdriver.common.by")
    by.By = SimpleNamespace(CSS_SELECTOR="css")
    actions = types.ModuleType("selenium.webdriver.common.action_chains")
    actions.ActionChains = Actions
    with patch.dict(sys.modules, {
        "selenium": selenium, "selenium.webdriver": webdriver,
        "selenium.webdriver.common": common, "selenium.webdriver.common.by": by,
        "selenium.webdriver.common.action_chains": actions,
    }):
        with pytest.raises(PreflightGeometryError, match="PID|foreground"):
            collect_verified_v5_firefox_roi(
                Driver(), tmp_path, SID,
                build_fill001_v5_source_plan("K_trim_0_y190_w2"),
                native_mouse=object(), now_utc=NOW,
            )


def test_v5_probe_diagnostic_persists_blocked_reason_without_execution(tmp_path):
    from fill001_firefox_auto_probe import write_v5_probe_result
    result = write_v5_probe_result(
        tmp_path / "v5_passive_roi",
        candidate_id="K_trim_0_y190_w2",
        session_id=SID,
        status="BLOCKED",
        reason="Firefox foreground PID mismatch",
    )
    document = json.loads(result.read_text(encoding="utf-8"))
    assert document["status"] == "BLOCKED"
    assert document["session_id"] == SID
    assert document["blocked_reason"] == "Firefox foreground PID mismatch"
    assert document["stage6_execution_allowed"] is False
    assert document["actual_chalk"] is None
    assert document["game_png_quality"] == "NOT_EVALUATED"
    assert "token" not in document
    assert "cookie" not in document
    second = write_v5_probe_result(
        tmp_path / "v5_passive_roi",
        candidate_id="K_trim_0_y190_w2",
        session_id=SID,
        status="BLOCKED",
        reason="Another independent failure",
    )
    assert second != result
    assert json.loads(result.read_text(encoding="utf-8")) == document


def test_v5_probe_diagnostic_rejects_false_pass_or_missing_proof(tmp_path):
    from fill001_firefox_auto_probe import write_v5_probe_result
    with pytest.raises(PreflightGeometryError, match="Unknown"):
        write_v5_probe_result(
            tmp_path, candidate_id="K_trim_0_y190_w2", session_id=SID,
            status="PASS_E4",
        )
    with pytest.raises(PreflightGeometryError, match="reason"):
        write_v5_probe_result(
            tmp_path, candidate_id="K_trim_0_y190_w2", session_id=SID,
            status="BLOCKED",
        )
    with pytest.raises(PreflightGeometryError, match="incomplete"):
        write_v5_probe_result(
            tmp_path, candidate_id="K_trim_0_y190_w2", session_id=SID,
            status="PASSIVE_MAPPING_ONLY_NOT_EXECUTOR_READY",
        )
    assert not list(tmp_path.glob("*.json"))


def test_recent_samples_accepts_three_new_events_in_full_sixteen_slot_ring(tmp_path):
    session, _, _ = build_fixture()
    path = tmp_path / "session.json"
    original = deepcopy(session["passive_preflight_samples"][-1])
    baseline = []
    for index in range(16):
        item = deepcopy(original)
        item["captured_at_utc"] = (NOW-timedelta(seconds=2)
            + timedelta(milliseconds=10*index)).isoformat()
        item["clientX"] = 600.0 + index
        item["clientY"] = 250.0 + index
        baseline.append(item)
    session["passive_preflight_samples"] = deepcopy(baseline)
    path.write_text(json.dumps(session), encoding="utf-8")
    # Exactly three new server-timestamped events replace the oldest slots.
    for index in range(3):
        item = deepcopy(original)
        item["captured_at_utc"] = (NOW-timedelta(milliseconds=300)
            + timedelta(milliseconds=100*index)).isoformat()
        item["clientX"] = 760.0 + index*20
        item["clientY"] = 350.0 + index*10
        session["passive_preflight_samples"] = (
            session["passive_preflight_samples"] + [item]
        )[-16:]
    assert len(session["passive_preflight_samples"]) == 16
    path.write_text(json.dumps(session), encoding="utf-8")
    actual, witnesses = _recent_samples(
        path, SID, baseline, deadline=time.monotonic()+0.3,
    )
    assert actual["session_id"] == SID
    assert len(witnesses) == 3
    assert witnesses[-1]["clientX"] == 800.0


@pytest.mark.parametrize("fault", ["only_two_new", "old_timestamps", "duplicate_coords", "wrong_session"])
def test_recent_samples_fails_closed_on_nonfresh_ring_suffix(tmp_path, fault, monkeypatch):
    session, _, _ = build_fixture()
    baseline = []
    original = deepcopy(session["passive_preflight_samples"][-1])
    for i in range(16):
        sample = deepcopy(original)
        sample["captured_at_utc"] = (NOW-timedelta(seconds=2)
            + timedelta(milliseconds=i*10)).isoformat()
        sample["clientX"] = 600+i
        sample["clientY"] = 250+i
        baseline.append(sample)
    session["passive_preflight_samples"] = deepcopy(baseline)
    extra = []
    for i in range(3 if fault != "only_two_new" else 2):
        sample = deepcopy(original)
        sample["captured_at_utc"] = (
            NOW-timedelta(milliseconds=300) + timedelta(milliseconds=i*100)
        ).isoformat() if fault != "old_timestamps" else baseline[-1]["captured_at_utc"]
        sample["clientX"] = 760+i*20
        sample["clientY"] = 350+i*10
        if fault == "duplicate_coords":
            sample["clientX"], sample["clientY"] = 760, 350
        if fault == "wrong_session":
            sample["session_id"] = "other"
        extra.append(sample)
    session["passive_preflight_samples"] = (baseline+extra)[-16:]
    path = tmp_path / "session.json"
    path.write_text(json.dumps(session), encoding="utf-8")
    monkeypatch.setattr("fill001_firefox_auto_probe.time.sleep", lambda _: None)
    with pytest.raises(PreflightGeometryError, match="No three fresh"):
        _recent_samples(path, SID, baseline, deadline=time.monotonic()+0.03)

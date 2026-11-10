"""Controlled fakes for passive V5 Firefox + OS pointer probe; no browser or game."""
from __future__ import annotations

from copy import deepcopy
import json
import sys
import types
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from fill001_boardpane_preflight import PreflightGeometryError
from fill001_firefox_auto_probe import collect_verified_v5_firefox_roi
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

    def append(client_x,client_y,screen_x,screen_y):
        document = json.loads(session_path.read_text(encoding="utf-8"))
        sample = deepcopy(document["passive_preflight_samples"][-1])
        sample.update({"clientX":client_x,"clientY":client_y,
                       "screenX":screen_x,"screenY":screen_y})
        document["passive_preflight_samples"].append(sample)
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
    with patch.dict(sys.modules,{
        "selenium":selenium,"selenium.webdriver":selenium_webdriver,
        "selenium.webdriver.common":selenium_common,
        "selenium.webdriver.common.by":selenium_by,
        "selenium.webdriver.common.action_chains":action_module,
    }):
        mapped,proof,roi=collect_verified_v5_firefox_roi(
            Driver(),tmp_path,SID,
            build_fill001_v5_source_plan("K_trim_0_y189_w3"),
            native_mouse=native,now_utc=NOW,
        )
    assert len(native.moves)==3
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

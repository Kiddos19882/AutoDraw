"""Fail-closed contract tests for opt-in Firefox Game Monitor attachment."""
import sys
import json
import uuid
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from firefox_monitor_session import (
    GAME_ORIGIN, FirefoxMonitorError, attach_monitor_after_confirmation,
    find_game_frame, validate_bridge_snippet, write_bridge_diagnostic, bridge_session_diagnostic,
    open_firefox, PORTAL_URL, LNA_ENABLED_PREF, LNA_WEBSOCKET_ENABLED_PREF,
)


class _Switch:
    def __init__(self, driver):
        self.driver = driver

    def default_content(self):
        self.driver.depth = 0

    def frame(self, frame):
        self.driver.depth += 1

    def parent_frame(self):
        self.driver.depth -= 1


class _Driver:
    def __init__(self, *, origin=GAME_ORIGIN, detected=True):
        self.origin = origin
        self.detected = detected
        self.depth = 0
        self.switch_to = _Switch(self)
        self.injected = []

    def find_elements(self, *args):
        return []

    def execute_script(self, code):
        if code == "return location.origin":
            return self.origin
        if "canvasCount:" in code:
            return {"canvasCount": 1, "egret": True}
        if "return !!(window.AutoDrawGameMonitor" in code:
            return False
        if "return AutoDrawGameMonitor.status()" in code:
            return {"version": "0.2.4", "boardDetected": self.detected}
        self.injected.append(code)


class FirefoxMonitorContractTests(unittest.TestCase):
    def setUp(self):
        selenium = types.ModuleType("selenium")
        webdriver = types.ModuleType("selenium.webdriver")
        common = types.ModuleType("selenium.webdriver.common")
        by = types.ModuleType("selenium.webdriver.common.by")
        by.By = types.SimpleNamespace(CSS_SELECTOR="css")
        self.modules = patch.dict(sys.modules, {
            "selenium": selenium, "selenium.webdriver": webdriver,
            "selenium.webdriver.common": common,
            "selenium.webdriver.common.by": by,
        })
        self.modules.start()

    def tearDown(self):
        self.modules.stop()

    def test_open_firefox_disables_lna_only_in_temporary_test_profile(self):
        events = []
        preferences = {}
        driver = types.SimpleNamespace(get=lambda url: events.append(("navigate", url)))
        webdriver = sys.modules["selenium.webdriver"]
        webdriver.FirefoxOptions = lambda: types.SimpleNamespace(
            set_preference=lambda name, value: preferences.update({name: value}))
        def launch(*, options):
            events.append(("launch", dict(preferences)))
            return driver
        webdriver.Firefox = launch
        sys.modules["selenium"].webdriver = webdriver
        self.assertIs(open_firefox(diagnostic=lambda event, **fields:
                      events.append((event, fields))), driver)
        self.assertEqual(preferences, {
            "dom.webnotifications.enabled": False,
            "network.lna.enabled": False,
            "network.lna.websocket.enabled": False,
        })
        self.assertEqual(events[0][0], "firefox_lna_profile_configured")
        self.assertEqual(events[0][1]["scope"], "temporary_webdriver_profile")
        self.assertTrue(events[0][1]["test_only"])
        self.assertEqual(events[0][1]["preferences"], {
            LNA_ENABLED_PREF: False, LNA_WEBSOCKET_ENABLED_PREF: False,
        })
        self.assertTrue(events[0][1]["proxy_unchanged"])
        self.assertEqual(events[1], ("launch", preferences))
        self.assertEqual(events[2], ("navigate", PORTAL_URL))

    def test_open_firefox_quits_when_navigation_fails(self):
        webdriver = sys.modules["selenium.webdriver"]
        webdriver.FirefoxOptions = lambda: types.SimpleNamespace(
            set_preference=lambda name, value: None)
        closed = []
        def fail_navigation(url):
            raise RuntimeError("navigation failed")
        driver = types.SimpleNamespace(get=fail_navigation, quit=lambda: closed.append(True))
        webdriver.Firefox = lambda **kwargs: driver
        sys.modules["selenium"].webdriver = webdriver
        with self.assertRaisesRegex(RuntimeError, "navigation failed"):
            open_firefox()
        self.assertEqual(closed, [True])

    def test_session_diagnostic_does_not_copy_raw_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sid = str(uuid.uuid4())
            session = root / sid / "session.json"
            session.parent.mkdir()
            session.write_text(json.dumps({
                "secret": "DO_NOT_COPY",
                "bridge_diagnostics": {"connection_closed": False,
                    "last_monitor_status": {"version": "0.2.4", "inputTelemetryEnabled": True}},
                "renderer_geometry": {"players": [{"boardStageCorners": {}}]},
                "bridge_configuration": {"inputTelemetry": {"requested": True, "enabled": True}},
            }), encoding="utf-8")
            rows = bridge_session_diagnostic(root)
            self.assertEqual(rows[0]["session_id"], sid)
            self.assertEqual(rows[0]["board_count"], 1)
            self.assertTrue(rows[0]["telemetry_enabled"])
            log = root / "startup.jsonl"
            write_bridge_diagnostic(log, "poll", sessions=rows)
            saved = log.read_text(encoding="utf-8")
            self.assertNotIn("DO_NOT_COPY", saved)
            self.assertEqual(json.loads(saved)["event"], "poll")

    def test_invalid_snippet_rejected(self):
        for snippet in ("", "__AUTODRAW_BRIDGE_TOKEN__ new WebSocket()",
                        "__AUTODRAW_INPUT_TELEMETRY_ENABLED__ new WebSocket()"):
            with self.assertRaises(FirefoxMonitorError):
                validate_bridge_snippet(snippet)

    def test_exact_origin_required(self):
        self.assertIsNone(find_game_frame(_Driver(origin="https://other.example")))
        self.assertIsNotNone(find_game_frame(_Driver()))

    def test_no_confirmation_never_executes_script(self):
        driver = _Driver()
        with self.assertRaisesRegex(FirefoxMonitorError, "не подтвердил"):
            attach_monitor_after_confirmation(
                driver, Path("missing.js"), Path("missing-snippet.js"),
                operator_confirmed=False,
            )
        self.assertEqual(driver.injected, [])

    def test_confirmed_monitor_and_snippet(self):
        with tempfile.TemporaryDirectory() as tmp:
            monitor = Path(tmp) / "monitor.js"
            snippet = Path(tmp) / "bridge.js"
            monitor.write_text("window.example = 1;", encoding="utf-8")
            snippet.write_text("new WebSocket('ws://127.0.0.1:8765');", encoding="utf-8")
            driver = _Driver()
            result = attach_monitor_after_confirmation(
                driver, monitor, snippet, operator_confirmed=True,
            )
            self.assertEqual(result["status"], "MONITOR_INJECTED")
            self.assertEqual(len(driver.injected), 2)

    def test_monitor_only_waits_for_delayed_board_without_bridge(self):
        class Delayed(_Driver):
            installed = False
            polls = 0

            def execute_script(self, code):
                if "return !!(window.AutoDrawGameMonitor" in code:
                    return self.installed
                if "return AutoDrawGameMonitor.status()" in code:
                    self.polls += 1
                    return {"version": "0.2.4", "boardDetected": self.polls == 2}
                if code == "window.example = 1;":
                    self.installed = True
                return super().execute_script(code)

        with tempfile.TemporaryDirectory() as tmp:
            monitor=Path(tmp)/"monitor.js"
            monitor.write_text("window.example = 1;", encoding="utf-8")
            driver=Delayed()
            ownership=[]
            with patch("firefox_monitor_session.time.sleep"):
                result=attach_monitor_after_confirmation(
                    driver, monitor, None, operator_confirmed=True, monitor_only=True,
                    on_monitor_install=lambda:ownership.append(True))
            self.assertEqual(result["status"],"MONITOR_READY")
            self.assertEqual(driver.polls,2)
            self.assertEqual(driver.injected,["window.example = 1;"])
            self.assertEqual(ownership,[True])
            with self.assertRaisesRegex(FirefoxMonitorError,"уже установлен"):
                attach_monitor_after_confirmation(driver,monitor,None,
                                                  operator_confirmed=True,monitor_only=True)
            with self.assertRaisesRegex(FirefoxMonitorError,"остановил"):
                attach_monitor_after_confirmation(_Driver(),monitor,None,
                    operator_confirmed=True,monitor_only=True,stop_requested=lambda:True)

    def test_wrong_board_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            monitor = Path(tmp) / "monitor.js"
            snippet = Path(tmp) / "bridge.js"
            monitor.write_text("window.example = 1;", encoding="utf-8")
            snippet.write_text("new WebSocket('ws://127.0.0.1:8765');", encoding="utf-8")
            driver = _Driver(detected=False)
            with self.assertRaises(FirefoxMonitorError):
                attach_monitor_after_confirmation(
                    driver, monitor, snippet, operator_confirmed=True,
                    timeout_seconds=0,
                )
            self.assertEqual(driver.injected, [])


if __name__ == "__main__":
    unittest.main()

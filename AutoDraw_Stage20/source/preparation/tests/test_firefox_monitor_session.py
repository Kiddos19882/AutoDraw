"""Fail-closed contract tests for opt-in Firefox Game Monitor attachment."""
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from firefox_monitor_session import (
    GAME_ORIGIN, FirefoxMonitorError, attach_monitor_after_confirmation,
    find_game_frame, validate_bridge_snippet,
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

"""Optional Firefox WebDriver attachment to the existing Game Monitor Bridge.

No mouse/keyboard input, no implicit confirmation and no executor calibration.
The operator must confirm that the game board is open before injection.
"""
from __future__ import annotations

import time
from pathlib import Path

PORTAL_URL = "https://pet-eu.hust.me/"
GAME_ORIGIN = "https://eufbpet.hust.me"
MONITOR_VERSION = "0.2.4"


class FirefoxMonitorError(RuntimeError):
    pass


def validate_bridge_snippet(source: str) -> None:
    if not source or "new WebSocket" not in source:
        raise FirefoxMonitorError("Bridge snippet отсутствует или не готов.")
    if "__AUTODRAW_BRIDGE_TOKEN__" in source or "__AUTODRAW_INPUT_TELEMETRY_ENABLED__" in source:
        raise FirefoxMonitorError("Bridge snippet содержит неразрешённый placeholder.")


def open_firefox():
    """Create a dedicated temporary WebDriver session; the operator logs in."""
    try:
        from selenium import webdriver
    except ImportError as exc:
        raise FirefoxMonitorError(
            "Selenium не установлен. Установите selenium в окружение AutoDraw."
        ) from exc
    options = webdriver.FirefoxOptions()
    options.set_preference("dom.webnotifications.enabled", False)
    driver = webdriver.Firefox(options=options)
    driver.get(PORTAL_URL)
    return driver


def find_game_frame(driver, *, max_depth: int = 5) -> dict | None:
    """Leave WebDriver focused on the one verified Egret iframe."""
    from selenium.webdriver.common.by import By

    driver.switch_to.default_content()

    def visit(depth: int):
        origin = driver.execute_script("return location.origin")
        if origin == GAME_ORIGIN:
            info = driver.execute_script("""
                return {
                    canvasCount: document.querySelectorAll('canvas').length,
                    egret: !!(window.egret && window.egret.Capabilities)
                };
            """)
            if info["egret"] and info["canvasCount"] > 0:
                return info
        if depth >= max_depth:
            return None
        for frame in driver.find_elements(By.CSS_SELECTOR, "iframe,frame"):
            try:
                driver.switch_to.frame(frame)
                found = visit(depth + 1)
                if found:
                    return found
                driver.switch_to.parent_frame()
            except Exception:
                driver.switch_to.parent_frame()
        return None

    return visit(0)


def attach_monitor_after_confirmation(
    driver, monitor_file: Path, snippet_file: Path, *,
    operator_confirmed: bool,
    timeout_seconds: float = 45,
) -> dict:
    """Attach only read-only telemetry; reject unknown iframe/monitor/board."""
    if operator_confirmed is not True:
        raise FirefoxMonitorError("Оператор не подтвердил открытую игровую доску.")
    if not monitor_file.is_file() or not snippet_file.is_file():
        raise FirefoxMonitorError("Monitor/Bridge файлы недоступны.")
    monitor_source = monitor_file.read_text(encoding="utf-8")
    snippet = snippet_file.read_text(encoding="utf-8")
    validate_bridge_snippet(snippet)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            if find_game_frame(driver) is None:
                time.sleep(1)
                continue
            installed = driver.execute_script(
                "return !!(window.AutoDrawGameMonitor && window.AutoDrawGameMonitor.status)")
            if not installed:
                driver.execute_script(monitor_source)
            status = driver.execute_script("return AutoDrawGameMonitor.status()")
            if status.get("version") != MONITOR_VERSION or not status.get("boardDetected"):
                time.sleep(1)
                continue
            driver.execute_script(snippet)
            return {"status": "MONITOR_INJECTED", "monitor_version": status["version"],
                    "board_detected": True, "game_origin": GAME_ORIGIN}
        except FirefoxMonitorError:
            raise
        except Exception:
            time.sleep(1)
    raise FirefoxMonitorError(
        "BLOCKED: не найден единственный доступный Egret BoardPane нужного Origin."
    )

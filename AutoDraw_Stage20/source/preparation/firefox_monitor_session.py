"""Optional Firefox WebDriver attachment to the existing Game Monitor Bridge.

No mouse/keyboard input, no implicit confirmation and no executor calibration.
The operator must confirm that the game board is open before injection.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

PORTAL_URL = "https://pet-eu.hust.me/"
GAME_ORIGIN = "https://eufbpet.hust.me"
MONITOR_VERSION = "0.2.4"


class FirefoxMonitorError(RuntimeError):
    pass


def write_bridge_diagnostic(path: Path, event: str, **fields) -> None:
    """Append only caller-supplied safe metadata; diagnostics never grant input."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        row = {"utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
               "event": event, **fields}
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    except (OSError, TypeError, ValueError):
        pass


def browser_bridge_diagnostic(driver) -> dict:
    """Read startup metadata only, not source, URLs, cookies or auth payloads."""
    try:
        return driver.execute_script("""
            const d = window.AutoDrawGameMonitorBridgeDiagnostics;
            const b = window.AutoDrawGameMonitorBridge;
            const m = window.AutoDrawGameMonitor;
            const s = m && m.status ? m.status() : null;
            return {
                expectedOrigin: location.origin === arguments[0],
                online: navigator.onLine, secureContext: window.isSecureContext,
                visibility: document.visibilityState, monitorPresent: !!m,
                monitorVersion: s && s.version, boardDetected: s && s.boardDetected,
                inputTelemetry: s && s.inputTelemetryEnabled,
                bridgePresent: !!b, connected: !!(b && b.connected),
                sessionId: b && b.sessionId, closeCode: b && b.closeCode,
                startup: d ? {sessionId: d.sessionId, events: d.events} : null
            };
        """, GAME_ORIGIN)
    except Exception as exc:
        return {"read_error_type": type(exc).__name__}


def bridge_session_diagnostic(root: Path) -> list[dict]:
    """Summarize why a collector session may be rejected without copying its payload."""
    rows = []
    try:
        paths = sorted(Path(root).glob("*/session.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:12]
    except (OSError, TypeError, ValueError):
        return [{"read_error": "directory_scan_failed"}]
    now = datetime.now(timezone.utc)
    for path in paths:
        try:
            sid = str(uuid.UUID(path.parent.name))
            row = {"session_id": sid}
        except ValueError:
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            d = doc.get("bridge_diagnostics", {})
            g = doc.get("renderer_geometry") or {}
            players = g.get("players") or []
            boards = [p for p in players if isinstance(p, dict) and isinstance(p.get("boardStageCorners"), dict)]
            tel = doc.get("bridge_configuration", {}).get("inputTelemetry") or {}
            status = d.get("last_monitor_status") or {}
            stamp = d.get("last_message_at_utc")
            age = (now - datetime.fromisoformat(stamp.replace("Z", "+00:00"))).total_seconds() if stamp else None
            row.update(connection_closed=d.get("connection_closed"), age_seconds=age,
                       last_message_at_utc=stamp, last_heartbeat_at_utc=d.get("last_heartbeat_at_utc"),
                       geometry_present=bool(g), board_count=len(boards),
                       board_client_mapping_present=bool(len(boards)==1 and boards[0].get("boardClientCorners")),
                       telemetry_requested=tel.get("requested"), telemetry_enabled=tel.get("enabled"),
                       monitor_version=status.get("version"), monitor_telemetry=status.get("inputTelemetryEnabled"),
                       persist_failures=d.get("session_persist_failures", 0))
        except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
            row["read_error_type"] = type(exc).__name__
        rows.append(row)
    return rows


def proxy_environment_diagnostic() -> dict:
    # Record presence only, never proxy hostnames, credentials or PAC URLs.
    names = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY")
    present = {k: bool(os.environ.get(k) or os.environ.get(k.lower())) for k in names}
    if os.name == "nt":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as key:
                for name in ("ProxyEnable", "ProxyServer", "AutoConfigURL"):
                    try:
                        present["windows_" + name] = bool(winreg.QueryValueEx(key, name)[0])
                    except OSError:
                        present["windows_" + name] = False
        except OSError:
            present["windows_proxy_read_failed"] = True
    return present


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
    driver, monitor_file: Path, snippet_file: Path | None, *,
    operator_confirmed: bool,
    timeout_seconds: float = 45,
    monitor_only: bool = False,
    stop_requested=None,
    on_monitor_install=None,
    diagnostic=None,
) -> dict:
    """Wait for the existing Monitor readiness gate, then optionally attach Bridge.

    The established Bridge call remains the default. A28 explicitly opts into
    Monitor-only mode (direct WebDriver telemetry, no fake Bridge session).
    """
    if operator_confirmed is not True:
        raise FirefoxMonitorError("Оператор не подтвердил открытую игровую доску.")
    if not monitor_file.is_file():
        raise FirefoxMonitorError("Monitor файл недоступен.")
    if monitor_only:
        if snippet_file is not None:
            raise FirefoxMonitorError("Monitor-only режим не принимает Bridge snippet.")
        snippet = None
    else:
        if snippet_file is None or not snippet_file.is_file():
            raise FirefoxMonitorError("Bridge файл недоступен.")
        snippet = snippet_file.read_text(encoding="utf-8")
        validate_bridge_snippet(snippet)
    monitor_source = monitor_file.read_text(encoding="utf-8")
    def note(event, **fields):
        if diagnostic is not None:
            diagnostic(event, **fields)

    injected = False
    note("attach_started", monitor_only=monitor_only)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if stop_requested is not None and stop_requested():
            raise FirefoxMonitorError("Оператор остановил ожидание игровой доски.")
        try:
            frame = find_game_frame(driver)
            if frame is None:
                note("game_frame_not_found")
                time.sleep(1)
                continue
            installed = driver.execute_script(
                "return !!(window.AutoDrawGameMonitor && window.AutoDrawGameMonitor.status)")
            note("game_frame_found", canvas_count=frame.get("canvasCount"), monitor_already_installed=installed)
            if monitor_only and installed and not injected:
                raise FirefoxMonitorError("Monitor уже установлен: нужна новая A28 Firefox-сессия.")
            if not installed:
                if on_monitor_install is not None:
                    on_monitor_install()
                injected = True
                driver.execute_script(monitor_source)
                note("monitor_script_executed")
            status = driver.execute_script("return AutoDrawGameMonitor.status()")
            note("monitor_status", version=status.get("version"), board_detected=status.get("boardDetected"),
                 input_telemetry=status.get("inputTelemetryEnabled"))
            if status.get("version") != MONITOR_VERSION or not status.get("boardDetected"):
                time.sleep(1)
                continue
            if snippet is not None:
                note("bridge_snippet_injecting")
                driver.execute_script(snippet)
                note("bridge_snippet_returned")
            return {"status": "MONITOR_READY" if monitor_only else "MONITOR_INJECTED", "monitor_version": status["version"],
                    "board_detected": True, "game_origin": GAME_ORIGIN}
        except FirefoxMonitorError:
            raise
        except Exception as exc:
            note("attach_attempt_error", error_type=type(exc).__name__)
            time.sleep(1)
    raise FirefoxMonitorError(
        "BLOCKED: не найден единственный доступный Egret BoardPane нужного Origin."
    )

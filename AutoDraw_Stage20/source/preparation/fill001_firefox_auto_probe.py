"""Collect real, non-clicking Firefox native-mouse probes for the existing E4 preflight.

No executor input, brush switch, game clear, or screenshot calibration fallback.
This collector fails closed if Firefox is not foreground or Windows coordinates
cannot be reconciled with the authenticated Game Monitor session.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

from fill001_boardpane_preflight import PreflightGeometryError
from fill001_v5_auto_roi import derive_v5_roi_from_verified_passive_moves
from fill001_v5_handoff import validate_fill001_v5_source_plan



def write_v5_probe_result(
    directory: Path,
    *,
    candidate_id: str,
    session_id: str | None,
    status: str,
    reason: str | None = None,
    roi: dict[str, int] | None = None,
    mapping: dict[str, Any] | None = None,
    source_strokes_sha256: str | None = None,
) -> Path:
    """Persist one immutable diagnostic outcome, never permission to execute.

    No cookies, credentials, WebDriver profile, Bridge token, or untrusted JS
    are collected.  BLOCKED results preserve failures for Windows E4 review.
    """
    import uuid
    from datetime import datetime, timezone

    allowed = {"PASSIVE_MAPPING_ONLY_NOT_EXECUTOR_READY", "BLOCKED"}
    if status not in allowed:
        raise PreflightGeometryError("Unknown V5 preflight diagnostic status.")
    if (not isinstance(candidate_id, str) or not candidate_id
            or session_id is not None and (not isinstance(session_id, str) or not session_id)):
        raise PreflightGeometryError("Missing V5 diagnostic identity.")
    if status == "BLOCKED" and (not isinstance(reason, str) or not reason.strip()):
        raise PreflightGeometryError("Blocked diagnostics require a reason.")
    if status != "BLOCKED" and (
        not isinstance(roi, dict) or not isinstance(mapping, dict)
        or not isinstance(source_strokes_sha256, str)
    ):
        raise PreflightGeometryError("Successful passive evidence is incomplete.")
    document = {
        "schema": "FILL001_V5_FIREFOX_PASSIVE_ROI_DIAGNOSTIC_V1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "candidate_id": candidate_id,
        "session_id": session_id,
        "source_strokes_sha256": source_strokes_sha256,
        "screen_roi": roi,
        "mapping": mapping,
        "blocked_reason": reason,
        "actual_chalk": None,
        "game_png_quality": "NOT_EVALUATED",
        "stage6_execution_allowed": False,
    }
    destination = Path(directory)
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / f"probe-{uuid.uuid4().hex}.json"
    with target.open("x", encoding="utf-8") as f:
        json.dump(document, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
    return target

def _load_session(path: Path, sid: str) -> dict[str, Any]:
    try:
        session = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PreflightGeometryError("Game Monitor session evidence is unavailable.") from exc
    if not isinstance(session, dict) or session.get("session_id") != sid:
        raise PreflightGeometryError("Bridge session identity changed during probe.")
    return session


def _recent_samples(path: Path, sid: str, baseline_count: int, *,
                    deadline: float) -> tuple[dict, list[dict]]:
    while time.monotonic() < deadline:
        session = _load_session(path, sid)
        samples = session.get("passive_preflight_samples")
        if isinstance(samples, list) and len(samples) >= baseline_count+3:
            suffix = samples[-3:]
            if all(isinstance(item, dict) and item.get("session_id") == sid
                   for item in suffix):
                return session, suffix
        time.sleep(0.2)
    raise PreflightGeometryError("No three fresh passive BoardPane input witnesses.")


def collect_verified_v5_firefox_roi(
    driver: Any, bridge_root: Path, session_id: str,
    source_plan: dict, *, native_mouse: Any, now_utc: Any,
    firefox_foreground_checker: Any = None,
) -> tuple[dict, dict, dict]:
    """Selenium hover + actual OS pointer hover, then existing Stage/Bridge validator.

    The caller must minimize AutoDraw first; no mouseDown, click or game
    invocation is performed here. Native OS pointer events are never faked.
    """
    # Untrusted V5 geometry must be rejected before optional browser imports,
    # WebDriver access, or any physical pointer movement.  In particular the
    # negative CI test must not require Selenium to be installed.
    validate_fill001_v5_source_plan(source_plan)
    return _collect_verified_boardpane_roi(
        driver, bridge_root, session_id, source_plan,
        native_mouse=native_mouse, now_utc=now_utc,
        firefox_foreground_checker=firefox_foreground_checker,
    )


def collect_verified_series_firefox_roi(
    manifest: dict, driver: Any, bridge_root: Path, session_id: str,
    source_plan: dict, *, native_mouse: Any, now_utc: Any,
    firefox_foreground_checker: Any = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, int]]:
    """Reuse actual V5 passive Firefox/OS probes for one signed series plan.

    No drawing, click or calibration fallback. The same native and Bridge
    witness collection remains unchanged.
    """
    from fill001_series_handoff import validate_series_source_plan
    validate_series_source_plan(manifest, source_plan)
    return _collect_verified_boardpane_roi(
        driver, bridge_root, session_id, source_plan,
        native_mouse=native_mouse, now_utc=now_utc,
        firefox_foreground_checker=firefox_foreground_checker,
    )


def _collect_verified_boardpane_roi(
    driver: Any, bridge_root: Path, session_id: str,
    source_plan: dict, *, native_mouse: Any, now_utc: Any,
    firefox_foreground_checker: Any = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, int]]:
    """Shared authenticated passive BoardPane probe; callers validate plans."""

    try:
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.by import By
    except ImportError as exc:
        raise PreflightGeometryError(
            "Selenium is required for the optional Firefox V5 passive probe."
        ) from exc
    from firefox_monitor_session import find_game_frame
    if find_game_frame(driver) is None:
        raise PreflightGeometryError("Wrong Firefox frame / Egret board not found.")
    root = Path(bridge_root)
    session_file = root / session_id / "session.json"
    session = _load_session(session_file, session_id)
    geo = session.get("renderer_geometry")
    players = geo.get("players") if isinstance(geo, dict) else None
    if not isinstance(players, list) or len(players) != 1:
        raise PreflightGeometryError("Exactly one BoardPane required for passive probe.")
    corners = players[0].get("boardClientCorners")
    if not isinstance(corners, dict):
        raise PreflightGeometryError("Missing client board corners.")
    try:
        x0,y0 = float(corners["topLeft"]["x"]),float(corners["topLeft"]["y"])
        x1,y1 = float(corners["bottomRight"]["x"]),float(corners["bottomRight"]["y"])
    except (KeyError, TypeError, ValueError) as exc:
        raise PreflightGeometryError("Invalid BoardPane client corners.") from exc
    if not all(math.isfinite(v) for v in (x0,y0,x1,y1)) or x1<=x0 or y1<=y0:
        raise PreflightGeometryError("Invalid BoardPane rectangle.")
    fraction_targets = ((.34,.40),(.50,.52),(.66,.64))
    css_targets = [(x0+(x1-x0)*fx,y0+(y1-y0)*fy)
                   for fx,fy in fraction_targets]
    # Match exactly one eligible canvas in the already-verified iframe.
    candidates = []
    for canvas in driver.find_elements(By.CSS_SELECTOR, "canvas"):
        rect = driver.execute_script(
            "const r=arguments[0].getBoundingClientRect();"
            "return {x:r.x,y:r.y,width:r.width,height:r.height};", canvas,
        )
        if (isinstance(rect, dict) and rect.get("width",0)>0
                and rect.get("height",0)>0
                and all(rect["x"]<=cx<=rect["x"]+rect["width"]
                        and rect["y"]<=cy<=rect["y"]+rect["height"]
                        for cx,cy in css_targets)):
            candidates.append((canvas,rect))
    if len(candidates) != 1:
        raise PreflightGeometryError("Ambiguous or missing Firefox game canvas.")
    canvas,rect = candidates[0]
    before = session.get("passive_preflight_samples") or []
    if not isinstance(before,list):
        raise PreflightGeometryError("Invalid Bridge passive sample history.")
    # A GUI caller must supply a real native foreground-window witness.
    # The collector is research-only until a verified Windows implementation
    # is wired in; never move a cursor based merely on Selenium window focus.
    def require_foreground() -> None:
        try:
            active = (
                callable(firefox_foreground_checker)
                and firefox_foreground_checker() is True
            )
        except Exception as exc:
            raise PreflightGeometryError(
                "Cannot authenticate foreground Firefox window."
            ) from exc
        if not active:
            raise PreflightGeometryError(
                "BLOCKED: Firefox is not proven to be the foreground window."
            )

    if firefox_foreground_checker is None:
        from firefox_foreground_witness import firefox_foreground_witness
        # Operator activation has already been checked by the UI worker.
        # Never call WebDriver focus or Win32 SetForegroundWindow here.
        # Every passive movement rechecks the real Windows foreground PID.
        firefox_foreground_checker = lambda: firefox_foreground_witness(driver)

    # W3C element-relative offset uses center of element. No click ever occurs.
    for cx,cy in css_targets:
        require_foreground()
        dx = int(round(cx-(rect["x"]+rect["width"]/2)))
        dy = int(round(cy-(rect["y"]+rect["height"]/2)))
        ActionChains(driver).move_to_element_with_offset(canvas,dx,dy).perform()
        time.sleep(0.3)
    preliminary, witnesses = _recent_samples(
        session_file, session_id, len(before), deadline=time.monotonic()+8,
    )
    offsets = [(float(e["screenX"])-float(e["clientX"]),
                float(e["screenY"])-float(e["clientY"])) for e in witnesses]
    if (max(abs(x-offsets[0][0]) for x,_ in offsets)>0.01
            or max(abs(y-offsets[0][1]) for _,y in offsets)>0.01):
        raise PreflightGeometryError("Preliminary Firefox desktop offset changed.")
    offset_x, offset_y = offsets[0]
    native_targets = [
        (round(cx+offset_x),round(cy+offset_y)) for cx,cy in css_targets
    ]
    if len(set(native_targets)) != 3:
        raise PreflightGeometryError("Native probe targets are ambiguous.")
    physical = native_mouse.size()
    desktop_width,desktop_height = int(physical.width),int(physical.height)
    for x,y in native_targets:
        if not (0<=x<desktop_width and 0<=y<desktop_height):
            raise PreflightGeometryError("Native mouse target outside primary desktop.")
    baseline = preliminary.get("passive_preflight_samples") or []
    for x,y in native_targets:
        require_foreground()
        native_mouse.moveTo(x,y,duration=0)
        time.sleep(0.35)
    actual, samples = _recent_samples(
        session_file,session_id,len(baseline),deadline=time.monotonic()+8,
    )
    # Resolve wall-clock time AFTER the passive samples were collected.
    # A snapshot taken before Selenium/OS moves would make fresh samples
    # appear to come from the future and correctly fail the E4 geometry gate.
    validation_time = now_utc() if callable(now_utc) else now_utc
    return derive_v5_roi_from_verified_passive_moves(
        source_plan, actual, samples, expected_session_id=session_id,
        desktop_width=desktop_width, desktop_height=desktop_height,
        native_mouse_targets=native_targets, now_utc=validation_time,
    )

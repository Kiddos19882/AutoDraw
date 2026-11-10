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
) -> tuple[dict, dict, dict]:
    """Selenium hover + actual OS pointer hover, then existing Stage/Bridge validator.

    The caller must minimize AutoDraw first; no mouseDown, click or game
    invocation is performed here. Native OS pointer events are never faked.
    """
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.common.by import By
    from firefox_monitor_session import find_game_frame

    # Reject tampered source plans BEFORE any browser/desktop cursor movements.
    validate_fill001_v5_source_plan(source_plan)
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
    # W3C element-relative offset uses center of element. No click ever occurs.
    for cx,cy in css_targets:
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
        native_mouse.moveTo(x,y,duration=0)
        time.sleep(0.35)
    actual, samples = _recent_samples(
        session_file,session_id,len(baseline),deadline=time.monotonic()+8,
    )
    return derive_v5_roi_from_verified_passive_moves(
        source_plan, actual, samples, expected_session_id=session_id,
        desktop_width=desktop_width, desktop_height=desktop_height,
        native_mouse_targets=native_targets, now_utc=now_utc,
    )

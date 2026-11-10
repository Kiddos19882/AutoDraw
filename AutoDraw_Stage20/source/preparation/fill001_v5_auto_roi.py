"""V5 automatic ROI calculation from SAME-SESSION passive mouse witnesses.

Research-only: this module calls existing BoardPane preflight validator.
No clicks, no Stage6 input, no manual offsets, no persistent calibration.
"""
from __future__ import annotations

from datetime import datetime
from math import ceil, floor, isfinite
from typing import Any

from fill001_boardpane_preflight import (
    PreflightGeometryError, boardpane_preflight_transform,
)

MAX_NATIVE_SCREEN_RESIDUAL = 1.0


def derive_v5_roi_from_verified_passive_moves(
    source_plan: dict[str, Any],
    session: dict[str, Any],
    samples: list[dict[str, Any]],
    *,
    expected_session_id: str,
    desktop_width: int,
    desktop_height: int,
    native_mouse_targets: list[tuple[int, int]],
    now_utc: datetime,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, int]]:
    """Turn three genuine passive game events into an ROI using existing E4 gate.

    Native mouse targets MUST come from distinct non-clicking OS-level probes.
    The external collector must ensure they were executed while Firefox was
    foreground; this function enforces their exact correspondence to browser
    screenX/screenY as recorded in the live authenticated Bridge.
    """
    if (type(desktop_width) is not int or type(desktop_height) is not int
            or desktop_width < 460 or desktop_height < 240):
        raise PreflightGeometryError("Invalid physical desktop dimensions.")
    if (not isinstance(samples, list) or len(samples) != 3
            or not isinstance(native_mouse_targets, list)
            or len(native_mouse_targets) != 3):
        raise PreflightGeometryError("Exactly three OS-level passive probes required.")
    if len(set(native_mouse_targets)) != 3:
        raise PreflightGeometryError("OS-level probe positions must be distinct.")
    geometry = session.get("renderer_geometry") if isinstance(session, dict) else None
    players = geometry.get("players") if isinstance(geometry, dict) else None
    if not isinstance(players, list) or len(players) != 1:
        raise PreflightGeometryError("Exactly one BoardPane required.")
    client = players[0].get("boardClientCorners") if isinstance(players[0], dict) else None
    if not isinstance(client, dict):
        raise PreflightGeometryError("Board client corners are not available.")
    try:
        left = float(client["topLeft"]["x"])
        top = float(client["topLeft"]["y"])
        right = float(client["bottomRight"]["x"])
        bottom = float(client["bottomRight"]["y"])
        delta = [
            (float(item["screenX"])-float(item["clientX"]),
             float(item["screenY"])-float(item["clientY"]))
            for item in samples
        ]
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise PreflightGeometryError("Invalid passive sample coordinates.") from exc
    if not all(isfinite(v) for v in (left, top, right, bottom, *[c for pair in delta for c in pair])):
        raise PreflightGeometryError("Non-finite passive screen geometry.")
    for index, (target, sample) in enumerate(zip(native_mouse_targets, samples)):
        if (not isinstance(target, (tuple, list)) or len(target) != 2
                or any(type(coord) is not int for coord in target)):
            raise PreflightGeometryError("Native mouse targets must be integer desktop points.")
        try:
            sx, sy = float(sample["screenX"]), float(sample["screenY"])
        except (KeyError, TypeError, ValueError) as exc:
            raise PreflightGeometryError("Missing passive mouse screen positions.") from exc
        if (abs(sx-target[0]) > MAX_NATIVE_SCREEN_RESIDUAL
                or abs(sy-target[1]) > MAX_NATIVE_SCREEN_RESIDUAL):
            raise PreflightGeometryError(
                f"OS mouse and browser desktop coordinates disagree on probe {index}."
            )
    # Existing BoardPane validator independently checks event freshness,
    # session, geometry, source, uniform scale, and offset residual.
    ox = sum(item[0] for item in delta)/len(delta)
    oy = sum(item[1] for item in delta)/len(delta)
    x0, y0 = floor(left+ox), floor(top+oy)
    x1, y1 = ceil(right+ox), ceil(bottom+oy)
    if not (0 <= x0 < x1 <= desktop_width and 0 <= y0 < y1 <= desktop_height):
        raise PreflightGeometryError("Board ROI is outside the physical primary display.")
    roi = {"x": x0, "y": y0, "width": x1-x0, "height": y1-y0}
    mapped, witness = boardpane_preflight_transform(
        source_plan, roi, session, samples,
        expected_session_id=expected_session_id, now_utc=now_utc,
    )
    return mapped, witness, roi

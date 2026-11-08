from __future__ import annotations

"""Research-only FILL-001 BoardPane preflight transform (NO executor integration).

Requires fresh, non-drawing DOM client/screen samples tied to a verified live
Monitor session. Current Monitor 0.2.4 does NOT emit this evidence pre-run:
without such a source this module deliberately fails closed. Never substitute
post-run mouse events from a previous FILL-001 capture.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from math import isfinite
from typing import Any

SCHEMA = "FILL001_BOARDPANE_PREFLIGHT_V1"
SAMPLE_TYPE = "BOARD_SCREEN_PREFLIGHT_SAMPLE"
MAX_SAMPLE_AGE_SECONDS = 5.0
MAX_HEARTBEAT_AGE_SECONDS = 4.0
MAX_OFFSET_RESIDUAL_PX = 0.01
LOGICAL_WIDTH, LOGICAL_HEIGHT = 460, 240
VALID_MAPPING = ("getBoxQuads_content", "validated_axis_aligned_rect")


class PreflightGeometryError(ValueError):
    pass


def _number(value: Any, field: str) -> float:
    if type(value) not in (int, float) or not isfinite(value):
        raise PreflightGeometryError(f"{field}: expected a finite number.")
    return float(value)


def _utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise PreflightGeometryError(f"{field}: missing UTC timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PreflightGeometryError(f"{field}: invalid UTC timestamp.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise PreflightGeometryError(f"{field}: UTC offset required.")
    return parsed.astimezone(timezone.utc)


def _age(now: datetime, stamp: datetime, max_age: float, field: str) -> None:
    age = (now - stamp).total_seconds()
    if not 0 <= age <= max_age:
        raise PreflightGeometryError(f"{field}: stale or future evidence ({age:.3f}s).")


def _geometry_hash(geometry: dict[str, Any]) -> str:
    encoded = json.dumps(geometry, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _rectangle(corners: Any, field: str) -> tuple[float, float, float, float]:
    if not isinstance(corners, dict):
        raise PreflightGeometryError(f"{field}: missing corners.")
    try:
        p = [corners[k] for k in ("topLeft", "topRight", "bottomRight", "bottomLeft")]
        x0, y0 = _number(p[0]["x"], field), _number(p[0]["y"], field)
        x1, y1 = _number(p[2]["x"], field), _number(p[2]["y"], field)
        coords = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        if x1 <= x0 or y1 <= y0 or any(
            abs(_number(q["x"], field) - x) > 1e-5
            or abs(_number(q["y"], field) - y) > 1e-5
            for q, (x, y) in zip(p, coords)
        ):
            raise PreflightGeometryError(f"{field}: non-axis-aligned rectangle.")
    except (KeyError, TypeError) as exc:
        raise PreflightGeometryError(f"{field}: invalid corners.") from exc
    return x0, y0, x1, y1


def boardpane_preflight_transform(
    plan: dict[str, Any],
    screen_roi: dict[str, int],
    session: dict[str, Any],
    samples: list[dict[str, Any]],
    *,
    expected_session_id: str,
    now_utc: datetime,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a NEW ROI-local plan only when a current, independent probe is valid.

    DOM samples must be emitted by a future read-only preflight probe while the
    mouse is UP. Their provenance cannot be fabricated by this routine and
    this function is not a live authentication mechanism. Never use an archived
    draw-run MOUSE_MOVE_SAMPLE as a preflight witness.
    """
    if not isinstance(now_utc, datetime) or now_utc.tzinfo is None:
        raise PreflightGeometryError("now_utc must be timezone-aware.")
    now = now_utc.astimezone(timezone.utc)
    if (not isinstance(expected_session_id, str) or not expected_session_id
            or not isinstance(session, dict)
            or session.get("session_id") != expected_session_id):
        raise PreflightGeometryError("Missing or mismatched session identity.")
    diag = session.get("bridge_diagnostics")
    config = session.get("bridge_configuration")
    if not isinstance(diag, dict) or not isinstance(config, dict):
        raise PreflightGeometryError("Authenticated live Bridge state missing.")
    status = diag.get("last_monitor_status")
    telemetry = config.get("inputTelemetry")
    if (diag.get("connection_closed") is not False
            or not isinstance(status, dict)
            or status.get("version") != "0.2.4"
            or status.get("active") is not True
            or status.get("boardDetected") is not True
            or status.get("inputTelemetryEnabled") is not True
            or status.get("engineFrameObserverConnected") is not True
            or not isinstance(telemetry, dict)
            or telemetry.get("requested") is not True
            or telemetry.get("enabled") is not True):
        raise PreflightGeometryError("Live Monitor/Bridge preflight requirements not met.")
    _age(now, _utc(diag.get("last_heartbeat_at_utc"), "heartbeat"),
         MAX_HEARTBEAT_AGE_SECONDS, "heartbeat")
    geometry = session.get("renderer_geometry")
    if not isinstance(geometry, dict):
        raise PreflightGeometryError("Renderer geometry missing.")
    if (geometry.get("boardLogicalSize") != {"width": LOGICAL_WIDTH,
                                             "height": LOGICAL_HEIGHT}
            or geometry.get("renderMode") != "webgl"
            or geometry.get("engineVersion") != "5.4.1"):
        raise PreflightGeometryError("Wrong BoardPane geometry or Egret version.")
    players = geometry.get("players")
    if not isinstance(players, list) or len(players) != 1:
        raise PreflightGeometryError("Exactly one BoardPane is required.")
    player = players[0]
    if player.get("boardClientMappingMethod") not in VALID_MAPPING:
        raise PreflightGeometryError("Board client mapping is unvalidated.")
    cx0, cy0, cx1, cy1 = _rectangle(player.get("boardClientCorners"), "boardClientCorners")
    sx0, sy0, sx1, sy1 = _rectangle(player.get("boardStageCorners"), "boardStageCorners")
    if abs(sx1 - sx0 - LOGICAL_WIDTH) > 1e-5 or abs(sy1 - sy0 - LOGICAL_HEIGHT) > 1e-5:
        raise PreflightGeometryError("Unexpected Stage board extent.")
    if any(type(screen_roi.get(k)) is not int for k in ("x", "y", "width", "height")):
        raise PreflightGeometryError("ROI must contain integer x/y/width/height.")
    rx, ry, width, height = (screen_roi[k] for k in ("x", "y", "width", "height"))
    if rx < 0 or ry < 0 or width <= 1 or height <= 1:
        raise PreflightGeometryError("Invalid ROI.")
    geometry_sha = _geometry_hash(geometry)
    if not isinstance(samples, list) or len(samples) < 3:
        raise PreflightGeometryError("At least three passive pre-run input samples required.")
    offset_x, offset_y, seen = [], [], set()
    for i, sample in enumerate(samples):
        if not isinstance(sample, dict):
            raise PreflightGeometryError("Preflight sample must be a JSON object.")
        if (sample.get("type") != SAMPLE_TYPE
                or sample.get("source") != "window-bubble-after-egret-canvas"
                or sample.get("session_id") != expected_session_id
                or sample.get("renderer_geometry_sha256") != geometry_sha
                or sample.get("buttons") != 0
                or sample.get("pre_drawing") is not True):
            raise PreflightGeometryError(f"Sample {i}: invalid type/source/run/geometry.")
        _age(now, _utc(sample.get("captured_at_utc"), "sample timestamp"),
             MAX_SAMPLE_AGE_SECONDS, "sample timestamp")
        client_x = _number(sample.get("clientX"), "sample.clientX")
        client_y = _number(sample.get("clientY"), "sample.clientY")
        screen_x = _number(sample.get("screenX"), "sample.screenX")
        screen_y = _number(sample.get("screenY"), "sample.screenY")
        if not (cx0 <= client_x <= cx1 and cy0 <= client_y <= cy1):
            raise PreflightGeometryError("Passive sample is outside BoardPane.")
        seen.add((client_x, client_y))
        offset_x.append(screen_x - client_x)
        offset_y.append(screen_y - client_y)
    if len(seen) < 3:
        raise PreflightGeometryError("Require three distinct passive mouse coordinates.")
    ox = sum(offset_x) / len(offset_x)
    oy = sum(offset_y) / len(offset_y)
    if (max(abs(v-ox) for v in offset_x) > MAX_OFFSET_RESIDUAL_PX
            or max(abs(v-oy) for v in offset_y) > MAX_OFFSET_RESIDUAL_PX):
        raise PreflightGeometryError("Client-to-desktop mapping changed during preflight.")
    bx0, by0, bx1, by1 = cx0+ox, cy0+oy, cx1+ox, cy1+oy
    scale_x, scale_y = (bx1-bx0)/LOGICAL_WIDTH, (by1-by0)/LOGICAL_HEIGHT
    if abs(scale_x-scale_y)/max(scale_x, scale_y) > 0.01:
        raise PreflightGeometryError("BoardPane is not uniformly scaled.")
    if (bx1 <= rx or by1 <= ry or bx0 >= rx+width or by0 >= ry+height):
        raise PreflightGeometryError("ROI and current BoardPane have no overlap.")
    if (not isinstance(plan, dict) or plan.get("coordinate_system") != "logical_board_pixels"
            or plan.get("canvas") != {"width": LOGICAL_WIDTH, "height": LOGICAL_HEIGHT}):
        raise PreflightGeometryError("Only a 460x240 logical plan can be mapped.")
    result = deepcopy(plan)
    strokes = result.get("strokes")
    if not isinstance(strokes, list) or not strokes:
        raise PreflightGeometryError("No strokes to map.")
    for stroke in strokes:
        points = stroke.get("points") if isinstance(stroke, dict) else None
        if not isinstance(points, list) or not points:
            raise PreflightGeometryError("Invalid stroke geometry.")
        for point in points:
            if not isinstance(point, dict):
                raise PreflightGeometryError("Invalid point.")
            x = _number(point.get("x"), "stroke.x")
            y = _number(point.get("y"), "stroke.y")
            if not 0 <= x <= LOGICAL_WIDTH or not 0 <= y <= LOGICAL_HEIGHT:
                raise PreflightGeometryError("Logical point outside board.")
            mapped_x = bx0 + x*scale_x - rx
            mapped_y = by0 + y*scale_y - ry
            # These are coordinates relative to the SAME configured executor ROI.
            if not (0 <= mapped_x < width and 0 <= mapped_y < height):
                raise PreflightGeometryError(
                    "Mapped point outside executor ROI: needs recalibration, no clipping.")
            point["x"], point["y"] = mapped_x, mapped_y
    result["coordinate_system"] = "local_canvas_pixels"
    result["canvas"] = {"width": width, "height": height}
    result["width"], result["height"] = width, height
    generation = result.setdefault("generation", {})
    if not isinstance(generation, dict):
        raise PreflightGeometryError("Invalid generation metadata.")
    evidence_sha = hashlib.sha256(
        json.dumps(samples, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    mapping = {
        "schema": SCHEMA,
        "status": "validated_preflight_input_transform_not_live_draw",
        "session_id": expected_session_id,
        "renderer_geometry_sha256": geometry_sha,
        "passive_samples_sha256": evidence_sha,
        "passive_sample_count": len(samples),
        "client_to_desktop_offset": {"x": ox, "y": oy},
        "board_screen_corners": {"left": bx0, "top": by0, "right": bx1, "bottom": by1},
        "screen_roi": dict(screen_roi),
        "method": "same_session_passive_DOM_mouse_plus_validated_BoardPane_corners",
        "no_fallback": True,
        "preflight_valid_at_utc": now.isoformat(),
    }
    generation["screen_transform"] = mapping
    return result, mapping

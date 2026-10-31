from __future__ import annotations

"""Closed-loop brush-radius feedback helpers.

The slider coordinate is only an initial estimate. The game-reported radius is
the authority; correction coordinates are calculated from a monotonic bracket.
"""

from typing import Any


def monitor_radius_from_status(status: object) -> int | None:
    """Extract the scalar current radius from AutoDrawGameMonitor.status()."""
    if not isinstance(status, dict):
        return None
    snapshot = status.get("snapshot")
    if not isinstance(snapshot, dict):
        snapshot = status
    value = snapshot.get("currentRadius")
    if value is None:
        value = snapshot.get("radius")
    if isinstance(value, (list, tuple)):
        value = value[-1] if value else None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        numeric = float(value)
        if not numeric.is_integer() or not 1 <= numeric <= 30:
            return None
    except (TypeError, ValueError, OverflowError):
        return None
    return int(numeric)



def read_active_bridge_radius(
    bridge_root: str | Any,
    *,
    after_utc: str | None = None,
    max_age_seconds: float = 4.0,
) -> dict[str, Any] | None:
    """Read the newest fresh radius from an active Game Monitor Bridge session."""
    import json
    from datetime import datetime, timezone
    from pathlib import Path

    def parse_stamp(value: object) -> datetime | None:
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            stamp = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return stamp.astimezone(timezone.utc)

    root = Path(bridge_root)
    if not root.is_dir():
        return None
    after = parse_stamp(after_utc) if after_utc else None
    now = datetime.now(timezone.utc)
    candidates: list[tuple[datetime, dict[str, Any]]] = []
    for session_path in root.glob("*/session.json"):
        try:
            record = json.loads(session_path.read_text(encoding="utf-8"))
            diagnostics = record.get("bridge_diagnostics", {})
            if not isinstance(diagnostics, dict) or diagnostics.get("connection_closed") is True:
                continue
            if diagnostics.get("last_message_type") != "heartbeat":
                continue
            stamp_text = diagnostics.get("last_message_at_utc")
            stamp = parse_stamp(stamp_text)
            if stamp is None or (now - stamp).total_seconds() > max_age_seconds:
                continue
            if after is not None and stamp <= after:
                continue
            status = diagnostics.get("last_monitor_status")
            radius = monitor_radius_from_status(status)
            if radius is None:
                continue
            candidates.append((stamp, {
                "radius": radius,
                "session_id": record.get("session_id"),
                "observed_at_utc": stamp_text,
                "snapshot": status.get("snapshot") if isinstance(status, dict) else None,
            }))
        except (OSError, ValueError, TypeError, AttributeError):
            continue
    return max(candidates, key=lambda item: item[0])[1] if candidates else None

def calculate_radius_correction_target(
    high_point: tuple[int, int] | list[int],
    high_radius: int,
    low_point: tuple[int, int] | list[int],
    low_radius: int,
    requested_radius: int,
) -> tuple[int, int]:
    """Use a bounded secant step between known higher- and lower-radius positions."""
    if not (1 <= low_radius < requested_radius < high_radius <= 30):
        raise ValueError("Для коррекции нужны границы: low < requested < high.")
    if not (isinstance(high_point, (tuple, list)) and len(high_point) == 2):
        raise ValueError("Точка верхней границы должна содержать X и Y.")
    if not (isinstance(low_point, (tuple, list)) and len(low_point) == 2):
        raise ValueError("Точка нижней границы должна содержать X и Y.")
    hx, hy = int(high_point[0]), int(high_point[1])
    lx, ly = int(low_point[0]), int(low_point[1])
    ratio = (high_radius - requested_radius) / (high_radius - low_radius)
    candidate = (round(hx + (lx - hx) * ratio), round(hy + (ly - hy) * ratio))
    if candidate in {(hx, hy), (lx, ly)}:
        candidate = (round((hx + lx) / 2), round((hy + ly) / 2))
    if candidate in {(hx, hy), (lx, ly)}:
        raise ValueError("Разрешения координат ползунка недостаточно для дальнейшей коррекции.")
    return candidate

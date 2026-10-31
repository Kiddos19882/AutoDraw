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
    if int(value) != value or not 1 <= int(value) <= 30:
        return None
    return int(value)


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

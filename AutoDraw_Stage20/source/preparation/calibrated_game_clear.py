"""Shared calibrated game Clear action, extracted from the existing brush lab.

ENGINE-001 used the game's normal Clear UI via calibrated pyautogui.click,
followed by a settled screenshot and evaluate_board_clear. This function
centralizes ONLY that already-existing action; it does not access game internals,
invent DOM selectors, or substitute Monitor.clear() for a board reset.
"""
from __future__ import annotations

from typing import Any, Callable


class CalibratedClearBlocked(ValueError):
    pass


def click_calibrated_board_clear(
    profile: dict[str, Any],
    *,
    screen_size: tuple[int, int],
    click: Callable[[int, int], None],
    foreground_verified: Callable[[], bool],
    stop_requested: Callable[[], bool],
) -> dict[str, Any]:
    """Perform one legacy calibrated Clear UI click, without implicit retries.

    Same calibration profile keys as BrushBehaviorTestTab. The caller is
    responsible for already obtaining one-time operator consent, maintaining
    Firefox focus, and verifying screenshot + exact counters after the click.
    """
    if not isinstance(profile, dict):
        raise CalibratedClearBlocked("Missing brush-test calibration profile")
    if (not isinstance(screen_size, tuple) or len(screen_size) != 2
            or any(type(v) is not int or v <= 0 for v in screen_size)):
        raise CalibratedClearBlocked("Invalid physical screen size")
    expected = profile.get("screen_size")
    if (not isinstance(expected, dict)
            or (expected.get("width"), expected.get("height")) != screen_size):
        raise CalibratedClearBlocked("Calibrated screen size no longer matches desktop")
    points = profile.get("points")
    status = profile.get("status")
    states = status.get("points") if isinstance(status, dict) else None
    clear = points.get("clear_board") if isinstance(points, dict) else None
    if (not isinstance(clear, dict) or not isinstance(states, dict)
            or states.get("clear_board") != "confirmed"
            or any(type(clear.get(a)) is not int for a in ("x", "y"))):
        raise CalibratedClearBlocked("Game Clear coordinate is missing or not confirmed")
    x,y = clear["x"],clear["y"]
    if not (0 <= x < screen_size[0] and 0 <= y < screen_size[1]):
        raise CalibratedClearBlocked("Game Clear coordinate outside desktop")
    if (not callable(click) or not callable(foreground_verified)
            or not callable(stop_requested)
            or stop_requested() is True
            or foreground_verified() is not True):
        raise CalibratedClearBlocked("Clear requires explicit consent, focus and active stop gate")
    # This is the original game UI action. Never call Monitor.clear() here.
    click(x, y)
    return {
        "schema": "AUTODRAW_CALIBRATED_GAME_CLEAR_CLICK_V1",
        "action": "normal_game_ui_clear",
        "screen_x": x, "screen_y": y,
        "click_sent": True,
        "board_cleared_verified": False,
    }

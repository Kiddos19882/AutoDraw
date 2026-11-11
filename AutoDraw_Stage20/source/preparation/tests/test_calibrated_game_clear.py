"""Regression of the existing ENGINE-001 calibrated game Clear click contract.

The tests inject the existing single-click action; they never touch the game.
"""
import pytest

from calibrated_game_clear import (
    CalibratedClearBlocked, click_calibrated_board_clear,
)


def profile(state="set"):
    return {
        "screen_size": {"width": 1920, "height": 1080},
        "points": {"clear_board": {"x": 1500, "y": 175}},
        "status": {"points": {"clear_board": state}},
        "needs_review": False,
    }


@pytest.mark.parametrize("status", ["set", "confirmed"])
def test_existing_calibrated_game_clear_click_reused(status):
    clicks = []
    result = click_calibrated_board_clear(
        profile(status), screen_size=(1920, 1080),
        click=lambda x, y: clicks.append((x, y)),
        foreground_verified=lambda: True,
        stop_requested=lambda: False,
    )
    assert clicks == [(1500, 175)]
    assert result["action"] == "normal_game_ui_clear"
    assert result["click_sent"] is True
    assert result["board_cleared_verified"] is False


@pytest.mark.parametrize("modify", [
    lambda p: p.update(needs_review=True),
    lambda p: p["status"]["points"].update(clear_board="needs_review"),
    lambda p: p["points"]["clear_board"].update(x=4000),
    lambda p: p["screen_size"].update(width=2560),
    lambda p: p["points"]["clear_board"].update(x=True),
])
def test_never_click_when_previous_profile_invalid(modify):
    p = profile()
    modify(p)
    calls = []
    with pytest.raises(CalibratedClearBlocked):
        click_calibrated_board_clear(
            p, screen_size=(1920, 1080),
            click=lambda *a: calls.append(a),
            foreground_verified=lambda: True,
            stop_requested=lambda: False,
        )
    assert not calls


@pytest.mark.parametrize("foreground,stop", [(False, False), (True, True)])
def test_no_click_on_wrong_window_or_stop(foreground, stop):
    clicks = []
    with pytest.raises(CalibratedClearBlocked):
        click_calibrated_board_clear(
            profile(), screen_size=(1920, 1080),
            click=lambda *a: clicks.append(a),
            foreground_verified=lambda: foreground,
            stop_requested=lambda: stop,
        )
    assert clicks == []

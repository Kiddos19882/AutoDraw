"""Synthetic-only reuse tests for proven ENGINE-001 calibrated game Clear."""
from datetime import datetime, timedelta, timezone

import pytest
from PIL import Image

from fill001_series_engine001_clear import (
    SeriesClearBlocked, clear_with_existing_engine001,
)


def snap(n, second):
    return {
        "session_id": "persistent", "mapping_sha256": "a"*64,
        "pointCount": n, "maxPoints": 6000, "remainingPoints": 6000-n,
        "isExact": True, "captured_at_utc": (
            datetime(2026, 11, 11, tzinfo=timezone.utc)
            + timedelta(seconds=second)
        ).isoformat(),
    }


def setup(tmp_path, *, dirty=False):
    img = Image.new("RGB", (200, 200), (20, 20, 20))
    baseline = tmp_path / "blank-board-reference.png"
    img.save(baseline)
    after = img.copy()
    if dirty:
        # Within historical ENGINE-001 <=0.15% tolerance.
        after.putpixel((50, 50), (255, 255, 255))
    profile = {
        "screen_size": {"width": 1920, "height": 1080},
        "regions": {"board_area": {"x": 400, "y": 200, "width": 200, "height": 200}},
        "points": {"clear_board": {"x": 1500, "y": 175}},
        "status": {"points": {"clear_board": "set"}},
        "needs_review": False,
    }
    metadata = {
        "reference_type": "user_confirmed_blank_board_roi",
        "user_confirmed_blank": True,
        "screen_size": profile["screen_size"],
        "board_region": profile["regions"]["board_area"],
        "image_file": baseline.name,
    }
    return baseline, after, profile, metadata


@pytest.mark.parametrize("one_changed_pixel", [False, True])
def test_reuse_original_engine001_clear_not_stricter_new_threshold(tmp_path, one_changed_pixel):
    reference, screenshot, profile, meta = setup(tmp_path, dirty=one_changed_pixel)
    clicks = []
    next_snapshot = iter([snap(1, 1), snap(1, 2)])
    result = clear_with_existing_engine001(
        profile=profile, reference_png=reference, reference_metadata=meta,
        session_id="persistent", mapping_sha256="a"*64,
        pre_clear_snapshot=snap(100, 0),
        live_snapshot=lambda: next(next_snapshot),
        grab_board_roi=lambda: screenshot.copy(),
        click=lambda x, y: clicks.append((x, y)),
        foreground_verified=lambda: True, stop_requested=lambda: False,
        wait_settle=lambda: None,
        after_clear_png=tmp_path / "after-clear.png",
        mouse_released=True,
    )
    assert clicks == [(1500, 175)]
    assert result["pointCount"] == 1
    proof = result["blank_screen_verification"]
    assert proof["schema"] == "FILL001_SERIES_ENGINE001_CLEAR_REUSE_V1"
    assert proof["engine001_visual_status"] in ("restored", "restored_within_pixel_tolerance")
    assert proof["engine001_tolerance_percent"] == 0.15
    assert (tmp_path / "after-clear.png").is_file()


@pytest.mark.parametrize("invalid", [
    "reference_metadata", "profile_changed", "mouse_pressed", "bad_pre_count",
    "wrong_session", "changed_mapping", "wrong_focus", "stop",
])
def test_unsafe_clear_refuses_game_input(tmp_path, invalid):
    reference, screenshot, profile, meta = setup(tmp_path)
    clicks = []
    if invalid == "reference_metadata":
        meta["user_confirmed_blank"] = False
    if invalid == "profile_changed":
        profile["needs_review"] = True
    params = dict(
        profile=profile, reference_png=reference, reference_metadata=meta,
        session_id="persistent", mapping_sha256="a"*64,
        pre_clear_snapshot=snap(1 if invalid == "bad_pre_count" else 100, 0),
        live_snapshot=lambda: snap(1, 1), grab_board_roi=lambda: screenshot.copy(),
        click=lambda x, y: clicks.append((x, y)),
        foreground_verified=lambda: invalid != "wrong_focus",
        stop_requested=lambda: invalid == "stop",
        wait_settle=lambda: None,
        after_clear_png=tmp_path / "after-clear.png",
        mouse_released=(invalid != "mouse_pressed"),
    )
    if invalid == "wrong_session":
        params["pre_clear_snapshot"]["session_id"] = "foreign"
    if invalid == "changed_mapping":
        params["pre_clear_snapshot"]["mapping_sha256"] = "b"*64
    with pytest.raises((SeriesClearBlocked, ValueError)):
        clear_with_existing_engine001(**params)
    assert clicks == []


def test_counter_not_restored_blocks_after_single_click(tmp_path):
    reference, screenshot, profile, meta = setup(tmp_path)
    clicks = []
    with pytest.raises(SeriesClearBlocked, match="did not reset"):
        clear_with_existing_engine001(
            profile=profile, reference_png=reference, reference_metadata=meta,
            session_id="persistent", mapping_sha256="a"*64,
            pre_clear_snapshot=snap(100, 0),
            live_snapshot=lambda: snap(100, 1),
            grab_board_roi=lambda: screenshot,
            click=lambda x, y: clicks.append((x, y)),
            foreground_verified=lambda: True, stop_requested=lambda: False,
            wait_settle=lambda: None,
            after_clear_png=tmp_path / "after-clear.png",
            mouse_released=True,
        )
    assert clicks == [(1500, 175)]
    assert not (tmp_path / "after-clear.png").exists()


def test_rejected_clear_preserves_visual_metrics_and_png_but_never_passes(tmp_path):
    reference, screenshot, profile, meta = setup(tmp_path)
    # 100 / 40000 changed pixels = 0.25%, above frozen 0.15% threshold.
    for x in range(100):
        screenshot.putpixel((x, 0), (255, 255, 255))
    calls = []
    snapshots = iter([snap(1, 1), snap(1, 2)])
    target = tmp_path / "after-clear.png"
    with pytest.raises(SeriesClearBlocked, match="rejected Clear") as err:
        clear_with_existing_engine001(
            profile=profile, reference_png=reference, reference_metadata=meta,
            session_id="persistent", mapping_sha256="a"*64,
            pre_clear_snapshot=snap(100, 0),
            live_snapshot=lambda: next(snapshots),
            grab_board_roi=lambda: screenshot.copy(),
            click=lambda x, y: calls.append((x, y)),
            foreground_verified=lambda: True, stop_requested=lambda: False,
            wait_settle=lambda: None,
            after_clear_png=target, mouse_released=True,
        )
    message = str(err.value)
    assert "status=not_restored" in message
    assert "changed_percent=0.25" in message
    assert "tolerance_percent=0.15" in message
    assert "changed_pixels=100" in message
    assert "total_pixels=40000" in message
    assert "reference_sha256=" in message
    assert "after_clear_sha256=" in message
    assert calls == [(1500, 175)]
    assert target.is_file()
    # The rejected comparator must not return valid Clear proof or schedule
    # another click / game stroke, even when exact counters are already blank.

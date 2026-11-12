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


def test_boardpane_series_reference_uses_verified_native_roi_not_manual_profile(tmp_path):
    from fill001_series_engine001_clear import (
        capture_verified_series_boardpane_blank, require_same_series_boardpane_roi,
    )
    import json
    screen = Image.new("RGB", (800, 600), (120, 30, 30))  # UI red
    # The only game board is in the witness ROI, not at any manual coordinates.
    for y in range(120, 320):
        for x in range(170, 470):
            screen.putpixel((x, y), (25, 25, 25))
    roi = {"x": 170, "y": 120, "width": 300, "height": 200}
    filename = tmp_path / "boardpane-blank" / "blank-board-reference.png"
    metadata_path = filename.with_suffix(".json")
    record = capture_verified_series_boardpane_blank(
        roi=roi, screen_size={"width": 800, "height": 600},
        session_id="live-sid", mapping_sha256="a"*64, point_count=1,
        operator_confirmed=True, grab_screen=lambda: screen.copy(),
        reference_png=filename, metadata_path=metadata_path,
    )
    assert record["board_region"] == roi
    assert record["source"] == "verified_boardpane_native_probe"
    assert json.loads(metadata_path.read_text(encoding="utf-8")) == record
    with Image.open(filename) as blank:
        assert blank.size == (300, 200)
        assert blank.getpixel((0, 0)) == (25, 25, 25)
        assert blank.getpixel((299, 199)) == (25, 25, 25)
    assert require_same_series_boardpane_roi(
        roi, record, session_id="live-sid", mapping_sha256="a"*64,
    ) == roi
    with pytest.raises(SeriesClearBlocked, match="overwrite forbidden"):
        capture_verified_series_boardpane_blank(
            roi=roi, screen_size={"width": 800, "height": 600},
            session_id="live-sid", mapping_sha256="a"*64, point_count=1,
            operator_confirmed=True, grab_screen=lambda: screen,
            reference_png=filename, metadata_path=metadata_path,
        )


@pytest.mark.parametrize("change", [
    "shifted_roi", "other_session", "changed_mapping",
])
def test_series_boardpane_blank_rejects_moved_window_or_other_session(tmp_path, change):
    from fill001_series_engine001_clear import (
        capture_verified_series_boardpane_blank, require_same_series_boardpane_roi,
    )
    roi = {"x": 100, "y": 50, "width": 120, "height": 80}
    record = capture_verified_series_boardpane_blank(
        roi=roi, screen_size={"width": 640, "height": 480},
        session_id="sid", mapping_sha256="b"*64, point_count=1,
        operator_confirmed=True,
        grab_screen=lambda: Image.new("RGB", (640, 480)),
        reference_png=tmp_path / "baseline.png",
        metadata_path=tmp_path / "baseline.json",
    )
    new_roi = {**roi, "x": 101} if change == "shifted_roi" else roi
    sid = "sid-other" if change == "other_session" else "sid"
    mapping = "c"*64 if change == "changed_mapping" else "b"*64
    with pytest.raises(SeriesClearBlocked, match="differs"):
        require_same_series_boardpane_roi(
            new_roi, record, session_id=sid, mapping_sha256=mapping,
        )


@pytest.mark.parametrize("change", [
    "not_blank", "unconfirmed", "outside_screen", "screen_mismatch",
])
def test_series_boardpane_blank_refuses_invalid_evidence(tmp_path, change):
    from fill001_series_engine001_clear import capture_verified_series_boardpane_blank
    roi = {"x": 100, "y": 50, "width": 120, "height": 80}
    props = dict(
        roi=roi, screen_size={"width": 640, "height": 480},
        session_id="sid", mapping_sha256="b"*64, point_count=1,
        operator_confirmed=True,
        grab_screen=lambda: Image.new("RGB", (640, 480)),
        reference_png=tmp_path / "blank.png",
        metadata_path=tmp_path / "blank.json",
    )
    if change == "not_blank":
        props["point_count"] = 55
    elif change == "unconfirmed":
        props["operator_confirmed"] = False
    elif change == "outside_screen":
        props["roi"] = {**roi, "x": 610}
    elif change == "screen_mismatch":
        props["grab_screen"] = lambda: Image.new("RGB", (800, 600))
    with pytest.raises(SeriesClearBlocked):
        capture_verified_series_boardpane_blank(**props)
    assert not (tmp_path / "blank.png").exists()


def test_reuse_native_boardpane_crop_for_after_clear_and_blank(tmp_path):
    from fill001_series_engine001_clear import (
        capture_verified_series_boardpane_blank, capture_same_boardpane_roi,
    )
    roi = {"x": 170, "y": 120, "width": 300, "height": 200}
    full = Image.new("RGB", (800, 600), (200, 60, 60))
    full.paste(Image.new("RGB", (300, 200), (14, 26, 38)), (170, 120))
    screen_size = {"width": 800, "height": 600}
    reference = tmp_path / "series-board-blank.png"
    meta = capture_verified_series_boardpane_blank(
        roi=roi, screen_size=screen_size, session_id="sid",
        mapping_sha256="a"*64, point_count=1, operator_confirmed=True,
        grab_screen=lambda: full.copy(), reference_png=reference,
        metadata_path=tmp_path / "series-board-blank.json",
    )
    image = capture_same_boardpane_roi(
        roi=roi, reference_metadata=meta, session_id="sid",
        mapping_sha256="a"*64, screen_size=screen_size,
        grab_screen=lambda: full.copy(),
    )
    with Image.open(reference) as first:
        assert first.tobytes() == image.tobytes()
    assert image.size == (300, 200)
    assert image.getpixel((0, 0)) == (14, 26, 38)


@pytest.mark.parametrize("invalid", [
    "shifted", "session", "mapping", "resolution", "wrong_screen",
    "out_of_bounds", "invalid_image",
])
def test_native_boardpane_crop_never_falls_back_to_manual_roi(tmp_path, invalid):
    from fill001_series_engine001_clear import (
        capture_verified_series_boardpane_blank, capture_same_boardpane_roi,
    )
    roi = {"x": 40, "y": 30, "width": 120, "height": 80}
    size = {"width": 640, "height": 480}
    meta = capture_verified_series_boardpane_blank(
        roi=roi, screen_size=size, session_id="sid",
        mapping_sha256="b"*64, point_count=1, operator_confirmed=True,
        grab_screen=lambda: Image.new("RGB", (640, 480)),
        reference_png=tmp_path / "baseline.png",
        metadata_path=tmp_path / "baseline.json",
    )
    kwargs = dict(
        roi=roi, reference_metadata=meta, session_id="sid",
        mapping_sha256="b"*64, screen_size=size,
        grab_screen=lambda: Image.new("RGB", (640, 480)),
    )
    if invalid == "shifted":
        kwargs["roi"] = {**roi, "x": 41}
    elif invalid == "session":
        kwargs["session_id"] = "other"
    elif invalid == "mapping":
        kwargs["mapping_sha256"] = "c"*64
    elif invalid == "resolution":
        kwargs["screen_size"] = {"width": 800, "height": 600}
    elif invalid == "wrong_screen":
        kwargs["grab_screen"] = lambda: Image.new("RGB", (800, 600))
    elif invalid == "out_of_bounds":
        kwargs["roi"] = {**roi, "x": 630}
        kwargs["reference_metadata"] = {**meta, "board_region": kwargs["roi"]}
    elif invalid == "invalid_image":
        kwargs["grab_screen"] = lambda: None
    with pytest.raises(SeriesClearBlocked):
        capture_same_boardpane_roi(**kwargs)

"""Offline-only tests for read-only post-Clear blank-screen verifier."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from fill001_series_blank_verification import (
    BlankVerificationError, verify_blank_screen_after_clear,
)

SID = "series-session-1"
MAPPING = "a" * 64


def snap(n, seconds):
    return {
        "session_id": SID,
        "mapping_sha256": MAPPING,
        "isExact": True,
        "pointCount": n,
        "maxPoints": 6000,
        "remainingPoints": 6000 - n,
        "captured_at_utc": (
            datetime(2026, 11, 11, tzinfo=timezone.utc)
            + timedelta(seconds=seconds)
        ).isoformat(),
    }


def test_exact_png_and_settled_counter_pass(tmp_path):
    p = tmp_path / "blank.png"
    after = tmp_path / "after.png"
    rgb = np.zeros((20, 40, 3), dtype=np.uint8)
    rgb[:, :] = [10, 30, 50]
    Image.fromarray(rgb).save(p)
    Image.fromarray(rgb).save(after)
    result = verify_blank_screen_after_clear(
        session_id=SID,
        mapping_sha256=MAPPING,
        reference_blank_png=p,
        after_clear_png=after,
        reference_blank_snapshot=snap(1, -1), pre_clear_snapshot=snap(1707, 0),
        settled_snapshots=[snap(1, 1), snap(1, 2)],
        cursor_parked_off_roi=True,
        mouse_released=True,
    )
    assert result["status"] == "PASS"
    assert result["changed_screen_pixels"] == 0
    assert result["post_clear_pointCount"] == 1
    assert result["clear_ui_action_proven"] is False
    assert result["live_clear_operation_executed_by_verifier"] is False


@pytest.mark.parametrize("tamper", [
    lambda pre, post: pre.update(pointCount=1, remainingPoints=5999),
    lambda pre, post: post[0].update(pointCount=2, remainingPoints=5998),
    lambda pre, post: post[1].update(isExact=False),
    lambda pre, post: post[1].update(maxPoints=7000),
    lambda pre, post: post[1].update(session_id="other"),
    lambda pre, post: post[0].update(mapping_sha256="b" * 64),
    lambda pre, post: post[1].update(captured_at_utc=pre["captured_at_utc"]),
])
def test_counter_provenance_fail_closed(tmp_path, tamper):
    a, b = tmp_path / "blank.png", tmp_path / "after.png"
    rgb = np.zeros((8, 10, 3), dtype=np.uint8)
    Image.fromarray(rgb).save(a)
    Image.fromarray(rgb).save(b)
    pre, post = snap(200, 0), [snap(1, 1), snap(1, 2)]
    tamper(pre, post)
    with pytest.raises(BlankVerificationError):
        verify_blank_screen_after_clear(
            session_id=SID, mapping_sha256=MAPPING,
            reference_blank_png=a, after_clear_png=b,
            reference_blank_snapshot=snap(1, -1), pre_clear_snapshot=pre, settled_snapshots=post,
            cursor_parked_off_roi=True, mouse_released=True,
        )


def test_visible_residual_never_accepted_even_if_counter_reset(tmp_path):
    a, b = tmp_path / "blank.png", tmp_path / "after.png"
    first = np.full((8, 10, 3), 100, dtype=np.uint8)
    last = first.copy()
    last[3, 4, 1] = 101
    Image.fromarray(first).save(a)
    Image.fromarray(last).save(b)
    with pytest.raises(BlankVerificationError, match="differs"):
        verify_blank_screen_after_clear(
            session_id=SID, mapping_sha256=MAPPING,
            reference_blank_png=a, after_clear_png=b,
            reference_blank_snapshot=snap(1, -1), pre_clear_snapshot=snap(200, 0),
            settled_snapshots=[snap(1, 1), snap(1, 2)],
            cursor_parked_off_roi=True, mouse_released=True,
        )


@pytest.mark.parametrize("kwargs", [
    {"cursor_parked_off_roi": False},
    {"mouse_released": False},
    {"allow_rgb_pixel_differences": 1},
    {"allow_rgb_pixel_differences": True},
])
def test_no_unsafe_tolerance_or_pointer_state(tmp_path, kwargs):
    a = tmp_path / "same.png"
    Image.fromarray(np.zeros((8, 10, 3), dtype=np.uint8)).save(a)
    params = {
        "session_id": SID, "mapping_sha256": MAPPING,
        "reference_blank_png": a, "after_clear_png": a,
        "reference_blank_snapshot": snap(1, -1),
        "pre_clear_snapshot": snap(200, 0),
        "settled_snapshots": [snap(1, 1), snap(1, 2)],
        "cursor_parked_off_roi": True, "mouse_released": True,
    }
    params.update(kwargs)
    with pytest.raises(BlankVerificationError):
        verify_blank_screen_after_clear(**params)

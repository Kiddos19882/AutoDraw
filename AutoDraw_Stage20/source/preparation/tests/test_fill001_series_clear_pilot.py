"""Synthetic Clear pilot evidence must not be mistaken for automated UI validation."""
from datetime import datetime, timedelta, timezone
import json

from PIL import Image
import numpy as np

from fill001_series_clear_pilot import evaluate_clear_pilot, write_clear_pilot


def snap(points, seconds):
    return {
        "session_id": "session-1", "mapping_sha256": "a"*64,
        "isExact": True, "pointCount": points,
        "maxPoints": 6000, "remainingPoints": 6000-points,
        "captured_at_utc": (
            datetime(2026, 11, 11, tzinfo=timezone.utc) +
            timedelta(seconds=seconds)
        ).isoformat(),
    }


def evidence(tmp_path):
    p = tmp_path / "reference.png"
    q = tmp_path / "after.png"
    pixels = np.zeros((12, 20, 3), dtype=np.uint8)
    pixels[:] = [11, 13, 17]
    Image.fromarray(pixels).save(p)
    Image.fromarray(pixels).save(q)
    return {
        "session_id": "session-1", "mapping_sha256": "a"*64,
        "reference_blank_png": str(p), "after_clear_png": str(q),
        "reference_blank_snapshot": snap(1, -1),
        "pre_clear_snapshot": snap(1240, 0),
        "settled_snapshots": [snap(1, 1), snap(1, 2)],
        "cursor_parked_off_roi": True,
        "mouse_released": True,
    }


def test_screen_pilot_pass_is_not_clear_ui_pass(tmp_path):
    data = evidence(tmp_path)
    result = evaluate_clear_pilot(data)
    assert result["status"] == "SCREEN_AND_COUNTER_PASS"
    assert result["blank_screen_proof"]["changed_screen_pixels"] == 0
    assert result["e4_live_clear_action_verified"] is False
    assert result["game_clear_click_executed_by_tool"] is False
    path = write_clear_pilot(data, tmp_path / "evidence")
    assert json.loads(path.read_text(encoding="utf-8"))["status"] == "SCREEN_AND_COUNTER_PASS"


def test_negative_pilot_persisted(tmp_path):
    data = evidence(tmp_path)
    data["settled_snapshots"][-1]["remainingPoints"] = 5998
    path = write_clear_pilot(data, tmp_path / "evidence")
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["status"] == "BLOCKED"
    assert "reason" in report
    assert report["blank_screen_proof"] is None

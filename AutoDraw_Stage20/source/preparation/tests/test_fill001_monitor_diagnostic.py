from __future__ import annotations

import copy
import json
from pathlib import Path

from PIL import Image
import pytest

from fill001_monitor_diagnostic import (
    PROTOCOL, BASELINE_PLAN_SIGNATURE, BASELINE_MASK_SHA256,
    _valid_board_geometry, _valid_rgb_pair, audit_diagnostic_capture,
    validate_baseline_task,
)


def _task():
    return {
        "phase_id": "FILL001", "plan_variant": "FILL001_RS_V1",
        "shape_id": "rectangle", "requested_radius": 10,
        "scanline_row_step": 5, "scanline_offset": 0,
        "expected_strokes": 27, "plan_signature": BASELINE_PLAN_SIGNATURE,
        "target_mask_sha256": BASELINE_MASK_SHA256,
        "repeat_index": 1, "capture_status": "pending", "task_id": "new-rep1",
    }


def _geometry():
    corners = {
        "topLeft": {"x": 100.0, "y": 200.0},
        "topRight": {"x": 560.0, "y": 200.0},
        "bottomRight": {"x": 560.0, "y": 440.0},
        "bottomLeft": {"x": 100.0, "y": 440.0},
    }
    return {
        "boardLogicalSize": {"width": 460, "height": 240}, "renderMode": "webgl",
        "players": [{
            "boardClientMappingMethod": "validated_axis_aligned_rect",
            "boardStageCorners": copy.deepcopy(corners),
            "boardClientCorners": copy.deepcopy(corners),
        }],
    }


def _screens(tmp_path):
    roi = {"x": 10, "y": 20, "width": 30, "height": 20}
    full = tmp_path / "full.png"
    crop = tmp_path / "roi.png"
    with Image.new("RGB", (60, 50), (255, 255, 255)) as screen:
        screen.save(full)
        screen.crop((10, 20, 40, 40)).save(crop)
    return full, crop, roi


def test_baseline_and_geometry_fail_closed():
    task = _task()
    validate_baseline_task(task)
    assert _valid_board_geometry(_geometry()) is True
    changed = dict(task, scanline_row_step=4)
    with pytest.raises(ValueError, match="frozen RS"):
        validate_baseline_task(changed)
    wrong = _geometry()
    wrong["players"][0]["boardClientMappingMethod"] = "unavailable"
    assert not _valid_board_geometry(wrong)


def test_full_screen_png_must_match_same_frame_roi(tmp_path):
    full, crop, roi = _screens(tmp_path)
    result = _valid_rgb_pair(full, crop, roi)
    assert result["roi_size"] == [30, 20]
    with Image.new("RGB", (30, 20), (0, 0, 0)) as changed:
        changed.save(crop)
    with pytest.raises(ValueError, match="same frame"):
        _valid_rgb_pair(full, crop, roi)


def test_diagnostic_run_rejects_unbound_telemetry(tmp_path):
    full, crop, roi = _screens(tmp_path)
    path = tmp_path / "run.json"
    path.write_text(json.dumps({
        "session_id": "unrelated-session",
        "run_id": "run-1",
        "stroke_count": 27,
        "chalk": {"status": "exact", "consumed_points": 1260},
        "events": [], "event_count": 0,
    }), encoding="utf-8")
    result = audit_diagnostic_capture(
        task=_task(), readiness={
            "protocol": PROTOCOL, "session_id": "the-real-session",
            "renderer_geometry_sha256": "0" * 64,
        }, monitor_run_path=path, before_full=full, before_roi=crop,
        after_full=full, after_roi=crop, screen_roi=roi,
    )
    assert result["status"] == "PARTIAL"
    assert "run_session_or_27_stroke_identity_invalid" in result["reasons"]
    assert "exact_chalk_binding_invalid" in result["reasons"]
    assert "accepted_stream_not_one_to_one" in result["reasons"]
    assert "mouse_input_telemetry_missing" in result["reasons"]
    assert "same_run_native_geometry_unstable_or_missing" in result["reasons"]
    assert result["exact_chalk"] == 1260
    assert result["before"]["full_screen_sha256"] == result["after"]["full_screen_sha256"]

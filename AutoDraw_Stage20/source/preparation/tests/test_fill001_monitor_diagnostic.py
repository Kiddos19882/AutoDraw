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


def test_diagnostic_preflight_requires_fresh_exact_budget_and_native_geometry(tmp_path, monkeypatch):
    import fill001_monitor_diagnostic as diag

    session_file = tmp_path / "session.json"
    session = {
        "session_id": "valid-session",
        "monitor_status_at_connect": {"version": "0.2.4"},
        "renderer_geometry": _geometry(),
        "bridge_diagnostics": {
            "last_monitor_status": {"snapshot": {
                "isExact": True, "remainingPoints": 5999,
            }},
        },
    }
    session_file.write_text(json.dumps(session), encoding="utf-8")
    monkeypatch.setattr(diag, "inspect_ready_bridge", lambda _root: {
        "session_id": "valid-session",
        "session_path": str(session_file),
        "heartbeat_at_utc": "2026-11-08T00:00:00+00:00",
    })
    result = diag.inspect_diagnostic_preflight(tmp_path, _task())
    assert result["protocol"] == PROTOCOL
    assert result["observed_remaining_points"] == 5999
    assert result["minimum_remaining_points_required"] == 1600
    session["bridge_diagnostics"]["last_monitor_status"]["snapshot"]["remainingPoints"] = 1300
    session_file.write_text(json.dumps(session), encoding="utf-8")
    with pytest.raises(ValueError, match="1600 points"):
        diag.inspect_diagnostic_preflight(tmp_path, _task())
    session["bridge_diagnostics"]["last_monitor_status"]["snapshot"]["remainingPoints"] = 5000
    session["renderer_geometry"]["players"][0]["boardClientMappingMethod"] = "unavailable"
    session_file.write_text(json.dumps(session), encoding="utf-8")
    with pytest.raises(ValueError, match="verified client corners"):
        diag.inspect_diagnostic_preflight(tmp_path, _task())


def test_complete_27_stroke_raw_monitor_and_screen_evidence_can_pass(tmp_path):
    import fill001_monitor_diagnostic as diag

    full, roi_image, roi = _screens(tmp_path)
    after_full, after_crop = tmp_path / "after-full.png", tmp_path / "after-roi.png"
    with Image.open(full) as source:
        updated = source.copy()
    updated.putpixel((15, 25), (0, 0, 0))
    updated.save(after_full)
    updated.crop((10, 20, 40, 40)).save(after_crop)
    geometry = _geometry()
    events, accepted, mode_rows, frame_rows = [], [], [], []
    t = 0
    for i in range(27):
        stroke_id = f"pointer-stroke-{i+1}"
        for j in range(2):
            t += 1
            point = {"x": float(50+i+j), "y": float(70+i),
                     "t": float(t), "stroke_id": stroke_id, "point_delta": 1}
            accepted.append(point)
            events.append({
                "monitorVersion": "0.2.4", "type": "DRAW_SAMPLE", "t": t,
                "strokeId": stroke_id, "pointDelta": 1,
                "acceptedPoint": {"x": point["x"], "y": point["y"]},
            })
        t += 1
        events.append({
            "monitorVersion": "0.2.4", "type": "ENGINE_FRAME_SAMPLE", "t": t,
            "strokeId": stroke_id, "strokeOptionRaw": True,
        })
        t += 1
        events.append({
            "monitorVersion": "0.2.4", "type": "MOUSE_MOVE_SAMPLE", "t": t,
            "strokeId": stroke_id, "boardX": float(50+i), "boardY": float(70+i),
        })
        mode_rows.append({"stroke_id": stroke_id, "stroke_option_raw": True})
        frame_rows.append({"stroke_id": stroke_id, "frame_count": 1})
    count = len(accepted)
    run = {
        "run_id": "run-1", "session_id": "valid-session",
        "execution_status": "completed",
        "stroke_count": 27, "stroke_candidate_count": 27,
        "non_consuming_stroke_candidate_count": 0,
        "chalk": {"status": "exact", "consumed_points": count},
        "pre_test_snapshot": {"pointCount": 1},
        "post_test_snapshot": {"pointCount": count+1},
        "point_delta_matches_chalk": True,
        "sampled_point_delta_total": count,
        "events": events, "event_count": len(events),
        "accepted_points": accepted,
        "engine_frame_samples": {"event_count": 27, "by_stroke": frame_rows},
        "observed_stroke_modes": mode_rows,
        "bridge_configuration_at_start": {
            "inputTelemetry": {"requested": True, "enabled": True}
        },
        "dropped_events": 0, "monitor_buffer_dropped_events_delta": 0,
        "monitor_error_count_delta": 0, "bridge_send_failures_delta": 0,
        "collector_sequence_gap_count": 0,
        "renderer_geometry_update_overflow_count": 0,
        "renderer_geometry_at_start": geometry,
        "renderer_geometry_at_end": copy.deepcopy(geometry),
        "renderer_geometry_updates": [],
    }
    path = tmp_path / "run.json"
    path.write_text(json.dumps(run), encoding="utf-8")
    result = audit_diagnostic_capture(
        task=_task(), readiness={
            "protocol": PROTOCOL, "session_id": "valid-session",
            "renderer_geometry_sha256": diag._geometry_fingerprint(geometry),
        }, monitor_run_path=path,
        before_full=full, before_roi=roi_image,
        after_full=after_full, after_roi=after_crop, screen_roi=roi,
    )
    assert result["status"] == "PASS_E4_RAW_CAPTURE"
    assert result["reasons"] == []
    assert result["accepted_points_count"] == 54
    assert result["engine_frame_count"] == 27
    assert result["mouse_move_count"] == 27
    assert result["exact_chalk"] == 54
    assert "native alpha" in " ".join(result["limitations"])
    run["renderer_geometry_at_end"]["players"][0]["boardClientCorners"]["topLeft"]["x"] += 1
    path.write_text(json.dumps(run), encoding="utf-8")
    altered = audit_diagnostic_capture(
        task=_task(), readiness={
            "protocol": PROTOCOL, "session_id": "valid-session",
            "renderer_geometry_sha256": diag._geometry_fingerprint(geometry),
        }, monitor_run_path=path,
        before_full=full, before_roi=roi_image,
        after_full=after_full, after_roi=after_crop, screen_roi=roi,
    )
    assert altered["status"] == "PARTIAL"
    assert "same_run_native_geometry_unstable_or_missing" in altered["reasons"]

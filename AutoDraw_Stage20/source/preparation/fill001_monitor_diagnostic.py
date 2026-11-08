from __future__ import annotations

"""Versioned, read-only FILL-001 same-run Monitor 0.2.4 diagnostic.

This module adds no game input, capture acceptance, renderer calibration or
CHALK estimator. It reuses the ENGINE-001 fresh Bridge preflight and only
evaluates exact raw evidence from the selected FILL-001 single-task run.
"""
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops

from engine001_lab import inspect_ready_bridge

PROTOCOL = "FILL001_MONITOR_SAME_RUN_V1"
AB_PROTOCOL = "FILL001_SMOOTH_AB_V1"
AB_V2_PROTOCOL = "FILL001_SMOOTH_AB_V2"
BASELINE_PLAN_SIGNATURE = "a0e422160f222276baafea73aa884e3407255d7b3da5ab47778a4d70f434e417"
BASELINE_MASK_SHA256 = "ac1c6660e5986cdf534328c6dbcd5020f631168b1473c24b29e7609eb827998b"
# Preflight budget only, not a model of exact CHALK for a future run.
MIN_REMAINING_POINTS_FOR_SAFE_PILOT = 1600


def _expected_mode(task: dict[str, Any]) -> tuple[str, bool]:
    """V1 is historically fixed to smooth=True; A/B has an explicit contract."""
    if task.get("experiment_protocol") in (AB_PROTOCOL, AB_V2_PROTOCOL):
        if type(task.get("expected_smooth")) is not bool:
            raise ValueError("Smooth A/B expected_smooth must be an explicit boolean.")
        return task["experiment_protocol"], task["expected_smooth"]
    if "experiment_protocol" in task or "expected_smooth" in task:
        raise ValueError("Unknown/undeclared FILL-001 smoothing protocol.")
    return PROTOCOL, True


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _geometry_fingerprint(geometry: Any) -> str:
    return hashlib.sha256(
        json.dumps(geometry, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _valid_board_geometry(geometry: Any) -> bool:
    if not isinstance(geometry, dict) or geometry.get("boardLogicalSize") != {
        "width": 460, "height": 240
    }:
        return False
    players = geometry.get("players")
    if not isinstance(players, list) or len(players) != 1:
        return False
    player = players[0]
    if player.get("boardClientMappingMethod") not in (
        "getBoxQuads_content", "validated_axis_aligned_rect"
    ):
        return False
    for name in ("boardStageCorners", "boardClientCorners"):
        corners = player.get(name)
        if not isinstance(corners, dict):
            return False
        for corner in ("topLeft", "topRight", "bottomRight", "bottomLeft"):
            value = corners.get(corner)
            if not isinstance(value, dict) or any(
                isinstance(value.get(axis), bool)
                or not isinstance(value.get(axis), (int, float))
                or not math.isfinite(value[axis])
                for axis in ("x", "y")
            ):
                return False
    return geometry.get("renderMode") == "webgl"


def validate_baseline_task(task: dict[str, Any]) -> None:
    """One pre-registered 27-stroke RS rectangle, never the 45-cell batch."""
    if not isinstance(task, dict) or any([
        task.get("phase_id") != "FILL001",
        task.get("plan_variant") != "FILL001_RS_V1",
        task.get("shape_id") != "rectangle",
        type(task.get("requested_radius")) is not int or task["requested_radius"] != 10,
        task.get("scanline_row_step") != 5,
        task.get("scanline_offset") != 0,
        task.get("expected_strokes") != 27,
        task.get("plan_signature") != BASELINE_PLAN_SIGNATURE,
        task.get("target_mask_sha256") != BASELINE_MASK_SHA256,
        task.get("repeat_index") != 1,
        task.get("capture_status") != "pending",
    ]):
        raise ValueError("FILL-001 diagnostic requires exactly the frozen RS rectangle/r10/step5/offset0/rep1 task.")


def inspect_diagnostic_preflight(bridge_root: Path, task: dict[str, Any]) -> dict[str, Any]:
    validate_baseline_task(task)
    protocol, expected_smooth = _expected_mode(task)
    ready = inspect_ready_bridge(Path(bridge_root))
    session_file = Path(ready["session_path"])
    session = json.loads(session_file.read_text(encoding="utf-8"))
    geometry = session.get("renderer_geometry")
    if (session.get("session_id") != ready["session_id"]
            or not _valid_board_geometry(geometry)
            or session.get("monitor_status_at_connect", {}).get("version") != "0.2.4"):
        raise ValueError("FILL-001 diagnostic needs exactly one native WebGL BoardPane with verified client corners and Monitor 0.2.4.")
    diagnostics = session.get("bridge_diagnostics") or {}
    status = diagnostics.get("last_monitor_status") or {}
    snapshot = status.get("snapshot") or {}
    if (snapshot.get("isExact") is not True
            or type(snapshot.get("remainingPoints")) is not int
            or snapshot["remainingPoints"] < MIN_REMAINING_POINTS_FOR_SAFE_PILOT):
        raise ValueError("FILL-001 diagnostic needs an exact fresh CHALK snapshot with at least 1600 points remaining.")
    return {
        "protocol": protocol, "session_id": ready["session_id"],
        **({"expected_smooth": expected_smooth} if protocol in (AB_PROTOCOL, AB_V2_PROTOCOL) else {}),
        "session_file": str(session_file), "monitor_version": "0.2.4",
        "renderer_geometry_sha256": _geometry_fingerprint(geometry),
        "bridge_heartbeat_at_utc": ready["heartbeat_at_utc"],
        "minimum_remaining_points_required": MIN_REMAINING_POINTS_FOR_SAFE_PILOT,
        "observed_remaining_points": snapshot["remainingPoints"],
        "board_client_mapping_method": geometry["players"][0]["boardClientMappingMethod"],
        "screen_projection_status": "REQUIRES_INDEPENDENT_POST_RUN_FIT",
    }


def _valid_rgb_pair(full_path: Path, roi_path: Path, roi: Any) -> dict[str, Any]:
    if not isinstance(roi, dict) or any(
        type(roi.get(k)) is not int for k in ("x", "y", "width", "height")
    ):
        raise ValueError("Diagnostic calibrated ROI is invalid.")
    if roi["x"] < 0 or roi["y"] < 0 or roi["width"] < 2 or roi["height"] < 2:
        raise ValueError("Diagnostic calibrated ROI is out of range.")
    if not full_path.is_file() or not roi_path.is_file():
        raise ValueError("Diagnostic screen/ROI PNG pair is missing.")
    with Image.open(full_path) as full_image, Image.open(roi_path) as crop_image:
        if full_image.format != "PNG" or crop_image.format != "PNG":
            raise ValueError("Diagnostic captures must be original PNG.")
        if (roi["x"] + roi["width"] > full_image.width or
                roi["y"] + roi["height"] > full_image.height):
            raise ValueError("Diagnostic ROI falls outside full screen.")
        actual_crop = full_image.crop((
            roi["x"], roi["y"], roi["x"] + roi["width"], roi["y"] + roi["height"]
        )).convert("RGB")
        crop_rgb = crop_image.convert("RGB")
        if actual_crop.size != crop_rgb.size or ImageChops.difference(
            actual_crop, crop_rgb
        ).getbbox() is not None:
            raise ValueError("Diagnostic full-screen PNG and ROI are not from the same frame.")
        return {
            "full_screen_size": [full_image.width, full_image.height],
            "roi_size": [crop_image.width, crop_image.height],
            "full_screen_sha256": _hash(full_path),
            "board_roi_sha256": _hash(roi_path),
        }


def audit_diagnostic_capture(
    *, task: dict[str, Any], readiness: dict[str, Any],
    monitor_run_path: Path, before_full: Path, before_roi: Path,
    after_full: Path, after_roi: Path, screen_roi: dict[str, int],
) -> dict[str, Any]:
    """Produce PASS/PARTIAL E4 telemetry audit regardless of FILL PNG quality.

    The original FILL acceptance validator still independently enforces
    coverage>=99% and leakage==0. A diagnostic PASS cannot override its FAIL.
    """
    validate_baseline_task({**task, "capture_status": "pending"})
    protocol, expected_smooth = _expected_mode(task)
    run_path = Path(monitor_run_path)
    run = json.loads(run_path.read_text(encoding="utf-8"))
    reasons: list[str] = []
    if (readiness.get("protocol") != protocol
            or (protocol in (AB_PROTOCOL, AB_V2_PROTOCOL) and readiness.get("expected_smooth") is not expected_smooth)
            or run.get("session_id") != readiness.get("session_id")
            or run.get("execution_status") != "completed"
            or run.get("stroke_count") != 27
            or run.get("stroke_candidate_count") != 27
            or run.get("non_consuming_stroke_candidate_count") != 0):
        reasons.append("run_session_or_27_stroke_identity_invalid")
    chalk = run.get("chalk") or {}
    pre = run.get("pre_test_snapshot") or {}
    post = run.get("post_test_snapshot") or {}
    count = chalk.get("consumed_points")
    if (chalk.get("status") != "exact"
            or type(count) is not int or count <= 0
            or type(pre.get("pointCount")) is not int
            or type(post.get("pointCount")) is not int
            or post["pointCount"] - pre["pointCount"] != count
            or run.get("point_delta_matches_chalk") is not True
            or run.get("sampled_point_delta_total") != count):
        reasons.append("exact_chalk_binding_invalid")
    events = run.get("events")
    if not isinstance(events, list):
        events = []
    if (len(events) != run.get("event_count")
            or any(not isinstance(e, dict) or e.get("monitorVersion") != "0.2.4" for e in events)):
        reasons.append("raw_events_incomplete_or_wrong_version")
    points = run.get("accepted_points")
    if not isinstance(points, list):
        points = []
    positive = [e for e in events if e.get("type") == "DRAW_SAMPLE" and
                type(e.get("pointDelta")) is int and e["pointDelta"] > 0]
    ids = [p.get("stroke_id") for p in points if isinstance(p, dict)]
    if (type(count) is not int or len(points) != count or
            len(positive) != count or len(ids) != count or len(set(ids)) != 27
            or any(type(e.get("pointDelta")) is not int or e["pointDelta"] != 1 for e in positive)
            or any(not isinstance(p, dict) or p.get("point_delta") != 1 or
                   not all(type(p.get(k)) in (int, float) and math.isfinite(p[k])
                           for k in ("x", "y", "t")) for p in points)
            or any(e.get("strokeId") != p.get("stroke_id")
                   or e.get("acceptedPoint") != {"x": p.get("x"), "y": p.get("y")}
                   for e, p in zip(positive, points))):
        reasons.append("accepted_stream_not_one_to_one")
    frames = run.get("engine_frame_samples") or {}
    observed_frame_events = [e for e in events if e.get("type") == "ENGINE_FRAME_SAMPLE"]
    by_stroke = frames.get("by_stroke")
    if (type(frames.get("event_count")) is not int or frames["event_count"] < 27
            or frames["event_count"] != len(observed_frame_events)
            or not isinstance(by_stroke, list) or len(by_stroke) != 27
            or any(type(item.get("frame_count")) is not int or item["frame_count"] <= 0
                   for item in by_stroke if isinstance(item, dict))
            or any(not isinstance(item, dict) for item in by_stroke)):
        reasons.append("engine_enter_frame_evidence_incomplete")
    modes = run.get("observed_stroke_modes") or []
    if (len(modes) != 27 or len({x.get("stroke_id") for x in modes if isinstance(x, dict)}) != 27
            or any(not isinstance(x, dict) or type(x.get("stroke_option_raw")) is not bool
                   or x["stroke_option_raw"] is not expected_smooth for x in modes)):
        reasons.append("smooth_mode_unverified_or_changed")
    if protocol in (AB_PROTOCOL, AB_V2_PROTOCOL):
        # Verify the declared condition against each original Egret frame, not
        # merely a reconstructed per-stroke summary from the Bridge collector.
        observed_ids = {
            row.get("stroke_id") for row in modes if isinstance(row, dict)
        }
        frame_ids = {
            row.get("strokeId") for row in observed_frame_events if isinstance(row, dict)
        }
        if (len(frame_ids) != 27 or frame_ids != observed_ids
                or any(not isinstance(row, dict)
                       or type(row.get("strokeOptionRaw")) is not bool
                       or row["strokeOptionRaw"] is not expected_smooth
                       for row in observed_frame_events)):
            reasons.append("raw_engine_smooth_mode_missing_or_mixed")
    input_count = sum(e.get("type") == "MOUSE_MOVE_SAMPLE" for e in events)
    if input_count <= 0:
        reasons.append("mouse_input_telemetry_missing")
    config = run.get("bridge_configuration_at_start") or {}
    telemetry = config.get("inputTelemetry") or {}
    if telemetry.get("requested") is not True or telemetry.get("enabled") is not True:
        reasons.append("bridge_input_telemetry_not_enabled")
    for name in ("dropped_events", "monitor_buffer_dropped_events_delta",
                 "monitor_error_count_delta", "bridge_send_failures_delta",
                 "collector_sequence_gap_count", "renderer_geometry_update_overflow_count"):
        if run.get(name) != 0:
            reasons.append("nonzero_" + name)
    g0 = run.get("renderer_geometry_at_start")
    g1 = run.get("renderer_geometry_at_end")
    if (not _valid_board_geometry(g0) or g0 != g1
            or run.get("renderer_geometry_updates") != []
            or _geometry_fingerprint(g0) != readiness.get("renderer_geometry_sha256")):
        reasons.append("same_run_native_geometry_unstable_or_missing")
    before = _valid_rgb_pair(Path(before_full), Path(before_roi), screen_roi)
    after = _valid_rgb_pair(Path(after_full), Path(after_roi), screen_roi)
    if before["full_screen_size"] != after["full_screen_size"]:
        reasons.append("screen_dimensions_changed")
    with Image.open(before_roi) as ib, Image.open(after_roi) as ia:
        if ImageChops.difference(ib.convert("RGB"), ia.convert("RGB")).getbbox() is None:
            reasons.append("no_visible_screen_change")
    return {
        "schema_version": 1, "protocol": protocol,
        **({"expected_smooth": expected_smooth} if protocol in (AB_PROTOCOL, AB_V2_PROTOCOL) else {}),
        "status": "PASS_E4_RAW_CAPTURE" if not reasons else "PARTIAL",
        "reasons": reasons, "run_id": run.get("run_id"),
        "session_id": run.get("session_id"), "task_id": task.get("task_id"),
        "plan_signature": task.get("plan_signature"),
        "monitor_version": "0.2.4", "exact_chalk": count if type(count) is int else None,
        "accepted_points_count": len(points),
        "positive_draw_samples": len(positive),
        "stroke_count": run.get("stroke_count"),
        "observed_stroke_modes": modes,
        "engine_frame_count": len(observed_frame_events),
        "mouse_move_count": input_count,
        "geometry_at_start_sha256": _geometry_fingerprint(g0),
        "raw_run_sha256": _hash(run_path),
        "before": before, "after": after,
        "screen_roi": screen_roi,
        "limitations": [
            "Observing ENTER_FRAME does not prove actual Stage rendering order.",
            "Same-run client geometry requires independent desktop/PNG alignment validation.",
            "Screenshots contain RGB; native alpha cannot be inferred.",
            ("No per-stroke live PNG; game smooth toggle remains operator-controlled."
             if protocol in (AB_PROTOCOL, AB_V2_PROTOCOL) else
             "No per-stroke live PNG and no direct normal-mode control in this protocol."),
            "A diagnostic PASS is not FILL coverage/leakage acceptance or CHALK prediction.",
        ],
    }

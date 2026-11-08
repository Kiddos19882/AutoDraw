from __future__ import annotations

"""ENGINE-001 isolated one-click laboratory evidence guards (no UI/mouse logic).

The existing CHALK block state machine owns all side effects. This module is
deliberately fail-closed: no fresh Egret observer => no game input; a missing
run-bound screenshot/geometry/accepted sample cannot be a PASS.
"""
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops

ENGINE001_PHASE = "ENGINE001"
ENGINE001_SCENARIOS = (
    "engine001_horizontal_endpoint",
    "engine001_vertical_axis",
    "engine001_diagonal_axis",
)
ENGINE001_EXPECTED_TASKS = 9
ENGINE001_EXPERIMENT_ID = "ENGINE001_ONE_CLICK_LAB_V1"


def _utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None


def inspect_ready_bridge(root: Path, *, now: datetime | None = None) -> dict[str, Any]:
    """Require exactly one fresh live authenticated Bridge and Egret frame observer."""
    now = now or datetime.now(timezone.utc)
    candidates = []
    for path in Path(root).glob("*/session.json"):
        try:
            session = json.loads(path.read_text("utf-8"))
        except (OSError, UnicodeError, ValueError):
            continue
        diagnostics = session.get("bridge_diagnostics")
        if not isinstance(diagnostics, dict) or diagnostics.get("connection_closed") is not False:
            continue
        # The collector updates last_message_type for every event and frame probe.
        # Freshness must be tied to an actual status-bearing heartbeat, not the
        # most recent arbitrary WebSocket message.
        if "last_heartbeat_at_utc" in diagnostics:
            heartbeat_at = diagnostics["last_heartbeat_at_utc"]
        else:
            # Preserve the old fail-closed check for pre-upgrade session files.
            if diagnostics.get("last_message_type") != "heartbeat":
                continue
            heartbeat_at = diagnostics.get("last_message_at_utc")
        stamp = _utc(heartbeat_at)
        if stamp is None or not 0 <= (now - stamp).total_seconds() <= 4.0:
            continue
        status = diagnostics.get("last_monitor_status")
        if not isinstance(status, dict):
            continue
        config = session.get("bridge_configuration")
        if not isinstance(config, dict):
            config = {}
        requested_input = config.get("inputTelemetry")
        if not isinstance(requested_input, dict):
            requested_input = {}
        geometry = session.get("renderer_geometry")
        players = geometry.get("players") if isinstance(geometry, dict) else None
        board_count = sum(
            isinstance(player, dict) and isinstance(player.get("boardStageCorners"), dict)
            for player in players
        ) if isinstance(players, list) else 0
        if (
            status.get("version") != "0.2.4"
            or status.get("active") is not True
            or status.get("boardDetected") is not True
            or status.get("inputTelemetryEnabled") is not True
            or status.get("engineFrameObserverConnected") is not True
            or requested_input.get("requested") is not True
            or requested_input.get("enabled") is not True
            or board_count != 1
            or not isinstance(session.get("session_id"), str)
            or not session["session_id"]
        ):
            continue
        candidates.append({
            "session_id": session["session_id"],
            "heartbeat_at_utc": stamp.isoformat(),
            "monitor_version": status.get("version"),
            "board_count": board_count,
            "geometry_mapping_state": "RAW_CSS_ONLY_NOT_DESKTOP_CALIBRATED",
            "session_path": str(path),
        })
    if len(candidates) != 1:
        raise ValueError(
            "ENGINE-001: нужен ровно один свежий Bridge/Monitor с включённой "
            "input telemetry, наблюдателем Egret ENTER_FRAME и одной BoardPane; "
            f"подходящих сессий: {len(candidates)}. Без этого рисование запрещено."
        )
    return candidates[0]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _diff_board(before: Path, after: Path) -> dict[str, Any]:
    with Image.open(before) as ib, Image.open(after) as ia:
        a, b = ib.convert("RGB"), ia.convert("RGB")
        if a.size != b.size:
            raise ValueError("Lab before/after board ROI dimensions differ.")
        # Compare saved screen ROIs, NOT predicted game pixel masks.
        delta = ImageChops.difference(a, b)
        rgb = delta.tobytes()
        width, height = a.size
        changed_x, changed_y = [], []
        for index in range(width * height):
            pos = 3 * index
            if max(rgb[pos], rgb[pos+1], rgb[pos+2]) >= 20:
                changed_x.append(index % width)
                changed_y.append(index // width)
        return {
            "method": "screen_board_roi_rgb_max_channel_difference_ge_20",
            "roi_width": width,
            "roi_height": height,
            "changed_pixel_count": len(changed_x),
            "changed_bounds_roi": (
                {"left": min(changed_x), "top": min(changed_y),
                 "right": max(changed_x), "bottom": max(changed_y)}
                if changed_x else None
            ),
            "not_a_native_stroke_mask": True,
        }


def audit_single_capture(experiment_dir: Path) -> dict[str, Any]:
    """Write an immutable per-attempt diagnostic; return PASS/PARTIAL, never live E5."""
    folder = Path(experiment_dir)
    manifest_path = folder / "experiment.json"
    report_path = folder / "monitor_report.json"
    manifest = json.loads(manifest_path.read_text("utf-8"))
    report = json.loads(report_path.read_text("utf-8"))
    phase = manifest.get("chalk_experiment_matrix")
    if not isinstance(phase, dict) or phase.get("phase_id") != ENGINE001_PHASE or (
        phase.get("scenario_id") not in ENGINE001_SCENARIOS
    ) or phase.get("expected_strokes") != 1:
        raise ValueError("ENGINE-001 capture has the wrong task/phase identity.")
    exp = manifest.get("experiment_id")
    if not isinstance(exp, str) or not exp or report.get("autodraw_experiment_id") != exp:
        raise ValueError("ENGINE-001 experiment identity differs from Bridge copy.")
    summary = manifest.get("game_monitor_summary")
    if not isinstance(summary, dict):
        raise ValueError("ENGINE-001 monitor summary is missing.")
    if not all(
        report.get(key) == summary.get(key) and report.get(key)
        for key in ("run_id", "session_id")
    ):
        raise ValueError("ENGINE-001 run/session identity mismatch.")
    failures = []
    chalk = report.get("chalk") or {}
    pre, post = report.get("pre_test_snapshot") or {}, report.get("post_test_snapshot") or {}
    consumed = chalk.get("consumed_points")
    if (
        chalk.get("status") != "exact"
        or type(consumed) is not int or consumed <= 0
        or type(pre.get("pointCount")) is not int
        or type(post.get("pointCount")) is not int
        or post["pointCount"] - pre["pointCount"] != consumed
        or report.get("point_delta_matches_chalk") is not True
        or report.get("stroke_count") != 1
        or report.get("execution_status") != "completed"
    ):
        failures.append("exact_chalk_or_stroke_binding_invalid")
    points = report.get("accepted_points")
    if not isinstance(points, list) or not points or (
        len(points) != consumed
        or any(type(p.get("point_delta")) is not int or p["point_delta"] != 1
               or not all(isinstance(p.get(k), (int, float)) and math.isfinite(p[k]) for k in ("x","y","t"))
               for p in points if isinstance(p, dict))
        or any(not isinstance(p, dict) for p in points)
    ):
        failures.append("accepted_points_incomplete")
        points = []
    modes = report.get("observed_stroke_modes")
    expected_stroke_id = points[0].get("stroke_id") if points else None
    valid_mode = (
        isinstance(modes, list)
        and len(modes) == 1
        and isinstance(modes[0], dict)
        and type(modes[0].get("stroke_option_raw")) is bool
        and isinstance(expected_stroke_id, str)
        and modes[0].get("stroke_id") == expected_stroke_id
    )
    if not valid_mode:
        failures.append("native_stroke_mode_not_observed")
    frames = report.get("engine_frame_samples")
    by_stroke = frames.get("by_stroke") if isinstance(frames, dict) else None
    valid_frames = (
        isinstance(frames, dict)
        and type(frames.get("event_count")) is int
        and frames["event_count"] > 0
        and isinstance(by_stroke, list)
        and len(by_stroke) == 1
        and isinstance(by_stroke[0], dict)
        and by_stroke[0].get("stroke_id") == expected_stroke_id
        and type(by_stroke[0].get("frame_count")) is int
        and by_stroke[0]["frame_count"] > 0
    )
    if not valid_frames:
        failures.append("egret_enter_frame_telemetry_incomplete")
    # Cross-check Bridge rollups against the raw, run-bound engine callbacks.
    raw_events = report.get("events")
    frame_events = [
        ev for ev in raw_events
        if isinstance(ev, dict) and ev.get("type") == "ENGINE_FRAME_SAMPLE"
    ] if isinstance(raw_events, list) else []
    if (
        not valid_frames
        or len(frame_events) != frames["event_count"]
        or any(ev.get("strokeId") != expected_stroke_id for ev in frame_events)
    ):
        failures.append("raw_engine_frame_event_binding_missing")
    if valid_mode and frame_events and any(
        type(ev.get("strokeOptionRaw")) is not bool
        or ev["strokeOptionRaw"] != modes[0]["stroke_option_raw"]
        for ev in frame_events
    ):
        failures.append("native_mode_changed_or_unknown_inside_stroke")
    if any(report.get(key) != 0 for key in (
        "dropped_events", "monitor_buffer_dropped_events_delta",
        "monitor_error_count_delta", "bridge_send_failures_delta",
        "collector_sequence_gap_count"
    )):
        failures.append("telemetry_loss_or_monitor_errors")
    g0 = report.get("renderer_geometry_at_start")
    g1 = report.get("renderer_geometry_at_end")
    if not isinstance(g0, dict) or not isinstance(g1, dict) or g0 != g1 or (
        report.get("renderer_geometry_updates") != []
        or report.get("renderer_geometry_update_overflow_count") != 0
    ):
        failures.append("same_run_geometry_unstable_or_missing")
    phases = manifest.get("phases") or {}
    before_files = (phases.get("before_draw") or {}).get("files") or {}
    after_files = (phases.get("after_draw") or {}).get("files") or {}
    required_names = [
        before_files.get("full_screen"), before_files.get("board_roi"),
        after_files.get("full_screen"), after_files.get("board_roi"),
        "monitor_report.json", "experiment.json",
    ]
    if not all(isinstance(n, str) and n and "/" not in n and "\\" not in n
               and (folder / n).is_file() for n in required_names):
        failures.append("run_bound_png_or_report_missing")
    files = {}
    for n in required_names:
        if isinstance(n, str) and n and "/" not in n and "\\" not in n and (folder/n).is_file():
            files[n] = _sha256(folder/n)
    diffs = None
    if (
        isinstance(before_files.get("board_roi"), str) and isinstance(after_files.get("board_roi"), str)
        and (folder/before_files["board_roi"]).is_file()
        and (folder/after_files["board_roi"]).is_file()
    ):
        diffs = _diff_board(folder/before_files["board_roi"],folder/after_files["board_roi"])
        if diffs["changed_pixel_count"] == 0:
            failures.append("no_visible_stroke_in_screen_roi")
    result = {
        "schema_version": 1, "experiment_id": ENGINE001_EXPERIMENT_ID,
        "status": "PASS_E4_RAW_CAPTURE" if not failures else "PARTIAL",
        "reasons": failures, "source_experiment_id": exp,
        "session_id": report.get("session_id"), "run_id": report.get("run_id"),
        "scenario_id": phase["scenario_id"], "repeat_index": phase.get("repeat_index"),
        "exact_chalk": consumed if not failures or chalk.get("status") == "exact" else None,
        "accepted_points": len(points),
        "first_accepted": points[0] if points else None,
        "penultimate_accepted": points[-2] if len(points) > 1 else None,
        "last_accepted": points[-1] if points else None,
        "observed_modes": modes,
        "engine_frame_samples": frames,
        "raf_frame_probe": report.get("frame_probe"),
        "renderer_geometry_binding": {
            "same_run_start_and_end_equal": g0 == g1 and isinstance(g0, dict),
            "raw_client_corners": (
                [item.get("boardClientCorners") for item in g0.get("players", [])]
                if isinstance(g0, dict) else None
            ),
            "screen_projection": "UNCALIBRATED_UNTIL_INDEPENDENT_SAME_RUN_GEOMETRY_AUDIT",
        },
        "board_roi_pixel_diff": diffs,
        "raw_sha256": files,
        "limitations": [
            "One game run per stroke; no shared screen transform from another session",
            "ENTER_FRAME observer does not establish exact rendering order",
            "Changed screen ROI pixels are not a native stroke mask or quality score",
            "No automatic model acceptance without separate same-run transform and PNG audit",
        ],
    }
    dest = folder / "engine001-lab-audit.json"
    if dest.exists():
        raise FileExistsError("ENGINE-001 audit already exists; never overwrite prior raw evidence.")
    temp = dest.with_name("." + dest.name + ".tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(dest)
    return result

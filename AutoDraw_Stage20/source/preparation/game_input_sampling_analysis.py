from __future__ import annotations

"""Offline analysis of Game Monitor input-to-accepted-point telemetry.

This utility is diagnostic only. It does not infer OS/PyAutoGUI events that never
reached the DOM, and it does not treat browser requestAnimationFrame probes as
Egret ENTER_FRAME measurements.
"""

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _point(value: Any) -> tuple[float, float] | None:
    if not isinstance(value, dict):
        return None
    x, y = _number(value.get("x")), _number(value.get("y"))
    return (x, y) if x is not None and y is not None else None


def _percentile(values: list[float], percentile_value: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile_value * len(ordered)) - 1))
    return round(ordered[index], 3)


def _summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "min": None, "median": None, "p95": None, "max": None}
    return {
        "count": len(values),
        "min": round(min(values), 3),
        "median": round(float(median(values)), 3),
        "p95": _percentile(values, 0.95),
        "max": round(max(values), 3),
    }


def _event_time(event: dict[str, Any]) -> float | None:
    return _number(event.get("t"))


def _monitor_version(run: dict[str, Any], session: dict[str, Any] | None) -> str | None:
    status = session.get("monitor_status_at_connect") if isinstance(session, dict) else None
    if isinstance(status, dict) and isinstance(status.get("version"), str):
        return status["version"]
    for event in run.get("events", []):
        if isinstance(event, dict) and isinstance(event.get("monitorVersion"), str):
            return event["monitorVersion"]
    return None


def _telemetry_status(run: dict[str, Any], session: dict[str, Any] | None) -> str:
    status = session.get("monitor_status_at_connect") if isinstance(session, dict) else None
    has_samples = any(
        isinstance(event, dict) and event.get("type") == "MOUSE_MOVE_SAMPLE"
        for event in run.get("events", [])
    )
    if isinstance(status, dict):
        enabled = status.get("inputTelemetryEnabled")
        if enabled is True:
            return "enabled" if has_samples else "enabled_no_samples"
        if enabled is False:
            # This is only the connection-time status. The API can be toggled
            # later while Bridge is connected, so observed events take priority.
            return "observed_after_connect_or_status_conflict" if has_samples else "disabled"
    if has_samples:
        return "observed"
    version = _monitor_version(run, session)
    if version:
        try:
            parts = tuple(int(part) for part in version.split(".")[:3])
            if parts < (0, 2, 2):
                return "unsupported_monitor_version"
        except (TypeError, ValueError):
            pass
    return "not_observed_or_not_enabled"


def _analyze_stroke(stroke_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(events, key=lambda event: (
        _event_time(event) is None,
        _event_time(event) if _event_time(event) is not None else float("inf")
    ))
    mouse = [event for event in ordered
             if event.get("type") == "MOUSE_MOVE_SAMPLE" and _event_time(event) is not None]
    quota = [event for event in ordered
             if event.get("type") == "POINT_QUOTA_UPDATE"
             and (_number(event.get("pointDelta")) or 0) > 0
             and _event_time(event) is not None]

    matches: list[dict[str, Any]] = []
    latency_values: list[float] = []
    dispatch_lag_values: list[float] = []
    board_delta_values: list[float] = []
    stage_delta_values: list[float] = []
    missing_prior_input = 0
    ambiguous_delta_updates = 0
    missing_intermediate_points = 0
    cursor = 0
    latest_index: int | None = None
    last_used_index = -1
    unmatched_input_between_accepts = 0
    reused_input_sample = 0

    for update in quota:
        update_time = _event_time(update)
        assert update_time is not None
        while cursor < len(mouse) and (_event_time(mouse[cursor]) or 0) <= update_time:
            latest_index = cursor
            cursor += 1

        delta = int(_number(update.get("pointDelta")) or 0)
        if delta > 1:
            ambiguous_delta_updates += 1
            missing_intermediate_points += delta - 1

        if latest_index is None:
            missing_prior_input += 1
            matches.append({
                "update_t": update_time,
                "point_delta": delta,
                "accepted_point": update.get("acceptedPoint"),
                "match": "no_preceding_mousemove"
            })
            continue

        input_event = mouse[latest_index]
        input_time = _event_time(input_event)
        assert input_time is not None
        if latest_index > last_used_index:
            unmatched_input_between_accepts += max(0, latest_index - last_used_index - 1)
            last_used_index = latest_index
        else:
            reused_input_sample += 1

        latency = update_time - input_time
        latency_values.append(latency)
        dom_time = _number(input_event.get("domEventTimeStamp"))
        if dom_time is not None:
            dispatch_lag_values.append(input_time - dom_time)

        input_board = ( _number(input_event.get("boardX")), _number(input_event.get("boardY")) )
        update_board = ( _number(update.get("boardX")), _number(update.get("boardY")) )
        if None not in input_board and None not in update_board:
            board_delta_values.append(math.hypot(
                update_board[0] - input_board[0], update_board[1] - input_board[1]
            ))

        input_stage = (_number(input_event.get("stageX")), _number(input_event.get("stageY")))
        update_stage = (_number(update.get("stageX")), _number(update.get("stageY")))
        if None not in input_stage and None not in update_stage:
            stage_delta_values.append(math.hypot(
                update_stage[0] - input_stage[0], update_stage[1] - input_stage[1]
            ))

        matches.append({
            "update_t": update_time,
            "input_t": input_time,
            "input_to_accept_ms": round(latency, 3),
            "dom_dispatch_lag_ms": round(input_time - dom_time, 3) if dom_time is not None else None,
            "point_delta": delta,
            "accepted_point": update.get("acceptedPoint"),
            "input_board": {"x": input_event.get("boardX"), "y": input_event.get("boardY")},
            "accepted_board": {"x": update.get("boardX"), "y": update.get("boardY")},
            "input_stage": {"x": input_event.get("stageX"), "y": input_event.get("stageY")},
            "accepted_stage": {"x": update.get("stageX"), "y": update.get("stageY")},
            "match": "latest_preceding_mousemove"
        })

    trailing_input = max(0, len(mouse) - 1 - last_used_index) if mouse else 0
    draw_samples = [event for event in ordered if event.get("type") == "DRAW_SAMPLE"]
    draw_sample_deltas = [
        float(value) for event in draw_samples
        if (value := _number(event.get("pointDelta"))) is not None and value > 0
    ]
    point_delta_total = sum(int(_number(event.get("pointDelta")) or 0) for event in quota)

    positions = [
        (_number(event.get("stageX")), _number(event.get("stageY")))
        for event in mouse
    ]
    valid_positions = [(x, y) for x, y in positions if x is not None and y is not None]
    unique_positions = len(set(valid_positions))

    return {
        "stroke_id": stroke_id,
        "mouse_move_sample_count": len(mouse),
        "unique_stage_positions": unique_positions if valid_positions else None,
        "repeated_stage_position_count": len(valid_positions) - unique_positions if valid_positions else None,
        "positive_point_quota_update_count": len(quota),
        "accepted_point_delta_total": point_delta_total,
        "point_delta_gt_one_update_count": ambiguous_delta_updates,
        "unobserved_intermediate_point_count": missing_intermediate_points,
        "updates_without_preceding_mousemove": missing_prior_input,
        "reused_latest_mousemove_count": reused_input_sample,
        "unmatched_mousemoves_between_accepts": unmatched_input_between_accepts,
        "trailing_mousemove_count": trailing_input,
        "input_to_accept_ms": _summary(latency_values),
        "dom_listener_dispatch_lag_ms": _summary(dispatch_lag_values),
        "input_to_accepted_board_distance": _summary(board_delta_values),
        "input_to_accepted_stage_distance": _summary(stage_delta_values),
        "draw_sample_count": len(draw_samples),
        "draw_sample_point_delta_gt_one_count": sum(1 for value in draw_sample_deltas if value > 1),
        "matches": matches,
    }


def analyze_run(run: dict[str, Any], session: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(run, dict):
        raise ValueError("Game Monitor run must be a JSON object.")
    events = run.get("events")
    if not isinstance(events, list):
        raise ValueError("Game Monitor run must contain an events array.")

    counts = Counter(
        event.get("type") for event in events
        if isinstance(event, dict) and isinstance(event.get("type"), str)
    )
    for event_type in (
        "MOUSE_MOVE_SAMPLE", "POINT_QUOTA_UPDATE", "DRAW_SAMPLE",
        "DRAW_START", "DRAW_END", "POINTER_DOWN_CANDIDATE", "POINTER_UP_CANDIDATE"
    ):
        counts.setdefault(event_type, 0)
    by_stroke: dict[str, list[dict[str, Any]]] = defaultdict(list)
    events_without_stroke_id = 0
    for event in events:
        if not isinstance(event, dict):
            continue
        stroke_id = event.get("strokeId")
        if isinstance(stroke_id, str) and stroke_id:
            by_stroke[stroke_id].append(event)
        elif event.get("type") in {
            "MOUSE_MOVE_SAMPLE", "POINT_QUOTA_UPDATE", "DRAW_SAMPLE",
            "DRAW_START", "DRAW_END", "POINTER_DOWN_CANDIDATE", "POINTER_UP_CANDIDATE"
        }:
            events_without_stroke_id += 1

    strokes = [
        _analyze_stroke(stroke_id, by_stroke[stroke_id])
        for stroke_id in sorted(by_stroke)
    ]
    all_latency = [
        match["input_to_accept_ms"]
        for stroke in strokes for match in stroke["matches"]
        if isinstance(match.get("input_to_accept_ms"), (int, float))
    ]
    probes = run.get("frame_probes") if isinstance(run.get("frame_probes"), list) else []
    probe_intervals = [
        float(value) for probe in probes if isinstance(probe, dict)
        for value in (probe.get("intervals") if isinstance(probe.get("intervals"), list) else [])
        if _number(value) is not None and float(value) >= 0
    ]

    quota_delta_total = sum(
        int(_number(event.get("pointDelta")) or 0)
        for event in events
        if isinstance(event, dict) and event.get("type") == "POINT_QUOTA_UPDATE"
        and (_number(event.get("pointDelta")) or 0) > 0
    )
    return {
        "schema_version": 1,
        "analysis": "game_input_sampling_trace",
        "run_id": run.get("run_id"),
        "session_id": run.get("session_id"),
        "monitor_version": _monitor_version(run, session),
        "input_telemetry_status": _telemetry_status(run, session),
        "event_counts": dict(sorted(counts.items())),
        "stroke_count_with_events": len(strokes),
        "events_without_stroke_id": events_without_stroke_id,
        "point_quota_delta_total": quota_delta_total,
        "run_sampled_point_delta_total": run.get("sampled_point_delta_total"),
        "point_delta_matches_chalk": run.get("point_delta_matches_chalk"),
        "input_to_accept_ms": _summary(all_latency),
        "per_stroke": strokes,
        "browser_raf_interval_ms": _summary(probe_intervals),
        "interpretation_limits": [
            "MOUSE_MOVE_SAMPLE includes only DOM mousemove events delivered to the canvas; OS/PyAutoGUI events coalesced before DOM dispatch are not observable.",
            "POINT_QUOTA_UPDATE records the exact latest accepted point for that quota update; when pointDelta > 1, intermediate accepted coordinates are unavailable.",
            "The nearest preceding MOUSE_MOVE_SAMPLE is a temporal correlation, not proof that it alone caused the accepted point.",
            "DRAW_SAMPLE is polling/wrapper telemetry and may aggregate changes; it is not a replacement for POINT_QUOTA_UPDATE.",
            "frame_probes measure browser requestAnimationFrame intervals, not a direct Egret ENTER_FRAME counter."
        ]
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Game Monitor input-to-accepted-point telemetry.")
    parser.add_argument("--run", required=True, type=Path, help="game-monitor-run-*.json")
    parser.add_argument("--session", type=Path, help="Optional session.json for telemetry-enabled status.")
    parser.add_argument("--output", type=Path, help="Optional derived JSON output path.")
    args = parser.parse_args()

    run = json.loads(args.run.read_text(encoding="utf-8"))
    session = json.loads(args.session.read_text(encoding="utf-8")) if args.session else None
    report = analyze_run(run, session)
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

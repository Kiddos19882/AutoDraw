"""Authenticated loopback WebSocket collector for Game Monitor brush experiments.

The browser agent only streams read-only Game Monitor events and frame timings.
This service never sends commands to the game or controls the mouse.
"""
from __future__ import annotations

import argparse
import asyncio
import hmac
import json
import math
import os
import secrets
import statistics
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import websockets
from websockets.exceptions import ConnectionClosed

HOST = "127.0.0.1"
PORT = 8765
MAX_MESSAGE_BYTES = 65536
MAX_EVENTS_PER_RUN = 100000
MAX_GEOMETRY_UPDATES_PER_RUN = 32
INPUT_TELEMETRY_PLACEHOLDER = "__AUTODRAW_INPUT_TELEMETRY_ENABLED__"


def render_bridge_snippet(
    source: str,
    token: str,
    port: int,
    *,
    enable_input_telemetry: bool = False,
) -> str:
    """Render a one-time browser snippet with explicit, opt-in input telemetry."""
    if not isinstance(source, str):
        raise TypeError("Bridge snippet source must be text.")
    if not isinstance(token, str) or not token:
        raise ValueError("A non-empty one-time Bridge token is required.")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("Bridge port must be an integer from 1 to 65535.")
    if type(enable_input_telemetry) is not bool:
        raise TypeError("enable_input_telemetry must be a boolean.")
    if source.count("__AUTODRAW_BRIDGE_TOKEN__") != 1:
        raise ValueError("Bridge token placeholder must occur exactly once.")
    if source.count(INPUT_TELEMETRY_PLACEHOLDER) != 1:
        raise ValueError("Input telemetry placeholder must occur exactly once.")
    rendered = source.replace("__AUTODRAW_BRIDGE_TOKEN__", token)
    rendered = rendered.replace("ws://127.0.0.1:8765", f"ws://127.0.0.1:{port}")
    rendered = rendered.replace(
        INPUT_TELEMETRY_PLACEHOLDER,
        "true" if enable_input_telemetry else "false",
    )
    if "__AUTODRAW_BRIDGE_TOKEN__" in rendered or INPUT_TELEMETRY_PLACEHOLDER in rendered:
        raise ValueError("Bridge snippet contains an unresolved configuration placeholder.")
    return rendered
ALLOWED_TYPES = {"BOARD_ATTACHED", "BOARD_DETACHED", "DRAW_START", "DRAW_START_APPLIED",
                 "DRAW_SAMPLE", "DRAW_END", "BRUSH_CHANGE", "BRUSH_CHANGE_APPLIED",
                 "POINT_QUOTA_UPDATE", "GAME_METHOD_ERROR", "ENGINE_FRAME_SAMPLE", "POINTER_DOWN_CANDIDATE",
                 "POINTER_UP_CANDIDATE", "MOUSE_MOVE_SAMPLE"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def valid_origin(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        return (parsed.scheme == "https" and bool(parsed.netloc)
                and parsed.username is None and parsed.password is None
                and parsed.path in ("", "/") and not parsed.query and not parsed.fragment)
    except ValueError:
        return False


def parse_json(raw: str) -> dict | None:
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_MESSAGE_BYTES:
        return None
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeError):
        return None
    return value if isinstance(value, dict) else None


def exact_snapshot(value: object) -> bool:
    return (isinstance(value, dict) and value.get("isExact") is True
            and type(value.get("maxPoints")) is int
            and type(value.get("pointCount")) is int
            and type(value.get("remainingPoints")) is int
            and value["maxPoints"] > 0
            and 0 <= value["pointCount"] <= value["maxPoints"]
            and value["pointCount"] + value["remainingPoints"] == value["maxPoints"])


def summarize_intervals(intervals: object) -> dict:
    values = [float(x) for x in intervals if isinstance(x, (int, float)) and 0 < x < 1000] if isinstance(intervals, list) else []
    if not values:
        return {"status": "unavailable", "frame_count": 0, "average_fps": None,
                "median_fps": None, "median_interval_ms": None, "p95_interval_ms": None,
                "max_interval_ms": None}
    ordered = sorted(values)
    median_interval = statistics.median(values)
    p95 = ordered[min(len(ordered) - 1, max(0, math.ceil(len(ordered) * 0.95) - 1))]
    return {
        "status": "measured",
        "frame_count": len(values) + 1,
        "average_fps": round(1000 / statistics.mean(values), 3),
        "median_fps": round(1000 / median_interval, 3),
        "median_interval_ms": round(median_interval, 3),
        "p95_interval_ms": round(p95, 3),
        "max_interval_ms": round(max(values), 3),
        "visibility_interruption": False,
    }


def summarize_per_stroke_metrics(events: object) -> list[dict]:
    """Summarize exact point-counter changes and timing for each identified stroke.

    POINT_QUOTA_UPDATE timestamps come from Monitor's wrapped updateLess calls.
    They measure accepted point updates, not every ENTER_FRAME callback.
    """
    if not isinstance(events, list):
        return []
    starts: dict[str, dict] = {}
    ends: dict[str, dict] = {}
    updates: dict[str, list[dict]] = {}
    start_types = {"DRAW_START", "POINTER_DOWN_CANDIDATE"}
    end_types = {"DRAW_END", "POINTER_UP_CANDIDATE"}
    for event in events:
        if not isinstance(event, dict):
            continue
        stroke_id = event.get("strokeId")
        if not isinstance(stroke_id, str) or not stroke_id:
            continue
        event_type = event.get("type")
        if event_type in start_types:
            previous = starts.get(stroke_id)
            if previous is None or event.get("t", float("inf")) < previous.get("t", float("inf")):
                starts[stroke_id] = event
        elif event_type in end_types:
            previous = ends.get(stroke_id)
            if previous is None or event.get("t", float("-inf")) > previous.get("t", float("-inf")):
                ends[stroke_id] = event
        elif event_type == "POINT_QUOTA_UPDATE":
            updates.setdefault(stroke_id, []).append(event)

    stroke_ids = set(starts) | set(ends) | set(updates)
    ordered_ids = sorted(stroke_ids, key=lambda key: (
        starts.get(key, {}).get("t", float("inf")), key
    ))
    results: list[dict] = []
    for stroke_id in ordered_ids:
        start = starts.get(stroke_id, {})
        end = ends.get(stroke_id, {})
        start_snapshot = start.get("board") or start.get("before")
        end_snapshot = end.get("board") or end.get("after")
        before_count = start_snapshot.get("pointCount") if isinstance(start_snapshot, dict) else None
        after_count = end_snapshot.get("pointCount") if isinstance(end_snapshot, dict) else None
        exact_counts = (
            type(before_count) is int and type(after_count) is int
            and after_count >= before_count
        )
        point_delta = after_count - before_count if exact_counts else None
        stroke_updates = sorted(
            updates.get(stroke_id, []),
            key=lambda item: item.get("t", float("inf"))
        )
        update_deltas: list[int] = []
        update_times: list[float] = []
        all_update_snapshots_exact = True
        for item in stroke_updates:
            before = item.get("before")
            after = item.get("after")
            if (isinstance(before, dict) and isinstance(after, dict)
                    and type(before.get("pointCount")) is int
                    and type(after.get("pointCount")) is int
                    and after["pointCount"] >= before["pointCount"]):
                update_deltas.append(after["pointCount"] - before["pointCount"])
            else:
                all_update_snapshots_exact = False
            timestamp = item.get("t")
            if isinstance(timestamp, (int, float)) and not isinstance(timestamp, bool):
                update_times.append(float(timestamp))
        intervals = sorted(
            right - left for left, right in zip(update_times, update_times[1:])
            if right >= left
        )
        def percentile(values: list[float], fraction: float) -> float | None:
            if not values:
                return None
            index = min(len(values) - 1, max(0, math.ceil(len(values) * fraction) - 1))
            return round(values[index], 3)
        start_t, end_t = start.get("t"), end.get("t")
        duration = (
            round(float(end_t) - float(start_t), 3)
            if isinstance(start_t, (int, float)) and isinstance(end_t, (int, float))
            and end_t >= start_t else None
        )
        update_delta_sum = sum(update_deltas)
        results.append({
            "stroke_id": stroke_id,
            "lifecycle_status": "complete" if start and end else "incomplete",
            "started_at_performance_ms": start_t,
            "ended_at_performance_ms": end_t,
            "duration_ms": duration,
            "point_count_before": before_count if type(before_count) is int else None,
            "point_count_after": after_count if type(after_count) is int else None,
            "point_count_delta": point_delta,
            "point_update_event_count": len(stroke_updates),
            "point_update_delta_sum": update_delta_sum,
            "point_count_delta_matches_updates": (
                update_delta_sum == point_delta
                if exact_counts and all_update_snapshots_exact and stroke_updates else None
            ),
            "accepted_points_per_second": (
                round(point_delta * 1000.0 / duration, 3)
                if point_delta is not None and duration and duration > 0 else None
            ),
            "median_point_update_interval_ms": percentile(intervals, 0.5),
            "p95_point_update_interval_ms": percentile(intervals, 0.95),
            "max_point_update_interval_ms": round(max(intervals), 3) if intervals else None,
        })
    return results


class RunRecorder:
    def __init__(self, output_dir: Path, session_id: str, idle_seconds: float):
        self.output_dir = output_dir
        self.session_id = session_id
        self.idle_seconds = idle_seconds
        self.current: dict | None = None
        self.last_activity = 0.0
        self.last_status: dict | None = None
        self.last_bridge_diagnostics: dict | None = None
        self.run_count = 0
        self.active_stroke_ids: set[str] = set()
        self.stroke_started_at: dict[str, float] = {}
        self.observed_stroke_ids: set[str] = set()
        self.accepted_stroke_ids: set[str] = set()
        self.lifecycle_sources: set[str] = set()
        self.renderer_geometry: dict | None = None
        self.renderer_geometry_updated_at_utc: str | None = None
        self.bridge_configuration: dict | None = None

    def set_bridge_configuration(self, configuration: dict) -> None:
        if not isinstance(configuration, dict):
            raise ValueError("bridge configuration must be an object")
        try:
            encoded = json.dumps(configuration, ensure_ascii=False, separators=(",", ":"))
        except (TypeError, ValueError):
            raise ValueError("bridge configuration must be JSON serializable") from None
        if len(encoded.encode("utf-8")) > 4096:
            raise ValueError("bridge configuration is too large")
        self.bridge_configuration = json.loads(encoded)

    def set_renderer_geometry(self, geometry: dict, reason: str | None = None) -> None:
        if not isinstance(geometry, dict):
            raise ValueError("renderer geometry must be an object")
        try:
            encoded = json.dumps(geometry, ensure_ascii=False, separators=(",", ":"))
        except (TypeError, ValueError):
            raise ValueError("renderer geometry must be JSON serializable") from None
        if len(encoded.encode("utf-8")) > MAX_MESSAGE_BYTES // 2:
            raise ValueError("renderer geometry snapshot is too large")
        snapshot = json.loads(encoded)
        self.renderer_geometry = snapshot
        self.renderer_geometry_updated_at_utc = utc_now()
        if self.current is not None:
            updates = self.current.setdefault("renderer_geometry_updates", [])
            if len(updates) < MAX_GEOMETRY_UPDATES_PER_RUN:
                updates.append({
                    "updated_at_utc": self.renderer_geometry_updated_at_utc,
                    "reason": reason if isinstance(reason, str) and len(reason) <= 128 else None,
                    "snapshot": snapshot,
                })
            else:
                self.current["renderer_geometry_update_overflow_count"] = (
                    self.current.get("renderer_geometry_update_overflow_count", 0) + 1
                )

    def _start(self, event: dict) -> None:
        self.run_count += 1
        before = event.get("before") if isinstance(event.get("before"), dict) else event.get("board")
        self.current = {
            "schema_version": 1,
            "record_type": "autodraw_game_monitor_run",
            "session_id": self.session_id,
            "run_id": str(uuid.uuid4()),
            "started_at_utc": utc_now(),
            "started_at_performance_ms": event.get("t"),
            "execution_status": "in_progress",
            "pre_test_snapshot": before,
            "post_test_snapshot": None,
            "renderer_geometry_at_start": self.renderer_geometry,
            "renderer_geometry_updated_at_start_utc": self.renderer_geometry_updated_at_utc,
            "bridge_configuration_at_start": self.bridge_configuration,
            "renderer_geometry_updates": [],
            "renderer_geometry_update_overflow_count": 0,
            "brush_radius": (before or {}).get("currentRadius") if isinstance(before, dict) else None,
            "events": [],
            "frame_probes": [],
            "active_drawing_duration_ms": 0.0,
            "dropped_events": 0,
            "monitor_buffer_dropped_events_start": (
                self.last_status.get("droppedEvents")
                if isinstance(self.last_status, dict)
                and type(self.last_status.get("droppedEvents")) is int else None
            ),
            "monitor_buffer_dropped_events_end": (
                self.last_status.get("droppedEvents")
                if isinstance(self.last_status, dict)
                and type(self.last_status.get("droppedEvents")) is int else None
            ),
            "monitor_buffer_dropped_events_delta": 0,
            "monitor_error_count_start": (
                self.last_status.get("errors")
                if isinstance(self.last_status, dict)
                and type(self.last_status.get("errors")) is int else None
            ),
            "monitor_error_count_end": (
                self.last_status.get("errors")
                if isinstance(self.last_status, dict)
                and type(self.last_status.get("errors")) is int else None
            ),
            "monitor_error_count_delta": 0,
            # Browser Bridge initializes sendFailureCount at zero for each session.
            "bridge_send_failures_start": (
                self.last_bridge_diagnostics.get("sendFailureCount")
                if isinstance(self.last_bridge_diagnostics, dict)
                and type(self.last_bridge_diagnostics.get("sendFailureCount")) is int else 0
            ),
            "bridge_send_failures_end": (
                self.last_bridge_diagnostics.get("sendFailureCount")
                if isinstance(self.last_bridge_diagnostics, dict)
                and type(self.last_bridge_diagnostics.get("sendFailureCount")) is int else None
            ),
            "bridge_send_failures_delta": 0,
            "collector_sequence_gap_count": 0,
            "monitor_errors": [],
            "interpretation": {"chalk_status": "inconclusive",
                               "path_length_status": "incomplete_until_verified"}
        }

    def _append_event(self, event: dict) -> None:
        if self.current is None:
            return
        if len(self.current["events"]) >= MAX_EVENTS_PER_RUN:
            self.current["dropped_events"] += 1
            return
        self.current["events"].append(event)
        for key in ("after", "board"):
            snapshot = event.get(key)
            if exact_snapshot(snapshot):
                self.current["post_test_snapshot"] = snapshot
        if event.get("type") == "DRAW_SAMPLE":
            point = event.get("acceptedPoint")
            delta = event.get("pointDelta")
            if type(delta) is int and delta > 0:
                stroke_id = event.get("strokeId")
                if stroke_id is None and len(self.active_stroke_ids) == 1:
                    stroke_id = next(iter(self.active_stroke_ids))
                if stroke_id is not None:
                    self.accepted_stroke_ids.add(str(stroke_id))
            if isinstance(point, dict) and isinstance(point.get("x"), (int, float)) and isinstance(point.get("y"), (int, float)):
                self.current.setdefault("accepted_points", []).append({
                    "t": event.get("t"), "stroke_id": event.get("strokeId"),
                    "x": point["x"], "y": point["y"], "point_delta": delta
                })
            if not isinstance(delta, int) or delta > 1:
                self.current["interpretation"]["path_length_status"] = "incomplete_samples"
        if event.get("type") == "GAME_METHOD_ERROR":
            self.current["monitor_errors"].append(event)

    def _event_stroke_id(self, event: dict) -> str:
        value = event.get("strokeId")
        if value is not None:
            return str(value)
        # Older exports and synthetic tests may omit strokeId. If exactly one
        # stroke is active, its matching end boundary is unambiguous.
        if len(self.active_stroke_ids) == 1:
            return next(iter(self.active_stroke_ids))
        return f"unidentified-{event.get('t')}"

    def _begin_stroke(self, event: dict, now: float, source: str) -> None:
        if self.current is not None and now - self.last_activity >= self.idle_seconds:
            previous_status = "completed" if self.current.get("execution_status") == "completed" else "partial"
            self.finalize(previous_status)
        if self.current is None:
            self._start(event)
        stroke_id = self._event_stroke_id(event)
        self.lifecycle_sources.add(source)
        self.observed_stroke_ids.add(stroke_id)
        if stroke_id not in self.active_stroke_ids:
            self.active_stroke_ids.add(stroke_id)
            if isinstance(event.get("t"), (int, float)):
                self.stroke_started_at[stroke_id] = event["t"]
        self.current["execution_status"] = "in_progress"
        self.last_activity = now

    def _end_stroke(self, event: dict, now: float, source: str) -> None:
        if self.current is None:
            return
        stroke_id = self._event_stroke_id(event)
        # A single active stroke is also an unambiguous match when one side
        # of an older event stream omitted or changed its strokeId.
        if stroke_id not in self.active_stroke_ids and len(self.active_stroke_ids) == 1:
            stroke_id = next(iter(self.active_stroke_ids))
        self.lifecycle_sources.add(source)
        if stroke_id in self.active_stroke_ids:
            self.active_stroke_ids.remove(stroke_id)
            started = self.stroke_started_at.pop(stroke_id, None)
            ended = event.get("t")
            if isinstance(started, (int, float)) and isinstance(ended, (int, float)):
                self.current["active_drawing_duration_ms"] += max(0.0, ended - started)
        if not self.active_stroke_ids:
            self.current["execution_status"] = "completed"
            self.current["ended_at_performance_ms"] = event.get("t")
        self.last_activity = now
        if isinstance(event.get("after"), dict):
            self.current["post_test_snapshot"] = event["after"]

    def event(self, event: dict, now: float) -> None:
        event_type = event.get("type")
        if event_type not in ALLOWED_TYPES:
            raise ValueError("unsupported event type")

        if event_type == "DRAW_START":
            self._begin_stroke(event, now, "engine")
        elif event_type == "POINTER_DOWN_CANDIDATE":
            self._begin_stroke(event, now, "pointer_observer")

        if self.current is not None:
            self._append_event(event)

        if event_type in {"DRAW_START", "DRAW_START_APPLIED", "DRAW_SAMPLE", "DRAW_END",
                          "POINTER_DOWN_CANDIDATE", "POINTER_UP_CANDIDATE"}:
            self.last_activity = now

        if event_type == "DRAW_END":
            self._end_stroke(event, now, "engine")
        elif event_type == "POINTER_UP_CANDIDATE":
            self._end_stroke(event, now, "pointer_observer")

    def frame_probe(self, message: dict) -> None:
        if self.current is None:
            return
        stroke_id = message.get("strokeId")
        self.current["frame_probes"].append({
            "stroke_id": stroke_id if isinstance(stroke_id, str) and stroke_id else None,
            "started_at_performance_ms": message.get("startedAtPerformanceMs"),
            "ended_at_performance_ms": message.get("endedAtPerformanceMs"),
            "visible": message.get("visible") is True,
            "intervals": message.get("intervals", []),
        })

    def note_collector_sequence_gap(self, missing_count: int) -> None:
        if self.current is not None and type(missing_count) is int and missing_count > 0:
            self.current["collector_sequence_gap_count"] += missing_count

    def heartbeat(
        self,
        status: dict,
        now: float,
        bridge_diagnostics: dict | None = None,
    ) -> None:
        self.last_status = status
        if isinstance(bridge_diagnostics, dict):
            self.last_bridge_diagnostics = bridge_diagnostics
        if self.current is not None:
            dropped = status.get("droppedEvents")
            if type(dropped) is int:
                self.current["monitor_buffer_dropped_events_end"] = dropped
                start = self.current.get("monitor_buffer_dropped_events_start")
                self.current["monitor_buffer_dropped_events_delta"] = (
                    max(0, dropped - start) if type(start) is int else None
                )
            self.current["monitor_dropped_events"] = dropped  # Deprecated session-cumulative alias.
            errors = status.get("errors")
            if type(errors) is int:
                self.current["monitor_error_count_end"] = errors
                start_errors = self.current.get("monitor_error_count_start")
                self.current["monitor_error_count_delta"] = (
                    max(0, errors - start_errors) if type(start_errors) is int else None
                )
            self.current["monitor_error_count"] = errors  # Deprecated cumulative alias.
            self.current["monitor_active"] = status.get("active")
            failures = bridge_diagnostics.get("sendFailureCount") if isinstance(bridge_diagnostics, dict) else None
            if type(failures) is int:
                self.current["bridge_send_failures_end"] = failures
                start_failures = self.current.get("bridge_send_failures_start")
                self.current["bridge_send_failures_delta"] = (
                    max(0, failures - start_failures) if type(start_failures) is int else None
                )
        if self.current is not None and now - self.last_activity >= self.idle_seconds:
            status = "completed" if self.current["execution_status"] == "completed" else "partial"
            self.finalize(status)

    def finalize(self, status: str = "partial") -> Path | None:
        if self.current is None:
            return None
        run = self.current
        self.current = None
        if run["execution_status"] != "completed":
            run["execution_status"] = status
        post = run.get("post_test_snapshot")
        pre = run.get("pre_test_snapshot")
        if exact_snapshot(pre) and exact_snapshot(post) and pre["maxPoints"] == post["maxPoints"]:
            delta = post["pointCount"] - pre["pointCount"]
            if delta >= 0:
                run["chalk"] = {"status": "exact", "consumed_points": delta,
                                "pre_point_count": pre["pointCount"],
                                "post_point_count": post["pointCount"],
                                "max_points": pre["maxPoints"]}
            else:
                run["chalk"] = {"status": "inconclusive", "reason": "negative_point_delta"}
        else:
            run["chalk"] = {"status": "inconclusive", "reason": "missing_or_inconsistent_exact_snapshots"}
        accepted = run.get("accepted_points", [])
        observed_stroke_ids = self.observed_stroke_ids | self.accepted_stroke_ids
        run["stroke_count"] = len(self.accepted_stroke_ids)
        run["stroke_candidate_count"] = len(observed_stroke_ids)
        run["non_consuming_stroke_candidate_count"] = len(observed_stroke_ids - self.accepted_stroke_ids)
        run["stroke_lifecycle_sources"] = sorted(self.lifecycle_sources)
        run.pop("stroke_started_at_performance_ms", None)
        self.active_stroke_ids.clear()
        self.stroke_started_at.clear()
        self.observed_stroke_ids.clear()
        self.accepted_stroke_ids.clear()
        self.lifecycle_sources.clear()
        sample_events = [event for event in run["events"] if event.get("type") == "DRAW_SAMPLE"]
        point_deltas = [event.get("pointDelta") for event in sample_events]
        point_delta_complete = bool(sample_events) and all(type(delta) is int and delta >= 0 for delta in point_deltas)
        run["sampled_point_delta_total"] = sum(delta for delta in point_deltas if type(delta) is int and delta >= 0)
        run["point_delta_matches_chalk"] = (
            run["sampled_point_delta_total"] == run["chalk"]["consumed_points"]
            if run["chalk"]["status"] == "exact" and point_delta_complete else None
        )
        observed_radii = set()
        for event in run["events"]:
            for snapshot_key in ("board", "before", "after"):
                snapshot = event.get(snapshot_key)
                radius = snapshot.get("currentRadius") if isinstance(snapshot, dict) else None
                if isinstance(radius, (int, float)) and not isinstance(radius, bool):
                    observed_radii.add(float(radius))
        run["observed_brush_radii"] = sorted(observed_radii)
        run["brush_radius_status"] = (
            "unavailable" if not observed_radii else "single" if len(observed_radii) == 1 else "mixed"
        )
        by_stroke: dict[str, list[dict]] = {}
        for point in accepted:
            by_stroke.setdefault(str(point.get("stroke_id")), []).append(point)
        observed_length = 0.0
        for points in by_stroke.values():
            for left, right in zip(points, points[1:]):
                dx, dy = right["x"] - left["x"], right["y"] - left["y"]
                observed_length += (dx * dx + dy * dy) ** 0.5
        run["trajectory"] = {
            "observed_segment_length_lower_bound": round(observed_length, 4),
            "accepted_sample_count": len(accepted),
            "status": run["interpretation"]["path_length_status"],
            "note": "Coalesced pointDelta values mean intermediate accepted coordinates may be missing."
        }
        run["per_stroke_metrics"] = summarize_per_stroke_metrics(run["events"])
        # True Egret BoardPane ENTER_FRAME observer callbacks, not browser RAF.
        frame_events = [event for event in run["events"]
                        if event.get("type") == "ENGINE_FRAME_SAMPLE"]
        grouped_frames: dict[str, list[dict]] = {}
        for event in frame_events:
            sid = event.get("strokeId")
            if isinstance(sid, str) and sid:
                grouped_frames.setdefault(sid, []).append(event)
        run["engine_frame_samples"] = {
            "source": "BoardPane.EgretEvent.ENTER_FRAME_observer",
            "event_count": len(frame_events),
            "by_stroke": [
                {
                    "stroke_id": sid,
                    "frame_count": len(events),
                    "observed_positive_point_delta_frames": sum(
                        type(event.get("observedPointDeltaSincePreviousFrame")) is int
                        and event["observedPointDeltaSincePreviousFrame"] > 0
                        for event in events),
                    "observed_stationary_frames": sum(
                        event.get("observedPointDeltaSincePreviousFrame") == 0
                        for event in events),
                    "first_t_ms": events[0].get("t"),
                    "last_t_ms": events[-1].get("t"),
                }
                for sid, events in sorted(grouped_frames.items())
            ],
            "is_full_engine_render_timeline": False,
            "caveat": "Observer may miss callbacks and does not establish game render ordering.",
        }
        # Bound Egret event handlers can bypass the instance onDrawStart
        # wrapper. Prefer its directly observed option when present, otherwise
        # use the first native ENTER_FRAME observer raw option for that stroke.
        # Never infer a mode from executor intent or an older capture.
        observed_modes: dict[str, dict] = {}
        for event in run["events"]:
            if event.get("type") != "ENGINE_FRAME_SAMPLE":
                continue
            sid = event.get("strokeId")
            option = event.get("strokeOptionRaw")
            if isinstance(sid, str) and sid and type(option) is bool:
                observed_modes.setdefault(sid, {
                    "stroke_id": sid,
                    "stroke_option_raw": option,
                    "source": "BoardPane.atom.options[from_ENGINE_FRAME_SAMPLE]",
                })
        for event in run["events"]:
            if event.get("type") != "DRAW_START_APPLIED":
                continue
            sid = event.get("strokeId")
            option = event.get("strokeOptionRaw")
            if isinstance(sid, str) and sid and type(option) is bool:
                observed_modes[sid] = {
                    "stroke_id": sid,
                    "stroke_option_raw": option,
                    "source": "BoardPane.atom.options[from_DRAW_START_APPLIED]",
                }
        run["observed_stroke_modes"] = [
            observed_modes[sid] for sid in sorted(observed_modes)
        ]
        probe_summaries = []
        for probe in run["frame_probes"]:
            summary = summarize_intervals(probe.get("intervals", []))
            summary.update({
                "stroke_id": probe.get("stroke_id"),
                "started_at_performance_ms": probe.get("started_at_performance_ms"),
                "ended_at_performance_ms": probe.get("ended_at_performance_ms"),
                "visible": probe.get("visible") is True,
            })
            probe_summaries.append(summary)
        run["frame_probe_by_stroke"] = probe_summaries
        all_intervals = [interval for probe in run["frame_probes"]
                         for interval in probe.get("intervals", [])]
        fps = summarize_intervals(all_intervals)
        fps["stroke_probe_count"] = len(run["frame_probes"])
        fps["visibility_interruption"] = (any(probe.get("visible") is not True for probe in run["frame_probes"])
                                          if run["frame_probes"] else None)
        run["frame_probe"] = fps
        # Keep raw per-probe intervals in frame_probes for reproducible timing analysis.
        run["interpretation"]["chalk_status"] = run["chalk"]["status"]
        if isinstance(run.get("started_at_performance_ms"), (int, float)) and isinstance(run.get("ended_at_performance_ms"), (int, float)):
            run["elapsed_from_first_to_last_stroke_ms"] = max(0.0, run["ended_at_performance_ms"] - run["started_at_performance_ms"])
        run["renderer_geometry_at_end"] = self.renderer_geometry
        run["renderer_geometry_updated_at_end_utc"] = self.renderer_geometry_updated_at_utc
        run["finished_at_utc"] = utc_now()
        run["event_count"] = len(run["events"])
        run["dropped_events"] += 0
        self.output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        path = self.output_dir / f"game-monitor-run-{stamp}-{run['run_id'][:8]}.json"
        temp = path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(path)
        return path



async def persist_json_atomically(
    path: Path,
    payload: dict,
    *,
    attempts: int = 6,
    retry_delay: float = 0.05,
) -> bool:
    """Write JSON atomically, retrying transient Windows sharing violations."""
    temp_path = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        retry_count = max(1, attempts)
        for attempt in range(retry_count):
            try:
                os.replace(temp_path, path)
                return True
            except PermissionError:
                if attempt + 1 >= retry_count:
                    return False
                await asyncio.sleep(max(0.0, retry_delay) * (2 ** attempt))
            except OSError:
                return False
        return False
    except OSError:
        return False
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass



def make_handler(token: str, origin: str, output_dir: Path, idle_seconds: float):
    active_connections = {"count": 0}

    async def handler(websocket):
        if active_connections["count"]:
            await websocket.close(code=4008, reason="bridge already has an active browser")
            return
        raw = await asyncio.wait_for(websocket.recv(), timeout=10)
        message = parse_json(raw)
        if not message or set(message) != {"type", "token"} or message.get("type") != "auth":
            await websocket.close(code=4001, reason="invalid auth message")
            return
        candidate = message.get("token")
        if not isinstance(candidate, str) or not hmac.compare_digest(token, candidate):
            await websocket.close(code=4003, reason="authentication failed")
            return
        if active_connections["count"]:
            await websocket.close(code=4008, reason="bridge already has an active browser")
            return
        active_connections["count"] += 1
        recorder: RunRecorder | None = None
        last_sequence = 0
        session_path: Path | None = None
        session_record: dict | None = None

        async def persist_session() -> None:
            if session_path is None or session_record is None:
                return
            saved = await persist_json_atomically(session_path, session_record)
            if not saved:
                diagnostics = session_record["bridge_diagnostics"]
                diagnostics["session_persist_failures"] = diagnostics.get("session_persist_failures", 0) + 1
                diagnostics["last_session_persist_error"] = "atomic_replace_failed"
                print(
                    f"WARNING: unable to persist Game Monitor session {recorder.session_id if recorder else 'unknown'}; "
                    "will retry on the next message",
                    file=sys.stderr,
                )

        try:
            await websocket.send(json.dumps({"type": "ready"}, separators=(",", ":")))
            async for raw in websocket:
                message = parse_json(raw)
                if not message:
                    await websocket.close(code=4002, reason="invalid JSON message")
                    return
                msg_type = message.get("type")
                if msg_type == "session_start":
                    if recorder is not None:
                        await websocket.close(code=4002, reason="duplicate session_start")
                        return
                    if message.get("sequence") != 1:
                        await websocket.close(code=4002, reason="invalid initial sequence")
                        return
                    session_id = message.get("sessionId")
                    try:
                        session_id = str(uuid.UUID(session_id))
                    except (ValueError, TypeError, AttributeError):
                        await websocket.close(code=4002, reason="invalid session id")
                        return
                    initial_geometry = message.get("rendererGeometry")
                    if initial_geometry is not None and not isinstance(initial_geometry, dict):
                        await websocket.close(code=4002, reason="invalid renderer geometry")
                        return
                    recorder = RunRecorder(output_dir / session_id, session_id, idle_seconds)
                    if isinstance(initial_geometry, dict):
                        try:
                            recorder.set_renderer_geometry(initial_geometry, "session_start")
                        except ValueError:
                            await websocket.close(code=4002, reason="invalid renderer geometry")
                            return
                    initial_bridge_configuration = message.get("bridgeConfiguration")
                    if initial_bridge_configuration is not None:
                        if not isinstance(initial_bridge_configuration, dict):
                            await websocket.close(code=4002, reason="invalid bridge configuration")
                            return
                        try:
                            recorder.set_bridge_configuration(initial_bridge_configuration)
                        except ValueError:
                            await websocket.close(code=4002, reason="invalid bridge configuration")
                            return
                    initial_status = message.get("monitorStatus")
                    if isinstance(initial_status, dict):
                        recorder.last_status = initial_status
                    initial_bridge_diagnostics = message.get("bridgeDiagnostics")
                    if isinstance(initial_bridge_diagnostics, dict):
                        recorder.last_bridge_diagnostics = initial_bridge_diagnostics
                    session_dir = output_dir / session_id
                    session_dir.mkdir(parents=True, exist_ok=True)
                    session_path = session_dir / "session.json"
                    session_record = {
                        "schema_version": 2,
                        "session_id": session_id,
                        "started_at_utc": utc_now(),
                        "run_idle_seconds": idle_seconds,
                        "browser": message.get("browser"),
                        "page": message.get("page"),
                        "monitor_status_at_connect": message.get("monitorStatus"),
                        "bridge_configuration": recorder.bridge_configuration,
                        "renderer_geometry": recorder.renderer_geometry,
                        "renderer_geometry_updated_at_utc": recorder.renderer_geometry_updated_at_utc,
                        "bridge_diagnostics": {
                            "received_message_count": 1,
                            "received_event_count": 0,
                            "received_event_types": {},
                            "last_message_type": "session_start",
                            "last_sequence": 1,
                            "collector_sequence_gap_count": 0,
                            "last_message_at_utc": utc_now(),
                            "last_monitor_status": message.get("monitorStatus"),
                            "browser_bridge": None,
                            "frame_probe_count": 0,
                            "connection_closed": False,
                        },
                    }
                    last_sequence = 1
                    await persist_session()
                    continue
                if recorder is None or message.get("sessionId") != recorder.session_id:
                    await websocket.close(code=4002, reason="unknown session")
                    return
                sequence = message.get("sequence")
                if type(sequence) is not int or sequence <= last_sequence:
                    await websocket.close(code=4002, reason="invalid sequence")
                    return
                sequence_gap = sequence - last_sequence - 1
                if sequence_gap > 0:
                    recorder.note_collector_sequence_gap(sequence_gap)
                    if session_record is not None:
                        diagnostics = session_record["bridge_diagnostics"]
                        diagnostics["collector_sequence_gap_count"] = (
                            diagnostics.get("collector_sequence_gap_count", 0) + sequence_gap
                        )
                last_sequence = sequence
                if session_record is not None:
                    diagnostics = session_record["bridge_diagnostics"]
                    diagnostics["received_message_count"] += 1
                    diagnostics["last_message_type"] = msg_type
                    diagnostics["last_sequence"] = sequence
                    diagnostics["last_message_at_utc"] = utc_now()
                if msg_type == "event":
                    event = message.get("event")
                    if not isinstance(event, dict):
                        await websocket.close(code=4002, reason="invalid event")
                        return
                    if session_record is not None:
                        diagnostics = session_record["bridge_diagnostics"]
                        diagnostics["received_event_count"] += 1
                        event_type = str(event.get("type", "unknown"))
                        event_types = diagnostics["received_event_types"]
                        event_types[event_type] = event_types.get(event_type, 0) + 1
                        diagnostics["last_event_type"] = event_type
                        diagnostics["last_event_performance_ms"] = event.get("t")
                    try:
                        recorder.event(event, asyncio.get_running_loop().time())
                    except ValueError:
                        await websocket.close(code=4002, reason="unsupported game event")
                        return
                elif msg_type == "renderer_geometry":
                    geometry = message.get("rendererGeometry")
                    if not isinstance(geometry, dict):
                        await websocket.close(code=4002, reason="invalid renderer geometry")
                        return
                    reason = message.get("reason")
                    try:
                        recorder.set_renderer_geometry(geometry, reason if isinstance(reason, str) else None)
                    except ValueError:
                        await websocket.close(code=4002, reason="invalid renderer geometry")
                        return
                    if session_record is not None:
                        session_record["renderer_geometry"] = recorder.renderer_geometry
                        session_record["renderer_geometry_updated_at_utc"] = recorder.renderer_geometry_updated_at_utc
                        session_record["renderer_geometry_update_reason"] = (
                            reason if isinstance(reason, str) and len(reason) <= 128 else None
                        )
                elif msg_type == "heartbeat":
                    status = message.get("monitorStatus")
                    if isinstance(status, dict):
                        bridge_diagnostics = message.get("bridgeDiagnostics")
                        recorder.heartbeat(
                            status,
                            asyncio.get_running_loop().time(),
                            bridge_diagnostics if isinstance(bridge_diagnostics, dict) else None,
                        )
                        if session_record is not None:
                            session_record["bridge_diagnostics"]["last_monitor_status"] = status
                    if session_record is not None:
                        session_record["bridge_diagnostics"]["browser_bridge"] = message.get("bridgeDiagnostics")
                elif msg_type == "frame_probe":
                    recorder.frame_probe(message)
                    if session_record is not None:
                        diagnostics = session_record["bridge_diagnostics"]
                        diagnostics["frame_probe_count"] += 1
                else:
                    await websocket.close(code=4002, reason="unsupported message type")
                    return
                await persist_session()
        except (asyncio.TimeoutError, ConnectionClosed):
            pass
        finally:
            if recorder is not None:
                recorder.finalize("partial")
            if session_record is not None:
                session_record["bridge_diagnostics"]["connection_closed"] = True
                session_record["bridge_diagnostics"]["closed_at_utc"] = utc_now()
                await persist_session()
            active_connections["count"] = max(0, active_connections["count"] - 1)

    return handler


async def run_server(
    origin: str, port: int, output_dir: Path, idle_seconds: float, token: str,
    snippet_file: Path | None = None, enable_input_telemetry: bool = False,
) -> None:
    print("AutoDraw Game Monitor Bridge — read-only telemetry collector")
    print(f"Listening only on ws://{HOST}:{port}")
    print(f"Allowed game Origin: {origin}")
    print(f"Output directory: {output_dir.resolve()}")
    print("Session token (keep local; do not share):")
    print(token)
    bridge_path = Path(__file__).with_name("game_monitor_bridge.js")
    snippet = render_bridge_snippet(
        bridge_path.read_text(encoding="utf-8"),
        token,
        port,
        enable_input_telemetry=enable_input_telemetry,
    )
    print(
        "Input telemetry: automatically enabled for this Bridge session."
        if enable_input_telemetry else
        "Input telemetry: unchanged (default Bridge mode)."
    )
    if snippet_file is not None:
        snippet_file = snippet_file.expanduser().resolve()
        snippet_file.parent.mkdir(parents=True, exist_ok=True)
        snippet_file.write_text(snippet, encoding="utf-8")
        print(f"Ready-to-copy browser snippet written to: {snippet_file}")
    print("\nPaste this complete snippet into the Console of the game iframe after Game Monitor is loaded:\n")
    print(snippet)
    print("\nWaiting for browser telemetry. Press Ctrl+C to stop.")
    try:
        async with websockets.serve(make_handler(token, origin, output_dir, idle_seconds),
                                    HOST, port, origins=[origin], max_size=MAX_MESSAGE_BYTES,
                                    max_queue=128, ping_interval=20, ping_timeout=10,
                                    close_timeout=3):
            await asyncio.Future()
    finally:
        if snippet_file is not None:
            try:
                snippet_file.unlink(missing_ok=True)
            except OSError as exc:
                print(f"Warning: could not remove temporary browser snippet: {exc}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True, help="Exact HTTPS origin from the game iframe")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--output-dir", type=Path,
                        default=Path("AutoDraw_Stage20/data/results/brush_behavior_tests/game_monitor_bridge"))
    parser.add_argument("--idle-seconds", type=float, default=2.5)
    parser.add_argument("--snippet-file", type=Path, default=None,
                        help="Write the tokenized browser snippet here until the server stops")
    parser.add_argument(
        "--enable-input-telemetry", action="store_true",
        help="Opt in to MOUSE_MOVE_SAMPLE telemetry for a paired-renderer capture; restored when the browser Bridge disconnects.",
    )
    args = parser.parse_args()
    if not valid_origin(args.origin):
        parser.error("--origin must be an exact HTTPS origin without path/query/fragment")
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if not 0.5 <= args.idle_seconds <= 15:
        parser.error("--idle-seconds must be between 0.5 and 15")
    try:
        asyncio.run(run_server(
            args.origin.rstrip("/"), args.port, args.output_dir,
            args.idle_seconds, secrets.token_urlsafe(32), args.snippet_file,
            args.enable_input_telemetry,
        ))
    except KeyboardInterrupt:
        print("\nBridge stopped.")
    except OSError as exc:
        print(f"Could not start bridge: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

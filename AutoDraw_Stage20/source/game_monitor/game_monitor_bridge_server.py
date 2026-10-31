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
ALLOWED_TYPES = {"BOARD_ATTACHED", "BOARD_DETACHED", "DRAW_START", "DRAW_START_APPLIED",
                 "DRAW_SAMPLE", "DRAW_END", "BRUSH_CHANGE", "BRUSH_CHANGE_APPLIED",
                 "POINT_QUOTA_UPDATE", "GAME_METHOD_ERROR", "POINTER_DOWN_CANDIDATE",
                 "POINTER_UP_CANDIDATE"}


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


class RunRecorder:
    def __init__(self, output_dir: Path, session_id: str, idle_seconds: float):
        self.output_dir = output_dir
        self.session_id = session_id
        self.idle_seconds = idle_seconds
        self.current: dict | None = None
        self.last_activity = 0.0
        self.last_status: dict | None = None
        self.run_count = 0

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
            "brush_radius": (before or {}).get("currentRadius") if isinstance(before, dict) else None,
            "events": [],
            "frame_probes": [],
            "active_drawing_duration_ms": 0.0,
            "stroke_started_at_performance_ms": event.get("t"),
            "dropped_events": 0,
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
            if isinstance(point, dict) and isinstance(point.get("x"), (int, float)) and isinstance(point.get("y"), (int, float)):
                self.current.setdefault("accepted_points", []).append({
                    "t": event.get("t"), "stroke_id": event.get("strokeId"),
                    "x": point["x"], "y": point["y"], "point_delta": delta
                })
            if not isinstance(delta, int) or delta > 1:
                self.current["interpretation"]["path_length_status"] = "incomplete_samples"
        if event.get("type") == "GAME_METHOD_ERROR":
            self.current["monitor_errors"].append(event)

    def event(self, event: dict, now: float) -> None:
        event_type = event.get("type")
        if event_type not in ALLOWED_TYPES:
            raise ValueError("unsupported event type")
        if event_type == "DRAW_START":
            if self.current is not None and now - self.last_activity >= self.idle_seconds:
                previous_status = "completed" if self.current.get("execution_status") == "completed" else "partial"
                self.finalize(previous_status)
            if self.current is None:
                self._start(event)
            else:
                self.current["stroke_started_at_performance_ms"] = event.get("t")
        if self.current is not None:
            self._append_event(event)
        if event_type in {"DRAW_START", "DRAW_START_APPLIED", "DRAW_SAMPLE", "DRAW_END"}:
            self.last_activity = now
        if event_type == "DRAW_END" and self.current is not None:
            self.current["execution_status"] = "completed"
            self.current["ended_at_performance_ms"] = event.get("t")
            stroke_start = self.current.get("stroke_started_at_performance_ms")
            if isinstance(stroke_start, (int, float)) and isinstance(event.get("t"), (int, float)):
                self.current["active_drawing_duration_ms"] += max(0.0, event["t"] - stroke_start)
            self.current["stroke_started_at_performance_ms"] = None
            if isinstance(event.get("after"), dict):
                self.current["post_test_snapshot"] = event["after"]

    def frame_probe(self, message: dict) -> None:
        if self.current is None:
            return
        self.current["frame_probes"].append({
            "started_at_performance_ms": message.get("startedAtPerformanceMs"),
            "ended_at_performance_ms": message.get("endedAtPerformanceMs"),
            "visible": message.get("visible") is True,
            "intervals": message.get("intervals", []),
        })

    def heartbeat(self, status: dict, now: float) -> None:
        self.last_status = status
        if self.current is not None:
            self.current["monitor_dropped_events"] = status.get("droppedEvents")
            self.current["monitor_error_count"] = status.get("errors")
            self.current["monitor_active"] = status.get("active")
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
        run["stroke_count"] = sum(1 for event in run["events"] if event.get("type") == "DRAW_START")
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
        all_intervals = [interval for probe in run["frame_probes"]
                         for interval in probe.get("intervals", [])]
        fps = summarize_intervals(all_intervals)
        fps["stroke_probe_count"] = len(run["frame_probes"])
        fps["visibility_interruption"] = (any(probe.get("visible") is not True for probe in run["frame_probes"])
                                          if run["frame_probes"] else None)
        run["frame_probe"] = fps
        run["frame_probes"].clear()
        run["interpretation"]["chalk_status"] = run["chalk"]["status"]
        if run.get("monitor_dropped_events", 0):
            run["interpretation"]["path_length_status"] = "monitor_events_dropped"
        if isinstance(run.get("started_at_performance_ms"), (int, float)) and isinstance(run.get("ended_at_performance_ms"), (int, float)):
            run["elapsed_from_first_to_last_stroke_ms"] = max(0.0, run["ended_at_performance_ms"] - run["started_at_performance_ms"])
        run.pop("stroke_started_at_performance_ms", None)
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
        await websocket.send(json.dumps({"type": "ready"}, separators=(",", ":")))
        recorder: RunRecorder | None = None
        last_sequence = 0
        try:
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
                    recorder = RunRecorder(output_dir / session_id, session_id, idle_seconds)
                    (output_dir / session_id).mkdir(parents=True, exist_ok=True)
                    (output_dir / session_id / "session.json").write_text(
                        json.dumps({"session_id": session_id, "started_at_utc": utc_now(),
                                    "browser": message.get("browser"), "page": message.get("page"),
                                    "monitor_status": message.get("monitorStatus")}, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
                    continue
                if recorder is None or message.get("sessionId") != recorder.session_id:
                    await websocket.close(code=4002, reason="unknown session")
                    return
                sequence = message.get("sequence")
                if not isinstance(sequence, int) or sequence <= last_sequence:
                    await websocket.close(code=4002, reason="invalid sequence")
                    return
                last_sequence = sequence
                if msg_type == "event":
                    event = message.get("event")
                    if not isinstance(event, dict):
                        await websocket.close(code=4002, reason="invalid event")
                        return
                    try:
                        recorder.event(event, asyncio.get_running_loop().time())
                    except ValueError:
                        await websocket.close(code=4002, reason="unsupported game event")
                        return
                elif msg_type == "heartbeat":
                    status = message.get("monitorStatus")
                    if isinstance(status, dict):
                        recorder.heartbeat(status, asyncio.get_running_loop().time())
                elif msg_type == "frame_probe":
                    recorder.frame_probe(message)
                else:
                    await websocket.close(code=4002, reason="unsupported message type")
                    return
        except (asyncio.TimeoutError, ConnectionClosed):
            pass
        finally:
            if recorder is not None:
                recorder.finalize("partial")
            active_connections["count"] = max(0, active_connections["count"] - 1)

    return handler


async def run_server(origin: str, port: int, output_dir: Path, idle_seconds: float, token: str) -> None:
    print("AutoDraw Game Monitor Bridge — read-only telemetry collector")
    print(f"Listening only on ws://{HOST}:{port}")
    print(f"Allowed game Origin: {origin}")
    print(f"Output directory: {output_dir.resolve()}")
    print("Session token (keep local; do not share):")
    print(token)
    bridge_path = Path(__file__).with_name("game_monitor_bridge.js")
    snippet = bridge_path.read_text(encoding="utf-8").replace("__AUTODRAW_BRIDGE_TOKEN__", token)
    snippet = snippet.replace("ws://127.0.0.1:8765", f"ws://127.0.0.1:{port}")
    print("\nPaste this complete snippet into the Console of the game iframe after Game Monitor is loaded:\n")
    print(snippet)
    print("\nWaiting for browser telemetry. Press Ctrl+C to stop.")
    async with websockets.serve(make_handler(token, origin, output_dir, idle_seconds),
                                HOST, port, origins=[origin], max_size=MAX_MESSAGE_BYTES,
                                max_queue=128, ping_interval=20, ping_timeout=10,
                                close_timeout=3):
        await asyncio.Future()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True, help="Exact HTTPS origin from the game iframe")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--output-dir", type=Path,
                        default=Path("AutoDraw_Stage20/data/results/brush_behavior_tests/game_monitor_bridge"))
    parser.add_argument("--idle-seconds", type=float, default=2.5)
    args = parser.parse_args()
    if not valid_origin(args.origin):
        parser.error("--origin must be an exact HTTPS origin without path/query/fragment")
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if not 0.5 <= args.idle_seconds <= 15:
        parser.error("--idle-seconds must be between 0.5 and 15")
    try:
        asyncio.run(run_server(args.origin.rstrip("/"), args.port, args.output_dir,
                               args.idle_seconds, secrets.token_urlsafe(32)))
    except KeyboardInterrupt:
        print("\nBridge stopped.")
    except OSError as exc:
        print(f"Could not start bridge: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""FILL-001 V5 live safety gate: same-session telemetry, blank board, geometry.

This module does not click Clear, paint, or authorize the executor by itself.
The caller must recheck it *immediately* before the first game mouse-down.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any

from fill001_monitor_diagnostic import _boardpane_mapping_fingerprint
from fill001_v5_handoff import Fill001V5Error

SCHEMA = "FILL001_V5_LIVE_GATE_V1"
GAME_ORIGIN = "https://eufbpet.hust.me"
MAX_HEARTBEAT_AGE_SECONDS = 4.0


def _time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise Fill001V5Error("Missing Bridge heartbeat timestamp.")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise Fill001V5Error("Invalid Bridge heartbeat timestamp.") from exc
    if result.tzinfo is None:
        raise Fill001V5Error("Bridge heartbeat timestamp lacks UTC offset.")
    return result.astimezone(timezone.utc)


def verify_v5_live_gate(
    bridge_root: Path,
    *,
    session_id: str,
    expected_mapping_sha256: str,
    require_blank: bool = True,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Read one exact session. Never silently switch to a newer Bridge session."""
    if not isinstance(session_id, str) or not session_id:
        raise Fill001V5Error("V5 requires a specific Bridge session ID.")
    if not isinstance(expected_mapping_sha256, str) or len(expected_mapping_sha256) != 64:
        raise Fill001V5Error("V5 requires the passive BoardPane fingerprint.")
    path = Path(bridge_root) / session_id / "session.json"
    # Bridge atomically replaces session.json on every heartbeat. On Windows,
    # an overlapping open/replace can briefly raise PermissionError. Retry
    # only the open, never reuse a prior snapshot or relax heartbeat validation.
    record = None
    for attempt in range(4):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            break
        except PermissionError as exc:
            # Fail closed for permanent access denial too, after a bounded
            # wait. Do not retry malformed JSON or missing session files.
            if attempt < 3:
                time.sleep((0.025, 0.05, 0.1)[attempt])
                continue
            winerror = getattr(exc, "winerror", None)
            detail = (f", winerror={winerror}" if type(winerror) is int else "")
            raise Fill001V5Error(
                "V5 Bridge session evidence is missing. "
                f"read_error=PermissionError{detail}"
            ) from exc
        except (OSError, ValueError) as exc:
            raise Fill001V5Error(
                "V5 Bridge session evidence is missing. "
                f"read_error={type(exc).__name__}"
            ) from exc
    diagnostics = record.get("bridge_diagnostics") if isinstance(record, dict) else None
    status = diagnostics.get("last_monitor_status") if isinstance(diagnostics, dict) else None
    snapshot = status.get("snapshot") if isinstance(status, dict) else None
    telemetry = record.get("bridge_configuration", {}).get("inputTelemetry") if isinstance(record, dict) else None
    geometry = record.get("renderer_geometry") if isinstance(record, dict) else None
    if (
        record.get("session_id") != session_id
        or record.get("page", {}).get("origin") != GAME_ORIGIN
        or not isinstance(diagnostics, dict)
        or diagnostics.get("connection_closed") is not False
        or diagnostics.get("collector_sequence_gap_count") != 0
        or not isinstance(status, dict)
        or status.get("version") != "0.2.4"
        or status.get("active") is not True
        or status.get("boardDetected") is not True
        or status.get("inputTelemetryEnabled") is not True
        or not isinstance(telemetry, dict)
        or telemetry.get("requested") is not True
        or telemetry.get("enabled") is not True
    ):
        raise Fill001V5Error("V5 requires an active, unambiguous telemetry-enabled Bridge session.")
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise Fill001V5Error("V5 gate requires timezone-aware UTC.")
    age = (now.astimezone(timezone.utc) - _time(diagnostics.get("last_heartbeat_at_utc"))).total_seconds()
    if not 0 <= age <= MAX_HEARTBEAT_AGE_SECONDS:
        raise Fill001V5Error("V5 Bridge heartbeat is stale or from the future.")
    if not isinstance(geometry, dict) or geometry.get("boardLogicalSize") != {"width": 460, "height": 240}:
        raise Fill001V5Error("V5 BoardPane geometry is invalid.")
    players = geometry.get("players")
    if not isinstance(players, list) or len(players) != 1 or players[0].get("boardClientMappingMethod") != "validated_axis_aligned_rect":
        raise Fill001V5Error("V5 requires exactly one validated BoardPane.")
    fingerprint = _boardpane_mapping_fingerprint(geometry)
    if fingerprint != expected_mapping_sha256:
        raise Fill001V5Error("V5 BoardPane has moved or changed since passive calibration.")
    if not isinstance(snapshot, dict):
        raise Fill001V5Error("V5 exact resource snapshot is unavailable.")
    points, maximum, remaining = (
        snapshot.get("pointCount"), snapshot.get("maxPoints"), snapshot.get("remainingPoints")
    )
    if (snapshot.get("isExact") is not True or type(points) is not int
            or type(maximum) is not int or type(remaining) is not int
            or maximum <= 0 or not 0 <= points <= maximum or points + remaining != maximum):
        raise Fill001V5Error("V5 exact resource counters are invalid.")
    radius = snapshot.get("currentRadius")
    if type(radius) is not int or not 1 <= radius <= 30:
        raise Fill001V5Error("V5 brush radius observation is invalid.")
    if require_blank and points != 1:
        raise Fill001V5Error(
            f"V5 board is not clean: exact pointCount={points}, expected 1. "
            "No drawing permitted."
        )
    return {
        "schema": SCHEMA,
        "session_id": session_id,
        "mapping_sha256": fingerprint,
        "heartbeat_at_utc": diagnostics["last_heartbeat_at_utc"],
        "pointCount": points,
        "maxPoints": maximum,
        "remainingPoints": remaining,
        "currentRadius": radius,
        "exact": True,
        "blank_counter_confirmed": points == 1,
        "stage6_execution_allowed": False,
    }

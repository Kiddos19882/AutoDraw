"""FILL001-SERIES-001 read-only blank-screen verification after game Clear.

This module NEVER clicks, invokes BoardPane.clear(), or manipulates game state.
It verifies a settled post-Clear screenshot against an original run-bound blank
screen and a sequence of exact same-session resource snapshots. A PASS means
only "screen and counter returned to baseline", not live UI Clear validated.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

SCHEMA = "FILL001_SERIES_BLANK_SCREEN_VERIFICATION_V1"


class BlankVerificationError(ValueError):
    pass


def _time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise BlankVerificationError("Timestamp must be an ISO-8601 string")
    try:
        t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BlankVerificationError("Invalid timestamp") from exc
    if t.tzinfo is None or t.utcoffset() is None:
        raise BlankVerificationError("Timestamp must have UTC offset")
    return t


def _snapshot(snapshot: Any, *, session_id: str, mapping_sha256: str) -> dict:
    if (not isinstance(snapshot, dict)
            or snapshot.get("session_id") != session_id
            or snapshot.get("mapping_sha256") != mapping_sha256
            or snapshot.get("isExact") is not True
            or type(snapshot.get("pointCount")) is not int
            or type(snapshot.get("maxPoints")) is not int
            or type(snapshot.get("remainingPoints")) is not int
            or snapshot["maxPoints"] <= 0
            or snapshot["pointCount"] < 0
            or snapshot["remainingPoints"] < 0
            or snapshot["pointCount"] + snapshot["remainingPoints"] != snapshot["maxPoints"]):
        raise BlankVerificationError("Missing exact same-session resource evidence")
    _time(snapshot.get("captured_at_utc"))
    return snapshot


def _read_png(path: Path) -> tuple[np.ndarray, str]:
    if not Path(path).is_file():
        raise BlankVerificationError(f"Missing screenshot: {path}")
    data = Path(path).read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    try:
        with Image.open(path) as im:
            if im.format != "PNG":
                raise BlankVerificationError("Screenshot is not PNG")
            pixels = np.asarray(im.convert("RGB"), dtype=np.uint8)
    except (OSError, ValueError) as exc:
        raise BlankVerificationError("Invalid PNG") from exc
    if pixels.ndim != 3 or pixels.shape[2] != 3:
        raise BlankVerificationError("Screenshot is not RGB")
    return pixels, sha


def verify_blank_screen_after_clear(
    *, session_id: str, mapping_sha256: str,
    reference_blank_png: Path, after_clear_png: Path,
    pre_clear_snapshot: dict, settled_snapshots: list[dict],
    cursor_parked_off_roi: bool, mouse_released: bool,
    allow_rgb_pixel_differences: int = 0,
) -> dict:
    """Fail closed on stale mapping, quota uncertainty or visible residual paint.

    Pixel tolerance is fixed at zero for the first version. A new method/version
    is required before any nonzero tolerance may be considered.
    """
    if (not isinstance(session_id, str) or not session_id
            or not isinstance(mapping_sha256, str)
            or len(mapping_sha256) != 64
            or not isinstance(cursor_parked_off_roi, bool)
            or cursor_parked_off_roi is not True
            or mouse_released is not True
            or type(allow_rgb_pixel_differences) is not int
            or allow_rgb_pixel_differences != 0):
        raise BlankVerificationError("Blank verification requires fixed mapping and released parked cursor")
    try:
        int(mapping_sha256, 16)
    except ValueError as exc:
        raise BlankVerificationError("Invalid mapping hash") from exc
    if not isinstance(settled_snapshots, list) or len(settled_snapshots) < 2:
        raise BlankVerificationError("At least two exact settled observations required")
    before = _snapshot(pre_clear_snapshot, session_id=session_id, mapping_sha256=mapping_sha256)
    settled = [_snapshot(x, session_id=session_id, mapping_sha256=mapping_sha256)
               for x in settled_snapshots]
    if before["pointCount"] <= 1:
        raise BlankVerificationError("No painted pre-Clear board proven")
    if any(x["pointCount"] != 1 or x["maxPoints"] != before["maxPoints"] for x in settled):
        raise BlankVerificationError("Counter did not return to exact clean baseline")
    times = [_time(x["captured_at_utc"]) for x in [before, *settled]]
    if not all(b > a for a, b in zip(times, times[1:])):
        raise BlankVerificationError("Snapshots are stale or out of sequence")
    reference, ref_sha = _read_png(reference_blank_png)
    after, after_sha = _read_png(after_clear_png)
    if reference.shape != after.shape:
        raise BlankVerificationError("Blank image and post-Clear image dimensions differ")
    mismatch = int(np.count_nonzero(np.any(reference != after, axis=2)))
    if mismatch:
        raise BlankVerificationError(
            f"Post-Clear PNG differs from frozen blank reference at {mismatch} pixels"
        )
    return {
        "schema": SCHEMA, "status": "PASS",
        "scope": "same-session exact counter and zero-difference RGB screen only",
        "session_id": session_id, "mapping_sha256": mapping_sha256,
        "reference_png_sha256": ref_sha, "post_clear_png_sha256": after_sha,
        "reference_dimensions": [int(reference.shape[1]), int(reference.shape[0])],
        "changed_screen_pixels": mismatch,
        "pre_clear_pointCount": before["pointCount"],
        "post_clear_pointCount": settled[-1]["pointCount"],
        "settled_observations": len(settled),
        "clear_ui_action_proven": False,
        "live_clear_operation_executed_by_verifier": False,
    }

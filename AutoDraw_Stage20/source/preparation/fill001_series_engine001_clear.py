"""FILL001-SERIES-001 reuse of the proven ENGINE-001 game Clear mechanism.

One calibrated *normal game UI* click, then the existing brush-lab
evaluate_board_clear reference comparator (unchanged tolerance), alongside
fresh exact Monitor snapshots. Never uses Monitor.clear() or game internals.
The native callbacks are supplied by the current Firefox/Bridge owner.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from PIL import Image
from brush_experiment_capture import evaluate_board_clear
from calibrated_game_clear import click_calibrated_board_clear, CalibratedClearBlocked

SCHEMA = "FILL001_SERIES_ENGINE001_CLEAR_REUSE_V1"


class SeriesClearBlocked(ValueError):
    pass


def _time(v: Any) -> datetime:
    if not isinstance(v, str):
        raise SeriesClearBlocked("Missing exact Bridge snapshot UTC time")
    try:
        stamp = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SeriesClearBlocked("Invalid Bridge snapshot UTC time") from exc
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise SeriesClearBlocked("Bridge snapshot time must be aware")
    return stamp


def _exact(snapshot: Any, sid: str, mapping: str) -> dict:
    if (not isinstance(snapshot, dict)
            or snapshot.get("session_id") != sid
            or snapshot.get("mapping_sha256") != mapping
            or snapshot.get("isExact") is not True
            or type(snapshot.get("pointCount")) is not int
            or type(snapshot.get("maxPoints")) is not int
            or type(snapshot.get("remainingPoints")) is not int
            or snapshot["pointCount"] < 0
            or snapshot["maxPoints"] <= 0
            or snapshot["pointCount"] + snapshot["remainingPoints"] != snapshot["maxPoints"]):
        raise SeriesClearBlocked("Game Bridge exact session counters invalid")
    _time(snapshot.get("captured_at_utc"))
    return snapshot


def _hash(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clear_with_existing_engine001(
    *, profile: dict, reference_png: Path, reference_metadata: dict,
    session_id: str, mapping_sha256: str,
    pre_clear_snapshot: dict,
    live_snapshot: Callable[[], dict], grab_board_roi: Callable[[], Image.Image],
    click: Callable[[int, int], None], foreground_verified: Callable[[], bool],
    stop_requested: Callable[[], bool], wait_settle: Callable[[], None],
    after_clear_png: Path, mouse_released: bool,
) -> dict:
    """Perform one normal UI Clear; capture proof before allowing next run.

    Native game inputs are permitted ONLY after explicit higher-level consent
    and the same already-confirmed brush-lab calibrated desktop profile.
    No retry, no direct element or Monitor API call, no threshold changes.
    """
    if (not isinstance(session_id, str) or not session_id
            or not isinstance(mapping_sha256, str) or len(mapping_sha256) != 64
            or mouse_released is not True):
        raise SeriesClearBlocked("Missing session mapping or released mouse")
    if not isinstance(reference_metadata, dict):
        raise SeriesClearBlocked("Blank-board reference metadata missing")
    region = profile.get("regions", {}).get("board_area")
    screen = profile.get("screen_size")
    if (not isinstance(region, dict) or not isinstance(screen, dict)
            or any(type(region.get(k)) is not int for k in ("x", "y", "width", "height"))
            or any(region[k] < 0 for k in ("x","y"))
            or region["width"] <= 0 or region["height"] <= 0
            or reference_metadata.get("reference_type") != "user_confirmed_blank_board_roi"
            or reference_metadata.get("user_confirmed_blank") is not True
            or reference_metadata.get("board_region") != region
            or reference_metadata.get("screen_size") != screen
            or Path(reference_png).name != reference_metadata.get("image_file")):
        raise SeriesClearBlocked("Original ENGINE-001 blank board reference/profile mismatch")
    if profile.get("needs_review") is True:
        raise SeriesClearBlocked("Unreviewed calibration profile")
    reference_png = Path(reference_png)
    with Image.open(reference_png) as file:
        if file.format != "PNG" or file.size != (region["width"], region["height"]):
            raise SeriesClearBlocked("Invalid blank-board ROI reference PNG")
        original_blank = file.copy()
    before = _exact(pre_clear_snapshot, session_id, mapping_sha256)
    if before["pointCount"] <= 1:
        raise SeriesClearBlocked("Clear was requested without completed painted board")
    if (not callable(live_snapshot) or not callable(grab_board_roi)
            or not callable(wait_settle)):
        raise SeriesClearBlocked("Required game capture or settle callbacks unavailable")
    if stop_requested() is True:
        raise SeriesClearBlocked("Stop requested before Clear")
    click_report = click_calibrated_board_clear(
        profile, screen_size=(screen["width"], screen["height"]),
        click=click, foreground_verified=foreground_verified,
        stop_requested=stop_requested,
    )
    wait_settle()
    first = _exact(live_snapshot(), session_id, mapping_sha256)
    if first["pointCount"] != 1 or first["maxPoints"] != before["maxPoints"]:
        raise SeriesClearBlocked("ENGINE-001 Clear did not reset exact game counter")
    if stop_requested() is True or foreground_verified() is not True:
        raise SeriesClearBlocked("Lost consent/foreground while settling Clear")
    second = _exact(live_snapshot(), session_id, mapping_sha256)
    if second["pointCount"] != 1 or second["maxPoints"] != before["maxPoints"]:
        raise SeriesClearBlocked("Game pointCount unstable after Clear")
    if not (_time(before["captured_at_utc"]) < _time(first["captured_at_utc"])
            < _time(second["captured_at_utc"])):
        raise SeriesClearBlocked("Stale Clear observations")
    image = grab_board_roi()
    if not isinstance(image, Image.Image) or image.size != original_blank.size:
        raise SeriesClearBlocked("After Clear ROI changed since calibration")
    # Use the SAME comparator and frozen default tolerance as ENGINE-001.
    visual = evaluate_board_clear(original_blank, image)
    after_clear_png = Path(after_clear_png)
    after_clear_png.parent.mkdir(parents=True, exist_ok=True)
    with after_clear_png.open("xb") as stream:
        image.save(stream, format="PNG")
    if visual["status"] not in ("restored", "restored_within_pixel_tolerance"):
        # Preserve fail-closed behavior but retain the original ENGINE-001
        # comparator metrics in the immutable per-task Clear error record.
        comparison = visual["comparison"]
        raise SeriesClearBlocked(
            "Existing ENGINE-001 blank-board comparator rejected Clear: "
            f"status={visual['status']}, "
            f"changed_percent={visual['changed_percent']}, "
            f"tolerance_percent={visual['tolerance_percent']}, "
            f"changed_pixels={comparison['changed_pixels']}, "
            f"total_pixels={comparison['total_pixels']}, "
            f"reference_sha256={_hash(reference_png)}, "
            f"after_clear_sha256={_hash(after_clear_png)}"
        )
    return {
        "valid": True, "fresh_board": True, "pointCount": 1,
        "mouse_released": True, "clear_click": click_report,
        "blank_screen_verification": {
            "schema": SCHEMA, "status": "PASS",
            "session_id": session_id, "mapping_sha256": mapping_sha256,
            "post_clear_pointCount": 1,
            "reference_png_sha256": _hash(reference_png),
            "post_clear_png_sha256": _hash(after_clear_png),
            "engine001_visual_status": visual["status"],
            "engine001_tolerance_percent": visual["tolerance_percent"],
            "engine001_changed_percent": visual["changed_percent"],
            "last_settled_at_utc": second["captured_at_utc"],
            "comparison": visual["comparison"],
            "clear_ui_action_proven": True,
            "screen_evidence_status": "ENGINE001_EXISTING_COMPARATOR_PASS",
        },
    }


def capture_verified_series_boardpane_blank(
    *, roi: dict, screen_size: dict, session_id: str,
    mapping_sha256: str, point_count: int, operator_confirmed: bool,
    grab_screen: Callable[[], Image.Image], reference_png: Path,
    metadata_path: Path,
) -> dict:
    """Capture immutable series-specific blank reference from a verified desktop ROI.

    The caller owns the live native BoardPane witness and exact same-session
    empty game gate. This function never estimates browser-to-desktop offsets
    or silently falls back to a hand-calibrated board rectangle.
    """
    keys = ("x", "y", "width", "height")
    if (not isinstance(roi, dict) or any(type(roi.get(k)) is not int for k in keys)
            or roi["x"] < 0 or roi["y"] < 0
            or roi["width"] <= 0 or roi["height"] <= 0
            or not isinstance(screen_size, dict)
            or any(type(screen_size.get(k)) is not int for k in ("width", "height"))
            or screen_size["width"] <= 0 or screen_size["height"] <= 0
            or roi["x"] + roi["width"] > screen_size["width"]
            or roi["y"] + roi["height"] > screen_size["height"]
            or not isinstance(session_id, str) or not session_id
            or not isinstance(mapping_sha256, str) or len(mapping_sha256) != 64
            or any(c not in "0123456789abcdef" for c in mapping_sha256)
            or type(point_count) is not int or point_count != 1
            or operator_confirmed is not True
            or not callable(grab_screen)):
        raise SeriesClearBlocked("Verified BoardPane blank-reference evidence is incomplete")
    screen = grab_screen()
    if not isinstance(screen, Image.Image) or screen.size != (
            screen_size["width"], screen_size["height"]):
        raise SeriesClearBlocked("BoardPane reference screen size changed")
    region = {key: roi[key] for key in keys}
    crop = screen.crop((
        region["x"], region["y"],
        region["x"] + region["width"], region["y"] + region["height"],
    ))
    reference_png = Path(reference_png)
    metadata_path = Path(metadata_path)
    if reference_png.exists() or metadata_path.exists():
        raise SeriesClearBlocked("Series blank reference already exists; overwrite forbidden")
    reference_png.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with reference_png.open("xb") as stream:
        crop.save(stream, format="PNG")
    record = {
        "schema_version": 1,
        "reference_type": "user_confirmed_blank_board_roi",
        "user_confirmed_blank": True,
        "source": "verified_boardpane_native_probe",
        "session_id": session_id,
        "boardpane_mapping_sha256": mapping_sha256,
        "blank_pointCount": point_count,
        "screen_size": dict(screen_size),
        "board_region": region,
        "image_file": reference_png.name,
        "image_sha256": _hash(reference_png),
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "limitations": "User-confirmed blank and exact counter; screenshot evidence is not independent E5.",
    }
    with metadata_path.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return record


def require_same_series_boardpane_roi(
    roi: dict, metadata: dict, *, session_id: str, mapping_sha256: str,
) -> dict:
    """Refuse any change in native ROI/session before reuse of a blank reference."""
    if (not isinstance(metadata, dict)
            or metadata.get("source") != "verified_boardpane_native_probe"
            or metadata.get("user_confirmed_blank") is not True
            or metadata.get("session_id") != session_id
            or metadata.get("boardpane_mapping_sha256") != mapping_sha256
            or not isinstance(roi, dict)
            or metadata.get("board_region") != roi):
        raise SeriesClearBlocked("BoardPane desktop ROI/session differs from series blank reference")
    return roi

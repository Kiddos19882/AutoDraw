from __future__ import annotations

"""Fail-closed adapter from Game Monitor exports to FILL-001 captures."""

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from chalk_fill_experiment import build_fill_target_mask, fill_target_mask_sha256
from chalk_fill_matrix import FillMatrixError

FILL001_MONITOR_VERSION = "0.2.1"
FILL001_SAMPLING_PROFILE = {
    "profile_id": "P1",
    "sampling_step": 4,
    "delay_ms": 5,
}
PNG_CHANGE_THRESHOLD = 8


def _snapshot_point_count(snapshot: Any, label: str) -> int:
    if not isinstance(snapshot, dict) or snapshot.get("isExact") is not True:
        raise FillMatrixError(f"{label}: Monitor snapshot не является exact.")
    value = snapshot.get("pointCount")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise FillMatrixError(f"{label}: некорректный pointCount.")
    return value


def _png_pixels(path: str | Path) -> tuple[np.ndarray, str]:
    target = Path(path)
    if not target.is_file():
        raise FillMatrixError(f"PNG evidence file отсутствует: {target}")
    raw = target.read_bytes()
    if not raw:
        raise FillMatrixError(f"PNG evidence file пуст: {target}")
    digest = hashlib.sha256(raw).hexdigest()
    try:
        with Image.open(target) as image:
            if image.format != "PNG":
                raise FillMatrixError(f"Evidence не является PNG: {target}")
            pixels = np.asarray(image.convert("RGB"), dtype=np.int16)
    except (OSError, ValueError) as exc:
        raise FillMatrixError(f"Не удалось прочитать PNG {target}: {exc}") from exc
    return pixels, digest


def audit_fill001_png_pair(
    shape_id: str,
    before_png: str | Path,
    after_png: str | Path,
) -> dict[str, Any]:
    """Audit a tightly cropped 460x240 logical-board PNG pair."""
    before, before_hash = _png_pixels(before_png)
    after, after_hash = _png_pixels(after_png)
    if before.shape != after.shape or before.shape != (240, 460, 3):
        raise FillMatrixError("PNG pair должен быть одинакового размера 460x240 logical board.")
    changed = np.any(np.abs(after - before) > PNG_CHANGE_THRESHOLD, axis=2)
    mask = build_fill_target_mask(shape_id)
    target_area = int(np.count_nonzero(mask))
    covered = int(np.count_nonzero(changed & mask))
    leakage = int(np.count_nonzero(changed & ~mask))
    return {
        "before_png": str(Path(before_png)),
        "after_png": str(Path(after_png)),
        "before_png_sha256": before_hash,
        "after_png_sha256": after_hash,
        "coverage_fraction": covered / target_area,
        "leakage_pixels": leakage,
        "changed_pixels": int(np.count_nonzero(changed)),
        "png_audit_status": "passed" if covered / target_area >= 0.99 and leakage == 0 else "failed",
        "change_threshold": PNG_CHANGE_THRESHOLD,
        "audit_method": "rgb_absolute_difference_on_logical_board_crop",
    }


def build_fill001_capture(
    task: dict[str, Any],
    monitor_export: Any,
    *,
    sampling_profile: dict[str, Any],
    before_png: str | Path,
    after_png: str | Path,
    run_id: str,
    bridge_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    """Convert one unmodified Game Monitor export into a validated capture.

    The export must contain the full event list; truncated, reordered, mixed-radius,
    incomplete or diagnostically degraded runs are rejected.
    """
    if not isinstance(task, dict) or not isinstance(monitor_export, dict):
        raise FillMatrixError("Task и Monitor export должны быть JSON objects.")
    if sampling_profile != FILL001_SAMPLING_PROFILE or sampling_profile != task.get("sampling_profile"):
        raise FillMatrixError("Sampling profile не совпадает с frozen P1 (step=4, delay=5 ms).")
    if not isinstance(run_id, str) or not run_id.strip():
        raise FillMatrixError("Требуется внешний уникальный run_id.")
    if not isinstance(bridge_diagnostics, dict):
        raise FillMatrixError("Требуется отдельный bridge diagnostics report.")
    if bridge_diagnostics.get("run_id") != run_id or bridge_diagnostics.get("event_count") != monitor_export.get("eventCount"):
        raise FillMatrixError("Bridge diagnostics не связаны с этим run_id/eventCount.")
    for key in ("bridge_failures", "sequence_gaps"):
        value = bridge_diagnostics.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise FillMatrixError(f"Некорректный bridge diagnostic: {key}.")
    if monitor_export.get("schemaVersion") != 1:
        raise FillMatrixError("Неподдерживаемая schemaVersion Game Monitor.")
    if monitor_export.get("monitorVersion") != FILL001_MONITOR_VERSION:
        raise FillMatrixError("Game Monitor version не совпадает с проверенной schema adapter.")
    events = monitor_export.get("events")
    if not isinstance(events, list) or not events:
        raise FillMatrixError("Monitor export не содержит event list.")
    if monitor_export.get("eventCount") != len(events):
        raise FillMatrixError("eventCount не совпадает с длиной events: возможна потеря событий.")
    dropped = monitor_export.get("droppedEvents")
    errors = monitor_export.get("errors")
    if dropped != 0 or not isinstance(errors, list) or errors:
        raise FillMatrixError("Monitor export содержит dropped events или errors.")

    previous_time = -1.0
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise FillMatrixError(f"Некорректное событие #{index}.")
        event_time = event.get("t")
        if isinstance(event_time, bool) or not isinstance(event_time, (int, float)) or event_time < previous_time:
            raise FillMatrixError(f"Нарушен порядок событий по t у события #{index}.")
        previous_time = event_time

    starts = [i for i, event in enumerate(events) if event.get("type") == "DRAW_START"]
    ends = [i for i, event in enumerate(events) if event.get("type") == "DRAW_END"]
    if len(starts) != task.get("expected_strokes") or len(ends) != len(starts):
        raise FillMatrixError("Число DRAW_START/DRAW_END не совпадает с expected_strokes.")
    if any(start_index >= end_index for start_index, end_index in zip(starts, ends)):
        raise FillMatrixError("Нарушен порядок границ штрихов.")

    stroke_deltas: list[int] = []
    seen_stroke_ids: set[str] = set()
    for start_index, end_index in zip(starts, ends):
        start, end = events[start_index], events[end_index]
        stroke_id = start.get("strokeId")
        if not isinstance(stroke_id, str) or not stroke_id or stroke_id in seen_stroke_ids:
            raise FillMatrixError("Отсутствует или повторяется strokeId.")
        seen_stroke_ids.add(stroke_id)
        if end.get("strokeId") != stroke_id:
            raise FillMatrixError("DRAW_END не соответствует DRAW_START по strokeId.")
        if any(
            event.get("type") == "DRAW_START"
            for event in events[start_index + 1:end_index]
        ):
            raise FillMatrixError("Вложенные/перекрывающиеся штрихи не поддерживаются.")
        before_count = _snapshot_point_count(start.get("before"), "DRAW_START.before")
        after_count = _snapshot_point_count(end.get("after"), "DRAW_END.after")
        delta = after_count - before_count
        if delta <= 0:
            raise FillMatrixError("Штрих не добавил точек или pointCount уменьшился.")
        samples = [
            event for event in events[start_index + 1:end_index]
            if event.get("type") == "DRAW_SAMPLE"
        ]
        sample_deltas = []
        for sample in samples:
            if sample.get("strokeId") != stroke_id:
                raise FillMatrixError("DRAW_SAMPLE привязан к другому strokeId.")
            point_delta = sample.get("pointDelta")
            if point_delta is None:
                continue
            if isinstance(point_delta, bool) or not isinstance(point_delta, int) or point_delta < 0:
                raise FillMatrixError("Некорректный DRAW_SAMPLE.pointDelta.")
            sample_deltas.append(point_delta)
        start_applied = next((event for event in events[start_index + 1:end_index] if event.get("type") == "DRAW_START_APPLIED"), None)
        if not isinstance(start_applied, dict):
            raise FillMatrixError("Отсутствует DRAW_START_APPLIED.")
        applied_count = _snapshot_point_count(start_applied.get("after"), "DRAW_START_APPLIED.after")
        initial_delta = applied_count - before_count
        if initial_delta < 0 or sum(sample_deltas) + initial_delta != delta:
            raise FillMatrixError("Сумма initial point и DRAW_SAMPLE.pointDelta не совпадает с delta штриха.")
        stroke_deltas.append(delta)

    radius_events = [
        event for event in events
        if event.get("type") == "BRUSH_CHANGE_APPLIED"
    ]
    if not radius_events:
        raise FillMatrixError("Нет BRUSH_CHANGE_APPLIED для подтверждения observed radius.")
    observed_radii = {
        event.get("after", {}).get("currentRadius")
        for event in radius_events
        if isinstance(event.get("after"), dict)
    }
    if observed_radii != {task.get("requested_radius")}:
        raise FillMatrixError("Observed radius отсутствует, неоднозначен или отличается от task.")

    relevant_errors = [event for event in events if event.get("type") == "GAME_METHOD_ERROR"]
    if relevant_errors:
        raise FillMatrixError("Game Monitor зафиксировал GAME_METHOD_ERROR.")

    pre_count = _snapshot_point_count(events[starts[0]].get("before"), "first DRAW_START.before")
    post_count = _snapshot_point_count(events[ends[-1]].get("after"), "last DRAW_END.after")
    exact_chalk = post_count - pre_count
    if sum(stroke_deltas) != exact_chalk:
        raise FillMatrixError("Сумма per-stroke CHALK не совпадает с run-level exact CHALK.")

    if fill_target_mask_sha256(task["shape_id"]) != task.get("target_mask_sha256"):
        raise FillMatrixError("Task target_mask_sha256 не совпадает с frozen mask.")
    png_audit = audit_fill001_png_pair(task["shape_id"], before_png, after_png)
    capture = {
        "task_id": task["task_id"],
        "run_id": run_id,
        "plan_signature": task["plan_signature"],
        "target_mask_sha256": task["target_mask_sha256"],
        "requested_radius": task["requested_radius"],
        "observed_radius": next(iter(observed_radii)),
        "pre_point_count": pre_count,
        "post_point_count": post_count,
        "exact_chalk": exact_chalk,
        "coverage_fraction": png_audit["coverage_fraction"],
        "leakage_pixels": png_audit["leakage_pixels"],
        "completed_strokes": len(stroke_deltas),
        "expected_strokes": task["expected_strokes"],
        "dropped_events": dropped,
        "monitor_errors": len(errors),
        "bridge_failures": bridge_diagnostics["bridge_failures"],
        "sequence_gaps": bridge_diagnostics["sequence_gaps"],
        "stroke_chalk_deltas": stroke_deltas,
        "before_png": png_audit["before_png"],
        "after_png": png_audit["after_png"],
        "before_png_sha256": png_audit["before_png_sha256"],
        "after_png_sha256": png_audit["after_png_sha256"],
        "png_audit_status": png_audit["png_audit_status"],
        "sampling_profile": dict(sampling_profile),
        "monitor_version": monitor_export["monitorVersion"],
        "event_count": len(events),
        "png_audit": png_audit,
    }
    from chalk_fill_matrix import validate_fill001_capture
    validate_fill001_capture(task, capture)
    return capture

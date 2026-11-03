from __future__ import annotations

"""Fail-closed adapter from Game Monitor exports to FILL-001 captures."""

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from brush_coordinate_transform import (
    LOGICAL_BOARD_HEIGHT,
    LOGICAL_BOARD_WIDTH,
    MAX_UNIFORM_SCALE_RELATIVE_ERROR,
)
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
    *,
    screen_roi: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Compare a client-resolution screen crop against the frozen logical mask.

    The game canvas and frozen mask remain 460x240 logical pixels. The captured
    PNG is the calibrated client ROI and may have any dimensions whose aspect
    ratio matches the game's uniform BoardPane scale.
    """
    before, before_hash = _png_pixels(before_png)
    after, after_hash = _png_pixels(after_png)
    if before.shape != after.shape or before.ndim != 3 or before.shape[2] != 3:
        raise FillMatrixError("PNG before/after должны иметь одинаковый RGB размер.")
    screen_height, screen_width = before.shape[:2]
    if screen_width < 2 or screen_height < 2:
        raise FillMatrixError("Screen ROI PNG должен быть не меньше 2x2 px.")

    roi_record = None
    if screen_roi is not None:
        if not isinstance(screen_roi, dict):
            raise FillMatrixError("screen_roi должен быть объектом калибровки.")
        required = ("x", "y", "width", "height")
        if any(
            isinstance(screen_roi.get(key), bool) or not isinstance(screen_roi.get(key), int)
            for key in required
        ):
            raise FillMatrixError("screen_roi должен содержать целые x, y, width и height.")
        if screen_roi["x"] < 0 or screen_roi["y"] < 0:
            raise FillMatrixError("Координаты calibrated screen ROI не могут быть отрицательными.")
        if screen_roi["width"] < 2 or screen_roi["height"] < 2:
            raise FillMatrixError("Calibrated screen ROI должен быть не меньше 2x2 px.")
        if (screen_roi["width"], screen_roi["height"]) != (screen_width, screen_height):
            raise FillMatrixError("Размер PNG не совпадает с фактическим calibrated screen ROI.")
        roi_record = {key: int(screen_roi[key]) for key in required}

    scale_x = (screen_width - 1) / LOGICAL_BOARD_WIDTH
    scale_y = (screen_height - 1) / LOGICAL_BOARD_HEIGHT
    scale_error = abs(scale_x - scale_y) / max(scale_x, scale_y)
    if scale_error > MAX_UNIFORM_SCALE_RELATIVE_ERROR:
        raise FillMatrixError(
            "Пропорции screen ROI не соответствуют равномерному масштабу BoardPane: "
            f"scaleX={scale_x:.6f}, scaleY={scale_y:.6f}, "
            f"расхождение={scale_error:.2%} (допуск {MAX_UNIFORM_SCALE_RELATIVE_ERROR:.0%}). "
            "Проверьте калибровку границ игровой доски."
        )

    logical_mask = build_fill_target_mask(shape_id)
    mask_image = Image.fromarray(logical_mask.astype(np.uint8) * 255, mode="L")
    screen_mask = np.asarray(
        mask_image.resize((screen_width, screen_height), resample=Image.Resampling.NEAREST),
        dtype=np.uint8,
    ) > 0
    changed = np.any(np.abs(after - before) > PNG_CHANGE_THRESHOLD, axis=2)
    target_area = int(np.count_nonzero(screen_mask))
    if target_area <= 0:
        raise FillMatrixError("После rasterization frozen mask стала пустой.")
    covered = int(np.count_nonzero(changed & screen_mask))
    leakage = int(np.count_nonzero(changed & ~screen_mask))
    coverage = covered / target_area
    transform = {
        "method": "logical_mask_nearest_neighbor_to_calibrated_screen_roi",
        "source_coordinate_system": "logical_board_pixels",
        "target_coordinate_system": "screen_roi_pixels",
        "logical_board": {"width": LOGICAL_BOARD_WIDTH, "height": LOGICAL_BOARD_HEIGHT},
        "screen_roi": roi_record or {"width": screen_width, "height": screen_height},
        "scale_x": scale_x,
        "scale_y": scale_y,
        "uniform_scale_relative_error": scale_error,
        "uniform_scale_tolerance": MAX_UNIFORM_SCALE_RELATIVE_ERROR,
        "mask_raster_scale_x": screen_width / LOGICAL_BOARD_WIDTH,
        "mask_raster_scale_y": screen_height / LOGICAL_BOARD_HEIGHT,
        "mask_resampling": "nearest_neighbor",
    }
    return {
        "before_png": str(Path(before_png)),
        "after_png": str(Path(after_png)),
        "before_png_sha256": before_hash,
        "after_png_sha256": after_hash,
        "coverage_fraction": coverage,
        "leakage_pixels": leakage,
        "changed_pixels": int(np.count_nonzero(changed)),
        "target_pixels": target_area,
        "png_audit_status": "passed" if coverage >= 0.99 and leakage == 0 else "failed",
        "change_threshold": PNG_CHANGE_THRESHOLD,
        "audit_method": "rgb_absolute_difference_on_calibrated_screen_roi",
        "logical_to_screen_transform": transform,
    }



def _complete_lifecycle_pairs(
    events: list[dict[str, Any]],
    start_type: str,
    end_type: str,
    expected_strokes: int,
) -> list[tuple[int, int, str]] | None:
    starts = [i for i, event in enumerate(events) if event.get("type") == start_type]
    ends = [i for i, event in enumerate(events) if event.get("type") == end_type]
    if len(starts) != expected_strokes or len(ends) != expected_strokes:
        return None
    pairs: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    for start_index, end_index in zip(starts, ends):
        if start_index >= end_index:
            return None
        stroke_id = events[start_index].get("strokeId")
        if not isinstance(stroke_id, str) or not stroke_id or stroke_id in seen:
            return None
        if events[end_index].get("strokeId") != stroke_id:
            return None
        if any(events[index].get("type") == start_type for index in range(start_index + 1, end_index)):
            return None
        seen.add(stroke_id)
        pairs.append((start_index, end_index, stroke_id))
    return pairs


def _extract_stroke_chalk_deltas(
    events: list[dict[str, Any]],
    expected_strokes: int,
    lifecycle_source: str,
) -> tuple[list[int], int, int]:
    if lifecycle_source == "engine":
        pairs = _complete_lifecycle_pairs(events, "DRAW_START", "DRAW_END", expected_strokes)
        start_snapshot_key, end_snapshot_key = "before", "after"
    elif lifecycle_source == "pointer_observer":
        pairs = _complete_lifecycle_pairs(
            events, "POINTER_DOWN_CANDIDATE", "POINTER_UP_CANDIDATE", expected_strokes
        )
        start_snapshot_key = end_snapshot_key = "board"
    else:
        raise FillMatrixError("Неизвестный stroke lifecycle source.")
    if pairs is None:
        raise FillMatrixError(f"Нет полного {lifecycle_source} lifecycle для всех штрихов.")

    stroke_deltas: list[int] = []
    assigned_samples: set[int] = set()
    for start_index, end_index, stroke_id in pairs:
        start, end = events[start_index], events[end_index]
        before_count = _snapshot_point_count(
            start.get(start_snapshot_key), f"{lifecycle_source} start snapshot"
        )
        after_count = _snapshot_point_count(
            end.get(end_snapshot_key), f"{lifecycle_source} end snapshot"
        )
        delta = after_count - before_count
        if delta <= 0:
            raise FillMatrixError("Штрих не добавил точек или pointCount уменьшился.")
        samples = []
        for index in range(start_index + 1, end_index):
            event = events[index]
            if event.get("type") == "DRAW_SAMPLE":
                if event.get("strokeId") != stroke_id:
                    raise FillMatrixError("DRAW_SAMPLE внутри stroke lifecycle привязан к другому strokeId.")
                point_delta = event.get("pointDelta")
                if isinstance(point_delta, bool) or not isinstance(point_delta, int) or point_delta < 0:
                    raise FillMatrixError("Некорректный или отсутствующий DRAW_SAMPLE.pointDelta.")
                samples.append(point_delta)
                assigned_samples.add(index)

        if not samples:
            raise FillMatrixError("В stroke lifecycle отсутствуют DRAW_SAMPLE events.")
        if lifecycle_source == "engine":
            applied = [
                event for event in events[start_index + 1:end_index]
                if event.get("type") == "DRAW_START_APPLIED"
            ]
            if len(applied) != 1 or applied[0].get("strokeId") != stroke_id:
                raise FillMatrixError("Отсутствует однозначный DRAW_START_APPLIED.")
            applied_count = _snapshot_point_count(
                applied[0].get("after"), "DRAW_START_APPLIED.after"
            )
            initial_delta = applied_count - before_count
            if initial_delta < 0 or sum(samples) + initial_delta != delta:
                raise FillMatrixError("Initial point + DRAW_SAMPLE deltas не совпадают с delta штриха.")
        elif sum(samples) != delta:
            raise FillMatrixError("Pointer-observer DRAW_SAMPLE deltas не совпадают с board snapshot delta.")
        stroke_deltas.append(delta)

    all_sample_indices = {
        index for index, event in enumerate(events) if event.get("type") == "DRAW_SAMPLE"
    }
    if assigned_samples != all_sample_indices:
        raise FillMatrixError("Есть DRAW_SAMPLE вне подтверждённых stroke lifecycle boundaries.")
    pre_count = _snapshot_point_count(
        events[pairs[0][0]].get(start_snapshot_key), f"first {lifecycle_source} start"
    )
    post_count = _snapshot_point_count(
        events[pairs[-1][1]].get(end_snapshot_key), f"last {lifecycle_source} end"
    )
    return stroke_deltas, pre_count, post_count


def build_fill001_capture(
    task: dict[str, Any],
    monitor_export: Any,
    *,
    sampling_profile: dict[str, Any],
    before_png: str | Path,
    after_png: str | Path,
    run_id: str,
    bridge_diagnostics: dict[str, Any],
    stroke_lifecycle_source: str | None = None,
    observed_radius: int | float | None = None,
    screen_roi: dict[str, int] | None = None,
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

    expected_strokes = task.get("expected_strokes")
    engine_pairs = _complete_lifecycle_pairs(events, "DRAW_START", "DRAW_END", expected_strokes)
    pointer_pairs = _complete_lifecycle_pairs(
        events, "POINTER_DOWN_CANDIDATE", "POINTER_UP_CANDIDATE", expected_strokes
    )
    if stroke_lifecycle_source is None:
        if engine_pairs is not None:
            stroke_lifecycle_source = "engine"
        elif pointer_pairs is not None:
            stroke_lifecycle_source = "pointer_observer"
        else:
            raise FillMatrixError("Нет полного engine или pointer lifecycle для всех штрихов.")
    stroke_deltas, pre_count, post_count = _extract_stroke_chalk_deltas(
        events, expected_strokes, stroke_lifecycle_source
    )

    radius_events = [
        event for event in events
        if event.get("type") == "BRUSH_CHANGE_APPLIED"
    ]
    event_radii = {
        event.get("after", {}).get("currentRadius")
        for event in radius_events
        if isinstance(event.get("after"), dict)
    }
    if observed_radius is None:
        if not radius_events or event_radii != {task.get("requested_radius")}:
            raise FillMatrixError("Observed radius отсутствует, неоднозначен или отличается от task.")
        observed_radius = next(iter(event_radii))
    elif observed_radius != task.get("requested_radius"):
        raise FillMatrixError("Runtime observed radius отличается от task.")
    elif event_radii and event_radii != {task.get("requested_radius")}:
        raise FillMatrixError("BRUSH_CHANGE_APPLIED расходится с runtime observed radius.")

    relevant_errors = [event for event in events if event.get("type") == "GAME_METHOD_ERROR"]
    if relevant_errors:
        raise FillMatrixError("Game Monitor зафиксировал GAME_METHOD_ERROR.")

    exact_chalk = post_count - pre_count
    if sum(stroke_deltas) != exact_chalk:
        raise FillMatrixError("Сумма per-stroke CHALK не совпадает с run-level exact CHALK.")

    if fill_target_mask_sha256(task["shape_id"]) != task.get("target_mask_sha256"):
        raise FillMatrixError("Task target_mask_sha256 не совпадает с frozen mask.")
    png_audit = audit_fill001_png_pair(
        task["shape_id"], before_png, after_png, screen_roi=screen_roi
    )
    capture = {
        "task_id": task["task_id"],
        "run_id": run_id,
        "plan_signature": task["plan_signature"],
        "target_mask_sha256": task["target_mask_sha256"],
        "requested_radius": task["requested_radius"],
        "observed_radius": observed_radius,
        "stroke_lifecycle_source": stroke_lifecycle_source,
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
        "screen_roi": png_audit["logical_to_screen_transform"]["screen_roi"],
        "logical_to_screen_transform": png_audit["logical_to_screen_transform"],
    }
    from chalk_fill_matrix import validate_fill001_capture
    validate_fill001_capture(task, capture)
    return capture


def build_fill001_capture_from_runtime(
    task: dict[str, Any],
    *,
    session_path: str | Path,
    executor_report_path: str | Path,
    before_png: str | Path,
    after_png: str | Path,
    screen_roi: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build a live capture only from persisted Bridge and executor runtime artifacts.

    Unlike build_fill001_capture(), this entrypoint does not accept caller-supplied
    run IDs, Bridge diagnostics, or sampling metadata.
    """
    from chalk_fill_runtime_binding import load_fill001_runtime_binding

    binding = load_fill001_runtime_binding(task, session_path, executor_report_path)
    capture = build_fill001_capture(
        task,
        binding["monitor_export"],
        sampling_profile=binding["sampling_profile"],
        before_png=before_png,
        after_png=after_png,
        run_id=binding["run_id"],
        bridge_diagnostics=binding["bridge_diagnostics"],
        stroke_lifecycle_source=binding["stroke_lifecycle_source"],
        observed_radius=binding["observed_radius"],
        screen_roi=screen_roi,
    )
    capture.update({
        "session_id": binding["session_id"],
        "execution_id": binding["execution_id"],
        "executor_config": binding["executor_config"],
        "source_plan_file_sha256": binding["source_plan_file_sha256"],
        "session_file": binding["session_file"],
        "session_file_sha256": binding["session_file_sha256"],
        "bridge_run_file": binding["bridge_run_file"],
        "bridge_run_file_sha256": binding["bridge_run_file_sha256"],
        "executor_report_file": binding["executor_report_file"],
        "executor_report_file_sha256": binding["executor_report_file_sha256"],
        "runtime_binding_status": "passed",
    })
    return capture

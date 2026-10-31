from __future__ import annotations

import json
import shutil
import uuid
import ctypes
import platform
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any

import pyautogui
from PIL import Image, ImageGrab
from pynput import keyboard

from brush_test_workflow import (
    calculate_slider_target, validate_brush_test_preflight, validate_observed_brush_radius,
    should_run_postdraw_workflow,
)
from brush_experiment_capture import (
    compare_images, crop_calibrated_regions,
    measure_meter_fill_against_baseline, evaluate_meter_restoration, evaluate_board_clear,
    measure_stroke_visibility,
)


# Verified against the master game bundle: Graphics.lineStyle receives atom.radius directly.
MAX_BRUSH_LINE_WIDTH_LOGICAL_PX = 30;



def _parse_monitor_timestamp(value: Any) -> datetime | None:
    """Parse an ISO timestamp as an aware UTC datetime."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)



def is_exact_positive_chalk_measurement(chalk: dict[str, Any]) -> bool:
    """Accept only a positive, internally consistent, non-reset CHALK counter delta."""
    try:
        pre = int(chalk.get("pre_point_count"))
        post = int(chalk.get("post_point_count"))
        consumed = int(chalk.get("consumed_points"))
    except (TypeError, ValueError):
        return False
    return (
        chalk.get("status") == "exact"
        and post >= pre
        and post - pre == consumed
        and consumed > 0
    )


def select_execution_monitor_run(
    candidates: list[tuple[Path, dict[str, Any]]],
    *,
    execution_report: dict[str, Any],
    requested_brush: int | None,
    expected_strokes: int,
    before_draw_at: str | None = None,
) -> tuple[tuple[Path, dict[str, Any]] | None, str, int]:
    """Select one run strictly correlated with an executor interval; never guess by mtime."""
    if expected_strokes <= 0:
        return None, "expected_stroke_count_unavailable", 0
    execution_start = _parse_monitor_timestamp(execution_report.get("started_at"))
    execution_end = _parse_monitor_timestamp(execution_report.get("ended_at"))
    if execution_start is None or execution_end is None or execution_end < execution_start:
        return None, "execution_time_window_unavailable", 0

    before_draw = _parse_monitor_timestamp(before_draw_at)
    window_start = execution_start - timedelta(seconds=1)
    if before_draw is not None:
        window_start = max(window_start, before_draw)
    # The collector may finalize shortly after the executor releases the mouse.
    window_end = execution_end + timedelta(seconds=5)

    matching: list[tuple[Path, dict[str, Any]]] = []
    for source_path, report in candidates:
        if not isinstance(report, dict) or report.get("record_type") != "autodraw_game_monitor_run":
            continue
        if report.get("execution_status") not in {"completed", "partial"}:
            continue
        started = _parse_monitor_timestamp(report.get("started_at_utc"))
        finished = _parse_monitor_timestamp(report.get("finished_at_utc"))
        if started is None or finished is None or finished < started:
            continue
        if started < window_start or finished > window_end:
            continue
        try:
            observed_brush = int(round(float(report.get("brush_radius"))))
            stroke_count = int(report.get("stroke_count", 0))
        except (TypeError, ValueError, OverflowError):
            continue
        if requested_brush is not None and observed_brush != requested_brush:
            continue
        if stroke_count != expected_strokes:
            continue
        radii = report.get("observed_brush_radii")
        if report.get("brush_radius_status") != "single":
            continue
        if not isinstance(radii, list) or radii != [observed_brush]:
            continue
        matching.append((source_path, report))

    if len(matching) == 1:
        return matching[0], "matched_executor_window", 1
    if len(matching) > 1:
        return None, "ambiguous_executor_window", len(matching)
    return None, "no_run_matches_executor_window", 0


def _screen_local_strokes_for_capture(
    plan: dict[str, Any],
    board_size: tuple[int, int],
) -> tuple[list[dict[str, Any]] | None, str | None]:
    """Return expected strokes in screenshot-ROI pixels, using saved logical transform."""
    strokes = plan.get("strokes")
    if not isinstance(strokes, list):
        return None, "drawing_plan_has_no_strokes"
    canvas = plan.get("canvas")
    if not isinstance(canvas, dict):
        return None, "drawing_plan_has_no_canvas"
    try:
        canvas_size = (int(canvas.get("width", -1)), int(canvas.get("height", -1)))
    except (TypeError, ValueError):
        return None, "drawing_plan_canvas_dimensions_invalid"
    if canvas_size == board_size:
        return strokes, None

    if plan.get("coordinate_system") != "logical_board_pixels":
        return None, "drawing_plan_canvas_dimensions_mismatch"
    generation = plan.get("generation")
    transform = generation.get("screen_transform") if isinstance(generation, dict) else None
    if not isinstance(transform, dict):
        return None, "drawing_plan_canvas_dimensions_mismatch"
    roi = transform.get("screen_roi")
    logical_board = transform.get("logical_board")
    if not isinstance(roi, dict) or not isinstance(logical_board, dict):
        return None, "drawing_plan_screen_transform_missing"
    try:
        roi_size = (int(roi.get("width", -1)), int(roi.get("height", -1)))
        logical_size = (int(logical_board.get("width", -1)), int(logical_board.get("height", -1)))
        scale_x = float(transform["scale_x"])
        scale_y = float(transform["scale_y"])
    except (KeyError, TypeError, ValueError):
        return None, "drawing_plan_screen_transform_invalid"
    if roi_size != board_size:
        return None, "drawing_plan_screen_transform_roi_mismatch"
    if logical_size != canvas_size or scale_x <= 0 or scale_y <= 0:
        return None, "drawing_plan_screen_transform_invalid"

    screen_strokes: list[dict[str, Any]] = []
    for stroke in strokes:
        if not isinstance(stroke, dict) or not isinstance(stroke.get("points"), list):
            return None, "drawing_plan_strokes_invalid"
        screen_stroke = dict(stroke)
        screen_points: list[dict[str, Any]] = []
        for point in stroke["points"]:
            if not isinstance(point, dict):
                return None, "drawing_plan_points_invalid"
            try:
                x, y = float(point["x"]), float(point["y"])
            except (KeyError, TypeError, ValueError):
                return None, "drawing_plan_points_invalid"
            screen_point = dict(point)
            screen_point["x"] = x * scale_x
            screen_point["y"] = y * scale_y
            screen_points.append(screen_point)
        screen_stroke["points"] = screen_points
        screen_strokes.append(screen_stroke)
    return screen_strokes, None

TEST_CASES: dict[str, dict[str, Any]] = {
    "Расход краски — серия длинных линий": {
        "id": "paint_consumption_long_lines",
        "description": (
            "Контрольная серия из 6 длинных параллельных линий длиной 400 px с шагом 36 px. "
            "Шаг выбран больше максимальной номинальной толщины линии из движка (30 логических px) "
            "с запасом 6 px. Перед измерением обязательно подтвердить фактическую кисть и "
            "исходное состояние ресурса; это не измеряет расход на отдельный штрих автоматически."
        ),
        "strokes": [
            {
                "name": f"consumption_line_{index + 1:02d}",
                "points": [[20, 18 + index * 36], [420, 18 + index * 36]],
            }
            for index in range(6)
        ],
    },
    "Горизонтальные линии": {
        "id": "horizontal_lengths",
        "description": "Проверка длины и фактической ширины следа на прямых линиях.",
        "strokes": [
            {"name": "horizontal_10", "points": [[20, 20], [30, 20]]},
            {"name": "horizontal_20", "points": [[20, 45], [40, 45]]},
            {"name": "horizontal_50", "points": [[20, 70], [70, 70]]},
            {"name": "horizontal_100", "points": [[20, 95], [120, 95]]},
            {"name": "horizontal_200", "points": [[20, 120], [220, 120]]},
        ],
    },
    "Вертикальные линии": {
        "id": "vertical_lengths",
        "description": "Проверка ширины следа по X и окончания вертикального штриха.",
        "strokes": [
            {"name": "vertical_10", "points": [[20, 20], [20, 30]]},
            {"name": "vertical_20", "points": [[45, 20], [45, 40]]},
            {"name": "vertical_50", "points": [[70, 20], [70, 70]]},
            {"name": "vertical_100", "points": [[95, 20], [95, 120]]},
        ],
    },
    "Диагонали": {
        "id": "diagonal_lengths",
        "description": "Проверка кривизны диагонали, формы концов и эффективной длины.",
        "strokes": [
            {"name": "diagonal_20", "points": [[20, 20], [40, 40]]},
            {"name": "diagonal_50", "points": [[20, 55], [70, 105]]},
            {"name": "diagonal_100", "points": [[20, 120], [120, 220]]},
        ],
    },
    "Короткие линии и точки": {
        "id": "short_strokes",
        "description": "Поиск минимальной длины, которая стабильно появляется в игре.",
        "strokes": [
            {"name": "length_0", "points": [[15, 20], [15, 20]]},
            {"name": "length_1", "points": [[35, 20], [36, 20]]},
            {"name": "length_2", "points": [[55, 20], [57, 20]]},
            {"name": "length_3", "points": [[75, 20], [78, 20]]},
            {"name": "length_5", "points": [[95, 20], [100, 20]]},
            {"name": "length_8", "points": [[115, 20], [123, 20]]},
            {"name": "length_10", "points": [[135, 20], [145, 20]]},
        ],
    },
    "Прямоугольник и углы": {
        "id": "rectangle_corners",
        "description": "Проверка соединения линий, скругления углов и замыкания контура.",
        "strokes": [
            {"name": "top", "points": [[20, 20], [120, 20]]},
            {"name": "right", "points": [[120, 20], [120, 80]]},
            {"name": "bottom", "points": [[120, 80], [20, 80]]},
            {"name": "left", "points": [[20, 80], [20, 20]]},
        ],
    },
    "Непрерывные повороты": {
        "id": "continuous_turns",
        "description": (
            "Проверка одного непрерывного штриха с прямыми углами, острым поворотом и S-образной траекторией. "
            "Нужна для оценки скругления углов, срезания поворотов и непрерывности следа."
        ),
        "strokes": [
            {"name": "right_angle_path", "points": [[25, 25], [115, 25], [115, 85], [205, 85]]},
            {"name": "acute_turn_path", "points": [[25, 115], [95, 165], [155, 115], [225, 165]]},
            {"name": "s_curve_path", "points": [[250, 25], [290, 55], [250, 85], [290, 115], [250, 145]]},
        ],
    },
    "Параллельные линии и расстояние": {
        "id": "parallel_spacing",
        "description": (
            "Проверка фактической ширины следа, равномерности и слияния параллельных линий "
            "при разных расстояниях между центральными линиями."
        ),
        "strokes": [
            {"name": "spacing_4px_a", "points": [[20, 25], [200, 25]]},
            {"name": "spacing_4px_b", "points": [[20, 29], [200, 29]]},
            {"name": "spacing_8px_a", "points": [[20, 55], [200, 55]]},
            {"name": "spacing_8px_b", "points": [[20, 63], [200, 63]]},
            {"name": "spacing_16px_a", "points": [[20, 95], [200, 95]]},
            {"name": "spacing_16px_b", "points": [[20, 111], [200, 111]]},
            {"name": "spacing_24px_a", "points": [[20, 145], [200, 145]]},
            {"name": "spacing_24px_b", "points": [[20, 169], [200, 169]]},
        ],
    },
    "Замкнутый контур одной траекторией": {
        "id": "continuous_closed_contour",
        "description": (
            "Проверка замыкания непрерывного маршрута, стыка начала/конца и углов без разрыва между отдельными штрихами."
        ),
        "strokes": [
            {"name": "closed_rectangle_path", "points": [[35, 35], [205, 35], [205, 155], [35, 155], [35, 35]]},
            {"name": "closed_triangle_path", "points": [[255, 45], [365, 165], [145, 165], [255, 45]]},
        ],
    },
    "Проверка границ доски": {
        "id": "board_boundary_probe",
        "description": (
            "Короткая контрольная серия для проверки попадания курсора в четыре включительные границы BoardPane 460×240. "
            "Каждый штрих начинается внутри доски и заканчивается точно на одной из границ; для первого запуска "
            "используй радиус 1 и проверь фактические точки через Game Monitor."
        ),
        "strokes": [
            {"name": "right_boundary_probe", "points": [[420, 120], [460, 120]]},
            {"name": "left_boundary_probe", "points": [[40, 120], [0, 120]]},
            {"name": "bottom_boundary_probe", "points": [[230, 200], [230, 240]]},
            {"name": "top_boundary_probe", "points": [[230, 40], [230, 0]]},
        ],
    },
    "Длинные изолированные линии": {
        "id": "long_isolated_lines",
        "description": "Контроль геометрии длинных независимых горизонтальных и вертикальных штрихов на полном диапазоне доски.",
        "strokes": [
            {"name": "horizontal_100", "points": [[20, 18], [120, 18]]},
            {"name": "horizontal_200", "points": [[20, 54], [220, 54]]},
            {"name": "horizontal_300", "points": [[20, 90], [320, 90]]},
            {"name": "horizontal_400", "points": [[20, 126], [420, 126]]},
            {"name": "vertical_100", "points": [[55, 18], [55, 118]]},
            {"name": "vertical_180", "points": [[115, 18], [115, 198]]}
        ]
    },
    "Повторное покрытие одного следа": {
        "id": "repeated_coverage",
        "description": "Три независимых повторных прохода по одним и тем же координатам; сравнивать путь, точки и новые пиксели отдельно.",
        "strokes": [
            {"name": "repeat_pass_1", "points": [[30, 45], [230, 45]]},
            {"name": "repeat_pass_2", "points": [[30, 45], [230, 45]]},
            {"name": "repeat_pass_3", "points": [[30, 45], [230, 45]]},
            {"name": "control_parallel", "points": [[30, 105], [230, 105]]}
        ]
    },
    "Поперечный профиль и пересечения": {
        "id": "cross_section_intersections",
        "description": "Пересечение горизонтальных и вертикальных линий в центре и смещённой точке для оценки формы следа и соединения штрихов.",
        "strokes": [
            {"name": "horizontal_center", "points": [[40, 70], [420, 70]]},
            {"name": "vertical_center", "points": [[230, 20], [230, 220]]},
            {"name": "horizontal_offset", "points": [[40, 170], [420, 170]]},
            {"name": "vertical_offset", "points": [[120, 120], [120, 220]]}
        ]
    }
}


def summarize_game_monitor_report(
    document: dict[str, Any],
    requested_brush_value: int | None = None,
) -> dict[str, Any]:
    """Summarize passive telemetry and compare requested size with radii used by actual draw samples."""
    if not isinstance(document, dict):
        raise ValueError("Отчёт Monitor должен содержать JSON-объект.")
    events = document.get("events")
    if not isinstance(events, list):
        raise ValueError("В JSON нет массива events; выбери полный экспорт Game Monitor.")

    counts: dict[str, int] = {}
    drawing_samples = []
    for event in events:
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("type", "UNKNOWN"))
        counts[event_type] = counts.get(event_type, 0) + 1
        if event_type == "DRAW_SAMPLE" and event.get("source") == "onDrawing_wrapper":
            drawing_samples.append(event)

    radii: set[int] = set()
    for event in drawing_samples:
        board = event.get("board")
        values = board.get("radius") if isinstance(board, dict) else None
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            if int(value) == value and int(value) > 0:
                radii.add(int(value))

    observed = sorted(radii)
    if requested_brush_value is None:
        brush_status = "not_compared"
        brush_matches = None
    elif not observed:
        brush_status = "unavailable"
        brush_matches = None
    elif observed == [requested_brush_value]:
        brush_status = "match"
        brush_matches = True
    elif requested_brush_value in observed:
        brush_status = "mixed"
        brush_matches = False
    else:
        brush_status = "mismatch"
        brush_matches = False

    return {
        "monitor_version": document.get("monitorVersion"),
        "event_count": document.get("eventCount", len(events)),
        "dropped_events": document.get("droppedEvents"),
        "error_count": len(document.get("errors", [])) if isinstance(document.get("errors"), list) else None,
        "board_detected": document.get("boardDetected"),
        "event_counts": counts,
        "pointer_down_count": counts.get("POINTER_DOWN_CANDIDATE", 0),
        "pointer_up_count": counts.get("POINTER_UP_CANDIDATE", 0),
        "draw_sample_count": counts.get("DRAW_SAMPLE", 0),
        "drawing_sample_count": len(drawing_samples),
        "requested_brush_value": requested_brush_value,
        "observed_draw_radii": observed,
        "brush_value_status": brush_status,
        "brush_value_matches_requested": brush_matches,
        "interpretation": "passive_browser_telemetry_not_direct_paint_resource_measurement",
    }


def build_brush_test_record(
    *, brush_value: int, test_case: str, canvas_area: dict[str, int] | None = None,
    screen_area: dict[str, int] | None = None, screenshot_path: str | None = None,
    drawing_plan_path: str | None = None, drawing_plan: dict[str, Any] | None = None,
    execution_report_path: str | None = None, execution_report: dict[str, Any] | None = None,
    measurements: dict[str, Any] | None = None, notes: str = "", outcome: str = "not_reviewed",
    screen_resolution: dict[str, int] | None = None, brush_control: dict[str, Any] | None = None,
    game_monitor_report_path: str | None = None, game_monitor_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a versioned, portable observation record for later brush-model fitting."""
    if isinstance(brush_value, bool) or not isinstance(brush_value, int) or not 1 <= brush_value <= 30:
        raise ValueError("Размер кисти должен быть целым числом от 1 до 30.")
    if test_case not in TEST_CASES:
        raise ValueError(f"Неизвестный тест кисти: {test_case}")
    scenario = TEST_CASES[test_case]
    return {
        "schema_version": 1,
        "record_type": "autodraw_brush_behavior_observation",
        "record_id": uuid.uuid4().hex,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "brush_value": brush_value,
        "test_case": {"id": scenario["id"], "name": test_case, "description": scenario["description"]},
        "canvas_area": canvas_area,
        "board_selection_origin": ({"x": canvas_area["x"], "y": canvas_area["y"]} if canvas_area else None),
        "board_selection_size": ({"width": canvas_area["width"], "height": canvas_area["height"]} if canvas_area else None),
        "screen_resolution": screen_resolution,
        "screen_area": screen_area,
        "brush_control": brush_control,
        "screenshot_path": screenshot_path,
        "drawing_plan_path": drawing_plan_path,
        "drawing_plan": drawing_plan,
        "execution_report_path": execution_report_path,
        "execution_report": execution_report,
        "game_monitor_report_path": game_monitor_report_path,
        "game_monitor_summary": game_monitor_summary,
        "outcome": outcome,
        "notes": notes.strip(),
        "planned_strokes": scenario["strokes"],
        "measurement_fields": {
            "observed_stroke_count": None,
            "visible_stroke_names": [],
            "missing_stroke_names": [],
            "measured_footprint_width_px": None,
            "measured_footprint_height_px": None,
            "endpoints_offset_px": None,
            "paint_points_before": None,
            "paint_points_after": None,
            "browser_zoom_percent": None,
            "device_pixel_ratio": None,
            **(measurements or {}),
        },
        "interpretation": {
            "status": "raw_observation",
            "automatic_execution_allowed": False,
            "note": "Запись фиксирует тестовый шаблон и наблюдение; модель кисти строится после заполнения измерений.",
        },
    }


def build_brush_test_drawing_plan(
    test_case: str,
    canvas_size: tuple[int, int],
    *,
    coordinate_system: str = "local_canvas_pixels",
) -> dict[str, Any]:
    """Build a brush-test plan in either screen-local or explicit logical coordinates."""
    if test_case not in TEST_CASES:
        raise ValueError(f"Неизвестный тест кисти: {test_case}")
    if coordinate_system not in {"local_canvas_pixels", "logical_board_pixels"}:
        raise ValueError(f"Неподдерживаемая система координат: {coordinate_system}")
    width, height = (int(canvas_size[0]), int(canvas_size[1]))
    if width < 1 or height < 1:
        raise ValueError("Размер тестового холста должен быть положительным.")
    scenario = TEST_CASES[test_case]
    inclusive_bounds = coordinate_system == "logical_board_pixels"
    strokes = []
    for item in scenario["strokes"]:
        points = item["points"]
        outside = any(
            x < 0 or y < 0 or (x > width or y > height if inclusive_bounds else x >= width or y >= height)
            for x, y in points
        )
        if outside:
            raise ValueError(
                f"Штрих {item['name']} выходит за пределы холста {width} × {height}."
            )
        strokes.append({
            "name": item["name"],
            "points": [{"x": float(x), "y": float(y)} for x, y in points],
            "closed": False,
            "metadata": {"role": "brush_behavior_test", "test_case": scenario["id"], "line_extension_px_override": 0.0},
        })
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "schema_version": 1,
        "name": f"Brush behavior test — {scenario['id']}",
        "created_at": now,
        "coordinate_system": coordinate_system,
        "canvas": {"width": width, "height": height},
        "width": width,
        "height": height,
        "strokes": strokes,
        "generation": {
            "method": "manual_brush_behavior_test",
            "test_case": scenario["id"],
            "brush_value_must_be_set_manually": True,
            "note": "Set the requested brush size in the browser before executing this plan.",
        },
    }


class BrushBehaviorTestTab:
    """Manual browser brush test matrix, screenshot capture, and raw-data storage."""

    def __init__(
        self, root: tk.Misc, parent: tk.Widget, output_dir: str | Path,
        area_selector_cls, *, get_canvas_size, get_canvas_area, on_transfer_plan, get_brush_control=None,
        get_calibration_profile=None, on_brush_ready=None,
    ):
        self.root = root
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.area_selector_cls = area_selector_cls
        self.get_canvas_size = get_canvas_size
        self.get_canvas_area = get_canvas_area
        self.get_brush_control = get_brush_control
        self.get_calibration_profile = get_calibration_profile
        self.on_transfer_plan = on_transfer_plan
        self.on_brush_ready = on_brush_ready
        self._start_executor_after_brush_drag = False
        self.experiment_dir: Path | None = None
        self.experiment_phases: dict[str, dict[str, Any]] = {}
        self.current_plan: dict[str, Any] | None = None
        self.current_plan_path: Path | None = None
        self.canvas_area: dict[str, int] | None = None
        self.screen_area: dict[str, int] | None = None
        self.screen_resolution: dict[str, int] | None = None
        self.brush_slider_start: tuple[int, int] | None = None
        self.brush_slider_end: tuple[int, int] | None = None
        self._brush_drag_state: dict[str, Any] | None = None
        self._brush_drag_after_id: str | None = None
        self._brush_drag_countdown_id: str | None = None
        self._brush_hotkey_listener = None
        self._brush_drag_mouse_down = False
        self._brush_drag_purpose = "set_brush_size"
        self._experiment_requested_brush: int | None = None
        self._postdraw_final_status = "unknown"
        self._postdraw_final_reason = ""
        self._automated_preclear_active = False
        self._automated_preclear_after_id: str | None = None
        self._automated_postdraw_active = False
        self._automated_postdraw_stop_requested = False
        self._automated_postdraw_after_id: str | None = None
        self.root.bind_all("<Alt_L>", self._on_brush_workflow_stop_key, add="+")
        self.root.bind_all("<Alt_R>", self._on_brush_workflow_stop_key, add="+")
        self.screenshot_path: Path | None = None
        self.execution_report_path: Path | None = None
        self.execution_report: dict[str, Any] | None = None
        self.game_monitor_report_path: Path | None = None
        self.game_monitor_summary: dict[str, Any] | None = None
        self._bridge_capture_poll_id: str | None = None
        self.last_record_path: Path | None = None
        self.brush_var = tk.StringVar(value="7")
        self.case_var = tk.StringVar(value=next(iter(TEST_CASES)))
        self.outcome_var = tk.StringVar(value="not_reviewed")
        self.notes_var = tk.StringVar()
        self.visible_strokes_var = tk.StringVar()
        self.missing_strokes_var = tk.StringVar()
        self.footprint_width_var = tk.StringVar()
        self.footprint_height_var = tk.StringVar()
        self.paint_before_var = tk.StringVar()
        self.paint_after_var = tk.StringVar()
        self.zoom_var = tk.StringVar(value="100")
        self.area_var = tk.StringVar(value="Область доски берётся из профиля исполнения.")
        self.slider_start_var = tk.StringVar()
        self.slider_end_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Выбери радиус и тест. Автоустановка 1–30 работает только с расширенным ползунком игры.")
        self._build(parent)
        self._load_brush_control_into_fields()

    def _build(self, parent: tk.Widget) -> None:
        outer = ttk.Frame(parent, padding=10)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Тест поведения кистей", font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text=("Для каждой кисти выполняй тест отдельно на чистой тестовой доске. Сначала запиши исходный запас краски, "
                  "затем выполни указанные штрихи через исполнитель AutoDraw. После завершения выбери область снимка: "
                  "в JSON сохраняются параметры, координаты запланированных штрихов, путь к скриншоту и поля для измерений. "
                  "Размер задаётся радиусом: обычный режим предлагает радиусы 7, 14 и 20; расширенный ползунок меняет радиус от 30 слева до 1 справа."),
            wraplength=1150, justify="left",
        ).pack(anchor="w", pady=(4, 10))

        controls = ttk.LabelFrame(outer, text="Настройки серии", padding=8)
        controls.pack(fill="x", pady=(0, 8))
        row = ttk.Frame(controls)
        row.pack(fill="x")
        ttk.Label(row, text="Радиус кисти (1–30)").pack(side="left")
        ttk.Entry(row, textvariable=self.brush_var, width=6).pack(side="left", padx=(6, 16))
        ttk.Label(row, text="Тест").pack(side="left")
        ttk.Combobox(row, textvariable=self.case_var, values=tuple(TEST_CASES), state="readonly", width=30).pack(side="left", padx=6)
        ttk.Label(controls, textvariable=self.area_var, wraplength=1100).pack(anchor="w", pady=(8, 0))
        slider = ttk.LabelFrame(controls, text="Автоматическая установка кисти", padding=6)
        slider.pack(fill="x", pady=(8, 0))
        ttk.Label(slider, text="Левый край 30 (X,Y)").pack(side="left")
        ttk.Entry(slider, textvariable=self.slider_start_var, width=12).pack(side="left", padx=4)
        ttk.Label(slider, text="Правый край 1 (X,Y)").pack(side="left", padx=(8, 0))
        ttk.Entry(slider, textvariable=self.slider_end_var, width=12).pack(side="left", padx=4)
        ttk.Button(slider, text="Установить кисть", command=self.set_brush_size).pack(side="left", padx=6)
        ttk.Label(slider, text="Координаты расширенного ползунка: слева радиус 30, справа радиус 1. После перетаскивания проверь значение в игре.", wraplength=350).pack(side="left", padx=6)
        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(0, 8))
        ttk.Button(actions, text="Создать и передать тест в исполнитель →", command=self.create_and_transfer_plan).pack(side="left")
        ttk.Button(actions, text="Снять скриншот сейчас", command=self.capture_screenshot).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Сохранить эталон пустой доски…", command=self.capture_blank_board_reference).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Привязать отчёт исполнения…", command=self.load_execution_report).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Привязать Game Monitor JSON…", command=self.load_game_monitor_report).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Эксперимент: снимок ДО", command=lambda: self.capture_experiment_phase("before_draw")).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Эксперимент: ПОСЛЕ рисования", command=lambda: self.capture_experiment_phase("after_draw")).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Очистить и снять ПОСЛЕ", command=lambda: self.capture_experiment_phase("after_clear")).pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Сохранить запись теста…", command=self.save_record_dialog).pack(side="left", padx=(6, 0))

        details = ttk.LabelFrame(outer, text="Шаблон и фиксация результата", padding=8)
        details.pack(fill="both", expand=True)
        self.template_text = tk.Text(details, height=13, wrap="word")
        self.template_text.pack(fill="both", expand=True)
        self.template_text.configure(state="disabled")
        self.case_var.trace_add("write", lambda *_: self._refresh_template())
        self._refresh_template()
        result = ttk.Frame(details)
        result.pack(fill="x", pady=(8, 0))
        ttk.Label(result, text="Наблюдение").pack(side="left")
        ttk.Combobox(
            result, textvariable=self.outcome_var, state="readonly", width=22,
            values=("not_reviewed", "all_visible", "partial", "none_visible", "distorted"),
        ).pack(side="left", padx=(6, 14))
        ttk.Label(result, text="Заметки").pack(side="left")
        ttk.Entry(result, textvariable=self.notes_var).pack(side="left", fill="x", expand=True, padx=6)
        measurements = ttk.LabelFrame(details, text="Измерения для будущей модели", padding=6)
        measurements.pack(fill="x", pady=(8, 0))
        measure_row1 = ttk.Frame(measurements)
        measure_row1.pack(fill="x")
        for label, variable, width in (
            ("Видимые штрихи", self.visible_strokes_var, 24),
            ("Пропущенные", self.missing_strokes_var, 20),
            ("Ширина следа, px", self.footprint_width_var, 7),
            ("Высота, px", self.footprint_height_var, 7),
        ):
            ttk.Label(measure_row1, text=label).pack(side="left", padx=(0, 3))
            ttk.Entry(measure_row1, textvariable=variable, width=width).pack(side="left", padx=(0, 10))
        measure_row2 = ttk.Frame(measurements)
        measure_row2.pack(fill="x", pady=(6, 0))
        for label, variable in (
            ("Краска до", self.paint_before_var),
            ("Краска после", self.paint_after_var),
            ("Масштаб браузера, %", self.zoom_var),
        ):
            ttk.Label(measure_row2, text=label).pack(side="left", padx=(0, 3))
            ttk.Entry(measure_row2, textvariable=variable, width=9).pack(side="left", padx=(0, 12))
        ttk.Label(
            measurements,
            text="Видимые/пропущенные штрихи указывай через запятую по именам из шаблона. Числовые поля можно оставить пустыми.",
            wraplength=1100,
        ).pack(anchor="w", pady=(5, 0))
        ttk.Label(outer, textvariable=self.status_var, wraplength=1150).pack(anchor="w", pady=(8, 0))

    def _load_brush_control_into_fields(self) -> None:
        """Populate visible brush coordinates from the saved calibration profile."""
        try:
            calibrated = self.get_brush_control() if callable(self.get_brush_control) else None
            if not calibrated or calibrated.get("mode") in ("unsaved", "unselected"):
                return
            if calibrated.get("mode") == "slider" and calibrated.get("start") and calibrated.get("end"):
                start = self._parse_point(
                    f"{calibrated['start'][0]},{calibrated['start'][1]}", "Край 30 из профиля"
                )
                end = self._parse_point(
                    f"{calibrated['end'][0]},{calibrated['end'][1]}", "Край 1 из профиля"
                )
                self.slider_start_var.set(f"{start[0]}, {start[1]}")
                self.slider_end_var.set(f"{end[0]}, {end[1]}")
                self.status_var.set("Координаты кисти загружены из сохранённого профиля калибровки.")
            elif calibrated.get("mode") == "presets":
                self.status_var.set("Координаты пресетов кисти загружаются из сохранённого профиля.")
        except (ValueError, TypeError, AttributeError):
            self.status_var.set("Не удалось автоматически загрузить координаты кисти; проверь профиль калибровки.")

    def _refresh_template(self) -> None:
        scenario = TEST_CASES.get(self.case_var.get())
        if not scenario:
            return
        lines = [scenario["description"], "", "Координаты тестового шаблона (логическая доска игры 460×240; при передаче будет преобразована в экранный ROI):"]
        for stroke in scenario["strokes"]:
            points = stroke["points"]
            route = " → ".join(f"({point[0]}, {point[1]})" for point in points)
            lines.append(f"• {stroke['name']}: {route}")
        lines.extend(["", "Рекомендации:", "1. Каждый элемент списка — отдельный штрих; точки внутри него образуют один непрерывный маршрут.",
                      "2. Не меняй масштаб браузера и размер кисти в середине серии.",
                      "3. Запиши размер кисти, видимые/пропущенные штрихи и остаток краски в заметках или заполни measurement_fields в JSON.",
                      "4. Снимок должен включать всю тестовую область и не закрывать её окнами приложения."])
        self.template_text.configure(state="normal")
        self.template_text.delete("1.0", "end")
        self.template_text.insert("1.0", "\n".join(lines))
        self.template_text.configure(state="disabled")

    def _validate_automation_preflight(self) -> bool:
        """Block automatic brush actions unless saved calibration matches this screen."""
        config = self.get_calibration_profile() if callable(self.get_calibration_profile) else None
        brush_control = self.get_brush_control() if callable(self.get_brush_control) else None
        try:
            screen = ImageGrab.grab()
            result = validate_brush_test_preflight(
                config,
                (int(screen.width), int(screen.height)),
                brush_control=brush_control,
            )
        except Exception as exc:
            messagebox.showerror(
                "Не удалось проверить калибровку",
                f"Автоматический тест не запущен. До любых действий мышью произошла ошибка проверки: {exc}",
                parent=self.root,
            )
            self.status_var.set(f"Предварительная проверка калибровки завершилась ошибкой: {exc}")
            return False
        if not result["valid"]:
            details = "\n".join(f"• {error}" for error in result["errors"])
            messagebox.showwarning(
                "Калибровка не готова",
                "План не будет передан и кисть не будет перемещена. Исправь профиль на вкладке 8:\n\n" + details,
                parent=self.root,
            )
            self.status_var.set("Автоматический тест заблокирован: профиль калибровки требует исправления.")
            return False
        return True

    def create_and_transfer_plan(self) -> None:
        if not self._validate_automation_preflight():
            return
        canvas_size = self.get_canvas_size()
        if not canvas_size:
            messagebox.showwarning(
                "Не выбрана область холста",
                "Сначала выбери реальную область рисования на вкладке исполнения. "
                "Тестовый план должен совпадать с её размером.",
                parent=self.root,
            )
            return
        try:
            plan = build_brush_test_drawing_plan(
                self.case_var.get(), canvas_size, coordinate_system="logical_board_pixels"
            )
            area = self.get_canvas_area()
            self.canvas_area = dict(area) if area else None
            brush = int(self.brush_var.get().strip())
            if not 1 <= brush <= 30:
                raise ValueError("Размер кисти должен быть целым числом от 1 до 30.")
            self.output_dir.mkdir(parents=True, exist_ok=True)
            path = self.output_dir / (
                f"brush-plan-{plan['generation']['test_case']}-b{brush}-"
                f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
            )
            plan["generation"]["requested_brush_value"] = brush
            path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
            self.current_plan = plan
            self.current_plan_path = path
            if not self.on_transfer_plan(plan, path):
                return
            self._reset_observation_fields()
            self._start_automated_preclear()
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror("Не удалось создать тестовый план", str(exc), parent=self.root)

    def _reset_observation_fields(self) -> None:
        """Prevent evidence from a previous run being attached to a new test plan."""
        self._experiment_requested_brush = int(self.brush_var.get().strip())
        self.screenshot_path = None
        self.experiment_dir = None
        self.experiment_phases = {}
        self.execution_report_path = None
        self.execution_report = None
        self.game_monitor_report_path = None
        self.game_monitor_summary = None
        if self._bridge_capture_poll_id is not None:
            try:
                self.root.after_cancel(self._bridge_capture_poll_id)
            except (tk.TclError, ValueError):
                pass
            self._bridge_capture_poll_id = None
        self.brush_slider_start = None
        self.brush_slider_end = None
        self.outcome_var.set("not_reviewed")
        self.notes_var.set("")
        self.visible_strokes_var.set("")
        self.missing_strokes_var.set("")
        self.footprint_width_var.set("")
        self.footprint_height_var.set("")
        self.paint_before_var.set("")
        self.paint_after_var.set("")
        self.zoom_var.set("100")

    def select_screenshot_area(self) -> None:
        def selected(area) -> None:
            if area is None:
                self.status_var.set("Выбор области снимка отменён.")
                return
            self.screen_area = {"x": int(area.x), "y": int(area.y), "width": int(area.width), "height": int(area.height)}
            self.area_var.set(f"Область снимка: X={area.x}, Y={area.y}, {area.width} × {area.height} px.")
            self.status_var.set("Область сохранена. После завершения теста нажми «Снять скриншот сейчас».")
        self.area_selector_cls(self.root, selected, instruction="Выдели область завершённого теста кисти. Esc — отмена.")

    @staticmethod
    def _parse_point(raw: str, field: str) -> tuple[int, int]:
        parts = [part.strip() for part in raw.replace(";", ",").split(",")]
        if len(parts) != 2:
            raise ValueError(f"{field}: введи координаты X,Y.")
        try:
            return int(parts[0]), int(parts[1])
        except ValueError as exc:
            raise ValueError(f"{field}: X и Y должны быть целыми числами.") from exc

    def set_brush_size(self) -> bool:
        """Set brush size only by dragging the calibrated extended-mode slider."""
        try:
            brush = int(self.brush_var.get().strip())
            if not 1 <= brush <= 30:
                raise ValueError("Размер кисти должен быть целым числом от 1 до 30.")
            if platform.system() != "Windows":
                raise RuntimeError("Автоматическая установка кисти доступна только в Windows.")
            calibrated = self.get_brush_control() if callable(self.get_brush_control) else None
            if calibrated:
                mode = calibrated.get("mode")
                if mode == "unsaved":
                    raise ValueError("Сначала сохрани профиль калибровки на вкладке 8.")
                if mode == "presets":
                    raise ValueError(
                        "Этот режим использует щелчки по пресетам. Для установки размера перетаскиванием "
                        "переключи профиль калибровки на «Расширенный ползунок 1–30», отметь оба конца "
                        "ползунка и сохрани профиль."
                    )
                if mode == "slider":
                    if not calibrated.get("start") or not calibrated.get("end"):
                        raise ValueError("Для режима ползунка задай и сохрани положения кисти 1 и 30 на вкладке 8.")
                    # The engine slider runs from brush 30 at the left endpoint to brush 1 at the right.
                    start = self._parse_point(
                        f"{calibrated['start'][0]},{calibrated['start'][1]}", "Край 30 из профиля"
                    )
                    end = self._parse_point(
                        f"{calibrated['end'][0]},{calibrated['end'][1]}", "Край 1 из профиля"
                    )
                    self.slider_start_var.set(f"{start[0]}, {start[1]}")
                    self.slider_end_var.set(f"{end[0]}, {end[1]}")
                else:
                    raise ValueError("Выбери режим управления кистью на вкладке 8 и сохрани профиль.")
            else:
                start = self._parse_point(self.slider_start_var.get(), "Край 30")
                end = self._parse_point(self.slider_end_var.get(), "Край 1")
            x, y = calculate_slider_target(start, end, brush)
            self.brush_slider_start, self.brush_slider_end = start, end
            self.status_var.set(
                f"Через 3 секунды ползунок будет перетащен к радиусу кисти {brush}. "
                "Переключись в браузер и не трогай мышь."
            )
            # Minimize AutoDraw before the countdown so it cannot cover the game slider.
            self.root.iconify()
            self._start_brush_hotkey_listener()
            self._brush_drag_countdown_id = self.root.after(
                3000, lambda: self._start_scheduled_brush_drag(start, x, y, brush)
            )
            return True
        except (ValueError, RuntimeError, AttributeError) as exc:
            if self._brush_drag_countdown_id is not None:
                try:
                    self.root.after_cancel(self._brush_drag_countdown_id)
                except (tk.TclError, ValueError):
                    pass
                self._brush_drag_countdown_id = None
            self._stop_brush_hotkey_listener()
            try:
                self.root.deiconify()
                self.root.lift()
            except tk.TclError:
                pass
            messagebox.showwarning("Не настроен ползунок кисти", str(exc), parent=self.root)
            return False

    def _apply_brush_preset_click(self, x: int, y: int, brush: int) -> None:
        """Select one of the ordinary game brush presets at its calibrated screen point."""
        try:
            pyautogui.click(x, y)
        except Exception as exc:
            self.status_var.set(f"Не удалось выбрать пресет кисти {brush}: {exc}")
            return
        self.status_var.set(
            f"Выполнен клик по пресету кисти {brush} ({x}, {y}). Проверь, что игра выбрала нужный размер."
        )

    def _start_brush_hotkey_listener(self) -> None:
        """Listen for a global Alt key during the minimized-window countdown and drag."""
        self._stop_brush_hotkey_listener()

        def on_press(key):
            if key in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r):
                try:
                    if self._automated_preclear_active:
                        self.root.after(0, self._cancel_automated_preclear)
                    elif self._automated_postdraw_active:
                        self._automated_postdraw_stop_requested = True
                        self.root.after(0, self._cancel_automated_postdraw)
                    else:
                        self.root.after(0, self.cancel_brush_drag)
                except (tk.TclError, RuntimeError):
                    pass

        listener = keyboard.Listener(on_press=on_press)
        listener.daemon = True
        listener.start()
        self._brush_hotkey_listener = listener

    def _stop_brush_hotkey_listener(self) -> None:
        listener = self._brush_hotkey_listener
        self._brush_hotkey_listener = None
        if listener is not None:
            try:
                listener.stop()
            except Exception:
                pass

    def _start_scheduled_brush_drag(
        self, start: tuple[int, int], target_x: int, target_y: int, brush: int
    ) -> None:
        self._brush_drag_countdown_id = None
        if self._brush_hotkey_listener is None:
            return
        self._begin_brush_drag(start, target_x, target_y, brush)

    def _begin_brush_drag(
        self, start: tuple[int, int], target_x: int, target_y: int, brush: int
    ) -> None:
        """Start a cancellable slider drag without blocking Tk's event loop."""
        if self._brush_drag_state is not None:
            self.status_var.set("Перетаскивание кисти уже выполняется; повторный запуск заблокирован.")
            return
        try:
            user32 = ctypes.windll.user32
            start_x, start_y = start
            distance = max(abs(target_x - start_x), abs(target_y - start_y))
            self._brush_drag_state = {
                "start": (start_x, start_y),
                "target": (target_x, target_y),
                "brush": brush,
                "step": 0,
                "steps": max(10, min(100, distance)),
                "user32": user32,
                "purpose": self._brush_drag_purpose,
            }
            self._brush_drag_purpose = "set_brush_size"
            user32.SetCursorPos(start_x, start_y)
            self.root.after(150, self._press_and_continue_brush_drag)
        except Exception as exc:
            self._finish_brush_drag(error=f"Не удалось начать перетаскивание: {exc}")

    def _press_and_continue_brush_drag(self) -> None:
        state = self._brush_drag_state
        if state is None:
            return
        try:
            if state.get("cancel_requested"):
                self._finish_brush_drag(cancelled=True)
                return
            state["user32"].mouse_event(0x0002, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTDOWN
            self._brush_drag_mouse_down = True
            self._move_brush_drag_step()
        except Exception as exc:
            self._finish_brush_drag(error=f"Ошибка при нажатии на ползунок: {exc}")

    def _move_brush_drag_step(self) -> None:
        state = self._brush_drag_state
        if state is None:
            return
        try:
            if state.get("cancel_requested"):
                self._finish_brush_drag(cancelled=True)
                return
            step = int(state["step"]) + 1
            steps = int(state["steps"])
            start_x, start_y = state["start"]
            target_x, target_y = state["target"]
            ratio = min(1.0, step / steps)
            current_x = round(start_x + (target_x - start_x) * ratio)
            current_y = round(start_y + (target_y - start_y) * ratio)
            state["user32"].SetCursorPos(current_x, current_y)
            state["step"] = step
            if step >= steps:
                self._finish_brush_drag()
            else:
                self._brush_drag_after_id = self.root.after(10, self._move_brush_drag_step)
        except Exception as exc:
            self._finish_brush_drag(error=f"Ошибка перемещения ползунка: {exc}")

    def _on_brush_workflow_stop_key(self, _event=None) -> str | None:
        """Alt cancels a pending/active brush drag; otherwise let the executor handle it."""
        if self._brush_drag_state is not None or self._brush_drag_countdown_id is not None:
            self.cancel_brush_drag()
            return "break"
        return None

    def cancel_brush_drag(self) -> None:
        """Cancel the countdown or active drag and release the mouse if it is held."""
        if self._brush_drag_countdown_id is not None:
            purpose = self._brush_drag_purpose
            try:
                self.root.after_cancel(self._brush_drag_countdown_id)
            except (tk.TclError, ValueError):
                pass
            self._brush_drag_countdown_id = None
            self._stop_brush_hotkey_listener()
            self.status_var.set("Установка кисти отменена по Alt до начала перетаскивания.")
            self._brush_drag_purpose = "set_brush_size"
            if purpose == "restore_brush_30":
                self._record_brush_restore_result("stopped", "Alt отменил возврат кисти до начала перетаскивания.")
                return
            try:
                self.root.deiconify()
                self.root.lift()
            except tk.TclError:
                pass
            return
        if self._brush_drag_state is not None:
            self._finish_brush_drag(cancelled=True)

    def _finish_brush_drag(self, *, cancelled: bool = False, error: str | None = None) -> None:
        state = self._brush_drag_state
        self._stop_brush_hotkey_listener()
        if self._brush_drag_after_id is not None:
            try:
                self.root.after_cancel(self._brush_drag_after_id)
            except (tk.TclError, ValueError):
                pass
            self._brush_drag_after_id = None
        release_error = None
        if self._brush_drag_mouse_down:
            try:
                user32 = state.get("user32") if state else ctypes.windll.user32
                user32.mouse_event(0x0004, 0, 0, 0, 0)  # MOUSEEVENTF_LEFTUP
            except Exception as exc:
                release_error = str(exc)
            finally:
                self._brush_drag_mouse_down = False
        self._brush_drag_state = None
        purpose = state.get("purpose", "set_brush_size") if state else self._brush_drag_purpose
        if purpose == "restore_brush_30":
            self._start_executor_after_brush_drag = False
            if cancelled or error or release_error:
                restore_status = "stopped" if cancelled else "failed"
                detail = "Alt отменил возврат кисти." if cancelled else (error or release_error or "Неизвестная ошибка.")
            else:
                restore_status = "drag_completed_unverified"
                detail = "Жест перетаскивания к позиции кисти 30 завершён; значение необходимо проверить в игре."
            self._record_brush_restore_result(restore_status, detail, state=state)
            return
        if cancelled or error or release_error:
            self._start_executor_after_brush_drag = False
        if release_error:
            self.status_var.set(f"КРИТИЧЕСКАЯ ОШИБКА: не удалось подтвердить отпускание кнопки мыши: {release_error}")
        elif error:
            self.status_var.set(error)
        elif cancelled:
            self.status_var.set("Перетаскивание кисти остановлено по Alt; проверь положение ползунка вручную.")
        elif state:
            target_x, target_y = state["target"]
            brush = state["brush"]
            self.status_var.set(
                f"Перетаскивание к радиусу кисти {brush} завершено ({target_x}, {target_y}). "
                "Размер не подтверждён игрой — проверь значение перед рисованием."
            )
            if self._start_executor_after_brush_drag:
                self._start_executor_after_brush_drag = False
                self._confirm_brush_before_test(brush, state)
        if cancelled or error or release_error:
            try:
                self.root.deiconify()
                self.root.lift()
            except tk.TclError:
                pass

    def _confirm_brush_before_test(self, brush: int, state: dict[str, Any]) -> None:
        """Require visual confirmation before using a requested brush size in a measurement."""
        start = state.get("start")
        target = state.get("target")
        phase = {
            "status": "awaiting_user_confirmation",
            "requested_value": int(brush),
            "drag_start": list(start) if isinstance(start, (tuple, list)) else None,
            "drag_target": list(target) if isinstance(target, (tuple, list)) else None,
            "drag_completed_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "confirmation_required": True,
            "note": (
                "A completed mouse drag does not prove the game selected the requested brush size. "
                "The user must visually check the slider position before the test executor can start."
            ),
        }
        self.experiment_phases["brush_setup"] = phase
        if self.experiment_dir is not None:
            try:
                self._write_experiment_manifest()
            except (OSError, ValueError, TypeError) as exc:
                phase["status"] = "manifest_write_failed"
                phase["error"] = str(exc)
                self.status_var.set(
                    "Размер кисти не подтверждён; не удалось сохранить запись. Исполнитель не запущен."
                )
                return

        try:
            self.root.deiconify()
            self.root.lift()
        except tk.TclError:
            pass

        try:
            monitor_radius_text = simpledialog.askstring(
                "Проверка фактической кисти",
                (
                    "До начала рисования проверь внутреннее значение игры.\n\n"
                    "1. Переключись в игровой iframe и выполни в консоли:\n"
                    "   AutoDrawGameMonitor.status().snapshot.radius\n"
                    "2. Вставь сюда полученное значение целиком (например, 14 или [14]).\n\n"
                    f"Запрошенный радиус AutoDraw: {brush}. "
                    "Пустой ответ или несовпадение отменит тест."
                ),
                parent=self.root,
            )
            verification = validate_observed_brush_radius(brush, monitor_radius_text)
            phase["monitor_preflight"] = {
                **verification,
                "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "source": "user_transcribed_AutoDrawGameMonitor.status_snapshot_radius",
            }
            if not verification["valid"]:
                phase["status"] = "brush_mismatch" if verification["status"] in {"mismatch", "mixed"} else "brush_unverified"
                phase["observed_radii"] = verification["observed_radii"]
                phase["confirmation_method"] = "game_monitor_pre_draw_snapshot"
                if self.experiment_dir is not None:
                    try:
                        self._write_experiment_manifest()
                    except (OSError, ValueError, TypeError) as exc:
                        phase["manifest_write_error"] = str(exc)
                self.status_var.set(
                    f"Тест отменён: запрошено {brush}, фактическое значение не подтверждено "
                    f"(Monitor: {verification['observed_radii'] or 'нет данных'})."
                )
                messagebox.showwarning(
                    "Проверка кисти не пройдена",
                    "Исполнитель не запущен. Проверь ползунок и повтори установку кисти.",
                    parent=self.root,
                )
                return
            phase["monitor_preflight"]["status"] = "match"
            if self.experiment_dir is not None:
                self._write_experiment_manifest()
            confirmed = messagebox.askyesno(
                "Подтвердить положение кисти",
                (
                    f"Game Monitor подтвердил внутренний радиус {brush}.\n"
                    f"Целевая координата ползунка: {target}.\n\n"
                    "Теперь визуально проверь положение ползунка. Продолжать тест?"
                ),
                icon="question",
                parent=self.root,
            )
        except Exception as exc:
            phase["status"] = "confirmation_dialog_failed"
            phase["error"] = str(exc)
            if self.experiment_dir is not None:
                try:
                    self._write_experiment_manifest()
                except (OSError, ValueError, TypeError):
                    pass
            self.status_var.set("Не удалось запросить подтверждение кисти. Исполнитель не запущен.")
            return

        if not confirmed:
            phase["status"] = "declined_by_user"
            phase["declined_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            if self.experiment_dir is not None:
                try:
                    self._write_experiment_manifest()
                except (OSError, ValueError, TypeError) as exc:
                    phase["manifest_write_error"] = str(exc)
            self.status_var.set(
                "Размер кисти не подтверждён; тестовое рисование отменено. "
                "Проверь ползунок и повтори установку при необходимости."
            )
            return

        phase["status"] = "confirmed_by_user"
        phase["confirmed_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        phase["confirmation_method"] = "explicit_user_visual_confirmation"
        if self.experiment_dir is not None:
            try:
                self._write_experiment_manifest()
            except (OSError, ValueError, TypeError) as exc:
                phase["status"] = "manifest_write_failed_after_confirmation"
                phase["manifest_write_error"] = str(exc)
                self.status_var.set(
                    "Подтверждение получено, но не удалось записать манифест. Исполнитель не запущен."
                )
                return
        if callable(self.on_brush_ready):
            self.status_var.set(f"Размер {brush} подтверждён; запуск тестового исполнения.")
            self.root.after(0, lambda: self.on_brush_ready(brush))
        else:
            phase["status"] = "executor_callback_missing"
            self.status_var.set("Кисть подтверждена, но callback запуска исполнителя не подключён.")

    def capture_screenshot(self) -> None:
        self.status_var.set("Через 3 секунды будет сохранён полный скриншот экрана. Переключись в браузер.")
        self.root.after(3000, self._capture_screenshot_now)

    def _capture_screenshot_now(self) -> None:
        try:
            image = ImageGrab.grab()
            if image.width < 1 or image.height < 1:
                raise ValueError("Получился пустой снимок.")
            self.screen_resolution = {"width": int(image.width), "height": int(image.height)}
            area = self.get_canvas_area()
            self.canvas_area = ({key: int(area[key]) for key in ("x", "y", "width", "height")} if area else None)
            self.screen_area = {"x": 0, "y": 0, "width": image.width, "height": image.height}
            self.output_dir.mkdir(parents=True, exist_ok=True)
            path = self.output_dir / f"brush-screenshot-full-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
            image.save(path)
            self.screenshot_path = path
            self.area_var.set(f"Экран: {image.width} × {image.height}; доска: {self.canvas_area or 'не найдена в профиле'}")
            self.status_var.set(f"Полный скриншот сохранён: {path}")
        except Exception as exc:
            messagebox.showerror("Не удалось снять скриншот", str(exc), parent=self.root)

    def _start_automated_preclear(self) -> None:
        """Clear the board and verify it against the explicit blank reference before brush setup."""
        config = self.get_calibration_profile() if callable(self.get_calibration_profile) else None
        if not isinstance(config, dict):
            self.status_var.set("Тест остановлен до очистки: профиль калибровки недоступен.")
            messagebox.showwarning("Нет профиля", "Автоматическая подготовка не запущена.", parent=self.root)
            return
        reference_path, metadata_path = self._blank_board_reference_paths()
        if not reference_path.is_file() or not metadata_path.is_file():
            self.status_var.set("Тест заблокирован: сначала сохрани отдельный эталон пустой доски.")
            messagebox.showwarning(
                "Нет эталона пустой доски",
                "Перед автоматическим тестом нажми «Сохранить эталон пустой доски…» и подтверди, что доска пуста.",
                parent=self.root,
            )
            return
        points = config.get("points")
        points = points if isinstance(points, dict) else {}
        statuses = config.get("status")
        statuses = statuses if isinstance(statuses, dict) else {}
        clear_point = points.get("clear_board", {})
        point_status = statuses.get("points", {})
        point_status = point_status if isinstance(point_status, dict) else {}
        if not isinstance(clear_point, dict) or point_status.get("clear_board") == "needs_review":
            self.status_var.set("Тест заблокирован: координата Clear требует проверки.")
            messagebox.showwarning("Clear не откалиброван", "Проверь точку Clear на вкладке 8.", parent=self.root)
            return
        if not messagebox.askyesno(
            "Подтвердить очистку перед тестом",
            "AutoDraw нажмёт Clear и удалит текущий рисунок. Продолжать только на тестовой доске, "
            "где рисунок можно удалить. Если очистка не подтвердится эталоном, тест не начнётся.",
            icon="warning",
            parent=self.root,
        ):
            self.status_var.set("Автоматический тест отменён до очистки.")
            return
        brush = int(self.brush_var.get().strip())
        scenario = TEST_CASES.get(self.case_var.get(), {}).get("id", "unknown")
        if self.experiment_dir is None:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            self.experiment_dir = self.output_dir / f"experiment-{stamp}-b{brush}-{scenario}"
            self.experiment_dir.mkdir(parents=True, exist_ok=False)
        self.experiment_phases = {}
        self._automated_preclear_active = True
        self.status_var.set("Через 3 секунды будет выполнен Clear и проверка пустой доски. Alt отменяет подготовку.")
        self.root.iconify()
        self._start_brush_hotkey_listener()
        self._automated_preclear_after_id = self.root.after(
            3000, lambda: self._perform_automated_preclear(config, clear_point)
        )

    def _cancel_automated_preclear(self) -> None:
        if not self._automated_preclear_active:
            return
        self._automated_preclear_active = False
        if self._automated_preclear_after_id is not None:
            try:
                self.root.after_cancel(self._automated_preclear_after_id)
            except (tk.TclError, ValueError):
                pass
            self._automated_preclear_after_id = None
        self._stop_brush_hotkey_listener()
        if self.experiment_dir is not None:
            self.experiment_phases["before_clear"] = {
                "status": "stopped",
                "reason": "Alt",
                "captured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            try:
                self._write_experiment_manifest()
            except (OSError, ValueError, TypeError) as exc:
                self.status_var.set(f"Подготовка остановлена; не удалось записать манифест: {exc}")
        self.status_var.set("Подготовка теста отменена по Alt. Рисование не запускалось; проверь доску вручную.")
        try:
            self.root.deiconify()
            self.root.lift()
        except tk.TclError:
            pass

    def _perform_automated_preclear(self, config: dict[str, Any], clear_point: dict[str, int]) -> None:
        if not self._automated_preclear_active:
            return
        self._automated_preclear_after_id = None
        try:
            reference_path, metadata_path = self._blank_board_reference_paths()
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            screen = ImageGrab.grab()
            expected = config.get("screen_size", {})
            if isinstance(expected, dict):
                ew, eh = expected.get("width"), expected.get("height")
                if ew is not None and eh is not None and (int(ew), int(eh)) != screen.size:
                    raise ValueError("Разрешение экрана изменилось после калибровки.")
            region = config.get("regions", {}).get("board_area", {})
            current_region = {key: int(region[key]) for key in ("x", "y", "width", "height")}
            if (
                metadata.get("reference_type") != "user_confirmed_blank_board_roi"
                or metadata.get("user_confirmed_blank") is not True
                or metadata.get("screen_size") != {"width": screen.width, "height": screen.height}
                or metadata.get("board_region") != current_region
                or metadata.get("image_file") != reference_path.name
            ):
                raise ValueError("Эталон пустой доски не соответствует текущему разрешению/ROI.")
            with Image.open(reference_path) as reference:
                if reference.size != (current_region["width"], current_region["height"]):
                    raise ValueError("Размер эталона не совпадает с ROI доски.")
            pyautogui.click(int(clear_point["x"]), int(clear_point["y"]))
            self.status_var.set("Clear нажат; через 1,5 секунды будет проверена доска.")
            self._automated_preclear_after_id = self.root.after(
                1500, lambda: self._capture_and_verify_preclear(config, metadata, reference_path)
            )
        except Exception as exc:
            self._finish_automated_preclear_failure("preclear_failed", str(exc))

    def _capture_and_verify_preclear(self, config: dict[str, Any], metadata: dict[str, Any], reference_path: Path) -> None:
        if not self._automated_preclear_active:
            return
        self._automated_preclear_after_id = None
        try:
            screen = ImageGrab.grab()
            expected = config.get("screen_size", {})
            if isinstance(expected, dict):
                ew, eh = expected.get("width"), expected.get("height")
                if ew is not None and eh is not None and (int(ew), int(eh)) != screen.size:
                    raise ValueError("Разрешение экрана изменилось во время подготовки.")
            crops = crop_calibrated_regions(screen, config.get("regions", {}))
            with Image.open(reference_path) as reference:
                clear_check = evaluate_board_clear(reference.copy(), crops["board_area"])
            phase_dir = self.experiment_dir
            if phase_dir is None:
                raise ValueError("Каталог опыта отсутствует.")
            screen_path = phase_dir / "before_clear-screen.png"
            board_path = phase_dir / "before_clear-board.png"
            meter_path = phase_dir / "before_clear-paint-meter.png"
            screen.save(screen_path)
            crops["board_area"].save(board_path)
            crops["paint_meter_area"].save(meter_path)
            self.experiment_phases["before_clear"] = {
                "status": clear_check["status"],
                "board_clear_check": clear_check,
                "captured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "screen_size": {"width": screen.width, "height": screen.height},
                "files": {
                    "full_screen": screen_path.name,
                    "board_roi": board_path.name,
                    "paint_meter_roi": meter_path.name,
                },
            }
            if clear_check["status"] not in {"restored", "restored_within_pixel_tolerance"}:
                self._write_experiment_manifest()
                self._finish_automated_preclear_failure(
                    "board_clear_not_confirmed",
                    f"Очистка не подтверждена эталоном (статус: {clear_check['status']}). Рисование не запускалось.",
                    write_manifest=False,
                )
                return
            self.experiment_phases["before_draw"] = {
                "captured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "screen_size": {"width": screen.width, "height": screen.height},
                "clear_check": clear_check,
                "files": {
                    "full_screen": screen_path.name,
                    "board_roi": board_path.name,
                    "paint_meter_roi": meter_path.name,
                },
            }
            self._write_experiment_manifest()
            self._automated_preclear_active = False
            self._stop_brush_hotkey_listener()
            self.root.deiconify()
            self.root.lift()
            self._start_executor_after_brush_drag = True
            if not self.set_brush_size():
                self._start_executor_after_brush_drag = False
                self.status_var.set("Доска очищена и проверена, но кисть не установлена. Исполнитель не запущен.")
                self._write_experiment_manifest()
                return
            self.status_var.set("Доска очищена и проверена; начата установка кисти. После перетаскивания подтверди радиус в игре.")
        except Exception as exc:
            self._finish_automated_preclear_failure("preclear_capture_failed", str(exc))

    def _finish_automated_preclear_failure(self, status: str, reason: str, *, write_manifest: bool = True) -> None:
        self._automated_preclear_active = False
        if self._automated_preclear_after_id is not None:
            try:
                self.root.after_cancel(self._automated_preclear_after_id)
            except (tk.TclError, ValueError):
                pass
            self._automated_preclear_after_id = None
        self._stop_brush_hotkey_listener()
        if self.experiment_dir is not None:
            self.experiment_phases.setdefault("before_clear", {})
            self.experiment_phases["before_clear"].update({
                "status": status,
                "reason": reason,
                "captured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            })
            if write_manifest:
                try:
                    self._write_experiment_manifest()
                except (OSError, ValueError, TypeError) as exc:
                    reason += f"; ошибка сохранения манифеста: {exc}"
        self.status_var.set(f"Тест остановлен до рисования: {reason}")
        try:
            self.root.deiconify()
            self.root.lift()
        except tk.TclError:
            pass
        messagebox.showwarning("Автоматический тест остановлен", reason, parent=self.root)

    def _blank_board_reference_paths(self) -> tuple[Path, Path]:
        return (
            self.output_dir / "blank-board-reference.png",
            self.output_dir / "blank-board-reference.json",
        )

    def capture_blank_board_reference(self) -> None:
        """Capture an explicitly user-confirmed blank-board ROI for later Clear checks."""
        config = self.get_calibration_profile() if callable(self.get_calibration_profile) else None
        if not isinstance(config, dict):
            messagebox.showwarning(
                "Профиль калибровки недоступен",
                "Сначала сохрани и проверь профиль калибровки на вкладке 8.",
                parent=self.root,
            )
            return
        regions = config.get("regions", {})
        statuses = config.get("status", {})
        region_status = statuses.get("regions", {}) if isinstance(statuses, dict) else {}
        board_region = regions.get("board_area") if isinstance(regions, dict) else None
        if not isinstance(board_region, dict) or region_status.get("board_area") == "needs_review":
            messagebox.showwarning(
                "Область доски требует проверки",
                "Проверь ROI игровой доски на вкладке 8 перед созданием эталона.",
                parent=self.root,
            )
            return
        if not messagebox.askyesno(
            "Эталон пустой доски",
            "Убедись, что игровая доска уже полностью пустая, затем переключись в браузер. "
            "Будет сохранён отдельный эталон ROI, который используется для проверки Clear. Продолжить?",
            icon="warning",
            parent=self.root,
        ):
            return
        self.status_var.set("Через 3 секунды будет снят эталон пустой доски. Переключись в браузер.")
        self.root.withdraw()
        self.root.after(3000, lambda: self._capture_blank_board_reference_now(config))

    def _capture_blank_board_reference_now(self, config: dict[str, Any]) -> None:
        try:
            screen = ImageGrab.grab()
            expected = config.get("screen_size", {})
            if isinstance(expected, dict):
                ew, eh = expected.get("width"), expected.get("height")
                if ew is not None and eh is not None and (int(ew), int(eh)) != screen.size:
                    raise ValueError(
                        f"Разрешение профиля {ew} × {eh} не совпадает со снимком "
                        f"{screen.width} × {screen.height}."
                    )
            crops = crop_calibrated_regions(screen, config.get("regions", {}))
            reference_path, metadata_path = self._blank_board_reference_paths()
            crops["board_area"].save(reference_path)
            region = config["regions"]["board_area"]
            metadata = {
                "schema_version": 1,
                "reference_type": "user_confirmed_blank_board_roi",
                "captured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "screen_size": {"width": screen.width, "height": screen.height},
                "board_region": {key: int(region[key]) for key in ("x", "y", "width", "height")},
                "calibration_profile_path": str(config.get("profile_path", "")) or None,
                "image_file": reference_path.name,
                "user_confirmed_blank": True,
                "limitations": "Visual reference only; does not prove the game's internal board state.",
            }
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.status_var.set(f"Эталон пустой доски сохранён: {reference_path}. Перед использованием проверь, что доска действительно пуста.")
        except Exception as exc:
            self.status_var.set(f"Не удалось сохранить эталон пустой доски: {exc}")
            messagebox.showerror("Не удалось сохранить эталон", str(exc), parent=self.root)
        finally:
            self.root.deiconify()
            self.root.lift()

    def capture_experiment_phase(self, phase: str) -> None:
        """Capture calibrated board/meter evidence for before, after-draw and after-clear phases."""
        labels = {
            "before_draw": "до рисования",
            "after_draw": "после рисования",
            "after_clear": "после очистки",
        }
        if phase not in labels:
            messagebox.showerror("Неизвестный этап", phase, parent=self.root)
            return
        if self.current_plan is None:
            messagebox.showwarning(
                "Нет тестового плана",
                "Сначала создай и передай тестовый план в исполнитель.",
                parent=self.root,
            )
            return
        if phase == "before_draw":
            self.experiment_dir = None
            self.experiment_phases = {}
        elif phase == "after_draw" and "before_draw" not in self.experiment_phases:
            messagebox.showwarning(
                "Нет исходного снимка",
                "Сначала сделай снимок ДО рисования, затем выполни тест и сними результат.",
                parent=self.root,
            )
            return
        elif phase == "after_clear" and "after_draw" not in self.experiment_phases:
            messagebox.showwarning(
                "Нет снимка после рисования",
                "Сначала сохрани снимок ПОСЛЕ рисования. Очистка доски необратима для текущего рисунка.",
                parent=self.root,
            )
            return

        config = self.get_calibration_profile() if callable(self.get_calibration_profile) else None
        if not isinstance(config, dict):
            messagebox.showwarning(
                "Профиль калибровки недоступен",
                "Сохрани профиль на вкладке 8 и проверь области доски, полоски краски и координату Clear.",
                parent=self.root,
            )
            return
        regions = config.get("regions", {})
        points = config.get("points", {})
        statuses = config.get("status", {})
        region_status = statuses.get("regions", {}) if isinstance(statuses, dict) else {}
        point_status = statuses.get("points", {}) if isinstance(statuses, dict) else {}
        for key in ("board_area", "paint_meter_area"):
            if not isinstance(regions.get(key), dict) or region_status.get(key) == "needs_review":
                messagebox.showwarning(
                    "Область требует калибровки",
                    f"Область {key} отсутствует или требует повторной проверки на вкладке 8.",
                    parent=self.root,
                )
                return
        clear_point = points.get("clear_board")
        if phase == "after_clear":
            if not isinstance(clear_point, dict) or point_status.get("clear_board") == "needs_review":
                messagebox.showwarning(
                    "Координата Clear недоступна",
                    "Проверь координату кнопки очистки на вкладке 8.",
                    parent=self.root,
                )
                return
            confirmed = messagebox.askyesno(
                "Очистить игровую доску?",
                "Сейчас AutoDraw нажмёт откалиброванную кнопку Clear и уничтожит текущий рисунок. "
                "Продолжать только если тестовый рисунок можно удалить.",
                icon="warning",
                parent=self.root,
            )
            if not confirmed:
                return

        if phase == "before_draw":
            brush = self.brush_var.get().strip() or "unknown"
            case = TEST_CASES.get(self.case_var.get(), {}).get("id", "unknown")
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            self.experiment_dir = self.output_dir / f"experiment-{stamp}-b{brush}-{case}"
            self.experiment_dir.mkdir(parents=True, exist_ok=False)
            self.experiment_phases = {}

        if self.experiment_dir is None:
            messagebox.showwarning(
                "Нет папки эксперимента",
                "Начни серию со снимка ДО рисования.",
                parent=self.root,
            )
            return
        self.status_var.set(
            f"Через 3 секунды будет сохранён снимок {labels[phase]}. Переключись в браузер."
        )
        self.root.withdraw()
        self.root.after(3000, lambda: self._capture_experiment_phase_now(phase, config, clear_point if phase == "after_clear" else None))

    def _capture_experiment_phase_now(
        self, phase: str, config: dict[str, Any], clear_point: dict[str, int] | None,
    ) -> None:
        try:
            if clear_point is not None:
                pyautogui.click(int(clear_point["x"]), int(clear_point["y"]))
                time.sleep(1.5)
            screen = ImageGrab.grab()
            expected_size = config.get("screen_size", {})
            expected_width = expected_size.get("width") if isinstance(expected_size, dict) else None
            expected_height = expected_size.get("height") if isinstance(expected_size, dict) else None
            if (
                expected_width is not None and expected_height is not None
                and (int(expected_width), int(expected_height)) != (screen.width, screen.height)
            ):
                raise ValueError(
                    "Размер снимка экрана не совпадает с сохранённым профилем калибровки: "
                    f"профиль {expected_width} × {expected_height}, снимок "
                    f"{screen.width} × {screen.height}. Проверь DPI/масштаб и откалибруй заново."
                )
            crops = crop_calibrated_regions(screen, config.get("regions", {}))
            if self.experiment_dir is None:
                raise ValueError("Папка эксперимента не создана.")
            screen_path = self.experiment_dir / f"{phase}-screen.png"
            board_path = self.experiment_dir / f"{phase}-board.png"
            meter_path = self.experiment_dir / f"{phase}-paint-meter.png"
            screen.save(screen_path)
            crops["board_area"].save(board_path)
            crops["paint_meter_area"].save(meter_path)
            self.screen_resolution = {"width": int(screen.width), "height": int(screen.height)}

            phase_record: dict[str, Any] = {
                "captured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "screen_size": {"width": int(screen.width), "height": int(screen.height)},
                "clear_click_sent": clear_point is not None,
                "files": {
                    "full_screen": screen_path.name,
                    "board_roi": board_path.name,
                    "paint_meter_roi": meter_path.name,
                },
            }
            before = self.experiment_phases.get("before_draw")
            after = self.experiment_phases.get("after_draw")
            if phase == "after_draw":
                # Only analyze per-stroke visibility against a separately confirmed blank
                # reference whose screen geometry matches the active calibration profile.
                reference_path, metadata_path = self._blank_board_reference_paths()
                visibility: dict[str, Any] = {
                    "status": "inconclusive",
                    "reason": "missing_explicit_blank_board_reference",
                    "note": "Для анализа отдельных штрихов нужен подтверждённый эталон пустой доски.",
                }
                try:
                    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                    region = config.get("regions", {}).get("board_area", {})
                    current_region = {key: int(region[key]) for key in ("x", "y", "width", "height")}
                    valid_reference = (
                        metadata.get("reference_type") == "user_confirmed_blank_board_roi"
                        and metadata.get("user_confirmed_blank") is True
                        and metadata.get("board_region") == current_region
                        and metadata.get("screen_size") == {"width": screen.width, "height": screen.height}
                        and reference_path.is_file()
                    )
                    if not valid_reference:
                        visibility["reason"] = "reference_profile_mismatch_or_invalid"
                    elif not isinstance(self.current_plan, dict) or not isinstance(self.current_plan.get("strokes"), list):
                        visibility["reason"] = "drawing_plan_has_no_strokes"
                    else:
                        with Image.open(reference_path) as reference_image, Image.open(board_path) as after_image:
                            reference = reference_image.convert("RGB")
                            current_board = after_image.convert("RGB")
                            if reference.size != current_board.size:
                                visibility["reason"] = "reference_board_dimensions_mismatch"
                            else:
                                capture_strokes, transform_error = _screen_local_strokes_for_capture(
                                    self.current_plan, current_board.size
                                )
                                if transform_error:
                                    visibility["reason"] = transform_error
                                else:
                                    try:
                                        brush_value = int(
                                            self._experiment_requested_brush
                                            if self._experiment_requested_brush is not None
                                            else self.brush_var.get().strip()
                                        )
                                    except (TypeError, ValueError):
                                        brush_value = 1
                                    visibility = measure_stroke_visibility(
                                        reference,
                                        current_board,
                                        capture_strokes or [],
                                        padding_px=max(2, brush_value + 1),
                                    )
                                    visibility["reference_file"] = reference_path.name
                                    visibility["padding_px"] = max(2, brush_value + 1)
                                    visibility["requested_brush_value"] = brush_value
                except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
                    visibility["status"] = "inconclusive"
                    visibility["reason"] = "reference_or_plan_analysis_failed"
                    visibility["error"] = str(exc)
                phase_record["stroke_visibility_analysis"] = visibility
            if phase == "after_clear":
                reference_path, metadata_path = self._blank_board_reference_paths()
                clear_check: dict[str, Any] = {
                    "status": "inconclusive",
                    "reason": "missing_explicit_blank_board_reference",
                    "note": "Очистка не считается подтверждённой без отдельного эталона пустой доски.",
                }
                try:
                    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                    region = config.get("regions", {}).get("board_area", {})
                    current_region = {key: int(region[key]) for key in ("x", "y", "width", "height")}
                    if (
                        metadata.get("reference_type") != "user_confirmed_blank_board_roi"
                        or metadata.get("user_confirmed_blank") is not True
                        or metadata.get("board_region") != current_region
                        or metadata.get("screen_size") != {"width": screen.width, "height": screen.height}
                        or not reference_path.is_file()
                    ):
                        clear_check["reason"] = "reference_profile_mismatch_or_invalid"
                    else:
                        with Image.open(reference_path) as reference_image, Image.open(board_path) as after_clear_image:
                            clear_check = evaluate_board_clear(reference_image.copy(), after_clear_image.copy())
                            clear_check["reference_file"] = reference_path.name
                except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
                    clear_check["reason"] = "reference_unavailable_or_invalid"
                    clear_check["error"] = str(exc)
                phase_record["board_clear_check"] = clear_check
                phase_record["board_clear_status"] = clear_check.get("status", "inconclusive")
            if before is not None:
                baseline_meter_path = self.experiment_dir / before["files"]["paint_meter_roi"]
                with Image.open(baseline_meter_path) as baseline_meter, Image.open(meter_path) as current_meter:
                    phase_record["paint_meter_measurement"] = measure_meter_fill_against_baseline(baseline_meter, current_meter)
                    if phase == "after_clear":
                        phase_record["paint_meter_restoration"] = evaluate_meter_restoration(baseline_meter, current_meter)
            for baseline_name, baseline in (("before_draw", before), ("after_draw", after)):
                if baseline is None or baseline_name == phase:
                    continue
                for roi_key, file_key in (("board_area", "board_roi"), ("paint_meter_area", "paint_meter_roi")):
                    baseline_path = self.experiment_dir / baseline["files"][file_key]
                    current_path = board_path if roi_key == "board_area" else meter_path
                    with Image.open(baseline_path) as first, Image.open(current_path) as second:
                        phase_record.setdefault("visual_comparisons", {})[f"{roi_key}_vs_{baseline_name}"] = compare_images(first, second)

            self.experiment_phases[phase] = phase_record
            manifest = {
                "schema_version": 1,
                "record_type": "autodraw_brush_paint_experiment",
                "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "test_case": TEST_CASES.get(self.case_var.get(), {}).get("id"),
                "brush_value_requested": self._experiment_requested_brush if self._experiment_requested_brush is not None else int(self.brush_var.get().strip()),
                "drawing_plan_path": str(self.current_plan_path) if self.current_plan_path else None,
                "execution_report_path": str(self.execution_report_path) if self.execution_report_path else None,
                "calibration_profile_path": str(config.get("profile_path", "")) or None,
                "phases": self.experiment_phases,
                "interpretation_limits": [
                    "Screenshots are captured from the configured screen-coordinate system.",
                    "Meter fill is a provisional estimate against the before-draw baseline, not OCR or a direct reading of the game's resource counter.",
                    "Ambiguous or non-contiguous changes are marked inconclusive and require manual review.",
                    "A successful executor report does not prove that every stroke was registered by the game.",
                    "The automated post-draw workflow does not click Clear; the drawing remains on the board for manual inspection.",
                    "Board-clear status is confirmed only against a separately captured, user-confirmed blank-board ROI; missing/mismatched reference means inconclusive.",
                ],
            }
            manifest_path = self.experiment_dir / "experiment.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.screenshot_path = screen_path
            self.area_var.set(
                f"Эксперимент: {self.experiment_dir.name}; снимок {phase}: "
                f"доска {crops['board_area'].width} × {crops['board_area'].height}, "
                f"полоска краски {crops['paint_meter_area'].width} × {crops['paint_meter_area'].height}."
            )
            self.status_var.set(
                f"Сохранён этап {phase}. ROI и experiment.json записаны в {self.experiment_dir}. "
                "Оценка заполнения полоски предварительная; это не OCR и не чтение внутреннего счётчика."
            )
        except Exception as exc:
            messagebox.showerror("Не удалось сохранить этап эксперимента", str(exc), parent=self.root)
            self.status_var.set(f"Ошибка снимка эксперимента: {exc}")
        finally:
            self.root.deiconify()
            self.root.lift()

    def _cancel_automated_postdraw(self) -> None:
        """Stop future post-draw actions and persist partial evidence on global Alt."""
        if not self._automated_postdraw_active:
            return
        self._automated_postdraw_active = False
        if self._automated_postdraw_after_id is not None:
            try:
                self.root.after_cancel(self._automated_postdraw_after_id)
            except (tk.TclError, ValueError):
                pass
            self._automated_postdraw_after_id = None
        self._stop_brush_hotkey_listener()
        self.experiment_phases.setdefault("postdraw_workflow", {}).update({
            "status": "stopped",
            "reason": "Alt",
            "captured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "note": "No later automatic action was started after Alt.",
        })
        try:
            self._write_experiment_manifest()
        except (OSError, ValueError, TypeError) as exc:
            self.status_var.set(f"Постэтап остановлен Alt; не удалось сохранить манифест: {exc}")
        else:
            self.status_var.set("Постэтап остановлен по Alt. Новые действия не запускаются; проверь доску и кисть вручную.")
        try:
            self.root.deiconify()
            self.root.lift()
        except tk.TclError:
            pass

    def _start_automated_postdraw(self) -> None:
        """Capture the completed drawing and preserve the board for manual inspection."""
        if self.experiment_dir is None:
            self.status_var.set("Постэтап пропущен: каталог эксперимента отсутствует.")
            return
        config = self.get_calibration_profile() if callable(self.get_calibration_profile) else None
        if not isinstance(config, dict):
            self.experiment_phases["postdraw_workflow"] = {
                "status": "failed", "reason": "calibration_profile_unavailable"
            }
            self._write_experiment_manifest()
            self.status_var.set("Постэтап остановлен: профиль калибровки недоступен.")
            return
        self._automated_postdraw_active = True
        self._automated_postdraw_stop_requested = False
        self.status_var.set("Исполнение завершено. Через 2 секунды сохраняется результат; доска останется без очистки. Alt отменяет дальнейшие действия.")
        self.root.iconify()
        self._start_brush_hotkey_listener()
        self._automated_postdraw_after_id = self.root.after(
            2000, lambda: self._capture_automated_after_draw(config)
        )

    def _capture_automated_after_draw(self, config: dict[str, Any]) -> None:
        if not self._automated_postdraw_active:
            return
        self._automated_postdraw_after_id = None
        try:
            screen = ImageGrab.grab()
            expected = config.get("screen_size", {})
            if isinstance(expected, dict):
                ew, eh = expected.get("width"), expected.get("height")
                if ew is not None and eh is not None and (int(ew), int(eh)) != screen.size:
                    raise ValueError("Разрешение экрана изменилось после калибровки.")
            crops = crop_calibrated_regions(screen, config.get("regions", {}))
            if self.experiment_dir is None:
                raise ValueError("Каталог эксперимента отсутствует.")
            screen_path = self.experiment_dir / "after_draw-screen.png"
            board_path = self.experiment_dir / "after_draw-board.png"
            meter_path = self.experiment_dir / "after_draw-paint-meter.png"
            screen.save(screen_path)
            crops["board_area"].save(board_path)
            crops["paint_meter_area"].save(meter_path)
            self.experiment_phases["after_draw"] = {
                "status": "captured",
                "captured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "screen_size": {"width": screen.width, "height": screen.height},
                "files": {"full_screen": screen_path.name, "board_roi": board_path.name, "paint_meter_roi": meter_path.name},
            }
            before = self.experiment_phases.get("before_draw")
            if before and before.get("files", {}).get("paint_meter_roi"):
                baseline = self.experiment_dir / before["files"]["paint_meter_roi"]
                with Image.open(baseline) as first, Image.open(meter_path) as second:
                    self.experiment_phases["after_draw"]["paint_meter_measurement"] = measure_meter_fill_against_baseline(first, second)
            # Keep the automated post-draw path aligned with the manual capture path.
            # Visibility-analysis failures are recorded as inconclusive and must not
            # interrupt the post-draw capture/restore workflow.
            visibility: dict[str, Any] = {
                "status": "inconclusive",
                "reason": "missing_explicit_blank_board_reference",
            }
            try:
                reference_path, metadata_path = self._blank_board_reference_paths()
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                region = config.get("regions", {}).get("board_area", {})
                current_region = {key: int(region[key]) for key in ("x", "y", "width", "height")}
                valid_reference = (
                    metadata.get("reference_type") == "user_confirmed_blank_board_roi"
                    and metadata.get("user_confirmed_blank") is True
                    and metadata.get("board_region") == current_region
                    and metadata.get("screen_size") == {"width": screen.width, "height": screen.height}
                    and reference_path.is_file()
                )
                if not valid_reference:
                    visibility["reason"] = "reference_profile_mismatch_or_invalid"
                elif not isinstance(self.current_plan, dict) or not isinstance(self.current_plan.get("strokes"), list):
                    visibility["reason"] = "drawing_plan_has_no_strokes"
                else:
                    with Image.open(reference_path) as reference_image, Image.open(board_path) as after_image:
                        reference = reference_image.convert("RGB")
                        current_board = after_image.convert("RGB")
                        if reference.size != current_board.size:
                            visibility["reason"] = "reference_board_dimensions_mismatch"
                        else:
                            capture_strokes, transform_error = _screen_local_strokes_for_capture(
                                self.current_plan, current_board.size
                            )
                            if transform_error:
                                visibility["reason"] = transform_error
                            else:
                                try:
                                    brush_value = int(
                                        self._experiment_requested_brush
                                        if self._experiment_requested_brush is not None
                                        else self.brush_var.get().strip()
                                    )
                                except (TypeError, ValueError):
                                    brush_value = 1
                                padding_px = max(2, brush_value + 1)
                                visibility = measure_stroke_visibility(
                                    reference, current_board, capture_strokes or [],
                                    padding_px=padding_px,
                                )
                                visibility.update({
                                    "reference_file": reference_path.name,
                                    "padding_px": padding_px,
                                    "requested_brush_value": brush_value,
                                })
            except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
                visibility = {
                    "status": "inconclusive",
                    "reason": "reference_or_plan_analysis_failed",
                    "error": str(exc),
                }
            self.experiment_phases["after_draw"]["stroke_visibility_analysis"] = visibility
            self._write_experiment_manifest()
            if self._automated_postdraw_stop_requested or not self._automated_postdraw_active:
                self._cancel_automated_postdraw()
                return
            self._finish_automated_postdraw(
                "completed",
                "Результат сохранён; автоматическая очистка отключена, рисунок оставлен на доске.",
                restore_brush=True,
            )
        except Exception as exc:
            self._finish_automated_postdraw("failed", f"Не удалось сохранить результат после рисования: {exc}")

    def _capture_automated_after_clear(
        self, config: dict[str, Any], reference_path: Path, metadata: dict[str, Any]
    ) -> None:
        if not self._automated_postdraw_active:
            return
        self._automated_postdraw_after_id = None
        clear_status = "inconclusive"
        try:
            screen = ImageGrab.grab()
            expected = config.get("screen_size", {})
            if isinstance(expected, dict):
                ew, eh = expected.get("width"), expected.get("height")
                if ew is not None and eh is not None and (int(ew), int(eh)) != screen.size:
                    raise ValueError("Разрешение экрана изменилось во время проверки очистки.")
            crops = crop_calibrated_regions(screen, config.get("regions", {}))
            if self.experiment_dir is None:
                raise ValueError("Каталог эксперимента отсутствует.")
            screen_path = self.experiment_dir / "after_clear-screen.png"
            board_path = self.experiment_dir / "after_clear-board.png"
            meter_path = self.experiment_dir / "after_clear-paint-meter.png"
            screen.save(screen_path)
            crops["board_area"].save(board_path)
            crops["paint_meter_area"].save(meter_path)
            with Image.open(reference_path) as reference:
                clear_check = evaluate_board_clear(reference.copy(), crops["board_area"])
            clear_status = clear_check.get("status", "inconclusive")
            self.experiment_phases["after_clear"] = {
                "status": clear_status,
                "board_clear_check": clear_check,
                "board_clear_status": clear_status,
                "captured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "screen_size": {"width": screen.width, "height": screen.height},
                "files": {"full_screen": screen_path.name, "board_roi": board_path.name, "paint_meter_roi": meter_path.name},
            }
            before = self.experiment_phases.get("before_draw")
            if before and before.get("files", {}).get("paint_meter_roi"):
                baseline = self.experiment_dir / before["files"]["paint_meter_roi"]
                with Image.open(baseline) as first, Image.open(meter_path) as second:
                    self.experiment_phases["after_clear"]["paint_meter_restoration"] = evaluate_meter_restoration(first, second)
            self.experiment_phases["postdraw_workflow"]["status"] = "clear_verified" if clear_status in {"restored", "restored_within_pixel_tolerance"} else "clear_not_confirmed"
            self._write_experiment_manifest()
            if self._automated_postdraw_stop_requested or not self._automated_postdraw_active:
                self._cancel_automated_postdraw()
                return
            self._finish_automated_postdraw(
                "completed" if clear_status in {"restored", "restored_within_pixel_tolerance"} else "inconclusive",
                "Очистка подтверждена эталоном." if clear_status in {"restored", "restored_within_pixel_tolerance"} else f"Очистка не подтверждена эталоном: {clear_status}.",
                restore_brush=True,
            )
        except Exception as exc:
            if self._automated_postdraw_stop_requested:
                self._cancel_automated_postdraw()
            else:
                self._finish_automated_postdraw("failed", f"Не удалось проверить очистку: {exc}", restore_brush=True)

    def _finish_automated_postdraw(
        self, status: str, reason: str, *, restore_brush: bool = False
    ) -> None:
        self._automated_postdraw_active = False
        if self._automated_postdraw_after_id is not None:
            try:
                self.root.after_cancel(self._automated_postdraw_after_id)
            except (tk.TclError, ValueError):
                pass
            self._automated_postdraw_after_id = None
        self._stop_brush_hotkey_listener()
        self._postdraw_final_status = status
        self._postdraw_final_reason = reason
        self.experiment_phases.setdefault("postdraw_workflow", {}).update({
            "status": status,
            "reason": reason,
            "finished_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        try:
            self._write_experiment_manifest()
        except (OSError, ValueError, TypeError) as exc:
            self._postdraw_final_reason += f"; ошибка записи манифеста: {exc}"
        if restore_brush:
            requested_brush = self._experiment_requested_brush
            if requested_brush is None:
                try:
                    requested_brush = int(self.brush_var.get().strip())
                except (ValueError, AttributeError):
                    requested_brush = 30
            self._start_executor_after_brush_drag = False
            try:
                if not self._schedule_brush_restore_30(requested_brush):
                    raise RuntimeError("Не удалось запланировать перетаскивание кисти к 30.")
                self.experiment_phases["restore_brush_30"] = {
                    "status": "drag_scheduled",
                    "requested_value": 30,
                    "drag_start_for_requested_brush": list(calculate_slider_target(
                        self.brush_slider_start, self.brush_slider_end, requested_brush
                    )),
                    "drag_target_for_brush_30": list(self.brush_slider_start),
                    "note": "The return drag starts at the tested brush position and ends at the calibrated brush-30 endpoint. The game value still requires visual confirmation.",
                }
                self._write_experiment_manifest()
                self.status_var.set(
                    f"Постэтап: {status}. {self._postdraw_final_reason} Возврат кисти к 30 запланирован; "
                    "переключись в браузер и не трогай мышь 3 секунды. Alt отменяет перетаскивание."
                )
                return
            except Exception as exc:
                self.experiment_phases["restore_brush_30"] = {
                    "status": "failed",
                    "requested_value": 30,
                    "error": str(exc),
                    "note": "Could not schedule the return drag; manual recovery is required.",
                }
                try:
                    self._write_experiment_manifest()
                except (OSError, ValueError, TypeError):
                    pass
                self._postdraw_final_reason += f" Возврат кисти к 30 не запланирован: {exc}"
        self._show_postdraw_completion_notification()

    def _schedule_brush_restore_30(self, requested_brush: int) -> bool:
        """Drag from the tested slider position back to the calibrated brush-30 endpoint."""
        if platform.system() != "Windows":
            raise RuntimeError("Автоматический возврат кисти доступен только в Windows.")
        calibrated = self.get_brush_control() if callable(self.get_brush_control) else None
        if not isinstance(calibrated, dict) or calibrated.get("mode") != "slider":
            raise ValueError("Для автоматического возврата требуется сохранённый профиль «Расширенный ползунок 1–30».")
        if not calibrated.get("start") or not calibrated.get("end"):
            raise ValueError("В профиле калибровки отсутствуют оба конца ползунка.")
        start_30 = self._parse_point(
            f"{calibrated['start'][0]},{calibrated['start'][1]}", "Край 30 из профиля"
        )
        end_1 = self._parse_point(
            f"{calibrated['end'][0]},{calibrated['end'][1]}", "Край 1 из профиля"
        )
        drag_start = calculate_slider_target(start_30, end_1, requested_brush)
        self.brush_slider_start, self.brush_slider_end = start_30, end_1
        self.brush_var.set("30")
        self._brush_drag_purpose = "restore_brush_30"
        self.status_var.set(
            f"Через 3 секунды кисть будет перетащена с позиции радиуса {requested_brush} к радиусу 30. "
            "Переключись в браузер и не трогай мышь. Alt отменяет действие."
        )
        self.root.iconify()
        self._start_brush_hotkey_listener()
        try:
            self._brush_drag_countdown_id = self.root.after(
                3000, lambda: self._start_scheduled_brush_drag(drag_start, start_30[0], start_30[1], 30)
            )
        except Exception:
            self._brush_drag_purpose = "set_brush_size"
            self._stop_brush_hotkey_listener()
            try:
                self.root.deiconify()
                self.root.lift()
            except tk.TclError:
                pass
            raise
        return True

    def _record_brush_restore_result(
        self, status: str, detail: str, *, state: dict[str, Any] | None = None
    ) -> None:
        """Persist the final restore-drag result and notify the user after the last mouse action."""
        phase: dict[str, Any] = {
            "status": status,
            "requested_value": 30,
            "finished_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "note": detail,
        }
        if state:
            phase["drag_start"] = list(state.get("start", ()))
            phase["drag_target"] = list(state.get("target", ()))
        self.experiment_phases["restore_brush_30"] = phase
        try:
            self._write_experiment_manifest()
        except (OSError, ValueError, TypeError) as exc:
            detail += f" Не удалось обновить experiment.json: {exc}"
        self._postdraw_final_reason = f"{self._postdraw_final_reason} {detail}".strip()
        try:
            self.root.deiconify()
            self.root.lift()
        except tk.TclError:
            pass
        self.status_var.set(f"Тест завершён: {self._postdraw_final_status}. {self._postdraw_final_reason}")
        self._show_postdraw_completion_notification(restore_status=status)

    def _show_postdraw_completion_notification(self, *, restore_status: str | None = None) -> None:
        """Show a visible end-of-test notification instead of relying on a hidden status bar."""
        try:
            self.root.deiconify()
            self.root.lift()
        except tk.TclError:
            pass
        restore_ok = restore_status == "drag_completed_unverified"
        if self._postdraw_final_status == "completed" and restore_ok:
            messagebox.showinfo(
                "Тест кисти завершён",
                "Скриншоты и experiment.json сохранены. Перетаскивание кисти к позиции 30 выполнено, "
                "но игра не предоставляет автоматического подтверждения выбранного радиуса. "
                "Проверь кисть в браузере и результат в папке эксперимента.",
                parent=self.root,
            )
            return
        details = self._postdraw_final_reason
        if restore_status == "stopped":
            details += " Возврат кисти отменён по Alt; выставь 30 вручную."
        elif restore_status == "failed":
            details += " Автоматический возврат кисти не завершён; выставь 30 вручную."
        elif restore_status is None:
            details += " Проверь состояние кисти и папку эксперимента вручную."
        messagebox.showwarning(
            "Тест кисти завершён не полностью",
            f"Статус постэтапа: {self._postdraw_final_status}.\n{details}",
            parent=self.root,
        )

    def handle_executor_finished(self, summary: dict[str, Any], report_path: str | Path | None) -> bool:
        """Attach the real executor result to the active brush experiment without a modal dialog."""
        try:
            self.execution_report = dict(summary) if isinstance(summary, dict) else {"summary": str(summary)}
            self.execution_report_path = Path(report_path).resolve() if report_path else None
            status = str(self.execution_report.get("status", "unknown"))
            self.experiment_phases["execution"] = {
                "status": status,
                "report_path": str(self.execution_report_path) if self.execution_report_path else None,
                "summary": self.execution_report,
                "captured_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            if self.experiment_dir is not None:
                self._write_experiment_manifest()
                self._schedule_bridge_report_capture()
            self.status_var.set(
                f"Исполнитель завершил тест со статусом «{status}». "
                + (f"Отчёт: {self.execution_report_path}" if self.execution_report_path else "Файл отчёта не создан.")
            )
            if should_run_postdraw_workflow(status) and self.experiment_dir is not None:
                self._start_automated_postdraw()
            else:
                self.experiment_phases["postdraw_workflow"] = {
                    "status": "skipped",
                    "reason": f"executor_status_not_successful:{status}",
                    "note": "No automatic post-draw clear was attempted after a stopped/failed/unknown execution.",
                }
                if self.experiment_dir is not None:
                    self._write_experiment_manifest()
            return True
        except Exception as exc:
            self.status_var.set(f"Не удалось привязать результат исполнителя к тесту кисти: {exc}")
            return False

    def _schedule_bridge_report_capture(self, attempt: int = 0) -> None:
        """Attach only the unique Game Monitor run matching the completed executor interval."""
        if self.experiment_dir is None:
            return
        if attempt == 0 and self._bridge_capture_poll_id is not None:
            return

        bridge_root = self.output_dir / "game_monitor_bridge"
        execution = self.execution_report if isinstance(self.execution_report, dict) else {}
        plan_strokes = self.current_plan.get("strokes") if isinstance(self.current_plan, dict) else None
        try:
            expected_strokes = len(plan_strokes) if isinstance(plan_strokes, list) else int(
                execution.get("total_strokes", execution.get("completed_strokes", 0))
            )
        except (TypeError, ValueError):
            expected_strokes = 0

        before_phase = self.experiment_phases.get("before_draw", {})
        before_text = before_phase.get("captured_at_utc") if isinstance(before_phase, dict) else None
        requested = self._experiment_requested_brush
        if requested is None:
            try:
                requested = int(self.brush_var.get().strip())
            except (AttributeError, TypeError, ValueError):
                requested = None

        candidates: list[tuple[Path, dict[str, Any]]] = []
        if bridge_root.is_dir():
            for source_path in bridge_root.rglob("game-monitor-run-*.json"):
                try:
                    report = json.loads(source_path.read_text(encoding="utf-8"))
                    if isinstance(report, dict):
                        candidates.append((source_path, report))
                except (OSError, UnicodeError, json.JSONDecodeError):
                    continue

        selected, match_reason, candidate_count = select_execution_monitor_run(
            candidates,
            execution_report=execution,
            requested_brush=requested,
            expected_strokes=expected_strokes,
            before_draw_at=before_text,
        )
        if selected is not None:
            source_path, report = selected
            try:
                target_path = self.experiment_dir / "monitor_report.json"
                shutil.copy2(source_path, target_path)
                chalk = report.get("chalk") if isinstance(report.get("chalk"), dict) else {}
                frame_probe = report.get("frame_probe") if isinstance(report.get("frame_probe"), dict) else {}
                trajectory = report.get("trajectory") if isinstance(report.get("trajectory"), dict) else {}
                summary = {
                    "source": "loopback_websocket_bridge",
                    "session_id": report.get("session_id"),
                    "run_id": report.get("run_id"),
                    "execution_status": report.get("execution_status"),
                    "brush_radius": report.get("brush_radius"),
                    "observed_brush_radii": report.get("observed_brush_radii"),
                    "brush_radius_status": report.get("brush_radius_status"),
                    "chalk": chalk,
                    "sampled_point_delta_total": report.get("sampled_point_delta_total"),
                    "point_delta_matches_chalk": report.get("point_delta_matches_chalk"),
                    "stroke_count": report.get("stroke_count"),
                    "frame_probe": frame_probe,
                    "trajectory": trajectory,
                    "event_count": report.get("event_count"),
                    "dropped_events": report.get("dropped_events"),
                    "monitor_dropped_events": report.get("monitor_dropped_events"),
                    "monitor_error_count": report.get("monitor_error_count"),
                    "started_at_utc": report.get("started_at_utc"),
                    "finished_at_utc": report.get("finished_at_utc"),
                }
                self.game_monitor_report_path = target_path.resolve()
                self.game_monitor_summary = summary
                chalk_counter_consistent = is_exact_positive_chalk_measurement(chalk)
                telemetry_clean = (
                    report.get("execution_status") == "completed"
                    and chalk.get("status") == "exact"
                    and chalk_counter_consistent
                    and int(report.get("stroke_count", 0) or 0) == expected_strokes
                    and report.get("brush_radius_status") == "single"
                    and report.get("observed_brush_radii") == [requested]
                    and report.get("point_delta_matches_chalk") is True
                    and frame_probe.get("status") == "measured"
                    and frame_probe.get("visibility_interruption") is False
                    and int(trajectory.get("accepted_sample_count", 0) or 0) > 0
                    and report.get("dropped_events", 0) == 0
                    and report.get("monitor_dropped_events", 0) == 0
                    and report.get("monitor_error_count", 0) == 0
                )
                self.experiment_phases["monitor_capture"] = {
                    "status": "saved" if telemetry_clean else "partial",
                    "transport": "loopback_websocket",
                    "match_reason": match_reason,
                    "session_id": report.get("session_id"),
                    "run_id": report.get("run_id"),
                    "source_path": str(source_path.resolve()),
                    "report_path": target_path.name,
                    "report_event_count": report.get("event_count"),
                    "dropped_events": report.get("dropped_events"),
                    "monitor_dropped_events": report.get("monitor_dropped_events"),
                    "monitor_error_count": report.get("monitor_error_count"),
                    "stroke_count": report.get("stroke_count"),
                    "expected_stroke_count": expected_strokes,
                    "point_delta_matches_chalk": report.get("point_delta_matches_chalk"),
                    "brush_radius_status": report.get("brush_radius_status"),
                    "chalk_status": chalk.get("status", "inconclusive"),
                    "chalk_counter_consistent": chalk_counter_consistent,
                    "captured_at_utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                }
                self._bridge_capture_poll_id = None
                self._write_experiment_manifest()
                self.status_var.set(
                    f"Game Monitor привязан к прогону исполнителя: CHALK "
                    f"{chalk.get('consumed_points', 'не определён')}, радиус {report.get('brush_radius')}, "
                    f"штрихов {report.get('stroke_count')}/{expected_strokes}."
                )
                return
            except (OSError, UnicodeError, TypeError, ValueError):
                pass

        if attempt < 20:
            self._bridge_capture_poll_id = self.root.after(
                500, lambda: self._schedule_bridge_report_capture(attempt + 1)
            )
            return

        self._bridge_capture_poll_id = None
        self.experiment_phases["monitor_capture"] = {
            "status": "unavailable",
            "transport": "loopback_websocket",
            "reason": match_reason,
            "candidate_count": candidate_count,
            "expected_stroke_count": expected_strokes,
            "execution_started_at": execution.get("started_at"),
            "execution_ended_at": execution.get("ended_at"),
            "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        }
        try:
            self._write_experiment_manifest()
        except (OSError, ValueError, TypeError):
            pass

    def _write_experiment_manifest(self) -> Path | None:
        """Persist current experiment evidence; safe to call after any completed phase."""
        if self.experiment_dir is None:
            return None
        config = self.get_calibration_profile() if callable(self.get_calibration_profile) else None
        manifest = {
            "schema_version": 1,
            "record_type": "autodraw_brush_paint_experiment",
            "updated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "test_case": TEST_CASES.get(self.case_var.get(), {}).get("id"),
            "brush_value_requested": self._experiment_requested_brush if self._experiment_requested_brush is not None else int(self.brush_var.get().strip()),
            "drawing_plan_path": str(self.current_plan_path) if self.current_plan_path else None,
            "execution_report_path": str(self.execution_report_path) if self.execution_report_path else None,
            "execution_report": self.execution_report,
            "game_monitor_report_path": str(self.game_monitor_report_path) if self.game_monitor_report_path else None,
            "game_monitor_summary": self.game_monitor_summary,
            "monitor_capture": self.experiment_phases.get("monitor_capture"),
            "calibration_profile_path": (str(config.get("profile_path", "")) or None) if isinstance(config, dict) else None,
            "phases": self.experiment_phases,
            "interpretation_limits": [
                "Meter fill is a provisional image estimate, not a direct read of the game's internal resource counter.",
                "A successful executor report does not prove every stroke was registered by the game.",
                "Execution status and visual evidence are recorded separately.",
            ],
        }
        path = self.experiment_dir / "experiment.json"
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path

    def load_execution_report(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Выбери JSON-отчёт последнего исполнения AutoDraw",
            initialdir=str(self.output_dir.parent),
            filetypes=(("JSON", "*.json"), ("Все файлы", "*.*")),
        )
        if not path:
            return
        try:
            document = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                raise ValueError("Отчёт должен содержать JSON-объект.")
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            messagebox.showerror("Не удалось прочитать отчёт", str(exc), parent=self.root)
            return
        self.execution_report_path = Path(path).resolve()
        self.execution_report = document
        self.status_var.set(f"Отчёт исполнения привязан к тесту: {self.execution_report_path}")

    def load_game_monitor_report(self) -> None:
        """Attach a passive Game Monitor JSON report and extract only verifiable telemetry."""
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Выбери JSON-отчёт Game Monitor",
            initialdir=str(self.output_dir.parent),
            filetypes=(("JSON", "*.json"), ("Все файлы", "*.*")),
        )
        if not path:
            return
        try:
            document = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                raise ValueError("Отчёт Monitor должен содержать JSON-объект.")
            requested_brush = self._experiment_requested_brush
            if requested_brush is None:
                setup = self.experiment_phases.get("brush_setup", {})
                requested_brush = setup.get("requested_value") if isinstance(setup, dict) else None
            if requested_brush is None:
                try:
                    requested_brush = int(self.brush_var.get().strip())
                except (AttributeError, TypeError, ValueError):
                    requested_brush = None
            self.game_monitor_report_path = Path(path).resolve()
            self.game_monitor_summary = summarize_game_monitor_report(document, requested_brush)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
            messagebox.showerror("Не удалось прочитать Game Monitor JSON", str(exc), parent=self.root)
            return
        summary = self.game_monitor_summary
        manifest_path = None
        try:
            manifest_path = self._write_experiment_manifest()
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            messagebox.showwarning(
                "Не удалось сохранить привязку Monitor",
                f"JSON прочитан, но манифест эксперимента не обновлён: {exc}",
                parent=self.root,
            )
        persistence_note = (
            f"Манифест обновлён: {manifest_path.name}."
            if manifest_path is not None
            else "Отчёт привязан только в текущем сеансе; активный манифест эксперимента отсутствует."
        )
        brush_status = summary["brush_value_status"]
        if brush_status == "mismatch":
            self.status_var.set(
                f"Game Monitor: радиус в игре {summary['observed_draw_radii']}, "
                f"запрошено {summary['requested_brush_value']}. Несовпадение!"
            )
            messagebox.showwarning(
                "Размер кисти не совпал",
                f"Запрошено: {summary['requested_brush_value']}\n"
                f"Фактически в DRAW_SAMPLE: {summary['observed_draw_radii']}\n\n"
                f"{persistence_note}\nНе используй этот прогон как подтверждение запрошенного размера.",
                parent=self.root,
            )
        elif brush_status == "mixed":
            self.status_var.set(
                f"Game Monitor: в одном отчёте обнаружены разные радиусы {summary['observed_draw_radii']}."
            )
            messagebox.showwarning(
                "В отчёте несколько размеров кисти",
                f"Обнаруженные радиусы: {summary['observed_draw_radii']}.\n"
                f"Проверь, что отчёт относится только к одному эксперименту.\n{persistence_note}",
                parent=self.root,
            )
        elif brush_status == "unavailable":
            self.status_var.set(f"Game Monitor привязан, но в отчёте нет DRAW_SAMPLE с координатами активного рисования. {persistence_note}")
        else:
            self.status_var.set(
                f"Game Monitor привязан: {self.game_monitor_report_path.name}; "
                f"событий {summary['event_count']}, "
                f"активных DRAW_SAMPLE {summary['drawing_sample_count']}, "
                f"радиус {summary['observed_draw_radii']}. {persistence_note}"
            )

    def _measurement_values(self) -> dict[str, Any]:
        def optional_number(raw: str, field: str):
            value = raw.strip()
            if not value:
                return None
            try:
                number = float(value.replace(",", "."))
            except ValueError as exc:
                raise ValueError(f"Поле «{field}» должно быть числом.") from exc
            if number < 0:
                raise ValueError(f"Поле «{field}» не может быть отрицательным.")
            return int(number) if number.is_integer() else number

        visible = [item.strip() for item in self.visible_strokes_var.get().split(",") if item.strip()]
        missing = [item.strip() for item in self.missing_strokes_var.get().split(",") if item.strip()]
        return {
            "observed_stroke_count": len(visible) if visible or missing else None,
            "visible_stroke_names": visible,
            "missing_stroke_names": missing,
            "measured_footprint_width_px": optional_number(self.footprint_width_var.get(), "ширина следа"),
            "measured_footprint_height_px": optional_number(self.footprint_height_var.get(), "высота следа"),
            "paint_points_before": optional_number(self.paint_before_var.get(), "краска до"),
            "paint_points_after": optional_number(self.paint_after_var.get(), "краска после"),
            "browser_zoom_percent": optional_number(self.zoom_var.get(), "масштаб браузера"),
        }

    def _build_record(self) -> dict[str, Any]:
        try:
            brush = int(self.brush_var.get().strip())
        except ValueError as exc:
            raise ValueError("Размер кисти должен быть целым числом от 1 до 30.") from exc
        calibrated = self.get_brush_control() if callable(self.get_brush_control) else None
        if calibrated and calibrated.get("mode") == "presets":
            brush_control = {
                "type": "preset_click",
                "mode": "presets",
                "selected_brush_point": calibrated.get("presets", {}).get(str(brush)),
                "presets": calibrated.get("presets", {}),
            }
        elif calibrated and calibrated.get("mode") == "slider":
            brush_control = {
                "type": "linear_drag_slider_inverse_radius_1_to_30",
                "mode": "slider",
                "min_value": 1,
                "max_value": 30,
                "start": calibrated.get("start"),
                "end": calibrated.get("end"),
            }
        else:
            brush_control = {
                "type": "manual_or_unconfigured",
                "mode": calibrated.get("mode") if calibrated else None,
                "start": list(self.brush_slider_start) if self.brush_slider_start else None,
                "end": list(self.brush_slider_end) if self.brush_slider_end else None,
            }
        return build_brush_test_record(
            brush_value=brush,
            test_case=self.case_var.get(),
            canvas_area=self.canvas_area,
            screen_area=self.screen_area,
            screenshot_path=str(self.screenshot_path) if self.screenshot_path else None,
            drawing_plan_path=str(self.current_plan_path) if self.current_plan_path else None,
            drawing_plan=self.current_plan,
            execution_report_path=str(self.execution_report_path) if self.execution_report_path else None,
            execution_report=self.execution_report,
            game_monitor_report_path=str(self.game_monitor_report_path) if self.game_monitor_report_path else None,
            game_monitor_summary=self.game_monitor_summary,
            measurements=self._measurement_values(),
            notes=self.notes_var.get(),
            outcome=self.outcome_var.get(),
            screen_resolution=self.screen_resolution,
            brush_control=brush_control,
        )

    def save_record_dialog(self) -> None:
        try:
            record = self._build_record()
        except ValueError as exc:
            messagebox.showerror("Параметры теста", str(exc), parent=self.root)
            return
        suggested = f"brush-test-{record['test_case']['id']}-b{record['brush_value']}-{record['record_id'][:8]}.json"
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Сохранить данные теста кисти",
            initialdir=str(self.output_dir), initialfile=suggested,
            defaultextension=".json", filetypes=(("JSON", "*.json"),),
        )
        if not path:
            return
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        self.last_record_path = target
        self.status_var.set(f"Данные теста сохранены: {target}")

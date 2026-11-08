from __future__ import annotations

import json
import shutil
import sys
import uuid
import ctypes
import platform
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any
from urllib.parse import urlsplit

import pyautogui
from PIL import Image, ImageGrab
from pynput import keyboard

from brush_test_workflow import (
    calculate_slider_target, validate_brush_test_preflight,
    should_run_postdraw_workflow,
)
from brush_radius_feedback import (
    calculate_radius_correction_target, read_active_bridge_radius, read_active_bridge_geometry,
)
from chalk_radius_matrix import (
    MATRIX_SCENARIO_ID, build_chalk_radius_matrix_metadata, is_monitor_run_claimed,
)
from chalk_experiment_matrix import (
    GEOMETRY_MATRIX_SCENARIOS, PHASE_BY_SCENARIO, INDEPENDENT_VALIDATION_PHASE,
    RADIUS_GEOMETRY_VALIDATION_PHASE,
    build_chalk_experiment_matrix_metadata, inspect_chalk_matrix_series,
)
from chalk_test_blocks import (
    build_chalk_test_block_plan, create_chalk_test_block_journal,
    claim_next_chalk_block_task, finish_chalk_block_task,
    load_chalk_test_block_journal, chalk_test_block_progress,
    validate_chalk_block_experiment, stop_chalk_test_block as stop_chalk_test_block_journal,
    record_chalk_block_task_experiment, mark_interrupted_chalk_block_task,
    resolve_interrupted_chalk_block_task,
    acquire_chalk_block_owner_lock, release_chalk_block_owner_lock,
)
from engine001_lab import (
    ENGINE001_PHASE, ENGINE001_EXPECTED_TASKS, ENGINE001_EXPERIMENT_ID,
    inspect_ready_bridge, audit_single_capture,
)
from brush_experiment_capture import (
    compare_images, crop_calibrated_regions,
    measure_meter_fill_against_baseline, evaluate_meter_restoration, evaluate_board_clear,
    measure_stroke_visibility,
)


# Verified against the master game bundle: Graphics.lineStyle receives atom.radius directly.
MAX_BRUSH_LINE_WIDTH_LOGICAL_PX = 30

# Frozen settings for one isolated live stroke consumed by the paired renderer replay.
PAIRED_RENDERER_TEST_CASE_ID = "paired_renderer_single_stroke"
PAIRED_RENDERER_VERTICAL_TEST_CASE_ID = "paired_renderer_vertical_single_stroke"
PAIRED_RENDERER_DIAGONAL_TEST_CASE_ID = "paired_renderer_diagonal_single_stroke"
PAIRED_RENDERER_TEST_CASE_IDS = frozenset({
    PAIRED_RENDERER_TEST_CASE_ID,
    PAIRED_RENDERER_VERTICAL_TEST_CASE_ID,
    PAIRED_RENDERER_DIAGONAL_TEST_CASE_ID,
    "engine001_horizontal_endpoint",
    "engine001_vertical_axis",
    "engine001_diagonal_axis",
})
PAIRED_RENDERER_REQUESTED_RADIUS = 10
PAIRED_RENDERER_PATH_MODE = "smooth"
PAIRED_RENDERER_EXECUTOR_CONFIG = {
    "point_step_px": 2,
    "line_extension_px": 0,
    "point_delay_ms": 10,
    "after_mouse_up_ms": 20,
    "before_mouse_down_ms": 20,
    "after_mouse_down_ms": 40,
    "end_hold_ms": 50,
    "countdown_seconds": 5,
}


def _is_legacy_chalk_radius_matrix_run(scenario_id: str | None, chalk_block_task: dict[str, Any] | None) -> bool:
    """Keep the legacy radius matrix separate from automated G1/G2/G3 block tasks."""
    return scenario_id == MATRIX_SCENARIO_ID and chalk_block_task is None


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


def _cursor_safe_point_outside_region(
    region: dict[str, Any],
    screen_size: tuple[int, int],
    *,
    margin: int = 32,
    avoid_regions: tuple[dict[str, Any], ...] = (),
) -> tuple[int, int]:
    """Choose a capture point outside the board and every additional interactive ROI."""
    if not isinstance(region, dict):
        raise ValueError("Область доски не задана.")
    try:
        screen_width, screen_height = (int(value) for value in screen_size)
        margin = int(margin)
        raw_regions = (region, *avoid_regions)
        rectangles = [
            tuple(int(item[key]) for key in ("x", "y", "width", "height"))
            for item in raw_regions
        ]
    except (KeyError, TypeError, ValueError):
        raise ValueError("Некорректные размеры областей или экрана.") from None
    if screen_width <= 0 or screen_height <= 0 or margin < 1:
        raise ValueError("Размеры экрана и отступ должны быть положительными.")
    for x, y, width, height in rectangles:
        if width <= 0 or height <= 0:
            raise ValueError("Размеры областей должны быть положительными.")
        if x < 0 or y < 0 or x + width > screen_width or y + height > screen_height:
            raise ValueError("Область выходит за пределы экрана.")

    x, y, width, height = rectangles[0]
    center_x, center_y = x + width // 2, y + height // 2
    # The preferred destination is below the lowest interactive region, not merely
    # below the board: this prevents hovering the paint meter and opening its tooltip.
    lowest_region_bottom = max(ry + rh for _, ry, _, rh in rectangles)
    candidates = [(center_x, lowest_region_bottom + margin)]
    for rx, ry, rw, rh in rectangles:
        candidates.extend((
            (rx - margin - 1, ry + rh // 2),
            (rx + rw + margin, ry + rh // 2),
            (rx + rw // 2, ry - margin - 1),
            (rx + rw // 2, ry + rh + margin),
        ))

    def is_clear(point: tuple[int, int]) -> bool:
        px, py = point
        if not (0 <= px < screen_width and 0 <= py < screen_height):
            return False
        return all(
            not (rx - margin <= px <= rx + rw - 1 + margin
                 and ry - margin <= py <= ry + rh - 1 + margin)
            for rx, ry, rw, rh in rectangles
        )

    valid = [point for point in candidates if is_clear(point)]
    if not valid:
        raise ValueError("Не удалось найти безопасную точку курсора вне доски и интерактивных областей.")
    if is_clear(candidates[0]):
        return candidates[0]
    return min(valid, key=lambda point: (point[0] - center_x) ** 2 + (point[1] - center_y) ** 2)


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
    "ENGINE-001 — горизонталь, окончание": {
        "id": "engine001_horizontal_endpoint",
        "description": "Отдельный штрих x=75..385 y=120: проверка принятых точек, midpoint и видимого правого края; запуск только в лабораторном блоке.",
        "strokes": [{"name": "engine001_horizontal_endpoint", "points": [[75,120],[385,120]]}],
    },
    "ENGINE-001 — вертикаль, калибровка": {
        "id": "engine001_vertical_axis",
        "description": "Отдельный вертикальный штрих для калибровки Y; никакой подмены исторических координат.",
        "strokes": [{"name": "engine001_vertical_axis", "points": [[230,35],[230,205]]}],
    },
    "ENGINE-001 — диагональ, обе оси": {
        "id": "engine001_diagonal_axis",
        "description": "Отдельный диагональный штрих для независимого X/Y fit на same-run PNG.",
        "strokes": [{"name": "engine001_diagonal_axis", "points": [[75,70],[385,175]]}],
    },
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
    "Парный renderer — один длинный штрих": {
        "id": PAIRED_RENDERER_TEST_CASE_ID,
        "description": (
            "Изолированный горизонтальный штрих длиной 400 логических px для парного сравнения "
            "live PNG с offline replay по принятым Game Monitor координатам. Требуется ровно один "
            "strokeId, радиус 10, режим игрового рендеринга smooth и активные Game Monitor + Bridge "
            "с input telemetry. Executor profile заморожен: step=2 px, delay=10 ms, line extension=0."
        ),
        "strokes": [
            {"name": "paired_renderer_long_horizontal", "points": [[20, 120], [420, 120]]},
        ],
    },
    "Парный renderer — один вертикальный штрих": {
        "id": PAIRED_RENDERER_VERTICAL_TEST_CASE_ID,
        "description": (
            "Изолированный вертикальный штрих длиной 200 логических px для проверки Y-fit "
            "по same-run Game Monitor telemetry и X fallback по screenshot BoardPane bounds. "
            "Требуется один strokeId, радиус 10, smooth renderer и активные Game Monitor + Bridge."
        ),
        "strokes": [
            {"name": "paired_renderer_long_vertical", "points": [[230, 20], [230, 220]]},
        ],
    },
    "Парный renderer — один диагональный штрих": {
        "id": PAIRED_RENDERER_DIAGONAL_TEST_CASE_ID,
        "description": (
            "Изолированный диагональный штрих от (20,20) до (440,220) для независимого X/Y fit "
            "по same-run Game Monitor telemetry. Требуется один strokeId, радиус 10, smooth renderer "
            "и активные Game Monitor + Bridge с input telemetry."
        ),
        "strokes": [
            {"name": "paired_renderer_long_diagonal", "points": [[20, 20], [440, 220]]},
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
    },
    "V1 — диагонали разных наклонов": {
        "id": "int006_diagonals",
        "description": "INT-006 V1: шесть диагоналей разных наклонов.",
        "strokes": [
            {"name": "slope_025", "points": [[20, 25], [180, 65]]},
            {"name": "slope_050", "points": [[220, 20], [340, 80]]},
            {"name": "slope_100", "points": [[20, 100], [100, 180]]},
            {"name": "slope_200", "points": [[140, 100], [180, 180]]},
            {"name": "negative_shallow", "points": [[220, 170], [380, 130]]},
            {"name": "negative_steep", "points": [[410, 60], [400, 220]]}
        ],
    },
    "V2 — короткие штрихи 12–30 px (follow-up)": {
        "id": "int006_short_strokes_followup",
        "description": "INT-006 V2 follow-up: изолированные штрихи длиной 12, 16, 20, 24 и 30 logical px; отдельная серия, не смешивать с исходными V2 1–10 px.",
        "strokes": [
            {"name": "length_12_horizontal", "points": [[25, 35], [37, 35]]},
            {"name": "length_16_vertical", "points": [[90, 72], [90, 88]]},
            {"name": "length_20_diagonal", "points": [[150, 110], [162, 126]]},
            {"name": "length_24_horizontal", "points": [[250, 170], [274, 170]]},
            {"name": "length_30_vertical", "points": [[370, 195], [370, 225]]}
        ],
    },
    "V3 — непрерывные повороты": {
        "id": "int006_turns",
        "description": "INT-006 V3: три непрерывные ломаные с прямыми, острыми и последовательными поворотами.",
        "strokes": [
            {"name": "right_angle", "points": [[20, 20], [180, 20], [180, 100], [360, 100]]},
            {"name": "acute_zigzag", "points": [[20, 140], [60, 80], [100, 140], [140, 80], [160, 140]]},
            {"name": "multi_turn", "points": [[20, 210], [90, 170], [160, 210], [230, 170], [300, 210], [420, 170]]}
        ],
    },
    "V4 — замкнутые контуры": {
        "id": "int006_closed_contours",
        "description": "INT-006 V4: три замкнутых контура разных типов.",
        "strokes": [
            {"name": "rectangle", "points": [[20, 20], [180, 20], [180, 100], [20, 100], [20, 20]]},
            {"name": "triangle", "points": [[260, 20], [420, 120], [180, 120], [260, 20]]},
            {"name": "irregular_polygon", "points": [[250, 150], [390, 150], [420, 220], [300, 220], [220, 190], [250, 150]]}
        ],
    },
    "V5 — пересечения и sweep параллельных линий": {
        "id": "int006_intersections_spacing_sweep",
        "description": "INT-006 V5 follow-up: X/T/крестовые пересечения и пять независимых пар параллельных линий со spacing 8/12/16/20/24 logical px; 16 штрихов. Отдельная серия, не смешивать с исходным V5.",
        "strokes": [
            {"name": "x_a", "points": [[20, 20], [100, 100]]},
            {"name": "x_b", "points": [[20, 100], [100, 20]]},
            {"name": "t_vertical", "points": [[130, 20], [130, 100]]},
            {"name": "t_horizontal", "points": [[90, 60], [170, 60]]},
            {"name": "cross_horizontal", "points": [[200, 60], [270, 60]]},
            {"name": "cross_vertical", "points": [[235, 20], [235, 100]]},
            {"name": "parallel_s08_a", "points": [[20, 186], [95, 186]]},
            {"name": "parallel_s08_b", "points": [[20, 194], [95, 194]]},
            {"name": "parallel_s12_a", "points": [[105, 184], [180, 184]]},
            {"name": "parallel_s12_b", "points": [[105, 196], [180, 196]]},
            {"name": "parallel_s16_a", "points": [[190, 182], [265, 182]]},
            {"name": "parallel_s16_b", "points": [[190, 198], [265, 198]]},
            {"name": "parallel_s20_a", "points": [[275, 180], [350, 180]]},
            {"name": "parallel_s20_b", "points": [[275, 200], [350, 200]]},
            {"name": "parallel_s24_a", "points": [[360, 178], [435, 178]]},
            {"name": "parallel_s24_b", "points": [[360, 202], [435, 202]]}
        ],
    },
    "INT-006 D1 — смешанные прямые": {
        "id": "int006_validation_d1_mixed_lines",
        "description": "Независимая validation D1: четыре изолированных прямых — горизонталь, вертикаль и две диагонали.",
        "strokes": [
            {"name": "d1_horizontal_100", "points": [[30, 30], [130, 30]]},
            {"name": "d1_vertical_80", "points": [[160, 20], [160, 100]]},
            {"name": "d1_diagonal_1", "points": [[210, 25], [280, 95]]},
            {"name": "d1_diagonal_2", "points": [[310, 100], [390, 40]]}
        ],
    },
    "INT-006 D2 — пятиугольник отдельными сторонами": {
        "id": "int006_validation_d2_polygon",
        "description": "Независимая validation D2: пять отдельных штрихов образуют замкнутый пятиугольник.",
        "strokes": [
            {"name": "d2_side_1", "points": [[40, 35], [130, 25]]},
            {"name": "d2_side_2", "points": [[130, 25], [170, 85]]},
            {"name": "d2_side_3", "points": [[170, 85], [110, 155]]},
            {"name": "d2_side_4", "points": [[110, 155], [30, 115]]},
            {"name": "d2_side_5", "points": [[30, 115], [40, 35]]}
        ],
    },
    "INT-006 D3 — пересечения X, крест и T": {
        "id": "int006_validation_d3_intersections",
        "description": "Независимая validation D3: шесть отдельных линий формируют X, крест и T-узел.",
        "strokes": [
            {"name": "d3_x_a", "points": [[40, 30], [140, 130]]},
            {"name": "d3_x_b", "points": [[40, 130], [140, 30]]},
            {"name": "d3_cross_vertical", "points": [[230, 30], [230, 150]]},
            {"name": "d3_cross_horizontal", "points": [[170, 90], [290, 90]]},
            {"name": "d3_t_horizontal", "points": [[330, 40], [390, 40]]},
            {"name": "d3_t_vertical", "points": [[360, 10], [360, 40]]}
        ],
    },
    "INT-006 D4 — короткие детали": {
        "id": "int006_validation_d4_short_details",
        "description": "Независимая validation D4: изолированные штрихи точной длины 1/2/3/5/8/10 logical px; lookup без интерполяции.",
        "strokes": [
            {"name": "d4_length_1", "points": [[30, 30], [31, 30]]},
            {"name": "d4_length_2", "points": [[60, 30], [60, 32]]},
            {"name": "d4_length_3", "points": [[90, 30], [93, 30]]},
            {"name": "d4_length_5", "points": [[130, 30], [130, 35]]},
            {"name": "d4_length_8", "points": [[170, 30], [178, 30]]},
            {"name": "d4_length_10", "points": [[210, 30], [210, 40]]}
        ],
    },
    "INT-006 D5 — повторное покрытие": {
        "id": "int006_validation_d5_repeated_coverage",
        "description": "Независимая validation D5: три траектории выполняются по два раза; каждый проход является отдельным stroke.",
        "strokes": [
            {"name": "d5_line_50_pass_1", "points": [[40, 40], [90, 40]]},
            {"name": "d5_line_50_pass_2", "points": [[40, 40], [90, 40]]},
            {"name": "d5_line_100_pass_1", "points": [[40, 90], [140, 90]]},
            {"name": "d5_line_100_pass_2", "points": [[40, 90], [140, 90]]},
            {"name": "d5_line_120_pass_1", "points": [[40, 150], [160, 150]]},
            {"name": "d5_line_120_pass_2", "points": [[40, 150], [160, 150]]}
        ],
    },

}



def should_enable_input_telemetry_for_test_case(test_case_label: str) -> bool:
    """Opt in to mouse-coordinate telemetry only for paired-renderer scenarios."""
    scenario = TEST_CASES.get(test_case_label)
    return isinstance(scenario, dict) and scenario.get("id") in PAIRED_RENDERER_TEST_CASE_IDS


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

    renderer_geometry = document.get("renderer_geometry_at_start")
    if not isinstance(renderer_geometry, dict):
        renderer_geometry = document.get("renderer_geometry")
    geometry_summary = None
    if isinstance(renderer_geometry, dict):
        players = renderer_geometry.get("players")
        players = players if isinstance(players, list) else []
        board_players = [
            item for item in players
            if isinstance(item, dict) and isinstance(item.get("boardStageCorners"), dict)
        ]
        selected_player = board_players[0] if len(board_players) == 1 else None
        geometry_summary = {
            "board_detected": bool(board_players),
            "board_ambiguous": len(board_players) > 1,
            "board_client_mapping_method": (
                selected_player.get("boardClientMappingMethod", "unavailable")
                if selected_player else "ambiguous_or_unavailable"
            ),
            "board_stage_corners": selected_player.get("boardStageCorners") if selected_player else None,
            "board_client_corners": selected_player.get("boardClientCorners") if selected_player else None,
            "window_geometry": renderer_geometry.get("windowGeometry"),
            "coordinate_space": "css_client_pixels",
            "desktop_screen_mapping_available": False,
            "executor_usable": False,
        }
    geometry_updates = document.get("renderer_geometry_updates")
    geometry_update_count = len(geometry_updates) if isinstance(geometry_updates, list) else 0
    geometry_end = document.get("renderer_geometry_at_end")
    geometry_end_summary = None
    if isinstance(geometry_end, dict):
        end_players = geometry_end.get("players")
        end_players = end_players if isinstance(end_players, list) else []
        end_board_players = [
            item for item in end_players
            if isinstance(item, dict) and isinstance(item.get("boardStageCorners"), dict)
        ]
        end_player = end_board_players[0] if len(end_board_players) == 1 else None
        geometry_end_summary = {
            "board_detected": bool(end_board_players),
            "board_ambiguous": len(end_board_players) > 1,
            "board_client_mapping_method": (
                end_player.get("boardClientMappingMethod", "unavailable")
                if end_player else "ambiguous_or_unavailable"
            ),
            "board_client_corners": end_player.get("boardClientCorners") if end_player else None,
            "window_geometry": geometry_end.get("windowGeometry"),
        }

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
        "renderer_geometry": geometry_summary,
        "renderer_geometry_update_count": geometry_update_count,
        "renderer_geometry_at_end": geometry_end_summary,
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


# INT006R reuses the exact D1-D5 geometry while assigning a distinct scenario identity.
for _int006r_label, _int006_label in (
    ("INT-006R D1 — смешанные прямые", "INT-006 D1 — смешанные прямые"),
    ("INT-006R D2 — пятиугольник отдельными сторонами", "INT-006 D2 — пятиугольник отдельными сторонами"),
    ("INT-006R D3 — пересечения X, крест и T", "INT-006 D3 — пересечения X, крест и T"),
    ("INT-006R D4 — короткие детали", "INT-006 D4 — короткие детали"),
    ("INT-006R D5 — повторное покрытие", "INT-006 D5 — повторное покрытие"),
):
    _source_scenario = TEST_CASES[_int006_label]
    TEST_CASES[_int006r_label] = {
        **_source_scenario,
        "id": _source_scenario["id"].replace("int006_validation_", "int006r_validation_"),
        "description": f"INT006R cross-validation: {_source_scenario['description']}",
        "strokes": [
            {**stroke, "points": [list(point) for point in stroke["points"]]}
            for stroke in _source_scenario["strokes"]
        ],
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
    generation = {
        "method": "manual_brush_behavior_test",
        "test_case": scenario["id"],
        "brush_value_must_be_set_manually": True,
        "note": "Set the requested brush size in the browser before executing this plan.",
    }
    if scenario["id"] in PAIRED_RENDERER_TEST_CASE_IDS:
        generation["paired_renderer_capture"] = {
            "schema_version": 1,
            "scenario_id": scenario["id"],
            "requested_radius": PAIRED_RENDERER_REQUESTED_RADIUS,
            "expected_strokes": 1,
            "renderer_path_mode": PAIRED_RENDERER_PATH_MODE,
            "executor_parameters": dict(PAIRED_RENDERER_EXECUTOR_CONFIG),
        }
    return {
        "schema_version": 1,
        "name": f"Brush behavior test — {scenario['id']}",
        "created_at": now,
        "coordinate_system": coordinate_system,
        "canvas": {"width": width, "height": height},
        "width": width,
        "height": height,
        "strokes": strokes,
        "generation": generation,
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
        self._workflow_brush_ready_callback = None
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
        self._brush_feedback_state: dict[str, Any] | None = None
        self._brush_feedback_poll_id: str | None = None
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
        self._geometry_poll_after_id: str | None = None
        self.bridge_snippet_path: Path | None = None
        self.bridge_process: subprocess.Popen | None = None
        self.bridge_input_telemetry_requested = False
        self.last_record_path: Path | None = None
        self.brush_var = tk.StringVar(value="1")
        self.case_var = tk.StringVar(value="Расход краски — серия длинных линий")
        self.matrix_series_var = tk.StringVar(
            value=f"chalk-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        )
        self.matrix_block_var = tk.StringVar(value="1")
        self._chalk_matrix_metadata: dict[str, Any] | None = None
        self._chalk_experiment_matrix_metadata: dict[str, Any] | None = None
        self._experiment_id: str | None = None
        self.chalk_block_phase_var = tk.StringVar(value="G1")
        self.chalk_block_progress_var = tk.StringVar(value="Блок CHALK не запущен.")
        self._chalk_block_journal_path: Path | None = None
        self._chalk_block_owner_lock = None
        self._chalk_block_recovery_journal_path: Path | None = None
        self._chalk_block_recovery_scan_after_id: str | None = None
        self._chalk_block_task: dict[str, Any] | None = None
        self._chalk_block_stop_requested = False
        self._chalk_block_capture_poll_id: str | None = None
        self._chalk_block_clear_confirmed = False
        self._engine001_lab_session_id: str | None = None
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
        self.geometry_status_var = tk.StringVar(value="Геометрия доски: ожидание Game Monitor Bridge.")
        self.slider_start_var = tk.StringVar()
        self.slider_end_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Выбери радиус и тест. Автоустановка 1–30 работает только с расширенным ползунком игры.")
        self._build(parent)
        self._load_brush_control_into_fields()
        self._chalk_block_recovery_scan_after_id = self.root.after(0, self._scan_chalk_block_recovery)
        self._geometry_poll_after_id = self.root.after(500, self._poll_game_monitor_geometry)

    def _cancel_pending_chalk_block_recovery_scan(self) -> None:
        callback_id = getattr(self, "_chalk_block_recovery_scan_after_id", None)
        if callback_id is None:
            return
        try:
            self.root.after_cancel(callback_id)
        except (tk.TclError, ValueError):
            pass
        self._chalk_block_recovery_scan_after_id = None

    def _on_recovery_scan_owner_destroyed(self, event) -> None:
        if event.widget is getattr(self, "_recovery_scan_frame", None):
            self._cancel_pending_chalk_block_recovery_scan()
            self._cancel_pending_geometry_poll()

    def _cancel_pending_geometry_poll(self) -> None:
        callback_id = getattr(self, "_geometry_poll_after_id", None)
        if callback_id is None:
            return
        try:
            self.root.after_cancel(callback_id)
        except (tk.TclError, ValueError):
            pass
        self._geometry_poll_after_id = None

    def _poll_game_monitor_geometry(self) -> None:
        self._geometry_poll_after_id = None
        try:
            snapshot = read_active_bridge_geometry(self.output_dir / "game_monitor_bridge")
        except Exception as exc:
            snapshot = None
            message = f"Геометрия Game Monitor: ошибка чтения ({type(exc).__name__})."
        else:
            if snapshot is None:
                message = "Геометрия доски: нет активной сессии Bridge или renderer snapshot."
            elif snapshot.get("board_ambiguous"):
                message = "BoardPane: обнаружено несколько кандидатов; автоматическая геометрия заблокирована."
            elif not snapshot.get("board_detected"):
                message = "Game Monitor подключён, но BoardPane не обнаружен."
            elif not snapshot.get("board_client_corners"):
                message = "BoardPane обнаружен; client mapping недоступен. Используется ручной профиль калибровки."
            else:
                corners = snapshot["board_client_corners"]
                top_left = corners.get("topLeft") or corners.get("top_left") or {}
                bottom_right = corners.get("bottomRight") or corners.get("bottom_right") or {}
                window = snapshot.get("window_geometry") or {}
                screen_size = ""
                if window.get("screenWidth") and window.get("screenHeight"):
                    screen_size = f"; screen {window['screenWidth']}×{window['screenHeight']}"
                message = (
                    f"BoardPane: {snapshot.get('board_client_mapping_method')}; "
                    f"CSS client TL=({top_left.get('x', 0):.1f},{top_left.get('y', 0):.1f}), "
                    f"BR=({bottom_right.get('x', 0):.1f},{bottom_right.get('y', 0):.1f})"
                    f"{screen_size}. Это не desktop/screenshot mapping; executor продолжает использовать профиль калибровки."
                )
        try:
            self.geometry_status_var.set(message)
            if self._recovery_scan_frame.winfo_exists():
                self._geometry_poll_after_id = self.root.after(1000, self._poll_game_monitor_geometry)
        except tk.TclError:
            self._geometry_poll_after_id = None

    def _build(self, parent: tk.Widget) -> None:
        outer = ttk.Frame(parent, padding=10)
        self._recovery_scan_frame = outer
        outer.bind("<Destroy>", self._on_recovery_scan_owner_destroyed, add="+")
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
        ttk.Combobox(row, textvariable=self.case_var, values=tuple(TEST_CASES), state="readonly", width=42).pack(side="left", padx=6)
        matrix_row = ttk.Frame(controls)
        matrix_row.pack(fill="x", pady=(8, 0))
        ttk.Label(matrix_row, text="ID серии CHALK").pack(side="left")
        ttk.Entry(matrix_row, textvariable=self.matrix_series_var, width=28).pack(side="left", padx=(6, 16))
        ttk.Label(matrix_row, text="Блок / повтор (1–3)").pack(side="left")
        ttk.Entry(matrix_row, textvariable=self.matrix_block_var, width=4).pack(side="left", padx=6)
        ttk.Label(
            matrix_row,
            text="Для ручных G1/G2 номер повтора задаётся вручную. Автоматические блоки G1/G2/G3 назначают ячейки и порядок самостоятельно.",
        ).pack(side="left", padx=8)
        ttk.Label(controls, textvariable=self.area_var, wraplength=1100).pack(anchor="w", pady=(8, 0))
        slider = ttk.LabelFrame(controls, text="Автоматическая установка кисти", padding=6)
        slider.pack(fill="x", pady=(8, 0))
        ttk.Label(slider, text="Левый край 30 (X,Y)").pack(side="left")
        ttk.Entry(slider, textvariable=self.slider_start_var, width=12).pack(side="left", padx=4)
        ttk.Label(slider, text="Правый край 1 (X,Y)").pack(side="left", padx=(8, 0))
        ttk.Entry(slider, textvariable=self.slider_end_var, width=12).pack(side="left", padx=4)
        ttk.Button(slider, text="Установить кисть", command=self.set_brush_size).pack(side="left", padx=6)
        ttk.Label(slider, text="Слева радиус 30, справа радиус 1. Game Monitor автоматически проверяет и корректирует фактический радиус; мост должен быть подключён.", wraplength=410).pack(side="left", padx=6)

        bridge = ttk.LabelFrame(controls, text="Game Monitor WebSocket", padding=6)
        bridge.pack(fill="x", pady=(8, 0))
        ttk.Button(bridge, text="Запустить сокет", command=self.start_game_monitor_bridge).pack(side="left")
        ttk.Button(
            bridge, text="Копировать snippet подключения",
            command=self.copy_game_monitor_bridge_snippet,
        ).pack(side="left", padx=(6, 0))
        ttk.Button(
            bridge, text="Копировать game_monitor.js",
            command=self.copy_game_monitor_source,
        ).pack(side="left", padx=(6, 0))
        ttk.Label(
            bridge,
            text="Сначала запусти сокет, затем скопируй и выполни game_monitor.js, после него — snippet подключения в Console игрового iframe.",
            wraplength=760,
        ).pack(side="left", padx=8)
        ttk.Label(
            bridge, textvariable=self.geometry_status_var, wraplength=1100, justify="left"
        ).pack(fill="x", anchor="w", pady=(6, 0))
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

        block_controls = ttk.LabelFrame(outer, text="Автоматический блок CHALK — полный пакет тестов", padding=8)
        block_controls.pack(fill="x", pady=(0, 8))
        ttk.Label(block_controls, text="Фаза").pack(side="left")
        ttk.Combobox(
            block_controls, textvariable=self.chalk_block_phase_var,
            values=("G1", "G2", "G3", "V1", "V2", "V3", "V4", "V5", "INT006", "INT006R", "PRR"), state="readonly", width=10,
        ).pack(side="left", padx=(6, 10))
        ttk.Button(block_controls, text="Запустить полный блок", command=self.start_chalk_test_block).pack(side="left")
        ttk.Button(block_controls, text="Остановить после текущего опыта", command=self.request_stop_chalk_test_block).pack(side="left", padx=6)
        ttk.Button(block_controls, text="Восстановить прерванный блок", command=self.resume_interrupted_chalk_test_block).pack(side="left", padx=6)
        ttk.Button(block_controls, text="Закрыть приостановленный блок", command=self.close_paused_chalk_test_block).pack(side="left", padx=6)
        ttk.Label(block_controls, textvariable=self.chalk_block_progress_var, wraplength=650).pack(side="left", padx=10)

        # One operator action after the existing calibration and browser Bridge
        # bootstrap. The 9 attempts run in the existing locked CHALK state machine.
        lab = ttk.LabelFrame(outer, text="ENGINE-001 — чистая лаборатория", padding=8)
        lab.pack(fill="x", pady=(0, 8))
        ttk.Button(
            lab, text="Запустить лабораторию: 9 опытов (Clear)",
            command=self.start_engine001_lab,
        ).pack(side="left")
        ttk.Label(lab, text=(
            "3 направления × 3 повтора, один штрих на пустой доске. "
            "Требуются уже подключённые Monitor + Bridge с input telemetry, "
            "сохранённая калибровка и эталон пустой доски. "
            "Все опыты выполняются автоматически; Alt — остановка."
        ), wraplength=880).pack(side="left", padx=10)

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


    @staticmethod
    def normalize_game_monitor_origin(value: str) -> str | None:
        """Accept only a bare HTTPS origin copied from the game iframe."""
        raw = str(value).strip()
        if not raw or "?" in raw or "#" in raw:
            return None
        try:
            parsed = urlsplit(raw)
            _ = parsed.port
        except ValueError:
            return None
        if (
            parsed.scheme.lower() != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
            or any(character.isspace() for character in parsed.netloc)
        ):
            return None
        return raw.rstrip("/")

    def start_game_monitor_bridge(
        self, *, require_input_telemetry: bool | None = None,
    ) -> bool:
        """Launch the one shared Bridge, with an explicit FILL-001 opt-in mode.

        None preserves the existing brush-lab scenario-dependent behavior.
        True is required for FILL-001 V3; never silently reuse a Bridge that
        was started without input telemetry.
        """
        selected_scenario = TEST_CASES.get(self.case_var.get(), {})
        enable_input_telemetry = (
            bool(require_input_telemetry)
            if require_input_telemetry is not None else (
                isinstance(selected_scenario, dict)
                and selected_scenario.get("id") in PAIRED_RENDERER_TEST_CASE_IDS
            )
        )
        if self.bridge_process is not None and self.bridge_process.poll() is None:
            if enable_input_telemetry != self.bridge_input_telemetry_requested:
                expected_mode = (
                    "режим с обязательной input telemetry (FILL-001 V3 / paired-renderer)"
                    if enable_input_telemetry else "обычный режим без автоматического включения input telemetry"
                )
                messagebox.showwarning(
                    "Game Monitor Bridge уже запущен",
                    "Режим Bridge фиксируется при запуске. Для текущего выбранного сценария требуется: "
                    f"{expected_mode}. Останови текущий Bridge (Ctrl+C в окне сервера) и запусти его заново.",
                    parent=self.root,
                )
            else:
                messagebox.showinfo(
                    "Game Monitor Bridge",
                    "Совместимый мост уже запущен. Используйте действующий одноразовый snippet.",
                    parent=self.root,
                )
            return (
                enable_input_telemetry == self.bridge_input_telemetry_requested
            )
        origin_value = simpledialog.askstring(
            "Запуск Game Monitor WebSocket",
            "Вставь точный Origin игрового iframe. Получить его можно в Console iframe командой location.origin:",
            parent=self.root,
        )
        if not origin_value:
            return False
        origin = self.normalize_game_monitor_origin(origin_value)
        if origin is None:
            messagebox.showerror(
                "Некорректный Origin",
                "Нужен точный HTTPS Origin без пути, query и fragment. Скопируй location.origin именно из игрового iframe.",
                parent=self.root,
            )
            return False
        if platform.system() != "Windows":
            messagebox.showerror(
                "Недоступный запуск",
                "Кнопка запуска использует Windows .bat. На этой системе запусти game_monitor_bridge_server.py вручную.",
                parent=self.root,
            )
            return False

        if getattr(sys, "frozen", False):
            app_root = Path(sys.executable).resolve().parent
            bridge_dir = app_root / "game_monitor"
            working_directory = app_root
        else:
            app_root = Path(__file__).resolve().parents[2]
            bridge_dir = app_root / "source" / "game_monitor"
            working_directory = app_root.parent
        batch_path = bridge_dir / "start_game_monitor_bridge.bat"
        if not batch_path.is_file():
            messagebox.showerror(
                "Файл запуска не найден",
                f"Не найден файл:\n{batch_path}",
                parent=self.root,
            )
            return False

        snippet_dir = self.output_dir / "game_monitor_bridge"
        snippet_path = snippet_dir / f"connection_snippet_{uuid.uuid4().hex}.js"
        try:
            snippet_dir.mkdir(parents=True, exist_ok=True)
            snippet_path.unlink(missing_ok=True)
            self.bridge_process = subprocess.Popen(
                [
                    "cmd.exe", "/c", "call", str(batch_path),
                    origin, str(snippet_path), str(snippet_dir),
                    "true" if enable_input_telemetry else "false",
                ],
                cwd=str(working_directory),
                creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
            )
        except (OSError, subprocess.SubprocessError) as exc:
            messagebox.showerror(
                "Не удалось запустить WebSocket",
                str(exc),
                parent=self.root,
            )
            return False
        self.bridge_snippet_path = snippet_path
        self.bridge_input_telemetry_requested = enable_input_telemetry
        telemetry_mode = (
            "Для paired-renderer input telemetry включится автоматически после подключения snippet и восстановится при отключении Bridge. "
            if enable_input_telemetry else
            "Input telemetry автоматически не включается. "
        )
        self.status_var.set(
            telemetry_mode
            + "WebSocket запускается в отдельном окне. После появления сообщения о готовности скопируй snippet подключения."
        )
        return True

    def _copy_text_to_clipboard(self, content: str, success_message: str) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.root.update_idletasks()
        self.status_var.set(success_message)
        messagebox.showinfo("Буфер обмена", success_message, parent=self.root)

    def copy_game_monitor_bridge_snippet(self) -> None:
        """Copy the one-time-token snippet generated by the active local server."""
        path = self.bridge_snippet_path
        if path is None or not path.is_file():
            messagebox.showwarning(
                "Snippet пока не готов",
                "Сначала запусти WebSocket и дождись появления в его окне строки Listening и готового snippet. Затем повтори копирование.",
                parent=self.root,
            )
            return
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Ошибка чтения snippet", str(exc), parent=self.root)
            return
        if "__AUTODRAW_BRIDGE_TOKEN__" in content or "new WebSocket" not in content:
            messagebox.showerror(
                "Некорректный snippet",
                "Файл подключения не содержит готовый одноразовый токен. Перезапусти WebSocket.",
                parent=self.root,
            )
            return
        self._copy_text_to_clipboard(
            content,
            "Готовый snippet подключения скопирован. Не публикуй его: он содержит одноразовый секретный токен.",
        )

    def copy_game_monitor_source(self) -> None:
        """Copy the exact Game Monitor source shipped with this application."""
        if getattr(sys, "frozen", False):
            bridge_dir = Path(sys.executable).resolve().parent / "game_monitor"
        else:
            bridge_dir = Path(__file__).resolve().parents[1] / "game_monitor"
        path = bridge_dir / "game_monitor.js"
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            messagebox.showerror(
                "Не удалось прочитать game_monitor.js",
                f"{path}\n\n{exc}",
                parent=self.root,
            )
            return
        self._copy_text_to_clipboard(
            content,
            "Полный исходник game_monitor.js скопирован. Вставь его в Console игрового iframe первым.",
        )

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
        if scenario["id"] in PAIRED_RENDERER_TEST_CASE_IDS:
            lines.extend([
                "",
                "Профиль парного renderer capture (фиксированный):",
                "• Радиус кисти: 10 (создание плана блокируется при другом значении).",
                "• Исполнитель: point_step_px=2, point_delay_ms=10, line_extension_px=0.",
                "• Остальные параметры: before_mouse_down=20 ms, after_mouse_down=40 ms, "
                "after_mouse_up=20 ms, end_hold=50 ms, countdown=5 s.",
                "• Выбери этот paired-renderer сценарий до запуска кнопки «Запустить сокет»: Bridge автоматически включит input telemetry при подключении snippet и восстановит исходное состояние при отключении.",
                "• Если Bridge запущен вручную или в обычном режиме, включи input telemetry вручную в Console игрового iframe командой AutoDrawGameMonitor.setInputTelemetryEnabled(true).",
                "• До штриха и после него сохрани AutoDrawGameMonitor.status() с pointCount; "
                "после запуска также сохрани AutoDrawGameMonitor.inspect().",
                "• После одного запуска сохрани raw Game Monitor run JSON, session.json, "
                "AutoDrawGameMonitor.inspect(), pointCount до/после и PNG доски после штриха.",
                "• В offline renderer reference используй режим smooth и line width 10.",
                "• Replay будет принят только при одном strokeId, полном acceptedPoint-потоке и pointDelta=1.",
            ])
        self.template_text.configure(state="normal")
        self.template_text.delete("1.0", "end")
        self.template_text.insert("1.0", "\n".join(lines))
        self.template_text.configure(state="disabled")

    def _chalk_block_series_is_in_use(self, series_id: str) -> bool:
        for manifest_path in self.output_dir.rglob("experiment.json"):
            try:
                document = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            metadata = document.get("chalk_experiment_matrix") if isinstance(document, dict) else None
            if isinstance(metadata, dict) and metadata.get("series_id") == series_id:
                return True
        journal_root = self.output_dir / "chalk_test_blocks"
        if journal_root.is_dir():
            for journal_path in journal_root.glob("*.json"):
                try:
                    journal = load_chalk_test_block_journal(journal_path)
                except (OSError, ValueError, json.JSONDecodeError):
                    continue
                if journal.get("series_id") == series_id and journal.get("status") not in {"completed", "stopped"}:
                    return True
        return False

    def _scan_chalk_block_recovery(self) -> None:
        self._chalk_block_recovery_scan_after_id = None
        root = self.output_dir / "chalk_test_blocks"
        if not root.is_dir():
            return
        unresolved: list[Path] = []
        interrupted_details = None
        ownership_conflict = False
        for journal_path in sorted(root.glob("*.json")):
            try:
                journal = load_chalk_test_block_journal(journal_path)
            except (OSError, ValueError, json.JSONDecodeError):
                unresolved.append(journal_path)
                continue
            if journal.get("status") not in {"ready", "running", "paused", "failed"}:
                continue
            if self._chalk_block_owner_lock is not None:
                unresolved.append(journal_path)
                continue
            owner_lock = acquire_chalk_block_owner_lock(journal_path)
            if owner_lock is None:
                ownership_conflict = True
                unresolved.append(journal_path)
                continue
            if self._chalk_block_owner_lock is None:
                self._chalk_block_owner_lock = owner_lock
            else:
                release_chalk_block_owner_lock(owner_lock)
                unresolved.append(journal_path)
                continue
            if journal.get("status") == "running":
                try:
                    task = mark_interrupted_chalk_block_task(journal_path)
                    journal = load_chalk_test_block_journal(journal_path)
                    attempt = task.get("attempts", [])[-1] if task.get("attempts") else {}
                    interrupted_details = (
                        journal_path,
                        task.get("task_id"),
                        attempt.get("experiment_id"),
                        attempt.get("experiment_dir"),
                    )
                except (OSError, ValueError, RuntimeError):
                    unresolved.append(journal_path)
                    continue
            unresolved.append(journal_path)
        if interrupted_details:
            self._chalk_block_recovery_journal_path = interrupted_details[0]
        elif unresolved:
            self._chalk_block_recovery_journal_path = unresolved[0]
        if interrupted_details:
            path, task_id, experiment_id, experiment_dir = interrupted_details
            self.chalk_block_progress_var.set(f"Найден interrupted block: {task_id}; требуется ручная проверка доски.")
            messagebox.showwarning(
                "Обнаружен прерванный блок CHALK",
                f"Задача: {task_id}\nExperiment ID: {experiment_id or 'не зарегистрирован'}\n"
                f"Каталог: {experiment_dir or 'не создан'}\nЖурнал: {path}\n\n"
                "Автоматического повторного рисования не будет. Сначала вручную проверь игровую доску. "
                "После проверки можно явно разрешить новую попытку или закрыть блок.",
                parent=self.root,
            )
        elif unresolved and ownership_conflict:
            self.chalk_block_progress_var.set("Журнал CHALK используется другим экземпляром AutoDraw.")
            messagebox.showwarning(
                "Блок CHALK уже обслуживается",
                f"Журнал: {unresolved[0]}\nДругой экземпляр AutoDraw удерживает блокировку сеанса. "
                "Не запускай восстановление или второй блок одновременно.",
                parent=self.root,
            )
        elif unresolved:
            self.chalk_block_progress_var.set("Найден сохранённый/приостановленный блок; требуется явное восстановление или закрытие.")
            messagebox.showwarning(
                "Найден незавершённый блок CHALK",
                f"Журнал: {unresolved[0]}\nНовый блок не будет запущен параллельно. "
                "Используй восстановление, чтобы продолжить готовый журнал, либо закрой приостановленный блок.",
                parent=self.root,
            )

    def resume_interrupted_chalk_test_block(self) -> None:
        path = self._chalk_block_recovery_journal_path
        if path is None:
            self._scan_chalk_block_recovery()
            path = self._chalk_block_recovery_journal_path
        if path is None:
            messagebox.showinfo("Нет прерванного блока", "Журналов, требующих восстановления, не найдено.", parent=self.root)
            return
        if getattr(self, "_chalk_block_owner_lock", None) is None:
            owner_lock = acquire_chalk_block_owner_lock(path)
            if owner_lock is None:
                messagebox.showwarning(
                    "Блок уже обслуживается",
                    "Другой экземпляр AutoDraw удерживает этот журнал. Восстановление запрещено.",
                    parent=self.root,
                )
                return
            self._chalk_block_owner_lock = owner_lock
        try:
            journal = load_chalk_test_block_journal(path)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Не удалось прочитать журнал", str(exc), parent=self.root)
            return
        interrupted = [
            task for task in journal.get("tasks", [])
            if task.get("status") == "interrupted"
        ]
        if not interrupted and journal.get("status") == "ready":
            if not messagebox.askyesno(
                "Продолжить готовый блок",
                "В журнале есть ожидающие задачи без незавершённого запуска. AutoDraw продолжит блок с первой pending-задачи "
                "и перед рисованием автоматически очистит/проверит доску. Подтверждаешь, что это тестовая доска?",
                icon="warning",
                parent=self.root,
            ):
                return
            self._chalk_block_recovery_journal_path = None
            self._chalk_block_journal_path = path
            self._chalk_block_task = None
            self._chalk_block_stop_requested = False
            self._chalk_block_clear_confirmed = True
            self._start_next_chalk_block_task()
            return
        if len(interrupted) != 1:
            messagebox.showwarning(
                "Повтор не разрешён",
                "В журнале нет ровно одной interrupted-задачи. Failed-задачи нельзя автоматически повторять; закрой блок после проверки доски.",
                parent=self.root,
            )
            return
        task = interrupted[0]
        attempt = task.get("attempts", [])[-1] if task.get("attempts") else {}
        if not messagebox.askyesno(
            "Подтвердить проверку доски и повтор",
            f"Прерванная задача: {task['task_id']}\nКаталог частичного опыта: {attempt.get('experiment_dir') or 'не создан'}\n\n"
            "Ты вручную проверил состояние игровой доски и подтверждаешь, что AutoDraw может очистить её "
            "по эталону и выполнить эту задачу заново отдельной попыткой?",
            icon="warning",
            parent=self.root,
        ):
            return
        try:
            resolve_interrupted_chalk_block_task(
                path, task["task_id"], board_checked=True, decision="retry"
            )
        except (OSError, ValueError, RuntimeError) as exc:
            messagebox.showerror("Не удалось восстановить блок", str(exc), parent=self.root)
            return
        self._chalk_block_recovery_journal_path = None
        self._chalk_block_journal_path = path
        self._chalk_block_task = None
        self._chalk_block_stop_requested = False
        self._chalk_block_clear_confirmed = True
        self._start_next_chalk_block_task()

    def close_paused_chalk_test_block(self) -> None:
        path = self._chalk_block_recovery_journal_path
        if path is None:
            messagebox.showinfo("Нет приостановленного блока", "Журналов для закрытия не найдено.", parent=self.root)
            return
        if getattr(self, "_chalk_block_owner_lock", None) is None:
            owner_lock = acquire_chalk_block_owner_lock(path)
            if owner_lock is None:
                messagebox.showwarning(
                    "Блок уже обслуживается",
                    "Другой экземпляр AutoDraw удерживает этот журнал. Закрытие запрещено.",
                    parent=self.root,
                )
                return
            self._chalk_block_owner_lock = owner_lock
        if not messagebox.askyesno(
            "Закрыть приостановленный блок",
            "После проверки игровой доски блок будет окончательно закрыт без продолжения оставшихся задач. "
            "Все первичные попытки и журнал сохранятся. Продолжить?",
            icon="warning",
            parent=self.root,
        ):
            return
        try:
            journal = stop_chalk_test_block_journal(path, board_checked=True)
        except (OSError, ValueError, RuntimeError) as exc:
            messagebox.showerror("Не удалось закрыть блок", str(exc), parent=self.root)
            return
        self._chalk_block_recovery_journal_path = None
        owner_lock = getattr(self, "_chalk_block_owner_lock", None)
        if owner_lock is not None:
            release_chalk_block_owner_lock(owner_lock)
            self._chalk_block_owner_lock = None
        self.chalk_block_progress_var.set(
            f"{journal.get('phase_id')}: блок закрыт; первичные попытки сохранены."
        )
        self.status_var.set("Приостановленный блок закрыт. Его незавершённые задачи не будут запущены.")

    def _has_unresolved_chalk_block_journal(self) -> bool:
        root = self.output_dir / "chalk_test_blocks"
        if not root.is_dir():
            return False
        for journal_path in root.glob("*.json"):
            try:
                journal = load_chalk_test_block_journal(journal_path)
            except (OSError, ValueError, json.JSONDecodeError):
                return True
            if journal.get("status") in {"ready", "running", "paused", "failed"}:
                return True
        return False

    def _has_completed_g1_block(self) -> bool:
        root = self.output_dir / "chalk_test_blocks"
        if not root.is_dir():
            return False
        for journal_path in root.glob("*.json"):
            try:
                journal = load_chalk_test_block_journal(journal_path)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            if (
                journal.get("phase_id") == "G1"
                and journal.get("status") == "completed"
                and journal.get("expected_task_count") == 12
                and len(journal.get("tasks", [])) == 12
                and all(task.get("status") == "completed" for task in journal.get("tasks", []))
            ):
                return True
        return False

    def _has_completed_g2_block(self) -> bool:
        """Require one fully accepted G2 block before exposing G3 live execution."""
        journal_dir = self.output_dir / "chalk_test_blocks"
        if not journal_dir.is_dir():
            return False
        for journal_path in journal_dir.glob("chalk-block-G2-*.json"):
            try:
                journal = load_chalk_test_block_journal(journal_path)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            if (
                journal.get("phase_id") == "G2"
                and journal.get("status") == "completed"
                and journal.get("expected_task_count") == 18
                and len(journal.get("tasks", [])) == 18
                and all(task.get("status") == "completed" for task in journal.get("tasks", []))
            ):
                return True
        return False

    def _has_completed_v1_v5_blocks(self) -> bool:
        """Require accepted V1-V5 blocks before the independent model validation."""
        journal_dir = self.output_dir / "chalk_test_blocks"
        if not journal_dir.is_dir():
            return False
        for phase_id in ("V1", "V2", "V3", "V4", "V5"):
            expected = 9
            found = False
            for journal_path in journal_dir.glob(f"chalk-block-{phase_id}-*.json"):
                try:
                    journal = load_chalk_test_block_journal(journal_path)
                except (OSError, ValueError, json.JSONDecodeError):
                    continue
                if (
                    journal.get("phase_id") == phase_id
                    and journal.get("status") == "completed"
                    and journal.get("expected_task_count") == expected
                    and len(journal.get("tasks", [])) == expected
                    and all(task.get("status") == "completed" for task in journal.get("tasks", []))
                ):
                    found = True
                    break
            if not found:
                return False
        return True

    def start_engine001_lab(self) -> None:
        """One-button lab once the existing Monitor/Bridge bootstrap is ready."""
        if self._chalk_block_journal_path is not None or self._chalk_block_task is not None:
            messagebox.showwarning(
                "Другой блок активен", "Закрой или заверши предыдущий блок CHALK.",
                parent=self.root,
            )
            return
        try:
            ready = inspect_ready_bridge(self.output_dir / "game_monitor_bridge")
        except (ValueError, OSError) as exc:
            messagebox.showwarning("Лаборатория не готова", str(exc), parent=self.root)
            return
        self._engine001_lab_session_id = ready["session_id"]
        self.chalk_block_progress_var.set(
            "ENGINE-001: подключение подтверждено; проверка калибровки и запуск."
        )
        self.start_chalk_test_block(lab_one_click=True)

    def start_chalk_test_block(self, *, lab_one_click: bool = False) -> None:
        if self._chalk_block_task is not None or self._chalk_block_journal_path is not None:
            messagebox.showwarning("Блок уже активен", "Сначала заверши или останови текущий блок.", parent=self.root)
            return
        if not self._validate_automation_preflight():
            return
        if self._has_unresolved_chalk_block_journal():
            messagebox.showwarning(
                "Есть незавершённый блок CHALK",
                "Найден активный или приостановленный журнал. Сначала выполните recovery/разбор этого блока; параллельный запуск запрещён.",
                parent=self.root,
            )
            return
        phase_id = ENGINE001_PHASE if lab_one_click else self.chalk_block_phase_var.get().strip()
        if phase_id not in {"G1", "G2", "G3", "V1", "V2", "V3", "V4", "V5", "INT006", "INT006R", "PRR", ENGINE001_PHASE}:
            messagebox.showwarning("Неизвестная фаза", "Выбери G1/G2/G3, V1–V5, INT006, INT006R или PRR.", parent=self.root)
            return
        if phase_id == "G2" and not self._has_completed_g1_block():
            messagebox.showwarning(
                "G2 пока закрыта",
                "Сначала полностью выполни и прими автоматический блок G1. G2 нельзя запускать до завершения G1.",
                parent=self.root,
            )
            return
        if phase_id == "G3" and not self._has_completed_g2_block():
            messagebox.showwarning(
                "G3 пока закрыта",
                "Сначала полностью выполни и прими автоматический блок G2. G3 нельзя запускать до завершения G2.",
                parent=self.root,
            )
            return
        if phase_id == "INT006" and not self._has_completed_v1_v5_blocks():
            messagebox.showwarning(
                "INT006 пока закрыта",
                "Сначала должны быть полностью приняты блоки V1, V2, V3, V4 и V5. Независимую validation нельзя смешивать с незавершёнными геометрическими сериями.",
                parent=self.root,
            )
            return
        if platform.system() != "Windows":
            messagebox.showwarning(
                "Платформа не поддерживается",
                "Автоматический блок требует Windows для калиброванного перетаскивания ползунка кисти.",
                parent=self.root,
            )
            return
        brush_control = self.get_brush_control() if callable(self.get_brush_control) else None
        if (
            not isinstance(brush_control, dict)
            or brush_control.get("mode") != "slider"
            or not brush_control.get("start")
            or not brush_control.get("end")
        ):
            messagebox.showwarning(
                "Ползунок кисти не откалиброван",
                "До запуска блока требуется сохранённый профиль расширенного ползунка 1–30 с обеими крайними координатами.",
                parent=self.root,
            )
            return
        if self._read_live_brush_radius() is None:
            messagebox.showwarning(
                "Game Monitor не подключён",
                "Для автоматического блока нужен активный Game Monitor Bridge со свежим heartbeat.",
                parent=self.root,
            )
            return
        config = self.get_calibration_profile() if callable(self.get_calibration_profile) else None
        reference_path, metadata_path = self._blank_board_reference_paths()
        if not isinstance(config, dict) or not reference_path.is_file() or not metadata_path.is_file():
            messagebox.showwarning(
                "Подготовка блока не завершена",
                "Нужны сохранённый профиль калибровки и подтверждённый эталон пустой доски.",
                parent=self.root,
            )
            return
        points = config.get("points") if isinstance(config.get("points"), dict) else {}
        statuses = config.get("status") if isinstance(config.get("status"), dict) else {}
        point_status = statuses.get("points") if isinstance(statuses.get("points"), dict) else {}
        if not isinstance(points.get("clear_board"), dict) or point_status.get("clear_board") == "needs_review":
            messagebox.showwarning("Clear не откалиброван", "Проверь координату Clear на вкладке калибровки.", parent=self.root)
            return
        if not self.get_canvas_size():
            messagebox.showwarning("Нет области доски", "Сначала выбери область игрового холста.", parent=self.root)
            return
        series_id = self.matrix_series_var.get().strip()
        if self._chalk_block_series_is_in_use(series_id):
            messagebox.showwarning(
                "ID серии уже используется",
                "Для автоматического блока нужен новый ID серии без ранее сохранённых manifests или незавершённого журнала.",
                parent=self.root,
            )
            return
        try:
            block_plan = build_chalk_test_block_plan(
                series_id=series_id,
                phase_id=phase_id,
                repeats=2 if phase_id == "PRR" else 3,
            )
        except (TypeError, ValueError) as exc:
            messagebox.showerror("Неверные параметры блока", str(exc), parent=self.root)
            return
        # The explicit ENGINE-001 button is the single consent action.
        # No second confirmation, but all calibration/Bridge checks remain.
        if not lab_one_click and not messagebox.askyesno(
            "Подтвердить автоматический блок",
            f"Будет выполнено {block_plan['expected_task_count']} экспериментов фазы {phase_id}, "
            "каждый на тестовой доске. AutoDraw будет автоматически нажимать Clear между опытами. "
            "Убедись, что текущий рисунок можно удалить. При любой ошибке блок остановится без пропуска теста. Продолжить?",
            icon="warning",
            parent=self.root,
        ):
            return
        journal_dir = self.output_dir / "chalk_test_blocks"
        journal_path = journal_dir / (
            f"chalk-block-{phase_id}-{series_id}-{block_plan['block_id'][:8]}.json"
        )
        owner_lock = acquire_chalk_block_owner_lock(journal_path)
        if owner_lock is None:
            messagebox.showwarning(
                "Блок уже обслуживается",
                "Другой экземпляр AutoDraw уже владеет этим журналом. Параллельный запуск запрещён.",
                parent=self.root,
            )
            return
        try:
            create_chalk_test_block_journal(journal_path, block_plan)
        except (OSError, ValueError) as exc:
            release_chalk_block_owner_lock(owner_lock)
            messagebox.showerror("Не удалось создать журнал блока", str(exc), parent=self.root)
            return
        self._chalk_block_owner_lock = owner_lock
        self._chalk_block_journal_path = journal_path
        self._chalk_block_task = None
        self._chalk_block_stop_requested = False
        self._chalk_block_clear_confirmed = True
        self.status_var.set("Журнал полного блока сохранён до первого действия мышью.")
        self._update_chalk_block_progress()
        self._start_next_chalk_block_task()

    def request_stop_chalk_test_block(self) -> None:
        if self._chalk_block_journal_path is None:
            self.status_var.set("Активного блока CHALK нет.")
            return
        self._chalk_block_stop_requested = True
        self.status_var.set("Остановка запрошена: текущий опыт будет доведён до безопасной границы; следующий не начнётся.")
        if self._chalk_block_task is None:
            try:
                stop_chalk_test_block_journal(self._chalk_block_journal_path)
            except (OSError, ValueError, RuntimeError) as exc:
                self._chalk_block_recovery_journal_path = self._chalk_block_journal_path
                self.status_var.set(f"Не удалось остановить блок: {exc}. Журнал сохранён для восстановления.")
                self._update_chalk_block_progress()
                self._clear_chalk_block_runtime()
                return
            self._update_chalk_block_progress()
            self._chalk_block_recovery_journal_path = None
            self._clear_chalk_block_runtime()
    
    def _clear_chalk_block_runtime(self) -> None:
        if self._chalk_block_capture_poll_id is not None:
            try:
                self.root.after_cancel(self._chalk_block_capture_poll_id)
            except (tk.TclError, ValueError):
                pass
            self._chalk_block_capture_poll_id = None
        self._chalk_block_journal_path = None
        self._chalk_block_task = None
        owner_lock = getattr(self, "_chalk_block_owner_lock", None)
        if owner_lock is not None:
            release_chalk_block_owner_lock(owner_lock)
            self._chalk_block_owner_lock = None
        self._chalk_block_clear_confirmed = False
        self._chalk_block_stop_requested = False

    def _update_chalk_block_progress(self) -> None:
        if self._chalk_block_journal_path is None:
            return
        try:
            journal = load_chalk_test_block_journal(self._chalk_block_journal_path)
            progress = chalk_test_block_progress(journal)
            current = self._chalk_block_task.get("scenario_id") if self._chalk_block_task else "—"
            self.chalk_block_progress_var.set(
                f"{journal.get('phase_id')}: {progress['completed']}/{progress['total']} завершено; "
                f"текущий: {current}; осталось: {progress['pending']}; статус: {progress['status']}"
            )
        except (OSError, ValueError, KeyError):
            self.chalk_block_progress_var.set("Не удалось прочитать журнал блока.")

    def _start_next_chalk_block_task(self) -> None:
        if self._chalk_block_journal_path is None:
            return
        if self._chalk_block_stop_requested:
            try:
                stop_chalk_test_block_journal(self._chalk_block_journal_path)
            except (OSError, ValueError, RuntimeError) as exc:
                self._fail_chalk_test_block(f"safe_stop_failed:{exc}")
                return
            self._update_chalk_block_progress()
            self.status_var.set("Блок остановлен на границе опыта.")
            self._chalk_block_recovery_journal_path = None
            self._clear_chalk_block_runtime()
            return
        try:
            task = claim_next_chalk_block_task(self._chalk_block_journal_path)
        except (OSError, ValueError, RuntimeError) as exc:
            self._fail_chalk_test_block(f"task_claim_failed:{exc}")
            return
        if task is None:
            journal = load_chalk_test_block_journal(self._chalk_block_journal_path)
            self._update_chalk_block_progress()
            if journal.get("status") == "completed":
                self.status_var.set(f"Блок {journal.get('phase_id')} завершён: все опыты приняты.")
                self._show_chalk_block_completion_notification(journal)
                self.matrix_series_var.set(
                    f"chalk-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
                )
                self._chalk_block_recovery_journal_path = None
                self._clear_chalk_block_runtime()
            else:
                self._fail_chalk_test_block(f"block_not_complete:{journal.get('status')}")
            return
        if task.get("scenario_id") in {
            "engine001_horizontal_endpoint", "engine001_vertical_axis",
            "engine001_diagonal_axis",
        }:
            try:
                fresh = inspect_ready_bridge(self.output_dir / "game_monitor_bridge")
                if fresh["session_id"] != self._engine001_lab_session_id:
                    raise ValueError("В лаборатории изменилась browser Bridge session.")
            except (ValueError, OSError) as exc:
                self._chalk_block_task = task
                self._fail_chalk_test_block(f"lab_bridge_gate:{exc}")
                return
        self._chalk_block_task = task
        self.experiment_dir = None
        self.experiment_phases = {}
        self._experiment_id = None
        self.execution_report = None
        self.execution_report_path = None
        self.game_monitor_summary = None
        self.game_monitor_report_path = None
        label = next(
            (name for name, details in TEST_CASES.items() if details.get("id") == task.get("scenario_id")),
            None,
        )
        if label is None:
            self._fail_chalk_test_block("scenario_not_available_in_brush_test_ui")
            return
        self.case_var.set(label)
        self.brush_var.set(str(task.get("requested_radius", 10)))
        self.matrix_series_var.set(load_chalk_test_block_journal(self._chalk_block_journal_path)["series_id"])
        self.matrix_block_var.set(str(task["repeat_index"]))
        self._update_chalk_block_progress()
        self.create_and_transfer_plan()

    def _show_chalk_block_completion_notification(self, journal: dict[str, Any]) -> None:
        """Bring the UI forward and explicitly notify the operator after all block tasks are accepted."""
        phase = str(journal.get("phase_id", "CHALK"))
        tasks = journal.get("tasks", [])
        total = int(journal.get("expected_task_count", len(tasks)))
        completed = sum(1 for task in tasks if isinstance(task, dict) and task.get("status") == "completed")
        try:
            self.root.deiconify()
            self.root.lift()
        except tk.TclError:
            pass
        try:
            messagebox.showinfo(
                f"Блок {phase} завершён",
                f"Принято опытов: {completed}/{total}.\nЖурнал блока и результаты сохранены.",
                parent=self.root,
            )
        except tk.TclError:
            self.status_var.set(f"Блок {phase} завершён: принято {completed}/{total} опытов.")

    def _fail_chalk_test_block(self, reason: str) -> None:
        if self._chalk_block_journal_path is not None and self._chalk_block_task is not None:
            try:
                finish_chalk_block_task(
                    self._chalk_block_journal_path,
                    self._chalk_block_task["task_id"],
                    accepted=False,
                    experiment_id=self._experiment_id,
                    experiment_dir=self.experiment_dir,
                    reason=reason,
                )
            except (OSError, ValueError, RuntimeError):
                pass
        if self._chalk_block_journal_path is not None:
            self._chalk_block_recovery_journal_path = self._chalk_block_journal_path
        self.status_var.set(f"Блок CHALK приостановлен без пропуска теста: {reason}")
        self._update_chalk_block_progress()
        self._clear_chalk_block_runtime()

    def _wait_for_chalk_block_capture(self, attempt: int = 0) -> None:
        self._chalk_block_capture_poll_id = None
        if self._chalk_block_journal_path is None or self._chalk_block_task is None:
            return
        capture = self.experiment_phases.get("monitor_capture", {})
        if isinstance(capture, dict) and capture.get("status") == "saved":
            manifest_path = self.experiment_dir / "experiment.json" if self.experiment_dir else None
            if manifest_path is None:
                self._fail_chalk_test_block("experiment_manifest_missing")
                return
            try:
                journal = load_chalk_test_block_journal(self._chalk_block_journal_path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                self._fail_chalk_test_block(f"block_journal_unavailable_during_acceptance:{exc}")
                return
            journal_task = next(
                (item for item in journal.get("tasks", [])
                 if item.get("task_id") == self._chalk_block_task.get("task_id")),
                None,
            )
            if not isinstance(journal_task, dict) or journal_task.get("status") != "running":
                self._fail_chalk_test_block("active_block_task_missing_from_journal")
                return
            active_attempt_id = journal_task.get("active_attempt_id")
            active_attempt = next(
                (item for item in reversed(journal_task.get("attempts", []))
                 if item.get("attempt_id") == active_attempt_id),
                None,
            )
            if not isinstance(active_attempt, dict):
                self._fail_chalk_test_block("active_block_attempt_missing_from_journal")
                return
            accepted, reason, _record = validate_chalk_block_experiment(
                manifest_path,
                expected_task=journal_task,
                expected_block=journal,
                expected_experiment_id=active_attempt.get("experiment_id"),
                expected_experiment_dir=active_attempt.get("experiment_dir"),
            )
            if not accepted:
                self._fail_chalk_test_block(reason)
                return
            if journal.get("phase_id") == ENGINE001_PHASE:
                try:
                    audit = audit_single_capture(self.experiment_dir)
                    if audit.get("status") != "PASS_E4_RAW_CAPTURE":
                        self._fail_chalk_test_block(
                            "lab_raw_capture_rejected:" + ",".join(audit.get("reasons", []))
                        )
                        return
                    if audit.get("session_id") != self._engine001_lab_session_id:
                        self._fail_chalk_test_block("lab_bridge_session_changed")
                        return
                except (OSError, ValueError, TypeError, KeyError) as exc:
                    self._fail_chalk_test_block(f"lab_audit_error:{exc}")
                    return
            try:
                finish_chalk_block_task(
                    self._chalk_block_journal_path,
                    self._chalk_block_task["task_id"],
                    accepted=True,
                    experiment_id=self._experiment_id,
                    experiment_dir=self.experiment_dir,
                )
            except (OSError, ValueError, RuntimeError) as exc:
                self._fail_chalk_test_block(f"journal_finish_failed:{exc}")
                return
            self._chalk_block_task = None
            self._update_chalk_block_progress()
            self.status_var.set("Опыт принят: точный CHALK и полный per-stroke breakdown подтверждены.")
            self._start_next_chalk_block_task()
            return
        if attempt >= 60:
            self._fail_chalk_test_block(
                f"monitor_capture_gate_timeout:{capture.get('status', 'missing') if isinstance(capture, dict) else 'invalid'}"
            )
            return
        self._chalk_block_capture_poll_id = self.root.after(
            500, lambda: self._wait_for_chalk_block_capture(attempt + 1)
        )

    def _on_chalk_block_restore_finished(self, restore_status: str) -> None:
        if self._chalk_block_journal_path is None or self._chalk_block_task is None:
            return
        if restore_status != "drag_completed_unverified":
            self._fail_chalk_test_block(f"brush_restore_{restore_status}")
            return
        self.status_var.set("Перетаскивание кисти завершено. Проверяю точный CHALK и телеметрию перед следующим опытом…")
        self._wait_for_chalk_block_capture()

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
            if self._chalk_block_task is not None:
                self._fail_chalk_test_block("automation_preflight_failed")
            return
        canvas_size = self.get_canvas_size()
        if not canvas_size:
            if self._chalk_block_task is not None:
                self._fail_chalk_test_block("canvas_area_unavailable")
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
            scenario_id = plan["generation"].get("test_case")
            active_bridge_process = getattr(self, "bridge_process", None)
            bridge_running = active_bridge_process is not None and active_bridge_process.poll() is None
            if (
                scenario_id in PAIRED_RENDERER_TEST_CASE_IDS
                and bridge_running
                and not getattr(self, "bridge_input_telemetry_requested", False)
            ):
                raise ValueError(
                    "Для paired-renderer нужен Bridge, запущенный после выбора этого сценария: "
                    "он должен автоматически включить input telemetry. Останови Bridge и запусти его заново."
                )
            if scenario_id in PAIRED_RENDERER_TEST_CASE_IDS and brush != PAIRED_RENDERER_REQUESTED_RADIUS:
                raise ValueError(
                    "Для парного renderer capture требуется радиус кисти 10. "
                    "Установи 10 в поле «Радиус кисти» и создай план повторно."
                )
            self.output_dir.mkdir(parents=True, exist_ok=True)
            experiment_id = uuid.uuid4().hex
            plan["generation"]["experiment_id"] = experiment_id
            path = self.output_dir / (
                f"brush-plan-{plan['generation']['test_case']}-b{brush}-"
                f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{experiment_id[:8]}.json"
            )
            plan["generation"]["requested_brush_value"] = brush
            matrix_metadata = None
            experiment_matrix_metadata = None
            scenario_id = plan["generation"].get("test_case")
            if _is_legacy_chalk_radius_matrix_run(scenario_id, self._chalk_block_task):
                matrix_metadata = build_chalk_radius_matrix_metadata(
                    series_id=self.matrix_series_var.get(),
                    block=int(self.matrix_block_var.get().strip()),
                    requested_radius=brush,
                )
                plan["generation"]["chalk_radius_matrix"] = matrix_metadata
            elif scenario_id in GEOMETRY_MATRIX_SCENARIOS:
                if PHASE_BY_SCENARIO.get(scenario_id) in {
                    INDEPENDENT_VALIDATION_PHASE, RADIUS_GEOMETRY_VALIDATION_PHASE
                } and self._chalk_block_task is None:
                    raise ValueError("D1–D5 validation разрешено запускать только через полный автоматический блок соответствующей фазы.")
                if scenario_id in {
                    "paired_renderer_vertical_single_stroke",
                    "paired_renderer_diagonal_single_stroke",
                    "paint_consumption_long_lines",
                    "int006_diagonals",
                    "int006_short_strokes",
                    "int006_turns",
                    "int006_closed_contours",
                    "int006_intersections_spacing",
                    "int006r_validation_d1_mixed_lines",
                    "int006r_validation_d2_polygon",
                    "int006r_validation_d3_intersections",
                    "int006r_validation_d4_short_details",
                    "int006r_validation_d5_repeated_coverage",
                } and self._chalk_block_task is None:
                    raise ValueError(
                        "G3 и V1–V5 разрешено запускать только полными автоматическими блоками. "
                        "Отдельные ручные опыты запрещены, чтобы не обходить порядок и матрицу повторов."
                    )
                series_id = self.matrix_series_var.get()
                repeat_index = int(self._chalk_block_task["repeat_index"]) if self._chalk_block_task else int(self.matrix_block_var.get().strip())
                if self._chalk_block_task is not None:
                    experiment_matrix_metadata = build_chalk_experiment_matrix_metadata(
                        series_id=series_id,
                        scenario_id=scenario_id,
                        repeat_index=repeat_index,
                        requested_radius=brush,
                        strokes=plan["strokes"],
                        matrix_order_index=int(self._chalk_block_task["matrix_order_index"]),
                        executor_parameters=self._chalk_block_task.get("executor_parameters"),
                        prediction_id=self._chalk_block_task.get("prediction_id"),
                    )
                    plan["generation"]["chalk_test_block"] = {
                        "block_id": load_chalk_test_block_journal(self._chalk_block_journal_path)["block_id"],
                        "task_id": self._chalk_block_task["task_id"],
                        "phase_id": load_chalk_test_block_journal(self._chalk_block_journal_path)["phase_id"],
                    }
                else:
                    series_state = inspect_chalk_matrix_series(
                        self.output_dir,
                        series_id=series_id,
                        scenario_id=scenario_id,
                        repeat_index=repeat_index,
                    )
                    duplicate_path = series_state["duplicate_manifest_path"]
                    if duplicate_path:
                        raise ValueError(
                            f"Повтор {repeat_index} для сценария {scenario_id} уже сохранён в этой серии: "
                            f"{duplicate_path}. Выбери другой номер повтора (1–3) или новый ID серии."
                        )
                    experiment_matrix_metadata = build_chalk_experiment_matrix_metadata(
                        series_id=series_id,
                        scenario_id=scenario_id,
                        repeat_index=repeat_index,
                        requested_radius=brush,
                        strokes=plan["strokes"],
                        matrix_order_index=series_state["next_matrix_order_index"],
                    )
                plan["generation"]["chalk_experiment_matrix"] = experiment_matrix_metadata
            path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
            self.current_plan = plan
            self.current_plan_path = path
            self._experiment_id = experiment_id
            self._chalk_matrix_metadata = matrix_metadata
            self._chalk_experiment_matrix_metadata = experiment_matrix_metadata
            if not self.on_transfer_plan(plan, path):
                if self._chalk_block_task is not None:
                    self._fail_chalk_test_block("executor_plan_transfer_failed")
                return
            self._reset_observation_fields()
            self._start_automated_preclear()
        except (OSError, ValueError, TypeError) as exc:
            if self._chalk_block_task is not None:
                self._fail_chalk_test_block(f"plan_creation_failed:{exc}")
            messagebox.showerror("Не удалось создать тестовый план", str(exc), parent=self.root)

    def _reset_observation_fields(self) -> None:
        """Prevent evidence from a previous run being attached to a new test plan."""
        self._experiment_requested_brush = int(self.brush_var.get().strip())
        self._experiment_id = getattr(self, "_experiment_id", None) or uuid.uuid4().hex
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

    def set_brush_size_for_workflow(self, brush: int, on_verified) -> bool:
        """Reuse the verified drag/heartbeat state machine for a separate experiment runner."""
        if not callable(on_verified):
            raise ValueError("Для автоматического запуска требуется callback подтверждения радиуса.")
        if self._workflow_brush_ready_callback is not None or self._start_executor_after_brush_drag:
            raise RuntimeError("Другой автоматический запуск кисти уже ожидает подтверждения.")
        self.brush_var.set(str(int(brush)))
        self._workflow_brush_ready_callback = on_verified
        self._start_executor_after_brush_drag = True
        if not self.set_brush_size():
            self._workflow_brush_ready_callback = None
            self._start_executor_after_brush_drag = False
            return False
        return True

    def set_brush_size(self) -> bool:
        """Set brush size only by dragging the calibrated extended-mode slider."""
        try:
            if (
                getattr(self, "_brush_feedback_state", None) is not None
                or self._brush_drag_state is not None
                or self._brush_drag_countdown_id is not None
            ):
                raise RuntimeError("Установка или проверка кисти уже выполняется.")
            brush = int(self.brush_var.get().strip())
            if not 1 <= brush <= 30:
                raise ValueError("Размер кисти должен быть целым числом от 1 до 30.")
            if platform.system() != "Windows":
                raise RuntimeError("Автоматическая установка кисти доступна только в Windows.")
            if self._read_live_brush_radius() is None:
                raise RuntimeError(
                    "Для автоматической коррекции требуется активный Game Monitor Bridge. "
                    "Подключи мост в игровом iframe и дождись свежего heartbeat."
                )
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
            self._brush_feedback_state = {
                "requested_radius": brush,
                "start_30": start,
                "end_1": end,
                "high_point": start,
                "high_radius": 30,
                "low_point": end,
                "low_radius": 1,
                "current_point": (x, y),
                "attempt": 0,
                "poll_count": 0,
                "observations": [],
            }
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
        if (
            self._brush_drag_state is not None
            or self._brush_drag_countdown_id is not None
            or getattr(self, "_brush_feedback_state", None) is not None
        ):
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
            self._brush_drag_purpose = "set_brush_size"
            if purpose == "restore_brush_30":
                self._record_brush_restore_result("stopped", "Alt отменил возврат кисти до начала перетаскивания.")
                return
            if getattr(self, "_brush_feedback_state", None) is not None:
                self._fail_brush_radius_feedback(
                    "cancelled_by_user", "Проверка/установка радиуса отменена по Alt."
                )
                return
            self.status_var.set("Установка кисти отменена по Alt до начала перетаскивания.")
            try:
                self.root.deiconify()
                self.root.lift()
            except tk.TclError:
                pass
            return
        if self._brush_drag_state is not None:
            self._finish_brush_drag(cancelled=True)
            return
        if getattr(self, "_brush_feedback_state", None) is not None:
            self._fail_brush_radius_feedback(
                "cancelled_by_user", "Проверка радиуса отменена по Alt."
            )

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
        feedback = getattr(self, "_brush_feedback_state", None)
        if purpose in {"set_brush_size", "correct_brush_size"} and feedback is not None and state:
            if cancelled or error or release_error:
                self._fail_brush_radius_feedback(
                    "drag_cancelled" if cancelled else "drag_failed",
                    error or release_error or "Перетаскивание отменено.",
                )
            else:
                feedback["current_point"] = tuple(state["target"])
                feedback["await_after_utc"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
                feedback["poll_count"] = 0
                feedback.pop("last_status_timestamp", None)
                feedback.pop("candidate_radius", None)
                feedback["stable_status_count"] = 0
                self.status_var.set(
                    f"Положение для радиуса {feedback['requested_radius']} установлено. "
                    "Проверяю фактическое значение Game Monitor…"
                )
                self._start_brush_hotkey_listener()
                self._brush_feedback_poll_id = self.root.after(250, self._poll_brush_radius_feedback)
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
        if cancelled or error or release_error:
            try:
                self.root.deiconify()
                self.root.lift()
            except tk.TclError:
                pass

    def _read_live_brush_radius(self, *, after_utc: str | None = None) -> dict[str, Any] | None:
        """Read the active bridge heartbeat from the shared feedback helper."""
        return read_active_bridge_radius(
            self.output_dir / "game_monitor_bridge",
            after_utc=after_utc,
        )

    def _poll_brush_radius_feedback(self) -> None:
        """Wait for a post-drag heartbeat, then correct the slider until the game reports the target."""
        self._brush_feedback_poll_id = None
        feedback = self._brush_feedback_state
        if not isinstance(feedback, dict):
            return
        observation = self._read_live_brush_radius(after_utc=feedback.get("await_after_utc"))
        if observation is None:
            feedback["poll_count"] = int(feedback.get("poll_count", 0)) + 1
            if feedback["poll_count"] >= 48:
                self._fail_brush_radius_feedback(
                    "monitor_unavailable",
                    "Нет свежего heartbeat Game Monitor после отпускания ползунка. "
                    "Проверь подключение Game Monitor Bridge.",
                )
                return
            self._brush_feedback_poll_id = self.root.after(250, self._poll_brush_radius_feedback)
            return

        stamp = observation.get("observed_at_utc")
        if stamp != feedback.get("last_status_timestamp"):
            feedback["last_status_timestamp"] = stamp
            observed_candidate = int(observation["radius"])
            if feedback.get("candidate_radius") == observed_candidate:
                feedback["stable_status_count"] = int(feedback.get("stable_status_count", 1)) + 1
            else:
                feedback["candidate_radius"] = observed_candidate
                feedback["stable_status_count"] = 1
        if int(feedback.get("stable_status_count", 0)) < 2:
            self._brush_feedback_poll_id = self.root.after(250, self._poll_brush_radius_feedback)
            return

        requested = int(feedback["requested_radius"])
        observed = int(observation["radius"])
        feedback.setdefault("observations", []).append({
            "requested_radius": requested,
            "observed_radius": observed,
            "observed_at_utc": observation["observed_at_utc"],
            "session_id": observation["session_id"],
            "position": list(feedback["current_point"]),
        })
        if observed == requested:
            self._complete_brush_radius_feedback(observation)
            return

        attempt = int(feedback.get("attempt", 0))
        if attempt >= 7:
            self._fail_brush_radius_feedback(
                "correction_limit_reached",
                f"После {attempt + 1} проверок игра сообщает радиус {observed}, "
                f"а запрошен {requested}.",
            )
            return

        current_point = tuple(feedback["current_point"])
        if observed > requested:
            feedback["high_point"] = current_point
            feedback["high_radius"] = observed
        else:
            feedback["low_point"] = current_point
            feedback["low_radius"] = observed
        try:
            target = calculate_radius_correction_target(
                feedback["high_point"], int(feedback["high_radius"]),
                feedback["low_point"], int(feedback["low_radius"]), requested,
            )
        except (TypeError, ValueError) as exc:
            self._fail_brush_radius_feedback("correction_calculation_failed", str(exc))
            return
        if target == current_point:
            self._fail_brush_radius_feedback(
                "correction_has_no_progress",
                "Координатного разрешения ползунка недостаточно для следующей коррекции.",
            )
            return

        feedback["attempt"] = attempt + 1
        self.status_var.set(
            f"Game Monitor показывает {observed} вместо {requested}. "
            f"Автоматическая коррекция {feedback['attempt']}/7…"
        )
        self._brush_drag_purpose = "correct_brush_size"
        try:
            self.root.iconify()
            self._start_brush_hotkey_listener()
            self._begin_brush_drag(current_point, target[0], target[1], requested)
        except Exception as exc:
            self._fail_brush_radius_feedback("correction_drag_failed", str(exc))

    def _complete_brush_radius_feedback(self, observation: dict[str, Any]) -> None:
        feedback = self._brush_feedback_state
        if not isinstance(feedback, dict):
            return
        requested = int(feedback["requested_radius"])
        phase = {
            "status": "verified_by_game_monitor",
            "requested_value": requested,
            "observed_value": int(observation["radius"]),
            "verification_source": "active_game_monitor_bridge_heartbeat",
            "session_id": observation.get("session_id"),
            "verified_at_utc": observation.get("observed_at_utc"),
            "final_position": list(feedback["current_point"]),
            "correction_count": int(feedback.get("attempt", 0)),
            "observations": list(feedback.get("observations", [])),
        }
        workflow_mode = callable(self._workflow_brush_ready_callback)
        if not workflow_mode:
            self.experiment_phases["brush_setup"] = phase
        self._stop_brush_hotkey_listener()
        if not workflow_mode and self.experiment_dir is not None:
            try:
                self._write_experiment_manifest()
            except (OSError, ValueError, TypeError) as exc:
                self._fail_brush_radius_feedback(
                    "manifest_write_failed",
                    f"Игра подтвердила радиус, но манифест не сохранён: {exc}",
                )
                return
        self._brush_feedback_state = None
        # Keep AutoDraw minimized during automated block handoff: restoring this
        # window would steal focus from the game immediately before Stage6 starts.
        if not self._start_executor_after_brush_drag:
            try:
                self.root.deiconify()
                self.root.lift()
            except tk.TclError:
                pass
        self.status_var.set(
            f"Фактический радиус {requested} подтверждён Game Monitor. "
            f"Коррекций выполнено: {phase['correction_count']}."
        )
        state = {
            "start": feedback["start_30"],
            "target": feedback["current_point"],
            "brush": requested,
        }
        if self._start_executor_after_brush_drag:
            self._start_executor_after_brush_drag = False
            self._confirm_brush_before_test(requested, state, observation)
        else:
            messagebox.showinfo(
                "Кисть установлена",
                f"Game Monitor подтвердил фактический радиус {requested}.",
                parent=self.root,
            )

    def _fail_brush_radius_feedback(self, reason: str, detail: str) -> None:
        feedback = self._brush_feedback_state
        if self._brush_feedback_poll_id is not None:
            try:
                self.root.after_cancel(self._brush_feedback_poll_id)
            except (tk.TclError, ValueError):
                pass
            self._brush_feedback_poll_id = None
        self._brush_feedback_state = None
        self._stop_brush_hotkey_listener()
        workflow_mode = callable(self._workflow_brush_ready_callback)
        self._start_executor_after_brush_drag = False
        self._workflow_brush_ready_callback = None
        phase = {
            "status": "verification_failed",
            "reason": reason,
            "detail": detail,
            "requested_value": feedback.get("requested_radius") if isinstance(feedback, dict) else None,
            "observations": list(feedback.get("observations", [])) if isinstance(feedback, dict) else [],
            "failed_at_utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        }
        if not workflow_mode:
            self.experiment_phases["brush_setup"] = phase
            if self.experiment_dir is not None:
                try:
                    self._write_experiment_manifest()
                except (OSError, ValueError, TypeError):
                    pass
        try:
            self.root.deiconify()
            self.root.lift()
        except tk.TclError:
            pass
        self.status_var.set(
            f"Автоустановка кисти не подтверждена: {detail} Исполнитель не запущен."
        )
        if self._chalk_block_task is not None:
            self._fail_chalk_test_block(f"brush_radius_feedback_{reason}:{detail}")
        messagebox.showwarning(
            "Не удалось подтвердить размер кисти",
            f"{detail}\n\nПроверь Game Monitor Bridge и профиль ползунка. "
            "Рисование не запускалось.",
            parent=self.root,
        )

    def _confirm_brush_before_test(
        self, brush: int, state: dict[str, Any], observation: dict[str, Any]
    ) -> None:
        """Continue automatically after an exact, fresh Game Monitor radius match."""
        workflow_callback = self._workflow_brush_ready_callback
        workflow_mode = callable(workflow_callback)
        phase = {} if workflow_mode else self.experiment_phases.setdefault("brush_setup", {})
        if int(observation.get("radius", -1)) != int(brush):
            self._fail_brush_radius_feedback(
                "monitor_radius_mismatch_at_handoff",
                f"Game Monitor сообщил радиус {observation.get('radius')}, ожидался {brush}.",
            )
            return
        phase["status"] = (
            "confirmed_by_monitor_for_automated_block"
            if self._chalk_block_task is not None
            else "verified_by_game_monitor"
        )
        phase["verification_source"] = "active_game_monitor_bridge_heartbeat"
        phase["visual_confirmation_required"] = False
        phase["confirmed_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if not workflow_mode and self.experiment_dir is not None:
            try:
                self._write_experiment_manifest()
            except (OSError, ValueError, TypeError) as exc:
                phase["status"] = "manifest_write_failed"
                phase["manifest_write_error"] = str(exc)
                self.status_var.set(
                    "Game Monitor подтвердил точный радиус, но манифест не сохранён. Исполнитель не запущен."
                )
                if self._chalk_block_task is not None:
                    self._fail_chalk_test_block(f"brush_confirmation_manifest_failed:{exc}")
                return
        if callable(workflow_callback):
            self._workflow_brush_ready_callback = None
            self.status_var.set(f"Размер {brush} подтверждён Game Monitor; запуск FILL-001.")
            self.root.after(0, lambda: workflow_callback(brush))
        elif callable(self.on_brush_ready):
            self.status_var.set(f"Размер {brush} подтверждён Game Monitor; запуск тестового исполнения.")
            self.root.after(0, lambda: self.on_brush_ready(brush))
        elif self._chalk_block_task is not None:
            self._fail_chalk_test_block("executor_callback_missing")
        else:
            phase["status"] = "executor_callback_missing"
            self.status_var.set("Кисть подтверждена Game Monitor, но callback запуска исполнителя не подключён.")

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
            if self._chalk_block_task is not None:
                self._fail_chalk_test_block("calibration_profile_unavailable_before_preclear")
            self.status_var.set("Тест остановлен до очистки: профиль калибровки недоступен.")
            messagebox.showwarning("Нет профиля", "Автоматическая подготовка не запущена.", parent=self.root)
            return
        reference_path, metadata_path = self._blank_board_reference_paths()
        if not reference_path.is_file() or not metadata_path.is_file():
            if self._chalk_block_task is not None:
                self._fail_chalk_test_block("blank_board_reference_missing")
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
            if self._chalk_block_task is not None:
                self._fail_chalk_test_block("clear_point_requires_review")
            self.status_var.set("Тест заблокирован: координата Clear требует проверки.")
            messagebox.showwarning("Clear не откалиброван", "Проверь точку Clear на вкладке 8.", parent=self.root)
            return
        if self._chalk_block_task is None and not messagebox.askyesno(
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
            experiment_id = self._experiment_id or uuid.uuid4().hex
            self._experiment_id = experiment_id
            self.experiment_dir = self.output_dir / f"experiment-{stamp}-b{brush}-{scenario}-{experiment_id[:8]}"
            try:
                self.experiment_dir.mkdir(parents=True, exist_ok=False)
            except OSError as exc:
                if self._chalk_block_task is not None:
                    self._fail_chalk_test_block(f"experiment_directory_create_failed:{exc}")
                else:
                    self.status_var.set(f"Не удалось создать каталог эксперимента: {exc}")
                return
        if self._chalk_block_task is not None and self._chalk_block_journal_path is not None:
            try:
                record_chalk_block_task_experiment(
                    self._chalk_block_journal_path,
                    self._chalk_block_task["task_id"],
                    experiment_id=self._experiment_id,
                    experiment_dir=self.experiment_dir,
                )
            except (OSError, ValueError, RuntimeError) as exc:
                self._fail_chalk_test_block(f"experiment_identity_journal_failed:{exc}")
                return
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
        if self._chalk_block_task is not None:
            self._fail_chalk_test_block("preclear_cancelled_by_user")
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
                if self._chalk_block_task is not None:
                    self._fail_chalk_test_block("brush_setup_not_started")
                return
            self.status_var.set("Доска очищена и проверена; начата установка кисти. Game Monitor автоматически проверит радиус и скорректирует ползунок.")
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
        if self._chalk_block_task is not None:
            self._fail_chalk_test_block(f"{status}:{reason}")
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
        if self._chalk_block_task is not None:
            self._fail_chalk_test_block("postdraw_cancelled_by_user")
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
            if self._chalk_block_task is not None:
                self._fail_chalk_test_block("postdraw_calibration_profile_unavailable")
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
            regions = config.get("regions", {})
            board_region = regions.get("board_area", {}) if isinstance(regions, dict) else {}
            paint_meter_region = regions.get("paint_meter_area", {}) if isinstance(regions, dict) else {}
            safe_cursor_point = _cursor_safe_point_outside_region(
                board_region,
                screen.size,
                margin=32,
                avoid_regions=(paint_meter_region,),
            )
            # Drawing has completed; release any residual button state before moving off-board.
            pyautogui.mouseUp()
            pyautogui.moveTo(*safe_cursor_point, duration=0)
            time.sleep(0.15)
            screen = ImageGrab.grab()
            if isinstance(expected, dict):
                ew, eh = expected.get("width"), expected.get("height")
                if ew is not None and eh is not None and (int(ew), int(eh)) != screen.size:
                    raise ValueError("Разрешение экрана изменилось после перемещения курсора.")
            crops = crop_calibrated_regions(screen, regions)
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
                "cursor_exclusion": {
                    "status": "moved_outside_board_before_capture",
                    "method": "mouse_up_then_move_without_click",
                    "screen_point": {"x": safe_cursor_point[0], "y": safe_cursor_point[1]},
                    "margin_px": 32,
                    "avoided_regions": ["board_area", "paint_meter_area"],
                    "destination_policy": "below_board_and_paint_meter",
                },
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
        if status != "completed" and self._chalk_block_task is not None:
            self._fail_chalk_test_block(f"postdraw_{status}:{reason}")
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
        if self._chalk_block_task is not None:
            self._on_chalk_block_restore_finished(status)
            return
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
                if self._chalk_block_task is not None:
                    self._fail_chalk_test_block(f"executor_status_{status}")
            return True
        except Exception as exc:
            self.status_var.set(f"Не удалось привязать результат исполнителя к тесту кисти: {exc}")
            if self._chalk_block_task is not None:
                self._fail_chalk_test_block(f"executor_callback_failed:{exc}")
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
                run_id = report.get("run_id")
                if is_monitor_run_claimed(
                    self.output_dir, run_id, exclude_experiment_dir=self.experiment_dir
                ):
                    selected = None
                    match_reason = "monitor_run_already_claimed"
                    candidate_count = 0
                    self.status_var.set("Game Monitor run уже привязан к другому experiment; повторная привязка запрещена.")
                    self._bridge_capture_poll_id = None
                    self.experiment_phases["monitor_capture"] = {
                        "status": "unavailable",
                        "transport": "loopback_websocket",
                        "reason": match_reason,
                        "run_id": run_id,
                        "experiment_id": getattr(self, "_experiment_id", None),
                    }
                    self._write_experiment_manifest()
                    return
                target_path = self.experiment_dir / "monitor_report.json"
                report_copy = dict(report)
                report_copy["autodraw_experiment_id"] = getattr(self, "_experiment_id", None)
                report_copy["chalk_radius_matrix"] = getattr(self, "_chalk_matrix_metadata", None)
                report_copy["chalk_experiment_matrix"] = getattr(self, "_chalk_experiment_matrix_metadata", None)
                target_path.write_text(
                    json.dumps(report_copy, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                chalk = report.get("chalk") if isinstance(report.get("chalk"), dict) else {}
                frame_probe = report.get("frame_probe") if isinstance(report.get("frame_probe"), dict) else {}
                trajectory = report.get("trajectory") if isinstance(report.get("trajectory"), dict) else {}
                summary = {
                    "source": "loopback_websocket_bridge",
                    "autodraw_experiment_id": getattr(self, "_experiment_id", None),
                    "chalk_radius_matrix": getattr(self, "_chalk_matrix_metadata", None),
                    "chalk_experiment_matrix": getattr(self, "_chalk_experiment_matrix_metadata", None),
                    "run_id": report.get("run_id"),
                    "session_id": report.get("session_id"),
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
                    "monitor_dropped_events": report.get("monitor_dropped_events"),  # Deprecated cumulative alias.
                    "monitor_buffer_dropped_events_start": report.get("monitor_buffer_dropped_events_start"),
                    "monitor_buffer_dropped_events_end": report.get("monitor_buffer_dropped_events_end"),
                    "monitor_buffer_dropped_events_delta": report.get("monitor_buffer_dropped_events_delta"),
                    "monitor_error_count_delta": report.get("monitor_error_count_delta"),
                    "bridge_send_failures_delta": report.get("bridge_send_failures_delta"),
                    "collector_sequence_gap_count": report.get("collector_sequence_gap_count"),
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
                    and report.get("monitor_error_count_delta", 0) == 0
                    and report.get("bridge_send_failures_delta", 0) == 0
                    and report.get("collector_sequence_gap_count", 0) == 0
                )
                self.experiment_phases["monitor_capture"] = {
                    "status": "saved" if telemetry_clean else "partial",
                    "transport": "loopback_websocket",
                    "match_reason": match_reason,
                    "experiment_id": getattr(self, "_experiment_id", None),
                    "chalk_radius_matrix": getattr(self, "_chalk_matrix_metadata", None),
                    "chalk_experiment_matrix": getattr(self, "_chalk_experiment_matrix_metadata", None),
                    "session_id": report.get("session_id"),
                    "run_id": report.get("run_id"),
                    "source_path": str(source_path.resolve()),
                    "report_path": target_path.name,
                    "report_event_count": report.get("event_count"),
                    "dropped_events": report.get("dropped_events"),
                    "monitor_dropped_events": report.get("monitor_dropped_events"),  # Deprecated cumulative alias.
                    "monitor_buffer_dropped_events_start": report.get("monitor_buffer_dropped_events_start"),
                    "monitor_buffer_dropped_events_end": report.get("monitor_buffer_dropped_events_end"),
                    "monitor_buffer_dropped_events_delta": report.get("monitor_buffer_dropped_events_delta"),
                    "monitor_error_count_delta": report.get("monitor_error_count_delta"),
                    "bridge_send_failures_delta": report.get("bridge_send_failures_delta"),
                    "collector_sequence_gap_count": report.get("collector_sequence_gap_count"),
                    "monitor_error_count": report.get("monitor_error_count"),  # Deprecated cumulative alias.
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
            "experiment_id": getattr(self, "_experiment_id", None),
            "chalk_radius_matrix": getattr(self, "_chalk_matrix_metadata", None),
            "chalk_experiment_matrix": getattr(self, "_chalk_experiment_matrix_metadata", None),
            "chalk_test_block": (
                self.current_plan.get("generation", {}).get("chalk_test_block")
                if isinstance(self.current_plan, dict) and isinstance(self.current_plan.get("generation"), dict)
                else None
            ),
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

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any


MODEL_ID = "game-board-point-quota-v1"
DEFAULT_POINT_SAFETY_FACTOR = 0.85

# Limits observed in the game engine. These are stored point quotas, not pixels.
BOARD_ITEM_POINT_LIMITS: dict[str, int] = {
    "BoardItem0": 3_000,
    "BoardItem1": 6_000,
    "BoardItem2": 6_000,
    "BoardItem3": 12_000,
    "BoardItem4": 12_000,
}
SUPPORTED_BOARD_POINT_LIMITS = (3_000, 6_000, 12_000)

# Values emitted by the three standard brush buttons in normal mode.
# The extended painter slider can produce integer values from 1 through 30.
# For the first planner version, use 1..20: smaller values help with details,
# while values above the largest standard button (20) are not needed yet.
STANDARD_BRUSH_PRESETS: tuple[dict[str, Any], ...] = (
    {"id": "large", "label": "Крупная", "value": 20, "purpose": "крупные однородные области"},
    {"id": "medium", "label": "Средняя", "value": 14, "purpose": "области среднего размера"},
    {"id": "small", "label": "Тонкая", "value": 7, "purpose": "детали и узкие участки"},
)
EXTENDED_BRUSH_SLIDER_MIN_VALUE = 1
EXTENDED_BRUSH_SLIDER_MAX_VALUE = 30
PLANNER_BRUSH_MIN_VALUE = 1
PLANNER_BRUSH_MAX_VALUE = 20
SUPPORTED_PLANNER_BRUSH_VALUES = tuple(range(PLANNER_BRUSH_MIN_VALUE, PLANNER_BRUSH_MAX_VALUE + 1))

POINT_COUNT_SEMANTICS = (
    "BoardPane считает сохранённые уникальные точки штрихов. Начальная точка добавляется "
    "при начале штриха, следующие точки считываются по кадрам игры; одинаковые подряд "
    "координаты не добавляются. Число точек зависит от реальной частоты кадров и движения мыши."
)


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} должно быть числом.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} должно быть числом.") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field} должно быть конечным числом.")
    return number


def _validate_point_limit(max_points: Any) -> int:
    if isinstance(max_points, bool) or not isinstance(max_points, int):
        raise ValueError("Лимит точек должен быть целым числом.")
    if max_points not in SUPPORTED_BOARD_POINT_LIMITS:
        supported = ", ".join(str(value) for value in SUPPORTED_BOARD_POINT_LIMITS)
        raise ValueError(f"Неизвестный лимит доски: {max_points}. Поддерживаются: {supported}.")
    return max_points


def get_board_point_limit(board_item_type: str) -> int:
    """Return the known engine point quota for BoardItem0..BoardItem4."""
    if not isinstance(board_item_type, str):
        raise ValueError("Тип доски должен быть строкой.")
    try:
        return BOARD_ITEM_POINT_LIMITS[board_item_type]
    except KeyError as exc:
        raise ValueError(f"Неизвестный тип доски: {board_item_type!r}.") from exc


def create_board_resource_profile(
    max_points: int,
    *,
    safety_factor: float = DEFAULT_POINT_SAFETY_FACTOR,
) -> dict[str, Any]:
    """Describe the hard point quota separately from the conservative planning budget."""
    point_limit = _validate_point_limit(max_points)
    factor = _finite_number(safety_factor, "Коэффициент запаса")
    if not 0 < factor <= 1:
        raise ValueError("Коэффициент запаса должен быть больше 0 и не больше 1.")

    planning_budget = math.floor(point_limit * factor)
    return {
        "model_id": MODEL_ID,
        "point_limit": point_limit,
        "safety_factor": factor,
        "planning_budget_points": planning_budget,
        "reserved_points": point_limit - planning_budget,
        "standard_brushes": [dict(preset) for preset in STANDARD_BRUSH_PRESETS],
        "extended_brush_slider": {
            "min_value": EXTENDED_BRUSH_SLIDER_MIN_VALUE,
            "max_value": EXTENDED_BRUSH_SLIDER_MAX_VALUE,
            "integer_values": True,
            "availability": "расширенный режим рисования; положение элементов UI нужно калибровать",
        },
        "planner_brush_values": list(SUPPORTED_PLANNER_BRUSH_VALUES),
        "planner_brush_range": [PLANNER_BRUSH_MIN_VALUE, PLANNER_BRUSH_MAX_VALUE],
        "point_count_semantics": POINT_COUNT_SEMANTICS,
        "calibration_required_for_point_estimate": True,
    }


def estimate_calibrated_point_usage(
    stroke_lengths_px: Iterable[float],
    *,
    points_per_path_px: float,
    max_points: int,
    safety_factor: float = DEFAULT_POINT_SAFETY_FACTOR,
) -> dict[str, Any]:
    """Estimate stored game points using an explicitly calibrated point/path ratio.

    points_per_path_px describes additional frame-sampled points per path pixel;
    one initial point is counted separately for each stroke. No default ratio is
    provided intentionally: MouseExecutor movement step is not the same as the
    game's frame-sampled point spacing, so an uncalibrated estimate would be false
    precision.
    """
    profile = create_board_resource_profile(max_points, safety_factor=safety_factor)
    density = _finite_number(points_per_path_px, "Коэффициент точек на пиксель пути")
    if density <= 0:
        raise ValueError("Коэффициент точек на пиксель пути должен быть больше нуля.")

    try:
        lengths = list(stroke_lengths_px)
    except TypeError as exc:
        raise ValueError("Длины штрихов должны быть переданы как последовательность чисел.") from exc

    if len(lengths) > 250_000:
        raise ValueError("Слишком много штрихов для оценки: максимум 250 000.")

    normalized_lengths: list[float] = []
    for index, raw_length in enumerate(lengths):
        length = _finite_number(raw_length, f"Длина штриха {index + 1}")
        if length < 0:
            raise ValueError("Длина штриха не может быть отрицательной.")
        normalized_lengths.append(length)

    # The start point is added when every stroke begins; sampled points along
    # each path are estimated independently to avoid hiding per-stroke rounding.
    path_sample_points = sum(math.ceil(length * density) for length in normalized_lengths)
    start_points = len(normalized_lengths)
    estimated_points = path_sample_points + start_points
    hard_limit = profile["point_limit"]
    planning_budget = profile["planning_budget_points"]

    if estimated_points > hard_limit:
        risk_level = "over_limit"
        risk_label = "Расчёт превышает жёсткий лимит точек"
    elif estimated_points > planning_budget:
        risk_level = "near_limit"
        risk_label = "Выше безопасного бюджета: нужен дополнительный запас"
    else:
        risk_level = "within_budget"
        risk_label = "В пределах безопасного бюджета"

    return {
        "model_id": MODEL_ID,
        "is_estimate": True,
        "is_calibrated_estimate": True,
        "point_limit": hard_limit,
        "planning_budget_points": planning_budget,
        "safety_factor": profile["safety_factor"],
        "stroke_count": start_points,
        "estimated_path_sample_points": path_sample_points,
        "estimated_stroke_start_points": start_points,
        "estimated_point_count": estimated_points,
        "estimated_usage_percent": round(estimated_points / hard_limit * 100, 3),
        "estimated_safe_budget_usage_percent": round(estimated_points / planning_budget * 100, 3),
        "points_per_path_px": density,
        "risk_level": risk_level,
        "risk_label": risk_label,
        "calibration_note": (
            "Оценка использует измеренный коэффициент точек на пиксель пути. "
            "Он зависит от скорости движения мыши, частоты кадров игры и настроек исполнителя; "
            "результат всё равно нужно сверять с реальным запуском."
        ),
    }

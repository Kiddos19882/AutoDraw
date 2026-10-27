from __future__ import annotations

import math
from typing import Any, Iterable


MODEL_ID = "empirical-ink-cost-v1"
DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT = 6.67
DEFAULT_PAINT_BUDGET_PX_EQUIVALENT = 25_650.0
CALIBRATED_BUDGET_LOW_PX_EQUIVALENT = 25_610.0
CALIBRATED_BUDGET_HIGH_PX_EQUIVALENT = 25_730.0
SINGLE_PIXEL_EXECUTED_LENGTH_PX = 1.0

# Observations supplied from the real game board (660x340). The path and stroke
# values are completed/visible parts when the paint stopped appearing.
CALIBRATION_OBSERVATIONS: tuple[dict[str, int], ...] = (
    {"stroke_length_px": 650, "completed_strokes": 39, "visible_path_px": 25_350, "planned_strokes": 40, "planned_path_px": 26_000},
    {"stroke_length_px": 200, "completed_strokes": 124, "visible_path_px": 24_800, "planned_strokes": 130, "planned_path_px": 26_000},
    {"stroke_length_px": 50, "completed_strokes": 454, "visible_path_px": 22_700, "planned_strokes": 520, "planned_path_px": 26_000},
    {"stroke_length_px": 10, "completed_strokes": 1_537, "visible_path_px": 15_370, "planned_strokes": 2_600, "planned_path_px": 26_000},
)


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} должно быть числом.")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} должно быть числом.") from exc
    if not math.isfinite(result):
        raise ValueError(f"{field} должно быть конечным числом.")
    return result


def estimate_paint_cost(
    drawing_length_px: float,
    stroke_count: int,
    single_pixel_stroke_count: int = 0,
    *,
    stroke_overhead_px_equivalent: float = DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT,
    paint_budget_px_equivalent: float = DEFAULT_PAINT_BUDGET_PX_EQUIVALENT,
) -> dict[str, Any]:
    """Estimate consumption of the game's stored-point quota in pixel-equivalent units.

    The game does not use an independent ink tank here: BoardPane counts the
    unique cursor coordinates stored in atom.points. This legacy metric converts
    that quota to an empirical equivalent-pixel scale for the tested executor
    profile. The model is effective path length + per-stroke overhead. The
    executor expands a point-stroke to a 1 px line, so that path is included too.

    Four observed runs imply around 6.67 px-equivalent per stroke and about
    25,650 px-equivalent for the tested setup. The equivalent-pixel scale is not
    universal: it depends on frame sampling, movement step, delay, and board quota.
    """
    path_length = _finite_number(drawing_length_px, "Длина рисования")
    overhead = _finite_number(stroke_overhead_px_equivalent, "Расход на штрих")
    budget = _finite_number(paint_budget_px_equivalent, "Оценочный запас краски")
    if path_length < 0:
        raise ValueError("Длина рисования не может быть отрицательной.")
    if overhead < 0:
        raise ValueError("Расход на штрих не может быть отрицательным.")
    if budget <= 0:
        raise ValueError("Оценочный запас краски должен быть больше нуля.")
    if isinstance(stroke_count, bool) or not isinstance(stroke_count, int) or stroke_count < 0:
        raise ValueError("Количество штрихов должно быть неотрицательным целым числом.")
    if isinstance(single_pixel_stroke_count, bool) or not isinstance(single_pixel_stroke_count, int):
        raise ValueError("Количество одиночных пикселей должно быть целым числом.")
    if not 0 <= single_pixel_stroke_count <= stroke_count:
        raise ValueError("Количество одиночных пикселей должно быть между нулём и общим числом штрихов.")

    single_pixel_extra_path = single_pixel_stroke_count * SINGLE_PIXEL_EXECUTED_LENGTH_PX
    effective_path = path_length + single_pixel_extra_path
    stroke_overhead = stroke_count * overhead
    total = effective_path + stroke_overhead
    usage_percent = total / budget * 100.0
    conservative_percent = total / CALIBRATED_BUDGET_LOW_PX_EQUIVALENT * 100.0
    remaining = budget - total

    if usage_percent >= 100.0:
        risk_level = "over_budget"
        risk_label = "Выше оценочного запаса краски"
    elif usage_percent >= 90.0:
        risk_level = "very_high"
        risk_label = "Очень высокий расход — близко к пределу"
    elif usage_percent >= 75.0:
        risk_level = "high"
        risk_label = "Высокий расход — нужен запас"
    elif usage_percent >= 50.0:
        risk_level = "moderate"
        risk_label = "Средний расход"
    else:
        risk_level = "lower"
        risk_label = "Ниже половины оценочного запаса"

    return {
        "model_id": MODEL_ID,
        "is_estimate": True,
        "resource_basis": "frame_sampled_unique_game_points",
        "resource_semantics_note": (
            "Legacy pixel-equivalent estimate for BoardPane's shared stored-coordinate quota; "
            "not an independent per-color ink supply."
        ),
        "drawing_length_px": round(path_length, 3),
        "single_pixel_extra_path_px": round(single_pixel_extra_path, 3),
        "effective_path_length_px": round(effective_path, 3),
        "stroke_count": stroke_count,
        "stroke_overhead_px_equivalent": round(overhead, 4),
        "estimated_stroke_overhead_px_equivalent": round(stroke_overhead, 3),
        "estimated_total_ink_px_equivalent": round(total, 3),
        "estimated_budget_px_equivalent": round(budget, 3),
        "calibrated_budget_low_px_equivalent": CALIBRATED_BUDGET_LOW_PX_EQUIVALENT,
        "calibrated_budget_high_px_equivalent": CALIBRATED_BUDGET_HIGH_PX_EQUIVALENT,
        "estimated_usage_percent": round(usage_percent, 3),
        "conservative_usage_percent": round(conservative_percent, 3),
        "estimated_remaining_px_equivalent": round(remaining, 3),
        "risk_level": risk_level,
        "risk_label": risk_label,
        "calibration_observation_count": len(CALIBRATION_OBSERVATIONS),
        "calibration_note": (
            "Пиксель-эквивалент является эмпирическим приближением квоты сохранённых точек BoardPane, "
            "а не отдельным счётчиком краски. Результат зависит от частоты кадров и настроек исполнителя "
            "и должен сверяться с реальным запуском."
        ),
    }


def estimate_color_plan_paint_cost(
    plan: dict[str, Any],
    *,
    stroke_overhead_px_equivalent: float = DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT,
    paint_budget_px_equivalent: float = DEFAULT_PAINT_BUDGET_PX_EQUIVALENT,
) -> dict[str, Any]:
    """Estimate both whole-plan and per-color consumption for a color plan.

    The experiment used only one color, so the game may have either one shared
    pool or an independent pool per selected color. Return both interpretations
    instead of pretending the experiment has established which one is true.
    """
    if not isinstance(plan, dict) or not isinstance(plan.get("summary"), dict):
        raise ValueError("Не найден summary цветного плана.")
    summary = plan["summary"]
    overall = estimate_paint_cost(
        summary.get("drawing_length_px"),
        summary.get("stroke_count"),
        summary.get("single_pixel_stroke_count", 0),
        stroke_overhead_px_equivalent=stroke_overhead_px_equivalent,
        paint_budget_px_equivalent=paint_budget_px_equivalent,
    )

    by_color: dict[int, dict[str, Any]] = {}
    raw_strokes = plan.get("strokes", [])
    if not isinstance(raw_strokes, list):
        raise ValueError("Список штрихов плана повреждён.")
    for stroke in raw_strokes:
        if not isinstance(stroke, dict):
            raise ValueError("Штрих цветного плана должен быть объектом.")
        color = stroke.get("color")
        points = stroke.get("points")
        if not isinstance(color, dict) or not isinstance(points, list) or len(points) != 2:
            raise ValueError("У цветного штриха отсутствуют цвет или две точки.")
        try:
            palette_index = int(color["palette_index"])
            x1, y1 = float(points[0]["x"]), float(points[0]["y"])
            x2, y2 = float(points[1]["x"]), float(points[1]["y"])
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise ValueError("Не удалось прочитать геометрию цветного штриха.") from exc
        if palette_index < 0 or not all(math.isfinite(v) for v in (x1, y1, x2, y2)):
            raise ValueError("Цветовой индекс и координаты штриха должны быть корректными.")
        is_single = math.isclose(x1, x2, abs_tol=1e-9) and math.isclose(y1, y2, abs_tol=1e-9)
        aggregate = by_color.setdefault(palette_index, {
            "palette_index": palette_index,
            "id": str(color.get("id", palette_index)),
            "name": str(color.get("name", f"Цвет {palette_index}")),
            "hex": str(color.get("hex", "")),
            "stroke_count": 0,
            "drawing_length_px": 0.0,
            "single_pixel_stroke_count": 0,
        })
        aggregate["stroke_count"] += 1
        aggregate["drawing_length_px"] += math.hypot(x2 - x1, y2 - y1)
        if is_single:
            aggregate["single_pixel_stroke_count"] += 1

    per_color_estimates: list[dict[str, Any]] = []
    for palette_index in sorted(by_color):
        aggregate = by_color[palette_index]
        estimate = estimate_paint_cost(
            aggregate["drawing_length_px"],
            aggregate["stroke_count"],
            aggregate["single_pixel_stroke_count"],
            stroke_overhead_px_equivalent=stroke_overhead_px_equivalent,
            paint_budget_px_equivalent=paint_budget_px_equivalent,
        )
        per_color_estimates.append({
            "palette_index": palette_index,
            "id": aggregate["id"],
            "name": aggregate["name"],
            "hex": aggregate["hex"],
            "stroke_count": aggregate["stroke_count"],
            "drawing_length_px": round(aggregate["drawing_length_px"], 3),
            "single_pixel_stroke_count": aggregate["single_pixel_stroke_count"],
            "estimated_total_ink_px_equivalent": estimate["estimated_total_ink_px_equivalent"],
            "estimated_usage_percent": estimate["estimated_usage_percent"],
            "conservative_usage_percent": estimate["conservative_usage_percent"],
            "risk_level": estimate["risk_level"],
            "risk_label": estimate["risk_label"],
        })

    highest_color = max(per_color_estimates, key=lambda entry: entry["estimated_usage_percent"], default=None)
    overall["per_color_estimates"] = per_color_estimates
    overall["max_per_color_usage_percent"] = (
        highest_color["estimated_usage_percent"] if highest_color else 0.0
    )
    overall["highest_use_color"] = highest_color
    overall["resource_scope_note"] = (
        "Движок считает точки всех цветов в одном BoardPane.atom.points, поэтому игровая квота общая для всего "
        "рисунка. Строки по цветам — диагностическая разбивка той же общей суммы; их проценты нельзя трактовать "
        "как отдельные независимые запасы."
    )
    return overall


def fit_model_to_calibration_observations(
    observations: Iterable[dict[str, Any]] = CALIBRATION_OBSERVATIONS,
) -> dict[str, float | int]:
    """Fit B ~= visible_path + overhead * visible_strokes by least squares."""
    data: list[tuple[float, float]] = []
    for item in observations:
        try:
            strokes = float(item["completed_strokes"])
            path = float(item["visible_path_px"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Каждое наблюдение должно содержать completed_strokes и visible_path_px.") from exc
        if not math.isfinite(strokes) or not math.isfinite(path) or strokes <= 0 or path < 0:
            raise ValueError("Наблюдения должны иметь положительное число штрихов и неотрицательную длину.")
        data.append((strokes, path))
    if len(data) < 2:
        raise ValueError("Для оценки модели нужны минимум два наблюдения.")
    mean_n = sum(n for n, _ in data) / len(data)
    mean_path = sum(path for _, path in data) / len(data)
    variance = sum((n - mean_n) ** 2 for n, _ in data)
    if variance <= 0:
        raise ValueError("Наблюдения должны отличаться по числу штрихов.")
    covariance = sum((n - mean_n) * (path - mean_path) for n, path in data)
    overhead = -covariance / variance
    budget = mean_path + overhead * mean_n
    reconstructed = [path + overhead * n for n, path in data]
    residuals = [value - budget for value in reconstructed]
    return {
        "observation_count": len(data),
        "stroke_overhead_px_equivalent": round(overhead, 4),
        "paint_budget_px_equivalent": round(budget, 2),
        "minimum_reconstructed_budget_px_equivalent": round(min(reconstructed), 2),
        "maximum_reconstructed_budget_px_equivalent": round(max(reconstructed), 2),
        "max_abs_residual_px_equivalent": round(max(abs(v) for v in residuals), 2),
    }

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

from board_resource_model import DEFAULT_POINT_SAFETY_FACTOR, SUPPORTED_BOARD_POINT_LIMITS
from paint_cost_model import CALIBRATION_OBSERVATIONS, fit_model_to_calibration_observations


MODEL_ID = "game-frame-sampled-point-calibration-v1"

# Verified in the bundled game engine: BoardPane.onDrawing is registered on
# ENTER_FRAME and stores the cursor coordinate only if it differs from the
# previous stored coordinate. The engine's default stage frame rate is 48 FPS;
# actual FPS may be lower under browser or device load.
GAME_ENGINE_DEFAULT_FRAME_RATE_FPS = 48.0

# Current MouseExecutor defaults. The historic depletion records do not persist
# the executor settings for each test, so this is a best-supported baseline.
DEFAULT_EXECUTOR_POINT_STEP_PX = 2.0
DEFAULT_EXECUTOR_POINT_DELAY_MS = 10


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


def _validate_point_limit(value: Any, field: str = "Лимит точек") -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} должен быть целым числом.")
    if value not in SUPPORTED_BOARD_POINT_LIMITS:
        supported = ", ".join(str(item) for item in SUPPORTED_BOARD_POINT_LIMITS)
        raise ValueError(f"{field} должен быть одним из значений: {supported}.")
    return value


def estimate_theoretical_points_per_path_px(
    *,
    point_step_px: float = DEFAULT_EXECUTOR_POINT_STEP_PX,
    point_delay_ms: float = DEFAULT_EXECUTOR_POINT_DELAY_MS,
    frame_rate_fps: float = GAME_ENGINE_DEFAULT_FRAME_RATE_FPS,
) -> float:
    """Estimate frame-sampled points per screen-path pixel.

    Approximation: points_per_px = FPS * delay_seconds / movement_step_px.
    It assumes each game frame sees a new cursor coordinate. Real values can
    differ because of frame scheduling, integer coordinates, browser load, and
    the game canvas scale.
    """
    step = _finite_number(point_step_px, "Шаг исполнителя")
    delay = _finite_number(point_delay_ms, "Задержка исполнителя")
    fps = _finite_number(frame_rate_fps, "Частота кадров")
    if step <= 0:
        raise ValueError("Шаг исполнителя должен быть больше нуля.")
    if delay <= 0:
        raise ValueError(
            "Для теоретической оценки задержка должна быть больше нуля; "
            "при задержке 0 мс скорость ограничивается вводом и операционной системой."
        )
    if fps <= 0:
        raise ValueError("Частота кадров должна быть больше нуля.")
    return fps * (delay / 1000.0) / step


def build_engine_point_calibration_report(
    observations: Iterable[dict[str, Any]] = CALIBRATION_OBSERVATIONS,
    *,
    point_step_px: float = DEFAULT_EXECUTOR_POINT_STEP_PX,
    point_delay_ms: float = DEFAULT_EXECUTOR_POINT_DELAY_MS,
    frame_rate_fps: float = GAME_ENGINE_DEFAULT_FRAME_RATE_FPS,
    calibration_point_limit: int | None = None,
) -> dict[str, Any]:
    """Compare empirical exhaustion observations with the game's point quotas.

    Existing observations include completed path lengths and stroke counts, but
    not the board item type or exact executor settings used in every run. The
    nearest supported point quota is therefore reported as an inference unless
    calibration_point_limit is explicitly supplied.
    """
    observation_list = list(observations)
    fit = fit_model_to_calibration_observations(observation_list)
    theoretical_density = estimate_theoretical_points_per_path_px(
        point_step_px=point_step_px,
        point_delay_ms=point_delay_ms,
        frame_rate_fps=frame_rate_fps,
    )
    baseline_theoretical_density = estimate_theoretical_points_per_path_px()
    budget = float(fit["paint_budget_px_equivalent"])
    if budget <= 0:
        raise ValueError("Калиброванный бюджет должен быть больше нуля.")

    theoretical_capacity = budget * theoretical_density
    nearest_limit = min(
        SUPPORTED_BOARD_POINT_LIMITS,
        key=lambda value: abs(value - theoretical_capacity),
    )
    is_inferred = calibration_point_limit is None
    base_limit = nearest_limit if is_inferred else _validate_point_limit(calibration_point_limit)
    empirical_density_at_baseline = base_limit / budget
    density_scale = theoretical_density / baseline_theoretical_density
    effective_density = empirical_density_at_baseline * density_scale
    stroke_overhead_points = (
        empirical_density_at_baseline * float(fit["stroke_overhead_px_equivalent"])
    )

    observation_results: list[dict[str, Any]] = []
    for item in observation_list:
        path_px = _finite_number(item["visible_path_px"], "Длина видимого пути")
        strokes_raw = item["completed_strokes"]
        if isinstance(strokes_raw, bool) or not isinstance(strokes_raw, int) or strokes_raw < 0:
            raise ValueError("Количество завершённых штрихов должно быть целым неотрицательным числом.")
        equivalent_cost = path_px + float(fit["stroke_overhead_px_equivalent"]) * strokes_raw
        empirical_points = equivalent_cost * empirical_density_at_baseline
        theoretical_points = equivalent_cost * theoretical_density
        observation_results.append({
            "stroke_length_px": item.get("stroke_length_px"),
            "completed_strokes": strokes_raw,
            "visible_path_px": round(path_px, 3),
            "effective_path_equivalent_px": round(equivalent_cost, 3),
            "estimated_points_using_calibrated_density": round(empirical_points, 2),
            "estimated_points_using_theoretical_density": round(theoretical_points, 2),
            "empirical_residual_points": round(empirical_points - base_limit, 2),
            "theoretical_residual_points": round(theoretical_points - base_limit, 2),
        })

    empirical_residuals = [abs(item["empirical_residual_points"]) for item in observation_results]
    theoretical_residuals = [abs(item["theoretical_residual_points"]) for item in observation_results]
    nearest_deviation_percent = abs(theoretical_capacity - nearest_limit) / nearest_limit * 100.0
    spread_percent = (
        (
            float(fit["maximum_reconstructed_budget_px_equivalent"])
            - float(fit["minimum_reconstructed_budget_px_equivalent"])
        )
        / budget
        * 100.0
    )

    return {
        "model_id": MODEL_ID,
        "engine_resource": "Количество уникальных соседних координат, сохранённых в BoardPane.atom.points.",
        "engine_sampling": (
            "Начальная координата добавляется при старте штриха; затем курсор считывается на ENTER_FRAME. "
            "Повтор одинаковой соседней координаты не сохраняется."
        ),
        "executor_profile": {
            "point_step_px": round(_finite_number(point_step_px, "Шаг исполнителя"), 4),
            "point_delay_ms": round(_finite_number(point_delay_ms, "Задержка исполнителя"), 4),
            "frame_rate_fps": round(_finite_number(frame_rate_fps, "Частота кадров"), 4),
            "frame_rate_is_nominal": True,
            "theoretical_points_per_path_px": round(theoretical_density, 6),
            "effective_points_per_path_px": round(effective_density, 6),
            "points_per_stroke_equivalent_overhead": round(stroke_overhead_points, 6),
            "theoretical_path_step_per_frame_px": round(1.0 / theoretical_density, 4),
        },
        "observed_cutoff_fit": {
            "observation_count": int(fit["observation_count"]),
            "stroke_overhead_px_equivalent": fit["stroke_overhead_px_equivalent"],
            "paint_budget_px_equivalent": fit["paint_budget_px_equivalent"],
            "minimum_reconstructed_budget_px_equivalent": fit["minimum_reconstructed_budget_px_equivalent"],
            "maximum_reconstructed_budget_px_equivalent": fit["maximum_reconstructed_budget_px_equivalent"],
            "budget_spread_percent": round(spread_percent, 4),
            "max_abs_residual_px_equivalent": fit["max_abs_residual_px_equivalent"],
        },
        "point_limit_inference": {
            "selected_limit": base_limit,
            "is_inferred": is_inferred,
            "is_verified_from_observation_metadata": not is_inferred,
            "theoretical_capacity_points": round(theoretical_capacity, 2),
            "nearest_supported_limit": nearest_limit,
            "nearest_limit_deviation_percent": round(nearest_deviation_percent, 3),
            "consistency": (
                "strong" if nearest_deviation_percent <= 5.0
                else "plausible" if nearest_deviation_percent <= 15.0
                else "weak"
            ),
            "supported_limits": list(SUPPORTED_BOARD_POINT_LIMITS),
        },
        "validation": {
            "max_abs_empirical_residual_points": round(max(empirical_residuals, default=0.0), 2),
            "max_abs_theoretical_residual_points": round(max(theoretical_residuals, default=0.0), 2),
            "empirical_density_is_scaled_for_current_executor_profile": True,
            "historic_executor_profile_was_recorded": False,
            "note": (
                "The empirical fit uses the existing depletion observations. The nearest quota and historic "
                "executor profile are inferred because these metadata were not saved with the observations."
            ),
        },
        "observations": observation_results,
    }


def estimate_point_quota_usage(
    drawing_length_px: float,
    stroke_count: int,
    *,
    board_point_limit: int,
    single_pixel_stroke_count: int = 0,
    point_step_px: float = DEFAULT_EXECUTOR_POINT_STEP_PX,
    point_delay_ms: float = DEFAULT_EXECUTOR_POINT_DELAY_MS,
    frame_rate_fps: float = GAME_ENGINE_DEFAULT_FRAME_RATE_FPS,
    calibration_point_limit: int | None = None,
    safety_factor: float = DEFAULT_POINT_SAFETY_FACTOR,
) -> dict[str, Any]:
    """Estimate point-quota usage separately from the legacy pixel-equivalent model.

    board_point_limit is the quota of the target board. The sample density is
    anchored to the inferred or explicitly supplied calibration board limit and
    scaled for the selected executor timing.
    """
    path_px = _finite_number(drawing_length_px, "Длина рисования")
    if path_px < 0:
        raise ValueError("Длина рисования не может быть отрицательной.")
    if isinstance(stroke_count, bool) or not isinstance(stroke_count, int) or stroke_count < 0:
        raise ValueError("Количество штрихов должно быть целым неотрицательным числом.")
    if isinstance(single_pixel_stroke_count, bool) or not isinstance(single_pixel_stroke_count, int):
        raise ValueError("Количество одиночных пикселей должно быть целым числом.")
    if not 0 <= single_pixel_stroke_count <= stroke_count:
        raise ValueError("Количество одиночных пикселей должно быть между нулём и числом штрихов.")
    limit = _validate_point_limit(board_point_limit, "Лимит доски")
    factor = _finite_number(safety_factor, "Коэффициент запаса")
    if not 0 < factor <= 1:
        raise ValueError("Коэффициент запаса должен быть больше нуля и не больше единицы.")

    report = build_engine_point_calibration_report(
        point_step_px=point_step_px,
        point_delay_ms=point_delay_ms,
        frame_rate_fps=frame_rate_fps,
        calibration_point_limit=calibration_point_limit,
    )
    profile = report["executor_profile"]
    effective_path_px = path_px + float(single_pixel_stroke_count)
    path_points = effective_path_px * float(profile["effective_points_per_path_px"])
    stroke_overhead_points = stroke_count * float(profile["points_per_stroke_equivalent_overhead"])
    estimated_points_float = path_points + stroke_overhead_points
    estimated_points = math.ceil(estimated_points_float)
    planning_budget = math.floor(limit * factor)
    if planning_budget < 1:
        raise ValueError("Коэффициент запаса слишком мал для получения положительного бюджета.")

    if estimated_points > limit:
        risk_level = "over_limit"
        risk_label = "Оценка превышает жёсткий лимит игровых точек"
    elif estimated_points > planning_budget:
        risk_level = "near_limit"
        risk_label = "Выше безопасного бюджета точек — нужен больший запас"
    else:
        risk_level = "within_budget"
        risk_label = "В пределах безопасного бюджета игровых точек"

    return {
        "model_id": MODEL_ID,
        "is_estimate": True,
        "is_calibrated_estimate": True,
        "board_point_limit": limit,
        "planning_budget_points": planning_budget,
        "safety_factor": factor,
        "drawing_length_px": round(path_px, 3),
        "single_pixel_extra_path_px": round(float(single_pixel_stroke_count), 3),
        "effective_path_length_px": round(effective_path_px, 3),
        "stroke_count": stroke_count,
        "estimated_path_sample_points": round(path_points, 3),
        "estimated_stroke_overhead_points": round(stroke_overhead_points, 3),
        "estimated_point_count_float": round(estimated_points_float, 3),
        "estimated_point_count": estimated_points,
        "estimated_usage_percent": round(estimated_points / limit * 100.0, 3),
        "estimated_safe_budget_usage_percent": round(estimated_points / planning_budget * 100.0, 3),
        "points_per_path_px": profile["effective_points_per_path_px"],
        "points_per_stroke_equivalent_overhead": profile["points_per_stroke_equivalent_overhead"],
        "calibration_point_limit": report["point_limit_inference"]["selected_limit"],
        "calibration_point_limit_is_inferred": report["point_limit_inference"]["is_inferred"],
        "risk_level": risk_level,
        "risk_label": risk_label,
        "calibration_report": report,
        "calibration_note": (
            "Игровой лимит — количество сохранённых координат. Расчёт откалиброван по четырём наблюдениям "
            "и номинальным настройкам исполнителя; тип доски в исходных наблюдениях не записан, поэтому "
            "лимит калибровочной доски помечен как вывод, а не подтверждённый факт."
        ),
    }

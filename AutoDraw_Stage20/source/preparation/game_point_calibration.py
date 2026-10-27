"""Analyze direct browser-game point-quota calibration experiments.

A fit is only a model from manually observed exhaustion thresholds. It is not an
engine-reported exact point counter; browser frame timing and the last visible
stroke introduce uncertainty.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

import numpy as np

from board_resource_model import BOARD_ITEM_POINT_LIMITS
from engine_point_calibration import estimate_theoretical_points_per_path_px
from interval_quota_fit import fit_interval_censored_quota


SCHEMA_VERSION = 1
REPORT_SCHEMA_VERSION = 2
FRAME_PROBE_SCHEMA_VERSION = 2
MIN_FIT_RUNS = 3
MIN_DISTINCT_LENGTHS = 3
MAX_ACCEPTABLE_RELATIVE_ERROR_PERCENT = 10.0
CUTOFF_INTERVAL_TOLERANCE_POINTS = 1.0
MAX_ACCEPTABLE_FRAME_GAP_MS = 1000.0


class GamePointCalibrationError(ValueError):
    """Invalid browser calibration run or observation document."""


def _number(value: Any, field: str, *, positive: bool = False) -> float:
    if isinstance(value, bool):
        raise GamePointCalibrationError(f"{field} должно быть числом.")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise GamePointCalibrationError(f"{field} должно быть числом.") from exc
    if not math.isfinite(result) or (positive and result <= 0):
        suffix = " положительным и конечным" if positive else " конечным"
        raise GamePointCalibrationError(f"{field} должно быть{suffix} числом.")
    return result


def _integer(value: Any, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise GamePointCalibrationError(f"{field} должно быть целым числом не меньше {minimum}.")
    return value


def _validate_document(document: Any) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(document, dict) or document.get("schema_version") != SCHEMA_VERSION:
        raise GamePointCalibrationError("Неизвестная версия JSON калибровки; ожидается schema_version=1.")
    browser = document.get("browser")
    runs = document.get("runs")
    if not isinstance(browser, dict) or not isinstance(runs, list):
        raise GamePointCalibrationError("Ожидаются объекты browser и массив runs.")

    probe = browser.get("frame_probe")
    if not isinstance(probe, dict):
        raise GamePointCalibrationError("Добавьте результат browser_frame_probe.js в browser.frame_probe.")
    if probe.get("schema_version") != FRAME_PROBE_SCHEMA_VERSION:
        raise GamePointCalibrationError(
            f"Версия browser.frame_probe должна быть {FRAME_PROBE_SCHEMA_VERSION}; "
            "запустите актуальный browser_frame_probe.js заново."
        )
    if probe.get("probe_status") != "completed":
        raise GamePointCalibrationError("Замер кадров не завершён корректно; повторите его.")
    if probe.get("visibility_interrupted") is not False:
        raise GamePointCalibrationError("Замер был прерван изменением видимости вкладки.")
    visibility_changes = _integer(
        probe.get("visibility_change_count"),
        "Число изменений видимости вкладки",
        minimum=0,
    )
    if visibility_changes != 0:
        raise GamePointCalibrationError("Видимость вкладки изменилась во время замера; повторите его.")
    if probe.get("document_visibility") != "visible":
        raise GamePointCalibrationError("Вкладка была скрыта во время замера FPS; повторите его на видимой вкладке.")

    fps = _number(probe.get("average_fps"), "Средний FPS из browser.frame_probe", positive=True)
    median_fps = _number(probe.get("median_fps"), "Медианный FPS", positive=True)
    duration = _number(probe.get("duration_ms"), "Длительность замера FPS", positive=True)
    wall_duration = _number(probe.get("wall_clock_elapsed_ms"), "Реальная длительность замера FPS", positive=True)
    frame_count = _integer(probe.get("frame_count"), "Число измеренных интервалов кадров", minimum=30)
    median_interval = _number(
        probe.get("median_frame_interval_ms"),
        "Медианный интервал кадров",
        positive=True,
    )
    p95_interval = _number(
        probe.get("p95_frame_interval_ms"),
        "95-й перцентиль интервала кадров",
        positive=True,
    )
    maximum_interval = _number(
        probe.get("max_frame_interval_ms"),
        "Максимальный интервал кадров",
        positive=True,
    )
    if fps > 300 or median_fps > 300:
        raise GamePointCalibrationError("FPS выглядит недопустимо высоким; проверьте результат DevTools probe.")
    if duration < 3000:
        raise GamePointCalibrationError("Для калибровки используйте замер FPS длительностью не менее 3 секунд.")
    if wall_duration < duration * 0.9:
        raise GamePointCalibrationError("Реальная длительность замера меньше ожидаемой; повторите измерение.")
    if maximum_interval > MAX_ACCEPTABLE_FRAME_GAP_MS:
        raise GamePointCalibrationError(
            "В замере есть пауза кадров свыше 1000 мс; повторите его без приостановки вкладки."
        )
    if not median_interval <= p95_interval <= maximum_interval:
        raise GamePointCalibrationError("Статистика интервалов кадров внутренне противоречива.")
    interval_median_fps = 1000.0 / median_interval
    if abs(interval_median_fps - median_fps) / median_fps > 0.03:
        raise GamePointCalibrationError("Медианный FPS не согласуется с медианным интервалом кадров.")
    fps_from_count = frame_count * 1000.0 / duration
    if abs(fps_from_count - fps) / fps > 0.15:
        raise GamePointCalibrationError("Число кадров, длительность и средний FPS не согласуются.")
    normalized_probe = dict(probe)
    normalized_probe["average_fps"] = fps
    normalized_probe["median_fps"] = median_fps

    normalized_runs: list[dict[str, Any]] = []
    excluded_runs: list[dict[str, Any]] = []
    seen_run_ids: set[str] = set()
    allowed_outcomes = {"all_visible", "partial", "none_visible"}
    for position, raw in enumerate(runs, start=1):
        if not isinstance(raw, dict):
            raise GamePointCalibrationError(f"Запуск №{position} должен быть объектом JSON.")
        run_id = str(raw.get("run_id") or f"run-{position}")
        if run_id in seen_run_ids:
            raise GamePointCalibrationError(f"Повторяется run_id={run_id!r}; каждому запуску нужен уникальный ID.")
        seen_run_ids.add(run_id)
        board_type = raw.get("board_item_type")
        if board_type not in BOARD_ITEM_POINT_LIMITS:
            raise GamePointCalibrationError(
                f"{run_id}: неизвестный board_item_type {board_type!r}; допустимо: "
                + ", ".join(BOARD_ITEM_POINT_LIMITS)
                + "."
            )
        point_limit = _integer(raw.get("board_point_limit"), f"{run_id}: board_point_limit", minimum=1)
        expected_limit = BOARD_ITEM_POINT_LIMITS[board_type]
        if point_limit != expected_limit:
            raise GamePointCalibrationError(
                f"{run_id}: лимит {point_limit} не соответствует {board_type} (ожидается {expected_limit})."
            )
        step = _number(raw.get("point_step_px"), f"{run_id}: point_step_px", positive=True)
        delay = _number(raw.get("point_delay_ms"), f"{run_id}: point_delay_ms", positive=True)
        if step > 100 or delay > 1000:
            raise GamePointCalibrationError(f"{run_id}: шаг или задержка выглядят неправдоподобно.")
        outcome = raw.get("outcome")
        if outcome not in allowed_outcomes:
            raise GamePointCalibrationError(
                f"{run_id}: outcome должен быть all_visible, partial или none_visible."
            )
        planned_count = _integer(raw.get("planned_strokes"), f"{run_id}: planned_strokes", minimum=1)
        stroke_length = _number(raw.get("stroke_length_px"), f"{run_id}: stroke_length_px", positive=True)
        planned_path = _number(raw.get("planned_path_length_px"), f"{run_id}: planned_path_length_px", positive=True)
        repeat_index = _integer(raw.get("repeat_index", 1), f"{run_id}: repeat_index", minimum=1)
        if not isinstance(raw.get("fresh_supply_confirmed"), bool):
            raise GamePointCalibrationError(
                f"{run_id}: fresh_supply_confirmed должен быть true/false; не оставляйте поле пустым."
            )
        fresh = raw["fresh_supply_confirmed"]
        last_visible = raw.get("last_visible_strokes")
        if outcome == "all_visible":
            if last_visible is not None and _integer(
                last_visible, f"{run_id}: last_visible_strokes", minimum=0
            ) != planned_count:
                raise GamePointCalibrationError(
                    f"{run_id}: all_visible противоречит last_visible_strokes; ожидалось planned_strokes."
                )
            visible_count = planned_count
        elif outcome == "none_visible":
            if last_visible is not None and _integer(
                last_visible, f"{run_id}: last_visible_strokes", minimum=0
            ) != 0:
                raise GamePointCalibrationError(
                    f"{run_id}: none_visible противоречит last_visible_strokes; ожидалось 0."
                )
            visible_count = 0
        else:
            visible_count = _integer(last_visible, f"{run_id}: last_visible_strokes", minimum=1)
            if visible_count >= planned_count:
                raise GamePointCalibrationError(
                    f"{run_id}: при outcome=partial число last_visible_strokes должно быть от 1 до planned_strokes - 1."
                )

        expected_planned_path = planned_count * stroke_length
        planned_path_tolerance = max(1.0, expected_planned_path * 0.001)
        if abs(planned_path - expected_planned_path) > planned_path_tolerance:
            raise GamePointCalibrationError(
                f"{run_id}: planned_path_length_px не согласуется с planned_strokes × stroke_length_px."
            )
        expected_visible_path = visible_count * stroke_length
        visible_path = _number(
            raw.get("visible_path_length_px", expected_visible_path),
            f"{run_id}: visible_path_length_px",
        )
        visible_path_tolerance = max(1.0, expected_visible_path * 0.001)
        if visible_path < 0 or abs(visible_path - expected_visible_path) > visible_path_tolerance:
            raise GamePointCalibrationError(
                f"{run_id}: visible_path_length_px не согласуется с количеством полностью видимых штрихов."
            )
        if visible_path > planned_path + planned_path_tolerance:
            raise GamePointCalibrationError(
                f"{run_id}: видимый путь не может быть длиннее запланированного."
            )
        normalized = {
            "run_id": run_id,
            "board_item_type": board_type,
            "board_point_limit": point_limit,
            "point_step_px": step,
            "point_delay_ms": delay,
            "measured_frame_rate_fps": fps,
            "scenario_id": str(raw.get("scenario_id") or ""),
            "stroke_length_px": stroke_length,
            "planned_strokes": planned_count,
            "planned_path_length_px": planned_path,
            "outcome": outcome,
            "last_visible_strokes": visible_count,
            "visible_path_length_px": visible_path,
            "fresh_supply_confirmed": fresh,
            "repeat_index": repeat_index,
            "notes": str(raw.get("notes") or ""),
        }
        normalized_runs.append(normalized)
        if outcome != "partial":
            excluded_runs.append({
                "run_id": run_id,
                "reason": (
                    "all_visible: лимит не был достигнут в тестовом объёме."
                    if outcome == "all_visible"
                    else "none_visible: отсутствие видимого цвета не доказывает исчерпание ресурса."
                ),
            })
        elif not fresh:
            excluded_runs.append({
                "run_id": run_id,
                "reason": "fresh_supply_confirmed=false; запас краски не подтверждён как сопоставимый.",
            })
    return {"browser": browser, "frame_probe": normalized_probe}, normalized_runs, excluded_runs


def analyze_game_point_calibration(document: Any) -> dict[str, Any]:
    """Fit points per path pixel and per stroke using depletion observations by config."""
    normalized, runs, excluded = _validate_document(document)
    probe = normalized["frame_probe"]
    fps = float(probe["average_fps"])

    groups: dict[tuple[str, int, float, float, float], list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        if run["outcome"] != "partial" or not run["fresh_supply_confirmed"]:
            continue
        key = (
            run["board_item_type"],
            run["board_point_limit"],
            round(run["point_step_px"], 4),
            round(run["point_delay_ms"], 4),
            round(run["measured_frame_rate_fps"], 2),
        )
        groups[key].append(run)

    models: list[dict[str, Any]] = []
    for (board_type, point_limit, step, delay, measured_fps), group in sorted(groups.items()):
        visible_length = np.asarray([item["visible_path_length_px"] for item in group], dtype=np.float64)
        visible_strokes = np.asarray([item["last_visible_strokes"] for item in group], dtype=np.float64)
        stroke_lengths = np.asarray([item["stroke_length_px"] for item in group], dtype=np.float64)

        # The quota crossing is interval-censored: the quota was not reached
        # after the last complete stroke, but was reached/rejected during the
        # next one. Fit to the midpoint of that interval rather than pretending
        # the last visible stroke is an exact quota boundary.
        midpoint_lengths = visible_length + stroke_lengths / 2.0
        midpoint_strokes = visible_strokes + 0.5
        matrix = np.column_stack((midpoint_lengths, midpoint_strokes))
        distinct_lengths = sorted({round(float(item["stroke_length_px"]), 4) for item in group})
        fit_base = {
            "board_item_type": board_type,
            "board_point_limit": point_limit,
            "point_step_px": step,
            "point_delay_ms": delay,
            "measured_average_frame_rate_fps": measured_fps,
            "run_count": len(group),
            "distinct_stroke_lengths_px": distinct_lengths,
            "run_ids": [item["run_id"] for item in group],
        }
        if len(group) < MIN_FIT_RUNS:
            models.append({
                **fit_base,
                "fit_status": "insufficient_data",
                "note": f"Нужно минимум {MIN_FIT_RUNS} частичных замеров; рекомендуется серия из 650, 200, 50 и 10 px.",
            })
            continue
        rank = int(np.linalg.matrix_rank(matrix))
        if rank < 2:
            models.append({
                **fit_base,
                "fit_status": "underdetermined",
                "matrix_rank": rank,
                "note": "Нельзя отдельно оценить стоимость пути и накладные расходы на штрих: наблюдения линейно зависимы. Используйте разные длины штриха.",
            })
            continue
        if len(distinct_lengths) < MIN_DISTINCT_LENGTHS:
            models.append({
                **fit_base,
                "fit_status": "insufficient_data",
                "matrix_rank": rank,
                "note": f"Нужно минимум {MIN_DISTINCT_LENGTHS} разных длин штриха; рекомендуется серия из 650, 200, 50 и 10 px.",
            })
            continue

        target = np.full(len(group), float(point_limit), dtype=np.float64)
        coefficients, _residuals, _rank, _singular = np.linalg.lstsq(matrix, target, rcond=None)
        density, per_stroke = (float(coefficients[0]), float(coefficients[1]))
        if not math.isfinite(density) or not math.isfinite(per_stroke) or density <= 0 or per_stroke <= 0:
            models.append({
                **fit_base,
                "fit_status": "invalid_fit",
                "matrix_rank": rank,
                "raw_coefficients": [density, per_stroke],
                "note": "Получены неположительные коэффициенты; проверьте однородность запаса краски и результаты наблюдений.",
            })
            continue

        midpoint_coefficients = coefficients.copy()
        interval_fit = fit_interval_censored_quota(
            matrix,
            visible_length,
            visible_strokes,
            stroke_lengths,
            float(point_limit),
            midpoint_coefficients,
        )
        if interval_fit["status"] == "feasible":
            coefficients = np.asarray(
                [
                    interval_fit["points_per_path_px"],
                    interval_fit["points_per_stroke"],
                ],
                dtype=np.float64,
            )
            density, per_stroke = float(coefficients[0]), float(coefficients[1])

        predicted = matrix @ coefficients
        absolute_errors = np.abs(predicted - target)
        relative_errors = absolute_errors / float(point_limit) * 100.0
        mean_abs_error = float(np.mean(absolute_errors))
        max_relative_error = float(np.max(relative_errors))
        lower_cutoff_points = visible_length * density + visible_strokes * per_stroke
        upper_cutoff_points = (
            (visible_length + stroke_lengths) * density
            + (visible_strokes + 1.0) * per_stroke
        )
        cutoff_interval_width_points = upper_cutoff_points - lower_cutoff_points
        cutoff_interval_contains_quota = (
            (lower_cutoff_points <= float(point_limit) + CUTOFF_INTERVAL_TOLERANCE_POINTS)
            & (upper_cutoff_points >= float(point_limit) - CUTOFF_INTERVAL_TOLERANCE_POINTS)
        )
        all_cutoff_intervals_consistent = bool(np.all(cutoff_interval_contains_quota))
        maximum_cutoff_interval_width_percent = float(
            np.max(cutoff_interval_width_points) / float(point_limit) * 100.0
        )
        try:
            theoretical_density = estimate_theoretical_points_per_path_px(
                point_step_px=step,
                point_delay_ms=delay,
                frame_rate_fps=measured_fps,
            )
        except ValueError:
            theoretical_density = None
        density_delta = (
            (density - theoretical_density) / theoretical_density * 100.0
            if theoretical_density else None
        )
        fit_status = (
            "calibrated"
            if interval_fit["status"] == "feasible"
            and max_relative_error <= MAX_ACCEPTABLE_RELATIVE_ERROR_PERCENT
            and all_cutoff_intervals_consistent
            else "needs_repeat"
        )
        models.append({
            **fit_base,
            "fit_status": fit_status,
            "fitting_method": (
                "interval_constrained_least_squares_v1"
                if interval_fit["status"] == "feasible"
                else "least_squares_on_cutoff_interval_midpoints_v1_fallback"
            ),
            "interval_fit": interval_fit,
            "midpoint_reference_coefficients": {
                "points_per_path_px": round(float(midpoint_coefficients[0]), 8),
                "points_per_stroke": round(float(midpoint_coefficients[1]), 4),
            },
            "midpoint_fit_error_is_not_a_measurement_of_absolute_accuracy": True,
            "matrix_rank": rank,
            "points_per_path_px": round(density, 8),
            "points_per_stroke": round(per_stroke, 4),
            "equivalent_path_overhead_px_per_stroke": round(per_stroke / density, 4),
            "theoretical_points_per_path_px_from_measured_fps": round(theoretical_density, 8) if theoretical_density else None,
            "empirical_density_delta_from_theory_percent": round(density_delta, 3) if density_delta is not None else None,
            "mean_absolute_midpoint_fit_error_points": round(mean_abs_error, 2),
            "maximum_fit_error_percent_of_quota": round(max_relative_error, 3),
            "cutoff_interval_tolerance_points": CUTOFF_INTERVAL_TOLERANCE_POINTS,
            "all_cutoff_intervals_consistent": all_cutoff_intervals_consistent,
            "cutoff_interval_consistent_run_count": int(np.count_nonzero(cutoff_interval_contains_quota)),
            "cutoff_interval_run_count": len(group),
            "maximum_cutoff_interval_width_points": round(float(np.max(cutoff_interval_width_points)), 2),
            "maximum_cutoff_interval_width_percent_of_quota": round(maximum_cutoff_interval_width_percent, 3),
            "per_run_fit": [
                {
                    "run_id": item["run_id"],
                    "stroke_length_px": item["stroke_length_px"],
                    "observed_visible_path_length_px": item["visible_path_length_px"],
                    "fully_visible_strokes": item["last_visible_strokes"],
                    "cutoff_lower_points_estimate": round(float(lower_cutoff_points[index]), 2),
                    "cutoff_upper_points_estimate": round(float(upper_cutoff_points[index]), 2),
                    "cutoff_interval_width_points": round(float(cutoff_interval_width_points[index]), 2),
                    "cutoff_interval_contains_quota": bool(cutoff_interval_contains_quota[index]),
                    "predicted_points_at_cutoff_interval_midpoint": round(float(predicted[index]), 2),
                    "midpoint_absolute_error_points": round(float(absolute_errors[index]), 2),
                    "midpoint_relative_error_percent": round(float(relative_errors[index]), 3),
                }
                for index, item in enumerate(group)
            ],
            "notes": (
                "Порог наблюдается как интервал между стоимостью последнего полностью видимого штриха "
                "и стоимостью ещё одного штриха. Коэффициенты подогнаны по серединам этих интервалов; "
                "это уменьшает ложную точность, но не доказывает абсолютную точность модели. "
                "Интервалы должны согласоваться с лимитом с допуском на одну точку. "
                "Коэффициенты относятся только к этому профилю движения и частоте кадров."
            ),
        })

    calibrated = [model for model in models if model.get("fit_status") == "calibrated"]
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "model_id": "browser-observed-game-point-calibration-v2-interval",
        "is_engine_exact_counter": False,
        "generated_at": document.get("updated_at"),
        "browser": {
            **dict(normalized["browser"]),
            "frame_probe": probe,
        },
        "input_run_count": len(runs),
        "fit_eligible_run_count": sum(
            1 for run in runs
            if run["outcome"] == "partial" and run["fresh_supply_confirmed"]
        ),
        "excluded_runs": excluded,
        "models": models,
        "summary": (
            "Получена хотя бы одна модель с ошибкой не выше 10%."
            if calibrated
            else "Пока нет модели, удовлетворяющей критерию: нужны повторяемые частичные результаты на нескольких длинах штриха с сопоставимым полным запасом."
        ),
        "interpretation_limits": [
            "RequestAnimationFrame измеряет кадровую частоту видимой вкладки, но не читает внутренний счётчик точек игры напрямую.",
            "Граница расхода задана интервалом между последним полностью видимым и следующим штрихом; коэффициенты подбираются с ограничениями по всем интервалам, а середины используются только как целевая функция и диагностическая метрика.",
            "Узкий интервал и небольшая ошибка подгонки не доказывают абсолютную точность: на результат влияют повторяемость и условия браузера.",
            "Коэффициенты нельзя переносить на другой шаг, задержку, браузерную нагрузку или тип доски без проверки.",
        ],
    }

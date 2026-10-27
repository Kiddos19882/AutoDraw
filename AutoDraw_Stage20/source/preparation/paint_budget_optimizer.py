from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

import numpy as np
from PIL import Image

from color_scanline import ColorScanlinePlanError, build_color_scanline_plan
from paint_cost_model import DEFAULT_PAINT_BUDGET_PX_EQUIVALENT, DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT
from palette_quantization import PaletteQuantizationError, PaletteQuantizationResult, normalize_palette


class PaintBudgetOptimizationError(ValueError):
    """Raised when an image cannot be reduced to a valid paint-budget plan."""


def _validate_index_map(index_map: Any, palette_size: int) -> np.ndarray:
    try:
        indexes = np.asarray(index_map)
    except (TypeError, ValueError) as exc:
        raise PaintBudgetOptimizationError("Не удалось прочитать карту цветов.") from exc
    if indexes.ndim != 2 or not indexes.size:
        raise PaintBudgetOptimizationError("Карта цветов должна быть непустой двумерной матрицей.")
    if indexes.dtype.kind not in "iu":
        raise PaintBudgetOptimizationError("Индексы карты цветов должны быть целыми числами.")
    if int(indexes.min()) < -1 or int(indexes.max()) >= palette_size:
        raise PaintBudgetOptimizationError("Карта содержит индекс за пределами палитры.")
    if not np.any(indexes >= 0):
        raise PaintBudgetOptimizationError("На изображении нет видимых пикселей для рисования.")
    return indexes.astype(np.int32, copy=True)


def _mode_block_map(indexes: np.ndarray, block_size: int) -> np.ndarray:
    """Replace each square block with its most common index while preserving canvas size."""
    if block_size <= 1:
        return indexes.copy()
    height, width = indexes.shape
    output = np.empty_like(indexes)
    for y in range(0, height, block_size):
        y_end = min(height, y + block_size)
        for x in range(0, width, block_size):
            x_end = min(width, x + block_size)
            tile = indexes[y:y_end, x:x_end].reshape(-1)
            values, counts = np.unique(tile, return_counts=True)
            most_common = values[counts == counts.max()]
            # On a tie, keep a visible palette color rather than erasing the tile.
            visible = most_common[most_common >= 0]
            chosen = int(visible.min()) if visible.size else -1
            output[y:y_end, x:x_end] = chosen
    return output


def _row_run_count(row: np.ndarray) -> int:
    valid = row >= 0
    if not bool(np.any(valid)):
        return 0
    starts = valid.copy()
    if row.size > 1:
        starts[1:] &= (~valid[:-1]) | (row[1:] != row[:-1])
    return int(np.count_nonzero(starts))


def _best_row_offset(indexes: np.ndarray, row_step: int) -> int | None:
    """Choose a sampling phase that preserves the most visible pixels for this block size."""
    height = indexes.shape[0]
    best_offset: int | None = None
    best_score: tuple[int, int, int] | None = None
    for offset in range(min(row_step, height)):
        rows = np.arange(offset, height, row_step, dtype=np.int32)
        if not rows.size:
            continue
        sampled = indexes[rows]
        visible_count = int(np.count_nonzero(sampled >= 0))
        if visible_count == 0:
            continue
        run_count = sum(_row_run_count(row) for row in sampled)
        score = (visible_count, -run_count, -offset)
        if best_score is None or score > best_score:
            best_score = score
            best_offset = offset
    return best_offset


def _candidate_plan(
    index_map: np.ndarray,
    palette: Any,
    *,
    block_size: int,
    stroke_overhead: float,
    budget: float,
) -> tuple[dict[str, Any], int] | None:
    offset = _best_row_offset(index_map, block_size)
    if offset is None:
        return None
    try:
        plan = build_color_scanline_plan(
            index_map,
            palette,
            row_step_px=block_size,
            row_offset_px=offset,
            paint_stroke_overhead_px_equivalent=stroke_overhead,
            paint_budget_px_equivalent=budget,
            plan_name="Автоматически упрощённый план под лимит краски",
        )
    except (ColorScanlinePlanError, PaletteQuantizationError, ValueError, TypeError, MemoryError):
        return None
    return plan, offset


def _candidate_sizes(max_size: int) -> list[int]:
    values = list(range(1, min(12, max_size) + 1))
    values.extend((
        14, 16, 18, 20, 22, 24, 28, 32, 40, 48, 56, 64, 80, 96, 112, 128,
        160, 192, 224, 256, 320, 384, 448, 512, 640, 768, 1024, 1536,
        2048, 3072, 4096,
    ))
    return sorted({value for value in values if 1 <= value <= max_size} | {max_size})


def _make_output_image(
    index_map: np.ndarray,
    palette: list[dict[str, Any]],
    source_image: Image.Image,
) -> Image.Image:
    palette_rgb = np.asarray([entry["rgb"] for entry in palette], dtype=np.uint8)
    visible = index_map >= 0
    source_rgba = np.asarray(source_image.convert("RGBA"), dtype=np.uint8)
    rgba = np.zeros((index_map.shape[0], index_map.shape[1], 4), dtype=np.uint8)
    if bool(np.any(visible)):
        rgba[visible, :3] = palette_rgb[index_map[visible]]
        rgba[..., 3][visible] = source_rgba[..., 3][visible]
    has_alpha = "A" in source_image.getbands() or bool(np.any(~visible))
    return Image.fromarray(rgba, mode="RGBA") if has_alpha else Image.fromarray(rgba[..., :3].copy(), mode="RGB")


def _update_palette_report(report: dict[str, Any], index_map: np.ndarray, palette: list[dict[str, Any]]) -> None:
    visible_count = int(np.count_nonzero(index_map >= 0))
    counts = np.bincount(index_map[index_map >= 0], minlength=len(palette)).astype(np.int64)
    palette_stats: list[dict[str, Any]] = []
    used_colors: list[dict[str, Any]] = []
    for entry in palette:
        count = int(counts[int(entry["index"])])
        item = {
            **entry,
            "pixel_count": count,
            "percentage_visible": round(100.0 * count / visible_count, 4) if visible_count else 0.0,
        }
        palette_stats.append(item)
        if count:
            used_colors.append(item)
    report["palette"] = palette_stats
    report["used_colors"] = used_colors
    report["used_palette_color_count"] = len(used_colors)
    report["unused_palette_color_count"] = len(palette) - len(used_colors)
    report["visible_pixel_count"] = visible_count
    report["transparent_pixel_count"] = int(index_map.size - visible_count)


def fit_result_to_paint_budget(
    result: PaletteQuantizationResult,
    palette: Any,
    *,
    paint_budget_px_equivalent: float = DEFAULT_PAINT_BUDGET_PX_EQUIVALENT,
    stroke_overhead_px_equivalent: float = DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT,
    target_usage_percent: float = 75.0,
) -> tuple[PaletteQuantizationResult, int, int, dict[str, Any]]:
    """Coarsen color blocks and sample fewer rows until estimated paint use fits a target."""
    if not isinstance(result, PaletteQuantizationResult):
        raise PaintBudgetOptimizationError("Ожидался результат преобразования изображения этапа 18.")
    if isinstance(target_usage_percent, bool):
        raise PaintBudgetOptimizationError("Целевой расход должен быть числом от 10 до 95%.")
    try:
        target_percent = float(target_usage_percent)
        budget = float(paint_budget_px_equivalent)
        overhead = float(stroke_overhead_px_equivalent)
    except (TypeError, ValueError) as exc:
        raise PaintBudgetOptimizationError("Параметры лимита краски должны быть числами.") from exc
    if not math.isfinite(target_percent) or not 10.0 <= target_percent <= 95.0:
        raise PaintBudgetOptimizationError("Целевой расход должен быть от 10 до 95%.")
    if not math.isfinite(budget) or budget <= 0:
        raise PaintBudgetOptimizationError("Оценочный запас краски должен быть больше нуля.")
    if not math.isfinite(overhead) or overhead < 0:
        raise PaintBudgetOptimizationError("Расход на один штрих должен быть неотрицательным числом.")

    normalized = normalize_palette(palette.get("colors", []) if isinstance(palette, dict) else palette)
    indexes = _validate_index_map(result.index_map, len(normalized))
    if indexes.shape != (result.image.height, result.image.width):
        raise PaintBudgetOptimizationError("Размер карты цветов не соответствует исходному изображению.")
    height, width = indexes.shape
    max_size = max(height, width)
    target_cost = budget * target_percent / 100.0

    baseline_result = _candidate_plan(
        indexes, normalized, block_size=1, stroke_overhead=overhead, budget=budget
    )
    if baseline_result is None:
        raise PaintBudgetOptimizationError("Не удалось построить исходный цветной план.")
    baseline_plan, _ = baseline_result
    baseline_estimate = baseline_plan["summary"]["paint_cost_estimate"]

    chosen_map = indexes.copy()
    chosen_step = 1
    chosen_offset = 0
    chosen_plan = baseline_plan
    fallback_used = False
    tested_sizes: list[int] = [1]

    if float(baseline_estimate["estimated_total_ink_px_equivalent"]) > target_cost:
        last_failed_size = 1
        found = False
        for size in _candidate_sizes(max_size):
            if size <= 1:
                continue
            candidate_map = _mode_block_map(indexes, size)
            candidate_result = _candidate_plan(
                candidate_map, normalized, block_size=size,
                stroke_overhead=overhead, budget=budget,
            )
            tested_sizes.append(size)
            if candidate_result is None:
                last_failed_size = size
                continue
            candidate_plan, candidate_offset = candidate_result
            candidate_cost = float(
                candidate_plan["summary"]["paint_cost_estimate"]["estimated_total_ink_px_equivalent"]
            )
            if candidate_cost <= target_cost:
                # Refine the interval before accepting a coarse step to preserve more detail.
                for refined_size in range(last_failed_size + 1, size):
                    refined_map = _mode_block_map(indexes, refined_size)
                    refined_result = _candidate_plan(
                        refined_map, normalized, block_size=refined_size,
                        stroke_overhead=overhead, budget=budget,
                    )
                    tested_sizes.append(refined_size)
                    if refined_result is None:
                        continue
                    refined_plan, refined_offset = refined_result
                    refined_cost = float(
                        refined_plan["summary"]["paint_cost_estimate"]["estimated_total_ink_px_equivalent"]
                    )
                    if refined_cost <= target_cost:
                        candidate_map = refined_map
                        candidate_plan = refined_plan
                        candidate_offset = refined_offset
                        size = refined_size
                        candidate_cost = refined_cost
                        break
                chosen_map = candidate_map
                chosen_step = size
                chosen_offset = candidate_offset
                chosen_plan = candidate_plan
                found = True
                break
            last_failed_size = size

        if not found:
            # Last-resort guarantee for ordinary board budgets: draw only the source row
            # with the most useful visible content instead of creating an empty plan.
            row_scores = [
                (_row_run_count(indexes[y]), int(np.count_nonzero(indexes[y] >= 0)), y)
                for y in range(height)
            ]
            visible_rows = [item for item in row_scores if item[1] > 0]
            if not visible_rows:
                raise PaintBudgetOptimizationError("Не найдено ни одной видимой строки для резервного плана.")
            _runs, _visible, fallback_offset = max(visible_rows, key=lambda item: (item[1], -item[0], -item[2]))
            fallback_plan = build_color_scanline_plan(
                indexes,
                normalized,
                row_step_px=max_size,
                row_offset_px=fallback_offset,
                paint_stroke_overhead_px_equivalent=overhead,
                paint_budget_px_equivalent=budget,
                plan_name="Резервный однострочный план под лимит краски",
            )
            fallback_cost = float(
                fallback_plan["summary"]["paint_cost_estimate"]["estimated_total_ink_px_equivalent"]
            )
            if fallback_cost <= target_cost:
                chosen_map = indexes.copy()
                chosen_step = max_size
                chosen_offset = fallback_offset
                chosen_plan = fallback_plan
                fallback_used = True
            else:
                coarse_map = _mode_block_map(indexes, max_size)
                coarse_result = _candidate_plan(
                    coarse_map, normalized, block_size=max_size,
                    stroke_overhead=overhead, budget=budget,
                )
                if coarse_result is None:
                    raise PaintBudgetOptimizationError(
                        f"Однострочный резерв требует {fallback_cost:,.0f} px-экв., "
                        f"что выше целевого лимита {target_cost:,.0f}."
                    )
                coarse_plan, coarse_offset = coarse_result
                coarse_cost = float(coarse_plan["summary"]["paint_cost_estimate"]["estimated_total_ink_px_equivalent"])
                if coarse_cost > target_cost:
                    raise PaintBudgetOptimizationError(
                        f"Даже максимально упрощённый план требует {coarse_cost:,.0f} px-экв., "
                        f"что выше целевого лимита {target_cost:,.0f}."
                    )
                chosen_map = coarse_map
                chosen_step = max_size
                chosen_offset = coarse_offset
                chosen_plan = coarse_plan
                fallback_used = True

    output = PaletteQuantizationResult(
        image=_make_output_image(chosen_map, normalized, result.image),
        index_map=chosen_map,
        report=deepcopy(result.report) if isinstance(result.report, dict) else {},
    )
    before_unique = np.unique(indexes[indexes >= 0])
    after_unique = np.unique(chosen_map[chosen_map >= 0])
    changed_count = int(np.count_nonzero(chosen_map != indexes))
    after_estimate = chosen_plan["summary"]["paint_cost_estimate"]
    before_point_estimate = baseline_plan["summary"]["point_quota_estimate"]
    after_point_estimate = chosen_plan["summary"]["point_quota_estimate"]
    target_point_count = math.floor(
        int(after_point_estimate["board_point_limit"]) * target_percent / 100.0
    )
    optimization_report: dict[str, Any] = {
        "enabled": True,
        "method": "progressive_block_mode_plus_row_sampling",
        "target_usage_percent": target_percent,
        "budget_px_equivalent": round(budget, 3),
        "target_cost_px_equivalent": round(target_cost, 3),
        "block_size_px": chosen_step,
        "row_step_px": chosen_step,
        "row_offset_px": chosen_offset,
        "stroke_count_before": int(baseline_plan["summary"]["stroke_count"]),
        "stroke_count_after": int(chosen_plan["summary"]["stroke_count"]),
        "estimated_ink_before_px_equivalent": float(baseline_estimate["estimated_total_ink_px_equivalent"]),
        "estimated_ink_after_px_equivalent": float(after_estimate["estimated_total_ink_px_equivalent"]),
        "estimated_usage_after_percent": float(after_estimate["estimated_usage_percent"]),
        "board_point_limit": int(after_point_estimate["board_point_limit"]),
        "target_point_usage_percent": target_percent,
        "target_point_count": target_point_count,
        "estimated_game_points_before": int(before_point_estimate["estimated_point_count"]),
        "estimated_game_points_after": int(after_point_estimate["estimated_point_count"]),
        "estimated_game_point_usage_after_percent": float(after_point_estimate["estimated_usage_percent"]),
        "estimated_game_point_risk_after": str(after_point_estimate["risk_level"]),
        "game_point_target_met": int(after_point_estimate["estimated_point_count"]) <= target_point_count,
        "used_color_count_before": int(before_unique.size),
        "used_color_count_after": int(after_unique.size),
        "visible_pixel_count_before": int(np.count_nonzero(indexes >= 0)),
        "visible_pixel_count_after": int(np.count_nonzero(chosen_map >= 0)),
        "changed_pixel_count": changed_count,
        "changed_pixel_percentage": round(100.0 * changed_count / indexes.size, 4),
        "sampled_row_omitted_pixel_count": int(chosen_plan["summary"].get("omitted_by_row_step_pixel_count", 0)),
        "tested_block_sizes_px": sorted(set(tested_sizes)),
        "fallback_used": fallback_used,
        "note": (
            "Режим постепенно заменяет квадратные блоки наиболее частым цветом и выбирает "
            "реже расположенные строки, пока оценка не достигает заданной доли бюджета. "
            "Цвета берутся только из исходной игровой палитры; размер холста не меняется. "
            "Это намеренно упрощённый результат, оценка расхода экспериментальная."
        ),
    }
    output.report["paint_budget_optimization"] = optimization_report
    _update_palette_report(output.report, chosen_map, normalized)
    return output, chosen_step, chosen_offset, optimization_report

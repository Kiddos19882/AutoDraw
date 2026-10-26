"""Search geometry-plan candidates against the empirical paint budget."""
from __future__ import annotations

import math
from typing import Any

import cv2
import numpy as np


def _rescale_map_centered(indexes: np.ndarray, scale: float) -> np.ndarray:
    if scale >= 1.0:
        return indexes.copy()
    height, width = indexes.shape
    new_width = max(1, round(width * scale))
    new_height = max(1, round(height * scale))
    # Reduce the sampling grid, then map it back to the original canvas size.
    # Padding the reduced image would make the drawing itself shrink toward the
    # center and leave unused board space; upscaling the reduced grid preserves
    # the source composition while merging nearby pixels into larger color blocks.
    # OpenCV resize does not support CV_32S maps on all supported builds.
    # Palette indexes are small integers, so float32 can represent them exactly.
    source = indexes.astype(np.float32, copy=False)
    reduced = cv2.resize(source, (new_width, new_height), interpolation=cv2.INTER_NEAREST)
    restored = cv2.resize(reduced, (width, height), interpolation=cv2.INTER_NEAREST)
    return np.rint(restored).astype(np.int32, copy=False)


def optimize_geometry_plan_to_budget(
    index_map: Any,
    palette: Any,
    *,
    mode: str,
    paint_budget_px_equivalent: float,
    target_usage_percent: float = 75.0,
    stroke_overhead_px_equivalent: float = 6.67,
    simplify_tolerance_px: float = 0.8,
    source_name: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Search quality-preserving candidates until the estimated ink budget fits.

    The optimizer prefers the largest image scale, then the least component loss and
    the smallest RDP tolerance. If no single-board candidate fits, the best low-cost
    candidate is returned so the caller can offer a multi-board split.
    """
    # Lazy imports avoid a module cycle: the planner delegates candidate search
    # to this module, while the optimizer calls back into the planner to build candidates.
    from geometry_color_plan import (
        GeometryColorPlanError,
        _estimate_geometry_paint_cost,
        _validate_index_map,
        build_geometry_color_plan,
        validate_geometry_color_plan,
    )
    from palette_quantization import normalize_palette

    normalized = normalize_palette(palette.get("colors", []) if isinstance(palette, dict) else palette)
    original = _validate_index_map(index_map, len(normalized))
    try:
        budget = float(paint_budget_px_equivalent)
        target = float(target_usage_percent)
        overhead = float(stroke_overhead_px_equivalent)
    except (TypeError, ValueError) as exc:
        raise GeometryColorPlanError("Параметры бюджета должны быть числами.") from exc
    if not math.isfinite(budget) or budget <= 0:
        raise GeometryColorPlanError("Бюджет краски должен быть больше нуля.")
    if not math.isfinite(target) or not 10 <= target <= 95:
        raise GeometryColorPlanError("Целевой расход должен быть от 10 до 95%.")
    if not math.isfinite(overhead) or overhead < 0:
        raise GeometryColorPlanError("Расход на один штрих должен быть неотрицательным.")
    target_cost = budget * target / 100.0
    before = build_geometry_color_plan(
        original, normalized, mode=mode, simplify_tolerance_px=0.0,
        min_component_area=1, source_name=source_name,
    )
    before_estimate = _estimate_geometry_paint_cost(
        before,
        stroke_overhead_px_equivalent=overhead,
        paint_budget_px_equivalent=budget,
    )
    scales = (1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3)
    tolerances = tuple(sorted(set((0.0, float(simplify_tolerance_px), 1.0, 2.0, 3.5, 5.0)))
                        )
    component_thresholds = (1, 2, 4, 8, 16)
    best: dict[str, Any] | None = None
    best_report: dict[str, Any] | None = None
    target_fits_at_scale = False
    source_visible = int(np.count_nonzero(original >= 0))

    for scale in scales:
        scaled_map = _rescale_map_centered(original, scale)
        candidates: list[tuple[tuple[float, float, int], dict[str, Any], dict[str, Any]]] = []
        for min_area in component_thresholds:
            for tolerance in tolerances:
                try:
                    candidate = build_geometry_color_plan(
                        scaled_map, normalized, mode=mode,
                        simplify_tolerance_px=tolerance,
                        min_component_area=min_area,
                        source_name=source_name,
                    )
                    estimate = _estimate_geometry_paint_cost(
                        candidate,
                        stroke_overhead_px_equivalent=overhead,
                        paint_budget_px_equivalent=budget,
                    )
                except (GeometryColorPlanError, ValueError, TypeError, MemoryError):
                    continue
                cost = float(estimate["estimated_total_ink_px_equivalent"])
                visible = int(candidate["summary"]["visible_pixel_count"])
                quality = (float(source_visible - visible), float(tolerance), min_area)
                report = {
                    "enabled": True,
                    "mode": mode,
                    "scale": scale,
                    "min_component_area": min_area,
                    "simplify_tolerance_px": tolerance,
                    "source_visible_pixel_count": source_visible,
                    "retained_visible_pixel_count": visible,
                    "estimated_ink_before_px_equivalent": before_estimate["estimated_total_ink_px_equivalent"],
                    "estimated_ink_after_px_equivalent": cost,
                    "target_cost_px_equivalent": round(target_cost, 3),
                    "paint_budget_px_equivalent": budget,
                    "target_usage_percent": target,
                    "fits_budget": cost <= target_cost,
                    "needs_multi_board_split": cost > target_cost,
                }
                if best is None or cost < float(best_report["estimated_ink_after_px_equivalent"]):
                    best, best_report = candidate, report
                if cost <= target_cost:
                    candidates.append((quality, candidate, report))
        if candidates:
            _quality, best_at_scale, report_at_scale = min(candidates, key=lambda item: item[0])
            best, best_report = best_at_scale, report_at_scale
            target_fits_at_scale = True
            break

    if best is None or best_report is None:
        raise GeometryColorPlanError("Не удалось построить ни одного допустимого геометрического плана.")
    best["generation"]["budget_optimization"] = dict(best_report)
    best["summary"]["paint_cost_estimate"] = _estimate_geometry_paint_cost(
        best,
        stroke_overhead_px_equivalent=overhead,
        paint_budget_px_equivalent=budget,
    )
    best_report["fits_budget"] = bool(
        best_report["estimated_ink_after_px_equivalent"] <= target_cost
    )
    best_report["needs_multi_board_split"] = not best_report["fits_budget"]
    best_report["target_fits_at_scale"] = target_fits_at_scale
    return validate_geometry_color_plan(best), best_report



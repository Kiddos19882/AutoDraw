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


def measure_geometry_plan_quality(index_map: Any, plan: dict[str, Any]) -> dict[str, Any]:
    """Compare a rasterized geometry plan with the indexed source image pixel by pixel."""
    from geometry_color_plan import (
        _validate_index_map,
        render_geometry_color_preview,
        validate_geometry_color_plan,
    )

    validated = validate_geometry_color_plan(plan)
    source = np.asarray(index_map)
    canvas = validated["canvas"]
    width, height = int(canvas["width"]), int(canvas["height"])
    if source.shape != (height, width):
        raise ValueError("Размер исходной карты не совпадает с геометрическим планом.")
    source = _validate_index_map(source, len(validated["palette"]))

    preview = render_geometry_color_preview(validated, max_dimension=max(width, height))
    rgba = np.asarray(preview.convert("RGBA"))
    if rgba.shape[:2] != source.shape:
        raise ValueError("Не удалось получить предпросмотр геометрического плана в исходном масштабе.")

    rendered_indexes = np.full(source.shape, -1, dtype=np.int32)
    alpha = rgba[:, :, 3] > 0
    for color in validated["palette"]:
        rgb = np.asarray(color["rgb"], dtype=np.uint8)
        matches = alpha & np.all(rgba[:, :, :3] == rgb, axis=2)
        rendered_indexes[matches] = int(color["index"])

    source_indexes = source.astype(np.int32, copy=False)
    mismatches = rendered_indexes != source_indexes
    mismatch_count = int(np.count_nonzero(mismatches))
    total_pixels = int(source.size)
    source_visible = source_indexes >= 0
    visible_count = int(np.count_nonzero(source_visible))
    exact_visible_matches = int(np.count_nonzero((rendered_indexes == source_indexes) & source_visible))
    visible_accuracy = 100.0 * exact_visible_matches / visible_count if visible_count else 100.0

    return {
        "quality_measure": "exact_preview_rgb_pixel_comparison_v1",
        "quality_measure_scope": "programmatic_preview",
        "quality_is_preview_estimate": True,
        "quality_measure_note": (
            "Сравнение точное относительно программного предпросмотра, но не гарантирует "
            "пиксель-в-пиксель совпадение с браузерной игрой: фактический след мыши и отрисовка могут отличаться."
        ),
        "quality_pixel_count": total_pixels,
        "quality_mismatch_pixel_count": mismatch_count,
        "quality_mismatch_percent": round(100.0 * mismatch_count / total_pixels, 4) if total_pixels else 0.0,
        "quality_pixel_accuracy_percent": round(100.0 * (total_pixels - mismatch_count) / total_pixels, 4)
        if total_pixels else 100.0,
        "quality_source_visible_pixel_count": visible_count,
        "quality_exact_visible_pixel_count": exact_visible_matches,
        "quality_visible_pixel_accuracy_percent": round(visible_accuracy, 4),
    }


def optimize_geometry_plan_to_budget(
    index_map: Any,
    palette: Any,
    *,
    mode: str,
    paint_budget_px_equivalent: float,
    target_usage_percent: float = 75.0,
    stroke_overhead_px_equivalent: float = 6.67,
    simplify_tolerance_px: float = 0.8,
    min_component_area: int = 1,
    source_name: str | None = None,
    board_point_limit: int = 6_000,
    point_safety_factor: float = 0.85,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Search candidates against separate paint-cost and game-point safety budgets.

    Both constraints must fit before a candidate is accepted. If no single-board
    candidate fits, return the candidate with the lowest normalized combined
    budget pressure so the caller can offer a multi-board split.
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
    from engine_point_calibration import estimate_point_quota_usage

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
    if (
        isinstance(min_component_area, bool)
        or not isinstance(min_component_area, int)
        or min_component_area < 1
    ):
        raise GeometryColorPlanError("Минимальная площадь компонента должна быть целым числом от 1.")
    if isinstance(board_point_limit, bool) or not isinstance(board_point_limit, int) or board_point_limit < 1:
        raise GeometryColorPlanError("Лимит игровых точек должен быть положительным целым числом.")
    try:
        point_factor = float(point_safety_factor)
    except (TypeError, ValueError) as exc:
        raise GeometryColorPlanError("Коэффициент запаса игровых точек должен быть числом.") from exc
    if not math.isfinite(point_factor) or not 0 < point_factor <= 1:
        raise GeometryColorPlanError("Коэффициент запаса игровых точек должен быть больше 0 и не больше 1.")
    target_cost = budget * target / 100.0
    target_points = math.floor(board_point_limit * point_factor)
    if target_points < 1:
        raise GeometryColorPlanError("Безопасный бюджет игровых точек должен быть положительным.")
    before_cost: float | None = None
    baseline_note: str | None = None
    try:
        before = build_geometry_color_plan(
            original, normalized, mode=mode, simplify_tolerance_px=0.0,
            min_component_area=1, source_name=source_name,
        )
        before_estimate = _estimate_geometry_paint_cost(
            before,
            stroke_overhead_px_equivalent=overhead,
            paint_budget_px_equivalent=budget,
        )
        before_cost = float(before_estimate["estimated_total_ink_px_equivalent"])
    except (GeometryColorPlanError, ValueError, TypeError, MemoryError) as exc:
        # Do not block optimization merely because the unoptimized source has
        # too many strokes to serialize. Smaller sampling grids may still fit.
        baseline_note = str(exc)
    scales = (1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.25, 0.2, 0.15, 0.1, 0.075, 0.05)
    tolerances = tuple(sorted(set((0.0, float(simplify_tolerance_px), 1.0, 2.0, 3.5, 5.0)))
                        )
    component_thresholds = tuple(sorted({
        min_component_area,
        *[value for value in (1, 2, 4, 8, 16, 32, 64) if value >= min_component_area],
    }))
    best: dict[str, Any] | None = None
    best_report: dict[str, Any] | None = None
    best_pressure = math.inf
    target_fits_at_scale = False
    source_visible = int(np.count_nonzero(original >= 0))

    for scale in scales:
        scaled_map = _rescale_map_centered(original, scale)
        candidates: list[tuple[tuple[int, float, int, float], dict[str, Any], dict[str, Any]]] = []
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
                point_estimate = estimate_point_quota_usage(
                    drawing_length_px=float(estimate["drawing_length_px"]),
                    stroke_count=int(estimate["stroke_count"]),
                    single_pixel_stroke_count=int(estimate["single_pixel_stroke_count"]),
                    board_point_limit=board_point_limit,
                    safety_factor=point_factor,
                )
                fits_paint_budget = cost <= target_cost
                fits_point_budget = int(point_estimate["estimated_point_count"]) <= target_points
                fits_both_budgets = fits_paint_budget and fits_point_budget
                point_count = int(point_estimate["estimated_point_count"])
                pressure = max(cost / target_cost, point_count / target_points)
                report = {
                    "enabled": True,
                    "mode": mode,
                    "scale": scale,
                    "min_component_area": min_area,
                    "simplify_tolerance_px": tolerance,
                    "source_visible_pixel_count": source_visible,
                    "retained_visible_pixel_count": visible,
                    "estimated_ink_before_px_equivalent": before_cost,
                    "baseline_plan_available": before_cost is not None,
                    "baseline_note": baseline_note,
                    "estimated_ink_after_px_equivalent": cost,
                    "target_cost_px_equivalent": round(target_cost, 3),
                    "paint_budget_px_equivalent": budget,
                    "target_usage_percent": target,
                    "fits_paint_budget": fits_paint_budget,
                    "estimated_game_points_after": point_count,
                    "board_point_limit": board_point_limit,
                    "target_point_count": target_points,
                    "point_safety_factor": point_factor,
                    "point_quota_estimate": point_estimate,
                    "fits_point_budget": fits_point_budget,
                    "combined_budget_pressure": round(pressure, 6),
                    "fits_budget": fits_both_budgets,
                    "needs_multi_board_split": not fits_both_budgets,
                }
                if best is None or pressure < best_pressure or (
                    math.isclose(pressure, best_pressure)
                    and cost < float(best_report["estimated_ink_after_px_equivalent"])
                ):
                    best, best_report, best_pressure = candidate, report, pressure
                if fits_both_budgets:
                    quality_report = measure_geometry_plan_quality(original, candidate)
                    report.update(quality_report)
                    quality = (
                        int(quality_report["quality_mismatch_pixel_count"]),
                        float(tolerance),
                        min_area,
                        pressure,
                        cost,
                    )
                    candidates.append((quality, candidate, report))
        if candidates:
            _quality, best_at_scale, report_at_scale = min(candidates, key=lambda item: item[0])
            best, best_report = best_at_scale, report_at_scale
            target_fits_at_scale = True
            break

    if best is None or best_report is None:
        raise GeometryColorPlanError("Не удалось построить ни одного допустимого геометрического плана.")
    if "quality_mismatch_pixel_count" not in best_report:
        best_report.update(measure_geometry_plan_quality(original, best))
    best["generation"]["budget_optimization"] = dict(best_report)
    best["summary"]["paint_cost_estimate"] = _estimate_geometry_paint_cost(
        best,
        stroke_overhead_px_equivalent=overhead,
        paint_budget_px_equivalent=budget,
    )
    best_report["fits_paint_budget"] = bool(
        best_report["estimated_ink_after_px_equivalent"] <= target_cost
    )
    best_report["fits_point_budget"] = bool(
        best_report["estimated_game_points_after"] <= target_points
    )
    best_report["fits_budget"] = bool(
        best_report["fits_paint_budget"] and best_report["fits_point_budget"]
    )
    best_report["needs_multi_board_split"] = not best_report["fits_budget"]
    best_report["target_fits_at_scale"] = target_fits_at_scale
    return validate_geometry_color_plan(best), best_report

def optimize_geometry_plan_across_modes(
    index_map: Any,
    palette: Any,
    *,
    paint_budget_px_equivalent: float,
    target_usage_percent: float = 75.0,
    stroke_overhead_px_equivalent: float = 6.67,
    simplify_tolerance_px: float = 0.8,
    min_component_area: int = 1,
    source_name: str | None = None,
    board_point_limit: int = 6_000,
    point_safety_factor: float = 0.85,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Evaluate scanline, contour and skeleton plans against paint and point budgets."""
    from geometry_color_plan import GeometryColorPlanError, validate_geometry_color_plan

    candidates: list[tuple[tuple[int, float, float, float, int], dict[str, Any], dict[str, Any]]] = []
    failures: list[str] = []
    for mode_priority, mode in enumerate(("scanline", "contour", "skeleton")):
        try:
            plan, report = optimize_geometry_plan_to_budget(
                index_map,
                palette,
                mode=mode,
                paint_budget_px_equivalent=paint_budget_px_equivalent,
                target_usage_percent=target_usage_percent,
                stroke_overhead_px_equivalent=stroke_overhead_px_equivalent,
                simplify_tolerance_px=simplify_tolerance_px,
                min_component_area=min_component_area,
                source_name=source_name,
                board_point_limit=board_point_limit,
                point_safety_factor=point_safety_factor,
            )
        except (GeometryColorPlanError, ValueError, TypeError, MemoryError) as exc:
            failures.append(f"{mode}: {exc}")
            continue

        # If at least one candidate fits, choose by measured pixel fidelity first.
        # If none fit, preserve the existing policy of returning the cheapest candidate
        # and flagging that a multi-board split is needed.
        if report["fits_budget"]:
            key = (
                0,
                int(report.get("quality_mismatch_pixel_count", 0)),
                -float(report.get("scale", 1.0)),
                float(report.get("combined_budget_pressure", report["estimated_ink_after_px_equivalent"])),
                mode_priority,
            )
        else:
            key = (
                1,
                float(report.get("combined_budget_pressure", report["estimated_ink_after_px_equivalent"])),
                float(report.get("quality_mismatch_pixel_count", 0)),
                -float(report.get("scale", 1.0)),
                mode_priority,
            )
        candidates.append((key, plan, report))

    if not candidates:
        joined = "; ".join(failures) or "нет допустимых режимов"
        raise ValueError(f"Не удалось построить геометрический план ни в одном режиме: {joined}")

    _key, best_plan, chosen_report = min(candidates, key=lambda item: item[0])
    mode_summaries = [
        {
            "mode": report["mode"],
            "fits_budget": bool(report["fits_budget"]),
            "scale": float(report["scale"]),
            "stroke_count": int(plan["summary"]["stroke_count"]),
            "estimated_ink_after_px_equivalent": float(report["estimated_ink_after_px_equivalent"]),
            "estimated_game_points_after": int(report["estimated_game_points_after"]),
            "target_point_count": int(report["target_point_count"]),
            "fits_paint_budget": bool(report["fits_paint_budget"]),
            "fits_point_budget": bool(report["fits_point_budget"]),
            "combined_budget_pressure": float(report["combined_budget_pressure"]),
            "quality_mismatch_pixel_count": int(report.get("quality_mismatch_pixel_count", 0)),
            "quality_pixel_accuracy_percent": float(report.get("quality_pixel_accuracy_percent", 0.0)),
        }
        for _score, plan, report in candidates
    ]
    chosen_report = dict(chosen_report)
    chosen_report["requested_mode"] = "automatic"
    chosen_report["mode_candidates"] = mode_summaries
    chosen_report["automatic_selection_policy"] = (
        "A candidate fits only when both paint cost and calibrated game-point estimate are within their safety targets. "
        "Among fitting candidates: fewest exact-color pixel mismatches, then highest sampling scale, then lowest combined "
        "budget pressure. If none fits, choose the lowest normalized combined pressure and flag multi-board splitting."
    )
    best_plan["generation"]["budget_optimization"] = dict(chosen_report)
    return validate_geometry_color_plan(best_plan), chosen_report


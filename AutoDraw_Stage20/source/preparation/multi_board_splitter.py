"""Spatial partitioning and export of multi-board geometry plans."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

_EPSILON = 1e-7


def _point_distance(first: tuple[float, float], second: tuple[float, float]) -> float:
    return math.hypot(second[0] - first[0], second[1] - first[1])


def _clip_segment(
    first: tuple[float, float],
    last: tuple[float, float],
    xmin: float,
    ymin: float,
    xmax: float,
    ymax: float,
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    """Liang-Barsky segment clipping."""
    x0, y0 = first
    x1, y1 = last
    dx, dy = x1 - x0, y1 - y0
    p = (-dx, dx, -dy, dy)
    q = (x0 - xmin, xmax - x0, y0 - ymin, ymax - y0)
    u0, u1 = 0.0, 1.0
    for pi, qi in zip(p, q):
        if abs(pi) < _EPSILON:
            if qi < 0:
                return None
            continue
        t = qi / pi
        if pi < 0:
            u0 = max(u0, t)
        else:
            u1 = min(u1, t)
        if u0 > u1:
            return None
    return (x0 + u0 * dx, y0 + u0 * dy), (x0 + u1 * dx, y0 + u1 * dy)


def _clip_stroke_to_tile(
    stroke: dict[str, Any],
    tile: tuple[int, int, int, int],
) -> list[dict[str, Any]]:
    x0, y0, x1, y1 = tile
    xmin, ymin, xmax, ymax = float(x0), float(y0), float(x1 - 1), float(y1 - 1)
    points = [(float(p["x"]), float(p["y"])) for p in stroke["points"]]
    closed = bool(stroke.get("closed"))
    segments = list(zip(points, points[1:]))
    if closed and len(points) >= 3 and _point_distance(points[-1], points[0]) > _EPSILON:
        segments.append((points[-1], points[0]))
    if not segments:
        return []

    pieces: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    for first, last in segments:
        clipped = _clip_segment(first, last, xmin, ymin, xmax, ymax)
        if clipped is None:
            if len(current) >= 2:
                pieces.append(current)
            current = []
            continue
        start, end = clipped
        continues = bool(current) and _point_distance(current[-1], start) <= 1e-5
        if not continues:
            if len(current) >= 2:
                pieces.append(current)
            current = [start, end]
        else:
            if _point_distance(current[-1], end) > _EPSILON:
                current.append(end)
        # If a segment was clipped at either end, the path is broken at this tile edge.
        reached_end = _point_distance(end, last) <= 1e-5
        reached_start = _point_distance(start, first) <= 1e-5
        if not (reached_end and reached_start):
            if len(current) >= 2:
                pieces.append(current)
            current = []
    if len(current) >= 2:
        pieces.append(current)

    output: list[dict[str, Any]] = []
    for piece in pieces:
        local = [(max(0.0, x - x0), max(0.0, y - y0)) for x, y in piece]
        clean: list[tuple[float, float]] = []
        for point in local:
            if not clean or _point_distance(clean[-1], point) > _EPSILON:
                clean.append(point)
        if len(clean) == 1:
            clean.append(clean[0])
        if len(clean) < 2:
            continue
        copied = {
            "name": str(stroke.get("name", "stroke")) + f"_tile_{x0}_{y0}_{len(output) + 1}",
            "points": [{"x": x, "y": y} for x, y in clean],
            "closed": False,
            "color": dict(stroke["color"]),
            "metadata": {**dict(stroke.get("metadata", {})), "clipped_from": stroke.get("name", "")},
        }
        output.append(copied)
    return output


def split_geometry_plan_to_boards(
    plan: Any,
    *,
    paint_budget_px_equivalent: float,
    target_usage_percent: float = 75.0,
    stroke_overhead_px_equivalent: float = 6.67,
    min_tile_size: int = 24,
    max_boards: int = 64,
    board_width: int = 660,
    board_height: int = 340,
) -> dict[str, Any]:
    """Partition an already-optimized vector plan into spatial tile plans.

    Paths are clipped to tile rectangles, not re-contoured from each crop. Therefore
    artificial color borders are not introduced along tile edges. Tile plans preserve
    the original full canvas size expected by the executor; their path coordinates are
    local to each tile. The manifest records source rectangles for later stitching.
    """
    # Lazy imports avoid a cycle: the geometry planner delegates tiling here.
    from geometry_color_plan import (
        GEOMETRY_PLAN_TYPE,
        GeometryColorPlanError,
        _estimate_geometry_paint_cost,
        _orient_and_order_strokes,
        _summarize_plan,
        validate_geometry_color_plan,
    )

    data = validate_geometry_color_plan(plan)
    budget = float(paint_budget_px_equivalent)
    target = float(target_usage_percent)
    overhead = float(stroke_overhead_px_equivalent)
    if not math.isfinite(budget) or budget <= 0:
        raise GeometryColorPlanError("Бюджет краски должен быть больше нуля.")
    if not 10 <= target <= 95 or not math.isfinite(target):
        raise GeometryColorPlanError("Целевой расход должен быть от 10 до 95%.")
    if min_tile_size < 2 or max_boards < 1:
        raise GeometryColorPlanError("Недопустимые параметры разбиения на доски.")
    if isinstance(board_width, bool) or isinstance(board_height, bool) or board_width < 2 or board_height < 2:
        raise GeometryColorPlanError("Размеры физической доски должны быть целыми числами от 2.")
    width, height = int(data["canvas"]["width"]), int(data["canvas"]["height"])
    target_cost = budget * target / 100.0
    pending = [(0, 0, width, height)]
    accepted: list[tuple[tuple[int, int, int, int], list[dict[str, Any]], dict[str, Any]]] = []

    def tile_strokes(tile: tuple[int, int, int, int]) -> list[dict[str, Any]]:
        clipped: list[dict[str, Any]] = []
        for stroke in data["strokes"]:
            clipped.extend(_clip_stroke_to_tile(stroke, tile))
        # The local tile plan uses the same physical board dimensions, so coordinates
        # stay near the origin and are accepted by the current stage-20 area validator.
        return _orient_and_order_strokes(clipped, True)

    while pending:
        if len(pending) + len(accepted) > max_boards:
            raise GeometryColorPlanError(
                f"Разбиение потребовало бы больше {max_boards} досок. Увеличьте допустимый бюджет или упростите изображение."
            )
        tile = pending.pop(0)
        x0, y0, x1, y1 = tile
        strokes = tile_strokes(tile)
        if not strokes:
            continue
        draft = _summarize_plan(
            strokes, data["palette"], board_width, board_height,
            visible_pixel_count=0, transparent_pixel_count=board_width * board_height,
            generation={
                **data["generation"],
                "tile": {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0},
                "coverage_metrics_available": False,
            },
            name=f"{data.get('name', 'Геометрический план')} — фрагмент",
            source={**data.get("source", {}), "source_tile": {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0}},
        )
        estimate = _estimate_geometry_paint_cost(
            draft, stroke_overhead_px_equivalent=overhead, paint_budget_px_equivalent=budget
        )
        cost = float(estimate["estimated_total_ink_px_equivalent"])
        tile_width, tile_height = x1 - x0, y1 - y0
        if tile_width > board_width or tile_height > board_height:
            if tile_width / max(1, board_width) >= tile_height / max(1, board_height) and tile_width > board_width:
                middle = x0 + tile_width // 2
                pending[0:0] = [(x0, y0, middle, y1), (middle, y0, x1, y1)]
            else:
                middle = y0 + tile_height // 2
                pending[0:0] = [(x0, y0, x1, middle), (x0, middle, x1, y1)]
            continue
        if cost <= target_cost or (tile_width <= min_tile_size and tile_height <= min_tile_size):
            draft["summary"]["paint_cost_estimate"] = estimate
            accepted.append((tile, strokes, draft))
            continue

        if tile_width >= tile_height and tile_width > min_tile_size:
            middle = x0 + tile_width // 2
            pending[0:0] = [(x0, y0, middle, y1), (middle, y0, x1, y1)]
        elif tile_height > min_tile_size:
            middle = y0 + tile_height // 2
            pending[0:0] = [(x0, y0, x1, middle), (x0, middle, x1, y1)]
        else:
            draft["summary"]["paint_cost_estimate"] = estimate
            accepted.append((tile, strokes, draft))

    boards: list[dict[str, Any]] = []
    for index, (tile, _strokes, board_plan) in enumerate(accepted, start=1):
        x0, y0, x1, y1 = tile
        bounds = {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0}
        board_plan["name"] = f"{data.get('name', 'План')} — доска {index}"
        board_plan["source"]["source_tile"] = bounds
        board_plan["generation"]["tile"] = bounds
        board_plan["generation"]["board_index"] = index
        board_plan["generation"]["board_count"] = len(accepted)
        board_plan["generation"]["paint_budget_optimization"] = {
            "target_cost_px_equivalent": round(target_cost, 3),
            "estimated_ink_after_px_equivalent": board_plan["summary"]["paint_cost_estimate"]["estimated_total_ink_px_equivalent"],
            "fits_budget": board_plan["summary"]["paint_cost_estimate"]["estimated_total_ink_px_equivalent"] <= target_cost,
        }
        boards.append(validate_geometry_color_plan(board_plan))
    return {
        "schema_version": 1,
        "plan_type": "autodraw_multi_board_manifest",
        "source_plan_type": GEOMETRY_PLAN_TYPE,
        "source_plan_name": str(data.get("name", "Геометрический план")),
        "canvas": {"width": width, "height": height},
        "board_size": {"width": board_width, "height": board_height},
        "target_budget_px_equivalent": budget,
        "target_usage_percent": target,
        "board_count": len(boards),
        "boards": [
            {
                "board_index": index,
                "tile": dict(board["source"]["source_tile"]),
                "stroke_count": board["summary"]["stroke_count"],
                "estimated_ink_px_equivalent": board["summary"]["paint_cost_estimate"]["estimated_total_ink_px_equivalent"],
                "fits_budget": board["generation"]["paint_budget_optimization"]["fits_budget"],
                "plan": board,
            }
            for index, board in enumerate(boards, start=1)
        ],
        "notes": [
            "Это разбиение по пространственным областям, а не произвольное распределение штрихов между досками.",
            "Каждый дочерний план рисуется на холсте полного размера; траектории локализованы у начала холста.",
            "Для сборки общей картинки используйте метаданные tile и обрезайте соответствующие прямоугольники с готовых досок.",
            "Расход оценивается экспериментальной моделью; результат нужно сверять с реальным счётчиком игры.",
        ],
    }


def save_multi_board_manifest(path: str | Path, manifest: Any) -> Path:
    from geometry_color_plan import GeometryColorPlanError

    if not isinstance(manifest, dict) or manifest.get("plan_type") != "autodraw_multi_board_manifest":
        raise GeometryColorPlanError("Это не манифест многодосочного плана.")
    output = Path(path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    output.write_text(payload, encoding="utf-8")
    return output

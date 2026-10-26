from __future__ import annotations

from dataclasses import dataclass
from math import acos, degrees, hypot, isfinite
from typing import Iterable

import cv2
import numpy as np

from models import DrawingPlan, Point, Stroke


@dataclass(frozen=True, slots=True)
class StrokeOptimizationSettings:
    """Настройки оптимизации DrawingPlan.

    minimum_stroke_length_px используется только для диагностики, пока
    remove_short_strokes=False. Фильтрация коротких штрихов выключена по умолчанию.
    Объединение отдельных открытых штрихов также выключено, поскольку соединитель
    между ними может появиться на изображении.
    """

    simplify_tolerance_px: float = 0.5
    reorder_strokes: bool = True
    reverse_open_strokes: bool = True
    rotate_closed_strokes: bool = True
    minimum_stroke_length_px: float = 0.0
    remove_short_strokes: bool = False
    merge_open_strokes: bool = False
    max_merge_gap_px: float = 2.0
    max_join_angle_deg: float = 25.0

    def __post_init__(self) -> None:
        numeric = {
            "Допуск упрощения": self.simplify_tolerance_px,
            "Минимальная длина штриха": self.minimum_stroke_length_px,
            "Максимальный промежуток объединения": self.max_merge_gap_px,
            "Максимальный угол объединения": self.max_join_angle_deg,
        }
        for label, value in numeric.items():
            if not isfinite(value):
                raise ValueError(f"{label} должен быть конечным числом.")
        if self.simplify_tolerance_px < 0:
            raise ValueError("Допуск упрощения не может быть отрицательным.")
        if self.minimum_stroke_length_px < 0:
            raise ValueError("Минимальная длина штриха не может быть отрицательной.")
        if self.max_merge_gap_px < 0:
            raise ValueError("Максимальный промежуток объединения не может быть отрицательным.")
        if not 0 <= self.max_join_angle_deg <= 90:
            raise ValueError("Угол объединения должен находиться в диапазоне 0–90 градусов.")

    def to_dict(self) -> dict:
        return {
            "simplify_tolerance_px": self.simplify_tolerance_px,
            "reorder_strokes": self.reorder_strokes,
            "reverse_open_strokes": self.reverse_open_strokes,
            "rotate_closed_strokes": self.rotate_closed_strokes,
            "minimum_stroke_length_px": self.minimum_stroke_length_px,
            "remove_short_strokes": self.remove_short_strokes,
            "merge_open_strokes": self.merge_open_strokes,
            "max_merge_gap_px": self.max_merge_gap_px,
            "max_join_angle_deg": self.max_join_angle_deg,
        }


@dataclass(frozen=True, slots=True)
class PlanMetrics:
    stroke_count: int
    point_count: int
    drawing_length_px: float
    pen_up_distance_px: float
    estimated_move_calls: int

    def to_dict(self) -> dict:
        return {
            "stroke_count": self.stroke_count,
            "point_count": self.point_count,
            "drawing_length_px": round(self.drawing_length_px, 3),
            "pen_up_distance_px": round(self.pen_up_distance_px, 3),
            "estimated_move_calls_at_2px_step": self.estimated_move_calls,
        }


@dataclass(slots=True)
class OptimizationResult:
    original_plan: DrawingPlan
    optimized_plan: DrawingPlan
    original_metrics: PlanMetrics
    optimized_metrics: PlanMetrics
    short_strokes_detected: int
    short_strokes_removed: int
    points_removed_by_simplification: int
    merged_stroke_pairs: int
    settings: StrokeOptimizationSettings


def measure_plan(plan: DrawingPlan, point_step_px: float = 2.0) -> PlanMetrics:
    return PlanMetrics(
        stroke_count=plan.stroke_count,
        point_count=sum(len(stroke.points) for stroke in plan.strokes),
        drawing_length_px=plan.total_drawing_length_px,
        pen_up_distance_px=plan.pen_up_distance_px,
        estimated_move_calls=plan.estimated_move_calls(point_step_px),
    )


def _copy_stroke(stroke: Stroke, *, points: list[Point] | None = None,
                 name: str | None = None, closed: bool | None = None,
                 metadata: dict[str, str] | None = None) -> Stroke:
    return Stroke(
        name=name if name is not None else stroke.name,
        points=list(points if points is not None else stroke.points),
        closed=stroke.closed if closed is None else closed,
        metadata=dict(stroke.metadata if metadata is None else metadata),
    )


def _simplify_stroke(stroke: Stroke, tolerance_px: float) -> Stroke:
    if tolerance_px <= 0 or len(stroke.points) <= (3 if stroke.closed else 2):
        return _copy_stroke(stroke)

    coordinates = np.asarray([(p.x, p.y) for p in stroke.points], dtype=np.float32).reshape(-1, 1, 2)
    simplified = cv2.approxPolyDP(coordinates, epsilon=float(tolerance_px), closed=stroke.closed)
    # approxPolyDP returns existing contour vertices, but float32 conversion can slightly
    # change their decimal representation. Snap each output vertex back to its nearest
    # original Point so endpoints and source coordinates remain exact.
    source_points = list(stroke.points)
    new_points: list[Point] = []
    for raw in simplified.reshape(-1, 2):
        nearest = min(source_points, key=lambda point: hypot(point.x - float(raw[0]), point.y - float(raw[1])))
        if not new_points or nearest != new_points[-1]:
            new_points.append(nearest)
    if not stroke.closed and len(new_points) >= 2:
        new_points[0] = stroke.points[0]
        new_points[-1] = stroke.points[-1]

    # Never let approximation collapse a valid path into an invalid or degenerate stroke.
    unique = {(round(point.x, 5), round(point.y, 5)) for point in new_points}
    minimum_points = 3 if stroke.closed else 2
    if len(unique) < minimum_points:
        return _copy_stroke(stroke)

    candidate = _copy_stroke(stroke, points=new_points)
    if candidate.closed and candidate.length_px <= 0:
        return _copy_stroke(stroke)
    return candidate


def _normalized_vector(start: Point, end: Point) -> tuple[float, float] | None:
    dx = end.x - start.x
    dy = end.y - start.y
    length = hypot(dx, dy)
    if length <= 1e-9:
        return None
    return dx / length, dy / length


def _angle_between_vectors(first: tuple[float, float], second: tuple[float, float]) -> float:
    dot = max(-1.0, min(1.0, first[0] * second[0] + first[1] * second[1]))
    return degrees(acos(dot))


def _oriented_open_stroke(stroke: Stroke, current: Point, allow_reverse: bool) -> Stroke:
    if stroke.closed or not allow_reverse:
        return _copy_stroke(stroke)
    if stroke.points[-1].distance_to(current) < stroke.points[0].distance_to(current):
        return _copy_stroke(stroke, points=list(reversed(stroke.points)))
    return _copy_stroke(stroke)


def _rotate_closed_stroke(stroke: Stroke, current: Point) -> Stroke:
    if not stroke.closed or len(stroke.points) < 3:
        return _copy_stroke(stroke)
    start_index = min(range(len(stroke.points)), key=lambda i: (stroke.points[i].distance_to(current), i))
    points = stroke.points[start_index:] + stroke.points[:start_index]
    return _copy_stroke(stroke, points=points)


def _order_strokes(strokes: list[Stroke], settings: StrokeOptimizationSettings) -> list[Stroke]:
    """Greedy nearest-neighbour order, preserving the first stroke as an anchor.

    The first stroke stays in its original orientation because the executor's initial
    screen cursor position is not known. Each subsequent open stroke may be reversed;
    each subsequent closed stroke may start at its vertex nearest to the current point.
    """
    if len(strokes) < 2:
        return [_copy_stroke(stroke) for stroke in strokes]

    ordered = [_copy_stroke(strokes[0])]
    remaining = list(enumerate(strokes[1:], start=1))
    current = ordered[0].points[0] if ordered[0].closed else ordered[0].points[-1]

    while remaining:
        candidates: list[tuple[float, int, Stroke]] = []
        for original_index, stroke in remaining:
            candidate = _copy_stroke(stroke)
            if candidate.closed and settings.rotate_closed_strokes:
                candidate = _rotate_closed_stroke(candidate, current)
            elif not candidate.closed and settings.reverse_open_strokes:
                candidate = _oriented_open_stroke(candidate, current, True)
            distance = current.distance_to(candidate.points[0])
            candidates.append((distance, original_index, candidate))

        _distance, selected_index, selected_stroke = min(candidates, key=lambda item: (item[0], item[1]))
        ordered.append(selected_stroke)
        remaining = [(idx, stroke) for idx, stroke in remaining if idx != selected_index]
        current = selected_stroke.points[0] if selected_stroke.closed else selected_stroke.points[-1]

    return ordered


def _oriented_options(stroke: Stroke) -> list[Stroke]:
    if stroke.closed:
        return [_copy_stroke(stroke)]
    forward = _copy_stroke(stroke)
    backward = _copy_stroke(stroke, points=list(reversed(stroke.points)))
    return [forward, backward]


def _merge_candidate(first: Stroke, second: Stroke, settings: StrokeOptimizationSettings):
    """Return a valid orientation of two open paths to join, or None.

    A short connector may be drawn between endpoints, so this operation is opt-in.
    Both incoming path directions must roughly align with the connector.
    """
    if first.closed or second.closed or len(first.points) < 2 or len(second.points) < 2:
        return None

    best = None
    for a in _oriented_options(first):
        for b in _oriented_options(second):
            endpoint_a = a.points[-1]
            endpoint_b = b.points[0]
            gap = endpoint_a.distance_to(endpoint_b)
            if gap > settings.max_merge_gap_px:
                continue

            incoming = _normalized_vector(a.points[-2], endpoint_a)
            outgoing = _normalized_vector(endpoint_b, b.points[1])
            if incoming is None or outgoing is None:
                continue

            if gap <= 1e-6:
                angle = _angle_between_vectors(incoming, outgoing)
                if angle > settings.max_join_angle_deg:
                    continue
                angle_score = angle
            else:
                connector = _normalized_vector(endpoint_a, endpoint_b)
                if connector is None:
                    continue
                first_angle = _angle_between_vectors(incoming, connector)
                second_angle = _angle_between_vectors(connector, outgoing)
                if first_angle > settings.max_join_angle_deg or second_angle > settings.max_join_angle_deg:
                    continue
                angle_score = first_angle + second_angle

            score = (gap, angle_score)
            if best is None or score < best[0]:
                best = (score, a, b)
    return best


def _merge_open_strokes(strokes: list[Stroke], settings: StrokeOptimizationSettings) -> tuple[list[Stroke], int]:
    if not settings.merge_open_strokes or len(strokes) < 2:
        return [_copy_stroke(stroke) for stroke in strokes], 0

    working = [_copy_stroke(stroke) for stroke in strokes]
    merged_pairs = 0
    while True:
        best = None
        for i in range(len(working)):
            if working[i].closed:
                continue
            for j in range(i + 1, len(working)):
                if working[j].closed:
                    continue
                candidate = _merge_candidate(working[i], working[j], settings)
                if candidate is None:
                    continue
                score, first, second = candidate
                record = (score, i, j, first, second)
                if best is None or (record[0], record[1], record[2]) < (best[0], best[1], best[2]):
                    best = record

        if best is None:
            break
        _score, i, j, first, second = best
        points = list(first.points)
        if points[-1].distance_to(second.points[0]) <= 1e-6:
            points.extend(second.points[1:])
        else:
            # The connector is deliberate and is allowed only under configured limits.
            points.extend(second.points)
        old_merge_count = int(first.metadata.get("merged_path_count", "1")) + int(
            second.metadata.get("merged_path_count", "1")
        )
        combined = Stroke(
            name=f"Merged stroke {merged_pairs + 1}",
            points=points,
            closed=False,
            metadata={
                "merged_path_count": str(old_merge_count),
                "merged_from": f"{first.metadata.get('merged_from', first.name)} | {second.metadata.get('merged_from', second.name)}",
                "connector_gap_px": f"{first.points[-1].distance_to(second.points[0]):.3f}",
            },
        )
        # Preserve first item's approximate place and remove second item.
        working[i] = combined
        del working[j]
        merged_pairs += 1

    return working, merged_pairs


def optimize_plan(
    plan: DrawingPlan,
    settings: StrokeOptimizationSettings | None = None,
) -> OptimizationResult:
    """Create an optimized copy of a DrawingPlan without mutating the input."""
    settings = settings or StrokeOptimizationSettings()
    plan.validate_bounds()
    original_metrics = measure_plan(plan)

    simplified_strokes = [_simplify_stroke(stroke, settings.simplify_tolerance_px) for stroke in plan.strokes]
    points_after_simplification = sum(len(stroke.points) for stroke in simplified_strokes)
    points_removed = max(0, sum(len(stroke.points) for stroke in plan.strokes) - points_after_simplification)

    threshold = settings.minimum_stroke_length_px
    short_strokes_detected = sum(1 for stroke in simplified_strokes if threshold > 0 and stroke.length_px < threshold)
    if settings.remove_short_strokes and threshold > 0:
        filtered = [stroke for stroke in simplified_strokes if stroke.length_px >= threshold]
        if not filtered:
            raise ValueError(
                "Фильтр коротких штрихов удалит весь план. Уменьшите минимальную длину или отключите удаление."
            )
        short_strokes_removed = len(simplified_strokes) - len(filtered)
        simplified_strokes = filtered
    else:
        short_strokes_removed = 0

    merged_strokes, merged_pairs = _merge_open_strokes(simplified_strokes, settings)
    if settings.reorder_strokes:
        optimized_strokes = _order_strokes(merged_strokes, settings)
    else:
        optimized_strokes = [_copy_stroke(stroke) for stroke in merged_strokes]

    optimized_plan = DrawingPlan(
        width=plan.width,
        height=plan.height,
        strokes=optimized_strokes,
        name=f"{plan.name} (optimized)",
    )
    optimized_plan.validate_bounds()
    optimized_metrics = measure_plan(optimized_plan)

    return OptimizationResult(
        original_plan=plan,
        optimized_plan=optimized_plan,
        original_metrics=original_metrics,
        optimized_metrics=optimized_metrics,
        short_strokes_detected=short_strokes_detected,
        short_strokes_removed=short_strokes_removed,
        points_removed_by_simplification=points_removed,
        merged_stroke_pairs=merged_pairs,
        settings=settings,
    )


def render_plan_preview(plan: DrawingPlan, max_dimension: int = 1600) -> "Image.Image":
    """Render a white-background preview, capped in size to avoid huge images."""
    from PIL import Image, ImageDraw

    scale = min(1.0, max_dimension / max(plan.width, plan.height))
    out_width = max(1, round(plan.width * scale))
    out_height = max(1, round(plan.height * scale))
    scale_x = out_width / plan.width
    scale_y = out_height / plan.height
    image = Image.new("RGB", (out_width, out_height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    line_color = (208, 37, 125)
    start_color = (0, 160, 85)
    line_width = max(1, round(scale * 1.2))
    marker_radius = max(1, round(scale * 2.5))

    for stroke in plan.strokes:
        points = [(round(p.x * scale_x), round(p.y * scale_y)) for p in stroke.points]
        if len(points) < 2:
            continue
        if stroke.closed:
            points.append(points[0])
        draw.line(points, fill=line_color, width=line_width, joint="curve")
        x, y = points[0]
        draw.ellipse((x - marker_radius, y - marker_radius, x + marker_radius, y + marker_radius), fill=start_color)
    return image

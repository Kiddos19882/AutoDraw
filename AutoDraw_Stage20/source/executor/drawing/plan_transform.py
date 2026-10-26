from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from models import DrawingPlan, Point, Stroke


@dataclass(frozen=True, slots=True)
class PlanFitInfo:
    source_width: int
    source_height: int
    target_width: int
    target_height: int
    scale_x: float
    scale_y: float
    offset_x: float
    offset_y: float
    preserve_aspect_ratio: bool

    @property
    def is_identity(self) -> bool:
        return (
            self.source_width == self.target_width
            and self.source_height == self.target_height
            and abs(self.scale_x - 1.0) < 1e-9
            and abs(self.scale_y - 1.0) < 1e-9
            and abs(self.offset_x) < 1e-9
            and abs(self.offset_y) < 1e-9
        )

    def to_dict(self) -> dict:
        return {
            "source_size": {"width": self.source_width, "height": self.source_height},
            "target_size": {"width": self.target_width, "height": self.target_height},
            "scale_x": round(self.scale_x, 6),
            "scale_y": round(self.scale_y, 6),
            "offset_x": round(self.offset_x, 3),
            "offset_y": round(self.offset_y, 3),
            "preserve_aspect_ratio": self.preserve_aspect_ratio,
            "identity_transform": self.is_identity,
        }


def fit_plan_to_size(
    plan: DrawingPlan,
    target_width: int,
    target_height: int,
    *,
    preserve_aspect_ratio: bool = True,
) -> tuple[DrawingPlan, PlanFitInfo]:
    """Return a new plan mapped to target dimensions; the input plan is not modified.

    When preserving aspect ratio, the drawing is uniformly scaled to fit and centred in
    the target area. Empty margins are left on one axis when aspect ratios differ.
    When preserve_aspect_ratio=False, the drawing is scaled independently on both axes.
    """
    if target_width <= 0 or target_height <= 0:
        raise ValueError("Размеры целевой области должны быть положительными.")

    source_width = plan.width
    source_height = plan.height
    if preserve_aspect_ratio:
        scale = min(target_width / source_width, target_height / source_height)
        scale_x = scale_y = scale
        offset_x = (target_width - source_width * scale) / 2.0
        offset_y = (target_height - source_height * scale) / 2.0
    else:
        scale_x = target_width / source_width
        scale_y = target_height / source_height
        offset_x = offset_y = 0.0

    numeric_values = (scale_x, scale_y, offset_x, offset_y)
    if not all(isfinite(value) for value in numeric_values):
        raise ValueError("Не удалось рассчитать преобразование DrawingPlan.")

    transformed_strokes: list[Stroke] = []
    for stroke in plan.strokes:
        transformed_points = []
        for point in stroke.points:
            # Clamp tiny floating-point overshoots to valid canvas bounds.
            x = min(float(target_width), max(0.0, point.x * scale_x + offset_x))
            y = min(float(target_height), max(0.0, point.y * scale_y + offset_y))
            transformed_points.append(Point(x, y))
        transformed_strokes.append(
            Stroke(
                name=stroke.name,
                points=transformed_points,
                closed=stroke.closed,
                metadata=dict(stroke.metadata),
            )
        )

    transformed = DrawingPlan(
        width=target_width,
        height=target_height,
        strokes=transformed_strokes,
        name=f"{plan.name} (подгонка {target_width}x{target_height})",
    )
    info = PlanFitInfo(
        source_width=source_width,
        source_height=source_height,
        target_width=target_width,
        target_height=target_height,
        scale_x=scale_x,
        scale_y=scale_y,
        offset_x=offset_x,
        offset_y=offset_y,
        preserve_aspect_ratio=preserve_aspect_ratio,
    )
    return transformed, info

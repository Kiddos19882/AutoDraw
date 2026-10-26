from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import ceil, fsum
from pathlib import Path
import json

from .point import Point
from .stroke import Stroke


@dataclass(slots=True)
class DrawingPlan:
    """План рисования в координатах локального холста."""

    width: int
    height: int
    strokes: list[Stroke]
    name: str = "Test drawing plan"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Размеры плана должны быть положительными.")
        if not self.strokes:
            raise ValueError("План должен содержать хотя бы один штрих.")
        self.validate_bounds()

    def validate_bounds(self) -> None:
        for stroke in self.strokes:
            for index, point in enumerate(stroke.points):
                if not (0 <= point.x <= self.width and 0 <= point.y <= self.height):
                    raise ValueError(
                        f"Точка {index + 1} штриха '{stroke.name}' выходит за границы холста: "
                        f"({point.x:.1f}, {point.y:.1f}), размер {self.width} × {self.height}."
                    )

    @property
    def stroke_count(self) -> int:
        return len(self.strokes)

    @property
    def total_drawing_length_px(self) -> float:
        return fsum(stroke.length_px for stroke in self.strokes)

    @property
    def pen_up_distance_px(self) -> float:
        """Путь между штрихами без рисования, при порядке в плане."""
        if len(self.strokes) < 2:
            return 0.0
        distances: list[float] = []
        for previous, current in zip(self.strokes, self.strokes[1:]):
            previous_end = previous.points[0] if previous.closed else previous.points[-1]
            distances.append(previous_end.distance_to(current.points[0]))
        return fsum(distances)

    def estimated_move_calls(self, point_step_px: float = 2.0) -> int:
        if point_step_px <= 0:
            raise ValueError("Шаг точек должен быть больше нуля.")
        calls = 0
        for stroke in self.strokes:
            for start, end in stroke.iter_segments():
                calls += max(1, ceil(start.distance_to(end) / point_step_px))
        return calls

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "created_at": self.created_at,
            "coordinate_system": "local_canvas_pixels",
            "canvas": {"width": self.width, "height": self.height},
            "summary": {
                "stroke_count": self.stroke_count,
                "drawing_length_px": round(self.total_drawing_length_px, 2),
                "pen_up_distance_px": round(self.pen_up_distance_px, 2),
            },
            "strokes": [stroke.to_dict() for stroke in self.strokes],
        }

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def from_dict(cls, data: dict) -> "DrawingPlan":
        canvas = data["canvas"]
        return cls(
            width=int(canvas["width"]),
            height=int(canvas["height"]),
            name=str(data.get("name", "Loaded drawing plan")),
            created_at=str(data.get("created_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))),
            schema_version=int(data.get("schema_version", 1)),
            strokes=[Stroke.from_dict(stroke) for stroke in data["strokes"]],
        )

    @classmethod
    def load(cls, path: str | Path) -> "DrawingPlan":
        source = Path(path)
        return cls.from_dict(json.loads(source.read_text(encoding="utf-8")))

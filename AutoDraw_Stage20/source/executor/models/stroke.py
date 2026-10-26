from __future__ import annotations

from dataclasses import dataclass, field
from math import fsum
from typing import Iterator

from .point import Point


@dataclass(slots=True)
class Stroke:
    """Один непрерывный штрих; closed=True замыкает последнюю точку на первую."""

    name: str
    points: list[Point]
    closed: bool = False
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("У штриха должно быть имя.")
        if len(self.points) < 2:
            raise ValueError(f"Штрих '{self.name}' должен иметь не менее двух точек.")
        if self.closed and len(self.points) < 3:
            raise ValueError(f"Замкнутый контур '{self.name}' должен иметь не менее трёх точек.")
        if not all(isinstance(point, Point) for point in self.points):
            raise TypeError("Все элементы points должны быть объектами Point.")

    def iter_segments(self) -> Iterator[tuple[Point, Point]]:
        for index in range(len(self.points) - 1):
            yield self.points[index], self.points[index + 1]
        if self.closed:
            yield self.points[-1], self.points[0]

    @property
    def length_px(self) -> float:
        return fsum(start.distance_to(end) for start, end in self.iter_segments())

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "closed": self.closed,
            "points": [point.to_dict() for point in self.points],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Stroke":
        return cls(
            name=str(data["name"]),
            closed=bool(data.get("closed", False)),
            points=[Point.from_dict(point) for point in data["points"]],
            metadata={str(k): str(v) for k, v in data.get("metadata", {}).items()},
        )

from __future__ import annotations

from dataclasses import dataclass
from math import hypot, isfinite


@dataclass(frozen=True, slots=True)
class Point:
    """Точка в локальных координатах холста, а не экрана."""

    x: float
    y: float

    def __post_init__(self) -> None:
        if not isfinite(self.x) or not isfinite(self.y):
            raise ValueError("Координаты точки должны быть конечными числами.")

    def distance_to(self, other: "Point") -> float:
        return hypot(other.x - self.x, other.y - self.y)

    def to_dict(self) -> dict[str, float]:
        return {"x": round(self.x, 3), "y": round(self.y, 3)}

    @classmethod
    def from_dict(cls, data: dict) -> "Point":
        return cls(x=float(data["x"]), y=float(data["y"]))

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Literal

import cv2
import numpy as np
from PIL import Image, ImageDraw

from models import DrawingPlan, Point, Stroke

RetrievalMode = Literal["external", "all"]
ForegroundMode = Literal["dark", "light"]


@dataclass(frozen=True, slots=True)
class ContourSettings:
    """Параметры извлечения контуров из бинарной маски.

    min_contour_length_px=0 отключает фильтр коротких контуров.
    epsilon_percent задаёт допуск approxPolyDP как процент периметра.
    """

    min_contour_length_px: float = 0.0
    epsilon_percent: float = 0.1
    retrieval_mode: RetrievalMode = "external"
    foreground_mode: ForegroundMode = "dark"
    threshold: int = 127

    def __post_init__(self) -> None:
        if not isfinite(self.min_contour_length_px) or self.min_contour_length_px < 0:
            raise ValueError("Минимальная длина контура должна быть конечным числом >= 0.")
        if not isfinite(self.epsilon_percent) or not 0 <= self.epsilon_percent <= 10:
            raise ValueError("Допуск упрощения должен быть в диапазоне 0–10%.")
        if self.retrieval_mode not in ("external", "all"):
            raise ValueError("Неизвестный режим извлечения контуров.")
        if self.foreground_mode not in ("dark", "light"):
            raise ValueError("Неизвестный тип переднего плана.")
        if not 0 <= self.threshold <= 255:
            raise ValueError("Порог маски должен быть в диапазоне 0–255.")

    def to_dict(self) -> dict:
        return {
            "min_contour_length_px": self.min_contour_length_px,
            "epsilon_percent": self.epsilon_percent,
            "retrieval_mode": self.retrieval_mode,
            "foreground_mode": self.foreground_mode,
            "threshold": self.threshold,
        }


@dataclass(slots=True)
class ContourExtractionResult:
    """Результат анализа маски. plan будет None, если подходящих контуров нет."""

    plan: DrawingPlan | None
    contours_found: int
    contours_kept: int
    skipped_by_length: int
    skipped_invalid: int
    source_point_count: int
    planned_point_count: int
    source_mask: Image.Image
    foreground_mask: Image.Image
    settings: ContourSettings


def _as_grayscale(mask: Image.Image | np.ndarray) -> Image.Image:
    if isinstance(mask, Image.Image):
        gray = mask.convert("L")
    else:
        array = np.asarray(mask)
        if array.ndim == 3:
            if array.shape[2] == 4:
                array = cv2.cvtColor(array, cv2.COLOR_BGRA2GRAY)
            elif array.shape[2] == 3:
                array = cv2.cvtColor(array, cv2.COLOR_BGR2GRAY)
            else:
                raise ValueError("Массив маски должен иметь 1, 3 или 4 канала.")
        if array.ndim != 2:
            raise ValueError("Маска должна быть двумерным изображением в оттенках серого.")
        if array.size == 0:
            raise ValueError("Маска пустая.")
        if array.dtype != np.uint8:
            if np.issubdtype(array.dtype, np.floating):
                array = np.nan_to_num(array, nan=0.0, posinf=255.0, neginf=0.0)
            array = np.clip(array, 0, 255).astype(np.uint8)
        gray = Image.fromarray(array, mode="L")
    if gray.width <= 0 or gray.height <= 0:
        raise ValueError("Маска имеет нулевой размер.")
    if gray.width * gray.height > 40_000_000:
        raise ValueError("Маска слишком велика: более 40 млн пикселей.")
    return gray


def _clean_contour_points(contour: np.ndarray) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    for raw in contour.reshape(-1, 2):
        point = (int(raw[0]), int(raw[1]))
        if not points or point != points[-1]:
            points.append(point)
    # OpenCV иногда явно повторяет первую точку в конце. Stroke.closed замыкает путь сам.
    if len(points) > 1 and points[0] == points[-1]:
        points.pop()
    return points


def extract_contours(
    mask: Image.Image | np.ndarray,
    settings: ContourSettings | None = None,
    plan_name: str = "Contour drawing plan",
) -> ContourExtractionResult:
    """Превращает бинарную маску в DrawingPlan.

    Важное допущение: контуры строятся вокруг областей переднего плана. Если маска
    содержит толстые чёрные линии, план обводит их границы, а не автоматически
    восстанавливает центральную линию исходного штриха.
    """
    settings = settings or ContourSettings()
    grayscale = _as_grayscale(mask)
    mask_array = np.asarray(grayscale, dtype=np.uint8)

    threshold_type = cv2.THRESH_BINARY_INV if settings.foreground_mode == "dark" else cv2.THRESH_BINARY
    _, foreground = cv2.threshold(mask_array, settings.threshold, 255, threshold_type)

    retrieval = cv2.RETR_EXTERNAL if settings.retrieval_mode == "external" else cv2.RETR_LIST
    contours, _hierarchy = cv2.findContours(foreground.copy(), retrieval, cv2.CHAIN_APPROX_SIMPLE)

    candidates: list[dict] = []
    skipped_by_length = 0
    skipped_invalid = 0
    source_point_count = 0

    for contour in contours:
        perimeter = float(cv2.arcLength(contour, True))
        source_point_count += int(len(contour))
        if settings.min_contour_length_px > 0 and perimeter < settings.min_contour_length_px:
            skipped_by_length += 1
            continue

        epsilon = perimeter * settings.epsilon_percent / 100.0
        approximated = cv2.approxPolyDP(contour, epsilon, True) if epsilon > 0 else contour
        points_xy = _clean_contour_points(approximated)

        if len(set(points_xy)) < 2:
            skipped_invalid += 1
            continue

        area = abs(float(cv2.contourArea(contour)))
        # Degenerate 1px-wide components may have zero area. Represent them as open
        # paths instead of creating a closed loop from only two points.
        closed = len(points_xy) >= 3 and area > 0.0
        if closed and len(points_xy) < 3:
            skipped_invalid += 1
            continue

        x, y, width, height = cv2.boundingRect(contour)
        candidates.append({
            "points": points_xy,
            "perimeter": perimeter,
            "area": area,
            "bbox": (int(y), int(x), int(height), int(width)),
            "source_count": int(len(contour)),
            "approx_count": len(points_xy),
            "closed": closed,
        })

    # Stable reading order makes previews and JSON deterministic across runs.
    candidates.sort(key=lambda item: (item["bbox"][0], item["bbox"][1], -item["area"], item["perimeter"]))

    strokes: list[Stroke] = []
    for index, item in enumerate(candidates, start=1):
        points = [Point(float(x), float(y)) for x, y in item["points"]]
        strokes.append(Stroke(
            name=f"Contour {index:03d}",
            points=points,
            closed=bool(item["closed"]),
            metadata={
                "source_contour_index": str(index),
                "source_point_count": str(item["source_count"]),
                "planned_point_count": str(item["approx_count"]),
                "perimeter_px": f"{item['perimeter']:.3f}",
                "area_px2": f"{item['area']:.3f}",
                "bounds_xywh": ",".join(map(str, item["bbox"][1:])),
            },
        ))

    plan = None
    if strokes:
        plan = DrawingPlan(
            width=grayscale.width,
            height=grayscale.height,
            strokes=strokes,
            name=plan_name,
        )
        plan.validate_bounds()

    return ContourExtractionResult(
        plan=plan,
        contours_found=len(contours),
        contours_kept=len(strokes),
        skipped_by_length=skipped_by_length,
        skipped_invalid=skipped_invalid,
        source_point_count=source_point_count,
        planned_point_count=sum(len(stroke.points) for stroke in strokes),
        source_mask=grayscale,
        foreground_mask=Image.fromarray(foreground, mode="L"),
        settings=settings,
    )


def render_contour_preview(mask: Image.Image, plan: DrawingPlan | None) -> Image.Image:
    """Создаёт PNG-предпросмотр: исходная маска с цветными траекториями поверх."""
    base = _as_grayscale(mask).convert("RGB")
    if plan is None:
        return base
    if base.size != (plan.width, plan.height):
        raise ValueError("Размер маски не совпадает с размерами DrawingPlan.")

    draw = ImageDraw.Draw(base)
    stroke_color = (238, 45, 145)  # яркий цвет, различимый и на белом, и на чёрном
    start_color = (0, 185, 90)
    for stroke in plan.strokes:
        points = [(round(point.x), round(point.y)) for point in stroke.points]
        if len(points) < 2:
            continue
        line_points = points + ([points[0]] if stroke.closed else [])
        draw.line(line_points, fill=stroke_color, width=1, joint="curve")
        x, y = points[0]
        draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=start_color)
    return base

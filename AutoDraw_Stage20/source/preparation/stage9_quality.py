from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageOps


@dataclass(frozen=True)
class QualityReport:
    width: int
    height: int
    source_foreground_pixels: int
    rendered_foreground_pixels: int
    matched_pixels: int
    missing_pixels: int
    extra_pixels: int
    pixel_accuracy_percent: float
    precision_percent: float
    recall_percent: float
    f1_percent: float
    dimensions_match: bool
    stroke_count: int
    point_count: int
    out_of_bounds_points: int
    empty_strokes: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_mask(path: str | Path) -> Image.Image:
    try:
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert('L')
    except (OSError, ValueError) as exc:
        raise ValueError(f'Не удалось открыть изображение: {exc}') from exc
    if image.width * image.height > 40_000_000:
        raise ValueError('Изображение превышает лимит 40 млн пикселей.')
    return image


def load_plan(path: str | Path) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f'Не удалось прочитать DrawingPlan JSON: {exc}') from exc
    if not isinstance(data, dict):
        raise ValueError('Корень DrawingPlan JSON должен быть объектом.')
    if not isinstance(data.get('strokes'), list):
        raise ValueError("В JSON не найден массив 'strokes'.")
    return data


def plan_dimensions(plan: dict[str, Any]) -> tuple[int, int]:
    canvas = plan.get('canvas')
    if isinstance(canvas, dict) and 'width' in canvas and 'height' in canvas:
        width, height = int(canvas['width']), int(canvas['height'])
    else:
        width, height = int(plan.get('width', 0)), int(plan.get('height', 0))
    if width < 1 or height < 1:
        raise ValueError('В плане должны быть указаны положительные размеры canvas.width и canvas.height.')
    if width * height > 40_000_000:
        raise ValueError('Холст плана превышает лимит 40 млн пикселей.')
    return width, height


def _point(raw: Any) -> tuple[float, float]:
    try:
        if isinstance(raw, dict):
            x, y = float(raw['x']), float(raw['y'])
        elif isinstance(raw, (list, tuple)) and len(raw) >= 2:
            x, y = float(raw[0]), float(raw[1])
        else:
            raise ValueError
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f'Некорректная точка в плане: {raw!r}') from exc
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError(f'Координаты должны быть конечными числами: {raw!r}')
    return x, y


def make_binary_mask(image: Image.Image, threshold: int = 127, foreground: str = 'dark') -> Image.Image:
    if not 0 <= threshold <= 255:
        raise ValueError('Порог должен находиться в диапазоне 0–255.')
    if foreground not in ('dark', 'light'):
        raise ValueError("foreground должен быть 'dark' или 'light'.")
    gray = image.convert('L')
    if foreground == 'dark':
        return gray.point(lambda p: 255 if p <= threshold else 0, mode='L')
    return gray.point(lambda p: 255 if p >= threshold else 0, mode='L')


def render_plan(plan: dict[str, Any]) -> tuple[Image.Image, int, int, int]:
    width, height = plan_dimensions(plan)
    image = Image.new('L', (width, height), 0)
    draw = ImageDraw.Draw(image)
    point_count = 0
    out_of_bounds = 0
    empty_strokes = 0
    for index, stroke in enumerate(plan['strokes']):
        if not isinstance(stroke, dict) or not isinstance(stroke.get('points'), list):
            raise ValueError(f'Штрих №{index + 1} должен содержать массив points.')
        points = [_point(p) for p in stroke['points']]
        point_count += len(points)
        if not points:
            empty_strokes += 1
            continue
        for x, y in points:
            if x < 0 or y < 0 or x > width - 1 or y > height - 1:
                out_of_bounds += 1
        integer_points = [(int(round(x)), int(round(y))) for x, y in points]
        if len(integer_points) == 1:
            x, y = integer_points[0]
            draw.point((x, y), fill=255)
        else:
            draw.line(integer_points, fill=255, width=1)
        if stroke.get('closed') and len(integer_points) > 2:
            draw.line([integer_points[-1], integer_points[0]], fill=255, width=1)
    return image, point_count, out_of_bounds, empty_strokes


def analyze_quality(mask: Image.Image, plan: dict[str, Any], threshold: int = 127,
                    foreground: str = 'dark') -> tuple[QualityReport, Image.Image, Image.Image, Image.Image]:
    source = make_binary_mask(mask, threshold, foreground)
    rendered, point_count, out_of_bounds, empty_strokes = render_plan(plan)
    dimensions_match = source.size == rendered.size
    # A direct pixel comparison is only valid when both images use the same coordinate grid.
    if not dimensions_match:
        raise ValueError(
            f'Размеры не совпадают: маска {source.width}×{source.height}, '
            f'план {rendered.width}×{rendered.height}. Масштабирование автоматически не выполняется.'
        )
    src = source.load()
    out = rendered.load()
    matched = missing = extra = 0
    source_count = rendered_count = 0
    for y in range(source.height):
        for x in range(source.width):
            a, b = src[x, y] > 0, out[x, y] > 0
            source_count += int(a)
            rendered_count += int(b)
            if a and b:
                matched += 1
            elif a:
                missing += 1
            elif b:
                extra += 1
    total = source.width * source.height
    accuracy = 100.0 * (total - missing - extra) / total if total else 100.0
    precision = 100.0 * matched / rendered_count if rendered_count else (100.0 if source_count == 0 else 0.0)
    recall = 100.0 * matched / source_count if source_count else (100.0 if rendered_count == 0 else 0.0)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    report = QualityReport(source.width, source.height, source_count, rendered_count, matched,
                           missing, extra, accuracy, precision, recall, f1, dimensions_match,
                           len(plan['strokes']), point_count, out_of_bounds, empty_strokes)
    # Difference image: white = missing, black = extra, gray = matched, dark background = neither.
    diff = Image.new('RGB', source.size, (24, 24, 24))
    sp, rp, dp = source.load(), rendered.load(), diff.load()
    for y in range(source.height):
        for x in range(source.width):
            a, b = sp[x, y] > 0, rp[x, y] > 0
            if a and b:
                dp[x, y] = (120, 120, 120)
            elif a:
                dp[x, y] = (255, 255, 255)  # missing
            elif b:
                dp[x, y] = (230, 50, 50)     # extra
    return report, source, rendered, diff


def save_report(path: str | Path, report: QualityReport) -> None:
    Path(path).write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')

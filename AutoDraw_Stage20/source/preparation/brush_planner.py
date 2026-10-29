from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from brush_footprint_geometry import footprint_pixel_bounds


BRUSH_PLAN_SCHEMA_VERSION = 1
BRUSH_PLAN_TYPE = "autodraw_adaptive_brush_plan"
DEFAULT_MIN_BRUSH_VALUE = 1
DEFAULT_MAX_BRUSH_VALUE = 20
MAX_BRUSH_PLAN_STROKES = 500_000


class BrushPlannerError(ValueError):
    """Raised when an adaptive-brush plan cannot be built safely."""


def _canonical_plan_sha256(plan: dict[str, Any]) -> str:
    try:
        payload = json.dumps(
            plan, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise BrushPlannerError("Исходный цветной план не сериализуется в безопасный JSON.") from exc
    return hashlib.sha256(payload).hexdigest()


def _finite_positive(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise BrushPlannerError(f"{field} должен быть положительным числом.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise BrushPlannerError(f"{field} должен быть положительным числом.") from exc
    if not math.isfinite(number) or number <= 0:
        raise BrushPlannerError(f"{field} должен быть конечным числом больше нуля.")
    return number


def _validate_index_map(index_map: Any, width: int, height: int) -> np.ndarray:
    try:
        indexes = np.asarray(index_map)
    except (TypeError, ValueError) as exc:
        raise BrushPlannerError("Не удалось прочитать карту индексов цветов.") from exc
    if indexes.ndim != 2 or indexes.shape != (height, width):
        raise BrushPlannerError(
            f"Размер карты цветов должен совпадать с планом ({width}×{height})."
        )
    if indexes.dtype.kind not in "iu":
        raise BrushPlannerError("Индексы цветов должны быть целыми числами.")
    if indexes.size and int(indexes.min()) < -1:
        raise BrushPlannerError("Индекс прозрачности не может быть меньше -1.")
    return indexes.astype(np.int32, copy=False)


def _line_is_safe(
    indexes: np.ndarray,
    *,
    palette_index: int,
    x_start: float,
    x_end: float,
    y: float,
    brush_value: int,
    scale_x: float,
    scale_y: float,
) -> bool:
    """Check the brush footprint against exact palette indexes, conservatively."""
    height, width = indexes.shape
    bounds = footprint_pixel_bounds(
        x_start, x_end, y, brush_value, scale_x, scale_y, width, height
    )
    if bounds is None:
        return False
    left, right, top, bottom = bounds
    region = indexes[top:bottom + 1, left:right + 1]
    return bool(region.size and np.all(region == palette_index))


def _make_stroke(
    *,
    source_index: int,
    source_stroke: dict[str, Any],
    x_start: float,
    x_end: float,
    y: float,
    brush_value: int | None,
    role: str,
    safe: bool,
    scale_x: float,
    scale_y: float,
) -> dict[str, Any]:
    points = [{"x": float(x_start), "y": float(y)}, {"x": float(x_end), "y": float(y)}]
    suffix = f"{role}_brush{brush_value}" if brush_value is not None else f"{role}_legacy"
    return {
        "name": f"{source_stroke.get('name', f'stroke_{source_index + 1}')}__{suffix}",
        "source_stroke_index": source_index,
        "closed": False,
        "points": points,
        "color": dict(source_stroke["color"]),
        "brush": {
            "value": brush_value,
            "role": role,
            "safe_for_color_map": safe,
            "safe_to_execute": False,
            "width_in_source_px": (
                {"x": round(brush_value * scale_x, 4), "y": round(brush_value * scale_y, 4)}
                if brush_value is not None else None
            ),
        },
        "metadata": dict(source_stroke.get("metadata", {})),
    }


def build_adaptive_brush_plan(
    index_map: Any,
    color_plan: dict[str, Any],
    *,
    brush_scale_x: float = 1.0,
    brush_scale_y: float = 1.0,
    min_brush_value: int = DEFAULT_MIN_BRUSH_VALUE,
    max_brush_value: int = DEFAULT_MAX_BRUSH_VALUE,
    calibration_confirmed: bool = False,
) -> dict[str, Any]:
    """Build safe brush recommendations for an ordered color scanline plan.

    The scale values map one game brush unit to source-image pixels. A long run
    can be split into thin edge segments and a thicker interior segment. If the
    complete brush footprint is not a single exact palette color, the planner
    falls back instead of risking overpainting. Until mapping is calibrated,
    recommendations are not marked ready for automatic execution.
    """
    if not isinstance(color_plan, dict) or color_plan.get("plan_type") != "autodraw_color_scanline_plan":
        raise BrushPlannerError("Ожидался autodraw_color_scanline_plan.")
    if color_plan.get("schema_version") != 1:
        raise BrushPlannerError("Неподдерживаемая версия цветного плана.")
    canvas = color_plan.get("canvas")
    if not isinstance(canvas, dict):
        raise BrushPlannerError("В плане отсутствует размер canvas.")
    try:
        width, height = int(canvas["width"]), int(canvas["height"])
    except (KeyError, TypeError, ValueError) as exc:
        raise BrushPlannerError("Размеры canvas должны быть целыми числами.") from exc
    if width <= 0 or height <= 0 or width != canvas.get("width") or height != canvas.get("height"):
        raise BrushPlannerError("Размеры canvas должны быть положительными целыми числами.")
    if isinstance(min_brush_value, bool) or not isinstance(min_brush_value, int):
        raise BrushPlannerError("Минимальный размер кисти должен быть целым числом.")
    if isinstance(max_brush_value, bool) or not isinstance(max_brush_value, int):
        raise BrushPlannerError("Максимальный размер кисти должен быть целым числом.")
    if not 1 <= min_brush_value <= max_brush_value <= 20:
        raise BrushPlannerError("Диапазон кистей должен находиться внутри 1…20.")
    if not isinstance(calibration_confirmed, bool):
        raise BrushPlannerError("calibration_confirmed должен быть логическим значением.")
    scale_x = _finite_positive(brush_scale_x, "Масштаб кисти по X")
    scale_y = _finite_positive(brush_scale_y, "Масштаб кисти по Y")
    indexes = _validate_index_map(index_map, width, height)

    source_strokes = color_plan.get("strokes")
    if not isinstance(source_strokes, list) or not source_strokes:
        raise BrushPlannerError("В исходном цветном плане нет штрихов.")
    if len(source_strokes) > 250_000:
        raise BrushPlannerError("В исходном плане слишком много штрихов.")

    output_strokes: list[dict[str, Any]] = []
    per_brush: Counter[int] = Counter()
    fallback_source_strokes = 0
    split_source_strokes = 0
    previous_brush: int | None = None
    brush_switch_count = 0

    for source_index, source_stroke in enumerate(source_strokes):
        if not isinstance(source_stroke, dict) or not isinstance(source_stroke.get("color"), dict):
            raise BrushPlannerError(f"Штрих №{source_index + 1} повреждён.")
        points = source_stroke.get("points")
        try:
            if not isinstance(points, list) or len(points) != 2:
                raise ValueError
            x1, y1 = float(points[0]["x"]), float(points[0]["y"])
            x2, y2 = float(points[1]["x"]), float(points[1]["y"])
            color_index = source_stroke["color"]["palette_index"]
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise BrushPlannerError(f"Не удалось прочитать геометрию штриха №{source_index + 1}.") from exc
        if isinstance(color_index, bool) or not isinstance(color_index, int) or color_index < 0:
            raise BrushPlannerError(f"Штрих №{source_index + 1} имеет неверный индекс цвета.")
        if not all(math.isfinite(v) for v in (x1, y1, x2, y2)):
            raise BrushPlannerError(f"Координаты штриха №{source_index + 1} должны быть конечными.")
        if not (math.isclose(y1, y2, abs_tol=1e-7) and 0 <= y1 < height and 0 <= x1 <= x2 < width):
            raise BrushPlannerError(f"Штрих №{source_index + 1} должен быть горизонтальным и находиться внутри canvas.")
        if any(not math.isclose(v, round(v), abs_tol=1e-7) for v in (x1, x2, y1)):
            raise BrushPlannerError(f"Координаты scanline-штриха №{source_index + 1} должны лежать на пиксельной сетке.")
        x1, x2, y = float(round(x1)), float(round(x2)), float(round(y1))
        if int(indexes[int(y), int(x1)]) != color_index or int(indexes[int(y), int(x2)]) != color_index:
            raise BrushPlannerError(f"Концы штриха №{source_index + 1} не совпадают с его цветом в карте.")
        if not bool(np.all(indexes[int(y), int(x1):int(x2) + 1] == color_index)):
            raise BrushPlannerError(f"Штрих №{source_index + 1} пересекает другой цвет или прозрачность.")

        picked_value: int | None = None
        inner_start, inner_end = x1, x2
        for candidate in range(max_brush_value, min_brush_value, -1):
            inset = int(math.ceil(candidate * scale_x / 2.0))
            if x2 - x1 <= 2 * inset:
                continue
            candidate_start = x1 + inset
            candidate_end = x2 - inset
            if not _line_is_safe(
                indexes, palette_index=color_index, x_start=candidate_start, x_end=candidate_end,
                y=y, brush_value=candidate, scale_x=scale_x, scale_y=scale_y,
            ):
                continue
            left_safe = _line_is_safe(
                indexes, palette_index=color_index, x_start=x1, x_end=candidate_start,
                y=y, brush_value=min_brush_value, scale_x=scale_x, scale_y=scale_y,
            )
            right_safe = _line_is_safe(
                indexes, palette_index=color_index, x_start=candidate_end, x_end=x2,
                y=y, brush_value=min_brush_value, scale_x=scale_x, scale_y=scale_y,
            )
            if left_safe and right_safe:
                picked_value, inner_start, inner_end = candidate, candidate_start, candidate_end
                break

        if picked_value is None:
            if _line_is_safe(
                indexes, palette_index=color_index, x_start=x1, x_end=x2,
                y=y, brush_value=min_brush_value, scale_x=scale_x, scale_y=scale_y,
            ):
                created = [_make_stroke(
                    source_index=source_index, source_stroke=source_stroke,
                    x_start=x1, x_end=x2, y=y, brush_value=min_brush_value,
                    role="whole_run", safe=True, scale_x=scale_x, scale_y=scale_y,
                )]
            else:
                fallback_source_strokes += 1
                created = [_make_stroke(
                    source_index=source_index, source_stroke=source_stroke,
                    x_start=x1, x_end=x2, y=y, brush_value=None,
                    role="legacy_fallback", safe=False, scale_x=scale_x, scale_y=scale_y,
                )]
        else:
            split_source_strokes += 1
            created = [
                _make_stroke(
                    source_index=source_index, source_stroke=source_stroke,
                    x_start=x1, x_end=inner_start, y=y, brush_value=min_brush_value,
                    role="leading_edge", safe=True, scale_x=scale_x, scale_y=scale_y,
                ),
                _make_stroke(
                    source_index=source_index, source_stroke=source_stroke,
                    x_start=inner_start, x_end=inner_end, y=y, brush_value=picked_value,
                    role="interior", safe=True, scale_x=scale_x, scale_y=scale_y,
                ),
                _make_stroke(
                    source_index=source_index, source_stroke=source_stroke,
                    x_start=inner_end, x_end=x2, y=y, brush_value=min_brush_value,
                    role="trailing_edge", safe=True, scale_x=scale_x, scale_y=scale_y,
                ),
            ]

        for planned in created:
            if len(output_strokes) >= MAX_BRUSH_PLAN_STROKES:
                raise BrushPlannerError(f"План превысил лимит {MAX_BRUSH_PLAN_STROKES:,} штрихов.")
            chosen = planned["brush"]["value"]
            # Geometry calibration alone does not calibrate the Stage 20 UI controls
            # or connect this recommendation plan to the mouse executor.
            planned["brush"]["safe_to_execute"] = False
            if chosen is not None:
                per_brush[chosen] += 1
                if previous_brush is not None and previous_brush != chosen:
                    brush_switch_count += 1
                previous_brush = chosen
            output_strokes.append(planned)

    return {
        "schema_version": BRUSH_PLAN_SCHEMA_VERSION,
        "plan_type": BRUSH_PLAN_TYPE,
        "source_plan_type": color_plan["plan_type"],
        "source_plan_name": str(color_plan.get("plan_name", "Цветной scanline-план")),
        "source_plan_sha256": _canonical_plan_sha256(color_plan),
        "canvas": {"width": width, "height": height},
        "brush_configuration": {
            "min_value": min_brush_value,
            "max_value": max_brush_value,
            "scale_x_source_px_per_game_unit": scale_x,
            "scale_y_source_px_per_game_unit": scale_y,
            "calibration_confirmed": calibration_confirmed,
            "automatic_execution_allowed": False,
            "execution_blockers": [
                "План кистей ещё не подключён к исполнителю Stage 20.",
                "Координаты и управление ползунком кисти в Stage 20 не откалиброваны.",
            ],
            "safety_rule": "Весь проверяемый след кисти должен попадать на тот же palette_index; границы разбиваются на тонкие края и безопасную внутреннюю часть.",
        },
        "summary": {
            "source_stroke_count": len(source_strokes),
            "planned_stroke_count": len(output_strokes),
            "split_source_stroke_count": split_source_strokes,
            "legacy_fallback_source_stroke_count": fallback_source_strokes,
            "additional_stroke_count": len(output_strokes) - len(source_strokes),
            "recommended_brush_switch_count": brush_switch_count,
            "stroke_count_by_brush": {str(k): per_brush[k] for k in sorted(per_brush)},
            "geometry_safety_confirmed": fallback_source_strokes == 0,
            "geometry_calibration_confirmed": calibration_confirmed,
            "ready_for_automatic_execution": False,
            "execution_blockers": [
                "План кистей ещё не подключён к исполнителю Stage 20.",
                "Координаты и управление ползунком кисти в Stage 20 не откалиброваны.",
            ],
            "note": (
                "Размеры кисти назначены консервативно. Этот этап сохраняет исходное покрытие, "
                "но может разделять длинные штрихи на края и внутреннюю часть. Следующим этапом "
                "будет сокращение числа штрихов через безопасное пропускание рядов."
            ),
        },
        "strokes": output_strokes,
    }


def validate_adaptive_brush_plan(plan: Any) -> dict[str, Any]:
    if not isinstance(plan, dict) or plan.get("plan_type") != BRUSH_PLAN_TYPE:
        raise BrushPlannerError("Это не adaptive-brush-план AutoDraw.")
    if plan.get("schema_version") != BRUSH_PLAN_SCHEMA_VERSION:
        raise BrushPlannerError("Неподдерживаемая версия adaptive-brush-плана.")
    canvas, summary, strokes = plan.get("canvas"), plan.get("summary"), plan.get("strokes")
    if not isinstance(canvas, dict) or not isinstance(summary, dict) or not isinstance(strokes, list):
        raise BrushPlannerError("В adaptive-brush-плане отсутствуют обязательные поля.")
    if len(strokes) != summary.get("planned_stroke_count") or not strokes:
        raise BrushPlannerError("Количество штрихов не совпадает со сводкой.")
    source_hash = plan.get("source_plan_sha256")
    if not isinstance(source_hash, str) or len(source_hash) != 64 or any(c not in "0123456789abcdef" for c in source_hash):
        raise BrushPlannerError("В плане отсутствует корректная SHA-256 исходного цветного плана.")
    if plan.get("brush_configuration", {}).get("automatic_execution_allowed") is not False:
        raise BrushPlannerError("Адаптивный план не может сам разрешать автоматическое исполнение.")
    for index, stroke in enumerate(strokes, start=1):
        if not isinstance(stroke, dict) or not isinstance(stroke.get("brush"), dict):
            raise BrushPlannerError(f"В штрихе №{index} отсутствует информация о кисти.")
        value = stroke["brush"].get("value")
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 20):
            raise BrushPlannerError(f"В штрихе №{index} указан недопустимый размер кисти.")
        if stroke["brush"].get("safe_to_execute") and not stroke["brush"].get("safe_for_color_map"):
            raise BrushPlannerError(f"Небезопасный штрих №{index} отмечен готовым к исполнению.")
    return plan



def save_adaptive_brush_plan(path: str | Path, plan: Any) -> Path:
    """Validate and atomically save an adaptive brush plan."""
    validated = validate_adaptive_brush_plan(plan)
    destination = Path(path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(validated, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="\n", dir=destination.parent,
            prefix=f".{destination.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = handle.name
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except OSError:
        if temporary:
            try:
                os.unlink(temporary)
            except OSError:
                pass
        raise
    return destination


def load_adaptive_brush_plan(path: str | Path) -> dict[str, Any]:
    """Load an adaptive brush plan and reject invalid or executable-looking documents."""
    source = Path(path).expanduser().resolve()
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BrushPlannerError(f"Не удалось загрузить адаптивный план кистей: {exc}") from exc
    return validate_adaptive_brush_plan(raw)

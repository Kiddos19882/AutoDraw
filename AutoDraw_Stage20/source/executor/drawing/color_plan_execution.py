from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable

from models import DrawingPlan, Point, Stroke


class ColorPlanExecutionError(ValueError):
    """A color plan or its browser palette cannot be executed safely."""


def normalize_brush_slider_points(
    min_point: Any,
    max_point: Any,
    *,
    max_y_difference: int = 8,
) -> tuple[int, int, int]:
    """Convert two screen clicks into the slider endpoints and a shared Y coordinate."""
    try:
        x_min, y_min = int(min_point[0]), int(min_point[1])
        x_max, y_max = int(max_point[0]), int(max_point[1])
    except (TypeError, ValueError, IndexError) as exc:
        raise ColorPlanExecutionError(
            "Не удалось прочитать две точки ползунка. Выберите обе точки заново."
        ) from exc

    if min(x_min, y_min, x_max, y_max) < 0:
        raise ColorPlanExecutionError("Координаты точек ползунка не могут быть отрицательными.")
    if x_max <= x_min:
        raise ColorPlanExecutionError(
            "Сначала отметьте позицию значения 1 слева, затем позицию значения 30 справа."
        )
    if x_max - x_min < 29:
        raise ColorPlanExecutionError(
            "Между крайними точками ползунка должно быть не менее 29 px."
        )
    if abs(y_max - y_min) > max_y_difference:
        raise ColorPlanExecutionError(
            "Точки оказались на разных высотах. Щёлкните две позиции на одной горизонтальной дорожке."
        )
    return x_min, x_max, round((y_min + y_max) / 2)


@dataclass(frozen=True, slots=True)
class PaletteTarget:
    palette_index: int
    color_id: str
    name: str
    rgb: tuple[int, int, int]
    hex: str
    screen_x: int
    screen_y: int
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "palette_index": self.palette_index,
            "color_id": self.color_id,
            "name": self.name,
            "rgb": list(self.rgb),
            "hex": self.hex,
            "screen_x": self.screen_x,
            "screen_y": self.screen_y,
            "status": self.status,
        }


def validate_color_plan(plan: Any) -> dict[str, Any]:
    """Use the Stage 19 validator, importing lazily to avoid import-cycle issues."""
    try:
        from color_scanline import validate_color_scanline_plan
        return validate_color_scanline_plan(plan)
    except Exception as exc:
        if isinstance(exc, ColorPlanExecutionError):
            raise
        raise ColorPlanExecutionError(f"Некорректный цветной план: {exc}") from exc


def _canonical_color_plan_sha256(plan: dict[str, Any]) -> str:
    try:
        serialized = json.dumps(
            plan, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ColorPlanExecutionError("Исходный цветной план не сериализуется в безопасный JSON.") from exc
    return hashlib.sha256(serialized).hexdigest()


def adaptive_brush_plan_to_drawing_plan(brush_plan: Any, source_color_plan: Any) -> DrawingPlan:
    """Convert an exported adaptive plan only when bound to its exact source color plan."""
    try:
        from brush_planner import validate_adaptive_brush_plan
        adaptive = validate_adaptive_brush_plan(brush_plan)
    except Exception as exc:
        raise ColorPlanExecutionError(f"Некорректный адаптивный план кистей: {exc}") from exc
    color_plan = validate_color_plan(source_color_plan)
    if adaptive.get("source_plan_sha256") != _canonical_color_plan_sha256(color_plan):
        raise ColorPlanExecutionError(
            "Адаптивный план кистей создан для другого цветного плана. "
            "Загрузите соответствующий исходный план этапа 19 и повторите."
        )
    canvas = adaptive["canvas"]
    source_canvas = color_plan["canvas"]
    if (canvas.get("width"), canvas.get("height")) != (source_canvas.get("width"), source_canvas.get("height")):
        raise ColorPlanExecutionError("Размер адаптивного плана не совпадает с исходным цветным планом.")
    summary = adaptive.get("summary", {})
    if int(summary.get("legacy_fallback_source_stroke_count", 0)) > 0:
        raise ColorPlanExecutionError(
            "Адаптивный план содержит штрихи без подтверждённой безопасности. "
            "Для исполнения используйте обычный цветной план или пересчитайте рекомендации."
        )
    if adaptive.get("brush_configuration", {}).get("automatic_execution_allowed") is not False:
        raise ColorPlanExecutionError("Адаптивный план не прошёл обязательную блокировку автоматического исполнения.")

    width, height = int(canvas["width"]), int(canvas["height"])
    brush_configuration = adaptive.get("brush_configuration", {})
    if brush_configuration.get("calibration_confirmed") is not True:
        raise ColorPlanExecutionError(
            "Stage 19 не подтвердил, что карта цветов покрывает весь игровой холст. "
            "Повторно рассчитайте адаптивный план и подтвердите геометрию 460×240."
        )
    try:
        from board_resource_model import GAME_BOARD_LOGICAL_HEIGHT, GAME_BOARD_LOGICAL_WIDTH
        actual_scale_x = float(brush_configuration["scale_x_source_px_per_game_unit"])
        actual_scale_y = float(brush_configuration["scale_y_source_px_per_game_unit"])
    except (ImportError, KeyError, TypeError, ValueError) as exc:
        raise ColorPlanExecutionError("В адаптивном плане отсутствует рассчитанный масштаб кисти.") from exc
    expected_scale_x = width / GAME_BOARD_LOGICAL_WIDTH
    expected_scale_y = height / GAME_BOARD_LOGICAL_HEIGHT
    if (abs(actual_scale_x - expected_scale_x) > max(0.01, expected_scale_x * 0.03)
            or abs(actual_scale_y - expected_scale_y) > max(0.01, expected_scale_y * 0.03)):
        raise ColorPlanExecutionError(
            "Масштаб кисти адаптивного плана не согласуется с логическим холстом 460×240. "
            f"Ожидалось X≈{expected_scale_x:.4f}, Y≈{expected_scale_y:.4f}; "
            f"в плане X={actual_scale_x:.4f}, Y={actual_scale_y:.4f}. Пересчитайте Stage 19."
        )
    palette = color_plan["palette"]
    source_strokes = color_plan["strokes"]
    strokes: list[Stroke] = []
    previous_source_index = -1
    for index, raw in enumerate(adaptive["strokes"], start=1):
        try:
            source_index = raw["source_stroke_index"]
            color_index = int(raw["color"]["palette_index"])
            brush_data = raw["brush"]
            brush_value = brush_data["value"]
            points = [Point(float(point["x"]), float(point["y"])) for point in raw["points"]]
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise ColorPlanExecutionError(f"Адаптивный штрих №{index} повреждён.") from exc
        if isinstance(source_index, bool) or not isinstance(source_index, int) or not 0 <= source_index < len(source_strokes):
            raise ColorPlanExecutionError(f"Адаптивный штрих №{index} ссылается на неверный исходный штрих.")
        if source_index < previous_source_index:
            raise ColorPlanExecutionError(
                f"Адаптивный штрих №{index} нарушает исходный порядок рисования; порядок штрихов не должен переставляться."
            )
        previous_source_index = source_index
        if isinstance(brush_value, bool) or not isinstance(brush_value, int) or not 1 <= brush_value <= 20:
            raise ColorPlanExecutionError(f"В адаптивном штрихе №{index} отсутствует допустимый размер кисти.")
        if not isinstance(brush_data, dict) or brush_data.get("safe_for_color_map") is not True:
            raise ColorPlanExecutionError(f"Безопасность адаптивного штриха №{index} не подтверждена.")
        try:
            source_color_index = int(source_strokes[source_index]["color"]["palette_index"])
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise ColorPlanExecutionError(f"Не удалось проверить цвет исходного штриха №{source_index + 1}.") from exc
        if color_index != source_color_index or not 0 <= color_index < len(palette):
            raise ColorPlanExecutionError(f"Цвет адаптивного штриха №{index} не совпадает с исходным планом.")
        if len(points) != 2 or any(
            not (0 <= point.x <= width and 0 <= point.y < height) for point in points
        ):
            raise ColorPlanExecutionError(f"Координаты адаптивного штриха №{index} выходят за пределы холста.")
        if points[1].x < points[0].x or not abs(points[0].y - points[1].y) <= 1e-7:
            raise ColorPlanExecutionError(
                f"Адаптивный штрих №{index} должен сохранять горизонтальное направление scanline."
            )
        try:
            source_points = source_strokes[source_index]["points"]
            source_x1 = float(source_points[0]["x"])
            source_y1 = float(source_points[0]["y"])
            source_x2 = float(source_points[1]["x"])
            source_y2 = float(source_points[1]["y"])
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise ColorPlanExecutionError(
                f"Нельзя проверить геометрию исходного штриха №{source_index + 1}."
            ) from exc
        if (not all(map(math.isfinite, (source_x1, source_y1, source_x2, source_y2)))
                or abs(source_y1 - source_y2) > 1e-7
                or abs(points[0].y - source_y1) > 1e-7
                or abs(points[1].y - source_y1) > 1e-7
                or source_x2 < source_x1
                or points[0].x < source_x1 - 1e-7
                or points[1].x > source_x2 + 1e-7):
            raise ColorPlanExecutionError(
                f"Адаптивный штрих №{index} выходит за границы или строку своего исходного участка."
            )
        if points[0].distance_to(points[1]) == 0:
            if points[0].x >= width:
                raise ColorPlanExecutionError(f"Одиночный адаптивный штрих №{index} расположен за правой границей.")
            points[1] = Point(points[0].x + 1.0, points[0].y)

        palette_color = palette[color_index]
        metadata = {
            "palette_index": str(color_index),
            "color_id": str(palette_color["id"]),
            "color_name": str(palette_color["name"]),
            "color_hex": str(palette_color["hex"]),
            "color_rgb": ",".join(str(channel) for channel in palette_color["rgb"]),
            "color_scanline_order": str(index),
            "adaptive_brush_plan": "true",
            "brush_value": str(brush_value),
            "brush_role": str(brush_data.get("role", "unspecified")),
            "brush_plan_source_stroke_index": str(source_index),
            "line_extension_px_override": "0",
        }
        strokes.append(Stroke(
            name=str(raw.get("name") or f"adaptive-color-stroke-{index}"),
            points=points,
            closed=False,
            metadata=metadata,
        ))
    converted = DrawingPlan(
        width=width,
        height=height,
        strokes=strokes,
        name=f"{str(adaptive.get('source_plan_name') or 'Цветной план')} (адаптивные кисти)",
        created_at=str(color_plan.get("created_at") or ""),
        schema_version=1,
    )
    converted.validate_bounds()
    return converted


@dataclass(frozen=True, slots=True)
class BrushSliderCalibration:
    """User-calibrated screen mapping for the extended painter brush slider."""

    x_at_min: int
    x_at_max: int
    y: int
    initial_value: int
    screen_width: int
    screen_height: int
    confirmed: bool
    min_value: int = 1
    max_value: int = 30

    @classmethod
    def from_dict(cls, data: Any) -> "BrushSliderCalibration":
        if not isinstance(data, dict):
            raise ColorPlanExecutionError("Профиль ползунка кисти должен быть JSON-объектом.")
        try:
            return cls(
                x_at_min=int(data["x_at_min"]),
                x_at_max=int(data["x_at_max"]),
                y=int(data["y"]),
                initial_value=int(data["initial_value"]),
                screen_width=int(data["screen_width"]),
                screen_height=int(data["screen_height"]),
                confirmed=data.get("confirmed") is True,
                min_value=int(data.get("min_value", 1)),
                max_value=int(data.get("max_value", 30)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ColorPlanExecutionError("В профиле ползунка кисти не хватает корректных координат.") from exc

    def coordinate_for_value(self, value: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or not self.min_value <= value <= self.max_value:
            raise ColorPlanExecutionError(
                f"Размер кисти {value!r} вне диапазона {self.min_value}–{self.max_value}."
            )
        fraction = (value - self.min_value) / (self.max_value - self.min_value)
        return round(self.x_at_min + fraction * (self.x_at_max - self.x_at_min))

    def validate(self, current_screen_size: Any, target_area: dict[str, int] | None = None) -> None:
        if not self.confirmed:
            raise ColorPlanExecutionError(
                "Калибровка ползунка кисти не подтверждена. Укажите координаты крайних значений "
                "1 и 30, начальный размер и подтвердите калибровку на текущем разрешении."
            )
        if (self.min_value, self.max_value) != (1, 30):
            raise ColorPlanExecutionError("Поддерживается расширенный ползунок кисти со значениями 1–30.")
        try:
            if hasattr(current_screen_size, "width"):
                screen_width, screen_height = int(current_screen_size.width), int(current_screen_size.height)
            else:
                screen_width, screen_height = int(current_screen_size[0]), int(current_screen_size[1])
        except (TypeError, ValueError, IndexError, AttributeError) as exc:
            raise ColorPlanExecutionError("Не удалось определить размер экрана для ползунка кисти.") from exc
        if (screen_width, screen_height) != (self.screen_width, self.screen_height):
            raise ColorPlanExecutionError(
                f"Разрешение экрана изменилось после калибровки ползунка: "
                f"{self.screen_width}×{self.screen_height}, сейчас {screen_width}×{screen_height}. "
                "Подтвердите калибровку заново."
            )
        if not (0 <= self.x_at_min < screen_width and 0 <= self.x_at_max < screen_width):
            raise ColorPlanExecutionError("Крайние X-координаты ползунка выходят за пределы экрана.")
        if abs(self.x_at_max - self.x_at_min) < self.max_value - self.min_value:
            raise ColorPlanExecutionError(
                "Длина ползунка слишком мала для раздельного выбора всех значений 1–30."
            )
        if not 0 <= self.y < screen_height:
            raise ColorPlanExecutionError("Y-координата ползунка выходит за пределы экрана.")
        if not self.min_value <= self.initial_value <= self.max_value:
            raise ColorPlanExecutionError("Начальный размер кисти должен быть в диапазоне 1–30.")
        if target_area:
            # Check every integer value, not only endpoints: a track crossing the
            # selected canvas must never cause a brush-selection drag over artwork.
            for value in range(self.min_value, self.max_value + 1):
                x = self.coordinate_for_value(value)
                if (target_area["x"] <= x < target_area["x"] + target_area["width"]
                        and target_area["y"] <= self.y < target_area["y"] + target_area["height"]):
                    raise ColorPlanExecutionError(
                        "Ползунок кисти попадает внутрь выделенной области рисования. "
                        "Проверьте область холста и координаты элементов управления, чтобы AutoDraw не кликнул по рисунку."
                    )


def build_brush_visual_test_plan(width: int, height: int) -> DrawingPlan:
    """Create four separated horizontal strokes to visually verify brush-size switching."""
    if isinstance(width, bool) or isinstance(height, bool):
        raise ColorPlanExecutionError("Размер тестовой области должен быть целым числом.")
    try:
        width, height = int(width), int(height)
    except (TypeError, ValueError) as exc:
        raise ColorPlanExecutionError("Не удалось прочитать размер тестовой области.") from exc
    if width < 180 or height < 160:
        raise ColorPlanExecutionError(
            "Для визуального теста выберите свободный прямоугольник не менее 180 × 160 px."
        )

    brush_values = (1, 7, 14, 20)
    margin_x = max(16, min(30, width // 10))
    margin_y = max(20, min(26, height // 8))
    available_height = height - margin_y * 2
    strokes: list[Stroke] = []
    for index, brush_value in enumerate(brush_values):
        y = round(margin_y + index * available_height / (len(brush_values) - 1))
        strokes.append(
            Stroke(
                name=f"Проверка кисти {brush_value}",
                points=[Point(margin_x, y), Point(width - margin_x, y)],
                metadata={
                    "brush_value": str(brush_value),
                    "line_extension_px_override": "0",
                    "brush_visual_test": "true",
                },
            )
        )
    return DrawingPlan(
        width=width,
        height=height,
        strokes=strokes,
        name="Визуальный тест изменения размера кисти",
    )


class BrushSliderController:
    """Drag the currently selected slider thumb to the calibrated target value."""

    def __init__(
        self,
        calibration: BrushSliderCalibration,
        target_area: dict[str, int],
        *,
        current_screen_size_provider: Callable[[], Any] | None = None,
    ):
        self.calibration = calibration
        self.target_area = dict(target_area)
        self.current_screen_size_provider = current_screen_size_provider
        self.current_value = calibration.initial_value
        self.selection_count = 0
        self.selection_order: list[int] = []

    def validate(self) -> None:
        screen = (
            self.current_screen_size_provider()
            if self.current_screen_size_provider is not None
            else (self.calibration.screen_width, self.calibration.screen_height)
        )
        self.calibration.validate(screen, self.target_area)

    def before_stroke(self, executor: Any, stroke_index: int, stroke: Stroke) -> str:
        raw_value = stroke.metadata.get("brush_value")
        if raw_value is None:
            raise ColorPlanExecutionError(
                f"Адаптивный штрих №{stroke_index} не содержит размера кисти; обычный план не должен использовать этот контроллер."
            )
        try:
            value = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise ColorPlanExecutionError(f"В штрихе №{stroke_index} указан неверный размер кисти.") from exc
        if not 1 <= value <= 20:
            raise ColorPlanExecutionError(f"Размер кисти {value} не входит в диапазон планировщика 1–20.")
        return self.select_value(executor, value)

    def select_value(self, executor: Any, value: int) -> str:
        """Move the slider without drawing; the visual test also uses this to restore its starting value."""
        if isinstance(value, bool) or not isinstance(value, int):
            raise ColorPlanExecutionError("Размер кисти должен быть целым числом.")
        if not self.calibration.min_value <= value <= self.calibration.max_value:
            raise ColorPlanExecutionError(
                f"Размер кисти {value} вне диапазона {self.calibration.min_value}–{self.calibration.max_value}."
            )
        self.validate()
        if self.current_value == value:
            return f"Кисть {value} уже выбрана."

        import pyautogui

        current_x = self.calibration.coordinate_for_value(self.current_value)
        target_x = self.calibration.coordinate_for_value(value)
        y = self.calibration.y
        executor._check_stop()
        pyautogui.moveTo(current_x, y, duration=0)
        executor.move_calls += 1
        executor._wait_interruptibly(executor.config.before_mouse_down_ms / 1000.0)
        executor._check_stop()
        pyautogui.mouseDown()
        try:
            executor._wait_interruptibly(executor.config.after_mouse_down_ms / 1000.0)
            executor._check_stop()
            pyautogui.moveTo(target_x, y, duration=0)
            executor.move_calls += 1
            executor._wait_interruptibly(0.03)
        finally:
            if not executor._release_mouse():
                raise RuntimeError(
                    f"Не удалось отпустить мышь после переключения кисти на {value}: "
                    f"{executor._release_errors[-1]}"
                )
        executor._wait_interruptibly(executor.config.after_mouse_up_ms / 1000.0)
        self.current_value = value
        self.selection_count += 1
        self.selection_order.append(value)
        return f"Выбрана кисть {value}."


def color_plan_to_drawing_plan(plan: Any) -> DrawingPlan:
    """Convert color geometry to the stage-14 DrawingPlan without losing stroke order.

    Color information is kept in string metadata for reporting and is consumed by
    ColorPlanExecutionHooks. This converted plan must never be sent to the monochrome
    executor without those hooks.
    """
    color_plan = validate_color_plan(plan)
    canvas = color_plan["canvas"]
    width, height = int(canvas["width"]), int(canvas["height"])
    palette = color_plan["palette"]
    strokes: list[Stroke] = []
    for index, raw_stroke in enumerate(color_plan["strokes"], start=1):
        color = raw_stroke["color"]
        palette_index = int(color["palette_index"])
        palette_color = palette[palette_index]
        points = [Point(float(point["x"]), float(point["y"])) for point in raw_stroke["points"]]
        metadata = {
            "palette_index": str(palette_index),
            "color_id": str(palette_color["id"]),
            "color_name": str(palette_color["name"]),
            "color_hex": str(palette_color["hex"]),
            "color_rgb": ",".join(str(channel) for channel in palette_color["rgb"]),
            "color_scanline_order": str(index),
        }

        # A one-pixel run is encoded by Stage 19 as two identical points.  The
        # target board ignores a mouse click with no movement, so turn this into
        # a real one-pixel horizontal drag.  The line uses this pixel's own color.
        # DrawingPlan accepts the right canvas boundary (x == width); this keeps
        # the raster's left-to-right direction and avoids overwriting the pixel
        # immediately before a singleton at the right edge.
        if len(points) == 2 and points[0].distance_to(points[1]) == 0:
            start = points[0]
            if start.x < width:
                end = Point(start.x + 1.0, start.y)
            else:  # Defensive fallback for malformed/out-of-contract input.
                raise ColorPlanExecutionError(
                    f"Одиночный пиксель штриха №{index} находится за правой границей холста."
                )
            points = [start, end]
            metadata.update({
                "single_pixel_expanded": "true",
                "single_pixel_expansion": "horizontal_1px_same_color",
                "single_pixel_original_x": str(int(start.x)),
                "single_pixel_original_y": str(int(start.y)),
            })

        strokes.append(Stroke(
            name=str(raw_stroke.get("name") or f"color-stroke-{index}"),
            points=points,
            closed=False,
            metadata=metadata,
        ))
    converted = DrawingPlan(
        width=width,
        height=height,
        strokes=strokes,
        name=f"{str(color_plan.get('name') or 'Цветной план')} (цветное исполнение)",
        created_at=str(color_plan.get("created_at") or ""),
        schema_version=1,
    )
    return converted


def build_palette_targets(
    color_plan: Any,
    profile_document: Any,
    *,
    current_screen_size: tuple[int, int] | None = None,
) -> dict[int, PaletteTarget]:
    """Map palette indexes to confirmed/correctable screen swatch coordinates by RGB."""
    plan = validate_color_plan(color_plan)
    try:
        from palette_profiles import validate_palette_profile
        profile = validate_palette_profile(profile_document)
    except Exception as exc:
        raise ColorPlanExecutionError(f"Не удалось проверить профиль палитры: {exc}") from exc

    screen = profile["screen"]
    saved_screen = (int(screen["width"]), int(screen["height"]))
    if current_screen_size is not None:
        try:
            actual_size = (int(current_screen_size[0]), int(current_screen_size[1]))
        except (TypeError, ValueError, IndexError) as exc:
            raise ColorPlanExecutionError("Не удалось определить размер текущего экрана.") from exc
        if actual_size != saved_screen:
            raise ColorPlanExecutionError(
                f"Разрешение экрана изменилось: профиль {saved_screen[0]}×{saved_screen[1]}, "
                f"сейчас {actual_size[0]}×{actual_size[1]}. Перекалибруйте палитру на вкладке 3."
            )

    profile_by_rgb: dict[tuple[int, int, int], dict[str, Any]] = {}
    for color in profile["colors"]:
        key = tuple(int(channel) for channel in color["rgb"])
        if key in profile_by_rgb:
            raise ColorPlanExecutionError(f"В профиле повторяется цвет {color['hex']}.")
        profile_by_rgb[key] = color

    used_indexes = sorted({int(stroke["color"]["palette_index"]) for stroke in plan["strokes"]})
    targets: dict[int, PaletteTarget] = {}
    for palette_index in used_indexes:
        try:
            plan_color = plan["palette"][palette_index]
            rgb = tuple(int(channel) for channel in plan_color["rgb"])
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise ColorPlanExecutionError(f"Не удаётся прочитать цвет палитры №{palette_index + 1}.") from exc
        profile_color = profile_by_rgb.get(rgb)
        if profile_color is None:
            hex_value = str(plan_color.get("hex", rgb))
            raise ColorPlanExecutionError(
                f"В загруженном профиле «{profile['profile_name']}» нет цвета {hex_value}, "
                "который используется в цветном плане. Загрузите профиль, соответствующий этапу 18."
            )
        if profile_color.get("status") not in {"confirmed", "corrected"}:
            raise ColorPlanExecutionError(
                f"Цвет {profile_color['name']} ({profile_color['hex']}) не подтверждён. "
                "Откройте вкладку 3, подтвердите цвет и сохраните профиль перед рисованием."
            )
        x, y = int(profile_color["screen_x"]), int(profile_color["screen_y"])
        if not (0 <= x < saved_screen[0] and 0 <= y < saved_screen[1]):
            raise ColorPlanExecutionError(
                f"Координаты образца {profile_color['name']} ({x}, {y}) выходят за границы экрана."
            )
        targets[palette_index] = PaletteTarget(
            palette_index=palette_index,
            color_id=str(profile_color["id"]),
            name=str(profile_color["name"]),
            rgb=rgb,
            hex=str(profile_color["hex"]),
            screen_x=x,
            screen_y=y,
            status=str(profile_color["status"]),
        )
    return targets


class ColorPlanExecutionHooks:
    """Provides preflight palette validation and ordered color selection for MouseExecutor.

    The executor calls preflight after its countdown so the browser palette can be visible,
    then calls before_stroke immediately before each raster stroke. Colors are selected in
    the plan's original order; no stroke reordering or color grouping happens here.
    """

    def __init__(
        self,
        color_plan: Any,
        profile_document: Any,
        *,
        current_screen_size_provider: Callable[[], tuple[int, int]] | None = None,
        screenshot_provider: Callable[[], Any] | None = None,
        dpi_scale_provider: Callable[[], int] | None = None,
        brush_slider_calibration: dict[str, Any] | BrushSliderCalibration | None = None,
        brush_target_area: dict[str, int] | None = None,
    ):
        self.plan = validate_color_plan(color_plan)
        self.profile_document = profile_document
        size = current_screen_size_provider() if current_screen_size_provider else None
        self.targets = build_palette_targets(self.plan, profile_document, current_screen_size=size)
        self.current_palette_index: int | None = None
        self.selection_count = 0
        self.selection_order: list[int] = []
        self.preflight_passed = False
        self.screenshot_provider = screenshot_provider
        self.dpi_scale_provider = dpi_scale_provider
        self.brush_controller: BrushSliderController | None = None
        if brush_slider_calibration is not None:
            calibration = (
                brush_slider_calibration
                if isinstance(brush_slider_calibration, BrushSliderCalibration)
                else BrushSliderCalibration.from_dict(brush_slider_calibration)
            )
            if brush_target_area is None:
                raise ColorPlanExecutionError("Для калибровки кисти не передана область рисования.")
            self.brush_controller = BrushSliderController(
                calibration,
                brush_target_area,
                current_screen_size_provider=current_screen_size_provider,
            )
            self.brush_controller.validate()
        try:
            from palette_profiles import validate_palette_profile
            self.profile = validate_palette_profile(profile_document)
        except Exception as exc:
            raise ColorPlanExecutionError(f"Некорректный профиль палитры: {exc}") from exc

    @staticmethod
    def _get_screenshot() -> Any:
        import pyautogui
        return pyautogui.screenshot()

    @staticmethod
    def _get_dpi_scale() -> int:
        try:
            from palette_profiles import get_windows_scale_percent
            return get_windows_scale_percent()
        except Exception as exc:
            raise ColorPlanExecutionError(f"Не удалось проверить масштаб Windows: {exc}") from exc

    def preflight(self, executor: Any) -> str:
        executor._check_stop()
        screenshot = (self.screenshot_provider or self._get_screenshot)()
        dpi_scale = (self.dpi_scale_provider or self._get_dpi_scale)()
        try:
            from palette_profiles import check_profile_against_screenshot
            result = check_profile_against_screenshot(
                self.profile,
                screenshot,
                current_dpi_scale_percent=dpi_scale,
            )
        except Exception as exc:
            raise ColorPlanExecutionError(f"Не удалось проверить калибровку палитры перед рисованием: {exc}") from exc
        if result.get("status") != "current":
            details = list(result.get("issues") or []) + list(result.get("warnings") or [])
            joined = "\n".join(f"• {message}" for message in details) or "Калибровка не подтверждена."
            raise ColorPlanExecutionError(
                "Палитра не прошла проверку на текущем экране. Рисование не начато.\n"
                f"{joined}\nОткройте браузер с палитрой, проверьте профиль на вкладке 3 и повторите запуск."
            )
        if self.brush_controller is not None:
            self.brush_controller.validate()
        self.preflight_passed = True
        return f"Палитра «{self.profile['profile_name']}» проверена: {len(self.targets)} используемых цветов."

    def before_stroke(self, executor: Any, stroke_index: int, stroke: Stroke) -> str:
        try:
            palette_index = int(stroke.metadata["palette_index"])
            target = self.targets[palette_index]
        except (KeyError, TypeError, ValueError) as exc:
            raise ColorPlanExecutionError(
                f"У штриха №{stroke_index} отсутствует сопоставление с цветом палитры."
            ) from exc

        executor._check_stop()
        details: list[str] = []
        if self.current_palette_index == palette_index:
            details.append(f"Цвет {target.hex} уже выбран.")
        else:
            import pyautogui

            # Move to the saved swatch, click it, and always release before drawing.
            pyautogui.moveTo(target.screen_x, target.screen_y, duration=0)
            executor.move_calls += 1
            executor._wait_interruptibly(executor.config.before_mouse_down_ms / 1000.0)
            executor._check_stop()
            pyautogui.mouseDown()
            try:
                executor._wait_interruptibly(executor.config.after_mouse_down_ms / 1000.0)
            finally:
                if not executor._release_mouse():
                    raise RuntimeError(
                        f"Не удалось отпустить мышь после выбора цвета {target.hex}: "
                        f"{executor._release_errors[-1]}"
                    )

            executor._wait_interruptibly(executor.config.after_mouse_up_ms / 1000.0)
            self.current_palette_index = palette_index
            self.selection_count += 1
            self.selection_order.append(palette_index)
            details.append(f"Выбран цвет {target.name} {target.hex}.")
        if self.brush_controller is not None:
            details.append(self.brush_controller.before_stroke(executor, stroke_index, stroke))
        details.append(f"штрих {stroke_index} идёт по плану")
        return " ".join(details)

    def to_report(self) -> dict[str, Any]:
        return {
            "profile_name": self.profile.get("profile_name"),
            "browser_label": self.profile.get("calibration", {}).get("browser_label", ""),
            "selected_color_count": self.selection_count,
            "selection_order": list(self.selection_order),
            "used_colors": [self.targets[index].to_dict() for index in sorted(self.targets)],
            "selection_policy": "select_only_when_color_changes; preserve_scanline_stroke_order",
            "screenshot_preflight": "passed" if self.preflight_passed else "not_completed",
            "brush_size_selection_count": (
                self.brush_controller.selection_count if self.brush_controller is not None else 0
            ),
            "brush_size_selection_order": (
                list(self.brush_controller.selection_order) if self.brush_controller is not None else []
            ),
            "final_brush_value": (
                self.brush_controller.current_value if self.brush_controller is not None else None
            ),
            "brush_slider_calibration": (
                {
                    "x_at_min": self.brush_controller.calibration.x_at_min,
                    "x_at_max": self.brush_controller.calibration.x_at_max,
                    "y": self.brush_controller.calibration.y,
                    "initial_value": self.brush_controller.calibration.initial_value,
                    "screen_width": self.brush_controller.calibration.screen_width,
                    "screen_height": self.brush_controller.calibration.screen_height,
                    "confirmed": self.brush_controller.calibration.confirmed,
                }
                if self.brush_controller is not None else None
            ),
        }

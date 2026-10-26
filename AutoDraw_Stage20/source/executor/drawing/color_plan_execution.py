from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from models import DrawingPlan, Point, Stroke


class ColorPlanExecutionError(ValueError):
    """A color plan or its browser palette cannot be executed safely."""


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
        if self.current_palette_index == palette_index:
            return f"Цвет {target.hex} уже выбран; штрих {stroke_index} идёт по плану."

        import pyautogui

        # Move to the saved swatch, click it, and always release the mouse before drawing.
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
        return f"Выбран цвет {target.name} {target.hex}; штрих {stroke_index}."

    def to_report(self) -> dict[str, Any]:
        return {
            "profile_name": self.profile.get("profile_name"),
            "browser_label": self.profile.get("calibration", {}).get("browser_label", ""),
            "selected_color_count": self.selection_count,
            "selection_order": list(self.selection_order),
            "used_colors": [self.targets[index].to_dict() for index in sorted(self.targets)],
            "selection_policy": "select_only_when_color_changes; preserve_scanline_stroke_order",
            "screenshot_preflight": "passed" if self.preflight_passed else "not_completed",
        }

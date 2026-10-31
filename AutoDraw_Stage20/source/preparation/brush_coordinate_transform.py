from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any


LOGICAL_BOARD_WIDTH = 420
LOGICAL_BOARD_HEIGHT = 240
LOGICAL_BOARD_SIZE = (LOGICAL_BOARD_WIDTH, LOGICAL_BOARD_HEIGHT)


def transform_logical_brush_plan_to_screen(
    plan: dict[str, Any],
    screen_area: dict[str, int],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Map a logical 420x240 brush-test plan to screen-local ROI pixels.

    The logical board's inclusive coordinate bounds [0, 420] x [0, 240]
    are mapped to the screen ROI's pixel-center bounds [0, width-1] x
    [0, height-1]. The returned plan is a copy; the source plan is untouched.
    """
    if not isinstance(plan, dict):
        raise ValueError("Логический план кисти должен быть JSON-объектом.")
    if plan.get("coordinate_system") != "logical_board_pixels":
        raise ValueError("Преобразование разрешено только для logical_board_pixels.")
    canvas = plan.get("canvas")
    if not isinstance(canvas, dict):
        raise ValueError("В логическом плане отсутствует объект canvas.")
    logical_width = canvas.get("width")
    logical_height = canvas.get("height")
    if (logical_width, logical_height) != LOGICAL_BOARD_SIZE:
        raise ValueError(
            f"Ожидается логическая доска {LOGICAL_BOARD_WIDTH}×{LOGICAL_BOARD_HEIGHT}."
        )

    if not isinstance(screen_area, dict):
        raise ValueError("Экранная область должна быть объектом.")
    try:
        values = [screen_area[key] for key in ("x", "y", "width", "height")]
    except KeyError as exc:
        raise ValueError("Экранная область должна содержать целые x, y, width и height.") from exc
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise ValueError("Координаты и размеры экранной области должны быть целыми числами.")
    origin_x, origin_y, screen_width, screen_height = values
    if screen_width < 2 or screen_height < 2:
        raise ValueError("Экранный ROI должен быть не меньше 2×2 пикселя.")

    scale_x = (screen_width - 1) / LOGICAL_BOARD_WIDTH
    scale_y = (screen_height - 1) / LOGICAL_BOARD_HEIGHT
    transformed = deepcopy(plan)
    strokes = transformed.get("strokes")
    if not isinstance(strokes, list) or not strokes:
        raise ValueError("Логический план должен содержать непустой массив strokes.")

    for stroke in strokes:
        if not isinstance(stroke, dict) or not isinstance(stroke.get("points"), list):
            raise ValueError("Каждый штрих должен содержать массив points.")
        for point in stroke["points"]:
            if not isinstance(point, dict):
                raise ValueError("Точки логического плана должны быть объектами x/y.")
            x, y = point.get("x"), point.get("y")
            if (
                isinstance(x, bool) or isinstance(y, bool)
                or not isinstance(x, (int, float)) or not isinstance(y, (int, float))
                or not isfinite(float(x)) or not isfinite(float(y))
            ):
                raise ValueError("Координаты логического плана должны быть конечными числами.")
            if not (0 <= x <= LOGICAL_BOARD_WIDTH and 0 <= y <= LOGICAL_BOARD_HEIGHT):
                raise ValueError(
                    f"Логическая точка ({x}, {y}) выходит за границы "
                    f"{LOGICAL_BOARD_WIDTH}×{LOGICAL_BOARD_HEIGHT}."
                )
            point["x"] = float(x) * scale_x
            point["y"] = float(y) * scale_y

    transform = {
        "method": "inclusive_logical_bounds_to_screen_pixel_centers",
        "source_coordinate_system": "logical_board_pixels",
        "target_coordinate_system": "local_canvas_pixels",
        "logical_board": {"width": LOGICAL_BOARD_WIDTH, "height": LOGICAL_BOARD_HEIGHT},
        "screen_roi": {
            "x": origin_x, "y": origin_y,
            "width": screen_width, "height": screen_height,
        },
        "scale_x": scale_x,
        "scale_y": scale_y,
        "logical_bounds": {
            "x": [0, LOGICAL_BOARD_WIDTH],
            "y": [0, LOGICAL_BOARD_HEIGHT],
        },
        "screen_local_bounds": {
            "x": [0, screen_width - 1],
            "y": [0, screen_height - 1],
        },
        "boundary_mapping": "logical_max_to_last_screen_pixel",
        "executor_coordinate_units": "screen_pixels",
        "point_step_px_units": "screen_pixels",
    }

    transformed["coordinate_system"] = "local_canvas_pixels"
    transformed["canvas"] = {"width": screen_width, "height": screen_height}
    transformed["width"] = screen_width
    transformed["height"] = screen_height
    generation = transformed.setdefault("generation", {})
    if not isinstance(generation, dict):
        raise ValueError("Поле generation должно быть объектом.")
    generation["source_coordinate_system"] = "logical_board_pixels"
    generation["source_canvas"] = {
        "width": LOGICAL_BOARD_WIDTH, "height": LOGICAL_BOARD_HEIGHT,
    }
    generation["screen_transform"] = transform
    return transformed, transform

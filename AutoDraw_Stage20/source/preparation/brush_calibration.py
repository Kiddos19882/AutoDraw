from __future__ import annotations

"""Versioned screen-coordinate profile for brush and paint-meter calibration."""

import json
import os
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

PROFILE_SCHEMA_VERSION = 1
COORDINATE_SYSTEM = "primary_screen_physical_pixels"
POINT_KEYS = (
    "clear_board",
    "brush_7",
    "brush_14",
    "brush_20",
    "brush_slider_value_1",
    "brush_slider_value_30",
    "editor_open",
    "save_drawing",
)
REGION_KEYS = ("board_area", "paint_meter_area", "brush_value_area")
VALID_STATUSES = {"not_set", "set", "verified", "needs_review"}


class BrushCalibrationError(ValueError):
    """Raised when a brush-calibration profile is invalid or unsafe to use."""


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool):
        raise BrushCalibrationError(f"{label}: требуется целое число.")
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise BrushCalibrationError(f"{label}: требуется целое число.") from exc
    if parsed != value or parsed < minimum:
        raise BrushCalibrationError(f"{label}: значение должно быть целым числом не меньше {minimum}.")
    return parsed


def _screen_size(screen_size: tuple[int, int] | list[int] | None) -> tuple[int, int] | None:
    if screen_size is None:
        return None
    if not isinstance(screen_size, (tuple, list)) or len(screen_size) != 2:
        raise BrushCalibrationError("Размер экрана должен содержать ширину и высоту.")
    width = _integer(screen_size[0], "Ширина экрана", minimum=1)
    height = _integer(screen_size[1], "Высота экрана", minimum=1)
    if width > 32768 or height > 32768:
        raise BrushCalibrationError("Размер экрана превышает допустимый диапазон.")
    return width, height


def create_default_profile(
    screen_size: tuple[int, int] | list[int] | None = None,
) -> dict[str, Any]:
    size = _screen_size(screen_size)
    return {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "profile_name": "brush-paint-calibration",
        "coordinate_system": COORDINATE_SYSTEM,
        "environment": {
            "screen_width": size[0] if size else None,
            "screen_height": size[1] if size else None,
            "windows_scale_percent": None,
            "browser_zoom_percent": 100,
            "browser": "",
            "browser_version": "",
        },
        "points": {key: None for key in POINT_KEYS},
        "regions": {key: None for key in REGION_KEYS},
        "status": {
            "points": {key: "not_set" for key in POINT_KEYS},
            "regions": {key: "not_set" for key in REGION_KEYS},
        },
    }


def normalize_point(
    x: Any,
    y: Any,
    screen_size: tuple[int, int] | list[int] | None = None,
) -> dict[str, int]:
    px = _integer(x, "X")
    py = _integer(y, "Y")
    size = _screen_size(screen_size)
    if size and (px >= size[0] or py >= size[1]):
        raise BrushCalibrationError(
            f"Точка ({px}, {py}) находится за пределами экрана {size[0]} × {size[1]}."
        )
    return {"x": px, "y": py}


def normalize_region(
    x1: Any,
    y1: Any,
    x2: Any,
    y2: Any,
    screen_size: tuple[int, int] | list[int] | None = None,
    *,
    min_width: int = 2,
    min_height: int = 2,
) -> dict[str, int]:
    ax, ay = _integer(x1, "X1"), _integer(y1, "Y1")
    bx, by = _integer(x2, "X2"), _integer(y2, "Y2")
    left, top = min(ax, bx), min(ay, by)
    right, bottom = max(ax, bx), max(ay, by)
    width, height = right - left, bottom - top
    if width < min_width or height < min_height:
        raise BrushCalibrationError(
            f"Область слишком мала: требуется не менее {min_width} × {min_height} px."
        )
    size = _screen_size(screen_size)
    if size and (right > size[0] or bottom > size[1]):
        raise BrushCalibrationError(
            f"Область ({left}, {top}, {width}, {height}) выходит за пределы экрана {size[0]} × {size[1]}."
        )
    return {"x": left, "y": top, "width": width, "height": height}


def validate_profile(profile: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(profile, dict):
        raise BrushCalibrationError("Профиль калибровки должен быть JSON-объектом.")
    if profile.get("schema_version") != PROFILE_SCHEMA_VERSION:
        raise BrushCalibrationError(f"Неподдерживаемая версия профиля: {profile.get('schema_version')!r}.")
    if profile.get("coordinate_system") != COORDINATE_SYSTEM:
        raise BrushCalibrationError("Неизвестная система экранных координат.")
    if not isinstance(profile.get("profile_name"), str) or not profile["profile_name"].strip():
        raise BrushCalibrationError("Имя профиля не должно быть пустым.")

    env = profile.get("environment")
    points = profile.get("points")
    regions = profile.get("regions")
    status = profile.get("status")
    if not all(isinstance(value, dict) for value in (env, points, regions, status)):
        raise BrushCalibrationError("Профиль должен содержать объекты environment, points, regions и status.")
    screen_width = env.get("screen_width")
    screen_height = env.get("screen_height")
    if (screen_width is None) != (screen_height is None):
        raise BrushCalibrationError("Ширину и высоту экрана нужно указывать одновременно.")
    size = _screen_size((screen_width, screen_height) if screen_width is not None else None)

    for key in POINT_KEYS:
        if key not in points:
            raise BrushCalibrationError(f"В профиле отсутствует точка {key}.")
        value = points[key]
        state = status.get("points", {}).get(key) if isinstance(status.get("points"), dict) else None
        if state not in VALID_STATUSES:
            raise BrushCalibrationError(f"Некорректный статус точки {key}.")
        if value is None:
            if state != "not_set":
                raise BrushCalibrationError(f"Пустая точка {key} должна иметь статус not_set.")
            continue
        if not isinstance(value, dict) or set(value) < {"x", "y"}:
            raise BrushCalibrationError(f"Точка {key} должна содержать X и Y.")
        normalized = normalize_point(value["x"], value["y"], size)
        if normalized != {"x": value["x"], "y": value["y"]}:
            raise BrushCalibrationError(f"Точка {key} содержит некорректные координаты.")
        if state == "not_set":
            raise BrushCalibrationError(f"Заданная точка {key} не может иметь статус not_set.")

    for key in REGION_KEYS:
        if key not in regions:
            raise BrushCalibrationError(f"В профиле отсутствует область {key}.")
        value = regions[key]
        state = status.get("regions", {}).get(key) if isinstance(status.get("regions"), dict) else None
        if state not in VALID_STATUSES:
            raise BrushCalibrationError(f"Некорректный статус области {key}.")
        if value is None:
            if state != "not_set":
                raise BrushCalibrationError(f"Пустая область {key} должна иметь статус not_set.")
            continue
        if not isinstance(value, dict) or not {"x", "y", "width", "height"} <= set(value):
            raise BrushCalibrationError(f"Область {key} должна содержать X, Y, width и height.")
        normalized = normalize_region(
            value["x"], value["y"],
            value["x"] + value["width"], value["y"] + value["height"],
            size,
        )
        if normalized != {name: value[name] for name in ("x", "y", "width", "height")}:
            raise BrushCalibrationError(f"Область {key} содержит некорректные координаты.")
        if state == "not_set":
            raise BrushCalibrationError(f"Заданная область {key} не может иметь статус not_set.")

    for key in ("browser_zoom_percent", "windows_scale_percent"):
        value = env.get(key)
        if value is not None:
            parsed = _integer(value, key, minimum=25)
            if parsed > 500:
                raise BrushCalibrationError(f"{key}: значение должно быть в диапазоне 25–500.")
    for key in ("browser", "browser_version"):
        if key in env and not isinstance(env[key], str):
            raise BrushCalibrationError(f"environment.{key} должно быть текстом.")
    return profile


def adapt_profile_to_screen(
    profile: dict[str, Any],
    screen_size: tuple[int, int] | list[int],
) -> tuple[dict[str, Any], bool]:
    """Mark old coordinates for review when the primary-screen dimensions changed."""
    result = deepcopy(validate_profile(profile))
    width, height = _screen_size(screen_size)
    env = result["environment"]
    old_size = (env.get("screen_width"), env.get("screen_height"))
    if old_size == (width, height):
        return result, False

    env["screen_width"], env["screen_height"] = width, height
    for key, point in result["points"].items():
        if point is None:
            continue
        if point["x"] >= width or point["y"] >= height:
            result["points"][key] = None
            result["status"]["points"][key] = "not_set"
        else:
            result["status"]["points"][key] = "needs_review"
    for key, region in result["regions"].items():
        if region is None:
            continue
        if region["x"] + region["width"] > width or region["y"] + region["height"] > height:
            result["regions"][key] = None
            result["status"]["regions"][key] = "not_set"
        else:
            result["status"]["regions"][key] = "needs_review"
    validate_profile(result)
    return result, True


def missing_required_fields(
    profile: dict[str, Any],
    brush_value: int | None = None,
) -> list[str]:
    validate_profile(profile)
    missing: list[str] = []
    for key in ("clear_board",):
        if profile["points"].get(key) is None:
            missing.append(key)
    for key in ("board_area", "paint_meter_area"):
        if profile["regions"].get(key) is None:
            missing.append(key)
    if brush_value is not None:
        if isinstance(brush_value, bool) or not isinstance(brush_value, int) or not 1 <= brush_value <= 30:
            raise BrushCalibrationError("Размер кисти должен быть целым числом от 1 до 30.")
        if brush_value in (7, 14, 20):
            key = f"brush_{brush_value}"
            if profile["points"].get(key) is None:
                missing.append(key)
        elif profile["points"].get("brush_slider_value_1") is None or profile["points"].get("brush_slider_value_30") is None:
            for key in ("brush_slider_value_1", "brush_slider_value_30"):
                if profile["points"].get(key) is None:
                    missing.append(key)
    return missing


def save_profile(path: str | Path, profile: dict[str, Any]) -> Path:
    validated = validate_profile(deepcopy(profile))
    destination = Path(path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{destination.stem}.", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(validated, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, destination)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise
    return destination


def load_profile(path: str | Path) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    try:
        with source.open("r", encoding="utf-8-sig") as stream:
            document = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise BrushCalibrationError(f"Не удалось загрузить профиль {source}: {exc}") from exc
    return deepcopy(validate_profile(document))

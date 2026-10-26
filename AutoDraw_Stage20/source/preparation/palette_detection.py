from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import cv2
import numpy as np
from PIL import Image

SCHEMA_VERSION = 1


class PaletteFormatError(ValueError):
    """Raised when a saved browser palette is malformed or unsupported."""


def rgb_to_hex(rgb: Iterable[int]) -> str:
    values = tuple(int(value) for value in rgb)
    if len(values) != 3 or any(value < 0 or value > 255 for value in values):
        raise ValueError("RGB должен содержать три значения от 0 до 255.")
    return "#{:02X}{:02X}{:02X}".format(*values)


def parse_hex_color(value: str) -> tuple[int, int, int]:
    text = str(value).strip()
    if text.startswith("#"):
        text = text[1:]
    if len(text) != 6:
        raise ValueError("Цвет должен быть задан в формате #RRGGBB.")
    try:
        values = tuple(int(text[index:index + 2], 16) for index in (0, 2, 4))
    except ValueError as exc:
        raise ValueError("Цвет должен быть задан в формате #RRGGBB.") from exc
    return values  # type: ignore[return-value]


def sample_color_at(
    image: Image.Image,
    x: int,
    y: int,
    *,
    radius: int = 2,
) -> tuple[int, int, int]:
    """Sample a small central patch, using its channel-wise median to reduce noise."""
    rgb = image.convert("RGB")
    if not (0 <= int(x) < rgb.width and 0 <= int(y) < rgb.height):
        raise ValueError("Точка выборки находится за пределами изображения.")
    radius = max(0, min(int(radius), 10))
    x1, x2 = max(0, x - radius), min(rgb.width, x + radius + 1)
    y1, y2 = max(0, y - radius), min(rgb.height, y + radius + 1)
    patch = np.asarray(rgb.crop((x1, y1, x2, y2)), dtype=np.uint8).reshape(-1, 3)
    median = np.median(patch, axis=0).astype(np.uint8)
    return tuple(int(channel) for channel in median)  # type: ignore[return-value]


def build_palette_entry(
    image: Image.Image,
    local_x: int,
    local_y: int,
    *,
    origin_x: int = 0,
    origin_y: int = 0,
    source: str = "manual",
    name: str | None = None,
    radius: int = 2,
) -> dict[str, Any]:
    """Create a palette entry whose pick coordinates are desktop screen coordinates."""
    rgb = sample_color_at(image, local_x, local_y, radius=radius)
    return {
        "name": name or "Цвет",
        "hex": rgb_to_hex(rgb),
        "rgb": list(rgb),
        "screen_x": int(origin_x) + int(local_x),
        "screen_y": int(origin_y) + int(local_y),
        "local_x": int(local_x),
        "local_y": int(local_y),
        "source": str(source),
    }


def _sample_component_color(image: Image.Image, x: int, y: int, w: int, h: int) -> tuple[int, int, int]:
    """Use the central part of a candidate swatch rather than its border."""
    pad_x = max(0, int(w * 0.22))
    pad_y = max(0, int(h * 0.22))
    left = x + pad_x
    top = y + pad_y
    right = max(left + 1, x + w - pad_x)
    bottom = max(top + 1, y + h - pad_y)
    return sample_color_at(image, (left + right - 1) // 2, (top + bottom - 1) // 2, radius=2)


def detect_color_candidates(
    region_image: Image.Image,
    *,
    origin_x: int = 0,
    origin_y: int = 0,
    min_area: int = 40,
    min_dimension: int = 6,
    max_dimension: int = 180,
    saturation_threshold: int = 35,
) -> list[dict[str, Any]]:
    """Find likely colourful swatches in a cropped screenshot.

    This is deliberately a candidate finder, not a claim of perfect palette detection.
    It detects substantial connected colourful patches; grayscale colors and buttons
    with icons/borders may need to be sampled manually in the UI.
    """
    rgb_image = region_image.convert("RGB")
    rgb = np.asarray(rgb_image, dtype=np.uint8)
    if rgb_image.width < min_dimension or rgb_image.height < min_dimension:
        return []

    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    # Keep colourful non-near-black patches. White/gray/black are sampled manually.
    mask = cv2.inRange(
        hsv,
        np.array([0, max(0, min(255, saturation_threshold)), 20], dtype=np.uint8),
        np.array([179, 255, 255], dtype=np.uint8),
    )
    kernel = np.ones((3, 3), dtype=np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates: list[dict[str, Any]] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = int(cv2.contourArea(contour))
        if area < min_area:
            continue
        if w < min_dimension or h < min_dimension or w > max_dimension or h > max_dimension:
            continue
        aspect = w / max(1, h)
        if aspect < 0.40 or aspect > 2.50:
            continue
        fill_ratio = area / max(1, w * h)
        if fill_ratio < 0.35:
            continue
        local_x = x + w // 2
        local_y = y + h // 2
        r, g, b = _sample_component_color(rgb_image, x, y, w, h)
        if max(r, g, b) - min(r, g, b) < saturation_threshold:
            # Do not report a candidate if the swatch's central pixels are actually gray.
            continue
        candidates.append({
            "name": "Цвет",
            "hex": rgb_to_hex((r, g, b)),
            "rgb": [r, g, b],
            "screen_x": int(origin_x) + local_x,
            "screen_y": int(origin_y) + local_y,
            "local_x": local_x,
            "local_y": local_y,
            "source": "auto",
            "bounds": {"x": x, "y": y, "width": w, "height": h},
            "area": area,
        })

    # Top-to-bottom, then left-to-right, matching the drawing convention.
    candidates.sort(key=lambda item: (item["local_y"], item["local_x"]))
    return candidates


def merge_palette_entries(
    current: list[dict[str, Any]],
    incoming: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Append colors that are not already present; uniqueness is by RGB hex value."""
    merged = [dict(item) for item in current]
    known = {str(item.get("hex", "")).upper() for item in merged}
    added = 0
    for raw in incoming:
        color_hex = str(raw.get("hex", "")).upper()
        if color_hex in known:
            continue
        item = dict(raw)
        item["name"] = f"Цвет {len(merged) + 1}"
        item.pop("bounds", None)
        item.pop("area", None)
        merged.append(item)
        known.add(color_hex)
        added += 1
    return merged, added


def validate_palette_document(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise PaletteFormatError("Корневой элемент файла палитры должен быть объектом JSON.")
    if document.get("schema_version") != SCHEMA_VERSION:
        raise PaletteFormatError(f"Неподдерживаемая версия палитры: {document.get('schema_version')!r}.")
    screen = document.get("screen")
    region = document.get("region")
    colors = document.get("colors")
    if not isinstance(screen, dict) or not isinstance(region, dict) or not isinstance(colors, list):
        raise PaletteFormatError("В файле палитры обязательны объекты screen, region и массив colors.")
    for key in ("width", "height"):
        value = screen.get(key)
        if not isinstance(value, int) or value <= 0:
            raise PaletteFormatError(f"screen.{key} должен быть положительным целым числом.")
    for key in ("x", "y", "width", "height"):
        value = region.get(key)
        if not isinstance(value, int) or (key in ("width", "height") and value <= 0) or (key in ("x", "y") and value < 0):
            raise PaletteFormatError(f"region.{key} имеет недопустимое значение.")
    if region["x"] + region["width"] > screen["width"] or region["y"] + region["height"] > screen["height"]:
        raise PaletteFormatError("Область палитры выходит за границы снимка экрана.")
    metadata = document.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise PaletteFormatError("metadata должен быть объектом JSON.")
    seen: set[str] = set()
    validated_colors: list[dict[str, Any]] = []
    for index, raw in enumerate(colors, start=1):
        if not isinstance(raw, dict):
            raise PaletteFormatError(f"Цвет №{index} должен быть объектом.")
        try:
            hex_color = "#" + str(raw["hex"]).strip().lstrip("#").upper()
            parsed = parse_hex_color(hex_color)
            rgb_raw = raw["rgb"]
            rgb = tuple(int(v) for v in rgb_raw)
            screen_x = int(raw["screen_x"])
            screen_y = int(raw["screen_y"])
            local_x = int(raw["local_x"])
            local_y = int(raw["local_y"])
        except (KeyError, TypeError, ValueError) as exc:
            raise PaletteFormatError(f"Некорректные данные цвета №{index}: {exc}") from exc
        if len(rgb) != 3 or any(v < 0 or v > 255 for v in rgb) or rgb != parsed:
            raise PaletteFormatError(f"RGB и HEX цвета №{index} не совпадают.")
        if min(screen_x, screen_y, local_x, local_y) < 0:
            raise PaletteFormatError(f"Координаты цвета №{index} не могут быть отрицательными.")
        if local_x >= region["width"] or local_y >= region["height"]:
            raise PaletteFormatError(f"Координаты цвета №{index} находятся за пределами области палитры.")
        if screen_x != region["x"] + local_x or screen_y != region["y"] + local_y:
            raise PaletteFormatError(f"Экранные координаты цвета №{index} не соответствуют области палитры.")
        if hex_color in seen:
            raise PaletteFormatError(f"Цвет {hex_color} повторяется в палитре.")
        seen.add(hex_color)
        validated_colors.append({
            "name": str(raw.get("name") or f"Цвет {index}"),
            "hex": hex_color,
            "rgb": list(rgb),
            "screen_x": screen_x,
            "screen_y": screen_y,
            "local_x": local_x,
            "local_y": local_y,
            "source": str(raw.get("source") or "manual"),
        })
    if not validated_colors:
        raise PaletteFormatError("В палитре должен быть хотя бы один цвет.")

    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": str(document.get("created_at") or datetime.now(timezone.utc).isoformat()),
        "screen": {"width": int(screen["width"]), "height": int(screen["height"])},
        "region": {key: int(region[key]) for key in ("x", "y", "width", "height")},
        "colors": validated_colors,
        "metadata": dict(metadata),
    }


def create_palette_document(
    colors: list[dict[str, Any]],
    *,
    screen_size: tuple[int, int],
    region: dict[str, int],
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return validate_palette_document({
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "screen": {"width": int(screen_size[0]), "height": int(screen_size[1])},
        "region": {key: int(region[key]) for key in ("x", "y", "width", "height")},
        "colors": colors,
        "metadata": metadata or {},
    })


def save_palette(path: str | Path, document: dict[str, Any]) -> Path:
    """Validate and atomically save a palette JSON without silently overwriting invalid data."""
    target = Path(path).resolve()
    normalized = validate_palette_document(document)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{target.stem}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(normalized, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        Path(temporary_name).replace(target)
    except Exception:
        try:
            Path(temporary_name).unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return target


def load_palette(path: str | Path) -> dict[str, Any]:
    try:
        with Path(path).open("r", encoding="utf-8") as stream:
            document = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise PaletteFormatError(f"Не удалось прочитать палитру: {exc}") from exc
    return validate_palette_document(document)

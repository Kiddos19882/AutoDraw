from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
from PIL import Image, ImageOps

FitMode = Literal["contain", "cover", "stretch"]
ThresholdMode = Literal["manual", "otsu"]


@dataclass(frozen=True, slots=True)
class ProcessingSettings:
    """Настройки преобразования уже вписанного в размер холста изображения."""

    brightness: int = 0
    contrast: float = 1.0
    denoise_level: int = 0  # 0 — выключено, 1..4 — median blur 3..9 px
    threshold_mode: ThresholdMode = "otsu"
    threshold: int = 128

    def __post_init__(self) -> None:
        if not -100 <= self.brightness <= 100:
            raise ValueError("Яркость должна быть в диапазоне от -100 до 100.")
        if not math.isfinite(self.contrast) or not 0.5 <= self.contrast <= 2.5:
            raise ValueError("Контраст должен быть в диапазоне от 0.5 до 2.5.")
        if not 0 <= self.denoise_level <= 4:
            raise ValueError("Уровень подавления шума должен быть от 0 до 4.")
        if self.threshold_mode not in ("manual", "otsu"):
            raise ValueError("Неизвестный режим бинаризации.")
        if not 0 <= self.threshold <= 255:
            raise ValueError("Порог бинаризации должен быть от 0 до 255.")


@dataclass(slots=True)
class ProcessingResult:
    """Результаты подготовки. Все выходные изображения имеют размер холста."""

    prepared_color: Image.Image
    grayscale: Image.Image
    binary_mask: Image.Image
    threshold_used: int
    target_width: int
    target_height: int
    fit_mode: FitMode
    crop_box: tuple[int, int, int, int] | None
    settings: ProcessingSettings


def load_rgb_image(path: str | Path) -> Image.Image:
    """Открывает изображение, учитывает EXIF-ориентацию и сводит прозрачность к белому."""
    source_path = Path(path)
    try:
        with Image.open(source_path) as opened:
            oriented = ImageOps.exif_transpose(opened)
            if oriented.mode in ("RGBA", "LA") or "transparency" in oriented.info:
                rgba = oriented.convert("RGBA")
                background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
                return Image.alpha_composite(background, rgba).convert("RGB")
            return oriented.convert("RGB")
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ValueError(f"Не удалось открыть изображение: {exc}") from exc


def _validate_crop_box(crop_box: tuple[int, int, int, int] | None,
                       image_width: int, image_height: int) -> tuple[int, int, int, int] | None:
    if crop_box is None:
        return None
    if len(crop_box) != 4:
        raise ValueError("Область обрезки должна содержать x1, y1, x2, y2.")
    x1, y1, x2, y2 = (int(value) for value in crop_box)
    if x1 < 0 or y1 < 0 or x2 > image_width or y2 > image_height or x2 <= x1 or y2 <= y1:
        raise ValueError("Область обрезки выходит за границы изображения или имеет нулевой размер.")
    if x2 - x1 < 2 or y2 - y1 < 2:
        raise ValueError("Область обрезки слишком маленькая.")
    return x1, y1, x2, y2


def fit_to_canvas(image: Image.Image, target_width: int, target_height: int,
                  fit_mode: FitMode) -> Image.Image:
    """Возвращает RGB-изображение точного размера холста."""
    if target_width <= 0 or target_height <= 0:
        raise ValueError("Ширина и высота холста должны быть положительными.")
    if target_width * target_height > 40_000_000:
        raise ValueError("Размер холста слишком велик для безопасной обработки (более 40 млн пикселей).")
    if fit_mode not in ("contain", "cover", "stretch"):
        raise ValueError(f"Неизвестный режим масштабирования: {fit_mode}")

    rgb = image.convert("RGB")
    target_size = (int(target_width), int(target_height))
    resampling = Image.Resampling.LANCZOS

    if fit_mode == "stretch":
        return rgb.resize(target_size, resampling)

    source_width, source_height = rgb.size
    scale_x = target_width / source_width
    scale_y = target_height / source_height
    scale = min(scale_x, scale_y) if fit_mode == "contain" else max(scale_x, scale_y)

    if fit_mode == "contain":
        resized_width = max(1, min(target_width, round(source_width * scale)))
        resized_height = max(1, min(target_height, round(source_height * scale)))
        resized = rgb.resize((resized_width, resized_height), resampling)
        canvas = Image.new("RGB", target_size, (255, 255, 255))
        offset = ((target_width - resized_width) // 2, (target_height - resized_height) // 2)
        canvas.paste(resized, offset)
        return canvas

    # cover: после увеличения обе стороны должны быть не меньше целевого размера.
    resized_width = max(target_width, math.ceil(source_width * scale))
    resized_height = max(target_height, math.ceil(source_height * scale))
    resized = rgb.resize((resized_width, resized_height), resampling)
    left = (resized_width - target_width) // 2
    top = (resized_height - target_height) // 2
    return resized.crop((left, top, left + target_width, top + target_height))


def process_image(image: Image.Image,
                  target_width: int,
                  target_height: int,
                  fit_mode: FitMode = "contain",
                  crop_box: tuple[int, int, int, int] | None = None,
                  settings: ProcessingSettings | None = None) -> ProcessingResult:
    """Полный конвейер: crop -> fit -> grayscale -> denoise -> contrast/brightness -> threshold.

    В бинарной маске чёрный (0) обозначает тёмные области исходника, белый (255) — фон.
    """
    settings = settings or ProcessingSettings()
    if target_width <= 0 or target_height <= 0:
        raise ValueError("Размеры холста должны быть положительными.")
    if target_width * target_height > 40_000_000:
        raise ValueError("Размер холста слишком велик для безопасной обработки (более 40 млн пикселей).")

    rgb = image.convert("RGB")
    validated_box = _validate_crop_box(crop_box, *rgb.size)
    if validated_box is not None:
        rgb = rgb.crop(validated_box)

    prepared_color = fit_to_canvas(rgb, int(target_width), int(target_height), fit_mode)
    rgb_array = np.asarray(prepared_color, dtype=np.uint8)
    gray_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2GRAY)

    if settings.denoise_level > 0:
        kernel_size = settings.denoise_level * 2 + 1
        gray_array = cv2.medianBlur(gray_array, kernel_size)

    # Держим преобразование детерминированным и ограничиваем диапазон 0..255.
    transformed = (gray_array.astype(np.float32) - 127.5) * float(settings.contrast) + 127.5 + settings.brightness
    gray_array = np.clip(transformed, 0, 255).astype(np.uint8)

    if settings.threshold_mode == "otsu":
        threshold_value, binary_array = cv2.threshold(
            gray_array, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU
        )
    else:
        threshold_value, binary_array = cv2.threshold(
            gray_array, int(settings.threshold), 255, cv2.THRESH_BINARY
        )

    return ProcessingResult(
        prepared_color=prepared_color,
        grayscale=Image.fromarray(gray_array, mode="L"),
        binary_mask=Image.fromarray(binary_array, mode="L"),
        threshold_used=int(round(threshold_value)),
        target_width=int(target_width),
        target_height=int(target_height),
        fit_mode=fit_mode,
        crop_box=validated_box,
        settings=settings,
    )

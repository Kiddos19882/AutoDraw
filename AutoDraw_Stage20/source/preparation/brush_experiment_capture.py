from __future__ import annotations

"""Pure helpers for calibrated board and paint-meter experiment snapshots."""

from typing import Any

from PIL import Image, ImageChops


REQUIRED_REGIONS = ("board_area", "paint_meter_area")


def crop_calibrated_regions(
    screen: Image.Image,
    regions: dict[str, Any],
) -> dict[str, Image.Image]:
    """Crop calibrated regions from a screen image, rejecting stale/out-of-bounds ROIs."""
    if not isinstance(screen, Image.Image) or screen.width < 1 or screen.height < 1:
        raise ValueError("Снимок экрана пуст или имеет неверный формат.")
    if not isinstance(regions, dict):
        raise ValueError("Не заданы откалиброванные области.")

    crops: dict[str, Image.Image] = {}
    for key in REQUIRED_REGIONS:
        region = regions.get(key)
        if not isinstance(region, dict):
            raise ValueError(f"В профиле не задана область {key}.")
        try:
            x, y = int(region["x"]), int(region["y"])
            width, height = int(region["width"]), int(region["height"])
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"Область {key} содержит некорректные координаты.") from exc
        if x < 0 or y < 0 or width < 2 or height < 2:
            raise ValueError(f"Область {key} должна иметь положительные координаты и размер.")
        if x + width > screen.width or y + height > screen.height:
            raise ValueError(
                f"Область {key} ({x}, {y}, {width}, {height}) выходит за снимок "
                f"{screen.width} × {screen.height}; проверь разрешение и профиль."
            )
        crops[key] = screen.crop((x, y, x + width, y + height)).copy()
    return crops


def compare_images(first: Image.Image, second: Image.Image) -> dict[str, Any]:
    """Report visual pixel differences without claiming to decode the game meter value."""
    if not isinstance(first, Image.Image) or not isinstance(second, Image.Image):
        raise ValueError("Для сравнения нужны два изображения.")
    if first.size != second.size:
        raise ValueError(f"Размеры снимков различаются: {first.size} и {second.size}.")

    left = first.convert("RGB")
    right = second.convert("RGB")
    difference = ImageChops.difference(left, right)
    total_pixels = left.width * left.height
    changed_pixels = sum(1 for pixel in difference.getdata() if pixel != (0, 0, 0))
    channel_means = difference.getchannel("R"), difference.getchannel("G"), difference.getchannel("B")
    mean_absolute_difference = sum(
        sum(channel.getdata()) / total_pixels for channel in channel_means
    ) / 3
    return {
        "width": left.width,
        "height": left.height,
        "total_pixels": total_pixels,
        "changed_pixels": changed_pixels,
        "changed_percent": round(100.0 * changed_pixels / total_pixels, 4),
        "pixel_similarity_percent": round(100.0 * (total_pixels - changed_pixels) / total_pixels, 4),
        "mean_absolute_rgb_difference": round(mean_absolute_difference, 4),
        "exact_match": changed_pixels == 0,
        "interpretation": "visual_pixel_comparison_only_not_a_reading_of_the_game_resource_counter",
    }

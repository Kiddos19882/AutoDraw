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


def measure_meter_fill_against_baseline(baseline: Image.Image, current: Image.Image, *, color_distance_threshold: float = 24.0, minimum_changed_suffix_fraction: float = 0.03) -> dict[str, Any]:
    """Estimate a left-filled bar against a known full baseline; ambiguous cases stay inconclusive."""
    import math
    if not isinstance(baseline, Image.Image) or not isinstance(current, Image.Image):
        raise ValueError("Для измерения шкалы нужны два изображения.")
    if baseline.size != current.size:
        raise ValueError(f"Размеры шкалы различаются: {baseline.size} и {current.size}.")
    if baseline.width < 8 or baseline.height < 3:
        raise ValueError("Область шкалы слишком мала для надёжного измерения.")
    if color_distance_threshold <= 0 or not 0 < minimum_changed_suffix_fraction < 0.5:
        raise ValueError("Некорректные параметры измерения шкалы.")
    left, right = baseline.convert("RGB"), current.convert("RGB")
    y0, y1 = max(1, int(left.height * .2)), min(left.height - 1, max(2, int(left.height * .8)))
    base_cols, now_cols = [], []
    for x in range(left.width):
        a = sorted(left.getpixel((x, y)) for y in range(y0, y1))
        b = sorted(right.getpixel((x, y)) for y in range(y0, y1))
        base_cols.append(a[len(a)//2])
        now_cols.append(b[len(b)//2])
    distances = [math.sqrt(sum((c1-c2)**2 for c1,c2 in zip(a,b))) for a,b in zip(base_cols,now_cols)]
    changed = [d > color_distance_threshold for d in distances]
    count = sum(changed)
    common = {"bar_width_px": left.width, "changed_columns": count, "color_distance_threshold": color_distance_threshold,
              "method": "baseline_color_suffix_estimate", "interpretation": "estimate_only_not_game_counter_or_OCR"}
    if count == 0:
        return {**common, "status":"unchanged_or_full", "filled_width_px":left.width, "fill_fraction":1.0,
                "fill_percent":100.0, "confidence":"low",
                "note":"Изменений относительно исходной шкалы не обнаружено; полный ресурс не доказан."}
    first = next((i for i,v in enumerate(changed) if v), left.width)
    suffix = changed[first:]
    suffix_consistency = sum(suffix)/len(suffix) if suffix else 0.0
    prefix_consistency = sum(not v for v in changed[:first])/first if first else 1.0
    if (len(suffix)/left.width < minimum_changed_suffix_fraction or suffix_consistency < .9 or prefix_consistency < .9):
        return {**common, "status":"inconclusive", "filled_width_px":None, "fill_fraction":None,
                "fill_percent":None, "confidence":"low",
                "note":"Изменения не образуют достаточно чёткую непрерывную правую часть шкалы."}
    fraction = first/left.width
    return {**common, "status":"estimated", "filled_width_px":first, "fill_fraction":round(fraction,5),
            "fill_percent":round(fraction*100,2), "confidence":"provisional",
            "suffix_consistency":round(suffix_consistency,4), "prefix_consistency":round(prefix_consistency,4),
            "note":"Оценка предполагает полную исходную шкалу и уменьшение заполнения справа налево."}


def evaluate_meter_restoration(baseline: Image.Image, after_clear: Image.Image, *, tolerance_fraction: float = .03) -> dict[str, Any]:
    """Classify whether the post-clear meter visually returned to its baseline."""
    if not 0 <= tolerance_fraction <= .25:
        raise ValueError("Допуск восстановления должен быть от 0 до 0.25.")
    estimate = measure_meter_fill_against_baseline(baseline, after_clear)
    comparison = compare_images(baseline, after_clear)
    if comparison["exact_match"]:
        status = "restored"
    elif estimate["status"] == "estimated" and estimate["fill_fraction"] is not None:
        status = "not_restored" if estimate["fill_fraction"] < 1-tolerance_fraction else "inconclusive"
    elif comparison["changed_percent"] <= tolerance_fraction*100:
        status = "restored_within_pixel_tolerance"
    else:
        status = "inconclusive"
    return {"status":status, "tolerance_fraction":tolerance_fraction, "changed_percent":comparison["changed_percent"],
            "baseline_comparison":comparison, "fill_estimate":estimate,
            "note":"Визуальная оценка; не прямое чтение внутреннего счётчика игры."}

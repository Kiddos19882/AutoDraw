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

def evaluate_board_clear(blank_reference: Image.Image, after_clear: Image.Image, *, tolerance_percent: float = 0.15) -> dict[str, Any]:
    """Compare a post-clear board to a separately captured, known-empty reference.

    A before/after comparison alone cannot prove that a board is empty. This helper
    only returns a restored status when the post-clear ROI matches an explicit blank-board
    reference within the configured pixel tolerance. It never captures the reference
    or clicks Clear itself.
    """
    if not isinstance(blank_reference, Image.Image) or not isinstance(after_clear, Image.Image):
        raise ValueError("Для проверки очистки нужны эталон пустой доски и текущий снимок.")
    if blank_reference.size != after_clear.size:
        raise ValueError(
            f"Размеры эталона пустой доски и текущего снимка различаются: "
            f"{blank_reference.size} и {after_clear.size}."
        )
    if not 0 <= tolerance_percent <= 5:
        raise ValueError("Допуск сравнения доски должен быть от 0 до 5 процентов.")
    comparison = compare_images(blank_reference, after_clear)
    changed_percent = float(comparison["changed_percent"])
    if comparison["exact_match"]:
        status = "restored"
    elif changed_percent <= tolerance_percent:
        status = "restored_within_pixel_tolerance"
    else:
        status = "not_restored"
    return {
        "status": status,
        "tolerance_percent": tolerance_percent,
        "changed_percent": changed_percent,
        "comparison": comparison,
        "reference_type": "explicit_blank_board_roi",
        "note": "Визуальное совпадение с отдельно сохранённым эталоном пустой доски; это не доказательство внутреннего состояния игры.",
    }


def measure_stroke_visibility(
    blank_reference: Image.Image,
    current: Image.Image,
    strokes: list[dict[str, Any]],
    *,
    padding_px: int = 4,
    color_distance_threshold: float = 24.0,
    minimum_changed_pixels: int = 2,
) -> dict[str, Any]:
    """Measure visual changes in per-stroke bounding boxes against a blank-board ROI.

    Stroke coordinates are local to the supplied board ROI. This is a visual heuristic,
    not proof that the game accepted a stroke. Overlapping padded ROIs are explicitly
    marked ambiguous because neighboring marks may contaminate the result.
    """
    import math

    if not isinstance(blank_reference, Image.Image) or not isinstance(current, Image.Image):
        raise ValueError("Для анализа штрихов нужны эталон пустой доски и снимок после рисования.")
    if blank_reference.size != current.size:
        raise ValueError(f"Размеры доски различаются: {blank_reference.size} и {current.size}.")
    if not isinstance(strokes, list):
        raise ValueError("Список штрихов должен быть массивом.")
    if padding_px < 0 or color_distance_threshold <= 0 or minimum_changed_pixels < 1:
        raise ValueError("Некорректные параметры обнаружения штрихов.")

    baseline = blank_reference.convert("RGB")
    observed = current.convert("RGB")
    width, height = baseline.size
    changed = Image.new("L", baseline.size, 0)
    base_pixels, current_pixels = baseline.load(), observed.load()
    changed_pixels = changed.load()
    for y in range(height):
        for x in range(width):
            a, b = base_pixels[x, y], current_pixels[x, y]
            distance = math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)))
            if distance > color_distance_threshold:
                changed_pixels[x, y] = 255

    regions: list[tuple[int, int, int, int]] = []
    normalized: list[dict[str, Any]] = []
    for index, stroke in enumerate(strokes):
        if not isinstance(stroke, dict):
            raise ValueError(f"Штрих {index} имеет неверный формат.")
        points = stroke.get("points")
        if not isinstance(points, list) or not points:
            raise ValueError(f"У штриха {index} нет точек.")
        coordinates: list[tuple[float, float]] = []
        for point in points:
            try:
                if isinstance(point, dict):
                    x, y = float(point["x"]), float(point["y"])
                else:
                    x, y = float(point[0]), float(point[1])
            except (KeyError, TypeError, ValueError, IndexError, OverflowError) as exc:
                raise ValueError(f"У штриха {index} некорректная точка.") from exc
            if not math.isfinite(x) or not math.isfinite(y):
                raise ValueError(f"У штриха {index} неконечная координата.")
            coordinates.append((x, y))
        x0 = max(0, math.floor(min(p[0] for p in coordinates)) - padding_px)
        y0 = max(0, math.floor(min(p[1] for p in coordinates)) - padding_px)
        x1 = min(width, math.ceil(max(p[0] for p in coordinates)) + padding_px + 1)
        y1 = min(height, math.ceil(max(p[1] for p in coordinates)) + padding_px + 1)
        if x0 >= x1 or y0 >= y1:
            raise ValueError(f"ROI штриха {index} находится за пределами снимка.")
        regions.append((x0, y0, x1, y1))
        normalized.append({"name": str(stroke.get("name", f"stroke_{index + 1}")), "roi": (x0, y0, x1, y1)})

    results: list[dict[str, Any]] = []
    for index, item in enumerate(normalized):
        x0, y0, x1, y1 = item["roi"]
        changed_count = sum(
            1 for y in range(y0, y1) for x in range(x0, x1)
            if changed_pixels[x, y] != 0
        )
        overlaps = []
        for other_index, (ox0, oy0, ox1, oy1) in enumerate(regions):
            if other_index == index:
                continue
            if x0 < ox1 and ox0 < x1 and y0 < oy1 and oy0 < y1:
                overlaps.append(other_index)
        if overlaps:
            status = "ambiguous_overlap"
        elif changed_count >= minimum_changed_pixels:
            status = "visible_change_detected"
        else:
            status = "no_change_detected"
        results.append({
            "name": item["name"],
            "status": status,
            "changed_pixels_in_roi": changed_count,
            "roi": {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0},
            "overlapping_stroke_indices": overlaps,
            "interpretation": "visual_roi_heuristic_not_game_acceptance",
        })

    return {
        "status": "analyzed",
        "stroke_count": len(results),
        "visible_change_count": sum(r["status"] == "visible_change_detected" for r in results),
        "no_change_count": sum(r["status"] == "no_change_detected" for r in results),
        "ambiguous_count": sum(r["status"] == "ambiguous_overlap" for r in results),
        "results": results,
        "note": "ROI могут включать эффекты кисти и фон; пересекающиеся ROI помечаются неоднозначными.",
    }

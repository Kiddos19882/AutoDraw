from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

import numpy as np
from PIL import Image

QUANTIZATION_SCHEMA_VERSION = 1
MAX_PALETTE_COLORS = 512
MAX_IMAGE_PIXELS = 40_000_000
MAX_DISTANCE_COMPARISONS = 300_000_000


class PaletteQuantizationError(ValueError):
    """Raised when an image or browser palette cannot be quantized safely."""


@dataclass(slots=True)
class PaletteQuantizationResult:
    image: Image.Image
    index_map: np.ndarray
    report: dict[str, Any]


@dataclass(slots=True)
class BackgroundRemovalResult:
    image: Image.Image
    removed_mask: np.ndarray
    report: dict[str, Any]


def _parse_rgb(raw: Any, index: int) -> tuple[int, int, int]:
    if isinstance(raw, dict):
        if "rgb" in raw:
            rgb_raw = raw["rgb"]
        elif "hex" in raw:
            value = str(raw["hex"]).strip().lstrip("#")
            if len(value) != 6:
                raise PaletteQuantizationError(f"HEX цвета №{index} должен содержать 6 шестнадцатеричных символов.")
            try:
                return tuple(int(value[pos:pos + 2], 16) for pos in (0, 2, 4))  # type: ignore[return-value]
            except ValueError as exc:
                raise PaletteQuantizationError(f"Некорректный HEX цвета №{index}.") from exc
        else:
            raise PaletteQuantizationError(f"Для цвета №{index} нужны поля rgb или hex.")
    else:
        rgb_raw = raw
    if not isinstance(rgb_raw, (list, tuple)) or len(rgb_raw) != 3:
        raise PaletteQuantizationError(f"RGB цвета №{index} должен содержать три компонента.")
    values: list[int] = []
    for value in rgb_raw:
        if isinstance(value, bool):
            raise PaletteQuantizationError(f"RGB цвета №{index} содержит недопустимое значение.")
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise PaletteQuantizationError(f"RGB цвета №{index} содержит нечисловой компонент.") from exc
        if number < 0 or number > 255 or number != value:
            raise PaletteQuantizationError(f"Компоненты RGB цвета №{index} должны быть целыми числами от 0 до 255.")
        values.append(number)
    return tuple(values)  # type: ignore[return-value]


def normalize_palette(colors: Iterable[dict[str, Any] | list[int] | tuple[int, int, int]]) -> list[dict[str, Any]]:
    """Validate palette entries, normalize color values and reject duplicate RGB colors."""
    if isinstance(colors, (str, bytes, dict)):
        raise PaletteQuantizationError("Палитра должна быть списком цветов.")
    try:
        raw_items = list(colors)
    except TypeError as exc:
        raise PaletteQuantizationError("Палитра должна быть списком цветов.") from exc
    if not raw_items:
        raise PaletteQuantizationError("Палитра пуста. Сначала загрузите профиль палитры браузера.")
    if len(raw_items) > MAX_PALETTE_COLORS:
        raise PaletteQuantizationError(f"Слишком много цветов: максимум {MAX_PALETTE_COLORS}.")

    normalized: list[dict[str, Any]] = []
    seen: set[tuple[int, int, int]] = set()
    for index, raw in enumerate(raw_items, start=1):
        rgb = _parse_rgb(raw, index)
        if isinstance(raw, dict) and raw.get("hex") is not None:
            hex_value = str(raw["hex"]).strip().lstrip("#")
            if len(hex_value) != 6:
                raise PaletteQuantizationError(f"HEX цвета №{index} должен содержать 6 шестнадцатеричных символов.")
            try:
                from_hex = tuple(int(hex_value[pos:pos + 2], 16) for pos in (0, 2, 4))
            except ValueError as exc:
                raise PaletteQuantizationError(f"Некорректный HEX цвета №{index}.") from exc
            if from_hex != rgb:
                raise PaletteQuantizationError(f"RGB и HEX цвета №{index} не совпадают.")
        if rgb in seen:
            raise PaletteQuantizationError(f"Цвет #{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X} повторяется в палитре.")
        seen.add(rgb)
        if isinstance(raw, dict):
            name = str(raw.get("name") or f"Цвет {index}").strip()
            color_id = str(raw.get("id") or f"color-{index}")
        else:
            name = f"Цвет {index}"
            color_id = f"color-{index}"
        normalized.append({
            "index": index - 1,
            "id": color_id,
            "name": name,
            "rgb": list(rgb),
            "hex": "#" + "".join(f"{channel:02X}" for channel in rgb),
        })
    return normalized


def rgb_to_lab(rgb: np.ndarray | Iterable[float]) -> np.ndarray:
    """Convert sRGB values (0..255) to CIELAB using the D65 reference white."""
    values = np.asarray(rgb, dtype=np.float64)
    if values.shape[-1] != 3:
        raise ValueError("RGB array must have a final dimension of 3.")
    srgb = np.clip(values / 255.0, 0.0, 1.0)
    linear = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
    matrix = np.array([
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ], dtype=np.float64)
    xyz = linear @ matrix.T
    xyz = xyz / np.array([0.95047, 1.0, 1.08883], dtype=np.float64)
    delta = 6 / 29
    threshold = delta ** 3
    f_xyz = np.where(xyz > threshold, np.cbrt(xyz), xyz / (3 * delta * delta) + 4 / 29)
    fx, fy, fz = f_xyz[..., 0], f_xyz[..., 1], f_xyz[..., 2]
    return np.stack((116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)), axis=-1)


def delta_e_ciede2000(lab1: np.ndarray | Iterable[float], lab2: np.ndarray | Iterable[float]) -> np.ndarray:
    """Compute CIEDE2000 color difference; NumPy broadcasting is supported."""
    first = np.asarray(lab1, dtype=np.float64)
    second = np.asarray(lab2, dtype=np.float64)
    if first.shape[-1] != 3 or second.shape[-1] != 3:
        raise ValueError("Lab arrays must have a final dimension of 3.")
    L1, a1, b1 = first[..., 0], first[..., 1], first[..., 2]
    L2, a2, b2 = second[..., 0], second[..., 1], second[..., 2]

    C1 = np.sqrt(a1 * a1 + b1 * b1)
    C2 = np.sqrt(a2 * a2 + b2 * b2)
    C_bar = (C1 + C2) / 2
    C_bar_7 = C_bar ** 7
    G = 0.5 * (1 - np.sqrt(C_bar_7 / (C_bar_7 + 25.0 ** 7)))
    a1p = (1 + G) * a1
    a2p = (1 + G) * a2
    C1p = np.sqrt(a1p * a1p + b1 * b1)
    C2p = np.sqrt(a2p * a2p + b2 * b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360

    dLp = L2 - L1
    dCp = C2p - C1p
    product = C1p * C2p
    raw_dh = h2p - h1p
    dhp = np.where(raw_dh > 180, raw_dh - 360, raw_dh)
    dhp = np.where(dhp < -180, dhp + 360, dhp)
    dhp = np.where(product == 0, 0.0, dhp)
    dHp = 2 * np.sqrt(product) * np.sin(np.radians(dhp / 2))

    L_bar_p = (L1 + L2) / 2
    C_bar_p = (C1p + C2p) / 2
    sum_h = h1p + h2p
    abs_h_diff = np.abs(h1p - h2p)
    h_bar_p = np.where(
        product == 0,
        sum_h,
        np.where(
            abs_h_diff <= 180,
            sum_h / 2,
            np.where(sum_h < 360, (sum_h + 360) / 2, (sum_h - 360) / 2),
        ),
    )

    T = (
        1
        - 0.17 * np.cos(np.radians(h_bar_p - 30))
        + 0.24 * np.cos(np.radians(2 * h_bar_p))
        + 0.32 * np.cos(np.radians(3 * h_bar_p + 6))
        - 0.20 * np.cos(np.radians(4 * h_bar_p - 63))
    )
    delta_theta = 30 * np.exp(-(((h_bar_p - 275) / 25) ** 2))
    C_bar_p_7 = C_bar_p ** 7
    R_C = 2 * np.sqrt(C_bar_p_7 / (C_bar_p_7 + 25.0 ** 7))
    S_L = 1 + (0.015 * ((L_bar_p - 50) ** 2)) / np.sqrt(20 + ((L_bar_p - 50) ** 2))
    S_C = 1 + 0.045 * C_bar_p
    S_H = 1 + 0.015 * C_bar_p * T
    R_T = -np.sin(np.radians(2 * delta_theta)) * R_C

    l_term = dLp / S_L
    c_term = dCp / S_C
    h_term = dHp / S_H
    result_sq = l_term * l_term + c_term * c_term + h_term * h_term + R_T * c_term * h_term
    return np.sqrt(np.maximum(result_sq, 0.0))


def _extract_palette_colors(palette: Any) -> list[dict[str, Any]]:
    if isinstance(palette, dict):
        # Accept either a profile document, legacy palette document, or raw list under "colors".
        palette = palette.get("colors")
    return normalize_palette(palette or [])


def remove_edge_connected_background(
    image: Image.Image,
    *,
    background_rgb: tuple[int, int, int] = (255, 255, 255),
    tolerance: int = 24,
) -> BackgroundRemovalResult:
    """Make near-background pixels transparent only when connected to image edges.

    This is intended for a white or near-white canvas around a foreground figure.
    It intentionally does not remove every white pixel: enclosed white details
    (for example, an eye inside a dark outline) remain opaque unless they connect
    to the outer image edge through other matching pixels.

    `tolerance` is a per-channel RGB tolerance, not a perceptual color distance.
    Existing transparent pixels remain transparent. The input image is never modified.
    """
    if not isinstance(image, Image.Image):
        raise PaletteQuantizationError("Источник должен быть изображением Pillow.")
    if image.width <= 0 or image.height <= 0:
        raise PaletteQuantizationError("Размер изображения должен быть положительным.")
    if image.width * image.height > MAX_IMAGE_PIXELS:
        raise PaletteQuantizationError(f"Изображение слишком большое: максимум {MAX_IMAGE_PIXELS:,} пикселей.")
    if isinstance(tolerance, bool) or not isinstance(tolerance, int) or not 0 <= tolerance <= 255:
        raise PaletteQuantizationError("Допуск фона должен быть целым числом от 0 до 255.")
    if (
        not isinstance(background_rgb, (list, tuple))
        or len(background_rgb) != 3
        or any(isinstance(value, bool) or not isinstance(value, (int, np.integer)) or not 0 <= int(value) <= 255
               for value in background_rgb)
    ):
        raise PaletteQuantizationError("Цвет фона должен состоять из трёх целых RGB-компонентов от 0 до 255.")

    try:
        import cv2
    except ImportError as exc:
        raise PaletteQuantizationError("Для удаления фона требуется OpenCV. Установите зависимости из requirements-runtime.txt.") from exc

    rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8).copy()
    rgb = rgba[..., :3].astype(np.int16)
    alpha = rgba[..., 3]
    target = np.asarray(background_rgb, dtype=np.int16).reshape(1, 1, 3)
    near_background = np.max(np.abs(rgb - target), axis=2) <= tolerance
    candidate = near_background & (alpha > 0)

    try:
        # Four-connectivity avoids treating diagonal corner-touching pixels as
        # connected, which helps preserve thin diagonal foreground contours.
        _label_count, labels = cv2.connectedComponents(
            np.ascontiguousarray(candidate.astype(np.uint8)), connectivity=4
        )
    except (cv2.error, MemoryError) as exc:
        raise PaletteQuantizationError(f"Не удалось определить связные области фона: {exc}") from exc

    edge_labels = np.unique(np.concatenate((labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1])))
    edge_labels = edge_labels[edge_labels != 0]
    if edge_labels.size:
        removed = np.isin(labels, edge_labels) & candidate
    else:
        removed = np.zeros(candidate.shape, dtype=bool)

    rgba[..., 3][removed] = 0
    output = Image.fromarray(rgba, mode="RGBA")
    report = {
        "method": "edge_connected_rgb_tolerance",
        "background_rgb": [int(value) for value in background_rgb],
        "background_hex": "#" + "".join(f"{int(value):02X}" for value in background_rgb),
        "tolerance_per_rgb_channel": tolerance,
        "connectivity": 4,
        "candidate_pixel_count": int(candidate.sum()),
        "removed_pixel_count": int(removed.sum()),
        "preserves_enclosed_background_color": True,
        "note": "Удалены только подходящие по RGB-допуску пиксели, связанные с краем изображения.",
    }
    return BackgroundRemovalResult(output, removed, report)


def quantize_image_to_palette(
    image: Image.Image,
    palette: Any,
    *,
    chunk_pixels: int = 8192,
) -> PaletteQuantizationResult:
    """Map every visible source pixel to its nearest palette color using CIEDE2000.

    The original dimensions and alpha channel are retained. No dithering or spatial
    filtering is applied, so pixel geometry and isolated details are not spread or
    removed. Transparent pixels remain transparent and are excluded from distance stats.
    """
    if not isinstance(image, Image.Image):
        raise PaletteQuantizationError("Источник должен быть изображением Pillow.")
    if image.width <= 0 or image.height <= 0:
        raise PaletteQuantizationError("Размер изображения должен быть положительным.")
    pixel_count = image.width * image.height
    if pixel_count > MAX_IMAGE_PIXELS:
        raise PaletteQuantizationError(f"Изображение слишком большое: максимум {MAX_IMAGE_PIXELS:,} пикселей.")
    if isinstance(chunk_pixels, bool) or not isinstance(chunk_pixels, int) or chunk_pixels < 1:
        raise PaletteQuantizationError("Размер блока должен быть положительным целым числом.")

    normalized = _extract_palette_colors(palette)
    palette_rgb = np.asarray([entry["rgb"] for entry in normalized], dtype=np.uint8)
    palette_lab = rgb_to_lab(palette_rgb)
    alpha_present = "A" in image.getbands() or "transparency" in image.info
    source_mode = "RGBA" if alpha_present else "RGB"
    converted = image.convert(source_mode)
    source_arr = np.asarray(converted, dtype=np.uint8)
    source_rgb = source_arr[..., :3]
    alpha = source_arr[..., 3].copy() if alpha_present else None
    flat_rgb = source_rgb.reshape(-1, 3)
    active = np.ones(pixel_count, dtype=bool) if alpha is None else alpha.reshape(-1) > 0
    active_indices = np.flatnonzero(active)
    if active_indices.size and active_indices.size * len(normalized) > MAX_DISTANCE_COMPARISONS:
        raise PaletteQuantizationError(
            "Слишком много сравнений цветов для безопасной обработки. "
            "Используйте подготовленное изображение меньшего размера или палитру с меньшим числом цветов."
        )
    if active_indices.size == 0:
        empty_index = np.full((image.height, image.width), -1, dtype=np.int32)
        report = _make_report(normalized, image.size, empty_index, np.array([], dtype=np.float64), 0, 0, pixel_count)
        output = Image.fromarray(source_arr.copy(), mode=source_mode)
        return PaletteQuantizationResult(output, empty_index, report)

    output_rgb = flat_rgb.copy()
    index_map = np.full(pixel_count, -1, dtype=np.int32)
    distances = np.full(pixel_count, np.nan, dtype=np.float32)
    # Keep distance matrix and its intermediate arrays to a manageable size.
    block_size = min(chunk_pixels, max(1, 750_000 // len(normalized)))
    for start in range(0, active_indices.size, block_size):
        chosen_source_indexes = active_indices[start:start + block_size]
        rgb_block = flat_rgb[chosen_source_indexes]
        lab_block = rgb_to_lab(rgb_block)
        distances_matrix = delta_e_ciede2000(lab_block[:, None, :], palette_lab[None, :, :])
        nearest = np.argmin(distances_matrix, axis=1)
        nearest_distance = distances_matrix[np.arange(len(nearest)), nearest]
        output_rgb[chosen_source_indexes] = palette_rgb[nearest]
        index_map[chosen_source_indexes] = nearest.astype(np.int32)
        distances[chosen_source_indexes] = nearest_distance.astype(np.float32)

    output_rgb = output_rgb.reshape(image.height, image.width, 3)
    if alpha is not None:
        output_rgba = np.dstack((output_rgb, alpha))
        output_image = Image.fromarray(output_rgba.astype(np.uint8), mode="RGBA")
    else:
        output_image = Image.fromarray(output_rgb.astype(np.uint8), mode="RGB")
    index_map_2d = index_map.reshape(image.height, image.width)
    active_distances = distances[active]
    changed = np.any(flat_rgb[active] != output_rgb.reshape(-1, 3)[active], axis=1)
    report = _make_report(
        normalized,
        image.size,
        index_map_2d,
        active_distances,
        int(active_indices.size),
        int(changed.sum()),
        int((~active).sum()),
    )
    return PaletteQuantizationResult(output_image, index_map_2d, report)




def _count_scanline_runs(index_map: np.ndarray) -> int:
    """Count draw runs using the same adjacent-index rule as the color scanline planner."""
    indexes = np.asarray(index_map)
    total = 0
    for row in indexes:
        valid = row >= 0
        if not bool(np.any(valid)):
            continue
        starts = valid.copy()
        if row.size > 1:
            starts[1:] &= (~valid[:-1]) | (row[1:] != row[:-1])
        total += int(np.count_nonzero(starts))
    return total


def merge_rare_palette_colors(
    result: PaletteQuantizationResult,
    palette: Any,
    *,
    min_pixel_count: int = 20,
    min_percentage: float = 0.05,
    max_delta_e: float = 8.0,
    min_frequency_ratio: float = 2.0,
) -> tuple[PaletteQuantizationResult, dict[str, Any]]:
    """Merge infrequent mapped palette colors into similar, more frequent colors.

    A used color is considered rare when its count is at most ``min_pixel_count``
    OR its share of visible pixels is below ``min_percentage``. A target must be
    non-rare, used by at least ``min_frequency_ratio`` times as many pixels, and
    within ``max_delta_e`` CIEDE2000 units of the source palette color. Colors with
    no sufficiently similar target are preserved. Transparent index -1 is never
    changed. Palette order is not changed; only the pixel indices and matching
    report are updated.

    The operation is deliberately conservative by default. It can merge tiny
    colored speckles and reduce scanline fragments, but does not remove colors
    merely because they are rare when the nearest abundant color is too different.
    """
    if not isinstance(result, PaletteQuantizationResult):
        raise PaletteQuantizationError("Результат преобразования имеет неверный тип.")
    if isinstance(min_pixel_count, bool) or not isinstance(min_pixel_count, int) or min_pixel_count < 0:
        raise PaletteQuantizationError("Минимальное число пикселей должно быть целым числом не меньше 0.")
    if isinstance(min_percentage, bool) or not isinstance(min_percentage, (int, float)):
        raise PaletteQuantizationError("Порог доли цвета должен быть числом от 0 до 100.")
    if not np.isfinite(min_percentage) or not 0 <= float(min_percentage) <= 100:
        raise PaletteQuantizationError("Порог доли цвета должен быть числом от 0 до 100.")
    if isinstance(max_delta_e, bool) or not isinstance(max_delta_e, (int, float)):
        raise PaletteQuantizationError("Максимальное цветовое отличие должно быть числом от 0 до 100.")
    if not np.isfinite(max_delta_e) or not 0 <= float(max_delta_e) <= 100:
        raise PaletteQuantizationError("Максимальное цветовое отличие должно быть числом от 0 до 100.")
    if isinstance(min_frequency_ratio, bool) or not isinstance(min_frequency_ratio, (int, float)):
        raise PaletteQuantizationError("Коэффициент частоты должен быть числом от 1 до 1000.")
    if not np.isfinite(min_frequency_ratio) or not 1 <= float(min_frequency_ratio) <= 1000:
        raise PaletteQuantizationError("Коэффициент частоты должен быть числом от 1 до 1000.")

    normalized = _extract_palette_colors(palette)
    index_map_before = np.asarray(result.index_map)
    if index_map_before.ndim != 2 or index_map_before.shape != (result.image.height, result.image.width):
        raise PaletteQuantizationError("Карта цветов не соответствует размеру преобразованного изображения.")
    if index_map_before.dtype.kind not in "iu":
        raise PaletteQuantizationError("Индексы цветов должны быть целыми числами.")
    if index_map_before.size and (int(index_map_before.min()) < -1 or int(index_map_before.max()) >= len(normalized)):
        raise PaletteQuantizationError("Карта цветов содержит индекс вне палитры.")

    indexes = index_map_before.astype(np.int32, copy=True)
    visible_mask = indexes >= 0
    visible_count = int(np.count_nonzero(visible_mask))
    counts = np.bincount(indexes[visible_mask], minlength=len(normalized)).astype(np.int64)
    percentages = counts.astype(np.float64) * (100.0 / visible_count) if visible_count else np.zeros(len(normalized))
    before_strokes = _count_scanline_runs(indexes)
    used_indexes = [i for i, count in enumerate(counts) if count > 0]

    def is_rare(color_index: int) -> bool:
        return int(counts[color_index]) <= min_pixel_count or float(percentages[color_index]) < float(min_percentage)

    rare_indexes = [i for i in used_indexes if is_rare(i)]
    common_targets = [i for i in used_indexes if not is_rare(i)]
    palette_rgb = np.asarray([entry["rgb"] for entry in normalized], dtype=np.uint8)
    palette_lab = rgb_to_lab(palette_rgb)
    mapping: dict[int, int] = {}
    color_distances: dict[tuple[int, int], float] = {}

    for source_index in sorted(rare_indexes, key=lambda i: (int(counts[i]), i)):
        source_count = int(counts[source_index])
        eligible_targets = [
            target_index for target_index in common_targets
            if target_index != source_index
            and int(counts[target_index]) >= max(source_count + 1, int(np.ceil(source_count * float(min_frequency_ratio))))
        ]
        if not eligible_targets:
            continue
        distances = delta_e_ciede2000(
            palette_lab[source_index],
            palette_lab[np.asarray(eligible_targets, dtype=np.int32)],
        )
        nearest_position = int(np.argmin(distances))
        target_index = eligible_targets[nearest_position]
        difference = float(distances[nearest_position])
        if difference <= float(max_delta_e):
            mapping[source_index] = target_index
            color_distances[(source_index, target_index)] = difference

    # Build one index remap table and apply it in a single vectorized pass instead
    # of scanning the entire image once for every rare color.
    index_remap = np.arange(len(normalized), dtype=np.int32)
    for source_index, target_index in mapping.items():
        index_remap[source_index] = target_index
    updated_indexes = indexes.copy()
    valid_before = updated_indexes >= 0
    updated_indexes[valid_before] = index_remap[updated_indexes[valid_before]]
    mapping_reports: list[dict[str, Any]] = []
    moved_pixels = 0
    weighted_delta_sum = 0.0
    max_merge_delta = 0.0
    for source_index, target_index in mapping.items():
        pixel_count = int(counts[source_index])
        source = normalized[source_index]
        target = normalized[target_index]
        difference = color_distances[(source_index, target_index)]
        moved_pixels += pixel_count
        weighted_delta_sum += difference * pixel_count
        max_merge_delta = max(max_merge_delta, difference)
        mapping_reports.append({
            "source_index": source_index,
            "source_id": source["id"],
            "source_name": source["name"],
            "source_hex": source["hex"],
            "source_pixel_count": pixel_count,
            "source_percentage_visible": round(float(percentages[source_index]), 6),
            "target_index": target_index,
            "target_id": target["id"],
            "target_name": target["name"],
            "target_hex": target["hex"],
            "target_pixel_count_before_merge": int(counts[target_index]),
            "delta_e_2000": round(difference, 6),
        })

    after_strokes = _count_scanline_runs(updated_indexes)
    new_counts = np.bincount(updated_indexes[updated_indexes >= 0], minlength=len(normalized)).astype(np.int64)
    visible_after = int(np.count_nonzero(updated_indexes >= 0))
    palette_counts: list[dict[str, Any]] = []
    for entry in normalized:
        count = int(new_counts[int(entry["index"])])
        palette_counts.append({
            **entry,
            "pixel_count": count,
            "percentage_visible": round(100.0 * count / visible_after, 4) if visible_after else 0.0,
        })
    used_colors = [entry for entry in palette_counts if entry["pixel_count"] > 0]

    rgba = np.asarray(result.image.convert("RGBA"), dtype=np.uint8).copy()
    # Rewrite only remapped pixel colors. This stays proportional to the number of
    # pixels affected by the optimization rather than the entire canvas.
    changed_mask = updated_indexes != indexes
    if bool(np.any(changed_mask)):
        rgba[..., :3][changed_mask] = palette_rgb[updated_indexes[changed_mask]]
    has_alpha = "A" in result.image.getbands() or bool(np.any(updated_indexes < 0))
    output_image = Image.fromarray(rgba, mode="RGBA") if has_alpha else Image.fromarray(rgba[..., :3].copy(), mode="RGB")

    stroke_reduction = before_strokes - after_strokes
    merge_report: dict[str, Any] = {
        "enabled": True,
        "method": "frequency_weighted_nearest_palette_color_ciede2000",
        "min_pixel_count": int(min_pixel_count),
        "min_percentage": float(min_percentage),
        "max_delta_e_2000": float(max_delta_e),
        "min_frequency_ratio": float(min_frequency_ratio),
        "visible_pixel_count": visible_count,
        "used_color_count_before": len(used_indexes),
        "used_color_count_after": len(used_colors),
        "rare_color_count_detected": len(rare_indexes),
        "rare_color_count_merged": len(mapping),
        "remapped_pixel_count": moved_pixels,
        "estimated_scanline_strokes_before": before_strokes,
        "estimated_scanline_strokes_after": after_strokes,
        "estimated_scanline_strokes_reduced": stroke_reduction,
        "estimated_scanline_stroke_reduction_percentage": round(100.0 * stroke_reduction / before_strokes, 4) if before_strokes else 0.0,
        "mean_delta_e_2000_for_merged_colors": round(weighted_delta_sum / moved_pixels, 6) if moved_pixels else 0.0,
        "max_delta_e_2000_for_merged_colors": round(max_merge_delta, 6),
        "mappings": mapping_reports,
        "note": (
            "Цвет считался редким, если его доля меньше заданного процента ИЛИ число пикселей не больше заданного минимума. "
            "Он объединялся только с не-редким цветом, который встречается чаще в заданное число раз, "
            "и если CIEDE2000 не превышает максимальный допуск. Прозрачные пиксели не изменяются."
        ),
    }

    # Keep existing conversion/background/profile metadata, update only palette usage
    # and add an explicit note that original quantization distances are pre-merge metrics.
    updated_report = dict(result.report)
    updated_report.update({
        "palette": palette_counts,
        "used_colors": used_colors,
        "used_palette_color_count": len(used_colors),
        "unused_palette_color_count": len(normalized) - len(used_colors),
        "rare_color_merge": merge_report,
        "distance_metrics_scope": (
            "mean/p95/p99/max_delta_e_2000 describe initial nearest-palette quantization. "
            "Additional change introduced by rare-color merging is reported separately under rare_color_merge."
        ),
    })
    result.image = output_image
    result.index_map = updated_indexes
    result.report = updated_report
    return result, merge_report

def remove_white_palette_pixels(
    result: PaletteQuantizationResult,
    palette: Any,
    source_image: Image.Image,
    *,
    tolerance: int = 24,
    threshold_percentage: float | None = None,
) -> tuple[PaletteQuantizationResult, dict[str, Any]]:
    """Make all near-white palette-mapped pixels transparent.

    `threshold_percentage=None` always removes matching white palette pixels.
    Otherwise removal occurs only when their share of currently visible pixels is
    strictly greater than the supplied threshold. The percentage is measured after
    palette quantization, before removal, and excludes pixels that were already
    transparent in the source.

    White is defined by every RGB channel being within `tolerance` of 255. The
    index map is updated to -1 for removed pixels, so the color scanline planner
    skips them rather than drawing white.
    """
    if not isinstance(result, PaletteQuantizationResult):
        raise PaletteQuantizationError("Результат преобразования имеет неверный тип.")
    if not isinstance(source_image, Image.Image):
        raise PaletteQuantizationError("Исходное изображение для удаления белого цвета не задано.")
    if source_image.size != result.image.size:
        raise PaletteQuantizationError("Исходное изображение и результат преобразования должны иметь одинаковый размер.")
    if isinstance(tolerance, bool) or not isinstance(tolerance, int) or not 0 <= tolerance <= 255:
        raise PaletteQuantizationError("Допуск белого цвета должен быть целым числом от 0 до 255.")
    if threshold_percentage is not None:
        if isinstance(threshold_percentage, bool) or not isinstance(threshold_percentage, (int, float)):
            raise PaletteQuantizationError("Порог процента белого должен быть числом от 0 до 100.")
        if not np.isfinite(threshold_percentage) or not 0 <= float(threshold_percentage) <= 100:
            raise PaletteQuantizationError("Порог процента белого должен быть числом от 0 до 100.")

    normalized = _extract_palette_colors(palette)
    white_entries = [
        entry for entry in normalized
        if all(255 - int(channel) <= tolerance for channel in entry["rgb"])
    ]
    white_indexes = {int(entry["index"]) for entry in white_entries}
    index_map_before = np.asarray(result.index_map)
    if index_map_before.ndim != 2 or index_map_before.shape != (result.image.height, result.image.width):
        raise PaletteQuantizationError("Карта цветов не соответствует размеру преобразованного изображения.")

    visible_before_mask = index_map_before >= 0
    visible_before_count = int(np.count_nonzero(visible_before_mask))
    if white_indexes:
        white_mask = np.isin(index_map_before, np.asarray(sorted(white_indexes), dtype=index_map_before.dtype)) & visible_before_mask
    else:
        white_mask = np.zeros(index_map_before.shape, dtype=bool)
    white_count = int(np.count_nonzero(white_mask))
    white_percentage = (100.0 * white_count / visible_before_count) if visible_before_count else 0.0
    should_remove = threshold_percentage is None or white_percentage > float(threshold_percentage)
    removed_mask = white_mask if should_remove else np.zeros(white_mask.shape, dtype=bool)
    removed_count = int(np.count_nonzero(removed_mask))

    if threshold_percentage is None:
        mode = "remove_all_white_palette_pixels"
        decision = "removed_all_matching_white_pixels" if removed_count else "no_matching_white_pixels"
    elif should_remove:
        mode = "remove_if_white_percentage_exceeds_threshold"
        decision = "white_percentage_exceeded_threshold"
    else:
        mode = "remove_if_white_percentage_exceeds_threshold"
        decision = "white_percentage_did_not_exceed_threshold"

    removal_report: dict[str, Any] = {
        "enabled": True,
        "mode": mode,
        "applied": removed_count > 0,
        "white_palette_colors": [
            {"index": int(entry["index"]), "name": entry["name"], "hex": entry["hex"], "rgb": entry["rgb"]}
            for entry in white_entries
        ],
        "tolerance_per_rgb_channel": tolerance,
        "white_pixel_count_before_removal": white_count,
        "visible_pixel_count_before_removal": visible_before_count,
        "white_percentage_of_visible_pixels": round(white_percentage, 4),
        "threshold_percentage": float(threshold_percentage) if threshold_percentage is not None else None,
        "removed_pixel_count": removed_count,
        "decision": decision,
        "note": (
            "Доля белого считается среди видимых пикселей уже преобразованного изображения; "
            "удалённые пиксели получают альфа-канал 0 и индекс -1."
        ),
    }

    if removed_count == 0:
        # Keep image and index map unchanged when the threshold is not exceeded or
        # the selected palette has no near-white colors.
        result.report["white_color_removal"] = removal_report
        return result, removal_report

    rgba = np.asarray(result.image.convert("RGBA"), dtype=np.uint8).copy()
    rgba[removed_mask, 3] = 0
    updated_index_map = index_map_before.astype(np.int32, copy=True)
    updated_index_map[removed_mask] = -1

    # Recalculate color-match statistics for the pixels that remain drawable. Work
    # in chunks so this extra step does not require one large Lab array for the image.
    source_rgba = np.asarray(source_image.convert("RGBA"), dtype=np.uint8).reshape(-1, 4)
    output_rgba = rgba.reshape(-1, 4)
    remaining_indexes = np.flatnonzero(updated_index_map.reshape(-1) >= 0)
    distances = np.empty(remaining_indexes.size, dtype=np.float32)
    changed_count = 0
    chunk_size = 262_144
    for offset in range(0, remaining_indexes.size, chunk_size):
        selected = remaining_indexes[offset:offset + chunk_size]
        source_rgb = source_rgba[selected, :3]
        output_rgb = output_rgba[selected, :3]
        changed_count += int(np.count_nonzero(np.any(source_rgb != output_rgb, axis=1)))
        source_lab = rgb_to_lab(source_rgb)
        output_lab = rgb_to_lab(output_rgb)
        distances[offset:offset + selected.size] = delta_e_ciede2000(source_lab, output_lab).astype(np.float32)

    updated_report = _make_report(
        normalized,
        result.image.size,
        updated_index_map,
        distances,
        int(remaining_indexes.size),
        changed_count,
        int(updated_index_map.size - remaining_indexes.size),
    )
    updated_report["white_color_removal"] = removal_report
    result.image = Image.fromarray(rgba, mode="RGBA")
    result.index_map = updated_index_map
    result.report = updated_report
    return result, removal_report

def _make_report(
    palette: list[dict[str, Any]],
    size: tuple[int, int],
    index_map: np.ndarray,
    distances: np.ndarray,
    visible_pixels: int,
    changed_pixels: int,
    transparent_pixels: int,
) -> dict[str, Any]:
    palette_counts: list[dict[str, Any]] = []
    flat_indexes = index_map.reshape(-1)
    for entry in palette:
        count = int(np.count_nonzero(flat_indexes == entry["index"]))
        palette_counts.append({
            **entry,
            "pixel_count": count,
            "percentage_visible": round(100.0 * count / visible_pixels, 4) if visible_pixels else 0.0,
        })
    used = [entry for entry in palette_counts if entry["pixel_count"] > 0]
    values = np.asarray(distances, dtype=np.float64)
    values = values[np.isfinite(values)]
    if values.size:
        mean_delta = float(np.mean(values))
        max_delta = float(np.max(values))
        p95_delta = float(np.percentile(values, 95))
        p99_delta = float(np.percentile(values, 99))
        exact = int(np.count_nonzero(values <= 0.0001))
    else:
        mean_delta = max_delta = p95_delta = p99_delta = 0.0
        exact = 0
    return {
        "schema_version": QUANTIZATION_SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "algorithm": "CIELAB + CIEDE2000",
        "dithering": False,
        "source_size": {"width": int(size[0]), "height": int(size[1])},
        "palette_color_count": len(palette),
        "visible_pixel_count": int(visible_pixels),
        "transparent_pixel_count": int(transparent_pixels),
        "changed_pixel_count": int(changed_pixels),
        "changed_pixel_percentage": round(100.0 * changed_pixels / visible_pixels, 4) if visible_pixels else 0.0,
        "exact_color_pixel_count": exact,
        "mean_delta_e_2000": round(mean_delta, 6),
        "p95_delta_e_2000": round(p95_delta, 6),
        "p99_delta_e_2000": round(p99_delta, 6),
        "max_delta_e_2000": round(max_delta, 6),
        "used_palette_color_count": len(used),
        "unused_palette_color_count": len(palette) - len(used),
        "used_colors": used,
        "palette": palette_counts,
    }

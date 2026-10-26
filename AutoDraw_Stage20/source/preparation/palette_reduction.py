from __future__ import annotations

from typing import Any

import numpy as np

from palette_detection import parse_hex_color, rgb_to_hex


def _rgb_to_lab(rgb_values: np.ndarray) -> np.ndarray:
    """Convert sRGB samples to CIELAB/D65 coordinates."""
    values = np.asarray(rgb_values, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 3:
        raise ValueError("RGB палитры должен иметь форму N×3.")
    srgb = np.clip(values / 255.0, 0.0, 1.0)
    linear = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
    matrix = np.array([
        [0.4124564, 0.3575761, 0.1804375],
        [0.3575761, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ], dtype=np.float64)
    xyz = linear @ matrix.T
    xyz /= np.array([0.95047, 1.0, 1.08883], dtype=np.float64)
    delta = 6 / 29
    f_xyz = np.where(xyz > delta ** 3, np.cbrt(xyz), xyz / (3 * delta * delta) + 4 / 29)
    return np.stack((
        116 * f_xyz[:, 1] - 16,
        500 * (f_xyz[:, 0] - f_xyz[:, 1]),
        200 * (f_xyz[:, 1] - f_xyz[:, 2]),
    ), axis=1)


def select_representative_palette_colors(
    colors: list[dict[str, Any]],
    target_count: int = 32,
    *,
    max_iterations: int = 20,
    required_hex_colors: tuple[str, ...] = ("#FFFFFF", "#000000"),
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Choose representative real palette swatches without creating synthetic RGB values.

    Farthest-point seeding covers the palette's colour range, then Lloyd-style
    refinement moves each centre to the existing swatch nearest its cluster mean.
    Returned entries preserve original sample coordinates and metadata. Pure white and
    black are reserved by default when present, so clustering cannot replace them.
    """
    if not isinstance(colors, list):
        raise ValueError("Палитра должна быть списком цветов.")
    if isinstance(target_count, bool) or not isinstance(target_count, int) or not 1 <= target_count <= 512:
        raise ValueError("Количество основных цветов должно быть целым числом от 1 до 512.")
    if isinstance(max_iterations, bool) or not isinstance(max_iterations, int) or not 1 <= max_iterations <= 100:
        raise ValueError("Число итераций должно быть целым числом от 1 до 100.")
    if len(colors) > 4096:
        raise ValueError("Слишком большая палитра: максимум 4096 исходных образцов.")
    if not colors:
        raise ValueError("Палитра пуста.")

    entries: list[dict[str, Any]] = []
    rgbs: list[tuple[int, int, int]] = []
    seen: set[tuple[int, int, int]] = set()
    for index, raw in enumerate(colors, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"Цвет №{index} должен быть объектом.")
        if "rgb" not in raw:
            raise ValueError(f"Для цвета №{index} отсутствует RGB.")
        try:
            rgb = tuple(int(value) for value in raw["rgb"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"RGB цвета №{index} задан некорректно.") from exc
        if len(rgb) != 3 or any(value < 0 or value > 255 for value in rgb):
            raise ValueError(f"RGB цвета №{index} должен содержать три значения от 0 до 255.")
        if isinstance(raw.get("hex"), str) and parse_hex_color(raw["hex"]) != rgb:
            raise ValueError(f"RGB и HEX цвета №{index} не совпадают.")
        if rgb in seen:
            raise ValueError(f"Цвет {rgb_to_hex(rgb)} повторяется в исходной палитре.")
        seen.add(rgb)
        entries.append(dict(raw))
        rgbs.append(rgb)

    input_count = len(entries)
    output_count = min(target_count, input_count)
    hex_to_index = {rgb_to_hex(rgb): index for index, rgb in enumerate(rgbs)}
    normalized_required: list[str] = []
    for value in required_hex_colors:
        try:
            color_hex = rgb_to_hex(parse_hex_color(value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Обязательный цвет {value!r} не является допустимым HEX.") from exc
        if color_hex not in normalized_required:
            normalized_required.append(color_hex)
    required_indices = [
        hex_to_index[color_hex] for color_hex in normalized_required
        if color_hex in hex_to_index
    ]
    preserved_required_colors = [
        color_hex for color_hex in normalized_required if color_hex in hex_to_index
    ]
    missing_required_colors = [
        color_hex for color_hex in normalized_required if color_hex not in hex_to_index
    ]
    if len(required_indices) > output_count:
        raise ValueError(
            f"Нужно сохранить {len(required_indices)} обязательных цветов, но лимит равен {output_count}."
        )

    if input_count <= target_count:
        return entries, {
            "enabled": False,
            "method": "lab_farthest_point_plus_palette_medoid_refinement",
            "input_color_count": input_count,
            "output_color_count": input_count,
            "target_color_count": target_count,
            "removed_color_count": 0,
            "mean_delta_e76": 0.0,
            "max_delta_e76": 0.0,
            "clusters": [],
            "required_color_hexes": normalized_required,
            "preserved_required_colors": preserved_required_colors,
            "missing_required_colors": missing_required_colors,
            "note": f"Палитра уже содержит не более {target_count} цветов; исходный список сохранён.",
        }

    lab = _rgb_to_lab(np.asarray(rgbs, dtype=np.uint8))
    palette_size = len(entries)

    # Required colors are fixed medoids. Other medoids are selected for broad coverage.
    if required_indices:
        medoids = list(required_indices)
    else:
        first = int(np.argmin(np.sum((lab - lab.mean(axis=0)) ** 2, axis=1)))
        medoids = [first]
    seeded = set(medoids)
    nearest_sq = np.min(
        np.sum((lab[:, None, :] - lab[np.asarray(medoids, dtype=np.int32)][None, :, :]) ** 2, axis=2),
        axis=1,
    )
    while len(medoids) < output_count:
        nearest_sq[list(seeded)] = -1.0
        candidate = int(np.argmax(nearest_sq))
        if candidate in seeded:
            candidate = next(index for index in range(palette_size) if index not in seeded)
        medoids.append(candidate)
        seeded.add(candidate)
        new_sq = np.sum((lab - lab[candidate]) ** 2, axis=1)
        nearest_sq = np.minimum(nearest_sq, new_sq)

    fixed_required_indices = set(required_indices)

    def farthest_unused(used: set[int]) -> int:
        available = [index for index in range(palette_size) if index not in used]
        if not available:
            raise ValueError("Не удалось выбрать уникальные цвета-образцы.")
        if not used:
            return available[0]
        used_indexes = np.asarray(sorted(used), dtype=np.int32)
        available_indexes = np.asarray(available, dtype=np.int32)
        distances = np.sum((lab[available_indexes, None, :] - lab[used_indexes][None, :, :]) ** 2, axis=2)
        return int(available[int(np.argmax(np.min(distances, axis=1)))])

    for _iteration in range(max_iterations):
        centers = lab[np.asarray(medoids, dtype=np.int32)]
        distances = np.sum((lab[:, None, :] - centers[None, :, :]) ** 2, axis=2)
        labels = np.argmin(distances, axis=1)
        updated: list[int] = []
        used: set[int] = set(fixed_required_indices)

        for cluster_index in range(output_count):
            if cluster_index < len(required_indices):
                # These slots are reserved; clustering cannot replace white/black.
                updated.append(required_indices[cluster_index])
                continue

            members = np.flatnonzero(labels == cluster_index)
            if members.size:
                centroid = lab[members].mean(axis=0)
                candidate_distances = np.sum((lab[members] - centroid) ** 2, axis=1)
                order = np.argsort(candidate_distances, kind="stable")
                candidate = next(
                    (int(members[position]) for position in order if int(members[position]) not in used),
                    -1,
                )
                if candidate < 0:
                    candidate = farthest_unused(used)
            else:
                candidate = medoids[cluster_index] if medoids[cluster_index] not in used else farthest_unused(used)
            if candidate in used:
                candidate = farthest_unused(used)
            updated.append(candidate)
            used.add(candidate)
        if updated == medoids:
            break
        medoids = updated

    # Keep selected swatches in the original game's order for easier visual checking.
    selected_indices = sorted(set(medoids))
    used = set(selected_indices)
    while len(selected_indices) < output_count:
        candidate = farthest_unused(used)
        selected_indices.append(candidate)
        used.add(candidate)
    selected_indices.sort()

    selected_lab = lab[np.asarray(selected_indices, dtype=np.int32)]
    squared_distances = np.sum((lab[:, None, :] - selected_lab[None, :, :]) ** 2, axis=2)
    assignment = np.argmin(squared_distances, axis=1)
    nearest_delta = np.sqrt(squared_distances[np.arange(palette_size), assignment])
    selected_colors = [dict(entries[index]) for index in selected_indices]
    clusters = []
    for selected_position, source_index in enumerate(selected_indices):
        member_mask = assignment == selected_position
        clusters.append({
            "representative_hex": str(entries[source_index].get("hex") or rgb_to_hex(rgbs[source_index])),
            "representative_name": str(entries[source_index].get("name") or f"Цвет {source_index + 1}"),
            "represented_color_count": int(np.count_nonzero(member_mask)),
            "max_delta_e76": round(float(np.max(nearest_delta[member_mask])), 4) if np.any(member_mask) else 0.0,
        })

    report = {
        "enabled": True,
        "method": "CIELAB_farthest_point_seeding_plus_palette_medoid_refinement",
        "input_color_count": input_count,
        "output_color_count": len(selected_colors),
        "target_color_count": target_count,
        "removed_color_count": input_count - len(selected_colors),
        "required_color_hexes": normalized_required,
        "preserved_required_colors": preserved_required_colors,
        "missing_required_colors": missing_required_colors,
        "reserved_color_hexes": preserved_required_colors,
        "mean_delta_e76": round(float(np.mean(nearest_delta)), 4),
        "max_delta_e76": round(float(np.max(nearest_delta)), 4),
        "clusters": clusters,
        "selected_hex_colors": [str(entry.get("hex") or rgb_to_hex(entry["rgb"])) for entry in selected_colors],
        "note": (
            "Выбраны реальные образцы из исходной игровой палитры; координаты кликов и RGB "
            "сохранены без изменений. Обязательные цвета остаются в палитре, если присутствуют в источнике. "
            "ΔE76 используется для кластеризации и оценки покрытия."
        ),
    }
    return selected_colors, report

"""Per-color connected-component filtering for binary image layers."""
from __future__ import annotations

import cv2
import numpy as np


class LayerSegmentationError(ValueError):
    """Raised when a binary color layer cannot be segmented safely."""


def filter_small_components(mask: np.ndarray, min_component_area: int) -> tuple[np.ndarray, int]:
    if isinstance(min_component_area, bool) or not isinstance(min_component_area, int) or min_component_area < 1:
        raise LayerSegmentationError("Минимальная площадь компонента должна быть целым числом от 1.")
    binary = np.asarray(mask)
    if binary.ndim != 2 or binary.size == 0:
        raise LayerSegmentationError("Маска цветового слоя должна быть непустой двумерной матрицей.")
    binary = (binary > 0).astype(np.uint8)
    count, labels, stats, _centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
    # Build one lookup table from component label to keep/remove. Comparing the
    # full label image once per component is O(pixel_count * component_count),
    # which becomes extremely expensive for noisy images with many tiny islands.
    areas = stats[1:count, cv2.CC_STAT_AREA]
    keep_label = np.zeros(count, dtype=np.uint8)
    keep_label[1:count] = (areas >= min_component_area).astype(np.uint8)
    removed_pixels = int(areas[areas < min_component_area].sum())
    cleaned = keep_label[labels]
    return cleaned, removed_pixels



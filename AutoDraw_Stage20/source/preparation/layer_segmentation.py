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
    cleaned = np.zeros(binary.shape, dtype=np.uint8)
    removed_pixels = 0
    for label in range(1, count):
        area = int(stats[label, cv2.CC_STAT_AREA])
        component = labels == label
        if area < min_component_area:
            removed_pixels += area
        else:
            cleaned[component] = 1
    return cleaned, removed_pixels



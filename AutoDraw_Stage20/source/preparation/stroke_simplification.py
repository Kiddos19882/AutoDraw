"""Ramer-Douglas-Peucker simplification with color-layer safety checks."""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image, ImageDraw


def simplify_path(
    points: list[tuple[float, float]],
    *,
    closed: bool,
    tolerance_px: float,
    safe_mask: np.ndarray | None,
) -> list[tuple[float, float]]:
    minimum = 3 if closed else 2
    if len(points) < minimum:
        candidate = points
    elif tolerance_px > 0 and len(points) > minimum:
        contour = np.asarray(points, dtype=np.float32).reshape(-1, 1, 2)
        reduced = cv2.approxPolyDP(contour, float(tolerance_px), closed).reshape(-1, 2)
        candidate = [(float(x), float(y)) for x, y in reduced]
        if not closed and len(candidate) >= 2:
            candidate[0] = points[0]
            candidate[-1] = points[-1]
        if len(candidate) < minimum:
            candidate = points
    else:
        candidate = points

    # Validate the actual rendered footprint even when simplification did not
    # run. Two-point skeleton edges can still rasterize through transparent
    # pixels between their endpoints.
    if safe_mask is not None and len(candidate) >= 2:
        height, width = safe_mask.shape
        pairs = list(zip(candidate, candidate[1:]))
        if closed and len(candidate) >= 3:
            pairs.append((candidate[-1], candidate[0]))
        for first, last in pairs:
            x1, y1 = int(round(first[0])), int(round(first[1]))
            x2, y2 = int(round(last[0])), int(round(last[1]))
            if not (
                0 <= x1 < width and 0 <= x2 < width
                and 0 <= y1 < height and 0 <= y2 < height
            ):
                return points
            xmin, xmax = min(x1, x2), max(x1, x2)
            ymin, ymax = min(y1, y2), max(y1, y2)
            line_image = Image.new("1", (xmax - xmin + 1, ymax - ymin + 1), 0)
            ImageDraw.Draw(line_image).line(
                (x1 - xmin, y1 - ymin, x2 - xmin, y2 - ymin),
                fill=1,
                width=1,
            )
            line = np.asarray(line_image, dtype=np.uint8)
            region = safe_mask[ymin:ymax + 1, xmin:xmax + 1]
            if bool(np.any((line > 0) & (region == 0))):
                return points
    return candidate

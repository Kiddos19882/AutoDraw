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
    if tolerance_px <= 0 or len(points) <= (3 if closed else 2):
        return points
    contour = np.asarray(points, dtype=np.float32).reshape(-1, 1, 2)
    reduced = cv2.approxPolyDP(contour, float(tolerance_px), closed).reshape(-1, 2)
    candidate = [(float(x), float(y)) for x, y in reduced]
    if not closed and len(candidate) >= 2:
        candidate[0] = points[0]
        candidate[-1] = points[-1]
    minimum = 3 if closed else 2
    if len(candidate) < minimum:
        return points

    # RDP can cut across a neighboring color. Rasterize every resulting segment
    # and require every sampled point to remain inside this exact color layer.
    if safe_mask is not None:
        height, width = safe_mask.shape
        pairs = list(zip(candidate, candidate[1:]))
        if closed:
            pairs.append((candidate[-1], candidate[0]))
        for first, last in pairs:
            x1, y1 = int(round(first[0])), int(round(first[1]))
            x2, y2 = int(round(last[0])), int(round(last[1]))
            # Validate in a segment-sized ROI instead of allocating a full-canvas
            # image for every RDP segment. This keeps simplification practical for
            # large source images.
            if not (
                0 <= x1 < width and 0 <= x2 < width
                and 0 <= y1 < height and 0 <= y2 < height
            ):
                return points
            xmin, xmax = min(x1, x2), max(x1, x2)
            ymin, ymax = min(y1, y2), max(y1, y2)
            # Match the benchmark and preview renderer exactly. OpenCV LINE_8
            # and Pillow ImageDraw.line can rasterize some segments differently;
            # validating with another rasterizer can approve a path that later
            # paints transparent pixels in the preview.
            roi_size = (xmax - xmin + 1, ymax - ymin + 1)
            line_image = Image.new("1", roi_size, 0)
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



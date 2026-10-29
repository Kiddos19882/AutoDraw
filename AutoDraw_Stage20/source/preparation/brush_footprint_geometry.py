from __future__ import annotations

"""Conservative mapping from a continuous brush footprint to raster pixel cells.

The color map stores pixels as cells, not mathematical points. A safety check
must include every pixel cell with positive-area intersection with the modeled
brush footprint; testing only pixel centers can miss edge bleed.
"""

import math


def footprint_pixel_bounds(
    x_start: float,
    x_end: float,
    y: float,
    brush_value: int,
    scale_x: float,
    scale_y: float,
    width: int,
    height: int,
) -> tuple[int, int, int, int] | None:
    """Return inclusive raster bounds intersected by a horizontal brush stroke.

    Coordinates refer to pixel centers. Cells that only touch the brush exactly
    at an edge are excluded; any positive-area intersection is included. Bounds
    are clipped to the canvas because painting cannot affect pixels outside it.
    Return None when the clipped footprint is empty.
    """
    if width <= 0 or height <= 0:
        return None
    if brush_value <= 0 or scale_x <= 0 or scale_y <= 0:
        raise ValueError("Brush value and axis scales must be positive.")
    if not all(math.isfinite(value) for value in (x_start, x_end, y, scale_x, scale_y)):
        raise ValueError("Brush geometry values must be finite.")
    if x_start > x_end:
        raise ValueError("x_start must not exceed x_end.")

    half_x = brush_value * scale_x / 2.0
    half_y = brush_value * scale_y / 2.0
    # A pixel centered at p occupies [p - 0.5, p + 0.5]. The strict
    # inequalities exclude cells that touch only along a zero-area edge.
    epsilon = 1e-9
    left = math.floor(x_start - half_x - 0.5 + epsilon) + 1
    right = math.ceil(x_end + half_x + 0.5 - epsilon) - 1
    top = math.floor(y - half_y - 0.5 + epsilon) + 1
    bottom = math.ceil(y + half_y + 0.5 - epsilon) - 1

    left = max(0, left)
    right = min(width - 1, right)
    top = max(0, top)
    bottom = min(height - 1, bottom)
    if left > right or top > bottom:
        return None
    return left, right, top, bottom

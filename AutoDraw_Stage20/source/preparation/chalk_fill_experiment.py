from __future__ import annotations

"""Deterministic frozen target masks for the isolated FILL-001 experiment.

This module deliberately does not generate executor-ready strokes. Target masks
are frozen inputs for the later fixed-radius planner and coverage simulator.
"""

import hashlib
import json
import math
from typing import Any

import numpy as np


FILL001_CANVAS_WIDTH = 460
FILL001_CANVAS_HEIGHT = 240
FILL001_SHAPES = ("rectangle", "wide_irregular", "narrow_irregular")
FILL001_RADII = (1, 5, 10, 20, 30)
FILL001_MASK_SCHEMA_VERSION = 1


def _rounded_row_inset(
    y_values: np.ndarray,
    *,
    y_min: int,
    y_max: int,
    corner_radius: float,
) -> np.ndarray:
    """Return the horizontal inset of a rounded rectangle at each row."""
    distance = np.maximum(
        np.maximum(y_min + corner_radius - y_values, 0.0),
        y_values - (y_max - corner_radius),
    )
    inside = (y_values >= y_min) & (y_values <= y_max)
    inset = corner_radius - np.sqrt(
        np.maximum(0.0, corner_radius * corner_radius - distance * distance)
    )
    return np.where(inside, inset, float(max(FILL001_CANVAS_WIDTH, FILL001_CANVAS_HEIGHT)))


def _build_masks() -> dict[str, np.ndarray]:
    yy, xx = np.indices((FILL001_CANVAS_HEIGHT, FILL001_CANVAS_WIDTH), dtype=np.float64)

    # Broad rectangle with rounded corners. Its area is the reference for the
    # approximately area-matched irregular shapes below.
    rect_y_min, rect_y_max, rect_radius = 50, 190, 24.0
    rect_inset = _rounded_row_inset(
        yy, y_min=rect_y_min, y_max=rect_y_max, corner_radius=rect_radius
    )
    rectangle = (
        (yy >= rect_y_min)
        & (yy <= rect_y_max)
        & (xx >= 70.0 + rect_inset)
        & (xx <= 390.0 - rect_inset)
    )

    # Wide irregular area: gently varying left/right boundaries and rounded
    # top/bottom ends. The geometry remains broad enough for radius 30.
    wide_y_min, wide_y_max, wide_radius = 45, 195, 24.0
    wide_inset = _rounded_row_inset(
        yy, y_min=wide_y_min, y_max=wide_y_max, corner_radius=wide_radius
    )
    wide_left = 78.0 + wide_inset + 7.0 * np.sin(yy / 25.0)
    wide_right = 382.0 - wide_inset + 8.0 * np.cos(yy / 31.0)
    wide_irregular = (
        (yy >= wide_y_min)
        & (yy <= wide_y_max)
        & (xx >= wide_left)
        & (xx <= wide_right)
    )

    # Narrower, taller irregular area. Its width varies smoothly but remains
    # safely above the largest tested line width in the central region.
    narrow_y_min, narrow_y_max, narrow_radius = 10, 230, 24.0
    narrow_inset = _rounded_row_inset(
        yy, y_min=narrow_y_min, y_max=narrow_y_max, corner_radius=narrow_radius
    )
    narrow_center = 230.0 + 6.0 * np.sin(yy / 23.0)
    narrow_left = narrow_center - 205.0 / 2.0 + narrow_inset
    narrow_right = narrow_center + 205.0 / 2.0 - narrow_inset + 6.0 * np.cos(yy / 29.0)
    narrow_irregular = (
        (yy >= narrow_y_min)
        & (yy <= narrow_y_max)
        & (xx >= narrow_left)
        & (xx <= narrow_right)
    )

    return {
        "rectangle": rectangle.astype(bool),
        "wide_irregular": wide_irregular.astype(bool),
        "narrow_irregular": narrow_irregular.astype(bool),
    }


def build_fill_target_mask(shape_id: str) -> np.ndarray:
    """Return a read-only deterministic target mask for one FILL-001 shape."""
    if not isinstance(shape_id, str) or shape_id not in FILL001_SHAPES:
        raise ValueError(f"Неизвестная форма FILL-001: {shape_id!r}.")
    mask = _build_masks()[shape_id]
    if not bool(np.any(mask)):
        raise RuntimeError(f"Пустая frozen target mask FILL-001: {shape_id}.")
    mask.setflags(write=False)
    return mask


def fill_target_mask_sha256(shape_id: str, mask: Any | None = None) -> str:
    """Hash the canonical shape ID, dimensions and packed binary mask."""
    target = build_fill_target_mask(shape_id) if mask is None else np.asarray(mask)
    if target.ndim != 2 or target.dtype.kind != "b" or not target.size:
        raise ValueError("FILL-001 mask должна быть непустым двумерным bool-массивом.")
    if target.shape != (FILL001_CANVAS_HEIGHT, FILL001_CANVAS_WIDTH):
        raise ValueError("Размер FILL-001 mask не совпадает с frozen canvas.")
    header = json.dumps(
        {
            "schema_version": FILL001_MASK_SCHEMA_VERSION,
            "shape_id": shape_id,
            "width": FILL001_CANVAS_WIDTH,
            "height": FILL001_CANVAS_HEIGHT,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    packed = np.packbits(target.reshape(-1), bitorder="little").tobytes()
    return hashlib.sha256(header + b"\0" + packed).hexdigest()


def describe_fill_target_mask(shape_id: str) -> dict[str, Any]:
    """Return immutable metadata needed to bind a FILL-001 task to its mask."""
    mask = build_fill_target_mask(shape_id)
    return {
        "schema_version": FILL001_MASK_SCHEMA_VERSION,
        "shape_id": shape_id,
        "canvas": {"width": FILL001_CANVAS_WIDTH, "height": FILL001_CANVAS_HEIGHT},
        "target_area_pixels": int(np.count_nonzero(mask)),
        "target_mask_sha256": fill_target_mask_sha256(shape_id, mask),
        "coordinate_system": "logical_board_pixels",
    }

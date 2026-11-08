from __future__ import annotations

"""FILL-001 Screen Mask V2: diagnostic, run-bound screen projection.

This module NEVER changes the frozen FILL-001 V1 acceptance result. It uses
explicit independently validated desktop-screen BoardPane geometry, never a
fitted offset or inferred coordinates from the painted pixels.
"""

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from chalk_fill_experiment import (
    FILL001_CANVAS_HEIGHT,
    FILL001_CANVAS_WIDTH,
    build_fill_target_mask,
    fill_target_mask_sha256,
)
from chalk_fill_capture_adapter import PNG_CHANGE_THRESHOLD, audit_fill001_png_pair
from chalk_fill_matrix import FillMatrixError

SCHEMA = "FILL001_SCREEN_MASK_V2"


def _screen_pixels(path: str | Path) -> tuple[np.ndarray, str]:
    path = Path(path)
    if not path.is_file():
        raise FillMatrixError(f"Screen Mask V2: PNG not found: {path}")
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        with Image.open(path) as image:
            if image.format != "PNG":
                raise FillMatrixError("Screen Mask V2 requires PNG files.")
            pixels = np.asarray(image.convert("RGB"), dtype=np.int16)
    except (OSError, ValueError) as exc:
        raise FillMatrixError(f"Invalid Screen Mask V2 PNG: {exc}") from exc
    return pixels, digest


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FillMatrixError(f"{label} must be a finite number.")
    value = float(value)
    if not np.isfinite(value):
        raise FillMatrixError(f"{label} must be finite.")
    return value


def _check_geometry(geometry: Any, run_id: str) -> tuple[float, float, float, float]:
    if not isinstance(geometry, dict):
        raise FillMatrixError("Screen Mask V2 requires explicit run-bound geometry.")
    if (geometry.get("run_id") != run_id or
            geometry.get("coordinate_system") != "desktop_screen_css_pixels" or
            geometry.get("validation_status") != "valid" or
            geometry.get("independent_screen_mapping") is not True or
            geometry.get("same_run") is not True):
        raise FillMatrixError("Screen Mask V2: unvalidated, mismatched, or non-screen geometry.")
    corners = geometry.get("board_screen_corners")
    if not isinstance(corners, dict):
        raise FillMatrixError("Screen Mask V2 requires board_screen_corners.")
    x0 = _finite_number(corners.get("left"), "left")
    y0 = _finite_number(corners.get("top"), "top")
    x1 = _finite_number(corners.get("right"), "right")
    y1 = _finite_number(corners.get("bottom"), "bottom")
    if x1 <= x0 or y1 <= y0:
        raise FillMatrixError("Screen Mask V2: invalid board dimensions.")
    if not isinstance(geometry.get("evidence_sha256"), str) or len(geometry["evidence_sha256"]) != 64:
        raise FillMatrixError("Screen Mask V2 requires provenance evidence SHA256.")
    try:
        int(geometry["evidence_sha256"], 16)
    except ValueError as exc:
        raise FillMatrixError("Screen Mask V2: invalid evidence SHA256.") from exc
    return x0, y0, x1, y1


def project_screen_mask_v2(
    shape_id: str,
    *,
    run_id: str,
    screen_roi: dict[str, int],
    geometry: dict[str, Any],
) -> np.ndarray:
    """Project frozen logical pixels to ROI pixel centers via same-run screen bounds.

    The board corners are screen-space positions of logical [0,460]x[0,240].
    Pixels outside BoardPane are excluded. No adjustable translations, dilation,
    erosion, quality threshold changes or post-hoc alignment are supported.
    """
    if not isinstance(run_id, str) or not run_id.strip():
        raise FillMatrixError("Screen Mask V2 requires a nonempty run_id.")
    if not isinstance(screen_roi, dict) or any(
        type(screen_roi.get(k)) is not int for k in ("x", "y", "width", "height")
    ):
        raise FillMatrixError("Screen Mask V2 requires integer ROI x/y/width/height.")
    ox, oy, width, height = (screen_roi[k] for k in ("x", "y", "width", "height"))
    if ox < 0 or oy < 0 or width < 2 or height < 2:
        raise FillMatrixError("Screen Mask V2: invalid screen ROI.")
    x0, y0, x1, y1 = _check_geometry(geometry, run_id)

    # Explicit centers in desktop screenshot pixels. Geometry is never
    # estimated from the before/after image or the drawn strokes.
    lx = (ox + np.arange(width, dtype=np.float64) - x0) * FILL001_CANVAS_WIDTH / (x1 - x0)
    ly = (oy + np.arange(height, dtype=np.float64) - y0) * FILL001_CANVAS_HEIGHT / (y1 - y0)
    within_x = (lx >= 0) & (lx <= FILL001_CANVAS_WIDTH)
    within_y = (ly >= 0) & (ly <= FILL001_CANVAS_HEIGHT)
    if not np.any(within_x) or not np.any(within_y):
        raise FillMatrixError("Screen Mask V2: ROI and BoardPane have no overlap.")
    ix = np.clip(np.rint(lx).astype(np.intp), 0, FILL001_CANVAS_WIDTH - 1)
    iy = np.clip(np.rint(ly).astype(np.intp), 0, FILL001_CANVAS_HEIGHT - 1)
    mask = build_fill_target_mask(shape_id)[np.ix_(iy, ix)]
    mask &= within_y[:, None] & within_x[None, :]
    if not np.any(mask):
        raise FillMatrixError("Screen Mask V2: empty projected target.")
    mask.setflags(write=False)
    return mask


def audit_screen_mask_v2(
    shape_id: str,
    before_png: str | Path,
    after_png: str | Path,
    *,
    run_id: str,
    screen_roi: dict[str, int],
    geometry: dict[str, Any],
) -> dict[str, Any]:
    """Read-only diagnostic; retain independent V1 metrics and FAIL status."""
    before, before_sha = _screen_pixels(before_png)
    after, after_sha = _screen_pixels(after_png)
    if before.shape != after.shape or before.ndim != 3 or before.shape[2] != 3:
        raise FillMatrixError("Screen Mask V2: PNG pair dimensions differ.")
    if (before.shape[1], before.shape[0]) != (screen_roi.get("width"), screen_roi.get("height")):
        raise FillMatrixError("Screen Mask V2: ROI size does not match PNG dimensions.")
    mask = project_screen_mask_v2(shape_id, run_id=run_id, screen_roi=screen_roi, geometry=geometry)
    changed = np.any(np.abs(after - before) > PNG_CHANGE_THRESHOLD, axis=2)
    covered = int(np.count_nonzero(changed & mask))
    target = int(np.count_nonzero(mask))
    leak = int(np.count_nonzero(changed & ~mask))
    v1 = audit_fill001_png_pair(shape_id, before_png, after_png, screen_roi=screen_roi)
    return {
        "schema": SCHEMA,
        "diagnostic_only": True,
        "run_id": run_id,
        "geometry_evidence_sha256": geometry["evidence_sha256"],
        "frozen_target_mask_sha256": fill_target_mask_sha256(shape_id),
        "before_png_sha256": before_sha,
        "after_png_sha256": after_sha,
        "rgb_change_threshold": PNG_CHANGE_THRESHOLD,
        "target_pixels": target,
        "covered_pixels": covered,
        "uncovered_pixels": target - covered,
        "coverage_fraction": covered / target,
        "leakage_pixels": leak,
        "changed_pixels": int(np.count_nonzero(changed)),
        "v1_original": {
            "coverage_fraction": v1["coverage_fraction"],
            "leakage_pixels": v1["leakage_pixels"],
            "png_audit_status": v1["png_audit_status"],
        },
        "v2_diagnostic_gate": "PASS" if covered / target >= .99 and leak == 0 else "FAIL",
        "acceptance_override": False,
    }

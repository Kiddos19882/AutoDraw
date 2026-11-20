#!/usr/bin/env python3
"""ENGINE-001/BPRED-S4-R1: generic original-RGB source maps, research only.

Not a stroke-admission oracle. No manual ROIs, legacy palette seeds, Egret
coordinates, or privileged knowledge of the heldout image filenames.
Original P1 Lab/deltaE/Sobel idea reused without P1's fixed shape/ROIs.
"""
from __future__ import annotations

import hashlib
import io
from typing import Any

import numpy as np
from PIL import Image, ImageOps
from scipy import ndimage
from skimage import color, filters

VERSION = "ENGINE001_BPRED_S4R1_GENERIC_SOURCE_MAP_V1"
MAX_PIXELS = 16_000_000
DELTA_E_STRONG = 12.0  # inherited source-only P1 diagnostic, not a safety gate
SOBEL_PERCENTILE = 90.0  # inherited source-only P1 diagnostic, not a safety gate


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def decode_original(raw: bytes) -> dict[str, Any]:
    """Decode original, apply EXIF orientation, and preserve RGB/alpha exactly."""
    if not isinstance(raw, bytes) or not raw:
        raise ValueError("BLOCKED_S4R1_EMPTY_OR_NONBINARY_SOURCE")
    with Image.open(io.BytesIO(raw)) as opened:
        opened.load()
        original_mode = opened.mode
        exif_orientation = int(opened.getexif().get(274, 1))
        oriented = ImageOps.exif_transpose(opened)
        width, height = oriented.size
        if width < 1 or height < 1 or width * height > MAX_PIXELS:
            raise ValueError("BLOCKED_S4R1_SOURCE_SIZE")
        rgba = np.asarray(oriented.convert("RGBA"), dtype=np.uint8).copy()
    if rgba.shape != (height, width, 4):
        raise ValueError("BLOCKED_S4R1_SOURCE_DECODE")
    return {
        "rgba": rgba,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_sha1": git_blob_sha1(raw),
        "original_mode": original_mode,
        "exif_orientation": exif_orientation,
        "width": width,
        "height": height,
    }


def letterbox_binding(source_wh: tuple[int, int],
                      target_wh: tuple[int, int] | None = None) -> dict[str, Any]:
    """Document an image-space affine with explicit letterbox, never a game calibration."""
    sw, sh = source_wh
    if target_wh is None:
        target_wh = source_wh
    tw, th = target_wh
    if any(not isinstance(v, (int, np.integer)) or v < 1 for v in (sw, sh, tw, th)):
        raise ValueError("BLOCKED_S4R1_INVALID_COORDINATE_BINDING")
    if sw * sh > MAX_PIXELS or tw * th > MAX_PIXELS:
        raise ValueError("BLOCKED_S4R1_COORDINATE_SIZE")
    factor = min(tw / sw, th / sh)
    cw = min(tw, max(1, int(round(sw * factor))))
    ch = min(th, max(1, int(round(sh * factor))))
    ox, oy = (tw - cw) // 2, (th - ch) // 2
    sx, sy = cw / sw, ch / sh
    return {
        "source_wh": [int(sw), int(sh)],
        "target_wh": [int(tw), int(th)],
        "content_xywh": [int(ox), int(oy), int(cw), int(ch)],
        "source_to_target_xy": [[float(sx), 0.0, float(ox)],
                                [0.0, float(sy), float(oy)]],
        "target_to_source_xy": [[float(1 / sx), 0.0, float(-ox / sx)],
                                [0.0, float(1 / sy), float(-oy / sy)]],
        "coordinate_system": "image-pixel-edges; NOT desktop/client/Egret calibration",
    }


def generic_source_maps(
    rgba: np.ndarray, *,
    owner_index: np.ndarray | None = None,
    owner_palette_rgb: np.ndarray | None = None,
    source_white_owner: int | None = None,
    logical_wh: tuple[int, int] | None = None,
) -> dict[str, Any]:
    """Source evidence only. UNKNOWN is never equivalent to ADMISSIBLE."""
    if (not isinstance(rgba, np.ndarray) or rgba.ndim != 3 or
            rgba.shape[2] != 4 or rgba.dtype != np.uint8 or
            rgba.shape[0] * rgba.shape[1] > MAX_PIXELS or
            min(rgba.shape[:2]) < 1):
        raise ValueError("BLOCKED_S4R1_INVALID_ORIGINAL_RGBA")
    h, w = rgba.shape[:2]
    rgb = rgba[:, :, :3].copy()
    alpha = rgba[:, :, 3].copy()
    owner_rgb = None
    if (owner_index is None) != (owner_palette_rgb is None):
        raise ValueError("BLOCKED_S4R1_OWNER_PALETTE_PROVENANCE_MISSING")
    if owner_index is not None:
        if (not isinstance(owner_index, np.ndarray) or owner_index.shape != (h, w)
                or not np.issubdtype(owner_index.dtype, np.integer) or
                not isinstance(owner_palette_rgb, np.ndarray) or
                owner_palette_rgb.ndim != 2 or owner_palette_rgb.shape[1] != 3 or
                owner_palette_rgb.dtype != np.uint8 or len(owner_palette_rgb) < 1 or
                int(owner_index.min()) < 0 or
                int(owner_index.max()) >= len(owner_palette_rgb)):
            raise ValueError("BLOCKED_S4R1_INVALID_OWNER_PALETTE")
        owner_index = owner_index.copy()
        owner_rgb = owner_palette_rgb[owner_index].copy()
    if source_white_owner is not None:
        if owner_index is None or not isinstance(source_white_owner, (int, np.integer)) or not (
            0 <= int(source_white_owner) < len(owner_palette_rgb)
        ):
            raise ValueError("BLOCKED_S4R1_UNBOUND_WHITE_OWNER")
    # P1's source-derived Lab CIEDE2000 and Sobel algorithm, generalized to HxW.
    lab = color.rgb2lab(rgb.astype(np.float64) / 255.0)
    delta = np.zeros((h, w), dtype=np.float32)
    if h > 1:
        vertical = color.deltaE_ciede2000(lab[:-1], lab[1:]).astype(np.float32)
        delta[:-1] = np.maximum(delta[:-1], vertical)
        delta[1:] = np.maximum(delta[1:], vertical)
    if w > 1:
        horizontal = color.deltaE_ciede2000(lab[:, :-1], lab[:, 1:]).astype(np.float32)
        delta[:, :-1] = np.maximum(delta[:, :-1], horizontal)
        delta[:, 1:] = np.maximum(delta[:, 1:], horizontal)
    gray = color.rgb2gray(rgb.astype(np.float64) / 255.0)
    sobel = filters.sobel(gray)
    # A constant source must not become an all-edge mask from FP roundoff.
    # This is a numerical zero guard, NOT a visual/safety acceptance threshold.
    sobel = np.where(sobel <= 1e-12, 0.0, sobel)
    positive = sobel[sobel > 0]
    sobel_threshold = (float(np.percentile(positive, SOBEL_PERCENTILE))
                       if len(positive) else None)
    source_edge = (sobel >= sobel_threshold if sobel_threshold is not None
                   else np.zeros((h, w), dtype=bool))
    source_edge |= (delta >= DELTA_E_STRONG)
    owner_edge = np.zeros((h, w), dtype=bool)
    if owner_index is not None:
        if h > 1:
            diff = owner_index[:-1] != owner_index[1:]
            owner_edge[:-1] |= diff
            owner_edge[1:] |= diff
        if w > 1:
            diff = owner_index[:, :-1] != owner_index[:, 1:]
            owner_edge[:, :-1] |= diff
            owner_edge[:, 1:] |= diff
    transparent = alpha == 0
    partial_alpha = (alpha > 0) & (alpha < 255)
    exact_white = (alpha == 255) & np.all(rgb == 255, axis=2)
    owner_white = (owner_index == source_white_owner if source_white_owner is not None
                   else np.zeros((h, w), dtype=bool))
    geometric_detail = source_edge | owner_edge
    boundary_band = ndimage.binary_dilation(geometric_detail, iterations=1)
    # Conservative source masks are NOT proof of semantically complete protection.
    protected = (boundary_band | exact_white | owner_white | transparent | partial_alpha)
    unknown = ~protected  # No independently validated semantic model or native false-safe bound.
    geometric_interior = (alpha == 255) & ~protected
    candidate_interior = geometric_interior & (owner_index is not None)
    assert np.all(protected | unknown) and not np.any(protected & unknown)
    return {
        "version": VERSION,
        "source_rgb": rgb,
        "source_alpha": alpha,
        "owner_index": owner_index,
        "owner_rgb": owner_rgb,
        "owner_status": "SOURCE_BOUND" if owner_index is not None else "MISSING",
        "source_edge": source_edge,
        "source_delta_e": delta,
        "source_sobel": sobel.astype(np.float32),
        "owner_edge": owner_edge,
        "geometric_detail_evidence": geometric_detail,
        "semantic_detail_status": "UNKNOWN_NO_VERIFIED_SEMANTIC_MODEL",
        "transparent": transparent,
        "partial_alpha": partial_alpha,
        "exact_white_evidence": exact_white,
        "explicit_white_owner": owner_white,
        "protected": protected,
        "unknown": unknown,
        "geometric_interior": geometric_interior,
        "candidate_interior": candidate_interior,
        "stroke_admission": "FORBIDDEN_UNTIL_NATIVE_INDEPENDENT_VALIDATION",
        "source_to_logical": letterbox_binding((w, h), logical_wh),
        "counts": {k: int(np.count_nonzero(v)) for k, v in {
            "source_edges": source_edge, "owner_edges": owner_edge,
            "geometric_detail": geometric_detail,
            "protected": protected, "unknown": unknown,
            "transparent": transparent, "partial_alpha": partial_alpha,
            "exact_white": exact_white, "owner_white": owner_white,
            "geometric_interior": geometric_interior,
            "candidate_interior": candidate_interior,
        }.items()},
    }

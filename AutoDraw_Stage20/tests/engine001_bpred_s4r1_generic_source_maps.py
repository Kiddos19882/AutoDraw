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
from scipy.spatial import cKDTree
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


# S4R1 owner128 DEV step: a palette proximity PROPOSAL, never a verified owner.
PROPOSAL_VERSION = "ENGINE001_BPRED_S4R1_OWNER128_PROVISIONAL_V1"
PINNED_ENGINE_BLOB_SHA1 = "46cc74de00b6cb5d207b1e1a2ffcd81613b6d388"
PINNED_ENGINE_BYTES = 4859418
PROPOSAL_CHUNK_PIXELS = 32768


def provisional_game128_owner_maps(
    original_raw: bytes,
    game128: np.ndarray,
    engine_provenance: dict[str, Any],
) -> dict[str, Any]:
    """Original RGB nearest-Lab game128 hypothesis; NEVER source-bound / SAFE.

    Caller must obtain game128/provenance from the pre-existing B1-R P3B
    read_engine_palette() SHA-pinned parser. Do not call its 32-color selector
    or its image-specific ROI/shape code. Alpha<255 cannot have known owner.
    """
    original = decode_original(original_raw)  # input bytes + EXIF/alpha pin
    if (
        not isinstance(game128, np.ndarray)
        or game128.shape != (128, 3)
        or game128.dtype != np.uint8
        or np.unique(game128, axis=0).shape[0] != 128
        or not isinstance(engine_provenance, dict)
        or engine_provenance.get("engine_git_blob_sha1") != PINNED_ENGINE_BLOB_SHA1
        or engine_provenance.get("engine_bytes") != PINNED_ENGINE_BYTES
        or engine_provenance.get("engine_colors") != 128
        or engine_provenance.get("painter_method")
           != "PainterPopup.createElaborateEasterEggs"
        or not isinstance(engine_provenance.get("swatch_RGB"), list)
        or len(engine_provenance["swatch_RGB"]) != 128
        or not np.array_equal(game128[6], [255, 255, 255])
    ):
        raise ValueError("BLOCKED_S4R1_UNVERIFIED_GAME128_PROVENANCE")
    # Bind the supplied array to the per-index RGB metadata returned by P3B.
    for i, record in enumerate(engine_provenance["swatch_RGB"]):
        if (not isinstance(record, dict) or record.get("index") != i
                or record.get("RGB") != game128[i].tolist()):
            raise ValueError("BLOCKED_S4R1_PALETTE_METADATA_MISMATCH")

    rgba = original["rgba"]
    height, width = rgba.shape[:2]
    opaque = rgba[:, :, 3] == 255
    opaque_flat_indices = np.flatnonzero(opaque.reshape(-1))
    owner_flat = np.full(height * width, -1, dtype=np.int16)
    # Distances are EXPLORATORY CIELAB Euclidean, not calibrated owner confidence.
    distance_flat = np.full(height * width, np.nan, dtype=np.float32)
    game_lab = color.rgb2lab(
        game128.astype(np.float64).reshape(1, 128, 3) / 255.0
    ).reshape(128, 3)
    tree = cKDTree(game_lab)
    original_rgb_flat = rgba[:, :, :3].reshape(-1, 3)
    for start in range(0, len(opaque_flat_indices), PROPOSAL_CHUNK_PIXELS):
        positions = opaque_flat_indices[start:start + PROPOSAL_CHUNK_PIXELS]
        source_lab = color.rgb2lab(
            original_rgb_flat[positions].astype(np.float64).reshape(1, -1, 3)
            / 255.0
        ).reshape(-1, 3)
        dist, nearest = tree.query(source_lab, k=2, workers=1)
        # For an exact numerical tie between two returned neighbors, use
        # the lower index (but never infer any semantic certainty from it).
        chosen = np.where(
            np.isclose(dist[:, 0], dist[:, 1], rtol=0, atol=1e-10),
            np.minimum(nearest[:, 0], nearest[:, 1]),
            nearest[:, 0],
        )
        owner_flat[positions] = chosen.astype(np.int16)
        distance_flat[positions] = dist[:, 0].astype(np.float32)
    proposal = owner_flat.reshape(height, width)
    distance = distance_flat.reshape(height, width)
    # Only valid-and-valid neighboring owner changes are eligible evidence.
    edges = np.zeros((height, width), dtype=bool)
    if height > 1:
        changed = (opaque[:-1] & opaque[1:] &
                   (proposal[:-1] != proposal[1:]))
        edges[:-1] |= changed
        edges[1:] |= changed
    if width > 1:
        changed = (opaque[:, :-1] & opaque[:, 1:] &
                   (proposal[:, :-1] != proposal[:, 1:]))
        edges[:, :-1] |= changed
        edges[:, 1:] |= changed
    preview = rgba.copy()
    if len(opaque_flat_indices):
        preview.reshape(-1, 4)[opaque_flat_indices, :3] = game128[
            owner_flat[opaque_flat_indices]
        ]
    valid_distances = distance_flat[opaque_flat_indices]
    return {
        "version": PROPOSAL_VERSION,
        "source_sha256": original["sha256"],
        "source_git_blob_sha1": original["git_blob_sha1"],
        "source_wh": [width, height],
        "source_alpha_unmodified": True,
        "game_engine_git_blob_sha1": PINNED_ENGINE_BLOB_SHA1,
        "game128_palette_sha256": hashlib.sha256(game128.tobytes()).hexdigest(),
        "provisional_owner_index": proposal,
        "provisional_owner_rgb_preview": preview,
        "provisional_owner_valid": opaque,
        "provisional_owner_edge": edges,
        "lab_nearest_distance": distance,
        "proposal_status": "PROVISIONAL_LAB_NEAREST_NOT_SOURCE_OWNER",
        "source_owner_status": "MISSING",
        "semantic_detail_status": "UNKNOWN_NO_VERIFIED_SEMANTIC_MODEL",
        "stroke_admission": "FORBIDDEN_UNTIL_NATIVE_INDEPENDENT_VALIDATION",
        "counts": {
            "opaque_assigned_provisionally": int(len(opaque_flat_indices)),
            "unassigned_nonopaque": int(opaque.size - len(opaque_flat_indices)),
            "unique_proposed_game_colors": int(len(np.unique(owner_flat[
                opaque_flat_indices]))) if len(opaque_flat_indices) else 0,
            "proposed_owner_edges": int(np.count_nonzero(edges)),
        },
        "lab_nearest_distance_mean": (
            float(np.mean(valid_distances)) if len(valid_distances) else None),
        "lab_nearest_distance_p95": (
            float(np.percentile(valid_distances, 95)) if len(valid_distances) else None),
        "owner_accuracy": "UNKNOWN_NO_SOURCE_OWNER_GROUND_TRUTH",
        "source_to_logical": letterbox_binding((width, height)),
    }

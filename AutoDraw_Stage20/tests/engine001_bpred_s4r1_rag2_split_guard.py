#!/usr/bin/env python3
"""RAG2: original-only source-detail-aware SLIC split and guarded game128 grouping.

Research E2 only. No old RAG1/FC1/E/F/G32/V44/P4D artwork or strokes are inputs.
Geometry is computed from this original + pinned real game128 palette.
"""
from __future__ import annotations

from collections import defaultdict
import numpy as np
from scipy.spatial import cKDTree
from skimage import color, measure

import engine001_bpred_s4r1_generic_source_maps as source


VERSION = "ENGINE001_BPRED_S4R1_RAG2_SOURCE_DETAIL_SPLIT_GUARD_V1"
SOURCE_STRONG_LAB = 12.0
SOURCE_MEAN_LAB = 12.0
CANDIDATE_MAX_AREA = 3  # Only eligibility; never blindly delete small detail
MAX_ADDED_RGB_MAE = 1.0
CHUNK = 65536


def _split_geometry(slic: np.ndarray, provisional: np.ndarray, opaque: np.ndarray):
    """SLIC region * source-nearest game swatch; 4-connected components.

    skimage.measure.label groups equal nonzero input values with 4-connectivity.
    Thus even a 1px detail *inside* an original SLIC cannot be silently merged.
    """
    packed = np.zeros(slic.shape, dtype=np.int32)
    packed[opaque] = ((slic[opaque].astype(np.int32) - 1) * 128
                       + provisional[opaque].astype(np.int32) + 1)
    return measure.label(packed, background=0, connectivity=1).astype(np.int32)


def _rag_adjacency(regions: np.ndarray, lab: np.ndarray):
    """Return unique real 4-neighbor edges with length and max source contrast."""
    n = int(regions.max()) + 1
    all_keys, all_delta = [], []
    for a, b, la, lb in (
        (regions[:, :-1], regions[:, 1:], lab[:, :-1], lab[:, 1:]),
        (regions[:-1, :], regions[1:, :], lab[:-1, :], lab[1:, :]),
    ):
        mask = (a > 0) & (b > 0) & (a != b)
        if not np.any(mask):
            continue
        left = a[mask].astype(np.int64)
        right = b[mask].astype(np.int64)
        keys = np.minimum(left, right) * n + np.maximum(left, right)
        contrast = np.linalg.norm((la - lb)[mask], axis=1)
        all_keys.append(keys)
        all_delta.append(contrast)
    if not all_keys:
        return np.empty((0, 2), np.int32), np.empty(0, np.int64), np.empty(0)
    keys = np.concatenate(all_keys)
    contrast = np.concatenate(all_delta)
    unique, inverse, lengths = np.unique(keys, return_inverse=True, return_counts=True)
    maximum = np.zeros(len(unique), np.float64)
    np.maximum.at(maximum, inverse, contrast)
    pairs = np.column_stack((unique // n, unique % n)).astype(np.int32)
    return pairs, lengths.astype(np.int64), maximum


def build_rag2(original_rgba: np.ndarray, game128: np.ndarray) -> dict:
    if (not isinstance(original_rgba, np.ndarray)
            or original_rgba.ndim != 3 or original_rgba.shape[2] != 4
            or original_rgba.dtype != np.uint8
            or min(original_rgba.shape[:2]) < 1
            or original_rgba.shape[0] * original_rgba.shape[1] > source.MAX_PIXELS):
        raise ValueError("BLOCKED_RAG2_INVALID_ORIGINAL")
    if (not isinstance(game128, np.ndarray)
            or game128.dtype != np.uint8 or game128.shape != (128, 3)
            or len(np.unique(game128, axis=0)) != 128):
        raise ValueError("BLOCKED_RAG2_INVALID_PALETTE")
    rgba = original_rgba
    h, w = rgba.shape[:2]
    opaque = rgba[:, :, 3] == 255
    owners = np.full((h, w), -1, np.int16)
    baseline = owners.copy()
    preview = rgba.copy()
    zeros = np.zeros((h, w), np.int32)
    strong = np.zeros((h, w), bool)
    if not opaque.any():
        return {
            "version": VERSION, "region_ids": zeros, "game_index": owners,
            "baseline_index": baseline, "preview_rgba": preview,
            "source_strong_edge": strong, "source_owner_status": "MISSING",
            "stroke_admission": "FORBIDDEN_UNTIL_INDEPENDENT_NATIVE_VALIDATION",
            "counts": {"initial_slic_regions": 0, "initial_split_regions": 0,
                       "final_regions": 0, "reassigned_components": 0,
                       "reassigned_pixels": 0, "candidate_small_components": 0},
        }
    original_maps = source.generic_source_maps(rgba)
    source_regions = source.original_source_region_uncertainty(rgba, original_maps)
    slic = source_regions["region_ids"]
    if (slic.shape != (h, w) or np.any(slic[opaque] <= 0)
            or np.any(slic[~opaque] != 0)):
        raise ValueError("BLOCKED_RAG2_BAD_SOURCE_SLIC")
    rgb = rgba[:, :, :3]
    lab = color.rgb2lab(rgb.astype(np.float64) / 255.0)
    game_lab = color.rgb2lab(
        game128.reshape((1, 128, 3)).astype(np.float64) / 255.0
    ).reshape(128, 3)
    tree = cKDTree(game_lab)
    opaque_flat = np.flatnonzero(opaque.ravel())
    all_lab = lab.reshape(-1, 3)
    flat_base = baseline.ravel()
    for start in range(0, len(opaque_flat), CHUNK):
        indices = opaque_flat[start:start + CHUNK]
        flat_base[indices] = tree.query(all_lab[indices], k=1, workers=1)[1].astype(np.int16)
    owners[opaque] = baseline[opaque]

    initial = _split_geometry(slic, baseline, opaque)
    n = int(initial.max())
    ids = initial[opaque]
    counts = np.bincount(ids, minlength=n + 1).astype(np.int64)
    initial_owner = np.full(n + 1, -1, np.int16)
    initial_owner[ids] = baseline[opaque]
    lab_sums = np.zeros((n + 1, 3), np.float64)
    orig_lab = lab[opaque]
    for c in range(3):
        lab_sums[:, c] = np.bincount(ids, weights=orig_lab[:, c], minlength=n + 1)
    mean_lab = np.zeros_like(lab_sums)
    mean_lab[1:] = lab_sums[1:] / np.maximum(counts[1:, None], 1)
    pairs, lengths, boundary_max = _rag_adjacency(initial, lab)
    candidates = np.flatnonzero((counts > 0) & (counts <= CANDIDATE_MAX_AREA))
    candidates = candidates[candidates > 0]
    candidates_set = set(int(i) for i in candidates)
    adjacency = defaultdict(list)
    source_strong_edges = int(np.count_nonzero(boundary_max > SOURCE_STRONG_LAB))
    for (a, b), length, maximum in zip(pairs, lengths, boundary_max):
        a, b = int(a), int(b)
        # A strong source boundary disqualifies the pair; nothing is erased.
        if maximum > SOURCE_STRONG_LAB:
            continue
        if a in candidates_set:
            adjacency[a].append((b, int(length)))
        if b in candidates_set:
            adjacency[b].append((a, int(length)))
    # The split components are contiguous in a flattened, stable sorted index;
    # gather up to 3 original pixels for a proposed regional swatch reassignment.
    flat_initial = initial.ravel()
    valid_positions = np.flatnonzero(flat_initial)
    sorted_order = np.argsort(flat_initial[valid_positions], kind="stable")
    sorted_positions = valid_positions[sorted_order]
    offsets = np.zeros(n + 2, np.int64)
    offsets[1:] = np.cumsum(counts)
    # There is no source area for region 0; its count is always zero by design.
    if counts[0] != 0 or int(offsets[-1]) != len(sorted_positions):
        raise ValueError("BLOCKED_RAG2_REGION_COUNTS")
    flat_rgb = rgb.reshape(-1, 3)
    flat_owner = owners.ravel()
    accepted = 0
    accepted_pixels = 0
    rejected_mean = 0
    rejected_cost = 0
    no_weak_neighbor = 0
    for region in candidates:
        region = int(region)
        neighbors = adjacency.get(region, [])
        if not neighbors:
            no_weak_neighbor += 1
            continue
        pos = sorted_positions[offsets[region]:offsets[region + 1]]
        source_pixels = flat_rgb[pos].astype(np.float64)
        old_index = int(initial_owner[region])
        old_error = float(np.abs(source_pixels - game128[old_index]).mean())
        best = None
        for neighbor, shared in neighbors:
            new_index = int(initial_owner[neighbor])
            if new_index == old_index:
                continue
            if np.linalg.norm(mean_lab[region] - mean_lab[neighbor]) > SOURCE_MEAN_LAB:
                rejected_mean += 1
                continue
            new_error = float(np.abs(source_pixels - game128[new_index]).mean())
            added = new_error - old_error
            if added > MAX_ADDED_RGB_MAE + 1e-10:
                rejected_cost += 1
                continue
            rank = (round(added, 12), -shared, new_index)
            if best is None or rank < best[0]:
                best = (rank, new_index)
        if best is not None:
            flat_owner[pos] = best[1]
            accepted += 1
            accepted_pixels += len(pos)
    # The returned geometry must remain 4-connected and distinguish region vs color.
    final = _split_geometry(slic, owners, opaque)
    preview[opaque, :3] = game128[owners[opaque]]
    for a, b in (
        ((lab[:, :-1], lab[:, 1:]), (strong[:, :-1], strong[:, 1:])),
        ((lab[:-1], lab[1:]), (strong[:-1], strong[1:])),
    ):
        contrast = np.linalg.norm(a[0] - a[1], axis=2) > SOURCE_STRONG_LAB
        b[0] |= contrast
        b[1] |= contrast
    return {
        "version": VERSION, "region_ids": final, "game_index": owners,
        "baseline_index": baseline, "preview_rgba": preview,
        "source_strong_edge": strong, "source_owner_status": "MISSING",
        "stroke_admission": "FORBIDDEN_UNTIL_INDEPENDENT_NATIVE_VALIDATION",
        "counts": {
            "initial_slic_regions": int(np.unique(slic[opaque]).size),
            "initial_split_regions": n, "final_regions": int(final.max()),
            "reassigned_components": accepted, "reassigned_pixels": accepted_pixels,
            "candidate_small_components": int(len(candidates)),
            "pairs_with_source_strong_boundary": source_strong_edges,
            "skipped_without_weak_neighbor": no_weak_neighbor,
            "rejected_mean_source_lab": rejected_mean,
            "rejected_rgb_reconstruction_cost": rejected_cost,
            "game_colors": int(np.unique(owners[opaque]).size),
        },
    }


def color_islands(owners: np.ndarray) -> dict:
    """Original source-resolution game colors; connected is 8-neighbor."""
    from scipy import ndimage
    opaque = owners >= 0
    singletons = 0
    components = 0
    le3 = 0
    for val in np.unique(owners[opaque]):
        labels, n = ndimage.label(owners == val, structure=np.ones((3, 3), bool))
        area = np.bincount(labels.ravel())[1:]
        singletons += int(np.sum(area == 1))
        le3 += int(np.sum(area <= 3))
        components += n
    return {"components": components, "singletons": singletons,
            "components_le3": le3}


def evaluate_rag2(original_rgba: np.ndarray, game128: np.ndarray, data: dict) -> dict:
    opaque = original_rgba[:, :, 3] == 255
    if not opaque.any():
        return {"opaque": 0, "baseline": color_islands(data["baseline_index"]),
                "candidate": color_islands(data["game_index"]), "candidate_counts": data["counts"]}
    rgb = original_rgba[:, :, :3][opaque].astype(np.float64)
    a = game128[data["baseline_index"][opaque]].astype(np.float64)
    b = game128[data["game_index"][opaque]].astype(np.float64)
    return {
        "opaque": int(np.sum(opaque)),
        "baseline_rgb_mae": float(np.mean(np.abs(rgb - a))),
        "candidate_rgb_mae": float(np.mean(np.abs(rgb - b))),
        "baseline": color_islands(data["baseline_index"]),
        "candidate": color_islands(data["game_index"]),
        "candidate_counts": data["counts"],
    }

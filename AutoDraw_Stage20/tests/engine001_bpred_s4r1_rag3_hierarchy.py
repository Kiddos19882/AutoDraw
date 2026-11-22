#!/usr/bin/env python3
"""RAG3: source-only S4 main surfaces and nested protected detail colors.

Research E2. Every geometry/color is computed from the supplied original RGBA
and game128 swatches; NO historical artistic maps, outputs, strokes or labels.
This module never authorizes a production stroke or an Egret calibration.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage import color, measure

import engine001_bpred_s4r1_generic_source_maps as source


VERSION = "ENGINE001_BPRED_S4R1_RAG3_HIERARCHICAL_SOURCE_V1"
STRONG_LAB = 12.0
REGION_MEAN_LAB = 12.0
WEAK_BOUNDARY_STRONG_FRACTION = 0.125
CONFIRMED_SPLIT_MIN_AREA = 32
CONFIRMED_SPLIT_MIN_FRACTION = 0.20
CONFIRMED_SPLIT_MIN_EDGE = 8
CONFIRMED_SPLIT_EDGE_FRACTION = 0.5
DETAIL_RGB_IMPROVEMENT = 0.5
CHUNK = 65536


def _connected(values: np.ndarray) -> np.ndarray:
    """Treat equal integer labels as distinct unless connected by 4-neighbors."""
    return measure.label(values, background=0, connectivity=1).astype(np.int32)


def _boundary_stats(regions: np.ndarray, lab: np.ndarray):
    """All true opaque 4-neighbor RAG edges: count, mean and strong fraction."""
    n = int(regions.max()) + 1
    encoded, distances = [], []
    for a, b, la, lb in (
        (regions[:, :-1], regions[:, 1:], lab[:, :-1], lab[:, 1:]),
        (regions[:-1], regions[1:], lab[:-1], lab[1:]),
    ):
        valid = (a > 0) & (b > 0) & (a != b)
        if not np.any(valid):
            continue
        left, right = a[valid].astype(np.int64), b[valid].astype(np.int64)
        encoded.append(np.minimum(left, right) * n + np.maximum(left, right))
        distances.append(np.linalg.norm((la - lb)[valid], axis=1))
    if not encoded:
        return np.empty((0, 2), np.int32), np.empty(0, np.int64), np.empty(0), np.empty(0)
    keys = np.concatenate(encoded)
    contrast = np.concatenate(distances)
    unique, inverse, count = np.unique(keys, return_inverse=True, return_counts=True)
    total = np.bincount(inverse, weights=contrast, minlength=len(unique))
    strong = np.bincount(inverse, weights=(contrast >= STRONG_LAB),
                         minlength=len(unique))
    pair = np.column_stack((unique // n, unique % n)).astype(np.int32)
    return pair, count, total / count, strong / count


def _lab_means(labels: np.ndarray, lab: np.ndarray):
    n = int(labels.max())
    indices = labels[labels > 0]
    values = lab[labels > 0]
    counts = np.bincount(indices, minlength=n + 1).astype(np.int64)
    sums = np.column_stack([
        np.bincount(indices, weights=values[:, c], minlength=n + 1)
        for c in range(3)
    ])
    means = sums / np.maximum(counts[:, None], 1)
    return counts, sums, means


def _merge_slic(slic: np.ndarray, lab: np.ndarray):
    """One deterministic RAG pass: only weak real neighbors, never a color-ID join."""
    n = int(slic.max())
    counts, sums, means = _lab_means(slic, lab)
    pairs, length, boundary_mean, strong_fraction = _boundary_stats(slic, lab)
    parent = np.arange(n + 1, dtype=np.int32)
    weight = counts.copy()
    totals = sums.copy()

    def find(x: int) -> int:
        while int(parent[x]) != x:
            parent[x] = parent[int(parent[x])]
            x = int(parent[x])
        return x

    # Fixed order: strongest weak boundary first, then original IDs.
    ordering = sorted(range(len(pairs)), key=lambda i:
                      (float(boundary_mean[i]), -int(length[i]),
                       int(pairs[i, 0]), int(pairs[i, 1])))
    unions = 0
    for i in ordering:
        if (boundary_mean[i] > STRONG_LAB
                or strong_fraction[i] > WEAK_BOUNDARY_STRONG_FRACTION):
            continue
        a, b = find(int(pairs[i, 0])), find(int(pairs[i, 1]))
        if a == b:
            continue
        ma, mb = totals[a] / weight[a], totals[b] / weight[b]
        if np.linalg.norm(ma - mb) > REGION_MEAN_LAB:
            continue
        lo, hi = sorted((a, b))
        parent[hi] = lo
        weight[lo] += weight[hi]
        totals[lo] += totals[hi]
        unions += 1
    mapped = np.array([find(i) for i in range(n + 1)], dtype=np.int32)
    merged = _connected(mapped[slic])
    return merged, {"source_slic": n, "source_rag_edges": len(pairs),
                    "source_rag_unions": unions,
                    "merged_surfaces": int(merged.max())}


def _original_strong_edges(lab: np.ndarray, opaque: np.ndarray,
                           source_edges: np.ndarray):
    strong = source_edges.copy() & opaque
    for (a, b, left, right, opa, opb) in (
        (lab[:, :-1], lab[:, 1:], strong[:, :-1], strong[:, 1:],
         opaque[:, :-1], opaque[:, 1:]),
        (lab[:-1], lab[1:], strong[:-1], strong[1:],
         opaque[:-1], opaque[1:]),
    ):
        evidence = (np.linalg.norm(a - b, axis=2) >= STRONG_LAB) & opa & opb
        left[...] |= evidence
        right[...] |= evidence
    return strong


def _split_confirmed_source_edges(surfaces: np.ndarray, lab: np.ndarray,
                                  opaque: np.ndarray):
    """One source-supported split of sustained internal strong-edge sides.

    A candidate must have a connected, sizeable source-Lab-distinct side and
    a sustained observed strong interface. Small protected details stay in
    the detail layer, not in the main surface-ID namespace.
    """
    if not np.any(opaque):
        return surfaces, 0
    area, _, mean = _lab_means(surfaces, lab)
    deviation = np.linalg.norm(lab - mean[surfaces], axis=2)
    candidate = opaque & (deviation >= STRONG_LAB)
    parts = _connected(np.where(candidate, surfaces, 0).astype(np.int32))
    n = int(parts.max())
    if not n:
        return surfaces, 0
    sizes = np.bincount(parts.ravel(), minlength=n + 1)
    parents = np.zeros(n + 1, np.int32)
    parents[parts[candidate]] = surfaces[candidate]
    border = np.zeros(n + 1, np.int64)
    strong_border = np.zeros(n + 1, np.int64)
    for a, b, sa, sb, la, lb in (
        (parts[:, :-1], parts[:, 1:], surfaces[:, :-1], surfaces[:, 1:],
         lab[:, :-1], lab[:, 1:]),
        (parts[:-1], parts[1:], surfaces[:-1], surfaces[1:],
         lab[:-1], lab[1:]),
    ):
        distance = np.linalg.norm(la - lb, axis=2)
        for inside, outside in ((a, b), (b, a)):
            interface = (inside > 0) & (outside == 0) & (sa == sb) & (sa > 0)
            if np.any(interface):
                ids = inside[interface]
                border += np.bincount(ids, minlength=n + 1)
                strong_border += np.bincount(
                    ids, weights=(distance[interface] >= STRONG_LAB),
                    minlength=n + 1).astype(np.int64)
    accepted = (
        (sizes >= CONFIRMED_SPLIT_MIN_AREA)
        & (sizes >= CONFIRMED_SPLIT_MIN_FRACTION * area[parents])
        & (border >= CONFIRMED_SPLIT_MIN_EDGE)
        & (strong_border >= CONFIRMED_SPLIT_EDGE_FRACTION * np.maximum(border, 1))
    )
    accepted[0] = False
    count = int(np.count_nonzero(accepted))
    if not count:
        return surfaces, 0
    packed = surfaces.copy()
    selected = accepted[parts]
    packed[selected] = int(surfaces.max()) + parts[selected]
    return _connected(packed), count


def build_rag3(original_rgba: np.ndarray, game128: np.ndarray) -> dict:
    if (not isinstance(original_rgba, np.ndarray) or original_rgba.dtype != np.uint8
            or original_rgba.ndim != 3 or original_rgba.shape[2] != 4
            or min(original_rgba.shape[:2]) < 1
            or np.prod(original_rgba.shape[:2], dtype=np.int64) > source.MAX_PIXELS):
        raise ValueError("BLOCKED_RAG3_INVALID_ORIGINAL")
    if (not isinstance(game128, np.ndarray) or game128.dtype != np.uint8
            or game128.shape != (128, 3)
            or np.unique(game128, axis=0).shape[0] != 128):
        raise ValueError("BLOCKED_RAG3_INVALID_PALETTE")

    rgba = original_rgba
    h, w = rgba.shape[:2]
    opaque = rgba[:, :, 3] == 255
    index = np.full((h, w), -1, np.int16)
    base_index = index.copy()
    main_color = index.copy()
    preview = rgba.copy()
    empty = np.zeros((h, w), np.int32)
    if not np.any(opaque):
        return {
            "version": VERSION, "surface_id": empty, "detail_id": empty.copy(),
            "surface_color_index": main_color, "detail_parent_surface_id": np.zeros(1, np.int32),
            "detail_color_index": np.full(1, -1, np.int16),
            "game_index": index, "baseline_index": base_index,
            "preview_rgba": preview, "source_edge": np.zeros((h, w), bool),
            "unknown": np.ones((h, w), bool),
            "adjacency": np.empty((0, 2), np.int32),
            "counts": {"source_slic": 0, "source_rag_edges": 0,
                       "source_rag_unions": 0, "merged_surfaces": 0,
                       "confirmed_splits": 0, "main_surfaces": 0,
                       "detail_segments": 0, "detail_pixels": 0,
                       "game_colors": 0},
            "source_owner_status": "MISSING",
            "stroke_admission": "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE",
        }

    src = source.generic_source_maps(rgba)
    regions = source.original_source_region_uncertainty(rgba, src)
    slic = _connected(regions["region_ids"])
    if np.any(slic[opaque] <= 0) or np.any(slic[~opaque]):
        raise ValueError("BLOCKED_RAG3_SOURCE_ALPHA_OR_REGIONS")
    lab = color.rgb2lab(rgba[:, :, :3].astype(np.float64) / 255.0)
    palette_lab = color.rgb2lab(
        game128.reshape(1, 128, 3).astype(np.float64) / 255.0).reshape(128, 3)
    tree = cKDTree(palette_lab)
    source_edge = _original_strong_edges(lab, opaque, src["source_edge"])
    flat_indices = np.flatnonzero(opaque.ravel())
    lab_flat = lab.reshape(-1, 3)
    base_flat = base_index.ravel()
    for start in range(0, len(flat_indices), CHUNK):
        ids = flat_indices[start:start + CHUNK]
        base_flat[ids] = tree.query(lab_flat[ids], k=1, workers=1)[1].astype(np.int16)

    merged, stats = _merge_slic(slic, lab)
    surfaces, split_count = _split_confirmed_source_edges(merged, lab, opaque)
    main_n = int(surfaces.max())
    counts, sums, main_mean = _lab_means(surfaces, lab)
    # Mean may lie BETWEEN a narrow strong detail and its dominant source
    # background, causing both colors to be marked as one cancelling detail.
    # The actual source-Lab median is a robust surface-color anchor; it does
    # not import or partition by old game/pixel-nearest art labels.
    main_anchor = np.zeros_like(main_mean)
    for region_id, sl in enumerate(ndimage.find_objects(surfaces), start=1):
        if sl is None:
            raise ValueError("BLOCKED_RAG3_DISCONNECTED_MAIN_LABEL")
        local = surfaces[sl] == region_id
        main_anchor[region_id] = np.median(lab[sl][local], axis=0)
    main_table = np.full(main_n + 1, -1, np.int16)
    main_table[1:] = tree.query(main_anchor[1:], k=1, workers=1)[1].astype(np.int16)
    main_color[opaque] = main_table[surfaces[opaque]]
    index[opaque] = main_color[opaque]

    # A detail ID is a source-Lab-distinct 4-connected subregion of its parent.
    # It cannot create a new MAIN surface. Its color needs observed source edge
    # evidence plus actual RGB reconstruction improvement over its parent.
    deviation = np.linalg.norm(lab - main_anchor[surfaces], axis=2)
    candidate = opaque & (deviation >= STRONG_LAB)
    provisional = _connected(np.where(candidate, surfaces, 0).astype(np.int32))
    dcount = int(provisional.max())
    parents = np.zeros(dcount + 1, np.int32)
    if dcount:
        parents[provisional[candidate]] = surfaces[candidate]
    d_sizes, d_sums, d_means = _lab_means(provisional, lab)
    details_table = np.full(dcount + 1, -1, np.int16)
    admitted = np.zeros(dcount + 1, bool)
    if dcount:
        details_table[1:] = tree.query(d_means[1:], k=1, workers=1)[1].astype(np.int16)
        witnessed = np.bincount(provisional[candidate],
                                weights=source_edge[candidate].astype(np.int8),
                                minlength=dcount + 1) > 0
        valid = (witnessed &
                 (details_table != main_table[parents]) &
                 (np.linalg.norm(d_means - main_anchor[parents], axis=1) >= STRONG_LAB))
        valid[0] = False
        # Aggregate per-detail pixelwise RGB costs without any legacy map.
        ids = provisional[candidate]
        original_rgb = rgba[:, :, :3][candidate].astype(np.float64)
        old_rgb = game128[main_table[parents[ids]]].astype(np.float64)
        new_rgb = game128[details_table[ids]].astype(np.float64)
        diff = np.abs(original_rgb - old_rgb).mean(axis=1)
        improved = np.abs(original_rgb - new_rgb).mean(axis=1)
        old_sum = np.bincount(ids, weights=diff, minlength=dcount + 1)
        new_sum = np.bincount(ids, weights=improved, minlength=dcount + 1)
        admitted = valid & ((old_sum - new_sum) >= DETAIL_RGB_IMPROVEMENT * d_sizes)
        admitted[0] = False
    details = np.where(admitted[provisional], provisional, 0).astype(np.int32)
    selected = details > 0
    index[selected] = details_table[details[selected]]
    preview[opaque, :3] = game128[index[opaque]]
    adjacency, _, _, _ = _boundary_stats(surfaces, lab)
    if (np.any(details[~opaque]) or np.any(surfaces[~opaque])
            or np.any(index[~opaque] != -1)
            or not np.array_equal(preview[:, :, 3], rgba[:, :, 3])):
        raise ValueError("BLOCKED_RAG3_ALPHA_OR_PARENT_INVARIANT")
    if np.any(parents[details[selected]] != surfaces[selected]):
        raise ValueError("BLOCKED_RAG3_DETAIL_PARENT")
    return {
        "version": VERSION, "surface_id": surfaces, "detail_id": details,
        "surface_color_index": main_color, "surface_color_table": main_table,
        "detail_parent_surface_id": parents, "detail_color_index": details_table,
        "game_index": index, "baseline_index": base_index,
        "preview_rgba": preview, "source_edge": source_edge,
        "unknown": np.ones((h, w), bool), "adjacency": adjacency,
        "source_owner_status": "MISSING",
        "stroke_admission": "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE",
        "counts": {
            **stats, "confirmed_splits": split_count, "main_surfaces": main_n,
            "detail_segments": int(np.count_nonzero(admitted)),
            "detail_pixels": int(np.count_nonzero(selected)),
            "detail_candidate_segments": dcount,
            "detail_candidate_pixels": int(np.count_nonzero(candidate)),
            "game_colors": int(np.unique(index[opaque]).size),
            "opaque_pixels": int(np.count_nonzero(opaque)),
        },
    }


def _islands(index: np.ndarray) -> dict:
    singles, components = 0, 0
    for swatch in np.unique(index[index >= 0]):
        labels, n = ndimage.label(index == swatch, structure=np.ones((3, 3), bool))
        areas = np.bincount(labels.ravel())[1:]
        components += n
        singles += int(np.count_nonzero(areas == 1))
    return {"components": components, "singletons": singles}


def _retained_source_contrast(original: np.ndarray, game: np.ndarray,
                              opaque: np.ndarray):
    supported, retained, crossed = 0, 0, 0
    for a, b, ga, gb, mask_a, mask_b in (
        (original[:, :-1], original[:, 1:], game[:, :-1], game[:, 1:],
         opaque[:, :-1], opaque[:, 1:]),
        (original[:-1], original[1:], game[:-1], game[1:],
         opaque[:-1], opaque[1:]),
    ):
        valid = mask_a & mask_b
        true_edge = (np.linalg.norm(a - b, axis=2) >= STRONG_LAB) & valid
        mapped_edge = np.linalg.norm(ga - gb, axis=2) >= STRONG_LAB
        supported += int(np.count_nonzero(true_edge))
        retained += int(np.count_nonzero(true_edge & mapped_edge))
        crossed += int(np.count_nonzero(true_edge & ~mapped_edge))
    return {"source_strong_pairs": supported, "retained_pairs": retained,
            "missing_contrast_pairs": crossed,
            "retained_fraction": (retained / supported if supported else None)}


def evaluate_rag3(rgba: np.ndarray, game128: np.ndarray, data: dict) -> dict:
    opaque = rgba[:, :, 3] == 255
    report = {
        "opaque": int(np.count_nonzero(opaque)),
        "baseline": _islands(data["baseline_index"]),
        "candidate": _islands(data["game_index"]),
        "counts": data["counts"],
    }
    if not np.any(opaque):
        return report
    original_rgb = rgba[:, :, :3][opaque].astype(np.float64)
    before = game128[data["baseline_index"][opaque]].astype(np.float64)
    after = game128[data["game_index"][opaque]].astype(np.float64)
    src_lab = color.rgb2lab(rgba[:, :, :3].astype(np.float64) / 255)
    new_lab = color.rgb2lab(data["preview_rgba"][:, :, :3].astype(np.float64) / 255)
    report.update({
        "baseline_rgb_mae": float(np.abs(original_rgb - before).mean()),
        "candidate_rgb_mae": float(np.abs(original_rgb - after).mean()),
        "strong_source_contrast": _retained_source_contrast(src_lab, new_lab, opaque),
        "main_surface_adjacency_edges": int(len(data["adjacency"])),
    })
    return report

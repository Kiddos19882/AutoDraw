#!/usr/bin/env python3
"""RAG7 original-only connected source chroma modes, exact region-color L1.

All geometry and source chroma grouping recomputed from CURRENT original RGB
and alpha. RAG6 imported only for pure stateless source topology functions.
NEVER calls build_rag6 or consumes saved RAG1..RAG6 artistic images/maps.
No native game stroke or executor admission is implied.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage import color

import engine001_bpred_s4r1_generic_source_maps as source
import engine001_bpred_s4r1_rag3_hierarchy as original_geometry
import engine001_bpred_s4r1_rag6_edge_topology as original_edges


VERSION = "ENGINE001_BPRED_S4R1_RAG7_ORIGINAL_CHROMA_MODES_V1"
MODE_MIN_AREA = 24
MODE_MIN_SIDE = 8
MODE_MIN_FRACTION = 0.20
MODE_MIN_LAB_DELTA = 14.0
MODE_MIN_SSE_REDUCTION = 0.30
MODE_QUANTILES = (0.15, 0.85)
MODE_LLOYD_ITERATIONS = 5
MODE_BUDGET_FRACTION = 0.075
DETAIL_MIN_RGB_GAIN = 1.0
BASELINE_CHUNK = 65536


def _validate(original: np.ndarray, palette: np.ndarray) -> None:
    if (not isinstance(original, np.ndarray) or original.dtype != np.uint8
            or original.ndim != 3 or original.shape[-1] != 4
            or min(original.shape[:2]) < 1
            or int(np.prod(original.shape[:2], dtype=np.int64)) > source.MAX_PIXELS):
        raise ValueError("BLOCKED_RAG7_INVALID_ORIGINAL")
    if (not isinstance(palette, np.ndarray) or palette.dtype != np.uint8
            or palette.shape != (128, 3)
            or len(np.unique(palette, axis=0)) != 128):
        raise ValueError("BLOCKED_RAG7_INVALID_GAME_PALETTE")


def _blank(original: np.ndarray):
    h, w = original.shape[:2]
    zeros = np.zeros((h, w), np.int32)
    missing = np.full((h, w), -1, np.int16)
    return {
        "version": VERSION,
        "surface_id": zeros.copy(), "base_patch_id": zeros.copy(),
        "patch_id": zeros.copy(), "patch_parent_surface_id": np.zeros(1, np.int32),
        "patch_color_index": np.full(1, -1, np.int16),
        "edge_component_id": zeros.copy(), "detail_id": zeros.copy(),
        "detail_parent_surface_id": np.zeros(1, np.int32),
        "detail_color_index": np.full(1, -1, np.int16),
        "paintable_id": zeros.copy(), "game_index": missing.copy(),
        "baseline_index": missing.copy(), "preview_rgba": original.copy(),
        "source_edge": np.zeros((h, w), bool),
        "unknown": np.ones((h, w), bool),
        "adjacency": np.empty((0, 2), np.int32),
        "source_to_logical": source.letterbox_binding((w, h)),
        "source_owner_status": "MISSING",
        "stroke_admission": "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE",
        "counts": {
            "source_slic": 0, "source_rag_edges": 0, "source_rag_unions": 0,
            "confirmed_splits": 0, "main_surfaces": 0,
            "source_graph_regions": 0, "base_source_patches": 0,
            "mode_eligible": 0, "mode_accepted": 0, "mode_budget": 0,
            "refined_source_patches": 0, "edge_topology_pixels": 0,
            "edge_components": 0, "detail_components": 0, "detail_pixels": 0,
            "paintable_components": 0, "game_colors": 0, "opaque_pixels": 0,
        },
    }


def _connected_mode_proposal(patch_mask: np.ndarray,
                             patch_lab: np.ndarray):
    """One source-Lab PCA two-mode proposal; only real connected source sets.

    patch_mask: 2-D Boolean connected base-source patch crop.
    patch_lab: full RGB-derived Lab crop. No palette is touched.
    Returns (absolute SSE gain, Boolean mode-1 map) or None.
    """
    mask = np.asarray(patch_mask, dtype=bool)
    if int(mask.sum()) < MODE_MIN_AREA:
        return None
    points = patch_lab[mask].astype(np.float64)
    count = len(points)
    mean = points.mean(axis=0)
    centered = points - mean
    covariance = centered.T @ centered
    vals, vectors = np.linalg.eigh(covariance)
    axis = vectors[:, -1].copy()
    anchor = int(np.argmax(np.abs(axis)))
    if axis[anchor] < 0:
        axis = -axis
    projections = centered @ axis
    q0, q1 = np.quantile(projections, MODE_QUANTILES)
    if q1 - q0 < 1e-12:
        return None
    centers = mean[None, :] + np.array([q0, q1])[:, None] * axis[None, :]
    membership = np.zeros(count, bool)
    for _ in range(MODE_LLOYD_ITERATIONS):
        d0 = np.sum((points - centers[0]) ** 2, axis=1)
        d1 = np.sum((points - centers[1]) ** 2, axis=1)
        membership = d1 < d0  # ties consistently to mode 0
        if not np.any(membership) or np.all(membership):
            return None
        centers[0] = points[~membership].mean(axis=0)
        centers[1] = points[membership].mean(axis=0)
    # Determine final groups by the final centers, not the previous iteration.
    d0 = np.sum((points - centers[0]) ** 2, axis=1)
    d1 = np.sum((points - centers[1]) ** 2, axis=1)
    membership = d1 < d0
    n1 = int(membership.sum())
    n0 = count - n1
    if (min(n0, n1) < MODE_MIN_SIDE
            or min(n0, n1) < MODE_MIN_FRACTION * count):
        return None
    m0, m1 = points[~membership].mean(axis=0), points[membership].mean(axis=0)
    if np.linalg.norm(m1 - m0) < MODE_MIN_LAB_DELTA:
        return None
    sse_before = float(np.sum(centered ** 2))
    sse_after = float(np.sum((points[~membership] - m0) ** 2) +
                      np.sum((points[membership] - m1) ** 2))
    gain = sse_before - sse_after
    if not sse_before or gain < MODE_MIN_SSE_REDUCTION * sse_before:
        return None
    mode1 = np.zeros(mask.shape, bool)
    mode1[mask] = membership
    mode0 = mask & ~mode1
    # 4-neighbor spatial connection of EACH color mode is mandatory.
    connectivity = ndimage.generate_binary_structure(2, 1)
    if (ndimage.label(mode0, structure=connectivity)[1] != 1
            or ndimage.label(mode1, structure=connectivity)[1] != 1):
        return None
    return gain, mode1


def _source_mode_refine(base: np.ndarray, lab: np.ndarray):
    """Sparse, original-only, at most one 4-connected 2-way split per base patch."""
    n = int(base.max())
    mode_budget = int(np.floor(MODE_BUDGET_FRACTION * n))
    if not n:
        return base.copy(), {"mode_budget": 0, "mode_eligible": 0,
                             "mode_accepted": 0}
    proposals = []
    for rid, sl in enumerate(ndimage.find_objects(base), 1):
        if sl is None:
            raise ValueError("BLOCKED_RAG7_EMPTY_BASE_SOURCE_PATCH")
        mask = base[sl] == rid
        if int(mask.sum()) < MODE_MIN_AREA:
            continue
        answer = _connected_mode_proposal(mask, lab[sl])
        if answer is not None:
            benefit, mode1 = answer
            proposals.append((float(benefit), int(rid), sl, mode1))
    proposals.sort(key=lambda p: (-p[0], p[1]))
    selected = proposals[:mode_budget]
    packed = base.astype(np.int64) * 2
    for benefit, rid, sl, mode1 in selected:
        view = packed[sl]
        view[mode1] = 2 * rid + 1
    refined = original_geometry._connected(packed)
    if int(refined.max()) != n + len(selected):
        raise ValueError("BLOCKED_RAG7_MODE_SPLIT_NOT_CONNECTED")
    return refined, {
        "mode_eligible": len(proposals), "mode_accepted": len(selected),
        "mode_budget": mode_budget,
    }


def _best_whole_region_l1(samples: np.ndarray, palette: np.ndarray) -> int:
    """Exact min of sum |original RGB - swatch RGB| among ALL real 128 swatches.

    3-channel source 0..255 histograms + cumulative rank sums avoid Nx128
    large allocations and reproduce brute force loss without approximation.
    """
    if not isinstance(samples, np.ndarray) or samples.ndim != 2 or samples.shape[1] != 3:
        raise ValueError("BLOCKED_RAG7_INVALID_SOURCE_REGION_SAMPLES")
    if len(samples) == 0:
        raise ValueError("BLOCKED_RAG7_EMPTY_SOURCE_REGION")
    if samples.dtype != np.uint8:
        raise ValueError("BLOCKED_RAG7_NON_UINT8_RGB_SAMPLES")
    population = int(len(samples))
    candidate_cost = np.zeros(128, np.int64)
    levels = np.arange(256, dtype=np.int64)
    for channel in range(3):
        histogram = np.bincount(samples[:, channel], minlength=256).astype(np.int64)
        prefix_count = histogram.cumsum()
        prefix_rgb = (histogram * levels).cumsum()
        color_value = palette[:, channel].astype(np.int64)
        candidate_cost += (
            color_value * (2 * prefix_count[color_value] - population)
            + prefix_rgb[-1] - 2 * prefix_rgb[color_value]
        )
    return int(np.argmin(candidate_cost))


def _region_colors(rgba: np.ndarray, main: np.ndarray,
                   patches: np.ndarray, edge_groups: np.ndarray,
                   palette: np.ndarray):
    rgb = rgba[:, :, :3]
    num_patch = int(patches.max())
    parents = np.zeros(num_patch + 1, np.int32)
    colors = np.full(num_patch + 1, -1, np.int16)
    for rid, sl in enumerate(ndimage.find_objects(patches), 1):
        if sl is None:
            raise ValueError("BLOCKED_RAG7_EMPTY_REFINED_PATCH")
        selected = patches[sl] == rid
        original_pixels = rgb[sl][selected]
        main_parents = main[sl][selected]
        if not len(original_pixels) or not np.all(main_parents == main_parents[0]):
            raise ValueError("BLOCKED_RAG7_WRONG_PATCH_PARENT")
        parents[rid] = int(main_parents[0])
        colors[rid] = _best_whole_region_l1(original_pixels, palette)
    base_swatches = colors[patches]
    num_edges = int(edge_groups.max())
    allowed = np.zeros(num_edges + 1, bool)
    edge_parents = np.zeros(num_edges + 1, np.int32)
    edge_colors = np.full(num_edges + 1, -1, np.int16)
    for eid, sl in enumerate(ndimage.find_objects(edge_groups), 1):
        if sl is None:
            raise ValueError("BLOCKED_RAG7_EMPTY_EDGE_REGION")
        selected = edge_groups[sl] == eid
        original_pixels = rgb[sl][selected]
        original_parents = main[sl][selected]
        old_swatches = base_swatches[sl][selected]
        if not len(original_pixels) or not np.all(original_parents == original_parents[0]):
            raise ValueError("BLOCKED_RAG7_EDGE_PARENT")
        edge_parents[eid] = int(original_parents[0])
        new_swatch = _best_whole_region_l1(original_pixels, palette)
        # Compare exact whole-group L1 per source RGB channel, even if it
        # currently spans more than one source patch's base swatch.
        before = float(np.abs(
            original_pixels.astype(np.float64) -
            palette[old_swatches].astype(np.float64)).mean())
        after = float(np.abs(
            original_pixels.astype(np.float64) -
            palette[new_swatch].astype(np.float64)).mean())
        if np.any(old_swatches != new_swatch) and before - after >= DETAIL_MIN_RGB_GAIN:
            allowed[eid] = True
            edge_colors[eid] = new_swatch
    chosen = np.flatnonzero(allowed)
    remap = np.zeros(num_edges + 1, np.int32)
    remap[chosen] = np.arange(1, len(chosen) + 1, dtype=np.int32)
    detail_ids = remap[edge_groups]
    detail_parents = np.zeros(len(chosen) + 1, np.int32)
    detail_palette = np.full(len(chosen) + 1, -1, np.int16)
    detail_parents[1:] = edge_parents[chosen]
    detail_palette[1:] = edge_colors[chosen]
    return parents, colors, detail_ids, detail_parents, detail_palette


def build_rag7(original_rgba: np.ndarray, game128: np.ndarray) -> dict:
    _validate(original_rgba, game128)
    rgba = original_rgba
    h, w = rgba.shape[:2]
    opaque = rgba[:, :, 3] == 255
    if not np.any(opaque):
        return _blank(rgba)

    # Fresh original-source geometry ONLY. No previous artistic map is an input.
    source_maps = source.generic_source_maps(rgba)
    rough = source.original_source_region_uncertainty(rgba, source_maps)
    coarse = original_geometry._connected(rough["region_ids"])
    if np.any(coarse[opaque] <= 0) or np.any(coarse[~opaque]):
        raise ValueError("BLOCKED_RAG7_COARSE_ALPHA")
    lab = color.rgb2lab(rgba[:, :, :3].astype(np.float64) / 255)
    main_merged, main_stats = original_geometry._merge_slic(coarse, lab)
    main, nsplit = original_geometry._split_confirmed_source_edges(
        main_merged, lab, opaque)
    if np.any(main[opaque] <= 0) or np.any(main[~opaque]):
        raise ValueError("BLOCKED_RAG7_MAIN_ALPHA")

    original_graph = original_edges._source_graph(rgba, opaque)
    base, graph_stats = original_edges._merge_source_graph_within_main(
        original_graph, main, lab)
    refined, mode_stats = _source_mode_refine(base, lab)
    strong_edges = original_geometry._original_strong_edges(
        lab, opaque, source_maps["source_edge"])
    # Original-only true source edge geometry computed BEFORE any swatch.
    edge_groups, edge_stats = original_edges._original_edge_components(
        rgba, main, refined, lab, strong_edges)

    parents, patch_colors, detail_ids, detail_parents, detail_colors = (
        _region_colors(rgba, main, refined, edge_groups, game128))
    composed = np.full((h, w), -1, np.int16)
    composed[opaque] = patch_colors[refined[opaque]]
    has_detail = detail_ids > 0
    composed[has_detail] = detail_colors[detail_ids[has_detail]]

    # Fresh independent per-pixel nearest only for frozen quality comparison.
    game_lab = color.rgb2lab(
        game128.reshape((1, 128, 3)).astype(np.float64) / 255
    ).reshape(128, 3)
    tree = cKDTree(game_lab)
    baseline = np.full((h, w), -1, np.int16)
    selected_flat = np.flatnonzero(opaque.ravel())
    original_lab_flat = lab.reshape(-1, 3)
    baseline_flat = baseline.ravel()
    for start in range(0, len(selected_flat), BASELINE_CHUNK):
        pos = selected_flat[start:start + BASELINE_CHUNK]
        baseline_flat[pos] = tree.query(
            original_lab_flat[pos], k=1, workers=1)[1].astype(np.int16)

    encoded = np.zeros((h, w), np.int64)
    encoded[opaque] = main[opaque].astype(np.int64) * 128 + composed[opaque] + 1
    paintable = original_geometry._connected(encoded)
    neighbors, _, _, _ = original_geometry._boundary_stats(main, lab)
    preview = rgba.copy()
    preview[opaque, :3] = game128[composed[opaque]]
    if (
        np.any(main[~opaque]) or np.any(base[~opaque]) or np.any(refined[~opaque])
        or np.any(edge_groups[~opaque]) or np.any(detail_ids[~opaque])
        or np.any(paintable[~opaque]) or np.any(composed[~opaque] != -1)
        or np.any(baseline[~opaque] != -1)
        or np.any(parents[refined[opaque]] != main[opaque])
        or np.any(detail_parents[detail_ids[has_detail]] != main[has_detail])
        or np.any(detail_colors[detail_ids[has_detail]] != composed[has_detail])
        or not np.array_equal(preview[:, :, 3], rgba[:, :, 3])
    ):
        raise ValueError("BLOCKED_RAG7_SOURCE_ALPHA_OR_PARENT")
    return {
        "version": VERSION,
        "surface_id": main, "base_patch_id": base, "patch_id": refined,
        "patch_parent_surface_id": parents, "patch_color_index": patch_colors,
        "edge_component_id": edge_groups, "detail_id": detail_ids,
        "detail_parent_surface_id": detail_parents,
        "detail_color_index": detail_colors,
        "paintable_id": paintable, "game_index": composed,
        "baseline_index": baseline, "preview_rgba": preview,
        "source_edge": strong_edges, "unknown": np.ones((h, w), bool),
        "adjacency": neighbors,
        "source_to_logical": source.letterbox_binding((w, h)),
        "source_owner_status": "MISSING",
        "stroke_admission": "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE",
        "counts": {
            **main_stats, **graph_stats, **mode_stats, **edge_stats,
            "confirmed_splits": int(nsplit),
            "main_surfaces": int(main.max()),
            "source_graph_regions": int(original_graph.max()),
            "base_source_patches": int(base.max()),
            "refined_source_patches": int(refined.max()),
            "detail_components": int(len(detail_colors) - 1),
            "detail_pixels": int(np.count_nonzero(has_detail)),
            "paintable_components": int(paintable.max()),
            "game_colors": int(np.unique(composed[opaque]).size),
            "opaque_pixels": int(np.count_nonzero(opaque)),
        },
    }


def evaluate_rag7(rgba: np.ndarray, game128: np.ndarray, data: dict) -> dict:
    # Pure source-only metric on freshly generated RAG7 current-original arrays.
    return original_edges.evaluate_rag6(rgba, game128, data)

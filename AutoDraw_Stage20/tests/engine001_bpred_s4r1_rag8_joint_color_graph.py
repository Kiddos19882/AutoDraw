#!/usr/bin/env python3
"""ENGINE-001 RAG8: original-only chromatic graph + joint regional game128 cost.

RESEARCH E2, source only. Reads exactly current original RGB/alpha and caller's
genuine game128. Pure source geometry primitives recompute CURRENT source
arrays, never reads or calls previous RAG1-RAG7 build pipelines or their art.
The original graph topology is computed before any game swatch decisions.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage import color, segmentation

import engine001_bpred_s4r1_generic_source_maps as source
import engine001_bpred_s4r1_rag3_hierarchy as spatial
import engine001_bpred_s4r1_rag6_edge_topology as pure_source
import engine001_bpred_s4r1_rag7_source_color_modes as pure_color

VERSION = "ENGINE001_BPRED_S4R1_RAG8_ORIGINAL_JOINT_CHROMA_GRAPH_V1"
GRAPH_SCALE = 70
GRAPH_SIGMA = 0
GRAPH_MIN_SIZE = 4
CHROMA_WEIGHT = 1.6
SOURCE_MEAN_BOUNDARY = 10.0
SOURCE_STRONG_FRACTION = 0.10
SOURCE_REGION_MEAN_LAB = 12.0
JOINT_BOUNDARY_RGB_PENALTY = 12.0
EDGE_LAB = 12.0
DETAIL_RGB_IMPROVEMENT = 1.0
PALETTE_CHUNK = 4096
NEAREST_CHUNK = 65536


def _validate(rgba: np.ndarray, game128: np.ndarray) -> None:
    pure_source._validate(rgba, game128)


def _source_chromatic_graph(lab: np.ndarray, opaque: np.ndarray,
                           main: np.ndarray) -> np.ndarray:
    """Source CIE Lab contrast feature with extra chroma weight, NO PALETTE."""
    h, w = opaque.shape
    if min(h, w) < 2 or int(np.count_nonzero(opaque)) < 16:
        return spatial._connected(main.astype(np.int64))
    feature = np.empty((h, w, 3), dtype=np.float64)
    feature[:, :, 0] = np.clip(lab[:, :, 0] / 100.0, 0.0, 1.0)
    feature[:, :, 1] = np.clip(
        CHROMA_WEIGHT * (lab[:, :, 1] + 128.0) / 255.0, 0.0, CHROMA_WEIGHT)
    feature[:, :, 2] = np.clip(
        CHROMA_WEIGHT * (lab[:, :, 2] + 128.0) / 255.0, 0.0, CHROMA_WEIGHT)
    graph = segmentation.felzenszwalb(
        feature, scale=GRAPH_SCALE, sigma=GRAPH_SIGMA,
        min_size=GRAPH_MIN_SIZE, channel_axis=-1,
    ).astype(np.int64) + 1
    # SOURCE-ONLY chromatic primitives, intersect current original main and alpha.
    ids = np.zeros((h, w), np.int64)
    factor = int(main.max()) + 1
    ids[opaque] = graph[opaque] * factor + main[opaque]
    result = spatial._connected(ids)
    if np.any(result[~opaque] != 0) or np.any(result[opaque] < 1):
        raise ValueError("BLOCKED_RAG8_SOURCE_GRAPH_ALPHA")
    return result


def _full_palette_cost(rgb_pixels: np.ndarray, game128: np.ndarray) -> np.ndarray:
    """Exact whole-region all128 RGB L1 sums in int64, not nearest pixel seeds."""
    if len(rgb_pixels) < 1:
        raise ValueError("BLOCKED_RAG8_EMPTY_REGIONAL_COST")
    costs = np.zeros(128, np.int64)
    palette = game128.astype(np.int16)
    for off in range(0, len(rgb_pixels), PALETTE_CHUNK):
        pixels = rgb_pixels[off:off + PALETTE_CHUNK].astype(np.int16)
        costs += np.abs(pixels[:, None, :] - palette[None, :, :]).sum(
            axis=(0, 2), dtype=np.int64)
    return costs


def _source_region_costs(graph: np.ndarray, rgb: np.ndarray,
                         game128: np.ndarray) -> np.ndarray:
    costs = np.zeros((int(graph.max()) + 1, 128), np.int64)
    for rid, sl in enumerate(ndimage.find_objects(graph), 1):
        if sl is None:
            raise ValueError("BLOCKED_RAG8_DISCONNECTED_SOURCE_GRAPH")
        pixels = rgb[sl][graph[sl] == rid]
        if not len(pixels):
            raise ValueError("BLOCKED_RAG8_EMPTY_SOURCE_GRAPH_REGION")
        costs[rid] = _full_palette_cost(pixels, game128)
    return costs


def _joint_source_regional_optimization(
    graph: np.ndarray, main: np.ndarray, lab: np.ndarray, rgb: np.ndarray,
    palette: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict]:
    """One ranked pass: REAL source 4-neighbor topology jointly with all128 costs.

    The primitive graph is constructed without palette input; the shared
    128-vector determines only original-connected weak-boundary merges.
    """
    n = int(graph.max())
    if not n:
        z = np.zeros_like(graph, np.int32)
        return z, np.zeros(1, np.int32), np.full(1, -1, np.int16), z, {
            "source_graph_regions": 0, "joint_boundary_pairs": 0,
            "joint_attempts": 0, "joint_accepted_merges": 0,
            "joint_rejected_source": 0, "joint_rejected_loss": 0,
            "joint_loss_total_rgb": 0,
        }
    counts, totals, _ = spatial._lab_means(graph, lab)
    cost = _source_region_costs(graph, rgb, palette)
    pairs, length, source_edge, strong = spatial._boundary_stats(graph, lab)
    parents = np.zeros(n + 1, np.int32)
    opaque = graph > 0
    parents[graph[opaque]] = main[opaque]
    if np.any(parents[graph[opaque]] != main[opaque]):
        raise ValueError("BLOCKED_RAG8_SOURCE_GRAPH_PARENT")

    uf = np.arange(n + 1, dtype=np.int32)
    mass = counts.copy()
    lab_sum = totals.copy()
    stats = {
        "source_graph_regions": n, "joint_boundary_pairs": int(len(pairs)),
        "joint_attempts": 0, "joint_accepted_merges": 0,
        "joint_rejected_source": 0, "joint_rejected_loss": 0,
        "joint_loss_total_rgb": 0,
    }

    def root(idx: int) -> int:
        while int(uf[idx]) != idx:
            uf[idx] = uf[int(uf[idx])]
            idx = int(uf[idx])
        return idx

    sorted_edges = sorted(range(len(pairs)), key=lambda i:
                          (float(source_edge[i]), -int(length[i]),
                           int(pairs[i, 0]), int(pairs[i, 1])))
    for idx in sorted_edges:
        a, b = int(pairs[idx, 0]), int(pairs[idx, 1])
        if parents[a] != parents[b]:
            continue
        stats["joint_attempts"] += 1
        if (float(source_edge[idx]) > SOURCE_MEAN_BOUNDARY
                or float(strong[idx]) > SOURCE_STRONG_FRACTION):
            stats["joint_rejected_source"] += 1
            continue
        a, b = root(a), root(b)
        if a == b:
            continue
        source_shift = float(np.linalg.norm(
            lab_sum[a] / mass[a] - lab_sum[b] / mass[b]))
        if source_shift > SOURCE_REGION_MEAN_LAB:
            stats["joint_rejected_source"] += 1
            continue
        new_cost = cost[a] + cost[b]
        loss_increase = (int(new_cost.min())
                         - int(cost[a].min()) - int(cost[b].min()))
        if loss_increase > JOINT_BOUNDARY_RGB_PENALTY * int(length[idx]):
            stats["joint_rejected_loss"] += 1
            continue
        left, right = sorted((a, b))
        uf[right] = left
        cost[left] = new_cost
        mass[left] += mass[right]
        lab_sum[left] += lab_sum[right]
        stats["joint_accepted_merges"] += 1
        stats["joint_loss_total_rgb"] += loss_increase

    canonical = np.array([root(x) for x in range(n + 1)], np.int32)
    canonical_grid = canonical[graph]
    patch_id = spatial._connected(canonical_grid)
    num = int(patch_id.max())
    patch_roots = np.zeros(num + 1, np.int32)
    patch_roots[patch_id[opaque]] = canonical_grid[opaque]
    color_index = np.full(num + 1, -1, np.int16)
    parent_main = np.zeros(num + 1, np.int32)
    color_index[1:] = np.argmin(cost[patch_roots[1:]], axis=1).astype(np.int16)
    parent_main[patch_id[opaque]] = main[opaque]
    if (np.any(parent_main[patch_id[opaque]] != main[opaque])
            or np.any(patch_id[~opaque])):
        raise ValueError("BLOCKED_RAG8_MERGE_PARENT")
    stats["joint_patches"] = num
    return patch_id, parent_main, color_index, canonical_grid, stats


def _blank(original_rgba: np.ndarray) -> dict:
    d = pure_source._empty(original_rgba)
    d["version"] = VERSION
    d["source_graph_id"] = np.zeros(original_rgba.shape[:2], np.int32)
    d["source_joint_root"] = np.zeros(original_rgba.shape[:2], np.int32)
    d["counts"].update({
        "source_graph_regions": 0, "joint_boundary_pairs": 0,
        "joint_attempts": 0, "joint_accepted_merges": 0,
        "joint_rejected_source": 0, "joint_rejected_loss": 0,
        "joint_loss_total_rgb": 0,
    })
    return d


def build_rag8(original_rgba: np.ndarray, game128: np.ndarray) -> dict:
    _validate(original_rgba, game128)
    rgba = original_rgba
    h, w = rgba.shape[:2]
    opaque = rgba[:, :, 3] == 255
    if not opaque.any():
        return _blank(rgba)

    # Every operation below re-generates source topology from current original.
    # NEVER call build_rag6/build_rag7 or read cached derived art as input.
    original_maps = source.generic_source_maps(rgba)
    coarse = source.original_source_region_uncertainty(rgba, original_maps)
    coarse_labels = spatial._connected(coarse["region_ids"])
    if np.any(coarse_labels[opaque] < 1) or np.any(coarse_labels[~opaque]):
        raise ValueError("BLOCKED_RAG8_ORIGINAL_COARSE_ALPHA")
    lab = color.rgb2lab(rgba[:, :, :3].astype(np.float64) / 255.0)
    main_merged, main_stats = spatial._merge_slic(coarse_labels, lab)
    main, split_count = spatial._split_confirmed_source_edges(
        main_merged, lab, opaque)

    # NEW ORIGINAL source-only chroma graph, completely independent of palette.
    graph = _source_chromatic_graph(lab, opaque, main)
    patches, parent, region_color, joint_roots, joint_stats = (
        _joint_source_regional_optimization(
            graph, main, lab, rgba[:, :, :3], game128))

    source_strong_edge = spatial._original_strong_edges(
        lab, opaque, original_maps["source_edge"])
    detail_groups, detail_graph_stats = pure_source._original_edge_components(
        rgba, main, patches, lab, source_strong_edge)
    # Stateless pure original-source detail RGB L1: no historic preview input.
    detail_id, detail_parent, detail_color = pure_color._assign_original_detail(
        rgba, main, patches, detail_groups, region_color, game128)

    composed = np.full((h, w), -1, np.int16)
    composed[opaque] = region_color[patches[opaque]]
    on_detail = detail_id > 0
    composed[on_detail] = detail_color[detail_id[on_detail]]

    palette_lab = color.rgb2lab(
        game128.reshape(1, 128, 3).astype(np.float64) / 255.0
    ).reshape(128, 3)
    tree = cKDTree(palette_lab)
    baseline = np.full((h, w), -1, np.int16)
    indices = np.flatnonzero(opaque.ravel())
    flat_lab = lab.reshape(-1, 3)
    base_flat = baseline.ravel()
    for off in range(0, len(indices), NEAREST_CHUNK):
        current = indices[off:off + NEAREST_CHUNK]
        base_flat[current] = tree.query(
            flat_lab[current], k=1, workers=1)[1].astype(np.int16)
    packed = np.zeros((h, w), np.int64)
    packed[opaque] = main[opaque].astype(np.int64) * 128 + composed[opaque] + 1
    paintable = spatial._connected(packed)
    adjacency, _, _, _ = spatial._boundary_stats(main, lab)
    preview = rgba.copy()
    preview[opaque, :3] = game128[composed[opaque]]

    if (np.any(main[~opaque]) or np.any(graph[~opaque])
            or np.any(patches[~opaque]) or np.any(detail_groups[~opaque])
            or np.any(detail_id[~opaque]) or np.any(paintable[~opaque])
            or np.any(composed[~opaque] != -1)
            or np.any(baseline[~opaque] != -1)
            or np.any(parent[patches[opaque]] != main[opaque])
            or np.any(detail_parent[detail_id[on_detail]] != main[on_detail])
            or np.any(detail_color[detail_id[on_detail]] != composed[on_detail])
            or not np.array_equal(preview[:, :, 3], rgba[:, :, 3])):
        raise ValueError("BLOCKED_RAG8_PARENT_ALPHA_COLOR")

    return {
        "version": VERSION, "surface_id": main,
        "source_graph_id": graph, "source_joint_root": joint_roots,
        "edge_component_id": detail_groups,
        "patch_id": patches, "patch_parent_surface_id": parent,
        "patch_color_index": region_color,
        "detail_id": detail_id, "detail_parent_surface_id": detail_parent,
        "detail_color_index": detail_color,
        "paintable_id": paintable, "game_index": composed,
        "baseline_index": baseline, "preview_rgba": preview,
        "source_edge": source_strong_edge,
        "unknown": np.ones((h, w), bool),
        "adjacency": adjacency,
        "source_to_logical": source.letterbox_binding((w, h)),
        "source_owner_status": "MISSING",
        "stroke_admission": "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE",
        "counts": {
            **main_stats, **joint_stats, **detail_graph_stats,
            "confirmed_splits": int(split_count),
            "main_surfaces": int(main.max()),
            "patches": int(patches.max()),
            "edge_components": int(detail_graph_stats["edge_components"]),
            "detail_components": int(detail_color.size - 1),
            "detail_pixels": int(on_detail.sum()),
            "paintable_components": int(paintable.max()),
            "game_colors": int(np.unique(composed[opaque]).size),
            "opaque_pixels": int(opaque.sum()),
        },
    }


def evaluate_rag8(rgba: np.ndarray, game128: np.ndarray,
                  data: dict) -> dict:
    return pure_source.evaluate_rag6(rgba, game128, data)

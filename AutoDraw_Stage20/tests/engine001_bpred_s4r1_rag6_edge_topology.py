#!/usr/bin/env python3
"""RAG6 E2 RESEARCH ONLY: original edge-topology before choosing any game colors.

Original RGB/alpha + real game128 are the only art inputs. Pure previously
tested source functions operate on this CURRENT original; NO historical maps,
previews, palette-owner image, strokes or native data are read. All output
colors/IDs are new, with UNKNOWN and forbidden executor admission.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage import color, segmentation

import engine001_bpred_s4r1_generic_source_maps as source
import engine001_bpred_s4r1_rag3_hierarchy as original_graph
import engine001_bpred_s4r1_rag5_source_multiscale as source_utils


VERSION = "ENGINE001_BPRED_S4R1_RAG6_SOURCE_EDGE_TOPOLOGY_V1"
GRAPH_SCALE = 70
GRAPH_SIGMA = 0
GRAPH_MIN_SIZE = 4
MERGE_BORDER_LAB = 10.0
MERGE_STRONG_FRACTION = 0.10
MERGE_REGION_LAB = 10.0
EDGE_LAB = 12.0
EDGE_REGION_DEVIATION = 12.0
EDGE_LOCAL_DEVIATION = 12.0
EDGE_WITHIN_GROUP_LAB = 12.0
MIN_DETAIL_RGB_IMPROVEMENT = 1.0
CHUNK = 65536


def _validate(rgba: np.ndarray, palette: np.ndarray) -> None:
    if (not isinstance(rgba, np.ndarray) or rgba.ndim != 3
            or rgba.shape[-1] != 4 or rgba.dtype != np.uint8
            or min(rgba.shape[:2]) < 1
            or int(np.prod(rgba.shape[:2], dtype=np.int64)) > source.MAX_PIXELS):
        raise ValueError("BLOCKED_RAG6_INVALID_ORIGINAL")
    if (not isinstance(palette, np.ndarray) or palette.dtype != np.uint8
            or palette.shape != (128, 3)
            or len(np.unique(palette, axis=0)) != 128):
        raise ValueError("BLOCKED_RAG6_INVALID_GAME_PALETTE")


def _empty(rgba: np.ndarray) -> dict:
    h, w = rgba.shape[:2]
    z = np.zeros((h, w), np.int32)
    missing = np.full((h, w), -1, np.int16)
    return {
        "version": VERSION, "surface_id": z.copy(),
        "edge_component_id": z.copy(), "patch_id": z.copy(),
        "patch_parent_surface_id": np.zeros(1, np.int32),
        "patch_color_index": np.full(1, -1, np.int16),
        "detail_id": z.copy(),
        "detail_parent_surface_id": np.zeros(1, np.int32),
        "detail_color_index": np.full(1, -1, np.int16),
        "paintable_id": z.copy(), "game_index": missing.copy(),
        "baseline_index": missing.copy(), "preview_rgba": rgba.copy(),
        "source_edge": np.zeros((h, w), bool),
        "unknown": np.ones((h, w), bool),
        "adjacency": np.empty((0, 2), np.int32),
        "source_to_logical": source.letterbox_binding((w, h)),
        "source_owner_status": "MISSING",
        "stroke_admission": "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE",
        "counts": {"main_surfaces": 0, "graph_regions": 0, "initial_patch_regions": 0,
                   "patch_unions": 0, "patches": 0,
                   "edge_topology_pixels": 0, "edge_components": 0,
                   "detail_components": 0, "detail_pixels": 0,
                   "paintable_components": 0, "game_colors": 0,
                   "opaque_pixels": 0},
    }


def _source_graph(rgba: np.ndarray, opaque: np.ndarray) -> np.ndarray:
    """Build original-neighbor-weighted image segments BEFORE game palette lookup."""
    h, w = opaque.shape
    if min(h, w) < 2 or int(opaque.sum()) < 16:
        return ndimage.label(opaque, structure=ndimage.generate_binary_structure(2, 1))[0].astype(np.int32)
    graph = segmentation.felzenszwalb(
        rgba[:, :, :3].astype(np.float64) / 255.0,
        scale=GRAPH_SCALE, sigma=GRAPH_SIGMA, min_size=GRAPH_MIN_SIZE,
        channel_axis=-1,
    )
    graph = np.asarray(graph, dtype=np.int64) + 1
    graph[~opaque] = 0
    return original_graph._connected(graph)


def _merge_source_graph_within_main(graph: np.ndarray, main: np.ndarray,
                                    lab: np.ndarray):
    """Merge original graph components only on weak REAL source neighbor borders."""
    opaque = main > 0
    factor = int(main.max()) + 1
    ids = np.zeros(main.shape, np.int64)
    ids[opaque] = graph[opaque].astype(np.int64) * factor + main[opaque]
    initial = original_graph._connected(ids)
    n = int(initial.max())
    if not n:
        return initial, {"initial_patch_regions": 0, "patch_unions": 0}
    parents = np.zeros(n + 1, np.int32)
    parents[initial[opaque]] = main[opaque]
    sizes, total, _ = original_graph._lab_means(initial, lab)
    pair, length, mean_edge, strong_fraction = original_graph._boundary_stats(initial, lab)
    uf = np.arange(n + 1, dtype=np.int32)
    mass = sizes.copy()
    weights = total.copy()

    def find(idx: int) -> int:
        while int(uf[idx]) != idx:
            uf[idx] = uf[int(uf[idx])]
            idx = int(uf[idx])
        return idx

    ordering = sorted(range(len(pair)), key=lambda i:
                      (float(mean_edge[i]), -int(length[i]),
                       int(pair[i, 0]), int(pair[i, 1])))
    accepted = 0
    for i in ordering:
        a, b = int(pair[i, 0]), int(pair[i, 1])
        if parents[a] != parents[b]:
            continue
        if mean_edge[i] > MERGE_BORDER_LAB or strong_fraction[i] > MERGE_STRONG_FRACTION:
            continue
        a, b = find(a), find(b)
        if a == b:
            continue
        if np.linalg.norm(weights[a] / mass[a] - weights[b] / mass[b]) > MERGE_REGION_LAB:
            continue
        left, right = sorted((a, b))
        uf[right] = left
        mass[left] += mass[right]
        weights[left] += weights[right]
        accepted += 1
    canonical = np.array([find(i) for i in range(n + 1)], np.int32)
    final = original_graph._connected(canonical[initial])
    if np.any(final[opaque] < 1) or np.any(final[~opaque]):
        raise ValueError("BLOCKED_RAG6_SOURCE_PATCH_ALPHA")
    return final, {"initial_patch_regions": n, "patch_unions": accepted}


def _local_original_lab_average(lab: np.ndarray, main: np.ndarray):
    """4-neighbor LAB average within THIS original main surface; no palette."""
    neighbors = np.zeros_like(lab)
    counts = np.zeros(main.shape, np.float64)
    for a, b, la, lb, na, nb, ca, cb in (
        (main[:, :-1], main[:, 1:], lab[:, :-1], lab[:, 1:],
         neighbors[:, :-1], neighbors[:, 1:],
         counts[:, :-1], counts[:, 1:]),
        (main[:-1], main[1:], lab[:-1], lab[1:],
         neighbors[:-1], neighbors[1:],
         counts[:-1], counts[1:]),
    ):
        valid = (a > 0) & (a == b)
        na[valid] += lb[valid]
        nb[valid] += la[valid]
        ca[valid] += 1
        cb[valid] += 1
    local = lab.copy()
    positive = counts > 0
    local[positive] = neighbors[positive] / counts[positive, None]
    return local


def _original_edge_components(rgba: np.ndarray, main: np.ndarray,
                              patches: np.ndarray, lab: np.ndarray,
                              source_edge: np.ndarray):
    """Compute source-only contrast-side topology BEFORE palette swatch assignment."""
    n = int(patches.max())
    median_lab = np.zeros((n + 1, 3), np.float64)
    for region, sl in enumerate(ndimage.find_objects(patches), 1):
        if sl is None:
            raise ValueError("BLOCKED_RAG6_EMPTY_PATCH")
        samples = rgba[:, :, :3][sl][patches[sl] == region]
        median_rgb = np.median(samples, axis=0) / 255.0
        median_lab[region] = color.rgb2lab(median_rgb.reshape(1, 1, 3)).reshape(3)
    local_lab = _local_original_lab_average(lab, main)
    candidates = (
        (main > 0) & source_edge &
        (np.linalg.norm(lab - median_lab[patches], axis=2) >= EDGE_REGION_DEVIATION) &
        (np.linalg.norm(lab - local_lab, axis=2) >= EDGE_LOCAL_DEVIATION)
    )
    # Pure original source Lab neighbors, true 4-connectivity and parent MAIN.
    groups, count = source_utils._connected_source_detail_candidates(
        candidates, main, lab)
    return groups, {"edge_topology_pixels": int(candidates.sum()),
                    "edge_components": int(count)}


def _assign_source_colors(
    rgba: np.ndarray, main: np.ndarray, patches: np.ndarray,
    edge_groups: np.ndarray, palette: np.ndarray,
    palette_lab: np.ndarray, tree: cKDTree
):
    """All region and detail candidates derived from real source RGB, not nearest map."""
    num_patch = int(patches.max())
    parent = np.zeros(num_patch + 1, np.int32)
    patch_colors = np.full(num_patch + 1, -1, np.int16)
    rgb = rgba[:, :, :3]
    for rid, sl in enumerate(ndimage.find_objects(patches), 1):
        if sl is None:
            raise ValueError("BLOCKED_RAG6_MISSING_PATCH")
        mask = patches[sl] == rid
        pixels = rgb[sl][mask]
        mains = main[sl][mask]
        if not len(pixels) or not np.all(mains == mains[0]):
            raise ValueError("BLOCKED_RAG6_PATCH_PARENT")
        parent[rid] = int(mains[0])
        patch_colors[rid] = source_utils._choose_color(
            pixels, palette, palette_lab, tree)
    base_swatches = patch_colors[patches]

    n = int(edge_groups.max())
    accepted = np.zeros(n + 1, bool)
    target_color = np.full(n + 1, -1, np.int16)
    detail_parent = np.zeros(n + 1, np.int32)
    for rid, sl in enumerate(ndimage.find_objects(edge_groups), 1):
        if sl is None:
            raise ValueError("BLOCKED_RAG6_MISSING_EDGE_GROUP")
        mask = edge_groups[sl] == rid
        pixels = rgb[sl][mask]
        mains = main[sl][mask]
        old = base_swatches[sl][mask]
        if not len(pixels) or not np.all(mains == mains[0]):
            raise ValueError("BLOCKED_RAG6_DETAIL_PARENT")
        detail_parent[rid] = int(mains[0])
        proposed = source_utils._choose_color(pixels, palette, palette_lab, tree)
        old_loss = float(np.abs(pixels.astype(np.float64) -
                                palette[old].astype(np.float64)).mean())
        next_loss = float(np.abs(pixels.astype(np.float64) -
                                 palette[proposed].astype(np.float64)).mean())
        if (np.any(old != proposed)
                and old_loss - next_loss >= MIN_DETAIL_RGB_IMPROVEMENT):
            accepted[rid] = True
            target_color[rid] = int(proposed)

    keep = np.flatnonzero(accepted)
    new_ids = np.zeros(n + 1, np.int32)
    new_ids[keep] = np.arange(1, len(keep) + 1, dtype=np.int32)
    detail_id = new_ids[edge_groups]
    parents = np.zeros(len(keep) + 1, np.int32)
    colors = np.full(len(keep) + 1, -1, np.int16)
    parents[1:] = detail_parent[keep]
    colors[1:] = target_color[keep]
    return parent, patch_colors, detail_id, parents, colors


def build_rag6(original_rgba: np.ndarray, game128: np.ndarray) -> dict:
    _validate(original_rgba, game128)
    rgba = original_rgba
    h, w = rgba.shape[:2]
    opaque = rgba[:, :, 3] == 255
    if not opaque.any():
        return _empty(rgba)

    original_maps = source.generic_source_maps(rgba)
    coarse = source.original_source_region_uncertainty(rgba, original_maps)
    coarse_label = original_graph._connected(coarse["region_ids"])
    if np.any(coarse_label[opaque] <= 0) or np.any(coarse_label[~opaque]):
        raise ValueError("BLOCKED_RAG6_COARSE_SOURCE_ALPHA")
    lab = color.rgb2lab(rgba[:, :, :3].astype(np.float64) / 255.0)
    merged, main_stats = original_graph._merge_slic(coarse_label, lab)
    main, split_count = original_graph._split_confirmed_source_edges(
        merged, lab, opaque)

    # This original RGB graph is built BEFORE any game swatch lookup.
    graph = _source_graph(rgba, opaque)
    patches, patch_stats = _merge_source_graph_within_main(graph, main, lab)
    strong = original_graph._original_strong_edges(lab, opaque,
                                                    original_maps["source_edge"])
    edge_components, edge_stats = _original_edge_components(
        rgba, main, patches, lab, strong)

    palette_lab = color.rgb2lab(
        game128.reshape(1, 128, 3).astype(np.float64) / 255.0).reshape(128, 3)
    tree = cKDTree(palette_lab)
    parent, patch_colors, detail_id, d_parent, d_color = _assign_source_colors(
        rgba, main, patches, edge_components, game128, palette_lab, tree)
    # Palette mapping is downstream of BOTH original topologies, never a seed.
    composed = np.full((h, w), -1, np.int16)
    composed[opaque] = patch_colors[patches[opaque]]
    details = detail_id > 0
    composed[details] = d_color[detail_id[details]]

    # Independent nearest original Lab baseline ONLY for source quality screen.
    baseline = np.full((h, w), -1, np.int16)
    idx = np.flatnonzero(opaque.ravel())
    flat_lab = lab.reshape(-1, 3)
    for off in range(0, len(idx), CHUNK):
        pos = idx[off:off + CHUNK]
        baseline.ravel()[pos] = tree.query(
            flat_lab[pos], k=1, workers=1)[1].astype(np.int16)
    packed = np.zeros((h, w), np.int64)
    packed[opaque] = main[opaque].astype(np.int64) * 128 + composed[opaque] + 1
    paintable = original_graph._connected(packed)
    main_adjacency, _, _, _ = original_graph._boundary_stats(main, lab)
    preview = rgba.copy()
    preview[opaque, :3] = game128[composed[opaque]]

    if (
        np.any(main[~opaque]) or np.any(patches[~opaque]) or
        np.any(edge_components[~opaque]) or np.any(detail_id[~opaque]) or
        np.any(paintable[~opaque]) or np.any(composed[~opaque] != -1) or
        np.any(baseline[~opaque] != -1) or
        np.any(parent[patches[opaque]] != main[opaque]) or
        np.any(d_parent[detail_id[details]] != main[details]) or
        np.any(d_color[detail_id[details]] != composed[details]) or
        not np.array_equal(preview[:, :, 3], rgba[:, :, 3])
    ):
        raise ValueError("BLOCKED_RAG6_SOURCE_PARENT_ALPHA_OR_SWATCH")

    return {
        "version": VERSION, "surface_id": main,
        "edge_component_id": edge_components, "patch_id": patches,
        "patch_parent_surface_id": parent, "patch_color_index": patch_colors,
        "detail_id": detail_id, "detail_parent_surface_id": d_parent,
        "detail_color_index": d_color, "paintable_id": paintable,
        "game_index": composed, "baseline_index": baseline,
        "preview_rgba": preview, "source_edge": strong,
        "unknown": np.ones((h, w), bool),
        "adjacency": main_adjacency,
        "source_to_logical": source.letterbox_binding((w, h)),
        "source_owner_status": "MISSING",
        "stroke_admission": "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE",
        "counts": {
            **main_stats, **patch_stats, **edge_stats,
            "confirmed_splits": int(split_count),
            "main_surfaces": int(main.max()),
            "graph_regions": int(graph.max()),
            "patches": int(patches.max()),
            "detail_components": int(len(d_color) - 1),
            "detail_pixels": int(np.count_nonzero(details)),
            "paintable_components": int(paintable.max()),
            "game_colors": int(np.unique(composed[opaque]).size),
            "opaque_pixels": int(np.count_nonzero(opaque)),
        },
    }


def evaluate_rag6(rgba: np.ndarray, game128: np.ndarray, data: dict) -> dict:
    # Reuse a metric that measures the SAME nearest128 RGB/singletons/edge pairs
    # as RAG5, but on completely newly generated ORIGINAL-ONLY RAG6 layers.
    return source_utils.evaluate_rag5(rgba, game128, data)

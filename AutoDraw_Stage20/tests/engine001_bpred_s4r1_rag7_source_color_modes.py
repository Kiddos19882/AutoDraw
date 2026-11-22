#!/usr/bin/env python3
"""RAG7: source-only chromatic color modes within independent edge-first source regions.

Never reads/uses RAG1-RAG6 derived art. Source graph/edge helper functions are
called ONLY with the current, immutable original RGB/alpha; game128 never
seeds geometry. This is S4 source E2 research, NOT native brush safety/admission.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage import color

import engine001_bpred_s4r1_generic_source_maps as source
import engine001_bpred_s4r1_rag3_hierarchy as spatial
import engine001_bpred_s4r1_rag6_edge_topology as original_graph


VERSION = "ENGINE001_BPRED_S4R1_RAG7_SOURCE_CHROMATIC_MODES_V1"
MIN_MODE_PARENT_AREA = 32
LAB_CENTROID_SEPARATION = 16.0
MIN_MODE_SHARE = 0.20
MIN_MODE_REGION_AREA = 12
MIN_MODE_CONNECTED_SHARE = 0.15
MIN_MODE_INTERFACE_PAIRS = 8
MIN_MODE_INTERFACE_LAB = 8.0
MIN_MODE_INTERFACE_STRONG_FRACTION = 0.20
SOURCE_STRONG_LAB = 12.0
KMEANS_ITERATIONS = 4
MODE_LOSS_IMPROVEMENT_RGB = 1.0
DETAIL_LOSS_IMPROVEMENT_RGB = 1.0
PALETTE_CHUNK = 4096
CHUNK = 65536


def _validate(rgba: np.ndarray, palette: np.ndarray) -> None:
    original_graph._validate(rgba, palette)


def _blank(rgba: np.ndarray) -> dict:
    empty = original_graph._empty(rgba)
    empty["version"] = VERSION
    shape = rgba.shape[:2]
    empty["source_patch_id"] = np.zeros(shape, np.int32)
    empty["source_mode_id"] = np.zeros(shape, np.int32)
    empty["counts"].update({
        "mode_patches_considered": 0, "mode_candidates": 0,
        "mode_reject_source": 0, "mode_reject_spatial": 0,
        "mode_reject_rgb": 0, "mode_splits_accepted": 0,
        "mode_pixels": 0,
    })
    return empty


def _best_palette(source_rgb: np.ndarray, palette: np.ndarray) -> tuple[int, float]:
    """Find original-RGB L1 minimum across all real swatches, not median-only 5."""
    n = len(source_rgb)
    if n < 1:
        raise ValueError("BLOCKED_RAG7_EMPTY_SWATCH_REGION")
    costs = np.zeros(128, np.int64)
    for offset in range(0, n, PALETTE_CHUNK):
        pixels = source_rgb[offset:offset + PALETTE_CHUNK].astype(np.int16)
        difference = np.abs(
            pixels[:, None, :] - palette[None, :, :].astype(np.int16))
        costs += difference.sum(axis=(0, 2), dtype=np.int64)
    best = int(np.argmin(costs))
    return best, float(costs[best])


def _largest_connected(component: np.ndarray) -> np.ndarray:
    labels, n = ndimage.label(
        component, structure=ndimage.generate_binary_structure(2, 1))
    if not n:
        return np.zeros_like(component, bool)
    area = np.bincount(labels.ravel(), minlength=n + 1)
    area[0] = 0
    return labels == int(np.argmax(area))


def _real_interface(mask: np.ndarray, parent: np.ndarray, lab: np.ndarray
                    ) -> tuple[int, float, float]:
    distances = []
    for left, right, pl, pr, ll, lr in (
        (mask[:, :-1], mask[:, 1:], parent[:, :-1], parent[:, 1:],
         lab[:, :-1], lab[:, 1:]),
        (mask[:-1], mask[1:], parent[:-1], parent[1:],
         lab[:-1], lab[1:]),
    ):
        real = (left != right) & (pl > 0) & (pl == pr)
        if np.any(real):
            distances.append(np.linalg.norm((ll - lr)[real], axis=1))
    if not distances:
        return 0, 0.0, 0.0
    distances = np.concatenate(distances)
    return len(distances), float(np.mean(distances)), float(
        np.count_nonzero(distances >= SOURCE_STRONG_LAB) / len(distances))


def _source_mode_candidate(source_lab: np.ndarray,
                           mask: np.ndarray) -> tuple[np.ndarray | None, str]:
    """One source-only 2-means PCA split; return ONLY a source-connected secondary."""
    samples = source_lab[mask]
    n = len(samples)
    if n < MIN_MODE_PARENT_AREA:
        return None, "small_source"
    centered = samples - np.mean(samples, axis=0)
    covariance = np.dot(centered.T, centered) / n
    values, vectors = np.linalg.eigh(covariance)
    axis = vectors[:, -1].copy()
    pivot = int(np.argmax(np.abs(axis)))
    if axis[pivot] < 0:
        axis *= -1
    proj = samples @ axis
    q_lo, q_hi = np.quantile(proj, [0.25, 0.75])
    low = samples[proj <= q_lo]
    high = samples[proj >= q_hi]
    if not len(low) or not len(high):
        return None, "zero_source_modes"
    centroids = np.vstack((np.median(low, axis=0), np.median(high, axis=0)))
    assigned = np.zeros(n, bool)
    for _ in range(KMEANS_ITERATIONS):
        distance = np.sum(
            (samples[:, None, :] - centroids[None, :, :]) ** 2, axis=2)
        assigned = distance[:, 1] < distance[:, 0]
        if np.all(assigned) or not np.any(assigned):
            return None, "empty_color_mode"
        centroids[0] = np.mean(samples[~assigned], axis=0)
        centroids[1] = np.mean(samples[assigned], axis=0)
    if (np.linalg.norm(centroids[0] - centroids[1]) <
            LAB_CENTROID_SEPARATION
            or min(np.count_nonzero(assigned), np.count_nonzero(~assigned)) <
            MIN_MODE_SHARE * n):
        return None, "insufficient_source_modes"

    # If equally numerous, prefer class 1 for deterministic minority.
    minority_label = bool(np.count_nonzero(assigned) <= np.count_nonzero(~assigned))
    mode = np.zeros_like(mask, bool)
    mode[mask] = assigned == minority_label
    secondary = _largest_connected(mode)
    area = int(np.count_nonzero(secondary))
    if (area < MIN_MODE_REGION_AREA
            or area < MIN_MODE_CONNECTED_SHARE * n):
        return None, "no_significant_connected_mode"
    pairs, mean, strong_frac = _real_interface(
        secondary, mask, source_lab)
    if (pairs < MIN_MODE_INTERFACE_PAIRS
            or mean < MIN_MODE_INTERFACE_LAB
            or strong_frac < MIN_MODE_INTERFACE_STRONG_FRACTION):
        return None, "weak_source_mode_boundary"
    return secondary, "candidate"


def _refine_source_patches(original_rgb: np.ndarray, source_lab: np.ndarray,
                           coarse_patches: np.ndarray, palette: np.ndarray):
    """Source chromatic modes FIRST; palette only judges whole split benefit."""
    n = int(coarse_patches.max())
    selected_mask = np.zeros(coarse_patches.shape, bool)
    counts = {
        "mode_patches_considered": 0, "mode_candidates": 0,
        "mode_reject_source": 0, "mode_reject_spatial": 0,
        "mode_reject_rgb": 0, "mode_splits_accepted": 0,
        "mode_pixels": 0,
    }
    for rid, sl in enumerate(ndimage.find_objects(coarse_patches), 1):
        if sl is None:
            raise ValueError("BLOCKED_RAG7_SOURCE_PATCH_MISSING")
        local_parent = coarse_patches[sl] == rid
        if int(np.count_nonzero(local_parent)) < MIN_MODE_PARENT_AREA:
            continue
        counts["mode_patches_considered"] += 1
        secondary, reason = _source_mode_candidate(
            source_lab[sl], local_parent)
        if secondary is None:
            if reason in ("no_significant_connected_mode", "weak_source_mode_boundary"):
                counts["mode_reject_spatial"] += 1
            else:
                counts["mode_reject_source"] += 1
            continue
        counts["mode_candidates"] += 1
        src = original_rgb[sl]
        _, orig_loss = _best_palette(src[local_parent], palette)
        secondary_rgb = src[secondary]
        remainder_rgb = src[local_parent & ~secondary]
        _, split_loss1 = _best_palette(secondary_rgb, palette)
        _, split_loss2 = _best_palette(remainder_rgb, palette)
        improvement = (orig_loss - split_loss1 - split_loss2) / (
            3.0 * np.count_nonzero(local_parent))
        if improvement + 1e-12 < MODE_LOSS_IMPROVEMENT_RGB:
            counts["mode_reject_rgb"] += 1
            continue
        selected_mask[sl] |= secondary
        counts["mode_splits_accepted"] += 1
        counts["mode_pixels"] += len(secondary_rgb)

    # Original SOURCE graph IDs are never merged across their source boundary;
    # adding at most one 4-connected secondary per original patch.
    remaining = coarse_patches.astype(np.int64)
    remaining[selected_mask] += n
    patch_id = spatial._connected(remaining)
    mode_id = np.where(selected_mask, patch_id, 0).astype(np.int32)
    if np.any(mode_id[coarse_patches == 0]):
        raise ValueError("BLOCKED_RAG7_MODE_ALPHA")
    return patch_id, mode_id, counts


def _assign_patch_colors(original_rgb: np.ndarray, main: np.ndarray,
                         patches: np.ndarray, palette: np.ndarray):
    n = int(patches.max())
    parent = np.zeros(n + 1, np.int32)
    chosen = np.full(n + 1, -1, np.int16)
    for rid, sl in enumerate(ndimage.find_objects(patches), 1):
        if sl is None:
            raise ValueError("BLOCKED_RAG7_DISCONNECTED_PATCH_ID")
        selected = patches[sl] == rid
        src = original_rgb[sl][selected]
        mains = main[sl][selected]
        if not len(src) or not np.all(mains == mains[0]):
            raise ValueError("BLOCKED_RAG7_SPANS_SOURCE_MAIN")
        chosen[rid], _ = _best_palette(src, palette)
        parent[rid] = int(mains[0])
    return parent, chosen


def _assign_original_detail(
    rgba: np.ndarray, main: np.ndarray, patches: np.ndarray,
    source_groups: np.ndarray, regional_colors: np.ndarray,
    palette: np.ndarray
):
    n = int(source_groups.max())
    accepted = np.zeros(n + 1, bool)
    targets = np.full(n + 1, -1, np.int16)
    parents = np.zeros(n + 1, np.int32)
    rgb = rgba[:, :, :3]
    for rid, sl in enumerate(ndimage.find_objects(source_groups), 1):
        if sl is None:
            raise ValueError("BLOCKED_RAG7_EMPTY_SOURCE_DETAIL")
        selector = source_groups[sl] == rid
        samples = rgb[sl][selector]
        mains = main[sl][selector]
        original_colors = regional_colors[patches[sl][selector]]
        if not len(samples) or not np.all(mains == mains[0]):
            raise ValueError("BLOCKED_RAG7_SOURCE_DETAIL_CROSSES_MAIN")
        parents[rid] = int(mains[0])
        swatch, total = _best_palette(samples, palette)
        original_loss = int(np.abs(
            samples.astype(np.int16) -
            palette[original_colors].astype(np.int16)).sum(dtype=np.int64))
        benefit = (original_loss - total) / (3.0 * len(samples))
        if (np.any(original_colors != swatch)
                and benefit + 1e-12 >= DETAIL_LOSS_IMPROVEMENT_RGB):
            accepted[rid] = True
            targets[rid] = int(swatch)

    keep = np.flatnonzero(accepted)
    renumber = np.zeros(n + 1, np.int32)
    renumber[keep] = np.arange(1, len(keep) + 1, dtype=np.int32)
    detail_id = renumber[source_groups]
    detail_parents = np.zeros(len(keep) + 1, np.int32)
    detail_colors = np.full(len(keep) + 1, -1, np.int16)
    detail_parents[1:] = parents[keep]
    detail_colors[1:] = targets[keep]
    return detail_id, detail_parents, detail_colors


def build_rag7(original_rgba: np.ndarray, game128: np.ndarray) -> dict:
    _validate(original_rgba, game128)
    rgba = original_rgba
    h, w = rgba.shape[:2]
    opaque = rgba[:, :, 3] == 255
    if not opaque.any():
        return _blank(rgba)

    # Stateless pure functions process only THIS current original; do not call
    # build_rag6 or consume ANY previous derived artwork/colors/labels.
    original_maps = source.generic_source_maps(rgba)
    coarse = source.original_source_region_uncertainty(rgba, original_maps)
    coarse_labels = spatial._connected(coarse["region_ids"])
    if np.any(coarse_labels[opaque] == 0) or np.any(coarse_labels[~opaque]):
        raise ValueError("BLOCKED_RAG7_ORIGINAL_COARSE_ALPHA")
    lab = color.rgb2lab(rgba[:, :, :3].astype(np.float64) / 255.0)
    merged, main_stats = spatial._merge_slic(coarse_labels, lab)
    main, confirmed_splits = spatial._split_confirmed_source_edges(
        merged, lab, opaque)
    graph = original_graph._source_graph(rgba, opaque)
    source_patches, patch_stats = original_graph._merge_source_graph_within_main(
        graph, main, lab)
    patch_id, source_mode_id, mode_stats = _refine_source_patches(
        rgba[:, :, :3], lab, source_patches, game128)
    strong = spatial._original_strong_edges(
        lab, opaque, original_maps["source_edge"])
    edge_components, original_detail_stats = original_graph._original_edge_components(
        rgba, main, patch_id, lab, strong)

    parent, patch_colors = _assign_patch_colors(
        rgba[:, :, :3], main, patch_id, game128)
    detail_id, d_parent, d_colors = _assign_original_detail(
        rgba, main, patch_id, edge_components, patch_colors, game128)
    composed = np.full((h, w), -1, np.int16)
    composed[opaque] = patch_colors[patch_id[opaque]]
    detail_mask = detail_id > 0
    composed[detail_mask] = d_colors[detail_id[detail_mask]]

    # Nearest game128 from full original Lab is INDEPENDENT and used
    # only to evaluate; no palette index ever seeded spatial topology.
    game_lab = color.rgb2lab(
        game128.reshape(1, 128, 3).astype(np.float64) / 255.0).reshape(128, 3)
    tree = cKDTree(game_lab)
    baseline = np.full((h, w), -1, np.int16)
    indices = np.flatnonzero(opaque.ravel())
    flat_lab = lab.reshape(-1, 3)
    base_flat = baseline.ravel()
    for start in range(0, len(indices), CHUNK):
        current = indices[start:start + CHUNK]
        base_flat[current] = tree.query(
            flat_lab[current], k=1, workers=1)[1].astype(np.int16)

    packed = np.zeros((h, w), np.int64)
    packed[opaque] = main[opaque].astype(np.int64) * 128 + composed[opaque] + 1
    paintable = spatial._connected(packed)
    neighbors, _, _, _ = spatial._boundary_stats(main, lab)
    preview = rgba.copy()
    preview[opaque, :3] = game128[composed[opaque]]

    if (
        np.any(main[~opaque]) or np.any(source_patches[~opaque]) or
        np.any(source_mode_id[~opaque]) or np.any(patch_id[~opaque]) or
        np.any(edge_components[~opaque]) or np.any(detail_id[~opaque]) or
        np.any(paintable[~opaque]) or np.any(baseline[~opaque] != -1) or
        np.any(composed[~opaque] != -1) or
        np.any(parent[patch_id[opaque]] != main[opaque]) or
        np.any(d_parent[detail_id[detail_mask]] != main[detail_mask]) or
        np.any(d_colors[detail_id[detail_mask]] != composed[detail_mask]) or
        not np.array_equal(preview[:, :, 3], rgba[:, :, 3])
    ):
        raise ValueError("BLOCKED_RAG7_SOURCE_MODE_PARENT_OR_ALPHA")

    return {
        "version": VERSION, "surface_id": main,
        "source_patch_id": source_patches,
        "source_mode_id": source_mode_id,
        "patch_id": patch_id, "patch_parent_surface_id": parent,
        "patch_color_index": patch_colors,
        "edge_component_id": edge_components,
        "detail_id": detail_id, "detail_parent_surface_id": d_parent,
        "detail_color_index": d_colors, "paintable_id": paintable,
        "game_index": composed, "baseline_index": baseline,
        "preview_rgba": preview, "source_edge": strong,
        "unknown": np.ones((h, w), bool),
        "adjacency": neighbors,
        "source_to_logical": source.letterbox_binding((w, h)),
        "source_owner_status": "MISSING",
        "stroke_admission": "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE",
        "counts": {
            **main_stats, **patch_stats, **original_detail_stats, **mode_stats,
            "confirmed_splits": int(confirmed_splits),
            "main_surfaces": int(main.max()),
            "source_graph_regions": int(graph.max()),
            "source_patches": int(source_patches.max()),
            "patches": int(patch_id.max()),
            "detail_components": int(len(d_colors) - 1),
            "detail_pixels": int(np.count_nonzero(detail_mask)),
            "paintable_components": int(paintable.max()),
            "game_colors": int(np.unique(composed[opaque]).size),
            "opaque_pixels": int(np.count_nonzero(opaque)),
        },
    }


def evaluate_rag7(original_rgba: np.ndarray, game128: np.ndarray, data: dict) -> dict:
    # Same signed source-MAE, singleton and strong source-neighbor metric used
    # for RAG5/RAG6, evaluated on new current-original RAG7 layers.
    return original_graph.evaluate_rag6(original_rgba, game128, data)

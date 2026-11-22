#!/usr/bin/env python3
"""RAG4: source-only coherent color subregions INSIDE source RAG main surfaces.

One preregistered E0 candidate. No RAG1/RAG2/RAG3 derived art, masks, owner
maps, stroke plans or previews are read. Pure geometry helpers rerun on the
current original. This source-only candidate cannot admit a production stroke.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
from scipy.spatial import cKDTree
from skimage import color

import engine001_bpred_s4r1_generic_source_maps as source
import engine001_bpred_s4r1_rag2_split_guard as source_components
import engine001_bpred_s4r1_rag3_hierarchy as source_hierarchy


VERSION = "ENGINE001_BPRED_S4R1_RAG4_SOURCE_COHERENT_DETAIL_V1"
MAX_SMALL_SEGMENT_AREA = 3
MAX_BOUNDARY_LAB = 12.0
MAX_REGION_LAB = 12.0
MAX_ADDED_RGB_MAE = 1.0
CHUNK = 65536


def _empty_result(rgba: np.ndarray) -> dict:
    h, w = rgba.shape[:2]
    zero = np.zeros((h, w), np.int32)
    missing = np.full((h, w), -1, np.int16)
    return {
        "version": VERSION, "surface_id": zero, "color_segment_id": zero.copy(),
        "detail_id": zero.copy(), "surface_color_index": missing.copy(),
        "surface_color_table": np.array([-1], np.int16),
        "detail_parent_surface_id": np.zeros(1, np.int32),
        "detail_color_index": np.array([-1], np.int16),
        "game_index": missing.copy(), "baseline_index": missing.copy(),
        "preview_rgba": rgba.copy(), "source_edge": np.zeros((h, w), bool),
        "unknown": np.ones((h, w), bool),
        "adjacency": np.empty((0, 2), np.int32),
        "counts": {
            "source_slic": 0, "source_rag_edges": 0, "source_rag_unions": 0,
            "merged_surfaces": 0, "confirmed_splits": 0, "main_surfaces": 0,
            "initial_color_segments": 0, "final_color_segments": 0,
            "detail_segments": 0, "detail_pixels": 0,
            "small_color_candidates": 0, "recolored_color_segments": 0,
            "recolored_pixels": 0, "game_colors": 0, "opaque_pixels": 0,
        },
        "source_owner_status": "MISSING",
        "stroke_admission": "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE",
    }


def _surface_and_color_details(surface: np.ndarray, owners: np.ndarray,
                               opaque: np.ndarray) -> dict:
    """Color segmentation is nested; it may never redefine MAIN surface IDs."""
    h, w = surface.shape
    final = source_components._split_geometry(surface, owners, opaque)
    num_seg = int(final.max())
    num_surface = int(surface.max())
    # Mode of the resulting *source-bounded* current color map, stable swatch tie.
    counts = np.bincount(
        surface[opaque].astype(np.int64) * 128 + owners[opaque].astype(np.int64),
        minlength=(num_surface + 1) * 128).reshape(num_surface + 1, 128)
    table = np.full(num_surface + 1, -1, np.int16)
    table[1:] = np.argmax(counts[1:], axis=1).astype(np.int16)
    surface_color = np.full((h, w), -1, np.int16)
    surface_color[opaque] = table[surface[opaque]]

    seg_parent = np.zeros(num_seg + 1, np.int32)
    seg_color = np.full(num_seg + 1, -1, np.int16)
    ids = final[opaque]
    seg_parent[ids] = surface[opaque]
    seg_color[ids] = owners[opaque]
    keep = np.zeros(num_seg + 1, bool)
    keep[1:] = seg_color[1:] != table[seg_parent[1:]]
    valid_ids = np.flatnonzero(keep)
    # Canonicalize detail IDs to dense 1..N, but never identify color with shape.
    mapping = np.zeros(num_seg + 1, np.int32)
    mapping[valid_ids] = np.arange(1, len(valid_ids) + 1, dtype=np.int32)
    detail_id = mapping[final]
    detail_parents = np.zeros(len(valid_ids) + 1, np.int32)
    detail_colors = np.full(len(valid_ids) + 1, -1, np.int16)
    detail_parents[1:] = seg_parent[valid_ids]
    detail_colors[1:] = seg_color[valid_ids]
    return {
        "color_segment_id": final,
        "detail_id": detail_id,
        "surface_color_index": surface_color,
        "surface_color_table": table,
        "detail_parent_surface_id": detail_parents,
        "detail_color_index": detail_colors,
    }


def build_rag4(original_rgba: np.ndarray, game128: np.ndarray) -> dict:
    if (not isinstance(original_rgba, np.ndarray) or original_rgba.dtype != np.uint8
            or original_rgba.ndim != 3 or original_rgba.shape[2] != 4
            or min(original_rgba.shape[:2]) < 1
            or int(np.prod(original_rgba.shape[:2], dtype=np.int64)) > source.MAX_PIXELS):
        raise ValueError("BLOCKED_RAG4_INVALID_ORIGINAL")
    if (not isinstance(game128, np.ndarray) or game128.dtype != np.uint8
            or game128.shape != (128, 3)
            or np.unique(game128, axis=0).shape[0] != 128):
        raise ValueError("BLOCKED_RAG4_INVALID_GAME_PALETTE")

    rgba = original_rgba
    h, w = rgba.shape[:2]
    opaque = rgba[:, :, 3] == 255
    if not np.any(opaque):
        return _empty_result(rgba)
    # These stateless helpers do not read any historic art, and operate on
    # EXACT current original bytes, re-decoded before each research build.
    original_maps = source.generic_source_maps(rgba)
    original_slic = source.original_source_region_uncertainty(rgba, original_maps)
    slic = source_hierarchy._connected(original_slic["region_ids"])
    if np.any(slic[opaque] < 1) or np.any(slic[~opaque] != 0):
        raise ValueError("BLOCKED_RAG4_SOURCE_ALPHA_CROSSING")

    rgb = rgba[:, :, :3]
    lab = color.rgb2lab(rgb.astype(np.float64) / 255.0)
    game_lab = color.rgb2lab(
        game128.reshape(1, 128, 3).astype(np.float64) / 255.0).reshape(128, 3)
    tree = cKDTree(game_lab)
    baseline = np.full((h, w), -1, np.int16)
    indices = np.flatnonzero(opaque.ravel())
    flat_lab = lab.reshape(-1, 3)
    flat_baseline = baseline.ravel()
    for start in range(0, len(indices), CHUNK):
        idx = indices[start:start + CHUNK]
        flat_baseline[idx] = tree.query(flat_lab[idx], k=1, workers=1)[1].astype(np.int16)

    merged, stats = source_hierarchy._merge_slic(slic, lab)
    surface, split_count = source_hierarchy._split_confirmed_source_edges(
        merged, lab, opaque)
    main_n = int(surface.max())
    if np.any(surface[opaque] < 1) or np.any(surface[~opaque] != 0):
        raise ValueError("BLOCKED_RAG4_MAIN_ALPHA_OR_GEOMETRY")

    # Each provisional color is grouped into a WHOLE connected subregion of
    # THIS source-derived main surface, not a new main geometry region.
    initial = source_components._split_geometry(surface, baseline, opaque)
    n = int(initial.max())
    initial_regions = initial[opaque]
    size = np.bincount(initial_regions, minlength=n + 1).astype(np.int64)
    init_swatch = np.full(n + 1, -1, np.int16)
    init_main = np.zeros(n + 1, np.int32)
    init_swatch[initial_regions] = baseline[opaque]
    init_main[initial_regions] = surface[opaque]
    source_sums = np.column_stack([
        np.bincount(initial_regions, weights=lab[opaque, j],
                    minlength=n + 1) for j in range(3)
    ])
    mean_lab = source_sums / np.maximum(size[:, None], 1)
    pairs, lengths, boundary_max = source_components._rag_adjacency(initial, lab)
    small = np.flatnonzero((size > 0) & (size <= MAX_SMALL_SEGMENT_AREA))
    small = small[small != 0]
    small_set = set(int(x) for x in small)
    adjacency = defaultdict(list)
    for (a, b), shared, max_lab in zip(pairs, lengths, boundary_max):
        a, b = int(a), int(b)
        if (max_lab > MAX_BOUNDARY_LAB
                or init_main[a] != init_main[b]):
            continue
        if a in small_set:
            adjacency[a].append((b, int(shared)))
        if b in small_set:
            adjacency[b].append((a, int(shared)))
    ordered = np.flatnonzero(initial.ravel() > 0)
    ordered = ordered[np.argsort(initial.ravel()[ordered], kind="stable")]
    offsets = np.zeros(n + 2, np.int64)
    offsets[1:] = np.cumsum(size)
    if size[0] or int(offsets[-1]) != len(ordered):
        raise ValueError("BLOCKED_RAG4_COLOR_SUBREGION_OFFSETS")

    current = baseline.copy()
    current_flat = current.ravel()
    rgb_flat = rgb.reshape(-1, 3)
    reassigned = 0
    changed_pixels = 0
    rejected_strong = 0
    rejected_cost = 0
    rejected_mean = 0
    for segment in small:
        segment = int(segment)
        pos = ordered[offsets[segment]:offsets[segment + 1]]
        swatch = int(init_swatch[segment])
        old_rgb_mae = float(np.abs(
            rgb_flat[pos].astype(np.float64) - game128[swatch]).mean())
        choice = None
        for neighbour, shared in adjacency.get(segment, ()):
            if init_main[segment] != init_main[neighbour]:
                raise ValueError("BLOCKED_RAG4_CROSS_SURFACE_CANDIDATE")
            target = int(init_swatch[neighbour])
            if target == swatch:
                continue
            if np.linalg.norm(mean_lab[segment] - mean_lab[neighbour]) > MAX_REGION_LAB:
                rejected_mean += 1
                continue
            new_mae = float(np.abs(
                rgb_flat[pos].astype(np.float64) - game128[target]).mean())
            added = new_mae - old_rgb_mae
            if added > MAX_ADDED_RGB_MAE + 1e-10:
                rejected_cost += 1
                continue
            rank = (round(added, 12), -shared, target, neighbour)
            if choice is None or rank < choice[0]:
                choice = (rank, target)
        if choice is not None:
            current_flat[pos] = choice[1]
            reassigned += 1
            changed_pixels += int(len(pos))

    # Current color parts and parent IDs are coherent; two surfaces sharing
    # the same swatch NEVER lose their distinct geometry identity.
    hierarchy = _surface_and_color_details(surface, current, opaque)
    preview = rgba.copy()
    preview[opaque, :3] = game128[current[opaque]]
    strong = source_hierarchy._original_strong_edges(
        lab, opaque, original_maps["source_edge"])
    main_adjacency, _, _, _ = source_hierarchy._boundary_stats(surface, lab)
    d_id = hierarchy["detail_id"]
    d_parent = hierarchy["detail_parent_surface_id"]
    d_color = hierarchy["detail_color_index"]
    detail_mask = d_id > 0
    if (np.any(d_id[~opaque]) or np.any(surface[~opaque])
            or np.any(current[~opaque] != -1) or np.any(baseline[~opaque] != -1)
            or not np.array_equal(preview[:, :, 3], rgba[:, :, 3])
            or np.any(d_parent[d_id[detail_mask]] != surface[detail_mask])
            or np.any(d_color[d_id[detail_mask]] != current[detail_mask])):
        raise ValueError("BLOCKED_RAG4_COLOR_PARENT_ALPHA_CONTRACT")
    # Non-accredited SOURCE semantics and native brush: explicit fail closed.
    return {
        "version": VERSION, "surface_id": surface, **hierarchy,
        "game_index": current, "baseline_index": baseline,
        "preview_rgba": preview, "source_edge": strong,
        "unknown": np.ones((h, w), bool), "adjacency": main_adjacency,
        "source_owner_status": "MISSING",
        "stroke_admission": "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE",
        "counts": {
            **stats, "confirmed_splits": split_count,
            "main_surfaces": main_n, "initial_color_segments": n,
            "final_color_segments": int(hierarchy["color_segment_id"].max()),
            "detail_segments": len(d_parent) - 1,
            "detail_pixels": int(np.count_nonzero(detail_mask)),
            "small_color_candidates": int(len(small)),
            "recolored_color_segments": reassigned,
            "recolored_pixels": changed_pixels,
            "rejected_mean_lab": rejected_mean,
            "rejected_rgb_cost": rejected_cost,
            "game_colors": int(np.unique(current[opaque]).size),
            "opaque_pixels": int(np.count_nonzero(opaque)),
        }
    }


def evaluate_rag4(original_rgba: np.ndarray, game128: np.ndarray, data: dict):
    from scipy import ndimage
    opaque = original_rgba[:, :, 3] == 255
    result = {"opaque": int(opaque.sum()), "counts": data["counts"]}
    def islands(index):
        components, singletons = 0, 0
        for swatch in np.unique(index[index >= 0]):
            labels, count = ndimage.label(index == swatch, structure=np.ones((3, 3), bool))
            sz = np.bincount(labels.ravel())[1:]
            components += int(count)
            singletons += int(np.count_nonzero(sz == 1))
        return {"components": components, "singletons": singletons}
    result["baseline"] = islands(data["baseline_index"])
    result["candidate"] = islands(data["game_index"])
    if opaque.any():
        a = original_rgba[:, :, :3][opaque].astype(np.float64)
        b = game128[data["baseline_index"][opaque]].astype(np.float64)
        c = game128[data["game_index"][opaque]].astype(np.float64)
        original_lab = color.rgb2lab(original_rgba[:, :, :3].astype(np.float64) / 255.0)
        result.update({
            "baseline_rgb_mae": float(np.abs(a - b).mean()),
            "candidate_rgb_mae": float(np.abs(a - c).mean()),
            "strong_source_contrast":
                source_hierarchy._retained_source_contrast(
                    original_lab,
                    color.rgb2lab(data["preview_rgba"][:, :, :3].astype(np.float64) / 255.0),
                    opaque),
            "main_adjacency_edges": int(len(data["adjacency"])),
        })
    return result

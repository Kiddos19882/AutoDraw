#!/usr/bin/env python3
"""ENGINE-001 / CHROMA-AB1: two frozen, source-only color diagnostic tests.

A: unmerged chromatic original source regions + exact full128 RGB L1.
B: SAME original regions + top4 original contrast-aware two-pass game swatches.
Neither test reads old RAG8/RAG9 maps/previews/strokes or relaxes detail gates.
E0: dc11901d7502679e98f945637625a83320b5d67b.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
from scipy.spatial import cKDTree
from skimage import color

import engine001_bpred_s4r1_generic_source_maps as source
import engine001_bpred_s4r1_rag3_hierarchy as spatial
import engine001_bpred_s4r1_rag6_edge_topology as pure_source
import engine001_bpred_s4r1_rag7_source_color_modes as details
import engine001_bpred_s4r1_rag8_joint_color_graph as chroma
import engine001_bpred_s4r1_rag9_hard_edge_chroma as original_pairs

VERSION = "ENGINE001_BPRED_S4R1_CHROMA_AB1_UNMERGED_SOURCE_COLOR_V1"
E0_BLOB = "dc11901d7502679e98f945637625a83320b5d67b"
VARIANTS = ("A", "B")
TOP_COLORS = 4
CONTRAST_PENALTY = 16
CONTRAST_LAB = 12.0
ITERATIONS = 2
BASELINE_CHUNK = 65536


def _contrast_swatch_optimization(
    costs: np.ndarray, source_regions: np.ndarray,
    opaque: np.ndarray, lab: np.ndarray, swatches: np.ndarray
):
    """Only difference between A and B; original graph stays immutable."""
    n = int(source_regions.max())
    if costs.shape != (n + 1, 128):
        raise ValueError("BLOCKED_CHROMA_AB1_COST_VECTOR")
    dh = np.linalg.norm(lab[:, :-1] - lab[:, 1:], axis=2)
    dv = np.linalg.norm(lab[:-1] - lab[1:], axis=2)
    pairs, lengths = original_pairs._original_strong_region_edges(
        source_regions, opaque, dh, dv)
    chosen = np.full(n + 1, -1, np.int16)
    chosen[1:] = np.argmin(costs[1:], axis=1).astype(np.int16)
    local_candidates = np.argsort(costs[1:], axis=1, kind="stable")[:, :TOP_COLORS]
    palette_lab = color.rgb2lab(
        swatches.reshape(1, 128, 3).astype(np.float64) / 255.
    ).reshape(128, 3)
    adjacency = defaultdict(list)
    for (a, b), count in zip(pairs, lengths):
        adjacency[int(a)].append((int(b), int(count)))
        adjacency[int(b)].append((int(a), int(count)))
    for _ in range(ITERATIONS):
        for rid in range(1, n + 1):
            ranked = []
            for option in local_candidates[rid - 1]:
                swatch = int(option)
                penalty = sum(
                    CONTRAST_PENALTY * count
                    for neighbor, count in adjacency.get(rid, ())
                    if np.linalg.norm(
                        palette_lab[swatch] - palette_lab[int(chosen[neighbor])]
                    ) < CONTRAST_LAB
                )
                ranked.append((
                    int(costs[rid, swatch]) + penalty,
                    int(costs[rid, swatch]), swatch
                ))
            chosen[rid] = min(ranked)[2]
    return chosen, pairs, lengths


def build_chroma_ab1(original_rgba: np.ndarray,
                     game128: np.ndarray, variant: str):
    if variant not in VARIANTS:
        raise ValueError("BLOCKED_CHROMA_AB1_INVALID_TEST")
    pure_source._validate(original_rgba, game128)
    rgba = original_rgba
    h, w = rgba.shape[:2]
    opaque = rgba[:, :, 3] == 255
    if not np.any(opaque):
        empty = chroma._blank(rgba)
        empty.update({
            "version": VERSION, "test_variant": variant,
            "source_graph_id": np.zeros((h, w), np.int32),
            "region_id": np.zeros((h, w), np.int32),
            "region_parent_main": np.zeros(1, np.int32),
            "region_color_index": np.full(1, -1, np.int16),
            "original_strong_boundary_pairs": np.empty((0, 2), np.int32),
            "original_strong_boundary_lengths": np.empty(0, np.int64),
            "counts": {
                "main_surfaces": 0, "source_graph_regions": 0,
                "regions": 0, "detail_components": 0,
                "detail_pixels": 0, "paintable_components": 0,
                "opaque_pixels": 0,
            },
        })
        return empty

    # Fresh from source ONLY. No call to build_rag8 or build_rag9, no saved art.
    original_maps = source.generic_source_maps(rgba)
    coarse = source.original_source_region_uncertainty(rgba, original_maps)
    coarse_labels = spatial._connected(coarse["region_ids"])
    if np.any(coarse_labels[opaque] <= 0) or np.any(coarse_labels[~opaque] != 0):
        raise ValueError("BLOCKED_CHROMA_AB1_ORIGINAL_REGION_ALPHA")
    lab = color.rgb2lab(rgba[:, :, :3].astype(np.float64) / 255.)
    pre_main, _ = spatial._merge_slic(coarse_labels, lab)
    main, _ = spatial._split_confirmed_source_edges(pre_main, lab, opaque)
    graph = chroma._source_chromatic_graph(lab, opaque, main)
    region = graph.copy()
    n = int(region.max())
    if n < 1:
        raise ValueError("BLOCKED_CHROMA_AB1_NO_SOURCE_REGIONS")
    regional_cost = chroma._source_region_costs(region, rgba[:, :, :3], game128)
    plain_color = np.full(n + 1, -1, np.int16)
    plain_color[1:] = np.argmin(regional_cost[1:], axis=1).astype(np.int16)

    # For both A and B, use original true 4-neighbor contrast (never the game).
    original_dh = np.linalg.norm(lab[:, :-1] - lab[:, 1:], axis=2)
    original_dv = np.linalg.norm(lab[:-1] - lab[1:], axis=2)
    original_pairs_array, original_length = (
        original_pairs._original_strong_region_edges(
            region, opaque, original_dh, original_dv
        )
    )
    if variant == "A":
        chosen = plain_color
    else:
        chosen, pair_test, length_test = _contrast_swatch_optimization(
            regional_cost, region, opaque, lab, game128)
        if (not np.array_equal(pair_test, original_pairs_array)
                or not np.array_equal(length_test, original_length)):
            raise ValueError("BLOCKED_CHROMA_AB1_ORIGINAL_PAIRS_MISMATCH")

    parent = np.zeros(n + 1, np.int32)
    parent[region[opaque]] = main[opaque]
    if np.any(parent[region[opaque]] != main[opaque]):
        raise ValueError("BLOCKED_CHROMA_AB1_PARENT")
    source_strong = spatial._original_strong_edges(
        lab, opaque, original_maps["source_edge"])
    detail_groups, _ = pure_source._original_edge_components(
        rgba, main, region, lab, source_strong)
    detail_id, detail_parent, detail_color = details._assign_original_detail(
        rgba, main, region, detail_groups, chosen, game128)

    game_index = np.full((h, w), -1, np.int16)
    game_index[opaque] = chosen[region[opaque]]
    on_detail = detail_id > 0
    game_index[on_detail] = detail_color[detail_id[on_detail]]
    # Original-only evaluation baseline, never a seed for geometry or coloring.
    palette_lab = color.rgb2lab(
        game128.reshape(1, 128, 3).astype(np.float64) / 255.
    ).reshape(128, 3)
    tree = cKDTree(palette_lab)
    nearest = np.full((h, w), -1, np.int16)
    positions = np.flatnonzero(opaque.ravel())
    original_lab_flat = lab.reshape(-1, 3)
    for offset in range(0, len(positions), BASELINE_CHUNK):
        pos = positions[offset:offset + BASELINE_CHUNK]
        nearest.ravel()[pos] = tree.query(
            original_lab_flat[pos], k=1, workers=1)[1].astype(np.int16)

    actual_paintable = np.zeros((h, w), np.int64)
    actual_paintable[opaque] = (
        main[opaque].astype(np.int64) * 128 + game_index[opaque] + 1)
    paintable = spatial._connected(actual_paintable)
    preview = rgba.copy()
    preview[opaque, :3] = game128[game_index[opaque]]
    main_adjacency, _, _, _ = spatial._boundary_stats(main, lab)

    if (np.any(graph[~opaque]) or np.any(region[~opaque])
            or np.any(main[~opaque]) or np.any(paintable[~opaque])
            or np.any(detail_id[~opaque])
            or np.any(game_index[~opaque] != -1)
            or np.any(nearest[~opaque] != -1)
            or np.any(parent[region[opaque]] != main[opaque])
            or np.any(detail_parent[detail_id[on_detail]] != main[on_detail])
            or np.any(detail_color[detail_id[on_detail]]
                      != game_index[on_detail])
            or not np.array_equal(preview[..., 3], rgba[..., 3])):
        raise ValueError("BLOCKED_CHROMA_AB1_PARENT_ALPHA_COLOR")
    return {
        "version": VERSION, "test_variant": variant,
        "surface_id": main, "source_graph_id": graph,
        "region_id": region, "region_parent_main": parent,
        "region_color_index": chosen,
        "edge_component_id": detail_groups,
        "detail_id": detail_id, "detail_parent_main": detail_parent,
        "detail_color_index": detail_color,
        "original_strong_boundary_pairs": original_pairs_array,
        "original_strong_boundary_lengths": original_length,
        "paintable_id": paintable, "game_index": game_index,
        "baseline_index": nearest, "preview_rgba": preview,
        "source_edge": source_strong, "unknown": np.ones((h, w), bool),
        "adjacency": main_adjacency,
        "source_to_logical": source.letterbox_binding((w, h)),
        "source_owner_status": "MISSING",
        "stroke_admission": "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE",
        "counts": {
            "main_surfaces": int(main.max()),
            "source_graph_regions": int(graph.max()),
            "regions": int(region.max()),
            "original_strong_region_pairs": len(original_pairs_array),
            "detail_components": int(detail_color.size - 1),
            "detail_pixels": int(on_detail.sum()),
            "paintable_components": int(paintable.max()),
            "game_colors": int(np.unique(game_index[opaque]).size),
            "opaque_pixels": int(opaque.sum()),
        },
    }


def evaluate_chroma_ab1(rgba: np.ndarray, game128: np.ndarray, data: dict):
    return pure_source.evaluate_rag6(rgba, game128, data)

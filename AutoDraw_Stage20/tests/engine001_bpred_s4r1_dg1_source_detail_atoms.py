#!/usr/bin/env python3
"""ENGINE-001 / DG1: current-original protected detail ATOMS before swatches.

One prospective E0 at Git blob c3db5ff1508eddee3268f13730ef96e1f67811e4.
Research-only source S4.2+S4.3; no old image outputs, game brushes or CHALK.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree
from skimage import color

import engine001_bpred_s4r1_generic_source_maps as source
import engine001_bpred_s4r1_rag3_hierarchy as spatial
import engine001_bpred_s4r1_rag6_edge_topology as source_validation
import engine001_bpred_s4r1_rag8_joint_color_graph as pure_chroma_graph
import engine001_bpred_s4r1_chroma_ab1_color_tests as pure_strong_swatch

VERSION = "ENGINE001_BPRED_S4R1_DG1_SOURCE_PROTECTED_ATOMS_BEFORE_COLOR_V1"
E0_SHA1 = "c3db5ff1508eddee3268f13730ef96e1f67811e4"
DOT_MIN_ORIGINAL_LAB = 24.0
DOT_MIN_OPAQUE_NEIGHBORS = 3
CHROMA_COST_PER_PIXEL = 1.0
NEAREST_CHUNK = 65536


def _protected_original_dots(lab: np.ndarray, opaque: np.ndarray) -> np.ndarray:
    """Protect a truly isolated high-contrast 1px source feature BEFORE game128.

    Any RGB source dot with >=3 true opaque 4-neighbors AND contrast >=24 to
    each qualifies. No already predicted palette indices are consulted.
    """
    neighbors = np.zeros(opaque.shape, np.uint8)
    minimum = np.full(opaque.shape, np.inf, np.float64)
    for (a, b, mask_a, mask_b, opa_a, opa_b) in (
        (lab[:, :-1], lab[:, 1:], minimum[:, :-1], minimum[:, 1:],
         opaque[:, :-1], opaque[:, 1:]),
        (lab[:-1], lab[1:], minimum[:-1], minimum[1:],
         opaque[:-1], opaque[1:]),
    ):
        diff = np.linalg.norm(a - b, axis=2)
        valid = opa_a & opa_b
        effective = np.where(valid, diff, np.inf)
        np.minimum(mask_a, effective, out=mask_a)
        np.minimum(mask_b, effective, out=mask_b)
        if a.shape[0] == lab.shape[0]:
            neighbors[:, :-1] += valid.astype(np.uint8)
            neighbors[:, 1:] += valid.astype(np.uint8)
        else:
            neighbors[:-1] += valid.astype(np.uint8)
            neighbors[1:] += valid.astype(np.uint8)
    return opaque & (neighbors >= DOT_MIN_OPAQUE_NEIGHBORS) & (
        minimum >= DOT_MIN_ORIGINAL_LAB)


def _original_detail_atoms(graph: np.ndarray, main: np.ndarray,
                           protected: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Split source-only chroma graph where high-contrast original points exist.

    Every original 4-connected remaining side is separately numbered.
    """
    opaque = main > 0
    if graph.shape != main.shape or protected.shape != main.shape:
        raise ValueError("BLOCKED_DG1_SOURCE_SHAPE")
    if np.any(graph[opaque] == 0) or np.any(graph[~opaque]) or np.any(protected[~opaque]):
        raise ValueError("BLOCKED_DG1_SOURCE_GRAPH_ALPHA")
    ids = graph.astype(np.int64)
    n = int(protected.sum())
    if n:
        ids[protected] = (int(graph.max()) + 1 +
                          np.arange(n, dtype=np.int64))
    # Native _connected is true 4-connected. Removed dot may split a graph.
    new_regions = spatial._connected(ids)
    num = int(new_regions.max())
    parents = np.zeros(num + 1, np.int32)
    parents[new_regions[opaque]] = main[opaque]
    if (np.any(parents[new_regions[opaque]] != main[opaque])
            or np.any(new_regions[~opaque])
            or np.any(new_regions[opaque] == 0)):
        raise ValueError("BLOCKED_DG1_ORIGINAL_ATOM_PARENT")
    return new_regions, parents


def _chroma_original_score(
    atoms: np.ndarray, lab: np.ndarray, rgb: np.ndarray,
    game128: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Exact regional all128 original RGB L1 + frozen rounded per-pixel ab loss."""
    # Pure current original helper, NO historical RAG8 image/preview input.
    exact_rgb_cost = pure_chroma_graph._source_region_costs(atoms, rgb, game128)
    n = int(atoms.max())
    if exact_rgb_cost.shape != (n + 1, 128):
        raise ValueError("BLOCKED_DG1_SOURCE_COST_SHAPE")
    weights, lab_totals, _ = spatial._lab_means(atoms, lab)
    palette_lab = color.rgb2lab(
        game128.reshape(1, 128, 3).astype(np.float64) / 255.
    ).reshape(128, 3)
    augmented = exact_rgb_cost.copy()
    if n:
        mean_chroma = lab_totals[1:, 1:] / weights[1:, None]
        source_chroma_distance = np.linalg.norm(
            mean_chroma[:, None, :] - palette_lab[None, :, 1:],
            axis=2,
        )
        chroma_penalty = np.floor(
            CHROMA_COST_PER_PIXEL * weights[1:, None] *
            source_chroma_distance + 0.5).astype(np.int64)
        augmented[1:] += chroma_penalty
    return exact_rgb_cost, augmented, palette_lab


def _empty(rgba: np.ndarray) -> dict:
    h, w = rgba.shape[:2]
    z = np.zeros((h, w), np.int32)
    neg = np.full((h, w), -1, np.int16)
    return {
        "version": VERSION, "source_graph_id": z.copy(),
        "surface_id": z.copy(), "source_atom_id": z.copy(),
        "protected_original_dot": np.zeros((h, w), bool),
        "atom_parent_main": np.zeros(1, np.int32),
        "atom_color_index": np.full(1, -1, np.int16),
        "source_strong_pair": np.empty((0, 2), np.int32),
        "source_strong_length": np.empty(0, np.int64),
        "paintable_id": z.copy(), "game_index": neg.copy(),
        "baseline_index": neg.copy(), "source_edge": np.zeros((h, w), bool),
        "preview_rgba": rgba.copy(), "unknown": np.ones((h, w), bool),
        "adjacency": np.empty((0, 2), np.int32),
        "source_to_logical": source.letterbox_binding((w, h)),
        "source_owner_status": "MISSING",
        "stroke_admission": "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE",
        "counts": {
            "main_surfaces": 0, "source_graph_regions": 0,
            "source_protected_original_points": 0, "source_atoms": 0,
            "paintable_components": 0, "opaque_pixels": 0,
        },
    }


def build_dg1(original_rgba: np.ndarray, game128: np.ndarray) -> dict:
    source_validation._validate(original_rgba, game128)
    rgba = original_rgba
    h, w = rgba.shape[:2]
    opaque = rgba[..., 3] == 255
    if not np.any(opaque):
        return _empty(rgba)

    # The full source geometry below is regenerated from CURRENT original.
    original_maps = source.generic_source_maps(rgba)
    coarse = source.original_source_region_uncertainty(rgba, original_maps)
    coarse_ids = spatial._connected(coarse["region_ids"])
    lab = color.rgb2lab(rgba[..., :3].astype(np.float64) / 255.)
    pre_main, _ = spatial._merge_slic(coarse_ids, lab)
    main, _ = spatial._split_confirmed_source_edges(pre_main, lab, opaque)
    if np.any(main[~opaque]) or np.any(main[opaque] == 0):
        raise ValueError("BLOCKED_DG1_ORIGINAL_MAIN")

    chroma_graph = pure_chroma_graph._source_chromatic_graph(lab, opaque, main)
    protected = _protected_original_dots(lab, opaque)
    regions, parents = _original_detail_atoms(chroma_graph, main, protected)
    exact_cost, color_score, palette_lab = _chroma_original_score(
        regions, lab, rgba[..., :3], game128)

    # Same pure original-neighbor, swatch adjacency math but DIFFERENT
    # source-only topology; there is NO independent after-color detail overlay.
    chosen, strong_pairs, strong_lengths = (
        pure_strong_swatch._contrast_swatch_optimization(
            color_score, regions, opaque, lab, game128
        )
    )
    composed = np.full((h, w), -1, np.int16)
    composed[opaque] = chosen[regions[opaque]]
    if np.any(composed[opaque] < 0) or np.any(composed[opaque] > 127):
        raise ValueError("BLOCKED_DG1_INVALID_SOURCE_SWATCH")

    tree = cKDTree(palette_lab)
    nearest = np.full((h, w), -1, np.int16)
    valid_locations = np.flatnonzero(opaque.ravel())
    original_flat = lab.reshape(-1, 3)
    for offset in range(0, len(valid_locations), NEAREST_CHUNK):
        part = valid_locations[offset:offset + NEAREST_CHUNK]
        nearest.ravel()[part] = tree.query(
            original_flat[part], k=1, workers=1)[1].astype(np.int16)

    actual_ids = np.zeros((h, w), np.int64)
    actual_ids[opaque] = (main[opaque].astype(np.int64) * 128
                          + composed[opaque].astype(np.int64) + 1)
    paintable = spatial._connected(actual_ids)
    preview = rgba.copy()
    preview[opaque, :3] = game128[composed[opaque]]
    strong_edges = spatial._original_strong_edges(
        lab, opaque, original_maps["source_edge"])
    adjacency, _, _, _ = spatial._boundary_stats(main, lab)

    # Strong source dot ALWAYS remains an atom; verify data invariants.
    if (np.any(main[~opaque]) or np.any(chroma_graph[~opaque])
            or np.any(regions[~opaque]) or np.any(paintable[~opaque])
            or np.any(composed[~opaque] != -1)
            or np.any(nearest[~opaque] != -1)
            or np.any(parents[regions[opaque]] != main[opaque])
            or np.any(protected & ~opaque)
            or not np.array_equal(preview[..., 3], rgba[..., 3])
            or not np.array_equal(composed[opaque], chosen[regions[opaque]])
            or int(paintable.max()) > int(regions.max())):
        raise ValueError("BLOCKED_DG1_ORIGINAL_SOURCE_INVARIANTS")
    if np.any(protected):
        source_ids = regions[protected]
        if (len(np.unique(source_ids)) != int(np.count_nonzero(protected))
                or np.any(np.bincount(regions.ravel())[source_ids] != 1)):
            raise ValueError("BLOCKED_DG1_TRUE_PROTECTED_POINTS")

    return {
        "version": VERSION, "surface_id": main,
        "source_graph_id": chroma_graph, "source_atom_id": regions,
        "atom_parent_main": parents, "atom_color_index": chosen,
        "protected_original_dot": protected,
        "source_strong_pair": strong_pairs,
        "source_strong_length": strong_lengths,
        "game_index": composed, "baseline_index": nearest,
        "paintable_id": paintable, "source_edge": strong_edges,
        "preview_rgba": preview, "unknown": np.ones((h, w), bool),
        "adjacency": adjacency,
        "source_to_logical": source.letterbox_binding((w, h)),
        "source_owner_status": "MISSING",
        "stroke_admission": "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE",
        "counts": {
            "main_surfaces": int(main.max()),
            "source_graph_regions": int(chroma_graph.max()),
            "source_protected_original_points": int(protected.sum()),
            "source_atoms": int(regions.max()),
            "source_strong_pairs": int(len(strong_pairs)),
            "paintable_components": int(paintable.max()),
            "game_colors": int(np.unique(composed[opaque]).size),
            "opaque_pixels": int(opaque.sum()),
        },
    }


def evaluate_dg1(rgba: np.ndarray, game128: np.ndarray, data: dict) -> dict:
    # Exactly the same original-only source metric; no gameplay output claimed.
    return source_validation.evaluate_rag6(rgba, game128, data)

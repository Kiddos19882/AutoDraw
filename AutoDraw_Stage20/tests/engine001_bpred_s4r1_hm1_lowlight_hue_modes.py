#!/usr/bin/env python3
"""HM1: original chromatic HUE OWNER modes before palette, categorical dark hue.

Research S4.2+S4.3 ONLY. Frozen original E0 blob
ee10dec2a1a22732e69e4aa5a3a0f42c63e4569f. No prior candidate art/ROI.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
from scipy.spatial import cKDTree
from skimage import color

import engine001_bpred_s4r1_generic_source_maps as source
import engine001_bpred_s4r1_rag3_hierarchy as spatial
import engine001_bpred_s4r1_rag6_edge_topology as validator
import engine001_bpred_s4r1_rag8_joint_color_graph as original_graph
import engine001_bpred_s4r1_rag9_hard_edge_chroma as original_pairs
from engine001_bpred_s4r1_dg1_source_detail_atoms import (
    _protected_original_dots, _original_detail_atoms
)

VERSION = "ENGINE001_BPRED_S4R1_HM1_ORIGINAL_LOWLIGHT_HUE_FAMILIES_V1"
E0_SHA1 = "ee10dec2a1a22732e69e4aa5a3a0f42c63e4569f"
DARK_SOURCE_L_MAX = 45.0
DARK_SOURCE_CHROMA_MIN = 10.0
HUE_FAMILY_COUNT = 8
HUE_MODE_MIN_PIXELS = 12
HUE_MODE_MIN_PARENT_FRACTION = .20
GAME_SWATCH_MIN_CHROMA = 6.0
HUE_OWNER_MIN_REGION_PIXELS = 8
HUE_COMPATIBLE_DOT_MIN = 0.0
TOP_SWATCHES = 4
STRONG_ORIGINAL_LAB = 12.0
STRONG_GAME_LAB = 12.0
STRONG_RECOLOR_PENALTY = 16
ICM_SWEEPS = 2
NEAREST_CHUNK = 65536


def _original_hue_mode(lab: np.ndarray, opaque: np.ndarray) -> np.ndarray:
    """1..8 source hue sectors, angle centered 0,45,..315 deg; 0 no mode."""
    if lab.shape != (*opaque.shape, 3):
        raise ValueError("BLOCKED_HM1_ORIGINAL_LAB_SHAPE")
    chroma = np.linalg.norm(lab[..., 1:], axis=2)
    dark = opaque & (lab[..., 0] <= DARK_SOURCE_L_MAX) & (
        chroma >= DARK_SOURCE_CHROMA_MIN)
    angles = np.arctan2(lab[..., 2], lab[..., 1])
    rotation = np.pi / HUE_FAMILY_COUNT
    width = 2.0 * np.pi / HUE_FAMILY_COUNT
    sectors = np.floor(np.mod(angles + rotation, 2.0 * np.pi) / width).astype(np.int16)
    result = np.zeros(opaque.shape, np.uint8)
    result[dark] = (sectors[dark] + 1).astype(np.uint8)
    return result


def _new_connected_hue_atoms(
    original_atoms: np.ndarray, main: np.ndarray, hue: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Accept *source-original* connected hue components with area support.

    All accepted groups and disconnected leftover become 4connected final
    owners BEFORE any game128 swatches are examined.
    """
    if (hue.shape != main.shape or original_atoms.shape != main.shape
            or np.any(hue[main == 0]) or np.any(original_atoms[main > 0] == 0)):
        raise ValueError("BLOCKED_HM1_SOURCE_MODE_PARENT")
    opaque = main > 0
    key = np.zeros(main.shape, np.int64)
    key[opaque] = (original_atoms[opaque].astype(np.int64) *
                   (HUE_FAMILY_COUNT + 1) + hue[opaque].astype(np.int64) + 1)
    components = spatial._connected(key)
    n = int(components.max())
    count = np.bincount(components.ravel(), minlength=n + 1)
    parent_atom = np.zeros(n + 1, np.int32)
    component_hue = np.zeros(n + 1, np.uint8)
    parent_atom[components[opaque]] = original_atoms[opaque]
    component_hue[components[opaque]] = hue[opaque]
    total = np.bincount(original_atoms.ravel(),
                        minlength=int(original_atoms.max()) + 1)
    accepted = ((component_hue > 0)
                & (count >= HUE_MODE_MIN_PIXELS)
                & (count >= HUE_MODE_MIN_PARENT_FRACTION * total[parent_atom]))
    accepted[0] = False
    labels = original_atoms.astype(np.int64)
    picked = accepted[components]
    labels[picked] = (int(original_atoms.max()) +
                      components[picked].astype(np.int64))
    final = spatial._connected(labels)
    nfinal = int(final.max())
    original_parent = np.zeros(nfinal + 1, np.int32)
    final_source_mode = np.zeros(nfinal + 1, np.uint8)
    original_parent[final[opaque]] = main[opaque]
    # Source hue-family annotation is only for those selected original modes.
    final_source_mode[final[picked]] = hue[picked]
    if (np.any(final[~opaque]) or np.any(original_parent[final[opaque]] != main[opaque])
            or np.any(final[opaque] <= 0)):
        raise ValueError("BLOCKED_HM1_SOURCE_HUE_ATOM_ALPHA_PARENT")
    return final, original_parent, final_source_mode


def _hue_family_palette(
    regions: np.ndarray, rgb: np.ndarray, lab: np.ndarray,
    opaque: np.ndarray, game128: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Exact all128 RGB L1, original supported dark-hue compatible candidates.

    Source hue ownership constrains the admissible game swatch set without
    a chroma-L1 weight, then true source strong-neighbor pairs guide ICM.
    """
    n = int(regions.max())
    exact = original_graph._source_region_costs(regions, rgb, game128)
    counts, totals, _ = spatial._lab_means(regions, lab)
    means = totals / np.maximum(counts[:, None], 1)
    swatch_lab = color.rgb2lab(
        game128.reshape(1, 128, 3).astype(np.float64) / 255.
    ).reshape(128, 3)
    swatch_c = np.linalg.norm(swatch_lab[:, 1:], axis=1)
    mean_c = np.linalg.norm(means[:, 1:], axis=1)
    supported = ((counts >= HUE_OWNER_MIN_REGION_PIXELS)
                 & (means[:, 0] <= DARK_SOURCE_L_MAX)
                 & (mean_c >= DARK_SOURCE_CHROMA_MIN))
    supported[0] = False
    compatible = np.ones((n + 1, 128), bool)
    supported_ids = np.flatnonzero(supported)
    for rid in supported_ids:
        matched = ((swatch_c >= GAME_SWATCH_MIN_CHROMA)
                   & ((swatch_lab[:, 1:] @ means[rid, 1:]) >
                      HUE_COMPATIBLE_DOT_MIN))
        if not np.any(matched):
            raise ValueError("BLOCKED_HM1_HUE_NO_REAL_SWATCH")
        compatible[rid] = matched
    scored = np.where(compatible, exact, np.iinfo(np.int64).max)
    ranked = np.argsort(scored[1:], axis=1, kind="stable")[:, :TOP_SWATCHES]
    initial = np.full(n + 1, -1, np.int16)
    initial[1:] = ranked[:, 0].astype(np.int16)

    dh = np.linalg.norm(lab[:, :-1] - lab[:, 1:], axis=2)
    dv = np.linalg.norm(lab[:-1] - lab[1:], axis=2)
    pairs, lengths = original_pairs._original_strong_region_edges(
        regions, opaque, dh, dv)
    adjacency = defaultdict(list)
    for (a, b), length in zip(pairs, lengths):
        a, b, length = int(a), int(b), int(length)
        adjacency[a].append((b, length))
        adjacency[b].append((a, length))
    close_swatches = (np.linalg.norm(
        swatch_lab[:, None, :] - swatch_lab[None, :, :], axis=2
    ) < STRONG_GAME_LAB)
    selected = initial.copy()
    for _ in range(ICM_SWEEPS):
        for rid in range(1, n + 1):
            candidates = ranked[rid - 1]
            best = None
            choice = -1
            for option in candidates:
                index = int(option)
                if not compatible[rid, index]:
                    continue
                penalty = sum(
                    STRONG_RECOLOR_PENALTY * length
                    for neighbor, length in adjacency.get(rid, ())
                    if close_swatches[index, int(selected[neighbor])]
                )
                candidate = (int(exact[rid, index]) + penalty,
                             int(exact[rid, index]), index)
                if best is None or candidate < best:
                    best = candidate
                    choice = index
            if choice < 0:
                raise ValueError("BLOCKED_HM1_NO_ADMISSIBLE_GAME128")
            selected[rid] = choice
    if np.any(selected[1:] < 0) or np.any(selected[1:] >= 128):
        raise ValueError("BLOCKED_HM1_SWATCH_OUT_OF_GENUINE_RANGE")
    if np.any(~compatible[np.arange(1, n + 1), selected[1:]]):
        raise ValueError("BLOCKED_HM1_SOURCE_HUE_OWNER_VIOLATION")
    return selected, supported, compatible, pairs, lengths


def _empty(rgba: np.ndarray) -> dict:
    h, w = rgba.shape[:2]
    zero = np.zeros((h, w), np.int32)
    neg = np.full((h, w), -1, np.int16)
    return {
        "version": VERSION, "surface_id": zero.copy(),
        "original_graph_id": zero.copy(),
        "protected_source_atom_id": zero.copy(),
        "original_hue_mode": np.zeros((h, w), np.uint8),
        "source_mode_region_id": zero.copy(),
        "source_region_parent_main": np.zeros(1, np.int32),
        "region_hue_mode": np.zeros(1, np.uint8),
        "region_supported_dark_hue": np.zeros(1, bool),
        "region_color_index": np.full(1, -1, np.int16),
        "protected_original_dot": np.zeros((h, w), bool),
        "strong_original_region_pair": np.empty((0, 2), np.int32),
        "strong_original_region_length": np.empty(0, np.int64),
        "paintable_id": zero.copy(), "game_index": neg.copy(),
        "baseline_index": neg.copy(),
        "source_edge": np.zeros((h, w), bool),
        "preview_rgba": rgba.copy(), "unknown": np.ones((h, w), bool),
        "adjacency": np.empty((0, 2), np.int32),
        "source_to_logical": source.letterbox_binding((w, h)),
        "source_owner_status": "MISSING",
        "stroke_admission": "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE",
        "counts": {"main_surfaces": 0, "original_chroma_graph": 0,
                   "source_protected_original_points": 0,
                   "source_modes": 0, "source_final_regions": 0,
                   "supported_dark_hue_regions": 0, "paintable_components": 0,
                   "opaque_pixels": 0},
    }


def build_hm1(original_rgba: np.ndarray, game128: np.ndarray) -> dict:
    validator._validate(original_rgba, game128)
    rgba = original_rgba
    h, w = rgba.shape[:2]
    opaque = rgba[..., 3] == 255
    if not np.any(opaque):
        return _empty(rgba)
    original_maps = source.generic_source_maps(rgba)
    coarse = source.original_source_region_uncertainty(rgba, original_maps)
    coarse_ids = spatial._connected(coarse["region_ids"])
    lab = color.rgb2lab(rgba[..., :3].astype(np.float64) / 255.)
    pre_main, _ = spatial._merge_slic(coarse_ids, lab)
    main, _ = spatial._split_confirmed_source_edges(pre_main, lab, opaque)
    if np.any(main[~opaque]) or np.any(main[opaque] <= 0):
        raise ValueError("BLOCKED_HM1_MAIN_ALPHA")
    graph = original_graph._source_chromatic_graph(lab, opaque, main)
    protected = _protected_original_dots(lab, opaque)
    base, _ = _original_detail_atoms(graph, main, protected)

    original_hue = _original_hue_mode(lab, opaque)
    final, parent, region_mode = _new_connected_hue_atoms(
        base, main, original_hue)
    swatch, supported, _, strong_pairs, strong_lengths = _hue_family_palette(
        final, rgba[..., :3], lab, opaque, game128)
    painted = np.full((h, w), -1, np.int16)
    painted[opaque] = swatch[final[opaque]]
    if np.any(painted[opaque] < 0):
        raise ValueError("BLOCKED_HM1_MISSING_GAME128")

    swatch_lab = color.rgb2lab(
        game128.reshape(1, 128, 3).astype(np.float64) / 255.
    ).reshape(128, 3)
    tree = cKDTree(swatch_lab)
    nearest = np.full((h, w), -1, np.int16)
    original_lab_flat = lab.reshape(-1, 3)
    eligible = np.flatnonzero(opaque.ravel())
    for offset in range(0, len(eligible), NEAREST_CHUNK):
        part = eligible[offset:offset + NEAREST_CHUNK]
        nearest.ravel()[part] = tree.query(
            original_lab_flat[part], k=1, workers=1)[1].astype(np.int16)

    paint_key = np.zeros((h, w), np.int64)
    paint_key[opaque] = (main[opaque].astype(np.int64) * 128
                         + painted[opaque].astype(np.int64) + 1)
    paintable = spatial._connected(paint_key)
    preview = rgba.copy()
    preview[opaque, :3] = game128[painted[opaque]]
    source_edges = spatial._original_strong_edges(
        lab, opaque, original_maps["source_edge"])
    adjacency, _, _, _ = spatial._boundary_stats(main, lab)
    if (np.any(graph[~opaque]) or np.any(base[~opaque]) or
            np.any(final[~opaque]) or np.any(paintable[~opaque]) or
            np.any(original_hue[~opaque]) or np.any(protected[~opaque]) or
            np.any(painted[~opaque] != -1) or np.any(nearest[~opaque] != -1) or
            np.any(parent[final[opaque]] != main[opaque]) or
            not np.array_equal(painted[opaque], swatch[final[opaque]]) or
            not np.array_equal(preview[..., 3], rgba[..., 3]) or
            int(paintable.max()) > int(final.max())):
        raise ValueError("BLOCKED_HM1_SOURCE_OWNER_ALPHA_GEOMETRY")
    if np.any(protected):
        ids = final[protected]
        if (len(np.unique(ids)) != int(protected.sum())
                or np.any(np.bincount(final.ravel())[ids] != 1)):
            raise ValueError("BLOCKED_HM1_ORIGINAL_PROTECTED_DETAIL_LOST")
    return {
        "version": VERSION, "surface_id": main,
        "original_graph_id": graph, "protected_source_atom_id": base,
        "original_hue_mode": original_hue,
        "source_mode_region_id": final, "source_region_parent_main": parent,
        "region_hue_mode": region_mode,
        "region_supported_dark_hue": supported,
        "region_color_index": swatch, "protected_original_dot": protected,
        "strong_original_region_pair": strong_pairs,
        "strong_original_region_length": strong_lengths,
        "paintable_id": paintable, "game_index": painted,
        "baseline_index": nearest, "source_edge": source_edges,
        "preview_rgba": preview, "unknown": np.ones((h, w), bool),
        "adjacency": adjacency,
        "source_to_logical": source.letterbox_binding((w, h)),
        "source_owner_status": "MISSING",
        "stroke_admission": "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE",
        "counts": {
            "main_surfaces": int(main.max()),
            "original_chroma_graph": int(graph.max()),
            "source_protected_original_points": int(protected.sum()),
            "source_modes": int(np.count_nonzero(region_mode)),
            "source_final_regions": int(final.max()),
            "supported_dark_hue_regions": int(np.count_nonzero(supported)),
            "paintable_components": int(paintable.max()),
            "game_colors": int(np.unique(painted[opaque]).size),
            "opaque_pixels": int(opaque.sum()),
        },
    }


def evaluate_hm1(rgba: np.ndarray, game128: np.ndarray, result: dict) -> dict:
    return validator.evaluate_rag6(rgba, game128, result)

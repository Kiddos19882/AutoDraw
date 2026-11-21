#!/usr/bin/env python3
"""DEC-048 RAG1: research-only original RGB/alpha regions and joint game128 colors.

Not a stroke planner, source-owner ground truth, native Egret evidence or
production admission. No historical image/map/plan is loaded.
"""
from __future__ import annotations

import hashlib
from collections import Counter

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage import color

import engine001_bpred_s4r1_generic_source_maps as source

VERSION = "ENGINE001_BPRED_S4R1_RAG1_V1"
MAX_LAB_MEAN_DISTANCE = 12.0
SOURCE_STRONG_LAB = 12.0
MAX_STRONG_FRACTION = 0.25
MAX_ADDED_COLOR_SSE = 100.0


def _connected_relabel(raw: np.ndarray, opaque: np.ndarray) -> np.ndarray:
    """Split any disconnected SLIC labels into deterministic 4-connected IDs."""
    if np.any(raw[~opaque] != 0) or np.any(raw[opaque] <= 0):
        raise ValueError("BLOCKED_RAG1_SLIC_ALPHA_OR_LABEL")
    labels = np.zeros_like(raw, dtype=np.int32)
    number = 0
    for label_id, sl in enumerate(ndimage.find_objects(raw), start=1):
        if sl is None:
            continue
        components, count = ndimage.label(
            raw[sl] == label_id,
            structure=ndimage.generate_binary_structure(2, 1))
        for comp in range(1, count + 1):
            number += 1
            view = labels[sl]
            view[components == comp] = number
    if np.any(labels[opaque] <= 0):
        raise ValueError("BLOCKED_RAG1_REGION_CONNECTIVITY")
    return labels


def _source_rag(labels: np.ndarray, lab: np.ndarray, opaque: np.ndarray):
    """4-neighbor source edges: length and count of original strong transitions."""
    h, w = labels.shape
    edges = {}
    strong = np.zeros((h, w), bool)
    directions = [
        (labels[:, :-1], labels[:, 1:], lab[:, :-1], lab[:, 1:],
         opaque[:, :-1], opaque[:, 1:], "h"),
        (labels[:-1, :], labels[1:, :], lab[:-1, :], lab[1:, :],
         opaque[:-1, :], opaque[1:, :], "v"),
    ]
    for a, b, la, lb, oa, ob, axis in directions:
        contrast = (np.linalg.norm(la - lb, axis=2) > SOURCE_STRONG_LAB) & oa & ob
        if axis == "h":
            strong[:, :-1] |= contrast
            strong[:, 1:] |= contrast
        else:
            strong[:-1, :] |= contrast
            strong[1:, :] |= contrast
        pairmask = (a > 0) & (b > 0) & (a != b)
        if not pairmask.any():
            continue
        n = int(labels.max()) + 1
        left, right = a[pairmask].astype(np.int64), b[pairmask].astype(np.int64)
        keys = np.minimum(left, right) * n + np.maximum(left, right)
        values, inverse = np.unique(keys, return_inverse=True)
        counts = np.bincount(inverse)
        count_strong = np.bincount(inverse, weights=contrast[pairmask])
        for v, k, st in zip(values, counts, count_strong):
            key = (int(v // n), int(v % n))
            prev = edges.get(key, (0, 0.0))
            edges[key] = (prev[0] + int(k), prev[1] + float(st))
    return edges, strong


def build_rag1(original_rgba: np.ndarray, game128: np.ndarray) -> dict:
    if (not isinstance(original_rgba, np.ndarray)
            or original_rgba.dtype != np.uint8 or original_rgba.ndim != 3
            or original_rgba.shape[2] != 4 or min(original_rgba.shape[:2]) < 1
            or original_rgba.shape[0] * original_rgba.shape[1] > source.MAX_PIXELS):
        raise ValueError("BLOCKED_RAG1_INVALID_ORIGINAL")
    if (not isinstance(game128, np.ndarray) or game128.dtype != np.uint8
            or game128.shape != (128, 3)
            or np.unique(game128, axis=0).shape[0] != 128):
        raise ValueError("BLOCKED_RAG1_INVALID_GAME_PALETTE")
    h, w = original_rgba.shape[:2]
    opaque = original_rgba[:, :, 3] == 255
    labels = np.zeros((h, w), np.int32)
    owners = np.full((h, w), -1, np.int16)
    baseline = owners.copy()
    preview = original_rgba.copy()
    strong = np.zeros((h, w), bool)
    if not np.any(opaque):
        return {
            "version": VERSION, "region_ids": labels, "game_index": owners,
            "baseline_index": baseline, "preview_rgba": preview,
            "source_strong_edge": strong,
            "source_owner_status": "MISSING",
            "stroke_admission": "FORBIDDEN_UNTIL_INDEPENDENT_NATIVE_VALIDATION",
            "counts": {"initial_regions": 0, "final_regions": 0, "merges": 0},
        }

    maps = source.generic_source_maps(original_rgba)
    initial = source.original_source_region_uncertainty(original_rgba, maps)
    labels = _connected_relabel(initial["region_ids"], opaque)
    initial_n = int(labels.max())
    lab = color.rgb2lab(original_rgba[:, :, :3].astype(np.float64) / 255.0)
    game_lab = color.rgb2lab(game128.reshape((1, 128, 3)).astype(np.float64) / 255.0).reshape((128, 3))
    palette_tree = cKDTree(game_lab)

    # Fresh original-only pixelwise nearest baseline, never input to RAG.
    opaque_positions = np.flatnonzero(opaque.reshape(-1))
    flat = lab.reshape(-1, 3)
    for start in range(0, len(opaque_positions), 65536):
        subset = opaque_positions[start:start + 65536]
        baseline.reshape(-1)[subset] = palette_tree.query(
            flat[subset], k=1, workers=1)[1].astype(np.int16)

    original_labels = labels.copy()
    ids = labels[opaque]
    source_lab = lab[opaque]
    areas = np.bincount(ids, minlength=initial_n + 1).astype(np.int64)
    sums = np.zeros((initial_n + 1, 3), np.float64)
    for c in range(3):
        sums[:, c] = np.bincount(
            ids, weights=source_lab[:, c], minlength=initial_n + 1)
    squares = np.bincount(
        ids, weights=np.einsum("ij,ij->i", source_lab, source_lab),
        minlength=initial_n + 1).astype(np.float64)
    parent = np.arange(initial_n + 1, dtype=np.int32)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = int(parent[x])
        return x

    def nearest_and_cost(size, lab_sum, squared):
        mean = lab_sum / size
        k = int(palette_tree.query(mean, k=1, workers=1)[1])
        color_lab = game_lab[k]
        error = max(0.0, float(squared - 2.0 * np.dot(color_lab, lab_sum)
                               + size * np.dot(color_lab, color_lab)))
        return k, error

    graph, strong = _source_rag(labels, lab, opaque)
    order = []
    for (a, b), (length, strong_count) in graph.items():
        if strong_count / length > MAX_STRONG_FRACTION:
            continue
        distance = float(np.linalg.norm(sums[a] / areas[a] - sums[b] / areas[b]))
        order.append((distance, a, b))
    merges = 0
    for _, a, b in sorted(order):
        a, b = find(a), find(b)
        if a == b:
            continue
        distance = float(np.linalg.norm(sums[a] / areas[a] - sums[b] / areas[b]))
        if distance > MAX_LAB_MEAN_DISTANCE:
            continue
        _, before_a = nearest_and_cost(areas[a], sums[a], squares[a])
        _, before_b = nearest_and_cost(areas[b], sums[b], squares[b])
        _, after = nearest_and_cost(
            areas[a] + areas[b], sums[a] + sums[b], squares[a] + squares[b])
        if after - before_a - before_b > MAX_ADDED_COLOR_SSE + 1e-6:
            continue
        if a > b:
            a, b = b, a
        parent[b] = a
        areas[a] += areas[b]
        sums[a] += sums[b]
        squares[a] += squares[b]
        merges += 1

    root = np.array([find(i) for i in range(initial_n + 1)], np.int32)
    ordered_roots = sorted(set(int(v) for v in root[1:]))
    region_ids = {r: i + 1 for i, r in enumerate(ordered_roots)}
    new_label_lookup = np.zeros(initial_n + 1, np.int32)
    game_lookup = np.full(initial_n + 1, -1, np.int16)
    root_game = {r: nearest_and_cost(areas[r], sums[r], squares[r])[0]
                 for r in ordered_roots}
    for i in range(1, initial_n + 1):
        r = int(root[i])
        new_label_lookup[i] = region_ids[r]
        game_lookup[i] = root_game[r]
    final_labels = new_label_lookup[original_labels]
    owners[opaque] = game_lookup[original_labels[opaque]]
    preview[opaque, :3] = game128[owners[opaque]]
    return {
        "version": VERSION,
        "region_ids": final_labels, "game_index": owners,
        "baseline_index": baseline, "preview_rgba": preview,
        "source_strong_edge": strong,
        "source_owner_status": "MISSING",
        "stroke_admission": "FORBIDDEN_UNTIL_INDEPENDENT_NATIVE_VALIDATION",
        "counts": {
            "initial_regions": initial_n, "final_regions": len(ordered_roots),
            "merges": merges, "source_strong_edge_cells": int(strong.sum()),
            "game_colors": int(np.unique(owners[opaque]).size),
        },
    }


def count_color_islands(owners: np.ndarray) -> dict:
    """Source-pixel 8-connected islands; no special-cased white owner index."""
    sizes = Counter()
    opaque = owners >= 0
    structure = np.ones((3, 3), dtype=np.uint8)
    for value in np.unique(owners[opaque]):
        components, n = ndimage.label(owners == value, structure=structure)
        if n:
            counts = np.bincount(components.ravel())[1:]
            sizes.update({int(k): int(v) for k, v in zip(
                *np.unique(counts, return_counts=True))})
    return {
        "components": int(sum(sizes.values())),
        "singletons": int(sizes[1]),
        "components_le3": int(sum(n for sz, n in sizes.items() if sz <= 3)),
        "pixels_in_components_le3": int(sum(sz * n for sz, n in sizes.items() if sz <= 3)),
    }


def evaluate_rag1(original_rgba: np.ndarray, palette: np.ndarray, result: dict) -> dict:
    """Compare newly computed source-only baseline and candidate, no old art."""
    opaque = original_rgba[:, :, 3] == 255
    old_owner = result["baseline_index"]
    new_owner = result["game_index"]
    if not np.any(opaque):
        return {"opaque": 0, "baseline": count_color_islands(old_owner),
                "candidate": count_color_islands(new_owner)}
    old = palette[old_owner[opaque]].astype(np.float64)
    new = palette[new_owner[opaque]].astype(np.float64)
    rgb = original_rgba[:, :, :3][opaque].astype(np.float64)
    strong = result["source_strong_edge"] & opaque
    return {
        "opaque": int(opaque.sum()),
        "baseline_rgb_mae": float(np.mean(np.abs(rgb - old))),
        "candidate_rgb_mae": float(np.mean(np.abs(rgb - new))),
        "source_strong_cells": int(strong.sum()),
        "baseline": count_color_islands(old_owner),
        "candidate": count_color_islands(new_owner),
        "candidate_counts": result["counts"],
    }

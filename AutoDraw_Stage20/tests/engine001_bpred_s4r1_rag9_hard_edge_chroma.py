#!/usr/bin/env python3
"""ENGINE-001 / RAG9 prospective source-only hard-edge chromatic propagation.

Frozen E0 Git blob: 5bd38c425f599747e3d8319edf20973782e9bb74.
Input is the CURRENT original RGBA plus genuine game128. NO historical art,
saved maps, RAG1-RAG8 builders, full-Egret claims, or production admission.
"""
from __future__ import annotations

from collections import defaultdict, deque
import heapq
import math

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage import color

import engine001_bpred_s4r1_generic_source_maps as source
import engine001_bpred_s4r1_rag3_hierarchy as spatial
import engine001_bpred_s4r1_rag6_edge_topology as pure_source

VERSION = "ENGINE001_BPRED_S4R1_RAG9_HARD_SOURCE_EDGE_CHROMA_GEODESIC_V1"
E0_SHA1 = "5bd38c425f599747e3d8319edf20973782e9bb74"
BIN_FACTOR = 65536
NEAREST_CHUNK = 65536


def _hard_source_edges(lab: np.ndarray, opaque: np.ndarray):
    """Forbidden original 4-neighbor crossings, independent of game palette."""
    dh = np.linalg.norm(lab[:, :-1] - lab[:, 1:], axis=2)
    dv = np.linalg.norm(lab[:-1] - lab[1:], axis=2)
    ch = np.linalg.norm(lab[:, :-1, 1:] - lab[:, 1:, 1:], axis=2)
    cv = np.linalg.norm(lab[:-1, :, 1:] - lab[1:, :, 1:], axis=2)
    sh = np.zeros(dh.shape, bool)
    sv = np.zeros(dv.shape, bool)
    chs = np.zeros(ch.shape, bool)
    cvs = np.zeros(cv.shape, bool)
    sh[1:] |= dh[:-1] >= 12.0
    sh[:-1] |= dh[1:] >= 12.0
    sv[:, 1:] |= dv[:, :-1] >= 12.0
    sv[:, :-1] |= dv[:, 1:] >= 12.0
    chs[1:] |= ch[:-1] >= 9.0
    chs[:-1] |= ch[1:] >= 9.0
    cvs[:, 1:] |= cv[:, :-1] >= 9.0
    cvs[:, :-1] |= cv[:, 1:] >= 9.0
    barh = (dh >= 24.0) | ((dh >= 12.0) & sh) | ((ch >= 9.0) & chs)
    barv = (dv >= 24.0) | ((dv >= 12.0) & sv) | ((cv >= 9.0) & cvs)
    barh |= ~(opaque[:, :-1] & opaque[:, 1:])
    barv |= ~(opaque[:-1] & opaque[1:])
    return barh, barv, dh, dv


def _allowed_components(owner: np.ndarray, barh: np.ndarray,
                        barv: np.ndarray) -> np.ndarray:
    """4-connectivity while respecting forbidden PAIR crossings (not pixels)."""
    h, w = owner.shape
    out = np.zeros((h, w), np.int32)
    queue = deque()
    count = 0
    for y in range(h):
        for x in range(w):
            key = int(owner[y, x])
            if key == 0 or out[y, x]:
                continue
            count += 1
            out[y, x] = count
            queue.append((y, x))
            while queue:
                yy, xx = queue.popleft()
                if xx and not barh[yy, xx - 1] and not out[yy, xx - 1] and owner[yy, xx - 1] == key:
                    out[yy, xx - 1] = count
                    queue.append((yy, xx - 1))
                if xx + 1 < w and not barh[yy, xx] and not out[yy, xx + 1] and owner[yy, xx + 1] == key:
                    out[yy, xx + 1] = count
                    queue.append((yy, xx + 1))
                if yy and not barv[yy - 1, xx] and not out[yy - 1, xx] and owner[yy - 1, xx] == key:
                    out[yy - 1, xx] = count
                    queue.append((yy - 1, xx))
                if yy + 1 < h and not barv[yy, xx] and not out[yy + 1, xx] and owner[yy + 1, xx] == key:
                    out[yy + 1, xx] = count
                    queue.append((yy + 1, xx))
    return out


def _source_bins(lab: np.ndarray) -> np.ndarray:
    light = np.floor(np.clip(lab[..., 0], 0, 100) / 10).astype(np.int32)
    aa = np.floor(np.clip(lab[..., 1] + 128, 0, 255) / 6).astype(np.int32)
    bb = np.floor(np.clip(lab[..., 2] + 128, 0, 255) / 6).astype(np.int32)
    return ((light * 64 + aa) * 64 + bb).astype(np.int32)


def _atom_modes(atoms: np.ndarray, main: np.ndarray, lab: np.ndarray,
                bins: np.ndarray, barh: np.ndarray, barv: np.ndarray,
                dh: np.ndarray, dv: np.ndarray):
    """Find source modal bins and valid supported/strong-dot anchor atoms."""
    n = int(atoms.max())
    opaque = atoms > 0
    atom_parent = np.zeros(n + 1, np.int32)
    atom_parent[atoms[opaque]] = main[opaque]
    atom_sizes = np.bincount(atoms[opaque], minlength=n + 1)
    if np.any(atom_parent[atoms[opaque]] != main[opaque]):
        raise ValueError("BLOCKED_RAG9_ATOM_PARENT")
    key = atoms[opaque].astype(np.int64) * BIN_FACTOR + bins[opaque]
    joint, counts = np.unique(key, return_counts=True)
    atom_idx = (joint // BIN_FACTOR).astype(np.int32)
    bin_idx = (joint % BIN_FACTOR).astype(np.int32)
    max_count = np.zeros(n + 1, np.int64)
    np.maximum.at(max_count, atom_idx, counts)
    choices = counts == max_count[atom_idx]
    mode = np.zeros(n + 1, np.int32)
    # np.unique ordered by atom, then ascending bin: first equal maximum wins.
    mode[atom_idx[choices]] = bin_idx[choices]

    area = np.bincount(main[opaque], minlength=int(main.max()) + 1)
    main_bin = main[opaque].astype(np.int64) * BIN_FACTOR + bins[opaque]
    keys, support_counts = np.unique(main_bin, return_counts=True)
    is_supported = (support_counts >= 8) & (support_counts >=
                                            np.ceil(.02 * area[(keys // BIN_FACTOR).astype(np.int32)]))
    supported_keys = keys[is_supported]
    present_keys = atom_parent[1:].astype(np.int64) * BIN_FACTOR + mode[1:]
    seeded = np.zeros(n + 1, bool)
    seeded[1:] = np.isin(present_keys, supported_keys, assume_unique=False)
    if not seeded[1:].any():
        largest = int(np.argmax(atom_sizes[1:])) + 1
        seeded[largest] = True
    # Preserve 1px strongly contrasted original dots even when rare (<8).
    high = np.zeros(atoms.shape, bool)
    high[:, :-1] |= (dh >= 24.0) & barh
    high[:, 1:] |= (dh >= 24.0) & barh
    high[:-1] |= (dv >= 24.0) & barv
    high[1:] |= (dv >= 24.0) & barv
    high_atoms = np.unique(atoms[high & opaque])
    seeded[high_atoms] = True

    # Exact per-atom three-dimensional original-Lab medians for geodesic costs.
    flat_ids = atoms.ravel()
    indexes = np.flatnonzero(flat_ids)
    order = indexes[np.argsort(flat_ids[indexes], kind="stable")]
    sorted_ids = flat_ids[order]
    bounds = np.searchsorted(sorted_ids, np.arange(1, n + 2), side="left")
    flat_lab = lab.reshape(-1, 3)
    medians = np.zeros((n + 1, 3), np.float64)
    for rid in range(1, n + 1):
        values = flat_lab[order[bounds[rid - 1]:bounds[rid]]]
        if not len(values):
            raise ValueError("BLOCKED_RAG9_EMPTY_ATOM")
        medians[rid] = np.median(values, axis=0)
    return atom_parent, atom_sizes, mode, seeded, medians, high


def _source_atom_adjacency(atoms: np.ndarray, main: np.ndarray,
                           bh: np.ndarray, bv: np.ndarray):
    """Real, nonbarred, within-main 4-neighbor adjacency of source atoms."""
    n = int(atoms.max())
    edges = []
    for left, right, block, ma, mb in (
        (atoms[:, :-1], atoms[:, 1:], bh, main[:, :-1], main[:, 1:]),
        (atoms[:-1], atoms[1:], bv, main[:-1], main[1:]),
    ):
        take = (left > 0) & (right > 0) & (left != right) & ~block & (ma == mb)
        if not np.any(take):
            continue
        a = np.minimum(left[take], right[take]).astype(np.int64)
        b = np.maximum(left[take], right[take]).astype(np.int64)
        edges.append(a * (n + 1) + b)
    if not edges:
        return np.zeros((0, 2), np.int32), np.zeros(0, np.int64)
    numbers, lengths = np.unique(np.concatenate(edges), return_counts=True)
    return np.column_stack((numbers // (n + 1),
                            numbers % (n + 1))).astype(np.int32), lengths


def _propagate(atoms: np.ndarray, main: np.ndarray, parent: np.ndarray,
               mode: np.ndarray, seeds: np.ndarray,
               medians: np.ndarray, atom_pairs: np.ndarray):
    """One deterministic multi-source original-only geodesic Dijkstra."""
    n = int(atoms.max())
    adjacency = defaultdict(list)
    for a, b in atom_pairs:
        aa, bb = int(a), int(b)
        delta = medians[aa] - medians[bb]
        cost = 1.0 + 2.0 * float(np.linalg.norm(delta[1:])) + .5 * abs(float(delta[0]))
        adjacency[aa].append((bb, cost))
        adjacency[bb].append((aa, cost))
    for arr in adjacency.values():
        arr.sort(key=lambda t: t[0])
    best = np.full(n + 1, np.inf, np.float64)
    owner = np.full(n + 1, -1, np.int64)
    heap = []
    for aid in range(1, n + 1):
        if not seeds[aid]:
            continue
        seed_key = int(parent[aid]) * BIN_FACTOR + int(mode[aid])
        best[aid], owner[aid] = 0.0, seed_key
        heapq.heappush(heap, (0.0, seed_key, aid, aid))
    while heap:
        dist, seed_key, origin, at = heapq.heappop(heap)
        if dist > best[at] + 1e-10 or (abs(dist - best[at]) <= 1e-10 and owner[at] != seed_key):
            continue
        for nxt, cost in adjacency[at]:
            candidate = dist + cost
            if (candidate < best[nxt] - 1e-10 or
                    (abs(candidate - best[nxt]) <= 1e-10 and seed_key < owner[nxt])):
                best[nxt], owner[nxt] = candidate, seed_key
                heapq.heappush(heap, (candidate, seed_key, origin, nxt))
    # An unseeded disconnected source graph component retains its source mode.
    for aid in range(1, n + 1):
        if owner[aid] == -1:
            owner[aid] = int(parent[aid]) * BIN_FACTOR + int(mode[aid])
    uf = np.arange(n + 1, dtype=np.int32)
    def root(x):
        while uf[x] != x:
            uf[x] = uf[uf[x]]
            x = int(uf[x])
        return x
    for a, b in atom_pairs:
        aa, bb = int(a), int(b)
        if owner[aa] == owner[bb]:
            left, right = root(aa), root(bb)
            if left != right:
                uf[max(left, right)] = min(left, right)
    roots = np.zeros(n + 1, np.int32)
    for aid in range(1, n + 1):
        roots[aid] = root(aid)
    _, inverse = np.unique(roots[1:], return_inverse=True)
    atom_region = np.zeros(n + 1, np.int32)
    atom_region[1:] = inverse + 1
    region = atom_region[atoms]
    nregion = int(region.max())
    region_parent = np.zeros(nregion + 1, np.int32)
    region_seed = np.zeros(nregion + 1, np.int64)
    region_parent[region[atoms > 0]] = main[atoms > 0]
    region_seed[atom_region[1:]] = owner[1:]
    if np.any(region_parent[region[atoms > 0]] != main[atoms > 0]):
        raise ValueError("BLOCKED_RAG9_MODE_PARENT")
    return region, region_parent, region_seed, owner, len(heap)


def _regional_palette_cost(region: np.ndarray, rgb: np.ndarray,
                           palette: np.ndarray) -> np.ndarray:
    n = int(region.max())
    result = np.zeros((n + 1, 128), np.int64)
    slices = ndimage.find_objects(region)
    p = palette.astype(np.int16)
    for rid, sl in enumerate(slices, 1):
        if sl is None:
            raise ValueError("BLOCKED_RAG9_REGION_DISCONNECTED")
        px = rgb[sl][region[sl] == rid].astype(np.int16)
        if not len(px):
            raise ValueError("BLOCKED_RAG9_REGION_EMPTY")
        for pos in range(0, len(px), 4096):
            chunk = px[pos:pos + 4096]
            result[rid] += np.abs(chunk[:, None] - p[None, :]).sum(axis=(0, 2), dtype=np.int64)
    return result


def _original_strong_region_edges(region: np.ndarray, opaque: np.ndarray,
                                  dh: np.ndarray, dv: np.ndarray):
    n = int(region.max())
    pairs = []
    for a, b, valid, d in (
        (region[:, :-1], region[:, 1:], opaque[:, :-1] & opaque[:, 1:], dh),
        (region[:-1], region[1:], opaque[:-1] & opaque[1:], dv),
    ):
        mask = valid & (d >= 12.0) & (a != b)
        if np.any(mask):
            left = np.minimum(a[mask], b[mask]).astype(np.int64)
            right = np.maximum(a[mask], b[mask]).astype(np.int64)
            pairs.append(left * (n + 1) + right)
    if not pairs:
        return np.zeros((0, 2), np.int32), np.zeros(0, np.int64)
    ids, counts = np.unique(np.concatenate(pairs), return_counts=True)
    return np.column_stack((ids // (n + 1), ids % (n + 1))).astype(np.int32), counts


def _regional_game128(region: np.ndarray, original_rgb: np.ndarray,
                      palette: np.ndarray, strong_pairs: np.ndarray,
                      strong_lengths: np.ndarray):
    costs = _regional_palette_cost(region, original_rgb, palette)
    n = costs.shape[0] - 1
    chosen = np.full(n + 1, -1, np.int16)
    chosen[1:] = np.argmin(costs[1:], axis=1).astype(np.int16)
    palette_lab = color.rgb2lab(palette.reshape(1, 128, 3).astype(np.float64) / 255.).reshape(128, 3)
    adjacency = defaultdict(list)
    for (a, b), length in zip(strong_pairs, strong_lengths):
        adjacency[int(a)].append((int(b), int(length)))
        adjacency[int(b)].append((int(a), int(length)))
    candidates = np.argsort(costs[1:], axis=1, kind="stable")[:, :4]
    for _ in range(2):
        for rid in range(1, n + 1):
            ranked = []
            for candidate in candidates[rid - 1]:
                idx = int(candidate)
                penalty = sum(16 * count for other, count in adjacency.get(rid, ())
                              if np.linalg.norm(palette_lab[idx] - palette_lab[int(chosen[other])]) < 12.0)
                ranked.append((int(costs[rid, idx]) + penalty, int(costs[rid, idx]), idx))
            chosen[rid] = min(ranked)[-1]
    return chosen, costs


def build_rag9(original_rgba: np.ndarray, game128: np.ndarray) -> dict:
    pure_source._validate(original_rgba, game128)
    rgba = original_rgba
    h, w = rgba.shape[:2]
    opaque = rgba[:, :, 3] == 255
    if not np.any(opaque):
        z = np.zeros((h, w), np.int32)
        miss = np.full((h, w), -1, np.int16)
        return dict(version=VERSION, surface_id=z.copy(), barrier_atom_id=z.copy(),
                    atom_source_bin=np.zeros(1, np.int32), patch_id=z.copy(),
                    patch_parent_surface_id=np.zeros(1, np.int32),
                    patch_source_mode=np.zeros(1, np.int64),
                    patch_color_index=np.full(1, -1, np.int16),
                    game_index=miss.copy(), baseline_index=miss.copy(),
                    paintable_id=z.copy(), preview_rgba=rgba.copy(),
                    barrier_h=np.zeros((h, max(0, w - 1)), bool),
                    barrier_v=np.zeros((max(0, h - 1), w), bool),
                    source_edge=np.zeros((h, w), bool),
                    unknown=np.ones((h, w), bool),
                    adjacency=np.empty((0, 2), np.int32),
                    source_to_logical=source.letterbox_binding((w, h)),
                    source_owner_status="MISSING",
                    stroke_admission="FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE",
                    counts=dict(main_surfaces=0, atoms=0, patches=0,
                                paintable_components=0, opaque_pixels=0))
    original_maps = source.generic_source_maps(rgba)
    coarse = source.original_source_region_uncertainty(rgba, original_maps)
    coarse_id = spatial._connected(coarse["region_ids"])
    lab = color.rgb2lab(rgba[:, :, :3].astype(np.float64) / 255.)
    merged, _ = spatial._merge_slic(coarse_id, lab)
    main, _ = spatial._split_confirmed_source_edges(merged, lab, opaque)
    if np.any(main[~opaque]) or np.any(main[opaque] < 1):
        raise ValueError("BLOCKED_RAG9_MAIN_ALPHA")
    bh, bv, dh, dv = _hard_source_edges(lab, opaque)
    combined = np.zeros((h, w), np.int64)
    combined[opaque] = coarse_id[opaque].astype(np.int64) * (int(main.max()) + 1) + main[opaque]
    atoms = _allowed_components(combined, bh, bv)
    bins = _source_bins(lab)
    parent, sizes, modes, seeds, medians, original_high = _atom_modes(
        atoms, main, lab, bins, bh, bv, dh, dv)
    edges, lengths = _source_atom_adjacency(atoms, main, bh, bv)
    patches, patch_parent, patch_modes, atom_owners, _ = _propagate(
        atoms, main, parent, modes, seeds, medians, edges)
    strong_pairs, strong_lengths = _original_strong_region_edges(
        patches, opaque, dh, dv)
    region_color, regional_costs = _regional_game128(
        patches, rgba[:, :, :3], game128, strong_pairs, strong_lengths)

    composed = np.full((h, w), -1, np.int16)
    composed[opaque] = region_color[patches[opaque]]
    palette_lab = color.rgb2lab(game128.reshape(1, 128, 3).astype(np.float64) / 255.).reshape(128, 3)
    tree = cKDTree(palette_lab)
    baseline = np.full((h, w), -1, np.int16)
    original_index = np.flatnonzero(opaque.ravel())
    for off in range(0, len(original_index), NEAREST_CHUNK):
        pos = original_index[off:off + NEAREST_CHUNK]
        baseline.ravel()[pos] = tree.query(
            lab.reshape(-1, 3)[pos], k=1, workers=1)[1].astype(np.int16)
    packed = np.zeros((h, w), np.int64)
    packed[opaque] = main[opaque].astype(np.int64) * 128 + composed[opaque] + 1
    paintable = spatial._connected(packed)
    edge_pixels = np.zeros((h, w), bool)
    edge_pixels[:, :-1] |= bh & (dh >= 12.)
    edge_pixels[:, 1:] |= bh & (dh >= 12.)
    edge_pixels[:-1] |= bv & (dv >= 12.)
    edge_pixels[1:] |= bv & (dv >= 12.)
    edge_pixels &= opaque
    preview = rgba.copy()
    preview[opaque, :3] = game128[composed[opaque]]
    adjacency, _, _, _ = spatial._boundary_stats(main, lab)
    if (np.any(atoms[~opaque]) or np.any(patches[~opaque])
            or np.any(paintable[~opaque]) or np.any(composed[~opaque] != -1)
            or np.any(baseline[~opaque] != -1)
            or np.any(patch_parent[patches[opaque]] != main[opaque])
            or not np.array_equal(preview[..., 3], rgba[..., 3])):
        raise ValueError("BLOCKED_RAG9_SOURCE_INVARIANTS")
    return dict(version=VERSION, surface_id=main,
                barrier_atom_id=atoms, atom_source_bin=modes,
                atom_source_owner=atom_owners, patch_id=patches,
                patch_parent_surface_id=patch_parent, patch_source_mode=patch_modes,
                patch_color_index=region_color, game_index=composed,
                baseline_index=baseline, paintable_id=paintable,
                preview_rgba=preview, barrier_h=bh, barrier_v=bv,
                source_edge=edge_pixels, unknown=np.ones((h, w), bool),
                adjacency=adjacency,
                source_to_logical=source.letterbox_binding((w, h)),
                source_owner_status="MISSING",
                stroke_admission="FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE",
                counts=dict(main_surfaces=int(main.max()),
                            atoms=int(atoms.max()), patches=int(patches.max()),
                            geodesic_seed_atoms=int(seeds.sum()),
                            supported_source_modes=int(np.unique(atom_owners[1:]).size),
                            source_hard_h=int(bh.sum()), source_hard_v=int(bv.sum()),
                            original_high_contrast_pixels=int(original_high.sum()),
                            strong_region_neighbor_pairs=len(strong_pairs),
                            paintable_components=int(paintable.max()),
                            opaque_pixels=int(opaque.sum()),
                            game_colors=int(np.unique(composed[opaque]).size)))


def evaluate_rag9(rgba: np.ndarray, game128: np.ndarray, data: dict) -> dict:
    # Reuse only stateless E2 original-vs-candidate metric, not old art.
    import engine001_bpred_s4r1_rag5_source_multiscale as metrics
    return metrics.evaluate_rag5(rgba, game128, data)

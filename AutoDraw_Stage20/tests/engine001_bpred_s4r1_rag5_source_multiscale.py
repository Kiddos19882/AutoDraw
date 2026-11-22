#!/usr/bin/env python3
"""RAG5 source-only two-scale color patches with source-supported details.

Only the current original RGB/alpha + pinned real game128 swatches are inputs.
RAG2/RAG3 modules are used for STATELESS source geometry functions only.
No previous artwork/region/color/map/report is ever read or used as seed.
Research E2 only; does not authorize a native/production stroke.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage import color, segmentation

import engine001_bpred_s4r1_generic_source_maps as source
import engine001_bpred_s4r1_rag3_hierarchy as spatial


VERSION = "ENGINE001_BPRED_S4R1_RAG5_SOURCE_MULTISCALE_V1"
FINE_AREA = 24
FINE_MAX_SEGMENTS = 12000
FINE_COMPACTNESS = 4.0
BORDER_MEAN_LAB = 12.0
BORDER_STRONG_FRACTION = 0.125
PATCH_MEAN_LAB = 12.0
STRONG_DETAIL_DEVIATION_LAB = 20.0
DETAIL_ADJACENT_LAB = 12.0
DETAIL_IMPROVEMENT_RGB = 2.0
CHUNK = 65536
PALETTE_CANDIDATES_LAB = 5


def _check_input(rgba: np.ndarray, palette: np.ndarray) -> None:
    if (not isinstance(rgba, np.ndarray) or rgba.dtype != np.uint8
            or rgba.ndim != 3 or rgba.shape[-1] != 4
            or min(rgba.shape[:2]) < 1
            or int(np.prod(rgba.shape[:2], dtype=np.int64)) > source.MAX_PIXELS):
        raise ValueError("BLOCKED_RAG5_INVALID_ORIGINAL")
    if (not isinstance(palette, np.ndarray) or palette.dtype != np.uint8
            or palette.shape != (128, 3)
            or len(np.unique(palette, axis=0)) != 128):
        raise ValueError("BLOCKED_RAG5_INVALID_PALETTE")


def _blank(rgba: np.ndarray) -> dict:
    h, w = rgba.shape[:2]
    empty = np.zeros((h, w), np.int32)
    missing = np.full((h, w), -1, np.int16)
    return {
        "version": VERSION, "surface_id": empty.copy(),
        "patch_id": empty.copy(), "patch_parent_surface_id": np.zeros(1, np.int32),
        "patch_color_index": np.full(1, -1, np.int16),
        "detail_id": empty.copy(), "detail_parent_surface_id": np.zeros(1, np.int32),
        "detail_color_index": np.full(1, -1, np.int16),
        "paintable_id": empty.copy(), "game_index": missing.copy(),
        "baseline_index": missing.copy(), "preview_rgba": rgba.copy(),
        "source_edge": np.zeros((h, w), bool),
        "unknown": np.ones((h, w), bool),
        "adjacency": np.empty((0, 2), np.int32),
        "source_to_logical": source.letterbox_binding((w, h)),
        "source_owner_status": "MISSING",
        "stroke_admission": "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE",
        "counts": {
            "source_slic": 0, "source_rag_unions": 0,
            "main_surfaces": 0, "fine_slic_segments": 0,
            "initial_patch_regions": 0, "patches": 0, "patch_unions": 0,
            "detail_source_candidates": 0, "detail_components": 0,
            "details_accepted": 0, "detail_pixels": 0,
            "paintable_components": 0, "game_colors": 0, "opaque_pixels": 0,
        },
    }


def _fresh_fine_slic(rgba: np.ndarray, opaque: np.ndarray) -> np.ndarray:
    h, w = opaque.shape
    pixels = int(np.count_nonzero(opaque))
    if pixels < 16 or min(h, w) < 2:
        labels, _ = ndimage.label(
            opaque, structure=ndimage.generate_binary_structure(2, 1))
        return labels.astype(np.int32)
    n_segments = max(1, min(FINE_MAX_SEGMENTS, (pixels + FINE_AREA - 1) // FINE_AREA))
    fine = segmentation.slic(
        rgba[:, :, :3].astype(np.float64) / 255.0,
        n_segments=n_segments, compactness=FINE_COMPACTNESS,
        sigma=0, convert2lab=True, enforce_connectivity=True,
        start_label=1, channel_axis=-1, slic_zero=False, mask=opaque
    ).astype(np.int32)
    if np.any(fine[~opaque]) or np.any(fine[opaque] < 1):
        raise ValueError("BLOCKED_RAG5_FINE_SOURCE_ALPHA")
    return spatial._connected(fine)


def _source_merge_patches(surface: np.ndarray, fine: np.ndarray, lab: np.ndarray):
    """One deterministic spatial RAG join of source fine patches within parent."""
    main_n = int(surface.max()) + 1
    packed = np.zeros(surface.shape, np.int32)
    opaque = surface > 0
    # These labels contain NO swatch; they encode only source SLIC and parent.
    packed[opaque] = fine[opaque].astype(np.int32) * main_n + surface[opaque]
    initial = spatial._connected(packed)
    n = int(initial.max())
    if not n:
        return initial, {"initial_patch_regions": 0, "patch_unions": 0}
    ids = initial[opaque]
    parent_main = np.zeros(n + 1, np.int32)
    parent_main[ids] = surface[opaque]
    area, sums, _ = spatial._lab_means(initial, lab)
    pairs, lengths, contrast, strong_fraction = spatial._boundary_stats(initial, lab)
    uf = np.arange(n + 1, dtype=np.int32)
    total = sums.copy()
    mass = area.copy()

    def find(v: int) -> int:
        while uf[v] != v:
            uf[v] = uf[int(uf[v])]
            v = int(uf[v])
        return v

    order = sorted(range(len(pairs)), key=lambda i: (
        float(contrast[i]), -int(lengths[i]),
        int(pairs[i, 0]), int(pairs[i, 1])))
    accepted = 0
    for i in order:
        a, b = int(pairs[i, 0]), int(pairs[i, 1])
        if parent_main[a] != parent_main[b]:
            continue
        if (contrast[i] > BORDER_MEAN_LAB
                or strong_fraction[i] > BORDER_STRONG_FRACTION):
            continue
        a, b = find(a), find(b)
        if a == b:
            continue
        if np.linalg.norm(total[a] / mass[a] - total[b] / mass[b]) > PATCH_MEAN_LAB:
            continue
        left, right = sorted((a, b))
        uf[right] = left
        mass[left] += mass[right]
        total[left] += total[right]
        accepted += 1

    mapped = np.array([find(i) for i in range(n + 1)], np.int32)
    patches = spatial._connected(mapped[initial])
    if np.any(patches[~opaque]) or np.any(patches[opaque] == 0):
        raise ValueError("BLOCKED_RAG5_PATCH_ALPHA_OR_CONNECTION")
    return patches, {"initial_patch_regions": n, "patch_unions": accepted}


def _choose_color(samples_rgb: np.ndarray, palette: np.ndarray,
                  game_lab: np.ndarray, tree: cKDTree):
    """Minimize actual aggregate original RGB L1 among fixed source candidates."""
    sample = samples_rgb.astype(np.float64)
    median = np.median(sample, axis=0)
    median_lab = color.rgb2lab((median / 255.0).reshape(1, 1, 3)).reshape(3)
    near = tree.query(median_lab, k=PALETTE_CANDIDATES_LAB, workers=1)[1]
    near_rgb = int(np.argmin(np.abs(
        palette.astype(np.float64) - median[None, :]).sum(axis=1)))
    candidates = sorted(set(int(v) for v in np.ravel(near)) | {near_rgb})
    loss = np.abs(sample[:, None, :] -
                  palette[np.asarray(candidates, np.intp)][None, :, :]).sum(axis=(0, 2))
    # Exact deterministic tie-break on palette index, not arbitrary tree order.
    best = min(range(len(candidates)), key=lambda k: (float(loss[k]), candidates[k]))
    return candidates[best]


def _patch_palette(patches: np.ndarray, surface: np.ndarray, rgba: np.ndarray,
                   palette: np.ndarray, game_lab: np.ndarray, tree: cKDTree):
    n = int(patches.max())
    parents = np.zeros(n + 1, np.int32)
    colors = np.full(n + 1, -1, np.int16)
    mean_lab = np.zeros((n + 1, 3), np.float64)
    rgb = rgba[:, :, :3]
    # Deterministic full-original connected source patches, no palette seed.
    for rid, sl in enumerate(ndimage.find_objects(patches), 1):
        if sl is None:
            raise ValueError("BLOCKED_RAG5_EMPTY_SOURCE_PATCH")
        mask = patches[sl] == rid
        sample = rgb[sl][mask]
        if not len(sample):
            raise ValueError("BLOCKED_RAG5_EMPTY_SOURCE_PATCH_PIXELS")
        parent_values = surface[sl][mask]
        if not np.all(parent_values == parent_values[0]):
            raise ValueError("BLOCKED_RAG5_PATCH_SPANS_TWO_MAINS")
        parents[rid] = int(parent_values[0])
        mean_lab[rid] = np.mean(color.rgb2lab(
            sample.astype(np.float64).reshape(1, -1, 3) / 255.0).reshape(-1, 3), axis=0)
        colors[rid] = _choose_color(sample, palette, game_lab, tree)
    return parents, colors, mean_lab


def _connected_source_detail_candidates(candidate: np.ndarray,
                                        surface: np.ndarray, lab: np.ndarray):
    """Join 4-neighbor *source Lab similar* detail pixels, not palette IDs."""
    h, w = candidate.shape
    positions = np.flatnonzero(candidate.ravel())
    n = len(positions)
    output = np.zeros((h, w), np.int32)
    if not n:
        return output, 0
    local = np.full(h * w, -1, np.int32)
    local[positions] = np.arange(n, dtype=np.int32)
    local = local.reshape(h, w)
    uf = np.arange(n, dtype=np.int32)

    def find(v):
        while int(uf[v]) != v:
            uf[v] = uf[int(uf[v])]
            v = int(uf[v])
        return v

    for a, b, sa, sb, la, lb in (
        (local[:, :-1], local[:, 1:], surface[:, :-1], surface[:, 1:],
         lab[:, :-1], lab[:, 1:]),
        (local[:-1, :], local[1:, :], surface[:-1], surface[1:],
         lab[:-1], lab[1:]),
    ):
        allowed = ((a >= 0) & (b >= 0) & (sa == sb) & (sa > 0) &
                   (np.linalg.norm(la - lb, axis=2) <= DETAIL_ADJACENT_LAB))
        for left, right in zip(a[allowed], b[allowed]):
            ra, rb = find(int(left)), find(int(right))
            if ra != rb:
                lo, hi = sorted((ra, rb))
                uf[hi] = lo
    root = np.fromiter((find(i) for i in range(n)), dtype=np.int32, count=n)
    _, canonical = np.unique(root, return_inverse=True)
    output.ravel()[positions] = canonical.astype(np.int32) + 1
    return output, int(canonical.max()) + 1


def _strong_details(rgba: np.ndarray, surface: np.ndarray,
                    patches: np.ndarray, patch_color: np.ndarray,
                    patch_mean_lab: np.ndarray, source_edge: np.ndarray,
                    lab: np.ndarray, palette: np.ndarray,
                    game_lab: np.ndarray, tree: cKDTree):
    opaque = surface > 0
    base = patch_color[patches]
    base_lab = game_lab[np.maximum(base, 0)]
    residual = np.linalg.norm(lab - patch_mean_lab[patches], axis=2)
    color_residual = np.linalg.norm(lab - base_lab, axis=2)
    candidate = (opaque & source_edge &
                 (residual >= STRONG_DETAIL_DEVIATION_LAB) &
                 (color_residual >= STRONG_DETAIL_DEVIATION_LAB))
    groups, n = _connected_source_detail_candidates(candidate, surface, lab)
    selected = np.zeros(n + 1, bool)
    proposed = np.full(n + 1, -1, np.int16)
    parent_main = np.zeros(n + 1, np.int32)
    rgb = rgba[:, :, :3]
    proposed[0] = -1
    for rid, sl in enumerate(ndimage.find_objects(groups), 1):
        if sl is None:
            raise ValueError("BLOCKED_RAG5_EMPTY_SOURCE_DETAIL")
        mask = groups[sl] == rid
        samples = rgb[sl][mask]
        base_swatches = base[sl][mask]
        main_ids = surface[sl][mask]
        if not np.all(main_ids == main_ids[0]):
            raise ValueError("BLOCKED_RAG5_DETAIL_CROSSES_MAIN")
        parent_main[rid] = int(main_ids[0])
        target = _choose_color(samples, palette, game_lab, tree)
        old_loss = float(np.abs(samples.astype(np.float64) -
                                palette[base_swatches].astype(np.float64)).mean())
        new_loss = float(np.abs(samples.astype(np.float64) -
                                palette[target].astype(np.float64)).mean())
        if (np.any(base_swatches != target)
                and old_loss - new_loss >= DETAIL_IMPROVEMENT_RGB):
            proposed[rid] = target
            selected[rid] = True
    accepted = np.flatnonzero(selected)
    map_ids = np.zeros(n + 1, np.int32)
    map_ids[accepted] = np.arange(1, len(accepted) + 1, dtype=np.int32)
    details = map_ids[groups]
    parents = np.zeros(len(accepted) + 1, np.int32)
    colors = np.full(len(accepted) + 1, -1, np.int16)
    parents[1:] = parent_main[accepted]
    colors[1:] = proposed[accepted]
    return details, parents, colors, {
        "detail_source_candidates": int(candidate.sum()),
        "detail_components": n,
        "details_accepted": int(len(accepted)),
        "detail_pixels": int(np.count_nonzero(details)),
    }


def build_rag5(original_rgba: np.ndarray, game128: np.ndarray) -> dict:
    _check_input(original_rgba, game128)
    rgba = original_rgba
    h, w = rgba.shape[:2]
    opaque = rgba[:, :, 3] == 255
    if not opaque.any():
        return _blank(rgba)

    # RAG3 helpers compute fresh source geometry only. No old artwork is an input.
    original_maps = source.generic_source_maps(rgba)
    first = source.original_source_region_uncertainty(rgba, original_maps)
    slic = spatial._connected(first["region_ids"])
    if np.any(slic[opaque] <= 0) or np.any(slic[~opaque]):
        raise ValueError("BLOCKED_RAG5_COARSE_SOURCE_SLIC")
    lab = color.rgb2lab(rgba[:, :, :3].astype(np.float64) / 255.0)
    merged, main_stats = spatial._merge_slic(slic, lab)
    surfaces, split_count = spatial._split_confirmed_source_edges(merged, lab, opaque)
    if np.any(surfaces[opaque] <= 0) or np.any(surfaces[~opaque]):
        raise ValueError("BLOCKED_RAG5_MAIN_SOURCE_ALPHA")

    fine = _fresh_fine_slic(rgba, opaque)
    patches, patch_stats = _source_merge_patches(surfaces, fine, lab)
    palette_lab = color.rgb2lab(
        game128.reshape(1, 128, 3).astype(np.float64) / 255.0).reshape(128, 3)
    tree = cKDTree(palette_lab)
    parent, patch_color, patch_mean = _patch_palette(
        patches, surfaces, rgba, game128, palette_lab, tree)
    strong = spatial._original_strong_edges(lab, opaque, original_maps["source_edge"])
    details, detail_parent, detail_color, detail_stats = _strong_details(
        rgba, surfaces, patches, patch_color, patch_mean,
        strong, lab, game128, palette_lab, tree)
    composed = np.full((h, w), -1, np.int16)
    composed[opaque] = patch_color[patches[opaque]]
    overlay = details > 0
    composed[overlay] = detail_color[details[overlay]]

    # Source-only independent fresh baseline, NEVER a geometry seed.
    baseline = np.full((h, w), -1, np.int16)
    selected = np.flatnonzero(opaque.ravel())
    base_flat = baseline.ravel()
    lab_flat = lab.reshape(-1, 3)
    for start in range(0, len(selected), CHUNK):
        pos = selected[start:start + CHUNK]
        base_flat[pos] = tree.query(lab_flat[pos], k=1, workers=1)[1].astype(np.int16)

    paintable = np.zeros((h, w), np.int32)
    # Encoded distinct main + swatch; a same-color patch may be separate
    # provenance but never forces a redundant paintable component.
    encoded = np.zeros((h, w), np.int32)
    encoded[opaque] = surfaces[opaque] * 128 + composed[opaque] + 1
    paintable = spatial._connected(encoded)
    neighbors, _, _, _ = spatial._boundary_stats(surfaces, lab)
    preview = rgba.copy()
    preview[opaque, :3] = game128[composed[opaque]]
    if (np.any(patches[~opaque]) or np.any(details[~opaque])
            or np.any(paintable[~opaque]) or np.any(composed[~opaque] != -1)
            or np.any(baseline[~opaque] != -1)
            or np.any(parent[patches[opaque]] != surfaces[opaque])
            or np.any(detail_parent[details[overlay]] != surfaces[overlay])
            or np.any(detail_color[details[overlay]] != composed[overlay])
            or not np.array_equal(preview[:, :, 3], rgba[:, :, 3])):
        raise ValueError("BLOCKED_RAG5_SOURCE_LAYER_PARENT_ALPHA")
    return {
        "version": VERSION, "surface_id": surfaces, "patch_id": patches,
        "patch_parent_surface_id": parent, "patch_color_index": patch_color,
        "detail_id": details, "detail_parent_surface_id": detail_parent,
        "detail_color_index": detail_color, "paintable_id": paintable,
        "game_index": composed, "baseline_index": baseline,
        "preview_rgba": preview, "source_edge": strong,
        "unknown": np.ones((h, w), bool), "adjacency": neighbors,
        "source_to_logical": source.letterbox_binding((w, h)),
        "source_owner_status": "MISSING",
        "stroke_admission": "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE",
        "counts": {
            **main_stats, **patch_stats, **detail_stats,
            "confirmed_splits": int(split_count),
            "main_surfaces": int(surfaces.max()),
            "fine_slic_segments": int(fine.max()),
            "patches": int(patches.max()),
            "paintable_components": int(paintable.max()),
            "game_colors": int(np.unique(composed[opaque]).size),
            "opaque_pixels": int(np.count_nonzero(opaque)),
        },
    }


def _palette_islands(index: np.ndarray) -> dict:
    counts, singletons = 0, 0
    for swatch in np.unique(index[index >= 0]):
        labels, n = ndimage.label(index == swatch, structure=np.ones((3, 3), bool))
        area = np.bincount(labels.ravel())[1:]
        counts += n
        singletons += int(np.count_nonzero(area == 1))
    return {"components": int(counts), "singletons": int(singletons)}


def evaluate_rag5(rgba: np.ndarray, game128: np.ndarray, data: dict) -> dict:
    opaque = rgba[:, :, 3] == 255
    report = {
        "opaque": int(np.count_nonzero(opaque)), "counts": data["counts"],
        "baseline": _palette_islands(data["baseline_index"]),
        "candidate": _palette_islands(data["game_index"]),
    }
    if not opaque.any():
        return report
    rgb = rgba[:, :, :3][opaque].astype(np.float64)
    before = game128[data["baseline_index"][opaque]].astype(np.float64)
    after = game128[data["game_index"][opaque]].astype(np.float64)
    lab = color.rgb2lab(rgba[:, :, :3].astype(np.float64) / 255)
    composed_lab = color.rgb2lab(data["preview_rgba"][:, :, :3].astype(np.float64) / 255)
    report.update({
        "baseline_rgb_mae": float(np.abs(rgb - before).mean()),
        "candidate_rgb_mae": float(np.abs(rgb - after).mean()),
        "strong_source_contrast":
            spatial._retained_source_contrast(lab, composed_lab, opaque),
        "main_adjacency_edges": int(len(data["adjacency"])),
    })
    return report

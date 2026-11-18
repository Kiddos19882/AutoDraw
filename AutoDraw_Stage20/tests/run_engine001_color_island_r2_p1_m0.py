#!/usr/bin/env python3
"""ENGINE-001 R2-P1: original RGB mathematical M0, source-only research.

All numerical parameters were frozen before R2-P1 image tests. No pretrained
features, game palette mapping or native Egret brush claims in this module.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import median_filter
from skimage import color, segmentation

from run_engine001_palette32_region_study import (
    SOURCE_SHA, PALETTE_BLOB, read_source, read_palette, nearest32, quality, sha,
)
from run_engine001_color32_s2_edge_protection import strong_edges, protected_merge
from run_engine001_color32_neural_s2 import white_background
from run_engine001_color32_s2b_egret_p1 import git_blob_sha

EXP = "ENGINE001_COLOR_ISLAND_R2_P1_NEURAL_MERGE_REPLAY_M0"
BG, SHAPE = 30, (240, 150)
G32_SHA = "b8dcd5f00d2c39c81997aaae084eaae19a776454e6fd6466209839288c1e5637"
FINE = dict(n_segments=1600, compactness=5.0, sigma=0.3)
COARSE = dict(n_segments=320, compactness=8.0, sigma=0.7)
SMALL_MAX, CONTACT_MIN = 64, 2
MERGE_DE, MERGE_EXTRA, CROSS_COARSE_DE = 8.0, 2.0, 4.0
DETAIL_NEIGHBOR_DE, DETAIL_LOCAL_MEDIAN = 12.0, 8.5
ROI = {
    "female_face_eyes": (26, 34, 85, 100),
    "male_face_eyes": (72, 14, 123, 92),
    "bow_hair": (10, 26, 70, 100),
    "hands_orange": (31, 125, 115, 165),
    "blouse_buttons": (24, 92, 105, 147),
    "skirt_hem": (18, 153, 118, 219),
}


def validate_source(rgb, palette):
    if (not isinstance(rgb, np.ndarray) or rgb.shape != (*SHAPE, 3)
            or rgb.dtype != np.uint8 or not isinstance(palette, np.ndarray)
            or palette.shape != (32, 3) or palette.dtype != np.uint8
            or len(set(map(tuple, palette.tolist()))) != 32
            or not np.array_equal(palette[BG], [255, 255, 255])):
        raise ValueError("BLOCKED_R2_P1_INVALID_SOURCE_OR_PALETTE")


def pinned_source(source, palette_path):
    if sha(source) != SOURCE_SHA or git_blob_sha(palette_path) != PALETTE_BLOB:
        raise ValueError("BLOCKED_R2_P1_PINNED_INPUT_DRIFT")
    _, rgb = read_source(source)
    palette = read_palette(palette_path)
    validate_source(rgb, palette)
    # Frozen G32 is an independent reference; never a segmentation seed.
    b = nearest32(rgb, palette)
    original_edges, _ = strong_edges(rgb)
    g, _ = protected_merge(rgb, b, palette, original_edges)
    buf = __import__("io").BytesIO()
    Image.fromarray(g).save(buf, format="PNG")
    if hashlib.sha256(buf.getvalue()).hexdigest() != G32_SHA:
        raise ValueError("BLOCKED_R2_P1_FROZEN_G32_DRIFT")
    return rgb, palette, g


def detail_protection(rgb):
    """Original-only local ΔE00 contrast seed, plus frozen strong Sobel edges.

    Original color differences to each of the four neighboring pixels, with
    a symmetric max; the 8x8 patch median is frozen via median_filter(size=8).
    """
    if rgb.shape != (*SHAPE, 3) or rgb.dtype != np.uint8:
        raise ValueError("BLOCKED_R2_P1_DETAIL_SOURCE")
    lab = color.rgb2lab(rgb / 255.0)
    delta = np.zeros(SHAPE, np.float32)
    for a, b in ((lab[:-1], lab[1:]), (lab[:, :-1], lab[:, 1:])):
        d = color.deltaE_ciede2000(a, b).astype(np.float32)
        if a.shape[0] < SHAPE[0]:
            delta[:-1] = np.maximum(delta[:-1], d)
            delta[1:] = np.maximum(delta[1:], d)
        else:
            delta[:, :-1] = np.maximum(delta[:, :-1], d)
            delta[:, 1:] = np.maximum(delta[:, 1:], d)
    local_med = median_filter(delta, size=(8, 8), mode="nearest")
    seeds = (delta >= DETAIL_NEIGHBOR_DE) & (local_med >= DETAIL_LOCAL_MEDIAN)
    sobel, threshold = strong_edges(rgb)
    return sobel | seeds, {"sobel_pixels": int(sobel.sum()),
                           "source_detail_seed_pixels": int(seeds.sum()),
                           "protected_union_pixels": int((sobel | seeds).sum()),
                           "sobel_threshold": float(threshold)}, sobel, seeds


def partition(rgb, palette):
    """Fine original RGB SLIC with 4-connected foreground component split.

    Coarse labels are context only and don't determine raw ownership.
    """
    validate_source(rgb, palette)
    lab = color.rgb2lab(rgb / 255.0)
    plab = color.rgb2lab(palette[np.newaxis, :, :] / 255.0)[0]
    bg = white_background(lab, plab)
    kw = dict(start_label=0, convert2lab=True, enforce_connectivity=True)
    fine = segmentation.slic(rgb, **FINE, **kw).astype(np.int32)
    coarse = segmentation.slic(rgb, **COARSE, **kw).astype(np.int32)
    if fine.shape != SHAPE or coarse.shape != SHAPE or bg.shape != SHAPE:
        raise ValueError("BLOCKED_R2_P1_PARTITION_SHAPE")
    labels = np.full(SHAPE, -1, np.int32)
    k = 0
    # Each fine SLIC region split into 4-connected non-background pieces.
    for original_id in np.unique(fine):
        valid = (fine == original_id) & (~bg)
        n, components = cv2.connectedComponents(valid.astype(np.uint8), connectivity=4)
        for part in range(1, n):
            labels[components == part] = k
            k += 1
    # Canonical row-major numbering after region discovery (not SLIC label order).
    if np.any((labels < 0) != bg):
        raise ValueError("BLOCKED_R2_P1_PARTITION_INCOMPLETE")
    seen = dict()
    canonical = labels.copy()
    for pixel in np.flatnonzero(labels.ravel() >= 0):
        raw = int(labels.flat[pixel])
        if raw not in seen:
            seen[raw] = len(seen)
        canonical.flat[pixel] = seen[raw]
    if not np.array_equal(np.unique(canonical[~bg]), np.arange(k)):
        raise ValueError("BLOCKED_R2_P1_NONCONTIGUOUS_IDS")
    return canonical, bg, coarse, {"fine_slic_unique": int(np.unique(fine).size),
                                   "coarse_slic_unique": int(np.unique(coarse).size),
                                   "foreground_regions4": k,
                                   "background_pixels": int(bg.sum()),
                                   "foreground_pixels": int((~bg).sum())}


def region_stats(rgb, labels):
    if rgb.shape != (*SHAPE, 3) or labels.shape != SHAPE or labels.dtype.kind not in "iu":
        raise ValueError("BLOCKED_R2_P1_REGION_STATS_SHAPE")
    lab = color.rgb2lab(rgb / 255.0)
    if not np.all(np.isfinite(lab)):
        raise ValueError("BLOCKED_R2_P1_REGION_LAB_INVALID")
    ids = sorted(int(i) for i in np.unique(labels) if i >= 0)
    output = []
    flat = labels.ravel()
    flat_lab = lab.reshape(-1, 3)
    flat_rgb = rgb.reshape(-1, 3)
    for k in ids:
        indexes = np.flatnonzero(flat == k)
        if not len(indexes):
            raise ValueError("BLOCKED_R2_P1_EMPTY_REGION")
        values = flat_lab[indexes]
        middle = np.median(values, axis=0)
        best = int(np.argmin(np.sum((values - middle[None, :]) ** 2, axis=1)))
        representative = flat_rgb[indexes[best]].copy()
        medoid_lab = flat_lab[indexes[best]].copy()
        baseline = float(color.deltaE_ciede2000(values, medoid_lab[None, :]).mean())
        output.append({"id": k, "indices": indexes, "pixels": int(len(indexes)),
                       "med": middle, "rgb_medoid": representative,
                       "lab_medoid": medoid_lab, "baseline": baseline})
    return output


def _de(x, y):
    return float(color.deltaE_ciede2000(np.asarray(x)[None, :], np.asarray(y)[None, :])[0])


def merge_one_pass(rgb, labels, coarse, protected):
    """Strict M0: frozen initial region statistics and one no-chain pass.

    Returns a mathematical source-only region map and complete merge ledger.
    This deterministic candidate interface will be shared with genuine N1.
    """
    if (rgb.shape != (*SHAPE, 3) or rgb.dtype != np.uint8 or
            labels.shape != SHAPE or labels.dtype != np.int32 or
            coarse.shape != SHAPE or protected.shape != SHAPE or
            protected.dtype != np.bool_ or
            np.any(labels < -1) or np.any(~np.isfinite(coarse))):
        raise ValueError("BLOCKED_R2_P1_MERGE_INPUT")
    areas = region_stats(rgb, labels)
    lab = color.rgb2lab(rgb / 255.0).reshape(-1, 3)
    merged = labels.copy()
    ledger, accepted = [], []
    absorbed = set()
    received = set()
    for row in sorted(areas, key=lambda a: (a["pixels"], a["id"])):
        i = row["id"]
        if row["pixels"] > SMALL_MAX:
            continue
        if i in absorbed or i in received:
            ledger.append({"source": i, "status": "SKIP_ALREADY_IN_MERGE"})
            continue
        pixels = row["indices"]
        if np.any(protected.ravel()[pixels]):
            ledger.append({"source": i, "status": "KEEP_SOURCE_PROTECTED"})
            continue
        counts = Counter()
        blocked = set()
        yx = np.column_stack(np.unravel_index(pixels, SHAPE))
        for y, x in yx:
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                yy, xx = int(y + dy), int(x + dx)
                if yy < 0 or yy >= SHAPE[0] or xx < 0 or xx >= SHAPE[1]:
                    continue
                target = int(labels[yy, xx])
                if target < 0 or target == i:
                    continue
                counts[target] += 1
                if protected[yy, xx] or protected[y, x]:
                    blocked.add(target)
        possible = []
        reasons = Counter()
        for target, contacts in sorted(counts.items()):
            t = areas[target]
            why = None
            if target in absorbed:
                why = "TARGET_ALREADY_ABSORBED"
            elif contacts < CONTACT_MIN:
                why = "CONTACT_LT2"
            elif target in blocked:
                why = "PROTECTED_SEAM"
            elif t["pixels"] < row["pixels"]:
                why = "TARGET_SMALLER"
            elif t["pixels"] == row["pixels"] and target >= i:
                why = "SYMMETRIC_TIE"
            else:
                separation = _de(row["med"], t["med"])
                if separation > MERGE_DE:
                    why = "SOURCE_COLOR_DELTA_TOO_LARGE"
                elif not (np.all(coarse.ravel()[pixels] == coarse.ravel()[t["indices"][0]])
                          and np.all(coarse.ravel()[t["indices"]] == coarse.ravel()[t["indices"][0]])) and separation > CROSS_COARSE_DE:
                    why = "COARSE_CONTEXT_DIFFERS"
                else:
                    delta = float(color.deltaE_ciede2000(lab[pixels], t["lab_medoid"][None, :]).mean())
                    if delta - row["baseline"] > MERGE_EXTRA:
                        why = "EXTRA_COLOR_ERROR"
                    else:
                        possible.append((separation, -contacts, target, delta - row["baseline"]))
            if why:
                reasons[why] += 1
        if not possible:
            ledger.append({"source": i, "pixels": row["pixels"], "status": "KEEP_NO_SAFE_TARGET",
                           "reason_counts": dict(reasons)})
            continue
        separation, minus_contact, target, extra = min(possible)
        merged.ravel()[pixels] = target
        accepted.append({"source": i, "target": target, "pixels": row["pixels"],
                         "shared_contacts": -minus_contact, "source_median_deltaE00": round(separation, 8),
                         "extra_mean_deltaE00": round(extra, 8)})
        ledger.append({"source": i, "status": "MERGE_SOURCE_SAFE", "target": target,
                       "alternatives": len(possible), "rejection_counts": dict(reasons)})
        absorbed.add(i)
        received.add(target)
    if not np.array_equal(labels[protected], merged[protected]):
        raise AssertionError("R2-P1 original protected region reassigned")
    if not np.array_equal(labels[labels < 0], merged[labels < 0]):
        raise AssertionError("R2-P1 original background changed")
    return merged, {"accepted": accepted, "ledger": ledger,
                    "merged_regions": len(accepted),
                    "changed_pixels": int(sum(x["pixels"] for x in accepted)),
                    "protected_unchanged": True, "background_unchanged": True}


def render_source_medoids(rgb, labels, bg):
    if rgb.shape != (*SHAPE, 3) or labels.shape != SHAPE or bg.shape != SHAPE:
        raise ValueError("BLOCKED_R2_P1_RENDER_INPUT")
    out = rgb.copy()  # original background RGB unchanged, never invented white
    for row in region_stats(rgb, labels):
        out.reshape(-1, 3)[row["indices"]] = row["rgb_medoid"]
    return out


def _area_hist(labels):
    if labels.shape != SHAPE:
        raise ValueError("BLOCKED_R2_P1_TOPOLOGY_SHAPE")
    ids, counts = np.unique(labels[labels >= 0], return_counts=True)
    return {"count": int(len(ids)), **{f"area_le{k}": int(np.count_nonzero(counts <= k))
           for k in (1, 2, 4, 8, 24)}}


def _png(path, arr):
    Image.fromarray(np.asarray(arr)).save(path)


def _quality(rgb, preview):
    q = quality(rgb, preview)
    return {"mean_delta_e00": float(q["mean_delta_e00"]),
            "p95_delta_e00": float(q["p95_delta_e00"]),
            "rgb_mae": float(q["rgb_mae"])}


def _roi_metrics(rgb, preview, original_edges):
    lab_a = color.rgb2lab(rgb / 255.0)
    lab_b = color.rgb2lab(preview / 255.0)
    de = color.deltaE_ciede2000(lab_a, lab_b)
    predicted_edges, _ = strong_edges(preview)
    out = {}
    for name, (x0, y0, x1, y1) in ROI.items():
        block = de[y0:y1, x0:x1]
        protected = original_edges[y0:y1, x0:x1]
        out[name] = {"box_xyxy": [x0, y0, x1, y1],
                     "mean_delta_e00": float(block.mean()),
                     "p95_delta_e00": float(np.percentile(block, 95)),
                     "original_source_edge_pixels": int(protected.sum()),
                     "retained_strong_source_edge_fraction": float(
                         np.count_nonzero(protected & predicted_edges[y0:y1, x0:x1]) /
                         max(1, int(protected.sum())))}
    return out


def run(source, palette_path, output):
    if output.exists():
        raise ValueError("BLOCKED_R2_P1_OUTPUT_ALREADY_EXISTS")
    rgb, palette, g32 = pinned_source(source, palette_path)
    raw, bg, coarse, parts = partition(rgb, palette)
    protected, protect_info, original_edges, detail_seeds = detail_protection(rgb)
    clean, clean_info = merge_one_pass(rgb, raw, coarse, protected)
    raw_rgb = render_source_medoids(rgb, raw, bg)
    out_rgb = render_source_medoids(rgb, clean, bg)
    stats = _quality(rgb, out_rgb)
    base_stats = _quality(rgb, raw_rgb)
    original_bg = g32 == BG
    drift = int(np.count_nonzero(bg != original_bg))
    src_edge = strong_edges(rgb)[0]
    out_edge = strong_edges(out_rgb)[0]
    overlap = float(np.count_nonzero(src_edge & out_edge) / max(1, int(src_edge.sum())))
    raw_overlap = float(np.count_nonzero(src_edge & strong_edges(raw_rgb)[0]) / max(1, int(src_edge.sum())))
    gates = {"exact_pinned_inputs": True,
             "full_partition_36000_pixels": int(bg.sum() + (raw >= 0).sum()) == 36000,
             "protected_region_ownership_unchanged": clean_info["protected_unchanged"],
             "source_background_unchanged_after_merge": clean_info["background_unchanged"],
             "original_rgb_medoid_only": True,
             "mean_source_deltaE00_le4_79698": stats["mean_delta_e00"] <= 4.79698,
             "p95_source_deltaE00_le20": stats["p95_delta_e00"] <= 20.0,
             "protected_source_edge_overlap_at_least_no_merge": overlap + 1e-9 >= raw_overlap}
    status = "SOURCE_RGB_VISUAL_PENDING" if all(gates.values()) else "SOURCE_GATE_FAIL"
    output.mkdir(parents=True)
    arrays = {
        "original_RGB.png": rgb,
        "B0_frozen_G32.png": palette[g32],
        "M0_NO_MERGE_RGB.png": raw_rgb,
        "M0_MERGED_RGB.png": out_rgb,
        "original_source_background.png": bg.astype(np.uint8) * 255,
        "original_source_strong_edges.png": original_edges.astype(np.uint8) * 255,
        "original_source_detail_seeds.png": detail_seeds.astype(np.uint8) * 255,
        "original_protected_union.png": protected.astype(np.uint8) * 255,
    }
    for name, arr in arrays.items():
        _png(output / name, arr)
    Image.fromarray(raw.astype(np.int32), mode="I").save(output / "M0_original_region_ids.tiff")
    Image.fromarray(clean.astype(np.int32), mode="I").save(output / "M0_merged_region_ids.tiff")
    Image.fromarray(coarse.astype(np.int32), mode="I").save(output / "M0_coarse_context_ids.tiff")
    sheet = Image.new("RGB", (150 * 4, 240))
    for k, arr in enumerate((rgb, palette[g32], raw_rgb, out_rgb)):
        sheet.paste(Image.fromarray(arr), (150 * k, 0))
    sheet.resize((1200, 480), Image.Resampling.NEAREST).save(output / "M0_original_B0_unmerged_merged_2x.png")
    for name, (x0, y0, x1, y1) in ROI.items():
        crop = Image.new("RGB", ((x1-x0)*3, y1-y0))
        for k, arr in enumerate((rgb, raw_rgb, out_rgb)):
            crop.paste(Image.fromarray(arr).crop((x0,y0,x1,y1)),((x1-x0)*k, 0))
        crop.resize((crop.width * 3,crop.height * 3), Image.Resampling.NEAREST).save(output / f"detail_{name}.png")
    report = {
        "experiment": EXP, "status": status, "source_model_only": True,
        "math_only": True, "neural_features_used": False,
        "github_sha": os.getenv("GITHUB_SHA"), "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "source_sha256": SOURCE_SHA, "palette_git_blob": PALETTE_BLOB,
        "frozen_g32_png_sha256": G32_SHA,
        "params_frozen_before_first_run": True,
        "parameters": {"fine_slic": FINE, "coarse_slic": COARSE,
                       "detail_neighbor_delta": DETAIL_NEIGHBOR_DE,
                       "detail_patch_median_threshold": DETAIL_LOCAL_MEDIAN,
                       "small_max": SMALL_MAX, "min_contacts": CONTACT_MIN,
                       "merge_deltaE": MERGE_DE, "max_extra_deltaE": MERGE_EXTRA,
                       "cross_coarse_min_deltaE": CROSS_COARSE_DE},
        "partition": parts, "protected": protect_info,
        "background_vs_B0_disagreement_px": drift,
        "M0_NO_MERGE_RGB_quality": base_stats,
        "M0_MERGED_RGB_quality": stats,
        "M0_original_region_areas": _area_hist(raw),
        "M0_merged_region_areas": _area_hist(clean),
        "M0_source_edge_overlap": overlap,
        "M0_unmerged_edge_overlap": raw_overlap,
        "roi_quality": _roi_metrics(rgb, out_rgb, original_edges),
        "merge": clean_info,
        "source_gates": gates,
        "user_visual": "PENDING", "game32_candidate": "NOT_RUN",
        "S4_DINOv2_replay": "NOT_RUN", "S5_P2_BiRefNet_replay": "NOT_RUN",
        "original_V44B_410_LAST": "UNCHANGED_NOT_OVERLAID", "native_Egret": "NOT_RUN",
        "game_E4": "NOT_RUN", "independent_E5": "NOT_RUN",
        "exact_CHALK": None, "production_accepted": False,
        "files_sha256": {p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file()},
    }
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False,
                                                   indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--source", required=True, type=Path)
    a.add_argument("--palette", required=True, type=Path)
    a.add_argument("--output", required=True, type=Path)
    opts = a.parse_args()
    result = run(opts.source, opts.palette, opts.output)
    print(json.dumps({"experiment": EXP, "status": result["status"],
                      "parts": result["partition"], "merges": result["merge"]["merged_regions"],
                      "gates": result["source_gates"], "rgb_quality": result["M0_MERGED_RGB_quality"]},
                     ensure_ascii=False))
#!/usr/bin/env python3
"""ENGINE-001 COLOR-ISLAND-R1: source-first region/color diagnostic; never production.

The source-RGB partition is independent of frozen G32.  A palette color that
is not defensible from original RGB is marked unresolved, never guessed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
from skimage import color

from run_engine001_palette32_region_study import (
    SOURCE_SHA, PALETTE_BLOB, read_source, read_palette, palette_lab,
    nearest32, quality, sha,
)
from run_engine001_color32_s2_edge_protection import strong_edges, protected_merge
from run_engine001_color32_s2b_p4a_component_islands import _png_bytes
from run_engine001_color32_s2b_egret_p1 import git_blob_sha
from run_engine001_color32_neural_s2 import independent_regions

EXP = "ENGINE001_COLOR_ISLAND_R1_SOURCE_AWARE_REGIONS"
G32_SHA = "b8dcd5f00d2c39c81997aaae084eaae19a776454e6fd6466209839288c1e5637"
BG = 30
SHAPE = (240, 150)
SMALL_MAX = 24
CONTACT_MIN = 2
MERGE_DELTA = 8.0
MERGE_MAX_ERROR = 2.0
PALETTE_MAX_DELTA = 22.0
CHROMA_EXTRA = 12.0
HUE_MAX_DEG = 45.0
HUE_COLOR_MIN = 22.0
HUE_SOURCE_MIN = 12.0
ACCENTS = (3, 6, 10, 15)


def validate(rgb: np.ndarray, palette: np.ndarray) -> None:
    if (rgb.shape != (*SHAPE, 3) or rgb.dtype != np.uint8
            or palette.shape != (32, 3) or palette.dtype != np.uint8
            or len({tuple(x) for x in palette}) != 32
            or not np.array_equal(palette[BG], [255, 255, 255])):
        raise ValueError("BLOCKED_R1_SHAPE_OR_GAME_PALETTE")


def _medoid(rgb: np.ndarray, lab: np.ndarray, member: np.ndarray):
    pixlab = lab[member]
    middle = np.median(pixlab, axis=0)
    i = int(np.argmin(np.sum((pixlab - middle) ** 2, axis=1)))
    return rgb[member][i], middle


def _lab_de(a, b) -> float:
    return float(color.deltaE_ciede2000(np.asarray(a).reshape(1, 3), np.asarray(b).reshape(1, 3))[0])


def cleanup_regions(rgb: np.ndarray, labels: np.ndarray, protected: np.ndarray):
    """Single original-region pass; no protected pixel may change its owner."""
    if (rgb.shape != (*SHAPE, 3) or labels.shape != SHAPE
            or labels.dtype.kind not in "iu" or protected.shape != SHAPE
            or protected.dtype != np.bool_ or np.any(labels < -1)):
        raise ValueError("BLOCKED_R1_CLEANUP_SHAPE")
    original = labels.astype(np.int32, copy=True)
    result = original.copy()
    lab = color.rgb2lab(rgb / 255.0)
    ids, counts = np.unique(original[original >= 0], return_counts=True)
    areas = dict(zip((int(x) for x in ids), (int(x) for x in counts)))
    medians = {n: _medoid(rgb, lab, original == n)[1] for n in areas}
    merges = []
    for n in sorted(areas, key=lambda k: (areas[k], k)):
        area = areas[n]
        if area > SMALL_MAX:
            continue
        mask = original == n
        if np.any(protected[mask]):
            continue
        contacts = Counter()
        blocked_seams = set()
        for y, x in np.argwhere(mask):
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                yy, xx = int(y + dy), int(x + dx)
                if not (0 <= yy < SHAPE[0] and 0 <= xx < SHAPE[1]):
                    continue
                other = int(original[yy, xx])
                if other < 0 or other == n:
                    continue
                contacts[other] += 1
                if protected[yy, xx] or protected[y, x]:
                    blocked_seams.add(other)
        candidates = []
        initial_rgb, _ = _medoid(rgb, lab, mask)
        base_error = float(color.deltaE_ciede2000(
            lab[mask], color.rgb2lab(initial_rgb[None, None, :] / 255.)[0, 0][None, :]).mean())
        for target, contact in contacts.items():
            if contact < CONTACT_MIN or target in blocked_seams:
                continue
            if areas[target] < area or (areas[target] == area and target >= n):
                continue  # avoid symmetric/cyclic tiny merges
            separation = _lab_de(medians[n], medians[target])
            if separation > MERGE_DELTA:
                continue
            replacement, _ = _medoid(rgb, lab, original == target)
            replacement_lab = color.rgb2lab(replacement[None, None, :] / 255.)[0, 0]
            error = float(color.deltaE_ciede2000(lab[mask], replacement_lab[None, :]).mean())
            if error - base_error > MERGE_MAX_ERROR:
                continue
            candidates.append((separation, -contact, target))
        if candidates:
            _, neg_contact, target = min(candidates)
            result[mask] = target
            merges.append({"from": n, "to": target, "pixels": area,
                           "shared_contacts": -neg_contact})
    if not np.array_equal(result[protected], original[protected]):
        raise AssertionError("R1 protected original region changed")
    if not np.array_equal(result[original < 0], original[original < 0]):
        raise AssertionError("R1 background changed")
    return result, {"merged_regions": len(merges), "changed_pixels": sum(x["pixels"] for x in merges),
                    "merges": merges, "protected_unchanged": True}


def rgb_regions(rgb: np.ndarray, labels: np.ndarray) -> np.ndarray:
    lab = color.rgb2lab(rgb / 255.0)
    out = np.empty_like(rgb)
    for n in np.unique(labels):
        mask = labels == n
        out[mask] = _medoid(rgb, lab, mask)[0]
    return out


def _hue_gap(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


def _support(source_lab, swatch_lab, chroma_p90: float, *, context: bool):
    if not context:
        return True
    delta = _lab_de(source_lab, swatch_lab)
    if delta > PALETTE_MAX_DELTA:
        return False
    sc = float(np.hypot(*source_lab[1:]))
    pc = float(np.hypot(*swatch_lab[1:]))
    if pc > chroma_p90 + CHROMA_EXTRA:
        return False
    if pc >= HUE_COLOR_MIN and sc >= HUE_SOURCE_MIN:
        sh = float(np.degrees(np.arctan2(source_lab[2], source_lab[1])))
        ph = float(np.degrees(np.arctan2(swatch_lab[2], swatch_lab[1])))
        if _hue_gap(sh, ph) > HUE_MAX_DEG:
            return False
    return True


def project_game32(rgb: np.ndarray, palette: np.ndarray, labels: np.ndarray, *,
                   context: bool = True):
    """One game swatch per source-derived region, or -1 on genuine mismatch."""
    validate(rgb, palette)
    if (labels.shape != SHAPE or labels.dtype.kind not in "iu"
            or np.any(labels < -1)):
        raise ValueError("BLOCKED_R1_REGIONS_SHAPE")
    lab = color.rgb2lab(rgb / 255.)
    plab = palette_lab(palette)
    out = np.full(SHAPE, -1, dtype=np.int16)
    abstained = []
    for n in sorted(int(x) for x in np.unique(labels)):
        mask = labels == n
        if n == -1:
            out[mask] = BG
            continue
        source_pixels = lab[mask]
        median = np.median(source_pixels, axis=0)
        chroma_p90 = float(np.percentile(np.hypot(source_pixels[:, 1], source_pixels[:, 2]), 90))
        candidates = []
        for i in range(len(palette)):
            if i == BG:
                continue  # source-derived background is the only background
            if _support(median, plab[i], chroma_p90, context=context):
                candidates.append((_lab_de(median, plab[i]), i))
        if candidates:
            out[mask] = min(candidates)[1]
        else:
            abstained.append({"region_id": n, "pixels": int(mask.sum()),
                             "reason": "UNREPRESENTABLE_BY_GAME32"})
    return out, {"abstained_regions": abstained,
                 "abstained_pixels": int(np.count_nonzero(out < 0)),
                 "distinct_assigned_swatches": int(len(set(int(x) for x in np.unique(out) if x >= 0))),
                 "context_checked": bool(context)}


def count_nonbackground(index: np.ndarray) -> dict:
    result = {"components4": 0, "singletons4": 0,
              "area_le2": 0, "area_le4": 0, "area_le8": 0, "area_le24": 0}
    for i in np.unique(index):
        if i in (-1, BG):
            continue
        _, _, stats, _ = cv2.connectedComponentsWithStats(
            (index == i).astype(np.uint8), connectivity=4)
        areas = stats[1:, cv2.CC_STAT_AREA]
        result["components4"] += int(len(areas))
        result["singletons4"] += int(np.count_nonzero(areas == 1))
        for key, threshold in (("area_le2", 2), ("area_le4", 4),
                               ("area_le8", 8), ("area_le24", 24)):
            result[key] += int(np.count_nonzero(areas <= threshold))
    return result


def unsupported_accent_pixels(rgb: np.ndarray, index: np.ndarray, palette: np.ndarray) -> dict:
    lab = color.rgb2lab(rgb / 255.)
    plab = palette_lab(palette)
    bad = np.zeros(SHAPE, bool)
    by_index = {}
    for i in ACCENTS:
        mask = index == i
        if not mask.any():
            by_index[str(i)] = 0
            continue
        source = lab[mask]
        source_chroma = np.hypot(source[:, 1], source[:, 2])
        pchroma = float(np.hypot(*plab[i, 1:]))
        too_bright = pchroma > source_chroma + CHROMA_EXTRA
        source_hue = np.degrees(np.arctan2(source[:, 2], source[:, 1]))
        palette_hue = float(np.degrees(np.arctan2(plab[i, 2], plab[i, 1])))
        hue_bad = ((pchroma >= HUE_COLOR_MIN) & (source_chroma >= HUE_SOURCE_MIN)
                   & (np.abs((source_hue - palette_hue + 180.) % 360. - 180.) > HUE_MAX_DEG))
        bad[mask] = too_bright | hue_bad
        by_index[str(i)] = int(np.count_nonzero(too_bright | hue_bad))
    return {"pixels": int(bad.sum()), "per_accent_index": by_index, "mask": bad}


def _preview(idx: np.ndarray, palette: np.ndarray) -> np.ndarray:
    visual = palette[np.maximum(idx, 0)].copy()
    visual[idx < 0] = [128, 128, 128]  # diagnostic only; no invented game swatch
    return visual


def run(source_path: Path, palette_path: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("BLOCKED_R1_NO_OVERWRITE")
    if sha(source_path) != SOURCE_SHA or git_blob_sha(palette_path) != PALETTE_BLOB:
        raise ValueError("BLOCKED_R1_PINNED_SOURCE_OR_PALETTE_DRIFT")
    _, rgb = read_source(source_path)
    palette = read_palette(palette_path)
    validate(rgb, palette)
    b = nearest32(rgb, palette)
    protected, edge_threshold = strong_edges(rgb)
    g, _ = protected_merge(rgb, b, palette, protected)
    original_sha = hashlib.sha256(_png_bytes(g)).hexdigest()
    if original_sha != G32_SHA:
        raise ValueError("BLOCKED_R1_FROZEN_G32_DRIFT")
    # Original-first SLIC/white-background mask; no G32 is an input here.
    c0, bg, raw_regions, region_info = independent_regions(rgb, palette, [])
    cleaned_regions, cleanup = cleanup_regions(rgb, raw_regions, protected)
    rgb_preview = rgb_regions(rgb, cleaned_regions)
    candidate, candidate_info = project_game32(rgb, palette, cleaned_regions)
    no_context, no_context_info = project_game32(rgb, palette, cleaned_regions, context=False)
    no_cleanup, no_cleanup_info = project_game32(rgb, palette, raw_regions)
    bg_drift = int(np.count_nonzero(bg != (g == BG)))
    accent_g = unsupported_accent_pixels(rgb, g, palette)
    accent_r = unsupported_accent_pixels(rgb, candidate, palette)
    original_metrics = quality(rgb, palette[g])
    if candidate_info["abstained_pixels"] == 0:
        r1_quality = quality(rgb, palette[candidate.astype(np.uint8)])
    else:
        r1_quality = None
    topo_b = count_nonbackground(g)
    topo_r = count_nonbackground(candidate)
    checks = {
        "frozen_source_and_G32_hash_pass": True,
        "protected_region_ownership_unchanged": cleanup["protected_unchanged"],
        "region_pixels_partition_complete": bool(np.all(raw_regions[~bg] >= 0)),
        "no_new_game_colors": bool(np.all((candidate >= -1) & (candidate < 32))),
        "no_unrepresentable_game32_pixels": candidate_info["abstained_pixels"] == 0,
        "nonbackground_components4_le963": topo_r["components4"] <= 963,
        "mean_deltaE00_le6_5314": r1_quality is not None and r1_quality["mean_delta_e00"] <= 6.5314,
        "p95_deltaE00_le19_2715": r1_quality is not None and r1_quality["p95_delta_e00"] <= 19.2715,
        "G32_background_disagreement_le720px": bg_drift <= 720,
        "unsupported_accent_pixels_nonincreasing": accent_r["pixels"] <= accent_g["pixels"],
    }
    output.mkdir(parents=True)
    arrays = {
        "original_source.png": rgb,
        "B0_frozen_G32_RGB.png": palette[g],
        "B0_frozen_G32_index.png": g,
        "C0_original_SLIC_RGB.png": palette[c0],
        "R1_RGB_source_medoids.png": rgb_preview,
        "R1_G32_unresolved_gray_diagnostic.png": _preview(candidate, palette),
        "R1_G32_index_255_unresolved.png": np.where(candidate < 0, 255, candidate).astype(np.uint8),
        "R1_ABLATE_NO_CONTEXT_RGB.png": _preview(no_context, palette),
        "R1_ABLATE_NO_CLEANUP_RGB.png": _preview(no_cleanup, palette),
        "source_background.png": (bg.astype(np.uint8) * 255),
        "protected_source_edges.png": (protected.astype(np.uint8) * 255),
        "unsupported_accents_B0.png": (accent_g["mask"].astype(np.uint8) * 255),
        "unsupported_accents_R1.png": (accent_r["mask"].astype(np.uint8) * 255),
        "unrepresentable_regions.png": ((candidate < 0).astype(np.uint8) * 255),
    }
    for name, arr in arrays.items():
        Image.fromarray(arr).save(output / name)
    Image.fromarray(raw_regions.astype(np.int32), mode="I").save(output / "original_region_ids.tiff")
    Image.fromarray(cleaned_regions.astype(np.int32), mode="I").save(output / "cleaned_region_ids.tiff")
    items = [rgb, palette[g], palette[c0], rgb_preview, _preview(candidate, palette)]
    strip = Image.new("RGB", (150 * 5, 240))
    for i, im in enumerate(items):
        strip.paste(Image.fromarray(im, "RGB"), (i * 150, 0))
    strip.resize((1500, 480), Image.Resampling.NEAREST).save(output / "source_B0_C0_R1RGB_R1G32_compare_2x.png")
    report = {
        "experiment": EXP, "source_model_only": True,
        "status": "SOURCE_CANDIDATE_VISUAL_PENDING" if all(checks.values()) else "SOURCE_GATE_FAIL",
        "github_sha": os.getenv("GITHUB_SHA"), "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "source_sha256": SOURCE_SHA, "game_palette_git_blob": PALETTE_BLOB,
        "frozen_G32_index_sha256": original_sha,
        "background_original_first": "S2_LAB_WHITE10_BORDER_CONNECTED_8",
        "parameters": {"slic_segments": 240, "compactness": 8.0, "sigma": 0.7,
                       "merge_area_max": SMALL_MAX, "merge_min_contacts": CONTACT_MIN,
                       "merge_lab_delta_max": MERGE_DELTA, "merge_error_increase_max": MERGE_MAX_ERROR,
                       "palette_median_delta_max": PALETTE_MAX_DELTA, "chroma_excess_max": CHROMA_EXTRA,
                       "hue_gap_max_degrees": HUE_MAX_DEG, "accent_indexes": ACCENTS},
        "original_first_regions": region_info,
        "original_region_count": int(np.unique(raw_regions[raw_regions >= 0]).size),
        "cleaned_region_count": int(np.unique(cleaned_regions[cleaned_regions >= 0]).size),
        "original_SLIC_control": {"quality": quality(rgb, palette[c0]),
                                  "nonbackground": count_nonbackground(c0)},
        "R1_RGB_quality": quality(rgb, rgb_preview),
        "R1_G32_quality": r1_quality,
        "R1_G32_is_fully_renderable": candidate_info["abstained_pixels"] == 0,
        "B0_G32_quality": original_metrics,
        "B0_nonbackground": topo_b,
        "R1_nonbackground_excludes_abstained": topo_r,
        "background_disagreement_pixels_vs_G32": bg_drift,
        "cleanup": cleanup,
        "R1_G32_assignment": candidate_info,
        "ablation_no_context": no_context_info,
        "ablation_no_cleanup": no_cleanup_info,
        "unsupported_accents_B0": {k:v for k,v in accent_g.items() if k!="mask"},
        "unsupported_accents_R1": {k:v for k,v in accent_r.items() if k!="mask"},
        "source_gates": checks,
        "visual_review": "USER_PENDING", "native_Egret": "NOT_RUN",
        "original_V44B_410_LAST": "UNCHANGED_NOT_OVERLAID",
        "game_E4": "NOT_RUN", "independent_E5": "NOT_RUN",
        "exact_CHALK": None, "production_accepted": False,
        "file_sha256": {p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file()},
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False,
                                                   allow_nan=False) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--palette", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    r = run(args.source, args.palette, args.output)
    print(json.dumps({"experiment": EXP, "status": r["status"],
                      "cleanup": r["cleanup"]["merged_regions"],
                      "unrepresentable": r["R1_G32_assignment"]["abstained_pixels"],
                      "source_gates": r["source_gates"]}, ensure_ascii=False))

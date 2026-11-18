#!/usr/bin/env python3
"""ENGINE001 B1-R-P2: original-only RGB regions and a jointly derived new outline.

Test-only evidence. Not a game32 palette, native Egret footprint or live CHALK.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
from pathlib import Path

import cv2
import numpy as np
import scipy
import skimage
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from skimage import color, filters, measure, morphology, segmentation

from run_engine001_b1r_p1_fullrgb_edge_aware import (
    FULL_SHAPE, LOGICAL_WH, ROIS_FULL, SOURCE_SHA256,
    check_source, compose_preview, filter_original, full_features,
    logical_rgb, original_outline_rgba,
)

EXPERIMENT = "ENGINE001_B1R_P2_JOINT_REGION_OUTLINE_V1"
VARIANTS = {
    "J_FINE": {"filter": "A_SOFT", "n_segments": 900, "compactness": 6.0},
    "J_COARSE": {"filter": "A_MID", "n_segments": 500, "compactness": 9.0},
}
LOGICAL_SHAPE = (240, 150, 3)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_full(full: np.ndarray) -> None:
    if full.shape != FULL_SHAPE or full.dtype != np.uint8:
        raise ValueError("BLOCKED_B1R_P2_ORIGINAL_RGB_DIMENSIONS")


def slic_labels(guide: np.ndarray, name: str) -> np.ndarray:
    validate_full(guide)
    if name not in VARIANTS:
        raise ValueError("BLOCKED_B1R_P2_VARIANT_NOT_PREREGISTERED")
    p = VARIANTS[name]
    labels = segmentation.slic(
        guide.astype(np.float64) / 255.0,
        n_segments=p["n_segments"],
        compactness=p["compactness"],
        sigma=0,
        convert2lab=True,
        enforce_connectivity=True,
        start_label=1,
        channel_axis=-1,
        slic_zero=False,
    ).astype(np.int32)
    if labels.shape != FULL_SHAPE[:2] or labels.min() != 1:
        raise ValueError("BLOCKED_B1R_P2_INVALID_LABELS")
    unique = np.unique(labels)
    if not np.array_equal(unique, np.arange(1, len(unique) + 1)):
        raise ValueError("BLOCKED_B1R_P2_NONCONTIGUOUS_LABEL_IDS")
    # SLIC connectivity is an explicit pre-registered contract, not an assumption.
    for label_id in unique:
        if measure.label(labels == label_id, connectivity=1).max() != 1:
            raise ValueError("BLOCKED_B1R_P2_DISCONNECTED_LABEL")
    return labels


def source_region_medoids(original: np.ndarray, labels: np.ndarray):
    """Actual in-region original RGB medoid, stable first-row-major tie."""
    validate_full(original)
    if labels.shape != FULL_SHAPE[:2] or labels.dtype.kind not in "iu":
        raise ValueError("BLOCKED_B1R_P2_MEDOID_LABEL_SHAPE")
    ids = np.unique(labels)
    if len(ids) == 0 or ids[0] != 1 or not np.array_equal(
        ids, np.arange(1, len(ids) + 1)
    ):
        raise ValueError("BLOCKED_B1R_P2_MEDOID_LABEL_IDS")
    lab = color.rgb2lab(original.astype(np.float64) / 255.0).reshape(-1, 3)
    source_flat = original.reshape(-1, 3)
    flat_labels = labels.reshape(-1)
    result = np.empty_like(source_flat)
    ledger = []
    for label_id in ids:
        locations = np.flatnonzero(flat_labels == label_id)
        if not locations.size:
            raise ValueError("BLOCKED_B1R_P2_EMPTY_REGION")
        source_lab = lab[locations]
        median_lab = np.median(source_lab, axis=0)
        dist2 = np.sum((source_lab - median_lab) ** 2, axis=1)
        best = int(locations[int(np.argmin(dist2))])
        swatch = source_flat[best].copy()
        result[locations] = swatch
        ledger.append({
            "id": int(label_id), "area_original_pixels": int(locations.size),
            "source_pixel_xy": [int(best % FULL_SHAPE[1]),
                                int(best // FULL_SHAPE[1])],
            "RGB_original": [int(v) for v in swatch],
        })
    full_map = result.reshape(FULL_SHAPE)
    for item in ledger:
        x, y = item["source_pixel_xy"]
        if (labels[y, x] != item["id"] or
                list(original[y, x]) != item["RGB_original"]):
            raise AssertionError("BLOCKED_B1R_P2_MEDOID_NOT_IN_ORIGINAL_REGION")
    return full_map, ledger


def joint_outline(original: np.ndarray, labels: np.ndarray, original_features: dict):
    """Only source edges + THIS variant's regions; no historical contour input."""
    validate_full(original)
    if labels.shape != FULL_SHAPE[:2]:
        raise ValueError("BLOCKED_B1R_P2_OUTLINE_LABEL_DIMENSIONS")
    f = original_features
    if any(f[k].shape != FULL_SHAPE[:2] for k in
           ("source_edges", "delta4", "priority")):
        raise ValueError("BLOCKED_B1R_P2_ORIGINAL_FEATURE_DIMENSIONS")
    boundary = segmentation.find_boundaries(
        labels, connectivity=1, mode="inner")
    original_support = f["source_edges"] | (f["delta4"] >= 12.0)
    # High gradients select only plausible boundary portions; 1 original px.
    candidate_boundary = boundary & ndimage.binary_dilation(
        original_support, iterations=1)
    roi_detail = f["priority"] & (
        (f["delta4"] >= 6.0) | f["source_edges"])
    candidate = morphology.thin(candidate_boundary | roi_detail)
    cc = measure.label(candidate, connectivity=2)
    areas = np.bincount(cc.ravel())
    priority_cc = np.bincount(cc[roi_detail].ravel(), minlength=len(areas)) > 0
    keep = (areas >= 3) | priority_cc
    keep[0] = False
    outline = candidate & keep[cc]
    if not outline.any():
        raise ValueError("BLOCKED_B1R_P2_NEW_CONTOUR_EMPTY")
    # All non-priority pixels stem from the new joint region boundary.
    other = outline & ~roi_detail
    near_boundary = ndimage.binary_dilation(boundary, iterations=1)
    if np.any(other & ~near_boundary):
        # This can happen at the ends of thin ROI details, which remain
        # inside a preregistered ROI rather than outside source region lines.
        if np.any(other & ~f["priority"] & ~near_boundary):
            raise ValueError("BLOCKED_B1R_P2_OUTLINE_NOT_LINKED_TO_REGION")
    return outline, boundary, roi_detail


def logical_region_map(full_map: np.ndarray) -> np.ndarray:
    validate_full(full_map)
    return np.asarray(Image.fromarray(full_map).resize(
        LOGICAL_WH, Image.Resampling.NEAREST), dtype=np.uint8).copy()


def delta_metrics(source: np.ndarray, result: np.ndarray):
    if source.shape != LOGICAL_SHAPE or result.shape != LOGICAL_SHAPE:
        raise ValueError("BLOCKED_B1R_P2_METRIC_DIMENSIONS")
    source_lab = color.rgb2lab(source / 255.0)
    result_lab = color.rgb2lab(result / 255.0)
    de = color.deltaE_ciede2000(source_lab, result_lab)
    values = {
        "mean_deltaE00": float(np.mean(de)),
        "p95_deltaE00": float(np.percentile(de, 95)),
    }
    for name, (x0, y0, x1, y1) in ROIS_FULL.items():
        ix0, iy0, ix1, iy1 = (round(x0 * .75), round(y0 * .75),
                              round(x1 * .75), round(y1 * .75))
        values[name + "_mean_deltaE00"] = float(de[iy0:iy1, ix0:ix1].mean())
    return values, source_lab, result_lab


def fixed_original_edge_recall(original: np.ndarray, composite: np.ndarray):
    base_sobel = filters.sobel(color.rgb2gray(original / 255.0))
    after_sobel = filters.sobel(color.rgb2gray(composite / 255.0))
    positive = base_sobel[base_sobel > 0]
    if not positive.size:
        raise ValueError("BLOCKED_B1R_P2_NO_SOURCE_EDGES")
    threshold = float(np.percentile(positive, 90))
    original_edges = base_sobel >= threshold
    near_response = ndimage.maximum_filter(after_sobel, size=3)
    return float(np.count_nonzero(
        original_edges & (near_response >= .5 * threshold)) /
        np.count_nonzero(original_edges))


def evaluate(original: np.ndarray, region_map: np.ndarray, composite: np.ndarray,
             labels: np.ndarray, ledger: list, outline: np.ndarray,
             boundary: np.ndarray, roi_detail: np.ndarray):
    source_stats, source_lab, map_lab = delta_metrics(original, region_map)
    composite_stats, _, _ = delta_metrics(original, composite)
    source_chroma = np.linalg.norm(source_lab[..., 1:3], axis=2)
    map_chroma = np.linalg.norm(map_lab[..., 1:3], axis=2)
    label_count = len(ledger)
    logical_unique = int(np.unique(region_map.reshape(-1, 3), axis=0).shape[0])
    full_region_color_unique = len({tuple(x["RGB_original"]) for x in ledger})
    linked = bool(not np.any(outline & ~roi_detail &
                             ~ndimage.binary_dilation(boundary, iterations=1) &
                             ~roi_detail))
    # ROI-detail contributions are source-driven, not required to be a boundary.
    stats = {
        "source_RGB_no_outline": source_stats,
        "composite_with_own_outline": composite_stats,
        "original_logical_RGB_unique": int(np.unique(
            original.reshape(-1, 3), axis=0).shape[0]),
        "labels_full": label_count,
        "source_medoid_full_RGB_unique": full_region_color_unique,
        "logical_RGB_unique": logical_unique,
        "logical_chroma_excess_over_original_plus12_pixels":
            int(np.count_nonzero(map_chroma > source_chroma + 12.0)),
        "fixed_original_sobel90_recall_composite_1px":
            fixed_original_edge_recall(original, composite),
        "new_joint_outline_full_pixels": int(np.count_nonzero(outline)),
        "new_joint_region_boundary_full_pixels": int(np.count_nonzero(boundary)),
        "original_roi_detail_full_pixels": int(np.count_nonzero(roi_detail)),
        "new_outline_linked_to_own_region_boundary_outside_ROI_detail": linked,
    }
    gates = {
        "region_medoid_exists_in_original_own_region": True,
        "source_unique_reduction": logical_unique <
                                    stats["original_logical_RGB_unique"],
        "source_map_unique_not_above_region_count": logical_unique <= label_count,
        "source_mean_deltaE00": source_stats["mean_deltaE00"] <= 6.0,
        "source_p95_deltaE00": source_stats["p95_deltaE00"] <= 23.0,
        "female_face_source_deltaE00":
            source_stats["female_face_eyes_mean_deltaE00"] <= 8.0,
        "male_face_source_deltaE00":
            source_stats["male_face_eyes_mean_deltaE00"] <= 8.0,
        "hands_source_deltaE00":
            source_stats["hands_mean_deltaE00"] <= 9.0,
        "chroma_excess":
            stats["logical_chroma_excess_over_original_plus12_pixels"] <= 1800,
        "fixed_original_strong_edges":
            stats["fixed_original_sobel90_recall_composite_1px"] >= .60,
        "nonempty_new_outline": stats["new_joint_outline_full_pixels"] > 0,
        "new_outline_linked_to_own_regions": linked,
    }
    stats["gates"] = gates
    stats["status"] = ("SOURCE_SCREEN_PASS_VISUAL_PENDING" if all(gates.values())
                       else "SOURCE_GATE_FAIL")
    return stats


def draw_comparison(raw: np.ndarray, results: dict, previews: dict, path: Path):
    entries = [("ORIGINAL_RGB", raw, Image.fromarray(raw))] + [
        (name, results[name], previews[name]) for name in VARIANTS
    ]
    canvas = Image.new("RGB", (3 * 450, 2 * 755), "white")
    painter = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 21)
    except OSError:
        font = ImageFont.load_default()
    for col, (name, rgb, contour_img) in enumerate(entries):
        for row, img in enumerate((Image.fromarray(rgb), contour_img)):
            left, top = col * 450, row * 755
            canvas.paste(img.resize((450, 720), Image.Resampling.NEAREST),
                         (left, top + 35))
            painter.text((left + 6, top + 6),
                         name + (" / REGION RGB" if row == 0 else " / OWN OUTLINE"),
                         font=font, fill=(0, 0, 0))
    canvas.save(path)


def run(source_path: Path, output: Path):
    if output.exists():
        raise ValueError("BLOCKED_B1R_P2_OVERWRITE")
    source = check_source(source_path)
    original_features = full_features(source)
    original_logical = logical_rgb(source)
    output.mkdir(parents=True)
    Image.fromarray(source).save(output / "ORIGINAL_FULL_RGB.png")
    Image.fromarray(original_logical).save(output / "ORIGINAL_LOGICAL_RGB.png")
    Image.fromarray((original_features["protected"] * 255).astype(np.uint8)).save(
        output / "ORIGINAL_PROTECTED_FULL.png")
    Image.fromarray((original_features["source_edges"] * 255).astype(np.uint8)).save(
        output / "ORIGINAL_STRONG_EDGES_FULL.png")
    results, logicals, previews = {}, {}, {}
    for name, p in VARIANTS.items():
        filtered = filter_original(source, p["filter"], original_features["protected"])
        labels = slic_labels(filtered, name)
        full_map, ledger = source_region_medoids(source, labels)
        logical_map = logical_region_map(full_map)
        outline, boundary, roi_detail = joint_outline(
            source, labels, original_features)
        outline_rgba = original_outline_rgba(source, outline)
        composite = compose_preview(logical_map, outline_rgba)
        composite_arr = np.asarray(composite, dtype=np.uint8)
        results[name] = evaluate(original_logical, logical_map,
                                 composite_arr, labels, ledger,
                                 outline, boundary, roi_detail)
        logicals[name] = logical_map
        previews[name] = composite
        Image.fromarray(filtered).save(output / (name + "_GUIDE_FULL_RGB.png"))
        Image.fromarray(full_map).save(output / (name + "_REGIONS_FULL_RGB.png"))
        Image.fromarray(logical_map).save(output / (name + "_REGIONS_LOGICAL_RGB.png"))
        Image.fromarray((outline * 255).astype(np.uint8)).save(
            output / (name + "_NEW_OUTLINE_MASK_FULL.png"))
        Image.fromarray(outline_rgba).save(output / (name + "_NEW_OUTLINE_RGBA_FULL.png"))
        composite.save(output / (name + "_REGIONS_PLUS_OWN_OUTLINE.png"))
        np.save(output / (name + "_LABELS_FULL.npy"), labels, allow_pickle=False)
        (output / (name + "_MEDOID_LEDGER.json")).write_text(
            json.dumps(ledger, indent=2, ensure_ascii=False) + "\n",
            encoding="utf8")
    draw_comparison(original_logical, logicals, previews,
                    output / "B1R_P2_RGB_AND_JOINT_OUTLINE_COMPARISON.png")
    file_sha = {
        p.name: digest(p.read_bytes()) for p in sorted(output.iterdir())
        if p.is_file()
    }
    report = {
        "experiment": EXPERIMENT,
        "candidate_source": "original_RGB",
        "source_sha256": SOURCE_SHA256,
        "github_sha": os.getenv("GITHUB_SHA"),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "legacy_G32_used_as_candidate": False,
        "legacy_V44_used_as_candidate": False,
        "legacy_M1_mask_used_as_candidate": False,
        "historical_comparison_input_count": 0,
        "original_only_B1R_P1_math_reused": True,
        "original_shape": list(FULL_SHAPE),
        "logical_shape": list(LOGICAL_SHAPE),
        "original_protected_full_pixels":
            int(np.count_nonzero(original_features["protected"])),
        "fixed_original_full_sobel90": original_features["threshold90"],
        "candidate_config_preregistered": VARIANTS,
        "priority_original_full_RGB_rectangles": ROIS_FULL,
        "metrics": results,
        "file_sha256": file_sha,
        "human_visual": "PENDING",
        "outline_type": "NEW_ORIGINAL_RGB_JOINT_REGIONS_PREVIEW_NOT_NATIVE",
        "game32_projection": "NOT_RUN",
        "native_round_brush_E3": "NOT_RUN",
        "live_E4": "NOT_RUN",
        "independent_E5": "NOT_RUN",
        "exact_game_CHALK": None,
        "production_accepted": False,
        "versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "opencv": cv2.__version__,
            "Pillow": Image.__version__,
            "scipy": scipy.__version__,
            "skimage": skimage.__version__,
        },
    }
    (output / "report.json").write_text(json.dumps(
        report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf8")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    report = run(args.source, args.output)
    for name, value in report["metrics"].items():
        print(name, value["status"],
              "source_DE00", round(value["source_RGB_no_outline"]["mean_deltaE00"], 4),
              "edge_recall", round(
                  value["fixed_original_sobel90_recall_composite_1px"], 4),
              "source_colors", value["logical_RGB_unique"],
              "regions", value["labels_full"])
    print("GAME32_NATIVE_E4_E5_CHALK_NOT_RUN")

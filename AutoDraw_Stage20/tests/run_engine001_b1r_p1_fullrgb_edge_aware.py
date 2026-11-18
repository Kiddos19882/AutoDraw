#!/usr/bin/env python3
"""B1-R-P1: new original-only RGB visual candidate, not game32 or native Egret paint."""
from __future__ import annotations
import argparse
import hashlib
import io
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
from skimage import color, filters, measure, morphology

EXPERIMENT = "ENGINE001_B1R_P1_FULLRGB_EDGE_AWARE_A"
SOURCE_SHA256 = "07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
FULL_SHAPE = (320, 200, 3)
LOGICAL_WH = (150, 240)
ROIS_FULL = {
    "female_face_eyes": (35, 45, 113, 133),
    "male_face_eyes": (96, 19, 164, 123),
    "hands": (41, 167, 153, 220),
    "blouse": (32, 123, 140, 196),
}
METHODS = {
    "A_SOFT": {"d": 5, "sigmaColor": 18, "sigmaSpace": 2.0},
    "A_MID": {"d": 7, "sigmaColor": 28, "sigmaSpace": 3.0},
}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def check_source(source_path):
    data = source_path.read_bytes()
    if digest(data) != SOURCE_SHA256:
        raise ValueError("BLOCKED_B1R_P1_ORIGINAL_SHA")
    full = np.asarray(Image.open(io.BytesIO(data)).convert("RGB"), dtype=np.uint8)
    if full.shape != FULL_SHAPE:
        raise ValueError("BLOCKED_B1R_P1_SOURCE_DIMENSIONS")
    return full

def logical_rgb(full):
    if full.shape != FULL_SHAPE or full.dtype != np.uint8:
        raise ValueError("BLOCKED_B1R_P1_RESIZE_SOURCE")
    return np.asarray(
        Image.fromarray(full).resize(LOGICAL_WH, Image.Resampling.LANCZOS),
        dtype=np.uint8,
    ).copy()

def full_features(full):
    """Only ORIGINAL full RGB; no old external masks, RGB palette or contour inputs."""
    if full.shape != FULL_SHAPE or full.dtype != np.uint8:
        raise ValueError("BLOCKED_B1R_P1_FEATURE_SOURCE")
    original_lab = color.rgb2lab(full.astype(np.float64) / 255.0)
    delta = np.zeros(FULL_SHAPE[:2], dtype=np.float32)
    for shift in (0, 1):
        if shift == 0:
            d = color.deltaE_ciede2000(original_lab[:-1, :, :],
                                      original_lab[1:, :, :]).astype(np.float32)
            delta[:-1, :] = np.maximum(delta[:-1, :], d)
            delta[1:, :] = np.maximum(delta[1:, :], d)
        else:
            d = color.deltaE_ciede2000(original_lab[:, :-1, :],
                                      original_lab[:, 1:, :]).astype(np.float32)
            delta[:, :-1] = np.maximum(delta[:, :-1], d)
            delta[:, 1:] = np.maximum(delta[:, 1:], d)
    sobel = filters.sobel(color.rgb2gray(full.astype(np.float64) / 255.0))
    positive = sobel[sobel > 0]
    if not len(positive):
        raise ValueError("BLOCKED_B1R_P1_NO_ORIGINAL_EDGES")
    th90 = float(np.percentile(positive, 90))
    priority = np.zeros(FULL_SHAPE[:2], dtype=bool)
    for x0, y0, x1, y1 in ROIS_FULL.values():
        priority[y0:y1, x0:x1] = True
    source_edges = sobel >= th90
    high_source_detail = delta >= 12.0
    roi_source_detail = priority & (delta >= 6.0)
    priority_dilated = ndimage.binary_dilation(
        roi_source_detail, structure=ndimage.generate_binary_structure(2, 1)
    ) & priority
    protected = source_edges | high_source_detail | priority_dilated
    if not protected.any():
        raise ValueError("BLOCKED_B1R_P1_PROTECTION_EMPTY")
    # A separate newly calculated, original-only, 8-connected thinned contour.
    candidate = morphology.thin(source_edges & (delta >= 6.0))
    components = measure.label(candidate, connectivity=2)
    counts = np.bincount(components.ravel())
    keep = (counts >= 3)
    if len(keep):
        keep[0] = False
    outline = candidate & (keep[components] | (priority & (delta >= 12.0)))
    if not outline.any():
        raise ValueError("BLOCKED_B1R_P1_CONTOUR_EMPTY")
    return {
        "sobel": sobel,
        "threshold90": th90,
        "delta4": delta,
        "priority": priority,
        "protected": protected.astype(bool),
        "source_edges": source_edges.astype(bool),
        "new_outline": outline.astype(bool),
    }

def logical_protection(full_protection):
    if full_protection.shape != FULL_SHAPE[:2]:
        raise ValueError("BLOCKED_B1R_P1_FULL_PROTECTION_SHAPE")
    small = Image.fromarray((full_protection.astype(np.uint8) * 255), mode="L")
    return np.asarray(small.resize(LOGICAL_WH, Image.Resampling.BOX)) > 0

def filter_original(full, method, protected_full):
    if method not in METHODS or full.shape != FULL_SHAPE or (
        protected_full.shape != FULL_SHAPE[:2]
    ):
        raise ValueError("BLOCKED_B1R_P1_FILTER_INPUT_OR_METHOD")
    p = METHODS[method]
    result = cv2.bilateralFilter(
        full, p["d"], p["sigmaColor"], p["sigmaSpace"]
    ).copy()
    result[protected_full] = full[protected_full]
    if not np.array_equal(result[protected_full], full[protected_full]):
        raise AssertionError("BLOCKED_B1R_P1_FULL_PROTECTION_DRIFT")
    return result

def output_rgb(full, method, features, raw_logical=None, protected_logical=None):
    if raw_logical is None:
        raw_logical = logical_rgb(full)
    if protected_logical is None:
        protected_logical = logical_protection(features["protected"])
    result_full = filter_original(full, method, features["protected"])
    logical = logical_rgb(result_full)
    logical[protected_logical] = raw_logical[protected_logical]
    if not np.array_equal(logical[protected_logical], raw_logical[protected_logical]):
        raise AssertionError("BLOCKED_B1R_P1_LOGICAL_PROTECTION_DRIFT")
    return result_full, logical

def original_outline_rgba(full, outline):
    """Dark RGB is selected from original 3x3 neighbors, not invented or recolored."""
    if full.shape != FULL_SHAPE or outline.shape != FULL_SHAPE[:2]:
        raise ValueError("BLOCKED_B1R_P1_NEW_OUTLINE_INPUT")
    luminance = color.rgb2gray(full.astype(np.float64) / 255.0)
    lum_pad = np.pad(luminance, 1, mode="edge")
    rgb_pad = np.pad(full, ((1, 1), (1, 1), (0, 0)), mode="edge")
    scores = np.stack([
        lum_pad[y:y + FULL_SHAPE[0], x:x + FULL_SHAPE[1]]
        for y in range(3) for x in range(3)
    ], axis=-1)
    neighbors = np.stack([
        rgb_pad[y:y + FULL_SHAPE[0], x:x + FULL_SHAPE[1], :]
        for y in range(3) for x in range(3)
    ], axis=-2)
    closest_dark = np.argmin(scores, axis=-1)
    chosen = np.take_along_axis(
        neighbors, closest_dark[..., None, None], axis=2
    )[:, :, 0, :]
    rgba = np.zeros((*FULL_SHAPE[:2], 4), dtype=np.uint8)
    rgba[outline, :3] = chosen[outline]
    rgba[outline, 3] = 185
    # Exact original source-pixel provenance for every preview contour RGB pixel.
    if not np.array_equal(rgba[outline, :3], chosen[outline]):
        raise AssertionError("BLOCKED_B1R_P1_OUTLINE_PALETTE_DRIFT")
    return rgba

def compose_preview(logical, outline_full):
    if logical.shape != (240, 150, 3) or outline_full.shape != (*FULL_SHAPE[:2], 4):
        raise ValueError("BLOCKED_B1R_P1_PREVIEW_SHAPE")
    outline_small = Image.fromarray(outline_full).resize(
        LOGICAL_WH, Image.Resampling.NEAREST
    ).convert("RGBA")
    rgb = Image.fromarray(logical).convert("RGBA")
    return Image.alpha_composite(rgb, outline_small).convert("RGB")

def roughness(rgb, flat):
    """Original-masked RGB contrast across neighboring logical pixels."""
    a = rgb.astype(np.float64)
    pair_h = flat[:, :-1] & flat[:, 1:]
    pair_v = flat[:-1, :] & flat[1:, :]
    values = []
    if np.any(pair_h):
        values.append(np.abs(a[:, 1:] - a[:, :-1]).mean(axis=2)[pair_h])
    if np.any(pair_v):
        values.append(np.abs(a[1:, :] - a[:-1, :]).mean(axis=2)[pair_v])
    if not values:
        raise ValueError("BLOCKED_B1R_P1_FLAT_MASK_EMPTY")
    return float(np.concatenate(values).mean())

def evaluate(original_full, original_logical, result_full, result_logical,
             full_protected, logical_protected):
    lab0 = color.rgb2lab(original_logical / 255.0)
    lab1 = color.rgb2lab(result_logical / 255.0)
    de = color.deltaE_ciede2000(lab0, lab1)
    base_sobel = filters.sobel(color.rgb2gray(original_logical / 255.0))
    candidate_sobel = filters.sobel(color.rgb2gray(result_logical / 255.0))
    positive = base_sobel[base_sobel > 0]
    th = float(np.percentile(positive, 90))
    edges = base_sobel >= th
    flat = base_sobel <= float(np.median(positive))
    before = roughness(original_logical, flat)
    after = roughness(result_logical, flat)
    labc0 = np.hypot(lab0[..., 1], lab0[..., 2])
    labc1 = np.hypot(lab1[..., 1], lab1[..., 2])
    stats = {
        "full_original_protected_equal": bool(
            np.array_equal(result_full[full_protected], original_full[full_protected])),
        "logical_original_protected_equal": bool(
            np.array_equal(result_logical[logical_protected],
                           original_logical[logical_protected])),
        "mean_deltaE00": float(de.mean()),
        "p95_deltaE00": float(np.percentile(de, 95)),
        "fixed_logical_original_sobel90_overlap": float(
            np.count_nonzero(edges & (candidate_sobel >= th)) /
            max(1, np.count_nonzero(edges))),
        "excess_chroma_over_original_plus12_pixels": int(
            np.count_nonzero(labc1 > labc0 + 12.0)),
        "logical_unique_RGB": int(np.unique(result_logical.reshape(-1, 3), axis=0).shape[0]),
        "logical_changed_pixels": int(
            np.count_nonzero(np.any(result_logical != original_logical, axis=2))),
        "flat_rgb_roughness_before": before,
        "flat_rgb_roughness_after": after,
        "flat_rgb_roughness_reduction_fraction": float(
            (before - after) / max(1e-12, before)),
    }
    for name, (x0, y0, x1, y1) in ROIS_FULL.items():
        ix0, iy0 = round(x0 * .75), round(y0 * .75)
        ix1, iy1 = round(x1 * .75), round(y1 * .75)
        stats[name + "_mean_deltaE00"] = float(de[iy0:iy1, ix0:ix1].mean())
    gates = {
        "full_protected_exact": stats["full_original_protected_equal"],
        "logical_protected_exact": stats["logical_original_protected_equal"],
        "mean_deltaE00": stats["mean_deltaE00"] <= 2.0,
        "p95_deltaE00": stats["p95_deltaE00"] <= 7.0,
        "fixed_original_edges": stats["fixed_logical_original_sobel90_overlap"] >= .90,
        "female_face": stats["female_face_eyes_mean_deltaE00"] <= 2.0,
        "male_face": stats["male_face_eyes_mean_deltaE00"] <= 2.0,
        "hands": stats["hands_mean_deltaE00"] <= 2.0,
        "chroma_excess": stats["excess_chroma_over_original_plus12_pixels"] <= 60,
        "roughness_reduction": stats["flat_rgb_roughness_reduction_fraction"] >= .01,
    }
    stats["gates"] = gates
    stats["status"] = ("SOURCE_SCREEN_PASS_VISUAL_PENDING" if all(gates.values())
                       else "SOURCE_GATE_FAIL")
    return stats

def comparison(original, variants, contours, path):
    entries = [("ORIGINAL_RGB", original)] + list(variants.items())
    if len(entries) != 3:
        raise ValueError("BLOCKED_B1R_P1_COMPARISON_VARIANTS")
    canvas = Image.new("RGB", (3 * 450, 2 * 755), "white")
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 21)
    except OSError:
        font = ImageFont.load_default()
    for col, (name, rgb) in enumerate(entries):
        if rgb.shape != (240, 150, 3):
            raise ValueError("BLOCKED_B1R_P1_PANEL_DIMENSION")
        for row, sample in enumerate((Image.fromarray(rgb), contours[name])):
            image = sample.resize((450, 720), Image.Resampling.NEAREST)
            left, top = col * 450, row * 755
            canvas.paste(image, (left, top + 35))
            draw.text((left + 6, top + 6),
                      name + (" / RGB" if row == 0 else " / NEW SOURCE OUTLINE"),
                      fill=(0, 0, 0), font=font)
    canvas.save(path)

def run(source_path, output):
    if output.exists():
        raise ValueError("BLOCKED_B1R_P1_OVERWRITE")
    full = check_source(source_path)
    features = full_features(full)
    raw = logical_rgb(full)
    mask_logical = logical_protection(features["protected"])
    original_outline = original_outline_rgba(full, features["new_outline"])
    output.mkdir(parents=True)
    Image.fromarray(full).save(output / "ORIGINAL_FULL_RGB.png")
    Image.fromarray(raw).save(output / "ORIGINAL_LOGICAL_RGB.png")
    Image.fromarray((features["protected"] * 255).astype(np.uint8)).save(
        output / "ORIGINAL_PROTECTED_FULL.png")
    Image.fromarray((mask_logical * 255).astype(np.uint8)).save(
        output / "ORIGINAL_PROTECTED_LOGICAL.png")
    Image.fromarray((features["source_edges"] * 255).astype(np.uint8)).save(
        output / "ORIGINAL_STRONG_EDGES_FULL.png")
    Image.fromarray(original_outline).save(output / "NEW_ORIGINAL_DERIVED_OUTLINE_RGBA.png")
    source_outline = compose_preview(raw, original_outline)
    source_outline.save(output / "ORIGINAL_PLUS_NEW_OUTLINE_PREVIEW.png")
    results, logicals = {}, {}
    contours = {"ORIGINAL_RGB": source_outline}
    for name in METHODS:
        full_filtered, logical = output_rgb(full, name, features, raw, mask_logical)
        results[name] = evaluate(full, raw, full_filtered, logical,
                                 features["protected"], mask_logical)
        logicals[name] = logical
        Image.fromarray(full_filtered).save(output / (name + "_FULL_RGB.png"))
        Image.fromarray(logical).save(output / (name + "_LOGICAL_RGB.png"))
        contours[name] = compose_preview(logical, original_outline)
        contours[name].save(output / (name + "_PLUS_NEW_OUTLINE_PREVIEW.png"))
    comparison(raw, logicals, contours, output / "B1R_P1_RGB_NEW_OUTLINE_COMPARISON.png")
    sha_files = {
        p.name: digest(p.read_bytes())
        for p in sorted(output.iterdir()) if p.is_file()
    }
    report = {
        "experiment": EXPERIMENT,
        "candidate_source": "original_RGB",
        "legacy_G32_used_as_candidate": False,
        "legacy_V44_used_as_candidate": False,
        "legacy_M1_mask_used_as_candidate": False,
        "historical_comparison_input_count": 0,
        "source_sha256": SOURCE_SHA256,
        "github_sha": os.getenv("GITHUB_SHA"),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "full_original_shape": list(FULL_SHAPE),
        "logical_shape": [240, 150, 3],
        "protected_full_pixels": int(features["protected"].sum()),
        "protected_logical_pixels": int(mask_logical.sum()),
        "new_original_outline_pixels": int(features["new_outline"].sum()),
        "original_full_sobel90": features["threshold90"],
        "priority_original_full_RGB_rectangles": ROIS_FULL,
        "source_methods": METHODS,
        "metrics": results,
        "file_sha256": sha_files,
        "human_visual": "PENDING",
        "new_outline_quality": "SOURCE_ONLY_PREVIEW_NOT_NATIVE",
        "game32_projection": "NOT_RUN",
        "game_round_brush": "NOT_RUN",
        "live_E4": "NOT_RUN",
        "independent_E5": "NOT_RUN",
        "exact_game_CHALK": None,
        "production_accepted": False,
        "versions": {
            "python": platform.python_version(),
            "opencv": cv2.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "skimage": skimage.__version__,
            "Pillow": Image.__version__,
        },
    }
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf8",
    )
    return report

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    report = run(args.source, args.output)
    for name, result in report["metrics"].items():
        print(name, result["status"],
              "DE00", round(result["mean_deltaE00"], 5),
              "edge", round(result["fixed_logical_original_sobel90_overlap"], 5),
              "flat_reduction", round(result["flat_rgb_roughness_reduction_fraction"], 5),
              "chroma_excess", result["excess_chroma_over_original_plus12_pixels"])

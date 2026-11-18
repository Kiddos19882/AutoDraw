#!/usr/bin/env python3
"""ENGINE001 B1-R-P2B: independent original-only RGB residual ink evidence.

Region medoids + source-exact detail residual, NOT game32/native/CHALK.
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
from skimage import color

from run_engine001_b1r_p1_fullrgb_edge_aware import (
    FULL_SHAPE, LOGICAL_WH, ROIS_FULL, SOURCE_SHA256,
    check_source, filter_original, full_features, logical_rgb,
)
from run_engine001_b1r_p2_joint_region_outline import (
    delta_metrics, digest, fixed_original_edge_recall,
    logical_region_map, slic_labels, source_region_medoids,
)

EXPERIMENT = "ENGINE001_B1R_P2B_RGB_RESIDUAL_INK_V1"
VARIANTS = {
    "K_RESTRAINED": {
        "outside_deltaE00": 11.0, "outside_dark_L": 7.0,
        "inside_deltaE00": 6.0, "inside_dark_L": 3.0,
    },
    "K_DETAIL": {
        "outside_deltaE00": 8.0, "outside_dark_L": 5.0,
        "inside_deltaE00": 4.5, "inside_dark_L": 2.5,
    },
}


def ink_residual(original: np.ndarray, full_map: np.ndarray,
                 original_features: dict, variant: str):
    if (original.shape != FULL_SHAPE or original.dtype != np.uint8 or
            full_map.shape != FULL_SHAPE or full_map.dtype != np.uint8):
        raise ValueError("BLOCKED_B1R_P2B_RGB_INPUT")
    if variant not in VARIANTS:
        raise ValueError("BLOCKED_B1R_P2B_UNREGISTERED_VARIANT")
    if any(original_features[k].shape != FULL_SHAPE[:2] for k in
           ("delta4", "priority", "source_edges")):
        raise ValueError("BLOCKED_B1R_P2B_ORIGINAL_FEATURE_SHAPE")
    p = VARIANTS[variant]
    source_lab = color.rgb2lab(original.astype(np.float64) / 255.0)
    medoid_lab = color.rgb2lab(full_map.astype(np.float64) / 255.0)
    de = color.deltaE_ciede2000(source_lab, medoid_lab)
    dark = medoid_lab[..., 0] - source_lab[..., 0]
    priority = original_features["priority"]
    detail_near = ndimage.binary_dilation(
        original_features["delta4"] >= 4.0, iterations=1)
    de_threshold = np.where(priority, p["inside_deltaE00"],
                            p["outside_deltaE00"])
    dark_threshold = np.where(priority, p["inside_dark_L"],
                              p["outside_dark_L"])
    mask = detail_near & ((de >= de_threshold) | (dark >= dark_threshold))
    if not np.any(mask):
        raise ValueError("BLOCKED_B1R_P2B_EMPTY_SOURCE_DETAIL")
    rgba = np.zeros((*FULL_SHAPE[:2], 4), dtype=np.uint8)
    rgba[mask, :3] = original[mask]
    rgba[mask, 3] = 255
    merged = full_map.copy()
    merged[mask] = original[mask]
    if (not np.array_equal(rgba[mask, :3], original[mask]) or
            not np.array_equal(merged[mask], original[mask]) or
            np.any(rgba[~mask, 3])):
        raise AssertionError("BLOCKED_B1R_P2B_SOURCE_EXACT_INK")
    return mask, rgba, merged, {
        "source_detail_near_full": int(np.count_nonzero(detail_near)),
        "source_residual_full_pixels": int(np.count_nonzero(mask)),
        "source_residual_original_ratio": float(mask.mean()),
        "source_residual_full_priority_pixels": int(np.count_nonzero(mask & priority)),
        "source_original_delta4_ge4_px": int(np.count_nonzero(
            original_features["delta4"] >= 4.0)),
        "source_ink_selected_only_near_original_contrast":
            bool(not np.any(mask & ~detail_near)),
        "full_ink_RGB_exact_original":
            bool(np.array_equal(merged[mask], original[mask])),
    }


def logical_composite(full: np.ndarray) -> np.ndarray:
    if full.shape != FULL_SHAPE or full.dtype != np.uint8:
        raise ValueError("BLOCKED_B1R_P2B_LOGICAL_INPUT")
    return np.asarray(
        Image.fromarray(full).resize(LOGICAL_WH, Image.Resampling.LANCZOS),
        dtype=np.uint8).copy()


def candidate_metrics(source_logical: np.ndarray, flat_logical: np.ndarray,
                      composite_logical: np.ndarray,
                      ink_summary: dict, label_count: int):
    flat, _, _ = delta_metrics(source_logical, flat_logical)
    composite, source_lab, composite_lab = delta_metrics(
        source_logical, composite_logical)
    flat_unique = int(np.unique(flat_logical.reshape(-1, 3), axis=0).shape[0])
    composite_unique = int(np.unique(
        composite_logical.reshape(-1, 3), axis=0).shape[0])
    chroma0 = np.linalg.norm(source_lab[..., 1:3], axis=2)
    chroma1 = np.linalg.norm(composite_lab[..., 1:3], axis=2)
    edge_recall = fixed_original_edge_recall(
        source_logical, composite_logical)
    stats = {
        "flat_original_source_RGB": flat,
        "residual_own_source_composite": composite,
        "flat_labels": label_count,
        "flat_logical_unique_RGB": flat_unique,
        "composite_logical_unique_RGB_NOT_game32": composite_unique,
        "logical_chroma_excess_over_source_plus12":
            int(np.count_nonzero(chroma1 > chroma0 + 12.0)),
        "fixed_original_sobel90_recall_composite_1px": edge_recall,
        "full_source_ink": ink_summary,
    }
    gates = {
        "source_exact_residual_ink": ink_summary["full_ink_RGB_exact_original"],
        "source_detail_original_only":
            ink_summary["source_ink_selected_only_near_original_contrast"],
        "nonempty_and_bounded_source_detail":
            0 < ink_summary["source_residual_original_ratio"] <= .30,
        "flat_medoid_unique_count": flat_unique <= label_count <= 900,
        "composite_mean_deltaE00": composite["mean_deltaE00"] <= 4.2,
        "composite_p95_deltaE00": composite["p95_deltaE00"] <= 20.0,
        "female_face_composite":
            composite["female_face_eyes_mean_deltaE00"] <= 7.0,
        "male_face_composite":
            composite["male_face_eyes_mean_deltaE00"] <= 7.0,
        "hands_composite": composite["hands_mean_deltaE00"] <= 7.0,
        "female_face_improves_20percent":
            composite["female_face_eyes_mean_deltaE00"] <=
                .8 * flat["female_face_eyes_mean_deltaE00"],
        "male_face_improves_20percent":
            composite["male_face_eyes_mean_deltaE00"] <=
                .8 * flat["male_face_eyes_mean_deltaE00"],
        "strong_original_source_edges": edge_recall >= .90,
        "chroma_excess": stats["logical_chroma_excess_over_source_plus12"] <= 1400,
    }
    stats["gates"] = gates
    stats["status"] = ("SOURCE_SCREEN_PASS_VISUAL_PENDING" if all(gates.values())
                       else "SOURCE_GATE_FAIL")
    return stats


def save_roi_comparison(original: np.ndarray, flat: np.ndarray,
                        composite: np.ndarray, output: Path, prefix: str):
    for key, (x0, y0, x1, y1) in ROIS_FULL.items():
        sx0, sy0, sx1, sy1 = (
            round(x0 * .75), round(y0 * .75),
            round(x1 * .75), round(y1 * .75))
        cuts = [x[sy0:sy1, sx0:sx1] for x in
                (original, flat, composite)]
        h, w = cuts[0].shape[:2]
        canvas = Image.new("RGB", (w * 12, h * 4), (255, 255, 255))
        for i, cut in enumerate(cuts):
            canvas.paste(Image.fromarray(cut).resize(
                (w * 4, h * 4), Image.Resampling.NEAREST), (i * w * 4, 0))
        canvas.save(output / (prefix + "_ROI_" + key + ".png"))


def panel(original: np.ndarray, flat: np.ndarray, variants: dict, output: Path):
    entries = [("ORIGINAL", original), ("FLAT_MEDOID", flat)] + [
        (key, variants[key]) for key in VARIANTS
    ]
    canvas = Image.new("RGB", (4 * 450, 755), "white")
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 21)
    except OSError:
        font = ImageFont.load_default()
    for col, (name, arr) in enumerate(entries):
        canvas.paste(Image.fromarray(arr).resize(
            (450, 720), Image.Resampling.NEAREST), (col * 450, 35))
        draw.text((col * 450 + 6, 6), name, fill=(0, 0, 0), font=font)
    canvas.save(output)


def run(source_path: Path, output: Path):
    if output.exists():
        raise ValueError("BLOCKED_B1R_P2B_OVERWRITE")
    original = check_source(source_path)
    f = full_features(original)
    raw_logical = logical_rgb(original)
    # Compute original-only source base afresh. Never load frozen P2 masks/PNGs.
    guide = filter_original(original, "A_SOFT", f["protected"])
    labels = slic_labels(guide, "J_FINE")
    flat_full, ledger = source_region_medoids(original, labels)
    flat_logical = logical_region_map(flat_full)
    output.mkdir(parents=True)
    Image.fromarray(original).save(output / "ORIGINAL_FULL_RGB.png")
    Image.fromarray(raw_logical).save(output / "ORIGINAL_LOGICAL_RGB.png")
    Image.fromarray(guide).save(output / "ORIGINAL_ONLY_FILTERED_GUIDE_FULL.png")
    Image.fromarray(flat_full).save(output / "FLAT_MEDOID_FULL_RGB.png")
    Image.fromarray(flat_logical).save(output / "FLAT_MEDOID_LOGICAL_RGB.png")
    Image.fromarray((f["delta4"] >= 4).astype(np.uint8) * 255).save(
        output / "ORIGINAL_DETAIL_SEED_FULL.png")
    np.save(output / "ORIGINAL_ONLY_SLIC_LABELS_FULL.npy",
            labels, allow_pickle=False)
    (output / "ORIGINAL_SOURCE_MEDOID_LEDGER.json").write_text(
        json.dumps(ledger, indent=2, ensure_ascii=False) + "\n",
        encoding="utf8")
    stats, logical_results = {}, {}
    for name in VARIANTS:
        mask, rgba, composed, summary = ink_residual(
            original, flat_full, f, name)
        logical = logical_composite(composed)
        stats[name] = candidate_metrics(
            raw_logical, flat_logical, logical, summary, len(ledger))
        logical_results[name] = logical
        Image.fromarray((mask * 255).astype(np.uint8)).save(
            output / (name + "_SOURCE_INK_MASK_FULL.png"))
        Image.fromarray(rgba).save(
            output / (name + "_SOURCE_EXACT_INK_RGBA_FULL.png"))
        Image.fromarray(composed).save(
            output / (name + "_COMPOSITE_FULL_RGB.png"))
        Image.fromarray(logical).save(
            output / (name + "_COMPOSITE_LOGICAL_RGB.png"))
        save_roi_comparison(
            raw_logical, flat_logical, logical, output, name)
    panel(raw_logical, flat_logical, logical_results,
          output / "B1R_P2B_ORIGINAL_FLAT_TWO_RESIDUALS.png")
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
        "frozen_P2V1_artifacts_as_input": False,
        "historical_comparison_input_count": 0,
        "source_original_full_shape": list(FULL_SHAPE),
        "source_logical_shape": [240, 150, 3],
        "regions_original_only_recomputed": True,
        "source_region_count": len(ledger),
        "source_protected_full_original_only":
            int(np.count_nonzero(f["protected"])),
        "fixed_original_sobel90": f["threshold90"],
        "region_baseline": {
            "filter": "A_SOFT", "n_segments": 900, "compactness": 6.0,
            "median_lab_original_swatch": True,
        },
        "variant_parameters": VARIANTS,
        "metrics": stats,
        "file_sha256": file_sha,
        "human_visual": "PENDING",
        "detail_layer_type": "ORIGINAL_RGB_RESIDUAL_PIXEL_PROXY_NOT_NATIVE",
        "game32_projection": "NOT_RUN",
        "native_Egret": "NOT_RUN",
        "live_E4": "NOT_RUN",
        "independent_E5": "NOT_RUN",
        "exact_game_CHALK": None,
        "production_accepted": False,
        "versions": {
            "python": platform.python_version(),
            "opencv": cv2.__version__,
            "Pillow": Image.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "skimage": skimage.__version__,
        },
    }
    (output / "report.json").write_text(json.dumps(
        report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf8")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    report = run(args.source, args.output)
    for key, stats in report["metrics"].items():
        print(key, stats["status"],
              "mean_DE00", round(stats["residual_own_source_composite"]["mean_deltaE00"],5),
              "female_DE00", round(stats["residual_own_source_composite"]["female_face_eyes_mean_deltaE00"],5),
              "male_DE00", round(stats["residual_own_source_composite"]["male_face_eyes_mean_deltaE00"],5),
              "p95", round(stats["residual_own_source_composite"]["p95_deltaE00"],5),
              "ink_percent",round(100*stats["full_source_ink"]["source_residual_original_ratio"],3))
    print("B1R_P2B_GAME32_NATIVE_E4_E5_CHALK_NOT_RUN")

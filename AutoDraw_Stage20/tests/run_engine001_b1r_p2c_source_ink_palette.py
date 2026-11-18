#!/usr/bin/env python3
"""B1-R-P2C: source-ink medoid palette compression, original RGB only.

Research previews are NOT game32, native Egret, or measured CHALK.
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
from scipy.cluster.vq import kmeans2
from skimage import color

from run_engine001_b1r_p1_fullrgb_edge_aware import (
    FULL_SHAPE, LOGICAL_WH, ROIS_FULL, SOURCE_SHA256, check_source,
    filter_original, full_features, logical_rgb,
)
from run_engine001_b1r_p2_joint_region_outline import (
    delta_metrics, digest, fixed_original_edge_recall,
    logical_region_map, slic_labels, source_region_medoids,
)
from run_engine001_b1r_p2b_residual_ink import (
    ink_residual, logical_composite,
)

EXPERIMENT = "ENGINE001_B1R_P2C_SOURCE_INK_PALETTE_V1"
VARIANTS = {"C_096": 96, "C_192": 192}
CLUSTER_SEED = 1729
CLUSTER_ITERATIONS = 16
LOGICAL_SHAPE = (240, 150, 3)


def unique_rgb(rgb: np.ndarray) -> int:
    return int(np.unique(rgb.reshape(-1, 3), axis=0).shape[0])


def compress_source_ink(original: np.ndarray, flat: np.ndarray,
                        ink_mask: np.ndarray, variant: str):
    """Cluster only original-mask pixels, choose actual source-member colors."""
    if variant not in VARIANTS:
        raise ValueError("BLOCKED_B1R_P2C_UNREGISTERED_VARIANT")
    if (original.shape != FULL_SHAPE or original.dtype != np.uint8 or
            flat.shape != FULL_SHAPE or flat.dtype != np.uint8 or
            ink_mask.shape != FULL_SHAPE[:2] or ink_mask.dtype != np.bool_):
        raise ValueError("BLOCKED_B1R_P2C_SOURCE_INPUT_SHAPE")
    budget = VARIANTS[variant]
    positions = np.flatnonzero(ink_mask.ravel())
    if not positions.size:
        raise ValueError("BLOCKED_B1R_P2C_EMPTY_SOURCE_INK")
    source_pixels = original.reshape(-1, 3)[positions]
    if unique_rgb(source_pixels) < budget:
        raise ValueError("BLOCKED_B1R_P2C_INSUFFICIENT_SOURCE_RGB")
    source_lab = color.rgb2lab(
        source_pixels.astype(np.float64).reshape(-1, 1, 3) / 255.0,
    ).reshape(-1, 3)
    centers, groups = kmeans2(
        source_lab, budget, iter=CLUSTER_ITERATIONS, minit="++",
        missing="raise", seed=CLUSTER_SEED,
    )
    if (not np.all(np.isfinite(centers)) or
            not np.all(np.isfinite(source_lab))):
        raise ValueError("BLOCKED_B1R_P2C_NONFINITE_CLUSTERS")
    if len(centers) != budget or len(groups) != len(positions):
        raise ValueError("BLOCKED_B1R_P2C_INVALID_CLUSTER_COUNT")
    if not np.array_equal(np.unique(groups), np.arange(budget)):
        raise ValueError("BLOCKED_B1R_P2C_EMPTY_CLUSTER")
    selected = np.zeros((budget, 3), dtype=np.uint8)
    ledger = []
    for i in range(budget):
        members = np.flatnonzero(groups == i)
        distance_sq = np.sum((source_lab[members] - centers[i]) ** 2, axis=1)
        member_index = int(members[int(np.argmin(distance_sq))])
        source_index = int(positions[member_index])
        y, x = divmod(source_index, FULL_SHAPE[1])
        selected[i] = original[y, x]
        ledger.append({
            "cluster": i,
            "member_count": int(members.size),
            "source_full_xy": [int(x), int(y)],
            "source_RGB": selected[i].tolist(),
        })
    mapped = selected[groups]
    full = flat.copy()
    full.reshape(-1, 3)[positions] = mapped
    if not np.array_equal(full[~ink_mask], flat[~ink_mask]):
        raise AssertionError("BLOCKED_B1R_P2C_CHANGED_NON_INK")
    masked_colors = {tuple(row) for row in source_pixels}
    if not all(tuple(c) in masked_colors for c in np.unique(mapped, axis=0)):
        raise AssertionError("BLOCKED_B1R_P2C_NON_SOURCE_PALETTE")
    for entry in ledger:
        x, y = entry["source_full_xy"]
        if (not ink_mask[y, x] or
                list(original[y, x]) != entry["source_RGB"]):
            raise AssertionError("BLOCKED_B1R_P2C_MEDOID_PROVENANCE")
    rgba = np.zeros((*FULL_SHAPE[:2], 4), dtype=np.uint8)
    rgba[ink_mask, :3] = mapped
    rgba[ink_mask, 3] = 255
    return full, rgba, ledger


def resample_discrete(full: np.ndarray) -> np.ndarray:
    if full.shape != FULL_SHAPE or full.dtype != np.uint8:
        raise ValueError("BLOCKED_B1R_P2C_DISCRETE_SHAPE")
    return np.asarray(Image.fromarray(full).resize(
        LOGICAL_WH, Image.Resampling.NEAREST), dtype=np.uint8).copy()


def evaluate(original_logical: np.ndarray, flat_full: np.ndarray,
             flat_logical: np.ndarray, reference_logical: np.ndarray,
             candidate_full: np.ndarray, candidate_lanczos: np.ndarray,
             candidate_discrete: np.ndarray, mask: np.ndarray,
             ledger: list, budget: int):
    source_stats, source_lab, result_lab = delta_metrics(
        original_logical, candidate_lanczos)
    reference_stats, _, _ = delta_metrics(original_logical, reference_logical)
    edge_recall = fixed_original_edge_recall(original_logical, candidate_lanczos)
    chroma0 = np.linalg.norm(source_lab[..., 1:3], axis=-1)
    chroma1 = np.linalg.norm(result_lab[..., 1:3], axis=-1)
    flat_unique = unique_rgb(flat_full)
    full_unique = unique_rgb(candidate_full)
    discrete_unique = unique_rgb(candidate_discrete)
    masked_distinct = unique_rgb(candidate_full[mask])
    source_distinct = unique_rgb(mask.astype(np.uint8)[..., None].repeat(3, axis=-1))
    # All count gates apply to the uninterpolated full and NEAREST sources.
    stats = {
        "source_original_lanczos": source_stats,
        "same_run_uncompressed_K_DETAIL_lanczos": reference_stats,
        "source_original_ink_pixels": int(np.count_nonzero(mask)),
        "flat_full_distinct_RGB": flat_unique,
        "flat_logical_distinct_RGB": unique_rgb(flat_logical),
        "full_composite_distinct_RGB": full_unique,
        "logical_discrete_NEAREST_distinct_RGB": discrete_unique,
        "logical_visual_LANCZOS_distinct_RGB_NOT_palette": unique_rgb(candidate_lanczos),
        "compressed_masked_RGB_distinct": masked_distinct,
        "source_ink_source_mask_nonempty": bool(mask.any()),
        "original_fixed_sobel90_1px_recall": edge_recall,
        "logical_chroma_excess_vs_source_plus12":
            int(np.count_nonzero(chroma1 > chroma0 + 12)),
        "per_cluster_source_rgb_ledger_count": len(ledger),
    }
    gates = {
        "ink_mask_nonempty": stats["source_ink_source_mask_nonempty"],
        "exact_budget_ledger": len(ledger) == budget,
        "source_member_provenance": True,
        "no_changes_outside_original_ink": True,
        "flat_full_colors_bounded": 0 < flat_unique <= 900,
        "full_rgb_bounded": full_unique <= flat_unique + budget,
        "discrete_logical_no_new_colors": discrete_unique <= full_unique,
        "mean_deltaE00": source_stats["mean_deltaE00"] <= 3.5,
        "p95_deltaE00": source_stats["p95_deltaE00"] <= 11.0,
        "female_face_deltaE00":
            source_stats["female_face_eyes_mean_deltaE00"] <= 4.0,
        "male_face_deltaE00":
            source_stats["male_face_eyes_mean_deltaE00"] <= 4.0,
        "hands_deltaE00": source_stats["hands_mean_deltaE00"] <= 4.5,
        "female_face_baseline_drift_max2":
            source_stats["female_face_eyes_mean_deltaE00"] <=
            reference_stats["female_face_eyes_mean_deltaE00"] + 2.0,
        "male_face_baseline_drift_max2":
            source_stats["male_face_eyes_mean_deltaE00"] <=
            reference_stats["male_face_eyes_mean_deltaE00"] + 2.0,
        "original_edge_recall": edge_recall >= .90,
        "chroma_excess": stats["logical_chroma_excess_vs_source_plus12"] <= 600,
    }
    stats["gates"] = gates
    stats["status"] = ("SOURCE_SCREEN_PASS_VISUAL_PENDING"
                       if all(gates.values()) else "SOURCE_GATE_FAIL")
    return stats


def visual_panel(names_and_arrays: list, destination: Path):
    canvas = Image.new("RGB", (len(names_and_arrays) * 450, 755), "white")
    painter = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 21)
    except OSError:
        font = ImageFont.load_default()
    for col, (name, img) in enumerate(names_and_arrays):
        if img.shape != LOGICAL_SHAPE or img.dtype != np.uint8:
            raise ValueError("BLOCKED_B1R_P2C_VISUAL_DIMENSION")
        canvas.paste(Image.fromarray(img).resize(
            (450, 720), Image.Resampling.NEAREST), (col * 450, 35))
        painter.text((col * 450 + 6, 6), name,
                     font=font, fill=(0, 0, 0))
    canvas.save(destination)


def region_crops(original: np.ndarray, flat: np.ndarray,
                 reference: np.ndarray, candidates: dict, root: Path):
    for name, (x0, y0, x1, y1) in ROIS_FULL.items():
        fx0, fy0, fx1, fy1 = (round(x0 * .75), round(y0 * .75),
                              round(x1 * .75), round(y1 * .75))
        cuts = [a[fy0:fy1, fx0:fx1] for a in
                (original, flat, reference,
                 candidates["C_096"], candidates["C_192"])]
        h, w = cuts[0].shape[:2]
        dest = Image.new("RGB", (w * 5 * 4, h * 4), "white")
        for i, sample in enumerate(cuts):
            dest.paste(Image.fromarray(sample).resize(
                (w * 4, h * 4), Image.Resampling.NEAREST),
                (i * w * 4, 0))
        dest.save(root / ("REVIEW_ROI_" + name + ".png"))


def run(source: Path, destination: Path):
    if destination.exists():
        raise ValueError("BLOCKED_B1R_P2C_OVERWRITE")
    original = check_source(source)
    f = full_features(original)
    filtered = filter_original(original, "A_SOFT", f["protected"])
    labels = slic_labels(filtered, "J_FINE")
    flat, flat_ledger = source_region_medoids(original, labels)
    ink_mask, exact_rgba, reference_full, exact_summary = ink_residual(
        original, flat, f, "K_DETAIL")
    original_logical = logical_rgb(original)
    flat_logical = logical_region_map(flat)
    ref_logical = logical_composite(reference_full)
    destination.mkdir(parents=True)
    Image.fromarray(original).save(destination / "00_ORIGINAL_FULL_RGB.png")
    Image.fromarray(original_logical).save(destination / "00_ORIGINAL_LOGICAL_RGB.png")
    Image.fromarray(flat).save(destination / "01_FLAT_REGION_MEDOIDS_FULL.png")
    Image.fromarray(flat_logical).save(destination / "01_FLAT_REGION_MEDOIDS_LOGICAL.png")
    Image.fromarray((ink_mask * 255).astype(np.uint8)).save(
        destination / "02_SOURCE_INK_GEOMETRY_MASK.png")
    Image.fromarray(reference_full).save(
        destination / "03_UNCOMPRESSED_K_DETAIL_FULL.png")
    Image.fromarray(ref_logical).save(
        destination / "03_UNCOMPRESSED_K_DETAIL_LANCZOS.png")
    np.save(destination / "SOURCE_ONLY_REGION_LABELS_FULL.npy",
            labels, allow_pickle=False)
    (destination / "SOURCE_ONLY_FLAT_REGION_LEDGER.json").write_text(
        json.dumps(flat_ledger, ensure_ascii=False, indent=2) + "\n",
        encoding="utf8")
    candidates, discrete, metrics = {}, {}, {}
    masks = {}
    for name, budget in VARIANTS.items():
        full, rgba, palette_ledger = compress_source_ink(
            original, flat, ink_mask, name)
        if not np.array_equal(full[~ink_mask], flat[~ink_mask]):
            raise AssertionError("BLOCKED_B1R_P2C_NON_INK_RGB_CHANGED")
        preview = logical_composite(full)
        nearest = resample_discrete(full)
        metrics[name] = evaluate(
            original_logical, flat, flat_logical,
            ref_logical, full, preview, nearest, ink_mask,
            palette_ledger, budget)
        candidates[name] = preview
        discrete[name] = nearest
        masks[name] = full
        Image.fromarray(full).save(destination / (name + "_COMPRESSED_FULL_RGB.png"))
        Image.fromarray(preview).save(
            destination / (name + "_VISUAL_LANCZOS_RGB.png"))
        Image.fromarray(nearest).save(
            destination / (name + "_DISCRETE_NEAREST_RGB.png"))
        Image.fromarray(rgba).save(
            destination / (name + "_SOURCE_MEMBER_INK_RGBA.png"))
        (destination / (name + "_INK_MEDOIDS.json")).write_text(
            json.dumps(palette_ledger, ensure_ascii=False, indent=2) + "\n",
            encoding="utf8")
    visual_panel([
        ("ORIGINAL", original_logical),
        ("FLAT 252", flat_logical),
        ("P2B K_DETAIL", ref_logical),
        ("C_096", candidates["C_096"]),
        ("C_192", candidates["C_192"]),
    ], destination / "REVIEW_MAIN_ORIGINAL_FLAT_P2B_C096_C192.png")
    visual_panel([
        ("C_096 NEAREST", discrete["C_096"]),
        ("C_192 NEAREST", discrete["C_192"]),
    ], destination / "REVIEW_DISCRETE_COLOR_SWATCHES.png")
    region_crops(
        original_logical, flat_logical, ref_logical, candidates, destination)
    (destination / "README_REVIEW_RU.txt").write_text(
        "ENGINE-001 B1-R-P2C. Визуальная проверка оригинала и двух вариантов\n"
        "Откройте REVIEW_MAIN_ORIGINAL_FLAT_P2B_C096_C192.png: оригинал,\n"
        "плоская карта, предыдущий P2B K_DETAIL, новые C_096 и C_192.\n"
        "REVIEW_ROI_* — увеличенные исходные области лиц, рук и одежды,\n"
        "тот же порядок пяти колонок. REVIEW_DISCRETE_COLOR_SWATCHES.png\n"
        "показывает математическую палитру NEAREST без новых смешанных тонов.\n"
        "Остальные PNG/JSON/NPY — источники аудита и карта выбранных цветов.\n"
        "Палитры 96/192 — ИССЛЕДОВАТЕЛЬСКИЕ, НЕ игровые 32 цвета.\n"
        "Линии оригинала не являются готовой геометрией кисти Egret.\n"
        "Визуальную пригодность исходного рисунка должен подтвердить человек.\n",
        encoding="utf8",
    )
    file_sha = {
        p.name: digest(p.read_bytes()) for p in sorted(destination.iterdir())
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
        "frozen_P2_V1_or_P2B_artifacts_used_as_input": False,
        "only_original_RGB_file_read": True,
        "full_original_shape": list(FULL_SHAPE),
        "logical_shape": list(LOGICAL_SHAPE),
        "source_ink_mask_original_pixels": int(np.count_nonzero(ink_mask)),
        "reference_original_only_K_DETAIL_full_RGB_unique": unique_rgb(reference_full),
        "reference_original_only_K_DETAIL_logical_unique": unique_rgb(ref_logical),
        "original_only_flat_labels": len(flat_ledger),
        "original_only_flat_full_RGB_unique": unique_rgb(flat),
        "original_only_flat_source_ink_geometry": exact_summary,
        "variant_budgets": VARIANTS,
        "clustering": {
            "seed": CLUSTER_SEED, "iterations": CLUSTER_ITERATIONS,
            "method": "scipy.cluster.vq.kmeans2",
            "minit": "++", "missing": "raise",
            "palette": "original_in_mask_RGB_medoid_only",
        },
        "metrics": metrics,
        "file_sha256": file_sha,
        "human_visual": "PENDING",
        "game32_projection": "NOT_RUN",
        "native_Egret_brush": "NOT_RUN",
        "live_E4": "NOT_RUN",
        "independent_E5": "NOT_RUN",
        "exact_game_CHALK": None,
        "production_accepted": False,
        "versions": {
            "python": platform.python_version(), "numpy": np.__version__,
            "scipy": scipy.__version__, "skimage": skimage.__version__,
            "opencv": cv2.__version__, "Pillow": Image.__version__,
        },
    }
    (destination / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf8",
    )
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    report = run(args.source, args.output)
    for name, result in report["metrics"].items():
        print(name, result["status"],
              "full_colors", result["full_composite_distinct_RGB"],
              "nearest_colors", result["logical_discrete_NEAREST_distinct_RGB"],
              "meanDE00", round(result["source_original_lanczos"]["mean_deltaE00"], 4),
              "faceF", round(result["source_original_lanczos"]["female_face_eyes_mean_deltaE00"], 4),
              "faceM", round(result["source_original_lanczos"]["male_face_eyes_mean_deltaE00"], 4),
              "failed", [k for k,v in result["gates"].items() if not v])
    print("PALETTE32_NATIVE_E4_E5_EXACT_CHALK_NOT_RUN")

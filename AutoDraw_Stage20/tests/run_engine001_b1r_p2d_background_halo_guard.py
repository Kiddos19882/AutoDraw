#!/usr/bin/env python3
"""ENGINE-001 B1-R-P2D: original RGB source-bright background correction only.

Research-only mathematical preview. Not native Egret, game32, or exact CHALK.
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
    FULL_SHAPE, LOGICAL_WH, SOURCE_SHA256,
    check_source, filter_original, full_features, logical_rgb,
)
from run_engine001_b1r_p2_joint_region_outline import (
    delta_metrics, digest, fixed_original_edge_recall,
    logical_region_map, slic_labels, source_region_medoids,
)
from run_engine001_b1r_p2b_residual_ink import (
    ink_residual, logical_composite,
)
from run_engine001_b1r_p2c_source_ink_palette import (
    VARIANTS as INK_PALETTES,
    compress_source_ink, resample_discrete, unique_rgb,
)

EXPERIMENT = "ENGINE001_B1R_P2D_SOURCE_BRIGHT_HALO_GUARD_V1"
GUARD_VARIANTS = ("D_BORDER", "D_COMPONENT24")
FULL_COORDINATES = "original_RGB_200x320"
HAIR_ROI_LOGICAL = (76, 4, 91, 19)
HAIR_CROP_LOGICAL = (70, 2, 104, 42)
ORIGINAL_MIN_CHANNEL = 245
ORIGINAL_MAX_CHANNEL_SPREAD = 18
SOURCE_FLAT_MEAN_DARKENING = 12
FLAT_MEAN_MAX = 239
COMPONENT_MINIMUM_PIXELS = 24
SOURCE_HAIR_BASELINE_EXPECTED = 27


def source_bright_guard(original: np.ndarray, flat: np.ndarray,
                        ink_mask: np.ndarray, strategy: str):
    """Derive protection exclusively from original RGB and current-run flat map.

    Changes never depend on a specific image coordinate (except source-white
    swatch provenance). Annotated ROI is exclusively a *measurement*.
    """
    if strategy not in GUARD_VARIANTS:
        raise ValueError("BLOCKED_B1R_P2D_UNKNOWN_STRATEGY")
    if (original.shape != FULL_SHAPE or original.dtype != np.uint8 or
            flat.shape != FULL_SHAPE or flat.dtype != np.uint8 or
            ink_mask.shape != FULL_SHAPE[:2] or
            ink_mask.dtype != np.bool_):
        raise ValueError("BLOCKED_B1R_P2D_SOURCE_FORMAT")
    if np.any(original[0, 0] < ORIGINAL_MIN_CHANNEL):
        raise ValueError("BLOCKED_B1R_P2D_SOURCE_WHITE_SWATCH")
    if int(np.max(original[0, 0])) - int(np.min(original[0, 0])) > ORIGINAL_MAX_CHANNEL_SPREAD:
        raise ValueError("BLOCKED_B1R_P2D_SOURCE_WHITE_SPREAD")

    source_min = np.min(original, axis=2)
    source_spread = (np.max(original, axis=2).astype(np.int16) -
                     source_min.astype(np.int16))
    bright = ((source_min >= ORIGINAL_MIN_CHANNEL) &
              (source_spread <= ORIGINAL_MAX_CHANNEL_SPREAD))
    src_mean = np.mean(original.astype(np.float64), axis=2)
    flat_mean = np.mean(flat.astype(np.float64), axis=2)
    false_gray = (bright &
                  (src_mean - flat_mean >= SOURCE_FLAT_MEAN_DARKENING) &
                  (flat_mean <= FLAT_MEAN_MAX))

    label_map, component_count = ndimage.label(
        bright, structure=np.ones((3, 3), dtype=np.uint8))
    if strategy == "D_BORDER":
        touching = np.unique(np.concatenate([
            label_map[0, :], label_map[-1, :],
            label_map[:, 0], label_map[:, -1],
        ]))
        touching = touching[touching != 0]
        supported = np.isin(label_map, touching) & bright
    elif strategy == "D_COMPONENT24":
        sizes = np.bincount(label_map.ravel())
        supported = bright & (sizes[label_map] >= COMPONENT_MINIMUM_PIXELS)
    else:
        raise AssertionError("BLOCKED_B1R_P2D_STRATEGY_LOGIC")

    guard = false_gray & supported & ~ink_mask
    if not np.any(guard):
        raise ValueError("BLOCKED_B1R_P2D_NO_CONFIRMED_SOURCE_GRAY")
    if np.any(guard & ink_mask) or np.any(guard & ~false_gray):
        raise AssertionError("BLOCKED_B1R_P2D_CHANGED_NOT_SOURCE_GRAY")
    return guard, {
        "total_source_bright_full": int(np.count_nonzero(bright)),
        "source_false_gray_full": int(np.count_nonzero(false_gray)),
        "source_bright_components": int(component_count),
        "guard_source_pixels": int(np.count_nonzero(guard)),
        "guard_changed_ink_pixels": int(np.count_nonzero(guard & ink_mask)),
        "corrected_rgb_source_xy": [0, 0],
        "corrected_rgb": original[0, 0].tolist(),
        "original_min_channel": ORIGINAL_MIN_CHANNEL,
        "original_spread_max": ORIGINAL_MAX_CHANNEL_SPREAD,
        "source_minus_flat_mean_threshold": SOURCE_FLAT_MEAN_DARKENING,
        "flat_mean_max": FLAT_MEAN_MAX,
        "bright_component_minimum": (
            "touching_original_full_border" if strategy == "D_BORDER"
            else COMPONENT_MINIMUM_PIXELS
        ),
        "original_full_coordinates": FULL_COORDINATES,
    }


def apply_source_bright_guard(original: np.ndarray,
                              base_full: np.ndarray,
                              original_ink_mask: np.ndarray,
                              guard: np.ndarray):
    if (original.shape != FULL_SHAPE or original.dtype != np.uint8 or
            base_full.shape != FULL_SHAPE or base_full.dtype != np.uint8 or
            original_ink_mask.shape != FULL_SHAPE[:2] or
            original_ink_mask.dtype != np.bool_ or
            guard.shape != FULL_SHAPE[:2] or guard.dtype != np.bool_):
        raise ValueError("BLOCKED_B1R_P2D_APPLY_SHAPE")
    if np.any(guard & original_ink_mask):
        raise ValueError("BLOCKED_B1R_P2D_GUARD_OVERLAPS_INK")
    # Fail closed even if a future caller bypasses source_bright_guard():
    # never turn a genuine dark contour or colored detail into background white.
    if np.any(guard):
        original_guard = original[guard]
        spread = (np.max(original_guard, axis=1).astype(np.int16) -
                  np.min(original_guard, axis=1).astype(np.int16))
        if (np.any(np.min(original_guard, axis=1) < ORIGINAL_MIN_CHANNEL)
                or np.any(spread > ORIGINAL_MAX_CHANNEL_SPREAD)):
            raise ValueError("BLOCKED_B1R_P2D_NON_SOURCE_BRIGHT_MASK")
    corrected = base_full.copy()
    corrected[guard] = original[0, 0]
    if not np.array_equal(corrected[~guard], base_full[~guard]):
        raise AssertionError("BLOCKED_B1R_P2D_NON_GUARD_CHANGED")
    if not np.array_equal(corrected[original_ink_mask],
                          base_full[original_ink_mask]):
        raise AssertionError("BLOCKED_B1R_P2D_INK_CHANGED")
    if not np.all(corrected[guard] == original[0, 0]):
        raise AssertionError("BLOCKED_B1R_P2D_SOURCE_SWATCH_MISMATCH")
    if unique_rgb(corrected) > unique_rgb(base_full) + 1:
        raise AssertionError("BLOCKED_B1R_P2D_NEW_COLORS")
    return corrected


def hair_dark_count(original_logical: np.ndarray, candidate_logical: np.ndarray):
    if (original_logical.shape != (240, 150, 3) or
            candidate_logical.shape != (240, 150, 3)):
        raise ValueError("BLOCKED_B1R_P2D_HAIR_RGB_SHAPE")
    x0, y0, x1, y1 = HAIR_ROI_LOGICAL
    src = original_logical[y0:y1, x0:x1].astype(np.float64)
    cand = candidate_logical[y0:y1, x0:x1].astype(np.float64)
    bright = np.min(src, axis=2) >= ORIGINAL_MIN_CHANNEL
    false_gray = bright & (
        (np.mean(src, axis=2) - np.mean(cand, axis=2)) >= SOURCE_FLAT_MEAN_DARKENING
    )
    return {
        "original_bright_logical_pixels": int(np.count_nonzero(bright)),
        "false_dark_logical_pixels": int(np.count_nonzero(false_gray)),
        "marked_ROI_logical_xyxy": list(HAIR_ROI_LOGICAL),
    }


def source_delta(original_logical: np.ndarray, candidate_logical: np.ndarray):
    stats, src_lab, cand_lab = delta_metrics(original_logical, candidate_logical)
    chroma_original = np.linalg.norm(src_lab[..., 1:3], axis=-1)
    chroma_candidate = np.linalg.norm(cand_lab[..., 1:3], axis=-1)
    return {
        "deltaE00": stats,
        "original_fixed_sobel90_recall_1px":
            fixed_original_edge_recall(original_logical, candidate_logical),
        "source_chroma_excess_plus12":
            int(np.count_nonzero(chroma_candidate > chroma_original + 12)),
    }


def evaluate(original_logical: np.ndarray, base_full: np.ndarray,
             baseline_visual: np.ndarray, baseline_nearest: np.ndarray,
             candidate_full: np.ndarray, candidate_visual: np.ndarray,
             candidate_nearest: np.ndarray, guard_mask: np.ndarray,
             ink_mask: np.ndarray, source_ink_palette_size: int):
    baseline = source_delta(original_logical, baseline_visual)
    current = source_delta(original_logical, candidate_visual)
    a = baseline["deltaE00"]
    b = current["deltaE00"]
    oldhair = hair_dark_count(original_logical, baseline_nearest)
    newhair = hair_dark_count(original_logical, candidate_nearest)
    same_ink = np.array_equal(
        candidate_full[ink_mask], base_full[ink_mask])
    unchanged_elsewhere = np.array_equal(
        candidate_full[~guard_mask], base_full[~guard_mask])
    original_full_colors = unique_rgb(base_full)
    new_full_colors = unique_rgb(candidate_full)
    nearest_colors = unique_rgb(candidate_nearest)
    new_color_budget = source_ink_palette_size
    gates = {
        "guard_nonzero": bool(guard_mask.any()),
        "guard_disjoint_ink": not bool(np.any(guard_mask & ink_mask)),
        "K_DETAIL_ink_source_palette_unmodified": same_ink,
        "all_pixels_outside_guard_unchanged": unchanged_elsewhere,
        "full_RGB_plus_one_color_bound": new_full_colors <= original_full_colors + 1,
        "NEAREST_no_synthetic_colors": nearest_colors <= new_full_colors,
        "baseline_hair_reproduces_E1": (
            oldhair["false_dark_logical_pixels"] == SOURCE_HAIR_BASELINE_EXPECTED
        ),
        "marked_hair_false_dark_reduced": (
            newhair["false_dark_logical_pixels"] <
            oldhair["false_dark_logical_pixels"]
        ),
        "marked_hair_false_dark_at_most20": (
            newhair["false_dark_logical_pixels"] <= 20
        ),
        "whole_source_mean_DeltaE00_within0p10": (
            b["mean_deltaE00"] <= a["mean_deltaE00"] + .10
        ),
        "whole_source_p95_DeltaE00_within0p35": (
            b["p95_deltaE00"] <= a["p95_deltaE00"] + .35
        ),
        "female_face_mean_within0p20": (
            b["female_face_eyes_mean_deltaE00"] <=
            a["female_face_eyes_mean_deltaE00"] + .20
        ),
        "male_face_mean_within0p20": (
            b["male_face_eyes_mean_deltaE00"] <=
            a["male_face_eyes_mean_deltaE00"] + .20
        ),
        "hands_mean_within0p20": (
            b["hands_mean_deltaE00"] <= a["hands_mean_deltaE00"] + .20
        ),
        "original_edge_recall_at_least0p90": (
            current["original_fixed_sobel90_recall_1px"] >= .90
        ),
        "no_source_chroma_excess_over600": (
            current["source_chroma_excess_plus12"] <= 600
        ),
    }
    return {
        "source_ink_budget_unchanged": new_color_budget,
        "corrected_original_full_pixels": int(guard_mask.sum()),
        "baseline_full_unique_RGB": original_full_colors,
        "candidate_full_unique_RGB": new_full_colors,
        "candidate_NEAREST_unique_RGB": nearest_colors,
        "candidate_LANCZOS_unique_RGB_NOT_game_palette": unique_rgb(candidate_visual),
        "baseline_original_source_quality": baseline,
        "candidate_original_source_quality": current,
        "marked_hair_before": oldhair,
        "marked_hair_after": newhair,
        "gates": gates,
        "status": (
            "SOURCE_SCREEN_PASS_VISUAL_PENDING"
            if all(gates.values()) else "SOURCE_GATE_FAIL"
        ),
    }


def draw_panel(items: list[tuple[str, np.ndarray]],
               path: Path, crop: tuple | None = None, scale: int = 3):
    arrays = []
    for _, a in items:
        if a.shape != (240, 150, 3) or a.dtype != np.uint8:
            raise ValueError("BLOCKED_B1R_P2D_PREVIEW_SHAPE")
        if crop is not None:
            x0, y0, x1, y1 = crop
            arrays.append(a[y0:y1, x0:x1])
        else:
            arrays.append(a)
    widths = [a.shape[1] * scale for a in arrays]
    heights = [a.shape[0] * scale for a in arrays]
    canvas = Image.new("RGB", (sum(widths), max(heights) + 35), "white")
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 17)
    except OSError:
        font = ImageFont.load_default()
    x = 0
    for (name, _), sample, width in zip(items, arrays, widths):
        draw.text((x + 5, 7), name, font=font, fill=(0, 0, 0))
        canvas.paste(
            Image.fromarray(sample).resize(
                (width, sample.shape[0] * scale), Image.Resampling.NEAREST),
            (x, 35),
        )
        x += width
    canvas.save(path)


def run(source: Path, output: Path):
    if output.exists():
        raise ValueError("BLOCKED_B1R_P2D_OVERWRITE")
    original = check_source(source)
    f = full_features(original)
    filtered = filter_original(original, "A_SOFT", f["protected"])
    labels = slic_labels(filtered, "J_FINE")
    flat_full, flat_ledger = source_region_medoids(original, labels)
    ink_mask, _, k_detail_full, ink_summary = ink_residual(
        original, flat_full, f, "K_DETAIL")
    original_logical = logical_rgb(original)
    flat_logical = logical_region_map(flat_full)
    k_detail_logical = logical_composite(k_detail_full)

    # Compute source-only masks independently of P2C palette assignments.
    guards = {}
    guard_ledgers = {}
    for strategy in GUARD_VARIANTS:
        guards[strategy], guard_ledgers[strategy] = source_bright_guard(
            original, flat_full, ink_mask, strategy)
    # A guard must not derive from any baseline candidate or earlier artifact.
    output.mkdir(parents=True)
    Image.fromarray(original).save(output / "ORIGINAL_FULL_RGB.png")
    Image.fromarray(original_logical).save(output / "ORIGINAL_LOGICAL_RGB.png")
    Image.fromarray(flat_full).save(output / "J_FINE_FLAT_FULL_RGB.png")
    Image.fromarray(flat_logical).save(output / "J_FINE_FLAT_LOGICAL_RGB.png")
    Image.fromarray(k_detail_logical).save(output / "K_DETAIL_ORIGINAL_RGB_LANCZOS.png")
    Image.fromarray((ink_mask * 255).astype(np.uint8)).save(
        output / "K_DETAIL_SOURCE_INK_MASK_FULL.png")
    Image.fromarray((np.min(original, axis=2) >= ORIGINAL_MIN_CHANNEL).astype(np.uint8) * 255).save(
        output / "ORIGINAL_SOURCE_BRIGHT_MIN245_DEBUG.png")
    np.save(output / "ORIGINAL_ONLY_J_FINE_REGION_LABELS.npy", labels,
            allow_pickle=False)
    (output / "ORIGINAL_ONLY_REGION_RGB_PROVENANCE.json").write_text(
        json.dumps(flat_ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    for strategy, guard in guards.items():
        Image.fromarray((guard * 255).astype(np.uint8)).save(
            output / (strategy + "_CORRECTED_SOURCE_MASK_FULL.png"))
    results = {}
    source_baselines = {}
    for budget in INK_PALETTES:
        base_full, _, ink_ledger = compress_source_ink(
            original, flat_full, ink_mask, budget)
        base_nearest = resample_discrete(base_full)
        base_visual = logical_composite(base_full)
        source_baselines[budget] = {
            "baseline_full_RGB_distinct": unique_rgb(base_full),
            "baseline_NEAREST_RGB_distinct": unique_rgb(base_nearest),
            "baseline_annotated_hair_false_dark": hair_dark_count(
                original_logical, base_nearest),
        }
        Image.fromarray(base_full).save(
            output / (budget + "_FROZEN_MATH_BASELINE_FULL_RGB.png"))
        Image.fromarray(base_nearest).save(
            output / (budget + "_FROZEN_MATH_BASELINE_NEAREST_RGB.png"))
        Image.fromarray(base_visual).save(
            output / (budget + "_FROZEN_MATH_BASELINE_LANCZOS_RGB.png"))
        (output / (budget + "_FROZEN_MATH_SOURCE_INK_LEDGER.json")).write_text(
            json.dumps(ink_ledger, ensure_ascii=False, indent=2) + "\n",
            encoding="utf8")
        visual_items = [
            ("ORIGINAL", original_logical),
            ("FLAT", flat_logical),
            ("P2B K_DETAIL", k_detail_logical),
            (budget + " OLD", base_nearest),
        ]
        visual_lanczos_items = [
            ("ORIGINAL", original_logical),
            ("FLAT", flat_logical),
            ("P2B K_DETAIL", k_detail_logical),
            (budget + " OLD", base_visual),
        ]
        results[budget] = {}
        for strategy in GUARD_VARIANTS:
            masked = apply_source_bright_guard(
                original, base_full, ink_mask, guards[strategy])
            new_visual = logical_composite(masked)
            new_nearest = resample_discrete(masked)
            result = evaluate(
                original_logical, base_full, base_visual, base_nearest,
                masked, new_visual, new_nearest, guards[strategy],
                ink_mask, INK_PALETTES[budget],
            )
            results[budget][strategy] = result
            prefix = budget + "_" + strategy
            Image.fromarray(masked).save(
                output / (prefix + "_CORRECTED_FULL_RGB.png"))
            Image.fromarray(new_nearest).save(
                output / (prefix + "_CORRECTED_NEAREST_RGB.png"))
            Image.fromarray(new_visual).save(
                output / (prefix + "_CORRECTED_LANCZOS_RGB.png"))
            visual_items.append((strategy, new_nearest))
            visual_lanczos_items.append((strategy, new_visual))
        draw_panel(visual_items, output / (
            "REVIEW_" + budget + "_NEAREST_ORIG_FLAT_KDETAIL_BASE_D_BORDER_D_COMPONENT24.png"),
            crop=None, scale=3)
        draw_panel(visual_items, output / (
            "REVIEW_" + budget + "_MARKED_HAIR_NEAREST_x12.png"),
            crop=HAIR_CROP_LOGICAL, scale=12)
        draw_panel(visual_lanczos_items, output / (
            "REVIEW_" + budget + "_MARKED_HAIR_LANCZOS_x12.png"),
            crop=HAIR_CROP_LOGICAL, scale=12)
    (output / "README_REVIEW_RU.txt").write_text(
        "B1-R-P2D: обе P2C палитры сохранены, исправляется только источник\n"
        "ошибочного затемнения почти белого фона. В одном ZIP: все результаты.\n"
        "Сначала смотрите REVIEW_C_096_MARKED_HAIR_NEAREST_x12.png и\n"
        "REVIEW_C_192_MARKED_HAIR_NEAREST_x12.png. Колонки: ORIGINAL,\n"
        "FLAT, P2B K_DETAIL, P2C OLD, D_BORDER, D_COMPONENT24.\n"
        "Далее REVIEW_*_NEAREST_ORIG...png (вся картинка) и\n"
        "REVIEW_*_MARKED_HAIR_LANCZOS_x12.png (сглаженный просмотр).\n"
        "Все белые исправленные пиксели — источник original[0,0], не игра.\n"
        "Цифровые гейты в report.json; технический PASS не означает\n"
        "визуальный PASS, native Egret, CHALK или 32 игровых цвета.\n",
        encoding="utf8",
    )
    file_hashes = {
        p.name: digest(p.read_bytes()) for p in sorted(output.iterdir())
        if p.is_file()
    }
    report = {
        "experiment": EXPERIMENT,
        "source_original_sha256": SOURCE_SHA256,
        "github_sha": os.getenv("GITHUB_SHA"),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "source_only_original_file_read": True,
        "no_frozen_P2B_or_P2C_artifacts_read_as_inputs": True,
        "legacy_G32_input": False,
        "legacy_V44_input": False,
        "legacy_M1_input": False,
        "source_full_dimensions": list(FULL_SHAPE),
        "original_region_labels_count": len(flat_ledger),
        "original_flat_RGB_unique": unique_rgb(flat_full),
        "original_ink_mask_pixels": int(np.count_nonzero(ink_mask)),
        "original_ink_summary": ink_summary,
        "original_rgb_swatch_full_xy": [0, 0],
        "original_rgb_swatch": original[0, 0].tolist(),
        "baseline": source_baselines,
        "guard_parameters": {
            "strategies": list(GUARD_VARIANTS),
            "source_bright_min_channel": ORIGINAL_MIN_CHANNEL,
            "source_max_channel_spread": ORIGINAL_MAX_CHANNEL_SPREAD,
            "source_mean_minus_flat_min": SOURCE_FLAT_MEAN_DARKENING,
            "flat_mean_max": FLAT_MEAN_MAX,
            "minimum_component_pixels": COMPONENT_MINIMUM_PIXELS,
            "marked_hair_logical_xyxy": list(HAIR_ROI_LOGICAL),
            "E1_marked_hair_original_false_dark_count": SOURCE_HAIR_BASELINE_EXPECTED,
        },
        "guard_source_ledgers": guard_ledgers,
        "results": results,
        "file_sha256": file_hashes,
        "user_assessment_of_P2C": "BOTH_MOSTLY_GOOD_BUT_MARKED_DEFECT",
        "new_P2D_user_visual_signoff": "PENDING",
        "production_candidate": False,
        "game32_projection": "NOT_RUN",
        "native_Egret_round_brush": "NOT_RUN",
        "game_E4": "NOT_RUN",
        "independent_E5": "NOT_RUN",
        "exact_game_CHALK": None,
        "versions": {
            "python": platform.python_version(), "numpy": np.__version__,
            "scipy": scipy.__version__, "skimage": skimage.__version__,
            "opencv": cv2.__version__, "Pillow": Image.__version__,
        },
    }
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf8",
    )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run(args.source, args.output)
    for palette, strategies in result["results"].items():
        for strategy, item in strategies.items():
            print(
                palette, strategy, item["status"],
                "mark", item["marked_hair_before"]["false_dark_logical_pixels"],
                "->", item["marked_hair_after"]["false_dark_logical_pixels"],
                "changed_full_pixels", item["corrected_original_full_pixels"],
                "full_colors", item["candidate_full_unique_RGB"],
                "meanDE", round(item["candidate_original_source_quality"]["deltaE00"]["mean_deltaE00"], 5),
                "failed", [k for k, ok in item["gates"].items() if not ok],
            )
    print("PALETTE32_NATIVE_EGRET_E4_E5_EXACT_CHALK_NOT_RUN")

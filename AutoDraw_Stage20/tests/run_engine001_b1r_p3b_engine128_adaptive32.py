#!/usr/bin/env python3
"""B1-R-P3B independent original-source adaptive32 from static engine128.

Only offline source-palette screening. Never a native Egret/CHALK/ready game plan.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
from pathlib import Path

import cv2
import numpy as np
import scipy
import skimage
from PIL import Image, ImageDraw, ImageFont
from skimage import color

from run_engine001_b1r_p1_fullrgb_edge_aware import (
    FULL_SHAPE, LOGICAL_WH, ROIS_FULL, SOURCE_SHA256, check_source,
    filter_original, full_features, logical_rgb,
)
from run_engine001_b1r_p2_joint_region_outline import (
    delta_metrics, digest, fixed_original_edge_recall,
    slic_labels, source_region_medoids,
)
from run_engine001_b1r_p2b_residual_ink import ink_residual, logical_composite
from run_engine001_b1r_p2c_source_ink_palette import (
    VARIANTS as SOURCE_INK_BUDGETS,
    compress_source_ink, resample_discrete, unique_rgb,
)
from run_engine001_b1r_p2d_background_halo_guard import (
    GUARD_VARIANTS, source_bright_guard, apply_source_bright_guard,
    hair_dark_count,
)

EXPERIMENT = "ENGINE001_B1R_P3B_ENGINE128_ADAPTIVE32_V1"
ENGINE_GIT_BLOB_SHA1 = "46cc74de00b6cb5d207b1e1a2ffcd81613b6d388"
SOURCE_SHA = SOURCE_SHA256
ENGINE_SIZE = 4859418
ENGINE_COLOR_COUNT = 128
GAME_COLOR_BUDGET = 32
ENGINE_WHITE_INDEX = 6
LOGICAL_SHAPE = (240, 150, 3)
METHODS = ("A_BALANCED", "B_FACE_DETAIL")
METHOD_WEIGHTS = {
    "A_BALANCED": {"base": 1, "face_extra": 2, "hands_extra": 2, "edge_extra": 1},
    "B_FACE_DETAIL": {"base": 1, "face_extra": 10, "hands_extra": 5, "edge_extra": 3},
}
ENGINE_REGEX = re.compile(
    r"o\.prototype\.createElaborateEasterEggs=function\(\)\{"
    r"if\(0==this\._isPainterExtend\)return void this\.oldCreateElaborateEasterEggs\(\);"
    r"var e=\[([0-9,]+)\]"
)
OLD_REGEX = re.compile(
    r"o\.prototype\.oldCreateElaborateEasterEggs=function\(\)\{var e=\[([0-9,]+)\]"
)


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\x00" + data
    ).hexdigest()


def parse_engine_palette(js: str) -> np.ndarray:
    main_matches = list(ENGINE_REGEX.finditer(js))
    old_matches = list(OLD_REGEX.finditer(js))
    if len(main_matches) != 1 or len(old_matches) != 1:
        raise ValueError("BLOCKED_P3B_ENGINE_PALETTE_CONTEXT_NOT_UNIQUE")
    numbers = [int(v) for v in main_matches[0].group(1).split(",")]
    old_numbers = [int(v) for v in old_matches[0].group(1).split(",")]
    if (len(numbers) != ENGINE_COLOR_COUNT or
            numbers != old_numbers or
            len(set(numbers)) != ENGINE_COLOR_COUNT or
            any(n < 0 or n > 0xFFFFFF for n in numbers)):
        raise ValueError("BLOCKED_P3B_ENGINE_128_SWATCH_DRIFT")
    if numbers[ENGINE_WHITE_INDEX] != 0xFFFFFF:
        raise ValueError("BLOCKED_P3B_ENGINE_WHITE_INDEX_DRIFT")
    rgb = np.array([
        [(n >> 16) & 255, (n >> 8) & 255, n & 255] for n in numbers
    ], dtype=np.uint8)
    if unique_rgb(rgb) != 128:
        raise ValueError("BLOCKED_P3B_ENGINE_DUPLICATE_RGB")
    return rgb


def read_engine_palette(engine_js: Path) -> tuple[np.ndarray, dict]:
    data = engine_js.read_bytes()
    if git_blob_sha(data) != ENGINE_GIT_BLOB_SHA1 or len(data) != ENGINE_SIZE:
        raise ValueError("BLOCKED_P3B_ENGINE_BLOB_SHA_OR_SIZE")
    js = data.decode("utf-8")
    colors = parse_engine_palette(js)
    return colors, {
        "source_file": "AutoDraw_Stage20/gameEngine/main.min_653f95bc.js",
        "engine_git_blob_sha1": ENGINE_GIT_BLOB_SHA1,
        "engine_sha256": hashlib.sha256(data).hexdigest(),
        "engine_bytes": len(data),
        "painter_method": "PainterPopup.createElaborateEasterEggs",
        "old_painter_method_has_identical_128_swatches": True,
        "engine_colors": ENGINE_COLOR_COUNT,
        "swatch_availability_live_E4": "UNKNOWN",
        "engine_is_extended_mode_conditional": True,
        "swatch_RGB": [
            {"index": i, "hex": "#" + "".join(f"{v:02X}" for v in row),
             "RGB": row.tolist()}
            for i, row in enumerate(colors)
        ],
    }


def lab_rgb(array: np.ndarray) -> np.ndarray:
    if (array.dtype != np.uint8 or array.ndim != 3 or
            array.shape[-1] != 3):
        raise ValueError("BLOCKED_P3B_RGB_FORMAT")
    return color.rgb2lab(array.astype(np.float64) / 255)


def roi_logical(name: str):
    x0, y0, x1, y1 = ROIS_FULL[name]
    return (round(x0 * .75), round(y0 * .75),
            round(x1 * .75), round(y1 * .75))


def original_edge_map(original_logical: np.ndarray):
    if original_logical.shape != LOGICAL_SHAPE:
        raise ValueError("BLOCKED_P3B_ORIGINAL_LOGICAL_SHAPE")
    gray = cv2.cvtColor(original_logical, cv2.COLOR_RGB2GRAY).astype(np.float32)
    sx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    sy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    strength = np.hypot(sx, sy)
    nonzero = strength[strength > 0]
    if not len(nonzero):
        return np.zeros(strength.shape, dtype=bool)
    return (strength > 0) & (
        strength >= np.percentile(strength, 90)
    )


def selection_weights(original_logical: np.ndarray, method: str):
    if method not in METHODS:
        raise ValueError("BLOCKED_P3B_UNKNOWN_SELECTION")
    w = METHOD_WEIGHTS[method]
    weights = np.full(LOGICAL_SHAPE[:2], w["base"], dtype=np.float64)
    for name in ("female_face_eyes", "male_face_eyes"):
        x0, y0, x1, y1 = roi_logical(name)
        weights[y0:y1, x0:x1] += w["face_extra"]
    x0, y0, x1, y1 = roi_logical("hands")
    weights[y0:y1, x0:x1] += w["hands_extra"]
    weights[original_edge_map(original_logical)] += w["edge_extra"]
    if np.any(weights <= 0):
        raise AssertionError("BLOCKED_P3B_NONPOSITIVE_WEIGHTS")
    return weights


def unique_target_distances(target: np.ndarray, swatches: np.ndarray):
    if (target.shape != LOGICAL_SHAPE or target.dtype != np.uint8 or
            swatches.shape != (ENGINE_COLOR_COUNT, 3) or
            swatches.dtype != np.uint8):
        raise ValueError("BLOCKED_P3B_TARGET_OR_ENGINE_SHAPE")
    uniq, inverse = np.unique(
        target.reshape(-1, 3), axis=0, return_inverse=True
    )
    lab_target = lab_rgb(uniq.reshape(-1, 1, 3)).reshape(-1, 3)
    lab_swatches = lab_rgb(swatches.reshape(-1, 1, 3)).reshape(-1, 3)
    distances = color.deltaE_ciede2000(
        lab_target[:, None, :], lab_swatches[None, :, :]
    )
    if (distances.shape != (len(uniq), 128) or
            not np.all(np.isfinite(distances))):
        raise ValueError("BLOCKED_P3B_CIEDE2000_DISTANCES")
    return uniq, inverse.reshape(target.shape[:2]), distances, lab_swatches


def greedy_source_palette(target: np.ndarray, original: np.ndarray,
                          swatches: np.ndarray, method: str):
    if original.shape != LOGICAL_SHAPE or original.dtype != np.uint8:
        raise ValueError("BLOCKED_P3B_ORIGINAL_INPUT")
    uniq, inverse, distances, _ = unique_target_distances(target, swatches)
    weights = selection_weights(original, method)
    by_unique = np.bincount(
        inverse.ravel(), weights=weights.ravel(), minlength=len(uniq)
    )
    if not np.isclose(by_unique.sum(), weights.sum()):
        raise AssertionError("BLOCKED_P3B_WEIGHT_ACCOUNTING")
    used = np.zeros(ENGINE_COLOR_COUNT, dtype=bool)
    picked = [ENGINE_WHITE_INDEX]
    used[ENGINE_WHITE_INDEX] = True
    best_cost = distances[:, ENGINE_WHITE_INDEX] ** 2
    ledger = [{
        "step": 0, "engine_index": ENGINE_WHITE_INDEX,
        "weighted_squared_loss_after": float(np.dot(by_unique, best_cost)),
    }]
    # Pick nearest objective improvement; deterministic argmax lower index tie.
    for step in range(1, GAME_COLOR_BUDGET):
        future = np.minimum(best_cost[:, None], distances ** 2)
        benefit = np.sum(
            (best_cost[:, None] - future) * by_unique[:, None], axis=0
        )
        benefit[used] = -np.inf
        winner = int(np.argmax(benefit))
        if used[winner] or not np.isfinite(benefit[winner]):
            raise ValueError("BLOCKED_P3B_NOT_ENOUGH_DISTINCT_SWATCHES")
        used[winner] = True
        picked.append(winner)
        best_cost = future[:, winner]
        ledger.append({
            "step": step, "engine_index": winner,
            "weighted_squared_loss_after": float(np.dot(by_unique, best_cost)),
            "loss_reduction": float(benefit[winner]),
        })
    if (len(picked) != 32 or len(set(picked)) != 32 or
            ENGINE_WHITE_INDEX not in picked):
        raise AssertionError("BLOCKED_P3B_SELECTION_BUDGET")
    return np.asarray(picked, dtype=np.int16), ledger, {
        "method": method,
        "selection_weights": METHOD_WEIGHTS[method],
        "unique_target_RGB": int(len(uniq)),
        "weighted_squared_loss_final": float(np.dot(by_unique, best_cost)),
    }


def color_circular_hue_delta(orig_lab: np.ndarray,
                             swatch_lab: np.ndarray):
    source_hue = np.degrees(np.arctan2(orig_lab[..., 2], orig_lab[..., 1]))
    game_hue = np.degrees(np.arctan2(swatch_lab[:, 2], swatch_lab[:, 1]))
    return np.abs(((source_hue[..., None] - game_hue + 180) % 360) - 180)


def assign_engine32(target: np.ndarray, original: np.ndarray,
                    game128: np.ndarray, chosen: np.ndarray):
    if (target.shape != LOGICAL_SHAPE or target.dtype != np.uint8 or
            original.shape != LOGICAL_SHAPE or original.dtype != np.uint8 or
            game128.shape != (128, 3) or game128.dtype != np.uint8 or
            chosen.shape != (32,) or chosen.dtype != np.int16 or
            len(set(chosen.tolist())) != 32 or
            ENGINE_WHITE_INDEX not in chosen or
            np.any(chosen < 0) or np.any(chosen >= 128)):
        raise ValueError("BLOCKED_P3B_ASSIGNMENT_SHAPE_OR_PALETTE")
    colors = game128[chosen]
    target_lab = lab_rgb(target)
    orig_lab = lab_rgb(original)
    picked_lab = lab_rgb(colors.reshape(-1, 1, 3)).reshape(32, 3)
    # Stack bounded 32x36k CIEDE2000; no 36k x128xCIEDE full-buffer.
    target_de = color.deltaE_ciede2000(
        target_lab[..., None, :], picked_lab[None, None, :, :]
    )
    source_de = color.deltaE_ciede2000(
        orig_lab[..., None, :], picked_lab[None, None, :, :]
    )
    source_chroma = np.linalg.norm(orig_lab[..., 1:], axis=2)
    chosen_chroma = np.linalg.norm(picked_lab[:, 1:], axis=1)
    chroma_excess = np.maximum(
        0., chosen_chroma[None, None, :] -
        source_chroma[..., None] - 12.
    )
    hue_distance = color_circular_hue_delta(orig_lab, picked_lab)
    hue_valid = (
        (source_chroma[..., None] >= 12.) &
        (chosen_chroma[None, None, :] >= 12.)
    )
    hue_penalty = np.where(hue_valid,
                           np.maximum(hue_distance - 45., 0.), 0.)
    scores = (
        target_de +
        .6 * np.maximum(0., source_de - 16.) +
        1.5 * chroma_excess +
        .25 * hue_penalty
    )
    local_index = np.argmin(scores, axis=2)
    engine_index = chosen[local_index].astype(np.uint8)
    source_bright = np.min(original, axis=2) >= 245
    engine_index[source_bright] = ENGINE_WHITE_INDEX
    output_rgb = game128[engine_index]
    if (output_rgb.shape != LOGICAL_SHAPE or
            not np.array_equal(output_rgb, game128[engine_index]) or
            not set(np.unique(engine_index)).issubset(set(chosen.tolist()))):
        raise AssertionError("BLOCKED_P3B_NON_GAME_RGB_ASSIGNED")
    if not np.all(engine_index[source_bright] == ENGINE_WHITE_INDEX):
        raise AssertionError("BLOCKED_P3B_SOURCE_BACKGROUND_CHANGED")
    return engine_index, output_rgb


def full_engine128_diagnostic(target: np.ndarray, source: np.ndarray,
                              game128: np.ndarray):
    _, inverse, distances, _ = unique_target_distances(target, game128)
    engine_index = np.argmin(distances, axis=1)[inverse].astype(np.uint8)
    engine_index[np.min(source, axis=2) >= 245] = ENGINE_WHITE_INDEX
    return engine_index, game128[engine_index]


def connected_color_islands(index: np.ndarray):
    if index.shape != (240, 150):
        raise ValueError("BLOCKED_P3B_INDEX_SHAPE")
    count, tiny, single = 0, 0, 0
    by_color = []
    for idx in np.unique(index):
        pix = (index == idx).astype(np.uint8)
        n, labels, stats, _ = cv2.connectedComponentsWithStats(
            pix, connectivity=4
        )
        sizes = stats[1:, cv2.CC_STAT_AREA]
        count += len(sizes)
        tiny += int(np.count_nonzero(sizes <= 3))
        single += int(np.count_nonzero(sizes == 1))
        by_color.append({
            "engine_index": int(idx),
            "components4": len(sizes),
            "tiny_components_size1_3": int(np.count_nonzero(sizes <= 3)),
            "single_pixel_components": int(np.count_nonzero(sizes == 1)),
            "pixel_count": int(pix.sum()),
        })
    return {
        "components4": count,
        "tiny_components_size1_to3": tiny,
        "single_pixel_components": single,
        "per_engine_color": by_color,
    }


def source_quality(original: np.ndarray, rgb: np.ndarray,
                   index: np.ndarray, selected: np.ndarray):
    metrics, lab_source, lab_out = delta_metrics(original, rgb)
    c_src = np.linalg.norm(lab_source[..., 1:], axis=2)
    c_out = np.linalg.norm(lab_out[..., 1:], axis=2)
    hue = color_circular_hue_delta(
        lab_source, lab_out.reshape(-1, 3)
    ) if False else None
    hue_source = np.degrees(np.arctan2(lab_source[..., 2], lab_source[..., 1]))
    hue_out = np.degrees(np.arctan2(lab_out[..., 2], lab_out[..., 1]))
    hue_diff = np.abs(((hue_source - hue_out + 180) % 360) - 180)
    chroma_bad = c_out > c_src + 12
    hue_bad = (c_src >= 12) & (c_out >= 12) & (hue_diff > 45)
    recall = fixed_original_edge_recall(original, rgb)
    halo = hair_dark_count(original, rgb)
    used = np.unique(index)
    gates = {
        "real_engine_swatches_only": np.all(np.isin(used, selected)),
        "assigned_game_swatches_at_most32": len(used) <= 32,
        "original_mean_deltaE00_at_most5p5": metrics["mean_deltaE00"] <= 5.5,
        "original_p95_deltaE00_at_most22":
            metrics["p95_deltaE00"] <= 22.0,
        "female_face_eye_deltaE00_at_most11":
            metrics["female_face_eyes_mean_deltaE00"] <= 11.0,
        "male_face_eye_deltaE00_at_most11":
            metrics["male_face_eyes_mean_deltaE00"] <= 11.0,
        "hands_deltaE00_at_most11": metrics["hands_mean_deltaE00"] <= 11.0,
        "original_sobel90_edge_recall_at_least0p65": recall >= .65,
        "original_bright_hair_false_dark_at_most20":
            halo["false_dark_logical_pixels"] <= 20,
        "chroma_excess_pixels_at_most1500":
            int(chroma_bad.sum()) <= 1500,
        "hue_mismatch_pixels_at_most1200":
            int(hue_bad.sum()) <= 1200,
    }
    return {
        "original_deltaE00": metrics,
        "original_sobel90_1px_recall": recall,
        "hair_original_bright_false_dark_logical": halo,
        "source_chroma_excess_plus12": int(chroma_bad.sum()),
        "source_hue_mismatch_chroma12_hue45": int(hue_bad.sum()),
        "engine_color_indices_used": [int(x) for x in used],
        "connected_color_islands": connected_color_islands(index),
        "gates": {k: bool(v) for k, v in gates.items()},
        "status": ("SOURCE_SCREEN_PASS_VISUAL_PENDING_RUNTIME_ACCESS_UNVERIFIED"
                   if all(gates.values()) else "SOURCE_GATE_FAIL"),
        "source_chroma_excess_mask": chroma_bad,
        "source_hue_mismatch_mask": hue_bad,
    }


def review_panel(named: list[tuple[str, np.ndarray]], path: Path,
                 roi: tuple[int, int, int, int] | None = None,
                 scale: int = 3):
    images = []
    for name, rgb in named:
        if rgb.shape != LOGICAL_SHAPE or rgb.dtype != np.uint8:
            raise ValueError("BLOCKED_P3B_REVIEW_SOURCE_SHAPE")
        if roi is not None:
            x0, y0, x1, y1 = roi
            rgb = rgb[y0:y1, x0:x1]
        images.append((name, rgb))
    widths = [im.shape[1] * scale for _, im in images]
    height = max(im.shape[0] * scale for _, im in images) + 30
    sheet = Image.new("RGB", (sum(widths), height), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 14)
    except OSError:
        font = ImageFont.load_default()
    x = 0
    for (name, rgb), width in zip(images, widths):
        draw.text((x + 5, 5), name, fill=(0, 0, 0), font=font)
        sheet.paste(Image.fromarray(rgb).resize(
            (width, rgb.shape[0] * scale), Image.Resampling.NEAREST
        ), (x, 30))
        x += width
    sheet.save(path)


def swatch_sheet(engine_rgb: np.ndarray, chosen: dict[str, np.ndarray],
                  path: Path):
    scale = 36
    sheet = Image.new("RGB", (16 * scale, 8 * (scale + 16)), "white")
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 11)
    except OSError:
        font = ImageFont.load_default()
    selected = {int(x) for arr in chosen.values() for x in arr}
    for i, rgb in enumerate(engine_rgb):
        x, y = (i % 16) * scale, (i // 16) * (scale + 16)
        c = tuple(int(v) for v in rgb)
        d.rectangle((x, y, x + scale - 1, y + scale - 1), fill=c)
        d.text((x + 2, y + scale), str(i), fill="black", font=font)
        if i in selected:
            d.rectangle((x + 1, y + 1, x + scale - 2, y + scale - 2),
                        outline="white" if sum(c) < 360 else "black",
                        width=2)
    sheet.save(path)


def run(source: Path, engine_js: Path, output: Path):
    if output.exists():
        raise ValueError("BLOCKED_P3B_OUTPUT_EXISTS")
    original = check_source(source)
    game, provenance = read_engine_palette(engine_js)
    if original.shape != FULL_SHAPE or unique_rgb(game) != 128:
        raise ValueError("BLOCKED_P3B_INPUT_NOT_ORIGINAL_128")
    features = full_features(original)
    filtered = filter_original(original, "A_SOFT", features["protected"])
    labels = slic_labels(filtered, "J_FINE")
    flat, region_ledger = source_region_medoids(original, labels)
    ink_mask, _, _, detail_summary = ink_residual(
        original, flat, features, "K_DETAIL")
    original_logical = logical_rgb(original)
    guards = {}
    for variant in GUARD_VARIANTS:
        guards[variant], _ = source_bright_guard(
            original, flat, ink_mask, variant
        )
    if len(region_ledger) != 682 or int(ink_mask.sum()) != 14904:
        raise ValueError("BLOCKED_P3B_RECOMPUTED_ORIGINAL_SOURCE_GEOMETRY")
    output.mkdir(parents=True)
    Image.fromarray(original_logical).save(output / "00_ORIGINAL_RGB_LOGICAL.png")
    Image.fromarray(original).save(output / "00_ORIGINAL_RGB_FULL.png")
    Image.fromarray(flat).save(output / "01_SOURCE_J_FINE_FLAT_FULL_RGB.png")
    Image.fromarray((ink_mask.astype(np.uint8) * 255)).save(
        output / "02_SOURCE_K_DETAIL_INK_MASK_FULL.png")
    for k, v in guards.items():
        Image.fromarray(v.astype(np.uint8) * 255).save(
            output / (k + "_SOURCE_BACKGROUND_GUARD_FULL.png"))
    all_results, selections, candidates = {}, {}, {}
    for ink_budget in SOURCE_INK_BUDGETS:
        base, _, source_ledger = compress_source_ink(
            original, flat, ink_mask, ink_budget
        )
        (output / (ink_budget + "_SOURCE_INK_MEDOIDS.json")).write_text(
            json.dumps(source_ledger, ensure_ascii=False, indent=2) + "\n",
            encoding="utf8")
        for guard in GUARD_VARIANTS:
            full = apply_source_bright_guard(
                original, base, ink_mask, guards[guard]
            )
            want_unique = 347 if ink_budget == "C_096" else 443
            want_guard = 56 if guard == "D_BORDER" else 243
            if (unique_rgb(full) != want_unique or
                    np.count_nonzero(guards[guard]) != want_guard):
                raise ValueError("BLOCKED_P3B_SOURCE_P2D_BASELINE_DRIFT")
            target = resample_discrete(full)
            halo = hair_dark_count(original_logical, target)
            if halo["false_dark_logical_pixels"] != 1:
                raise ValueError("BLOCKED_P3B_SOURCE_P2D_HAIR_DRIFT")
            key = ink_budget + "_" + guard
            Image.fromarray(full).save(
                output / (key + "_P2D_ACCEPTED_SOURCE_FULL_RGB.png"))
            Image.fromarray(target).save(
                output / (key + "_P2D_ACCEPTED_SOURCE_NEAREST_RGB.png"))
            Image.fromarray(logical_composite(full)).save(
                output / (key + "_P2D_ACCEPTED_SOURCE_LANCZOS_RGB.png"))
            candidates[key] = target
            full128_id, full128_rgb = full_engine128_diagnostic(
                target, original_logical, game
            )
            Image.fromarray(full128_rgb).save(
                output / (key + "_FULL128_NEAREST_DIAGNOSTIC_NOT_32.png"))
            all_results[key] = {
                "source_full_RGB_count": unique_rgb(full),
                "source_logical_RGB_count": unique_rgb(target),
                "source_guard_original_full_pixels": int(guards[guard].sum()),
                "source_hair_false_gray_logical": halo,
                "full128_not_a_32_color_candidate": {
                    "game_colors_used": int(np.unique(full128_id).size),
                    "source_deltaE00": delta_metrics(
                        original_logical, full128_rgb)[0],
                },
                "palette32_methods": {},
            }
            variants = [
                ("ORIGINAL", original_logical),
                ("ACCEPTED " + key, target),
            ]
            for method in METHODS:
                chosen, ledger, sel_info = greedy_source_palette(
                    target, original_logical, game, method
                )
                selected_key = key + "_" + method
                selections[selected_key] = chosen
                idx, rgb = assign_engine32(
                    target, original_logical, game, chosen
                )
                result = source_quality(
                    original_logical, rgb, idx, chosen
                )
                chroma_mask = result.pop("source_chroma_excess_mask")
                hue_mask = result.pop("source_hue_mismatch_mask")
                if not np.array_equal(rgb, game[idx]):
                    raise AssertionError("BLOCKED_P3B_NOT_EXACT_ENGINE_RGB")
                prefix = selected_key
                Image.fromarray(rgb).save(
                    output / (prefix + "_ENGINE32_RGB.png"))
                Image.fromarray(idx).save(
                    output / (prefix + "_ENGINE128_INDICES_SELECTED32.png"))
                Image.fromarray(chroma_mask.astype(np.uint8) * 255).save(
                    output / (prefix + "_SOURCE_CHROMA_EXCESS_MASK.png"))
                Image.fromarray(hue_mask.astype(np.uint8) * 255).save(
                    output / (prefix + "_SOURCE_HUE_MISMATCH_MASK.png"))
                selected_entries = [
                    provenance["swatch_RGB"][int(i)] for i in chosen
                ]
                (output / (prefix + "_SELECTED_GAME32_SWATCH_LEDGER.json")).write_text(
                    json.dumps({
                        "method": method,
                        "palette32_engine_indices": chosen.tolist(),
                        "selection_ledger": ledger,
                        "selection": sel_info,
                        "game32_swatches": selected_entries,
                    }, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf8",
                )
                all_results[key]["palette32_methods"][method] = {
                    "selected_engine_indices": chosen.tolist(),
                    "source_palette_selection": sel_info,
                    **result,
                }
                variants.append((method, rgb))
            variants.append(("128 FULL DIAG", full128_rgb))
            review_panel(
                variants, output / ("REVIEW_" + key + "_MAIN_FIVE_WAY.png"))
            for roi_name in ("female_face_eyes", "male_face_eyes", "hands"):
                review_panel(
                    variants, output / ("REVIEW_" + key + "_ROI_" + roi_name + ".png"),
                    roi=roi_logical(roi_name), scale=6)
    swatch_sheet(game, selections, output / "ENGINE_128_ALL_RGB_AND_SELECTED32.png")
    (output / "ENGINE_128_SOURCE_FROM_JS.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n",
        encoding="utf8",
    )
    (output / "README_REVIEW_RU.txt").write_text(
        "B1-R-P3B: выбрали 32 из 128 RGB, найденных непосредственно в движке.\n"
        "Для каждого из 4 ранее одобренных RGB вариантов два выбора:\n"
        "A_BALANCED — баланс покрытия цвета, лица и детали;\n"
        "B_FACE_DETAIL — повышенный приоритет лиц и рук.\n"
        "REVIEW_C_096_D_BORDER_MAIN_FIVE_WAY.png и 3 аналогичных:\n"
        "ORIGINAL | принятый исходный P2D | A_BALANCED | B_FACE_DETAIL |\n"
        "128 FULL DIAG (ТОЛЬКО диагностическое изображение, не 32 цвета).\n"
        "REVIEW_*_ROI_* — лица, руки, сравнение увеличено.\n"
        "ENGINE_128_ALL_RGB_AND_SELECTED32.png — статическая палитра движка.\n"
        "Все выводы из статического кода. Доступность доп. цветов в запущенной\n"
        "игре не подтверждена; game32 и native Egret/CHALK не принимались.\n"
        "Используйте report.json: численные gates каждого кандидата.\n",
        encoding="utf8",
    )
    member_hashes = {
        p.name: digest(p.read_bytes()) for p in sorted(output.iterdir())
        if p.is_file()
    }
    report = {
        "experiment": EXPERIMENT,
        "source_original_sha256": SOURCE_SHA,
        "actual_static_engine_palette": provenance,
        "original_source_200x320_only": True,
        "G32_legacy_mapping_input_used": False,
        "V44_legacy_contours_input_used": False,
        "M1_legacy_masks_input_used": False,
        "frozen_P2B_P2C_P2D_P3_artifacts_as_input": False,
        "old_screen32_used_as_selection_seed_or_target": False,
        "source_P2D_manual_acceptance": "C096_C192_X_BOTH_GUARDS_ACCEPTED",
        "source_original_region_count": len(region_ledger),
        "source_K_DETAIL_pixels_full": int(ink_mask.sum()),
        "source_K_DETAIL_info": detail_summary,
        "source_guard_full_counts": {
            k: int(v.sum()) for k, v in guards.items()
        },
        "selection_methods": METHOD_WEIGHTS,
        "all_candidate_results": all_results,
        "source_game32_visual_acceptance": "PENDING",
        "engine128_gameplay_runtime_access": "UNKNOWN_E4_NOT_RUN",
        "actual_native_Egret_round_brush": "NOT_RUN",
        "actual_game_CHALK_bound_to_run": None,
        "independent_E5": "NOT_RUN",
        "production_promotion": False,
        "github_sha": os.getenv("GITHUB_SHA"),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "file_sha256": member_hashes,
        "versions": {
            "python": platform.python_version(), "numpy": np.__version__,
            "scipy": scipy.__version__, "skimage": skimage.__version__,
            "OpenCV": cv2.__version__, "Pillow": Image.__version__,
        },
    }
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf8",
    )
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--engine-js", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    report = run(args.source, args.engine_js, args.output)
    for source_key, result in report["all_candidate_results"].items():
        for method, r in result["palette32_methods"].items():
            print("P3B_RESULT", source_key, method, r["status"],
                  "colors_used", len(r["engine_color_indices_used"]),
                  "meanDE", round(r["original_deltaE00"]["mean_deltaE00"], 4),
                  "p95", round(r["original_deltaE00"]["p95_deltaE00"], 4),
                  "male_face", round(r["original_deltaE00"]["male_face_eyes_mean_deltaE00"], 4),
                  "chroma_excess", r["source_chroma_excess_plus12"],
                  "hue_mismatch", r["source_hue_mismatch_chroma12_hue45"],
                  "failed", [n for n, passed in r["gates"].items() if not passed])
    print("NATIVE_EGRET_PALETTE_ACCESS_E4_E5_EXACT_CHALK_NOT_RUN")

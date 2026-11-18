#!/usr/bin/env python3
"""ENGINE-001 P3D: mask-only original RGB structural edge protection ablation.

M0 generated from original via current-run P3C/P3B, never frozen ZIP.
Reuses P3C T_LOCAL exactly; only original-derived protection differs.
Offline indexed color evidence, not native game Egret or exact CHALK.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from skimage import color

import run_engine001_b1r_p3c_source_coherence as p3c
import run_engine001_b1r_p3b_engine128_adaptive32 as p3b
from run_engine001_b1r_p1_fullrgb_edge_aware import check_source, logical_rgb
from run_engine001_b1r_p2_joint_region_outline import digest

EXPERIMENT = "ENGINE001_B1R_P3D_SOURCE_EDGE_MASK_ABLATION_V1"
MASKS = ("E_SOBEL90", "F_SOBEL90_LAB12")
LAB_EDGE_THRESHOLD = 12.0


def source_edge_masks(original_logical: np.ndarray):
    if (original_logical.shape != p3b.LOGICAL_SHAPE or
            original_logical.dtype != np.uint8):
        raise ValueError("BLOCKED_P3D_ORIGINAL_LOGICAL_SHAPE_OR_DTYPE")
    high_sobel = p3b.original_edge_map(original_logical)
    roi = np.zeros((240, 150), dtype=bool)
    for name in ("female_face_eyes", "male_face_eyes", "hands"):
        x0, y0, x1, y1 = p3b.roi_logical(name)
        roi[y0:y1, x0:x1] = True
    source_bright = np.min(original_logical, axis=2) >= 245
    e_mask = high_sobel | roi | source_bright
    lab = p3b.lab_rgb(original_logical)
    xdiff = color.deltaE_ciede2000(lab[:, 1:, :], lab[:, :-1, :])
    ydiff = color.deltaE_ciede2000(lab[1:, :, :], lab[:-1, :, :])
    high_lab = np.zeros((240, 150), dtype=bool)
    xhigh = xdiff >= LAB_EDGE_THRESHOLD
    yhigh = ydiff >= LAB_EDGE_THRESHOLD
    high_lab[:, 1:] |= xhigh
    high_lab[:, :-1] |= xhigh
    high_lab[1:, :] |= yhigh
    high_lab[:-1, :] |= yhigh
    f_mask = e_mask | high_lab
    if (not np.array_equal(f_mask | e_mask, f_mask) or
            not np.array_equal(e_mask[roi], np.ones(int(roi.sum()), bool)) or
            not np.array_equal(f_mask[source_bright],
                               np.ones(int(source_bright.sum()), bool))):
        raise AssertionError("BLOCKED_P3D_SOURCE_PROTECTION_INVALID")
    counts = {
        "source_original_sobel90_pixels": int(high_sobel.sum()),
        "fixed_face_eye_hand_roi_pixels": int(roi.sum()),
        "original_bright_white_pixels": int(source_bright.sum()),
        "source_original_CIEDE00_4neighbor_ge12_pixels": int(high_lab.sum()),
        "E_SOBEL90_protected_pixels": int(e_mask.sum()),
        "F_SOBEL90_LAB12_protected_pixels": int(f_mask.sum()),
        "E_is_subset_of_F": True,
    }
    return {MASKS[0]: e_mask, MASKS[1]: f_mask}, counts


def run(source: Path, engine_js: Path, output: Path):
    if output.exists():
        raise ValueError("BLOCKED_P3D_OUTPUT_EXISTS")
    original_full = check_source(source)
    original = logical_rgb(original_full)
    game128, _ = p3b.read_engine_palette(engine_js)
    protection, mask_counts = source_edge_masks(original)
    output.mkdir(parents=True)
    Image.fromarray(original).save(output / "00_ORIGINAL_RGB_LOGICAL.png")
    for k, mask in protection.items():
        Image.fromarray(mask.astype(np.uint8) * 255).save(
            output / (k + "_ORIGINAL_RGB_PROTECTION.png"))
    all_results = {}
    with tempfile.TemporaryDirectory(prefix="engine001-p3d-p3c-current-run-") as tmp:
        interim = Path(tmp) / "p3c_original_only"
        parent = p3c.run(source, engine_js, interim)
        if (parent["experiment"] != p3c.EXPERIMENT or
                parent["original_sha256"] != p3b.SOURCE_SHA or
                parent["engine_blob_sha1"] != p3b.ENGINE_GIT_BLOB_SHA1 or
                parent["P3B_recomputed_original_only"] is not True or
                any(not record["P3B_A_B_exact_pixel_identity"]
                    for record in parent["source_results"].values())):
            raise ValueError("BLOCKED_P3D_FRESH_P3B_BASELINE_DRIFT")
        for key in ("C_096_D_BORDER", "C_096_D_COMPONENT24",
                    "C_192_D_BORDER", "C_192_D_COMPONENT24"):
            def load(filename: str):
                return np.asarray(Image.open(interim / filename), dtype=np.uint8).copy()
            index = load(key + "_M0_ENGINE_INDICES.png")
            source_rgb = load(key + "_P2D_ACCEPTED_SOURCE_NEAREST_RGB.png")
            palette = np.asarray(
                parent["source_results"][key]["selected_engine_indices"],
                dtype=np.int16)
            if (index.shape != (240, 150) or
                    source_rgb.shape != p3b.LOGICAL_SHAPE or
                    len(set(palette.tolist())) != 32 or
                    not np.array_equal(load(key + "_M0_RGB.png"), game128[index]) or
                    not all(parent["source_results"][key]["M0_baseline"]["gates"].values())):
                raise ValueError("BLOCKED_P3D_SOURCE_PARENT_M0_INVALID")
            before = p3c._metrics(index, original, game128, palette)
            if (before["connected_color_islands"]["tiny_components_size1_to3"] !=
                    parent["source_results"][key]["M0_baseline"]
                    ["connected_color_islands"]["tiny_components_size1_to3"]):
                raise ValueError("BLOCKED_P3D_P3C_M0_LEDGER_DRIFT")
            Image.fromarray(source_rgb).save(
                output / (key + "_ACCEPTED_P2D_NEAREST_RGB.png"))
            Image.fromarray(game128[index]).save(
                output / (key + "_P3B_A_EQ_B_M0_RGB.png"))
            Image.fromarray(index).save(output / (key + "_P3B_M0_INDICES.png"))
            variants = [("ORIGINAL", original),
                        ("ACCEPTED SOURCE", source_rgb),
                        ("P3B M0 A=B", game128[index])]
            all_results[key] = {
                "P3B_A_B_exact": True,
                "selected_engine_indices": palette.tolist(),
                "source_rgb_baseline": before,
                "methods": {},
            }
            for name in MASKS:
                mask = protection[name]
                result_index, edits = p3c.coherence_pass(
                    index, original, game128, palette, mask, "T_LOCAL")
                scored = p3c._metrics(result_index, original, game128, palette)
                gates, status = p3c._gates(
                    before, scored, index, result_index, original, mask)
                if np.any(result_index[mask] != index[mask]):
                    raise AssertionError("BLOCKED_P3D_CHANGED_TRUE_SOURCE_EDGE")
                tiny_a = before["connected_color_islands"]["tiny_components_size1_to3"]
                tiny_b = scored["connected_color_islands"]["tiny_components_size1_to3"]
                all_results[key]["methods"][name] = {
                    "status": status,
                    "gates": gates,
                    "tiny_before": tiny_a,
                    "tiny_after": tiny_b,
                    "tiny_eliminated": tiny_a - tiny_b,
                    "tiny_reduction_fraction": (tiny_a - tiny_b) / tiny_a,
                    "metrics": scored,
                    "changes": edits,
                    "original_source_protected_pixels": int(mask.sum()),
                }
                prefix = key + "_" + name
                Image.fromarray(result_index).save(
                    output / (prefix + "_ENGINE_INDICES.png"))
                Image.fromarray(game128[result_index]).save(
                    output / (prefix + "_RGB.png"))
                Image.fromarray(
                    (result_index != index).astype(np.uint8) * 255
                ).save(output / (prefix + "_CHANGED_LOGICAL_MASK.png"))
                variants.append((name, game128[result_index]))
            p3b.review_panel(variants, output / ("REVIEW_" + key + "_FIVE_WAY.png"))
            for roi in ("female_face_eyes", "male_face_eyes", "hands"):
                p3b.review_panel(
                    variants, output / ("REVIEW_" + key + "_ROI_" + roi + ".png"),
                    roi=p3b.roi_logical(roi), scale=6)
    (output / "README_REVIEW_RU.txt").write_text(
        "B1-R-P3D: сравните ORIGINAL | принятый RGB P2D | "
        "P3B A=B M0 | E_SOBEL90 | F_SOBEL90_LAB12.\n"
        "Это только математический тест без рисования настоящей игровой кистью.\n"
        "В текущем опыте изменены только маски охраны оригинального RGB;\n"
        "логика T_LOCAL и все gate пороги P3C сохранены без изменений.\n"
        "REVIEW_*_FIVE_WAY.png — полный оригинал и три цветовых варианта,\n"
        "ROI_* — увеличения глаз, лиц, рук; отдельные source-маски и changed.\n"
        "Даже численный PASS потребует отдельного визуального решения пользователя.\n",
        encoding="utf8",
    )
    member_hashes = {
        p.name: digest(p.read_bytes()) for p in sorted(output.iterdir())
        if p.is_file()
    }
    report = {
        "experiment": EXPERIMENT,
        "original_source_sha256": p3b.SOURCE_SHA,
        "engine_git_blob_sha1": p3b.ENGINE_GIT_BLOB_SHA1,
        "engine_palette_static_colors": 128,
        "parent_p3c_experiment": p3c.EXPERIMENT,
        "parent_p3c_T_LOCAL_algorithm_changed": False,
        "P3B_M0_A_B_user_visual": "BOTH_ACCEPTED_OFFLINE_ONLY_DEC037",
        "P3B_original_recomputed_in_current_run": True,
        "read_frozen_ZIP_as_source": False,
        "legacy_G32_V44_M1_used_as_source": False,
        "one_variable": "source_original_protection_mask_only",
        "method_settings": {
            name: {"original_mask": name,
                   "merge_solver": "P3C T_LOCAL unchanged",
                   "unchanged_max_changed_pixels": p3c.MAX_CHANGED_PIXELS}
            for name in MASKS
        },
        "source_mask_counts": mask_counts,
        "all_results": all_results,
        "new_user_visual_approval": "PENDING",
        "engine128_runtime_access_E4": "UNKNOWN",
        "native_game_Egret": "NOT_RUN",
        "independent_game_validation_E5": "NOT_RUN",
        "exact_run_bound_CHALK": None,
        "production_promotion": False,
        "github_sha": os.getenv("GITHUB_SHA"),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "file_sha256": member_hashes,
    }
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf8")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--engine-js", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    report = run(args.source, args.engine_js, args.output)
    for k, r in report["all_results"].items():
        for method, v in r["methods"].items():
            print("P3D", k, method, v["status"], "changed",
                  v["changes"]["changed_pixels"], "islands",
                  v["tiny_before"], "to", v["tiny_after"],
                  "failed", [g for g, ok in v["gates"].items() if not ok])
    print("EGRET_E4_CHALK_NOT_RUN_ENGINE128_RUNTIME_ACCESS_UNKNOWN")

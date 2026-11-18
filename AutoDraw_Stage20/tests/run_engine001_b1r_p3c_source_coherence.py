#!/usr/bin/env python3
"""ENGINE-001 B1-R-P3C: source-protected tiny-island cleanup, offline only.

Recompute P3B from original each run. No frozen P3B outputs or legacy G32/V44.
This study measures 4-connected game-palette pixels, NOT native brush/CHALK.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from skimage import color

import run_engine001_b1r_p3b_engine128_adaptive32 as p3b
from run_engine001_b1r_p1_fullrgb_edge_aware import (
    check_source, full_features, logical_protection, logical_rgb,
)
from run_engine001_b1r_p2_joint_region_outline import digest

EXPERIMENT = "ENGINE001_B1R_P3C_SOURCE_COHERENCE_V1"
METHODS = {
    "S_STRICT": {"max_mean_loss_increase": 0.0,
                 "max_worst_loss_increase": 1.0,
                 "max_border_source_de": 10.0, "expand_protection": True},
    "T_LOCAL": {"max_mean_loss_increase": 1.0,
                "max_worst_loss_increase": 2.0,
                "max_border_source_de": 14.0, "expand_protection": False},
}
MAX_CHANGED_PIXELS = 360
MAX_COMPONENT_AREA = 3
MIN_TINY_REDUCTION = 0.05
NEIGHBORS4 = ((-1, 0), (0, -1), (0, 1), (1, 0))


def original_protection(full: np.ndarray, original_logical: np.ndarray) -> np.ndarray:
    """Source-only detail+Sobel+fixed ROIs+white lock."""
    if original_logical.shape != p3b.LOGICAL_SHAPE:
        raise ValueError("BLOCKED_P3C_ORIGINAL_LOGICAL_SHAPE")
    protected = logical_protection(full_features(full)["protected"])
    protected |= p3b.original_edge_map(original_logical)
    for region in ("female_face_eyes", "male_face_eyes", "hands"):
        x0, y0, x1, y1 = p3b.roi_logical(region)
        protected[y0:y1, x0:x1] = True
    protected |= np.min(original_logical, axis=2) >= 245
    if not protected.any() or protected.shape != (240, 150):
        raise ValueError("BLOCKED_P3C_PROTECTION_EMPTY")
    return protected


def _component_candidates(index: np.ndarray):
    """Tiny four-connected M0 components in stable global row-major order."""
    collected = []
    for engine_index in np.unique(index):
        mask = np.asarray(index == engine_index, np.uint8)
        n, labels, stats, _ = cv2.connectedComponentsWithStats(
            mask, connectivity=4
        )
        for label in range(1, n):
            left, top, width, height, size = (int(v) for v in stats[label])
            if not 1 <= size <= MAX_COMPONENT_AREA:
                continue
            sub_y, sub_x = np.where(
                labels[top:top + height, left:left + width] == label
            )
            pixels = sorted(zip((sub_y + top).tolist(), (sub_x + left).tolist()))
            if len(pixels) != size:
                raise AssertionError("BLOCKED_P3C_COMPONENT_AREA_DRIFT")
            collected.append((pixels[0], int(engine_index), pixels))
    collected.sort(key=lambda x: (x[0][0], x[0][1], x[1]))
    return collected


def _chroma_hue_bad(orig_lab: np.ndarray, swatch_lab: np.ndarray):
    src_c = np.linalg.norm(orig_lab[..., 1:], axis=-1)
    out_c = np.linalg.norm(swatch_lab[1:])
    chroma = out_c > src_c + 12.0
    h0 = np.degrees(np.arctan2(orig_lab[..., 2], orig_lab[..., 1]))
    h1 = np.degrees(np.arctan2(swatch_lab[2], swatch_lab[1]))
    diff = np.abs(((h0 - h1 + 180.0) % 360.0) - 180.0)
    hue = (src_c >= 12.0) & (out_c >= 12.0) & (diff > 45.0)
    return chroma, hue


def coherence_pass(index: np.ndarray, original: np.ndarray,
                   game128: np.ndarray, selected: np.ndarray,
                   protected_core: np.ndarray, method: str):
    """Single original-grounded snapshot pass; never remap selected palette."""
    if (method not in METHODS or index.shape != (240, 150) or
            index.dtype != np.uint8 or original.shape != p3b.LOGICAL_SHAPE or
            original.dtype != np.uint8 or game128.shape != (128, 3) or
            game128.dtype != np.uint8 or selected.shape != (32,) or
            selected.dtype != np.int16 or
            len(set(selected.tolist())) != 32 or
            p3b.ENGINE_WHITE_INDEX not in selected or
            protected_core.shape != index.shape or
            protected_core.dtype != np.bool_ or
            not set(np.unique(index).tolist()).issubset(set(selected.tolist()))):
        raise ValueError("BLOCKED_P3C_INPUT_OR_PALETTE")
    if np.any(index[np.min(original, axis=2) >= 245] != p3b.ENGINE_WHITE_INDEX):
        raise ValueError("BLOCKED_P3C_BASELINE_WHITE_LOCK_DRIFT")
    conf = METHODS[method]
    protect = protected_core.copy()
    if conf["expand_protection"]:
        kernel = np.asarray([[0, 1, 0], [1, 1, 1], [0, 1, 0]], np.uint8)
        protect = cv2.dilate(protect.astype(np.uint8), kernel) > 0
    output = index.copy()
    changed_mask = np.zeros(index.shape, dtype=bool)
    reasons = Counter()
    accepted = []
    rejected_examples = []
    orig_lab = p3b.lab_rgb(original)
    selected_unique = np.unique(selected)
    swatch_lab = p3b.lab_rgb(game128.reshape(128, 1, 3)).reshape(128, 3)
    # Vectorized source distances reused by each tiny component.
    source_losses = {
        int(k): color.deltaE_ciede2000(orig_lab, swatch_lab[int(k)])
        for k in selected_unique
    }
    all_components = _component_candidates(index)
    for _, own, pixels in all_components:
        ys = np.array([p[0] for p in pixels], dtype=np.intp)
        xs = np.array([p[1] for p in pixels], dtype=np.intp)
        if protect[ys, xs].any():
            reasons["protected_source"] += 1
            continue
        if changed_mask[ys, xs].any():
            reasons["overlapping_component"] += 1
            continue
        contacts = defaultdict(list)
        for y, x in pixels:
            for dy, dx in NEIGHBORS4:
                yy, xx = y + dy, x + dx
                if 0 <= yy < 240 and 0 <= xx < 150:
                    donor = int(index[yy, xx])  # immutable M0 map
                    if donor != own and donor in source_losses:
                        contacts[donor].append((y, x, yy, xx))
        if not contacts:
            reasons["no_4_neighbor_donor"] += 1
            continue
        chosen = []
        for donor, edges in contacts.items():
            if any(changed_mask[e[2], e[3]] for e in edges):
                continue
            a = np.asarray([e[:2] for e in edges], dtype=np.intp)
            b = np.asarray([e[2:] for e in edges], dtype=np.intp)
            border_de = color.deltaE_ciede2000(
                orig_lab[a[:, 0], a[:, 1]],
                orig_lab[b[:, 0], b[:, 1]]
            )
            if float(np.mean(border_de)) > conf["max_border_source_de"]:
                continue
            loss_change = (source_losses[donor][ys, xs] -
                           source_losses[own][ys, xs])
            if (float(np.mean(loss_change)) >
                    conf["max_mean_loss_increase"] + 1e-9 or
                    float(np.max(loss_change)) >
                    conf["max_worst_loss_increase"] + 1e-9):
                continue
            src = orig_lab[ys, xs]
            old_bad_c, old_bad_h = _chroma_hue_bad(src, swatch_lab[own])
            new_bad_c, new_bad_h = _chroma_hue_bad(src, swatch_lab[donor])
            if np.any(new_bad_c & ~old_bad_c) or np.any(new_bad_h & ~old_bad_h):
                continue
            rank = (
                float(np.mean(source_losses[donor][ys, xs])),
                -len(edges), donor,
            )
            chosen.append((rank, donor, float(np.mean(loss_change)),
                           float(np.mean(border_de))))
        if not chosen:
            reasons["no_source_supported_donor"] += 1
            if len(rejected_examples) < 12:
                rejected_examples.append({"anchor_yx": list(pixels[0]),
                                          "engine_index": own,
                                          "reason": "no_source_supported_donor"})
            continue
        if int(np.count_nonzero(changed_mask)) + len(pixels) > MAX_CHANGED_PIXELS:
            reasons["changed_pixel_cap"] += 1
            continue
        _, donor, delta, border = min(chosen, key=lambda v: v[0])
        output[ys, xs] = np.uint8(donor)
        changed_mask[ys, xs] = True
        accepted.append({
            "component_anchor_yx": list(pixels[0]),
            "pixels_yx": [list(p) for p in pixels],
            "before_engine_index": own, "after_engine_index": donor,
            "mean_original_de_change": delta,
            "mean_original_border_de": border,
        })
    if (np.any(output[protect] != index[protect]) or
            int(changed_mask.sum()) > MAX_CHANGED_PIXELS or
            not np.array_equal(changed_mask, output != index) or
            not set(np.unique(output).tolist()).issubset(set(selected.tolist())) or
            np.any(output[np.min(original, axis=2) >= 245] !=
                   p3b.ENGINE_WHITE_INDEX)):
        raise AssertionError("BLOCKED_P3C_PROTECTION_OR_ENGINE_GUARD")
    return output, {
        "method": method, "params": conf,
        "candidate_components": len(all_components),
        "accepted_components": len(accepted),
        "changed_pixels": int(changed_mask.sum()),
        "rejected_counts": dict(reasons),
        "accepted_component_ledger": accepted,
        "rejected_examples": rejected_examples,
        "protected_logical_pixels": int(protect.sum()),
        "all_changes_complete_components_from_M0": True,
    }


def _metrics(index, original, palette, chosen):
    data = p3b.source_quality(original, palette[index], index, chosen)
    data.pop("source_chroma_excess_mask")
    data.pop("source_hue_mismatch_mask")
    return data


def _gates(baseline: dict, candidate: dict, original_index: np.ndarray,
           updated_index: np.ndarray, original: np.ndarray, protected_core: np.ndarray):
    before = baseline["original_deltaE00"]
    after = candidate["original_deltaE00"]
    tiny_old = baseline["connected_color_islands"]["tiny_components_size1_to3"]
    tiny_new = candidate["connected_color_islands"]["tiny_components_size1_to3"]
    changed = updated_index != original_index
    gates = {
        "all_original_P3B_source_gates": all(candidate["gates"].values()),
        "mean_de_at_most_baseline_plus0p15":
            after["mean_deltaE00"] <= before["mean_deltaE00"] + .15,
        "p95_de_at_most_baseline_plus0p40":
            after["p95_deltaE00"] <= before["p95_deltaE00"] + .40,
        "female_face_at_most_baseline_plus0p01":
            after["female_face_eyes_mean_deltaE00"] <=
            before["female_face_eyes_mean_deltaE00"] + .01,
        "male_face_at_most_baseline_plus0p01":
            after["male_face_eyes_mean_deltaE00"] <=
            before["male_face_eyes_mean_deltaE00"] + .01,
        "hands_at_most_baseline_plus0p01":
            after["hands_mean_deltaE00"] <= before["hands_mean_deltaE00"] + .01,
        "original_edge_recall_at_least_baseline_minus0p01":
            candidate["original_sobel90_1px_recall"] >=
            baseline["original_sobel90_1px_recall"] - .01,
        "chroma_excess_at_most_baseline_plus30":
            candidate["source_chroma_excess_plus12"] <=
            baseline["source_chroma_excess_plus12"] + 30,
        "hue_mismatch_at_most_baseline_plus30":
            candidate["source_hue_mismatch_chroma12_hue45"] <=
            baseline["source_hue_mismatch_chroma12_hue45"] + 30,
        "all_original_protected_pixels_identical":
            not changed[protected_core].any(),
        "original_bright_pixels_identical":
            not changed[np.min(original, axis=2) >= 245].any(),
        "changed_pixels_at_most360": int(changed.sum()) <= MAX_CHANGED_PIXELS,
        "tiny_components_reduce_at_least5percent":
            tiny_new <= tiny_old * (1.0 - MIN_TINY_REDUCTION),
        "at_least20_tiny_components_eliminated": tiny_old - tiny_new >= 20,
    }
    fidelity_keys = list(gates)[:-2]
    status = ("SOURCE_GATE_FAIL" if not all(gates[k] for k in fidelity_keys)
              else "NO_MATERIAL_ISLAND_GAIN" if not
              (gates["tiny_components_reduce_at_least5percent"] and
               gates["at_least20_tiny_components_eliminated"])
              else "SOURCE_SCREEN_PASS_VISUAL_PENDING_RUNTIME_ACCESS_UNVERIFIED")
    return {k: bool(v) for k, v in gates.items()}, status


def run(source: Path, engine_js: Path, output: Path):
    if output.exists():
        raise ValueError("BLOCKED_P3C_OUTPUT_EXISTS")
    original = check_source(source)
    original_logical = logical_rgb(original)
    game128, palette_prov = p3b.read_engine_palette(engine_js)
    protection = original_protection(original, original_logical)
    output.mkdir(parents=True)
    Image.fromarray(original_logical).save(output / "00_ORIGINAL_LOGICAL_RGB.png")
    Image.fromarray(protection.astype(np.uint8) * 255).save(
        output / "01_ORIGINAL_PROTECTED_LOGICAL.png")
    source_results = {}
    with tempfile.TemporaryDirectory(prefix="engine001-p3c-p3b-fresh-") as tmp:
        p3b_directory = Path(tmp) / "fresh_p3b_original_only"
        old_report = p3b.run(source, engine_js, p3b_directory)
        if (old_report["experiment"] != p3b.EXPERIMENT or
                old_report["source_original_sha256"] != p3b.SOURCE_SHA or
                old_report["source_original_region_count"] != 682 or
                old_report["source_K_DETAIL_pixels_full"] != 14904 or
                old_report["source_guard_full_counts"] !=
                {"D_BORDER": 56, "D_COMPONENT24": 243}):
            raise ValueError("BLOCKED_P3C_P3B_RECOMPUTATION_DRIFT")
        for key in ("C_096_D_BORDER", "C_096_D_COMPONENT24",
                    "C_192_D_BORDER", "C_192_D_COMPONENT24"):
            def load(filename: str):
                return np.array(Image.open(p3b_directory / filename), dtype=np.uint8)
            source_rgb = load(key + "_P2D_ACCEPTED_SOURCE_NEAREST_RGB.png")
            names = [key + "_" + m for m in p3b.METHODS]
            a = load(names[0] + "_ENGINE128_INDICES_SELECTED32.png")
            b = load(names[1] + "_ENGINE128_INDICES_SELECTED32.png")
            r_a = old_report["all_candidate_results"][key]["palette32_methods"]["A_BALANCED"]
            r_b = old_report["all_candidate_results"][key]["palette32_methods"]["B_FACE_DETAIL"]
            selected = np.asarray(r_a["selected_engine_indices"], dtype=np.int16)
            if (source_rgb.shape != p3b.LOGICAL_SHAPE or
                    a.shape != (240, 150) or
                    not np.array_equal(a, b) or
                    set(r_a["selected_engine_indices"]) !=
                    set(r_b["selected_engine_indices"]) or
                    not np.array_equal(game128[a], game128[b]) or
                    not all(r_a["gates"].values()) or
                    not all(r_b["gates"].values())):
                raise ValueError("BLOCKED_P3C_P3B_A_B_BASELINE_NOT_IDENTICAL_PASS")
            shutil.copyfile(
                p3b_directory / (key + "_P2D_ACCEPTED_SOURCE_NEAREST_RGB.png"),
                output / (key + "_P2D_ACCEPTED_SOURCE_NEAREST_RGB.png"))
            Image.fromarray(a).save(output / (key + "_M0_ENGINE_INDICES.png"))
            Image.fromarray(game128[a]).save(output / (key + "_M0_RGB.png"))
            control = _metrics(a, original_logical, game128, selected)
            source_results[key] = {
                "P3B_A_B_exact_pixel_identity": True,
                "selected_engine_indices": selected.tolist(),
                "source_reference_rgb_count_full":
                    old_report["all_candidate_results"][key]["source_full_RGB_count"],
                "M0_baseline": control,
                "candidate_methods": {},
            }
            comparisons = [("ORIGINAL", original_logical),
                           ("ACCEPTED P2D", source_rgb),
                           ("P3B M0 A=B", game128[a])]
            for method in METHODS:
                index, ledger = coherence_pass(
                    a, original_logical, game128, selected, protection, method)
                scored = _metrics(index, original_logical, game128, selected)
                gates, status = _gates(
                    control, scored, a, index, original_logical, protection)
                tiny_0 = control["connected_color_islands"]["tiny_components_size1_to3"]
                tiny_1 = scored["connected_color_islands"]["tiny_components_size1_to3"]
                item = {
                    "status": status,
                    "gates": gates,
                    "tiny_components_before": tiny_0,
                    "tiny_components_after": tiny_1,
                    "tiny_components_eliminated": tiny_0 - tiny_1,
                    "tiny_reduction_fraction": (tiny_0 - tiny_1) / tiny_0,
                    "source_metrics": scored,
                    "changes": ledger,
                }
                source_results[key]["candidate_methods"][method] = item
                prefix = key + "_" + method
                Image.fromarray(index).save(output / (prefix + "_ENGINE_INDICES.png"))
                Image.fromarray(game128[index]).save(output / (prefix + "_RGB.png"))
                Image.fromarray((index != a).astype(np.uint8) * 255).save(
                    output / (prefix + "_CHANGED_LOGICAL_MASK.png"))
                comparisons.append((method, game128[index]))
            p3b.review_panel(comparisons,
                             output / ("REVIEW_" + key + "_FIVE_WAY.png"))
            for roi in ("female_face_eyes", "male_face_eyes", "hands"):
                p3b.review_panel(
                    comparisons, output / ("REVIEW_" + key + "_" + roi + ".png"),
                    roi=p3b.roi_logical(roi), scale=6)
    (output / "README_REVIEW_RU.txt").write_text(
        "ENGINE-001 B1-R-P3C. ORIGINAL | P2D SOURCE | P3B A=B M0 | "
        "S_STRICT | T_LOCAL.\n"
        "Все картинки — только офлайн RGB, НЕ настоящие следы кисти.\n"
        "Посмотрите REVIEW_*_FIVE_WAY.png и увеличения лиц/рук.\n"
        "Маски *_CHANGED_LOGICAL_MASK.png показывают реально изменённые пиксели.\n"
        "Исходные P3B и пользовательское A/B принятие сохранены, "
        "новая численная проверка НЕ равна ручному принятию.\n"
        "Проверка возможности выбора 128 цветов в живой игре — UNKNOWN.\n",
        encoding="utf8")
    hashes = {p.name: digest(p.read_bytes()) for p in sorted(output.iterdir())
              if p.is_file()}
    report = {
        "experiment": EXPERIMENT,
        "original_sha256": p3b.SOURCE_SHA,
        "engine_blob_sha1": p3b.ENGINE_GIT_BLOB_SHA1,
        "engine_palette_colors": len(game128),
        "engine_palette_runtime_E4": "UNKNOWN",
        "P3B_A_B_user_visual_acceptance": "BOTH_ACCEPTED_OFFLINE_ONLY_DEC037",
        "P3B_recomputed_original_only": True,
        "legacy_G32_V44_M1_inputs": False,
        "frozen_P3B_images_or_artifacts_used_as_input": False,
        "P3B_base_experiment": p3b.EXPERIMENT,
        "source_original_protected_pixels": int(protection.sum()),
        "source_results": source_results,
        "methods": METHODS,
        "new_P3C_human_visual_acceptance": "PENDING",
        "game_Egret_native_round_brush": "NOT_RUN",
        "live_E4": "NOT_RUN",
        "independent_E5": "NOT_RUN",
        "exact_run_bound_CHALK": None,
        "production_promotion": False,
        "github_sha": os.getenv("GITHUB_SHA"),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "python": platform.python_version(),
        "file_sha256": hashes,
    }
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--engine-js", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.source, args.engine_js, args.output)
    for key, src in result["source_results"].items():
        for name, item in src["candidate_methods"].items():
            print("P3C", key, name, item["status"],
                  "changed", item["changes"]["changed_pixels"],
                  "tiny", item["tiny_components_before"],
                  "->", item["tiny_components_after"],
                  "failed", [k for k, v in item["gates"].items() if not v])
    print("ENGINE128_RUNTIME_UNKNOWN_EGRET_E4_E5_CHALK_NOT_RUN")

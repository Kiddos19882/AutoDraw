#!/usr/bin/env python3
"""ENGINE-001 NEURAL-S1: frozen G32 versus externally produced REAL neural masks.

SOURCE_ONLY. Never calls Egret/executor; no exact CHALK or native quality PASS.
Protocol: docs/ENGINE001_COLOR32_NEURAL_S1_REGION_SEGMENTATION_PROTOCOL_2026-11-17.md
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
from PIL import Image
from skimage import color

from run_engine001_palette32_region_study import (
    PALETTE_BLOB, SOURCE_SHA, ROI_WH, nearest32, palette_lab,
    read_palette, read_source, sha,
)
from run_engine001_color32_s2_edge_protection import strong_edges, protected_merge
from run_engine001_color32_p4c0_all_owner_feasibility import (
    G_PNG_SHA, _png_sha, git_blob_sha,
)

EXP = "ENGINE001_COLOR32_NEURAL_S1_REGION_MASKS"
BG = 30
MIN_MASK_PIXELS = 4
MAX_MASKS = 32
PARAMS = {"top_masks": MAX_MASKS, "min_mask_pixels": MIN_MASK_PIXELS,
          "threshold": "binary/no interpolation", "palette_metric": "CIEDE2000",
          "restores_original_G32_background": True}


def original_g32(src, palette):
    b = nearest32(src, palette)
    edges, threshold = strong_edges(src)
    g, _ = protected_merge(src, b, palette, edges)
    if _png_sha(g) != G_PNG_SHA:
        raise ValueError("BLOCKED_NEURAL_S1_FROZEN_G_DRIFT")
    return g, edges, float(threshold)


def _load_mask_archive(path: Path, manifest_path: Path):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest.get("experiment") != EXP or
            manifest.get("source_sha256") != SOURCE_SHA or
            manifest.get("mask_shape_hw") != [240, 150] or
            manifest.get("model") != "SAM2.1_HIERA_TINY" or
            manifest.get("parameters") != {
                "points_per_side": 8, "points_per_batch": 8,
                "crop_n_layers": 0, "pred_iou_thresh": 0.8,
                "stability_score_thresh": 0.95} or
            manifest.get("mask_archive_sha256") != sha(path) or
            not manifest.get("model_checkpoint_sha256") or
            not manifest.get("sam2_git_sha")):
        raise ValueError("BLOCKED_NEURAL_S1_MODEL_OR_ARCHIVE_IDENTITY")
    entries = manifest.get("masks", [])
    if type(entries) is not list or len(entries) > 1024:
        raise ValueError("BLOCKED_NEURAL_S1_MASK_COUNT")
    masks = []
    with np.load(path, allow_pickle=False) as blob:
        if set(blob.files) != {e.get("key") for e in entries}:
            raise ValueError("BLOCKED_NEURAL_S1_MASK_KEYS")
        for e in entries:
            a = blob[e["key"]]
            if (a.shape != (240, 150) or a.dtype != np.bool_ or
                    a.sum() != e.get("area") or
                    hashlib.sha256(a.tobytes()).hexdigest() != e.get("sha256")):
                raise ValueError("BLOCKED_NEURAL_S1_MASK_SHAPE_OR_HASH")
            iou = e.get("predicted_iou")
            stability = e.get("stability_score")
            if (not isinstance(iou, (float, int)) or
                    not isinstance(stability, (float, int)) or
                    not np.isfinite(iou) or not np.isfinite(stability) or
                    not 0 <= iou <= 1 or not 0 <= stability <= 1):
                raise ValueError("BLOCKED_NEURAL_S1_MASK_SCORE")
            if int(a.sum()) >= MIN_MASK_PIXELS:
                masks.append((float(iou), float(stability), int(a.sum()),
                              str(e["key"]), a.copy()))
    masks.sort(key=lambda x: (-x[0], -x[1], -x[2], x[3]))
    return masks[:MAX_MASKS], manifest


def apply_masks(rgb: np.ndarray, palette: np.ndarray, g: np.ndarray, masks,
                protected: np.ndarray | None = None) -> tuple[np.ndarray, dict]:
    if (rgb.shape != (240, 150, 3) or palette.shape != (32, 3) or
            g.shape != (240, 150) or g.dtype != np.uint8 or
            (protected is not None and
             (protected.shape != g.shape or protected.dtype != np.bool_))):
        raise ValueError("BLOCKED_NEURAL_S1_SOURCE_SHAPE")
    out = g.copy()
    owned = np.zeros(g.shape, bool)
    src_lab = color.rgb2lab(rgb / 255.)
    plab = palette_lab(palette)
    proposed = 0
    for iou, stability, area, key, mask in masks:
        if mask.shape != g.shape or mask.dtype != np.bool_:
            raise ValueError("BLOCKED_NEURAL_S1_MASK_SHAPE")
        candidate = mask & ~owned & (g != BG)
        if int(candidate.sum()) < MIN_MASK_PIXELS:
            continue
        # Deterministic original-RGB palette assignment, no invented colors.
        mean_lab = src_lab[candidate].mean(axis=0)
        dist = color.deltaE_ciede2000(mean_lab[None, :], plab)
        owner = int(np.argmin(dist))
        if owner == BG:
            # Dark/light masks corresponding to background are kept as G32.
            continue
        out[candidate] = owner
        owned[candidate] = True
        proposed += 1
    out[g == BG] = BG
    if protected is not None:
        out[protected] = g[protected]
    if np.any(out >= 32) or np.any(out[g == BG] != BG):
        raise AssertionError("NEURAL_S1_PALETTE_OR_BG_DRIFT")
    return out, {"accepted_masks": proposed,
                 "assigned_nonbackground_pixels": int(owned.sum()),
                 "restored_protected_pixels": int(protected.sum())
                 if protected is not None else 0}


def source_metrics(rgb, idx, palette, protected, g):
    if idx.shape != (240, 150) or idx.dtype != np.uint8:
        raise ValueError("BLOCKED_NEURAL_S1_INDEX_SHAPE")
    src_lab = color.rgb2lab(rgb / 255.)
    rendered = palette[idx]
    dst_lab = color.rgb2lab(rendered / 255.)
    delta = color.deltaE_ciede2000(src_lab, dst_lab)
    counts, singletons, tiny = 0, 0, 0
    per_owner = {}
    for k in sorted(int(x) for x in np.unique(idx) if int(x) != BG):
        own = (idx == k).astype(np.uint8)
        n, cc, stats, _ = cv2.connectedComponentsWithStats(own, 4)
        sizes = stats[1:, cv2.CC_STAT_AREA]
        per_owner[str(k)] = {"components4": n - 1,
                             "singletons": int(np.count_nonzero(sizes == 1)),
                             "components_le4": int(np.count_nonzero(sizes <= 4))}
        counts += n - 1
        singletons += int(np.count_nonzero(sizes == 1))
        tiny += int(np.count_nonzero(sizes <= 4))
    boundary = np.count_nonzero(idx[1:] != idx[:-1]) + np.count_nonzero(
        idx[:, 1:] != idx[:, :-1])
    return {
        "components4_non_background": int(counts),
        "singletons4_non_background": int(singletons),
        "components_le4_non_background": int(tiny),
        "palette_colors_used_including_bg": int(np.unique(idx).size),
        "source_deltaE00_mean": float(delta.mean()),
        "source_deltaE00_p95": float(np.percentile(delta, 95)),
        "rgb_mae": float(np.abs(rgb.astype(np.int16) -
                                rendered.astype(np.int16)).mean()),
        "four_neighbor_color_changes": int(boundary),
        "g32_protected_pixels_changed": int(np.count_nonzero(
            (idx != g) & protected)),
        "g32_background_pixels_changed": int(np.count_nonzero(
            (idx != g) & (g == BG))),
        "per_owner": per_owner,
    }


def source_gate(control, candidate, *, edge_protected):
    if control["components4_non_background"] <= 0:
        raise ValueError("BLOCKED_NEURAL_S1_BASELINE_COMPONENTS")
    return {
        "component_reduction_ge25pct":
            candidate["components4_non_background"] <=
            .75 * control["components4_non_background"],
        "palette_le32": candidate["palette_colors_used_including_bg"] <= 32,
        "deltaE00_growth_le1":
            candidate["source_deltaE00_mean"] <=
            control["source_deltaE00_mean"] + 1.0,
        "no_protected_edge_change":
            (not edge_protected or candidate["g32_protected_pixels_changed"] == 0),
    }


def run(source_path: Path, palette_path: Path, output: Path,
        masks_path: Path | None = None, manifest_path: Path | None = None):
    if output.exists():
        raise ValueError("BLOCKED_NEURAL_S1_NO_OVERWRITE")
    if git_blob_sha(palette_path) != PALETTE_BLOB:
        raise ValueError("BLOCKED_NEURAL_S1_PALETTE_DRIFT")
    _, rgb = read_source(source_path)
    palette = read_palette(palette_path)
    g, protected, edge_threshold = original_g32(rgb, palette)
    if (masks_path is None) != (manifest_path is None):
        raise ValueError("BLOCKED_NEURAL_S1_PARTIAL_MODEL_INPUT")
    variants = {"B0_G32": g}
    info = {}
    manifest = None
    if masks_path is not None:
        masks, manifest = _load_mask_archive(masks_path, manifest_path)
        if not masks:
            raise ValueError("BLOCKED_NEURAL_S1_NO_NEURAL_MASKS")
        variants["N1_SAM2"] , info["N1_SAM2"] = apply_masks(rgb, palette, g, masks)
        variants["N2_SAM2_EDGE"], info["N2_SAM2_EDGE"] = apply_masks(
            rgb, palette, g, masks, protected)
    output.mkdir(parents=True)
    m = {name: source_metrics(rgb, idx, palette, protected, g)
         for name, idx in variants.items()}
    for name, idx in variants.items():
        Image.fromarray(idx, "L").save(output / f"{name}-indices.png")
        Image.fromarray(palette[idx], "RGB").save(output / f"{name}-RGB.png")
    Image.fromarray(rgb, "RGB").save(output / "original-source-RGB.png")
    Image.fromarray(protected.astype(np.uint8) * 255, "L").save(
        output / "protected-edges.png")
    gates = {k: source_gate(m["B0_G32"], val, edge_protected=(k == "N2_SAM2_EDGE"))
             for k, val in m.items() if k != "B0_G32"}
    hashes = {p.name: sha(p) for p in output.iterdir() if p.is_file()}
    report = {
        "experiment": EXP,
        "status": ("BASELINE_ONLY_NO_NEURAL_INFERENCE" if manifest is None else
                   "SOURCE_CANDIDATES_VISUAL_PENDING"),
        "github_sha": os.environ.get("GITHUB_SHA"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "source_sha256": SOURCE_SHA,
        "palette_blob": PALETTE_BLOB,
        "g32_png_sha256": G_PNG_SHA,
        "protected_source_edge_threshold": edge_threshold,
        "parameters": PARAMS,
        "model_input_manifest": manifest,
        "variant_info": info,
        "source_only_metrics": m,
        "source_candidate_gates": gates,
        "any_source_candidate_meets_all_gates": any(all(v.values()) for v in gates.values()),
        "visual_recognizability": "PENDING",
        "actual_AniLines_mask": "NOT_RUN",
        "flatmagic_pretrained_inference": "BLOCKED_MODEL",
        "native_Egret_paint": "NOT_RUN",
        "original_V44B_410_LAST": "FROZEN_NOT_RENDERED",
        "game_E4": "NOT_RUN", "independent_E5": "NOT_RUN",
        "exact_CHALK": None,
        "production_accepted": False,
        "output_file_sha256": hashes,
        "versions": {"python": platform.python_version(),
                     "opencv": cv2.__version__, "numpy": np.__version__}
    }
    (output / "report.json").write_text(json.dumps(report, indent=2,
        ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, type=Path)
    p.add_argument("--palette", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--masks", type=Path)
    p.add_argument("--manifest", type=Path)
    a = p.parse_args()
    report = run(a.source, a.palette, a.output, a.masks, a.manifest)
    print(json.dumps({"status": report["status"],
                      "source_metrics": report["source_only_metrics"],
                      "source_gates": report["source_candidate_gates"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()

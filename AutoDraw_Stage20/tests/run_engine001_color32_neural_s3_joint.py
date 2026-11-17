#!/usr/bin/env python3
"""ENGINE-001 S3 joint color-region graph + original V44-B immutable contour guidance.

Not a learned color picker. Reuses authentic SAM2 S1 masks only for region proposals.
Source-only, not native Egret paint; never modifies or redraws V44-B strokes.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from skimage import color

from run_engine001_palette32_region_study import SOURCE_SHA, PALETTE_BLOB, read_source, read_palette, sha
from run_engine001_color32_neural_s2 import (
    BG, _read_original_archive, independent_regions, metrics,
)

EXP = "ENGINE001_COLOR32_NEURAL_S3_JOINT_COLOR_CONTOUR"
FROZEN_CONTOUR_ZIP_SHA = "43cb8e14a7e387b26772612ac06d1c7c6f176b8bd0c2d41e8945042fc80304a1"
FROZEN_CONTOUR_PNG_SHA = "0145975e4578bc86c1e4feb44d5ff93ecd486d576faf97626e1267a5c12b0275"
FROZEN_PLAN_SHA = "9db4dda0661ea529547e91a09dcae38b27043dad57383fb483b945f0de08496a"
FROZEN_REPORT_SHA = "c729a81eb1c84cc0778b1f316f1a0e039c447d83ec147002484bb6c4212ff428"
PARAMS = {"rgb_region_mean_deltaE00_to_allow_smoothing": 8.0,
          "edge_gradient_protect_deltaE00": 15.0,
          "pairwise_smoothing_per_contact": 2.0, "edge_contact_cap": 16,
          "pink_chroma_excess_allowance": 8.0,
          "pink_chroma_penalty": 0.4, "icm_sweeps": 3,
          "native_contour_alpha_cutoff": 24,
          "joint_boundary_contour_confidence_min": .25,
          "original_native_roi_x0": 155, "original_native_scale": 3}


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def read_immutable_contour(path: Path):
    if sha(path) != FROZEN_CONTOUR_ZIP_SHA:
        raise ValueError("BLOCKED_S3_CONTOUR_ZIP_SHA")
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("BLOCKED_S3_CONTOUR_ZIP_CRC")
        members = ("B/V44-B-color-100.png", "color-plans.json", "report.json")
        if any(p not in archive.namelist() for p in members):
            raise ValueError("BLOCKED_S3_MISSING_ORIGINAL_CONTOUR_MEMBERS")
        blob, plan, report = [archive.read(p) for p in members]
        if (digest(blob) != FROZEN_CONTOUR_PNG_SHA or
                digest(plan) != FROZEN_PLAN_SHA or
                digest(report) != FROZEN_REPORT_SHA):
            raise ValueError("BLOCKED_S3_CONTOUR_MEMBER_SHA")
    meta = json.loads(plan)
    b = meta["plans"]["B"]
    strokes = b["strokes"]
    tail = strokes[-410:]
    if (b.get("sequence") != ["paint", "detail"] or
            b.get("paint_strokes") != 1945 or b.get("detail_strokes") != 410 or
            len(strokes) != 2355 or
            any(t.get("layer") != "paint" for t in strokes[:-410]) or
            any(t.get("layer") != "detail" for t in tail) or
            sum(len(t["stroke"]["points"]) for t in tail) != 1792):
        raise ValueError("BLOCKED_S3_CONTOUR_GEOMETRY_OR_LAYER_DRIFT")
    for i, row in enumerate(tail):
        s = row["stroke"]
        if (s.get("strokeId") != f"detail-v18-B-{i}" or
                s.get("colorIndex") != 100 or s.get("width") != 1):
            raise ValueError("BLOCKED_S3_CONTOUR_IDENTITY_DRIFT")
    rgba = np.asarray(Image.open(io.BytesIO(blob)).convert("RGBA"), dtype=np.uint8)
    if rgba.shape != (720, 1380, 4):
        raise ValueError("BLOCKED_S3_CONTOUR_IMAGE_SHAPE")
    alpha = rgba[:, :, 3]
    outside = np.count_nonzero(alpha[:, :465] >= 24) + np.count_nonzero(alpha[:, 915:] >= 24)
    if outside != 0:
        raise ValueError("BLOCKED_S3_CONTOUR_OUTSIDE_ROI")
    # 3x backing pixels per one original logical pixel; never shift ROI or interpolate.
    native_roi = alpha[:, 465:915]
    if native_roi.shape != (720, 450):
        raise ValueError("BLOCKED_S3_CONTOUR_NATIVE_CROP")
    compressed = native_roi.reshape(240, 3, 150, 3).max(axis=(1, 3))
    # The original high-res RGBA is intentionally not returned for mutation.
    return compressed >= 24, {
        "original_zip_sha256": FROZEN_CONTOUR_ZIP_SHA,
        "original_png_sha256": FROZEN_CONTOUR_PNG_SHA,
        "original_plan_sha256": FROZEN_PLAN_SHA,
        "original_report_sha256": FROZEN_REPORT_SHA,
        "detail_strokes": 410, "detail_vertices": 1792,
        "native_ink_alpha24": int(np.count_nonzero(alpha >= 24)),
        "native_ink_outside_roi": outside,
        "logical_contour_guide_pixels": int(np.count_nonzero(compressed >= 24))
    }


def build_adjacency(regions, lab, ink):
    if regions.shape != (240, 150) or ink.shape != regions.shape:
        raise ValueError("BLOCKED_S3_REGION_CONTOUR_DIMENSIONS")
    graph = {}
    for direction in (0, 1):
        left = regions[:-1] if direction == 0 else regions[:, :-1]
        right = regions[1:] if direction == 0 else regions[:, 1:]
        la = lab[:-1] if direction == 0 else lab[:, :-1]
        lb = lab[1:] if direction == 0 else lab[:, 1:]
        ink_a = ink[:-1] if direction == 0 else ink[:, :-1]
        ink_b = ink[1:] if direction == 0 else ink[:, 1:]
        crossing = (left != right) & (left >= 0) & (right >= 0)
        y, x = np.where(crossing)
        if not len(y):
            continue
        gradients = color.deltaE_ciede2000(la[crossing], lb[crossing])
        support = (ink_a[crossing] | ink_b[crossing]) & (gradients >= 15.)
        for i, (py, px) in enumerate(zip(y.tolist(), x.tolist())):
            u, v = sorted((int(left[py, px]), int(right[py, px])))
            if u == v:
                continue
            value = graph.setdefault((u, v), [0, 0])
            value[0] += 1
            value[1] += int(support[i])
    return graph


def solve_region_colors(rgb, palette, regions, ink, *, use_contour, chroma_penalty):
    """Deterministic nearest palette + adjacency consistency, NOT neural color inference."""
    if (rgb.shape != (240, 150, 3) or palette.shape != (32, 3) or
            regions.shape != rgb.shape[:2] or ink.shape != regions.shape):
        raise ValueError("BLOCKED_S3_SOURCE_SHAPE")
    if np.min(regions) < -1:
        raise ValueError("BLOCKED_S3_REGION_LABELS")
    lab = color.rgb2lab(rgb / 255.0)
    plab = color.rgb2lab(palette[np.newaxis, :, :] / 255.0)[0]
    n = int(regions.max()) + 1
    median_lab = np.empty((n, 3), float)
    for rid in range(n):
        samples = lab[regions == rid]
        if samples.size == 0:
            raise ValueError("BLOCKED_S3_EMPTY_REGION")
        median_lab[rid] = np.median(samples, axis=0)
    unary = color.deltaE_ciede2000(median_lab[:, None, :], plab[None, :, :])
    if chroma_penalty:
        original_chroma = np.linalg.norm(median_lab[:, 1:], axis=1)
        game_chroma = np.linalg.norm(plab[:, 1:], axis=1)
        extra = np.maximum(0., game_chroma[None, :] - original_chroma[:, None] - 8.)
        unary += extra * .4
    unary[:, BG] = np.inf
    assignment = np.argmin(unary, axis=1).astype(np.uint8)
    edges = build_adjacency(regions, lab, ink)
    neighborhood = [[] for _ in range(n)]
    contour_protected_edges = 0
    for (u, v), (contacts, evidence) in edges.items():
        median_de = float(color.deltaE_ciede2000(median_lab[u], median_lab[v]))
        if median_de > 8:
            continue
        protected = bool(use_contour and contacts and evidence / contacts >= .25)
        if protected:
            contour_protected_edges += 1
            continue
        weight = 2.0 * min(contacts, 16)
        neighborhood[u].append((v, weight))
        neighborhood[v].append((u, weight))
    for _ in range(3):
        for rid in range(n):
            cost = unary[rid].copy()
            for neighbor, weight in neighborhood[rid]:
                cost += weight * (np.arange(32) != int(assignment[neighbor]))
            assignment[rid] = np.argmin(cost)
    result = np.full((240, 150), BG, dtype=np.uint8)
    result[regions >= 0] = assignment[regions[regions >= 0]]
    return result, {"solver": "deterministic_CIELAB_region_graph_NOT_NEURAL_COLOR_MODEL",
                    "region_count": n, "region_adjacency_pairs": len(edges),
                    "smoothing_edges": sum(len(x) for x in neighborhood)//2,
                    "contour_protected_edges": contour_protected_edges,
                    "chroma_excess_penalty": bool(chroma_penalty),
                    "contour_used_for_color_prior": bool(use_contour)}


def run(source_path: Path, palette_path: Path, s1_path: Path,
        contour_path: Path | None, output: Path):
    if output.exists():
        raise ValueError("BLOCKED_S3_NO_OVERWRITE")
    _, rgb = read_source(source_path)
    palette = read_palette(palette_path)
    raw = palette_path.read_bytes()
    blobsha = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if blobsha != PALETTE_BLOB:
        raise ValueError("BLOCKED_S3_PALETTE_DRIFT")
    masks, frozen_g, _ = _read_original_archive(s1_path)
    # S3 candidate region labels are independently built from ORIGINAL RGB
    # without reading or passing frozen G32 labels.
    _, bg, region_ids, info = independent_regions(rgb, palette, masks)
    ink = None
    provenance = {"status": "BLOCKED_CONTOUR_PROVENANCE",
                  "reason": "NO_AUTHENTICATED_NATIVE_V44B_ARCHIVE"}
    if contour_path is not None:
        try:
            ink, provenance = read_immutable_contour(contour_path)
            provenance["status"] = "VERIFIED_IMMUTABLE_NATIVE_V44B_SOURCE"
        except ValueError as exc:
            if not str(exc).startswith("BLOCKED_S3_"):
                raise
            # Fail closed ONLY for J1 contour-guided candidate; J0 source
            # control can still run. Never reconstruct or modify V44-B.
            ink = None
            provenance = {"status": "BLOCKED_CONTOUR_PROVENANCE",
                          "reason": str(exc)}
    outputs = {}
    details = {}
    for with_penalty in (False, True):
        tag = "CHROMA" if with_penalty else "PLAIN"
        name = f"J0_COLOR_ONLY_{tag}"
        outputs[name], details[name] = solve_region_colors(
            rgb, palette, region_ids, np.zeros(bg.shape, bool),
            use_contour=False, chroma_penalty=with_penalty)
        if ink is not None:
            name = f"J1_FROZEN_CONTOUR_{tag}"
            outputs[name], details[name] = solve_region_colors(
                rgb, palette, region_ids, ink,
                use_contour=True, chroma_penalty=with_penalty)
    measured = {k: metrics(rgb, image, palette) for k, image in outputs.items()}
    measured["B0_FROZEN_G32_CONTROL"] = metrics(rgb, frozen_g, palette)
    baseline = measured["B0_FROZEN_G32_CONTROL"]
    # Exact same gate for all candidates, independent of pipeline controls.
    gates = {}
    for name, report in measured.items():
        if name.startswith("B0_"):
            continue
        color_bg = int(np.count_nonzero((outputs[name] == BG) != (frozen_g == BG)))
        gates[name] = {
            "component_reduction_ge25pct": report["components4"] <= .75 * baseline["components4"],
            "mean_deltaE00_growth_le1": report["mean_deltaE00"] <= baseline["mean_deltaE00"] + 1.,
            "p95_deltaE00_growth_le2": report["p95_deltaE00"] <= baseline["p95_deltaE00"] + 2.,
            "background_mismatch_le2pct": color_bg <= .02 * frozen_g.size,
            "palette_le32": report["palette_colors_used"] <= 32,
        }
    output.mkdir(parents=True)
    Image.fromarray(rgb, "RGB").save(output/"original-RGB.png")
    Image.fromarray(palette[frozen_g], "RGB").save(output/"B0_G32-RGB.png")
    Image.fromarray(bg.astype(np.uint8) * 255, "L").save(output/"original-bg.png")
    if ink is not None:
        Image.fromarray(ink.astype(np.uint8)*255, "L").save(output/"V44-B-original-native-contour-alpha24-logical.png")
    for name, idx in outputs.items():
        Image.fromarray(idx, "L").save(output/f"{name}-indices.png")
        Image.fromarray(palette[idx], "RGB").save(output/f"{name}-RGB.png")
    hashes = {p.name: sha(p) for p in output.iterdir() if p.is_file()}
    status = "SOURCE_CANDIDATE_VISUAL_PENDING" if any(all(x.values()) for x in gates.values()) else "SOURCE_CANDIDATE_FAIL"
    report = {"experiment": EXP, "status": status, "model_only": True,
              "original_source_sha256": SOURCE_SHA, "palette_blob": PALETTE_BLOB,
              "real_pretrained_S1_SAM2_proposals": len(masks),
              "learned_semantic_color_model": "NOT_RUN",
              "candidate_source_original_only": True,
              "V44_B_native_contour": provenance,
              "V44_B_contours_changed": False,
              "V44_B_contours_final_native_execution": "NOT_RUN",
              "s3_regions": info, "solver_details": details,
              "metrics": measured, "source_gates": gates, "parameters": PARAMS,
              "github_sha": os.getenv("GITHUB_SHA"), "github_run_id": os.getenv("GITHUB_RUN_ID"),
              "visual_user_review": "PENDING", "real_Egret_brush_quality": "NOT_RUN",
              "game_E4": "NOT_RUN", "independent_E5": "NOT_RUN", "exact_CHALK": None,
              "production_accepted": False, "output_file_sha256": hashes}
    (output/"report.json").write_text(json.dumps(report, ensure_ascii=False,
        indent=2, allow_nan=False)+"\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("--source", type=Path, required=True)
    cli.add_argument("--palette", type=Path, required=True)
    cli.add_argument("--s1-archive", type=Path, required=True)
    cli.add_argument("--v44b-archive", type=Path)
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    result = run(args.source, args.palette, args.s1_archive, args.v44b_archive, args.output)
    print(json.dumps({"status": result["status"], "source_gates": result["source_gates"],
                     "metrics": result["metrics"], "contour": result["V44_B_native_contour"]},
                     ensure_ascii=False))

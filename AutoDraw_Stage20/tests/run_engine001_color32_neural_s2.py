#!/usr/bin/env python3
"""ENGINE-001 NEURAL-S2: original-first independent SLIC flatting + frozen real SAM2 masks.

B0 G32 is loaded ONLY after construction of C1/C2 for comparison.
S1 SAM2 genuine model masks are replayed by original SHA. Source-only model, NOT Egret.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import zipfile

import cv2
import numpy as np
from PIL import Image
from skimage import color, segmentation

from run_engine001_palette32_region_study import (
    SOURCE_SHA, PALETTE_BLOB, ROI_WH, read_source, read_palette, sha,
)

EXP = "ENGINE001_COLOR32_NEURAL_S2_ORIGINAL_FIRST_FLATTING"
S1_ARCHIVE_SHA = "9cceb35e8a6f1ef70ba8a4e4157e9409bb1125c0f50b22c1883a46686b225bd0"
S1_MASKS_SHA = "cd3783e36dbebe73d5bac573e8c43feab172bbc04e14235996bb67d6d02ed8f3"
S1_MANIFEST_SHA = "86533ad5ea8d3586cd01d894e32d79aa65077c03fb6b82efe338324bc3065b52"
S1_REPORT_SHA = "a8755153067c8e378924de3dc1c87d7947806e5f90ad405ee34206247d7d7a48"
G32_PNG_SHA = "b8dcd5f00d2c39c81997aaae084eaae19a776454e6fd6466209839288c1e5637"
SAM_SOURCE_SHA = "2b90b9f5ceec907a1c18123530e92e794ad901a4"
SAM_WEIGHTS_SHA = "7402e0d864fa82708a20fbd15bc84245c2f26dff0eb43a4b5b93452deb34be69"
BG = 30
PARAMS = {"slic_n_segments": 240, "compactness": 8.0, "sigma": 0.7,
          "connectivity": 4, "original_white_edge_deltaE00": 10.0,
          "mask_min_pixels": 4, "assignment": "median_LAB_nearest_CIEDE2000"}

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _read_original_archive(path: Path):
    if sha(path) != S1_ARCHIVE_SHA:
        raise ValueError("BLOCKED_S2_ORIGINAL_S1_ZIP_DRIFT")
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:
            raise ValueError("BLOCKED_S2_ARCHIVE_CRC")
        prefix = "engine001-neural-s1-"
        names = {
            "mask": prefix + "sam2/sam2_masks.npz",
            "manifest": prefix + "sam2/sam2_manifest.json",
            "report": prefix + "evaluation/report.json",
            "g": prefix + "evaluation/B0_G32-indices.png",
        }
        if not all(n in z.namelist() for n in names.values()):
            raise ValueError("BLOCKED_S2_ARCHIVE_CONTENT")
        data = {k: z.read(n) for k, n in names.items()}
        if (digest(data["mask"]) != S1_MASKS_SHA or
                digest(data["manifest"]) != S1_MANIFEST_SHA or
                digest(data["report"]) != S1_REPORT_SHA or
                digest(data["g"]) != G32_PNG_SHA):
            raise ValueError("BLOCKED_S2_SOURCE_ARCHIVE_MEMBER_SHA")
        manifest = json.loads(data["manifest"])
        report = json.loads(data["report"])
        if (manifest.get("model") != "SAM2.1_HIERA_TINY" or
                manifest.get("sam2_git_sha") != SAM_SOURCE_SHA or
                manifest.get("model_checkpoint_sha256") != SAM_WEIGHTS_SHA or
                manifest.get("source_sha256") != SOURCE_SHA or
                manifest.get("mask_archive_sha256") != S1_MASKS_SHA or
                report.get("source_sha256") != SOURCE_SHA):
            raise ValueError("BLOCKED_S2_REAL_SAM2_PROVENANCE")
        masks = []
        with np.load(io.BytesIO(data["mask"]), allow_pickle=False) as archive:
            if set(archive.files) != {m["key"] for m in manifest["masks"]}:
                raise ValueError("BLOCKED_S2_MASK_INDEX")
            for m in manifest["masks"]:
                a = archive[m["key"]]
                if (a.shape != (240, 150) or a.dtype != np.bool_ or
                        digest(a.tobytes()) != m["sha256"] or
                        int(a.sum()) != int(m["area"])):
                    raise ValueError("BLOCKED_S2_MASK_DRIFT")
                masks.append((float(m["predicted_iou"]),
                              float(m["stability_score"]), str(m["key"]), a.copy()))
        masks.sort(key=lambda x: (-x[0], -x[1], x[2]))
        g = np.asarray(Image.open(io.BytesIO(data["g"])), dtype=np.uint8).copy()
        if g.shape != (240, 150) or g.max() >= 32:
            raise ValueError("BLOCKED_S2_G32_SHAPE")
        return masks, g, manifest

def white_background(lab: np.ndarray, palette_lab: np.ndarray):
    within = color.deltaE_ciede2000(lab, palette_lab[BG][None, None, :]) <= 10.0
    n, ids = cv2.connectedComponents(within.astype(np.uint8), connectivity=8)
    border = np.unique(np.concatenate([ids[0], ids[-1], ids[:, 0], ids[:, -1]]))
    bg = np.isin(ids, border[border != 0])
    return bg

def independent_regions(rgb: np.ndarray, palette: np.ndarray, masks):
    """Never accepts or reads a G32 index: independent original RGB segmentation."""
    if rgb.shape != (240, 150, 3) or rgb.dtype != np.uint8 or palette.shape != (32, 3):
        raise ValueError("BLOCKED_S2_RGB_SHAPE")
    lab = color.rgb2lab(rgb / 255.0)
    plab = color.rgb2lab(palette[None, :, :] / 255.0)[0]
    bg = white_background(lab, plab)
    slic = segmentation.slic(rgb, n_segments=240, compactness=8.0,
        sigma=0.7, start_label=0, convert2lab=True, enforce_connectivity=True)
    regions = np.full(bg.shape, -1, np.int32)
    neural_pixels = 0
    k = 0
    for _, _, _, mask in masks:
        if mask.shape != bg.shape or mask.dtype != np.bool_:
            raise ValueError("BLOCKED_S2_NEURAL_MASK_SHAPE")
        available = mask & (~bg) & (regions < 0)
        if int(available.sum()) < 4:
            continue
        regions[available] = k
        neural_pixels += int(available.sum())
        k += 1
    for label in np.unique(slic):
        part = (slic == label) & (regions < 0) & (~bg)
        n, components = cv2.connectedComponents(part.astype(np.uint8), connectivity=4)
        for component in range(1, n):
            regions[components == component] = k
            k += 1
    if np.any((regions < 0) & (~bg)):
        raise AssertionError("S2 original region partition incomplete")
    out = np.full(bg.shape, BG, np.uint8)
    for region_id in range(k):
        mask = regions == region_id
        med = np.median(lab[mask], axis=0)
        distances = color.deltaE_ciede2000(med[None, :], plab).reshape(-1)
        distances[BG] = np.inf
        out[mask] = int(np.argmin(distances))
    return out, bg, regions, {"regions": k, "neural_owned_pixels": neural_pixels,
                "nonbackground_pixels": int((~bg).sum()),
                "slic_source_segments": int(np.unique(slic).size)}

def metrics(rgb, out, palette):
    lab = color.rgb2lab(rgb / 255.)
    rendered = palette[out]
    distances = color.deltaE_ciede2000(lab, color.rgb2lab(rendered / 255.))
    counts = {"components4": 0, "singletons4": 0, "components_le4": 0}
    for owner in np.unique(out):
        if owner == BG:
            continue
        n, labels, stat, _ = cv2.connectedComponentsWithStats(
            (out == owner).astype(np.uint8), connectivity=4)
        size = stat[1:, cv2.CC_STAT_AREA]
        counts["components4"] += n - 1
        counts["singletons4"] += int(np.count_nonzero(size == 1))
        counts["components_le4"] += int(np.count_nonzero(size <= 4))
    return {**counts, "mean_deltaE00": float(distances.mean()),
            "p95_deltaE00": float(np.percentile(distances, 95)),
            "rgb_mae": float(np.abs(rgb.astype(np.int16) -
                              rendered.astype(np.int16)).mean()),
            "palette_colors_used": int(np.unique(out).size),
            "pink_owner_counts": {str(i): int((out == i).sum()) for i in (10, 15, 19, 29)},
            "white_background_pixels": int((out == BG).sum())}

def evaluate(rgb, palette, masks, g):
    # Construct C1 and C2 independently BEFORE using G32 as frozen control.
    c1, b1, r1, i1 = independent_regions(rgb, palette, [])
    c2, b2, r2, i2 = independent_regions(rgb, palette, masks)
    assert np.array_equal(b1, b2)
    measured = {k: metrics(rgb, v, palette) for k, v in [
        ("B0_G32", g), ("C1_SLIC_ORIGINAL", c1), ("C2_SAM2_SLIC_ORIGINAL", c2)]}
    baseline = measured["B0_G32"]
    a = measured["C2_SAM2_SLIC_ORIGINAL"]
    drift = int(np.count_nonzero(b2 != (g == BG)))
    checks = {
        "component_reduction_ge25pct": a["components4"] <= .75 * baseline["components4"],
        "mean_deltaE00_growth_le1": a["mean_deltaE00"] <= baseline["mean_deltaE00"] + 1.,
        "palette_le32": a["palette_colors_used"] <= 32,
        "background_drift_le2pct_roi": drift <= .02 * g.size,
        "neural_owned_at_least1pct_foreground": i2["neural_owned_pixels"] >= .01 * int((~b2).sum()),
    }
    return {"c1": c1, "c2": c2, "bg": b2, "r1": r1, "r2": r2,
            "metrics": measured, "mask_info": i2,
            "c1_regions": i1, "background_drift_pixels_vs_G32": drift,
            "gates": checks, "source_candidate_all_gates_pass": all(checks.values())}

def run(source: Path, palette_file: Path, frozen_archive: Path, outdir: Path):
    if outdir.exists():
        raise ValueError("BLOCKED_S2_NO_OVERWRITE")
    if sha(source) != SOURCE_SHA:
        raise ValueError("BLOCKED_S2_SOURCE_DRIFT")
    raw = palette_file.read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if blob != PALETTE_BLOB:
        raise ValueError("BLOCKED_S2_PALETTE_DRIFT")
    _, rgb = read_source(source)
    palette = read_palette(palette_file)
    masks, g, manifest = _read_original_archive(frozen_archive)
    result = evaluate(rgb, palette, masks, g)
    outdir.mkdir(parents=True)
    for name, idx in [("B0_G32", g), ("C1_ORIGINAL", result["c1"]),
                      ("C2_ORIGINAL_SAM2", result["c2"])]:
        Image.fromarray(idx, "L").save(outdir / (name + "-indices.png"))
        Image.fromarray(palette[idx], "RGB").save(outdir / (name + "-RGB.png"))
    Image.fromarray(rgb, "RGB").save(outdir / "original-RGB.png")
    Image.fromarray(result["bg"].astype(np.uint8)*255, "L").save(outdir / "original-background-mask.png")
    Image.fromarray(result["r2"].astype(np.int32), "I").save(outdir / "original-partition-labels.png")
    hashes = {p.name: sha(p) for p in outdir.iterdir() if p.is_file()}
    report = {
        "experiment": EXP, "status": "SOURCE_CANDIDATE_FAIL" if not result["source_candidate_all_gates_pass"] else "SOURCE_CANDIDATE_VISUAL_PENDING",
        "source_only": True, "no_G32_in_candidate_construction": True,
        "real_neural_mask_origin": "CI44127991472_REUSED_S1_MASKS_EXPLORATORY",
        "original_s1_artifact_sha256": S1_ARCHIVE_SHA,
        "sam2_source_sha": SAM_SOURCE_SHA, "sam2_checkpoint_sha256": SAM_WEIGHTS_SHA,
        "github_sha": os.environ.get("GITHUB_SHA"), "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "source_sha256": SOURCE_SHA, "palette_blob": PALETTE_BLOB, "parameters": PARAMS,
        "mask_count": len(masks),
        "metrics": result["metrics"], "mask_info": result["mask_info"],
        "c1_regions": result["c1_regions"],
        "background_drift_pixels_vs_G32": result["background_drift_pixels_vs_G32"],
        "source_candidate_gates": result["gates"],
        "visual_quality": "USER_REVIEW_PENDING",
        "native_Egret": "NOT_RUN", "original_410_contours_LAST": "NOT_RUN",
        "game_E4": "NOT_RUN", "independent_E5": "NOT_RUN",
        "exact_CHALK": None, "production_accepted": False,
        "output_file_sha256": hashes,
    }
    (outdir / "report.json").write_text(json.dumps(report, ensure_ascii=False,
        indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return report

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--palette", type=Path, required=True)
    p.add_argument("--s1-archive", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    r = run(args.source, args.palette, args.s1_archive, args.output)
    print(json.dumps({"status":r["status"],"metrics":r["metrics"],
                      "gates":r["source_candidate_gates"]}, ensure_ascii=False))

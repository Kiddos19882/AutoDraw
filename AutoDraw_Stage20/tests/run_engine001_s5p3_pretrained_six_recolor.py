#!/usr/bin/env python3
"""ENGINE-001 S5-P3: pretrained six-palette recoloring, original RGB only.

Experimental RGB preview. Not game32, not a game paint plan or Egret validation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from run_engine001_palette32_region_study import read_source, sha, SOURCE_SHA

EXP = "ENGINE001_S5_P3_RECOLOR_PRO_PRETRAINED_SIX_COLOR_RGB"
UPSTREAM_SHA = "4ef126095ad21394deabf72db807aeb3e728b553"
GOOGLE_DRIVE_CHECKPOINT_ID = "1dLir8CG_BdsSfxCKlHDgpOPShKpWooRr"
SOURCE_PALETTE_SIZE = 6


def six_source_colors(rgb: np.ndarray) -> list[list[int]]:
    """Deterministic condition-only palette, never a learned color prediction."""
    if rgb.shape != (240, 150, 3) or rgb.dtype != np.uint8:
        raise ValueError("BLOCKED_S5P3_SOURCE_IMAGE_SHAPE")
    original = Image.fromarray(rgb, "RGB")
    indexed = original.quantize(
        colors=SOURCE_PALETTE_SIZE,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    )
    colors = indexed.getpalette() or []
    ranked = sorted(indexed.getcolors() or [], key=lambda item: -item[0])
    selected = [tuple(int(c) for c in colors[3*i:3*i+3]) for _, i in ranked]
    if len(selected) != SOURCE_PALETTE_SIZE or len(set(selected)) != SOURCE_PALETTE_SIZE:
        raise ValueError("BLOCKED_S5P3_NOT_SIX_DISTINCT_SOURCE_COLORS")
    selected.sort(key=lambda c: (299*c[0]+587*c[1]+114*c[2], c))
    return [list(c) for c in selected]


def check_output(result: Image.Image, reference: np.ndarray) -> dict:
    if not isinstance(result, Image.Image) or result.size != (150, 240):
        raise ValueError("BLOCKED_S5P3_INFERENCE_OUTPUT_SIZE")
    arr = np.asarray(result.convert("RGB"), dtype=np.uint8)
    if arr.shape != reference.shape:
        raise ValueError("BLOCKED_S5P3_INFERENCE_OUTPUT_SHAPE")
    changed = int(np.count_nonzero(np.any(arr != reference, axis=2)))
    if changed == 0:
        raise ValueError("BLOCKED_S5P3_NEURAL_NO_EFFECT")
    from skimage.color import rgb2lab, deltaE_ciede2000
    de = deltaE_ciede2000(rgb2lab(reference/255.0), rgb2lab(arr/255.0))
    return {
        "changed_pixels": changed, "mean_deltaE00": float(np.mean(de)),
        "p95_deltaE00": float(np.percentile(de, 95)),
        "unique_output_rgb_colors": int(np.unique(arr.reshape(-1, 3), axis=0).shape[0]),
        "original_nearwhite_pixels_HEURISTIC": int(np.count_nonzero(np.all(reference >= 245, axis=2))),
        "result_nearwhite_pixels_HEURISTIC": int(np.count_nonzero(np.all(arr >= 245, axis=2))),
        "model_output": "REAL_PRETRAINED_FULL_RGB_NOT_GAME32",
        "visual_user_review": "PENDING",
    }


def run(source: Path, checkpoint: Path, upstream: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("BLOCKED_S5P3_NO_OVERWRITE")
    original, rgb = read_source(source)
    if not checkpoint.is_file() or checkpoint.stat().st_size < 1_000_000:
        raise ValueError("BLOCKED_PRETRAINED_WEIGHTS_MISSING_OR_TOO_SMALL")
    if not (upstream/"infer.py").is_file() or not (upstream/"model.py").is_file():
        raise ValueError("BLOCKED_S5P3_PINNED_UPSTREAM_INFERENCE_MISSING")
    palette = six_source_colors(rgb)
    import torch
    if torch.cuda.is_available():
        raise ValueError("BLOCKED_S5P3_CPU_ONLY_PROTOCOL")
    torch.set_num_threads(2)
    sys.path.insert(0, str(upstream))
    from infer import load_model, recolor_image

    checkpoint_sha = sha(checkpoint)
    # Upstream load_model uses weights_only=True; never execute pickle object fallback.
    model = load_model(str(checkpoint), device="cpu")
    with torch.inference_mode():
        recolored = recolor_image(model, original, palette, "cpu")
    stats = check_output(recolored, rgb)

    output.mkdir(parents=True)
    original.save(output/"original-RGB.png")
    recolored.convert("RGB").save(output/"pretrained-six-color-recolored-RGB.png")
    strip = Image.new("RGB", (150, 18), "white")
    from PIL import ImageDraw
    brush = ImageDraw.Draw(strip)
    for index, rgb_color in enumerate(palette):
        brush.rectangle((index*25, 0, (index+1)*25-1, 17), fill=tuple(rgb_color))
    strip.save(output/"six-original-colors.png")
    side = Image.new("RGB", (300, 240), "white")
    side.paste(original, (0, 0))
    side.paste(recolored.convert("RGB"), (150, 0))
    side.resize((900, 720), Image.Resampling.NEAREST).save(output/"original-vs-pretrained-recolor-3x.png")
    (output/"six-original-colors.json").write_text(
        json.dumps({"palette_source": "PILLOW_MEDIANCUT_ORIGINAL_RGB_ONLY", "colors_rgb": palette},
            indent=2)+"\n", encoding="utf-8")
    report = {
        "experiment": EXP, "status": "VISUAL_REVIEW_PENDING",
        "original_source_sha256": SOURCE_SHA,
        "upstream_project": "itmesneha/Recolorization-Pro",
        "upstream_commit": UPSTREAM_SHA,
        "official_checkpoint_google_drive_file_id": GOOGLE_DRIVE_CHECKPOINT_ID,
        "checkpoint_sha256": checkpoint_sha, "checkpoint_bytes": checkpoint.stat().st_size,
        "actual_pretrained_neural_inference": True,
        "conditioning_six_colors_rgb": palette,
        "conditioning_color_selection": "MATH_MEDIANCUT_NOT_NEURAL",
        "RGB_output_unrestricted": True, "game32_gate": "NOT_APPLICABLE_VISUAL_PILOT",
        "source_quality_gates_S3_S4": "HISTORICAL_UNCHANGED_NOT_RUN",
        "measurements": stats,
        "native_Egret": "NOT_RUN", "game_E4": "NOT_RUN", "independent_E5": "NOT_RUN",
        "exact_CHALK": None, "V44_B_410_final_contours_changed": False,
        "production_accepted": False,
        "github_sha": os.getenv("GITHUB_SHA"), "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "file_sha256": {p.name:sha(p) for p in sorted(output.iterdir()) if p.is_file()},
    }
    (output/"report.json").write_text(json.dumps(
        report, indent=2, ensure_ascii=False, allow_nan=False)+"\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    opts = parser.parse_args()
    report = run(opts.source, opts.checkpoint, opts.upstream, opts.output)
    print(json.dumps({
        "status": report["status"], "checkpoint_sha256": report["checkpoint_sha256"],
        "conditioning_six_colors_rgb": report["conditioning_six_colors_rgb"],
        "measurements": report["measurements"]}, ensure_ascii=False))

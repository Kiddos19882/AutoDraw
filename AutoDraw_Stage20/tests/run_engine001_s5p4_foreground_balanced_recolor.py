#!/usr/bin/env python3
"""S5-P4: pretrained BiRefNet foreground guidance and real six-color RGB recoloring.

Research only. Does not generate game32 colors, native strokes or game CHALK.
"""
from __future__ import annotations
import argparse
import json
import os
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from run_engine001_palette32_region_study import read_source, sha, SOURCE_SHA
from run_engine001_color32_s5p2_birefnet import run as run_birefnet
from run_engine001_s5p3_pretrained_six_recolor import (
    UPSTREAM_SHA, GOOGLE_DRIVE_CHECKPOINT_ID, check_output,
)

EXP = "ENGINE001_S5_P4_FOREGROUND_BALANCED_SIX_RECOLOR"
EXPECTED_RECOLOR_SHA256 = "525144a0022ea43096079b8a27f1d4bbb7768dfdcae98444b5275de4ac536321"
EXPECTED_RECOLOR_BYTES = 118010004
EXPECTED_MASK_SHA256 = "5600024376f572a557870a5eb0afb1e5961636bef4e1e22132025467d0f03333"
SHAPE = (240, 150)
MASK_THRESHOLD = 128
NEARWHITE_MIN = 245
BUCKET_WIDTH = 16
MIN_COLOR_DISTANCE = 18.0


def six_balanced_source_colors(rgb: np.ndarray, alpha: np.ndarray) -> list[list[int]]:
    """Exactly one source-nearwhite background and five diverse foreground colors.

    The only source for conditioning RGB is the original image, not a game32 proxy.
    Alpha is the separate pretrained foreground guide (not ground truth).
    """
    if rgb.shape != (*SHAPE, 3) or rgb.dtype != np.uint8:
        raise ValueError("BLOCKED_S5P4_SOURCE_SHAPE")
    if alpha.shape != SHAPE or alpha.dtype != np.uint8:
        raise ValueError("BLOCKED_S5P4_ALPHA_SHAPE")
    if int(alpha.max()) == int(alpha.min()):
        raise ValueError("BLOCKED_S5P4_CONSTANT_ALPHA")
    nearwhite = np.all(rgb >= NEARWHITE_MIN, axis=2)
    bg = rgb[(alpha < MASK_THRESHOLD) & nearwhite]
    fg = rgb[(alpha >= MASK_THRESHOLD) & ~nearwhite]
    if len(bg) < 1 or len(fg) < 5:
        raise ValueError("BLOCKED_S5P4_BACKGROUND_OR_FOREGROUND_EMPTY")
    background = np.median(bg.astype(np.float64), axis=0).round().astype(np.uint8)
    # RGB bucket histogram with representatives derived from original pixel means.
    buckets = (fg.astype(np.int32) // BUCKET_WIDTH)
    keys = buckets[:, 0] * 256 + buckets[:, 1] * 16 + buckets[:, 2]
    unique_keys, inverse, counts = np.unique(keys, return_inverse=True, return_counts=True)
    sums = np.stack([np.bincount(inverse, weights=fg[:, c], minlength=len(counts))
                     for c in range(3)], axis=1)
    reps = np.rint(sums / counts[:, None]).astype(np.int32)
    # Chroma bonus counteracts the nearwhite imbalance without inventing hues.
    chroma = (reps.max(axis=1) - reps.min(axis=1)).astype(np.float64) / 255.0
    support = np.sqrt(counts.astype(np.float64))
    weights = support * (1.0 + 2.0 * chroma)
    order = np.lexsort((unique_keys, -weights))
    chosen = [background.astype(np.float64)]
    selected: list[list[int]] = []
    remaining = list(int(i) for i in order)
    for _ in range(5):
        ranked = []
        for i in remaining:
            distances = np.linalg.norm(np.stack(chosen) - reps[i], axis=1)
            closest = float(distances.min())
            if closest >= MIN_COLOR_DISTANCE:
                score = float(weights[i]) * min(closest / 64.0, 3.0)
                ranked.append((-score, -int(counts[i]), int(unique_keys[i]), i))
        if not ranked:
            raise ValueError("BLOCKED_S5P4_INSUFFICIENT_DIVERSE_FOREGROUND")
        picked = min(ranked)[-1]
        color = [int(x) for x in reps[picked]]
        selected.append(color)
        chosen.append(np.array(color, dtype=np.float64))
        remaining.remove(picked)
    # Keep the background first; tie-breaking of foreground choices is deterministic.
    result = [[int(x) for x in background]] + selected
    if len({tuple(x) for x in result}) != 6 or not all(0 <= c <= 255 for x in result for c in x):
        raise ValueError("BLOCKED_S5P4_INVALID_SIX_COLORS")
    return result


def run(source: Path, checkpoint: Path, upstream: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("BLOCKED_S5P4_NO_OVERWRITE")
    original, rgb = read_source(source)
    if sha(source) != SOURCE_SHA:
        raise ValueError("BLOCKED_S5P4_SOURCE_SHA_DRIFT")
    if not checkpoint.is_file() or checkpoint.stat().st_size != EXPECTED_RECOLOR_BYTES:
        raise ValueError("BLOCKED_S5P4_CHECKPOINT_SIZE_DRIFT")
    checkpoint_sha = sha(checkpoint)
    if checkpoint_sha != EXPECTED_RECOLOR_SHA256:
        raise ValueError("BLOCKED_S5P4_RECOLOR_CHECKPOINT_SHA_DRIFT")
    if not (upstream / "infer.py").is_file() or not (upstream / "model.py").is_file():
        raise ValueError("BLOCKED_S5P4_PINNED_UPSTREAM_MISSING")
    import torch
    if torch.cuda.is_available():
        raise ValueError("BLOCKED_S5P4_CPU_ONLY")

    # Reuse P2 model loading, checksum verification and real ONNX mask inference.
    with tempfile.TemporaryDirectory(prefix="engine001-s5p4-") as tmp:
        mask_dir = Path(tmp) / "p2-foreground"
        mask_report = run_birefnet(source, mask_dir)
        if mask_report["model_sha256"] != EXPECTED_MASK_SHA256:
            raise ValueError("BLOCKED_S5P4_MASK_SHA_DRIFT")
        alpha = np.asarray(Image.open(mask_dir / "foreground-alpha.png").convert("L"), dtype=np.uint8)
        colors = six_balanced_source_colors(rgb, alpha)

        # Unmodified pinned upstream inference, same interface as frozen S5-P3.
        import sys
        sys.path.insert(0, str(upstream))
        from infer import load_model, recolor_image
        torch.set_num_threads(2)
        model = load_model(str(checkpoint), device="cpu")
        with torch.inference_mode():
            recolored = recolor_image(model, original, colors, "cpu")
        metrics = check_output(recolored, rgb)
        result = np.asarray(recolored.convert("RGB"), dtype=np.uint8)
        foreground = alpha >= MASK_THRESHOLD
        nearwhite = lambda x: np.all(x >= NEARWHITE_MIN, axis=2)
        metrics["source_nearwhite_foreground_pixels"] = int((nearwhite(rgb) & foreground).sum())
        metrics["result_nearwhite_foreground_pixels"] = int((nearwhite(result) & foreground).sum())
        metrics["source_nearwhite_background_pixels"] = int((nearwhite(rgb) & ~foreground).sum())
        metrics["result_nearwhite_background_pixels"] = int((nearwhite(result) & ~foreground).sum())
        metrics["source_mean_saturation"] = float(
            np.mean((rgb.max(axis=2).astype(float) - rgb.min(axis=2)) / 255.0))
        metrics["result_mean_saturation"] = float(
            np.mean((result.max(axis=2).astype(float) - result.min(axis=2)) / 255.0))

        output.mkdir(parents=True)
        original.save(output / "original-RGB.png")
        Image.fromarray(alpha, "L").save(output / "foreground-alpha.png")
        recolored.convert("RGB").save(output / "s5p4-pretrained-recolored-RGB.png")
        strip = Image.new("RGB", (150, 18), "white")
        draw = ImageDraw.Draw(strip)
        for index, color in enumerate(colors):
            draw.rectangle((index * 25, 0, (index + 1) * 25 - 1, 17), fill=tuple(color))
        strip.save(output / "six-source-colors.png")
        side = Image.new("RGB", (300, 240), "white")
        side.paste(original, (0, 0))
        side.paste(recolored.convert("RGB"), (150, 0))
        side.resize((900, 720), Image.Resampling.NEAREST).save(output / "original-vs-s5p4-3x.png")
        (output / "six-source-colors.json").write_text(json.dumps(
            {"background_first": True, "colors_rgb": colors,
             "selection": "SOURCE_RGB_MASK128_CHROMA_WEIGHTED_BUCKET16_DIVERSITY18"},
            indent=2) + "\n", encoding="utf-8")
        report = {
            "experiment": EXP, "status": "VISUAL_USER_REVIEW_PENDING",
            "source_sha256": SOURCE_SHA, "source_original_only": True,
            "mask_checkpoint_sha256": mask_report["model_sha256"],
            "mask_real_pretrained_onnx": mask_report["actual_pretrained_onnx_inference"],
            "recolor_checkpoint_sha256": checkpoint_sha,
            "recolor_checkpoint_bytes": checkpoint.stat().st_size,
            "recolor_upstream_commit": UPSTREAM_SHA,
            "google_drive_checkpoint_id": GOOGLE_DRIVE_CHECKPOINT_ID,
            "actual_pretrained_neural_recolor": True,
            "six_source_conditioning_rgb": colors,
            "conditioning_is_neural": False,
            "output": "REAL_PRETRAINED_FULL_RGB_NOT_GAME32",
            "metrics": metrics,
            "frozen_p3_comparison": {
                "p3_ci": 44151445030, "p3_mean_deltaE00": 8.1148479,
                "p3_p95_deltaE00": 18.9549259,
                "p3_result_nearwhite_pixels": 0,
                "p3_distinct_rgb": 15890,
                "pixelwise_p3_comparison": "NOT_RUN",
            },
            "visual_accepted": False, "historical_gates_modified": False,
            "V44_B_410_last_contours_modified": False, "native_Egret": "NOT_RUN",
            "game_E4": "NOT_RUN", "independent_E5": "NOT_RUN",
            "exact_CHALK": None, "production_accepted": False,
            "github_sha": os.getenv("GITHUB_SHA"), "github_run_id": os.getenv("GITHUB_RUN_ID"),
            "file_sha256": {p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file()},
        }
        (output / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8")
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.source, args.checkpoint, args.upstream, args.output)
    print(json.dumps({"status": result["status"], "sha": result["recolor_checkpoint_sha256"],
                      "colors": result["six_source_conditioning_rgb"], "metrics": result["metrics"]}))

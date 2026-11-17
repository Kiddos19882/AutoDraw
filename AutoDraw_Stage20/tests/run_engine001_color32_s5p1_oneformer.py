#!/usr/bin/env python3
"""S5-P1: authentic pinned pretrained OneFormer semantic guidance, source-only.

This generates ADE20K semantic labels, NOT a 32-game-swatch color assignment.
No Stage6, Egret, original contour or frozen experiment mutation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

from run_engine001_palette32_region_study import read_source, sha, SOURCE_SHA

EXPERIMENT = "ENGINE001_COLOR32_S5P1_ONEFORMER_ORIGINAL_SEMANTICS"
MODEL_ID = "shi-labs/oneformer_ade20k_swin_tiny"
REVISION = "05f2812b1eccf9909b3897777450f8d68148cafc"
SIZE = (240, 150)  # H, W
MODEL_LABEL_LIMIT = 150


def validate_labels(value: np.ndarray, limit: int = MODEL_LABEL_LIMIT) -> dict:
    if value.shape != SIZE or not np.issubdtype(value.dtype, np.integer):
        raise ValueError("BLOCKED_S5P1_SEMANTIC_SHAPE_OR_DTYPE")
    if value.min() < 0 or value.max() >= limit:
        raise ValueError("BLOCKED_S5P1_SEMANTIC_LABEL_RANGE")
    counts = Counter(int(v) for v in value.reshape(-1))
    most = max(counts.values())
    boundary = np.zeros(SIZE, dtype=bool)
    boundary[:, 1:] |= value[:, 1:] != value[:, :-1]
    boundary[1:, :] |= value[1:, :] != value[:-1, :]
    return {
        "label_count": len(counts),
        "class_pixel_counts": {str(k): int(v) for k, v in sorted(counts.items())},
        "largest_class_fraction": round(most / value.size, 8),
        "boundary_pixel_count": int(np.count_nonzero(boundary)),
        "feasibility_gate": "PASS" if len(counts) >= 2 and most <= .95 * value.size else "FAIL",
    }


def preview_labels(labels: np.ndarray) -> np.ndarray:
    # Display-only colors, NOT the game's 32 original swatches.
    out = np.zeros((*labels.shape, 3), dtype=np.uint8)
    for k in np.unique(labels):
        n = int(k) + 1
        out[labels == k] = [(53*n + 31) % 256, (97*n + 67) % 256, (193*n + 13) % 256]
    return out


def run(source: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("BLOCKED_S5P1_NO_OVERWRITE")
    image, rgb = read_source(source)  # original-RGB 150x240, SHA-checked
    output.mkdir(parents=True)
    image.save(output / "original-RGB.png")
    # The checkpoint is downloaded and used for actual inference. No mock fallback.
    import torch
    from huggingface_hub import snapshot_download
    from transformers import OneFormerProcessor, OneFormerForUniversalSegmentation

    directory = snapshot_download(
        repo_id=MODEL_ID, revision=REVISION,
        allow_patterns=["*.json", "*.txt", "*.bin"],
    )
    checkpoint = Path(directory) / "pytorch_model.bin"
    if not checkpoint.is_file():
        raise ValueError("BLOCKED_S5P1_OFFICIAL_CHECKPOINT_MISSING")
    weight_sha = sha(checkpoint)
    if checkpoint.stat().st_size < 100_000_000:
        raise ValueError("BLOCKED_S5P1_OFFICIAL_CHECKPOINT_TOO_SMALL")
    torch.set_num_threads(2)
    processor = OneFormerProcessor.from_pretrained(directory)
    model = OneFormerForUniversalSegmentation.from_pretrained(directory, use_safetensors=False)
    model.eval()
    with torch.inference_mode():
        inputs = processor(images=image, task_inputs=["semantic"], return_tensors="pt")
        logits = model(**inputs)
        labels = processor.post_process_semantic_segmentation(
            logits, target_sizes=[SIZE]
        )[0].cpu().numpy()
    # ADE20K segmentation has 150 categories; upstream id2label may carry ImageNet names.
    # Never promote unvalidated names or >149 IDs into this source-only report.
    stats = validate_labels(labels, limit=MODEL_LABEL_LIMIT)
    u8 = labels.astype(np.uint8)
    Image.fromarray(u8, "L").save(output / "oneformer-semantic-labels.png")
    Image.fromarray(preview_labels(u8), "RGB").save(output / "oneformer-semantic-preview.png")
    boundary = np.zeros(SIZE, dtype=np.uint8)
    boundary[:, 1:] |= (labels[:, 1:] != labels[:, :-1]).astype(np.uint8)
    boundary[1:, :] |= (labels[1:, :] != labels[:-1, :]).astype(np.uint8)
    Image.fromarray(boundary*255, "L").save(output / "oneformer-semantic-boundaries.png")
    report = {
        "experiment": EXPERIMENT, "model_id": MODEL_ID, "model_revision": REVISION,
        "model_checkpoint_sha256": weight_sha,
        "model_checkpoint_bytes": checkpoint.stat().st_size,
        "actual_pretrained_inference": True, "source_sha256": SOURCE_SHA,
        "input_original_rgb_only": True, "input_shape": list(rgb.shape),
        "semantic_class_names": "NOT_VERIFIED_UPSTREAM_ID2LABEL_MAPPING",
        "upstream_config_id2label_count": len(model.config.id2label),
        "semantic_stats": stats,
        "trained_game32_palette_head": False, "game32_palette_conversion": "NOT_RUN",
        "native_Egret_quality": "NOT_RUN", "game_E4": "NOT_RUN",
        "independent_E5": "NOT_RUN", "exact_CHALK": None,
        "V44_B_410_final_strokes_changed": False,
        "production_accepted": False,
        "github_sha": os.getenv("GITHUB_SHA"), "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "output_sha256": {p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file()},
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)+"\n")
    return report


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("--source", required=True, type=Path)
    cli.add_argument("--output", required=True, type=Path)
    opts = cli.parse_args()
    result = run(opts.source, opts.output)
    print(json.dumps({"status": result["semantic_stats"]["feasibility_gate"],
        "checkpoint_sha256": result["model_checkpoint_sha256"],
        "semantic_stats": result["semantic_stats"]}, ensure_ascii=False))

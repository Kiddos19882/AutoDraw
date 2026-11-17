#!/usr/bin/env python3
"""Actual SAM2.1 tiny masks export. No synthetic or OpenCV masks used as neural.

Optional EXPLORATORY CPU inference; frozen source input and immutable report.
No production changes or native quality assertions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path

import numpy as np
from run_engine001_palette32_region_study import SOURCE_SHA, read_source, sha
from run_engine001_color32_neural_s1 import EXP

FROZEN_SAM2_SOURCE_SHA = "2b90b9f5ceec907a1c18123530e92e794ad901a4"
FROZEN_SAM2_TINY_CHECKPOINT_SHA = "7402e0d864fa82708a20fbd15bc84245c2f26dff0eb43a4b5b93452deb34be69"


def git_sha(directory: Path):
    return subprocess.check_output(
        ["git", "-C", str(directory), "rev-parse", "HEAD"],
        text=True, timeout=15).strip()


def run(source: Path, sam2_repo: Path, checkpoint: Path, output: Path):
    if output.exists():
        raise ValueError("BLOCKED_NEURAL_S1_NO_OVERWRITE")
    if not sam2_repo.is_dir() or not checkpoint.is_file():
        raise ValueError("BLOCKED_NEURAL_S1_MODEL_MISSING")
    if git_sha(sam2_repo) != FROZEN_SAM2_SOURCE_SHA:\n        raise ValueError("BLOCKED_NEURAL_S1_SAM2_CODE_DRIFT")\n    if sha(checkpoint) != FROZEN_SAM2_TINY_CHECKPOINT_SHA:\n        raise ValueError("BLOCKED_NEURAL_S1_SAM2_WEIGHT_DRIFT")\n    _, image = read_source(source)\n    import torch
    import sam2
    from sam2.build_sam import build_sam2
    from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator
    torch.manual_seed(0)
    torch.set_num_threads(2)
    model = build_sam2("configs/sam2.1/sam2.1_hiera_t.yaml",
                       str(checkpoint), device="cpu", apply_postprocessing=False)
    model.eval()
    generator = SAM2AutomaticMaskGenerator(
        model, points_per_side=8, points_per_batch=8, crop_n_layers=0,
        pred_iou_thresh=0.8, stability_score_thresh=0.95,
        output_mode="binary_mask")
    with torch.inference_mode():
        results = generator.generate(image)
    masks = {}
    entries = []
    for i, item in enumerate(results):
        mask = np.asarray(item["segmentation"], dtype=np.bool_)
        if mask.shape != (240, 150):
            raise ValueError("BLOCKED_NEURAL_S1_MODEL_MASK_GEOMETRY")
        if not mask.any():
            continue
        key = f"mask_{i:04d}"
        masks[key] = mask
        entries.append({
            "key": key, "area": int(mask.sum()),
            "sha256": hashlib.sha256(mask.tobytes()).hexdigest(),
            "predicted_iou": float(item["predicted_iou"]),
            "stability_score": float(item["stability_score"]),
        })
    if not entries:
        raise ValueError("BLOCKED_NEURAL_S1_SAM2_NO_MASKS")
    output.mkdir(parents=True)
    archive = output / "sam2_masks.npz"
    np.savez_compressed(archive, **masks)
    manifest = {
        "experiment": EXP,
        "status": "ACTUAL_SAM2_MASKS_EXPLORATORY",
        "model": "SAM2.1_HIERA_TINY",
        "source_sha256": SOURCE_SHA,
        "mask_shape_hw": [240, 150],
        "mask_archive_sha256": sha(archive),
        "model_checkpoint_sha256": sha(checkpoint),
        "sam2_git_sha": git_sha(sam2_repo),
        "model_config": "configs/sam2.1/sam2.1_hiera_t.yaml",
        "model_checkpoint_download": "https://huggingface.co/facebook/sam2.1-hiera-tiny/resolve/main/sam2.1_hiera_tiny.pt",
        "parameters": {"points_per_side": 8, "points_per_batch": 8,
                       "crop_n_layers": 0, "pred_iou_thresh": 0.8,
                       "stability_score_thresh": 0.95},
        "masks": entries,
        "github_sha": os.environ.get("GITHUB_SHA"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "versions": {"python": platform.python_version(),
                     "numpy": np.__version__, "torch": torch.__version__,
                     "sam2_python_file": str(Path(sam2.__file__).resolve())},
        "game_E4": "NOT_RUN", "exact_CHALK": None,
        "production_accepted": False,
    }
    (output / "sam2_manifest.json").write_text(json.dumps(
        manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8")
    return manifest


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--sam2-repo", type=Path, required=True)
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    r = run(a.source, a.sam2_repo, a.checkpoint, a.output)
    print("NEURAL S1 REAL SAM2 MASKS:", len(r["masks"]))
    print("NEURAL S1 MODEL SHA:", r["model_checkpoint_sha256"])
    print("NEURAL S1 SAM2 SOURCE SHA:", r["sam2_git_sha"])


if __name__ == "__main__":
    main()

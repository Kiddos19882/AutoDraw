#!/usr/bin/env python3
"""S5-P2 authentic pretrained BiRefNet ONNX original-image foreground mask.

Binary/soft foreground ONLY; not a learned 32-color palette assignment.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image

from run_engine001_palette32_region_study import read_source, sha, SOURCE_SHA

EXP = "ENGINE001_COLOR32_S5P2_BIREFNET_ONNX_FOREGROUND"
MODEL = "birefnet-general-lite"
EXPECTED_ONNX_MD5 = "4fab47adc4ff364be1713e97b7e66334"
SHAPE = (240, 150)


def foreground_metrics(alpha: np.ndarray, rgb: np.ndarray) -> dict:
    if alpha.shape != SHAPE or alpha.dtype != np.uint8 or rgb.shape != (*SHAPE, 3):
        raise ValueError("BLOCKED_S5P2_INVALID_ALPHA_OR_RGB_SHAPE")
    if int(alpha.max()) <= int(alpha.min()):
        raise ValueError("BLOCKED_S5P2_CONSTANT_MASK")
    fractions = {str(t): round(float(np.count_nonzero(alpha >= t) / alpha.size), 8)
                 for t in (64, 128, 192)}
    foreground = alpha >= 128
    boundaries = np.zeros(SHAPE, dtype=bool)
    boundaries[:, 1:] |= foreground[:, 1:] != foreground[:, :-1]
    boundaries[1:, :] |= foreground[1:, :] != foreground[:-1, :]
    white_proxy = np.all(rgb >= 245, axis=2)
    fraction = fractions["128"]
    return {
        "alpha_min": int(alpha.min()),
        "alpha_max": int(alpha.max()),
        "alpha_mean": round(float(alpha.mean()), 6),
        "foreground_fraction_by_threshold": fractions,
        "boundary_pixels_at_128": int(boundaries.sum()),
        "uncertain_alpha_64_to_192": int(((alpha >= 64) & (alpha <= 192)).sum()),
        "source_nearwhite_rgb_proxy_pixels_NOT_GROUND_TRUTH": int(white_proxy.sum()),
        "foreground_on_source_nearwhite_proxy_pixels_NOT_QUALITY_GATE": int(
            np.count_nonzero(foreground & white_proxy)),
        "feasibility_gate": "PASS" if .05 <= fraction <= .95 else "FAIL",
    }


def run(source: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("BLOCKED_S5P2_NO_OVERWRITE")
    image, rgb = read_source(source)
    output.mkdir(parents=True)
    image.save(output / "original-RGB.png")
    # CPU ONNX inference via a published pretrained model, without trust_remote_code.
    from rembg import new_session, remove
    import rembg
    import onnxruntime

    session = new_session(MODEL, providers=["CPUExecutionProvider"])
    model_file = Path(session.download_models())
    if not model_file.is_file():
        raise ValueError("BLOCKED_S5P2_ONNX_CHECKPOINT_MISSING")
    actual_md5 = hashlib.md5(model_file.read_bytes()).hexdigest()
    if actual_md5 != EXPECTED_ONNX_MD5:
        raise ValueError("BLOCKED_S5P2_ONNX_CHECKPOINT_MD5_DRIFT")
    model_sha = sha(model_file)
    raw_mask = remove(image, session=session, only_mask=True)
    if not isinstance(raw_mask, Image.Image):
        raise ValueError("BLOCKED_S5P2_ONNX_NOT_PIL_MASK")
    alpha = np.asarray(raw_mask.convert("L"), dtype=np.uint8)
    details = foreground_metrics(alpha, rgb)
    Image.fromarray(alpha, "L").save(output / "foreground-alpha.png")
    Image.fromarray(((alpha >= 128)*255).astype(np.uint8), "L").save(
        output / "foreground-mask-128.png")
    rgba = np.dstack((rgb, alpha))
    Image.fromarray(rgba, "RGBA").save(output / "foreground-preview-RGBA.png")
    report = {
        "experiment": EXP,
        "actual_pretrained_onnx_inference": True,
        "model": MODEL,
        "model_file_basename": model_file.name,
        "model_md5": actual_md5,
        "model_sha256": model_sha,
        "model_bytes": model_file.stat().st_size,
        "rembg_version": getattr(rembg, "__version__", "UNREPORTED"),
        "onnxruntime_version": onnxruntime.__version__,
        "source_sha256": SOURCE_SHA,
        "source_original_rgb_only": True,
        "mask_metrics": details,
        "background_comparison_to_B0": "NOT_RUN",
        "trained_game32_palette_head": False,
        "game32_color_conversion": "NOT_RUN",
        "V44_B_410_final_strokes_changed": False,
        "native_Egret_quality": "NOT_RUN",
        "game_E4": "NOT_RUN", "independent_E5": "NOT_RUN",
        "exact_CHALK": None, "production_accepted": False,
        "github_sha": os.getenv("GITHUB_SHA"), "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "output_sha256": {p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file()},
    }
    (output / "report.json").write_text(json.dumps(
        report, indent=2, ensure_ascii=False, allow_nan=False)+"\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    rep = run(options.source, options.output)
    print(json.dumps({"model_sha256": rep["model_sha256"],
        "mask_metrics":rep["mask_metrics"]}, ensure_ascii=False))

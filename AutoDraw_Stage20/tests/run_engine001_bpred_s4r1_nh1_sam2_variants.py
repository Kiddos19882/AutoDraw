#!/usr/bin/env python3
"""ENGINE-001/BPRED-S4-R1 NH1: genuine pinned SAM2.1 tiny, NO training.

Only frozen KNOWN/DEV originals. Proposals are hints, NOT source-owner
ground truth, brush stroke permission, source-color improvement or E4 CHALK.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

from engine001_bpred_s4r1_generic_source_maps import (
    decode_original, generic_source_maps, original_source_region_uncertainty,
)

EXPERIMENT = "ENGINE001_BPRED_S4R1_NH1_SAM2_NO_TRAIN_V1"
SAM2_SHA = "2b90b9f5ceec907a1c18123530e92e794ad901a4"
WEIGHTS_SHA = "7402e0d864fa82708a20fbd15bc84245c2f26dff0eb43a4b5b93452deb34be69"
CORPUS = Path("AutoDraw_Stage20/data/generated_autodraw_plan/images_31_first")
SAMPLES = (
    ("wV6VeZI9S1Y.png", "KNOWN_CONTROL", "d3cd95b846f036a3f8acecf75d2a237e46dcf13a"),
    ("Sanrio_Characters_Hello_Kitty_Image026.webp", "DEV", "072711810ac4ae65d1a786291869e810a421f61c"),
)
AUTO_VARIANTS = {
    "A0_original_auto8_strict": dict(points_per_side=8, points_per_batch=8,
                                     pred_iou_thresh=0.8, stability_score_thresh=0.95,
                                     crop_n_layers=0),
    "A1_original_auto16_open": dict(points_per_side=16, points_per_batch=8,
                                    pred_iou_thresh=0.7, stability_score_thresh=0.85,
                                    crop_n_layers=0),
    "A2_original_auto16_crop1": dict(points_per_side=16, points_per_batch=8,
                                     pred_iou_thresh=0.7, stability_score_thresh=0.85,
                                     crop_n_layers=1, crop_n_points_downscale_factor=2),
}
PROMPT_LIMIT = 8
PROMPT_MIN_REGION = 64
SOURCE_RGB_CONTRAST = 40
SOURCE_PROMPT_SEPARATION = 12


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def original_to_model_rgb(rgba: np.ndarray) -> np.ndarray:
    if not isinstance(rgba, np.ndarray) or rgba.ndim != 3 or rgba.shape[2] != 4 or rgba.dtype != np.uint8:
        raise ValueError("BLOCKED_NH1_RGBA")
    rgb = rgba[:, :, :3].astype(np.uint32)
    a = rgba[:, :, 3:4].astype(np.uint32)
    # Only for the model input: never modify original alpha or source RGB.
    return ((rgb * a + 255 * (255 - a) + 127) // 255).astype(np.uint8)


def choose_source_prompts(regions: dict, source_maps: dict,
                          limit: int = PROMPT_LIMIT) -> list[dict]:
    """Automatic source-only geometry; no human points/ROIs or owner labels."""
    labels = regions["region_ids"]
    core = regions["geometric_potential_core"]
    rgb = source_maps["source_rgb"]
    if labels.ndim != 2 or core.shape != labels.shape or rgb.shape != (*labels.shape, 3):
        raise ValueError("BLOCKED_NH1_PROMPT_ALIGNMENT")
    if source_maps["owner_status"] != "MISSING" or not source_maps["stroke_admission"].startswith("FORBIDDEN"):
        raise ValueError("BLOCKED_NH1_PROMPT_OWNER_PROVENANCE")
    reps = regions["representatives"]
    sorted_reps = sorted(reps, key=lambda r: (-r["pixels"], r["region_id"]))
    prompts = []
    for r in sorted_reps:
        if len(prompts) >= limit:
            break
        if r["pixels"] < PROMPT_MIN_REGION:
            continue
        rid = int(r["region_id"])
        pixels = np.argwhere((labels == rid) & core)
        if len(pixels) == 0:
            continue
        # First source-core position in row-major order: deterministic,
        # automatically inside same source region and outside protected edges.
        y, x = map(int, pixels[len(pixels)//2])
        point_rgb = rgb[y, x].astype(np.int16)
        negative = None
        for other in sorted_reps:
            if int(other["region_id"]) == rid:
                continue
            nx, ny = map(int, other["source_pixel_xy"])
            if (np.hypot(nx - x, ny - y) < SOURCE_PROMPT_SEPARATION
                    or np.linalg.norm(rgb[ny, nx].astype(np.int16) - point_rgb)
                       < SOURCE_RGB_CONTRAST):
                continue
            if source_maps["source_alpha"][ny, nx] != 255:
                continue
            negative = [nx, ny]
            break
        if negative is None:
            # A single positive point is an accepted predictor input.
            coords, pt_labels = [[x, y]], [1]
        else:
            coords, pt_labels = [[x, y], negative], [1, 0]
        prompts.append({
            "source_region_id": rid, "source_region_pixels": int(r["pixels"]),
            "point_coords_xy": coords, "point_labels": pt_labels,
            "automatic_only": True,
        })
    return prompts


def mask_metrics(masks: np.ndarray, rgba: np.ndarray, source_maps: dict) -> dict:
    if (not isinstance(masks, np.ndarray) or masks.ndim != 3 or masks.dtype != bool
            or masks.shape[1:] != rgba.shape[:2]):
        raise ValueError("BLOCKED_NH1_MODEL_MASK_SHAPE")
    if not np.isfinite(masks).all():
        raise ValueError("BLOCKED_NH1_MODEL_NONFINITE")
    count = masks.shape[0]
    union = masks.any(axis=0)
    boundary = np.zeros(rgba.shape[:2], bool)
    for mask in masks:
        if mask.shape[0] > 1:
            dy = mask[:-1] != mask[1:]
            boundary[:-1] |= dy
            boundary[1:] |= dy
        if mask.shape[1] > 1:
            dx = mask[:, :-1] != mask[:, 1:]
            boundary[:, :-1] |= dx
            boundary[:, 1:] |= dx
    inflated_edge = ndimage.binary_dilation(
        source_maps["source_edge"], structure=ndimage.generate_binary_structure(2, 1)
    )
    areas = masks.reshape(count, -1).sum(axis=1).astype(int) if count else np.empty(0, np.int64)
    area = sorted(areas.tolist())
    return {
        "model_proposal_masks": int(count),
        "nonempty_proposals": int(np.count_nonzero(areas)),
        "model_union_pixels": int(union.sum()),
        "model_union_original_invalid_alpha_pixels": int((union & (rgba[:, :, 3] < 255)).sum()),
        "model_union_source_protected_pixels": int((union & source_maps["protected"]).sum()),
        "model_boundary_pixels": int(boundary.sum()),
        "model_boundary_near_original_rgb_edge_pixels": int((boundary & inflated_edge).sum()),
        "model_boundary_near_original_rgb_edge_ratio": (
            round(float((boundary & inflated_edge).sum() / boundary.sum()), 8)
            if boundary.any() else None),
        "mask_area_min_median_max": (
            [int(area[0]), float(np.median(area)), int(area[-1])]
            if len(area) else None),
        "source_owner_status": "MISSING",
        "critical_semantic_recall": "UNKNOWN_NO_INDEPENDENT_GROUND_TRUTH",
        "s4_strict": "BLOCKED",
        "stroke_admission": "FORBIDDEN_UNTIL_NATIVE_INDEPENDENT_VALIDATION",
    }


def save_variant(out: Path, name: str, masks: np.ndarray, rgba: np.ndarray,
                 model_view: np.ndarray, source_maps: dict, metadata: dict) -> dict:
    out.mkdir(parents=True, exist_ok=False)
    metrics = mask_metrics(masks, rgba, source_maps)
    np.savez_compressed(out / "model_raw_binary_masks.npz", masks=masks)
    union = masks.any(axis=0)
    Image.fromarray(union.astype(np.uint8)*255, "L").save(out / "model_union.png")
    blend = model_view.copy()
    if union.any():
        blend[union] = np.rint(0.65 * blend[union] + 0.35 * np.array(
            [30, 205, 95], dtype=np.float32)).astype(np.uint8)
    Image.fromarray(blend, "RGB").save(out / "model_diagnostic_overlay.png")
    return {
        "name": name, "metrics": metrics, "input_original_rgb_unchanged": True,
        "model_pseudo_truth": False, "actual_model_inference": True,
        "metadata": metadata,
        "sha256": {p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file()},
    }


def run(root: Path, checkpoint: Path, sam_repo: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("BLOCKED_NH1_NO_OVERWRITE")
    if not checkpoint.is_file() or sha(checkpoint) != WEIGHTS_SHA:
        raise ValueError("BLOCKED_NH1_PINNED_WEIGHTS")
    if not sam_repo.is_dir():
        raise ValueError("BLOCKED_NH1_SAM2_CODE_MISSING")
    git_sha = subprocess.check_output(
        ["git", "-C", str(sam_repo), "rev-parse", "HEAD"],
        text=True, timeout=15).strip()
    if git_sha != SAM2_SHA:
        raise ValueError("BLOCKED_NH1_SAM2_CODE_DRIFT")
    import torch
    from sam2.build_sam import build_sam2
    from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator
    from sam2.sam2_image_predictor import SAM2ImagePredictor
    torch.manual_seed(0)
    torch.set_num_threads(2)
    model = build_sam2(
        "configs/sam2.1/sam2.1_hiera_t.yaml", str(checkpoint),
        device="cpu", apply_postprocessing=False,
    ).eval()
    output.mkdir(parents=True)
    report = {
        "experiment": EXPERIMENT, "no_training": True,
        "model": "OFFICIAL_SAM2_1_HIERA_TINY",
        "sam2_source_git_sha": git_sha,
        "sam2_model_checkpoint_sha256": WEIGHTS_SHA,
        "cpu_threads": 2,
        "github_sha": os.getenv("GITHUB_SHA"),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "s4_strict": "BLOCKED",
        "all_source_owners": "MISSING",
        "stroke_admission": "FORBIDDEN_UNTIL_NATIVE_INDEPENDENT_VALIDATION",
        "source_color_quality": "NOT_ASSESSED",
        "semantic_gt": "MISSING",
        "native_E3": "NOT_RUN", "game_E4": "NOT_RUN",
        "independent_E5": "NOT_RUN", "exact_CHALK": None,
        "production_accepted": False,
        "records": [],
    }
    def persist():
        (output / "manifest.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
            encoding="utf8")
    persist()
    t0 = time.monotonic()
    for filename, role, expected_blob in SAMPLES:
        raw = (root / CORPUS / filename).read_bytes()
        if git_blob(raw) != expected_blob:
            raise ValueError("BLOCKED_NH1_FROZEN_ORIGINAL_BLOB:" + filename)
        src = decode_original(raw)
        rgba = src["rgba"]
        original_sha = hashlib.sha256(rgba.tobytes()).hexdigest()
        view = original_to_model_rgb(rgba)
        sm = generic_source_maps(rgba)
        regions = original_source_region_uncertainty(rgba, sm)
        prompts = choose_source_prompts(regions, sm)
        sample_dir = output / hashlib.sha256(filename.encode()).hexdigest()[:12]
        sample_dir.mkdir()
        Image.fromarray(view, "RGB").save(sample_dir/"model_view_original_composite.png")
        record = {
            "file": filename, "role": role, "input_sha256": src["sha256"],
            "raw_git_blob_sha1": src["git_blob_sha1"], "original_rgba_sha256": original_sha,
            "original_hw": list(rgba.shape[:2]),
            "original_alpha_has_invalid": bool((rgba[:,:,3]<255).any()),
            "source_regions": int(regions["counts"]["regions"]),
            "source_owner_status": sm["owner_status"],
            "source_semantics": "UNKNOWN",
            "automatic_source_prompts": prompts,
            "variants": [],
        }
        report["records"].append(record)
        persist()
        for name, cfg in AUTO_VARIANTS.items():
            if name.startswith("A2_") and role != "KNOWN_CONTROL":
                continue
            start = time.monotonic()
            generator = SAM2AutomaticMaskGenerator(model, output_mode="binary_mask", **cfg)
            with torch.inference_mode():
                result = generator.generate(view)
            masks = (
                np.stack([np.asarray(m["segmentation"], dtype=bool)
                          for m in result], axis=0)
                if result else np.zeros((0, *rgba.shape[:2]), dtype=bool)
            )
            if masks.shape[1:] != rgba.shape[:2]:
                raise ValueError("BLOCKED_NH1_AUTO_MASK_WRONG_ORIGINAL_SHAPE")
            variant = save_variant(sample_dir/name, name, masks, rgba, view, sm, {
                "mode": "SAM2AutomaticMaskGenerator", "parameters": cfg,
                "seconds": round(time.monotonic()-start,3),
                "model_scores": [{
                    "predicted_iou": float(m["predicted_iou"]),
                    "stability_score": float(m["stability_score"]),
                } for m in result],
            })
            record["variants"].append(variant)
            persist()
        start = time.monotonic()
        masks_list, ious = [], []
        if prompts:
            predictor = SAM2ImagePredictor(model)
            with torch.inference_mode():
                predictor.set_image(view)
                for prompt in prompts:
                    result, scores, _ = predictor.predict(
                        point_coords=np.asarray(prompt["point_coords_xy"], dtype=np.float32),
                        point_labels=np.asarray(prompt["point_labels"], dtype=np.int32),
                        multimask_output=False,
                        normalize_coords=False,
                    )
                    if result.shape != (1, *rgba.shape[:2]) or not np.isfinite(scores).all():
                        raise ValueError("BLOCKED_NH1_PROMPT_PREDICTION_SHAPE")
                    masks_list.append(np.asarray(result[0], dtype=bool))
                    ious.append(float(scores[0]))
                predictor.reset_predictor()
        masks = (np.stack(masks_list, axis=0)
                 if masks_list else np.zeros((0,*rgba.shape[:2]), dtype=bool))
        variant = save_variant(
            sample_dir/"P1_original_slic_positive_negative", "P1_original_slic_positive_negative",
            masks, rgba, view, sm,
            {"mode": "SAM2ImagePredictor", "automatic_prompt_count":len(prompts),
             "single_mask_prediction":True, "source_auto_prompts":prompts,
             "predicted_iou":ious, "seconds":round(time.monotonic()-start,3),
             "status": "ACTUAL_PROMPT_MODEL" if prompts else "SKIPPED_NO_VALID_PROMPTS"}
        )
        variant["actual_model_inference"] = bool(prompts)
        record["variants"].append(variant)
        if hashlib.sha256(rgba.tobytes()).hexdigest() != original_sha:
            raise ValueError("BLOCKED_NH1_SOURCE_IMAGE_MUTATED")
        record["sha256"] = {p.name:sha(p) for p in sample_dir.iterdir() if p.is_file()}
        persist()
    report["runtime_seconds"] = round(time.monotonic()-t0,3)
    report["information_only_gate"] = (
        "E2_PROPOSAL_DIVERSITY_ONLY" if any(
            v["metrics"]["nonempty_proposals"] > 0
            for rec in report["records"] for v in rec["variants"])
        else "NOT_USEFUL_ALL_PROPOSALS_EMPTY")
    persist()
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--sam2-repo",type=Path,required=True)
    p.add_argument("--checkpoint",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    report=run(a.root,a.checkpoint,a.sam2_repo,a.output)
    print(json.dumps({
        "status":report["information_only_gate"],
        "runtime_seconds":report["runtime_seconds"],
        "variants":[(r["file"], v["name"], v["metrics"]["model_proposal_masks"])
                    for r in report["records"] for v in r["variants"]],
        "s4_strict":report["s4_strict"], "stroke_admission":report["stroke_admission"],
    }, ensure_ascii=False,allow_nan=False))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""ENGINE-001 S4: actual pretrained DINOv2 dense features influence fixed game32 colors.

The feature encoder is neural; the palette-index graph is deterministic.
This is not a trained 32-class color head or an Egret brush measurement.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image
from skimage import color

from run_engine001_palette32_region_study import PALETTE_BLOB, SOURCE_SHA, read_source, read_palette, sha
from run_engine001_color32_neural_s2 import BG, _read_original_archive, independent_regions, metrics
from run_engine001_color32_neural_s3_joint import optional_native_contour, build_adjacency

EXPERIMENT = "ENGINE001_COLOR32_NEURAL_S4_DINOV2_CONTEXT_PALETTE"
REVISION = "ed25f3a31f01632728cabb09d1542f84ab7b0056"
WEIGHTS_SHA = "ae1e99fcefd534ed978cdeb8326f08030c96e28b7a81ffcbc98a857c84d14be1"


def real_dino_features(image, model_dir):
    """No synthetic embeddings, no download fallback, pinned checkpoint only."""
    if sha(model_dir / "model.safetensors") != WEIGHTS_SHA:
        raise ValueError("BLOCKED_S4_MODEL_SHA_DRIFT")
    import torch
    import transformers
    from transformers import Dinov2Model, AutoImageProcessor
    torch.manual_seed(0)
    torch.set_num_threads(2)
    processor = AutoImageProcessor.from_pretrained(str(model_dir), local_files_only=True, use_fast=False)
    model = Dinov2Model.from_pretrained(
        str(model_dir), local_files_only=True, use_safetensors=True).eval().to("cpu")
    pixels = processor(images=Image.fromarray(image, "RGB"), return_tensors="pt")["pixel_values"]
    with torch.inference_mode():
        patches = model(pixel_values=pixels).last_hidden_state
    h, w = (int(pixels.shape[-2] // model.config.patch_size),
            int(pixels.shape[-1] // model.config.patch_size))
    if tuple(patches.shape[:2]) != (1, 1 + h*w):
        raise ValueError("BLOCKED_S4_PATCH_GRID")
    grid = patches[:, 1:, :].transpose(1, 2).reshape(1, -1, h, w)
    dense = torch.nn.functional.interpolate(
        grid, size=(240, 150), mode="bilinear", align_corners=False)
    dense = torch.nn.functional.normalize(dense, dim=1)
    field = dense.squeeze(0).permute(1, 2, 0).numpy().astype(np.float32)
    if field.shape[:2] != (240, 150) or not np.isfinite(field).all():
        raise ValueError("BLOCKED_S4_BAD_NEURAL_FEATURES")
    return field, {"weights_sha256": WEIGHTS_SHA, "revision": REVISION,
                   "config_sha256": sha(model_dir/"config.json"),
                   "processor_sha256": sha(model_dir/"preprocessor_config.json"),
                   "grid_hw": [h, w], "field_hwc": list(field.shape),
                   "torch_version": torch.__version__,
                   "transformers_version": transformers.__version__}


def region_embeddings(field, regions):
    n = int(regions.max()) + 1
    if field.shape[:2] != regions.shape or n < 1:
        raise ValueError("BLOCKED_S4_REGION_ALIGNMENT")
    vectors = np.zeros((n, field.shape[-1]), np.float64)
    for i in range(n):
        values = field[regions == i]
        if not values.size:
            raise ValueError("BLOCKED_S4_EMPTY_REGION")
        mean = values.mean(axis=0).astype(np.float64)
        norm = np.linalg.norm(mean)
        if norm < 1e-8 or not np.isfinite(norm):
            raise ValueError("BLOCKED_S4_FEATURE_NORM")
        vectors[i] = mean / norm
    return vectors


def choose_colors(rgb, palette, regions, ink, neural_vectors=None, contour_enabled=False):
    if (rgb.shape != (240, 150, 3) or palette.shape != (32, 3) or
            regions.shape != (240, 150) or ink.shape != regions.shape):
        raise ValueError("BLOCKED_S4_SHAPE")
    lab = color.rgb2lab(rgb/255.)
    p_lab = color.rgb2lab(palette[None, :, :]/255.)[0]
    n = int(regions.max()) + 1
    med = np.array([np.median(lab[regions == k],axis=0) for k in range(n)])
    costs = color.deltaE_ciede2000(med[:, None, :], p_lab[None, :, :])
    costs += .4*np.maximum(0.,np.linalg.norm(p_lab[:,1:],axis=1)[None,:] -
                          np.linalg.norm(med[:,1:],axis=1)[:,None]-8.)
    costs[:,BG] = np.inf
    labels = np.argmin(costs, axis=1).astype(np.uint8)
    if neural_vectors is not None and neural_vectors.shape[0] != n:
        raise ValueError("BLOCKED_S4_NEURAL_REGION_COUNT")
    neighbors=[[] for _ in range(n)]
    neural_edges=outline_edges=0
    for (u,v),(contacts, supported) in build_adjacency(
            regions,lab,ink if contour_enabled else np.zeros_like(ink)).items():
        de=float(color.deltaE_ciede2000(med[u],med[v]))
        if de>=15.:
            continue
        if contour_enabled and supported/contacts>=.25:
            outline_edges+=1
            continue
        if neural_vectors is None:
            smooth=de<=8.
        else:
            smooth=float(neural_vectors[u]@neural_vectors[v])>=.85
            neural_edges+=int(smooth)
        if smooth:
            weight=2.*min(contacts,16)
            neighbors[u].append((v,weight))
            neighbors[v].append((u,weight))
    for _ in range(3):
        for rid in range(n):
            options=costs[rid].copy()
            for other,weight in neighbors[rid]:
                options += weight*(np.arange(32)!=int(labels[other]))
            labels[rid]=int(np.argmin(options))
    out=np.full(regions.shape,BG,dtype=np.uint8)
    out[regions>=0]=labels[regions[regions>=0]]
    return out,{"pretrained_neural_features_used":neural_vectors is not None,
                "neural_similarity_edges":neural_edges,
                "outline_protected_edges":outline_edges,
                "smoothing_edges":sum(len(x) for x in neighbors)//2,
                "trained_palette_head":"NOT_TRAINED"}


def run(source,palette_path,s1_archive,outline_archive,model_dir,output):
    if output.exists():
        raise ValueError("BLOCKED_S4_NO_OVERWRITE")
    raw=palette_path.read_bytes()
    blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    if blob != PALETTE_BLOB:
        raise ValueError("BLOCKED_S4_PALETTE_DRIFT")
    _,rgb=read_source(source)
    palette=read_palette(palette_path)
    masks,g32,_=_read_original_archive(s1_archive)
    _,bg,regions,info=independent_regions(rgb,palette,masks)
    real_outline,provenance=optional_native_contour(outline_archive)
    ink=real_outline if real_outline is not None else np.zeros(bg.shape,bool)
    field,model_provenance=real_dino_features(rgb,model_dir)
    vectors=region_embeddings(field,regions)
    guide=real_outline is not None
    variant_specs=[
       ("D0_MATH_COLOR_GRAPH",None,guide),
       ("D1_REAL_DINOV2_CONTEXT",vectors,guide),
       ("D1_REAL_DINOV2_NO_CONTOUR",vectors,False)]
    outputs,details={},{}
    for name,vec,with_contour in variant_specs:
        outputs[name],details[name]=choose_colors(
            rgb,palette,regions,ink,vec,with_contour)
    metric={name:metrics(rgb,value,palette) for name,value in outputs.items()}
    metric["B0_ORIGINAL_G32"]=metrics(rgb,g32,palette)
    baseline=metric["B0_ORIGINAL_G32"]
    gates={}
    for name,item in metric.items():
        if name=="B0_ORIGINAL_G32":continue
        drift=int(np.count_nonzero((outputs[name]==BG)!=(g32==BG)))
        gates[name]={
          "regions_at_most_75pct_B0":item["components4"]<=.75*baseline["components4"],
          "deltaE00_mean_le_B0_plus1":item["mean_deltaE00"]<=baseline["mean_deltaE00"]+1.,
          "deltaE00_p95_le_B0_plus2":item["p95_deltaE00"]<=baseline["p95_deltaE00"]+2.,
          "background_mismatch_le2pct":drift<=.02*g32.size,
          "palette_le32":item["palette_colors_used"]<=32}
    delta=int(np.count_nonzero(outputs["D0_MATH_COLOR_GRAPH"]!=outputs["D1_REAL_DINOV2_CONTEXT"]))
    output.mkdir(parents=True)
    Image.fromarray(rgb,"RGB").save(output/"original-RGB.png")
    Image.fromarray(palette[g32],"RGB").save(output/"B0-G32-RGB.png")
    for name,index in outputs.items():
        Image.fromarray(index,"L").save(output/(name+"-indices.png"))
        Image.fromarray(palette[index],"RGB").save(output/(name+"-RGB.png"))
    np.savez_compressed(output/"real-dinov2-dense-features.npz",
                        dense=field,regions=vectors.astype(np.float32))
    hashes={p.name:sha(p) for p in output.iterdir() if p.is_file()}
    report={"experiment":EXPERIMENT,
            "status":"SOURCE_CANDIDATE_VISUAL_PENDING" if delta and
                   any(all(x.values()) for x in gates.values()) else "SOURCE_QUALITY_FAIL",
            "genuine_neural_encoder":"PRETRAINED_DINOV2_SMALL",
            "learned_32_color_palette_head":"NOT_TRAINED",
            "checkpoint":model_provenance,"source_sha256":SOURCE_SHA,
            "palette_blob":PALETTE_BLOB,
            "original_sam2_mask_count":len(masks),
            "original_source_regions":info,
            "V44_B_native_original_contour":provenance,
            "original_410_contours_unchanged":True,
            "D0_D1_neural_changed_pixels":delta,
            "D0_D1_neural_impact_proven":delta>0,
            "solver_details":details,"source_metrics":metric,"source_gates":gates,
            "user_visual_review":"PENDING","native_Egret":"NOT_RUN",
            "game_E4":"NOT_RUN","independent_E5":"NOT_RUN",
            "exact_CHALK":None,"production_accepted":False,
            "github_sha":os.getenv("GITHUB_SHA"),
            "github_run_id":os.getenv("GITHUB_RUN_ID"),
            "output_file_sha256":hashes}
    (output/"report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n")
    return report


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    for x in ("source","palette","s1-archive","model-dir","output"):
        ap.add_argument("--"+x,type=Path,required=True)
    ap.add_argument("--v44b-archive",type=Path)
    q=ap.parse_args()
    r=run(q.source,q.palette,q.s1_archive,q.v44b_archive,q.model_dir,q.output)
    print(json.dumps({"status":r["status"],"neural_changed_pixels":r["D0_D1_neural_changed_pixels"],
                      "gates":r["source_gates"]},ensure_ascii=False))

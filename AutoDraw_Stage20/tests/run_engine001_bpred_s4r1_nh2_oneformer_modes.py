#!/usr/bin/env python3
"""S4-R1 NH2: genuine pinned OneFormer semantic/instance/panoptic source-only.
No training, game color assignment, SAFE stroke map or semantic ground truth.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

from engine001_bpred_s4r1_generic_source_maps import decode_original, generic_source_maps
from run_engine001_bpred_s4r1_nh1_sam2_variants import (
    CORPUS, SAMPLES, git_blob, original_to_model_rgb, sha,
)

EXPERIMENT = "ENGINE001_BPRED_S4R1_NH2_ONEFORMER_NO_TRAIN_V1"
MODEL_ID = "shi-labs/oneformer_ade20k_swin_tiny"
MODEL_REVISION = "05f2812b1eccf9909b3897777450f8d68148cafc"
WEIGHT_SHA = "909b07dbf4129c2bbb8df4498e35dcd46f305e3ec45329d3ff6d4f0360de27f3"
TASKS = ("semantic", "instance", "panoptic")
THRESHOLDS = (0.5, 0.3)
SEMANTIC_LABEL_LIMIT = 150


def safe_segments(segments):
    """Keep numeric segment provenance only; do not trust id2label names."""
    if segments is None:
        return []
    if not isinstance(segments,(list,tuple)):
        raise ValueError("BLOCKED_NH2_SEGMENTS_SHAPE")
    cleaned=[]
    for entry in segments:
        if not isinstance(entry,dict) or "id" not in entry:
            raise ValueError("BLOCKED_NH2_SEGMENTS_ID")
        x={}
        for k,v in entry.items():
            if isinstance(v,np.generic):
                v=v.item()
            if isinstance(v,(int,float,str,bool)) or v is None:
                x[str(k)]=v
        x["id"]=int(entry["id"])
        if x["id"] < 0:
            raise ValueError("BLOCKED_NH2_NEGATIVE_SEGMENT_ID")
        cleaned.append(x)
    if len({x["id"] for x in cleaned})!=len(cleaned):
        raise ValueError("BLOCKED_NH2_DUPLICATE_SEGMENT_ID")
    return cleaned


def validate_prediction(task: str, segmentation, segments_info,
                        rgba: np.ndarray, source_maps: dict) -> dict:
    if task not in TASKS:
        raise ValueError("BLOCKED_NH2_UNKNOWN_TASK")
    if (rgba.ndim!=3 or rgba.shape[-1]!=4 or rgba.dtype!=np.uint8
            or source_maps.get("owner_status")!="MISSING"
            or not source_maps["stroke_admission"].startswith("FORBIDDEN")):
        raise ValueError("BLOCKED_NH2_SOURCE_OR_OWNER_PROVENANCE")
    hw=rgba.shape[:2]
    segs=safe_segments(segments_info)
    if segmentation is None:
        if task=="semantic" or segs:
            raise ValueError("BLOCKED_NH2_MISSING_SEGMENTATION")
        arr=np.full(hw,-1,np.int32)
        valid=np.zeros(hw,bool)
        status="NO_SEGMENTS_NOT_MODEL_QUALITY_PASS"
    else:
        arr=np.asarray(segmentation)
        if (arr.shape!=hw or not np.issubdtype(arr.dtype,np.integer)
                or np.any(arr < -1)):
            raise ValueError("BLOCKED_NH2_SEGMENTATION_SHAPE_OR_IDS")
        arr=arr.astype(np.int32)
        if task=="semantic":
            if len(segs) or arr.min()<0 or arr.max()>=SEMANTIC_LABEL_LIMIT:
                raise ValueError("BLOCKED_NH2_SEMANTIC_CLASS_RANGE")
            valid=np.ones(hw,bool)
            status="REAL_SEMANTIC_PSEUDOLABELS_ONLY"
        else:
            known_ids=set(x["id"] for x in segs)
            if np.any((arr>=0)&~np.isin(arr,np.asarray(sorted(known_ids),np.int32))):
                raise ValueError("BLOCKED_NH2_UNBOUND_INSTANCE_SEGMENT_ID")
            valid=arr>=0
            status="REAL_INSTANCE_PANOPTIC_PSEUDOLABELS_ONLY" if known_ids else "NO_SEGMENTS_NOT_MODEL_QUALITY_PASS"
    boundary=np.zeros(hw,bool)
    if hw[0]>1:
        e=(arr[:-1]!=arr[1:])&valid[:-1]&valid[1:]
        boundary[:-1]|=e;boundary[1:]|=e
    if hw[1]>1:
        e=(arr[:,:-1]!=arr[:,1:])&valid[:,:-1]&valid[:,1:]
        boundary[:,:-1]|=e;boundary[:,1:]|=e
    near=ndimage.binary_dilation(
        source_maps["source_edge"],structure=ndimage.generate_binary_structure(2,1))
    unique,counts=np.unique(arr[valid],return_counts=True)
    ids={str(int(i)):int(n) for i,n in zip(unique,counts)}
    return {
        "status":status, "label_or_segment_counts":ids,
        "distinct_ids":len(ids),
        "segments_info":segs,
        "selected_pixels":int(valid.sum()),
        "selected_invalid_original_alpha_pixels":int((valid&(rgba[:,:,3]<255)).sum()),
        "boundary_pixels":int(boundary.sum()),
        "boundary_near_source_rgb_edge":int((boundary&near).sum()),
        "boundary_near_source_rgb_edge_ratio":round(float((boundary&near).sum()/boundary.sum()),8) if boundary.any() else None,
        "source_owner_status":"MISSING", "semantic_reference":"PSEUDOLABEL_NOT_INDEPENDENT_GT",
        "stroke_admission":"FORBIDDEN_UNTIL_NATIVE_INDEPENDENT_VALIDATION",
        "native_E3":"NOT_RUN","game_E4":"NOT_RUN","exact_CHALK":None,
        "labels":arr,
    }


def preview(labels: np.ndarray) -> np.ndarray:
    """Display-only RGB, not a game palette mapping."""
    h,w=labels.shape
    out=np.full((h,w,3),248,np.uint8)
    for label in np.unique(labels):
        if label<0:continue
        n=int(label)+1
        out[labels==label]=[(53*n+31)%256,(97*n+67)%256,(193*n+13)%256]
    return out


def serialize_prediction(parent: Path,name: str,validated: dict,meta: dict) -> dict:
    if parent.exists():
        raise ValueError("BLOCKED_NH2_NO_OUTPUT_OVERWRITE")
    parent.mkdir(parents=True)
    arr=validated["labels"]
    np.savez_compressed(parent/"model_raw_segment_ids.npz",labels=arr)
    Image.fromarray(preview(arr),"RGB").save(parent/"model_segment_preview.png")
    result={k:v for k,v in validated.items() if k!="labels"}
    result["name"]=name
    result["actual_pretrained_inference"]=True
    result["metadata"]=meta
    result["sha256"]={x.name:sha(x) for x in parent.iterdir() if x.is_file()}
    return result


def run(root:Path,output:Path)->dict:
    if output.exists():
        raise ValueError("BLOCKED_NH2_NO_OVERWRITE")
    import torch
    from transformers import OneFormerProcessor, OneFormerForUniversalSegmentation
    from huggingface_hub import snapshot_download

    checkpoint_dir=Path(snapshot_download(
        repo_id=MODEL_ID, revision=MODEL_REVISION,
        allow_patterns=["*.json","*.txt","*.bin"],
    ))
    weight=checkpoint_dir/"pytorch_model.bin"
    if not weight.is_file() or sha(weight)!=WEIGHT_SHA or weight.stat().st_size<100_000_000:
        raise ValueError("BLOCKED_NH2_MODEL_WEIGHTS_PROVENANCE")
    processor=OneFormerProcessor.from_pretrained(str(checkpoint_dir))
    model=OneFormerForUniversalSegmentation.from_pretrained(
        str(checkpoint_dir), use_safetensors=False,
    ).eval().to("cpu")
    torch.manual_seed(0)
    torch.set_num_threads(2)
    output.mkdir(parents=True)
    report={
        "experiment":EXPERIMENT,"no_training":True,"model_id":MODEL_ID,
        "model_revision":MODEL_REVISION,"actual_checkpoint_sha256":sha(weight),
        "source_original_first":True, "task_modes":list(TASKS),
        "fixed_postprocess_thresholds":list(THRESHOLDS),
        "model_id2label_class_names":"UNVERIFIED_DO_NOT_USE",
        "semantic_ground_truth":"MISSING",
        "original_game_color_owner":"MISSING",
        "s4_strict":"BLOCKED",
        "stroke_admission":"FORBIDDEN_UNTIL_NATIVE_INDEPENDENT_VALIDATION",
        "github_sha":os.getenv("GITHUB_SHA"),"github_run_id":os.getenv("GITHUB_RUN_ID"),
        "native_E3":"NOT_RUN","game_E4":"NOT_RUN","independent_E5":"NOT_RUN",
        "exact_CHALK":None,"production_accepted":False,"records":[]
    }
    def persist():
        (output/"manifest.json").write_text(
            json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf8")
    persist()
    t0=time.monotonic()
    for name,role,expected_blob in SAMPLES:
        raw=(root/CORPUS/name).read_bytes()
        if git_blob(raw)!=expected_blob:
            raise ValueError("BLOCKED_NH2_FROZEN_SOURCE_BLOB:"+name)
        data=decode_original(raw)
        rgba=data["rgba"]
        original_rgba_sha=hashlib.sha256(rgba.tobytes()).hexdigest()
        view=original_to_model_rgb(rgba)
        source=generic_source_maps(rgba)
        h,w=rgba.shape[:2]
        sample_dir=output/hashlib.sha256(name.encode()).hexdigest()[:12]
        sample_dir.mkdir()
        Image.fromarray(view,"RGB").save(sample_dir/"original_model_view.png")
        rec={"file":name,"role":role,"source_sha256":data["sha256"],
             "source_git_blob_sha1":data["git_blob_sha1"],
             "source_rgba_sha256":original_rgba_sha,
             "original_hw":[h,w],"original_source_owner":"MISSING",
             "model_modes":[]}
        report["records"].append(rec)
        persist()
        for task in TASKS:
            start=time.monotonic()
            model_inputs=processor(images=Image.fromarray(view,"RGB"),
                                   task_inputs=[task],return_tensors="pt")
            with torch.inference_mode():
                outputs=model(**model_inputs)
            if task=="semantic":
                labels=processor.post_process_semantic_segmentation(
                    outputs,target_sizes=[(h,w)]
                )[0].cpu().numpy().astype(np.int32)
                checked=validate_prediction(task,labels,[],rgba,source)
                rec["model_modes"].append(serialize_prediction(
                    sample_dir/f"{task}_oneformer",task,checked,
                    {"model_task_token":task,"threshold":None,
                     "seconds_forward_and_postprocess":round(time.monotonic()-start,3)}))
            else:
                for threshold in THRESHOLDS:
                    if task=="instance":
                        res=processor.post_process_instance_segmentation(
                            outputs,task_type="instance",
                            threshold=threshold,mask_threshold=0.5,
                            target_sizes=[(h,w)]
                        )[0]
                    else:
                        res=processor.post_process_panoptic_segmentation(
                            outputs,threshold=threshold,mask_threshold=0.5,
                            target_sizes=[(h,w)]
                        )[0]
                    if not isinstance(res,dict):
                        raise ValueError("BLOCKED_NH2_UPSTREAM_POSTPROCESS_SHAPE")
                    segmentation=res.get("segmentation")
                    if hasattr(segmentation,"cpu"):segmentation=segmentation.cpu().numpy()
                    checked=validate_prediction(
                        task,segmentation,res.get("segments_info"),rgba,source)
                    label=f"{task}_threshold_{str(threshold).replace('.','p')}"
                    rec["model_modes"].append(serialize_prediction(
                        sample_dir/label,label,checked,
                        {"model_task_token":task,"threshold":threshold,
                         "mask_threshold":0.5,
                         "seconds_inference_and_postprocess":round(time.monotonic()-start,3)}))
            persist()
        if original_rgba_sha!=hashlib.sha256(rgba.tobytes()).hexdigest():
            raise ValueError("BLOCKED_NH2_ORIGINAL_CHANGED")
        rec["sample_sha256"]={x.name:sha(x) for x in sample_dir.iterdir() if x.is_file()}
        persist()
    report["runtime_seconds"]=round(time.monotonic()-t0,3)
    report["research_only_outcome"]="REAL_TASK_MODES_INSPECT_ONLY_NO_VERIFIED_SEMANTIC_GT"
    persist()
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    r=run(a.root,a.output)
    print(json.dumps({"outcome":r["research_only_outcome"],
        "models":[(x["file"],p["name"],p["distinct_ids"])
                  for x in r["records"] for p in x["model_modes"]],
        "runtime_seconds":r["runtime_seconds"],
        "s4_strict":r["s4_strict"]},ensure_ascii=False,allow_nan=False))

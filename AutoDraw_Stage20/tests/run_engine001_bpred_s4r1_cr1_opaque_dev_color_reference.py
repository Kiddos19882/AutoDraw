#!/usr/bin/env python3
"""S4R1 CR1: exactly 14 non-heldout opaque DEV source contrast audits.

Validation review-only packet, no semantic labels, game owners or strokes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from engine001_bpred_s4r1_original_rgb_pair_reference import (
    score_original_rgb_reference, THRESHOLD, VERSION,
)
from engine001_bpred_s4r1_generic_source_maps import (
    decode_original, generic_source_maps, original_source_region_uncertainty,
)
from run_engine001_bpred_s4r1_corpus_integrity import manifest, REL_CORPUS, REL_E0

EXPERIMENT = "ENGINE001_BPRED_S4R1_CR1_OPAQUE_DEV_RAW_RGB_REFERENCE"
EXPECTED_OPAQUE_DEV = 14
EXPECTED_ALPHA_DEV = "Sanrio_Characters_Hello_Kitty_Image026.webp"


def sha(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preview(original:np.ndarray, reference:np.ndarray,
            missed:np.ndarray, core:np.ndarray)->np.ndarray:
    """Original-source pixels remain unchanged in original png; overlay is DISPLAY ONLY."""
    out=original[:,:,:3].copy()
    # Core first (teal), raw reference protected (yellow), missed contrast (red).
    # Priorities prevent missed (red) from hiding under geometrical candidate core.
    out[core]=np.clip(
        np.rint(out[core].astype(np.float64)*.55
                + np.array([0,190,192])*.45),0,255).astype(np.uint8)
    out[reference]=np.array([255,212,38],np.uint8)
    out[missed]=np.array([255,34,40],np.uint8)
    return out


def run(root:Path, output:Path)->dict:
    if output.exists():
        raise ValueError("BLOCKED_CR1_NO_OVERWRITE_OUTPUT")
    entries=manifest(root/REL_E0)
    dev=[r for r in entries if r["role"]=="DEV"]
    if len(dev)!=15:
        raise ValueError("BLOCKED_CR1_FROZEN_DEV_ROLE_COUNT")
    output.mkdir(parents=True)
    report={
        "experiment":EXPERIMENT, "reference_version":VERSION,
        "original_rgb_threshold":THRESHOLD,
        "expected_opaque_dev":EXPECTED_OPAQUE_DEV,
        "model_inference":"NOT_RUN",
        "human_semantic_reference":"NOT_ANNOTATED_NEEDS_INDEPENDENT_VALIDATION",
        "source_owner":"MISSING",
        "all_strokes":"FORBIDDEN_UNTIL_NATIVE_INDEPENDENT_VALIDATION",
        "strict_s4":"BLOCKED",
        "heldout_outputs":0,
        "production_accepted":False,
        "game_E4":"NOT_RUN","exact_CHALK":None,
        "records":[],
    }
    skipped=[]
    for entry in dev:
        p=root/REL_CORPUS/entry["file"]
        raw=p.read_bytes()
        decoded=decode_original(raw)
        if len(raw)!=entry["bytes"] or decoded["git_blob_sha1"]!=entry["git_blob"]:
            raise ValueError("BLOCKED_CR1_FROZEN_DEV_SOURCE_CHANGED:"+entry["file"])
        rgba=decoded["rgba"]
        if np.any(rgba[:,:,3]<255):
            skipped.append(entry["file"])
            continue
        maps=generic_source_maps(rgba)
        regions=original_source_region_uncertainty(rgba,maps)
        result=score_original_rgb_reference(rgba,maps,regions)
        endpoints=result.pop("reference_endpoints")
        missed=result.pop("reference_missed")
        core=regions["geometric_potential_core"]
        key=hashlib.sha256(entry["file"].encode()).hexdigest()[:12]
        source_out=output/(key+"_original_source_RGB.png")
        overlay_out=output/(key+"_review_contrast_protection_core.png")
        Image.fromarray(rgba[:,:,:3],"RGB").save(source_out)
        Image.fromarray(preview(rgba,endpoints,missed,core),"RGB").save(overlay_out)
        record={
            "file":entry["file"],"role":entry["role"],
            "original_source_raw_sha256":decoded["sha256"],
            "original_source_git_blob_sha1":decoded["git_blob_sha1"],
            "original_rgba_sha256":result["source_rgba_sha256"],
            "original_hw":[decoded["height"],decoded["width"]],
            "source_regions":int(regions["counts"]["regions"]),
            "existing_source_geometric_potential_core":int(core.sum()),
            "reference":result,
            "review_packet_png_sha256":{
                source_out.name:sha(source_out),
                overlay_out.name:sha(overlay_out),
            },
            "review_colors":{
                "teal":"geometric_potential_core_UNKNOWN_NOT_PAINT_SAFE",
                "yellow":"raw_RGB_contrast_pair_endpoint_existing_protection",
                "red":"raw_RGB_contrast_pair_endpoint_NOT_PROTECTED_RISK_PROXY",
            },
            "review_status":"NEEDS_INDEPENDENT_SEMANTIC_HUMAN_VERIFICATION",
            "source_game_owner_status":"MISSING",
            "stroke_admission":"FORBIDDEN_UNTIL_NATIVE_INDEPENDENT_VALIDATION",
        }
        report["records"].append(record)
    if (len(report["records"])!=EXPECTED_OPAQUE_DEV
            or skipped!=[EXPECTED_ALPHA_DEV]):
        raise ValueError("BLOCKED_CR1_NOT_FROZEN_14_OPAQUE_DEV:"+repr(skipped))
    report["excluded_alpha_dev"]=skipped
    report["counts"]={
        "opaque_dev":len(report["records"]),
        "source_contrast_endpoints":sum(x["reference"]["source_contrast_endpoints"]
                                       for x in report["records"]),
        "source_contrast_protected":sum(x["reference"]["source_contrast_protected_endpoints"]
                                      for x in report["records"]),
        "source_contrast_unprotected":sum(x["reference"]["source_contrast_unprotected_endpoints"]
                                        for x in report["records"]),
        "source_contrast_geometric_potential_core_overlap":sum(
            x["reference"]["source_contrast_geometric_potential_core_overlap"]
            for x in report["records"]),
        "source_geometric_potential_core_pixels":sum(
            x["existing_source_geometric_potential_core"] for x in report["records"]),
        "reference_not_applicable":sum(x["reference"]["source_contrast_endpoints"]==0
                                      for x in report["records"]),
        "diagnostic_failure_images":sum(
            x["reference"]["source_contrast_unprotected_endpoints"]>0
            for x in report["records"]),
    }
    report["scientific_status"]=(
        "SOURCE_CONTRAST_DIAGNOSTIC_FAIL" if report["counts"]["source_contrast_unprotected"]>0
        else "PASS_SOURCE_CONTRAST_REFERENCE_ONLY_NOT_SEMANTIC"
    )
    assert len(list(output.glob("*.png")))==28
    (output/"cr1_report.json").write_text(
        json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf8")
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    report=run(a.root,a.output)
    print(json.dumps({"technical":"CR1_COMPLETED_14_DEV_ONLY",
        "scientific":report["scientific_status"],"counts":report["counts"],
        "owner":"MISSING","stroke":"FORBIDDEN",
        "native_E3":"NOT_RUN","game_E4":"NOT_RUN"},ensure_ascii=False))

#!/usr/bin/env python3
"""ENGINE-001/BPRED-S3v2l: frozen isolated original Egret RGB premultiply-byte lattice.
Offline E2 on 40 signed original isolated S3v2j captures, NOT new native E3.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import run_engine001_bpred_s3v2k_owner_alpha_interval as prev

EXPERIMENT = "ENGINE001_BPRED_S3V2L_ISOLATED_NATIVE_RGB_BYTE_LATTICE_V1"
E0_BLOB = "85ea039ad6b1683b40297ed307ec750c021b4630"
E0_FILE = "ENGINE001_BPRED001_S3V2L_ISOLATED_RGB_PREMULT_LATTICE_PREREG_2026-11-20.md"
PREV_RUN = "44741517301"
PREV_SHA = "88e53c1205e163fd86db9251bb168f2be491fb97"
F1_MODES = ("floor","nearest_even","ceil")
ALPHA_BINS = ((0,0),(1,15),(16,63),(64,127),(128,254),(255,255))
RGB_PADDING = 2.


def blocked(reason):
    raise ValueError("BLOCKED_BPRED_S3V2L_"+reason)


def check_negative_archive(z):
    members=z.namelist()
    if (len(members)!=4 or len(set(members))!=4 or z.testzip() is not None
            or any(n.startswith("/") or "\\" in n or ".." in Path(n).parts for n in members)):
        blocked("PRIOR_NEGATIVE_ARCHIVE_CRC_OR_SET")
    report=json.loads(z.read("report.json"))
    frozen={
        "experiment":prev.EXPERIMENT,"E0_blob":prev.E0_BLOB,
        "source_sha":prev.SOURCE_SHA,"source_run":prev.SOURCE_RUN,
        "github_sha":PREV_SHA,"github_run_id":PREV_RUN,
        "original_C0_canvas_pass_40":31,"original_C0_QH_webgl_pass_40":21,
        "QH_stage_RGB_mismatch":0,"QH_stage_alpha_mismatch":0,
        "source_hidden_alpha0_changed_owner_pixels":21,
        "I1_full_image_source_owner_pixel_misses":3186,
        "D2_full_source_owner_interval":"FAIL",
        "S0_BLIND_used":False,"production_promotion":False
    }
    if any(report.get(name)!=value for name,value in frozen.items()):
        blocked("PRIOR_S3V2K_SCIENCE_OR_PROVENANCE_DRIFT")
    hashes=report.get("members_sha256")
    if not isinstance(hashes,dict) or len(hashes)!=3 or set(hashes)!=set(members)-{"report.json"}:
        blocked("PRIOR_S3V2K_HASH_SET")
    for name,sign in hashes.items():
        if prev.digest(z.read(name))!=sign:
            blocked("PRIOR_S3V2K_MEMBER_SHA_"+name)
    previous=json.loads(z.read("ALL_I1_OUT_OF_ENVELOPE_PIXELS.json"))
    if len(previous)!=3186:
        blocked("PRIOR_3186_NEGATIVE_PIXELS_DRIFT")
    support={"top_only":0,"bottom_only":0,"overlap":0,"other":0}
    for p in previous:
        b,t=p["source_bottom_RGBA"][3],p["source_top_RGBA"][3]
        category=("top_only" if b==0 and t>0 else
                  "bottom_only" if t==0 and b>0 else
                  "overlap" if b>0 and t>0 else "other")
        support[category]+=1
    if support!={"top_only":1580,"bottom_only":1580,"overlap":26,"other":0}:
        blocked("PRIOR_SUPPORT_COUNTS_DRIFT")
    if len(json.loads(z.read("ALL_21_ALPHA0_OWNER_RISK_AUDIT.json")))!=21:
        blocked("PRIOR_OWNER_DAMAGE_LIST_DRIFT")
    if len(json.loads(z.read("ALL_40_SOURCE_OWNER_INTERVAL_CASES.json")))!=40:
        blocked("PRIOR_40_ORDERED_CASES_DRIFT")
    return support


def premul_roundtrip(color,alpha,mode):
    """Fixed F1: premult byte from native exported A and owner source RGB, half-up readback."""
    color=np.asarray(color,dtype=np.float64)
    a=np.asarray(alpha,dtype=np.float64)
    if color.shape!=(3,) or not np.all(np.isfinite(color)) or np.any(color<0) or np.any(color>255):
        blocked("INVALID_SOURCE_OWNER_COLOR")
    if a.ndim!=1 or np.any(a<=0) or np.any(a>255):
        blocked("F1_ALPHA_SHAPE_OR_ZERO")
    if mode not in F1_MODES:
        blocked("F1_UNFROZEN_ROUNDING")
    f=color[None,:]*a[:,None]/255.
    premul={"floor":np.floor,"nearest_even":np.rint,"ceil":np.ceil}[mode](f)
    return np.clip(np.floor(255.*premul/a[:,None]+.5),0,255).astype(np.uint8)


def f2_lattice_interval(color,alpha):
    """F2: ±.5 true alpha byte endpoints, floor/nearest/ceil p, half-up readback; ±2 envelope."""
    color=np.asarray(color,dtype=np.float64)
    a=np.asarray(alpha,dtype=np.float64)
    if color.shape!=(3,) or a.ndim!=1 or np.any(a<=0) or np.any(a>=255):
        blocked("F2_PARTIAL_ALPHA_ONLY")
    lower=np.full((len(a),3),np.inf)
    upper=np.full((len(a),3),-np.inf)
    for real_a in (np.maximum(0.,a-.5),np.minimum(255.,a+.5)):
        if np.any(real_a<=0):
            blocked("F2_UNDEFINED_ALPHA_INTERVAL")
        premul=color[None,:]*real_a[:,None]/255.
        for fn in (np.floor,np.rint,np.ceil):
            p=fn(premul)
            rgb=np.clip(np.floor(255.*p/real_a[:,None]+.5),0,255)
            lower=np.minimum(lower,rgb)
            upper=np.maximum(upper,rgb)
    return np.maximum(0.,lower-RGB_PADDING),np.minimum(255.,upper+RGB_PADDING)


def case_isolated(z,case):
    if case["variant"] not in ("A_ONLY","B_ONLY") or len(case["source_strokes"])!=1:
        blocked("ISOLATED_SOURCE_OWNER_EXPECTED")
    image=prev.rgba(z,case,"ALIGNED_MAIN_RGBA")
    color=prev.rgb_owner(case["source_strokes"][0])
    alpha=image[:,:,3]
    ys,xs=np.where((alpha>0)&(alpha<255))
    rgba=image[ys,xs]
    if rgba.size==0:
        blocked("PARTIAL_ALPHA_MISSING_"+case["sample_id"])
    ca=rgba[:,3]
    actual=rgba[:,:3].astype(np.int16)
    rgba_source_rgb=color.astype(np.int16)
    original_abs=np.abs(actual-rgba_source_rgb[None,:])
    initial_owner_missed=np.any(original_abs>2,axis=1)
    f1={}
    f1_pred={}
    for mode in F1_MODES:
        predictions=premul_roundtrip(color,ca,mode)
        f1_pred[mode]=predictions
        difference=np.abs(predictions.astype(np.int16)-actual)
        f1[mode]={
            "exact_RGB_physical_pixels":int((difference==0).all(axis=1).sum()),
            "RGB_mismatch_physical_pixels":int(np.any(difference!=0,axis=1).sum()),
            "max_absolute_channel_byte":int(difference.max(initial=0)),
            "sum_absolute_RGB_bytes":int(difference.sum())
        }
    low,high=f2_lattice_interval(color,ca)
    f2_contains=(actual.astype(np.float64)>=low-1e-9)&(actual.astype(np.float64)<=high+1e-9)
    misses=np.any(~f2_contains,axis=1)
    width=high-low
    confidence=(width<=16.).all(axis=1)
    qualifying=ca>=16
    all_misses=[]
    for i in np.flatnonzero(misses):
        i=int(i)
        all_misses.append({
            "sample_id":case["sample_id"],"width":case["width"],
            "relation":case["relation"],"variant":case["variant"],
            "native_physical_xy":[int(xs[i]),int(ys[i])],
            "original_owner_RGB":color.astype(np.uint8).tolist(),
            "actual_RGBA":rgba[i].tolist(),
            "F0_palette_absolute_RGB_error":original_abs[i].tolist(),
            "F1_fixed_candidates_RGB":{m:f1_pred[m][i].tolist() for m in F1_MODES},
            "F2_lower_RGBA_RGB":low[i].tolist(),"F2_upper_RGBA_RGB":high[i].tolist(),
            "F2_missed_RGB_channels":(~f2_contains[i]).tolist()
        })
    opaque=alpha==255
    if not np.any(opaque):
        blocked("OPAQUE_CONTROL_ABSENT_"+case["sample_id"])
    opaque_error=np.any(image[:,:,:3]!=color[None,None,:],axis=2)&opaque
    buckets={}
    for amin,amax in ALPHA_BINS:
        key=str(amin) if amin==amax else f"{amin}..{amax}"
        if amin==0:
            m=(alpha==0)
            buckets[key]={"pixels":int(m.sum()),"F0_missed_physical_pixels":None,
                          "F2_missed_physical_pixels":None,"F2_unknown":True}
        elif amin==255:
            m=opaque
            buckets[key]={"pixels":int(m.sum()),"F0_missed_physical_pixels":int(opaque_error.sum()),
                          "F2_missed_physical_pixels":None,"F2_unknown":False}
        else:
            m=(ca>=amin)&(ca<=amax)
            buckets[key]={
                "pixels":int(m.sum()),
                "F0_missed_physical_pixels":int((m&initial_owner_missed).sum()),
                "F2_missed_physical_pixels":int((m&misses).sum()),
                "F2_confident_width_le_16_RGB_channels":int((m&confidence).sum()),
                "F2_all_RGB_interval_width_max":float(width[m].max(initial=0.))
            }
    return {
        "sample_id":case["sample_id"],"width":case["width"],
        "relation":case["relation"],"variant":case["variant"],
        "color_rgb":color.astype(np.uint8).tolist(),
        "source_plan_sha256":case["source_plan_sha256"],
        "runtime_plan_sha256":case["runtime_plan_sha256"],
        "partial_alpha_pixels":int(len(ca)),
        "F0_palette_rgb_gt2_physical_pixels":int(initial_owner_missed.sum()),
        "F0_max_absolute_rgb_byte":int(original_abs.max(initial=0)),
        "F1_fixed_candidates":f1,
        "F2_missed_physical_pixels":int(misses.sum()),
        "F2_confident_alpha_ge16_pixels":int(qualifying.sum()),
        "F2_confident_alpha_ge16_width_le16_pixels":int((qualifying&confidence).sum()),
        "F3_native_opaque_pixels":int(opaque.sum()),
        "F3_native_opaque_owner_RGB_different_pixels":int(opaque_error.sum()),
        "alpha_bins":buckets
    },all_misses


def run(source_zip,negative_zip,output,workspace=None):
    if output.exists():
        blocked("OUTPUT_EXISTS")
    if workspace is not None:
        p=workspace/"AutoDraw_Stage20"/"docs"/E0_FILE
        if not p.is_file():
            blocked("PREREG_UNAVAILABLE")
        raw=p.read_bytes()
        git=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
        if git!=E0_BLOB:
            blocked("PREREG_BLOB_DRIFT")
    with ZipFile(source_zip) as z,ZipFile(negative_zip) as nz:
        scenes,risks=prev.check_parent(z)
        frozen_support=check_negative_archive(nz)
        output.mkdir(parents=True)
        rows=[];failures=[]
        for w in prev.WIDTHS:
            for relation in prev.RELATIONS:
                for v in ("A_ONLY","B_ONLY"):
                    case=scenes[(w,relation,v)]
                    rec,bad=case_isolated(z,case)
                    rows.append(rec);failures.extend(bad)
        if len(rows)!=40 or len({r["sample_id"] for r in rows})!=40:
            blocked("ISOLATED_MATRIX_CARDINALITY")
        partial=sum(r["partial_alpha_pixels"] for r in rows)
        f0=sum(r["F0_palette_rgb_gt2_physical_pixels"] for r in rows)
        f2=sum(r["F2_missed_physical_pixels"] for r in rows)
        opaque=sum(r["F3_native_opaque_pixels"] for r in rows)
        opaque_errors=sum(r["F3_native_opaque_owner_RGB_different_pixels"] for r in rows)
        confident_total=sum(r["F2_confident_alpha_ge16_pixels"] for r in rows)
        confident=sum(r["F2_confident_alpha_ge16_width_le16_pixels"] for r in rows)
        if (len(failures)!=f2 or opaque<=0 or partial<=0 or confident_total<=0):
            blocked("RESULT_CARDINALITY")
        f1={m:{"exact_RGB_physical_pixels":sum(row["F1_fixed_candidates"][m]["exact_RGB_physical_pixels"] for row in rows),
               "RGB_mismatch_physical_pixels":sum(row["F1_fixed_candidates"][m]["RGB_mismatch_physical_pixels"] for row in rows),
               "max_absolute_channel_byte":max(row["F1_fixed_candidates"][m]["max_absolute_channel_byte"] for row in rows)}
            for m in F1_MODES}
        prev.write_json(output/"ALL_40_TRUE_NATIVE_ISOLATED_OWNER_RGB_CASES.json",rows)
        prev.write_json(output/"ALL_F2_PHYSICAL_RGB_OUTSIDE_FIXED_LATTICE.json",failures)
        report={
            "experiment":EXPERIMENT,"E0_blob":E0_BLOB,
            "github_sha":os.getenv("GITHUB_SHA"),"github_run_id":os.getenv("GITHUB_RUN_ID"),
            "source_sha":prev.SOURCE_SHA,"source_run":prev.SOURCE_RUN,
            "source_archive_crc_sha_members":856,"prior_s3v2k_run":PREV_RUN,
            "prior_s3v2k_sha":PREV_SHA,"prior_negative_output_sha_members":3,
            "prior_s3v2k_D2_misses":3186,"prior_support":frozen_support,
            "original_C0_canvas_pass_40":31,"original_C0_QH_webgl_pass_40":21,
            "source_hidden_alpha0_changed_owner_pixels":21,
            "isolate_scenes":40,"partial_alpha_physical_pixels":partial,
            "F0_original_palette_RGB_gt2_pixels":f0,"F1_exact_roundtrip_modes":f1,
            "F2_lattice_outside_physical_pixels":f2,
            "F2_confident_16to254_total":confident_total,
            "F2_confident_16to254_width_le16":confident,
            "F2_confident_fraction":confident/confident_total,
            "F3_alpha255_physical_pixels":opaque,"F3_opaque_wrong_owner_RGB_pixels":opaque_errors,
            "D0_original_source_and_prior_3186_integrity":"PASS",
            "D1_opaque_owner_RGB_exact":"PASS" if opaque_errors==0 else "FAIL",
            "D2_fixed_lattice_RGB_full_coverage":"PASS" if f2==0 else "FAIL",
            "D3_nonvacuous_lattice_width16_at_least90percent":"PASS" if 10*confident>=9*confident_total else "FAIL",
            "D4_original_C0_QH_and_owner_risk_unchanged":"PASS",
            "source_owner_safety":"MODEL_ONLY_UNKNOWN",
            "original_S3v2k_D2":"FAIL_UNCHANGED",
            "original_S3v2j_H3":"FAIL_UNCHANGED",
            "original_EF_protected_quality":"FAIL_UNCHANGED",
            "S0_BLIND_used":False,"new_native_E3":False,
            "E4_game":"NOT_RUN","E5_independent":"NOT_RUN",
            "exact_game_CHALK":None,"production_promotion":False
        }
        report["members_sha256"]={
            p.relative_to(output).as_posix():prev.digest(p.read_bytes())
            for p in sorted(output.rglob("*")) if p.is_file()}
        prev.write_json(output/"report.json",report)
        print("BPRED_S3V2L_ORIGINAL_INTEGRITY_PASS",partial,opaque,flush=True)
        print("BPRED_S3V2L_F0_F2",f0,f2,"F1",f1,flush=True)
        print("BPRED_S3V2L_DIAGNOSTIC_D1_D2_D3",
              report["D1_opaque_owner_RGB_exact"],
              report["D2_fixed_lattice_RGB_full_coverage"],
              report["D3_nonvacuous_lattice_width16_at_least90percent"],flush=True)
        return report


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source-zip",required=True,type=Path)
    p.add_argument("--negative-zip",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--workspace",type=Path)
    a=p.parse_args()
    run(a.source_zip,a.negative_zip,a.output,a.workspace)

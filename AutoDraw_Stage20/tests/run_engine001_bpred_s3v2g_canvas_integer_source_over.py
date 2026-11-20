#!/usr/bin/env python3
"""ENGINE-001 BPRED-S3v2g: preregistered byte-premultiplied Canvas C0.

Known, previously inspected genuine S3v2f Egret artifact only; NOT new-native,
S0 independent BLIND, game runtime, or a source quality safety acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import zipfile

import numpy as np
from PIL import Image

import run_engine001_bpred_s3_native_source_over as s3
import run_engine001_bpred_s3v2f_prospective_native_rgba8 as f

EXPERIMENT="ENGINE001_BPRED_S3V2G_KNOWN_SOURCE_CANVAS_INTEGER_C0_V1"
E0_FILE="ENGINE001_BPRED001_S3V2G_CANVAS_INTEGER_SOURCE_OVER_PREREG_2026-11-20.md"
E0_BLOB="9dd47155d284f63c81cbb525ad757b137c287f11"
PARENT_RUN="44710870514"
PARENT_SHA="819b7fd20272e5ac87ead72ce0610687fa51cbf4"
PARENT_E0="24259eeeadb9451c43390bdcf5a01fb67c7cf39a"
PARENT_EXPERIMENT="ENGINE001_BPRED_S3V2F_PROSPECTIVE_ORIGINAL_EGRET_RGBA8_V1"
PARENT_RUNNER_BLOB="0c3b799f6bc22958911d35420a30fef1950813dd"
SOURCE_OVER_BLOB="1bf56df9507f2a34fd16e68eef190229c3184ce5"
NAMES=("P0","P1","P2","P3")
BINS=((0,0),(1,15),(16,63),(64,127),(128,254),(255,255))


def blocked(label):
    raise ValueError("BLOCKED_BPRED_S3V2G_"+label)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


def save(path, data):
    with path.open("x",encoding="utf8") as stream:
        json.dump(data,stream,indent=2,ensure_ascii=False,allow_nan=False)
        stream.write("\n")


def byte_blend(bottom, top, mode):
    if (mode not in ("P1","P2","P3") or
            not isinstance(bottom,np.ndarray) or
            not isinstance(top,np.ndarray) or
            bottom.dtype!=np.uint8 or top.dtype!=np.uint8 or
            bottom.shape!=top.shape or bottom.ndim!=3 or bottom.shape[-1]!=4):
        blocked("UNFROZEN_BLEND_MODE_RGBA")
    fn={"P1":np.floor,"P2":np.rint,"P3":np.ceil}[mode]
    b=bottom.astype(np.float64)
    t=top.astype(np.float64)
    ba=b[:,:,3]
    ta=t[:,:,3]
    pb=fn(b[:,:,:3]*ba[:,:,None]/255.0)
    pt=fn(t[:,:,:3]*ta[:,:,None]/255.0)
    ao=fn(ta+ba*(255.0-ta)/255.0)
    po=fn(pt+pb*(255.0-ta[:,:,None])/255.0)
    po=np.maximum(0.0,np.minimum(po,ao[:,:,None]))
    rgb=np.zeros_like(po)
    np.divide(255.0*po,ao[:,:,None],out=rgb,where=ao[:,:,None]>0)
    rgb=np.floor(rgb+0.5)
    return np.rint(np.clip(np.dstack((rgb,ao)),0.0,255.0)).astype(np.uint8)


def source_image(z, sample_id, kind):
    if kind not in ("ALIGNED_MAIN_RGBA","REAL_WEBGL"):
        blocked("UNFROZEN_SOURCE_KIND")
    path=f"native/{sample_id}/{sample_id}_{kind}.png"
    try:
        raw=z.read(path)
    except KeyError:
        blocked("SOURCE_IMAGE_MISSING_"+sample_id)
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        blocked("SOURCE_PNG_INVALID")
    with Image.open(io.BytesIO(raw)) as im:
        img=np.array(im.convert("RGBA"),dtype=np.uint8)
    if img.shape != (720,1380,4):
        blocked("SOURCE_NATIVE_RGBA_SHAPE")
    return img[279:441,435:597,:].copy()


def feasible_lookup():
    """Number of byte premul candidates yielding a straight half-up RGBA byte."""
    out=np.zeros((256,256),np.uint8)
    for a in range(1,255):
        for p in range(a+1):
            c=min(255,int(math.floor(255.0*p/a+0.5)))
            out[a,c]+=1
    return out


def unknown_pixels(img, lookup):
    if img.ndim!=3 or img.shape[-1]!=4 or img.dtype!=np.uint8:
        blocked("UNKNOWN_SOURCE_SHAPE")
    a=img[:,:,3]
    partial=(a>0)&(a<255)
    perchannel=lookup[a[:,:,None],img[:,:,:3]]
    ambiguous=np.any((perchannel!=1)&partial[:,:,None],axis=2)
    return {"fractional_alpha_pixels":int(partial.sum()),
            "unknown_fractional_rgba_pixels":int(ambiguous.sum()),
            "zero_feasible_channels":int(np.count_nonzero((perchannel==0)&partial[:,:,None])),
            "multiple_feasible_channels":int(np.count_nonzero((perchannel>1)&partial[:,:,None]))}


def verify_native_parent(z, workspace):
    e0=workspace/"AutoDraw_Stage20"/"docs"/E0_FILE
    if not e0.is_file() or blob(e0.read_bytes())!=E0_BLOB:
        blocked("FROZEN_E0_GIT_BLOB")
    if blob(Path(s3.__file__).read_bytes())!=SOURCE_OVER_BLOB or (
            blob(Path(f.__file__).read_bytes())!=PARENT_RUNNER_BLOB):
        blocked("PARENT_S3_MODEL_SOURCE_DRIFT")
    names=z.namelist()
    if len(names)!=656 or len(set(names))!=656 or z.testzip() is not None:
        blocked("SOURCE_ARCHIVE_CRC_OR_MEMBER_COUNT")
    if any(name.startswith("/") or ".." in Path(name).parts or "\\" in name
           for name in names):
        blocked("SOURCE_ZIP_UNSAFE_PATH")
    r=json.loads(z.read("report.json"))
    if (r.get("experiment")!=PARENT_EXPERIMENT or
            r.get("github_sha")!=PARENT_SHA or str(r.get("github_run_id"))!=PARENT_RUN or
            r.get("E0_blob")!=PARENT_E0 or r.get("S0_BLIND_used") is not False or
            r.get("true_native_primary")!=80 or r.get("true_native_main_canvas_PNG")!=80 or
            r.get("true_native_mask_canvas_PNG")!=80 or
            r.get("true_native_final_webgl_PNG")!=91 or
            r.get("H1_QH_new_native_exact_stage")!="PASS" or
            r.get("H2_QH_source_over_at_least_30_of_40")!="FAIL" or
            r.get("D1_RGB_mismatch_by_mode")!={"Q0":17001,"QC":131,"QH":0} or
            r.get("D2_C0_pass_count_by_mode_40")!={"Q0":0,"QC":14,"QH":14} or
            r.get("D2_real_main_canvas_C0_pass_count_40")!=23 or
            r.get("S0_BLIND_used") is not False):
        blocked("SOURCE_REPORT_DRIFT")
    hashes=r.get("members_sha256")
    if (not isinstance(hashes,dict) or len(hashes)!=655 or
            set(hashes)!=set(names)-{"report.json"}):
        blocked("SOURCE_MEMBER_SET")
    for name,hash_ in hashes.items():
        if sha(z.read(name))!=hash_:
            blocked("SOURCE_MEMBER_SHA_"+name)
    src=json.loads(z.read("FROZEN_S3V2F_MANIFEST.json"))
    if (src.get("experiment")!=PARENT_EXPERIMENT or
            src.get("E0_blob")!=PARENT_E0 or
            src.get("S0_BLIND_used") is not False or
            src.get("source_game_blob")!=f.p4d3.ENGINE_GIT_BLOB or
            src.get("source_renderer_blob")!=f.p4d3.RENDERER_GIT_BLOB or
            src.get("new_primary")!=80 or src.get("replays")!=10 or
            src.get("blank")!=1 or src.get("final_webgl_PNG")!=91 or
            src.get("main_PNG")!=80 or src.get("mask_PNG")!=80):
        blocked("SOURCE_MANIFEST_METADATA_DRIFT")
    scenes=src.get("scenes")
    controls=src.get("controls")
    if (not isinstance(scenes,list) or len(scenes)!=80 or
            not isinstance(controls,list) or len(controls)!=10 or
            len({x["sample_id"] for x in scenes})!=80):
        blocked("SOURCE_MANIFEST_CARDINALITY_DRIFT")
    expected={(width,relation,variant) for width in f.WIDTHS
              for relation in f.RELATIONS for variant in f.VARIANTS}
    actual={(row["width"],row["relation"],row["variant"]) for row in scenes}
    if actual!=expected:
        blocked("SOURCE_MANIFEST_MATRIX_DRIFT")
    for row in scenes:
        sid=f'BPRED-S3V2F-W{row["width"]:02d}-{row["relation"]}-{row["variant"]}'
        if (row.get("sample_id")!=sid or
                row.get("source_plan_sha256")!=s3.digest(s3.canonical(row["source_strokes"])) or
                row.get("runtime_plan_sha256")!=s3.digest(s3.canonical(row["runtime_strokes"])) or
                json.loads(z.read(f"native/{sid}/SOURCE_PLAN.json"))!=row["source_strokes"] or
                json.loads(z.read(f"native/{sid}/RUNTIME_PLAN.json"))!=row["runtime_strokes"]):
            blocked("SOURCE_MANIFEST_PLAN_SHA_OR_BYTES_DRIFT")
    if {c["sample_id"] for c in controls}!={f"BPRED-S3V2F-REPLAY-W{w:02d}"
                                                 for w in f.WIDTHS}:
        blocked("SOURCE_MANIFEST_CONTROLS_DRIFT")
    # Original source runner is byte-pinned and every parent ZIP member hash is
    # verified above. Do not recompute original Windows trig on Linux: math.cos/
    # sin can legitimately vary by the last bit across platforms.
    return r


def metric(mode,bottom,top,target,mask):
    pred=(s3.source_over(bottom,top) if mode=="P0"
          else byte_blend(bottom,top,mode))
    stat,_=s3.rgba_difference(pred,target,mask)
    stat["frozen_H1_pass"]=bool(stat["max_channel_byte"]<=2 and
                                stat["mean_channel_byte"]<=1)
    diff=pred.astype(np.int16)-target.astype(np.int16)
    stat["alpha_different_pixels"]=int(np.count_nonzero(diff[:,:,3]))
    stat["rgb_different_pixels"]=int(np.any(diff[:,:,:3]!=0,axis=2).sum())
    stat["max_alpha_byte"]=int(np.abs(diff[:,:,3]).max(initial=0))
    return stat,pred


def run(workspace,source_zip,output):
    if output.exists():
        blocked("OUTPUT_EXISTS")
    if not source_zip.is_file():
        blocked("SOURCE_ZIP_MISSING")
    output.mkdir(parents=True)
    rows=[]; ident=[]; lookup=feasible_lookup()
    with zipfile.ZipFile(source_zip) as z:
        parent=verify_native_parent(z,workspace)
        for width in f.WIDTHS:
            for relation in f.RELATIONS:
                plans=f.plans_for(width,relation)
                frames={v:{
                    "canvas":source_image(z,plans[v]["sample_id"],"ALIGNED_MAIN_RGBA"),
                    "webgl":source_image(z,plans[v]["sample_id"],"REAL_WEBGL")}
                    for v in f.VARIANTS}
                for iso in ("A_ONLY","B_ONLY"):
                    src=frames[iso]["canvas"]
                    ident.append({"width":width,"relation":relation,"owner":iso,
                                  **unknown_pixels(src,lookup)})
                ordered={}
                for variant in ("A_THEN_B","B_THEN_A"):
                    a,b=frames["A_ONLY"]["canvas"],frames["B_ONLY"]["canvas"]
                    bottom,top=(a,b) if variant=="A_THEN_B" else (b,a)
                    target=frames[variant]
                    union=(a[:,:,3]>0)|(b[:,:,3]>0)|(
                        target["canvas"][:,:,3]>0)|(
                        target["webgl"][:,:,3]>0)
                    candidate={}
                    for name in NAMES:
                        cm,pred=metric(name,bottom,top,target["canvas"],union)
                        wm,_=s3.rgba_difference(f.quantize_half_up(pred),
                                                target["webgl"],union)
                        wm["frozen_H1_pass"]=bool(
                            wm["max_channel_byte"]<=2 and wm["mean_channel_byte"]<=1)
                        candidate[name]={"against_original_main_Canvas":cm,
                                         "QH_then_against_original_WebGL":wm}
                    ordered[variant]=candidate
                rows.append({"pair_id":f"BPRED-S3V2G-W{width:02d}-{relation}",
                             "width":width,"relation":relation,
                             "ordered_variants":ordered})
    if len(rows)!=20 or len(ident)!=40:
        blocked("SCENE_MATRIX_DRIFT")
    canvas_pass={m:sum(int(v[m]["against_original_main_Canvas"]["frozen_H1_pass"])
                     for row in rows for v in row["ordered_variants"].values()) for m in NAMES}
    webgl_pass={m:sum(int(v[m]["QH_then_against_original_WebGL"]["frozen_H1_pass"])
                    for row in rows for v in row["ordered_variants"].values()) for m in NAMES}
    if canvas_pass["P0"]!=23 or webgl_pass["P0"]!=14:
        blocked("FROZEN_BASELINE_C0_NOT_REPRODUCED")
    save(output/"C0_ALL_40_VARIANTS.json",rows)
    save(output/"D3_SOURCE_REPRESENTABILITY.json",ident)
    source_unknown=sum(x["unknown_fractional_rgba_pixels"] for x in ident)
    total_partial=sum(x["fractional_alpha_pixels"] for x in ident)
    report={
        "experiment":EXPERIMENT,"E0_blob":E0_BLOB,
        "github_sha":os.getenv("GITHUB_SHA"),"github_run_id":os.getenv("GITHUB_RUN_ID"),
        "parent_run":PARENT_RUN,"parent_sha":PARENT_SHA,
        "source_authentic_native":True,"new_native_E3":False,"S0_BLIND_used":False,
        "source_original_s3v2f_H1":"PASS_UNCHANGED",
        "source_original_s3v2f_H2":"FAIL_UNCHANGED",
        "D1_canvas_C0_pass_by_mode_40":canvas_pass,
        "D2_QH_corrected_WebGL_C0_pass_by_mode_40":webgl_pass,
        "D3_input_fractional_alpha_pixels":total_partial,
        "D3_input_unknown_fractional_pixels":source_unknown,
        "D3_zero_feasible_channels":sum(x["zero_feasible_channels"] for x in ident),
        "D3_multiple_feasible_channels":sum(x["multiple_feasible_channels"] for x in ident),
        "diagnostic_H1_P2_canvas_at_least30of40":"PASS" if canvas_pass["P2"]>=30 else "FAIL",
        "diagnostic_H2_P2_webgl_at_least30of40":"PASS" if webgl_pass["P2"]>=30 else "FAIL",
        "original_S3_H1":"FAIL_UNCHANGED","original_EF_protected_quality":"FAIL_UNCHANGED",
        "research_model_only":True,"production_promotion":False,
        "E4_live_game":"NOT_RUN","E5_independent":"NOT_RUN","exact_game_CHALK":None,
        "source_parent_report_sha256":sha(json.dumps(parent,sort_keys=True).encode())}
    report["members_sha256"]={p.name:sha(p.read_bytes()) for p in sorted(output.iterdir()) if p.is_file()}
    save(output/"report.json",report)
    print("BPRED_S3V2G_FROZEN_CANVAS_C0",canvas_pass,flush=True)
    print("BPRED_S3V2G_FROZEN_WEBGL_C0",webgl_pass,flush=True)
    print("BPRED_S3V2G_UNKNOWN",source_unknown,"/",total_partial,flush=True)
    print("BPRED_S3V2G_SCIENCE",report["diagnostic_H1_P2_canvas_at_least30of40"],
          report["diagnostic_H2_P2_webgl_at_least30of40"],flush=True)
    return report


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--workspace",type=Path,required=True)
    ap.add_argument("--source-zip",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    run(args.workspace,args.source_zip,args.output)

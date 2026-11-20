#!/usr/bin/env python3
"""BPRED-S3v2k preregistered offline owner-alpha interval, original S3v2j Egret E3 only.
Scientific diagnostics are NOT a production paint or owner-safety model.
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
from PIL import Image

import run_engine001_bpred_s3_native_source_over as s3
import run_engine001_bpred_s3v2f_prospective_native_rgba8 as v2f

EXPERIMENT="ENGINE001_BPRED_S3V2K_OWNER_INTERVAL_OFFLINE_V1"
E0_BLOB="3ae0356c353b89249ad636fa03cdd094e3d3e713"
E0_NAME="ENGINE001_BPRED001_S3V2K_SOURCE_OWNER_ALPHA_INTERVAL_PREREG_2026-11-20.md"
SOURCE_SHA="ad1fa7fd66d4df563d729b7faae27651ca8279ea"
SOURCE_RUN="44721915503"
SOURCE_E0="6801292e01a650a2b014ffe09256313ebe10562b"
SOURCE_EXP="ENGINE001_BPRED_S3V2J_NEW_NATIVE_ALPHA0_OWNER_INFLUENCE_V1"
WIDTHS=tuple(range(1,11))
RELATIONS=("CROSS_ROTATED","NEAR_SKEW")
VARIANTS=("A_ONLY","B_ONLY","A_THEN_B","B_THEN_A")
STRATA=((0,0),(1,15),(16,63),(64,127),(128,254),(255,255))
ROI=(slice(279,441),slice(435,597))
PAD_RGB=2.0
PAD_ALPHA=1.0
MARGIN_LOGICAL=3.0

def blocked(label):
    raise ValueError("BLOCKED_BPRED_S3V2K_"+label)

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(v):
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf8")

def write_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x",encoding="utf8") as f:
        json.dump(obj,f,ensure_ascii=False,indent=2,allow_nan=False)
        f.write("\n")

def check_parent(z):
    names=z.namelist()
    if (len(names)!=857 or len(set(names))!=857 or z.testzip() is not None or
            any(n.startswith("/") or "\\" in n or ".." in Path(n).parts for n in names)):
        blocked("PARENT_ZIP_CRC_MEMBERS")
    parent=json.loads(z.read("report.json"))
    expected={"experiment":SOURCE_EXP,"E0_blob":SOURCE_E0,"github_sha":SOURCE_SHA,
              "github_run_id":SOURCE_RUN,"true_new_native_primary":80,
              "H2_hidden_top_alpha0_native_owner_changed_pixel_occurrences":21,
              "H3_original_C0_canvas_pass_count_40":31,
              "H3_original_C0_QH_webgl_pass_count_40":21,
              "H3_QH_stage_RGB_mismatch_pixels":0,"H3_QH_stage_alpha_mismatch_pixels":0,
              "H1_first_owner_exact_40":"PASS","H1_last_native_main_exact_80":"PASS",
              "S0_BLIND_used":False}
    if any(parent.get(k)!=v for k,v in expected.items()):
        blocked("PARENT_REPORT_NOT_FROZEN")
    hashes=parent.get("members_sha256",{})
    if len(hashes)!=856 or set(hashes)!=set(names)-{"report.json"}:
        blocked("PARENT_SHA_SET")
    for name,signature in hashes.items():
        if digest(z.read(name))!=signature:
            blocked("PARENT_SHA_"+name)
    m=json.loads(z.read("FROZEN_S3V2J_MANIFEST.json"))
    if m.get("experiment")!=SOURCE_EXP or m.get("E0_blob")!=SOURCE_E0 or len(m.get("scenes",[]))!=80:
        blocked("FROZEN_MANIFEST")
    lookup={}
    for case in m["scenes"]:
        k=(case["width"],case["relation"],case["variant"])
        if k in lookup or k[0] not in WIDTHS or k[1] not in RELATIONS or k[2] not in VARIANTS:
            blocked("UNFROZEN_CASE")
        sid=f"BPRED-S3V2J-W{k[0]:02d}-{k[1]}-{k[2]}"
        if sid!=case["sample_id"] or (digest(canonical(case["source_strokes"]))!=
               case["source_plan_sha256"] or digest(canonical(case["runtime_strokes"]))!=
               case["runtime_plan_sha256"]):
            blocked("SOURCE_PLAN_SHA")
        for key,plan in (("SOURCE_PLAN.json",case["source_strokes"]),
                         ("RUNTIME_PLAN.json",case["runtime_strokes"])):
            if json.loads(z.read("native/"+sid+"/"+key))!=plan:
                blocked("SOURCE_PLAN_FILE_DRIFT")
        if "G32" in json.dumps(case).upper() or "V44" in json.dumps(case).upper():
            blocked("FORBIDDEN_LEGACY_PLAN")
        lookup[k]=case
    if set(lookup)!={(w,r,v) for w in WIDTHS for r in RELATIONS for v in VARIANTS}:
        blocked("CASE_MATRIX_INCOMPLETE")
    risks=json.loads(z.read("EVERY_ALPHA0_TOP_OWNER_CHANGED_PIXEL.json"))
    if (len(risks)!=21 or len({(p["sample_id"],tuple(p["native_physical_xy"]))
                                for p in risks})!=21):
        blocked("FROZEN_RISK_COUNT")
    if len(json.loads(z.read("ALL_40_ORDERED_TRUE_OWNER_EFFECT.json")))!=40:
        blocked("FROZEN_ORDERED_COUNT")
    return lookup,risks

def rgba(z,case,suffix):
    sid=case["sample_id"]
    with Image.open(io.BytesIO(z.read(f"native/{sid}/{sid}_{suffix}.png"))) as im:
        image=np.asarray(im.convert("RGBA"),dtype=np.uint8).copy()
    if image.shape!=(720,1380,4):
        blocked("NATIVE_BOARD_SHAPE_"+sid)
    return image

def rgb_owner(stroke):
    val=stroke["colorRgb"]
    if type(val) is not int or not 0<=val<=0xffffff:
        blocked("OWNER_RGB_INVALID")
    return np.array([(val>>16)&255,(val>>8)&255,val&255],dtype=np.float64)

def alpha_interval(a):
    if a.dtype!=np.uint8:
        blocked("SOURCE_ALPHA_BYTE")
    v=a.astype(np.float64)
    return np.maximum(0.,v-.5)/255.,np.minimum(255.,v+.5)/255.

def interval_envelope(bottom,top,cb,ct):
    """I1: four alpha endpoint combinations, original owner RGB, ±2RGB/±1alpha padding."""
    if (bottom.shape!=top.shape or bottom.dtype!=np.uint8 or
            bottom.ndim!=3 or bottom.shape[-1]!=4):
        blocked("ALPHA_INTERVAL_RGBA_INPUT")
    bl,bh=alpha_interval(bottom[:,:,3])
    tl,th=alpha_interval(top[:,:,3])
    cb,ct=np.asarray(cb,dtype=np.float64),np.asarray(ct,dtype=np.float64)
    if cb.shape!=(3,) or ct.shape!=(3,) or not np.all(np.isfinite(cb)) or not np.all(np.isfinite(ct)):
        blocked("OWNER_SOURCE_RGB")
    low=np.full((*bl.shape,3),np.inf)
    high=np.full((*bl.shape,3),-np.inf)
    amin=np.ones(bl.shape)
    amax=np.zeros(bl.shape)
    for b in (bl,bh):
        for t in (tl,th):
            ao=t+(1-t)*b
            amin=np.minimum(amin,ao)
            amax=np.maximum(amax,ao)
            num=t[:,:,None]*ct+(1-t)[:,:,None]*b[:,:,None]*cb
            rgb=num/np.maximum(ao,1e-30)[:,:,None]
            low=np.minimum(low,rgb)
            high=np.maximum(high,rgb)
    unknown=amin<=0
    low=np.maximum(0.,low-PAD_RGB)
    high=np.minimum(255.,high+PAD_RGB)
    low[unknown]=0.
    high[unknown]=255.
    lower=np.concatenate((low,np.maximum(0.,amin*255.-PAD_ALPHA)[:,:,None]),axis=2)
    upper=np.concatenate((high,np.minimum(255.,amax*255.+PAD_ALPHA)[:,:,None]),axis=2)
    return lower,upper,unknown

def output_contained(actual,low,high):
    if actual.shape!=low.shape or low.shape!=high.shape or actual.dtype!=np.uint8:
        blocked("INTERVAL_OUTPUT_SHAPE")
    return (actual.astype(np.float64)>=low-1e-9)&(actual.astype(np.float64)<=high+1e-9)

def segment_distance(xs,ys,points):
    if len(points)!=2:
        blocked("OWNER_SEGMENT_INVALID")
    a,b=points
    ax,ay,bx,by=map(float,(a["x"],a["y"],b["x"],b["y"]))
    vx,vy=bx-ax,by-ay
    if not all(np.isfinite((ax,ay,bx,by))) or vx*vx+vy*vy<=0:
        blocked("OWNER_SEGMENT_NOT_FINITE")
    px=(xs+.5)/3.
    py=(ys+.5)/3.
    t=np.clip(((px-ax)*vx+(py-ay)*vy)/(vx*vx+vy*vy),0.,1.)
    return np.hypot(px-(ax+t*vx),py-(ay+t*vy))

def classifier(bottom,top,actual,stroke,xoff=0,yoff=0):
    if bottom.shape!=top.shape or actual.shape!=top.shape:
        blocked("CLASSIFIER_RGBA_SHAPE")
    ys,xs=np.where((bottom[:,:,3]>0)&(top[:,:,3]==0))
    width=stroke["width"]
    if type(width) is not int or width not in WIDTHS:
        blocked("OWNER_ORIGINAL_WIDTH")
    d=segment_distance(xs+xoff,ys+yoff,stroke["points"])
    candidate=d>width/2.+MARGIN_LOGICAL
    altered=np.any(actual[ys,xs]!=bottom[ys,xs],axis=1)
    return {"total_zone":int(len(xs)),"changed":int(altered.sum()),
            "unchanged":int((~altered).sum()),
            "unchanged_candidate_correct":int((candidate&~altered).sum()),
            "false_safe":int((candidate&altered).sum()),
            "unknown":int((~candidate).sum())}

def frozen_c0(bottom,top,actual,webgl):
    frames=[frame[ROI] for frame in (bottom,top,actual,webgl)]
    b,t,real,gl=frames
    pred=s3.source_over(b,t)
    mask=(b[:,:,3]>0)|(t[:,:,3]>0)|(real[:,:,3]>0)
    m,_=s3.rgba_difference(pred,real,mask)
    w,_=s3.rgba_difference(v2f.quantize_half_up(pred),gl,mask)
    for item in (m,w):
        item["frozen_H1_pass"]=bool(item["max_channel_byte"]<=2 and item["mean_channel_byte"]<=1)
    return m,w

def run(source_zip,output,workspace=None):
    if output.exists():
        blocked("OUTPUT_EXISTS")
    if workspace is not None:
        p=workspace/"AutoDraw_Stage20"/"docs"/E0_NAME
        if not p.is_file():
            blocked("E0_NOT_FOUND")
        raw=p.read_bytes()
        got=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
        if got!=E0_BLOB:
            blocked("E0_SOURCE_DRIFT")
    with ZipFile(source_zip) as z:
        lookup,original_risks=check_parent(z)
        output.mkdir(parents=True)
        risks_by_scene={}
        for risk in original_risks:
            risks_by_scene.setdefault(risk["sample_id"],set()).add(tuple(risk["native_physical_xy"]))
        ordered_rows=[];misses=[];audited=[];qh_rgb=qh_alpha=0
        for width in WIDTHS:
            for relation in RELATIONS:
                pair={v:lookup[(width,relation,v)] for v in VARIANTS}
                frame={v:rgba(z,case,"ALIGNED_MAIN_RGBA") for v,case in pair.items()}
                for variant,case in pair.items():
                    gl=rgba(z,case,"REAL_WEBGL")
                    stage=v2f.quantize_half_up(frame[variant])
                    qh_rgb+=int(np.any(stage[:,:,:3]!=gl[:,:,:3],axis=2).sum())
                    qh_alpha+=int((stage[:,:,3]!=gl[:,:,3]).sum())
                for variant in ("A_THEN_B","B_THEN_A"):
                    case=pair[variant]
                    bottom,top=(frame["A_ONLY"],frame["B_ONLY"]) if variant=="A_THEN_B" else (
                        frame["B_ONLY"],frame["A_ONLY"])
                    target=frame[variant]
                    gl=rgba(z,case,"REAL_WEBGL")
                    original_canvas,original_webgl=frozen_c0(bottom,top,target,gl)
                    active=np.any((bottom!=0)|(top!=0)|(target!=0),axis=2)
                    y,x=np.where(active)
                    if not len(x):
                        blocked("EMPTY_NATIVE_SOURCE")
                    x0,x1,y0,y1=int(x.min()),int(x.max()+1),int(y.min()),int(y.max()+1)
                    b=bottom[y0:y1,x0:x1]
                    t=top[y0:y1,x0:x1]
                    a=target[y0:y1,x0:x1]
                    cb,ct=[rgb_owner(s) for s in case["source_strokes"]]
                    lo,hi,unknown=interval_envelope(b,t,cb,ct)
                    contained=output_contained(a,lo,hi)
                    missed=np.any(~contained,axis=2)
                    for yy,xx in np.argwhere(missed):
                        yy,xx=int(yy),int(xx)
                        misses.append({"sample_id":case["sample_id"],"xy_physical":[xx+x0,yy+y0],
                                       "actual_RGBA":a[yy,xx].tolist(),
                                       "source_bottom_RGBA":b[yy,xx].tolist(),
                                       "source_top_RGBA":t[yy,xx].tolist(),
                                       "I1_lower":lo[yy,xx].tolist(),"I1_upper":hi[yy,xx].tolist(),
                                       "missed_channels":(~contained[yy,xx]).tolist()})
                    i2=classifier(b,t,a,case["source_strokes"][-1],x0,y0)
                    zone=(b[:,:,3]>0)&(t[:,:,3]==0)
                    affected=zone&np.any(a!=b,axis=2)
                    positions=np.argwhere(affected)
                    got_risks={(int(xx+x0),int(yy+y0)) for yy,xx in positions}
                    if got_risks!=risks_by_scene.get(case["sample_id"],set()):
                        blocked("ORIGINAL_RISK_POSITION_DRIFT_"+case["sample_id"])
                    for yy,xx in positions:
                        yy,xx=int(yy),int(xx)
                        audited.append({"sample_id":case["sample_id"],
                                        "xy_physical":[xx+x0,yy+y0],
                                        "actual_RGBA":a[yy,xx].tolist(),
                                        "source_bottom_RGBA":b[yy,xx].tolist(),
                                        "source_top_RGBA":t[yy,xx].tolist(),
                                        "I1_contains_RGBA":bool(contained[yy,xx].all()),
                                        "I1_lower":lo[yy,xx].tolist(),"I1_upper":hi[yy,xx].tolist()})
                    groups={}
                    for amin,amax in STRATA:
                        label=f"{amin}" if amin==amax else f"{amin}..{amax}"
                        selection=active[y0:y1,x0:x1]&(t[:,:,3]>=amin)&(t[:,:,3]<=amax)
                        groups[label]={"pixels":int(selection.sum()),
                                       "I1_outside":int((selection&missed).sum())}
                    ordered_rows.append({"sample_id":case["sample_id"],"width":width,
                                         "relation":relation,"variant":variant,
                                         "phase_xy":case["phase_xy"],"angle_deg":case["angle_deg"],
                                         "original_canvas_C0":original_canvas,
                                         "original_QH_webgl_C0":original_webgl,
                                         "I1_interval_missed_physical_pixels":int(missed.sum()),
                                         "I1_unknown_low_alpha_physical_pixels":int(unknown.sum()),
                                         "I2":i2,"top_source_alpha_bins":groups})
        count_canvas=sum(int(x["original_canvas_C0"]["frozen_H1_pass"]) for x in ordered_rows)
        count_webgl=sum(int(x["original_QH_webgl_C0"]["frozen_H1_pass"]) for x in ordered_rows)
        if (len(ordered_rows),len(audited),count_canvas,count_webgl,qh_rgb,qh_alpha)!=(
                40,21,31,21,0,0):
            blocked("ORIGINAL_D4_BASELINE_DRIFT")
        uncertain=sum(not p["I1_contains_RGBA"] for p in audited)
        false=sum(x["I2"]["false_safe"] for x in ordered_rows)
        unchanged=sum(x["I2"]["unchanged"] for x in ordered_rows)
        safe=sum(x["I2"]["unchanged_candidate_correct"] for x in ordered_rows)
        if unchanged==0 or safe>unchanged or not 0<=uncertain<=21:
            blocked("UNCERTAINTY_COUNTS_INVALID")
        write_json(output/"ALL_40_SOURCE_OWNER_INTERVAL_CASES.json",ordered_rows)
        write_json(output/"ALL_I1_OUT_OF_ENVELOPE_PIXELS.json",misses)
        write_json(output/"ALL_21_ALPHA0_OWNER_RISK_AUDIT.json",audited)
        report={"experiment":EXPERIMENT,"E0_blob":E0_BLOB,
                "github_sha":os.getenv("GITHUB_SHA"),"github_run_id":os.getenv("GITHUB_RUN_ID"),
                "source_sha":SOURCE_SHA,"source_run":SOURCE_RUN,
                "source_archive_members_SHA_CRC":856,"source_scenes":80,
                "ordered_cases":40,"original_C0_canvas_pass_40":count_canvas,
                "original_C0_QH_webgl_pass_40":count_webgl,
                "QH_stage_RGB_mismatch":qh_rgb,"QH_stage_alpha_mismatch":qh_alpha,
                "source_hidden_alpha0_changed_owner_pixels":21,
                "I1_known_risk_misses":uncertain,
                "I1_full_image_source_owner_pixel_misses":len(misses),
                "I2_false_safe_pixels":false,
                "I2_genuine_unchanged_pixels":unchanged,
                "I2_correct_unchanged_candidates":safe,"I2_correct_fraction":safe/unchanged,
                "D1_21_known_covered_zero_false_safe":"PASS" if uncertain==false==0 else "FAIL",
                "D2_full_source_owner_interval":"PASS" if not misses else "FAIL",
                "D3_nonvacuous_at_least_50_percent":"PASS" if 2*safe>=unchanged else "FAIL",
                "D4_original_metrics_unchanged":"PASS",
                "original_S3v2j_source_over":"FAIL_UNCHANGED",
                "original_S3v2f_H2":"FAIL_UNCHANGED",
                "original_S3v2g_P2":"FAIL_UNCHANGED",
                "original_EF_protected_quality":"FAIL_UNCHANGED",
                "model_status":"MODEL_ONLY_UNKNOWN","new_native_E3":False,
                "E4_game":"NOT_RUN","E5_independent":"NOT_RUN",
                "exact_game_CHALK":None,"S0_BLIND_used":False,
                "production_promotion":False}
        report["members_sha256"]={
            p.relative_to(output).as_posix():digest(p.read_bytes())
            for p in sorted(output.rglob("*")) if p.is_file()}
        write_json(output/"report.json",report)
        print("BPRED_S3V2K_D4_BASELINE",count_canvas,count_webgl,qh_rgb,qh_alpha,flush=True)
        print("BPRED_S3V2K_D1_D2_D3",report["D1_21_known_covered_zero_false_safe"],
              report["D2_full_source_owner_interval"],
              report["D3_nonvacuous_at_least_50_percent"],flush=True)
        print("BPRED_S3V2K_RISK_MISS_TOTAL_UNKNOWN_SAFE",uncertain,len(misses),false,safe,unchanged,flush=True)
        return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source-zip",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--workspace",type=Path)
    a=p.parse_args()
    run(a.source_zip,a.output,a.workspace)

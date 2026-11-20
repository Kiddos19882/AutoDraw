#!/usr/bin/env python3
"""BPRED-S2v2: strict leave-one-angle-out monotone AA correction (MODEL_ONLY).

Reuse S1 true Egret RGBA pixels and original S2v1 area8 without new native
renders. Fit each width on TWO calibration angle families; score the THIRD.
Never inspect frozen S0 BLIND or alter P4D16, S1, S2v1 originals.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics

import numpy as np
from PIL import Image

import run_engine001_bpred_s0_corpus_audit as s0
import run_engine001_bpred_s2_alpha_aa_eval as v1

EXPERIMENT="ENGINE001_BPRED_S2V2_ANGLE_HOLDOUT_ISOTONIC_ALPHA_V1"
E0_DOC="ENGINE001_BPRED001_S2V2_ISOTONIC_ALPHA_RESIDUAL_PREREG_2026-11-20.md"
E0_GIT_BLOB="420a9502b665d6405adb8de177d1ea11fe2409f6"
V1_SOURCE_BLOB="ed29df1d559409d5a5783556a12c30d24df7118d"
NATIVE_RUN=v1.SOURCE_RUN
NATIVE_SHA=v1.SOURCE_SHA
PARENT_RUN="44651134628"
PARENT_SHA="4d2c7991e8472ed41ee64632658c55c9cd43287b"
PARENT_ARTIFACT=14589809874
ANGLES=(7,73,166)
WIDTHS=tuple(range(1,11))
MODELS=("M2_AREA8","M3_ISOTONIC")

def blocked(msg):
    raise ValueError("BLOCKED_BPRED_S2V2_"+msg)

def sha256(raw):
    return hashlib.sha256(raw).hexdigest()

def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("xb") as out:
        out.write(json.dumps(obj,ensure_ascii=False,indent=2,
                             allow_nan=False).encode("utf8")+b"\n")

def fit_isotonic(counts:np.ndarray,sums:np.ndarray):
    """Weighted PAVA on fixed observed levels1..254; interpolation, 0/255 anchors."""
    if (counts.shape!=(256,) or sums.shape!=(256,) or
        not np.issubdtype(counts.dtype,np.integer) or
        not np.all(np.isfinite(sums)) or np.any(counts<0) or np.any(sums<0)):
        blocked("TRAIN_HISTOGRAM")
    levels=np.flatnonzero(counts[1:255])+1
    if len(levels)==0:
        return np.arange(256,dtype=np.uint8),{
            "status":"IDENTITY_NO_INTERMEDIATE_ALPHA","observed_levels":0,
            "observed_training_pixels":0,"blocks":0,
            "observed":[], "mapping_sha256":sha256(np.arange(256,dtype=np.uint8).tobytes())}
    blocks=[]
    for index in levels:
        w=int(counts[index])
        total=float(sums[index])
        if w<=0 or total<0 or total>255*w:
            blocked("INVALID_TARGET_SUM")
        blocks.append([int(index),int(index),w,total])
        while len(blocks)>=2 and blocks[-2][3]/blocks[-2][2]>blocks[-1][3]/blocks[-1][2]:
            a=blocks.pop();b=blocks.pop()
            blocks.append([b[0],a[1],b[2]+a[2],b[3]+a[3]])
    targets={}
    for start,end,w,total in blocks:
        for v in levels:
            if start<=v<=end:
                targets[int(v)]=min(255.,max(0.,float(total/w)))
    if len(targets)!=len(levels):
        blocked("PAVA_COVERAGE")
    anchors=np.r_[0,levels,255]
    values=np.r_[0.,[targets[int(x)] for x in levels],255.]
    if np.any(np.diff(values)<-1e-9):
        blocked("PAVA_NONMONOTONE")
    mapping=np.rint(np.interp(np.arange(256),anchors,values)).astype(np.uint8)
    if (mapping[0]!=0 or mapping[255]!=255 or
        np.any(np.diff(mapping.astype(np.int16))<0)):
        blocked("PAVA_ENDPOINTS")
    return mapping,{
        "status":"FITTED_TRAIN_ONLY",
        "observed_levels":len(levels),
        "observed_training_pixels":int(sum(counts[1:255])),
        "blocks":len(blocks),
        "observed":[{"pred_alpha":int(x),"trained_alpha":float(targets[int(x)]),
                     "count":int(counts[x])} for x in levels],
        "mapping_sha256":sha256(mapping.tobytes())}

def accumulate(train_items):
    """Target pixels are used ONLY in training folds, with 0 and255 fixed."""
    counts=np.zeros(256,np.int64)
    sums=np.zeros(256,np.float64)
    for item in train_items:
        for pred,true in item["pixel_pairs"]:
            mask=(pred>0)&(pred<255)
            x=pred[mask].ravel()
            counts+=np.bincount(x,minlength=256)
            sums+=np.bincount(x,weights=true[mask].ravel(),minlength=256)
    return counts,sums

def prepare_cases(source):
    original,rows=v1.source_files(source)
    result=[]
    for row in rows:
        rgba,runtime=v1.load_case(source,row)
        pairs=[]
        for center,stroke in zip(s0.CENTERS,runtime):
            roi=rgba[(center[1]-27)*3:(center[1]+27)*3,
                     (center[0]-27)*3:(center[0]+27)*3,:]
            if roi.shape!=(162,162,4):
                blocked("ROI_SHAPE")
            pred=v1.predict_p16_all_widths(stroke["points"],stroke["width"],
                    (center[0]-27)*3,(center[1]-27)*3,"area8")
            native=roi[:,:,3].copy()
            pairs.append((pred,native))
        if (row["angle_deg"] not in ANGLES or row["width"] not in WIDTHS or
            len(pairs)!=3):
            blocked("CASE_ANGLE_OR_WIDTH")
        result.append({
            "sample_id":row["sample_id"],
            "angle_deg":row["angle_deg"],"width":row["width"],
            "length_logical":row["length_logical"],"phase_x":row["phase_x"],
            "phase_y":row["phase_y"],"pixel_pairs":pairs,
            "native_png_sha256":row["native_png_sha256"]})
    if (len(result)!=120 or len({r["sample_id"] for r in result})!=120 or
        any(sum(r["width"]==w and r["angle_deg"]==a for r in result)!=4
            for w in WIDTHS for a in ANGLES)):
        blocked("FULL_CALIBRATION_MATRIX")
    return original,result

def verify_parent(v1dir):
    path=v1dir/"report.json"
    if not path.is_file():
        blocked("V1_PARENT_MISSING")
    r=json.loads(path.read_text("utf8"))
    if (r.get("experiment")!=v1.EXPERIMENT or
        r.get("github_sha")!=PARENT_SHA or
        str(r.get("github_run_id"))!=PARENT_RUN or
        r.get("source_native_sha")!=NATIVE_SHA or
        r.get("source_native_member_sha256_verified")!=363 or
        r.get("calibration_cases")!=120 or
        r.get("calibration_physical_ROIs")!=360 or
        r.get("new_Egret_render_count")!=0 or
        r.get("blind_case_count_evaluated")!=0 or
        r.get("metrics",{}).get("hypothesis_H1_M2_alpha24_macro_vs_M1")!="PASS"):
        blocked("V1_PARENT_PROVENANCE")
    members=r.get("members_sha256",{})
    if not isinstance(members,dict) or set(members)!={
        "CASE_ROWS_APPEND_ONLY.jsonl","WORST_CASES_MODEL_ONLY.json"}:
        blocked("V1_PARENT_MEMBER_LIST")
    for f,hashvalue in members.items():
        if sha256((v1dir/f).read_bytes())!=hashvalue:
            blocked("V1_PARENT_SHA_"+f)
    return r

def metrics_by_model(rows,model):
    if not rows:
        blocked("EMPTY_AGGREGATE")
    def macro(key,threshold=None):
        if threshold is None:
            return float(statistics.fmean(statistics.fmean(
                c["models"][model][key] for c in r["cells"]) for r in rows))
        return float(statistics.fmean(statistics.fmean(
                c["models"][model][f"alpha{threshold}"][key] for c in r["cells"]) for r in rows))
    result={"alpha_MAE_union":macro("alpha_MAE_union"),
            "alpha_MAE_all":macro("alpha_MAE_all"),
            "n_cases":len(rows),"n_correlated_rois":3*len(rows)}
    for threshold in (1,24):
        vals=[c["models"][model][f"alpha{threshold}"]
              for r in rows for c in r["cells"]]
        result[f"alpha{threshold}"]={
          "IoU_macro":macro("IoU",threshold),
          "TP":sum(v["TP"] for v in vals),
          "FP":sum(v["FP"] for v in vals),
          "FN":sum(v["FN"] for v in vals),
          "exact_masks":sum(v["exact_mask"] for v in vals)}
    return result

def build_folds(cases):
    entries=[]
    knots=[]
    for heldout in ANGLES:
        train=[c for c in cases if c["angle_deg"]!=heldout]
        val=[c for c in cases if c["angle_deg"]==heldout]
        if (len(train)!=80 or len(val)!=40 or
            {c["angle_deg"] for c in train}!={x for x in ANGLES if x!=heldout} or
            {c["angle_deg"] for c in val}!={heldout} or
            {c["sample_id"] for c in train}&{c["sample_id"] for c in val}):
            blocked("FOLD_SPLIT_LEAKAGE")
        for width in WIDTHS:
            training=[r for r in train if r["width"]==width]
            testing=[r for r in val if r["width"]==width]
            if len(training)!=8 or len(testing)!=4:
                blocked("PER_WIDTH_SPLIT")
            counts,sums=accumulate(training)
            mapping,summary=fit_isotonic(counts,sums)
            knots.append({
                "heldout_angle":heldout,"width":width,
                "train_family_ids":[s["sample_id"] for s in training],
                "validation_family_ids":[s["sample_id"] for s in testing],
                "train_n_scenes":len(training), "train_n_ROIs":3*len(training),
                "validation_n_scenes":len(testing),"validation_n_ROIs":3*len(testing),
                "table_uint8":mapping.tolist(),**summary})
            for scene in testing:
                cells=[]
                for copy_index,(pred,true) in enumerate(scene["pixel_pairs"]):
                    m3=mapping[pred]
                    cells.append({
                        "copy_index":copy_index,"absolute_center":list(s0.CENTERS[copy_index]),
                        "models":{
                            "M2_AREA8":v1.alpha_metrics(pred,true),
                            "M3_ISOTONIC":v1.alpha_metrics(m3,true)}
                    })
                entries.append({key:val for key,val in scene.items() if key!="pixel_pairs"}|
                               {"fold_heldout_angle":heldout,"cells":cells})
    entries.sort(key=lambda r:(r["width"],r["angle_deg"],r["length_logical"],
                              r["phase_x"],r["phase_y"]))
    if (len(entries)!=120 or len(knots)!=30 or
        len({r["sample_id"] for r in entries})!=120):
        blocked("FOLD_OUTPUT_COUNT")
    return entries,knots

def run(source,v1_parent,output,workspace):
    if output.exists():
        blocked("OUTPUT_ALREADY_EXISTS")
    doc=workspace/"AutoDraw_Stage20/docs"/E0_DOC
    if not doc.is_file() or s0.git_blob(doc.read_bytes())!=E0_GIT_BLOB:
        blocked("E0_NOT_FROZEN")
    if s0.git_blob(Path(v1.__file__).read_bytes())!=V1_SOURCE_BLOB:
        blocked("V1_SOURCE_DRIFT")
    source_meta,cases=prepare_cases(source)
    parent=verify_parent(v1_parent)
    rows,knots=build_folds(cases)
    v1metrics=metrics_by_model(rows,"M2_AREA8")
    m3=metrics_by_model(rows,"M3_ISOTONIC")
    original=parent["metrics"]["all"]["M2_AREA8"]
    if (abs(original["alpha24"]["IoU_macro"]-v1metrics["alpha24"]["IoU_macro"])>1e-12 or
        abs(original["alpha_MAE_union"]-v1metrics["alpha_MAE_union"])>1e-12 or
        original["alpha24"]["FP"]!=v1metrics["alpha24"]["FP"] or
        original["alpha24"]["FN"]!=v1metrics["alpha24"]["FN"]):
        blocked("V1_RESULT_REPLAY_DRIFT")
    h1=bool(m3["alpha_MAE_union"]<=.97*v1metrics["alpha_MAE_union"])
    h2=bool(m3["alpha24"]["FP"]<=.90*v1metrics["alpha24"]["FP"] and
            m3["alpha24"]["FN"]<=1.25*v1metrics["alpha24"]["FN"])
    h3=bool(m3["alpha24"]["IoU_macro"]>=v1metrics["alpha24"]["IoU_macro"]-.002)
    safe=bool(all(m3[f"alpha{t}"]["FP"]==0 and m3[f"alpha{t}"]["FN"]==0
                  for t in (1,24)))
    summary={
        "M2_AREA8":v1metrics,"M3_ISOTONIC":m3,
        "per_fold":{str(a):{k:metrics_by_model([r for r in rows if r["angle_deg"]==a],k)
                           for k in MODELS} for a in ANGLES},
        "per_width":{str(w):{k:metrics_by_model([r for r in rows if r["width"]==w],k)
                            for k in MODELS} for w in WIDTHS},
        "hypothesis_H1_M3_MAE_improvement":"PASS" if h1 else "FAIL",
        "hypothesis_H2_M3_FP_reduction_FN_bound":"PASS" if h2 else "FAIL",
        "hypothesis_H3_M3_IoU_noninferiority":"PASS" if h3 else "FAIL",
        "M3_pixel_exact_safe_calibration":safe,
        "model_status":"CALIBRATION_ONLY_NOT_BLIND_VALIDATED" if safe else "MODEL_ONLY_UNSAFE"}
    output.mkdir(parents=True)
    with (output/"CASE_ROWS_APPEND_ONLY.jsonl").open("x",encoding="utf8") as fd:
        for row in rows:
            fd.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+"\n")
    save(output/"M3_FOLD_WIDTH_KNOTS.json",{
        "schema":"BPRED_S2V2_ISOTONIC_FOLDS_V1",
        "training_source":"true-native S1 CALIBRATION only",
        "folds":list(ANGLES),"widths":list(WIDTHS),
        "original_P4D16_formula_unchanged":True,
        "knot_tables":knots})
    report={
      "experiment":EXPERIMENT,"github_sha":os.getenv("GITHUB_SHA"),
      "github_run_id":os.getenv("GITHUB_RUN_ID"),
      "source_native_sha":NATIVE_SHA,"source_native_run":NATIVE_RUN,
      "source_native_artifact":v1.SOURCE_ARTIFACT,
      "source_native_members_verified":363,
      "parent_S2v1_run":PARENT_RUN,"parent_S2v1_sha":PARENT_SHA,
      "parent_S2v1_artifact":PARENT_ARTIFACT,
      "parent_S2v1_report_sha256":sha256((v1_parent/"report.json").read_bytes()),
      "source_browser":source_meta["browser"],
      "source_game_blob":s0.GAME_BLOB,"source_renderer_blob":s0.RENDERER_BLOB,
      "new_native_scenes_rendered":0,"blind_S0_cases_evaluated":0,
      "source_calibration_cases":120,"angle_heldout_fold_count":3,
      "trained_width_tables":30,"validation_scenes":120,
      "validation_ROIs":360,"validation_type":"INTERNAL_CALIBRATION_ANGLE_HOLDOUT",
      "fixed_thresholds":{"H1_MAE_ratio_max":.97,
                           "H2_FP_ratio_max":.90,
                           "H2_FN_ratio_max":1.25,
                           "H3_IoU_max_loss":.002},
      "metrics":summary,
      "pixel_safe_evidence":"NOT_PROVEN",
      "production_promotion":False,"E4_game":"NOT_RUN",
      "E5_independent_BLIND":"NOT_RUN","exact_run_bound_CHALK":None}
    report["members_sha256"]={
        str(p.relative_to(output)).replace("\\","/"):sha256(p.read_bytes())
        for p in sorted(output.rglob("*")) if p.is_file()}
    save(output/"report.json",report)
    print("BPRED_S2V2_MAE",v1metrics["alpha_MAE_union"],m3["alpha_MAE_union"])
    print("BPRED_S2V2_ALPHA24_IOU",v1metrics["alpha24"]["IoU_macro"],m3["alpha24"]["IoU_macro"])
    print("BPRED_S2V2_ALPHA24_FP_FN",v1metrics["alpha24"]["FP"],v1metrics["alpha24"]["FN"],
          m3["alpha24"]["FP"],m3["alpha24"]["FN"])
    print("BPRED_S2V2_H1_H2_H3",
          summary["hypothesis_H1_M3_MAE_improvement"],
          summary["hypothesis_H2_M3_FP_reduction_FN_bound"],
          summary["hypothesis_H3_M3_IoU_noninferiority"])
    return report

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    for opt in ("workspace","source-native","source-s2v1","output"):
        ap.add_argument("--"+opt,type=Path,required=True)
    a=ap.parse_args()
    run(a.source_native,a.source_s2v1,a.output,a.workspace)

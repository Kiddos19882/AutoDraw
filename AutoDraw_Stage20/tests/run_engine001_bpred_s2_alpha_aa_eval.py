#!/usr/bin/env python3
"""BPRED-S2v1: evaluate frozen P4D16 physical alpha models on real S1 Egret PNG.

Do not re-render or open BLIND, do not fit M2, do not edit parents, and never
promote alpha-model metrics into owner/color/game safety claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import statistics

import numpy as np
from PIL import Image

import run_engine001_bpred_s0_corpus_audit as s0
import run_engine001_bpred_s1_native_geometry as s1
import run_engine001_b1r_p4d16_canvas_aa_density as p16

EXPERIMENT = "ENGINE001_BPRED_S2_ALPHA_AA_CALIBRATION_V1"
PREREG = "ENGINE001_BPRED001_S2_PHYSICAL_ALPHA_AA_CALIBRATION_PREREG_2026-11-20.md"
PREREG_FROZEN_GIT_BLOB = "2c8ee61cfd29939bdef29d6ba6c9cdeefa317dd3"
P16_BLOB = "9f30dbe7cd2e2cb913db1d4f816e74b80668125d"
S1_BLOB = "546f417c4dbddd0974db86b9015bd670326bb2d5"
SOURCE_SHA = "f38f2dbfe8dcb45ea57cdcc7cba2302a848286c1"
SOURCE_RUN = "44646682797"
SOURCE_ARTIFACT = 14589516497
MODE_MAP = (("M0_NAIVE","naive"),("M1_EGRET_SHIFT","source_halfpixel"),
            ("M2_AREA8","area8"))
WIDTHS = tuple(range(1,11))
ANGLES = (7,73,166)
LENGTHS = (7,19)
PHASES = ((1/16,3/16),(5/16,7/16))
CENTERS = s0.CENTERS

def blocked(reason):
    raise ValueError("BLOCKED_BPRED_S2_" + reason)

def save_exclusive(path, obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("xb") as f:
        f.write(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False).encode("utf8")+b"\n")

def digest(b):
    return hashlib.sha256(b).hexdigest()

def source_files(parent):
    """Fail-closed complete provenance audit of all 363 frozen native members."""
    report_path=parent/"report.json"
    if not report_path.is_file():
        blocked("SOURCE_REPORT_MISSING")
    report=json.loads(report_path.read_text("utf8"))
    if (report.get("experiment")!=s1.EXPERIMENT or
        str(report.get("github_run_id"))!=SOURCE_RUN or
        report.get("github_sha")!=SOURCE_SHA or
        report.get("native_case_count")!=120 or
        report.get("native_scene_count")!=121 or
        report.get("native_calibration_observations")!=360 or
        report.get("blind_holdout_E3")!="NOT_RUN" or
        report.get("engine_blob")!=s0.GAME_BLOB or
        report.get("renderer_blob")!=s0.RENDERER_BLOB or
        report.get("S0_source_run")!=s1.S0_RUN or
        report.get("S0_source_artifact")!=s1.S0_ARTIFACT):
        blocked("SOURCE_PROVENANCE")
    browser=report.get("browser",{})
    if browser.get("browserName")!="firefox" or not str(browser.get("browserVersion","")).startswith("159."):
        blocked("BROWSER_DRIFT")
    listed=report.get("members_sha256",{})
    if not isinstance(listed,dict) or len(listed)!=363:
        blocked("SOURCE_MEMBER_COUNT")
    names=set(listed)
    files=set(str(x.relative_to(parent)).replace("\\","/")
              for x in parent.rglob("*") if x.is_file())
    if files!={"report.json"}|names:
        blocked("SOURCE_MEMBER_SET_DRIFT")
    for name,expected in sorted(listed.items()):
        if (s0.clean_member(name)!=name or
            not isinstance(expected,str) or len(expected)!=64):
            blocked("SOURCE_INVALID_MEMBER")
        if digest((parent/name).read_bytes())!=expected:
            blocked("SOURCE_SHA_"+name)
    blank=parent/"REAL_EGRET_BLANK.png"
    with Image.open(blank) as im:
        if im.size!=(1380,720) or im.mode!="RGBA" or im.getchannel("A").getbbox() is not None:
            blocked("NATIVE_BLANK")
    ledger=parent/"CASE_ROWS_APPEND_ONLY.jsonl"
    lines=[json.loads(x) for x in ledger.read_text("utf8").splitlines()]
    if len(lines)!=120 or len({r.get("sample_id") for r in lines})!=120:
        blocked("SOURCE_LEDGER_DRIFT")
    expected={(w,a,l,px,py) for w in WIDTHS for a in ANGLES
              for l in LENGTHS for px,py in PHASES}
    found={(r.get("width"),r.get("angle_deg"),r.get("length_logical"),
            r.get("phase_x"),r.get("phase_y")) for r in lines}
    if expected!=found:
        blocked("SOURCE_MATRIX_DRIFT")
    if len(list(parent.rglob("*_REAL_EGRET.png"))) !=120:
        blocked("NATIVE_CASE_IMAGE_COUNT")
    return report,lines

def load_case(parent,row):
    sid=row["sample_id"]
    if not isinstance(sid,str) or not sid.startswith("BPRED-W") or "/" in sid or "\\" in sid:
        blocked("SAMPLE_ID")
    folder=parent/"native"/sid
    path=folder/(sid+"_REAL_EGRET.png")
    with Image.open(path) as im:
        if im.size!=(1380,720) or im.mode!="RGBA":
            blocked("NATIVE_PNG_FORMAT")
        image=np.asarray(im).copy()
    if digest(path.read_bytes())!=row["native_png_sha256"]:
        blocked("SCENE_NATIVE_SHA")
    source=json.loads((folder/(sid+"_PLAN.json")).read_text("utf8"))
    runtime=json.loads((folder/(sid+"_RUNTIME_PLAN.json")).read_text("utf8"))
    if (len(source)!=3 or len(runtime)!=3 or
        s0.sha256(s0.canonical_json(source))!=row["original_plan_sha256"] or
        s0.sha256(s0.canonical_json(runtime))!=row["runtime_plan_sha256"]):
        blocked("PLAN_SHA")
    props={"width":row["width"],"angle_deg":row["angle_deg"],
           "length_logical":row["length_logical"],
           "phase_x":row["phase_x"],"phase_y":row["phase_y"]}
    if (row.get("family_id") != f'W{props["width"]:02d}_A{props["angle_deg"]%180:03d}_L{props["length_logical"]:02d}' or
        row["angle_deg"] not in ANGLES or row["width"] not in WIDTHS or
        row["length_logical"] not in LENGTHS or
        (row["phase_x"],row["phase_y"]) not in PHASES):
        blocked("CASE_MATRIX")
    expect=[s0.scene_points(x,y,row["angle_deg"],row["length_logical"],
                            (round(row["phase_x"]*16),round(row["phase_y"]*16)))
            for x,y in CENTERS]
    for j,(s,t,p) in enumerate(zip(source,runtime,expect)):
        if (s.get("strokeId")!=f"bpred-{j}" or
            t.get("strokeId")!=f"icon-{j}" or
            {k:v for k,v in s.items() if k!="strokeId"}!={k:v for k,v in t.items() if k!="strokeId"} or
            s["points"]!=p or s.get("width")!=row["width"] or
            s.get("colorIndex")!=1 or s.get("colorRgb")!=s0.OWNER_COLOR):
            blocked("NATIVE_SOURCE_STROKE_MISMATCH")
    if (image.shape!=(720,1380,4) or
        int(np.count_nonzero(image[:,:,3])) !=row["native_ink_physical"]):
        blocked("REAL_RGBA_CROPS")
    return image,runtime

def alpha_metrics(pred,native):
    if pred.shape!=(162,162) or native.shape!=(162,162) or (
        pred.dtype!=np.uint8 or native.dtype!=np.uint8):
        blocked("ALPHA_ARRAY")
    union=(pred>0)|(native>0)
    diff=np.abs(pred.astype(np.int16)-native.astype(np.int16))
    result={"alpha_MAE_union":float(diff[union].mean()) if np.any(union) else 0.,
            "alpha_MAE_all":float(diff.mean()), "exact_rgba_alpha_mask":bool(np.array_equal(pred,native)),
            "native_alpha_sum":int(native.astype(np.uint64).sum()),
            "predicted_alpha_sum":int(pred.astype(np.uint64).sum())}
    for threshold in (1,24):
        p=pred>=threshold
        a=native>=threshold
        tp=int(np.count_nonzero(p&a))
        fp=int(np.count_nonzero(p&~a))
        fn=int(np.count_nonzero(~p&a))
        result[f"alpha{threshold}"]={"TP":tp,"FP":fp,"FN":fn,
             "IoU":float(tp/(tp+fp+fn)) if tp+fp+fn else 1.0,
             "exact_mask":bool(fp==0 and fn==0),
             "false_safe_prediction":fp,
             "missed_native_coverage":fn}
    return result

def score_case(parent,row):
    image,runtime=load_case(parent,row)
    cells=[]
    total=0
    for ix,(center,stroke) in enumerate(zip(CENTERS,runtime)):
        roi=image[(center[1]-27)*3:(center[1]+27)*3,
                  (center[0]-27)*3:(center[0]+27)*3,:]
        native=roi[:,:,3]
        total+=int(np.count_nonzero(native))
        if native.shape!=(162,162) or not np.any(native):
            blocked("EMPTY_NATIVE_ROI")
        left=(center[0]-27)*3
        top=(center[1]-27)*3
        modes={}
        for model,original_mode in MODE_MAP:
            predicted=p16.predict_alpha(stroke["points"],stroke["width"],left,top,original_mode)
            modes[model]=alpha_metrics(predicted,native)
        cells.append({"absolute_logical_center":list(center),"index":ix,
                      "models":modes})
    if total!=row["native_ink_physical"]:
        blocked("OUT_OF_BOUNDS_NATIVE_INK")
    return {"sample_id":row["sample_id"],"family_id":row["family_id"],
            "width":row["width"],"angle_deg":row["angle_deg"],
            "length_logical":row["length_logical"],
            "phase_x":row["phase_x"],"phase_y":row["phase_y"],
            "native_png_sha256":row["native_png_sha256"],"cells":cells}

def metric_mean(rows,model,field,threshold=None):
    """Macro mean: first 3 correlated copies, then one vote per scene family."""
    values=[]
    for r in rows:
        v=[c["models"][model][field] if threshold is None else
           c["models"][model][f"alpha{threshold}"][field] for c in r["cells"]]
        values.append(statistics.fmean(v))
    return float(statistics.fmean(values))

def group_summary(rows):
    summary={}
    for model,_ in MODE_MAP:
        item={
          "alpha_MAE_union":metric_mean(rows,model,"alpha_MAE_union"),
          "alpha_MAE_all":metric_mean(rows,model,"alpha_MAE_all"),
          "exact_alpha_bytes_ROI":sum(c["models"][model]["exact_rgba_alpha_mask"]
                                    for r in rows for c in r["cells"])
        }
        for t in (1,24):
            a=[c["models"][model][f"alpha{t}"] for r in rows for c in r["cells"]]
            item[f"alpha{t}"]={
                "IoU_macro":metric_mean(rows,model,"IoU",t),
                "TP":sum(x["TP"] for x in a),"FP":sum(x["FP"] for x in a),
                "FN":sum(x["FN"] for x in a),
                "exact_masks":sum(x["exact_mask"] for x in a)}
        summary[model]=item
    return summary

def aggregate(rows):
    if len(rows)!=120 or {r["width"] for r in rows}!=set(WIDTHS) or (
        any(len(r["cells"])!=3 for r in rows)):
        blocked("MISSING_CASES")
    allsummary=group_summary(rows)
    naive=allsummary["M0_NAIVE"]
    m1=allsummary["M1_EGRET_SHIFT"]
    m2=allsummary["M2_AREA8"]
    odd=[x for x in rows if x["width"] in (1,3)]
    if len(odd)!=24:
        blocked("ODD_CASE_COUNT")
    oddsummary=group_summary(odd)
    h1=bool(m2["alpha24"]["IoU_macro"]>=.985 and
            m2["alpha24"]["IoU_macro"]-m1["alpha24"]["IoU_macro"]>=.005)
    h2=bool(m1["alpha_MAE_union"]>0 and
            m2["alpha_MAE_union"]<=.90*m1["alpha_MAE_union"])
    h3=bool(oddsummary["M1_EGRET_SHIFT"]["alpha24"]["IoU_macro"]-
            oddsummary["M0_NAIVE"]["alpha24"]["IoU_macro"]>=.025)
    safe=bool(all(m2[f"alpha{t}"]["FP"]==0 and m2[f"alpha{t}"]["FN"]==0 for t in (1,24)))
    return {
        "n_cases":120,"n_correlated_location_rois":360,
        "all":allsummary,"odd_widths":oddsummary,
        "per_width":{str(w):group_summary([r for r in rows if r["width"]==w]) for w in WIDTHS},
        "per_angle":{str(a):group_summary([r for r in rows if r["angle_deg"]==a]) for a in ANGLES},
        "per_length":{str(l):group_summary([r for r in rows if r["length_logical"]==l]) for l in LENGTHS},
        "per_phase":{f"PX{int(x*16)}PY{int(y*16)}":group_summary([
            r for r in rows if (r["phase_x"],r["phase_y"])==(x,y)]) for x,y in PHASES},
        "per_position":{f"copy{i}":group_summary([{**r,"cells":[r["cells"][i]]} for r in rows])
                        for i in range(3)},
        "hypothesis_H1_M2_alpha24_macro_vs_M1":"PASS" if h1 else "FAIL",
        "hypothesis_H2_M2_alphaMAE_union_vs_M1":"PASS" if h2 else "FAIL",
        "hypothesis_H3_M1_odd_alpha24_vs_M0":"PASS" if h3 else "FAIL",
        "M2_pixel_exact_safe_calibration":safe,
        "model_status":"MODEL_ONLY" if not safe else "CALIBRATION_ONLY_NOT_BLIND_VALIDATED",
        "foreign_owner_safety":"NOT_EVALUATED",
        "S2_color_compositor":"NOT_RUN"
    }

def run(parent,output,workspace):
    if output.exists():
        blocked("OUTPUT_ALREADY_EXISTS")
    prereg=workspace/"AutoDraw_Stage20/docs"/PREREG
    if not prereg.is_file() or s0.git_blob(prereg.read_bytes()) != PREREG_FROZEN_GIT_BLOB:
        blocked("PREREG_BLOB_DRIFT")
    if (s0.git_blob(Path(s1.__file__).read_bytes())!=S1_BLOB or
        s0.git_blob(Path(p16.__file__).read_bytes())!=P16_BLOB):
        blocked("PINNED_SOURCE_DRIFT")
    source,ledger=source_files(parent)
    output.mkdir(parents=True)
    cases=[]
    with (output/"CASE_ROWS_APPEND_ONLY.jsonl").open("x",encoding="utf8") as fh:
        for row in ledger:
            entry=score_case(parent,row)
            cases.append(entry)
            fh.write(json.dumps(entry,ensure_ascii=False,allow_nan=False)+"\n")
            fh.flush()
            if len(cases)%20==0:
                print("BPRED_S2_VERIFIED_NATIVE_PNG",len(cases),"/120",flush=True)
    summary=aggregate(cases)
    worst=sorted(({"sample_id":r["sample_id"],"width":r["width"],
        "M2_alpha24_IoU":statistics.fmean(c["models"]["M2_AREA8"]["alpha24"]["IoU"] for c in r["cells"]),
        "M2_false_safe_alpha24":sum(c["models"]["M2_AREA8"]["alpha24"]["FP"] for c in r["cells"]),
        "M2_false_negative_alpha24":sum(c["models"]["M2_AREA8"]["alpha24"]["FN"] for c in r["cells"])}
        for r in cases),key=lambda x:(x["M2_alpha24_IoU"],-x["M2_false_safe_alpha24"],x["sample_id"]))
    save_exclusive(output/"WORST_CASES_MODEL_ONLY.json",worst[:12])
    report={
      "experiment":EXPERIMENT,"status":"SOURCE_NATIVE_E3_REANALYSIS",
      "github_sha":os.environ.get("GITHUB_SHA"),"github_run_id":os.environ.get("GITHUB_RUN_ID"),
      "source_native_sha":SOURCE_SHA,"source_native_run_id":SOURCE_RUN,
      "source_native_artifact_id":SOURCE_ARTIFACT,
      "source_Egret_browser":source["browser"],
      "source_Egret_game_blob":source["engine_blob"],
      "source_Egret_renderer_blob":source["renderer_blob"],
      "original_S1_report_sha256":digest((parent/"report.json").read_bytes()),
      "source_native_member_sha256_verified":363,
      "new_Egret_render_count":0,
      "calibration_cases":120,"calibration_physical_ROIs":360,
      "blind_case_count_evaluated":0,"native_BLIND_status":"NOT_RUN",
      "models":{"M0_NAIVE":"P4D16 naive binary unshifted",
                "M1_EGRET_SHIFT":"P4D16 source_halfpixel binary shift odd widths",
                "M2_AREA8":"P4D16 area8 8x8 subpixel integration shifted odd widths"},
      "hypothesis_thresholds_frozen":{"H1_macro_IoU_min":.985,
                  "H1_vs_M1_delta_min":.005,"H2_MAE_ratio_max":.90,
                  "H3_odd_vs_naive_IoU_delta_min":.025},
      "metrics":summary,"source_original_untouched":True,
      "technical_result":"E3_NATIVE_ARCHIVE_INTEGRITY_AND_E2_PREDICTION_VALIDATED",
      "independent_blind_validation":"NOT_RUN",
      "E4_game":"NOT_RUN","E5_independent":"NOT_RUN",
      "exact_run_bound_CHALK":None,"production_promotion":False
    }
    report["members_sha256"]={str(p.relative_to(output)).replace("\\","/"):digest(p.read_bytes())
                              for p in sorted(output.rglob("*")) if p.is_file()}
    save_exclusive(output/"report.json",report)
    print("BPRED_S2_H1_H2_H3",summary["hypothesis_H1_M2_alpha24_macro_vs_M1"],
          summary["hypothesis_H2_M2_alphaMAE_union_vs_M1"],
          summary["hypothesis_H3_M1_odd_alpha24_vs_M0"],flush=True)
    print("BPRED_S2_M2_METRICS",json.dumps({"M2_IoU_alpha24":summary["all"]["M2_AREA8"]["alpha24"]["IoU_macro"],
          "M1_IoU_alpha24":summary["all"]["M1_EGRET_SHIFT"]["alpha24"]["IoU_macro"],
          "M2_alpha_MAE_union":summary["all"]["M2_AREA8"]["alpha_MAE_union"],
          "M2_FP_alpha24":summary["all"]["M2_AREA8"]["alpha24"]["FP"],
          "M2_FN_alpha24":summary["all"]["M2_AREA8"]["alpha24"]["FN"],
          "pixel_exact_safe":summary["M2_pixel_exact_safe_calibration"]}),flush=True)
    return report

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--source-artifact",required=True,type=Path)
    a.add_argument("--output",required=True,type=Path)
    a.add_argument("--workspace",required=True,type=Path)
    p=a.parse_args()
    run(p.source_artifact,p.output,p.workspace)

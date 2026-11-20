#!/usr/bin/env python3
"""BPRED-S2v4: genuinely NEW Egret high-alpha-core stress test, E0 frozen beforehand.

120 preregistered new widths/angles/lengths/independent XY phases, 10 exact
replays and one blank. NEVER touch S0 BLIND. M5 alpha>=128 is a preselected
candidate from prior exploratory S2v3, NOT a native-safe production policy.
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

import run_engine001_bpred_s0_corpus_audit as s0
import run_engine001_b1r_p4d3_native_brush_repeatability as p4d3
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
import run_engine001_bpred_s2_alpha_aa_eval as v1
import run_engine001_bpred_s2v3_risk_aware_alpha as v3

EXPERIMENT="ENGINE001_BPRED_S2V4_NEW_NATIVE_CORE_V1"
E0_DOC="ENGINE001_BPRED001_S2V4_NEW_NATIVE_CORE_VALIDATION_PREREG_2026-11-20.md"
E0_BLOB="68f34975e9bb6b2262af8d38ba033bece289059e"
V3_BLOB="5e527afa17e975459af937bb277593c53b71f1d9"
V1_BLOB="ed29df1d559409d5a5783556a12c30d24df7118d"
P4D3_BLOB=s0.P4D3_BLOB
PARENT_SHA="fe39bba16c8df21a8fa3f796da35323f240c7269"
PARENT_RUN="44657226273"
PARENT_ARTIFACT=14593881636
ANGLES=(22,111,241)
LENGTHS=(9,23)
PHASES=((1,11),(13,7))  # numerator /32 independent in X/Y
WIDTHS=tuple(range(1,11))
FROZEN_COPY_CENTERS=s0.CENTERS
M5_ALPHA_THRESHOLD=128
ALPHA_GATE=24
EXPECTED_SCENES=120
EXPECTED_REPLAYS=10


def blocked(message):
    raise ValueError("BLOCKED_BPRED_S2V4_"+message)


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def save_json(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("xb") as f:
        f.write(json.dumps(obj,ensure_ascii=False,indent=2,
                           allow_nan=False).encode("utf8")+b"\n")


def source_points(cx,cy,angle,length,phase):
    if angle not in ANGLES or length not in LENGTHS or phase not in PHASES:
        blocked("UNFROZEN_GEOMETRY")
    radians=math.radians(angle%180)
    dx=length*math.cos(radians)/2.
    dy=length*math.sin(radians)/2.
    x=cx+.25+phase[0]/32
    y=cy+.375+phase[1]/32
    points=[{"x":float(x-dx),"y":float(y-dy)},
            {"x":float(x+dx),"y":float(y+dy)}]
    if angle>=180:
        points.reverse()
    return points


def prepare_scene(width,angle,length,phase):
    if type(width) is not int or width not in WIDTHS:
        blocked("UNFROZEN_WIDTH")
    strokes=[]
    bounds=[]
    for i,(cx,cy) in enumerate(FROZEN_COPY_CENTERS):
        points=source_points(cx,cy,angle,length,phase)
        radius=width/2.
        a=min(x["x"] for x in points)-radius
        b=max(x["x"] for x in points)+radius
        c=min(x["y"] for x in points)-radius
        d=max(x["y"] for x in points)+radius
        if not (0<a<b<460 and 0<c<d<240):
            blocked("BOARD_CLIP")
        for e,f,g,h in bounds:
            if a<f and e<b and c<h and g<d:
                blocked("OVERLAPPING_STROKES")
        bounds.append((a,b,c,d))
        strokes.append({"strokeId":f"bpred-{i}","width":width,
                        "colorIndex":1,"colorRgb":s0.OWNER_COLOR,
                        "points":points})
    px,py=phase
    sid=f"BPRED-S2V4-W{width:02d}-A{angle:03d}-L{length:02d}-PX{px:02d}-PY{py:02d}"
    runtime=[{**s,"strokeId":f"icon-{i}"} for i,s in enumerate(strokes)]
    if any({k:v for k,v in a.items() if k!="strokeId"}!={k:v for k,v in b.items() if k!="strokeId"}
           for a,b in zip(strokes,runtime)):
        blocked("RUNTIME_TRANSPORT_CHANGED_INPUT")
    return {"sample_id":sid,"width":width,"angle_deg":angle,
            "length_logical":length,"phase_x":px/32.,"phase_y":py/32.,
            "source_plan_sha256":s0.sha256(s0.canonical_json(strokes)),
            "runtime_plan_sha256":s0.sha256(s0.canonical_json(runtime)),
            "strokes":strokes,"runtime":runtime,
            "native_png_sha256":None,"native_status":"NOT_RUN"}


def manifest():
    scenes=[prepare_scene(w,a,l,p)
            for w in WIDTHS for a in ANGLES for l in LENGTHS for p in PHASES]
    if len(scenes)!=EXPECTED_SCENES or len({x["sample_id"] for x in scenes})!=len(scenes):
        blocked("SCENE_MATRIX")
    if {x["angle_deg"]%180 for x in scenes}&({7,73,166}|{38,121,97}):
        blocked("S0_BLIND_OR_CALIBRATION_LEAKAGE")
    repeats=[]
    for w in WIDTHS:
        parent=next(x for x in scenes
                    if x["width"]==w and x["angle_deg"]==22 and
                       x["length_logical"]==9 and
                       (x["phase_x"],x["phase_y"])==(1/32,11/32))
        repeats.append({"sample_id":f"BPRED-S2V4-REPEAT-W{w:02d}",
                        "parent_sample_id":parent["sample_id"],
                        "width":w, "runtime_plan_sha256":parent["runtime_plan_sha256"],
                        "native_status":"NOT_RUN"})
    return {"experiment":EXPERIMENT,"frozen":True,"source_e0_blob":E0_BLOB,
            "primary_scene_count":len(scenes),
            "exact_replay_count":len(repeats),"blank_count":1,
            "total_native_png_planned":131,
            "no_S0_BLIND":True,"scenes":scenes,"repeat_controls":repeats}


def verify_parent(root:Path):
    p=root/"report.json"
    if not p.is_file():
        blocked("S2V3_PARENT_MISSING")
    meta=json.loads(p.read_text("utf8"))
    if (meta.get("experiment")!=v3.EXPERIMENT or
        meta.get("github_sha")!=PARENT_SHA or
        str(meta.get("github_run_id"))!=PARENT_RUN or
        meta.get("source_calibration_cases")!=120 or
        meta.get("new_native_scenes_rendered")!=0 or
        meta.get("S0_BLIND_scenes_evaluated")!=0 or
        meta.get("metrics",{}).get("independent_safety_gate_zero_FP")!="FAIL"):
        blocked("S2V3_PARENT_PROVENANCE")
    members=meta.get("members_sha256",{})
    if not isinstance(members,dict) or set(members)!={
        "CASE_ROWS_APPEND_ONLY.jsonl","M4_FOLD_WIDTH_GUARDS.json","WORST_MODEL_ONLY_CASES.json"}:
        blocked("S2V3_PARENT_MEMBER_NAMES")
    for file,sha in members.items():
        if sha256((root/file).read_bytes())!=sha:
            blocked("S2V3_PARENT_HASH")
    raw=json.loads((root/"M4_FOLD_WIDTH_GUARDS.json").read_text("utf8"))
    entries=raw.get("fold_width_guards",[])
    if len(entries)!=30 or raw.get("quantile")!=.995:
        blocked("S2V3_PARENT_GUARD_MATRIX")
    bywidth={w:[] for w in WIDTHS}
    for x in entries:
        if (x.get("width") not in WIDTHS or
            x.get("heldout_angle") not in (7,73,166) or
            type(x.get("higher_quantile_uint8")) is not int):
            blocked("S2V3_PARENT_Q")
        bywidth[x["width"]].append(x["higher_quantile_uint8"])
    if any(len(v)!=3 for v in bywidth.values()):
        blocked("S2V3_PARENT_GUARD_GROUPS")
    return {w:max(v) for w,v in bywidth.items()},meta


def row_metrics(scene,rgba,meta,qmax):
    if rgba.shape!=p4d3.NATIVE_SHAPE or rgba.dtype!=np.uint8:
        blocked("NATIVE_FRAME_SHAPE")
    cells=[]
    total_ink=0
    for i,((cx,cy),stroke) in enumerate(zip(FROZEN_COPY_CENTERS,scene["runtime"])):
        roi=p4d3.roi(rgba,cx,cy)
        actual=roi[:,:,3]
        total_ink+=int(np.count_nonzero(actual))
        if roi.shape!=(162,162,4) or not np.any(actual):
            blocked("EMPTY_NATIVE_COPY")
        predicted=v1.predict_p16_all_widths(stroke["points"],stroke["width"],
                            (cx-27)*3,(cy-27)*3,"area8")
        candidate=v3.classify_pair(predicted,actual,M5_ALPHA_THRESHOLD-ALPHA_GATE)
        diagnostic=v3.classify_pair(predicted,actual,qmax)
        if candidate["M2_AREA8"]!=diagnostic["M2_AREA8"]:
            blocked("BASELINE_DIAGNOSTIC_DRIFT")
        cells.append({"copy_index":i,"logical_center":[cx,cy],
            "M2_AREA8":candidate["M2_AREA8"],
            "M5_HIGH_ALPHA_CORE":candidate["M4_EMPIRICAL_ALPHA_GUARD"],
            "M4_PREVIOUS_MAX_Q_DIAGNOSTIC":diagnostic["M4_EMPIRICAL_ALPHA_GUARD"],
            "M4_previous_q":qmax,
            "native_alpha24_count":candidate["native_alpha24_count"],
            "UNKNOWN_native_positive":candidate["UNKNOWN_native_positive_pixels"],
            "native_alpha_sum":int(actual.astype(np.uint64).sum()),
            "M2_alpha1":v1.alpha_metrics(predicted,actual)["alpha1"],
            "M2_alpha24":v1.alpha_metrics(predicted,actual)["alpha24"]})
    if total_ink!=int(np.count_nonzero(rgba[:,:,3])):
        blocked("NATIVE_ALPHA_OUTSIDE_THREE_ROIS")
    return {
        "sample_id":scene["sample_id"],"width":scene["width"],
        "angle_deg":scene["angle_deg"],"length_logical":scene["length_logical"],
        "phase_x":scene["phase_x"],"phase_y":scene["phase_y"],
        "source_plan_sha256":scene["source_plan_sha256"],
        "runtime_plan_sha256":scene["runtime_plan_sha256"],
        "native_png_sha256":meta["source_png_sha256"],
        "native_ink_physical":total_ink,"cells":cells}


def total_for(rows,model):
    cells=[c for r in rows for c in r["cells"]]
    return {k:int(sum(c[model][k] for c in cells))
            for k in ("TP","FP","FN","positive_predicted")}


def evaluate(rows):
    if len(rows)!=120 or any(len(r["cells"])!=3 for r in rows):
        blocked("RESULT_SCENES")
    m2=total_for(rows,"M2_AREA8")
    m5=total_for(rows,"M5_HIGH_ALPHA_CORE")
    m4=total_for(rows,"M4_PREVIOUS_MAX_Q_DIAGNOSTIC")
    if m2["TP"]<=0:
        blocked("NO_BASELINE_TP")
    h1=m5["FP"]==0
    h2=m5["TP"]>=.90*m2["TP"]
    by_width={}
    for w in WIDTHS:
        grp=[r for r in rows if r["width"]==w]
        a=total_for(grp,"M2_AREA8");b=total_for(grp,"M5_HIGH_ALPHA_CORE")
        by_width[str(w)]={"M2":a,"M5":b,
            "retained_TP_ratio":float(b["TP"]/a["TP"]) if a["TP"] else None}
    by_angle={}
    for a in ANGLES:
        grp=[r for r in rows if r["angle_deg"]==a]
        p=total_for(grp,"M2_AREA8");q=total_for(grp,"M5_HIGH_ALPHA_CORE")
        by_angle[str(a)]={"M2":p,"M5":q,
            "retained_TP_ratio":float(q["TP"]/p["TP"]) if p["TP"] else None}
    if any(x["M2"]["TP"]<=0 for x in (*by_width.values(),*by_angle.values())):
        blocked("ZERO_STRATUM_DENOMINATOR")
    h3=all(x["retained_TP_ratio"]>=.80 for x in by_width.values()) and (
       all(x["retained_TP_ratio"]>=.85 for x in by_angle.values()))
    return {
        "primary_scene_count":120,"native_calibration_ROIs":360,
        "M2_AREA8":m2,"M5_HIGH_ALPHA_CORE":m5,
        "M4_PREVIOUS_MAX_Q_DIAGNOSTIC":m4,
        "M5_TP_retained_fraction":float(m5["TP"]/m2["TP"]),
        "H1_zero_FP":"PASS" if h1 else "FAIL",
        "H2_90pct_TP_retention":"PASS" if h2 else "FAIL",
        "H3_each_width_and_angle_retention":"PASS" if h3 else "FAIL",
        "safety_gate_zero_FP":"PASS" if m5["FP"]==0 else "FAIL",
        "M5_model_status":"MODEL_ONLY_NEW_NATIVE_STRESS_ONLY",
        "M5_pixel_exact_safe":False,
        "per_width":by_width,"per_angle":by_angle
    }


def run(workspace:Path,engine:Path,renderer:Path,source_v3:Path,output:Path):
    if output.exists():
        blocked("OUTPUT_EXISTS")
    doc=workspace/"AutoDraw_Stage20"/"docs"/E0_DOC
    pins=[
        (doc,E0_BLOB),
        (engine,s0.GAME_BLOB),
        (renderer,s0.RENDERER_BLOB),
        (Path(p4d3.__file__),P4D3_BLOB),
        (Path(v1.__file__),V1_BLOB),
        (Path(v3.__file__),V3_BLOB)
    ]
    for p,sha in pins:
        if not p.is_file() or s0.git_blob(p.read_bytes())!=sha:
            blocked("SOURCE_GIT_BLOB_"+p.name)
    original=workspace/"AutoDraw_Stage20"/"testImages"/"wV6VeZI9S1Y.png"
    if not original.is_file() or sha256(original.read_bytes())!=s0.SOURCE_SHA256:
        blocked("ORIGINAL_SHA")
    qmax,parent=verify_parent(source_v3)
    plan=manifest()
    output.mkdir(parents=True)
    save_json(output/"FROZEN_NEW_SCENE_MANIFEST.json",plan)
    save_json(output/"S2V3_SOURCE_PROVENANCE.json",{
        "parent_run":PARENT_RUN,"parent_sha":PARENT_SHA,
        "parent_artifact":PARENT_ARTIFACT,
        "parent_report_sha256":sha256((source_v3/"report.json").read_bytes()),
        "max_q_per_width":{str(k):v for k,v in qmax.items()}})
    rows=[]
    with p4b7.native_egret_session(workspace) as driver:
        caps={"browserName":driver.capabilities.get("browserName"),
              "browserVersion":driver.capabilities.get("browserVersion"),
              "platformName":driver.capabilities.get("platformName")}
        if caps["browserName"]!="firefox" or not str(caps["browserVersion"]).startswith("159."):
            blocked("BROWSER_NOT_PINNED")
        blank_ret=driver.execute_script(p4d3.CMD,[])
        blank,blankmeta=p4d3.read_webgl_result(blank_ret,output,"S2V4_REAL_EGRET_BLANK")
        if (blank.shape!=p4d3.NATIVE_SHAPE or
            blankmeta.get("schema")!="ENGINE001_B1R_P4A2_BLANK_WEBGL" or
            int(np.count_nonzero(blank[:,:,3]))!=0):
            blocked("BLANK_NOT_ZERO_ALPHA")
        with (output/"CASE_ROWS_APPEND_ONLY.jsonl").open("x",encoding="utf8") as f:
            first_bywidth={}
            for scene in plan["scenes"]:
                sid=scene["sample_id"]
                root=output/"native"/sid
                root.mkdir(parents=True,exist_ok=False)
                save_json(root/(sid+"_PLAN.json"),scene["strokes"])
                save_json(root/(sid+"_RUNTIME_PLAN.json"),scene["runtime"])
                image,meta=p4d3.read_scene(driver,root,sid+"_REAL_EGRET",scene["runtime"])
                row=row_metrics(scene,image,meta,qmax[scene["width"]])
                rows.append(row)
                f.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+"\n")
                f.flush()
                if (scene["angle_deg"],scene["length_logical"],scene["phase_x"],scene["phase_y"])==(
                    22,9,1/32,11/32):
                    first_bywidth[scene["width"]]=(image.copy(),scene)
                if len(rows)%20==0:
                    print("BPRED_S2V4_NEW_NATIVE",len(rows),"/120",flush=True)
        repeat_checks=[]
        for item in plan["repeat_controls"]:
            w=item["width"]
            first,ref=first_bywidth[w]
            folder=output/"replays"
            folder.mkdir(parents=True,exist_ok=True)
            image,meta=p4d3.read_scene(driver,folder,
                          item["sample_id"]+"_REAL_EGRET",ref["runtime"])
            exact=bool(np.array_equal(first,image))
            repeat_checks.append({"width":w,"sample_id":item["sample_id"],
                "parent_sample_id":ref["sample_id"],
                "native_png_sha256":meta["source_png_sha256"],"rgba_exact":exact})
            if not exact:
                blocked("REPEAT_NATIVE_RGBA_DRIFT_W"+str(w))
    score=evaluate(rows)
    worst=sorted(rows,key=lambda r:(
        sum(c["M5_HIGH_ALPHA_CORE"]["FP"] for c in r["cells"]),
        sum(c["M2_AREA8"]["FP"] for c in r["cells"])),reverse=True)[:12]
    save_json(output/"WORST_NEW_NATIVE_CASES.json",[
        {"sample_id":r["sample_id"],"width":r["width"],"angle":r["angle_deg"],
         "M2_FP":sum(c["M2_AREA8"]["FP"] for c in r["cells"]),
         "M5_FP":sum(c["M5_HIGH_ALPHA_CORE"]["FP"] for c in r["cells"])}
        for r in worst])
    save_json(output/"REPLAY_CONTROLS.json",repeat_checks)
    report={
        "experiment":EXPERIMENT,"github_sha":os.getenv("GITHUB_SHA"),
        "github_run_id":os.getenv("GITHUB_RUN_ID"),
        "new_native_primary_scenes":len(rows),
        "new_native_replay_controls":len(repeat_checks),
        "new_native_blank_scenes":1,
        "new_native_total_PNG":len(rows)+len(repeat_checks)+1,
        "S0_reserved_BLIND_used":False,
        "native_browser":caps,
        "source_game_blob":s0.GAME_BLOB,
        "source_renderer_blob":s0.RENDERER_BLOB,
        "frozen_E0_blob":E0_BLOB,
        "source_parent_S2v3_sha":PARENT_SHA,
        "source_parent_S2v3_run":PARENT_RUN,
        "source_parent_S2v3_artifact":PARENT_ARTIFACT,
        "native_blank_alpha0":True,
        "all_replay_RGBA_exact":all(x["rgba_exact"] for x in repeat_checks),
        "source_colored_one_owner_test_only":True,
        "threshold_M2_positive":ALPHA_GATE,
        "threshold_M5_trusted_positive":M5_ALPHA_THRESHOLD,
        "fixed_gates":{"H1_M5_FP_required":0,"H2_M5_TP_retention_min":.90,
                       "H3_width_TP_retention_min":.80,
                       "H3_angle_TP_retention_min":.85},
        "metrics":score,
        "full_RGB_owner_protected_quality":"NOT_EVALUATED_P4D18_FAIL_UNCHANGED",
        "M5_production_promotion":False,
        "E4_game":"NOT_RUN","E5_independent":"NOT_RUN",
        "exact_run_bound_CHALK":None
    }
    report["members_sha256"]={
        str(p.relative_to(output)).replace("\\","/"):sha256(p.read_bytes())
        for p in sorted(output.rglob("*")) if p.is_file()}
    save_json(output/"report.json",report)
    print("BPRED_S2V4_FP_TP",score["M2_AREA8"]["FP"],score["M5_HIGH_ALPHA_CORE"]["FP"],
        score["M2_AREA8"]["TP"],score["M5_HIGH_ALPHA_CORE"]["TP"])
    print("BPRED_S2V4_H1_H2_H3",
        score["H1_zero_FP"],score["H2_90pct_TP_retention"],
        score["H3_each_width_and_angle_retention"])
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for n in ("workspace","engine","renderer","source-v3","output"):
        p.add_argument("--"+n,type=Path,required=True)
    args=p.parse_args()
    run(args.workspace,args.engine,args.renderer,args.source_v3,args.output)

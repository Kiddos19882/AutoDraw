#!/usr/bin/env python3
"""P4B8: four pre-registered source-causal surgery arms with true Egret native replay."""
from __future__ import annotations
import argparse
import json
import os
import shutil
import tempfile
from copy import deepcopy
from pathlib import Path
import numpy as np
from PIL import Image

import run_engine001_b1r_p4b6_source_protected_margin as p4b6
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
import run_engine001_b1r_p4b5_protected_baseline_rebalance as p4b5
import run_engine001_b1r_p4b4_boundary_tolerance_sweep as p4b4
from run_engine001_b1r_p4b1_hybrid_zone_coverage import _source_centerline
from run_engine001_b1r_p1_fullrgb_edge_aware import check_source
from run_engine001_b1r_p2_joint_region_outline import digest

EXPERIMENT="ENGINE001_B1R_P4B8_CAUSAL_STROKE_SURGERY_V1"
PREREG="ENGINE001_B1R_P4B8_CAUSAL_NATIVE_STROKE_SURGERY_PREREG_2026-11-18.md"
P4B6_BLOB="2f9ca1756da58e7062fcae6c6c64c83e4db79ea9"
P4B7_BLOB="87ea292c01c75e594c4ff09acf716c4500e88644"
RENDERER_BLOB="76d950e0a8911888a9df3b675b866519ecf7bba4"
SOURCE_SHA="07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
METHODS=("E_SOBEL90","F_SOBEL90_LAB12")
ARM="G1_0"
ARMS=("DROP2","WIDTH1","TRIM50","WIDTH1_TRIM50")
CULPRITS={"E_SOBEL90":(100,114),"F_SOBEL90_LAB12":(98,114)}
COUNTS={"E_SOBEL90":214,"F_SOBEL90_LAB12":212}
TARGETS=((191,833),(275,776))
ALPHA=24
COVERAGE_GATE=.99
SPILL_GATE=3.
MAX_STROKES=250
MAX_VERTICES=500


def supported(stroke,component):
    if (not isinstance(stroke,dict) or
            not isinstance(stroke.get("points"),list) or
            len(stroke["points"])!=2 or
            component.shape!=p4b5.SHAPE or component.dtype!=np.bool_):
        return False
    try:
        points=np.array([[float(q["x"])-155.,float(q["y"])]
                         for q in stroke["points"]],np.float64)
    except (ValueError,TypeError,KeyError):
        return False
    if (points.shape!=(2,2) or not np.isfinite(points).all() or
            (points[:,0]<0).any() or (points[:,0]>=150).any() or
            (points[:,1]<0).any() or (points[:,1]>=240).any()):
        return False
    return _source_centerline([tuple(x) for x in points],component)


def surgery(parent,method,arm,component,repair_start):
    if (method not in METHODS or arm not in ARMS or
            type(repair_start) is not int or repair_start<=0 or
            not isinstance(parent,list) or len(parent)!=COUNTS[method] or
            component.shape!=p4b5.SHAPE or component.dtype!=np.bool_):
        raise ValueError("BLOCKED_P4B8_PINNED_INPUT_OR_SOURCE")
    if (sum(len(s.get("points",[])) for s in parent)>MAX_VERTICES or
            any(s.get("strokeId")!="icon-%d"%i or
                s.get("colorIndex")!=115 or
                type(s.get("width")) is not int or not 1<=s["width"]<=10 or
                not isinstance(s.get("points"),list) or
                not 2<=len(s["points"])<=128 for i,s in enumerate(parent))):
        raise ValueError("BLOCKED_P4B8_INVALID_PARENT_STROKES")
    culprits=CULPRITS[method]
    if any(i<repair_start or i>=len(parent) for i in culprits):
        raise ValueError("BLOCKED_P4B8_CULPRIT_NOT_CORRECTION")
    if any(not supported(parent[i],component) for i in culprits):
        raise ValueError("BLOCKED_P4B8_ORIGINAL_CULPRIT_SOURCE_UNSUPPORTED")
    modified=deepcopy(parent)
    if arm=="DROP2":
        modified=[s for i,s in enumerate(modified) if i not in culprits]
        for i,s in enumerate(modified):
            s["strokeId"]="icon-%d"%i
    else:
        for i in culprits:
            row=modified[i]
            before=deepcopy(row["points"])
            if arm in ("WIDTH1","WIDTH1_TRIM50"):
                row["width"]=1
            if arm in ("TRIM50","WIDTH1_TRIM50"):
                a,b=before
                row["points"]=[
                    {"x":.75*a["x"]+.25*b["x"],"y":.75*a["y"]+.25*b["y"]},
                    {"x":.25*a["x"]+.75*b["x"],"y":.25*a["y"]+.75*b["y"]},
                ]
            if not supported(row,component):
                raise ValueError("BLOCKED_P4B8_SURGERY_NOT_SOURCE_SUPPORTED")
    if (not modified or len(modified)>MAX_STROKES or
            sum(len(s["points"]) for s in modified)>MAX_VERTICES or
            len({s["strokeId"] for s in modified})!=len(modified)):
        raise ValueError("BLOCKED_P4B8_RESOURCES_OR_DUPLICATED_ID")
    for i,original in enumerate(parent):
        if i in culprits:continue
        j=i-sum(x<i for x in culprits) if arm=="DROP2" else i
        if {k:v for k,v in modified[j].items() if k!="strokeId"}!={
                k:v for k,v in original.items() if k!="strokeId"}:
            raise ValueError("BLOCKED_P4B8_NONCULPRIT_CHANGED")
    ledger={
        "method":method,"arm":arm,
        "culprit_original_final_indices":list(culprits),
        "culprit_original_stroke_ids":[parent[i]["strokeId"] for i in culprits],
        "culprit_original_widths":[parent[i]["width"] for i in culprits],
        "culprit_original_points":[parent[i]["points"] for i in culprits],
        "culprit_modified_widths":[] if arm=="DROP2" else [modified[i]["width"] for i in culprits],
        "culprit_modified_points":[] if arm=="DROP2" else [modified[i]["points"] for i in culprits],
        "nonculprit_geometry_unchanged":True,"source_support_verified":True,
        "new_strokes_created":False,"total_strokes":len(modified),
        "synthetic_vertices_NOT_CHALK":sum(len(s["points"]) for s in modified)
    }
    return modified,ledger


def visual_difference(original,changed,component,owner,protected,path):
    ref=original[:,:,3]>=ALPHA
    new=changed[:,:,3]>=ALPHA
    target=p4b4.backing(component)
    sensitive=p4b4.backing(protected&~owner)
    rgb=np.full((720,1380,3),255,np.uint8)
    rgb[ref&new]=(205,205,205)
    rgb[ref&~new&target]=(244,168,26)
    rgb[~ref&new&target]=(35,181,35)
    rgb[ref&~new&~target]=(45,100,230)
    rgb[~ref&new&~target]=(225,32,32)
    rgb[new&sensitive]=(205,5,180)
    Image.fromarray(rgb,"RGB").save(path)


def run(workspace,source,engine_js,renderer,output):
    if output.exists():
        raise ValueError("BLOCKED_P4B8_OUTPUT_EXISTS")
    check_source(source)
    if (p4b4.git_blob(Path(p4b6.__file__).read_bytes())!=P4B6_BLOB or
            p4b4.git_blob(Path(p4b7.__file__).read_bytes())!=P4B7_BLOB or
            p4b4.git_blob(renderer.read_bytes())!=RENDERER_BLOB):
        raise ValueError("BLOCKED_P4B8_FROZEN_PARENT_DRIFT")
    if EXPERIMENT not in (workspace/"AutoDraw_Stage20"/"docs"/PREREG).read_text("utf8"):
        raise ValueError("BLOCKED_P4B8_MISSING_PREREG")
    output.mkdir(parents=True)
    results={}
    with tempfile.TemporaryDirectory(prefix="engine001-p4b8-original-") as folder:
        parent_dir=Path(folder)/"ORIGINAL_FRESH_P4B6"
        parent=p4b6.run(workspace,source,engine_js,renderer,parent_dir)
        if (parent["experiment"]!=p4b6.EXPERIMENT or
                parent["result"]!="NATIVE_GUARDS_QUALITY_NOT_ALL_PASS" or
                parent["original_source_SHA256"]!=SOURCE_SHA or
                parent["legacy_G32_P4c1_V44_used"] or
                parent["frozen_P4B5_ZIP_used_as_candidate"] or
                set(parent["methods"])!=set(METHODS)):
            raise ValueError("BLOCKED_P4B8_CHANGED_FRESH_SOURCE")
        protected=p4b4.source_critical_rois()
        for method in METHODS:
            p=parent["methods"][method]["arms"][ARM]
            strokes=json.loads((parent_dir/(method+"_G1_0_FINAL_STROKES.json")).read_text("utf8"))
            index=np.asarray(Image.open(parent_dir/(method+"_SOURCE_ENGINE_INDICES.png")),np.uint8)
            component=np.asarray(Image.open(parent_dir/(method+"_OWNER_COMPONENT.png")).convert("L"),np.uint8)>0
            owner=index==115
            if (index.shape!=p4b5.SHAPE or component.shape!=p4b5.SHAPE or
                    not component.any() or (component&~owner).any() or
                    len(strokes)!=COUNTS[method] or p["native_quality_pass"] or
                    p["native_final_alpha"]["24"][
                        "native_protected_foreign_face_eyes_hands_pixels"]!=2):
                raise ValueError("BLOCKED_P4B8_CHANGED_P4B6_OWNER")
            refpath=parent_dir/("NATIVE_G1_0_FINAL_REPAIRED_"+method)/(
                "P4B5-G1_0_FINAL_REPAIRED-"+method+"-color-115.png")
            reference=np.asarray(Image.open(refpath).convert("RGBA"),np.uint8)
            if (p4b7.protected_targets(reference,owner,protected)!=list(TARGETS) or
                    p4b7.pixel_alpha(reference,list(TARGETS))!=[35,35]):
                raise ValueError("BLOCKED_P4B8_P4B7_TARGET_DRIFT")
            x=output/("SOURCE_"+method)
            x.mkdir()
            for suffix in ("OWNER_COMPONENT","SOURCE_ENGINE_INDICES","SOURCE_RGB"):
                shutil.copyfile(parent_dir/(method+"_"+suffix+".png"),x/(suffix+".png"))
            (x/"P4B6_ORIGINAL_G1_FINAL_STROKES.json").write_text(
                json.dumps(strokes,ensure_ascii=False,indent=2)+"\n","utf8")
            native_result={}
            with p4b7.native_egret_session(workspace) as driver:
                control=p4b7.native_replay_in_session(
                    driver,output,method,"P4B8_REFERENCE_FULL",deepcopy(strokes))
                if not np.array_equal(control[:,:,3],reference[:,:,3]):
                    raise ValueError("BLOCKED_P4B8_REUSED_FIREFOX_ALPHA_DRIFT")
                print("P4B8_FULL_ALPHA_PARITY_PASS",method,flush=True)
                for arm in ARMS:
                    plan,ledger=surgery(
                        strokes,method,arm,component,
                        int(p["source_pruning"]["surviving_source_strokes"]))
                    base=method+"_"+arm
                    (output/(base+"_STROKES.json")).write_text(
                        json.dumps(plan,ensure_ascii=False,indent=2)+"\n","utf8")
                    (output/(base+"_LEDGER.json")).write_text(
                        json.dumps(ledger,ensure_ascii=False,indent=2)+"\n","utf8")
                    img=p4b7.native_replay_in_session(
                        driver,output,method,"P4B8_"+arm,plan)
                    blankname=output/("P4B7-"+method+"-P4B8_"+arm+"-blank.png")
                    real_blank=np.asarray(Image.open(blankname).convert("RGBA"),np.uint8)
                    measures,blank=p4b4.native_diagnostics(
                        img,real_blank,component,owner,protected)
                    if blank!=0:raise ValueError("BLOCKED_P4B8_NONEMPTY_BLANK")
                    a=measures["24"]
                    quality=bool(a["native_component_coverage"]>=COVERAGE_GATE and
                        a["native_protected_foreign_face_eyes_hands_pixels"]==0 and
                        a["native_foreign_distance_gt_T3_0"]==0 and
                        a["actual_native_ink_backing_pixels"]>0)
                    visual_difference(reference,img,component,owner,protected,
                                      output/(base+"_NATIVE_DIFF.png"))
                    native_result[arm]={
                        "actual_native_Egret":True,"native_blank_zero":blank,
                        "source_surgery_ledger":ledger,"native_alpha":measures,
                        "original_P4B7_protected_target_alpha":
                            p4b7.pixel_alpha(img,list(TARGETS)),
                        "coverage_delta_percentage_points":
                            100*(a["native_component_coverage"]-
                                 p["native_final_alpha"]["24"]["native_component_coverage"]),
                        "native_quality_pass":quality,
                        "status":"SURGERY_NATIVE_QUALITY_PASS" if quality else
                                 "SURGERY_NATIVE_QUALITY_FAIL"}
                    print("P4B8_NATIVE",method,arm,"coverage",
                          round(a["native_component_coverage"],7),"protected",
                          a["native_protected_foreign_face_eyes_hands_pixels"],
                          "far3",a["native_foreign_distance_gt_T3_0"],
                          "targets",native_result[arm][
                          "original_P4B7_protected_target_alpha"],flush=True)
            results[method]={
                "fresh_G1_original_native_alpha":p["native_final_alpha"],
                "culprit_ids":[strokes[i]["strokeId"] for i in CULPRITS[method]],
                "same_run_native_full_alpha_parity":True,"arms":native_result}
        shutil.copytree(parent_dir,output/"P4B6_ORIGINAL_FRESH_EVIDENCE")
    success=all(any(x["native_quality_pass"] for x in r["arms"].values())
                for r in results.values())
    members={str(f.relative_to(output)).replace("\\","/"):digest(f.read_bytes())
             for f in sorted(output.rglob("*")) if f.is_file()}
    report={
        "experiment":EXPERIMENT,"prereg_id":EXPERIMENT,
        "result":"SURGICAL_ALL_GATES_PASS" if success else
                 "SURGICAL_NATIVE_QUALITY_NOT_ALL_PASS",
        "native_Egret_scenes_8_complete":True,
        "original_source_SHA256":SOURCE_SHA,"source_key":"C_192_D_COMPONENT24",
        "source_owner_index":115,"P4B6_git_blob":P4B6_BLOB,
        "P4B7_git_blob":P4B7_BLOB,"renderer_git_blob":RENDERER_BLOB,
        "original_P4B6_recomputed_fresh":True,
        "legacy_G32_P4c1_V44_used":False,
        "arms":list(ARMS),"native_alpha_gate":ALPHA,
        "original_native_coverage_gate":COVERAGE_GATE,
        "original_protected_foreign_gate":0,
        "original_spill_logical_gate":SPILL_GATE,
        "original_stroke_cap":MAX_STROKES,"original_vertex_cap_NOT_CHALK":MAX_VERTICES,
        "methods":results,"production_promotion":False,
        "E4_game_runtime":"NOT_RUN","E5_independent":"NOT_RUN",
        "exact_run_bound_CHALK":None,
        "github_sha":os.getenv("GITHUB_SHA"),"github_run_id":os.getenv("GITHUB_RUN_ID"),
        "file_sha256":members}
    (output/"README_REVIEW_RU.txt").write_text(
        "P4B8 — сравнение 4 вариантов локального исправления точных штрихов.\n"
        "DROP2 — удалить два штриха; WIDTH1 — уменьшить кисть до1;\n"
        "TRIM50 — укоротить штрихи вдвое; WIDTH1_TRIM50 — оба изменения.\n"
        "Игровая Egret кисть реальная, не модель. Всё остальное неизменно.\n"
        "Пороги: >=99% своей области, 0 пикселей защищённого чужого,\n"
        "0 чужих пикселей дальше 3 логических px. CHALK не измерялся.\n",
        "utf8")
    (output/"report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
    return report


if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("--workspace",type=Path,required=True)
    cli.add_argument("--source",type=Path,required=True)
    cli.add_argument("--engine-js",type=Path,required=True)
    cli.add_argument("--renderer",type=Path,required=True)
    cli.add_argument("--output",type=Path,required=True)
    args=cli.parse_args()
    try:
        r=run(args.workspace,args.source,args.engine_js,args.renderer,args.output)
    except Exception as error:
        args.output.mkdir(parents=True,exist_ok=True)
        (args.output/"FAILED_EVIDENCE.json").write_text(
            json.dumps({"experiment":EXPERIMENT,"status":"BLOCKED",
                        "error":str(error),"error_type":type(error).__name__,
                        "github_sha":os.getenv("GITHUB_SHA"),"github_run_id":os.getenv("GITHUB_RUN_ID"),
                        "exact_CHALK":None},ensure_ascii=False,indent=2)+"\n","utf8")
        raise
    print("P4B8_RESULT",r["result"],"E4_E5_EXACT_CHALK_NOT_RUN",flush=True)

#!/usr/bin/env python3
"""P4B6 fixed original-source protected foreign centerline clearance ablation.

Two prereg safety margins .5/1.0 vs selected P4B5 source model-safe strokes.
Actual Egret 5.4.1 BoardPane/WebGL native RGBA determines coverage and spills.
Original RGB P3D and parent P4B5 regenerated in current run, no archived ZIP
input, no G32/P4c1/V44 candidate, no live E4 or exact CHALK.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import run_engine001_b1r_p4b5_protected_baseline_rebalance as p4b5
import run_engine001_b1r_p4b4_boundary_tolerance_sweep as p4b4
import run_engine001_b1r_p4b2_native_edge_repair as p4b2
from run_engine001_b1r_p1_fullrgb_edge_aware import check_source
from run_engine001_b1r_p2_joint_region_outline import digest

EXPERIMENT="ENGINE001_B1R_P4B6_SOURCE_PROTECTED_MARGIN_V1"
FROZEN_P4B5_BLOB="6bde1a99ff200c55cd7929f7cea32eae0aba9178"
FROZEN_P4B4_BLOB="6f67edcb942018bb006ed60b853470e4a202408d"
RENDERER_BLOB="76d950e0a8911888a9df3b675b866519ecf7bba4"
ARMS={"G0_5":.5, "G1_0":1.0}
METHODS=p4b5.METHODS
SOURCE=p4b5.SOURCE
OWNER=p4b5.OWNER
SHAPE=p4b5.SHAPE
MAX_STROKES=250
MAX_VERTICES=500
LEGACY_NATIVE_SPILL=3.0
COVERAGE_GATE=.99
NATIVE_ALPHA=24


def _guard_distance_map(full_owner:np.ndarray, protected:np.ndarray):
    if (full_owner.shape!=SHAPE or protected.shape!=SHAPE or
            full_owner.dtype!=np.bool_ or protected.dtype!=np.bool_ or
            not full_owner.any() or not protected.any()):
        raise ValueError("BLOCKED_P4B6_SOURCE_MASK_SHAPE")
    foreign=protected&~full_owner
    if not foreign.any():
        raise ValueError("BLOCKED_P4B6_NO_PROTECTED_FOREIGN_COLOR")
    return cv2.distanceTransform(
        (~foreign).astype(np.uint8),cv2.DIST_L2,cv2.DIST_MASK_PRECISE)


def clearance(points:list, width:int, dist:np.ndarray):
    """MODEL_ONLY centerline-to-protected foreign Euclidean clearance.

    Path coordinates are SOURCE logical x0..149,y0..239, not board x155.
    """
    if (not isinstance(points,list) or not 2<=len(points)<=128 or
            type(width)!=int or not 1<=width<=10 or
            dist.shape!=SHAPE or not np.issubdtype(dist.dtype,np.floating)):
        raise ValueError("BLOCKED_P4B6_CLEARANCE_INPUT")
    arr=np.asarray(points,dtype=np.float64)
    if (arr.shape!=(len(points),2) or not np.isfinite(arr).all() or
            np.any(arr[:,0]<0) or np.any(arr[:,0]>=150) or
            np.any(arr[:,1]<0) or np.any(arr[:,1]>=240)):
        raise ValueError("BLOCKED_P4B6_UNSAFE_SOURCE_POINTS")
    rounded=np.rint(arr).astype(np.int32)
    line=np.zeros(SHAPE,dtype=np.uint8)
    cv2.polylines(line,[rounded.reshape(-1,1,2)],False,
                  255,1,cv2.LINE_8)
    if not line.any():
        raise ValueError("BLOCKED_P4B6_EMPTY_CENTERLINE")
    return float(dist[line!=0].min()-width/2.0)


def stroke_clearance(stroke:dict, dist:np.ndarray):
    if (not isinstance(stroke,dict) or
            stroke.get("colorIndex")!=OWNER or
            not isinstance(stroke.get("points"),list)):
        raise ValueError("BLOCKED_P4B6_WRONG_SOURCE_RGB_OWNER")
    points=[(float(pt["x"])-p4b5.ROI_X0,float(pt["y"]))
            for pt in stroke["points"]]
    return clearance(points,stroke["width"],dist)


def prune_with_margin(pruned_parent:list[dict], full_owner:np.ndarray,
                      protected:np.ndarray, arm:str):
    if (arm not in ARMS or not isinstance(pruned_parent,list) or
            not 1<=len(pruned_parent)<MAX_STROKES or
            any(s.get("colorIndex")!=OWNER for s in pruned_parent)):
        raise ValueError("BLOCKED_P4B6_PRUNE_INPUT")
    dist=_guard_distance_map(full_owner,protected)
    accepted=[]
    dropped=[]
    mapping=[]
    for row,s in enumerate(pruned_parent):
        gap=stroke_clearance(s,dist)
        if gap<=ARMS[arm]:
            dropped.append({
                "P4B5_pruned_order":row,
                "P4B5_pruned_id":s["strokeId"],
                "width":s["width"],
                "source_clearance_minus_half_width_logical_MODEL_ONLY":gap,
                "points":s["points"],
            })
            continue
        keep={k:s[k] for k in
              ("strokeId","width","colorIndex","colorRgb","points")}
        keep["strokeId"]="icon-%d"%len(accepted)
        mapping.append({
            "P4B5_pruned_order":row,
            "old_id":s["strokeId"],
            "new_id":keep["strokeId"],
            "coordinates_unchanged":True,
            "source_model_clearance_logical":gap,
        })
        accepted.append(keep)
    if not accepted or sum(len(s["points"]) for s in accepted)>=MAX_VERTICES:
        raise ValueError("BLOCKED_P4B6_PRUNED_BASELINE_EMPTY_OR_COST")
    return accepted,{"arm":arm,
                     "additional_original_P4B5_model_safe_strokes_removed":len(dropped),
                     "surviving_source_strokes":len(accepted),
                     "retained_renumbered":mapping,
                     "dropped_original_geometry":dropped,
                     "model_is_NOT_native_Egret":True}


def filter_candidate_margin(candidates:list[dict], full_owner:np.ndarray,
                            protected:np.ndarray, arm:str):
    if arm not in ARMS or not isinstance(candidates,list):
        raise ValueError("BLOCKED_P4B6_CANDIDATE_INPUT")
    dist=_guard_distance_map(full_owner,protected)
    kept=[]
    for c in candidates:
        if (not isinstance(c,dict) or
                "source_xy" not in c or "width" not in c or
                "projected_max_nonowner_distance_MODEL_ONLY" not in c):
            raise ValueError("BLOCKED_P4B6_UNPINNED_MODEL_CANDIDATE")
        # The common catalog is frozen at <=4 logical px by P4B4.
        # P4B6's legacy T3.0 arm must SKIP (not abort on) members >3.
        if c["projected_max_nonowner_distance_MODEL_ONLY"]>LEGACY_NATIVE_SPILL:
            continue
        val=clearance(c["source_xy"],int(c["width"]),dist)
        if val>ARMS[arm]:
            kept.append(c)
    return kept


def _read_mask(z:Path,method:str):
    return np.asarray(Image.open(z/(method+"_OWNER_COMPONENT.png")).convert("L"),
                      np.uint8)>0


def run(workspace:Path, source:Path, engine_js:Path, renderer:Path,
        output:Path):
    if output.exists():
        raise ValueError("BLOCKED_P4B6_OUTPUT_EXISTS")
    check_source(source)
    if (p4b4.git_blob(Path(p4b5.__file__).read_bytes())!=FROZEN_P4B5_BLOB or
            p4b4.git_blob(Path(p4b4.__file__).read_bytes())!=FROZEN_P4B4_BLOB or
            p4b4.git_blob(renderer.read_bytes())!=RENDERER_BLOB):
        raise ValueError("BLOCKED_P4B6_PARENT_OR_RENDERER_GIT_BLOB")
    output.mkdir(parents=True)
    from run_engine001_b1r_p3b_engine128_adaptive32 import (
        SOURCE_SHA,ENGINE_GIT_BLOB_SHA1,read_engine_palette)
    engine,_=read_engine_palette(engine_js)
    protected=p4b4.source_critical_rois()
    results={}
    with tempfile.TemporaryDirectory(prefix="engine001-p4b6-original-only-") as d:
        parent_dir=Path(d)/"P4B5_same_run_original"
        parent=p4b5.run(workspace,source,engine_js,renderer,parent_dir)
        if (parent["experiment"]!=p4b5.EXPERIMENT or
                parent["status"]!="NATIVE_PROTECTED_QUALITY_NOT_ALL_PASS" or
                not parent["source_original_only_all_EF_P3D_quality_pass"] or
                parent["legacy_G32_P4c1_V44_used_as_candidate"] or
                parent["frozen_old_ZIPs_as_source"] or
                set(parent["methods"])!=set(METHODS)):
            raise ValueError("BLOCKED_P4B6_PARENT_ORIGINAL_P4B5_DRIFT")
        shutil.copyfile(parent_dir/"report.json",
                        output/"FRESH_PARENT_P4B5_E3_REPORT.json")
        shutil.copyfile(parent_dir/"SOURCE_ORIGINAL_LOGICAL_RGB.png",
                        output/"SOURCE_ORIGINAL_LOGICAL_RGB.png")
        for method in METHODS:
            component=_read_mask(parent_dir,method)
            index=np.asarray(Image.open(parent_dir/(
                method+"_SOURCE_ENGINE_INDICES.png")),np.uint8)
            full_owner=index==OWNER
            if (not component.any() or np.any(component&~full_owner) or
                    not (protected&~full_owner).any()):
                raise ValueError("BLOCKED_P4B6_CHANGED_SOURCE_COLOR")
            for postfix in ("OWNER_COMPONENT","SOURCE_ENGINE_INDICES","SOURCE_RGB"):
                shutil.copyfile(parent_dir/(method+"_"+postfix+".png"),
                                output/(method+"_"+postfix+".png"))
            parent_strokes=json.loads((parent_dir/(
                method+"_SOURCE_PROTECTED_PRUNED_STROKES.json")).read_text("utf8"))
            parent_data=parent["methods"][method]
            if (parent_data["pruned_strokes_count"]!=len(parent_strokes) or
                    parent_data["unsafe_original_A_strokes_removed"]!=48 or
                    parent_data["native_actual_quality_pass"]):
                raise ValueError("BLOCKED_P4B6_ORIGINAL_PARENT_SAFETY_DRIFT")
            shutil.copyfile(parent_dir/(
                method+"_SOURCE_PROTECTED_PRUNED_STROKES.json"),
                output/(method+"_P4B5_FRESH_MODEL_SAFE_PARENT_STROKES.json"))
            method_results={
                "P4B5_original_model_safe_parent_strokes":len(parent_strokes),
                "P4B5_original_source_pruned_parent_protected":
                    parent_data["original_pruned_native_alpha"]["24"]
                    ["native_protected_foreign_face_eyes_hands_pixels"],
                "P4B5_native_final_protected":
                    parent_data["native_final_alpha"]["24"]
                    ["native_protected_foreign_face_eyes_hands_pixels"],
                "arms":{},
            }
            for arm,margin in ARMS.items():
                kept,ledger=prune_with_margin(
                    parent_strokes,full_owner,protected,arm)
                (output/(method+"_"+arm+"_ADDITIONAL_PRUNING.json")).write_text(
                    json.dumps(ledger,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
                (output/(method+"_"+arm+"_BASELINE_STROKES.json")).write_text(
                    json.dumps(kept,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
                baseline=p4b5.native_replay(
                    workspace,method,arm+"_GUARD_BASELINE",kept,output)
                base_scores,base_blank=p4b5.source_metrics(
                    baseline,component,full_owner,protected)
                if base_blank:
                    raise ValueError("BLOCKED_P4B6_NATIVE_BLANK_HAS_INK")
                weights,eligible,missing,miss_detail=p4b2.boundary_missing(
                    baseline["color-115"],component)
                if eligible.any():
                    original_catalog=p4b4.candidate_catalog(
                        component,full_owner,weights,eligible,protected)
                    adm=filter_candidate_margin(
                        original_catalog,full_owner,protected,arm)
                    if adm:
                        corrections,decision=p4b4.choose_from_catalog(
                            adm,weights,kept,engine,"T3_0")
                    else:
                        corrections=[]
                        decision={"catalog_total_before_guard":len(original_catalog),
                                  "catalog_guard_admissible":0,
                                  "no_source_guard_safe_correction":True}
                    decision["catalog_total_before_guard"]=len(original_catalog)
                    decision["catalog_guard_admissible"]=len(adm)
                else:
                    corrections=[]
                    decision={"no_source_edge_gaps_at_alpha24":True,
                              "catalog_total_before_guard":0,
                              "catalog_guard_admissible":0}
                final=kept+corrections
                cost=sum(len(s["points"]) for s in final)
                if (not final or len(final)>MAX_STROKES or cost>MAX_VERTICES or
                        any(s.get("colorIndex")!=OWNER or
                            not 1<=s.get("width",0)<=10 for s in final)):
                    raise ValueError("BLOCKED_P4B6_COLOR_WIDTH_OR_VERTEX_BUDGET")
                (output/(method+"_"+arm+"_REPAIR_STROKES.json")).write_text(
                    json.dumps(corrections,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
                (output/(method+"_"+arm+"_FINAL_STROKES.json")).write_text(
                    json.dumps(final,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
                replay=p4b5.native_replay(
                    workspace,method,arm+"_FINAL_REPAIRED",final,output)
                scored,blank=p4b5.source_metrics(
                    replay,component,full_owner,protected)
                a24=scored["24"];b24=base_scores["24"]
                quality=bool(
                    blank==0 and
                    a24["native_component_coverage"]>=COVERAGE_GATE and
                    a24["native_component_coverage"]>=b24[
                        "native_component_coverage"]-1e-9 and
                    a24["native_foreign_distance_gt_T3_0"]==0 and
                    a24["native_protected_foreign_face_eyes_hands_pixels"]==0 and
                    a24["actual_native_ink_backing_pixels"]>0)
                method_results["arms"][arm]={
                    "model_only_protected_margin_source_logical":margin,
                    "source_pruning":ledger,
                    "original_Safe_P4B5_model_strokes_geometry_unchanged":True,
                    "same_run_current_original_only_EF":True,
                    "model_candidate_filter":decision,
                    "total_strokes":len(final),
                    "total_synthetic_vertices_NOT_CHALK":cost,
                    "added_width_1to10_repair_count":len(corrections),
                    "actual_real_Egret_native_baseline":True,
                    "actual_real_Egret_native_final":True,
                    "native_blank_baseline":base_blank,
                    "native_blank_final":blank,
                    "native_baseline_alpha":base_scores,
                    "native_final_alpha":scored,
                    "source_original_RGB_or_index_changed":False,
                    "native_quality_pass":quality,
                    "quality_status":"NATIVE_SOURCE_PROTECTED_MARGIN_PASS" if quality
                      else "NATIVE_SOURCE_PROTECTED_MARGIN_QUALITY_FAIL",
                }
                print("P4B6_NATIVE",method,arm,
                      "pruned_extra",ledger[
                          "additional_original_P4B5_model_safe_strokes_removed"],
                      "baseline_protected",b24[
                          "native_protected_foreign_face_eyes_hands_pixels"],
                      "final_protected",a24[
                          "native_protected_foreign_face_eyes_hands_pixels"],
                      "coverage",round(a24["native_component_coverage"],6),
                      "beyond3",a24["native_foreign_distance_gt_T3_0"],
                      "strokes",len(final),
                      "status",method_results["arms"][arm]["quality_status"],
                      flush=True)
            results[method]=method_results
    if set(results)!=set(METHODS) or any(set(x["arms"])!=set(ARMS)
                                    for x in results.values()):
        raise AssertionError("BLOCKED_P4B6_MISSING_8_NATIVE_SCENES")
    success=all(x["native_quality_pass"] for data in results.values()
                for x in data["arms"].values())
    (output/"README_REVIEW_RU.txt").write_text(
        "P4B6: два заранее фиксированных источниковых защитных отступа "
        "0.5 и 1.0 логического px ОТ ЧУЖИХ защищённых лиц/глаз/рук.\n"
        "Допуск выхода за цветовую область остаётся 3 логических px; "
        "порог покрытия 99% и нулевой защищённый чужой цвет.\n"
        "Сначала реальный Egret pruned baseline, затем реальные Egret "
        "correction replay, E и F независимо.\n"
        "MODEL_ONLY clearance/candidate rankings не доказывают геометрию "
        "игровой кисти; NATIVE_* PNG подлинные архивные BoardPane/WebGL.\n"
        "Восемь настоящих сцен: 2 карты × 2 guards × 2 стадий. "
        "E4 живой игры/E5/CHALK NOT_RUN.\n",
        encoding="utf8")
    hashes={
        str(p.relative_to(output)).replace("\\","/"):digest(p.read_bytes())
        for p in sorted(output.rglob("*")) if p.is_file()
    }
    report={
        "experiment":EXPERIMENT,
        "prereg_id":EXPERIMENT,
        "result":"ALL_FOUR_NATIVE_GUARD_QUALITY_PASS" if success else
                 "NATIVE_GUARDS_QUALITY_NOT_ALL_PASS",
        "native_Egret_scenes_8_complete":True,
        "original_source_SHA256":SOURCE_SHA,
        "engine_blob_sha1":ENGINE_GIT_BLOB_SHA1,
        "renderer_blob_sha1":RENDERER_BLOB,
        "parent_P4B5_runner_blob":FROZEN_P4B5_BLOB,
        "parent_P4B4_runner_blob":FROZEN_P4B4_BLOB,
        "P4B5_recomputed_current_original_only":True,
        "P3D_EF_original_source_gates_unchanged":True,
        "legacy_G32_P4c1_V44_used":False,
        "frozen_P4B5_ZIP_used_as_candidate":False,
        "source_key":SOURCE,
        "source_owner_index":OWNER,
        "source_centerline_extra_guards_logical":ARMS,
        "native_spill_logical_gate_unchanged":LEGACY_NATIVE_SPILL,
        "source_owner_coverage_gate_unchanged":COVERAGE_GATE,
        "max_strokes":MAX_STROKES,
        "max_vertices_NOT_CHALK":MAX_VERTICES,
        "methods":results,
        "E4_game_runtime":"NOT_RUN",
        "E5_independent":"NOT_RUN",
        "exact_run_bound_CHALK":None,
        "production_promotion":False,
        "github_sha":os.getenv("GITHUB_SHA"),
        "github_run_id":os.getenv("GITHUB_RUN_ID"),
        "file_sha256":hashes,
    }
    (output/"report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf8")
    return report


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--workspace",type=Path,required=True)
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--engine-js",type=Path,required=True)
    ap.add_argument("--renderer",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    try:
        r=run(args.workspace,args.source,args.engine_js,args.renderer,args.output)
    except Exception as error:
        args.output.mkdir(parents=True,exist_ok=True)
        (args.output/"FAILED_EVIDENCE.json").write_text(
            json.dumps({
                "experiment":EXPERIMENT,"status":"BLOCKED",
                "error_type":type(error).__name__,"reason":str(error),
                "github_sha":os.getenv("GITHUB_SHA"),
                "github_run_id":os.getenv("GITHUB_RUN_ID"),
                "true_native_quality_not_established":True,
                "exact_run_bound_CHALK":None,
            },ensure_ascii=False,indent=2)+"\n",encoding="utf8")
        raise
    print("P4B6_RESULT",r["result"],"E4/E5/EXACT_CHALK_NOT_RUN")

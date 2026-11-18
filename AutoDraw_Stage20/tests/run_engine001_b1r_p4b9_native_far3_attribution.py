#!/usr/bin/env python3
"""P4B9 real Egret farther3 owner-foreign native stroke attribution, source-only."""
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
import run_engine001_b1r_p4b6_source_protected_margin as p4b6
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
import run_engine001_b1r_p4b8_causal_stroke_surgery as p4b8
import run_engine001_b1r_p4b5_protected_baseline_rebalance as p4b5
import run_engine001_b1r_p4b4_boundary_tolerance_sweep as p4b4
from run_engine001_b1r_p1_fullrgb_edge_aware import check_source
from run_engine001_b1r_p2_joint_region_outline import digest

EXPERIMENT="ENGINE001_B1R_P4B9_NATIVE_FAR3_ATTRIBUTION_V1"
PREREG="ENGINE001_B1R_P4B9_NATIVE_FAR3_ATTRIBUTION_PREREG_2026-11-18.md"
P4B6_BLOB="2f9ca1756da58e7062fcae6c6c64c83e4db79ea9"
P4B7_BLOB="87ea292c01c75e594c4ff09acf716c4500e88644"
P4B8_BLOB="9ddf8e2f745de4f78006b14c00e99e74c2f3cb67"
RENDERER_BLOB="76d950e0a8911888a9df3b675b866519ecf7bba4"
SOURCE_SHA="07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
METHODS=p4b8.METHODS
EXPECTED_FAR={"E_SOBEL90":4,"F_SOBEL90_LAB12":2}
MAX_SPLIT=64
MAX_LOO=16
ALPHA=24
COVERAGE_GATE=.99
SPILL_GATE=3.
MAX_STROKES=250
MAX_VERTICES=500


def native_far3_targets(rgba:np.ndarray,full_owner:np.ndarray):
    """Real Egret RGBA; exact P4B4 true backing 3x source owner distance."""
    if (rgba.shape!=p4b5.BACKING or rgba.dtype!=np.uint8 or
            full_owner.shape!=p4b5.SHAPE or full_owner.dtype!=np.bool_ or
            not full_owner.any()):
        raise ValueError("BLOCKED_P4B9_NATIVE_SOURCE_SHAPE")
    owner=p4b4.backing(full_owner)
    d=cv2.distanceTransform(
        (~owner).astype(np.uint8),cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
    yx=np.argwhere((rgba[:,:,3]>=ALPHA)&~owner&(d>SPILL_GATE*3))
    return [(int(y),int(x)) for y,x in yx]


def _native_score(rgba,blank,component,owner,protected):
    metrics,blank_sum=p4b4.native_diagnostics(
        rgba,blank,component,owner,protected)
    if blank_sum!=0:
        raise ValueError("BLOCKED_P4B9_NONEMPTY_NATIVE_BLANK")
    return metrics


def run(workspace:Path,source:Path,engine_js:Path,renderer:Path,output:Path):
    if output.exists():raise ValueError("BLOCKED_P4B9_OUTPUT_EXISTS")
    check_source(source)
    if (p4b4.git_blob(Path(p4b6.__file__).read_bytes())!=P4B6_BLOB or
            p4b4.git_blob(Path(p4b7.__file__).read_bytes())!=P4B7_BLOB or
            p4b4.git_blob(Path(p4b8.__file__).read_bytes())!=P4B8_BLOB or
            p4b4.git_blob(renderer.read_bytes())!=RENDERER_BLOB):
        raise ValueError("BLOCKED_P4B9_PARENT_OR_NATIVE_BLOB")
    if EXPERIMENT not in (workspace/"AutoDraw_Stage20"/"docs"/PREREG).read_text("utf8"):
        raise ValueError("BLOCKED_P4B9_MISSING_PREREG")
    output.mkdir(parents=True)
    results={}
    with tempfile.TemporaryDirectory(prefix="engine001-p4b9-original-") as tmp:
        parent_dir=Path(tmp)/"FRESH_ORIGINAL_P4B6"
        parent=p4b6.run(workspace,source,engine_js,renderer,parent_dir)
        if (parent["experiment"]!=p4b6.EXPERIMENT or
                parent["result"]!="NATIVE_GUARDS_QUALITY_NOT_ALL_PASS" or
                parent["original_source_SHA256"]!=SOURCE_SHA or
                parent["legacy_G32_P4c1_V44_used"] or
                parent["frozen_P4B5_ZIP_used_as_candidate"] or
                set(parent["methods"])!=set(METHODS)):
            raise ValueError("BLOCKED_P4B9_ORIGINAL_SOURCE_DRIFT")
        protected=p4b4.source_critical_rois()
        for method in METHODS:
            meta=parent["methods"][method]["arms"]["G1_0"]
            original=json.loads((parent_dir/(method+"_G1_0_FINAL_STROKES.json")).read_text("utf8"))
            index=np.asarray(Image.open(parent_dir/(method+"_SOURCE_ENGINE_INDICES.png")),np.uint8)
            component=np.asarray(Image.open(parent_dir/(method+"_OWNER_COMPONENT.png")).convert("L"),np.uint8)>0
            owner=index==115
            if (index.shape!=p4b5.SHAPE or not component.any() or
                    (component&~owner).any() or
                    meta["native_quality_pass"] or
                    len(original)!=p4b8.COUNTS[method] or
                    meta["native_final_alpha"]["24"][
                        "native_protected_foreign_face_eyes_hands_pixels"]!=2):
                raise ValueError("BLOCKED_P4B9_SOURCE_OWNER_OR_STROKE_DRIFT")
            trim,ledger=p4b8.surgery(
                original,method,"TRIM50",component,
                int(meta["source_pruning"]["surviving_source_strokes"]))
            outputfile=output/(method+"_TRIM50_SOURCE_STROKES.json")
            outputfile.write_text(json.dumps(trim,ensure_ascii=False,indent=2)+"\n","utf8")
            (output/(method+"_TRIM50_SOURCE_LEDGER.json")).write_text(
                json.dumps(ledger,ensure_ascii=False,indent=2)+"\n","utf8")
            # New independent genuine Egret reference, no frozen ZIP replay.
            fresh=p4b5.native_replay(
                workspace,method,"P4B9_TRIM50_REFERENCE",trim,output)
            ref=fresh["color-115"]
            scores=_native_score(ref,fresh["blank"],component,owner,protected)
            a=scores["24"]
            targets=native_far3_targets(ref,owner)
            if (len(targets)!=EXPECTED_FAR[method] or
                    a["native_foreign_distance_gt_T3_0"]!=len(targets) or
                    a["native_protected_foreign_face_eyes_hands_pixels"]!=0 or
                    abs(a["native_component_coverage"]-
                        meta["native_final_alpha"]["24"]["native_component_coverage"])>1e-12 or
                    not (0<a["native_component_coverage"]<COVERAGE_GATE)):
                raise ValueError("BLOCKED_P4B9_FROZEN_P4B8_TRIM50_DRIFT")
            original_alpha=p4b7.pixel_alpha(ref,targets)
            if any(x<ALPHA for x in original_alpha):
                raise ValueError("BLOCKED_P4B9_FAR_TARGET_ALPHA")
            stage_dir=output/(method+"_SOURCE")
            stage_dir.mkdir()
            for suffix in ("SOURCE_ENGINE_INDICES","OWNER_COMPONENT","SOURCE_RGB"):
                shutil.copyfile(parent_dir/(method+"_"+suffix+".png"),
                                stage_dir/(suffix+".png"))
            with p4b7.native_egret_session(workspace) as driver:
                second=p4b7.native_replay_in_session(
                    driver,output,method,"P4B9_FULL_CONTROL",trim)
                if not np.array_equal(second[:,:,3],ref[:,:,3]):
                    raise ValueError("BLOCKED_P4B9_TRUE_NATIVE_PARITY")
                print("P4B9_TRUE_NATIVE_PARITY",method,"far3",targets,flush=True)
                c=[0]
                def draw(indices,stage):
                    scene=p4b7.native_replay_in_session(
                        driver,output,method,"P4B9_"+stage,
                        p4b7.normalized_subset(trim,indices))
                    c[0]+=1
                    alpha=p4b7.pixel_alpha(scene,targets)
                    print("P4B9_NATIVE_SUBSET",method,stage,"count",len(indices),
                          "alpha",alpha,"scene",c[0],flush=True)
                    return alpha
                tracing=p4b7.split_trace(len(trim),original_alpha,draw,MAX_SPLIT)
                leaves=sorted(tracing["leaves"])
                leave_one_out=[]
                state=tracing["status"]
                if state=="ATTRIBUTION_LEAVES_COMPLETE":
                    if len(leaves)>MAX_LOO or not leaves:
                        state="PARTIAL_TOO_MANY_CAUSAL_LEAVES"
                    else:
                        for i in leaves:
                            idx=tuple(x for x in range(len(trim)) if x!=i)
                            without=draw(idx,"LOO_%03d"%i)
                            necessary=p4b7.necessary_pixels(original_alpha,without)
                            leave_one_out.append({
                                "original_final_stroke_index":i,
                                "original_final_stroke_id":trim[i]["strokeId"],
                                "actual_brush_width":trim[i]["width"],
                                "original_stroke_points":trim[i]["points"],
                                "target_alpha_without_stroke":without,
                                "individually_necessary_target_indices":necessary,
                            })
                        state="COMPLETE_NATIVE_FAR3_ATTRIBUTION"
            data={
                "source_method":method,
                "source_arm":"P4B8_TRIM50",
                "native_real_egret_complete":True,
                "full_native_reference_and_control_alpha_identical":True,
                "native_reference_alpha":scores,
                "far3_target_backing_yx":[list(t) for t in targets],
                "far3_original_native_target_alpha":original_alpha,
                "far3_original_source_logical_xy":[[x//3-155,y//3] for y,x in targets],
                "frozen_far3_3logical_threshold":SPILL_GATE,
                "baseline_protected_foreign_alpha24":a[
                    "native_protected_foreign_face_eyes_hands_pixels"],
                "trim50_source_ledger":ledger,
                "native_group_replays":tracing["calls"],
                "max_split_replays":MAX_SPLIT,
                "raw_split_status":tracing["status"],
                "group_ledger":tracing["ledger"],
                "possible_contributor_indices":leaves,
                "possible_contributor_ids":[trim[i]["strokeId"] for i in leaves],
                "possible_contributor_raw_alpha":{
                    str(i):tracing["leaves"][i] for i in leaves},
                "leave_one_out_native":leave_one_out,
                "additional_loo_scenes":c[0]-tracing["calls"],
                "causal_status":state,
                "full_paint_native_quality_pass":False,
            }
            (output/(method+"_FAR3_ATTRIBUTION.json")).write_text(
                json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
            print("P4B9_FAR3_ATTRIBUTION",method,state,"targets",targets,
                  "possible_strokes",data["possible_contributor_ids"],
                  "native_groups",tracing["calls"],"loo",len(leave_one_out),flush=True)
            results[method]=data
        shutil.copytree(parent_dir,output/"FRESH_P4B6_ORIGINAL_EGRET_EVIDENCE")
    state=("COMPLETE_NATIVE_FAR3_ATTRIBUTION" if all(
        rec["causal_status"]=="COMPLETE_NATIVE_FAR3_ATTRIBUTION"
        for rec in results.values()) else "PARTIAL_NATIVE_FAR3_ATTRIBUTION")
    hashes={
        str(x.relative_to(output)).replace("\\","/"):digest(x.read_bytes())
        for x in sorted(output.rglob("*")) if x.is_file()
    }
    report={
        "experiment":EXPERIMENT,"prereg_id":EXPERIMENT,
        "result":state,"source_key":"C_192_D_COMPONENT24",
        "original_source_sha256":SOURCE_SHA,
        "original_recomputed_same_run":True,
        "native_Egret_EF_reference_parity":True,
        "native_test_alpha":ALPHA,"spill_logical_gate":SPILL_GATE,
        "native_selected_owner_coverage_gate":COVERAGE_GATE,
        "max_strokes":MAX_STROKES,"synthetic_vertices_cap_NOT_CHALK":MAX_VERTICES,
        "p4b6_git_blob":P4B6_BLOB,"p4b7_git_blob":P4B7_BLOB,
        "p4b8_git_blob":P4B8_BLOB,"renderer_git_blob":RENDERER_BLOB,
        "legacy_G32_P4c1_V44_used":False,
        "methods":results,
        "native_full_artwork_quality_pass":False,
        "production_promotion":False,
        "E4_game_runtime":"NOT_RUN","E5_independent":"NOT_RUN",
        "exact_game_CHALK":None,
        "github_sha":os.getenv("GITHUB_SHA"),"github_run_id":os.getenv("GITHUB_RUN_ID"),
        "file_sha256":hashes,
    }
    (output/"README_REVIEW_RU.txt").write_text(
        "P4B9. Нативные пиксели за пределами3 логических px для TRIM50 E/F.\n"
        "В файлах FAR3_ATTRIBUTION.json реальные координаты PNG и виновные штрихи.\n"
        "Все PNG — настоящий рендерер игры Egret; в CI одиночные штрихи и\n"
        "планы без одного штриха повторно отрисованы. Это диагностика, не\n"
        "исправление всего рисунка. Покрытие >=99% остаётся не достигнутым.\n",
        "utf8")
    (output/"report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
    return report


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--workspace",type=Path,required=True)
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--engine-js",type=Path,required=True)
    ap.add_argument("--renderer",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    try:r=run(a.workspace,a.source,a.engine_js,a.renderer,a.output)
    except Exception as exc:
        a.output.mkdir(parents=True,exist_ok=True)
        (a.output/"FAILED_EVIDENCE.json").write_text(
            json.dumps({"experiment":EXPERIMENT,"status":"BLOCKED",
                        "error":str(exc),"error_type":type(exc).__name__,
                        "github_sha":os.getenv("GITHUB_SHA"),
                        "github_run_id":os.getenv("GITHUB_RUN_ID"),
                        "actual_native_quality_NOT_ESTABLISHED":True},
                       ensure_ascii=False,indent=2)+"\n","utf8")
        raise
    print("P4B9_RESULT",r["result"],"E4_E5_EXACT_CHALK_NOT_RUN",flush=True)

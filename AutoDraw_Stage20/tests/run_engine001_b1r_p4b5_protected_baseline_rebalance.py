#!/usr/bin/env python3
"""B1-R-P4B5: original-source protected A-baseline pruning, native Egret refill.

Prune only source-model strokes that intersect original protected FOREIGN
face/eye/hand owners. Then measure genuine Egret gaps, refill at legacy3px
with widths1..10, fixed250 strokes /500 vertices, source E/F unchanged.
No legacy G32/V44 candidates; no live E4/exact CHALK.
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

import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
import run_engine001_b1r_p4b2_native_edge_repair as p4b2
import run_engine001_b1r_p4b4_boundary_tolerance_sweep as p4b4
from run_engine001_b1r_p3b_engine128_adaptive32 import (
    ENGINE_GIT_BLOB_SHA1,SOURCE_SHA,read_engine_palette,
)
from run_engine001_b1r_p1_fullrgb_edge_aware import check_source
from run_engine001_b1r_p2_joint_region_outline import digest
from run_engine001_complex_holdout_v5 import native_batch

EXPERIMENT="ENGINE001_B1R_P4B5_PROTECTED_BASELINE_REBALANCE_V1"
P4B1_BLOB="b95aa361cf2ec94d5fa28e7309bd3e4af15eca93"
P4B2_BLOB="0053829480c6327ef5c541024593f6e0018aa35e"
P4B4_BLOB="6f67edcb942018bb006ed60b853470e4a202408d"
RENDERER_BLOB="76d950e0a8911888a9df3b675b866519ecf7bba4"
SOURCE=p4b2.SOURCE
METHODS=p4b2.METHODS
OWNER=115
ALPHA=24
MAX_STROKES=250
MAX_VERTICES=500
COVERAGE_GATE=.99
SPILL_GATE=3.0
ROI_X0=155
SHAPE=(240,150)
BACKING=(720,1380,4)


def original_safety_model(stroke:dict,component:np.ndarray,
                          full_owner:np.ndarray,protected:np.ndarray):
    if (component.shape!=SHAPE or component.dtype!=np.bool_ or
            full_owner.shape!=SHAPE or full_owner.dtype!=np.bool_ or
            protected.shape!=SHAPE or protected.dtype!=np.bool_ or
            np.any(component&~full_owner) or not component.any() or
            not isinstance(stroke,dict) or
            stroke.get("colorIndex")!=OWNER or
            not isinstance(stroke.get("width"),int) or
            not 1<=stroke["width"]<=10 or
            not isinstance(stroke.get("points"),list) or
            not 2<=len(stroke["points"])<=128):
        raise ValueError("BLOCKED_P4B5_ORIGINAL_STROKE_OR_SOURCE")
    arr=np.asarray([[p["x"]-ROI_X0,p["y"]] for p in stroke["points"]],
                   dtype=np.float64)
    if (not np.isfinite(arr).all() or
            np.any(arr[:,0]<0) or np.any(arr[:,0]>=150) or
            np.any(arr[:,1]<0) or np.any(arr[:,1]>=240)):
        raise ValueError("BLOCKED_P4B5_STROKE_COORDINATE_DRIFT")
    xy=np.rint(arr).astype(np.int32)
    model=np.zeros(SHAPE,np.uint8)
    cv2.polylines(model,[xy.reshape(-1,1,2)],False,255,
                  stroke["width"],cv2.LINE_8)
    hits=int(np.count_nonzero(
        (model!=0)&protected&~full_owner))
    return hits


def prune_original_baseline(strokes:list[dict],component:np.ndarray,
                            full_owner:np.ndarray,protected:np.ndarray):
    if (not isinstance(strokes,list) or not 1<len(strokes)<MAX_STROKES or
            any(s.get("colorIndex")!=OWNER for s in strokes)):
        raise ValueError("BLOCKED_P4B5_BASELINE_INPUT")
    survivors=[];removed=[];mapped=[]
    for position,s in enumerate(strokes):
        hits=original_safety_model(s,component,full_owner,protected)
        if hits>0:
            removed.append({
                "original_order":position,
                "original_id":s["strokeId"],
                "width":int(s["width"]),
                "source_model_unsafe_foreign_protected_logical_pixels":hits,
                "original_points":s["points"],
            })
        else:
            new={
                k:s[k] for k in ("strokeId","width","colorIndex",
                                "colorRgb","points")
            }
            new["strokeId"]="icon-%d"%len(survivors)
            mapped.append({
                "original_order":position,"original_id":s["strokeId"],
                "new_id":new["strokeId"],"width":new["width"],
                "original_geometry_retained":True,
            })
            survivors.append(new)
    if not survivors:
        raise ValueError("BLOCKED_P4B5_PRUNED_ALL_BASELINE")
    if sum(len(s["points"]) for s in survivors)>=MAX_VERTICES:
        raise ValueError("BLOCKED_P4B5_NO_RESOURCE_AFTER_PRUNING")
    return survivors,removed,mapped


def native_replay(workspace:Path,method:str,stage:str,strokes:list[dict],
                  output:Path):
    folder=output/("NATIVE_"+stage+"_"+method)
    if folder.exists():
        raise ValueError("BLOCKED_P4B5_OVERWRITE_NATIVE_CAPTURES")
    folder.mkdir()
    actual,metadata,manifest=native_batch(
        workspace,"P4B5-"+stage+"-"+method,strokes,folder,
        renderer_method="renderP4A2BrushWidths1to10Probe")
    if (set(actual)!={"blank","composite","color-115"} or
            set(metadata)!=set(actual) or
            metadata["composite"].get("schema")!=
            "ENGINE001_B1R_P4A2_NATIVE_1_TO_10" or
            metadata["composite"].get("renderer")!=
            "real Egret 5.4.1 BoardPane/WebGLRenderer" or
            manifest["colors_rendered"]!=[OWNER] or
            any(x.shape!=BACKING or x.dtype!=np.uint8 for x in actual.values())):
        raise ValueError("BLOCKED_P4B5_NOT_REAL_PINNED_EGRET")
    return actual


def source_metrics(native:dict,component:np.ndarray,owner:np.ndarray,
                   protected:np.ndarray):
    if set(native)!={"blank","composite","color-115"}:
        raise ValueError("BLOCKED_P4B5_NATIVE_REPLAY_DICT")
    score,blank=p4b4.native_diagnostics(
        native["color-115"],native["blank"],component,owner,protected)
    return score,blank


def run(workspace:Path,source:Path,engine_js:Path,renderer:Path,output:Path):
    if output.exists():
        raise ValueError("BLOCKED_P4B5_OUTPUT_EXISTS")
    check_source(source)
    engine,_=read_engine_palette(engine_js)
    if (p4b4.git_blob(Path(p4b1.__file__).read_bytes())!=P4B1_BLOB or
            p4b4.git_blob(Path(p4b2.__file__).read_bytes())!=P4B2_BLOB or
            p4b4.git_blob(Path(p4b4.__file__).read_bytes())!=P4B4_BLOB or
            p4b4.git_blob(renderer.read_bytes())!=RENDERER_BLOB):
        raise ValueError("BLOCKED_P4B5_SOURCE_PROVENANCE_OR_EGRET_DRIFT")
    output.mkdir(parents=True)
    protected=p4b4.source_critical_rois()
    results={}
    with tempfile.TemporaryDirectory(prefix="engine001-p4b5-p4b2-source-") as tmp:
        parent_dir=Path(tmp)/"same_run_p4b2"
        parent=p4b2.run(workspace,source,engine_js,renderer,parent_dir)
        if (parent["experiment"]!=p4b2.EXPERIMENT or
                parent["result"]!="NATIVE_EDGE_REPAIR_PARTIAL_OR_FAIL" or
                not parent["P4B1_recomputed_current_run_original_only"] or
                not parent["P3D_original_only_all_EF_quality_pass"] or
                parent["legacy_G32_P4c1_V44_as_input"] or
                parent["read_frozen_P4B1_P3D_ZIPs_for_candidate"] or
                set(parent["methods_results"])!=set(METHODS)):
            raise ValueError("BLOCKED_P4B5_PARENT_P4B2_ORIGINAL_ONLY")
        shutil.copyfile(parent_dir/"report.json",
                        output/"SAME_RUN_P4B2_FROZEN_REFERENCE_REPORT.json")
        shutil.copyfile(parent_dir/"SOURCE_ORIGINAL_LOGICAL_RGB.png",
                        output/"SOURCE_ORIGINAL_LOGICAL_RGB.png")
        for method in METHODS:
            index=np.asarray(Image.open(parent_dir/(method+
                                "_SOURCE_ENGINE_INDICES.png")),np.uint8)
            component=np.asarray(Image.open(parent_dir/(method+
                          "_OWNER_COMPONENT.png")).convert("L"),np.uint8)>0
            owner=index==OWNER
            if not component.any() or np.any(component&~owner):
                raise ValueError("BLOCKED_P4B5_OWNER_COMPONENT_DRIFT")
            for ext in ("SOURCE_ENGINE_INDICES","OWNER_COMPONENT","SOURCE_RGB"):
                shutil.copyfile(parent_dir/(method+"_"+ext+".png"),
                                output/(method+"_"+ext+".png"))
            baseline_json=json.loads((parent_dir/(method+
                           "_ORIGINAL_A_STROKES.json")).read_text("utf8"))
            original=[{
                k:s[k] for k in ("strokeId","width","colorIndex",
                                "colorRgb","points")
            } for s in baseline_json]
            pruned,removed,id_mapping=prune_original_baseline(
                original,component,owner,protected)
            if not removed:
                # If original no unsafe model footprints but native is already
                # unsafe, never pretend the prefilter repaired source overlap.
                original_rgba=np.asarray(Image.open(parent_dir/(method+
                    "_BEFORE_NATIVE_COLOR.png")).convert("RGBA"),np.uint8)
                metrics,_=p4b4.native_diagnostics(
                    original_rgba,np.zeros_like(original_rgba),component,
                    owner,protected)
                if metrics["24"]["native_protected_foreign_face_eyes_hands_pixels"]>0:
                    raise ValueError("BLOCKED_MODEL_TO_NATIVE_PROTECTION_MISMATCH")
            (output/(method+"_PRUNED_UNSAFE_STROKES_LEDGER.json")).write_text(
                json.dumps({"removed":removed,"retained_id_map":id_mapping},
                            ensure_ascii=False,indent=2)+"\n",encoding="utf8")
            (output/(method+"_SOURCE_PROTECTED_PRUNED_STROKES.json")).write_text(
                json.dumps(pruned,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
            # Re-render the actual pruned baseline, rather than subtracting
            # model masks from the prior Egret image.
            first=native_replay(workspace,method,"PRUNED_BASELINE",pruned,output)
            pruned_metrics,pruned_blank=source_metrics(
                first,component,owner,protected)
            weights,eligible,missing,missing_diagnostics=p4b2.boundary_missing(
                first["color-115"],component)
            if not eligible.any():
                # An already-covered component is acceptable as pruned-only;
                # preserve it with native capture instead of inventing repairs.
                corrections=[];decision={
                    "status":"NO_NATIVE_MISSING_SOURCE_EDGE",
                    "cumulative_strokes":len(pruned),
                    "cumulative_vertices_NOT_CHALK":sum(len(s["points"]) for s in pruned),
                    "catalog_arm_admissible":0
                }
            else:
                catalog=p4b4.candidate_catalog(
                    component,owner,weights,eligible,protected)
                corrections,decision=p4b4.choose_from_catalog(
                    catalog,weights,pruned,engine,"T3_0")
            combined=pruned+corrections
            if (not combined or len(combined)>MAX_STROKES or
                    sum(len(s["points"]) for s in combined)>MAX_VERTICES):
                raise ValueError("BLOCKED_P4B5_RESOURCE_LIMIT")
            (output/(method+"_FINAL_CORRECTIONS.json")).write_text(
                json.dumps(corrections,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
            (output/(method+"_FINAL_FULL_REPLAY_STROKES.json")).write_text(
                json.dumps(combined,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
            second=native_replay(workspace,method,"PRUNED_AND_REPAIRED",
                                 combined,output)
            final_metrics,final_blank=source_metrics(
                second,component,owner,protected)
            alpha24=final_metrics["24"]
            former=pruned_metrics["24"]
            success=bool(
                alpha24["native_component_coverage"]>=COVERAGE_GATE and
                alpha24["native_component_coverage"]>=former[
                    "native_component_coverage"]-1e-9 and
                alpha24["native_foreign_distance_gt_T3_0"]==0 and
                alpha24["native_protected_foreign_face_eyes_hands_pixels"]==0 and
                alpha24["actual_native_ink_backing_pixels"]>0 and
                pruned_blank==0 and final_blank==0)
            results[method]={
                "source_owner":OWNER,"source_original_rgb_changed":False,
                "original_A_baseline_strokes":len(original),
                "pruned_strokes_count":len(pruned),
                "unsafe_original_A_strokes_removed":len(removed),
                "retained_model_safe_original_strokes_geometry_unchanged":True,
                "original_source_face_eye_hands_foreign_guard":True,
                "pruned_baseline_Egret_native":True,
                "original_pruned_native_alpha":pruned_metrics,
                "new_native_missing_gap_evidence":missing_diagnostics,
                "final_repair_admission":decision,
                "native_final_Egret_real":True,
                "native_final_alpha":final_metrics,
                "pruned_blank_nonzero":pruned_blank,
                "final_blank_nonzero":final_blank,
                "native_actual_quality_pass":success,
                "status":"NATIVE_PROTECTED_COMPONENT_PASS" if success else
                    "NATIVE_PROTECTED_COMPONENT_QUALITY_FAIL",
            }
            print("P4B5_NATIVE",method,results[method]["status"],
                  "removed",len(removed),"pruned_coverage",
                  round(former["native_component_coverage"],6),
                  "pruned_protected",former[
                      "native_protected_foreign_face_eyes_hands_pixels"],
                  "final_coverage",round(alpha24["native_component_coverage"],6),
                  "final_protected",alpha24[
                      "native_protected_foreign_face_eyes_hands_pixels"],
                  "far3",alpha24["native_foreign_distance_gt_T3_0"],
                  "total_strokes",len(combined),flush=True)
    if set(results)!=set(METHODS):
        raise AssertionError("BLOCKED_P4B5_MISSING_TWO_METHODS")
    passed=all(v["native_actual_quality_pass"] for v in results.values())
    (output/"README_REVIEW_RU.txt").write_text(
        "ENGINE001 P4B5 источник — исходный RGB, C192 D_COMPONENT24 "
        "оригинальная карта E/F.\\n"
        "Каждый original A штрих сначала проверен на модельное пересечение "
        "с оригинальными чужими защищёнными пикселями лица, глаз и рук.\\n"
        "NATIVE_PRUNED_BASELINE_E/F и NATIVE_PRUNED_AND_REPAIRED_E/F — "
        "настоящие Egret/BoardPane WebGL PNG до и после нового лечения.\\n"
        "Реальная native alpha24 coverage99%, чужие защищённые0 и "
        "не далее3 logicalpx — отдельные неослабленные критерии.\\n"
        "250 штрихов,500 вершин максимальные лимиты; source index RGB "
        "не изменены.\\n"
        "E3 не доказывает E4 game или точный CHALK.\\n",encoding="utf8")
    hashes={
        str(p.relative_to(output)).replace("\\","/"):digest(p.read_bytes())
        for p in sorted(output.rglob("*")) if p.is_file()
    }
    report={
        "experiment":EXPERIMENT,
        "prereg":"ENGINE001_B1R_P4B5_PROTECTED_BASELINE_REBALANCE_V1",
        "status":"NATIVE_PROTECTED_BOTH_PASS" if passed else
                 "NATIVE_PROTECTED_QUALITY_NOT_ALL_PASS",
        "native_E3_scenes_complete":4,
        "source_SHA256":SOURCE_SHA,
        "engine_blob_sha1":ENGINE_GIT_BLOB_SHA1,
        "renderer_blob_sha1":RENDERER_BLOB,
        "source_original_only_all_EF_P3D_quality_pass":True,
        "P4B1_BLOB":P4B1_BLOB,"P4B2_BLOB":P4B2_BLOB,"P4B4_BLOB":P4B4_BLOB,
        "source_key":SOURCE,
        "source_color_owner_index":OWNER,
        "methods":results,
        "new_brush_widths_available_1to10":list(range(1,11)),
        "native_coverage_gate_unchanged":COVERAGE_GATE,
        "legacy_3logical_spill_gate_unchanged":SPILL_GATE,
        "max_strokes":MAX_STROKES,
        "max_synthetic_vertices_NOT_CHALK":MAX_VERTICES,
        "legacy_G32_P4c1_V44_used_as_candidate":False,
        "frozen_old_ZIPs_as_source":False,
        "E4_actual_game":"NOT_RUN","E5_independent":"NOT_RUN",
        "exact_run_bound_CHALK":None,"production_promotion":False,
        "github_sha":os.getenv("GITHUB_SHA"),
        "github_run_id":os.getenv("GITHUB_RUN_ID"),
        "file_sha256":hashes
    }
    (output/"report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf8")
    return report


if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--workspace",type=Path,required=True)
    a.add_argument("--source",type=Path,required=True)
    a.add_argument("--engine-js",type=Path,required=True)
    a.add_argument("--renderer",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    args=a.parse_args()
    try:
        r=run(args.workspace,args.source,args.engine_js,args.renderer,args.output)
    except Exception as e:
        args.output.mkdir(parents=True,exist_ok=True)
        (args.output/"FAILED_EVIDENCE.json").write_text(
            json.dumps({
                "experiment":EXPERIMENT,"status":"BLOCKED",
                "error_type":type(e).__name__,"reason":str(e),
                "github_sha":os.getenv("GITHUB_SHA"),
                "github_run_id":os.getenv("GITHUB_RUN_ID"),
                "quality_not_proven":True,"exact_CHALK":None,
            },ensure_ascii=False,indent=2)+"\n",encoding="utf8")
        raise
    print("P4B5_RESULT",r["status"],"4 archived Egret E3 scenes, E4/CHALK NOT_RUN")

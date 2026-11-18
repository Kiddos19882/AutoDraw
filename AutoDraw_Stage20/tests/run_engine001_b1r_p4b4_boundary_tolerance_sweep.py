#!/usr/bin/env python3
"""B1-R P4B4: independent native boundary spill admission sweep, not production.

Three fixed arms 3 / 3.5 / 4 logical pixels share SAME candidate catalog.
Actual native E3 coverage controls every conclusion, not OpenCV model strokes.
P4B1/P4B2 parents are recomputed exclusively from original P3D in same run.
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import os
import shutil
import tempfile
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
import run_engine001_b1r_p4b2_native_edge_repair as p4b2
from run_engine001_b1r_p3b_engine128_adaptive32 import (
    ENGINE_GIT_BLOB_SHA1, SOURCE_SHA, read_engine_palette, roi_logical,
)
from run_engine001_b1r_p1_fullrgb_edge_aware import check_source
from run_engine001_b1r_p2_joint_region_outline import digest
from run_engine001_complex_holdout_v5 import native_batch

EXPERIMENT = "ENGINE001_B1R_P4B4_BOUNDARY_TOLERANCE_SWEEP_V1"
P4B1_BLOB = "b95aa361cf2ec94d5fa28e7309bd3e4af15eca93"
P4B2_BLOB = "0053829480c6327ef5c541024593f6e0018aa35e"
RENDERER_BLOB = "76d950e0a8911888a9df3b675b866519ecf7bba4"
SOURCE = "C_192_D_COMPONENT24"
METHODS = ("E_SOBEL90", "F_SOBEL90_LAB12")
ARMS = {"T3_0": 3.0, "T3_5": 3.5, "T4_0": 4.0}
CANDIDATE_WIDTHS = tuple(range(10, 0, -1))
CORRECTION_MODES = ("H", "V")
LOGICAL = (240, 150)
BACKING = (720, 1380, 4)
ROI_X0 = 155
OWNER = 115
NATIVE_ALPHA = 24
COVERAGE_GATE = .99
LEGACY_GATE = 3.0
MAX_STROKES = 250
MAX_VERTICES = 500
EDGE_DISTANCE = 2.0


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def source_critical_rois() -> np.ndarray:
    protected = np.zeros(LOGICAL, np.bool_)
    for name in ("female_face_eyes", "male_face_eyes", "hands"):
        x0, y0, x1, y1 = roi_logical(name)
        protected[y0:y1, x0:x1] = True
    if not protected.any():
        raise AssertionError("BLOCKED_P4B4_ORIGINAL_FEATURE_ROI_MISSING")
    return protected


def original_component_inputs(component, full_owner, weights, eligible,
                              protected):
    if (component.shape != LOGICAL or component.dtype != np.bool_ or
            full_owner.shape != LOGICAL or full_owner.dtype != np.bool_ or
            weights.shape != LOGICAL or
            not np.issubdtype(weights.dtype, np.integer) or
            eligible.shape != LOGICAL or eligible.dtype != np.bool_ or
            protected.shape != LOGICAL or protected.dtype != np.bool_ or
            np.any(weights < 0) or np.any(component & ~full_owner) or
            np.any(eligible & ~component) or not np.any(component)):
        raise ValueError("BLOCKED_P4B4_INVALID_SOURCE_OWNER_OR_NATIVE_GAPS")


def _candidate(points, width, component, full_owner, outside, protected,
               direction):
    if width not in CANDIDATE_WIDTHS or len(points) != 2:
        raise ValueError("BLOCKED_P4B4_CANDIDATE_WIDTH_OR_VERTICES")
    if not p4b1._source_centerline(points, component):
        return None
    xy = np.rint(np.asarray(points, dtype=np.float64)).astype(np.int32)
    x0=max(0,int(xy[:,0].min())-width-2)
    x1=min(150,int(xy[:,0].max())+width+3)
    y0=max(0,int(xy[:,1].min())-width-2)
    y1=min(240,int(xy[:,1].max())+width+3)
    mask=np.zeros((y1-y0,x1-x0),np.uint8)
    local=xy.copy();local[:,0]-=x0;local[:,1]-=y0
    cv2.polylines(mask,[local.reshape(-1,1,2)],False,255,
                  thickness=width,lineType=cv2.LINE_8)
    ys,xs=np.where(mask!=0)
    if not len(xs):
        return None
    yy,xx=ys+y0,xs+x0
    foreign=(~full_owner[yy,xx])
    if np.any(foreign & protected[yy,xx]):
        return None
    max_dist=float(np.max(outside[yy[foreign],xx[foreign]])) if foreign.any() else 0.0
    # Superset fixed before any arm: NEVER admit projected foreign >4.
    if max_dist>max(ARMS.values())+1e-9:
        return None
    flat=np.unique((yy[component[yy,xx]]*150+xx[component[yy,xx]]).astype(np.int32))
    if len(flat)==0:
        return None
    return {
        "source_xy":points,"width":width,"direction":direction,
        "owner_flat":flat,"projected_max_nonowner_distance_MODEL_ONLY":max_dist,
        "projected_foreign_model_pixels":int(foreign.sum()),
        "vertices":2,
    }


def candidate_catalog(component,full_owner,weights,eligible,protected):
    original_component_inputs(component,full_owner,weights,eligible,protected)
    outside=cv2.distanceTransform((~full_owner).astype(np.uint8),
                                  cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
    # Exact same source pixels + placements for ALL arms.
    options=[]
    for y,x in np.argwhere(eligible):
        x=int(x);y=int(y)
        for width in CANDIDATE_WIDTHS:
            for direction in CORRECTION_MODES:
                if direction=="H":
                    points=[(x+.125,float(y)),(x+.375,float(y))]
                else:
                    points=[(float(x),y+.125),(float(x),y+.375)]
                c=_candidate(points,width,component,full_owner,outside,
                             protected,direction)
                if c is not None:
                    options.append(c)
    return options


def choose_from_catalog(catalog: list[dict], measured_weights: np.ndarray,
                        baseline_strokes: list[dict], game128: np.ndarray,
                        arm: str):
    if (arm not in ARMS or measured_weights.shape != LOGICAL or
            not np.issubdtype(measured_weights.dtype,np.integer) or
            np.any(measured_weights<0) or game128.shape!=(128,3) or
            game128.dtype!=np.uint8 or not isinstance(baseline_strokes,list) or
            not 1<=len(baseline_strokes)<MAX_STROKES or
            any(s["colorIndex"]!=OWNER for s in baseline_strokes)):
        raise ValueError("BLOCKED_P4B4_SELECTION_INPUT")
    prev_vertices=sum(len(s["points"]) for s in baseline_strokes)
    if prev_vertices>=MAX_VERTICES:
        raise ValueError("BLOCKED_P4B4_BASELINE_RESOURCE_CAP")
    cap=min(MAX_STROKES-len(baseline_strokes),
            (MAX_VERTICES-prev_vertices)//2)
    max_distance=ARMS[arm]
    options=[
        c for c in catalog
        if c["projected_max_nonowner_distance_MODEL_ONLY"]<=max_distance+1e-9
    ]
    left=measured_weights.astype(np.int32).reshape(-1).copy()
    heap=[]
    for i,c in enumerate(options):
        gain=int(left[c["owner_flat"]].sum())
        if gain>0:
            # Fixed gain weighting / vertex count; prefer wider on ties.
            heapq.heappush(heap,(-gain/c["vertices"],-gain,
                                 -c["width"],i,gain))
    chosen=[]
    hist=Counter()
    while heap and len(chosen)<cap:
        _,_,_,i,previous=heapq.heappop(heap)
        c=options[i]
        gain=int(left[c["owner_flat"]].sum())
        if gain!=previous:
            if gain:
                heapq.heappush(heap,(-gain/c["vertices"],-gain,
                                     -c["width"],i,gain))
            continue
        if gain<=0:
            continue
        rgb=game128[OWNER]
        points=[{"x":float(x)+ROI_X0,"y":float(y)}
                for x,y in c["source_xy"]]
        chosen.append({
            "strokeId":"icon-%d"%(len(baseline_strokes)+len(chosen)),
            "width":int(c["width"]),
            "colorIndex":OWNER,
            "colorRgb":(int(rgb[0])<<16)|(int(rgb[1])<<8)|int(rgb[2]),
            "points":points,
        })
        hist[str(c["width"])]+=1
        left[c["owner_flat"]]=0
    return chosen,{
        "arm":arm,"model_spill_admission_logical":max_distance,
        "catalog_total_before_arm_filter":len(catalog),
        "catalog_arm_admissible":len(options),
        "chosen_strokes":len(chosen),
        "cumulative_strokes":len(chosen)+len(baseline_strokes),
        "cumulative_vertices_NOT_CHALK":prev_vertices+len(chosen)*2,
        "model_residual_native_gap_weight_NOT_EGRET":int(left.sum()),
        "models_are_ranking_only":True,
        "width_histogram":{str(w):hist[str(w)] for w in CANDIDATE_WIDTHS},
    }


def backing(mask: np.ndarray):
    return p4b1._board_backing(mask)


def native_diagnostics(rgba: np.ndarray, blank: np.ndarray, component: np.ndarray,
                       full_owner: np.ndarray, protected: np.ndarray):
    if (rgba.shape!=BACKING or rgba.dtype!=np.uint8 or
            blank.shape!=BACKING or blank.dtype!=np.uint8 or
            component.shape!=LOGICAL or component.dtype!=np.bool_ or
            full_owner.shape!=LOGICAL or full_owner.dtype!=np.bool_ or
            protected.shape!=LOGICAL or protected.dtype!=np.bool_):
        raise ValueError("BLOCKED_P4B4_NATIVE_GROUND_TRUTH_SHAPE")
    target=backing(component)
    owner=backing(full_owner)
    sensitive_foreign=backing(protected & ~full_owner)
    # True Egret backing 3x Euclidean distance. All three exact pre-registered thresholds.
    outside=cv2.distanceTransform((~owner).astype(np.uint8),
                                  cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
    metrics={}
    for alpha in (24,128):
        ink=(rgba[:,:,3]>=alpha)
        own=ink & target
        missing=int(np.count_nonzero(target & ~ink))
        measured={
            "native_component_coverage":float(own.sum()/target.sum()),
            "native_component_missing_backing_pixels":missing,
            "native_any_foreign_color_backing_pixels":int(np.count_nonzero(ink & ~owner)),
            "native_protected_foreign_face_eyes_hands_pixels":
                int(np.count_nonzero(ink & sensitive_foreign)),
            "actual_native_ink_backing_pixels":int(ink.sum()),
        }
        for arm,tol in ARMS.items():
            measured["native_foreign_distance_gt_"+arm] = int(np.count_nonzero(
                ink & ~owner & (outside>tol*3)))
        metrics[str(alpha)]=measured
    blank_nonzero=int(np.count_nonzero(blank[:,:,3]))
    return metrics,blank_nonzero


def run(workspace:Path,source:Path,engine_js:Path,renderer:Path,output:Path):
    if output.exists():
        raise ValueError("BLOCKED_P4B4_OUTPUT_ALREADY_EXISTS")
    check_source(source)
    game128,_=read_engine_palette(engine_js)
    if (git_blob(Path(p4b1.__file__).read_bytes())!=P4B1_BLOB or
            git_blob(Path(p4b2.__file__).read_bytes())!=P4B2_BLOB or
            git_blob(renderer.read_bytes())!=RENDERER_BLOB):
        raise ValueError("BLOCKED_P4B4_PINNED_PARENT_OR_NATIVE_EGRET_DRIFT")
    output.mkdir(parents=True)
    results={}
    sensitive=source_critical_rois()
    with tempfile.TemporaryDirectory(prefix="engine001-p4b4-original-source-") as tmp:
        parent_dir=Path(tmp)/"same_run_P4B2"
        parent=p4b2.run(workspace,source,engine_js,renderer,parent_dir)
        if (parent["experiment"]!=p4b2.EXPERIMENT or
                parent["result"]!="NATIVE_EDGE_REPAIR_PARTIAL_OR_FAIL" or
                not parent["P4B1_recomputed_current_run_original_only"] or
                not parent["P3D_original_only_all_EF_quality_pass"] or
                parent["legacy_G32_P4c1_V44_as_input"] or
                parent["read_frozen_P4B1_P3D_ZIPs_for_candidate"] or
                set(parent["methods_results"])!=set(METHODS)):
            raise ValueError("BLOCKED_P4B4_PARENT_PROVENANCE_OR_FROZEN_FAIL")
        shutil.copyfile(parent_dir/"report.json",output/"SAME_RUN_P4B2_PARENT_REPORT.json")
        shutil.copyfile(parent_dir/"SOURCE_ORIGINAL_LOGICAL_RGB.png",
                        output/"SOURCE_ORIGINAL_LOGICAL_RGB.png")
        for method in METHODS:
            mask=np.asarray(Image.open(parent_dir/(
                method+"_OWNER_COMPONENT.png")).convert("L"),np.uint8)>0
            index=np.asarray(Image.open(parent_dir/(
                method+"_SOURCE_ENGINE_INDICES.png")),np.uint8).copy()
            full_owner=index==OWNER
            src_rgb=np.asarray(Image.open(parent_dir/(
                method+"_SOURCE_RGB.png")).convert("RGB"),np.uint8)
            if not mask.any() or np.any(mask&~full_owner):
                raise ValueError("BLOCKED_P4B4_SOURCE_OWNER_CHANGED")
            for ext in ("OWNER_COMPONENT","SOURCE_ENGINE_INDICES","SOURCE_RGB"):
                shutil.copyfile(parent_dir/(method+"_"+ext+".png"),
                                output/(method+"_"+ext+".png"))
            before=np.asarray(Image.open(parent_dir/(
                method+"_BEFORE_NATIVE_COLOR.png")).convert("RGBA"),np.uint8)
            p4b2_control=np.asarray(Image.open(parent_dir/(
                "NATIVE_P4B2_"+method)/("P4B2-"+method+"-color-115.png")
            ).convert("RGBA"),np.uint8)
            previous_coverage=parent["methods_results"][method][
                "corrected_native_after"]["24"]["native_component_coverage"]
            scores=parent["methods_results"][method]["original_A_native_before"]
            if (abs(previous_coverage-(
                    p4b1.native_metrics(p4b2_control,np.zeros_like(p4b2_control),
                                        mask,full_owner)[0]["24"]["native_component_coverage"]))>1e-12
                    or scores["24"]["native_component_coverage"]>=COVERAGE_GATE):
                raise ValueError("BLOCKED_P4B4_PINNED_NATIVE_BASELINE_DRIFT")
            for key,arr in [("P4B1_BEFORE_NATIVE_COLOR",before),
                            ("P4B2_AFTER_NATIVE_COLOR",p4b2_control)]:
                Image.fromarray(arr).save(output/(method+"_"+key+".png"))
            weights,eligible,_,before_gap=p4b2.boundary_missing(before,mask)
            if not eligible.any():
                raise ValueError("BLOCKED_P4B4_NO_ORIGINAL_EDGE_MISSES")
            baseline_raw=json.loads((parent_dir/(
                method+"_ORIGINAL_A_STROKES.json")).read_text(encoding="utf8"))
            baseline=[{k:s[k] for k in ("strokeId","width","colorIndex",
                                        "colorRgb","points")} for s in baseline_raw]
            catalog=candidate_catalog(mask,full_owner,weights,eligible,sensitive)
            if not catalog:
                raise ValueError("BLOCKED_P4B4_NO_ACCEPTABLE_SOURCE_CANDIDATES")
            record={
                "source_owner_engine_index":OWNER,
                "true_native_P4B1_before_coverage":scores["24"]["native_component_coverage"],
                "true_native_P4B2_control_coverage":previous_coverage,
                "sensitive_original_foreign_source_pixels":int((sensitive&~full_owner).sum()),
                "source_native_gap_summary":before_gap,
                "original_A_base_strokes":len(baseline),
                "candidate_source_count":len(catalog),
                "arms":{},
            }
            for arm,tolerance in ARMS.items():
                corrections,model=choose_from_catalog(
                    catalog,weights,baseline,game128,arm)
                full=baseline+corrections
                if (not corrections or
                        len(full)>MAX_STROKES or
                        sum(len(s["points"]) for s in full)>MAX_VERTICES or
                        any(not 1<=s["width"]<=10 for s in full)):
                    raise ValueError("BLOCKED_P4B4_COLOR_OR_RESOURCE_LIMIT")
                (output/(method+"_"+arm+"_CORRECTIONS.json")).write_text(
                    json.dumps(corrections,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
                (output/(method+"_"+arm+"_FULL_STROKES.json")).write_text(
                    json.dumps(full,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
                d=output/("NATIVE_"+method+"_"+arm)
                d.mkdir()
                real,metadata,manifest=native_batch(
                    workspace,"P4B4-"+method+"-"+arm,full,d,
                    renderer_method="renderP4A2BrushWidths1to10Probe")
                if (set(real)!={"blank","composite","color-115"} or
                        set(metadata)!=set(real) or
                        metadata["composite"].get("schema")!=
                        "ENGINE001_B1R_P4A2_NATIVE_1_TO_10" or
                        metadata["composite"].get("renderer")!=
                        "real Egret 5.4.1 BoardPane/WebGLRenderer" or
                        manifest["colors_rendered"]!=[OWNER] or
                        any(arr.shape!=BACKING or arr.dtype!=np.uint8
                            for arr in real.values())):
                    raise ValueError("BLOCKED_P4B4_TRUE_EGRET_NATIVE_CAPTURE")
                real_scores,blank_count=native_diagnostics(
                    real["color-115"],real["blank"],mask,full_owner,sensitive)
                a24=real_scores["24"]
                spill_own=a24["native_foreign_distance_gt_"+arm]
                quality=bool(
                    a24["native_component_coverage"]>=COVERAGE_GATE and
                    a24["native_component_coverage"]>=previous_coverage-1e-9 and
                    spill_own==0 and
                    a24["native_protected_foreign_face_eyes_hands_pixels"]==0 and
                    a24["actual_native_ink_backing_pixels"]>0 and
                    blank_count==0)
                record["arms"][arm]={
                    "model_admission":model,
                    "actual_Egret_native_RGBA":True,
                    "native_blank_nonzero_alpha_pixels":blank_count,
                    "native_alpha":real_scores,
                    "passes_original_legacy_3px_gate": bool(
                        a24["native_foreign_distance_gt_T3_0"]==0),
                    "quality_status": (
                        "NATIVE_EXPLORATORY_TOLERANCE_PASS_NOT_PRODUCTION"
                        if quality else "NATIVE_TOLERANCE_QUALITY_FAIL"),
                    "true_native_component_quality_pass":quality,
                    "source_original_RGB_changed":False,
                    "original_P4B1_A_strokes_unchanged":True,
                    "original_source_protected_ROIs_preserved":True,
                }
                print("P4B4_NATIVE",method,arm,
                      record["arms"][arm]["quality_status"],
                      "coverage",round(a24["native_component_coverage"],7),
                      "outside>3",a24["native_foreign_distance_gt_T3_0"],
                      "outside>3.5",a24["native_foreign_distance_gt_T3_5"],
                      "outside>4",a24["native_foreign_distance_gt_T4_0"],
                      "protected_foreign",
                      a24["native_protected_foreign_face_eyes_hands_pixels"],
                      "strokes",model["cumulative_strokes"],
                      "admitted",model["catalog_arm_admissible"],flush=True)
            results[method]=record
    n=sum(len(v["arms"]) for v in results.values())
    if n!=6:
        raise AssertionError("BLOCKED_P4B4_SIX_NATIVE_ARM_CAPTURES_MISSING")
    good=sum(int(entry["true_native_component_quality_pass"])
             for result in results.values() for entry in result["arms"].values())
    hashes={
        str(p.relative_to(output)).replace("\\","/"):digest(p.read_bytes())
        for p in sorted(output.rglob("*")) if p.is_file()
    }
    (output/"README_REVIEW_RU.txt").write_text(
        "P4B4 — исходные E/F и настоящий Egret/WebGL. Три заранее заданных "
        "лимита выхода 3, 3.5, 4 логических px.\n"
        "NATIVE_* — реальные кадры, *_FULL_STROKES.json — планы с общим "
        "ограничением 250 штрихов/500 точек.\n"
        "Отдельно измеряются покрытие выбранной зоны99%, выход за 3/3.5/4 "
        "и попадание в защищённые чужие цвета лица/глаз/рук.\n"
        "Старые P4B1/P4B2/P4B3 не переписаны и сохраняют FAIL.\n"
        "Нативный Egret E3 не равен live game E4 и не измеряет CHALK.\n",
        encoding="utf8")
    hashes["README_REVIEW_RU.txt"]=digest(
        (output/"README_REVIEW_RU.txt").read_bytes())
    report={
        "experiment":EXPERIMENT,
        "prereg":"ENGINE001_B1R_P4B4_BOUNDARY_TOLERANCE_SWEEP_V1",
        "status":"SOME_EXPLORATORY_NATIVE_PASS" if good else
                 "ALL_NEW_NATIVE_QUALITY_FAIL",
        "native_arm_scenes_completed":n,"quality_pass_arms":good,
        "arm_tolerance_logical":ARMS,"widths_available":list(CANDIDATE_WIDTHS),
        "original_coverage_gate_unchanged":COVERAGE_GATE,
        "original_3px_quality_gate_unchanged":LEGACY_GATE,
        "source_SHA256":SOURCE_SHA,
        "engine_blob_sha1":ENGINE_GIT_BLOB_SHA1,
        "renderer_blob_sha1":RENDERER_BLOB,
        "P4B1_blob_sha1":P4B1_BLOB,"P4B2_blob_sha1":P4B2_BLOB,
        "source_key":SOURCE,"owner_engine_index":OWNER,
        "P4B2_and_P4B1_recomputed_original_only":True,
        "old_G32_P4c1_V44_used_as_input":False,
        "frozen_parent_archive_used_as_input":False,
        "P3D_source_EF_frozen_gates_unchanged":True,
        "real_game_E4":"NOT_RUN","independent_E5":"NOT_RUN",
        "exact_run_bound_CHALK":None,"production_promotion":False,
        "methods":results,
        "github_sha":os.getenv("GITHUB_SHA"),
        "github_run_id":os.getenv("GITHUB_RUN_ID"),
        "file_sha256":hashes,
    }
    (output/"report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n",
        encoding="utf8")
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--workspace",required=True,type=Path)
    p.add_argument("--source",required=True,type=Path)
    p.add_argument("--engine-js",required=True,type=Path)
    p.add_argument("--renderer",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    try:
        result=run(a.workspace,a.source,a.engine_js,a.renderer,a.output)
    except Exception as error:
        a.output.mkdir(parents=True,exist_ok=True)
        (a.output/"FAILED_EVIDENCE.json").write_text(
            json.dumps({
                "experiment":EXPERIMENT,
                "status":"BLOCKED",
                "error_type":type(error).__name__,"reason":str(error),
                "github_sha":os.getenv("GITHUB_SHA"),
                "github_run_id":os.getenv("GITHUB_RUN_ID"),
                "source_quality_or_game_CHALK_pass":False,
            },ensure_ascii=False,indent=2)+"\n",encoding="utf8")
        raise
    print("P4B4_RESULT",result["status"],
          "native",result["native_arm_scenes_completed"],
          "quality_pass",result["quality_pass_arms"],
          "exact_CHALK_NOT_RUN",flush=True)

#!/usr/bin/env python3
"""P4B10 original-source true Egret native width-only sweep, not production."""
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
import run_engine001_b1r_p4b8_causal_stroke_surgery as p4b8
import run_engine001_b1r_p4b9_native_far3_attribution as p4b9
import run_engine001_b1r_p4b5_protected_baseline_rebalance as p4b5
import run_engine001_b1r_p4b4_boundary_tolerance_sweep as p4b4
from run_engine001_b1r_p1_fullrgb_edge_aware import check_source
from run_engine001_b1r_p2_joint_region_outline import digest

EXPERIMENT="ENGINE001_B1R_P4B10_NATIVE_CORRECTION_WIDTH_SWEEP_V1"
PREREG="ENGINE001_B1R_P4B10_NATIVE_CORRECTION_WIDTH_SWEEP_PREREG_2026-11-18.md"
P4B6_BLOB="2f9ca1756da58e7062fcae6c6c64c83e4db79ea9"
P4B7_BLOB="87ea292c01c75e594c4ff09acf716c4500e88644"
P4B8_BLOB="9ddf8e2f745de4f78006b14c00e99e74c2f3cb67"
P4B9_BLOB="c4b1d06011a6acbd90bb4e18d8bd6a72a3cce4ef"
RENDERER_BLOB="76d950e0a8911888a9df3b675b866519ecf7bba4"
SOURCE_SHA="07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
METHODS=("E_SOBEL90","F_SOBEL90_LAB12")
E_METHOD,F_METHOD=METHODS
OWNER=115
WIDTH_IDS={E_METHOD:(110,202),F_METHOD:(109,)}
ORIGINAL_WIDTHS={E_METHOD:(10,6),F_METHOD:(10,)}
SOURCE_KEY="C_192_D_COMPONENT24"
MAX_STROKES=250
MAX_VERTICES=500
ALPHA=24
COVERAGE_GATE=.99
PROTECTED_GATE=0
SPILL_GATE=3.
EXPECTED_FAR={E_METHOD:4,F_METHOD:2}
EXPECTED_COUNTS={E_METHOD:214,F_METHOD:212}


def width_arms(method):
    """Frozen E 10x6 Cartesian grid; F 1..10. Stable order / no omissions."""
    if method==E_METHOD:
        return tuple((f"W{w1:02d}_W{w2:02d}",(w1,w2))
                     for w1 in range(1,11) for w2 in range(1,7))
    if method==F_METHOD:
        return tuple((f"W{w:02d}",(w,)) for w in range(1,11))
    raise ValueError("BLOCKED_P4B10_UNKNOWN_SOURCE_METHOD")


def width_only_variant(original,method,widths,component,repair_start):
    if (method not in METHODS or not isinstance(original,list) or
            len(original)!=EXPECTED_COUNTS[method] or
            component.shape!=p4b5.SHAPE or component.dtype!=np.bool_ or
            type(repair_start) is not int or repair_start<=0 or
            not isinstance(widths,tuple) or len(widths)!=len(WIDTH_IDS[method]) or
            any(type(w) is not int for w in widths)):
        raise ValueError("BLOCKED_P4B10_PINNED_VARIANT_INPUT")
    ids=WIDTH_IDS[method]
    if (any(i<repair_start or i>=len(original) for i in ids) or
            any(original[i].get("strokeId")!="icon-%d"%i or
                original[i].get("colorIndex")!=OWNER or
                original[i].get("width")!=ORIGINAL_WIDTHS[method][j] or
                not p4b8.supported(original[i],component)
                for j,i in enumerate(ids))):
        raise ValueError("BLOCKED_P4B10_CAUSAL_CORRECTION_PROVENANCE")
    if any(w<1 or w>ORIGINAL_WIDTHS[method][j] for j,w in enumerate(widths)):
        raise ValueError("BLOCKED_P4B10_UNREGISTERED_WIDTH")
    if (any(s.get("strokeId")!="icon-%d"%i or
            s.get("colorIndex")!=OWNER or
            type(s.get("width")) is not int or not 1<=s["width"]<=10 or
            not isinstance(s.get("points"),list) or
            not 2<=len(s["points"])<=128
            for i,s in enumerate(original)) or
            len(original)>MAX_STROKES or
            sum(len(s["points"]) for s in original)>MAX_VERTICES):
        raise ValueError("BLOCKED_P4B10_ORIGINAL_RESOURCE_OR_ID_DRIFT")
    candidate=deepcopy(original)
    for i,w in zip(ids,widths):
        candidate[i]["width"]=w
        if not p4b8.supported(candidate[i],component):
            raise ValueError("BLOCKED_P4B10_CHANGED_STROKE_OFF_SOURCE")
    if (len(candidate)>MAX_STROKES or
            sum(len(s["points"]) for s in candidate)>MAX_VERTICES):
        raise ValueError("BLOCKED_P4B10_BUDGET")
    # Source geometry, color, ordering and all nonculprits strictly immutable.
    for i,(a,b) in enumerate(zip(original,candidate)):
        if {k:v for k,v in a.items() if k!="width"}!={
                k:v for k,v in b.items() if k!="width"}:
            raise ValueError("BLOCKED_P4B10_NONWIDTH_MUTATION")
        if i not in ids and a["width"]!=b["width"]:
            raise ValueError("BLOCKED_P4B10_NONCULPRIT_WIDTH_CHANGED")
    modified=sum(1 for j,i in enumerate(ids)
                 if original[i]["width"]!=widths[j])
    ledger={
        "method":method,"original_full_stroke_ids":[s["strokeId"] for s in original],
        "changed_candidate_ids":[original[i]["strokeId"] for j,i in enumerate(ids)
                                 if original[i]["width"]!=widths[j]],
        "culprit_positions_in_original_final":list(ids),
        "original_widths":list(ORIGINAL_WIDTHS[method]),
        "tested_widths":list(widths),
        "changed_width_count":modified,
        "all_original_points_and_colors_immutable":True,
        "all_nonculprits_immutable":True,
        "source_supported_true":True,
        "new_strokes_created":False,
        "strokes_NOT_CHALK":len(candidate),
        "synthetic_vertices_NOT_CHALK":sum(len(s["points"]) for s in candidate),
    }
    return candidate,ledger


def choose_best_safe(results):
    """Deterministic predeclared Pareto diagnostic, never production approval."""
    if not isinstance(results,dict):
        raise ValueError("BLOCKED_P4B10_RANK_INPUT")
    eligible=[]
    for name,item in results.items():
        measured=item.get("native_alpha",{}).get("24",{})
        protect=measured.get("native_protected_foreign_face_eyes_hands_pixels")
        far=measured.get("native_foreign_distance_gt_T3_0")
        if protect==0 and far==0 and item.get("native_blank_zero")==0:
            c=measured.get("native_component_coverage")
            ledger=item.get("source_width_ledger",{})
            if (type(c) is not float or not np.isfinite(c) or not 0<=c<=1
                    or type(ledger.get("changed_width_count")) is not int
                    or not isinstance(ledger.get("tested_widths"),list)
                    or not ledger["tested_widths"]):
                raise ValueError("BLOCKED_P4B10_BAD_NATIVE_SAFE_RANK")
            eligible.append((name,c,ledger["changed_width_count"],
                             sum(ledger["tested_widths"])))
    if not eligible:
        return {"status":"NO_NATIVE_SAFE_WIDTH_COMBO","arm":None}
    eligible.sort(key=lambda a:(-a[1],a[2],-a[3],a[0]))
    name,coverage,changes,total_width=eligible[0]
    return {
        "status":"BEST_NATIVE_SOURCE_SAFE_DIAGNOSTIC_ONLY",
        "arm":name,"owner_coverage":coverage,"changed_culprit_widths":changes,
        "combined_culprit_width":total_width,
        "overall_artwork_quality_pass":coverage>=COVERAGE_GATE,
    }


def run(workspace:Path,source:Path,engine_js:Path,renderer:Path,output:Path):
    if output.exists():raise ValueError("BLOCKED_P4B10_OUTPUT_EXISTS")
    check_source(source)
    for mod,want in ((p4b6,P4B6_BLOB),(p4b7,P4B7_BLOB),
                     (p4b8,P4B8_BLOB),(p4b9,P4B9_BLOB)):
        if p4b4.git_blob(Path(mod.__file__).read_bytes())!=want:
            raise ValueError("BLOCKED_P4B10_FROZEN_PARENT_BLOB")
    if p4b4.git_blob(renderer.read_bytes())!=RENDERER_BLOB:
        raise ValueError("BLOCKED_P4B10_EGRET_RENDERER_BLOB")
    if EXPERIMENT not in (workspace/"AutoDraw_Stage20"/"docs"/PREREG).read_text("utf8"):
        raise ValueError("BLOCKED_P4B10_PREREG")
    if (len(width_arms(E_METHOD))!=60 or len(width_arms(F_METHOD))!=10 or
            len(set(name for name,_ in width_arms(E_METHOD)))!=60 or
            len(set(name for name,_ in width_arms(F_METHOD)))!=10):
        raise ValueError("BLOCKED_P4B10_WIDTH_MATRIX")
    output.mkdir(parents=True)
    findings={}
    with tempfile.TemporaryDirectory(prefix="engine001-p4b10-original-") as tmp:
        original_dir=Path(tmp)/"SAME_RUN_P4B6"
        parent=p4b6.run(workspace,source,engine_js,renderer,original_dir)
        if (parent["experiment"]!=p4b6.EXPERIMENT or
                parent["result"]!="NATIVE_GUARDS_QUALITY_NOT_ALL_PASS" or
                parent["original_source_SHA256"]!=SOURCE_SHA or
                parent["legacy_G32_P4c1_V44_used"] or
                parent["frozen_P4B5_ZIP_used_as_candidate"] or
                set(parent["methods"])!=set(METHODS)):
            raise ValueError("BLOCKED_P4B10_ORIGINAL_SOURCE_PROVENANCE")
        protected=p4b4.source_critical_rois()
        for method in METHODS:
            arm="G1_0"
            parentdata=parent["methods"][method]["arms"][arm]
            raw=json.loads((original_dir/(method+"_G1_0_FINAL_STROKES.json")).read_text("utf8"))
            component=np.asarray(Image.open(
                original_dir/(method+"_OWNER_COMPONENT.png")).convert("L"),np.uint8)>0
            index=np.asarray(Image.open(
                original_dir/(method+"_SOURCE_ENGINE_INDICES.png")),np.uint8)
            owner=index==OWNER
            if (len(raw)!=EXPECTED_COUNTS[method] or
                    index.shape!=p4b5.SHAPE or component.shape!=p4b5.SHAPE or
                    not component.any() or (component&~owner).any() or
                    parentdata["native_quality_pass"] or
                    parentdata["native_final_alpha"]["24"][
                        "native_protected_foreign_face_eyes_hands_pixels"]!=2):
                raise ValueError("BLOCKED_P4B10_PINNED_OWNER_OR_G1_RESULT")
            trim,trim_ledger=p4b8.surgery(
                raw,method,"TRIM50",component,
                int(parentdata["source_pruning"]["surviving_source_strokes"]))
            if any(trim[i]["width"]!=w
                   for i,w in zip(WIDTH_IDS[method],ORIGINAL_WIDTHS[method])):
                raise ValueError("BLOCKED_P4B10_WRONG_P4B9_CAUSAL_WIDTH")
            method_dir=output/method
            method_dir.mkdir()
            for suffix in ("SOURCE_RGB","SOURCE_ENGINE_INDICES","OWNER_COMPONENT"):
                shutil.copyfile(original_dir/(method+"_"+suffix+".png"),
                                method_dir/(suffix+".png"))
            (method_dir/"TRIM50_FROZEN_STROKES.json").write_text(
                json.dumps(trim,ensure_ascii=False,indent=2)+"\n","utf8")
            (method_dir/"TRIM50_FROZEN_LEDGER.json").write_text(
                json.dumps(trim_ledger,ensure_ascii=False,indent=2)+"\n","utf8")
            # Same-run native original TRIM50. Never treat model as footprint.
            native=p4b5.native_replay(
                workspace,method,"P4B10_FROZEN_TRIM50",trim,method_dir)
            ref=native["color-115"]
            ref_metrics,blank=p4b4.native_diagnostics(
                ref,native["blank"],component,owner,protected)
            a=ref_metrics["24"]
            far_yx=p4b9.native_far3_targets(ref,owner)
            if (blank!=0 or len(far_yx)!=EXPECTED_FAR[method] or
                    a["native_protected_foreign_face_eyes_hands_pixels"]!=0 or
                    a["native_foreign_distance_gt_T3_0"]!=EXPECTED_FAR[method] or
                    abs(a["native_component_coverage"]-parentdata[
                        "native_final_alpha"]["24"]["native_component_coverage"])>1e-12):
                raise ValueError("BLOCKED_P4B10_FROZEN_P4B8_P4B9_NATIVE_DRIFT")
            if len(p4b7.protected_targets(ref,owner,protected))!=0:
                raise ValueError("BLOCKED_P4B10_PROTECTED_FROZEN_NATIVE")
            original_targets=[
                (191,833),(275,776)
            ]
            arms={}
            # One Firefox per source E/F; full original alpha parity required.
            with p4b7.native_egret_session(workspace) as driver:
                control=p4b7.native_replay_in_session(
                    driver,method_dir,method,"P4B10_FULL_NATIVE_CONTROL",trim)
                if not np.array_equal(control[:,:,3],ref[:,:,3]):
                    raise ValueError("BLOCKED_P4B10_SAME_RUN_NATIVE_ALPHA_PARITY")
                print("P4B10_NATIVE_FULL_CONTROL_PASS",method,flush=True)
                for name,widths in width_arms(method):
                    proposed,ledger=width_only_variant(
                        trim,method,widths,component,
                        int(parentdata["source_pruning"]["surviving_source_strokes"]))
                    label="P4B10_"+name
                    armfolder=method_dir/name
                    armfolder.mkdir()
                    (armfolder/"PLAN.json").write_text(
                        json.dumps(proposed,ensure_ascii=False,indent=2)+"\n","utf8")
                    (armfolder/"WIDTH_LEDGER.json").write_text(
                        json.dumps(ledger,ensure_ascii=False,indent=2)+"\n","utf8")
                    image=p4b7.native_replay_in_session(
                        driver,armfolder,method,label,proposed)
                    blankpath=armfolder/("P4B7-"+method+"-"+label+"-blank.png")
                    real_blank=np.asarray(Image.open(blankpath).convert("RGBA"),np.uint8)
                    metrics,blank_nonzero=p4b4.native_diagnostics(
                        image,real_blank,component,owner,protected)
                    if blank_nonzero:
                        raise ValueError("BLOCKED_P4B10_NONZERO_NATIVE_BLANK")
                    z=metrics["24"]
                    far=p4b9.native_far3_targets(image,owner)
                    if len(far)!=z["native_foreign_distance_gt_T3_0"]:
                        raise ValueError("BLOCKED_P4B10_FAR3_METRIC_DISAGREES")
                    safe=(z["native_protected_foreign_face_eyes_hands_pixels"]==0 and
                          z["native_foreign_distance_gt_T3_0"]==0)
                    quality=bool(safe and z["native_component_coverage"]>=COVERAGE_GATE
                                 and z["actual_native_ink_backing_pixels"]>0)
                    arms[name]={
                        "source_width_ledger":ledger,
                        "native_Egret_real":True,
                        "native_blank_zero":blank_nonzero,
                        "native_alpha":metrics,
                        "native_far3_target_backing_yx":[list(t) for t in far],
                        "original_protected_target_raw_alpha":
                            p4b7.pixel_alpha(image,original_targets),
                        "native_safe_protected_and_far3":safe,
                        "native_quality_pass":quality,
                        "quality_status": "NATIVE_ALL_GATES_PASS" if quality
                              else "NATIVE_CORRECTION_WIDTH_QUALITY_FAIL",
                    }
                    print("P4B10_NATIVE",method,name,"coverage",
                          round(z["native_component_coverage"],7),"protected",
                          z["native_protected_foreign_face_eyes_hands_pixels"],
                          "far3",z["native_foreign_distance_gt_T3_0"],
                          "quality",arms[name]["quality_status"],flush=True)
            best=choose_best_safe(arms)
            if best["arm"]:
                arm=best["arm"]
                selected=method_dir/arm/("P4B7-"+method+"-P4B10_"+arm+"-color-115.png")
                shutil.copyfile(selected,method_dir/"BEST_SAFE_DIAGNOSTIC_NATIVE.png")
            if len(arms)!=len(width_arms(method)):
                raise ValueError("BLOCKED_P4B10_INCOMPLETE_REAL_SCENES")
            findings[method]={
                "original_P4B8_trim50_full_alpha_metrics":ref_metrics,
                "original_P4B9_far3_backing_yx":[list(t) for t in far_yx],
                "exact_native_full_alpha_parity":True,
                "p4b8_source_trim50_ledger":trim_ledger,
                "all_arms_genuine_native":True,
                "arms":arms,
                "native_safe_width_arm_count":sum(1 for o in arms.values()
                                                   if o["native_safe_protected_and_far3"]),
                "native_all_gates_pass_arm_count":sum(1 for o in arms.values()
                                                      if o["native_quality_pass"]),
                "best_safe_diagnostic":best,
                "overall_quality_frozen99_0protected_far3":
                    any(o["native_quality_pass"] for o in arms.values()),
            }
            print("P4B10_METHOD_RESULT",method,"native_safe",
                  findings[method]["native_safe_width_arm_count"],"best",best,
                  flush=True)
        shutil.copytree(original_dir,output/"FRESH_P4B6_SAME_RUN_ORIGINAL")
    success=all(rec["overall_quality_frozen99_0protected_far3"]
                for rec in findings.values())
    if (set(findings)!=set(METHODS) or
            len(findings[E_METHOD]["arms"])!=60 or
            len(findings[F_METHOD]["arms"])!=10):
        raise ValueError("BLOCKED_P4B10_MISSING_70_NATIVE_RESULTS")
    hashes={
        str(f.relative_to(output)).replace("\\","/"):digest(f.read_bytes())
        for f in sorted(output.rglob("*")) if f.is_file()
    }
    report={
        "experiment":EXPERIMENT,"prereg_id":EXPERIMENT,
        "result":"BOTH_EF_NATIVE_ALL_GATES_PASS" if success else
                 "NATIVE_WIDTH_SWEEP_QUALITY_NOT_ALL_PASS",
        "true_Egret_native_arms_complete":70,
        "source_original_SHA256":SOURCE_SHA,
        "source_key":SOURCE_KEY,"source_engine_owner_index":OWNER,
        "p4b6_git_blob":P4B6_BLOB,"p4b7_git_blob":P4B7_BLOB,
        "p4b8_git_blob":P4B8_BLOB,"p4b9_git_blob":P4B9_BLOB,
        "renderer_git_blob":RENDERER_BLOB,
        "p4b6_recomputed_original_same_run":True,
        "frozen_width_matrix_E_60_F_10":True,
        "source_original_EF_only":True,
        "old_G32_P4c1_V44_as_candidate":False,
        "native_alpha_gate":ALPHA,
        "frozen_owner_coverage_gate":COVERAGE_GATE,
        "frozen_protected_foreign_gate":PROTECTED_GATE,
        "frozen_spill_logical_gate":SPILL_GATE,
        "max_strokes":MAX_STROKES,
        "max_synthetic_vertices_NOT_CHALK":MAX_VERTICES,
        "methods":findings,
        "production_promotion":False,
        "E4_game_runtime":"NOT_RUN","E5_independent":"NOT_RUN",
        "exact_CHALK":None,
        "github_sha":os.getenv("GITHUB_SHA"),
        "github_run_id":os.getenv("GITHUB_RUN_ID"),
        "file_sha256":hashes,
    }
    (output/"README_REVIEW_RU.txt").write_text(
        "P4B10: настоящая игровая Egret кисть на 70 полнометражных вариантах.\n"
        "Исходные C192 E/F и TRIM50 неизменны кроме ширин двух E и одной F.\n"
        "В E 10*6=60 комбинаций, в F 10 ширин; реальные PNG и blank каждого.\n"
        "Best safe: ноль чужого защищённого alpha24 и ноль farther3.\n"
        "Даже safe вариант НЕЛЬЗЯ принимать, если своей области <99%.\n"
        "Точный CHALK и игра E4 не измерялись; все результаты только E3.\n",
        "utf8")
    (output/"report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
    return report


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--workspace",required=True,type=Path)
    ap.add_argument("--source",required=True,type=Path)
    ap.add_argument("--engine-js",required=True,type=Path)
    ap.add_argument("--renderer",required=True,type=Path)
    ap.add_argument("--output",required=True,type=Path)
    args=ap.parse_args()
    try:
        r=run(args.workspace,args.source,args.engine_js,args.renderer,args.output)
    except Exception as ex:
        args.output.mkdir(parents=True,exist_ok=True)
        (args.output/"FAILED_EVIDENCE.json").write_text(
            json.dumps({"experiment":EXPERIMENT,"status":"BLOCKED",
                        "exception_type":type(ex).__name__,
                        "reason":str(ex),"github_sha":os.getenv("GITHUB_SHA"),
                        "github_run_id":os.getenv("GITHUB_RUN_ID"),
                        "native_quality_NOT_ESTABLISHED":True,
                        "exact_CHALK":None},ensure_ascii=False,indent=2)+"\n","utf8")
        raise
    print("P4B10_RESULT",r["result"],"E4_E5_EXACT_CHALK_NOT_RUN",flush=True)

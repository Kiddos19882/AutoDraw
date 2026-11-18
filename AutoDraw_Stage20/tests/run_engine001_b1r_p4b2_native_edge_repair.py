#!/usr/bin/env python3
"""ENGINE-001 B1-R-P4B2: ONE true-native alpha24 boundary gap feedback pass.

P4B1 original-only generated IN THIS RUN; no archived source maps as inputs.
Each measured gap is true Egret BoardPane/WebGL alpha, not model coverage.
No game E4, exact CHALK, old G32/P4c1/V44 or production edits.
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import os
import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
from run_engine001_b1r_p3b_engine128_adaptive32 import (
    ENGINE_GIT_BLOB_SHA1, SOURCE_SHA, read_engine_palette
)
from run_engine001_b1r_p1_fullrgb_edge_aware import check_source
from run_engine001_b1r_p2_joint_region_outline import digest
from run_engine001_complex_holdout_v5 import native_batch

EXPERIMENT = "ENGINE001_B1R_P4B2_NATIVE_EDGE_GAP_REPAIR_V1"
P4B1_SOURCE_BLOB = "b95aa361cf2ec94d5fa28e7309bd3e4af15eca93"
RENDERER_BLOB = p4b1.RENDERER_BLOB
SOURCE = p4b1.NATIVE_SOURCE_KEY
METHODS = p4b1.METHODS
STRATEGY = "A_ORIENTED"
CORRECTION_WIDTHS = (2, 1)
CONTOUR_CHORD_OFFSETS = (4, 8)
CONTOUR_START_STRIDE = 2
MICRO_STROKE_LENGTH = .25
EDGE_MAX_DISTANCE = 2.0
MAX_TOTAL_STROKES = p4b1.MAX_STROKES
MAX_TOTAL_VERTICES = p4b1.MAX_VERTICES
ALPHA_PRIMARY = 24
COVERAGE_GATE = p4b1.NATIVE_COMPONENT_COVERAGE_GATE
LEAKAGE_GATE = p4b1.LEAKAGE_MAX_LOGICAL
ROI_X0 = p4b1.ROI_X0
LOGICAL = p4b1.LOGICAL_SHAPE
BACKING = p4b1.BACKING_SHAPE


def boundary_missing(native_rgba: np.ndarray, component: np.ndarray):
    """True native gaps collapsed from each 3x3 source logical cell, no models."""
    if (native_rgba.shape != BACKING or native_rgba.dtype != np.uint8 or
            component.shape != LOGICAL or component.dtype != np.bool_):
        raise ValueError("BLOCKED_P4B2_NATIVE_OR_COMPONENT_SHAPE")
    actual = native_rgba[:, ROI_X0*3:(ROI_X0+150)*3, 3] >= ALPHA_PRIMARY
    expanded = np.repeat(np.repeat(component, 3, axis=0), 3, axis=1)
    missing = expanded & ~actual
    weights = missing.reshape(240, 3, 150, 3).sum(axis=(1, 3)).astype(np.int16)
    dist = cv2.distanceTransform(
        np.pad(component.astype(np.uint8), 1),
        cv2.DIST_L2, cv2.DIST_MASK_PRECISE)[1:-1, 1:-1]
    eligible = component & (dist <= EDGE_MAX_DISTANCE) & (weights > 0)
    if np.any(eligible & ~component) or np.any(weights[~component]):
        raise AssertionError("BLOCKED_P4B2_NATIVE_MISSING_OUTSIDE_SOURCE")
    return weights, eligible, missing, {
        "native_component_missing_backing_pixels": int(missing.sum()),
        "native_missing_logical_cells_any_alpha24": int((weights > 0).sum()),
        "source_boundary_eligible_logical_cells": int(eligible.sum()),
        "source_boundary_eligible_backing_pixels_weight": int(
            weights[eligible].sum()),
        "source_interior_gt2_missing_backing_pixels": int(
            weights[component & (dist > EDGE_MAX_DISTANCE)].sum()),
    }


def repair_candidates(component: np.ndarray, full_owner: np.ndarray,
                      eligible: np.ndarray):
    """Source-supported short boundary chords/micros, model only for shortlist."""
    if (component.shape != LOGICAL or component.dtype != np.bool_ or
            full_owner.shape != LOGICAL or full_owner.dtype != np.bool_ or
            eligible.shape != LOGICAL or eligible.dtype != np.bool_ or
            np.any(component & ~full_owner) or
            np.any(eligible & ~component)):
        raise ValueError("BLOCKED_P4B2_REPAIR_CANDIDATE_INPUT")
    outside = cv2.distanceTransform(
        (~full_owner).astype(np.uint8), cv2.DIST_L2,
        cv2.DIST_MASK_PRECISE)
    nontarget = np.uint8(component)
    contours, _ = cv2.findContours(
        nontarget, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    contours = sorted(contours, key=lambda c: (
        cv2.boundingRect(c)[1], cv2.boundingRect(c)[0],
        cv2.boundingRect(c)[2], cv2.boundingRect(c)[3]))
    result = []
    dedupe = set()

    def add(points, width, kind):
        if (len(points) != 2 or
                not p4b1._source_centerline(points, component)):
            return
        key = (width, tuple(round(v, 4) for xy in points for v in xy))
        if key in dedupe:
            return
        dedupe.add(key)
        opt = p4b1._model_candidate(
            points, width, component, full_owner, outside,
            kind, "SOURCE_BOUNDARY")
        if opt is not None:
            # Never consider an option unrelated to ACTUALLY missing edge cells.
            if bool(np.any(eligible.ravel()[opt["owner_flat"]])):
                result.append(opt)

    for contour in contours:
        xy = contour.reshape(-1, 2)
        n = len(xy)
        if n < 2:
            continue
        for start in range(0, n, CONTOUR_START_STRIDE):
            for offset in CONTOUR_CHORD_OFFSETS:
                if offset >= n:
                    continue
                first = tuple(float(x) for x in xy[start])
                end = tuple(float(x) for x in xy[(start+offset) % n])
                if first == end:
                    continue
                for width in CORRECTION_WIDTHS:
                    add([first, end], width, "contour_source_short")
    for y, x in np.argwhere(eligible):
        y, x = int(y), int(x)
        pts = [(x+.125, float(y)), (x+.125+MICRO_STROKE_LENGTH, float(y))]
        for width in CORRECTION_WIDTHS:
            add(pts, width, "source_micro_gap")
    return result


def choose_corrections(component: np.ndarray, full_owner: np.ndarray,
                       measured_weights: np.ndarray,
                       eligible: np.ndarray,
                       engine_index: int, game128: np.ndarray,
                       baseline_strokes: list[dict]):
    if (component.shape != LOGICAL or component.dtype != np.bool_ or
            full_owner.shape != LOGICAL or full_owner.dtype != np.bool_ or
            measured_weights.shape != LOGICAL or
            not np.issubdtype(measured_weights.dtype, np.integer) or
            np.any(measured_weights < 0) or
            eligible.shape != LOGICAL or eligible.dtype != np.bool_ or
            np.any(eligible & ~component) or
            game128.shape != (128, 3) or game128.dtype != np.uint8 or
            not 0 <= engine_index < 128 or
            not isinstance(baseline_strokes, list)):
        raise ValueError("BLOCKED_P4B2_SELECTION_INPUT")
    base_count = len(baseline_strokes)
    base_points = sum(len(s["points"]) for s in baseline_strokes)
    if (not 1 <= base_count < MAX_TOTAL_STROKES or
            not 2 <= base_points < MAX_TOTAL_VERTICES or
            any(s.get("colorIndex") != engine_index for s in baseline_strokes)):
        raise ValueError("BLOCKED_P4B2_BASELINE_BUDGET_OR_COLOR")
    room_strokes = MAX_TOTAL_STROKES - base_count
    room_points = MAX_TOTAL_VERTICES - base_points
    if room_strokes < 1 or room_points < 2:
        raise ValueError("BLOCKED_P4B2_NO_REPAIR_RESOURCE")
    opts = repair_candidates(component, full_owner, eligible)
    remain = measured_weights.astype(np.int32).ravel().copy()
    heap = []
    for i, item in enumerate(opts):
        gain = int(remain[item["owner_flat"]].sum())
        if gain > 0:
            heapq.heappush(heap, (-gain/item["vertices"], -gain,
                                  -item["width"], i, gain))
    selected = []
    selected_by_kind = {}
    while heap and len(selected) < room_strokes and 2*len(selected)+2 <= room_points:
        _, _, _, idx, old = heapq.heappop(heap)
        item = opts[idx]
        gain = int(remain[item["owner_flat"]].sum())
        if gain != old:
            if gain:
                heapq.heappush(heap, (-gain/item["vertices"], -gain,
                                      -item["width"], idx, gain))
            continue
        if gain <= 0:
            continue
        rgb = game128[engine_index]
        stroke = {
            "strokeId": "icon-%d" % (base_count + len(selected)),
            "width": int(item["width"]),
            "colorIndex": int(engine_index),
            "colorRgb": (int(rgb[0]) << 16) | (int(rgb[1]) << 8) | int(rgb[2]),
            "points": [
                {"x": float(x)+ROI_X0, "y": float(y)}
                for x, y in item["points"]
            ],
        }
        selected.append(stroke)
        remain[item["owner_flat"]] = 0
        selected_by_kind[item["kind"]] = selected_by_kind.get(item["kind"],0)+1
    if (base_count+len(selected)>MAX_TOTAL_STROKES or
            base_points+2*len(selected)>MAX_TOTAL_VERTICES):
        raise AssertionError("BLOCKED_P4B2_RESOURCE_CAP_DRIFT")
    return selected, {
        "original_stroke_count": base_count,
        "original_synthetic_vertices_NOT_CHALK": base_points,
        "additional_stroke_count": len(selected),
        "additional_vertices_NOT_CHALK": 2*len(selected),
        "combined_stroke_count": base_count+len(selected),
        "combined_synthetic_vertices_NOT_CHALK": base_points+2*len(selected),
        "candidate_short_boundary_count_MODEL_ONLY": len(opts),
        "eligible_native_missing_backing_weight": int(
            measured_weights[eligible].sum()),
        "unaddressed_MODEL_ONLY_native_missing_backing_weight": int(
            remain.reshape(LOGICAL)[eligible].sum()),
        "greedy_ranking_uses_actual_native_alpha24_miss_weight": True,
        "only_one_feedback_batch": True,
        "repair_width_histogram": {
            str(w): sum(s["width"] == w for s in selected)
            for w in CORRECTION_WIDTHS
        },
        "repair_route_kinds": selected_by_kind,
    }


def get_rgba(archive_dir: Path, method: str, strategy: str):
    file = (archive_dir/("NATIVE_"+method+"_"+strategy)/
            ("P4B1-"+method+"-"+strategy+"-color-115.png"))
    return np.asarray(Image.open(file).convert("RGBA"), dtype=np.uint8).copy()


def overlay(source: np.ndarray, component: np.ndarray, native: np.ndarray):
    """Exact native missing highlighted red, covered owner green, source behind."""
    if source.shape != (240,150,3):
        raise ValueError("BLOCKED_P4B2_SOURCE_RGB_SHAPE")
    rgb = np.repeat(np.repeat(source, 3, axis=0), 3, axis=1).copy()
    target = np.repeat(np.repeat(component,3,axis=0),3,axis=1)
    ink = native[:, ROI_X0*3:(ROI_X0+150)*3,3] >= ALPHA_PRIMARY
    painted = target & ink
    missed = target & ~ink
    # A source plus overlay is for human diagnosis, NOT a geometry estimate.
    rgb[painted] = (
        .38*rgb[painted] + .62*np.array([43,200,93])
    ).astype(np.uint8)
    rgb[missed] = (
        .25*rgb[missed] + .75*np.array([255,47,42])
    ).astype(np.uint8)
    return Image.fromarray(rgb)


def run(workspace: Path, source: Path, engine_js: Path,
        renderer: Path, output: Path):
    if output.exists():
        raise ValueError("BLOCKED_P4B2_OUTPUT_EXISTS")
    check_source(source)
    engine, _ = read_engine_palette(engine_js)
    if (p4b1.git_blob(Path(p4b1.__file__).read_bytes()) != P4B1_SOURCE_BLOB or
            p4b1.git_blob(renderer.read_bytes()) != RENDERER_BLOB):
        raise ValueError("BLOCKED_P4B2_PINNED_BASELINE_OR_EGRET_CODE")
    output.mkdir(parents=True)
    results = {}
    board_views = []
    with tempfile.TemporaryDirectory(prefix="engine001-p4b2-same-run-") as tmp:
        baseline_dir = Path(tmp)/"p4b1_from_original"
        parent = p4b1.run(workspace,source,engine_js,renderer,baseline_dir)
        if (parent["experiment"] != p4b1.EXPERIMENT or
                parent["result"] != "NATIVE_COMPONENT_QUALITY_NOT_ALL_PASS" or
                not parent["P3D_original_only_recomputed"] or
                not parent["P3D_all8_source_quality_pass"] or
                parent["legacy_G32_P4c1_V44_as_input"] or
                parent["original_P3D_frozen_ZIP_as_input"] or
                parent["native_source_key"] != SOURCE or
                set(parent["source_results"][SOURCE]["methods"]) != set(METHODS)):
            raise ValueError("BLOCKED_P4B2_CURRENT_RUN_ORIGINAL_PROVENANCE")
        shutil.copyfile(baseline_dir/"report.json",
                        output/"P4B1_SAME_RUN_BASELINE_REPORT.json")
        shutil.copyfile(baseline_dir/"SOURCE_ORIGINAL_LOGICAL_RGB.png",
                        output/"SOURCE_ORIGINAL_LOGICAL_RGB.png")
        for method in METHODS:
            original_prefix=SOURCE+"_"+method
            owner_info=parent["source_results"][SOURCE]["source_common_owner"]
            owner=int(owner_info["engine_index"])
            comp_file=baseline_dir/(original_prefix+"_SELECTED_COMPONENT_MASK.png")
            index_file=baseline_dir/(original_prefix+"_SOURCE_ENGINE_INDICES.png")
            rgb_file=baseline_dir/(original_prefix+"_SOURCE_RGB.png")
            component=np.asarray(Image.open(comp_file).convert("L"),
                                 np.uint8)>0
            index=np.asarray(Image.open(index_file),np.uint8).copy()
            full_owner=index==owner
            source_rgb=np.asarray(Image.open(rgb_file).convert("RGB"),
                                  np.uint8).copy()
            if not np.any(component) or np.any(component&~full_owner):
                raise ValueError("BLOCKED_P4B2_DRIFTED_OWNER_COMPONENT")
            for f,stub in ((comp_file,"OWNER_COMPONENT"),
                           (index_file,"SOURCE_ENGINE_INDICES"),
                           (rgb_file,"SOURCE_RGB")):
                shutil.copyfile(f,output/(method+"_"+stub+".png"))
            base_native=get_rgba(baseline_dir,method,STRATEGY)
            shutil.copyfile(
                baseline_dir/("NATIVE_"+method+"_"+STRATEGY)/
                ("P4B1-"+method+"-"+STRATEGY+"-color-115.png"),
                output/(method+"_BEFORE_NATIVE_COLOR.png"))
            parent_obj=parent["source_results"][SOURCE]["methods"][method][STRATEGY]
            if parent_obj["native_status"] != "NATIVE_COMPONENT_QUALITY_FAIL":
                raise ValueError("BLOCKED_P4B2_EXPECTED_BASELINE_NEGATIVE_DRIFT")
            base_scores=parent_obj["native"]["alpha_masks"]
            if (base_scores["24"]["native_component_coverage"] >= COVERAGE_GATE or
                    base_scores["24"]["native_beyond3logicalpx_other_color_pixels"]):
                raise ValueError("BLOCKED_P4B2_NATIVE_BASELINE_METRICS_DRIFT")
            measured_weights, eligible, missing, evidence = boundary_missing(
                base_native,component)
            Image.fromarray(missing.astype(np.uint8)*255).save(
                output/(method+"_ACTUAL_BEFORE_NATIVE_MISSING_ROI_BACKING.png"))
            Image.fromarray(eligible.astype(np.uint8)*255).save(
                output/(method+"_SOURCE_ORIGINAL_EDGE_ELIGIBLE.png"))
            old_path_file=baseline_dir/(
                "PATHS_"+SOURCE+"_"+method+"_"+STRATEGY+".json")
            baseline_path=json.loads(old_path_file.read_text(encoding="utf8"))
            shutil.copyfile(old_path_file,
                            output/(method+"_ORIGINAL_A_STROKES.json"))
            source_strokes=[{k:s[k] for k in
                        ("strokeId","width","colorIndex","colorRgb","points")}
                        for s in baseline_path]
            corrected,decision=choose_corrections(
                component,full_owner,measured_weights,eligible,
                owner,engine,source_strokes)
            corrected_combined=source_strokes+corrected
            if not corrected:
                # A no-gain result should still preserve full native replay.
                decision["no_eligible_corrective_stroke"]=True
            (output/(method+"_P4B2_CORRECTIVE_STROKES.json")).write_text(
                json.dumps(corrected,ensure_ascii=False,indent=2)+"\n",
                encoding="utf8")
            (output/(method+"_P4B2_FULL_REPLAY_STROKES.json")).write_text(
                json.dumps(corrected_combined,ensure_ascii=False,indent=2)+"\n",
                encoding="utf8")
            scene=output/("NATIVE_P4B2_"+method)
            scene.mkdir()
            native,meta,manifest=native_batch(
                workspace,"P4B2-"+method,corrected_combined,scene,
                renderer_method="renderP4A2BrushWidths1to10Probe")
            if (set(native) != {"blank","composite","color-"+str(owner)} or
                    set(meta) != set(native) or
                    meta["composite"].get("schema") !=
                    "ENGINE001_B1R_P4A2_NATIVE_1_TO_10" or
                    meta["composite"].get("renderer") !=
                    "real Egret 5.4.1 BoardPane/WebGLRenderer" or
                    manifest["colors_rendered"] != [owner]):
                raise ValueError("BLOCKED_P4B2_NATIVE_EGRET_IDENTITY")
            corrected_scores,blank_count=p4b1.native_metrics(
                native["color-"+str(owner)],native["blank"],component,full_owner)
            after=corrected_scores["24"]["native_component_coverage"]
            before=base_scores["24"]["native_component_coverage"]
            far=corrected_scores["24"][
                "native_beyond3logicalpx_other_color_pixels"]
            nonregression=(after >= before-1e-9)
            quality_pass=bool(
                after>=COVERAGE_GATE and far==0 and blank_count==0 and
                nonregression and
                corrected_scores["24"]["native_nonzero_ink_backing_pixels"]>0)
            results[method]={
                "source_owner_engine_index":owner,
                "original_A_native_before":base_scores,
                "corrected_native_after":corrected_scores,
                "native_blank_nonzero_alpha_pixels":blank_count,
                "real_native_Egret_BoardPane":True,
                "changed_source_RGB_or_game_index_pixels":0,
                "correction_decision":decision,
                "native_missing_evidence":evidence,
                "before_after_coverage_gain":after-before,
                "before_after_missing_backing_pixels": (
                    base_scores["24"][
                        "native_selected_component_total_backing_pixels"]-
                    base_scores["24"][
                        "native_selected_component_owner_backing_pixels"],
                    corrected_scores["24"][
                        "native_selected_component_total_backing_pixels"]-
                    corrected_scores["24"][
                        "native_selected_component_owner_backing_pixels"]
                ),
                "native_no_coverage_regression":nonregression,
                "status":"NATIVE_EDGE_REPAIR_PASS" if quality_pass
                         else "NATIVE_EDGE_REPAIR_INCOMPLETE_OR_FAIL",
            }
            board_views.append((
                method,
                overlay(source_rgb,component,base_native),
                overlay(source_rgb,component,native["color-"+str(owner)]),
                before,after
            ))
            print("P4B2",method,results[method]["status"],
                  "baseline",round(before,6),"after",round(after,6),
                  "new_strokes",len(corrected),"leakage_far",far,
                  "blank_nonzero",blank_count,flush=True)
    if set(results)!=set(METHODS):
        raise AssertionError("BLOCKED_P4B2_TWO_EF_RESULTS_NOT_RECORDED")
    panel=Image.new("RGB",(900,1540),"white")
    canvas=ImageDraw.Draw(panel)
    canvas.text((10,8),"P4B2 ACTUAL NATIVE EGRET ALPHA24: green covered / red missing",
                fill=(15,15,15))
    for i,(name,before_im,after_im,before,after) in enumerate(board_views):
        y0=40+i*750
        canvas.text((10,y0),name+" BEFORE "+format(before*100,".2f")+"%",
                    fill=(0,0,0))
        canvas.text((460,y0),name+" AFTER "+format(after*100,".2f")+"%",
                    fill=(0,0,0))
        panel.paste(before_im,(0,y0+22))
        panel.paste(after_im,(450,y0+22))
    panel.save(output/"REVIEW_NATIVE_EF_BEFORE_AFTER_EDGE_GAPS.png")
    (output/"README_REVIEW_RU.txt").write_text(
        "P4B2: ТОЛЬКО настоящий Egret/BoardPane alpha24: зелёный покрыто, "
        "красный пропуск.\n"
        "P4B1 SAME-RUN A E/F baseline and P4B2 one measured-boundary repair.\n"
        "Использованы только исходный RGB, accepted P3D, widths 1/2 "
        "для ДОБАВОЧНЫХ штрихов.\n"
        "Заливка чужих цветов >3 logicalpx и 99% true native coverage "
        "считаются по реальному PNG.\n"
        "MODEL_ONLY shortlist не является доказательством покрытия.\n"
        "Игровой E4/E5 и точный CHALK NOT_RUN. "
        "Все отрицательные результаты сохранены.\n",
        encoding="utf8")
    hashes={
        str(f.relative_to(output)).replace("\\","/"):digest(f.read_bytes())
        for f in sorted(output.rglob("*")) if f.is_file()
    }
    passed=all(results[m]["status"]=="NATIVE_EDGE_REPAIR_PASS" for m in METHODS)
    report={
        "experiment":EXPERIMENT,
        "parent_same_run_experiment":p4b1.EXPERIMENT,
        "parent_same_run_quality_gate":"NATIVE_COMPONENT_QUALITY_NOT_ALL_PASS",
        "result":"NATIVE_EDGE_REPAIR_PASS" if passed else
                 "NATIVE_EDGE_REPAIR_PARTIAL_OR_FAIL",
        "native_two_EF_replay_scenes_complete":True,
        "source_sha256":SOURCE_SHA,
        "engine_git_blob_sha1":ENGINE_GIT_BLOB_SHA1,
        "renderer_git_blob_sha1":RENDERER_BLOB,
        "baseline_P4B1_runner_blob_sha1":P4B1_SOURCE_BLOB,
        "P4B1_recomputed_current_run_original_only":True,
        "P3D_original_only_all_EF_quality_pass":True,
        "legacy_G32_P4c1_V44_as_input":False,
        "read_frozen_P4B1_P3D_ZIPs_for_candidate":False,
        "source_key":SOURCE,
        "methods":list(METHODS),
        "new_widths_only":[1,2],
        "one_native_feedback_round":True,
        "fixed_cumulative_max_strokes":MAX_TOTAL_STROKES,
        "fixed_cumulative_max_synthetic_vertices_NOT_CHALK":MAX_TOTAL_VERTICES,
        "coverage_alpha24_gate":COVERAGE_GATE,
        "far_leakage_logical_px_gate":LEAKAGE_GATE,
        "methods_results":results,
        "actual_game_E4":"NOT_RUN",
        "independent_E5":"NOT_RUN",
        "exact_game_run_bound_CHALK":None,
        "production_promotion":False,
        "github_sha":os.getenv("GITHUB_SHA"),
        "github_run_id":os.getenv("GITHUB_RUN_ID"),
        "file_sha256":hashes,
    }
    (output/"report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n",
        encoding="utf8")
    return report


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--workspace",type=Path,required=True)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--engine-js",type=Path,required=True)
    p.add_argument("--renderer",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    try:
        result=run(args.workspace,args.source,args.engine_js,
                   args.renderer,args.output)
    except Exception as error:
        if not args.output.exists():
            args.output.mkdir(parents=True)
        (args.output/"FAILED_EVIDENCE.json").write_text(
            json.dumps({"experiment":EXPERIMENT,
                        "status":"BLOCKED_TECHNICAL",
                        "error_type":type(error).__name__,
                        "error":str(error),
                        "github_sha":os.getenv("GITHUB_SHA"),
                        "github_run_id":os.getenv("GITHUB_RUN_ID"),
                        "exact_CHALK":None},ensure_ascii=False,indent=2)+"\n",
            encoding="utf8")
        raise
    print("P4B2_FINAL",result["result"],
          "both original E/F real native alpha24 compared,"
          "E4/E5/exact CHALK NOT_RUN")

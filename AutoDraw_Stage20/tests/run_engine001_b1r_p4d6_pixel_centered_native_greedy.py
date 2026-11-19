#!/usr/bin/env python3
"""P4D6: single-variable *input endpoints* controlled continuation of P4D5.

Reuse entire original P4D5 candidate pool, Egret oracle, cumulative state
re-render, safety gates and baseline; only move candidates to pixel centers.
The original P4D5 source is never edited and historical CI is immutable.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
from pathlib import Path

import numpy as np

import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
import run_engine001_b1r_p4d5_pixel_state_native_feedback as parent
from run_engine001_b1r_p2_joint_region_outline import digest

EXPERIMENT="ENGINE001_B1R_P4D6_PIXEL_CENTERED_NATIVE_GREEDY_V1"
PREREG="ENGINE001_B1R_P4D6_PIXEL_CENTERED_NATIVE_BRUSH_PREREG_2026-11-19.md"
PARENT_BLOB="147f4c2ec439bac72228b6828c67bfd45b49b28e"
FROZEN_P4D5_SAFE=9
FROZEN_P4D5_CORRECT=10
FROZEN_P4D5_NONWHITE=307
P4D6_LONG_OFFSET=.5
P4D6_MICRO_OFFSETS=(.49,.51)
P4D6_MICRO_Y_OFFSET=.5


def centered_candidate(owner:int,width:int,points:list[tuple[int,int]],
                       palette:np.ndarray,index:np.ndarray,
                       original):
    """Reuse parent model screening, only reposition native candidate controls."""
    c=original(owner,width,points,palette,index)
    if c is None:
        return None
    if not points:
        raise ValueError("BLOCKED_P4D6_EMPTY_SOURCE_POINTS")
    if len(points)==1:
        x,y=points[0]
        native=parent.make_stroke(owner,palette,width,
                                  x+P4D6_MICRO_OFFSETS[0],y+P4D6_MICRO_Y_OFFSET,
                                  x+P4D6_MICRO_OFFSETS[1],y+P4D6_MICRO_Y_OFFSET)
    else:
        x0,y0=points[0]
        x1,y1=points[-1]
        native=parent.make_stroke(owner,palette,width,
                                  x0+P4D6_LONG_OFFSET,y0+P4D6_LONG_OFFSET,
                                  x1+P4D6_LONG_OFFSET,y1+P4D6_LONG_OFFSET)
    if (c["stroke"]["colorIndex"]!=native["colorIndex"] or
        c["stroke"]["colorRgb"]!=native["colorRgb"] or
        c["stroke"]["width"]!=native["width"] or
        c["model_only"] is not True):
        raise ValueError("BLOCKED_P4D6_PARENT_SOURCE_GEOMETRY_DRIFT")
    c["stroke"]=native
    return c


@contextmanager
def scoped_centered_trial():
    if p4b1.git_blob(Path(parent.__file__).read_bytes())!=PARENT_BLOB:
        raise ValueError("BLOCKED_P4D6_FROZEN_P4D5_MODULE_CHANGED")
    original=parent._source_candidate
    old_id,old_doc=parent.EXPERIMENT,parent.PREREG
    def dispatch(owner,width,points,palette,index):
        return centered_candidate(owner,width,points,palette,index,original)
    parent._source_candidate=dispatch
    parent.EXPERIMENT=EXPERIMENT
    parent.PREREG=PREREG
    try:
        yield
    finally:
        parent._source_candidate=original
        parent.EXPERIMENT=old_id
        parent.PREREG=old_doc


def run(workspace:Path,source:Path,engine_js:Path,renderer:Path,output:Path):
    # This scoped adapter does not modify the original source bytes, default
    # algorithms, game engine or actual renderer. Only in-memory test calls.
    if EXPERIMENT not in (workspace/"AutoDraw_Stage20"/"docs"/PREREG).read_text("utf8"):
        raise ValueError("BLOCKED_P4D6_NOT_PREREGISTERED")
    with scoped_centered_trial():
        result=parent.run(workspace,source,engine_js,renderer,output)
    if result["experiment"]!=EXPERIMENT:
        raise ValueError("BLOCKED_P4D6_WRONG_EXPERIMENT")
    for method,report in result["methods"].items():
        base=report["source_owner_correct_zero_to_one_native_baseline"]
        greedy=report["source_owner_correct_zero_to_one_native_greedy"]
        if (report["target_nonwhite_pixels"]!=FROZEN_P4D5_NONWHITE or
            base["correct_logical_native_5_of_9"]!=FROZEN_P4D5_NONWHITE or
            base["white_target_ink_alpha24_backing"]!=264 or
            base["any_ink_outside_crop_alpha24_backing"]!=52):
            raise ValueError("BLOCKED_P4D6_PARENT_CONTROL_OR_SOURCE_CHANGED")
        report["same_original_index_as_P4D5"]=True
        report["changed_only_native_candidate_point_centers"]=True
        report["P4D5_previous_safe_candidates"]=FROZEN_P4D5_SAFE
        report["P4D5_previous_correct_owner_pixels"]=FROZEN_P4D5_CORRECT
        report["delta_safe_candidates_vs_P4D5"]=(
            report["isolated_native_safe_candidates"]-FROZEN_P4D5_SAFE)
        report["delta_correct_owner_pixels_vs_P4D5"]=(
            greedy["correct_logical_native_5_of_9"]-FROZEN_P4D5_CORRECT)
        report["P4D6_improved_safe_coverage"]=(
            report["isolated_native_safe_candidates"]>FROZEN_P4D5_SAFE and
            greedy["correct_logical_native_5_of_9"]>FROZEN_P4D5_CORRECT and
            greedy["white_target_ink_alpha24_backing"]==0 and
            greedy["any_ink_outside_crop_alpha24_backing"]==0 and
            report["accepted_candidate_native_foreign_alpha24_zero"])
        print("P4D6_COMPARE",method,"safe",FROZEN_P4D5_SAFE,"->",
              report["isolated_native_safe_candidates"],"correct",
              FROZEN_P4D5_CORRECT,"->",greedy["correct_logical_native_5_of_9"],
              "target",FROZEN_P4D5_NONWHITE,"improved",
              report["P4D6_improved_safe_coverage"],flush=True)
    result["technical_result"]="P4D6_EF_NATIVE_PIXEL_CENTERED_FULL_ORACLE_AND_FEEDBACK"
    result["P4D5_original_sha"]="3b1d82b5abdfdaee5d435cb99c16dee931642f38"
    result["P4D5_original_E3_run"]=44424883298
    result["P4D5_original_artifact_id"]=14484520872
    result["parent_P4D5_git_blob"]=PARENT_BLOB
    result["changed_variable"]="source-pixel-center input control points only"
    result["native_point_position_2pt_micro"]={
        "x_delta_start":P4D6_MICRO_OFFSETS[0],"x_delta_end":P4D6_MICRO_OFFSETS[1],
        "y_delta":P4D6_MICRO_Y_OFFSET}
    result["native_point_position_long"]={"x_delta":.5,"y_delta":.5}
    result["scientific_result"]=(
        "PILOT_COVERAGE_IMPROVED_WITH_ZERO_ALPHA24_SPILL"
        if all(m["P4D6_improved_safe_coverage"] for m in result["methods"].values())
        else "PILOT_NO_SAFE_COVERAGE_IMPROVEMENT")
    (output/"README_RU.txt").write_text(
        "ENGINE001 P4D6: одно изменение относительно P4D5: native centers "
        "+0.5,+0.5 logical (микро-линия x+.49..x+.51,y+.5), без изменения "
        "цветов, ROI, C192 E/F, толщин, pool, порогов, Egret. "
        "P4D5 9 безопасных из240 и 10/307 source pixels. "
        "P4D6 проверено native PNG, каждый шаг 0/1 real cumulative WebGL. "
        "Не production, не живой CHALK, E/F crop identical.\n","utf8")
    # Re-create audit manifest after replacing the parent README.
    result["members_sha256"]={
        str(p.relative_to(output)).replace("\\","/"):digest(p.read_bytes())
        for p in sorted(output.rglob("*")) if p.is_file() and p.name!="report.json"
    }
    (output/"report.json").write_text(json.dumps(
        result,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--workspace",type=Path,required=True)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--engine-js",type=Path,required=True)
    p.add_argument("--renderer",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    run(args.workspace,args.source,args.engine_js,args.renderer,args.output)

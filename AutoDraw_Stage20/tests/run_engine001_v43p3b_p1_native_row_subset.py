#!/usr/bin/env python3
"""V43-P3b/P1: real Egret old-route subset checks ranked by native ink row overlap.

Never edits or executes full A/B paint plan; P0 is imported without changing it.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
from run_engine001_v43p3b_native_subset import (
    EXP as P0_EXP, ALPHAS, WIDTHS, MAX_SAMPLE_PER_WIDTH,
    load_p3a3, subset_result, P3A3_ARTIFACT_ZIP_SHA256,
)
from run_engine001_boundary_shift_native_v39 import verified_input
from run_engine001_complex_holdout_v5 import native_batch
from run_engine001_native_color_boundary_audit_v38 import original_labels
from run_engine001_native_warm_color_v34 import SOURCE_SHA,sha
from run_engine001_native_wide_interior_v43p2a import largest_dark_component

EXP="ENGINE001_V43P3B_P1_NATIVE_ROW_INTERSECTION"


def rank_old_strokes(base:dict, candidate_alpha:np.ndarray):
    """Native ink on original source stroke center row ONLY ranks candidates.

    Full replacement requires a separate real native subset proof.
    """
    if (base.get("paint_strokes"),base.get("detail_strokes"),
        base.get("synthetic_vertices_NOT_CHALK"),len(base.get("strokes",[])))!=(
            1945,410,5682,2355):
        raise ValueError("P1 original V37-P2 stroke plan counts drift")
    if (candidate_alpha.shape!=(720,1380) or
        candidate_alpha.dtype!=np.uint8):
        raise ValueError("P1 native candidate alpha shape/type drift")
    scored=[]
    for idx,entry in enumerate(base["strokes"][:1945]):
        stroke=entry["stroke"]
        if entry["layer"]!="paint":
            raise ValueError("P1 paint layer identity drift")
        if stroke["colorIndex"]!=7:
            continue
        a,b=stroke["points"]
        if (stroke["width"]!=2 or len(stroke["points"])!=2 or
            a["y"]!=b["y"] or a["y"]!=round(a["y"]) or
            a["x"]!=round(a["x"]) or b["x"]!=round(b["x"]) or
            not (155<=a["x"]<=b["x"]<305 and 0<=a["y"]<240)):
            raise ValueError("P1 original color7 width2 geometry drift")
        x0,x1,y=int(a["x"]),int(b["x"]),int(a["y"])
        score=int(np.count_nonzero(candidate_alpha[
            3*y:3*(y+1),3*x0:3*(x1+1)]>=24))
        if score>0:
            scored.append((score,idx,stroke))
    scored.sort(key=lambda x:(-x[0],x[1]))
    selected=scored[:MAX_SAMPLE_PER_WIDTH]
    return [{"original_paint_array_index":i,"native_candidate_row_alpha24_score":score,
             "stroke":s} for score,i,s in selected],{
        "selection":"P1_REAL_NATIVE_INK_SOURCE_ROW_RANKING_NOT_FULL_REPLACEMENT",
        "eligible_positive_score":len(scored),
        "selected":len(selected),
        "unsampled_positive_score":max(0,len(scored)-MAX_SAMPLE_PER_WIDTH),
        "selected_IDs_in_ranking_order":[s["strokeId"] for _,_,s in selected],
        "max_sample_per_width":MAX_SAMPLE_PER_WIDTH,
    }


def main():
    p=argparse.ArgumentParser()
    for name in ("workspace","source","v37p2-archive","p3a3-archive","output"):
        p.add_argument("--"+name,required=True,type=Path)
    a=p.parse_args()
    if sha(a.source)!=SOURCE_SHA:
        raise ValueError("P1 source SHA drift")
    if a.output.exists():
        raise ValueError("P1 no overwrite")
    base=verified_input(a.v37p2_archive)
    p3a3,actual_candidates=load_p3a3(a.p3a3_archive,SOURCE_SHA)
    labels=original_labels(a.source)[::3,::3].copy()
    _,_,component=largest_dark_component(labels)
    if component["component_area"]!=5005:
        raise ValueError("P1 source component drift")
    a.output.mkdir(parents=True)
    results={}
    total_replays=0
    for width in WIDTHS:
        selected,selection=rank_old_strokes(base,actual_candidates[width])
        records=[]
        for i,item in enumerate(selected):
            out=a.output/str(width)/f"old-{i:02d}"
            out.mkdir(parents=True)
            raw=item["stroke"]
            scenes,_,_=native_batch(a.workspace,f"V43P3bP1-w{width}-old-{i:02d}",
                [raw],out,renderer_method="renderComplexHoldoutColorProbe")
            old=scenes["color-7"][:,:,3]
            if not np.array_equal(old,scenes["composite"][:,:,3]):
                raise ValueError("P1 single stroke old alpha mismatches composite")
            analysis=subset_result(old,actual_candidates[width],labels)
            analysis.update({
                "original_stroke_id":raw["strokeId"],
                "original_paint_array_index":item["original_paint_array_index"],
                "native_candidate_row_alpha24_score":item["native_candidate_row_alpha24_score"],
                "original_stroke_width":raw["width"],
                "original_stroke_points":raw["points"],
            })
            records.append(analysis)
            total_replays+=1
        replaceable=[r["original_stroke_id"] for r in records
                     if r["potential_replacement_ONLY"]]
        results[str(width)]={
            "selection":selection,
            "native_old_stroke_evidence":records,
            "potential_replacement_ids_SAMPLE_ONLY":replaceable,
            "potential_net_old_stroke_savings_MINUS_3_NEW_ONLY":len(replaceable)-3,
            "status":("NO_SAMPLE" if not selected else
                "POTENTIAL_SAVINGS_SAMPLE_ONLY" if len(replaceable)>3
                else "NO_NET_SAVINGS_SAMPLE"),
        }
    if not total_replays:
        raise ValueError("P1 NO_NATIVE_OLD_STROKE_SAMPLE")
    hashes={str(file.relative_to(a.output)).replace("\\","/"):sha(file)
            for file in a.output.rglob("*") if file.is_file()}
    report={
        "experiment":EXP,"source_sha256":SOURCE_SHA,
        "status":"REAL_NATIVE_SUBSET_SAMPLED_NOT_FULL_FILL",
        "p0_prior_negative_experiment":P0_EXP,
        "p3a3_artifact_id":14224453656,
        "p3a3_zip_sha256":P3A3_ARTIFACT_ZIP_SHA256,
        "p3a3_manifest_sha256":p3a3["report_linked_SHA256"],
        "native_original_strokes_rendered":total_replays,
        "widths":list(WIDTHS),"per_width":results,
        "report_linked_SHA256":hashes,
        "full_original_paint_strokes_removed":0,
        "new_oriented_paint_strokes_added_to_full_scene":0,
        "original_V44B_410_contour_strokes_modified":False,
        "game_exact_CHALK":None,"game_E4":"NOT_RUN",
        "full_image_A_B_visual":"NOT_RUN",
        "production_accepted":False,
    }
    (a.output/"report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n",
        encoding="utf-8")
    print(json.dumps({k:{"eligible":v["selection"]["eligible_positive_score"],
          "sampled":len(v["native_old_stroke_evidence"]),
          "potential_full_replacements":len(v["potential_replacement_ids_SAMPLE_ONLY"]),
          "status":v["status"]} for k,v in results.items()},indent=2))


if __name__=="__main__":
    main()

#!/usr/bin/env python3
"""S5-R7 exact original4x2 comparison; no native Egret or gameplay."""
from __future__ import annotations

import argparse
import io
import json
import time
from pathlib import Path
import numpy as np

import run_engine001_bpred_s5r3_dev_visual as original
import engine001_bpred_s5r4_offset_lanes as r45
import engine001_bpred_s5r6_boustrophedon_cells as r6
import engine001_bpred_s5r7_cell_marginal as r7

canonical, sha = original.canonical, original.sha
R3_TOTAL = (9248,9062,53300,15368)
R4_TOTAL = (17823,23756,120466,74318)
R5_TOTAL = (13858,23135,120016,60992)
R6_TOTAL = (2768,7196,157164,13921)
R4_NONWHITE = (1541,6622,110777,12458)
R5_NONWHITE = (2726,7501,110028,14877)
R6_NONWHITE = (2767,7196,157164,13921)


def independent(plan, arrays):
    h,w=arrays["game_index"].shape
    painted=np.zeros((h,w),bool)
    source_ids=arrays["paintable_id"]
    game=arrays["game_index"]
    rgba=arrays["original_rgba"]
    for stroke in plan["proposals"]:
        footprint=r7.source.swept_capsule_pixel_masks(
            stroke["points"],stroke["brush_value"],1.,1.,w,h)
        for x,y in footprint["potential_cells"]:
            if (source_ids[y,x] != stroke["paintable_id"] or
                    game[y,x] != stroke["color_index"] or rgba[y,x,3] != 255):
                raise ValueError("BLOCKED_S5R7_ORIGINAL_OWNER_MASK")
            painted[y,x]=True
    data={
        "total":int(painted.sum()),
        "nonwhite":int(np.count_nonzero(painted & (game!=6))),
        "white":int(np.count_nonzero(painted & (game==6))),
        "edge":int(np.count_nonzero(painted & arrays["source_edge"])),
        "protected":int(np.count_nonzero(painted & arrays["protected_original_dot"]))}
    if (data["total"] != plan["potential_covered_pixel_count"] or
            data["protected"] != plan["protected_dot_potential_covered"]):
        raise ValueError("BLOCKED_S5R7_MODEL_COUNT_DRIFT")
    return data


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    opts=p.parse_args()
    root,out=opts.root.resolve(),opts.output.resolve()
    if out.exists():
        raise ValueError("BLOCKED_S5R7_OUTPUT_ALREADY_EXISTS")
    out.mkdir(parents=True,exist_ok=False)
    palette,prov=original.palette.read_engine_palette(root/"gameEngine/main.min_653f95bc.js")
    if prov["engine_git_blob_sha1"]!=original.dev.ENGINE_BLOB:
        raise ValueError("BLOCKED_S5R7_ENGINE")
    report={
        "schema":"ENGINE001_BPRED_S5R7_ORIGINAL4X2_MODEL_ONLY_V1",
        "experiment":"ENGINE001_BPRED_S5R7_CELL_BALANCED_MARGINAL_COVERAGE_V1",
        "frozen_e0":"ENGINE001_BPRED_S5R7_CELL_BALANCED_MARGINAL_COVERAGE_PREREG_2026-11-23.md",
        "source_original_only":True,"drawing_mode":"normal","smooth":False,
        "engine_git_blob":original.dev.ENGINE_BLOB,
        "native_Egret":"NOT_RUN","exact_game_chalk":"NOT_RUN",
        "production_promotion":False,
        "web_methods":{
            "Boustrophedon_Cellular_Decomposition":"APPLIED_dual_axis_owner_cell_split_merge",
            "Euclidean_Distance_Transform":"APPLIED_source_clearance",
            "dynamic_marginal_geometric_set_cover":"PARTIAL_residual_gain_with_owner_deficit",
            "Medial_Axis":"NOT_IMPLEMENTED",
            "Contour_Parallel":"NOT_IMPLEMENTED",
            "Spiral":"NOT_IMPLEMENTED"},
        "sources":[]}
    for i,relative in enumerate(original.dev.SOURCES):
        input_bytes=(root/relative).read_bytes()
        rgba=original.original_io.decode_original(input_bytes)["rgba"]
        fresh=[]
        durations=[]
        first_arrays=None
        for repeat in range(2):
            t=time.perf_counter()
            ctr=original.ctr.build_ctr1(rgba,palette)
            manifest,packet=original.s46.export_quarantined(
                input_bytes,rgba,palette,ctr,relative,original.dev.ENGINE_BLOB)
            original.s46.verify_quarantined(manifest,packet,input_bytes)
            a=original.r3.build_from_verified_s46(manifest,packet,input_bytes)
            b=r45.build_from_verified_s46(manifest,packet,input_bytes)
            c=r45.build_from_verified_s46(
                manifest,packet,input_bytes,allocation="content_s5r5")
            d=r6.build_from_verified_s46(manifest,packet,input_bytes)
            e=r7.build_from_verified_s46(manifest,packet,input_bytes)
            with np.load(io.BytesIO(packet),allow_pickle=False) as z:
                arrays={k:z[k] for k in (
                    "original_rgba","paintable_id","game_index",
                    "protected_original_dot","source_edge")}
            for result in (a,b,c,d,e):
                original.verifier.validate_model(result,arrays)
                if (result["phase_trials"]["broad"]>1400 or
                        result["phase_trials"]["detail"]>600 or
                        result["phase_strokes"]["broad"]>80 or
                        result["phase_strokes"]["detail"]>120):
                    raise ValueError("BLOCKED_S5R7_FROZEN_BUDGET")
            measure=independent(e,arrays)
            if (measure["nonwhite"] != e["modeled_nonwhite6_covered"] or
                    measure["white"] != e["modeled_white6_covered"] or
                    measure["edge"] != e["modeled_source_edge_covered"]):
                raise ValueError("BLOCKED_S5R7_CONTENT_LEDGER")
            fresh.append((tuple(canonical(p) for p in (a,b,c,d,e)),
                          sha(manifest),measure))
            durations.append(round(time.perf_counter()-t,4))
            if i==0 and repeat==0:
                first_arrays=arrays
        if fresh[0]!=fresh[1]:
            raise ValueError("BLOCKED_S5R7_DOUBLE_FRESH_DETERMINISM")
        plans_raw,manifest_hash,metric=fresh[0]
        plans=[json.loads(raw) for raw in plans_raw]
        if ([x["potential_covered_pixel_count"] for x in plans[:4]] !=
                [R3_TOTAL[i],R4_TOTAL[i],R5_TOTAL[i],R6_TOTAL[i]]):
            raise ValueError("BLOCKED_S5R7_FROZEN_BASELINE_TOTAL")
        for k,reference in [(1,R4_NONWHITE[i]),(2,R5_NONWHITE[i]),
                            (3,R6_NONWHITE[i])]:
            actual=sum(x["modeled_new_potential_cells"] for x in plans[k]["proposals"]
                       if x["color_index"]!=6)
            if actual!=reference:
                raise ValueError("BLOCKED_S5R7_FROZEN_CONTENT_BASELINE")
        names=[f"{i:02d}_{key}.json" for key in ("R3","R4","R5","R6","R7")]
        for n,raw in zip(names,plans_raw):
            (out/n).write_bytes(raw)
        e=plans[4]
        minimum=max(R4_NONWHITE[i],R5_NONWHITE[i])
        row={
            "source":relative, "source_sha256":sha(input_bytes),
            "source_packet_manifest_sha256":manifest_hash,
            "models":{key:{"file":n,"sha256":sha(raw)} for key,n,raw
                      in zip(("r3","r4","r5","r6","r7"),names,plans_raw)},
            "r3_covered":R3_TOTAL[i],"r4_covered":R4_TOTAL[i],
            "r5_covered":R5_TOTAL[i],"r6_covered":R6_TOTAL[i],
            "r7_covered":metric["total"],"r7_metrics":metric,
            "r7_guaranteed":e["guaranteed_covered_pixel_count"],
            "r7_trials":e["phase_trials"],"r7_strokes":e["phase_strokes"],
            "r7_topology":e["topology"],"r7_scheduler":e["scheduler"],
            "frozen_nonwhite_minimum":minimum,
            "nonwhite_gate":metric["nonwhite"]>=minimum,
            "strict_10percent_gain":metric["nonwhite"]>=minimum*1.1,
            "total_r3_gate":metric["total"]>=R3_TOTAL[i],
            "protected120_gate":metric["protected"]>=120,
            "double_fresh_determinism":"PASS",
            "build_seconds":durations}
        if i==0:
            row["visual"]=original.visual_report(
                first_arrays,palette,e,out/"00_wV_S5R7_ACTUAL_MODEL_CELL_MARGINAL.png")
        report["sources"].append(row)
        print(json.dumps({
            "source":row["source"],"r7_covered":row["r7_covered"],
            "r7_metrics":metric,"nonwhite_gate":row["nonwhite_gate"],
            "strict_10percent_gain":row["strict_10percent_gain"],
            "scheduler":row["r7_scheduler"],
            "build_seconds":durations},sort_keys=True),flush=True)
    s=report["sources"]
    ok=(all(x["nonwhite_gate"] and x["total_r3_gate"] and x["protected120_gate"]
            for x in s) and sum(x["strict_10percent_gain"] for x in s)>=2)
    report["frozen_cell_fair_feasibility"]=(
        "PASS_CELL_FAIR_COVERAGE_FEASIBILITY" if ok
        else "FAIL_CELL_FAIR_COVERAGE_FEASIBILITY")
    (out/"00_S5R7_RESULTS.json").write_bytes(canonical(report))
    print("S5R7_FROZEN_FEASIBILITY",report["frozen_cell_fair_feasibility"],flush=True)


if __name__=="__main__":
    main()

#!/usr/bin/env python3
"""ENGINE-001: fresh original S4.6 -> independent R1/R2 source-only x2.

No old artwork input, no game coordinates/renderer/CHALK or executor output.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import time

import numpy as np

import engine001_bpred_s4r1_generic_source_maps as originals
import engine001_bpred_s4r1_ctr1_source_contour as ctr
import engine001_bpred_s4r1_s46_source_contract as s46
import engine001_bpred_s5r1_offline_candidates as r1
import engine001_bpred_s5r2_region_candidates as r2
import run_engine001_bpred_s4r1_ctr1_dev as dev
import run_engine001_b1r_p3b_engine128_adaptive32 as palette


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       indent=2, allow_nan=False) + "\n").encode("utf8")


def validate_model(result, arrays):
    game, ids, rgba = (arrays[k] for k in
        ("game_index", "paintable_id", "original_rgba"))
    h, w = game.shape
    if (result["drawing_mode"] != "normal" or result["smooth"] is not False
            or result["safe_to_execute"] is not False
            or result["admissible_for_gameplay"] is not False
            or result["source_owner_status"] != "MISSING"
            or result["native_calibration"] != "UNVERIFIED"):
        raise ValueError("BLOCKED_S5R2_FALSE_GAMEPLAY_ADMISSION")
    if result["trials"] > 2000 or result["stroke_count"] > 200:
        raise ValueError("BLOCKED_S5R2_BUDGET")
    if ((result["uncovered_potential_pixel_count"] > 0) !=
            (result["status"] == "PARTIAL")):
        raise ValueError("BLOCKED_S5R2_COVERAGE_STATUS")
    opaque = rgba[..., 3] == 255
    if result["visible_pixel_count"] != int(opaque.sum()):
        raise ValueError("BLOCKED_S5R2_VISIBLE_COUNT")
    footprint_union = np.zeros((h, w), bool)
    for p in result["proposals"]:
        if p["drawing_mode"] != "normal" or p["smooth"] is not False or p["safe_to_execute"] is not False:
            raise ValueError("BLOCKED_S5R2_STROKE_MODE")
        footprint = r2.swept_capsule_pixel_masks(
            p["points"],p["brush_value"],1.,1.,w,h)
        for x,y in footprint["potential_cells"]:
            if ids[y,x] != p["paintable_id"] or game[y,x] != p["color_index"] or not opaque[y,x]:
                raise ValueError("BLOCKED_S5R2_FOREIGN_MODEL_CELL")
            footprint_union[y,x] = True
    if (int(footprint_union.sum()) != result["potential_covered_pixel_count"]
            or int(np.count_nonzero(opaque & ~footprint_union)) !=
            result["uncovered_potential_pixel_count"]):
        raise ValueError("BLOCKED_S5R2_COVERAGE_LEDGER")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    root=args.root.resolve()
    out=args.output.resolve()
    out.mkdir(parents=True,exist_ok=True)
    game128, prov=palette.read_engine_palette(root/"gameEngine/main.min_653f95bc.js")
    if prov["engine_git_blob_sha1"] != dev.ENGINE_BLOB:
        raise ValueError("BLOCKED_S5R2_GAME_ENGINE_SHA")
    result={"schema":"ENGINE001_BPRED_S5R2_FOUR_ORIGINALS_V1",
            "original_source_only":True,"smooth":False,"drawing_mode":"normal",
            "R1_model_only":True,"R2_model_only":True,
            "native":"NOT_RUN","chalk":"NOT_RUN",
            "admissible_for_gameplay":False,
            "engine_git_blob_sha1":dev.ENGINE_BLOB,"sources":[]}
    for i,relative in enumerate(dev.SOURCES):
        source_bytes=(root/relative).read_bytes()
        rgba=originals.decode_original(source_bytes)["rgba"]
        pair=[]
        build_seconds=[]
        for repeat in range(2):
            start=time.perf_counter()
            source_maps=ctr.build_ctr1(rgba,game128)
            manifest,raw=s46.export_quarantined(source_bytes,rgba,game128,
                       source_maps,relative,dev.ENGINE_BLOB)
            s46.verify_quarantined(manifest,raw,source_bytes)
            baseline=r1.build_from_verified_s46(manifest,raw,source_bytes,
                       max_strokes=200,max_seed_trials=2000)
            candidate=r2.build_from_verified_s46(manifest,raw,source_bytes,
                       max_strokes=200,max_trials=2000)
            with np.load(io.BytesIO(raw),allow_pickle=False) as packet:
                validate_model(candidate,{k:packet[k] for k in
                    ("game_index","paintable_id","original_rgba")})
            pair.append((json_bytes(baseline),json_bytes(candidate),manifest))
            build_seconds.append(time.perf_counter()-start)
        if pair[0] != pair[1]:
            raise ValueError("BLOCKED_S5R2_FRESH_DOUBLE_BUILD_CHANGED")
        old,new,manifest=pair[0]
        old_name=f"{i:02d}_S5R1_BASELINE_ONLY.json"
        new_name=f"{i:02d}_S5R2_REGION_ONLY.json"
        (out/old_name).write_bytes(old)
        (out/new_name).write_bytes(new)
        a,b=json.loads(old),json.loads(new)
        enough=b["potential_covered_pixel_count"]>=a["potential_covered_pixel_count"]
        improvement=b["potential_covered_pixel_count"]>a["potential_covered_pixel_count"]
        result["sources"].append({
            "source":relative,"input_sha256":digest(source_bytes),
            "source_manifest_sha256":digest(manifest),
            "r1_output":old_name,"r1_sha256":digest(old),
            "r2_output":new_name,"r2_sha256":digest(new),
            "source_original_shape":b["source_shape"],
            "visible":b["visible_pixel_count"],
            "r1_covered":a["potential_covered_pixel_count"],
            "r2_covered":b["potential_covered_pixel_count"],
            "r2_guaranteed":b["guaranteed_covered_pixel_count"],
            "r2_protected_dots":b["protected_original_dot_count"],
            "r2_protected_touched":b["protected_dot_potential_covered"],
            "r2_region_total":b["regions_total"],
            "r2_regions_visited":b["regions_visited"],
            "r2_regions_not_visited":b["regions_not_visited"],
            "r2_strokes":b["stroke_count"],"r2_trials":b["trials"],
            "r2_status":b["status"],
            "not_worse_model_coverage":enough,
            "strict_model_coverage_gain":improvement,
            "double_original_fresh_determinism":"PASS",
            "build_plus_two_models_seconds":[round(x,4) for x in build_seconds],
        })
        print(json.dumps(result["sources"][-1],ensure_ascii=False,sort_keys=True),flush=True)
    records=result["sources"]
    result["feasibility_E0"] = ("PASS_MODEL_FEASIBILITY_ONLY"
        if all(row["not_worse_model_coverage"] for row in records)
        and sum(row["strict_model_coverage_gain"] for row in records)>=2
        else "FAIL_MODEL_FEASIBILITY")
    (out/"00_S5R2_RESULTS.json").write_bytes(json_bytes(result))
    print(json.dumps({"feasibility_E0":result["feasibility_E0"],
                      "sources":len(records)},sort_keys=True))


if __name__=="__main__":
    main()

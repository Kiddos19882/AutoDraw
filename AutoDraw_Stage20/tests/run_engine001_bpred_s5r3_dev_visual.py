#!/usr/bin/env python3
"""S5-R3 genuine source original×2 E2 and faithful ideal-brush PNG audit.

PNG panels are RENDERED FROM THE ACTUAL SOURCE AND ACCEPTED MODEL STROKES.
Not an AI-generated illustration and not native Egret raster/CHALK.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
import engine001_bpred_s4r1_generic_source_maps as original_io
import engine001_bpred_s4r1_ctr1_source_contour as ctr
import engine001_bpred_s4r1_s46_source_contract as s46
import engine001_bpred_s5r2b_two_ledger_candidates as r2b
import engine001_bpred_s5r3_clearance_paths as r3
import run_engine001_bpred_s5r2_dev as verifier
import run_engine001_bpred_s4r1_ctr1_dev as dev
import run_engine001_b1r_p3b_engine128_adaptive32 as palette

sha = verifier.digest
canonical = verifier.json_bytes
R2B_COVERED=(2826,3005,3705,3372)
R2B_DETAIL=(120,120,120,120)


def visual_report(arrays, palette128, r3plan, filepath):
    """Pixel-faithful IDEAL FOOTPRINT of actual accepted R3 strokes (not Egret)."""
    rgba=arrays["original_rgba"]
    idx=arrays["game_index"]
    ids=arrays["paintable_id"]
    h,w=idx.shape
    base=np.asarray(Image.fromarray(rgba,"RGBA").convert("RGB")).copy()
    visible=rgba[:,:,3]==255
    painted=np.full((h,w,3),255,dtype=np.uint8)
    potential=np.zeros((h,w),dtype=bool)
    guaranteed=np.zeros((h,w),dtype=bool)
    drawlines=Image.new("RGB",(w,h),(255,255,255))
    drawer=ImageDraw.Draw(drawlines)
    model_brush_hist={}
    for s in r3plan["proposals"]:
        brush=s["brush_value"]
        model_brush_hist[str(brush)]=model_brush_hist.get(str(brush),0)+1
        footprint=r3.source.swept_capsule_pixel_masks(
            s["points"],brush,1.,1.,w,h)
        color=np.asarray(palette128[int(s["color_index"])],dtype=np.uint8)
        for x,y in footprint["potential_cells"]:
            if ids[y,x]!=s["paintable_id"] or idx[y,x]!=s["color_index"] or not visible[y,x]:
                raise ValueError("BLOCKED_VISUAL_FOREIGN_OWNER")
            painted[y,x]=color
            potential[y,x]=True
        for x,y in footprint["guaranteed_cells"]:
            guaranteed[y,x]=True
        coords=[(int(round(a)),int(round(b))) for a,b in s["points"]]
        hue=(33,99,198) if s["phase"]=="broad" else (222,113,15)
        drawer.line(coords,fill=hue,width=1)
        for x,y in (coords[0],coords[-1]):
            drawer.ellipse((x-1,y-1,x+1,y+1),fill=hue)
    if int(np.count_nonzero(potential))!=r3plan["potential_covered_pixel_count"]:
        raise ValueError("BLOCKED_VISUAL_UNION_MISMATCH")
    if int(np.count_nonzero(guaranteed))!=r3plan["guaranteed_covered_pixel_count"]:
        raise ValueError("BLOCKED_VISUAL_GUARANTEED_MISMATCH")
    # Coverage audit: green = modeled potential ink; red = original residual.
    residual=np.full((h,w,3),255,dtype=np.uint8)
    residual[visible & ~potential]=[217,68,73]
    residual[visible & potential]=[66,163,106]
    # 2x2 source-sized panels; labels are outside actual input pixels.
    panel_w= max(w,300)
    label_h=27
    image=Image.new("RGB",(panel_w*2,(h+label_h)*2),(240,242,245))
    draw=ImageDraw.Draw(image)
    samples=[
        (base, "INPUT: genuine RGB original"),
        (painted, "MODEL: ideal capsule potential color pixels"),
        (np.asarray(drawlines), "PATHS: broad=blue, detail=orange"),
        (residual, "MASK: covered=green, residual=red"),
    ]
    for n,(data,title) in enumerate(samples):
        x=(n%2)*panel_w
        y=(n//2)*(h+label_h)
        draw.text((x+6,y+6),title,fill=(16,22,31))
        image.paste(Image.fromarray(data,"RGB"),(x,y+label_h))
    image.save(filepath,format="PNG",optimize=True)
    return {"preview_file":filepath.name,"preview_sha256":sha(filepath.read_bytes()),
            "preview_kind":"ACTUAL_ORIGINAL_PLUS_IDEAL_GEOMETRY_NOT_NATIVE",
            "brush_histogram":model_brush_hist,
            "potential_px":int(potential.sum()),
            "guaranteed_px":int(guaranteed.sum()),
            "residual_px":int(np.count_nonzero(visible & ~potential))}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    root,out=args.root.resolve(),args.output.resolve()
    out.mkdir(parents=True,exist_ok=True)
    game128,prov=palette.read_engine_palette(root/"gameEngine/main.min_653f95bc.js")
    if prov["engine_git_blob_sha1"]!=dev.ENGINE_BLOB:
        raise ValueError("BLOCKED_S5R3_ENGINE")
    summary={"schema":"ENGINE001_BPRED_S5R3_4DEV_VISUAL_V1",
             "source_original_only":True,"smooth":False,
             "drawing_mode":"normal","native_Egret":"NOT_RUN",
             "exact_game_chalk":"NOT_RUN","admissible_for_gameplay":False,
             "sources":[]}
    for i,relative in enumerate(dev.SOURCES):
        input_bytes=(root/relative).read_bytes()
        rgba=original_io.decode_original(input_bytes)["rgba"]
        records=[]
        seconds=[]
        first_arrays=None
        for repeat in range(2):
            start=time.perf_counter()
            maps=ctr.build_ctr1(rgba,game128)
            manifest,raw=s46.export_quarantined(input_bytes,rgba,game128,
                                      maps,relative,dev.ENGINE_BLOB)
            s46.verify_quarantined(manifest,raw,input_bytes)
            baseline=r2b.build_from_verified_s46(manifest,raw,input_bytes)
            candidate=r3.build_from_verified_s46(manifest,raw,input_bytes)
            with np.load(io.BytesIO(raw),allow_pickle=False) as data:
                values={k:data[k] for k in
                        ("original_rgba","paintable_id","game_index","protected_original_dot")}
            verifier.validate_model(candidate,values)
            if (candidate["phase_trials"]["broad"]>1400 or
                candidate["phase_trials"]["detail"]>600 or
                candidate["phase_strokes"]["broad"]>80 or
                candidate["phase_strokes"]["detail"]>120):
                raise ValueError("BLOCKED_R3_PHASE_BUDGET")
            records.append((canonical(baseline),canonical(candidate),manifest))
            if i==0 and repeat==0:
                first_arrays=values
            seconds.append(round(time.perf_counter()-start,4))
        if records[0]!=records[1]:
            raise ValueError("BLOCKED_R3_FRESH_REBUILD_DETERMINISM")
        old,new,manifest=records[0]
        a,b=json.loads(old),json.loads(new)
        baseline_name=f"{i:02d}_R2B_BASELINE.json"
        candidate_name=f"{i:02d}_R3_PATHS.json"
        (out/baseline_name).write_bytes(old)
        (out/candidate_name).write_bytes(new)
        row={"source":relative,"input_sha256":sha(input_bytes),
             "source_manifest_sha256":sha(manifest),
             "r2b_file":baseline_name,"r2b_sha256":sha(old),
             "r3_file":candidate_name,"r3_sha256":sha(new),
             "r2b_covered":a["potential_covered_pixel_count"],
             "r3_covered":b["potential_covered_pixel_count"],
             "r3_guaranteed":b["guaranteed_covered_pixel_count"],
             "r3_uncovered":b["uncovered_potential_pixel_count"],
             "r3_protected_touched":b["protected_dot_potential_covered"],
             "r3_regions_feasible_corridors":b["regions_feasible_corridors"],
             "r3_broad_strokes":b["phase_strokes"]["broad"],
             "r3_detail_strokes":b["phase_strokes"]["detail"],
             "r3_trials":b["trials"],
             "coverage_not_worse":b["potential_covered_pixel_count"]>=R2B_COVERED[i],
             "coverage_strict_gain":b["potential_covered_pixel_count"]>R2B_COVERED[i],
             "protected_gate":b["protected_dot_potential_covered"]>=R2B_DETAIL[i],
             "double_fresh_determinism":"PASS","wall_seconds":seconds}
        if i==0:
            row["visual"]=visual_report(
                first_arrays,game128,b,out/"00_wV_S5R3_ACTUAL_MODEL_BRUSH_VISUAL.png")
        summary["sources"].append(row)
        print(json.dumps(row,sort_keys=True,ensure_ascii=False),flush=True)
    entries=summary["sources"]
    gate=(all(x["coverage_not_worse"] and x["protected_gate"] for x in entries)
          and sum(x["coverage_strict_gain"] for x in entries)>=2)
    summary["frozen_model_feasibility"]="PASS_MODEL_FEASIBILITY_ONLY" if gate else "FAIL_MODEL_FEASIBILITY"
    (out/"00_S5R3_RESULTS.json").write_bytes(canonical(summary))
    print(json.dumps({"frozen_model_feasibility":summary["frozen_model_feasibility"],
                      "originals":len(entries)},sort_keys=True))


if __name__=="__main__":
    main()

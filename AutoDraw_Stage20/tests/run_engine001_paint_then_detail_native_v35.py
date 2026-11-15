#!/usr/bin/env python3
"""ENGINE-001 V35 native pilot: genuine Egret paint first, V18-B details last.

This never executes game Stage6 or measures run-bound CHALK. No modeled brush.
"""
from __future__ import annotations
import argparse,hashlib,json,math,platform,sys
from pathlib import Path
import numpy as np
from PIL import Image
from engine001_paint_then_detail_v35 import build_layered_native_plan,native_strokes
from run_engine001_native_warm_color_v34 import (
    SOURCE_SHA,sha,png_pixel_exact_replay,warm_mask,mae)
from run_engine001_native_v29_brush2_v33 import logical_crop
from run_engine001_complex_holdout_v5 import native_batch
from run_engine001_visual_roi_palette_v28 import prepare_source,sheet

EXP="ENGINE001_PAINT_THEN_DETAIL_V35_NATIVE_PILOT_1"
V34R_SHA="93b46223f5525b02def1631de8b49af4e1ddc0c799e5ec28224143d94fac0be2"
V18_B_SHA="752dbc5ff55e90b0d38f492fadfde9be8811b70ebc66bce4999f716c4a86ed57"
V18_RGB=[49,38,43]
DETAIL_INDEX=100

def unpack_v18(rows):
    if not isinstance(rows,list) or len(rows)!=410 or sum(
            len(x["logical_points"]) for x in rows)!=1792:
        raise ValueError("V35 frozen V18-B contours changed")
    out=[]
    seen=set()
    for row in rows:
        if row["id"] in seen: raise ValueError("V35 duplicated frozen contour ID")
        seen.add(row["id"])
        if row["color_rgb"]!=V18_RGB or row["brush_width_parameter"]!=1:
            raise ValueError("V35 frozen V18 stroke color/width changed")
        pts=[{"x":float(x),"y":float(y)} for x,y in row["logical_points"]]
        out.append({"strokeId":"detail-"+row["id"],"width":1,
                    "colorRgb":0x31262B,"colorIndex":DETAIL_INDEX,"points":pts,
                    "v18_source_id":row["id"]})
    return out

def choose_salient(rows):
    """Frozen V35 C rule: upper y<125 OR logical polyline length>=15."""
    return [
        item for item in rows
        if any(y<125 for x,y in item["logical_points"]) or
        sum(math.hypot(x2-x1,y2-y1) for ((x1,y1),(x2,y2)) in
            zip(item["logical_points"],item["logical_points"][1:]))>=15.0
    ]

def verify_frozen(v34r, v18):
    report=json.loads((v34r/"report.json").read_text(encoding="utf-8"))
    if report["experiment"]!="ENGINE001_NATIVE_WARM_COLOR_V34R" or (
        report["strokes"],report["synthetic_vertices_NOT_CHALK"])!=(1945,3890):
        raise ValueError("V35 V34R native baseline identity or counts drift")
    if not report["v33_native_pixel_rgba_exact_replay"] or not report[
        "native_alpha_identical"]:
        raise ValueError("V35 V34R native source incomplete")
    for p,d in report["derived_sha256"].items():
        if sha(v34r/p)!=d:raise ValueError("V35 V34R artifact hash drift "+p)
    if sha(v18/"B-paths.json")!=V18_B_SHA:
        raise ValueError("V35 frozen V18-B path hash drift")
    v18report=json.loads((v18/"report.json").read_text(encoding="utf-8"))
    if (v18report["source_sha256"]!=SOURCE_SHA or
            v18report["B"]["paths"]!=410 or v18report["B"]["vertices"]!=1792):
        raise ValueError("V35 V18-B frozen report drift")
    if v18report["artifacts_sha256"]["B-paths.json"]!=V18_B_SHA:
        raise ValueError("V35 V18-B manifest drift")
    fill=json.loads((v34r/"V34-B-strokes.json").read_text(encoding="utf-8"))
    rows=fill["strokes"]
    if len(rows)!=1945 or sum(len(s["points"]) for s in rows)!=3890:
        raise ValueError("V35 frozen native color plan count drift")
    for s in rows:
        if s["width"]!=2 or s["colorIndex"] not in (4,5,6,7):
            raise ValueError("V35 frozen fill width/ownership changed")
    paths=json.loads((v18/"B-paths.json").read_text(encoding="utf-8"))
    return rows,paths

def main():
    p=argparse.ArgumentParser()
    for n in ("workspace","source","v34r-archive","v18-archive","output"):
        p.add_argument("--"+n,required=True,type=Path)
    a=p.parse_args()
    if a.output.exists() and any(a.output.iterdir()):
        raise ValueError("V35 no overwrite of previous evidence")
    if sha(a.source)!=SOURCE_SHA:raise ValueError("V35 original source hash drift")
    original,_=prepare_source(a.source)
    color,paths=verify_frozen(a.v34r_archive,a.v18_archive)
    all_detail=unpack_v18(paths)
    salient=choose_salient(paths)
    few_detail=unpack_v18(salient) if len(salient)==410 else [
        row for row in all_detail if row["v18_source_id"] in
            {p["id"] for p in salient}]
    if len(few_detail)!=297 or sum(len(r["points"]) for r in few_detail)!=1379:
        raise ValueError("V35 frozen C selection count drift")
    if len({s["strokeId"] for s in few_detail})!=len(few_detail):
        raise ValueError("V35 duplicate C IDs")
    plans={
        "A":build_layered_native_plan(color,[]),
        "B":build_layered_native_plan(color,all_detail),
        "C":build_layered_native_plan(color,few_detail),
    }
    expected={"A":(1945,3890),"B":(2355,5682),"C":(2242,5269)}
    for key,plan in plans.items():
        if (len(plan["strokes"]),plan["synthetic_vertices_NOT_CHALK"])!=expected[key]:
            raise ValueError("V35 frozen "+key+" count drift")
    out=a.output;out.mkdir(parents=True)
    (out/"plans.json").write_text(json.dumps(plans,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    warm=warm_mask(original)
    score={};cropped={}
    for key,plan in plans.items():
        scene=out/key;scene.mkdir()
        raw,scenes,manifest=native_batch(a.workspace,"V35-"+key,native_strokes(plan),scene)
        if key=="A":
            replay=png_pixel_exact_replay(a.v34r_archive/"V34-B-composite.png",
                                          scene/"V35-A-composite.png")
            if not replay["pixel_rgba_exact"]:
                raise ValueError("V35 native A differs from V34R actual B fill")
        else:
            replay=None
        crop=logical_crop(raw["composite"])
        crop.save(out/("V35-"+key+"-roi.png"))
        cropped[key]=crop
        score[key]={
            "strokes":len(plan["strokes"]),
            "synthetic_vertices_NOT_CHALK":plan["synthetic_vertices_NOT_CHALK"],
            "paint_strokes":plan["paint_strokes"],"detail_strokes":plan["detail_strokes"],
            "source_RGB_MAE":mae(crop,original),
            "warm_RGB_MAE":mae(crop,original,warm),
            "native_composite_alpha24_pixels":int(np.count_nonzero(raw["composite"][:,:,3]>=24)),
            "scene_metadata":scenes,"replay":replay}
    sheet([original,cropped["A"],cropped["B"],cropped["C"]],
          ["Original RGB","V34R fill only A","V35 fill + all B","V35 fill + selected C"],
          out/"comparison-full.png")
    sheet([original,cropped["A"],cropped["B"],cropped["C"]],
          ["Original","Fill only","All contours last","Selected contours last"],
          out/"comparison-faces.png",top=True)
    hashes={str(p.relative_to(out)).replace("\\","/"):sha(p)
            for p in out.rglob("*") if p.is_file()}
    report={"experiment":EXP,"status":"ACTUAL_ARCHIVED_EGRET_E3_NOT_GAME",
            "original_source_sha":SOURCE_SHA,
            "frozen_V18_B_path_SHA":V18_B_SHA,
            "native_V34R_reference":"CI43740639321 artifact14171839402",
            "native_A_replay_V34R_pixel_exact":True,
            "warm_source_pixels":int(np.count_nonzero(warm)),
            "variants":score,"C_selected_source_ids":[r["id"] for r in salient],
            "real_native_renderer":True,"native_alpha_threshold":24,
            "source_class_color_quality_ACCEPTED":False,
            "game_CHALK_NOT_MEASURED":True,"not_tested":["live E4","E5","exact CHALK",
                "per-color >=99% complete","native 3 logical px leakage for details"],
            "artifacts_sha256":hashes,
            "versions":{"Python":platform.python_version(),"numpy":np.__version__}}
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:{q:v[q] for q in ("strokes","synthetic_vertices_NOT_CHALK",
        "source_RGB_MAE","warm_RGB_MAE")} for k,v in score.items()},indent=2))

if __name__=="__main__":
    main()

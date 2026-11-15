#!/usr/bin/env python3
"""V33: unchanged V29 color plan rendered by actual game Egret normal width2."""
from __future__ import annotations
import argparse,hashlib,json,platform,sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"source"/"preparation"))
from run_engine001_visual_roi_palette_v28 import prepare_source,quantize_case,sheet,sha
from run_engine001_complex_holdout_v5 import native_batch,read_webgl_result
from run_engine001_two_icon_mask_probe import compare
from run_engine001_painted_frontier_v2 import measure_halo

FROZEN_PLAN_SHA="e3dfb8b36831c74283b21ed694335e93d262e383938a9f1fb38222c7939d57cd"
FROZEN_PREVIEW_SHA="4cf405fc25a91f6e9b6bfc0be284d628f2681586de8d5a7332fea002a6264c91"
SOURCE_SHA="07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
WIDTH=2
ALPHA=(24,128)
ROI_X=155
SCALE=3

def translate(plan,indexes,palette):
    if len(plan["strokes"])!=1945 or (
       plan["summary"]["point_quota_estimate"]["estimated_point_count"]!=4498):
        raise ValueError("Frozen V29 plan counts/forecast changed")
    rgb_by_idx={int(entry["index"]):list(entry["rgb"]) for entry in palette}
    converted=[]
    zero=0
    for i,item in enumerate(plan["strokes"]):
        path=item["points"]
        if len(path)!=2:raise ValueError("Unexpected V29 route length")
        if item["closed"]:raise ValueError("Unexpected closed V29 stroke")
        color=item["color"]
        index=int(color["palette_index"])
        rgb=rgb_by_idx[index]
        if color["rgb"]!=rgb:raise ValueError("V29 palette identity differs from V28 original")
        pts=[{"x":float(p["x"]),"y":float(p["y"])} for p in path]
        if pts[0]==pts[1]:
            zero+=1
            pts[1]["x"]+=0.25
        if any(not (155<=p["x"]<305 and 0<=p["y"]<240) for p in pts):
            raise ValueError("V33 endpoint outside frozen source ROI")
        converted.append({
            "strokeId":f"icon-{i}","width":WIDTH,
            "colorRgb":rgb[0]*65536+rgb[1]*256+rgb[2],
            "colorIndex":index,"points":pts,
            "sourceStrokeName":item["name"]})
    if zero!=447:raise ValueError("V29 zero-length point count changed")
    if sum(len(x["points"]) for x in converted)!=3890:
        raise ValueError("V33 synthetic accepted point cap mismatch")
    return converted,zero

def logical_crop(rgba:np.ndarray)->Image.Image:
    if rgba.shape!=(720,1380,4):
        raise ValueError("Actual Egret native output shape mismatch")
    image=Image.fromarray(rgba,"RGBA")
    white=Image.new("RGBA",image.size,(255,255,255,255))
    merged=Image.alpha_composite(white,image).convert("RGB")
    return merged.resize((460,240),Image.Resampling.LANCZOS).crop((155,0,305,240))

def main():
    p=argparse.ArgumentParser()
    for name in ("workspace","source","v29-archive","output"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    out=a.output
    if out.exists() and any(out.iterdir()):raise ValueError("No overwrite V33 evidence")
    source_roi,canvas=prepare_source(a.source)
    if sha(a.source)!=SOURCE_SHA:raise ValueError("Source SHA drift")
    idx,pal,skipped=quantize_case(source_roi,canvas,8,False,True)
    if skipped!=[0,1,2,3]:raise ValueError("V28 source palette skip control differs")
    archive=a.v29_archive
    frozen_plan=archive/"budgeted-plan.json"
    frozen_preview=archive/"budgeted-roi.png"
    if sha(frozen_plan)!=FROZEN_PLAN_SHA or sha(frozen_preview)!=FROZEN_PREVIEW_SHA:
        raise ValueError("Frozen V29 original plan/preview SHA mismatch")
    plan=json.loads(frozen_plan.read_text())
    if [k["rgb"] for k in plan["palette"]] != [c["rgb"] for c in pal]:
        raise ValueError("Actual original Stage20 V29 palette differs")
    strokes,zeros=translate(plan,idx,pal)
    out.mkdir(exist_ok=True,parents=True)
    (out/"native-width2-strokes.json").write_text(json.dumps({
        "experiment":"ENGINE001_NATIVE_V29_BRUSH2_V33",
        "source_V29_plan_sha256":FROZEN_PLAN_SHA,
        "fixed_zero_length_shim_dx":0.25,"zero_length_count":zeros,
        "synthetic_accepted_points_not_chalk":3890,
        "strokes":strokes},ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    # Reuse actual archived Egret BoardPane/WebGL (not PIL/OpenCV/rectangle).
    raw,scenes,manifest=native_batch(a.workspace,"V33",strokes,out)
    targets=np.repeat(np.repeat(idx,3,axis=0),3,axis=1)
    metrics={}
    for color in sorted({s["colorIndex"] for s in strokes}):
        mask=targets==color
        rgba=raw[f"color-{color}"]
        metrics[str(color)]={
          "source_target_pixels":int(np.count_nonzero(mask)),
          "strokes":sum(s["colorIndex"]==color for s in strokes)}
        for threshold in ALPHA:
            painted=rgba[:,:,3]>=threshold
            c=compare(mask,painted)
            halo=measure_halo(mask,painted)
            metrics[str(color)][str(threshold)]={
                "native_target_recall":c["coverage"],
                "painted_native_pixels":int(np.count_nonzero(painted)),
                "foreign_palette_pixel_count":int(np.count_nonzero(painted&(targets>=0)&(targets!=color))),
                "outside_artwork_roi_pixels":int(np.count_nonzero(painted[:,:155]))+
                                             int(np.count_nonzero(painted[:,305*3:])),
                "inside_3_logical_halo":halo["all_leakage_in_3logical_halo"],
                "target_diagnostic":c}
    all_target=targets>=0
    native_union=np.zeros(all_target.shape,bool)
    for color in sorted({s["colorIndex"] for s in strokes}):
        native_union |= (raw[f"color-{color}"][:,:,3]>=24)
    silhouette=compare(all_target,native_union)
    main=raw["composite"]
    native_roi=logical_crop(main)
    with Image.open(frozen_preview) as image:
        preview_roi=image.convert("RGB").copy()
    source_roi.save(out/"original-roi.png")
    preview_roi.save(out/"V29-Stage20-model-roi.png")
    native_roi.save(out/"V33-real-Egret-brush2-roi.png")
    sheet([source_roi,preview_roi,native_roi],
          ["Original RGB","V29 Stage20 preview","V33 actual Egret width2"],
          out/"comparison-full.png")
    sheet([source_roi,preview_roi,native_roi],
          ["Original RGB","V29 thin preview","V33 game brush2"],
          out/"comparison-faces.png",top=True)
    relative_hashes={str(file.relative_to(out)).replace("\\","/"):sha(file)
                     for file in out.rglob("*") if file.is_file()}
    report={
        "experiment":"ENGINE001_NATIVE_V29_BRUSH2_V33",
        "status":"REAL_ARCHIVED_EGRET_E3_NOT_GAME",
        "source_sha256":SOURCE_SHA,
        "frozen_V29_plan_sha256":FROZEN_PLAN_SHA,
        "frozen_V29_preview_sha256":FROZEN_PREVIEW_SHA,
        "board":{"logical":[460,240],"native":[1380,720],"source_roi":[155,0,150,240]},
        "real_lineStyle_width":WIDTH,"synthetic_strokes":1945,
        "synthetic_vertices_not_CHALK":3890,"zero_length_dx_shim_count":zeros,
        "unchanged_original_V29_estimated_game_points_NOT_CHALK":4498,
        "native_quantized_target_silhouette":silhouette,
        "native_per_color":metrics,
        "native_renderer":{k:{"strokeCount":v.get("strokeCount"),
                             "syntheticAcceptedVerticesNotChalk":v.get("syntheticAcceptedVerticesNotChalk"),
                             "webglDrawCalls":v.get("webglDrawCalls")}
                           for k,v in scenes.items()},
        "browser_helper":manifest,
        "derived_sha256":relative_hashes,
        "candidate_modifications":"same V29 paths/colors, width2 for all, second endpoint x+0.25 only 447 zero-length strokes",
        "not_tested":["live E4","exact run-bound CHALK","full fidelity original RGB",
                      "3px game leakage","native game >=99% full color acceptance","E5"],
        "versions":{"python":platform.python_version(),"numpy":np.__version__,
                    "Pillow":Image.__version__}}
    (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"strokes":1945,"synthetic_points":3890,
        "source_target_silhouette_coverage":silhouette["coverage"],
        "per_color_coverage_alpha24":{k:round(v["24"]["native_target_recall"],5) for k,v in metrics.items()}},indent=2))

if __name__=="__main__":main()

#!/usr/bin/env python3
"""V30: existing experimental adaptive fill plans, conservative footprint MODEL only."""
import argparse,json,platform,sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"source"/"preparation"))
from run_engine001_visual_roi_palette_v28 import prepare_source,quantize_case,sha,sheet
from color_scanline import build_color_scanline_plan,render_color_scanline_preview
from interior_fill_planner import build_interior_fill_plan
from outline_first_fill_planner import build_outline_first_fill_plan
from brush_footprint_geometry import footprint_pixel_bounds

def validate_and_model(plan,source_indexes,colors):
    if plan["canvas"]!={"width":150,"height":240}:
        raise ValueError("V30 expected exact ROI geometry")
    if plan["brush_configuration"]["automatic_execution_allowed"] is not False or (
        plan["summary"]["ready_for_automatic_execution"] is not False):
        raise ValueError("V30 execution flag not fail-closed")
    out=np.full((240,150,3),255,np.uint8)
    filled=np.full((240,150),-1,np.int32)
    overlap=0;counts={}
    for index,stroke in enumerate(plan["strokes"]):
        color=int(stroke["color_index"])
        if not 0<=color<len(colors) or not stroke["safe_for_color_map"] or stroke["safe_to_execute"]:
            raise ValueError("V30 unsafe stroke identity "+str(index))
        points=stroke["points"]
        if len(points)!=2 or points[0]["y"]!=points[1]["y"]:
            raise ValueError("V30 nonhorizontal stroke")
        a,b=points
        if not (0<=a["x"]<=b["x"]<150 and 0<=a["y"]<240):
            raise ValueError("V30 stroke points outside bounded ROI")
        brush=int(stroke["brush_value"])
        if not 1<=brush<=20:
            raise ValueError("V30 nonfrozen brush range")
        bounds=footprint_pixel_bounds(float(a["x"]),float(b["x"]),float(a["y"]),
                                      brush,1.0,1.0,150,240)
        if bounds is None:raise ValueError("V30 no footprint "+str(index))
        x1,x2,y1,y2=bounds
        if not np.all(source_indexes[y1:y2+1,x1:x2+1]==color):
            raise ValueError("V30 owner violation "+str(index))
        region=filled[y1:y2+1,x1:x2+1]
        overlap+=int(np.count_nonzero(region==color))
        if np.any((region!=-1)&(region!=color)):
            raise ValueError("V30 cross-color overlap "+str(index))
        region[:]=color
        out[y1:y2+1,x1:x2+1]=colors[color]["rgb"]
        counts[brush]=counts.get(brush,0)+1
    visible=source_indexes>=0
    missing=int(np.count_nonzero(visible & (filled<0)))
    mismatch=int(np.count_nonzero(visible & (filled>=0) & (filled!=source_indexes)))
    leakage=int(np.count_nonzero((~visible)&(filled>=0)))
    if mismatch or leakage:raise ValueError("V30 model mispaint or transparency leak")
    result={"stroke_count":len(plan["strokes"]),"endpoint_count_not_game_points":2*len(plan["strokes"]),
            "covered_visible_model_pixels":int(np.count_nonzero(visible & (filled>=0))),
            "target_visible_pixels":int(np.count_nonzero(visible)),
            "missing_model_pixels":missing,"owner_mismatch_model_pixels":mismatch,
            "outside_target_model_pixels":leakage,"overdraw_same_class_cells":overlap,
            "brush_histogram":{str(k):v for k,v in sorted(counts.items())},
            "summary":plan["summary"],"automatic_execution_allowed":False}
    return Image.fromarray(out),result

def run(source,frozen_d,frozen_v29,output):
    output=Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("V30 cannot overwrite evidence")
    roi,canvas=prepare_source(source)
    idx,colors,skipped=quantize_case(roi,canvas,8,False,True)
    if skipped!=[0,1,2,3]:raise ValueError("V28 palette drift")
    native=build_color_scanline_plan(idx,colors,source_name="wV6VeZI9S1Y.png")
    if len(native["strokes"])!=6373 or native["summary"]["point_quota_estimate"]["estimated_point_count"]!=13258:
        raise ValueError("Frozen V28-D source baseline changed")
    old=render_color_scanline_preview(native,max_dimension=1600)
    white=Image.new("RGB",(460,240),"white");white.paste(old,(0,0),old)
    v28=white.crop((155,0,305,240))
    with Image.open(frozen_d) as image:
        expected=image.convert("RGB")
    if expected.size!=(150,240) or not np.array_equal(np.asarray(expected),np.asarray(v28)):
        raise ValueError("V28-D authentic PNG mismatch")
    with Image.open(frozen_v29) as image:
        v29=image.convert("RGB")
    if v29.size!=(150,240):
        raise ValueError("V29 input reference dimension")
    # Data-only crop to the true source ROI; does not rescale or alter class labels.
    source_classes=idx[:,155:305].copy()
    output.mkdir(parents=True,exist_ok=True)
    results={};pictures=[]
    for name,builder in (("interior",build_interior_fill_plan),
                         ("outline-first",build_outline_first_fill_plan)):
        plan=builder(source_classes,max_brush_value=20,min_brush_value=2,
                     brush_scale_x=1.0,brush_scale_y=1.0,fallback_merge_gap_px=3)
        model,metrics=validate_and_model(plan,source_classes,colors)
        metrics["source_rgb_mae_model_not_native"]=round(float(
            np.abs(np.asarray(model,dtype=np.int16)-np.asarray(roi,dtype=np.int16)).mean()),4)
        model.save(output/(name+"-MODEL-roi.png"))
        (output/(name+"-nonexecuting-plan.json")).write_text(
            json.dumps(plan,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf8")
        pictures.append(model)
        results[name]=metrics
    roi.save(output/"original-source-roi.png")
    v28.save(output/"frozen-V28-D-roi.png")
    v29.save(output/"frozen-V29-roi.png")
    names=["Original","V28-D native Stage20","V29 row step 2",
           "V30 INTERIOR model","V30 OUTLINE model"]
    sheet([roi,v28,v29]+pictures,names,output/"comparison-full.png")
    sheet([roi,v28,v29]+pictures,names,output/"comparison-faces.png",top=True)
    report={"experiment":"ENGINE001_VISUAL_ADAPTIVE_FILL_V30",
            "status":"EXPERIMENTAL_MODEL_ONLY_NOT_GAME",
            "source_sha256":sha(source),"frozen_V28_D_png_sha256":sha(frozen_d),
            "frozen_V29_roi_png_sha256":sha(frozen_v29),
            "brush_footprint_model":"conservative_axis_aligned_rectangle",
            "planner_defaults":{"max_brush_value":20,"min_brush_value":2,
                                "brush_scale_x":1.0,"brush_scale_y":1.0,
                                "fallback_merge_gap_px":3},
            "modes":results,"not_tested":["native Egret game painting","exact CHALK",
                  "stage6 execution","live <=3px leakage","live >=99% fill","E5"],
            "production_modified":False,
            "versions":{"python":platform.python_version(),"numpy":np.__version__,
                        "pillow":Image.__version__}}
    report["derived_sha256"]={f.name:sha(f) for f in sorted(output.iterdir()) if f.is_file()}
    (output/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({k:{x:v[x] for x in ("stroke_count","covered_visible_model_pixels",
                                          "missing_model_pixels","source_rgb_mae_model_not_native")}
                      for k,v in results.items()},indent=2))
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for n in ("source","frozen-d","frozen-v29","output"):p.add_argument("--"+n,required=True,type=Path)
    a=p.parse_args()
    run(a.source,a.frozen_d,a.frozen_v29,a.output)

#!/usr/bin/env python3
"""V29 existing Stage20 budget-aware color optimization, on frozen V28-D only."""
import argparse,hashlib,json,platform,sys
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/"source"/"preparation"))
from run_engine001_visual_roi_palette_v28 import prepare_source,quantize_case,sha,sheet
from color_scanline import (build_color_scanline_plan,render_color_scanline_preview,
                            validate_color_scanline_plan)
from paint_budget_optimizer import fit_result_to_paint_budget
from palette_quantization import PaletteQuantizationResult

FROZEN_STROKES=6373
FROZEN_EST_POINTS=13258
SOURCE_SHA="07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"

def preview_for(plan):
    validate_color_scanline_plan(plan)
    rendered=render_color_scanline_preview(plan,max_dimension=1600)
    if rendered.size!=(460,240):raise ValueError("Native plan dimensions changed")
    arr=np.asarray(rendered.convert("RGBA"))
    if np.any(arr[:,:155,3]>0) or np.any(arr[:,305:,3]>0):
        yy,xx=np.nonzero(np.r_[arr[:,:155,3].flatten(),arr[:,305:,3].flatten()])
        raise ValueError("V29 actual native preview crosses frozen source ROI")
    white=Image.new("RGB",(460,240),"white")
    white.paste(rendered,(0,0),rendered)
    return rendered,white.crop((155,0,305,240)),int(np.count_nonzero(arr[:,155:305,3]))

def do_run(source,frozen_v28,output):
    output=Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("V29 evidence output exists, refusing overwrite")
    roi,canvas=prepare_source(source)
    if sha(source)!=SOURCE_SHA:raise ValueError("Frozen source mismatch")
    indexes,colors,skipped=quantize_case(roi,canvas,8,False,True)
    if skipped!=[0,1,2,3]:
        raise ValueError("V28-D near-white class population changed")
    baseline=build_color_scanline_plan(indexes,colors,row_step_px=1,row_offset_px=0,
                                       source_name="wV6VeZI9S1Y.png")
    prior=baseline["summary"]["point_quota_estimate"]["estimated_point_count"]
    if len(baseline["strokes"])!=FROZEN_STROKES or prior!=FROZEN_EST_POINTS:
        raise ValueError("Frozen V28-D baseline geometry/point model mismatch")
    orig_alpha,orig_crop,orig_alpha_count=preview_for(baseline)
    with Image.open(frozen_v28) as img:
        prior_roi=img.convert("RGB")
    if prior_roi.size!=(150,240) or not np.array_equal(np.asarray(prior_roi),np.asarray(orig_crop)):
        raise ValueError("V29 baseline color preview differs from authentic V28-D")
    result=PaletteQuantizationResult(image=canvas.convert("RGBA"),index_map=indexes,report={})
    optimized,step,offset,optimization=fit_result_to_paint_budget(
        result,colors,target_usage_percent=75.0,board_item_type="BoardItem2")
    if not optimization["game_point_target_met"]:
        raise ValueError("Resource target forecast failed in existing optimizer")
    if optimization["estimated_game_points_after"]>6000:
        raise ValueError("Even forecast game points exceed actual board nominal 6000")
    candidate=build_color_scanline_plan(
        optimized.index_map,colors,row_step_px=step,row_offset_px=offset,
        source_name="wV6VeZI9S1Y.png")
    native,crop,ink=preview_for(candidate)
    if (candidate["summary"]["point_quota_estimate"]["estimated_point_count"]!=
        optimization["estimated_game_points_after"]):
        raise ValueError("Optimizer and actual final plan have different quota estimates")
    if (candidate["summary"]["stroke_count"]!=optimization["stroke_count_after"] or
        int(np.count_nonzero(optimized.index_map[:,:155]>=0)) or
        int(np.count_nonzero(optimized.index_map[:,305:]>=0))):
        raise ValueError("Optimizer result identity/ROI mismatch")
    output.mkdir(parents=True,exist_ok=True)
    (output/"baseline-D-plan.json").write_text(
        json.dumps(baseline,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf8")
    (output/"budgeted-plan.json").write_text(
        json.dumps(candidate,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf8")
    (output/"optimizer-report.json").write_text(
        json.dumps(optimization,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf8")
    native.save(output/"budgeted-full-alpha.png")
    crop.save(output/"budgeted-roi.png")
    orig_crop.save(output/"baseline-D-roi.png")
    sheet([roi,orig_crop,crop],["Original RGB","V28-D: 13258 est. points",
                                "V29: existing budget optimizer"],output/"comparison-full.png")
    sheet([roi,orig_crop,crop],["Original RGB","V28-D","V29 budget"],
          output/"comparison-faces.png",top=True)
    pixels=np.asarray(crop,dtype=np.int16)
    source_rgb=np.asarray(roi,dtype=np.int16)
    before=np.asarray(orig_crop,dtype=np.int16)
    xmap=np.asarray(optimized.index_map)
    results={
        "experiment":"ENGINE001_VISUAL_BUDGET_V29",
        "status":"OFFLINE_NATIVE_PLANNER_PREVIEW_NOT_GAME",
        "source_sha256":SOURCE_SHA,
        "frozen_V28_D_preview_sha256":sha(frozen_v28),
        "input_palette_rgb":[c["rgb"] for c in colors],
        "input_visible_index_pixels":int(np.count_nonzero(indexes>=0)),
        "original_D":{"strokes":FROZEN_STROKES,"estimated_game_points":FROZEN_EST_POINTS,
                      "preview_alpha_pixels":orig_alpha_count,
                      "original_rgb_mae":round(float(np.abs(before-source_rgb).mean()),4)},
        "budgeted":{"strokes":len(candidate["strokes"]),
                    "estimated_game_points":optimization["estimated_game_points_after"],
                    "row_step":step,"row_offset":offset,
                    "preview_alpha_pixels":ink,
                    "source_index_visible_after":int(np.count_nonzero(xmap>=0)),
                    "original_rgb_mae":round(float(np.abs(pixels-source_rgb).mean()),4),
                    "changed_from_D_rgb_pixels":int(np.any(pixels!=before,axis=2).sum())},
        "optimized_resource_report":optimization,
        "versions":{"python":platform.python_version(),"numpy":np.__version__,
                    "pillow":Image.__version__},
        "not_tested":["live E4","actual CHALK","native Egret full-color quality",
                      ">=99% actual paint coverage","3 logical px game leakage",
                      "independent E5 recognizability"],
        "production_changed":False}
    results["derived_sha256"]={f.name:sha(f) for f in sorted(output.iterdir()) if f.is_file()}
    (output/"report.json").write_text(json.dumps(results,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps({"baseline":results["original_D"],"optimized":results["budgeted"],
                      "quota_met":optimization["game_point_target_met"]},indent=2))
    return results

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for f in ["source","frozen-v28","output"]:p.add_argument("--"+f,type=Path,required=True)
    a=p.parse_args()
    do_run(a.source,a.frozen_v28,a.output)

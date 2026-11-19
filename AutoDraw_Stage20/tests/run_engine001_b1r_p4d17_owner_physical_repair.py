#!/usr/bin/env python3
"""P4D17 experimental full original E/F actual Egret native redraw.
NO production writes, NO direct capsule quality oracle, NO exact CHALK claims.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

import run_engine001_b1r_p3b_engine128_adaptive32 as p3b
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
import run_engine001_b1r_p4b4_boundary_tolerance_sweep as p4b4
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
import run_engine001_b1r_p4c0_full_multicolor_native_preview as p4c0
import run_engine001_b1r_p4d0_unbounded_adaptive_vs_scanline_native as p4d0
import run_engine001_b1r_p4d13_full_original_relaxed_finish as p4d13
import run_engine001_b1r_p4d16_canvas_aa_density as p4d16
from run_engine001_b1r_p2_joint_region_outline import digest

EXPERIMENT="ENGINE001_B1R_P4D17_OWNER_PHYSICAL_REPAIR_V1"
PREREG="ENGINE001_B1R_P4D17_OWNER_PHYSICAL_REPAIR_PREREG_2026-11-19.md"
METHODS=p4d0.METHODS
ARMS=("BASELINE","OWNER_FIRST_OCCURRENCE","OWNER_REVERSED","INTERIOR_SUBPIXEL_REPAIR")
MAX_EXTRA_STROKES=1200
NATIVE_SHAPE=(720,1380,4)
SCALE=3
X0=155
WHITE=6
ALPHA=24
RGB_TOL=32


def grouped(plan:list[dict],reverse:bool=False)->list[dict]:
    """Stable owner grouping retains every original stroke and its internal order."""
    if not plan or any("colorIndex" not in s for s in plan):
        raise ValueError("BLOCKED_P4D17_INVALID_FROZEN_PLAN")
    first={}
    for s in plan:
        first.setdefault(int(s["colorIndex"]),len(first))
    owners=sorted(first,key=lambda c:first[c],reverse=reverse)
    return [s for c in owners for s in plan if int(s["colorIndex"])==c]


def physical_owner_score(native:np.ndarray,index:np.ndarray,
                         palette:np.ndarray)->tuple[np.ndarray,np.ndarray,np.ndarray]:
    if (native.shape!=NATIVE_SHAPE or native.dtype!=np.uint8 or
        index.shape!=(240,150) or index.dtype!=np.uint8 or
        palette.shape!=(128,3) or palette.dtype!=np.uint8):
        raise ValueError("BLOCKED_P4D17_NATIVE_SOURCE_SHAPE")
    roi=native[:,X0*SCALE:(X0+150)*SCALE,:]
    rgb=np.asarray(p4c0.preview_native(native),dtype=np.uint8)
    source=np.repeat(np.repeat(palette[index],SCALE,0),SCALE,1)
    diff=np.max(np.abs(rgb.astype(np.int16)-source.astype(np.int16)),axis=2)
    good=(roi[:,:,3]>=ALPHA)&(diff<=RGB_TOL)
    count=good.reshape(240,SCALE,150,SCALE).sum(axis=(1,3))
    return good,count,diff


def strict_interior(index:np.ndarray)->np.ndarray:
    """3x3 owner-identical logical cells; source-white never eligible."""
    if index.shape!=(240,150) or index.dtype!=np.uint8:
        raise ValueError("BLOCKED_P4D17_SOURCE_FORMAT")
    eligible=np.zeros(index.shape,bool)
    for owner in np.unique(index):
        if int(owner)==WHITE:
            continue
        same=(index==owner).astype(np.uint8)
        eligible |= cv2.erode(same,np.ones((3,3),np.uint8),
                              borderType=cv2.BORDER_CONSTANT,
                              borderValue=0).astype(bool)
    return eligible


def repair_plan(index:np.ndarray,palette:np.ndarray,native:np.ndarray,
                limit:int=MAX_EXTRA_STROKES)->tuple[list[dict],dict]:
    """Target a missing physical pixel center within 3x3 same-owner interior.

    No capsule model is used as evidence: this merely proposes genuine Egret
    width1 strokes. The post-render native PNG decides whether they helped.
    """
    if limit!=MAX_EXTRA_STROKES:
        raise ValueError("BLOCKED_P4D17_FROZEN_EXPERIMENT_CAP")
    good,count,diff=physical_owner_score(native,index,palette)
    roi=native[:,X0*SCALE:(X0+150)*SCALE,:]
    safe=strict_interior(index)
    targets=np.argwhere(safe&(count<9))
    targets=sorted((int(y),int(x)) for y,x in targets)
    targets.sort(key=lambda p:(int(count[p]),p[0],p[1]))
    plan=[]
    hole_cells=0
    wrong_color_cells=0
    for y,x in targets[:limit]:
        tiles=good[y*3:y*3+3,x*3:x*3+3]
        if np.all(tiles):
            raise ValueError("BLOCKED_P4D17_ALREADY_CORRECT")
        alpha=roi[y*3:y*3+3,x*3:x*3+3,3]
        delta=diff[y*3:y*3+3,x*3:x*3+3]
        wrong=np.argwhere(~tiles)
        # Deterministic: true alpha0 first, then low-alpha, then largest RGB error.
        physical=sorted(((int(yy),int(xx)) for yy,xx in wrong),
                        key=lambda pos:(int(alpha[pos]),-int(delta[pos]),pos[0],pos[1]))
        yy,xx=physical[0]
        hole_cells+=int(int(alpha[yy,xx])==0)
        wrong_color_cells+=int(int(alpha[yy,xx])>=ALPHA)
        # The true Egret CanvasRenderer shifts width1 by (+.5,+.5) logical.
        center_x=x+(xx+.5)/3.
        center_y=y+(yy+.5)/3.
        path_x=center_x-.5
        path_y=center_y-.5
        owner=int(index[y,x])
        source=p4d0._stroke(owner,palette,path_x-.025,path_x+.025,y,width=1)
        for p in source["points"]:
            p["y"]=float(path_y)
        plan.append(source)
    return p4c0.renumber(plan),{
        "interior_target_cells_not_9of9":len(targets),
        "new_width1_strokes":len(plan),
        "selected_native_alpha0_targets":hole_cells,
        "selected_existing_ink_wrong_color_targets":wrong_color_cells,
        "strict_source_3x3_owner_only":True,
        "max_additional_strokes":MAX_EXTRA_STROKES,
    }


def score(native:np.ndarray,index:np.ndarray,palette:np.ndarray)->dict:
    good,count,diff=physical_owner_score(native,index,palette)
    original=p4d13.native_metrics(native,index,palette)
    nonwhite=index!=WHITE
    inside=strict_interior(index)
    crop=native[:,X0*SCALE:(X0+150)*SCALE,3]
    interior=np.repeat(np.repeat(inside,3,0),3,1)
    return {
        "logical_correct5":int(((count>=5)&nonwhite).sum()),
        "logical_correct7":int(((count>=7)&nonwhite).sum()),
        "logical_correct9":int(((count>=9)&nonwhite).sum()),
        "correct_owner_backing_pixels":int((good&np.repeat(
             np.repeat(nonwhite,3,0),3,1)).sum()),
        "source_nonwhite_backing":int(nonwhite.sum()*9),
        "original_white_alpha24_backing":original["original_white_ink_alpha24_backing"],
        "protected_original_white_alpha24_backing":
            original["protected_original_white_ink_alpha24_backing"],
        "far_gt3logical_native_ink_alpha24_diagnostic":
            original["far_gt3logical_native_ink_alpha24_diagnostic"],
        "out_of_source_rectangle_native_ink_alpha24":
            original["out_of_source_rectangle_native_ink_alpha24"],
        "interior_true_alpha0_physical":
            int(((crop==0)&interior).sum()),
        "interior_physical_below24":
            int(((crop<24)&interior).sum()),
        "nonwhite_alpha24_wrong_color_backing":int((~good&(crop>=24)&
            np.repeat(np.repeat(nonwhite,3,0),3,1)).sum()),
        "face_24x24_logical_correct5":
            int(((count>=5)&nonwhite)[45:69,40:64].sum()),
        "face_24x24_logical_correct9":
            int(((count>=9)&nonwhite)[45:69,40:64].sum()),
        "target_nonwhite_logical":int(nonwhite.sum()),
        "protected_real_foreign_owner_attribution":
            "NOT_PROVEN_WITH_FINAL_COMPOSITE",
    }


def baseline_guard(a:dict,b:dict)->bool:
    return (
        b["original_white_alpha24_backing"]<=a["original_white_alpha24_backing"]
        and b["protected_original_white_alpha24_backing"]<=a["protected_original_white_alpha24_backing"]
        and b["logical_correct5"]>=a["logical_correct5"]
        and b["far_gt3logical_native_ink_alpha24_diagnostic"]<=
            a["far_gt3logical_native_ink_alpha24_diagnostic"]
    )


def choose_arm(results:dict[str,dict])->str:
    order=("BASELINE","OWNER_FIRST_OCCURRENCE","OWNER_REVERSED")
    eligible=[x for x in order if baseline_guard(
        results["BASELINE"],results[x])]
    if "BASELINE" not in eligible:
        raise ValueError("BLOCKED_P4D17_BASELINE_NOT_ELIGIBLE")
    # Max correct physical; deterministic order ties favor baseline.
    return max(eligible,key=lambda name:results[name]["correct_owner_backing_pixels"])


def comparison(original:np.ndarray,target:np.ndarray,
               previews:dict[str,Image.Image],output:Path)->None:
    images=[
        ("ORIGINAL RGB",Image.fromarray(original).resize((450,720),
                    Image.Resampling.NEAREST)),
        ("B1-R SOURCE GAME COLORS",Image.fromarray(target).resize(
                    (450,720),Image.Resampling.NEAREST)),
        *[(key.replace("_"," "),previews[key]) for key in ARMS],
    ]
    picture=Image.new("RGB",(450*len(images),756),"white")
    pen=ImageDraw.Draw(picture)
    for i,(title,img) in enumerate(images):
        picture.paste(img,(450*i,30))
        pen.text((450*i+8,10),title,fill="black")
    picture.save(output/"P4D17_ORIGINAL_VS_4_NATIVE_EGRET_ARMS.png")
    x0,y0,x1,y1=(40,45,64,69)
    face=Image.new("RGB",(240*len(images),268),"white")
    painter=ImageDraw.Draw(face)
    for i,(name,img) in enumerate(images):
        face.paste(img.crop((x0*3,y0*3,x1*3,y1*3)).resize(
            (240,240),Image.Resampling.NEAREST),(i*240,28))
        painter.text((i*240+3,8),name,fill="black")
    face.save(output/"P4D17_FACE_EYES_VS_4_NATIVE_EGRET_ARMS.png")


def run(workspace:Path,engine_js:Path,renderer:Path,source_artifact:Path,
        output:Path)->dict:
    if output.exists():
        raise ValueError("BLOCKED_P4D17_OUTPUT_EXISTS")
    if (p4b1.git_blob(engine_js.read_bytes())!=p3b.ENGINE_GIT_BLOB_SHA1 or
        p4b1.git_blob(renderer.read_bytes())!=p4d0.RENDERER_BLOB):
        raise ValueError("BLOCKED_P4D17_PINNED_GAME_RENDERER")
    prereg=workspace/"AutoDraw_Stage20"/"docs"/PREREG
    if not prereg.is_file() or EXPERIMENT not in prereg.read_text("utf8"):
        raise ValueError("BLOCKED_P4D17_PREREG")
    frozen=p4d16.FrozenArtifact(source_artifact)
    try:
        parent=frozen.check()
        if parent.get("experiment")!=p4d13.EXPERIMENT:
            raise ValueError("BLOCKED_P4D17_FROZEN_PARENT_DRIFT")
        original=frozen.image("ORIGINAL_RGB_LOGICAL.png","RGB",(150,240))
        source={}
        for method in METHODS:
            index=frozen.image(method+"/SOURCE_OWNER_INDEX.png","L",(150,240))
            rgb=frozen.image(method+"/SOURCE_OWNER_RGB.png","RGB",(150,240))
            plan=json.loads(frozen.read(method+"/FINAL_RELAXED_FULL_PLAN.json"))
            old=frozen.image(method+"/STAGE_03_RELAXED_REPAIR_NATIVE.png",
                             "RGBA",(1380,720))
            if (len(plan)!=parent["methods"][method]["stages"][
                    "STAGE_03_RELAXED_REPAIR"]["total_strokes"] or
                int((index!=WHITE).sum())!=parent["methods"][method]["nonwhite_target"]):
                raise ValueError("BLOCKED_P4D17_UNPINNED_FULL_SOURCE_PLAN")
            source[method]=(index,rgb,plan,old)
    finally:
        frozen.close()
    palette,_=p3b.read_engine_palette(engine_js)
    for method,(idx,rgb,plan,old) in source.items():
        if not np.array_equal(palette[idx],rgb) or any(
            s["colorRgb"]!=((int(palette[s["colorIndex"],0])<<16)|
                            (int(palette[s["colorIndex"],1])<<8)|
                             int(palette[s["colorIndex"],2]))
            for s in plan):
            raise ValueError("BLOCKED_P4D17_TARGET_COLOR_OR_STROKE_DRIFT")
    output.mkdir(parents=True)
    Image.fromarray(original).save(output/"ORIGINAL_RGB_LOGICAL.png")
    all_methods={}
    with p4d0.patched_test_renderer(renderer):
        with p4b7.native_egret_session(workspace) as driver:
            driver.set_script_timeout(900)
            browser={
                "browserName":driver.capabilities.get("browserName"),
                "browserVersion":driver.capabilities.get("browserVersion"),
                "platformName":driver.capabilities.get("platformName")
            }
            blank,meta=p4d13.render(driver,output,"REAL_EGRET_BLANK",[])
            if np.any(blank[:,:,3]):
                raise ValueError("BLOCKED_P4D17_NONEMPTY_TRUE_EGRET_BLANK")
            for method in METHODS:
                idx,rgb,base,old=source[method]
                folder=output/method
                folder.mkdir()
                Image.fromarray(idx).save(folder/"SOURCE_OWNER_INDEX.png")
                Image.fromarray(rgb).save(folder/"SOURCE_OWNER_RGB.png")
                plans={
                    "BASELINE":base,
                    "OWNER_FIRST_OCCURRENCE":grouped(base,False),
                    "OWNER_REVERSED":grouped(base,True),
                }
                if (len(plans["BASELINE"])!=len(plans["OWNER_FIRST_OCCURRENCE"]) or
                    len(plans["BASELINE"])!=len(plans["OWNER_REVERSED"])):
                    raise ValueError("BLOCKED_P4D17_REORDER_LOST_STROKES")
                previews={}
                results={}
                real={}
                for arm in ARMS[:3]:
                    plan=p4c0.renumber(plans[arm])
                    (folder/(arm+"_PLAN.json")).write_text(
                        json.dumps(plan,ensure_ascii=False,indent=2)+"\n","utf8")
                    native,metadata=p4d13.render(driver,folder,arm+"_REAL_NATIVE",plan)
                    results[arm]=score(native,idx,palette)
                    results[arm]["strokes"]=len(plan)
                    results[arm]["native_png_sha256"]=metadata["source_sha256"]
                    previews[arm]=p4c0.preview_native(native)
                    previews[arm].save(folder/(arm+"_PREVIEW.png"))
                    real[arm]=native
                    print("P4D17_REAL_NATIVE",method,arm,
                          results[arm]["correct_owner_backing_pixels"],
                          results[arm]["logical_correct9"],
                          results[arm]["original_white_alpha24_backing"],
                          flush=True)
                chosen=choose_arm(results)
                repairs,diag=repair_plan(idx,palette,real[chosen])
                complete=p4c0.renumber(plans[chosen]+repairs)
                (folder/"INTERIOR_SUBPIXEL_REPAIR_PLAN.json").write_text(
                    json.dumps(complete,ensure_ascii=False,indent=2)+"\n","utf8")
                native,metadata=p4d13.render(driver,folder,
                    "INTERIOR_SUBPIXEL_REPAIR_REAL_NATIVE",complete)
                results["INTERIOR_SUBPIXEL_REPAIR"]=score(native,idx,palette)
                results["INTERIOR_SUBPIXEL_REPAIR"]["strokes"]=len(complete)
                results["INTERIOR_SUBPIXEL_REPAIR"]["native_png_sha256"]=metadata["source_sha256"]
                previews["INTERIOR_SUBPIXEL_REPAIR"]=p4c0.preview_native(native)
                previews["INTERIOR_SUBPIXEL_REPAIR"].save(
                    folder/"INTERIOR_SUBPIXEL_REPAIR_PREVIEW.png")
                original_baseline=score(old,idx,palette)
                comparison(original,rgb,previews,folder)
                results["INTERIOR_SUBPIXEL_REPAIR"]["delta_vs_selected"]={
                    k:results["INTERIOR_SUBPIXEL_REPAIR"][k]-results[chosen][k]
                    for k in ("logical_correct5","logical_correct7",
                              "logical_correct9","correct_owner_backing_pixels",
                              "interior_true_alpha0_physical",
                              "original_white_alpha24_backing",
                              "protected_original_white_alpha24_backing")
                }
                all_methods[method]={
                    "results":results,
                    "frozen_P4D13_original_baseline":original_baseline,
                    "selected_before_repair":chosen,
                    "selected_pre_repair_eligible":baseline_guard(
                        results["BASELINE"],results[chosen]),
                    "repair_selection":diag,
                    "new_repair_not_worsen_original_white":
                        (results["INTERIOR_SUBPIXEL_REPAIR"][
                         "original_white_alpha24_backing"]<=
                         results["BASELINE"]["original_white_alpha24_backing"]),
                    "new_repair_not_worsen_protected_white":
                        (results["INTERIOR_SUBPIXEL_REPAIR"][
                         "protected_original_white_alpha24_backing"]<=
                         results["BASELINE"]["protected_original_white_alpha24_backing"]),
                    "new_repair_5of9_non_degradation":
                        (results["INTERIOR_SUBPIXEL_REPAIR"]["logical_correct5"]>=
                         results["BASELINE"]["logical_correct5"]),
                }
                print("P4D17_FINAL",method,chosen,
                      results["INTERIOR_SUBPIXEL_REPAIR"]["correct_owner_backing_pixels"],
                      "holes",results["INTERIOR_SUBPIXEL_REPAIR"]["interior_true_alpha0_physical"],
                      "white",results["INTERIOR_SUBPIXEL_REPAIR"]["original_white_alpha24_backing"],
                      flush=True)
    if p4b1.git_blob(renderer.read_bytes())!=p4d0.RENDERER_BLOB:
        raise ValueError("BLOCKED_P4D17_TEST_RENDERER_RESTORATION")
    final={
        "experiment":EXPERIMENT,
        "technical_result":"P4D17_TRUE_EGRET_FULL_ORIGINAL_EF_OWNER_REORDER_AND_PHYSICAL_REPAIR",
        "parent_P4D13_E3_SHA":p4d16.PARENT_P4D13_SHA,
        "parent_manifest_SHA256_verified":39,
        "source_original_sha256":p4d0.SOURCE_SHA,
        "game_bundle_blob":p3b.ENGINE_GIT_BLOB_SHA1,
        "renderer_blob":p4d0.RENDERER_BLOB,
        "original_source_target_only":True,
        "no_G32_V44_used":True,
        "browser":browser,
        "native_blank_alpha0":True,
        "native_full_scene_count":9,
        "arms":list(ARMS),
        "methods":all_methods,
        "production_promotion":False,
        "protected_foreign_zero_full_quality_gate":"NOT_PROVEN",
        "E4_game_live":"NOT_RUN",
        "E5_independent_visual":"NOT_RUN",
        "exact_run_bound_CHALK":None,
        "github_sha":os.getenv("GITHUB_SHA"),
        "github_run_id":os.getenv("GITHUB_RUN_ID"),
    }
    final["members_sha256"]={
        str(p.relative_to(output)).replace("\\","/"):digest(p.read_bytes())
        for p in sorted(output.rglob("*")) if p.is_file()
    }
    (output/"report.json").write_text(json.dumps(
        final,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
    return final


if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("--workspace",type=Path,required=True)
    cli.add_argument("--engine-js",type=Path,required=True)
    cli.add_argument("--renderer",type=Path,required=True)
    cli.add_argument("--source-artifact",type=Path,required=True)
    cli.add_argument("--output",type=Path,required=True)
    a=cli.parse_args()
    run(a.workspace,a.engine_js,a.renderer,a.source_artifact,a.output)

#!/usr/bin/env python3
"""P4D13: finish full original B1-R E/F with cumulative native Egret and overlap.

SCIENTIFIC VISUAL DIAGNOSTIC ONLY: deliberately DO NOT reject paint for touching
other source colors. Reuse frozen P4D0 adaptive source, native renderer and
scanline reference; three real native-feedback source-index residual passes.
Never change production/executor/CHALK thresholds or use fake brush geometry.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

import run_engine001_b1r_p3d_source_edge_mask_ablation as p3d
import run_engine001_b1r_p3b_engine128_adaptive32 as p3b
import run_engine001_b1r_p4b4_boundary_tolerance_sweep as p4b4
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
import run_engine001_b1r_p4c0_full_multicolor_native_preview as p4c0
import run_engine001_b1r_p4d0_unbounded_adaptive_vs_scanline_native as p4d0
from run_engine001_b1r_p1_fullrgb_edge_aware import check_source
from run_engine001_b1r_p2_joint_region_outline import digest

EXPERIMENT="ENGINE001_B1R_P4D13_FULL_ORIGINAL_RELAXED_FINISH_V1"
PREREG="ENGINE001_B1R_P4D13_FULL_ORIGINAL_RELAXED_FINISH_PREREG_2026-11-19.md"
METHODS=p4d0.METHODS
SOURCE=p4d0.SOURCE
WHITE=p4d0.WHITE
ALPHA=p4d0.ALPHA
X0=p4d0.X0
SCALE=p4d0.SCALE
BOARD_SHAPE=p4d0.NATIVE_SHAPE
MAX_REPAIR_ROUNDS=3
RGB_TOL=32
MIN_CORRECT_SUBPIXELS=5
CMD=("return window.AutoDrawGameRendererReference."
     "renderP4A2BrushWidths1to10Probe(arguments[0]);")


def full_source_state(native:np.ndarray,index:np.ndarray,palette:np.ndarray)->np.ndarray:
    """Correct color on >=5/9 ACTUAL Egret backing pixels, across 150x240 source."""
    if (native.shape!=BOARD_SHAPE or native.dtype!=np.uint8 or
        index.shape!=(240,150) or index.dtype!=np.uint8 or
        palette.shape!=(128,3) or palette.dtype!=np.uint8):
        raise ValueError("BLOCKED_P4D13_BAD_NATIVE_SOURCE_SHAPE")
    preview=np.asarray(p4c0.preview_native(native),dtype=np.uint8)
    if preview.shape!=(240*SCALE,150*SCALE,3):
        raise ValueError("BLOCKED_P4D13_NATIVE_PREVIEW_SHAPE")
    expected=np.repeat(np.repeat(palette[index],SCALE,axis=0),SCALE,axis=1)
    ink=native[:,X0*SCALE:(X0+150)*SCALE,3]>=ALPHA
    close=np.max(np.abs(preview.astype(np.int16)-expected.astype(np.int16)),
                 axis=2)<=RGB_TOL
    subpixel=((close & ink).reshape(240,SCALE,150,SCALE)
              .sum(axis=(1,3)))
    return (subpixel>=MIN_CORRECT_SUBPIXELS)&(index!=WHITE)


def residual_owner_runs(index:np.ndarray,state:np.ndarray,palette:np.ndarray)->list[dict]:
    """One width1 source-color row-run for EVERY remaining wrong nonwhite cell."""
    if (index.shape!=(240,150) or state.shape!=index.shape or
        index.dtype!=np.uint8 or state.dtype!=np.bool_ or
        palette.shape!=(128,3)):
        raise ValueError("BLOCKED_P4D13_RESIDUAL_FORMAT")
    strokes=[]
    for y in range(240):
        x=0
        while x<150:
            owner=int(index[y,x])
            if owner==WHITE or state[y,x]:
                x+=1
                continue
            start=x
            while (x+1<150 and int(index[y,x+1])==owner and
                   not state[y,x+1]):
                x+=1
            strokes.append(p4d0._stroke(
                owner,palette,float(start)+.125,float(x)+.375,y,width=1))
            x+=1
    # Deliberately do NOT gate on neighboring owner, white or cumulative loss.
    return strokes


def native_metrics(native:np.ndarray,index:np.ndarray,palette:np.ndarray)->dict:
    state=full_source_state(native,index,palette)
    target=index!=WHITE
    correct=int(state.sum())
    real=p4d0._native_stats(native,index,palette)
    by_owner={}
    for v in sorted(int(x) for x in np.unique(index) if int(x)!=WHITE):
        owner=index==v
        by_owner[str(v)]={
            "target_logical":int(owner.sum()),
            "correct_logical":int((owner&state).sum()),
            "remaining_logical":int((owner&~state).sum()),
        }
    # Board-wide distance from actual full-source nonwhite logical pixels:
    # useful far>3 diagnostic, NOT a replacement for frozen acceptance checks.
    target_full=np.zeros((240,460),bool)
    target_full[:,X0:X0+150]=target
    distance=cv2.distanceTransform(
        (~target_full).astype(np.uint8),cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
    far=np.repeat(np.repeat(distance>3,SCALE,axis=0),SCALE,axis=1)
    raw_ink=native[:,:,3]>=ALPHA
    protected=p4b4.source_critical_rois()
    if protected.shape!=index.shape:
        raise ValueError("BLOCKED_P4D13_PROTECTED_SOURCE_DRIFT")
    protected_target=protected&target
    crop_ink=raw_ink[:,X0*SCALE:(X0+150)*SCALE]
    white_rep=np.repeat(np.repeat(index==WHITE,SCALE,0),SCALE,1)
    prot_white_rep=np.repeat(np.repeat(protected&(index==WHITE),SCALE,0),SCALE,1)
    return {
        "target_nonwhite_logical":int(target.sum()),
        "correct_owner_logical_5of9":correct,
        "correct_fraction":float(correct/target.sum()) if target.any() else 1.,
        "remaining_source_owner_zeros":int((target&~state).sum()),
        "target_original_white_logical":int((index==WHITE).sum()),
        "original_white_ink_alpha24_backing":int((crop_ink&white_rep).sum()),
        "protected_original_white_ink_alpha24_backing":
            int((crop_ink&prot_white_rep).sum()),
        "protected_nonwhite_logical_target":int(protected_target.sum()),
        "protected_nonwhite_logical_incorrect":
            int((protected_target&~state).sum()),
        "far_gt3logical_native_ink_alpha24_diagnostic":int((raw_ink&far).sum()),
        "out_of_source_rectangle_native_ink_alpha24":int(
            raw_ink.sum()-crop_ink.sum()),
        "native_any_ink_coverage":real["native_nonwhite_any_ink_coverage_alpha24"],
        "native_composite_rgb_delta_le32":
            real["native_source_palette_rgb_maxchannel_delta_le32_on_nonwhite"],
        "per_source_owner":by_owner,
        "protected_real_foreign_owner_attribution":
            "NOT_MEASURED_FINAL_COMPOSITE_CANNOT_INFER_STROKE_OWNER",
    }


def draw_comparison(original:np.ndarray,palette_index:np.ndarray,
                    palette:np.ndarray,previews:dict[str,Image.Image],
                    index:np.ndarray,final_state:np.ndarray,
                    folder:Path)->None:
    # All native canvases are p4c0.preview_native real BoardPane crops.
    cards=[
        ("ORIGINAL RGB",Image.fromarray(original).resize(
            (450,720),Image.Resampling.NEAREST)),
        ("B1-R ENGINE PALETTE",Image.fromarray(palette[palette_index]).resize(
            (450,720),Image.Resampling.NEAREST)),
        ("ADAPTIVE FIRST PASS",previews["INITIAL_ADAPTIVE"]),
        ("ADAPTIVE AFTER 3 REPAIR",previews["FINAL_RELAXED"]),
        ("NATIVE SCANLINE CONTROL",previews["SCANLINE_CONTROL"]),
    ]
    image=Image.new("RGB",(450*len(cards),758),"white")
    painter=ImageDraw.Draw(image)
    for i,(title,card) in enumerate(cards):
        image.paste(card,(i*450,38))
        painter.text((i*450+10,10),title,fill=(0,0,0))
    image.save(folder/"P4D13_VISUAL_FULL_ORIGINAL_VS_RELAXED_EGRET.png")
    x0,y0,x1,y1=(40,45,64,69)
    face_cards=[]
    for title,card in cards:
        face_cards.append((title,card.crop(
            (x0*SCALE,y0*SCALE,x1*SCALE,y1*SCALE)).resize(
                (288,288),Image.Resampling.NEAREST)))
    face=Image.new("RGB",(288*len(face_cards),322),"white")
    painter=ImageDraw.Draw(face)
    for i,(label,img) in enumerate(face_cards):
        face.paste(img,(i*288,30))
        painter.text((i*288+6,8),label,fill=(0,0,0))
    face.save(folder/"P4D13_VISUAL_FACE_EYES_5WAY.png")
    # Inspection mask; model-only illustration of measured native state.
    good=final_state
    target=index!=WHITE
    result=np.full((240,150,3),255,np.uint8)
    result[target&~good]=(220,73,74)
    result[good]=(59,155,91)
    Image.fromarray(result).save(folder/"P4D13_NATIVE_MEASURED_STATE_GREEN_RED.png")


def render(driver,folder:Path,stem:str,strokes:list[dict]):
    strokes=p4c0.renumber(strokes)
    result=driver.execute_script(CMD,strokes)
    native,meta=p4d0.read_webgl_result(result,folder,stem)
    schema=("ENGINE001_B1R_P4A2_NATIVE_1_TO_10" if strokes else
            "ENGINE001_B1R_P4A2_BLANK_WEBGL")
    if (native.shape!=BOARD_SHAPE or native.dtype!=np.uint8 or
        meta.get("schema")!=schema or
        meta.get("renderer")!="real Egret 5.4.1 BoardPane/WebGLRenderer" or
        (strokes and meta.get("strokeCount")!=len(strokes))):
        raise ValueError("BLOCKED_P4D13_NOT_TRUE_EGRET")
    return native,meta


def run(workspace:Path,source:Path,engine_js:Path,
        renderer:Path,output:Path)->dict:
    if output.exists():
        raise ValueError("BLOCKED_P4D13_OUTPUT_EXISTS")
    check_source(source)
    if (p4d0.p4b1.git_blob(renderer.read_bytes())!=p4d0.RENDERER_BLOB or
        p4d0.p4b1.git_blob(engine_js.read_bytes())!=p3b.ENGINE_GIT_BLOB_SHA1):
        raise ValueError("BLOCKED_P4D13_PINNED_RENDERER_ENGINE")
    prereg=workspace/"AutoDraw_Stage20"/"docs"/PREREG
    if not prereg.is_file() or EXPERIMENT not in prereg.read_text("utf8"):
        raise ValueError("BLOCKED_P4D13_NOT_PREREGISTERED")
    palette,_=p3b.read_engine_palette(engine_js)
    output.mkdir(parents=True)
    (output/"README_RU.txt").write_text(
        "P4D13: исходная E/F, ПОЛНЫЙ источник150x240, реальный native Egret. "
        "Сознательно допускается задевание чужих цветов для научной визуализации. "
        "Покраска не отклоняется из-за чужих пикселей. Три последовательных "
        "native-feedback width1 repair rounds после полного adaptive плана, "
        "и scanline native control. ЗАПРЕЩЕНО использовать как production "
        "PASS, protected0 не доказан, exact game CHALK/E4/E5 NOT_RUN.\n","utf8")
    result={}
    with tempfile.TemporaryDirectory(prefix="engine001-p4d13-original-") as temp:
        fresh=Path(temp)/"original_p3d"
        parent=p3d.run(source,engine_js,fresh)
        if (parent["experiment"]!=p3d.EXPERIMENT or
            parent["original_source_sha256"]!=p4d0.SOURCE_SHA or
            not parent["P3B_original_recomputed_in_current_run"] or
            parent["legacy_G32_V44_M1_used_as_source"]):
            raise ValueError("BLOCKED_P4D13_BAD_SOURCE_PROVENANCE")
        original=np.asarray(Image.open(
            fresh/"00_ORIGINAL_RGB_LOGICAL.png").convert("RGB"),dtype=np.uint8)
        Image.fromarray(original).save(output/"ORIGINAL_RGB_LOGICAL.png")
        targets={}
        for method in METHODS:
            folder=output/method
            folder.mkdir()
            index=np.asarray(Image.open(
                fresh/(SOURCE+"_"+method+"_ENGINE_INDICES.png")),dtype=np.uint8)
            selected=parent["all_results"][SOURCE]["selected_engine_indices"]
            p4c0.validate_source(index,palette,selected)
            if parent["all_results"][SOURCE]["methods"][method]["status"]!=(
                "SOURCE_SCREEN_PASS_VISUAL_PENDING_RUNTIME_ACCESS_UNVERIFIED"):
                raise ValueError("BLOCKED_P4D13_SOURCE_SELECTION_DRIFT")
            Image.fromarray(index).save(folder/"SOURCE_OWNER_INDEX.png")
            Image.fromarray(palette[index]).save(folder/"SOURCE_OWNER_RGB.png")
            targets[method]=index
        if np.array_equal(targets[METHODS[0]],targets[METHODS[1]]):
            raise ValueError("BLOCKED_P4D13_FULL_EF_MUST_HAVE_SOURCE_DIFFERENCES")
        plans={}
        for method in METHODS:
            idx=targets[method]
            adaptive,model=p4d0.adaptive_unbounded(idx,palette)
            control=p4d0.first_scanline(idx,palette)
            plans[method]=(adaptive,control,model)
            folder=output/method
            for kind,plan in (("ADAPTIVE_INITIAL",adaptive),
                              ("FIRST_SCANLINE",control)):
                (folder/(kind+"_PLAN.json")).write_text(json.dumps(
                    plan,ensure_ascii=False,allow_nan=False)+"\n","utf8")
        with p4d0.patched_test_renderer(renderer) as audit:
            with p4b7.native_egret_session(workspace) as driver:
                driver.set_script_timeout(900)
                blank,meta=render(driver,output,"REAL_EGRET_BLANK",[])
                if np.any(blank[:,:,3]):
                    raise ValueError("BLOCKED_P4D13_NONEMPTY_NATIVE_BLANK")
                for method in METHODS:
                    folder=output/method
                    idx=targets[method]
                    initial,control,model=plans[method]
                    stage_metrics={}
                    previews={}
                    plan=list(initial)
                    # Never reject due to foreign overlap or protected damage:
                    # measure risks after each FULL native render.
                    native,meta=render(
                        driver,folder,"STAGE_00_INITIAL_ADAPTIVE_NATIVE",plan)
                    state=full_source_state(native,idx,palette)
                    stage_metrics["STAGE_00_INITIAL"]={
                        "native":native_metrics(native,idx,palette),
                        "total_strokes":len(plan),
                        "synthetic_vertices_NOT_CHALK":sum(len(s["points"]) for s in plan),
                        "native_png_sha256":meta["source_sha256"]}
                    previews["INITIAL_ADAPTIVE"]=p4c0.preview_native(native).copy()
                    previews["INITIAL_ADAPTIVE"].save(
                        folder/"STAGE_00_INITIAL_ADAPTIVE_REAL_EGRET_CROP.png")
                    for round_no in range(1,MAX_REPAIR_ROUNDS+1):
                        before=state.copy()
                        repairs=residual_owner_runs(idx,state,palette)
                        if repairs:
                            plan.extend(repairs)
                        # Native full replay (no accepting/rejecting individual strokes).
                        native,meta=render(
                            driver,folder,
                            f"STAGE_{round_no:02d}_RELAXED_REPAIR_NATIVE",plan)
                        state=full_source_state(native,idx,palette)
                        native_result=native_metrics(native,idx,palette)
                        stage_metrics[f"STAGE_{round_no:02d}_RELAXED_REPAIR"]={
                            "new_width1_run_strokes":len(repairs),
                            "pre_correct":int(before.sum()),
                            "new_correct_0_to_1":int((state&~before).sum()),
                            "lost_correct_1_to_0":int((before&~state).sum()),
                            "native":native_result,
                            "total_strokes":len(plan),
                            "synthetic_vertices_NOT_CHALK":sum(len(s["points"]) for s in plan),
                            "native_png_sha256":meta["source_sha256"]}
                        p4c0.preview_native(native).save(
                            folder/f"STAGE_{round_no:02d}_RELAXED_REAL_EGRET_CROP.png")
                        print("P4D13_NATIVE_REPAIR",method,round_no,
                              "additional_strokes",len(repairs),
                              "correct",int(state.sum()),
                              "remaining",native_result["remaining_source_owner_zeros"],
                              "new",int((state&~before).sum()),
                              "lost",int((before&~state).sum()),flush=True)
                    previews["FINAL_RELAXED"]=p4c0.preview_native(native).copy()
                    final_state=state.copy()
                    (folder/"FINAL_RELAXED_FULL_PLAN.json").write_text(
                        json.dumps(p4c0.renumber(plan),ensure_ascii=False,
                                   allow_nan=False)+"\n","utf8")
                    scan,meta=render(
                        driver,folder,"SCANLINE_CONTROL_REAL_NATIVE",control)
                    control_metrics=native_metrics(scan,idx,palette)
                    previews["SCANLINE_CONTROL"]=p4c0.preview_native(scan).copy()
                    previews["SCANLINE_CONTROL"].save(
                        folder/"SCANLINE_CONTROL_REAL_EGRET_CROP.png")
                    draw_comparison(original,idx,palette,previews,idx,
                                    final_state,folder)
                    result[method]={
                        "source_unique_owner_count":len(set(np.unique(idx))-{WHITE}),
                        "nonwhite_target":int((idx!=WHITE).sum()),
                        "adaptive_model_provenance":
                            "P4D0 original B1-R source heuristic; all image quality from real native",
                        "adaptive_initial_strokes":len(initial),
                        "scanline_control_strokes":len(control),
                        "scanline_native":control_metrics,
                        "stages":stage_metrics,
                        "final_repair_rounds":MAX_REPAIR_ROUNDS,
                        "final_owner_correct":int(final_state.sum()),
                        "final_owner_remaining":int(((idx!=WHITE)&~final_state).sum()),
                        "final_overlaps_not_rejected":True,
                        "native_full_scene_captures":5,
                    }
                    print("P4D13_FINAL_METHOD",method,
                          "first",stage_metrics["STAGE_00_INITIAL"]["native"][
                              "correct_owner_logical_5of9"],
                          "final",result[method]["final_owner_correct"],
                          "of",result[method]["nonwhite_target"],
                          "control",control_metrics["correct_owner_logical_5of9"],
                          flush=True)
        if p4d0.p4b1.git_blob(renderer.read_bytes())!=p4d0.RENDERER_BLOB:
            raise ValueError("BLOCKED_P4D13_RENDERER_WAS_NOT_RESTORED")
    report={
        "experiment":EXPERIMENT,
        "technical_result":"P4D13_FULL_SOURCE_EF_TRUE_NATIVE_RELAXED_FINISH",
        "source_original_sha256":p4d0.SOURCE_SHA,
        "source_B1R_P3D_fresh":True,
        "source_methods":list(METHODS),
        "all_original_EF_source_fully_painted":True,
        "original_EF_full_index_distinct":True,
        "game_bundle_git_blob":p3b.ENGINE_GIT_BLOB_SHA1,
        "renderer_git_blob":p4d0.RENDERER_BLOB,
        "actual_renderer":"real Egret 5.4.1 BoardPane/WebGLRenderer",
        "native_blank_alpha0":True,
        "original_source_pixels_shape":[240,150],
        "full_game_board_native_shape":list(BOARD_SHAPE),
        "expected_native_scenes":11,
        "native_overlap_policy":"UNRESTRICTED_DIAGNOSTIC_RECORD_ALL_DAMAGE",
        "protection_gate_P4B4":"NOT_PASSED_BY_DESIGN_REQUIRES_SEPARATE_ACCEPTANCE",
        "max_repair_rounds":MAX_REPAIR_ROUNDS,
        "methods":result,
        "production_promotion":False,
        "E4_live":"NOT_RUN",
        "E5_independent":"NOT_RUN",
        "exact_run_bound_CHALK":None,
        "github_sha":os.getenv("GITHUB_SHA"),
        "github_run_id":os.getenv("GITHUB_RUN_ID"),
    }
    report["members_sha256"]={
        str(f.relative_to(output)).replace("\\","/"):digest(f.read_bytes())
        for f in sorted(output.rglob("*")) if f.is_file()
    }
    (output/"report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
    return report


if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("--workspace",type=Path,required=True)
    cli.add_argument("--source",type=Path,required=True)
    cli.add_argument("--engine-js",type=Path,required=True)
    cli.add_argument("--renderer",type=Path,required=True)
    cli.add_argument("--output",type=Path,required=True)
    a=cli.parse_args()
    run(a.workspace,a.source,a.engine_js,a.renderer,a.output)

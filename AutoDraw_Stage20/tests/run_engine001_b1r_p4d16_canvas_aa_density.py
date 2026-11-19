#!/usr/bin/env python3
"""ENGINE-001 B1-R P4D16: true Egret raster phase & original P4D13 physical density.

Study A consumes immutable real E3 PNG and compares alpha/owner RGB (5/7/9).
Study B renders new genuine BoardPane/Egret phases and compares explicitly
MODEL_ONLY capsule/8x8 coverage to the actual native RGBA. No production use.
"""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import contextmanager
import hashlib
from io import BytesIO
import json
import math
import os
from pathlib import Path
from zipfile import ZipFile

import cv2
import numpy as np
from PIL import Image, ImageDraw

import run_engine001_b1r_p4d3_native_brush_repeatability as p4d3
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
import run_engine001_b1r_p4c0_full_multicolor_native_preview as p4c0
import run_engine001_b1r_p4d0_unbounded_adaptive_vs_scanline_native as p4d0
from run_engine001_b1r_p2_joint_region_outline import digest

EXPERIMENT="ENGINE001_B1R_P4D16_CANVAS_AA_DENSITY_V1"
PREREG="ENGINE001_B1R_P4D16_CANVAS_AA_DENSITY_PREREG_2026-11-19.md"
PARENT_P4D13_SHA="1f8b4dd13a0d74896643e6fc82c9a56d9ef65574"
PARENT_P4D3_BLOB="3437a9326b381d9c94d6ade80059d40adf233d09"
GAME_BLOB="46cc74de00b6cb5d207b1e1a2ffcd81613b6d388"
RENDERER_BLOB="76d950e0a8911888a9df3b675b866519ecf7bba4"
WHITE=6
X0=155
SCALE=3
ALPHA=24
RGB_TOL=32
METHODS=("E_SOBEL90","F_SOBEL90_LAB12")
STAGES=(
    ("STAGE_00_INITIAL","STAGE_00_INITIAL_ADAPTIVE_NATIVE.png"),
    ("STAGE_01_RELAXED_REPAIR","STAGE_01_RELAXED_REPAIR_NATIVE.png"),
    ("STAGE_02_RELAXED_REPAIR","STAGE_02_RELAXED_REPAIR_NATIVE.png"),
    ("STAGE_03_RELAXED_REPAIR","STAGE_03_RELAXED_REPAIR_NATIVE.png"),
    ("SCANLINE_CONTROL","SCANLINE_CONTROL_REAL_NATIVE.png"),
)
WIDTHS=(1,2,3,5,10)
ANGLES=(0,15,45,90,135)
LENGTHS=(4,34)
PHASES=(0.0,0.125,0.5)
EXPECTED_PHASE_CASES=150
EXPECTED_PHASE_NATIVE_SCENES=156
SIDE=162

class FrozenArtifact:
    def __init__(self,root:Path):
        self.root=root
        self.archive=ZipFile(root) if root.is_file() else None
        if not root.exists() or (self.archive is None and not root.is_dir()):
            raise ValueError("BLOCKED_P4D16_MISSING_PARENT_ARTIFACT")
    def read(self,path:str)->bytes:
        if path.startswith("/") or ".." in Path(path).parts:
            raise ValueError("BLOCKED_P4D16_UNSAFE_ARCHIVE_ENTRY")
        return self.archive.read(path) if self.archive else (self.root/path).read_bytes()
    def check(self)->dict:
        if self.archive and self.archive.testzip() is not None:
            raise ValueError("BLOCKED_P4D16_PARENT_ZIP_CRC")
        r=json.loads(self.read("report.json"))
        if (r.get("github_sha")!=PARENT_P4D13_SHA or
            r.get("game_bundle_git_blob")!=GAME_BLOB or
            r.get("renderer_git_blob")!=RENDERER_BLOB or
            r.get("source_original_sha256")!=p4d0.SOURCE_SHA or
            tuple(r.get("source_methods",()))!=METHODS or
            len(r.get("members_sha256",{}))!=39 or
            r.get("experiment")!="ENGINE001_B1R_P4D13_FULL_ORIGINAL_RELAXED_FINISH_V1"):
            raise ValueError("BLOCKED_P4D16_UNPINNED_P4D13")
        for file,sha in r["members_sha256"].items():
            if hashlib.sha256(self.read(file)).hexdigest()!=sha:
                raise ValueError("BLOCKED_P4D16_P4D13_HASH "+file)
        if r.get("native_blank_alpha0") is not True:
            raise ValueError("BLOCKED_P4D16_NO_TRUE_NATIVE_BLANK")
        return r
    def image(self,path:str,mode:str,size:tuple[int,int])->np.ndarray:
        with Image.open(BytesIO(self.read(path))) as im:
            if im.mode!=mode or im.size!=size:
                raise ValueError("BLOCKED_P4D16_PARENT_IMAGE_FORMAT "+path)
            return np.asarray(im).copy()
    def close(self):
        if self.archive:
            self.archive.close()


def color_subpixels(native:np.ndarray, index:np.ndarray,
                    source_rgb:np.ndarray)->tuple[np.ndarray,np.ndarray]:
    if (native.shape!=(720,1380,4) or native.dtype!=np.uint8 or
        index.shape!=(240,150) or index.dtype!=np.uint8 or
        source_rgb.shape!=(240,150,3) or source_rgb.dtype!=np.uint8):
        raise ValueError("BLOCKED_P4D16_REAL_NATIVE_SOURCE_SHAPES")
    # Identical source-over-white composition used by actual P4D13 quality.
    ink=native[:,X0*SCALE:(X0+150)*SCALE,:]
    composite=np.asarray(Image.alpha_composite(
        Image.new("RGBA",(450,720),"white"),Image.fromarray(ink,"RGBA")
    ).convert("RGB"),dtype=np.uint8)
    source=np.repeat(np.repeat(source_rgb,SCALE,axis=0),SCALE,axis=1)
    close=np.max(np.abs(composite.astype(np.int16)-source.astype(np.int16)),axis=2)<=RGB_TOL
    exact=(ink[:,:,3]>=ALPHA)&close
    count=exact.reshape(240,SCALE,150,SCALE).sum(axis=(1,3))
    return count,ink


def physical_holes(ink:np.ndarray,interior:np.ndarray)->dict:
    if ink.shape!=(720,450,4) or interior.shape!=(240,150):
        raise ValueError("BLOCKED_P4D16_BAD_HOLE_INPUT")
    valid=np.repeat(np.repeat(interior,SCALE,axis=0),SCALE,axis=1)
    zero=(ink[:,:,3]==0)&valid
    below=(ink[:,:,3]<ALPHA)&valid
    n,labels,stats,centroids=cv2.connectedComponentsWithStats(
        zero.astype(np.uint8),8)
    areas=stats[1:,cv2.CC_STAT_AREA] if n>1 else np.empty(0,np.int32)
    return {
        "interior_physical_cells":int(valid.sum()),
        "native_alpha_eq0_physical":int(zero.sum()),
        "native_alpha_below24_physical":int(below.sum()),
        "native_alpha_1_to_23_physical":int((below&~zero).sum()),
        "transparent_connected_components_all_sizes":len(areas),
        "transparent_connected_components_area_ge3":int((areas>=3).sum()),
        "largest_transparent_component_physical":int(areas.max()) if len(areas) else 0,
        "largest_component_areas_physical":sorted(map(int,areas),reverse=True)[:12],
    }


def density_visual(count:np.ndarray,index:np.ndarray,path:Path)->None:
    """Display measured true Egret source-owner count, not synthetic brush geometry."""
    if count.shape!=(240,150) or index.shape!=(240,150):
        raise ValueError("BLOCKED_P4D16_DENSITY_IMAGE_SHAPE")
    t=np.clip(count,0,9).astype(np.float32)/9.
    image=np.full((240,150,3),255,np.uint8)
    valid=index!=WHITE
    image[valid,0]=np.rint(235*(1-t[valid])+20*t[valid]).astype(np.uint8)
    image[valid,1]=np.rint(50*(1-t[valid])+170*t[valid]).astype(np.uint8)
    image[valid,2]=np.rint(50*(1-t[valid])+85*t[valid]).astype(np.uint8)
    Image.fromarray(image,"RGB").resize((450,720),Image.Resampling.NEAREST).save(path)


def density_audit(parent:FrozenArtifact,report:dict,folder:Path)->dict:
    folder.mkdir(parents=True,exist_ok=True)
    output={}
    for method in METHODS:
        source_index=parent.image(method+"/SOURCE_OWNER_INDEX.png","L",(150,240))
        source_rgb=parent.image(method+"/SOURCE_OWNER_RGB.png","RGB",(150,240))
        if np.any(source_rgb[source_index==WHITE]!=255):
            # The palette white can be non-RGB255, so do not assume literal white.
            # Original index is authoritative; this is only an informational note.
            pass
        target=source_index!=WHITE
        interior=cv2.distanceTransform(
            target.astype(np.uint8),cv2.DIST_L2,cv2.DIST_MASK_PRECISE)>=2
        published=report["methods"][method]
        if int(target.sum())!=published["nonwhite_target"]:
            raise ValueError("BLOCKED_P4D16_ORIGINAL_SOURCE_TARGET_DRIFT")
        results={}
        for key,filename in STAGES:
            raw=parent.image(method+"/"+filename,"RGBA",(1380,720))
            count,ink=color_subpixels(raw,source_index,source_rgb)
            published_metrics=(published["scanline_native"] if key=="SCANLINE_CONTROL"
                  else published["stages"][key]["native"])
            correct5=int(((count>=5)&target).sum())
            if correct5!=published_metrics["correct_owner_logical_5of9"]:
                raise ValueError("BLOCKED_P4D16_PARENT_5OF9_NOT_REPRODUCED "+method+"/"+key)
            original_white=np.repeat(np.repeat(~target,3,0),3,1)
            original_white_alpha24=int(((ink[:,:,3]>=ALPHA)&original_white).sum())
            if original_white_alpha24!=published_metrics["original_white_ink_alpha24_backing"]:
                raise ValueError("BLOCKED_P4D16_PARENT_WHITE_SPILL_DRIFT")
            holes=physical_holes(ink,interior)
            stages={
                "source_nonwhite_logical":int(target.sum()),
                "source_white_logical":int((~target).sum()),
                "source_interior_nonwhite_logical_distance_ge2":int(interior.sum()),
                "correct_owner_by_threshold":{
                    str(t):int(((count>=t)&target).sum()) for t in (5,7,9)
                },
                "interior_correct_owner_by_threshold":{
                    str(t):int(((count>=t)&interior).sum()) for t in (5,7,9)
                },
                "correct_owner_subpixel_histogram":{
                    str(t):int(((count==t)&target).sum()) for t in range(10)
                },
                "native_ink_on_original_white_alpha24_physical":
                    original_white_alpha24,
                "native_ink_on_protected_original_white_alpha24_physical":
                    published_metrics["protected_original_white_ink_alpha24_backing"],
                "holes_in_nonwhite_interior":holes,
                "face_roi_24x24_nonwhite":{
                    "logical_count":int(target[45:69,40:64].sum()),
                    "correct5":int(((count>=5)&target)[45:69,40:64].sum()),
                    "correct7":int(((count>=7)&target)[45:69,40:64].sum()),
                    "correct9":int(((count>=9)&target)[45:69,40:64].sum()),
                },
            }
            results[key]=stages
            density_visual(count,source_index,folder/(method+"_"+key+"_PHYSICAL_DENSITY.png"))
        final=results["STAGE_03_RELAXED_REPAIR"]
        if (final["correct_owner_by_threshold"]["5"] !=
            published["final_owner_correct"] or
            final["correct_owner_by_threshold"]["5"] !=
            final["source_nonwhite_logical"]):
            raise ValueError("BLOCKED_P4D16_NOT_FROZEN_P4D13_FINAL")
        output[method]={"stages":results,"original_rgb_from_pinned_p4d13":True}
        print("P4D16_ARTWORK_E3_ARCHIVE",method,
              final["correct_owner_by_threshold"],
              "interior_alpha_zero",final["holes_in_nonwhite_interior"][
                  "native_alpha_eq0_physical"],flush=True)
    if (output[METHODS[0]]["stages"]["STAGE_03_RELAXED_REPAIR"][
            "source_nonwhite_logical"]==output[METHODS[1]]["stages"][
                "STAGE_03_RELAXED_REPAIR"]["source_nonwhite_logical"]):
        raise ValueError("BLOCKED_P4D16_EF_NOT_DISTINCT")
    (folder/"ARTWORK_STAGES_NATIVE_DENSITY.json").write_text(
        json.dumps(output,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
    return output


def phase_plan(width:int,angle:int,length:int,phase:float)->list[dict]:
    if (width not in WIDTHS or angle not in ANGLES or
        length not in LENGTHS or phase not in PHASES):
        raise ValueError("BLOCKED_P4D16_PHASE_PLAN")
    strokes=p4d3.build_primary(width,angle,length)
    for stroke in strokes:
        for p in stroke["points"]:
            p["x"]=float(p["x"]+phase)
            p["y"]=float(p["y"]+phase)
    return strokes


def _segment_distance_sq(points:list[dict],x:np.ndarray,y:np.ndarray,
                         shift:float)->np.ndarray:
    ax=float(points[0]["x"])+shift
    ay=float(points[0]["y"])+shift
    dx=float(points[1]["x"])-float(points[0]["x"])
    dy=float(points[1]["y"])-float(points[0]["y"])
    if dx*dx+dy*dy==0:
        return (x-ax)**2+(y-ay)**2
    t=np.clip(((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy),0,1)
    return (x-ax-t*dx)**2+(y-ay-t*dy)**2


def predict_alpha(points:list[dict],width:int,left:int,top:int,
                  mode:str)->np.ndarray:
    """MODEL_ONLY physical alpha: binary capsule or 8×8 area sampling."""
    if (width not in WIDTHS or len(points)!=2 or mode not in
        ("naive","source_halfpixel","area8") or
        not all(np.isfinite(p[k]) for p in points for k in ("x","y"))):
        raise ValueError("BLOCKED_P4D16_MODEL_INPUT")
    shift=0.5 if mode!="naive" and width in (1,3) else 0.
    xbase=np.arange(SIDE,dtype=np.float64)+left
    ybase=np.arange(SIDE,dtype=np.float64)+top
    radius_sq=(width/2.)**2
    if mode!="area8":
        x=(xbase[None,:]+.5)/SCALE
        y=(ybase[:,None]+.5)/SCALE
        return (_segment_distance_sq(points,x,y,shift)<=radius_sq).astype(np.uint8)*255
    count=np.zeros((SIDE,SIDE),np.uint8)
    for sy in range(8):
        y=(ybase[:,None]+(sy+.5)/8.)/SCALE
        for sx in range(8):
            x=(xbase[None,:]+(sx+.5)/8.)/SCALE
            count+=(_segment_distance_sq(points,x,y,shift)<=radius_sq).astype(np.uint8)
    return np.rint(count.astype(np.float32)*(255./64)).astype(np.uint8)


def mask_accuracy(pred:np.ndarray,actual:np.ndarray)->dict:
    if (pred.shape!=actual.shape or pred.shape!=(SIDE,SIDE) or
        pred.dtype!=np.uint8 or actual.dtype!=np.uint8):
        raise ValueError("BLOCKED_P4D16_ALPHA_ARRAY")
    union_alpha=(pred>0)|(actual>0)
    diff=np.abs(pred.astype(np.int16)-actual.astype(np.int16))
    out={"rgba_predicted":False,
         "alpha_mae_in_nonzero_union":float(diff[union_alpha].mean())
          if np.any(union_alpha) else 0.}
    for threshold in (1,24):
        a=pred>=threshold;b=actual>=threshold
        tp=int((a&b).sum());fp=int((a&~b).sum());fn=int((~a&b).sum())
        out[f"alpha{threshold}"]={
            "IoU":float(tp/(tp+fp+fn)) if tp+fp+fn else 1.,
            "false_positive":fp,"false_negative":fn,
            "exact_mask":fp+fn==0,
        }
    return out


def sample_summary(rows:list[dict])->dict:
    if not rows: raise ValueError("BLOCKED_P4D16_EMPTY_GROUP")
    out={"n":len(rows),
         "translated_rgba_identical":sum(r["native_translated_all10_identical"] for r in rows)}
    for mode in ("naive","source_halfpixel","area8"):
        out[mode]={
            "mean_IoU_alpha24":float(np.mean([r["models"][mode]["alpha24"]["IoU"] for r in rows])),
            "mean_IoU_alpha1":float(np.mean([r["models"][mode]["alpha1"]["IoU"] for r in rows])),
            "mean_alpha_MAE_union":float(np.mean([r["models"][mode]["alpha_mae_in_nonzero_union"] for r in rows])),
            "exact_alpha24_masks":sum(r["models"][mode]["alpha24"]["exact_mask"] for r in rows),
            "FP_alpha24":sum(r["models"][mode]["alpha24"]["false_positive"] for r in rows),
            "FN_alpha24":sum(r["models"][mode]["alpha24"]["false_negative"] for r in rows),
        }
    return out


def phase_native_run(workspace:Path,engine_js:Path,renderer:Path,
                     folder:Path)->dict:
    if (p4b1.git_blob(renderer.read_bytes())!=RENDERER_BLOB or
        p4b1.git_blob(engine_js.read_bytes())!=GAME_BLOB or
        p4b1.git_blob(Path(p4d3.__file__).read_bytes())!=PARENT_P4D3_BLOB):
        raise ValueError("BLOCKED_P4D16_FROZEN_RENDERER_AND_SOURCE")
    folder.mkdir(parents=True,exist_ok=True)
    cases=[]; repeats=0
    with p4b7.native_egret_session(workspace) as driver:
        driver.set_script_timeout(180)
        browser={"name":driver.capabilities.get("browserName"),
                 "version":driver.capabilities.get("browserVersion"),
                 "platform":driver.capabilities.get("platformName")}
        blank_response=driver.execute_script(p4d3.CMD,[])
        blank,meta=p4d3.read_webgl_result(blank_response,folder,"REAL_EGRET_BLANK")
        if (blank.shape!=p4d3.NATIVE_SHAPE or
            meta.get("schema")!="ENGINE001_B1R_P4A2_BLANK_WEBGL" or
            np.any(blank[:,:,3])):
            raise ValueError("BLOCKED_P4D16_NATIVE_BLANK")
        with (folder/"CASES_APPEND_ONLY.jsonl").open("a",encoding="utf8") as ledger:
            for width in WIDTHS:
                for angle in ANGLES:
                    for length in LENGTHS:
                        for phase in PHASES:
                            case=f"W{width:02d}_A{angle:03d}_L{length:02d}_P{int(phase*1000):03d}"
                            plan=phase_plan(width,angle,length,phase)
                            (folder/(case+"_PLAN.json")).write_text(
                                json.dumps(plan,ensure_ascii=False,allow_nan=False)+"\n","utf8")
                            native,meta=p4d3.read_scene(driver,folder,case,plan)
                            if (native.shape!=p4d3.NATIVE_SHAPE or
                                meta.get("renderer")!="real Egret 5.4.1 BoardPane/WebGLRenderer" or
                                meta.get("stroke_count")!=21):
                                raise ValueError("BLOCKED_P4D16_NOT_TRUE_NATIVE")
                            copies=p4d3.scores(native)
                            ref=p4d3.roi(native,*p4d3.CENTERS[0])
                            left=(p4d3.CENTERS[0][0]-p4d3.HALF)*SCALE
                            top=(p4d3.CENTERS[0][1]-p4d3.HALF)*SCALE
                            actual=ref[:,:,3]
                            models={
                                mode:mask_accuracy(predict_alpha(
                                    plan[0]["points"],width,left,top,mode),actual)
                                for mode in ("naive","source_halfpixel","area8")
                            }
                            row={"case":case,"width":width,"angle":angle,
                                 "length":length,"phase":phase,
                                 "native_png_sha256":meta["source_png_sha256"],
                                 "native_translated_all10_identical":
                                     bool(copies["isolated10_all_exact_rgba"]),
                                 "native_translated_mismatch_pixels":
                                     int(copies["isolated10_mismatch_pixels_total"]),
                                 "native_translated_alpha24_XOR":
                                     int(sum(v["alpha24_xor_pixels"] for v in
                                         copies["isolated10_mismatch_each"])),
                                 "models":models}
                            cases.append(row)
                            ledger.write(json.dumps(row,allow_nan=False)+"\n")
                            ledger.flush()
                            if angle==0 and length==4 and phase==0.:
                                again,meta2=p4d3.read_scene(
                                    driver,folder,case+"_EXACT_REPLAY",plan)
                                if (not np.array_equal(native,again) or
                                    meta2["source_png_sha256"]!=meta["source_png_sha256"]):
                                    raise ValueError("BLOCKED_P4D16_CROSS_RENDER_NOT_EXACT")
                                repeats+=1
                    print("P4D16_NATIVE_EGRET",width,angle,
                          "cases",len(cases),"replays",repeats,flush=True)
    if len(cases)!=EXPECTED_PHASE_CASES or repeats!=len(WIDTHS):
        raise ValueError("BLOCKED_P4D16_PHASE_SAMPLE_INCOMPLETE")
    result={
        "native_scene_count":1+len(cases)+repeats,
        "native_case_count":len(cases),
        "exact_scene_replays":repeats,
        "native_blank_zero_alpha":True,
        "native_browser_environment":browser,
        "all":sample_summary(cases),
        "phase_0_baseline":sample_summary([r for r in cases if r["phase"]==0.]),
        "phase_1of8":sample_summary([r for r in cases if r["phase"]==.125]),
        "phase_1of2_heldout":sample_summary([r for r in cases if r["phase"]==.5]),
        "by_width":{str(w):sample_summary([r for r in cases if r["width"]==w])
                    for w in WIDTHS},
        "by_angle":{str(a):sample_summary([r for r in cases if r["angle"]==a])
                    for a in ANGLES},
        "mathematical_model_only_never_native_quality_pass":True,
        "all_phase_case_rows":cases,
    }
    (folder/"NATIVE_PHASE_SUMMARY.json").write_text(
        json.dumps(result,indent=2,allow_nan=False)+"\n","utf8")
    return result


def run(parent_path:Path,output:Path,workspace:Path|None=None,
        engine_js:Path|None=None,renderer:Path|None=None,
        density_only:bool=False)->dict:
    if output.exists():
        raise ValueError("BLOCKED_P4D16_OUTPUT_EXISTS")
    if not density_only:
        if not all((workspace,engine_js,renderer)):
            raise ValueError("BLOCKED_P4D16_MISSING_EGRET_PATHS")
        prereg=workspace/"AutoDraw_Stage20"/"docs"/PREREG
        if not prereg.is_file() or EXPERIMENT not in prereg.read_text("utf8"):
            raise ValueError("BLOCKED_P4D16_NOT_PREREG")
    frozen=FrozenArtifact(parent_path)
    try:
        report=frozen.check()
        output.mkdir(parents=True,exist_ok=True)
        density=density_audit(frozen,report,output/"density")
    finally:
        frozen.close()
    phase=None if density_only else phase_native_run(
        workspace,engine_js,renderer,output/"phase")
    result={
        "experiment":EXPERIMENT,
        "technical_result":("DENSITY_ONLY_FROM_FROZEN_E3" if density_only
                            else "P4D16_FULL_TRUE_NATIVE_AND_ARCHIVED_E3"),
        "archived_p4d13_sha":PARENT_P4D13_SHA,
        "archived_p4d13_members_sha256_verified":39,
        "original_source_sha256":p4d0.SOURCE_SHA,
        "renderer_blob":RENDERER_BLOB,
        "game_bundle_blob":GAME_BLOB,
        "native_artwork_density":density,
        "new_native_phase":phase,
        "new_native_E3":("NOT_RUN" if density_only else "PASS_TECHNICAL_ONLY"),
        "E4_live":"NOT_RUN",
        "E5_independent_quality":"NOT_RUN",
        "exact_run_bound_CHALK":None,
        "quality_gate_protected0":"NOT_PASSED_BY_P4D13",
        "production_promotion":False,
        "github_sha":os.getenv("GITHUB_SHA"),
        "github_run_id":os.getenv("GITHUB_RUN_ID"),
    }
    result["members_sha256"]={
        str(p.relative_to(output)).replace("\\","/"):digest(p.read_bytes())
        for p in sorted(output.rglob("*")) if p.is_file()
    }
    (output/"report.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
    return result


if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("--source-artifact",type=Path,required=True)
    cli.add_argument("--output",type=Path,required=True)
    cli.add_argument("--workspace",type=Path)
    cli.add_argument("--engine-js",type=Path)
    cli.add_argument("--renderer",type=Path)
    cli.add_argument("--density-only",action="store_true")
    args=cli.parse_args()
    run(args.source_artifact,args.output,args.workspace,args.engine_js,
        args.renderer,args.density_only)

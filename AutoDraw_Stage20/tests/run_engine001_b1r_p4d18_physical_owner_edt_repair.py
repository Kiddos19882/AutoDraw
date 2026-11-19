#!/usr/bin/env python3
"""P4D18 true Egret E/F physical owner-boundary EDT micro-repair, research-only.

Uses frozen E3 P4D17 final plan/native as exact input. No production changes.
"""
from __future__ import annotations
import argparse
from io import BytesIO
import hashlib
import json
import os
from pathlib import Path
from zipfile import ZipFile

import cv2
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import distance_transform_edt

import run_engine001_b1r_p3b_engine128_adaptive32 as p3b
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
import run_engine001_b1r_p4c0_full_multicolor_native_preview as p4c0
import run_engine001_b1r_p4d0_unbounded_adaptive_vs_scanline_native as p4d0
import run_engine001_b1r_p4d13_full_original_relaxed_finish as p4d13
import run_engine001_b1r_p4d17_owner_physical_repair as p4d17
from run_engine001_b1r_p2_joint_region_outline import digest

EXPERIMENT="ENGINE001_B1R_P4D18_PHYSICAL_OWNER_EDT_REPAIR_V1"
PREREG="ENGINE001_B1R_P4D18_EDT_PHYSICAL_OWNER_REPAIR_PREREG_2026-11-19.md"
PARENT_SHA="de3e3610c12e8202bed8fa249803c3a91b4f3cad"
RENDERER_BLOB="76d950e0a8911888a9df3b675b866519ecf7bba4"
GAME_BLOB="46cc74de00b6cb5d207b1e1a2ffcd81613b6d388"
METHODS=("E_SOBEL90","F_SOBEL90_LAB12")
ARMS=("BASE_P4D17","EDT_MARGIN_2P7","EDT_MARGIN_2P1","EDT_MARGIN_1P6")
MARGINS={"EDT_MARGIN_2P7":2.7,"EDT_MARGIN_2P1":2.1,"EDT_MARGIN_1P6":1.6}
LIMIT=600
WHITE=6
ALPHA=24
RGB_TOL=32
X0=155

class OriginalP4D17:
    def __init__(self,path:Path):
        if not path.exists(): raise ValueError("BLOCKED_P4D18_PARENT_NOT_FOUND")
        self.path=path
        self.zip=ZipFile(path) if path.is_file() else None
        if self.zip is None and not path.is_dir():
            raise ValueError("BLOCKED_P4D18_PARENT_NOT_FILE_OR_DIRECTORY")
    def read(self,name:str)->bytes:
        if name.startswith("/") or ".." in Path(name).parts:
            raise ValueError("BLOCKED_P4D18_PARENT_PATH")
        return self.zip.read(name) if self.zip else (self.path/name).read_bytes()
    def image(self,name:str,mode:str,shape:tuple[int,int])->np.ndarray:
        with Image.open(BytesIO(self.read(name))) as im:
            if im.mode!=mode or im.size!=shape:
                raise ValueError("BLOCKED_P4D18_PARENT_NATIVE_IMAGE_FORMAT "+name)
            return np.asarray(im).copy()
    def validate(self)->dict:
        if self.zip is not None and self.zip.testzip() is not None:
            raise ValueError("BLOCKED_P4D18_PARENT_CRC")
        r=json.loads(self.read("report.json"))
        if (r.get("github_sha")!=PARENT_SHA or
            r.get("experiment")!=p4d17.EXPERIMENT or
            r.get("game_bundle_blob")!=GAME_BLOB or
            r.get("renderer_blob")!=RENDERER_BLOB or
            len(r.get("members_sha256",{}))!=34 or
            r.get("native_full_scene_count")!=9 or
            not r.get("native_blank_alpha0") or
            r.get("browser",{}).get("browserVersion")!="159.0" or
            r.get("no_G32_V44_used") is not True):
            raise ValueError("BLOCKED_P4D18_PARENT_PROVENANCE")
        for n,sha in r["members_sha256"].items():
            if hashlib.sha256(self.read(n)).hexdigest()!=sha:
                raise ValueError("BLOCKED_P4D18_PARENT_HASH "+n)
        return r
    def close(self):
        if self.zip is not None: self.zip.close()


def physical_owner_distance(idx:np.ndarray)->np.ndarray:
    if idx.shape!=(240,150) or idx.dtype!=np.uint8:
        raise ValueError("BLOCKED_P4D18_OWNER_SOURCE_SHAPE")
    owner=np.repeat(np.repeat(idx,3,0),3,1)
    distance=np.zeros(owner.shape,np.float32)
    for color in np.unique(owner):
        if int(color)==WHITE:continue
        mask=owner==color
        d=distance_transform_edt(mask).astype(np.float32)
        distance[mask]=d[mask]
    return distance


def repair_physical_edt(index:np.ndarray,palette:np.ndarray,
                        baseline:np.ndarray,margin:float)->tuple[list[dict],dict]:
    if margin not in MARGINS.values() or baseline.shape!=(720,1380,4):
        raise ValueError("BLOCKED_P4D18_EDT_BAD_INPUT")
    good,count,diff=p4d17.physical_owner_score(baseline,index,palette)
    ink=baseline[:,X0*3:(X0+150)*3,:]
    dist=physical_owner_distance(index)
    mask=np.repeat(np.repeat(index!=WHITE,3,0),3,1)
    physical=(~good)&mask&(dist>margin)
    per_cell=physical.reshape(240,3,150,3).sum(axis=(1,3))
    eligible=np.argwhere(per_cell>0)
    cells=sorted((int(y),int(x)) for y,x in eligible)
    cells.sort(key=lambda p:(int(count[p]),p[0],p[1]))
    new=[];hole=0;wrong=0
    for y,x in cells[:LIMIT]:
        candidates=np.argwhere(physical[3*y:3*y+3,3*x:3*x+3])
        if not len(candidates):
            raise ValueError("BLOCKED_P4D18_PHYSICAL_CANDIDATE_DRIFT")
        def ordering(p):
            a,b=(int(p[0]),int(p[1]))
            return (int(ink[3*y+a,3*x+b,3]),-int(diff[3*y+a,3*x+b]),a,b)
        yy,xx=map(int,min(candidates,key=ordering))
        alpha=int(ink[3*y+yy,3*x+xx,3])
        hole+=int(alpha==0)
        wrong+=int(alpha>=24)
        # Source Egret halfpixel +.5 must be removed from desired pixel center.
        desired_x=x+(xx+.5)/3
        desired_y=y+(yy+.5)/3
        owner=int(index[y,x])
        s=p4d0._stroke(owner,palette,desired_x-.5-.025,
                       desired_x-.5+.025,y,width=1)
        for p in s["points"]:
            p["y"]=float(desired_y-.5)
        new.append(s)
    return p4c0.renumber(new),{
        "distance_owner_physical_margin":margin,
        "eligible_logical_cells":int(len(cells)),
        "eligible_wrong_physical_backing":int(physical.sum()),
        "new_width1_strokes":len(new),
        "target_had_alpha0":hole,
        "target_had_alpha24_wrong_color":wrong,
        "scientific_not_protected_quality_pass":True,
        "no_original_source_recolorization":True,
    }


def nonwhite_interior_alpha0(native:np.ndarray,index:np.ndarray)->dict:
    if native.shape!=(720,1380,4) or index.shape!=(240,150):
        raise ValueError("BLOCKED_P4D18_INTERIOR_SHAPE")
    inside=cv2.distanceTransform((index!=WHITE).astype(np.uint8),
                                 cv2.DIST_L2,cv2.DIST_MASK_PRECISE)>=2
    backing=np.repeat(np.repeat(inside,3,0),3,1)
    cropped=native[:,X0*3:(X0+150)*3,3]
    return {
        "interior_nonwhite_alpha0":int(((cropped==0)&backing).sum()),
        "interior_nonwhite_below24":int(((cropped<24)&backing).sum()),
        "interior_nonwhite_physical_total":int(backing.sum()),
    }


def compare_original_rgb(original:np.ndarray,target:np.ndarray,
                         native:dict[str,Image.Image],folder:Path):
    entries=[("ORIGINAL RGB",Image.fromarray(original).resize(
                         (450,720),Image.Resampling.NEAREST)),
             ("B1-R OWNER TARGET",Image.fromarray(target).resize(
                         (450,720),Image.Resampling.NEAREST))]
    entries.extend((key.replace("_"," "),native[key]) for key in ARMS)
    picture=Image.new("RGB",(len(entries)*450,758),"white")
    draw=ImageDraw.Draw(picture)
    for k,(name,im) in enumerate(entries):
        picture.paste(im,(k*450,32))
        draw.text((k*450+5,10),name,fill="black")
    picture.save(folder/"P4D18_ORIGINAL_VS_4_EGRET_NATIVE_PHYSICAL_ARMS.png")
    face=Image.new("RGB",(len(entries)*240,264),"white")
    pen=ImageDraw.Draw(face)
    for i,(name,im) in enumerate(entries):
        crop=im.crop((40*3,45*3,64*3,69*3)).resize(
                  (240,240),Image.Resampling.NEAREST)
        face.paste(crop,(i*240,24))
        pen.text((i*240+4,6),name,fill="black")
    face.save(folder/"P4D18_FACE_EYES_4_ARMS.png")


def run(workspace:Path,engine_js:Path,renderer:Path,
        source_artifact:Path,output:Path)->dict:
    if output.exists():
        raise ValueError("BLOCKED_P4D18_OUTPUT_EXISTS")
    if p4b1.git_blob(engine_js.read_bytes())!=GAME_BLOB or (
        p4b1.git_blob(renderer.read_bytes())!=RENDERER_BLOB):
        raise ValueError("BLOCKED_P4D18_RENDERER_GAME_PIN")
    prereg=workspace/"AutoDraw_Stage20"/"docs"/PREREG
    if not prereg.is_file() or EXPERIMENT not in prereg.read_text("utf8"):
        raise ValueError("BLOCKED_P4D18_E0_NOT_FROZEN")
    parent=OriginalP4D17(source_artifact)
    try:
        history=parent.validate()
        original=parent.image("ORIGINAL_RGB_LOGICAL.png","RGB",(150,240))
        data={}
        for method in METHODS:
            idx=parent.image(method+"/SOURCE_OWNER_INDEX.png","L",(150,240))
            rgb=parent.image(method+"/SOURCE_OWNER_RGB.png","RGB",(150,240))
            plan=json.loads(parent.read(method+"/INTERIOR_SUBPIXEL_REPAIR_PLAN.json"))
            original_native=parent.image(
                method+"/INTERIOR_SUBPIXEL_REPAIR_REAL_NATIVE.png","RGBA",(1380,720))
            if (len(plan)!=history["methods"][method]["results"][
                    "INTERIOR_SUBPIXEL_REPAIR"]["strokes"] or
                int((idx!=WHITE).sum())!=history["methods"][method]["results"][
                    "BASELINE"]["target_nonwhite_logical"]):
                raise ValueError("BLOCKED_P4D18_PARENT_PLAN_DRIFT")
            data[method]=(idx,rgb,plan,original_native)
    finally:
        parent.close()
    palette,_=p3b.read_engine_palette(engine_js)
    if any(not np.array_equal(palette[idx],rgb) for idx,rgb,_,_ in data.values()):
        raise ValueError("BLOCKED_P4D18_NOT_CURRENT_GAME_PALETTE")
    output.mkdir(parents=True)
    Image.fromarray(original).save(output/"ORIGINAL_RGB_LOGICAL.png")
    methods={}
    with p4d0.patched_test_renderer(renderer):
        with p4b7.native_egret_session(workspace) as driver:
            driver.set_script_timeout(900)
            browser={
                "browserName":driver.capabilities.get("browserName"),
                "browserVersion":driver.capabilities.get("browserVersion"),
                "platformName":driver.capabilities.get("platformName")}
            blank,_=p4d13.render(driver,output,"REAL_EGRET_BLANK",[])
            if np.any(blank[:,:,3]):
                raise ValueError("BLOCKED_P4D18_NATIVE_BLANK")
            for method,(idx,rgb,source_plan,pinned) in data.items():
                folder=output/method;folder.mkdir()
                Image.fromarray(idx).save(folder/"SOURCE_OWNER_INDEX.png")
                Image.fromarray(rgb).save(folder/"SOURCE_OWNER_RGB.png")
                metrics={};previews={};notes={}
                for name in ARMS:
                    if name=="BASE_P4D17":
                        candidate=list(source_plan)
                        notes[name]={"strokes_added":0,"source_unmodified":True}
                    else:
                        new,meta=repair_physical_edt(idx,palette,pinned,MARGINS[name])
                        candidate=list(source_plan)+new
                        notes[name]=meta
                    candidate=p4c0.renumber(candidate)
                    (folder/(name+"_PLAN.json")).write_text(
                         json.dumps(candidate,ensure_ascii=False,indent=2)+"\n","utf8")
                    native,native_meta=p4d13.render(driver,folder,name+"_REAL_NATIVE",candidate)
                    s=p4d17.score(native,idx,palette)
                    s.update(nonwhite_interior_alpha0(native,idx))
                    s["strokes"]=len(candidate)
                    s["native_png_sha256"]=native_meta["source_sha256"]
                    metrics[name]=s
                    previews[name]=p4c0.preview_native(native)
                    previews[name].save(folder/(name+"_PREVIEW.png"))
                    print("P4D18_E3",method,name,"correct_physical",
                          s["correct_owner_backing_pixels"],
                          "logical5",s["logical_correct5"],
                          "holes",s["interior_nonwhite_alpha0"],
                          "white",s["original_white_alpha24_backing"],
                          flush=True)
                baseline=metrics["BASE_P4D17"]
                choices=[name for name in ARMS if (
                    p4d17.baseline_guard(baseline,metrics[name]) and
                    metrics[name]["correct_owner_backing_pixels"]>=
                    baseline["correct_owner_backing_pixels"])]
                if not choices:raise ValueError("BLOCKED_P4D18_BASELINE_NOT_VALID")
                selected=max(choices,key=lambda k:metrics[k]["correct_owner_backing_pixels"])
                compare_original_rgb(original,rgb,previews,folder)
                methods[method]={
                    "results":metrics,"plans":notes,
                    "best_eligible_arm":selected,
                    "best_eligible_physical_gain":
                        metrics[selected]["correct_owner_backing_pixels"]-
                        baseline["correct_owner_backing_pixels"],
                    "best_eligible_reduces_interior_alpha0":
                        metrics[selected]["interior_nonwhite_alpha0"]<
                        baseline["interior_nonwhite_alpha0"],
                    "full_protected_foreign_owner_gate":"NOT_PROVEN",
                }
    if p4b1.git_blob(renderer.read_bytes())!=RENDERER_BLOB:
        raise ValueError("BLOCKED_P4D18_SCOPED_RENDERER_NOT_RESTORED")
    report={
        "experiment":EXPERIMENT,
        "parent_P4D17_github_sha":PARENT_SHA,
        "p4d17_manifest_members_verified":34,
        "original_source_sha256":p4d0.SOURCE_SHA,
        "renderer_git_blob":RENDERER_BLOB,
        "game_bundle_git_blob":GAME_BLOB,
        "native_Egret_renderer":"real Egret 5.4.1 BoardPane/WebGLRenderer",
        "native_browser":browser,
        "native_full_scenes":9,
        "blank_true_native_alpha0":True,
        "all_arms":list(ARMS),
        "method_results":methods,
        "technical_result":"P4D18_REAL_NATIVE_EF_EDT_MARGIN_DIAGNOSTIC",
        "protection_original_white_not_relaxed":True,
        "protected_foreign_zero":"NOT_PROVEN",
        "production_promotion":False,
        "E4_live":"NOT_RUN","E5_independent":"NOT_RUN",
        "exact_run_bound_CHALK":None,
        "github_sha":os.getenv("GITHUB_SHA"),
        "github_run_id":os.getenv("GITHUB_RUN_ID"),
    }
    report["members_sha256"]={
        str(path.relative_to(output)).replace("\\","/"):digest(path.read_bytes())
        for path in sorted(output.rglob("*")) if path.is_file()
    }
    (output/"report.json").write_text(json.dumps(
        report,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
    return report

if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("--workspace",required=True,type=Path)
    cli.add_argument("--engine-js",required=True,type=Path)
    cli.add_argument("--renderer",required=True,type=Path)
    cli.add_argument("--source-artifact",required=True,type=Path)
    cli.add_argument("--output",required=True,type=Path)
    a=cli.parse_args()
    run(a.workspace,a.engine_js,a.renderer,a.source_artifact,a.output)

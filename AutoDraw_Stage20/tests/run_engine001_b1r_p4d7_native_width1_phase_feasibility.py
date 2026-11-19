#!/usr/bin/env python3
"""P4D7: actual Egret single-width1 fractional (x,y) placement feasibility.

Protect original P3D eye-region owner colors; never use simulated brush masks
as E3 evidence. All 21 exact predetermined source pixels x 66 positions.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import tempfile

import cv2
import numpy as np
from PIL import Image, ImageDraw

import run_engine001_b1r_p3d_source_edge_mask_ablation as p3d
import run_engine001_b1r_p3b_engine128_adaptive32 as p3b
import run_engine001_b1r_p4b4_boundary_tolerance_sweep as p4b4
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
import run_engine001_b1r_p4c0_full_multicolor_native_preview as p4c0
import run_engine001_b1r_p4d5_pixel_state_native_feedback as p4d5
from run_engine001_b1r_p1_fullrgb_edge_aware import check_source
from run_engine001_b1r_p2_joint_region_outline import digest

EXPERIMENT="ENGINE001_B1R_P4D7_NATIVE_WIDTH1_SUBPIXEL_PHASE_FEASIBILITY_V1"
PREREG="ENGINE001_B1R_P4D7_NATIVE_SUBPIXEL_PHASE_FEASIBILITY_PREREG_2026-11-19.md"
METHODS=p4d5.METHODS
SOURCE=p4d5.SOURCE
CROP=p4d5.CROP
WHITE=p4d5.WHITE
X0=p4d5.X0
SCALE=p4d5.SCALE
ALPHA=p4d5.ALPHA
PHASES=(0,.125,.25,.375,.5,.625,.75,.875)
EXPECTED_SAMPLES=21
VARIANTS=tuple((f"GRID_X{ix}_Y{iy}",px,py)
               for ix,px in enumerate(PHASES)
               for iy,py in enumerate(PHASES)) + (
                   ("P4D5_ORIGINAL_INPUT",None,None),
                   ("P4D6_CENTERED_INPUT",None,None))
EXPECTED_VARIANTS=66
NATIVE_SHAPE=p4d5.BOARD_SHAPE


def owner_samples(index:np.ndarray)->list[dict]:
    """One earliest min distance and earliest max distance per source owner."""
    if index.shape!=(240,150) or index.dtype!=np.uint8:
        raise ValueError("BLOCKED_P4D7_SOURCE_INDEX_FORMAT")
    roi=p4d5.crop_target(index)
    owners=sorted(int(x) for x in np.unique(index[roi]) if int(x)!=WHITE)
    samples=[]
    for owner in owners:
        present=index==owner
        distance=cv2.distanceTransform(
            np.pad(present.astype(np.uint8),1),
            cv2.DIST_L2,cv2.DIST_MASK_PRECISE)[1:-1,1:-1]
        coords=np.argwhere(roi & present)
        if len(coords)==0:
            raise ValueError("BLOCKED_P4D7_EMPTY_OWNER")
        min_pt=coords[int(np.argmin(distance[coords[:,0],coords[:,1]]))]
        max_pt=coords[int(np.argmax(distance[coords[:,0],coords[:,1]]))]
        for kind,pt in (("minimum_clearance",min_pt),("maximum_clearance",max_pt)):
            y,x=map(int,pt)
            if any(z["owner"]==owner and z["x"]==x and z["y"]==y for z in samples):
                continue
            samples.append({"owner":owner,"x":x,"y":y,
                            "source_clearance":float(distance[y,x]),
                            "position_reason":kind,
                            "sample_id":f"OWNER{owner:03d}_X{x:03d}_Y{y:03d}"})
    if len(owners)!=20 or len(samples)!=EXPECTED_SAMPLES:
        raise ValueError("BLOCKED_P4D7_FROZEN_SOURCE_21_SAMPLE_DRIFT")
    if not p4b4.source_critical_rois()[roi].all():
        raise ValueError("BLOCKED_P4D7_CROP_NOT_FROZEN_PROTECTED_FACE")
    return samples


def phase_stroke(sample:dict,variant:tuple,palette:np.ndarray)->dict:
    name,dx,dy=variant
    x,y,owner=sample["x"],sample["y"],sample["owner"]
    if name=="P4D5_ORIGINAL_INPUT":
        p0=(x+.125,y)
        p1=(x+.375,y)
    elif name=="P4D6_CENTERED_INPUT":
        p0=(x+.49,y+.5)
        p1=(x+.51,y+.5)
    else:
        if dx not in PHASES or dy not in PHASES or not name.startswith("GRID_"):
            raise ValueError("BLOCKED_P4D7_BAD_PHASE")
        p0=(x+dx-.01,y+dy)
        p1=(x+dx+.01,y+dy)
    return p4d5.make_stroke(owner,palette,1,*p0,*p1)


def full_backing_source_mask(mask:np.ndarray)->np.ndarray:
    if mask.shape!=(240,150):
        raise ValueError("BLOCKED_P4D7_SOURCE_MASK")
    board=np.zeros(NATIVE_SHAPE[:2],bool)
    board[:,X0*SCALE:(X0+150)*SCALE]=np.repeat(
        np.repeat(mask,SCALE,0),SCALE,1)
    return board


def actual_native_single_metrics(native:np.ndarray,index:np.ndarray,
                                 palette:np.ndarray,protected:np.ndarray,
                                 sample:dict)->dict:
    """No translated stamps; evaluate exact full-board Egret RGBA image."""
    if (native.shape!=NATIVE_SHAPE or native.dtype!=np.uint8 or
        index.shape!=(240,150) or protected.shape!=(240,150)):
        raise ValueError("BLOCKED_P4D7_NATIVE_OR_MASK_SHAPE")
    owner=int(sample["owner"])
    own=full_backing_source_mask(index==owner)
    target_white=full_backing_source_mask(index==WHITE)
    protected_other=full_backing_source_mask(protected & (index!=owner))
    mask=native[:,:,3]>=ALPHA
    foreign=mask & ~own
    white=foreign & target_white
    protected_foreign=foreign & protected_other
    alpha1_foreign=(native[:,:,3]>0) & ~own
    x0,y0,x1,y1=CROP
    crop_full=np.zeros_like(mask)
    crop_full[y0*SCALE:y1*SCALE,
              (X0+x0)*SCALE:(X0+x1)*SCALE]=True
    same_outside=mask & own & ~crop_full
    state=p4d5.actual_state(native,index,palette)
    own_cell_correct=bool(state[sample["y"],sample["x"]])
    return {
        "native_alphage24_real_owner_ink_backing":int((mask&own).sum()),
        "native_alpha24_genuine_foreign_backing":int(foreign.sum()),
        "native_alpha24_protected_foreign_backing":int(protected_foreign.sum()),
        "native_alpha24_target_white_backing":int(white.sum()),
        "native_alpha1_genuine_foreign_backing":int(alpha1_foreign.sum()),
        "native_alpha24_same_owner_outside_pilot_crop_backing":int(same_outside.sum()),
        "native_exact_sample_cell_correct_5of9":own_cell_correct,
        "native_other_correct_logical_in_crop":int((state & (index==owner)).sum()),
        "native_alpha24_ink_total":int(mask.sum()),
        "phase_feasible":bool(own_cell_correct and not foreign.any() and
                              not protected_foreign.any()),
    }


def summarize(samples:list[dict],rows:list[dict])->list[dict]:
    by_sample=defaultdict(list)
    for row in rows:
        by_sample[row["sample_id"]].append(row)
    result=[]
    for source in samples:
        found=by_sample[source["sample_id"]]
        if len(found)!=EXPECTED_VARIANTS:
            raise ValueError("BLOCKED_P4D7_MISSING_PHASE_NATIVE_SCENES")
        feasible=[r for r in found if r["measured"]["phase_feasible"]]
        best=min(feasible,key=lambda r:(r["measured"]["native_alpha1_genuine_foreign_backing"],
                                       r["variant"])) if feasible else None
        result.append({**source,
            "real_native_variants":len(found),
            "feasible_variants":len(feasible),
            "has_safe_correct_native_phase":bool(feasible),
            "best_safe_variant":best["variant"] if best else None,
            "minimum_native_foreign_alpha24":min(
                x["measured"]["native_alpha24_genuine_foreign_backing"] for x in found),
            "max_target_correct_at_any_phase":any(
                x["measured"]["native_exact_sample_cell_correct_5of9"] for x in found),
            "P4D5_original_control_feasible":any(
                r["variant"]=="P4D5_ORIGINAL_INPUT" and
                r["measured"]["phase_feasible"] for r in found),
            "P4D6_centered_control_feasible":any(
                r["variant"]=="P4D6_CENTERED_INPUT" and
                r["measured"]["phase_feasible"] for r in found),
        })
    return result


def native_heatmap(samples:list[dict],rows:list[dict],output:Path):
    # Rectangles encode VERIFIED Egret outputs; not generated brush footprints.
    by_id={(r["sample_id"],r["variant"]):r for r in rows}
    cell=13;label=220;head=60
    canvas=Image.new("RGB",(label+8*cell+30,head+len(samples)*8*cell+35),
                     (248,248,248))
    painter=ImageDraw.Draw(canvas)
    painter.text((6,7),"Green=safe and correct; red=foreign; yellow=not enough owner ink",
                 fill=(20,20,20))
    for k,x in enumerate(PHASES):
        painter.text((label+k*cell,40),str(x),fill=(10,10,10))
    for i,s in enumerate(samples):
        y0=head+i*8*cell
        painter.text((6,y0+5),s["sample_id"],fill=(20,20,20))
        for ix in range(8):
            for iy in range(8):
                label_=f"GRID_X{ix}_Y{iy}"
                row=by_id[(s["sample_id"],label_)]
                m=row["measured"]
                color=(57,156,85) if m["phase_feasible"] else (
                    (209,71,65) if m["native_alpha24_genuine_foreign_backing"]>0
                    else (239,199,68))
                x0=label+ix*cell
                yy=y0+iy*cell
                painter.rectangle((x0,yy,x0+cell-2,yy+cell-2),fill=color)
    canvas.save(output/"REAL_EGRET_NATIVE_PHASE_FEASIBILITY_MAP.png")


def run(workspace:Path,source:Path,engine_js:Path,
        renderer:Path,output:Path):
    if output.exists():
        raise ValueError("BLOCKED_P4D7_EXISTING_OUTPUT")
    check_source(source)
    if (p4d5.p4b1.git_blob(renderer.read_bytes())!=p4d5.p4d0.RENDERER_BLOB or
        p4d5.p4b1.git_blob(engine_js.read_bytes())!=p3b.ENGINE_GIT_BLOB_SHA1):
        raise ValueError("BLOCKED_P4D7_FROZEN_EGRET_OR_ENGINE_CHANGED")
    if EXPERIMENT not in (workspace/"AutoDraw_Stage20"/"docs"/PREREG).read_text("utf8"):
        raise ValueError("BLOCKED_P4D7_NOT_PREREGISTERED")
    palette,_=p3b.read_engine_palette(engine_js)
    output.mkdir(parents=True)
    (output/"README_RU.txt").write_text(
        "P4D7: исходный RGB E/F, 21 замороженный source owner sample "
        "в защищённой female_face_eyes, кисть1, 8×8 дробные фазы + два "
        "точных контрольных варианта P4D5/P4D6. 1386 REAL Egret BoardPane/WebGL "
        "снимков + blank; каждая фаза отдельный рендер в настоящих координатах, "
        "сравнение per-owner native alpha24 чужого и 5/9 правильных цветов. "
        "Никакой model-only acceptance. ROI E/F одинаковый, F не дублируется "
        "как независимая выборка. Это не готовая заливка/не E4/не CHALK.\n","utf8")
    with tempfile.TemporaryDirectory(prefix="engine001-p4d7-source-") as tmp:
        fresh=Path(tmp)/"fresh_p3d"
        parent=p3d.run(source,engine_js,fresh)
        if (parent["experiment"]!=p3d.EXPERIMENT or
            parent["original_source_sha256"]!=p4d5.SOURCE_SHA or
            not parent["P3B_original_recomputed_in_current_run"] or
            parent["legacy_G32_V44_M1_used_as_source"]):
            raise ValueError("BLOCKED_P4D7_ORIGINAL_SOURCE_NOT_FRESH")
        source_index={}
        for method in METHODS:
            ix=np.asarray(Image.open(fresh/(SOURCE+"_"+method+"_ENGINE_INDICES.png")),
                          np.uint8).copy()
            selection=parent["all_results"][SOURCE]["selected_engine_indices"]
            p4c0.validate_source(ix,palette,selection)
            source_index[method]=ix
            Image.fromarray(ix[p4d5.CROP[1]:p4d5.CROP[3],
                               p4d5.CROP[0]:p4d5.CROP[2]]).save(
                                   output/(method+"_SOURCE_RGB_INDEX_CROP.png"))
        a,b=(source_index[name] for name in METHODS)
        x0,y0,x1,y1=CROP
        if not np.array_equal(a[y0:y1,x0:x1],b[y0:y1,x0:x1]):
            raise ValueError("BLOCKED_P4D7_FROZEN_IDENTICAL_EF_CROP_CHANGED")
        samples=owner_samples(a)
        protected=p4b4.source_critical_rois()
        rows=[]
        (output/"FIXED_ORIGINAL_SOURCE_SAMPLES.json").write_text(
            json.dumps(samples,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
        scenes=output/"REAL_EGRET_WIDTH1_PHASE_SCENES"
        scenes.mkdir()
        with p4b7.native_egret_session(workspace) as driver:
            driver.set_script_timeout(180)
            blank,_=p4d5._native(driver,output,"REAL_EGRET_BLANK",[])
            if np.any(blank[:,:,3]):
                raise ValueError("BLOCKED_P4D7_NATIVE_BLANK")
            with (output/"NATIVE_PHASE_RESULTS_APPEND_ONLY.jsonl").open("a",encoding="utf8") as ledger:
                for sample in samples:
                    each=scenes/sample["sample_id"]
                    each.mkdir()
                    for variant in VARIANTS:
                        name=variant[0]
                        stroke=phase_stroke(sample,variant,palette)
                        rgba,meta=p4d5._native(driver,each,name,[stroke])
                        measured=actual_native_single_metrics(
                            rgba,a,palette,protected,sample)
                        row={"sample_id":sample["sample_id"],
                            "owner":sample["owner"],"x":sample["x"],"y":sample["y"],
                            "variant":name,
                            "points":stroke["points"],"width":stroke["width"],
                            "colorIndex":stroke["colorIndex"],
                            "colorRgb":stroke["colorRgb"],
                            "exact_original_source_EF_duplicate":True,
                            "real_Egret_renderer":meta["renderer"],
                            "native_png_sha256":meta["source_sha256"],
                            "measured":measured}
                        rows.append(row)
                        ledger.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+"\n")
                        ledger.flush()
                    part=rows[-EXPECTED_VARIANTS:]
                    feasible=sum(x["measured"]["phase_feasible"] for x in part)
                    print("P4D7_NATIVE_OWNER_PIXEL",sample["sample_id"],
                          "feasible phases",feasible,"of",EXPECTED_VARIANTS,flush=True)
        results=summarize(samples,rows)
        native_heatmap(samples,rows,output)
        correct=sum(x["has_safe_correct_native_phase"] for x in results)
        native_scenes=len(rows)+1
        if len(samples)!=EXPECTED_SAMPLES or len(rows)!=EXPECTED_SAMPLES*EXPECTED_VARIANTS:
            raise ValueError("BLOCKED_P4D7_INCOMPLETE_FROZEN_MATRIX")
        report={
            "experiment":EXPERIMENT,
            "technical_result":"ALL_1387_TRUE_NATIVE_EGRET_PHASE_IMAGES_CAPTURED",
            "scientific_result":("SUBPIXEL_PHASE_YIELDS_SAFE_OWNER_PIXELS"
                                 if correct>0 else "NO_SAFE_CORRECT_PHASE_IN_TESTED_GRID"),
            "original_source_sha256":p4d5.SOURCE_SHA,
            "current_EF_source_original_only":True,
            "original_EF_frozen_ROI_index_exact_identical":True,
            "source_owner_20_and_fixed_samples_21":True,
            "selected_source":SOURCE,
            "protected_roi":"female_face_eyes",
            "protected_roi_source_fully_covers_test_crop":True,
            "crop_xyxy":list(CROP),
            "owners":20,"samples":len(samples),"phases_grid":list(PHASES),
            "variants_per_sample":len(VARIANTS),
            "native_scene_capture_total":native_scenes,
            "blank_native_zero":True,
            "native_true_renderer":"real Egret 5.4.1 BoardPane/WebGLRenderer",
            "renderer_git_blob":p4d5.p4d0.RENDERER_BLOB,
            "game_bundle_git_blob":p3b.ENGINE_GIT_BLOB_SHA1,
            "native_alpha24_foreign_owner_gate":0,
            "native_logical_color_5of9_gate":5,
            "safe_and_correct_samples":correct,
            "impossible_in_sampled_phase_set":len(samples)-correct,
            "number_P4D5_control_feasible":sum(x["P4D5_original_control_feasible"] for x in results),
            "number_P4D6_control_feasible":sum(x["P4D6_centered_control_feasible"] for x in results),
            "sample_results":results,
            "full_art_native_owner99_protected0_far3":"NOT_MEASURED",
            "E4_live":"NOT_RUN","E5_independent":"NOT_RUN",
            "exact_run_bound_CHALK":None,
            "production_promotion":False,
            "github_sha":os.getenv("GITHUB_SHA"),"github_run_id":os.getenv("GITHUB_RUN_ID"),
        }
        report["members_sha256"]={
            str(p.relative_to(output)).replace("\\","/"):digest(p.read_bytes())
            for p in sorted(output.rglob("*")) if p.is_file()
        }
        (output/"report.json").write_text(
            json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
        print("P4D7_REAL_NATIVE_PHASE_RESULT",correct,"feasible owner pixels of",
              len(samples),"native scenes",native_scenes,flush=True)
        return report


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--workspace",type=Path,required=True)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--engine-js",type=Path,required=True)
    parser.add_argument("--renderer",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    run(args.workspace,args.source,args.engine_js,args.renderer,args.output)

#!/usr/bin/env python3
"""P4D2: source-index owner-colored inner boundary as ordinary local fill strokes.

No global dark contour / no p4c0.source_joint_outline. All browser-quality
measurements are genuine Egret 5.4.1 BoardPane/WebGL, not model brush footprints.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import tempfile

import numpy as np
from PIL import Image, ImageDraw

import run_engine001_b1r_p3d_source_edge_mask_ablation as p3d
import run_engine001_b1r_p3b_engine128_adaptive32 as p3b
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
import run_engine001_b1r_p4c0_full_multicolor_native_preview as p4c0
import run_engine001_b1r_p4d0_unbounded_adaptive_vs_scanline_native as p4d0
from run_engine001_b1r_p1_fullrgb_edge_aware import check_source
from run_engine001_b1r_p2_joint_region_outline import digest
from run_engine001_complex_holdout_v5 import read_webgl_result

EXPERIMENT = "ENGINE001_B1R_P4D2_OWNER_COLORED_BOUNDARY_AS_FILL_NATIVE_V1"
PREREG = "ENGINE001_B1R_P4D2_OWNER_COLORED_BOUNDARY_AS_FILL_PREREG_2026-11-19.md"
P4D0_PARENT_BLOB = "cf4f0b0b8a1fef5879067f41901f2806758e81bd"
SOURCE = p4d0.SOURCE
SOURCE_SHA = p4d0.SOURCE_SHA
METHODS = p4d0.METHODS
ARMS = p4d0.ARMS
WHITE = p4d0.WHITE
STAGES = ("PAINT_ONLY_CONTROL", "OWNER_COLOR_BOUNDARY_AS_PAINT")
FIELDS = ("width", "colorIndex", "colorRgb", "points")


def identity(s: dict) -> str:
    """Stroke identity, excluding the sequential ID overwritten for native replay."""
    return json.dumps({key:s[key] for key in FIELDS}, sort_keys=True,
                      separators=(",",":"), allow_nan=False)


def owner_inner_boundary(index: np.ndarray) -> np.ndarray:
    """4-neighbor boundary INSIDE each nonwhite owner (never from legacy paths)."""
    if index.shape != (240, 150) or index.dtype != np.uint8:
        raise ValueError("BLOCKED_P4D2_INVALID_ORIGINAL_INDEX")
    up = np.zeros_like(index, np.bool_)
    dn = np.zeros_like(index, np.bool_)
    le = np.zeros_like(index, np.bool_)
    ri = np.zeros_like(index, np.bool_)
    up[1:] = index[1:] == index[:-1]
    dn[:-1] = index[:-1] == index[1:]
    le[:, 1:] = index[:, 1:] == index[:, :-1]
    ri[:, :-1] = index[:, :-1] == index[:, 1:]
    return (index != WHITE) & ~(up & dn & le & ri)


def _rgbpack(color: np.ndarray) -> int:
    return (int(color[0])<<16) | (int(color[1])<<8) | int(color[2])


def source_boundary_runs(index: np.ndarray, palette: np.ndarray):
    """Maximal horizontal owner-colored inner-edge strokes and provenance runs."""
    edge = owner_inner_boundary(index)
    if palette.shape != (128,3) or palette.dtype != np.uint8:
        raise ValueError("BLOCKED_P4D2_PALETTE")
    entries = []
    for y in range(index.shape[0]):
        x = 0
        while x < index.shape[1]:
            if not edge[y,x]:
                x += 1
                continue
            first = x
            owner = int(index[y,x])
            if owner == WHITE:
                raise ValueError("BLOCKED_P4D2_WHITE_OWNER_EDGE")
            while (x+1 < index.shape[1] and edge[y,x+1] and
                   int(index[y,x+1]) == owner):
                x += 1
            last = x
            stroke = p4d0._stroke(owner, palette, first+.125, last+.375, y,
                                  width=1)
            # Strict original-index binding for EVERY logical point in this run.
            if not np.all(index[y,first:last+1] == owner):
                raise ValueError("BLOCKED_P4D2_FOREIGN_OWNER_IN_BOUNDARY")
            if stroke["colorIndex"] != owner or stroke["colorRgb"] != _rgbpack(palette[owner]):
                raise ValueError("BLOCKED_P4D2_BOUNDARY_COLOR_NOT_SOURCE_OWNER")
            entries.append({
                "owner":owner, "y":y, "x0":first, "x1":last, "stroke":stroke
            })
            x += 1
    recovered = np.zeros_like(edge)
    for entry in entries:
        recovered[entry["y"],entry["x0"]:entry["x1"]+1] = True
    if not np.array_equal(recovered,edge):
        raise ValueError("BLOCKED_P4D2_ORIGINAL_INNER_EDGE_NOT_FULLY_PLANNED")
    return entries, edge


def check_parent_paint(paint: list[dict], palette: np.ndarray):
    if not paint:
        raise ValueError("BLOCKED_P4D2_EMPTY_PAINT")
    for stroke in paint:
        owner = int(stroke["colorIndex"])
        if owner == WHITE or owner < 0 or owner >= 128:
            raise ValueError("BLOCKED_P4D2_BAD_PAINT_OWNER")
        if int(stroke["colorRgb"]) != _rgbpack(palette[owner]):
            raise ValueError("BLOCKED_P4D2_PAINT_RGB_MISMATCH")


def adaptive_owner_fill_with_edges(paint: list[dict], entries: list[dict],
                                   palette: np.ndarray):
    """Append a color's edge runs inside its ORIGINAL P4D0 owner paint block."""
    check_parent_paint(paint,palette)
    by_owner = defaultdict(list)
    for e in entries:
        by_owner[e["owner"]].append(e["stroke"])
    original = {int(s["colorIndex"]) for s in paint}
    if set(by_owner) != original:
        raise ValueError("BLOCKED_P4D2_EDGE_AND_PAINT_OWNER_SET")
    seen = set()
    out = []
    prev = None
    for stroke in paint:
        owner = int(stroke["colorIndex"])
        if prev is not None and owner != prev:
            out.extend(by_owner[prev])
            seen.add(prev)
            if owner in seen:
                raise ValueError("BLOCKED_P4D2_PARENT_ADAPTIVE_NOT_OWNER_GROUPED")
        out.append(stroke)
        prev = owner
    out.extend(by_owner[prev])
    plan = p4c0.renumber(out)
    _validate_plan_same_color_edges(plan,paint,entries,palette)
    return plan


def scanline_fill_with_edges(paint: list[dict], entries: list[dict],
                             index: np.ndarray, palette: np.ndarray):
    """Append own-color inner-edge runs directly after EACH parent row/run."""
    check_parent_paint(paint,palette)
    by_row = defaultdict(list)
    for entry in entries:
        by_row[entry["y"]].append(entry)
    consumed = 0
    out = []
    last_row_x = (-1,-1)
    for stroke in paint:
        if len(stroke["points"]) != 2 or int(stroke["width"]) != 2:
            raise ValueError("BLOCKED_P4D2_SCANLINE_PARENT_CHANGED")
        left,right=stroke["points"]
        y=int(left["y"])
        if y<0 or y>=240 or y!=int(right["y"]):
            raise ValueError("BLOCKED_P4D2_SCANLINE_PARENT_COORDINATE")
        x0=int(round(float(left["x"]) - p4d0.X0 - .125))
        x1=int(round(float(right["x"])- p4d0.X0 - .375))
        owner=int(stroke["colorIndex"])
        if (x0<0 or x1>=150 or x1<x0 or (y,x0)<last_row_x or
            not np.all(index[y,x0:x1+1]==owner)):
            raise ValueError("BLOCKED_P4D2_SCANLINE_ORDER_OR_OWNER")
        last_row_x=(y,x0)
        out.append(stroke)
        for entry in by_row[y]:
            if entry["x0"] < x0 or entry["x1"] > x1:
                continue
            if entry["owner"] != owner:
                raise ValueError("BLOCKED_P4D2_SCANLINE_CROSS_OWNER")
            out.append(entry["stroke"])
            consumed += 1
    if consumed != len(entries):
        raise ValueError("BLOCKED_P4D2_SCANLINE_DROPPED_EDGE")
    plan=p4c0.renumber(out)
    _validate_plan_same_color_edges(plan,paint,entries,palette)
    return plan


def _validate_plan_same_color_edges(plan,paint,entries,palette):
    edge_strokes=[e["stroke"] for e in entries]
    if (len(plan)!=len(paint)+len(edge_strokes) or
        Counter(map(identity,plan))!=Counter(map(identity,paint+edge_strokes))):
        raise ValueError("BLOCKED_P4D2_ADDED_OR_LOST_STROKE")
    # Every parent's original fill stroke appears in EXACT same relative order.
    # The classification is by metadata signature, not uniqueness assumptions.
    remaining=Counter(map(identity,edge_strokes))
    retained=[]
    for s in plan:
        sig=identity(s)
        if remaining[sig]:
            remaining[sig]-=1
        else:
            retained.append(sig)
    if retained != list(map(identity,paint)):
        raise ValueError("BLOCKED_P4D2_PARENT_FILL_ORDER_MUTATED")
    if any(int(s["colorRgb"])!=_rgbpack(palette[int(s["colorIndex"])])
           for s in plan):
        raise ValueError("BLOCKED_P4D2_FOREIGN_COLOR_OR_GLOBAL_DARK_OUTLINE")
    if [s["strokeId"] for s in plan] != [f"icon-{i}" for i in range(len(plan))]:
        raise ValueError("BLOCKED_P4D2_SEQUENCE_IDS")


def source_review(folder: Path, original: np.ndarray, index_rgb: np.ndarray,
                  base: Image.Image, with_boundary: Image.Image):
    cards=[
        ("ORIGINAL RGB",Image.fromarray(original).resize((450,720),Image.Resampling.NEAREST)),
        ("CURRENT B1-R GAME COLORS",Image.fromarray(index_rgb).resize((450,720),Image.Resampling.NEAREST)),
        ("EGRET FILL ONLY",base),
        ("EGRET SAME-COLOR EDGE + FILL",with_boundary),
    ]
    out=Image.new("RGB",(1800,764),(252,252,252))
    draw=ImageDraw.Draw(out)
    for i,(label,img) in enumerate(cards):
        out.paste(img,(450*i,44))
        draw.text((450*i+8,15),label,fill=(0,0,0))
    out.save(folder/"COMPARE_NATIVE_OWNER_COLOR_AS_FILL.png")


def run(workspace: Path, source: Path, engine_js: Path,
        renderer: Path, output: Path):
    if output.exists():
        raise ValueError("BLOCKED_P4D2_EXISTING_EVIDENCE_OUTPUT")
    check_source(source)
    if p4b1.git_blob(renderer.read_bytes())!=p4d0.RENDERER_BLOB:
        raise ValueError("BLOCKED_P4D2_FROZEN_RENDERER_CHANGED")
    if p4b1.git_blob(Path(p4d0.__file__).read_bytes())!=P4D0_PARENT_BLOB:
        raise ValueError("BLOCKED_P4D2_FROZEN_PARENT_CHANGED")
    if EXPERIMENT not in (workspace/"AutoDraw_Stage20"/"docs"/PREREG).read_text("utf8"):
        raise ValueError("BLOCKED_P4D2_NOT_PREREGISTERED")
    palette,_=p3b.read_engine_palette(engine_js)
    output.mkdir(parents=True)
    (output/"README_RU.txt").write_text(
        "P4D2: обычные native Egret штрихи границы имеют RGB СОБСТВЕННОЙ цветовой области E/F.\n"
        "Никакого отдельно накладываемого тёмного/общего контура. Граница — часть местной заливки.\n"
        "PAINT_ONLY_CONTROL vs OWNER_COLOR_BOUNDARY_AS_PAINT, E/F adaptive+scanline.\n"
        "Все строки исходных индексов, без сокращения граничных штрихов, game CHALK NOT_RUN.\n",
        "utf8")
    output_results={}
    work=[]
    with tempfile.TemporaryDirectory(prefix="engine001-p4d2-original-") as tmp:
        fresh=Path(tmp)/"fresh_p3d"
        parent=p3d.run(source,engine_js,fresh)
        if (parent["experiment"]!=p3d.EXPERIMENT or
            parent["original_source_sha256"]!=SOURCE_SHA or
            not parent["P3B_original_recomputed_in_current_run"] or
            parent["legacy_G32_V44_M1_used_as_source"]):
            raise ValueError("BLOCKED_P4D2_NOT_RECOMPUTED_SOURCE")
        original=np.asarray(Image.open(fresh/"00_ORIGINAL_RGB_LOGICAL.png").convert("RGB"),np.uint8)
        Image.fromarray(original).save(output/"ORIGINAL_RGB_LOGICAL.png")
        for method in METHODS:
            folder=output/method
            folder.mkdir()
            index=np.asarray(Image.open(fresh/(SOURCE+"_"+method+"_ENGINE_INDICES.png")),np.uint8).copy()
            selected=parent["all_results"][SOURCE]["selected_engine_indices"]
            p4c0.validate_source(index,palette,selected)
            if parent["all_results"][SOURCE]["methods"][method]["status"]!=(
                    "SOURCE_SCREEN_PASS_VISUAL_PENDING_RUNTIME_ACCESS_UNVERIFIED"):
                raise ValueError("BLOCKED_P4D2_ORIGINAL_SOURCE_STATUS")
            Image.fromarray(index).save(folder/"SOURCE_ENGINE_INDICES.png")
            source_rgb=palette[index]
            Image.fromarray(source_rgb).save(folder/"SOURCE_GAME32_RGB.png")
            entries,edge=source_boundary_runs(index,palette)
            Image.fromarray(edge.astype(np.uint8)*255).save(folder/"OWNER_INNER_BOUNDARY_MASK.png")
            true_rgb=palette[index].copy()
            true_rgb[~edge]=(255,255,255)
            Image.fromarray(true_rgb).save(folder/"OWNER_INNER_BOUNDARY_SOURCE_RGB.png")
            adaptive, model=p4d0.adaptive_unbounded(index,palette)
            scanline=p4d0.first_scanline(index,palette)
            output_results[method]={
                "source":SOURCE,"source_original_only":True,
                "no_legacy_g32_v44_used":True,
                "selected_swatches_including_white":len(selected),
                "nonwhite_source_owners":len(set(np.unique(index))-{WHITE}),
                "inner_owner_edge_logical_pixels":int(edge.sum()),
                "inner_owner_colored_boundary_runs":len(entries),
                "global_dark_outline_strokes":0,
                "adaptive_parent_model_only":model,
                "arms":{},
            }
            print("P4D2_BOUNDARY_SOURCE",method,"logical edge",int(edge.sum()),
                  "runs",len(entries),flush=True)
            for arm,paint in zip(ARMS,(adaptive,scanline)):
                native_dir=folder/arm
                native_dir.mkdir()
                colorplan=(adaptive_owner_fill_with_edges(paint,entries,palette)
                           if arm==ARMS[0] else
                           scanline_fill_with_edges(paint,entries,index,palette))
                # No source-wide outline; every added stroke is a local owner fill.
                for stage,plan in ((STAGES[0],paint),(STAGES[1],colorplan)):
                    (native_dir/(stage+"_FULL_PLAN.json")).write_text(
                        json.dumps(plan,ensure_ascii=False,allow_nan=False)+"\n","utf8")
                output_results[method]["arms"][arm]={
                    "paint_strokes":len(paint),
                    "owner_color_boundary_strokes":len(entries),
                    "full_strokes":len(colorplan),
                    "paint_vertices_NOT_CHALK":sum(len(s["points"]) for s in paint),
                    "full_vertices_NOT_CHALK":sum(len(s["points"]) for s in colorplan),
                    "boundary_width":1,"native_status":"NOT_RUN",
                    "stages":{},
                    "owner_specific_quality_gates":"NOT_MEASURED",
                }
                work.append((method,arm,index,paint,colorplan))
                print("P4D2_PLANS_READY",method,arm,len(paint),len(colorplan),
                      flush=True)
        renderer_audit={}
        with p4d0.patched_test_renderer(renderer) as audit:
            renderer_audit=dict(audit)
            with p4b7.native_egret_session(workspace) as driver:
                driver.set_script_timeout(900)
                for method,arm,index,paint,colorplan in work:
                    folder=output/method/arm
                    result=output_results[method]["arms"][arm]
                    imgs={}
                    for stage,plan in ((STAGES[0],paint),(STAGES[1],colorplan)):
                        stage_dir=folder/stage
                        stage_dir.mkdir()
                        response=driver.execute_script(
                            "return window.AutoDrawGameRendererReference."
                            "renderP4A2BrushWidths1to10Probe(arguments[0]);",plan)
                        rgba,meta=read_webgl_result(response,stage_dir,"REAL_EGRET_NATIVE_BOARD")
                        if (meta.get("schema")!="ENGINE001_B1R_P4A2_NATIVE_1_TO_10"
                            or meta.get("renderer")!="real Egret 5.4.1 BoardPane/WebGLRenderer"
                            or rgba.shape!=p4d0.NATIVE_SHAPE
                            or meta.get("strokeCount")!=len(plan)
                            or meta.get("syntheticAcceptedVerticesNotChalk")!=sum(len(s["points"]) for s in plan)):
                            raise ValueError("BLOCKED_P4D2_EGRET_NATIVE_RENDERER_OR_COUNT")
                        img=p4c0.preview_native(rgba)
                        img.save(stage_dir/"REAL_EGRET_CROP.png")
                        p4d0._native_error_masks(rgba,index,palette,stage_dir)
                        stats=p4d0._native_stats(rgba,index,palette)
                        result["stages"][stage]={
                            "true_native_egret":True,
                            "renderer":meta["renderer"],
                            "schema":meta["schema"],
                            "accepted_strokes":meta["strokeCount"],
                            "accepted_vertices_NOT_CHALK":meta["syntheticAcceptedVerticesNotChalk"],
                            "png_native_sha256":meta["source_sha256"],
                            "native_composite":stats,
                        }
                        imgs[stage]=img
                        print("P4D2_NATIVE",method,arm,stage,
                              "rgb",round(stats["native_source_palette_rgb_maxchannel_delta_le32_on_nonwhite"],6),
                              "any_ink",round(stats["native_nonwhite_any_ink_coverage_alpha24"],6),
                              "whiteink",stats["native_ink_on_white_background_backing_px"],
                              flush=True)
                    a=result["stages"][STAGES[0]]["native_composite"]
                    b=result["stages"][STAGES[1]]["native_composite"]
                    improvement=(b["native_source_palette_rgb_maxchannel_delta_le32_on_nonwhite"] >
                                 a["native_source_palette_rgb_maxchannel_delta_le32_on_nonwhite"]
                                 and b["native_ink_on_white_background_backing_px"] <=
                                 a["native_ink_on_white_background_backing_px"])
                    result["numeric_candidate"]=("COMPOSITE_CANDIDATE_VISUAL_PENDING" if improvement
                                                 else "NO_NUMERIC_IMPROVEMENT")
                    result["change_from_paint_only"]={
                        "native_RGB_within32_nonwhite_delta":
                        b["native_source_palette_rgb_maxchannel_delta_le32_on_nonwhite"] -
                        a["native_source_palette_rgb_maxchannel_delta_le32_on_nonwhite"],
                        "native_any_ink_nonwhite_delta":
                        b["native_nonwhite_any_ink_coverage_alpha24"] -
                        a["native_nonwhite_any_ink_coverage_alpha24"],
                        "native_white_background_ink_backing_delta":
                        b["native_ink_on_white_background_backing_px"] -
                        a["native_ink_on_white_background_backing_px"],
                    }
                    result["native_status"]="COMPLETE"
                    source_review(folder,original,palette[index],imgs[STAGES[0]],imgs[STAGES[1]])
                blank_response=driver.execute_script(
                    "return window.AutoDrawGameRendererReference."
                    "renderP4A2BrushWidths1to10Probe([]);")
                blank,blank_meta=read_webgl_result(blank_response,output,"REAL_EGRET_BLANK")
                if (blank.shape!=p4d0.NATIVE_SHAPE or np.any(blank[:,:,3]) or
                    blank_meta.get("schema")!="ENGINE001_B1R_P4A2_BLANK_WEBGL"):
                    raise ValueError("BLOCKED_P4D2_NATIVE_BLANK_NOT_EMPTY")
        if p4b1.git_blob(renderer.read_bytes())!=p4d0.RENDERER_BLOB:
            raise ValueError("BLOCKED_P4D2_FROZEN_RENDERER_NOT_RESTORED")
    report={
        "experiment":EXPERIMENT,
        "result":"ALL_EIGHT_OWNER_COLORED_NATIVE_EGRET_SCENES_COMPLETED",
        "original_source_sha256":SOURCE_SHA,"source_recomputed_current_run":True,
        "source":SOURCE,"methods":output_results,
        "native_scenes":8,"true_native_blank_alpha0":True,
        "no_dark_or_global_contour":True,
        "runtime_renderer_test_only":renderer_audit,
        "frozen_owner99_protected0_far3":"NOT_MEASURED_COMPOSITE_ONLY",
        "production_promotion":False,
        "E4_live_game":"NOT_RUN","E5_independent":"NOT_RUN",
        "exact_run_bound_CHALK":None,
        "github_sha":os.getenv("GITHUB_SHA"),
        "github_run_id":os.getenv("GITHUB_RUN_ID"),
    }
    report["members_sha256"]={
        str(file.relative_to(output)).replace("\\","/"):digest(file.read_bytes())
        for file in sorted(output.rglob("*")) if file.is_file()
    }
    (output/"report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n","utf8")
    print("P4D2_EGRET_DONE",report["native_scenes"],"scenes",flush=True)
    return report


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--workspace",type=Path,required=True)
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--engine-js",type=Path,required=True)
    ap.add_argument("--renderer",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    run(args.workspace,args.source,args.engine_js,args.renderer,args.output)

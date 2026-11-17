#!/usr/bin/env python3
"""ENGINE-001 S2b EGRET-P3: locally adaptive directional residual repair.

Reuses frozen P2 multiring plan and original Egret native_batch.
Source OpenCV masks rank proposals ONLY; native RGBA makes decisions.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import platform
from pathlib import Path

import cv2
import numpy as np

from run_engine001_color32_s2b_egret_p1 import (
    ALPHAS, ROI_X0, ROI_SHAPE, FROZEN_PALETTE_GIT_BLOB,
    FROZEN_RENDERER_GIT_BLOB, git_blob_sha, native_metrics,
)
from run_engine001_color32_s2b_egret_p2 import (
    OWNERS, FROZEN_DETAILS, FROZEN_DETAIL_VERTICES, plan_p2,
)
from run_engine001_palette32_region_study import (
    read_source, read_palette, nearest32, sha,
)
from run_engine001_color32_s2_edge_protection import strong_edges, protected_merge
from run_engine001_complex_holdout_v5 import native_batch

EXP = "ENGINE001_COLOR32_S2B_EGRET_P3_DIRECTIONAL_NATIVE"
WIDTHS = (30, 15, 10, 6, 4, 2)
ANGLES = tuple(range(0, 180, 15))
MAX_SEEDS_PER_OWNER = 80
MAX_ADDITIONAL_STROKES = 240
MAX_ADDITIONAL_VERTICES = 480
MAX_LINE_HALF_LENGTH = 24
MIN_ABSOLUTE_NATIVE_GAIN_PP = 1.0
NATIVE_QUALITY_TARGET = .99


def _model_footprint(points, width):
    img = np.zeros(ROI_SHAPE, np.uint8)
    xy = np.asarray([(round(p["x"] - ROI_X0), round(p["y"]))
                     for p in points], np.int32)
    if len(xy) < 2:
        raise ValueError("BLOCKED_P3_PATH_POINTS")
    cv2.polylines(img, [xy], False, 255, width, cv2.LINE_8)
    return img != 0


def _residual_after_p2(labels: np.ndarray, p2: list[dict]):
    remain = {owner: labels == owner for owner in OWNERS}
    for stroke in p2:
        owner = stroke["colorIndex"]
        if owner not in remain:
            raise ValueError("BLOCKED_P3_UNKNOWN_OWNER")
        remain[owner][_model_footprint(stroke["points"], stroke["width"])] = False
    return remain


def _seed_points(residual: np.ndarray, distance: np.ndarray):
    """Spatially distributed residuals + one representative per component."""
    number, cc, stats, _ = cv2.connectedComponentsWithStats(
        residual.astype(np.uint8), 8)
    origins = []
    for i in range(1, number):
        yy, xx = np.nonzero(cc == i)
        if len(xx):
            best = int(np.argmax(distance[yy, xx]))
            origins.append((int(xx[best]), int(yy[best])))
    # Deterministic coarse spatial sampling avoids starving thin side regions.
    cells = {}
    for y, x in zip(*np.nonzero(residual)):
        key = (int(y) // 4, int(x) // 4)
        val = (float(distance[y, x]), int(x), int(y))
        if key not in cells or val[0] > cells[key][0]:
            cells[key] = val
    origins.extend((x, y) for _, x, y in
                   (cells[k] for k in sorted(cells)))
    result, used = [], set()
    for point in origins:
        if point not in used:
            result.append(point)
            used.add(point)
        if len(result) >= MAX_SEEDS_PER_OWNER:
            break
    return result


def _candidate(owner: int, seed, width: int, angle: int,
               own: np.ndarray, dt: np.ndarray, outside: np.ndarray,
               palette: np.ndarray):
    sx, sy = seed
    min_clearance = max(.5, width / 2 - 2)
    if float(dt[sy, sx]) < min_clearance:
        return None
    theta = math.radians(angle)
    vx, vy = math.cos(theta), math.sin(theta)
    ends = []
    for sign in (-1, 1):
        last = (sx, sy)
        for step in range(1, MAX_LINE_HALF_LENGTH + 1):
            x = int(round(sx + sign * step * vx))
            y = int(round(sy + sign * step * vy))
            if not (0 <= x < ROI_SHAPE[1] and 0 <= y < ROI_SHAPE[0]):
                break
            if not own[y, x] or dt[y, x] < min_clearance:
                break
            last = (x, y)
        ends.append(last)
    (x1,y1),(x2,y2) = ends
    if (x1-x2)**2 + (y1-y2)**2 < 2:
        return None
    line = np.zeros(ROI_SHAPE,np.uint8)
    cv2.line(line,(x1,y1),(x2,y2),255,1,cv2.LINE_8)
    if not np.all(own[line>0]):
        return None
    points = [{"x":float(x1+ROI_X0),"y":float(y1)},
              {"x":float(x2+ROI_X0),"y":float(y2)}]
    fp = _model_footprint(points,width)
    if np.any(fp & (outside > 3.0)):
        return None
    # Proposals near ROI clipping need separate native evidence. Reject ones
    # whose nominal radius extends >3 logical px outside the original ROI.
    margin = max(0., width/2.-3.)
    if any(p["x"]-ROI_X0 < margin or
           p["x"]-ROI_X0 > ROI_SHAPE[1]-1-margin or
           p["y"] < margin or p["y"] > ROI_SHAPE[0]-1-margin
           for p in points):
        return None
    rgb=palette[owner]
    return {
        "owner":owner, "width":width, "angle_degrees_undirected":angle,
        "seed":seed, "points":points,
        "own_indices":np.flatnonzero(fp & own).astype(np.int32),
        "source_footprint_owner_pixels":int(np.count_nonzero(fp & own)),
        "colorRgb":(int(rgb[0])<<16)|(int(rgb[1])<<8)|int(rgb[2]),
    }


def plan_p3(labels: np.ndarray, palette: np.ndarray,
            p2: list[dict], max_additional=MAX_ADDITIONAL_STROKES):
    if (not isinstance(labels,np.ndarray) or labels.shape != ROI_SHAPE or
            labels.dtype != np.uint8 or palette.shape != (32,3) or
            any(not np.any(labels==owner) for owner in OWNERS) or
            not p2 or type(max_additional) is not int or
            not 0 < max_additional <= MAX_ADDITIONAL_STROKES):
        raise ValueError("BLOCKED_P3_INPUT")
    if any(s["colorIndex"] not in OWNERS or
           not 2 <= len(s["points"]) <= 128 for s in p2):
        raise ValueError("BLOCKED_P3_BASE_PLAN")
    baseline_verts = sum(len(s["points"]) for s in p2)
    if (baseline_verts + FROZEN_DETAIL_VERTICES + MAX_ADDITIONAL_VERTICES > 5900
            or len(p2) + FROZEN_DETAILS + max_additional > 3000):
        raise ValueError("BLOCKED_P3_RESERVED_RESOURCE")
    remaining = _residual_after_p2(labels,p2)
    options=[]
    sample={}
    for owner in OWNERS:
        own = labels == owner
        dt = cv2.distanceTransform(own.astype(np.uint8),
                                   cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
        outside = cv2.distanceTransform((~own).astype(np.uint8),
                                        cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
        seeds = _seed_points(remaining[owner],dt)
        sample[str(owner)] = {"residual_model_before":int(remaining[owner].sum()),
                              "sampled_seed_count":len(seeds)}
        for index,seed in enumerate(seeds):
            for width in WIDTHS:
                for angle in ANGLES:
                    cand = _candidate(owner,seed,width,angle,own,dt,outside,palette)
                    if cand is not None:
                        cand["seed_index"]=index
                        options.append(cand)
    selected=[]
    used=set()
    histogram={str(width):0 for width in WIDTHS}
    owner_count={str(owner):0 for owner in OWNERS}
    while len(selected)<max_additional:
        best=None
        for i,option in enumerate(options):
            if i in used:
                continue
            gain=int(np.count_nonzero(
                remaining[option["owner"]].ravel()[option["own_indices"]]))
            if gain==0:
                continue
            # Each source line has two vertices; maximize new own-color gain,
            # with same-color overlap explicitly free of any cost.
            score=(gain/2.,gain,-option["owner"],option["width"],
                   -option["angle_degrees_undirected"],-option["seed_index"])
            if best is None or score>best[0]:
                best=(score,i,option,gain)
        if best is None:
            break
        _,i,cand,gain=best
        used.add(i)
        owner=cand["owner"]
        stroke={
            "strokeId":f"icon-{len(p2)+len(selected)}",
            "colorIndex":owner, "colorRgb":cand["colorRgb"],
            "width":cand["width"],
            "points":cand["points"],
        }
        selected.append(stroke)
        remaining[owner].ravel()[cand["own_indices"]]=False
        histogram[str(cand["width"])]+=1
        owner_count[str(owner)]+=1
    status=("SOURCE_READY_FOR_E3" if selected else
            "BLOCKED_NO_SAFE_REPAIR")
    info={
        "status":status, "widths_considered":list(WIDTHS),
        "angles_mod_180_degrees":list(ANGLES),
        "360_degree_heading_equivalence":True,
        "same_color_overlap_penalty":0,
        "sample":sample, "candidate_count":len(options),
        "additional_paths":len(selected),
        "additional_vertices_NOT_CHALK":sum(len(x["points"]) for x in selected),
        "additional_width_histogram":histogram,
        "additional_per_owner":owner_count,
        "model_residual_after_NOT_EGRET":
            {str(o):int(remaining[o].sum()) for o in OWNERS},
        "planned_total_strokes_with_frozen_V44B410":
            len(p2)+len(selected)+FROZEN_DETAILS,
        "planned_total_vertices_with_frozen_V44B_NOT_CHALK":
            baseline_verts+2*len(selected)+FROZEN_DETAIL_VERTICES,
        "V44B_frozen_410_LAST_unmodified":True,
        "game_exact_CHALK":None,"safe_to_execute_game":False,
    }
    if (info["additional_vertices_NOT_CHALK"] > MAX_ADDITIONAL_VERTICES or
            info["planned_total_strokes_with_frozen_V44B410"]>3000 or
            info["planned_total_vertices_with_frozen_V44B_NOT_CHALK"]>5900):
        raise ValueError("BLOCKED_P3_RESOURCE")
    return selected,info


def native_compare(p2:dict,p3:dict):
    entries={}
    gate={}
    for alpha in ALPHAS:
        for owner in OWNERS:
            before=p2[str(alpha)][str(owner)]
            after=p3[str(alpha)][str(owner)]
            target=after["owner_target_backing_pixels"]
            if target != before["owner_target_backing_pixels"] or target<=0:
                raise ValueError("BLOCKED_P3_TARGET_DRIFT")
            improvement=100. * (after["native_correct_owner_pixels"]-
                                 before["native_correct_owner_pixels"])/target
            own_fraction=after["native_correct_owner_pixels"]/target
            foreign=after["non_owner_beyond_3logical_px"]
            outside=after["ink_outside_image_ROI"]
            key=f"alpha{alpha}_owner{owner}"
            gate[key]=bool(improvement>=MIN_ABSOLUTE_NATIVE_GAIN_PP and
                           foreign==0 and outside==0)
            entries[key]={
                "p2_native_owner_pixels":before["native_correct_owner_pixels"],
                "p3_native_owner_pixels":after["native_correct_owner_pixels"],
                "target_backing_pixels":target,
                "absolute_coverage_gain_pp":improvement,
                "p3_coverage_percent":100.*own_fraction,
                "gap_to_99pp":max(0.,99.-100.*own_fraction),
                "foreign_any_distance":after["non_owner_native_pixels_any_distance"],
                "foreign_beyond_3logical_px":foreign,
                "outside_original_ROI_pixels":outside,
                "native_full_owner_99pct_diagnostic":own_fraction>=NATIVE_QUALITY_TARGET,
            }
    return {"checks":gate,"native_incremental_gate_pass":all(gate.values()),
            "both_owners_99pct_at_alpha24":all(
                entries[f"alpha24_owner{owner}"]["native_full_owner_99pct_diagnostic"]
                for owner in OWNERS),
            "measurements":entries,"full_image_quality":"NOT_RUN"}


def run(workspace:Path,source:Path,palette_path:Path,output:Path):
    if output.exists():
        raise ValueError("BLOCKED_P3_EVIDENCE_OVERWRITE")
    if (git_blob_sha(palette_path)!=FROZEN_PALETTE_GIT_BLOB or
            git_blob_sha(workspace/"AutoDraw_Stage20/tests/game_renderer_reference.js")
            !=FROZEN_RENDERER_GIT_BLOB):
        raise ValueError("BLOCKED_P3_SOURCE_BLOB_DRIFT")
    _,rgb=read_source(source)
    palette=read_palette(palette_path)
    b=nearest32(rgb,palette)
    strong,_=strong_edges(rgb)
    g,_=protected_merge(rgb,b,palette,strong)
    p2,p2_info=plan_p2(g,palette)
    if p2_info["status"]!="SOURCE_MODEL_READY_FOR_E3":
        raise ValueError("BLOCKED_P3_P2_NOT_FROZEN_SOURCE_READY")
    additions,planned=plan_p3(g,palette,p2)
    if planned["status"]!="SOURCE_READY_FOR_E3":
        raise ValueError("BLOCKED_P3_NO_REPAIR_PATHS")
    p3=p2+additions
    output.mkdir(parents=True)
    (output/"source-plan.json").write_text(json.dumps({
        "experiment":EXP,"source_sha256":sha(source),
        "game32_palette_blob":FROZEN_PALETTE_GIT_BLOB,
        "archived_Egret_renderer_blob":FROZEN_RENDERER_GIT_BLOB,
        "g_index_sha256":hashlib.sha256(g.tobytes()).hexdigest(),
        "p2_frozen_paths":p2,"p3_additional_paths":additions,
        "p2_frozen_preflight":p2_info,"p3_source_preflight":planned,
        "native_renderer_not_game":True,"safe_to_execute_game":False,
        "game_exact_CHALK":None,
    },indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    observed={}
    for label,paths in (("P2-BASELINE",p2),("P3-DIRECTIONAL",p3)):
        folder=output/label
        folder.mkdir()
        frames,metadata,manifest=native_batch(
            workspace,label,paths,folder,
            renderer_method="renderComplexHoldoutColorProbe")
        observed[label]={
            "native_rgba":native_metrics(frames,g,paths),
            "metadata":metadata,"native_manifest":manifest,
            "path_count":len(paths),
            "vertices_NOT_CHALK":sum(len(x["points"]) for x in paths),
        }
    comparison=native_compare(observed["P2-BASELINE"]["native_rgba"],
                              observed["P3-DIRECTIONAL"]["native_rgba"])
    hashes={str(f.relative_to(output)).replace("\\","/"):sha(f)
            for f in output.rglob("*") if f.is_file()}
    report={
        "experiment":EXP,
        "status":"P3_NATIVE_INCREMENTAL_PASS_NOT_FULL_IMAGE" if comparison[
            "native_incremental_gate_pass"] else "P3_NATIVE_INCREMENTAL_FAIL_NOT_FULL_IMAGE",
        "github_sha":os.environ.get("GITHUB_SHA"),
        "github_run_id":os.environ.get("GITHUB_RUN_ID"),
        "source_sha256":sha(source),
        "palette_git_blob":FROZEN_PALETTE_GIT_BLOB,
        "renderer_git_blob":FROZEN_RENDERER_GIT_BLOB,
        "baseline_P2_CI_run_id":44008672803,
        "baseline_P2_original_report_sha256":
            "02499eeb1fc4a45fecd9a2d04da36cb958af7ddc0ea5bafaf271809e6770e9c1",
        "preflight":planned,"native_variants":observed,
        "native_comparison":comparison,
        "original_V44B410_last":"NOT_RENDERED_UNMODIFIED",
        "other_game32_owners":"NOT_RUN",
        "visual_review":"PENDING",
        "full_image_quality":"NOT_RUN",
        "E4_game":"NOT_RUN","E5_independent":"NOT_RUN",
        "exact_game_CHALK":None,"production_accepted":False,
        "report_linked_SHA256":hashes,
        "versions":{"python":platform.python_version(),
                    "numpy":np.__version__,"opencv":cv2.__version__},
    }
    (output/"report.json").write_text(json.dumps(
        report,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    return report


def main():
    ap=argparse.ArgumentParser()
    for arg in ("workspace","source","palette","output"):
        ap.add_argument("--"+arg,required=True,type=Path)
    args=ap.parse_args()
    r=run(args.workspace,args.source,args.palette,args.output)
    print(json.dumps({
        "status":r["status"],
        "source_added":r["preflight"]["additional_paths"],
        "native":r["native_comparison"]["measurements"],
        "numeric_gate":r["native_comparison"]["native_incremental_gate_pass"],
        "full_image":"NOT_RUN","CHALK":None,
    },ensure_ascii=False))


if __name__=="__main__":
    main()

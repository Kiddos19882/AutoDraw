#!/usr/bin/env python3
"""ENGINE001 P3b: immutable P3 routes, width6->4 ONLY, actual Egret A/B."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path

import cv2
import numpy as np

from run_engine001_color32_s2b_egret_p3 import (
    plan_p3, native_compare, FROZEN_SOURCE_SHA256,
)
from run_engine001_color32_s2b_egret_p2 import (
    plan_p2, OWNERS, FROZEN_DETAILS, FROZEN_DETAIL_VERTICES,
)
from run_engine001_color32_s2b_egret_p1 import (
    FROZEN_PALETTE_GIT_BLOB, FROZEN_RENDERER_GIT_BLOB,
    git_blob_sha, native_metrics,
)
from run_engine001_palette32_region_study import (
    read_source, read_palette, nearest32, sha,
)
from run_engine001_color32_s2_edge_protection import strong_edges, protected_merge
from run_engine001_complex_holdout_v5 import native_batch

EXP = "ENGINE001_COLOR32_S2B_EGRET_P3B_WIDTH4_NATIVE"
FROZEN_P3_CI_RUN_ID = 44012588733
FROZEN_P3_REPORT_SHA256 = "ff2df0c596fab692461a970f30d042aaa14f876131873096a009e85e2ffb7cbf"
FROZEN_ADDITIONS_CANONICAL_SHA256 = "ea0a7fef8712d0a853ea688ec9e07cd6058b7c166e49d7264f38fa224c94eada"
ORIGINAL_WIDTH = 6
REPLAY_WIDTH = 4
FROZEN_ADDITIONAL_PATH_COUNT = 56


def canonical_path_sha(strokes):
    return hashlib.sha256(json.dumps(
        strokes,sort_keys=True,ensure_ascii=False,
        separators=(",",":")).encode("utf-8")).hexdigest()


def make_width4_replay(p2, additions,
                       expected_sha=FROZEN_ADDITIONS_CANONICAL_SHA256):
    if (type(p2) is not list or not p2 or
            type(additions) is not list or not additions or
            not isinstance(expected_sha,str) or len(expected_sha)!=64):
        raise ValueError("BLOCKED_P3B_REPLAY_INPUT")
    canonical = canonical_path_sha(additions)
    if canonical!=expected_sha:
        raise ValueError("BLOCKED_P3B_FROZEN_P3_PATH_DRIFT")
    if (len(additions)!=FROZEN_ADDITIONAL_PATH_COUNT or
            any(s.get("width")!=ORIGINAL_WIDTH or
                s.get("colorIndex") not in OWNERS or
                len(s.get("points",[]))!=2
                for s in additions)):
        raise ValueError("BLOCKED_P3B_FROZEN_ROUTE_CONTRACT")
    combined=[{**s,"points":[dict(p) for p in s["points"]]}
              for s in p2]
    for s in additions:
        combined.append({**s,"width":REPLAY_WIDTH,
                         "points":[dict(p) for p in s["points"]]})
    ids=[s["strokeId"] for s in combined]
    verts=sum(len(s["points"]) for s in combined)
    if (len(set(ids))!=len(ids) or
            len(ids)+FROZEN_DETAILS>3000 or
            verts+FROZEN_DETAIL_VERTICES>5900):
        raise ValueError("BLOCKED_P3B_RESOURCES_OR_DUPLICATE_ID")
    if ([(s["colorIndex"],s["colorRgb"],s["points"])
         for s in combined[len(p2):]]
        !=[(s["colorIndex"],s["colorRgb"],s["points"]) for s in additions]):
        raise AssertionError("P3b must not change any original P3 route geometry")
    return combined,{
        "original_P3_paths_canonical_SHA256":canonical,
        "original_P3_additions":len(additions),
        "new_P3b_additions":len(additions),
        "only_brush_width_changed_from":ORIGINAL_WIDTH,
        "only_brush_width_changed_to":REPLAY_WIDTH,
        "additional_synthetic_vertices_NOT_CHALK":len(additions)*2,
        "total_strokes_with_original410_V44B_LAST":len(combined)+FROZEN_DETAILS,
        "total_vertices_with_original1792_V44B_LAST_NOT_CHALK":
            verts+FROZEN_DETAIL_VERTICES,
        "original_P2_strokes_preserved":len(p2),
        "original_410_V44B_colored_contours_unchanged_LAST":True,
        "safe_to_execute_game":False,
        "exact_game_CHALK":None,
    }


def run(workspace:Path,source:Path,palette_path:Path,output:Path):
    if output.exists():
        raise ValueError("BLOCKED_P3B_NO_OVERWRITE")
    if (sha(source)!=FROZEN_SOURCE_SHA256 or
            git_blob_sha(palette_path)!=FROZEN_PALETTE_GIT_BLOB or
            git_blob_sha(workspace/"AutoDraw_Stage20/tests/game_renderer_reference.js")
            !=FROZEN_RENDERER_GIT_BLOB):
        raise ValueError("BLOCKED_P3B_FROZEN_SOURCE_DRIFT")
    _,src=read_source(source)
    palette=read_palette(palette_path)
    b=nearest32(src,palette)
    protected,_=strong_edges(src)
    g,_=protected_merge(src,b,palette,protected)
    p2,p2_info=plan_p2(g,palette)
    if p2_info["status"]!="SOURCE_MODEL_READY_FOR_E3":
        raise ValueError("BLOCKED_P3B_BASE_P2_SOURCE")
    additions,orig=plan_p3(g,palette,p2)
    if orig["status"]!="SOURCE_READY_FOR_E3":
        raise ValueError("BLOCKED_P3B_BASE_P3_SOURCE")
    p3b,replay=make_width4_replay(p2,additions)
    output.mkdir(parents=True)
    (output/"source-plan.json").write_text(json.dumps({
        "experiment":EXP,
        "source_sha256":sha(source),
        "original_P2_source_paths":p2,
        "frozen_P3_original_width6_paths":additions,
        "P3b_only_width4_path_ids":[p["strokeId"] for p in p3b[len(p2):]],
        "replay_preflight":replay,
        "source_G_indices_sha256":hashlib.sha256(g.tobytes()).hexdigest(),
        "palette_git_blob":FROZEN_PALETTE_GIT_BLOB,
        "renderer_git_blob":FROZEN_RENDERER_GIT_BLOB,
        "exact_game_CHALK":None,"safe_to_execute_game":False,
    },indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    captures={}
    for label,paths in (("P2-BASELINE",p2),("P3B-WIDTH4",p3b)):
        folder=output/label
        folder.mkdir()
        frames,metadata,manifest=native_batch(
            workspace,label,paths,folder,
            renderer_method="renderComplexHoldoutColorProbe")
        captures[label]={
            "native_rgba_metrics":native_metrics(frames,g,paths),
            "renderer_metadata":metadata,
            "renderer_manifest":manifest,
            "path_count":len(paths),
            "synthetic_vertices_NOT_CHALK":sum(len(s["points"]) for s in paths),
        }
    comparison=native_compare(
        captures["P2-BASELINE"]["native_rgba_metrics"],
        captures["P3B-WIDTH4"]["native_rgba_metrics"])
    linked={str(p.relative_to(output)).replace("\\","/"):sha(p)
            for p in output.rglob("*") if p.is_file()}
    report={
        "experiment":EXP,
        "status":("P3B_NATIVE_INCREMENTAL_PASS_NOT_FULL_IMAGE"
                  if comparison["native_incremental_gate_pass"] else
                  "P3B_NATIVE_INCREMENTAL_FAIL_NOT_FULL_IMAGE"),
        "github_sha":os.environ.get("GITHUB_SHA"),
        "github_run_id":os.environ.get("GITHUB_RUN_ID"),
        "original_P3_negative_run_id":FROZEN_P3_CI_RUN_ID,
        "original_P3_negative_report_SHA256":FROZEN_P3_REPORT_SHA256,
        "original_P3_positive_execution_but_quality_FAIL":True,
        "source_sha256":sha(source),
        "palette_git_blob":FROZEN_PALETTE_GIT_BLOB,
        "renderer_git_blob":FROZEN_RENDERER_GIT_BLOB,
        "source_replay":replay,
        "source_p3_existing_model_preflight":orig,
        "native_original_archived_BoardPane_Firefox_WebGL":True,
        "native_variants":captures,
        "native_comparison":comparison,
        "full_image_quality":"NOT_RUN",
        "all_game32_colors":"NOT_RUN",
        "visual_review":"PENDING",
        "original_V44B_410_colored_detail_last":"NOT_RENDERED_UNMODIFIED",
        "E4_game":"NOT_RUN","E5_independent":"NOT_RUN",
        "exact_game_CHALK":None,"production_accepted":False,
        "report_linked_SHA256":linked,
        "versions":{"python":platform.python_version(),
                    "numpy":np.__version__,"opencv":cv2.__version__},
    }
    (output/"report.json").write_text(json.dumps(
        report,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    return report


def main():
    ap=argparse.ArgumentParser()
    for arg in ("workspace","source","palette","output"):
        ap.add_argument("--"+arg,required=True,type=Path)
    args=ap.parse_args()
    result=run(args.workspace,args.source,args.palette,args.output)
    print(json.dumps({
        "status":result["status"],
        "relative_to_P2":result["native_comparison"]["measurements"],
        "all_owner_beyond3px_safe":all(v["foreign_beyond_3logical_px"]==0
             for v in result["native_comparison"]["measurements"].values()),
        "full_image_quality":"NOT_RUN",
        "exact_game_CHALK":None,
    },ensure_ascii=False))


if __name__=="__main__":
    main()

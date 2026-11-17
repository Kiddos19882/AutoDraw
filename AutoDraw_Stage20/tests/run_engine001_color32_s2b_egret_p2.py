#!/usr/bin/env python3
"""ENGINE-001 S2b-EGRET-P2: source-model ranked multirings, REAL Egret A/B.

Never treat OpenCV source masks as native coverage. No game CHALK.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path

import cv2
import numpy as np

from run_engine001_color32_s2b_egret_p1 import (
    EXP as P1_EXP, ALPHAS, ROI_SHAPE, ROI_X0,
    FROZEN_PALETTE_GIT_BLOB, FROZEN_RENDERER_GIT_BLOB,
    git_blob_sha, native_metrics, select_interior_loops,
)
from run_engine001_palette32_region_study import (
    read_source, read_palette, nearest32, sha,
)
from run_engine001_color32_s2_edge_protection import (
    strong_edges, protected_merge,
)
from run_engine001_v43p4_b3_contour_source import (
    contour_candidates, _safe_owner_footprint,
)
from run_engine001_complex_holdout_v5 import native_batch

EXP = "ENGINE001_COLOR32_S2B_EGRET_P2_NATIVE_MULTIRING"
OWNERS = (31, 29)
WIDTHS = (10, 6, 4, 2)
MAX_P2_STROKES = 256
MAX_P2_VERTICES = 1200
FROZEN_DETAILS = 410
FROZEN_DETAIL_VERTICES = 1792
MIN_NATIVE_RELATIVE_GAIN = 0.20


def plan_p2(g: np.ndarray, palette: np.ndarray) -> tuple[list[dict], dict]:
    if (not isinstance(g, np.ndarray) or g.shape != ROI_SHAPE or
            g.dtype != np.uint8 or palette.shape != (32, 3)
            or any(not np.any(g == owner) for owner in OWNERS)):
        raise ValueError("BLOCKED_P2_SOURCE_GEOMETRY")
    owner_masks = {owner: g == owner for owner in OWNERS}
    remaining = {owner: owner_masks[owner].copy() for owner in OWNERS}
    npaths, nverts = 0, 0
    accepted = []
    counts = {str(owner): {str(width): 0 for width in WIDTHS} for owner in OWNERS}
    rejected = {str(owner): 0 for owner in OWNERS}
    model_coverage = {}
    first_rejected = None

    for width in WIDTHS:
        # Existing B3 source contour generator; output footprints are ranking
        # proxies only. Actual acceptance uses real BoardPane RGBA below.
        candidates = {}
        used = {}
        for owner in OWNERS:
            own = owner_masks[owner]
            outside = cv2.distanceTransform(
                (~own).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
            eligible = []
            for candidate in contour_candidates(own, width):
                if not _safe_owner_footprint(candidate["footprint"], own, outside):
                    rejected[str(owner)] += 1
                    continue
                if not 2 <= candidate["vertices"] <= 128:
                    raise ValueError("BLOCKED_P2_PATH_VERTICES")
                eligible.append(candidate)
            candidates[owner] = eligible
            used[owner] = set()

        while True:
            proposals = []
            for owner in OWNERS:
                best = None
                for i, cand in enumerate(candidates[owner]):
                    if i in used[owner]:
                        continue
                    gain = int(np.count_nonzero(
                        cand["footprint"] & remaining[owner]))
                    if gain <= 0:
                        continue
                    # Prefer higher original-owner gain per vertex. Stable
                    # tie breaks use gain then owner ID then candidate index.
                    score = (gain / cand["vertices"], gain, -owner, -i)
                    if best is None or score > best[0]:
                        best = (score, i, cand, gain)
                if best is not None:
                    proposals.append((best[0], owner, best[1:]))
            if not proposals:
                break
            _, owner, (i, cand, gain) = max(proposals)
            used[owner].add(i)
            attempt_strokes, attempt_vertices = npaths + 1, nverts + cand["vertices"]
            if (attempt_strokes > MAX_P2_STROKES or
                    attempt_vertices > MAX_P2_VERTICES or
                    attempt_strokes + FROZEN_DETAILS > 3000 or
                    attempt_vertices + FROZEN_DETAIL_VERTICES > 5900):
                first_rejected = {
                    "owner": owner, "width": width, "candidate_index": i,
                    "attempted_paint_strokes": attempt_strokes,
                    "attempted_paint_vertices_NOT_CHALK": attempt_vertices,
                    "reason": "BLOCKED_RESOURCE",
                }
                break
            rgb = palette[owner]
            accepted.append({
                "strokeId": f"icon-{npaths}",
                "colorIndex": owner,
                "colorRgb": int((int(rgb[0]) << 16) |
                                (int(rgb[1]) << 8) | int(rgb[2])),
                "width": width,
                "points": [{"x": float(x + ROI_X0), "y": float(y)}
                           for x, y in cand["points"]],
            })
            remaining[owner][cand["footprint"] & owner_masks[owner]] = False
            counts[str(owner)][str(width)] += 1
            npaths, nverts = attempt_strokes, attempt_vertices
        if first_rejected:
            break

    for owner in OWNERS:
        target = int(np.count_nonzero(owner_masks[owner]))
        left = int(np.count_nonzero(remaining[owner]))
        model_coverage[str(owner)] = {
            "target": target,
            "remaining_model_only": left,
            "model_fraction_NOT_EGRET": (target - left) / target,
        }
    status = ("BLOCKED_RESOURCE" if first_rejected else
              "BLOCKED_NO_P2_OWNER_PATH" if set(s["colorIndex"] for s in accepted)
              != set(OWNERS) else "SOURCE_MODEL_READY_FOR_E3")
    evidence = {
        "status": status,
        "source_selection": list(OWNERS),
        "candidate_width_order": list(WIDTHS),
        "paint_paths": npaths, "paint_vertices_NOT_CHALK": nverts,
        "provisioned_total_strokes_with_V44B410": npaths + FROZEN_DETAILS,
        "provisioned_total_vertices_NOT_CHALK": nverts + FROZEN_DETAIL_VERTICES,
        "same_color_revisit_penalty": 0,
        "source_MODEL_ONLY_estimated_owner_coverage": model_coverage,
        "accepted_paths_by_width_and_owner": counts,
        "rejected_source_model_beyond_3px": rejected,
        "first_rejected": first_rejected,
        "safe_to_execute_game": False,
        "V44B_frozen_410_detail_unmodified_and_not_executed": True,
        "exact_game_CHALK": None,
    }
    return accepted, evidence


def compare_native(base: dict, candidate: dict) -> dict:
    gates = {}
    rows = {}
    for alpha in ALPHAS:
        for owner in OWNERS:
            p1 = base[str(alpha)][str(owner)]
            p2 = candidate[str(alpha)][str(owner)]
            den = p1["native_correct_owner_pixels"]
            if den <= 0:
                raise ValueError("BLOCKED_P1_NATIVE_ZERO_BASELINE")
            gain = (p2["native_correct_owner_pixels"] - den) / den
            zero_far = (p2["non_owner_beyond_3logical_px"] == 0 and
                        p2["ink_outside_image_ROI"] == 0)
            key = f"alpha{alpha}_owner{owner}"
            gates[key] = bool(gain >= MIN_NATIVE_RELATIVE_GAIN and zero_far)
            rows[key] = {
                "P1_native_owner_pixels": den,
                "P2_native_owner_pixels": p2["native_correct_owner_pixels"],
                "relative_gain": gain,
                "foreign_native_pixels_any_distance":
                    p2["non_owner_native_pixels_any_distance"],
                "foreign_beyond_3logical_px":
                    p2["non_owner_beyond_3logical_px"],
                "outside_ROI_native_pixels": p2["ink_outside_image_ROI"],
                "P2_fraction_of_full_owner_NOT_full_fill":
                    p2["isolated_fraction_of_full_owner_NOT_full_fill_coverage"],
            }
    return {"checks": gates, "measurements": rows,
            "native_P2_source_gate_pass": all(gates.values()),
            "NOT_full_image_quality_gate": True}


def run(workspace: Path, source: Path, palette_path: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("BLOCKED_P2_OUTPUT_EXISTS")
    if (git_blob_sha(palette_path) != FROZEN_PALETTE_GIT_BLOB or
            git_blob_sha(workspace / "AutoDraw_Stage20/tests/game_renderer_reference.js")
            != FROZEN_RENDERER_GIT_BLOB):
        raise ValueError("BLOCKED_P2_GAME_SOURCE_DRIFT")
    _, src = read_source(source)
    palette = read_palette(palette_path)
    b = nearest32(src, palette)
    strong, _ = strong_edges(src)
    g, _ = protected_merge(src, b, palette, strong)
    p1, info = select_interior_loops(g, palette)
    if [s["colorIndex"] for s in p1] != list(OWNERS):
        raise ValueError("BLOCKED_P2_P1_BASELINE_SELECTION_DRIFT")
    p2, planned = plan_p2(g, palette)
    if planned["status"] != "SOURCE_MODEL_READY_FOR_E3":
        raise ValueError("P2 " + planned["status"] + ": no partial native render")
    p1 = [{**s, "width": 10} for s in p1]
    output.mkdir(parents=True)
    (output / "source-plan.json").write_text(json.dumps({
        "experiment": EXP, "source_sha256": sha(source),
        "palette_git_blob": FROZEN_PALETTE_GIT_BLOB,
        "renderer_git_blob": FROZEN_RENDERER_GIT_BLOB,
        "G_index_sha256": hashlib.sha256(g.tobytes()).hexdigest(),
        "P1_immutable_reference_experiment": P1_EXP,
        "P1_width10_paths": p1, "P2_adaptive_paths": p2,
        "P2_model_preflight": planned,
        "safe_to_execute_game": False, "game_CHALK": None,
    }, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    native = {}
    for kind, paths in (("P1-W10", p1), ("P2-MULTIRING", p2)):
        folder = output / kind
        folder.mkdir()
        capture, metadata, native_run = native_batch(
            workspace, "S2B-"+kind, paths, folder,
            renderer_method="renderComplexHoldoutColorProbe")
        native[kind] = {
            "metrics": native_metrics(capture, g, paths),
            "metadata": metadata, "renderer_run": native_run,
            "stroke_count": len(paths),
            "synthetic_vertices_NOT_CHALK": sum(len(p["points"]) for p in paths),
        }
    compared = compare_native(native["P1-W10"]["metrics"],
                              native["P2-MULTIRING"]["metrics"])
    hashes = {str(p.relative_to(output)).replace("\\", "/"): sha(p)
              for p in output.rglob("*") if p.is_file()}
    report = {
        "experiment": EXP, "status": ("NATIVE_P2_SOURCE_GATE_PASS_NOT_FULL_FILL"
                                     if compared["native_P2_source_gate_pass"] else
                                     "NATIVE_P2_SOURCE_GATE_FAIL_NOT_FULL_FILL"),
        "github_sha": os.environ.get("GITHUB_SHA"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "source_sha256": sha(source),
        "palette_git_blob": FROZEN_PALETTE_GIT_BLOB,
        "renderer_git_blob": FROZEN_RENDERER_GIT_BLOB,
        "native_renderer": "original archived BoardPane Firefox WebGL",
        "P1_frozen_run_id": 44007375262,
        "P1_frozen_report_sha256":
            "bf3495f409850a348c097042165002f631cfdbbd498a184773fd3a91f43116f4",
        "p2_preflight": planned,
        "native_variants": native,
        "native_comparison": compared,
        "full_image_quality": "NOT_RUN",
        "visual_review": "PENDING",
        "original_V44B_410_colored_detail_last": "NOT_RENDERED_UNMODIFIED",
        "game_E4": "NOT_RUN", "E5": "NOT_RUN", "exact_game_CHALK": None,
        "production_accepted": False,
        "report_linked_SHA256": hashes,
        "versions": {"Python": platform.python_version(), "numpy": np.__version__,
                     "opencv": cv2.__version__},
    }
    (output / "report.json").write_text(json.dumps(
        report, ensure_ascii=False, indent=2, allow_nan=False)+"\n",encoding="utf-8")
    return report


def main():
    p=argparse.ArgumentParser()
    for arg in ("workspace","source","palette","output"):
        p.add_argument("--"+arg,required=True,type=Path)
    args=p.parse_args()
    report=run(args.workspace,args.source,args.palette,args.output)
    print(json.dumps({
        "status": report["status"],
        "P2_paths": report["p2_preflight"]["paint_paths"],
        "P2_vertices": report["p2_preflight"]["paint_vertices_NOT_CHALK"],
        "comparison": report["native_comparison"]["measurements"],
        "exact_game_CHALK": None,
    },ensure_ascii=False))


if __name__ == "__main__":
    main()

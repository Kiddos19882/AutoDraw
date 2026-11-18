#!/usr/bin/env python3
"""B1-R-P4B3 original-only native 3x backing-grid phase probe.

Only shift existing P4B2 corrective strokes; no new points, radius,
palette mapping or baseline A strokes. Native Egret/WebGL only, NOT live E4.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import run_engine001_b1r_p4b2_native_edge_repair as p4b2
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
from run_engine001_b1r_p1_fullrgb_edge_aware import check_source
from run_engine001_b1r_p2_joint_region_outline import digest
from run_engine001_complex_holdout_v5 import native_batch

EXPERIMENT = "ENGINE001_B1R_P4B3_NATIVE_GRID_PHASE_V1"
SOURCE_P4B1_BLOB = "b95aa361cf2ec94d5fa28e7309bd3e4af15eca93"
SOURCE_P4B2_BLOB = "0053829480c6327ef5c541024593f6e0018aa35e"
RENDERER_BLOB = "76d950e0a8911888a9df3b675b866519ecf7bba4"
METHODS = ("E_SOBEL90", "F_SOBEL90_LAB12")
PHASES = {
    "S_X25": (0.25, 0.0),
    "S_Y25": (0.0, 0.25),
    "S_XY25": (0.25, 0.25),
}
ALPHA_GATE = 24
SOURCE_KEY = "C_192_D_COMPONENT24"
OWNER = 115
FIXED_STROKES = 250
FIXED_VERTICES = 500
NATIVE_COVERAGE_GATE = .99
FAR_LEAKAGE_LOGICAL = 3.0


def verify_code_blob(path: Path, wanted: str):
    if p4b1.git_blob(path.read_bytes()) != wanted:
        raise ValueError("BLOCKED_P4B3_PINNED_NATIVE_OR_BASELINE_CODE")


def shift_correctives(baseline: list[dict], corrections: list[dict],
                      owner_mask: np.ndarray, phase: str):
    """All-or-nothing, only corrected points translated on original component."""
    if (phase not in PHASES or owner_mask.shape != (240, 150) or
            owner_mask.dtype != np.bool_ or
            not isinstance(baseline, list) or
            not isinstance(corrections, list) or
            len(baseline) + len(corrections) != FIXED_STROKES or
            sum(len(s["points"]) for s in baseline+corrections) != FIXED_VERTICES):
        raise ValueError("BLOCKED_P4B3_INVARIANT_INPUT")
    dx, dy = PHASES[phase]
    all_shifted = []
    for idx, stroke in enumerate(corrections):
        if (stroke.get("width") != 2 or stroke.get("colorIndex") != OWNER or
                len(stroke.get("points", [])) != 2 or
                stroke.get("strokeId") != "icon-%d" % (len(baseline)+idx)):
            raise ValueError("BLOCKED_P4B3_CORRECTION_PROVENANCE")
        candidate = {
            **stroke,
            "points": [
                {"x": float(p["x"])+dx, "y": float(p["y"])+dy}
                for p in stroke["points"]
            ],
        }
        points_xy = [
            (float(p["x"])-p4b1.ROI_X0, float(p["y"]))
            for p in candidate["points"]
        ]
        if (any(not (np.isfinite(x) and np.isfinite(y) and
                     0 <= x < 150 and 0 <= y < 240)
                for x,y in points_xy) or
                not p4b1._source_centerline(points_xy, owner_mask)):
            raise ValueError("BLOCKED_P4B3_PHASE_SOURCE_OWNER_OR_BOARD")
        all_shifted.append(candidate)
    # Unmodified baseline records and their order as immutable control.
    if len(all_shifted) != len(corrections):
        raise AssertionError("BLOCKED_P4B3_DROPPED_CORRECTION")
    replay = baseline + all_shifted
    if (len(replay) != FIXED_STROKES or
            sum(len(s["points"]) for s in replay) != FIXED_VERTICES or
            any(s["colorIndex"] != OWNER for s in replay)):
        raise AssertionError("BLOCKED_P4B3_SOURCE_RESOURCE_DRIFT")
    return replay


def actual_native_metrics(rgba: np.ndarray, blank: np.ndarray,
                          mask: np.ndarray, full_owner: np.ndarray):
    if (mask.shape != (240,150) or mask.dtype != np.bool_ or
            full_owner.shape != mask.shape or
            not np.all(~mask | full_owner)):
        raise ValueError("BLOCKED_P4B3_INVALID_OWNER_MASK")
    return p4b1.native_metrics(rgba, blank, mask, full_owner)


def residual_phase(rgba: np.ndarray, mask: np.ndarray):
    if (rgba.shape != (720, 1380, 4) or rgba.dtype != np.uint8 or
            mask.shape != (240, 150) or mask.dtype != np.bool_):
        raise ValueError("BLOCKED_P4B3_INVALID_NATIVE_PHASE_DATA")
    expanded = np.repeat(np.repeat(mask, 3, axis=0), 3, axis=1)
    ink = rgba[:,155*3:(155+150)*3,3] >= ALPHA_GATE
    missed = expanded & ~ink
    counts = np.zeros((3,3), np.int64)
    for yi in range(3):
        for xi in range(3):
            counts[yi,xi] = int(missed[yi::3,xi::3].sum())
    return {
        "native_missing_backing_pixels": int(missed.sum()),
        "x_mod3": counts.sum(axis=0).astype(int).tolist(),
        "y_mod3": counts.sum(axis=1).astype(int).tolist(),
        "phase_matrix_yx": counts.astype(int).tolist(),
        "source_missing_logical_pixels": int(
            missed.reshape(240,3,150,3).any(axis=(1,3)).sum()),
    }


def source_overlay(rgb: np.ndarray, component: np.ndarray, rgba: np.ndarray):
    return p4b2.overlay(rgb, component, rgba)


def run(workspace: Path, source: Path, engine_js: Path,
        renderer: Path, output: Path):
    if output.exists():
        raise ValueError("BLOCKED_P4B3_EXISTING_OUTPUT")
    check_source(source)
    verify_code_blob(Path(p4b1.__file__), SOURCE_P4B1_BLOB)
    verify_code_blob(Path(p4b2.__file__), SOURCE_P4B2_BLOB)
    verify_code_blob(renderer, RENDERER_BLOB)
    output.mkdir(parents=True)
    results = {}
    image_rows = {}
    with tempfile.TemporaryDirectory(prefix="engine001-p4b3-original-only-") as d:
        parent_dir = Path(d) / "p4b2_current_run"
        parent = p4b2.run(workspace,source,engine_js,renderer,parent_dir)
        if (parent["experiment"] != p4b2.EXPERIMENT or
                parent["result"] != "NATIVE_EDGE_REPAIR_PARTIAL_OR_FAIL" or
                not parent["P4B1_recomputed_current_run_original_only"] or
                parent["legacy_G32_P4c1_V44_as_input"] or
                parent["read_frozen_P4B1_P3D_ZIPs_for_candidate"] or
                set(parent["methods_results"]) != set(METHODS)):
            raise ValueError("BLOCKED_P4B3_PARENT_P4B2_DRIFT")
        shutil.copyfile(parent_dir/"report.json",
                        output/"P4B2_FRESH_PARENT_REPORT.json")
        shutil.copyfile(parent_dir/"SOURCE_ORIGINAL_LOGICAL_RGB.png",
                        output/"SOURCE_ORIGINAL_LOGICAL_RGB.png")
        for method in METHODS:
            prefix = method + "_"
            p_obj = parent["methods_results"][method]
            if (p_obj["status"] != "NATIVE_EDGE_REPAIR_INCOMPLETE_OR_FAIL" or
                    p_obj["source_owner_engine_index"] != OWNER or
                    p_obj["correction_decision"]["combined_stroke_count"] != FIXED_STROKES or
                    p_obj["correction_decision"]["combined_synthetic_vertices_NOT_CHALK"] != FIXED_VERTICES):
                raise ValueError("BLOCKED_P4B3_PARENT_EXPECTED_NEGATIVE_DRIFT")
            original_file = parent_dir/(prefix+"ORIGINAL_A_STROKES.json")
            correction_file = parent_dir/(prefix+"P4B2_CORRECTIVE_STROKES.json")
            full_file = parent_dir/(prefix+"P4B2_FULL_REPLAY_STROKES.json")
            base_raw = json.loads(original_file.read_text(encoding="utf8"))
            correction_raw = json.loads(correction_file.read_text(encoding="utf8"))
            parent_full = json.loads(full_file.read_text(encoding="utf8"))
            base = [{
                k: p[k] for k in ("strokeId","width","colorIndex",
                                  "colorRgb","points")
            } for p in base_raw]
            if parent_full != base + correction_raw:
                raise ValueError("BLOCKED_P4B3_PARENT_STROKE_LIST_MISMATCH")
            mask = np.asarray(Image.open(parent_dir/(prefix+"OWNER_COMPONENT.png")).convert("L"),
                              dtype=np.uint8) > 0
            index = np.asarray(Image.open(parent_dir/(prefix+"SOURCE_ENGINE_INDICES.png")),
                               dtype=np.uint8).copy()
            rgb = np.asarray(Image.open(parent_dir/(prefix+"SOURCE_RGB.png")).convert("RGB"),
                             dtype=np.uint8).copy()
            full_owner = index == OWNER
            if not mask.any() or np.any(mask & ~full_owner):
                raise ValueError("BLOCKED_P4B3_SOURCE_MASK_DRIFT")
            shutil.copyfile(parent_dir/(prefix+"SOURCE_RGB.png"),
                            output/(prefix+"SOURCE_RGB.png"))
            shutil.copyfile(parent_dir/(prefix+"SOURCE_ENGINE_INDICES.png"),
                            output/(prefix+"SOURCE_ENGINE_INDICES.png"))
            shutil.copyfile(parent_dir/(prefix+"OWNER_COMPONENT.png"),
                            output/(prefix+"OWNER_COMPONENT.png"))
            shutil.copyfile(full_file,output/(prefix+"P4B2_CONTROL_REPLAY_STROKES.json"))
            source_png = parent_dir/("NATIVE_P4B2_"+method)/(
                "P4B2-"+method+"-color-115.png")
            original_rgba = np.asarray(Image.open(source_png).convert("RGBA"),
                                       dtype=np.uint8).copy()
            shutil.copyfile(source_png,output/(prefix+"P4B2_ACTUAL_NATIVE_COLOR.png"))
            blank_png = parent_dir/("NATIVE_P4B2_"+method)/(
                "P4B2-"+method+"-blank.png")
            original_blank = np.asarray(Image.open(blank_png).convert("RGBA"),
                                        dtype=np.uint8).copy()
            previous_metrics, original_blank_count = actual_native_metrics(
                original_rgba, original_blank, mask, full_owner)
            if (original_blank_count != 0 or
                    abs(previous_metrics["24"]["native_component_coverage"] -
                        p_obj["corrected_native_after"]["24"]["native_component_coverage"]) > 1e-12):
                raise ValueError("BLOCKED_P4B3_PARENT_NATIVE_E3_DRIFT")
            result = {
                "original_control_source_rgb_sha256": digest(rgb.tobytes()),
                "original_p4b2_native_alpha24": previous_metrics["24"],
                "original_p4b2_native_missing_grid_phases": residual_phase(
                    original_rgba, mask),
                "original_blank_alpha_nonzero": original_blank_count,
                "corrective_strokes": len(correction_raw),
                "original_strokes": len(base),
                "original_combined_vertices_NOT_CHALK": FIXED_VERTICES,
                "fixed_phase_variants": {},
            }
            image_rows[method] = [(
                "P4B2 BASELINE",
                source_overlay(rgb, mask, original_rgba),
                previous_metrics["24"]["native_component_coverage"],
            )]
            for phase in PHASES:
                phase_item = {"method":method,"phase":phase,
                              "dx_dy_logical":list(PHASES[phase])}
                try:
                    strokes = shift_correctives(base, correction_raw, mask, phase)
                except ValueError as error:
                    phase_item.update({
                        "status":"BLOCKED_SOURCE_CENTERLINE",
                        "reason":str(error),
                        "actual_native_e3_capture":"NOT_RUN",
                        "source_color_remained_unchanged":True,
                        "native_quality_pass":False,
                    })
                    result["fixed_phase_variants"][phase] = phase_item
                    print("P4B3_PHASE_BLOCKED",method,phase,str(error),
                          flush=True)
                    continue
                path_file = output/(prefix+phase+"_SHIFTS_ONLY_STROKES.json")
                path_file.write_text(json.dumps(
                    strokes,ensure_ascii=False,indent=2,allow_nan=False)+"\n",
                    encoding="utf8")
                scene_dir = output/("NATIVE_"+method+"_"+phase)
                scene_dir.mkdir()
                native,meta,manifest = native_batch(
                    workspace,"P4B3-"+method+"-"+phase,strokes,scene_dir,
                    renderer_method="renderP4A2BrushWidths1to10Probe")
                if (set(native) != {"blank","composite","color-115"} or
                        set(meta) != set(native) or
                        manifest["colors_rendered"] != [OWNER] or
                        meta["composite"].get("schema") !=
                        "ENGINE001_B1R_P4A2_NATIVE_1_TO_10" or
                        meta["composite"].get("renderer") !=
                        "real Egret 5.4.1 BoardPane/WebGLRenderer"):
                    raise ValueError("BLOCKED_P4B3_NATIVE_RENDERER_E3_NOT_MATCHED")
                scored, blank_count = actual_native_metrics(
                    native["color-115"],native["blank"],mask,full_owner)
                before=previous_metrics["24"]["native_component_coverage"]
                after=scored["24"]["native_component_coverage"]
                far=scored["24"]["native_beyond3logicalpx_other_color_pixels"]
                quality = bool(blank_count == 0 and
                               scored["24"]["native_nonzero_ink_backing_pixels"] > 0 and
                               after >= NATIVE_COVERAGE_GATE and far == 0 and
                               after >= before - 1e-9)
                phase_item.update({
                    "status":"NATIVE_PHASE_PASS" if quality else "NATIVE_PHASE_FAIL",
                    "actual_native_e3_capture":"PASS",
                    "native_quality_pass":quality,
                    "same_source_original_P3D_RGB":True,
                    "original_P4B1_strokes_unchanged":True,
                    "native_blank_nonzero_alpha_pixels":blank_count,
                    "alpha_metrics":scored,
                    "native_missing_grid_phases":residual_phase(
                        native["color-115"],mask),
                    "native_gain_fraction":after-before,
                    "source_original_owner_index":OWNER,
                    "cumulative_strokes":FIXED_STROKES,
                    "cumulative_synthetic_vertices_NOT_CHALK":FIXED_VERTICES,
                })
                result["fixed_phase_variants"][phase] = phase_item
                image_rows[method].append((
                    phase,source_overlay(rgb,mask,native["color-115"]),after
                ))
                print("P4B3_NATIVE_PHASE",method,phase,
                      phase_item["status"],"coverage",round(after,7),
                      "before",round(before,7),"far",far,flush=True)
            results[method]=result
    # This is a diagnostic panel; native color PNG remain separate in ZIP.
    canvas=Image.new("RGB",(1800,1540),"white")
    draw=ImageDraw.Draw(canvas)
    draw.text((9,7),"P4B3 ACTUAL EGRET ALPHA24 / GREEN INK ON OWNER / RED MISSING",
              fill=(0,0,0))
    for row,method in enumerate(METHODS):
        y=30+row*755
        for col,(name,im,cov) in enumerate(image_rows[method]):
            x=450*col
            draw.text((x+6,y),method+" "+name+" "+f"{cov*100:.3f}%",
                      fill=(0,0,0))
            canvas.paste(im,(x,y+25))
    canvas.save(output/"REVIEW_P4B3_NATIVE_PHASES_3X_GRID.png")
    (output/"README_REVIEW_RU.txt").write_text(
        "P4B3 — независимая проверка субпиксельного положения уже "
        "существующих коррекций P4B2.\n"
        "Все 3 сдвига исходно зафиксированы: +0.25 X / +0.25 Y / +0.25 XY.\n"
        "Зеленый — реальный Egret alpha24 в выбранной исходной цветовой области, "
        "красный — действительные пропуски.\n"
        "NATIVE_* — реальная архивная Egret/BoardPane WebGL, "
        "PARTIAL/BLOCKED сохранить.\n"
        "Оригинальный RGB/P3D неизменен, никакого G32/V44, "
        "ничего не запускалось в настоящей игре.\n"
        "Exact CHALK E4 E5 NOT_RUN.\n",encoding="utf8")
    e3_count=sum(
        results[method]["fixed_phase_variants"][phase].get(
            "actual_native_e3_capture") == "PASS"
        for method in METHODS for phase in PHASES)
    total_quality=sum(
        results[method]["fixed_phase_variants"][phase]["native_quality_pass"]
        for method in METHODS for phase in PHASES)
    overall = (
        "NATIVE_PHASE_ALL_6_PASS" if total_quality == 6 else
        "NATIVE_PHASE_SOME_QUALITY_PASS" if total_quality > 0 else
        "NATIVE_PHASE_SOURCE_BLOCKED_OR_QUALITY_FAIL")
    hashes = {
        str(p.relative_to(output)).replace("\\", "/"): digest(p.read_bytes())
        for p in sorted(output.rglob("*")) if p.is_file()
    }
    report={
        "experiment":EXPERIMENT,
        "prereg":"ENGINE001_B1R_P4B3_NATIVE_GRID_PHASE_V1",
        "status":overall,
        "actual_native_E3_phase_scenes":e3_count,
        "planned_phase_source_method_comparisons":6,
        "actual_phase_99_gate_PASS_count":total_quality,
        "source_original_only_P4B1_P4B2_recomputed":True,
        "frozen_P4B1_P4B2_archive_used_as_input":False,
        "legacy_G32_V44_P4c1_candidate_used":False,
        "source_SHA256":p4b2.SOURCE_SHA,
        "engine_git_blob_sha1":p4b2.ENGINE_GIT_BLOB_SHA1,
        "renderer_git_blob_sha1":RENDERER_BLOB,
        "p4b1_source_runner_blob_sha1":SOURCE_P4B1_BLOB,
        "p4b2_source_runner_blob_sha1":SOURCE_P4B2_BLOB,
        "methods":list(METHODS),
        "phases":{k:list(v) for k,v in PHASES.items()},
        "fixed_resource_stroke_cap":FIXED_STROKES,
        "fixed_resource_vertices_cap_NOT_CHALK":FIXED_VERTICES,
        "native_coverage_gate":NATIVE_COVERAGE_GATE,
        "far_leakage_logical_gate":FAR_LEAKAGE_LOGICAL,
        "source_results":results,
        "real_game_E4":"NOT_RUN",
        "independent_E5":"NOT_RUN",
        "exact_run_bound_CHALK":None,
        "production_promotion":False,
        "github_sha":os.getenv("GITHUB_SHA"),
        "github_run_id":os.getenv("GITHUB_RUN_ID"),
        "file_sha256":hashes,
    }
    (output/"report.json").write_text(json.dumps(
        report,indent=2,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf8")
    return report


if __name__=="__main__":
    arg=argparse.ArgumentParser()
    arg.add_argument("--workspace",required=True,type=Path)
    arg.add_argument("--source",required=True,type=Path)
    arg.add_argument("--engine-js",required=True,type=Path)
    arg.add_argument("--renderer",required=True,type=Path)
    arg.add_argument("--output",required=True,type=Path)
    opts=arg.parse_args()
    try:
        result=run(opts.workspace,opts.source,opts.engine_js,
                   opts.renderer,opts.output)
    except Exception as error:
        if not opts.output.exists():
            opts.output.mkdir(parents=True)
        (opts.output/"FAILED_EVIDENCE.json").write_text(
            json.dumps({
                "experiment":EXPERIMENT,"status":"BLOCKED_TECHNICAL",
                "error":str(error),"error_type":type(error).__name__,
                "github_sha":os.getenv("GITHUB_SHA"),
                "github_run_id":os.getenv("GITHUB_RUN_ID"),
                "game_E4":"NOT_RUN","exact_CHALK":None,
            },indent=2,ensure_ascii=False)+"\n",encoding="utf8")
        raise
    print("P4B3_OVERALL_NATIVE_E3",result["status"],
          result["actual_native_E3_phase_scenes"],"of6 actual scenes",
          result["actual_phase_99_gate_PASS_count"],"quality passes",
          "exact CHALK NOT_RUN",flush=True)

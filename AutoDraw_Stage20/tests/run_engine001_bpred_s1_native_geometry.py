#!/usr/bin/env python3
"""BPRED-S1: E0-registered source-derived two-point Egret centroid/bounds experiment.

Only S0 CALIBRATION (120 scenes) is rendered by the authentic P4D3 BoardPane
runner. S0 BLIND and its exact-replay controls remain untouched for S4.
Geometry predictions are MODEL_ONLY, never alpha/owner quality claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import statistics

import numpy as np

import run_engine001_bpred_s0_corpus_audit as s0
import run_engine001_b1r_p4d3_native_brush_repeatability as p4d3
import run_engine001_b1r_p4d14_egret_halfpixel_centroid as p4d14
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
from run_engine001_b1r_p2_joint_region_outline import digest

EXPERIMENT = "ENGINE001_BPRED_S1_GEOMETRY_V1"
PREREG = "ENGINE001_BPRED001_S1_SOURCE_GEOMETRY_NATIVE_PREREG_2026-11-20.md"
S0_RUN = "44644039555"
S0_ARTIFACT = 14586574667
P4D14_BLOB = "21000076aedf2a2db65d3b0d7db88525e33bf5da"
S0_BLOB = "4b4166dafce7d04d8b34976734cf775cec748024"
SCENE_COUNT = 120
CENTER_OBSERVATIONS = 360
ALPHA_THRESHOLDS = (1, 24)
H1_RATIO = 0.5
H1_M1_MAX_MEAN_LOGICAL = 0.20


def blocked(reason):
    raise ValueError("BLOCKED_BPRED_S1_" + reason)


def save_json(path: Path, item):
    """No accidental overwrite of native evidence or the frozen plan."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as f:
        f.write(json.dumps(item, ensure_ascii=False, indent=2,
                           allow_nan=False).encode("utf8") + b"\n")


def adapt_runtime_plan(source: dict) -> list[dict]:
    """Only transport identity bpred-N -> icon-N; numerical input stays frozen."""
    strokes = source["strokes"]
    if len(strokes) != 3 or source["split"] != "CALIBRATION":
        blocked("NOT_THREE_FROZEN_CALIBRATION")
    if s0.sha256(s0.canonical_json(strokes)) != source["plan_sha256"]:
        blocked("SOURCE_PLAN_SHA")
    adapted = []
    for n, stroke in enumerate(strokes):
        if (stroke.get("strokeId") != "bpred-" + str(n) or
            type(stroke.get("width")) is not int or
            stroke["width"] != source["width"] or
            stroke.get("colorIndex") != 1 or
            stroke.get("colorRgb") != s0.OWNER_COLOR or
            not isinstance(stroke.get("points"), list) or
            len(stroke["points"]) != 2):
            blocked("FROZEN_STROKE_FIELDS")
        points = stroke["points"]
        if any(type(p.get(k)) not in (int, float) or
               not math.isfinite(p[k]) for p in points for k in ("x", "y")):
            blocked("NONFINITE_POINTS")
        adapted.append({**stroke, "strokeId": "icon-" + str(n)})
        if {k: v for k, v in adapted[-1].items() if k != "strokeId"} != {
            k: v for k, v in stroke.items() if k != "strokeId"}:
            blocked("UNAUTHORIZED_GEOMETRY_CHANGE")
    return adapted


def validate_frozen_source(path: Path) -> tuple[dict, str]:
    """Use original S0 artifact data, NOT recomputed S0 floats on another OS."""
    if not path.is_file():
        blocked("MISSING_S0_MANIFEST")
    if s0.git_blob(Path(s0.__file__).read_bytes()) != S0_BLOB:
        blocked("S0_RUNNER_SHA")
    if s0.git_blob(Path(p4d14.__file__).read_bytes()) != P4D14_BLOB:
        blocked("P4D14_RUNNER_SHA")
    manifest = json.loads(path.read_text("utf8"))
    if (manifest.get("schema") != s0.SCHEMA or
        manifest.get("scene_count_planned") != 251 or
        manifest.get("base_head") != s0.BASELINE_SHA or
        len(manifest.get("calibration", [])) != SCENE_COUNT or
        len(manifest.get("blind_holdout", [])) != 120 or
        len(manifest.get("controls", [])) != 11):
        blocked("SOURCE_MANIFEST_SCHEMA")
    source_ids = set()
    expected_groups = set()
    for row in manifest["calibration"]:
        if row["sample_id"] in source_ids:
            blocked("SOURCE_DUPLICATE")
        source_ids.add(row["sample_id"])
        width = row.get("width")
        angle = row.get("angle_deg")
        length = row.get("length_logical")
        px, py = row.get("phase_x"), row.get("phase_y")
        if (width not in range(1, 11) or angle not in s0.CAL_ANGLES or
            length not in s0.LENGTHS or (px, py) not in
            tuple((x / 16, y / 16) for x, y in s0.PHASES)):
            blocked("SOURCE_CASE_NOT_PREREG")
        if (row.get("family_id") != f"W{width:02d}_A{angle % 180:03d}_L{length:02d}" or
            row.get("capture_status") != "NOT_RUN" or
            row.get("native_png_sha256") is not None or
            row.get("game_blob") != s0.GAME_BLOB or
            row.get("renderer_blob") != s0.RENDERER_BLOB):
            blocked("SOURCE_CASE_DRIFT")
        expected_groups.add((width, angle, length, px, py))
        adapt_runtime_plan(row)
    expected = {(w, a, le, x / 16, y / 16)
                for w in range(1, 11) for a in s0.CAL_ANGLES
                for le in s0.LENGTHS for x, y in s0.PHASES}
    if expected_groups != expected or len(source_ids) != SCENE_COUNT:
        blocked("SOURCE_MATRIX_INCOMPLETE")
    blind_groups = {r["family_id"] for r in manifest["blind_holdout"]}
    if blind_groups & {r["family_id"] for r in manifest["calibration"]}:
        blocked("BLIND_FAMILY_LEAKAGE")
    if any(x["capture_status"] != "NOT_RUN" for x in manifest["blind_holdout"]):
        blocked("BLIND_ALREADY_EXPOSED")
    return manifest, s0.sha256(path.read_bytes())


def validate_s0_artifact(root: Path, manifest_sha: str) -> None:
    report = root / "report.json"
    if not report.is_file():
        blocked("S0_ARTIFACT_REPORT_MISSING")
    data = json.loads(report.read_text("utf8"))
    if (data.get("schema") != s0.SCHEMA or
        data.get("github_run_id") != S0_RUN or
        data.get("github_sha") != "5b6ed18a065740c3a99b3463129c36118fc6514c" or
        data.get("future_scene_plan_sha256") != manifest_sha or
        data.get("verified_original_artifacts") != 7 or
        data.get("verified_member_files") != 3961 or
        data.get("original_archives_crc_sha") != "PASS" or
        data.get("future_scenes_rendered") != 0):
        blocked("S0_ARTIFACT_PROVENANCE")


def model_center(stroke: dict, source_halfpixel: bool):
    """Thin reuse of previously pinned P4D14 source-derived source geometry."""
    return p4d14.model_center(stroke, source_halfpixel)


def ideal_bbox_physical(stroke: dict, use_source_shift: bool) -> tuple[int, int, int, int]:
    """MODEL_ONLY continuous round capsule AABB (exclusive upper edge), physical."""
    w = stroke["width"]
    pts = stroke["points"]
    if type(w) is not int or w not in range(1, 11) or len(pts) != 2:
        blocked("BBOX_INPUT")
    sh = p4d14.egret_graphics_halfpixel(w) if use_source_shift else 0.0
    radius = w / 2.0
    min_x = min(pt["x"] for pt in pts) + sh - radius
    max_x = max(pt["x"] for pt in pts) + sh + radius
    min_y = min(pt["y"] for pt in pts) + sh - radius
    max_y = max(pt["y"] for pt in pts) + sh + radius
    if any(not math.isfinite(v) for v in (min_x,max_x,min_y,max_y)):
        blocked("NONFINITE_BBOX")
    bounds = (math.floor(min_x * 3), math.floor(min_y * 3),
              math.ceil(max_x * 3), math.ceil(max_y * 3))
    if not (0 <= bounds[0] < bounds[2] <= 1380 and
            0 <= bounds[1] < bounds[3] <= 720):
        blocked("BBOX_CLIPPED")
    return bounds


def physical_bbox_miss(roi: np.ndarray, center: tuple, bounds, threshold: int) -> int:
    if roi.shape != (162, 162, 4) or roi.dtype != np.uint8 or threshold not in ALPHA_THRESHOLDS:
        blocked("ROI_FORMAT")
    y0 = (center[1] - 27) * 3
    x0 = (center[0] - 27) * 3
    yy, xx = np.nonzero(roi[:,:,3] >= threshold)
    return int(np.count_nonzero((xx+x0 < bounds[0]) | (xx+x0 >= bounds[2]) |
                                (yy+y0 < bounds[1]) | (yy+y0 >= bounds[3])))


def measured_row(case: dict, native: np.ndarray, adapted: list[dict], image_sha: str):
    if (native.shape != p4d3.NATIVE_SHAPE or native.dtype != np.uint8 or
        len(adapted) != 3):
        blocked("NATIVE_SHAPE")
    samples = []
    native_ink_total = int(np.count_nonzero(native[:,:,3]))
    ink_in_rois = 0
    for i, center in enumerate(s0.CENTERS):
        roi = p4d3.roi(native, *center)
        ink_in_rois += int(np.count_nonzero(roi[:,:,3]))
        measured = p4d14.native_alpha_centroid(roi, *center)
        m0 = model_center(adapted[i], False)
        m1 = model_center(adapted[i], True)
        e0 = p4d14.euclidean(measured, m0)
        e1 = p4d14.euclidean(measured, m1)
        b0 = ideal_bbox_physical(adapted[i], False)
        b1 = ideal_bbox_physical(adapted[i], True)
        samples.append({
            "center_logical": list(center), "native_centroid_logical": list(measured),
            "M0_center_logical": list(m0), "M1_center_logical": list(m1),
            "M0_error_logical": e0, "M1_error_logical": e1,
            "M0_bbox_physical": list(b0), "M1_bbox_physical": list(b1),
            "bbox_model_only": True,
            "M0_bbox_false_negative_alpha1_physical": physical_bbox_miss(roi,center,b0,1),
            "M1_bbox_false_negative_alpha1_physical": physical_bbox_miss(roi,center,b1,1),
            "M0_bbox_false_negative_alpha24_physical": physical_bbox_miss(roi,center,b0,24),
            "M1_bbox_false_negative_alpha24_physical": physical_bbox_miss(roi,center,b1,24),
            "native_alpha_sum": int(roi[:,:,3].astype(np.uint64).sum())
        })
        if samples[-1]["native_alpha_sum"] <= 0:
            blocked("EMPTY_NATIVE_CELL")
    if native_ink_total != ink_in_rois:
        blocked("UNEXPECTED_INK_OUTSIDE_THREE_ROIS")
    return {
        "sample_id": case["sample_id"], "family_id": case["family_id"],
        "width": case["width"], "angle_deg": case["angle_deg"],
        "length_logical": case["length_logical"],
        "phase_x": case["phase_x"], "phase_y": case["phase_y"],
        "original_plan_sha256": case["plan_sha256"],
        "runtime_plan_sha256": s0.sha256(s0.canonical_json(adapted)),
        "native_png_sha256": image_sha, "native_ink_physical": ink_in_rois,
        "cells": samples
    }


def aggregate(cases: list[dict]):
    if not cases:
        blocked("EMPTY_SUMMARY")
    cells = [c for r in cases for c in r["cells"]]
    e0 = [c["M0_error_logical"] for c in cells]
    e1 = [c["M1_error_logical"] for c in cells]
    odd = [c for r in cases if r["width"] in (1,3) for c in r["cells"]]
    others = [c for r in cases if r["width"] not in (1,3) for c in r["cells"]]
    odd0 = statistics.fmean(c["M0_error_logical"] for c in odd)
    odd1 = statistics.fmean(c["M1_error_logical"] for c in odd)
    other_eq = all(c["M0_error_logical"] == c["M1_error_logical"] and
                   c["M0_center_logical"] == c["M1_center_logical"]
                   for c in others)
    out = {
        "n_cases":len(cases), "n_observations":len(cells),
        "M0_mean_error_logical":float(statistics.fmean(e0)),
        "M1_mean_error_logical":float(statistics.fmean(e1)),
        "odd_1_3_count":len(odd),
        "odd_M0_mean_error":float(odd0), "odd_M1_mean_error":float(odd1),
        "odd_error_reduction_fraction":float(1-odd1/odd0) if odd0 else None,
        "other_widths_count":len(others), "other_width_predictions_exactly_same":other_eq,
        "per_width": {
            str(w): {
                "n":len([c for r in cases if r["width"]==w for c in r["cells"]]),
                "M0_mean":float(statistics.fmean(c["M0_error_logical"] for r in cases
                                 if r["width"]==w for c in r["cells"])),
                "M1_mean":float(statistics.fmean(c["M1_error_logical"] for r in cases
                                 if r["width"]==w for c in r["cells"])),
                "M1_p95":float(np.quantile([c["M1_error_logical"] for r in cases
                               if r["width"]==w for c in r["cells"]],0.95))
            } for w in range(1,11)
        },
        "M1_bbox_false_negative_alpha1_total":sum(c["M1_bbox_false_negative_alpha1_physical"] for c in cells),
        "M1_bbox_false_negative_alpha24_total":sum(c["M1_bbox_false_negative_alpha24_physical"] for c in cells),
        "bbox_can_prove_native_safety":False,
        "H1_M1_halfpixel_effectiveness": ("PASS" if odd0>0 and odd1 <= H1_RATIO*odd0
                                             and odd1 <= H1_M1_MAX_MEAN_LOGICAL else "FAIL"),
        "H2_other_widths_source_invariant": "PASS" if other_eq else "FAIL"
    }
    if len(odd) != 72 or len(others) != 288 or len(cells) != CENTER_OBSERVATIONS:
        blocked("INCOMPLETE_OBSERVATIONS")
    return out


def run(workspace:Path,source_artifact:Path,engine_js:Path,renderer:Path,output:Path):
    if output.exists():
        blocked("OUTPUT_ALREADY_EXISTS")
    if (p4b1.git_blob(engine_js.read_bytes()) != s0.GAME_BLOB or
        p4b1.git_blob(renderer.read_bytes()) != s0.RENDERER_BLOB or
        p4b1.git_blob(Path(p4d3.__file__).read_bytes()) != s0.P4D3_BLOB or
        s0.git_blob(Path(s0.__file__).read_bytes()) != S0_BLOB or
        s0.git_blob(Path(p4d14.__file__).read_bytes()) != P4D14_BLOB):
        blocked("SOURCE_PIN_DRIFT")
    prereg = workspace/"AutoDraw_Stage20"/"docs"/PREREG
    if not prereg.is_file() or EXPERIMENT not in prereg.read_text("utf8"):
        blocked("MISSING_PRE_NATIVE_E0")
    if s0.sha256((workspace/"AutoDraw_Stage20/testImages/wV6VeZI9S1Y.png").read_bytes()) != s0.SOURCE_SHA256:
        blocked("SOURCE_ORIGINAL_SHA")
    manifest, digest_manifest = validate_frozen_source(source_artifact/"future_native_scene_plans.json")
    validate_s0_artifact(source_artifact, digest_manifest)
    output.mkdir(parents=True)
    save_json(output/"S0_INPUT_PROVENANCE.json",{
        "S0_archived_run":S0_RUN, "S0_archived_artifact":S0_ARTIFACT,
        "frozen_future_plan_sha256":digest_manifest, "calibration_cases":120,
        "blind_holdout_not_rendered":True, "controls_not_rendered":True})
    rows=[]
    with p4b7.native_egret_session(workspace) as driver:
        driver.set_script_timeout(180)
        browser = {"browserName":driver.capabilities.get("browserName"),
                   "browserVersion":driver.capabilities.get("browserVersion"),
                   "platformName":driver.capabilities.get("platformName")}
        if browser["browserName"]!="firefox" or not str(browser["browserVersion"]).startswith("159."):
            blocked("FIREFOX_VERSION")
        response = driver.execute_script(p4d3.CMD,[])
        blank,meta = p4d3.read_webgl_result(response,output,"REAL_EGRET_BLANK")
        if (blank.shape != p4d3.NATIVE_SHAPE or
            meta.get("schema") != "ENGINE001_B1R_P4A2_BLANK_WEBGL" or
            np.any(blank[:,:,3])):
            blocked("NATIVE_BLANK")
        with (output/"CASE_ROWS_APPEND_ONLY.jsonl").open("x",encoding="utf8") as ledger:
            for case in manifest["calibration"]:
                stem=case["sample_id"]
                folder=output/"native"/stem
                folder.mkdir(parents=True)
                save_json(folder/(stem+"_PLAN.json"),case["strokes"])
                adapted=adapt_runtime_plan(case)
                save_json(folder/(stem+"_RUNTIME_PLAN.json"),adapted)
                native,metadata=p4d3.read_scene(driver,folder,stem+"_REAL_EGRET",adapted)
                row=measured_row(case,native,adapted,metadata["source_png_sha256"])
                rows.append(row)
                ledger.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+"\n")
                ledger.flush()
                if len(rows)%20==0:
                    print("BPRED_S1_TRUE_NATIVE",len(rows),"/120",flush=True)
    score=aggregate(rows)
    report={
        "experiment":EXPERIMENT, "technical_status":"TRUE_NATIVE_CALIBRATION_CAPTURED",
        "github_sha":os.getenv("GITHUB_SHA"),"github_run_id":os.getenv("GITHUB_RUN_ID"),
        "browser":browser, "engine_blob":s0.GAME_BLOB,
        "renderer_blob":s0.RENDERER_BLOB, "P4D3_blob":s0.P4D3_BLOB,
        "P4D14_blob":P4D14_BLOB,"S0_blob":S0_BLOB,
        "S0_source_run":S0_RUN,"S0_source_artifact":S0_ARTIFACT,
        "source_future_manifest_sha256":digest_manifest,
        "native_blank_alpha0":True,"native_scene_count":1+len(rows),
        "native_case_count":len(rows),"native_calibration_observations":3*len(rows),
        "blind_holdout_E3":"NOT_RUN","blind_controls_E3":"NOT_RUN",
        "model_scope":"two-point stroke centroid and ideal bbox only; NO physical alpha predictor",
        "original_image_EF_quality":"NOT_EVALUATED_P4D18_PROTECTED_FAIL_UNCHANGED",
        "metrics":score,
        "S1_M1_efficacy":score["H1_M1_halfpixel_effectiveness"],
        "S1_native_E3_technical":"PASS_SOURCE_NATIVE_CALIBRATION_ONLY",
        "production_promotion":False,"E4_game":"NOT_RUN","E5_validation":"NOT_RUN",
        "exact_run_bound_CHALK":None
    }
    report["members_sha256"]={str(p.relative_to(output)).replace("\\","/"):digest(p.read_bytes())
       for p in sorted(output.rglob("*")) if p.is_file()}
    save_json(output/"report.json",report)
    print("BPRED_S1_RESULT",json.dumps({
        "H1":score["H1_M1_halfpixel_effectiveness"],
        "H2":score["H2_other_widths_source_invariant"],
        "M0odd":score["odd_M0_mean_error"],"M1odd":score["odd_M1_mean_error"],
        "bbox_alpha24_false_negative":score["M1_bbox_false_negative_alpha24_total"]},
        allow_nan=False),flush=True)
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for required in ("workspace","source-artifact","engine-js","renderer","output"):
        p.add_argument("--"+required,required=True,type=Path)
    a=p.parse_args()
    run(a.workspace,a.source_artifact,a.engine_js,a.renderer,a.output)

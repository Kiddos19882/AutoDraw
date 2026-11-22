#!/usr/bin/env python3
"""ENGINE-001 S5-R1 brush/fill diagnostic matrix — MODEL ONLY; no Egret claims.

Frozen E0: docs/ENGINE001_BPRED_S5R1_BRUSH_FILL_VALIDATION_MATRIX_PREREG_2026-11-23.md
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

SOURCE = Path(__file__).resolve().parents[1] / "source" / "preparation"
sys.path.insert(0, str(SOURCE))
from brush_footprint_geometry import swept_capsule_pixel_masks
from interior_fill_planner import build_interior_fill_plan
from engine001_bpred_s5r1_offline_candidates import build_candidates

WIDTHS = tuple(range(1, 11))
ANGLES = tuple(range(0, 360, 15))
LENGTHS = (0.0, 13.0)
PHASES = (0.0, 0.25)
BOARD = 64


def _dist(px, py, a, b):
    x1, y1 = a
    x2, y2 = b
    dx, dy = x2 - x1, y2 - y1
    den = dx * dx + dy * dy
    t = min(1., max(0., ((px-x1)*dx + (py-y1)*dy)/den)) if den else 0.
    return math.hypot(px-x1-t*dx, py-y1-t*dy)


def _canonical(d):
    return (json.dumps(d, sort_keys=True, ensure_ascii=False,
                       indent=2, allow_nan=False) + "\n").encode("utf-8")


def _model_cases():
    failures = []
    records = []
    total_potential = total_guaranteed = 0
    for width in WIDTHS:
        for angle in ANGLES:
            rad = math.radians(angle)
            for length in LENGTHS:
                for phase in PHASES:
                    a = (24.0+phase, 24.0+phase)
                    b = (a[0]+length*math.cos(rad), a[1]+length*math.sin(rad))
                    points = (a, b)
                    result = swept_capsule_pixel_masks(points, width, 1.,1.,BOARD,BOARD)
                    rev = swept_capsule_pixel_masks((b,a),width,1.,1.,BOARD,BOARD)
                    po = result["potential_cells"]
                    gu = result["guaranteed_cells"]
                    label = (width, angle, length, phase)
                    if not gu.issubset(po):
                        failures.append(("lower_not_subset_upper",label))
                    if po != rev["potential_cells"] or gu != rev["guaranteed_cells"]:
                        failures.append(("reverse_asymmetry",label))
                    # Independent analytic center-point capsule membership.
                    # A radius-separated center is necessarily intersected;
                    # a cell whose farthest corner is inside is guaranteed.
                    r = width/2
                    for y in range(13, 45):
                        for x in range(13, 45):
                            d = _dist(x,y,a,b)
                            point = (x,y)
                            if d < r-1e-7 and point not in po:
                                failures.append(("missed_center_intersection",label,x,y))
                            if d+math.sqrt(0.5)<r-1e-7 and point not in gu:
                                failures.append(("missed_fully_inside_cell",label,x,y))
                            if d>r+math.sqrt(0.5)+1e-7 and point in po:
                                failures.append(("outside_bounding_distance",label,x,y))
                    total_potential += len(po)
                    total_guaranteed += len(gu)
                    records.append({"width":width,"angle":angle,"length":length,
                        "phase":phase,"potential":len(po),"guaranteed":len(gu)})
    return failures, records, total_potential, total_guaranteed


def _example_maps():
    a = np.zeros((12,12),np.int16)
    a[4:8,4:8] = 1
    b = np.full((12,12),-1,np.int16)
    b[1:11,1:11] = 4
    b[4:8,4:8] = -1
    c = np.fromfunction(lambda y,x:(x+y)%2,(12,12),dtype=int).astype(np.int16)
    d = np.full((12,12), -1,np.int16)
    np.fill_diagonal(d,7)
    return {"square":a,"donut_alpha":b,"checkerboard":c,"diagonal_1px":d}


def _fill_comparator():
    results = []
    fails = []
    for name, idx in _example_maps().items():
        start = time.perf_counter()
        # Existing baseline uses rectangle geometry; its reported 100% is
        # NOT an Egret/round capsule/true coverage result.
        plan = build_interior_fill_plan(idx,max_brush_value=10,min_brush_value=2,
                                        brush_scale_x=1.,brush_scale_y=1.)
        dt = time.perf_counter()-start
        if plan["summary"]["covered_visible_pixel_count"] != int(np.count_nonzero(idx>=0)):
            fails.append(("horizontal_modeled_coverage",name))
        if any(s["safe_to_execute"] is not False for s in plan["strokes"]):
            fails.append(("horizontal_exec_admission",name))
        rgba = np.zeros((*idx.shape,4),np.uint8)
        rgba[idx>=0,3] = 255
        arr = {"game_index":idx,"paintable_id":np.where(idx>=0,idx+1,0).astype(np.int32),
               "original_rgba":rgba,
               "protected_original_dot":np.zeros(idx.shape,bool)}
        try:
            candidate=build_candidates(arr,max_strokes=120,max_seed_trials=700)
            cand = {"status":candidate["status"],
                    "potential_covered":candidate["potential_covered_pixel_count"],
                    "guaranteed_covered":candidate["guaranteed_covered_pixel_count"],
                    "remaining":candidate["uncovered_potential_pixel_count"],
                    "strokes":candidate["stroke_count"],"trials":candidate["trials"],
                    "safe_to_execute":candidate["safe_to_execute"]}
            if candidate["safe_to_execute"] is not False:
                fails.append(("candidate_exec_admission",name))
        except ValueError as exc:
            cand = {"status":"BLOCKED","reason":str(exc)}
        results.append({"map":name,"visible":int(np.count_nonzero(idx>=0)),
            "horizontal":plan["summary"],"horizontal_seconds":round(dt,6),
            "candidate":cand})
    return results, fails


def _performance():
    rows=[]
    # Native outside scope; timing is hardware-specific diagnostic.
    for size in (64,256,512):
        runs=[]
        for _ in range(3):
            start=time.perf_counter()
            f=swept_capsule_pixel_masks(((4.,4.),(size-5.,size-5.)),
                10,1.,1.,size,size)
            runs.append(time.perf_counter()-start)
        rows.append({"canvas_wh":[size,size],"brush":10,"angle_deg":45,
            "time_seconds":[round(t,6) for t in runs],
            "potential_cells":len(f["potential_cells"])})
    return rows


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    start=time.perf_counter()
    failures,records,potential,guaranteed=_model_cases()
    examples,fill_fails=_fill_comparator()
    failures.extend(fill_fails)
    speed=_performance()
    report={"experiment":"ENGINE001_BPRED_S5R1_BRUSH_FILL_MATRIX_V1",
        "scope":"OFFLINE_IDEAL_CAPSULE_AND_RECTANGLE_NOT_NATIVE",
        "model_cases":len(records),
        "expected_model_cases":10*24*2*2,
        "widths":list(WIDTHS),"angles_degrees":list(ANGLES),
        "lengths":list(LENGTHS),"phases":list(PHASES),
        "model_sum_potential":potential,"model_sum_guaranteed":guaranteed,
        "model_failures":failures[:100],
        "model_failure_total":len(failures),
        "model_status":"PASS" if not failures else "FAIL",
        "synthetic_fill":examples,
        "perf":speed,
        "wall_seconds":round(time.perf_counter()-start,4),
        "execution_allowed":False,"native_Egret":"NOT_RUN","game_CHALK":"NOT_RUN"}
    out=args.output
    out.mkdir(parents=True,exist_ok=True)
    (out/"matrix_cases.json").write_bytes(_canonical(records))
    cases_sha=hashlib.sha256((out/"matrix_cases.json").read_bytes()).hexdigest()
    report["matrix_cases_sha256"]=cases_sha
    (out/"brush_fill_model_report.json").write_bytes(_canonical(report))
    print(json.dumps({"model_cases":len(records),"model_status":report["model_status"],
          "failures":len(failures),"wall_seconds":report["wall_seconds"],
          "matrix_sha256":cases_sha},sort_keys=True))
    if failures or len(records)!=10*24*2*2:
        raise SystemExit("FAIL_S5R1_BRUSH_FILL_MODEL")


if __name__=="__main__":
    main()

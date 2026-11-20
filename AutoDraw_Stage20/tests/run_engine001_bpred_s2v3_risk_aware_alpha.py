#!/usr/bin/env python3
"""ENGINE-001 BPRED-S2v3: native-sourced alpha residual and guarded positives.

Strictly CALIBRATION: leave-one-angle-out, M2 P4D16 alpha unchanged.
M4 is an empirical guard, NOT native-exact, NOT confident negative, NOT CHALK.
Source S1 and old S2v1/v2 frozen archives are read-only. Never open BLIND.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np

import run_engine001_bpred_s0_corpus_audit as s0
import run_engine001_bpred_s2_alpha_aa_eval as v1
import run_engine001_bpred_s2v2_isotonic_eval as v2

EXPERIMENT = "ENGINE001_BPRED_S2V3_RISK_AWARE_ALPHA_V1"
E0_DOC = "ENGINE001_BPRED001_S2V3_RISK_AWARE_ALPHA_PREREG_2026-11-20.md"
E0_BLOB = "fc6b1081c97519fd8dc25d34f77a0ea02dc8f879"
V1_BLOB = "ed29df1d559409d5a5783556a12c30d24df7118d"
V2_BLOB = "952c86aebf281ee71867f9e0d12fcd9442b7ce99"
V2_PARENT_SHA = "4656b62eeb8196faaa66f9c10023a24d4c866a21"
V2_PARENT_RUN = "44652423011"
V2_PARENT_ARTIFACT = 14591791460
ALPHA_GATE = 24
RESIDUAL_QUANTILE = .995
BANDS = ((0,0),(1,23),(24,63),(64,127),(128,191),(192,254),(255,255))
ANGLES = (7,73,166)
WIDTHS = tuple(range(1,11))
SCENES = 120
ROI_COUNT = 360


def blocked(reason: str):
    raise ValueError("BLOCKED_BPRED_S2V3_" + reason)


def save(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2,
                           allow_nan=False).encode("utf8") + b"\n")


def checked_pair(pred: np.ndarray, real: np.ndarray):
    if (pred.shape != (162,162) or real.shape != (162,162) or
            pred.dtype != np.uint8 or real.dtype != np.uint8):
        blocked("PIXEL_PAIR_SHAPE_OR_DTYPE")


def quantile_higher_from_hist(hist: np.ndarray) -> tuple[int,int]:
    """Exact NumPy quantile(method='higher') for integer alpha error 0..255."""
    if hist.shape != (256,) or not np.issubdtype(hist.dtype, np.integer):
        blocked("QUANTILE_HISTOGRAM")
    if np.any(hist < 0):
        blocked("NEGATIVE_QUANTILE_COUNTS")
    count = int(hist.astype(np.int64).sum())
    if count <= 0:
        blocked("EMPTY_TRAINING_UNION")
    # index ceil((N-1)*0.995); compare against integer cumulative counts.
    index = math.ceil((count-1)*RESIDUAL_QUANTILE)
    q = int(np.searchsorted(np.cumsum(hist, dtype=np.int64), index+1))
    if q < 0 or q > 255:
        blocked("QUANTILE_RESULT")
    return q,count


def fit_guard(train_cases: list[dict]) -> tuple[int,dict]:
    """Fit per-width training folds only, on union real>0 or M2>0."""
    histogram = np.zeros(256, dtype=np.int64)
    n_cases = len(train_cases)
    if n_cases != 8:
        blocked("TRAIN_PER_WIDTH_CASE_COUNT")
    for case in train_cases:
        if len(case["pixel_pairs"]) != 3:
            blocked("TRAIN_COPY_COUNT")
        for predicted,actual in case["pixel_pairs"]:
            checked_pair(predicted,actual)
            keep = (predicted>0)|(actual>0)
            dif = np.abs(predicted.astype(np.int16)-actual.astype(np.int16))
            histogram += np.bincount(dif[keep],minlength=256)
    q,count = quantile_higher_from_hist(histogram)
    return q,{
        "train_scenes":n_cases, "train_ROIs":3*n_cases,
        "train_union_physical_pixels":count,
        "quantile":RESIDUAL_QUANTILE,
        "higher_quantile_uint8":q,
        "trust_alpha24_threshold_uint16":ALPHA_GATE+q,
        "train_histogram_sha256":hashlib.sha256(histogram.tobytes()).hexdigest(),
        "train_error_histogram":histogram.tolist(),
        "calibration_only":True
    }


def classify_pair(pred: np.ndarray,real: np.ndarray,q:int) -> dict:
    checked_pair(pred,real)
    if type(q) is not int or not 0<=q<=255:
        blocked("INVALID_GUARD_Q")
    p=pred.astype(np.uint16)
    positive=p>=ALPHA_GATE
    accepted=p>=ALPHA_GATE+q  # integer guard, never uint8 overflows
    actual=real>=ALPHA_GATE
    if np.any(accepted & ~positive):
        blocked("M4_NOT_SUBSET_M2")
    def stats(mask):
        tp=int(np.count_nonzero(mask&actual))
        fp=int(np.count_nonzero(mask&~actual))
        return {"TP":tp,"FP":fp,"FN":int(np.count_nonzero(actual))-tp,
                "positive_predicted":int(np.count_nonzero(mask))}
    m2=stats(positive)
    m4=stats(accepted)
    delta=np.abs(p.astype(np.int16)-real.astype(np.int16))
    bins=[]
    for low,high in BANDS:
        mask=(p>=low)&(p<=high)
        n=int(np.count_nonzero(mask))
        bins.append({"pred_min":low,"pred_max":high,"count":n,
            "native_alpha24":int(np.count_nonzero(mask&actual)),
            "M2_false_positives":int(np.count_nonzero(mask&positive&~actual)),
            "abs_error_sum":int(delta[mask].astype(np.int64).sum()),
            "abs_error_mean":float(delta[mask].mean()) if n else None})
    if sum(b["count"] for b in bins)!=pred.size:
        blocked("BAND_PARTITION")
    return {
        "M2_AREA8":m2, "M4_EMPIRICAL_ALPHA_GUARD":m4,
        "guard_q_uint8":q, "guard_threshold_uint16":ALPHA_GATE+q,
        "native_alpha24_count":int(np.count_nonzero(actual)),
        "UNKNOWN_physical_pixels":int(pred.size)-m4["positive_predicted"],
        "UNKNOWN_native_positive_pixels":int(np.count_nonzero(actual))-m4["TP"],
        "total_physical_pixels":int(pred.size), "predicted_alpha_error_bins":bins,
        "pixel_exact_safe_claim":False, "confident_negative_claim":False
    }


def sum_counters(rows: list[dict]):
    cells=[c for row in rows for c in row["cells"]]
    return {
        "n_scenes":len(rows),"n_ROIs":len(cells),
        "M2":{k:sum(c["M2_AREA8"][k] for c in cells)
              for k in ("TP","FP","FN","positive_predicted")},
        "M4":{k:sum(c["M4_EMPIRICAL_ALPHA_GUARD"][k] for c in cells)
              for k in ("TP","FP","FN","positive_predicted")},
        "UNKNOWN_physical_pixels":sum(c["UNKNOWN_physical_pixels"] for c in cells),
        "UNKNOWN_native_positive_pixels":sum(c["UNKNOWN_native_positive_pixels"] for c in cells)
    }


def hypothesis_scores(rows: list[dict], baseline: dict):
    if len(rows)!=SCENES or any(len(r["cells"])!=3 for r in rows):
        blocked("INCOMPLETE_HOLDOUT")
    total=sum_counters(rows)
    base_tp=total["M2"]["TP"]
    base_fp=total["M2"]["FP"]
    m4_tp=total["M4"]["TP"]
    m4_fp=total["M4"]["FP"]
    if base_tp<=0:
        blocked("NO_M2_CORRECT_PREDICTIONS")
    if (base_tp!=baseline["alpha24"]["TP"] or
        base_fp!=baseline["alpha24"]["FP"] or
        total["M2"]["FN"]!=baseline["alpha24"]["FN"]):
        blocked("S2V1_BASELINE_DRIFT")
    fold_summaries={}
    passed=True
    for angle in ANGLES:
        subset=[r for r in rows if r["angle_deg"]==angle]
        if len(subset)!=40:
            blocked("PER_ANGLE_40")
        stats=sum_counters(subset)
        b=stats["M2"];c=stats["M4"]
        fold_ok=(c["FP"]<=.10*b["FP"] and c["TP"]>=.80*b["TP"])
        passed &=fold_ok
        fold_summaries[str(angle)]={
            "M2":b,"M4":c,
            "TP_retained_ratio":float(c["TP"]/b["TP"]) if b["TP"] else None,
            "FP_remaining_ratio":float(c["FP"]/b["FP"]) if b["FP"] else (0. if c["FP"]==0 else None),
            "H3_fold":"PASS" if fold_ok else "FAIL"}
    h1=m4_fp<=.10*base_fp
    h2=m4_tp>=.90*base_tp
    h3=bool(passed)
    return {
        "all":total,"by_fold":fold_summaries,
        "H1_total_FP_90pct_reduction":"PASS" if h1 else "FAIL",
        "H2_total_TP_90pct_retention":"PASS" if h2 else "FAIL",
        "H3_each_angle_FP_and_TP":"PASS" if h3 else "FAIL",
        "independent_safety_gate_zero_FP":"PASS" if m4_fp==0 else "FAIL",
        "M4_pixel_exact_safe":False, "M4_confident_negative":False,
        "M4_model_status":"MODEL_ONLY_CALIBRATION_NOT_BLIND_VALIDATED",
        "M4_accepted_fraction_of_M2_TP":float(m4_tp/base_tp),
        "M4_FP_fraction_of_M2_FP":float(m4_fp/base_fp) if base_fp else 0.,
        "per_width":{str(w):sum_counters([r for r in rows if r["width"]==w])
                     for w in WIDTHS},
        "per_phase":{f"{x}_{y}":sum_counters(
                    [r for r in rows if r["phase_x"]==x and r["phase_y"]==y])
                     for x,y in v1.PHASES}
    }


def verify_v2_parent(dirpath: Path) -> dict:
    path=dirpath/"report.json"
    if not path.is_file():
        blocked("S2V2_PARENT_MISSING")
    r=json.loads(path.read_text("utf8"))
    if (r.get("experiment")!=v2.EXPERIMENT or
        r.get("github_sha")!=V2_PARENT_SHA or
        str(r.get("github_run_id"))!=V2_PARENT_RUN or
        r.get("source_calibration_cases")!=120 or
        r.get("blind_S0_cases_evaluated")!=0 or
        r.get("new_native_scenes_rendered")!=0 or
        r.get("metrics",{}).get("hypothesis_H1_M3_MAE_improvement")!="FAIL" or
        r.get("metrics",{}).get("hypothesis_H2_M3_FP_reduction_FN_bound")!="FAIL" or
        r.get("metrics",{}).get("hypothesis_H3_M3_IoU_noninferiority")!="PASS"):
        blocked("S2V2_PARENT_PROVENANCE")
    members=r.get("members_sha256",{})
    if not isinstance(members,dict) or set(members)!={"CASE_ROWS_APPEND_ONLY.jsonl","M3_FOLD_WIDTH_KNOTS.json"}:
        blocked("S2V2_MEMBER_NAMES")
    for name,sha in members.items():
        if s0.sha256((dirpath/name).read_bytes())!=sha:
            blocked("S2V2_MEMBER_SHA")
    return r


def build_folds(cases:list[dict]):
    rows,guards=[],[]
    for angle in ANGLES:
        training=[x for x in cases if x["angle_deg"]!=angle]
        testing=[x for x in cases if x["angle_deg"]==angle]
        if len(training)!=80 or len(testing)!=40 or (
            {x["sample_id"] for x in training}&{x["sample_id"] for x in testing}):
            blocked("FOLD_FAMILY_LEAKAGE")
        for width in WIDTHS:
            train=[x for x in training if x["width"]==width]
            test=[x for x in testing if x["width"]==width]
            if len(train)!=8 or len(test)!=4:
                blocked("FOLD_WIDTH_MATRIX")
            q,guard=fit_guard(train)
            guards.append({
                "heldout_angle":angle,"width":width,
                "train_sample_ids":[x["sample_id"] for x in train],
                "test_sample_ids":[x["sample_id"] for x in test],
                **guard
            })
            for case in test:
                cells=[]
                for index,(p,t) in enumerate(case["pixel_pairs"]):
                    cell=classify_pair(p,t,q)
                    cell["copy_index"]=index
                    cell["absolute_logical_center"]=list(s0.CENTERS[index])
                    cells.append(cell)
                row={k:v for k,v in case.items() if k!="pixel_pairs"}
                row.update({
                    "heldout_angle":angle,"M4_q_uint8":q,
                    "M4_guard_threshold_uint16":ALPHA_GATE+q,
                    "cells":cells
                })
                rows.append(row)
    rows.sort(key=lambda r:(r["width"],r["angle_deg"],r["length_logical"],
                            r["phase_x"],r["phase_y"]))
    guards.sort(key=lambda r:(r["heldout_angle"],r["width"]))
    if (len(rows)!=120 or len(guards)!=30 or
        len({r["sample_id"] for r in rows})!=120):
        blocked("FULL_VALIDATION_MATRIX")
    return rows,guards


def run(native_source:Path,v1_source:Path,v2_source:Path,output:Path,workspace:Path):
    if output.exists():
        blocked("OUTPUT_ALREADY_EXISTS")
    prereg=workspace/"AutoDraw_Stage20"/"docs"/E0_DOC
    if not prereg.is_file() or s0.git_blob(prereg.read_bytes())!=E0_BLOB:
        blocked("E0_NOT_FROZEN")
    if s0.git_blob(Path(v1.__file__).read_bytes())!=V1_BLOB:
        blocked("V1_SOURCE_DRIFT")
    if s0.git_blob(Path(v2.__file__).read_bytes())!=V2_BLOB:
        blocked("V2_SOURCE_DRIFT")
    native_report,cases=v2.prepare_cases(native_source)
    original_v1=v2.verify_parent(v1_source)
    historical_v2=verify_v2_parent(v2_source)
    rows,guards=build_folds(cases)
    scores=hypothesis_scores(rows,original_v1["metrics"]["all"]["M2_AREA8"])
    output.mkdir(parents=True)
    with (output/"CASE_ROWS_APPEND_ONLY.jsonl").open("x",encoding="utf8") as f:
        for row in rows:
            f.write(json.dumps(row,ensure_ascii=False,allow_nan=False)+"\n")
    save(output/"M4_FOLD_WIDTH_GUARDS.json",{
        "schema":"BPRED_S2V3_ANGLE_HOLDOUT_QUANTILE_GUARDS_V1",
        "source":"frozen 120 original real Egret calibration scenes",
        "quantile_method":"higher","quantile":RESIDUAL_QUANTILE,
        "widths":list(WIDTHS),"angles":list(ANGLES),
        "fold_width_guards":guards,
        "no_negative_claim":True,"blind_not_seen":True
    })
    worst=sorted(rows,key=lambda r:(sum(c["M4_EMPIRICAL_ALPHA_GUARD"]["FP"] for c in r["cells"]),
                                    sum(c["M2_AREA8"]["FP"] for c in r["cells"])),
                 reverse=True)[:12]
    save(output/"WORST_MODEL_ONLY_CASES.json",[
        {"sample_id":r["sample_id"],"angle_deg":r["angle_deg"],
         "width":r["width"],"q":r["M4_q_uint8"],
         "M2_FP":sum(c["M2_AREA8"]["FP"] for c in r["cells"]),
         "M4_FP":sum(c["M4_EMPIRICAL_ALPHA_GUARD"]["FP"] for c in r["cells"])}
        for r in worst])
    report={
        "experiment":EXPERIMENT,"github_sha":os.getenv("GITHUB_SHA"),
        "github_run_id":os.getenv("GITHUB_RUN_ID"),
        "source_native_sha":v2.NATIVE_SHA,"source_native_run":v2.NATIVE_RUN,
        "source_native_artifact":v1.SOURCE_ARTIFACT,
        "native_parent_members_SHA_verified":363,
        "parent_S2v1_sha":v2.PARENT_SHA,"parent_S2v1_run":v2.PARENT_RUN,
        "parent_S2v2_sha":V2_PARENT_SHA,"parent_S2v2_run":V2_PARENT_RUN,
        "parent_S2v2_artifact":V2_PARENT_ARTIFACT,
        "parent_S2v2_report_sha256":s0.sha256((v2_source/"report.json").read_bytes()),
        "source_browser":native_report["browser"],
        "source_game_blob":s0.GAME_BLOB,"source_renderer_blob":s0.RENDERER_BLOB,
        "source_angle_folds":list(ANGLES),
        "new_native_scenes_rendered":0,
        "S0_BLIND_scenes_evaluated":0,
        "source_calibration_cases":len(cases),
        "fold_validation_scenes":len(rows),"fold_validation_ROIs":3*len(rows),
        "model":"M4_EMPIRICAL_ALPHA_GUARD",
        "alpha24_trusted_only":True,"non_trusted_state":"UNKNOWN",
        "fixed_hypotheses":{
            "quantile":RESIDUAL_QUANTILE,
            "H1_M4_FP_ratio_max":.10,"H2_M4_TP_ratio_min":.90,
            "H3_each_fold_FP_ratio_max":.10,"H3_each_fold_TP_ratio_min":.80,
            "provisional_safety_requires_zero_FP":True
        },
        "metrics":scores,
        "pixel_safe_independent_validation":"NOT_RUN",
        "production_promotion":False,"E4_live":"NOT_RUN","E5_blind":"NOT_RUN",
        "exact_run_bound_CHALK":None,
        "lineage_S2v2_H1_H2_H3":[
            historical_v2["metrics"]["hypothesis_H1_M3_MAE_improvement"],
            historical_v2["metrics"]["hypothesis_H2_M3_FP_reduction_FN_bound"],
            historical_v2["metrics"]["hypothesis_H3_M3_IoU_noninferiority"]
        ]
    }
    report["members_sha256"]={
        str(p.relative_to(output)).replace("\\","/"):s0.sha256(p.read_bytes())
        for p in sorted(output.rglob("*")) if p.is_file()
    }
    save(output/"report.json",report)
    print("BPRED_S2V3_FOLDS",len(guards),len(rows))
    print("BPRED_S2V3_FP_TP",
        scores["all"]["M2"]["FP"],scores["all"]["M4"]["FP"],
        scores["all"]["M2"]["TP"],scores["all"]["M4"]["TP"])
    print("BPRED_S2V3_H1_H2_H3",
        scores["H1_total_FP_90pct_reduction"],
        scores["H2_total_TP_90pct_retention"],
        scores["H3_each_angle_FP_and_TP"])
    print("BPRED_S2V3_PROVISIONAL_ZERO_FP",scores["independent_safety_gate_zero_FP"])
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for opt in ("workspace","source-native","source-s2v1","source-s2v2","output"):
        p.add_argument("--"+opt,type=Path,required=True)
    a=p.parse_args()
    run(a.source_native,a.source_s2v1,a.source_s2v2,a.output,a.workspace)

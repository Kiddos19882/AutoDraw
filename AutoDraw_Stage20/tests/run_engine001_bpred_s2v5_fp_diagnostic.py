#!/usr/bin/env python3
"""ENGINE-001 BPRED-S2v5: READ-ONLY diagnosis of frozen S2v4 Egret false-safe pixels.

No new Egret draws, no adaptive threshold fitting, no S0 BLIND.
Measures exact physical locations of all M5 false positives and H3 strata.
This cannot validate RGB source-over, owner safety or gameplay CHALK.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
from PIL import Image

import run_engine001_b1r_p4d3_native_brush_repeatability as p4d3
import run_engine001_b1r_p4d14_egret_halfpixel_centroid as p4d14
import run_engine001_bpred_s0_corpus_audit as s0
import run_engine001_bpred_s2_alpha_aa_eval as v1
import run_engine001_bpred_s2v4_native_core as v4

EXPERIMENT = "ENGINE001_BPRED_S2V5_FALSE_SAFE_DIAGNOSTIC_V1"
E0_DOC = "ENGINE001_BPRED001_S2V5_FALSE_SAFE_DIAGNOSTIC_PREREG_2026-11-20.md"
E0_BLOB = "05b4caded0264b643d6748fd19bc9ffd39acb532"
PARENT_SHA = "2faf01de258da005edec5b4d59a6ca5d48d63e74"
PARENT_RUN = "44659022526"
PARENT_ARTIFACT = 14593824723
V4_BLOB = "366ee70961ea97622c18dc639475aa6548829cb2"
V1_BLOB = "ed29df1d559409d5a5783556a12c30d24df7118d"
M5_CUTOFF = 128
ALPHA24 = 24
EXPECTED_FP = 3
ROI_SHAPE = (162, 162)


def blocked(reason: str):
    raise ValueError("BLOCKED_BPRED_S2V5_" + reason)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write_once(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as out:
        out.write(json.dumps(obj, ensure_ascii=False, indent=2,
                             allow_nan=False, sort_keys=True).encode("utf8") + b"\n")


def safe_id(value: str):
    if not isinstance(value, str) or not value.startswith("BPRED-S2V4-W"):
        blocked("INVALID_SAMPLE_ID")
    if any(x in value for x in ("/", "\\", "\0", "..")):
        blocked("SAMPLE_PATH_TRAVERSAL")
    return value


def signed_capsule_margin_logical(stroke: dict, physical_x: int, physical_y: int):
    """Model-only signed distance to ideal capsule, positive means inside."""
    pts = stroke["points"]
    width = stroke["width"]
    if type(width) is not int or width not in range(1, 11) or len(pts) != 2:
        blocked("CAPSULE_INPUT")
    shift = p4d14.egret_graphics_halfpixel(width)
    p1 = (float(pts[0]["x"])+shift, float(pts[0]["y"])+shift)
    p2 = (float(pts[1]["x"])+shift, float(pts[1]["y"])+shift)
    if any(not math.isfinite(v) for v in p1+p2):
        blocked("CAPSULE_NONFINITE")
    x, y = ((physical_x+.5)/3.0, (physical_y+.5)/3.0)
    dx, dy = p2[0]-p1[0], p2[1]-p1[1]
    denom = dx*dx+dy*dy
    if denom <= 0:
        blocked("CAPSULE_ZERO_LENGTH")
    t = max(0.0, min(1.0, ((x-p1[0])*dx+(y-p1[1])*dy)/denom))
    distance = math.hypot(x-(p1[0]+t*dx),y-(p1[1]+t*dy))
    return (width/2.0)-distance


def fp_coordinates(pred: np.ndarray, actual: np.ndarray):
    """Native real alpha<24 and M2 predicted alpha>=128, y/x sorted."""
    if (pred.shape != ROI_SHAPE or actual.shape != ROI_SHAPE or
        pred.dtype != np.uint8 or actual.dtype != np.uint8):
        blocked("MALFORMED_NATIVE_ALPHA_PAIR")
    yyxx = np.argwhere((pred>=M5_CUTOFF) & (actual<ALPHA24))
    return [(int(y),int(x),int(pred[y,x]),int(actual[y,x])) for y,x in yyxx]


def native_neighbor_distance_physical(actual: np.ndarray, y: int, x: int):
    if actual.shape != ROI_SHAPE or actual.dtype != np.uint8:
        blocked("INVALID_NATIVE_ROI")
    neighbors = np.argwhere(actual >= ALPHA24)
    if len(neighbors)==0:
        blocked("EMPTY_NATIVE_FOREGROUND")
    dif = neighbors.astype(np.float64)-np.array([y,x])
    return float(np.sqrt(np.min(np.sum(dif*dif,axis=1))))


def failing_strata(metrics: dict):
    per_w = metrics["per_width"]
    per_a = metrics["per_angle"]
    if set(per_w)!={str(w) for w in range(1,11)} or set(per_a)!={"22","111","241"}:
        blocked("STRATA_COVERAGE")
    def check_group(label,items,gate):
        out=[]
        for key in sorted(items,key=lambda s:int(s)):
            row=items[key]
            denominator=row["M2"]["TP"]
            numerator=row["M5"]["TP"]
            ratio=row["retained_TP_ratio"]
            if (type(denominator) is not int or denominator<=0 or
                type(numerator) is not int or numerator<0 or
                not isinstance(ratio,(int,float)) or not math.isfinite(ratio) or
                abs(ratio-numerator/denominator)>1e-12):
                blocked("STRATA_DENOMINATOR_OR_RATIO")
            out.append({"group":label,"key":int(key),"TP_M2":denominator,
                        "TP_M5":numerator,"retained_TP_ratio":ratio,
                        "minimum_required":gate,
                        "status":"PASS" if ratio>=gate else "FAIL"})
        return out
    widths=check_group("width",per_w,.80)
    angles=check_group("angle",per_a,.85)
    return {"widths":widths,"angles":angles,
            "failures":[x for x in widths+angles if x["status"]=="FAIL"]}


def read_source(parent: Path):
    src=parent/"report.json"
    if not src.is_file():
        blocked("MISSING_ORIGINAL_REPORT")
    report=json.loads(src.read_text("utf8"))
    metrics=report.get("metrics",{})
    if (report.get("experiment")!=v4.EXPERIMENT or
        report.get("github_sha")!=PARENT_SHA or
        str(report.get("github_run_id"))!=PARENT_RUN or
        report.get("new_native_total_PNG")!=131 or
        report.get("new_native_primary_scenes")!=120 or
        not report.get("native_blank_alpha0") or
        not report.get("all_replay_RGBA_exact") or
        report.get("S0_reserved_BLIND_used") is not False or
        report.get("source_game_blob")!=s0.GAME_BLOB or
        report.get("source_renderer_blob")!=s0.RENDERER_BLOB or
        report.get("frozen_E0_blob")!=v4.E0_BLOB or
        not str(report.get("native_browser",{}).get("browserVersion","")).startswith("159.") or
        report.get("threshold_M2_positive")!=24 or
        report.get("threshold_M5_trusted_positive")!=128 or
        metrics.get("H1_zero_FP")!="FAIL" or
        metrics.get("H2_90pct_TP_retention")!="PASS" or
        metrics.get("H3_each_width_and_angle_retention")!="FAIL" or
        metrics.get("safety_gate_zero_FP")!="FAIL" or
        metrics.get("M2_AREA8",{}).get("TP")!=402639 or
        metrics.get("M2_AREA8",{}).get("FP")!=2379 or
        metrics.get("M5_HIGH_ALPHA_CORE",{}).get("TP")!=383505 or
        metrics.get("M5_HIGH_ALPHA_CORE",{}).get("FP")!=EXPECTED_FP):
        blocked("FROZEN_PARENT_PROVENANCE_OR_METRICS")
    members=report.get("members_sha256")
    if not isinstance(members,dict) or len(members)!=376:
        blocked("ORIGINAL_MEMBER_COUNT")
    listed=set(members)
    actual={p.relative_to(parent).as_posix() for p in parent.rglob("*") if p.is_file()}
    if actual!={*listed,"report.json"}:
        blocked("ORIGINAL_MEMBER_SET")
    for name,expected in sorted(members.items()):
        if s0.clean_member(name)!=name or not isinstance(expected,str) or len(expected)!=64:
            blocked("BAD_MEMBER_NAME")
        if sha256((parent/name).read_bytes())!=expected:
            blocked("ORIGINAL_MEMBER_SHA")
    for file in (parent/"S2V4_REAL_EGRET_BLANK.png",):
        with Image.open(file) as im:
            if im.size!=(1380,720) or im.mode!="RGBA" or im.getchannel("A").getbbox():
                blocked("BLANK_IS_NOT_NATIVE_ZERO")
    replay=json.loads((parent/"REPLAY_CONTROLS.json").read_text("utf8"))
    if len(replay)!=10 or not all(x.get("rgba_exact") is True for x in replay):
        blocked("REPLAY_SOURCE")
    data=json.loads((parent/"FROZEN_NEW_SCENE_MANIFEST.json").read_text("utf8"))
    cases=data.get("scenes",[])
    if data.get("total_native_png_planned")!=131 or len(cases)!=120:
        blocked("MANIFEST_SCENE_COUNT")
    ledger=[json.loads(x) for x in (parent/"CASE_ROWS_APPEND_ONLY.jsonl").read_text("utf8").splitlines()]
    expected={(w,a,l,px/32,py/32) for w in range(1,11)
             for a in (22,111,241) for l in (9,23) for px,py in ((1,11),(13,7))}
    found={(x["width"],x["angle_deg"],x["length_logical"],x["phase_x"],x["phase_y"])
            for x in ledger}
    if len(ledger)!=120 or len(set(x["sample_id"] for x in ledger))!=120 or found!=expected:
        blocked("FROZEN_SCENE_MATRIX")
    by_id={r["sample_id"]:r for r in ledger}
    if set(by_id)!={s["sample_id"] for s in cases}:
        blocked("LEDGER_MANIFEST_DRIFT")
    if len(list((parent/"native").rglob("*_REAL_EGRET.png")))!=120:
        blocked("NATIVE_PNG_COUNT")
    return report,cases,by_id


def diagnostic(parent: Path):
    report,scenes,by_id=read_source(parent)
    exact=[]
    strata=[]
    sums={k:{"TP":0,"FP":0} for k in ("M2_AREA8","M5_HIGH_ALPHA_CORE")}
    for scene in scenes:
        sid=safe_id(scene["sample_id"])
        row=by_id[sid]
        folder=parent/"native"/sid
        native_path=folder/(sid+"_REAL_EGRET.png")
        if (row.get("source_plan_sha256")!=scene["source_plan_sha256"] or
            row.get("runtime_plan_sha256")!=scene["runtime_plan_sha256"] or
            row.get("native_png_sha256")!=sha256(native_path.read_bytes())):
            blocked("CASE_SOURCE_SHA")
        src=json.loads((folder/(sid+"_PLAN.json")).read_text("utf8"))
        runtime=json.loads((folder/(sid+"_RUNTIME_PLAN.json")).read_text("utf8"))
        if (src!=scene["strokes"] or runtime!=scene["runtime"] or
            s0.sha256(s0.canonical_json(src))!=scene["source_plan_sha256"] or
            s0.sha256(s0.canonical_json(runtime))!=scene["runtime_plan_sha256"] or
            len(runtime)!=3 or len(row["cells"])!=3):
            blocked("SOURCE_RUNTIME_PLAN_DRIFT")
        with Image.open(native_path) as im:
            if im.size!=(1380,720) or im.mode!="RGBA":
                blocked("NATIVE_RGBA_FORMAT")
            rgba=np.asarray(im).copy()
        casefp=0
        case_tp=0
        phase=(scene["phase_x"],scene["phase_y"])
        for i, ((cx,cy),stroke) in enumerate(zip(s0.CENTERS,runtime)):
            native=p4d3.roi(rgba,cx,cy)[:,:,3]
            pred=v1.predict_p16_all_widths(stroke["points"],stroke["width"],
                              (cx-27)*3,(cy-27)*3,"area8")
            if pred.shape!=ROI_SHAPE or pred.dtype!=np.uint8:
                blocked("MODEL_ALPHA_BAD_SHAPE")
            real_pos=(native>=ALPHA24)
            core=(pred>=M5_CUTOFF)
            baseline=(pred>=ALPHA24)
            stats={
                "M2_AREA8":{"TP":int(np.count_nonzero(baseline&real_pos)),
                            "FP":int(np.count_nonzero(baseline&~real_pos))},
                "M5_HIGH_ALPHA_CORE":{"TP":int(np.count_nonzero(core&real_pos)),
                                     "FP":int(np.count_nonzero(core&~real_pos))}
            }
            for model in stats:
                for k in ("TP","FP"):
                    if stats[model][k]!=row["cells"][i][model][k]:
                        blocked("RECOMPUTED_PER_COPY_DRIFT")
                    sums[model][k]+=stats[model][k]
            casefp+=stats["M5_HIGH_ALPHA_CORE"]["FP"]
            case_tp+=stats["M5_HIGH_ALPHA_CORE"]["TP"]
            for y,x,palpha,aalpha in fp_coordinates(pred,native):
                bx,by=(cx-27)*3+x,(cy-27)*3+y
                exact.append({
                    "sample_id":sid,"copy_index":i,"width":scene["width"],
                    "angle_deg":scene["angle_deg"],"length_logical":scene["length_logical"],
                    "phase_x":phase[0],"phase_y":phase[1],
                    "relative_x":x,"relative_y":y,
                    "physical_x":bx,"physical_y":by,
                    "predicted_alpha_M2":palpha,"native_alpha_Egret":aalpha,
                    "distance_to_native_alpha24_px":native_neighbor_distance_physical(native,y,x),
                    "ideal_capsule_signed_margin_logical":signed_capsule_margin_logical(stroke,bx,by),
                    "model_only_capsule_diagnostic":True,
                    "image_owner_damage_measured":False
                })
        strata.append({
            "sample_id":sid,"width":scene["width"],
            "angle_deg":scene["angle_deg"],"length_logical":scene["length_logical"],
            "phase_x":phase[0],"phase_y":phase[1],
            "M5_FP_all_copies":casefp,"M5_TP_all_copies":case_tp,
            "source_native_png_sha256":row["native_png_sha256"]
        })
    if sums!={"M2_AREA8":{"TP":402639,"FP":2379},
              "M5_HIGH_ALPHA_CORE":{"TP":383505,"FP":3}}:
        blocked("GLOBAL_RECOMPUTED_COUNTS_DRIFT")
    if len(exact)!=EXPECTED_FP:
        blocked("EXACT_FP_RECONSTRUCTION")
    groups=failing_strata(report["metrics"])
    if not groups["failures"]:
        blocked("H3_FAIL_WITHOUT_FAILING_STRATUM")
    return report,exact,groups,strata


def run(workspace: Path, source: Path, output: Path):
    if output.exists():
        blocked("OUTPUT_EXISTS")
    prereg=workspace/"AutoDraw_Stage20"/"docs"/E0_DOC
    if (not prereg.is_file() or s0.git_blob(prereg.read_bytes())!=E0_BLOB or
        s0.git_blob(Path(v4.__file__).read_bytes())!=V4_BLOB or
        s0.git_blob(Path(v1.__file__).read_bytes())!=V1_BLOB):
        blocked("SOURCE_BLOB_PIN_DRIFT")
    parent,fp,group,rows=diagnostic(source)
    output.mkdir(parents=True)
    write_once(output/"EXACT_S2V4_THREE_FP.json",fp)
    write_once(output/"WIDTH_ANGLE_RETAINED_TP.json",group)
    with (output/"SAMPLE_STRATA.jsonl").open("x",encoding="utf8") as ledger:
        for row in rows:
            ledger.write(json.dumps(row,ensure_ascii=False,allow_nan=False,sort_keys=True)+"\n")
    output_hashes={p.relative_to(output).as_posix():sha256(p.read_bytes())
                  for p in sorted(output.rglob("*")) if p.is_file()}
    science={
        "source_experiment":v4.EXPERIMENT,
        "scientific_status_S2v4":"H1_FAIL_H2_PASS_H3_FAIL",
        "E2_diagnostic":"PASS_SOURCE_HASH_AND_PIXEL_RECONSTRUCTION",
        "S2v4_pixel_safe":False,
        "adaptive_stroke_risk_model":"NOT_IMPLEMENTED",
        "source_over_owner_effect":"NOT_EVALUATED",
        "native_E3_new":"NOT_RUN",
        "S0_BLIND_source_read":False,
        "production_promotion":False,
        "E4_game":"NOT_RUN","E5_independent":"NOT_RUN","exact_CHALK":None
    }
    result={
        "experiment":EXPERIMENT,"github_sha":os.getenv("GITHUB_SHA"),
        "github_run_id":os.getenv("GITHUB_RUN_ID"),
        "source_sha":PARENT_SHA,"source_run":PARENT_RUN,
        "source_artifact_id":PARENT_ARTIFACT,
        "source_report_sha256":sha256((source/"report.json").read_bytes()),
        "original_raw_members_reverified":len(parent["members_sha256"]),
        "real_original_native_png_count":131,
        "reconstructed_original_families":len(rows),
        "physical_ROIs":360,
        "all_three_FP_recovered":len(fp)==3,
        "M5_false_positive_count":len(fp),
        "strata_failing":group["failures"],
        "original_global_M2_TP":402639,"original_global_M2_FP":2379,
        "original_global_M5_TP":383505,"original_global_M5_FP":3,
        "original_H1":"FAIL","original_H2":"PASS","original_H3":"FAIL",
        "evidence":science,"members_sha256":output_hashes
    }
    write_once(output/"report.json",result)
    print("BPRED_S2V5_SCIENCE_UNCHANGED_H1_H2_H3 FAIL PASS FAIL",flush=True)
    print("BPRED_S2V5_EXACT_FP",json.dumps(fp,ensure_ascii=False),flush=True)
    print("BPRED_S2V5_H3_FAILING_STRATA",json.dumps(group["failures"],ensure_ascii=False),flush=True)
    print("BPRED_S2V5_CI_DIAGNOSTIC_HASH_PASS",len(parent["members_sha256"]),flush=True)
    return result


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    for n in ("workspace","source","output"):
        parser.add_argument("--"+n,required=True,type=Path)
    args=parser.parse_args()
    run(args.workspace.resolve(),args.source.resolve(),args.output.resolve())

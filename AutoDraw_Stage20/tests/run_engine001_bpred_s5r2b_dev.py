#!/usr/bin/env python3
"""ENGINE001 S5-R2b: original-first double fresh E2 comparison with frozen R1.

Research-only, smooth false, no native source owner/CHALK/executor.
"""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
import time
import numpy as np

import engine001_bpred_s4r1_generic_source_maps as original_io
import engine001_bpred_s4r1_ctr1_source_contour as ctr
import engine001_bpred_s4r1_s46_source_contract as s46
import engine001_bpred_s5r1_offline_candidates as r1
import engine001_bpred_s5r2b_two_ledger_candidates as r2b
import run_engine001_bpred_s5r2_dev as previous_runner
import run_engine001_bpred_s4r1_ctr1_dev as dev
import run_engine001_b1r_p3b_engine128_adaptive32 as palette

sha = previous_runner.digest
canonical = previous_runner.json_bytes
validate_model = previous_runner.validate_model
R2_DOT_BASELINE = (119,118,118,118)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    root,out=args.root.resolve(),args.output.resolve()
    out.mkdir(parents=True,exist_ok=True)
    engine, provenance=palette.read_engine_palette(root/"gameEngine/main.min_653f95bc.js")
    if provenance["engine_git_blob_sha1"] != dev.ENGINE_BLOB:
        raise ValueError("BLOCKED_R2B_ENGINE_SHA")
    report={"schema":"ENGINE001_BPRED_S5R2B_4DEV_V1",
        "engine_git_blob_sha1":dev.ENGINE_BLOB,
        "original_source_only":True,"drawing_mode":"normal","smooth":False,
        "native":"NOT_RUN","game_chalk":"NOT_RUN",
        "admissible_for_gameplay":False,"sources":[]}
    for i,path in enumerate(dev.SOURCES):
        input_bytes=(root/path).read_bytes()
        rgba=original_io.decode_original(input_bytes)["rgba"]
        raw_repetitions=[]
        times=[]
        for repetition in range(2):
            start=time.perf_counter()
            ctr1=ctr.build_ctr1(rgba,engine)
            manifest,raw=s46.export_quarantined(
                input_bytes,rgba,engine,ctr1,path,dev.ENGINE_BLOB)
            s46.verify_quarantined(manifest,raw,input_bytes)
            baseline=r1.build_from_verified_s46(manifest,raw,input_bytes,
                                                max_strokes=200,max_seed_trials=2000)
            planned=r2b.build_from_verified_s46(manifest,raw,input_bytes,
                                                max_strokes=200,max_trials=2000)
            with np.load(io.BytesIO(raw),allow_pickle=False) as arrays:
                validate_model(planned,{k:arrays[k] for k in
                                       ("game_index","paintable_id","original_rgba")})
                protected=arrays["protected_original_dot"]
                if planned["protected_original_dot_count"] != int(protected.sum()):
                    raise ValueError("BLOCKED_R2B_PROTECTED_DOTS_COUNT")
            if (planned["phase_trials"]["broad"] > 1400
                or planned["phase_trials"]["detail"] > 600
                or planned["phase_strokes"]["broad"] > 80
                or planned["phase_strokes"]["detail"] > 120):
                raise ValueError("BLOCKED_R2B_TWO_LEDGER_BUDGET")
            raw_repetitions.append((canonical(baseline),canonical(planned),
                                     manifest))
            times.append(round(time.perf_counter()-start,4))
        if raw_repetitions[0] != raw_repetitions[1]:
            raise ValueError("BLOCKED_R2B_DOUBLE_FRESH_NONDETERMINISTIC")
        old,now,manifest=raw_repetitions[0]
        r1_name=f"{i:02d}_R1_FROZEN.json"
        r2_name=f"{i:02d}_R2B_TWO_LEDGER.json"
        (out/r1_name).write_bytes(old)
        (out/r2_name).write_bytes(now)
        a,b=json.loads(old),json.loads(now)
        no_worse=(b["potential_covered_pixel_count"]>=a["potential_covered_pixel_count"])
        improved=(b["potential_covered_pixel_count"]>a["potential_covered_pixel_count"])
        detail_pass=(b["protected_dot_potential_covered"]>=R2_DOT_BASELINE[i])
        summary={"source":path,
            "input_sha256":sha(input_bytes),
            "source_manifest_sha256":sha(manifest),
            "r1_output":r1_name,"r1_sha256":sha(old),
            "r2b_output":r2_name,"r2b_sha256":sha(now),
            "source_shape":b["source_shape"],
            "visible":b["visible_pixel_count"],
            "r1_covered":a["potential_covered_pixel_count"],
            "r2b_covered":b["potential_covered_pixel_count"],
            "r2b_guaranteed":b["guaranteed_covered_pixel_count"],
            "r2b_residual":b["uncovered_potential_pixel_count"],
            "r2b_protected_total":b["protected_original_dot_count"],
            "r2b_protected_touched":b["protected_dot_potential_covered"],
            "r2b_protected_remaining":b["protected_dot_remaining"],
            "r2b_regions_total":b["regions_total"],
            "r2b_regions_visited":b["regions_visited"],
            "r2b_strokes":b["stroke_count"],"r2b_trials":b["trials"],
            "r2b_phase_strokes":b["phase_strokes"],
            "r2b_phase_trials":b["phase_trials"],
            "r2b_status":b["status"],
            "not_worse_r1_coverage":no_worse,
            "strict_improvement_r1":improved,
            "not_worse_r2_protected_dots":detail_pass,
            "double_fresh_determinism":"PASS",
            "build_both_models_seconds":times}
        report["sources"].append(summary)
        print(json.dumps(summary,ensure_ascii=False,sort_keys=True),flush=True)
    rows=report["sources"]
    passed=(all(s["not_worse_r1_coverage"] and
                s["not_worse_r2_protected_dots"] for s in rows)
            and sum(s["strict_improvement_r1"] for s in rows)>=2)
    report["frozen_model_feasibility"]="PASS_MODEL_FEASIBILITY_ONLY" if passed else "FAIL_MODEL_FEASIBILITY"
    (out/"00_S5R2B_RESULTS.json").write_bytes(canonical(report))
    print(json.dumps({"frozen_model_feasibility":report["frozen_model_feasibility"],
                      "sources":len(rows)},sort_keys=True),flush=True)


if __name__=="__main__":
    main()

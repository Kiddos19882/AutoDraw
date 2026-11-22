#!/usr/bin/env python3
"""ENGINE-001 S5-R1: four source originals x2, non-executable bounded E2."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

import engine001_bpred_s4r1_generic_source_maps as original_io
import engine001_bpred_s4r1_ctr1_source_contour as ctr
import engine001_bpred_s4r1_s46_source_contract as s46
import engine001_bpred_s5r1_offline_candidates as s5
import run_engine001_bpred_s4r1_ctr1_dev as ctr1_runner
import run_engine001_b1r_p3b_engine128_adaptive32 as palette_io


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(obj) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True,
                       indent=2, allow_nan=False) + "\n").encode("utf8")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    root, out = args.root.resolve(), args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    game128, provenance = palette_io.read_engine_palette(
        root / "gameEngine/main.min_653f95bc.js")
    if provenance["engine_git_blob_sha1"] != ctr1_runner.ENGINE_BLOB:
        raise ValueError("BLOCKED_S5R1_GAME_ENGINE_CHANGED")
    summary = {"schema": s5.VERSION, "source_original_only": True,
               "native": "NOT_RUN", "chalk": "NOT_RUN", "s5_native": "BLOCKED",
               "admissible_for_gameplay": False, "sources": []}
    for i, path in enumerate(ctr1_runner.SOURCES):
        source_bytes = (root / path).read_bytes()
        rgba = original_io.decode_original(source_bytes)["rgba"]
        outputs = []
        source_meta_sha = None
        for repeat in range(2):
            data = ctr.build_ctr1(rgba, game128)
            meta, raw = s46.export_quarantined(source_bytes, rgba, game128,
                data, path, ctr1_runner.ENGINE_BLOB)
            result = s5.build_from_verified_s46(meta, raw, source_bytes,
                max_strokes=200, max_seed_trials=2000)
            outputs.append(canonical(result))
            source_meta_sha = sha(meta)
        if outputs[0] != outputs[1]:
            raise ValueError("BLOCKED_S5R1_NOT_DETERMINISTIC")
        filename = f"{i:02d}_s5_model_only.json"
        (out / filename).write_bytes(outputs[0])
        report = json.loads(outputs[0])
        summary["sources"].append({
            "path": path, "input_sha256": sha(source_bytes),
            "source_contract_manifest_sha256": source_meta_sha,
            "output_file": filename, "output_sha256": sha(outputs[0]),
            "model_strokes": report["stroke_count"],
            "upper_bound_covered": report["potential_covered_pixel_count"],
            "lower_bound_covered": report["guaranteed_covered_pixel_count"],
            "uncovered": report["uncovered_potential_pixel_count"],
            "status": report["status"], "rejected": report["rejected"],
            "double_fresh_determinism": "PASS",
        })
    (out / "00_S5R1_RESULTS.json").write_bytes(canonical(summary))
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

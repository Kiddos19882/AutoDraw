#!/usr/bin/env python3
"""S4.6 genuine four original source-only builds, without legacy art inputs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import engine001_bpred_s4r1_generic_source_maps as original_io
import engine001_bpred_s4r1_ctr1_source_contour as ctr
import engine001_bpred_s4r1_s46_source_contract as packet
import run_engine001_bpred_s4r1_ctr1_dev as ctr1_runner
import run_engine001_b1r_p3b_engine128_adaptive32 as palette_io


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    game128, prov = palette_io.read_engine_palette(
        root / "gameEngine/main.min_653f95bc.js")
    if prov["engine_git_blob_sha1"] != ctr1_runner.ENGINE_BLOB:
        raise ValueError("BLOCKED_S46_GENUINE_GAME_ENGINE_CHANGED")
    summary = {
        "schema": packet.CONTRACT_VERSION, "contract_e0_git_blob_sha1": packet.FROZEN_E0_BLOB,
        "engine_git_blob_sha1": ctr1_runner.ENGINE_BLOB,
        "source_original_only": True, "old_processed_art_input": False,
        "count": 4, "double_fresh": True, "native": "NOT_RUN",
        "formal_BPREDS4": "BLOCKED", "exact_chalk": "NOT_RUN",
        "s45_quality": "PARTIAL", "admissible_for_gameplay": False,
        "sources": [],
    }
    for i, relative in enumerate(ctr1_runner.SOURCES):
        original_bytes = (root / relative).read_bytes()
        rgba = original_io.decode_original(original_bytes)["rgba"]
        data_a = ctr.build_ctr1(rgba, game128)
        data_b = ctr.build_ctr1(rgba, game128)
        meta_a, raw_a = packet.export_quarantined(
            original_bytes, rgba, game128, data_a,
            relative, ctr1_runner.ENGINE_BLOB)
        meta_b, raw_b = packet.export_quarantined(
            original_bytes, rgba, game128, data_b,
            relative, ctr1_runner.ENGINE_BLOB)
        if meta_a != meta_b or raw_a != raw_b:
            raise ValueError("BLOCKED_S46_FRESH_DOUBLE_BUILD_DIFFERENT")
        obj = packet.verify_quarantined(meta_a, raw_a, original_bytes)
        folder = output / ("%02d" % i)
        folder.mkdir(exist_ok=True)
        (folder / "source_contract.json").write_bytes(meta_a)
        (folder / "source_arrays.npz").write_bytes(raw_a)
        summary["sources"].append({
            "source_path": relative,
            "input_sha256": obj["input_sha256"],
            "raw_npz_sha256": obj["raw_npz_sha256"],
            "manifest_sha256": hashlib.sha256(meta_a).hexdigest(),
            "contour_segments": int(data_a["contour_segments"].shape[0]),
            "source_atom_count": int(data_a["counts"]["source_atoms"]),
            "research_only": not obj["admissible_for_gameplay"],
        })
    (output / "00_S46_RESULTS.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2, ensure_ascii=False)+"\n",
        encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()

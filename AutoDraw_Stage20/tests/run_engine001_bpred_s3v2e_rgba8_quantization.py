#!/usr/bin/env python3
"""BPRED-S3v2e: research-only RGBA8 stage diagnostic on immutable native S3v2d raw.

Known-source exploratory comparison, NOT S4 BLIND or production acceptance.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

import run_engine001_bpred_s3_native_source_over as s3
import run_engine001_b1r_p4d3_native_brush_repeatability as p4d3

EXPERIMENT = "ENGINE001_BPRED_S3V2E_RGBA8_ROUNDTRIP_DIAGNOSTIC_V1"
E0_NAME = "ENGINE001_BPRED001_S3V2E_RGBA8_QUANTIZATION_PREREG_2026-11-20.md"
E0_BLOB = "cab7f2d0867e87201913d588357bc1adc045e8ef"
SOURCE_SHA = "2ba4241be547cb14bfc0a180633ce7bfe6a9ab9a"
SOURCE_RUN = "44697386598"
SOURCE_EXPERIMENT = "ENGINE001_BPRED_S3V2D_TRUE_MAIN_CANVAS_VS_WEBGL_V1"
SOURCE_E0_BLOB = "1eb60858facc4d208f238ca9bb1c39e2f937ca1b"
S3_SOURCE_BLOB = "1bf56df9507f2a34fd16e68eef190229c3184ce5"
NAMES = ("Q0", "QF", "QR", "QC")
BINS = ((0, 0), (1, 15), (16, 63), (64, 127), (128, 254), (255, 255))


def blocked(why):
    raise ValueError("BLOCKED_BPRED_S3V2E_" + why)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def gitblob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf8") as f:
        json.dump(payload, f, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        f.write("\n")


def quantize_stage(rgba, mode):
    """Frozen E0: one 8-bit premultiply then nearest-even unpremultiply."""
    if (not isinstance(rgba, np.ndarray) or rgba.dtype != np.uint8
            or rgba.ndim != 3 or rgba.shape[-1] != 4 or mode not in NAMES):
        blocked("RGBA_MODE_DTYPE_SHAPE")
    out = rgba.copy()
    if mode == "Q0":
        return out
    a = rgba[:, :, 3]
    fractional = (a > 0) & (a < 255)
    if not np.any(fractional):
        return out
    alpha = a[fractional].astype(np.float64)[:, None]
    c = rgba[fractional, :3].astype(np.float64)
    premul = c * alpha / 255.0
    if mode == "QF":
        p = np.floor(premul)
    elif mode == "QR":
        p = np.rint(premul)
    else:
        p = np.ceil(premul)
    converted = np.clip(np.rint(255.0 * p / alpha), 0.0, 255.0)
    out[fractional, :3] = converted.astype(np.uint8)
    if not np.array_equal(out[:, :, 3], a):
        blocked("ALPHA_MUTATED")
    return out


def load_rgba(raw):
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        blocked("NOT_PNG")
    with Image.open(io.BytesIO(raw)) as im:
        rgba = np.array(im.convert("RGBA"), dtype=np.uint8)
    if rgba.shape != p4d3.NATIVE_SHAPE:
        blocked("NOT_ORIGINAL_NATIVE_SHAPE")
    return rgba


def verify_source(z, root):
    if not root.joinpath("AutoDraw_Stage20", "docs", E0_NAME).is_file():
        blocked("E0_MISSING")
    if gitblob(root.joinpath("AutoDraw_Stage20", "docs", E0_NAME).read_bytes()) != E0_BLOB:
        blocked("E0_CHANGED")
    if gitblob(Path(s3.__file__).read_bytes()) != S3_SOURCE_BLOB:
        blocked("SOURCE_OVER_IMPLEMENTATION_DRIFT")
    names = z.namelist()
    if len(names) != 656 or len(set(names)) != len(names) or z.testzip() is not None:
        blocked("ORIGINAL_ARCHIVE_CRC_OR_MEMBERS")
    if any(x.startswith("/") or ".." in Path(x).parts or "\\" in x for x in names):
        blocked("ARCHIVE_UNSAFE_MEMBER_PATH")
    report = json.loads(z.read("report.json"))
    if (report.get("experiment") != SOURCE_EXPERIMENT or
            report.get("github_sha") != SOURCE_SHA or
            str(report.get("github_run_id")) != SOURCE_RUN or
            report.get("S3v2d_frozen_E0_blob") != SOURCE_E0_BLOB or
            report.get("source_original_s3_science") != "FAIL" or
            report.get("S0_BLIND_used") is not False or
            report.get("H1_new_true_intermediate_Canvas_pass_count_40") != 38 or
            report.get("H1_original_final_S3_pass_count_40") != 10 or
            report.get("true_native_primary") != 80 or
            report.get("true_native_intermediate_canvas_PNG") != 80 or
            report.get("true_native_mask_canvas_PNG") != 80 or
            report.get("true_native_final_webgl_PNG") != 91 or
            report.get("all_primary_parent_deBG_equivalent") is not True):
        blocked("SOURCE_NATIVE_PROVENANCE_DRIFT")
    hashes = report.get("members_sha256")
    if not isinstance(hashes, dict) or len(hashes) != 655 or set(hashes) != set(names) - {"report.json"}:
        blocked("SOURCE_MEMBER_SET_DRIFT")
    for name, expected in hashes.items():
        if sha(z.read(name)) != expected:
            blocked("SOURCE_MEMBER_SHA_" + name)
    originals = [json.loads(line) for line in z.read("PAIRS_APPEND_ONLY.jsonl").decode().splitlines()]
    if len(originals) != 20 or len({x["pair_id"] for x in originals}) != 20:
        blocked("SOURCE_C0_MATRIX_DRIFT")
    originals_c = sum(int(v["source_over_original_C0_on_true_Canvas"]["frozen_H1_pass"])
                      for row in originals for v in row["ordered_variants"].values())
    originals_w = sum(int(v["source_over_original_C0_on_true_WebGL"]["frozen_H1_pass"])
                      for row in originals for v in row["ordered_variants"].values())
    if (originals_c, originals_w) != (38, 10):
        blocked("ORIGINAL_FROZEN_H1_DRIFT")
    return report


def source_file(sample_id, suffix):
    return "native/{0}/{0}_{1}.png".format(sample_id, suffix)


def difference(pred, actual):
    if pred.shape != actual.shape or pred.dtype != np.uint8 or actual.dtype != np.uint8:
        blocked("DIFFERENCE_SHAPE")
    rgb = np.abs(pred[:, :, :3].astype(np.int16) - actual[:, :, :3].astype(np.int16))
    return {"rgb_mismatch_pixels": int(np.any(rgb != 0, axis=2).sum()),
            "rgb_abs_error_sum": int(rgb.sum()),
            "rgb_max_channel_byte": int(rgb.max(initial=0)),
            "alpha_mismatch_pixels": int(np.count_nonzero(pred[:, :, 3] != actual[:, :, 3]))}


def stage_row(scene, original, webgl):
    if not np.array_equal(original[:, :, 3], webgl[:, :, 3]):
        blocked("SOURCE_STAGE_ALPHA_DRIFT")
    bands = {}
    for lo, hi in BINS:
        mask = (original[:, :, 3] >= lo) & (original[:, :, 3] <= hi)
        bands[str(lo) + "_" + str(hi)] = {}
        for mode in NAMES:
            pred = quantize_stage(original, mode)
            dc = np.any(pred[:, :, :3] != webgl[:, :, :3], axis=2)
            bands[str(lo) + "_" + str(hi)][mode] = int(np.count_nonzero(dc & mask))
    metrics = {mode: difference(quantize_stage(original, mode), webgl) for mode in NAMES}
    return {"sample_id": scene["sample_id"], "width": scene["width"],
            "relation": scene["relation"], "variant": scene["variant"],
            "mode_metrics": metrics, "alpha_bins_rgb_mismatch": bands}


def c0_row(width, relation, frames):
    ordered = {}
    for variant in ("A_THEN_B", "B_THEN_A"):
        a, b = (frames["A_ONLY"]["canvas"], frames["B_ONLY"]["canvas"])
        bottom, top = (a, b) if variant == "A_THEN_B" else (b, a)
        orig_c0 = s3.source_over(bottom, top)
        target = frames[variant]["final"]
        mask = ((a[:, :, 3] > 0) | (b[:, :, 3] > 0) | (target[:, :, 3] > 0))
        ordered[variant] = {}
        for mode in NAMES:
            predicted = quantize_stage(orig_c0, mode)
            metric, _ = s3.rgba_difference(predicted, target, mask)
            metric["frozen_H1_pass"] = bool(
                metric["max_channel_byte"] <= 2 and metric["mean_channel_byte"] <= 1)
            ordered[variant][mode] = metric
    return {"pair_id": "BPRED-S3V2-W%02d-%s" % (width, relation),
            "ordered_variants": ordered}


def run(source_zip, workspace, output):
    if output.exists():
        blocked("OUTPUT_EXISTS")
    output.mkdir(parents=True)
    with zipfile.ZipFile(source_zip, "r") as z:
        parent = verify_source(z, workspace)
        stages, ordered = [], []
        frames = defaultdict(dict)
        for scene in s3.manifest()["scenes"]:
            sample_id = scene["sample_id"]
            c = load_rgba(z.read(source_file(sample_id, "ALIGNED_MODEL_ONLY")))
            w = load_rgba(z.read(source_file(sample_id, "REAL_WEBGL")))
            stages.append(stage_row(scene, c, w))
            pair = (scene["width"], scene["relation"])
            frames[pair][scene["variant"]] = {
                "canvas": p4d3.roi(c, s3.CX, s3.CY).copy(),
                "final": p4d3.roi(w, s3.CX, s3.CY).copy()}
        if len(stages) != 80 or len(frames) != 20:
            blocked("SOURCE_SCENE_MATRIX_DRIFT")
        for width in s3.WIDTHS:
            for relation in s3.RELATIONS:
                if set(frames[(width, relation)]) != set(s3.VARIANTS):
                    blocked("SOURCE_PAIR_INCOMPLETE")
                ordered.append(c0_row(width, relation, frames[(width, relation)]))
    write(output / "D1_SOURCE_STAGE_80.json", stages)
    write(output / "D2_C0_ORDERED_40.json", ordered)
    d1 = {name: sum(r["mode_metrics"][name]["rgb_mismatch_pixels"] for r in stages)
          for name in NAMES}
    a1 = sum(row["mode_metrics"]["Q0"]["alpha_mismatch_pixels"] for row in stages)
    d2 = {name: sum(int(v[name]["frozen_H1_pass"]) for row in ordered
                    for v in row["ordered_variants"].values()) for name in NAMES}
    if d1["Q0"] != 12694 or a1 != 0:
        blocked("FROZEN_DIRECT_STAGE_BASELINE_DRIFT")
    q_h1 = d1["QC"] < 12694 and a1 == 0
    q_h2 = d2["QC"] > 10
    report = {"experiment": EXPERIMENT, "E0_blob": E0_BLOB,
              "source_run_id": SOURCE_RUN, "source_sha": SOURCE_SHA,
              "source_parent_report_sha256": sha(json.dumps(parent, sort_keys=True).encode("utf8")),
              "github_sha": os.getenv("GITHUB_SHA"),
              "github_run_id": os.getenv("GITHUB_RUN_ID"),
              "source_80_scene_real_Egret_only": True,
              "new_native_E3": False, "S0_BLIND_used": False,
              "source_d1_RGB_mismatch_by_mode": d1, "source_d1_alpha_mismatch": a1,
              "source_d2_frozen_H1_pass_by_mode_40": d2,
              "original_C0_H1_main_Canvas_40": 38,
              "original_C0_H1_WebGL_40": 10,
              "diagnostic_H1_QC_less_RGB_mismatch": "PASS" if q_h1 else "FAIL",
              "diagnostic_H2_QC_more_frozen_C0_PASS": "PASS" if q_h2 else "FAIL",
              "research_model_only_not_native_independent": True,
              "original_s3_science": "FAIL_UNCHANGED",
              "protected_EF_quality": "FAIL_UNCHANGED",
              "E4_live_game": "NOT_RUN",
              "E5_independent": "NOT_RUN", "exact_game_CHALK": None,
              "production_promotion": False}
    report["members_sha256"] = {
        p.name: sha(p.read_bytes()) for p in sorted(output.iterdir()) if p.is_file()}
    write(output / "report.json", report)
    print("BPRED_S3V2E_Q_STAGE_RGBA8", d1)
    print("BPRED_S3V2E_Q_C0_H1", d2)
    print("BPRED_S3V2E_DIAGNOSTIC_H1_H2", report["diagnostic_H1_QC_less_RGB_mismatch"],
          report["diagnostic_H2_QC_more_frozen_C0_PASS"])
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-zip", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    a = parser.parse_args()
    run(a.source_zip, a.workspace, a.output)

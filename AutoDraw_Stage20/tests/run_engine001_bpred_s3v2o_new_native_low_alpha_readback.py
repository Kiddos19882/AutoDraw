#!/usr/bin/env python3
"""BPRED-S3v2o: NEW actual Egret native low-alpha source RGB/readback holdout.

Scientific gates P1/P2/P4 are separate from technical CI; never a production predictor.
"""
from __future__ import annotations

import argparse
from functools import lru_cache
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np

import run_engine001_bpred_s3v2j_new_native_alpha0_owner_influence as j
import run_engine001_bpred_s3v2n_correlated_alpha_premult as n
import run_engine001_bpred_s3v2_native_canvas_stage as v2
import run_engine001_bpred_s3v2c_multicapture_trace as trace
import run_engine001_bpred_s3_native_source_over as s3
import run_engine001_b1r_p4d3_native_brush_repeatability as p4d3
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1

EXPERIMENT = "ENGINE001_BPRED_S3V2O_NEW_NATIVE_LOW_ALPHA_READBACK_V1"
E0_FILE = "ENGINE001_BPRED001_S3V2O_NEW_NATIVE_LOW_ALPHA_READBACK_PREREG_2026-11-20.md"
E0_BLOB = "72343545d1f8645625085afb36e5fddeda2f91c8"
WIDTHS = tuple(range(1, 11))
RELATIONS = j.RELATIONS
VARIANTS = j.VARIANTS
ANGLES = (17, 59, 101, 149, 187, 229, 269, 307, 337, 379)
COLORS = (
    (0xD12A69, 0x3584C7), (0x1EAE73, 0xE65B18),
    (0xB83FD4, 0x2099A6), (0xE39422, 0x4658D9),
    (0x307DAE, 0xCE4B82), (0x9FCD34, 0x3947AB),
    (0xF05B86, 0x229A43), (0x7B2EDA, 0xDF9340),
    (0x28B7D0, 0xBE5365), (0xE8BD57, 0x4769A1))
MODES = ("floor", "nearest_even", "ceil")


def blocked(reason):
    raise ValueError("BLOCKED_BPRED_S3V2O_" + reason)


def plans_for(width, relation):
    if type(width) is not int or width not in WIDTHS or relation not in RELATIONS:
        blocked("NOT_FROZEN_GEOMETRY")
    px = ((11 * width + 7) % 47 + 0.25) / 64
    py = ((13 * width + 5) % 47 + 0.75) / 64
    cx, cy = 176 + px, 116 + py
    angle = ANGLES[width - 1]
    a = j.midpoint(cx, cy, angle, 13 + width % 4)
    if relation == "CROSS_ROTATED":
        b = j.midpoint(cx + 0.28125, cy - 0.46875,
                       (angle + 117) % 360, 12 + width % 3)
    else:
        r = math.radians(angle)
        d = 0.82 * width + 0.47
        b = j.midpoint(cx - math.sin(r) * d, cy + math.cos(r) * d,
                       (angle + 19) % 360, 12 + width % 3)
    if any(not (math.isfinite(p["x"]) and math.isfinite(p["y"])
                and 0 < p["x"] < 460 and 0 < p["y"] < 240)
           for path in (a, b) for p in path):
        blocked("CLIPPED_OR_NONFINITE_BOARD_GEOMETRY")
    ca, cb = COLORS[width - 1]
    strokes = {
        "A": {"strokeId": "bpred-A", "width": width, "colorIndex": 1,
              "colorRgb": ca, "points": a},
        "B": {"strokeId": "bpred-B", "width": width, "colorIndex": 2,
              "colorRgb": cb, "points": b},
    }
    orders = {"A_ONLY": ("A",), "B_ONLY": ("B",),
              "A_THEN_B": ("A", "B"), "B_THEN_A": ("B", "A")}
    scenes = {}
    for variant, order in orders.items():
        original = [dict(strokes[k]) for k in order]
        runtime = [{**x, "strokeId": f"icon-{i}"} for i, x in enumerate(original)]
        sid = f"BPRED-S3V2O-W{width:02d}-{relation}-{variant}"
        scenes[variant] = {
            "sample_id": sid, "width": width, "relation": relation,
            "variant": variant, "angle_deg": angle, "phase_xy": [px, py],
            "source_colors": [ca, cb], "source_strokes": original,
            "runtime_strokes": runtime,
            "source_plan_sha256": s3.digest(s3.canonical(original)),
            "runtime_plan_sha256": s3.digest(s3.canonical(runtime))}
    return scenes


def manifest():
    scenes = [plans_for(w, relation)[variant] for w in WIDTHS
              for relation in RELATIONS for variant in VARIANTS]
    controls = [
        {"sample_id": f"BPRED-S3V2O-REPLAY-W{w:02d}",
         "parent_sample_id": plans_for(w, "CROSS_ROTATED")["A_THEN_B"]["sample_id"],
         "width": w} for w in WIDTHS]
    if (len(scenes), len({s["sample_id"] for s in scenes}), len(controls)) != (80, 80, 10):
        blocked("SOURCE_MATRIX_CARDINALITY")
    return {
        "experiment": EXPERIMENT, "E0_blob": E0_BLOB,
        "original_engine_blob": p4d3.ENGINE_GIT_BLOB,
        "original_renderer_blob": p4d3.RENDERER_GIT_BLOB,
        "scene_count": 80, "replays": 10, "blank": 1,
        "new_original_native_E3": True, "S0_BLIND_used": False,
        "scenes": scenes, "controls": controls}


def verify_source(workspace, engine, renderer, scripts):
    j.check_source(workspace, engine, renderer, scripts)
    n.verify_e0(workspace)
    e0 = workspace / "AutoDraw_Stage20" / "docs" / E0_FILE
    if not e0.is_file() or p4b1.git_blob(e0.read_bytes()) != E0_BLOB:
        blocked("NEW_E0_MISSING_OR_MUTATED")


def quantize_mode(t: Fraction, mode: str) -> int:
    if mode == "floor":
        return n.floor_fraction(t)
    if mode == "nearest_even":
        return n.nearest_even_fraction(t)
    if mode == "ceil":
        return n.ceil_fraction(t)
    blocked("INVALID_READBACK_MODE")


@lru_cache(maxsize=196608)
def single_mode_channel_bounds(color: int, alpha: int, mode: str) -> tuple[int, int]:
    """Frozen correlated exact transitions for ONE mode, same +/-2 padding as G3."""
    if (type(color) is not int or not 0 <= color <= 255
            or type(alpha) is not int or not 1 <= alpha <= 254
            or mode not in MODES):
        blocked("INVALID_RGB_ALPHA_MODE")
    if color == 0:
        return (0, 2)
    low = Fraction(2 * alpha - 1, 2)
    high = Fraction(2 * alpha + 1, 2)
    tmin, tmax = Fraction(color, 255) * low, Fraction(color, 255) * high
    start = max(0, n.floor_fraction(tmin) - 2)
    stop = min(255, n.ceil_fraction(tmax) + 2)
    points = {low, high}
    for k in range(start, stop + 1):
        i = Fraction(255 * k, color)
        half = Fraction(255 * (2 * k + 1), 2 * color)
        if low < i < high:
            points.add(i)
        if low < half < high:
            points.add(half)
    ordered = sorted(points)
    values = []
    for a in ordered:
        p = quantize_mode(Fraction(color, 255) * a, mode)
        if 0 <= p <= 255:
            values.append(n.readback(p, a))
    for left, right in zip(ordered[:-1], ordered[1:]):
        p = quantize_mode(Fraction(color, 255) * ((left + right) / 2), mode)
        if 0 <= p <= 255:
            values.extend((n.readback(p, left), n.readback(p, right)))
    if not values:
        blocked("EMPTY_READBACK_MODEL")
    return max(0, min(values) - 2), min(255, max(values) + 2)


def mode_rgb_bounds(color, alpha_bytes, mode):
    if mode not in MODES:
        blocked("INVALID_READBACK_MODE")
    alpha = np.asarray(alpha_bytes)
    if (alpha.ndim != 1 or not np.issubdtype(alpha.dtype, np.integer)
            or np.any(alpha < 1) or np.any(alpha > 254)):
        blocked("INVALID_PARTIAL_ALPHA_VECTOR")
    rgb = np.asarray(color)
    if rgb.shape != (3,) or not np.issubdtype(rgb.dtype, np.integer) or np.any(rgb > 255) or np.any(rgb < 0):
        blocked("INVALID_RGB_VECTOR")
    lo = np.empty((len(alpha), 3), dtype=np.uint8)
    hi = np.empty_like(lo)
    for i, channel in enumerate(rgb):
        for a in np.unique(alpha):
            low, high = single_mode_channel_bounds(int(channel), int(a), mode)
            mask = alpha == a
            lo[mask, i] = low
            hi[mask, i] = high
    return lo, hi


def source_rgb(value):
    if type(value) is not int or not 0 <= value <= 0xFFFFFF:
        blocked("SOURCE_RGB_INVALID")
    return np.array([(value >> 16) & 255, (value >> 8) & 255, value & 255], dtype=np.uint8)


def analyze_isolated(items, output):
    records, misses, buckets = [], [], {}
    modes = ("G3",) + MODES
    totals = {k: {"misses": 0, "informative": 0} for k in modes}
    counts = {"partial": 0, "qualified": 0, "opaque": 0, "opaque_miss": 0}
    for item in items:
        scene = item["scene"]
        if scene["variant"] not in ("A_ONLY", "B_ONLY"):
            continue
        canvas = item["canvas"]
        owner = source_rgb(scene["source_strokes"][0]["colorRgb"])
        alpha = canvas[:, :, 3]
        mask = (alpha > 0) & (alpha < 255)
        ys, xs = np.where(mask)
        native = canvas[ys, xs]
        A = native[:, 3].astype(np.int16)
        actual = native[:, :3]
        qualified = A >= 16
        counts["partial"] += len(A)
        counts["qualified"] += int(qualified.sum())
        opaque = alpha == 255
        wrong_opaque = opaque & np.any(canvas[:, :, :3] != owner[None, None, :], axis=2)
        counts["opaque"] += int(opaque.sum())
        counts["opaque_miss"] += int(wrong_opaque.sum())
        for y, x in np.argwhere(wrong_opaque):
            misses.append({"sample_id": scene["sample_id"], "type": "OPAQUE",
                           "native_physical_xy": [int(x), int(y)],
                           "actual_RGBA": canvas[y, x].tolist(), "owner_RGB": owner.tolist()})
        candidates = {"G3": n.g3(owner, A)}
        for mode in MODES:
            candidates[mode] = mode_rgb_bounds(owner, A, mode)
        row = {"sample_id": scene["sample_id"], "width": scene["width"],
               "relation": scene["relation"], "variant": scene["variant"],
               "source_color": owner.tolist(), "partial_pixels": len(A),
               "alpha16_254": int(qualified.sum()), "opaque_pixels": int(opaque.sum()),
               "opaque_misses": int(wrong_opaque.sum()), "modes": {}}
        for name, (low, high) in candidates.items():
            within = np.all((actual >= low) & (actual <= high), axis=1)
            informative = qualified & np.all((high.astype(np.int16) - low.astype(np.int16)) <= 16, axis=1)
            totals[name]["misses"] += int((~within).sum())
            totals[name]["informative"] += int(informative.sum())
            row["modes"][name] = {"RGB_misses": int((~within).sum()),
                                  "informative_A16_254": int(informative.sum())}
            for idx in np.flatnonzero(~within):
                misses.append({"sample_id": scene["sample_id"], "mode": name,
                               "width": scene["width"], "relation": scene["relation"],
                               "variant": scene["variant"],
                               "native_physical_xy": [int(xs[idx]), int(ys[idx])],
                               "actual_RGBA": native[idx].tolist(),
                               "owner_RGB": owner.tolist(), "low": low[idx].tolist(),
                               "high": high[idx].tolist()})
            for bin_name, sel in (
                ("A01_15", A < 16), ("A16_63", (A >= 16) & (A <= 63)),
                ("A64_127", (A >= 64) & (A <= 127)),
                ("A128_254", A >= 128)):
                key = buckets.setdefault(bin_name, {"pixels": 0, "modes": {}})
                if name == "G3":
                    key["pixels"] += int(sel.sum())
                mv = key["modes"].setdefault(name, {"RGB_misses": 0, "informative": 0})
                mv["RGB_misses"] += int((sel & ~within).sum())
                mv["informative"] += int((sel & informative).sum())
        records.append(row)
    if len(records) != 40 or len({r["sample_id"] for r in records}) != 40 or counts["qualified"] == 0:
        blocked("NEW_NATIVE_ISOLATED_SAMPLE_INCOMPLETE")
    v2.write_json(output / "ALL_40_NEW_ISOLATED_RGB_MODES.json", records)
    v2.write_json(output / "EVERY_NEW_NATIVE_RGB_INTERVAL_MISS.json", misses)
    v2.write_json(output / "NEW_LOW_ALPHA_BUCKETS.json", buckets)
    return counts, totals, len(misses), buckets


def run(workspace, engine, renderer, scripts, output):
    if output.exists():
        blocked("OUTPUT_EXISTS")
    verify_source(workspace, engine, renderer, scripts)
    specification = manifest()
    output.mkdir(parents=True, exist_ok=False)
    v2.write_json(output / "FROZEN_S3V2O_NEW_NATIVE_MANIFEST.json", specification)
    items = []
    with trace.pinned_native_egret_session(workspace) as driver:
        caps = {key: driver.capabilities.get(key)
                for key in ("browserName", "browserVersion", "platformName")}
        if caps["browserName"] != "firefox" or not str(caps["browserVersion"]).startswith("159."):
            blocked("FIREFOX159_NOT_PINNED")
        for script in scripts:
            driver.execute_script(script.read_text("utf8"))
        if driver.execute_script("return typeof window.AutoDrawBPRED_S3v2hOriginalStrokeStepTrace;") != "function":
            blocked("TRUE_NATIVE_STROKE_OBSERVER_MISSING")
        blank, blankmeta = p4d3.read_webgl_result(
            driver.execute_script(p4d3.CMD, []), output, "S3V2O_REAL_EGRET_BLANK")
        if blankmeta.get("schema") != "ENGINE001_B1R_P4A2_BLANK_WEBGL" or np.any(blank[:, :, 3]):
            blocked("ORIGINAL_NATIVE_BLANK_NOT_BLANK")
        with (output / "NATIVE_APPEND_ONLY.jsonl").open("x", encoding="utf8") as ledger:
            for scene in specification["scenes"]:
                try:
                    item = j.extract_scene(driver, scene, output)
                except Exception as exc:
                    v2.write_json(output / "BLOCKED_OR_FAILED_SCENE.json", {
                        "sample_id": scene["sample_id"], "completed": len(items),
                        "exception_type": type(exc).__name__, "exception": str(exc)})
                    raise
                items.append(item)
                ledger.write(json.dumps({"sample_id": scene["sample_id"],
                    "source_plan_sha256": scene["source_plan_sha256"],
                    "runtime_plan_sha256": scene["runtime_plan_sha256"],
                    "actual_stroke_events": len(item["steps"])},
                    ensure_ascii=False, allow_nan=False) + "\n")
                ledger.flush()
                print("BPRED_S3V2O_REAL_ORIGINAL_EGRET", len(items), "/80", flush=True)
        (output / "replays").mkdir(exist_ok=False)
        replays = []
        for c in specification["controls"]:
            parent = plans_for(c["width"], "CROSS_ROTATED")["A_THEN_B"]
            frame, meta = p4d3.read_scene(
                driver, output / "replays", c["sample_id"] + "_REAL_EGRET",
                parent["runtime_strokes"])
            target = next(x["webgl"] for x in items if x["scene"]["sample_id"] == parent["sample_id"])
            same = bool(np.array_equal(p4d3.roi(frame, s3.CX, s3.CY),
                                       p4d3.roi(target, s3.CX, s3.CY)))
            replays.append({"sample_id": c["sample_id"], "parent": parent["sample_id"],
                            "RGBA_ROI_exact": same, "sha256": meta["source_png_sha256"]})
            if not same:
                blocked("REPLAY_DIFFERENT_" + c["sample_id"])
    v2.write_json(output / "REPLAY_CONTROLS.json", replays)
    pairs, damage = j.calculate_pairs(items, output)
    counts, totals, miss_count, buckets = analyze_isolated(items, output)
    first = sum(r["first_event_vs_same_run_isolated_owner"]["RGBA_different_physical_pixels"] for r in pairs)
    last = sum(x["last_difference"]["RGBA_different_physical_pixels"] for x in items)
    c0_canvas = sum(int(r["original_fixed_C0_canvas"]["frozen_H1_pass"]) for r in pairs)
    c0_webgl = sum(int(r["original_fixed_C0_QH_webgl"]["frozen_H1_pass"]) for r in pairs)
    stage_rgb = sum(x["stage"]["QH"]["rgb_mismatch_pixels"] for x in items)
    stage_alpha = sum(x["stage"]["QH"]["alpha_mismatch_pixels"] for x in items)
    report = {
        "experiment": EXPERIMENT, "E0_blob": E0_BLOB,
        "github_sha": os.getenv("GITHUB_SHA"), "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "browser": caps,
        "original_game_engine_blob": p4d3.ENGINE_GIT_BLOB,
        "original_renderer_blob": p4d3.RENDERER_GIT_BLOB,
        "true_new_native_primary": len(items), "true_main_canvas_PNG": 80,
        "true_mask_canvas_PNG": 80, "true_final_webgl_PNG": 91,
        "true_stroke_snapshots": sum(len(x["steps"]) for x in items),
        "native_stroke_count_distribution": [
            {"id": x["scene"]["sample_id"], "events": len(x["steps"])} for x in items],
        "blank_alpha0": True, "replays": len(replays),
        "isolated_source_frames": 40, "new_source_counts": counts,
        "G3_new_source_RGB_misses": totals["G3"]["misses"],
        "G3_informative_A16_254": totals["G3"]["informative"],
        "G3_informative_fraction": totals["G3"]["informative"] / counts["qualified"],
        "P1_G3_new_native_coverage": "PASS_NEW_NATIVE_E3_SOURCE_ONLY"
            if totals["G3"]["misses"] == 0 and counts["opaque_miss"] == 0 else "FAIL",
        "P2_G3_usefulness_frozen90pct": "PASS"
            if totals["G3"]["informative"] / counts["qualified"] >= .90 else "FAIL",
        "P3_modes_diagnostic_only": {name: {**totals[name],
            "informative_fraction": totals[name]["informative"] / counts["qualified"]}
            for name in MODES},
        "P3_model_selection": "NOT_ALLOWED_ON_HOLDOUT",
        "P4_first_owner_exact_40": "PASS" if first == 0 else "FAIL",
        "P4_last_native_main_exact_80": "PASS" if last == 0 else "FAIL",
        "P4_first_RGBA_changed_pixels": first,
        "P4_last_RGBA_changed_pixels": last,
        "P4_isolated_top_alpha0_lower_owner_changed_pixels": len(damage),
        "P4_foreign_owner_safety": "FAIL" if damage else "UNKNOWN_NOT_PRODUCTION_SAFE",
        "P4_original_C0_canvas_pass_40": c0_canvas,
        "P4_original_C0_QH_webgl_pass_40": c0_webgl,
        "P4_QH_stage_RGB_misses": stage_rgb, "P4_QH_stage_alpha_misses": stage_alpha,
        "S3v2n_original_source_G3_misses": 0,
        "S3v2n_original_D2": "FAIL_6851_OF_7753",
        "S3v2k_original_source_D2": "FAIL_3186",
        "S3v2l_original_F2": "FAIL_327",
        "S3v2j_original_hidden_alpha0_damage": 21,
        "S3v2j_original_C0_QH_webgl": "FAIL_21_OF_40",
        "original_EF_protected_quality": "FAIL_UNCHANGED",
        "source_owner_safety": "NOT_PROMOTED",
        "S0_BLIND_used": False, "E4_game": "NOT_RUN", "E5_independent": "NOT_RUN",
        "exact_game_CHALK": None, "production_promotion": False,
        "new_RGB_miss_report_records": miss_count,
        "alpha_bucket_names": sorted(buckets),
    }
    report["members_sha256"] = {
        p.relative_to(output).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(output.rglob("*")) if p.is_file()}
    v2.write_json(output / "report.json", report)
    print("BPRED_S3V2O_NEW_E3_G3", report["P1_G3_new_native_coverage"],
          "P2", report["P2_G3_usefulness_frozen90pct"],
          totals["G3"]["informative"], "/", counts["qualified"], flush=True)
    print("BPRED_S3V2O_HIDDEN_ALPHA0_OWNER_EFFECT", len(damage),
          "P4", report["P4_foreign_owner_safety"], flush=True)
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for flag in ("workspace", "engine", "renderer", "trace-js", "selector-js", "stroke-js", "output"):
        p.add_argument("--" + flag, required=True, type=Path)
    a = p.parse_args()
    run(a.workspace, a.engine, a.renderer,
        (a.trace_js, a.selector_js, a.stroke_js), a.output)

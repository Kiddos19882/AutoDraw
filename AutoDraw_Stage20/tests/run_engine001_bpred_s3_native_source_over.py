#!/usr/bin/env python3
"""ENGINE-001/BPRED-S3: frozen research-only two-owner native Egret source-over.

80 genuinely new A/B scenes + 10 exact replays + blank, no S0 BLIND.
C0 uses actual isolated native RGBA; C1 uses unchanged P4D16 M2 area8.
Scientific H failures are recorded, not changed into technical failures.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np

import run_engine001_b1r_p4d3_native_brush_repeatability as p4d3
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
import run_engine001_bpred_s2_alpha_aa_eval as v1

EXPERIMENT = "ENGINE001_BPRED_S3_NATIVE_SOURCE_OVER_V1"
E0_FILE = "ENGINE001_BPRED001_S3_NATIVE_SOURCE_OVER_PREREG_2026-11-20.md"
E0_BLOB = "61996b3253c794c5cd16ca989a70628b6609669f"
GAME_BLOB = p4d3.ENGINE_GIT_BLOB
RENDERER_BLOB = p4d3.RENDERER_GIT_BLOB
P4D3_BLOB = "3437a9326b381d9c94d6ade80059d40adf233d09"
M2_BLOB = "ed29df1d559409d5a5783556a12c30d24df7118d"
WIDTHS = tuple(range(1, 11))
RELATIONS = ("CROSSING", "NEAR_PARALLEL_OVERLAP")
VARIANTS = ("A_ONLY", "B_ONLY", "A_THEN_B", "B_THEN_A")
COLOR = {"A": 0x503D35, "B": 0xC54191}
CX, CY = 172, 120
LEFT, TOP = (CX - 27) * 3, (CY - 27) * 3
ALPHA_GATE = 24
PRED_CONFIDENT_ALPHA = 128


def blocked(reason):
    raise ValueError("BLOCKED_BPRED_S3_" + reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf8")


def save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


def points_for(width, relation):
    if type(width) is not int or width not in WIDTHS or relation not in RELATIONS:
        blocked("UNFROZEN_GEOMETRY")
    px, py = .25 + 1 / 16, .375 + 3 / 16
    a = [{"x": CX - 8 + px, "y": CY + py},
         {"x": CX + 8 + px, "y": CY + py}]
    if relation == "CROSSING":
        b = [{"x": CX + px + 1 / 8, "y": CY - 8 + py},
             {"x": CX + px + 1 / 8, "y": CY + 8 + py}]
    else:
        b = [{"x": CX - 8 + px, "y": CY + py + width / 2},
             {"x": CX + 8 + px, "y": CY + py + width / 2}]
    if not all(0 < p[k] < (460 if k == "x" else 240)
               for stroke in (a, b) for p in stroke for k in ("x", "y")):
        blocked("BOARD_CLIPPING")
    return a, b


def plans_for(width, relation):
    a, b = points_for(width, relation)
    owner = {
        "A": {"strokeId": "bpred-A", "width": width, "colorIndex": 1,
              "colorRgb": COLOR["A"], "points": a},
        "B": {"strokeId": "bpred-B", "width": width, "colorIndex": 2,
              "colorRgb": COLOR["B"], "points": b}}
    orders = {"A_ONLY": ("A",), "B_ONLY": ("B",),
              "A_THEN_B": ("A", "B"), "B_THEN_A": ("B", "A")}
    result = {}
    for variant in VARIANTS:
        src = [dict(owner[c]) for c in orders[variant]]
        run = [{**s, "strokeId": f"icon-{i}"} for i, s in enumerate(src)]
        if any({k: v for k, v in s.items() if k != "strokeId"} !=
               {k: v for k, v in t.items() if k != "strokeId"}
               for s, t in zip(src, run)):
            blocked("TRANSPORT_MUTATION")
        result[variant] = {
            "sample_id": f"BPRED-S3-W{width:02d}-{relation}-{variant}",
            "width": width, "relation": relation, "variant": variant,
            "source_strokes": src, "runtime_strokes": run,
            "source_plan_sha256": digest(canonical(src)),
            "runtime_plan_sha256": digest(canonical(run))}
    return result


def manifest():
    rows = [plans_for(w, r)[v] for w in WIDTHS
            for r in RELATIONS for v in VARIANTS]
    repeats = [{"sample_id": f"BPRED-S3-REPLAY-W{w:02d}",
                "parent_sample_id": plans_for(w, "CROSSING")["A_THEN_B"]["sample_id"],
                "width": w} for w in WIDTHS]
    if (len(rows), len(repeats), len({x["sample_id"] for x in rows})) != (80, 10, 80):
        blocked("FROZEN_MATRIX")
    return {"experiment": EXPERIMENT, "E0_blob": E0_BLOB,
            "source_owner_RGB": COLOR, "S0_BLIND_used": False,
            "new_primary": 80, "replays": 10, "blank": 1,
            "expected_native_PNG": 91, "scenes": rows, "controls": repeats}


def source_over(bottom, top):
    """Frozen C0/C1: straight sRGB RGBA, float64, round-to-even once."""
    if (bottom.shape != top.shape or bottom.ndim != 3 or
            bottom.shape[-1] != 4 or bottom.dtype != np.uint8 or
            top.dtype != np.uint8):
        blocked("SOURCE_OVER_SHAPE_DTYPE")
    b = bottom.astype(np.float64) / 255.0
    t = top.astype(np.float64) / 255.0
    ba, ta = b[..., 3], t[..., 3]
    ao = ta + (1.0 - ta) * ba
    numerator = t[..., :3] * ta[..., None] + b[..., :3] * (
        ba * (1.0 - ta))[..., None]
    rgb = np.zeros_like(numerator)
    np.divide(numerator, ao[..., None], out=rgb, where=ao[..., None] > 0)
    merged = np.concatenate((rgb, ao[..., None]), axis=2)
    return np.rint(np.clip(merged * 255.0, 0, 255)).astype(np.uint8)


def predicted_stroke(stroke):
    alpha = v1.predict_p16_all_widths(
        stroke["points"], stroke["width"], LEFT, TOP, "area8")
    if alpha.shape != (162, 162) or alpha.dtype != np.uint8:
        blocked("FROZEN_M2_ALPHA")
    rgb = np.array([(stroke["colorRgb"] >> 16) & 255,
                    (stroke["colorRgb"] >> 8) & 255,
                    stroke["colorRgb"] & 255], np.uint8)
    rgba = np.zeros((162, 162, 4), np.uint8)
    rgba[:, :, :3] = rgb
    rgba[:, :, 3] = alpha
    rgba[alpha == 0, :3] = 0
    return rgba


def rgba_difference(expected, actual, mask):
    if expected.shape != actual.shape or mask.shape != expected.shape[:2]:
        blocked("ERROR_MASK_SHAPE")
    delta = np.abs(expected.astype(np.int16) - actual.astype(np.int16))
    vals = delta[mask]
    return {"union_pixels": int(mask.sum()),
            "max_channel_byte": int(vals.max()) if vals.size else 0,
            "mean_channel_byte": float(vals.mean()) if vals.size else 0.0,
            "different_physical_pixels": int(np.any(delta != 0, axis=2)[mask].sum()),
            "transparent_rgb_diff_outside_union": int(
                np.any(delta[:, :, :3] != 0, axis=2)[~mask].sum())}, delta


def confusion(pred, native):
    a, b = pred[:, :, 3] >= ALPHA_GATE, native[:, :, 3] >= ALPHA_GATE
    confident = pred[:, :, 3] >= PRED_CONFIDENT_ALPHA
    rgb_error = np.any(np.abs(pred[:, :, :3].astype(np.int16) -
                              native[:, :, :3].astype(np.int16)) > 2, axis=2)
    return {"TP": int((a & b).sum()), "FP": int((a & ~b).sum()),
            "FN": int((~a & b).sum()),
            "confident_alpha128_false_safe": int((confident & ~b).sum()),
            "confident_wrong_rgb_gt2": int((confident & b & rgb_error).sum())}


def owner_effect(bottom_native, top_native, actual, model):
    # Synthetic owner territories come from separately rendered native A/B,
    # never from a fabricated original E/F protected map.
    base = bottom_native[:, :, 3] >= ALPHA_GATE
    top = top_native[:, :, 3] >= ALPHA_GATE
    delta_actual = np.any(np.abs(actual[:, :, :3].astype(np.int16) -
                                 bottom_native[:, :, :3].astype(np.int16)) > 2, axis=2)
    delta_model = np.any(np.abs(model[:, :, :3].astype(np.int16) -
                                bottom_native[:, :, :3].astype(np.int16)) > 2, axis=2)
    return {"bottom_owner_alpha24_pixels": int(base.sum()),
            "native_overlap_owner_pixels": int((base & top).sum()),
            "native_changed_bottom_RGB_gt2": int((base & delta_actual).sum()),
            "model_missed_native_owner_change": int((
                base & delta_actual & ~delta_model).sum()),
            "model_false_owner_change": int((
                base & ~delta_actual & delta_model).sum())}


def source_rgb_proof(image, color):
    a = image[:, :, 3] == 255
    target = np.array([(color >> 16) & 255, (color >> 8) & 255, color & 255])
    good = a & np.all(image[:, :, :3] == target, axis=2)
    return {"alpha255_pixels": int(a.sum()),
            "exact_owner_rgb_alpha255_pixels": int(good.sum()),
            "rgb24": [int(v) for v in target]}


def isolated_scene_valid(frame, color, sample_id):
    proof = source_rgb_proof(frame, color)
    if proof["exact_owner_rgb_alpha255_pixels"] <= 0:
        blocked("NATIVE_OWNER_RGB_UNPROVEN_" + sample_id)
    return proof


def analyze_pair(width, relation, original, out):
    iso_a, iso_b = original["A_ONLY"], original["B_ONLY"]
    if not np.any(iso_a[:, :, 3]) or not np.any(iso_b[:, :, 3]):
        blocked("EMPTY_NATIVE_OWNER")
    model_plans = plans_for(width, relation)
    m_a = predicted_stroke(model_plans["A_ONLY"]["runtime_strokes"][0])
    m_b = predicted_stroke(model_plans["B_ONLY"]["runtime_strokes"][0])
    data = {"width": width, "relation": relation, "variants": {},
            "order_change_physical": None}
    for name in ("A_THEN_B", "B_THEN_A"):
        actual = original[name]
        bottom, top = (iso_a, iso_b) if name == "A_THEN_B" else (iso_b, iso_a)
        pred_bottom, pred_top = (m_a, m_b) if name == "A_THEN_B" else (m_b, m_a)
        c0 = source_over(bottom, top)
        c1 = source_over(pred_bottom, pred_top)
        union = ((bottom[:, :, 3] > 0) | (top[:, :, 3] > 0) |
                 (actual[:, :, 3] > 0))
        c0_score, delta0 = rgba_difference(c0, actual, union)
        c1_union = (c1[:, :, 3] > 0) | (actual[:, :, 3] > 0)
        c1_score, delta1 = rgba_difference(c1, actual, c1_union)
        case_id = model_plans[name]["sample_id"]
        maps = out / "error_maps"
        maps.mkdir(exist_ok=True)
        np.savez_compressed(maps / (case_id + "_ERRORS.npz"),
                            C0_abs_RGBA_bytes=delta0.astype(np.uint8),
                            C1_abs_RGBA_bytes=delta1.astype(np.uint8),
                            union_native=union.astype(np.uint8))
        data["variants"][name] = {
            "native_sample": case_id,
            "C0_RGBA_native_isolated_source_over": c0_score,
            "C0_H1_pass": c0_score["max_channel_byte"] <= 2 and
                          c0_score["mean_channel_byte"] <= 1,
            "C1_M2_RGBA": c1_score,
            "C1_M2_confusion": confusion(c1, actual),
            "owner_effect_diagnostic": owner_effect(bottom, top, actual, c1)}
    ab = original["A_THEN_B"]
    ba = original["B_THEN_A"]
    both = (ab[:, :, 3] >= ALPHA_GATE) & (ba[:, :, 3] >= ALPHA_GATE)
    differ = np.any(ab[:, :, :3] != ba[:, :, :3], axis=2) & both
    data["order_change_physical"] = int(differ.sum())
    data["H2_order_effect_pass"] = bool(np.any(differ))
    return data


def run(workspace: Path, engine: Path, renderer: Path, output: Path):
    if output.exists():
        blocked("OUTPUT_ALREADY_EXISTS")
    pins = [(workspace / "AutoDraw_Stage20" / "docs" / E0_FILE, E0_BLOB),
            (engine, GAME_BLOB), (renderer, RENDERER_BLOB),
            (Path(p4d3.__file__), P4D3_BLOB), (Path(v1.__file__), M2_BLOB)]
    for path, sha in pins:
        if not path.is_file() or p4b1.git_blob(path.read_bytes()) != sha:
            blocked("PINNED_GIT_BLOB_" + path.name)
    frozen = manifest()
    output.mkdir(parents=True)
    save_json(output / "FROZEN_S3_MANIFEST.json", frozen)
    rows, controls, first = [], [], {}
    with p4b7.native_egret_session(workspace) as driver:
        caps = {k: driver.capabilities.get(k)
                for k in ("browserName", "browserVersion", "platformName")}
        if caps["browserName"] != "firefox" or not str(caps["browserVersion"]).startswith("159."):
            blocked("PINNED_FIREFOX159_REQUIRED")
        blank, meta_blank = p4d3.read_webgl_result(
            driver.execute_script(p4d3.CMD, []), output, "S3_REAL_EGRET_BLANK")
        if (meta_blank.get("schema") != "ENGINE001_B1R_P4A2_BLANK_WEBGL" or
                blank.shape != p4d3.NATIVE_SHAPE or np.any(blank[:, :, 3])):
            blocked("NATIVE_BLANK_NONZERO")
        blank_digest = meta_blank["source_sha256"]
        with (output / "CASE_ROWS_APPEND_ONLY.jsonl").open("x", encoding="utf8") as ledger:
            for width in WIDTHS:
                for relation in RELATIONS:
                    scenes = plans_for(width, relation)
                    frames, captures, proofs = {}, {}, {}
                    for variant in VARIANTS:
                        scene = scenes[variant]
                        folder = output / "native" / scene["sample_id"]
                        folder.mkdir(parents=True, exist_ok=False)
                        save_json(folder / "source_plan.json", scene["source_strokes"])
                        save_json(folder / "runtime_plan.json", scene["runtime_strokes"])
                        full, meta = p4d3.read_scene(
                            driver, folder, scene["sample_id"] + "_REAL_EGRET",
                            scene["runtime_strokes"])
                        crop = p4d3.roi(full, CX, CY).copy()
                        if int(np.count_nonzero(full[:, :, 3])) != int(
                                np.count_nonzero(crop[:, :, 3])):
                            blocked("INK_OUTSIDE_FROZEN_PHYSICAL_ROI")
                        frames[variant] = crop
                        captures[variant] = meta
                        if variant in ("A_ONLY", "B_ONLY"):
                            proofs[variant] = isolated_scene_valid(
                                crop, COLOR[variant[0]], scene["sample_id"])
                        if relation == "CROSSING" and variant == "A_THEN_B":
                            first[width] = (full.copy(), scene)
                    outcome = analyze_pair(width, relation, frames, output)
                    row = {"pair_id": f"BPRED-S3-W{width:02d}-{relation}",
                           "source_RGB_proof": proofs,
                           "native_meta": captures, **outcome}
                    rows.append(row)
                    ledger.write(json.dumps(row, allow_nan=False, ensure_ascii=False) + "\n")
                    ledger.flush()
                    print("BPRED_S3_REAL_NATIVE_PAIR", len(rows), "/20", flush=True)
        for width in WIDTHS:
            reference, scene = first[width]
            folder = output / "replays"
            folder.mkdir(exist_ok=True)
            sample_id = f"BPRED-S3-REPLAY-W{width:02d}"
            replay, meta = p4d3.read_scene(
                driver, folder, sample_id + "_REAL_EGRET", scene["runtime_strokes"])
            exact = bool(np.array_equal(replay, reference))
            controls.append({"sample_id": sample_id, "parent": scene["sample_id"],
                             "RGBA_exact": exact, "png_sha256": meta["source_png_sha256"]})
            if not exact:
                blocked("REPLAY_NOT_RGBA_EXACT_W" + str(width))
    save_json(output / "REPLAY_CONTROLS.json", controls)
    h1 = all(v["C0_H1_pass"] for row in rows for v in row["variants"].values())
    h2 = all(row["H2_order_effect_pass"] for row in rows)
    totals = {k: int(sum(row["variants"][v]["C1_M2_confusion"][k]
                         for row in rows for v in ("A_THEN_B", "B_THEN_A")))
              for k in ("TP", "FP", "FN", "confident_alpha128_false_safe",
                        "confident_wrong_rgb_gt2")}
    report = {
        "experiment": EXPERIMENT, "github_sha": os.getenv("GITHUB_SHA"),
        "github_run_id": os.getenv("GITHUB_RUN_ID"), "frozen_E0_git_blob": E0_BLOB,
        "source_game_git_blob": GAME_BLOB, "source_renderer_git_blob": RENDERER_BLOB,
        "native_browser": caps, "native_primary_scenes": 80,
        "native_replay_controls": len(controls), "native_blank_scenes": 1,
        "native_total_PNG": 91, "native_blank_sha256": blank_digest,
        "native_blank_alpha0": True, "all_replays_RGBA_exact": True,
        "S0_BLIND_used": False, "raw_single_color_owner_proved": True,
        "C0_H1_all_40_ordered_composites": "PASS" if h1 else "FAIL",
        "H2_all_20_order_pairs": "PASS" if h2 else "FAIL",
        "H3_C1_owner_diagnostic": "MODEL_ONLY_UNSAFE" if (
            totals["confident_alpha128_false_safe"] or
            totals["confident_wrong_rgb_gt2"]) else "MODEL_ONLY_NOT_VALIDATED",
        "H3_M2_RGBA_confusion_totals": totals, "H1_H2_gates_fixed": {
            "C0_max_channel_bytes": 2, "C0_mean_channel_bytes": 1,
            "native_order_effect_min_physical_pixels_each_pair": 1},
        "synthetic_two_color_only_not_original_EF": True,
        "P4D18_protected_quality": "FAIL_UNCHANGED",
        "production_promotion": False, "E4_game": "NOT_RUN",
        "E5_independent": "NOT_RUN", "exact_run_bound_CHALK": None,
        "pairs_jsonl": "CASE_ROWS_APPEND_ONLY.jsonl"}
    report["members_sha256"] = {
        str(p.relative_to(output)).replace("\\", "/"): digest(p.read_bytes())
        for p in sorted(output.rglob("*")) if p.is_file()}
    save_json(output / "report.json", report)
    print("BPRED_S3_NATIVE_E3", len(rows), "pairs; 91 PNG; H1",
          report["C0_H1_all_40_ordered_composites"], "H2",
          report["H2_all_20_order_pairs"], "C1", totals, flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for field in ("workspace", "engine", "renderer", "output"):
        parser.add_argument("--" + field, type=Path, required=True)
    args = parser.parse_args()
    run(args.workspace, args.engine, args.renderer, args.output)

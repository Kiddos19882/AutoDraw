#!/usr/bin/env python3
"""BPRED-S3v2: frozen native CanvasRenderer intermediate vs WebGL after S3 H1 FAIL.

No new paint path, no altered C0, no BLIND. 80 real intermediate PNG, 91
fresh true Egret final PNG, all compared to frozen S3 source artifact.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import io
import json
import math
import os
from pathlib import Path

import numpy as np
from PIL import Image

import run_engine001_bpred_s3_native_source_over as s3
import run_engine001_b1r_p4d3_native_brush_repeatability as p4d3
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7

EXPERIMENT = "ENGINE001_BPRED_S3V2_CANVAS_WEBGL_ORIGINAL_STAGE_V1"
E0_FILE = "ENGINE001_BPRED001_S3V2_NATIVE_CANVAS_COMPOSITING_DIAGNOSTIC_PREREG_2026-11-20.md"
E0_BLOB = "d8d703779f6364a3dda8e8edf9717fe0d065ef45"
PARENT_RUN = "44683117471"
PARENT_SHA = "6dedf6ddfde36db17f07fc0aa00dd463dc525ca8"
PARENT_ARTIFACT = 14604987986
PARENT_S3_BLOB = "1bf56df9507f2a34fd16e68eef190229c3184ce5"
RENDERER_JS = "AutoDraw_Stage20/tests/engine001_bpred_s3v2_canvas_capture.js"
SCALE = 3
BOARD_SHAPE = p4d3.NATIVE_SHAPE


def blocked(reason):
    raise ValueError("BLOCKED_BPRED_S3V2_" + reason)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


def read_png_data_url(encoded, path):
    if not isinstance(encoded, str) or not encoded.startswith("data:image/png;base64,"):
        blocked("NOT_NATIVE_PNG_URL")
    raw = base64.b64decode(encoded.partition(",")[2], validate=True)
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        blocked("BAD_PNG_SIGNATURE")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as f:
        f.write(raw)
    with Image.open(io.BytesIO(raw)) as im:
        rgba = np.array(im.convert("RGBA"), dtype=np.uint8)
    return rgba, sha256(raw)


def source_stage_align(canvas, node, transform):
    """Map true node-local raster to 3x original 460x240 backing, no fitting."""
    if (canvas.ndim != 3 or canvas.shape[2] != 4 or
            canvas.dtype != np.uint8 or
            set(node) != {"x", "y", "width", "height"} or
            len(transform) != 6 or
            not all(isinstance(v, (int, float)) and math.isfinite(v)
                    for v in (*node.values(), *transform))):
        blocked("CANVAS_ALIGNMENT_METADATA")
    x, y, width, height = (float(node[k]) for k in ("x", "y", "width", "height"))
    a, b, c, d, e, f = (float(k) for k in transform)
    if (width <= 0 or height <= 0 or
            not math.isclose(a, 3.0, abs_tol=1e-9) or
            not math.isclose(d, 3.0, abs_tol=1e-9) or
            any(abs(v) > 1e-9 for v in (b, c)) or
            not math.isclose(e, -SCALE * x, abs_tol=1e-7) or
            not math.isclose(f, -SCALE * y, abs_tol=1e-7)):
        blocked("UNSUPPORTED_NATIVE_TRANSFORM")
    left, top = round(SCALE * x), round(SCALE * y)
    if not math.isclose(left, SCALE * x, abs_tol=1e-7) or not math.isclose(
            top, SCALE * y, abs_tol=1e-7):
        blocked("NONINTEGER_PHYSICAL_NODE_ORIGIN")
    if (canvas.shape[1] != math.ceil(SCALE * width) or
            canvas.shape[0] != math.ceil(SCALE * height)):
        blocked("CANVAS_NODE_SIZE_DRIFT")
    height_final, width_final = BOARD_SHAPE[:2]
    source_x0, source_y0 = max(0, -left), max(0, -top)
    destination_x0, destination_y0 = max(0, left), max(0, top)
    overlap_width = min(canvas.shape[1] - source_x0, width_final - destination_x0)
    overlap_height = min(canvas.shape[0] - source_y0, height_final - destination_y0)
    if overlap_width <= 0 or overlap_height <= 0:
        blocked("CANVAS_NOT_OVERLAPPING_NATIVE_BOARD")
    aligned = np.zeros(BOARD_SHAPE, np.uint8)
    aligned[destination_y0:destination_y0 + overlap_height,
            destination_x0:destination_x0 + overlap_width] = canvas[
                source_y0:source_y0 + overlap_height,
                source_x0:source_x0 + overlap_width]
    outside = canvas.copy()
    outside[source_y0:source_y0 + overlap_height,
            source_x0:source_x0 + overlap_width] = 0
    if np.any(outside[:, :, 3]):
        blocked("CANVAS_INK_OUTSIDE_NATIVE_BOARD")
    return aligned, {"node_origin_physical": [int(left), int(top)],
                     "cropped_source_xy": [source_x0, source_y0],
                     "pasted_native_xy": [destination_x0, destination_y0],
                     "overlap_native_size": [overlap_width, overlap_height]}


def verify_parent(parent):
    path = parent / "report.json"
    if not path.is_file():
        blocked("FROZEN_PARENT_MISSING")
    report = json.loads(path.read_text("utf8"))
    if (report.get("experiment") != s3.EXPERIMENT or
            report.get("github_sha") != PARENT_SHA or
            report.get("github_run_id") != PARENT_RUN or
            report.get("native_total_PNG") != 91 or
            report.get("C0_H1_all_40_ordered_composites") != "FAIL" or
            report.get("H2_all_20_order_pairs") != "PASS" or
            report.get("S0_BLIND_used") is not False):
        blocked("FROZEN_PARENT_REPORT_PROVENANCE")
    hashes = report.get("members_sha256", {})
    if not isinstance(hashes, dict) or len(hashes) != 294:
        blocked("FROZEN_PARENT_MEMBER_SET")
    for relative, expected in hashes.items():
        part = parent / relative
        if not part.is_file() or sha256(part.read_bytes()) != expected:
            blocked("FROZEN_PARENT_MEMBER_SHA_" + relative)
    frozen = json.loads((parent / "FROZEN_S3_MANIFEST.json").read_text("utf8"))
    if frozen != s3.manifest():
        blocked("FROZEN_PARENT_MANIFEST_CHANGED")
    return report


def native_png_in_parent(parent, sample_id, repeat=False, blank=False):
    if blank:
        return parent / "S3_REAL_EGRET_BLANK.png"
    if repeat:
        return parent / "replays" / (sample_id + "_REAL_EGRET.png")
    return (parent / "native" / sample_id /
            (sample_id + "_REAL_EGRET.png"))


def capture(driver, scene, output, parent):
    sid = scene["sample_id"]
    root = output / "native" / sid
    root.mkdir(parents=True, exist_ok=False)
    write_json(root / "SOURCE_PLAN.json", scene["source_strokes"])
    write_json(root / "RUNTIME_PLAN.json", scene["runtime_strokes"])
    result = driver.execute_script(
        "return window.AutoDrawBPRED_S3v2CanvasCapture(arguments[0]);",
        scene["runtime_strokes"])
    if (not isinstance(result, dict) or
            result.get("schema") != "ENGINE001_BPRED_S3V2_TRUE_NATIVE_CANVAS_WEBGL_PAIR" or
            result.get("originalCanvasRendererRestored") is not True or
            result.get("sourceStrokeCount") != len(scene["runtime_strokes"]) or
            len(result.get("captures", [])) != 1):
        blocked("INSTRUMENTATION_NOT_RESTORED_OR_AMBIGUOUS")
    stage = result["captures"][0]
    img, raw_sha = read_png_data_url(stage.pop("originalCanvasPngDataUrl"),
                                     root / (sid + "_REAL_CANVAS_INTERMEDIATE.png"))
    if list(img.shape[:2][::-1]) != stage.get("canvasSize"):
        blocked("INTERMEDIATE_CANVAS_SIZE_MISMATCH")
    aligned, mapping = source_stage_align(img, stage["node"], stage["transform"])
    Image.fromarray(aligned, mode="RGBA").save(
        root / (sid + "_ALIGNED_MODEL_ONLY.png"))
    native, meta = p4d3.read_webgl_result(
        result["native"], root, sid + "_REAL_WEBGL")
    if (meta.get("schema") != "ENGINE001_B1R_P4A2_NATIVE_1_TO_10" or
            meta.get("renderer") != "real Egret 5.4.1 BoardPane/WebGLRenderer" or
            native.shape != BOARD_SHAPE or
            meta.get("strokeCount") != len(scene["runtime_strokes"])):
        blocked("FINAL_NOT_ORIGINAL_EGRET")
    previous = native_png_in_parent(parent, sid)
    if not previous.is_file() or sha256(previous.read_bytes()) != meta["source_sha256"]:
        blocked("RENDER_NOT_BYTE_EXACT_PARENT_" + sid)
    expected = np.any((aligned[:, :, 3] > 0) | (native[:, :, 3] > 0))
    if not expected:
        blocked("EMPTY_INTERMEDIATE_OR_NATIVE_INK")
    mask = (aligned[:, :, 3] > 0) | (native[:, :, 3] > 0)
    deviation, _ = s3.rgba_difference(aligned, native, mask)
    write_json(root / "NATIVE_CAPTURE_METADATA.json", {
        "sample_id": sid, "source_plan_sha256": scene["source_plan_sha256"],
        "runtime_plan_sha256": scene["runtime_plan_sha256"],
        "raw_canvas_sha256": raw_sha, "native_webgl_sha256": meta["source_sha256"],
        "stage_source": stage, "native_renderer": meta,
        "source_to_native_geometry": mapping,
        "intermediate_to_webgl_RGBA": deviation})
    return aligned, native, deviation


def row_for(width, relation, intermediate, final):
    row = {"pair_id": f"BPRED-S3V2-W{width:02d}-{relation}",
           "width": width, "relation": relation,
           "ordered_variants": {}, "stage_attribution": None}
    for variant in ("A_THEN_B", "B_THEN_A"):
        def compare(frames):
            a = p4d3.roi(frames["A_ONLY"], s3.CX, s3.CY)
            b = p4d3.roi(frames["B_ONLY"], s3.CX, s3.CY)
            bottom, top = (a, b) if variant == "A_THEN_B" else (b, a)
            target = p4d3.roi(frames[variant], s3.CX, s3.CY)
            modeled = s3.source_over(bottom, top)
            mask = ((a[:, :, 3] > 0) | (b[:, :, 3] > 0) |
                    (target[:, :, 3] > 0))
            metric, _ = s3.rgba_difference(modeled, target, mask)
            metric["frozen_H1_pass"] = bool(
                metric["max_channel_byte"] <= 2 and
                metric["mean_channel_byte"] <= 1)
            return metric
        cm = compare(intermediate)
        wm = compare(final)
        row["ordered_variants"][variant] = {
            "source_over_original_C0_on_true_Canvas": cm,
            "source_over_original_C0_on_true_WebGL": wm}
    canvas_all = all(z["source_over_original_C0_on_true_Canvas"]["frozen_H1_pass"]
                     for z in row["ordered_variants"].values())
    webgl_all = all(z["source_over_original_C0_on_true_WebGL"]["frozen_H1_pass"]
                    for z in row["ordered_variants"].values())
    row["stage_attribution"] = (
        "CANVAS_C0_MISMATCH_PRESENT" if not canvas_all else
        "WEBGL_ONLY_C0_FAILURE_CANDIDATE" if not webgl_all else
        "BOTH_STAGE_C0_WITHIN_FROZEN_H1")
    return row


def run(workspace, engine, renderer, parent, capture_js, output):
    if output.exists():
        blocked("OUTPUT_EXISTS")
    pins = [
        (workspace / "AutoDraw_Stage20" / "docs" / E0_FILE, E0_BLOB),
        (engine, p4d3.ENGINE_GIT_BLOB), (renderer, p4d3.RENDERER_GIT_BLOB),
        (Path(p4d3.__file__), s3.P4D3_BLOB), (Path(s3.__file__), PARENT_S3_BLOB)]
    for path, sha in pins:
        if not path.is_file() or p4b1.git_blob(path.read_bytes()) != sha:
            blocked("PINNED_SOURCE_" + path.name)
    if not capture_js.is_file() or capture_js.name != Path(RENDERER_JS).name:
        blocked("MISSING_SCOPED_P4D15_REUSE_JS")
    previous = verify_parent(parent)
    plan = s3.manifest()
    output.mkdir(parents=True)
    write_json(output / "FROZEN_SOURCE_MANIFEST.json", plan)
    meta_rows, rows, repeats = [], [], []
    canvas_frames, webgl_frames = {}, {}
    with p4b7.native_egret_session(workspace) as driver:
        caps = {k: driver.capabilities.get(k)
                for k in ("browserName", "browserVersion", "platformName")}
        if caps["browserName"] != "firefox" or not str(caps["browserVersion"]).startswith("159."):
            blocked("BROWSER_NOT_PINNED")
        driver.execute_script(capture_js.read_text("utf8"))
        present = driver.execute_script(
            "return typeof window.AutoDrawBPRED_S3v2CanvasCapture;")
        if present != "function":
            blocked("JS_CAPTURE_NOT_EXPOSED")
        blank, bm = p4d3.read_webgl_result(
            driver.execute_script(p4d3.CMD, []), output, "S3V2_REAL_EGRET_BLANK")
        if bm.get("schema") != "ENGINE001_B1R_P4A2_BLANK_WEBGL" or np.any(blank[:, :, 3]):
            blocked("TRUE_NATIVE_BLANK_INVALID")
        if sha256(native_png_in_parent(parent, "", blank=True).read_bytes()) != bm["source_sha256"]:
            blocked("BLANK_BYTE_DRIFT")
        with (output / "PAIRS_APPEND_ONLY.jsonl").open("x", encoding="utf8") as f:
            for width in s3.WIDTHS:
                for relation in s3.RELATIONS:
                    c, w = {}, {}
                    for variant in s3.VARIANTS:
                        scene = s3.plans_for(width, relation)[variant]
                        ca, we, change = capture(driver, scene, output, parent)
                        c[variant], w[variant] = ca, we
                        meta_rows.append({"sample_id": scene["sample_id"],
                                          "intermediate_to_final": change})
                    canvas_frames[(width, relation)] = c
                    webgl_frames[(width, relation)] = w
                    row = row_for(width, relation, c, w)
                    rows.append(row)
                    f.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
                    f.flush()
                    print("BPRED_S3V2_TRUE_CANVAS_PAIR", len(rows), "/20", flush=True)
        for control in plan["controls"]:
            sid = control["sample_id"]
            scene = s3.plans_for(control["width"], "CROSSING")["A_THEN_B"]
            outdir = output / "replays"
            outdir.mkdir(exist_ok=True)
            replay, meta = p4d3.read_scene(driver, outdir, sid + "_REAL_EGRET",
                                            scene["runtime_strokes"])
            old = native_png_in_parent(parent, sid, repeat=True)
            exact = bool(meta["source_png_sha256"] == sha256(old.read_bytes()))
            repeats.append({"sample_id": sid,
                            "parent_sample_id": scene["sample_id"],
                            "original_native_byte_exact": exact,
                            "png_sha256": meta["source_png_sha256"]})
            if not exact or not np.array_equal(
                    replay, webgl_frames[(control["width"], "CROSSING")]["A_THEN_B"]):
                blocked("REPLAY_NOT_EXACT_" + sid)
    write_json(output / "REPLAY_CONTROLS.json", repeats)
    canvas_pass = sum(v["source_over_original_C0_on_true_Canvas"]["frozen_H1_pass"]
                      for row in rows for v in row["ordered_variants"].values())
    webgl_pass = sum(v["source_over_original_C0_on_true_WebGL"]["frozen_H1_pass"]
                     for row in rows for v in row["ordered_variants"].values())
    if webgl_pass != 10:
        blocked("ORIGINAL_S3_H1_DRIFT_NO_RETUNE")
    report = {
        "experiment": EXPERIMENT, "github_sha": os.getenv("GITHUB_SHA"),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "source_parent_git_sha": PARENT_SHA,
        "source_parent_run_id": PARENT_RUN,
        "source_parent_artifact": PARENT_ARTIFACT,
        "parent_report_sha256": sha256((parent / "report.json").read_bytes()),
        "E0_frozen_blob": E0_BLOB, "stage_capture_js_git_blob": p4b1.git_blob(
            capture_js.read_bytes()),
        "source_renderer_git_blob": p4d3.RENDERER_GIT_BLOB,
        "native_browser": caps, "true_native_primary": 80,
        "true_native_intermediate_canvas_PNG": 80, "true_native_final_webgl_PNG": 91,
        "true_native_replays": len(repeats), "native_blank_alpha0": True,
        "all_primary_parent_byte_exact": True, "all_replays_byte_exact": True,
        "H1_original_final_S3_pass_count_40": webgl_pass,
        "H1_new_true_intermediate_Canvas_pass_count_40": canvas_pass,
        "original_S3_H1": "FAIL_UNCHANGED",
        "stage_diagnostic_not_safety_promotion": True,
        "source_original_s3_science": previous["C0_H1_all_40_ordered_composites"],
        "S0_BLIND_used": False, "protected_EF_paint_quality": "FAIL_UNCHANGED",
        "E4_live_game": "NOT_RUN", "E5_independent": "NOT_RUN",
        "exact_game_CHALK": None, "production_promotion": False}
    report["members_sha256"] = {
        str(f.relative_to(output)).replace("\\", "/"): sha256(f.read_bytes())
        for f in sorted(output.rglob("*")) if f.is_file()}
    write_json(output / "report.json", report)
    print("BPRED_S3V2_E3_80_NATIVE_CANVAS_91_FINAL", "CANVAS_H1",
          canvas_pass, "/40", "WEBGL_H1", webgl_pass, "/40", flush=True)
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    for key in ("workspace", "engine", "renderer", "parent", "capture-js", "output"):
        ap.add_argument("--" + key, type=Path, required=True)
    args = ap.parse_args()
    run(args.workspace, args.engine, args.renderer, args.parent, args.capture_js,
        args.output)

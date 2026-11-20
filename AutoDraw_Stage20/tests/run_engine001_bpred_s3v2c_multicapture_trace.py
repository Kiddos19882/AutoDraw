#!/usr/bin/env python3
"""BPRED-S3v2c: eight frozen genuinely original Egret multi-Canvas trace captures."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch

import numpy as np

import run_engine001_bpred_s3_native_source_over as s3
import run_engine001_bpred_s3v2_native_canvas_stage as v2
import run_engine001_b1r_p4d3_native_brush_repeatability as p4d3
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
from engine001_bpred_s3v2b_png_equivalence import verify_parent_png_equivalence

EXPERIMENT = "ENGINE001_BPRED_S3V2C_MULTICAPTURE_TRACE_V1"
E0_FILE = "ENGINE001_BPRED001_S3V2C_CANVAS_CAPTURE_TRACE_PREREG_2026-11-20.md"
E0_BLOB = "b8a22597fee26cc3e950bb6289aad83a5f465a2d"
S3_FILE_BLOB = "1bf56df9507f2a34fd16e68eef190229c3184ce5"
GAME_BLOB = p4d3.ENGINE_GIT_BLOB
RENDERER_BLOB = p4d3.RENDERER_GIT_BLOB


def blocked(reason):
    raise ValueError("BLOCKED_BPRED_S3V2C_" + reason)


def frozen_samples():
    scenes = []
    for width in (1, 10):
        for relation in s3.RELATIONS:
            for variant in ("A_ONLY", "A_THEN_B"):
                scenes.append(s3.plans_for(width, relation)[variant])
    assert len(scenes) == 8 and len({s["sample_id"] for s in scenes}) == 8
    return scenes


def compare_snapshots(images, snapshots):
    out = []
    for i in range(len(images)):
        for j in range(i + 1, len(images)):
            aa, bb = images[i], images[j]
            valid_same_shape = aa.shape == bb.shape
            out.append({
                "first_capture": i, "second_capture": j,
                "same_node_bounds": snapshots[i]["node"] == snapshots[j]["node"],
                "same_canvas_transform": snapshots[i]["transform"] == snapshots[j]["transform"],
                "same_draw_data_count": snapshots[i]["drawDataCount"] == snapshots[j]["drawDataCount"],
                "same_canvas_shape": bool(valid_same_shape),
                "same_rgba_pixel_values": bool(valid_same_shape and np.array_equal(aa, bb)),
                "RGBA_changed_pixels": (int(np.any(aa != bb, axis=2).sum())
                                        if valid_same_shape else None)})
    return out


@contextmanager
def pinned_native_egret_session(workspace):
    """Reuse existing P4B7 source harness, but bind EXACT Firefox executable."""
    path = Path(os.environ.get("AUTODRAW_PINNED_FIREFOX_BINARY", ""))
    if not path.is_file() or path.name.lower() != "firefox.exe":
        blocked("PINNED_FIREFOX_EXECUTABLE_MISSING")
    original_firefox = p4b7.webdriver.Firefox

    def exact_binary_firefox(*args, **kwargs):
        opts = kwargs.get("options")
        if opts is None or args:
            blocked("UNEXPECTED_SOURCE_FIREFOX_CONSTRUCTOR")
        opts.binary_location = str(path.resolve())
        return original_firefox(*args, **kwargs)

    with patch.object(p4b7.webdriver, "Firefox", exact_binary_firefox):
        with p4b7.native_egret_session(workspace) as driver:
            yield driver


def run(workspace, engine, renderer, parent, trace_js, output):
    if output.exists():
        blocked("OUTPUT_EXISTS")
    pins = [
        (workspace / "AutoDraw_Stage20" / "docs" / E0_FILE, E0_BLOB),
        (engine, GAME_BLOB), (renderer, RENDERER_BLOB),
        (Path(s3.__file__), S3_FILE_BLOB)]
    for file, blob in pins:
        if not file.is_file() or p4b1.git_blob(file.read_bytes()) != blob:
            blocked("FROZEN_GIT_BLOB_" + file.name)
    if not trace_js.is_file() or trace_js.name != "engine001_bpred_s3v2c_multicapture_trace.js":
        blocked("MISSING_INSTRUMENTATION")
    v2.verify_parent(parent)
    scenes = frozen_samples()
    output.mkdir(parents=True)
    v2.write_json(output / "FROZEN_EIGHT_NATIVE_CASES.json", scenes)
    rows = []
    with pinned_native_egret_session(workspace) as driver:
        caps = {k: driver.capabilities.get(k) for k in
                ("browserName", "browserVersion", "platformName")}
        if caps["browserName"] != "firefox" or not str(caps["browserVersion"]).startswith("159."):
            blocked("BROWSER_VERSION_DRIFT_" + str(caps))
        driver.execute_script(trace_js.read_text("utf8"))
        if driver.execute_script(
                "return typeof window.AutoDrawBPRED_S3v2cCaptureTrace;") != "function":
            blocked("TRACE_JS_NOT_LOADED")
        with (output / "CAPTURES_APPEND_ONLY.jsonl").open("x", encoding="utf8") as ledger:
            for case in scenes:
                sid = case["sample_id"]
                folder = output / "native" / sid
                folder.mkdir(parents=True, exist_ok=False)
                v2.write_json(folder / "source_plan.json", case["source_strokes"])
                v2.write_json(folder / "runtime_plan.json", case["runtime_strokes"])
                val = driver.execute_script(
                    "return window.AutoDrawBPRED_S3v2cCaptureTrace(arguments[0]);",
                    case["runtime_strokes"])
                if (not isinstance(val, dict) or
                        val.get("schema") != "ENGINE001_BPRED_S3V2C_ORIGINAL_CANVAS_MULTICAPTURE_TRACE" or
                        val.get("originalCanvasRendererRestored") is not True or
                        val.get("originalStrokeCount") != len(case["runtime_strokes"]) or
                        not 1 <= len(val.get("captures", [])) <= 64):
                    blocked("INCOMPLETE_TRUE_NATIVE_TRACE_" + sid)
                native, webgl_meta = p4d3.read_webgl_result(
                    val["native"], folder, sid + "_REAL_EGRET_FINAL_WEBGL")
                if (webgl_meta.get("schema") != "ENGINE001_B1R_P4A2_NATIVE_1_TO_10"
                        or webgl_meta.get("renderer") !=
                            "real Egret 5.4.1 BoardPane/WebGLRenderer"):
                    blocked("NOT_REAL_NATIVE_EGRET_" + sid)
                original = v2.native_png_in_parent(parent, sid)
                new = folder / (sid + "_REAL_EGRET_FINAL_WEBGL.png")
                webgl_proof = verify_parent_png_equivalence(
                    original.read_bytes(), new.read_bytes())
                frames, captures = [], []
                for index, src in enumerate(val["captures"]):
                    png = folder / f"{sid}_CANVAS_CALL_{index:02d}_TRUE.png"
                    image, h = v2.read_png_data_url(
                        src.pop("rawCanvasPngDataUrl"), png)
                    if image.shape[:2][::-1] != tuple(src["size"]):
                        blocked("ORIGINAL_CONTEXT_IMAGE_SIZE_" + sid)
                    frames.append(image)
                    captures.append({
                        "chronological_index": src["chronologicalIndex"],
                        "png_sha256": h,
                        "original_node": src["node"],
                        "original_transform": src["transform"],
                        "canvas_size": src["size"],
                        "drawDataCount": src["drawDataCount"]})
                pairwise = compare_snapshots(frames, val["captures"])
                row = {
                    "sample_id": sid, "width": case["width"],
                    "relation": case["relation"], "variant": case["variant"],
                    "source_plan_sha256": case["source_plan_sha256"],
                    "runtime_plan_sha256": case["runtime_plan_sha256"],
                    "capture_count": len(frames),
                    "all_duplicate_snapshots_pixel_exact": all(
                        x["same_rgba_pixel_values"] for x in pairwise),
                    "all_duplicate_geometry_exact": all(
                        x["same_node_bounds"] and x["same_canvas_transform"] and
                        x["same_draw_data_count"] for x in pairwise),
                    "true_canvas_captures": captures,
                    "pairwise_no_selection": pairwise,
                    "parent_native_webgl_equivalence": webgl_proof,
                    "original_native_rgba_nonempty": bool(np.any(native[:, :, 3]))}
                if not row["original_native_rgba_nonempty"]:
                    blocked("NO_ORIGINAL_NATIVE_PAINT_" + sid)
                rows.append(row)
                ledger.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
                ledger.flush()
                print("BPRED_S3V2C_TRUE_ORIGINAL_CANVAS_TRACE", len(rows), "/8",
                      sid, "calls", len(frames), flush=True)
    v2.write_json(output / "CAPTURE_STRUCTURE_SUMMARY.json", {
        "case_count": len(rows), "capture_counts": [r["capture_count"] for r in rows],
        "all_canvas_duplicates_rgba_exact_case_count": sum(
            r["all_duplicate_snapshots_pixel_exact"] for r in rows),
        "all_canvas_duplicates_geometry_exact_case_count": sum(
            r["all_duplicate_geometry_exact"] for r in rows)})
    report = {
        "experiment": EXPERIMENT,
        "github_sha": os.getenv("GITHUB_SHA"),
        "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "parent_S3_run": v2.PARENT_RUN,
        "parent_S3_SHA": v2.PARENT_SHA,
        "frozen_E0_blob": E0_BLOB,
        "native_browser": caps, "scenes_frozen": 8,
        "true_final_webgl_PNG": 8,
        "true_canvas_intermediate_PNG": sum(x["capture_count"] for x in rows),
        "all_canvas_snapshots_preserved_without_selection": True,
        "all_parent_webgl_deBG_only_equivalent": True,
        "S3_science_H1": "FAIL_UNCHANGED",
        "S3v2_S3v2b_research_status": "TECHNICAL_BLOCKED_ARCHIVED",
        "S0_BLIND_used": False, "P4D18_protected_quality": "FAIL_UNCHANGED",
        "E4_live": "NOT_RUN", "E5_independent": "NOT_RUN", "exact_CHALK": None,
        "production_promotion": False}
    report["members_sha256"] = {
        str(f.relative_to(output)).replace("\\", "/"):
            hashlib.sha256(f.read_bytes()).hexdigest()
        for f in sorted(output.rglob("*")) if f.is_file()}
    v2.write_json(output / "report.json", report)
    print("BPRED_S3V2C_E3_8_NATIVE_SCENES",
          "CANVAS_CALLS", report["true_canvas_intermediate_PNG"])
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    for name in ("workspace", "engine", "renderer", "parent", "trace-js", "output"):
        ap.add_argument("--" + name, type=Path, required=True)
    a = ap.parse_args()
    run(a.workspace, a.engine, a.renderer, a.parent, a.trace_js, a.output)

#!/usr/bin/env python3
"""S3v2h frozen research: actual original Egret Canvas2D.stroke post-call snapshots.

Strict 24 existing S3v2f scenes; unexpected structure BLOCKED, never S4 BLIND.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image

import run_engine001_bpred_s3_native_source_over as s3
import run_engine001_bpred_s3v2_native_canvas_stage as v2
import run_engine001_bpred_s3v2c_multicapture_trace as ctrace
import run_engine001_bpred_s3v2f_prospective_native_rgba8 as v2f
import run_engine001_b1r_p4d3_native_brush_repeatability as p4d3
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
from engine001_bpred_s3v2b_png_equivalence import verify_parent_png_equivalence

EXPERIMENT = "ENGINE001_BPRED_S3V2H_REAL_STROKE_STEP_CAPTURE_V1"
E0_FILE = "ENGINE001_BPRED001_S3V2H_NATIVE_CANVAS_STROKE_STEP_PREREG_2026-11-20.md"
E0_BLOB = "75255a7f48d5be00a34a164edb2bcf03e6349d76"
PARENT_RUN = "44710870514"
PARENT_SHA = "819b7fd20272e5ac87ead72ce0610687fa51cbf4"
PARENT_EXPERIMENT = v2f.EXPERIMENT
PARENT_E0 = v2f.E0_BLOB
PARENT_MEMBER_COUNT = 655
WIDTHS = (1, 5, 10)
RELATIONS = ("CROSS_ROTATED", "NEAR_SKEW")
VARIANTS = ("A_ONLY", "B_ONLY", "A_THEN_B", "B_THEN_A")
JS_NAMES = (
    "engine001_bpred_s3v2c_multicapture_trace.js",
    "engine001_bpred_s3v2d_source_node_selector.js",
    "engine001_bpred_s3v2h_original_stroke_step_trace.js"
)
JS_BLOBS = (
    "250a6f46c12498c15157825664a08ee4f12a2b83",
    "de3b5c5f956e3de7a71817830874b346904bc9e2",
    "383e0b25000f4c387687fb38423dce790f149499"
)
SOURCE_PY_BLOBS = {
    "run_engine001_bpred_s3_native_source_over.py": "1bf56df9507f2a34fd16e68eef190229c3184ce5",
    "run_engine001_bpred_s3v2_native_canvas_stage.py": "511e81a362c4340e0dfdc36a292faa9cb2ef1e83",
    "run_engine001_bpred_s3v2c_multicapture_trace.py": "974de6a86359e9ff49e2e77ee1f420dffa08064b",
    "run_engine001_bpred_s3v2f_prospective_native_rgba8.py": "0c3b799f6bc22958911d35420a30fef1950813dd",
    "run_engine001_b1r_p4d3_native_brush_repeatability.py": "3437a9326b381d9c94d6ade80059d40adf233d09"
}


def blocked(label):
    raise ValueError("BLOCKED_BPRED_S3V2H_" + label)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def check_pins(workspace, engine, renderer, scripts):
    pins = [(workspace / "AutoDraw_Stage20" / "docs" / E0_FILE, E0_BLOB),
            (engine, p4d3.ENGINE_GIT_BLOB),
            (renderer, p4d3.RENDERER_GIT_BLOB)]
    tests = workspace / "AutoDraw_Stage20" / "tests"
    pins += [(tests / name, sha) for name, sha in SOURCE_PY_BLOBS.items()]
    if tuple(p.name for p in scripts) != JS_NAMES:
        blocked("JS_ORDER_NOT_PREREGISTERED")
    pins += list(zip(scripts, JS_BLOBS))
    for p, expected in pins:
        if not p.is_file() or p4b1.git_blob(p.read_bytes()) != expected:
            blocked("SOURCE_BLOB_DRIFT_" + p.name)
    return True


def verify_parent(z):
    names = z.namelist()
    if (len(names) != 656 or len(set(names)) != len(names)
            or z.testzip() is not None
            or any(x.startswith("/") or "\\" in x or ".." in Path(x).parts for x in names)):
        blocked("PARENT_ZIP_MEMBERS_OR_CRC")
    report = json.loads(z.read("report.json"))
    if (report.get("experiment") != PARENT_EXPERIMENT
            or report.get("github_run_id") != PARENT_RUN
            or report.get("github_sha") != PARENT_SHA
            or report.get("E0_blob") != PARENT_E0
            or report.get("true_native_primary") != 80
            or report.get("true_native_main_canvas_PNG") != 80
            or report.get("true_native_mask_canvas_PNG") != 80
            or report.get("true_native_final_webgl_PNG") != 91
            or report.get("H1_QH_new_native_exact_stage") != "PASS"
            or report.get("H2_QH_source_over_at_least_30_of_40") != "FAIL"
            or report.get("S0_BLIND_used") is not False):
        blocked("PARENT_S3V2F_PROVENANCE")
    hashes = report.get("members_sha256", {})
    if len(hashes) != PARENT_MEMBER_COUNT or set(hashes) != set(names) - {"report.json"}:
        blocked("PARENT_MEMBER_SET")
    for name, expected in hashes.items():
        if digest(z.read(name)) != expected:
            blocked("PARENT_MEMBER_SHA_" + name)
    manifest = json.loads(z.read("FROZEN_S3V2F_MANIFEST.json"))
    if manifest.get("experiment") != PARENT_EXPERIMENT or manifest.get("E0_blob") != PARENT_E0:
        blocked("PARENT_MANIFEST_HEADER")
    if len(manifest.get("scenes", [])) != 80 or len(manifest.get("controls", [])) != 10:
        blocked("PARENT_MANIFEST_CARDINALITY")
    matrix = {}
    for row in manifest["scenes"]:
        k = (row["width"], row["relation"], row["variant"])
        if k in matrix or row.get("sample_id") != (
                f"BPRED-S3V2F-W{row['width']:02d}-{row['relation']}-{row['variant']}"):
            blocked("PARENT_DUPLICATE_OR_MUTATED_SAMPLE_ID")
        if (s3.digest(s3.canonical(row["source_strokes"])) != row["source_plan_sha256"]
                or s3.digest(s3.canonical(row["runtime_strokes"])) != row["runtime_plan_sha256"]):
            blocked("PARENT_PLAN_SHA")
        sample = row["sample_id"]
        stem = "native/" + sample + "/" + sample
        if (json.loads(z.read(stem + "_REAL_WEBGL.png")) if False else False):
            blocked("UNREACHABLE")  # no reinterpretation of PNG
        folder = "native/" + sample + "/"
        if (json.loads(z.read(folder + "SOURCE_PLAN.json")) != row["source_strokes"]
                or json.loads(z.read(folder + "RUNTIME_PLAN.json")) != row["runtime_strokes"]):
            blocked("PARENT_PLAN_FILE_DRIFT")
        if any(x in json.dumps(row).upper() for x in ("G32", "V44")):
            blocked("FORBIDDEN_LEGACY_SOURCE")
        matrix[k] = row
    expected_keys = {(w,r,v) for w in WIDTHS for r in RELATIONS for v in VARIANTS}
    if not expected_keys <= set(matrix):
        blocked("PREREG_24_SOURCE_CASES_MISSING")
    return matrix


def expected_event_count(variant):
    if variant not in VARIANTS:
        blocked("UNEXPECTED_VARIANT")
    return 1 if variant.endswith("_ONLY") else 2


def full_delta(a, b):
    if a.shape != b.shape or a.dtype != np.uint8 or b.dtype != np.uint8:
        blocked("DIFF_SHAPE")
    delta = np.abs(a.astype(np.int16)-b.astype(np.int16)).astype(np.uint8)
    return delta, {
        "RGBA_different_physical_pixels": int(np.any(delta != 0, axis=2).sum()),
        "RGB_different_physical_pixels": int(np.any(delta[:,:,:3] != 0, axis=2).sum()),
        "alpha_different_physical_pixels": int(np.count_nonzero(delta[:,:,3])),
        "max_channel_byte": int(delta.max(initial=0)),
        "alpha_absolute_sum": int(delta[:,:,3].sum(dtype=np.int64)),
        "RGB_absolute_sum": int(delta[:,:,:3].sum(dtype=np.int64))
    }


def validate_native_response(response, scene, dir_path):
    sid = scene["sample_id"]
    if not isinstance(response, dict):
        blocked("NON_DICT_SOURCE_RESPONSE_" + sid)
    source = response.get("source", {})
    events = response.get("mainStrokeSnapshots", [])
    counts = {"sample_id": sid, "variant": scene["variant"],
              "expected_main_stroke_calls": expected_event_count(scene["variant"]),
              "main_stroke_calls": response.get("trueMainStrokeCalls"),
              "mask_stroke_calls": response.get("originalMaskStrokeCalls"),
              "actual_events": len(events) if isinstance(events, list) else None,
              "originalStrokeMethodRestored": response.get("originalStrokeMethodRestored"),
              "originalCanvasRendererRestored": source.get("originalCanvasRendererRestored"),
              "originalCaptureCount": source.get("originalCaptureCount"),
              "schema": response.get("schema")}
    v2.write_json(dir_path / "STRUCTURE_COUNTS.json", counts)
    if (response.get("schema") != "ENGINE001_BPRED_S3V2H_ORIGINAL_CANVAS_STROKE_STEP_TRACE"
            or response.get("originalStrokeMethodRestored") is not True
            or source.get("originalCanvasRendererRestored") is not True
            or source.get("structuralSelectionVersion") != "S3V2D_SOURCE_NODE_GEOMETRY_FROZEN_V1"
            or source.get("originalCaptureCount") != 2
            or not isinstance(events, list)
            or source.get("sourceStrokeCount") != len(scene["runtime_strokes"])):
        blocked("ORIGINAL_RENDERER_PROVENANCE_" + sid)
    if len(events) != expected_event_count(scene["variant"]):
        blocked("ACTUAL_MAIN_STROKE_COUNT_" + sid + "_" + str(len(events)))
    if response.get("trueMainStrokeCalls") != len(events):
        blocked("MAIN_CHRONOLOGY_COUNT_" + sid)
    return source, events


def read_scene(driver, z, scene, output):
    sid = scene["sample_id"]
    root = output / "native" / sid
    root.mkdir(parents=True, exist_ok=False)
    v2.write_json(root / "SOURCE_PLAN.json", scene["source_strokes"])
    v2.write_json(root / "RUNTIME_PLAN.json", scene["runtime_strokes"])
    response = driver.execute_script(
        "return window.AutoDrawBPRED_S3v2hOriginalStrokeStepTrace(arguments[0]);",
        scene["runtime_strokes"])
    source, events = validate_native_response(response, scene, root)
    if len(source.get("captures", [])) != 1 or not isinstance(source.get("mask_capture"), dict):
        blocked("MAIN_MASK_SOURCE_NOT_UNIQUE_" + sid)
    main, mask = source["captures"][0], source["mask_capture"]
    if (main.get("node") != {"x":-2,"y":-2,"width":464,"height":244}
            or main.get("canvasSize") != [1392,732]
            or main.get("transform") != [3,0,0,3,6,6]
            or main.get("drawDataCount") != 2+len(scene["runtime_strokes"])
            or mask.get("node") != {"x":0,"y":0,"width":460,"height":240}
            or mask.get("canvasSize") != [1380,720]
            or mask.get("transform") != [3,0,0,3,0,0]
            or mask.get("drawDataCount") != 1):
        blocked("MAIN_MASK_GEOMETRY_DRIFT_" + sid)
    main_raw, main_sha = v2.read_png_data_url(
        main.pop("originalCanvasPngDataUrl"), root / (sid + "_REAL_MAIN_CANVAS.png"))
    mask_raw, mask_sha = v2.read_png_data_url(
        mask.pop("originalCanvasPngDataUrl"), root / (sid + "_REAL_MASK_CANVAS.png"))
    if main_raw.shape != (732,1392,4) or mask_raw.shape != p4d3.NATIVE_SHAPE:
        blocked("MAIN_MASK_PIXEL_SIZE_" + sid)
    aligned, mapping = v2.source_stage_align(main_raw, main["node"], main["transform"])
    Image.fromarray(aligned, mode="RGBA").save(root / (sid + "_ALIGNED_MAIN_RGBA.png"))
    webgl, native_meta = p4d3.read_webgl_result(
        source["native"], root, sid + "_REAL_WEBGL")
    if (native_meta.get("schema") != "ENGINE001_B1R_P4A2_NATIVE_1_TO_10"
            or native_meta.get("renderer") != "real Egret 5.4.1 BoardPane/WebGLRenderer"
            or native_meta.get("strokeCount") != len(scene["runtime_strokes"])
            or webgl.shape != p4d3.NATIVE_SHAPE):
        blocked("WEBGL_NOT_ORIGINAL_EGRET_" + sid)
    stem = "native/" + sid + "/" + sid
    parent_raw = z.read(stem + "_REAL_WEBGL.png")
    equivalence = verify_parent_png_equivalence(
        parent_raw, (root / (sid + "_REAL_WEBGL.png")).read_bytes())
    with Image.open(io.BytesIO(z.read(stem + "_ALIGNED_MAIN_RGBA.png"))) as p:
        reference = np.asarray(p.convert("RGBA"), dtype=np.uint8).copy()
    if not np.array_equal(reference, aligned):
        blocked("PARENT_CANVAS_RGBA_DRIFT_" + sid)
    v2.write_json(root / "ORIGINAL_STAGE_PROVENANCE.json", {
        "source_case":sid, "main_sha256":main_sha, "mask_sha256":mask_sha,
        "main_metadata":main,"mask_metadata":mask,"native_meta":native_meta,
        "alignment":mapping,"parent_native_png_equivalence":equivalence})
    aligned_steps = []
    for i,event in enumerate(events):
        if (event.get("kind") != "original_main"
                or event.get("canvasSize") != [1392,732]
                or event.get("transform") != [3,0,0,3,6,6]
                or not isinstance(event.get("originalNativePngDataUrl"), str)):
            blocked("TRUE_MAIN_STEP_TRANSFORM_" + sid + "_" + str(i))
        png = root / (sid + f"_ORIGINAL_STROKE_STEP_{i+1:02d}.png")
        raster, raw_sha = v2.read_png_data_url(event.pop("originalNativePngDataUrl"), png)
        if raster.shape != (732,1392,4):
            blocked("TRUE_MAIN_STEP_PNG_SHAPE_" + sid)
        step_aligned, _ = v2.source_stage_align(raster, main["node"], main["transform"])
        aligned_steps.append(step_aligned)
        event["raw_png_sha256"] = raw_sha
        event["step_index"] = i+1
    v2.write_json(root / "TRUE_NATIVE_STROKE_EVENT_METADATA.json", {
        "mainStrokeCount":len(events), "maskEvents":response.get("maskStrokeMetadata"),
        "mainEvents":events, "true_main_node":main["node"]})
    if not aligned_steps:
        blocked("NO_MAIN_STROKES_" + sid)
    d_final, last_comparison = full_delta(aligned_steps[-1], aligned)
    Image.fromarray(d_final, mode="RGBA").save(root / "STEP_LAST_TO_TRUE_MAIN_DELTA.png")
    return {"scene":scene, "canvas":aligned, "webgl":webgl,
            "steps":aligned_steps,"last_to_main":last_comparison,
            "native_source_sha256": native_meta["source_sha256"]}


def compare_all(items, out):
    rows, by_pair = [], {}
    for item in items:
        scene=item["scene"]
        by_pair[(scene["width"],scene["relation"],scene["variant"])]=item
    for width in WIDTHS:
        for relation in RELATIONS:
            pair={(v):by_pair[(width,relation,v)] for v in VARIANTS}
            ac,bc=(pair["A_ONLY"]["canvas"],pair["B_ONLY"]["canvas"])
            for variant in VARIANTS:
                item=pair[variant]
                first=item["steps"][0]
                target=pair["A_ONLY"]["canvas"] if variant in ("A_ONLY","A_THEN_B") else pair["B_ONLY"]["canvas"]
                if variant=="B_THEN_A":
                    target=pair["B_ONLY"]["canvas"]
                first_image, m_first = full_delta(first,target)
                last_image, m_last = full_delta(item["steps"][-1],item["canvas"])
                root=out/"native"/item["scene"]["sample_id"]
                Image.fromarray(first_image,mode="RGBA").save(root/"STEP_FIRST_TO_ISOLATED_DELTA.png")
                Image.fromarray(last_image,mode="RGBA").save(root/"STEP_LAST_TO_FINAL_MAIN_DELTA.png")
                result={"sample_id":item["scene"]["sample_id"],"width":width,
                        "relation":relation,"variant":variant,
                        "observed_main_stroke_calls":len(item["steps"]),
                        "first_vs_isolated":m_first,"last_vs_original_main":m_last}
                if variant in ("A_THEN_B","B_THEN_A"):
                    d, effect = full_delta(item["steps"][0],item["steps"][-1])
                    Image.fromarray(d, mode="RGBA").save(root/"STEP_FIRST_TO_SECOND_EFFECT_RGBA.png")
                    ordered=s3.source_over(ac,bc) if variant=="A_THEN_B" else s3.source_over(bc,ac)
                    real=item["canvas"]
                    roi_model=p4d3.roi(ordered,s3.CX,s3.CY)
                    roi_real=p4d3.roi(real,s3.CX,s3.CY)
                    roi_webgl=p4d3.roi(item["webgl"],s3.CX,s3.CY)
                    union=(p4d3.roi(ac,s3.CX,s3.CY)[:,:,3]>0)|(
                        p4d3.roi(bc,s3.CX,s3.CY)[:,:,3]>0)|(roi_real[:,:,3]>0)
                    metric_canvas,_=s3.rgba_difference(roi_model,roi_real,union)
                    metric_webgl,_=s3.rgba_difference(
                        v2f.quantize_half_up(roi_model),roi_webgl,union)
                    for m in (metric_canvas,metric_webgl):
                        m["original_H1_pass"]=bool(
                            m["max_channel_byte"]<=2 and m["mean_channel_byte"]<=1)
                    result.update({"actual_first_to_second_effect":effect,
                                   "original_C0_against_canvas":metric_canvas,
                                   "original_C0_QH_against_webgl":metric_webgl})
                rows.append(result)
    return rows


def run(workspace,engine,renderer,scripts,source_zip,output):
    if output.exists():
        blocked("OUTPUT_EXISTS")
    check_pins(workspace,engine,renderer,scripts)
    with zipfile.ZipFile(source_zip) as z:
        matrix=verify_parent(z)
        output.mkdir(parents=True)
        selected=[matrix[(w,r,v)] for w in WIDTHS for r in RELATIONS for v in VARIANTS]
        v2.write_json(output/"SELECTED_FROZEN_S3V2F_24.json",selected)
        items=[]
        with ctrace.pinned_native_egret_session(workspace) as driver:
            caps={k:driver.capabilities.get(k) for k in
                  ("browserName","browserVersion","platformName")}
            if caps["browserName"]!="firefox" or not str(caps["browserVersion"]).startswith("159."):
                blocked("NOT_PINNED_FIREFOX159")
            for js in scripts:
                driver.execute_script(js.read_text("utf8"))
            if driver.execute_script("return typeof window.AutoDrawBPRED_S3v2hOriginalStrokeStepTrace;")!="function":
                blocked("STEP_JS_NOT_INSTALLED")
            blank,meta=p4d3.read_webgl_result(
                driver.execute_script(p4d3.CMD,[]),output,"S3V2H_REAL_EGRET_BLANK")
            if meta.get("schema")!="ENGINE001_B1R_P4A2_BLANK_WEBGL" or np.any(blank[:,:,3]):
                blocked("BLANK_NOT_ALPHA0")
            with (output/"OBSERVATIONS_APPEND_ONLY.jsonl").open("x",encoding="utf8") as f:
                for scene in selected:
                    try:
                        item=read_scene(driver,z,scene,output)
                    except Exception as exc:
                        v2.write_json(output/"BLOCKED_OR_FAILED_SCENE.json", {
                            "sample_id":scene["sample_id"],
                            "error_type":type(exc).__name__,"error":str(exc),
                            "all_prior_successful_scenes":len(items)})
                        raise
                    items.append(item)
                    entry={"sample_id":scene["sample_id"],"width":scene["width"],
                           "relation":scene["relation"],"variant":scene["variant"],
                           "true_main_stroke_calls":len(item["steps"]),
                           "last_to_true_main":item["last_to_main"],
                           "original_webgl_sha256":item["native_source_sha256"]}
                    f.write(json.dumps(entry,ensure_ascii=False,allow_nan=False)+"\n")
                    f.flush()
                    print("BPRED_S3V2H_NATIVE_STROKE_SCENE",len(items),"/24",flush=True)
            controls=[]
            for width in WIDTHS:
                case=matrix[(width,"CROSS_ROTATED","A_THEN_B")]
                p=f"BPRED-S3V2H-REPLAY-W{width:02d}"
                (output/"replays").mkdir(exist_ok=True)
                replay,meta=p4d3.read_scene(
                    driver,output/"replays",p+"_REAL_EGRET",case["runtime_strokes"])
                target=next(x for x in items if x["scene"]["sample_id"]==case["sample_id"])["webgl"]
                exact=np.array_equal(p4d3.roi(replay,s3.CX,s3.CY),
                                     p4d3.roi(target,s3.CX,s3.CY))
                controls.append({"sample_id":p,"parent_sample_id":case["sample_id"],
                                 "RGBA_ROI_exact":bool(exact)})
                if not exact:
                    blocked("REPLAY_ROI_RGBA_CHANGED_"+p)
        v2.write_json(output/"REPLAY_CONTROLS.json",controls)
        comparisons=compare_all(items,output)
        v2.write_json(output/"S1_S2_S3_ORIGINAL_NATIVE_COMPARISONS_24.json",comparisons)
        s1=sum(v["first_vs_isolated"]["RGBA_different_physical_pixels"] for v in comparisons)
        s2=sum(v["last_vs_original_main"]["RGBA_different_physical_pixels"]
               for v in comparisons if v["variant"] in ("A_THEN_B","B_THEN_A"))
        s3_canvas=sum(int(v["original_C0_against_canvas"]["original_H1_pass"])
                      for v in comparisons if v["variant"] in ("A_THEN_B","B_THEN_A"))
        s3_webgl=sum(int(v["original_C0_QH_against_webgl"]["original_H1_pass"])
                     for v in comparisons if v["variant"] in ("A_THEN_B","B_THEN_A"))
        report={"experiment":EXPERIMENT,"E0_blob":E0_BLOB,
                "github_sha":os.getenv("GITHUB_SHA"),
                "github_run_id":os.getenv("GITHUB_RUN_ID"),
                "source_original_E3_run":PARENT_RUN,"source_original_E3_sha":PARENT_SHA,
                "source_original_E3_members_sha_verified":655,
                "browser":caps,"true_native_cases":24,"true_main_canvas_PNG":24,
                "true_mask_canvas_PNG":24,"true_webgl_PNG":28,
                "true_main_stroke_step_PNG":sum(len(i["steps"]) for i in items),
                "true_replays":3,"blank_alpha0":True,
                "S1_first_stroke_exact":"PASS" if s1==0 else "FAIL",
                "S2_last_stroke_exact":"PASS" if s2==0 else "FAIL",
                "S1_first_stroke_diff_pixels":s1,
                "S2_last_stroke_diff_pixels":s2,
                "S3_original_C0_canvas_pass_count_12":s3_canvas,
                "S3_original_C0_QH_webgl_pass_count_12":s3_webgl,
                "original_S3v2f_H2":"FAIL_UNCHANGED",
                "original_S3v2g_P2":"FAIL_UNCHANGED",
                "scientific_S3_safe":False,"S0_BLIND_used":False,
                "E4_live_game":"NOT_RUN","E5_independent":"NOT_RUN",
                "exact_game_CHALK":None,"production_promotion":False}
        report["members_sha256"]={
            str(p.relative_to(output)).replace("\\","/"):digest(p.read_bytes())
            for p in sorted(output.rglob("*")) if p.is_file()}
        v2.write_json(output/"report.json",report)
        print("BPRED_S3V2H_S1_S2_NATIVE",report["S1_first_stroke_exact"],
              report["S2_last_stroke_exact"],s1,s2,flush=True)
        print("BPRED_S3V2H_DESCRIPTIVE_C0",s3_canvas,s3_webgl,flush=True)
        return report


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    for name in ("workspace","engine","renderer","trace-js","selector-js",
                 "stroke-js","source-zip","output"):
        ap.add_argument("--"+name,type=Path,required=True)
    a=ap.parse_args()
    run(a.workspace,a.engine,a.renderer,
        (a.trace_js,a.selector_js,a.stroke_js),a.source_zip,a.output)

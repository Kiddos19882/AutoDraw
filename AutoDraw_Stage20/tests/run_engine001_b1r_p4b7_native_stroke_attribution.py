#!/usr/bin/env python3
"""P4B7 diagnostic: genuine native Egret stroke-to-protected-pixel attribution.

No automatic paint repair, no legacy G32/V44 inputs, no CHALK assertion.
P4B6 is rerun fresh from the original, not imported from a frozen ZIP.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
import threading
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np
from PIL import Image
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from run_engine001_complex_holdout_v5 import read_webgl_result

import run_engine001_b1r_p4b6_source_protected_margin as p4b6
import run_engine001_b1r_p4b5_protected_baseline_rebalance as p4b5
import run_engine001_b1r_p4b4_boundary_tolerance_sweep as p4b4
from run_engine001_b1r_p1_fullrgb_edge_aware import check_source
from run_engine001_b1r_p2_joint_region_outline import digest

EXPERIMENT = "ENGINE001_B1R_P4B7_NATIVE_STROKE_ATTRIBUTION_V1"
FROZEN_P4B6_BLOB = "2f9ca1756da58e7062fcae6c6c64c83e4db79ea9"
SOURCE_SHA = "07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
RENDERER_BLOB = p4b6.RENDERER_BLOB
METHODS = p4b6.METHODS
ARM = "G1_0"
MAX_SPLIT_REPLAYS = 48
MAX_LOO_REPLAYS = 12
EXPECTED_TARGETS = 2
ALPHA_GATE = 24
EXPECTED_STROKES = {"E_SOBEL90": 214, "F_SOBEL90_LAB12": 212}


@contextmanager
def native_egret_session(workspace: Path):
    """Same genuine Egret BoardPane renderer, reused Firefox (test-only).

    Each render invokes the pinned JS method afresh; no path/width optimization,
    raster emulation, production settings, or source transformation.
    """
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(workspace), **kwargs)
        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    driver = None
    try:
        opts = Options()
        opts.add_argument("-headless")
        opts.set_preference("webgl.disabled", False)
        opts.set_preference("webgl.force-enabled", True)
        opts.set_preference("webgl.disable-fail-if-major-performance-caveat", True)
        driver = webdriver.Firefox(options=opts)
        driver.set_page_load_timeout(180)
        driver.set_script_timeout(180)
        driver.get(f"http://127.0.0.1:{server.server_port}/"
                   "AutoDraw_Stage20/tests/game_renderer_reference.html"
                   "?twoicons=home-envelope")
        WebDriverWait(driver, 90).until(
            lambda d: d.execute_script(
                "return document.body.dataset.twoIconStatus") == "ready")
        yield driver
    finally:
        if driver is not None:
            driver.quit()
        server.shutdown()
        server.server_close()


def native_replay_in_session(driver, output: Path, method: str,
                             stage: str, strokes: list[dict]):
    """Real pinned game renderer and a real blank control for every subset."""
    if (not strokes or not isinstance(stage, str) or not stage
            or method not in METHODS):
        raise ValueError("BLOCKED_P4B7_REPLAY_ARGS")
    stem = "P4B7-"+method+"-"+stage
    if (output/(stem+"-color-115.png")).exists():
        raise ValueError("BLOCKED_P4B7_NATIVE_CAPTURE_ALREADY_EXISTS")
    command = ("return window.AutoDrawGameRendererReference."
               "renderP4A2BrushWidths1to10Probe(arguments[0]);")
    real = driver.execute_script(command, strokes)
    rgba, metadata = read_webgl_result(real, output, stem+"-color-115")
    if (metadata.get("schema") != "ENGINE001_B1R_P4A2_NATIVE_1_TO_10"
            or metadata.get("renderer") !=
                "real Egret 5.4.1 BoardPane/WebGLRenderer"):
        raise ValueError("BLOCKED_P4B7_NOT_REAL_NATIVE_EGRET")
    empty = driver.execute_script(command, [])
    blank, blank_meta = read_webgl_result(empty, output, stem+"-blank")
    if (blank_meta.get("schema") != "ENGINE001_B1R_P4A2_BLANK_WEBGL"
            or blank_meta.get("renderer") !=
                "real Egret 5.4.1 BoardPane/WebGLRenderer"
            or np.any(blank[:, :, 3])):
        raise ValueError("BLOCKED_P4B7_NATIVE_BLANK_NONZERO")
    meta_path = output/(stem+"-metadata.json")
    meta_path.write_text(json.dumps(
        {"real_scene": metadata, "real_blank": blank_meta,
         "parent_stroke_count": len(strokes), "stage": stage},
        ensure_ascii=False, indent=2, allow_nan=False)+"\n", "utf8")
    return rgba


def normalized_subset(strokes: list[dict], indices: tuple[int, ...]) -> list[dict]:
    """Renumber IDs only for isolated replay; preserve coordinates/width/color."""
    if not isinstance(strokes, list) or not strokes or not isinstance(indices, tuple):
        raise ValueError("BLOCKED_P4B7_BAD_SUBSET")
    if not indices or len(set(indices)) != len(indices) or any(
            type(i) is not int or i < 0 or i >= len(strokes) for i in indices):
        raise ValueError("BLOCKED_P4B7_SUBSET_INDICES")
    if tuple(sorted(indices)) != indices:
        raise ValueError("BLOCKED_P4B7_UNSTABLE_ORDER")
    result = []
    for i in indices:
        s = strokes[i]
        if (not isinstance(s, dict) or not isinstance(s.get("strokeId"), str)
                or not isinstance(s.get("width"), int) or not 1 <= s["width"] <= 10
                or s.get("colorIndex") != 115 or not isinstance(s.get("points"), list)
                or not 2 <= len(s["points"]) <= 128
                or not isinstance(s.get("colorRgb"), int)):
            raise ValueError("BLOCKED_P4B7_INVALID_PARENT_STROKE")
        points = s["points"]
        xy = np.asarray([[p["x"], p["y"]] for p in points], np.float64)
        if (xy.shape != (len(points), 2) or not np.isfinite(xy).all()
                or np.any(xy[:, 0] < 155) or np.any(xy[:, 0] > 305)
                or np.any(xy[:, 1] < 0) or np.any(xy[:, 1] > 240)):
            raise ValueError("BLOCKED_P4B7_INVALID_SOURCE_COORD")
        result.append({"strokeId": "icon-%d" % len(result),
                       "width": s["width"], "colorIndex": s["colorIndex"],
                       "colorRgb": s["colorRgb"],
                       "points": [dict(p) for p in points]})
    return result


def protected_targets(rgba: np.ndarray, owner: np.ndarray,
                      protected: np.ndarray) -> list[tuple[int, int]]:
    if (rgba.shape != p4b5.BACKING or rgba.dtype != np.uint8
            or owner.shape != p4b5.SHAPE or protected.shape != p4b5.SHAPE
            or owner.dtype != np.bool_ or protected.dtype != np.bool_):
        raise ValueError("BLOCKED_P4B7_NATIVE_MASK_SHAPE")
    native_sensitive = p4b4.backing(protected & ~owner)
    locations = np.argwhere((rgba[:, :, 3] >= ALPHA_GATE) & native_sensitive)
    return [(int(y), int(x)) for y, x in locations]


def pixel_alpha(rgba: np.ndarray, targets: list[tuple[int, int]]) -> list[int]:
    if rgba.shape != p4b5.BACKING or rgba.dtype != np.uint8 or not targets:
        raise ValueError("BLOCKED_P4B7_BAD_NATIVE_PIXEL_LIST")
    if any(y < 0 or x < 0 or y >= 720 or x >= 1380 for y, x in targets):
        raise ValueError("BLOCKED_P4B7_PIXEL_OUTSIDE_BACKING")
    return [int(rgba[y, x, 3]) for y, x in targets]


def split_trace(count: int, full_alpha: list[int], draw, cap: int):
    """Pure deterministic bisection; draw is real-Egret callback in run().

    Alpha>0 selects *possible contributors*, not necessarily causal strokes
    at alpha24. An unexplained parent pixel fails closed as partial, not PASS.
    """
    if (type(count) is not int or count < 2 or type(cap) is not int or cap < 2
            or not isinstance(full_alpha, list) or not full_alpha
            or any(type(a) is not int or not 0 <= a <= 255 for a in full_alpha)
            or not all(a >= ALPHA_GATE for a in full_alpha)):
        raise ValueError("BLOCKED_P4B7_SPLIT_INPUT")
    queue = [(tuple(range(count)), list(full_alpha), "R")]
    ledger, leaves = [], {}
    calls = 0
    while queue:
        indices, parent_alpha, path = queue.pop(0)
        if len(indices) == 1:
            leaves[indices[0]] = parent_alpha
            continue
        if calls + 2 > cap:
            return {"status": "PARTIAL_NATIVE_SPLIT_LIMIT", "calls": calls,
                    "ledger": ledger, "leaves": leaves, "remaining": len(queue)+1}
        middle = len(indices)//2
        chunks = (indices[:middle], indices[middle:])
        child = []
        for part, side in zip(chunks, ("L", "R")):
            a = draw(part, "SPLIT_%03d_%s" % (calls, side))
            if (not isinstance(a, list) or len(a) != len(full_alpha)
                    or any(type(v) is not int or not 0 <= v <= 255 for v in a)):
                raise ValueError("BLOCKED_P4B7_BAD_NATIVE_ALPHA_VECTOR")
            ledger.append({"path": path+side, "original_indices": list(part),
                           "target_alpha1_to255": a,
                           "native_replay_index": calls})
            child.append((part, a, path+side))
            calls += 1
        if any(parent_alpha[j] > 0 and
               child[0][1][j] == 0 and child[1][1][j] == 0
               for j in range(len(full_alpha))):
            return {"status": "PARTIAL_NONADDITIVE_NATIVE_ALPHA",
                    "calls": calls, "ledger": ledger, "leaves": leaves,
                    "remaining": len(queue)+1}
        for item in child:
            if any(x > 0 for x in item[1]):
                queue.append(item)
    return {"status": "ATTRIBUTION_LEAVES_COMPLETE", "calls": calls,
            "ledger": ledger, "leaves": leaves, "remaining": 0}


def necessary_pixels(original_alpha: list[int], without_alpha: list[int]):
    if (len(original_alpha) != len(without_alpha) or not original_alpha
            or any(type(a) is not int or not 0 <= a <= 255
                   for a in original_alpha + without_alpha)):
        raise ValueError("BLOCKED_P4B7_LOO_VECTOR")
    return [i for i, (before, after) in enumerate(
        zip(original_alpha, without_alpha))
        if before >= ALPHA_GATE and after < ALPHA_GATE]


def run(workspace: Path, source: Path, engine_js: Path, renderer: Path,
        output: Path) -> dict:
    if output.exists():
        raise ValueError("BLOCKED_P4B7_OUTPUT_EXISTS")
    check_source(source)
    if (p4b4.git_blob(Path(p4b6.__file__).read_bytes()) != FROZEN_P4B6_BLOB
            or p4b4.git_blob(renderer.read_bytes()) != RENDERER_BLOB):
        raise ValueError("BLOCKED_P4B7_PARENT_BLOB_DRIFT")
    output.mkdir(parents=True)
    outcome = {}
    with tempfile.TemporaryDirectory(prefix="engine001-p4b7-original-") as tmp:
        parent_dir = Path(tmp)/"P4B6_same_run"
        parent = p4b6.run(workspace, source, engine_js, renderer, parent_dir)
        if (parent["experiment"] != p4b6.EXPERIMENT
                or parent["result"] != "NATIVE_GUARDS_QUALITY_NOT_ALL_PASS"
                or parent["original_source_SHA256"] != SOURCE_SHA
                or parent["legacy_G32_P4c1_V44_used"]
                or parent["frozen_P4B5_ZIP_used_as_candidate"]
                or set(parent["methods"]) != set(METHODS)):
            raise ValueError("BLOCKED_P4B7_PARENT_PROVENANCE_DRIFT")
        protected = p4b4.source_critical_rois()
        for method in METHODS:
            info = parent["methods"][method]["arms"][ARM]
            if (info["native_quality_pass"]
                    or info["total_strokes"] != EXPECTED_STROKES[method]
                    or info["native_final_alpha"]["24"][
                        "native_protected_foreign_face_eyes_hands_pixels"] != EXPECTED_TARGETS):
                raise ValueError("BLOCKED_P4B7_FROZEN_NATIVE_DRIFT")
            data = json.loads((parent_dir/
                (method+"_"+ARM+"_FINAL_STROKES.json")).read_text("utf8"))
            if (len(data) != EXPECTED_STROKES[method]
                    or len({s["strokeId"] for s in data}) != len(data)
                    or sum(len(s["points"]) for s in data) > p4b6.MAX_VERTICES):
                raise ValueError("BLOCKED_P4B7_CHANGED_FINAL_STROKES")
            index = np.asarray(Image.open(parent_dir/
                (method+"_SOURCE_ENGINE_INDICES.png")), np.uint8)
            if index.shape != p4b5.SHAPE:
                raise ValueError("BLOCKED_P4B7_OWNER_MAP_SHAPE")
            owner = index == p4b6.OWNER
            full_filename = ("P4B5-"+ARM+"_FINAL_REPAIRED-"+
                             method+"-color-115.png")
            full = np.asarray(Image.open(
                parent_dir/("NATIVE_"+ARM+"_FINAL_REPAIRED_"+method)/
                full_filename).convert("RGBA"), np.uint8)
            targets = protected_targets(full, owner, protected)
            if len(targets) != EXPECTED_TARGETS:
                raise ValueError("BLOCKED_P4B7_NATIVE_TARGET_DRIFT")
            original_alpha = pixel_alpha(full, targets)
            if any(a < ALPHA_GATE for a in original_alpha):
                raise ValueError("BLOCKED_P4B7_FULL_ALPHA_DRIFT")

            with native_egret_session(workspace) as driver:
                full_control = native_replay_in_session(
                    driver,output,method,"FULL_REPLAY_CONTROL",
                    normalized_subset(data,tuple(range(len(data)))))
                if not np.array_equal(full_control[:, :, 3],full[:, :, 3]):
                    raise ValueError("BLOCKED_P4B7_NATIVE_SESSION_MISMATCH")
                print("P4B7_NATIVE_FULL_CONTROL_PASS",method,
                      "original_target_alpha",original_alpha,flush=True)
                # Every subset is still rendered afresh by the pinned real
                # Egret BoardPane method; only Firefox process startup is reused.
                # A real full-plan control must match frozen P4B6 native alpha.
                draw_counter = [0]
                progress_path = output/(method+"_PROGRESS.json")
                def draw(indices, stage):
                    rgb = native_replay_in_session(
                        driver, output, method, stage,
                        normalized_subset(data, indices))
                    draw_counter[0] += 1
                    alpha = pixel_alpha(rgb, targets)
                    print("P4B7_NATIVE_PROGRESS", method, "scene",draw_counter[0],
                          "stage",stage,"subset",len(indices),
                          "target_alpha",alpha, flush=True)
                    progress_path.write_text(json.dumps({
                        "experiment":EXPERIMENT, "method":method, "stage":stage,
                        "scene_number":draw_counter[0], "subset_size":len(indices),
                        "target_alpha":alpha, "status":"NATIVE_IN_PROGRESS",
                    }, ensure_ascii=False, indent=2)+"\n", "utf8")
                    return alpha

                trace = split_trace(len(data), original_alpha,
                                    draw, MAX_SPLIT_REPLAYS)
                candidates = sorted(trace["leaves"])
                record = {"source_method": method, "arm": ARM,
                          "native_original_target_backing_yx":
                              [list(x) for x in targets],
                          "native_original_target_alpha": original_alpha,
                          "target_source_logical_xy":
                              [[x//3-155, y//3] for y,x in targets],
                          "full_native_protected_pixels": len(targets),
                          "total_frozen_final_strokes": len(data),
                          "split_native_replays": trace["calls"],
                          "split_status": trace["status"],
                          "split_ledger": trace["ledger"],
                          "nonzero_native_contributor_indices": candidates,
                          "nonzero_native_contributor_original_stroke_ids":
                              [data[i]["strokeId"] for i in candidates],
                          "nonzero_native_contributor_per_pixel_raw_alpha":
                              {str(i): trace["leaves"][i] for i in candidates},
                          "leave_one_out": [],
                          "native_replay_blank_zero": True}
                if trace["status"] == "ATTRIBUTION_LEAVES_COMPLETE":
                    if len(candidates) > MAX_LOO_REPLAYS or not candidates:
                        record["attribution_status"] = "PARTIAL_NATIVE_LOO_LIMIT_OR_NO_LEAF"
                    else:
                        for i in candidates:
                            remaining = tuple(k for k in range(len(data)) if k != i)
                            alpha = draw(remaining, "LOO_%03d" % i)
                            loss = necessary_pixels(original_alpha, alpha)
                            record["leave_one_out"].append({
                                "removed_original_index": i,
                                "removed_original_stroke_id": data[i]["strokeId"],
                                "native_without_target_alpha": alpha,
                                "individually_necessary_target_pixel_indices": loss})
                        record["attribution_status"] = (
                            "ATTRIBUTION_COMPLETE_NATIVE_POSSIBLE_AND_NECESSARY")
                else:
                    record["attribution_status"] = trace["status"]
                record["additional_native_loo_replays"] = (
                    draw_counter[0] - trace["calls"])
                record["total_additional_real_native_replays"] = draw_counter[0]
                (output/(method+"_ATTRIBUTION.json")).write_text(
                    json.dumps(record, indent=2, ensure_ascii=False)+"\n", "utf8")
                outcome[method] = record
            print("P4B7_NATIVE",method,record["attribution_status"],
                  "targets",targets, "candidates",candidates,
                  "group_scenes",trace["calls"], "loo",len(record["leave_one_out"]),
                  flush=True)
        shutil.copytree(parent_dir, output/"P4B6_FRESH_SAME_RUN_EVIDENCE")
    hashes = {str(p.relative_to(output)).replace("\\","/"): digest(p.read_bytes())
              for p in sorted(output.rglob("*")) if p.is_file()}
    result = ("NATIVE_ATTRIBUTION_COMPLETE"
              if all(v["attribution_status"] ==
                     "ATTRIBUTION_COMPLETE_NATIVE_POSSIBLE_AND_NECESSARY"
                     for v in outcome.values()) else "NATIVE_ATTRIBUTION_PARTIAL")
    report = {"experiment": EXPERIMENT, "result": result,
              "E3_true_native_Egret": True,
              "p4b6_fresh_recomputed_from_original": True,
              "source_sha256": SOURCE_SHA, "parent_runner_git_blob": FROZEN_P4B6_BLOB,
              "renderer_git_blob": RENDERER_BLOB, "source_key": p4b6.SOURCE,
              "source_owner_index": 115, "methods": outcome,
              "frozen_coverage_gate": .99, "frozen_protected_foreign_gate": 0,
              "frozen_spill_gate_logical": 3.0,
              "max_strokes": 250, "max_synthetic_vertices_NOT_CHALK": 500,
              "old_G32_P4c1_V44_used": False, "production_promotion": False,
              "native_quality_pass_claim": False, "E4_runtime": "NOT_RUN",
              "E5_independent": "NOT_RUN", "exact_CHALK": None,
              "github_sha": os.environ.get("GITHUB_SHA"),
              "github_run_id": os.environ.get("GITHUB_RUN_ID"),
              "file_sha256": hashes}
    (output/"report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)+"\n",
        encoding="utf8")
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True, type=Path)
    ap.add_argument("--source", required=True, type=Path)
    ap.add_argument("--engine-js", required=True, type=Path)
    ap.add_argument("--renderer", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    try:
        result = run(args.workspace, args.source, args.engine_js,
                     args.renderer, args.output)
        print("P4B7_RESULT", result["result"], "NO_E4_OR_EXACT_CHALK")
    except Exception as exc:
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output/"FAILED_EVIDENCE.json").write_text(
            json.dumps({"experiment": EXPERIMENT, "status": "BLOCKED",
                        "reason": str(exc), "error_type": type(exc).__name__,
                        "github_sha": os.environ.get("GITHUB_SHA"),
                        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
                        "native_quality_not_established": True,
                        "exact_CHALK": None}, indent=2)+"\n", "utf8")
        raise

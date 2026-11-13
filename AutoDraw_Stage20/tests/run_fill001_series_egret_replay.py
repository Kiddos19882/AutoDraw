#!/usr/bin/env python3
"""FILL001_SERIES_EGRET_REPLAY_V1: six frozen live PNGs versus real Egret Stage WebGL.

Read-only to frozen source. Exact CHALK is a game counter delta, never simulated.
For two Monitor runs with point_delta=2, one accepted coordinate is absent;
the resulting replay is diagnostic and must not be labelled pixel-exact.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
import subprocess
from pathlib import Path, PureWindowsPath
import threading
import traceback
from urllib.parse import quote

import numpy as np
from PIL import Image
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait

SERIES = "fill001-series-3e1fd32c4d99"
SESSION = "e04234bc-b9ee-4d06-bd20-f1e13b8423ba"
BASE = Path("AutoDraw_Stage20/data/results/brush_behavior_tests/fill001/series")
MONITOR_BASE = Path("AutoDraw_Stage20/data/results/brush_behavior_tests/game_monitor_bridge") / SESSION
# Authoritative source commit: 3f67c05d8dfd2f4db8954063850bd67b96232dd1.
# Pinned Git blob SHAs for the original unmodified Monitor JSON.
CASES = (
    ("c001-f001", "623be5e5e730fb009ee49afe2267d7de8d826a78"),
    ("c001-f002", "93771f49728c54b33a303dab68377e9df4f418a1"),
    ("c001-f003", "3b939c4454f986c1954f192e75f5438939d11643"),
    ("c002-f001", "5ef05dcfeded397df3f55ab7dcdb88ea560e7b8c"),
    ("c002-f002", "f1bdbbac9a13a8f3d3a14309c6856dfeead8262f"),
    ("c002-f003", "4d7959ba62479439eaa83f44c51e2a1008f1eabb"),
)


def git_blob_sha(raw: bytes) -> str:
    prefix = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(prefix + raw).hexdigest()


def validate_case(workspace: Path, figure: str, expected_blob: str) -> dict:
    folder = workspace / BASE / f"{SERIES}-runs"
    item = json.loads((folder / f"{SERIES}-{figure}.json").read_text(encoding="utf-8"))
    if item["series_id"] != SERIES or item["task_id"] != f"{SERIES}-{figure}":
        raise ValueError(f"{figure}: series/task binding mismatch")
    stage_dirs = list((folder / "stage6").glob("series-*/report.json"))
    candidates = []
    for report_path in stage_dirs:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("task_id") == item["task_id"]:
            candidates.append((report_path, report))
    if len(candidates) != 1:
        raise ValueError(f"{figure}: expected one Stage6 report; got {len(candidates)}")
    report_path, report = candidates[0]
    binding = report.get("binding", {})
    if binding.get("status") != "EXACT_RUN_BOUND" or binding.get("session_id") != SESSION:
        raise ValueError(f"{figure}: invalid Stage6 game run binding")
    raw_names = binding.get("bridge_run_paths") or []
    if len(raw_names) != 1:
        raise ValueError(f"{figure}: expected one pinned Monitor run")
    monitor_path = workspace / MONITOR_BASE / PureWindowsPath(raw_names[0]).name
    # Read exact Git object at checkout HEAD, avoiding Windows CRLF filters;
    # the pinned expected blob SHA guarantees identical original source bytes.
    relative_monitor = monitor_path.relative_to(workspace).as_posix()
    raw = subprocess.run(
        ["git", "show", f"HEAD:{relative_monitor}"],
        cwd=workspace, check=True, capture_output=True,
    ).stdout
    sha = git_blob_sha(raw)
    if sha != expected_blob:
        raise ValueError(f"{figure}: frozen Git blob SHA mismatch {sha}")
    monitor = json.loads(raw)
    run_id = monitor.get("run_id")
    if (monitor.get("session_id") != SESSION or binding.get("run_ids") != [run_id]
            or item.get("runtime", {}).get("run_id") != run_id):
        raise ValueError(f"{figure}: Monitor run ID/session mismatch")
    before, after = monitor.get("pre_test_snapshot", {}), monitor.get("post_test_snapshot", {})
    chalk = after.get("pointCount", -1) - before.get("pointCount", -1)
    if (chalk != item.get("actual_chalk") or chalk != binding.get("exact_chalk")
            or monitor.get("point_delta_matches_chalk") is not True
            or sum(p["point_delta"] for p in monitor.get("accepted_points", [])) != chalk):
        raise ValueError(f"{figure}: game counter / accepted-point delta mismatch")
    if (monitor.get("dropped_events") != 0
            or monitor.get("bridge_send_failures_delta") != 0
            or monitor.get("collector_sequence_gap_count") != 0
            or monitor.get("monitor_error_count_delta") != 0):
        raise ValueError(f"{figure}: recorder or Bridge loss")
    source = report_path.parent
    before_path = source / "before.png"
    after_path = source / "after_settled.png"
    before_png, after_png = before_path.read_bytes(), after_path.read_bytes()
    for name, raw_png in (("before_png", before_png), ("after_settled_png", after_png)):
        expected = report.get(name, {}).get("sha256")
        if expected is None or hashlib.sha256(raw_png).hexdigest() != expected:
            raise ValueError(f"{figure}: {name} SHA256 mismatch")
    mapping = report.get("request", {}).get("mapping", {})
    roi = report.get("request", {}).get("screen_roi", {})
    corners = mapping.get("board_screen_corners", {})
    if (mapping.get("session_id") != SESSION or
            not all(isinstance(roi.get(k), int) for k in ("x", "y", "width", "height")) or
            not all(isinstance(corners.get(k), (int, float))
                    for k in ("left", "right", "top", "bottom"))):
        raise ValueError(f"{figure}: unverified native screen geometry")
    if roi["width"] != 694 or roi["height"] != 363:
        raise ValueError(f"{figure}: unrecognized frozen ROI")
    return {
        "figure": figure, "monitor_sha": sha, "monitor_path": str(monitor_path.relative_to(workspace)),
        "run_id": run_id, "exact_chalk": chalk, "observed_points": len(monitor["accepted_points"]),
        "missing_points": chalk - len(monitor["accepted_points"]),
        "strokes": monitor["stroke_count"], "stage6_report": report,
        "before_png": before_png, "after_png": after_png, "source": source,
        "roi": roi, "screen_corners": corners,
    }



def audit_aggregated_points(workspace: Path) -> dict:
    """Bounded, read-only E1 inventory; no coordinate inference or raw event export."""
    cases = []
    for figure, blob in CASES:
        if figure not in ("c001-f003", "c002-f002"):
            continue
        validated = validate_case(workspace, figure, blob)
        path = workspace / validated["monitor_path"]
        relative = path.relative_to(workspace).as_posix()
        raw = subprocess.run(
            ["git", "show", f"HEAD:{relative}"],
            cwd=workspace, check=True, capture_output=True,
        ).stdout
        if git_blob_sha(raw) != blob:
            raise ValueError(f"{figure}: pinned blob changed")
        run = json.loads(raw)
        accepted = run["accepted_points"]
        events = [e for e in run["events"]
                  if e.get("type") == "DRAW_SAMPLE" and int(e.get("pointDelta") or 0) > 0]
        if len(events) != len(accepted):
            raise ValueError(f"{figure}: accepted/event length mismatch")
        gaps = []
        for index, (point, event) in enumerate(zip(accepted, events)):
            delta = int(point["point_delta"])
            if delta <= 1:
                continue
            if delta != int(event.get("pointDelta") or 0):
                raise ValueError(f"{figure}: aggregated delta mismatch")
            # Only describe field availability, not speculative reconstructed points.
            candidate_keys = sorted(k for k in event if any(
                word in k.lower() for word in ("point", "coord", "path", "sample", "position")))
            # Inspect bounded metadata from independent event categories, not
            # inferred coordinates. Keep payload values out of the report.
            event_time = event.get("t")
            near = [e for e in run["events"]
                    if e is not event and isinstance(e, dict)
                    and isinstance(e.get("t"), (int, float))
                    and isinstance(event_time, (int, float))
                    and abs(e["t"] - event_time) <= 100]
            nearby_types = sorted({str(e.get("type")) for e in near})[:24]
            nearby_candidate_fields = sorted({
                str(k) for e in near for k in e
                if any(w in str(k).lower() for w in
                       ("point", "coord", "pointer", "mouse", "position", "sample"))
            })[:24]
            # Small, source-faithful pointer/frame payload witness. Values are
            # observational only; never label them as accepted game points.
            witness_types = {"POINTER_DOWN_CANDIDATE", "MOUSE_MOVE_SAMPLE",
                             "ENGINE_FRAME_SAMPLE", "POINT_QUOTA_UPDATE"}
            witnesses = []
            ordered = sorted(
                (e for e in near if e.get("type") in witness_types),
                key=lambda e: (abs(e["t"] - event_time), str(e.get("type"))),
            )
            for witness in ordered[:12]:
                coordinates = {}
                for key in ("x", "y", "clientX", "clientY", "offsetX", "offsetY",
                            "logicalX", "logicalY", "screenX", "screenY"):
                    value = witness.get(key)
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        coordinates[key] = value
                for key in ("acceptedPoint", "pointer", "position", "mouse"):
                    value = witness.get(key)
                    if isinstance(value, dict):
                        subset = {k: value[k] for k in
                                  ("x", "y", "clientX", "clientY", "logicalX", "logicalY")
                                  if isinstance(value.get(k), (int, float))
                                  and not isinstance(value.get(k), bool)}
                        if subset:
                            coordinates[key] = subset
                witnesses.append({
                    "type": witness.get("type"),
                    "delta_t": witness["t"] - event_time,
                    "stroke_id": witness.get("strokeId"),
                    "coordinate_values": coordinates,
                })
            report = validated["stage6_report"]
            stage_request = report.get("request") or {}
            stage_binding = report.get("binding") or {}
            gaps.append({
                "accepted_index": index, "point_delta": delta,
                "stroke_id": point.get("stroke_id"),
                "event_candidate_fields": candidate_keys[:16],
                "accepted_fields": sorted(point.keys())[:16],
                "previous_same_stroke": index > 0 and accepted[index-1].get("stroke_id") == point.get("stroke_id"),
                "next_same_stroke": index+1 < len(accepted) and accepted[index+1].get("stroke_id") == point.get("stroke_id"),
                "missing_coordinate_count": delta-1,
                "nearby_event_types_100ms": nearby_types,
                "nearest_first_party_witnesses": witnesses,
                "nearby_coordinate_field_names_100ms": nearby_candidate_fields,
                "stage6_request_top_level_keys": sorted(stage_request.keys())[:32],
                "stage6_binding_top_level_keys": sorted(stage_binding.keys())[:32],
                "recovery_status": "NOT_ESTABLISHED",
            })
        if sum(g["missing_coordinate_count"] for g in gaps) != validated["missing_points"]:
            raise ValueError(f"{figure}: gap accounting mismatch")
        cases.append({
            "figure": figure, "monitor_blob_sha": blob,
            "run_id": validated["run_id"], "exact_chalk": validated["exact_chalk"],
            "missing_points": validated["missing_points"], "gaps": gaps,
            "status": "DIAGNOSTIC_ONLY",
        })
    return {
        "schema": "ENGINE001_AGGREGATED_POINT_INVENTORY_V1",
        "source_commit": "3f67c05d8dfd2f4db8954063850bd67b96232dd1",
        "scope": "Monitor accepted/event field inventory, bounded pointer/frame payload witnesses and Stage6 metadata keys; no independent coordinate recovery",
        "status": "E1_INVENTORY_ONLY", "cases": cases,
    }


def project_stage_rgba(stage: Image.Image, native_profile: dict, screen: dict, roi: dict) -> Image.Image:
    """Pre-declared Stage→verified desktop-ROI affine, no post-hoc alignment."""
    placement = native_profile["stage_placement"]
    corners = screen
    sx = (corners["right"] - corners["left"]) / 460.0
    sy = (corners["bottom"] - corners["top"]) / 240.0
    if sx <= 0 or sy <= 0:
        raise ValueError("Non-positive verified projection scale")
    fx = placement["scaleX"] / sx
    fy = placement["scaleY"] / sy
    tx = placement["x"] + (roi["x"] - corners["left"]) * fx
    ty = placement["y"] + (roi["y"] - corners["top"]) * fy
    if not all(np.isfinite(x) for x in (fx, fy, tx, ty)):
        raise ValueError("Non-finite fixed screen projection")
    # Pillow affine maps the output pixel centres to Stage-backing coordinates.
    return stage.convert("RGBA").transform(
        (roi["width"], roi["height"]), Image.Transform.AFFINE,
        (fx, 0.0, tx, 0.0, fy, ty),
        resample=Image.Resampling.BILINEAR
    )


def compare_images(before: bytes, after: bytes, projected: Image.Image, output: Path) -> dict:
    with Image.open(BytesIO(before)) as img:
        b = np.asarray(img.convert("RGB"), dtype=np.int16)
    with Image.open(BytesIO(after)) as img:
        a = np.asarray(img.convert("RGB"), dtype=np.int16)
    if b.shape != a.shape or a.shape[:2] != (projected.height, projected.width):
        raise ValueError("Game/native screen dimensions disagree")
    live = np.max(np.abs(a - b), axis=2) > 24  # Existing DEC-025 RGB24.
    model = np.asarray(projected, dtype=np.uint8)[:, :, 3] >= 24
    tp = int(np.count_nonzero(live & model))
    live_only = int(np.count_nonzero(live & ~model))
    model_only = int(np.count_nonzero(model & ~live))
    union = tp + live_only + model_only
    iou = tp / union if union else None
    precision = tp / (tp + model_only) if tp + model_only else None
    recall = tp / (tp + live_only) if tp + live_only else None
    overlay = np.zeros((projected.height, projected.width, 3), dtype=np.uint8)
    overlay[live & model] = (54, 176, 111)
    overlay[live & ~model] = (235, 79, 76)
    overlay[model & ~live] = (62, 115, 240)
    output.mkdir(parents=True, exist_ok=True)
    Image.fromarray(overlay, "RGB").save(output / "pixel-diff.png")
    projected.save(output / "egret-screen-projected.png")
    return {
        "status": "DIAGNOSTIC_ONLY_NOT_PRODUCTION_ACCEPTANCE",
        "rgb_abs_delta_threshold": 24, "native_alpha_threshold": 24,
        "projection": "verified native BoardPane screen corners; no fitted offset",
        "resampler": "Pillow BILINEAR",
        "live_pixels": int(np.count_nonzero(live)),
        "model_pixels": int(np.count_nonzero(model)),
        "true_positive": tp, "live_only": live_only, "model_only": model_only,
        "iou": iou, "precision": precision, "recall": recall,
        "symmetric_difference_over_live": ((live_only + model_only) / (tp + live_only))
        if tp + live_only else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", type=Path, default=Path("."))
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--validate-only", action="store_true")
    ap.add_argument("--audit-aggregated", action="store_true")
    args = ap.parse_args()
    workspace = args.workspace.resolve()
    destination = args.output_dir.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    if args.audit_aggregated:
        audit = audit_aggregated_points(workspace)
        (destination / "aggregated-point-inventory.json").write_text(
            json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("ENGINE001_AGGREGATED_POINT_INVENTORY_V1", audit["status"],
              "cases", len(audit["cases"]), flush=True)
        return 0
    results = {"schema": "FILL001_SERIES_EGRET_COMPARISON_V1", "series_id": SERIES,
               "source_commit": "3f67c05d8dfd2f4db8954063850bd67b96232dd1",
               "status": "NOT_RUN", "cases": []}
    driver = None
    server = None
    try:
        cases = [validate_case(workspace, f, sha) for f, sha in CASES]
        if args.validate_only:
            results["status"] = "SOURCE_VALIDATED_ONLY"
            results["cases"] = [
                {k: v for k, v in case.items()
                 if k in ("figure", "monitor_sha", "run_id", "exact_chalk",
                          "observed_points", "missing_points", "strokes")}
                for case in cases
            ]
            return 0
        class QuietHandler(SimpleHTTPRequestHandler):
            def __init__(self, *a, **kw):
                super().__init__(*a, directory=str(workspace), **kw)
            def log_message(self, fmt, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        opts = Options()
        opts.add_argument("-headless")
        opts.set_preference("webgl.disabled", False)
        opts.set_preference("webgl.force-enabled", True)
        opts.set_preference("webgl.disable-fail-if-major-performance-caveat", True)
        opts.set_preference("webgl.min_capability_mode", False)
        opts.set_preference("webgl.enable-webgl2", True)
        opts.set_preference("webgl.msaa-force", True)
        driver = webdriver.Firefox(options=opts)
        driver.set_page_load_timeout(180)
        base = f"http://127.0.0.1:{server.server_port}/AutoDraw_Stage20/tests/game_renderer_reference.html"
        results["browser"] = driver.capabilities.get("browserVersion")
        for case in cases:
            fig = case["figure"]
            single = {k: case[k] for k in
                      ("figure", "monitor_sha", "run_id", "exact_chalk",
                       "observed_points", "missing_points", "strokes")}
            results["cases"].append(single)
            driver.get(base + "?fill001series=3e1fd32c4d99&figure=" + quote(fig))
            WebDriverWait(driver, 240, poll_frequency=0.5).until(
                lambda d: d.execute_script(
                    "return document.body.dataset.seriesStatus") in ("complete", "error")
            )
            if driver.execute_script("return document.body.dataset.seriesStatus") != "complete":
                raise RuntimeError(f"{fig}: " + driver.find_element("id", "renderer-status").text)
            manifest = json.loads(driver.find_element("id", "renderer-manifest-json").get_property("textContent"))
            if (manifest.get("figure") != fig or manifest.get("run_id") != case["run_id"] or
                    manifest.get("exact_historical_chalk") != case["exact_chalk"] or
                    manifest.get("observed_coordinate_count") != case["observed_points"] or
                    manifest.get("missing_coordinate_count") != case["missing_points"]):
                raise ValueError(f"{fig}: browser replay provenance mismatch")
            png_url = driver.execute_script(
                "return document.querySelector('a[download$=\"stage-webgl.png\"]').href"
            )
            if not png_url.startswith("data:image/png;base64,"):
                raise RuntimeError(f"{fig}: native Stage image missing")
            stage = Image.open(BytesIO(base64.b64decode(png_url.partition(",")[2], validate=True)))
            projected = project_stage_rgba(stage, manifest, case["screen_corners"], case["roi"])
            folder = destination / fig
            folder.mkdir(parents=True, exist_ok=True)
            # Preserve byte-identical game screenshots alongside the model PNGs
            # for independent pixel audits and visual review of each frozen run.
            (folder / "game-before.png").write_bytes(case["before_png"])
            (folder / "game-after.png").write_bytes(case["after_png"])
            (folder / "native-stage-webgl.png").write_bytes(
                base64.b64decode(png_url.partition(",")[2], validate=True))
            scores = compare_images(case["before_png"], case["after_png"], projected, folder)
            single.update({"status": "DIAGNOSTIC_MISSING_COORDINATE" if case["missing_points"]
                           else "ACCEPTED_COORDINATES_COMPLETE",
                           "manifest": manifest, "comparison": scores,
                           "native_stage_sha256": hashlib.sha256(
                               (folder / "native-stage-webgl.png").read_bytes()).hexdigest()})
            (folder / "result.json").write_text(
                json.dumps(single, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"{fig}: CHALK={case['exact_chalk']} missing={case['missing_points']} "
                  f"IoU={scores['iou']:.6f} live-only={scores['live_only']} model-only={scores['model_only']}",
                  flush=True)
        results["status"] = "COMPLETED_DIAGNOSTIC_ONLY"
        return 0
    except Exception as exc:
        results["status"] = "BLOCKED"
        results["error"] = str(exc)
        results["traceback"] = traceback.format_exc()
        raise
    finally:
        (destination / "summary.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if driver is not None:
            driver.quit()
        if server is not None:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())

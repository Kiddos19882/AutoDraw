#!/usr/bin/env python3
"""ENGINE001_TWO_ICON_PREDICTIVE_CONTOUR_V1: preregistered experimental planner.

Contours are chosen for predicted gaps BEFORE native WebGL rendering. The
original pinned two-icon mask, quality limits and baseline remain immutable.
No actual game CHALK or live engine fidelity is inferred from this experiment.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
from pathlib import Path
import threading

import cv2
import numpy as np
from PIL import Image
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from run_engine001_two_icon_mask_probe import (
    ALPHA_THRESHOLD, HEIGHT, WIDTH, compare, composite_mask, plan_strokes, safe_interior
)

SCALE = 3
PREVIEW_STROKE_DIAMETER = 6
APPROX_EPSILON = 0.75
MIN_CONTOUR_LENGTH = 24.0
MIN_CONTOUR_NEW_PIXELS = 24
MAX_CONTOURS = 32
MIN_FILL_LENGTH = 8.0
MAX_ENDPOINT_TRIM = 4
CANDIDATE_SEGMENT_LENGTH = 90.0
EXPECTED_BASELINE = {
    "strokes": 380,
    "target_pixels": 157554,
    "iou": 0.9191568600129207,
    "coverage": 0.9210937202482958,
    "outside_target_pixels": 332,
}


def stroke_length(stroke: dict) -> float:
    pts = stroke["points"]
    return float(sum(np.hypot(a["x"]-b["x"], a["y"]-b["y"])
                     for a, b in zip(pts, pts[1:])))


def footprint(points: list[dict], shape: tuple[int, int]) -> np.ndarray:
    """Fixed preview only; do not confuse with true Egret WebGL rendering."""
    if len(points) < 2:
        raise ValueError("Contour/scanline requires >=2 points")
    xy = np.array([[round(p["x"]*SCALE), round(p["y"]*SCALE)]
                   for p in points], dtype=np.int32)
    pixels = np.zeros(shape, dtype=np.uint8)
    cv2.polylines(pixels, [xy], False, 255, PREVIEW_STROKE_DIAMETER, cv2.LINE_8)
    return pixels != 0


def proxy_union(strokes: list[dict], shape: tuple[int, int]) -> np.ndarray:
    canvas = np.zeros(shape, dtype=bool)
    for stroke in strokes:
        canvas |= footprint(stroke["points"], shape)
    return canvas


def contour_candidates(mask: np.ndarray) -> list[dict]:
    eroded = safe_interior(mask).astype(np.uint8)*255
    # Contours are anchored inside target, not offset outside the icon.
    contours, _ = cv2.findContours(eroded, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    result = []
    for contour_index, raw in enumerate(contours):
        if len(raw) < 3:
            continue
        approx = cv2.approxPolyDP(raw, APPROX_EPSILON, True)[:, 0, :]
        if len(approx) < 3:
            continue
        # Closed long outlines are segmented deterministically to avoid
        # overpainting entire outlines that do not address predicted holes.
        points = np.concatenate((approx, approx[:1]), axis=0)
        segment = [points[0]]
        length = 0.0
        for point in points[1:]:
            previous = segment[-1]
            step = float(np.hypot(*(point-previous)))
            if step <= 0.0:
                continue
            segment.append(point)
            length += step
            if length >= CANDIDATE_SEGMENT_LENGTH:
                if length >= MIN_CONTOUR_LENGTH:
                    result.append({"source_contour": contour_index,
                                   "points": [{"x": float(x)+0.5, "y": float(y)+0.5}
                                              for x, y in segment],
                                   "length": length})
                segment = [point]
                length = 0.0
        if length >= MIN_CONTOUR_LENGTH and len(segment) >= 2:
            result.append({"source_contour": contour_index,
                           "points": [{"x": float(x)+0.5, "y": float(y)+0.5}
                                      for x, y in segment],
                           "length": length})
    return result


def plan_joint(mask: np.ndarray) -> tuple[list[dict], dict, dict[str, np.ndarray]]:
    if mask.shape != (HEIGHT, WIDTH) or mask.dtype != np.dtype(bool):
        raise ValueError("Only pinned 460x240 binary target can be planned")
    base = plan_strokes(mask)
    target = np.repeat(np.repeat(mask, SCALE, axis=0), SCALE, axis=1)
    preview = proxy_union(base, target.shape)
    missing = target & ~preview
    outlines = []
    considered = []
    candidates = contour_candidates(mask)
    # Candidate scores are evaluated on the SAME preview before any native render.
    for candidate in candidates:
        cov = footprint(candidate["points"], target.shape)
        uncovered = int(np.count_nonzero(cov & missing))
        outside = int(np.count_nonzero(cov & ~target))
        score = uncovered / candidate["length"]
        considered.append({**candidate, "gain_initial": uncovered, "outside": outside,
                           "score_initial": score, "footprint": cov})
    # One deterministic greedy pass; no refitting to native outcomes.
    considered.sort(key=lambda c: (-c["score_initial"], -c["gain_initial"],
                                   c["source_contour"]))
    contour_proxy = np.zeros_like(target)
    decision_log = []
    for candidate in considered:
        if len(outlines) >= MAX_CONTOURS:
            break
        gain = int(np.count_nonzero(candidate["footprint"] & missing &
                                   ~contour_proxy))
        outside_new = int(np.count_nonzero(candidate["footprint"] &
                                          ~target & ~contour_proxy))
        accepted = (candidate["length"] >= MIN_CONTOUR_LENGTH and
                    gain >= MIN_CONTOUR_NEW_PIXELS and outside_new == 0)
        decision_log.append({
            "source_contour": candidate["source_contour"],
            "arc_length": round(candidate["length"], 3),
            "predicted_new_target_pixels": gain, "predicted_new_outside": outside_new,
            "decision": "ACCEPT" if accepted else "REJECT"
        })
        if accepted:
            outlines.append({"points": candidate["points"], "width": 2})
            contour_proxy |= candidate["footprint"]
    joint = []
    kept_fills = 0
    omitted_fills = 0
    endpoint_trim_pixels = 0
    for stroke in base:
        pts = [dict(v) for v in stroke["points"]]
        # Delete a fully redundant row only if the contour predictor already
        # covers all original row footprint pixels that were inside the target.
        original = footprint(pts, target.shape) & target
        if int(np.count_nonzero(original & ~contour_proxy)) == 0:
            omitted_fills += 1
            continue
        if stroke_length(stroke) < MIN_FILL_LENGTH:
            # No new tiny corrective lines; pre-existing short rows are removed
            # rather than silently converting to shorter fragments.
            omitted_fills += 1
            continue
        y_pixel = round(pts[0]["y"]*SCALE)
        original_x0 = pts[0]["x"]
        original_x1 = pts[-1]["x"]
        for _ in range(MAX_ENDPOINT_TRIM):
            if pts[-1]["x"]-pts[0]["x"] <= MIN_FILL_LENGTH+1:
                break
            x_pixel = round(pts[0]["x"]*SCALE)
            if contour_proxy[y_pixel, x_pixel]:
                pts[0]["x"] += 1.0
                endpoint_trim_pixels += 1
            else:
                break
        for _ in range(MAX_ENDPOINT_TRIM):
            if pts[-1]["x"]-pts[0]["x"] <= MIN_FILL_LENGTH+1:
                break
            x_pixel = round(pts[-1]["x"]*SCALE)
            if contour_proxy[y_pixel, x_pixel]:
                pts[-1]["x"] -= 1.0
                endpoint_trim_pixels += 1
            else:
                break
        if pts[0]["x"] < original_x0 or pts[-1]["x"] > original_x1:
            raise ValueError("Joint trimming must never extend a baseline stroke")
        joint.append({"points": pts, "width": 2})
        kept_fills += 1
    # Contours precede fill, so horizontal paths may overlap already painted
    # contours, but do not need to reach the outer silhouette.
    combined = outlines + joint
    for index, stroke in enumerate(combined):
        stroke["strokeId"] = f"icon-{index}"
    if not combined or len(combined) > 2500 or sum(len(s["points"]) for s in combined)>5900:
        raise ValueError("Joint plan exceeds fixed native harness capacity")
    joint_preview = proxy_union(combined, target.shape)
    notes = {
        "algorithm": "predictive_contour_first_then_trim_existing_horizontal_endpoints",
        "baseline_strokes": len(base), "candidate_contours": len(candidates),
        "evaluated_candidates": len(decision_log), "accepted_long_contours": len(outlines),
        "retained_horizontal_strokes": kept_fills,
        "omitted_horizontal_strokes": omitted_fills,
        "endpoint_trim_logical_pixels": endpoint_trim_pixels,
        "total_strokes": len(combined),
        "total_synthetic_vertices_not_chalk": sum(len(s["points"]) for s in combined),
        "contour_length_logical": sum(stroke_length(s) for s in outlines),
        "horizontal_length_logical": sum(stroke_length(s) for s in joint),
        "baseline_length_logical": sum(stroke_length(s) for s in base),
        "candidate_decisions": decision_log,
        "proxy_baseline_metrics": compare(target, preview),
        "proxy_joint_metrics": compare(target, joint_preview),
        "fixed_parameters": {
            "preview_scale": SCALE, "preview_LINE_8_diameter": PREVIEW_STROKE_DIAMETER,
            "contour_approx_epsilon_logical": APPROX_EPSILON,
            "min_contour_length_logical": MIN_CONTOUR_LENGTH,
            "min_new_native_proxy_pixels": MIN_CONTOUR_NEW_PIXELS,
            "max_long_contours": MAX_CONTOURS,
            "max_contour_segment_length_logical": CANDIDATE_SEGMENT_LENGTH,
            "min_horizontal_length_logical": MIN_FILL_LENGTH,
            "max_endpoint_trim_logical": MAX_ENDPOINT_TRIM,
        }
    }
    return combined, notes, {
        "target": target, "baseline_preview": preview,
        "missing_forecast": missing, "contour_preview": contour_proxy,
        "combined_preview": joint_preview,
    }


def render_native(strokes: list[dict], workspace: Path) -> dict:
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(workspace), **kw)
        def log_message(self, fmt, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    driver = None
    try:
        options = Options()
        options.add_argument("-headless")
        options.set_preference("webgl.disabled", False)
        options.set_preference("webgl.force-enabled", True)
        options.set_preference("webgl.disable-fail-if-major-performance-caveat", True)
        driver = webdriver.Firefox(options=options)
        driver.set_page_load_timeout(180)
        driver.get(f"http://127.0.0.1:{server.server_port}/"
                   "AutoDraw_Stage20/tests/game_renderer_reference.html?twoicons=home-envelope")
        WebDriverWait(driver, 90).until(
            lambda d: d.execute_script("return document.body.dataset.twoIconStatus") == "ready")
        return driver.execute_script(
            "return window.AutoDrawGameRendererReference.renderTwoIconMaskProbe(arguments[0]);",
            strokes)
    finally:
        if driver is not None:
            driver.quit()
        server.shutdown()
        server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    workspace, output = args.workspace.resolve(), args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    logical, sources = composite_mask(workspace)
    strokes, planning, previews = plan_joint(logical)
    for key, value in previews.items():
        Image.fromarray(value.astype(np.uint8)*255, "L").save(output/f"{key}.png")
    (output/"joint-strokes.json").write_text(
        json.dumps({"experiment_id": "ENGINE001_TWO_ICON_PREDICTIVE_CONTOUR_V1",
                    "strokes": strokes}, indent=2)+"\n", encoding="utf-8")
    result = render_native(strokes, workspace)
    png_url = result.pop("webglPngDataUrl")
    if not png_url.startswith("data:image/png;base64,"):
        raise ValueError("Actual native renderer did not provide PNG")
    raw = base64.b64decode(png_url.partition(",")[2],validate=True)
    (output/"joint-egret-webgl.png").write_bytes(raw)
    with Image.open(BytesIO(raw)) as image:
        pixels = np.asarray(image.convert("RGBA"))
    if pixels.shape != (HEIGHT*SCALE, WIDTH*SCALE, 4):
        raise ValueError("Native Stage output changed geometry")
    native = pixels[:, :, 3] >= ALPHA_THRESHOLD
    metrics = compare(previews["target"], native)
    overlay = np.full((*native.shape, 3), 255, dtype=np.uint8)
    overlay[native & previews["target"]] = (44, 145, 76)
    overlay[~native & previews["target"]] = (230, 80, 70)
    overlay[native & ~previews["target"]] = (65, 95, 205)
    Image.fromarray(overlay, "RGB").save(output/"joint-overlay.png")
    quality_pass = metrics["coverage"] >= .99 and metrics["outside_target_pixels"] == 0
    report = {
        "schema": "ENGINE001_TWO_ICON_PREDICTIVE_CONTOUR_V1",
        "status": "OFFLINE_QUALITY_PASS" if quality_pass else "OFFLINE_QUALITY_FAIL",
        "baseline_frozen": EXPECTED_BASELINE,
        "source": sources,
        "mode": "normal", "brush_radius": 2,
        "target": "same-pinned-460x240-source-mask",
        "native_scale": SCALE, "native_alpha_threshold": ALPHA_THRESHOLD,
        "hypothesis": "predictive long contour arcs plus trimmed horizontal segments reduce gaps without short repairs",
        "native": result, "native_png_sha256": hashlib.sha256(raw).hexdigest(),
        "planning": planning, "native_comparison": metrics,
        "quality": {"coverage_min": .99, "outside_max": 0,
                    "result": "PASS" if quality_pass else "FAIL"},
        "limitations": [
            "No real game CHALK; synthetic planned vertices are not engine pointCount",
            "Pre-render LINE_8 proxy is not native Egret, and any prediction error is reported",
            "No game screenshot, no actual Stage6 execution, no temporal E4 and no independent E5",
            "Contoured partial segments are not automatically production-ready",
            "No parameters selected or corrected using the resulting native PNG",
        ],
    }
    (output/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("ENGINE001_PREDICTIVE_CONTOUR",report["status"],"native IoU",metrics["iou"],
          "coverage",metrics["coverage"],"leakage",metrics["outside_target_pixels"],
          "total strokes",len(strokes),"contours",planning["accepted_long_contours"],flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())

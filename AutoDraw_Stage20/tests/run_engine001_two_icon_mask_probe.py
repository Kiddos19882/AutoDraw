#!/usr/bin/env python3
"""ENGINE001_TWO_ICON_MASK_V1: two pinned repository icons vs native Egret WebGL.

One composed 460x240 board; fixed radius=2 normal strokes from a simple
independent binary mask. Offline synthetic geometry, NOT live accepted points,
NOT exact CHALK, NOT a FILL quality acceptance.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
from pathlib import Path
import subprocess
import threading
import numpy as np
from PIL import Image
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path("AutoDraw_Stage20")
SOURCES = (
    ("home", "free-icon-font-home-3917033.png", "4c1f9c7a6682451d3949c539480e2f7550c5eedf", 50),
    ("envelope", "free-icon-font-envelope-3916611.png", "8d692665927fac8703f3fbc72b7cf437bda9dba2", 250),
)
WIDTH, HEIGHT = 460, 240
ICON_WIDTH = ICON_HEIGHT = 160
ICON_TOP = 40
STROKE_RADIUS = 2
STROKE_ROW_STEP = 2
ALPHA_THRESHOLD = 24  # renderer diagnostic threshold from existing six-figure replay


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()


def source_binary(raw: bytes) -> tuple[np.ndarray, str]:
    """Choose mask by existing transparency; opaque sources use fixed dark foreground."""
    with Image.open(BytesIO(raw)) as im:
        rgba = np.asarray(im.convert("RGBA"))
    alpha = rgba[:, :, 3]
    if alpha.min() != alpha.max():
        source = alpha >= 128
        rule = "source_png_alpha_ge_128"
    else:
        rgb = rgba[:, :, :3].astype(np.float32)
        source = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] +
                  0.114 * rgb[:, :, 2]) < 128
        rule = "opaque_source_luma_lt_128"
    im = Image.fromarray(source.astype(np.uint8) * 255, "L")
    resized = np.asarray(im.resize((ICON_WIDTH, ICON_HEIGHT), Image.Resampling.NEAREST)) >= 128
    if not (250 <= int(resized.sum()) <= 25000):
        raise ValueError("Two-icon source threshold produced an implausible silhouette")
    return resized, rule


def composite_mask(workspace: Path) -> tuple[np.ndarray, list[dict]]:
    mask = np.zeros((HEIGHT, WIDTH), dtype=bool)
    sources = []
    for name, filename, sha, left in SOURCES:
        relative = (ROOT / "testImages" / filename).as_posix()
        raw = subprocess.run(["git", "show", f"HEAD:{relative}"],
                             cwd=workspace, check=True, capture_output=True).stdout
        if git_blob_sha(raw) != sha:
            raise ValueError(f"{name}: pinned source Git blob hash differs")
        part, rule = source_binary(raw)
        region = mask[ICON_TOP:ICON_TOP+ICON_HEIGHT, left:left+ICON_WIDTH]
        if region.any():
            raise ValueError(f"{name}: icon silhouettes overlap")
        region[:] = part
        sources.append({
            "id": name, "path": relative, "git_blob_sha": sha,
            "source_binary_rule": rule, "position": [left, ICON_TOP],
            "size": [ICON_WIDTH, ICON_HEIGHT], "mask_pixels": int(part.sum()),
        })
    return mask, sources


def safe_interior(mask: np.ndarray) -> np.ndarray:
    """Fixed 4-connected one-pixel erosion, no adaptation to observed results."""
    p = np.pad(mask, 1, constant_values=False)
    return mask & p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]


def plan_strokes(mask: np.ndarray) -> list[dict]:
    interior = safe_interior(mask)
    strokes = []
    for y in range(0, HEIGHT, STROKE_ROW_STEP):
        row = np.pad(interior[y], (1, 1), constant_values=False).astype(np.int8)
        start = np.flatnonzero(np.diff(row) == 1)
        stop = np.flatnonzero(np.diff(row) == -1)
        for a, end in zip(start, stop):
            # Native normal path requires two distinct vertices; no single-point guessing.
            if end - a < 2:
                continue
            strokes.append({
                "strokeId": f"icon-{len(strokes)}", "width": STROKE_RADIUS,
                "points": [{"x": float(a) + 0.5, "y": float(y) + 0.5},
                           {"x": float(end - 1) + 0.5, "y": float(y) + 0.5}],
            })
    if not strokes or len(strokes) > 2500 or len(strokes)*2 > 5900:
        raise ValueError(f"Unexpected stroke count: {len(strokes)}")
    return strokes


def compare(target: np.ndarray, native: np.ndarray) -> dict:
    if target.shape != native.shape:
        raise ValueError("Mismatched target/native binary mask dimensions")
    true_positive = int(np.count_nonzero(target & native))
    missing = int(np.count_nonzero(target & ~native))
    leak = int(np.count_nonzero(native & ~target))
    t = true_positive + missing
    p = true_positive + leak
    union = true_positive + missing + leak
    return {
        "target_pixels": t, "rendered_pixels": p,
        "covered_target_pixels": true_positive, "uncovered_target_pixels": missing,
        "outside_target_pixels": leak, "iou": true_positive/union if union else None,
        "coverage": true_positive/t if t else None,
        "precision": true_positive/p if p else None,
        "recall": true_positive/t if t else None,
        "symmetric_difference_pixels": missing + leak,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path("."))
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)

    # Entire target fixed before native rendering; never shift or fit against output.
    logical, sources = composite_mask(workspace)
    strokes = plan_strokes(logical)
    Image.fromarray(logical.astype(np.uint8)*255, "L").save(out/"two-icon-logical-mask.png")
    target = np.repeat(np.repeat(logical, 3, axis=0), 3, axis=1)
    Image.fromarray(target.astype(np.uint8)*255, "L").save(out/"two-icon-target-mask-3x.png")
    (out/"fixed-strokes.json").write_text(
        json.dumps({"schema": "ENGINE001_TWO_ICON_STROKES_V1", "strokes": strokes},
                   ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

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
        url = (f"http://127.0.0.1:{server.server_port}/"
               "AutoDraw_Stage20/tests/game_renderer_reference.html?twoicons=home-envelope")
        driver.get(url)
        WebDriverWait(driver, 90).until(lambda d:
            d.execute_script("return document.body.dataset.twoIconStatus") == "ready")
        result = driver.execute_script(
            "return window.AutoDrawGameRendererReference.renderTwoIconMaskProbe(arguments[0]);",
            strokes)
        png_url = result.pop("webglPngDataUrl")
        if not png_url.startswith("data:image/png;base64,"):
            raise ValueError("Native Egret WebGL PNG not returned")
        raw = base64.b64decode(png_url.partition(",")[2], validate=True)
        native_png = out/"two-icon-egret-webgl.png"
        native_png.write_bytes(raw)
        with Image.open(BytesIO(raw)) as img:
            rgba = np.asarray(img.convert("RGBA"))
        if rgba.shape != (HEIGHT*3, WIDTH*3, 4):
            raise ValueError("Wrong native WebGL output dimensions")
        native = rgba[:, :, 3] >= ALPHA_THRESHOLD
        metrics = compare(target, native)
        overlay = np.full((HEIGHT*3, WIDTH*3, 3), 255, dtype=np.uint8)
        overlay[target & native] = (44, 145, 76)
        overlay[target & ~native] = (230, 80, 70)
        overlay[native & ~target] = (65, 95, 205)
        Image.fromarray(overlay, "RGB").save(out/"two-icon-mask-overlay.png")
        report = {
            "schema": "ENGINE001_TWO_ICON_COMPOSITE_MASK_V1",
            "experiment_id": "ENGINE001_TWO_ICON_HOME_ENVELOPE_V1",
            "status": "OFFLINE_DIAGNOSTIC_ONLY",
            "source": sources,
            "board": {"logical_width": WIDTH, "logical_height": HEIGHT,
                      "native_scale": 3},
            "plan": {"algorithm": "fixed_one_pixel_four_connected_interior_erode_then_horizontal_runs",
                     "stroke_row_step": STROKE_ROW_STEP, "radius": STROKE_RADIUS,
                     "mode": "normal", "stroke_count": len(strokes),
                     "synthetic_vertices_not_chalk": len(strokes)*2},
            "mask": {"target": "PNG silhouette nearest-neighbor at 160x160 per icon",
                     "threshold": "source alpha>=128 if nonopaque else luminance<128",
                     "native_alpha_threshold": ALPHA_THRESHOLD},
            "renderer": result, "comparison": metrics,
            "original_png_shas": {v["id"]: v["git_blob_sha"] for v in sources},
            "native_png_sha256": hashlib.sha256(raw).hexdigest(),
            "limitations": [
                "Offline generated scanline geometry; no live game or observed accepted points",
                "Mask comparison is not a live renderer IoU or DEC-025 formal acceptance",
                "No exact game CHALK is measured or estimated",
                "No tuning after output, no screen-ROI calibration or RGB live capture",
            ],
        }
        (out/"report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n",encoding="utf-8")
        print("ENGINE001_TWO_ICON_MASK", report["status"], "strokes", len(strokes),
              "IoU", metrics["iou"], "coverage", metrics["coverage"],
              "outside", metrics["outside_target_pixels"], flush=True)
    finally:
        if driver is not None:
            driver.quit()
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

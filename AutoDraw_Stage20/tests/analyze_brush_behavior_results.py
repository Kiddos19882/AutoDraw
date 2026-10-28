#!/usr/bin/env python3
"""Measure brush-test screenshots against saved drawing plans.

Requires Pillow: python -m pip install Pillow

The screenshot crop is the visible drawing board (not the whole browser window).
Defaults match the 1919x1079 screenshots collected on 2026-10-28 and the recorded
board profile at x=504, y=280, size 645x328. Override crop coordinates if the
capture uses another display scale, window position, or browser zoom.
Measurements are approximate because screenshots may be scaled by the browser
or display capture; this tool does not prove that the game charged paint.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover - environment-specific
    raise SystemExit(
        "Pillow is required. Install it with: python -m pip install Pillow"
    ) from exc


def load_plan(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        plan = json.load(stream)
    if not isinstance(plan.get("strokes"), list):
        raise ValueError(f"Plan has no strokes list: {path}")
    return plan


def dark_pixels(image: Any, box: tuple[int, int, int, int]) -> list[tuple[int, int]]:
    """Return near-black pixels in a local screenshot box."""
    left, top, right, bottom = box
    left = max(0, left)
    top = max(0, top)
    right = min(image.width, right)
    bottom = min(image.height, bottom)
    found: list[tuple[int, int]] = []
    pixels = image.load()
    for y in range(top, bottom):
        for x in range(left, right):
            pixel = pixels[x, y]
            if isinstance(pixel, int):
                rgb = (pixel, pixel, pixel)
            else:
                rgb = pixel[:3]
            # The ink is black; threshold tolerates antialiasing but excludes
            # the light-gray board and most interface decoration.
            if max(rgb) < 100:
                found.append((x, y))
    return found


def measure_pair(
    plan_path: Path,
    screenshot_path: Path,
    crop: tuple[int, int, int, int],
    threshold: int = 100,
    padding: float = 6.0,
) -> dict[str, Any]:
    plan = load_plan(plan_path)
    with Image.open(screenshot_path) as opened:
        screenshot = opened.convert("RGB")
    crop_x, crop_y, crop_width, crop_height = crop
    if crop_x < 0 or crop_y < 0 or crop_width <= 0 or crop_height <= 0:
        raise ValueError("Crop x/y must be >= 0 and width/height must be > 0")
    if crop_x + crop_width > screenshot.width or crop_y + crop_height > screenshot.height:
        raise ValueError(
            f"Crop {crop} exceeds screenshot {screenshot.width}x{screenshot.height}: "
            f"{screenshot_path}"
        )

    canvas_width = float(plan.get("width") or plan["canvas"]["width"])
    canvas_height = float(plan.get("height") or plan["canvas"]["height"])
    scale_x = crop_width / canvas_width
    scale_y = crop_height / canvas_height
    measurements = []

    # Crop to the board before thresholding so dark game UI cannot be counted.
    board = screenshot.crop((crop_x, crop_y, crop_x + crop_width, crop_y + crop_height))
    board_pixels = board.load()
    for stroke in plan["strokes"]:
        points = stroke.get("points", [])
        if len(points) < 2:
            continue
        xs = [float(point["x"]) for point in points]
        ys = [float(point["y"]) for point in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        # Include a small margin around the expected stroke, but avoid taking
        # the entire board or merging adjacent test strokes.
        x0 = max(0, math.floor((min_x - padding) * scale_x))
        x1 = min(board.width, math.ceil((max_x + padding) * scale_x) + 1)
        y0 = max(0, math.floor((min_y - padding) * scale_y))
        y1 = min(board.height, math.ceil((max_y + padding) * scale_y) + 1)
        coords = []
        for y in range(y0, y1):
            for x in range(x0, x1):
                pixel = board_pixels[x, y]
                if max(pixel[:3]) < threshold:
                    coords.append((x, y))
        if coords:
            bx0 = min(point[0] for point in coords)
            bx1 = max(point[0] for point in coords)
            by0 = min(point[1] for point in coords)
            by1 = max(point[1] for point in coords)
            bbox = {
                "left": bx0 + x0,
                "top": by0 + y0,
                "right": bx1 + x0,
                "bottom": by1 + y0,
                "width_px": bx1 - bx0 + 1,
                "height_px": by1 - by0 + 1,
            }
            bbox["estimated_canvas_width_px"] = round(bbox["width_px"] / scale_x, 2)
            bbox["estimated_canvas_height_px"] = round(bbox["height_px"] / scale_y, 2)
        else:
            bbox = None
        start, end = points[0], points[-1]
        planned_length = math.hypot(
            float(end["x"]) - float(start["x"]),
            float(end["y"]) - float(start["y"]),
        )
        measurements.append({
            "stroke": stroke.get("name", "unnamed"),
            "planned_length_px": round(planned_length, 2),
            "closed": bool(stroke.get("closed", False)),
            "dark_pixel_count": len(coords),
            "detected": bool(coords),
            "detected_bbox_board_px": bbox,
            "note": (
                "Bounding box coordinates are relative to the cropped board; "
                "the ROI may include nearby ink for overlapping strokes or corners."
            ),
        })

    return {
        "schema_version": 1,
        "plan_file": str(plan_path),
        "screenshot_file": str(screenshot_path),
        "screenshot_size": {"width": screenshot.width, "height": screenshot.height},
        "board_crop_screenshot_px": {
            "x": crop_x, "y": crop_y, "width": crop_width, "height": crop_height
        },
        "plan_canvas_size": {"width": canvas_width, "height": canvas_height},
        "screenshot_scale": {"x": round(scale_x, 6), "y": round(scale_y, 6)},
        "threshold_max_rgb": threshold,
        "roi_padding_canvas_px": padding,
        "requested_brush_value": plan.get("generation", {}).get("requested_brush_value"),
        "test_case": plan.get("generation", {}).get("test_case"),
        "measurements": measurements,
        "limitations": [
            "Threshold segmentation is approximate and can merge overlapping strokes.",
            "A detected dark trace does not prove the game registered a stroke or charged paint.",
            "Crop and scale must be verified for each screenshot capture setup.",
        ],
    }


def parse_pair(value: str) -> tuple[Path, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("Pair format must be PLAN.json=SCREENSHOT.png")
    plan, screenshot = value.split("=", 1)
    if not plan or not screenshot:
        raise argparse.ArgumentTypeError("Both plan and screenshot paths are required")
    return Path(plan), Path(screenshot)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pair", action="append", type=parse_pair, required=True,
        help="Plan/screenshot pair; repeat for each pair: PLAN.json=SCREENSHOT.png",
    )
    parser.add_argument("--crop-x", type=int, default=504)
    parser.add_argument("--crop-y", type=int, default=280)
    parser.add_argument("--crop-width", type=int, default=645)
    parser.add_argument("--crop-height", type=int, default=328)
    parser.add_argument("--threshold", type=int, default=100)
    parser.add_argument("--padding", type=float, default=6.0)
    parser.add_argument("--output", type=Path, default=Path("brush_behavior_measurements.json"))
    args = parser.parse_args()
    crop = (args.crop_x, args.crop_y, args.crop_width, args.crop_height)
    results = [
        measure_pair(plan, screenshot, crop, args.threshold, args.padding)
        for plan, screenshot in args.pair
    ]
    output = {"schema_version": 1, "result_count": len(results), "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Analyzed {len(results)} plan/screenshot pair(s).")
    print(f"Measurements saved to: {args.output}")
    for result in results:
        detected = sum(item["detected"] for item in result["measurements"])
        total = len(result["measurements"])
        print(
            f"- brush={result['requested_brush_value']} case={result['test_case']}: "
            f"{detected}/{total} planned strokes have dark pixels in their ROIs"
        )
    print("Reminder: this is image segmentation, not proof of in-game stroke registration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = REPO_ROOT / "AutoDraw_Stage20"
PREPARATION_ROOT = APP_ROOT / "source" / "preparation"
# Compatibility wrappers import the canonical shared pipeline from APP_ROOT.
for import_root in (PREPARATION_ROOT, APP_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from image_processing.pipeline import fit_to_canvas  # noqa: E402


def load_git_image(ref: str, repo_path: str) -> Image.Image:
    result = subprocess.run(
        ["git", "show", f"{ref}:{repo_path}"],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    from io import BytesIO

    return Image.open(BytesIO(result.stdout)).copy()


def fit_to_canvas_nearest(image: Image.Image, target_width: int, target_height: int) -> Image.Image:
    rgb = image.convert("RGB")
    source_width, source_height = rgb.size
    scale = min(target_width / source_width, target_height / source_height)
    resized_width = max(1, min(target_width, round(source_width * scale)))
    resized_height = max(1, min(target_height, round(source_height * scale)))
    resized = rgb.resize((resized_width, resized_height), Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (target_width, target_height), (255, 255, 255))
    offset = ((target_width - resized_width) // 2, (target_height - resized_height) // 2)
    canvas.paste(resized, offset)
    return canvas


def color_stats(image: Image.Image, *, top_count: int = 12) -> dict[str, Any]:
    rgb_image = image.convert("RGB")
    array = np.asarray(rgb_image, dtype=np.uint8)
    flat = array.reshape(-1, 3)
    counts = Counter(map(tuple, flat.tolist()))
    pixel_count = int(flat.shape[0])
    white_count = int(np.count_nonzero(np.all(array == 255, axis=2)))
    near_white_count = int(np.count_nonzero(np.all(array >= 248, axis=2)))
    non_white_mask = np.any(array < 250, axis=2)
    ys, xs = np.where(non_white_mask)
    bbox = None
    if xs.size:
        bbox = {
            "left": int(xs.min()),
            "top": int(ys.min()),
            "right_exclusive": int(xs.max()) + 1,
            "bottom_exclusive": int(ys.max()) + 1,
            "width": int(xs.max()) - int(xs.min()) + 1,
            "height": int(ys.max()) - int(ys.min()) + 1,
        }

    top_colors = []
    for color, count in counts.most_common(top_count):
        top_colors.append({
            "rgb": list(color),
            "hex": "#{:02X}{:02X}{:02X}".format(*color),
            "pixels": int(count),
            "percentage": round(100.0 * count / pixel_count, 4),
        })

    return {
        "size": {"width": rgb_image.width, "height": rgb_image.height},
        "mode_before_rgb_conversion": image.mode,
        "unique_exact_rgb_colors": len(counts),
        "pixel_count": pixel_count,
        "pure_white_pixels": white_count,
        "pure_white_percentage": round(100.0 * white_count / pixel_count, 4),
        "near_white_pixels_rgb_ge_248": near_white_count,
        "near_white_percentage_rgb_ge_248": round(100.0 * near_white_count / pixel_count, 4),
        "non_white_bbox_rgb_lt_250": bbox,
        "most_common_exact_colors": top_colors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect the master test image and compare LANCZOS vs NEAREST contain scaling."
    )
    parser.add_argument("--git-ref", default="origin/master")
    parser.add_argument("--git-path", default="AutoDraw_Stage20/testImages/images.png")
    parser.add_argument("--target-width", type=int, default=646)
    parser.add_argument("--target-height", type=int, default=323)
    parser.add_argument("--fit-mode", choices=("contain", "cover", "stretch"), default="contain")
    args = parser.parse_args()

    if args.target_width <= 0 or args.target_height <= 0:
        parser.error("Target dimensions must be positive.")

    source = load_git_image(args.git_ref, args.git_path)
    lanczos = fit_to_canvas(source, args.target_width, args.target_height, args.fit_mode)
    if args.fit_mode == "contain":
        nearest = fit_to_canvas_nearest(source, args.target_width, args.target_height)
    else:
        nearest = source.convert("RGB").resize(
            (args.target_width, args.target_height), Image.Resampling.NEAREST
        )

    report = {
        "source": {
            "git_ref": args.git_ref,
            "git_path": args.git_path,
            **color_stats(source),
        },
        "target": {
            "size": {"width": args.target_width, "height": args.target_height},
            "fit_mode": args.fit_mode,
            "resampling": {
                "lanczos": color_stats(lanczos),
                "nearest": color_stats(nearest),
            },
        },
        "interpretation": (
            "Exact RGB counts describe source/resampled raster colors, not the number "
            "of colors used after mapping to a specific browser palette. That requires "
            "the actual palette profile used for the conversion."
        ),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

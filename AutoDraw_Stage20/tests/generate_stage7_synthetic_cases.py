from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw


def make_cases(output_dir: Path) -> list[Path]:
    """Create deterministic transparent RGBA inputs for geometry stress benchmarks."""
    output_dir.mkdir(parents=True, exist_ok=True)
    size = (320, 160)
    paths: list[Path] = []

    image = Image.new("RGBA", size, (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 12, 170, 145), fill=(35, 125, 220, 255))
    draw.ellipse((55, 42, 120, 108), fill=(255, 255, 255, 255))
    draw.rectangle((171, 12, 307, 145), fill=(220, 65, 55, 255))
    draw.rectangle((205, 38, 270, 118), fill=(245, 195, 45, 255))
    paths.append(_save(image, output_dir, "broad_regions_hole_and_neighbor.png"))

    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.line((8, 150, 155, 8), fill=(35, 125, 220, 255), width=2)
    draw.line((165, 8, 310, 150), fill=(220, 65, 55, 255), width=3)
    draw.line((8, 80, 310, 80), fill=(245, 195, 45, 255), width=1)
    draw.line((80, 8, 80, 150), fill=(80, 170, 100, 255), width=2)
    paths.append(_save(image, output_dir, "thin_diagonal_and_crossing_lines.png"))

    image = Image.new("RGBA", size, (0, 0, 0, 0))
    pixels = image.load()
    colors = [(35, 125, 220, 255), (220, 65, 55, 255), (245, 195, 45, 255), (80, 170, 100, 255)]
    for y in range(8, 153, 9):
        for x in range(8 + (y // 9 % 3), 313, 11):
            if ((x // 11) + (y // 9)) % 5 != 0:
                pixels[x, y] = colors[((x // 11) + (y // 9)) % len(colors)]
    paths.append(_save(image, output_dir, "isolated_multicolor_pixels.png"))

    image = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    for row in range(4):
        for col in range(8):
            x, y = 8 + col * 39, 8 + row * 37
            color = colors[(row * 3 + col) % len(colors)]
            if (row + col) % 3 == 0:
                draw.ellipse((x, y, x + 20, y + 20), fill=color)
            elif (row + col) % 3 == 1:
                draw.rectangle((x, y, x + 22, y + 22), fill=color)
                draw.rectangle((x + 7, y + 7, x + 15, y + 15), fill=(0, 0, 0, 0))
            else:
                draw.polygon((x, y + 20, x + 12, y, x + 24, y + 20), fill=color)
    paths.append(_save(image, output_dir, "fragmented_components_and_holes.png"))
    return paths


def _save(image: Image.Image, output_dir: Path, filename: str) -> Path:
    path = output_dir / filename
    image.save(path)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    for path in make_cases(args.output_dir):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

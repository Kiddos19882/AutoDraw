from __future__ import annotations

import argparse
import json
from pathlib import Path

from stage7_validator_rules import skeleton_transparency_error


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate synthetic Stage 7 benchmark reports.")
    parser.add_argument("--report-dir", required=True, type=Path)
    args = parser.parse_args()

    reports = sorted(args.report_dir.glob("*-report.json"))
    if len(reports) != 4:
        raise SystemExit(f"Expected 4 synthetic reports, found {len(reports)} in {args.report_dir}")

    for path in reports:
        report = json.loads(path.read_text(encoding="utf-8"))
        source = report.get("source", {})
        width = int(report["configuration"]["target_width"])
        height = int(report["configuration"]["target_height"])
        visible = int(source.get("source_visible_pixel_count", -1))
        total = width * height
        if not 0 < visible < total:
            raise SystemExit(
                f"{path.name}: expected transparency to remain visible in report "
                f"(visible={visible}, canvas={total}); alpha/background handling may have regressed"
            )

        results = report.get("algorithm_results", [])
        by_name = {item.get("name"): item for item in results}
        if not {"contour", "skeleton", "scanline", "interior_fill"} <= by_name.keys():
            raise SystemExit(f"{path.name}: one or more expected algorithms are missing")
        # A measured, deliberately tiny tolerance is allowed only for the
        # experimental skeleton centerline: at most three isolated pixels per
        # image, no more than one per stroke. This is an offline rasterizer
        # tolerance, not proof that a real browser brush is harmless.
        max_skeleton_transparent_pixels = 3
        for name, item in by_name.items():
            transparent_count = int(item.get("painted_transparent_pixel_count", -1))
            if name != "skeleton":
                if transparent_count != 0:
                    raise SystemExit(
                        f"{path.name}: {name} painted {transparent_count} transparent pixels"
                    )
                continue

            error = skeleton_transparency_error(
                item,
                path.name,
                max_transparent_pixels=max_skeleton_transparent_pixels,
            )
            if error:
                raise SystemExit(error)
        print(
            f"PASS {path.name}: visible={visible}/{total}, "
            f"interior_fill_strokes={by_name['interior_fill']['stroke_count']}, "
            f"scanline_strokes={by_name['scanline']['stroke_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

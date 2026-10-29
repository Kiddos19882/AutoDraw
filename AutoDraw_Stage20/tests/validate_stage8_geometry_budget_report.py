from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


REQUIRED_CASES = {
    ("reference-image", "combined-budget"),
    ("checkerboard", "combined-budget"),
    ("horizontal_stripes", "combined-budget"),
    ("nested_details", "combined-budget"),
    ("four_color_blocks_with_transparency", "combined-budget"),
    ("constraint-isolation", "point-budget-priority"),
    ("constraint-isolation", "paint-budget-priority"),
    ("constraint-isolation", "combined-budget"),
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the Stage 8 benchmark report contract.")
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    path = Path(args.report)
    if not path.is_file():
        raise SystemExit(f"Stage 8 report does not exist: {path}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("schema_version") != 1:
        raise SystemExit("Unsupported Stage 8 report schema version.")
    if report.get("benchmark") != "stage8_geometry_budget_quality":
        raise SystemExit("Unexpected benchmark identifier.")
    results = report.get("results")
    if not isinstance(results, list) or report.get("case_count") != len(results):
        raise SystemExit("Stage 8 case_count does not match results.")
    found = {(item.get("case"), item.get("scenario")) for item in results}
    missing = REQUIRED_CASES - found
    if missing:
        raise SystemExit(f"Missing required Stage 8 scenarios: {sorted(missing)}")

    for item in results:
        for field in ("stroke_count", "quality_mismatch_pixel_count", "quality_pixel_accuracy_percent",
                      "quality_visible_pixel_accuracy_percent", "fits_paint_budget", "fits_point_budget",
                      "fits_both_budgets", "needs_multi_board_split", "quality_measure_scope"):
            if field not in item:
                raise SystemExit(f"{item.get('case')}/{item.get('scenario')} missing field {field!r}.")
        for field in ("stroke_count", "quality_mismatch_pixel_count"):
            if isinstance(item[field], bool) or not isinstance(item[field], int) or item[field] < 0:
                raise SystemExit(f"{item.get('case')}/{item.get('scenario')} has invalid {field}.")
        for field in ("quality_pixel_accuracy_percent", "quality_visible_pixel_accuracy_percent"):
            value = item[field]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 100:
                raise SystemExit(f"{item.get('case')}/{item.get('scenario')} has invalid {field}.")
        if item["quality_measure_scope"] != "programmatic_preview":
            raise SystemExit(f"{item.get('case')}/{item.get('scenario')} has an unexpected quality scope.")
        if not isinstance(item.get("fits_paint_budget"), bool) or not isinstance(item.get("fits_point_budget"), bool):
            raise SystemExit("Budget fit fields must be booleans.")
        if item["fits_both_budgets"] != (item["fits_paint_budget"] and item["fits_point_budget"]):
            raise SystemExit(f"{item.get('case')}/{item.get('scenario')} has inconsistent combined budget status.")
        if item["needs_multi_board_split"] == item["fits_both_budgets"]:
            raise SystemExit(f"{item.get('case')}/{item.get('scenario')} has inconsistent split recommendation.")
        artifacts = item.get("artifacts", {})
        for artifact_key in ("input", "plan", "preview", "report"):
            if not artifacts.get(artifact_key):
                raise SystemExit(f"{item.get('case')}/{item.get('scenario')} missing artifact {artifact_key!r}.")

    print(f"Stage 8 report validated: {len(results)} scenarios, quality and dual-budget fields are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

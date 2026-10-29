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
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
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

    by_case = {(item.get("case"), item.get("scenario")): item for item in results}
    reference = by_case[("reference-image", "combined-budget")]
    mode_candidates = reference.get("mode_candidates", [])
    if not isinstance(mode_candidates, list) or len(mode_candidates) < 2:
        raise SystemExit("Reference image must compare at least two optimized geometry modes.")
    if not {"scanline", "contour", "skeleton"}.issubset({item.get("mode") for item in mode_candidates}):
        raise SystemExit("Reference-image report must include scanline, contour and skeleton candidates.")
    fitting_modes = [item for item in mode_candidates if item.get("fits_budget") is True]
    for candidate in mode_candidates:
        value = candidate.get("quality_visible_pixel_accuracy_percent")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 100:
            raise SystemExit(f"Invalid visible-pixel accuracy for mode {candidate.get('mode')!r}.")
    if fitting_modes:
        max_visible_accuracy = max(float(item["quality_visible_pixel_accuracy_percent"]) for item in fitting_modes)
        if abs(float(reference.get("quality_visible_pixel_accuracy_percent", -2)) - max_visible_accuracy) > 0.0001:
            raise SystemExit("Selected reference mode is not the best fitting candidate by visible-pixel accuracy.")

    point_case = by_case[("constraint-isolation", "point-budget-priority")]
    point_baseline = point_case.get("baseline", {})
    if point_baseline.get("fits_point_budget") is not False or point_case.get("fits_point_budget") is not True:
        raise SystemExit("Point-priority case did not demonstrate coarsening into the point budget.")
    if not isinstance(point_case.get("scale"), (int, float)) or point_case["scale"] >= 1.0:
        raise SystemExit("Point-priority case did not coarsen the input.")

    paint_case = by_case[("constraint-isolation", "paint-budget-priority")]
    paint_baseline = paint_case.get("baseline", {})
    if paint_baseline.get("fits_paint_budget") is not False or paint_case.get("fits_paint_budget") is not True:
        raise SystemExit("Paint-priority case did not demonstrate coarsening into the paint budget.")
    if paint_baseline.get("fits_point_budget") is not True or paint_case.get("fits_point_budget") is not True:
        raise SystemExit("Paint-priority case does not isolate paint cost from the point budget.")
    if not isinstance(paint_case.get("scale"), (int, float)) or paint_case["scale"] >= 1.0:
        raise SystemExit("Paint-priority case did not coarsen the input.")

    combined_case = by_case[("constraint-isolation", "combined-budget")]
    combined_baseline = combined_case.get("baseline", {})
    if combined_baseline.get("fits_paint_budget") is not False or combined_baseline.get("fits_point_budget") is not False:
        raise SystemExit("Combined-budget case must start outside both resource targets.")

    for item in results:
        for field in ("stroke_count", "quality_mismatch_pixel_count", "quality_pixel_accuracy_percent",
                      "quality_coverage_percent", "quality_visible_pixel_accuracy_percent",
                      "quality_uncovered_visible_pixel_count", "quality_painted_transparent_pixel_count",
                      "fits_paint_budget", "fits_point_budget", "fits_both_budgets",
                      "needs_multi_board_split", "quality_measure_scope"):
            if field not in item:
                raise SystemExit(f"{item.get('case')}/{item.get('scenario')} missing field {field!r}.")
        for field in ("stroke_count", "quality_mismatch_pixel_count", "quality_uncovered_visible_pixel_count", "quality_painted_transparent_pixel_count"):
            if isinstance(item[field], bool) or not isinstance(item[field], int) or item[field] < 0:
                raise SystemExit(f"{item.get('case')}/{item.get('scenario')} has invalid {field}.")
        for field in ("quality_pixel_accuracy_percent", "quality_coverage_percent", "quality_visible_pixel_accuracy_percent"):
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
        baseline = item.get("baseline")
        if not isinstance(baseline, dict) or not isinstance(baseline.get("available"), bool):
            raise SystemExit(f"{item.get('case')}/{item.get('scenario')} missing baseline comparison status.")
        if baseline["available"]:
            for field in ("stroke_count", "path_length_px", "paint_cost_px_equivalent",
                          "estimated_game_points", "quality_pixel_accuracy_percent",
                          "quality_coverage_percent", "quality_visible_pixel_accuracy_percent",
                          "quality_uncovered_visible_pixel_count", "quality_painted_transparent_pixel_count"):
                if field not in baseline:
                    raise SystemExit(f"{item.get('case')}/{item.get('scenario')} baseline missing {field!r}.")
            loss = item.get("coarsening_quality_loss_percentage_points")
            if isinstance(loss, bool) or not isinstance(loss, (int, float)) or not math.isfinite(loss):
                raise SystemExit(f"{item.get('case')}/{item.get('scenario')} has invalid quality-loss comparison.")
        artifacts = item.get("artifacts", {})
        for artifact_key in ("input", "plan", "preview", "report"):
            if not artifacts.get(artifact_key):
                raise SystemExit(f"{item.get('case')}/{item.get('scenario')} missing artifact {artifact_key!r}.")
        if baseline["available"] and not artifacts.get("baseline_preview"):
            raise SystemExit(f"{item.get('case')}/{item.get('scenario')} missing baseline preview artifact.")

    print(f"Stage 8 report validated: {len(results)} scenarios, quality and dual-budget fields are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

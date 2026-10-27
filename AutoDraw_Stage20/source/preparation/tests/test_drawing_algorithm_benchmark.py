from __future__ import annotations

import numpy as np

from color_scanline import build_color_scanline_plan
from drawing_algorithm_benchmark import summarize_plan
from geometry_color_plan import build_geometry_color_plan


PALETTE = [
    {"id": "black", "name": "Black", "rgb": [0, 0, 0], "hex": "#000000"},
    {"id": "red", "name": "Red", "rgb": [255, 0, 0], "hex": "#FF0000"},
]


def _filled_shape() -> np.ndarray:
    indexes = np.full((40, 40), -1, dtype=np.int32)
    indexes[4:36, 4:36] = 0
    indexes[12:28, 12:28] = 1
    return indexes


def test_scanline_keeps_fill_while_contour_and_skeleton_measure_less_coverage():
    source = _filled_shape()
    scanline = build_color_scanline_plan(
        source, PALETTE, board_item_type="BoardItem2", board_point_limit=6000
    )
    contour = build_geometry_color_plan(
        source, PALETTE, mode="contour", simplify_tolerance_px=0.0
    )
    skeleton = build_geometry_color_plan(
        source, PALETTE, mode="skeleton", simplify_tolerance_px=0.0
    )

    scanline_metrics = summarize_plan("scanline", scanline, source)
    contour_metrics = summarize_plan("contour", contour, source)
    skeleton_metrics = summarize_plan("skeleton", skeleton, source)

    assert scanline_metrics["covered_source_visible_percent"] == 100.0
    assert scanline_metrics["exact_color_match_percent_of_source"] == 100.0
    assert contour_metrics["covered_source_visible_percent"] < 100.0
    assert skeleton_metrics["covered_source_visible_percent"] < 100.0
    assert contour_metrics["stroke_count"] < scanline_metrics["stroke_count"]
    assert skeleton_metrics["stroke_count"] < scanline_metrics["stroke_count"]


def test_benchmark_reports_both_resource_estimates_and_visual_metrics():
    source = _filled_shape()
    plan = build_color_scanline_plan(
        source, PALETTE, board_item_type="BoardItem2", board_point_limit=6000
    )

    metrics = summarize_plan("scanline", plan, source)

    assert metrics["source_visible_pixel_count"] > 0
    assert metrics["covered_source_pixel_count"] > 0
    assert metrics["paint_cost_estimate"]["estimated_total_ink_px_equivalent"] > 0
    assert metrics["point_quota_estimate"]["estimated_point_count"] > 0
    assert metrics["point_quota_estimate"]["frame_rate_fps_is_nominal"] is True


def test_load_palette_document_reads_confirmed_browser_profile(tmp_path):
    import json

    from drawing_algorithm_benchmark import load_palette_document

    path = tmp_path / "browser-palette.json"
    path.write_text(json.dumps({
        "profile_schema_version": 1,
        "profile_name": "Browser palette",
        "metadata": {"source": "desktop-screenshot", "method": "screenshot-assisted"},
        "colors": [
            {"id": "dark", "name": "Dark", "rgb": [27, 27, 27], "hex": "#1B1B1B", "status": "confirmed"},
            {"id": "white", "name": "White", "rgb": [255, 255, 255], "hex": "#FFFFFF", "status": "corrected"},
        ],
    }), encoding="utf-8")

    palette, report = load_palette_document(path)

    assert [item["hex"] for item in palette] == ["#1B1B1B", "#FFFFFF"]
    assert report["palette_name"] == "Browser palette"
    assert report["palette_color_count"] == 2
    assert report["confirmed_color_count"] == 2
    assert report["has_exact_black"] is False
    assert report["has_exact_white"] is True


def test_load_palette_document_rejects_unconfirmed_colors(tmp_path):
    import json
    import pytest

    from drawing_algorithm_benchmark import load_palette_document

    path = tmp_path / "unconfirmed.json"
    path.write_text(json.dumps({
        "profile_schema_version": 1,
        "colors": [
            {"id": "red", "name": "Red", "rgb": [255, 0, 0], "hex": "#FF0000", "status": "detected"},
        ],
    }), encoding="utf-8")

    with pytest.raises(ValueError, match="неподтверждённые цвета"):
        load_palette_document(path)

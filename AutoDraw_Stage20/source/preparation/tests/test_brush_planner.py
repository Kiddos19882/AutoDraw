from __future__ import annotations

import unittest

import numpy as np

from brush_planner import BrushPlannerError, build_adaptive_brush_plan, validate_adaptive_brush_plan


def make_plan(width: int, height: int, strokes: list[dict]) -> dict:
    return {
        "schema_version": 1,
        "plan_type": "autodraw_color_scanline_plan",
        "plan_name": "brush planner test",
        "canvas": {"width": width, "height": height},
        "strokes": strokes,
    }


def make_stroke(index: int, x1: int, x2: int, y: int, palette_index: int = 0) -> dict:
    return {
        "name": f"stroke_{index}",
        "closed": False,
        "points": [{"x": float(x1), "y": float(y)}, {"x": float(x2), "y": float(y)}],
        "color": {"palette_index": palette_index, "id": str(palette_index), "name": f"color{palette_index}", "hex": "#000000"},
        "metadata": {"row_y": y, "x_start": x1, "x_end": x2},
    }


class AdaptiveBrushPlannerTests(unittest.TestCase):
    def test_wide_uniform_run_splits_into_safe_edges_and_wide_interior(self):
        indexes = np.zeros((40, 100), dtype=np.int32)
        source = make_plan(100, 40, [make_stroke(0, 0, 99, 20)])
        result = build_adaptive_brush_plan(indexes, source, calibration_confirmed=True)
        planned = result["strokes"]
        self.assertEqual(len(planned), 3)
        self.assertEqual([item["brush"]["role"] for item in planned], ["leading_edge", "interior", "trailing_edge"])
        self.assertEqual([planned[i]["brush"]["value"] for i in range(3)], [1, 20, 1])
        self.assertTrue(all(not item["brush"]["safe_to_execute"] for item in planned))
        self.assertTrue(result["brush_configuration"]["calibration_confirmed"])
        self.assertFalse(result["brush_configuration"]["automatic_execution_allowed"])
        self.assertFalse(result["summary"]["ready_for_automatic_execution"])
        self.assertEqual(len(result["summary"]["execution_blockers"]), 2)
        validate_adaptive_brush_plan(result)

    def test_wide_brush_does_not_cross_adjacent_horizontal_color(self):
        indexes = np.zeros((30, 80), dtype=np.int32)
        indexes[:, 40:] = 1
        source = make_plan(80, 30, [make_stroke(0, 0, 39, 15, 0)])
        result = build_adaptive_brush_plan(indexes, source, calibration_confirmed=True)
        self.assertNotEqual(result["strokes"][0]["brush"]["value"], 20)
        self.assertTrue(all(item["brush"]["safe_for_color_map"] for item in result["strokes"]))

    def test_different_color_above_and_below_forces_thin_brush(self):
        indexes = np.zeros((30, 80), dtype=np.int32)
        indexes[14, :] = 1
        indexes[15, :40] = 0
        indexes[15, 40:] = 1
        indexes[16, :] = 1
        source = make_plan(80, 30, [make_stroke(0, 0, 39, 15, 0)])
        result = build_adaptive_brush_plan(indexes, source, calibration_confirmed=True)
        self.assertEqual(len(result["strokes"]), 1)
        self.assertEqual(result["strokes"][0]["brush"]["value"], 1)

    def test_without_calibration_plan_is_not_ready_for_automatic_execution(self):
        indexes = np.zeros((30, 80), dtype=np.int32)
        source = make_plan(80, 30, [make_stroke(0, 0, 79, 15)])
        result = build_adaptive_brush_plan(indexes, source)
        self.assertFalse(result["brush_configuration"]["automatic_execution_allowed"])
        self.assertTrue(all(not item["brush"]["safe_to_execute"] for item in result["strokes"]))
        self.assertFalse(result["summary"]["ready_for_automatic_execution"])

    def test_transparency_is_not_treated_as_same_color(self):
        indexes = np.zeros((30, 80), dtype=np.int32)
        indexes[:, 35:45] = -1
        source = make_plan(80, 30, [make_stroke(0, 0, 34, 15)])
        result = build_adaptive_brush_plan(indexes, source, calibration_confirmed=True)
        self.assertNotEqual(result["strokes"][0]["brush"]["value"], 20)
        self.assertTrue(all(item["brush"]["safe_for_color_map"] for item in result["strokes"]))

    def test_rejects_wrong_canvas_and_brush_outside_planner_range(self):
        indexes = np.zeros((30, 80), dtype=np.int32)
        source = make_plan(80, 30, [make_stroke(0, 0, 79, 15)])
        with self.assertRaises(BrushPlannerError):
            build_adaptive_brush_plan(np.zeros((31, 80), dtype=np.int32), source)
        with self.assertRaises(BrushPlannerError):
            build_adaptive_brush_plan(indexes, source, max_brush_value=21)

    def test_fallback_is_never_claimed_safe(self):
        indexes = np.zeros((5, 5), dtype=np.int32)
        indexes[2, 3:] = 1
        source = make_plan(5, 5, [make_stroke(0, 0, 2, 2)])
        result = build_adaptive_brush_plan(indexes, source, brush_scale_x=3, brush_scale_y=1)
        if result["strokes"][0]["brush"]["value"] is None:
            self.assertFalse(result["strokes"][0]["brush"]["safe_to_execute"])
            self.assertFalse(result["summary"]["ready_for_automatic_execution"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

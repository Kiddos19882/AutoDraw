#!/usr/bin/env python3
"""Algorithm-only V35 layer validation tests (no native brush claims)."""
import unittest

from engine001_paint_then_detail_v35 import (
    build_layered_native_plan, native_strokes,
)

def stroke(i, *, color=0xFF8000, x=155.0, width=2):
    return {
        "strokeId": f"s-{i}", "width": width, "colorRgb": color,
        "colorIndex": 5,
        "points": [{"x": x, "y": 4.0}, {"x": x + 0.25, "y": 4.0}],
    }

class V35LayerPlanTests(unittest.TestCase):
    def test_order_and_mutation_isolation(self):
        paint = [stroke(1), stroke(2)]
        detail = [stroke(3, color=0x302020)]
        p = build_layered_native_plan(paint, detail)
        self.assertEqual([x["layer"] for x in p["strokes"]],
                         ["paint", "paint", "detail"])
        self.assertEqual((p["paint_strokes"], p["detail_strokes"]), (2, 1))
        self.assertEqual(p["synthetic_vertices_NOT_CHALK"], 6)
        self.assertEqual(p["native_quality_status"], "NOT_RUN")
        self.assertIsNone(p["exact_CHALK"])
        paint[0]["points"][0]["x"] = 190.0
        self.assertEqual(p["strokes"][0]["stroke"]["points"][0]["x"], 155.0)
        flat = native_strokes(p)
        flat[0]["points"][0]["x"] = 200.0
        self.assertEqual(p["strokes"][0]["stroke"]["points"][0]["x"], 155.0)

    def test_empty_detail_permitted_empty_paint_rejected(self):
        self.assertEqual(build_layered_native_plan([stroke(1)], [])["detail_strokes"], 0)
        with self.assertRaisesRegex(ValueError, "paint layer"):
            build_layered_native_plan([], [stroke(1)])

    def test_no_duplicate_ids_or_invalid_width(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            build_layered_native_plan([stroke(1)], [stroke(1)])
        with self.assertRaisesRegex(ValueError, "width"):
            build_layered_native_plan([stroke(1, width=7)], [])
        with self.assertRaisesRegex(ValueError, "RGB"):
            bad=stroke(1);bad["colorRgb"]=-1
            build_layered_native_plan([bad], [])

    def test_no_out_of_board_nan_zero_length_or_invalid_point(self):
        for x in (-0.1, 460.0, float("nan"), float("inf")):
            with self.subTest(x=x), self.assertRaises(ValueError):
                build_layered_native_plan([stroke(1, x=x)], [])
        s=stroke(1);s["points"][1]=dict(s["points"][0])
        with self.assertRaisesRegex(ValueError, "zero-length"):
            build_layered_native_plan([s], [])
        s=stroke(2);s["points"][1]["x"]="bad"
        with self.assertRaisesRegex(ValueError, "non-finite"):
            build_layered_native_plan([s], [])

    def test_budget_rejection_not_truncation(self):
        with self.assertRaisesRegex(ValueError, "OVER_BUDGET"):
            build_layered_native_plan([stroke(1),stroke(2)], [stroke(3)],
                                      max_strokes=2)
        with self.assertRaisesRegex(ValueError, "OVER_BUDGET"):
            build_layered_native_plan([stroke(1)], [stroke(2)],
                                      max_vertices=3)

    def test_reversed_native_sequence_rejected(self):
        p=build_layered_native_plan([stroke(1)], [stroke(2)])
        p["strokes"].reverse()
        with self.assertRaisesRegex(ValueError, "order reversed"):
            native_strokes(p)

if __name__=="__main__":
    unittest.main()

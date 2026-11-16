#!/usr/bin/env python3
"""V43-P4.1 regression: source proxy only, not a native Egret proof."""
import unittest
import numpy as np

from run_engine001_full_adaptive_fill_v43p4 import (
    COLORS, FROZEN_DETAILS, MAX_STROKES, MAX_VERTICES,
    WIDTHS, checked_labels, source_plan,
)


class FullAdaptiveFillP4Tests(unittest.TestCase):
    def setUp(self):
        labels = np.zeros((240, 150), dtype=np.int16)
        labels[20:60, 10:60] = 4
        labels[65:100, 30:95] = 5
        labels[115:140, 20:100] = 6
        labels[160:220, 20:125] = 7
        self.labels = labels

    def test_source_only_all_classes_and_order(self):
        plan = source_plan(self.labels)
        self.assertFalse(plan["safe_to_execute"])
        self.assertFalse(plan["details_exact_verified"])
        self.assertEqual(plan["original_paint_retained"], 0)
        self.assertEqual(plan["detail_strokes_required_unchanged"], FROZEN_DETAILS)
        self.assertLessEqual(plan["paint_strokes"] + FROZEN_DETAILS, MAX_STROKES)
        self.assertLessEqual(plan[
            "synthetic_vertices_with_frozen_detail_NOT_CHALK"], MAX_VERTICES)
        self.assertEqual(set(plan["source_model_diagnostics_NOT_EGRET"]),
                         {str(x) for x in COLORS})
        self.assertEqual(set(s["colorIndex"] for s in plan["paint"]), set(COLORS))
        for owner in COLORS:
            strokes = [s for s in plan["paint"] if s["colorIndex"] == owner]
            order = [WIDTHS.index(s["width"]) for s in strokes]
            self.assertEqual(order, sorted(order))
            for s in strokes:
                self.assertEqual(len(s["points"]), 2)
                for p in s["points"]:
                    self.assertTrue(155 <= p["x"] < 305)
                    self.assertTrue(0 <= p["y"] < 240)
        self.assertIsNone(plan["exact_CHALK"])

    def test_deterministic(self):
        self.assertEqual(source_plan(self.labels), source_plan(self.labels))

    def test_fail_closed_for_invalid_inputs(self):
        with self.assertRaisesRegex(ValueError, "source labels"):
            checked_labels(np.zeros((5, 5), np.int16))
        with self.assertRaisesRegex(ValueError, "source labels"):
            checked_labels(np.ones((240, 150), np.float32))
        with self.assertRaisesRegex(ValueError, "source owner"):
            source_plan(np.zeros((240, 150), np.int16))
        with self.assertRaisesRegex(ValueError, "BLOCKED_RESOURCE"):
            source_plan(self.labels, max_strokes=FROZEN_DETAILS + 1)
        with self.assertRaisesRegex(ValueError, "resource caps"):
            source_plan(self.labels, max_vertices=1)


if __name__ == "__main__":
    unittest.main()

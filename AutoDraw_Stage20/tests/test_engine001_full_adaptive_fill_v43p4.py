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

    def test_native_assembly_preserves_410_details_and_rejects_original_paint(self):
        from copy import deepcopy
        from run_engine001_v43p4_native_ab import assemble_b0
        paints = []
        for i in range(1945):
            owner = COLORS[i % 4]
            paints.append({"layer": "paint", "stroke": {
                "strokeId": f"icon-{i}", "colorIndex": owner, "width": 2,
                "colorRgb": (owner << 16) | 0x2020,
                "points": [{"x": 155, "y": 5}, {"x": 156, "y": 5}],
            }})
        details = []
        for i in range(410):
            count = 5 if i < 152 else 4
            details.append({"layer": "detail", "stroke": {
                "strokeId": f"detail-v18-B-{i}", "colorIndex": 100,
                "width": 1, "colorRgb": 0xDD77AA + i,
                "points": [{"x": 160 + j, "y": i % 240}
                           for j in range(count)],
            }})
        frozen = {"strokes": paints + details}
        source = {
            "candidate": "B0_SOURCE_ONLY", "safe_to_execute": False,
            "original_paint_retained": 0, "paint_strokes": 4,
            "synthetic_vertices_with_frozen_detail_NOT_CHALK": 1800,
            "paint": [{"strokeId": f"p4-b0-{owner}-{i:05d}",
                       "colorIndex": owner, "width": WIDTHS[i],
                       "points": [{"x": 165, "y": 10 + i},
                                  {"x": 175, "y": 10 + i}]}
                      for i, owner in enumerate(COLORS)],
        }
        original = deepcopy(frozen)
        native, metadata = assemble_b0(source, frozen)
        self.assertEqual(frozen, original)
        self.assertEqual(native[4:], [entry["stroke"] for entry in details])
        self.assertEqual(metadata["original_paint_retained"], 0)
        self.assertEqual(metadata["detail_count"], 410)
        self.assertEqual(metadata["synthetic_vertices_NOT_CHALK"], 1800)
        self.assertTrue(metadata["V44B_410_detail_exact"])
        self.assertEqual(len(native), 414)
        bad = deepcopy(source)
        bad["paint"][0]["strokeId"] = "icon-0"
        with self.assertRaisesRegex(ValueError, "unexpected B0 paint"):
            assemble_b0(bad, frozen)
        bad = deepcopy(source)
        bad["safe_to_execute"] = True
        with self.assertRaisesRegex(ValueError, "invalid source-only"):
            assemble_b0(bad, frozen)

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

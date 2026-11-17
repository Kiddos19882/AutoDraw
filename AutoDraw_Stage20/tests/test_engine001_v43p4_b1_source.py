#!/usr/bin/env python3
"""B1 independently registered source constraints, not Egret quality tests."""
import unittest

import cv2
import numpy as np

from run_engine001_v43p4_b1_source import (
    EXPERIMENT, candidate_penalty, b1_source_plan,
)
from run_engine001_full_adaptive_fill_v43p4 import COLORS, WIDTHS


class SourceB1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        labels = np.zeros((240, 150), dtype=np.int16)
        labels[14:45, 15:65] = 4
        labels[54:99, 45:110] = 5
        labels[104:145, 20:100] = 6
        labels[154:213, 15:128] = 7
        cls.labels = labels

    def test_all_owners_preserved_and_width2_centers_owned(self):
        plan = b1_source_plan(self.labels)
        self.assertEqual(plan["experiment"], EXPERIMENT)
        self.assertEqual(plan["original_A_paint_retained"], 0)
        self.assertEqual(plan["original_B0_paint_retained"], 0)
        self.assertFalse(plan["safe_to_execute"])
        self.assertEqual(plan["E3_native"], "NOT_RUN")
        self.assertEqual(plan["fixed_candidate_score"]["foreign_required_penalty"], 2.0)
        self.assertLessEqual(plan["projected_total_strokes"], 3000)
        self.assertLessEqual(plan["projected_synthetic_vertices_NOT_CHALK"], 5900)
        self.assertEqual(set(plan["source_model_diagnostics_NOT_EGRET"]), set(map(str, COLORS)))
        self.assertEqual(set(s["colorIndex"] for s in plan["paint"]), set(COLORS))
        for s in plan["paint"]:
            self.assertTrue(s["strokeId"].startswith(f'p4-b1-{s["colorIndex"]}-'))
            self.assertIn(s["width"], WIDTHS)
            if s["width"] == 2:
                ink = np.zeros(self.labels.shape, np.uint8)
                a, b = s["points"]
                cv2.line(ink, (a["x"] - 155, a["y"]),
                         (b["x"] - 155, b["y"]), 255, 1, cv2.LINE_8)
                self.assertTrue(np.all(self.labels[ink > 0] == s["colorIndex"]))

    def test_deterministic_and_reject_unsafe_budget(self):
        self.assertEqual(b1_source_plan(self.labels), b1_source_plan(self.labels))
        with self.assertRaisesRegex(ValueError, "BLOCKED_RESOURCE"):
            b1_source_plan(self.labels, max_strokes=411)
        with self.assertRaisesRegex(ValueError, "missing required owner"):
            b1_source_plan(np.zeros((240, 150), np.int16))

    def test_width2_cross_class_center_rejected(self):
        labels = np.zeros((240, 150), dtype=np.int16)
        labels[70:75, 30:42] = 4
        labels[72, 35] = 5
        owner = 4
        # This is a candidate of the original B0 path schema, but center
        # intersects a real class5 pixel: B1 must reject it, not just penalize.
        candidate = (2, (32, 72), (40, 72),
                     np.array([72*150+x for x in (32,33,34,36,37,38,39,40)],
                              dtype=np.int32), 24)
        self.assertIsNone(candidate_penalty(labels, owner, candidate))
        labels[72, 35] = 4
        score = candidate_penalty(labels, owner, candidate)
        self.assertIsNotNone(score)
        self.assertEqual(len(score), 2)
        self.assertTrue(all(value >= 0 for value in score))


if __name__ == "__main__":
    unittest.main()

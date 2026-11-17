#!/usr/bin/env python3
"""All-source zone boundary planning regressions (geometry E2, not Egret E3)."""
import unittest
import numpy as np
import cv2

from run_engine001_color_zone_boundaries_native import (
    COLORS, DIAGNOSTIC_RGB, EXPERIMENT, EPSILON, MAX_STROKES,
    MAX_VERTICES, plan_zone_boundaries,
)


class ZoneBoundaryTests(unittest.TestCase):
    def test_disjoint_regions_holes_singletons_and_all_colors(self):
        labels = np.zeros((240,150),dtype=np.int16)
        cv2.circle(labels, (35, 45), 22, 4, -1)
        cv2.circle(labels, (35, 45), 7, 0, -1)
        cv2.rectangle(labels, (75, 12), (136, 68), 5, -1)
        cv2.rectangle(labels, (15, 112), (68, 176), 6, -1)
        cv2.circle(labels, (108, 169), 28, 7, -1)
        labels[210,4] = 4
        strokes, stats = plan_zone_boundaries(labels)
        self.assertTrue(stats["all_source_contours_included"])
        self.assertEqual(set(stats["per_owner"]), {"4","5","6","7"})
        self.assertEqual(set(s["colorIndex"] for s in strokes), set(COLORS))
        self.assertEqual(stats["total_paths"],len(strokes))
        self.assertEqual(stats["total_synthetic_vertices_NOT_CHALK"],
                         sum(len(s["points"]) for s in strokes))
        self.assertLessEqual(len(strokes),MAX_STROKES)
        self.assertLessEqual(stats["total_synthetic_vertices_NOT_CHALK"],MAX_VERTICES)
        self.assertGreater(stats["per_owner"]["4"]["single_point_islands_or_contours"],0)
        self.assertGreater(stats["per_owner"]["4"]["closed_boundary_paths"],0)
        self.assertEqual(len({s["strokeId"] for s in strokes}),len(strokes))
        for stroke in strokes:
            self.assertEqual(stroke["width"],2)
            self.assertEqual(stroke["colorRgb"],DIAGNOSTIC_RGB[stroke["colorIndex"]])
            self.assertTrue(2 <= len(stroke["points"]) <= 128)
            for point in stroke["points"]:
                self.assertTrue(155 <= point["x"] < 305)
                self.assertTrue(0 <= point["y"] < 240)

    def test_deterministic_contours(self):
        labels = np.zeros((240,150),dtype=np.int16)
        for i,color in enumerate(COLORS):
            cv2.circle(labels,(25+30*i,50+20*i),10,color,-1)
        self.assertEqual(plan_zone_boundaries(labels),plan_zone_boundaries(labels))

    def test_invalid_source_fails_closed(self):
        for wrong in (np.ones((50,50),dtype=np.int16),
                      np.ones((240,150),dtype=np.float32),
                      np.ones((240,150),dtype=np.int16)*8):
            with self.assertRaisesRegex(ValueError,"source labels"):
                plan_zone_boundaries(wrong)
        with self.assertRaisesRegex(ValueError,"required owner"):
            plan_zone_boundaries(np.zeros((240,150),dtype=np.int16))


if __name__ == "__main__":
    unittest.main()

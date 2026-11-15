#!/usr/bin/env python3
"""ENGINE-001 V43/P1: source-only geometry tests, NO native brush quality."""
import unittest

import numpy as np

from run_engine001_shape_adaptive_fill_v43p1 import (
    analyze_component, analyze_index_map,
)


class V43SourceShapeTests(unittest.TestCase):
    def test_wide_component_and_no_execution_authority(self):
        mask = np.ones((13, 13), dtype=bool)
        row = analyze_component(mask, 5, 1)
        self.assertEqual(row["area_source_px"], 169)
        self.assertEqual(row["role"], "wide_interior_candidate")
        self.assertFalse(row["safe_to_execute"])
        self.assertFalse(row["native_footprint_validated"])
        self.assertGreaterEqual(row["maximum_inscribed_radius_source_px"], 4)

    def test_thin_diagonal_oriented_candidate(self):
        mask = np.zeros((30, 30), dtype=bool)
        for t in range(2, 27):
            mask[t, t] = True
        row = analyze_component(mask, 6, 3)
        self.assertEqual(row["role"], "thin_shape_candidate")
        self.assertTrue(row["oriented_sweep_candidate"])
        # A perfectly straight line has a zero minor eigenvalue: ratio is +Inf
        # internally and JSON-safe None in this report, not a finite float.
        self.assertIsNone(row["anisotropy_ratio"])
        self.assertGreater(row["skeleton_pixels_or_status"], 0)

    def test_small_component_not_oriented(self):
        mask = np.ones((2, 3), dtype=bool)
        row = analyze_component(mask, 4, 1)
        self.assertFalse(row["oriented_sweep_candidate"])
        self.assertEqual(row["area_source_px"], 6)

    def test_source_class_components_exact_accounting(self):
        labels = np.zeros((240, 150), dtype=np.int16)
        labels[10:23, 12:25] = 5
        labels[50:80, 70:74] = 6
        labels[100:103, 10:13] = 7
        record = analyze_index_map(labels)
        self.assertEqual(record["target_source_pixels"], 169 + 120 + 9)
        self.assertEqual(record["per_color"]["5"]["component_count"], 1)
        self.assertEqual(record["per_color"]["4"]["component_count"], 0)
        self.assertEqual(record["per_color"]["6"]["source_class_pixels"], 120)
        self.assertTrue(all(not r["safe_to_execute"] for r in record["components"]))

    def test_reject_bad_masks_and_palette(self):
        with self.assertRaisesRegex(ValueError, "shape"):
            analyze_index_map(np.zeros((10, 10), dtype=np.int16))
        with self.assertRaisesRegex(ValueError, "integers"):
            analyze_index_map(np.zeros((240, 150), dtype=np.float64))
        with self.assertRaisesRegex(ValueError, "palette"):
            analyze_index_map(np.full((240, 150), 9, dtype=np.int16))
        with self.assertRaisesRegex(ValueError, "empty"):
            analyze_component(np.zeros((8, 8), dtype=bool), 4, 1)
        with self.assertRaisesRegex(ValueError, "bool mask"):
            analyze_component(np.ones((8, 8), dtype=np.uint8), 4, 1)


if __name__ == "__main__":
    unittest.main()

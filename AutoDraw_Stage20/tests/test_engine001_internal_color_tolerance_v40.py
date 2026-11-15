#!/usr/bin/env python3
"""V40 frozen source internal overlap tolerance arithmetic; model-only unit cases."""
import unittest

import numpy as np

from run_engine001_internal_color_tolerance_v40 import overlap_by_class


class V40InternalOverlapTests(unittest.TestCase):
    def setUp(self):
        self.labels = np.full((45, 45), -1, dtype=np.int16)
        self.labels[10:35, 10:20] = 4
        self.labels[10:35, 20:36] = 5

    def test_allowed_internal_crossing_not_treated_as_error(self):
        painted = np.zeros_like(self.labels, dtype=bool)
        painted[20, 20:29] = True  # distances 1..9 to own-color x=19
        x = overlap_by_class(self.labels, 4, painted)
        self.assertEqual(x["foreign_required_class_native_pixels"], 9)
        self.assertEqual(x["foreign_overlap_allowed_within_3logical_px"], 9)
        self.assertEqual(x["foreign_overlap_excess_beyond_3logical_px"], 0)
        self.assertEqual(x["by_foreign_target_class"]["5"]["beyond_3logical_px_native_pixels"], 0)

    def test_tenth_native_pixel_is_internal_violation(self):
        painted = np.zeros_like(self.labels, dtype=bool)
        painted[20, 20:30] = True  # last x=29 is 10 native pixels
        x = overlap_by_class(self.labels, 4, painted)
        self.assertEqual(x["foreign_required_class_native_pixels"], 10)
        self.assertEqual(x["foreign_overlap_allowed_within_3logical_px"], 9)
        self.assertEqual(x["foreign_overlap_excess_beyond_3logical_px"], 1)

    def test_own_class_coverage_separate_from_foreign_crossing(self):
        painted = np.zeros_like(self.labels, dtype=bool)
        painted[10:35, 10:20] = True
        painted[20, 20] = True
        x = overlap_by_class(self.labels, 4, painted)
        self.assertEqual(x["correct_class_recall"], 1.0)
        self.assertEqual(x["foreign_required_class_native_pixels"], 1)
        self.assertEqual(x["foreign_overlap_excess_beyond_3logical_px"], 0)

    def test_near_white_is_not_other_required_color(self):
        painted = np.zeros_like(self.labels, dtype=bool)
        painted[20, 9] = True
        x = overlap_by_class(self.labels, 4, painted)
        self.assertEqual(x["foreign_required_class_native_pixels"], 0)

    def test_fail_closed_wrong_shape_and_empty_owner(self):
        with self.assertRaisesRegex(ValueError, "mismatching"):
            overlap_by_class(self.labels, 4, np.zeros((3, 3), dtype=bool))
        with self.assertRaisesRegex(ValueError, "missing source class"):
            overlap_by_class(self.labels, 7, np.zeros_like(self.labels, dtype=bool))
        with self.assertRaisesRegex(ValueError, "invalid source owner"):
            overlap_by_class(self.labels, 9, np.zeros_like(self.labels, dtype=bool))


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""AQA1 synthetic single-review labels: NO claim of independent human ground truth."""
import unittest
import numpy as np

from run_engine001_bpred_s4r1_semref1_aqa1_uploaded_a_intake import (
    count_a_labels, CODES, CATEGORIES,
)


class TestSEMREF1AQA1(unittest.TestCase):
    def test_exact_categories_and_nonempty_one_reviewer_support(self):
        labels = np.asarray([[CODES[0], CODES[1], CODES[2]],
                             [CODES[3], CODES[4], CODES[1]]], dtype=np.uint8)
        c = count_a_labels(labels)
        self.assertEqual(sum(c[n] for n in CATEGORIES), 6)
        self.assertEqual(c["A_K"], 3)
        self.assertEqual(c["A_I"], 1)
        self.assertEqual(c["source_pixels"], 6)
        self.assertEqual(c["A_review_fraction"], 4/6)
        self.assertEqual(c["single_reviewer_support"], "PRESENT_UNVERIFIED")

    def test_no_interior_is_blocked(self):
        labels = np.tile(CODES[1], (2, 3, 1))
        c = count_a_labels(labels)
        self.assertEqual(c["A_I"], 0)
        self.assertEqual(c["single_reviewer_support"],
                         "BLOCKED_INSUFFICIENT_SINGLE_REVIEW_SUPPORT")

    def test_unreviewed_is_not_negative_or_success(self):
        labels = np.zeros((5, 7, 3), dtype=np.uint8)
        c = count_a_labels(labels)
        self.assertEqual(c["unreviewed"], 35)
        self.assertEqual(c["A_review_fraction"], 0)
        self.assertEqual(c["single_reviewer_support"],
                         "BLOCKED_INSUFFICIENT_SINGLE_REVIEW_SUPPORT")

    def test_non_palette_rgb_is_forbidden(self):
        labels = np.zeros((1, 1, 3), dtype=np.uint8)
        labels[0, 0] = (254, 0, 255)
        with self.assertRaisesRegex(ValueError, "INVALID_LABEL_CODES"):
            count_a_labels(labels)

    def test_input_shape_and_dtype_are_guarded(self):
        for v in (np.zeros((2, 3, 4), dtype=np.uint8),
                  np.zeros((2, 3), dtype=np.uint8),
                  np.zeros((2, 3, 3), dtype=np.int32)):
            with self.assertRaisesRegex(ValueError, "INVALID_LABEL_MATRIX"):
                count_a_labels(v)


if __name__ == "__main__":
    unittest.main()

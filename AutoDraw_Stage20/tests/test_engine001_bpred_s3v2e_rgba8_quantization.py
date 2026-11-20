#!/usr/bin/env python3
"""Frozen E0 S3v2e Q0/QF/QR/QC scalar and negative contract regressions."""
from __future__ import annotations
import unittest
import numpy as np

import run_engine001_bpred_s3v2e_rgba8_quantization as q
import run_engine001_bpred_s3_native_source_over as s3


class BpredS3v2eContracts(unittest.TestCase):
    def test_01_exact_e0_and_real_source_bindings(self):
        self.assertEqual(q.E0_BLOB, "cab7f2d0867e87201913d588357bc1adc045e8ef")
        self.assertEqual(q.SOURCE_RUN, "44697386598")
        self.assertEqual(q.SOURCE_SHA,
                         "2ba4241be547cb14bfc0a180633ce7bfe6a9ab9a")
        self.assertEqual(q.NAMES, ("Q0", "QF", "QR", "QC"))
        self.assertEqual(q.BINS, ((0, 0), (1, 15), (16, 63),
                                 (64, 127), (128, 254), (255, 255)))

    def test_02_qc_preregistered_fractional_pixel(self):
        a = np.array([[[80, 60, 52, 64]]], dtype=np.uint8)
        np.testing.assert_array_equal(q.quantize_stage(a, "QC"),
                                      [[[84, 64, 56, 64]]])
        np.testing.assert_array_equal(q.quantize_stage(a, "Q0"), a)

    def test_03_qf_qr_comparators_not_qc(self):
        a = np.array([[[80, 60, 52, 64]]], dtype=np.uint8)
        np.testing.assert_array_equal(q.quantize_stage(a, "QF"),
                                      [[[80, 60, 52, 64]]])
        np.testing.assert_array_equal(q.quantize_stage(a, "QR"),
                                      [[[80, 60, 52, 64]]])
        self.assertFalse(np.array_equal(q.quantize_stage(a, "QC"),
                                        q.quantize_stage(a, "QR")))

    def test_04_alpha_zero_and_opaque_stay_identical(self):
        a = np.array([[[30, 40, 50, 0], [80, 70, 60, 255],
                       [1, 2, 3, 64]]], dtype=np.uint8)
        for name in q.NAMES:
            b = q.quantize_stage(a, name)
            np.testing.assert_array_equal(b[:, :, 3], a[:, :, 3])
            np.testing.assert_array_equal(b[0, :2], a[0, :2])
            np.testing.assert_array_equal(a[0, 2], [1, 2, 3, 64])

    def test_05_input_array_is_not_mutated(self):
        a = np.array([[[80, 60, 52, 64]]], dtype=np.uint8)
        original = a.copy()
        for name in q.NAMES:
            b = q.quantize_stage(a, name)
            self.assertFalse(np.shares_memory(b, a))
            np.testing.assert_array_equal(a, original)

    def test_06_bad_dtype_shape_and_mode_fail_closed(self):
        good = np.zeros((1, 1, 4), np.uint8)
        for bad, mode in [
            (good.astype(np.int16), "QC"),
            (good[:, :, :3], "QC"),
            (good[0], "QC"),
            (None, "QC"),
            (good, "NONPREREG_Q"),
        ]:
            with self.assertRaisesRegex(ValueError, "RGBA_MODE_DTYPE_SHAPE"):
                q.quantize_stage(bad, mode)

    def test_07_direct_stage_counts_separate_rgb_from_alpha(self):
        a = np.array([[[80, 60, 52, 64]]], np.uint8)
        b = np.array([[[84, 64, 56, 64]]], np.uint8)
        actual = q.difference(a, b)
        self.assertEqual(actual["rgb_mismatch_pixels"], 1)
        self.assertEqual(actual["alpha_mismatch_pixels"], 0)
        self.assertEqual(q.difference(q.quantize_stage(a, "QC"), b)
                         ["rgb_mismatch_pixels"], 0)

    def test_08_ordered_c0_metrics_use_existing_source_over(self):
        clear = np.zeros((1, 1, 4), np.uint8)
        a = clear.copy()
        b = clear.copy()
        a[0, 0] = [80, 60, 52, 255]
        b[0, 0] = [197, 65, 145, 255]
        frames = {
            "A_ONLY": {"canvas": a, "final": a},
            "B_ONLY": {"canvas": b, "final": b},
            "A_THEN_B": {"canvas": b, "final": b},
            "B_THEN_A": {"canvas": a, "final": a},
        }
        row = q.c0_row(1, "CROSSING", frames)
        self.assertEqual(set(row["ordered_variants"]),
                         {"A_THEN_B", "B_THEN_A"})
        self.assertTrue(row["ordered_variants"]["A_THEN_B"]
                        ["QC"]["frozen_H1_pass"])
        self.assertTrue(row["ordered_variants"]["B_THEN_A"]
                        ["QC"]["frozen_H1_pass"])
        np.testing.assert_array_equal(s3.source_over(a, b), b)


if __name__ == "__main__":
    unittest.main()

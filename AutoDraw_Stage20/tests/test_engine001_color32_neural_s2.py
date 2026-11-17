#!/usr/bin/env python3
"""NEURAL-S2 original-first color partition: source-only unit regressions."""
import unittest
import numpy as np

from run_engine001_color32_neural_s2 import (
    EXP, BG, PARAMS, independent_regions, evaluate,
)


class OriginalFirstS2Contracts(unittest.TestCase):
    def setUp(self):
        self.palette = np.zeros((32, 3), np.uint8)
        self.palette[BG] = [255, 255, 255]
        self.palette[1] = [240, 130, 110]
        self.palette[2] = [27, 27, 27]
        self.rgb = np.full((240, 150, 3), 255, np.uint8)
        self.rgb[30:150, 25:115] = [233, 126, 103]
        self.rgb[60:110, 65:99] = [30, 29, 28]

    def test_original_first_candidate_accepts_no_g32_input(self):
        c1, bg, labels, info = independent_regions(self.rgb, self.palette, [])
        self.assertEqual(c1.shape, (240, 150))
        self.assertTrue(np.all(c1[bg] == BG))
        self.assertEqual(info["neural_owned_pixels"], 0)
        self.assertGreater(info["regions"], 0)
        self.assertTrue(np.all(labels[~bg] >= 0))

    def test_same_source_same_result(self):
        a = independent_regions(self.rgb, self.palette, [])
        b = independent_regions(self.rgb, self.palette, [])
        self.assertTrue(np.array_equal(a[0], b[0]))
        self.assertTrue(np.array_equal(a[1], b[1]))

    def test_real_mask_provenance_cannot_be_replaced_by_wrong_shape(self):
        bad = np.zeros((240, 149), bool)
        with self.assertRaisesRegex(ValueError, "BLOCKED_S2_NEURAL_MASK_SHAPE"):
            independent_regions(self.rgb, self.palette,
                                [(0.9, 0.95, "bad", bad)])

    def test_neural_mask_ownership_not_from_g32(self):
        mask = np.zeros((240, 150), bool)
        mask[70:105, 70:94] = True
        _, bg, _, info = independent_regions(
            self.rgb, self.palette, [(0.9, 0.95, "real-index", mask)])
        self.assertGreater(info["neural_owned_pixels"], 0)
        self.assertLessEqual(info["neural_owned_pixels"], mask.sum())
        self.assertFalse(bg[75, 75])

    def test_source_gate_is_separate_from_native_and_requires_deltaE(self):
        g = np.full((240, 150), BG, dtype=np.uint8)
        g[30:150, 25:115] = 1
        m = np.zeros((240, 150), bool)
        m[70:105, 70:94] = True
        report = evaluate(self.rgb, self.palette, [(0.9, 0.95, "x", m)], g)
        self.assertEqual(set(report["gates"]), {
            "component_reduction_ge25pct", "mean_deltaE00_growth_le1",
            "palette_le32", "background_drift_le2pct_roi",
            "neural_owned_at_least1pct_foreground"})
        self.assertIn("mean_deltaE00_growth_le1", report["gates"])
        self.assertEqual(PARAMS["slic_n_segments"], 240)
        self.assertEqual(BG, 30)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""S3 original source color-graph and immutable native V44-B archive preflight."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

from run_engine001_color32_neural_s3_joint import (
    BG, PARAMS, read_immutable_contour, optional_native_contour, solve_region_colors,
)


class S3ImmutableContours(unittest.TestCase):
    def test_bad_archive_must_fail_closed_before_native_guide_use(self):
        with tempfile.TemporaryDirectory() as tmp:
            wrong = Path(tmp) / "fake-v44b.zip"
            wrong.write_bytes(b"not the authenticated V44-B")
            with self.assertRaisesRegex(ValueError, "BLOCKED_S3_CONTOUR_ZIP_SHA"):
                read_immutable_contour(wrong)

    def test_bad_native_contour_blocks_j1_but_keeps_j0_control(self):
        with tempfile.TemporaryDirectory() as tmp:
            wrong = Path(tmp) / "unverified-V44B.zip"
            wrong.write_bytes(b"not the native source")
            ink, evidence = optional_native_contour(wrong)
            self.assertIsNone(ink)
            self.assertEqual(evidence["status"], "BLOCKED_CONTOUR_PROVENANCE")
            self.assertEqual(evidence["reason"], "BLOCKED_S3_CONTOUR_ZIP_SHA")
            missing, evidence2 = optional_native_contour(None)
            self.assertIsNone(missing)
            self.assertEqual(evidence2["status"], "BLOCKED_CONTOUR_PROVENANCE")

    @staticmethod
    def fixture():
        palette = np.zeros((32, 3), np.uint8)
        palette[BG] = [255, 255, 255]
        palette[1] = [224, 128, 118]
        palette[2] = [29, 29, 29]
        palette[3] = [226, 0, 133]
        rgb = np.full((240, 150, 3), 255, np.uint8)
        rgb[40:110, 30:100] = [220, 126, 116]
        rgb[40:110, 100:130] = [24, 24, 24]
        regions = np.full((240, 150), -1, np.int32)
        regions[40:110, 30:100] = 0
        regions[40:110, 100:130] = 1
        ink = np.zeros((240, 150), bool)
        ink[45:104, 99] = True
        return rgb, palette, regions, ink

    def test_empty_original_background_is_not_painted(self):
        rgb, palette, region_ids, ink = self.fixture()
        out, evidence = solve_region_colors(
            rgb, palette, region_ids, ink, use_contour=False,
            chroma_penalty=True)
        self.assertTrue(np.all(out[region_ids < 0] == BG))
        self.assertEqual(out.dtype, np.uint8)
        self.assertEqual(out.shape, (240, 150))
        self.assertTrue(np.all(out < 32))
        self.assertFalse(evidence["contour_used_for_color_prior"])

    def test_native_outline_prior_does_not_modify_shape_or_palette(self):
        rgb, palette, regions, ink = self.fixture()
        source_copy = ink.copy()
        out, evidence = solve_region_colors(
            rgb, palette, regions, ink, use_contour=True, chroma_penalty=True)
        self.assertTrue(np.array_equal(ink, source_copy))
        self.assertTrue(np.all(out[regions < 0] == BG))
        self.assertTrue(np.all(out < 32))
        self.assertTrue(evidence["contour_used_for_color_prior"])

    def test_chroma_unary_is_explicit_ablation_not_neural_model(self):
        rgb, palette, regions, ink = self.fixture()
        _, x = solve_region_colors(rgb, palette, regions, ink,
                                   use_contour=False, chroma_penalty=False)
        _, y = solve_region_colors(rgb, palette, regions, ink,
                                   use_contour=False, chroma_penalty=True)
        self.assertFalse(x["chroma_excess_penalty"])
        self.assertTrue(y["chroma_excess_penalty"])
        self.assertIn("NOT_NEURAL", x["solver"])
        self.assertEqual(PARAMS["icm_sweeps"], 3)

    def test_invalid_dimensions_are_rejected(self):
        rgb, palette, regions, ink = self.fixture()
        with self.assertRaisesRegex(ValueError, "BLOCKED_S3_SOURCE_SHAPE"):
            solve_region_colors(rgb, palette, regions[:, :-1], ink,
                                use_contour=False, chroma_penalty=False)


if __name__ == "__main__":
    unittest.main()

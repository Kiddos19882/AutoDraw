#!/usr/bin/env python3
"""S5-P3 independent synthetic contracts, not evidence of pretrained inference."""
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from run_engine001_s5p3_pretrained_six_recolor import (
    GOOGLE_DRIVE_CHECKPOINT_ID, SOURCE_PALETTE_SIZE, UPSTREAM_SHA,
    check_output, run, six_source_colors,
)


class S5P3NativeSixRecolor(unittest.TestCase):
    @staticmethod
    def source():
        rng = np.random.default_rng(1198)
        return rng.integers(0, 256, (240, 150, 3), dtype=np.uint8)

    def test_pinned_source_and_pretrained_model_identity(self):
        self.assertEqual(len(UPSTREAM_SHA), 40)
        self.assertEqual(GOOGLE_DRIVE_CHECKPOINT_ID, "1dLir8CG_BdsSfxCKlHDgpOPShKpWooRr")
        self.assertEqual(SOURCE_PALETTE_SIZE, 6)

    def test_six_distinct_deterministic_palette_colors(self):
        rgb = self.source()
        copied = rgb.copy()
        a, b = six_source_colors(rgb), six_source_colors(rgb)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 6)
        self.assertEqual(len({tuple(c) for c in a}), 6)
        self.assertTrue(np.array_equal(rgb, copied))

    def test_bad_shape_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_IMAGE_SHAPE"):
            six_source_colors(np.zeros((239, 150, 3), np.uint8))

    def test_inference_result_requires_real_rgb_change(self):
        rgb = self.source()
        with self.assertRaisesRegex(ValueError, "NEURAL_NO_EFFECT"):
            check_output(Image.fromarray(rgb, "RGB"), rgb)
        wrong = Image.new("RGB", (151, 240))
        with self.assertRaisesRegex(ValueError, "INFERENCE_OUTPUT_SIZE"):
            check_output(wrong, rgb)

    def test_source_result_is_valid_rgb_not_six_color_quantizer(self):
        rgb = self.source()
        img = Image.fromarray(255-rgb, "RGB")
        stats = check_output(img, rgb)
        self.assertGreater(stats["unique_output_rgb_colors"], 6)
        self.assertEqual(stats["visual_user_review"], "PENDING")
        self.assertEqual(stats["model_output"], "REAL_PRETRAINED_FULL_RGB_NOT_GAME32")

    def test_no_output_overwrite_and_missing_checkpoint_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            output = root / "exists"
            output.mkdir()
            with self.assertRaisesRegex(ValueError, "NO_OVERWRITE"):
                run(root/"missing.png", root/"missing.pt", root, output)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""S5-P2 synthetic foreground mask contracts; NOT a simulated pretrained model."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

from run_engine001_color32_s5p2_birefnet import (
    EXPECTED_ONNX_MD5, MODEL, foreground_metrics, run,
)


class BiRefNetForegroundContracts(unittest.TestCase):
    def test_authentic_model_identity(self):
        self.assertEqual(MODEL, "birefnet-general-lite")
        self.assertEqual(EXPECTED_ONNX_MD5, "4fab47adc4ff364be1713e97b7e66334")

    def test_valid_binary_segmentation_is_descriptive(self):
        rgb = np.full((240, 150, 3), 255, np.uint8)
        alpha = np.zeros((240, 150), np.uint8)
        alpha[:, 30:120] = 230
        stats = foreground_metrics(alpha, rgb)
        self.assertEqual(stats["feasibility_gate"], "PASS")
        self.assertEqual(stats["boundary_pixels_at_128"], 480)
        self.assertEqual(stats["foreground_fraction_by_threshold"]["128"], .6)

    def test_extremely_small_mask_fails_feasibility(self):
        rgb = np.zeros((240, 150, 3), np.uint8)
        alpha = np.zeros((240, 150), np.uint8)
        alpha[0:10, 0:10] = 255
        stats = foreground_metrics(alpha, rgb)
        self.assertEqual(stats["feasibility_gate"], "FAIL")

    def test_wrong_shape_and_constant_masks_fail_closed(self):
        rgb = np.zeros((240, 150, 3), np.uint8)
        with self.assertRaisesRegex(ValueError, "INVALID_ALPHA_OR_RGB"):
            foreground_metrics(np.zeros((240, 149), np.uint8), rgb)
        with self.assertRaisesRegex(ValueError, "CONSTANT_MASK"):
            foreground_metrics(np.full((240, 150), 255, np.uint8), rgb)

    def test_no_output_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "already_exists"
            output.mkdir()
            with self.assertRaisesRegex(ValueError, "NO_OVERWRITE"):
                run(Path(d) / "nonexistent", output)


if __name__ == "__main__":
    unittest.main()

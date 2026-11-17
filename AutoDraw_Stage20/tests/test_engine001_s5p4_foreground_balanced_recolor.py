#!/usr/bin/env python3
"""E2 synthetic contracts for S5-P4, not proof of neural inference."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

from run_engine001_s5p4_foreground_balanced_recolor import (
    EXPECTED_MASK_SHA256, EXPECTED_RECOLOR_SHA256, EXP,
    run, six_balanced_source_colors,
)


class S5P4ForegroundBalanced(unittest.TestCase):
    @staticmethod
    def fixture():
        rgb = np.full((240, 150, 3), 255, dtype=np.uint8)
        alpha = np.zeros((240, 150), dtype=np.uint8)
        palette = [
            (240, 110, 20), (225, 50, 45), (25, 35, 100),
            (35, 155, 55), (170, 55, 165), (230, 195, 80),
            (65, 110, 170), (140, 70, 40),
        ]
        alpha[35:225, 10:140] = 255
        for j, color in enumerate(palette):
            rgb[35 + (j // 4) * 90: 35 + ((j // 4) + 1) * 90,
                10 + (j % 4) * 32: 10 + ((j % 4) + 1) * 32] = color
        return rgb, alpha

    def test_pinned_identity(self):
        self.assertEqual(len(EXPECTED_MASK_SHA256), 64)
        self.assertEqual(len(EXPECTED_RECOLOR_SHA256), 64)
        self.assertIn("S5_P4", EXP)

    def test_deterministic_six_distinct_one_nearwhite(self):
        rgb, alpha = self.fixture()
        copy = rgb.copy()
        a = six_balanced_source_colors(rgb, alpha)
        b = six_balanced_source_colors(rgb, alpha)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 6)
        self.assertEqual(len(set(tuple(c) for c in a)), 6)
        self.assertTrue(all(v >= 245 for v in a[0]))
        self.assertEqual(sum(all(v >= 245 for v in c) for c in a), 1)
        self.assertTrue(np.array_equal(copy, rgb))
        self.assertTrue(all(all(0 <= v <= 255 for v in c) for c in a))

    def test_foreground_guidance_changes_palette(self):
        rgb, alpha = self.fixture()
        base = six_balanced_source_colors(rgb, alpha)
        modified = rgb.copy()
        modified[(alpha > 128) & (modified[:, :, 0] > 160)] = (35, 85, 125)
        other = six_balanced_source_colors(modified, alpha)
        self.assertNotEqual(base, other)

    def test_invalid_shapes_and_constant_mask_rejected(self):
        rgb, alpha = self.fixture()
        with self.assertRaisesRegex(ValueError, "SOURCE_SHAPE"):
            six_balanced_source_colors(rgb[1:], alpha)
        with self.assertRaisesRegex(ValueError, "ALPHA_SHAPE"):
            six_balanced_source_colors(rgb, alpha[1:])
        with self.assertRaisesRegex(ValueError, "CONSTANT_ALPHA"):
            six_balanced_source_colors(rgb, np.full_like(alpha, 255))

    def test_missing_background_and_missing_foreground_fail_closed(self):
        rgb, alpha = self.fixture()
        no_white = rgb.copy()
        no_white[alpha == 0] = (90, 90, 90)
        with self.assertRaisesRegex(ValueError, "BACKGROUND_OR_FOREGROUND"):
            six_balanced_source_colors(no_white, alpha)
        no_fg = rgb.copy()
        no_fg[alpha > 0] = (255, 255, 255)
        with self.assertRaisesRegex(ValueError, "BACKGROUND_OR_FOREGROUND"):
            six_balanced_source_colors(no_fg, alpha)

    def test_output_is_immutable_and_checksum_preconditions_fail(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            out = root / "out"
            out.mkdir()
            with self.assertRaisesRegex(ValueError, "NO_OVERWRITE"):
                run(root / "missing.png", root / "missing.pt", root, out)


if __name__ == "__main__":
    unittest.main()

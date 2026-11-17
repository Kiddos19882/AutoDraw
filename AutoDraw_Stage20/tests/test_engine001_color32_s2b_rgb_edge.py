#!/usr/bin/env python3
"""Regression tests for ENGINE-001 S2b source-only, no native brush claims."""
import hashlib
import tempfile
import unittest
from pathlib import Path

import numpy as np

from run_engine001_palette32_region_study import read_palette
from run_engine001_color32_s2_edge_protection import s1_rgb_gradient_overlap
from run_engine001_color32_s2b_rgb_edge import EXP, assess, run

ROOT = Path(__file__).resolve().parents[1]


def sample(overlap, components, de):
    return {
        "rgb_gradient_overlap_percent": overlap,
        "components": {"all_4_connected_components": components},
        "quality": {"mean_delta_e00": de},
    }


class S2BTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = ROOT / "testImages/wV6VeZI9S1Y.png"
        cls.palette = ROOT / "data/palettes/browser_palette.json"

    def test_s1_gradient_identity_and_unrelated_control(self):
        rng = np.random.default_rng(20261117)
        image = rng.integers(0, 256, size=(240, 150, 3), dtype=np.uint8)
        unrelated = rng.integers(0, 256, size=image.shape, dtype=np.uint8)
        self.assertAlmostEqual(s1_rgb_gradient_overlap(image, image), 100.0)
        self.assertLess(s1_rgb_gradient_overlap(image, unrelated), 50.0)

    def test_gate_positive_and_precisely_negative_controls(self):
        b = sample(86.166667, 2369, 5.44375)
        e = sample(84.416667, 1044, 5.55870)
        g = sample(85.333333, 1339, 5.53142)
        passed = assess(b, e, g, True)
        self.assertTrue(passed["passed"])
        self.assertGreaterEqual(passed["rgb_edge_G_recovery_pp"], 0.875)
        self.assertFalse(assess(b, e, sample(85.2, 1339, 5.53142), True)["passed"])
        self.assertFalse(assess(b, e, sample(85.333333, 1700, 5.53142), True)["passed"])
        self.assertFalse(assess(b, e, sample(85.333333, 1339, 5.8), True)["passed"])
        self.assertFalse(assess(b, e, g, False)["passed"])

    def test_input_is_actual32_game_swatch_profile(self):
        colors = read_palette(self.palette)
        self.assertEqual(colors.shape, (32, 3))
        self.assertEqual(len({tuple(x) for x in colors}), 32)
        self.assertEqual(colors[30].tolist(), [255, 255, 255])
        self.assertEqual(colors[31].tolist(), [27, 27, 27])

    def test_real_frozen_source_generates_hashes_without_native_claims(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "s2b-output"
            report = run(self.source, self.palette, out)
            self.assertEqual(report["experiment"], EXP)
            self.assertEqual(report["visual_review"], "PENDING")
            self.assertEqual(report["native_Egret_fill"], "NOT_RUN")
            self.assertIsNone(report["exact_CHALK"])
            self.assertFalse(report["production_accepted"])
            self.assertEqual(report["input_source_sha256"],
                             "07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a")
            self.assertEqual(len(report["variants"]), 3)
            self.assertEqual(report["settings"]["game_colors"], 32)
            self.assertIn(report["status"], ("SOURCE_GATE_PASS_VISUAL_PENDING", "SOURCE_GATE_FAIL"))
            for name, digest in report["file_sha256"].items():
                self.assertEqual(hashlib.sha256((out / name).read_bytes()).hexdigest(), digest)
            with self.assertRaisesRegex(ValueError, "BLOCKED_OUTPUT_EXISTS"):
                run(self.source, self.palette, out)


if __name__ == "__main__":
    unittest.main()

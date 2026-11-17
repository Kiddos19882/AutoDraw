#!/usr/bin/env python3
"""Regression controls for source-only COLOR32-S2, not real brush evidence."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

from run_engine001_palette32_region_study import ROI_WH, read_palette
from run_engine001_color32_s2_edge_protection import (
    EXP, protected_merge, source_gate, run, strong_edges, s1_rgb_gradient_overlap,
)

ROOT = Path(__file__).resolve().parents[1]


class EdgeProtectedS2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.palette_file = ROOT / "data/palettes/browser_palette.json"
        cls.palette = read_palette(cls.palette_file)
        cls.source_file = ROOT / "testImages/wV6VeZI9S1Y.png"

    def test_protected_region_preserved_and_unprotected_similar_region_merged(self):
        source = np.full((ROI_WH[1], ROI_WH[0], 3), 255, np.uint8)
        idx = np.full((ROI_WH[1], ROI_WH[0]), 30, np.uint8)
        idx[60, 30] = 29
        idx[120, 75] = 29
        mask = np.zeros(idx.shape, bool)
        mask[60, 30] = True
        result, stats = protected_merge(source, idx, self.palette, mask)
        self.assertEqual(int(result[60, 30]), 29)
        self.assertEqual(int(result[120, 75]), 30)
        self.assertGreater(sum(stats["edge_blocked_per_pass"]), 0)
        np.testing.assert_array_equal(result[mask], idx[mask])

    def test_deterministic_strong_source_edges(self):
        img = np.full((ROI_WH[1], ROI_WH[0], 3), 255, np.uint8)
        img[:, :50] = 27
        a, ta = strong_edges(img)
        b, tb = strong_edges(img)
        np.testing.assert_array_equal(a, b)
        self.assertEqual(ta, tb)
        self.assertGreater(np.count_nonzero(a), 0)
        self.assertLess(np.count_nonzero(a), img.shape[0] * img.shape[1])

    def test_legacy_rgb_gradient_diagnostic_distinct_from_s2_boundary_metric(self):
        original = np.full((ROI_WH[1], ROI_WH[0], 3), 255, dtype=np.uint8)
        original[:, :50] = 27
        self.assertAlmostEqual(s1_rgb_gradient_overlap(original, original), 100.0)
        flat = np.full_like(original, 255)
        self.assertLess(s1_rgb_gradient_overlap(original, flat), 100.0)

    def test_gate_negative_and_positive_does_not_rewrite_thresholds(self):
        def item(edge, comps, de):
            return {"edge_overlap_percent": edge, "components": {"all_4_connected_components": comps},
                    "quality": {"mean_delta_e00": de}}
        b, e = item(86.16, 2369, 5.44), item(84.41, 1044, 5.56)
        fail = source_gate(b, e, item(84.42, 1100, 5.55))
        self.assertFalse(fail["passed"])
        self.assertFalse(fail["edge_gate"])
        good = source_gate(b, e, item(85.4, 1600, 5.57))
        self.assertTrue(good["passed"])

    def test_frozen_source_and_palette_run_outputs_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "new"
            report = run(self.source_file, self.palette_file, out)
            self.assertEqual(report["experiment"], EXP)
            self.assertEqual(report["actual_game_swatch_count"], 32)
            self.assertFalse(report["production_accepted"])
            self.assertEqual(report["native_Egret_fill"], "NOT_RUN")
            self.assertIsNone(report["exact_CHALK"])
            self.assertEqual(len(report["variants"]), 3)
            self.assertIn("NOT equivalent", report["edge_metric_disclaimer"])
            for v in report["variants"].values():
                self.assertGreaterEqual(v["historical_S1_RGB_gradient_overlap_percent"], 0.0)
                self.assertLessEqual(v["historical_S1_RGB_gradient_overlap_percent"], 100.0)
            self.assertTrue((out / "G_edge_protected32_indices.png").is_file())
            self.assertEqual(report["variants"]["B_frozen_direct32"]["changed_from_B_pixels"], 0)
            self.assertGreaterEqual(report["protected_pixels"], 1)
            self.assertTrue(all(v["components"]["used_game_swatches_or_adaptive_colors"] <= 32
                                for v in report["variants"].values()))
            for p, digest in report["report_linked_SHA256"].items():
                import hashlib
                self.assertEqual(hashlib.sha256((out / p).read_bytes()).hexdigest(), digest)
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                run(self.source_file, self.palette_file, out)

    def test_fail_closed_geometry(self):
        bad = np.zeros((8, 8), dtype=np.uint8)
        mask = np.zeros((8, 8), dtype=bool)
        with self.assertRaisesRegex(ValueError, "BLOCKED_INVALID_S2_INPUT"):
            protected_merge(np.zeros((8,8,3), dtype=np.uint8), bad, self.palette, mask)


if __name__ == "__main__":
    unittest.main()

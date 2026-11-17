#!/usr/bin/env python3
"""NEURAL-S1 deterministic source-region adapter tests (NOT neural inference)."""
import unittest

import numpy as np

from run_engine001_color32_neural_s1 import (
    BG, MAX_MASKS, apply_masks, source_metrics, source_gate,
)


class NeuralS1SourceContracts(unittest.TestCase):
    def setUp(self):
        self.palette = np.zeros((32, 3), dtype=np.uint8)
        self.palette[BG] = [255, 255, 255]
        self.palette[3] = [255, 0, 0]
        self.palette[4] = [0, 255, 0]
        self.rgb = np.full((240, 150, 3), 255, np.uint8)
        self.rgb[20:50, 30:70] = [250, 0, 0]
        self.g = np.full((240, 150), BG, np.uint8)
        self.g[20:50, 30:70] = 3

    def test_neural_mask_changes_only_original_nonbackground(self):
        m = np.zeros((240, 150), bool)
        m[10:60, 20:80] = True
        out, info = apply_masks(
            self.rgb, self.palette, self.g, [(0.9, 0.96, int(m.sum()), "m0", m)])
        self.assertTrue(np.all(out[self.g == BG] == BG))
        self.assertEqual(info["accepted_masks"], 1)
        self.assertEqual(out[35, 35], 3)

    def test_protected_edges_are_exactly_preserved(self):
        m = np.zeros((240, 150), bool)
        m[20:50, 30:70] = True
        self.rgb[35, 35] = [0, 255, 0]
        protected = np.zeros(self.g.shape, bool)
        protected[35, 35] = True
        out, stats = apply_masks(
            self.rgb, self.palette, self.g, [(0.9, 0.96, int(m.sum()), "m0", m)],
            protected)
        self.assertEqual(out[35, 35], 3)
        self.assertEqual(stats["restored_protected_pixels"], 1)

    def test_invalid_mask_shape_rejected(self):
        bad = np.zeros((240, 149), bool)
        with self.assertRaisesRegex(ValueError, "BLOCKED_NEURAL_S1_MASK_SHAPE"):
            apply_masks(self.rgb, self.palette, self.g, [(0.9, 0.9, 10, "bad", bad)])

    def test_baseline_diagnostics_and_source_gates_are_not_native(self):
        protected = np.zeros(self.g.shape, bool)
        metrics = source_metrics(self.rgb, self.g, self.palette, protected, self.g)
        self.assertGreater(metrics["components4_non_background"], 0)
        self.assertEqual(metrics["g32_protected_pixels_changed"], 0)
        self.assertTrue(source_gate(metrics, metrics, edge_protected=True)[
            "palette_le32"])
        self.assertFalse(source_gate(metrics, metrics, edge_protected=True)[
            "component_reduction_ge25pct"])

    def test_frozen_resource_caps_not_changed_by_adapter(self):
        self.assertEqual(MAX_MASKS, 32)
        self.assertEqual(BG, 30)


if __name__ == "__main__":
    unittest.main()

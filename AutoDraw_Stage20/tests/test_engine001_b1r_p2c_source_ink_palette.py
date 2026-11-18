#!/usr/bin/env python3
"""B1-R-P2C pinned RGB palette and immutable source-line regression contracts."""
import ast
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
from PIL import Image

import run_engine001_b1r_p2c_source_ink_palette as p2c


def fixture():
    """Many true RGB values and thin edges; no frozen historic candidate."""
    a = np.full(p2c.FULL_SHAPE, (246, 238, 230), dtype=np.uint8)
    rng = np.random.default_rng(47)
    a[25:155, 20:100] = [75, 52, 50]
    a[65:215, 95:190] = [205, 157, 138]
    a[215:301, 20:176] = [237, 218, 198]
    # Variation inside original regions required to exercise ink compression.
    noise = rng.integers(-13, 14, size=a[65:215, 95:190].shape)
    a[65:215, 95:190] = np.clip(
        a[65:215, 95:190].astype(np.int16) + noise, 0, 255).astype(np.uint8)
    a[86:90, 115:160] = [27, 16, 21]
    a[116:118, 110:170] = [51, 36, 32]
    a[42:47, 43:88] = [19, 12, 13]
    return a


def fixed_mask():
    mask = np.zeros(p2c.FULL_SHAPE[:2], dtype=bool)
    mask[65:215, 95:190] = True
    return mask


class P2CSourceContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = fixture()
        cls.mask = fixed_mask()
        cls.flat = np.full(p2c.FULL_SHAPE, (195, 160, 142), dtype=np.uint8)

    def test_01_frozen_source_and_budgets(self):
        self.assertEqual(p2c.EXPERIMENT,
                         "ENGINE001_B1R_P2C_SOURCE_INK_PALETTE_V1")
        self.assertEqual(p2c.VARIANTS, {"C_096": 96, "C_192": 192})
        self.assertEqual(p2c.CLUSTER_SEED, 1729)
        self.assertEqual(p2c.CLUSTER_ITERATIONS, 16)
        self.assertEqual(p2c.SOURCE_SHA256,
                         "07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a")

    def test_02_96_medoid_palette_deterministic(self):
        a, rgba, ledger = p2c.compress_source_ink(
            self.original, self.flat, self.mask, "C_096")
        b, rgba2, ledger2 = p2c.compress_source_ink(
            self.original, self.flat, self.mask, "C_096")
        self.assertTrue(np.array_equal(a, b))
        self.assertTrue(np.array_equal(rgba, rgba2))
        self.assertEqual(ledger, ledger2)
        self.assertEqual(len(ledger), 96)

    def test_03_palette192_source_pixels_only(self):
        full, rgba, ledger = p2c.compress_source_ink(
            self.original, self.flat, self.mask, "C_192")
        self.assertEqual(len(ledger), 192)
        allowed = {tuple(c) for c in np.unique(
            self.original[self.mask], axis=0)}
        self.assertTrue(all(tuple(c) in allowed for c in np.unique(
            full[self.mask], axis=0)))
        self.assertLessEqual(p2c.unique_rgb(full[self.mask]), 192)
        for item in ledger:
            x, y = item["source_full_xy"]
            self.assertTrue(self.mask[y, x])
            self.assertEqual(list(self.original[y, x]), item["source_RGB"])

    def test_04_mask_footprint_outside_unchanged(self):
        for variant in p2c.VARIANTS:
            full, rgba, _ = p2c.compress_source_ink(
                self.original, self.flat, self.mask, variant)
            self.assertTrue(np.array_equal(full[~self.mask],
                                           self.flat[~self.mask]))
            self.assertTrue(np.array_equal(
                rgba[..., 3] > 0, self.mask))
            self.assertTrue(np.all(rgba[self.mask, 3] == 255))
            self.assertLessEqual(
                p2c.unique_rgb(full),
                p2c.unique_rgb(self.flat) + p2c.VARIANTS[variant])

    def test_05_no_new_colors_under_discrete_resize(self):
        full, _, _ = p2c.compress_source_ink(
            self.original, self.flat, self.mask, "C_096")
        discrete = p2c.resample_discrete(full)
        self.assertEqual(discrete.shape, p2c.LOGICAL_SHAPE)
        self.assertLessEqual(p2c.unique_rgb(discrete),
                             p2c.unique_rgb(full))

    def test_06_unknown_budget_or_shape_rejected(self):
        with self.assertRaisesRegex(ValueError, "UNREGISTERED_VARIANT"):
            p2c.compress_source_ink(self.original, self.flat, self.mask, "G32")
        with self.assertRaisesRegex(ValueError, "SOURCE_INPUT_SHAPE"):
            p2c.compress_source_ink(self.original[:10], self.flat,
                                     self.mask, "C_096")
        with self.assertRaisesRegex(ValueError, "DISCRETE_SHAPE"):
            p2c.resample_discrete(self.original[:10])

    def test_07_no_ink_and_insufficient_unique_fail_closed(self):
        empty = np.zeros(p2c.FULL_SHAPE[:2], dtype=bool)
        with self.assertRaisesRegex(ValueError, "EMPTY_SOURCE_INK"):
            p2c.compress_source_ink(self.original, self.flat,
                                     empty, "C_096")
        constant = np.full(p2c.FULL_SHAPE, 90, dtype=np.uint8)
        with self.assertRaisesRegex(ValueError, "INSUFFICIENT_SOURCE_RGB"):
            p2c.compress_source_ink(constant, self.flat,
                                     self.mask, "C_192")

    def test_08_metrics_rejection_does_not_masquerade_as_native(self):
        original = p2c.logical_rgb(self.original)
        flat_logical = p2c.logical_region_map(self.flat)
        full, _, ledger = p2c.compress_source_ink(
            self.original, self.flat, self.mask, "C_096")
        preview = p2c.logical_composite(full)
        reference = p2c.logical_composite(self.original)
        nearest = p2c.resample_discrete(full)
        result = p2c.evaluate(
            original, self.flat, flat_logical,
            reference, full, preview, nearest,
            self.mask, ledger, 96)
        self.assertIn("source_original_lanczos", result)
        self.assertIn("p95_deltaE00", result["gates"])
        self.assertIn(result["status"],
                      {"SOURCE_SCREEN_PASS_VISUAL_PENDING", "SOURCE_GATE_FAIL"})

    def test_09_original_sha_cannot_be_bypassed(self):
        with tempfile.TemporaryDirectory() as t:
            source = Path(t) / "different.png"
            Image.fromarray(self.original).save(source)
            with self.assertRaisesRegex(ValueError, "ORIGINAL_SHA"):
                p2c.check_source(source)

    def test_10_no_legacy_runner_imports_or_linked_game(self):
        imports = set()
        tree = ast.parse(Path(p2c.__file__).read_text(encoding="utf8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imports.add(node.module)
            elif isinstance(node, ast.Import):
                imports.update(a.name for a in node.names)
        actual = {n for n in imports if n and n.startswith("run_engine001")}
        self.assertEqual(actual, {
            "run_engine001_b1r_p1_fullrgb_edge_aware",
            "run_engine001_b1r_p2_joint_region_outline",
            "run_engine001_b1r_p2b_residual_ink",
        })
        self.assertNotIn("game32_projection", p2c.VARIANTS)

    def test_11_reject_existing_output_before_reading_source(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError, "OVERWRITE"):
                p2c.run(Path(t) / "never-read.png", Path(t))


if __name__ == "__main__":
    unittest.main()

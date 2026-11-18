#!/usr/bin/env python3
"""P2D: source RGB bright-background guard and immutable detail contracts."""
import ast
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

import run_engine001_b1r_p2d_background_halo_guard as p2d


def synthetic():
    original = np.full(p2d.FULL_SHAPE, [255, 255, 255], dtype=np.uint8)
    flat = original.copy()
    ink = np.zeros(p2d.FULL_SHAPE[:2], dtype=bool)
    # Actual source-bright but falsely gray region at upper original border.
    flat[3:17, 99:114] = [227, 226, 221]
    # source dark line crossing background; may never be turned white.
    original[9, 90:126] = [65, 46, 50]
    ink[9, 90:126] = True
    # Inside non-border source-bright island deliberately separated by dark band.
    original[150:190, 40:80] = [55, 45, 50]
    original[160:177, 49:69] = [251, 251, 250]
    flat[160:177, 49:69] = [222, 218, 209]
    # Too-small source-white island inside source dark — D_COMPONENT24 must reject.
    original[200:219, 90:109] = [60, 42, 47]
    original[207:210, 97:100] = [252, 250, 247]
    flat[207:210, 97:100] = [222, 218, 209]
    return original, flat, ink


class P2DGuardSyntheticTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original, cls.flat, cls.ink = synthetic()

    def test_01_preregistered_task_identity_and_source(self):
        self.assertEqual(
            p2d.EXPERIMENT, "ENGINE001_B1R_P2D_SOURCE_BRIGHT_HALO_GUARD_V1")
        self.assertEqual(p2d.GUARD_VARIANTS, ("D_BORDER", "D_COMPONENT24"))
        self.assertEqual(p2d.HAIR_ROI_LOGICAL, (76, 4, 91, 19))
        self.assertEqual(p2d.SOURCE_HAIR_BASELINE_EXPECTED, 27)
        self.assertEqual(p2d.SOURCE_SHA256,
                         "07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a")

    def test_02_border_guard_repairs_source_bright_false_gray(self):
        mask, ledger = p2d.source_bright_guard(
            self.original, self.flat, self.ink, "D_BORDER")
        self.assertTrue(mask[5, 105])
        self.assertFalse(mask[9, 105])
        self.assertFalse(mask[164, 55])
        self.assertFalse(mask[208, 98])
        self.assertEqual(ledger["guard_changed_ink_pixels"], 0)
        self.assertEqual(ledger["corrected_rgb"], [255, 255, 255])

    def test_03_component24_allows_supported_source_interior(self):
        mask, ledger = p2d.source_bright_guard(
            self.original, self.flat, self.ink, "D_COMPONENT24")
        self.assertTrue(mask[5, 105])
        self.assertTrue(mask[164, 55])
        self.assertFalse(mask[208, 98])
        self.assertGreater(ledger["guard_source_pixels"], 24)

    def test_04_ink_rgb_unchanged_and_no_new_non_guard_edits(self):
        base = self.flat.copy()
        base[self.ink] = [41, 31, 31]
        for strategy in p2d.GUARD_VARIANTS:
            mask, _ = p2d.source_bright_guard(
                self.original, self.flat, self.ink, strategy)
            got = p2d.apply_source_bright_guard(
                self.original, base, self.ink, mask)
            self.assertTrue(np.array_equal(got[self.ink], base[self.ink]))
            self.assertTrue(np.array_equal(got[~mask], base[~mask]))
            self.assertTrue(np.all(got[mask] == self.original[0, 0]))
            self.assertLessEqual(p2d.unique_rgb(got),
                                 p2d.unique_rgb(base) + 1)

    def test_05_true_source_dark_lines_not_turned_white(self):
        for strategy in p2d.GUARD_VARIANTS:
            mask, _ = p2d.source_bright_guard(
                self.original, self.flat, self.ink, strategy)
            self.assertFalse(np.any(mask[9, 90:126]))
            self.assertFalse(mask[161, 40])
            self.assertFalse(mask[190, 40])

    def test_06_wrong_strategy_shape_and_dtype_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "UNKNOWN_STRATEGY"):
            p2d.source_bright_guard(self.original, self.flat, self.ink, "G32")
        with self.assertRaisesRegex(ValueError, "SOURCE_FORMAT"):
            p2d.source_bright_guard(self.original[:12], self.flat,
                                     self.ink, "D_BORDER")
        with self.assertRaisesRegex(ValueError, "SOURCE_FORMAT"):
            p2d.source_bright_guard(self.original, self.flat,
                                     self.ink.astype(np.uint8), "D_BORDER")

    def test_07_invalid_white_swatch_fail_closed(self):
        original = self.original.copy()
        original[0, 0] = [11, 13, 15]
        with self.assertRaisesRegex(ValueError, "SOURCE_WHITE_SWATCH"):
            p2d.source_bright_guard(original, self.flat, self.ink, "D_BORDER")

    def test_08_apply_rejects_guard_ink_overlap_and_wrong_dimensions(self):
        guard, _ = p2d.source_bright_guard(
            self.original, self.flat, self.ink, "D_BORDER")
        overlap = guard.copy()
        overlap[9, 105] = True
        with self.assertRaisesRegex(ValueError, "GUARD_OVERLAPS_INK"):
            p2d.apply_source_bright_guard(
                self.original, self.flat, self.ink, overlap)
        with self.assertRaisesRegex(ValueError, "APPLY_SHAPE"):
            p2d.apply_source_bright_guard(
                self.original, self.flat[:10], self.ink, guard)

    def test_09_marked_hair_report_counts_only_bright_false_dark(self):
        original = np.full((240, 150, 3), 255, dtype=np.uint8)
        candidate = original.copy()
        candidate[4:7, 76:80] = [227, 226, 221]
        candidate[7, 81] = [30, 20, 40]
        original[7, 81] = [30, 20, 40]
        count = p2d.hair_dark_count(original, candidate)
        self.assertEqual(count["false_dark_logical_pixels"], 12)
        self.assertEqual(count["marked_ROI_logical_xyxy"],
                         [76, 4, 91, 19])

    def test_10_wrong_source_sha_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            fake = Path(root) / "fake.png"
            Image.fromarray(self.original).save(fake)
            with self.assertRaisesRegex(ValueError, "ORIGINAL_SHA"):
                p2d.check_source(fake)

    def test_11_no_legacy_source_or_game_imports(self):
        tree = ast.parse(Path(p2d.__file__).read_text(encoding="utf8"))
        source_runners = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("run_engine001"):
                    source_runners.add(node.module)
        self.assertEqual(source_runners, {
            "run_engine001_b1r_p1_fullrgb_edge_aware",
            "run_engine001_b1r_p2_joint_region_outline",
            "run_engine001_b1r_p2b_residual_ink",
            "run_engine001_b1r_p2c_source_ink_palette",
        })

    def test_13_manual_guard_cannot_whiten_real_source_dark(self):
        guard = np.zeros(p2d.FULL_SHAPE[:2], dtype=bool)
        guard[9, 105] = True
        no_ink = np.zeros_like(self.ink)
        with self.assertRaisesRegex(ValueError, "NON_SOURCE_BRIGHT_MASK"):
            p2d.apply_source_bright_guard(
                self.original, self.flat, no_ink, guard)

    def test_12_overwrite_not_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "OVERWRITE"):
                p2d.run(Path(tmp) / "no-access.png", Path(tmp))


if __name__ == "__main__":
    unittest.main()

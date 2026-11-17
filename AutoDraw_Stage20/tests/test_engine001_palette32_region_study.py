#!/usr/bin/env python3
"""REGRESSION: 32 genuine game swatches; six offline variants; no Egret claims."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from run_engine001_palette32_region_study import (
    EXP, ROI_WH, SOURCE_SHA, PARAMS, nearest32, read_palette, read_source,
    run, tiny_region_merge,
)


ROOT = Path(__file__).resolve().parents[1]


class Palette32RegionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = ROOT / "testImages/wV6VeZI9S1Y.png"
        cls.palette_file = ROOT / "data/palettes/browser_palette.json"
        cls.palette = read_palette(cls.palette_file)

    def test_frozen_source_and_exact_32_game_swatch_rgb(self):
        _, src = read_source(self.source)
        self.assertEqual(src.shape, (240, 150, 3))
        self.assertEqual(self.palette.shape, (32, 3))
        self.assertEqual(len({tuple(x) for x in self.palette}), 32)
        self.assertEqual(self.palette[30].tolist(), [255, 255, 255])
        self.assertEqual(self.palette[31].tolist(), [27, 27, 27])
        mapped = nearest32(self.palette.reshape(1, 32, 3), self.palette)
        np.testing.assert_array_equal(mapped[0], np.arange(32))
        self.assertEqual(SOURCE_SHA, "07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a")

    def test_tiny_compatible_component_merges_but_high_contrast_is_preserved(self):
        arr = np.full((ROI_WH[1], ROI_WH[0], 3), 255, dtype=np.uint8)
        idx = np.full((ROI_WH[1], ROI_WH[0]), 30, dtype=np.uint8)
        idx[120, 75] = 29
        merged, changes = tiny_region_merge(
            arr, idx, self.palette, max_area=8,
            max_extra_delta_e00=5.0, iterations=2)
        self.assertEqual(int(merged[120, 75]), 30)
        self.assertGreater(sum(changes), 0)
        arr[120, 75] = [27, 27, 27]
        idx[120, 75] = 31
        protected, _ = tiny_region_merge(
            arr, idx, self.palette, max_area=8,
            max_extra_delta_e00=5.0, iterations=2)
        self.assertEqual(int(protected[120, 75]), 31)

    def test_all_six_variants_and_digest_repeatability(self):
        with tempfile.TemporaryDirectory() as temp:
            out1, out2 = Path(temp) / "first", Path(temp) / "repeat"
            a = run(self.source, self.palette_file, out1)
            b = run(self.source, self.palette_file, out2)
            self.assertEqual(a, b)
            self.assertEqual(a["experiment"], EXP)
            self.assertEqual(set(a["variants"]), set(PARAMS))
            self.assertEqual(a["native_Egret_fill"], "NOT_RUN")
            self.assertFalse(a["production_accepted"])
            self.assertTrue(a["frozen_V44B_410_detail_untouched"])
            self.assertFalse(a["dither_used"])
            for name, metrics in a["variants"].items():
                self.assertEqual(len(metrics["used_palette_indices"]),
                                 metrics["components"]["used_game_swatches_or_adaptive_colors"])
                self.assertLessEqual(len(metrics["used_palette_indices"]), 32)
                self.assertTrue((out1 / f"{name}.png").is_file())
                self.assertTrue((out1 / f"{name}_indices.png").is_file())
                self.assertTrue((out1 / f"{name}_boundaries.png").is_file())
            self.assertLess(a["variants"]["E_regularized32"]["components"][
                "all_4_connected_components"],
                a["variants"]["B_direct32"]["components"]["all_4_connected_components"])
            self.assertGreater(a["variants"]["E_regularized32"]["quality"][
                "mean_delta_e00"], a["variants"]["B_direct32"]["quality"]["mean_delta_e00"])

    def test_fail_closed_source_and_palette_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            bad_src = Path(temp) / "wrong.png"
            bad_src.write_bytes(b"not the frozen png")
            with self.assertRaisesRegex(ValueError, "BLOCKED_SOURCE_DRIFT"):
                read_source(bad_src)
            bad_palette = Path(temp) / "wrong_palette.json"
            bad_palette.write_text(json.dumps({
                "colors": [{"rgb": [0,0,0], "hex": "#000000"}]}),
                encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "BLOCKED_PALETTE_DRIFT"):
                read_palette(bad_palette)
            with self.assertRaisesRegex(ValueError, "invalid tiny-region"):
                tiny_region_merge(np.zeros((240,150,3),np.uint8),
                                  np.zeros((50,50),np.uint8),self.palette,
                                  max_area=8,max_extra_delta_e00=5,iterations=2)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Deterministic source-color contracts for experimental ENGINE-001 COLOR-ISLAND-R1."""
from __future__ import annotations
import unittest
from pathlib import Path

import numpy as np

from run_engine001_color_island_r1 import (
    BG, EXP, G32_SHA, CHROMA_EXTRA, SHAPE,
    cleanup_regions, count_nonbackground, project_game32,
    rgb_regions, unsupported_accent_pixels, validate,
)
from run_engine001_palette32_region_study import read_palette

ROOT = Path(__file__).resolve().parents[1]


class SourceAwareIslandContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.palette = read_palette(ROOT / 'data/palettes/browser_palette.json')

    def fixture(self):
        src = np.empty((*SHAPE, 3), np.uint8)
        src[:] = self.palette[31]  # dark region with no real magenta
        labels = np.zeros(SHAPE, np.int32)
        labels[:10] = -1
        src[:10] = self.palette[BG]
        return src, labels

    def test_fixed_pins_and_source_guards(self):
        self.assertTrue(EXP.endswith('SOURCE_AWARE_REGIONS'))
        self.assertEqual(len(G32_SHA), 64)
        self.assertEqual(CHROMA_EXTRA, 12.)
        src, _ = self.fixture()
        validate(src, self.palette)
        with self.assertRaisesRegex(ValueError, 'SHAPE_OR_GAME_PALETTE'):
            validate(src[:-1], self.palette)
        with self.assertRaisesRegex(ValueError, 'SHAPE_OR_GAME_PALETTE'):
            validate(src, self.palette[:-1])

    def test_false_pink_in_originally_dark_region_is_never_invented(self):
        src, labels = self.fixture()
        projected, report = project_game32(src, self.palette, labels)
        self.assertEqual(report['abstained_pixels'], 0)
        self.assertTrue(np.all(projected[10:] == 31))
        self.assertTrue(np.all(projected[:10] == BG))
        self.assertEqual(unsupported_accent_pixels(src, projected, self.palette)['pixels'], 0)
        false_g = projected.copy()
        false_g[80:85, 75:80] = 10
        self.assertGreater(unsupported_accent_pixels(src, false_g, self.palette)['pixels'], 0)

    def test_real_small_pink_detail_not_globally_banned(self):
        src, labels = self.fixture()
        src[100:103, 70:73] = self.palette[10]
        labels[100:103, 70:73] = 1
        projected, r = project_game32(src, self.palette, labels)
        self.assertEqual(r['abstained_pixels'], 0)
        self.assertTrue(np.all(projected[100:103, 70:73] == 10))
        clean, diag = cleanup_regions(src, labels, np.zeros(SHAPE, bool))
        self.assertTrue(np.all(clean[100:103, 70:73] == 1))
        self.assertEqual(diag['merged_regions'], 0)  # high-contrast edge is real

    def test_tiny_unprotected_same_color_region_merges_as_whole(self):
        src, labels = self.fixture()
        labels[100:102, 70:72] = 2
        original = labels.copy()
        result, diag = cleanup_regions(src, labels, np.zeros(SHAPE, bool))
        self.assertTrue(np.array_equal(labels, original))
        self.assertEqual(diag['changed_pixels'], 4)
        self.assertEqual(diag['merged_regions'], 1)
        self.assertTrue(np.all(result[100:102, 70:72] == 0))
        protected = np.zeros(SHAPE, bool)
        protected[100, 70] = True
        rejected, no_merge = cleanup_regions(src, labels, protected)
        self.assertEqual(no_merge['merged_regions'], 0)
        self.assertTrue(np.array_equal(rejected, labels))

    def test_true_narrow_detail_and_protected_edge_survive(self):
        src, labels = self.fixture()
        for k in range(4):
            labels[120 + k, 50 + k] = 3
            src[120 + k, 50 + k] = self.palette[4]
        protected = labels == 3
        result, report = cleanup_regions(src, labels, protected)
        self.assertTrue(np.array_equal(result[protected], labels[protected]))
        # Diagonal single pixels might be 4-disconnected, but never smoothed over.
        self.assertTrue(np.all(rgb_regions(src, result)[protected] == self.palette[4]))

    def test_unrepresentable_gray_is_reported_not_painted_pink_or_white(self):
        src, labels = self.fixture()
        src[80:115, 40:100] = [120, 120, 120]
        labels[80:115, 40:100] = 3
        idx, r = project_game32(src, self.palette, labels)
        self.assertGreater(r['abstained_pixels'], 0)
        self.assertTrue(np.all(idx[80:115, 40:100] == -1))
        self.assertIn('UNREPRESENTABLE_BY_GAME32', r['abstained_regions'][0]['reason'])

    def test_region_medoid_is_from_original_rgb_not_neural_recolor(self):
        src, labels = self.fixture()
        src[90:105, 70:90] = [245, 151, 1]
        labels[90:105, 70:90] = 4
        out = rgb_regions(src, labels)
        self.assertEqual(out.shape, src.shape)
        self.assertEqual(out.dtype, np.uint8)
        self.assertTrue(np.all(out[90:105, 70:90] == [245, 151, 1]))
        self.assertEqual(count_nonbackground(np.full(SHAPE, BG, np.int16))['components4'], 0)

    def test_invalid_region_shapes_fail_closed(self):
        src, labels = self.fixture()
        with self.assertRaisesRegex(ValueError, 'REGIONS_SHAPE'):
            project_game32(src, self.palette, labels[:-1])
        with self.assertRaisesRegex(ValueError, 'CLEANUP_SHAPE'):
            cleanup_regions(src, labels, np.zeros(SHAPE, dtype=np.uint8))


if __name__ == '__main__':
    unittest.main()

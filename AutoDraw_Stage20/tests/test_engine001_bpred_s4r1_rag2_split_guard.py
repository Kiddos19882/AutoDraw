#!/usr/bin/env python3
"""RAG2 original-source E2 regressions; NOT native Egret or source owner GT."""
from __future__ import annotations

import unittest
import numpy as np
from scipy import ndimage

from engine001_bpred_s4r1_rag2_split_guard import (
    build_rag2, _split_geometry, _rag_adjacency, evaluate_rag2)


def palette():
    p = np.array([(i * 37 % 256, i * 61 % 256, i * 103 % 256)
                  for i in range(128)], np.uint8)
    p[0] = [100, 100, 100]
    p[1] = [245, 245, 245]
    assert np.unique(p, axis=0).shape[0] == 128
    return p


def image(h=46, w=59):
    a = np.empty((h, w, 4), np.uint8)
    a[:, :, :3] = 100
    a[:, :, 3] = 255
    return a


class RAG2SourceTests(unittest.TestCase):
    def test_inside_slic_thin_real_detail_preserved(self):
        a = image()
        a[3:-3, 28, :3] = 245
        original = a.copy()
        r = build_rag2(a, palette())
        self.assertTrue(np.array_equal(a, original))
        self.assertNotEqual(int(r["game_index"][20, 28]), int(r["game_index"][20, 27]))
        self.assertNotEqual(int(r["region_ids"][20, 28]), int(r["region_ids"][20, 27]))
        self.assertGreater(r["counts"]["initial_split_regions"],
                           r["counts"]["initial_slic_regions"])
        self.assertEqual(r["source_owner_status"], "MISSING")
        self.assertIn("FORBIDDEN", r["stroke_admission"])

    def test_split_geometry_four_connectivity_and_region_vs_swatch(self):
        slic = np.ones((4, 7), np.int32)
        nearest = np.ones((4, 7), np.int16)
        nearest[:, 3] = 2
        nearest[1, 1] = 2
        out = _split_geometry(slic, nearest, np.ones(slic.shape, bool))
        # Different areas with the same swatch remain different geometric IDs.
        self.assertNotEqual(int(out[1, 1]), int(out[2, 3]))
        self.assertNotEqual(int(out[0, 1]), int(out[0, 5]))
        for i in np.unique(out[out > 0]):
            _, count = ndimage.label(out == i)
            self.assertEqual(count, 1)

    def test_weak_and_strong_actual_original_boundaries(self):
        labels = np.array([[1, 2, 2], [1, 2, 2]], np.int32)
        lab = np.zeros((2, 3, 3), np.float64)
        lab[:, 1:, 0] = 25
        pairs, lengths, contrast = _rag_adjacency(labels, lab)
        self.assertEqual(pairs.tolist(), [[1, 2]])
        self.assertEqual(lengths.tolist(), [2])
        self.assertGreater(float(contrast[0]), 12)

    def test_transparency_owner_is_not_guessed(self):
        a = image()
        a[4:10, 5:14, 3] = 0
        a[18:21, 20:24, 3] = 128
        old = a.copy()
        r = build_rag2(a, palette())
        self.assertTrue(np.array_equal(old, a))
        self.assertTrue(np.all(r["game_index"][a[:, :, 3] < 255] == -1))
        self.assertTrue(np.all(r["region_ids"][a[:, :, 3] < 255] == 0))
        self.assertTrue(np.array_equal(r["preview_rgba"][:, :, 3], a[:, :, 3]))

    def test_reproducibility_and_real_swatches(self):
        a = image(36, 52)
        a[:, 26:, :3] = [245, 245, 245]
        p = palette()
        r1, r2 = build_rag2(a, p), build_rag2(a, p)
        for key in ("region_ids", "game_index", "baseline_index",
                    "preview_rgba", "source_strong_edge"):
            self.assertTrue(np.array_equal(r1[key], r2[key]), key)
        self.assertEqual(r1["counts"], r2["counts"])
        self.assertTrue(np.array_equal(r1["preview_rgba"][:, :, :3],
                                       p[r1["game_index"]]))
        self.assertTrue(np.isfinite(evaluate_rag2(a, p, r1)["candidate_rgb_mae"]))

    def test_preserve_strong_pixel_detail_even_if_small(self):
        a = image()
        a[21, 30, :3] = 245
        r = build_rag2(a, palette())
        self.assertEqual(int(r["game_index"][21, 30]), 1)
        self.assertNotEqual(int(r["game_index"][21, 30]), int(r["game_index"][21, 29]))

    def test_all_transparent_and_single_row(self):
        a = image(8, 11)
        a[:, :, 3] = 0
        r = build_rag2(a, palette())
        self.assertTrue(np.all(r["game_index"] == -1))
        self.assertEqual(r["counts"]["final_regions"], 0)
        b = image(1, 11)
        q = build_rag2(b, palette())
        self.assertEqual(q["region_ids"].shape, (1, 11))

    def test_invalid_sources_and_palette_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "INVALID_ORIGINAL"):
            build_rag2(np.zeros((4, 3, 3), np.uint8), palette())
        with self.assertRaisesRegex(ValueError, "INVALID_PALETTE"):
            build_rag2(image(), np.zeros((128, 3), np.uint8))


if __name__ == "__main__":
    unittest.main()

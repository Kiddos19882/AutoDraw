#!/usr/bin/env python3
"""DEC-048 RAG1 E2: source-only invariant regressions, not native brush evidence."""
from __future__ import annotations

import unittest
import numpy as np
from scipy import ndimage

from engine001_bpred_s4r1_rag1_region_color import (
    build_rag1, count_color_islands, evaluate_rag1, _connected_relabel)


def palette():
    p = np.array([(i, (i * 37) % 256, (i * 83) % 256)
                  for i in range(128)], dtype=np.uint8)
    p[6] = (255, 255, 255)
    return p


def image(h=48, w=64, left=(0, 0, 0), right=(255, 255, 255)):
    a = np.full((h, w, 4), 255, np.uint8)
    a[:, :w // 2, :3] = left
    a[:, w // 2:, :3] = right
    return a


class Rag1SourceTests(unittest.TestCase):
    def test_strong_source_boundary_survives(self):
        data = image()
        b = data.copy()
        r = build_rag1(data, palette())
        self.assertTrue(np.array_equal(data, b))
        self.assertNotEqual(int(r["region_ids"][22, 9]),
                            int(r["region_ids"][22, 55]))
        self.assertNotEqual(int(r["game_index"][22, 9]),
                            int(r["game_index"][22, 55]))
        self.assertTrue(r["source_strong_edge"][:, 31:33].all())
        self.assertEqual(r["source_owner_status"], "MISSING")
        self.assertIn("FORBIDDEN", r["stroke_admission"])

    def test_determinism_and_all_pixels_have_real_swatch(self):
        a = image(37, 59, (40, 110, 200), (75, 112, 190))
        p = palette()
        r = build_rag1(a, p)
        rr = build_rag1(a, p)
        for name in ("region_ids", "game_index", "baseline_index", "preview_rgba"):
            self.assertTrue(np.array_equal(r[name], rr[name]), name)
        self.assertGreater(r["counts"]["initial_regions"], 0)
        self.assertLessEqual(r["counts"]["final_regions"], r["counts"]["initial_regions"])
        self.assertTrue(((r["game_index"] >= 0) & (r["game_index"] < 128)).all())
        self.assertTrue(np.array_equal(r["preview_rgba"][:, :, :3],
                                       p[r["game_index"]]))
        metrics = evaluate_rag1(a, p, r)
        self.assertEqual(metrics["opaque"], a.shape[0] * a.shape[1])

    def test_transparency_and_nonopaque_not_fabricated_owner(self):
        a = image()
        a[7:14, 16:24, 3] = 0
        a[21:23, 33:41, 3] = 100
        old = a.copy()
        r = build_rag1(a, palette())
        self.assertTrue(np.array_equal(a, old))
        self.assertTrue((r["region_ids"][a[:, :, 3] != 255] == 0).all())
        self.assertTrue((r["game_index"][a[:, :, 3] != 255] == -1).all())
        self.assertTrue(np.array_equal(r["preview_rgba"][:, :, 3], a[:, :, 3]))

    def test_all_transparent_and_single_row(self):
        a = image(12, 17)
        a[:, :, 3] = 0
        r = build_rag1(a, palette())
        self.assertEqual(r["counts"]["final_regions"], 0)
        self.assertTrue((r["game_index"] == -1).all())
        b = image(1, 17)
        result = build_rag1(b, palette())
        self.assertEqual(result["region_ids"].shape, (1, 17))

    def test_disconnected_duplicate_slic_ids_split(self):
        initial = np.zeros((5, 11), np.int32)
        initial[1:3, 1:3] = 1
        initial[2:4, 8:10] = 1
        result = _connected_relabel(initial, initial > 0)
        self.assertEqual(len(np.unique(result[result > 0])), 2)
        for ident in np.unique(result[result > 0]):
            _, n = ndimage.label(result == ident)
            self.assertEqual(n, 1)

    def test_island_metric_not_special_casing_white_index(self):
        owners = np.array([[6, 6, -1, 3], [6, 6, -1, 3]], np.int16)
        got = count_color_islands(owners)
        self.assertEqual(got["components"], 2)
        self.assertEqual(got["singletons"], 0)

    def test_invalid_source_palette(self):
        with self.assertRaisesRegex(ValueError, "INVALID_ORIGINAL"):
            build_rag1(np.zeros((4, 4, 3), np.uint8), palette())
        with self.assertRaisesRegex(ValueError, "INVALID_GAME_PALETTE"):
            build_rag1(image(), np.zeros((128, 3), np.uint8))


if __name__ == "__main__":
    unittest.main()

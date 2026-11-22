#!/usr/bin/env python3
"""RAG3 E2 synthetic invariants; deliberately no native/production claims."""
import unittest

import numpy as np
from scipy import ndimage

from engine001_bpred_s4r1_rag3_hierarchy import (
    build_rag3, evaluate_rag3, _connected, _boundary_stats,
)


def palette():
    p = np.array([(i * 37 % 256, i * 61 % 256, i * 103 % 256)
                  for i in range(128)], dtype=np.uint8)
    p[0] = (100, 100, 100)
    p[1] = (245, 245, 245)
    assert np.unique(p, axis=0).shape[0] == 128
    return p


def image(h=48, w=56):
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = (100, 100, 100)
    rgba[:, :, 3] = 255
    return rgba


class RAG3Tests(unittest.TestCase):
    def test_thin_strong_source_detail_survives_inside_surface(self):
        a = image()
        a[4:-4, 26, :3] = (245, 245, 245)
        before = a.copy()
        r = build_rag3(a, palette())
        self.assertTrue(np.array_equal(a, before))
        self.assertNotEqual(int(r["game_index"][18, 26]),
                            int(r["game_index"][18, 25]))
        self.assertTrue(r["source_edge"][18, 26])
        self.assertGreater(r["counts"]["detail_pixels"], 0)
        self.assertGreater(r["counts"]["detail_segments"], 0)
        self.assertTrue(np.all(r["unknown"]))
        self.assertIn("FORBIDDEN", r["stroke_admission"])

    def test_weak_same_color_noise_does_not_make_main_islands(self):
        a = image()
        a[22, 22, :3] = (101, 100, 100)
        a[21, 22, :3] = (102, 100, 100)
        r = build_rag3(a, palette())
        self.assertEqual(int(r["surface_id"][22, 22]),
                         int(r["surface_id"][22, 23]))
        self.assertEqual(int(r["detail_id"][22, 22]), 0)

    def test_main_and_detail_are_four_connected(self):
        a = image(57, 53)
        a[14:43, 27:29, :3] = (245, 245, 245)
        a[7:9, 9:14, :3] = (245, 245, 245)
        r = build_rag3(a, palette())
        for key in ("surface_id", "detail_id"):
            lab = r[key]
            for i in np.unique(lab[lab > 0]):
                _, n = ndimage.label(lab == i)
                self.assertEqual(n, 1, (key, int(i)))
        d = r["detail_id"]
        selected = d > 0
        parents = r["detail_parent_surface_id"]
        self.assertTrue(np.array_equal(parents[d[selected]],
                                       r["surface_id"][selected]))
        self.assertGreater(len(r["adjacency"].shape), 1)

    def test_swatch_and_geometry_are_separate_identifiers(self):
        a = image(48, 56)
        a[:, 27, 3] = 0
        r = build_rag3(a, palette())
        self.assertNotEqual(int(r["surface_id"][10, 10]),
                            int(r["surface_id"][10, 40]))
        self.assertEqual(int(r["game_index"][10, 10]),
                         int(r["game_index"][10, 40]))

    def test_original_alpha_and_no_unverified_stroke(self):
        a = image()
        a[3:11, 8:15, 3] = 0
        a[15:21, 23:29, 3] = 128
        before = a.copy()
        r = build_rag3(a, palette())
        invalid = a[:, :, 3] < 255
        self.assertTrue(np.array_equal(a, before))
        self.assertTrue(np.all(r["surface_id"][invalid] == 0))
        self.assertTrue(np.all(r["detail_id"][invalid] == 0))
        self.assertTrue(np.all(r["game_index"][invalid] == -1))
        self.assertTrue(np.array_equal(r["preview_rgba"][:, :, 3],
                                       a[:, :, 3]))
        self.assertEqual(r["source_owner_status"], "MISSING")
        self.assertIn("UNKNOWN", r["stroke_admission"])

    def test_identical_runs_and_true_game128(self):
        a = image(44, 56)
        a[10:33, 20:28, :3] = (245, 245, 245)
        p = palette()
        x = build_rag3(a, p)
        y = build_rag3(a, p)
        for key in ("surface_id", "detail_id", "surface_color_index",
                    "surface_color_table", "detail_parent_surface_id",
                    "detail_color_index", "game_index", "baseline_index",
                    "preview_rgba", "source_edge", "unknown", "adjacency"):
            self.assertTrue(np.array_equal(x[key], y[key]), key)
        self.assertEqual(x["counts"], y["counts"])
        mask = a[:, :, 3] == 255
        self.assertTrue(np.array_equal(x["preview_rgba"][:, :, :3][mask],
                                       p[x["game_index"][mask]]))
        self.assertTrue(np.isfinite(evaluate_rag3(a, p, x)["candidate_rgb_mae"]))

    def test_transparent_and_single_row(self):
        a = image(8, 11)
        a[:, :, 3] = 0
        r = build_rag3(a, palette())
        self.assertEqual(r["counts"]["main_surfaces"], 0)
        self.assertTrue(np.all(r["game_index"] == -1))
        one = build_rag3(image(1, 9), palette())
        self.assertEqual(one["surface_id"].shape, (1, 9))

    def test_true_adjacency_and_component_split(self):
        ids = np.array([[1, 1, 2], [1, 2, 2]], dtype=np.int32)
        lab = np.zeros((2, 3, 3), dtype=np.float64)
        lab[:, 2, 0] = 30
        pairs, length, mean, fraction = _boundary_stats(ids, lab)
        self.assertEqual(pairs.tolist(), [[1, 2]])
        self.assertEqual(int(length[0]), 3)
        self.assertGreaterEqual(float(mean[0]), 0)
        raw = np.array([[1, 0, 1], [1, 0, 1]], np.int32)
        connected = _connected(raw)
        self.assertNotEqual(int(connected[0, 0]), int(connected[0, 2]))

    def test_invalid_original_and_palette_blocked(self):
        with self.assertRaisesRegex(ValueError, "INVALID_ORIGINAL"):
            build_rag3(np.zeros((2, 2, 3), np.uint8), palette())
        with self.assertRaisesRegex(ValueError, "INVALID_PALETTE"):
            build_rag3(image(), np.zeros((128, 3), np.uint8))


if __name__ == "__main__":
    unittest.main()

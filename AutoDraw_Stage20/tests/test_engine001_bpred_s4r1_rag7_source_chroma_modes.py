#!/usr/bin/env python3
"""RAG7 source-only original-chroma mode / exact RGB L1 synthetic E2 gates."""
from __future__ import annotations

import unittest

import numpy as np
from scipy import ndimage
from skimage import color

from engine001_bpred_s4r1_rag7_source_chroma_modes import (
    _best_whole_region_l1, _connected_mode_proposal, _source_mode_refine,
    build_rag7, evaluate_rag7,
)


def game128():
    p = np.array([(i * 37 % 256, i * 61 % 256, i * 103 % 256)
                  for i in range(128)], np.uint8)
    p[0] = (100, 100, 100)
    p[1] = (245, 245, 245)
    p[2] = (102, 100, 100)
    assert len(np.unique(p, axis=0)) == 128
    return p


def original(h=56, w=64):
    img = np.full((h, w, 4), 255, np.uint8)
    img[:, :, :3] = (100, 100, 100)
    return img


class RAG7OriginalSourceTests(unittest.TestCase):
    def test_exact_rgb_l1_full128_matches_brute_force(self):
        rng = np.random.default_rng(1729)
        p = game128()
        for n in (1, 9, 50, 257):
            original_pixels = rng.integers(0, 256, (n, 3), dtype=np.uint8)
            best = _best_whole_region_l1(original_pixels, p)
            brute = np.abs(original_pixels.astype(np.int64)[:, None, :]
                           - p.astype(np.int64)[None, :, :]).sum(axis=(0, 2))
            self.assertEqual(best, int(np.argmin(brute)))
        self.assertEqual(_best_whole_region_l1(np.array([[100, 100, 100]], np.uint8), p), 0)

    def test_connected_source_chromatic_modes_have_true_two_parts(self):
        rgb = np.zeros((24, 28, 3), np.uint8)
        rgb[:12] = (70, 25, 45)
        rgb[12:] = (145, 95, 90)
        lab = color.rgb2lab(rgb.astype(np.float64) / 255.0)
        ans = _connected_mode_proposal(np.ones((24, 28), bool), lab)
        self.assertIsNotNone(ans)
        gain, membership = ans
        self.assertGreater(gain, 0)
        self.assertGreaterEqual(int(membership.sum()), 8)
        self.assertEqual(ndimage.label(membership)[1], 1)
        self.assertEqual(ndimage.label(~membership)[1], 1)

    def test_disconnected_color_specks_cannot_create_source_mode(self):
        rgb = np.zeros((25, 28, 3), np.uint8)
        rgb[:] = (80, 50, 60)
        rgb[::2, ::2] = (190, 135, 170)
        lab = color.rgb2lab(rgb.astype(np.float64) / 255.0)
        self.assertIsNone(_connected_mode_proposal(np.ones((25, 28), bool), lab))

    def test_global_source_mode_budget_is_sparse_and_palette_independent(self):
        # Thirty 4-connected source patches; only one has two true source
        # chromatic blocks. Global budget floor(0.075 *30) == 2.
        base = np.zeros((100, 120), np.int32)
        counter = 0
        for y in range(5):
            for x in range(6):
                counter += 1
                base[y * 20:(y + 1) * 20, x * 20:(x + 1) * 20] = counter
        rgb = np.full((100, 120, 3), (100, 100, 100), np.uint8)
        rgb[:10, :20] = (90, 25, 50)
        rgb[10:20, :20] = (180, 120, 110)
        lab = color.rgb2lab(rgb.astype(np.float64) / 255.0)
        out, counts = _source_mode_refine(base, lab)
        self.assertEqual(counts["mode_budget"], 2)
        self.assertEqual(counts["mode_accepted"], 1)
        self.assertEqual(int(out.max()), 31)
        self.assertNotEqual(int(out[2, 5]), int(out[15, 5]))
        self.assertEqual(int(out[30, 25]), int(out[31, 26]))
        for rid in np.unique(out):
            self.assertEqual(ndimage.label(out == rid)[1], 1)

    def test_real_source_thin_line_and_contrasting_single_dot_survive(self):
        a = original()
        a[3:52, 30, :3] = (245, 245, 245)
        a[13, 13, :3] = (245, 245, 245)
        old = a.copy()
        r = build_rag7(a, game128())
        self.assertTrue(np.array_equal(a, old))
        self.assertEqual(int(r["game_index"][20, 30]), 1)
        self.assertEqual(int(r["game_index"][13, 13]), 1)
        self.assertEqual(int(r["game_index"][20, 29]), 0)
        self.assertEqual(int(r["game_index"][13, 14]), 0)
        self.assertTrue(r["source_edge"][20, 30])
        self.assertIn("FORBIDDEN", r["stroke_admission"])

    def test_original_weak_specks_do_not_create_palette_islands(self):
        a = original()
        a[8, 12, :3] = (102, 100, 100)
        a[40, 48, :3] = (102, 100, 100)
        r = build_rag7(a, game128())
        self.assertEqual(int(r["baseline_index"][8, 12]), 2)
        self.assertEqual(int(r["game_index"][8, 12]), 0)
        self.assertEqual(int(r["game_index"][40, 48]), 0)
        self.assertEqual(int(r["counts"]["paintable_components"]), 1)

    def test_connected_main_base_patch_refined_edge_detail_paintable_ids(self):
        a = original(67, 79)
        a[8:56, 24:30, :3] = (245, 245, 245)
        a[20:42, 44:48, :3] = (45, 40, 50)
        r = build_rag7(a, game128())
        for key in ("surface_id", "base_patch_id", "patch_id",
                    "edge_component_id", "detail_id", "paintable_id"):
            labels = r[key]
            for rid in np.unique(labels[labels > 0]):
                self.assertEqual(ndimage.label(labels == rid)[1], 1, (key, int(rid)))
        occupied = r["patch_id"] > 0
        self.assertTrue(np.array_equal(
            r["patch_parent_surface_id"][r["patch_id"][occupied]],
            r["surface_id"][occupied]))
        detail = r["detail_id"] > 0
        self.assertTrue(np.array_equal(
            r["detail_parent_surface_id"][r["detail_id"][detail]],
            r["surface_id"][detail]))
        self.assertTrue(np.array_equal(
            r["detail_color_index"][r["detail_id"][detail]],
            r["game_index"][detail]))

    def test_original_edge_topologies_independent_of_game_palette(self):
        a = original()
        a[5:49, 28:30, :3] = (245, 245, 245)
        p = game128()
        x = build_rag7(a, p)
        y = build_rag7(a, p[::-1].copy())
        for key in ("surface_id", "base_patch_id", "patch_id", "edge_component_id", "source_edge"):
            self.assertTrue(np.array_equal(x[key], y[key]), key)
        self.assertFalse(np.array_equal(x["game_index"], y["game_index"]))

    def test_disconnected_same_swatch_parent_shapes_never_join(self):
        a = original()
        a[:, 31, 3] = 0
        r = build_rag7(a, game128())
        self.assertNotEqual(int(r["surface_id"][20, 10]), int(r["surface_id"][20, 49]))
        self.assertEqual(int(r["game_index"][20, 10]), int(r["game_index"][20, 49]))
        self.assertNotEqual(int(r["patch_id"][20, 10]), int(r["patch_id"][20, 49]))

    def test_partial_alpha_transparency_and_original_nonmutation(self):
        a = original()
        a[4:13, 6:17, 3] = 0
        a[20:29, 33:42, 3] = 128
        before = a.copy()
        r = build_rag7(a, game128())
        excluded = a[:, :, 3] != 255
        self.assertTrue(np.array_equal(a, before))
        for k in ("surface_id", "base_patch_id", "patch_id", "edge_component_id",
                  "detail_id", "paintable_id"):
            self.assertTrue(np.all(r[k][excluded] == 0), k)
        for k in ("game_index", "baseline_index"):
            self.assertTrue(np.all(r[k][excluded] == -1), k)
        self.assertTrue(np.array_equal(a[:, :, 3], r["preview_rgba"][:, :, 3]))
        self.assertTrue(np.all(r["unknown"]))
        self.assertEqual(r["source_owner_status"], "MISSING")

    def test_two_complete_original_builds_reproduce_all_layers(self):
        a = original(46, 65)
        a[9:39, 22:27, :3] = (245, 245, 245)
        p = game128()
        x, y = build_rag7(a, p), build_rag7(a, p)
        keys = ("surface_id", "base_patch_id", "patch_id",
                "patch_parent_surface_id", "patch_color_index",
                "edge_component_id", "detail_id",
                "detail_parent_surface_id", "detail_color_index",
                "paintable_id", "game_index", "baseline_index",
                "preview_rgba", "source_edge", "unknown", "adjacency")
        for k in keys:
            self.assertTrue(np.array_equal(x[k], y[k]), k)
        self.assertEqual(x["counts"], y["counts"])
        self.assertEqual(x["source_to_logical"], y["source_to_logical"])
        opaque = a[:, :, 3] == 255
        self.assertTrue(np.array_equal(x["preview_rgba"][:, :, :3][opaque],
                                       p[x["game_index"][opaque]]))
        result = evaluate_rag7(a, p, x)
        self.assertTrue(np.isfinite(result["candidate_rgb_mae"]))

    def test_empty_original_and_one_row(self):
        a = original(7, 11)
        a[:, :, 3] = 0
        blank = build_rag7(a, game128())
        self.assertEqual(blank["counts"]["paintable_components"], 0)
        self.assertTrue(np.all(blank["game_index"] == -1))
        row = build_rag7(original(1, 13), game128())
        self.assertEqual(row["counts"]["paintable_components"], 1)
        self.assertEqual(row["surface_id"].shape, (1, 13))

    def test_invalid_source_and_palette_are_blocked(self):
        with self.assertRaisesRegex(ValueError, "INVALID_ORIGINAL"):
            build_rag7(np.zeros((3, 5, 3), np.uint8), game128())
        with self.assertRaisesRegex(ValueError, "INVALID_GAME_PALETTE"):
            build_rag7(original(), np.zeros((128, 3), np.uint8))


if __name__ == "__main__":
    unittest.main()

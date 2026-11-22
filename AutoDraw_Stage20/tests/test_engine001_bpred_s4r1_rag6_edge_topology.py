#!/usr/bin/env python3
"""RAG6 E2 source-only regression gates. No real brush, Egret or game CHALK."""
from __future__ import annotations

import unittest

import numpy as np
from scipy import ndimage

from engine001_bpred_s4r1_rag6_edge_topology import (
    build_rag6, evaluate_rag6,
)
from engine001_bpred_s4r1_rag5_source_multiscale import (
    _connected_source_detail_candidates,
)


def game128():
    p = np.array([(i * 37 % 256, i * 61 % 256, i * 103 % 256)
                  for i in range(128)], np.uint8)
    p[0] = (100, 100, 100)
    p[1] = (245, 245, 245)
    p[2] = (102, 100, 100)
    assert len(np.unique(p, axis=0)) == 128
    return p


def rgba(h=56, w=64):
    a = np.full((h, w, 4), 255, np.uint8)
    a[:, :, :3] = (100, 100, 100)
    return a


class RAG6SourceTests(unittest.TestCase):
    def test_true_thin_line_and_isolated_bright_dot_survive(self):
        img = rgba()
        img[4:-4, 30, :3] = (245, 245, 245)
        img[13, 13, :3] = (245, 245, 245)
        frozen = img.copy()
        r = build_rag6(img, game128())
        self.assertTrue(np.array_equal(img, frozen))
        self.assertEqual(int(r["game_index"][20, 30]), 1)
        self.assertEqual(int(r["game_index"][13, 13]), 1)
        self.assertEqual(int(r["game_index"][20, 29]), 0)
        self.assertEqual(int(r["game_index"][13, 14]), 0)
        self.assertTrue(r["source_edge"][20, 30])
        self.assertTrue(r["source_edge"][13, 13])
        self.assertGreater(int(r["counts"]["paintable_components"]), 1)

    def test_weak_one_pixel_noise_does_not_generate_palette_island(self):
        img = rgba()
        img[8, 12, :3] = (102, 100, 100)
        img[41, 49, :3] = (102, 100, 100)
        r = build_rag6(img, game128())
        self.assertEqual(int(r["baseline_index"][8, 12]), 2)
        self.assertEqual(int(r["game_index"][8, 12]), 0)
        self.assertEqual(int(r["game_index"][41, 49]), 0)
        self.assertEqual(int(r["counts"]["paintable_components"]), 1)
        self.assertEqual(int(r["counts"]["main_surfaces"]), 1)

    def test_constant_original_keeps_one_graph_source_patch(self):
        r = build_rag6(rgba(64, 71), game128())
        self.assertEqual(int(r["counts"]["main_surfaces"]), 1)
        self.assertEqual(int(r["counts"]["patches"]), 1)
        self.assertEqual(int(r["counts"]["graph_regions"]), 1)
        self.assertEqual(int(r["counts"]["paintable_components"]), 1)
        self.assertEqual(int(r["counts"]["detail_pixels"]), 0)

    def test_source_patches_and_details_are_separately_connected(self):
        img = rgba(70, 88)
        img[13:60, 39:45, :3] = (245, 245, 245)
        img[3:7, 9:17, :3] = (245, 245, 245)
        r = build_rag6(img, game128())
        for key in ("surface_id", "patch_id", "edge_component_id", "detail_id", "paintable_id"):
            labels = r[key]
            for rid in np.unique(labels[labels > 0]):
                _, n = ndimage.label(labels == rid)
                self.assertEqual(n, 1, (key, int(rid)))
        mask = r["patch_id"] > 0
        self.assertTrue(np.array_equal(
            r["patch_parent_surface_id"][r["patch_id"][mask]], r["surface_id"][mask]))
        selected = r["detail_id"] > 0
        self.assertTrue(np.array_equal(
            r["detail_parent_surface_id"][r["detail_id"][selected]],
            r["surface_id"][selected]))
        self.assertTrue(np.array_equal(
            r["detail_color_index"][r["detail_id"][selected]],
            r["game_index"][selected]))

    def test_same_swatch_separate_surface_across_alpha(self):
        img = rgba()
        img[:, 32, 3] = 0
        r = build_rag6(img, game128())
        self.assertNotEqual(int(r["surface_id"][22, 9]),
                            int(r["surface_id"][22, 52]))
        self.assertEqual(int(r["game_index"][22, 9]), int(r["game_index"][22, 52]))
        self.assertNotEqual(int(r["patch_id"][22, 9]), int(r["patch_id"][22, 52]))

    def test_partial_alpha_and_transparent_are_not_assigned(self):
        img = rgba()
        img[3:13, 5:19, 3] = 0
        img[19:27, 30:41, 3] = 128
        original = img.copy()
        r = build_rag6(img, game128())
        invalid = img[:, :, 3] != 255
        self.assertTrue(np.array_equal(original, img))
        for key in ("surface_id", "patch_id", "edge_component_id", "detail_id", "paintable_id"):
            self.assertTrue(np.all(r[key][invalid] == 0), key)
        for key in ("game_index", "baseline_index"):
            self.assertTrue(np.all(r[key][invalid] == -1), key)
        self.assertTrue(np.array_equal(r["preview_rgba"][:, :, 3], img[:, :, 3]))
        self.assertTrue(np.all(r["unknown"]))
        self.assertEqual(r["source_owner_status"], "MISSING")
        self.assertIn("FORBIDDEN", r["stroke_admission"])

    def test_source_lab_neighbor_graph_does_not_join_disconnected_edges(self):
        mask = np.zeros((4, 6), bool)
        mask[1, 1:4] = True
        mask[3, 3] = True
        s = np.ones((4, 6), np.int32)
        lab = np.zeros((4, 6, 3), np.float64)
        labels, n = _connected_source_detail_candidates(mask, s, lab)
        self.assertEqual(n, 2)
        self.assertEqual(int(labels[1, 1]), int(labels[1, 3]))
        self.assertNotEqual(int(labels[1, 3]), int(labels[3, 3]))

    def test_two_fresh_runs_match_every_layer_exactly(self):
        img = rgba(43, 58)
        img[7:37, 24:30, :3] = (245, 245, 245)
        p = game128()
        a, b = build_rag6(img, p), build_rag6(img, p)
        keys = ("surface_id", "edge_component_id", "patch_id", "patch_parent_surface_id",
                "patch_color_index", "detail_id", "detail_parent_surface_id",
                "detail_color_index", "paintable_id", "game_index",
                "baseline_index", "preview_rgba", "source_edge", "unknown",
                "adjacency")
        for key in keys:
            self.assertTrue(np.array_equal(a[key], b[key]), key)
        self.assertEqual(a["counts"], b["counts"])
        self.assertEqual(a["source_to_logical"], b["source_to_logical"])
        opaque = img[:, :, 3] == 255
        self.assertTrue(np.array_equal(a["preview_rgba"][:, :, :3][opaque],
                                       p[a["game_index"][opaque]]))
        result = evaluate_rag6(img, p, a)
        self.assertTrue(np.isfinite(result["candidate_rgb_mae"]))
        self.assertGreater(a["counts"]["edge_topology_pixels"], 0)

    def test_all_transparent_and_single_row(self):
        blank = rgba(7, 12)
        blank[:, :, 3] = 0
        r = build_rag6(blank, game128())
        self.assertEqual(r["counts"]["paintable_components"], 0)
        self.assertTrue(np.all(r["game_index"] == -1))
        row = build_rag6(rgba(1, 12), game128())
        self.assertEqual(row["counts"]["paintable_components"], 1)
        self.assertEqual(row["surface_id"].shape, (1, 12))


    def test_edge_topology_independent_of_game_color_permutation(self):
        img = rgba()
        img[5:50, 27:30, :3] = (245, 245, 245)
        base = game128()
        reversed_palette = base[::-1].copy()
        x = build_rag6(img, base)
        y = build_rag6(img, reversed_palette)
        for key in ("surface_id", "patch_id", "edge_component_id", "source_edge"):
            self.assertTrue(np.array_equal(x[key], y[key]), key)
        # Palette swatch indices can change, but original topology MUST NOT.
        self.assertFalse(np.array_equal(x["game_index"], y["game_index"]))

    def test_invalid_sources_and_swatches_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "INVALID_ORIGINAL"):
            build_rag6(np.zeros((3, 4, 3), np.uint8), game128())
        with self.assertRaisesRegex(ValueError, "INVALID_PALETTE"):
            build_rag6(rgba(), np.zeros((128, 3), np.uint8))


if __name__ == "__main__":
    unittest.main()

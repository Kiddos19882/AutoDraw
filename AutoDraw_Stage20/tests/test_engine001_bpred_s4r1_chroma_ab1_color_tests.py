#!/usr/bin/env python3
"""CHROMA-AB1 A and B prospective original-only source E2, no game/native."""
import unittest

import numpy as np
from scipy import ndimage
from skimage import color

from engine001_bpred_s4r1_chroma_ab1_color_tests import (
    VARIANTS, _contrast_swatch_optimization, build_chroma_ab1,
    evaluate_chroma_ab1
)


def palette():
    p = np.array([(i * 37 % 256, i * 61 % 256, i * 103 % 256)
                  for i in range(128)], np.uint8)
    p[0] = (100, 100, 100)
    p[1] = (245, 245, 245)
    p[2] = (102, 100, 100)
    assert len(np.unique(p, axis=0)) == 128
    return p


def source(h=60, w=73):
    a = np.full((h, w, 4), 255, np.uint8)
    a[:, :, :3] = (100, 100, 100)
    return a


class ChromaticSourceAB1Tests(unittest.TestCase):
    def test_two_exact_predeclared_variants_and_no_third(self):
        self.assertEqual(VARIANTS, ("A", "B"))
        for variant in ("random", "", "C"):
            with self.assertRaises(ValueError):
                build_chroma_ab1(source(), palette(), variant)

    def test_original_constant_is_one_paintable_and_deterministic_A_B(self):
        rgba = source()
        frozen = rgba.copy()
        results = []
        for name in VARIANTS:
            first = build_chroma_ab1(rgba, palette(), name)
            repeat = build_chroma_ab1(rgba, palette(), name)
            results.append(first)
            self.assertTrue(np.array_equal(rgba, frozen))
            self.assertEqual(first["counts"]["main_surfaces"], 1)
            self.assertEqual(first["counts"]["source_graph_regions"], 1)
            self.assertEqual(first["counts"]["paintable_components"], 1)
            self.assertEqual(first["counts"]["detail_pixels"], 0)
            self.assertEqual(first["source_owner_status"], "MISSING")
            self.assertEqual(first["stroke_admission"],
                             "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE")
            for key in ("surface_id", "source_graph_id", "region_id",
                        "region_color_index", "game_index", "paintable_id",
                        "preview_rgba", "source_edge"):
                self.assertTrue(np.array_equal(first[key], repeat[key]), (name, key))
        self.assertTrue(np.array_equal(results[0]["region_id"], results[1]["region_id"]))

    def test_both_protect_thin_original_high_contrast_line_and_dot(self):
        image = source()
        image[3:-3, 29, :3] = (245, 245, 245)
        image[17, 13, :3] = (245, 245, 245)
        for name in VARIANTS:
            r = build_chroma_ab1(image, palette(), name)
            self.assertEqual(int(r["game_index"][20, 29]), 1, name)
            self.assertEqual(int(r["game_index"][17, 13]), 1, name)
            self.assertEqual(int(r["game_index"][17, 14]), 0, name)
            self.assertEqual(int(r["game_index"][20, 28]), 0, name)
            self.assertTrue(r["source_edge"][17, 13], name)
            self.assertTrue(r["source_edge"][20, 29], name)

    def test_both_ignore_single_weak_nearest_swatch_noise(self):
        image = source(64, 73)
        image[9, 17, :3] = (102, 100, 100)
        image[41, 49, :3] = (102, 100, 100)
        for name in VARIANTS:
            r = build_chroma_ab1(image, palette(), name)
            self.assertEqual(int(r["baseline_index"][9, 17]), 2, name)
            self.assertEqual(int(r["game_index"][9, 17]), 0, name)
            self.assertEqual(int(r["game_index"][41, 49]), 0, name)

    def test_original_alpha_and_geometric_connectivity_both(self):
        image = source(67, 85)
        image[2:10, 3:15, 3] = 0
        image[11:18, 24:37, 3] = 128
        image[:, 42, 3] = 0
        for name in VARIANTS:
            r = build_chroma_ab1(image, palette(), name)
            invisible = image[:, :, 3] != 255
            for key in ("surface_id", "source_graph_id", "region_id",
                        "edge_component_id", "detail_id", "paintable_id"):
                labels = r[key]
                self.assertTrue(np.all(labels[invisible] == 0), (name, key))
                for rid in np.unique(labels[labels > 0]):
                    _, components = ndimage.label(labels == rid)
                    self.assertEqual(components, 1, (name, key, int(rid)))
            self.assertTrue(np.all(r["game_index"][invisible] == -1))
            self.assertTrue(np.all(r["baseline_index"][invisible] == -1))
            self.assertTrue(np.all(r["unknown"]))
            self.assertTrue(np.array_equal(r["preview_rgba"][:, :, 3], image[:, :, 3]))
            self.assertNotEqual(int(r["region_id"][30, 6]), int(r["region_id"][30, 65]))

    def test_original_source_regions_identical_between_A_and_B(self):
        image = source()
        image[5:49, 12:35, :3] = (60, 80, 125)
        image[9:45, 35:62, :3] = (180, 50, 76)
        a = build_chroma_ab1(image, palette(), "A")
        b = build_chroma_ab1(image, palette(), "B")
        for key in ("surface_id", "source_graph_id", "region_id",
                    "edge_component_id", "source_edge",
                    "original_strong_boundary_pairs",
                    "original_strong_boundary_lengths"):
            self.assertTrue(np.array_equal(a[key], b[key]), key)
        for key in ("region_id", "paintable_id"):
            for mode in (a, b):
                for rid in np.unique(mode[key][mode[key] > 0]):
                    _, count = ndimage.label(mode[key] == rid)
                    self.assertEqual(count, 1)

    def test_A_region_palette_exact_full128_RGB_L1(self):
        image = source(56, 64)
        image[10:42, 26:51, :3] = (63, 75, 123)
        game = palette()
        r = build_chroma_ab1(image, game, "A")
        for rid in np.unique(r["region_id"][r["region_id"] > 0]):
            pixels = image[:, :, :3][r["region_id"] == rid].astype(np.int16)
            candidates = np.abs(
                pixels[:, None, :] - game[None, :, :].astype(np.int16)
            ).sum(axis=(0, 2), dtype=np.int64)
            self.assertEqual(int(r["region_color_index"][rid]), int(np.argmin(candidates)))

    def test_B_top4_two_pass_original_strong_contrast_objective(self):
        image = source(2, 4)
        image[:, 2:, :3] = (245, 245, 245)
        label = np.array([[1, 1, 2, 2], [1, 1, 2, 2]], np.int32)
        lab = color.rgb2lab(image[:, :, :3].astype(np.float64) / 255.)
        costs = np.full((3, 128), 10000, np.int64)
        costs[1, 0:4] = [0, 40, 60, 100]
        costs[2, 0:4] = [30, 0, 50, 90]
        color_index, pairs, lengths = _contrast_swatch_optimization(
            costs, label, np.ones((2, 4), bool), lab, palette())
        self.assertEqual(pairs.shape, (1, 2))
        self.assertEqual(int(lengths[0]), 2)
        self.assertIn(int(color_index[1]), (0, 1, 2, 3))
        self.assertIn(int(color_index[2]), (0, 1, 2, 3))
        self.assertTrue(np.array_equal(pairs, np.array([[1, 2]], np.int32)))

    def test_game128_permutation_does_not_move_original_source_owners(self):
        image = source()
        image[9:51, 20:40, :3] = (58, 61, 103)
        original_palette = palette()
        for name in VARIANTS:
            a = build_chroma_ab1(image, original_palette, name)
            b = build_chroma_ab1(image, original_palette[::-1].copy(), name)
            for key in ("surface_id", "source_graph_id", "region_id",
                        "edge_component_id", "source_edge"):
                self.assertTrue(np.array_equal(a[key], b[key]), (name, key))

    def test_invalid_original_palette_and_partial_alpha_fails_closed(self):
        rgba = source()
        for name in VARIANTS:
            with self.assertRaises(ValueError):
                build_chroma_ab1(rgba[:, :, :3], palette(), name)
            with self.assertRaises(ValueError):
                build_chroma_ab1(rgba, palette()[:127], name)
            with self.assertRaises(ValueError):
                build_chroma_ab1(rgba, np.zeros((128, 3), np.uint8), name)

    def test_frozen_metric_reports_do_not_call_brush(self):
        image = source()
        image[11:43, 23, :3] = (245, 245, 245)
        for name in VARIANTS:
            r = build_chroma_ab1(image, palette(), name)
            summary = evaluate_chroma_ab1(image, palette(), r)
            self.assertIn("baseline_rgb_mae", summary)
            self.assertIn("candidate_rgb_mae", summary)
            self.assertIn("strong_source_contrast", summary)
            self.assertIn("retained_fraction", summary["strong_source_contrast"])


if __name__ == "__main__":
    unittest.main()

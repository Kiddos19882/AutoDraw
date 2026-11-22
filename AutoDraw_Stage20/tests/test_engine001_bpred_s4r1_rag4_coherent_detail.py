#!/usr/bin/env python3
"""RAG4 E2 synthetic tests for fresh original-source color hierarchy only."""
from __future__ import annotations

import unittest
import numpy as np
from scipy import ndimage

from engine001_bpred_s4r1_rag4_coherent_detail import build_rag4, evaluate_rag4


def palette():
    p = np.array([(i * 37 % 256, i * 61 % 256, i * 103 % 256)
                  for i in range(128)], dtype=np.uint8)
    p[0] = [100, 100, 100]
    p[1] = [245, 245, 245]
    p[2] = [102, 100, 100]
    assert len(np.unique(p, axis=0)) == 128
    return p


def image(h=46, w=58, rgb=(100, 100, 100)):
    rgba = np.empty((h, w, 4), dtype=np.uint8)
    rgba[:, :, :3] = rgb
    rgba[:, :, 3] = 255
    return rgba


class RAG4SourceTests(unittest.TestCase):
    def test_source_supported_thin_contrast_is_retained(self):
        rgba = image()
        rgba[4:-4, 29, :3] = [245, 245, 245]
        before = rgba.copy()
        result = build_rag4(rgba, palette())
        self.assertTrue(np.array_equal(rgba, before))
        self.assertEqual(result["game_index"][20, 29], 1)
        self.assertEqual(result["game_index"][20, 28], 0)
        self.assertNotEqual(result["detail_id"][20, 29], 0)
        self.assertTrue(result["source_edge"][20, 29])
        self.assertIn("FORBIDDEN", result["stroke_admission"])

    def test_weak_isolated_swatch_is_recolored_as_whole_segment(self):
        rgba = image()
        rgba[20, 26, :3] = [102, 100, 100]
        result = build_rag4(rgba, palette())
        self.assertEqual(int(result["baseline_index"][20, 26]), 2)
        self.assertEqual(int(result["game_index"][20, 26]), 0)
        self.assertGreaterEqual(result["counts"]["recolored_color_segments"], 1)
        self.assertEqual(int(result["surface_id"][20, 26]),
                         int(result["surface_id"][20, 27]))

    def test_main_and_detail_ids_each_four_connected_and_parented(self):
        rgba = image(57, 63)
        rgba[7:48, 22:24, :3] = [245, 245, 245]
        rgba[26:33, 40:43, :3] = [245, 245, 245]
        result = build_rag4(rgba, palette())
        for key in ("surface_id", "color_segment_id", "detail_id"):
            lab = result[key]
            for identifier in np.unique(lab[lab > 0]):
                _, count = ndimage.label(lab == identifier)
                self.assertEqual(count, 1, (key, int(identifier)))
        selected = result["detail_id"] > 0
        parent = result["detail_parent_surface_id"]
        color = result["detail_color_index"]
        self.assertTrue(np.array_equal(
            parent[result["detail_id"][selected]], result["surface_id"][selected]))
        self.assertTrue(np.array_equal(
            color[result["detail_id"][selected]], result["game_index"][selected]))

    def test_adjacent_same_swatch_main_surfaces_never_merge(self):
        rgba = image()
        rgba[:, 28, 3] = 0
        result = build_rag4(rgba, palette())
        self.assertNotEqual(int(result["surface_id"][18, 12]),
                            int(result["surface_id"][18, 42]))
        self.assertEqual(int(result["game_index"][18, 12]),
                         int(result["game_index"][18, 42]))
        self.assertEqual(result["source_owner_status"], "MISSING")

    def test_preserves_opaque_alpha_boundaries_and_partial_rgba(self):
        rgba = image()
        rgba[3:12, 11:20, 3] = 0
        rgba[18:24, 31:36, 3] = 128
        old = rgba.copy()
        r = build_rag4(rgba, palette())
        invalid = rgba[:, :, 3] < 255
        self.assertTrue(np.array_equal(rgba, old))
        for k in ("surface_id", "detail_id", "color_segment_id"):
            self.assertTrue(np.all(r[k][invalid] == 0), k)
        self.assertTrue(np.all(r["game_index"][invalid] == -1))
        self.assertTrue(np.array_equal(r["preview_rgba"][:, :, 3], rgba[:, :, 3]))
        self.assertTrue(np.all(r["unknown"]))

    def test_reproducible_game128_only_and_source_quality(self):
        rgba = image(36, 56)
        rgba[10:27, 20:23, :3] = [245, 245, 245]
        p = palette()
        a = build_rag4(rgba, p)
        b = build_rag4(rgba, p)
        for key in ("surface_id", "color_segment_id", "detail_id",
                    "surface_color_index", "surface_color_table",
                    "detail_color_index", "detail_parent_surface_id",
                    "game_index", "baseline_index", "preview_rgba",
                    "source_edge", "unknown", "adjacency"):
            self.assertTrue(np.array_equal(a[key], b[key]), key)
        self.assertEqual(a["counts"], b["counts"])
        opaque = rgba[:, :, 3] == 255
        self.assertTrue(np.array_equal(a["preview_rgba"][:, :, :3][opaque],
                                       p[a["game_index"][opaque]]))
        self.assertTrue(np.isfinite(evaluate_rag4(rgba, p, a)["candidate_rgb_mae"]))

    def test_transparent_and_single_row_not_guessed(self):
        a = image(8, 14)
        a[:, :, 3] = 0
        empty = build_rag4(a, palette())
        self.assertEqual(int(empty["counts"]["main_surfaces"]), 0)
        self.assertTrue(np.all(empty["game_index"] == -1))
        b = image(1, 11)
        row = build_rag4(b, palette())
        self.assertEqual(row["surface_id"].shape, (1, 11))
        self.assertTrue(np.all(row["game_index"] == 0))

    def test_not_pixelwise_blind_final_on_source_weak_noise(self):
        a = image()
        a[11, 12, :3] = [102, 100, 100]
        a[32, 33, :3] = [102, 100, 100]
        r = build_rag4(a, palette())
        self.assertTrue(np.any(r["baseline_index"] != r["game_index"]))
        self.assertEqual(int(r["game_index"][11, 12]), 0)
        self.assertEqual(int(r["game_index"][32, 33]), 0)

    def test_fail_closed_on_invalid_input_palette(self):
        with self.assertRaisesRegex(ValueError, "INVALID_ORIGINAL"):
            build_rag4(np.zeros((8, 8, 3), np.uint8), palette())
        with self.assertRaisesRegex(ValueError, "INVALID_GAME_PALETTE"):
            build_rag4(image(), np.zeros((128, 3), np.uint8))


if __name__ == "__main__":
    unittest.main()

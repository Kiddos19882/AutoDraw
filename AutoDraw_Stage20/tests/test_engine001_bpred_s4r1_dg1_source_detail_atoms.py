#!/usr/bin/env python3
"""DG1 E2 gates: real source detail atoms, no after-game128 patch pixels."""
import unittest

import numpy as np
from scipy import ndimage
from skimage import color

from engine001_bpred_s4r1_dg1_source_detail_atoms import (
    _protected_original_dots, _original_detail_atoms,
    _chroma_original_score, build_dg1, evaluate_dg1,
)


def palette():
    p = np.array([(i * 37 % 256, i * 61 % 256, i * 103 % 256)
                  for i in range(128)], np.uint8)
    p[0] = (100, 100, 100)
    p[1] = (245, 245, 245)
    p[2] = (102, 100, 100)
    assert len(np.unique(p, axis=0)) == 128
    return p


def original(h=56, w=68):
    a = np.full((h, w, 4), 255, np.uint8)
    a[..., :3] = (100, 100, 100)
    return a


def lab(img):
    return color.rgb2lab(img[..., :3].astype(np.float64) / 255.)


class DG1OriginalProtectedAtomsTests(unittest.TestCase):
    def test_original_high_dot_is_geometry_atom_not_after_color_overlay(self):
        rgba = original()
        rgba[15, 19, :3] = (245, 245, 245)
        source_lab = lab(rgba)
        protected = _protected_original_dots(
            source_lab, rgba[..., 3] == 255)
        self.assertTrue(bool(protected[15, 19]))
        self.assertEqual(int(protected.sum()), 1)
        before = np.ones(protected.shape, np.int32)
        main = before.copy()
        regions, parents = _original_detail_atoms(before, main, protected)
        self.assertEqual(int(regions.max()), 2)
        self.assertNotEqual(int(regions[15, 19]), int(regions[15, 20]))
        self.assertEqual(int(np.count_nonzero(regions == regions[15, 19])), 1)
        a = build_dg1(rgba, palette())
        self.assertTrue(bool(a["protected_original_dot"][15, 19]))
        self.assertEqual(int(a["game_index"][15, 19]), 1)
        self.assertEqual(int(a["game_index"][15, 20]), 0)
        self.assertNotEqual(int(a["source_atom_id"][15, 19]),
                            int(a["source_atom_id"][15, 20]))
        self.assertLessEqual(int(a["counts"]["paintable_components"]),
                             int(a["counts"]["source_atoms"]))

    def test_original_true_thin_line_has_own_color_no_post_layer(self):
        img = original(70, 85)
        img[6:-6, 39, :3] = (245, 245, 245)
        img[20, 10, :3] = (245, 245, 245)
        r = build_dg1(img, palette())
        self.assertEqual(int(r["game_index"][23, 39]), 1)
        self.assertEqual(int(r["game_index"][23, 38]), 0)
        self.assertEqual(int(r["game_index"][20, 10]), 1)
        self.assertTrue(bool(r["source_edge"][23, 39]))
        self.assertTrue(bool(r["source_edge"][20, 10]))
        self.assertNotEqual(int(r["source_atom_id"][23, 39]),
                            int(r["source_atom_id"][23, 38]))

    def test_one_weak_noise_pixel_is_not_protected_or_colored_island(self):
        img = original()
        img[13, 15, :3] = (102, 100, 100)
        img[33, 45, :3] = (102, 100, 100)
        r = build_dg1(img, palette())
        self.assertFalse(bool(r["protected_original_dot"][13, 15]))
        self.assertFalse(bool(r["protected_original_dot"][33, 45]))
        self.assertEqual(int(r["baseline_index"][13, 15]), 2)
        self.assertEqual(int(r["game_index"][13, 15]), 0)
        self.assertEqual(int(r["game_index"][33, 45]), 0)

    def test_constant_full_original_one_atom_and_one_real_paintable(self):
        img = original()
        original_copy = img.copy()
        a = build_dg1(img, palette())
        b = build_dg1(img, palette())
        self.assertTrue(np.array_equal(img, original_copy))
        self.assertEqual(int(a["counts"]["source_atoms"]), 1)
        self.assertEqual(int(a["counts"]["paintable_components"]), 1)
        self.assertEqual(int(a["counts"]["source_protected_original_points"]), 0)
        for key in ("surface_id", "source_graph_id", "source_atom_id",
                    "protected_original_dot", "game_index", "paintable_id",
                    "preview_rgba", "source_edge", "atom_color_index"):
            self.assertTrue(np.array_equal(a[key], b[key]), key)
        self.assertEqual(a["source_owner_status"], "MISSING")
        self.assertEqual(a["stroke_admission"],
                         "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE")

    def test_partial_and_transparent_alpha_never_painted(self):
        img = original(62, 80)
        img[2:9, 3:11, 3] = 0
        img[16:27, 19:31, 3] = 127
        img[:, 42, 3] = 0
        a = build_dg1(img, palette())
        invalid = img[..., 3] != 255
        self.assertTrue(np.all(a["protected_original_dot"][invalid] == 0))
        for key in ("surface_id", "source_graph_id", "source_atom_id",
                    "paintable_id"):
            self.assertTrue(np.all(a[key][invalid] == 0), key)
        for key in ("game_index", "baseline_index"):
            self.assertTrue(np.all(a[key][invalid] == -1), key)
        self.assertTrue(np.array_equal(img[..., 3], a["preview_rgba"][..., 3]))
        self.assertNotEqual(int(a["source_atom_id"][29, 10]),
                            int(a["source_atom_id"][29, 63]))

    def test_every_original_source_atom_and_paintable_truly_4connected(self):
        img = original(67, 81)
        img[7:57, 31:35, :3] = (245, 245, 245)
        img[22, 21, :3] = (245, 245, 245)
        img[32:43, 58:71, :3] = (36, 92, 154)
        a = build_dg1(img, palette())
        for key in ("surface_id", "source_graph_id", "source_atom_id",
                    "paintable_id"):
            regions = a[key]
            for val in np.unique(regions[regions > 0]):
                _, connected = ndimage.label(regions == val)
                self.assertEqual(connected, 1, (key, int(val)))
        on = a["source_atom_id"] > 0
        self.assertTrue(np.array_equal(
            a["atom_parent_main"][a["source_atom_id"][on]],
            a["surface_id"][on]))
        self.assertTrue(np.array_equal(
            a["game_index"][on],
            a["atom_color_index"][a["source_atom_id"][on]]))
        self.assertLessEqual(a["counts"]["paintable_components"],
                             a["counts"]["source_atoms"])

    def test_geometry_only_source_original_is_palette_order_invariant(self):
        img = original()
        img[7:46, 22:30, :3] = (67, 50, 115)
        img[10, 10, :3] = (245, 245, 245)
        a = build_dg1(img, palette())
        b = build_dg1(img, palette()[::-1].copy())
        for key in ("surface_id", "source_graph_id", "source_atom_id",
                    "protected_original_dot", "source_edge"):
            self.assertTrue(np.array_equal(a[key], b[key]), key)

    def test_exact_all128_original_RGB_cost_and_frozen_chroma_integer_term(self):
        img = original(3, 4)
        img[:, 2:, :3] = (245, 245, 245)
        labels = np.array([[1, 1, 2, 2]] * 3, np.int32)
        game = palette()
        rgb, augmented, plab = _chroma_original_score(
            labels, lab(img), img[..., :3], game)
        self.assertEqual(rgb.shape, (3, 128))
        self.assertEqual(int(rgb[1, 0]), 0)
        self.assertEqual(int(rgb[2, 1]), 0)
        self.assertGreaterEqual(int(augmented[1, 0]), int(rgb[1, 0]))
        self.assertGreaterEqual(int(augmented[2, 1]), int(rgb[2, 1]))
        chroma = lab(img)
        for rid in (1, 2):
            pix = img[..., :3][labels == rid].astype(np.int16)
            exact = np.abs(pix[:, None, :] - game[None, :, :].astype(np.int16)).sum(axis=(0, 2), dtype=np.int64)
            self.assertTrue(np.array_equal(rgb[rid], exact))
            mean_ab = chroma[labels == rid, 1:].mean(axis=0)
            rounded = np.floor(
                (labels == rid).sum() * np.linalg.norm(
                    mean_ab[None, :] - plab[:, 1:], axis=1) + .5).astype(np.int64)
            self.assertTrue(np.array_equal(augmented[rid], rgb[rid] + rounded))

    def test_source_neighbor_contrast_penalty_preserves_actual_source_edge(self):
        img = original(60, 72)
        img[:, 35:, :3] = (245, 245, 245)
        a = build_dg1(img, palette())
        metric = evaluate_dg1(img, palette(), a)
        self.assertGreaterEqual(
            metric["strong_source_contrast"]["retained_fraction"], .75)
        self.assertTrue(np.all(a["game_index"][:, 12] == 0))
        self.assertTrue(np.all(a["game_index"][:, 56] == 1))

    def test_invalid_rgba_and_game128_rejected(self):
        img = original()
        with self.assertRaises(ValueError):
            build_dg1(img[..., :3], palette())
        with self.assertRaises(ValueError):
            build_dg1(img, palette()[:127])
        with self.assertRaises(ValueError):
            build_dg1(img, np.zeros((128, 3), np.uint8))

    def test_all_transparent_remains_missing_and_never_admitted(self):
        img = original()
        img[..., 3] = 0
        a = build_dg1(img, palette())
        self.assertEqual(a["counts"]["source_atoms"], 0)
        self.assertTrue(np.all(a["game_index"] == -1))
        self.assertTrue(np.all(a["unknown"]))
        self.assertEqual(a["source_owner_status"], "MISSING")
        self.assertEqual(a["stroke_admission"],
                         "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE")


if __name__ == "__main__":
    unittest.main()

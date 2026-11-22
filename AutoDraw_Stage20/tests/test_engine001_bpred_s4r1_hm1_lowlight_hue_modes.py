#!/usr/bin/env python3
"""HM1 original source-only low-light hue-mode and real game128 E2 regressions."""
import unittest

import numpy as np
from scipy import ndimage
from skimage import color

from engine001_bpred_s4r1_hm1_lowlight_hue_modes import (
    _original_hue_mode, _new_connected_hue_atoms,
    _hue_family_palette, build_hm1, evaluate_hm1
)


def palette():
    p = np.array([(i * 37 % 256, i * 61 % 256, i * 103 % 256)
                  for i in range(128)], np.uint8)
    p[0] = (66, 66, 66)
    p[1] = (90, 73, 65)
    p[2] = (245, 245, 245)
    p[3] = (100, 100, 100)
    p[4] = (102, 100, 100)
    assert len(np.unique(p, axis=0)) == 128
    return p


def original(h=64, w=78):
    p = np.full((h, w, 4), 255, np.uint8)
    p[..., :3] = (100, 100, 100)
    return p


def lab(img):
    return color.rgb2lab(img[..., :3].astype(np.float64) / 255.)


class HM1SourceHueModeTests(unittest.TestCase):
    def test_original_hue_sectors_wrap_without_breaking_red_halfplane(self):
        arr = np.zeros((1, 5, 3), np.float64)
        arr[..., 0] = 25.
        for i, deg in enumerate((359., 1., 44., 91., 185.)):
            arr[0, i, 1] = 20 * np.cos(np.deg2rad(deg))
            arr[0, i, 2] = 20 * np.sin(np.deg2rad(deg))
        hue = _original_hue_mode(arr, np.ones((1, 5), bool))
        self.assertEqual(int(hue[0, 0]), 1)
        self.assertEqual(int(hue[0, 1]), 1)
        self.assertEqual(int(hue[0, 2]), 2)
        self.assertEqual(int(hue[0, 3]), 3)
        self.assertEqual(int(hue[0, 4]), 5)

    def test_original_hue_mode_requires_dark_actual_source_chroma(self):
        img = original()
        img[5:24, 8:39, :3] = (83, 54, 59)
        m = _original_hue_mode(lab(img), img[..., 3] == 255)
        self.assertGreater(int(m[13, 20]), 0)
        self.assertEqual(int(m[35, 45]), 0)
        img[5:24, 8:39, 3] = 0
        m2 = _original_hue_mode(lab(img), img[..., 3] == 255)
        self.assertEqual(int(m2[13, 20]), 0)

    def test_original_connected_hue_mode_requires_area_and_fraction(self):
        main = np.ones((10, 10), np.int32)
        original_atoms = main.copy()
        hue = np.zeros((10, 10), np.uint8)
        hue[1:3, 1:5] = 1  # 8 pixels, not accepted
        a, parent, modes = _new_connected_hue_atoms(original_atoms, main, hue)
        self.assertEqual(int(a.max()), 1)
        self.assertEqual(int(modes.sum()), 0)
        hue.fill(0)
        hue[1:5, 1:6] = 1  # exactly 20px, 20% total
        b, parent, modes = _new_connected_hue_atoms(original_atoms, main, hue)
        self.assertEqual(int(b.max()), 2)
        self.assertNotEqual(int(b[2, 2]), int(b[7, 7]))
        self.assertEqual(int(modes[b[2, 2]]), 1)
        self.assertEqual(int(parent[b[2, 2]]), 1)

    def test_dark_chromatic_original_owner_never_chooses_grayscale(self):
        src = original(8, 8)
        src[..., :3] = (83, 54, 59)
        labels = np.ones((8, 8), np.int32)
        source_lab = lab(src)
        pal = palette()
        chosen, supported, compatible, _, _ = _hue_family_palette(
            labels, src[..., :3], source_lab, np.ones((8, 8), bool), pal)
        self.assertTrue(bool(supported[1]))
        self.assertFalse(bool(compatible[1, 0]))  # grayscale RGB66
        selected_lab = color.rgb2lab(
            pal[int(chosen[1])].reshape(1, 1, 3).astype(float)/255.
        ).reshape(3)
        self.assertGreaterEqual(np.linalg.norm(selected_lab[1:]), 6.)
        self.assertGreater(np.dot(selected_lab[1:], source_lab[0, 0, 1:]), 0.)

    def test_true_gray_original_owner_may_choose_grayscale(self):
        src = original(8, 8)
        src[..., :3] = (66, 66, 66)
        chosen, supported, compatible, _, _ = _hue_family_palette(
            np.ones((8, 8), np.int32), src[..., :3], lab(src),
            np.ones((8, 8), bool), palette())
        self.assertFalse(bool(supported[1]))
        self.assertTrue(bool(compatible[1, 0]))
        self.assertEqual(int(chosen[1]), 0)

    def test_original_true_bright_one_pixel_dot_and_thin_line(self):
        img = original(70, 85)
        img[17, 14, :3] = (245, 245, 245)
        img[5:-5, 42, :3] = (245, 245, 245)
        r = build_hm1(img, palette())
        self.assertEqual(int(r["game_index"][17, 14]), 2)
        self.assertEqual(int(r["game_index"][18, 14]), 3)
        self.assertEqual(int(r["game_index"][22, 42]), 2)
        self.assertEqual(int(r["game_index"][22, 41]), 3)
        self.assertTrue(bool(r["protected_original_dot"][17, 14]))
        self.assertNotEqual(int(r["source_mode_region_id"][17, 14]),
                            int(r["source_mode_region_id"][17, 15]))
        self.assertTrue(bool(r["source_edge"][17, 14]))

    def test_weak_original_one_pixel_noise_not_important_detail(self):
        img = original()
        img[11, 12, :3] = (102, 100, 100)
        img[42, 51, :3] = (102, 100, 100)
        r = build_hm1(img, palette())
        self.assertFalse(bool(r["protected_original_dot"][11, 12]))
        self.assertFalse(bool(r["protected_original_dot"][42, 51]))
        self.assertEqual(int(r["game_index"][11, 12]), 3)
        self.assertEqual(int(r["game_index"][42, 51]), 3)
        self.assertEqual(int(r["baseline_index"][11, 12]), 4)

    def test_full_original_lowlight_dark_source_region_retains_hue_family(self):
        img = original(64, 85)
        img[8:51, 19:62, :3] = (83, 54, 59)
        r = build_hm1(img, palette())
        self.assertGreater(int(r["original_hue_mode"][28, 35]), 0)
        rid = int(r["source_mode_region_id"][28, 35])
        self.assertTrue(bool(r["region_supported_dark_hue"][rid]))
        swatch = palette()[int(r["game_index"][28, 35])]
        target_lab = color.rgb2lab(swatch.reshape(1, 1, 3).astype(float)/255.).reshape(3)
        self.assertGreaterEqual(np.linalg.norm(target_lab[1:]), 6.)
        self.assertEqual(int(r["game_index"][30, 72]), 3)
        self.assertNotEqual(int(r["source_mode_region_id"][28, 35]),
                            int(r["source_mode_region_id"][30, 72]))

    def test_nonopaque_stays_unknown_no_source_owner_or_color(self):
        img = original(66, 91)
        img[2:12, 3:16, 3] = 0
        img[15:29, 24:37, 3] = 128
        img[:, 47, 3] = 0
        result = build_hm1(img, palette())
        invalid = img[..., 3] != 255
        for key in ("surface_id", "original_graph_id",
                    "protected_source_atom_id", "source_mode_region_id",
                    "paintable_id", "original_hue_mode"):
            self.assertTrue(np.all(result[key][invalid] == 0), key)
        self.assertTrue(np.all(result["game_index"][invalid] == -1))
        self.assertTrue(np.all(result["baseline_index"][invalid] == -1))
        self.assertTrue(np.all(result["unknown"]))
        self.assertTrue(np.array_equal(result["preview_rgba"][..., 3], img[..., 3]))

    def test_all_original_source_regions_and_real_paintables_are_4connected(self):
        img = original(71, 83)
        img[8:45, 11:40, :3] = (83, 54, 59)
        img[16:58, 47:68, :3] = (46, 55, 102)
        img[27, 19, :3] = (245, 245, 245)
        r = build_hm1(img, palette())
        for key in ("surface_id", "original_graph_id",
                    "protected_source_atom_id", "source_mode_region_id",
                    "paintable_id"):
            arr = r[key]
            for value in np.unique(arr[arr>0]):
                _, count = ndimage.label(arr == value)
                self.assertEqual(count, 1, (key, int(value)))
        valid = r["source_mode_region_id"]>0
        self.assertTrue(np.array_equal(
            r["source_region_parent_main"][r["source_mode_region_id"][valid]],
            r["surface_id"][valid]))
        self.assertTrue(np.array_equal(
            r["region_color_index"][r["source_mode_region_id"][valid]],
            r["game_index"][valid]))
        self.assertLessEqual(r["counts"]["paintable_components"],
                             r["counts"]["source_final_regions"])

    def test_same_original_source_geometry_if_genuine_palette_permuted(self):
        img=original()
        img[8:47, 13:38, :3] = (83, 54, 59)
        a = build_hm1(img, palette())
        b = build_hm1(img, palette()[::-1].copy())
        for key in ("surface_id", "original_graph_id",
                    "protected_source_atom_id", "original_hue_mode",
                    "source_mode_region_id", "protected_original_dot",
                    "source_edge"):
            self.assertTrue(np.array_equal(a[key], b[key]), key)

    def test_invalid_source_and_invalid_palette_fail_closed(self):
        img = original()
        for rgba, p in ((img[..., :3], palette()),
                        (img, palette()[:127]),
                        (img, np.zeros((128, 3), np.uint8))):
            with self.assertRaises(ValueError):
                build_hm1(rgba, p)

    def test_clean_repeat_all_arrays_and_independent_source_metrics(self):
        img = original()
        img[10:47, 19:48, :3] = (83, 54, 59)
        img[24, 16, :3] = (245, 245, 245)
        original_bytes = img.copy()
        a = build_hm1(img, palette())
        b = build_hm1(img, palette())
        self.assertTrue(np.array_equal(img, original_bytes))
        for key in ("surface_id", "original_hue_mode", "source_mode_region_id",
                    "region_color_index", "paintable_id", "game_index",
                    "baseline_index", "source_edge", "preview_rgba"):
            self.assertTrue(np.array_equal(a[key], b[key]), key)
        metrics = evaluate_hm1(img, palette(), a)
        self.assertIn("baseline_rgb_mae", metrics)
        self.assertIn("candidate_rgb_mae", metrics)
        self.assertIn("retained_fraction", metrics["strong_source_contrast"])
        self.assertEqual(a["source_owner_status"], "MISSING")
        self.assertEqual(a["stroke_admission"],
                         "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE")

    def test_all_transparent_no_color_or_source_hue(self):
        img = original()
        img[..., 3] = 0
        r = build_hm1(img, palette())
        self.assertEqual(int(r["counts"]["source_final_regions"]), 0)
        self.assertTrue(np.all(r["game_index"] == -1))
        self.assertTrue(np.all(r["unknown"]))


if __name__ == "__main__":
    unittest.main()

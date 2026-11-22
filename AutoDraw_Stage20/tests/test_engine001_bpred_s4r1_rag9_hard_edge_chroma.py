#!/usr/bin/env python3
"""RAG9 frozen-source E2. Checks topology BEFORE any four-DEV original run."""
import unittest

import numpy as np
from scipy import ndimage
from skimage import color

from engine001_bpred_s4r1_rag9_hard_edge_chroma import (
    _allowed_components, _hard_source_edges, _source_bins,
    _source_atom_adjacency, _propagate, _regional_palette_cost,
    _original_strong_region_edges, _regional_game128,
    build_rag9, evaluate_rag9,
)


def palette():
    swatches = np.array([(i * 37 % 256, i * 61 % 256, i * 103 % 256)
                         for i in range(128)], np.uint8)
    swatches[0] = (100, 100, 100)
    swatches[1] = (245, 245, 245)
    swatches[2] = (102, 100, 100)
    assert len(np.unique(swatches, axis=0)) == 128
    return swatches


def original(h=48, w=56):
    out = np.full((h, w, 4), 255, np.uint8)
    out[:, :, :3] = (100, 100, 100)
    return out


def lab_of(image):
    return color.rgb2lab(image[:, :, :3].astype(np.float64) / 255.)


class RAG9OriginalSourceTests(unittest.TestCase):
    def test_high_contrast_border_hard_even_with_similar_palette(self):
        img = original(12, 16)
        img[:, 8:, :3] = (240, 240, 240)
        opaque = np.ones((12, 16), bool)
        bh, bv, dh, dv = _hard_source_edges(lab_of(img), opaque)
        self.assertTrue(np.all(bh[:, 7]))
        self.assertTrue(np.all(dh[:, 7] >= 24))
        atoms = _allowed_components(np.ones((12, 16), np.int32), bh, bv)
        self.assertNotEqual(int(atoms[5, 7]), int(atoms[5, 8]))
        self.assertEqual(int(atoms.max()), 2)

    def test_isolated_1px_dot_protected_without_parallel_support(self):
        img = original(15, 17)
        img[7, 8, :3] = (245, 245, 245)
        mask = np.ones((15, 17), bool)
        bh, bv, _, _ = _hard_source_edges(lab_of(img), mask)
        self.assertTrue(bh[7, 7] and bh[7, 8])
        self.assertTrue(bv[6, 8] and bv[7, 8])
        atoms = _allowed_components(np.ones((15, 17), np.int32), bh, bv)
        self.assertNotEqual(int(atoms[7, 8]), int(atoms[7, 7]))
        self.assertEqual(int(atoms.max()), 2)

    def test_mild_single_pixel_noise_stays_contiguous(self):
        img = original(12, 14)
        img[7, 6, :3] = (102, 100, 100)
        bh, bv, _, _ = _hard_source_edges(lab_of(img), np.ones((12, 14), bool))
        self.assertFalse(bh.any())
        self.assertFalse(bv.any())
        atoms = _allowed_components(np.ones((12, 14), np.int32), bh, bv)
        self.assertEqual(int(atoms.max()), 1)

    def test_alpha_crossing_and_partial_alpha_are_forbidden(self):
        img = original(17, 20)
        img[:, 10, 3] = 128
        opaque = img[:, :, 3] == 255
        bh, bv, _, _ = _hard_source_edges(lab_of(img), opaque)
        self.assertTrue(np.all(bh[:, 9]) and np.all(bh[:, 10]))
        atoms = _allowed_components(opaque.astype(np.int32), bh, bv)
        self.assertTrue(np.all(atoms[:, 10] == 0))
        self.assertNotEqual(int(atoms[5, 4]), int(atoms[5, 14]))

    def test_original_equal_luminance_different_chroma_bins(self):
        rgb = np.array([[[100, 40, 48], [70, 58, 113]]], np.uint8)
        lab = color.rgb2lab(rgb.astype(np.float64) / 255.)
        bins = _source_bins(lab)
        self.assertNotEqual(int(bins[0, 0]), int(bins[0, 1]))
        self.assertGreater(float(np.linalg.norm(lab[0, 0, 1:] - lab[0, 1, 1:])), 9.)

    def test_geodesic_modes_propagate_only_on_allowed_atom_edges(self):
        atoms = np.array([[1, 2, 3, 4]], np.int32)
        main = np.ones((1, 4), np.int32)
        parent = np.array([0, 1, 1, 1, 1], np.int32)
        modes = np.array([0, 100, 100, 200, 200], np.int32)
        seeds = np.array([False, True, False, False, True])
        med = np.array([[0., 0., 0.], [40., 14., 0.],
                        [40., 14., 0.], [40., -14., 0.], [40., -14., 0.]])
        edges = np.array([[1, 2], [3, 4]], np.int32)
        regions, rparent, rseed, owner, _ = _propagate(
            atoms, main, parent, modes, seeds, med, edges)
        self.assertEqual(int(regions[0, 0]), int(regions[0, 1]))
        self.assertEqual(int(regions[0, 2]), int(regions[0, 3]))
        self.assertNotEqual(int(regions[0, 1]), int(regions[0, 2]))
        self.assertEqual(int(owner[2]), int(owner[1]))
        self.assertEqual(int(owner[3]), int(owner[4]))

    def test_exact_all128_original_RGB_region_loss_and_2pass_palette(self):
        image = original(2, 4)
        image[:, :2, :3] = (100, 100, 100)
        image[:, 2:, :3] = (245, 245, 245)
        regions = np.repeat(np.array([[1, 1, 2, 2]], np.int32), 2, axis=0)
        colors = palette()
        costs = _regional_palette_cost(regions, image[:, :, :3], colors)
        self.assertEqual(costs.shape, (3, 128))
        self.assertEqual(int(costs[1, 0]), 0)
        self.assertEqual(int(costs[2, 1]), 0)
        lab = lab_of(image)
        pairs, lengths = _original_strong_region_edges(
            regions, np.ones((2, 4), bool),
            np.linalg.norm(lab[:, :-1] - lab[:, 1:], axis=2),
            np.linalg.norm(lab[:-1] - lab[1:], axis=2))
        self.assertEqual(len(pairs), 1)
        self.assertEqual(int(lengths[0]), 2)
        chosen, _ = _regional_game128(regions, image[:, :, :3], colors, pairs, lengths)
        self.assertEqual(int(chosen[1]), 0)
        self.assertEqual(int(chosen[2]), 1)

    def test_constant_original_determinism_and_connected_output(self):
        img = original()
        frozen = img.copy()
        a = build_rag9(img, palette())
        b = build_rag9(img, palette())
        self.assertTrue(np.array_equal(img, frozen))
        for key in ("surface_id", "barrier_atom_id", "patch_id", "game_index", "paintable_id"):
            self.assertTrue(np.array_equal(a[key], b[key]), key)
        self.assertEqual(int(a["counts"]["paintable_components"]), 1)
        self.assertEqual(int(a["counts"]["opaque_pixels"]), img.shape[0] * img.shape[1])
        self.assertEqual(a["source_owner_status"], "MISSING")
        self.assertEqual(a["stroke_admission"], "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE")

    def test_real_dot_and_line_game_palette_and_connected_regions(self):
        img = original()
        img[8:40, 29, :3] = (245, 245, 245)
        img[14, 12, :3] = (245, 245, 245)
        a = build_rag9(img, palette())
        self.assertEqual(int(a["game_index"][14, 12]), 1)
        self.assertEqual(int(a["game_index"][20, 29]), 1)
        self.assertEqual(int(a["game_index"][20, 28]), 0)
        self.assertNotEqual(int(a["patch_id"][14, 12]), int(a["patch_id"][14, 13]))
        for key in ("surface_id", "barrier_atom_id", "patch_id", "paintable_id"):
            labels = a[key]
            for rid in np.unique(labels[labels > 0]):
                _, count = ndimage.label(labels == rid)
                self.assertEqual(count, 1, (key, rid))

    def test_palette_permutation_preserves_all_source_geometry(self):
        img = original()
        img[10:38, 23:27, :3] = (245, 245, 245)
        a = build_rag9(img, palette())
        b = build_rag9(img, palette()[::-1].copy())
        for key in ("surface_id", "barrier_atom_id", "patch_id", "barrier_h", "barrier_v"):
            self.assertTrue(np.array_equal(a[key], b[key]), key)

    def test_invalid_original_and_palette_block(self):
        with self.assertRaises(ValueError):
            build_rag9(original()[:, :, :3], palette())
        with self.assertRaises(ValueError):
            build_rag9(original(), palette()[:127])
        with self.assertRaises(ValueError):
            build_rag9(original(), np.zeros((128, 3), np.uint8))


if __name__ == "__main__":
    unittest.main()

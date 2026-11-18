#!/usr/bin/env python3
"""P3D synthetic source-original edge masks, no legacy G32/V44."""
import ast
import tempfile
import unittest
from pathlib import Path

import numpy as np

import run_engine001_b1r_p3d_source_edge_mask_ablation as p3d
import run_engine001_b1r_p3b_engine128_adaptive32 as p3b


def synthetic_original():
    rgb = np.full(p3b.LOGICAL_SHAPE, (90, 90, 90), dtype=np.uint8)
    rgb[210:215, 130:135] = (130, 130, 130)
    rgb[230:240, 0:10] = (255, 255, 255)
    return rgb


class P3DEdgeMaskContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = synthetic_original()

    def test_01_prespecified_id_and_mask_methods(self):
        self.assertEqual(p3d.EXPERIMENT, "ENGINE001_B1R_P3D_SOURCE_EDGE_MASK_ABLATION_V1")
        self.assertEqual(p3d.MASKS, ("E_SOBEL90", "F_SOBEL90_LAB12"))
        self.assertEqual(p3d.LAB_EDGE_THRESHOLD, 12.0)

    def test_02_source_only_binary_shapes(self):
        masks, counts = p3d.source_edge_masks(self.source)
        self.assertEqual(set(masks), set(p3d.MASKS))
        for m in masks.values():
            self.assertEqual(m.shape, (240, 150))
            self.assertEqual(m.dtype, np.bool_)
        self.assertTrue(counts["E_is_subset_of_F"])

    def test_03_E_is_subset_F(self):
        masks, _ = p3d.source_edge_masks(self.source)
        self.assertTrue(np.all(~masks["E_SOBEL90"] | masks["F_SOBEL90_LAB12"]))

    def test_04_face_hand_ROI_whole_not_just_edges(self):
        masks, _ = p3d.source_edge_masks(self.source)
        for name in ("female_face_eyes", "male_face_eyes", "hands"):
            x0, y0, x1, y1 = p3b.roi_logical(name)
            for m in masks.values():
                self.assertTrue(m[y0:y1, x0:x1].all())

    def test_05_source_bright_white_locked(self):
        masks, _ = p3d.source_edge_masks(self.source)
        for m in masks.values():
            self.assertTrue(m[231:238, 1:8].all())

    def test_06_original_strong_LAB_boundary_protected(self):
        masks, counts = p3d.source_edge_masks(self.source)
        self.assertGreater(counts["source_original_CIEDE00_4neighbor_ge12_pixels"], 0)
        self.assertTrue(masks["F_SOBEL90_LAB12"][210:215, 130:135].all())

    def test_07_flat_original_not_entirely_protected(self):
        masks, counts = p3d.source_edge_masks(self.source)
        self.assertLess(counts["E_SOBEL90_protected_pixels"], 36000)
        self.assertLessEqual(counts["E_SOBEL90_protected_pixels"],
                             counts["F_SOBEL90_LAB12_protected_pixels"])
        self.assertFalse(masks["E_SOBEL90"][200, 135])

    def test_08_wrong_shape_dtype_rejected(self):
        with self.assertRaisesRegex(ValueError, "SHAPE_OR_DTYPE"):
            p3d.source_edge_masks(self.source[:-1])
        with self.assertRaisesRegex(ValueError, "SHAPE_OR_DTYPE"):
            p3d.source_edge_masks(self.source.astype(float))

    def test_09_original_input_unchanged(self):
        original = self.source.copy()
        p3d.source_edge_masks(self.source)
        self.assertTrue(np.array_equal(self.source, original))

    def test_10_all_legacy_G32_V44_absent(self):
        tree = ast.parse(Path(p3d.__file__).read_text(encoding="utf8"))
        modules = [n.module for n in ast.walk(tree)
                   if isinstance(n, ast.ImportFrom) and n.module]
        direct = [x.name for n in ast.walk(tree) if isinstance(n, ast.Import)
                  for x in n.names]
        self.assertTrue(all("G32" not in n and "v44" not in n.lower()
                            for n in modules + direct))
        self.assertIn("run_engine001_b1r_p3c_source_coherence", direct)

    def test_11_output_fail_closed_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "OUTPUT_EXISTS"):
                p3d.run(Path(directory) / "original.png",
                        Path(directory) / "engine.js", Path(directory))


if __name__ == "__main__":
    unittest.main()

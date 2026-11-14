"""Synthetic E2 guards for preregistered ENGINE001_COMPLEX_STRUCTURE_V6."""
import unittest
from unittest.mock import patch

import numpy as np

from run_engine001_complex_structure_v6 import (
    extract_edges, compare_edges, reconstruct_palette, roi_bounds, provenance_sha,
)


class ComplexStructureV6Tests(unittest.TestCase):
    def test_blank_source_has_unmeasurable_recall_not_false_pass(self):
        a = np.zeros((32, 32), dtype=bool)
        summary = compare_edges(a, a.copy())
        self.assertIsNone(summary["source_edge_recall_within_1px"])
        self.assertEqual(summary["eligible_source_components_ge12"], 0)

    def test_identical_long_line_is_preserved(self):
        a = np.zeros((30, 60), dtype=bool)
        a[12, 5:35] = True
        metrics = compare_edges(a, a)
        self.assertEqual(metrics["source_edge_recall_within_1px"], 1.0)
        self.assertEqual(metrics["eligible_source_components_ge12"], 1)
        self.assertEqual(metrics["components_retained_ge50pct"], 1)

    def test_absent_long_line_is_lost(self):
        a = np.zeros((30, 60), dtype=bool)
        a[12, 5:35] = True
        metrics = compare_edges(a, np.zeros_like(a))
        self.assertEqual(metrics["source_edge_recall_within_1px"], 0.0)
        self.assertEqual(metrics["components_lost_ge50pct"], 1)

    def test_one_pixel_shift_tolerated_two_not(self):
        a = np.zeros((30, 60), dtype=bool)
        a[12, 5:35] = True
        b = np.zeros_like(a)
        b[13, 5:35] = True
        self.assertEqual(compare_edges(a, b)["source_edge_recall_within_1px"], 1.0)
        b[:] = False
        b[14, 5:35] = True
        self.assertEqual(compare_edges(a, b)["source_edge_recall_within_1px"], 0.0)

    def test_short_components_excluded_from_component_gate_not_pixel_recall(self):
        a = np.zeros((30, 60), dtype=bool)
        a[4, 2:8] = True
        result = compare_edges(a, np.zeros_like(a))
        self.assertEqual(result["eligible_source_components_ge12"], 0)
        self.assertEqual(result["missing_source_edge_pixels"], 6)

    def test_shape_and_dtype_mismatch_fail_closed(self):
        a = np.zeros((16, 16), dtype=bool)
        with self.assertRaises(ValueError):
            compare_edges(a, np.zeros((16, 17), dtype=bool))
        with self.assertRaises(ValueError):
            compare_edges(a, a.astype(np.uint8))

    def test_palette_reconstruction_and_roi_contract(self):
        labels = np.array([[0, 1, 0], [1, 0, 1]], dtype=np.uint8)
        colors = {"palette_rgb": {"0": [255, 255, 255], "1": [0, 0, 0]}}
        rgb = reconstruct_palette(labels, colors)
        self.assertEqual(tuple(rgb[0, 1]), (0, 0, 0))
        ys, xs = roi_bounds({"paste_xy": [1, 0], "resized_size": [2, 2]}, labels.shape)
        self.assertEqual(rgb[ys, xs].shape, (2, 2, 3))
        with self.assertRaises(ValueError):
            roi_bounds({"paste_xy": [2, 0], "resized_size": [2, 2]}, labels.shape)

    def test_checkout_sha_provenance_fail_closed(self):
        with patch.dict("os.environ", {"GITHUB_SHA": "A" * 40}):
            self.assertEqual(provenance_sha(), "a" * 40)
        with patch.dict("os.environ", {"GITHUB_SHA": "not-a-sha"}):
            with self.assertRaises(ValueError):
                provenance_sha()
        with patch.dict("os.environ", {"GITHUB_SHA": ""}):
            self.assertIsNone(provenance_sha())

    def test_canny_detects_sharp_boundary(self):
        rgb = np.full((64, 64, 3), 255, dtype=np.uint8)
        rgb[:, :32] = 0
        edges = extract_edges(rgb)
        self.assertEqual(edges.dtype, np.dtype(bool))
        self.assertGreater(int(edges.sum()), 30)
        self.assertLess(int(edges.sum()), 128)


if __name__ == "__main__":
    unittest.main()

"""Synthetic E2 guards for preregistered ENGINE001_COMPLEX_STRUCTURE_V6."""
import unittest
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np

from run_engine001_complex_structure_v6 import (
    extract_edges, compare_edges, reconstruct_palette, roi_bounds, provenance_sha,
    run, SOURCE_SHA256, fixed_grid_edge_loss,
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

    def test_pinned_repository_image_end_to_end_artifacts(self):
        # Regression of original-to-report provenance; this is not native art quality.
        workspace = Path(__file__).resolve().parents[2]
        png = workspace / "AutoDraw_Stage20/testImages/wV6VeZI9S1Y.png"
        self.assertTrue(png.is_file(), "Pinned source missing from checkout")
        self.assertEqual(hashlib.sha256(png.read_bytes()).hexdigest(), SOURCE_SHA256)
        with TemporaryDirectory() as td:
            out = Path(td)
            result = run(workspace, out)
            self.assertEqual(result["source"]["original_size"], [200, 320])
            self.assertEqual(result["roi"]["width"], 150)
            self.assertEqual(result["roi"]["height"], 240)
            self.assertEqual(result["roi"]["paste_xy"], [155, 0])
            self.assertEqual(result["status"],
                             "DIAGNOSTIC_COMPLETE_NOT_RECOGNITION_PASS")
            self.assertEqual(result["quality"]["v6_recognition"], "NOT_TESTED")
            self.assertEqual(len(result["fixed_grid_3cols_4rows"]), 12)
            self.assertEqual(
                sum(tile["missing_edge_pixels"] for tile in result["fixed_grid_3cols_4rows"]),
                result["metrics"]["missing_source_edge_pixels"])
            self.assertEqual(len(result["derived_png_sha256"]), 6)
            self.assertIn("edge-retention-overlay.png", result["derived_png_sha256"])
            from PIL import Image
            with Image.open(out / "edge-retention-overlay.png") as img:
                self.assertEqual(img.size, (150, 240))
                self.assertEqual(img.mode, "RGB")
            report = json.loads((out / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["source"]["png_sha256"], SOURCE_SHA256)
            self.assertEqual(
                report["metrics"]["missing_source_edge_pixels"],
                report["metrics"]["source_edge_pixels"] -
                report["metrics"]["source_edges_matched_within_1px"])
            for name, digest in report["derived_png_sha256"].items():
                self.assertEqual(hashlib.sha256((out / name).read_bytes()).hexdigest(),
                                 digest)

    def test_fixed_spatial_grid_retains_global_edge_totals(self):
        src = np.zeros((24, 30), dtype=bool)
        pal = np.zeros_like(src)
        src[5, 9] = True
        src[6, 10] = True
        src[23, 29] = True
        pal[5, 10] = True  # One-pixel match across x=10 tile boundary.
        tiles = fixed_grid_edge_loss(src, pal)
        self.assertEqual(len(tiles), 12)
        self.assertEqual(sum(t["source_edge_pixels"] for t in tiles), 3)
        self.assertEqual(sum(t["matched_edge_pixels"] for t in tiles), 2)
        self.assertEqual(sum(t["missing_edge_pixels"] for t in tiles), 1)
        self.assertEqual(tiles[0]["matched_edge_pixels"], 1)
        self.assertEqual(tiles[1]["matched_edge_pixels"], 1)
        self.assertIsNone(tiles[2]["edge_recall"])

    def test_fixed_spatial_grid_fails_closed_for_bad_shapes(self):
        a = np.zeros((4, 3), dtype=bool)
        with self.assertRaises(ValueError):
            fixed_grid_edge_loss(a, a.astype(np.uint8))
        with self.assertRaises(ValueError):
            fixed_grid_edge_loss(a, np.zeros((4, 4), dtype=bool))
        with self.assertRaises(ValueError):
            fixed_grid_edge_loss(np.zeros((3, 3), dtype=bool),
                                 np.zeros((3, 3), dtype=bool))

    def test_canny_detects_sharp_boundary(self):
        rgb = np.full((64, 64, 3), 255, dtype=np.uint8)
        rgb[:, :32] = 0
        edges = extract_edges(rgb)
        self.assertEqual(edges.dtype, np.dtype(bool))
        self.assertGreater(int(edges.sum()), 30)
        self.assertLess(int(edges.sum()), 128)


if __name__ == "__main__":
    unittest.main()

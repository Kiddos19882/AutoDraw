"""ENGINE001_STRUCTURE_FIRST_V7 isolated synthetic and pinned-source guards."""
import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from run_engine001_structure_first_v7 import (
    edge_mask, plan_line_only, preview_paths, run, MAX_POINTS, MAX_STROKES,
    MAX_VERTICES,
)


class StructureFirstV7Tests(unittest.TestCase):
    def test_blank_source_is_measurable_without_false_recognition(self):
        a = np.full((48, 64, 3), 255, dtype=np.uint8)
        paths, summary, edges = plan_line_only(a, (0, 0))
        self.assertEqual(paths, [])
        self.assertEqual(summary["accepted_paths"], 0)
        self.assertFalse(edges.any())
        _, _, metric = preview_paths(a, paths, (0, 0), edges)
        self.assertIsNone(metric["edge_coverage_proxy"])

    def test_long_connected_contour_is_kept(self):
        a = np.full((64, 96, 3), 255, dtype=np.uint8)
        a[20:43, 22:72] = (35, 25, 30)
        paths, summary, edges = plan_line_only(a, (10, 20))
        self.assertGreater(summary["accepted_paths"], 0)
        self.assertTrue(edges.any())
        for stroke in paths:
            self.assertGreaterEqual(len(stroke["points"]), 2)
            self.assertLessEqual(len(stroke["points"]), MAX_POINTS)
            self.assertTrue(all(10 <= p["x"] < 106 and 20 <= p["y"] < 84
                                for p in stroke["points"]))
        self.assertLessEqual(summary["accepted_paths"], MAX_STROKES)
        self.assertLessEqual(summary["accepted_vertices"], MAX_VERTICES)

    def test_invalid_source_dtype_is_rejected(self):
        with self.assertRaises(ValueError):
            edge_mask(np.zeros((30, 50), dtype=np.uint8))
        with self.assertRaises(ValueError):
            edge_mask(np.zeros((30, 50, 3), dtype=np.float32))

    def test_deterministic_same_source(self):
        a = np.full((64, 96, 3), 255, dtype=np.uint8)
        a[15:45, 20:70] = (50, 40, 30)
        first, summary1, edges1 = plan_line_only(a, (155, 0))
        second, summary2, edges2 = plan_line_only(a, (155, 0))
        self.assertEqual(first, second)
        self.assertEqual(summary1, summary2)
        self.assertTrue(np.array_equal(edges1, edges2))

    def test_original_pinned_source_and_artifacts(self):
        workspace = Path(__file__).resolve().parents[2]
        source = workspace / "AutoDraw_Stage20/testImages/wV6VeZI9S1Y.png"
        self.assertTrue(source.exists())
        self.assertEqual(
            hashlib.sha256(source.read_bytes()).hexdigest(),
            "07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a")
        with TemporaryDirectory() as d:
            output = Path(d)
            report = run(workspace, output)
            self.assertEqual(report["status"],
                             "OFFLINE_EXPLORATORY_PATH_PREVIEW_NOT_NATIVE")
            self.assertEqual(report["quality"]["native_egret"], "NOT_RUN")
            self.assertEqual(len(report["derived_png_sha256"]), 4)
            paths = json.loads((output/"paths.json").read_text(encoding="utf-8"))
            self.assertEqual(report["statistics"]["accepted_paths"], len(paths))
            for path, digest in report["derived_png_sha256"].items():
                self.assertEqual(hashlib.sha256((output/path).read_bytes()).hexdigest(), digest)


if __name__ == "__main__":
    unittest.main()

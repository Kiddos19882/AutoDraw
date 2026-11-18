#!/usr/bin/env python3
"""ENGINE001 B1-R-P2 deterministic source-only region/outline contracts."""
import ast
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
from PIL import Image
from skimage import measure

import run_engine001_b1r_p2_joint_region_outline as p2
from run_engine001_b1r_p1_fullrgb_edge_aware import full_features


def fixture():
    rgb = np.full(p2.FULL_SHAPE, 247, dtype=np.uint8)
    rgb[24:146, 18:94] = [58, 48, 51]
    rgb[65:175, 100:179] = [188, 164, 134]
    rgb[130:136, 38:165] = [27, 25, 29]
    rgb[176:287, 40:174] = [230, 223, 205]
    rgb[188:213, 56:164] = [241, 156, 129]
    rgb[80:85, 62:68] = [14, 9, 12]
    return rgb


class B1RP2Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rgb = fixture()
        cls.features = full_features(cls.rgb)

    def test_01_preregistered_variants_are_exact(self):
        self.assertEqual(
            p2.EXPERIMENT, "ENGINE001_B1R_P2_JOINT_REGION_OUTLINE_V1")
        self.assertEqual(p2.SOURCE_SHA256,
                         "07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a")
        self.assertEqual(p2.VARIANTS, {
            "J_FINE": {"filter": "A_SOFT", "n_segments": 900, "compactness": 6.0},
            "J_COARSE": {"filter": "A_MID", "n_segments": 500, "compactness": 9.0},
        })

    def test_02_original_only_slic_is_deterministic_and_connected(self):
        for name in p2.VARIANTS:
            one = p2.slic_labels(self.rgb, name)
            two = p2.slic_labels(self.rgb, name)
            self.assertTrue(np.array_equal(one, two))
            self.assertEqual(one.shape, (320, 200))
            self.assertEqual(one.min(), 1)
            for i in np.unique(one):
                self.assertEqual(measure.label(one == i, connectivity=1).max(), 1)

    def test_03_medoid_source_rgb_is_exact_and_in_own_region(self):
        labels = p2.slic_labels(self.rgb, "J_FINE")
        mapped, ledger = p2.source_region_medoids(self.rgb, labels)
        self.assertEqual(mapped.shape, p2.FULL_SHAPE)
        self.assertEqual(len(ledger), len(np.unique(labels)))
        for entry in ledger:
            x, y = entry["source_pixel_xy"]
            self.assertEqual(labels[y, x], entry["id"])
            self.assertEqual(list(self.rgb[y, x]), entry["RGB_original"])
            self.assertTrue(np.all(mapped[labels == entry["id"]] ==
                                   self.rgb[y, x]))
        repeat, repeated_ledger = p2.source_region_medoids(self.rgb, labels)
        self.assertTrue(np.array_equal(mapped, repeat))
        self.assertEqual(ledger, repeated_ledger)

    def test_04_nearest_resizing_introduces_no_new_colors(self):
        labels = p2.slic_labels(self.rgb, "J_COARSE")
        mapped, ledger = p2.source_region_medoids(self.rgb, labels)
        result = p2.logical_region_map(mapped)
        self.assertEqual(result.shape, p2.LOGICAL_SHAPE)
        medoids = {tuple(entry["RGB_original"]) for entry in ledger}
        self.assertTrue(all(tuple(c) in medoids for c in
                            np.unique(result.reshape(-1, 3), axis=0)))

    def test_05_joint_outline_is_derived_from_own_labels_and_source(self):
        labels = p2.slic_labels(self.rgb, "J_FINE")
        outline, boundary, roi_detail = p2.joint_outline(
            self.rgb, labels, self.features)
        self.assertTrue(outline.any())
        self.assertTrue(boundary.any())
        self.assertTrue(np.all(outline & ~roi_detail <=
                               np.asarray(
                                   __import__("scipy").ndimage.binary_dilation(
                                       boundary, iterations=1)) |
                               self.features["priority"]))
        rgba = p2.original_outline_rgba(self.rgb, outline)
        self.assertEqual(rgba.shape, (320, 200, 4))
        self.assertTrue(np.array_equal(rgba[..., 3] != 0, outline))
        self.assertTrue(np.all(rgba[outline, 3] == 185))

    def test_06_fail_closed_on_invalid_inputs_and_unknown_methods(self):
        with self.assertRaisesRegex(ValueError, "ORIGINAL_RGB_DIMENSIONS"):
            p2.validate_full(self.rgb[:40])
        with self.assertRaisesRegex(ValueError, "VARIANT_NOT_PREREGISTERED"):
            p2.slic_labels(self.rgb, "G32")
        with self.assertRaisesRegex(ValueError, "MEDOID_LABEL_SHAPE"):
            p2.source_region_medoids(self.rgb, np.zeros((32, 20), np.int32))
        with self.assertRaisesRegex(ValueError, "METRIC_DIMENSIONS"):
            p2.delta_metrics(np.zeros((2, 2, 3)), np.zeros((2, 2, 3)))

    def test_07_original_sha_failure_remains_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            filename = Path(d) / "f.png"
            Image.fromarray(self.rgb).save(filename)
            with self.assertRaisesRegex(ValueError, "BLOCKED_B1R_P1_ORIGINAL_SHA"):
                p2.check_source(filename)

    def test_08_metrics_do_not_masquerade_as_game_quality(self):
        labels = p2.slic_labels(self.rgb, "J_FINE")
        mapped, ledger = p2.source_region_medoids(self.rgb, labels)
        outline, boundary, roi_detail = p2.joint_outline(
            self.rgb, labels, self.features)
        logical = p2.logical_region_map(mapped)
        original = p2.logical_rgb(self.rgb)
        outline_rgba = p2.original_outline_rgba(self.rgb, outline)
        composite = np.asarray(p2.compose_preview(logical, outline_rgba))
        outcome = p2.evaluate(original, logical, composite,
                              labels, ledger, outline, boundary, roi_detail)
        self.assertIn("source_mean_deltaE00", outcome["gates"])
        self.assertIn("fixed_original_strong_edges", outcome["gates"])
        self.assertIn("composite_with_own_outline", outcome)
        self.assertIn(outcome["status"],
                      {"SOURCE_SCREEN_PASS_VISUAL_PENDING", "SOURCE_GATE_FAIL"})

    def test_09_runner_artifact_hashes_and_safe_rejection_of_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "b1rp2"
            with mock.patch.object(p2, "check_source", return_value=self.rgb.copy()):
                report = p2.run(Path(d) / "synthetic-unused.png", dest)
            self.assertEqual(set(report["metrics"]), set(p2.VARIANTS))
            self.assertFalse(report["legacy_G32_used_as_candidate"])
            self.assertFalse(report["legacy_V44_used_as_candidate"])
            self.assertFalse(report["legacy_M1_mask_used_as_candidate"])
            self.assertEqual(report["game32_projection"], "NOT_RUN")
            self.assertIsNone(report["exact_game_CHALK"])
            self.assertEqual(report["human_visual"], "PENDING")
            self.assertTrue((dest / "B1R_P2_RGB_AND_JOINT_OUTLINE_COMPARISON.png").exists())
            for filename, want_hash in report["file_sha256"].items():
                self.assertEqual(p2.digest((dest / filename).read_bytes()), want_hash)
            with self.assertRaisesRegex(ValueError, "BLOCKED_B1R_P2_OVERWRITE"):
                p2.run(Path(d) / "synthetic-unused.png", dest)

    def test_10_no_historical_runner_or_g32_v44_imports(self):
        tree = ast.parse(Path(p2.__file__).read_text(encoding="utf8"))
        imported = {
            n.module for n in ast.walk(tree)
            if isinstance(n, ast.ImportFrom) and n.module
        }
        imported |= {
            alias.name for n in ast.walk(tree)
            if isinstance(n, ast.Import) for alias in n.names
        }
        engine_imports = {i for i in imported if i.startswith("run_engine001")}
        self.assertEqual(
            engine_imports, {"run_engine001_b1r_p1_fullrgb_edge_aware"})


if __name__ == "__main__":
    unittest.main()

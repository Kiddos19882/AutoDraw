#!/usr/bin/env python3
"""B1-R-P2B: 9 synthetic source-detail and provenance regression contracts."""
import ast
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
from PIL import Image

import run_engine001_b1r_p2b_residual_ink as p2b


def fixture():
    a = np.full(p2b.FULL_SHAPE, 249, dtype=np.uint8)
    a[23:158, 18:103] = [74, 60, 57]
    a[55:179, 100:183] = [193, 162, 144]
    a[123:128, 30:165] = [27, 21, 25]
    a[177:286, 35:176] = [233, 225, 214]
    a[193:220, 62:163] = [244, 161, 141]
    a[71:79, 66:74] = [7, 8, 11]
    return a


class B1RP2BContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = fixture()
        cls.features = p2b.full_features(cls.source)
        guide = p2b.filter_original(cls.source, "A_SOFT",
                                    cls.features["protected"])
        cls.labels = p2b.slic_labels(guide, "J_FINE")
        cls.flat, cls.ledger = p2b.source_region_medoids(cls.source, cls.labels)

    def test_01_exact_registered_contracts(self):
        self.assertEqual(p2b.EXPERIMENT, "ENGINE001_B1R_P2B_RGB_RESIDUAL_INK_V1")
        self.assertEqual(set(p2b.VARIANTS), {"K_RESTRAINED", "K_DETAIL"})
        self.assertEqual(p2b.VARIANTS["K_RESTRAINED"], {
            "outside_deltaE00": 11.0, "outside_dark_L": 7.0,
            "inside_deltaE00": 6.0, "inside_dark_L": 3.0,
        })
        self.assertEqual(p2b.VARIANTS["K_DETAIL"], {
            "outside_deltaE00": 8.0, "outside_dark_L": 5.0,
            "inside_deltaE00": 4.5, "inside_dark_L": 2.5,
        })

    def test_02_residual_exact_rgb_and_alpha(self):
        for name in p2b.VARIANTS:
            mask, rgba, merged, stats = p2b.ink_residual(
                self.source, self.flat, self.features, name)
            self.assertEqual(mask.shape, (320, 200))
            self.assertTrue(mask.any())
            self.assertTrue(np.array_equal(rgba[..., 3] == 255, mask))
            self.assertTrue(np.array_equal(rgba[mask, :3], self.source[mask]))
            self.assertTrue(np.array_equal(merged[mask], self.source[mask]))
            self.assertTrue(np.array_equal(merged[~mask], self.flat[~mask]))
            self.assertTrue(stats["source_ink_selected_only_near_original_contrast"])

    def test_03_stricter_variant_selects_subset_of_detail_variant(self):
        a = p2b.ink_residual(
            self.source, self.flat, self.features, "K_RESTRAINED")[0]
        b = p2b.ink_residual(
            self.source, self.flat, self.features, "K_DETAIL")[0]
        self.assertFalse(np.any(a & ~b))

    def test_04_original_only_same_run_regions_no_stored_p2_inputs(self):
        self.assertEqual(self.labels.shape, p2b.FULL_SHAPE[:2])
        self.assertEqual(len(self.ledger), len(np.unique(self.labels)))
        for item in self.ledger:
            x, y = item["source_pixel_xy"]
            self.assertEqual(self.labels[y, x], item["id"])
            self.assertEqual(list(self.source[y, x]), item["RGB_original"])

    def test_05_composite_metrics_are_separate_from_flat_control(self):
        _, _, full, summary = p2b.ink_residual(
            self.source, self.flat, self.features, "K_DETAIL")
        original = p2b.logical_rgb(self.source)
        flat = p2b.logical_region_map(self.flat)
        composite = p2b.logical_composite(full)
        outcome = p2b.candidate_metrics(
            original, flat, composite, summary, len(self.ledger))
        self.assertIn("flat_original_source_RGB", outcome)
        self.assertIn("residual_own_source_composite", outcome)
        self.assertIn("female_face_improves_20percent", outcome["gates"])
        self.assertEqual(outcome["gates"]["source_exact_residual_ink"], True)
        self.assertIn(outcome["status"],
                      {"SOURCE_SCREEN_PASS_VISUAL_PENDING", "SOURCE_GATE_FAIL"})

    def test_06_reject_unknown_method_and_wrong_dimensions(self):
        with self.assertRaisesRegex(ValueError, "UNREGISTERED_VARIANT"):
            p2b.ink_residual(self.source, self.flat, self.features, "V44-B")
        with self.assertRaisesRegex(ValueError, "RGB_INPUT"):
            p2b.ink_residual(self.source[:20], self.flat,
                             self.features, "K_DETAIL")
        with self.assertRaisesRegex(ValueError, "LOGICAL_INPUT"):
            p2b.logical_composite(self.flat[:20])

    def test_07_source_hash_cannot_be_bypassed(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "fake_original.png"
            Image.fromarray(self.source).save(path)
            with self.assertRaisesRegex(ValueError, "ORIGINAL_SHA"):
                p2b.check_source(path)

    def test_08_end_to_end_synthetic_artifacts_and_overwrite_guard(self):
        with tempfile.TemporaryDirectory() as t:
            dest = Path(t) / "out"
            with mock.patch.object(p2b, "check_source",
                                   return_value=self.source.copy()):
                report = p2b.run(Path(t) / "not-read.png", dest)
            self.assertEqual(set(report["metrics"]), set(p2b.VARIANTS))
            self.assertFalse(report["legacy_G32_used_as_candidate"])
            self.assertFalse(report["legacy_V44_used_as_candidate"])
            self.assertFalse(report["legacy_M1_mask_used_as_candidate"])
            self.assertFalse(report["frozen_P2V1_artifacts_as_input"])
            self.assertEqual(report["human_visual"], "PENDING")
            self.assertEqual(report["game32_projection"], "NOT_RUN")
            self.assertIsNone(report["exact_game_CHALK"])
            self.assertTrue((dest / "B1R_P2B_ORIGINAL_FLAT_TWO_RESIDUALS.png").exists())
            for filename, want in report["file_sha256"].items():
                self.assertEqual(p2b.digest((dest / filename).read_bytes()), want)
            with self.assertRaisesRegex(ValueError, "BLOCKED_B1R_P2B_OVERWRITE"):
                p2b.run(Path(t) / "not-read.png", dest)

    def test_09_no_legacy_runner_imports(self):
        imports = set()
        source = Path(p2b.__file__).read_text(encoding="utf8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imports.add(node.module)
            elif isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
        actual = {s for s in imports if s and s.startswith("run_engine001")}
        self.assertEqual(actual, {
            "run_engine001_b1r_p1_fullrgb_edge_aware",
            "run_engine001_b1r_p2_joint_region_outline",
        })


if __name__ == "__main__":
    unittest.main()

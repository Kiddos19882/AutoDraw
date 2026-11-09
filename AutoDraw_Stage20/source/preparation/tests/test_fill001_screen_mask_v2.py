from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from chalk_fill_experiment import build_fill_target_mask
from chalk_fill_matrix import FillMatrixError
from fill001_screen_mask_v2 import (
    SCHEMA, audit_screen_mask_v2, project_screen_mask_v2,
    evaluate_fill001_chalk_first_quality, FILL001_CHALK_FIRST_POLICY_V2,
)


class ScreenMaskV2Tests(unittest.TestCase):
    def setUp(self):
        self.roi = {"x": 100, "y": 200, "width": 461, "height": 241}
        self.geometry = {
            "run_id": "run-test", "same_run": True,
            "coordinate_system": "desktop_screen_css_pixels",
            "validation_status": "valid", "independent_screen_mapping": True,
            "board_screen_corners": {
                "left": 100.0, "top": 200.0, "right": 560.0, "bottom": 440.0,
            },
            "evidence_sha256": "a" * 64,
        }

    def project(self, **kwargs):
        return project_screen_mask_v2(
            "rectangle", run_id=kwargs.pop("run_id", "run-test"),
            screen_roi=kwargs.pop("roi", self.roi),
            geometry=kwargs.pop("geometry", self.geometry),
        )

    def test_identity_projection_preserves_frozen_mask(self):
        mask = self.project()
        np.testing.assert_array_equal(mask[:240, :460], build_fill_target_mask("rectangle"))
        self.assertFalse(mask[-1].any())
        self.assertFalse(mask[:, -1].any())
        self.assertFalse(mask.flags.writeable)

    def test_measured_offset_changes_only_v2_projection(self):
        geometry = dict(self.geometry)
        geometry["board_screen_corners"] = dict(self.geometry["board_screen_corners"])
        geometry["board_screen_corners"]["top"] += 2
        geometry["board_screen_corners"]["bottom"] += 2
        shifted = self.project(geometry=geometry)
        original = self.project()
        self.assertFalse(np.array_equal(shifted, original))
        np.testing.assert_array_equal(build_fill_target_mask("rectangle"),
                                      build_fill_target_mask("rectangle"))

    def test_rejects_unverified_or_stale_geometry(self):
        for field, value in (
            ("run_id", "other"), ("same_run", False),
            ("coordinate_system", "client_css_pixels"),
            ("validation_status", "unknown"),
            ("independent_screen_mapping", False),
            ("evidence_sha256", "not-a-hash"),
        ):
            with self.subTest(field=field):
                bad = dict(self.geometry, **{field: value})
                with self.assertRaises(FillMatrixError):
                    self.project(geometry=bad)
        with self.assertRaises(FillMatrixError):
            self.project(run_id="other")

    def test_rejects_invalid_corners_and_roi(self):
        bad = dict(self.geometry)
        bad["board_screen_corners"] = dict(self.geometry["board_screen_corners"], right=50)
        with self.assertRaises(FillMatrixError):
            self.project(geometry=bad)
        with self.assertRaises(FillMatrixError):
            self.project(roi=dict(self.roi, width=True))
        with self.assertRaises(FillMatrixError):
            self.project(roi=dict(self.roi, x=9000))

    def test_report_preserves_v1_audit_even_if_v2_changes(self):
        before = np.full((241, 461, 3), 255, np.uint8)
        after = before.copy()
        after[60:180, 80:380] = (0, 0, 0)
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "before.png"
            second = Path(directory) / "after.png"
            Image.fromarray(before).save(first)
            Image.fromarray(after).save(second)
            report = audit_screen_mask_v2(
                "rectangle", first, second, run_id="run-test",
                screen_roi=self.roi, geometry=self.geometry,
            )
            self.assertEqual(report["schema"], SCHEMA)
            self.assertTrue(report["diagnostic_only"])
            self.assertFalse(report["acceptance_override"])
            self.assertEqual(report["changed_pixels"], 120 * 300)
            self.assertIn("png_audit_status", report["v1_original"])
            self.assertEqual(report["geometry_evidence_sha256"], "a" * 64)


    def test_chalk_first_perimeter_quality_accepts_halo_rejects_remote_spill(self):
        target = np.zeros((60,90), dtype=np.bool_)
        target[10:50,20:70] = True
        painted = target.copy()
        painted[30,70:73] = True  # 1, 2, 3 logical px outside right edge
        result = evaluate_fill001_chalk_first_quality(
            target, painted, scale_x=1, scale_y=1,
        )
        self.assertEqual(result["policy_id"], FILL001_CHALK_FIRST_POLICY_V2)
        self.assertEqual(result["quality_gate"], "PASS")
        self.assertEqual(result["leakage_pixels"], 3)
        self.assertEqual(result["leakage_pixels_beyond_allowed_halo"], 0)
        self.assertEqual(result["max_perimeter_overshoot_logical_px"], 3.0)
        self.assertIsNone(result["exact_chalk"])
        self.assertEqual(result["chalk_evidence_status"], "NOT_EVALUATED")
        self.assertIn("min_run_bound_exact_chalk", result["chalk_selection_priority"])
        painted[30,73] = True
        result = evaluate_fill001_chalk_first_quality(
            target, painted, scale_x=1, scale_y=1,
        )
        self.assertEqual(result["quality_gate"], "FAIL")
        self.assertEqual(result["leakage_pixels_beyond_allowed_halo"], 1)

    def test_chalk_first_perimeter_checks_true_logical_scale_and_coverage(self):
        target = np.zeros((60,90), dtype=np.bool_)
        target[10:50,20:70] = True
        screen = np.repeat(np.repeat(target,3,axis=0),3,axis=1)
        painted = screen.copy()
        painted[90,210:220] = True  # final pixel is >3 logical px outside
        result = evaluate_fill001_chalk_first_quality(
            screen, painted, scale_x=3, scale_y=3,
        )
        self.assertEqual(result["quality_gate"], "FAIL")
        painted[90,219] = False
        result = evaluate_fill001_chalk_first_quality(
            screen, painted, scale_x=3, scale_y=3,
        )
        self.assertEqual(result["quality_gate"], "PASS")
        painted[40:48,60:100] = False
        result = evaluate_fill001_chalk_first_quality(
            screen, painted, scale_x=3, scale_y=3,
        )
        self.assertEqual(result["quality_gate"], "FAIL")
        self.assertLess(result["coverage_fraction"], 0.99)
        for sx,sy in ((0,1),(1,1.1),(float("nan"),1)):
            with self.subTest(sx=sx,sy=sy),self.assertRaises(FillMatrixError):
                evaluate_fill001_chalk_first_quality(
                    screen,screen,scale_x=sx,scale_y=sy,
                )
        with self.assertRaises(FillMatrixError):
            evaluate_fill001_chalk_first_quality(
                screen,screen.astype(np.uint8),scale_x=3,scale_y=3,
            )

    def test_chalk_first_policy_explicit_and_legacy_gate_unchanged(self):
        mask = self.project()
        before = np.full((241,461,3), 255, dtype=np.uint8)
        after = before.copy()
        after[mask] = (0,0,0)
        after[120,391:394] = (0,0,0)
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)
            b,a=p/"before.png",p/"after.png"
            Image.fromarray(before).save(b)
            Image.fromarray(after).save(a)
            kwargs=dict(run_id="run-test",screen_roi=self.roi,geometry=self.geometry)
            legacy=audit_screen_mask_v2("rectangle",b,a,**kwargs)
            active=audit_screen_mask_v2(
                "rectangle",b,a,quality_policy=FILL001_CHALK_FIRST_POLICY_V2,**kwargs,
            )
            self.assertEqual(legacy["v2_diagnostic_gate"], "FAIL")
            self.assertEqual(active["v2_diagnostic_gate"], "FAIL")
            self.assertEqual(legacy["v1_original"],active["v1_original"])
            self.assertNotIn("active_quality_gate",legacy)
            self.assertEqual(active["active_quality_gate"],"PASS")
            self.assertGreater(active["active_quality_metrics"]["leakage_pixels"],0)
            self.assertEqual(active["active_quality_policy_id"],FILL001_CHALK_FIRST_POLICY_V2)
            self.assertFalse(active["acceptance_override"])
            with self.assertRaises(FillMatrixError):
                audit_screen_mask_v2("rectangle",b,a,quality_policy="made_up",**kwargs)


if __name__ == "__main__":
    unittest.main()

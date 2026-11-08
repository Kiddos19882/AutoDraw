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


if __name__ == "__main__":
    unittest.main()

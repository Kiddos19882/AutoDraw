from __future__ import annotations

import copy
import unittest

import numpy as np

from color_scanline import (
    ColorScanlinePlanError,
    build_color_scanline_plan,
    validate_color_scanline_plan,
)


PALETTE = {
    "profile_name": "Point quota integration",
    "colors": [
        {"id": "red", "name": "Red", "rgb": [255, 0, 0], "hex": "#FF0000"},
        {"id": "blue", "name": "Blue", "rgb": [0, 0, 255], "hex": "#0000FF"},
    ],
}


class ColorPointQuotaIntegrationTests(unittest.TestCase):
    def test_color_plan_persists_calibrated_game_point_quota(self):
        plan = build_color_scanline_plan(
            np.asarray([[0, 0, 1]], dtype=np.int32), PALETTE
        )
        estimate = plan["summary"]["point_quota_estimate"]
        model = plan["generation"]["point_quota_model"]

        self.assertEqual(model["board_item_type"], "BoardItem2")
        self.assertEqual(model["board_point_limit"], 6_000)
        self.assertEqual(model["point_step_px"], 2.0)
        self.assertEqual(model["point_delay_ms"], 10)
        self.assertEqual(estimate["board_point_limit"], 6_000)
        self.assertEqual(estimate["stroke_count"], 2)
        self.assertTrue(estimate["is_calibrated_estimate"])
        self.assertFalse(estimate["calibration_point_limit_is_inferred"])
        self.assertLess(estimate["estimated_point_count"], 6_000)
        validate_color_scanline_plan(plan)

    def test_board_type_and_point_limit_must_match(self):
        with self.assertRaisesRegex(ColorScanlinePlanError, "не совпадает с типом"):
            build_color_scanline_plan(
                np.asarray([[0]], dtype=np.int32),
                PALETTE,
                board_item_type="BoardItem1",
                board_point_limit=3_000,
            )

    def test_tampered_point_quota_estimate_is_rejected(self):
        plan = build_color_scanline_plan(
            np.asarray([[0, 0, 1]], dtype=np.int32), PALETTE
        )
        tampered = copy.deepcopy(plan)
        tampered["summary"]["point_quota_estimate"]["estimated_point_count"] += 100
        with self.assertRaises(ColorScanlinePlanError):
            validate_color_scanline_plan(tampered)


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""P4c2 regression: immutable path contract and native E3 metrics, no model acceptance."""
import unittest

from run_engine001_color32_p4c2_full_native import (
    OWNERS, validate_frozen_paths, assess_native,
    FROZEN_PAINT_PATHS, FROZEN_PAINT_VERTICES,
)


class P4c2Contracts(unittest.TestCase):
    def test_p4c1_paths_must_have_frozen_count_before_renderer(self):
        with self.assertRaisesRegex(ValueError, "BLOCKED_P4C2_FROZEN_PATH_COUNTS"):
            validate_frozen_paths({"original_P4c0_strokes": [],
                                   "P4c1_additions": [],
                                   "safe_to_execute_game": False})
        self.assertEqual(FROZEN_PAINT_PATHS, 1133)
        self.assertEqual(FROZEN_PAINT_VERTICES, 3485)

    def fixture(self, coverage=.995, leak=0, exterior=0):
        data = {}
        for alpha in (24, 128):
            data[str(alpha)] = {}
            for o in OWNERS:
                data[str(alpha)][str(o)] = {
                    "owner_target_backing_pixels": 1000,
                    "native_correct_owner_pixels": int(1000 * coverage),
                    "native_alpha_ink_pixels": 1200,
                    "non_owner_beyond_3logical_px": leak,
                    "ink_outside_image_ROI": exterior,
                    "non_owner_native_pixels_any_distance": 100,
                }
        return data

    def test_native_all17_only_passes_when_cover_and_safe(self):
        result = assess_native(self.fixture())
        self.assertTrue(result["native_paint_numeric_gate"])
        self.assertEqual(result["owners_below99_native_alpha24"], [])
        self.assertEqual(result["full_image_quality"], "NOT_RUN")

    def test_one_owner_below99_fails_full_numeric_gate(self):
        f = self.fixture()
        f["24"]["28"]["native_correct_owner_pixels"] = 980
        res = assess_native(f)
        self.assertFalse(res["native_paint_numeric_gate"])
        self.assertEqual(res["owners_below99_native_alpha24"], [28])

    def test_any_foreign_far_or_roi_exterior_fails(self):
        for bad in ("non_owner_beyond_3logical_px", "ink_outside_image_ROI"):
            f = self.fixture()
            f["128"]["5"][bad] = 1
            self.assertFalse(assess_native(f)["native_alpha24_128_all17_safety"])

    def test_missing_owner_and_blank_native_fail_closed(self):
        f = self.fixture()
        del f["24"]["31"]
        with self.assertRaisesRegex(ValueError, "BLOCKED_P4C2_NATIVE_OWNER_SET"):
            assess_native(f)
        f = self.fixture()
        f["24"]["31"]["native_alpha_ink_pixels"] = 0
        with self.assertRaisesRegex(ValueError, "BLOCKED_P4C2_NATIVE_TARGET_OR_BLANK"):
            assess_native(f)


if __name__ == "__main__":
    unittest.main()

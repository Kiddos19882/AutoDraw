#!/usr/bin/env python3
"""AWEAK1 fixed source-pixel sensitivity tests, synthetic only, no source GT."""
import unittest
import numpy as np

from run_engine001_bpred_s4r1_aweak1_original_region_hint_diagnostic import (
    CODES, score_human_mark_proxies,
)


def fixture():
    h = w = 14
    labels = np.zeros((h,w,3),dtype=np.uint8)
    labels[4,4] = CODES[1]              # hand critical marker
    labels[7:12,7:12] = CODES[3]        # hand interior 5x5
    protected = np.zeros((h,w),bool)
    protected[4,6] = True               # at Chebyshev distance 2 from K
    unknown = ~protected
    core = np.zeros((h,w),bool)
    core[9,9] = True
    region_ids = np.ones((h,w),np.int32)
    region_ids[7:] = 2
    return labels,protected,unknown,core,region_ids


class TestAWEAK1SourceOnly(unittest.TestCase):
    def test_hand_position_sensitivity_is_not_exact_rgb_gt(self):
        a,p,u,c,ids=fixture()
        out=score_human_mark_proxies(a,p,u,c,ids)
        s=out["K_sensitivity_source_only"]
        self.assertEqual([s[str(r)]["K_near_protected"] for r in (0,2,5)], [0,1,1])
        self.assertEqual(out["source_label_counts"]["K_critical_or_boundary"], 1)
        self.assertEqual(out["source_label_counts"]["human_visual_interior"], 25)
        self.assertFalse(out["human_marks_are_exact_rgb_gt"])
        self.assertEqual(out["strict_s4"],"BLOCKED")

    def test_soft_visual_interior_eroded2_not_guaranteed_safe(self):
        a,p,u,c,ids=fixture()
        out=score_human_mark_proxies(a,p,u,c,ids)
        i=out["I_human_visual_interior"]
        self.assertEqual(i["eroded2_square_count"],1)
        self.assertEqual(i["eroded2_in_potential_core_NOT_safe"],1)
        self.assertEqual(i["raw_in_potential_core_NOT_safe"],1)
        self.assertEqual(out["stroke_admission"],"FORBIDDEN_UNTIL_NATIVE_INDEPENDENT_VALIDATION")

    def test_region_level_touch_no_pixel_color_identity(self):
        a,p,u,c,ids=fixture()
        out=score_human_mark_proxies(a,p,u,c,ids)["SLIC_region_touch_approximation"]
        self.assertEqual(out["total_regions"],2)
        self.assertEqual(out["regions_touched_by_K"],1)
        self.assertEqual(out["regions_touched_by_I"],1)
        self.assertEqual(out["regions_touched_by_both_K_and_I"],0)
        self.assertEqual(out["K_touched_regions_with_any_hypothetical_core"],0)

    def test_human_critical_core_conflict_just_warning(self):
        a,p,u,c,ids=fixture()
        c[4,4]=True
        out=score_human_mark_proxies(a,p,u,c,ids)
        self.assertEqual(out["K_exact_core_conflict_proxy"],1)
        self.assertEqual(out["SLIC_region_touch_approximation"]["K_touched_regions_with_any_hypothetical_core"],1)
        self.assertEqual(out["strict_s4"],"BLOCKED")

    def test_tiny_interior_erodes_to_not_applicable(self):
        a,p,u,c,ids=fixture()
        a[7:12,7:12]=CODES[0]
        a[9,9]=CODES[3]
        out=score_human_mark_proxies(a,p,u,c,ids)
        inner=out["I_human_visual_interior"]
        self.assertEqual(inner["eroded2_square_count"],0)
        self.assertIsNone(inner["eroded2_in_core_fraction"])
        self.assertEqual(inner["eroded2_status"],"NOT_APPLICABLE_NO_ERODED_INTERIOR")

    def test_missing_hand_categories_rejected(self):
        a,p,u,c,ids=fixture()
        a[4,4]=CODES[0]
        with self.assertRaisesRegex(ValueError,"REQUIRED_MARK_TYPES_ABSENT"):
            score_human_mark_proxies(a,p,u,c,ids)

    def test_illegal_label_rgb_rejected(self):
        a,p,u,c,ids=fixture()
        a[1,1]=(250,0,255)
        with self.assertRaisesRegex(ValueError,"INVALID_SOURCE_MARK_RGB_CLASS"):
            score_human_mark_proxies(a,p,u,c,ids)

    def test_misplaced_core_cannot_be_promoted(self):
        a,p,u,c,ids=fixture()
        c[4,6]=True
        with self.assertRaisesRegex(ValueError,"SOURCE_MAP_OR_UNCERTAINTY_CONTRACT"):
            score_human_mark_proxies(a,p,u,c,ids)


if __name__ == "__main__":
    unittest.main()

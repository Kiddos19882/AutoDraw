#!/usr/bin/env python3
"""B2-FULL source model tests only; no native/CHALK quality assertions."""
import unittest
import numpy as np
from run_engine001_v43p4_b2_full_source import (
    EXP, BROAD_WIDTHS, MICRO_LENGTH, micro_candidate, source_plan,
)


class FullB2ResourceTests(unittest.TestCase):
    def setUp(self):
        labels=np.zeros((240,150),dtype=np.int16)
        # Four source owners including both a broad area and singleton details.
        labels[25:43,20:55]=4
        labels[61:82,45:87]=5
        labels[101:117,15:55]=6
        labels[149:182,37:84]=7
        labels[15,15]=4
        labels[90,111]=5
        labels[125,130]=6
        labels[205,100]=7
        self.labels=labels

    def test_micro_owner_kernel_never_invents_native_acceptance(self):
        mask=self.labels==4
        loc=micro_candidate(mask,15,15)
        self.assertIn(15*150+15,loc)
        self.assertTrue(all(mask[x//150,x%150] for x in loc))
        with self.assertRaisesRegex(ValueError,"center"):
            micro_candidate(mask,3,3)

    def test_reproducibility_and_no_old_ids(self):
        p=source_plan(self.labels)
        q=source_plan(self.labels)
        self.assertEqual(p,q)
        self.assertEqual(p["experiment"],EXP)
        self.assertEqual(p["width_sequence"],[10,6,4,2])
        self.assertEqual(p["micro_segment_length_logical_px"],MICRO_LENGTH)
        self.assertFalse(p["safe_to_execute"])
        self.assertFalse(p["native_allowed"])
        self.assertIsNone(p["game_exact_CHALK"])
        self.assertEqual(p["original_A_paint_retained"],0)
        self.assertEqual(p["original_B0_paint_retained"],0)
        self.assertEqual(p["original_B1_paint_retained"],0)
        self.assertFalse(p["details_exact_verified"])
        self.assertLessEqual(p["projected_synthetic_vertices_NOT_CHALK"],5900)
        self.assertLessEqual(p["projected_total_strokes"],3000)
        for s in p["paint_diagnostic_only"]:
            self.assertTrue(s["strokeId"].startswith("p4-b2-"))
            self.assertIn(s["width"],[10,6,4,2])
            self.assertEqual(len(s["points"]),2)
            if s["source_only_stage"]=="micro":
                a,b=s["points"]
                self.assertAlmostEqual(((b["x"]-a["x"])**2+
                                        (b["y"]-a["y"])**2)**.5, .25)
        self.assertTrue(all(str(k) in p["source_model_by_owner"] for k in (4,5,6,7)))

    def test_budget_rejection_is_explicit_not_native(self):
        p=source_plan(self.labels,max_strokes=411,max_vertices=5900)
        self.assertEqual(p["status"],"BLOCKED_RESOURCE")
        self.assertTrue(p["blocked_resource"]["no_partial_native_render"])
        self.assertEqual(p["blocked_resource"]["attempted_total_strokes"],412)
        self.assertEqual(p["projected_total_strokes"],411)
        self.assertFalse(p["safe_to_execute"])
        self.assertFalse(p["native_allowed"])
        self.assertEqual(set(p["model_missing_pixels_by_owner_after_attempt"]),
                         set(map(str,(4,5,6,7))))

    def test_invalid_source_or_caps_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"source labels"):
            source_plan(np.zeros((5,5),np.int16))
        with self.assertRaisesRegex(ValueError,"resource caps"):
            source_plan(self.labels,max_vertices=1)
        empty=self.labels.copy()
        empty[empty==7]=0
        with self.assertRaisesRegex(ValueError,"owner missing"):
            source_plan(empty)


if __name__=="__main__":
    unittest.main()

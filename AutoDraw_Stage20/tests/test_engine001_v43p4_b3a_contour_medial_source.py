#!/usr/bin/env python3
"""V43-P4/B3a source-only tests; actual Egret is a separate E3 gate."""
import unittest

import cv2
import numpy as np

from run_engine001_v43p4_b3a_contour_medial_source import (
    EXP, STAGES, _make_micro_candidates, _medial_on_source, source_plan,
)


class ContourMedialB3aTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        labels=np.zeros((240,150),dtype=np.int16)
        cv2.circle(labels,(34,41),19,4,-1)
        cv2.rectangle(labels,(70,15),(135,68),5,-1)
        cv2.rectangle(labels,(17,102),(56,165),6,-1)
        cv2.circle(labels,(105,164),33,7,-1)
        cv2.circle(labels,(105,164),12,0,-1)
        # One isolated source singleton to check micro fallback.
        labels[217,9]=4
        cls.labels=labels

    def test_zero_penalty_all_owners_resource_and_no_old_strokes(self):
        r=source_plan(self.labels)
        self.assertEqual(r["experiment"],EXP)
        self.assertEqual(r["same_owner_overpaint_penalty"],0)
        self.assertEqual(r["fixed_stage_order"],list(STAGES))
        self.assertEqual(set(r["by_owner"]),{"4","5","6","7"})
        self.assertEqual(r["original_A_B0_B1_B2_B3_paint_retained"],0)
        self.assertFalse(r["safe_to_execute"])
        self.assertTrue(r["frozen_V44B_410_colored_details_required_last"])
        self.assertFalse(r["frozen_V44B_details_exact_verified"])
        self.assertEqual(r["E3_native"],"NOT_RUN")
        self.assertIsNone(r["game_exact_CHALK"])
        self.assertLessEqual(r["total_strokes_including_frozen_410"],3000)
        self.assertLessEqual(r["synthetic_vertices_including_frozen_1792_NOT_CHALK"],5900)
        self.assertEqual(set(x["colorIndex"] for x in r["paint_diagnostic_only"]),
                         {4,5,6,7})
        for s in r["paint_diagnostic_only"]:
            self.assertTrue(s["strokeId"].startswith(f'p4-b3a-{s["colorIndex"]}-'))
            self.assertIn(s["stage"],STAGES)
            self.assertIn(s["width"],(10,6,4,2))
            self.assertTrue(2<=len(s["points"])<=128)
            self.assertTrue(all(155<=p["x"]<305 and 0<=p["y"]<240
                                for p in s["points"]))

    def test_owner_centerline_admission_rejects_foreign_crossing(self):
        mask=np.zeros((240,150),bool)
        mask[45,20:40]=True
        self.assertTrue(_medial_on_source(mask,(21,45),(36,45)))
        mask[45,28]=False
        self.assertFalse(_medial_on_source(mask,(21,45),(36,45)))
        self.assertFalse(_medial_on_source(mask,(21,44),(36,44)))

    def test_micro_candidate_sparse_owner_and_fractional_motion(self):
        mask=np.zeros((240,150),bool)
        mask[50,15]=True
        candidates=_make_micro_candidates(mask,mask.copy())
        self.assertEqual(len(candidates),1)
        s=candidates[0]
        self.assertEqual(s["route_kind"],"short_residual")
        self.assertEqual(s["width"],2)
        self.assertEqual(len(s["owned_index"]),1)
        self.assertEqual(s["owned_index"][0],50*150+15)
        self.assertAlmostEqual(s["points"][1][0]-s["points"][0][0],.25)

    def test_deterministic_and_fail_closed_caps(self):
        first=source_plan(self.labels)
        self.assertEqual(first,source_plan(self.labels))
        limited=source_plan(self.labels,max_vertices=1792)
        self.assertEqual(limited["status"],"BLOCKED_RESOURCE")
        self.assertTrue(limited["resource_blocker"]["no_partial_native_render"])
        self.assertFalse(limited["safe_to_execute"])
        with self.assertRaisesRegex(ValueError,"resource caps"):
            source_plan(self.labels,max_vertices=1791)
        with self.assertRaisesRegex(ValueError,"missing original owner"):
            source_plan(np.zeros((240,150),np.int16))


if __name__=="__main__":
    unittest.main()

#!/usr/bin/env python3
"""P4c1 E2 SOURCE ONLY: original frozen P4c0 identity, direction and micro safety."""
import unittest
import cv2
import numpy as np

from run_engine001_color32_p4c1_directional_micro import (
    _micro,_frozen_base_paths_sha,plan_residual,
    FROZEN_P4C0_PLAN_SHA,WIDTHS,
)
from run_engine001_color32_p4c0_all_owner_feasibility import (
    plan_all_owners,ROI_SHAPE,ROI_X0,FROZEN_DETAILS,FROZEN_DETAIL_VERTICES,
    MAX_PAINT_STROKES,MAX_PAINT_VERTICES,
)

class P4c1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.palette=np.stack([np.arange(32,dtype=np.uint8)]*3,axis=1)
        labels=np.full(ROI_SHAPE,30,dtype=np.uint8)
        cv2.circle(labels,(35,45),20,31,-1)
        cv2.circle(labels,(110,150),19,29,-1)
        labels[95,77]=6  # one-pixel owner, no contour ring possible
        cls.labels=labels
        cls.baseline=[
            {"strokeId":"icon-0","colorIndex":31,"colorRgb":0x1f1f1f,
             "width":4,"points":[{"x":190.,"y":45.},{"x":200.,"y":45.}]},
            {"strokeId":"icon-1","colorIndex":29,"colorRgb":0x1d1d1d,
             "width":4,"points":[{"x":260.,"y":150.},{"x":270.,"y":150.}]},
        ]

    def test_single_pixel_micro_has_two_distinct_endpoints_and_conservative_halo(self):
        owner=self.labels==6
        outside=cv2.distanceTransform((~owner).astype(np.uint8),
                                      cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
        candidate=_micro(6,77,95,self.palette,owner,outside)
        self.assertIsNotNone(candidate)
        self.assertTrue(candidate["micro"])
        self.assertEqual(candidate["width"],2)
        self.assertEqual(len(candidate["points"]),2)
        self.assertAlmostEqual(candidate["points"][1]["x"]-
                               candidate["points"][0]["x"],.25)
        self.assertTrue(len(candidate["own_indices"])>0)
        self.assertIsNone(_micro(6,0,0,self.palette,owner,outside))

    def test_full_source_residual_keeps_baseline_untouched_and_17_budget(self):
        original=[dict(s,points=[dict(p) for p in s["points"]])
                  for s in self.baseline]
        extra,r=plan_residual(self.labels,self.palette,self.baseline,
                              max_paint_strokes=20,max_paint_vertices=50)
        self.assertEqual(self.baseline,original)
        self.assertGreater(r["additional_strokes"],0)
        self.assertEqual(r["original_owners"],[6,29,31])
        self.assertEqual(len(extra),r["additional_strokes"])
        self.assertEqual(len({s["strokeId"] for s in extra}),len(extra))
        self.assertTrue(all(s["width"] in WIDTHS and
                            s["colorIndex"] in (6,29,31) and
                            len(s["points"])==2 for s in extra))
        self.assertLessEqual(r["total_paint_strokes"],20)
        self.assertLessEqual(r["total_paint_vertices_NOT_CHALK"],50)
        self.assertEqual(r["projected_total_strokes_with_frozen_V44B410_LAST"],
                         r["total_paint_strokes"]+FROZEN_DETAILS)
        self.assertEqual(r["projected_total_vertices_with_frozen_V44B1792_NOT_CHALK"],
                         r["total_paint_vertices_NOT_CHALK"]+FROZEN_DETAIL_VERTICES)
        self.assertTrue(r["partial_candidate_not_approved_for_execution"])
        self.assertEqual(r["full_Egret_alpha24_128"],"NOT_RUN")
        self.assertIsNone(r["exact_CHALK"])

    def test_resource_rejection_preserved_without_overrun(self):
        _,r=plan_residual(self.labels,self.palette,self.baseline,
                          max_paint_strokes=3,max_paint_vertices=MAX_PAINT_VERTICES)
        self.assertEqual(r["status"],"BLOCKED_RESOURCE")
        self.assertIsNotNone(r["first_resource_rejection"])
        self.assertEqual(r["total_paint_strokes"],3)
        self.assertLessEqual(r["total_paint_vertices_NOT_CHALK"],MAX_PAINT_VERTICES)

    def test_invalid_input_and_caps_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"BLOCKED_P4C0_SOURCE_OR_PALETTE_SHAPE"):
            plan_residual(self.labels[:10],self.palette,self.baseline)
        with self.assertRaisesRegex(ValueError,"BLOCKED_P4C1_EMPTY_BASE"):
            plan_residual(self.labels,self.palette,[])
        with self.assertRaisesRegex(ValueError,"BLOCKED_P4C1_BUDGET_ARGUMENT"):
            plan_residual(self.labels,self.palette,self.baseline,max_paint_vertices=5900)
        with self.assertRaisesRegex(ValueError,"BLOCKED_P4C1_BASE_OWNERS"):
            plan_residual(self.labels,self.palette,[dict(self.baseline[0],colorIndex=27)])

    def test_original_p4c0_plan_digest_is_version_locked(self):
        # Original artifact-bound SHA check in P4c1.run protects the official
        # source-only negative P4c0 regardless of local synthetic unit fixtures.
        self.assertEqual(len(FROZEN_P4C0_PLAN_SHA),64)
        self.assertNotEqual(_frozen_base_paths_sha(self.baseline),
                            FROZEN_P4C0_PLAN_SHA)


if __name__=="__main__":
    unittest.main()

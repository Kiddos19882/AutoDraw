#!/usr/bin/env python3
"""E2 source gates for ENGINE-001 P3; actual brush geometry requires E3 native PNG."""
import unittest
from unittest.mock import patch

import cv2
import numpy as np

import run_engine001_color32_s2b_egret_p3 as p3


class AdaptiveP3PreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.palette=np.tile(np.arange(32,dtype=np.uint8)[:,None],(1,3))
        cls.labels=np.full(p3.ROI_SHAPE,30,np.uint8)
        cv2.circle(cls.labels,(40,60),24,31,-1)
        cv2.circle(cls.labels,(110,170),25,29,-1)
        cls.initial=[
            {"strokeId":"icon-0","colorIndex":31,"colorRgb":0,
             "width":10,"points":[{"x":185.,"y":60.},{"x":195.,"y":60.}]},
            {"strokeId":"icon-1","colorIndex":29,"colorRgb":0,
             "width":10,"points":[{"x":255.,"y":170.},{"x":265.,"y":170.}]},
        ]

    def test_candidate_directions_and_local_width_safety(self):
        own=self.labels==31
        dt=cv2.distanceTransform(own.astype(np.uint8),cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
        outside=cv2.distanceTransform((~own).astype(np.uint8),cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
        c=p3._candidate(31,(40,60),6,45,own,dt,outside,self.palette)
        self.assertIsNotNone(c)
        self.assertEqual(c["width"],6)
        self.assertEqual(c["angle_degrees_undirected"],45)
        self.assertEqual(c["points"][0]["x"]-155,c["points"][0]["y"])
        self.assertIn(30,p3.WIDTHS)
        self.assertIn(165,p3.ANGLES)
        self.assertEqual(len(p3.ANGLES),12)
        for bad in ((0,0),(100,100)):
            self.assertIsNone(p3._candidate(31,bad,30,0,own,dt,outside,self.palette))

    def test_deterministic_residual_paths_and_reserved_resource(self):
        with patch.object(p3,"MAX_SEEDS_PER_OWNER",8):
            paths, report=p3.plan_p3(self.labels,self.palette,self.initial,
                                     max_additional=5)
            again,other=p3.plan_p3(self.labels,self.palette,self.initial,
                                   max_additional=5)
        self.assertEqual((paths,report),(again,other))
        self.assertEqual(report["status"],"SOURCE_READY_FOR_E3")
        self.assertGreater(len(paths),0)
        self.assertLessEqual(len(paths),5)
        self.assertEqual(report["same_color_overlap_penalty"],0)
        self.assertTrue(all(s["width"] in p3.WIDTHS for s in paths))
        self.assertTrue(all(2==len(s["points"]) for s in paths))
        self.assertLessEqual(report["planned_total_strokes_with_frozen_V44B410"],3000)
        self.assertLessEqual(report["planned_total_vertices_with_frozen_V44B_NOT_CHALK"],5900)
        self.assertEqual(len(set(s["strokeId"] for s in paths)),len(paths))
        self.assertTrue(all(s["colorIndex"] in p3.OWNERS for s in paths))

    def test_invalid_owner_mask_and_baseline_are_blocked(self):
        with self.assertRaisesRegex(ValueError,"BLOCKED_P3_INPUT"):
            p3.plan_p3(self.labels[:10],self.palette,self.initial)
        with self.assertRaisesRegex(ValueError,"BLOCKED_P3_INPUT"):
            p3.plan_p3(self.labels,self.palette,[])
        with self.assertRaisesRegex(ValueError,"BLOCKED_P3_INPUT"):
            p3.plan_p3(self.labels,self.palette,self.initial,max_additional=241)
        with self.assertRaisesRegex(ValueError,"BLOCKED_P3_BASE_PLAN"):
            p3.plan_p3(self.labels,self.palette,
                       [{**self.initial[0],"colorIndex":25}])

    def test_native_gate_separates_gain_halo_and_full_quality(self):
        def row(own,foreign=0,far=0):
            return {
                "owner_target_backing_pixels":1000,
                "native_correct_owner_pixels":own,
                "non_owner_native_pixels_any_distance":foreign,
                "non_owner_beyond_3logical_px":far,
                "ink_outside_image_ROI":0,
            }
        before={str(a):{str(o):row(700) for o in p3.OWNERS}
                for a in p3.ALPHAS}
        after={str(a):{str(o):row(800,foreign=3) for o in p3.OWNERS}
               for a in p3.ALPHAS}
        good=p3.native_compare(before,after)
        self.assertTrue(good["native_incremental_gate_pass"])
        self.assertFalse(good["both_owners_99pct_at_alpha24"])
        after["128"]["29"]["non_owner_beyond_3logical_px"]=1
        self.assertFalse(p3.native_compare(before,after)["native_incremental_gate_pass"])
        after["128"]["29"]["non_owner_beyond_3logical_px"]=0
        after["24"]["29"]["native_correct_owner_pixels"]=705
        self.assertFalse(p3.native_compare(before,after)["native_incremental_gate_pass"])
        after["24"]["29"]["native_correct_owner_pixels"]=800
        before["24"]["31"]["owner_target_backing_pixels"]=2000
        with self.assertRaisesRegex(ValueError,"BLOCKED_P3_TARGET_DRIFT"):
            p3.native_compare(before,after)


if __name__=="__main__":
    unittest.main()

#!/usr/bin/env python3
"""B3 contour-parallel source-only regressions (no true Egret proof)."""
import unittest

import cv2
import numpy as np

from run_engine001_v43p4_b3_contour_source import (
    EXP, SHAPE, WIDTHS, _footprint, contour_candidates, source_plan,
)


class ContourParallelB3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data=np.zeros(SHAPE,np.int16)
        cv2.circle(data,(35,45),23,4,-1)
        cv2.circle(data,(35,45),8,0,-1)
        cv2.rectangle(data,(75,22),(135,66),5,-1)
        cv2.rectangle(data,(20,102),(72,156),6,-1)
        cv2.circle(data,(106,173),35,7,-1)
        cv2.circle(data,(106,173),18,0,-1)
        cv2.circle(data,(114,205),4,7,-1)
        cls.labels=data

    def test_contours_holes_and_disconnected_source_regions(self):
        mask=self.labels==7
        loops=contour_candidates(mask,4)
        self.assertGreater(len(loops),1)
        self.assertTrue(all(x["vertices"]<=128 for x in loops))
        self.assertTrue(all(x["width"]==4 for x in loops))
        # Valid long straight ring edges must NOT be rejected simply by
        # their vertex spacing. Assert source-boundness, including holes.
        outside=cv2.distanceTransform(
            (~mask).astype(np.uint8),cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
        for ring in loops:
            ink=_footprint(ring["points"],ring["width"])
            self.assertFalse(np.any(ink & (outside>3.0)))
        self.assertGreater(len(contour_candidates(self.labels==4,2)),0)

    def test_all_owner_fair_selection_and_zero_overlap_penalty(self):
        result=source_plan(self.labels)
        self.assertEqual(result["experiment"],EXP)
        self.assertEqual(result["own_color_overlap_penalty"],0)
        self.assertFalse(result["safe_to_execute"])
        self.assertTrue(result["no_original_A_B0_B1_B2_paint"])
        self.assertEqual(result["required_original_V44B_detail_strokes_last"],410)
        self.assertEqual(set(result["source_only_diagnostics"]),{"4","5","6","7"})
        self.assertEqual(set(x["colorIndex"] for x in result["paint_diagnostic_only"]),
                         {4,5,6,7})
        self.assertLessEqual(result["projected_total_strokes"],3000)
        self.assertLessEqual(result["projected_total_vertices_NOT_CHALK"],5900)
        self.assertTrue(all(x["strokeId"].startswith("p4-b3-")
                            for x in result["paint_diagnostic_only"]))
        self.assertTrue(all(x["width"] in WIDTHS and
                            len(x["points"])<=128 for x in result["paint_diagnostic_only"]))
        self.assertTrue(all(155<=p["x"]<305 and 0<=p["y"]<240
                            for x in result["paint_diagnostic_only"]
                            for p in x["points"]))
        self.assertIsNone(result["game_exact_CHALK"])

    def test_model_footprint_never_more_than_three_logical_px_from_owner(self):
        result=source_plan(self.labels)
        outside={}
        for owner in (4,5,6,7):
            outside[owner]=cv2.distanceTransform(
                (self.labels!=owner).astype(np.uint8),
                cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
        for route in result["paint_diagnostic_only"]:
            points=[(p["x"]-155,p["y"]) for p in route["points"]]
            ink=_footprint(points,route["width"])
            self.assertFalse(np.any(ink & (outside[route["colorIndex"]]>3.0)))

    def test_deterministic_and_fail_closed_resource(self):
        first=source_plan(self.labels)
        self.assertEqual(first,source_plan(self.labels))
        limited=source_plan(self.labels,max_vertices=1792)
        self.assertEqual(limited["status"],"BLOCKED_RESOURCE")
        self.assertTrue(limited["blocked_resource"]["no_partial_native_render"])
        self.assertFalse(limited["safe_to_execute"])
        with self.assertRaisesRegex(ValueError,"resource caps"):
            source_plan(self.labels,max_vertices=1791)
        with self.assertRaisesRegex(ValueError,"missing"):
            source_plan(np.zeros(SHAPE,np.int16))
        with self.assertRaisesRegex(ValueError,"source labels"):
            source_plan(np.zeros((2,2),np.int16))


if __name__=="__main__":
    unittest.main()

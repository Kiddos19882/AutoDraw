#!/usr/bin/env python3
"""P4c0 source-only B3 all-owner feasibility regressions, not native quality."""
import unittest
import cv2
import numpy as np
from run_engine001_color32_p4c0_all_owner_feasibility import (
    _validate,plan_all_owners,WHITE,WIDTHS,
    MAX_PAINT_STROKES,MAX_PAINT_VERTICES,
    FROZEN_DETAILS,FROZEN_DETAIL_VERTICES,
)

class P4c0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.palette=np.stack([np.arange(32,dtype=np.uint8)]*3,axis=1)
        labels=np.full((240,150),WHITE,np.uint8)
        cv2.circle(labels,(42,60),26,31,-1)
        cv2.circle(labels,(103,166),20,29,-1)
        cls.labels=labels

    def test_two_colored_owners_and_white_exclusion(self):
        self.assertEqual(_validate(self.labels,self.palette),[29,31])
        paths,r=plan_all_owners(self.labels,self.palette,cap=3)
        self.assertEqual(r["nonwhite_owners"],[29,31])
        self.assertGreater(len(paths),0)
        self.assertEqual(len(paths),r["paint_strokes"])
        self.assertEqual(len({s["strokeId"] for s in paths}),len(paths))
        self.assertTrue(all(s["colorIndex"] in (29,31) for s in paths))
        self.assertTrue(all(s["width"] in WIDTHS for s in paths))
        self.assertEqual(r["source_model_outside_limit_logical_px"],2.0)
        self.assertTrue(all(2<=len(s["points"])<=128 for s in paths))
        self.assertLessEqual(r["paint_strokes"],MAX_PAINT_STROKES)
        self.assertLessEqual(r["paint_vertices_NOT_CHALK"],MAX_PAINT_VERTICES)
        self.assertEqual(r["planned_total_strokes_with_V44B410"],
                         r["paint_strokes"]+FROZEN_DETAILS)
        self.assertEqual(r["planned_total_vertices_with_V44B1792_NOT_CHALK"],
                         r["paint_vertices_NOT_CHALK"]+FROZEN_DETAIL_VERTICES)
        self.assertEqual(r["native_E3"],"NOT_RUN")
        self.assertIsNone(r["exact_CHALK"])
        for s in paths:
            rgb=self.palette[s["colorIndex"]]
            self.assertEqual(s["colorRgb"],(int(rgb[0])<<16)|(int(rgb[1])<<8)|int(rgb[2]))

    def test_input_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"BLOCKED_P4C0_SOURCE_OR_PALETTE_SHAPE"):
            _validate(self.labels[:10],self.palette)
        with self.assertRaisesRegex(ValueError,"BLOCKED_P4C0_SOURCE_OR_PALETTE_SHAPE"):
            _validate(self.labels,self.palette[:10])
        with self.assertRaisesRegex(ValueError,"BLOCKED_P4C0_NO_COLOR_OWNERS"):
            _validate(np.full((240,150),WHITE,np.uint8),self.palette)
        with self.assertRaisesRegex(ValueError,"BLOCKED_P4C0_RESOURCE_ARGUMENT"):
            plan_all_owners(self.labels,self.palette,max_vertices=MAX_PAINT_VERTICES+1)
        with self.assertRaisesRegex(ValueError,"BLOCKED_P4C0_RESOURCE_ARGUMENT"):
            plan_all_owners(self.labels,self.palette,max_strokes=0)
        with self.assertRaisesRegex(ValueError,"BLOCKED_P4C0_RESOURCE_ARGUMENT"):
            plan_all_owners(self.labels,self.palette,cap=99)

    def test_budget_failure_records_first_rejection_and_never_accepts_partial(self):
        _,r=plan_all_owners(self.labels,self.palette,max_strokes=1,
                            max_vertices=6,cap=3)
        self.assertEqual(r["status"],"BLOCKED_RESOURCE")
        self.assertIsNotNone(r["first_rejected_resource"])
        self.assertTrue(r["partial_source_paths_not_accepted"])
        self.assertFalse(r["safe_to_execute_game"])
        self.assertEqual(r["paint_strokes"],1)
        self.assertLessEqual(r["paint_vertices_NOT_CHALK"],6)
        self.assertEqual(r["game_foreign_3px"],"NOT_RUN")

if __name__=="__main__":
    unittest.main()

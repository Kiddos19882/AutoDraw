#!/usr/bin/env python3
"""S5-R3 synthetic E2 long-path region/capsule invariants."""
import unittest
import numpy as np
from engine001_bpred_s5r3_clearance_paths import build_candidates
from engine001_bpred_s5r2_region_candidates import swept_capsule_pixel_masks, BlockedS5R2


def scene(game,regions=None,dots=()):
    a=np.asarray(game,dtype=np.int16)
    h,w=a.shape
    ids=np.where(a>=0,1,0).astype(np.int32) if regions is None else np.asarray(regions,dtype=np.int32)
    rgba=np.zeros((h,w,4),dtype=np.uint8)
    rgba[a>=0,3]=255
    p=np.zeros((h,w),dtype=bool)
    for y,x in dots:p[y,x]=True
    return {"game_index":a,"paintable_id":ids,"original_rgba":rgba,"protected_original_dot":p}


class S5R3Test(unittest.TestCase):
    def assert_safe(self,a,r):
        self.assertEqual(r["drawing_mode"],"normal")
        self.assertIs(r["smooth"],False)
        self.assertFalse(r["safe_to_execute"])
        self.assertFalse(r["admissible_for_gameplay"])
        self.assertLessEqual(r["phase_trials"]["broad"],1400)
        self.assertLessEqual(r["phase_trials"]["detail"],600)
        self.assertLessEqual(r["phase_strokes"]["broad"],80)
        self.assertLessEqual(r["phase_strokes"]["detail"],120)
        self.assertEqual(r["status"],"PARTIAL" if r["uncovered_potential_pixel_count"] else "MODEL_ONLY")
        h,w=a["game_index"].shape
        union=set()
        for s in r["proposals"]:
            self.assertIs(s["smooth"],False)
            self.assertFalse(s["safe_to_execute"])
            self.assertTrue(1<=s["brush_value"]<=10)
            pixels=swept_capsule_pixel_masks(s["points"],s["brush_value"],1.,1.,w,h)["potential_cells"]
            for x,y in pixels:
                self.assertEqual(int(a["paintable_id"][y,x]),s["paintable_id"])
                self.assertEqual(int(a["game_index"][y,x]),s["color_index"])
                self.assertEqual(int(a["original_rgba"][y,x,3]),255)
            union.update(pixels)
        self.assertEqual(len(union),r["potential_covered_pixel_count"])

    def test_long_horizontal_rectangle_and_determinism(self):
        a=scene(np.full((28,96),4,dtype=np.int16),dots=((0,0),))
        r=build_candidates(a)
        self.assert_safe(a,r)
        self.assertGreater(r["phase_strokes"]["broad"],0)
        self.assertTrue(any(abs(s["points"][1][0]-s["points"][0][0])>20
                            for s in r["proposals"] if s["phase"]=="broad"))
        self.assertEqual(r,build_candidates(a))

    def test_vertical_ribbon(self):
        a=scene(np.full((90,18),4,dtype=np.int16))
        r=build_candidates(a)
        self.assert_safe(a,r)
        self.assertTrue(any(abs(s["points"][1][1]-s["points"][0][1])>30
                            for s in r["proposals"] if s["phase"]=="broad"))

    def test_hole_neck_and_alpha_wall(self):
        m=np.full((44,64),5,dtype=np.int16)
        m[12:27,21:43]=-1
        m[28:41,32:34]=-1
        a=scene(m)
        self.assert_safe(a,build_candidates(a))

    def test_two_regions_same_palette(self):
        a=np.full((35,55),5,dtype=np.int16)
        ids=np.ones_like(a,dtype=np.int32)
        ids[:,28:]=2
        self.assert_safe(scene(a,ids),build_candidates(scene(a,ids)))

    def test_thin_diagonal_checker_and_protected(self):
        a=np.full((25,25),-1,dtype=np.int16)
        np.fill_diagonal(a,3)
        self.assert_safe(scene(a,dots=((7,7),)),build_candidates(scene(a,dots=((7,7),))))
        check=np.indices((12,12)).sum(axis=0).astype(np.int16)%2
        labels=np.arange(1,145,dtype=np.int32).reshape(12,12)
        self.assert_safe(scene(check,labels),build_candidates(scene(check,labels)))

    def test_invalid_and_budget(self):
        a=scene(np.ones((5,5),dtype=np.int16))
        for k in ({"max_trials":0},{"max_trials":True},{"max_strokes":201}):
            with self.assertRaises(BlockedS5R2): build_candidates(a,**k)
        invalid=scene(np.array([[1,2]],dtype=np.int16),np.array([[1,1]],dtype=np.int32))
        with self.assertRaises(BlockedS5R2):build_candidates(invalid)

if __name__=="__main__":
    unittest.main()

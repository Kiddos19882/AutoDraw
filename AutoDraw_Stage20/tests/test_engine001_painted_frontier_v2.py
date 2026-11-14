"""Synthetic safeguards for frozen painted-stroke-frontier hypothesis V2."""
import unittest
import numpy as np
from run_engine001_painted_frontier_v2 import (
    HEIGHT, WIDTH, MAX_CONTOURS, measure_halo, plan_painted_frontier,
    painted_frontier_candidates, permitted_halo
)

class PaintedFrontierV2Tests(unittest.TestCase):
    @staticmethod
    def shape():
        m=np.zeros((HEIGHT,WIDTH),dtype=bool)
        m[35:190,48:200]=True
        m[79:146,85:150]=False
        m[40:186,255:415]=True
        m[88:132,275:395]=False
        return m

    def test_halo_near_vs_far(self):
        mask=np.zeros((720,1380),dtype=bool)
        mask[150:450,120:510]=True
        native=mask.copy()
        native[149,200]=True
        native[138,200]=True
        halo=measure_halo(mask,native)
        self.assertGreater(halo["leaked_native_pixels"],0)
        self.assertEqual(halo["farther_than_3logical_native_pixels"],1)
        self.assertFalse(halo["all_leakage_in_3logical_halo"])

    def test_painted_boundary_not_target_border(self):
        painted=np.zeros((720,1380),dtype=bool)
        painted[150:160,200:600]=True
        candidates=painted_frontier_candidates(painted)
        self.assertTrue(candidates)
        self.assertTrue(any(abs(p["y"]-50)<5 for c in candidates for p in c["points"]))

    def test_deterministic(self):
        a,meta,_=plan_painted_frontier(self.shape())
        b,meta2,_=plan_painted_frontier(self.shape())
        self.assertEqual(a,b)
        self.assertEqual(meta["candidate_decisions"],meta2["candidate_decisions"])

    def test_no_short_repairs_and_bounds(self):
        strokes,meta,images=plan_painted_frontier(self.shape())
        self.assertGreater(len(strokes),0)
        self.assertLessEqual(meta["accepted_frontier_contours"],MAX_CONTOURS)
        self.assertEqual(images["target"].shape,(720,1380))
        self.assertTrue(all(len(s["points"])>=2 for s in strokes))
        self.assertTrue(all(0<=p["x"]<WIDTH and 0<=p["y"]<HEIGHT
                            for s in strokes for p in s["points"]))
        self.assertTrue(all(d["far_overshoot_pixels"]==0
                            for d in meta["candidate_decisions"] if d["accepted"]))

    def test_bad_inputs_fail_closed(self):
        with self.assertRaises(ValueError):
            plan_painted_frontier(np.zeros((HEIGHT,WIDTH-1),dtype=bool))
        with self.assertRaises(ValueError):
            permitted_halo(np.zeros((HEIGHT,WIDTH),dtype=bool))


if __name__=="__main__":
    unittest.main()

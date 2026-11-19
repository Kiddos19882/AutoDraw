"""P4D17 isolated E2 contracts for native physical owner-aware repair."""
import unittest
import numpy as np

import run_engine001_b1r_p4d17_owner_physical_repair as p

class P4D17Contracts(unittest.TestCase):
    def test_01_stable_owner_grouping(self):
        plan=[{"colorIndex":3,"k":1},{"colorIndex":8,"k":2},
              {"colorIndex":3,"k":3},{"colorIndex":8,"k":4},
              {"colorIndex":7,"k":5}]
        original=[(x["colorIndex"],x["k"]) for x in plan]
        a=p.grouped(plan)
        b=p.grouped(plan,True)
        self.assertEqual([x["k"] for x in a],[1,3,2,4,5])
        self.assertEqual([x["k"] for x in b],[5,2,4,1,3])
        self.assertEqual([(x["colorIndex"],x["k"]) for x in plan],original)
    def test_02_source_strict_interior(self):
        index=np.full((240,150),p.WHITE,np.uint8)
        index[10:15,10:15]=8
        safe=p.strict_interior(index)
        self.assertTrue(safe[12,12])
        self.assertFalse(safe[10,10])
        self.assertFalse(safe[9,12])
        self.assertFalse(safe[15,12])
        self.assertFalse(safe[0,0])
    def test_03_baseline_priority_and_non_degradation(self):
        base={"correct_owner_backing_pixels":1000,
              "original_white_alpha24_backing":5,
              "protected_original_white_alpha24_backing":2,
              "logical_correct5":500,
              "far_gt3logical_native_ink_alpha24_diagnostic":0}
        a={**base,"correct_owner_backing_pixels":1002}
        b={**base,"correct_owner_backing_pixels":1050,"original_white_alpha24_backing":6}
        self.assertEqual(p.choose_arm({"BASELINE":base,
            "OWNER_FIRST_OCCURRENCE":a,"OWNER_REVERSED":b}),"OWNER_FIRST_OCCURRENCE")
        self.assertFalse(p.baseline_guard(base,b))
        self.assertTrue(p.baseline_guard(base,base))
    def test_04_real_native_uses_composite_not_plan(self):
        native=np.zeros((720,1380,4),np.uint8)
        index=np.full((240,150),p.WHITE,np.uint8)
        index[50:70,50:70]=7
        palette=np.full((128,3),255,np.uint8)
        palette[7]=[23,34,45]
        real,counts,diff=p.physical_owner_score(native,index,palette)
        self.assertEqual(real.shape,(720,450))
        self.assertEqual(counts.shape,(240,150))
        self.assertEqual(int(counts[55,55]),0)
        self.assertFalse(real.any())
    def test_05_repair_not_boundary_not_white(self):
        native=np.zeros((720,1380,4),np.uint8)
        index=np.full((240,150),p.WHITE,np.uint8)
        index[50:54,50:54]=7
        palette=np.full((128,3),255,np.uint8)
        palette[7]=[23,34,45]
        repairs,meta=p.repair_plan(index,palette,native)
        self.assertTrue(meta["strict_source_3x3_owner_only"])
        self.assertEqual(len(repairs),4)
        self.assertTrue(all(s["colorIndex"]==7 and s["width"]==1 and
                            len(s["points"])==2 for s in repairs))
        for stroke in repairs:
            x=float(stroke["points"][0]["x"])-p.X0
            y=float(stroke["points"][0]["y"])
            self.assertGreater(x,49.5)
            self.assertLess(x,53.5)
            self.assertGreater(y,49.5)
            self.assertLess(y,53.5)
    def test_06_dot_phase_from_egret_halfpixel(self):
        idx=np.full((240,150),p.WHITE,np.uint8)
        idx[20:23,20:23]=9
        pal=np.full((128,3),255,np.uint8);pal[9]=[20,30,40]
        native=np.zeros((720,1380,4),np.uint8)
        strokes,_=p.repair_plan(idx,pal,native)
        self.assertEqual(len(strokes),1)
        # Central safe source cell is (21,21), target physical subpixel (0,0).
        got=(strokes[0]["points"][0]["x"]+
             strokes[0]["points"][1]["x"])/2-p.X0+.5
        self.assertAlmostEqual(got,21.+1./6.)
        self.assertAlmostEqual(strokes[0]["points"][0]["y"]+.5,21.+1./6.)
    def test_07_no_other_owner_neighborhood(self):
        idx=np.full((240,150),p.WHITE,np.uint8)
        idx[20:23,20:23]=9
        idx[20,20]=8
        pal=np.full((128,3),255,np.uint8)
        native=np.zeros((720,1380,4),np.uint8)
        strokes,_=p.repair_plan(idx,pal,native)
        self.assertEqual(len(strokes),0)
    def test_08_input_guards(self):
        with self.assertRaises(ValueError):
            p.grouped([])
        with self.assertRaises(ValueError):
            p.strict_interior(np.zeros((5,5),np.uint8))
        with self.assertRaises(ValueError):
            p.repair_plan(np.zeros((240,150),np.uint8),np.zeros((128,3),np.uint8),
                          np.zeros((720,1380,4),np.uint8),100)
    def test_09_bounded_deterministic_order(self):
        self.assertEqual(p.MAX_EXTRA_STROKES,1200)
        self.assertEqual(p.ARMS,("BASELINE","OWNER_FIRST_OCCURRENCE",
                               "OWNER_REVERSED","INTERIOR_SUBPIXEL_REPAIR"))

if __name__=="__main__":
    unittest.main()

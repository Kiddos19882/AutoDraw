"""P4D18 E2 fixed-margin source-owner math, never a native quality proxy."""
import unittest
import numpy as np
import run_engine001_b1r_p4d18_physical_owner_edt_repair as p

class PhysicalOwnerEDTRepairTests(unittest.TestCase):
    def test_01_preregistered_three_margins_only(self):
        self.assertEqual(p.MARGINS,{"EDT_MARGIN_2P7":2.7,
                                    "EDT_MARGIN_2P1":2.1,
                                    "EDT_MARGIN_1P6":1.6})
        self.assertEqual(p.LIMIT,600)
        self.assertEqual(len(p.ARMS),4)
    def test_02_physical_edt_distance_foreign(self):
        idx=np.full((240,150),p.WHITE,np.uint8)
        idx[20:23,20:23]=7
        d=p.physical_owner_distance(idx)
        self.assertEqual(d.shape,(720,450))
        self.assertEqual(d.dtype,np.float32)
        self.assertEqual(float(d[19*3,21*3]),0.)
        self.assertGreater(float(d[21*3+1,21*3+1]),4.)
    def test_03_zero_unsafe_area_never_repair(self):
        idx=np.full((240,150),p.WHITE,np.uint8)
        idx[20,20]=7
        palette=np.full((128,3),255,np.uint8)
        native=np.zeros((720,1380,4),np.uint8)
        strokes,meta=p.repair_physical_edt(idx,palette,native,2.7)
        self.assertEqual(len(strokes),0)
        self.assertEqual(meta["eligible_logical_cells"],0)
    def test_04_repair_phase_width1_correct_owner(self):
        idx=np.full((240,150),p.WHITE,np.uint8)
        idx[20:24,20:24]=7
        palette=np.full((128,3),255,np.uint8)
        palette[7]=[21,31,41]
        native=np.zeros((720,1380,4),np.uint8)
        strokes,meta=p.repair_physical_edt(idx,palette,native,2.1)
        self.assertGreater(len(strokes),0)
        self.assertTrue(all(s["colorIndex"]==7 and s["width"]==1 and
                           len(s["points"])==2 for s in strokes))
        self.assertEqual(meta["new_width1_strokes"],len(strokes))
    def test_05_stricter_monotone_eligible(self):
        idx=np.full((240,150),p.WHITE,np.uint8)
        idx[20:25,20:25]=7
        palette=np.full((128,3),255,np.uint8)
        native=np.zeros((720,1380,4),np.uint8)
        arms=[p.repair_physical_edt(idx,palette,native,m)[1] for m in (2.7,2.1,1.6)]
        self.assertLessEqual(arms[0]["eligible_wrong_physical_backing"],
                             arms[1]["eligible_wrong_physical_backing"])
        self.assertLessEqual(arms[1]["eligible_wrong_physical_backing"],
                             arms[2]["eligible_wrong_physical_backing"])
    def test_06_invalid_margin_fails_closed(self):
        idx=np.full((240,150),p.WHITE,np.uint8)
        palette=np.full((128,3),255,np.uint8)
        native=np.zeros((720,1380,4),np.uint8)
        with self.assertRaises(ValueError):
            p.repair_physical_edt(idx,palette,native,1.0)
        with self.assertRaises(ValueError):
            p.physical_owner_distance(np.zeros((3,3),np.uint8))
    def test_07_logical_original_interior(self):
        idx=np.full((240,150),p.WHITE,np.uint8)
        idx[50:70,50:70]=9
        native=np.zeros((720,1380,4),np.uint8)
        v=p.nonwhite_interior_alpha0(native,idx)
        self.assertGreater(v["interior_nonwhite_alpha0"],0)
        self.assertEqual(v["interior_nonwhite_alpha0"],v["interior_nonwhite_below24"])

if __name__=="__main__":
    unittest.main()

"""P4D13 E2 only: source-color residual runs and alpha/RGB shape contracts."""
import unittest
import numpy as np

import run_engine001_b1r_p4d13_full_original_relaxed_finish as d


def fixture():
    palette=np.zeros((128,3),np.uint8)
    palette[6]=(255,255,255)
    palette[7]=(90,40,120)
    palette[8]=(30,130,70)
    index=np.full((240,150),6,np.uint8)
    index[44,40:43]=7
    index[44,43]=8
    index[45,42]=7
    return index,palette


class P4D13NativeFullRelaxedTest(unittest.TestCase):
    def test_01_experiment_is_full_original_not_p4d8_crop(self):
        self.assertEqual(d.EXPERIMENT,
            "ENGINE001_B1R_P4D13_FULL_ORIGINAL_RELAXED_FINISH_V1")
        self.assertEqual(d.METHODS,("E_SOBEL90","F_SOBEL90_LAB12"))
        self.assertEqual(d.MAX_REPAIR_ROUNDS,3)
        self.assertEqual(d.BOARD_SHAPE,(720,1380,4))

    def test_02_whole_source_correct_initially_zero(self):
        index,palette=fixture()
        raw=np.zeros(d.BOARD_SHAPE,np.uint8)
        state=d.full_source_state(raw,index,palette)
        self.assertEqual(state.shape,(240,150))
        self.assertEqual(int(state.sum()),0)

    def test_03_native_5_of_9_source_owner_correct(self):
        index,palette=fixture()
        raw=np.zeros(d.BOARD_SHAPE,np.uint8)
        xx=(d.X0+40)*3
        for k in range(5):
            yx,xd=divmod(k,3)
            raw[44*3+yx,xx+xd,:3]=palette[7]
            raw[44*3+yx,xx+xd,3]=255
        state=d.full_source_state(raw,index,palette)
        self.assertTrue(state[44,40])
        self.assertEqual(int(state.sum()),1)

    def test_04_owner_runs_may_adjoin_other_colors(self):
        index,palette=fixture()
        state=np.zeros((240,150),bool)
        strokes=d.residual_owner_runs(index,state,palette)
        self.assertEqual(len(strokes),3)
        self.assertEqual([s["colorIndex"] for s in strokes],[7,8,7])
        self.assertTrue(all(s["width"]==1 for s in strokes))
        self.assertEqual(strokes[0]["points"][0]["x"],d.X0+40+.125)
        self.assertEqual(strokes[0]["points"][-1]["x"],d.X0+42+.375)

    def test_05_correct_one_skipped_without_requiring_neighbor_safe(self):
        index,palette=fixture()
        state=np.zeros((240,150),bool)
        state[44,41]=True
        strokes=d.residual_owner_runs(index,state,palette)
        self.assertEqual([s["colorIndex"] for s in strokes],[7,7,8,7])
        self.assertEqual(len(strokes),4)

    def test_06_original_white_never_planned_for_repair(self):
        index,palette=fixture()
        state=np.zeros((240,150),bool)
        strokes=d.residual_owner_runs(index,state,palette)
        self.assertTrue(all(x["colorIndex"]!=d.WHITE for x in strokes))

    def test_07_fail_closed_malformed_native_state(self):
        index,palette=fixture()
        with self.assertRaises(ValueError):
            d.full_source_state(np.zeros((24,24,4),np.uint8),index,palette)
        with self.assertRaises(ValueError):
            d.full_source_state(np.zeros(d.BOARD_SHAPE,np.uint8),
                                index.astype(np.int32),palette)

    def test_08_fail_closed_bad_source_mask_or_state(self):
        index,palette=fixture()
        with self.assertRaises(ValueError):
            d.residual_owner_runs(index,np.zeros((24,24),bool),palette)
        with self.assertRaises(ValueError):
            d.residual_owner_runs(index,np.zeros((240,150),np.uint8),palette)

    def test_09_soft_repair_does_not_claim_actual_chalk_or_native_in_units(self):
        index,palette=fixture()
        strokes=d.residual_owner_runs(index,np.zeros((240,150),bool),palette)
        self.assertTrue(strokes)
        self.assertFalse(any("chalk" in s for s in strokes))
        self.assertEqual(d.RGB_TOL,32)
        self.assertEqual(d.MIN_CORRECT_SUBPIXELS,5)


if __name__=="__main__":
    unittest.main()

"""P4D8 E2 contracts: cumulative Egret state/risk scoring (not native evidence)."""
from __future__ import annotations

import unittest

import numpy as np

import run_engine001_b1r_p4d8_native_cumulative_phase_pixel_state as d
import run_engine001_b1r_p4d7_native_width1_phase_feasibility as p4d7
import run_engine001_b1r_p4d5_pixel_state_native_feedback as p4d5


def fixture():
    index=np.full((240,150),6,np.uint8)
    index[45,40]=7
    index[45,41]=8
    palette=np.zeros((128,3),np.uint8)
    palette[6]=(255,255,255)
    palette[7]=(50,70,90)
    palette[8]=(110,90,60)
    return index,palette


def paint(native,index,palette,x,y,owner=None,alpha=255,amount=9):
    result=native.copy()
    if owner is None:
        owner=int(index[y,x])
    column=(p4d5.X0+x)*3
    for k in range(amount):
        dy,dx=divmod(k,3)
        result[y*3+dy,column+dx,:3]=palette[owner]
        result[y*3+dy,column+dx,3]=alpha
    return result


class P4D8CumulativeContracts(unittest.TestCase):
    def setUp(self):
        self.index,self.palette=fixture()
        self.blank=np.zeros(p4d5.BOARD_SHAPE,np.uint8)
        self.sample={"owner":7,"x":40,"y":45}

    def measure(self,before,after,sample=None):
        return d.trial_metrics(before,after,self.index,self.palette,
                p4d5.actual_state(before,self.index,self.palette),
                sample or self.sample)

    def test_01_frozen_experiment_source_and_21_samples(self):
        self.assertEqual(d.EXPERIMENT,
            "ENGINE001_B1R_P4D8_NATIVE_CUMULATIVE_PHASE_OWNER_PIXEL_V1")
        self.assertEqual(d.EXPECTED_SAMPLES,21)
        self.assertEqual(d.EXPECTED_ISOLATED,1386)
        self.assertEqual(len(p4d7.VARIANTS),66)
        self.assertEqual(d.CROP,(40,45,64,69))

    def test_02_safe_real_rgba_state_gain(self):
        after=paint(self.blank,self.index,self.palette,40,45,amount=5)
        row=self.measure(self.blank,after)
        self.assertTrue(row["accepted"])
        self.assertEqual(row["native_new_correct_0_to_1"],1)
        self.assertEqual(row["native_lost_correct_1_to_0"],0)
        self.assertEqual(row["native_changed_foreign_alpha24_backing"],0)

    def test_03_cumulative_preserves_old_good_ones(self):
        before=paint(self.blank,self.index,self.palette,40,45)
        after=paint(before,self.index,self.palette,41,45)
        row=self.measure(before,after,{"owner":8,"x":41,"y":45})
        self.assertTrue(row["accepted"])
        self.assertEqual((row["native_new_correct_0_to_1"],
                          row["native_lost_correct_1_to_0"]),(1,0))
        self.assertEqual(row["total_correct_after"],2)

    def test_04_source_foreign_alpha24_rejected(self):
        after=paint(self.blank,self.index,self.palette,40,45)
        after=paint(after,self.index,self.palette,41,45,owner=7)
        row=self.measure(self.blank,after)
        self.assertFalse(row["accepted"])
        self.assertEqual(row["native_changed_foreign_alpha24_backing"],9)

    def test_05_white_source_alpha24_rejected(self):
        after=paint(self.blank,self.index,self.palette,40,45)
        after=paint(after,self.index,self.palette,42,45,owner=7)
        row=self.measure(self.blank,after)
        self.assertFalse(row["accepted"])
        self.assertEqual(row["native_original_white_alpha24_backing"],9)

    def test_06_previous_correct_1_to_0_is_rejected(self):
        before=paint(self.blank,self.index,self.palette,40,45)
        after=paint(before,self.index,self.palette,41,45)
        after=paint(after,self.index,self.palette,40,45,owner=8)
        row=self.measure(before,after,{"owner":8,"x":41,"y":45})
        self.assertFalse(row["accepted"])
        self.assertEqual(row["native_lost_correct_1_to_0"],1)

    def test_07_alpha1_foreign_diagnostic_without_alpha24(self):
        after=paint(self.blank,self.index,self.palette,40,45)
        after=paint(after,self.index,self.palette,41,45,owner=7,alpha=10)
        row=self.measure(self.blank,after)
        self.assertTrue(row["accepted"])
        self.assertEqual(row["native_changed_foreign_alpha24_backing"],0)
        self.assertEqual(row["native_changed_foreign_alpha1_backing"],9)

    def test_08_only_real_isolated_safe_phases_and_deterministic_rank(self):
        row=lambda name,correct,alpha1,feasible=True:{
            "sample_id":"A","variant":name,"width":1,
            "measured":{"phase_feasible":feasible,
                        "native_exact_sample_cell_correct_5of9":True,
                        "native_alpha24_genuine_foreign_backing":0,
                        "native_other_correct_logical_in_crop":correct,
                        "native_alpha1_genuine_foreign_backing":alpha1}}
        v=d.eligible_rows([row("GRID_X0_Y0",1,10),
              row("GRID_X0_Y1",2,5),row("GRID_X0_Y2",9,0,False)],{"A"})
        self.assertEqual([x["variant"] for x in v],["GRID_X0_Y1","GRID_X0_Y0"])
        bad=row("GRID_X0_Y0",1,0)
        bad["measured"]["native_alpha24_genuine_foreign_backing"]=1
        with self.assertRaises(ValueError):
            d.eligible_rows([bad],{"A"})

    def test_09_fail_closed_shapes_and_unmatched_owner(self):
        with self.assertRaises(ValueError):
            d.trial_metrics(np.zeros((1,1,4),np.uint8),self.blank,
                self.index,self.palette,np.zeros((240,150),bool),self.sample)
        with self.assertRaises(ValueError):
            self.measure(self.blank,self.blank,{"owner":8,"x":40,"y":45})


if __name__=="__main__":
    unittest.main()

"""P4D11 E2 strict/soft/adaptive policy; no model-only brush quality claims."""
import unittest
import numpy as np

import run_engine001_b1r_p4d11_soft_adaptive_native_foreign_touch as d
import run_engine001_b1r_p4d5_pixel_state_native_feedback as p4d5
import run_engine001_b1r_p4d8_native_cumulative_phase_pixel_state as p4d8


def base(gain=1,loss=0,white=0,foreign=1):
    return {
        "target_sample_after":True,"target_sample_before":False,
        "native_new_correct_0_to_1":gain,
        "native_lost_correct_1_to_0":loss,
        "native_original_white_alpha24_backing":white,
        "native_changed_foreign_alpha24_backing":foreign,
        "accepted":foreign==0 and gain>0 and loss==0 and white==0,
    }


def impact(foreign=1,rgb=9,near=1,repairable=1,outboard=0):
    return {
        "foreign_changed_alpha24":foreign,
        "foreign_backing_max_visible_RGB_channel_delta":rgb,
        "foreign_max_Chebyshev_logical_distance_from_sample":near,
        "foreign_repairable_sample_backing":repairable,
        "foreign_outboard_backing":outboard,
    }


class P4D11NativeSoftAdaptive(unittest.TestCase):
    def test_01_pre_registered_arms_and_original_quality_gate(self):
        self.assertEqual(len(d.ARMS),5)
        self.assertEqual(d.BUDGETS["STRICT_P4D8"],0)
        self.assertEqual([d.BUDGETS[a] for a in d.ARMS[1:]], [1,2,3,2])
        self.assertEqual(d.RGB_MAX_DELTA,12)
        self.assertEqual(d.REPAIR_DISTANCE,1)
        self.assertEqual(d.BASELINE["source_owner_correct"],17)
        self.assertEqual(d.EXPERIMENT,
            "ENGINE001_B1R_P4D11_SOFT_ADAPTIVE_NATIVE_FOREIGN_TOUCH_V1")

    def test_02_soft_1_2_3_exact_physical_budgets(self):
        for n in (1,2,3,4):
            bb=base(foreign=n)
            ii=impact(foreign=n,repairable=n)
            for arm,limit in ((d.ARMS[1],1),(d.ARMS[2],2),(d.ARMS[3],3)):
                self.assertEqual(d.select_by_policy(arm,bb,ii),n<=limit)

    def test_03_adaptive_rgb_local_repairable(self):
        self.assertTrue(d.select_by_policy(
            d.ARMS[4],base(foreign=2),impact(foreign=2,rgb=12,near=1,repairable=2)))
        self.assertFalse(d.select_by_policy(
            d.ARMS[4],base(foreign=2),impact(foreign=2,rgb=13,near=1,repairable=2)))
        self.assertFalse(d.select_by_policy(
            d.ARMS[4],base(foreign=2),impact(foreign=2,rgb=12,near=2,repairable=2)))
        self.assertFalse(d.select_by_policy(
            d.ARMS[4],base(foreign=2),impact(foreign=2,rgb=12,near=1,repairable=1)))

    def test_04_zero_damage_zero_white_remain_hard_in_all_arms(self):
        for arm in d.ARMS:
            self.assertFalse(d.select_by_policy(arm,base(loss=1,foreign=0),impact(foreign=0,repairable=0)))
            self.assertFalse(d.select_by_policy(arm,base(white=1,foreign=0),impact(foreign=0,repairable=0)))
            self.assertFalse(d.select_by_policy(arm,base(gain=0,foreign=0),impact(foreign=0,repairable=0)))
            self.assertFalse(d.select_by_policy(arm,base(foreign=1),impact(outboard=1)))

    def test_05_strict_parent_parity_and_nonmatch_fail_closed(self):
        self.assertTrue(d.select_by_policy(d.ARMS[0],base(foreign=0),impact(foreign=0,repairable=0)))
        self.assertFalse(d.select_by_policy(d.ARMS[0],base(foreign=1),impact()))
        with self.assertRaises(ValueError):
            d.select_by_policy("SOFT_100",base(foreign=1),impact())
        with self.assertRaises(ValueError):
            d.select_by_policy(d.ARMS[0],base(foreign=0),impact(foreign=1))

    def test_06_true_native_foreign_mask_and_neighbor_distance(self):
        index=np.full((240,150),6,np.uint8)
        index[45,40]=7
        index[45,41]=8
        palette=np.zeros((128,3),np.uint8)
        palette[6]=(255,255,255)
        palette[7]=(50,70,90)
        palette[8]=(110,90,60)
        before=np.zeros(p4d5.BOARD_SHAPE,np.uint8)
        after=before.copy()
        left=(p4d5.X0+40)*3
        after[45*3:46*3,left:left+3,:3]=palette[7]
        after[45*3:46*3,left:left+3,3]=255
        foreign=(p4d5.X0+41)*3
        after[45*3+1,foreign,:3]=palette[7]
        after[45*3+1,foreign,3]=255
        sample={"x":40,"y":45,"owner":7,"sample_id":"A"}
        neighbor={"x":41,"y":45,"owner":8,"sample_id":"B"}
        measured,mask=d.actual_foreign_impact(
            before,after,index,7,sample,{"A":sample,"B":neighbor})
        self.assertEqual(measured["foreign_changed_alpha24"],1)
        self.assertEqual(measured["foreign_backing_max_visible_RGB_channel_delta"],205)
        self.assertEqual(measured["foreign_max_Chebyshev_logical_distance_from_sample"],1)
        self.assertEqual(measured["foreign_repairable_sample_backing"],1)
        self.assertEqual(int(mask.sum()),1)

    def test_07_actual_composite_small_delta_can_be_conditionally_adaptive(self):
        index=np.full((240,150),6,np.uint8)
        index[45,40]=7
        index[45,41]=8
        before=np.zeros(p4d5.BOARD_SHAPE,np.uint8)
        after=before.copy()
        x=(p4d5.X0+41)*3;y=45*3+1
        before[y,x,:3]=(110,90,60);before[y,x,3]=100
        after[y,x,:3]=(105,88,58);after[y,x,3]=102
        sample={"x":40,"y":45,"owner":7,"sample_id":"A"}
        neighbor={"x":41,"y":45,"owner":8,"sample_id":"B"}
        m,_=d.actual_foreign_impact(before,after,index,7,sample,
                                    {"A":sample,"B":neighbor})
        self.assertEqual(m["foreign_changed_alpha24"],1)
        self.assertLessEqual(m["foreign_backing_max_visible_RGB_channel_delta"],12)
        self.assertEqual(m["foreign_repairable_sample_backing"],1)

    def test_08_wrong_native_shapes_fail_closed(self):
        index=np.full((240,150),6,np.uint8)
        before=np.zeros(p4d5.BOARD_SHAPE,np.uint8)
        with self.assertRaises(ValueError):
            d.actual_foreign_impact(np.zeros((2,2,4),np.uint8),before,
                                    index,7,{"x":40,"y":45},{})

    def test_09_frozen_parent_state_not_reimplemented(self):
        self.assertEqual(d.CROP,p4d8.CROP)
        self.assertIs(d.p4d8.trial_metrics,p4d8.trial_metrics)
        self.assertIs(d.p4d5._native,p4d5._native)
        self.assertFalse(hasattr(d,"CHALK_ESTIMATOR"))


if __name__=="__main__":
    unittest.main()

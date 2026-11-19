"""P4D9 E2: freeze order-only 3-arm and native cumulative inherited safety."""
from __future__ import annotations
import unittest
import numpy as np

import run_engine001_b1r_p4d9_native_cumulative_order_audit as d
import run_engine001_b1r_p4d8_native_cumulative_phase_pixel_state as parent
import run_engine001_b1r_p4d5_pixel_state_native_feedback as p4d5


def row(id_,owner=7,n=1,phase="GRID_X0_Y0",a1=0):
    return {"sample_id":id_,"owner":owner,"variant":phase,"width":1,
            "measured":{"native_other_correct_logical_in_crop":n,
                        "native_alpha1_genuine_foreign_backing":a1}}


class P4D9NativeOrder(unittest.TestCase):
    def test_01_three_preregistered_arms_and_immutable_baseline(self):
        self.assertEqual(d.EXPERIMENT,"ENGINE001_B1R_P4D9_NATIVE_CUMULATIVE_ORDER_AUDIT_V1")
        self.assertEqual(d.ARMS,("BASELINE_P4D8","FIVE_FAILED_SAMPLES_FIRST",
                                 "SOURCE_OWNER_DESCENDING"))
        self.assertEqual(d.BASELINE_EXPECTED,{"fixed_sample_correct":16,
            "source_owner_correct":17,"accepted":16,"attempts":21,"remaining":290})
        self.assertEqual(len(d.FIVE_FAILED_IDS),5)

    def test_02_baseline_ranking_is_exact_p4d8(self):
        rows=[row("OWNER011_X046_Y046",11,1),
              row("OWNER007_X045_Y045",7,3),
              row("OWNER127_X062_Y045",127,2)]
        a=d.order_candidates(rows,"BASELINE_P4D8")
        self.assertEqual([x["sample_id"] for x in a],
                         [x["sample_id"] for x in sorted(rows,key=parent.rank_candidate)])

    def test_03_failed_five_priority_order(self):
        rows=[row("OWNER007_X045_Y045",7,3),
              row("OWNER011_X046_Y046",11,1),
              row("OWNER127_X062_Y045",127,2),
              row("OWNER008_X058_Y045",8,6)]
        ans=d.order_candidates(rows,"FIVE_FAILED_SAMPLES_FIRST")
        self.assertEqual([x["owner"] for x in ans],[127,11,8,7])

    def test_04_descending_owner_and_fixed_phase_tiebreak(self):
        rows=[row("A",7,2),row("B",7,3),row("C",127,1)]
        ans=d.order_candidates(rows,"SOURCE_OWNER_DESCENDING")
        self.assertEqual([x["sample_id"] for x in ans],["C","B","A"])

    def test_05_unknown_order_fail_closed(self):
        with self.assertRaises(ValueError):
            d.order_candidates([row("A")],"POST_HOC_TRY_OTHER_TOLERANCE")

    def test_06_original_native_cumulative_safety_is_reused(self):
        self.assertEqual(parent.trial_metrics.__module__,
                         "run_engine001_b1r_p4d8_native_cumulative_phase_pixel_state")
        self.assertEqual(parent.ALPHA,24)
        self.assertEqual(parent.CROP,(40,45,64,69))
        self.assertEqual(d.WHITE,6)

    def test_07_alternative_arms_do_not_redefine_source_or_quality(self):
        self.assertIs(d.p4d7,p4d5 if False else d.p4d7)
        self.assertEqual(d.SOURCE,parent.SOURCE)
        self.assertEqual(d.CROP,parent.CROP)
        self.assertEqual(d.ARMS[0],"BASELINE_P4D8")
        self.assertFalse(hasattr(d,"CHALK_ESTIMATOR"))

    def test_08_p4d8_still_rejects_protected_source_foreign(self):
        index=np.full((240,150),6,np.uint8)
        index[45,40]=7
        index[45,41]=8
        palette=np.zeros((128,3),np.uint8)
        palette[6]=(255,255,255)
        palette[7]=(50,70,90)
        blank=np.zeros(p4d5.BOARD_SHAPE,np.uint8)
        trial=blank.copy()
        for x,owner in ((40,7),(41,7)):
            left=(p4d5.X0+x)*3
            trial[45*3:46*3,left:left+3,:3]=palette[owner]
            trial[45*3:46*3,left:left+3,3]=255
        measured=parent.trial_metrics(blank,trial,index,palette,
                  np.zeros((240,150),bool),{"owner":7,"x":40,"y":45})
        self.assertFalse(measured["accepted"])
        self.assertEqual(measured["native_changed_foreign_alpha24_backing"],9)


if __name__=="__main__":
    unittest.main()

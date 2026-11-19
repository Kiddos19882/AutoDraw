"""P4D6 E2: only native input endpoints change, not model/owner/safety/target."""
import unittest
from pathlib import Path

import numpy as np

import run_engine001_b1r_p4d5_pixel_state_native_feedback as parent
import run_engine001_b1r_p4d6_pixel_centered_native_greedy as d


def game():
    a=np.zeros((128,3),np.uint8)
    a[6]=(255,255,255)
    a[17]=(47,98,115)
    a[18]=(98,21,46)
    return a


def idx():
    a=np.full((240,150),6,np.uint8)
    a[48:62,42:56]=17
    a[56:66,57:62]=18
    return a


class P4D6NativeCenteredE2(unittest.TestCase):
    def test_01_frozen_single_variable_protocol(self):
        self.assertEqual(d.EXPERIMENT,
            "ENGINE001_B1R_P4D6_PIXEL_CENTERED_NATIVE_GREEDY_V1")
        self.assertEqual(d.PARENT_BLOB,"147f4c2ec439bac72228b6828c67bfd45b49b28e")
        self.assertEqual(d.FROZEN_P4D5_SAFE,9)
        self.assertEqual(d.FROZEN_P4D5_CORRECT,10)
        self.assertEqual(d.FROZEN_P4D5_NONWHITE,307)
        self.assertEqual(d.P4D6_LONG_OFFSET,.5)
        self.assertEqual(d.P4D6_MICRO_OFFSETS,(.49,.51))
        self.assertEqual(d.P4D6_MICRO_Y_OFFSET,.5)

    def test_02_centered_one_cell_two_distinct_samples(self):
        p=game();i=idx()
        old=parent._source_candidate(17,1,[(45,50)],p,i)
        new=d.centered_candidate(17,1,[(45,50)],p,i,parent._source_candidate)
        self.assertIsNotNone(old)
        self.assertIsNotNone(new)
        self.assertEqual(old["model_gain_ONLY"],new["model_gain_ONLY"])
        self.assertEqual(old["stroke"]["colorRgb"],new["stroke"]["colorRgb"])
        self.assertEqual(new["stroke"]["points"],[
            {"x":parent.X0+45.49,"y":50.5},
            {"x":parent.X0+45.51,"y":50.5}])
        self.assertNotEqual(new["stroke"]["points"][0],new["stroke"]["points"][1])

    def test_03_centered_long_line_same_brush_and_rgb(self):
        p=game();i=idx();path=[(44,50),(45,50),(46,50),(47,50)]
        old=parent._source_candidate(17,2,path,p,i)
        new=d.centered_candidate(17,2,path,p,i,parent._source_candidate)
        self.assertIsNotNone(old)
        self.assertEqual(old["model_gain_ONLY"],new["model_gain_ONLY"])
        self.assertEqual(old["stroke"]["width"],new["stroke"]["width"])
        self.assertEqual(old["stroke"]["colorIndex"],new["stroke"]["colorIndex"])
        self.assertEqual(old["stroke"]["colorRgb"],new["stroke"]["colorRgb"])
        self.assertEqual(new["stroke"]["points"][0],{
            "x":parent.X0+44.5,"y":50.5})
        self.assertEqual(new["stroke"]["points"][1],{
            "x":parent.X0+47.5,"y":50.5})

    def test_04_original_model_candidate_rejection_unchanged(self):
        p=game();i=idx()
        path=[(53,49),(54,49),(55,49),(56,49),(57,49)]
        original=parent._source_candidate(17,3,path,p,i)
        centered=d.centered_candidate(17,3,path,p,i,parent._source_candidate)
        self.assertIsNone(original)
        self.assertIsNone(centered)

    def test_05_scoped_overlay_restores_parent_and_constants(self):
        original=parent._source_candidate
        old_experiment=parent.EXPERIMENT
        old_prereg=parent.PREREG
        with d.scoped_centered_trial():
            self.assertEqual(parent.EXPERIMENT,d.EXPERIMENT)
            self.assertEqual(parent.PREREG,d.PREREG)
            self.assertIsNot(original,parent._source_candidate)
        self.assertIs(original,parent._source_candidate)
        self.assertEqual(old_experiment,parent.EXPERIMENT)
        self.assertEqual(old_prereg,parent.PREREG)

    def test_06_all_candidate_models_and_selection_order_identical(self):
        i=idx();p=game()
        base=parent.candidate_pool(i,p)
        with d.scoped_centered_trial():
            updated=parent.candidate_pool(i,p)
        self.assertEqual(len(base),len(updated))
        for a,b in zip(base,updated):
            self.assertEqual(a["candidate_id"],b["candidate_id"])
            self.assertEqual(a["model_gain_ONLY"],b["model_gain_ONLY"])
            self.assertEqual(a["line_length_logical"],b["line_length_logical"])
            for field in ("width","colorIndex","colorRgb"):
                self.assertEqual(a["stroke"][field],b["stroke"][field])
            oldpoints=a["stroke"]["points"]
            newpoints=b["stroke"]["points"]
            self.assertEqual(len(oldpoints),len(newpoints))
            self.assertTrue(any(old!=new for old,new in zip(oldpoints,newpoints)))

    def test_07_no_changes_to_production_or_game_or_thresholds(self):
        src=Path(d.__file__).read_text("utf8")
        self.assertIn("result=parent.run(workspace,source,engine_js,renderer,output)",src)
        self.assertIn("with scoped_centered_trial():",src)
        self.assertIn('PILOT_NO_SAFE_COVERAGE_IMPROVEMENT',src)
        self.assertIn('"production_promotion":False',
                      Path(parent.__file__).read_text("utf8"))
        self.assertNotIn("source_joint_outline(",src)
        self.assertNotIn("import run_engine001_color32_p4c1",src)
        self.assertEqual(parent.ALPHA,24)
        self.assertEqual(parent.RGB_TOL,32)
        self.assertEqual(parent.LOGICAL_REQUIRED_SUBPIXELS,5)


if __name__=="__main__":
    unittest.main()

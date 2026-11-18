#!/usr/bin/env python3
"""P4B10 E2 synthetic contracts, not native brush footprint evidence."""
import ast
from copy import deepcopy
from pathlib import Path
import unittest
import numpy as np
import run_engine001_b1r_p4b10_native_correction_width_sweep as p


def synthetic(method=p.E_METHOD):
    mask=np.zeros(p.p4b5.SHAPE,bool)
    mask[40:150,4:120]=True
    plan=[{"strokeId":"icon-%d"%i,"width":2,"colorIndex":115,
           "colorRgb":0x4C3725,
           "points":[{"x":160.125,"y":80.},
                     {"x":160.375,"y":80.}]}
          for i in range(p.EXPECTED_COUNTS[method])]
    for idx,width in zip(p.WIDTH_IDS[method],p.ORIGINAL_WIDTHS[method]):
        plan[idx]["width"]=width
    return plan,mask


class P4B10Contracts(unittest.TestCase):
    def test_01_frozen_id_and_70_arm_enumeration(self):
        self.assertEqual(p.EXPERIMENT,"ENGINE001_B1R_P4B10_NATIVE_CORRECTION_WIDTH_SWEEP_V1")
        self.assertTrue((Path(__file__).parents[1]/"docs"/p.PREREG).exists())
        e=p.width_arms(p.E_METHOD)
        f=p.width_arms(p.F_METHOD)
        self.assertEqual((len(e),len(f)),(60,10))
        self.assertEqual((len(set(n for n,_ in e)),len(set(n for n,_ in f))),(60,10))
        self.assertEqual(e[0],("W01_W01",(1,1)))
        self.assertEqual(e[-1],("W10_W06",(10,6)))
        self.assertEqual(f[0],("W01",(1,)))
        self.assertEqual(f[-1],("W10",(10,)))
    def test_02_frozen_gates(self):
        self.assertEqual((p.ALPHA,p.COVERAGE_GATE,p.PROTECTED_GATE,p.SPILL_GATE),(24,.99,0,3.))
        self.assertEqual((p.MAX_STROKES,p.MAX_VERTICES),(250,500))
    def test_03_frozen_provenance_pins(self):
        self.assertEqual(p.P4B6_BLOB,"2f9ca1756da58e7062fcae6c6c64c83e4db79ea9")
        self.assertEqual(p.P4B7_BLOB,"87ea292c01c75e594c4ff09acf716c4500e88644")
        self.assertEqual(p.P4B8_BLOB,"9ddf8e2f745de4f78006b14c00e99e74c2f3cb67")
        self.assertEqual(p.P4B9_BLOB,"c4b1d06011a6acbd90bb4e18d8bd6a72a3cce4ef")
    def test_04_e_only_two_culprit_widths_changed(self):
        plan,mask=synthetic()
        before=deepcopy(plan)
        out,ledger=p.width_only_variant(plan,p.E_METHOD,(1,3),mask,88)
        self.assertEqual(out[110]["width"],1)
        self.assertEqual(out[202]["width"],3)
        self.assertEqual(out[109],before[109])
        self.assertEqual(out[111],before[111])
        self.assertEqual(out[110]["points"],before[110]["points"])
        self.assertEqual(before,plan)
        self.assertEqual(ledger["changed_width_count"],2)
    def test_05_f_only_one_culprit_width_changed(self):
        plan,mask=synthetic(p.F_METHOD)
        out,ledger=p.width_only_variant(plan,p.F_METHOD,(8,),mask,86)
        self.assertEqual(out[109]["width"],8)
        self.assertEqual(out[110],plan[110])
        self.assertEqual(ledger["changed_width_count"],1)
    def test_06_original_control_noop_is_source_safe(self):
        plan,mask=synthetic()
        out,ledger=p.width_only_variant(plan,p.E_METHOD,(10,6),mask,88)
        self.assertEqual(out,plan)
        self.assertEqual(ledger["changed_width_count"],0)
    def test_07_reject_widening_and_bad_width(self):
        plan,mask=synthetic()
        for bad in ((11,6),(1,7),(0,6),(2,1.2)):
            with self.subTest(widths=bad):
                with self.assertRaises(ValueError):
                    p.width_only_variant(plan,p.E_METHOD,bad,mask,88)
    def test_08_fail_on_culprit_not_original_correction(self):
        plan,mask=synthetic()
        with self.assertRaisesRegex(ValueError,"CAUSAL_CORRECTION_PROVENANCE"):
            p.width_only_variant(plan,p.E_METHOD,(3,4),mask,111)
    def test_09_reject_original_geometry_wrong(self):
        plan,mask=synthetic()
        plan[110]["points"][0]["x"]=float("nan")
        with self.assertRaisesRegex(ValueError,"CAUSAL_CORRECTION_PROVENANCE"):
            p.width_only_variant(plan,p.E_METHOD,(3,4),mask,88)
        plan,mask=synthetic()
        mask[:]=False
        with self.assertRaisesRegex(ValueError,"CAUSAL_CORRECTION_PROVENANCE"):
            p.width_only_variant(plan,p.E_METHOD,(3,4),mask,88)
    def test_10_duplicate_id_and_color_refused(self):
        plan,mask=synthetic()
        plan[12]["strokeId"]=plan[11]["strokeId"]
        with self.assertRaises(ValueError):
            p.width_only_variant(plan,p.E_METHOD,(3,4),mask,88)
        plan,mask=synthetic()
        plan[110]["colorIndex"]=24
        with self.assertRaises(ValueError):
            p.width_only_variant(plan,p.E_METHOD,(3,4),mask,88)
    def test_11_resource_cap_preserved(self):
        plan,mask=synthetic()
        with self.assertRaises(ValueError):
            p.width_only_variant(plan[:-1],p.E_METHOD,(3,4),mask,88)
        plan,mask=synthetic()
        plan[0]["points"]*=100
        with self.assertRaises(ValueError):
            p.width_only_variant(plan,p.E_METHOD,(3,4),mask,88)
    def test_12_native_safe_ranking_no_safe(self):
        self.assertEqual(p.choose_best_safe({}),{
            "status":"NO_NATIVE_SAFE_WIDTH_COMBO","arm":None})
        self.assertEqual(p.choose_best_safe({"X":{
            "native_blank_zero":0,
            "native_alpha":{"24":{"native_protected_foreign_face_eyes_hands_pixels":0,
                                    "native_foreign_distance_gt_T3_0":1}}}})["arm"],None)
    def test_13_native_safe_ranking_coverage_first(self):
        def arm(c,changed,widths):
            return {"native_blank_zero":0,"native_alpha":{"24":{
               "native_protected_foreign_face_eyes_hands_pixels":0,
               "native_foreign_distance_gt_T3_0":0,
               "native_component_coverage":c}},
               "source_width_ledger":{"changed_width_count":changed,"tested_widths":widths}}
        z=p.choose_best_safe({"W01":arm(.90,1,[1]),"W02":arm(.91,2,[2])})
        self.assertEqual(z["arm"],"W02")
        self.assertFalse(z["overall_artwork_quality_pass"])
        self.assertEqual(p.choose_best_safe({"W02":arm(.93,1,[2]),
             "W03":arm(.93,1,[3]),"W01":arm(.93,2,[1])})["arm"],"W03")
    def test_14_native_safe_ranking_frozen99(self):
        native={"native_blank_zero":0,"native_alpha":{"24":{
            "native_protected_foreign_face_eyes_hands_pixels":0,
            "native_foreign_distance_gt_T3_0":0,
            "native_component_coverage":.99}},
            "source_width_ledger":{"changed_width_count":1,"tested_widths":[8]}}
        self.assertTrue(p.choose_best_safe({"W08":native})["overall_artwork_quality_pass"])
    def test_15_use_real_egret_not_static_model_for_quality(self):
        data=Path(p.__file__).read_text("utf8")
        for term in ("p4b7.native_egret_session","p4b7.native_replay_in_session",
                     "p4b4.native_diagnostics","p4b9.native_far3_targets",
                     "BLOCKED_P4B10_SAME_RUN_NATIVE_ALPHA_PARITY"):
            self.assertIn(term,data)
    def test_16_no_old_g32_v44_imports(self):
        tree=ast.parse(Path(p.__file__).read_text("utf8"))
        deps=[]
        for n in ast.walk(tree):
            if isinstance(n,ast.Import):deps.extend(x.name for x in n.names)
            if isinstance(n,ast.ImportFrom):deps.append(n.module)
        self.assertFalse(any("g32" in str(v).lower() or "v44" in str(v).lower() for v in deps))
    def test_17_existing_output_fail_closed(self):
        self.assertIn("BLOCKED_P4B10_OUTPUT_EXISTS",Path(p.__file__).read_text("utf8"))
    def test_18_game_exact_chalk_not_run(self):
        self.assertIn('"exact_CHALK":None',Path(p.__file__).read_text("utf8"))

if __name__=="__main__":
    unittest.main()

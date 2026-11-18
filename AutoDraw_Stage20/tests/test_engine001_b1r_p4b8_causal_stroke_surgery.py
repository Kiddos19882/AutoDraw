#!/usr/bin/env python3
"""P4B8 source-causal geometry E2, no native-image quality proxy."""
import ast
from copy import deepcopy
from pathlib import Path
import unittest
import numpy as np
import run_engine001_b1r_p4b8_causal_stroke_surgery as p

def synth(method="E_SOBEL90"):
    region=np.zeros(p.p4b5.SHAPE,bool)
    region[40:150,4:120]=True
    strokes=[{"strokeId":"icon-%d"%i,"width":1+i%10,
              "colorIndex":115,"colorRgb":0x4c3725,
              "points":[{"x":160.125,"y":80.},{"x":160.375,"y":80.}]}
             for i in range(p.COUNTS[method])]
    return strokes,region

class P4B8Contracts(unittest.TestCase):
    def test_01_prereg_and_arm_count(self):
        self.assertEqual(p.EXPERIMENT,"ENGINE001_B1R_P4B8_CAUSAL_STROKE_SURGERY_V1")
        self.assertEqual(p.ARMS,("DROP2","WIDTH1","TRIM50","WIDTH1_TRIM50"))
        self.assertTrue((Path(__file__).parents[1]/"docs"/p.PREREG).exists())
    def test_02_locked_native_gates(self):
        self.assertEqual((p.COVERAGE_GATE,p.SPILL_GATE,p.MAX_STROKES,p.MAX_VERTICES,p.ALPHA),
                         (.99,3.,250,500,24))
        self.assertEqual(p.TARGETS,((191,833),(275,776)))
    def test_03_actual_source_component_validation(self):
        plan,mask=synth()
        self.assertTrue(p.supported(plan[100],mask))
        mask[:]=False
        self.assertFalse(p.supported(plan[100],mask))
    def test_04_drop_two_preserves_original(self):
        plan,mask=synth();before=deepcopy(plan)
        actual,ledger=p.surgery(plan,"E_SOBEL90","DROP2",mask,88)
        self.assertEqual(len(actual),212)
        self.assertEqual(actual[-1]["strokeId"],"icon-211")
        self.assertEqual(actual[100]["points"],plan[101]["points"])
        self.assertEqual(before,plan)
        self.assertTrue(ledger["nonculprit_geometry_unchanged"])
    def test_05_width_one_only_two(self):
        plan,mask=synth();before=deepcopy(plan)
        got,_=p.surgery(plan,"E_SOBEL90","WIDTH1",mask,88)
        self.assertEqual((got[100]["width"],got[114]["width"]),(1,1))
        self.assertEqual(got[99],before[99])
        self.assertEqual(plan,before)
    def test_06_trim_interpolation_and_nonmutation(self):
        plan,mask=synth();before=deepcopy(plan)
        got,_=p.surgery(plan,"E_SOBEL90","TRIM50",mask,88)
        self.assertAlmostEqual(got[100]["points"][0]["x"],160.1875)
        self.assertAlmostEqual(got[100]["points"][1]["x"],160.3125)
        self.assertEqual(got[100]["width"],plan[100]["width"])
        self.assertEqual(before,plan)
    def test_07_combination_both_changes(self):
        plan,mask=synth()
        got,_=p.surgery(plan,"E_SOBEL90","WIDTH1_TRIM50",mask,88)
        for i in p.CULPRITS["E_SOBEL90"]:
            self.assertEqual(got[i]["width"],1)
            self.assertAlmostEqual(got[i]["points"][0]["x"],160.1875)
    def test_08_f_culprit_positions(self):
        plan,mask=synth("F_SOBEL90_LAB12")
        got,_=p.surgery(plan,"F_SOBEL90_LAB12","DROP2",mask,86)
        self.assertEqual(len(got),210)
        self.assertEqual(got[98]["points"],plan[99]["points"])
    def test_09_culprit_must_be_repair(self):
        plan,mask=synth()
        with self.assertRaisesRegex(ValueError,"CULPRIT_NOT_CORRECTION"):
            p.surgery(plan,"E_SOBEL90","DROP2",mask,101)
    def test_10_invalid_ids_and_wrong_colors(self):
        plan,mask=synth()
        plan[3]["strokeId"]=plan[4]["strokeId"]
        with self.assertRaises(ValueError):
            p.surgery(plan,"E_SOBEL90","WIDTH1",mask,88)
        plan,mask=synth()
        plan[100]["colorIndex"]=23
        with self.assertRaises(ValueError):
            p.surgery(plan,"E_SOBEL90","WIDTH1",mask,88)
    def test_11_nonfinite_and_outside_source(self):
        plan,mask=synth()
        plan[100]["points"][0]["x"]=float("nan")
        with self.assertRaisesRegex(ValueError,"SOURCE_UNSUPPORTED"):
            p.surgery(plan,"E_SOBEL90","TRIM50",mask,88)
        plan,mask=synth()
        plan[100]["points"][0]["x"]=300.
        with self.assertRaisesRegex(ValueError,"SOURCE_UNSUPPORTED"):
            p.surgery(plan,"E_SOBEL90","WIDTH1",mask,88)
    def test_12_resource_gate(self):
        plan,mask=synth()
        with self.assertRaises(ValueError):
            p.surgery(plan[:-1],"E_SOBEL90","DROP2",mask,88)
        plan,mask=synth()
        plan[0]["points"]=plan[0]["points"]*100
        with self.assertRaises(ValueError):
            p.surgery(plan,"E_SOBEL90","DROP2",mask,88)
    def test_13_old_G32_V44_not_imported(self):
        tree=ast.parse(Path(p.__file__).read_text("utf8"))
        deps=[]
        for n in ast.walk(tree):
            if isinstance(n,ast.Import):deps.extend([a.name for a in n.names])
            if isinstance(n,ast.ImportFrom):deps.append(n.module)
        self.assertFalse(any("g32" in (x or "").lower() or "v44" in (x or "").lower()
                             for x in deps))
    def test_14_frozen_parent_blobs(self):
        self.assertEqual(p.P4B6_BLOB,"2f9ca1756da58e7062fcae6c6c64c83e4db79ea9")
        self.assertEqual(p.P4B7_BLOB,"87ea292c01c75e594c4ff09acf716c4500e88644")
    def test_15_actual_native_renderer_only(self):
        code=Path(p.__file__).read_text("utf8")
        for part in ("p4b7.native_egret_session","p4b7.native_replay_in_session",
                     "p4b4.native_diagnostics","np.array_equal(control[:,:,3]",
                     "BLOCKED_P4B8_REUSED_FIREFOX_ALPHA_DRIFT"):
            self.assertIn(part,code)
    def test_16_existing_output_fail_closed(self):
        self.assertIn("BLOCKED_P4B8_OUTPUT_EXISTS",Path(p.__file__).read_text("utf8"))

if __name__=="__main__":
    unittest.main()

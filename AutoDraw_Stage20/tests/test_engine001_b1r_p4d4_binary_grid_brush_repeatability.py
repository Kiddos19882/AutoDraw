"""P4D4 independent diagnosis: exact binary relative point offsets; E2 only."""
import unittest

import run_engine001_b1r_p4d3_native_brush_repeatability as p3
import run_engine001_b1r_p4d4_binary_grid_brush_repeatability as d


class QuantizedRepeatabilityContracts(unittest.TestCase):
    def test_01_fixed_scope_and_parent(self):
        self.assertEqual(d.EXPERIMENT,
            "ENGINE001_B1R_P4D4_BINARY_GRID_TRANSLATION_REPRODUCIBILITY_V1")
        self.assertEqual(d.GRID,256)
        self.assertEqual(d.PARENT_BLOB,"3437a9326b381d9c94d6ade80059d40adf233d09")
        self.assertEqual(d.FROZEN_P4D3_WITHIN_SAME_SCENE_EXACT,292)
        self.assertEqual(d.EXPECTED_PRIMARY,480)

    def test_02_all_width_angles_lengths_identical_relative_binary_coords(self):
        for length in p3.LENGTHS:
            for width in p3.WIDTHS:
                for angle in p3.ANGLES:
                    plan=d.quantized_primary(width,angle,length)
                    self.assertEqual(len(plan),21)
                    base=p3.CENTERS[0]
                    rel=[(point["x"]-base[0],point["y"]-base[1])
                         for point in plan[0]["points"]]
                    for i in range(10):
                        center=p3.CENTERS[i]
                        self.assertEqual(
                            [(point["x"]-center[0],point["y"]-center[1])
                             for point in plan[i]["points"]],rel)
                    self.assertTrue(all(
                        p["x"]*256==int(p["x"]*256) and
                        p["y"]*256==int(p["y"]*256)
                        for s in plan for p in s["points"]))

    def test_03_plan_other_parameters_unchanged(self):
        old=p3.build_primary(10,45,34)
        new=d.quantized_primary(10,45,34)
        for a,b in zip(old,new):
            for name in ("width","strokeId","colorRgb","colorIndex"):
                self.assertEqual(a[name],b[name])
            for a_point,b_point in zip(a["points"],b["points"]):
                self.assertLessEqual(abs(a_point["x"]-b_point["x"]),1/512+1e-12)
                self.assertLessEqual(abs(a_point["y"]-b_point["y"]),1/512+1e-12)
        self.assertEqual(new[11]["points"],new[-1]["points"])

    def test_04_reverse_endpoints_remain_identical(self):
        for w in p3.WIDTHS:
            for l in p3.LENGTHS:
                for angle in range(0,180,15):
                    a=d.quantized_primary(w,angle,l)[0]["points"]
                    b=d.quantized_primary(w,angle+180,l)[0]["points"]
                    self.assertEqual(a,list(reversed(b)))

    def test_05_parent_p4d3_still_unquantized(self):
        o=p3.build_primary(2,45,4)
        q=d.quantized_primary(2,45,4)
        self.assertNotEqual(o[0]["points"],q[0]["points"])
        self.assertEqual(o[0]["strokeId"],q[0]["strokeId"])

    def test_06_binary_grid_not_approx_native_evidence(self):
        import pathlib
        c=pathlib.Path(d.__file__).read_text("utf8")
        self.assertIn("with p4b7.native_egret_session(workspace)",c)
        self.assertIn("parent.read_scene(driver,folder,key+\"_R1\",plan)",c)
        self.assertIn('"E4_live_game":"NOT_RUN"',c)
        self.assertIn('"exact_run_bound_CHALK":None',c)
        self.assertIn('"production_promotion":False',c)


if __name__=="__main__":
    unittest.main()

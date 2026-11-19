"""P4D12 E2: frozen strict cumulative fine10 substitution, not soft tolerance."""
import unittest
import numpy as np

import run_engine001_b1r_p4d12_native_strict_cumulative_fine10 as d
import run_engine001_b1r_p4d10_native_fine_phase_conflict10 as p4d10
import run_engine001_b1r_p4d7_native_width1_phase_feasibility as p4d7
import run_engine001_b1r_p4d8_native_cumulative_phase_pixel_state as p4d8


def sample(id_):
    return {"sample_id":id_,"x":46,"y":46,"owner":11}


def original_rows():
    rows=[]
    for i,name in enumerate(p4d10.CONFLICT_IDS):
        rows.append({"sample_id":name,"variant":"GRID_X0_Y0",
                     "width":1,"colorIndex":11,"colorRgb":0x223344,
                     "points":[{"x":202.99,"y":46},{"x":203.01,"y":46}],
                     "native_png_sha256":f"original{i}",
                     "measured":{"phase_feasible":True}})
    rows.append({"sample_id":"OTHER","variant":"GRID_X0_Y0",
                 "width":1,"colorIndex":7,"colorRgb":0x223344,
                 "points":[],"native_png_sha256":"untouched",
                 "measured":{"phase_feasible":True}})
    return rows


def fine_rows():
    return [{"sample_id":id_,"variant":d.FINE_VARIANT,
             "width":1,"colorIndex":11,"colorRgb":0x223344,
             "stroke_points":[{"x":202.99,"y":46.03125},{"x":203.01,"y":46.03125}],
             "native_png_sha256":f"fine{i}",
             "measured":{"phase_feasible":True,
                         "native_exact_sample_cell_correct_5of9":True,
                         "native_alpha24_genuine_foreign_backing":0}}
            for i,id_ in enumerate(p4d10.CONFLICT_IDS)]


class P4D12NativeStrictFine(unittest.TestCase):
    def test_01_frozen_arms_and_baseline(self):
        self.assertEqual(d.EXPERIMENT,"ENGINE001_B1R_P4D12_NATIVE_STRICT_CUMULATIVE_FINE10_V1")
        self.assertEqual(d.ARMS,("BASELINE_P4D8_STRICT","FINE10_DY_1_32_STRICT"))
        self.assertEqual(d.FINE_PHASE,("FINE_X0_Y1",0.,1/32))
        self.assertEqual(d.BASELINE["fixed_sample_correct"],16)
        self.assertEqual(d.BASELINE["source_owner_correct"],17)

    def test_02_only_ten_replace_order_not_modified(self):
        ordinary=original_rows()
        swapped=d.replacement_order(ordinary,fine_rows(),p4d10.CONFLICT_IDS)
        self.assertEqual([x["sample_id"] for x in swapped],
                         [x["sample_id"] for x in ordinary])
        self.assertEqual(sum(x["variant"]==d.FINE_VARIANT for x in swapped),10)
        self.assertEqual(swapped[-1],ordinary[-1])
        self.assertEqual(swapped[0]["native_png_sha256"],"fine0")
        # The substituted row normalizes native P4D10 stroke_points to
        # the P4D8 points schema used by the cumulative renderer.
        self.assertEqual(swapped[0]["points"],fine_rows()[0]["stroke_points"])
        self.assertNotIn("stroke_points",swapped[0])

    def test_03_any_unsafe_fine_phase_fail_closed(self):
        a=fine_rows()
        a[0]["measured"]["native_alpha24_genuine_foreign_backing"]=1
        with self.assertRaises(ValueError):
            d.replacement_order(original_rows(),a,p4d10.CONFLICT_IDS)
        with self.assertRaises(ValueError):
            d.replacement_order(original_rows(),fine_rows()[:-1],p4d10.CONFLICT_IDS)

    def test_04_wrong_original_source_or_extra_phase_fails(self):
        a=original_rows()
        a[0]["variant"]="FINE_X0_Y0"
        with self.assertRaises(ValueError):
            d.replacement_order(a,fine_rows(),p4d10.CONFLICT_IDS)
        a=original_rows();a.insert(1,dict(a[0]))
        with self.assertRaises(ValueError):
            d.replacement_order(a,fine_rows(),p4d10.CONFLICT_IDS)

    def test_05_strict_original_egret_parent_kept(self):
        self.assertIs(d.p4d8.trial_metrics,p4d8.trial_metrics)
        self.assertIs(d.p4d7.actual_native_single_metrics,
                      p4d7.actual_native_single_metrics)
        self.assertEqual(d.p4d5.ALPHA,24)
        self.assertEqual(d.CROP,(40,45,64,69))
        self.assertFalse(hasattr(d,"FOREIGN_SOFT_BUDGET"))

    def test_06_native_fine_exact_stroke_has_same_width_and_rgb(self):
        s=sample(p4d10.CONFLICT_IDS[0])
        palette=np.zeros((128,3),np.uint8)
        palette[11]=(34,51,68)
        stroke=p4d10.exact_phase_stroke(s,d.FINE_PHASE,palette)
        original=p4d7.phase_stroke(s,("GRID_X0_Y0",0.,0.),palette)
        self.assertEqual(stroke["width"],original["width"])
        self.assertEqual(stroke["colorRgb"],original["colorRgb"])
        self.assertEqual(stroke["points"][0]["y"]-original["points"][0]["y"],1/32)

    def test_07_wrong_sample_set_not_registered(self):
        with self.assertRaises(ValueError):
            d.replacement_order(original_rows(),fine_rows(),("X",)*10)

    def test_08_source_owner_strict_inherited_no_cost_estimator(self):
        self.assertEqual(d.SOURCE,p4d7.SOURCE)
        self.assertFalse(hasattr(d,"CHALK_ESTIMATOR"))


if __name__=="__main__":
    unittest.main()

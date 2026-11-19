"""E2 contracts P4D7 exact native phase matrix, sample provenance and safety."""
import unittest
from pathlib import Path

import numpy as np

import run_engine001_b1r_p4d7_native_width1_phase_feasibility as d


def fixture():
    a=np.full((240,150),6,np.uint8)
    # White is the ACTUAL engine palette index 6. A synthetic fixture
    # must not count owner 6 among its 20 nonwhite source-color owners.
    for slot in range(1,20):
        owner=slot if slot<6 else slot+1
        a[45:69,39+slot]=owner
    a[46:51,60:63]=21  # 5x3, with one true source clearance>1
    palette=np.zeros((128,3),np.uint8)
    palette[6]=(255,255,255)
    for owner in range(1,22):
        palette[owner]=(owner*9,owner*7,owner*5)
    return a,palette


class P4D7NativePhase(unittest.TestCase):
    def test_01_full_phase_matrix_8x8_plus_exact_historical_controls(self):
        self.assertEqual(d.EXPERIMENT,
            "ENGINE001_B1R_P4D7_NATIVE_WIDTH1_SUBPIXEL_PHASE_FEASIBILITY_V1")
        self.assertEqual(d.PHASES,(0,.125,.25,.375,.5,.625,.75,.875))
        self.assertEqual(len(d.VARIANTS),66)
        self.assertEqual(len(set(v[0] for v in d.VARIANTS)),66)
        self.assertEqual(d.EXPECTED_SAMPLES,21)
        self.assertEqual(d.EXPECTED_VARIANTS,66)
        self.assertEqual(21*66,1386)
        self.assertEqual(d.ALPHA,24)

    def test_02_source_sample_selection_20_owners_21_deterministic_positions(self):
        index,_=fixture()
        a=d.owner_samples(index)
        b=d.owner_samples(index)
        self.assertEqual(a,b)
        self.assertEqual(len(a),21)
        self.assertEqual(len(set(x["owner"] for x in a)),20)
        self.assertEqual(len(set(x["sample_id"] for x in a)),21)
        self.assertTrue(all(index[s["y"],s["x"]]==s["owner"] for s in a))
        self.assertTrue(all(40<=s["x"]<64 and 45<=s["y"]<69 for s in a))

    def test_03_all_variants_are_two_points_true_width1_owner_color(self):
        index,pal=fixture()
        s=d.owner_samples(index)[0]
        for v in d.VARIANTS:
            stroke=d.phase_stroke(s,v,pal)
            self.assertEqual(stroke["width"],1)
            self.assertEqual(stroke["colorIndex"],s["owner"])
            self.assertEqual(stroke["colorRgb"],d.p4d5._rgb(s["owner"],pal))
            self.assertEqual(len(stroke["points"]),2)
            self.assertNotEqual(stroke["points"][0],stroke["points"][1])
            self.assertTrue(all(0<=p["x"]<460 and 0<=p["y"]<240
                                for p in stroke["points"]))

    def test_04_historical_parent_geometries_reproduced(self):
        idx,pal=fixture()
        s=d.owner_samples(idx)[0]
        x,y=s["x"],s["y"]
        a=d.phase_stroke(s,("P4D5_ORIGINAL_INPUT",None,None),pal)
        b=d.phase_stroke(s,("P4D6_CENTERED_INPUT",None,None),pal)
        self.assertEqual(a["points"],[
            {"x":float(d.X0+x+.125),"y":float(y)},
            {"x":float(d.X0+x+.375),"y":float(y)}])
        self.assertEqual(b["points"],[
            {"x":float(d.X0+x+.49),"y":float(y+.5)},
            {"x":float(d.X0+x+.51),"y":float(y+.5)}])

    def test_05_native_owner_genuine_foreign_not_crop_false_positive(self):
        idx,pal=fixture()
        sample=d.owner_samples(idx)[0]
        protected=d.p4b4.source_critical_rois()
        native=np.zeros(d.NATIVE_SHAPE,np.uint8)
        y,x=sample["y"],sample["x"]
        native[y*3:(y+1)*3,(d.X0+x)*3:(d.X0+x+1)*3,:3]=pal[sample["owner"]]
        native[y*3:(y+1)*3,(d.X0+x)*3:(d.X0+x+1)*3,3]=255
        m=d.actual_native_single_metrics(native,idx,pal,protected,sample)
        self.assertTrue(m["phase_feasible"])
        self.assertEqual(m["native_alpha24_genuine_foreign_backing"],0)
        self.assertEqual(m["native_alpha24_protected_foreign_backing"],0)
        native[y*3:(y+1)*3,(d.X0+63)*3:(d.X0+64)*3,3]=255
        m=d.actual_native_single_metrics(native,idx,pal,protected,sample)
        self.assertFalse(m["phase_feasible"])
        self.assertGreater(m["native_alpha24_genuine_foreign_backing"],0)
        self.assertGreater(m["native_alpha24_protected_foreign_backing"],0)

    def test_06_synthetic_result_summary_distinguishes_safe_from_paint_only(self):
        index,_=fixture()
        sample=d.owner_samples(index)[0]
        rows=[]
        for i,v in enumerate(d.VARIANTS):
            m={"phase_feasible":i==1,
               "native_alpha1_genuine_foreign_backing":0 if i==1 else 2,
               "native_alpha24_genuine_foreign_backing":0 if i==1 else 1,
               "native_exact_sample_cell_correct_5of9":i<=1}
            rows.append({"sample_id":sample["sample_id"],"variant":v[0],
                         "measured":m})
        res=d.summarize([sample],rows)
        self.assertEqual(len(res),1)
        self.assertEqual(res[0]["feasible_variants"],1)
        self.assertEqual(res[0]["best_safe_variant"],d.VARIANTS[1][0])
        self.assertFalse(res[0]["P4D5_original_control_feasible"])
        self.assertFalse(res[0]["P4D6_centered_control_feasible"])

    def test_07_fail_closed_bad_source_format(self):
        with self.assertRaisesRegex(ValueError,"SOURCE_INDEX_FORMAT"):
            d.owner_samples(np.zeros((24,24),np.uint8))

    def test_08_no_fake_renderer_or_production_or_chalk(self):
        src=Path(d.__file__).read_text("utf8")
        self.assertIn("p4b7.native_egret_session(workspace)",src)
        self.assertIn("p4d5._native(driver,each,name,[stroke])",src)
        self.assertIn("actual_native_single_metrics(",src)
        self.assertIn("p4b4.source_critical_rois()",src)
        self.assertIn('"production_promotion":False',src)
        self.assertIn('"exact_run_bound_CHALK":None',src)
        self.assertNotIn("source_joint_outline(",src)
        self.assertNotIn("import run_engine001_adaptive_color_outline_v44",src)


if __name__=="__main__":
    unittest.main()

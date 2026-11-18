"""P4D0: frozen original renderer unbounded test-bypass and row-major E2 contracts."""
import unittest
from pathlib import Path
import numpy as np

import run_engine001_b1r_p4d0_unbounded_adaptive_vs_scanline_native as d
import run_engine001_b1r_p4b1_hybrid_zone_coverage as b1


class P4D0Contracts(unittest.TestCase):
    def test_01_id_and_no_historical_inputs(self):
        self.assertEqual(d.EXPERIMENT,
            "ENGINE001_B1R_P4D0_UNBOUNDED_ADAPTIVE_VS_SCANLINE_EGRET_V1")
        self.assertEqual(d.SOURCE,"C_192_D_COMPONENT24")
        self.assertEqual(d.METHODS,("E_SOBEL90","F_SOBEL90_LAB12"))
        self.assertEqual(d.ARMS,("ADAPTIVE_UNBOUNDED","FIRST_SCANLINE"))
        s=Path(d.__file__).read_text("utf8")
        self.assertNotIn("import run_engine001_color32_p4c1",s)
        self.assertNotIn("import run_engine001_adaptive_color_outline_v44",s)
        self.assertIn("source_joint_outline(source_index,original,game)",s)

    def test_02_row_major_exact_color_runs_and_fixed_width(self):
        img=np.full((240,150),6,np.uint8)
        img[0,:3]=7
        img[0,3:5]=8
        img[0,6]=7
        img[1,0:2]=8
        game=np.zeros((128,3),np.uint8)
        game[7]=[1,2,3]
        game[8]=[4,5,6]
        s=d.first_scanline(img,game)
        self.assertEqual([v["colorIndex"] for v in s],[7,8,7,8])
        self.assertEqual([v["width"] for v in s],[2]*4)
        self.assertEqual([v["strokeId"] for v in s],
                         ["icon-0","icon-1","icon-2","icon-3"])
        self.assertEqual([(v["points"][0]["y"],v["points"][0]["x"])
                          for v in s],
                         [(0.,155.125),(0.,158.125),(0.,161.125),(1.,155.125)])
        self.assertEqual(s[2]["points"][-1]["x"],161.375)

    def test_03_white_no_paint(self):
        img=np.full((240,150),6,np.uint8)
        game=np.zeros((128,3),np.uint8)
        self.assertEqual(d.first_scanline(img,game),[])

    def test_04_input_fail_closed(self):
        game=np.zeros((128,3),np.uint8)
        with self.assertRaisesRegex(ValueError,"SCANLINE_SHAPE"):
            d.first_scanline(np.zeros((150,240),np.uint8),game)
        with self.assertRaisesRegex(ValueError,"SCANLINE_SHAPE"):
            d.first_scanline(np.zeros((240,150),np.int16),game)

    def test_05_parent_limits_restored_on_normal_and_exception(self):
        old=(b1.MAX_STROKES,b1.MAX_VERTICES)
        with d.unlimited_owner_planner():
            self.assertEqual(b1.MAX_STROKES,float("inf"))
            self.assertEqual(b1.MAX_VERTICES,float("inf"))
        self.assertEqual((b1.MAX_STROKES,b1.MAX_VERTICES),old)
        with self.assertRaisesRegex(ValueError,"sample"):
            with d.unlimited_owner_planner():
                raise ValueError("sample")
        self.assertEqual((b1.MAX_STROKES,b1.MAX_VERTICES),old)

    def test_06_renderer_test_patch_narrow_and_valid(self):
        src=Path(__file__).with_name("game_renderer_reference.js").read_text("utf8")
        patched=d.patch_renderer_in_memory(src)
        self.assertNotEqual(patched,src)
        self.assertIn("Math.max(6000, strokes.reduce",patched)
        self.assertIn("P4D0 test only: no aggregate",patched)
        a=src.index("function renderComplexHoldoutColorProbe(")
        z=src.index("\n  // ENGINE-001 V35",a)
        self.assertIn("strokes.length > 3000",src[a:z])
        self.assertNotIn("strokes.length > 3000",
                         patched[patched.index("function renderComplexHoldoutColorProbe("):
                                 patched.index("\n  // ENGINE-001 V35")])
        self.assertEqual(src,Path(__file__).with_name(
                          "game_renderer_reference.js").read_text("utf8"))
        self.assertEqual(d.patch_renderer_in_memory(src),patched)

    def test_07_renderer_wrong_source_fails_closed(self):
        with self.assertRaises((ValueError,Exception)):
            d.patch_renderer_in_memory("function makeTemporalBoard(){ }")

    def test_08_nonwhite_native_composite_metrics_no_fake_owner_pass(self):
        idx=np.full((240,150),6,np.uint8)
        idx[10:12,20:22]=7
        game=np.full((128,3),255,np.uint8)
        game[7]=[20,30,40]
        pix=np.zeros((720,1380,4),np.uint8)
        score=d._native_stats(pix,idx,game)
        self.assertEqual(score["native_nonwhite_any_ink_coverage_alpha24"],0.)
        self.assertEqual(score["per_owner_same_color_quality_gates"],
                         "NOT_MEASURED_COMPOSITE_ONLY")

    def test_09_true_native_shape_fail_closed(self):
        game=np.zeros((128,3),np.uint8)
        index=np.full((240,150),6,np.uint8)
        with self.assertRaisesRegex(ValueError,"NATIVE_RGBA"):
            d._native_stats(np.zeros((240,150,4),np.uint8),index,game)

    def test_10_score_is_not_exact_chalk_or_live(self):
        text=Path(d.__file__).read_text("utf8")
        self.assertIn('"exact_run_bound_CHALK":None',text)
        self.assertIn('"E4_game_runtime":"NOT_RUN"',text)
        self.assertIn('renderP4A2BrushWidths1to10Probe(arguments[0]);',text)
        self.assertIn('"production_promotion":False',text)


if __name__=="__main__":
    unittest.main()

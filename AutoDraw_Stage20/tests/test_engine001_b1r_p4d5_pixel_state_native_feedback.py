"""P4D5 E2: candidate/state semantics, fail-closed provenance and no fake native."""
import unittest
from pathlib import Path

import numpy as np

import run_engine001_b1r_p4d5_pixel_state_native_feedback as d


def palette():
    p=np.zeros((128,3),np.uint8)
    p[6]=(255,255,255)
    p[11]=(110,40,30)
    p[22]=(20,140,185)
    p[33]=(20,20,20)
    return p


def indexed():
    a=np.full((240,150),6,np.uint8)
    a[48:58,43:54]=11
    a[52:64,55:62]=22
    a[58,49]=33
    return a


def transparent():
    return np.zeros(d.BOARD_SHAPE,np.uint8)


def ink_pixel(native,x,y,color):
    native[y*d.SCALE:(y+1)*d.SCALE,
           (d.X0+x)*d.SCALE:(d.X0+x+1)*d.SCALE,:3]=color
    native[y*d.SCALE:(y+1)*d.SCALE,
           (d.X0+x)*d.SCALE:(d.X0+x+1)*d.SCALE,3]=255


class P4D5NativePixelStateContracts(unittest.TestCase):
    def test_01_active_source_and_frozen_thresholds(self):
        self.assertEqual(d.EXPERIMENT,
                         "ENGINE001_B1R_P4D5_PIXEL_STATE_NATIVE_FEEDBACK_V1")
        self.assertEqual(d.SOURCE,"C_192_D_COMPONENT24")
        self.assertEqual(d.METHODS,("E_SOBEL90","F_SOBEL90_LAB12"))
        self.assertEqual(d.CROP,(40,45,64,69))
        self.assertEqual(d.ALPHA,24)
        self.assertEqual(d.RGB_TOL,32)
        self.assertEqual(d.LOGICAL_REQUIRED_SUBPIXELS,5)
        self.assertEqual(d.WHITE,6)
        self.assertEqual(d.MAX_NATIVE_PROBES,240)

    def test_02_source_zero_map_and_white_not_painted(self):
        idx=indexed()
        target=d.crop_target(idx)
        self.assertEqual(target.shape,(240,150))
        self.assertEqual(int(target.sum()),110+84+1)
        self.assertTrue(target[58,49])
        self.assertFalse(target[45,40])
        self.assertFalse(target[69,40])

    def test_03_0_to_1_only_from_actual_native_rgba(self):
        idx=indexed()
        game=palette()
        native=transparent()
        self.assertFalse(d.actual_state(native,idx,game).any())
        ink_pixel(native,44,49,game[11])
        state=d.actual_state(native,idx,game)
        self.assertTrue(state[49,44])
        self.assertEqual(int(state.sum()),1)

    def test_04_wrong_color_or_alpha_cannot_flip_zero(self):
        idx=indexed()
        game=palette()
        native=transparent()
        ink_pixel(native,44,49,game[22])
        self.assertFalse(d.actual_state(native,idx,game)[49,44])
        ink_pixel(native,44,49,game[11])
        native[49*d.SCALE:(49+1)*d.SCALE,
               (d.X0+44)*d.SCALE:(d.X0+45)*d.SCALE,3]=10
        self.assertFalse(d.actual_state(native,idx,game)[49,44])

    def test_05_repaint_wrong_color_reverts_one_to_zero(self):
        idx=indexed()
        game=palette()
        native=transparent()
        ink_pixel(native,44,49,game[11])
        before=d.actual_state(native,idx,game)
        native_after=native.copy()
        ink_pixel(native_after,44,49,game[22])
        after=d.actual_state(native_after,idx,game)
        self.assertTrue(before[49,44])
        self.assertFalse(after[49,44])

    def test_06_five_of_nine_real_backing_threshold(self):
        idx=indexed()
        game=palette()
        native=transparent()
        y,x=49,44
        for k in range(4):
            native[y*3+k//3,(d.X0+x)*3+k%3,:3]=game[11]
            native[y*3+k//3,(d.X0+x)*3+k%3,3]=255
        self.assertFalse(d.actual_state(native,idx,game)[y,x])
        native[y*3+1,(d.X0+x)*3+1,:3]=game[11]
        native[y*3+1,(d.X0+x)*3+1,3]=255
        self.assertTrue(d.actual_state(native,idx,game)[y,x])

    def test_07_foreign_protection_even_if_pixel_already_covered(self):
        idx=indexed()
        p=palette()
        allowed=d.backing_allowed(idx,11)
        self.assertTrue(allowed[49*3,(d.X0+44)*3])
        self.assertFalse(allowed[56*3,(d.X0+56)*3])
        self.assertFalse(allowed[45*3,(d.X0+42)*3])
        self.assertFalse(allowed[40*3,(d.X0+44)*3])

    def test_08_native_single_stroke_rejects_white_or_other_owner(self):
        idx=indexed()
        p=palette()
        c={"stroke":d.make_stroke(11,p,1,44.125,49,44.375,49)}
        native=transparent()
        ink_pixel(native,44,49,p[11])
        safe=d.single_native_candidate(c,native,idx,p)
        self.assertEqual(safe["native_foreign_alpha24_backing_px"],0)
        self.assertEqual(safe["native_isolated_owner_correct_logical_px"],1)
        ink_pixel(native,56,56,p[11])
        not_safe=d.single_native_candidate(c,native,idx,p)
        self.assertGreater(not_safe["native_foreign_alpha24_backing_px"],0)

    def test_09_owner_rgb_from_real_palette_never_global_outline(self):
        p=palette()
        s=d.make_stroke(22,p,7,56.125,55.125,60.125,59.125)
        self.assertEqual(s["colorIndex"],22)
        self.assertEqual(s["colorRgb"],d._rgb(22,p))
        self.assertEqual(s["points"][0],{"x":d.X0+56.125,"y":55.125})
        self.assertEqual(s["width"],7)
        with self.assertRaisesRegex(ValueError,"STROKE_ARGS"):
            d.make_stroke(6,p,1,44,49,45,49)

    def test_10_greedy_maximizes_NEW_actual_zero_cells(self):
        state=np.zeros((240,150),bool)
        state[49,44]=True
        big=np.zeros_like(state)
        big[49,44]=True
        big[50,44]=True
        tiny=np.zeros_like(state)
        tiny[52,48]=True
        tiny[53,48]=True
        pool=[
            {"used":False,"unsafe":False,"stamp":big,
             "stroke":{"width":10},"length":6.0},
            {"used":False,"unsafe":False,"stamp":tiny,
             "stroke":{"width":3},"length":3.0}]
        self.assertEqual(d.next_choice(pool,state),(1,2))
        pool[1]["used"]=True
        self.assertEqual(d.next_choice(pool,state),(0,1))
        pool[0]["unsafe"]=True
        self.assertIsNone(d.next_choice(pool,state))

    def test_11_source_proposals_support_multiple_directions_and_widths(self):
        idx=indexed()
        p=palette()
        candidates=d.candidate_pool(idx,p)
        self.assertTrue(candidates)
        self.assertLessEqual(len(candidates),d.MAX_NATIVE_PROBES)
        self.assertEqual(len({x["candidate_id"] for x in candidates}),len(candidates))
        self.assertTrue(any(x["stroke"]["width"]==1 for x in candidates))
        self.assertTrue(any(x["stroke"]["width"]>1 for x in candidates))
        self.assertTrue(all(x["stroke"]["colorIndex"] in (11,22,33)
                            for x in candidates))
        self.assertTrue(all(x["stroke"]["colorRgb"]==d._rgb(x["stroke"]["colorIndex"],p)
                            for x in candidates))
        self.assertTrue(all(1<=x["stroke"]["width"]<=10 for x in candidates))

    def test_12_fallback_small_width_and_true_source_color_runs(self):
        a=indexed()
        p=palette()
        control=d.scanline_control(a,p)
        self.assertGreater(len(control),0)
        self.assertTrue(all(s["width"]==1 for s in control))
        self.assertEqual([s["strokeId"] for s in control],
                         [f"icon-{i}" for i in range(len(control))])
        self.assertTrue(all(s["colorRgb"]==d._rgb(s["colorIndex"],p)
                            for s in control))

    def test_13_real_metrics_bounded_to_crop_no_false_full_image_gate(self):
        a=indexed()
        p=palette()
        native=transparent()
        score=d.roi_metrics(native,a,p)
        self.assertEqual(score["remaining_zero_logical"],195)
        self.assertEqual(score["correct_logical_native_5_of_9"],0)
        self.assertEqual(score["any_ink_outside_crop_alpha24_backing"],0)
        ink_pixel(native,44,49,p[11])
        score=d.roi_metrics(native,a,p)
        self.assertEqual(score["remaining_zero_logical"],194)
        self.assertEqual(score["correct_logical_native_5_of_9"],1)

    def test_14_provenance_native_renderer_no_integration_changes(self):
        source=Path(d.__file__).read_text("utf8")
        self.assertIn("p3d.run(source,engine_js,fresh)",source)
        self.assertIn("p4b7.native_egret_session(workspace)",source)
        self.assertIn("read_webgl_result(render,folder,stem)",source)
        self.assertIn("single_native_candidate(candidate,native,index,palette)",source)
        self.assertIn("after=actual_state(native,index,palette)",source)
        self.assertIn('production_promotion":False',source)
        self.assertIn('"exact_run_bound_CHALK":None',source)
        self.assertNotIn("source_joint_outline(",source)
        self.assertNotIn("import run_engine001_adaptive_color_outline_v44",source)
        self.assertNotIn("import run_engine001_color32_p4c1",source)


if __name__=="__main__":
    unittest.main()

"""P4D3: deterministic experiment design E2 only; native evidence requires CI."""
import unittest

import numpy as np

import run_engine001_b1r_p4d3_native_brush_repeatability as d


class BrushMatrixContracts(unittest.TestCase):
    def test_01_matrix_all_10_widths_24_directions_2_lengths(self):
        self.assertEqual(d.EXPERIMENT,
            "ENGINE001_B1R_P4D3_NATIVE_BRUSH_WIDTH_DIRECTION_REPEATABILITY_V1")
        self.assertEqual(d.WIDTHS,tuple(range(1,11)))
        self.assertEqual(d.ANGLES,tuple(range(0,360,15)))
        self.assertEqual(d.LENGTHS,(4,34))
        self.assertEqual(len(d.WIDTHS)*len(d.ANGLES)*len(d.LENGTHS),480)
        self.assertEqual(len(d.WIDTHS)*len(d.EDGE_ANGLES),80)

    def test_02_pins_real_renderer_and_no_source_reuse(self):
        self.assertEqual(d.RENDERER_GIT_BLOB,
                         "76d950e0a8911888a9df3b675b866519ecf7bba4")
        self.assertEqual(d.ENGINE_GIT_BLOB,
                         "46cc74de00b6cb5d207b1e1a2ffcd81613b6d388")
        self.assertEqual(d.NATIVE_SHAPE,(720,1380,4))
        self.assertEqual(d.SCALE,3)
        self.assertIn("renderP4A2BrushWidths1to10Probe",d.CMD)

    def test_03_experiment_has_10_identical_separate_strokes_and_10_overlay(self):
        p=d.build_primary(7,45,34)
        self.assertEqual(len(p),21)
        self.assertEqual([x["strokeId"] for x in p],
                         [f"icon-{i}" for i in range(21)])
        self.assertTrue(all(x["width"]==7 and x["colorRgb"]==d.COLOR for x in p))
        self.assertEqual(p[11]["points"],p[12]["points"])
        self.assertEqual(p[11]["points"],p[-1]["points"])
        displacement=(p[1]["points"][0]["x"]-p[0]["points"][0]["x"],
                      p[1]["points"][0]["y"]-p[0]["points"][0]["y"])
        self.assertEqual(displacement,(114.0,0.0))
        for i in range(10):
            a,b=p[i]["points"]
            self.assertAlmostEqual(b["x"]-a["x"],
                                   p[0]["points"][1]["x"]-p[0]["points"][0]["x"])
            self.assertAlmostEqual(b["y"]-a["y"],
                                   p[0]["points"][1]["y"]-p[0]["points"][0]["y"])

    def test_04_reversal_exact_inverse_control_points(self):
        for angle in range(0,180,15):
            a=d.two_points(100.25,100.375,34,angle)
            b=d.two_points(100.25,100.375,34,angle+180)
            self.assertEqual(a,list(reversed(b)))

    def test_05_full_board_all_widths_angles_inside_renderer_and_no_trim(self):
        for width in d.WIDTHS:
            for angle in d.ANGLES:
                for length in d.LENGTHS:
                    p=d.build_primary(width,angle,length)
                    self.assertEqual(len(p),21)
                    self.assertEqual(sum(len(s["points"]) for s in p),42)
                    self.assertTrue(all(0<=v["x"]<460 and 0<=v["y"]<240
                                        for s in p for v in s["points"]))

    def test_06_stress_edge_center_fraction_and_colors(self):
        for width in d.WIDTHS:
            for angle in d.EDGE_ANGLES:
                p=d.build_edge(width,angle)
                self.assertEqual(len(p),11)
                self.assertEqual(len(set(s["colorRgb"] for s in p)),2)
                self.assertTrue(all(s["colorRgb"]==d.COLOR for s in p[:10]))
                self.assertEqual(p[-1]["colorRgb"],d.SECONDARY_COLOR)
                self.assertTrue(all(0<=v["x"]<460 and 0<=v["y"]<240
                                    for s in p for v in s["points"]))

    def test_07_copy_roi_native_backing_and_pixel_exact_delta(self):
        img=np.zeros(d.NATIVE_SHAPE,np.uint8)
        img[120,174,:]=[12,18,24,255]
        img[120,516,:]=[12,18,24,255]
        a=d.roi(img,*d.CENTERS[0])
        b=d.roi(img,*d.CENTERS[1])
        self.assertEqual(a.shape,(162,162,4))
        self.assertEqual(d.difference(a,b)["rgba_differing_pixels"],0)
        b=b.copy()
        b[2,3,3]=128
        self.assertEqual(d.difference(a,b)["rgba_differing_pixels"],1)

    def test_08_alpha24_and_alpha1_independently_tracked(self):
        a=np.zeros((3,3,4),np.uint8)
        b=a.copy()
        b[1,1,3]=12
        c=d.difference(a,b)
        self.assertEqual(c["alpha1_xor_pixels"],1)
        self.assertEqual(c["alpha24_xor_pixels"],0)
        b[1,1,3]=50
        c=d.difference(a,b)
        self.assertEqual(c["alpha1_xor_pixels"],1)
        self.assertEqual(c["alpha24_xor_pixels"],1)

    def test_09_unsupported_width_or_angle_fails_closed(self):
        for value in (0,11):
            with self.assertRaisesRegex(ValueError,"PLAN_ARGS"):
                d.build_primary(value,0,34)
        with self.assertRaisesRegex(ValueError,"PLAN_ARGS"):
            d.build_primary(1,7,34)
        with self.assertRaisesRegex(ValueError,"PLAN_ARGS"):
            d.build_primary(1,45,6)

    def test_10_invalid_native_shape_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"NATIVE_RGBA"):
            d.roi(np.zeros((240,460,4),np.uint8),58,40)

    def test_11_stress_invalid_angle_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"EDGE_ARGS"):
            d.build_edge(3,15)

    def test_12_native_not_fake_chalk_or_production(self):
        import pathlib
        code=pathlib.Path(d.__file__).read_text("utf8")
        self.assertIn('with p4b7.native_egret_session(workspace)',code)
        self.assertIn('"E4_live_game":"NOT_RUN"',code)
        self.assertIn('"exact_run_bound_CHALK":None',code)
        self.assertIn('"production_promotion":False',code)
        self.assertNotIn("p4d0.patched_test_renderer",code)
        self.assertNotIn("import run_engine001_adaptive_color_outline_v44",code)


if __name__=="__main__":
    unittest.main()

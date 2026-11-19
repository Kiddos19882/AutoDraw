"""P4D16 E2 mathematical and provenance contracts. No simulated-brush quality PASS."""
import unittest
import numpy as np
import run_engine001_b1r_p4d16_canvas_aa_density as p

class TestCanvasAAAndDensity(unittest.TestCase):
    def test_01_pinned_design(self):
        self.assertEqual(len(p.WIDTHS)*len(p.ANGLES)*len(p.LENGTHS)*len(p.PHASES),150)
        self.assertEqual(p.EXPECTED_PHASE_NATIVE_SCENES,156)
        self.assertEqual((p.WHITE,p.X0,p.SCALE,p.ALPHA,p.RGB_TOL),(6,155,3,24,32))
    def test_02_phase_copy_contract(self):
        a=p.phase_plan(1,15,4,0.)
        b=p.phase_plan(1,15,4,.125)
        self.assertEqual(len(a),21)
        self.assertEqual(len(b),21)
        self.assertAlmostEqual(b[0]["points"][0]["x"]-a[0]["points"][0]["x"],.125)
        self.assertAlmostEqual(b[0]["points"][0]["y"]-a[0]["points"][0]["y"],.125)
        with self.assertRaises(ValueError):
            p.phase_plan(11,15,4,0.)
        with self.assertRaises(ValueError):
            p.phase_plan(1,15,4,.333)
    def test_03_native_exact_composite(self):
        native=np.zeros((720,1380,4),np.uint8)
        native[:,465:915,:3]=[21,32,43]
        native[:,465:915,3]=255
        idx=np.ones((240,150),np.uint8)
        source=np.full((240,150,3),[21,32,43],dtype=np.uint8)
        counts,ink=p.color_subpixels(native,idx,source)
        self.assertEqual(ink.shape,(720,450,4))
        self.assertEqual(counts.shape,(240,150))
        self.assertTrue(np.all(counts==9))
        self.assertEqual(int((counts>=5).sum()),36000)
        self.assertEqual(int((counts>=7).sum()),36000)
        self.assertEqual(int((counts>=9).sum()),36000)
    def test_04_alpha_over_white_not_raw(self):
        native=np.zeros((720,1380,4),np.uint8)
        native[:,465:915,:3]=[0,0,0]
        native[:,465:915,3]=128
        source=np.full((240,150,3),[127,127,127],dtype=np.uint8)
        counts,_=p.color_subpixels(native,np.ones((240,150),np.uint8),source)
        self.assertTrue(np.all(counts==9))
    def test_05_alpha_zero_component(self):
        interior=np.zeros((240,150),bool)
        interior[2,3]=True
        ink=np.full((720,450,4),255,np.uint8)
        ink[6:9,9:12,3]=0
        d=p.physical_holes(ink,interior)
        self.assertEqual(d["native_alpha_eq0_physical"],9)
        self.assertEqual(d["native_alpha_below24_physical"],9)
        self.assertEqual(d["transparent_connected_components_area_ge3"],1)
        self.assertEqual(d["largest_transparent_component_physical"],9)
    def test_06_halfpixel_only_width1_3(self):
        pts=[{"x":58.,"y":40.},{"x":62.,"y":40.}]
        for w in (1,3):
            a=p.predict_alpha(pts,w,93,39,"naive")
            b=p.predict_alpha(pts,w,93,39,"source_halfpixel")
            self.assertTrue(np.any(a!=b),w)
        for w in (2,5,10):
            a=p.predict_alpha(pts,w,93,39,"naive")
            b=p.predict_alpha(pts,w,93,39,"source_halfpixel")
            self.assertTrue(np.array_equal(a,b),w)
    def test_07_area8_fractional(self):
        pts=[{"x":58.,"y":40.},{"x":62.,"y":40.}]
        a=p.predict_alpha(pts,1,93,39,"area8")
        self.assertEqual(a.shape,(162,162))
        self.assertEqual(a.dtype,np.uint8)
        self.assertTrue(np.any((a>0)&(a<255)))
        self.assertTrue(np.any(a==255))
    def test_08_mask_errors(self):
        a=np.zeros((162,162),np.uint8);b=np.zeros_like(a)
        a[0,0]=255;a[1,1]=255
        b[0,0]=255;b[2,2]=255
        q=p.mask_accuracy(a,b)
        self.assertAlmostEqual(q["alpha24"]["IoU"],1/3)
        self.assertEqual(q["alpha24"]["false_positive"],1)
        self.assertEqual(q["alpha24"]["false_negative"],1)
        self.assertFalse(q["alpha24"]["exact_mask"])
        self.assertTrue(p.mask_accuracy(np.zeros_like(a),np.zeros_like(a))["alpha24"]["exact_mask"])
    def test_09_bad_shapes_fail_closed(self):
        pts=[{"x":58.,"y":40.},{"x":62.,"y":40.}]
        with self.assertRaises(ValueError):
            p.predict_alpha(pts,0,0,0,"area8")
        with self.assertRaises(ValueError):
            p.predict_alpha(pts,1,0,0,"other")
        with self.assertRaises(ValueError):
            p.mask_accuracy(np.zeros((3,3),np.uint8),np.zeros((3,3),np.uint8))
        with self.assertRaises(ValueError):
            p.predict_alpha([{"x":float("nan"),"y":2.},pts[1]],1,0,0,"naive")
    def test_10_summary(self):
        m=p.mask_accuracy(np.zeros((162,162),np.uint8),np.zeros((162,162),np.uint8))
        row={"native_translated_all10_identical":True,
             "models":{x:m for x in ("naive","source_halfpixel","area8")}}
        s=p.sample_summary([row])
        self.assertEqual(s["n"],1)
        self.assertEqual(s["area8"]["exact_alpha24_masks"],1)

if __name__=="__main__":
    unittest.main()

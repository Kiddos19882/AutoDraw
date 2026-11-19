"""P4D15 E2-only ROI source math and stage classification tests."""
import unittest
import numpy as np
import run_engine001_b1r_p4d15_native_canvas_webgl_stage as d

class SourceTextureTranslationContracts(unittest.TestCase):
    def test_01_fixed_axes(self):
        self.assertEqual(d.CASE_COUNT,30)
        self.assertEqual(d.TOTAL_NATIVE,34)
        self.assertEqual(d.TOTAL_SOURCE,33)
        self.assertEqual(d.WIDTHS,(1,2,3,4,10))
        self.assertEqual(d.SIDE,162)
    def test_02_3x_canvas_crop_with_fractional_origin(self):
        native=np.zeros((720,1380,4),np.uint8)
        node={"x":.25,"y":.125}
        a=d.crop_source(native,node,58,40)
        b=d.crop_source(native,node,172,40)
        self.assertEqual(a.shape,(162,162,4))
        self.assertEqual(b.shape,a.shape)
    def test_03_exact_matched_rgba(self):
        vals=[np.zeros((162,162,4),np.uint8) for _ in range(10)]
        r=d.compare_copies(vals)
        self.assertTrue(r["isolated10_exact_rgba"])
        self.assertEqual(r["translated_rgba_different_pixels_total"],0)
    def test_04_alpha_and_rgb_diagnostic_separate(self):
        vals=[np.zeros((162,162,4),np.uint8) for _ in range(10)]
        vals[1][1,1,0]=5
        vals[2][2,2,3]=25
        r=d.compare_copies(vals)
        self.assertFalse(r["isolated10_exact_rgba"])
        self.assertEqual(r["translated_rgba_different_pixels_total"],2)
        self.assertEqual(r["translated_alpha24_xor_pixels_total"],1)
        self.assertEqual(r["translated_alpha1_xor_pixels_total"],1)
    def test_05_all_four_classifications(self):
        t={"isolated10_exact_rgba":True}
        f={"isolated10_exact_rgba":False}
        self.assertEqual(d.classify(t,t),"both_exact")
        self.assertEqual(d.classify(f,t),"canvas_changed_webgl_exact")
        self.assertEqual(d.classify(t,f),"canvas_exact_webgl_changed")
        self.assertEqual(d.classify(f,f),"both_changed")
    def test_06_fail_closed_wrong_shape(self):
        z=np.zeros((162,162,4),np.uint8)
        with self.assertRaises(ValueError):
            d.compare_copies([z]*9)
        with self.assertRaises(ValueError):
            d.compare_copies([z]*9+[np.zeros((1,1,4),np.uint8)])
        with self.assertRaises(ValueError):
            d.crop_source(np.zeros((1,1,4),np.uint8),
                          {"x":0,"y":0},58,40)

    def test_07_transparent_padding_outside_real_node_bounds(self):
        source=np.full((100,100,4),255,np.uint8)
        cropped=d.crop_source(source,{"x":0,"y":0},58,40)
        self.assertEqual(cropped.shape,(162,162,4))
        self.assertEqual(int(cropped[0,0,3]),255)
        self.assertEqual(int(cropped[-1,-1,3]),0)

    def test_08_all_coords_from_frozen_original_grid(self):

        import run_engine001_b1r_p4d3_native_brush_repeatability as old
        self.assertEqual(d.CASE_COUNT,len(d.WIDTHS)*len(d.ANGLES)*len(d.LENGTHS))
        self.assertEqual(len(old.CENTERS),12)
        self.assertEqual(tuple(d.REPEATS),(1,3,10))

if __name__=="__main__":
    unittest.main()

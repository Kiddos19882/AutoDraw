"""P4D14 source-driven center formula: E2 math only, not native evidence."""
import unittest
import numpy as np
import run_engine001_b1r_p4d14_egret_halfpixel_centroid as m

class P4D14MathContracts(unittest.TestCase):
    def test_01_halfpixel_source_widths(self):
        self.assertEqual([w for w in m.WIDTHS if m.egret_graphics_halfpixel(w)],[1,3])
        self.assertEqual(m.egret_graphics_halfpixel(1)*m.p4d3.SCALE,1.5)
    def test_02_fixed_matrix(self):
        self.assertEqual(m.ANGLES,(0,15,30,45,60,90,135,165))
        self.assertEqual(m.LENGTHS,(4,34))
        self.assertEqual((m.EXPECTED_CASES,m.EXPECTED_NATIVE_SCENES),(160,171))
    def test_03_model_centers(self):
        for w in m.WIDTHS:
            p=m.p4d3.build_primary(w,45,4)[0]
            n=m.model_center(p,False);real=m.model_center(p,True)
            h=.5 if w in (1,3) else 0.
            self.assertAlmostEqual(n[0],58.25);self.assertAlmostEqual(n[1],40.375)
            self.assertAlmostEqual(real[0],58.25+h)
            self.assertAlmostEqual(real[1],40.375+h)
    def test_04_native_3x_centroid(self):
        side=2*m.p4d3.HALF*m.p4d3.SCALE
        a=np.zeros((side,side,4),np.uint8)
        a[81,81,3]=255
        a[81,84,3]=85
        x,y=m.native_alpha_centroid(a,58,40)
        self.assertAlmostEqual(x,58-27+(81.5*.75+84.5*.25)/3)
        self.assertAlmostEqual(y,40-27+81.5/3)
    def test_05_no_alpha_fails_closed(self):
        side=2*m.p4d3.HALF*m.p4d3.SCALE
        with self.assertRaises(ValueError):
            m.native_alpha_centroid(np.zeros((side,side,4),np.uint8),58,40)
        with self.assertRaises(ValueError):
            m.native_alpha_centroid(np.zeros((side,side,3),np.uint8),58,40)
    def test_06_no_invalid_width(self):
        for w in (0,11,1.,True):
            with self.assertRaises(ValueError):m.egret_graphics_halfpixel(w)
    def test_07_nonfinite_source_fails(self):
        with self.assertRaises(ValueError):
            m.model_center({"width":1,"points":[{"x":float("nan"),"y":1},{"x":2,"y":1}]},True)
        with self.assertRaises(ValueError):
            m.euclidean((float("inf"),0),(0,0))
    def test_08_statistics_robust(self):
        self.assertEqual(m.summarize([0,0])["mean"],0)
        with self.assertRaises(ValueError):m.summarize([])
        with self.assertRaises(ValueError):m.summarize([float("nan")])
    def test_09_nominal_vs_shifted_width2_identical(self):
        p=m.p4d3.build_primary(2,0,34)[0]
        self.assertEqual(m.model_center(p,False),m.model_center(p,True))
    def test_10_no_hidden_fullfootprint_claim(self):
        self.assertIn("centroid",m.__doc__)
        self.assertEqual(m.PARENT_BLOB,"3437a9326b381d9c94d6ade80059d40adf233d09")

if __name__=="__main__":unittest.main()

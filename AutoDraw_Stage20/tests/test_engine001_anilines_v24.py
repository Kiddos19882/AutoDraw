"""Synthetic tests for V24 lossless native pixel audit, no renderer approximation."""
import unittest
import numpy as np
from run_engine001_anilines_v24 import classify_alpha

class Tests(unittest.TestCase):
    def setUp(self):
        self.palette=np.full((240,150),4,np.uint8)
        self.roi=np.full((240,150,3),100,np.uint8)
        self.fixture={"points":[{"x":200.0,"y":100.0},{"x":200.0,"y":100.0}]}
    def case(self,pixels):
        cov={}
        for t in (1,64,128,254):
            cov[str(t)]={"alphaPixels":sum(a>=t for _,_,a in pixels),
                         "foreignClassPixels":0,"outsideRoiPixels":0}
        return {"id":"v","kind":"vertex","coverage":cov,
                "alphaCoordinates":pixels,"nativeDrawCalls":0}
    def test_uniform(self):
        x=self.case([[600,300,255]])
        self.assertEqual(classify_alpha(x,self.fixture,self.palette,self.roi)["counts"]["128"]["alphaPixels"],1)
    def test_palette_mismatch_fails_closed(self):
        x=self.case([[603,300,255]])
        self.palette[100,46]=6
        with self.assertRaises(ValueError):
            classify_alpha(x,self.fixture,self.palette,self.roi)
    def test_non_background_rgb_distance(self):
        x=self.case([[603,300,255]])
        self.roi[100,46]=[200,100,100]
        outcome=classify_alpha(x,self.fixture,self.palette,self.roi)
        self.assertEqual(outcome["counts"]["128"]["same_class_far_rgb_ge_64"],1)
    def test_empty_and_bad_alpha(self):
        x=self.case([])
        with self.assertRaises(ValueError):
            classify_alpha(x,self.fixture,self.palette,self.roi)
        x=self.case([[600,300,257]])
        with self.assertRaises(ValueError):
            classify_alpha(x,self.fixture,self.palette,self.roi)
    def test_foreign_palette_near_rgb(self):
        x=self.case([[603,300,255]])
        self.palette[100,45]=6
        for t in x["coverage"].values():t["foreignClassPixels"]=1
        outcome=classify_alpha(x,self.fixture,self.palette,self.roi)
        self.assertEqual(outcome["counts"]["128"]["different_class_near_rgb_lt_32"],1)
if __name__=="__main__":
    unittest.main()

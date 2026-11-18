#!/usr/bin/env python3
"""Synthetic P0 invariants; source-only, never claims actual Egret fill."""
import unittest
import numpy as np
from PIL import Image
from skimage import color,filters
from run_engine001_rgb_visual_mvp_p0 import METHODS,filter_candidate,composite,metrics,sha
class TestRGBVisualMVP(unittest.TestCase):
    def setUp(self):
        y,x=np.indices((320,200))
        self.full=np.stack([np.where(x<100,65,240),(x*3+y*2)%256,np.where(y<160,85,225)],axis=-1).astype('uint8')
        self.source=np.array(Image.fromarray(self.full).resize((150,240),Image.Resampling.LANCZOS))
        self.protected=np.zeros((240,150),bool)
        self.protected[60:75,30:70]=True
    def test_all_filters_protect_original_rgb(self):
        for name,p in METHODS.items():
            with self.subTest(name=name):
                out=filter_candidate(self.full,p,self.source,self.protected)
                self.assertEqual(out.shape,(240,150,3))
                self.assertEqual(out.dtype,np.uint8)
                self.assertTrue(np.array_equal(out[self.protected],self.source[self.protected]))
    def test_all_filters_repeat_bitwise(self):
        for name,p in METHODS.items():
            with self.subTest(name=name):
                a=filter_candidate(self.full,p,self.source,self.protected)
                b=filter_candidate(self.full,p,self.source,self.protected)
                self.assertEqual(sha(a.tobytes()),sha(b.tobytes()))
    def test_unpinned_method_and_bad_shape_blocked(self):
        with self.assertRaisesRegex(ValueError,'BLOCKED_SHAPE'):
            filter_candidate(self.full[:100],METHODS['BILATERAL_LOW'],self.source,self.protected)
        with self.assertRaisesRegex(ValueError,'BLOCKED_METHOD'):
            filter_candidate(self.full,{'op':'unregistered'},self.source,self.protected)
    def test_composite_correct_native_roi_only(self):
        contour=np.zeros((720,1380,4),dtype=np.uint8)
        contour[100:105,465:470]=[30,60,90,255]
        result=composite(self.source,Image.fromarray(contour,'RGBA'))
        self.assertEqual(result.size,(450,720))
        self.assertEqual(result.getpixel((0,100)),(30,60,90))
        self.assertEqual(result.getpixel((449,719)),tuple(self.source[-1,-1]))
    def test_identity_candidate_is_not_improvement(self):
        contour=np.zeros((720,1380,4),dtype=np.uint8)
        contour[100:105,465:470]=[30,60,90,255]
        mag=filters.sobel(color.rgb2gray(self.source/255.))
        positive=mag[mag>0];threshold=np.percentile(positive,90)
        r=metrics(self.source,self.source,self.protected,Image.fromarray(contour,'RGBA'),
                  mag>=threshold,threshold,(mag>0)&(mag<np.percentile(positive,50)))
        self.assertEqual(r['whole_mean_deltaE00'],0)
        self.assertEqual(r['changed_pixels'],0)
        self.assertEqual(r['flat_region_roughness_reduction'],0)
        self.assertEqual(r['source_gate'],'SOURCE_GATE_FAIL')
if __name__=='__main__':unittest.main()

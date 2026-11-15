#!/usr/bin/env python3
"""Isolated V34 algorithmic regression checks; no native-brush acceptance claims."""
import unittest
import numpy as np
from PIL import Image
from run_engine001_native_warm_color_v34 import median_map,warm_mask,mae,recolor_strokes

class V34ColorOnlyTests(unittest.TestCase):
    def test_lower_median_is_deterministic_and_original_unchanged(self):
        pixels=np.full((240,150,3),255,dtype=np.uint8)
        idx=np.full((240,150),5,dtype=np.int16)
        pixels[0,0]=[20,30,40]
        pixels[0,1]=[100,110,120]
        idx[0,:2]=4
        idx[1,:]=6
        idx[2,:]=7
        original=Image.fromarray(pixels.copy(),"RGB")
        colors=median_map(original,idx,[4,5,6,7])
        self.assertEqual(colors[4],[20,30,40]) # two pixels => lower median
        self.assertEqual(colors[5],[255,255,255])
        self.assertTrue(np.array_equal(np.asarray(original),pixels))
        self.assertEqual(colors,median_map(original,idx,[4,5,6,7]))
    def test_reject_empty_label(self):
        original=Image.new("RGB",(150,240),"white")
        labels=np.zeros((240,150),dtype=np.int16)
        with self.assertRaises(ValueError):
            median_map(original,labels,[4])
    def test_recolor_only_changes_color_no_aliasing(self):
        base=[{"strokeId":"a","width":2,"colorIndex":4,"colorRgb":0,
               "points":[{"x":155.0,"y":1.0},{"x":155.25,"y":1.0}]},
              {"strokeId":"b","width":2,"colorIndex":7,"colorRgb":0,
               "points":[{"x":190.0,"y":2.0},{"x":191.0,"y":2.0}]}]
        colors={4:[255,100,0],5:[210,210,210],6:[50,60,70],7:[1,2,3]}
        recolored=recolor_strokes(base,colors)
        self.assertEqual(recolored[0]["colorRgb"],0xff6400)
        self.assertEqual(recolored[1]["colorRgb"],0x010203)
        self.assertEqual(base[0]["colorRgb"],0)
        recolored[0]["points"][0]["x"]=999
        self.assertEqual(base[0]["points"][0]["x"],155)
        self.assertEqual(recolored[0]["width"],2)
        self.assertEqual(len(recolored),2)
    def test_invalid_palette_fail_closed(self):
        base=[{"colorIndex":4,"colorRgb":0,"points":[]}]
        with self.assertRaises(ValueError):
            recolor_strokes(base,{4:[260,0,0],5:[0,0,0],6:[0,0,0],7:[0,0,0]})
        with self.assertRaises(ValueError):
            recolor_strokes(base,{4:[1,2,3]})
        with self.assertRaises(ValueError):
            recolor_strokes([{"colorIndex":9}],{4:[1,2,3],5:[0,0,0],6:[0,0,0],7:[0,0,0]})
    def test_warm_mask_and_mae(self):
        pixels=np.full((240,150,3),255,dtype=np.uint8)
        pixels[0,0]=[255,128,0] # warm orange
        pixels[0,1]=[0,0,255] # cold blue
        original=Image.fromarray(pixels,"RGB")
        mask=warm_mask(original)
        self.assertTrue(mask[0,0])
        self.assertFalse(mask[0,1])
        self.assertEqual(int(mask.sum()),1)
        self.assertEqual(mae(original,original),0)
        other=pixels.copy();other[0,0]=[254,128,0]
        self.assertAlmostEqual(mae(Image.fromarray(other,"RGB"),original,mask),1/3)
        with self.assertRaises(ValueError):
            mae(original,original,np.zeros((240,150),bool))
if __name__=="__main__":
    unittest.main()

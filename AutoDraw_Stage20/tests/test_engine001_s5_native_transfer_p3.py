"""Synthetic checks for P3 coordinate/assembly contract only, not native quality."""
import unittest

import numpy as np

import run_engine001_s5_native_transfer_p3 as p


class GeometryTest(unittest.TestCase):
    def test_all_cores_exact_once(self):
        counts=np.zeros((p.H,p.W),np.uint8)
        for row in range(p.NY):
            for col in range(p.NX):
                x,y,x1,y1=p.bounds(row,col)
                counts[y:y1,x:x1]+=1
        self.assertTrue(np.all(counts==1))
        self.assertEqual(p.bounds(6,7),(1232,1800,1235,1920))

    def test_halo_and_padding(self):
        source=np.zeros((p.H,p.W,3),np.uint8)
        source[:,:,0]=np.arange(p.W,dtype=np.int64)%251
        for row,col in [(0,0),(1,2),(6,7)]:
            x,y,x1,y1=p.bounds(row,col)
            tile=p.tile_target(source,row,col)
            self.assertEqual(tile.shape,(348,224,3))
            self.assertTrue(np.array_equal(tile[24:24+y1-y,24:24+x1-x],source[y:y1,x:x1]))
        self.assertTrue(np.all(p.tile_target(source,0,0)[:24]==255))
        self.assertTrue(np.all(p.tile_target(source,6,7)[:,27:]==255))

    def test_exact_backing_and_shared_strip(self):
        a=np.zeros((720,1380,4),np.uint8)
        a[60:660,514:866]=17
        self.assertTrue(np.all(p.region(a,0,0,p.bounds(0,0))==17))
        self.assertEqual(p.region(a,6,7,p.bounds(6,7)).shape,(240,6,4))
        # Same global 16-source-pixel strip must be accessible from both tiles.
        rect=(168,0,184,300)
        self.assertEqual(p.region(a,0,0,rect).shape,(600,32,4))
        self.assertEqual(p.region(a,0,1,rect).shape,(600,32,4))
        with self.assertRaises(RuntimeError):
            p.region(a,0,0,(1000,0,1001,1))

    def test_alpha_composite(self):
        raw=np.array([[[0,0,0,0],[0,0,0,255]]],np.uint8)
        self.assertTrue(np.array_equal(p.white_rgb(raw),np.array([[[255,255,255],[0,0,0]]])))


if __name__=="__main__":
    unittest.main()

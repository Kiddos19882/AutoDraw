"""ENGINE-001 V20 synthetic source and owner safety guards."""
import unittest
import numpy as np
from run_engine001_anilines_v20 import (chain_of_component,geometry_masks,owner_guard,candidates)

class V20Tests(unittest.TestCase):
    def test_simple_chain(self):
        self.assertEqual(chain_of_component([(10,10),(11,10),(12,10)]),
                         [(10,10),(11,10),(12,10)])
        self.assertIsNone(chain_of_component([(10,10)]))
        self.assertIsNone(chain_of_component([(i,10) for i in range(10)]))

    def test_two_and_eight_pixel_source_chains(self):
        self.assertEqual(len(chain_of_component([(20,60),(21,60)])),2)
        full=[(30+i,60) for i in range(8)]
        self.assertEqual(chain_of_component(full),full)
        self.assertIsNone(chain_of_component([(20,60),(21,60),(21,60)]))
        self.assertIsNone(chain_of_component([(20,60),(22,60)]))

    def test_wrong_palette_dimensions(self):
        with self.assertRaises(ValueError):
            owner_guard(np.zeros((240,460),bool),np.zeros((240,150),np.uint8),0)

    def test_branch_and_cycle(self):
        self.assertIsNone(chain_of_component([(10,10),(11,10),(10,11),(11,11)]))
        self.assertIsNone(chain_of_component([(10,10),(11,10),(12,10),(11,11)]))

    def test_owner_background_boundary_and_roi(self):
        raster=np.zeros((240,460),bool);raster[100,205]=True
        palette=np.full((240,460),4,np.uint8)
        self.assertEqual(owner_guard(raster,palette,0),4)
        self.assertIsNone(owner_guard(raster,palette,4))
        palette[100,206]=3
        self.assertIsNone(owner_guard(raster,palette,0))
        raster=np.zeros((240,460),bool);raster[100,155]=True
        self.assertIsNone(owner_guard(raster,palette,0))

    def test_real_candidate_guards_on_synthetic(self):
        missing=np.zeros((320,200),bool)
        for x in (60,61,62):missing[100,x]=True
        ani=missing.copy()
        pal=np.full((240,460),4,np.uint8)
        accepted,rejected,source,_,n=candidates(missing,ani,pal,0)
        self.assertEqual((len(accepted),n),(1,1))
        self.assertEqual(sum(rejected.values()),0)
        self.assertTrue(np.all(source<=ani))
        blocked,rejected,_,_,_=candidates(missing,ani,pal,4)
        self.assertEqual(len(blocked),0)
        self.assertEqual(rejected["owner_ambiguous"],1)
        ani[100,61]=False
        rejected_paths,reasons,_,_,_=candidates(missing,ani,pal,0)
        self.assertEqual(len(rejected_paths),0)
        self.assertEqual(reasons["raster_outside_source"],1)

    def test_no_source_shortcut(self):
        src,logical=geometry_masks([(5,5),(6,5),(7,5)])
        self.assertEqual(int(src.sum()),3)
        self.assertGreater(int(logical.sum()),0)

if __name__=="__main__":
    unittest.main()

"""ENGINE-001 V21 owner-boundary split safety regression."""
import unittest
import numpy as np
from run_engine001_anilines_v21 import split_chain
from run_engine001_anilines_v20 import geometry_masks,owner_guard

class V21Tests(unittest.TestCase):
    def setUp(self):
        self.ani=np.ones((320,200),bool)
        self.palette=np.full((240,460),4,np.uint8)

    def test_uniform_three_source_points(self):
        runs,verts,edges=split_chain([(80,100),(81,100),(82,100)],self.ani,self.palette,0)
        self.assertEqual(runs,[[(80,100),(81,100),(82,100)]])
        self.assertEqual((sum(verts),sum(edges)),(3,2))

    def test_boundary_never_bridge(self):
        chain=[(80+i,100) for i in range(5)]
        # Third point logical x=216/217; ban its 3x3 owner neighborhood.
        center=round(82*.75+155)
        self.palette[75,center]=1
        runs,verts,edges=split_chain(chain,self.ani,self.palette,0)
        self.assertFalse(edges[1])
        self.assertFalse(edges[2])
        self.assertFalse(any(a[0]==(81,100) and a[-1]==(83,100) for a in runs))
        for part in runs:
            self.assertIsNotNone(owner_guard(geometry_masks(part)[1],self.palette,0))

    def test_color_owner_change_cannot_connect(self):
        chain=[(70,100),(71,100),(72,100),(73,100)]
        # Force different neighborhood class on final point.
        x=round(73*.75+155)
        self.palette[:,x:]=5
        runs,_,edges=split_chain(chain,self.ani,self.palette,0)
        self.assertFalse(edges[-1])
        for p in runs:
            self.assertIsNotNone(owner_guard(geometry_masks(p)[1],self.palette,0))

    def test_background_rejects(self):
        runs,verts,edges=split_chain([(80,100),(81,100)],self.ani,self.palette,4)
        self.assertEqual(runs,[])
        self.assertEqual(sum(verts),0)
        self.assertEqual(sum(edges),0)

    def test_foreign_source_segment_rejected(self):
        self.ani[100,81]=False
        runs,_,edges=split_chain([(80,100),(81,100),(82,100)],self.ani,self.palette,0)
        self.assertEqual(runs,[])
        self.assertEqual(edges,[False,False])

    def test_disconnected_points_not_bridged(self):
        # Caller must provide only V20-validated unit-step chains.
        from run_engine001_anilines_v20 import chain_of_component
        self.assertIsNone(chain_of_component([(80,100),(82,100)]))

if __name__=="__main__":
    unittest.main()

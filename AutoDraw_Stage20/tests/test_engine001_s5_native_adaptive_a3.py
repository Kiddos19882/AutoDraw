"""Synthetic route contracts only, not native visual evidence."""
import unittest
import numpy as np
import run_engine001_s5_native_adaptive_a3 as v
import run_engine001_s5_native_adaptive_a1 as a


def stroke(pts,w,c,i):
    return dict(points=pts,width=w,colorRgb=c,strokeId=f"icon-{i}")


class ContinuousContracts(unittest.TestCase):
    def test_exact_local_shapes_and_union(self):
        self.assertEqual(len(v.shapes()),20)
        self.assertEqual(len(set(tuple(s) for s in v.shapes())),20)
        z=np.zeros((40,73,73),np.uint8)
        z[:,34:39,34:39]=255
        z[0,33,36]=1
        s,c=v.local_masks(z)
        self.assertTrue(s[33,36])
        self.assertFalse(c[33,36])
        z[0,0,0]=1
        with self.assertRaises(RuntimeError):
            v.local_masks(z)

    def test_fit_rejects_other_color_and_exterior(self):
        s=np.zeros((73,73),bool)
        s[34:39,34:39]=True
        m=np.ones((60,80),bool);m[20,21]=False
        result=v.fit(m,s)
        self.assertFalse(result[20,20])
        self.assertFalse(result[0,30])
        self.assertTrue(result[40,40])

    def test_maximal_runs_and_alternation(self):
        m=np.ones((8,42),bool)
        runs=v.lanes(m,3,m)
        self.assertEqual(runs,[[(0,0),(41,0)],[(41,3),(0,3)],
                               [(0,6),(41,6)],[(41,7),(0,7)]])
        self.assertEqual(v.lanes(m,3,np.zeros_like(m)),[])

    def test_connector_around_hole(self):
        m=np.ones((9,12),bool);m[1:8,4:8]=False
        walk=v.connect(m,(1,4),(10,4))
        self.assertEqual(walk[0],(1,4))
        self.assertEqual(walk[-1],(10,4))
        self.assertTrue(all(m[y,x] for x,y in walk))
        self.assertEqual(v.grid_walk(v.compress(walk)),walk)
        m[:,5]=False
        with self.assertRaises(RuntimeError):
            v.connect(m,(1,4),(10,4))

    def test_no_vertex_or_length_cap_and_no_reversal_loss(self):
        m=np.ones((90,50),bool)
        walk=v.route(m,v.lanes(m,1,m))
        p=v.compress(walk)
        self.assertGreater(len(p),128)
        self.assertGreater(len(walk),1000)
        self.assertEqual(v.grid_walk(p),walk)
        self.assertEqual(v.compress([(0,0),(1,0),(2,0),(1,0)]),
                         [(0,0),(2,0),(1,0)])

    def test_region_continuity_and_same_color(self):
        target=np.zeros((150,210,3),np.uint8)
        target[:,105:]=[100,200,50]
        s=np.zeros((73,73),bool);s[33:40,33:40]=True
        proof={"measurements":{f"{d}:2":{"lateral_min_backing_px":6}
                              for d in ("horizontal","vertical")}}
        paths,_=v.broad_plan(target,{2:(s,s)},proof,stroke)
        self.assertEqual(len(paths),2)
        sy,sx=np.nonzero(s)
        for p in paths:
            points=[(round(q["x"]-a.OX/3),round(q["y"])) for q in p["points"]]
            walk=v.grid_walk(points)
            self.assertGreater(len(walk),24)
            for x,y in walk:
                self.assertTrue(np.all(target[3*y+sy-v.R,3*x+sx-v.R]
                        ==np.array(list(p["colorRgb"].to_bytes(3,"big")))))
        self.assertEqual(v.continuity(paths)["multi_vertex"],2)


if __name__=="__main__":
    unittest.main()

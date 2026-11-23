"""Synthetic contracts; these do not demonstrate native quality."""
import unittest
import numpy as np
import run_engine001_s5_native_adaptive_a2 as v
import run_engine001_s5_native_adaptive_a1 as a


def fixture():
    z=np.zeros((2,73,115),np.uint8)
    z[:,33:40,45:70]=255
    z[1,32,57]=1
    return z


def stroke(pts,w,c,i):
    return dict(points=pts,width=w,colorRgb=c,strokeId=f"icon-{i}")


class A2Contracts(unittest.TestCase):
    def test_observed_union_and_core(self):
        s,c=v.mask_pair(fixture())
        self.assertTrue(s[32,57])
        self.assertFalse(c[32,57])
        self.assertTrue(c[36,57])
        z=fixture()
        z[0,0,57]=1
        with self.assertRaises(RuntimeError):
            v.mask_pair(z)

    def test_fit_anchor_and_outside(self):
        s,c=v.mask_pair(fixture())
        target=np.ones((100,150),bool)
        target[46,60]=False
        fit=v.fit(target,s)
        self.assertFalse(fit[50,60])
        self.assertFalse(fit[50,0])
        self.assertTrue(fit[70,80])
        self.assertEqual(v.pitch(c,6)[:2],(12,3))
        self.assertEqual(v.pitch(c,3)[:2],(6,3))

    def test_lengths_and_color_containment(self):
        s,c=v.mask_pair(fixture())
        target=np.zeros((100,150,3),np.uint8)
        target[:,75:]=[100,200,50]
        atlas={(w,l):(s,c) for w in range(2,11) for l in v.LENGTHS}
        paths,_=v.broad_plan(target,atlas,stroke)
        self.assertTrue(paths)
        sy,sx=np.nonzero(s)
        for p in paths:
            u,q=p["points"]
            x=round(3*(u["x"]+q["x"])/2)-a.OX
            y=round(3*u["y"])
            self.assertIn(round(q["x"]-u["x"]),v.LENGTHS)
            self.assertTrue(np.all(target[y+sy-v.RY,x+sx-v.RX]
                     ==np.array(list(p["colorRgb"].to_bytes(3,"big")))))

    def test_ranges(self):
        self.assertEqual(v.ranges([0,0,1,0,0,0,0,1,0,0]),[(1,3),(6,8)])
        self.assertEqual(v.ranges([1,0,1,0]),[(0,3)])
        self.assertEqual(v.ranges([0,0]),[])
        self.assertEqual(v.ranges([0,1]),[(0,1)])

    def test_residual_split_and_keep_unsampled(self):
        target=np.zeros((40,100,3),np.uint8)
        raw=np.zeros((40,100,4),np.uint8)
        raw[:,:,3]=255
        raw[15,40,3]=0
        p=stroke([dict(x=(a.OX+10)/3,y=5),dict(x=(a.OX+70)/3,y=5)],1,0,0)
        extra=dict(p,colorRgb=0x123456)
        paths,counts=v.residual([p,extra],target,raw,(2,2))
        self.assertEqual(len(paths),2)
        self.assertEqual(counts["split_original"],1)
        self.assertGreater(paths[0]["points"][0]["x"],p["points"][0]["x"])
        self.assertLess(paths[0]["points"][1]["x"],p["points"][1]["x"])
        self.assertEqual(paths[1],extra)
        raw[:,:,3]=255
        self.assertEqual(v.residual([p],target,raw,(2,2))[0],[])
        raw[:,:,3]=0
        self.assertEqual(v.residual([p],target,raw,(2,2))[0],[p])


if __name__=="__main__":
    unittest.main()

"""Synthetic algorithm contracts only. Never evidence of native brush quality."""
import unittest
import numpy as np

import run_engine001_s5_native_adaptive_a1 as a


def fixture():
    alpha=np.zeros((2,73,79),np.uint8)
    alpha[:,34:39,20:59]=255
    alpha[1,33,40]=1
    return a.masks(alpha)


def proof():
    return dict(renderer=a.RENDERER,smooth=False,mode="normal",probes=80,
        measurements={f"horizontal:{w}":dict(lateral_min_backing_px=3*w,
                      axial_min_backing_px=36+3*w) for w in range(1,11)})


def stroke(pts,w,c,i):
    return dict(points=pts,width=w,colorRgb=c,strokeId=f"icon-{i}")


class A1Contracts(unittest.TestCase):
    def test_measured_support_union_core_intersection(self):
        s,c=fixture()
        self.assertTrue(s[33,40])
        self.assertFalse(c[33,40])
        self.assertTrue(c[36,39])
        with self.assertRaises(RuntimeError):
            a.masks(np.zeros((2,73,79),np.uint8))

    def test_fit_rejects_foreign_pixel_and_board_exterior(self):
        s,_=fixture()
        color=np.ones((100,150),bool)
        color[47,61]=False
        fit=a.fit_centers(color,s)
        self.assertFalse(fit[50,60])
        self.assertFalse(fit[50,0])
        self.assertTrue(fit[70,80])

    def test_pitch_uses_measured_geometry(self):
        p=proof()
        self.assertEqual(a.pitch(p,2),(27,3))
        self.assertEqual(a.pitch(p,10),(27,24))
        p["smooth"]=True
        with self.assertRaises(RuntimeError):
            a.pitch(p,2)

    def test_broad_candidates_same_color(self):
        target=np.zeros((100,150,3),np.uint8)
        target[:,75:]=[100,200,50]
        s,c=fixture()
        paths,_=a.broad_plan(target,{w:(s,c) for w in range(1,11)},proof(),stroke)
        self.assertTrue(paths)
        sy,sx=np.nonzero(s)
        for p in paths:
            x=round(3*(p["points"][0]["x"]+6))-a.OX
            y=round(3*p["points"][0]["y"])
            self.assertTrue(np.all(target[y+sy-a.RY,x+sx-a.RX]
                 ==np.array(list(p["colorRgb"].to_bytes(3,"big")))))
            self.assertTrue(2<=p["width"]<=10)

    def test_readback_preserves_uncovered_and_unsampled_paths(self):
        target=np.zeros((40,60,3),np.uint8)
        raw=np.zeros((40,60,4),np.uint8)
        raw[:,:,:3]=0;raw[:,:,3]=255
        paths=[stroke([dict(x=(a.OX+x)/3,y=5),dict(x=(a.OX+x+3)/3,y=5)],1,0,i)
               for i,x in enumerate((10,35))]
        extra=stroke(paths[0]["points"],1,0x123456,3)
        raw[15,35,3]=0
        keep,reasons=a.retain_detail(paths+[extra],target,raw,(2,2))
        self.assertEqual(keep,[paths[1],extra])
        self.assertEqual(reasons["already_native_covered"],1)
        self.assertEqual(reasons["actual_missing_or_wrong"],1)
        self.assertEqual(reasons["no_backing_samples"],1)
        raw[15,35]=[255,255,255,255]
        self.assertEqual(a.retain_detail(paths,target,raw,(2,2))[0],[paths[1]])

    def test_composition_order(self):
        b=[stroke([],10,0,0),stroke([],2,0xeeeeee,1)]
        d=[stroke([],1,0,2),stroke([],1,0xeeeeee,3)]
        final=a.combine(b,d)
        self.assertEqual([p["width"] for p in final],[2,1,10,1])
        self.assertEqual(len({p["strokeId"] for p in final}),4)


if __name__=="__main__":
    unittest.main()

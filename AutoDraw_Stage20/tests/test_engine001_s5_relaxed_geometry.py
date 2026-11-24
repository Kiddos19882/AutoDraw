"""A9 MODEL_ONLY geometry contracts; native quality checked separately."""
import unittest
import numpy as np
import engine001_s5_relaxed_geometry as s

def masks():
    support=np.zeros((73,73),bool)
    support[35:38,35:38]=True
    return support,support.copy()

class RelaxedTests(unittest.TestCase):
    def test_soft_and_free(self):
        support,core=masks()
        target=np.zeros((12,12),bool); target[4:7,5]=True
        self.assertFalse(s.candidate_mask(target,support,core,0).any())
        self.assertTrue(s.candidate_mask(target,support,core,None)[5,5])
        self.assertFalse(s.candidate_mask(target,support,core,.5)[5,5])
        self.assertTrue(s.candidate_mask(target,support,core,.8)[5,5])
    def test_diagonal_maximal(self):
        valid=np.eye(8,dtype=bool)
        runs=s.runs_for_direction(valid,valid.astype(float),(1,1),1)
        self.assertEqual(runs,[((0,0),(7,7))])
    def test_singleton_and_fractional(self):
        support,core=masks()
        want=np.full((15,15,3),255,np.uint8);want[7,7]=0
        proof={"measurements":{f"{d}:4":{"lateral_min_backing_px":3} for d in ("horizontal","vertical")}}
        stroke=lambda pts,w,rgb,i:dict(points=pts,width=w,colorRgb=rgb,strokeId=f"icon-{i}")
        mask=np.zeros((15,15),bool);mask[7,7]=True
        self.assertEqual(s.runs_for_direction(mask,mask.astype(float),(1,0),1),[((7,7),(7,7))])
        self.assertEqual(s.tap_end((7,7),mask.shape),(8,7))
        want[4:10,4:10]=0
        paths,_=s.plan(want,{4:(support,core)},proof,stroke,None)
        self.assertTrue(paths);s.validate(paths)
        self.assertTrue(any(p["x"]%1 or p["y"]%1 for a in paths for p in a["points"]))
    def test_no_forbidden_width(self):
        with self.assertRaises(ValueError):
            s.validate([dict(width=3,points=[dict(x=1,y=1),dict(x=2,y=2)])])
    def test_white_repair(self):
        support,core=masks()
        want=np.full((15,15,3),255,np.uint8)
        actual=want.copy();actual[3:12,3:12]=0
        proof={"measurements":{f"{d}:4":{"lateral_min_backing_px":3} for d in ("horizontal","vertical")}}
        stroke=lambda pts,w,rgb,i:dict(points=pts,width=w,colorRgb=rgb,strokeId=f"icon-{i}")
        paths,_=s.plan(want,{4:(support,core)},proof,stroke,None,actual,True)
        self.assertTrue(paths);self.assertTrue(all(p["colorRgb"]==0xffffff for p in paths));s.validate(paths)

if __name__=="__main__":
    unittest.main()

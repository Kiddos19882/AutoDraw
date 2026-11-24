"""A5 model-only interval contracts; native render required separately."""
import unittest
from copy import deepcopy
import math
import run_engine001_s5_native_adaptive_a5 as v

def stroke(x,z,y=1,color=0,i=0,width=1):
    return dict(points=[dict(x=x,y=y),dict(x=z,y=y)],colorRgb=color,
                width=width,strokeId=f"icon-{i}")

def intervals(paths):
    return [(s["colorRgb"],s["points"][0]["y"],
             min(p["x"] for p in s["points"]),max(p["x"] for p in s["points"]))
            for s in paths]

class UnionContracts(unittest.TestCase):
    def test_overlap_nested_touching_and_gap(self):
        paths=[stroke(0,4,i=0),stroke(2,3,i=1),stroke(7,4,i=2),
               stroke(8,10,i=3),stroke(10,12,i=4),stroke(15,16,i=5)]
        out,ledger=v.union_detail(paths)
        self.assertEqual(intervals(out),[(0,1,0,7),(0,1,8,12),(0,1,15,16)])
        self.assertEqual(ledger["merged_groups"],2)
        self.assertEqual(out[-1],paths[-1])
        self.assertEqual(ledger["before"],6)
        self.assertEqual(ledger["after"],3)

    def test_color_row_phase_and_positive_gap_never_joined(self):
        paths=[stroke(0,4),stroke(2,5,color=1),stroke(2,5,y=1.0000000001),
               stroke(4.0000000001,6)]
        out,_=v.union_detail(paths)
        self.assertEqual(out,paths)

    def test_exact_union_and_input_immutability(self):
        paths=[stroke(6,9,i=0),stroke(0,3,i=1),stroke(2,7,i=2),
               stroke(12,15,i=3),stroke(13,14,i=4)]
        copy=deepcopy(paths)
        out,ledger=v.union_detail(paths)
        self.assertEqual(paths,copy)
        self.assertEqual(intervals(out),[(0,1,0,9),(0,1,12,15)])
        self.assertEqual(out[0]["strokeId"],paths[0]["strokeId"])
        self.assertEqual(v.union_detail(paths),(out,ledger))
        self.assertEqual(v.union_detail(out)[0],out)
        for x in [i/4 for i in range(-4,65)]:
            self.assertEqual(any(lo<=x<=hi for _,_,lo,hi in intervals(paths)),
                             any(lo<=x<=hi for _,_,lo,hi in intervals(out)))
        self.assertLess(ledger["per_color"]["0"]["length_after"],
                        ledger["per_color"]["0"]["length_before"])

    def test_long_continuous_without_cap(self):
        paths=[stroke(i,i+4,i=i) for i in range(300)]
        out,_=v.union_detail(paths)
        self.assertEqual(len(out),1)
        self.assertEqual(intervals(out),[(0,1,0,303)])

    def test_invalid_and_empty(self):
        self.assertEqual(v.union_detail([])[0],[])
        diagonal=stroke(0,1)
        diagonal["points"][1]["y"]=2
        for s in [diagonal,stroke(1,1),stroke(0,math.inf),stroke(0,1,width=2)]:
            with self.assertRaises(RuntimeError):
                v.union_detail([s])

if __name__=="__main__":
    unittest.main()

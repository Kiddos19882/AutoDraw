"""A4 route topology contracts only; not Egret evidence."""
import unittest
import numpy as np
import run_engine001_s5_native_adaptive_a3 as p
import run_engine001_s5_native_adaptive_a4 as v
from test_engine001_s5_native_adaptive_a3 import stroke

class LocalRouteContracts(unittest.TestCase):
    def test_nearest_and_disconnected(self):
        m=np.ones((9,12),bool)
        m[1:8,4:8]=False
        end,walk=v.nearest(m,(1,4),{(10,4):1,(1,6):2},set())
        self.assertEqual(end,(1,6))
        self.assertEqual(len(walk),3)
        m[:,5]=False
        with self.assertRaises(RuntimeError):
            v.nearest(m,(1,4),{(10,4):1},set())

    def test_branched_lanes_are_preserved_and_deterministic(self):
        m=np.ones((22,30),bool)
        m[1:21,12:18]=False
        runs=p.lanes(m,2,m)
        old,new,order,changed=v.choose_route(m,runs)
        self.assertEqual(v.choose_route(m,runs),(old,new,order,changed))
        self.assertEqual(sorted(i for i,_ in order),list(range(len(runs))))
        self.assertLessEqual(v.cost(new),v.cost(old))
        self.assertTrue(all(m[y,x] for x,y in new))
        edges={v.edge(u,w) for u,w in zip(new,new[1:])}
        for run in runs:
            lane=p.grid_walk(run)
            self.assertTrue(all(v.edge(u,w) in edges for u,w in zip(lane,lane[1:])))
        self.assertEqual(p.grid_walk(p.compress(new)),new)
        self.assertLess(v.cost(new),v.cost(old))

    def test_no_cap_and_tie_fallback(self):
        m=np.ones((90,50),bool)
        runs=p.lanes(m,1,m)
        old,new,order,changed=v.choose_route(m,runs)
        self.assertFalse(changed)
        self.assertEqual(old,new)
        self.assertGreater(len(p.compress(new)),128)
        self.assertGreater(len(new),1000)

    def test_width_allocation_matches_a3(self):
        target=np.zeros((150,210,3),np.uint8)
        target[:,105:]=[100,200,50]
        target[45:110,30:45]=255
        s=np.zeros((73,73),bool)
        s[33:40,33:40]=True
        proof={"measurements":{f"{d}:2":{"lateral_min_backing_px":6}
                              for d in ("horizontal","vertical")}}
        old,new,counts,ledger=v.broad_plan(target,{2:(s,s)},proof,stroke)
        ref,ref_counts=p.broad_plan(target,{2:(s,s)},proof,stroke)
        self.assertEqual(old,ref)
        self.assertEqual(counts,ref_counts)
        self.assertEqual([(q["width"],q["colorRgb"]) for q in old],
                         [(q["width"],q["colorRgb"]) for q in new])
        self.assertLessEqual(v.route_metrics(new)["total_edges"],v.route_metrics(old)["total_edges"])
        self.assertTrue(all(tuple(row["new_cost"])<=tuple(row["old_cost"]) for row in ledger))

if __name__=="__main__":
    unittest.main()

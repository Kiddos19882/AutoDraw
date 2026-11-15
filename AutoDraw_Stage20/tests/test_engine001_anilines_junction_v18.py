"""Synthetic checks for V18 topology; not a human semantic evaluation."""
import unittest
from pathlib import Path
import numpy as np
from run_engine001_anilines_junction_v18 import (
    build_graph, trace, join_pairs, stitch, edge, arc, SOURCE_SHA, ANI_SHA
)

class V18TopologyTests(unittest.TestCase):
    def sk(self,points):
        img=np.zeros((320,200),dtype=bool)
        for x,y in points:img[y,x]=True
        return img

    def test_triangle_suppression_removes_edge_only(self):
        img=self.sk([(20,20),(21,20),(21,21)])
        graph,removed=build_graph(img)
        self.assertEqual(removed,1)
        self.assertEqual(len(graph),3)
        self.assertNotIn((21,21),graph[(20,20)])
        self.assertEqual(sum(map(len,graph.values()))//2,2)

    def test_isolated_diagonal_is_preserved(self):
        graph,removed=build_graph(self.sk([(20,20),(21,21)]))
        self.assertEqual(removed,0)
        self.assertIn((21,21),graph[(20,20)])

    def test_long_line_remains_one_chain(self):
        graph,_=build_graph(self.sk([(x,20) for x in range(10,30)]))
        chains,deg,edges=trace(graph)
        self.assertEqual(len(chains),1)
        self.assertEqual(edges,19)
        self.assertEqual(len(chains[0]),20)

    def test_straight_junction_pairing_without_new_points(self):
        pts=[(x,20) for x in range(10,30)]+[(20,19),(20,18),(20,17),(20,16)]
        graph,_=build_graph(self.sk(pts))
        chains,deg,edges=trace(graph)
        pairs,count=join_pairs(chains,deg)
        self.assertGreater(count,0)
        routes,ids=stitch(chains,pairs)
        self.assertEqual(sum(len(q) for q in ids),len(chains))
        self.assertTrue(all(all(p in graph for p in route) for route in routes))

    def test_no_gap_bridge(self):
        graph,_=build_graph(self.sk([(10,20),(11,20),(13,20),(14,20)]))
        chains,deg,edges=trace(graph)
        pairs,count=join_pairs(chains,deg)
        self.assertEqual(count,0)
        routes,ids=stitch(chains,pairs)
        self.assertEqual(edges,2)
        self.assertEqual(len(routes),2)

    def test_deterministic_graph_and_paths(self):
        points=[(x,40) for x in range(10,23)]+[(16,y) for y in range(35,46)]
        img=self.sk(points)
        def computed():
            g,drop=build_graph(img)
            c,d,e=trace(g)
            m,count=join_pairs(c,d)
            return drop,c,count,stitch(c,m)
        self.assertEqual(computed(),computed())

    def test_source_hash_is_pinned(self):
        import hashlib
        file=Path(__file__).resolve().parents[1]/"testImages/wV6VeZI9S1Y.png"
        self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(),SOURCE_SHA)
        self.assertEqual(file.stat().st_size,97308)
        self.assertEqual(len(ANI_SHA),64)

if __name__=="__main__":
    unittest.main()

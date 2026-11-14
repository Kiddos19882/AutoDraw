"""ENGINE-001 frozen V3 geometry guards; no native quality is inferred from tests."""
import unittest
import numpy as np
from run_engine001_adaptive_brush_v3 import (
    WIDTH, HEIGHT, WIDTHS, plan_adaptive, variable_footprint, _spans_in_distance
)


class AdaptiveBrushV3Test(unittest.TestCase):
    @staticmethod
    def fixed_synthetic():
        m=np.zeros((HEIGHT,WIDTH),dtype=bool)
        m[30:205,30:195]=True
        m[65:162,75:137]=False
        m[33:202,240:420]=True
        m[95:143,270:398]=False
        return m

    def test_mixed_sizes_and_determinism(self):
        one,a,images=plan_adaptive(self.fixed_synthetic())
        two,b,_=plan_adaptive(self.fixed_synthetic())
        self.assertEqual(one,two)
        self.assertEqual(a["candidate_decisions"],b["candidate_decisions"])
        self.assertEqual(images["target"].shape,(720,1380))
        self.assertTrue(all(s["width"] in WIDTHS for s in one))
        self.assertTrue(all(len(s["points"])>=2 for s in one))
        self.assertGreater(a["horizontal_strokes"],0)

    def test_candidate_limits_no_short_repairs(self):
        plan,meta,_=plan_adaptive(self.fixed_synthetic())
        self.assertLessEqual(meta["horizontal_strokes"],420)
        self.assertLessEqual(meta["outline_strokes"],8)
        self.assertLessEqual(meta["synthetic_vertices_not_chalk"],5900)
        for s in plan:
            self.assertTrue(all(0<=p["x"]<WIDTH and 0<=p["y"]<HEIGHT
                                for p in s["points"]))
        self.assertTrue(all(d["far"]==0 for d in meta["candidate_decisions"]
                            if d["decision"]=="ACCEPT"))

    def test_inward_distance_excludes_oversized_brush(self):
        distance=np.zeros((HEIGHT,WIDTH),dtype=np.float32)
        distance[10,10:45]=6.0
        self.assertEqual(_spans_in_distance(distance,30,10),[])
        self.assertEqual(_spans_in_distance(distance,8,10),[(10,45)])

    def test_variable_footprint_rejects_unregistered_sizes(self):
        with self.assertRaises(ValueError):
            variable_footprint({"width":3,"points":[{"x":20,"y":30},{"x":80,"y":30}]})
        p=variable_footprint({"width":8,"points":[{"x":20,"y":30},{"x":80,"y":30}]})
        self.assertGreater(int(p.sum()),100)

    def test_bad_source_shape_rejected(self):
        with self.assertRaises(ValueError):
            plan_adaptive(np.zeros((HEIGHT,WIDTH),dtype=bool))
        with self.assertRaises(ValueError):
            plan_adaptive(np.zeros((HEIGHT,WIDTH-1),dtype=bool))
        with self.assertRaises(ValueError):
            plan_adaptive(np.ones((HEIGHT,WIDTH),dtype=np.uint8))


if __name__=="__main__":
    unittest.main()

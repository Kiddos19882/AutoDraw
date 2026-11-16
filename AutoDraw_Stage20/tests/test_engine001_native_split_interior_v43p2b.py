#!/usr/bin/env python3
"""V43-P2b deterministic split test only, not a simulation of game brush."""
import unittest
import numpy as np
from test_engine001_endpoint_extension_v40p2 import plan
from run_engine001_native_split_interior_v43p2b import (
    longest_interior_run, split_plan)


class V43SplitInteriorTests(unittest.TestCase):
    def setUp(self):
        self.base=plan()  # previously frozen 2355/5682 full-outline fixture
        self.mask=np.zeros((240,460),dtype=bool)
        self.distance=np.zeros((240,460),dtype=np.float32)
        self.mask[5,201:230]=True
        self.distance[5,201:230]=6.0
        for idx in range(60):
            row=self.base["strokes"][idx]["stroke"]
            row["colorIndex"]=7
            row["points"]=[{"x":200.0,"y":5.0},{"x":230.0,"y":5.0}]

    def test_split_B40_C50_preserves_full_user_outline(self):
        b,selected_b=split_plan(self.base,self.mask,self.distance,4,4.0,40)
        c,selected_c=split_plan(self.base,self.mask,self.distance,6,5.0,50)
        self.assertEqual((len(selected_b),len(selected_c)),(40,50))
        self.assertEqual([x["original_id"] for x in selected_b],
                         [f"icon-{i}" for i in range(40)])
        self.assertEqual((len(b["strokes"]),b["synthetic_vertices_NOT_CHALK"]),(2435,5842))
        self.assertEqual((len(c["strokes"]),c["synthetic_vertices_NOT_CHALK"]),(2455,5882))
        for p,wide in ((b,4),(c,6)):
            self.assertEqual(p["strokes"][-410:],self.base["strokes"][-410:])
            self.assertEqual([p["strokes"][i]["stroke"]["width"] for i in (0,1,2)],
                             [2,wide,2])
            self.assertEqual(p["strokes"][0]["stroke"]["points"],
                             [{"x":200.0,"y":5.0},{"x":201.0,"y":5.0}])
            self.assertEqual(p["strokes"][1]["stroke"]["points"],
                             [{"x":201.0,"y":5.0},{"x":229.0,"y":5.0}])
            self.assertEqual(p["strokes"][2]["stroke"]["points"],
                             [{"x":229.0,"y":5.0},{"x":230.0,"y":5.0}])
        self.assertEqual(self.base["strokes"][0]["stroke"]["width"],2)
        self.assertEqual(self.base["strokes"][0]["stroke"]["points"][1]["x"],230.0)

    def test_A_exact_frozen_plan(self):
        a,selected=split_plan(self.base,self.mask,self.distance,2,0.0,0)
        self.assertEqual(a,self.base)
        self.assertEqual(selected,[])

    def test_short_or_unowned_interior_not_eligible(self):
        s=self.base["strokes"][0]["stroke"]
        self.mask[5,201:230]=False
        self.assertIsNone(longest_interior_run(s,self.mask,self.distance,4.0))
        self.mask[5,201:230]=True
        self.distance[5,201:230]=3.0
        self.assertIsNone(longest_interior_run(s,self.mask,self.distance,4.0))

    def test_fail_closed_inadequate_population_and_bad_rule(self):
        with self.assertRaisesRegex(ValueError,"not preregistered"):
            split_plan(self.base,self.mask,self.distance,8,4.0,40)
        self.mask[:,:]=False
        with self.assertRaisesRegex(ValueError,"INSUFFICIENT_ELIGIBLE"):
            split_plan(self.base,self.mask,self.distance,4,4.0,40)
        bad=dict(self.base)
        bad["synthetic_vertices_NOT_CHALK"]=7000
        with self.assertRaisesRegex(ValueError,"counts drift"):
            split_plan(bad,self.mask,self.distance,2,0.0,0)


if __name__=="__main__":
    unittest.main()

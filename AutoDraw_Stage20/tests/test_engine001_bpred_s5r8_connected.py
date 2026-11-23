import unittest
from unittest.mock import patch

import numpy as np

import engine001_bpred_s5r8_connected as r8
from test_engine001_bpred_s5r7_cell_marginal import sample


class ConnectedSweeps(unittest.TestCase):
    def test_owner_swatch_alpha_detail_and_determinism(self):
        arrays = sample()
        game = arrays["game_index"]
        ids = arrays["paintable_id"]
        rgba = arrays["original_rgba"]
        # Same-swatch owners share a border. A one-pixel neck joins the
        # two sides of a transparent slit inside the right-hand owner.
        ids[9:52, 60:80] = 3
        game[ids == 3] = 23
        ids[9:52, 54:60] = 2
        game[ids == 2] = 23
        for row in (*range(12, 30), *range(31, 50)):
            game[row, 85:88] = -1
            ids[row, 85:88] = 0
            rgba[row, 85:88, 3] = 0
        with patch.object(r8.r7.source, "swept_capsule_pixel_masks",
                          wraps=r8.r7.source.swept_capsule_pixel_masks) as oracle:
            result = r8.build_candidates(arrays)
            self.assertEqual(oracle.call_count, result["trials"])
        self.assertEqual(result, r8.build_candidates(arrays))
        broad = [s for s in result["proposals"] if s["phase"] == "broad"]
        self.assertTrue(any(len(s["points"]) >= 6 for s in broad))
        self.assertTrue(all(2 <= len(s["points"]) <= 32 for s in broad))
        seen = set()
        for s in result["proposals"]:
            pts = s["points"]
            self.assertTrue(all(a != b for a,b in zip(pts,pts[1:])))
            footprint = r8.r7.source.swept_capsule_pixel_masks(
                pts,s["brush_value"],1.,1.,game.shape[1],game.shape[0])
            for x,y in footprint["potential_cells"]:
                self.assertEqual(ids[y,x], s["paintable_id"])
                self.assertEqual(game[y,x], s["color_index"])
                self.assertEqual(rgba[y,x,3], 255)
            seen.update(footprint["potential_cells"])
        self.assertIn((20,25), seen)
        self.assertEqual(len(seen), result["potential_covered_pixel_count"])

    def test_split_when_only_connector_hits_obstacle(self):
        ids = np.ones((24,32), np.int32)
        ids[8:14,18:29] = 2
        game = np.ones_like(ids)
        lanes = [dict(points=((4.,4.),(24.,4.))), dict(points=((4.,18.),(24.,18.)))]
        proposal = dict(owner=1,color=1,width=4,lanes=lanes)
        for limit, expected in [(1,1),(2,1),(3,2)]:
            pool,calls,rejected = r8._validate([proposal],ids,game,ids>0,max_calls=limit)
            self.assertLessEqual(calls,limit)
            self.assertEqual(len(pool),expected)
            if limit == 3:
                self.assertEqual(rejected["split_unsafe_connector"],1)

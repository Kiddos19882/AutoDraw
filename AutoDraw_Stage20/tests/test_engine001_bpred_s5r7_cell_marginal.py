"""S5-R7 dual-axis cell DAG + dynamic source-owner marginal scoring E2."""
import unittest
import numpy as np

import engine001_bpred_s5r7_cell_marginal as r7
import engine001_bpred_s5r6_boustrophedon_cells as r6
from engine001_bpred_s5r2_region_candidates import (
    BlockedS5R2, swept_capsule_pixel_masks)


def sample(height=62, width=120):
    game=np.full((height,width),6,np.int16)
    ids=np.ones((height,width),np.int32)
    game[9:height-10,5:width//2-4]=23
    ids[9:height-10,5:width//2-4]=2
    game[9:height-10,width//2+4:width-5]=42
    ids[9:height-10,width//2+4:width-5]=3
    game[20:33,14:32]=6
    ids[20:33,14:32]=4  # genuinely enclosed white
    rgba=np.zeros((height,width,4),np.uint8)
    rgba[:,:,3]=255
    dot=np.zeros(game.shape,bool)
    dot[25,20]=True
    edge=np.zeros(game.shape,bool)
    edge[:,1:] |= ids[:,1:]!=ids[:,:-1]
    edge[1:,:] |= ids[1:,:]!=ids[:-1,:]
    return dict(game_index=game,paintable_id=ids,original_rgba=rgba,
                protected_original_dot=dot,source_edge=edge)


class R7Tests(unittest.TestCase):
    def test_two_axis_true_graph_and_transpose(self):
        a=sample()
        g0,g1=r7.dual_graphs(a["paintable_id"],a["original_rgba"][:,:,3]==255)
        self.assertEqual(g0["opaque_pixels"],g1["opaque_pixels"])
        for g in (g0,g1):
            self.assertEqual(sum(c["area"] for c in g["cells"]),
                             a["game_index"].size)
            self.assertTrue(all(u<v for u,v in g["edges"]))
        self.assertEqual((g0,g1),r7.dual_graphs(
            a["paintable_id"],a["original_rgba"][:,:,3]==255))

    def test_owner_diversity_without_hard_quota(self):
        a=sample()
        r=r7.build_candidates(a)
        self.assertTrue(r["scheduler"]["per_owner_broad"])
        self.assertIn("2",r["scheduler"]["per_owner_broad"])
        self.assertIn("3",r["scheduler"]["per_owner_broad"])
        self.assertGreaterEqual(r["scheduler"]["owner_broad_count"],2)
        self.assertEqual(sum(r["scheduler"]["orientation_broad"].values()),
                         r["phase_strokes"]["broad"])
        self.assertEqual(r["web_methods"]["Medial_Axis"],"NOT_IMPLEMENTED")
        self.assertEqual(r,r7.build_candidates(a))

    def test_hard_model_owner_geometry_and_limits(self):
        a=sample()
        r=r7.build_candidates(a)
        self.assertFalse(r["smooth"])
        self.assertFalse(r["safe_to_execute"])
        self.assertFalse(r["admissible_for_gameplay"])
        self.assertEqual(r["source_owner_status"],"MISSING")
        self.assertLessEqual(r["phase_trials"]["broad"],1400)
        self.assertLessEqual(r["phase_trials"]["detail"],600)
        self.assertLessEqual(r["phase_strokes"]["broad"],80)
        self.assertLessEqual(r["phase_strokes"]["detail"],120)
        h,w=a["game_index"].shape
        seen=set()
        for p in r["proposals"]:
            potential=swept_capsule_pixel_masks(p["points"],p["brush_value"],
                                                1.,1.,w,h)["potential_cells"]
            for x,y in potential:
                self.assertEqual(a["paintable_id"][y,x],p["paintable_id"])
                self.assertEqual(a["game_index"][y,x],p["color_index"])
                self.assertEqual(a["original_rgba"][y,x,3],255)
            seen.update(potential)
        self.assertEqual(len(seen),r["potential_covered_pixel_count"])
        self.assertEqual(sum(s["modeled_new_potential_cells"] for s in r["proposals"]),
                         len(seen))

    def test_donut_split_merge_both_orientations(self):
        game=np.full((50,72),5,np.int16)
        game[14:36,20:53]=-1
        ids=np.where(game>=0,1,0).astype(np.int32)
        a=sample()
        a["game_index"]=game
        a["paintable_id"]=ids
        a["original_rgba"]=np.zeros((50,72,4),np.uint8)
        a["original_rgba"][game>=0,3]=255
        a["protected_original_dot"]=np.zeros(game.shape,bool)
        a["source_edge"]=np.zeros(game.shape,bool)
        g0,g1=r7.dual_graphs(ids,a["original_rgba"][:,:,3]==255)
        self.assertGreater(g0["split_events"],0)
        self.assertGreater(g1["split_events"],0)
        r=r7.build_candidates(a)
        self.assertGreater(r["potential_covered_pixel_count"],0)

    def test_fail_closed_on_inconsistent_source(self):
        a=sample()
        a["source_edge"]=np.zeros((1,2),bool)
        with self.assertRaises(BlockedS5R2):
            r7.build_candidates(a)
        a=sample()
        for kw in ({"max_trials":0},{"max_trials":2001},
                   {"max_trials":True},{"max_strokes":201}):
            with self.assertRaises(BlockedS5R2):
                r7.build_candidates(a,**kw)


if __name__=="__main__":
    unittest.main()

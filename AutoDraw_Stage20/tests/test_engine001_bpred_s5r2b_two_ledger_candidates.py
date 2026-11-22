#!/usr/bin/env python3
"""E2 isolated S5-R2b broad/detail normal-only source tests."""
import unittest
import numpy as np
from engine001_bpred_s5r2b_two_ledger_candidates import (
    build_candidates, BlockedS5R2b, BROAD_TRIALS, DETAIL_TRIALS)
from engine001_bpred_s5r2_region_candidates import swept_capsule_pixel_masks


def scene(indexes, region_ids=None, dots=()):
    game=np.asarray(indexes,dtype=np.int16)
    h,w=game.shape
    ids=np.where(game>=0,1,0).astype(np.int32) if region_ids is None else np.asarray(region_ids,dtype=np.int32)
    rgba=np.zeros((h,w,4),dtype=np.uint8)
    rgba[game>=0,3]=255
    protected=np.zeros((h,w),dtype=bool)
    for y,x in dots:
        protected[y,x]=True
    return {"game_index":game,"paintable_id":ids,"original_rgba":rgba,
            "protected_original_dot":protected}


class S5R2bTests(unittest.TestCase):
    def assert_model_safety(self, a, r):
        self.assertEqual(r["drawing_mode"], "normal")
        self.assertIs(r["smooth"],False)
        self.assertIs(r["safe_to_execute"],False)
        self.assertIs(r["admissible_for_gameplay"],False)
        self.assertEqual(r["status"], "PARTIAL" if r["uncovered_potential_pixel_count"] else "MODEL_ONLY")
        self.assertLessEqual(r["phase_trials"]["broad"],BROAD_TRIALS)
        self.assertLessEqual(r["phase_trials"]["detail"],DETAIL_TRIALS)
        self.assertLessEqual(r["phase_strokes"]["broad"],80)
        self.assertLessEqual(r["phase_strokes"]["detail"],120)
        self.assertLessEqual(r["stroke_count"],200)
        h,w=a["game_index"].shape
        seen=set()
        for p in r["proposals"]:
            self.assertIs(p["smooth"],False)
            self.assertFalse(p["safe_to_execute"])
            self.assertIn(p["phase"],("broad","detail"))
            if p["phase"]=="broad":
                self.assertGreaterEqual(p["brush_value"],2)
            else:
                self.assertEqual(p["brush_value"],1)
            footprint=swept_capsule_pixel_masks(p["points"],p["brush_value"],1.,1.,w,h)
            for x,y in footprint["potential_cells"]:
                self.assertEqual(int(a["paintable_id"][y,x]),p["paintable_id"])
                self.assertEqual(int(a["game_index"][y,x]),p["color_index"])
                self.assertEqual(int(a["original_rgba"][y,x,3]),255)
                seen.add((x,y))
        self.assertEqual(len(seen),r["potential_covered_pixel_count"])

    def test_broad_first_with_protected_detail_reservation(self):
        a=scene([[4]*40 for _ in range(40)],dots=((0,0),(39,39)))
        r=build_candidates(a)
        self.assert_model_safety(a,r)
        self.assertGreater(r["phase_strokes"]["broad"],0)
        self.assertGreaterEqual(r["protected_dot_potential_covered"],2)
        self.assertEqual(r["proposals"][0]["phase"],"broad")
        self.assertEqual(r["protected_dot_remaining"],0)

    def test_donut_transparency_and_protected_hole_neighbour(self):
        grid=np.full((22,22),2,dtype=np.int16)
        grid[8:14,8:14]=-1
        a=scene(grid,[[1 if v>=0 else 0 for v in row] for row in grid],
                dots=((7,8),(14,8)))
        r=build_candidates(a)
        self.assert_model_safety(a,r)
        self.assertGreaterEqual(r["protected_dot_potential_covered"],2)

    def test_same_palette_different_region(self):
        game=np.full((24,24),5,dtype=np.int16)
        ids=np.tile(np.array([1]*12+[2]*12,dtype=np.int32),(24,1))
        a=scene(game,ids)
        self.assert_model_safety(a,build_candidates(a))

    def test_single_pixel_and_checkerboard(self):
        single=scene([[-1,-1,-1],[-1,7,-1],[-1,-1,-1]],dots=((1,1),))
        self.assert_model_safety(single,build_candidates(single))
        checker=np.fromfunction(lambda y,x:(x+y)%2,(12,12),dtype=int).astype(np.int16)
        ids=(np.arange(144).reshape(12,12)+1).astype(np.int32)
        self.assert_model_safety(scene(checker,ids),
                                 build_candidates(scene(checker,ids)))

    def test_diagonal_and_neck(self):
        game=np.full((20,20),-1,dtype=np.int16)
        np.fill_diagonal(game,6)
        game[8:12,4:16]=6
        a=scene(game)
        self.assert_model_safety(a,build_candidates(a))

    def test_determinism(self):
        a=scene([[4]*24 for _ in range(24)],dots=((4,4),))
        p=build_candidates(a)
        q=build_candidates(a)
        self.assertEqual(p,q)
        self.assertEqual(p["result_sha256"],q["result_sha256"])

    def test_strict_small_budget_and_exhaustion(self):
        a=scene([[2]*30 for _ in range(30)])
        r=build_candidates(a,max_trials=10,max_strokes=1)
        self.assert_model_safety(a,r)
        self.assertLessEqual(r["trials"],10)
        self.assertLessEqual(r["stroke_count"],1)
        self.assertEqual(r["status"],"PARTIAL")

    def test_invalid_alpha_swatches_shape_budget(self):
        a=scene([[1,2]],[[1,1]])
        with self.assertRaises(BlockedS5R2b):
            build_candidates(a)
        a=scene([[1,-1]])
        a["paintable_id"][0,1]=1
        with self.assertRaises(BlockedS5R2b):
            build_candidates(a)
        a=scene([[1]])
        a["protected_original_dot"]=np.zeros((2,2),bool)
        with self.assertRaises(BlockedS5R2b):
            build_candidates(a)
        for v in (0,True,2001):
            with self.assertRaises(BlockedS5R2b):
                build_candidates(scene([[1]]),max_trials=v)


if __name__=="__main__":
    unittest.main()

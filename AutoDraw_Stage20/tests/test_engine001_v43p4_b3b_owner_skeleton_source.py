#!/usr/bin/env python3
"""B3b source-only deterministic owner skeleton regression tests."""
import unittest

import cv2
import numpy as np
from skimage.morphology import skeletonize

from run_engine001_v43p4_b3b_owner_skeleton_source import (
    EXP, SHAPE, STAGES, _adjacent_skeleton, _line_inside,
    direct_owner_skeleton_candidates, trace_owner_skeleton, source_plan,
)


class DirectOwnerSkeletonB3bTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        m=np.zeros(SHAPE,dtype=np.int16)
        # A 1-pixel thin color path which B3's inset rings cannot capture.
        m[17,7:54]=4
        m[18:60,54]=4
        cv2.rectangle(m,(72,15),(133,67),5,-1)
        m[106:172,21:23]=6
        cv2.circle(m,(102,169),31,7,-1)
        cv2.circle(m,(102,169),13,0,-1)
        cls.labels=m

    def test_direct_skeleton_traces_all_edges_without_new_bridges(self):
        mask=np.zeros(SHAPE,bool)
        mask[60,10:52]=True
        mask[61:81,32]=True
        mask[130,80]=True
        sk=skeletonize(mask)
        graph=_adjacent_skeleton(sk)
        graph_edges={(min(p,q),max(p,q))
                     for p,ns in graph.items() for q in ns}
        routes=trace_owner_skeleton(mask)
        traversed=[]
        for chain in routes:
            for a,b in zip(chain,chain[1:]):
                traversed.append((min(a,b),max(a,b)))
        self.assertEqual(set(traversed),graph_edges)
        self.assertEqual(len(traversed),len(set(traversed)))
        self.assertIn([(130,80)],routes)

    def test_closed_loops_not_collapsed_to_a_single_dot(self):
        mask=np.zeros(SHAPE,bool)
        cv2.circle(mask,(65,80),17,1,1)
        routes=trace_owner_skeleton(mask)
        self.assertTrue(routes)
        dist=cv2.distanceTransform((~mask).astype(np.uint8),
                                    cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
        candidates=direct_owner_skeleton_candidates(mask,mask.copy(),dist)
        self.assertTrue(candidates)
        self.assertTrue(any(len(x["points"])>=3 for x in candidates))
        for x in candidates:
            for a,b in zip(x["points"],x["points"][1:]):
                self.assertNotEqual(a,b)
                self.assertTrue(_line_inside(mask,a,b))

    def test_source_owner_centerline_admits_thin_regions_safely(self):
        mask=self.labels==4
        dist=cv2.distanceTransform((~mask).astype(np.uint8),
                                    cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
        cand=direct_owner_skeleton_candidates(mask,mask.copy(),dist)
        self.assertTrue(cand)
        self.assertTrue(all(x["vertices"]<=128 for x in cand))
        for item in cand:
            for a,b in zip(item["points"],item["points"][1:]):
                # Coordinates here are still local (before ROI_X0 shift).
                self.assertTrue(_line_inside(mask,a,b))

    def test_plan_uses_medial_without_same_color_overlap_penalty(self):
        r=source_plan(self.labels)
        self.assertEqual(r["experiment"],EXP)
        self.assertEqual(r["same_owner_overlap_penalty"],0)
        self.assertEqual(r["fixed_stage_order"],list(STAGES))
        self.assertFalse(r["safe_to_execute"])
        self.assertEqual(r["original_A_B0_B1_B2_B3_B3a_paint_retained"],0)
        self.assertEqual(r["frozen_original_V44B_details_required_last"],410)
        self.assertEqual(set(r["per_owner"]),{"4","5","6","7"})
        self.assertLessEqual(r["total_strokes_including_frozen_contours"],3000)
        self.assertLessEqual(r["synthetic_vertices_NOT_CHALK_including_details"],5900)
        self.assertIn("owner_skeleton2",[s["stage"] for s in r["paint_model_only"]])
        self.assertEqual(set(s["colorIndex"] for s in r["paint_model_only"]),
                         {4,5,6,7})
        self.assertTrue(all(s["strokeId"].startswith("p4-b3b-") for s in r["paint_model_only"]))
        self.assertTrue(all(2<=len(s["points"])<=128 for s in r["paint_model_only"]))
        self.assertIsNone(r["exact_game_CHALK"])

    def test_deterministic_and_resource_blocker(self):
        first=source_plan(self.labels)
        self.assertEqual(first,source_plan(self.labels))
        limited=source_plan(self.labels,max_vertices=1792)
        self.assertEqual(limited["status"],"BLOCKED_RESOURCE")
        self.assertTrue(limited["first_resource_blocker"]["no_partial_native_render"])
        with self.assertRaisesRegex(ValueError,"resource caps"):
            source_plan(self.labels,max_vertices=1791)
        with self.assertRaisesRegex(ValueError,"missing frozen original owner"):
            source_plan(np.zeros(SHAPE,np.int16))


if __name__=="__main__":
    unittest.main()

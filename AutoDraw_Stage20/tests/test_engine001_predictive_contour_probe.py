"""E2 synthetic invariants of the frozen predictive contour-first experiment."""
import unittest

import numpy as np

from run_engine001_predictive_contour_probe import (
    MAX_CONTOURS, MIN_FILL_LENGTH, contour_candidates, plan_joint, stroke_length,
)


class PredictiveContourTests(unittest.TestCase):
    @staticmethod
    def silhouette():
        mask = np.zeros((240, 460), dtype=bool)
        mask[30:200, 50:195] = True
        mask[75:160, 95:150] = False
        mask[40:195, 255:415] = True
        mask[90:130, 275:395] = False
        return mask

    def test_deterministic_fixed_joint_plan(self):
        a, info1, _ = plan_joint(self.silhouette())
        b, info2, _ = plan_joint(self.silhouette())
        self.assertEqual(a, b)
        self.assertEqual(info1["candidate_decisions"], info2["candidate_decisions"])

    def test_contour_candidates_are_inside_board_and_long(self):
        c = contour_candidates(self.silhouette())
        self.assertTrue(c)
        for candidate in c:
            self.assertGreaterEqual(candidate["length"], 24)
            self.assertGreaterEqual(len(candidate["points"]), 2)
            for point in candidate["points"]:
                self.assertGreaterEqual(point["x"], 0)
                self.assertLess(point["x"], 460)
                self.assertGreaterEqual(point["y"], 0)
                self.assertLess(point["y"], 240)

    def test_no_new_short_strokes_and_real_overlap_preference(self):
        a, info, data = plan_joint(self.silhouette())
        self.assertTrue(a)
        self.assertLessEqual(info["accepted_long_contours"], MAX_CONTOURS)
        self.assertTrue(all(stroke_length(s) >= MIN_FILL_LENGTH
                            for s in a if len(s["points"]) == 2))
        self.assertTrue(all(d["predicted_new_outside"] == 0
                            for d in info["candidate_decisions"] if d["decision"] == "ACCEPT"))
        self.assertEqual(data["target"].shape, (720, 1380))
        self.assertEqual(data["combined_preview"].shape, data["target"].shape)

    def test_empty_target_fails_closed(self):
        with self.assertRaises(ValueError):
            plan_joint(np.zeros((240, 460), dtype=bool))

    def test_bad_dimensions_or_type_fail_closed(self):
        with self.assertRaises(ValueError):
            plan_joint(np.zeros((240, 459), dtype=bool))
        with self.assertRaises(ValueError):
            plan_joint(np.zeros((240, 460), dtype=np.uint8))


if __name__ == "__main__":
    unittest.main()

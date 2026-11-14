"""Synthetic regression for ENGINE-001 fixed-mask residual diagnostic."""
import unittest
import numpy as np
from engine001_residual_audit import residual, edge, expand_4, tiles


class FixedResidualTests(unittest.TestCase):
    def test_one_pixel_boundary_disagreement(self):
        live = np.zeros((9, 9), dtype=bool)
        live[3:6, 3:6] = True
        model = live.copy()
        model[3, 3] = False
        r = residual(live, model)
        self.assertEqual((r["true_positive"], r["live_only"], r["model_only"]), (8, 1, 0))
        self.assertEqual((r["near_boundary_2px"], r["far_from_boundary_2px"]), (1, 0))
        self.assertEqual(sum(map(sum, r["live_only_tiles_3x3"])), 1)

    def test_missing_interior_island_not_hidden_as_boundary(self):
        live = np.zeros((21, 21), dtype=bool)
        live[1:20, 1:20] = True
        model = live.copy()
        model[7:14, 7:14] = False
        r = residual(live, model)
        self.assertEqual(r["residual_total"], 49)
        self.assertGreater(r["far_from_boundary_2px"], 0)
        self.assertEqual(r["near_boundary_2px"] + r["far_from_boundary_2px"], 49)

    def test_four_connected_border(self):
        mask = np.zeros((5, 5), dtype=bool)
        mask[0, 0] = True
        self.assertTrue(edge(mask)[0, 0])
        dilated = expand_4(mask, 1)
        self.assertEqual(int(dilated.sum()), 3)
        self.assertFalse(dilated[1, 1])

    def test_nondivisible_partition(self):
        self.assertEqual(sum(map(sum, tiles(np.ones((10, 11), dtype=bool)))), 110)

    def test_incompatible_mask_shapes_and_types_rejected(self):
        with self.assertRaises(ValueError):
            residual(np.zeros((3, 3), dtype=np.uint8), np.zeros((3, 3), dtype=bool))
        with self.assertRaises(ValueError):
            residual(np.zeros((3, 3), dtype=bool), np.zeros((3, 2), dtype=bool))


if __name__ == "__main__":
    unittest.main()

"""Pure planning checks for S5-LANE-P1. Native renderer is tested in CI separately."""
import math
import unittest

import numpy as np

import run_engine001_s5_lane_p1_native_spacing as lane


class TestLaneP1(unittest.TestCase):
    def test_frozen_matrix_is_complete_and_unique(self):
        keys = []
        for w in lane.WIDTHS:
            for a in lane.ANGLES:
                for ri in range(3):
                    for pi in range(2):
                        keys.append(lane.case_key(w, a, ri, pi))
        self.assertEqual(len(keys), 180)
        self.assertEqual(len(set(keys)), 180)

    def test_every_width_distance_direction_and_bounds(self):
        for w in lane.WIDTHS:
            for a in lane.ANGLES:
                for ri in range(3):
                    for pi in range(2):
                        first, second, geom = lane.make_plan(w, a, ri, pi)
                        self.assertEqual(first['width'], w)
                        self.assertEqual(second['width'], w)
                        self.assertEqual((first['strokeId'], second['strokeId']),
                                         ('icon-0', 'icon-1'))
                        nx, ny = geom['normal']
                        ax, ay = geom['axial']
                        c1, c2 = geom['center_a'], geom['center_b']
                        self.assertAlmostEqual((c2[0]-c1[0])*nx +
                                               (c2[1]-c1[1])*ny,
                                               w*lane.RATIOS[ri], places=8)
                        self.assertAlmostEqual(ax*nx+ay*ny, 0, places=8)
                        for s in (first, second):
                            self.assertEqual(len(s['points']), 2)
                            for p in s['points']:
                                self.assertTrue(0 < p['x'] < 460)
                                self.assertTrue(0 < p['y'] < 240)
                            dx = s['points'][1]['x'] - s['points'][0]['x']
                            dy = s['points'][1]['y'] - s['points'][0]['y']
                            self.assertAlmostEqual(math.hypot(dx,dy),34,places=8)

    def test_wrong_parameter_fails_closed(self):
        for args in ((0,0,0,0),(11,0,0,0),(1,30,0,0),
                     (1,0,3,0),(1,0,0,2)):
            with self.assertRaises(ValueError):
                lane.make_plan(*args)

    def test_metric_uses_native_rgba_alpha_and_both_thresholds(self):
        _,_,g = lane.make_plan(5,0,1,0)
        full = np.zeros(lane.SHAPE,np.uint8)
        full[:,:,3] = 255
        both = lane.gap_metrics(full,g)
        self.assertTrue(both['alpha24']['gap_free'])
        self.assertTrue(both['alpha128']['gap_free'])
        self.assertEqual(both['alpha128']['hole_pixels'],0)
        full[:,:,3] = 0
        zero = lane.gap_metrics(full,g)
        self.assertFalse(zero['alpha24']['gap_free'])
        self.assertFalse(zero['alpha128']['gap_free'])
        self.assertGreater(zero['alpha24']['hole_pixels'],0)

    def test_wrong_native_resolution_rejected(self):
        _,_,g = lane.make_plan(5,0,1,0)
        with self.assertRaises(ValueError):
            lane.gap_metrics(np.zeros((240,460,4),np.uint8),g)


if __name__ == '__main__':
    unittest.main()

"""Frozen normal multi-turn native E0 case generator and ROI math unit tests."""
import unittest
import numpy as np
import run_engine001_s5_lane_p2_native_turns as p2


class NativeTurnGeometryTests(unittest.TestCase):
    def test_exact_120_unique_frozen_cases(self):
        keys=[p2.case_key(w,a,pi,shape)
              for w in p2.WIDTHS for a in p2.ANGLES
              for pi in range(2) for shape in p2.SHAPES]
        self.assertEqual(len(keys),120)
        self.assertEqual(len(set(keys)),120)

    def test_each_polyline_equals_segmentation_geometry(self):
        for w in p2.WIDTHS:
            for angle in p2.ANGLES:
                for phase in range(2):
                    for shape in p2.SHAPES:
                        connected,separated,points=p2.make_strokes(w,angle,phase,shape)
                        self.assertEqual(len(connected),1)
                        self.assertEqual(len(points),3 if shape=="turn3" else 5)
                        self.assertEqual(len(separated),len(points)-1)
                        self.assertEqual(connected[0]["points"],points)
                        for i,segment in enumerate(separated):
                            self.assertEqual(segment["points"],points[i:i+2])
                            self.assertEqual(segment["width"],w)
                            self.assertEqual(segment["colorRgb"],connected[0]["colorRgb"])
                        for point in points:
                            self.assertGreater(point["x"],15)
                            self.assertLess(point["x"],445)
                            self.assertGreater(point["y"],15)
                            self.assertLess(point["y"],225)

    def test_intersection_angles_and_nonzero_segments(self):
        for angle in p2.ANGLES:
            for shape in p2.SHAPES:
                pts=p2.make_points(10,angle,0,shape)
                self.assertEqual(len(pts),3 if shape=="turn3" else 5)
                for a,b in zip(pts,pts[1:]):
                    length=np.hypot(a["x"]-b["x"],a["y"]-b["y"])
                    self.assertAlmostEqual(length,24 if shape=="turn3" else 20,places=7)

    def test_zero_and_full_alpha_metrics(self):
        _,_,points=p2.make_strokes(6,90,0,"turn3")
        empty=np.zeros(p2.SHAPE,np.uint8)
        zero=p2.metrics(empty,empty,points,6)
        self.assertEqual(zero["rgba_different_backing_pixels"],0)
        self.assertEqual(zero["alpha24"]["poly_ink_pixels"],0)
        self.assertEqual(zero["alpha128"]["xor_ink_pixels"],0)
        whole=empty.copy()
        whole[:,:,3]=255
        nonzero=p2.metrics(whole,whole,points,6)
        self.assertGreater(nonzero["alpha24"]["poly_ink_pixels"],0)
        self.assertEqual(nonzero["alpha24"]["xor_ink_pixels"],0)
        self.assertGreater(nonzero["alpha24"]["poly_outside_overshoot3px"],0)

    def test_alpha_threshold_has_real_effect(self):
        _,_,points=p2.make_strokes(6,90,0,"turn3")
        faint=np.zeros(p2.SHAPE,np.uint8)
        faint[:,:,3]=42
        metrics=p2.metrics(faint,np.zeros_like(faint),points,6)
        self.assertGreater(metrics["alpha24"]["xor_ink_pixels"],0)
        self.assertEqual(metrics["alpha128"]["xor_ink_pixels"],0)

    def test_unregistered_plan_and_wrong_backing_fail_closed(self):
        for args in ((0,90,0,"turn3"),(11,90,0,"turn3"),
                     (4,15,0,"turn3"),(4,90,-1,"turn3"),
                     (4,90,2,"turn3"),(4,90,0,"other")):
            with self.assertRaises(ValueError):
                p2.make_strokes(*args)
        _,_,points=p2.make_strokes(4,90,0,"turn3")
        with self.assertRaises(ValueError):
            p2.metrics(np.zeros((240,460,4),np.uint8),
                       np.zeros(p2.SHAPE,np.uint8),points,4)


if __name__=="__main__":
    unittest.main()

#!/usr/bin/env python3
"""B1-R-P4A2 width1..10 original-sourced proposal and native metric contracts."""
import ast
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

import run_engine001_b1r_p4a2_native_brush_widths as p


def maps():
    a = np.full((240, 150), 6, dtype=np.uint8)
    a[60:140, 35:120] = 115
    a[155:230, 70:140] = 127
    b = a.copy()
    b[60, 35:120] = 6
    b[155, 70:140] = 6
    swatches = np.asarray([6, 115, 127] + list(range(10, 39)), dtype=np.int16)
    engine = np.zeros((128, 3), dtype=np.uint8)
    engine[6] = (255, 255, 255)
    engine[115] = (100, 20, 40)
    engine[127] = (40, 50, 60)
    return a, b, swatches, engine


class P4A2Contracts(unittest.TestCase):
    def test_01_all_integer_widths_no_skip(self):
        self.assertEqual(p.WIDTHS, tuple(range(1, 11)))
        self.assertEqual(len(p.WIDTHS), 10)
        self.assertEqual(p.EXPERIMENT, "ENGINE001_B1R_P4A2_NATIVE_BRUSH_WIDTHS_1_TO_10_V1")

    def test_02_same_two_paths_supported_in_E_and_F(self):
        e, f, s, engine = maps()
        paths = p.choose_two_source_paths(e, f, s, engine)
        self.assertEqual(set(paths), {"HORIZONTAL", "DIAGONAL"})
        self.assertNotEqual(paths["HORIZONTAL"]["engine128_index"],
                            paths["DIAGONAL"]["engine128_index"])
        for name, (dx, dy) in p.DIRECTIONS.items():
            v = paths[name]
            y, x = v["source_anchor_yx"]
            self.assertEqual(v["two_board_logical_points_xy"][0], [x+155, y])
            self.assertEqual(v["two_board_logical_points_xy"][1], [x+dx+155,y+dy])
            self.assertTrue((e[y,x]==f[y,x]==v["engine128_index"]))

    def test_03_source_index_untouched(self):
        e, f, s, engine = maps()
        freeze = (e.copy(), f.copy())
        p.choose_two_source_paths(e, f, s, engine)
        self.assertTrue(np.array_equal(e,freeze[0]))
        self.assertTrue(np.array_equal(f,freeze[1]))

    def test_04_all_widths_have_two_two_point_actual_color_strokes(self):
        e, f, s, engine = maps()
        paths = p.choose_two_source_paths(e, f, s, engine)
        for width in p.WIDTHS:
            strokes = p.make_native_strokes(paths, width)
            self.assertEqual(len(strokes), 2)
            self.assertEqual({st["width"] for st in strokes}, {width})
            self.assertEqual(sum(len(st["points"]) for st in strokes), 4)
            self.assertEqual(len({st["colorRgb"] for st in strokes}), 2)

    def test_05_reject_width_0_11_float(self):
        e, f, s, engine = maps()
        paths = p.choose_two_source_paths(e, f, s, engine)
        for invalid in (0, 11, 1.5, True, "4"):
            with self.assertRaisesRegex(ValueError, "WIDTH_OR_ORIENTATION"):
                p.make_native_strokes(paths, invalid)

    def test_06_reject_invalid_map_palette(self):
        e, f, s, engine = maps()
        for args in ((e[:-1],f,s,engine),(e,f,s[:-1],engine),
                     (e,f,s,engine[:127]),(e.astype(np.int16),f,s,engine)):
            with self.assertRaisesRegex(ValueError,"SOURCE_MAP_OR_PALETTE"):
                p.choose_two_source_paths(*args)

    def test_07_no_distinct_color_region_fail_closed(self):
        e, f, s, engine = maps()
        e[e==127] = 6
        f[f==127] = 6
        with self.assertRaisesRegex(ValueError, "NO_DISTINCT_SOURCE"):
            p.choose_two_source_paths(e, f, s, engine)

    def test_08_owner_backing_is_true_board_offset_and_scale3(self):
        e, f, s, engine = maps()
        target = p._owner_backing(e, 115)
        self.assertEqual(target.shape,(720,1380))
        self.assertTrue(target[90*3, (155+50)*3])
        self.assertFalse(target[90*3, 50*3])
        self.assertFalse(target[90*3, (155+125)*3])

    def test_09_native_empty_vs_nonempty(self):
        target=np.zeros((720,1380),bool)
        target[200:215,500:515]=True
        d=cv2.distanceTransform((~target).astype(np.uint8),
                                cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
        rgba=np.zeros((720,1380,4),np.uint8)
        empty=p.geometry_metrics(rgba,target,d)
        self.assertEqual(empty["24"]["native_ink_backing_pixels"],0)
        self.assertFalse(empty["24"]["native_alpha_nonzero"])
        rgba[206,507,3]=255
        one=p.geometry_metrics(rgba,target,d)
        self.assertTrue(one["24"]["native_alpha_nonzero"])
        self.assertEqual(one["24"]["native_nonowner_beyond3logicalpx"],0)

    def test_10_native_far_leakage_count(self):
        target=np.zeros((720,1380),bool)
        target[200:215,500:515]=True
        d=cv2.distanceTransform((~target).astype(np.uint8),
                                cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
        rgba=np.zeros((720,1380,4),np.uint8)
        rgba[206,507,3]=255
        rgba[206,530,3]=255
        scored=p.geometry_metrics(rgba,target,d)
        self.assertEqual(scored["24"]["native_nonowner_beyond3logicalpx"],1)
        self.assertEqual(scored["128"]["native_nonowner_beyond3logicalpx"],1)

    def test_11_shape_and_dtype_fail_closed(self):
        target=np.zeros((720,1380),bool)
        dist=np.zeros(target.shape,np.float32)
        for source in (np.zeros((240,150,4),np.uint8),
                       np.zeros((720,1380,4),np.float32)):
            with self.assertRaisesRegex(ValueError,"NATIVE_OR_TARGET_SHAPE"):
                p.geometry_metrics(source,target,dist)

    def test_12_no_legacy_candidate_import(self):
        tree=ast.parse(Path(p.__file__).read_text(encoding="utf8"))
        modules=[node.module for node in ast.walk(tree)
                 if isinstance(node,ast.ImportFrom) and node.module]
        direct=[name.name for node in ast.walk(tree)
                if isinstance(node,ast.Import) for name in node.names]
        self.assertFalse(any("g32" in x.lower() or "v44" in x.lower()
                             for x in modules+direct))
        self.assertIn("run_engine001_b1r_p3d_source_edge_mask_ablation",direct)
        self.assertIn("run_engine001_complex_holdout_v5",modules)

    def test_13_source_geometry_deterministic(self):
        e,f,s,engine=maps()
        self.assertEqual(p.choose_two_source_paths(e,f,s,engine),
                         p.choose_two_source_paths(e,f,s,engine))

    def test_14_existing_output_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "OUTPUT_EXISTS"):
                p.run(Path(d),Path(d)/"bad.png",Path(d)/"bad.js",
                      Path(d)/"bad.renderer",Path(d))

if __name__=="__main__":
    unittest.main()

#!/usr/bin/env python3
"""P4B3 synthetic pre-registered same-budget phase sensitivity E2 contracts."""
import ast
import tempfile
import unittest
from pathlib import Path

import numpy as np

import run_engine001_b1r_p4b3_native_grid_phase as p


def fixture():
    comp = np.zeros((240,150),dtype=bool)
    comp[50:150,40:120] = True
    base = [{
        "strokeId":f"icon-{i}",
        "width":4,
        "colorIndex":115,
        "colorRgb":0x5a4941,
        "points":[{"x":215.0,"y":90.0},{"x":225.0,"y":90.0}],
    } for i in range(177)]
    correct=[{
        "strokeId":f"icon-{177+i}",
        "width":2,
        "colorIndex":115,
        "colorRgb":0x5a4941,
        "points":[{"x":220.0,"y":90.0},{"x":222.0,"y":90.0}],
    } for i in range(73)]
    return comp,base,correct


class P4B3Contracts(unittest.TestCase):
    def test_01_id_all_fixed_phases(self):
        self.assertEqual(p.EXPERIMENT,"ENGINE001_B1R_P4B3_NATIVE_GRID_PHASE_V1")
        self.assertEqual(p.PHASES,{
            "S_X25":(0.25,0.0),
            "S_Y25":(0.0,0.25),
            "S_XY25":(0.25,0.25),
        })

    def test_02_frozen_resource_and_quality(self):
        self.assertEqual(p.FIXED_STROKES,250)
        self.assertEqual(p.FIXED_VERTICES,500)
        self.assertEqual(p.NATIVE_COVERAGE_GATE,.99)
        self.assertEqual(p.FAR_LEAKAGE_LOGICAL,3.0)

    def test_03_shift_all_correctives_only(self):
        comp,base,corrections=fixture()
        result=p.shift_correctives(base,corrections,comp,"S_XY25")
        self.assertEqual(len(result),250)
        self.assertEqual(result[:177],base)
        self.assertAlmostEqual(result[177]["points"][0]["x"],220.25)
        self.assertAlmostEqual(result[177]["points"][0]["y"],90.25)

    def test_04_unshifted_original_immutable(self):
        comp,base,corr=fixture()
        frozen=[dict(s) for s in corr]
        p.shift_correctives(base,corr,comp,"S_X25")
        self.assertEqual(corr,frozen)
        self.assertEqual(base[0]["points"][0]["x"],215.0)

    def test_05_same_vertices_and_no_radius_change(self):
        comp,base,corr=fixture()
        for mode in p.PHASES:
            result=p.shift_correctives(base,corr,comp,mode)
            self.assertEqual(sum(len(s["points"]) for s in result),500)
            self.assertEqual(len(result),250)
            self.assertEqual([s["width"] for s in result[177:]], [2]*73)
            self.assertEqual([s["strokeId"] for s in result],
                             [f"icon-{i}" for i in range(250)])

    def test_06_phase_direction_x_only(self):
        comp,base,corr=fixture()
        r=p.shift_correctives(base,corr,comp,"S_X25")
        self.assertEqual(r[177]["points"][0],{"x":220.25,"y":90.0})

    def test_07_phase_direction_y_only(self):
        comp,base,corr=fixture()
        r=p.shift_correctives(base,corr,comp,"S_Y25")
        self.assertEqual(r[177]["points"][0],{"x":220.0,"y":90.25})

    def test_08_unsupported_phase_rejected(self):
        comp,base,corr=fixture()
        with self.assertRaisesRegex(ValueError,"INVARIANT_INPUT"):
            p.shift_correctives(base,corr,comp,"SHIFT_100")

    def test_09_wrong_budget_rejected(self):
        comp,base,corr=fixture()
        with self.assertRaisesRegex(ValueError,"INVARIANT_INPUT"):
            p.shift_correctives(base[:-1],corr,comp,"S_X25")

    def test_10_wrong_owner_color_rejected(self):
        comp,base,corr=fixture()
        bad=[dict(x) for x in corr]
        bad[0]["colorIndex"]=70
        with self.assertRaisesRegex(ValueError,"CORRECTION_PROVENANCE"):
            p.shift_correctives(base,bad,comp,"S_X25")

    def test_11_board_oob_guard(self):
        comp,base,corr=fixture()
        bad=[dict(x) for x in corr]
        bad[0]={**bad[0],"points":[{"x":304.99,"y":90.0},
                                     {"x":305.0,"y":90.0}]}
        with self.assertRaisesRegex(ValueError,"PHASE_SOURCE_OWNER_OR_BOARD"):
            p.shift_correctives(base,bad,comp,"S_X25")

    def test_12_source_original_owner_guard(self):
        comp,base,corr=fixture()
        comp[90,65:69] = False
        with self.assertRaisesRegex(ValueError,"PHASE_SOURCE_OWNER_OR_BOARD"):
            p.shift_correctives(base,corr,comp,"S_XY25")

    def test_13_native_phase_residual_counting(self):
        comp,base,corr=fixture()
        rgba=np.zeros((720,1380,4),dtype=np.uint8)
        result=p.residual_phase(rgba,comp)
        self.assertEqual(result["native_missing_backing_pixels"],int(comp.sum())*9)
        self.assertEqual(result["x_mod3"],[int(comp.sum())*3]*3)
        self.assertEqual(result["y_mod3"],[int(comp.sum())*3]*3)

    def test_14_native_shape_fail_closed(self):
        comp,base,corr=fixture()
        rgba=np.zeros((720,1380,4),np.uint8)
        with self.assertRaisesRegex(ValueError,"INVALID_NATIVE_PHASE_DATA"):
            p.residual_phase(rgba[:-1],comp)
        with self.assertRaisesRegex(ValueError,"INVALID_NATIVE_PHASE_DATA"):
            p.residual_phase(rgba,comp.astype(np.uint8))

    def test_15_deterministic_source_shift(self):
        comp,base,corr=fixture()
        a=p.shift_correctives(base,corr,comp,"S_XY25")
        b=p.shift_correctives(base,corr,comp,"S_XY25")
        self.assertEqual(a,b)

    def test_16_no_legacy_generating_imports(self):
        tree=ast.parse(Path(p.__file__).read_text(encoding="utf8"))
        modules=[
            n.name for x in ast.walk(tree) if isinstance(x,ast.Import)
            for n in x.names
        ]+[
            x.module for x in ast.walk(tree)
            if isinstance(x,ast.ImportFrom) and x.module
        ]
        self.assertFalse(any("g32" in n.lower() or "v44" in n.lower()
                             or "p4c1" in n.lower() for n in modules))
        self.assertIn("run_engine001_b1r_p4b2_native_edge_repair",modules)

    def test_17_output_overwrite_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"EXISTING_OUTPUT"):
                p.run(Path(d),Path(d)/"bad.png",Path(d)/"bad.js",
                      Path(d)/"bad.renderer",Path(d))

if __name__=="__main__":
    unittest.main()

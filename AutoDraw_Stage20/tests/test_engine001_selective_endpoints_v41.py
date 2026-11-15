#!/usr/bin/env python3
"""V41 selector unit tests: native input alpha for choices, no simulated brush."""
import unittest

import numpy as np

from run_engine001_selective_endpoints_native_v41 import selected_plan


def fixture():
    strokes = [{
        "layer": "paint",
        "stroke": {
            "strokeId": f"icon-{i}", "width": 2, "colorIndex": 5,
            "colorRgb": 0xAA7744,
            "points": [{"x": 200.0, "y": 5.0},
                       {"x": 201.0, "y": 5.0}],
        }
    } for i in range(1945)]
    for i in range(410):
        count = 5 if i < 152 else 4  # 152*5+258*4=1792 vertices
        strokes.append({
            "layer": "detail",
            "stroke": {
                "strokeId": f"detail-v18-B-{i}",
                "width": 1, "colorIndex": 100, "colorRgb": 0x31262B,
                "points": [{"x": 155.0 + j*0.25, "y": 5.0}
                           for j in range(count)],
            }
        })
    return {"paint_strokes": 1945, "detail_strokes": 410,
            "synthetic_vertices_NOT_CHALK": 5682, "strokes": strokes}


class V41SelectionTests(unittest.TestCase):
    def setUp(self):
        self.base = fixture()
        self.labels = np.full((720, 1380), -1, dtype=np.int16)
        self.native = {c: np.full((720, 1380), 255, dtype=np.uint8)
                       for c in (4, 5, 6, 7)}
        # For 0.25 extension, left probe x=198.75 and right probe=202.25.
        self.labels[5*3, 199*3] = 5
        self.labels[5*3, 202*3] = 5
        self.native[5][5*3, round(198.75*3)] = 0
        self.native[5][5*3, round(202.25*3)] = 0

    def test_select_only_native_unpainted_own_class_and_keep_all_contours(self):
        changed, journal = selected_plan(
            self.base, self.labels, self.native, 0.25)
        self.assertEqual(len(journal), 3890)
        self.assertEqual(sum(d["eligible"] for d in journal), 3890)
        self.assertEqual(changed["strokes"][0]["stroke"]["points"][0]["x"], 199.75)
        self.assertEqual(changed["strokes"][0]["stroke"]["points"][1]["x"], 201.25)
        self.assertEqual(changed["strokes"][1945:], self.base["strokes"][1945:])
        self.assertEqual(changed["synthetic_vertices_NOT_CHALK"], 5682)
        self.assertEqual(self.base["strokes"][0]["stroke"]["points"][0]["x"], 200.0)

    def test_wrong_class_not_selected_even_when_native_alpha_empty(self):
        self.labels[5*3, 199*3] = 6
        changed, journal = selected_plan(self.base, self.labels, self.native, 0.25)
        self.assertFalse(journal[0]["eligible"])
        self.assertEqual(changed["strokes"][0]["stroke"]["points"][0]["x"], 200.0)

    def test_covered_source_target_not_selected(self):
        self.native[5][5*3, round(202.25*3)] = 24
        changed, journal = selected_plan(self.base, self.labels, self.native, 0.25)
        self.assertFalse(journal[1]["eligible"])
        self.assertEqual(changed["strokes"][0]["stroke"]["points"][1]["x"], 201.0)

    def test_a_control_never_changes_geometry(self):
        same, _ = selected_plan(self.base, self.labels, self.native, 0)
        self.assertEqual(self.base, same)

    def test_bad_native_source_or_amplitude_fails(self):
        with self.assertRaisesRegex(ValueError, "unregistered"):
            selected_plan(self.base, self.labels, self.native, 0.4)
        with self.assertRaisesRegex(ValueError, "native shape"):
            selected_plan(self.base, np.zeros((2, 2), dtype=np.int16),
                          self.native, 0.25)
        broken = dict(self.native)
        broken[5] = np.zeros((1, 1), dtype=np.uint8)
        with self.assertRaisesRegex(ValueError, "source alpha invalid"):
            selected_plan(self.base, self.labels, broken, 0.25)


if __name__ == "__main__":
    unittest.main()

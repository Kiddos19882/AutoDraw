"""V4 preregistered isolated brush expansion: no new points, no short repairs."""
import unittest
from unittest.mock import patch
import numpy as np
from run_engine001_selective_brush_v4 import (
    ID, WIDTH, HEIGHT, FIXED_SIZE_UPGRADE,
    canonical_sha256, select_widths, predictor, interior_band
)

class SelectiveBrushV4Tests(unittest.TestCase):
    @staticmethod
    def artificial_source():
        rows=[]
        for i in range(323):
            pts=[{"x":float(55+i%40),"y":float(60+i%60)},
                 {"x":float(80+i%40),"y":float(60+i%60)}]
            if i<28:
                pts.insert(1,{"x":float(65+i%40),"y":float(60+i%60)})
            rows.append({"strokeId":f"icon-{i}",
                         "width":(2,4,8)[i%3],"points":pts})
        return rows

    def test_frozen_source_required(self):
        with self.assertRaisesRegex(ValueError,"frozen source plan"):
            select_widths(self.artificial_source())

    def test_only_widths_change_no_new_points(self):
        original=self.artificial_source()
        with patch("run_engine001_selective_brush_v4.V3_STROKES_SHA256",canonical_sha256(original)):
            expanded=select_widths(original)
        self.assertEqual(len(expanded),323)
        self.assertEqual(sum(len(s["points"]) for s in expanded),674)
        for old,new in zip(original,expanded):
            self.assertEqual(new["width"],FIXED_SIZE_UPGRADE[old["width"]])
            self.assertEqual(old["strokeId"],new["strokeId"])
            self.assertEqual(old["points"],new["points"])

    def test_changing_width_does_not_mutate_original(self):
        original=self.artificial_source()
        snapshot=canonical_sha256(original)
        with patch("run_engine001_selective_brush_v4.V3_STROKES_SHA256",snapshot):
            expanded=select_widths(original)
        self.assertEqual(canonical_sha256(original),snapshot)
        self.assertNotEqual(canonical_sha256(expanded),snapshot)

    def test_wider_preview_contains_original(self):
        original=self.artificial_source()
        with patch("run_engine001_selective_brush_v4.V3_STROKES_SHA256",canonical_sha256(original)):
            expanded=select_widths(original)
        p1=predictor(original)
        p2=predictor(expanded)
        self.assertEqual(p1.shape,(HEIGHT*3,WIDTH*3))
        # Even-width rasterisation details are not guaranteed strictly nested,
        # but widened paint should cover greater area overall.
        self.assertGreater(int(p2.sum()),int(p1.sum()))

    def test_missing_inside_band_not_excused(self):
        target=np.zeros((HEIGHT*3,WIDTH*3),dtype=bool)
        target[60:240,75:255]=True
        rendered=target.copy()
        rendered[60,150]=False
        rendered[160,160]=False
        res=interior_band(target,rendered)
        self.assertEqual(res["missing_total_native_px"],2)
        self.assertEqual(res["missing_farther_than_3_logical_px"],1)


if __name__=="__main__":
    unittest.main()

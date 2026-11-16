"""V44-P1 deterministic tests. Run: python -m unittest tests/test_engine001_adaptive_color_outline_v44.py"""
import unittest
import hashlib
import json
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image

from engine001_adaptive_color_outline_v44 import (
    DARK, OFFSET, MIN_CONTRAST, contrast, contrast_guard,
    side_backgrounds, adaptive_recolor,
)


class AdaptiveColorOutlineV44Tests(unittest.TestCase):
    def test_bright_background_darkens_light_source(self):
        picked, decision = contrast_guard([230, 210, 150], [[240, 220, 150], [240, 220, 150]])
        self.assertIn(decision, ("darkened", "unresolved"))
        self.assertEqual(len(picked), 3)
        if decision == "darkened":
            self.assertGreaterEqual(contrast(picked, [240, 220, 150]), MIN_CONTRAST)

    def test_good_source_color_is_preserved(self):
        color = [38, 26, 40]
        picked, decision = contrast_guard(color, [[230, 200, 170], [200, 180, 150]])
        self.assertEqual(picked, color)
        self.assertEqual(decision, "source")

    def test_missing_sides_fails_closed(self):
        self.assertEqual(contrast_guard([220, 220, 220], None),
                         (list(DARK), "missing_sides"))

    def test_median_side_sampling_respects_roi(self):
        pixels = np.empty((240, 150, 3), dtype=np.uint8)
        pixels[:] = [210, 180, 140]
        img = Image.fromarray(pixels, "RGB")
        sides = side_backgrounds(img, [{"x": 170, "y": 50}, {"x": 175, "y": 50}])
        self.assertEqual(sides, [[210, 180, 140], [210, 180, 140]])
        self.assertIsNone(side_backgrounds(img, [{"x": 155, "y": 0}]))

    def test_adaptive_rgb_does_not_mutate_stroke_geometry(self):
        pixels = np.empty((240, 150, 3), dtype=np.uint8)
        pixels[:] = [200, 190, 170]
        img = Image.fromarray(pixels, "RGB")
        fill = {"layer": "paint", "stroke": {"strokeId": "paint", "width": 2, "colorRgb": 12}}
        detail = {"layer": "detail", "stroke": {
            "strokeId": "detail-v18-B-test", "width": 1, "colorRgb": 0x31262B,
            "points": [{"x": 180, "y": 80}, {"x": 200, "y": 80}]}}
        # Each source contour is a distinct stroke object, as in frozen V35-B.
        # Reusing [detail] * 410 aliases one dictionary: recoloring the first
        # changes the next and falsely triggers the immutable-RGB guard.
        details = []
        for i in range(410):
            route = {"layer": "detail", "stroke": {
                **detail["stroke"], "strokeId": f"detail-v18-B-{i}",
                "points": [dict(p) for p in detail["stroke"]["points"]]}}
            details.append(route)
        base = {"strokes": [fill] * 1945 + details,
                "synthetic_vertices_NOT_CHALK": 5682}
        self.assertEqual(len({id(e) for e in details}), 410)
        self.assertEqual(len({e["stroke"]["strokeId"] for e in details}), 410)
        for variant in ("A", "B", "C"):
            changed, report = adaptive_recolor(base, img, variant)
            self.assertEqual(len(report), 410)
            self.assertEqual(changed["strokes"][:1945], base["strokes"][:1945])
            for a, b in zip(base["strokes"][1945:], changed["strokes"][1945:]):
                self.assertEqual(a["stroke"]["points"], b["stroke"]["points"])
                self.assertEqual(a["stroke"]["strokeId"], b["stroke"]["strokeId"])
                self.assertEqual(a["stroke"]["width"], b["stroke"]["width"])
        self.assertEqual(base["strokes"][1945]["stroke"]["colorRgb"], 0x31262B)


    def test_archive_manifest_integrity_and_frozen_identity(self):
        from run_engine001_adaptive_color_outline_native_v44 import validate_v37p2_archive
        from run_engine001_native_warm_color_v34 import SOURCE_SHA
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            native = root / "C" / "V37P2-C-composite.png"
            native.parent.mkdir()
            native.write_bytes(b"fixture")
            digest = hashlib.sha256(native.read_bytes()).hexdigest()
            report = {
                "experiment": "ENGINE001_LOCAL_FILL_COLOR_V37_P2",
                "original_source_SHA256": SOURCE_SHA,
                "V35_B_control_RGBA_pixel_exact": True,
                "same_native_alpha_all_variants": True,
                "metrics": {"C": {
                    "complete_detail_strokes": 410,
                    "synthetic_accepted_vertices_NOT_CHALK": 5682,
                    "changed_fill_strokes": 166}},
                "report_linked_SHA256": {"C/V37P2-C-composite.png": digest},
            }
            (root / "report.json").write_text(json.dumps(report), encoding="utf-8")
            self.assertEqual(validate_v37p2_archive(root), native)
            native.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "altered native"):
                validate_v37p2_archive(root)
            native.write_bytes(b"fixture")
            report["metrics"]["C"]["complete_detail_strokes"] = 409
            (root / "report.json").write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "identity drift"):
                validate_v37p2_archive(root)

    def test_source_contrast_diagnostic_is_not_native_evidence(self):
        from run_engine001_adaptive_color_outline_native_v44 import (
            source_side_contrast_diagnostic,
        )
        rows = [{"assigned_RGB": list(DARK),
                 "sides_RGB": [[235, 220, 200], [235, 220, 200]]}
                for _ in range(409)]
        rows.append({"assigned_RGB": list(DARK), "sides_RGB": None})
        summary = source_side_contrast_diagnostic(rows)
        self.assertEqual(summary["type"], "SOURCE_RGB_ONLY_NOT_NATIVE_PAINT")
        self.assertEqual(summary["measurable_contours"], 409)
        self.assertEqual(summary["missing_side_contours"], 1)
        self.assertEqual(summary["passing_contours"] + summary["failing_contours"], 409)
        with self.assertRaisesRegex(ValueError, "missing outlines"):
            source_side_contrast_diagnostic(rows[:-1])

    def test_invalid_roi_rejected(self):
        with self.assertRaisesRegex(ValueError, "ROI"):
            side_backgrounds(Image.new("RGB", (10, 10)),
                             [{"x": 170, "y": 50}, {"x": 175, "y": 50}])


if __name__ == "__main__":
    unittest.main()

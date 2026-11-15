#!/usr/bin/env python3
"""V40P2 model-only endpoint contract; native brush validated separately."""
import unittest
from run_engine001_endpoint_extension_native_v40p2 import extend


def plan():
    p=[]
    for i in range(1945):
        p.append({"layer":"paint","stroke":{
            "strokeId":f"icon-{i}","width":2,"colorRgb":0x884422,
            "colorIndex":5,"points":[{"x":155.0,"y":5.0},
                                     {"x":155.25,"y":5.0}]}})
    for i in range(410):
        p.append({"layer":"detail","stroke":{
            "strokeId":f"detail-v18-B-{i}","width":1,"colorRgb":0x31262B,
            "colorIndex":100,"points":[{"x":155.0,"y":5.0},
                                       {"x":156.0,"y":5.0}]}})
    return {"paint_strokes":1945,"detail_strokes":410,
            "synthetic_vertices_NOT_CHALK":5682,"strokes":p}


class V40EndpointTests(unittest.TestCase):
    def test_a_unchanged_and_b_c_preserve_all_dark_contours(self):
        src=plan()
        a,change_a=extend(src,0)
        b,change_b=extend(src,0.25)
        c,change_c=extend(src,0.5)
        self.assertEqual(change_a,0)
        self.assertEqual(change_b,1945)
        self.assertEqual(change_c,1945)
        self.assertEqual(a,src)
        for result in (b,c):
            self.assertEqual(result["strokes"][1945:],src["strokes"][1945:])
            self.assertEqual(result["synthetic_vertices_NOT_CHALK"],5682)
            self.assertEqual(result["strokes"][0]["stroke"]["points"][0]["x"],155.0)
            self.assertEqual(result["strokes"][0]["stroke"]["points"][0]["y"],5.0)
        self.assertEqual(b["strokes"][0]["stroke"]["points"][1]["x"],155.5)
        self.assertEqual(c["strokes"][0]["stroke"]["points"][1]["x"],155.75)
        self.assertEqual(src["strokes"][0]["stroke"]["points"][1]["x"],155.25)

    def test_clamp_to_artwork_roi_and_do_not_shift_y(self):
        src=plan()
        src["strokes"][0]["stroke"]["points"]=[
            {"x":304.5,"y":22.0},{"x":304.75,"y":22.0}]
        changed,_=extend(src,0.5)
        pts=changed["strokes"][0]["stroke"]["points"]
        self.assertEqual([p["x"] for p in pts],[304.0,304.75])
        self.assertEqual([p["y"] for p in pts],[22.0,22.0])

    def test_reject_nonhorizontal_and_invalid_source(self):
        src=plan()
        src["strokes"][0]["stroke"]["points"][1]["y"]=5.5
        with self.assertRaisesRegex(ValueError,"non-horizontal"):
            extend(src,0.25)
        src=plan()
        src["strokes"][0]["stroke"]["points"][0]["x"]=154.9
        with self.assertRaisesRegex(ValueError,"non-horizontal"):
            extend(src,0.25)

    def test_reject_outside_preregistered_amplitude(self):
        with self.assertRaisesRegex(ValueError,"unregistered"):
            extend(plan(),1.0)

    def test_reject_contour_resource_drift(self):
        src=plan()
        src["synthetic_vertices_NOT_CHALK"]=5683
        with self.assertRaisesRegex(ValueError,"plan count drift"):
            extend(src,0.25)


if __name__=="__main__":
    unittest.main()

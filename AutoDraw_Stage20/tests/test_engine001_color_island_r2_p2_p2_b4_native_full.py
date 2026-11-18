#!/usr/bin/env python3
"""B4 source-only frozen detail geometry / game32 palette / resource unit tests."""
import unittest
import numpy as np
from run_engine001_color_island_r2_p2_p2_b4_native_full import (
    nearest_original_detail_palette, validate_detail, assembled,to_int,parse_rgb)

def details_fixture():
    d=[{"strokeId":f"detail-v18-B-{i}","colorIndex":100,"colorRgb":i%395,
        "width":1,"points":[{"x":200.25,"y":1.5},{"x":200.75,"y":1.5}]}
       for i in range(410)]
    # 820 base + 820 added + 152 added =1792 original synthetic vertices.
    for i in range(410):
        d[i]["points"].extend(({"x":201.25,"y":2.25},{"x":201.5,"y":2.5}))
    for i in range(152):
        d[i]["points"].append({"x":201.75,"y":2.75})
    return d
def paint_fixture():
    p=[{"strokeId":f"icon-{i}","colorIndex":31,"colorRgb":0x1B1B1B,
        "width":2,"points":[{"x":180,"y":20},{"x":181,"y":20}]}
       for i in range(1133)]
    for i in range(1133):p[i]["points"].append({"x":182,"y":20})
    for i in range(86):p[i]["points"].append({"x":183,"y":20})
    assert sum(len(x["points"]) for x in p)==3485
    return p

class B4OriginalDetailTests(unittest.TestCase):
    def test_410_frozen_details_id_and_1792_vertices(self):
        d=details_fixture()
        self.assertEqual(len(d),410)
        self.assertEqual(sum(len(x["points"]) for x in d),1792)
        validate_detail(d)
    def test_410_original_detail_ids_or_geometry_cannot_drift(self):
        d=details_fixture();d[0]["strokeId"]="detail-v18-B-4"
        with self.assertRaisesRegex(ValueError,"BLOCKED_B4_CONTOUR_ID_OR_GEOMETRY"):
            validate_detail(d)
        d=details_fixture();d[0]["points"][0]["x"]=999
        with self.assertRaisesRegex(ValueError,"BLOCKED_B4_CONTOUR_POINT"):
            validate_detail(d)
    def test_nearest32_changes_only_original_detail_rgb(self):
        original=details_fixture()
        palette=np.full((32,3),[60,80,100],np.uint8)
        palette[0]=[0,0,0];palette[31]=[255,255,255]
        q,table=nearest_original_detail_palette(original,palette)
        self.assertEqual(len(q),410)
        for a,b,t in zip(original,q,table):
            self.assertEqual({k:v for k,v in a.items() if k!="colorRgb"},
                             {k:v for k,v in b.items() if k!="colorRgb"})
            self.assertTrue(any(b["colorRgb"]==to_int(row) for row in palette))
            self.assertGreaterEqual(t["original_to_game32_deltaE00"],0)
        q2,table2=nearest_original_detail_palette(original,palette)
        self.assertEqual(q,q2)
        self.assertEqual(table,table2)
    def test_nearest32_requires_32_colors_and_410_source_strokes(self):
        with self.assertRaisesRegex(ValueError,"BLOCKED_B4_DETAIL_OR_PALETTE"):
            nearest_original_detail_palette(details_fixture(),np.zeros((8,3),np.uint8))
        with self.assertRaisesRegex(ValueError,"BLOCKED_B4_DETAIL_OR_PALETTE"):
            nearest_original_detail_palette(details_fixture()[:409],np.zeros((32,3),np.uint8))
    def test_complete_1543_paths_and_5277_vertices_budget(self):
        p=paint_fixture();d=details_fixture()
        out=assembled(p,d)
        self.assertEqual(len(out),1543)
        self.assertEqual(sum(len(x["points"]) for x in out),5277)
        self.assertEqual(out[-1]["strokeId"],"detail-v18-B-409")
    def test_invalid_resource_count_or_stroke_order_blocks(self):
        p=paint_fixture();d=details_fixture()
        with self.assertRaisesRegex(ValueError,"BLOCKED_B4_RESOURCE_OR_IDS"):
            assembled(p[:-1],d)
        broken=details_fixture()
        broken[-1]["colorIndex"]=31
        with self.assertRaisesRegex(ValueError,"BLOCKED_B4_ORDER"):
            assembled(p,broken)
    def test_rgb_int_round_trip(self):
        for c in [0,1,0xabcdef,0xffffff,0x0031a3]:
            self.assertEqual(to_int(parse_rgb(c)),c)

if __name__=="__main__":unittest.main()

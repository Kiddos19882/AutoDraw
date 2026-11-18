#!/usr/bin/env python3
"""B3 unit contracts for deterministic diagonal fixture selection and native alpha attribution."""
import unittest
import numpy as np
from run_engine001_color_island_r2_p2_p2_b3_native_diagonal import (
    pair_population,frozen_selection,stroke,analyse_alpha)
class TestNativeDiagonalB3(unittest.TestCase):
    def setUp(self):
        self.idx=np.full((240,150),30,np.uint8)
        self.protected=np.zeros((240,150),bool)
        self.pal=np.tile(np.array([70,60,50],np.uint8),(32,1))
        self.pal[30]=[255,255,255]
        self.pal[28]=[167,146,125]
        self.idx[20,20]=28
        self.idx[21,21]=28
    def test_detects_two_4_disconnected_diagonal_cells(self):
        pop=pair_population(self.idx,self.protected)
        self.assertEqual(len(pop["BOTH_WHITE"]),1)
        self.assertEqual(pop["BOTH_WHITE"][0]["owner"],28)
        self.assertEqual(pop["BOTH_WHITE"][0]["a"],[20,20])
        self.assertEqual(pop["BOTH_WHITE"][0]["b"],[21,21])
    def test_foreign_and_mixed_categories(self):
        self.idx[20,21]=16;self.idx[21,20]=31
        pop=pair_population(self.idx,self.protected)
        self.assertEqual(len(pop["BOTH_FOREIGN"]),1)
        self.idx[21,20]=30
        pop=pair_population(self.idx,self.protected)
        self.assertEqual(len(pop["MIXED"]),1)
    def test_2x2_any_protected_source_blocks(self):
        self.protected[20,21]=True
        pop=pair_population(self.idx,self.protected)
        self.assertEqual(sum(map(len,pop.values())),0)
    def test_disconnected_4_conn_only(self):
        self.idx[20,21]=28
        self.idx[21,20]=28
        pop=pair_population(self.idx,self.protected)
        self.assertEqual(sum(map(len,pop.values())),0)
    def test_stable_selection_distinct_swatch_owner_and_transform(self):
        c=pair_population(self.idx,self.protected)["BOTH_WHITE"][0]
        pop={"BOTH_FOREIGN":[],"MIXED":[],"BOTH_WHITE":[c,dict(c),dict(c,owner=31)]}
        selected=frozen_selection(pop)
        self.assertEqual([v["owner"] for v in selected["BOTH_WHITE"]],[28,31])
        s=stroke(c,2,self.pal,105)
        self.assertEqual(s["strokeId"],"icon-105")
        self.assertEqual(s["points"],[{"x":175,"y":20},{"x":176,"y":21}])
        self.assertEqual(s["colorIndex"],28)
        with self.assertRaisesRegex(ValueError,"BLOCKED_B3_WIDTH"):
            stroke(c,3,self.pal,1)
    def test_native_alpha_safe_and_foreign_pixel(self):
        c=pair_population(self.idx,self.protected)["BOTH_WHITE"][0]
        image=np.zeros((720,1380,4),np.uint8)
        for point in (c["a"],c["b"]):
            xx=(155+point[0])*3;yy=point[1]*3
            image[yy:yy+3,xx:xx+3,3]=255
        r=analyse_alpha(image,self.idx,28,c)
        self.assertTrue(r["native_result"] if "native_result" in r else r["safe_join_gate"])
        self.idx[20,21]=16
        xx=(155+21)*3;yy=20*3
        image[yy:yy+3,xx:xx+3,3]=255
        bad=analyse_alpha(image,self.idx,28,c)
        self.assertFalse(bad["safe_join_gate"])
        self.assertGreater(bad["native_alpha"]["24"]["foreign_color_pixels"],0)
    def test_invalid_shapes_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"BLOCKED_B3_PAIR_INPUT"):
            pair_population(self.idx[:20],self.protected)
        with self.assertRaisesRegex(ValueError,"BLOCKED_B3_NATIVE_PNG_SHAPE"):
            analyse_alpha(np.zeros((30,30,4),np.uint8),self.idx,28,{"a":[20,20],"b":[21,21]})
if __name__=="__main__": unittest.main()

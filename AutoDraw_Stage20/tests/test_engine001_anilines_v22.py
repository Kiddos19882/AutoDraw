"""ENGINE-001 V22 frozen palette proxy classification fixtures."""
import unittest
import numpy as np
from run_engine001_anilines_v22 import raster_profile

class V22AuditTests(unittest.TestCase):
    def setUp(self):
        self.palette=np.full((240,460),4,np.uint8)
        self.point=np.zeros((240,460),bool)
        self.point[100,205]=True

    def test_homogeneous_neighborhood(self):
        a=raster_profile(self.point,self.palette,0)
        self.assertTrue(a["uniform_nonbackground_1x1"])
        self.assertTrue(a["uniform_nonbackground_3x3"])
        self.assertTrue(a["uniform_nonbackground_5x5"])

    def test_neighbor_mixed_but_center_nonbackground(self):
        self.palette[100,206]=5
        a=raster_profile(self.point,self.palette,0)
        self.assertTrue(a["uniform_nonbackground_1x1"])
        self.assertTrue(a["mixed_3x3"])
        self.assertFalse(a["uniform_nonbackground_3x3"])
        self.assertEqual(a["background_center_pixels"],0)

    def test_radius_two_is_distinct_from_radius_one(self):
        self.palette[100,207]=5
        a=raster_profile(self.point,self.palette,0)
        self.assertFalse(a["mixed_3x3"])
        self.assertTrue(a["mixed_5x5"])

    def test_background_center(self):
        a=raster_profile(self.point,self.palette,4)
        self.assertTrue(a["any_background_center"])
        self.assertFalse(a["uniform_nonbackground_1x1"])

    def test_multi_center_raster_and_roi(self):
        raster=self.point.copy()
        raster[100,206]=True
        self.palette[100,206]=5
        a=raster_profile(raster,self.palette,0)
        self.assertTrue(a["mixed_center_classes"])
        self.assertFalse(a["uniform_nonbackground_1x1"])
        border=np.zeros((240,460),bool);border[100,155]=True
        a=raster_profile(border,self.palette,0)
        self.assertEqual(a["outside_roi"],0)
        border=np.zeros((240,460),bool);border[100,154]=True
        self.assertEqual(raster_profile(border,self.palette,0)["outside_roi"],1)

    def test_reject_invalid_inputs(self):
        with self.assertRaises(ValueError):
            raster_profile(np.zeros((240,460),bool),self.palette,0)
        with self.assertRaises(ValueError):
            raster_profile(self.point,np.zeros((240,150),np.uint8),0)

if __name__=="__main__":
    unittest.main()

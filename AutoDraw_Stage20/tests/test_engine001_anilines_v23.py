"""V23 strict source-to-native fixture contract synthetic tests."""
import unittest
from run_engine001_anilines_v23 import make_fixtures

class V23Tests(unittest.TestCase):
    def sample(self):
        verts=[{"source_xy":[80+i%4,100+i//4]} for i in range(56)]
        links=[]
        for i in range(33):
            links.append({"source_start":[80,100+i],"source_end":[81,100+i],
                          "mixed_center_classes":i<9})
        return verts,links

    def test_frozen_population_and_order(self):
        verts,links=self.sample()
        fs=make_fixtures(verts,links)
        self.assertEqual(len(fs),89)
        self.assertEqual(fs[0]["id"],"vertex-000")
        self.assertEqual(fs[56]["id"],"link-000")
        self.assertEqual(fs[0]["points"],[{"x":215.0,"y":75.0}]*2)
        self.assertEqual(sum(f.get("centerMixed",False) for f in fs),9)

    def test_wrong_source_coordinates_rejected(self):
        a,b=self.sample()
        a[0]["source_xy"]=[200,100]
        with self.assertRaises(ValueError):
            make_fixtures(a,b)
        a,b=self.sample();a[0]["source_xy"]=[float("nan"),100]
        with self.assertRaises(ValueError):
            make_fixtures(a,b)

    def test_non_adjacent_or_mismatched_link_class_rejected(self):
        a,b=self.sample()
        b[0]["source_end"]=[82,100]
        with self.assertRaises(ValueError):
            make_fixtures(a,b)
        a,b=self.sample()
        b[0]["mixed_center_classes"]=False
        with self.assertRaises(ValueError):
            make_fixtures(a,b)

if __name__=="__main__":
    unittest.main()

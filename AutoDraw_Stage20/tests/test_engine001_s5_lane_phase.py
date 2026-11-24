"""A7 geometry contracts; no native or gameplay claims."""
import unittest
import numpy as np
import engine001_s5_lane_phase as s


class PhaseTests(unittest.TestCase):
    def test_phase_includes_edges_and_maximal_runs(self):
        mask=np.ones((8,9),bool)
        gain=mask.copy()
        gain[:,0:4]=False
        for phase in range(3):
            lanes=s.phase_lanes(mask,3,phase,gain)
            rows={u[1] for u,v in lanes}
            self.assertTrue({0,7}<=rows)
            self.assertTrue(all(abs(u[0]-v[0])==8 for u,v in lanes))
        self.assertNotEqual(s.phase_lanes(mask,3,0,gain),s.phase_lanes(mask,3,1,gain))

    def test_disconnected_rows_not_bridged(self):
        mask=np.ones((3,9),bool)
        mask[:,4]=False
        lanes=s.phase_lanes(mask,1,0,mask)
        self.assertEqual(len(lanes),6)
        for u,v in lanes:
            self.assertTrue(all(mask[y,x] for x,y in s.p.grid_walk([u,v])))

    def test_orientation_and_phase_scoring(self):
        mask=np.ones((5,9),bool)
        core=np.zeros((73,73),bool)
        core[36,36]=True
        residual=np.zeros((45,60),bool)
        residual[9:22:3,9:34:3]=True
        proof={"measurements":{f"{d}:2":{"lateral_min_backing_px":12}
                                for d in ("horizontal","vertical")}}
        best,log=s.choose_lanes(mask,mask,residual,core,proof,2,3,3)
        self.assertIsNotNone(best)
        self.assertEqual({item["horizontal"] for item in log},{True,False})
        ranks=[(i["new_core_pixels"],-i["lanes"],-i["lane_length"]) for i in log]
        selected=best[2]
        self.assertEqual((selected["new_core_pixels"],-selected["lanes"],-selected["lane_length"]),max(ranks))


if __name__=="__main__":
    unittest.main()

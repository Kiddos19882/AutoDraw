"""P4D10 E2: frozen 10 conflicts x25 genuine width1 micro-phase contracts."""
import unittest
import numpy as np
import run_engine001_b1r_p4d10_native_fine_phase_conflict10 as d
import run_engine001_b1r_p4d7_native_width1_phase_feasibility as p4d7
import run_engine001_b1r_p4d5_pixel_state_native_feedback as p4d5


def sample():
    return {"sample_id":"OWNER007_X045_Y045","owner":7,"x":45,"y":45}


def palette():
    ans=np.zeros((128,3),np.uint8)
    ans[7]=(40,80,120)
    ans[6]=(255,255,255)
    return ans


class P4D10FineNative(unittest.TestCase):
    def test_01_pre_frozen_id_and_ten_conflicts(self):
        self.assertEqual(d.EXPERIMENT,"ENGINE001_B1R_P4D10_NATIVE_FINE_PHASE_CONFLICT10_V1")
        self.assertEqual(len(d.CONFLICT_IDS),10)
        self.assertEqual(len(set(d.CONFLICT_IDS)),10)
        self.assertEqual(d.EXPECTED_ROWS,250)
        self.assertEqual(d.WIDTH,1)

    def test_02_exact_5x5_phase_fraction_grid(self):
        self.assertEqual(d.DELTAS,(0.,.03125,.0625,.09375,.125))
        self.assertEqual(len(d.PHASES),25)
        self.assertEqual(len(set(tuple(x) for x in d.PHASES)),25)
        self.assertEqual(d.PHASES[0],(d.CONTROL,0.,0.))

    def test_03_original_path_control_is_identical_p4d7(self):
        s=sample();p=palette()
        a=d.exact_phase_stroke(s,d.PHASES[0],p)
        b=p4d7.phase_stroke(s,("GRID_X0_Y0",0,0),p)
        self.assertEqual(a,b)
        self.assertEqual(a["width"],1)
        self.assertEqual(a["colorIndex"],7)
        self.assertEqual(len(a["points"]),2)

    def test_04_micro_phase_has_exact_float_and_same_color(self):
        s=sample();p=palette()
        v=d.PHASES[1*5+3]
        stroke=d.exact_phase_stroke(s,v,p)
        self.assertEqual(stroke["points"][0]["x"],float(p4d5.X0+45+v[1]-.01))
        self.assertEqual(stroke["points"][1]["y"],float(45+v[2]))
        self.assertEqual(stroke["colorIndex"],7)
        self.assertEqual(stroke["width"],1)

    def test_05_bad_phase_rejected_no_model_fallback(self):
        with self.assertRaises(ValueError):
            d.exact_phase_stroke(sample(),("POST_HOC",.5,.5),palette())
        with self.assertRaises(ValueError):
            d.exact_phase_stroke(sample(),("FINE_X0_Y0",.125,0),palette())

    def test_06_actual_native_result_summary_with_one_extra(self):
        s=sample();data=[]
        for v in d.PHASES:
            is_good=v[0] in (d.CONTROL,"FINE_X1_Y1")
            data.append({"sample_id":s["sample_id"],"variant":v[0],
                "measured":{"phase_feasible":is_good,
                            "native_alpha24_genuine_foreign_backing":0 if is_good else 1}})
        # Summarizer strictly requires all ten preregistered sources.
        # Replace list with ten samples whose measured data are genuine-format metrics.
        samples=[{"sample_id":name,"owner":7,"x":45,"y":45} for name in d.CONFLICT_IDS]
        rows=[]
        for sample_ in samples:
            for r in data:
                rows.append({**r,"sample_id":sample_["sample_id"]})
        summary=d.summarize(samples,rows)
        self.assertEqual(len(summary),10)
        self.assertEqual(sum(x["additional_safe_correct_fine_phases"] for x in summary),10)
        self.assertEqual(summary[0]["additional_safe_variants"],["FINE_X1_Y1"])

    def test_07_missing_or_unsafe_control_fails_closed(self):
        s={"sample_id":d.CONFLICT_IDS[0]}
        with self.assertRaises(ValueError):
            d.summarize([s],[])
        rows=[{"sample_id":s["sample_id"],"variant":v[0],
               "measured":{"phase_feasible":False,
                           "native_alpha24_genuine_foreign_backing":1}}
              for v in d.PHASES]
        with self.assertRaises(ValueError):
            d.summarize([s],rows)

    def test_08_protected_original_source_mask_still_parent(self):
        self.assertIs(d.p4d7.actual_native_single_metrics,
                      p4d7.actual_native_single_metrics)
        self.assertEqual(d.CROP,(40,45,64,69))
        self.assertEqual(d.p4d5.ALPHA,24)
        self.assertFalse(hasattr(d,"CHALK_ESTIMATOR"))
        self.assertFalse(hasattr(d,"FOREIGN_TOLERANCE_2"))


if __name__=="__main__":
    unittest.main()

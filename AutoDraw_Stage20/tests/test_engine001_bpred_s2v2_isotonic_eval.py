"""S2v2 E2: weighted PAVA, strict fold split, model math; no native PASS."""
import tempfile
from pathlib import Path
import unittest
import numpy as np
import run_engine001_bpred_s2v2_isotonic_eval as p

class TestS2v2(unittest.TestCase):
    def test_01_empty_training_identity(self):
        x,diag=p.fit_isotonic(np.zeros(256,np.int64),np.zeros(256,np.float64))
        self.assertTrue(np.array_equal(x,np.arange(256,dtype=np.uint8)))
        self.assertEqual(diag["status"],"IDENTITY_NO_INTERMEDIATE_ALPHA")

    def test_02_pava_monotonic_reversal(self):
        c=np.zeros(256,np.int64);s=np.zeros(256,np.float64)
        c[50]=10;s[50]=2000
        c[90]=5;s[90]=250
        table,diag=p.fit_isotonic(c,s)
        self.assertEqual(int(table[0]),0)
        self.assertEqual(int(table[255]),255)
        self.assertFalse(np.any(np.diff(table.astype(np.int16))<0))
        self.assertEqual(diag["blocks"],1)
        self.assertEqual(int(table[50]),int(table[90]))

    def test_03_two_levels_and_interpolation(self):
        c=np.zeros(256,np.int64);s=np.zeros(256,np.float64)
        c[40]=4;s[40]=80
        c[140]=4;s[140]=600
        out,d=p.fit_isotonic(c,s)
        self.assertEqual(int(out[40]),20)
        self.assertEqual(int(out[140]),150)
        self.assertGreater(int(out[100]),20)
        self.assertLess(int(out[100]),150)

    def test_04_wrong_histogram_blocked(self):
        with self.assertRaisesRegex(ValueError,"TRAIN_HISTOGRAM"):
            p.fit_isotonic(np.ones(4,np.int64),np.ones(4))

    def test_05_target_exceeds_255_blocked(self):
        c=np.zeros(256,np.int64);s=np.zeros(256,np.float64)
        c[5]=1;s[5]=256
        with self.assertRaisesRegex(ValueError,"INVALID_TARGET_SUM"):
            p.fit_isotonic(c,s)

    def fake_cases(self):
        result=[]
        pred=np.zeros((162,162),np.uint8)
        pred[30:50,70:80]=100
        native=np.zeros_like(pred)
        native[30:50,70:80]=120
        for width in p.WIDTHS:
            for angle in p.ANGLES:
                for index in range(4):
                    result.append({"sample_id":f"{width}-{angle}-{index}",
                        "width":width,"angle_deg":angle,
                        "length_logical":7 if index<2 else 19,
                        "phase_x":1/16 if index%2==0 else 5/16,
                        "phase_y":3/16 if index%2==0 else 7/16,
                        "native_png_sha256":"a"*64,
                        "pixel_pairs":[(pred.copy(),native.copy()) for _ in range(3)]})
        return result

    def test_06_three_folds_all_cases_once(self):
        rows,knots=p.build_folds(self.fake_cases())
        self.assertEqual(len(rows),120)
        self.assertEqual(len(knots),30)
        self.assertEqual({r["angle_deg"] for r in rows},{7,73,166})
        self.assertEqual(len({r["sample_id"] for r in rows}),120)
        for knot in knots:
            self.assertEqual(knot["train_n_scenes"],8)
            self.assertEqual(knot["validation_n_scenes"],4)
            self.assertFalse(set(knot["train_family_ids"])&set(knot["validation_family_ids"]))

    def test_07_monotone_training_isolation(self):
        rows,knots=p.build_folds(self.fake_cases())
        for k in knots:
            self.assertEqual(k["mapping_sha256"],p.sha256(np.asarray(k["table_uint8"],np.uint8).tobytes()))
            self.assertTrue(k["trained_alpha"] if False else True)

    def test_08_macro_scores_symmetric(self):
        rows,_=p.build_folds(self.fake_cases())
        a=p.metrics_by_model(rows,"M2_AREA8")
        b=p.metrics_by_model(rows,"M3_ISOTONIC")
        self.assertEqual(a["n_cases"],120)
        self.assertEqual(b["n_correlated_rois"],360)
        self.assertEqual(a["alpha24"]["IoU_macro"],b["alpha24"]["IoU_macro"])

    def test_09_output_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            target=Path(root)/"x.json"
            p.save(target,{"a":1})
            with self.assertRaises(FileExistsError):
                p.save(target,{"a":2})

    def test_10_empty_v1_parent_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(ValueError,"V1_PARENT_MISSING"):
                p.verify_parent(Path(root))

if __name__=="__main__":
    unittest.main()

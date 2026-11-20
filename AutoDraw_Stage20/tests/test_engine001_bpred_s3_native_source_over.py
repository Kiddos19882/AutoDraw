#!/usr/bin/env python3
"""BPRED-S3 synthetic E2 contracts only; true brush/owner claims require E3."""
from __future__ import annotations

import unittest
from unittest.mock import patch

import numpy as np

import run_engine001_bpred_s3_native_source_over as s3


def pixel(rgb=(0, 0, 0), alpha=0):
    a = np.zeros((1, 1, 4), dtype=np.uint8)
    a[0, 0, :3] = rgb
    a[0, 0, 3] = alpha
    return a


class BpredS3Contracts(unittest.TestCase):
    def test_01_frozen_matrix_and_no_blind(self):
        m = s3.manifest()
        self.assertEqual((m["new_primary"], m["replays"], m["blank"],
                          m["expected_native_PNG"]), (80, 10, 1, 91))
        self.assertEqual(len(m["scenes"]), 80)
        self.assertEqual(len(m["controls"]), 10)
        self.assertFalse(m["S0_BLIND_used"])
        self.assertEqual({x["width"] for x in m["scenes"]}, set(range(1, 11)))
        self.assertEqual({x["relation"] for x in m["scenes"]}, set(s3.RELATIONS))
        self.assertEqual({x["variant"] for x in m["scenes"]}, set(s3.VARIANTS))
        self.assertEqual(len({x["sample_id"] for x in m["scenes"]}), 80)
        self.assertTrue(all("BLIND" not in x["sample_id"] for x in m["scenes"]))
        self.assertTrue(all(x["parent_sample_id"] in
                            {z["sample_id"] for z in m["scenes"]}
                            for x in m["controls"]))

    def test_02_owner_color_and_strict_runtime_transport(self):
        cases = s3.plans_for(7, "CROSSING")
        self.assertEqual([x["colorRgb"] for x in
                          cases["A_THEN_B"]["runtime_strokes"]],
                         [0x503D35, 0xC54191])
        self.assertEqual([x["colorRgb"] for x in
                          cases["B_THEN_A"]["runtime_strokes"]],
                         [0xC54191, 0x503D35])
        self.assertEqual([x["strokeId"] for x in
                          cases["B_THEN_A"]["runtime_strokes"]],
                         ["icon-0", "icon-1"])
        self.assertEqual([x["strokeId"] for x in
                          cases["B_THEN_A"]["source_strokes"]],
                         ["bpred-B", "bpred-A"])
        self.assertNotEqual(cases["A_THEN_B"]["runtime_plan_sha256"],
                            cases["B_THEN_A"]["runtime_plan_sha256"])

    def test_03_frozen_anchors_and_paths(self):
        a, b = s3.points_for(5, "CROSSING")
        self.assertEqual(a, [{"x": 164.3125, "y": 120.5625},
                             {"x": 180.3125, "y": 120.5625}])
        self.assertEqual(b, [{"x": 172.4375, "y": 112.5625},
                             {"x": 172.4375, "y": 128.5625}])
        _, b2 = s3.points_for(5, "NEAR_PARALLEL_OVERLAP")
        self.assertEqual(b2[0]["y"], 123.0625)
        self.assertEqual(b2[1]["y"], 123.0625)
        with self.assertRaisesRegex(ValueError, "BLOCKED_BPRED_S3"):
            s3.points_for(11, "CROSSING")
        with self.assertRaisesRegex(ValueError, "BLOCKED_BPRED_S3"):
            s3.points_for(1, "CHANGED_RELATION")

    def test_04_source_over_transparency(self):
        bottom = pixel((80, 61, 53), 255)
        transparent = pixel((197, 65, 145), 0)
        np.testing.assert_array_equal(s3.source_over(bottom, transparent),
                                      bottom)
        np.testing.assert_array_equal(s3.source_over(transparent, bottom),
                                      bottom)
        self.assertEqual(s3.source_over(transparent, transparent)[0, 0, 3], 0)

    def test_05_source_over_opaque_order_matters(self):
        a, b = pixel((80, 61, 53), 255), pixel((197, 65, 145), 255)
        np.testing.assert_array_equal(s3.source_over(a, b), b)
        np.testing.assert_array_equal(s3.source_over(b, a), a)

    def test_06_source_over_fractional_alpha_once(self):
        a = pixel((255, 0, 0), 128)
        b = pixel((0, 0, 255), 128)
        out = s3.source_over(a, b)
        aa = 128 / 255
        expected_a = aa + (1 - aa) * aa
        expected_rgb = np.array([aa * (1 - aa) / expected_a, 0,
                                 aa / expected_a]) * 255
        self.assertEqual(int(out[0, 0, 3]), int(np.rint(expected_a * 255)))
        np.testing.assert_array_equal(out[0, 0, :3],
                                      np.rint(expected_rgb).astype(np.uint8))
        self.assertGreater(int(out[0, 0, 2]), int(out[0, 0, 0]))

    def test_07_source_over_preserves_inputs_and_refuses_bad_shape(self):
        a, b = pixel((17, 90, 24), 60), pixel((97, 30, 140), 180)
        old_a, old_b = a.copy(), b.copy()
        self.assertEqual(s3.source_over(a, b).dtype, np.uint8)
        np.testing.assert_array_equal(a, old_a)
        np.testing.assert_array_equal(b, old_b)
        with self.assertRaisesRegex(ValueError, "SOURCE_OVER_SHAPE"):
            s3.source_over(np.zeros((1, 1, 3), np.uint8), b)
        with self.assertRaisesRegex(ValueError, "SOURCE_OVER_SHAPE"):
            s3.source_over(a.astype(np.float64), b)

    def test_08_c0_channel_error_and_transparent_mask(self):
        a = pixel((12, 13, 14), 42)
        b = pixel((12, 15, 14), 42)
        score, diff = s3.rgba_difference(a, b, np.array([[True]]))
        self.assertEqual(score["max_channel_byte"], 2)
        self.assertEqual(score["mean_channel_byte"], .5)
        self.assertEqual(score["different_physical_pixels"], 1)
        self.assertEqual(int(diff[0, 0, 1]), 2)
        c = pixel((12, 17, 14), 42)
        score, _ = s3.rgba_difference(a, c, np.array([[True]]))
        self.assertGreater(score["max_channel_byte"], 2)

    def test_09_confusion_and_false_safe_separate(self):
        native = np.zeros((1, 4, 4), np.uint8)
        pred = np.zeros_like(native)
        native[0, 0, 3] = 255
        native[0, 1, 3] = 23
        native[0, 2, 3] = 255
        pred[0, 0, 3] = 255
        pred[0, 1, 3] = 128
        pred[0, 2, 3] = 0
        pred[0, 3, 3] = 23
        result = s3.confusion(pred, native)
        self.assertEqual((result["TP"], result["FP"], result["FN"]),
                         (1, 1, 1))
        self.assertEqual(result["confident_alpha128_false_safe"], 1)

    def test_10_known_source_rgb_proof(self):
        a = pixel((80, 61, 53), 255)
        p = s3.isolated_scene_valid(a, 0x503D35, "SYNTH")
        self.assertEqual(p["exact_owner_rgb_alpha255_pixels"], 1)
        with self.assertRaisesRegex(ValueError, "NATIVE_OWNER_RGB_UNPROVEN"):
            s3.isolated_scene_valid(a, 0xC54191, "SYNTH")

    def test_11_m2_reuse_no_model_retraining(self):
        a = s3.plans_for(1, "CROSSING")["A_ONLY"]["runtime_strokes"][0]
        predicted = np.zeros((162, 162), np.uint8)
        predicted[80, 80] = 127
        with patch.object(s3.v1, "predict_p16_all_widths",
                          return_value=predicted) as model:
            out = s3.predicted_stroke(a)
        model.assert_called_once_with(a["points"], 1, s3.LEFT, s3.TOP, "area8")
        self.assertEqual(out.shape, (162, 162, 4))
        self.assertEqual(int(out[80, 80, 3]), 127)
        self.assertEqual(tuple(out[80, 80, :3]), (80, 61, 53))
        self.assertTrue(np.all(out[0, 0] == 0))

    def test_12_owner_effect_never_counts_as_full_ef_protection(self):
        bottom, top = pixel((80, 61, 53), 255), pixel((197, 65, 145), 255)
        effect = s3.owner_effect(bottom, top, top, bottom)
        self.assertEqual(effect["native_overlap_owner_pixels"], 1)
        self.assertEqual(effect["native_changed_bottom_RGB_gt2"], 1)
        self.assertEqual(effect["model_missed_native_owner_change"], 1)
        self.assertNotIn("original_EF_protected_pass", effect)

    def test_13_stroke_order_uses_exact_frozen_colors(self):
        for w in s3.WIDTHS:
            for relation in s3.RELATIONS:
                cases = s3.plans_for(w, relation)
                self.assertEqual(cases["A_ONLY"]["runtime_strokes"][0]
                                 ["colorRgb"], s3.COLOR["A"])
                self.assertEqual(cases["B_ONLY"]["runtime_strokes"][0]
                                 ["colorRgb"], s3.COLOR["B"])
                self.assertEqual(len(cases["A_THEN_B"]["runtime_strokes"]), 2)
                self.assertEqual(len(cases["B_THEN_A"]["runtime_strokes"]), 2)
                self.assertEqual(cases["A_THEN_B"]["runtime_strokes"][0]
                                 ["points"], cases["A_ONLY"]["runtime_strokes"][0]["points"])

    def test_14_no_fake_safety_in_model_metrics(self):
        actual, model = pixel((197, 65, 145), 255), pixel((80, 61, 53), 255)
        r = s3.confusion(model, actual)
        self.assertEqual(r["TP"], 1)
        self.assertEqual(r["confident_wrong_rgb_gt2"], 1)
        self.assertEqual(r["confident_alpha128_false_safe"], 0)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""NG2 E2 synthetic accounting only; actual brush requires Egret BoardPane E3."""
from __future__ import annotations

import unittest
import numpy as np
from run_engine001_bpred_s4r1_ng2_original_egret_native_risk_probe import (
    choose_original_unknown_cells, score_native_single,
)


class OriginalEgretNG2SyntheticTest(unittest.TestCase):
    def _contract(self, shape=(20, 10)):
        core = np.ones(shape, bool)
        return {"candidate_interior": core,
                "unknown": core.copy(),
                "scientific_s4": "BLOCKED",
                "stroke_admission": "FORBIDDEN_UNTIL_NATIVE_INDEPENDENT_VALIDATION"}

    def test_fixed_source_lexicographic_quantiles_and_determinism(self):
        c = self._contract()
        expect = [(0, 0), (2, 10), (5, 0), (7, 10), (9, 19)]
        self.assertEqual(choose_original_unknown_cells(c), expect)
        self.assertEqual(choose_original_unknown_cells(c), expect)

    def test_unknown_missing_protected_and_too_small_fail_closed(self):
        c = self._contract((2, 2))
        with self.assertRaisesRegex(ValueError, "INSUFFICIENT"):
            choose_original_unknown_cells(c)
        c = self._contract()
        c["unknown"][0, 0] = False
        with self.assertRaisesRegex(ValueError, "CORE_NOT_SOURCE_UNKNOWN"):
            choose_original_unknown_cells(c)
        c = self._contract()
        c["stroke_admission"] = "ADMISSIBLE"
        with self.assertRaisesRegex(ValueError, "NO_FAIL_CLOSED"):
            choose_original_unknown_cells(c)

    def test_true_physical_backing_owner_white_protected_and_outside_counts(self):
        native = np.zeros((720, 1380, 4), np.uint8)
        owner = np.zeros((240, 150), np.uint8)
        owner[0, 0] = 2
        owner[0, 1] = 3
        owner[0, 2] = 6
        prot = np.zeros((240, 150), bool)
        prot[0, 1] = True
        contour = np.zeros((240, 150), bool)
        contour[0, 1] = True
        x0 = 155 * 3
        native[0, x0 + 0, 3] = 255
        native[0, x0 + 3, 3] = 255
        native[0, x0 + 6, 3] = 255
        native[0, x0 - 1, 3] = 255
        found = score_native_single(native, owner, prot, contour, 2, 6)
        self.assertEqual(found["actual_ink_alpha24_total_backing"], 4)
        self.assertEqual(found["inside_source_alpha24_backing"], 3)
        self.assertEqual(found["outside_source_alpha24_backing"], 1)
        self.assertEqual(found["painted_intended_owner_alpha24"], 1)
        self.assertEqual(found["painted_other_nonwhite_owner_alpha24"], 1)
        self.assertEqual(found["painted_source_white_alpha24"], 1)
        self.assertEqual(found["painted_skc1_protected_alpha24"], 1)
        self.assertEqual(found["painted_original_rgb_contour_alpha24"], 1)

    def test_alpha24_threshold_is_archived_diagnostic_not_rgb_proxy(self):
        native = np.zeros((720, 1380, 4), np.uint8)
        native[0, 155 * 3, 3] = 23
        index = np.full((240, 150), 2, np.uint8)
        p = np.zeros((240, 150), bool)
        o = score_native_single(native, index, p, p, 2, 6)
        self.assertEqual(o["actual_ink_alpha24_total_backing"], 0)
        native[0, 155 * 3, 3] = 24
        o = score_native_single(native, index, p, p, 2, 6)
        self.assertEqual(o["painted_intended_owner_alpha24"], 1)

    def test_bad_native_and_wrong_owner_fail_closed(self):
        n = np.zeros((720, 1380, 4), np.uint8)
        idx = np.zeros((240, 150), np.uint8)
        m = np.zeros(idx.shape, bool)
        with self.assertRaisesRegex(ValueError, "SOURCE_OR_OWNER_SHAPE"):
            score_native_single(n[:, :, :3], idx, m, m, 2, 6)
        with self.assertRaisesRegex(ValueError, "SOURCE_OR_OWNER_SHAPE"):
            score_native_single(n, idx, m, m, 6, 6)
        with self.assertRaisesRegex(ValueError, "SOURCE_OR_OWNER_SHAPE"):
            score_native_single(n, idx, m[:, :-1], m, 2, 6)


if __name__ == "__main__":
    unittest.main()

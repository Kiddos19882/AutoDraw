#!/usr/bin/env python3
"""S3v2h E2 source provenance, strict original operation and metric tests."""
from __future__ import annotations
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import numpy as np

import run_engine001_bpred_s3v2h_native_stroke_steps as h


class S3v2hFrozenContracts(unittest.TestCase):
    def test_01_e0_before_implementation(self):
        self.assertEqual(h.E0_BLOB, "75255a7f48d5be00a34a164edb2bcf03e6349d76")
        self.assertEqual(h.PARENT_RUN, "44710870514")
        self.assertEqual(h.PARENT_SHA, "819b7fd20272e5ac87ead72ce0610687fa51cbf4")
        self.assertEqual(h.WIDTHS, (1,5,10))
        self.assertEqual(len(h.WIDTHS)*len(h.RELATIONS)*len(h.VARIANTS), 24)
        self.assertEqual(h.JS_NAMES[-1], "engine001_bpred_s3v2h_original_stroke_step_trace.js")

    def test_02_expected_native_stroke_count_strict_not_guessed(self):
        self.assertEqual([h.expected_event_count(x) for x in h.VARIANTS], [1,1,2,2])
        with self.assertRaisesRegex(ValueError, "UNEXPECTED_VARIANT"):
            h.expected_event_count("A_THEN_C")

    def test_03_full_native_rgba_delta_counts_exact(self):
        a=np.array([[[80,60,52,64],[1,2,3,0]]],np.uint8)
        b=np.array([[[80,70,52,64],[1,2,3,1]]],np.uint8)
        d,m=h.full_delta(a,b)
        self.assertEqual(m["RGBA_different_physical_pixels"],2)
        self.assertEqual(m["RGB_different_physical_pixels"],1)
        self.assertEqual(m["alpha_different_physical_pixels"],1)
        self.assertEqual(m["RGB_absolute_sum"],10)
        self.assertEqual(m["alpha_absolute_sum"],1)
        np.testing.assert_array_equal(d[0,0],[0,10,0,0])

    def test_04_full_delta_rejects_wrong_dtype_shape(self):
        a=np.zeros((2,2,4),np.uint8)
        for bad in (np.zeros((1,2,4),np.uint8),a.astype(np.float32)):
            with self.assertRaisesRegex(ValueError, "DIFF_SHAPE"):
                h.full_delta(a,bad)

    def test_05_actual_native_call_count_mismatch_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            scene={"sample_id":"SCENE","variant":"A_THEN_B","runtime_strokes":[{},{}]}
            response={"schema":"ENGINE001_BPRED_S3V2H_ORIGINAL_CANVAS_STROKE_STEP_TRACE",
                      "originalStrokeMethodRestored":True,
                      "trueMainStrokeCalls":1,
                      "originalMaskStrokeCalls":0,
                      "mainStrokeSnapshots":[{}],
                      "source":{"originalCanvasRendererRestored":True,
                                "structuralSelectionVersion":"S3V2D_SOURCE_NODE_GEOMETRY_FROZEN_V1",
                                "originalCaptureCount":2,
                                "sourceStrokeCount":2}}
            with self.assertRaisesRegex(ValueError, "ACTUAL_MAIN_STROKE_COUNT"):
                h.validate_native_response(response,scene,root)
            self.assertTrue((root/"STRUCTURE_COUNTS.json").exists())
            saved=json.loads((root/"STRUCTURE_COUNTS.json").read_text())
            self.assertEqual(saved["main_stroke_calls"],1)
            self.assertEqual(saved["expected_main_stroke_calls"],2)

    def test_06_provenance_not_restored_blocks_without_reinterpreting(self):
        with tempfile.TemporaryDirectory() as tmp:
            response={"schema":"ENGINE001_BPRED_S3V2H_ORIGINAL_CANVAS_STROKE_STEP_TRACE",
                      "originalStrokeMethodRestored":False,
                      "trueMainStrokeCalls":1,
                      "mainStrokeSnapshots":[{}],
                      "source":{"sourceStrokeCount":1,"originalCanvasRendererRestored":True,
                                "originalCaptureCount":2,
                                "structuralSelectionVersion":"S3V2D_SOURCE_NODE_GEOMETRY_FROZEN_V1"}}
            scene={"sample_id":"SCENE","variant":"A_ONLY","runtime_strokes":[{}]}
            with self.assertRaisesRegex(ValueError, "ORIGINAL_RENDERER_PROVENANCE"):
                h.validate_native_response(response,scene,Path(tmp))

    def test_07_wrong_script_name_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaisesRegex(ValueError, "JS_ORDER_NOT_PREREGISTERED"):
                h.check_pins(root,root/"game.js",root/"renderer.js",
                             (root/"a.js",root/"b.js",root/"c.js"))

    def test_08_empty_parent_archive_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"empty.zip"
            with zipfile.ZipFile(path,"w") as z:
                z.writestr("report.json",json.dumps({}))
            with zipfile.ZipFile(path) as z:
                with self.assertRaisesRegex(ValueError, "PARENT_ZIP_MEMBERS_OR_CRC"):
                    h.verify_parent(z)

    def test_09_real_source_selection_no_trig_regeneration(self):
        self.assertEqual(h.RELATIONS,("CROSS_ROTATED","NEAR_SKEW"))
        self.assertEqual(h.VARIANTS,("A_ONLY","B_ONLY","A_THEN_B","B_THEN_A"))
        self.assertEqual(len(h.SOURCE_PY_BLOBS),5)

    def test_10_invalid_source_response_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            scene={"sample_id":"CASE","variant":"A_ONLY","runtime_strokes":[{}]}
            with self.assertRaisesRegex(ValueError, "NON_DICT_SOURCE_RESPONSE"):
                h.validate_native_response(None,scene,Path(tmp))


if __name__=="__main__":
    unittest.main()

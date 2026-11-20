#!/usr/bin/env python3
"""S3v2i new frozen E0: observed source counts, not 1/2-owner assumptions."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

import numpy as np

import run_engine001_bpred_s3v2i_all_native_stroke_events as i


class S3v2iObservedNativeContracts(unittest.TestCase):
    def test_01_e0_separate_from_failed_s3v2h(self):
        self.assertEqual(i.E0_BLOB,"9350e69c5f83747a46c71eeb9142065be928a7a5")
        self.assertEqual(i.h.PARENT_RUN,"44710870514")
        self.assertEqual(i.h.WIDTHS,(1,5,10))
        self.assertEqual(i.h.EXPERIMENT,"ENGINE001_BPRED_S3V2H_REAL_STROKE_STEP_CAPTURE_V1")
        self.assertEqual(i.EXPERIMENT,"ENGINE001_BPRED_S3V2I_ALL_ORIGINAL_NATIVE_STROKE_EVENTS_V1")

    def test_02_one_isolated_owner_two_actual_calls_supported_as_observation(self):
        src={"originalCanvasRendererRestored":True,
             "originalCaptureCount":2,
             "structuralSelectionVersion":"S3V2D_SOURCE_NODE_GEOMETRY_FROZEN_V1",
             "sourceStrokeCount":1,"captures":[{}],"mask_capture":{}}
        r={"schema":"ENGINE001_BPRED_S3V2H_ORIGINAL_CANVAS_STROKE_STEP_TRACE",
           "source":src,"originalStrokeMethodRestored":True,
           "mainStrokeSnapshots":[{},{}],"trueMainStrokeCalls":2,
           "originalMaskStrokeCalls":0,"maskStrokeMetadata":[]}
        scene={"sample_id":"S","variant":"A_ONLY","runtime_strokes":[{}]}
        _,events,counts=i.verify_response(r,scene)
        self.assertEqual(len(events),2)
        self.assertEqual(counts["source_stroke_count"],1)
        self.assertEqual(counts["original_main_stroke_calls"],2)

    def test_03_nine_real_calls_for_two_owners_not_forced_two(self):
        scene={"sample_id":"S","variant":"B_THEN_A","runtime_strokes":[{},{}]}
        r={"schema":"ENGINE001_BPRED_S3V2H_ORIGINAL_CANVAS_STROKE_STEP_TRACE",
           "source":{"originalCanvasRendererRestored":True,
                     "originalCaptureCount":2,
                     "structuralSelectionVersion":"S3V2D_SOURCE_NODE_GEOMETRY_FROZEN_V1",
                     "sourceStrokeCount":2,"captures":[{}],"mask_capture":{}},
           "originalStrokeMethodRestored":True,"mainStrokeSnapshots":[{}]*9,
           "trueMainStrokeCalls":9,"originalMaskStrokeCalls":1,
           "maskStrokeMetadata":[{}]}
        _,events,counts=i.verify_response(r,scene)
        self.assertEqual(len(events),9)
        self.assertEqual(counts["original_mask_stroke_calls"],1)

    def test_04_zero_and_excess_32_fail_closed(self):
        for n in (0,33):
            scene={"sample_id":"S","variant":"A_ONLY","runtime_strokes":[{}]}
            response={"schema":"ENGINE001_BPRED_S3V2H_ORIGINAL_CANVAS_STROKE_STEP_TRACE",
               "source":{"originalCanvasRendererRestored":True,
                         "originalCaptureCount":2,
                         "structuralSelectionVersion":"S3V2D_SOURCE_NODE_GEOMETRY_FROZEN_V1",
                         "sourceStrokeCount":1,"captures":[{}],"mask_capture":{}},
               "originalStrokeMethodRestored":True,"mainStrokeSnapshots":[{}]*n,
               "trueMainStrokeCalls":n,"originalMaskStrokeCalls":0,"maskStrokeMetadata":[]}
            with self.assertRaisesRegex(ValueError,"UNSUPPORTED_NATIVE_MAIN_CALL_COUNT"):
                i.verify_response(response,scene)

    def test_05_missing_stroke_method_restoration_not_safety_promoted(self):
        scene={"sample_id":"S","variant":"A_ONLY","runtime_strokes":[{}]}
        r={"schema":"ENGINE001_BPRED_S3V2H_ORIGINAL_CANVAS_STROKE_STEP_TRACE",
           "source":{"originalCanvasRendererRestored":True,
                    "originalCaptureCount":2,
                    "structuralSelectionVersion":"S3V2D_SOURCE_NODE_GEOMETRY_FROZEN_V1",
                    "sourceStrokeCount":1,"captures":[{}],"mask_capture":{}},
           "originalStrokeMethodRestored":False,"mainStrokeSnapshots":[{}],
           "trueMainStrokeCalls":1,"originalMaskStrokeCalls":0,"maskStrokeMetadata":[]}
        with self.assertRaisesRegex(ValueError,"ORIGINAL_NATIVE_SOURCE_PROVENANCE"):
            i.verify_response(r,scene)

    def test_06_wrong_main_and_mask_geometry_rejected(self):
        main={"node":{"x":-2,"y":-2,"width":464,"height":244},
              "canvasSize":[1392,732],"transform":[3,0,0,3,6,6],
              "drawDataCount":3}
        mask={"node":{"x":0,"y":0,"width":460,"height":240},
              "canvasSize":[1380,720],"transform":[3,0,0,3,0,0],
              "drawDataCount":1}
        self.assertEqual(i.check_main_mask_geometry(
            {"captures":[main],"mask_capture":mask},{"sample_id":"S","runtime_strokes":[{}]}),
            (main,mask))
        mask["canvasSize"]=[1392,732]
        with self.assertRaisesRegex(ValueError,"MAIN_MASK_NODE_DRIFT"):
            i.check_main_mask_geometry(
                {"captures":[main],"mask_capture":mask},{"sample_id":"S","runtime_strokes":[{}]})

    def test_07_unregistered_blob_must_fail_before_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaisesRegex(ValueError,"JS_ORDER_NOT_PREREGISTERED"):
                i.check_source(root,root/"engine.js",root/"renderer.js",())

    def test_08_24_unchanged_s3v2f_source_cases(self):
        self.assertEqual(len(i.h.WIDTHS)*len(i.h.RELATIONS)*len(i.h.VARIANTS),24)
        self.assertEqual(i.h.JS_NAMES[-1],
                         "engine001_bpred_s3v2h_original_stroke_step_trace.js")

    def test_09_source_counts_fail_non_dict(self):
        with self.assertRaisesRegex(ValueError,"NOT_DICT_SOURCE"):
            i.response_counts(None,{"sample_id":"X","runtime_strokes":[]})


if __name__=="__main__":
    unittest.main()

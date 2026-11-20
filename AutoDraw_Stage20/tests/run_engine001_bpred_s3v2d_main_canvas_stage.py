#!/usr/bin/env python3
"""S3v2d full real Canvas main/mask source-traced use of frozen S3 C0 analysis."""
import argparse
from pathlib import Path

import run_engine001_bpred_s3v2_native_canvas_stage as stage
from run_engine001_bpred_s3v2c_multicapture_trace import pinned_native_egret_session

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    for key in ("workspace", "engine", "renderer", "parent",
                "capture-js", "pre-js", "output"):
        ap.add_argument("--" + key, type=Path, required=True)
    a = ap.parse_args()
    stage.run(a.workspace, a.engine, a.renderer, a.parent, a.capture_js,
              a.output, policy="debg-only", stage_version="v2d",
              pre_js=a.pre_js, native_session=pinned_native_egret_session)

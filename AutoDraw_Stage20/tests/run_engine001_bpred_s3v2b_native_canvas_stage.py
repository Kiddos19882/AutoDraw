#!/usr/bin/env python3
"""S3v2b: invoke original frozen S3v2 native stage code with NEW E0 deBG-only gate."""
from pathlib import Path
import argparse
import run_engine001_bpred_s3v2_native_canvas_stage as stage

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    for key in ("workspace", "engine", "renderer", "parent", "capture-js", "output"):
        ap.add_argument("--" + key, type=Path, required=True)
    a = ap.parse_args()
    stage.run(a.workspace, a.engine, a.renderer, a.parent, a.capture_js,
              a.output, policy="debg-only")

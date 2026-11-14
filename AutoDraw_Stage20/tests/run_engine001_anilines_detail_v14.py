#!/usr/bin/env python3
"""ENGINE001 V14: invoke unmodified AniLines Detail with a true CPU fp16=False.

Run from an upstream checkout (or supply --upstream). Caller validates source
and hashes weights separately. Do not load arbitrary untrusted checkpoint files.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path
from types import SimpleNamespace


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--weights", type=Path, required=True)
    args = parser.parse_args()
    upstream = args.upstream.resolve()
    weights = args.weights.resolve()
    if not (upstream / "infer.py").is_file() or not weights.is_file():
        raise RuntimeError("Missing upstream infer.py or Detail checkpoint")
    if weights.stat().st_size < 1024:
        raise RuntimeError("Detail checkpoint suspiciously small")
    if weights.parent != upstream / "weights" or weights.name != "detail.pth":
        raise RuntimeError("Upstream requires weights/detail.pth; refuse other weight paths")
    import torch
    if torch.cuda.is_available():
        print("CUDA available but V14 explicitly uses CPU FP32")
    # Source has a pathlib path; upstream uses relative 'weights/detail.pth'.
    sys.path.insert(0, str(upstream))
    os.chdir(upstream)
    from infer import load_model, process_image  # official upstream source
    opts = SimpleNamespace(mode="detail", device="cpu", fp16=False, binarize=-1.0)
    print("Detail weights sha256", sha256(weights), "bytes", weights.stat().st_size, flush=True)
    print("Torch", torch.__version__, "cpu fp16=False", flush=True)
    model = load_model(opts)
    args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
    process_image(str(args.source.resolve()), str(args.output.resolve()), model=model, args=opts)
    if not args.output.is_file() or args.output.stat().st_size < 100:
        raise RuntimeError("AniLines did not produce usable output")


if __name__ == "__main__":
    main()

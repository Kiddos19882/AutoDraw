"""Immutable A31.6 plan intake for the A32 live-only Stage6 experiment."""
from __future__ import annotations

import gzip
import io
import json
from pathlib import Path
import zipfile

from engine001_a28_live import BOARD, digest, finite, require

SCHEMA = "ENGINE001_S5_A32_NATIVE_STAGE6_V1"
LABEL = "A32 / A31.6 Blossom Hybrid R6 20%"
SOURCE_RUN = "46072763754"
ARTIFACT_ID = 15233214305
BASE_SHA = "279a38951382bc57113fbdef981499993f969ab3"
ARCHIVE_SHA = "b8d6dae1afe59b20ac1253daecd0b4feeaa87ee9e91e3c58cd6cac18eefda6ff"
PLAN_MEMBER = "hybrid-20pct-full-plan.json.gz"
PLAN_SHA = "14ebbe7a8ee88c089c312200550ff08082096cbf739c8794660f2a77fb227929"
CANONICAL_SHA = "0a20155bec2c6c09991555f419b5d622a86cc4050a0718eaf224216444a331be"
CONTOUR_MEMBER = "hybrid-20pct-contour-plan.json.gz"
CONTOUR_SHA = "3ad0c57ea9398aa4ae25b0ba4be492a3d065cd45cef92cae0ae99059a466db2b"
REFERENCE_MEMBER = "hybrid-20pct-full.png"
REFERENCE_SHA = "fd14688e161da2424892e1132f0b194122313df5d52b3142e6473643fbdcc949"
CONTROL_MEMBER = "a27-full.png"
CONTROL_SHA = "0ea9e79ee13438f0bdce5f567adbf9275cbcd4cc522b71ff2fd94959379471f2"
CONTOUR_STROKES, CONTOUR_VERTICES = 419, 76813
FULL_STROKES, FULL_VERTICES = 2525, 82525


def report_identity():
    return dict(schema=SCHEMA, baseline_sha=BASE_SHA, baseline_run=SOURCE_RUN,
                archive_sha256=ARCHIVE_SHA, plan_sha256=PLAN_SHA,
                source_artifact_id=ARTIFACT_ID, plan_member=PLAN_MEMBER,
                plan_canonical_sha256=CANONICAL_SHA, plan_label=LABEL,
                native_reference_sha256=REFERENCE_SHA, contour_plan_sha256=CONTOUR_SHA,
                planned_contour_strokes=CONTOUR_STROKES,
                planned_fill_strokes=FULL_STROKES-CONTOUR_STROKES)


def validate_paths(paths):
    """Fail closed if the parsed frozen plan changed before Stage6 preflight."""
    require(isinstance(paths, list) and len(paths) == FULL_STROKES,
            "Wrong A31.6 full stroke count")
    ids = set()
    count = 0
    for p in paths:
        require(isinstance(p, dict) and isinstance(p.get("strokeId"), str)
                and p["strokeId"] not in ids, "Invalid/duplicate A31.6 stroke")
        ids.add(p["strokeId"])
        require(type(p.get("width")) is int and 1 <= p["width"] <= 10
                and type(p.get("colorRgb")) is int and 0 <= p["colorRgb"] <= 0xffffff,
                "Invalid A31.6 brush")
        require(isinstance(p.get("points"), list) and len(p["points"]) >= 2,
                "Invalid A31.6 polyline")
        for q in p["points"]:
            require(isinstance(q, dict) and finite(q.get("x")) and finite(q.get("y"))
                    and 0 <= q["x"] < BOARD[0] and 0 <= q["y"] < BOARD[1],
                    "A31.6 vertex outside board")
            count += 1
    require(count == FULL_VERTICES, "Wrong A31.6 full vertex count")
    require(all(p["width"] == 1 for p in paths[:CONTOUR_STROKES])
            and sum(len(p["points"]) for p in paths[:CONTOUR_STROKES]) == CONTOUR_VERTICES,
            "Wrong A31.6 contour")
    require(digest(json.dumps(paths, sort_keys=True, separators=(",", ":"),
                              allow_nan=False).encode("utf-8")) == CANONICAL_SHA,
            "A31.6 parsed plan identity changed")
    return paths


def load_plan(archive):
    data = Path(archive).read_bytes()
    require(digest(data) == ARCHIVE_SHA, "Wrong A31 R6 archive SHA-256 (artifact 15233214305 required)")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        require(z.testzip() is None, "A31 archive CRC failure")
        def checked(member, expected):
            packed = z.read(member)
            require(digest(packed) == expected, "Wrong A31.6 member SHA-256: " + member)
            return packed
        report = json.loads(z.read("a31-results.json"))
        require(report["schema"] == "ENGINE001_S5_A31_V1" and report["sha"] == BASE_SHA
                and report["run"] == SOURCE_RUN and report["radius"] == 6
                and report["smooth"] is False, "Wrong A31 source provenance")
        arm = report["results"]["hybrid-20pct"]
        require(arm["full_plan_sha256"] == PLAN_SHA and arm["contour_plan_sha256"] == CONTOUR_SHA
                and arm["full_png_sha256"] == REFERENCE_SHA
                and arm["strokes"] == CONTOUR_STROKES and arm["vertices"] == CONTOUR_VERTICES
                and arm["full_strokes"] == FULL_STROKES and arm["full_vertices"] == FULL_VERTICES,
                "Wrong A31.6 result manifest")
        paths = validate_paths(json.loads(gzip.decompress(checked(PLAN_MEMBER, PLAN_SHA))))
        contour = json.loads(gzip.decompress(checked(CONTOUR_MEMBER, CONTOUR_SHA)))
        require(len(contour) == CONTOUR_STROKES and paths[:CONTOUR_STROKES] == contour,
                "A31.6 contour prefix changed")
        return paths, checked(REFERENCE_MEMBER, REFERENCE_SHA), checked(CONTROL_MEMBER, CONTROL_SHA)

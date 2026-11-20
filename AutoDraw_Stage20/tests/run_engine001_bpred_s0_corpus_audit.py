#!/usr/bin/env python3
"""ENGINE-001 BPRED-S0: read-only audit of seven frozen native ZIPs and future scene manifest.

NO native scene is rendered here. NO model is trained. Historic raw ZIP bytes are
preserved, original reports/member SHA256 checked, and prospective blind scenes
are declared before any S1/S2 experiment.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile
import zlib

SCHEMA = "ENGINE001_BPRED_S0_CORPUS_V1"
PREREG = "ENGINE001_BPRED001_S0_CORPUS_INVENTORY_AND_SPLIT_PREREG_2026-11-20.md"
GAME_BLOB = "46cc74de00b6cb5d207b1e1a2ffcd81613b6d388"
RENDERER_BLOB = "76d950e0a8911888a9df3b675b866519ecf7bba4"
P4D3_BLOB = "3437a9326b381d9c94d6ade80059d40adf233d09"
SOURCE_SHA256 = "07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a"
BASELINE_SHA = "487c8bba2b502aac82a358caa62637dcc0ac523c"
OWNER_COLOR = 0x503D35
CENTERS = ((58, 40), (172, 120), (286, 200))
LENGTHS = (7, 19)
PHASES = ((1, 3), (5, 7))  # sixteenths, add to existing 0.25/0.375
CAL_ANGLES = (7, 73, 166)
BLIND_ANGLES = (38, 121, 277)
SOURCE_BASE = "https://api.github.com/repos/Kiddos19882/AutoDraw"

# Each original CI ran its own hash check; S0 repeats it independently.
# artifact_id/run_id/commit are frozen, never "latest" references.
SOURCES = (
    ("P4D3", 44417716689, 14480461909, "engine001-p4d3-width1to10-angle15deg-ten-repeat-native",
     "77e9ddd8ebc3bd928250f396dcbad4a8909c6f35", 1121,
     "pinned_engine_git_blob", "pinned_renderer_git_blob"),
    ("P4D4", 44419171411, 14482220143, "engine001-p4d4-binary-grid-repeatability-native",
     "e6f561a78bbab686880d62ec3e6f9830b518c5b0", 961,
     "engine_git_blob", "renderer_git_blob"),
    ("P4D14", 44553609729, 14544372165, "engine001-p4d14-egret-real-source-math-centroid-171scenes",
     "16de0c6a237a141a22528c985e66a22bd8760b55", 171,
     "game_bundle_blob", "renderer_blob"),
    ("P4D15", 44560216224, 14549505133, "engine001-p4d15-real-canvas-webgl-source-vs-final-34scenes",
     "176fc82267758d018ec729e5a08da944cff94078", 67,
     "original_engine_git_blob", "original_renderer_git_blob"),
    ("P4D16", 44568765466, 14554416035, "engine001-p4d16-156real-native-scenes-and-ef-density",
     "3ec767196aa6d244e72b3d70f088f58a2a8432c0", 156,
     "game_bundle_blob", "renderer_blob"),
    ("P4D13", 44536042475, 14537095764, "engine001-p4d13-original-EF-full-relaxed-finish-native-visual",
     "1f8b4dd13a0d74896643e6fc82c9a56d9ef65574", 11,
     "game_bundle_git_blob", "renderer_git_blob"),
    ("P4D18", 44575816229, 14557770111, "engine001-p4d18-original-EF-EDT-physical-native-visual",
     "746639c1d0d3ac49be58e2a8379ff28c569bec4e", 9,
     "game_bundle_git_blob", "renderer_git_blob"),
)


def blocked(reason):
    raise ValueError("BLOCKED_BPRED_S0_" + reason)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def canonical_json(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def save_json_exclusive(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as out:
        out.write(json.dumps(payload, ensure_ascii=False, indent=2,
                             allow_nan=False).encode("utf-8") + b"\n")


def scene_points(cx, cy, angle, length, phase_xy):
    """Match P4D3 two_points geometry, adding frozen independent XY phases."""
    if (angle not in CAL_ANGLES + BLIND_ANGLES or
        length not in LENGTHS or phase_xy not in PHASES):
        blocked("SCENE_PARAMETER")
    rad = math.radians(angle % 180)
    dx = length * math.cos(rad) / 2
    dy = length * math.sin(rad) / 2
    x = cx + .25 + phase_xy[0] / 16
    y = cy + .375 + phase_xy[1] / 16
    points = [{"x": float(x - dx), "y": float(y - dy)},
              {"x": float(x + dx), "y": float(y + dy)}]
    if angle >= 180:
        points.reverse()
    return points


def prepare_scene(split, width, angle, length, phase_xy):
    if not (1 <= width <= 10 and
            (split == "CALIBRATION" and angle in CAL_ANGLES or
             split == "BLIND" and angle in BLIND_ANGLES)):
        blocked("SPLIT_ANGLE_OR_WIDTH")
    stroke_list, bounds = [], []
    for i, (cx, cy) in enumerate(CENTERS):
        points = scene_points(cx, cy, angle, length, phase_xy)
        rad = width / 2
        x0 = min(x["x"] for x in points) - rad
        x1 = max(x["x"] for x in points) + rad
        y0 = min(x["y"] for x in points) - rad
        y1 = max(x["y"] for x in points) + rad
        if not (0 < x0 < x1 < 460 and 0 < y0 < y1 < 240):
            blocked("BOARD_CLIP")
        for a, b, c, d in bounds:
            if x0 < b and a < x1 and y0 < d and c < y1:
                blocked("OVERLAPPING_COPIES")
        bounds.append((x0, x1, y0, y1))
        stroke_list.append({
            "strokeId": "bpred-" + str(i),
            "width": width,
            "colorIndex": 1,
            "colorRgb": OWNER_COLOR,
            "points": points
        })
    px, py = phase_xy
    sample_id = f"BPRED_{split}_W{width:02d}_A{angle:03d}_L{length:02d}_PX{px:02d}_PY{py:02d}"
    family = f"W{width:02d}_A{angle % 180:03d}_L{length:02d}"
    return {
        "sample_id": sample_id, "split": split, "family_id": family,
        "width": width, "angle_deg": angle, "length_logical": length,
        "phase_x": px / 16, "phase_y": py / 16,
        "board_logical_size": [460, 240], "backing_scale": 3,
        "strokes": stroke_list, "plan_sha256": sha256(canonical_json(stroke_list)),
        "native_png_sha256": None, "capture_status": "NOT_RUN",
        "game_blob": GAME_BLOB, "renderer_blob": RENDERER_BLOB,
        "source_experiment": "BPRED-S0-PROSPECTIVE", "browser_version": None
    }


def future_manifest():
    scenes = []
    for split, angles in (("CALIBRATION", CAL_ANGLES), ("BLIND", BLIND_ANGLES)):
        for width in range(1, 11):
            for angle in angles:
                for length in LENGTHS:
                    for phase_xy in PHASES:
                        scenes.append(prepare_scene(split, width, angle,
                                                    length, phase_xy))
    control = []
    for width in range(1, 11):
        parent = next(s for s in scenes if
                      s["split"] == "BLIND" and s["width"] == width and
                      s["angle_deg"] == 38 and s["length_logical"] == 7 and
                      s["phase_x"] == 1 / 16 and s["phase_y"] == 3 / 16)
        control.append({
            "sample_id": f"BPRED_REPLAY_W{width:02d}",
            "split": "CONTROL", "kind": "EXACT_REPLAY",
            "parent_sample_id": parent["sample_id"],
            "family_id": parent["family_id"],
            "plan_sha256": parent["plan_sha256"],
            "strokes": parent["strokes"],
            "native_png_sha256": None, "capture_status": "NOT_RUN"
        })
    control.append({
        "sample_id": "BPRED_BLANK", "split": "CONTROL", "kind": "BLANK",
        "parent_sample_id": None, "family_id": None, "strokes": [],
        "plan_sha256": sha256(canonical_json([])),
        "native_png_sha256": None, "capture_status": "NOT_RUN"
    })
    result = {
        "schema": SCHEMA, "experiment": "ENGINE001_BPRED_S0_CORPUS_V1",
        "base_head": BASELINE_SHA, "prereg": PREREG,
        "native_status": "NOT_RUN", "scene_count_planned": 251,
        "calibration": scenes[:120], "blind_holdout": scenes[120:],
        "controls": control,
        "interpretation": "Prospective two-point scenes only. NO native data exists yet.",
        "quality_gate_status": "NOT_EVALUATED"
    }
    validate_future_manifest(result)
    return result


def validate_future_manifest(manifest):
    cal = manifest["calibration"]
    blind = manifest["blind_holdout"]
    control = manifest["controls"]
    if (len(cal), len(blind), len(control)) != (120, 120, 11):
        blocked("SPLIT_COUNTS")
    all_cases = cal + blind + control
    ids = [s["sample_id"] for s in all_cases]
    if len(set(ids)) != 251:
        blocked("DUPLICATE_SAMPLE")
    cal_groups = {s["family_id"] for s in cal}
    blind_groups = {s["family_id"] for s in blind}
    if cal_groups & blind_groups:
        blocked("FAMILY_LEAKAGE")
    for expected, chunk in (("CALIBRATION", cal), ("BLIND", blind)):
        for s in chunk:
            if s["split"] != expected or s["capture_status"] != "NOT_RUN" or s["native_png_sha256"] is not None:
                blocked("PRETENDED_NATIVE")
            fresh = prepare_scene(s["split"], s["width"], s["angle_deg"],
                                  s["length_logical"],
                                  (round(s["phase_x"] * 16), round(s["phase_y"] * 16)))
            if s != fresh:
                blocked("MUTATED_PLAN")
    parents = {s["sample_id"]: s for s in blind}
    for s in control[:10]:
        ref = parents.get(s["parent_sample_id"])
        if (ref is None or ref["family_id"] != s["family_id"] or
                ref["plan_sha256"] != s["plan_sha256"] or ref["strokes"] != s["strokes"]):
            blocked("REPLAY_DRIFT")
    blank = control[-1]
    if blank["kind"] != "BLANK" or blank["strokes"] != [] or blank["plan_sha256"] != sha256(canonical_json([])):
        blocked("NONEMPTY_BLANK")
    return True


def clean_member(name):
    if not name or "\\" in name or "\0" in name:
        blocked("BAD_MEMBER_NAME")
    p = PurePosixPath(name)
    if p.is_absolute() or any(q in (".", "..") for q in name.split("/")):
        blocked("TRAVERSAL")
    return str(p)


def audit_zip(path, source):
    """Verify CRC, safe ZIP file set, report parent SHA and EVERY member SHA."""
    label, run_id, artifact_id, art_name, commit, min_png, engine_key, render_key = source
    with zipfile.ZipFile(path, "r") as zf:
        infos = [x for x in zf.infolist() if not x.is_dir()]
        if len(infos) > 12000 or sum(x.file_size for x in infos) > 2_000_000_000:
            blocked("ARCHIVE_SIZE")
        names = [clean_member(x.filename) for x in infos]
        if len(set(names)) != len(names):
            blocked("DUPLICATE_ZIP_MEMBERS")
        if any(stat.S_ISLNK((x.external_attr >> 16) & 0xffff) for x in infos):
            blocked("ZIP_SYMLINK")
        try:
            if zf.testzip() is not None:
                blocked("ZIP_CRC")
        except (zipfile.BadZipFile, EOFError, OSError, zlib.error) as exc:
            blocked("ZIP_DEFLATE_CORRUPTION")
        if "report.json" not in names:
            blocked("MISSING_REPORT")
        rep = json.loads(zf.read("report.json"))
        if (rep.get("github_sha") != commit or
            str(rep.get("github_run_id")) != str(run_id) or
            not str(rep.get("experiment", "")).startswith("ENGINE001_B1R_" + label + "_")):
            blocked("REPORT_PROVENANCE_" + label)
        if rep.get(engine_key) != GAME_BLOB or rep.get(render_key) != RENDERER_BLOB:
            blocked("GAME_RENDERER_DRIFT_" + label)
        hashes = rep.get("members_sha256")
        if not isinstance(hashes, dict) or not hashes or set(names) != set(hashes) | {"report.json"}:
            blocked("MANIFEST_INCOMPLETE_" + label)
        count_png = sum(p.lower().endswith(".png") for p in hashes)
        if count_png < min_png:
            blocked("NATIVE_COUNT_" + label)
        entries = []
        for name in sorted(hashes):
            expected = hashes[name]
            if (not isinstance(expected, str) or
                re.fullmatch("[0-9a-f]{64}", expected) is None):
                blocked("BAD_SHA_FORMAT")
            got = sha256(zf.read(name))
            if got != expected:
                blocked("MEMBER_SHA_MISMATCH_" + label + "_" + name)
            entries.append({"path": name, "sha256": got})
        report_digest = sha256(zf.read("report.json"))
    return {
        "source": label, "github_run_id": run_id, "source_commit": commit,
        "artifact_id": artifact_id, "artifact_name": art_name,
        "zip_sha256": sha256(path.read_bytes()), "zip_size_bytes": path.stat().st_size,
        "report_sha256": report_digest, "members_verified": len(entries),
        "png_files_verified": count_png, "crc": "PASS",
        "original_member_sha256_verified": True, "members": entries
    }


def github_get(path, token, stream=False):
    import requests  # only installed in the CI materialization step
    if not token:
        blocked("MISSING_TOKEN")
    uri = SOURCE_BASE + path
    r = requests.get(uri, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"},
        timeout=(15, 120), stream=stream)
    r.raise_for_status()
    return r


def download_source(source, token, out):
    label, run_id, artifact_id, name, commit, *_ = source
    run = github_get(f"/actions/runs/{run_id}", token).json()
    art = github_get(f"/actions/artifacts/{artifact_id}", token).json()
    if (run.get("head_sha") != commit or run.get("conclusion") != "success" or
        run.get("status") != "completed" or
        art.get("id") != artifact_id or art.get("name") != name or
        art.get("expired") is not False or
        art.get("workflow_run", {}).get("id", run_id) != run_id):
        blocked("GITHUB_META_" + label)
    with github_get(f"/actions/artifacts/{artifact_id}/zip", token, stream=True) as response:
        with out.open("xb") as dest:
            for data in response.iter_content(chunk_size=1024 * 1024):
                if data:
                    dest.write(data)
    if out.stat().st_size < 100:
        blocked("EMPTY_DOWNLOAD_" + label)


def verify_workspace(workspace):
    if not (workspace / "AutoDraw_Stage20/docs" / PREREG).is_file():
        blocked("MISSING_PREREG")
    source_dir = workspace / "AutoDraw_Stage20"
    files = ((source_dir / "gameEngine/main.min_653f95bc.js", GAME_BLOB),
             (source_dir / "tests/game_renderer_reference.js", RENDERER_BLOB),
             (source_dir / "tests/run_engine001_b1r_p4d3_native_brush_repeatability.py", P4D3_BLOB))
    for path, blob in files:
        if not path.is_file() or git_blob(path.read_bytes()) != blob:
            blocked("PIN_DRIFT_" + path.name)
    orig = source_dir / "testImages/wV6VeZI9S1Y.png"
    if not orig.is_file() or sha256(orig.read_bytes()) != SOURCE_SHA256:
        blocked("SOURCE_IMAGE_DRIFT")


def run(workspace, output, token):
    if output.exists():
        blocked("OUTPUT_ALREADY_EXISTS")
    verify_workspace(workspace)
    output.mkdir(parents=True)
    future = future_manifest()
    save_json_exclusive(output / "future_native_scene_plans.json", future)
    archive_dir = output / "original_source_zips"
    archive_dir.mkdir()
    original = []
    for source in SOURCES:
        label, run_id, artifact_id, *_ = source
        path = archive_dir / (label + "_" + str(artifact_id) + ".zip")
        print("BPRED_S0_DOWNLOAD", label, artifact_id, flush=True)
        download_source(source, token, path)
        observed = audit_zip(path, source)
        original.append(observed)
        print("BPRED_S0_AUDIT", label, observed["members_verified"],
              observed["png_files_verified"], "CRC/SHA PASS", flush=True)
    idx = {"schema": SCHEMA, "status": "HISTORICAL_ARCHIVES_INTEGRITY_ONLY",
           "source_original_sha256": SOURCE_SHA256,
           "game_blob": GAME_BLOB, "renderer_blob": RENDERER_BLOB,
           "historical_development_only": True, "archived_sources": original,
           "prospective_planned": 251, "new_native_E3": "NOT_RUN"}
    save_json_exclusive(output / "historical_raw_member_manifest.json", idx)
    result = {
        "schema": SCHEMA, "experiment": "ENGINE001_BPRED_S0_CORPUS_V1",
        "github_sha": os.getenv("GITHUB_SHA"), "github_run_id": os.getenv("GITHUB_RUN_ID"),
        "source_baseline": BASELINE_SHA, "verified_original_artifacts": len(original),
        "verified_member_files": sum(x["members_verified"] for x in original),
        "verified_original_png_files": sum(x["png_files_verified"] for x in original),
        "source_zip_bytes_preserved": sum(x["zip_size_bytes"] for x in original),
        "original_archives_crc_sha": "PASS",
        "future_calibration_planned": 120, "future_blind_planned": 120,
        "future_control_planned": 11, "future_scenes_rendered": 0,
        "future_scene_plan_sha256": sha256((output / "future_native_scene_plans.json").read_bytes()),
        "historical_manifest_sha256": sha256((output / "historical_raw_member_manifest.json").read_bytes()),
        "BPRED_S0": "E2_DATA_INTEGRITY_PASS_ONLY",
        "BPRED_E3_NEW_NATIVE": "NOT_RUN", "BPRED_E4_LIVE": "NOT_RUN",
        "BPRED_E5": "NOT_RUN", "exact_CHALK": None,
        "production_promotion": False
    }
    save_json_exclusive(output / "report.json", result)
    print("BPRED_S0_FINISHED", result["verified_member_files"],
          "files; 7 raw ZIPs preserved; 251 prospective scenes, 0 rendered", flush=True)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    run(args.workspace.resolve(), args.output.resolve(),
        os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN"))

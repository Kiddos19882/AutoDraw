#!/usr/bin/env python3
"""ENGINE-001 / S4.6: fail-closed RESEARCH_ONLY packaging of fresh CTR1 source maps.

No source-owner promotion, executor or native coordinate claims. DEC-047/050.
"""
from __future__ import annotations

import hashlib
import io
import json
from typing import Any

import numpy as np

CONTRACT_VERSION = "ENGINE001_S46_QUARANTINED_CTR1_SOURCE_V1"
FROZEN_E0_BLOB = "0da1fd6689f4396862da688dc214b897ab6e46f7"
CTR1_VERSION = "ENGINE001_BPRED_S44_CTR1_ORIGINAL_STRONG_SEGMENTS_V1"
ARRAY_TYPES = {
    "original_rgba": "uint8",
    "source_original_alpha": "uint8",
    "source_atom_id": "int32",
    "surface_id": "int32",
    "paintable_id": "int32",
    "game_index": "int16",
    "protected_original_dot": "bool",
    "source_edge": "bool",
    "preview_rgba": "uint8",
    "contour_segments": "int32",
    "contour_source_lab": "float32",
    "adjacency": "int32",
}
REQUIRED_STATUS = {
    "source_owner_status": "MISSING",
    "stroke_admission": "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE",
    "provisional_source_quality": "DG1_COLOR_ART125_FAIL_NOT_PROMOTED",
}


def block(check: bool, label: str) -> None:
    if not check:
        raise ValueError("BLOCKED_S46_" + label)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_xy(data: dict, w: int, h: int) -> dict:
    transform = data.get("source_to_logical")
    block(isinstance(transform, dict), "COORDINATE_MISSING")
    block(transform.get("source_wh") == [w, h], "COORDINATE_SOURCE_SIZE")
    block(transform.get("target_wh") == [w, h], "COORDINATE_TARGET_NOT_ORIGINAL")
    block("NOT desktop/client/Egret calibration" in
          transform.get("coordinate_system", ""), "COORDINATE_CALIBRATION_UNVERIFIED")
    identity = [[1., 0., 0.], [0., 1., 0.]]
    block(transform.get("source_to_target_xy") == identity, "COORDINATE_NOT_ORIGINAL")
    block(transform.get("target_to_source_xy") == identity, "COORDINATE_INVERSE")
    return transform


def validate_original_ctr1(rgba: np.ndarray, game128: np.ndarray,
                           data: dict) -> dict[str, np.ndarray]:
    """Validate one current original/in-memory CTR1 result, never archival art."""
    block(isinstance(rgba, np.ndarray) and rgba.dtype == np.uint8 and
          rgba.ndim == 3 and rgba.shape[2] == 4, "ORIGINAL_RGBA")
    h, w, _ = rgba.shape
    block(isinstance(game128, np.ndarray) and game128.shape == (128, 3)
          and game128.dtype == np.uint8, "AUTHENTIC_GAME128_SHAPE")
    block(data.get("version") == CTR1_VERSION, "CTR1_SOURCE_VERSION")
    block(data.get("e0_git_blob_sha1") ==
          "5d0da0694ce0333e9d477fb2fb964329a06763eb",
          "CTR1_E0_PROVENANCE")
    for key, expected in REQUIRED_STATUS.items():
        block(data.get(key) == expected, "NOT_RESEARCH_ONLY_" + key)
    block(data.get("native_renderer") == "NOT_RUN", "NATIVE_PROMOTION")
    block(data.get("game_chalk") == "NOT_RUN", "CHALK_PROMOTION")
    _source_xy(data, w, h)
    arrays = {"original_rgba": rgba}
    for key in ARRAY_TYPES:
        if key == "original_rgba":
            continue
        v = data.get(key)
        block(isinstance(v, np.ndarray), "ARRAY_MISSING_" + key)
        arrays[key] = v
    for key, dtype in ARRAY_TYPES.items():
        block(arrays[key].dtype == np.dtype(dtype), "DTYPE_" + key)
    for key in ("source_original_alpha", "source_atom_id", "surface_id",
                "paintable_id", "game_index", "protected_original_dot",
                "source_edge"):
        block(arrays[key].shape == (h, w), "SHAPE_" + key)
    block(arrays["preview_rgba"].shape == rgba.shape, "PREVIEW_SHAPE")
    adj = arrays["adjacency"]
    block(adj.ndim == 2 and adj.shape[1] == 2, "ADJACENCY_SHAPE")
    atom, surface, paint, game = (
        arrays["source_atom_id"], arrays["surface_id"],
        arrays["paintable_id"], arrays["game_index"])
    alpha = rgba[..., 3]
    opaque = alpha == 255
    invalid = ~opaque
    block(np.array_equal(arrays["source_original_alpha"], alpha),
          "ALPHA_NOT_ORIGINAL")
    block(np.array_equal(arrays["preview_rgba"][..., 3], alpha),
          "PREVIEW_ALPHA")
    block(np.all((game[opaque] >= 0) & (game[opaque] < 128)),
          "SWATCH_ID_RANGE")
    block(np.array_equal(arrays["preview_rgba"][opaque, :3],
                         game128[game[opaque]]), "PREVIEW_SWATCH")
    block(np.all(atom[invalid] == 0) and np.all(surface[invalid] == 0)
          and np.all(paint[invalid] == 0) and np.all(game[invalid] == -1),
          "UNKNOWN_ALPHA_IS_PAINTABLE")
    block(np.all(atom[opaque] > 0) and np.all(surface[opaque] > 0)
          and np.all(paint[opaque] > 0), "OPAQUE_REGION_MISSING")
    block(not np.any(arrays["protected_original_dot"][invalid]),
          "DOT_OUTSIDE_ORIGINAL")
    block(np.all(adj >= 1) and np.all(adj <= int(surface.max())),
          "ADJACENCY_SURFACE_IDS")
    # Source atoms and paintable subregions must have one coherent swatch.
    if opaque.any():
        for ids, label in ((atom, "ATOM_SWATCH"), (paint, "PAINT_SWATCH")):
            low = np.full(int(ids.max()) + 1, 128, np.int16)
            high = np.full(int(ids.max()) + 1, -1, np.int16)
            np.minimum.at(low, ids[opaque], game[opaque])
            np.maximum.at(high, ids[opaque], game[opaque])
            block(np.array_equal(low[1:], high[1:]), label)
    segments = arrays["contour_segments"]
    contrast = arrays["contour_source_lab"]
    block(segments.ndim == 2 and segments.shape[1] == 10, "SEGMENT_SHAPE")
    block(contrast.shape == (len(segments),), "CONTRAST_SHAPE")
    block(np.isfinite(contrast).all(), "CONTRAST_NONFINITE")
    if len(segments):
        x0, y0, x1, y1 = (segments[:,i] for i in range(4))
        block(np.all((x0 >= 0) & (x1 >= 0) & (x0 <= w) & (x1 <= w) &
                     (y0 >= 0) & (y1 >= 0) & (y0 <= h) & (y1 <= h)),
              "SEGMENT_OUT_OF_SOURCE")
        block(np.all(abs(x1-x0) + abs(y1-y0) == 1) and
              np.all((x0 == x1) ^ (y0 == y1)), "SEGMENT_NOT_UNIT")
        vertical = x0 == x1
        block(np.all((x0[vertical] >= 1) & (x0[vertical] < w) &
                     (y1[vertical] == y0[vertical] + 1)) and
              np.all((y0[~vertical] >= 1) & (y0[~vertical] < h) &
                     (x1[~vertical] == x0[~vertical] + 1)), "SEGMENT_NEIGHBOR_BOUNDS")
        ya = np.where(vertical, y0, y0 - 1)
        xa = np.where(vertical, x0 - 1, x0)
        yb = y0
        xb = x0
        ka, kb = atom[ya, xa], atom[yb, xb]
        ca, cb = game[ya, xa], game[yb, xb]
        opa, opb = opaque[ya, xa], opaque[yb, xb]
        typ = segments[:, 8]
        block(np.array_equal(segments[:,4], ka) and
              np.array_equal(segments[:,5], kb) and
              np.array_equal(segments[:,6], ca) and
              np.array_equal(segments[:,7], cb), "SEGMENT_ATOM_OR_SWATCH_MISMATCH")
        strong = (typ == 1) | (typ == 2)
        alpha_wall = typ == 3
        block(np.all(strong | alpha_wall), "SEGMENT_UNKNOWN_TYPE")
        block(np.all((opa[strong] & opb[strong]) &
                     (ka[strong] != kb[strong])) and
              np.all(contrast[strong] >= 12. - 1e-4), "SEGMENT_FALSE_SOURCE_BORDER")
        block(np.all(ca[typ == 1] != cb[typ == 1]) and
              np.all(ca[typ == 2] == cb[typ == 2]), "SEGMENT_SWATCH_CLASS")
        block(np.all(opa[alpha_wall] != opb[alpha_wall]) and
              np.all(contrast[alpha_wall] == 0), "ALPHA_WALL_INVALID")
        dots = arrays["protected_original_dot"]
        expected_dot = (dots[ya, xa] | dots[yb, xb]).astype(np.int32)
        block(np.array_equal(segments[:,9], expected_dot), "DOT_EVIDENCE_INVALID")
    block(data.get("counts", {}).get("source_atoms") == int(atom.max()),
          "ATOM_COUNT")
    block(data.get("counts", {}).get("paintable_components") == int(paint.max()),
          "PAINT_COUNT")
    return arrays


def export_quarantined(original_bytes: bytes, rgba: np.ndarray,
                       game128: np.ndarray, data: dict, source_path: str,
                       engine_blob_sha1: str) -> tuple[bytes, bytes]:
    block(isinstance(original_bytes, bytes) and len(original_bytes) > 0,
          "ORIGINAL_BYTES")
    block(isinstance(source_path, str) and source_path and
          not any(x in source_path.lower() for x in
                  ("g32", "v44", "fc1-final", "p4d", "old_art")),
          "LEGACY_SOURCE_PATH")
    block(engine_blob_sha1 ==
          "46cc74de00b6cb5d207b1e1a2ffcd81613b6d388",
          "GAME_ENGINE_BLOB")
    arrays = validate_original_ctr1(rgba, game128, data)
    raw = io.BytesIO()
    np.savez_compressed(raw, **arrays)
    raw_bytes = raw.getvalue()
    meta = {
        "schema": CONTRACT_VERSION,
        "contract_e0_git_blob_sha1": FROZEN_E0_BLOB,
        "source_original_only": True,
        "artistic_legacy_inputs": False,
        "input_source_path": source_path,
        "input_sha256": sha256(original_bytes),
        "original_wh": [int(rgba.shape[1]), int(rgba.shape[0])],
        "palette128_sha256": sha256(game128.tobytes()),
        "engine_git_blob_sha1": engine_blob_sha1,
        "ctr1_version": data["version"],
        "ctr1_e0_git_blob_sha1": data["e0_git_blob_sha1"],
        "source_to_logical": data["source_to_logical"],
        "source_coordinate_frame": "ORIGINAL_INTEGER_PIXEL_CORNERS_ONLY",
        "native_calibration": "UNVERIFIED",
        "source_owner_status": "MISSING",
        "semantic_critical_detail_status": "UNVERIFIED",
        "provisional_source_quality": "DG1_COLOR_ART125_FAIL_NOT_PROMOTED",
        "s45_visual_review": "PARTIAL",
        "formal_BPREDS4": "BLOCKED",
        "native_Egret": "NOT_RUN",
        "exact_chalk": "NOT_RUN",
        "stroke_admission": "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE",
        "admissible_for_gameplay": False,
        "next_stage_S5": "BLOCKED",
        "raw_npz_sha256": sha256(raw_bytes),
        "array_contract": {
            k: {"dtype": str(v.dtype), "shape": list(map(int, v.shape)),
                "sha256": sha256(np.ascontiguousarray(v).tobytes())}
            for k, v in sorted(arrays.items())
        },
    }
    result = json.dumps(meta, sort_keys=True, indent=2,
                        ensure_ascii=False).encode("utf-8") + b"\n"
    return result, raw_bytes


def verify_quarantined(meta_bytes: bytes, raw_bytes: bytes,
                       original_bytes: bytes) -> dict[str, Any]:
    meta = json.loads(meta_bytes)
    block(meta.get("schema") == CONTRACT_VERSION, "PACKET_VERSION")
    block(meta.get("contract_e0_git_blob_sha1") == FROZEN_E0_BLOB,
          "PACKET_E0")
    block(meta.get("admissible_for_gameplay") is False and
          meta.get("next_stage_S5") == "BLOCKED" and
          meta.get("source_owner_status") == "MISSING" and
          meta.get("native_calibration") == "UNVERIFIED" and
          meta.get("stroke_admission") ==
          "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE" and
          meta.get("formal_BPREDS4") == "BLOCKED" and
          meta.get("native_Egret") == "NOT_RUN", "PACKET_PROMOTION")
    block(meta.get("input_sha256") == sha256(original_bytes),
          "PACKET_INPUT_SHA")
    block(meta.get("raw_npz_sha256") == sha256(raw_bytes),
          "PACKET_RAW_SHA")
    with np.load(io.BytesIO(raw_bytes), allow_pickle=False) as data:
        block(set(data.files) == set(ARRAY_TYPES), "PACKET_ARRAY_KEYS")
        desc = meta.get("array_contract", {})
        block(set(desc) == set(ARRAY_TYPES), "PACKET_DESCRIPTOR_KEYS")
        for key in ARRAY_TYPES:
            a = data[key]
            signature = desc[key]
            block(str(a.dtype) == signature.get("dtype") and
                  list(a.shape) == signature.get("shape") and
                  sha256(np.ascontiguousarray(a).tobytes()) ==
                  signature.get("sha256"), "PACKET_ARRAY_SHA_" + key)
    return meta

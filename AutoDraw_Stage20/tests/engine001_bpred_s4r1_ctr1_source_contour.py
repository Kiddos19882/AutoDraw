#!/usr/bin/env python3
"""ENGINE-001 S4.4 CTR1: source pixel-edge contour evidence, RESEARCH_ONLY.

Frozen E0 Git blob 5d0da0694ce0333e9d477fb2fb964329a06763eb
BEFORE code. Source-only original -> fresh DG1 geometry -> source crack
unit-segments. No old masks/PNG/strokes, native brush or gameplay.
"""
from __future__ import annotations

import numpy as np
from skimage import color

import engine001_bpred_s4r1_rag6_edge_topology as validation
import engine001_bpred_s4r1_dg1_source_detail_atoms as original_dg1

VERSION = "ENGINE001_BPRED_S44_CTR1_ORIGINAL_STRONG_SEGMENTS_V1"
E0_SHA1 = "5d0da0694ce0333e9d477fb2fb964329a06763eb"
ORIGINAL_STRONG_LAB = 12.0
REGION_STRONG_DIFFERENT_SWATCH = 1
REGION_STRONG_SAME_SWATCH_DETAIL = 2
TRUE_ALPHA_SILHOUETTE = 3
SEGMENT_FIELDS = (
    "x0", "y0", "x1", "y1", "atom_a", "atom_b",
    "game128_a", "game128_b", "contour_type", "protected_dot_evidence",
)


def _source_crack_segments(
    lab: np.ndarray, opaque: np.ndarray, atom: np.ndarray,
    game: np.ndarray, protected: np.ndarray
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Return true original strong-pair or alpha-wall unit lattice segments.

    Every line is encoded in coordinates of ORIGINAL PIXEL CORNERS, not
    desktop/logical/CSS/PNG or executor positions.
    """
    if (lab.shape != (*opaque.shape, 3)
            or atom.shape != opaque.shape or game.shape != opaque.shape
            or protected.shape != opaque.shape):
        raise ValueError("BLOCKED_CTR1_ORIGINAL_SHAPE")
    if (np.any(atom[~opaque]) or np.any(atom[opaque] <= 0)
            or np.any(game[~opaque] != -1)
            or np.any(game[opaque] < 0) or np.any(game[opaque] > 127)
            or np.any(protected[~opaque])):
        raise ValueError("BLOCKED_CTR1_ORIGINAL_OWNER_ALPHA")

    pieces = []
    distances = []
    summary = {
        "source_original_strong_4neighbor_pairs": 0,
        "represented_original_strong_4neighbor_pairs": 0,
        "unrepresented_within_atom_original_strong_pairs": 0,
        "excluded_weak_quantization_only_pairs": 0,
        "original_alpha_wall_pairs": 0,
        "protected_source_dot_count": int(protected.sum()),
        "protected_dot_true_strong_crack_edges": 0,
    }
    # Pair arrangement: original (a,b) are 4adjacent RGB pixel CENTERS.
    # Crack endpoints (x0,y0,x1,y1) are integer lattice PIXEL CORNERS.
    for orientation, (opa, opb, a_id, b_id, a_swatch, b_swatch,
                      a_dot, b_dot, left, right) in enumerate((
        (opaque[:, :-1], opaque[:, 1:], atom[:, :-1], atom[:, 1:],
         game[:, :-1], game[:, 1:],
         protected[:, :-1], protected[:, 1:],
         lab[:, :-1], lab[:, 1:]),
        (opaque[:-1], opaque[1:], atom[:-1], atom[1:],
         game[:-1], game[1:],
         protected[:-1], protected[1:],
         lab[:-1], lab[1:]),
    )):
        both = opa & opb
        raw_diff = np.linalg.norm(left - right, axis=2)
        strong = both & (raw_diff >= ORIGINAL_STRONG_LAB)
        different_atom = (a_id != b_id)
        captured = strong & different_atom
        same_color = a_swatch == b_swatch
        alpha_wall = opa != opb
        excluded = both & (~strong) & different_atom & (~same_color)

        summary["source_original_strong_4neighbor_pairs"] += int(strong.sum())
        summary["represented_original_strong_4neighbor_pairs"] += int(captured.sum())
        summary["unrepresented_within_atom_original_strong_pairs"] += int(
            (strong & ~different_atom).sum())
        summary["excluded_weak_quantization_only_pairs"] += int(excluded.sum())
        summary["original_alpha_wall_pairs"] += int(alpha_wall.sum())
        summary["protected_dot_true_strong_crack_edges"] += int(
            (captured & (a_dot | b_dot)).sum())

        for kind, hit in (
            (REGION_STRONG_DIFFERENT_SWATCH, captured & ~same_color),
            (REGION_STRONG_SAME_SWATCH_DETAIL, captured & same_color),
            (TRUE_ALPHA_SILHOUETTE, alpha_wall),
        ):
            y, x = np.nonzero(hit)
            if len(y) == 0:
                continue
            m = len(y)
            if orientation == 0:
                x0, y0, x1, y1 = x + 1, y, x + 1, y + 1
            else:
                x0, y0, x1, y1 = x, y + 1, x + 1, y + 1
            typ = np.full(m, kind, dtype=np.int32)
            flags = (a_dot[hit] | b_dot[hit]).astype(np.int32)
            rows = np.column_stack((
                x0, y0, x1, y1,
                a_id[hit], b_id[hit],
                a_swatch[hit], b_swatch[hit],
                typ, flags,
            )).astype(np.int32)
            pieces.append(rows)
            distances.append(
                np.where(kind == TRUE_ALPHA_SILHOUETTE, 0.,
                         raw_diff[hit]).astype(np.float32))

    if pieces:
        records = np.concatenate(pieces, axis=0)
        contrast = np.concatenate(distances)
        # Deterministic original y,x,orientation,type ordering.
        orientation = (records[:, 0] == records[:, 2]).astype(np.int32)
        order = np.lexsort((
            records[:, 8], orientation, records[:, 0], records[:, 1]))
        records, contrast = records[order], contrast[order]
    else:
        records = np.zeros((0, len(SEGMENT_FIELDS)), np.int32)
        contrast = np.zeros(0, np.float32)

    h, w = opaque.shape
    if len(records):
        x0, y0, x1, y1 = (records[:, i] for i in range(4))
        if (np.any(x0 < 0) or np.any(x1 > w) or np.any(y0 < 0)
                or np.any(y1 > h) or
                np.any(np.abs(x1-x0) + np.abs(y1-y0) != 1) or
                np.any((x0 != x1) & (y0 != y1)) or
                np.any(~np.isin(records[:, 8], (1, 2, 3)))):
            raise ValueError("BLOCKED_CTR1_SEGMENTS_NOT_SOURCE_UNIT_CRACK")
        # An alpha wall always carries exactly one opaque original side.
        silhouettes = records[records[:, 8] == TRUE_ALPHA_SILHOUETTE]
        if len(silhouettes):
            if np.any((silhouettes[:, 4] > 0) == (silhouettes[:, 5] > 0)):
                raise ValueError("BLOCKED_CTR1_INVALID_ALPHA_WALL")
            if np.any((silhouettes[:, 6] >= 0) == (silhouettes[:, 7] >= 0)):
                raise ValueError("BLOCKED_CTR1_UNKNOWN_SILHOUETTE_COLOR")

    summary["contour_unit_segment_count"] = int(len(records))
    for category, name in (
        (REGION_STRONG_DIFFERENT_SWATCH,"strong_different_swatch"),
        (REGION_STRONG_SAME_SWATCH_DETAIL,"strong_same_swatch_detail"),
        (TRUE_ALPHA_SILHOUETTE,"alpha_silhouette"),
    ):
        summary["contour_" + name] = int((records[:, 8] == category).sum())
    total = summary["source_original_strong_4neighbor_pairs"]
    summary["original_strong_pair_source_path_fraction"] = (
        summary["represented_original_strong_4neighbor_pairs"] / total
        if total else None)
    if (summary["represented_original_strong_4neighbor_pairs"] !=
            summary["contour_strong_different_swatch"] +
            summary["contour_strong_same_swatch_detail"]):
        raise ValueError("BLOCKED_CTR1_ORIGINAL_STRONG_COUNT")
    if (summary["original_alpha_wall_pairs"] !=
            summary["contour_alpha_silhouette"]):
        raise ValueError("BLOCKED_CTR1_ALPHA_BOUNDARY_COUNT")
    return records, contrast, summary


def build_ctr1(original_rgba: np.ndarray, game128: np.ndarray) -> dict:
    validation._validate(original_rgba, game128)
    # Crucial: whole original source -> FRESH DG1; not a read of old raster art.
    source = original_dg1.build_dg1(original_rgba, game128)
    opaque = original_rgba[..., 3] == 255
    lab = color.rgb2lab(
        original_rgba[..., :3].astype(np.float64) / 255.
    )
    rows, contrast, summary = _source_crack_segments(
        lab, opaque, source["source_atom_id"], source["game_index"],
        source["protected_original_dot"])
    if not np.array_equal(source["preview_rgba"][..., 3], original_rgba[..., 3]):
        raise ValueError("BLOCKED_CTR1_SOURCE_ALPHA_CHANGED")
    # Source original and provisional game swatches retain their own evidence;
    # no source owner or contour is admitted to a native executor.
    return {
        "version": VERSION, "e0_git_blob_sha1": E0_SHA1,
        "provisional_region_baseline": source["version"],
        "source_atom_id": source["source_atom_id"],
        "surface_id": source["surface_id"],
        "protected_original_dot": source["protected_original_dot"],
        "game_index": source["game_index"],
        "paintable_id": source["paintable_id"],
        "baseline_index": source["baseline_index"],
        "source_edge": source["source_edge"],
        "source_original_alpha": original_rgba[..., 3].copy(),
        "preview_rgba": source["preview_rgba"],
        "contour_segments": rows,
        "contour_source_lab": contrast,
        "contour_segment_columns": SEGMENT_FIELDS,
        "contour_summary": summary,
        "source_to_logical": source["source_to_logical"],
        "source_owner_status": "MISSING",
        "stroke_admission": "FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE",
        "provisional_source_quality": "DG1_COLOR_ART125_FAIL_NOT_PROMOTED",
        "native_renderer": "NOT_RUN",
        "game_chalk": "NOT_RUN",
        "counts": source["counts"],
    }

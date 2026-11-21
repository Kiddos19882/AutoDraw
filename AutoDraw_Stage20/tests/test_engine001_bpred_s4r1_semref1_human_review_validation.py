#!/usr/bin/env python3
"""SEMREF1 synthetic tests only. No fake human labels enter real DEV science."""
import hashlib
import io
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from engine001_bpred_s4r1_semref1_human_review_validation import (
    CODES, FORBIDDEN, run, score_pair, sha, source_label_bytes,
)


def fixture():
    rgba = np.zeros((3, 4, 4), dtype=np.uint8)
    rgba[:, :, :3] = (70, 90, 110)
    rgba[:, :, 3] = 255
    decoded = {
        "rgba": rgba,
        "height": 3, "width": 4,
        "sha256": sha(b"test only original"),
        "git_blob_sha1": hashlib.sha1(b"blob test").hexdigest(),
    }
    prot = np.zeros((3, 4), dtype=bool)
    prot[0, 0] = True
    core = np.zeros_like(prot)
    core[1, 1] = True
    source = {
        "owner_status": "MISSING",
        "stroke_admission": FORBIDDEN,
        "source_rgb": rgba[:, :, :3].copy(),
        "source_alpha": rgba[:, :, 3].copy(),
        "protected": prot,
        "unknown": ~prot,
        "candidate_interior": np.zeros_like(prot),
    }
    regions = {
        "source_owner_status": "MISSING",
        "stroke_admission": FORBIDDEN,
        "geometric_potential_core": core,
        "source_rgba_sha256": sha(rgba.tobytes()),
    }
    labels = np.zeros((3, 4, 3), np.uint8)
    labels[0, 0] = CODES[1]
    labels[1, 1] = CODES[3]
    return decoded, source, regions, labels


def pack(labels, decoded, reviewer="r1", **patch):
    image = Image.fromarray(labels, "RGB")
    b = io.BytesIO()
    image.save(b, format="PNG")
    png = b.getvalue()
    sidecar = {
        "reviewer_id": reviewer,
        "source_raw_sha256": decoded["sha256"],
        "source_git_blob_sha1": decoded["git_blob_sha1"],
        "original_rgba_sha256": sha(decoded["rgba"].tobytes()),
        "original_hw": [decoded["height"], decoded["width"]],
        "labels_png_sha256": sha(png),
        "source_only_blind_review": True,
        "annotation_tool_and_version": "synthetic-fixture-v1",
        "review_timestamp": "2026-11-21T11:00:00+00:00",
    }
    sidecar.update(patch)
    return png, sidecar


class SEMREF1SourceReview(unittest.TestCase):
    def test_agreed_critical_and_interior_risk_proxies_only(self):
        d, s, r, labels = fixture()
        out = score_pair(d, s, r, [pack(labels, d, "a"), pack(labels, d, "b")])
        self.assertEqual(out["scientific_status"],
                         "SOURCE_ONLY_HUMAN_ATTESTED_RISK_PROXY_NOT_NATIVE")
        self.assertEqual(out["counts"]["agreed_critical_or_region_boundary"], 1)
        self.assertEqual(out["counts"]["agreed_verified_interior"], 1)
        self.assertEqual(out["counts"]["hypothetical_core_on_reviewed_critical"], 0)
        self.assertEqual(out["counts"]["hypothetical_core_on_reviewed_interior"], 1)
        self.assertEqual(out["protected_recall_on_reviewed_critical"], 1.0)
        self.assertEqual(out["core_fraction_on_reviewed_interior"], 1.0)
        self.assertEqual(out["strict_s4"], "BLOCKED")
        self.assertEqual(out["stroke_admission"], FORBIDDEN)
        self.assertIsNone(out["exact_CHALK"])

    def test_critical_in_hypothetical_core_means_risk_not_admission(self):
        d, s, r, labels = fixture()
        labels[1, 1] = CODES[2]  # critical elsewhere still exists but no interior
        labels[2, 2] = CODES[3]
        out = score_pair(d, s, r, [pack(labels, d, "a"), pack(labels, d, "b")])
        self.assertEqual(out["counts"]["hypothetical_core_on_reviewed_critical"], 1)
        self.assertEqual(out["counts"]["hypothetical_core_on_reviewed_interior"], 0)
        self.assertEqual(out["stroke_admission"], FORBIDDEN)

    def test_missing_support_is_blocked_not_perfect(self):
        d, s, r, labels = fixture()
        labels[1, 1] = CODES[0]
        out = score_pair(d, s, r, [pack(labels, d, "a"), pack(labels, d, "b")])
        self.assertEqual(out["scientific_status"], "BLOCKED_INSUFFICIENT_VERIFIED_SUPPORT")
        self.assertIsNone(out["core_fraction_on_reviewed_interior"])

    def test_disagreement_and_ambiguous_become_unknown(self):
        d, s, r, labels = fixture()
        other = labels.copy()
        other[0, 0] = CODES[4]
        other[1, 1] = CODES[0]
        out = score_pair(d, s, r, [pack(labels, d, "a"), pack(other, d, "b")])
        self.assertEqual(out["counts"]["agreed_critical_or_region_boundary"], 0)
        self.assertEqual(out["counts"]["agreed_verified_interior"], 0)
        self.assertEqual(out["scientific_status"], "BLOCKED_INSUFFICIENT_VERIFIED_SUPPORT")

    def test_color_blend_forbidden_not_silent_relabel(self):
        d, s, r, labels = fixture()
        labels[1, 1] = (0, 254, 0)
        with self.assertRaisesRegex(ValueError, "INVALID_LABEL_COLOR"):
            score_pair(d, s, r, [pack(labels, d, "a"), pack(labels, d, "b")])

    def test_identical_reviewers_forbidden(self):
        d, s, r, labels = fixture()
        with self.assertRaisesRegex(ValueError, "IDENTITIES_NOT_DISTINCT"):
            score_pair(d, s, r, [pack(labels, d, "a"), pack(labels, d, "a")])

    def test_forged_original_hash_forbidden(self):
        d, s, r, labels = fixture()
        with self.assertRaisesRegex(ValueError, "SOURCE_OR_REVIEW_PROVENANCE"):
            score_pair(d, s, r, [pack(labels, d, "a", source_raw_sha256="wrong"),
                                  pack(labels, d, "b")])

    def test_unblinded_or_timezone_missing_forbidden(self):
        d, s, r, labels = fixture()
        for attr in ({"source_only_blind_review": False},
                     {"review_timestamp": "2026-11-21T11:00:00"}):
            with self.assertRaisesRegex(ValueError, "BLOCKED_SEMREF1"):
                score_pair(d, s, r, [pack(labels, d, "a", **attr),
                                      pack(labels, d, "b")])

    def test_source_invariants_fail_closed(self):
        d, s, r, labels = fixture()
        s["candidate_interior"][1, 1] = True
        with self.assertRaisesRegex(ValueError, "SOURCE_UNKNOWN_NOT_ADMISSIBLE"):
            score_pair(d, s, r, [pack(labels, d, "a"), pack(labels, d, "b")])

    def test_non_rgb_png_forbidden(self):
        d, s, r, labels = fixture()
        b = io.BytesIO()
        Image.fromarray(labels[:, :, 0], "L").save(b, format="PNG")
        with self.assertRaisesRegex(ValueError, "LABEL_PNG_MODE"):
            source_label_bytes(b.getvalue(), (3, 4))

    def test_no_human_labels_cannot_score_originals(self):
        root = Path(__file__).resolve().parents[2]
        result = run(root, None)
        self.assertEqual(result["scientific_status"], "BLOCKED_NO_INDEPENDENT_HUMAN_LABELS")
        self.assertEqual(result["records"], [])
        self.assertEqual(result["heldout_outputs"], 0)
        self.assertEqual(result["strict_s4"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()

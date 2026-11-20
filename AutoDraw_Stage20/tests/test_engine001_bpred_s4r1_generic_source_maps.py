#!/usr/bin/env python3
"""E2 contracts for S4R1 original-RGB-only research adapter (not native brush)."""
from __future__ import annotations

import hashlib
import io
import unittest

import numpy as np
from PIL import Image

from engine001_bpred_s4r1_generic_source_maps import (
    decode_original, generic_source_maps, git_blob_sha1, letterbox_binding,
)


def solid(w: int = 17, h: int = 11, rgb=(42, 81, 119)) -> np.ndarray:
    a = np.empty((h, w, 4), dtype=np.uint8)
    a[:, :, :3] = rgb
    a[:, :, 3] = 255
    return a


class GenericSourceMapsTest(unittest.TestCase):
    def test_arbitrary_shapes_and_no_hardcoded_egret_geometry(self):
        for wh in ((1, 1), (17, 11), (64, 43), (3, 127)):
            m = generic_source_maps(solid(*wh))
            self.assertEqual(m["source_rgb"].shape, (wh[1], wh[0], 3))
            self.assertEqual(m["source_to_logical"]["source_wh"], list(wh))
            self.assertEqual(m["source_to_logical"]["target_wh"], list(wh))

    def test_original_rgb_alpha_unmodified(self):
        a = solid()
        a[2:4, 4:7, 3] = 0
        b = a.copy()
        m = generic_source_maps(a)
        self.assertTrue(np.array_equal(a, b))
        self.assertTrue(np.array_equal(m["source_rgb"], a[:, :, :3]))
        self.assertTrue(np.array_equal(m["source_alpha"], a[:, :, 3]))

    def test_no_owner_is_missing_not_invented(self):
        m = generic_source_maps(solid())
        self.assertEqual(m["owner_status"], "MISSING")
        self.assertIsNone(m["owner_index"])
        self.assertFalse(m["candidate_interior"].any())

    def test_known_owner_has_geometric_candidates_but_never_admits_strokes(self):
        a = solid()
        index = np.zeros(a.shape[:2], dtype=np.uint8)
        palette = np.array([[42, 81, 119], [10, 20, 30]], dtype=np.uint8)
        m = generic_source_maps(a, owner_index=index, owner_palette_rgb=palette)
        self.assertGreater(int(m["candidate_interior"].sum()), 0)
        self.assertEqual(m["stroke_admission"], "FORBIDDEN_UNTIL_NATIVE_INDEPENDENT_VALIDATION")
        self.assertTrue(m["unknown"][m["candidate_interior"]].all())

    def test_owner_boundaries_conservatively_protected(self):
        a = solid(23, 19)
        index = np.zeros(a.shape[:2], dtype=np.uint8)
        index[:, 11:] = 1
        palette = np.array([[42, 81, 119], [100, 80, 90]], dtype=np.uint8)
        m = generic_source_maps(a, owner_index=index, owner_palette_rgb=palette)
        self.assertTrue(m["owner_edge"][:, 10:12].all())
        self.assertTrue(m["protected"][:, 10:12].all())
        self.assertEqual(m["owner_rgb"][4, 15].tolist(), [100, 80, 90])

    def test_exact_white_is_protected_not_assumed_to_be_background(self):
        a = solid()
        a[4, 8, :3] = 255
        m = generic_source_maps(a)
        self.assertTrue(m["exact_white_evidence"][4, 8])
        self.assertTrue(m["protected"][4, 8])
        self.assertFalse(m["candidate_interior"][4, 8])

    def test_alpha_and_transparent_are_protected(self):
        a = solid()
        a[2, 3, 3] = 0
        a[4, 5, 3] = 127
        m = generic_source_maps(a)
        self.assertTrue(m["transparent"][2, 3])
        self.assertTrue(m["partial_alpha"][4, 5])
        self.assertTrue(m["protected"][2, 3])
        self.assertTrue(m["protected"][4, 5])

    def test_explicit_white_owner_only_with_palette(self):
        a = solid()
        owner = np.ones(a.shape[:2], np.uint8)
        palette = np.array([[0, 0, 0], [235, 235, 235]], dtype=np.uint8)
        m = generic_source_maps(a, owner_index=owner, owner_palette_rgb=palette,
                                source_white_owner=1)
        self.assertTrue(m["explicit_white_owner"].all())
        with self.assertRaisesRegex(ValueError, "UNBOUND_WHITE_OWNER"):
            generic_source_maps(a, source_white_owner=1)

    def test_invalid_owner_and_palette_fail_closed(self):
        a = solid()
        owner = np.zeros(a.shape[:2], np.uint8)
        palette = np.array([[1, 2, 3]], dtype=np.uint8)
        with self.assertRaisesRegex(ValueError, "PROVENANCE_MISSING"):
            generic_source_maps(a, owner_index=owner)
        owner[0, 0] = 3
        with self.assertRaisesRegex(ValueError, "INVALID_OWNER_PALETTE"):
            generic_source_maps(a, owner_index=owner, owner_palette_rgb=palette)
        with self.assertRaisesRegex(ValueError, "INVALID_ORIGINAL_RGBA"):
            generic_source_maps(a[:, :, :3])

    def test_letterbox_invertible_and_explicit(self):
        v = letterbox_binding((200, 320), (150, 240))
        self.assertEqual(v["content_xywh"], [0, 0, 150, 240])
        f = v["source_to_target_xy"]
        inv = v["target_to_source_xy"]
        x, y = 37.25, 74.5
        xx, yy = f[0][0] * x + f[0][2], f[1][1] * y + f[1][2]
        self.assertAlmostEqual(x, inv[0][0] * xx + inv[0][2])
        self.assertAlmostEqual(y, inv[1][1] * yy + inv[1][2])
        self.assertEqual(letterbox_binding((10, 20), (30, 30))["content_xywh"],
                         [7, 0, 15, 30])
        with self.assertRaisesRegex(ValueError, "COORDINATE_BINDING"):
            letterbox_binding((10, 0))

    def test_flat_image_no_hallucinated_edges(self):
        m = generic_source_maps(solid(rgb=(42, 81, 119)))
        self.assertFalse(m["source_edge"].any())
        self.assertFalse(m["geometric_detail_evidence"].any())
        self.assertGreater(m["counts"]["unknown"], 0)

    def test_detects_original_edge_without_semantic_safety_pretence(self):
        a = solid(32, 24)
        a[:, 15:, :3] = [233, 23, 42]
        m = generic_source_maps(a)
        self.assertGreater(m["counts"]["source_edges"], 0)
        self.assertGreater(m["counts"]["protected"], 0)
        self.assertEqual(m["semantic_detail_status"],
                         "UNKNOWN_NO_VERIFIED_SEMANTIC_MODEL")

    def test_determinism(self):
        a = solid()
        a[3:5, 4:7, :3] = [90, 30, 20]
        b, c = generic_source_maps(a), generic_source_maps(a)
        for k in ("source_rgb", "source_edge", "protected", "unknown",
                  "source_delta_e", "geometric_detail_evidence"):
            self.assertTrue(np.array_equal(b[k], c[k]), k)
        self.assertEqual(b["counts"], c["counts"])

    def test_decode_sha_mode_and_preserve_transparency(self):
        a = solid(9, 7)
        a[4, 5, 3] = 0
        out = io.BytesIO()
        Image.fromarray(a, "RGBA").save(out, "PNG")
        data = out.getvalue()
        r = decode_original(data)
        self.assertEqual(r["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(r["git_blob_sha1"], git_blob_sha1(data))
        self.assertTrue(np.array_equal(r["rgba"], a))
        self.assertEqual(r["original_mode"], "RGBA")

    def test_exif_orientation_decode(self):
        im = Image.new("RGB", (5, 3), (20, 30, 40))
        exif = im.getexif()
        exif[274] = 6
        out = io.BytesIO()
        im.save(out, "JPEG", exif=exif)
        r = decode_original(out.getvalue())
        self.assertEqual((r["width"], r["height"]), (3, 5))
        self.assertEqual(r["exif_orientation"], 6)

    def test_corrupted_data_fail_closed(self):
        for raw in (b"", b"not an image"):
            with self.assertRaises((ValueError, OSError)):
                decode_original(raw)


if __name__ == "__main__":
    unittest.main()

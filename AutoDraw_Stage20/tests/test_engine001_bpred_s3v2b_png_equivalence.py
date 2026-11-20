#!/usr/bin/env python3
"""S3v2b E2 PNG strict ancillary deBG-only comparison."""
from __future__ import annotations

import io
import struct
import unittest
import zlib

import numpy as np
from PIL import Image

import engine001_bpred_s3v2b_png_equivalence as eq


def png_for(test_nonce=b"C7A01DCE0C0A103F"):
    a = np.zeros((720, 1380, 4), np.uint8)
    a[300, 400] = [80, 61, 53, 255]
    raw = io.BytesIO()
    Image.fromarray(a, "RGBA").save(raw, format="PNG")
    png = raw.getvalue()
    end_at = png.rfind(b"\x00\x00\x00\x00IEND")
    assert end_at > 0
    def chunk(t, data):
        return (struct.pack(">I", len(data)) + t + data +
                struct.pack(">I", zlib.crc32(t + data) & 0xffffffff))
    return png[:end_at] + chunk(b"deBG", test_nonce) + png[end_at:]


class BpredS3v2bContracts(unittest.TestCase):
    def test_01_true_nonce_only_equivalent(self):
        a = png_for(b"C7A01DCE0C0A103F")
        b = png_for(b"587A190515BA6635")
        outcome = eq.verify_parent_png_equivalence(a, b)
        self.assertTrue(outcome["allowed_deBG_only"])
        self.assertTrue(outcome["original_RGBA_pixel_exact"])
        self.assertFalse(outcome["raw_byte_identical"])
        self.assertNotEqual(outcome["parent_raw_sha256"], outcome["current_raw_sha256"])

    def test_02_byte_exact_is_valid_with_same_nonce(self):
        a = png_for()
        self.assertTrue(eq.verify_parent_png_equivalence(a, a)["raw_byte_identical"])

    def test_03_changed_idat_is_forbidden(self):
        a = png_for()
        b = bytearray(a)
        p = b.find(b"IDAT")
        self.assertGreater(p, 0)
        b[p + 20] ^= 1
        with self.assertRaisesRegex(ValueError, "BAD_PNG_CRC"):
            eq.verify_parent_png_equivalence(a, bytes(b))

    def test_04_crc_tampering_rejected(self):
        a = bytearray(png_for())
        p = a.find(b"deBG")
        self.assertGreater(p, 0)
        a[p + 4] ^= 1
        with self.assertRaisesRegex(ValueError, "BAD_PNG_CRC"):
            eq.verify_parent_png_equivalence(png_for(), bytes(a))

    def test_05_missing_debg_rejected(self):
        a = png_for()
        start = a.find(b"deBG") - 4
        b = a[:start] + a[start + 28:]
        with self.assertRaisesRegex(ValueError, "DEBG_MUST_BE_UNIQUE|CHUNK_COUNT_CHANGED"):
            eq.verify_parent_png_equivalence(a, b)

    def test_06_multiple_debg_rejected(self):
        a = png_for()
        start = a.find(b"deBG") - 4
        b = a[:start] + a[start:start + 28] + a[start:]
        with self.assertRaisesRegex(ValueError, "DEBG_MUST_BE_UNIQUE"):
            eq.verify_parent_png_equivalence(a, b)

    def test_07_wrong_nonce_length_rejected(self):
        b = png_for(b"SHORT")
        with self.assertRaisesRegex(ValueError, "DEBG_NOT_16_HEX"):
            eq.verify_parent_png_equivalence(png_for(), b)

    def test_08_non_hex_nonce_rejected(self):
        b = png_for(b"ZZZZZZZZZZZZZZZZ")
        with self.assertRaisesRegex(ValueError, "DEBG_NOT_16_HEX"):
            eq.verify_parent_png_equivalence(png_for(), b)

    def test_09_changed_srgb_or_critical_chunks_rejected(self):
        a = png_for()
        b = png_for(b"587A190515BA6635")
        # valid CRC of a modified IHDR means byte mismatch is still blocked
        p = b.find(b"IHDR")
        chunk = bytearray(b[p:p+17])
        chunk[4] = 1
        crc = zlib.crc32(chunk) & 0xffffffff
        b = b[:p] + bytes(chunk) + struct.pack(">I", crc) + b[p+21:]
        with self.assertRaisesRegex(ValueError, "FORBIDDEN_NON_DEBG"):
            eq.verify_parent_png_equivalence(a, b)

    def test_10_invalid_png_rejected(self):
        with self.assertRaisesRegex(ValueError, "INVALID_PNG_SIGNATURE"):
            eq.verify_parent_png_equivalence(b"not-png", png_for())


if __name__ == "__main__":
    unittest.main()

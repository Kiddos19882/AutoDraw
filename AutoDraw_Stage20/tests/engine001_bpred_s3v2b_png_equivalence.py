#!/usr/bin/env python3
"""BPRED-S3v2b pinned E0: compare original real WebGL PNG ignoring only deBG nonce.

Keep every raw PNG untouched, including CRC and nonce. The sole permitted
non-byte-identical chunk is one correct 16-byte uppercase-hex ancillary deBG.
No comparing a Canvas intermediate against WebGL with this equivalence.
"""
from __future__ import annotations

import hashlib
import io
import re
import struct
import zlib

import numpy as np
from PIL import Image


def blocked(reason):
    raise ValueError("BLOCKED_BPRED_S3V2B_" + reason)


def chunks(raw):
    if not isinstance(raw, bytes) or not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        blocked("INVALID_PNG_SIGNATURE")
    pos = 8
    out = []
    while pos < len(raw):
        if pos + 12 > len(raw):
            blocked("TRUNCATED_CHUNK_HEADER")
        n = struct.unpack(">I", raw[pos:pos + 4])[0]
        if n > len(raw) - pos - 12:
            blocked("TRUNCATED_CHUNK_DATA")
        tag = raw[pos + 4:pos + 8]
        if len(tag) != 4 or not all((65 <= k <= 90 or 97 <= k <= 122) for k in tag):
            blocked("INVALID_CHUNK_TAG")
        payload = raw[pos + 8:pos + 8 + n]
        expected = struct.unpack(">I", raw[pos + 8 + n:pos + 12 + n])[0]
        if (zlib.crc32(tag + payload) & 0xffffffff) != expected:
            blocked("BAD_PNG_CRC")
        out.append((tag, payload, raw[pos:pos + 12 + n]))
        pos += 12 + n
    if pos != len(raw) or not out or out[0][0] != b"IHDR" or out[-1][0] != b"IEND":
        blocked("INVALID_CHUNK_SEQUENCE")
    if len([z for z in out if z[0] == b"IHDR"]) != 1 or len(
            [z for z in out if z[0] == b"IEND"]) != 1:
        blocked("DUPLICATE_CRITICAL_CHUNKS")
    if not any(z[0] == b"IDAT" for z in out):
        blocked("MISSING_IDAT")
    if len([z for z in out if z[0] == b"deBG"]) != 1:
        blocked("DEBG_MUST_BE_UNIQUE")
    value = next(z[1] for z in out if z[0] == b"deBG")
    if len(value) != 16 or not re.fullmatch(rb"[0-9A-F]{16}", value):
        blocked("DEBG_NOT_16_HEX")
    return out


def verify_parent_png_equivalence(parent: bytes, current: bytes) -> dict:
    a, b = chunks(parent), chunks(current)
    if len(a) != len(b):
        blocked("CHUNK_COUNT_CHANGED")
    for i, (old, new) in enumerate(zip(a, b)):
        if old[0] != new[0]:
            blocked("CHUNK_ORDER_CHANGED")
        if old[0] != b"deBG" and old[2] != new[2]:
            blocked("FORBIDDEN_NON_DEBG_BYTE_DIFFERENCE")
    def rgba(data):
        with Image.open(io.BytesIO(data)) as image:
            img = image.convert("RGBA")
            if img.size != (1380, 720):
                blocked("NATIVE_BOARD_PHYSICAL_SIZE")
            return np.asarray(img, dtype=np.uint8).copy()
    old = rgba(parent)
    fresh = rgba(current)
    if old.shape != fresh.shape or not np.array_equal(old, fresh):
        blocked("NATIVE_RGBA_NOT_EXACT")
    return {
        "allowed_deBG_only": True,
        "current_raw_sha256": hashlib.sha256(current).hexdigest(),
        "parent_raw_sha256": hashlib.sha256(parent).hexdigest(),
        "raw_byte_identical": bool(parent == current),
        "deBG_nonce_parent": next(z[1].decode("ascii") for z in a if z[0] == b"deBG"),
        "deBG_nonce_current": next(z[1].decode("ascii") for z in b if z[0] == b"deBG"),
        "original_RGBA_pixel_exact": True,
        "IDAT_payload_sha256": hashlib.sha256(
            b"".join(z[1] for z in a if z[0] == b"IDAT")).hexdigest()
    }

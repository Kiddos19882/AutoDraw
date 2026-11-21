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




from engine001_bpred_s4r1_generic_source_maps import (
    PINNED_ENGINE_BLOB_SHA1, PINNED_ENGINE_BYTES,
    provisional_game128_owner_maps,
)


def _engine128_synthetic():
    palette = np.array([
        [i, (i * 17) % 256, (i * 37) % 256] for i in range(128)
    ], dtype=np.uint8)
    palette[6] = [255, 255, 255]
    assert len(np.unique(palette, axis=0)) == 128
    provenance = {
        "engine_git_blob_sha1": PINNED_ENGINE_BLOB_SHA1,
        "engine_bytes": PINNED_ENGINE_BYTES,
        "engine_colors": 128,
        "painter_method": "PainterPopup.createElaborateEasterEggs",
        "swatch_RGB": [
            {"index": i, "RGB": palette[i].tolist()} for i in range(128)
        ],
    }
    return palette, provenance


def _rgba_bytes(rgba):
    b = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(b, "PNG")
    return b.getvalue()


class Owner128ProvisionalBindingTest(unittest.TestCase):
    def test_unbounded_shapes_and_actual_swatch_identity(self):
        palette, prov = _engine128_synthetic()
        for wh in ((1, 1), (29, 11), (5, 41)):
            rgba = solid(*wh, rgb=tuple(palette[20].tolist()))
            raw = _rgba_bytes(rgba)
            proposal = provisional_game128_owner_maps(raw, palette, prov)
            self.assertEqual(proposal["source_wh"], list(wh))
            self.assertEqual(proposal["provisional_owner_index"].shape,
                             (wh[1], wh[0]))
            self.assertTrue((proposal["provisional_owner_index"] == 20).all())
            self.assertEqual(proposal["source_sha256"],
                             hashlib.sha256(raw).hexdigest())
            self.assertEqual(proposal["counts"]["opaque_assigned_provisionally"],
                             wh[0] * wh[1])
            self.assertEqual(proposal["counts"]["proposed_owner_edges"], 0)
            self.assertEqual(proposal["lab_nearest_distance_mean"], 0.0)

    def test_no_forced_32_and_detects_valid_owner_proposal_edges(self):
        palette, prov = _engine128_synthetic()
        rgba = solid(40, 5)
        for x in range(40):
            rgba[:, x, :3] = palette[20 + x]
        proposal = provisional_game128_owner_maps(_rgba_bytes(rgba), palette, prov)
        self.assertEqual(proposal["counts"]["unique_proposed_game_colors"], 40)
        self.assertTrue(proposal["provisional_owner_edge"][:, 1:-1].all())
        self.assertEqual(proposal["source_owner_status"], "MISSING")
        self.assertEqual(proposal["owner_accuracy"],
                         "UNKNOWN_NO_SOURCE_OWNER_GROUND_TRUTH")
        self.assertTrue(proposal["stroke_admission"].startswith("FORBIDDEN"))

    def test_transparent_partial_alpha_unassigned_not_game_color(self):
        palette, prov = _engine128_synthetic()
        rgba = solid(9, 7, rgb=tuple(palette[20].tolist()))
        rgba[2, 3, 3] = 0
        rgba[4, 5, 3] = 127
        original = rgba.copy()
        proposal = provisional_game128_owner_maps(_rgba_bytes(rgba), palette, prov)
        idx = proposal["provisional_owner_index"]
        self.assertEqual(int(idx[2, 3]), -1)
        self.assertEqual(int(idx[4, 5]), -1)
        self.assertEqual(proposal["counts"]["unassigned_nonopaque"], 2)
        self.assertTrue(np.isnan(proposal["lab_nearest_distance"][2, 3]))
        self.assertTrue(np.isnan(proposal["lab_nearest_distance"][4, 5]))
        self.assertTrue(np.array_equal(proposal["provisional_owner_rgb_preview"]
                                       [:, :, 3], original[:, :, 3]))
        self.assertTrue(np.array_equal(proposal["provisional_owner_rgb_preview"]
                                       [2, 3], original[2, 3]))
        self.assertFalse(proposal["provisional_owner_edge"][2, 3])

    def test_all_alpha_unknown_and_no_spurious_owners(self):
        palette, prov = _engine128_synthetic()
        rgba = solid(7, 5)
        rgba[:, :, 3] = 0
        proposal = provisional_game128_owner_maps(_rgba_bytes(rgba), palette, prov)
        self.assertEqual(proposal["counts"]["opaque_assigned_provisionally"], 0)
        self.assertEqual(proposal["counts"]["unique_proposed_game_colors"], 0)
        self.assertFalse(proposal["provisional_owner_edge"].any())
        self.assertTrue((proposal["provisional_owner_index"] == -1).all())
        self.assertIsNone(proposal["lab_nearest_distance_mean"])

    def test_reproducible_and_source_maps_never_admit_proposal(self):
        palette, prov = _engine128_synthetic()
        rgba = solid(31, 21)
        rgba[:, 15:, :3] = palette[45]
        original = rgba.copy()
        raw = _rgba_bytes(rgba)
        a = provisional_game128_owner_maps(raw, palette, prov)
        b = provisional_game128_owner_maps(raw, palette, prov)
        for key in ("provisional_owner_index", "provisional_owner_edge",
                    "provisional_owner_rgb_preview"):
            self.assertTrue(np.array_equal(a[key], b[key]), key)
        self.assertTrue(np.array_equal(rgba, original))
        m = generic_source_maps(rgba)
        self.assertEqual(m["owner_status"], "MISSING")
        self.assertEqual(m["counts"]["candidate_interior"], 0)
        self.assertTrue(m["stroke_admission"].startswith("FORBIDDEN"))

    def test_invalid_palette_and_provenance_fail_closed(self):
        palette, prov = _engine128_synthetic()
        raw = _rgba_bytes(solid(13, 7))
        for corrupt in (
            {**prov, "engine_git_blob_sha1": "0" * 40},
            {**prov, "engine_bytes": 0},
            {**prov, "engine_colors": 32},
            {**prov, "swatch_RGB": prov["swatch_RGB"][:-1]},
        ):
            with self.assertRaisesRegex(ValueError, "UNVERIFIED_GAME128"):
                provisional_game128_owner_maps(raw, palette, corrupt)
        wrong_meta = {**prov, "swatch_RGB": [dict(x) for x in prov["swatch_RGB"]]}
        wrong_meta["swatch_RGB"][20]["RGB"] = [5, 6, 7]
        with self.assertRaisesRegex(ValueError, "PALETTE_METADATA_MISMATCH"):
            provisional_game128_owner_maps(raw, palette, wrong_meta)
        with self.assertRaisesRegex(ValueError, "UNVERIFIED_GAME128"):
            provisional_game128_owner_maps(raw, palette[:32], prov)
        with self.assertRaises((ValueError, OSError)):
            provisional_game128_owner_maps(b"not an image", palette, prov)



from engine001_bpred_s4r1_generic_source_maps import original_source_region_uncertainty


class OriginalSourceRegionUncertaintyTest(unittest.TestCase):
    # Synthetic originals here define independent source truth. No real image
    # owner/semantic label is inferred from the nearest game swatch.
    def test_two_source_regions_edges_protected_and_core_not_safe(self):
        a = solid(88, 48, rgb=(30, 45, 70))
        a[:, 44:, :3] = [235, 30, 50]
        known_truth = np.zeros(a.shape[:2], dtype=np.uint8)
        known_truth[:, 44:] = 1
        source = generic_source_maps(a)
        seg = original_source_region_uncertainty(a, source)
        self.assertEqual(seg["region_ids"].shape, (48, 88))
        self.assertEqual(seg["counts"]["opaque"], 88 * 48)
        self.assertGreater(seg["counts"]["regions"], 0)
        self.assertGreater(seg["counts"]["geometric_potential_core"], 0)
        self.assertFalse(seg["geometric_potential_core"][:, 42:46].any())
        self.assertTrue((seg["source_region_warning"] |
                         source["protected"])[:, 43:45].all())
        self.assertEqual(seg["source_owner_status"], "MISSING")
        self.assertEqual(seg["region_owner_accuracy"],
                         "UNKNOWN_NO_INDEPENDENT_REAL_SOURCE_LABELS")
        self.assertEqual(seg["stroke_admission"],
                         "FORBIDDEN_UNTIL_NATIVE_INDEPENDENT_VALIDATION")
        self.assertTrue(source["unknown"][
            seg["geometric_potential_core"]].all())
        self.assertTrue(np.array_equal(known_truth[:, :43], 0 * known_truth[:, :43]))
        self.assertTrue(np.array_equal(known_truth[:, 45:], np.ones_like(known_truth[:, 45:])))

    def test_alpha_holes_excluded_and_source_untouched(self):
        a = solid(64, 48, rgb=(63, 77, 99))
        a[15:28, 19:35, 3] = 0
        a[6, 12, 3] = 126
        original = a.copy()
        source = generic_source_maps(a)
        seg = original_source_region_uncertainty(a, source)
        self.assertFalse(seg["region_ids"][15:28, 19:35].any())
        self.assertEqual(int(seg["region_ids"][6, 12]), 0)
        self.assertFalse(seg["geometric_potential_core"][15:28, 19:35].any())
        self.assertFalse(seg["geometric_potential_core"][6, 12])
        self.assertTrue(np.array_equal(a, original))
        self.assertTrue(np.array_equal(
            seg["source_medoids_preview_rgba"][15:28, 19:35], a[15:28, 19:35]
        ))
        self.assertTrue(np.array_equal(
            seg["source_medoids_preview_rgba"][:, :, 3], a[:, :, 3]
        ))
        self.assertEqual(seg["counts"]["opaque"], 64 * 48 - (28-15)*(35-19)-1)

    def test_every_medoid_is_a_true_pixel_of_its_own_source_region(self):
        a = solid(51, 35, rgb=(35, 78, 109))
        a[:, 16:33, :3] = [185, 111, 54]
        a[:, 33:, :3] = [20, 35, 70]
        a[5:11, 3:10, :3] = [255, 255, 255]
        seg = original_source_region_uncertainty(a, generic_source_maps(a))
        present = np.unique(seg["region_ids"])
        self.assertEqual(present.tolist(), list(range(1, len(present) + 1)))
        for entry in seg["representatives"]:
            x, y = entry["source_pixel_xy"]
            label = entry["region_id"]
            self.assertEqual(int(seg["region_ids"][y, x]), label)
            self.assertEqual(a[y, x, :3].tolist(), entry["source_rgb"])
            self.assertEqual(int(np.count_nonzero(seg["region_ids"] == label)),
                             entry["pixels"])
        original_colors = set(map(tuple, a[:, :, :3].reshape(-1, 3).tolist()))
        medoid_colors = set(map(tuple, seg[
            "source_medoids_preview_rgba"][:, :, :3].reshape(-1, 3).tolist()))
        self.assertTrue(medoid_colors.issubset(original_colors))

    def test_thin_original_source_line_produces_warning_without_semantic_claim(self):
        a = solid(61, 57, rgb=(216, 202, 179))
        a[28, 7:54, :3] = [18, 24, 36]
        source = generic_source_maps(a)
        seg = original_source_region_uncertainty(a, source)
        self.assertGreater(int(source["source_edge"].sum()), 0)
        self.assertTrue(np.all(seg["source_region_warning"][
            source["source_edge"] & (a[:, :, 3] == 255)]))
        self.assertFalse(seg["geometric_potential_core"][
            source["source_edge"]].any())
        self.assertEqual(seg["semantic_detail_status"],
                         "UNKNOWN_NO_VERIFIED_SEMANTIC_MODEL")

    def test_deterministic_region_labels_and_preview(self):
        a = solid(38, 26)
        a[:, 20:, :3] = [240, 35, 22]
        a[8:17, 4:13, :3] = [30, 190, 45]
        original = a.copy()
        source = generic_source_maps(a)
        x = original_source_region_uncertainty(a, source)
        y = original_source_region_uncertainty(a, source)
        for key in ("region_ids", "source_medoids_preview_rgba",
                    "region_boundary", "region_color_uncertain",
                    "source_region_warning", "geometric_potential_core"):
            self.assertTrue(np.array_equal(x[key], y[key]), key)
        self.assertEqual(x["counts"], y["counts"])
        self.assertTrue(np.array_equal(original, a))
        self.assertEqual(x["source_rgba_sha256"],
                         hashlib.sha256(a.tobytes()).hexdigest())

    def test_empty_alpha_yields_zero_regions_and_zero_core(self):
        a = solid(17, 13)
        a[:, :, 3] = 0
        s = original_source_region_uncertainty(a, generic_source_maps(a))
        self.assertEqual(s["counts"]["regions"], 0)
        self.assertEqual(s["counts"]["geometric_potential_core"], 0)
        self.assertEqual(s["segmentation_method"], "NO_OPAQUE_SOURCE_PIXELS")
        self.assertEqual(s["representatives"], [])
        self.assertTrue(np.array_equal(s["source_medoids_preview_rgba"], a))

    def test_small_and_narrow_shapes_fail_closed_with_alpha_component_fallback(self):
        for wh in ((1, 1), (1, 23), (2, 3), (7, 2)):
            a = solid(*wh)
            src = generic_source_maps(a)
            s = original_source_region_uncertainty(a, src)
            self.assertEqual(s["region_ids"].shape, (wh[1], wh[0]))
            self.assertTrue((s["region_ids"] > 0).all())
            self.assertTrue(s["stroke_admission"].startswith("FORBIDDEN"))

    def test_wrong_source_provenance_and_true_owner_binding_rejected(self):
        a = solid(23, 19)
        source = generic_source_maps(a)
        mutated = a.copy()
        mutated[2, 4, :3] = [255, 0, 10]
        with self.assertRaisesRegex(ValueError, "ORIGINAL_RGB_ALPHA_MISMATCH"):
            original_source_region_uncertainty(mutated, source)
        corrupt = dict(source)
        corrupt["candidate_interior"] = np.ones(a.shape[:2], dtype=bool)
        with self.assertRaisesRegex(ValueError, "UNSAFE_SOURCE_MASK"):
            original_source_region_uncertainty(a, corrupt)
        owner = np.zeros(a.shape[:2], dtype=np.int16)
        palette = np.array([[42, 81, 119]], dtype=np.uint8)
        source_bound = generic_source_maps(a, owner_index=owner,
                                           owner_palette_rgb=palette)
        with self.assertRaisesRegex(ValueError, "INPUT_PROVENANCE"):
            original_source_region_uncertainty(a, source_bound)



from engine001_bpred_s4r1_generic_source_maps import (
    original_alpha_interface_reference,
)


class OriginalAlphaReferenceTest(unittest.TestCase):
    def test_opaque_side_alpha0_and_partial_reference_exact_four_neighbors(self):
        # No RGB contrast: source Sobel/DeltaE alone cannot identify alpha-only edges.
        rgba = solid(11, 11, rgb=(80, 90, 100))
        rgba[3, 3, 3] = 0
        rgba[7, 7, 3] = 127
        original = rgba.copy()
        maps = generic_source_maps(rgba)
        expected = np.zeros((11, 11), dtype=bool)
        for y, x in ((2, 3), (3, 2), (3, 4), (4, 3),
                     (6, 7), (7, 6), (7, 8), (8, 7)):
            expected[y, x] = True
        self.assertTrue(np.array_equal(maps["alpha_opaque_interface"], expected))
        self.assertFalse(maps["source_edge"].any())
        self.assertTrue(maps["protected"][expected].all())
        self.assertFalse(maps["unknown"][expected].any())
        self.assertEqual(maps["counts"]["alpha_opaque_interface"], 8)
        ref = original_alpha_interface_reference(rgba, maps)
        self.assertEqual(ref["alpha_reference_status"],
                         "PASS_ALPHA_SOURCE_REFERENCE_ONLY")
        self.assertEqual(ref["invalid_pixels"], 2)
        self.assertEqual(ref["invalid_protected_pixels"], 2)
        self.assertEqual(ref["opaque_interface_pixels"], 8)
        self.assertEqual(ref["opaque_interface_protected_pixels"], 8)
        self.assertEqual(ref["opaque_interface_unprotected_pixels"], 0)
        self.assertTrue(np.array_equal(original, rgba))
        self.assertEqual(maps["owner_status"], "MISSING")
        self.assertEqual(maps["counts"]["candidate_interior"], 0)
        self.assertTrue(ref["stroke_admission"].startswith("FORBIDDEN"))

    def test_diagonal_is_not_alpha_interface(self):
        rgba = solid(5, 5)
        rgba[1, 1, 3] = 0
        m = generic_source_maps(rgba)
        mask = m["alpha_opaque_interface"]
        self.assertTrue(mask[0, 1] and mask[1, 0] and
                        mask[1, 2] and mask[2, 1])
        self.assertFalse(mask[2, 2])
        self.assertEqual(int(mask.sum()), 4)
        self.assertEqual(original_alpha_interface_reference(rgba, m)[
            "opaque_interface_pixels"], 4)

    def test_reference_detects_tampered_opaque_side_but_not_pseudo_semantics(self):
        rgba = solid(15, 13)
        rgba[5, 5, 3] = 0
        m = generic_source_maps(rgba)
        tampered = dict(m)
        tampered["protected"] = m["protected"].copy()
        tampered["protected"][5, 6] = False
        bad = original_alpha_interface_reference(rgba, tampered)
        self.assertEqual(bad["alpha_reference_status"],
                         "FAIL_ALPHA_INTERFACE_SOURCE_PROTECTION")
        self.assertGreater(bad["opaque_interface_unprotected_pixels"], 0)
        self.assertEqual(bad["source_owner_accuracy"],
                         "UNKNOWN_NO_INDEPENDENT_OWNER_LABELS")
        self.assertEqual(bad["semantic_recall"],
                         "NOT_READY_NO_INDEPENDENT_SEMANTIC_LABELS")

    def test_no_alpha_is_na_not_success(self):
        rgba = solid(13, 9)
        ref = original_alpha_interface_reference(rgba, generic_source_maps(rgba))
        self.assertEqual(ref["alpha_reference_status"],
                         "NOT_APPLICABLE_FULLY_OPAQUE_NO_ALPHA_REFERENCE")
        self.assertIsNone(ref["invalid_protected_fraction"])
        self.assertIsNone(ref["interface_protected_fraction"])
        self.assertEqual(ref["opaque_interface_pixels"], 0)

    def test_all_nonopaque_is_na_not_success(self):
        rgba = solid(9, 7)
        rgba[:, :, 3] = 50
        m = generic_source_maps(rgba)
        ref = original_alpha_interface_reference(rgba, m)
        self.assertEqual(ref["alpha_reference_status"],
                         "NOT_APPLICABLE_NO_OPAQUE_SIDE")
        self.assertEqual(ref["invalid_protected_fraction"], 1)
        self.assertEqual(ref["opaque_interface_pixels"], 0)
        self.assertEqual(m["counts"]["candidate_interior"], 0)

    def test_reference_detects_source_and_region_provenance_mismatch(self):
        rgba = solid(17, 11)
        rgba[3, 3, 3] = 0
        m = generic_source_maps(rgba)
        regions = original_source_region_uncertainty(rgba, m)
        good = original_alpha_interface_reference(rgba, m, regions)
        self.assertEqual(good["alpha_reference_status"],
                         "PASS_ALPHA_SOURCE_REFERENCE_ONLY")
        self.assertEqual(good["opaque_interface_in_diagnostic_core"], 0)
        altered = rgba.copy()
        altered[2, 2, :3] = [1, 20, 200]
        with self.assertRaisesRegex(ValueError, "ORIGINAL_MISMATCH"):
            original_alpha_interface_reference(altered, m, regions)
        bad_region = dict(regions)
        bad_region["source_rgba_sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "REGION_MISMATCH"):
            original_alpha_interface_reference(rgba, m, bad_region)


class SourceKnownEgretSKC1Test(unittest.TestCase):
    """Synthetic archive-shape/source integrity tests: not native Egret E3."""

    @staticmethod
    def sample(wh=(19, 11), method="E_SOBEL90"):
        from engine001_bpred_s4r1_generic_source_maps import (
            SOURCE_KNOWN_EGRET_ARTIFACT_SHA256,
            SOURCE_KNOWN_EGRET_RENDERER_BLOB,
        )
        palette, engine = _engine128_synthetic()
        original = solid(*wh)
        owner = np.full((wh[1], wh[0]), 20, dtype=np.uint8)
        rgb = palette[owner].copy()
        attrs = {
            "source_kind": "ORIGINAL_P4D18_EF_LOGICAL",
            "artifact_id": 14557770111,
            "archive_sha256": SOURCE_KNOWN_EGRET_ARTIFACT_SHA256,
            "method": method,
            "engine_git_blob_sha1": PINNED_ENGINE_BLOB_SHA1,
            "renderer_git_blob_sha1": SOURCE_KNOWN_EGRET_RENDERER_BLOB,
            "archive_members_verified": True,
            "original_rgba_sha256": hashlib.sha256(original.tobytes()).hexdigest(),
            "owner_index_sha256": hashlib.sha256(owner.tobytes()).hexdigest(),
            "owner_rgb_sha256": hashlib.sha256(rgb.tobytes()).hexdigest(),
            "game128_sha256": hashlib.sha256(palette.tobytes()).hexdigest(),
        }
        return original, owner, rgb, palette, engine, attrs

    def call(self, fixture):
        from engine001_bpred_s4r1_generic_source_maps import (
            source_known_egret_protection_contract,
        )
        return source_known_egret_protection_contract(*fixture)

    def test_true_source_index_stays_unknown_for_strokes(self):
        for method in ("E_SOBEL90", "F_SOBEL90_LAB12"):
            f = self.sample((21, 13), method)
            result = self.call(f)
            self.assertEqual(result["source_wh"], [21, 13])
            self.assertTrue(result["unknown"][result["candidate_interior"]].all())
            self.assertGreater(result["counts"]["candidate_interior"], 0)
            self.assertEqual(result["stroke_admission"],
                             "FORBIDDEN_UNTIL_NATIVE_INDEPENDENT_VALIDATION")
            self.assertEqual(result["scientific_s4"], "BLOCKED")
            self.assertEqual(result["semantic_detail_status"],
                             "UNKNOWN_NO_VERIFIED_CRITICAL_SEMANTICS")

    def test_source_owner_border_and_explicit_white_not_generic_background(self):
        f = list(self.sample())
        f[1][:, 9:] = 31
        f[1][2, 2] = 6
        f[2] = f[3][f[1]].copy()
        f[5] = dict(f[5])
        f[5]["owner_index_sha256"] = hashlib.sha256(f[1].tobytes()).hexdigest()
        f[5]["owner_rgb_sha256"] = hashlib.sha256(f[2].tobytes()).hexdigest()
        result = self.call(f)
        self.assertTrue(result["owner_edge"][:, 8:10].all())
        self.assertTrue(result["protected"][:, 8:10].all())
        self.assertTrue(result["owner_white"][2, 2])
        self.assertTrue(result["protected"][2, 2])
        self.assertFalse(result["exact_white"][2, 2])

    def test_original_rgb_four_neighbor_contrast_not_owner_nearest_lab(self):
        f = list(self.sample((7, 7)))
        f[0][3, 3, :3] = [255, 0, 0]
        f[5] = dict(f[5])
        f[5]["original_rgba_sha256"] = hashlib.sha256(f[0].tobytes()).hexdigest()
        result = self.call(f)
        self.assertEqual(result["counts"]["original_rgb_strong_contrast"], 5)
        self.assertTrue(result["protected"][3, 3])
        self.assertTrue(result["original_rgb_strong_contrast"][3, 2])
        self.assertFalse(result["original_rgb_strong_contrast"][2, 2])

    def test_original_exact_white_transparency_and_owner_white_independent(self):
        f = list(self.sample())
        f[0][4, 4, :3] = 255
        f[0][3, 2, 3] = 0
        f[0][3, 3, 3] = 75
        f[5] = dict(f[5])
        f[5]["original_rgba_sha256"] = hashlib.sha256(f[0].tobytes()).hexdigest()
        frozen = [item.copy() for item in f[:4]]
        result = self.call(f)
        self.assertTrue(result["exact_white"][4, 4])
        self.assertFalse(result["owner_white"][4, 4])
        self.assertTrue(result["protected"][3, 2])
        self.assertTrue(result["protected"][3, 3])
        self.assertTrue(result["alpha_opaque_interface"][2, 2])
        for item, original in zip(f[:4], frozen):
            self.assertTrue(np.array_equal(item, original))

    def test_bad_shape_or_owner_rgb_blocked(self):
        f = list(self.sample())
        f[2][0, 0, 1] ^= 1
        with self.assertRaisesRegex(ValueError, "OWNER_RGB_PALETTE_MISMATCH"):
            self.call(f)
        f = list(self.sample())
        f[1] = f[1][:, :-1]
        with self.assertRaisesRegex(ValueError, "OWNER_SHAPE_OR_MODE"):
            self.call(f)

    def test_archive_method_source_hash_and_engine_forgery_blocked(self):
        for key, bad in (("method", "HIDDEN_HELDOUT"),
                         ("archive_sha256", "0" * 64),
                         ("archive_members_verified", False),
                         ("owner_index_sha256", "0" * 64),
                         ("original_rgba_sha256", "0" * 64)):
            f = list(self.sample())
            f[5] = dict(f[5], **{key: bad})
            with self.assertRaisesRegex(ValueError, "SOURCE_PROVENANCE_OR_HASH"):
                self.call(f)
        f = list(self.sample())
        f[4] = dict(f[4], engine_git_blob_sha1="0" * 40)
        with self.assertRaisesRegex(ValueError, "GAME128_PROVENANCE"):
            self.call(f)

    def test_non_128_palette_and_unverified_provisional_owner_rejected(self):
        f = list(self.sample())
        f[3] = f[3][:32]
        with self.assertRaisesRegex(ValueError, "GAME128_PROVENANCE"):
            self.call(f)
        f = list(self.sample())
        f[1][0, 0] = 200
        with self.assertRaisesRegex(ValueError, "OWNER_RGB_PALETTE_MISMATCH"):
            self.call(f)


if __name__ == "__main__":
    unittest.main()

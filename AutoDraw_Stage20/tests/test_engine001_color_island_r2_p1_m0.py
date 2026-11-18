"""R2-P1 M0 synthetic contracts. No NN features, game painting or tuning."""
import unittest
import numpy as np
from skimage import color
from run_engine001_color_island_r2_p1_m0 import (
    SHAPE, validate_source, detail_protection, merge_one_pass,
    render_source_medoids, partition, _area_hist, _de,
)


class R2P1MathContracts(unittest.TestCase):
    def setup_regions(self, target=(75, 71, 69), source=None):
        image = np.full((*SHAPE, 3), 255, np.uint8)
        labels = np.full(SHAPE, -1, np.int32)
        image[120:132, 50:62] = target
        labels[120:132, 50:62] = 0
        image[123:125, 62:64] = target if source is None else source
        labels[123:125, 62:64] = 1
        coarse = np.zeros(SHAPE, np.int32)
        protected = np.zeros(SHAPE, bool)
        return image, labels, coarse, protected

    def test_r2_source_arrays_fail_closed(self):
        rgb = np.zeros((*SHAPE, 3), np.uint8)
        valid = np.array([[i, i + 1, i + 2] for i in range(32)], np.uint8)
        valid[30] = 255
        validate_source(rgb, valid)
        with self.assertRaisesRegex(ValueError, "BLOCKED_R2_P1"):
            validate_source(rgb.astype(np.float32), valid)
        with self.assertRaisesRegex(ValueError, "BLOCKED_R2_P1"):
            validate_source(rgb, valid[:31])
        with self.assertRaisesRegex(ValueError, "BLOCKED_R2_P1"):
            validate_source(rgb, np.zeros((32, 3), np.uint8))

    def test_false_pink_not_generated_from_dark_source(self):
        source, labels, coarse, prot = self.setup_regions()
        merged, info = merge_one_pass(source, labels, coarse, prot)
        output = render_source_medoids(source, merged, labels == -1)
        self.assertEqual(info["merged_regions"], 1)
        self.assertEqual(int(info["changed_pixels"]), 4)
        np.testing.assert_array_equal(output[123:125, 62:64], source[123:125, 62:64])
        self.assertFalse(np.any(np.all(output == [255, 0, 255], axis=2)))

    def test_true_tiny_pink_detail_is_not_absorbed(self):
        source, labels, coarse, prot = self.setup_regions(source=(245, 60, 160))
        merged, info = merge_one_pass(source, labels, coarse, prot)
        np.testing.assert_array_equal(merged, labels)
        self.assertEqual(info["merged_regions"], 0)
        out = render_source_medoids(source, merged, labels == -1)
        np.testing.assert_array_equal(out[123:125, 62:64], source[123:125, 62:64])
        self.assertTrue(any("SOURCE_COLOR" in x for x in info["ledger"][0]["reason_counts"]))

    def test_original_protected_eye_pixel_blocks_merge(self):
        source, labels, coarse, prot = self.setup_regions()
        prot[123, 62] = True
        merged, info = merge_one_pass(source, labels, coarse, prot)
        np.testing.assert_array_equal(merged, labels)
        self.assertTrue(any(x.get("status") == "KEEP_SOURCE_PROTECTED" for x in info["ledger"]))

    def test_protected_seam_blocks_merge(self):
        source, labels, coarse, prot = self.setup_regions()
        prot[123, 61] = True
        merged, info = merge_one_pass(source, labels, coarse, prot)
        np.testing.assert_array_equal(merged, labels)
        self.assertEqual(info["merged_regions"], 0)

    def test_narrow_diagonal_seed_remains(self):
        source, labels, coarse, prot = self.setup_regions()
        source[123:125, 62:64] = [30, 30, 30]
        prot[123, 62] = True
        prot[124, 63] = True
        merged, _ = merge_one_pass(source, labels, coarse, prot)
        np.testing.assert_array_equal(merged[123:125, 62:64], labels[123:125, 62:64])

    def test_cross_coarse_distinct_source_colors_blocked(self):
        source, labels, coarse, prot = self.setup_regions(target=(75, 71, 69), source=(82, 79, 73))
        coarse[123:125, 62:64] = 1
        merged, info = merge_one_pass(source, labels, coarse, prot)
        np.testing.assert_array_equal(merged, labels)
        self.assertEqual(info["merged_regions"], 0)

    def test_merge_contact_minimum_enforced(self):
        source, labels, coarse, prot = self.setup_regions()
        labels[124, 62] = -1
        merged, info = merge_one_pass(source, labels, coarse, prot)
        self.assertEqual(info["merged_regions"], 0)
        np.testing.assert_array_equal(merged, labels)

    def test_unconnected_white_highlight_preserved(self):
        source = np.full((*SHAPE, 3), 255, np.uint8)
        source[30:190, 20:130] = [78, 68, 66]
        source[70:73, 70:73] = 255
        palette = np.array([(i*7 % 255, i*11 % 255, i*13 % 255) for i in range(32)], np.uint8)
        palette[30] = [255, 255, 255]
        labels, bg, coarse, info = partition(source, palette)
        self.assertTrue(bg[0, 0])
        self.assertFalse(bg[71, 71], "Enclosed white highlight must not become background")
        self.assertGreaterEqual(labels[71, 71], 0)
        self.assertEqual(int(info["foreground_pixels"] + info["background_pixels"]), 36000)
        self.assertTrue(np.all(labels[~bg] >= 0))

    def test_detail_seed_or_strong_edge_on_real_pink(self):
        source = np.full((*SHAPE, 3), 75, np.uint8)
        source[60:75, 60:75] = [230, 60, 140]
        protected, info, strong, seeds = detail_protection(source)
        self.assertGreater(int(protected.sum()), 0)
        self.assertTrue(bool(protected[60, 65] or protected[59, 65]))
        self.assertTrue(np.all(protected[strong]))
        self.assertTrue(np.all(protected[seeds]))

    def test_render_merged_uses_source_member_rgb(self):
        rgb, labels, coarse, prot = self.setup_regions()
        merged, _ = merge_one_pass(rgb, labels, coarse, prot)
        out = render_source_medoids(rgb, merged, labels == -1)
        all_rgb = {tuple(x) for x in rgb.reshape(-1, 3)}
        self.assertTrue(all(tuple(x) in all_rgb for x in np.unique(out.reshape(-1,3), axis=0)))
        np.testing.assert_array_equal(out[labels == -1], rgb[labels == -1])

    def test_region_stats_gap_after_merge_and_areas(self):
        rgb, labels, coarse, prot = self.setup_regions()
        merged, _ = merge_one_pass(rgb, labels, coarse, prot)
        self.assertEqual(_area_hist(merged)["count"], 1)
        self.assertEqual(_area_hist(labels)["count"], 2)
        result = render_source_medoids(rgb, merged, labels == -1)
        self.assertEqual(result.shape, rgb.shape)

    def test_source_color_comparison_symmetry(self):
        a = color.rgb2lab(np.array([[[75, 71, 69]]], dtype=np.float64)/255.)[0,0]
        b = color.rgb2lab(np.array([[[81, 72, 70]]], dtype=np.float64)/255.)[0,0]
        self.assertAlmostEqual(_de(a, b), _de(b, a), places=8)

    def test_invalid_region_arrays_fail_closed(self):
        rgb, labels, coarse, prot = self.setup_regions()
        with self.assertRaisesRegex(ValueError, "BLOCKED_R2_P1"):
            merge_one_pass(rgb, labels.astype(np.int16), coarse, prot)
        with self.assertRaisesRegex(ValueError, "BLOCKED_R2_P1"):
            merge_one_pass(rgb, labels, coarse, prot.astype(np.uint8))


if __name__ == "__main__":
    unittest.main()
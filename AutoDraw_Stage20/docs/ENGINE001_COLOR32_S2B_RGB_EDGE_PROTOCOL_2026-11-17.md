# ENGINE-001 / COLOR32-S2b — проверка качества цветовых областей по исходным RGB-границам

**Дата регистрации:** 2026-11-17. **Статус:** E0 preregistration, before running S2b. **Parent task:** ENGINE-001 / V43-P4. **Baseline remote HEAD:** `c9a27a0962b7b7e4a772f6ac2dc01b4d1a888bc2`, branch `feature/image-geometry-optimization`. Frozen earlier S1, PAL32-V1, S2 protocols and negative output MUST NOT be overwritten.

## Research question

S2's index-boundary score saturated around 100%, causing its frozen acceptance gate to FAIL even though source RGB gradient agreement improved. S2b is a **separate** source-only comparison using S1's historical RGB Sobel definition as **primary**. Does conservative source-edge protection reduce the region count without losing the recognizable RGB structure? No claims about Egret, brush, or game CHALK.

## Frozen input and variants

Same original `testImages/wV6VeZI9S1Y.png` SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`, LANCZOS ROI 150×240. Same exactly32 real swatches from `data/palettes/browser_palette.json`, Git blob `461b5f3725b9b79888ad36e807b3cf4c9e445e98`. B=direct nearest CIEDE2000; E=PAL32 frozen tiny 4-component merge, area<=8, extra ΔE00<=5, 2 passes; G=S2 conservative whole-component reject when ANY candidate pixel lies in skimage Sobel(rgb2gray(source/255.0)) top10% positive source gradient. No modifications to algorithms B/E/G from their already registered code, no parameter sweep or new segmentation proposals in S2b.

## Primary metric (exact S1-compatible implementation)

`normalized_source_gradient`: cv2.cvtColor RGB→GRAY float32/255; cv2.Sobel(gray, CV_32F, dx1,dy0/ dx0,dy1, ksize3)/8; hypot. For source and mapped RGB **separately**, threshold gradient `>= np.percentile(gradient,90)` including zeros. Define `RGB_edge_overlap_percent=100 * count(hard_source & hard_mapped) / max(1,count(hard_source))`. This matches S1 formula but inputs B/E/G inherit the PAL32 study; do not assert other S1 fields bit-identical. Store also S2 index-boundary overlap as diagnostic only.

## Frozen source gates

For source-only candidate G, all must hold:
1. Edge recovery `G_RGB - E_RGB >= max(0.875 percentage points, 0.5 * max(0, B_RGB - E_RGB))`. This explicitly targets >=50% recovery of historical approx 1.75pp loss, without changing the failed S2 gate.
2. G 4-connected component reduction against B `>=35%` (all color classes, independent of the 1838 Egret contours).
3. G mean CIEDE2000 color error `<= E_mean + 0.1`.
4. G changes no pixel protected by source strong-edge mask and all mapped pixels are one of the original32 palette RGB values.
5. All B/E/G metrics must be deterministic in repeated runs; hashes and exact frozen source/palette checked; original source input and masks preserved.

**A passed source gate cannot be promoted to native/image quality PASS.** Visual review of original vs B/E/G (with and without archived original 410 true Egret V44-B detail overlay) explicitly examines eyes, hands, faces, hair, clothing boundaries, enclosed white and external white background. If this review fails or is unavailable, `VISUAL_PENDING`; E3 NOT_RUN. No auto-selection based only on numeric edge score.

## Execution and evidence

New self-contained report+PNG-producing offline runner reuses both PAL32-V1 and S2 source functions; build three RGB PNGs, index maps, strong-edge mask, comparison sheet, JSON report with all metrics/source SHA/palette SHA/run version and per-file SHA256. Write to new nonexisting output only, never overwrite frozen output. Unit tests verify exact S1 gradient control, pixel protection, source/palette provenance, error gates, and negative fixture. New isolated GitHub Actions workflow on working branch; source CI job success E2 is separated from `SOURCE_GATE_PASS`. Verify jobs, SHA, uploaded artifacts and report hashes, then freeze explicit PASS/FAIL or UNKNOWN.

## Scope limits

No production, Stage6 executor, Game Monitor, Bridge, painter defaults, palette swatches or original V44-B 410 contours modified. Real round brush/native Egret E3, gameplay E4, independent E5, exact run-bound `post.pointCount-pre.pointCount` and calibration are **NOT_RUN**. Preserve 3 logical px foreign/exterior tolerance, >=99% per-owner Egret coverage, <=3000 strokes and <=5900 synthetic vertices for a later *separately registered* fill experiment. Any threshold modification after results needs another ID.

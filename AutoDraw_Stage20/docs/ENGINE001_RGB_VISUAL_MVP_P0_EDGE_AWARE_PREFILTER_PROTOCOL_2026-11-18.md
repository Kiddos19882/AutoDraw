# ENGINE-001 / RGB-VISUAL-MVP-P0 — edge-aware original prefilter (2026-11-18)

**Experiment ID:** `ENGINE001_RGB_VISUAL_MVP_P0_EDGE_AWARE_PREFILTER`. **Registered before candidate measurement.** Scope: experimental/source-only; no production, `master`, palette replacement, game round-brush claims, Stage6, Monitor, Bridge or CHALK changes. Source `AutoDraw_Stage20/testImages/wV6VeZI9S1Y.png`, original 200×320 PNG SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`. Baseline color reference: archived M1 `44216262024`, artifact `14388687061` SHA256 `8bedc496bf01cf7205ecc8ceb7be8eb0f68b751b11c53ea67dbdd3982c7fe583`, `original_RGB.png` at logical 150×240 and `M1_MERGED_RGB.png` frozen. Detail guard from `source_protected_union.png` in that archive, an unmodified 150×240 boolean mask. Native original V44-B contour: run `43813812976` artifact `14201581692` SHA256 `43cb8e14a7e387b26772612ac06d1c7c6f176b8bd0c2d41e8945042fc80304a1`; `B/V44-B-color-100.png` SHA256 `0145975e4578bc86c1e4feb44d5ff93ecd486d576faf97626e1267a5c12b0275`, native backing 1380×720, ROI x465..914. Contour has original 410 strokes /1792 vertices, held exactly immutable.

## Hypothesis and independent controls

**Problem:** original-first SLIC M1 renders initially coarse regions; original faces/colors become unrecognizable; existing 410 strokes on top do not repair lost color information. **H1:** smooth source RGB gently *before* regional quantization and restore protected originals at logical resolution, so residual RGB structure/contour compatibility improves relative to M1 without introducing new swatches. **H0:** prefilter gives no useful simplification, loses detail or fails visual recognition.

**Fixed controls:** original ROI RGB exact pinned; M1 merged RGB exact pinned; original V44-B immutable overlay, no new outline or neural infer. Run four independent unquantized RGB candidate filters on original full-size 200×320, then resize 150×240 with **Pillow LANCZOS** (same `read_source`); explicitly restore archived original ROI RGB for all pixels in frozen `source_protected_union` (no dilated/manual face boxes). No game32 palette assignment or new labels/regions in this phase.

**Four fixed candidates (no parameter tuning after first result):**
- `BILATERAL_LOW`: OpenCV `bilateralFilter(d=5, sigmaColor=18, sigmaSpace=2.0)` on original RGB200×320.
- `BILATERAL_MID`: `bilateralFilter(d=7, sigmaColor=28, sigmaSpace=3.0)`.
- `MEANSHIFT_LOW`: `pyrMeanShiftFiltering(sp=5, sr=15, maxLevel=0)`.
- `MEANSHIFT_MID`: `pyrMeanShiftFiltering(sp=7, sr=25, maxLevel=0)`.
Methods are plain deterministic math; neither is a semantic segmenter or trained network. Save unquantized RGB image, original RGB+V44 native overlays via existing `run_engine001_color32_s2b_p4b_v44b_hybrid.py` `compose` method (full native E3 outline only, source raster fill), and comparison sheet with source/M1 controls. Preserve filenames and archival results.

## Preregistered diagnostic metrics and provisional source gate

For each candidate vs exact pinned original ROI 36,000 pixels: mean and p95 CIEDE2000, color error restricted to V44 alpha>=24 projected logical via backing (same native alpha, no synthetic contours), 100% bitwise original on archived protected union, source strong-Sobel90 fixed threshold overlaps, flat-region 4-connected-neighborhood average absolute RGB neighbor difference at locations below original Sobel median (local roughness). Report SHA256, source/protected hashes, method params, changed fraction, unique RGB count and actual versions.

**Initial source-only informative gate (all):** protected pixel identity PASS; whole-image mean ΔE00 <=3.0 and p95<=12; native-contour alpha-weighted location mean ΔE00<=6.0; >=85% overlap source Sobel90 original strong pixels by identical absolute source threshold; flat-region roughness reduction >=5% vs raw original. These are conservative *research screening* thresholds, not visual acceptance or game quality gates. Do not retune after result, archive all negatives. If source gate fails, mark SOURCE_GATE_FAIL; user visual recognition and legibility remain independent PENDING even on numeric PASS.

**Validation boundary:** use test-only script/tests, CI E2/E3 source-only if triggered; this local preview cannot verify game color mapping, native game round brush, CHALK, 32 palette quality, or success on other images. Saved contour is original Egret E3 alpha composited via Pillow, not a new Egret run. If unquantized preview looks good, further separately preregister color regions and game32; no implicit production promotion.

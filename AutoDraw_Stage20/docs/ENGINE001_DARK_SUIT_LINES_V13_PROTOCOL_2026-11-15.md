# ENGINE001_DARK_SUIT_LINES_V13 — pre-registered isolated recovery experiment

**Task:** ENGINE-001. **Date:** 2026-11-15. **Status:** PRE-REGISTERED BEFORE OUTCOMES. **Baseline:** user reports jacket seams/folds vanished in V11/V12. Source pinned original (200×320, 97308 bytes), Git blob `d3cd95b846f036a3f8acecf75d2a237e46dcf13a`, SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`; earlier V7/V8/V10 and V11/V12 exploratory masks are **not successful acceptance**.

## Scope and ROI

Extract dark-line candidates from **original RGB 200×320 before 150×240 resizing**, then compare enlarged fixed jacket region (source coordinates x=100..199, y=62..250) to source and ordinary Canny. This region intentionally includes overlaps and some nearby non-jacket pixels; report results as **ROI proxy, not verified jacket-only semantic segmentation**. Preserve unchanged image and logical aspect-contain (200×320→150×240, offset x=155).

## Fixed candidates (all thresholds frozen before local run)

A. **XDoG:** luminance uint8, two Gaussian blur sigma0.8 and1.6; response difference (G2-G1) for local dark valley (large-blur minus small-blur luminance), normalize using global max to 0..255; binary >=45; thin using deterministic morphological skeleton.
B. **Local blackhat+CLAHE:** luminance grayscale CLAHE(clipLimit2.0,tileGridSize8×8), blackhat 9×9 elliptical structuring element, threshold >=14; thin.
C. **Directional coherence proxy (NOT full FDoG):** `cv2.Sobel` grayscale gradients 3×3, Hessian coherence proxy via Gaussian-smoothed structure tensor sigma1.5; accept dark ridge (XDoG threshold>=28) only if coherence >0.35; thinning. This is explicitly **not implementation of Kang et al. FDoG**, and may reject thin weak lines. Compare honestly, do not call FDoG itself tested.
D. **Union A/B with local continuity constraint:** candidate A OR B; 8-connected components with >=8 pixels survive, skeleton. All evaluated before fill and distinct from color-palette boundaries; no generative neural inference.

**Black/white visualization:** draw candidate line 1 logical pixel black on white, first extracted at source resolution then downsample binary mask to 150×240 by nearest neighbor; drawing on original enlarged by nearest neighbor for side-by-side. Also save overlay on original to localize recovered dark-clothing details. Avoid inventing new edges through morphology closing. Refuse any claim of segmentation from suit mask; no inter-color stroke safety or game brush calibration measured.

## Diagnostics and falsifiability

Report total and fixed ROI line pixels, connected components >=8, source Canny edge support within1 original px and overlap vs Canny inside ROI, additions vs ordinary Canny and ratio of lines in the dark RGB pixels (`gray<120`); source hash and every artifact SHA. This is not recognition or true-positive ground truth. A high count of extra pixels can mean artifacts. Manually inspect seams, lapels, sleeve folds side by side against original; if low-contrast seams remain absent or noisy, label FAIL/PARTIAL, not PASS. No post-hoc threshold changes to this ID. AniLines detail weights/runtime are not available in local environment; status **NOT_RUN**, must not be claimed compared.

Independent new image and blind evaluation, true Egret, color safety, actual game E4 pointCount CHALK and E5 mandatory before any promotion. No production, executor, bridge, master changes.

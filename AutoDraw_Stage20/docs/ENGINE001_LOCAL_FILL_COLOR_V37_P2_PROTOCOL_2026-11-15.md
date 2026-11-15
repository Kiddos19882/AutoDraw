# ENGINE-001 / V37-P2 — source-region RGB on existing fill strokes, full V35-B outlines

**2026-11-15. PREREGISTERED / NOT_RUN** before native V37-P2 measurement. Follows complete [V37-P1](ENGINE001_FULL_OUTLINE_V37_P1_PROTOCOL_2026-11-15.md); user-preferred V35-B retains **all 410 original dark contour strokes**, drawn strictly after paint. This is a color-assignment pilot, not a coverage-geometry repair. Task ENGINE-001. No production/master/Stage6/executor changes.

## Baseline and resource rationale

Frozen V35 [CI43742747278](https://github.com/Kiddos19882/AutoDraw/actions/runs/43742747278) SHA `a183b53e366a2f6e50867bf3124f9420c58928e0`, artifact14173635779 ZIP SHA `350892e45a1941072e0dc3b590d348ea817d0ee8f7daf004915e683a3368f170`, original complex PNG SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`. Same BoardPane 460×240 logical board, original150×240 ROI x155..304, native1380×720 at scale3. Plan: 1945 paint width2 paths then **410 V18-B dark [49,38,43] width1 detail** = 2355 paths / 5682 synthetic accepted vertices **not exact CHALK**, 218 native probe cap headroom under5900. Do not introduce more strokes before actual game quota safety. Frozen V35-B native source RGB MAE20.21118519/warm37.89431998, 410-line outline user-preferred. V37-P1 color-only lines improve numeric RGB but user still prefers V35-B dark line appearance.

**Hypothesis:** assigning original source local warm RGB to existing V34R fill scanline paths, without affecting full dark contour, restores orange/gold garment and skin regions and lowers source warm error. It may also increase color noise and unwanted segment tint. Do not use output PNG to select candidate colors.

## Frozen A/B/C experiment (single varying dimension: RGB of paint paths)

- **A control:** original exact V35-B, unchanged frozen 1945 paint class RGB and 410 dark contour strokes, native decoded RGBA must match archived `B/V35-B-composite.png` exactly.
- **B per-class source-aware fill:** for every 1945 original two-point width2 paint stroke, sample at five deterministic logical positions `t=[0,.25,.5,.75,1]` along its segment. Each sample x/y use Python `round` (banker's nearest), then clamp x to ROI155..304 and y0..239. Reuse existing `prepare_source` and `quantize_case(roi,canvas,8,False,True)` with fixed LANCZOS original; retain only sample points whose frozen ROI8 palette index equals original stroke `colorIndex` (4/5/6/7). If **>=3 class-owned samples**, derive one RGB lower per-channel median of their actual original source RGB; otherwise keep unchanged frozen color. All 410 dark contours unchanged.
- **C warm-owned fill only:** same five sampling locations; require **>=3 own-class** AND **>=3 warm-source samples that are own-class** where warm source mask HSV H5..55°, saturation>=0.30, value>=0.20. Derive one lower median original RGB using the warm and owned samples only. All other paint paths retain exact frozen RGB. All 410 original dark contour strokes unchanged.

B and C use exactly the original stroke coordinates/order/widths/IDs/shims, no extra samples inserted in actual plan. C is a subset of B's eligible paths but may use different RGB from warm samples. Under no circumstances replace the frozen dark 410 contours with V35-C reduced297 lines, alter contours' RGB, or add filler geometry. Pilot anticipates more color switches; report them explicitly as risk for game execution latency/CHALK, no claim that equal synthetic vertex count guarantees equal game quota.

## Native validity and metrics

Use existing real Egret `renderV36SourceColoredContourProbe` via unchanged `native_batch` (per-stroke colors, native width2 fill/width1 detail). Validate original input SHA, V35 artifact 23/23 inner hashes, full sequence/410 contours/5682 vertices; no overwriting. Compare native A control to V35-B pixel-exact RGBA & IDAT; reject any unexpected alpha pixel difference across A/B/C isolated class layer and composite. Measure source full ROI RGB MAE and warm HSV MAE, reference source quantized coverage and true composite alpha>=24/128, foreign class/color bleeding, >3 logical px native exterior; retain separate original/color images and same face/hand crops. Report color switches, number of recolored paint paths, precise sample count and candidate rule, accepted synthetic points not CHALK.

**Fixed color diagnostic gate** = lower full ROI RGB MAE AND warm ROI RGB MAE versus A, same native alpha, no changed geometry or quota count. **Separate recognizability comparison** = full final native actual Egret images side-by-side with V35-B dark outlines (eyes/hair/hands/garment readability, no blind score). A candidate can be RGB PASS while visually worse: label separately, do not promote. This pilot **cannot** improve alpha coverage because geometry is unchanged, so cannot claim >=99% required source class coverage. Production remains BLOCKED until native per-color quality and <=3logical-px exterior, E4 run-bound exact CHALK (`post.pointCount-pre.pointCount`) and independent E5 requirements have evidence. Negative B/C results preserved, thresholds not tuned after result.


## Initial CI preflight failure (before any native V37-P2 quality result)

[CI43746951664](https://github.com/Kiddos19882/AutoDraw/actions/runs/43746951664) on SHA `31f81c26c8b3e8b16b0e2dc3e7f99d2d926258f8` completed **FAIL** in 2/4 new Python deterministic source sample tests, before running Egret. Traceback `IndexError: index 155 is out of bounds for axis 1 with size 150` in `source_samples`: RGB sampling erroneously used full-board x rather than ROI local x-155. The original prereg already specified source ROI x155..304 and logical-to-original mapping; this is a minimal **implementation correction, not a change to experimental independent variables, masks, thresholds or V35-B lines**. Fix commit `04e506a3bf41b5d197a19bb20e36e8f445d79dec` changes `arr[y,x]` to `arr[y,x-155]`. Prior CI remains FAIL and no V37-P2 native pixels or artifact are claimed. Native acceptance waits a separate exact-SHA successful run.


## Completed native V37-P2 E3 measurements — 2026-11-15

[CI43747149144](https://github.com/Kiddos19882/AutoDraw/actions/runs/43747149144) **E3 SUCCESS** SHA `04e506a3bf41b5d197a19bb20e36e8f445d79dec`, Windows actual archived Egret BoardPane/WebGL renderer and unchanged original V35-B full dark contour geometry. Artifact **14175105717** ZIP SHA256 `a9d97229fada28875d718ba7c1c068464dfe8529fc1b313becb9a77e2ed50959`. Inspected ZIP and **24/24** report-linked SHA256 files PASS. Baseline V35-B control exact native RGBA pixel replay, **A/B/C all native isolated composite alpha identical**, 2355 strokes / 5682 synthetic accepted vertices (NOT game CHALK), complete 410 original dark width1 contours retained.

| Variant | Original-source RGB MAE | Warm RGB MAE (2946 original warm pixels) | Changed original fill strokes | Distinct paint RGB | Paint RGB switches | Composite native alpha>=24 px |
|---|---:|---:|---:|---:|---:|---:|
| A unchanged V35-B full dark contour | 20.21118519 | 37.89431998 | 0 | 4 | 1535 | 161544 |
| B 5-point source median in palette-owned regions | **19.40516667** | **27.75695859** | 1550 | 1449 | 1927 | 161544 |
| C source warm-region-only owned median | 19.42033333 | 27.90450328 | **166** | 170 | **1543** | 161544 |

Both B/C meet prereg **source RGB MAE + warm RGB MAE decrease** with native alpha identical. Source ROI native alpha coverage cannot change when only RGB changes; per-color >=99% remains **not accepted**. Additional paint color switches (B +392 compared with A; C +8) may matter in game, and synthetic point count unchanged does **not** establish CHALK or real quota safety margin. No real gameplay E4, no independent E5, no exact CHALK.

**Unblinded visual inspection of original/raw native A/B/C:** Both B/C restore gold/orange belt/ribbon, pink hem/shading and skin tone compared with muted V35-B, while **all user-preferred dark expressive 410 contour routes remain**. B colors more paint strokes and may introduce fine, uneven localized tint; C reaches nearly same error improvement with fewer paint-color changes/switches. The user's aesthetic preference still applies to V35-B full outline; the judgement that C is a more conservative experimental successor is **exploratory**, not user sign-off or external recognition E5. Do not infer C best for all inputs from this single source.

**Classification:** `E3_NATIVE_SUCCESS / LOCAL_RGB_WARM_IMPROVEMENT / FULL_USER_PREFERRED_CONTOURS_PRESERVED / SOURCE_CLASS_COVERAGE_NOT_FIXED / PRODUCTION_BLOCKED`. Historical initial CI43746951664 FAIL due 150px ROI indexing remains preserved; no retroactive PASS. Next independent experiment must target native source-color **coverage gaps** under remaining resource headroom (5900-5682 = 218 synthetic vertices only), or seek resource-neutral stroke rearrangement, with full V35-B outlines immutable and no acceptance threshold relaxation.

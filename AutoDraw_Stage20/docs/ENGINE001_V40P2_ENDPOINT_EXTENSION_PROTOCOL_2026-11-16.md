# ENGINE-001 / V40-P2 — native, resource-neutral horizontal fill endpoints

**2026-11-16 | PREREGISTERED / NOT_RUN before native CI.** Separate experimental sub-ID after V40 archived-alpha internal 3logical-px audit. User permits **fill overlap of adjacent source colors up to 3 logical px**; never require non-intersection. Preserve **all 410 user-selected V35-B dark contours above fill**. No production, executor, Game Monitor, Stage6, master changes.

## Frozen inputs and hypothesis

V37-P2 [CI43747149144](https://github.com/Kiddos19882/AutoDraw/actions/runs/43747149144) SHA `04e506a3bf41b5d197a19bb20e36e8f445d79dec`, original test PNG SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`, artifact14175105717 ZIP SHA256 `a9d97229fada28875d718ba7c1c068464dfe8529fc1b313becb9a77e2ed50959`; frozen **C** plan 1945 source-region warm fill width2, then 410 V18-B dark width1 detail; 2355 strokes/5682 synthetic native accepted vertices **NOT exact game CHALK**, >5900 native cap prohibited. Native final source RGB MAE19.420333 and warm ROI27.904503. User specifically prefers **complete V35-B outline**, not V35-C 297-stroke subset.

V40-P1 archived true Egret alpha [CI43770499251](https://github.com/Kiddos19882/AutoDraw/actions/runs/43770499251), SHA `13739e8b356df6bb8fef5aa3b627348f0f1652a7`, artifact14183662948 ZIP SHA256 `0d3af2787e38cfb2a9f8048eb7878e4b293cd2273fff3b3ceec00a36632734af`. At alpha24, 38,479 actual native painted pixels fell onto **other** required source classes, ALL within 9 native px =3 logical px, **0 internal excess**; alpha128 35,660 allowed,0 excess; max foreign-source distances <=6.708 native px. Exterior >3logical px zero. V39 entire-row source-oriented y shifts ±0.25/0.5 failed all four per-color recalls and source RGB metrics; retain negative.

**Hypothesis:** expanding only the *horizontal x endpoints of existing two-point fill scanlines* 0.25 or0.5 logical px outwards can close native brush edge gaps without adding paths/accepted vertices, and without exceeding internal/external 3px tolerance. This might FAIL due to wrong-class overpaint or RGB regression. Do not modify y or shift rows, width2/width1, colors, point counts, layer order or original source palette.

## Predeclared A/B/C

- **A**: frozen V37-P2-C exactly; actual Egret final PNG must reproduce archived `C/V37P2-C-composite.png` pixel-exact RGBA and critical PNG IHDR/IDAT. If fails, block.
- **B**: extend every existing width2 paint segment start x left by0.25 logical px and endpoint x right by0.25 logical px; clamp each to frozen ROI **[155.0,304.75]** (not whole board), using `max(155,start.x - 0.25)`, `min(304.75,end.x + 0.25)`. Source original B image is NOT used to choose individual path; no tunable threshold.
- **C**: same endpoint extension/clamping with exactly0.5 logical px.
- **All variants**: frozen 1945 fill path identifiers/width2/pointCount2/y, source-derived V37-P2-C paint RGB, followed by exact same410 full dark V35-B contours width1, 2355 total strokes,5682 synthetic accepted vertices. If a source scanline is reversed/nonhorizontal, outside ROI, metadata-drifted or any E3 accepted point count differs, abort; never silently truncate.

## Evidence/decision

Native BoardPane/Egret actual WebGL PNG A/B/C: composite, separate alpha of each class4–7 and detail100. Reuse [V40-P1 metric contract](ENGINE001_V40_INTERNAL_COLOR_TOLERANCE_AUDIT_PROTOCOL_2026-11-16.md): per-class own true source-label recall, allowed internal foreign-color crossing <=9 native px, excess crossing>9 native px, source foreground silhouette recall/precision, exterior>9 native px, at **alpha24 and alpha128**. Keep final actual Egret composite ROI RGB MAE and warm source RGB MAE and same face/hand visual comparisons. Do not infer final visible pixel owner from isolated alpha; note dark contour is last.

Predeclared geometry/color diagnostic **PASS** only if at alpha24 **all four source-class own recalls are >= A**, at least one strictly greater, silhouette recall>=A, **internal excess remains0**, exterior >3logical px does not increase, native resource unchanged, final source full and warm RGB MAE <= A. Flag loss of recognizable facial/hair/hand details separately even if numeric PASS. Allowed overlap can increase without being a failure if it remains<=3px. Do not retune0.25/0.5 after CI or promote based on a single picture. Existing >=99% required-color gate, 3logical-px exterior, exact CHALK E4 `post.pointCount - pre.pointCount` and E5 remain separate; an E3 execution PASS is not production acceptance.


## V40-P2 after-run genuine Egret evidence — 2026-11-16

[CI43770948329](https://github.com/Kiddos19882/AutoDraw/actions/runs/43770948329) **E3 SUCCESS (native experiment executed)** SHA `d05e0ed1547046582f284bb75caa6f1ec07616ca`, artifact **14184625357**, ZIP SHA256 `3b307490b179539be18eaff45d9eec3d13437cdafa2e89327c7748fc46b94c85`; independent inspection 24/24 report-linked file SHA256 PASS. A controls exactly replay frozen V37-P2-C native RGBA pixels, B/C preserve all410 final dark contours pixel-identical alpha; total2355 strokes and5682 synthetic accepted vertices (NOT actual CHALK). Existing1945 fill paths have endpoint extensions in B/C, unchanged RGB/width/y/IDs.

| Genuine native actual Egret metric | A frozen original | B +0.25 logical x at endpoints | C +0.5 logical x at endpoints |
|---|---:|---:|---:|
| Source-quantized silhouette recall α24 | 93.868365% | 95.084346% | **96.377586%** |
| Own-color class4 recall α24 | 71.077766% | 73.6380% | 76.5231% |
| Own-color class5 recall α24 | 77.810362% | 79.2673% | 81.0525% |
| Own-color class6 recall α24 | 57.712223% | 59.3606% | 61.5600% |
| Own-color class7 recall α24 | 94.725559% | 95.1159% | 95.6640% |
| Source original ROI RGB MAE (lower is better) | **19.420333** | 20.337009 | 21.501389 |
| Warm original HSV ROI RGB MAE | **27.904503** | 28.838312 | 29.946142 |
| Native alpha24 **internal** foreign-owner overlap within3logical px | 38,479 | 45,989 | 56,075 |
| Internal excess **beyond3logical px** (alpha24 and128) | **0** | **0** | **0** |
| **External** overpaint >3logical px | **0** | **0** | **0** |

All four source-quantized own-class recalls improve monotonically, as does overall silhouette coverage; this improvement is **real native Egret alpha**, not geometric brush proxy. Allowed cross-color intersection increases; it is NOT in itself a violation because the explicit user-approved tolerance remains respected. **However**, both B/C increase total and warm RGB MAE versus A: the preregistered combined diagnostic condition `PASS` is **false** for both. Therefore **do not select B or C as a whole-image improvement**, do not change historical acceptance gates, and do not promote production. Entire line-art layer remains the user's preferred V35-B shape. Native resource counts equal is NOT game run-bound exact CHALK; no E4/E5.

Interpretation: uniform extension of every horizontal segment treats source-boundaries indiscriminately and improves own color coverage at cost of visible source color error. The **next separate prereg V41** should test selective endpoint extension (source/actual-native-alpha guided, not posthoc fitted to a rendered outcome) with baseline A/B/C frozen and unmodified, all410 dark contours unchanged. Need color target crossing<=3 logical px and source RGB non-regression simultaneously; otherwise preserve A.

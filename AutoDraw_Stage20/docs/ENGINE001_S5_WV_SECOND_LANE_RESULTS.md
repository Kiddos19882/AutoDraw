# ENGINE-001 · wV second-lane search, 2026-11-23

Baseline b079e755, fresh default eight-color wV, unrestricted counts, normal mode, smoothing disabled. Both runs share the input and source manifest. The opt-in second-lane experiment uses the original sweep cell, both axes, integer widths from two to the original value, four or more consecutive safe centers and two parallel spans separated by at least one brush width. Both connection ends are tested with the whole ideal capsule. The existing scheduler sees the original proposal and the best extra candidate.

Of 45 nonwhite single-lane proposals, 30 admitted a gainful connected second lane. For 18 of those 30 a narrower brush was required. The other 15 had no pair at the tested spacing and length. Colored broad coverage rose from 2,886 to 4,869 of 23,168 pixels, adding 1,983 and losing zero. Broad paths rose from 136 to 161, single dots rose from 2,812 to 2,880, and all paths including dots fell from 9,039 to 8,922. Both final RGB frames matched the same prepared target in all 64,000 pixels. Model plan hashes: baseline 96cd7a3279386c6e9ce60e5a74a44d1d19468122fa7ffd953cf4c5ed0832e8a1; study 2f8762aa40d352bc5649234d653817ab1dba9530cfba14599b89fb7ad225dca3.

E2 model only. Full-scene native replay and exact CHALK remain NOT_RUN. Keep this search opt-in. Next bind source ownership, image-to-board geometry, actual brush scale and genuine one-point semantics in the Egret bench before comparing full native frames.


## Native binding protocol (S5 wV, baseline 07ae05b)

Rebuild the eight-color test plan and require its recorded digest. Use the existing upright 150 by 240 board ROI at (155, 0) with source pixel centers, an isotropic scale of 0.75 and a 3x backing. Probe widths 1 through 10 on horizontal lines in different positions. Record midpoint offset and cross-section thickness at alpha 128. Probe the first nonwhite line, turn and single-point path from the plan, in scheduler order. Record alpha coverage and count backing pixels outside each source owner after inverse mapping. Board widths equal the nominal source integers in this diagnostic. Any visible out-of-owner ink is a discrepancy to report. Preserve the actual native PNGs even when the singleton is blank.

Technical controls require a transparent board, accepted vertex counts, the pinned game palette and renderer, and identical native line pixels before and after allowing one point through the fixture input check. This tests normal-mode full redraw on the isolated bench. A user touch event, live canvas calibration, full-scene quality and exact CHALK require separate evidence.

### Native result, run 45203361169

[Windows native E3 run](https://github.com/Kiddos19882/AutoDraw/actions/runs/45203361169) at c6546721. Blank and identical adapter line control passed. The original accepted singleton (plan index 167, width 1) produced zero nontransparent pixels on full redraw. The width-10 line had 9 of 3,067 alpha-128 backing pixels outside owner 876; the width-6 turn had 32 of 1,604 outside owner 2712. Counts use inverse source-center mapping. At 3x backing the measured alpha-128 mid-line thicknesses for widths 1..10 were 4, 7, 10, 13, 15, 19, 21, 25, 27 and 31 pixels. Across the ten placements the largest midpoint error along either axis was 0.542 board pixels. Each width has one placement in this experiment.

Technical E3 PASS; direct width transfer and singleton-as-painted assumption fail for these examples. The full eight-color plan contains 2,880 singleton paths; one path was sampled. Full-scene native and live CHALK remain NOT_RUN. Next test distinct two-point residual paths on the native bench, choose feasible width and orientation using the projected zone and actual footprint, and retain any unpaintable residual explicitly.


### Full native eight-color wV redraw protocol

Start with the fresh eight-color second-lane plan at e453121. Preserve all paths, restore each original color, use normal full redraw, and scale widths against the measured alpha-128 backing cross sections for the 0.75 board ROI. Probe four short two-point paths at all 16 fractional source-center positions on the same native bench. Rank residual candidates by touching the target, then by pixels beyond its owner, then by target coverage. Draw all multi-point paths first in original relative order, followed by the singleton replacements in original relative order. Save the actual full-board Egret frames with and without these replacements. Compare the native frame over white to the projected eight-color target by nearest-color agreement, foreground misses and mean RGB error. Record all results including degradation. Raise offline fixture capacity only; verify an unchanged native control and accepted vertex counts. No live or exact CHALK claim.

### Full native result on wV

[CI 45205918003](https://github.com/Kiddos19882/AutoDraw/actions/runs/45205918003) at bb11101a succeeded. Full-scene E3: 6,042 original multi-point strokes and 2,880 calibrated two-point replacements, 8 source swatches, normal full redraw in one BoardPane. Blank and line equivalence controls passed. Comparison covers the 450×720 backing-pixel artwork ROI. Nearest target-color agreement before/after repair was 266,018/265,841 out of 324,000. Foreground agreement improved from 70,213 to 74,073 of 117,215; foreground misclassified as white fell from 22,214 to 15,543. RGB mean absolute error decreased from 14.725 to 13.693. Calibration predicted outside-owner ink for 2,666 repairs. The visual baseline is available; full-image quality acceptance is open. Next select repairs by measured improvement to foreground and harm to neighboring colors. Live CHALK NOT_RUN.


### Paired 10 percent tolerance experiment

At baseline 55a1351 the full native runner limits the measured brush span to the projected nominal width. Residual direction minimizes outside-owner pixels among target-hitting candidates. Compare the unchanged 0% control with a 10% increase in both allowances: width ceiling times 1.10; residual spill budget floor(1.10 times baseline minimum spill), then maximize target-pixel hits and break ties by smaller spill. Retain zero spill where achievable. Same source plan, eight colors, phase calibration, smoothing off, scene order, number of paths and predeclared metrics. Repeat both complete native frames at both settings; compare control with stored full redraw and report foreground and white-background effects separately. Experimental brush policy only.

## Four-way native tolerance 0/10/15/20 (2026-11-23)

Research-only complete Egret/WebGL normal/smooth=false wV eight-color comparison. [CI45211813045](https://github.com/Kiddos19882/AutoDraw/actions/runs/45211813045), SHA `1bd22ce122360fe538ebebb5a8aacc2f7f8ae945`; all four matrix jobs **E3 PASS**. [Full validation](https://github.com/Kiddos19882/AutoDraw/actions/runs/45211813041) mandatory jobs PASS; optional benchmark, on-demand studies, portable build SKIPPED. Four fresh full redraws from source SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a` and common proposal digest `2f8762aa40d352bc5649234d653817ab1dba9530cfba14599b89fb7ad225dca3`; 8 colors, 6,042 broad plus 2,880 two-point repair strokes, same ordering and scene, normal mode, smoothing off. Difference: measured-width ceiling and permitted minimal residual outside-owner pixel *budget* multiplied by 1+allowance. No claim of no actual overpaint; prepared/pipeline source manifest file digest can vary between runs.

| Additional tolerance | Native nearest-correct total /324000 | Correct foreground /117215 | Foreground seen white | RGB MAE | Correct white-background /206785 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0% | 265841 | 74073 | 15543 | 13.692919 | 191768 |
| 10% | 266657 | 74891 | 15138 | 13.347011 | 191766 |
| 15% | 268899 | 77124 | 13139 | 12.344849 | 191775 |
| 20% | **269234** | **77456** | **12932** | **12.172922** | **191778** |

Full frames independently re-scored from each actual `full-crop.png` using the exact source 8-color target and nearest-RGB palette over the 450x720 backing region. Versus 0%, 20% fixes 3,739 previously wrong nearest-color pixels and worsens 346 previously correct, net +3,393. Of these, foreground fixes 3,671 and worsens 288; background fixes 68 and worsens 58. Versus 15%, 20% fixes 385 and worsens 50, net +335 (foreground +332, background +3). Gain is nonzero but sharply diminishing above 15%; apparent gaps and false white traces remain in hair and clothing. `predicted_outside_owner=2666` for all settings is a planner diagnostic on the replacement paths, **not a measured total spill count**.

Archives downloaded and verified: 0% artifact `14835749447`, ZIP SHA256 `1e8a110284ee6eb7d202571a95166086ab14dc597559f4e5305ef5803a828709`; 10% artifact `14837350791`, SHA256 `8973948b197341f451c201273b8b7bf5e4180b5e6c579e08baa5ddcf41888961`; 15% artifact `14836237335`, SHA256 `8a79d0127badbd05e9625877d7266716d240360b291a5de0bba63b2a44e30bac`; 20% artifact `14837101206`, SHA256 `d36c721b98399097c03bb4327a8176e34e32ed2a9a267f7ed2cd152b5e7652a0`. All 30/30 ZIP members passed CRC, `results.json` run and SHA match, 4 actual Egret crops and original source retained. No game E4, exact CHALK, cross-image held-out evaluation or independent E5; **quality PARTIAL**, no production promotion and no acceptance threshold changed.

**First next:** assess native before/after local target-owner and edge/protected-detail gains versus neighboring-color damage, including residual white cracks; choose a local adaptive tolerance policy for a separate preregistered E0, not a global 20% production default.

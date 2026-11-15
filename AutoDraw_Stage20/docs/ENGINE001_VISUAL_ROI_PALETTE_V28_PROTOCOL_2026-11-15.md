# ENGINE-001 / V28 — ROI palette composition for recognizable, efficient color previews

**Date 2026-11-15; status PREREGISTERED / NOT_RUN.** Recorded before V28 quantization results. Task ENGINE-001; exact image `wV6VeZI9S1Y.png` 200×320 SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a` 97308 bytes. Fixed ROI 150×240 on 460×240 board at (155,0), resized LANCZOS. Reuse only existing Stage20 `build_color_scanline_plan`, `render_color_scanline_preview`, `validate_color_scanline_plan` and frozen prior input. No production, game or AniLines integration.

**Reason:** V27 source-bound [CI43687584670](https://github.com/Kiddos19882/AutoDraw/actions/runs/43687584670) E3 SUCCESS but scanline 11638 strokes / predicted25585 game points vs6000 game board limit; full-canvas 8-color MEDIANCUT selected 5 near-white palette classes, losing original saturated details. V26 [CI43687362812](https://github.com/Kiddos19882/AutoDraw/actions/runs/43687362812) FAIL due to contour/skeleton preview 5 outside-ROI pixels; V27 preserved those ROI FAIL. V25 original vs AniLines/V18/V20 review concluded focus on silhouette, faces, clothing/real color rather than recovering 20 skeleton pixels.

## Frozen visual study (no parameter tuning after outcomes)

Run the same original, using Pillow MEDIANCUT and no dithering, four conditions, and a fifth original source control:

- A **V27-equivalent full-white-canvas quantization (8)**: quantize entire 460×240 white canvas with the source ROI, original 8 color palette, index_map = -1 outside ROI, include all colors inside.
- B **ROI-only quantization (8)**: MEDIANCUT only the 150×240 resized actual RGB crop, retain every palette class and all ROI pixels.
- C **ROI-only quantization (6)**: same as B but exactly six classes, chosen BEFORE outcomes to see stroke/color trade-off.
- D **ROI-only quantization (8), near-white skipped**: same palette/index source as B but set transparent (-1) for any quantized RGB class with each channel >=245; leave white board background. This is a controlled no-ink preview of white regions, not permission to omit real game strokes when necessary.

All settings use existing `build_color_scanline_plan` `row_step_px=1,row_offset_px=0`, no additional simplification and no stroke order modification. Add candidate identity and retained/transparent pixel counts to output. **No AniLines or any original RGB texture pasted over the rendered plan**; any white background comes from board and explicitly skipped classes. Map non-ROI pixels -1; verify no alpha outside ROI. Compare plan counts, color changes, predicted shared game point quota (only model estimate, never CHALK), HSV saturation spread of actual palette (diagnostic), and RGB source MAE on ROI for each variant. Save actual full plan JSON, native Stage20 plan preview alpha, same-sized RGB ROI previews, full/face comparison sheet, input/palette hashes.

## Outcomes and safeguards

Exploratory manual observation without independent blind review: count figures, distinguish facial expressions/hair, dress color and dark jacket, notice hands and edge breaks. No single numeric metric proves recognition. Passing V28 CI means reproducible offline preview only. User agreed to quality-first; retain true game gates original >=99% fill, <=3 logical px leakage tolerance, exact CHALK from run-bound post.pointCount-pre.pointCount. Reject any proposed single-board production plan whose predicted cost exceeds available 6000 limit until new game validation; forecasts guide triage but don't supply measured CHALK. C and D may lose light clothing edges, preserve negative findings. Do not retune palette colors after results to manufacture a win. Native Egret color output, real E4, independent E5 NOT_RUN.

**Next only if meaningful:** choose a fixed-color recognizable candidate, then separately prereg stroke-count/CHALK reduction using existing planners and semantic priorities, with no sacrifice of main visual features. Otherwise preserve negative results.

## Actual results, appendix (2026-11-15, AFTER preregistration)

[Focused CI43687934758](https://github.com/Kiddos19882/AutoDraw/actions/runs/43687934758) **E3 SUCCESS** at SHA `37ccf6b60efe85a77a32ca51df99962df1ad2f8d`. Pinned input 97308 bytes/200×320 SHA, genuine V27 A scanline exact pixel identity, four fixed color plans and offline previews, ROI=150×240 and zero paint beyond ROI in all four, output hashes PASS. Artifact **14151345459** `engine001-v28-roi-palette-visual-evidence`, size1424542 bytes, downloaded ZIP SHA256 `3788264792eeb4558a1dae41891270a75d7fa4b326187521c661b728d8bfe814`, independent validation of every report-listed SHA PASS.

| Frozen variant | Actual scanline strokes | Approximate game points (forecast, NOT CHALK) | ROI preview RGB MAE | Visible-index pixels |
|---|---:|---:|---:|---:|
| A full canvas MEDIANCUT8 | 11638 | 25585 | 7.5691 | 36000 |
| B source ROI MEDIANCUT8 | 11759 | 25724 | 7.3968 | 36000 |
| C source ROI MEDIANCUT6 | 9481 | 22149 | 13.2648 | 36000 |
| D source ROI MEDIANCUT8 skip palette classes each channel>=245 | **6373** | **13258** | 7.7909 | 16539 |

Original board point limit in the frozen V28 planner estimate: 6000, safe planning budget5100. **Every variant exceeds the estimated single-board resource capacity**. D reduces stroke count 45.24% versus A and estimated quota 48.18%, still ~2.21× nominal limit (and 2.60× safe budget); no real CHALK measured. The 16539 D visible index pixels refer to intentional sparse strokes, NOT actual native fill coverage; original white board is background. D skipped exactly classes 0/1/2/3 from ROI8 palette. Manual same-size visual observation: A and B preserve two character identities and outfits; ROI-only B yields slightly richer warm/dark contours than A but still flattens original vivid orange. C worsens detail; D remains readable while omitting many near-white strokes, but some pale dress and hair accents may weaken. This is exploratory one-image assessment, not independent recognition PASS.

**Hypothesis result:** ROI-only MEDIANCUT8 alone does not solve palette/color balancing or points, despite modest MAE gain. Near-white no-ink condition D is an encouraging **planning research candidate, not production**. It still loses saturation, forecasts >2× board quota, and has no game accuracy/leakage/CHALK validation. Do not change quality gates or claim V28 as feasible. Distinguish V26 geometry preview ROI=FAIL from V28 scanline ROI=PASS; these are different planners/modes.

**Next priority:** use an existing resource-aware fill/contour-first method (not raw per-pixel scanlines) to preserve recognizability within one-board cost and fix meaningful orange/saturated details; prereg new-ID one-image comparison with fixed source, actual native rendered RGB plans, no new pixel-edge tuning. Do NOT erase V26 failures or V21/V24 negatives.

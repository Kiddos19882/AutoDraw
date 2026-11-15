# ENGINE-001 / V29 — prereg: existing budget-aware color planner and recognizability

**2026-11-15. STATUS PREREGISTERED / NOT_RUN.** This is a *new separate experiment* on unchanged source and unchanged existing Stage20 optimizer; prereg committed before V29 output. Branch feature/image-geometry-optimization, baseline remote HEAD `060a5ab3a65d1489e57ddf9b6fccc7b9a21959c9` before prior V28 doc updates. Task ENGINE-001; priority: user-visible recognizable two-character artwork within *estimated* BoardItem2 quota, not extra short outline skeleton pixels. V25–V28 evidence retained intact.

## Frozen baseline

Pinned `AutoDraw_Stage20/testImages/wV6VeZI9S1Y.png`, 200x320 SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`, 97308 bytes. Logical board 460x240, ROI=(155,0)-(305,240), source resize LANCZOS, eight-class ROI-only MEDIANCUT without dithering; skip palette classes where every RGB component >=245, white board. This is the **exact same V28-D input rule** preregistered and run in [V28 CI43687934758](https://github.com/Kiddos19882/AutoDraw/actions/runs/43687934758) E3 SUCCESS, artifact14151345459. Frozen D: 6373 strokes, estimated 13258 game points > nominal BoardItem2 6000. These are forecasts, **not** actual CHALK or game quality; V28-D is not currently executable by established gate.

## Fixed V29 method

1. Use V28 `prepare_source/quantize_case` unchanged to reproduce exact original D color index map. Assert same V28 archived `D-roi8-skipwhite.png` pixel-by-pixel and baseline plan count 6373 / estimated game points 13258. No hand recoloring, crop/texture substitution, palette retuning, AniLines overlay or altered input coordinates.
2. Construct `PaletteQuantizationResult` from exact D index_map and corresponding original 460×240 source RGB with white outside ROI (report `{}`). Call existing `paint_budget_optimizer.fit_result_to_paint_budget` exactly **once** with **default** costs and `target_usage_percent=75.0`, `board_item_type=BoardItem2` nominal limit6000 and existing safety factor. Use returned index_map, row_step and row_offset unchanged; build one existing `color_scanline.build_color_scanline_plan`, validate plan and render using existing `render_color_scanline_preview`, no second parameter sweep.
3. Save real optimizer `optimization_report`, full plan JSON, full alpha PNG, derived ROI and pre/post full and face comparison sheets (source, frozen V28-D, optimized V29); record runtime versions, hashes. Fail closed if any alpha outside fixed source ROI, baseline mismatch, invalid paletted indices, nonfinite or missing cost/quota metrics or forecast > maximum 6000. Save model estimate as **forecast only**; target75% is a planning goal and cannot establish exact game quotas.
4. Separately measure actual preview alpha coverage vs **frozen D visible-index map** (and original source RGB ROI) with exact RGB MAE; record changed/omitted source locations, visual completeness of faces/hair/hands/orange clothing. A more economic plan can fail recognizability despite model budget PASS. No acceptance criteria will be moved after results. Expect negative or unrecognizable output is a valid, preserved result.
5. User-visible visual assessment: qualitative A/B on one image, not blind or statistically representative; no independent annotator requirement for exploration. Explicitly mark if 2 figures, eye/mouth/hair, hand pose, distinct dark jacket/pale dress and original orange cue are legible. Do **not** claim a new overlay actually drawn or production improvement unless a corresponding plan exists. Existing 3 logical px boundary and >=99% *real game* fill criteria remain unchanged and NOT_EVALUATED on offline previews; only E4 valid game session can measure exact CHALK post.pointCount-pre.pointCount. All production, Stage6, Monitor, Bridge and master untouched.

**Decision gate:** if optimizer reaches predicted quota but destroys recognizable identities, mark RESOURCE_ONLY / QUALITY_FAIL and next investigate minimal separate-ID semantic priority with actual outputs rather than promote. If recognition appears adequate, still do not promote without live E4 and color leak/coverage confirmation. No variation in palette or budget goal after seeing V29 result.

## Post-run results (2026-11-15, appended; prereg above unchanged)

[Focused V29 CI43688844089](https://github.com/Kiddos19882/AutoDraw/actions/runs/43688844089) **E3 SUCCESS** at SHA `bc1ae39ea1bd30a747c3a996544ef6b1e6df9315`. Frozen original source SHA/size and exact independent V28-D preview pixel identity PASS. Existing `fit_result_to_paint_budget` called once with default cost model and 75% target, generated validated original plan and optimized existing `color_scanline` plan, plan forecast identity/ROI guard PASS; artifact **14151317769** `engine001-v29-budgeted-color-visual-evidence`, original ZIP **SHA256 `0cba18530e47bc3a70f69c243f553ae16eb620cc206321393f62071ebd7da1c9`**, and all report-listed inner SHA256 independently verified.

| Metric | Frozen V28-D baseline | Actual V29 output |
|---|---:|---:|
| Real planned strokes (not CHALK) | 6373 | **1945** |
| Forecast game points (not exact CHALK) | 13258 | **4498** |
| Preview native Stage20 alpha pixels in source ROI | 16539 | **7743** |
| Source RGB ROI mean absolute channel error | 7.7909 | **29.9945** |
| Estimate <= nominal BoardItem2 6000 | FAIL | **PASS** |

Existing optimizer chose block size **2**, row step **2**, offset **1**, forecast estimated game point usage **74.967%** of nominal 6000. V29 alpha preview has **7743/36000** source ROI ink pixels, compared with V28-D **16539/36000**, and **10078/36000** RGB pixels changed from baseline. This is not actual painted-color area; white untouched board can match original pale areas. All before/after full/face PNGs and full plan JSONs are in the downloadable evidence artifact, not added to repository.

**Qualitative non-blind visual assessment on exactly one source:** two interacting persons remain recognizable as a dark-haired and a light-haired figure, but faces, expressions, hands and clothing boundary details become fragmented horizontal stripes. Major visible quality degradation relative to V28-D. **Classification: RESOURCE_FORECAST_PASS / RECOGNIZABILITY_QUALITY_FAIL**, NOT accepted. No semantic objective perceptual metric, game E4, actual CHALK, independent E5, native full color coverage or game leakage tested.

**Follow-up:** current generic `progressive_block_mode_plus_row_sampling` loses facial features because global row skipping discards fine contours. Only a *new separately preregistered* local-detail-preserving color proposal should be assessed, e.g. existing interior-fill or boundary-priority planners in experimental non-executable mode and genuine preview, or an independently defined selective eye/hand/hair stroke priority. Preserve V29 negative result; do not adjust original optimizer defaults, safety margin or production.

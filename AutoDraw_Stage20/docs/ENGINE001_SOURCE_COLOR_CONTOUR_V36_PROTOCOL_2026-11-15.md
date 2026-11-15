# ENGINE-001 / V36 — source-colored line overlay after true native V35

**2026-11-15. Status: PREREGISTERED / NOT_RUN.** New independent experiment after [V35 pilot2 E3 result](ENGINE001_PAINT_THEN_DETAIL_V35_PROTOCOL_2026-11-15.md). Task ENGINE-001; user's accepted layout: color regions painted first, important lines **on top**. No Stage6/executor/Bridge/Monitor/master or runtime edits.

## Baseline and falsifiable hypothesis

V35 [CI43742747278](https://github.com/Kiddos19882/AutoDraw/actions/runs/43742747278), SHA `a183b53e366a2f6e50867bf3124f9420c58928e0`, artifact14173635779 ZIP SHA256 `350892e45a1941072e0dc3b590d348ea817d0ee8f7daf004915e683a3368f170`, full original source SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`. V35 C has original 1945 width2 color-fill strokes followed by 297 V18-B width1 detail strokes, total2242 strokes/5269 synthetic accepted vertices (NOT CHALK). Actual native original RGB MAE18.58220370, warm source HSV mask2946 px MAE36.08983933; visual readable, color MAE worse than V34R fill-only14.08882407/warm31.21305725. Hypothesis: changing only the *detail stroke RGB* toward local original colors can reduce dark-line color distortion, while preserving shapes/alpha footprints and some facial readability. The hypothesis can fail: lighter lines may disappear, reducing expression.

## Predeclared deterministic A/B/C

All variants copy **exact frozen V35 C** paths, all source color fill strokes, order, width and 0.25-shim endpoints; no stroke additions, omissions, reorderings, geometry, background or settings changes. Actual Egret Stage WebGL `BoardPane` via V35 separate width1 native handler; no cv2 rectangle/capsule as game footprint.

- **A:** frozen V35-C unchanged, original dark RGB [49,38,43] on all 297 detail strokes. Native full PNG must reproduce the frozen V35-C pixels exactly, else STOP.
- **B:** for each detail polyline, read **original source RGB** at each frozen logical point, mapping x logical `155..304` to source ROI x `0..149` and y `0..239`, using original 200×320 to ROI 150×240 LANCZOS transform. Round pixel coordinates by Python `round` (banker's nearest) then clamp to ROI edge; per-channel **lower median** across all sampled vertices. Use those 3 original byte medians as the entire detail stroke RGB. Paint unchanged.
- **C:** same vertex median per detail stroke, but source-aware dark tint set to nearest integer with **half-up** rounding of `(darkRGB + localMedianRGB)/2` independently per channel. Fixed mixing coefficient1/2, no posthoc tuning. Paint unchanged.

For B and C, one RGB is assigned per V18 path; do not sample output images or native renders to pick colors. `colorIndex=100` remains diagnostic detail-layer identity, not source class ownership. The source-color sampler is MODEL_ONLY for choosing candidate RGB, **not** an inference of native game footprint. B/C both use the **actual** native Egret width1 brush.

## Fixed metrics and validity

Verify original V35 artifact/report SHA and all inner hashes before use, 2242 strokes/5269 synthetic vertices, 297 detail routes, A control native RGBA pixel identity with V35 C, A/B/C exact native alpha equality for each isolated detail and full composite. All source LANCZOS ROI processing and original source SHA frozen. Source masks/thresholds and visual same crop unchanged. Record full ROI original RGB MAE and original warm HSV H5..55°, S>=0.30,V>=0.20 ROI MAE, detailed face/hair/hand visual crops, count colors/switches, 3 logical px native exterior leakage and overlap onto source target classes. Save raw native PNG for every isolate/composite, JSON config, path colors, reports and SHA256. No manual source overlay.

Interpretation: **candidate improves color fidelity** only if it reduces **both** full RGB MAE and warm MAE relative to V35 C and preserves alpha exactly. It is a *recognizability candidate* only if visually salient face/hair/hand lines remain legible versus V35 C (exploratory non-blind assessment). Full production quality gate remains >=99% per required color, <=3 logical px leakage and appropriate game quota/safety; no posthoc relaxation even if B/C numerically improve. No exact CHALK (only run-bound game Monitor `post.pointCount-pre.pointCount`), no E4/E5 without live game. Previous V35 negative RGB and V34/V34R results remain frozen.

## Pipeline

Minimal adapter into existing `tests/run_engine001_paint_then_detail_native_v35.py` or separate focused V36 test runner, no alternative renderer. Pin user source and V35 artifact input; preserve independent V36 artifact identity and failure evidence, compare native actual Egret RGB/alpha and inspect face crops. Begin as opt-in Windows GitHub Actions. Do not promote automatically based solely on MAE or recognizability.


## After-run evidence — V36 native actual Egret E3 (2026-11-15)

[CI43743810164](https://github.com/Kiddos19882/AutoDraw/actions/runs/43743810164) **E3 SUCCESS** at SHA `86f8d5d5a85d051b3883571de1f284430aac87b2`, all required native job steps PASS, original source-bound V35-C PNG control exactly reproduced in decoded RGBA, A/B/C full composite plus isolated actual BoardPane/Egret WebGL strokes captured. Artifact **14173870057**, ZIP SHA256 **`acf7743e283b33d5d8cb3da82934eb8a4d8fcad1f4bff6e6db5c7de1fc5ec318`**, all **24/24** report-linked SHA256 PASS. Actual native alpha identical across A/B/C for all composite and isolated color layers. Same paint-first/297 selected width1 detail routes,2242 strokes/5269 synthetic accepted vertices **NOT exact CHALK**.

| Variant | Actual native ROI original RGB MAE | Warm HSV original RGB MAE | Native composite alpha>=24 px | Detail strokes |
|---|---:|---:|---:|---:|
| A / V35-C dark [49,38,43] | 18.58220370 | 36.08983933 | 160904 | 297 |
| B / per-path original RGB lower median | **12.27775926** | **28.10126726** | 160904 | 297 |
| C / fixed half-up 50% dark / 50% local RGB | 14.46130556 | 29.84691107 | 160904 | 297 |

Both B and C **PASS the prereg color MAE non-regression relative to V35-C A** (full and warm). B yields lowest numeric RGB error; C retains darker contours and, in *non-blind single-image review*, more distinct hair/face and clothing boundaries, potentially better recognition than B. A's lines are darkest but wash out warm detail. This is an exploratory tradeoff; **no independently established semantic recognizability score**. Compared against the pure V34R color fill without lines, RGB MAE14.088824 and warm MAE31.213057, B improves both, C is slightly worse in full RGB but improves warm RGB. It is incorrect to call C universally optimal.

True native RGBA alpha unchanged from V35-C, thus earlier real native source-silhouette recall95.113906% and all related geometric/3logical-px-exterior **diagnostics** are invariant under V36 color-only substitution, on this frozen image, alpha threshold24. **Per-color >=99% final actual quality remains NOT_ACCEPTED**, no game E4/E5/exact CHALK or independent safety margin. Strong result is source-RGB fidelity improvement **with real game-shaped thin overlay lines**, not production acceptance.

**Classification:** `NATIVE_E3_PASS / RGB_FIDELITY_IMPROVEMENT / RECOGNIZABILITY_EXPLORATORY / COLOR_QUALITY_NOT_ACCEPTED / PRODUCTION_BLOCKED`. Preserve entire A/B/C and failed V35 pilot1, neither re-tune RGB mixing coefficients nor replace historical baselines. Next separately prereg source-aware high-fidelity **paint/region restoration** and semantic contour selection, focused on saturated orange/pink costume and facial/hand details, before game runtime eligibility.

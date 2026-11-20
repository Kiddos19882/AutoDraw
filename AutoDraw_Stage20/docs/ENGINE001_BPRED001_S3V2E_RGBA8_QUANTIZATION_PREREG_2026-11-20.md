# ENGINE-001 / BPRED-S3v2e — frozen E0 for lossful RGB8 unpremultiplication diagnostic

**2026-11-20: FROZEN BEFORE any S3v2e numerical evaluation/code/CI.** Research-only continuation of S3, NOT a new acceptance gate or S4 independent validation. Source pinned [S3v2d native run44697386598](https://github.com/Kiddos19882/AutoDraw/actions/runs/44697386598) code SHA `2ba4241be547cb14bfc0a180633ce7bfe6a9ab9a`; archive [artifact14610824409](https://github.com/Kiddos19882/AutoDraw/actions/runs/44697386598/artifacts/14610824409), report `ENGINE001_BPRED_S3V2D_TRUE_MAIN_CANVAS_VS_WEBGL_V1`; original prereg S3v2d blob `1eb60858facc4d208f238ca9bb1c39e2f937ca1b`. Earlier source S3 H1 final WebGL **FAIL 30/40**, S3v2d main Canvas 38/40 (FAIL 2), final WebGL 10/40 (FAIL 30); no alteration of any frozen science.

## 1. Reasoned hypothesis and existing evidence, no hidden independent claim

S3v2d archived real Egret Firefox159.0 true main Canvas and final WebGL alpha are identical per physical pixel for 80 scenes; on posthoc pixel audit 12,694 RGB differences occurred only on partially transparent (1..254) pixels; fully opaque and zero-alpha unchanged. A handful of already inspected observed values, e.g. RGBA `(80,60,52,64)` became `(84,64,56,64)`, suggest an 8-bit premultiply/unpremultiply integer rounding path. This exploratory clue **precedes prereg** and therefore the 80 source scenes are *known calibration/diagnostic data*, never independent proof. WebGL 1.0 spec allows lossy RGB during HTMLCanvasElement 2D → WebGL texture upload because some implementations store premultiplied alpha; it does **not** specify the exact Egret/Firefox rounding path: [Khronos WebGL1 spec](https://registry.khronos.org/webgl/specs/latest/1.0/), [MDN pixelStorei](https://developer.mozilla.org/en-US/docs/Web/API/WebGLRenderingContext/pixelStorei).

Hypothesis to *check* (not assert): an explicitly preselected byte-limited channel transform is sufficient to explain a large fraction of native Canvas→WebGL RGB differences without moving alpha. Alternative explanations must be retained (color-space conversion, upload format, shader, framebuffer readback). Neither stage-varying textures nor exact native GL state were measured yet.

## 2. Frozen source and deterministic candidates (Q0/QF/QR/QC)

Use only 80 original primary pairs in S3v2d raw archive (80 main aligned Canvas and 80 final WebGL), plus 40 frozen AB/BA target composites for source-over check. Reverify ZIP CRC, `report.json` SHA256 for **all 655 listed members**, code SHA/run ID, source stage H1 38/40 and final H1 10/40, 80/80/91 count and frozen E0 blobs before any numeric metrics. No S0 BLIND, no downstream original E/F acceptance.

For every physical RGBA pixel with channel integer `c in 0..255` and `alpha a in 1..254`, define `p=c*a/255.0`; candidate channel `u=clip(np.rint(255*q(p)/a),0,255)` using exact float64 intermediate and NumPy nearest-even final rounding, where:
- **Q0 identity:** `u=c` (unchanged original true Canvas).
- **QF floor:** `q(p)=floor(p)`.
- **QR nearest:** `q(p)=np.rint(p)`.
- **QC ceil (preselected primary):** `q(p)=ceil(p)`.

At `a=255` return original `c` byte exactly; at `a=0` preserve original RGB (avoid inventing values) and alpha `a` unchanged for ALL Q. Preserve all physical coordinates, no alpha extrapolation, gamma, learned offsets, palette, masked exclusions or posthoc tuning. Check channel-wise vectorization agrees scalar cases; refuse any non-uint8 RGBA, missing/duplicate ZIP entries, metadata drift, untracked PNG, missing stage pairs or non-finite division. Compute direct native stage differences on all pixels including transparent RGB in a separate counter.

## 3. Frozen measurements and scientific decision

**D1 direct-stage diagnostic:** for each Q and each of 80 source main→WebGL samples record exact mismatched physical RGB pixel count, changed alpha count, RGB channel MAE/max, errors stratified by alpha bins `1..15`,`16..63`,`64..127`,`128..254`, `255`, `0`, and by variant/width/relation. Baseline Q0 source measurements: 12,694 physical RGB pixel occurrences changed, **zero alpha differences** across80; do not drop low-alpha pixels or modify source after viewing. **Primary diagnostic H1-QC: QC must have strictly fewer than 12,694 RGB-mismatching pixel occurrences than Q0, and no changed alpha pixels; otherwise FAIL.** This is not physical model safety gate. QF/QR are predeclared negative/comparator controls, not a search-driven acceptance threshold.

**D2 frozen ordered C0:** take real isolated source main Canvas A/B for each width×relation pair, apply the *unchanged original* `s3.source_over(bottom, top)` to produce 40 predicted ordered Canvas scenes; transform with each Q, then compare to actual frozen WebGL ordered targets, using original frozen S3 H1 **max ≤2/255, mean ≤1/255 per ordered variant union**. Baseline original WebGL H1 remains **10/40** from true isolated WebGL, and native Canvas H1 remains **38/40**; do NOT reclassify these baselines with any Q. Report separate candidate `QC_C0_to_WebGL` PASS count; **primary diagnostic H2-QC: QC candidate must exceed original 10/40 WebGL PASS count, else FAIL**; even PASS still MODEL_ONLY and not validated on untouched holdout.

**D3 residuals:** explicitly report S3v2d Canvas original W04/NEAR_PARALLEL_OVERLAP/B_THEN_A max3 and W10/NEAR_PARALLEL_OVERLAP/A_THEN_B max4 errors as existing science residual, never quietly suppress. Preserve metrics of all 40 candidates and all original 80 source scenes, including failures.

## 4. Implement/run limits and evidence

Create one research-only offline harness reusing S3 native source_over/rgba_difference and the immutable S3v2d artifact; focused deterministic synthetic Q0/QF/QR/QC, malformed-source, strict SHA regression tests; isolated CI downloads original real artifact using exact run ID. Freeze THIS E0 Git blob and prereg data/protocol before adding any S3v2e implementation or executing new candidate calculations. CI must store deterministic JSON, per-variant metrics, SHA/CRC and negative outcomes in a separate new archive, not overwrite original raw. No new Egret scenes required for this E1/E2 diagnostic; its provenance is source-native E3 but **S3v2e itself is NOT new native E3 or independent S4**.

If QC fits, next separately preregister a true new-native cross-phase/angle validation with actual GL-state/source instrumentation inside S3 before asserting causal texture mechanism; otherwise retain failures and pursue alternate alpha representation hypothesis. Original E/F protected quality, source owner protection, safety gates, Stage6/executor, game renderer/Monitor/Bridge, master remain untouched. E4/E5/exact game CHALK NOT_RUN.

# ENGINE-001 / BPRED-S3v2o — NEW original Egret low-alpha source RGB: P1 PASS, P2/P4 FAIL

**Measured 2026-11-20, no criterion relaxation.** New independent original Egret source-family E3 + E2 technical **PASS** on exact code SHA `207b070d3e788c28e111dbe96a770e5d02e43169`, [CI44782393795](https://github.com/Kiddos19882/AutoDraw/actions/runs/44782393795). Scientific **P1 PASS_NEW_NATIVE_E3_SOURCE_ONLY**, **P2 FAIL**, **P3 DIAGNOSTIC_ONLY (none safe)**, **P4 foreign owner FAIL**, first/last source fidelity PASS. No S0 BLIND/S4, game E4/E5 or exact CHALK. No production/Stage6/Bridge/Monitor/master change.

## Frozen prerequisites and primary evidence

Pre-code original [S3v2o E0](ENGINE001_BPRED001_S3V2O_NEW_NATIVE_LOW_ALPHA_READBACK_PREREG_2026-11-20.md) Git blob `72343545d1f8645625085afb36e5fddeda2f91c8`, committed `ab7aecf2262759e58225bf6c132a7544c0346d01` BEFORE all S3v2o code and native outcomes. Previous immutable [S3v2n results](ENGINE001_BPRED001_S3V2N_CORRELATED_ALPHA_PREMULT_RESULTS_2026-11-20.md), original G3 E0 blob `81f1a18ed5b04265123c337a3cbd63985a835307`: original known 40 isolated source PNG P1 0/8648 misses but P2 **6851/7753=88.3658% FAIL** vs frozen >=90%; original 327 earlier F2 RGB failures recovered; original source alpha0 owner harm21; original QH WebGL C0 21/40. The new 80 cases have new colors, phases, geometry and same pinned original Egret5.4.1/Firefox159 source and observer, not a re-evaluation of the previous 40.

New code limited to (ф) `tests/run_engine001_bpred_s3v2o_new_native_low_alpha_readback.py`, (ф) `tests/test_engine001_bpred_s3v2o_new_native_low_alpha_readback.py`, (ф) `.github/workflows/engine001-bpred-s3v2o-new-native-low-alpha-readback.yml`, with verified reuse of original S3v2j true stroke/Canvas/mask/WebGL observer. CI E2 13 new S3v2o + 11 S3v2n +10 S3v2j +9 S3v2i = **43 unit tests PASS**; original source Git blob verification PASS, script/JS compilation and Markdown audit PASS. In CI E3 source **80** unique real main Canvas1392x732 and **80** mask Canvas1380x720, 80 original WebGL plus 10 ROI-exact repeats plus one blank (**91** true WebGL), all immediate true original main `stroke()` snapshots saved, and signed source/runtimes/step/case IDs. Frozen E0 and original first-owner provenance verified.

[Raw CI artifact14652269071](https://github.com/Kiddos19882/AutoDraw/actions/runs/44782393795/artifacts/14652269071) independently downloaded: **860 ZIP members including report.json; CRC PASS; 859/859 member SHA-256 PASS**; ZIP SHA256 `351668166353a627b182798a17687a976c0a2ec3d9d2707ebc8effc9416cf4b7`, matches GitHub artifact digest. Raw report pinned exact run `44782393795` / code `207b070d3e788c28e111dbe96a770e5d02e43169`. No regenerating old captures, no posthoc scene modification. Initial [CI44781811958](https://github.com/Kiddos19882/AutoDraw/actions/runs/44781811958) failed **technical pre-E2** due to Windows checkout on-disk blob-byte mismatch; fixed only workflow source restoration from original pinned Git objects. [CI44782232152](https://github.com/Kiddos19882/AutoDraw/actions/runs/44782232152) cancelled by subsequent reproducibility guard commit. Historical failed/cancelled statuses retained, not rewritten PASS.

## Frozen primary scientific results

| E0 criterion | Actual independently captured native Egret result | Status |
|---|---|---|
| P0 original source and raw/manifest integrity | 80 true original native cases, 10 identical replay ROI, blank alpha0, E0/source SHA verified; ZIP CRC &859 SHA | **PASS E2/E3 provenance** |
| P1 G3 original source partial-alpha RGB coverage | **0 misses of 9,666** at A1..254 on 40 new A_ONLY/B_ONLY Canvas source | **PASS_NEW_NATIVE_E3_SOURCE_ONLY** |
| P1 original source fully opaque control | **60,197 /60,197 RGB exact**, misses0 | **PASS** |
| P2 G3 informative triple RGB intervals width<=16 at A16..254 | **7602/8614 =88.2516833%**, need >=90% =7753, deficit **151** | **FAIL** |
| P3 per-mode `floor` | informative 8414/8614=97.678%; **1911 actual RGB misses** | **FAIL for safe single-mode**, DIAGNOSTIC |
| P3 `nearest_even` | informative 8450/8614=98.096%; **959 actual RGB misses** | **FAIL for safe single-mode**, DIAGNOSTIC |
| P3 `ceil` | informative 8406/8614=97.585%; **3045 actual RGB misses** | **FAIL for safe single-mode**, DIAGNOSTIC |
| P4 first actual source owner vs same-run isolated owner | **40/40 full RGBA exact** | **PASS** |
| P4 final actual stroke snapshot vs true main Canvas | **80/80 full RGBA exact** | **PASS** |
| P4 isolated top alpha0 with lower-owner alpha>0 | **17 true lower-owner changed RGBA physical pixel occurrences**, including one-byte RGB changes, in 9 ordered scenes | **FAIL foreign owner safety** |
| Original source-over C0 on NEW ordered cases | Canvas **25/40** pass frozen max<=2/mean<=1; QH-WebGL **8/40** pass | **FAIL original composition model** |
| Original Canvas→WebGL QH stage | **0 RGB mismatching physical pixels; 0 alpha mismatches** across 80 cases | **PASS stage-only** |

G3 new native source buckets: alpha1..15 has1052 UNKNOWN_LOW_ALPHA, alpha16..63 has1801 pixels of which789 informative and **1012 UNKNOWN_WIDE**, alpha64..127 has1972/1972 informative, alpha128..254 has4841/4841 informative. New G3 nonvacuity failure is **not a reclassification** of previous S3v2n 902 unknown at A16..63 on old data. Each frozen E0 criterion is evaluated on its own correctly denominated population, with zero width/tolerance adjustment.

Single-mode floor/nearest-even/ceil would make the interval more usable but **all three exclude genuine native RGB**; per-pixel/per-width/per-color rounding-mode selection is not allowed. All 5915 P3 interval miss occurrences (1911+959+3045) are in the raw archive with physical coordinates and channel bounds; G3 itself had **zero misses**. Per-bin misses:
- alpha1..15: floor881, nearest359, ceil910;
- alpha16..63: floor933, nearest407, ceil1436;
- alpha64..127: floor97, nearest193, ceil699;
- alpha128..254: 0 for each mode.
No new accepted quantizer or CPU-specific mechanism inferred from a single held-out family.

P4 actual isolated-top-alpha0 owner harm: **17 pixels in 9 ordered scenes**, widths **4,6,7,8,9,10**. Example width4 `CROSS_ROTATED A_THEN_B` physical (522,346): lower-only RGBA (227,148,34,255), independently top-only RGBA (0,0,0,0), ordered actual (226,147,34,255), signed RGB (-1,-1,0). Lower-owner identity is changed despite top isolated exported alpha0; **zero foreign-owner protection not met**, even though WebGL stage itself has zero mismatches. Actual internal sub-byte coverage/blending or readback mechanism remains **unproven**. Preserve all 17 true negative native coordinates; do not treat difference <=1 as permitted or adjust existing protected gates.

## Interpretation, what remains open, next action

1. The original mathematical *union* G3 transfers to genuinely new native source data without RGB false exclusions (**P1 E3 PASS**), but is too conservative to be a useful source predictor at fixed 90% (**P2 FAIL by151**). Good calibration of source RGB alone does **NOT** prove safe overlapping-color composition.
2. Simple one-mode rounding is empirically refuted as a source-wide safe rule. The scientific root cause of low-alpha RGB uncertainty and 17 alpha0 neighbor effects is still open. The new native composition source Canvas C0 25/40 / QH WebGL8/40 fails; stage-only QH zero pixel errors does not fix Canvas owner mixing.
3. **NEXT one S3 step, separately frozen E0 before new code/data tests:** discriminate the original Firefox159 Canvas2D low-alpha *readback vs actual compositing* mechanisms using original genuine intermediate captures and new independent source family, preserving G3 envelope and protected zero-foreign gates. Inspect independent `getImageData`/Canvas PNG readback where available, alpha0 owner effects, phase/width strata, avoid assuming hidden internal premult bytes are observable through PNG. Do NOT promote a mode based on this new E3 or retune after 17 effects. Require new prospective native validation before any source-owner-safe decision.

S0 BLIND remains reserved sealed; S4 NOT_RUN; original P4D18 E/F protected full-quality **FAIL unchanged**; E4 live game, E5 independent runtime, and run-exact CHALK `post.pointCount-pre.pointCount` all NOT_RUN. No source candidate, Stage6, Bridge, Monitor, production or master modification.
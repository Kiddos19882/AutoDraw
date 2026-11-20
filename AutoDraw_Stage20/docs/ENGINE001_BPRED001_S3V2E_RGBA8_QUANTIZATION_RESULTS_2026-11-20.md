# ENGINE-001 / BPRED-S3v2e — RGB8 quantization source-stage diagnostic results (2026-11-20)

**Scope and decision:** Existing original Egret source only; **E2 PASS / diagnostic H1-QC PASS / diagnostic H2-QC PASS; original S3 physical H1 FAIL and full-quality acceptance BLOCKED**. No new native experiment (E3 inherited from S3v2d; S3v2e is offline E1/E2, not independent S4 or game E4).

Frozen before code / full calculation: [S3v2e E0](ENGINE001_BPRED001_S3V2E_RGBA8_QUANTIZATION_PREREG_2026-11-20.md) Git blob `cab7f2d0867e87201913d588357bc1adc045e8ef`. Input is prior [S3v2d original native E3](ENGINE001_BPRED001_S3V2D_MAIN_NODE_STAGE_RESULTS_2026-11-20.md) [CI44697386598](https://github.com/Kiddos19882/AutoDraw/actions/runs/44697386598), SHA `2ba4241be547cb14bfc0a180633ce7bfe6a9ab9a`, [raw artifact14610824409](https://github.com/Kiddos19882/AutoDraw/actions/runs/44697386598/artifacts/14610824409).

Final reproducible [S3v2e CI44699876591](https://github.com/Kiddos19882/AutoDraw/actions/runs/44699876591) SHA **`bf389d37d3a16bc4931e945e247a802b59f8069f`** technical **SUCCESS**, 8 new Q+14 S3v2+14 S3 focused E2 **36/36 PASS**, Python compile, Markdown integrity PASS. Repacked original 656 ZIP members with CRC and validated 655/655 source member SHA256 plus original source H1 Canvas38/40 and WebGL10/40, no source mismatch/BLIND. [Result JSON ZIP artifact14612491268](https://github.com/Kiddos19882/AutoDraw/actions/runs/44699876591/artifacts/14612491268) successfully uploaded, nonempty. Independent ZIP CRC and both tracked output member SHA256 verified; 80 stage rows and 20 relation/width pairs with 40 ordered comparisons. First [CI44699612034](https://github.com/Kiddos19882/AutoDraw/actions/runs/44699612034) performed identical science calculation and E2 PASS, but **did NOT upload archive** because result directory is hidden. Workflow-only upload fix `include-hidden-files:true` + `if-no-files-found:error` before final run; historical missing-artifact weakness preserved.

## D1: actual Canvas → WebGL stage mismatch against frozen Q candidates

For every original 80 real Egret 1380×720 aligned main Canvas and corresponding WebGL PNG, compare full RGB at physical pixels, no excluded alpha or coordinate shifts. All 80 actual alpha channels are **identical** between main Canvas and WebGL.

| Frozen candidate | RGB-different physical pixel occurrences (80 scenes) | Status |
|---|---:|---|
| Q0 original Canvas unchanged | 12 694 | Baseline |
| QF `floor(c*a/255)` then `np.rint(255*p/a)` | 14 250 | Worse than baseline |
| QR `np.rint(c*a/255)` then `np.rint(255*p/a)` | 12 694 | No improvement |
| **QC `ceil(c*a/255)` then `np.rint(255*p/a)`** | **70** | **Diagnostic H1-QC PASS**, 99.4485% fewer mismatches than Q0 |

Each mode preserves source RGB at alpha0 and alpha255 and preserves all actual alpha values. **QC residual 70 physical pixel occurrences across 43 scenes**, alpha bands: 63 in 16..63 and 7 in 64..127, zero in all other frozen alpha bins. Source differs only RGB for fractional alpha. This result is on known diagnostic scenes, **not** validation of an independent model or proof of exact Egret internal GL state.

## D2: frozen original C0 applied to true Canvas, Q correction against true WebGL

For 40 A_THEN_B/B_THEN_A variants, take **true isolated main Canvas** A/B from native S3v2d, compute unchanged original straight-sRGB `s3.source_over` and apply each Q before comparison with true ordered WebGL. Original **max channel≤2/255 AND mean≤1/255** per variant, not retuned.

| C0 path | Variants passing same numerical H1 /40 |
|---|---:|
| Original true isolated final WebGL C0 (original scientific baseline, not Q result) | **10/40** |
| True Canvas original C0, Q0 | 0/40 |
| True Canvas original C0, QF | 0/40 |
| True Canvas original C0, QR | 0/40 |
| True Canvas original C0, QC | **19/40** |

Preregistered **H2-QC PASS** because 19>10. But **21/40 still FAIL** original H1. The 0/40 Q0 comparator is **not** the original WebGL10/40 baseline; they use distinct source stages and must not be conflated. Original S3 source C0 **H1 FAIL30/40**, S3v2d main Canvas H1 38/40 (**2 FAIL**), S3v2d final WebGL 10/40 (**30 FAIL**) remain unchanged. S3v2e is not permitted to reclassify them.

## Optional posthoc clue, not preregistered Q model or independent acceptance

After inspecting frozen QC residuals, a separate **E0 hypothesis-generating** check of actual raw S3v2d pixels found all 70 QC residual occurrences at unpremultiply **half-integer ties**, where `np.rint` (ties-to-even) selects a byte one below actual WebGL. On the **same already-seen 80 scenes only**, replacing this last rounding by `floor(x+0.5)` eliminates those 70 residuals (0 direct-stage mismatches); this is **posthoc**, outside frozen Q0/QF/QR/QC, **not a new scientifically PASS criterion**. Real texture upload, premultiplication state, shader/readback and source renderer rounding implementation have not been instrumented, so exact causal attribution remains UNKNOWN. This is a starting hypothesis for separately frozen new-native evidence, not grounds to modify frozen S3 or production.

## Limitations and next step

- The source is genuine Egret/E3 from existing S3v2d, not new independently sampled native data; S3v2e is offline E1/E2 on known 80 scenes. Q0/QF/QR/QC success is diagnostic only.
- 21 ordered QC/C0 variants still violate the protected **unchanged** H1; two main Canvas variants have inherited H1 failures. Original S3 M2 owner model remains **MODEL_ONLY_UNSAFE**, original E/F P4D18 protected-white/source-owner quality **FAIL**. DEC-042 adaptive admissibility not yet implemented, quality gates unchanged.
- Reserved S0 **BLIND unopened**; no E4 game run/E5 independent/exact game CHALK; original renderer, Stage6, Bridge, Monitor, production, master untouched.

**NEXT one S3 step:** freeze separate prospective E0 for **new native** original Egret cases with different widths, angles, fractional positions, colors, and actual Canvas→WebGL capture/GL-state diagnostics. Prospectively compare pre-specified QC vs the now posthoc half-up hypothesis, report all 80 archived residuals and 21 ordered failures unchanged, and do not treat S3 source pixel-fidelity as solved. Move to S4 reserved BLIND and S5 original E/F only after appropriate independent native validation and no quality-gate violation.

# ENGINE-001 / BPRED-S3v2p — true original Egret Canvas getImageData versus PNG: byte readouts DIFFER, real owner harm in BOTH

**2026-11-20 measured from original native data.** Exact CI [44786503347](https://github.com/Kiddos19882/AutoDraw/actions/runs/44786503347) commit `0af378baf4f637a3248e822b203344aef5c75bfb`, technical **E2 42/42 PASS** (12 new + 11 S3v2n +10 S3v2j +9 S3v2i), **E3 80/80 true original Egret sources PASS** and independent ZIP CRC +1074/1074 member SHA-256 PASS. Scientific H0 source/provenance PASS, **H1 DIFFERENT_OBSERVED_READBACK**, **H2 foreign-owner safety FAIL**, H3 genuine first/last snapshots PASS but original compositing C0 still FAIL, **H4 G3 RGB coverage PASS_SOURCE_ONLY and usefulness FAIL**. No new production source-owner-safe model. No S0 BLIND/S4, E4 live game, E5 independent game or run-exact CHALK.

## Pre-code frozen prereg and real provenance

First [frozen S3v2p E0](ENGINE001_BPRED001_S3V2P_NATIVE_CANVAS_READBACK_VS_COMPOSITION_PREREG_2026-11-20.md), Git blob `44d6f3d72ed6c62f38054d11f050ee16cab50bc2`, committed `5388f7dea669caabdb0a3224a3e8d3e09a4ff84b` **before new S3v2p code and native measurements**; prior baseline HEAD `55ee8b58f3e8a47471802da1644adc406c744e2a`. No frozen acceptance adjustment. Research only:
- (ф) `tests/engine001_bpred_s3v2p_canvas_readback_observer.js`: wraps *original* `CanvasRenderingContext2D.stroke()` plus original native S3v2h observer, captures `getImageData` bytes after genuine native main stroke and before original PNG. Restores prototypes, no custom stroke rasterizer/`putImageData`.
- (ф) `tests/run_engine001_bpred_s3v2p_native_canvas_readback_vs_composition.py`: 80 genuinely new original Egret scenes, node-local physical readback ROI `x400,y220,w270,h270`, original source x/y alignment `-6,-6`, exact raw `.rgba` vs same-stroke PNG and both-path foreign-owner pixel audit.
- (ф) `tests/test_engine001_bpred_s3v2p_native_canvas_readback_vs_composition.py`: 12 source geometry/phase/owner, alpha0 byte regression and provenance tests.
- (ф) `.github/workflows/engine001-bpred-s3v2p-native-canvas-readback-vs-composition.yml`: pinned original engine/renderer, Firefox159, original Egret/S3v2j research parents and first E0 Git blobs, E2/E3/independent raw verifier.

Original Egret5.4.1 on Windows Firefox159 generated **80** NEW source plans (widths1..10, two relations, A/B/AB/BA), **80** original main Canvas 1392x732, **80** original mask 1380x720, **200** true original post-`stroke()` main PNG, **200 matched direct** `getImageData` RGBA source captures (raw bytes, SHA), 80 final real WebGL + **20 uninstrumented independent repeat controls** whose 162x162 ROI was full RGBA exact +1 blank = **101** WebGL PNG. Original first native owner 40/40 RGBA exact and last genuine stroke PNG vs original main Canvas 80/80 exact. No S0 BLIND or old S3v2o source plan reuse. Source-owner color RGB/angles/phases not fitted to 17 old negative pixels.

[Raw artifact14655565202](https://github.com/Kiddos19882/AutoDraw/actions/runs/44786503347/artifacts/14655565202) downloaded and independently inspected: **1075 ZIP entries including `report.json`**, full ZIP CRC PASS, **1074/1074 report-member SHA-256 PASS**, archive SHA-256 `27afcbaede715df22349d0cfbf2aa1b09691ee3233e591bdd2097de1864570dd` equals GitHub artifact digest. The raw `report.json` pins exact E0 blob, CI run, code SHA and browser; source, plans, raw node-local RGBA, true intermediate PNG, per-pixel signed negatives and controls are retained. This is genuine original Egret source E3, **not a live user-game E4**.

Early [CI44786045825](https://github.com/Kiddos19882/AutoDraw/actions/runs/44786045825) technical E2 FAIL before native due to missing `width/relation/variant` in synthetic test fixture for the negative alpha0 case (not source renderer bug), corrected only test fixture commit `0af378ba`; subsequent [CI44786417742](https://github.com/Kiddos19882/AutoDraw/actions/runs/44786417742) CANCELLED due to later source-test commit; preserve both technical outcomes and do not count as successful native E3. Final CI44786503347 exact E2/E3 and independent archive PASS. Final code diff is research scripts/observer/tests/CI and documentation only; no original Egret, production/Stage6/Bridge/Monitor or master changes.

## Frozen H0–H4 results on fresh independent source

| Frozen E0 measurement | Observed real original Egret | Scientific status |
|---|---|---|
| H0 original source/ROI/prototype/ZIP/provenance, genuine 80+20+blank | Native E3 and 1074 SHA/CRC verified | **PASS technical** |
| H1 direct getImageData vs original Canvas PNG same actual stroke | **51,275 different physical pixel occurrences across 200 original snapshots**; all on alpha1..254 | **DIFFERENT_OBSERVED_READBACK** |
| H1 changed channels and sign | **83,494 RGB channel byte differences; 83,494 exclusively −1 (getImageData − PNG)**; max abs 1; alpha differences **zero** | **MEASURED**, not internal precision proof |
| H2 isolated-top-alpha0 foreign-owner effects, PNG | **17** real physical pixel occurrences in 9 ordered scenes | **FAIL** zero-foreign |
| H2 isolated-top-alpha0 foreign-owner effects, getImageData | **17** at exactly same physical pixels; BOTH17, PNG_ONLY0, GETIMAGE_ONLY0 | **FAIL** zero-foreign |
| H3 first real stroke vs isolated main Canvas | **40/40 full RGBA exact** | **PASS** |
| H3 last true original stroke vs original main Canvas | **80/80 full RGBA exact** | **PASS** |
| H3 original straight-sRGB C0 composition | Canvas **30/40**, QH-WebGL **14/40** at original max<=2/mean<=1 | **FAIL** original C0 |
| H3 PNG Canvas→WebGL QH stage | **0 RGB, 0 alpha** differing physical pixel occurrences | **PASS stage-only** |
| H4 unchanged original G3 single-owner source coverage | **0 / 9,783** partial-alpha native RGB misses; opaque **60,189/60,189** exact | **PASS_SOURCE_ONLY** |
| H4 unchanged G3 useful all-three-RGB width<=16 among A16..254 | **7,725/8,690 = 88.8952819%**, need >=90% / at least7,821; **96 short** | **FAIL** |

### H1 distribution and exact sign

| Original PNG alpha stratum | Different PNG/getImageData pixel occurrences |
|---|---:|
| 0 | **0** |
| 1–15 | **4,227** |
| 16–63 | **9,411** |
| 64–127 | **10,841** |
| 128–254 | **26,796** |
| 255 | **0** |
| **All** | **51,275** |

All RGB channel deltas in `EVERY_TRUE_MAIN_READBACK_VS_PNG_DIFFERENT_PIXEL.json` are `-1` in `getImageData` relative to original `toDataURL` PNG; zero positive deltas, zero alpha deltas, no clipping at fully opaque or completely transparent original exported alpha. Up to three RGB channels can differ for one physical pixel; those 83,494 channel occurrences must NOT be confused with 51,275 pixel occurrences or unique board coordinates. Both readouts are exports of the same underlying Canvas; this observation does **not** identify hidden browser internal premultiplied raster bytes. [WHATWG Canvas](https://html.spec.whatwg.org/multipage/canvas.html) explicitly notes loss of precision on premultiplied/unpremultiplied conversion; do not infer rounding mode solely from this signed difference.

### H2 foreign-owner source harm is NOT explained by PNG-only serialization

All **17** original lower-owner changed pixels are exactly the same in independently collected PNG and getImageData comparison: BOTH17, PNG_ONLY0, GETIMAGE_ONLY0. For every such pixel the independently rendered top-owner alpha==0 and lower-owner alpha>0; RGB changed by exactly1 byte in each affected channel of the actual ordered source main Canvas. They occurred in **9** ordered new native scenes, widths3,5,6,8,9,10. Example width3 `CROSS_ROTATED B_THEN_A` physical aligned board `(544,335)`: isolated lower PNG and raw readback RGBA `(50,148,111,255)`, separately isolated top `(0,0,0,0)`, actual ordered in **both** readouts `(50,147,111,255)`. Signed change `(0,-1,0,0)`. No 1-byte forgiveness, protected-owner-zero remains FAIL.

Consequently, a correction limited to `PNG serialization vs getImageData` cannot remove the observed foreign-owner changes **on these readouts**. They may share common loss/rounding in Canvas compositor or before both readouts, or depend on actual subbyte coverage; the exact internal source-over mechanism is **UNKNOWN**. Do not overstate the evidence as direct proof of a specific Firefox blending implementation.

### H4 remaining source uncertainty

| Native isolated-source alpha | Physical pixels | G3 informative | UNKNOWN |
|---|---:|---:|---:|
| 1–15 | 1093 | 0 | 1093 |
| 16–63 | 1798 | 833 | 965 |
| 64–127 | 1993 | 1993 | 0 |
| 128–254 | 4899 | 4899 | 0 |

G3 transferred without false RGB exclusions on this new family, but 88.90% usefulness remains below the original frozen 90% bar; previous [S3v2o](ENGINE001_BPRED001_S3V2O_NEW_NATIVE_LOW_ALPHA_READBACK_RESULTS_2026-11-20.md) 88.25% FAIL and [S3v2n](ENGINE001_BPRED001_S3V2N_CORRELATED_ALPHA_PREMULT_RESULTS_2026-11-20.md) 88.37% FAIL retain their original sample denominators and cannot be retroactively renamed PASS. None of the old single-mode floor/nearest/ceil diagnostics was accepted as a safe model.

## Interpretation, blockers, next single planned S3 step

1. **Established on E3:** Same actual Canvas stroke yields systematically different exported partial-alpha RGB from PNG vs direct getImageData (exactly −1 byte for every disagreeing channel), but original top-alpha0 foreign-owner harm persists identically in both observations. The Canvas→WebGL QH stage is byte-exact on original native PNG inputs, and 20 independent uninstrumented repeat controls are exact. This separates one measurable readback effect from one persistent source-owner risk; does not prove complete internal composition model.
2. **Unresolved:** Whether the 17 shared foreign-owner changes come from actual subbyte alpha coverage, premultiplied integer storage transitions, or common internal conversion before both observations is **UNKNOWN**. Original straight-sRGB owner C0 still scientifically FAIL30/40 Canvas and14/40 QH-WebGL. G3 nonvacuity H4 FAIL by 96; neither issue can be addressed by relaxing original thresholds or fitting individual rounding modes to held-out data.
3. **NEXT bounded S3 only:** separately preregister a *mechanism-discriminating original native Canvas micro-alpha owner experiment* that uses a truly new source family and additional intermediate evidence (e.g. first owner genuine source plus top actual incremental changes, independent isolated-top readouts and native phase/angle strata). Before any new arithmetic/implementation, freeze candidate mechanisms, controls and owner-zero acceptance in a new E0. Preserve all 17 original S3v2p foreign-owner negatives and full original 51,275 readback discrepancies as signed immutable evidence. Do not reuse this holdout to tune or promote single-mode physics.
4. Original P4D18 full protected E/F **FAIL unchanged**, S0 BLIND sealed and S4/S5/S6 NOT_RUN, E4 live game/E5 independent runtime/exact CHALK `post.pointCount-pre.pointCount` NOT_RUN; Stage6/Bridge/Monitor/production/master unchanged. Engineering evidence for this model is source-native E3 within this pinned browser/engine family, not a demonstration of image-level or in-game correctness.

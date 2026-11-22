# ENGINE-001 / BPRED-S4-R1 — S4.6 original CTR1 quarantined source-contract E2 (2026-11-23)

**Signed E2 source schema TECH PASS / S4.5 important detail PARTIAL / S4 map acceptance FAIL/BLOCKED / S5 BLOCKED / native NOT_RUN.** Branch `feature/image-geometry-optimization`, final tested code SHA [`86c5133c9c2cb2603cfaf1bdab872705a3b7de88`](https://github.com/Kiddos19882/AutoDraw/commit/86c5133c9c2cb2603cfaf1bdab872705a3b7de88), [S4.6 isolated GitHub Actions run 45074109363](https://github.com/Kiddos19882/AutoDraw/actions/runs/45074109363), completed SUCCESS. Frozen [S4.6 E0](ENGINE001_BPRED001_S4R1_S46_SOURCE_CONTRACT_PREREG_2026-11-23.md) Git blob `0da1fd6689f4396862da688dc214b897ab6e46f7` was committed in [89fc332](https://github.com/Kiddos19882/AutoDraw/commit/89fc3325d1299cbf97d17f20994fedd50273210b) BEFORE the first S4.6 source code [0c51cb9](https://github.com/Kiddos19882/AutoDraw/commit/0c51cb9aee93cf6c0d9a750f4429abb6eb311149). Real128 game engine blob `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388` pinned.

## Result and checks

Single new research-only source validator/serializer in `tests/engine001_bpred_s4r1_s46_source_contract.py`, synthetic tests in `tests/test_engine001_bpred_s4r1_s46_source_contract.py`, four-original runner in `tests/run_engine001_bpred_s4r1_s46_dev.py` and isolated `.github/workflows/engine001-bpred-s4r1-s46-source-contract.yml`; existing CTR1 builder, palette reader and source decoder are **reused** without changing their code or production. For each original source file: re-decode fresh original bytes, recompute provisional DG1+CTR1 from same original twice, check byte-identical full JSON+NPZ; output 12 source arrays including decoded original RGB/alpha, original pixel-corner contour 10-column segments and Lab source contrast, region/surface/paintable IDs, game128 swatch index, protected original dot, genuine source alpha, source-edge, source adjacency and preview, with SHA per array and raw ZIP/NPZ SHA. Geometry remains source-only, no strokes or game calibration.

**S4.6 E2:** 11/11 synthetic tests PASS including positive original alpha/different-swatch/same-swatch and negative wrong original SHA, mutated segment source IDs/geometry/Lab, game color range, alpha, provenance, fake native coordinates and attempted status promotion. Four full original DEV each twice deterministically produced exactly one quarantined packet per source; full SHA/provenance CI validation completed. Output observed contour segments: wV **15,879**, Hello Kitty **14,604**, EZAL **88,167**, Pink Kitty **15,897** (source geometry, not game strokes).

| Source | Original source SHA256 prefix | Output raw NPZ SHA256 prefix | Manifest SHA256 prefix |
|---|---|---|---|
| wV 200×320 | `07cc4568` | `62ada78b` | `b5b75aec` |
| Hello Kitty 311×360 | `9c120316` | `405c95bc` | `96fadb48` |
| EZAL 1235×1920 | `51a55d95` | `63435b34` | `b5dad0fd` |
| Pink Kitty 554×554 | `62821b52` | `730bd530` | `e5ea2ab1` |

[Artifact14774034693](https://github.com/Kiddos19882/AutoDraw/actions/runs/45074109363/artifacts/14774034693): downloaded into independent project analysis; **4,556,279 bytes**, SHA256 `63ad479b26b097a9980b99701326ce6a41ea355cf536d99f7b61cb1906966581`. ZIP CRC **9/9 PASS**; all four source JSON/NPZ pairs, raw SHA, per-array shapes/dtypes and array SHA256 independently verified **48/48 PASS**; source input SHA values match separately verified frozen user CTR1 original SHA values. This independently verifies the exported files, but does **not** independently validate scene semantics or native effects.

## Negative E2 outcome preserved, then corrected

Initial [CI45074001214](https://github.com/Kiddos19882/AutoDraw/actions/runs/45074001214) at SHA `0c51cb9` **FAIL** (10/11 synthetic, the invalid swatch-index regression raised `IndexError` before fail-closed validation). Root cause: palette preview indexed `game128[game[opaque]]` before the range check. Minimal [fix 86c5133](https://github.com/Kiddos19882/AutoDraw/commit/86c5133c9c2cb2603cfaf1bdab872705a3b7de88) moved the swatch-range check before indexing; no CTR1 geometry, thresholds, palette, native code or output repair changed. Second pinned CI45074109363 **PASS** with all 11 synthetic + four original x2; first failure not reclassified.

## Deliberate remaining BLOCKED status

The manifest sets `admissible_for_gameplay=false`, `next_stage_S5=BLOCKED`, `source_owner_status=MISSING`, `native_calibration=UNVERIFIED`, `native_Egret=NOT_RUN`, `formal_BPREDS4=BLOCKED`, `semantic_critical_detail_status=UNVERIFIED`, `stroke_admission=FORBIDDEN_UNKNOWN_SOURCE_AND_NATIVE`. **S4.6 source packet interface is technically reproducible, not accepted as a source map**. The [S4.5 visual review](ENGINE001_BPRED001_S4R1_S45_CTR1_CROSS_ORIGINAL_SOURCE_VISUAL_E1_2026-11-23.md) remains PARTIAL with genuinely unrepresented wV/EZAL eye/hair/cloth source boundaries. Provisional DG1 wV RGB error **131.668% > 125% FAIL**, strong-edge wV 77.450%/EZAL75.474% and paintable gates unchanged. Historic scientific115 threshold and all E0 negatives preserved. No native true brush E3, live E4, independent E5, exact run-bound CHALK, color fix, master, Stage6, Bridge, Monitor or production changes.

**Next ONE step per existing S4.5→S4.6→S5 conditional plan:** decision on unresolved S4 source map color/detail/true owner eligibility before S5; if unacceptable, preserve BLOCKED instead of silently feeding this diagnostic schema to an executor. No fresh palette coefficient tuning or extra tests without a distinct justified original-first E0.

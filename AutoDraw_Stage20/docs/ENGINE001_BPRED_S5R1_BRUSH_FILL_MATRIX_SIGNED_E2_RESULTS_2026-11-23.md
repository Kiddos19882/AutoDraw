# ENGINE-001 BPRED-S5-R1 — signed E2 ideal brush matrix and fill comparator (2026-11-23)

**Исходное E0 ДО кода:** [S5-R1 960-case frozen protocol](ENGINE001_BPRED_S5R1_BRUSH_FILL_VALIDATION_MATRIX_PREREG_2026-11-23.md), Git blob `8e46437b19532dc2814d9988567686d29c69a2c6`. **Код/CI exact SHA** `32eec0fbe5162be46702fc43879ddb146588e859`, [GitHub Actions run45080309454](https://github.com/Kiddos19882/AutoDraw/actions/runs/45080309454) / job137386749280 **COMPLETED SUCCESS**. **E2 TECH PASS** — original region/quality and native pixels **NOT** thereby passed. `smooth=false` / `drawing_mode=normal` (DEC-052). S4 user-accepted for S5 (DEC-051), not changed.

## Primary reproducible evidence

[GitHub artifact14776628886](https://github.com/Kiddos19882/AutoDraw/actions/runs/45080309454/artifacts/14776628886), name `engine001-s5r1-brush-fill-matrix-model-only`, archive size6006 bytes, ZIP SHA256 `5d9cf8a1e3f3bbb06997c04083648ade05eddfcf3f30948d2d2837a3454b7048` independently downloaded and checked (zip.testzip=None). Two entries with matched CRC, local SHA256:
- `matrix_cases.json`, size117948, SHA256 `fcbae62539b5da18487012907036030defabbccfcce2059f39c29d3df56ab0f2` — also verified independently by CI against the report, exactly960 cases.
- `brush_fill_model_report.json`, size4413, SHA256 `7375bd306da13277b3a43971dfbcf1f762cf6e05d7454a9c4c1aa16ce4224056`.

Actual CI job steps PASS: frozen E0 Git blob, Python compile, Markdown checker, existing geometry/fill regression **55 passed** in0.32s, new S5-R1 9 synthetic regressions, 960-case matrix / four artificial shapes and speed report, independent output SHA, upload. Markdown audit: 359 total/359 indexed, duplicate_decisions0, current_broken_links0, historical_link_warnings1 **unchanged archival warning**, status **PASS**. Earlier distinct CI negative runs remain retained: [45075611249](https://github.com/Kiddos19882/AutoDraw/actions/runs/45075611249) and [45079897646](https://github.com/Kiddos19882/AutoDraw/actions/runs/45079897646) FAIL from wrong test expectation for tiny image versus modeled residual; [45079887120](https://github.com/Kiddos19882/AutoDraw/actions/runs/45079887120) FAIL unindexed S5-R0 prereg; [45080233560](https://github.com/Kiddos19882/AutoDraw/actions/runs/45080233560) FAIL inherited old test at prior SHA. Fixes: current code reports PARTIAL on actual residual; test checks measured residual instead of assuming fixed stroke cap is necessarily insufficient; README indexes missing E0 file. Frozen E0 numerical thresholds unchanged.

## Real measurements

- Ideal mathematically round capsule geometry: **960/960 PASS, 0 model invariant failures**, widths1–10 ×24 angles(0..345 by15°) × lengths(0,13) × source-local fractional phases(0,.25). `guaranteed ⊆ potential`, reversal, independently evaluated segment-distance pixel centers. This is an **E2 model check, not native Egret pixel exactness**.
- All synthetic shapes use **max_seed_trials700** and max_strokes120 S5-R1; prior horizontal `interior_fill_planner` uses independent rectangle mask and fallback1. Independent output:

| Scene | Eligible source pixels | Existing horizontal rectangle modeled covered | S5-R1 potential covered | S5-R1 guaranteed covered | S5-R1 strokes | S5-R1 status |
|---|---:|---:|---:|---:|---:|---|
| square |144|144|107 (74.31%)|77|4|PARTIAL|
| donut_alpha |84|84|28 (33.33%)|0|4|PARTIAL|
| checkerboard |144|144|4 (2.78%)|0|4|PARTIAL|
| diagonal_1px |12|12|4 (33.33%)|0|4|PARTIAL|

Both modeled coverage reports are **non-native and apples-to-apples only within their respective geometry definitions**, not comparable renderer-equivalent ink. The horizontal comparator's 100% assumed rectangle coverage is not true Egret coverage. S5-R1's low counts are heavily affected by artificial proposal caps and seed allocation, so they prove **limited candidate strategy**, not an impossibility theorem for adaptive brushes.
- Timing only for `swept_capsule_pixel_masks` one width10 diagonal, Linux hosted Python3.11 no special tuning: 64² ~0.028s, 256² ~0.436–0.440s, 512² ~1.729–1.783s (3 measurements each). This is a meaningful computational cost signal, not real-game renderer wall-time or global S5 benchmark. Need microbenchmark tiled/region-aware candidate generation before full EZAL.

## Interpretation / required next

**E2 technical success; S5-R1 full-coverage suitability PARTIAL.** Existing ideal capsule is reusable but expensive for numerous large candidate loops. Source detail `protected_original_dot` remains unscored in S5-R1; source provenance/owner MISSING, native calibration UNVERIFIED and native Egret replay not run for S5. Reuse prior archived real Egret P4D3/P4D4/S2v4 evidence only at exact corresponding SHA; do not represent this matrix as new E3.

**Next exact plan step:** obtain separately running [four fresh originals×2 S5-R1 job45080283784](https://github.com/Kiddos19882/AutoDraw/actions/runs/45080283784) and its raw artifact/metrics with pinned SHA`b9595ed80ec7fc49c2648ca9cbfe645eb5a6d5b4`; then freeze one E0 region-driven candidate architecture **S5-R2** and independent performance/geometry+native-risk gates. If job remains pending, status UNKNOWN, not PASS. No code or game default change in this results document.

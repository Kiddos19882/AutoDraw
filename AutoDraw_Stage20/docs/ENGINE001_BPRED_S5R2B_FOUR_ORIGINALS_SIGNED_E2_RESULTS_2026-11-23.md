# ENGINE-001 / BPRED S5-R2b — signed E2, preregistered model feasibility PASS, full coverage PARTIAL (2026-11-23)

**Frozen prospective E0 BEFORE R2b implementation:** [two-ledger broad-fill/protected-detail E0](ENGINE001_BPRED_S5R2B_TWO_LEDGER_COVERAGE_AND_DETAIL_PREREG_2026-11-23.md), Git blob `f0b0fb42a1822499ae9e008daa50c1f7a40c6864`; unchanged threshold. **Code/job pin:** `b78ec25878ff1d7cfdcb590a3c8dac393f34991e`, [CI45082642153](https://github.com/Kiddos19882/AutoDraw/actions/runs/45082642153), required job137394029965 COMPLETED SUCCESS. Synthetic prior [CI45082521413](https://github.com/Kiddos19882/AutoDraw/actions/runs/45082521413) SHA `f0afb3fbbe3127bfe5157c72290b3c28506ad0d6`: eight new synthetic E2 PASS, E0 integrity PASS, Markdown 364 indexed/364 PASS.

**Result level:** `E2 TECH PASS`, **frozen E0 model feasibility `PASS_MODEL_FEASIBILITY_ONLY`**, **full image coverage `PARTIAL`**; Egret native S5 NOT_RUN, actual gameplay E4/E5 and run-bound CHALK NOT_RUN; source owner `MISSING`, native pixel mapping `UNVERIFIED`. DEC-051 S4 user-accepted for S5 and DEC-052 `smooth=false` normal-only. Never call model touched/guaranteed cells actual Egret pixel coverage.

## Primary archive checked independently

[GitHub artifact14778425069](https://github.com/Kiddos19882/AutoDraw/actions/runs/45082642153/artifacts/14778425069), `engine001-s5r2b-originals-model-only`, GitHub archive digest/independently downloaded ZIP SHA256 `efe8240145df67b15d9736c5855e70c234ad12f1e80df6b008bedc43c792f217`. Nine member files, `ZipFile.testzip()==None` (9/9 CRC). Four model output byte SHA match signed `00_S5R2B_RESULTS.json` 4/4; and original4 ×2 canonical content SHA comparisons from workflow PASS. Four S5-R1 baseline outputs also have output SHA in summary and were independently rechecked against same archive by CI. All4 input original SHA, full source rebuild manifest SHA, game engine blob SHA `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`, read-only S4.6 verify and game128 extraction passed. Original-only source pixels, not previously painted R1/R2 data as input.

## Four original results, fixed 2000 footprint evaluations and 200 stroke caps

| Image | Visible original px | R1 modeled potential covered | R2b modeled potential covered | Improvement | R2b full-cell guaranteed modeled | R2b protected touched / original protected | R2b accepted wide/detail | R2b mode |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| wV 200×320 |64000|1575|2826|+79.4%|1819|120/604|17/120|PARTIAL|
| Hello Kitty 311×360 |72112|65|3005|×46.23|1953|120/480|17/120|PARTIAL|
| EZAL 1235×1920 |2371200|1637|3705|×2.26|2505|120/1243|15/120|PARTIAL|
| Pink Kitty 554×554 |306916|1637|3372|×2.06|2216|120/1681|17/120|PARTIAL|

Frozen detail gate was **at least** [119,118,118,118] touched protected pixels from R2 and every R2b source touched120; 4/4 PASS. Frozen R1 coverage gate `>=` for all4, strictly higher in ≥2: 4/4 strictly higher PASS. Source same-region/swatch/alpha overlap checks: zero accepted forbidden pixels; all details remain original-only and normal/no smoothing; false-gameplay admission forbidden. Determinism fresh four-original x2: 4/4 PASS. For absolute source quality all4 remain **PARTIAL** (wV residual61174, Hello69107, EZAL2367495, Pink303544): E0 feasibility pass does **not** imply drawing readiness.

## Detailed diagnosis from raw JSON, not guesswork

All four capped broad stage at **1400** actual ideal capsule geometry evaluations, but accepted only **17,17,15,17** wide strokes. Detailed stage accepted **120** width1 strokes each (120 further geometry evaluations). Output used **1520/2000 possible** geometric evaluations total; the spare480 is an explicit phase reservation and not evidence of completed coverage. Rejections per source:
- wV: model foreign/alpha208, centerline preflight215, no_gain0.
- Hello: foreign232, preflight163, no_gain0.
- EZAL: foreign0, preflight0, no_gain0.
- Pink: foreign64, preflight99, no_gain0.

Width histogram from archived proposals independently checked: wV wide (10×13,7×3,6×1), Hello (10×10,8×5,7×1,9×1), EZAL (10×15), Pink (10×13,2×2,4×1,3×1); each also 120 detail brush1. So R2 failure (all width1) is resolved, but **broad-candidate budget efficiency is still poor**: many repeated candidate variations on small set of broad seed regions, and each big region receives too few distinct long coverage paths. Need look beyond pixel-to-pixel greedy or another threshold adjustment.

End-to-end source decoding + CTR1 + fresh S4.6 + baseline R1 + R2b per repetition (same CI platform) wV2.61s, Hello2.93s, EZAL29.1-29.4s, Pink8.0s. Not live FPS or native painter runtime. Native P4D3/P4D4 positional non-equivalence and S2v4 false-safe (3 physical alpha FP) remain; don't declare the ideal capsule Egret pixel-perfect.

## Decision / only next step

**Accept S5-R2b as MODEL-FEASIBLE research component, not as full-image fill or production.** Preserve signed R1/R2 FAIL and this R2b PASS without changing any original gate. **Next S5-R3 needs a new E0 before code:** true region interior path construction using clearance/eroded medial corridors, orientation/long-run tracing, and directly generate a *small number of long, valid* candidate centerlines rather than 1400 short near-duplicate proposals. Retain one existing capsule verifier, broad/detail ledger and 4DEV original×2 protocol, normal-only `smooth=false`, no old artwork. Pre-register absolute source coverage and protected-detail safety gates, not merely relative gains. Native-only source-to-Egret transform and color-over checks stay gated by valid source owner and calibration, exact CHALK game-only.

**Files/code/production:** changed only experimental `tests/engine001_bpred_s5r2b_two_ledger_candidates.py`, `tests/test_engine001_bpred_s5r2b_two_ledger_candidates.py`, `tests/run_engine001_bpred_s5r2b_dev.py`, two isolated workflows, and necessary docs. No changes to `source/preparation/` existing footprint oracle, S4, Stage6, Bridge, Monitor, or `master`.

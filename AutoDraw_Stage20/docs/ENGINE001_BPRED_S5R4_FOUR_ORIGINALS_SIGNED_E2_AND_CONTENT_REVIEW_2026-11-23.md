# ENGINE-001 / S5-R4 — signed original4×2 E2, coverage PASS with content-detail caveat (2026-11-23)

**E0 prereg:** [region-offset-lane plan](ENGINE001_BPRED_S5R4_REGION_OFFSET_LANES_PREREG_2026-11-23.md), authored **before** S5-R4 source code/CI. **Branch:** `feature/image-geometry-optimization`. **Code and run SHA** [`b7e108f3199b880e36274a94a21b0ac2c5637b73`](https://github.com/Kiddos19882/AutoDraw/commit/b7e108f3199b880e36274a94a21b0ac2c5637b73); exact [CI45090117499](https://github.com/Kiddos19882/AutoDraw/actions/runs/45090117499) job137417536437 **COMPLETED SUCCESS**, all required steps. Prior [synthetic CI45090038737](https://github.com/Kiddos19882/AutoDraw/actions/runs/45090038737) SHA0d4c451 6/6 PASS and docs PASS. First [synthetic CI45089934227](https://github.com/Kiddos19882/AutoDraw/actions/runs/45089934227) tests6/6 PASS but markdown audit FAIL due three new not-indexed S5 reports, minimal README fix then rerun; preserve negative.

## Primary evidence

[Source-only artifact14781341222](https://github.com/Kiddos19882/AutoDraw/actions/runs/45090117499/artifacts/14781341222) 10 files, ZIP SHA256 (GitHub digest **and independently downloaded exact SHA**) `287efca5885c1bb9f6deccfd1fe55eb57f3be018cd4875219bb86cd5c9041f62`; CRC10/10 PASS, 8/8 individual R3/R4 source JSON sha256 match report, wV algorithm-produced model preview PNG sha match and model potential count equals new R4 union. All four originals fully rebuilt twice from true original→game128→CTR1→verified S4.6→same-input R3 vs R4; byte-identical double-fresh results 4/4. Engine git blob pinned `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`; original input SHA present in results. No inherited prepared image used as a new algorithm input. Research-only ideal swept capsule: not native S5 Egret or E4 gameplay.

**Model coverage E0 feasibility:** exactly frozen same caps ≤1400 broad ideal-footprint evaluations/80 strokes, ≤600 detail evaluations/120 strokes; total ≤2000/200, true per-region/alpha/game index hard checks via pre-existing oracle. Prior signed R3 counts 9248/9062/53300/15368 and protected120 each verified. Frozen E0 new R4 >=R3 on all4 with strict improvement on ≥2: **PASS 4/4 strict**. Protected potential dots touched120 each. This is only model relative feasibility, **NOT** full image quality.

| Source | Opaque pixels | R3 potential | R4 potential | R4 share original | R4 broad/detail | R4 footprint evals | R4 residual | Protected potential touched |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| wV 200×320 |64000|9248|17823|27.848%|80/120|1091|46177|120|
| Hello Kitty 311×360 |72112|9062|23756|32.943%|80/120|886|48356|120|
| EZAL 1235×1920 |2371200|53300|120466|5.080%|80/120|1520|2250734|120|
| Pink Kitty 554×554 |306916|15368|74318|24.214%|80/120|728|232598|120|

Actual multiple accepted broad lanes/region: 11,16,14,11 respectively. Synthetic E2 tests rectangle, vertical, donut alpha hole, same-swatch different owners, narrow protected, invalid budgets. Full preview from **algorithm's actual source and selected footprint results**, not AI-generated and not true painted Egret. Source original/ideal painted colors/real selected model paths/coverage vs residual shown, confirming most important character/contour components still missing.

## New post-result CONTENT diagnostic (do NOT revise frozen E0)

For each accepted S5-R3 and R4 stroke, summed already recorded `modeled_new_potential_cells` by **game palette index6 WHITE**, vs all other game indices. The sum matches frozen respective total potential count. This is a descriptive **model-only** diagnostic, not exact original-RGB foreground/semantic importance and not a retroactive acceptance gate.

| Source | R3 WHITE6 | R3 non-WHITE6 | R4 WHITE6 | R4 non-WHITE6 | Non-WHITE6 change |
|---|---:|---:|---:|---:|---:|
| wV |7434|1814|16282|1541|**−273** |
| Hello |4040|5022|17134|6622|+1600|
| EZAL |4346|48954|9689|110777|+61823|
| Pink |10675|4693|61860|12458|+7765|

R4 wV non-WHITE6 **regressed 273 modeled covered cells** while total modeled count rose 8575. On wV only 1541/17823 (8.65%) of new-model covered pixels are non-WHITE6. The model preview reveals large red unpainted interior components, while whitespace areas are increasingly covered; source contour/face/hair/body detail do NOT pass full visual quality. Protected source dot touch120 is a *count* only, not proof important contour, eye or silhouette integrity. Do not promote to native/production based on this relative model PASS or treat white-background gain as meaningful visual quality improvement. Similar white-dominated gains for Hello and Pink, though their non-WHITE6 counts improved.

**Architectural cause indicated by E1+E2 (hypothesis, not proven causal):** global broad candidate sorting by footprint size rewards high-area white background regions and consumes the frozen80 broad slots while nonwhite source objects remain unfilled. Simply adding more footprint trials/strokes, or local micro-retouch of the output image, would evade intended aim. Next prospective source-only stage should introduce **content-aware stratified allocation and source-specific important-region/detail priority**, preserving strict owner, contour/alpha constraints, instead of blindly optimizing total area. No original E0 threshold relaxation.

## Evidence and next action

- Pinned source4×2 artifact SHA and JSON/PNG structural checks: **PASS E2**.
- Frozen total modeled coverage feasibility: **PASS 4/4**; protected dot potential count: **PASS 4/4** (count only).
- Genuine full-color/detail quality: **PARTIAL**, wV non-WHITE6 model regression `−273` observed.
- S5 native Egret full scene, source owner/game calibration: **NOT_RUN / BLOCKED**; E4 runtime, E5 independent live, exact run-bound `post.pointCount-pre.pointCount`: **NOT_RUN**.
- No change to production, Stage6, Bridge, Monitor, CHALK estimator or default smooth. S5 experimental algorithm remains `safe_to_execute=false` and `admissible_for_gameplay=false`.

**Single next step:** freeze new source-only E0 for content-region-aware broad stroke distribution (not postprocessed picture fixing), predefine independent **non-WHITE6** and source-critical-detail metrics on each original as additional gates while retaining strict total coverage, protected, same budget and original source; then compare with R4. Requires architecture-level candidate policy, not acceptance manipulation.

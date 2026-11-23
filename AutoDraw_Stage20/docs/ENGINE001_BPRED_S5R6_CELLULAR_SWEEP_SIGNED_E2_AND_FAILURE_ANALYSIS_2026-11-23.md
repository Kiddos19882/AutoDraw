# ENGINE-001 / S5-R6 — genuine sweep-cell graph E2 signed; scientific content FAIL (2026-11-23)

**Scientific verdict: `FAIL_CELLULAR_CONTENT_FEASIBILITY`.** Branch `feature/image-geometry-optimization`. [Frozen before code E0](ENGINE001_BPRED_S5R6_CELLULAR_SWEEP_COVERAGE_PREREG_2026-11-23.md) / [DEC-053](DECISIONS.md). Code is **research-only**, normal `smooth=false`, `safe_to_execute=false`, `admissible_for_gameplay=false`; source owner MISSING, calibration UNVERIFIED, E4/CHALK NOT_RUN.

## Real tests and signed raw provenance

- [Synthetic topology CI45118829845](https://github.com/Kiddos19882/AutoDraw/actions/runs/45118829845), exact SHA `4c38a4f55f7c6a98f890df8d20674b95f98cc673`, required job **SUCCESS**: **16/16 tests PASS** (6 R4, 4 R5, 6 new R6) including donut split→merge, branched neck, transparency, same-swatch differing owner, deterministic topology, reconstructed full owner-mask partition and model paint owner guards; Markdown audit PASS. Test source deliberately exercises owner and hard budgets.
- First original4×2 [CI45119003303](https://github.com/Kiddos19882/AutoDraw/actions/runs/45119003303), source SHA `2a48ecc540e338bc74ca1a0d9783d129facb90fb` and archived artifact `14792688500` ZIP SHA256 `d045bb98f9ad5bc406e72b4f1a6e86ba988692cb409d5d09eac609539eff2fd4`: model outputs and PNG pass but only **60 event/edge examples** archived, so **full reproducible graph retained = incomplete**. Preserve as preliminary technical PASS with raw-evidence gap; no geometry change.
- Minimal **evidence-only correction**: export each entire row-sweep source-owner DAG + all intervals + split/merge/disappearance events in deterministic gzip, and require SHA256/area/edge/DAG verification in CI. No change to geometric candidate generator, thresholds or original source. Corrected [CI45119531408](https://github.com/Kiddos19882/AutoDraw/actions/runs/45119531408), exact SHA **`d9628bc0a0a17b87adbd5bf5f3a7400c6f35b7fe`**, job `137509891884` **COMPLETED SUCCESS** all required steps including full DAG/PNG/original×2 comparison. [GitHub artifact14793191824](https://github.com/Kiddos19882/AutoDraw/actions/runs/45119531408/artifacts/14793191824), **ZIP SHA256 `49df074027721f21592949f22227c30d44f4108046186e1afe670e0039356415`** exactly matches GitHub digest and independently downloaded ZIP, ZIP CRC **22/22 PASS**. All **16/16 R3/R4/R5/R6 model JSON SHA256**, 4/4 compressed full graph SHA256 and uncompressed graph SHA256, wV algorithm model PNG SHA256 `e6bd248f7456385492fb16af5c3f9436c44c2e5fba4bea69dd318dea86dba03c` verified. Full original→game128→CTR1→strict S4.6→R3/R4/R5/R6 computed **twice** independently for each original and byte-identical4/4; engine blob pinned `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`.
- Independent downloaded-graph checks additional to CI: all source rows' cell spans **pairwise non-overlapping**, sum of interval areas equals each original's opaque source area and all per-owner internal counts; 4/4 DAG edges unique and each corresponds to an archived event source parent, with `parent cell ID < child cell ID`; full graph topology, run and event counts reproduce signed model ledger. This is evidence for row-sweep partition **of archived original source owner arrays**, not true game object ownership or native pixels.

## Frozen content and total-coverage gates — failed, no retroactive changes

| Original | Frozen >= max(R4,R5) nonWHITE6 | R6 nonWHITE6 | Relative delta | R6 model total | Frozen R3 total minimum | Protected potential |
|---|---:|---:|---:|---:|---:|---:|
| wV 200×320 |2726|2767|+1.50%|2768|9248 **FAIL**|120|
| Hello Kitty 311×360 |7501|7196|−4.07% **FAIL**|7196|9062 **FAIL**|120|
| EZAL 1235×1920 |110777|157164|+41.88%|157164|53300 PASS|120|
| Pink Kitty 554×554 |14877|13921|−6.43% **FAIL**|13921|15368 **FAIL**|120|

Frozen all4 nonWHITE≥max(R4,R5) **FAIL2/4**; strict ≥10% gain on ≥2 originals **FAIL (only EZAL)**; total coverage≥frozen R3 **FAIL3/4**; protected dot120 each **PASS4/4**; owner/alpha safety within existing ideal swept capsule model **PASS**, per-phase caps broad80/1400 and detail120/600 respected; full 4×2 deterministic PASS. **Technical CI PASS is not scientific feasibility PASS; keep the negative in archived result.**

## Actual topology size and why it is not enough

| Original | Source-owner cells | Row-runs | Split | Merge/complex | Source-owner opaque pixels | Cells with accepted broad lanes |
|---|---:|---:|---:|---:|---:|---:|
| wV |4,797|12,900|383|196|64,000|34|
| Hello |2,759|6,698|148|72|72,112|28|
| EZAL |33,285|122,984|3,621|1,798|2,371,200|20|
| Pink |3,291|8,524|103|55|306,916|27|

These are REAL **row-sweep** cell-graph event counts, not mere shifted-line nicknames. They demonstrate genuine topology extraction, but not finished full Boustrophedon path-planning fidelity in arbitrary directions: **only horizontal 0° sweep paths are actually generated**, 90° cost-based orientation selection in original E0 is **NOT IMPLEMENTED**. Source-to-game geometry is uncalibrated; source-space 1-pixel pitch is not native game-width proof.

All four outputs have 80 broad +120 detail accepted model strokes, while broad model footprint calls are only wV82, Hello85, EZAL90, Pink94 (not approaching1400 allowed). Therefore the **80 accepted broad stroke cap**, not footprint-evaluation compute budget, is quickly exhausted. On EZAL **80/80 broad strokes belong to game swatch index47** (not proof of one source owner); other source component colors are starved. Multi-cell extraction did not resolve allocation/tile coverage. Wv ideal-footprint model preview is still heavily fragmented, with 2,768/64,000 potential coverage: visual quality **PARTIAL/FAIL for recognizability**, cannot promote. Future work should use cell-level marginal useful coverage, source-owner diversity, and connected in-cell coverage paths rather than retuning quotas, increasing caps, or patching finished PNG.

## Which network research methods ACTUALLY entered this test

| Method and published reference | S5-R6 evidence | Limitation |
|---|---|---|
| [Choset/Pignon Boustrophedon Cellular Decomposition (CMU)](https://publications.ri.cmu.edu/coverage-path-planning-the-boustrophedon-cellular-decomposition) | **APPLIED (partial planner)** explicit full owner-preserving horizontal row-sweep cells, split/merge DAG and independent full interval topology tests E2 | Only one sweep orientation; no full 2-axis orientation choice, no continuous in-cell snake trajectory |
| [Euclidean Distance Transform (OpenCV)](https://docs.opencv.org/4.x/d2/dbd/tutorial_distance_transform.html) | **APPLIED** `scipy.ndimage.distance_transform_edt` distance from owner/alpha walls guides width2–10 centerlines | Native Egret capsule is not represented by EDT |
| Parallel sweep coverage | **APPLIED (limited)** multi-row lanes inside each cell; widths from frozen game1..10, model verification | ≤4 selected width passes per cell and only80 broad globally; low absolute coverage |
| Greedy geometric set cover | **PARTIAL** reject zero new model cells and prioritize cell area; not global optimized marginal coverage | Owner diversity / fresh residual utility not fully considered |
| [Medial Axis](https://scikit-image.org/docs/stable/api/skimage.morphology.html) | **NOT IMPLEMENTED** | May later aid narrow pockets, not a solution for slot allocation by itself |
| Contour-parallel CNC, spiral toolpaths | **NOT IMPLEMENTED** | No arbitrary path or native Egret curve/turn test |

## One next non-microfix architecture task (E0 NOT YET EXECUTED)

Preserve existing source-only topology, but **separate geometric cell decomposition from actual bounded stroke scheduling**: dynamic cell-level marginal utility after each accepted footprint, diversify scarce80 broad slots by owner/region-content and coverage deficit, consider dense continuous in-cell zigzags (polyline) as a separately preregistered alternative only after native Egret curve/turn evidence; compare horizontal vs vertical cells in fixed prospective E0 instead of silently switching orientation. Keep same2000/200, source4×2, protected120, strict alpha/foreign boundaries. Must FIRST preregister new experiment with meaningful prior improvement gates; do not retroactively make S5-R6 PASS or tune a particular image. E3 native **full S5** NOT_RUN, E4/E5 gameplay NOT_RUN, exact `CHALK=post.pointCount-pre.pointCount` NOT_RUN; Stage6/production/Bridge/Monitor/master untouched.

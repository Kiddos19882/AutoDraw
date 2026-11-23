# ENGINE-001 / BPRED-S5-R7 — prospective E0: fair cell-level marginal coverage (2026-11-23)

**PROSPECTIVE, FROZEN BEFORE S5-R7 CODE OR TESTS.** Based on [signed S5-R6 row-sweep topology E2 and scientific FAIL](ENGINE001_BPRED_S5R6_CELLULAR_SWEEP_SIGNED_E2_AND_FAILURE_ANALYSIS_2026-11-23.md), [signed S5-R4 E2](ENGINE001_BPRED_S5R4_FOUR_ORIGINALS_SIGNED_E2_AND_CONTENT_REVIEW_2026-11-23.md) and [S5-R5 negative](ENGINE001_BPRED_S5R5_CONTENT_LANES_FOUR_ORIGINALS_SIGNED_E2_2026-11-23.md). Branch `feature/image-geometry-optimization`. Never use an old painted PNG as source input. No approval for gameplay from research E0.

## Why this step and which network methods it combines

S5-R6's **full Boustrophedon row-sweep split/merge graph** is genuine and has verified 4/4 owner-preserving area; the selection still spends all80 wide slots after only82–94 ideal-footprint evaluations, concentrating EZAL all80 swatch47 while covering just20 of 33,285 cells. The slot allocator, not an inaccurate brush diameter, is now the first reproducible blocker. Stop trivial width/color quota/offset patching.

Prospective single research-only architecture:
1. Reuse existing E2 original→game128→CTR1→S4.6 owner/edge/protected packet, existing tested `decompose` graph and `swept_capsule_pixel_masks` (no parallel planner). Build **two prospective sweep orientations** (rows 0° and columns 90°) using same complete split/merge/appear/disappear graph logic; graph and event integrity checked independently on donut/branch/alpha and distinct same-swatch owners. Choose orientation per source cell by one predeclared geometric cost (e.g. fraction of clearance-viable lanes, travel length and turns) **before** footprint selection, not by outcome on one image.
2. Compute EDT for clearance; generate source-owner-safe long parallel candidate lanes within each cell. **Differentiate geometric cell and game swatch**. Existing native Egret lineStyle size1..10 / alpha24/128 P4D3 and S5-LANE-P1 straight 0/90 native seam are evidence for *future game-space calibration*, not proof that original pixel-width equals game pixel-width.
3. Choose among source-cell candidates by **incremental new original-source coverage** recomputed on a common residual mask after every accepted broad stroke, with diversity/deficit terms to avoid spending 80 broad slots in one source color or one large cell. Rank area, content, `source_edge` proxy, protected-dot proximity, interior white detail, source-region owner separately; do **not** globally forbid white or optimize only palette index6 vs all others. The precise scoring weights/ranking must be included in implementation and tested on adversarial scenes; none is declared optimal by this E0.
4. Carry only **two-point straight strokes** through this comparison. Continuous multi-point zigzag turns would need a separate fixed native Egret corners/source-over experiment; do NOT silently introduce polyline curves/turns, pretend smoothing is on, or infer CHALK from stroke length.
5. For every proposed candidate reject any model foreign owner/game swatch/alpha cell. Preserve normal `smooth=false`, `safe_to_execute=false`, `admissible_for_gameplay=false`, `native_calibration=UNVERIFIED`. No changes to production, S4 maps, Stage6/Bridge/Monitor/CHALK estimator.

## Frozen budgets and science gate

- EXACTLY the same broad≤**1400 ideal footprint calls /80 accepted widths2..10**, detail≤**600 calls /120 width1**, aggregate≤**2000 /200** as R3–R6; avoid post-result expansion.
- Source4×2 fresh from original bytes; same engine blob `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`, S4.6 quarantined packet; compare signed R3/R4/R5/R6 from fresh inputs, no old result as algorithm input, independently check full source-owner masks for all proposals and record PNG/model and graph SHA.
- NonWHITE6 potential coverage **≥ signed max(R4,R5)** on EACH original: wV≥2726, Hello≥7501, EZAL≥110777, Pink≥14877; **≥10% strict relative improvement vs that max on ≥2 of four**. These represent a **model feasibility minimum**, not actual perceptual quality. No reduced values after seeing results.
- Total model potential coverage **≥signed R3** on EACH original (wV9248, Hello9062, EZAL53300, Pink15368); protected source original dots touched≥120 on each. Any fail = `FAIL_CELL_FAIR_COVERAGE_FEASIBILITY`, preserve raw negative and SHA.
- Report per-owner and per-game-color broad stroke counts, cell deficit/covered area, white/nonwhite/edge/protected original mask coverage, full original source residual, number and lengths of broad strokes, actual evaluated model candidates and CPU time for EZAL. Synthetic must prove that a second eligible region/color can receive coverage when a first larger region has already gained substantial coverage; it must NOT pass by forcing region quotas unrelated to residual geometry. Topology must reconstruct source pixels exactly, graph edges deterministic and meaningful, including in transposed view.
- S4 user-accepted visual status remains DEC-051; source-mapped face/eye/hair detail and recognizable full wV/Hello etc remain **separate visual quality PARTIAL/UNKNOWN**, no automatic production acceptance even if model feasibility passes. Native full-scene S5 painting / E4 / E5 / exact `post.pointCount-pre.pointCount` remain NOT_RUN/BLOCKED.

## Audit of methods found on the web

| Method | Status entering S5-R7 | Intended use |
|---|---|---|
| Boustrophedon Cellular Decomposition — [CMU](https://publications.ri.cmu.edu/coverage-path-planning-the-boustrophedon-cellular-decomposition) | **ALREADY PARTIAL E2 row-sweep topology**, dual orientation **NOT_RUN** | Owner-preserving split/merge cells and alternate 0°/90° |
| Euclidean Distance Transform — [OpenCV](https://docs.opencv.org/4.x/d2/dbd/tutorial_distance_transform.html) | **ALREADY APPLIED E2**, retained | Conservative preflight widths and boundary clearance |
| Greedy geometric set cover / residual coverage | **PARTIAL**, full cell-level dynamic marginal scheduling **NOT_RUN** | Efficient broad80 stroke allocation and negative-residual utility |
| Medial-axis skeleton — [scikit-image](https://scikit-image.org/docs/stable/api/skimage.morphology.html) | **NOT IMPLEMENTED** | Only if unresolved narrow branch cases after bounded cells |
| Contour-parallel and Spiral pocket CNC toolpaths | **NOT IMPLEMENTED** | Only future separate E0 if cellular sweeps fail on irregular regions |

**First next permitted step:** implement only S5-R7 dual-orientation cell candidate enumeration and a single fair marginal allocator in existing experimental source-only tests, then topology synthetic E2 and genuine original4×2 E2. Do not tune R6 signed failures or game-admit unverified coordinates.

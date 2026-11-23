# ENGINE-001 S5-R8 connected source-cell sweeps · 2026-11-23

**FAIL_CONNECTED_COVERAGE_FEASIBILITY.** The [frozen R8 protocol](ENGINE001_BPRED_S5R8_CONNECTED_CELL_SWEEPS_PREREG_2026-11-23.md) requires the nonwhite minimum on every original. wV missed by 381 source pixels. Three originals met the 10% gain criterion. The full-image native renderer, gameplay, CHALK and independent semantic validation were not run.

## Evidence

Baseline 0319b24, tested implementation 20bfb6aad7b2939fda8ffb63fc4b1ed2641cc15b. [GitHub Actions run 45130775300](https://github.com/Kiddos19882/AutoDraw/actions/runs/45130775300) completed successfully, job 137545512946. [Artifact 14797622459](https://github.com/Kiddos19882/AutoDraw/actions/runs/45130775300/artifacts/14797622459), GitHub-reported ZIP SHA256 316a486fbb963018fa425c2c3d338d8aa71f708f4ec79c065e42e24f5ce29956. The local run used Python 3.12 with the same six pinned packages as the Python 3.11 CI run. All four sets of total, nonwhite, white, edge and protected counts matched the CI log. Both runs checked deterministic manifests, packets, plans and model counts across two fresh builds of each original. Each scene has its plan, PNG with residuals, both full sweep graphs and source manifest.

23 synthetic/regression tests passed. R8 tests check the exact oracle call budget, a blocked turn between two individually valid lanes, connected lanes, different regions of the same swatch, opacity, internal white and a narrow passage. Every accepted footprint was checked against the source region, swatch and opacity. Paths use normal mode with smoothing off.

| Original | Required nonwhite | R8 nonwhite | Total potential | Source edge | Protected | Broad evaluations | Broad vertices |
|---|---:|---:|---:|---:|---:|---:|---:|
| wV | 2726 | 2345 | 18283 | 150 | 120 | 153 | 210 |
| Hello | 7501 | 8262 | 34073 | 199 | 120 | 172 | 276 |
| EZAL | 240845 | 1401493 | 1408605 | 318 | 120 | 1400 | 684 |
| Pink | 14877 | 19742 | 204188 | 258 | 120 | 327 | 528 |

All four accepted 80 broad paths plus 120 detail dots with 120 detail evaluations. The R3 total minimum passed on all four. The R4/R5/R7 nonwhite minima came from the frozen protocol. The original R7 results and the P2 native turn measurements remain separate evidence.

## Visual review and candidate diagnosis

The wV preview leaves both faces and most clothing unpainted. Hello and Pink show fragments of clothing and bows with incomplete outlines. In EZAL the dark background makes the silhouette visible while much of the character remains blank. Swatch 47 accounts for 1,342,572 of the 1,401,493 modeled nonwhite EZAL pixels. These counts include background.

On wV, 62/80 accepted broad paths contained one lane. A separate deterministic inspection of the generator on the fresh wV packet counted 38 single-lane and 5 multi-lane nonwhite proposals before scoring, alongside 64 single-lane and 16 multi-lane white proposals. Only one connector was rejected. The broad oracle used 153 of 1400 evaluations. Thus a shortage of multi-lane nonwhite proposals already exists before allocation. Whether alternate directions or widths fit more of those cells remains open.

Next research step: inspect both existing sweep directions and admissible widths for the single-lane nonwhite wV cells, recording clearance failures, skipped rows and feasible second lanes. Keep the frozen R8 result and thresholds. Production and live execution remain outside this experiment.

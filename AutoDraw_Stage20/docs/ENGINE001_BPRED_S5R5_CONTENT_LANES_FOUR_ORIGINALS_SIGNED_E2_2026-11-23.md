# ENGINE-001 / S5-R5 — source-content lane allocation, signed four-original E2 (2026-11-23)

**Verdict: `FAIL_CONTENT_FEASIBILITY` on frozen prereg E0; scientific negative retained, not rewritten.** Working branch `feature/image-geometry-optimization`. [Original prospective S5-R5 E0](ENGINE001_BPRED_S5R5_CONTENT_STRATIFIED_REGION_LANES_PREREG_2026-11-23.md) frozen before any S5-R5 code, [previous R4 signed E2](ENGINE001_BPRED_S5R4_FOUR_ORIGINALS_SIGNED_E2_AND_CONTENT_REVIEW_2026-11-23.md). Experiment implementation+tests on exact **`e8e64b17e5dacaa7aa1c0092bbfd68add8d0ea3b`**. All input paths are true fresh originals→game128→CTR1→verified quarantined S4.6→R3/R4/R5 on same source, double-built independently; no previous painted image used as new input.

## Verified evidence and provenance

- New [S5-R5 synthetic CI45092117681](https://github.com/Kiddos19882/AutoDraw/actions/runs/45092117681) exact SHA `e8e64b1`: Python 10/10 PASS (6 unchanged R4 +4 content-mode tests), markdown audit PASS, required job success. Earlier [CI45091985686](https://github.com/Kiddos19882/AutoDraw/actions/runs/45091985686) SHA`0c63ccd` **FAIL 9/10**: incorrect assertion demanded positive `source_edge` overpaint although conservative EDT safely leaves edge untouched. New test corrected to check preservation of conservative edge margin, source-edge component priority added without changing threshold; canceled interim CI retained.
- [Full source4×2 CI45092117700](https://github.com/Kiddos19882/AutoDraw/actions/runs/45092117700), SHA`e8e64b1`, job `137423827280` all required steps **SUCCESS**, including independent source SHA/arrays/output verification and archiving. This technical CI PASS does **not** imply frozen scientific gate PASS.
- [GitHub artifact14781334389](https://github.com/Kiddos19882/AutoDraw/actions/runs/45092117700/artifacts/14781334389), raw ZIP GitHub SHA256 and independent download SHA256 identical: **`cf7ab31d289b0db4ed7e8f575e1431dc77458a3cf7842b5eb23964015a95194f`**, ZIP CRC14/14 PASS; all 12 R3/R4/R5 JSON SHA256 match report; wV direct model preview PNG hash `7a6ea2a022614f336332007d0771d0fb7e76dec00a2ffeb26e2a9da407ae2e10` matches report and independently extracted bytes. Result schema `ENGINE001_BPRED_S5R5_FOUR_ORIGINALS_V1`; two fresh runs byte-identical4/4. All historic signed R3/R4 total/non-WHITE6 baselines independently pinned by runner; result candidate model counts equal sum of each accepted stroke's new-cell ledger.
- Source S4.6 `source_owner_status=MISSING`, `native_calibration=UNVERIFIED`, all R5 strokes `drawing_mode=normal`, `smooth=false`, `safe_to_execute=false`, `admissible_for_gameplay=false`; same broad≤1400 trials/80 strokes, detail≤600/120, all4 protected modeled dots120. No game-E4, native full-scene S5 Egret-E3, exact run-bound CHALK or independent semantic E5.

## Measured model-only results (predeclared gate)

| True original | R3 total | R4 total | R5 total | R3 nonWHITE6 | R4 nonWHITE6 | R5 nonWHITE6 | R5 protected | Result |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| wV | 9248 | 17823 | 13858 | 1814 | 1541 | **2726** | 120 | Nonwhite PASS |
| Hello Kitty | 9062 | 23756 | 23135 | 5022 | 6622 | **7501** | 120 | Nonwhite PASS |
| EZAL | 53300 | 120466 | 120016 | 48954 | **110777** | **110028** | 120 | **Nonwhite FAIL −749** |
| Pink Kitty | 15368 | 74318 | 60992 | 4693 | 12458 | **14877** | 120 | Nonwhite PASS |

- 3/4 originals have strictly higher nonWHITE6 coverage vs R4; strict gain on ≥2 **PASS**, frozen minimum total coverage≥R3 **PASS4/4**, protected120 **PASS4/4**, source-owner hard ideal-mask **PASS**.
- Predeclared independent all4 nonWHITE6 ≥ max(R3,R4) **FAIL1/4** (EZAL 110028<110777, difference −749), so aggregate **FAIL_CONTENT_FEASIBILITY** with no post-hoc relaxation. Do not call it an accepted S5-R5 variant.
- Diagnostic source-edge model-covered R4→R5: wV127→145, Hello140→165, EZAL161→161, Pink132→134. Source-edge is **not verified semantic contour** and remains a diagnostic, not acceptance.
- R5 broad/detail strokes80/120 for each; actual footprint evaluations wV1091, Hello886, EZAL1520, Pink728. Multiple accepted region lanes still generated; no additional brush/quota budget. Source-only approximate painting quality remains **PARTIAL**, wV preview shows most character structure unfilled even with nonwhite gain.

## Explicit web-research method use (requested by user)

| Published geometric method / prior source notes | S5-R5 actual use | How validated and caveat |
|---|---|---|
| [Euclidean Distance Transform (OpenCV)](https://docs.opencv.org/4.x/d2/dbd/tutorial_distance_transform.html) | **APPLIED** through R4 clearance preflight `scipy.ndimage.distance_transform_edt` | Restricts proposed centerlines away from owner borders; ideal potential masks independently checked E2; does not prove native pixels safe |
| Coverage sweeps / [Boustrophedon path planning (CMU)](https://publications.ri.cmu.edu/coverage-path-planning-the-boustrophedon-cellular-decomposition) | **PARTIAL**: repeated 0/90 parallel offset lines; **full cellular decomposition NOT IMPLEMENTED** | Measured real Egret straight-pair pitch in separately signed S5-LANE-P1 E3 limited angles/phases; no full region tiling or native scene quality |
| Greedy residual geometric set cover | **PARTIAL**: proposal ranking by ideal valid footprint/new modeled cells and per-region quotas | Same R4 ideal oracle and coverage ledgers; not a proven optimal set-cover or exact CHALK |
| [Medial Axis (scikit-image)](https://scikit-image.org/docs/stable/api/skimage.morphology.html) | **NOT IMPLEMENTED** | Reserved for narrow corridors/curves only after E0, no false claim |
| Contour-parallel CNC pocket paths | **NOT IMPLEMENTED** | Future comparison on curved interiors, not current code |
| Spiral trajectories | **NOT IMPLEMENTED** | Future candidate, not current E2 |

New S5-R5 implementation reuses the same original-only `tests/engine001_bpred_s5r4_offset_lanes.py` with opt-in `allocation=content_s5r5`; **R4 default remains `area`**, independently verified exact original frozen R4 counts and six previous tests. Components are softly grouped: nonwhite6, enclosed white6 (possible eye/clothes detail), border-connected white6 background, with bounded class quotas 60/12/8, remainder returned to all groups. Source `source_edge` contributes region prioritization but does not demand touching edge pixels. This is a planning heuristic, not learned/semantic segmentation.

## Engineering interpretation and one next step

This is **stronger evidence of content allocation usefulness but NOT acceptance**. Three subjects improved nonwhite source paint and all four retained R3 minimum total, but EZAL lost749 nonwhite model cells and the wV visual is still far from recognizable. Narrow weight/quota tweaking to recover just749 would risk the historical endless microfix loop the user explicitly rejected. Do not call the full stage successful and do not alter original gates.

**Next architectural decision:** stop simple white-vs-nonwhite global slot policy as the primary mechanism; instead preregister a **true region cellular decomposition / multi-cell sweep scheduler** using geometric area and boundary structure, protected/detail weighting and separately tracked source-swatch ownership. Consider [Boustrophedon](https://publications.ri.cmu.edu/coverage-path-planning-the-boustrophedon-cellular-decomposition) for splitting irregular connected regions into sweep cells, EDT for clearance, and a bounded residual-coverage selection objective; consider medial-axis only where narrow. Preserve S5-R3/R4/R5 signed evidence, normal smoothing off and original budgets. No further S5-R5 unregistered tuning.

# ENGINE-001 / BPRED-S5-R6 — prospective E0: true sweep-cell decomposition and coverage (2026-11-23)

**PROSPECTIVE FROZEN E0 before S5-R6 code or tests.** Decision [DEC-053](DECISIONS.md) after [S5-R5 scientific negative 4×2](ENGINE001_BPRED_S5R5_CONTENT_LANES_FOUR_ORIGINALS_SIGNED_E2_2026-11-23.md) SHA e8e64b1, [S5-R4 baseline](ENGINE001_BPRED_S5R4_FOUR_ORIGINALS_SIGNED_E2_AND_CONTENT_REVIEW_2026-11-23.md) SHAb7e108f. Experimental branch feature/image-geometry-optimization. S4 accepted for research DEC-051, smoothing off DEC-052. S4.6 original owner remains UNVERIFIED/MISSING, no game/CHALK claim.

## Hypothesis and actual published methods to implement

Instead of globally ranking lines on large white regions (R4) or reserving arbitrarily fixed class quotas (R5), split every source-owner connected component into **Boustrophedon cells** by scanning one axis and emitting a cell boundary on interval split/merge or appearance/disappearance events. Give each cell independently scored straight parallel fill lanes (0°/90° from sweep cost estimate) at a candidate pitch based on game-native S5-LANE-P1 measurements (native E3 supports ≤1× nominal width on tested conditions ONLY). Each lane clipped to actual source mask corridor and **independently** verified with existing source ideal footprint oracle; zero foreign owner, alpha leaks. Avoid falsely calling ordinary row/column scanning a full cellular decomposition: require explicit serialized cell graph, split/merge event classification and deterministic cell-coverage ledger. Use EDT for clearance and brush width1..10 selection; a narrow medial-axis branch is optional separate prospective variant only after comparing first decomposition result. **Do not implement contour-parallel/spiral just for decoration**; both remain alternatives for shapes where cellular sweeps fail.

- Source original bytes→genuine engine128→CTR1→strict S4.6 `original_rgba`, `game_index`, `paintable_id`, `source_edge`, `protected_original_dot`; all masks generated fresh. No source or S4 schema change, no old output PNG as input.
- Region cells must preserve source region ID even for adjacent same-swatch areas; real split/merge events must be logged and unit-tested on donut, branches, one-pixel neck, alpha wall, overlapping rows, two swatches and disconnected same-swatch components.
- Cell allocation constrained by visible unpainted content, boundary adjacency and important protected-dot proximity; preserve internal white detail as candidate. Rank by **measured marginal useful region coverage**, not global raw WHITE6 area; record original source nonWHITE6, WHITE6, edge, residual and per-cell coverage separately. No unverifiable semantic confidence claim.
- Keep exactly frozen source-only budgets broad ≤1400 model evaluations /80 accepted and detail ≤600/120; total ≤2000/200. Original normal/smooth=false and `safe_to_execute=false`. Each candidate requires existing `swept_capsule_pixel_masks` proof of model valid owner/game/alpha, including closed interior.
- Test by comparing same S5-R3, S5-R4, S5-R5 frozen code baselines and candidate R6 from EACH fresh four-source original twice, no archive inputs for source. Independent model footprint reconstruct all accepted proposal unions. Maintain SHA anchors and portable actual algorithm-generated visual panel(s); save source cell graph/event ledger, negatives and provenance.

## Frozen feasibility gates (before any result)

1. NonWHITE6 potential-covered source cells ≥ **max(frozen R4,R5)** each: wV≥2726, Hello≥7501, EZAL≥110777, Pink≥14877. Strict **≥10% relative improvement** over max(R4,R5) nonwhite on at least2/4 originals to require meaningful architectural gain, rather than tiny numeric tweaking. If gates fail retain `FAIL_CELLULAR_CONTENT_FEASIBILITY` and negative artifact without threshold revisions.
2. Total modeled potential coverage ≥ frozen R3 (wV9248, Hello9062, EZAL53300, Pink15368) on all four. Protected original dots potentially touched ≥120 each; zero foreign/alpha accepted, same caps and 4×2 deterministic.
3. Actual genuine Boustrophedon split/merge cell decomposition must pass synthetic topological invariants (no mixing, deterministic graph, no dropped source-allowed cells) before full originals; failure in segmentation is a scientific failure even if pixel coverage improves.
4. Full visual quality, original contour and semantic eyes/face/hair/shape remain **independent PARTIAL/UNKNOWN** until validated; modeled nonwhite gain isn't a human visual PASS. No pseudo-Chalk; E3 native full scene, E4/E5 and exact run-bound CHALK stay BLOCKED/NOT_RUN.

**Reproducibility:** new experiment ID `ENGINE001_BPRED_S5R6_BOUSTROPHEDON_SWEEP_CELLS_V1`; existing source128 engine bundle blob `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`, source quarantine and SHA pins. No production/Stage6/Bridge/Monitor/CHALK changes.

**Next implementation:** inspect current region masks and S5-R4/R5 selector, build source-only sweep-cell graph and synthetic topology tests as one bounded extension (not separate game renderer), then four originals×2 via new isolated CI. Evaluate failures before considering Medial Axis or contour-parallel variants.

## Explicit internet-method status before S5-R6 execution

- EDT: E2 **already used** as source-space clearance; no native production proof.
- Repeated parallel sweeps: E2 **already used partially** in S5-R4/R5.
- Full Boustrophedon Cellular Decomposition: **planned here, NOT_RUN** until cell graph and events exist.
- Marginal geometric set-cover scoring: **partial existing** with bounded selection, not guaranteed optimal.
- Medial Axis, contour-parallel and spiral methods: **not implemented**, reserved for evidence-based alternatives.

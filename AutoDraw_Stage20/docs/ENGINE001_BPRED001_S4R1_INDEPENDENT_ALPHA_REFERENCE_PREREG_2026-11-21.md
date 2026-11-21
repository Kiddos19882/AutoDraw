# ENGINE-001 / BPRED-S4-R1 — E0 independent original-alpha boundary reference

**Frozen prospective source-validation protocol, 2026-11-21.** Registered before any new alpha-interface metric or source-protection correction. Baseline remote branch HEAD `d9428b14ab2e09edb696e3134efb865cbad92869`. Continues the FIRST OPEN S4-R1 task: find a genuinely independent source-owner/critical reference, without pretending nearest palette labels, SLIC or pretrained pseudo-labels are semantic ground truth. Reuse current [31-source corpus prereg](ENGINE001_BPRED001_S4R1_AUTOMATIC_MULTIMAGE_PROTECTION_PREREG_2026-11-21.md), [existing S4R1 source-region E2](ENGINE001_BPRED001_S4R1_SOURCE_REGION_UNCERTAINTY_DEV_E2_RESULTS_2026-11-21.md), DEC-044/045 and [S0→S6 plan](ENGINE001_BPRED001_BRUSH_PREDICTION_PLAN_2026-11-20.md).

## E1 pre-experiment eligibility findings, no quality claim

The 31-source E2 audit and independently verified ZIP #14688895126 already record **15 DEV+8 KNOWN_CONTROL+8 LOCKED_HELDOUT**. Source metadata shows **1/15 DEV with any alpha <255** (`Sanrio_Characters_Hello_Kitty_Image026.webp`), and 5/8 known historical icons with alpha; 14 DEV fully opaque. Source alpha is a **real, independent binary reference for source opacity**; it is **NOT semantic ground truth, a human-verified owner partition, game paint coverage, or a reliable label of the original white background**. For 14 opaque DEV images alpha gives no independent interior owner/semantic classes. User disallows per-image manual production masks; independent test labels must not be injected into an automatic runtime mapping.

Frozen historical model evidence: [OneFormer CI44147852418](https://github.com/Kiddos19882/AutoDraw/actions/runs/44147852418) genuine original-source ADE20K semantic labels (numeric 0/22 only on known Egret); [SAM2 CI44127991472](https://github.com/Kiddos19882/AutoDraw/actions/runs/44127991472) original image masks with previous source quality FAIL, [DINOv2 CI44137289780](https://github.com/Kiddos19882/AutoDraw/actions/runs/44137289780) original embedding changes but source ΔE/background FAIL. None is an independent real-image source-color owner oracle. Do not rerun their old experiments or reinterpret their original quality FAIL.

## Hypothesis, independent source reference and frozen metrics

Use **original EXIF-oriented RGBA** as the only geometric opacity reference, before palette projection or segmentation. Define, exactly on each DEV/KNOWN source H×W:

- `invalid = original_alpha < 255`, including A0 and fractional alpha.
- `opaque = original_alpha == 255`.
- `opaque_interface_4 = opaque AND at_least_one_four_neighbor(invalid)`, never diagonal-only; exact source pixel grid (not logical, CSS, native or PNG replay). This marks the **opaque side** of a true alpha transition.
- `invalid_protected = count(invalid & source_maps.protected) / count(invalid)`.
- `interface_protected = count(opaque_interface_4 & source_maps.protected) / count(opaque_interface_4)`.
- `interface_geometric_core = count(opaque_interface_4 & source_regions.geometric_potential_core)` is a diagnostic; do not equate core with executable safety.
- If any denominator zero, mark N/A rather than 100%. Report counts and the **exact per-image SHA/shape/role**, not only averages; group DEV vs known controls separately.

**Frozen safety expectation:** invalid protection 100%, opaque-side four-connected alpha interface protection 100% on each of the six eligible DEV/KNOWN sources; otherwise **FAIL_ALPHA_INTERFACE_SOURCE_PROTECTION**. This does not reduce old native safety thresholds; it is a strictly additional source-only requirement. Internal semantic owner correctness/protected recall remain `UNKNOWN / NOT_READY`, even if every alpha pixel passes. Do not tune size-specific thresholds or infer pixel-safe from geometric core.

## Execution scope and test methods

1. Before new derived output, re-run existing immutable first E0/owner E0/region E0 hash, original raw SHA/Git blob/EXIF/alpha and dHash/pHash leakage *screen*. H8 may be read only as already-authorized source identity/near-duplicate metadata; **do not compute interface mask/results/output on H8**, do not use the reserve second50 or S0 BLIND120.
2. Add the smallest pure-array `original_alpha_interface_reference` utility to the **existing** (ф) `tests/engine001_bpred_s4r1_generic_source_maps.py`, use original `rgba`, `generic_source_maps` and `original_source_region_uncertainty` without changing SLIC, source ΔE, or game palette choices. For a failing baseline, preserve original failure evidence (E2 job/status, per-image counts) before a minimal correction. No fake fallback SAFE. A correction may explicitly protect the opaque side of verified original alpha transitions; it must not change provenance, acceptance metrics, production, stroke admission or old science.
3. Unit tests independent toy RGBA originals: opaque-to-A0 transition, opaque-to-partial-alpha transition, diagonal not four-connected, all opaque/all invalid are N/A, arbitrary dimensions, valid boundary counts and real alpha immutable. For actual DEV/KNOWN run record per-image reference totals in existing `dev_summary.json`; add no hand-drawn per-image masks, and retain 184 existing PNGs (unless specifically justified).
4. Aggregate only after per-image check; forbid source interface `PASS` on zero applicable sources. Record E2 code SHA, signed raw artifact hashes, CI jobs, negative cases and one source-only decision. A technical E2 pass and alpha-source reference pass **do not prove independent color owner/semantic truth**. If this limited alpha audit passes, next separate prereg is an external or genuinely annotated **DEV** semantic/owner reference, or a pinned pretrained *semantic hint* evaluated against such independent truth with abstention. OneFormer, SAM2, DINOv2, BiRefNet may provide hints, not ground truth.
5. Strict S4, independent BLIND120, heldout8 output, S5/S6, native E3, E4/E5, exact live CHALK, production, master, Stage6/Monitor/Bridge unchanged and not authorized by this E0.

**Stop:** If no independent original-label evidence beyond alpha is present, record partial source-reference utility and the unverified owner/semantic blocker. Never invent false semantic recall, relabel pretrained pseudo-masks as truth, or loosen native quality gates for PASS.

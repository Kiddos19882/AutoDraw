# ENGINE-001 / BPRED-S4-R1 / SEMREF1 — prospective blinded human-verified DEV reference

**2026-11-21; E0 / NOT_RUN.** Frozen *before* any SEMREF1 annotation ingestion, scoring code or scoring result. Existing source E2 CR1 is already known to be negative: 43,534/861,166 high-contrast original endpoints unprotected on 13/14 DEV. This is *not* a semantic or native brush ground truth. Baseline remote `feature/image-geometry-optimization` commit `b0466321d3bcde926debba66dae14eb1d14d6bf2`; [CR1 signed result](ENGINE001_BPRED001_S4R1_OPAQUE_DEV_COLOR_REFERENCE_E2_RESULTS_2026-11-21.md) and [accepted main plan](ENGINE001_BPRED001_BRUSH_PREDICTION_PLAN_2026-11-20.md), DEC-044/045 and earlier NH1–NH4 retain authority. No training, no source mask/threshold tuning, no production changes.

## Exact aim and pre-fixed limited DEV subset

Obtain **independent human-reviewed** source-image critical details and human-perceived distinct-color-region boundaries to check *risk proxies* of the unchanged `generic_source_maps` and P2 `geometric_potential_core`. A reviewed boundary is **not an exact game128 owner**; no stroke may be admitted from this study. Two independent reviewers must view **the untouched original source RGB only** and annotate without viewing CR1 red/teal overlays, math protected maps, SAM2, OneFormer, DINOv2 or BiRefNet outputs. Independent reviewers must not be the candidate algorithm or a generated pseudo-label. Do not self-certify independent review from source/code alone.

Precisely four frozen opaque DEV image basenames from the existing CR1 baseline, chosen *before* review by strata (three largest already observed CR1 unprotected counts and one zero-miss contrast control): `6f6fff4105b941bf85b1fbd8519a.jpg`, `ima56655ges.jpg`, `EZAL3k9ddfs.jpg`, `images (1).png`. These are **biased exploratory selection**; no inference to all 14 DEV or H8. Require exact `role=DEV`, original Git blob SHA, raw SHA256, RGBA SHA256, EXIF-oriented H×W from frozen [corpus E0](ENGINE001_BPRED001_S4R1_AUTOMATIC_MULTIMAGE_PROTECTION_PREREG_2026-11-21.md) and original source decoder. Never open the eight LOCKED_HELDOUT, S0 BLIND120, or reserve `images2_50_second`.

## Annotation input and independent identity

For each of the four, reviewers independently supply a **full source-H×W, RGB PNG** label map in exact pixel coordinates with no antialias/resize and these five literal RGB codes, one per pixel:
- `(0,0,0)`: UNREVIEWED, neither positive nor negative;
- `(255,0,255)`: independently verified eye/face/hair/hand/contour **critical detail**;
- `(0,255,255)`: independently verified boundary between **human-perceived distinct original-color regions**, without claiming game128 owner;
- `(0,255,0)`: verified interior of a single visually coherent source region, not semantic critical/boundary;
- `(255,255,0)`: ambiguous, forbidden for positive or negative scoring.

Collect two provenance sidecars per file: `reviewer_id` distinct nonblank IDs, `source_raw_sha256`, `source_git_blob_sha1`, `original_rgba_sha256`, `original_hw`, `labels_png_sha256`, `source_only_blind_review=true`, `annotation_tool_and_version`, and a review timestamp. Sidecars are attestations, **not automatic proof of reviewer independence**; absent, contradictory or algorithm-generated attestations block scoring. IDs should be pseudonymous, no personal identifiers. Reviewers must not use model-generated masks as labels.

Scored support is the pixelwise **agreement** of both reviewers on the critical, distinct-region-boundary or verified-interior labels; disagreement, ambiguity, or UNREVIEWED is **UNKNOWN/EXCLUDED**, not negative evidence. No inferred complete owner map. Require nonzero independently agreed critical/boundary pixels AND nonzero agreed interior pixels **on each image**; otherwise per-image `BLOCKED_INSUFFICIENT_VERIFIED_SUPPORT`, not zero-error PASS. Missing any of four image labels => cohort `BLOCKED`; no majority-of-four success promotion.

## Frozen outcomes, non-vacuity, and stop rules

For agreed critical/boundary support `K`: count `K & protected`, `K & unknown`, `K & geometric_potential_core`; report `protected_recall_on_reviewed_K` and `core_critical_overlap` (a **potential** false-safe *risk*, not admitted strokes). For agreed noncritical region interior `I`: count `I & core` and `I & protected`, `core_fraction_on_reviewed_I` (non-vacuous source-only usefulness proxy). Report both pixel-weighted and per-image results, numbers of reviewer disagreements/unreviewed and raw label PNG+input hashes. `candidate_interior` must remain empty and `stroke_admission=FORBIDDEN`; if either changes, stop. At this stage no optional neural new inference: existing NH masks can be compared **only under another prospective E0** after human reference is frozen, never used as true labels.

Existing hard native/protected-owner zero, far leakage <=3 logical px, coverage >=99%, usefulness baseline >=90%, S4 BLIND eligibility and S5/S6/CHALK gates **are not re-scored**. An all-UNKNOWN baseline cannot achieve useful-success by having zero accepted strokes. Even perfect `K` recall on four partially labelled DEV files is not full semantic safety PASS. Distinguish `E0` plan, `E1` static provenance audit, `E2` synthetic scorer tests, and `E3/E4/E5` genuine native/game/independent validation. In absence of two real independent reviewer labels, scientific status is **BLOCKED**, never simulated PASS.

## Execution limits and definition of the next result

Reuse existing original decoder, frozen manifest, CR1 review-only 14 original PNGs; **do not produce duplicate source-image packets**. Add only a small research-only validation/aggregation scorer and isolated synthetic regression + scoped CI for source provenance, disagreement/UNKNOWN, label codes/sha, and scientific BLOCKED when no human annotations are supplied. Do not commit fabricated image labels or pass synthetic labels off as original DEV evidence. Freeze this document as immutable Git blob before scorer implementation; CI may assert that blob. Record CI SHA and status, and a signed report explicitly stating `SEMANTIC_GT_NOT_YET_AVAILABLE` if human reviews are absent.

After real independent review and separately frozen data provenance, evaluate risk/abstention on the four DEV cases, then decide whether a larger independent DEV label set is justified. **Strict S4 and S0 BLIND120 remain BLOCKED, native original Egret S4 E3/S5/S6 and game E4/E5/exact CHALK NOT_RUN; no production/master/Stage6/Bridge/Monitor edits.**

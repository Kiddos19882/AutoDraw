# ENGINE-001 / V39 — resource-neutral native boundary-biased fill placement

**2026-11-16 | PREREGISTERED / NOT_RUN before V39 CI**. Task ENGINE-001. Built only after V38 native archival gap audit E3 PASS. User's approved arrangement: **1945 paint strokes, then all 410 user-preferred dark V35-B contour strokes**; do not remove or recolor user-selected outlines.

## Why test this

Source [V37-P2 CI43747149144](https://github.com/Kiddos19882/AutoDraw/actions/runs/43747149144), SHA `04e506a3bf41b5d197a19bb20e36e8f445d79dec`, original original PNG SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`, artifact `14175105717`, ZIP SHA256 `a9d97229fada28875d718ba7c1c068464dfe8529fc1b313becb9a77e2ed50959`. V37-P2-C restores warm colors by recoloring166 fill paths and preserves V35-B full dark contours. Native geometry 2355 strokes/5682 synthetic accepted vertices (NOT game CHALK), only218 synthetic vertices remain under the native5900 probe cap. A/C RGB MAE baseline V37-P2-C 19.42033333 and warm 27.90450328.

[V38 audit CI43767506202](https://github.com/Kiddos19882/AutoDraw/actions/runs/43767506202), SHA `e31d920e9b8cf40a9d1cac42c76f7a3ec1a56221`, artifact14182976831 ZIP SHA256 `b3638a459fcdeeaac1cf2d2e3a58b7a08f211f7eec527221b6d5f85db6fd3208`: true Egret source-ROI class native alpha24 recalls4=71.0778%,5=77.8104%,6=57.7122%,7=94.7256%; all class-target missed native pixels are within3 native pixels (1 logical) of their source class boundary, and no fill alpha farther than 3 logical px from source palette foreground. This is diagnostic source MEDIANCUT8, NOT proof of brush position correction or true per-color99% acceptance.

**Hypothesis**: shifting the *existing*, source-matched width2 horizontal scanline paint strokes slightly toward local same-class support can improve correct native same-color recall without additional accepted game points, preserving user-preferred full dark line topology and current warm RGB. This can FAIL by moving paint away from other required pixels or increasing wrong-class bleed. All measurements must use actual Egret BoardPane/WebGL PNG, not modeled brush footprints.

## Frozen A/B/C and exact shift rule (one variable: y offset)

Immutable input: `V37-P2/color-plans.json` variant **C**, exactly1945 fill with original V37-P2-C RGB + 410 frozen V18-B dark detail, 2355 strokes,5682 native accepted synthetic vertices. Colors, widths, x coordinates, endpoint shims, original stroke IDs and order, brush mode, backdrop and path count unchanged.

- **A:** frozen V37-P2-C, no coordinate edits. Native actual RGBA composite PNG must match `C/V37P2-C-composite.png` decoded pixel-for-pixel plus critical IHDR/IDAT chunks, or BLOCKED.
- **B:** y-shift `0.25` logical pixel for qualifying fill strokes (both endpoints equally); no movement otherwise.
- **C:** identical direction and qualifying strokes as B, but y-shift `0.5` logical pixel.

Determining direction from **original source mask alone**: LANCZOS source ROI 150×240, `quantize_case(roi,canvas,8,False,True)` to fixed 460×240 source label map. For each original width2 paint stroke, take the same 5 source-label sample x positions at t=(0,.25,.5,.75,1), Python `round` then clamp to board x155..304. Original row y must be integer-valued. At y-1 and y+1, count sample sites with the stroke's original `colorIndex` (4..7). If `bottom_count - top_count >=2`, direction +1, if `top_count - bottom_count >=2`, direction -1, otherwise0. Reject row shift beyond 0..239 and any original label mismatch or corrupted source. All unchanged detail strokes come **after** all paint; no deleting, splitting, shortening, recoloring or adding lines. This is a deterministic **source-derived placement proposal only**; never infer Egret footprints from this neighborhood count.

## Fixed evidence and decision

Verify frozen original source SHA and V37-P2 manifest hashes. Before render, assert all A/B/C have identical stroke count=2355, synthetic vertices=5682, all410 dark detail identities/order/coordinates exactly identical and **all** candidate differences limited to the y-coordinate of corresponding paint endpoints with absolute shift <=0.5 and x unchanged. Native renderer must accept every synthetic point. For isolated actual Egret class4/5/6/7 and detail100 plus composite, archive RGBA and immutable per-file hashes.

Measure at alpha thresholds24 and128 against **fixed MEDIANCUT source**: per-class target recall (not just union), wrong-class painted pixels, class interior holes, union silhouette recall/precision, leakage>3 logical px, actual source full RGB MAE and warm ROI MAE, A/B/C visual full + face/hand crops and unchanged contour isolated alpha. Preserve changed-stroke count and displacement direction histogram.

**Candidate boundary-placement diagnostic improvement** only if at alpha24 **all four correct-class recalls >= A**, at least one strictly >A, union foreground recall>=A, leakage>3 logical px not increased and no extra accepted points. Additional prerequisite for recommendation: source full RGB MAE and warm-region MAE cannot worsen vs A; source changed colors strictly forbidden. Visual review cannot lose recognizable eyes/hair/hands. Negative outcomes kept, no retuning of0.25/0.5 or support difference2 after seeing results.

This is **E3 native experiment only**, not game E4/independent E5 or exact CHALK. Equal synthetic accepted vertices do not guarantee actual game quota/cost safety. Original production >=99% required per-color gate and <=3logical-px exterior remain fixed, no promotion without source quality and actual-game run-bound `CHALK=post.pointCount-pre.pointCount` plus independent validation.

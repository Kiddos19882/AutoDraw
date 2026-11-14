# ENGINE001_STRUCTURE_FIRST_V7 — exploratory contour-path research preregistration

**Task:** ENGINE-001 / next complex-art architecture research. **Registered:** 2026-11-14 **before any V7 generated preview**. **Status:** PRE-REGISTERED, metrics NOT_RUN. **Baseline:** pinned source image SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`, Git blob `d3cd95b846f036a3f8acecf75d2a237e46dcf13a` (200×320, 97308 bytes); frozen V5 eight-color source-masks and native E3 fail, V6 local edge diagnostic 4402/4869 source edge pixels matched, 7/48 connected components under 50% retention.

## Hypothesis and scope

H1: extracting continuous image-edge paths **before** per-color segmentation can preserve identifiable contours that the V5 per-palette-class long-stroke selection discards. H0: path extraction yields insufficient coherent strokes or causes excessive line coloration/coverage side effects. V7 is **not** a new unbiased held-out sample (source was used for V5/V6), cannot prove human recognition or production suitability.

The frozen V5 source pre-processing remains unchanged: white logical 460×240, original 200×320 contain at 150×240 with (155,0), LANCZOS. Original logical source ROI only, Canny grayscale after 3×3 Gaussian blur, L2gradient=True, thresholds 60/120; 8-connected edge mask components and `cv2.findContours(RETR_LIST, CHAIN_APPROX_NONE)` on binary Canny edges. Ignore contours with original arcLength <12 logical px, approximate each with `cv2.approxPolyDP(epsilon=0.65, closed=False)`, reject candidates with fewer than 2 points or geometric path length <12, split paths over 128 vertices at shared endpoints; cap total paths to 400 and vertices to 2500, otherwise fail-closed. Add logical ROI offset (155,0), no alteration to pinned source. This is a **proposed static path generation heuristic** and not proven optimal for branching lines or junction connectivity.

Assign stroke RGB as median original RGB values sampled at rounded path vertices, not an inferred background replacement; set **research-only width parameter 2** to match opt-in BoardPane accepted width, explicitly without claiming it has calibrated physical footprint. Preserve paths and RGB/positions in JSON; count path length, strokes and vertices. Approximate preview on a white 150×240 ROI with OpenCV `cv2.polylines(thickness=2, LINE_AA)`, and separately preserve source and Canny masks; this is **not** native Egret or the intended multi-color final artwork and may overpaint at intersections. Generate an overlay to compare extracted paths to original contours, plus per-path lengths/colors and rejection counts. Do not re-use preview to select better constants under this ID.

## Validation gates

- Source bytes, Git blob and SHA must match pinned values, or abort.
- Enforce finite in-bounds coordinates and 2..128 points; reject or fail closed on quota.
- Record number of edges covered within 1px of centerline as an **exploratory path continuity proxy**, excess drawn pixels, total length, stroke and vertex counts, segmentation and rejection reasons.
- Unit fixtures for long line, short line, 128 vertex limit, path coordinates, deterministic selection, SHA guard.
- Allow local E1/E2 and optionally E3 true native Egret only after tests and source binding. Human recognition requires independent blind evaluation on *new* art; require per-color overpaint/coverage, symmetric 3px diagnostic boundary, unchanged >=99% geometry gate, independent game E4 exact CHALK and E5 before any production promotion.
- Do not modify V5/V6 freeze, production, executor, monitor, calibration, color-quality acceptance or master.

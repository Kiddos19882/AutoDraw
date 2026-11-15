# ENGINE-001 / V43 — adaptive shape-aware color fill with native Egret gates

**2026-11-16. Status: PREREGISTERED, phase P1 MODEL_ONLY/NOT_RUN.**
Task family: `ENGINE-001`, independent experiment ID `ENGINE001_SHAPE_ADAPTIVE_FILL_V43`. User accepted researching a **hybrid medial-axis / locally oriented boustrophedon / large-to-small brush** approach, instead of repeatedly extending uniform horizontal scanlines. This does **not** close or silently replace separately open V42 source-RGB-aware endpoint work: V43 is a new architecture candidate.

## Why new experiment, not a new production implementation

Recent source-native experiments on `wV6VeZI9S1Y.png` confirmed the **full V35-B 410 dark contour paths above paint** are preferred by the user. V37-P2-C is the frozen color-filled/outline reference: 1945 width2 fill strokes followed by410 width1 detail,2355 strokes /5682 synthetic accepted vertices **NOT actual CHALK**. [V41 CI43775534257](https://github.com/Kiddos19882/AutoDraw/actions/runs/43775534257) E3 executed B/C selective edge extensions: own source-class coverage increased but actual RGB error worsened; both combined quality gates FAIL. [V40-P1](ENGINE001_V40_INTERNAL_COLOR_TOLERANCE_AUDIT_PROTOCOL_2026-11-16.md) demonstrates **foreign source-color overlap <=3 logical pixels is explicitly allowed** and native alpha crossing stayed in tolerance. Requirement is **NOT** strict no-overlap.

Existing `source/preparation/brush_planner.py`, `interior_fill_planner.py`, `brush_footprint_geometry.py` use abstract/conservative footprint bounds and mark their geometry recommendations `safe_to_execute=False`. [V30 frozen negative](ENGINE001_VISUAL_ADAPTIVE_FILL_V30_PROTOCOL_2026-11-15.md): interior rectangle-model candidate6396 strokes and outline-first7892, both **more than V28-D6373**; theoretical model coverage does **not** establish true Egret brush behavior. Reuse `source/preparation/skeletonization.py` (Zhang–Suen skeleton, path tracing) and existing source `prepare_source`/`quantize_case`, calibration/harness where applicable. Do not fork another renderer or change production.

### Published method families (research leads, not directly validated game solutions)

- Choset, *Coverage Path Planning: The Boustrophedon Decomposition* (CMU) — cellwise parallel sweeps for complex areas.
- Hertzmann (SIGGRAPH 1998), *Painterly Rendering with Curved Brush Strokes of Multiple Sizes* — coarse-to-fine strokes.
- Medial-axis / distance-transform methods (scikit-image documentation) — local region thickness and shape.
- Region-based robotic painting and coverage planning — partition, stroke direction and feedback.

See referenced prior literature discussion in this conversation. The research hypothesis is that a **per-connected-component decision** among oriented sweeps, skeleton-following thin paths and wider interior strokes with later boundary corrections can reduce native resources without losing user-recognizable details. None of the papers proves game point economy or the correct Egret brush footprint.

## Frozen image and mask scope

- Source file `AutoDraw_Stage20/testImages/wV6VeZI9S1Y.png`, SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`; RGB200×320, LANCZOS resize ROI150×240, BoardPane logical460×240 at x155..304. Fixed 8-class Pillow MEDIANCUT source labels; required palette class IDs4..7, skipped0..3. Preserve source RGB/color assignments for A reference.
- Outline: archived original **410 V35-B contours**, **drawn LAST** with exactly the same native width1, color, ID, points and ordering across A/B/C.
- User-approved internal adjacent-color crossing **at most 3 logical px** and existing outer silhouette<=3logical px. Required class own-color coverage>=99% remains unchanged; no redefinition of acceptance after results.
- Real point quota is *only* run-bound game `CHALK=post.pointCount-pre.pointCount` with valid Monitor binding. Offline synthetic vertices, brush area and length must not substitute. Frozen native replay cap3000 strokes/5900 synthetic vertices is a harness safety limit, **not** certified game quota.

## P1 — shape analysis, implemented first, E1/E2 only

Read and verify source SHA and quantized required-color mask. For each 8-connected source-color component, compute component area, 2×2 pixel covariance/principal-axis angle, `cv2.distanceTransform` local thickness, and branch-relevant shape summary. Skeletonize **only component masks** via existing `thin_binary_mask` for modest image-size bounded components and record skeleton pixel count. Categorize each component as a **candidate**, not an executable path:
- `wide_interior_candidate`: max inscribed Euclidean distance >=4 *logical source pixels*.
- `thin_shape_candidate`: max distance <4; may use skeleton-following drawing.
- `oriented_sweep_candidate`: enough spatial anisotropy (major eigenvalue >=2× minor eigenvalue) and component area>=16; suggest sweep orthogonal to major axis as one approach to reduce stroke ends. These are predeclared heuristics for exploration, **not** assumptions about the game brush width, nor guaranteed coverage.
- Otherwise mark `mixed_or_small_candidate`, no speculative brush path.

Freeze JSON per-class component counts, area distribution, principal axes, distance maxima, candidate role summaries, original source hash, source mask checksum, versions. For memory/latency, skip Zhang–Suen skeleton for components area>3000 and mark `SKIPPED_RESOURCE_BOUND`; do not claim skeleton data from skipped items. Source class blobs differ from semantically continuous hair/skin regions: classifications are **not** semantic object recognition.

P1 may use cv2/Numpy only for **shape analysis**; it must not claim native paint coverage, cost, CHALK, visual likeness, actual brush safety, or production acceptance. Required checks: same source/classes, no invisible class as fill, all component pixels accounted for, deterministic output, source integrity, invalid masks rejected. E2 unit tests/CI required before moving on.

## P2 — future independently frozen actual native Egret A/B/C

Only after P1 E2 and source component evidence inspected, freeze three candidates *before* any native test:
- **A** = unmodified frozen V37-P2-C (1945 fill width2 + 410 untouched contours; true native RGBA baseline replay mandatory).
- **B** = connected-component adaptive oriented sweeps + actual Egret brush widths chosen from **supported native sizes**, with paths converted using existing code. Do not rely on model rectangle as brush acceptance.
- **C** = B plus skeleton-following thin-area paths / coarse-to-fine fill and **native alpha-based gap correction**. Never tune on the resulting final native PNG without a separately preregistered phase/new experiment ID.

Preserve A/B/C full physical source-mask and source RGB, all 410 final dark contours, same BoardPane WebGL image coordinate mapping and width semantics, native alpha24/128 by required class and per-color foreign overlap at<=9/>9 native px, silhouette leakage, original-source full/warm RGB MAE, user-reviewable face/hair/hand crops, stroke counts, synthetic accepted vertices and color switches. **Reject** an A/B/C candidate exceeding3000 native strokes/5900 synthetic accepted vertices or dropping contour paths; archive such a case as `OVER_BUDGET`, do not crop silently. Every native scene uses the real `BoardPane.redraw()` Egret canvas, not geometric raster proxies. Correct class coverage, silhouette and RGB non-regression remain separate gates; source α footprint cannot serve as exact game CHALK. E4/E5 and production changes are **NOT AUTHORIZED** by P1.

**Stopping rule:** if P1 only yields no sufficiently broad components, preserve `NO_WIDE_REGIONS` finding and do not blindly generate oversized brush paths. If P2 B/C worsens source RGB, violates internal/external3logical px, any class recall or visual outline legibility, reject and retain the frozen baseline.

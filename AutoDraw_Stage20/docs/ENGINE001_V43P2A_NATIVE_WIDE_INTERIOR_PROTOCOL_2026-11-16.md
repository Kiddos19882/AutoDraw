# ENGINE-001 / V43-P2a — actual Egret wide-brush feasibility on one large dark component

**2026-11-16 | PREREGISTERED BEFORE NATIVE CI | NOT_RUN.** Independent sub-experiment of [V43 hybrid fill research](ENGINE001_SHAPE_ADAPTIVE_FILL_V43_PROTOCOL_2026-11-16.md), not a complete replacement for oriented/skeleton paths. No changes to production, source/planner owner APIs, master, Stage6/executor/Bridge/Game Monitor.

## Frozen evidence and purpose

Frozen V37-P2-C actual source paint: [CI43747149144](https://github.com/Kiddos19882/AutoDraw/actions/runs/43747149144), SHA `04e506a3bf41b5d197a19bb20e36e8f445d79dec`, artifact14175105717 ZIP SHA256 `a9d97229fada28875d718ba7c1c068464dfe8529fc1b313becb9a77e2ed50959`. Original source `testImages/wV6VeZI9S1Y.png` SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`, ROI150×240 at x155..304 on 460×240 board, 3× actual BoardPane WebGL.

[V43-P1 CI43777328342](https://github.com/Kiddos19882/AutoDraw/actions/runs/43777328342) SHA `8d3a1892ab14ce288f161158e1688cf8b6b457af` **E2/MODEL_ONLY**: 1575 source-color components, 9 with maximum distance-to-boundary >=4 logical pixels; these 9 contain6928/16539 (~41.89%) required-color pixels. Largest retained source class7 dark-component area5005, max inscribed radius16. This justifies *testing* the native wider brush there, not assuming modeled rectangles or a resource saving.

**Hypothesis:** replacing width2 by width4 or width6 on existing interior strokes of only the **largest class7 dark component** could increase actual native same-color coverage at equal synthetic accepted vertices, but might worsen original/warm RGB or exceed 3 logical px internal/exterior overpaint.

## Fixed selection and variants

A/B/C all use **identical original V37-P2-C** 1945 paint path points/order/colors/IDs +410 original V35-B dark width1 detail paths LAST: 2355 total paths/5682 synthetic accepted vertices (NOT exact game CHALK). No skipped or added strokes and no modified coordinates. Deterministic selector from **original source pixels only**, with no native output used for B/C fitting:

1. Reuse frozen original label map from `tests/run_engine001_native_color_boundary_audit_v38.original_labels`, downsample native mask by3 to 240×460 logical labels. Find 8-connected components on source class7 and select the **largest** by area; tie-break lower connected-components label ID. Demand largest area **5005** (frozen P1 count), otherwise BLOCKED.
2. Compute `cv2.distanceTransform` with `DIST_L2`, `DIST_MASK_PRECISE` inside that component, with one-pixel zero-border padding. For each original **colorIndex=7** width2 **horizontal two-point paint stroke**, sample five points `t=(0,.25,.5,.75,1)`, original `round` logical x/y and clamp to original ROI, only if all five points are in that largest component.
3. **B width4** if **all five** source-center distances >=4 logical px. **C width6** if **all five** source-center distances >=5 logical px. Otherwise retain original width2. No width1/width2 original outline changes. These are source-proposal gates, **not simulated native brush footprints**.
4. Record selected IDs/counts and per-stroke distances, selected actual component ID/area, every width, source hashes. Source class7 is dark suit/garment, but no claim this mathematical blob corresponds perfectly to a semantic object. A always width2.

### Required native checks

Reuse actual archived Egret `BoardPane.redraw()` and existing native browser harness with an **isolated** V43-only method accepting fill widths2/4/6 and **detail width1 only**; original V35/V36 render methods and default semantics remain intact. Original A actual RGBA PNG must be pixel-exact archived V37-P2-C. All410 original dark contour source paths and native alpha must be exactly identical in B/C. Reject any modified stroke count, per-stroke source color/position, source SHA, native accepted points, native artifact mismatch, >3000 total strokes or >5900 synthetic vertices.

Record actual Egret source-quantized α24 and α128 per-color own recall, foreign-color internal crossing allowed<=9native px/excess>9native px, whole silhouette exterior>9 native px, original/warm RGB MAE, image composite and facial/hair/hand readability, actual alpha of isolated color7, strokes/vertices/width counts and comparison PNG/JSON with SHA256.

**Predeclared numeric native candidate PASS only if** class7 own α24 recall strictly greater than A and **classes4–6 own recall not worse**, union source foreground recall>=A, internal excess<=A at α24 and128 (A expected0), exterior excess<=A at α24/128, both full and warm RGB MAE<=A, same resource count. Other classes/alpha stats recorded; class colors/source RGB not altered. Outline legibility judged separately by same original crops. Failure of any required metric => candidate diagnostic FAIL, preserve raw PNG; no retuning thresholds after outcomes.

This P2a does **not** prove oriented boustrophedon/skeleton algorithm savings, production quality>=99% per required color, exact CHALK or live game E4/E5. After P2a evidence, only then draft a separate native full hybrid A/B/C path replacement under the same fixed source/user-quality and budget gates.

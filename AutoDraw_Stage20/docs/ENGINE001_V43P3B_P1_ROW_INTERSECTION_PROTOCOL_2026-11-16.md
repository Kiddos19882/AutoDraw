# ENGINE-001 / V43-P3b-P1 — native-footprint row-intersection old-stroke selection

**Дата:** 2026-11-16. **Статус:** PREREGISTERED / E2/E3 NOT_RUN. **Новый эксперимент:** `ENGINE001_V43P3B_P1_NATIVE_ROW_INTERSECTION`. Продолжение той же задачи ENGINE-001/V43-P3, **не переопределяет** замороженный P0. Production/executor/Bridge/Monitor/master не меняются.

## Контекст и гипотеза

[Замороженный P0 CI43878183627](https://github.com/Kiddos19882/AutoDraw/actions/runs/43878183627) E3 capture PASS, artifact14232130110 ZIP SHA256 `758edaf0b0888d40d10cf5fdf3ec0a1eb1cf5e5ea8e60a61feb29359662e8b4c`, but **0/18 full old scanlines substitutable**; old native-own-color pixels covered by three oriented strokes alpha24: width6 0/297, width10 42/1512 (2.78%). P0 limited candidates to entire original horizontal span inside union native bounding rectangle, missing crossing paths. Independent static row-intersection preflight found 14/26/40 original class7 line rows intersect real P3a3 native candidate alpha for width4/6/10; that result is not actual saved-stroke evidence.

Hypothesis: ranking original lines by **native P3a3 footprint ink where they cross the original center row** finds more meaningful candidate old paths than whole-span bbox. It **does not imply** any complete replacement; P1 must retain negative results if no full native owner pixels fit.

## Frozen inputs, ranking and cap

Source `wV6VeZI9S1Y.png` SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`; original 1945 V37-P2-C paint routes from CI43747149144 must pass original manifest; native P3a3 artifact14224453656 original zip SHA256 `4565925cead78a67a993a0b4629a457d9f3d6f5bcea230a1baa91e33b817faa6` must pass 6/6 actual PNG hash. Source largest class7 connected component area5005 and palette unchanged.

For widths **4,6,10** independently, select only frozen original class7 width2 2-endpoint horizontal paint strokes with x155..304/y0..239. Let `C_w` be P3a3 true Egret `color-7` PNG alpha>=24 on backing720x1380. For an original stroke from x0 through x1 inclusive, y logical integer, define **ranking score** exactly as number of ink pixels in native source center row slice `C_w[3*y:3*y+3, 3*x0:3*(x1+1)]` (sum at backing scale). A score of0 excludes the stroke. Score high-to-low, ties by **original frozen paint-list index**. Evaluate exactly **first 12** nonzero-score old strokes per width (or fewer if none). No bbox-full-span requirement. No posthoc re-ranking based on P1 output; report all candidate counts, selected IDs, overlap scores and skipped population. Zero eligible width retains `NO_SAMPLE`, not accepted paint; entire run with no original old strokes must FAIL.

For each selected old route, independently replay **same unchanged original route** via existing `native_batch` / default real BoardPane Egret WebGL. Compare its true isolated own-class7 native alpha24 **and** alpha128 with frozen P3a3 candidate alpha of corresponding width. Require all old own-class ink pixels represented by new candidate alpha at both thresholds to mark `potential_full_replacement_ONLY`. Report number uncovered even for FAIL. Source-only center-row score **cannot** replace per-stroke native full footprint. Reject if archived new oriented candidate foreign/silhouette excess>3 logical px. No deletion or adding strokes to full image in P1, no 410 V44-B contour changes.

## Acceptance/report

Evidence level E3 if legitimate Windows native rendering executed, unit/Node checks pass and all archived PNG hashes pass. Replacement strict savings criterion: selected old wholly substitutable count **greater than 3** for a given width (exact frozen new wide strokes=3), lowering both paths and synthetic vertices; no other resource-savings interpretation permitted. E3 renderer success is **not** replacement-quality PASS. Full-image V44-B original/warm MAE, per-class>=99%, <=3logicalpx, human recognizability, E4 exact `post.pointCount-pre.pointCount`, E5 all remain NOT_RUN. Preserve all negative raw PNG/report SHA evidence.

**Next step after P1 E3:** If no strict net savings, stop this 3-candidate replacement path and redesign wide-first source region coverage without overlay, separately preregistered. If >3, only then prereg complete V44-B A/B native full image; do not auto-promote.

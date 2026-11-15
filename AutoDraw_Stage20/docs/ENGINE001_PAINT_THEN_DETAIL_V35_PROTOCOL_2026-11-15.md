# ENGINE-001 / V35 — двухслойное рисование: заливка, затем штрихи поверх

**Дата 2026-11-15. Статус: USER-APPROVED EXPERIMENTAL ARCHITECTURE / PREREGISTERED / NOT_RUN.** Задача `ENGINE-001`. Инициатор пользователь: **«покраску отдельно, штрихи отдельно, штрихи класть по верх покраски»**; затем «фиксируй и продолжай». Принято как направление нового **исследовательского** V35, не как разрешение переключить production.

## Вопрос и гипотеза

Раздельный план `PAINT -> DETAIL` должен лучше сохранять узнаваемость лиц, волос, рук и границ одежды, чем бюджетная цветовая заливка V33/V34R без выделенной линии. Вторая гипотеза: выбор только значимых штрихов выгоднее по ограниченному бюджету, чем обводка каждой границы. Результат может быть отрицательным: контуры способны перезаполнить соседний цвет, исказить оттенки или превысить лимит.

**Обязательное правило:** слои разделены в плане и измерениях, но **выполняются последовательно на одной игровой доске**; финальный вид формируется от реального compositing игры. Не симулировать слои путём вставки RGB оригинала под штрихи. Финальные штрихи действительно следуют *после* последнего штриха заливки. Контур может иметь цвет из исходного локального участка, не обязан быть чёрным. Тонкие границы и внутренние черты маркировать отдельно от внешнего силуэта.

## Неизменный baseline

- Исходник `AutoDraw_Stage20/testImages/wV6VeZI9S1Y.png`: SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`; оригинал 200×320; ROI 150×240 при x155..304 на логической доске 460×240, backing 1380×720.
- Успешный native цветовой baseline: [V34R CI43740639321](https://github.com/Kiddos19882/AutoDraw/actions/runs/43740639321), commit `a209b409a417b5b4af12e2544c0e42866b27dcd4`, artifact `14171839402`, ZIP SHA256 `93b46223f5525b02def1631de8b49af4e1ddc0c799e5ec28224143d94fac0be2`. Original V33 width2 strokes1945; 3890 synthetic accepted vertices, 447 endpoints +0.25 x. Native control exact RGBA, 15/15 artifact file hashes PASS; V34R color-only RGB MAE 14.75660185 -> 14.08882407, warm MAE 34.87417968 -> 31.21305725. Color quality still FAIL (4/4 V33 classes below99%).
- Historical AniLines V14/[V25](ENGINE001_ANILINES_VISUAL_RECOGNIZABILITY_REVIEW_V25_2026-11-15.md), existing contour planners, `source/preparation` and `tests/game_renderer_reference.js` are candidate sources for **actual executable** detail trajectories. Prefer reuse to introducing alternative rendering engine.
- Resource: nominal quota6000 BoardItem2 points; 3890 accepted synthetic vertices **not exact CHALK**, and V29 old 4498 forecast is not V34R actual cost. Reserve capacity for detail while leaving safety margin unspecified until independently validated. Any proposed plan exceeding either experimental native probe cap3000 strokes / 5900 vertices or declared budget is rejected, not silently truncated.

## Separate, predeclared A/B/C

- **A / FILL_CONTROL:** frozen V34R B native actual width2 strokes, same order/colors/geometry. No new detail. Only this variant has measured historical native result.
- **B / FILL_ALL_CONTOURS:** identical paint stage followed by all admitted source-bound, independently extracted detail strokes in stable deterministic order. If full contours exceed resource cap, record `OVER_BUDGET` and mark B **NOT_EXECUTABLE**, never fake partial B as complete.
- **C / FILL_SALIENT_CONTOURS:** identical paint stage followed by only detail strokes ranked using a preregistered source-derived significance rule, protecting eyes/face, hair/hands and separating the two figures. Reserve detail budget **before** color planning in the next optimization stage; on this frozen A-first pilot, explicitly report residual capacity and do not claim quota-fit merely from endpoint counts. C may be smaller than B; don't modify score thresholds after visual review.

Detail must be mapped to source's logical ROI, correctly scaled, group/label/color ownership recorded, and have actual native accepted endpoints. Never assume that isolated zero-length or subpixel endpoints enter BoardPane without verifying in native replay. Mark uncertain geometry as rejected, not validated. All A/B/C use same source, palette colors for paint, gameplay renderer build, scale, background, same 3 logical px exterior quality gate and >=99% *per-required-color* coverage, unchanged source mask and alpha thresholds24/128. No posthoc threshold tuning.

## What to measure

Keep for each variant: separate paint-only native PNG/alpha, detail-only native PNG/alpha, **sequential composite actual Egret PNG**, native layer order; source and final color MAE, warm ROI MAE; silhouette coverage/precision; per-color correct coverage, foreign-color overpainting and 3 logical px exterior; face/hair/hand crops and user-inspectable side-by-side. Count detail strokes, synthetic endpoints, palette switches and forecast-only cost. Report signed improvements **and** regression relative to A.

Main exploratory selection: C is promising only if eyes/face/hand/hair visually clearer than A (record checklist with exact feature locations), native final RGB MAE not worse than A and no native exterior/foreign-color quality regression, with admissible resource count. A full pipeline PASS additionally requires >=99% native coverage each required color, <=3 logical px leakage, real gameplay E4, exact run-bound `CHALK=post.pointCount-pre.pointCount`, and E5 validation. V35 offline native E3 does **not** establish production acceptance.

## First engineering increment and validation

1. Reuse existing native renderer and contours; analyze paths/conversion and validate shape/owner before drafting new generator.
2. Add **minimal fail-closed layer-plan data model/validator only**: typed `paint` and `detail`, deterministic ordering `paint` then `detail`, source-linked RGB/stroke IDs, immutable baseline, positive widths, board positions, synthetic native probe caps. Unit-test order, mutation safety, invalid layers/counts/coordinates. This is E2 planning logic **not native brush acceptance**.
3. Only after verified V35 path conversion add opt-in Windows/Egret CI; independently render all selected variants with actual `BoardPane.redraw()` (no PIL/cv2/AABB as quality evidence). Freeze raw PNG/JSON/candidate exclusion reasons/hashes before grading.
4. No Stage6/executor default changes, no master changes, no live claims without E4 captures. Negative and aborted variants kept as artifacts.

**Baseline result note:** V34R completed E3 PASS as color-fidelity diagnostic only; V35 remains NOT_RUN until distinct native experiment. User proposal is accepted as research architecture, not as evidence that outline-after-fill already improves images.


## Pre-run native V35 pilot addendum — frozen before V35 native CI (2026-11-15)

**Native experiment ID: `ENGINE001_PAINT_THEN_DETAIL_V35_NATIVE_PILOT_1`.** This is a fully specified subset of the V35 architecture, not a rewrite of A/B/C after observing their results.

Frozen detail paths are V18-B from [CI43677851946](https://github.com/Kiddos19882/AutoDraw/actions/runs/43677851946), artifact14147096853 `engine001-v18-anilines-junction-ab`, ZIP SHA256 `cb53599baf9fcc763f76669be41b93a875a6d931f6b778d2631a648db4c2adc5`, `B-paths.json` SHA256 `752dbc5ff55e90b0d38f492fadfde9be8811b70ebc66bce4999f716c4a86ed57`. Frozen native fill from V34R `V34-B-strokes.json`, native artifact14171839402, ZIP SHA256 `93b46223f5525b02def1631de8b49af4e1ddc0c799e5ec28224143d94fac0be2`; validate source/path data and all archive manifest hashes before use.

**Adapter pinned:** for V18-B each `logical_points` maps unchanged to native `points` in the identical 460×240 logical board. V18 `brush_width_parameter=1` becomes actual native `width=1`, original V18 `color_rgb=[49,38,43]` becomes native packed RGB 0x31262B; assign diagnostic `colorIndex=100` **only as a dedicated detail layer identity**, never as an actual source palette owner; retain V18 route ID in metadata and produce unique `strokeId=detail-<original-id>`. Explicitly reject any source drift, unexpected nonpositive/duplicated coordinates, unsupported widths, outside-board point or changes to paint geometry. Real BoardPane acceptance must be checked, particularly closely spaced vertices and zero-length segments. No transfer from Cv2/PIL footprint.

**A** = frozen V34R color-fill B only (1945 strokes / 3890 synthetic vertices), unchanged. **B** = A + *all* frozen V18-B 410 paths / 1792 vertices, thus **2355 strokes / 5682 synthetic vertices** (<=3000/5900 native probe caps), details drawn strictly after all fill strokes. **C** = A + deterministically selected V18-B paths with **any** logical vertex at `y < 125` (upper face/hair/arms region), **or** Euclidean polyline length `>=15 logical px` (long salient structural curves elsewhere). No subjective hand-selected paths, no parameter tuning after results. On current frozen V18-B this selects **297 detail routes / 1379 vertices**, total **2242 strokes / 5269 synthetic vertices**. The C heuristic is exploratory; it is **not a semantic eye/hand detector**. B and C original V18 paths and C membership list must be archived.

**Protocol measurements:** native Egret actual WebGL sequential composite A/B/C, plus native separate per-layer alpha controls; two visual comparisons (whole ROI and top125 face crop) with no source texture pasted under outlines. Record source-original full RGB MAE and warm HSV mask MAE; log any improvement **and** worsening. Require A PNG pixels reproduce archived V34R B exactly on same source-bound renderer, or mark BLOCKED. Assert C is strict subset of B and all fill routes/positions/colors unchanged. Native stroke count/points are not exact CHALK. Note V18-B path vertices can be skipped by game `pushPoint` if too close: report accepted actual Egret vertices/scene stats; reject an unreported mismatch. No adaptive brush widths in this pilot: width2 fill, width1 detail, both actual Egret. All existing quality/leakage/CHALK gates remain unchanged; pilot is exploratory E3, no production claim.

**Decision:** favor C only if native visual detail increases without larger RGB error, cross-color bleed, ROI leakage or resource overrun. Neither C nor B quality can be accepted from a static composite mock; native evidence first.

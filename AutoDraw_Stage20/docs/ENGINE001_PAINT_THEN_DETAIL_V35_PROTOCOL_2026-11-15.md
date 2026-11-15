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

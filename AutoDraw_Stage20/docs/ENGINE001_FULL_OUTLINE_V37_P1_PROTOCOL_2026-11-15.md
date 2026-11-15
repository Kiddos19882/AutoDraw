# ENGINE-001 / V37-P1 — исходные цвета линий при полной обводке V35-B

**Дата:** 2026-11-15. **Статус:** PREREGISTERED / NOT_RUN, до первого native V37-P1 CI. **Задача:** ENGINE-001. **Решение пользователя:** «v35b лучше всего получилась обводка». Это предпочитаемая визуальная геометрия, НЕ автоматический RGB- или production-PASS.

## Цель и границы

Первый, изолированный подэтап V37 проверяет, можно ли сократить цветовой ущерб от **полной обводки V35-B**, не удаляя ни один из предпочитаемых пользователем 410 штрихов. **Меняется только RGB контурных линий; цветовая заливка и её геометрия не изменяются.** Восстановление недостающих насыщенных оранжевых/жёлтых областей остаётся следующим отдельным экспериментом V37-P2 и не смешивается с этим A/B/C.

Baseline — [V35 pilot2 CI43742747278](https://github.com/Kiddos19882/AutoDraw/actions/runs/43742747278), SHA `a183b53e366a2f6e50867bf3124f9420c58928e0`, immutable artifact `14173635779`, ZIP SHA256 `350892e45a1941072e0dc3b590d348ea817d0ee8f7daf004915e683a3368f170`, 23/23 report-linked hashes verified in source archive. Frozen exact source PNG SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`, original200×320, logical board460×240, ROI x155..304 / y0..239, native1380×720 / scale3. V35-B: **1945 width2 fill then 410 width1 V18-B detail**, 2355 strokes, 5682 synthetic accepted vertices (**NOT** game CHALK). Source RGB MAE20.21118519 / warm source HSV MAE37.89431998. Original V34R fill-only source RGB MAE14.08882407/warm31.21305725 is secondary context, not substitution for full-outline A. V36 source-median algorithm on *297* selected contours is a proof-of-concept only; V37-P1 transfers the predetermined RGB transformation to **all 410** and tests anew, never assumes its result.

## Predeclared candidates, single variable

- **A: exact V35-B** all 410 dark [49,38,43] contours over untouched V34R fill. Frozen original B native PNG `B/V35-B-composite.png` must match current control **RGBA pixel-for-pixel**, and `IHDR` / `IDAT` exactly as in existing V34R/V36 comparator; ancillary PNG metadata allowed to differ and reported. If control differs: BLOCKED.
- **B: per-stroke source RGB.** For all 410 original V18-B contours use existing deterministic `run_engine001_source_color_contour_native_v36.medians_for_path`: 150×240 original LANCZOS ROI at logical x155..304/y0..239; sample each accepted vertex using Python round+clamp, select **lower per-channel median**; one packed RGB per contour.
- **C: midpoint contour RGB.** Same per-stroke source median as B, with each RGB channel `(dark + original_median + 1)//2` (half-up). No posthoc tuning coefficient.

A/B/C retain identical 1945+410 strokes, 5682 accepted synthetic vertices, geometry, stroke IDs, width (2 fill, 1 detail), layer order, original palette fill RGB and 447 frozen V33 quarter-pixel endpoint shims. **Never** replace user-selected 410 contours with V35-C/V36 297 contour subset. Existing V36 `renderV36SourceColoredContourProbe` invokes actual archived BoardPane/Egret WebGL. Controls must reject if source, per-route count/IDs/points, SHA or native A replay differ; native A/B/C composite and detail alpha must match *all pixels*. Source sampling is for color proposals only and not a proxy brush footprint.

## Evidence, metrics, criteria

Save raw native PNG of all isolated classes and composite, full/facial crop comparison against **original actual source**, proposed RGB by contour with IDs, unchanged plan JSON, source/artifact hashes and report. At alpha>=24 and >=128 report native composite silhouette, source ROI foreign-color overlap, and exterior leakage >3 logical px from source foreground. Record source RGB MAE full 150×240 and warm HSV (H5..55°,S>=0.30,V>=0.20), total used line RGBs/color switches, line detail visibility (eyes/face, hair, fingers, garment boundaries), and synthetic counts. Compare B/C to V35-B A; separate cost and visual results.

Color candidate passes *diagnostic* only when both original-source full RGB MAE and warm-region MAE **strictly lower** than A, alpha unchanged and no geometry/resource increase. **Visual decision**: independent of RGB alone, compare same-scale face/hand/hair crops to user's V35-B outline; if faint lines lose preferred features, label **VISUAL_REGRESSION** even if MAE improves. No numeric metric can overrule the user preference for full 410 contour topology. Full acceptance still requires >=99% each required color, <=3 logical px exterior, bound game CHALK (`post.pointCount-pre.pointCount`) with quota safety and E4/E5 when applicable. No adaptation of thresholds to results, no Stage6, executor, Bridge, Monitor, production or master modifications.

**Decision after V37-P1:** only if B/C preserves preferred full native line geometry and passes explicit visual review should V37-P2 tackle additional source color-region fill; if both wash out contrast, next separately prereg variant with edge-aware dark-color preservation, not covert tuning of this run.


## Post-run native evidence — 2026-11-15

**[CI43745869245](https://github.com/Kiddos19882/AutoDraw/actions/runs/43745869245) E3 SUCCESS** at SHA `5b67a056ec47634ab7bcf0ba0ee1e8f4a21fcbfd`, Windows actual archived BoardPane/Egret WebGL. Artifact **14174860868**, ZIP SHA256 **`1e1361b43cb65a7dd808ef3d8cece984947d1ff7bbc96d664d2fac2f9fcef3a5`**, independently opened, 24/24 report-linked file SHA256 PASS. Frozen V35-B **control A RGBA exactly equal**, all A/B/C native alpha RGBA masks identical at every pixel for composite and all five isolates. All **410 full user-selected V35-B contours** after unchanged1945 width2 fill strokes preserved; totals2355 strokes/5682 synthetic accepted vertices, **NOT game CHALK**.

| Actual native variant | Original-source ROI RGB MAE | Warm source HSV MAE (2946 px) | Alpha≥24 composite pixels | Distinct contour RGB / detail color switches |
|---|---:|---:|---:|---:|
| A frozen V35-B 410 dark contours | 20.211185185 | 37.894319982 | 161544 | 1 / 0 |
| B source lower-median colors on all410 lines | **11.976037037** | **27.063589047** | 161544 | 395 / 407 |
| C 50% source / 50% dark half-up | 14.860574074 | 29.723127404 | 161544 | 389 / 407 |

**Preregistered color diagnostic:** B and C both `PASS` on source RGB + warm RGB MAE strictly less than frozen A, and identical native alpha. B best numeric. Single-image, unblinded visual inspection of the real native full and upper-face crops: A has highest dark-line contrast; B washes out blonde hair, facial outline, some expression details; C retains legible hair/face/garment detail more than B while reducing dark-overdraw substantially relative to A. This subjective judgement is **NOT** independent E5 and does not override user's explicit V35-B preference, which remains the appearance reference. In particular, **numeric MAE alone cannot choose production defaults**.

**Native scope constraints:** full A/B/C have identical source-silhouette alpha topology and unchanged color-fill geometry, but alpha equality alone does not prove actual per-color correct coverage when foreground detail RGB differs. No verified >=99% per-color gate; game run-bound `CHALK=post.pointCount-pre.pointCount`, independent E5 and live E4 all NOT_RUN. Experimental native budget 5682 is under internal 5900 cap, but **not certified safe under 6000 actual game point budget**. Full production quality remains BLOCKED.

**Decision:** Confirm source-dependent RGB line assignment can reduce objective color error without discarding any full V35-B lines. Keep frozen A as visual reference, B as color-fidelity candidate, C as candidate for human visual comparison. No changes to V35-B artifacts, original source or acceptance thresholds. **Next independent V37-P2 preregistration:** preserve complete410 contour geometry and compare source-region color restoration specifically for warm/orange costume and hair with actual native painter, considering additional stroke capacity; no assumption that further fills will fit game quota or improve recognizability. Only do runtime E4 after separate resource/safety analysis.

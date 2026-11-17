# ENGINE-001 / PAL32-REGION-V1 — сравнение игровых цветов и топологии областей

**Дата:** 2026-11-17. **Исследование E1 → E2; production и Egret не изменяются.** Рабочая ветка `feature/image-geometry-optimization`. Это исследование **перед** B3c, не замена замороженной V44-B и не изменение критериев V43-P4.

## Контекст и исходные данные

- Source (ф) `testImages/wV6VeZI9S1Y.png`, frozen SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`. Экспериментальная ROI150×240 LANCZOS (source image200×320), точный размер в report.
- Предопределённая игровая палитра — **все 32** исходных реальных RGB из (ф) `data/palettes/browser_palette.json`, Git blob `461b5f3725b9b79888ad36e807b3cf4c9e445e98`. Используем только подмножество цветов, фактически выбранное по изображению; искусственных RGB не создавать, координаты/живую калибровку цветов до применения в игре отдельно проверять.
- Архив source zone outlines [CI43995008472](https://github.com/Kiddos19882/AutoDraw/actions/runs/43995008472):1838 native Egret контуров только owners4–7 при старой MEDIANCUT8. Это не число **всех** связных цветных компонент будущей палитры (для честного сравнения используем 4-связные компоненты всех классов).
- Неизменные 410 native цветных деталей V44-B — visual reference, не часть офлайновой покраски. При создании preview из готового Egret contour PNG смешивание слоёв выполняется Pillow; **заполнение не нарисовано Egret**.
- Ретроспективная пилотная проверка до написания настоящего V1 CI: coarse SLIC теряет важные детали; SLIC parameter sweep и tiny-component merge для B уже выполнялись локально, поэтому указанные параметры являются **постпилотным фиксированным baseline для первого воспроизводимого GitHub E2**, а не доэкспериментальным слепым выбором. Отрицательные пилотные результаты сохранить.

## Фиксированные варианты первого E2

| ID | Метод | Настройки | Назначение |
|---|---|---|---|
| A | исходная палитра MEDIANCUT8 | Pillow `MEDIANCUT` 8 / `dither=NONE` | историческая модель, цвета не ограничены игровыми32 |
| B | nearest32 | CIELAB D65 и CIEDE2000; стабильный tie-break меньший palette index; без dithering | эталон 32 игровых цветов |
| C | SLIC coarse32 | `n_segments=260, compactness=12.0, sigma=0.7`; mean Lab per superpixel → nearest32 CIEDE2000 | возможность глобально убрать островки, риск потери деталей |
| D | C + merging | максимум8 итераций, мелкие connected components <42 пикселей, closest Lab / neighboring color | риск повторного упрощения (в пилоте не дал эффекта) |
| E | B + constrained tiny region merge | 4-connected owner regions, `area<=8`, два прохода, соседний уже существующий игровой цвет, mean extra ΔE00<=5, tie-break по большей длине общей границы и palette index | альтернативное сбережение деталей без SLIC |
| F | SLIC finer32 sensitivity | `n_segments=1600, compactness=8.0, sigma=0.3` | проверить, возможно ли восстановить контуры тонкими суперпикселями |

**Никаких изменений порогов после просмотра CI.** E, F — дополнительные варианты к первоначальным A–D. Все запуски без dithering. До реальной приёмки палитры не менять `palette_quantization.py`, `palette_reduction.py`, `browser_palette.json`, Stage6, executor, Monitor, Bridge, original V44-B 410 contour и frozen планы B0/B1/B2/B3.

## Результаты, которые нужно архивировать

Для каждого варианта сохранять PNG fill proxy, PNG boundaries, `index_map` как lossless npz/PNG при разрешённых индексах, mapping-used game swatches и SHA256. Report: source/palette blob/SHA, versions, фиксированные параметры и seed/отсутствие randomness; ΔE00 mean/p95/max по всей150×240 ROI, RGB MAE, число используемых игровых цветов, **все** 4-связные компоненты и количество мелких (<8/<16/<32), topology change vs B, boundary distance, распределение метрик foreground/background отдельно и визуальное сравнение лица/волос/одежды. Для предварительного визуального сравнения поверх base PNG разрешено положить замороженный native Egret V44-B `color-100` слой с маркировкой `offline fill + true Egret contour overlay`. Нельзя называть такой composite native Egret fill.

Acceptance: пока **не назначать победителя автоматически только по ΔE00 или числу компонент**. Первый GitHub E2 должен подтвердить точный input/palette, deterministic repeatability, 32-swatch-only для B/C/D/E/F, source SHA, отсутствие dithering, сохранение всех четырёх вариантов плюс отрицательных результатов, дефект важных границ и практический бюджет будущих путей. Малые зоны не удалять ценой распознаваемости глаз/лиц/рук и сохранения белого фона. E3 реальные кисти Egret и E4 game/CHALK/ E5 **NOT_RUN** до отдельной проверки. Описанные цифры пилота E1 не равны GitHub E2.

## PAL32-REGION-V1: actual GitHub E2 after local pilot, 2026-11-17

[Completed source-only CI43997979526](https://github.com/Kiddos19882/AutoDraw/actions/runs/43997979526) at commit `b3ee8c8d15e402ce5e3127d7f74a3f9cf7ac124b`, **SUCCESS**, all mandatory steps incl upload, 4/4 regressions PASS. Artifact14290961591 `engine001-pal32-region-v1-six-variants-source-only`, 21 ZIP members; original `report.json` SHA256 `ff8b38526b5ff18c9300a519e353087a2ff96463ea14d6b3cadd62b08d373b83`, 20/20 report-linked PNG hashes and ZIP CRC/integrity PASS, source/palette frozen verified. Both variants A/B/C/D and additional E/F are archived together. Comparability warning: these are **all-color 4-connected source pixel components**, not only earlier1838 real Egret boundary contours on owners4–7.

| Variant | Colors used | All 4-connected comps | mean ΔE00 |
|---|---:|---:|---:|
| A adaptive MEDIANCUT8 (NOT 32-restricted) |8|5879|3.70356|
| B direct nearest game32 CIEDE2000 |20|2369|5.44375|
| C coarse SLIC260 + game32 |9|28|8.09811|
| D C + tiny region merge |9|28|8.09811|
| E direct game32 + tiny-owner merge area<=8 / mean extra ΔE00<=5 / 2 passes |15|1044|5.55870|
| F finer SLIC1600 + game32 |10|76|7.48370|

**Pilot/source E2 conclusion:** C/D collapse details, even F severely simplifies the characters. E cuts B's 4-connected components by **55.93%** while increasing mean ΔE00 only **+0.11495**; 1653/36000 source ROI pixels (4.5917%) change labels. A **posthoc E1** edge-agreement check using the *same gradient/top-decile criterion* as [COLOR32-S1](ENGINE001_COLOR32_SPATIAL_SEGMENTATION_PROTOCOL_2026-11-17.md) found B **86.1667%** vs E **84.4167%**; this is a measurable loss of **1.75 percentage points** of strong-source-edge overlap. This is NOT in the frozen PAL32 CI JSON and must remain explicitly E1 supplementary until separately reproduced by E2; it is not a quality PASS. E visually looks closer to B than SLIC with the existing 410 V44-B contours overlaid, but source model+Pillow preview **does not equal Egret-painted fill or gameplay**. No A/B output path changed, no source/game palette/palette_quantization/prod/Stage6/master edits; E3 genuine Egret fill, E4, E5 and run-bound game CHALK NOT_RUN. Next goal is protecting important contour/face/hand/eye regions while reducing source class fragmentation and testing actual fill-route geometry, *not* promoting E automatically. Avoid duplicating the already closed original [COLOR32-S1](ENGINE001_COLOR32_SPATIAL_SEGMENTATION_PROTOCOL_2026-11-17.md) research: PAL32 E/F are supplementary sensitivity/regularization evidence.


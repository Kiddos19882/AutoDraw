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

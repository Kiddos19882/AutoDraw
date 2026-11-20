# ENGINE-001 / BPRED-S1 — source-derived геометрия кисти Egret: native результат

**2026-11-20. BPRED-S1 геометрия single two-point stroke: E2 PASS, E3 native calibration PASS, H1/H2 PASS.** **НЕ** подтверждена полная physical alpha/RGBA модель, boundary safety/owner/color/full image или E4/E5. [Замороженный до новых сцен S1 E0](ENGINE001_BPRED001_S1_SOURCE_GEOMETRY_NATIVE_PREREG_2026-11-20.md), [главный план](ENGINE001_BPRED001_BRUSH_PREDICTION_PLAN_2026-11-20.md), [DEC-041](DECISIONS.md).

## 1. Evidence / version / источник

- Ветка `feature/image-geometry-optimization`, код и native test SHA **`f38f2dbfe8dcb45ea57cdcc7cba2302a848286c1`**. S1 E0 prereg зафиксирован **ранее** на commit `606e3f8eff9ae843bb73158c1775234f3eede211` (родитель S1 implementation SHA); source S0 artifact [14586574667](https://github.com/Kiddos19882/AutoDraw/actions/runs/44644039555/artifacts/14586574667) validated on run44644039555 SHA5b6ed18a.
- **[Реальный Egret CI44646682797](https://github.com/Kiddos19882/AutoDraw/actions/runs/44646682797)** на SHA `f38f2dbfe8dcb45ea57cdcc7cba2302a848286c1`: единственная обязательная job `geometry-calibration-only` **SUCCESS**. Firefox **159.0**, original game engine Egret5.4.1 blob `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`, renderer blob `76d950e0a8911888a9df3b675b866519ecf7bba4`, parent P4D3/P4D14/S0 blobs matched. Native blank alpha0, Canvas/WebGL path genuine, no surrogate Pillow/OpenCV scene.
- Исходные frozen S0 будущие планы: `BPRED001_CORPUS_V1`. Native исследовал **строго** 120 `CALIBRATION` сцен, angles7,73,166°, widths1..10, lengths7/19, независимые X/Y phases (1/16,3/16) и (5/16,7/16); **3 пространственных копии =360 alpha-weighted centroid observations**. Ни одна из **120 BLIND** сцен или десяти BLIND replay-control не была отрисована/оценена; они остаются будущей независимой проверкой S4.
- Исходный S0 stroke ID `bpred-0..2` несовместим с regex реального native test API. Тонкий opt-in S1 adapter менял **только** `strokeId`→`icon-0..2`, не координаты, не width, не цвета, не порядок. Сохранены raw source `_PLAN.json`, runtime `_RUNTIME_PLAN.json`, оба SHA, native `_REAL_EGRET.png` + metadata, source artifact SHA, каждый rendered sample row. На нативной доске scale3 =1380×720 physical, no crossing native ROI.
- **[Сохранённый архив14589516497](https://github.com/Kiddos19882/AutoDraw/actions/runs/44646682797/artifacts/14589516497)** `engine001-bpred-s1-real-egret-geometry-calibration-120`, size **635,794 bytes**, `expired=false` при проверке, 120 real scenes+blank, append-only `CASE_ROWS_APPEND_ONLY.jsonl`, `S0_INPUT_PROVENANCE.json`, итоговый `report.json`, SHA256 manifest **363/363** подтверждён независимым шагом CI. Все новые данные E3 конкретно на SHA `f38f2dbfe8dcb45ea57cdcc7cba2302a848286c1`, а не игровой live runtime.

## 2. Зафиксированные гипотезы и фактические значения

| Гипотеза/метрика | Prereg gate | Измеренное native E3 | Вердикт |
|---|---|---|---|
| H1: widths1,3, M1 midpoint +(.5,.5) | mean M1 ≤50% M0 и mean M1≤0.20 logical | **M0 0.7197485571** → **M1 0.0320447431** logical, уменьшение **~95.55%** на72 observations | **PASS** |
| H2: other widths2,4,5,6,7,8,9,10 не меняют центр | M0=M1 для всех 288 observations | `other_width_predictions_exactly_same=true` | **PASS** |
| 120 primary native calibration + blank | 121 сцен,360 валидных centroid, exact source/FF pins | 120/120+blank; 360 observations, source hashes PASS | **PASS technical** |
| M1 идеальная capsule bbox, alpha24 outside count (только диагностика) | Всегда измерять; НЕ модельный native-quality gate | **0** физических alpha≥24 пикселей за прогнозируемым model-only bbox на этой calibration | **0 observed**, не универсальный PASS |

Ошибка центра вычислялась существующей `p4d14.native_alpha_centroid` как alpha-weighted physical pixel center и `p4d14.euclidean`, в logical единицах, без подбора фазы или порогов после результата. M0 = plain midpoint; M1 = midpoint +(.5,.5) **только widths1/3**, исходная логика Egret CanvasRenderer. M1 — source-derived location/bbox, а **не точная Canvas2D rasterizer**. Bbox alpha1/alpha24 в каждом raw row сохранены раздельно; aggregate alpha1 находится в `report.json`. Статус S2 полного physical alpha0..255 — **NOT_RUN**.

H1 mean рассчитан на **72 коррелированных наблюдениях** в 24 scene families двух widths, не на 72 независимых экспериментах; calibration не является blind test. Величина улучшения подтверждена только для этого source/browser/backing/набора углов/фаз.

## 3. Реализованные исследовательские файлы и E2/CI

- (ф) [run_engine001_bpred_s1_native_geometry.py](../tests/run_engine001_bpred_s1_native_geometry.py) — pinned source S0, sample ID adapter, повторное использование native `p4d3.read_scene`, `p4d14.model_center/native_alpha_centroid`, физический ideal capsule AABB diagnostic, H1/H2 score, append-only raw JSON/PNG/SHA; fail-closed unknown inputs/clip/source mismatch.
- (ф) [test_engine001_bpred_s1_native_geometry.py](../tests/test_engine001_bpred_s1_native_geometry.py): **12/12** synthetic E2 PASS (split gating, source unchanged, IDs adapter, coordinate shift, bbox diagnostics, scientific FAIL distinction, no overwrite). **10/10** прежних P4D14 contract tests PASS. Markdown audit PASS с историческим P4D7 link warning, который не является новой ошибкой.
- (ф) [engine001-bpred-s1-native-geometry.yml](../../.github/workflows/engine001-bpred-s1-native-geometry.yml): Windows pinned Firefox159, original renderer SHA restoration, frozen [S0](ENGINE001_BPRED001_S0_CORPUS_MATERIALIZATION_RESULTS_2026-11-20.md) artifact, 120 calibration native and raw SHA manifest, required artifact uploader. Никаких замен frozen P4D3/P4D14, game renderer или production.

## 4. Ограничения и действие дальше

**S1 DONE только как проверенная source-faithful single-stroke location & ideal bbox geometry для новой calibration**. Обнаруженная проверяемая поправка уменьшает ошибку положения центра, но **не доказывает**, что на каждом физическом пикселе alpha/RGB правильно предсказаны, что owner/white leakage безопасны, что планировщик работает или что качество изображения E/F улучшилось. Нулевой bbox-alpha24 false-negative в этой выборке не заменяет future S2 uncertainty или protected gates. S0 BLIND сохраняется для stage S4, не использовать его для M1 настройки.

**E4 live game, E5 independent model/generalization, exact run-bound CHALK = NOT_RUN**. Старый P4D18 original-white/protected leakage **FAIL** и P4D19 DEFERRED остаются. Production defaults, Stage6, Bridge/Monitor, `master`, source original image, renderer/engine blobs не менялись.

**Первый следующий шаг: BPRED-S2**, отдельный E0 до реализации физического alpha/AA predictor M0/M1/M2 с порогами и отдельными native checks на том же `CALIBRATION` корпусе; затем source-over цвет и независимый BLIND только на более позднем stage S4 после фиксации модели. Никакого нового «repair holes» направления.

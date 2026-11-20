# ENGINE-001 / BPRED-S2v1 — физическая альфа на настоящих Egret PNG

**2026-11-20. S2v1: E2 PASS, исходный native E3 доказан, offline/reanalysis CI PASS; H1/H2/H3 PASS, pixel-safe FAIL.** [Исходный frozen E0](ENGINE001_BPRED001_S2_PHYSICAL_ALPHA_AA_CALIBRATION_PREREG_2026-11-20.md) зафиксирован на SHA `4fb6e6fedcfc7631e695f290edcd3c5e11f0efe8` **до** расчёта. Исследовательский финальный код/workflow SHA `4d2c7991e8472ed41ee64632658c55c9cd43287b`; [CI44651134628](https://github.com/Kiddos19882/AutoDraw/actions/runs/44651134628) SUCCESS; [архив результатов14589809874](https://github.com/Kiddos19882/AutoDraw/actions/runs/44651134628/artifacts/14589809874) 41 334 bytes, `expired=false`, `report.json` +120 полный `CASE_ROWS_APPEND_ONLY.jsonl`+12 worst rows, каждый SHA verified в CI. Источник фактической альфы: неизменённые 120 Egret/Firefox159.0 PNG из [S1 E3 CI44646682797](https://github.com/Kiddos19882/AutoDraw/actions/runs/44646682797), SHA `f38f2dbfe8dcb45ea57cdcc7cba2302a848286c1`, 363/363 member SHA verified. **Ни одна новая native-сцена не создавалась.**

## 1. Первичные сравнительные метрики — неизменённые параметры

На 120 CALIBRATION scenes ×3 locations=360 ROI (162×162 physical), агрегирование **macro по 120 case families**. Порог alpha≥24 определён заранее, alphaMAE в объединении ненулевых.

| Модель | macro IoU alpha24 | macro IoU alpha1 | mean MAE union | FP alpha24 | FN alpha24 |
|---|---:|---:|---:|---:|---:|
| M0: naive binary | 0.863596684 | 0.849604397 | 29.50803420 | 3499 | 21193 |
| M1: Egret width1/3 shift binary | 0.920955990 | 0.897279136 | 12.24762901 | **0** | **17739** |
| M2: area8 shifted subpixel | **0.989298613** | **0.988022898** | **2.47050900** | **2167** | **559** |

**Предрегистрированные H1, H2, H3 = PASS**, исходные numerical gates в [E0](ENGINE001_BPRED001_S2_PHYSICAL_ALPHA_AA_CALIBRATION_PREREG_2026-11-20.md) не менялись. Pixel safety **FAIL**: M2 2167 FP (предсказано «закрашено», real alpha менее24) и559 FN. M1 без FP **только на этой CALIBRATION**, но пропускает много покрытия; никакой из них не даёт native гарантии для новых положений. Foreground owners, original-white и RGB source-over **не** измерялись.

**M2 по ширине, macro IoU alpha24:** w1 .98033; w2 .98184; w3 .98952; w4 .98974; w5 .99085; w6 .98921; w7 .98883; w8 .99366; w9 .99348; w10 .99553. Худшая family `BPRED-W02-A166-L07-PX05-PY07`: IoU .961887. Точное primary raw и метрики каждой фазы/позиции в исходном архиве.

## 2. Отрицательные технические запуски без исправления научных порогов

- [CI44650045193](https://github.com/Kiddos19882/AutoDraw/actions/runs/44650045193) SHA `62021d81`: 11/12 synthetic E2 PASS, один тест некорректно создавал только угол7 вместо 7/73/166; до загрузки PNG **FAIL technical**.
- [CI44650226187](https://github.com/Kiddos19882/AutoDraw/actions/runs/44650226187) SHA `985abcad`: E2 PASS, source retrieved, **BLOCKED** до расчёта из-за требования несуществующей строки experiment ID внутри frozen E0. Исправлена только проверка exact E0 Git blob, не сам E0.
- [CI44650479079](https://github.com/Kiddos19882/AutoDraw/actions/runs/44650479079) SHA `2db042ff`: E2 PASS, 20 native PNG обработаны, затем P4D16 исследовательский API отклонил width4 (оригинальные permitted widths1/2/3/5/10). Добавлен test-only opt-in адаптер к тому же P4D16 без переписывания исходной математической формулы; 2 новых E2 теста проверили для старых widths byte-exact и восстановление исходного gate.
- [CI44650857741](https://github.com/Kiddos19882/AutoDraw/actions/runs/44650857741) SHA `2207cee8`: E2 PASS, **все** 120 case и H1/H2/H3 PASS; заключительный audit FAIL из-за лексикографической сортировки `1,10,2` вместо numeric. Артефакт промежуточных данных сохранён [14590212659](https://github.com/Kiddos19882/AutoDraw/actions/runs/44650857741/artifacts/14590212659).
- **FINAL [CI44651134628](https://github.com/Kiddos19882/AutoDraw/actions/runs/44651134628)** SHA `4d2c7991e8472ed41ee64632658c55c9cd43287b`: 14/14 новых E2 + 10/10 исходных P4D16 regression PASS, native parent 363 member SHA, H1/H2/H3 PASS, full audit and results artifact **PASS**. Это CI анализ **раньше полученных** native pixels, не 120 новых rendering.

## 3. Вывод и дальнейшее действие по плану

Технически доступна рабочая математическая модель **alpha0..255** по двум точкам, без RGB. **M2=MODEL_ONLY**, так как 2167 FP/559 FN alpha24 остаются. Сохранена непротиворечивая возможность использовать M1 как внутреннюю консервативную подсказку (FP0 **только на calibration**, FN17739); обе не прошли независимую validation. Рабочий production/executor, CHALK estimator, Stage6, Bridge, game engine/renderer, master не менялись. P4D18 protected quality FAIL и P4D19 DEFERRED остаются, E4/E5 exact run-bound CHALK NOT_RUN. S0 BLIND120 и10 blind replays **не тронуты**.

**NEXT внутри S2:** отдельный frozen [S2v2 E0](ENGINE001_BPRED001_S2V2_ISOTONIC_ALPHA_RESIDUAL_PREREG_2026-11-20.md), обучить/проверить математическую изотоническую коррекцию alpha только на calibration с leave-one-angle-out; никаких S3/S4/production и никаких подгонок по blind.

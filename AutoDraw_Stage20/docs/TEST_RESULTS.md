# AutoDraw — реестр проверенных результатов

**Проверено по документации:** 2026-11-08 · **Evidence baseline HEAD:** `a2d1f0a52d47`. Это **навигационный реестр**, а не замена первичных experiment manifests, Game Monitor reports, PNG или CI artifacts. Все прежние детальные записи реестра сохранены в [TEST_RESULTS_HISTORY_THROUGH_2026-11-08.md](TEST_RESULTS_HISTORY_THROUGH_2026-11-08.md).

> **Обязательная формула:** exact `CHALK = pointCount_after - pointCount_before`, только при валидной привязке к конкретному запуску. Длина, количество strokes, площадь, pixel coverage, move calls и estimates — отдельные величины.

## 1. Реальные измерения CHALK

| Исследование | Принятые live captures / метрика | Результат и ограничения | Первоисточник |
|---|---|---|---|
| G1 (длина / направление) | 12/12 | Точные pre/post CHALK, короткие и длинные линии; только тестовые условия | [G1](CHALK_GEOMETRY_MATRIX_G1_RESULTS.md) |
| G2 (повороты / контуры / перекрытия) | 18/18 | Влияние геометрии, не универсальный fill predictor | [G2](CHALK_GEOMETRY_MATRIX_G2_RESULTS.md) |
| G3 (sampling step/delay) | 27/27 | Шаг меняет расход CHALK, задержка тоже может влиять; параметры изучены на фиксированной геометрии | [G3](CHALK_G3_RESULTS_2026-11-02.md) |
| Матрица радиусов | 21/21 | Шесть длинных линий: CHALK 722–728 при radius 1–30; нет установленного прямого radius multiplier | [Radius matrix](CHALK_RADIUS_MATRIX_RESULTS.md) |
| Исходные V1–V5 | 45/45 | Точные live captures; исходная матрица сохраняется независимо от исправленной | [V1–V5](CHALK_INT006_V1_V5_RESULTS_2026-11-02.md) |
| Исправленные V1–V5 | +45/45 | Step=2→4: снижение CHALK **38.5–49.4%** по пяти геометриям; visual/pixel checks отдельно | [Follow-up](CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md), [pixel audit](CHALK_INT006_PIXEL_AUDIT_2026-11-02.md) |
| INT-006 D1–D5 | 45/45 (пять планов × 3 профиля × 3 повтора) | Official analyzer **PASS**; MAE 1.408, MAPE 2.134%; P1 MAE 0.657 CHALK. P1 vs P0: расход 1010 vs 1884 CHALK в матрице. **Safety margin/production не утверждены** | [Официальный отчёт](CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md), [frozen model](CHALK_INT006_FROZEN_PREDICTIONS_AND_ANALYZER_2026-11-02.md) |
| INT006R | 45/45 D1–D5 × radius 1/10/30 × 3 | Суммарно CHALK **1011 / 1015 / 1017**. Важнее визуальные ограничения radius1/D2 и radius30/D4 | [Live report](CHALK_INT006R_LIVE_RESULTS_2026-11-03.md), [visual review](CHALK_INT006R_VISUAL_AUDIT_2026-11-03.md) |
| FILL-001 preflight до quota | 131 strokes completed; точный session-level quota 5999 | Это **не принятый FILL-001 quality/capture**, budget исчерпан; исторический негативный опыт | [Postmortem](CHALK_FILL001_PREFLIGHT_POSTMORTEM_2026-11-04.md) |
| FILL-001-RS сохранённый live run | 27/27; exact CHALK **1260** | Runtime binding PASS, **PNG gate FAIL:** coverage 98.430600% при target ≥99%, leakage 11 px при 0 | [Replay и raw evidence](CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md) |

**Интерпретация:** multiple runs/repeats не равны независимым DrawingPlan. Нельзя объявлять `95%` predictive coverage INT-006 по 45 captures, построенным из 5 геометрий.

## 2. Renderer / качество / автоматические проверки

| Направление | Подтверждено | Чего не доказывает | Источник |
|---|---|---|---|
| Paired renderer PRR | 6/6 `PASS_PER_RUN`, aggregate PASS в [CI 42321009715](https://github.com/Kiddos19882/AutoDraw/actions/runs/42321009715) | Pixel parity всех рисунков/конфигураций | [Game engine analysis](CHALK_GAME_ENGINE_POINT_COST_AND_BRUSH_WIDTH_2026-11-03.md) |
| FILL-001-RS static sweep | 2238 offline candidates, 62 passed simulation gate | Реальный CHALK или quality gate в игре | [Static sweep](CHALK_FILL001_RS_STATIC_SWEEP_2026-11-04.md) |
| FILL-001 committed PNG replay | 27/27, actual 98.430600% coverage, 11 leakage pixels | **Не PASS**, несмотря на успешные тесты replay | [Replay](CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md) |
| Monitor per-run integrity | Exact telemetry, binding и per-stroke deltas в принятых сериях | Автоматическое доказательство произвольного последующего live | [Bridge API](GAME_MONITOR_BRIDGE_REFERENCE.md), [overflow diagnosis](GAME_MONITOR_BUFFER_OVERFLOW_ANALYSIS_2026-11-02.md) |

## 3. Кандидатный корпус 81 реального изображения (OFFLINE ONLY)

| Проверка | Подтверждено |
|---|---|
| Источники | 31+50, **81 уникальных SHA-256**, отсутствие exact cross-batch duplicates |
| Планы | 81 monochrome и 81 color plan, source/geometry exact duplicates: 0 |
| Mono | 168237 total strokes, median N=1897, все горизонтальные scanlines |
| Color | 942206 total source strokes, median N=10727 |
| Singletons / color transitions | **395455 / 916312** по всем 81 color plans |
| Автоматическое совпадение pHash AND dHash | 0 strict flagged pairs, 20 closest pairs требуют ручного просмотра |
| Состояние статистики | `family_label=unclassified`, independence и predictor-domain **NOT ASSESSED** |

**Источники:** [screening CI 42417067363](https://github.com/Kiddos19882/AutoDraw/actions/runs/42417067363) и [artifact 13591858161](https://github.com/Kiddos19882/AutoDraw/actions/runs/42417067363/artifacts/13591858161), [geometry audit](VALIDATION_CORPUS_GENERATOR_2026-11-07.md). Конфигурация: canvas 646×323, contain, row step 1. Отсутствие source/geometry duplicates и strict perceptual flags не доказывает семантическую независимость.

Эти числа — **не измеренный CHALK**. Color scanline Stage6 и mono Stage8 — разные execution paths; INT-006 frozen predictor валидирован для D1–D5 line-based, не автоматически для fills. [95% split protocol](CHALK_95_PERCENT_CALIBRATION_HOLDOUT_PROTOCOL_2026-11-07.md) остаётся proposed, 19/59 не выполнялся.

## 4. CI и уровни подтверждения

- [Full AutoDraw validation 42417067391](https://github.com/Kiddos19882/AutoDraw/actions/runs/42417067391): **SUCCESS** на `5a55e9f`; Windows portable job мог быть SKIPPED — читать jobs конкретного run.
- [Offline screening 42417067363](https://github.com/Kiddos19882/AutoDraw/actions/runs/42417067363): **SUCCESS**, 5 regression tests на `5a55e9f`.
- [Full validation 42416307257](https://github.com/Kiddos19882/AutoDraw/actions/runs/42416307257): **SUCCESS** на `3fdffec`.
- [Corpus ingestion 42415293374](https://github.com/Kiddos19882/AutoDraw/actions/runs/42415293374): **SUCCESS** на `985e194`.

**Граница:** E3 CI ≠ E4 live game; E4 live ≠ статистическая гарантия для неподдерживаемого domain. [Правила доказательств](EVIDENCE_AND_VALIDATION.md) · [исторические тесты](TEST_RESULTS_HISTORY_THROUGH_2026-11-08.md).

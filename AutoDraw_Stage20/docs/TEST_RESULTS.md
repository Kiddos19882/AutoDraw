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
| ENGINE-001 accepted-only temporal Egret replay | [Browser job CI 42434968046](https://github.com/Kiddos19882/AutoDraw/actions/runs/42434968046) SUCCESS на `8d5d088`; 27 historical strokes/1260 accepted points; one-pass vs incremental: Canvas2D и WebGL final RGBA **0 отличий**, 29 vs 70 paths; [artifact 13599086458](https://github.com/Kiddos19882/AutoDraw/actions/runs/42434968046/artifacts/13599086458), независимая RGBA/PIL проверка | Не E4 complete `ENTER_FRAME` trace, не same-run screen calibration, не FILL-001 quality acceptance; old CHALK unchanged | [ENGINE-001 технический отчёт](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md), [harness](../tests/game_renderer_reference.js) |
| ENGINE-001 one-click laboratory implementation | New Monitor 0.2.4 Egret `ENGINE_FRAME_SAMPLE` + Bridge persistence + stage6-driven locked 9-run CHALK block, one GUI button after setup. Validation source/test SHA `a119b7d`, [CI 42443300762](https://github.com/Kiddos19882/AutoDraw/actions/runs/42443300762) (consult final status); [pytest readiness/immutability/negative-capture tests](../source/preparation/tests/test_engine001_lab.py) | E1 code; E2/E3 gated by CI; **live E4 NOT_RUN**, screenProjection UNCALIBRATED, new CHALK NOT_MEASURED; old FILL-001 FAIL unchanged | [ENGINE-001 §20](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md), [lab code](../source/preparation/engine001_lab.py) |
| ENGINE-001 stationary duplicate-ENTER_FRAME native Egret | [Full CI 42440876068](https://github.com/Kiddos19882/AutoDraw/actions/runs/42440876068) SUCCESS, `a35d782`; 0/27/81 extra frames across 27 archived strokes, 70/71/73 surviving paths, 1260 accepted unchanged, **0 final within-backend RGBA differences**, independent PNG threshold 1/64/128/254 zero; [native PNG+manifest](https://github.com/Kiddos19882/AutoDraw/actions/runs/42440876068/artifacts/13600769368), [independent audit](https://github.com/Kiddos19882/AutoDraw/actions/runs/42440876068/artifacts/13602035420) | Canvas2D vs WebGL baseline 243 differing RGBA px; no actual frame cadence/intermediate rendering/same-run screen mapping; old FILL PNG FAIL, new CHALK NOT_RUN | [ENGINE-001 §19](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md), [harness](../tests/game_renderer_reference.js) |
| ENGINE-001 native 5px closed contour on all 3 endpoint modes | [CI 42439343897](https://github.com/Kiddos19882/AutoDraw/actions/runs/42439343897) SUCCESS on `f381ffe`; native Egret 30 PNG ([artifact 13600612786](https://github.com/Kiddos19882/AutoDraw/actions/runs/42439343897/artifacts/13600612786)); independent 4-alpha OpenCV mask audit and overlays ([artifact 13601121751](https://github.com/Kiddos19882/AutoDraw/actions/runs/42439343897/artifacts/13601121751)): board-local coverage 99.6240% smooth / 99.6743% forced-normal at alpha128 | 31 new modeled leakage px per variant, right-middle game-smooth 55→55 (0 recovered), OpenCV added-mask IoU 0.9658/0.9762; **screenTransform UNCALIBRATED**, no new CHALK and actual FILL-001 PNG FAIL | [Native §18](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md), [analyzer](../tests/analyze_engine001_outline5_reference.py) |
| ENGINE-001 native Egret endpoint vs OpenCV | [CI 42438036187](https://github.com/Kiddos19882/AutoDraw/actions/runs/42438036187) SUCCESS на `1805ebf`; 15 PNG native Egret; full 27-stroke +2936 backing px / 0 removed при alpha≥128, selected +4/+9/+13 backing px; [native PNG](https://github.com/Kiddos19882/AutoDraw/actions/runs/42438036187/artifacts/13599599617), [independent analysis](https://github.com/Kiddos19882/AutoDraw/actions/runs/42438036187/artifacts/13600208683) | OpenCV cap ~0.9664–0.9669 IoU с native; historical screen mapping UNCALIBRATED, live FILL PNG FAIL, CHALK для новых вариантов NOT_RUN | [ENGINE-001 §17](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md) |
| FILL-001-RS static sweep | 2238 offline candidates, 62 passed simulation gate | Реальный CHALK или quality gate в игре | [Static sweep](CHALK_FILL001_RS_STATIC_SWEEP_2026-11-04.md) |
| FILL-001 A–D frozen-mask offline screening | [CI 42424959123](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123) SUCCESS на `6d790cd`, 3 маски × 4 стратегии, 15 PNG + JSON ([artifact 13595421597](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123/artifacts/13595421597)); C: 99.516% / 99.593% / 99.381%, modeled leakage=0; 12/12 PNG↔JSON independently checked | Не проверяет actual game screenshot, не измеряет CHALK; D oracle-based; Windows build SKIPPED | [Analyzer](../source/preparation/chalk_fill_strategy_comparison.py), [tests](../source/preparation/tests/test_chalk_fill_strategy_comparison.py) |
| FILL-001-RS saved-ROI counterfactual | [CI 42427514794](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794) SUCCESS на `16f0e1b`; target=71110, actual uncovered=1116, leakage=11; B-model uncovered=416, model-only=738, actual-only=38. Modeled contour offsets 5/6/7/8 recover 1092/734/335/157; offset6 leaves 382 and adds 0 modeled leakage; 6 PNG + JSON [artifact 13596093007](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794/artifacts/13596093007) | Hypothetical union, **not** game-drawn contour or fresh CHALK. Existing 11 leakage persists; ±1 screen px dilation for offset6 adds 89 modeled leaks. Original PNG FAIL. | [Analyzer](../source/preparation/chalk_fill_screen_residual_comparison.py), [regression tests](../source/preparation/tests/test_chalk_fill_screen_residual_comparison.py) |
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

- **Full validation CI [42434968046](https://github.com/Kiddos19882/AutoDraw/actions/runs/42434968046) — SUCCESS** на code/test SHA `8d5d0880c2027bf5c699608578d338025d64c595`: preparation 952 passed / 24 warnings / 82 subtests; Egret browser reference, Game Monitor/Bridge, executor, app integration и INT-006 PNG audit — SUCCESS; optional algorithm benchmarks и Windows portable build — SKIPPED. Это E3, не E4 gameplay.

- [CI 42427514794](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794): **SUCCESS** на `16f0e1b6cce0`. Preparation: **952 passed**, 82 subtests; Monitor/Bridge, executor, app integration, Egret and INT-006 PNG audit jobs SUCCESS; optional benchmarks/Windows portable build SKIPPED. [artifact 13596093007](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794/artifacts/13596093007) (ZIP SHA-256 `19313debbcc350f0eeda3edf2cba9e65350690a850d5bb2d9d733bb03794d620`); actual/counterfactual colored PNGs independently counted against JSON.
- [CI 42427122693](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427122693) на `c2ae5a0`: **FAIL** (943 passed / 8 failed) — строгая проверка Git-LF SHA ошибочно отклоняла неизменённый JSON в Windows-CRLF checkout; исправлено нормализацией **только JSON**, добавлен regression test. Отрицательный результат сохранён.

- [CI 42424959123](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123): **SUCCESS** on `6d790cd72326`. Preparation/G3, Monitor/Bridge, executor, app integration, Egret reference, INT-006 pixel-audit jobs passed. Optional benchmarks and Windows portable build **SKIPPED**. Artifact: [artifact 13595421597](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123/artifacts/13595421597). Это E3 offline, а не новый E4 runtime.

- [Full AutoDraw validation 42417067391](https://github.com/Kiddos19882/AutoDraw/actions/runs/42417067391): **SUCCESS** на `5a55e9f`; Windows portable job мог быть SKIPPED — читать jobs конкретного run.
- [Offline screening 42417067363](https://github.com/Kiddos19882/AutoDraw/actions/runs/42417067363): **SUCCESS**, 5 regression tests на `5a55e9f`.
- [Full validation 42416307257](https://github.com/Kiddos19882/AutoDraw/actions/runs/42416307257): **SUCCESS** на `3fdffec`.
- [Corpus ingestion 42415293374](https://github.com/Kiddos19882/AutoDraw/actions/runs/42415293374): **SUCCESS** на `985e194`.

**Граница:** E3 CI ≠ E4 live game; E4 live ≠ статистическая гарантия для неподдерживаемого domain. [Правила доказательств](EVIDENCE_AND_VALIDATION.md) · [исторические тесты](TEST_RESULTS_HISTORY_THROUGH_2026-11-08.md).

## Совместимость ссылок на исторический PRR batch

<a id="2026-11-07--локальный-prr-batch-и-exact-chalk-evidence"></a>
Полный набор локальных PRR run ID, exact CHALK и ссылок на исходные captures находится в [TEST_RESULTS_HISTORY_THROUGH_2026-11-08.md](TEST_RESULTS_HISTORY_THROUGH_2026-11-08.md#2026-11-07--локальный-prr-batch-и-exact-chalk-evidence). Формальная позднейшая renderer acceptance — [CI 42321009715](https://github.com/Kiddos19882/AutoDraw/actions/runs/42321009715) (6/6 PASS_PER_RUN).

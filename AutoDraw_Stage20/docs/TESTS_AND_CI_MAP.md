## 2026-11-07 — geometry audit и Windows offline runner

- `source/preparation/audit_validation_corpus.py` — open_project + frozen schema normalization, counts of zero-length and unsupported-short strokes; отчёт `corpus_geometry_audit.json`, predictor domain remains NOT ASSESSED.
- `source/preparation/tests/test_audit_validation_corpus.py` — smoke и проверка path traversal rejection.
- `.github/workflows/validation-corpus-smoke.yml` — создает .autodraw, color plans, manifest, N inventory и geometry audit; [CI 42388237279](https://github.com/Kiddos19882/AutoDraw/actions/runs/42388237279) SUCCESS.
- `run_validation_corpus_local.ps1` — запуск offline на Windows с собственной исходной папкой и уникальным output. `.github/workflows/geometry-tests.yml` теперь выполняет fixture smoke. [Run 42388505263](https://github.com/Kiddos19882/AutoDraw/actions/runs/42388505263) FAILED из-за Python environment mismatch; исправлено `bb9bb2ee`, повтор [42388837703](https://github.com/Kiddos19882/AutoDraw/actions/runs/42388837703) ожидает итогового результата.

---

# Карта тестов, диагностик и CI AutoDraw

**Область:** тестовые модули, диагностические скрипты, benchmark-инструменты и их запуск в GitHub Actions.  
**Источники:** текущие тестовые файлы, `.github/workflows/geometry-tests.yml`, `ARCHITECTURE.md`, `UI_INTEGRATION_MAP.md` и актуальные результаты `TEST_RESULTS.md`. Исторические root-level `PROJECT_GUIDE.md` и `PROJECT_DOCUMENTATION.md` не являются источниками текущего статуса.  
**Ограничение:** документ описывает обнаруженные связи и конфигурацию запуска. Тесты в рамках подготовки документа не запускались.

## Offline exploratory validation corpus workflow (2026-11-07)

`.github/workflows/validation-corpus-smoke.yml` — отдельный Ubuntu/Python 3.11 workflow; запускается при изменении testImages и связанных файлов pipeline, а также вручную. Повторно использует `generate_validation_corpus.py`, palette profile и сохраняет проекты, цветные планы, manifest и `exploratory_N_summary.json` в artifact `autodraw-exploratory-fixture-corpus`. Параметры: canvas 64×32, fit contain; это smoke для fixtures, не production CHALK validation. Первый run [42387397972](https://github.com/Kiddos19882/AutoDraw/actions/runs/42387397972) FAILED из-за import path; исправлен `PYTHONPATH`. Следующий [42387485762](https://github.com/Kiddos19882/AutoDraw/actions/runs/42387485762) SUCCESS, artifact [13580167471](https://github.com/Kiddos19882/AutoDraw/actions/runs/42387485762/artifacts/13580167471). Подробные измеренные N: [TEST_RESULTS.md](TEST_RESULTS.md).

Основной `.github/workflows/geometry-tests.yml` отдельно включает `AutoDraw_Stage20/testImages/**` в push paths (`e984b68`) для регрессии при расширении fixtures.

## 1. Уровни тестирования

| Уровень | Каталог | Инструмент | Назначение |
|---|---|---|---|
| Preparation | `source/preparation/tests/` | pytest | Проверка алгоритмов подготовки, цветных планов, профилей и геометрии |
| Executor | `source/executor/tests/` | unittest discovery | Проверка image processing, contour planner и executor API |
| Интеграционные/UI | `tests/` | pytest | Проверка объединённого приложения, передачи планов и общих контрактов |
| Диагностические/benchmark | `tests/` | Python scripts | Измерения, сравнения алгоритмов, отчёты и вспомогательные проверки |
| Browser/Game Monitor | `source/game_monitor/`, `tests/` | pytest + Node.js | Smoke-проверка локального WebSocket сервера и синтаксиса JS |
| Portable build | корень `AutoDraw_Stage20/` | batch + smoke script | Сборка и запуск portable-приложения на Windows |

## 2. Подтверждённые тестовые модули

### 2.1. Preparation

| Тест | Проверяемые модули/контракты | Основные проверки |
|---|---|---|
| `source/preparation/tests/test_palette_quantization.py` | `palette_quantization` | CIEDE2000, точное соответствие палитре, прозрачность, удаление фона, редкие цвета, лимиты палитры |
| `source/preparation/tests/test_color_scanline.py` | `color_scanline` | Порядок строк и сегментов, разрывы прозрачностью, singleton, row-step/offset, лимиты, сериализация и preview |
| `source/preparation/tests/test_geometry_color_plan.py` | `geometry_color_plan`, `geometry_budget_optimizer`, `layer_segmentation`, `skeletonization`, `stroke_simplification`, `stroke_order_optimizer` | Scanline/contour/skeleton, фильтрация компонентов, маршрутизация, multi-board, бюджет, валидаторы, качество и round-trip |
| `source/preparation/tests/test_chalk_radius_matrix.py` | `chalk_radius_matrix` | Валидация радиусов/блоков, уникальность Game Monitor run, experiment identity, точность CHALK и статистика повторов |
| `source/preparation/tests/test_chalk_experiment_matrix.py` | `chalk_experiment_matrix` | G1/G2 metadata, exact capture, уникальность repeat cells, per-stroke pointDelta и статистика |
| `source/preparation/tests/test_chalk_test_blocks.py` | `chalk_test_blocks` | Полные планы G1/G2/G3/INT006R и PRR; три повтора для обычных фаз, два дополнительных paired-renderer repeats (repeat 2/3), детерминированный порядок, journal tamper rejection, последовательный claim, fail-closed и interrupted recovery |
| `source/preparation/tests/test_chalk_int006r_validation.py` | `chalk_experiment_matrix`, `chalk_test_blocks`, `chalk_int006r_validation` | 45-cell radius × geometry matrix, радиусы 1/10/30, P1-only, journal tampering, duplicate cells и incomplete analyzer gate |
| `source/preparation/tests/test_chalk_fill_experiment.py` | `chalk_fill_experiment` | Frozen FILL-001 masks, SHA-256, area matching ±5%, shape aspect ratios, row connectivity и fail-closed input validation |
| `source/preparation/tests/test_chalk_fill_committed_capture_replay.py` | `Fill001Tab.finalize_capture`, `chalk_fill_runtime_binding`, `chalk_fill_capture_adapter`, PNG audit | Replay реальных committed manifest/attempt/executor report/Bridge session и run JSON/before-after PNG; legacy session не блокирует binding; runtime binding PASS, exact CHALK=1260, corrected PNG audit coverage=98.430600% и leakage=11; PNG gate остаётся REJECTED (требуется coverage≥99% и leakage=0). Значения 97.673218%/28 относятся к предыдущему audit до affine correction. |

Дополнительные импорты в `test_geometry_color_plan.py` подтверждают, что тест напрямую обращается к внутренним функциям и модулям-реализациям, а не только к публичному API. При изменении внутренних контрактов этот тестовый файл следует рассматривать как интеграционный тест нескольких алгоритмических компонентов.

### 2.2. Executor

| Тест | Проверяемые модули/контракты | Основные проверки |
|---|---|---|
| `source/executor/tests/test_image_processing.py` | `image_processing.pipeline` | contain/cover/stretch, размер canvas, manual/Otsu threshold, crop и валидация настроек |
| `source/executor/tests/test_contour_planner.py` | `models.DrawingPlan`, `path_planning.contour_planner` | Полярность foreground, внешние/внутренние контуры, фильтр длины, пустая маска, bounds, preview и JSON round-trip |

### 2.3. Интеграционные и общие тесты

| Тест | Прямые зависимости | Назначение |
|---|---|---|
| `tests/test_import_resolution_diagnostics.py` | `models`, `geometry_models`, preparation/executor adapters, `shared_image_processing` | Проверка разрешения коротких импортов, идентичности общих классов и pipeline, загрузки legacy DrawingPlan |
| `tests/test_stage7_validator_rules.py` | `stage7_validator_rules` | Граничные правила валидации skeleton-плана |
| `tests/test_unified_app.py` | `integrated_app`, `stage8_optimizer`, `models`, `stage6_execute_plan`, `paint_limit_test`, `color_scanline`, `palette_detection`, `palette_profiles`, `chalk_fill_matrix`, `chalk_fill_execution` | Передача планов, единые каталоги, UI-вкладки, прокрутка, профили палитры, преобразование изображения, цветное/геометрическое исполнение и FILL-001 runtime JSON/context handoff в Stage 6 |

`test_unified_app.py` импортирует `integrated_app` и создаёт Tkinter UI с использованием тестовых сценариев. Это не изолированный unit test: для него важны корректные import roots, доступность графической среды Windows и согласованность нескольких вкладок.

## 3. Прямые зависимости интеграционных тестов

### 3.1. Проверка разрешения импортов

`test_import_resolution_diagnostics.py` запускает отдельные дочерние процессы Python и проверяет два порядка добавления путей:
- preparation → executor;
- executor → preparation.

Отдельные проверки подтверждают:
- короткие имена `models` и `image_processing` разрешаются из первого корня в `sys.path`;
- `preparation.models` и `executor.models` возвращают те же классы, что и `geometry_models`;
- preparation/executor image-processing adapters возвращают общие типы из `shared_image_processing.pipeline`;
- legacy JSON DrawingPlan без новых optional-полей загружается с schema_version 1.

Это важный контракт совместимости: изменение порядка путей импорта может изменить разрешение короткого имени, даже если сам модуль не менялся.

### 3.2. Объединённое приложение

`test_unified_app.py` напрямую импортирует:
- `integrated_app`;
- `stage8_optimizer` и `models`;
- `stage6_execute_plan.TargetArea`;
- `paint_limit_test`;
- `color_scanline`;
- `palette_detection` и `palette_profiles`.

По набору тестов проверяется:
- единое хранилище для подготовки и исполнения;
- передача одноцветного, цветного, геометрического и тестового плана;
- запрет перезаписи текущего плана при невалидных данных;
- UI-навигация, вертикальная прокрутка и нижние элементы вкладок;
- сохранение, выбор, загрузка и удаление профиля палитры;
- преобразование изображения, удаление белого фона и обработка прозрачности;
- согласованность профиля и плана при передаче в executor.

Тестовые mocks и patching не доказывают, что браузерная игра примет штрихи или что реальный расход ресурса совпадёт с моделью.

## 4. CI workflow

Основной validation workflow: `.github/workflows/geometry-tests.yml`; отдельный exploratory candidate-corpus workflow описан выше.

### 4.1. Job: game-monitor-tests

Платформа: Windows. Проверяет JavaScript syntax, 18 Node.js Game Monitor tests (включая renderer/transform diagnostics), зависимости локального Bridge smoke server и WebSocket smoke test. Run [41896024383](https://github.com/Kiddos19882/AutoDraw/actions/runs/41896024383): job SUCCESS; весь workflow завершился SUCCESS (включая Windows build/startup smoke-test и INT-006 PNG audit).

### 4.2. Job: preparation-tests

Рабочая директория: `AutoDraw_Stage20/source/preparation`.

1. Checkout и установка Python 3.11.
2. Установка preparation и executor requirements, pytest.
3. Полный `python -m pytest -q -ra tests` для Preparation, brush, Game Monitor capture и G3 block regressions.
4. `tests/benchmark_capsule_rasterization.py` — сравнение global-AABB reference и per-segment capsule broad phase; проверка mask equivalence, candidate slots, predicate calls и median wall-clock. JSON публикуется как artifact `autodraw-capsule-broad-phase-benchmark`.
5. `tests/analyze_chalk_fill001_rs_sweep.py` — воспроизводимый exhaustive FILL-001-RS static spacing sweep; отчёт публикуется как artifact `autodraw-fill001-rs-static-sweep`.

### 4.3. Job: integration-tests

Рабочая директория: `AutoDraw_Stage20`.

- `tests/test_unified_app.py` — unified application и G3 UI handoff.
- Root build/import/test-runner regressions.
- Geometry validator и metric tests для fallback sweep / Stage 7.

### 4.4. Job: executor-tests

Рабочая директория: `AutoDraw_Stage20/source/executor`.

- Устанавливает executor и preparation requirements, pytest.
- Устанавливает PYTHONPATH на корень Stage20, preparation, executor и executor/tests.
- Запускает `python -m unittest discover -s tests -v`.

Точный состав автоматически найденных тестов определяется unittest discovery и файлами в `source/executor/tests/`.

### 4.5. Job: chalk-png-analysis

Зависит от успешных Preparation/G3 и Egret renderer-reference jobs. Загружает Stage A–D browser artifacts и run-bound per-run WebGL references, выполняет paired-renderer acceptance для сохранённых vertical/diagonal captures, pixel-level PNG analysis INT-006 V1–V5, independent CHALK prediction validation и INT006R radius×geometry validation; публикует отчёты и диагностические изображения. Отдельно упаковывает before/after PNG и runtime metadata для ручного visual review. Это анализ существующих captures, не новый live game run.

### 4.6. Job: windows-build-smoke

Рабочая директория: `AutoDraw_Stage20`.

Запускает `build_windows.bat` с `AUTODRAW_NO_PAUSE=1` и `AUTODRAW_SKIP_TESTS=1` после успешных обязательных regression jobs. После успешной сборки и startup smoke test публикует `release/AutoDrawPortable/` как artifact `autodraw-g3-preflight-build` (7 дней). Это не тест качества рисования в игре.

### 4.7. Job: algorithm-benchmarks

Длительный Stage 5/7/8 benchmark suite запускается только через `workflow_dispatch` с `run_algorithm_benchmarks=true`; по умолчанию job SKIPPED. В него входят image diagnostics, Stage 5/7/8 comparisons, synthetic Stage 7 cases, fallback merge sweep и outline-first comparison. Он не заменяет обязательные regression jobs и capsule broad-phase benchmark из preparation-tests.


## 2026-11-05 — verified Bridge automation and full CI result

- Full CI [41994624425](https://github.com/Kiddos19882/AutoDraw/actions/runs/41994624425) on code/test commit `58ebdda7cf3f07ceef1075020f2808a2782562b7`: all required jobs SUCCESS; optional benchmarks SKIPPED.
- Game Monitor/Bridge: Node lifecycle tests 4/4; Python WebSocket/snippet/provenance suite 31 passed. Opt-in telemetry is selected only for paired-renderer scenarios, pre-enabled user state is preserved, changed state is restored on disconnect, and configuration is written to session/run records.
- Preparation/G3: 880 passed, 24 warnings, 82 subtests. Capsule broad-phase benchmark artifact `13399777779`; FILL-001-RS static sweep artifact `13399922622`.
- Formal paired horizontal renderer gate: `PASS_PER_RUN`, artifact `13399663414`; this is not multi-axis series acceptance.
- V1–V5: 90/90 captures valid across 10 series × 9 runs; artifact `13400530501`.
- INT-006/INT006R: 45/45 accepted each; estimator safety margin/production eligibility remain not established; latest INT006R visual package awaits manual review.
- Windows portable build/startup smoke-test SUCCESS; artifact `13399627749`.
- FILL-001 committed PNG quality gate remains FAIL (coverage 98.430600%, leakage 11).

## 5. Диагностики и benchmark-скрипты

В workflow явно используются следующие скрипты:

| Скрипт | Назначение / результат |
|---|---|
| `tests/diagnose_reference_image.py` | Диагностика исходного эталонного изображения и параметров вписывания |
| `tests/report_game_point_calibration.py` | Формирование отчёта по имеющимся наблюдениям игровой квоты |
| `tests/benchmark_drawing_algorithms.py` | Benchmark алгоритмов Stage 5; отчёт и preview |
| `tests/benchmark_stage7_interior_fill.py` | Benchmark экспериментальной внутренней заливки |
| `tests/generate_stage7_synthetic_cases.py` | Создание детерминированных синтетических входов |
| `tests/validate_stage7_synthetic_reports.py` | Проверка набора synthetic reports |
| `tests/benchmark_stage7_fallback_merge_sweep.py` | Сравнение параметров fallback merge |
| `tests/benchmark_stage8_geometry_budget.py` | Benchmark геометрического бюджета и качества preview |
| `tests/validate_stage8_geometry_budget_report.py` | Проверка Stage 8 отчёта |
| `tests/test_fallback_sweep_metrics.py` | Тест метрик fallback sweep |
| `source/preparation/tests/test_outline_first_fill_planner.py` | Тест экспериментального outline-first planner |
| `tests/benchmark_outline_first_fill.py` | Сравнение outline-first и interior-fill стратегий |
| `tests/benchmark_capsule_rasterization.py` | Offline comparison global-AABB/per-segment capsule rasterization; mask equivalence, candidate slots, predicate calls и median wall-clock; CI artifact |
| `tests/test_import_resolution_diagnostics.py` | Проверка разрешения импортов и общих моделей |
| `tests/test_unified_app.py` | Интеграционные UI-регрессии |

Дополнительные скрипты анализа лабораторных данных (например, анализ серий brush experiments и centerline) документируются в соответствующих разделах [FILE_STORAGE_CATALOG.md](FILE_STORAGE_CATALOG.md) и [MODULE_REFERENCE.md](MODULE_REFERENCE.md). Их не следует считать частью каждого запуска CI, если они не перечислены в workflow.

## 6. Пути, артефакты и изоляция

- Benchmark output направляется в `AutoDraw_Stage20/benchmark-results/`; workflow публикует его через upload-artifact.
- Portable-сборка публикуется отдельным artifact `autodraw-g3-preflight-build` только после успешного startup smoke test; она предназначена для локального preflight и не содержит live G3 captures.
- WebSocket smoke test запускается отдельно от общего preparation pytest.
- Preparation и executor используют общий PYTHONPATH в отдельных шагах, но executor job дополнительно добавляет `source/executor/tests`.
- Для benchmark используются фиксированные параметры доски/изображения и palette profile. Изменение fixture или профиля может менять результаты benchmark, даже если тестируемый алгоритм не менялся.
- Не следует считать файлы в `benchmark-results/` долговременными пользовательскими данными: это CI-артефакты/выходы диагностических запусков.


### 2.4. Дополнительные тесты Preparation — прямые импорты

Следующие файлы прочитаны непосредственно; перечислены внутрипроектные импорты. Стандартная библиотека и сторонние библиотеки опущены.

| Тест | Прямые внутрипроектные импорты |
|---|---|
| `source/preparation/tests/test_brush_planner.py` | `brush_planner` |
| `source/preparation/tests/test_paint_cost_model.py` | `color_scanline`, `paint_cost_model` |
| `source/preparation/tests/test_stage13_profiles.py` | `profile_manager` |
| `source/preparation/tests/test_paint_limit_test.py` | `palette_detection`, `palette_profiles`, `paint_limit_test` |
| `source/preparation/tests/test_palette_profiles.py` | `palette_detection`, `palette_profiles` |
| `source/preparation/tests/test_stage12_workbench.py` | `image_processing`, `stage8_optimizer`, `stage9_quality`, `autodraw_project`, `models.drawing_plan` |
| `source/preparation/tests/test_palette_detection.py` | `palette_detection_ui`, `palette_detection`, `palette_reduction` |
| `source/preparation/tests/test_interval_quota_fit.py` | `interval_quota_fit` |
| `source/preparation/tests/test_board_resource_model.py` | `board_resource_model` |
| `source/preparation/tests/test_stroke_simplification.py` | `stroke_simplification` |

### 2.5. Дополнительные тесты Executor — прямые импорты

| Тест | Прямые внутрипроектные импорты |
|---|---|
| `source/executor/tests/test_drawing_plan.py` | `models`, `path_planning.test_shape` |
| `source/executor/tests/test_plan_transform.py` | `drawing.plan_transform`, `models` |
| `source/executor/tests/test_stroke_optimizer.py` | `models`, `path_planning.stroke_optimizer` |
| `source/executor/tests/test_execution_hardening.py` | `drawing.mouse_executor`, `models` |
| `source/executor/tests/test_execution_diagnostics.py` | `drawing.execution_diagnostics`, `models` |

### 2.6. Дополнительные общие тесты — прямые импорты

| Тест | Прямые внутрипроектные импорты |
|---|---|
| `tests/test_test_runner.py` | `run_all_tests` |
| `tests/test_build_helpers.py` | `build_windows` |
| `tests/test_fallback_sweep_metrics.py` | `benchmark_stage7_fallback_merge_sweep` |
| `tests/test_websocket_smoke_server.py` | `websocket_smoke_server` (локальный импорт внутри теста) |
| `tests/test_brush_experiment_series.py` | `analyze_brush_experiment_series` |
| `tests/analyze_chalk_radius_matrix.py` | `chalk_radius_matrix` (локальный импорт через preparation path) |

Указание «прямые импорты» означает только синтаксически обнаруженные import/from-import statements, включая локальные импорты внутри функций. Оно не описывает транзитивные зависимости импортируемого модуля и не является графом runtime-загрузки.


### 2.7. Ещё пять тестов Preparation — прямые импорты

| Тест | Прямые внутрипроектные импорты |
|---|---|
| `source/preparation/tests/test_paint_budget_optimizer.py` | `palette_quantization`, `paint_budget_optimizer` |
| `source/preparation/tests/test_game_point_calibration.py` | `game_point_calibration` |
| `source/preparation/tests/test_interior_fill_planner.py` | `interior_fill_planner` |
| `source/preparation/tests/test_geometry_budget_optimizer.py` | `geometry_budget_optimizer`, `geometry_color_plan` |
| `source/preparation/tests/test_outline_first_fill_planner.py` | `brush_footprint_geometry`, `outline_first_fill_planner` |


### 2.8. Дополнительные тесты Preparation — прямые импорты

| Тест | Прямые внутрипроектные импорты |
|---|---|
| `source/preparation/tests/test_brush_calibration.py` | `brush_calibration` |
| `source/preparation/tests/test_brush_test_workflow.py` | `brush_test_workflow` |
| `source/preparation/tests/test_color_point_quota_integration.py` | `color_scanline` |
| `source/preparation/tests/test_interior_fill_benchmark.py` | `benchmark_interior_fill`, `benchmark_stage7_interior_fill` |
| `source/preparation/tests/test_swept_footprint_geometry.py` | `swept_footprint_geometry` (включая локальные импорты helper-функции) |
| `source/preparation/tests/test_engine_point_calibration.py` | `engine_point_calibration` |
| `source/preparation/tests/test_brush_experiment_capture.py` | `brush_experiment_capture` |
| `source/preparation/tests/test_brush_footprint_geometry.py` | `brush_footprint_geometry` |
| `source/preparation/tests/test_geometry_execution_adapter.py` | `color_scanline`, `drawing.color_plan_execution`, `geometry_color_plan` |
| `source/preparation/tests/test_drawing_algorithm_benchmark.py` | `color_scanline`, `drawing_algorithm_benchmark`, `geometry_color_plan` |
| `source/preparation/tests/test_brush_behavior_test_ui.py` | `brush_behavior_test_ui`, `brush_radius_feedback` |
| `source/preparation/tests/test_brush_radius_feedback.py` | `brush_radius_feedback` |
| `source/preparation/tests/test_optimizer_end_to_end.py` | `color_scanline`, `paint_budget_optimizer`, `paint_cost_model`, `palette_quantization` |

### 2.9. Дополнительный тест Executor — прямые импорты

| Тест | Прямые внутрипроектные импорты |
|---|---|
| `source/executor/tests/test_color_plan_execution.py` | `test_execution_hardening` (тестовый helper), `palette_detection`, `palette_profiles`, `color_scanline`, `drawing.color_plan_execution`, `brush_radius_feedback`, `brush_planner`, `geometry_color_plan`, `models`, `drawing.mouse_executor` |

**Вспомогательный модуль тестов:** `source/executor/path_planning/test_shape.py` импортирует `models.DrawingPlan`, `Point`, `Stroke`; он используется как helper в `test_drawing_plan.py`, а не учитывается как отдельный discovery-тест в таблице выше.

## 7. Границы и недостающая инвентаризация

1. Поиск GitHub Code Search по `test_` обнаружил 46 уникальных файлов `test_*.py` в трёх каталогах: `source/preparation/tests/`, `source/executor/tests/` и `tests/`. Все 46 файлов представлены в таблицах раздела 2.
2. Для всех 46 файлов прочитаны исходники и зафиксированы прямые внутрипроектные import/from-import statements; стандартные и сторонние зависимости опущены.
3. `source/executor/path_planning/test_shape.py` отдельно отмечен как helper, используемый тестом DrawingPlan, а не как самостоятельный тест из discovery-каталога.
4. Вспомогательные скрипты из `tests/` не все имеют автоматические тесты: часть из них — CLI-инструменты/benchmark runners.
5. В рамках документирования не запускались тесты, benchmarks, UI или portable build.
6. CI YAML описывает предполагаемый процесс, но его наличие не является доказательством успешного выполнения на текущем commit. Для статуса выполнения следует смотреть конкретный GitHub Actions run.

## 8. Связанные документы

- [DEPENDENCY_MAP.md](DEPENDENCY_MAP.md) — production imports.
- [MODULE_REFERENCE.md](MODULE_REFERENCE.md) — каталог модулей.
- [EXECUTOR_API_REFERENCE.md](EXECUTOR_API_REFERENCE.md) — API executor.
- [PREPARATION_API_REFERENCE.md](PREPARATION_API_REFERENCE.md) — API preparation.
- [UI_INTEGRATION_MAP.md](UI_INTEGRATION_MAP.md) — интеграция UI.
- [FILE_STORAGE_CATALOG.md](FILE_STORAGE_CATALOG.md) — файлы и каталоги данных.
- [PROJECT_GUIDE.md](../PROJECT_GUIDE.md) — рабочие правила и общий план.


## 7. Game Monitor JavaScript behavior tests — INT-003

**Файл:** `source/game_monitor/tests/game_monitor.test.js`  
**Среда:** Node.js built-in test runner (`node --test`), без браузера и без реального игрового iframe.

Проверяемые контракты:
- точный O(1) snapshot из `BoardPane.max` и `BoardPane.less`;
- `pointCount=max-less` и delta между контрольными точками;
- отсутствие индексных чтений `atom.points` со стороны Monitor в `status()`, `export()` и wrappers;
- явный `diagnosticSnapshot()` выполняет полный подсчёт и сверяет его с ресурсным snapshot;
- отсутствие скрытого array fallback, если engine fields отсутствуют/невалидны;
- восстановление исходного метода после `stop()`;
- read-only `rendererSnapshot()`: engineVersion/renderMode/systemRenderer, canvas scale factors, DPR/viewport scale, stage/canvas dimensions и CSS transforms;
- stage→client mapping углов BoardPane через canvas content quad, display-object parent chain и mask metadata;
- безопасная деградация с `null`/пустым player list при отсутствии Egret runtime/canvas.

В `.github/workflows/geometry-tests.yml` добавлен отдельный шаг:
```powershell
node --test ..\\game_monitor\\tests\\game_monitor.test.js
```

**Граница:** эти тесты проверяют JS-логику Monitor на mock BoardPane. Они не заменяют живую проверку реального Egret BoardPane, frame probe или A/B/C-измерение overhead.


- Дополнительно проверяется `inspect()` после `stop()`: точный snapshot доступен без повторного attach и без изменения исходных методов BoardPane.


## Дополнение 2026-10-31 — тесты преобразования координат Brush Test

Добавлен `source/preparation/tests/test_brush_coordinate_transform.py`:
- отображение логических углов и центра доски в экранный ROI;
- проверка масштаба X/Y и метаданных transform;
- отсутствие мутации исходного плана;
- отклонение неверной системы координат, размера логической доски, ROI и координат за границами.

Обновлён `tests/test_unified_app.py`: тест передачи Brush Test теперь передаёт logical-план 420×240 и проверяет runtime-план в screen-local размере ROI и сохранение transform в исходном плане.

Эти проверки относятся к геометрическому преобразованию данных. Они не подтверждают физическое совпадение ROI с реальной доской в браузере; это требует live-проверки.


Дополнительно в `tests/test_unified_app.py` добавлен regression test: Stage6 должен отклонять исходный `logical_board_pixels` план, если он загружается напрямую, минуя преобразование Brush Test.

В commit `1b2d8a1` добавлен `test_fill001_plan_transfers_valid_json_context_to_stage6`: frozen FILL-001 task проходит `_transfer_brush_test_plan()`, runtime JSON повторно читается, experiment context проверяется, Stage 6 загружает DrawingPlan. Regression закрывает ошибку буквального `\n` после JSON object; CI run `41692129486` проверяет новый HEAD.



## Дополнение 2026-11-01 — запуск Game Monitor Bridge из Brush Test

В source/preparation/tests/test_brush_behavior_test_ui.py добавлена проверка normalize_game_monitor_origin(): принимается только bare HTTPS Origin; отклоняются HTTP, URL с путём, query, credentials и произвольный текст.

Серверная опция --snippet-file проверяется интеграционным запуском collector на уровне локальной Windows-сессии: UI должен получить токенизированный snippet, а после остановки сервера временный файл должен исчезнуть. Это live-интеграционный gate и не подменяется unit-тестом Origin.


**Portable build:** build_windows.py должен включать companion-каталог game_monitor рядом с AutoDraw.exe. В нём должны присутствовать game_monitor.js, game_monitor_bridge.js, game_monitor_bridge_server.py, requirements-bridge.txt и start_game_monitor_bridge.bat. Проверка Windows portable build подтверждает наличие файлов и запуск UI; реальное подключение Firefox iframe требует отдельного live-теста.


### Game Monitor Bridge — атомарное сохранение session.json

tests/test_websocket_smoke_server.py включает regression tests для persist_json_atomically():
- временные PermissionError от os.replace() должны переживаться с повтором и успешной атомарной заменой;
- при исчерпании повторов существующий session.json должен остаться неизменным, временный файл должен быть удалён;
- проверка выполняется в отдельном Windows CI step Test local WebSocket smoke server на Python 3.11.

Эти тесты проверяют политику восстановления файловой записи, но не заменяют повторный live-тест Firefox/игрового iframe с радиусом 10.


## CHALK geometry matrix G1/G2

- Production helper: `source/preparation/chalk_experiment_matrix.py`.
- Unit tests: `source/preparation/tests/test_chalk_experiment_matrix.py`.
- UI integration: `source/preparation/tests/test_brush_behavior_test_ui.py` verifies that geometry matrix metadata is preserved in experiment manifests.
- CLI: `tests/analyze_chalk_experiment_matrix.py` scans experiment manifests, validates exact captures and duplicate identities, calculates repeat statistics, and attempts stroke-level aggregation from `monitor_report.json`.
- Stroke-level aggregation is accepted only when unique `strokeId` count matches expected strokes and the sum of per-stroke `DRAW_SAMPLE.pointDelta` equals the exact experiment CHALK. Otherwise it is explicitly marked incomplete.
- Live data collection must wait for GitHub Actions success and follow `CHALK_GEOMETRY_MATRIX_PLAN.md`.


### CHALK automated block runner

- Production scheduler/journal and strict acceptance gate: `source/preparation/chalk_test_blocks.py`.
- Unit tests: `source/preparation/tests/test_chalk_test_blocks.py` — G1/G2 task completeness, repeat cells, deterministic order, journal safety, pause/interruption, complete per-stroke gate, clean frame probe and safe task-boundary stop.
- UI integration: `source/preparation/brush_behavior_test_ui.py` — Start G1/G2, progress, Stop-at-boundary, recovery, preclear, brush feedback, executor, Game Monitor capture, postdraw and transition.
- Callback workflow tests: `source/preparation/tests/test_chalk_test_block_ui_workflow.py` — accept-before-advance, incomplete evidence pause, capture timeout, executor failure, brush-restore gate, safe-stop journal recovery and G2 lock until all 12 G1 tasks are accepted.
- Recovery UI: startup detection of running/ready/paused journals, explicit board-check confirmation before retry, no automatic replay, and safe close of paused journals.
- Pending: callback-level failure injection across Tk lifecycle stages, GitHub Actions result and Windows portable smoke test.
- Live experiments must not start until CI and portable smoke test pass.


## 9. Фактический результат последнего G3 CI — 2026-11-01

**Workflow:** `.github/workflows/geometry-tests.yml` (`Geometry planner tests`).  
**Run:** [41340237207](https://github.com/Kiddos19882/AutoDraw/actions/runs/41340237207).  
**Проверенный HEAD:** `3dbf8f20bcea44c61290e49398e1a4daf182dbf9`, ветка `feature/image-geometry-optimization`.

Результат run: `completed / success`. Все три jobs завершились успешно:
- `geometry-tests`;
- `executor-tests`;
- `Windows portable build and startup smoke-test`.

Run относится к точному актуальному HEAD и включает commit `8c93a498864973b9879c926627030bb7e1d3ce2a` с тестом основного приложения, который проверяет отсутствие повторного `messagebox.askyesno` перед запуском brush-test executor.

### 9.1. Триггеры workflow

По текущему YAML:
- `push` в `feature/image-geometry-optimization`;
- `pull_request` с path-фильтром (изменения в перечисленных source/preparation, executor, game_monitor, integrated app, tests, build/runtime files и отдельных документационных файлах);
- ручной запуск `workflow_dispatch`.

Из-за path-фильтра pull_request изменение только тех файлов, которые не перечислены в YAML, может не запустить workflow. Не следует считать отсутствие run доказательством провала CI; сначала проверять event, base/head, path filter и SHA.

### 9.2. Интерпретация результата

- Успешный geometry job подтверждает прохождение включённых в него автоматических проверок и benchmark/validation steps.
- Успешный executor job подтверждает executor regression suite.
- Успешный Windows job подтверждает portable build/startup smoke-test на GitHub-hosted Windows runner.
- Ни один из этих jobs не выполняет реальный рисунок в пользовательской браузерной игре и не измеряет расход CHALK.

**Статус:** G3 software/CI gate закрыт на HEAD выше. Local Windows preflight и полный live G3 (27 captures) остаются открытыми. Исторические записи о том, что CI для popup-removal commits ожидается, superseded этим run и должны читаться как история, а не как текущий статус.


### Regression: AutoDraw focus during automatic brush handoff (2026-11-01)

- Source: `source/preparation/brush_behavior_test_ui.py::_complete_brush_radius_feedback`.
- Automated executor handoff must not call `root.deiconify()` or `root.lift()`; the game must retain foreground focus between brush verification and Stage6 execution.
- Manual brush adjustment must still restore the AutoDraw window and show its confirmation.
- Regression assertion: `test_automatic_brush_setup_starts_executor_without_visual_confirmation` checks that the root is not restored for the automatic path.
- New full CI and Windows live verification are pending; this fix is not yet a confirmed live G3 pass.
 
## 10. Оптимизированный CI и G3 regression coverage — 2026-11-02

Этот раздел описывает актуальную конфигурацию после коммитов workflow optimization; он supersedes прежнее описание job layout в разделах 4.1–4.3. Исторические CI runs и прежняя конфигурация сохранены выше для аудита.

### 10.1. Триггеры и устранение лишних запусков

- Автоматический запуск: только `push` в `feature/image-geometry-optimization` при изменениях в перечисленных исходниках, тестах, build/runtime-конфигурации или самом workflow.
- Ручной `workflow_dispatch`: запускает обязательные проверки и дополнительный длительный benchmark job.
- Удалён отдельный `pull_request` trigger, который вместе с push создавал два одинаковых набора CI на одном обновлении ветки. Проверка feature-ветки выполняется по push.
- `concurrency.group=autodraw-validation-${{ github.ref }}`, `cancel-in-progress=true`: новый commit отменяет устаревший run той же ветки, чтобы не тратить runner на промежуточные версии.
- Включён pip cache через setup-python; ключи зависят от файлов requirements соответствующего job.

### 10.2. Обязательные jobs на каждом code push

| Job | Состав |
|---|---|
| `game-monitor-tests` | Node syntax check, Node resource-snapshot tests, Python WebSocket/bridge tests |
| `preparation-tests` | Полный pytest `source/preparation/tests/`, включая G3 matrix, block journal, capture и brush UI regression tests |
| `integration-tests` | корневые тесты разделены на три изолированных pytest вызова: UI/G3 handoff (`test_unified_app.py`), build/import/test-runner/brush-series (`test_build_helpers.py`, `test_import_resolution_diagnostics.py` и др.), затем root geometry validator/metric functions. WebSocket test выполняется только в Game Monitor job. |
| `executor-tests` | Executor unittest discovery |
| `windows-build-smoke` | Portable build и startup smoke; запускается через `needs` только после успеха всех четырёх тестовых jobs, затем публикует `autodraw-g3-preflight-build` на 7 дней |

Build job устанавливает build/runtime requirements, но получает `AUTODRAW_SKIP_TESTS=1`: `build_windows.bat` пропускает встроенный повторный вызов `run_all_tests.py`, потому что его три suite уже прошли отдельные обязательные jobs. Без этой переменной обычная локальная сборка по-прежнему выполняет `run_all_tests.py`. Пропуск тестов в CI build не может сработать до успешного завершения Game Monitor, Preparation, Integration и Executor jobs благодаря `needs`.

### 10.3. Длительные benchmarks

`algorithm-benchmarks` запускается только вручную через `workflow_dispatch` и только если пользователь явно включил input `run_algorithm_benchmarks`; обычный manual validation run по умолчанию выполняет только обязательные tests/build. В него перенесены диагностика эталонного изображения, отчёт калибровки, Stage 5/7/8 benchmarks, синтетические Stage 7 cases, fallback merge sweep и сравнение outline-first/interior-fill. Эти исследования не нужны для проверки G3 handoff и больше не удлиняют каждый commit CI.

Benchmark job работает из корня `AutoDraw_Stage20/`; пути скриптов, fixture, palette и отчётов заданы относительно этой рабочей директории. Git reference paths остаются относительно корня репозитория. Отчёты и preview публикуются одним artifact `autodraw-algorithm-benchmarks`.

### 10.4. Дополнительные G3 regressions

- `source/preparation/tests/test_brush_behavior_test_ui.py::test_g3_block_task_bypasses_legacy_radius_matrix_routing` проверяет pure routing predicate для совпадающего legacy/G3 scenario ID.
- `test_g3_block_plan_writes_matrix_and_block_identity_instead_of_legacy_radius_matrix` проходит через настоящий `create_and_transfer_plan` с контролируемым UI shell и проверяет наличие `chalk_test_block`, G3 `chalk_experiment_matrix`, task-specific executor parameters и отсутствие legacy `chalk_radius_matrix`.
- `tests/test_unified_app.py::test_brush_test_executor_applies_g3_task_specific_parameters` проверяет, что параметры 2/20 из metadata передаются в Stage6 executor handoff без подмены стандартными 2/10.
- Сами тесты проверяют software contract. Они не заменяют live G3 capture, точный CHALK counter и проверку фокуса браузерной игры.

### 10.5. Текущий статус проверки

Последняя полная проверка: CI [41994624425](https://github.com/Kiddos19882/AutoDraw/actions/runs/41994624425), code/test commit `58ebdda7cf3f07ceef1075020f2808a2782562b7`, conclusion SUCCESS. Все обязательные jobs, включая Windows portable build/startup smoke-test, завершились успешно; optional algorithm benchmarks — SKIPPED. Это закрывает CI/build gate, но не заменяет локальный preflight и live capture на ПК пользователя. Новую live G3 серию можно планировать только после локального подтверждения окружения и отдельного согласования самой серии.

### 10.6. Изоляция UI tests и Tk callback lifecycle

Корневой UI test suite запускается из установленной рабочей директории Preparation и имеет отдельный 3-minute timeout. UnifiedAppCoreTests.setUp/tearDown создают временный data root и подменяют integrated_app.DATA_PATHS; тестовые окна не читают реальные data/results/brush_behavior_tests/chalk_test_blocks и не могут показать recovery warning из-за сохранённого пользовательского paused journal.

В BrushBehaviorTestTab отложенный recovery scan теперь хранит after ID. Владельческий frame отменяет callback при событии <Destroy>; сам callback очищает ID при начале выполнения. Regression test проверяет отмену pending callback. Это устраняет вызовы recovery scan после уничтожения Tk frame и изолирует UI suite от пользовательских/репозиторных журналов.
## Дополнение 2026-11-02 — Game Monitor buffer overflow / per-run integrity regression

- Node: `source/game_monitor/tests/game_monitor.test.js` проверяет, что после заполнения `MAX_EVENTS=50000` локальный массив остаётся ограниченным, счётчик buffer overflow увеличивается, а подписчики продолжают получать все события.
- Python: `tests/test_websocket_smoke_server.py` проверяет независимость per-run CHALK/trajectory от cumulative Monitor buffer overflow и старых ошибок Monitor.
- WebSocket integration: пропуск sequence должен попасть в `collector_sequence_gap_count` и в активный run report.
- Preparation: `source/preparation/tests/test_chalk_experiment_matrix.py` и `test_chalk_radius_matrix.py` проверяют, что cumulative `monitor_dropped_events` не отклоняет run, а новые per-run bridge/collector loss metrics отклоняют.
- Acceptance gate: использует `dropped_events`, `monitor_error_count_delta`, `bridge_send_failures_delta` и `collector_sequence_gap_count`. Session-cumulative `monitor_dropped_events` / `monitor_error_count` сохраняются только как диагностические aliases.
- CI job `game-monitor-tests` уже запускает Node suite и `test_websocket_smoke_server.py`; `preparation-tests` запускает матричные валидаторы. Live Firefox/Game iframe не покрывается этими тестами.


### INT-006 V1–V5
- `source/preparation/tests/test_chalk_experiment_matrix.py`: V-фазы, expected stroke counts и разрешённые sampling profiles.
- `source/preparation/tests/test_chalk_test_blocks.py`: полный 9-cell block/journal для каждой V-фазы.
- `source/preparation/tests/test_brush_behavior_test_ui.py`: число штрихов и logical-board bounds DrawingPlan.
- `tests/test_unified_app.py`: task-specific executor override для V5.
- Workflow `.github/workflows/geometry-tests.yml` покрывает эти тесты через preparation и integration jobs; успешный run для текущего HEAD ещё не подтверждён.


## INT006R radius × geometry validation

- Matrix contract: `source/preparation/chalk_experiment_matrix.py` — отдельные scenario IDs D1R–D5R, радиусы 1/10/30 и единственный sampling profile P1 (4/5).
- Durable block planner/journal: `source/preparation/chalk_test_blocks.py` — 45 уникальных ячеек `(scenario, radius, repeat)`; проверяются missing/duplicate cells, task IDs, radius, P1 и отсутствие frozen prediction artifact.
- UI and executor handoff: `source/preparation/brush_behavior_test_ui.py` и `integrated_app.py` — радиус устанавливается из task journal и повторно сверяется с requested brush до запуска штатного executor.
- Analyzer: `source/preparation/chalk_int006r_validation.py` — exact CHALK, completed journal attempt, experiment/run binding, per-stroke breakdown, before/after board ROI PNG readability/dimension checks, per-geometry/per-radius mean/median/range/population SD и сравнение с radius=10. Data completeness не закрывает отдельный manual visual-quality gate.
- Regression: `source/preparation/tests/test_chalk_int006r_validation.py` и `tests/test_unified_app.py`.
- CI/build prerequisite now passed in run `41994624425`. INT006R has 45/45 accepted captures and remains separate from frozen INT-006 predictions; it does not change the production estimator. Before using the latest visual-review package as a new manual audit, review artifact `13399289073`.


## Результаты запусков

Фактические результаты CI и тестов собраны в [TEST_RESULTS.md](TEST_RESULTS.md). Этот документ описывает состав и назначение проверок.

## Дополнение 2026-11-05 — multi-axis transform tests

- `source/preparation/tests/test_renderer_geometry.py`: synthetic horizontal, vertical and diagonal coordinate fits; screenshot fallback for an unspanned axis; inspect/screenshot cross-checks; offset and residual guards.
- `source/preparation/tests/test_brush_behavior_test_ui.py`: one-stroke vertical and diagonal paired-plan generation and metadata.
- `tests/test_unified_app.py`: paired horizontal/vertical/diagonal executor handoff with the fixed capture profile.
- `tests/compare_live_renderer_reference.py`: scenario-aware axis coverage validation; known paired scenario IDs require the corresponding Monitor-fit/screenshot-bound axes.
- CI [41976515362](https://github.com/Kiddos19882/AutoDraw/actions/runs/41976515362): all required jobs SUCCESS; optional algorithm benchmarks SKIPPED.


## Formal paired-renderer acceptance gates — 2026-11-05

- `source/preparation/renderer_acceptance.py`: fail-closed capture validation (experiment/run/session binding, exact pre/post `pointCount`, complete `POINT_QUOTA_UPDATE` / `DRAW_SAMPLE` accepted-point equality, single stroke, brush/executor profile, clean board and Monitor/Bridge integrity); transform thresholds; alpha-24 PNG metrics; per-run decision. Positive DRAW_SAMPLE may originate from `onDrawing_wrapper` or `state_poll`; both must match the ordered quota accepted-point stream exactly.
- `source/preparation/tests/test_renderer_acceptance.py`: regression checks for all three axis-source policies, capture validity and rejected evidence, transform/pixel thresholds, unique run IDs and series aggregation.
- `tests/compare_live_renderer_reference.py`: creates `comparison-report-independent-transform.json` with `PASS_PER_RUN` or `REJECTED_PER_RUN`. Only the independent, unshifted transform is scored; the post-hoc translation remains diagnostic and is excluded from acceptance.
- `tests/summarize_renderer_acceptance.py`: aggregates per-run reports. Overall multi-axis series requires three unique `PASS_PER_RUN` captures for vertical and three for diagonal; rejected attempts and duplicate run IDs are not counted.
- `tests/run_egret_stage_reference_firefox.py` generates per-run offline WebGL reference PNGs/manifests for saved non-baseline captures; `tests/run_paired_renderer_acceptance.py` binds each new run to its own reference and supports generated `manifest.json` alongside the committed baseline filename.
- Regression tests cover `state_poll` accepted-point fallback, run-bound reference directories and generated manifest resolution.
- Workflow: `.github/workflows/geometry-tests.yml`, preparation/G3 job and paired PNG audit. Run [41992373137](https://github.com/Kiddos19882/AutoDraw/actions/runs/41992373137) completed SUCCESS; artifact `13397839621` records horizontal `PASS_PER_RUN`.
- A per-run PASS is not environment-wide renderer acceptance and does not authorize calibration/profile or executor handoff. Real vertical/diagonal live captures remain required.



## Paired-renderer auto input telemetry — 2026-11-05

- `source/game_monitor/game_monitor_bridge_server.py`: strict opt-in `render_bridge_snippet()`, CLI `--enable-input-telemetry` defaults off.
- `source/game_monitor/game_monitor_bridge.js`: enables input telemetry only when requested; preserves pre-enabled user state and restores state at disconnect; reports configuration in `session_start`.
- Server persists `bridge_configuration` in `session.json` and `bridge_configuration_at_start` in run JSON.
- `source/preparation/brush_behavior_test_ui.py`: a selected paired-renderer scenario controls the opt-in flag; UI warns if a running Bridge was started in another mode.
- Regression tests: `source/game_monitor/tests/game_monitor_bridge.test.js` (4 lifecycle tests); `source/game_monitor/tests/test_game_monitor_bridge_server.py`; paired scenario selection in `source/preparation/tests/test_brush_behavior_test_ui.py`.
- Workflow [41994624425](https://github.com/Kiddos19882/AutoDraw/actions/runs/41994624425) is the active CI verification for the corrected commit `58ebdda7`.


### 2026-11-07 — run-bound paired-renderer acceptance automation

- `tests/run_egret_stage_reference_firefox.py` discovers valid saved paired-renderer experiments and creates a separate Firefox/Egret WebGL fixture, manifest and Stage A–D variants for each non-baseline run. Output is stored under `paired-renderer/<orientation>/<run_id>/`; the monitor report supplies the exact accepted point stream and same-run renderer geometry.
- `tests/run_paired_renderer_acceptance.py` uses committed baseline references for original repeat-1 runs and run-bound artifacts for later repeats. `renderer_manifest_path()` prefers the committed expected manifest filename and falls back to generated `manifest.json`.
- `source/preparation/renderer_acceptance.py` accepts positive DRAW_SAMPLE from `onDrawing_wrapper` or `state_poll`; the complete ordered stream must still match POINT_QUOTA_UPDATE accepted points exactly.
- Regression coverage: `source/preparation/tests/test_renderer_acceptance.py` (state_poll fallback) and `source/preparation/tests/test_paired_renderer_discovery.py` (per-run reference and manifest resolution).
- CI [42321009715](https://github.com/Kiddos19882/AutoDraw/actions/runs/42321009715): six unique captures, 6/6 PASS_PER_RUN; vertical 3/3, diagonal 3/3; aggregate series PASS. Artifact `13553551374`.


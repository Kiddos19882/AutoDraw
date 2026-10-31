# Карта тестов, диагностик и CI AutoDraw

**Область:** тестовые модули, диагностические скрипты, benchmark-инструменты и их запуск в GitHub Actions.  
**Источники:** текущие тестовые файлы, `.github/workflows/geometry-tests.yml`, `PROJECT_GUIDE.md` и `PROJECT_DOCUMENTATION.md`.  
**Ограничение:** документ описывает обнаруженные связи и конфигурацию запуска. Тесты в рамках подготовки документа не запускались.

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
| `tests/test_unified_app.py` | `integrated_app`, `stage8_optimizer`, `models`, `stage6_execute_plan`, `paint_limit_test`, `color_scanline`, `palette_detection`, `palette_profiles` | Передача планов, единые каталоги, UI-вкладки, прокрутка, профили палитры, преобразование изображения и интеграция цветного/геометрического исполнения |

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

Единый workflow: `.github/workflows/geometry-tests.yml`.

### 4.1. Job: geometry-tests

Рабочая директория: `AutoDraw_Stage20/source/preparation`.

Порядок основных шагов:
1. Checkout и установка Python 3.11.
2. `node --check` для `source/game_monitor/game_monitor.js`.
3. Установка зависимостей Game Monitor smoke server и pytest.
4. `tests/test_websocket_smoke_server.py` — отдельный локальный WebSocket smoke test.
5. Установка зависимостей preparation и executor.
6. Диагностика эталонного изображения.
7. Benchmark Stage 5 и загрузка отчётов/preview.
8. Benchmark Stage 7, синтетические геометрические сценарии и sweep fallback merge.
9. Benchmark Stage 8 и проверка его отчёта.
10. Проверки fallback sweep, outline-first fill и сравнение стратегий.
11. Полный pytest-набор `source/preparation/tests/`.
12. Проверка правил валидатора Stage 7.
13. Диагностика разрешения импортов.
14. UI-регрессии `tests/test_unified_app.py`.

### 4.2. Job: executor-tests

Рабочая директория: `AutoDraw_Stage20/source/executor`.

- Устанавливает executor и preparation requirements, pytest.
- Устанавливает PYTHONPATH на корень Stage20, preparation, executor и executor/tests.
- Запускает `python -m unittest discover -s tests -v`.

Точный состав автоматически найденных тестов определяется unittest discovery и файлами в `source/executor/tests/`; два конкретно проверенных теста перечислены в разделе 2.2.

### 4.3. Job: windows-build-smoke

Рабочая директория: `AutoDraw_Stage20`.

Запускает `build_windows.bat` с `AUTODRAW_NO_PAUSE=1`. Это отдельная проверка portable-сборки и startup smoke test; она не заменяет pytest/unittest и не является тестом качества рисунка в игре.

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
| `tests/test_outline_first_fill_planner.py` | Тест экспериментального outline-first planner |
| `tests/benchmark_outline_first_fill.py` | Сравнение outline-first и interior-fill стратегий |
| `tests/test_import_resolution_diagnostics.py` | Проверка разрешения импортов и общих моделей |
| `tests/test_unified_app.py` | Интеграционные UI-регрессии |

Дополнительные скрипты анализа лабораторных данных (например, анализ серий brush experiments и centerline) документируются в соответствующих разделах [FILE_STORAGE_CATALOG.md](FILE_STORAGE_CATALOG.md) и [MODULE_REFERENCE.md](MODULE_REFERENCE.md). Их не следует считать частью каждого запуска CI, если они не перечислены в workflow.

## 6. Пути, артефакты и изоляция

- Benchmark output направляется в `AutoDraw_Stage20/benchmark-results/`; workflow публикует его через upload-artifact.
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
| `source/preparation/tests/test_brush_behavior_test_ui.py` | `brush_behavior_test_ui` |
| `source/preparation/tests/test_optimizer_end_to_end.py` | `color_scanline`, `paint_budget_optimizer`, `paint_cost_model`, `palette_quantization` |

### 2.9. Дополнительный тест Executor — прямые импорты

| Тест | Прямые внутрипроектные импорты |
|---|---|
| `source/executor/tests/test_color_plan_execution.py` | `test_execution_hardening` (тестовый helper), `palette_detection`, `palette_profiles`, `color_scanline`, `drawing.color_plan_execution`, `brush_planner`, `geometry_color_plan`, `models`, `drawing.mouse_executor` |

**Вспомогательный модуль тестов:** `source/executor/path_planning/test_shape.py` импортирует `models.DrawingPlan`, `Point`, `Stroke`; он используется как helper в `test_drawing_plan.py`, а не учитывается как отдельный discovery-тест в таблице выше.

## 7. Границы и недостающая инвентаризация

1. Поиск GitHub Code Search по `test_` обнаружил 46 уникальных файлов `test_*.py` в трёх каталогах: `source/preparation/tests/`, `source/executor/tests/` и `tests/`. Все 46 файлов представлены в таблицах раздела 2.
2. Для всех 46 файлов прочитаны исходники и зафиксированы прямые внутрипроектные import/from-import statements; стандартные и сторонние зависимости опущены.
3. `source/executor/path_planning/test_shape.py` отдельно отмечен как helper, используемый тестом DrawingPlan, а не как самостоятельный тест из discovery-каталога.
4. Вспомогательные скрипты из `tests/` не все имеют автоматические тесты: часть из них — CLI-инструменты/benchmark runners.
4. В рамках документирования не запускались тесты, benchmarks, UI или portable build.
5. CI YAML описывает предполагаемый процесс, но его наличие не является доказательством успешного выполнения на текущем commit. Для статуса выполнения следует смотреть конкретный GitHub Actions run.

## 8. Связанные документы

- [DEPENDENCY_MAP.md](DEPENDENCY_MAP.md) — production imports.
- [MODULE_REFERENCE.md](MODULE_REFERENCE.md) — каталог модулей.
- [EXECUTOR_API_REFERENCE.md](EXECUTOR_API_REFERENCE.md) — API executor.
- [PREPARATION_API_REFERENCE.md](PREPARATION_API_REFERENCE.md) — API preparation.
- [UI_INTEGRATION_MAP.md](UI_INTEGRATION_MAP.md) — интеграция UI.
- [FILE_STORAGE_CATALOG.md](FILE_STORAGE_CATALOG.md) — файлы и каталоги данных.
- [PROJECT_GUIDE.md](../PROJECT_GUIDE.md) — рабочие правила и общий план.

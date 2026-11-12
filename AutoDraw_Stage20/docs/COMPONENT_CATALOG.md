# Каталог компонентов AutoDraw

Каталог предназначен для навигации по репозиторию. Он фиксирует размещение и тематическое назначение файлов, но не оценивает реализацию алгоритмов.

## Карта возможностей для повторного использования (E1, проверка кода 2026-11-12)

**Источник:** определения в рабочем дереве на commit `7cc938af4e349bd187981749d47f7e41c207ce24`. Здесь `owner` — модуль, реализующий возможность, а не имя человека; `shared/adapter/experimental` — область использования, **не** уровень E4/E5 и не разрешение на production. Поле «Тест» ведёт к исходнику проверки, но само наличие файла не доказывает E2 PASS. Актуальные сигнатуры, runtime side effects и CI подтверждать отдельно на текущем HEAD. Используйте поиск по действию/синонимам, затем откройте owner, consumer и тест.

<!-- AUTODRAW_CAPABILITIES_START -->
| ID | Что нужно / синонимы | Owner (от корня Stage20) | Entrypoint | Параметры контракта (AST) | Scope | Граница и запрет | Тест (путь, не PASS) |
|---|---|---|---|---|---|---|---|
| CAP-001 | Открыть Selenium Firefox | `source/preparation/firefox_monitor_session.py` | `open_firefox` | `-` | shared | Только браузер; разрешение на ввод отдельно | `source/preparation/tests/test_firefox_monitor_session.py` |
| CAP-002 | Подключить Game Monitor и Bridge | `source/preparation/firefox_monitor_session.py` | `attach_monitor_after_confirmation` | `driver,operator_confirmed` | shared | Нужно подтверждение доски; подключение не запускает Stage6 | `source/preparation/tests/test_firefox_monitor_session.py` |
| CAP-003 | Проверить foreground Firefox | `source/preparation/firefox_foreground_witness.py` | `wait_for_operator_firefox_foreground` | `-` | shared | Win32 PID и ручной фокус; при неоднозначности BLOCKED | `source/preparation/tests/test_firefox_foreground_witness.py` |
| CAP-004 | Получить валидный ROI серии | `source/preparation/fill001_firefox_auto_probe.py` | `collect_verified_series_firefox_roi` | `manifest,session_id,source_plan` | adapter | Подписанный план и fresh BoardPane; без fallback | `source/preparation/tests/test_fill001_series_firefox_probe.py` |
| CAP-005 | Кликнуть игровой Clear | `source/preparation/calibrated_game_clear.py` | `click_calibrated_board_clear` | `profile,screen_size` | shared | Это клик, не доказательство очистки; Monitor.clear запрещён | `source/preparation/tests/test_calibrated_game_clear.py` |
| CAP-006 | Оценить PNG после Clear | `source/preparation/brush_experiment_capture.py` | `evaluate_board_clear` | `blank_reference,after_clear` | shared | Порог 0.15% не подстраивать под результат | `source/preparation/tests/test_brush_experiment_capture.py` |
| CAP-007 | Очистить доску внутри серии | `source/preparation/fill001_series_engine001_clear.py` | `clear_with_existing_engine001` | `profile,session_id,mapping_sha256` | adapter | Требует released mouse и повторных exact snapshots | `source/preparation/tests/test_fill001_series_engine001_clear.py` |
| CAP-008 | Проверить чистую доску | `source/preparation/fill001_series_blank_verification.py` | `verify_blank_screen_after_clear` | `session_id,mapping_sha256` | experimental | Read-only; не является вызовом Clear | `source/preparation/tests/test_fill001_series_blank_verification.py` |
| CAP-009 | Построить fixed-radius фигуру | `source/preparation/chalk_fill_fixed_radius_planner.py` | `build_fixed_radius_fill_plan_for_task` | `task` | experimental | Offline геометрия не равна live quality | `source/preparation/tests/test_chalk_fill_fixed_radius_planner.py` |
| CAP-010 | Сформировать manifest серии | `source/preparation/fill001_series_runner.py` | `build_manifest` | `cycles,figures_per_cycle` | experimental | Создание manifest не разрешает input | `source/preparation/tests/test_fill001_series_runner.py` |
| CAP-011 | Выполнить защищённый цикл задач | `source/preparation/fill001_series_runner.py` | `run_with_validated_callbacks` | `manifest,run_one,clear_and_verify` | experimental | Только валидированные callbacks; no overwrite | `source/preparation/tests/test_fill001_series_runner.py` |
| CAP-012 | Получить Stage6 preflight | `source/preparation/fill001_series_stage6_preflight.py` | `prepare_series_stage6_preflight` | `-` | adapter | Fresh session/ROI; запрет устаревшей калибровки | `source/preparation/tests/test_fill001_series_stage6_preflight.py` |
| CAP-013 | Исполнить одну фигуру через Stage6 | `source/preparation/fill001_series_stage6_execution.py` | `execute_series_single_stage6` | `-` | adapter | Только opt-in, native input, release и Monitor | `source/preparation/tests/test_fill001_series_stage6_execution.py` |
| CAP-014 | Нормализовать Stage6 evidence | `source/preparation/fill001_series_stage6_execution.py` | `normalized_series_run` | `task,result` | adapter | QUOTA_LIMITED не quality PASS; exact proof обязателен | `source/preparation/tests/test_fill001_series_stage6_execution.py` |
| CAP-015 | Привязать точный CHALK к run | `source/preparation/fill001_series_run_binding.py` | `validate_series_bridge_runs` | `runs,session_id,task_id` | experimental | Только closed exact Monitor и post.pointCount-pre.pointCount | `source/preparation/tests/test_fill001_series_run_binding.py` |
| CAP-016 | Проверить экранное качество | `source/preparation/fill001_screen_mask_v2.py` | `audit_screen_mask_v2` | `-` | experimental | Run-bound PNG и frozen policy; не подменять CHALK | `source/preparation/tests/test_fill001_screen_mask_v2.py` |
| CAP-017 | Посчитать статистику серии | `source/preparation/fill001_series_statistics.py` | `analyze_series` | `manifest,results_dir` | experimental | QUOTA_LIMITED отдельно от quality PASS ranking | `source/preparation/tests/test_fill001_series_statistics.py` |
| CAP-018 | Захватить owner lock | `source/preparation/chalk_test_blocks.py` | `acquire_chalk_block_owner_lock` | `journal_path` | shared | Нельзя создавать второго владельца game input | `source/preparation/tests/test_chalk_test_blocks.py` |
| CAP-019 | Прочитать обратную связь кисти | `source/preparation/brush_radius_feedback.py` | `read_active_bridge_radius` | `-` | adapter | Достоверность свежей Bridge telemetry; не прогноз вместо факта | `source/preparation/tests/test_brush_radius_feedback.py` |
| CAP-020 | Подготовить offline варианты серии | `source/preparation/fill001_series_offline_plans.py` | `prepare_offline_variants` | `manifest` | experimental | Без игрового input и без заявления exact CHALK | `source/preparation/tests/test_fill001_series_offline_plans.py` |
<!-- AUTODRAW_CAPABILITIES_END -->

**Алгоритм reuse-first:** поиск по задаче → owner/entrypoint → текущая AST/реализация → прямые consumers и тесты → safety/quality/evidence gates → минимальная интеграция. Если нужная функция отсутствует или запись устарела — не создавать дубль автоматически; зафиксировать расхождение и исследовать существующие адаптеры.

**Граница автоматической проверки:** Python AST подтверждает наличие файла, top-level функции/класса, перечисленных имён параметров и тестового пути, но не безопасность вызова, производственный статус, точность описания, качество теста или runtime. Проверка контракта идёт через `tools/check_markdown_docs.py`.

### Проверенные статические связи owner → потребитель

В исходниках baseline `7cc938af` обнаружены прямые вызовы: `chalk_fill_ui.py` подключает общий `open_firefox()` и `attach_monitor_after_confirmation()`, использует `run_with_series_owner_lock()`, `normalized_series_run()` и `clear_with_existing_engine001()`; `fill001_series_stage6_execution.py` вызывает `validate_series_bridge_runs()` и `audit_screen_mask_v2()`. Эти связи дают маршрут для reuse, **не доказывают live PASS** и не заменяют текущий поиск всех consumers. Для новых импортов ориентироваться на текущий HEAD, а не копировать устаревший снимок зависимостей.

**Пример:** задача «стереть доску между опытами» → CAP-007 (adapter) → CAP-005 (штатный UI click) и CAP-006 (PNG comparator). Не писать отдельный `BoardPane.clear` или Selenium click. Задача «посчитать расход» → CAP-015; не использовать offline estimator как exact game CHALK.

## 1. Точки входа и упаковка

| Файл | Назначение |
|---|---|
| `integrated_app.py` | Основное объединённое Tkinter-приложение |
| `launcher.py` | Дополнительная точка запуска |
| `build_windows.bat` | Windows-сценарий подготовки окружения, проверок и сборки |
| `build_windows.py` | Сценарий сборки portable-приложения |
| `smoke_test_portable.py` | Проверка собранного portable-комплекта |
| `run_source.bat` | Запуск исходной версии |
| `run_tests.bat` | Запуск общего набора тестов |
| `run_all_tests.py` | Центральный запуск тестов |
| `app_features.json` | Манифест функций, включаемый в build metadata |

## 2. Подготовка изображения — `source/preparation/`

### Интерфейс и рабочее пространство
- `autodraw_project.py` — работа с форматом проекта AutoDraw.
- `stage13_workbench.py` — рабочее пространство подготовки.
- `stage8_optimizer.py`, `stage9_quality.py` — модули этапов оптимизации и качества.
- `palette_detection_ui.py`, `palette_quantization_ui.py`, `color_scanline_ui.py` — интерфейсы соответствующих инструментов.
- `paint_limit_test_ui.py`, `brush_behavior_test_ui.py`, `brush_calibration_ui.py` — интерфейсы вспомогательных инструментов и калибровки.

### Изображения и палитры
- `image_processing/` — пакет обработки изображений.
- `layer_segmentation.py`, `multi_board_splitter.py` — модули сегментации и разделения.
- `palette_detection.py`, `palette_profiles.py`, `palette_quantization.py`, `palette_reduction.py` — модули палитр.
- `color_scanline.py` — цветной план.
- `geometry_color_plan.py` — геометрический цветной план.

### Планы, ресурсы и геометрия
- `board_resource_model.py`, `game_point_calibration.py`, `engine_point_calibration.py`, `interval_quota_fit.py` — модели и материалы калибровок.
- `paint_cost_model.py`, `paint_budget_optimizer.py`, `paint_limit_test.py` — модули, относящиеся к учёту бюджета и тестовым сценариям.
- `brush_calibration.py`, `brush_experiment_capture.py`, `brush_test_workflow.py`, `brush_footprint_geometry.py`, `brush_planner.py` — модули калибровки и лаборатории кистей.
- `chalk_experiment_matrix.py`, `chalk_test_blocks.py` — контракты CHALK matrix, пакетное планирование, durable journal и capture acceptance.
- `chalk_int006_validation.py`, `chalk_int006r_validation.py` — отдельные анализаторы независимой INT-006 model validation и INT006R radius × geometry captures.
- `chalk_fill_experiment.py` — детерминированные frozen target masks и geometry SHA-256 для FILL-001; fixed-radius планировщик реализован экспериментально в `chalk_fill_fixed_radius_planner.py`; это не доказательство live-quality или production-ready.
- `geometry_budget_optimizer.py`, `skeletonization.py`, `stroke_simplification.py`, `stroke_order_optimizer.py`, `interior_fill_planner.py`, `outline_first_fill_planner.py`, `swept_footprint_geometry.py` — модули геометрической подготовки планов.
- `drawing_algorithm_benchmark.py` — вспомогательный benchmark-модуль.

### Модели и тесты
- `models/` — модели DrawingPlan, Point и Stroke.
- `tests/` — тесты модулей подготовки; имена тестов соответствуют тематике проверяемых компонентов.

## 3. Исполнение — `source/executor/`

- `stage1_calibration.py` — модуль калибровки.
- `stage2_drawing.py` — модуль рисования.
- `stage3_image_processing.py` — модуль обработки изображений.
- `stage4_contour_planning.py` — модуль планирования контуров.
- `stage5_stroke_optimization.py` — модуль оптимизации штрихов.
- `stage6_execute_plan.py` — модуль исполнения плана.
- `drawing/` — исполнитель цветных планов, преобразования и диагностика.
- `image_processing/` — пакет обработки изображений executor.
- `path_planning/` — планировщики контуров и штрихов.
- `models/` — модели плана, точки и штриха.
- `tests/` — тесты исполнительной подсистемы.

## 4. Общие пакеты

- `geometry_models/` — общие геометрические сущности.
- `shared_image_processing/` — общий конвейер обработки изображений.

## 5. Браузерная вспомогательная подсистема

Каталог `source/game_monitor/`:
- `game_monitor.js` — DevTools-snippet.
- `README.md` — инструкция и описание интерфейса Monitor.
- `websocket_smoke_server.py` — отдельный локальный транспортный smoke server.
- `requirements-smoke.txt` — изолированная зависимость smoke server.
- `status.json` и файлы `autodraw-game-monitor-*.json` — сохранённые данные Monitor.

## 6. Тесты и вспомогательные сценарии

Каталог `tests/` содержит:
- тесты общей интеграции и запуска;
- тесты формата проекта и импорта;
- тесты лаборатории кистей;
- скрипты подготовки и проверки отчётов;
- скрипты benchmark и диагностики;
- проверки правил валидаторов и тестового запуска.

Каталоги `source/preparation/tests/` и `source/executor/tests/` содержат тесты соответствующих подсистем.

## 7. CI workflows

| Workflow | Назначение по имени и конфигурации |
|---|---|
| `.github/workflows/geometry-tests.yml` | Проверки подготовки/геометрии, executor, smoke server и Windows portable build |
| `.github/workflows/game-brush-engine-analysis.yml` | Сбор материалов, связанных с browser game engine |
| `.github/workflows/brush-centerline-measurements.yml` | Workflow измерительных материалов кистей |
| `.github/workflows/brush-screenshot-measurements.yml` | Workflow материалов скриншотов кистей |

Фактический набор шагов конкретного workflow всегда определяется его YAML-файлом в текущем commit.

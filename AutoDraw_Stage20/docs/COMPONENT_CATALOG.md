# Каталог компонентов AutoDraw

Каталог предназначен для навигации по репозиторию. Он фиксирует размещение и тематическое назначение файлов, но не оценивает реализацию алгоритмов.

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

# Справочник модулей AutoDraw

**Назначение:** навигация по основным программным модулям и их структурным ролям.  
**Область:** исходники AutoDraw_Stage20 на ветке feature/image-geometry-optimization.

Этот документ не описывает внутренние алгоритмы и не оценивает поведение. Назначение модулей сформулировано по именам, docstrings, импортам и публичным определениям исходников. Для точной сигнатуры всегда сверяйтесь с указанным файлом текущей ветки.

## 1. Общие пакеты

### geometry_models/

Единые модели геометрических данных:
- point.py — Point;
- stroke.py — Stroke;
- drawing_plan.py — DrawingPlan.

Preparation и executor предоставляют совместимые import-модули, перенаправляющие на эти общие классы.

### shared_image_processing/

Общий конвейер обработки изображений:
- pipeline.py — определения FitMode, ThresholdMode, ProcessingResult, ProcessingSettings и функции load_rgb_image, fit_to_canvas, process_image.

Файлы source/preparation/image_processing/pipeline.py и source/executor/image_processing/pipeline.py экспортируют эти определения из общего пакета.

## 2. Подсистема подготовки — source/preparation/

### 2.1. Точка интеграции и рабочее пространство

| Модуль | Структурная роль |
|---|---|
| autodraw_project.py | Чтение, создание, экспорт и извлечение portable-проектов .autodraw |
| stage13_workbench.py | UI рабочего пространства подготовки |
| stage8_optimizer.py | UI/компонент этапа оптимизации |
| stage9_quality.py | Модуль отчётов качества и связанных представлений |
| profile_manager.py | Модели и операции с профилями подготовки/исполнения |
| palette_profiles.py | Схема и операции с профилями палитры |

### 2.2. Обработка изображения и палитры

| Модуль | Структурная роль |
|---|---|
| image_processing/pipeline.py | Совместимый импорт общего конвейера обработки изображений |
| layer_segmentation.py | Компоненты сегментации слоёв/областей |
| multi_board_splitter.py | Модели и экспорт разделения планов на доски |
| palette_detection.py | Обнаружение палитры и базовые типы палитровых данных |
| palette_quantization.py | Нормализация и преобразование палитры |
| palette_reduction.py | Сведение/сокращение палитры |
| color_scanline.py | Формирование цветного scanline-плана |
| geometry_color_plan.py | Формирование геометрического цветного плана |
| palette_detection_ui.py | UI обнаружения палитры |
| palette_quantization_ui.py | UI преобразования изображения к палитре |
| color_scanline_ui.py | UI цветного scanline-плана |

### 2.3. Геометрия, штрихи и планирование

| Модуль | Структурная роль |
|---|---|
| skeletonization.py | Модуль скелетизации масок и трассировки путей |
| stroke_simplification.py | Модуль упрощения путей |
| stroke_order_optimizer.py | Модуль порядка и ориентации штрихов |
| interior_fill_planner.py | Планировщик внутреннего заполнения |
| outline_first_fill_planner.py | Планировщик варианта outline-first |
| swept_footprint_geometry.py | Геометрические представления swept footprint |
| geometry_budget_optimizer.py | Компоненты оптимизации геометрического плана по бюджету |
| brush_footprint_geometry.py | Геометрические модели следа кисти |
| brush_planner.py | Формирование адаптивных brush-планов |
| brush_calibration.py | Модели калибровки кисти |
| brush_experiment_capture.py | Запись материалов лабораторных запусков |
| brush_test_workflow.py | Сценарии лаборатории кистей |\n| brush_radius_feedback.py | Чтение радиуса из Game Monitor и bounded-secant коррекция позиции ползунка |
| chalk_radius_matrix.py | Валидация метаданных, уникальности Game Monitor run и статистика матрицы CHALK по радиусам |

### 2.4. Ресурсные и калибровочные модули

| Модуль | Структурная роль |
|---|---|
| board_resource_model.py | Модель параметров ресурса игровой доски |
| paint_cost_model.py | Модель расчётных показателей расхода краски |
| paint_budget_optimizer.py | Компоненты планирования в рамках заданного бюджета |
| paint_limit_test.py | Сценарии теста лимита |
| game_point_calibration.py | Материалы калибровки игровых точек |
| engine_point_calibration.py | Материалы калибровки точек движка |
| interval_quota_fit.py | Модуль аппроксимации/подбора интервальных квот |
| drawing_algorithm_benchmark.py | Benchmark-модуль |

### 2.5. UI-модули подготовки

| Модуль | Назначение по имени/точке подключения |
|---|---|
| brush_behavior_test_ui.py | Интерфейс тестирования кистей и запись метаданных CHALK-матрицы |
| chalk_radius_matrix.py | Контракт серии/повтора и агрегирование точных CHALK-измерений |
| brush_calibration_ui.py | Интерфейс калибровки кистей |
| paint_limit_test_ui.py | Интерфейс теста лимита краски |

## 3. Подсистема исполнения — source/executor/

### 3.1. Этапные модули

| Модуль | Структурная роль |
|---|---|
| stage1_calibration.py | Калибровка экранной области |
| stage2_drawing.py | UI/компоненты рисования |
| stage3_image_processing.py | UI/компоненты обработки изображения |
| stage4_contour_planning.py | UI/компоненты планирования контуров |
| stage5_stroke_optimization.py | UI/компоненты оптимизации штрихов |
| stage6_execute_plan.py | UI/компоненты исполнения плана |

### 3.2. Пакет drawing/

| Модуль | Структурная роль |
|---|---|
| mouse_executor.py | MouseExecutor, ExecutorConfig, ExecutionSummary и callback-типы |
| color_plan_execution.py | Интерфейс исполнения цветных планов и связанные hooks/контроллеры |
| plan_transform.py | PlanFitInfo и fit_plan_to_size() |
| execution_diagnostics.py | Структуры и функции диагностики исполнения |

### 3.3. Другие пакеты

| Пакет | Содержимое |
|---|---|
| image_processing/ | Совместимый импорт общего конвейера обработки изображений |
| path_planning/ | contour_planner.py, stroke_optimizer.py, test_shape.py |
| models/ | Совместимые импорты общих Point, Stroke и DrawingPlan |
| tests/ | Тесты модулей executor |

## 4. Game Monitor — source/game_monitor/

| Файл | Структурная роль |
|---|---|
| game_monitor.js | Браузерный JavaScript-инструмент Monitor |
| README.md | Инструкция и описание инструмента |
| websocket_smoke_server.py | Отдельный локальный WebSocket smoke server |
| requirements-smoke.txt | Зависимости smoke server |
| status.json | Сохранённый статусный артефакт |
| autodraw-game-monitor-*.json | Экспортированные JSON-материалы |

Game Monitor документируется как самостоятельная вспомогательная подсистема. Он не является Python-пакетом основного приложения.

## 5. Тестовые каталоги

| Каталог | Область |
|---|---|
| source/preparation/tests/ | Тестовые модули подготовки |
| source/executor/tests/ | Тестовые модули исполнения |
| tests/ | Общие, интеграционные, форматные, build/smoke и вспомогательные проверки |

Имена тестов и расположение фиксируют организацию набора. Этот справочник не делает выводов о достаточности покрытия или корректности проверок.

## 6. Импортные соглашения

- Общие геометрические классы определены в geometry_models/.
- Preparation и executor импортируют Point, Stroke и DrawingPlan через локальные compatibility-модули.
- Обе подсистемы импортируют image processing API через локальные модули-адаптеры из shared_image_processing.
- Интегрированное приложение связывает UI двух подсистем через integrated_app.py.
- Публичные API цветных планов и исполнительных hooks следует сверять по исходным определениям в соответствующих файлах.

## 7. Что документировать далее

- Полные сигнатуры публичных функций и классов preparation.
- Полные сигнатуры публичных функций и классов executor.
- Форматы профилей, цветных планов, brush-планов и experiment manifests.
- Точки подключения UI к integrated_app.py.
- Диаграмму импортов с указанием направлений зависимостей.

При переименовании или перемещении модуля обновлять таблицы этого справочника и индекс документации.


## Дополнение 2026-10-31 — лаборатория кистей

- `source/preparation/brush_coordinate_transform.py` — преобразование явно маркированных logical-планов Brush Test 420×240 в screen-local ROI; исходный план сохраняется отдельно с transform metadata.

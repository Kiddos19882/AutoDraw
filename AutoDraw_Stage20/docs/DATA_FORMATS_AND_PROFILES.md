# Форматы данных: профили и планы

**Область:** пользовательские профили и JSON-артефакты подсистемы preparation.  
**Версия исходников:** ветка `feature/image-geometry-optimization`, HEAD на момент документирования `fe0bd0e42937d07b8c998d1ef907e03faa6ab651`.  
**Источники:** определения в `source/preparation/`.  
**Граница:** документ фиксирует структуру сериализуемых данных и назначение полей. Он не описывает алгоритмы формирования планов и не оценивает качество их содержимого.

## 1. Реестр профилей рабочей области

**Источник:** `profile_manager.py`.

Файл реестра имеет корневой JSON-объект:

- `schema_version` — версия схемы, сейчас `1`;
- `profiles` — массив объектов `WorkspaceProfile`.

### 1.1. WorkspaceProfile

Поля профиля:

| Поле | Тип | Назначение |
|---|---|---|
| `profile_id` | string | Идентификатор профиля |
| `name` | string | Имя |
| `canvas_width`, `canvas_height` | integer | Размер рабочего холста |
| `fit_mode` | string | Режим размещения: `contain`, `cover`, `stretch` |
| `brightness` | integer | Настройка яркости |
| `contrast` | number | Настройка контраста |
| `denoise_level` | integer | Уровень подавления шума |
| `threshold_mode` | string | `otsu` или `manual` |
| `threshold` | integer | Значение порога |
| `row_step_px` | integer | Шаг строк |
| `screen_area` | object/null | Экранная область |
| `calibration` | object | Настройки исполнения/калибровки |
| `notes` | string | Примечание |
| `created_at`, `updated_at` | string | Временные метки |

### 1.2. ScreenArea

Объект экранной области содержит:

- `x`, `y` — начало области;
- `width`, `height` — размеры;
- необязательные парные `screen_width`, `screen_height` — разрешение экрана, к которому привязана область.

В Stage 6 профиль целевой области экспортируется в форму `{"area": {"x", "y", "width", "height"}}`.

### 1.3. CalibrationSettings

Поля:

- `point_step_px`;
- `point_delay_ms`;
- `after_mouse_up_ms`;
- `before_mouse_down_ms`;
- `after_mouse_down_ms`;
- `end_hold_ms`;
- `countdown_seconds`.

Метод `to_stage6_settings()` возвращает словарь с этими же именами ключей.

### 1.4. ProfileStore

`ProfileStore` управляет JSON-реестром профилей. Публичные операции: `load()`, `save_all(profiles)`, `upsert(profile)`, `delete(profile_id)`. Статический метод `export_json(path, payload)` используется для экспорта JSON.

## 2. Документ палитры

**Источник:** `palette_detection.py`.  
**Константа версии:** `SCHEMA_VERSION = 1`.

Корневые поля:

| Поле | Состав |
|---|---|
| `schema_version` | Версия схемы |
| `created_at` | Временная метка создания |
| `screen` | `width`, `height` снимка экрана |
| `region` | `x`, `y`, `width`, `height` области палитры |
| `colors` | Массив записей цветов |
| `metadata` | Дополнительные метаданные, объект |

Запись `colors[]` содержит:

- `name` — название;
- `hex` — цвет в форме `#RRGGBB`;
- `rgb` — три целых канала;
- `screen_x`, `screen_y` — экранные координаты образца;
- `local_x`, `local_y` — координаты внутри `region`;
- `source` — источник записи.

Экранные координаты образца связаны с локальными координатами и началом области: `screen_x = region.x + local_x`, `screen_y = region.y + local_y`. RGB и HEX должны представлять один цвет. Повторяющиеся HEX-значения не допускаются.

## 3. Профиль палитры

**Источник:** `palette_profiles.py`.  
**Константа версии:** `PROFILE_SCHEMA_VERSION = 1`.

Профиль расширяет документ палитры и содержит:

- `profile_schema_version`;
- `profile_name`;
- `created_at`, `updated_at`;
- `screen`, `region`;
- `colors`;
- `calibration`;
- `metadata`.

Запись цвета профиля содержит поля документа палитры и дополнительные `id`, `status`. Статус принимает одно из значений: `detected`, `confirmed`, `corrected`.

Объект `calibration` содержит `dpi_scale_percent`, `browser_label`, `notes`, `captured_at`, `capture_method`.

Модуль поддерживает импорт документа палитры Stage 16 как исходного формата профиля и обратное преобразование через `palette_document_from_profile()`. При преобразовании профильные `id` и `status` не входят в документ палитры Stage 16.

## 4. Профиль калибровки кисти и шкалы краски

**Источник:** `brush_calibration.py`.  
**Константы:** `PROFILE_SCHEMA_VERSION = 1`, `COORDINATE_SYSTEM = "primary_screen_physical_pixels"`.

Корневые поля:

| Поле | Содержание |
|---|---|
| `schema_version` | Версия схемы |
| `profile_name` | Имя профиля |
| `coordinate_system` | Система экранных координат |
| `brush_control_mode` | `null`, `presets` или `slider` |
| `environment` | Разрешение, масштаб Windows, масштаб браузера, браузер и версия, время калибровки |
| `points` | Координаты точек управления |
| `regions` | Прямоугольные области |
| `status` | Статусы точек и областей |

Именованные точки:

- `clear_board`;
- `brush_7`, `brush_14`, `brush_20`;
- `brush_slider_value_1`, `brush_slider_value_30`;
- `editor_open`;
- `save_drawing`.

Именованные области:

- `board_area`;
- `paint_meter_area`;
- `brush_value_area`.

Каждая заданная точка хранит `x`, `y`; область — `x`, `y`, `width`, `height`. Для незаполненных элементов используется `null` и статус `not_set`. Допустимые статусы: `not_set`, `set`, `verified`, `needs_review`.

Основные операции API: `create_default_profile()`, `validate_profile()`, `adapt_profile_to_screen()`, `missing_required_fields()`, `save_profile()`, `load_profile()`.

## 5. Цветной scanline-план

**Источник:** `color_scanline.py`.  
**Константы:** `COLOR_SCANLINE_SCHEMA_VERSION = 1`, `COLOR_SCANLINE_PLAN_TYPE = "autodraw_color_scanline_plan"`.

План содержит идентификаторы схемы и типа, имя, размер холста, палитру, массив штрихов, сводные данные и метаданные источника/генерации. Основные операции: `build_color_scanline_plan()`, `validate_color_scanline_plan()`, `save_color_scanline_plan()`, `load_color_scanline_plan()`, `render_color_scanline_preview()`.

Запись штриха связывает горизонтальный отрезок с записью цвета палитры; координаты представлены парами `x`/`y`. Индекс `-1` в исходной карте цветов обозначает прозрачность и не является индексом элемента палитры. Точные поля сводки следует читать из текущего сериализованного документа и реализации соответствующей версии.

## 6. Геометрический цветной план

**Источник:** `geometry_color_plan.py`.  
**Константы:** `GEOMETRY_PLAN_SCHEMA_VERSION = 1`, `GEOMETRY_PLAN_TYPE = "autodraw_geometry_color_plan"`.

Верхнеуровневая структура включает:

- версию схемы и тип плана;
- `name`;
- `canvas`;
- `palette`;
- `strokes`;
- `summary`;
- `generation`;
- `source`.

Каждый штрих содержит `name`, массив `points` с координатами `x`/`y`, флаг `closed`, объект `color` и `metadata`. Объект цвета включает `palette_index`, `id`, `name`, `hex`, `rgb`. В метаданных штриха используется, в частности, `path_type` и `source_component_area`.

Публичные операции создания, проверки, сохранения, загрузки и построения preview перечислены в [PREPARATION_API_REFERENCE.md](PREPARATION_API_REFERENCE.md). Здесь зафиксирована только форма данных, не способ построения геометрии.

## 7. Адаптивный brush-план

**Источник:** `brush_planner.py`.  
**Константы:** `BRUSH_PLAN_SCHEMA_VERSION = 1`, `BRUSH_PLAN_TYPE = "autodraw_adaptive_brush_plan"`.

План связывает исходный цветной scanline-план с рекомендациями кисти. В записи штриха присутствуют:

- `name`;
- `source_stroke_index`;
- `closed`;
- `points`;
- `color`;
- `brush`;
- `metadata`.

Объект `brush` содержит `value`, `role`, `safe_for_color_map`, `safe_to_execute`, `width_in_source_px`. В исходном коде `safe_to_execute` при формировании записи задаётся как `false`; наличие плана само по себе не означает готовность к автоматическому исполнению.

Публичные операции: `build_adaptive_brush_plan()`, `validate_adaptive_brush_plan()`, `save_adaptive_brush_plan()`, `load_adaptive_brush_plan()`.

## 8. Манифест многодосочного плана

**Источник:** `multi_board_splitter.py`.

Корневые поля манифеста:

- `schema_version`;
- `plan_type = "autodraw_multi_board_manifest"`;
- `source_plan_type`, `source_plan_name`;
- `canvas`, `board_size`;
- `target_budget_px_equivalent`, `target_usage_percent`;
- `board_count`;
- `boards`;
- `notes`.

Каждая запись `boards[]` содержит `board_index`, `tile`, `stroke_count`, `estimated_ink_px_equivalent`, `fits_budget` и вложенный `plan`. Прямоугольник `tile` задаётся полями `x`, `y`, `width`, `height`.

Операции: `split_geometry_plan_to_boards()` и `save_multi_board_manifest()`.

## 9. Связи форматов

- Документ палитры является входным форматом для именованного профиля палитры.
- Карта индексов цветов и палитра используются при создании цветных планов.
- Адаптивный brush-план принимает цветной scanline-план и связанную с ним карту индексов.
- Манифест многодосочного плана содержит дочерние геометрические планы.
- Профиль рабочей области и профиль калибровки кисти — разные документы с разными назначениями и схемами.
- Общие геометрические сущности `Point`, `Stroke`, `DrawingPlan` описаны отдельно в [DATA_FORMATS_AND_MODELS.md](DATA_FORMATS_AND_MODELS.md).

## 10. Границы и дальнейшее уточнение

Этот справочник не объединяет разные JSON-схемы в одну универсальную схему. Версии `schema_version`, `profile_schema_version` и типы документов принадлежат конкретным форматам.

Дальнейшее документирование должно отдельно раскрыть форматы результатов лабораторных запусков, experiment manifests и экспорта Game Monitor. Точные поля JSON следует сверять с соответствующими сериализаторами текущей ветки; неизвестные поля не следует додумывать.


## 11. Журнал наблюдений теста лимита краски

**Источник:** `paint_limit_test.py`.

Файл журнала имеет корневую структуру:

- `schema_version = 1`;
- `updated_at`;
- `records` — массив записей наблюдений.

Запись, создаваемая `make_paint_limit_observation()`, содержит:

| Поле | Назначение |
|---|---|
| `recorded_at` | Время записи |
| `experiment_id` | Идентификатор серии |
| `scenario_id`, `scenario_label` | Идентификатор и название сценария |
| `profile_name` | Использованный профиль палитры |
| `color_hex` | Цвет теста |
| `outcome` | `all_visible`, `partial` или `none_visible` |
| `planned_strokes` | Запланированное количество штрихов |
| `last_visible_strokes` | Число видимых штрихов по ручному наблюдению |
| `first_missing_stroke` | Первый невидимый штрих для частичного исхода |
| `stroke_length_px` | Длина одного штриха |
| `estimated_visible_path_length_px` | Оценённая видимая длина |
| `planned_path_length_px` | Длина всего плана |
| `target_total_drawing_length_px` | Целевая суммарная длина |
| `row_spacing_px` | Интервал между строками |
| `fresh_supply_confirmed` | Подтверждение сопоставимого запаса краски |
| `notes`, `interpretation` | Примечание и текстовая интерпретация |

Журнал обновляется через `append_paint_limit_observation()`; запись добавляется в массив `records`. Значение `outcome` является ручным результатом наблюдения, а не автоматически считанным внутренним счётчиком игры.

## 12. Снимки и результаты brush-эксперимента

**Источники:** `brush_test_workflow.py`, `brush_experiment_capture.py`.

### 12.1. Снимок состояния workflow

`BrushExperimentState.to_dict()` формирует JSON-совместимый объект:

- `schema_version = 1`;
- `record_type = "autodraw_brush_test_workflow"`;
- `experiment_id`, `created_at_utc`;
- `requested_brush`, `test_case_id`;
- `phase`, `status`, `terminal`;
- `phase_results`;
- `warnings`;
- `error`, `stop_reason`.

Возможные фазы перечислены константой `PHASES`; конечные статусы — `completed`, `stopped`, `failed`, `inconclusive`. `phase_results` — объект, в котором ключами служат имена завершённых фаз, а значениями — переданные словари результатов.

### 12.2. Структуры визуальных измерений

Функции `brush_experiment_capture.py` возвращают словари измерений, которые могут использоваться в `phase_results`:

- `compare_images()`: размеры, число изменившихся пикселей, процент изменений, среднее RGB-отклонение и `exact_match`;
- `measure_meter_fill_against_baseline()`: статус оценки, ширина шкалы, оценка заполнения, процент и уровень уверенности;
- `evaluate_meter_restoration()`: статус, сравнение с baseline и оценка заполнения;
- `evaluate_board_clear()`: статус, процент отличий, сравнение с отдельным эталоном пустой доски;
- `measure_stroke_visibility()`: агрегированные количества видимых, невидимых и неоднозначных ROI, а также массив результатов по штрихам.

Эти поля являются результатами визуального сравнения изображений. В исходниках явно отделено такое сравнение от прямого чтения внутреннего игрового счётчика.

### 12.3. Файлы изображений

`crop_calibrated_regions()` возвращает изображения областей `board_area` и `paint_meter_area`. Функция сама не сохраняет их на диск. Пути и правила хранения снимков относятся к уровню UI/контроллера и должны документироваться по фактическим местам вызова, а не выводиться из этой функции.

## 13. Экспорт Game Monitor

Game Monitor — самостоятельный JavaScript DevTools-инструмент. Его экспорт формируется объектом телеметрии и может быть скачан методом `AutoDrawGameMonitor.download()`. README фиксирует типы собираемых событий, но не задаёт полную стабильную JSON-схему экспорта.

Поэтому точную структуру экспортируемого JSON следует документировать отдельно по реализации `game_monitor.js`, включая версию Monitor, поля статуса, события, ошибки и защиту URL. До такой сверки экспорт не считается формально описанным форматом.

## 14. Связи и границы

- Журнал теста лимита хранит наблюдения отдельно от исходного цветного плана; связь с серией задаётся `experiment_id`.
- Brush workflow snapshot содержит пофазные результаты, но не заменяет файлы изображений, если контроллер сохраняет их отдельно.
- Результаты визуальных измерений не следует переименовывать в подтверждения игрового счётчика.
- Экспорт Game Monitor не объединяется с журналом теста лимита или brush workflow без явного идентификатора связи.


## 15. JSON-экспорт Game Monitor

**Источник:** `source/game_monitor/game_monitor.js`, версия Monitor `0.1.2`.

Метод `AutoDrawGameMonitor.export()` возвращает объект со следующими полями верхнего уровня:

| Поле | Тип | Назначение |
|---|---|---|
| `schemaVersion` | number | Версия схемы экспорта, сейчас `1` |
| `monitorVersion` | string | Версия JavaScript Monitor |
| `startedAtPerformanceMs` | number/null | Время старта в шкале `performance.now()` |
| `exportedAtPerformanceMs` | number | Время формирования экспорта в той же шкале |
| `page` | object | `origin`, `pathname` |
| `frameContext` | object | `isTopFrame`, `currentFrame`, `frameCandidates` |
| `boardDetected` | boolean | Обнаружена ли доска |
| `boardLabel` | string/null | Метка экземпляра доски |
| `eventCount` | number | Число сохранённых событий |
| `droppedEvents` | number | Число событий, не помещённых в буфер |
| `errors` | array | Ошибки Monitor |
| `events` | array | Буфер событий |

Снимок доски, помещаемый в события и возвращаемый методом `status()`, содержит `logicalWidth`, `logicalHeight`, `scaleX`, `scaleY`, `pointCount`, `strokeArrayLength`, `lastPoint`, `radius`.

Событие включает общие поля `monitorVersion`, `t`, `type`, `strokeId`, `board` и дополнительные поля, зависящие от типа события. В реализации используются типы, связанные с запуском/остановкой Monitor, подключением доски, началом/завершением штриха, изменением кисти, обновлением квоты точек, снимками движения указателя, ошибками методов и Resource Timing. Поля дополнительных данных определяются конкретным событием и не образуют одну фиксированную структуру.

`AutoDrawGameMonitor.download()` сериализует результат `export()` в JSON-файл с именем `autodraw-game-monitor-<timestamp>.json`.

### 15.1. Структура ошибок

Элементы `errors[]` формируются как объекты с временем `t` и текстом `message`. Они относятся к ошибкам поиска stage, подключения/восстановления методов и наблюдения ресурсов.

### 15.2. Безопасность экспортируемых URL

Для Resource Timing URL пропускается через `safeUrl()`. Значения query-параметров, имена которых содержат `token`, `auth`, `session`, `cookie`, `secret`, `key`, `uid` или `user`, заменяются на `[REDACTED]`. Это правило относится к URL, обработанным Monitor; оно не является общей очисткой любых произвольных данных в экспортируемом JSON.


## 16. Входные данные и отчёт калибровки игровых точек

**Источник:** `game_point_calibration.py`.

### 16.1. Входной документ

Функция `analyze_game_point_calibration(document)` принимает JSON-совместимый объект с:

- `schema_version = 1`;
- `browser` — объект с данными браузерной среды;
- `browser.frame_probe` — снимок измерения кадров версии `2`;
- `runs` — массив запусков калибровочной серии.

Снимок `frame_probe` должен содержать `schema_version`, `probe_status`, признаки видимости вкладки, `average_fps`, `median_fps`, `duration_ms`, `wall_clock_elapsed_ms`, `frame_count`, `median_frame_interval_ms`, `p95_frame_interval_ms`, `max_frame_interval_ms`.

Запись `runs[]` содержит идентификатор запуска, тип доски и лимит точек, шаг и задержку исполнителя, измеренную частоту кадров, сценарий, длину штриха, количество запланированных штрихов и длину пути, исход наблюдения, количество последних полностью видимых штрихов, видимую длину пути, подтверждение сопоставимого запаса, номер повтора и примечание.

Допустимые исходы: `all_visible`, `partial`, `none_visible`. Входной документ использует `schema_version = 1`, отдельно от версии снимка кадров.

### 16.2. Отчёт

Результат `analyze_game_point_calibration()` имеет `schema_version = 2` и содержит:

- `model_id`, `is_engine_exact_counter`, `generated_at`;
- нормализованный объект `browser` и `frame_probe`;
- `input_run_count`, `fit_eligible_run_count`;
- `excluded_runs`;
- массив `models`;
- `summary`;
- `interpretation_limits`.

Каждая модель группируется по типу доски, лимиту, шагу, задержке и измеренной частоте кадров. Поля модели включают `fit_status`, `fitting_method`, коэффициенты `points_per_path_px` и `points_per_stroke`, диагностические показатели подгонки, `per_run_fit` и примечание. Варианты `fit_status` включают `insufficient_data`, `underdetermined`, `invalid_fit`, `calibrated`, `needs_repeat`.

Отчёт прямо помечен как не являющийся точным внутренним счётчиком движка. Его поля описывают результат калибровочной модели и ограничения исходных наблюдений.

## 17. Отчёты модели ресурса и расхода

**Источники:** `board_resource_model.py`, `paint_cost_model.py`, `engine_point_calibration.py`.

### 17.1. Профиль ресурса доски

`create_board_resource_profile()` возвращает объект с `model_id`, `point_limit`, `safety_factor`, `planning_budget_points`, `reserved_points`, описанием стандартных кистей, диапазоном расширенного ползунка, диапазоном кистей планировщика, семантикой подсчёта точек и флагом необходимости калибровки для оценки.

### 17.2. Оценка использования точек

`estimate_calibrated_point_usage()` возвращает объект с `model_id`, признаками `is_estimate` и `is_calibrated_estimate`, жёстким лимитом, безопасным бюджетом, коэффициентом точек на пиксель пути, количеством штрихов, оценками точек на путь и начало штриха, общей оценкой, процентами использования, `risk_level`, `risk_label` и примечанием к калибровке.

### 17.3. Оценка эквивалентного расхода

Функции `estimate_paint_cost()` и `estimate_color_plan_paint_cost()` возвращают словари с `model_id`, `is_estimate`, длиной пути, количеством штрихов, накладными расходами, оценкой общего расхода и бюджета, процентами использования, остатком, уровнем риска и примечанием к калибровке. Для цветного плана дополнительно формируются диагностические данные по цветам.

Поля `per_color` являются разбивкой общего расчёта, а не отдельными независимыми игровыми запасами. Идентификаторы модели и флаги оценки следует сохранять при передаче этих результатов в отчёты.

### 17.4. Отчёт engine point calibration

`build_engine_point_calibration_report()` возвращает составной объект без отдельного поля `schema_version`. Основные разделы:

- `model_id`, `engine_resource`, `engine_sampling`;
- `executor_profile`;
- `reference_profile_scenarios`;
- `calibration_profile`;
- `observed_cutoff_fit`;
- `point_limit_inference`;
- `validation`;
- `observations`.

В отчёте раздельно представлены текущие параметры исполнителя и исторические параметры калибровки. Поля `is_inferred`, `is_assumed`, `frame_rate_was_measured` и `is_verified_from_observation_metadata` характеризуют происхождение данных и не должны отбрасываться при экспорте отчёта.

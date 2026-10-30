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

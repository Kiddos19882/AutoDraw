# Каталог файлового хранилища AutoDraw

**Область:** пользовательские данные, временные файлы, экспортируемые проекты и результаты инструментов AutoDraw_Stage20.  
**Основной источник путей:** `integrated_app.py`, `source/preparation/autodraw_project.py`, модули профилей/экспериментов и `source/executor/drawing/execution_diagnostics.py`.  
**Граница:** перечислены только пути и форматы, подтверждённые текущими исходниками или явно указанными интерфейсами. Каталог не описывает содержимое каждого исторического файла в Git и не оценивает корректность данных.

## 1. Корень пользовательских данных

Единое приложение формирует базовый каталог:

```text
<APP_ROOT>/
└── data/
```

`APP_ROOT` — корень приложения, вычисляемый в `integrated_app.py`. В portable-сборке корень определяется layout сборки; фактическое значение следует брать из расположения приложения, а не фиксировать абсолютный путь Windows-пользователя.

При конфигурировании `integrated_app.py` формирует следующие пути:

| Путь | Тип | Назначение |
|---|---|---|
| `data/profiles/` | каталог | Реестр профилей и настройки |
| `data/palettes/` | каталог | Данные палитр |
| `data/palettes/profiles/` | каталог | Именованные профили палитры, используемые quantization и paint-limit UI |
| `data/projects/` | каталог | Экспортированные проекты |
| `data/results/` | каталог | Результаты инструментов и отчёты исполнения |
| `data/results/palette_conversions/` | каталог | Результаты преобразования изображения под палитру |
| `data/results/color_scanline_plans/` | каталог | Цветные scanline/geometry планы |
| `data/results/paint_limit_tests/` | каталог | Планы и записи наблюдений тестов лимита краски |
| `data/results/brush_behavior_tests/` | каталог | Эксперименты, снимки и манифесты теста кистей |
| `data/logs/` | каталог | Выделенный каталог журналов |
| `data/runtime/` | каталог | Промежуточные файлы передачи данных между вкладками |
| `data/profiles/brush_paint_calibration.json` | файл | Профиль калибровки кисти/шкалы |

## 2. Настройки и профили

| Путь | Формат | Источник/владелец |
|---|---|---|
| `data/profiles/profiles.json` | JSON, ProfileStore schema | `profile_manager.ProfileStore` |
| `data/profiles/target_profile.json` | JSON | Профиль экранной области Stage6 |
| `data/profiles/execution_settings.json` | JSON | Настройки исполнения Stage6 |
| `data/profiles/brush_paint_calibration.json` | JSON | `BrushCalibrationTab` / `brush_calibration.py` |
| `data/palettes/profiles/*.json` | JSON palette profile | `palette_profiles.save_palette_profile()` и UI палитры |

Профили палитры сохраняются в каталоге, переданном `PaletteQuantizationTab` и `PaintLimitTestTab`: в едином приложении это `data/palettes/profiles/`. Сырые данные обнаружения палитры и именованные профили не следует считать одним и тем же форматом.

Путь `data/profiles/profiles.json` задаётся `AUTODRAW_PROFILE_STORE_PATH`. Другие переменные окружения для целевой области, настроек исполнения, палитр и калибровки перечислены в [CONFIGURATION_AND_DATA.md](CONFIGURATION_AND_DATA.md).

## 3. Промежуточные файлы передачи в executor

Следующие файлы создаются интеграционным слоем в `data/runtime/`:

| Файл | Назначение |
|---|---|
| `current_plan_for_execution.json` | DrawingPlan после проверки и передачи из подготовки |
| `current_color_plan_for_execution.json` | Цветной scanline-план для Stage6 |
| `current_geometry_color_plan_for_execution.json` | Geometry color plan для Stage6 |
| `current_brush_behavior_test.json` | DrawingPlan теста кисти, загружаемый общим executor |

В `data/results/paint_limit_tests/` интеграционный слой также сохраняет промежуточный план вида `current_paint_limit_plan_<scenario>.json`.

Эти имена обозначают текущие рабочие файлы передачи, а не архивные версии. Их не следует путать с сохранёнными исходными планами, экспериментальными записями или execution reports.

## 4. Результаты исполнения

Stage6 сохраняет отчёт исполнения в каталоге результатов, переданном executor через конфигурацию. Имя формируется по шаблону:

```text
execution_<timestamp>_<id>.json
```

Формат отчёта описан в [DATA_FORMATS_AND_PROFILES.md](DATA_FORMATS_AND_PROFILES.md), раздел 19. Отчёт содержит происхождение плана, SHA-256, область, параметры исполнения, сводку и сведения о среде. Для цветного исполнения добавляется отчёт color hooks.

## 5. Результаты преобразования и цветные планы

### 5.1. Преобразование палитры

`PaletteQuantizationTab` получает отдельный каталог output для результатов преобразования: `data/results/palette_conversions/`. Конкретные имена создаваемых файлов зависят от операции и реализации UI; этот каталог не является хранилищем профилей палитры.

### 5.2. Цветные планы

`ColorScanlineTab` получает каталог `data/results/color_scanline_plans/`. Формат плана определяется его `plan_type`:

- `autodraw_color_scanline_plan`;
- `autodraw_geometry_color_plan`.

Сериализаторы и схемы описаны в [DATA_FORMATS_AND_PROFILES.md](DATA_FORMATS_AND_PROFILES.md).

## 6. Тест лимита краски

Каталог: `data/results/paint_limit_tests/`.

Подтверждённые шаблоны:

| Шаблон | Содержимое |
|---|---|
| `paint_limit_<experiment_id>_<scenario_id>.json` | Сохранённый цветной план теста |
| `current_paint_limit_plan_<scenario_id>.json` | Рабочая копия плана, передаваемая executor |
| `observations.json` | Журнал ручных наблюдений, объект schema_version 1 с массивом records |

Запись наблюдения добавляется через `append_paint_limit_observation()`. Сохранение выполняется через временный файл с последующей заменой целевого JSON.

## 7. Эксперименты кистей

Каталог: `data/results/brush_behavior_tests/`.

### 7.1. Эталон пустой доски

- `blank-board-reference.png` — эталонное изображение области доски.
- `blank-board-reference.json` — метаданные эталона и сведения о подтверждении/калибровке.

### 7.2. Каталог отдельного опыта

Имя каталога формируется по шаблону:

```text
experiment-<timestamp>-b<brush>-<test_case>/
```

Внутри сохраняются `experiment.json`, планы и материалы захвата. Имена изображений фаз включают фазу и область:

- `before_clear-screen.png`, `before_clear-board.png`, `before_clear-paint-meter.png`;
- `before_draw-screen.png`, `before_draw-board.png`, `before_draw-paint-meter.png`;
- `after_draw-screen.png`, `after_draw-board.png`, `after_draw-paint-meter.png`;
- `after_clear-screen.png`, `after_clear-board.png`, `after_clear-paint-meter.png`.

Набор файлов зависит от фактически пройденных и сохранённых фаз. Не каждый опыт обязан содержать все перечисленные изображения.

### 7.3. Сводки анализа сохранённых серий

Скрипт `tests/analyze_brush_experiment_series.py` использует следующие стандартные пути:

- входные эксперименты: `data/results/brush_behavior_tests/experiment-*/experiment.json`;
- эталон: `data/results/brush_behavior_tests/blank-board-reference.png`;
- сводка: `data/results/brush_behavior_tests/brush-geometry-summary.json`;
- таблица: `data/results/brush_behavior_tests/brush-geometry-summary.csv`.

Экспорт Game Monitor хранится отдельно, в частности в `data/test_monitor/` для сохранённых серий. Три ранних JSON-экспорта находятся в `source/game_monitor/`. Не считать наличие этих файлов доказательством автоматической ссылки на них из `experiment.json`: поля `game_monitor_report_path` и `game_monitor_summary` могут оставаться null.

## 8. Формат проекта .autodraw

Проект — ZIP-архив с manifest `project.json` и логическими файлами внутри архива. Подтверждённые внутренние пути:

```text
project.autodraw
├── project.json
├── assets/
│   ├── source_image.<ext>
│   ├── binary_mask.png
│   ├── prepared_color.png        (optional)
│   └── grayscale.png             (optional)
├── config/
│   └── processing_settings.json
├── plans/
│   └── drawing_plan.json
└── reports/
    ├── quality_report.json
    └── imported_quality_report.json (optional)
```

Manifest содержит логические ссылки `files`, контрольные суммы `sha256`, размеры `byte_sizes`, размеры canvas и метаданные проекта. Полная схема описана в [DATA_FORMATS_AND_MODELS.md](DATA_FORMATS_AND_MODELS.md).

## 9. Каталоги, которые не следует смешивать

- `data/runtime/` — промежуточные данные передачи, а не долговременный архив проектов.
- `data/results/` — результаты операций, отчёты и лабораторные данные.
- `data/projects/` — экспортированные пользовательские проекты.
- `data/profiles/` — настройки и калибровки.
- `data/palettes/profiles/` — профили палитр, а не преобразованные изображения.
- `source/game_monitor/` — исходный код, инструкция и часть исторических экспортов Monitor; не пользовательское хранилище приложения.

## 10. Резервное копирование и перенос

Для переноса пользовательского состояния сохранять как минимум:

1. `data/profiles/`;
2. `data/palettes/`;
3. `data/projects/`;
4. нужные подкаталоги `data/results/`;
5. `data/test_monitor/`, если нужны сохранённые экспорты Game Monitor.

`data/runtime/` содержит промежуточные копии планов. Перед переносом или очисткой следует завершить работу приложения и убедиться, что нужные планы уже сохранены в соответствующих проектных/результирующих каталогах.

Не переносите абсолютные пути из старых manifest как универсальные: пути в исторических экспериментальных записях могут ссылаться на исходный компьютер. Для архива опыта сохраняйте весь каталог опыта вместе с `experiment.json` и файлами, на которые он ссылается.

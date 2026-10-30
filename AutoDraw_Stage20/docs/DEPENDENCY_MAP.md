# Карта импортов и межмодульных зависимостей

**Область:** основные модули AutoDraw_Stage20 и точки входа.  
**Источник:** реальные import/from-import statements, экспортные списки адаптеров и код настройки путей в текущей ветке.  
**Граница:** схема показывает прямые зависимости и уровни импорта. Она не является runtime trace и не утверждает, что каждый импортируемый модуль загружается при каждом пользовательском сценарии.

## 1. Точки входа

| Файл | Роль |
|---|---|
| `integrated_app.py` | Основная точка входа единого приложения Stage20 |
| `source/executor/stage1_calibration.py` | Отдельный legacy-интерфейс калибровки |
| `source/executor/stage2_drawing.py` | Отдельный legacy-интерфейс построения/исполнения |
| `source/executor/stage3_image_processing.py` | Отдельный legacy-интерфейс обработки |
| `source/executor/stage4_contour_planning.py` | Отдельный legacy-интерфейс контурного планирования |
| `source/executor/stage5_stroke_optimization.py` | Отдельный legacy-интерфейс оптимизации |
| `source/executor/stage6_execute_plan.py` | UI executor, встраиваемый в единое приложение |
| `source/game_monitor/game_monitor.js` | Независимый DevTools-snippet для браузера |

В интегрированном приложении `ensure_import_paths()` добавляет каталоги `source/preparation` и `source/executor` в `sys.path`. `configure_environment()` задаёт общие `AUTODRAW_*` пути до импорта компонентов, читающих пути при загрузке.

## 2. Слои зависимостей

### 2.1. Интеграционный слой

`integrated_app.py` непосредственно импортирует:

- Workbench и функции подготовки: `stage13_workbench`, `stage8_optimizer`;
- общую модель плана: `models.DrawingPlan`;
- исполнитель и селекторы: `stage6_execute_plan.Stage6App`, `AreaSelector`, `TargetArea`;
- UI палитры и цветного плана: `palette_detection_ui`, `palette_quantization_ui`, `color_scanline_ui`;
- сериализаторы планов: `color_scanline`, `geometry_color_plan`;
- экспериментальные вкладки: `paint_limit_test_ui`, `brush_behavior_test_ui`, `brush_calibration_ui`.

Интеграционный слой создаёт UI-компоненты, передаёт им callbacks и маршрутизирует планы/профили в Stage6. Подробные связи описаны в [UI_INTEGRATION_MAP.md](UI_INTEGRATION_MAP.md).

### 2.2. Preparation

Основные прямые зависимости UI и модулей подготовки:

| Потребитель | Импортируемые модули |
|---|---|
| `stage13_workbench` | `image_processing`, `stage8_optimizer`, `stage9_quality`, `autodraw_project`, `profile_manager` |
| `palette_detection_ui` | `palette_detection`, `palette_reduction`, `palette_profiles` |
| `palette_quantization_ui` | `palette_profiles`, `palette_quantization` |
| `color_scanline_ui` | `paint_cost_model`, `brush_planner`, `board_resource_model`, `paint_budget_optimizer`, `color_scanline`, `geometry_color_plan` |
| `paint_limit_test_ui` | `color_scanline`, `paint_limit_test`, `palette_profiles` |
| `brush_behavior_test_ui` | `stage8_optimizer`, `brush_test_workflow`, `brush_experiment_capture` |
| `brush_calibration_ui` | `brush_calibration` |

Дополнительные прямые зависимости модулей подготовки описаны по каждому модулю в [PREPARATION_API_REFERENCE.md](PREPARATION_API_REFERENCE.md); этот документ не перечисляет все транзитивные связи библиотек.

### 2.3. Executor

| Потребитель | Импортируемые модули |
|---|---|
| `stage6_execute_plan` | `drawing.mouse_executor`, `drawing.color_plan_execution`, `brush_planner`, `drawing.execution_diagnostics`, `drawing.plan_transform`, `models`, `color_scanline`, `geometry_color_plan`, `paint_cost_model`, `palette_profiles`, `path_planning.stroke_optimizer` |
| `drawing.mouse_executor` | `models`, PyAutoGUI, pynput keyboard |
| `drawing.color_plan_execution` | `models`; по требованию — `palette_profiles`, `color_scanline`, `geometry_color_plan`, `brush_planner` |
| `drawing.plan_transform` | `models` |
| `drawing.execution_diagnostics` | стандартная библиотека Python |
| `path_planning.contour_planner` | `models`, OpenCV, NumPy, Pillow |
| `path_planning.stroke_optimizer` | `models`, OpenCV, NumPy |

### 2.4. Общие модули и compatibility adapters

- `geometry_models/` содержит общие определения `Point`, `Stroke`, `DrawingPlan`.
- Локальный `models` import в preparation/executor используется как compatibility-слой к общим геометрическим классам.
- `shared_image_processing/pipeline.py` — общий конвейер обработки изображения.
- `source/preparation/image_processing/pipeline.py` и `source/executor/image_processing/pipeline.py` — совместимые адаптеры, реэкспортирующие определения общего конвейера.
- Оба адаптера экспортируют `FitMode`, `ThresholdMode`, `ProcessingResult`, `ProcessingSettings`, `fit_to_canvas`, `load_rgb_image`, `process_image` через `__all__`.

## 3. Диаграмма основных зависимостей

```mermaid
flowchart TD
    IA[integrated_app.py]
    IA --> W[stage13_workbench]
    IA --> S6[stage6_execute_plan]
    IA --> PD[palette_detection_ui]
    IA --> PQ[palette_quantization_ui]
    IA --> CS[color_scanline_ui]
    IA --> PL[paint_limit_test_ui]
    IA --> BT[brush_behavior_test_ui]
    IA --> BC[brush_calibration_ui]

    W --> IP[shared image processing]
    W --> PFM[profile_manager]
    W --> PRJ[autodraw_project]
    PQ --> PP[palette_profiles]
    PQ --> Q[palette_quantization]
    PD --> DET[palette_detection]
    PD --> RED[palette_reduction]
    CS --> CSP[color_scanline]
    CS --> GEO[geometry_color_plan]
    CS --> COST[paint_cost_model]
    CS --> BPL[brush_planner]
    PL --> PLM[paint_limit_test]
    BT --> BWF[brush_test_workflow]
    BT --> BEC[brush_experiment_capture]

    S6 --> ME[MouseExecutor]
    S6 --> CPE[color_plan_execution]
    S6 --> TR[plan_transform]
    S6 --> DIAG[execution_diagnostics]
    S6 --> OPT[stroke_optimizer]
    S6 --> MODELS[geometry_models]
    CPE --> PP
    CPE --> CSP
    CPE --> GEO
    CPE --> BPL
    ME --> MODELS
    OPT --> MODELS
```

## 4. Импортные соглашения и ограничения

- Пути импорта preparation/executor зависят от того, что интегрированное приложение добавляет оба каталога исходников в `sys.path`.
- Общие модули импортируются через compatibility-имена; физический файл-адаптер и исходное определение класса могут находиться в разных каталогах.
- Не следует считать каждый импорт прямым пользовательским API: часть импортов локальная и используется только внутри одного модуля.
- `__all__` явно подтверждён для двух image-processing adapters; другие модули в этой карте не объявляются пакетными публичными API без соответствующего списка в исходнике.
- Game Monitor не импортируется Python-приложением: это отдельный JavaScript-файл, вставляемый в DevTools браузера.
- Тестовые модули рассматриваются как отдельные потребители production-кода и не включены в диаграмму основного приложения.

## 5. Источники для детализации

- [MODULE_REFERENCE.md](MODULE_REFERENCE.md) — каталог модулей.
- [PREPARATION_API_REFERENCE.md](PREPARATION_API_REFERENCE.md) — API preparation.
- [EXECUTOR_API_REFERENCE.md](EXECUTOR_API_REFERENCE.md) — API executor.
- [UI_INTEGRATION_MAP.md](UI_INTEGRATION_MAP.md) — callback-связи и передача данных.
- [CONFIGURATION_AND_DATA.md](CONFIGURATION_AND_DATA.md) — каталоги и переменные окружения.

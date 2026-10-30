# Справочник API подсистемы executor

**Область:** `source/executor/`, общие геометрические модели и общий конвейер изображений.  
**Точка интеграции актуального приложения:** `integrated_app.py` → `Stage6App`.  
**Источник:** объявления классов, функций, сигнатуры и экспортные списки текущей ветки.  
**Граница:** справочник фиксирует интерфейсы и связи. Он не анализирует алгоритмы рисования, не запускает мышь/браузер и не подтверждает runtime-поведение.

## 1. Этапы executor

| Модуль | Основной класс/точка входа | Назначение интерфейса |
|---|---|---|
| `stage1_calibration.py` | `CalibrationApp`, `AreaSelector`, `TargetArea`, `CalibrationProfile`, `main()` | Отдельный интерфейс калибровки |
| `stage2_drawing.py` | `DrawingApp`, `AreaSelector`, `TargetArea`, `main()` | Предыдущая самостоятельная версия рисования |
| `stage3_image_processing.py` | `ImageProcessingApp`, `main()` | Предыдущий самостоятельный интерфейс обработки изображения |
| `stage4_contour_planning.py` | `ContourPlanningApp`, `ImagePreview`, `load_mask_file()`, `main()` | Предыдущий интерфейс планирования по контурам |
| `stage5_stroke_optimization.py` | `StrokeOptimizationApp`, `PlanPreview`, `_percent_change()`, `main()` | Предыдущий интерфейс оптимизации штрихов |
| `stage6_execute_plan.py` | `Stage6App`, `TargetArea`, `AreaSelector`, `BrushSliderSelector`, `PlanPreview`, `main()` | Текущий UI-исполнитель, также используемый единым приложением |

Для Stage 1–5 в таблице указаны классы и точки входа, объявленные в модулях. Их внутренние Tkinter-обработчики не дублируются здесь как стабильный внешний API. Текущая интеграция приложения использует Stage6.

## 2. Stage6App

**Модуль:** `stage6_execute_plan.py`.

### 2.1. Основные структуры и конструктор

- `TargetArea(x: int, y: int, width: int, height: int)`
  - `to_dict(self) -> dict[str, int]`
  - `from_dict(cls, data: dict) -> TargetArea`
- `AreaSelector(parent: tk.Tk, on_done, *, instruction: str = "Выделите рабочую область холста перетаскиванием. Esc — отмена.")`
- `BrushSliderSelector(parent: tk.Tk, on_done)`
- `PlanPreview(parent: tk.Widget)`
  - `set_plan(self, plan: DrawingPlan | None) -> None`
  - `set_image(self, image: Image.Image | None) -> None`
- `Stage6App(root: tk.Tk, parent: tk.Widget | None = None, *, embedded: bool = False)`

### 2.2. Методы, используемые внешним кодом

- `apply_brush_control_profile(self, control: dict | None) -> bool`
- `load_plan_from_path(self, path: str | Path) -> None`
- `load_color_plan_from_path(self, path: str | Path) -> None`
- `load_adaptive_brush_plan_from_path(self, path: str | Path) -> None`
- `load_color_palette_profile_document(self, document: dict[str, Any], path: str | Path | None = None) -> None`
- `start_execution_from_workflow(self) -> bool`

Интеграционный слой единого приложения также читает/назначает атрибуты `area_change_callback` и `execution_finished_callback`. Это точки связи, фактически используемые `integrated_app.py`; они не оформлены отдельными типизированными методами Stage6App.

### 2.3. Внутренние группы методов

Для навигации по исходнику:

- настройки: `_load_settings`, `_save_settings`, `_read_executor_config`;
- экранная область: `_set_area_from_file`, `_set_area_fields`, `_select_area`, `_area_selected`, `_apply_area`, `_notify_area_change`, `_validate_area`, `_save_profile`;
- загрузка планов: `_open_color_plan`, `_open_adaptive_brush_plan`, `_load_color_palette_profile_dialog`, `_open_plan`, `_refresh_execution_plan`;
- выполнение: `_start_execution`, `_execute_in_worker`, `_update_progress`, `_finish_execution`, `_execution_crashed`, `_stop_execution`;
- закрытие/папки: `_open_project_folder`, `_open_results_folder`, `_on_close`.

## 3. MouseExecutor

**Модуль:** `drawing/mouse_executor.py`.

### 3.1. Конфигурация и результат

`ExecutorConfig` — dataclass со значениями по умолчанию:

- `point_step_px: float = 2.0`;
- `line_extension_px: float = 2.0`;
- `point_delay_ms: int = 10`;
- `after_mouse_up_ms: int = 20`;
- `before_mouse_down_ms: int = 20`;
- `after_mouse_down_ms: int = 40`;
- `end_hold_ms: int = 50`;
- `countdown_seconds: int = 5`.

Методы: `validate(self) -> None`, `to_dict(self) -> dict`.

`ExecutionSummary` — dataclass со статусом, количеством завершённых/общих штрихов, временными метками, длительностью, числом move calls, ошибкой/причиной остановки и результатом попытки отпустить кнопку мыши. Метод: `to_dict(self, config: ExecutorConfig) -> dict`.

Callback-типы:

- `ProgressCallback = Callable[[int, int, str], None]`;
- `StopReasonProvider = Callable[[], str | None]`;
- `PreflightCallback = Callable[[MouseExecutor], str | None]`;
- `BeforeStrokeCallback = Callable[[MouseExecutor, int, object], str | None]`.

### 3.2. Основной интерфейс

```python
MouseExecutor(
    stop_event: threading.Event,
    config: ExecutorConfig | None = None,
    *,
    stop_reason_provider: StopReasonProvider | None = None,
)
```

```python
execute(
    plan: DrawingPlan,
    area_x: int,
    area_y: int,
    progress: ProgressCallback | None = None,
    *,
    preflight: PreflightCallback | None = None,
    before_stroke: BeforeStrokeCallback | None = None,
) -> ExecutionSummary
```

Вспомогательные методы класса начинаются с подчёркивания и являются внутренними: обработка F12, проверка остановки, ожидание с прерыванием, преобразование локальных координат в экранные, движение по сегменту и освобождение кнопки мыши.

## 4. Цветное исполнение и управление кистью

**Модуль:** `drawing/color_plan_execution.py`.

### 4.1. Функции и структуры

- `ColorPlanExecutionError(ValueError)`
- `normalize_brush_slider_points(min_point: Any, max_point: Any, *, max_y_difference: int = 8) -> tuple[int, int, int]`
- `PaletteTarget(palette_index: int, color_id: str, name: str, rgb: tuple[int, int, int], hex: str, screen_x: int, screen_y: int, status: str)`
  - `to_dict(self) -> dict[str, Any]`
- `validate_color_plan(plan: Any) -> dict[str, Any]`
- `adaptive_brush_plan_to_drawing_plan(brush_plan: Any, source_color_plan: Any) -> DrawingPlan`
- `build_brush_visual_test_plan(width: int, height: int) -> DrawingPlan`
- `color_plan_to_drawing_plan(plan: Any) -> DrawingPlan`
- `geometry_color_plan_to_drawing_plan(plan: Any) -> DrawingPlan`
- `build_palette_targets(color_plan: Any, profile_document: Any, *, current_screen_size: tuple[int, int] | None = None) -> dict[int, PaletteTarget]`

### 4.2. BrushSliderCalibration

Поля dataclass:

- `x_at_min`, `x_at_max`, `y`;
- `initial_value`;
- `screen_width`, `screen_height`;
- `confirmed`;
- `min_value = 1`, `max_value = 30`.

Методы:

- `from_dict(cls, data: Any) -> BrushSliderCalibration`;
- `coordinate_for_value(self, value: int) -> int`;
- `validate(self, current_screen_size: Any, target_area: dict[str, int] | None = None) -> None`.

### 4.3. BrushSliderController

Конструктор:

```python
BrushSliderController(
    calibration: BrushSliderCalibration,
    target_area: dict[str, int],
    *,
    current_screen_size_provider: Callable[[], Any] | None = None,
)
```

Методы: `validate(self) -> None`, `before_stroke(self, executor: Any, stroke_index: int, stroke: Stroke) -> str`, `select_value(self, executor: Any, value: int) -> str`.

### 4.4. ColorPlanExecutionHooks

Конструктор:

```python
ColorPlanExecutionHooks(
    color_plan: Any,
    profile_document: Any,
    *,
    current_screen_size_provider: Callable[[], tuple[int, int]] | None = None,
    screenshot_provider: Callable[[], Any] | None = None,
    dpi_scale_provider: Callable[[], int] | None = None,
    brush_slider_calibration: dict[str, Any] | BrushSliderCalibration | None = None,
    brush_target_area: dict[str, int] | None = None,
)
```

Методы: `preflight(self, executor: Any) -> str`, `before_stroke(self, executor: Any, stroke_index: int, stroke: Stroke) -> str`, `to_report(self) -> dict[str, Any]`.

## 5. Преобразование и диагностика исполнения

### 5.1. `drawing/plan_transform.py`

`PlanFitInfo` содержит размеры исходной/целевой области, коэффициенты масштаба, смещения и флаг сохранения пропорций. Методы: `is_identity(self) -> bool`, `to_dict(self) -> dict`.

```python
fit_plan_to_size(
    plan: DrawingPlan,
    target_width: int,
    target_height: int,
    *,
    preserve_aspect_ratio: bool = True,
) -> tuple[DrawingPlan, PlanFitInfo]
```

### 5.2. `drawing/execution_diagnostics.py`

- `validate_target_area(x: int, y: int, width: int, height: int, screen_width: int, screen_height: int) -> None`
- `canonical_sha256(value: Any) -> str`
- `build_execution_report(*, stage: int, source_plan_path: str | Path | None, source_plan: Any | None, executed_plan: Any | None, target_area: dict[str, int] | None, fit_info: Any | None, summary: dict[str, Any], config: dict[str, Any] | None, status: str, error: str | None = None) -> dict[str, Any]`
- `build_crash_summary(error: str) -> dict[str, Any]`
- `write_execution_report(results_dir: str | Path, report: dict[str, Any]) -> Path`

## 6. Планирование контуров и оптимизация штрихов

### 6.1. `path_planning/contour_planner.py`

`ContourSettings` — dataclass с полями `min_contour_length_px`, `epsilon_percent`, `retrieval_mode`, `foreground_mode`, `threshold`; метод `to_dict(self) -> dict`.

`ContourExtractionResult` — dataclass с полями `plan`, `contours_found`, `contours_kept`, `skipped_by_length`, `skipped_invalid`, `source_point_count`, `planned_point_count`, `source_mask`, `foreground_mask`, `settings`.

- `extract_contours(mask: Image.Image | np.ndarray, settings: ContourSettings | None = None, plan_name: str = "Contour drawing plan") -> ContourExtractionResult`
- `render_contour_preview(mask: Image.Image, plan: DrawingPlan | None) -> Image.Image`

### 6.2. `path_planning/stroke_optimizer.py`

`StrokeOptimizationSettings` — dataclass с параметрами упрощения, порядка, реверса/поворота штрихов, диагностики коротких штрихов и объединения открытых штрихов. Метод `to_dict(self) -> dict`.

`PlanMetrics` — dataclass: `stroke_count`, `point_count`, `drawing_length_px`, `pen_up_distance_px`, `estimated_move_calls`; метод `to_dict(self) -> dict`.

`OptimizationResult` — dataclass с исходным и оптимизированным планом, метриками обоих планов, количеством обнаруженных/удалённых коротких штрихов, удалённых точек и объединённых пар, а также настройками.

- `measure_plan(plan: DrawingPlan, point_step_px: float = 2.0) -> PlanMetrics`
- `optimize_plan(plan: DrawingPlan, settings: StrokeOptimizationSettings | None = None) -> OptimizationResult`
- `render_plan_preview(plan: DrawingPlan, max_dimension: int = 1600) -> Image.Image`

## 7. Общие геометрические модели

**Источник:** `geometry_models/`. Executor импортирует модели через совместимый модуль `models.py`.

- `Point(x: float, y: float)`
  - `distance_to(self, other: Point) -> float`;
  - `to_dict(self) -> dict[str, float]`;
  - `from_dict(cls, data: dict) -> Point`.
- `Stroke(name: str, points: list[Point], closed: bool = False, metadata: dict[str, str] = {})`
  - `iter_segments(self) -> Iterator[tuple[Point, Point]]`;
  - `length_px(self) -> float`;
  - `to_dict(self) -> dict`;
  - `from_dict(cls, data: dict) -> Stroke`.
- `DrawingPlan(width: int, height: int, strokes: list[Stroke], name: str = "Test drawing plan", created_at: str = ..., schema_version: int = 1)`
  - `validate_bounds(self) -> None`;
  - свойства `stroke_count`, `total_drawing_length_px`, `pen_up_distance_px`;
  - `estimated_move_calls(self, point_step_px: float = 2.0) -> int`;
  - `to_dict(self) -> dict`, `save(self, path: str | Path) -> None`;
  - `from_dict(cls, data: dict) -> DrawingPlan`, `load(cls, path: str | Path) -> DrawingPlan`.

Общие модели и формат JSON также описаны в [DATA_FORMATS_AND_MODELS.md](DATA_FORMATS_AND_MODELS.md).

## 8. Общий конвейер обработки изображений

**Источник:** `shared_image_processing/pipeline.py`.  
**Адаптер executor:** `source/executor/image_processing/pipeline.py`.

Адаптер экспортирует через `__all__`:

- `FitMode`, `ThresholdMode`;
- `ProcessingResult`, `ProcessingSettings`;
- `fit_to_canvas`, `load_rgb_image`, `process_image`.

Основные интерфейсы:

- `load_rgb_image(path: str | Path) -> Image.Image`;
- `fit_to_canvas(image: Image.Image, target_width: int, target_height: int, fit_mode: FitMode) -> Image.Image`;
- `process_image(image: Image.Image, target_width: int, target_height: int, fit_mode: FitMode = "contain", crop_box: tuple[int, int, int, int] | None = None, settings: ProcessingSettings | None = None) -> ProcessingResult`.

`ProcessingSettings` и `ProcessingResult` — dataclass; `FitMode` принимает `contain`, `cover`, `stretch`; `ThresholdMode` — `manual`, `otsu`.

## 9. Границы и актуализация

- Сигнатуры без аннотаций в исходниках не получают придуманных типов.
- Приватные методы UI и executor не перечисляются как внешний API, если они не нужны для навигации по интеграции.
- Вызовы приватных методов из `integrated_app.py` описаны в [UI_INTEGRATION_MAP.md](UI_INTEGRATION_MAP.md) как фактические точки соединения.
- Legacy Stage 1–5 не следует путать с актуальной интеграционной точкой Stage6.
- Изменения API в исходниках требуют синхронного обновления этого справочника и [MODULE_REFERENCE.md](MODULE_REFERENCE.md).

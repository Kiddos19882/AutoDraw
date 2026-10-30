# Справочник API: preparation

**Область:** `AutoDraw_Stage20/source/preparation/`  
**Назначение:** структурный перечень объявленных интерфейсов модулей подготовки.  
**Источник:** сигнатуры и docstrings исходников ветки `feature/image-geometry-optimization`.  
**Ограничение:** документ не описывает алгоритмы, не оценивает поведение и не подтверждает корректность реализации.

## Правила чтения

- Сигнатуры приведены по объявлениям Python; внутренние функции с префиксом `_` не считаются публичным API.
- Для Tkinter-классов указаны классы-компоненты; методы интерфейса здесь не перечислены, если их контракт не вынесен в docstring.
- Типы, названия параметров и значения по умолчанию отражают исходники на момент документирования.
- `Any` и `dict[str, Any]` оставлены без предположений о полном составе полей.
- Модули-совместимые импорты повторно не объявляют API: первоисточник указан отдельно.

## 1. Обработка изображений

### `image_processing/`

Пакет содержит совместимые экспорты общего конвейера из `shared_image_processing`. Файл `pipeline.py` реэкспортирует:

- `FitMode`
- `ThresholdMode`
- `ProcessingResult`
- `ProcessingSettings`
- `fit_to_canvas`
- `load_rgb_image`
- `process_image`

`_validate_crop_box` импортируется внутри compatibility-модуля, но не включён в `__all__`. Определения и сигнатуры этих сущностей следует сверять в `source/shared_image_processing/`, а не считать локальными реализациями preparation.

## 2. Проект и модели ресурсов

### `autodraw_project.py`

- `ProjectFormatError(ValueError)` — исключение формата проекта.
- `ProjectBundle` — объект открытого набора проекта.
- `create_project(output_path, ...)` — создание portable-проекта; полный контракт параметров расположен в исходнике.
- `open_project(path: str | Path) -> ProjectBundle` — открытие проекта.
- `export_drawing_plan(project_path: str | Path, destination_path: str | Path) -> Path` — экспорт плана в отдельный JSON.
- `extract_project(project_path: str | Path, destination_dir: str | Path, *, overwrite: bool = False) -> Path` — извлечение проекта.
- `project_summary(bundle: ProjectBundle) -> str` — текстовое представление сводки.

Вспомогательные функции с префиксом `_` не являются внешним API.

### `board_resource_model.py`

- `get_board_point_limit(board_item_type: str) -> int`
- `create_board_resource_profile(max_points: int, ...)`
- `estimate_calibrated_point_usage(stroke_lengths_px: Iterable[float], ...)`

Модуль также содержит внутренние функции валидации чисел и лимита.

## 3. Палитра и преобразование изображения

### `palette_detection.py`

- `rgb_to_hex(rgb: Iterable[int]) -> str`
- `parse_hex_color(value: str) -> tuple[int, int, int]`
- `sample_color_at(image: Image.Image, x: int, y: int, *, radius: int = 2) -> tuple[int, int, int]`
- `build_palette_entry(image: Image.Image, local_x: int, local_y: int, *, origin_x: int = 0, origin_y: int = 0, source: str = "manual", name: str | None = None, radius: int = 2) -> dict[str, Any]`
- `detect_color_candidates(region_image: Image.Image, *, origin_x: int = 0, origin_y: int = 0, min_area: int = 40, min_dimension: int = 6, max_dimension: int = 180, saturation_threshold: int = 35) -> list[dict[str, Any]]`
- `merge_palette_entries(current: list[dict[str, Any]], incoming: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]`
- `validate_palette_document(document: Any) -> dict[str, Any]`
- `create_palette_document(colors: list[dict[str, Any]], *, screen_size: tuple[int, int], region: dict[str, int], metadata: dict[str, Any] | None = None) -> dict[str, Any]`
- `save_palette(path: str | Path, document: dict[str, Any]) -> Path`
- `load_palette(path: str | Path) -> dict[str, Any]`
- `PaletteFormatError(ValueError)` — исключение формата палитры.

### `palette_profiles.py`

- `PaletteProfileError(ValueError)`
- `get_windows_scale_percent(default: int = 100) -> int`
- `create_palette_profile(palette_document: dict[str, Any], profile_name: str, *, browser_label: str = "", dpi_scale_percent: int = 100, notes: str = "", previous_profile: dict[str, Any] | None = None) -> dict[str, Any]`
- `validate_palette_profile(document: Any) -> dict[str, Any]`
- `palette_document_from_profile(document: dict[str, Any]) -> dict[str, Any]`
- `save_palette_profile(path: str | Path, document: dict[str, Any]) -> Path`
- `load_palette_profile(path: str | Path) -> dict[str, Any]`
- `check_profile_freshness(document: dict[str, Any], *, current_screen_size: tuple[int, int] | None, current_region: dict[str, int] | None = None, current_dpi_scale_percent: int | None = None, observed_colors: dict[str, Iterable[int]] | None = None, rgb_tolerance: int = 16) -> dict[str, Any]`
- `sample_profile_colors(document: dict[str, Any], region_image: Image.Image, *, rgb_tolerance: int = 16) -> dict[str, Any]`
- `check_profile_against_screenshot(document: dict[str, Any], screenshot: Image.Image, *, current_dpi_scale_percent: int | None = None, rgb_tolerance: int = 16) -> dict[str, Any]`

### `palette_quantization.py`

- `PaletteQuantizationError(ValueError)`
- `PaletteQuantizationResult` — структура результата преобразования.
- `BackgroundRemovalResult` — структура результата обработки фона.
- `normalize_palette(colors: Iterable[dict[str, Any] | list[int] | tuple[int, int, int]]) -> list[dict[str, Any]]`
- `rgb_to_lab(rgb: np.ndarray | Iterable[float]) -> np.ndarray`
- `delta_e_ciede2000(lab1: np.ndarray | Iterable[float], lab2: np.ndarray | Iterable[float]) -> np.ndarray`
- `remove_edge_connected_background(image: Image.Image, *, background_rgb: tuple[int, int, int] = (255, 255, 255), tolerance: int = 24) -> BackgroundRemovalResult`
- `quantize_image_to_palette(image: Image.Image, palette: Any, *, chunk_pixels: int = 8192) -> PaletteQuantizationResult`
- `merge_rare_palette_colors(result: PaletteQuantizationResult, palette: Any, *, min_pixel_count: int = 20, min_percentage: float = 0.05, max_delta_e: float = 8.0, min_frequency_ratio: float = 2.0) -> tuple[PaletteQuantizationResult, dict[str, Any]]`
- `remove_white_palette_pixels(result: PaletteQuantizationResult, palette: Any, source_image: Image.Image, *, tolerance: int = 24, threshold_percentage: float | None = None) -> tuple[PaletteQuantizationResult, dict[str, Any]]`
- `optimize_short_scanline_runs(result: PaletteQuantizationResult, palette: Any, *, min_run_length: int = 3, max_delta_e: float = 8.0, min_frequency_ratio: float = 1.25, max_passes: int = 2) -> tuple[PaletteQuantizationResult, dict[str, Any]]`

### `palette_reduction.py`

- `select_representative_palette_colors(colors: list[dict[str, Any]], target_count: int = 32, *, max_iterations: int = 20, required_hex_colors: tuple[str, ...] = ("#FFFFFF", "#000000")) -> tuple[list[dict[str, Any]], dict[str, Any]]`

## 4. Планирование цветных и геометрических планов

### `color_scanline.py`

- `ColorScanlinePlanError(ValueError)`
- `build_color_scanline_plan(index_map: Any, ...)`
- `validate_color_scanline_plan(plan: Any) -> dict[str, Any]`
- `save_color_scanline_plan(path: str | Path, plan: dict[str, Any]) -> Path`
- `load_color_scanline_plan(path: str | Path) -> dict[str, Any]`
- `render_color_scanline_preview(plan: dict[str, Any], *, max_dimension: int = 1200, expand_single_pixel_strokes: bool = False) -> Image.Image`

### `geometry_color_plan.py`

- `GeometryColorPlanError(ValueError)`
- `build_geometry_color_plan(index_map: Any, ...)`
- `validate_geometry_color_plan(plan: Any) -> dict[str, Any]`
- `render_geometry_color_preview(plan: Any, max_dimension: int = 1600) -> Image.Image`
- `save_geometry_color_plan(path: str | Path, plan: Any) -> Path`
- `load_geometry_color_plan(path: str | Path) -> dict[str, Any]`

### `geometry_budget_optimizer.py`

- `measure_geometry_plan_quality(index_map: Any, plan: dict[str, Any]) -> dict[str, Any]`
- `optimize_geometry_plan_to_budget(index_map: Any, ...)`
- `optimize_geometry_plan_across_modes(index_map: Any, ...)`

### `interior_fill_planner.py`

- `InteriorFillError(ValueError)`
- `build_interior_fill_plan(index_map: Any, *, max_brush_value: int = 20, min_brush_value: int = 2, brush_scale_x: float = 1.0, brush_scale_y: float = 1.0, fallback_merge_gap_px: int = 3) -> dict[str, Any]`

### `outline_first_fill_planner.py`

- `build_outline_first_fill_plan(index_map: Any, *, max_brush_value: int = 20, min_brush_value: int = 2, brush_scale_x: float = 1.0, brush_scale_y: float = 1.0, fallback_merge_gap_px: int = 3) -> dict[str, Any]`

### `multi_board_splitter.py`

- `split_geometry_plan_to_boards(plan: Any, *, paint_budget_px_equivalent: float, target_usage_percent: float = 75.0, stroke_overhead_px_equivalent: float = 6.67, min_tile_size: int = 24, max_boards: int = 64, board_width: int = 660, board_height: int = 340) -> dict[str, Any]`
- `save_multi_board_manifest(path: str | Path, manifest: Any) -> Path`

### `brush_planner.py`

- `BrushPlannerError(ValueError)`
- `build_adaptive_brush_plan(index_map: Any, ...)`
- `validate_adaptive_brush_plan(plan: Any) -> dict[str, Any]`
- `save_adaptive_brush_plan(path: str | Path, plan: Any) -> Path`
- `load_adaptive_brush_plan(path: str | Path) -> dict[str, Any]`

## 5. Геометрия, кисть и порядок штрихов

### `brush_calibration.py`

- `BrushCalibrationError(ValueError)`
- `create_default_profile(screen_size: tuple[int, int] | list[int] | None = None, ...)`
- `normalize_point(x: Any, ...)`
- `normalize_region(x1: Any, ...)`
- `validate_profile(profile: dict[str, Any]) -> dict[str, Any]`
- `adapt_profile_to_screen(profile: dict[str, Any], ...)`
- `missing_required_fields(profile: dict[str, Any], ...)`
- `save_profile(path: str | Path, profile: dict[str, Any]) -> Path`
- `load_profile(path: str | Path) -> dict[str, Any]`

### `brush_footprint_geometry.py`

- `footprint_pixel_bounds(x_start: float, ...)`

### `swept_footprint_geometry.py`

- `check_swept_footprint(index_map: Any, points: Iterable[Any], *, color_index: int, brush_value: int = 1, scale_x: float = 1.0, scale_y: float = 1.0) -> dict[str, Any]`

### `stroke_order_optimizer.py`

- `orient_and_order_strokes(strokes: list[dict[str, Any]], color_grouping: bool) -> list[dict[str, Any]]`

### `stroke_simplification.py`

- `simplify_path(points: list[tuple[float, float]], *, closed: bool, tolerance_px: float, safe_mask: np.ndarray | None) -> list[tuple[float, float]]`

### `skeletonization.py`

- `SkeletonizationError(ValueError)`
- `thin_binary_mask(mask: np.ndarray) -> np.ndarray`
- `trace_skeleton_paths(skeleton: np.ndarray) -> list[tuple[list[tuple[float, float]], bool]]`

### `layer_segmentation.py`

- `LayerSegmentationError(ValueError)`
- `filter_small_components(mask: np.ndarray, min_component_area: int) -> tuple[np.ndarray, int]`

## 6. Модели затрат и калибровки ресурсов

### `paint_cost_model.py`

- `estimate_paint_cost(drawing_length_px: float, stroke_count: int, single_pixel_stroke_count: int = 0, *, stroke_overhead_px_equivalent: float = DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT, paint_budget_px_equivalent: float = DEFAULT_PAINT_BUDGET_PX_EQUIVALENT) -> dict[str, Any]`
- `estimate_color_plan_paint_cost(plan: dict[str, Any], *, stroke_overhead_px_equivalent: float = DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT, paint_budget_px_equivalent: float = DEFAULT_PAINT_BUDGET_PX_EQUIVALENT) -> dict[str, Any]`
- `fit_model_to_calibration_observations(observations: Iterable[dict[str, Any]] = CALIBRATION_OBSERVATIONS) -> dict[str, float | int]`

### `paint_budget_optimizer.py`

- `PaintBudgetOptimizationError(ValueError)`
- `fit_result_to_paint_budget(result: PaletteQuantizationResult, palette: Any, *, paint_budget_px_equivalent: float = DEFAULT_PAINT_BUDGET_PX_EQUIVALENT, stroke_overhead_px_equivalent: float = DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT, target_usage_percent: float = 75.0, board_item_type: str = "BoardItem2", board_point_limit: int = HISTORICAL_CALIBRATION_POINT_LIMIT, point_step_px: float = DEFAULT_EXECUTOR_POINT_STEP_PX, point_delay_ms: float = DEFAULT_EXECUTOR_POINT_DELAY_MS, frame_rate_fps: float = GAME_ENGINE_DEFAULT_FRAME_RATE_FPS, point_quota_safety_factor: float = DEFAULT_POINT_SAFETY_FACTOR) -> tuple[PaletteQuantizationResult, int, int, dict[str, Any]]`

### `interval_quota_fit.py`

- `fit_interval_censored_quota(midpoint_matrix: np.ndarray, visible_lengths: np.ndarray, visible_strokes: np.ndarray, stroke_lengths: np.ndarray, quota: float, midpoint_coefficients: np.ndarray) -> dict[str, Any]`

### `engine_point_calibration.py`

- `estimate_theoretical_points_per_path_px(*, point_step_px: float = DEFAULT_EXECUTOR_POINT_STEP_PX, point_delay_ms: float = DEFAULT_EXECUTOR_POINT_DELAY_MS, frame_rate_fps: float = GAME_ENGINE_DEFAULT_FRAME_RATE_FPS) -> float`
- `build_engine_point_calibration_report(observations: Iterable[dict[str, Any]] = CALIBRATION_OBSERVATIONS, *, point_step_px: float = DEFAULT_EXECUTOR_POINT_STEP_PX, point_delay_ms: float = DEFAULT_EXECUTOR_POINT_DELAY_MS, frame_rate_fps: float = GAME_ENGINE_DEFAULT_FRAME_RATE_FPS, calibration_point_limit: int | None = HISTORICAL_CALIBRATION_POINT_LIMIT, calibration_point_step_px: float | None = HISTORICAL_CALIBRATION_POINT_STEP_PX, calibration_point_delay_ms: float | None = HISTORICAL_CALIBRATION_POINT_DELAY_MS, calibration_frame_rate_fps: float | None = HISTORICAL_CALIBRATION_FRAME_RATE_FPS) -> dict[str, Any]`
- `estimate_point_quota_usage(drawing_length_px: float, stroke_count: int, *, board_point_limit: int, single_pixel_stroke_count: int = 0, point_step_px: float = DEFAULT_EXECUTOR_POINT_STEP_PX, point_delay_ms: float = DEFAULT_EXECUTOR_POINT_DELAY_MS, frame_rate_fps: float = GAME_ENGINE_DEFAULT_FRAME_RATE_FPS, calibration_point_limit: int | None = HISTORICAL_CALIBRATION_POINT_LIMIT, calibration_point_step_px: float | None = HISTORICAL_CALIBRATION_POINT_STEP_PX, calibration_point_delay_ms: float | None = HISTORICAL_CALIBRATION_POINT_DELAY_MS, calibration_frame_rate_fps: float | None = HISTORICAL_CALIBRATION_FRAME_RATE_FPS, safety_factor: float = DEFAULT_POINT_SAFETY_FACTOR) -> dict[str, Any]`

### `game_point_calibration.py`

- `GamePointCalibrationError(ValueError)`
- `analyze_game_point_calibration(document: Any) -> dict[str, Any]`

## 7. Сбор и хранение экспериментальных записей

### `paint_limit_test.py`

- `PaintLimitTestError(ValueError)`
- `build_paint_limit_test_plan(profile_document: dict[str, Any], *, canvas_width: int, canvas_height: int, color_hex: str, scenario_id: str, target_total_drawing_length_px: int = 800, row_spacing_px: int = 3, experiment_id: str = "", margin_px: int = 3) -> dict[str, Any]`
- `make_paint_limit_observation(plan: dict[str, Any], *, outcome: str, last_visible_strokes: int | None = None, notes: str = "", fresh_supply_confirmed: bool = False) -> dict[str, Any]`
- `append_paint_limit_observation(path: str | Path, record: dict[str, Any]) -> Path`
- `analyze_paint_limit_series(records: list[dict[str, Any]], experiment_id: str) -> str`
- `analyze_paint_limit_pair(records: list[dict[str, Any]], experiment_id: str) -> str`

### `brush_experiment_capture.py`

- `crop_calibrated_regions(screen: Image.Image, regions: dict[str, Any]) -> dict[str, Image.Image]`
- `compare_images(first: Image.Image, second: Image.Image) -> dict[str, Any]`
- `measure_meter_fill_against_baseline(baseline: Image.Image, current: Image.Image, *, color_distance_threshold: float = 24.0, minimum_changed_suffix_fraction: float = 0.03) -> dict[str, Any]`
- `evaluate_meter_restoration(baseline: Image.Image, after_clear: Image.Image, *, tolerance_fraction: float = .03) -> dict[str, Any]`
- `evaluate_board_clear(blank_reference: Image.Image, after_clear: Image.Image, *, tolerance_percent: float = 0.15) -> dict[str, Any]`
- `measure_stroke_visibility(blank_reference: Image.Image, current: Image.Image, strokes: list[dict[str, Any]], *, padding_px: int = 4, color_distance_threshold: float = 24.0, minimum_changed_pixels: int = 2) -> dict[str, Any]`

### `brush_test_workflow.py`

- `BrushWorkflowError(RuntimeError)`
- `should_run_postdraw_workflow(execution_status: object) -> bool`
- `calculate_slider_target(start_30: tuple[int, int] | list[int], end_1: tuple[int, int] | list[int], brush_value: int) -> tuple[int, int]`
- `validate_observed_brush_radius(requested_brush: int, observed_radii: object) -> dict[str, Any]`
- `validate_brush_test_preflight(profile: dict[str, Any] | None, screen_size: tuple[int, int], *, brush_control: dict[str, Any] | None = None, require_slider: bool = True) -> dict[str, Any]`
- `BrushExperimentState` — структура состояния workflow.

## 8. UI-компоненты и точки входа

Следующие классы являются UI-компонентами подготовки на Tkinter/ttk. Их публичная точка подключения — создание соответствующего класса в родительском приложении:

| Модуль | Класс | Назначение по docstring |
|---|---|---|
| `brush_calibration_ui.py` | `ScreenPointPicker` | Выбор экранной точки |
| `brush_calibration_ui.py` | `ScreenRegionPicker` | Выбор экранной области |
| `brush_calibration_ui.py` | `BrushCalibrationTab` | Вкладка калибровки кисти |
| `brush_behavior_test_ui.py` | `BrushBehaviorTestTab` | Интерфейс ручной матрицы испытаний кисти и хранения записей |
| `color_scanline_ui.py` | `ColorScanlineTab` | Вкладка цветного scanline-плана |
| `palette_detection_ui.py` | `ScreenRegionPicker` | Выбор области скриншота |
| `palette_detection_ui.py` | `PaletteDetectionTab` | Вкладка обнаружения палитры |
| `palette_quantization_ui.py` | `PaletteQuantizationTab` | Вкладка квантования палитры |
| `paint_limit_test_ui.py` | `PaintLimitTestTab` | Вкладка записей испытаний лимита |
| `stage13_workbench.py` | `ImagePreview` | Предпросмотр изображения с масштабированием и выбором crop |
| `stage13_workbench.py` | `AutoDrawWorkbench` | Основное окно workbench |

Дополнительные экспортируемые функции UI/служебных модулей:

- `palette_detection_ui.map_display_rect_to_image(rect, *, source_size, display_size, offset=(0.0, 0.0)) -> tuple[int, int, int, int]`
- `brush_behavior_test_ui.summarize_game_monitor_report(document, requested_brush_value=None) -> dict[str, Any]`
- `brush_behavior_test_ui.build_brush_test_record(*, brush_value, test_case, ... ) -> dict[str, Any]`
- `brush_behavior_test_ui.build_brush_test_drawing_plan(test_case: str, canvas_size: tuple[int, int]) -> dict[str, Any]`
- `stage13_workbench.main() -> None` — точка запуска workbench.

## 9. Утилиты предыдущих этапов

### `stage8_optimizer.py`

- `TimingProfile`, `PlanMetrics` — структуры данных.
- `load_json(path: str | Path) -> dict[str, Any]`
- `get_strokes(plan)`
- `analyze_plan(plan, profile=TimingProfile())`
- `load_mask(path)`
- `build_scanline_plan(mask, row_step_px=1, threshold=127, foreground='dark', max_strokes=250_000)`
- `render_plan_preview(plan, scale_limit=1000)`
- `save_plan(path, plan)`

### `stage9_quality.py`

- `QualityReport` — структура отчёта.
- `load_mask(path: str | Path) -> Image.Image`
- `load_plan(path: str | Path) -> dict[str, Any]`
- `plan_dimensions(plan: dict[str, Any]) -> tuple[int, int]`
- `make_binary_mask(image: Image.Image, threshold: int = 127, foreground: str = 'dark') -> Image.Image`
- `render_plan(plan: dict[str, Any]) -> tuple[Image.Image, int, int, int]`
- `analyze_quality(mask: Image.Image, plan: dict[str, Any], threshold: int = 127, foreground: str = 'dark') -> tuple[QualityReport, Image.Image, Image.Image, Image.Image]`
- `save_report(path: str | Path, report: QualityReport) -> None`

### `drawing_algorithm_benchmark.py`

- `load_palette_document(path: str | Path) -> tuple[list[dict[str, Any]], dict[str, Any]]`
- `render_plan_index_map(plan: dict[str, Any]) -> np.ndarray`
- `summarize_plan(name: str, plan: dict[str, Any], source_index_map: Any, *, board_item_type: str = "BoardItem2", point_step_px: float = DEFAULT_EXECUTOR_POINT_STEP_PX, point_delay_ms: float = DEFAULT_EXECUTOR_POINT_DELAY_MS, frame_rate_fps: float = GAME_ENGINE_DEFAULT_FRAME_RATE_FPS, safety_factor: float = DEFAULT_POINT_SAFETY_FACTOR, paint_budget_px_equivalent: float = DEFAULT_PAINT_BUDGET_PX_EQUIVALENT, stroke_overhead_px_equivalent: float = DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT) -> dict[str, Any]`
- `render_index_map_png(index_map: Any, palette: list[dict[str, Any]]) -> Image.Image`

## 10. Пробелы в детализации

Этот документ фиксирует API-контуры, но не заменяет полные Python type stubs. Для функций, у которых в перечне после параметров стоит `...`, полная сигнатура должна быть взята непосредственно из исходника при интеграции. Для классов UI публичные методы и события отдельно не инвентаризированы.

Следующие отдельные документы должны раскрыть структуры сохранённых данных и связи компонентов:

- профили палитры, кисти, рабочей области и калибровки;
- JSON-планы scanline, geometry и adaptive brush;
- manifest разбиения на доски и записи экспериментов;
- карта импортов и точки подключения UI.

## 11. Границы документирования

Не рассматриваются: внутреннее устройство алгоритмов, причины выбора параметров, точность результатов, производительность, безопасность, качество планов, browser/game runtime и результаты экспериментов. Наличие функции в перечне не является утверждением о корректности её работы.

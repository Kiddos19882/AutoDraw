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
- `create_project(output_path: str | Path, source_image_path: str | Path, mask_path: str | Path, drawing_plan_path: str | Path, *, project_name: str | None = None, processing_metadata_path: str | Path | None = None, imported_quality_report_path: str | Path | None = None, prepared_color_path: str | Path | None = None, grayscale_path: str | Path | None = None, quality_threshold: int | None = None, quality_foreground: str | None = None) -> Path` — создание portable-проекта.
- `open_project(path: str | Path) -> ProjectBundle` — открытие проекта.
- `export_drawing_plan(project_path: str | Path, destination_path: str | Path) -> Path` — экспорт плана в отдельный JSON.
- `extract_project(project_path: str | Path, destination_dir: str | Path, *, overwrite: bool = False) -> Path` — извлечение проекта.
- `project_summary(bundle: ProjectBundle) -> str` — текстовое представление сводки.

Вспомогательные функции с префиксом `_` не являются внешним API.

### `board_resource_model.py`

- `get_board_point_limit(board_item_type: str) -> int`
- `create_board_resource_profile(max_points: int, *, safety_factor: float = DEFAULT_POINT_SAFETY_FACTOR) -> dict[str, Any]`
- `estimate_calibrated_point_usage(stroke_lengths_px: Iterable[float], *, points_per_path_px: float, max_points: int, safety_factor: float = DEFAULT_POINT_SAFETY_FACTOR) -> dict[str, Any]`

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
- `build_color_scanline_plan(index_map: Any, palette: Any, *, source_report: dict[str, Any] | None = None, source_name: str | None = None, plan_name: str = "Цветной scanline-план", row_step_px: int = 1, row_offset_px: int = 0, max_strokes: int = MAX_COLOR_STROKES, paint_stroke_overhead_px_equivalent: float = DEFAULT_STROKE_OVERHEAD_PX_EQUIVALENT, paint_budget_px_equivalent: float = DEFAULT_PAINT_BUDGET_PX_EQUIVALENT, board_item_type: str = "BoardItem2", board_point_limit: int = HISTORICAL_CALIBRATION_POINT_LIMIT, point_step_px: float = DEFAULT_EXECUTOR_POINT_STEP_PX, point_delay_ms: float = DEFAULT_EXECUTOR_POINT_DELAY_MS, frame_rate_fps: float = GAME_ENGINE_DEFAULT_FRAME_RATE_FPS, point_quota_safety_factor: float = DEFAULT_POINT_SAFETY_FACTOR) -> dict[str, Any]`
- `validate_color_scanline_plan(plan: Any) -> dict[str, Any]`
- `save_color_scanline_plan(path: str | Path, plan: dict[str, Any]) -> Path`
- `load_color_scanline_plan(path: str | Path) -> dict[str, Any]`
- `render_color_scanline_preview(plan: dict[str, Any], *, max_dimension: int = 1200, expand_single_pixel_strokes: bool = False) -> Image.Image`

### `geometry_color_plan.py`

- `GeometryColorPlanError(ValueError)`
- `build_geometry_color_plan(index_map: Any, palette: Any, *, mode: str = "skeleton", simplify_tolerance_px: float = 0.8, min_component_area: int = 1, color_grouping: bool = True, max_strokes: int = MAX_GEOMETRY_STROKES, canvas_size: tuple[int, int] | None = None, source_tile: dict[str, int] | None = None, source_name: str | None = None) -> dict[str, Any]`
- `validate_geometry_color_plan(plan: Any) -> dict[str, Any]`
- `render_geometry_color_preview(plan: Any, max_dimension: int = 1600) -> Image.Image`
- `save_geometry_color_plan(path: str | Path, plan: Any) -> Path`
- `load_geometry_color_plan(path: str | Path) -> dict[str, Any]`

### `geometry_budget_optimizer.py`

- `measure_geometry_plan_quality(index_map: Any, plan: dict[str, Any]) -> dict[str, Any]`
- `optimize_geometry_plan_to_budget(index_map: Any, palette: Any, *, mode: str, paint_budget_px_equivalent: float, target_usage_percent: float = 75.0, stroke_overhead_px_equivalent: float = 6.67, simplify_tolerance_px: float = 0.8, min_component_area: int = 1, source_name: str | None = None, board_point_limit: int = 6_000, point_safety_factor: float = 0.85) -> tuple[dict[str, Any], dict[str, Any]]`
- `optimize_geometry_plan_across_modes(index_map: Any, palette: Any, *, paint_budget_px_equivalent: float, target_usage_percent: float = 75.0, stroke_overhead_px_equivalent: float = 6.67, simplify_tolerance_px: float = 0.8, min_component_area: int = 1, source_name: str | None = None, board_point_limit: int = 6_000, point_safety_factor: float = 0.85) -> tuple[dict[str, Any], dict[str, Any]]`

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
- `build_adaptive_brush_plan(index_map: Any, color_plan: dict[str, Any], *, brush_scale_x: float = 1.0, brush_scale_y: float = 1.0, min_brush_value: int = DEFAULT_MIN_BRUSH_VALUE, max_brush_value: int = DEFAULT_MAX_BRUSH_VALUE, calibration_confirmed: bool = False) -> dict[str, Any]`
- `validate_adaptive_brush_plan(plan: Any) -> dict[str, Any]`
- `save_adaptive_brush_plan(path: str | Path, plan: Any) -> Path`
- `load_adaptive_brush_plan(path: str | Path) -> dict[str, Any]`

## 5. Профили рабочей области и настройки

### `profile_manager.py`

Модуль объявляет следующие dataclass и хранилище:

- `ProfileValidationError(ValueError)` — ошибка проверки профиля.
- `ScreenArea(x: int, y: int, width: int, height: int, screen_width: int | None = None, screen_height: int | None = None)`; методы `validate() -> None`, `to_dict() -> dict[str, int]`, `from_dict(data: dict[str, Any]) -> ScreenArea`.
- `CalibrationSettings(point_step_px: float = 2.0, point_delay_ms: int = 10, after_mouse_up_ms: int = 20, before_mouse_down_ms: int = 20, after_mouse_down_ms: int = 40, end_hold_ms: int = 50, countdown_seconds: int = 5)`; методы `validate() -> None`, `to_dict() -> dict[str, int | float]`, `from_dict(data: dict[str, Any] | None) -> CalibrationSettings`, `to_stage6_settings() -> dict[str, int | float]`.
- `WorkspaceProfile(profile_id: str, name: str, canvas_width: int = 646, canvas_height: int = 323, fit_mode: str = "contain", brightness: int = 0, contrast: float = 1.0, denoise_level: int = 0, threshold_mode: str = "otsu", threshold: int = 128, row_step_px: int = 1, screen_area: ScreenArea | None = None, calibration: CalibrationSettings = CalibrationSettings(), notes: str = "", created_at: str = "", updated_at: str = "")`.
  - `create_default(name: str = "Основной") -> WorkspaceProfile`
  - `validate() -> None`
  - `to_dict() -> dict[str, Any]`
  - `from_dict(data: dict[str, Any]) -> WorkspaceProfile`
  - `from_external_dict(data: dict[str, Any], *, name: str | None = None) -> WorkspaceProfile`
  - `to_canvas_profile() -> dict[str, int]`
  - `to_stage6_target_profile() -> dict[str, dict[str, int]]`
  - `to_stage6_settings() -> dict[str, int | float]`
- `ProfileStore(path: str | Path)` — объект доступа к файлу набора профилей; методы `load() -> list[WorkspaceProfile]`, `save_all(profiles: list[WorkspaceProfile]) -> None`, `upsert(profile: WorkspaceProfile) -> list[WorkspaceProfile]`, `delete(profile_id: str) -> list[WorkspaceProfile]`.
- `ProfileStore.export_json(path: str | Path, payload: dict[str, Any]) -> Path` — статический метод экспорта JSON.

`PROFILE_SCHEMA_VERSION`, `FIT_MODES`, `THRESHOLD_MODES` и `DEFAULT_EXECUTION_SETTINGS` — публичные константы модуля.

## 6. Геометрия, кисть и порядок штрихов

### `brush_calibration.py`

- `BrushCalibrationError(ValueError)`
- `create_default_profile(screen_size: tuple[int, int] | list[int] | None = None) -> dict[str, Any]`
- `normalize_point(x: Any, y: Any, screen_size: tuple[int, int] | list[int] | None = None) -> dict[str, int]`
- `normalize_region(x1: Any, y1: Any, x2: Any, y2: Any, screen_size: tuple[int, int] | list[int] | None = None, *, min_width: int = 2, min_height: int = 2) -> dict[str, int]`
- `validate_profile(profile: dict[str, Any]) -> dict[str, Any]`
- `adapt_profile_to_screen(profile: dict[str, Any], screen_size: tuple[int, int] | list[int]) -> tuple[dict[str, Any], bool]`
- `missing_required_fields(profile: dict[str, Any], brush_value: int | None = None) -> list[str]`
- `save_profile(path: str | Path, profile: dict[str, Any]) -> Path`
- `load_profile(path: str | Path) -> dict[str, Any]`

### `brush_footprint_geometry.py`

- `footprint_pixel_bounds(x_start: float, x_end: float, y: float, brush_value: int, scale_x: float, scale_y: float, width: int, height: int) -> tuple[int, int, int, int] | None`

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

## 7. Модели затрат и калибровки ресурсов

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

## 8. Сбор и хранение экспериментальных записей

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

## 9. UI-компоненты и точки входа

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
- `brush_behavior_test_ui.build_brush_test_record(*, brush_value: int, test_case: str, canvas_area: dict[str, int] | None = None, screen_area: dict[str, int] | None = None, screenshot_path: str | None = None, drawing_plan_path: str | None = None, drawing_plan: dict[str, Any] | None = None, execution_report_path: str | None = None, execution_report: dict[str, Any] | None = None, measurements: dict[str, Any] | None = None, notes: str = "", outcome: str = "not_reviewed", screen_resolution: dict[str, int] | None = None, brush_control: dict[str, Any] | None = None, game_monitor_report_path: str | None = None, game_monitor_summary: dict[str, Any] | None = None) -> dict[str, Any]`
- `brush_behavior_test_ui.build_brush_test_drawing_plan(test_case: str, canvas_size: tuple[int, int]) -> dict[str, Any]`
- `stage13_workbench.main() -> None` — точка запуска workbench.


### 8.1. Методы UI-классов

Сигнатуры ниже отражают объявления исходников. Методы с подчёркиванием в начале имени перечислены для полноты структуры класса; само наличие в справочнике не означает публичную гарантию совместимости.

#### `brush_calibration_ui.py`

- `ScreenPointPicker.__init__(parent: tk.Tk, instruction: str, on_done: Callable[[tuple[int, int] | None], None])`
- `ScreenPointPicker._screen_size() -> tuple[int, int]`
- `ScreenPointPicker._motion(self, event) -> None`
- `ScreenPointPicker._select(self, event) -> None`
- `ScreenPointPicker._cancel(self, _event=None) -> None`
- `ScreenRegionPicker.__init__(parent: tk.Tk, instruction: str, on_done: Callable[[dict[str, int] | None], None])`
- `ScreenRegionPicker._motion(self, event) -> None`
- `ScreenRegionPicker._start(self, event) -> None`
- `ScreenRegionPicker._drag(self, event) -> None`
- `ScreenRegionPicker._finish(self, event) -> None`
- `ScreenRegionPicker._cancel(self, _event=None) -> None`
- `BrushCalibrationTab.__init__(root: tk.Tk, parent: tk.Widget, profile_path: str | Path, *, on_profile_saved: Callable[[dict[str, Any]], None] | None = None)`
- `BrushCalibrationTab.get_experiment_capture_config(self) -> dict[str, Any] | None`
- `BrushCalibrationTab.get_board_area(self) -> dict[str, int] | None`
- `BrushCalibrationTab.get_canvas_size(self) -> tuple[int, int] | None`
- `BrushCalibrationTab.get_brush_control(self) -> dict[str, Any] | None`
- `BrushCalibrationTab.is_ready(self, brush_value: int | None = None) -> tuple[bool, list[str]]`

Внутренние методы `BrushCalibrationTab`: `_screen_size`, `_load_initial_profile`, `_sync_environment_vars`, `_build`, `_ensure_screen_compatibility`, `_refresh_view`, `_status_label`, `_pick_point`, `_pick_region`, `_reset_point`, `_reset_region`, `_test_point`, `_preview_region`, `_show_region_preview`, `_apply_environment`, `_save`, `_save_as`, `_load_dialog`, `_reset_all`.

#### `brush_behavior_test_ui.py`

- `BrushBehaviorTestTab.__init__(self, root: tk.Misc, parent: tk.Widget, output_dir: str | Path, area_selector_cls, *, get_canvas_size, get_canvas_area, on_transfer_plan, get_brush_control=None, get_calibration_profile=None, on_brush_ready=None)`
- `BrushBehaviorTestTab.create_and_transfer_plan(self) -> None`
- `BrushBehaviorTestTab.select_screenshot_area(self) -> None`
- `BrushBehaviorTestTab.set_brush_size(self) -> bool`
- `BrushBehaviorTestTab.cancel_brush_drag(self) -> None`
- `BrushBehaviorTestTab.capture_screenshot(self) -> None`
- `BrushBehaviorTestTab.capture_blank_board_reference(self) -> None`
- `BrushBehaviorTestTab.capture_experiment_phase(self, phase: str) -> None`
- `BrushBehaviorTestTab.handle_executor_finished(self, summary: dict[str, Any], report_path: str | Path | None) -> bool`
- `BrushBehaviorTestTab.load_execution_report(self) -> None`
- `BrushBehaviorTestTab.load_game_monitor_report(self) -> None`
- `BrushBehaviorTestTab.save_record_dialog(self) -> None`

Внутренние методы класса: `_build`, `_load_brush_control_into_fields`, `_refresh_template`, `_validate_automation_preflight`, `_reset_observation_fields`, `_parse_point`, `_apply_brush_preset_click`, `_start_brush_hotkey_listener`, `_stop_brush_hotkey_listener`, `_start_scheduled_brush_drag`, `_begin_brush_drag`, `_press_and_continue_brush_drag`, `_move_brush_drag_step`, `_on_brush_workflow_stop_key`, `_finish_brush_drag`, `_confirm_brush_before_test`, `_capture_screenshot_now`, `_start_automated_preclear`, `_cancel_automated_preclear`, `_perform_automated_preclear`, `_capture_and_verify_preclear`, `_finish_automated_preclear_failure`, `_blank_board_reference_paths`, `_capture_blank_board_reference_now`, `_capture_experiment_phase_now`, `_cancel_automated_postdraw`, `_start_automated_postdraw`, `_capture_automated_after_draw`, `_capture_automated_after_clear`, `_finish_automated_postdraw`, `_schedule_brush_restore_30`, `_record_brush_restore_result`, `_show_postdraw_completion_notification`, `_write_experiment_manifest`, `_measurement_values`, `_build_record`.

#### `color_scanline_ui.py`

- `_PlanPreview.__init__(parent: tk.Widget, title: str)`
- `_PlanPreview.set_image(self, image: Image.Image | None) -> None`
- `_PlanPreview.render(self) -> None`
- `ColorScanlineTab.__init__(root: tk.Misc, parent: tk.Widget, output_dir: str | Path, get_quantized_data: Callable[[], dict[str, Any] | None])`
- `ColorScanlineTab.invalidate_source(self, reason: str) -> None`
- `ColorScanlineTab.use_latest_quantization(self) -> None`
- `ColorScanlineTab.build_plan(self) -> None`
- `ColorScanlineTab.build_geometry_plan(self) -> None`
- `ColorScanlineTab.fit_geometry_to_paint_budget(self) -> None`
- `ColorScanlineTab.split_geometry_to_boards_dialog(self) -> None`
- `ColorScanlineTab.fit_to_paint_budget(self) -> None`
- `ColorScanlineTab.save_brush_plan_dialog(self) -> None`
- `ColorScanlineTab.build_brush_recommendations(self) -> None`
- `ColorScanlineTab.reset_paint_model(self) -> None`
- `ColorScanlineTab.recalculate_paint_estimate(self) -> None`
- `ColorScanlineTab.save_plan_dialog(self) -> None`
- `ColorScanlineTab.open_plan_dialog(self) -> None`

Внутренние методы класса: `_display_built_plan`, `_display_geometry_plan`, `_parse_model_number`, `_format_paint_estimate`, `_populate_table`.

#### `palette_detection_ui.py`

- `map_display_rect_to_image(rect: tuple[float, float, float, float], *, source_size: tuple[int, int], display_size: tuple[int, int], offset: tuple[float, float] = (0.0, 0.0)) -> tuple[int, int, int, int]`
- `ScreenRegionPicker.__init__(root: tk.Misc, screenshot: Image.Image, on_selected: Callable[[tuple[int, int, int, int]], None])`
- `PaletteDetectionTab.__init__(root: tk.Misc, parent: tk.Widget, store_dir: str | Path)`
- `PaletteDetectionTab.request_screenshot(self) -> None`
- `PaletteDetectionTab.choose_region(self) -> None`
- `PaletteDetectionTab.auto_detect(self) -> None`
- `PaletteDetectionTab.edit_selected_hex(self) -> None`
- `PaletteDetectionTab.edit_selected_name(self) -> None`
- `PaletteDetectionTab.confirm_selected_color(self) -> None`
- `PaletteDetectionTab.confirm_all_colors(self) -> None`
- `PaletteDetectionTab.remove_selected(self) -> None`
- `PaletteDetectionTab.clear_colors(self) -> None`
- `PaletteDetectionTab.save_profile_dialog(self) -> None`
- `PaletteDetectionTab.load_profile_dialog(self) -> None`
- `PaletteDetectionTab.refresh_saved_profiles(self) -> None`
- `PaletteDetectionTab.load_selected_profile(self) -> None`
- `PaletteDetectionTab.delete_selected_profile(self) -> None`
- `PaletteDetectionTab.check_calibration(self) -> None`
- `PaletteDetectionTab.save_dialog(self) -> None`
- `PaletteDetectionTab.load_dialog(self) -> None`

Остальные методы классов `ScreenRegionPicker` и `PaletteDetectionTab` — внутренние обработчики выбора области, рендеринга, таблицы, профиля и скриншота: `_render`, `_clamp_canvas`, `_press`, `_drag`, `_release`, `_accept`, `_capture_screenshot`, `_open_region_picker`, `_apply_selected_region`, `_schedule_preview_render`, `_render_preview`, `_on_preview_click`, `_refresh_table`, `_selected_index`, `_ensure_palette_limit`, `_current_palette_document`, `_make_current_profile`, `_install_profile`, `_get_current_screen_size`, `_capture_calibration_screenshot`.

#### `palette_quantization_ui.py`

- `_PreviewPanel.__init__(parent: tk.Widget, title: str)`
- `_PreviewPanel.set_image(self, image: Image.Image | None) -> None`
- `_PreviewPanel.render(self) -> None`
- `PaletteQuantizationTab.__init__(root: tk.Misc, parent: tk.Widget, profile_dir: str | Path, output_dir: str | Path, get_prepared_image: Callable[[], Image.Image | None] | None = None)`
- `PaletteQuantizationTab.set_target_canvas_size(self, width: int, height: int) -> None`
- `PaletteQuantizationTab.refresh_profiles(self) -> None`
- `PaletteQuantizationTab.load_selected_profile(self) -> bool`
- `PaletteQuantizationTab.load_profile_file_dialog(self) -> None`
- `PaletteQuantizationTab.open_image_dialog(self) -> None`
- `PaletteQuantizationTab.use_prepared_image(self) -> None`
- `PaletteQuantizationTab.quantize(self) -> None`
- `PaletteQuantizationTab.save_image_dialog(self) -> None`
- `PaletteQuantizationTab.save_report_dialog(self) -> None`

Внутренние методы класса: `_update_scroll_region`, `_resize_scroll_content`, `_widget_is_in_scroll_content`, `_on_mousewheel`, `_on_mousewheel_linux`, `_set_background_mode`, `_toggle_background_tolerance`, `_toggle_rare_color_controls`, `_toggle_short_run_controls`, `_on_profile_selected`, `_read_profile`, `_format_palette_info`, `_set_source_image`, `_difference_preview`, `_populate_color_table`.

#### `paint_limit_test_ui.py`

- `PaintLimitTestTab.__init__(root: tk.Misc, parent: tk.Widget, output_dir: str | Path, profile_dir: str | Path, *, get_canvas_size: Callable[[], tuple[int, int] | None], on_transfer_plan: Callable[[dict[str, Any], dict[str, Any], Path], bool])`
- `PaintLimitTestTab.load_profile_dialog(self) -> None`
- `PaintLimitTestTab.set_profile(self, profile: dict[str, Any], path: Path | None = None) -> None`
- `PaintLimitTestTab.generate_plan(self) -> None`
- `PaintLimitTestTab.transfer_plan(self) -> None`
- `PaintLimitTestTab.new_experiment(self) -> None`
- `PaintLimitTestTab.record_observation(self) -> None`

Внутренние методы класса: `_bind_scroll_events`, `_on_mousewheel`, `_get_scenario_id`, `_on_outcome_changed`, `_render_preview`.

#### `stage13_workbench.py`

- `ImagePreview.__init__(self, parent, title: str, *, selectable: bool = False, on_selection=None)`
- `ImagePreview.set_image(self, image: Image.Image | None) -> None`
- `ImagePreview.set_selection(self, selection: tuple[int, int, int, int] | None) -> None`
- `AutoDrawWorkbench.__init__(self, root: tk.Tk, parent: tk.Widget | None = None, *, embedded: bool = False, on_select_canvas_area: Callable[[], None] | None = None)`
- `AutoDrawWorkbench.set_target_area(self, area: dict | Any, screen_size: tuple[int, int] | None = None) -> None`
- `AutoDrawWorkbench.cleanup(self) -> None`
- `main() -> None`

Внутренние методы `ImagePreview`: `_draw`, `_canvas_to_image`, `_on_press`, `_on_drag`, `_on_release`.

Внутренние методы `AutoDrawWorkbench`: `_build_ui`, `_build_image_tab`, `_build_plan_tab`, `_build_quality_tab`, `_build_project_tab`, `_build_profile_tab`, `_profile_entry_row`, `_profile_combo_row`, `_refresh_profile_combo`, `_on_profile_selected`, `_load_profile_into_form`, `_profile_from_form`, `_new_profile_from_current`, `_save_profile_from_form`, `_apply_profile_to_workbench`, `_delete_selected_profile`, `_import_profile`, `_export_profile`, `_export_canvas_profile`, `_export_stage6_target_profile`, `_export_stage6_settings`, `_set_project_details`, `_request_target_area`, `_load_image`, `_load_profile`, `_on_crop_selected`, `_reset_crop`, `_current_settings`, `_on_setting_changed`, `_on_threshold_mode_changed`, `_schedule_processing`, `_process_now`, `_build_plan`, `_check_quality`, `_safe_save_dialog`, `_save_plan_json`, `_save_quality_report`, `_processing_metadata`, `_prepare_project_files`, `_save_project`, `_open_project`, `_export_stage6_json`, `_save_processing_bundle`, `_clear_quality_previews`, `_on_close`.

### 8.2. События и callback-точки интеграции

В конструкторах UI-компонентов передаются следующие внешние зависимости:

- `BrushCalibrationTab`: `on_profile_saved` — callback с документом профиля `dict[str, Any]`.
- `BrushBehaviorTestTab`: `area_selector_cls`, `get_canvas_size`, `get_canvas_area`, `on_transfer_plan`, необязательные `get_brush_control`, `get_calibration_profile`, `on_brush_ready`.
- `ColorScanlineTab`: `get_quantized_data` — callback, возвращающий документ квантованных данных или `None`.
- `PaintLimitTestTab`: `get_canvas_size` и `on_transfer_plan` — callbacks размера холста и передачи плана.
- `PaletteQuantizationTab`: необязательный `get_prepared_image`.
- `AutoDrawWorkbench`: `on_select_canvas_area` — необязательный callback запроса выбора области холста.

Обработчики событий Tkinter/ttk, привязанные внутри классов, остаются деталями реализации UI. Внешние callback-параметры выше перечислены как явные зависимости конструкторов.

## 10. Утилиты предыдущих этапов

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

## 11. Пробелы в детализации

Сигнатуры приводятся в пределах аннотаций, фактически присутствующих в исходниках. Если в исходнике параметры не аннотированы, справочник не добавляет предполагаемые типы. Для UI-классов перечислены объявления методов и конструкторов; внутренние методы приведены для структурной навигации и не объявляются стабильным публичным контрактом. События Tkinter и callback-привязки, создаваемые внутри классов, не перечисляются как отдельный API.

Структуры профилей, цветных планов, лабораторных записей и калибровочных отчётов вынесены в [DATA_FORMATS_AND_PROFILES.md](DATA_FORMATS_AND_PROFILES.md). Оставшиеся отдельные задачи — общая карта импортов и точек подключения UI.

## 12. Границы документирования

Не рассматриваются: внутреннее устройство алгоритмов, причины выбора параметров, точность результатов, производительность, безопасность, качество планов, browser/game runtime и результаты экспериментов. Наличие функции в перечне не является утверждением о корректности её работы.

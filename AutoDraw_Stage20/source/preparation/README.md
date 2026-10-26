# Подготовка AutoDraw (этапы 12–18)

- `stage13_workbench.py`: подготовка изображения, растровый план, проект `.autodraw` и проверка качества.
- `palette_detection.py`, `palette_detection_ui.py`: обнаружение цветов браузерной палитры и ручная выборка.
- `palette_profiles.py`: сохранение профилей палитры и проверка калибровки.
- `palette_quantization.py`: сопоставление пикселей с цветами палитры через CIELAB + CIEDE2000; сохраняет размер и детали, не применяет дизеринг.
- `palette_quantization_ui.py`: вкладка этапа 18, выбор профиля, предпросмотр, статистика, экспорт PNG и отчёта JSON.

Этап 18 не создаёт цветной план штрихов и не запускает мышь. Цветной scanline-планировщик запланирован на этап 19.

Запуск тестов: `python -m unittest discover -s tests -v` из этой папки.

## Stage 19 — Color scanline planner

`color_scanline.py` builds a strict ordered plan from Stage 18's integer `index_map`; `color_scanline_ui.py` exposes it in the unified AutoDraw window. Every row is processed top-to-bottom and every run left-to-right. Adjacent pixels merge only if their palette indexes are equal. Transparent pixels (`-1`) are skipped and split runs. The plan records the exact color on each stroke and is saved in its own `autodraw_color_scanline_plan` JSON schema, not Stage 6's one-color schema. See the application README for workflow and Stage 20 limitations.

## Board point quota and standard brushes

`board_resource_model.py` keeps the game's stored-point quota separate from the empirical path-equivalent ink model in `paint_cost_model.py`. The confirmed board variants have quotas of 3,000, 6,000, or 12,000 points. Planning defaults to 85% of the hard limit, retaining a 15% reserve. Normal-mode brush button values are 20, 14, and 7. The extended painter slider supports integer values 1 through 30. The adaptive planner will initially use the full range 1–20: small sizes below 7 are available for thin details, and values above 20 are excluded because the current goal is to reduce overpainting rather than broaden the maximum brush.

The slider's presence and value range are separate from screen-coordinate calibration: before executor automation can change sizes, the extended-mode controls and slider position still need to be calibrated in the target UI.

The game samples cursor coordinates on its frame loop, so executor movement steps do **not** directly determine the number of saved board points. `estimate_calibrated_point_usage()` therefore requires a measured `points_per_path_px` ratio and labels its result as an estimate. Calibrate that ratio against real runs before using it to promise that a plan fits. The existing equivalent-pixel cost model remains a separate empirical estimate.

## Stage 19/20 — Adaptive brush planning

`brush_planner.py` produces a separate `autodraw_adaptive_brush_plan` from the color scanline plan and the exact palette-index map. It checks the conservative footprint of each brush against the source map. Long horizontal runs may be split into a narrow leading edge, a thicker interior section and a narrow trailing edge. Transparent pixels or pixels of another palette index prevent a thick brush from crossing that area. Where no safe mapping is proven, the output retains a marked legacy fallback instead of claiming the stroke is safe.

The parameters `brush_scale_x` and `brush_scale_y` mean source-map pixels per game brush unit. They must be calibrated for the actual board mapping. Until `calibration_confirmed=True` is supplied after calibration, the returned plan is a recommendation and is not marked ready for automatic execution. This initial planner preserves coverage but may increase strokes by splitting long runs; reducing stroke count by safely skipping covered rows is a later optimization step. Tests: `python -m unittest discover -s tests -v`.

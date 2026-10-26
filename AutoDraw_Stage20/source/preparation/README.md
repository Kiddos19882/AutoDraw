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

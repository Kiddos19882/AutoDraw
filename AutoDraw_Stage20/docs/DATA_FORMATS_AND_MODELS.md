# Модели данных и файловые форматы AutoDraw

**Область:** общие геометрические модели и portable-формат проекта.  
**Источники:** geometry_models/*.py и source/preparation/autodraw_project.py.

Документ описывает структуру объектов и сериализованных данных. Он не оценивает алгоритмы, результаты обработки или поведение приложения.

## 1. Общие геометрические модели

Единые определения находятся в папке geometry_models. Пакеты моделей preparation и executor являются совместимыми импортами тех же классов:

| Общая модель | Preparation import | Executor import |
|---|---|---|
| geometry_models.point.Point | source/preparation/models/point.py | source/executor/models/point.py |
| geometry_models.stroke.Stroke | source/preparation/models/stroke.py | source/executor/models/stroke.py |
| geometry_models.drawing_plan.DrawingPlan | source/preparation/models/drawing_plan.py | source/executor/models/drawing_plan.py |

Файлы-адаптеры экспортируют класс через __all__, не определяя отдельные локальные реализации.

## 2. Point

**Источник:** geometry_models/point.py

Неизменяемая dataclass-модель:

| Поле | Тип | Описание |
|---|---|---|
| x | float | Горизонтальная координата |
| y | float | Вертикальная координата |

Координаты заданы в локальной системе холста, не в экранных координатах.

Публичные методы:
- distance_to(other: Point) -> float — расстояние до другой точки.
- to_dict() -> dict[str, float] — сериализация в объект x/y с округлением до 3 знаков.
- from_dict(data: dict) -> Point — создание из ключей x и y.

При создании проверяется, что координаты являются конечными числами.

Пример JSON:

~~~json
{"x": 12.5, "y": 8.0}
~~~

## 3. Stroke

**Источник:** geometry_models/stroke.py

Dataclass одного штриха.

| Поле | Тип | Значение по умолчанию | Описание |
|---|---|---|---|
| name | str | — | Имя штриха; внешние пробелы удаляются |
| points | list[Point] | — | Упорядоченные точки |
| closed | bool | False | Признак замкнутого контура |
| metadata | dict[str, str] | пустой словарь | Дополнительные строковые атрибуты |

Ограничения структуры, заданные моделью:
- имя после удаления пробелов не должно быть пустым;
- требуется минимум две точки;
- для closed=True требуется минимум три точки;
- каждый элемент points должен быть экземпляром Point.

Публичные элементы:
- iter_segments() — итератор пар соседних точек; для замкнутого штриха дополнительно выдаёт сегмент от последней точки к первой.
- length_px — суммарная длина сегментов.
- to_dict() — сериализация name, closed, points, metadata.
- from_dict(data) — создание из словаря; значения metadata преобразуются в строки.

Пример:

~~~json
{
  "name": "stroke-1",
  "closed": false,
  "points": [{"x": 1.0, "y": 2.0}, {"x": 5.0, "y": 2.0}],
  "metadata": {"source": "example"}
}
~~~

## 4. DrawingPlan

**Источник:** geometry_models/drawing_plan.py

Dataclass плана рисования в локальных координатах холста.

| Поле | Тип | Значение по умолчанию | Описание |
|---|---|---|---|
| width | int | — | Ширина холста |
| height | int | — | Высота холста |
| strokes | list[Stroke] | — | Упорядоченный список штрихов |
| name | str | Test drawing plan | Название |
| created_at | str | UTC ISO timestamp | Дата создания |
| schema_version | int | 1 | Версия схемы |

Модель предоставляет:
- stroke_count — количество штрихов;
- total_drawing_length_px — суммарная длина рисуемых сегментов;
- pen_up_distance_px — расстояние переходов между штрихами в порядке плана;
- estimated_move_calls(point_step_px=2.0) — расчётное число сегментных перемещений по заданному шагу;
- validate_bounds() — проверку координат относительно размеров холста;
- to_dict(), from_dict(data), save(path), load(path).

Сериализованный объект содержит schema_version, name, created_at, coordinate_system, canvas, summary и strokes. Значение coordinate_system — local_canvas_pixels.

Пример верхнего уровня:

~~~json
{
  "schema_version": 1,
  "name": "Example",
  "created_at": "2026-10-31T00:00:00+00:00",
  "coordinate_system": "local_canvas_pixels",
  "canvas": {"width": 100, "height": 80},
  "summary": {
    "stroke_count": 1,
    "drawing_length_px": 4.0,
    "pen_up_distance_px": 0.0
  },
  "strokes": [
    {
      "name": "stroke-1",
      "closed": false,
      "points": [{"x": 1.0, "y": 2.0}, {"x": 5.0, "y": 2.0}],
      "metadata": {}
    }
  ]
}
~~~

## 5. Portable-формат .autodraw

**Источник:** source/preparation/autodraw_project.py

Файл проекта представляет собой ZIP-архив. Идентификатор формата — autodraw-project, текущая версия — 1. В корне архива располагается project.json.

### 5.1. Структура архива

Обязательные логические файлы:

| Логическое имя | Путь в архиве |
|---|---|
| source_image | assets/source_image.<ext> |
| binary_mask | assets/binary_mask.png |
| processing_settings | config/processing_settings.json |
| drawing_plan | plans/drawing_plan.json |
| quality_report | reports/quality_report.json |

Необязательные файлы:

| Логическое имя | Путь в архиве |
|---|---|
| prepared_color | assets/prepared_color.png |
| grayscale | assets/grayscale.png |
| imported_quality_report | reports/imported_quality_report.json |

### 5.2. Manifest project.json

Основные поля:

| Поле | Назначение |
|---|---|
| format | Идентификатор формата autodraw-project |
| format_version | Версия формата, сейчас 1 |
| project | Имя, дата создания и обновления |
| canvas | Ширина и высота холста |
| source | Исходные имена файлов, формат и размер исходного изображения |
| files | Соответствие логических имён путям внутри архива |
| sha256 | SHA-256 каждого файла архива, кроме manifest |
| byte_sizes | Размер каждого файла в байтах |
| quality_report_provenance | Происхождение включённого отчёта |
| compatibility | Сведения о совместимости, включая Stage 6 DrawingPlan JSON |

### 5.3. Лимиты формата из исходника

| Ограничение | Значение |
|---|---:|
| Максимум пикселей изображения/маски | 40 000 000 |
| Максимальный размер одного member | 100 MiB |
| Максимальный суммарный распакованный размер | 250 MiB |
| Максимальный размер JSON-плана при чтении | 100 MiB |

### 5.4. Публичный интерфейс модуля

- create_project(...) — формирует ZIP-проект из исходного изображения, маски и JSON DrawingPlan; поддерживает дополнительные входные материалы.
- open_project(path) -> ProjectBundle — читает архив и возвращает объект проекта.
- export_drawing_plan(project_path, destination_path) — экспортирует DrawingPlan в отдельный JSON.
- extract_project(project_path, destination_dir, overwrite=False) — извлекает файлы проекта в каталог.
- project_summary(bundle) -> str — формирует текстовую сводку.
- ProjectBundle — dataclass с path, manifest, files; предоставляет name, canvas, file_bytes(), json_file().
- ProjectFormatError — исключение формата проекта.

### 5.5. Соглашения формата

- DrawingPlan внутри проекта должен иметь canvas.width, canvas.height и непустой массив strokes.
- Каждый штрих содержит непустое имя и массив минимум из двух точек с числовыми x и y.
- Координаты плана допускают правую и нижнюю границу холста: x == width, y == height.
- Маска хранится в PNG и нормализуется в одноканальный режим L при создании проекта.
- processing_settings.json содержит сведения об обработке, scanline-параметрах, настройках профиля исполнения по умолчанию и исходной метаинформации Stage 3, если она передана.
- В проект включается canonical quality report, рассчитанный при создании на основе сохранённых маски и плана. Импортированный отчёт, если он передан, хранится отдельно.

## 6. Форматы для последующей документации

Отдельного описания требуют:
- профиль палитры;
- профиль экранной области и настройки исполнения;
- калибровка кисти и шкалы краски;
- цветные scanline- и geometry-планы;
- manifest лабораторного эксперимента и JSON-отчёты;
- экспорт Game Monitor.

## 7. Поддержание документа

При изменении dataclass, сериализованных ключей, версии формата или обязательных файлов проекта обновлять этот документ в том же изменении. Примеры JSON должны соответствовать текущим сериализаторам.

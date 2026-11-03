# FILL-001 — проверка эффективности заполнения областей разными радиусами

**Дата:** 2026-11-03  
**Статус:** FROZEN MASK GENERATOR, FIXED-RADIUS PLANNER И 45-CELL MATRIX/ANALYZER IMPLEMENTED; CI, preflight и live execution pending  
**Связь:** продолжение INT-006 после INT006R; не открывает INT-007 автоматически  
**Рабочая ветка:** `feature/image-geometry-optimization`  
**Приоритет:** высокий — проверка гипотезы об экономии CHALK при заполнении больших одноцветных областей

> Этот план является действующим рабочим документом. Не удалять и не заменять до выполнения матрицы, анализа PNG и фиксации итогового решения.

## 1. Цель

Проверить, может ли кисть большего радиуса заполнить одну и ту же одноцветную область с меньшим exact CHALK за счёт сокращения числа проходов, штрихов и игровых точек — при сопоставимом визуальном качестве.

Главная метрика:

`effective_area_per_chalk = accepted_target_area_px / exact_chalk`

Метрика учитывается только для опытов, прошедших критерии качества. Нельзя объявлять большой радиус эффективнее, если он расходует меньше CHALK из-за недозаполнения области.

## 2. Почему INT006R не отвечает на этот вопрос

INT006R проверил D1–D5 при P1 и радиусах 1/10/30. Включённые polygon и repeated-coverage сценарии измеряют штриховую геометрию и повторные проходы, но не сравнивают стратегии заполнения одинаковой площади.

Результат INT006R: суммарно 1011/1015/1017 CHALK для радиусов 1/10/30; различие около 0,6%. Это не является доказательством одинаковой эффективности заливки.

## 3. Экспериментальная матрица

| Фактор | Значения |
|---|---|
| Геометрия области | прямоугольная; широкая неправильная; узкая неправильная |
| Радиусы | 1, 5, 10, 20, 30 |
| Повторы | 3 на каждую ячейку |
| Sampling | один фиксированный профиль на всю матрицу; кандидат P1 (step=4, delay=5 ms), если он пройдёт preflight |
| Общее число captures | 3 × 5 × 3 = 45 |

Для каждой геометрии использовать одну и ту же замороженную целевую маску для всех пяти радиусов. По возможности выровнять целевую площадь трёх фигур, чтобы отдельно сравнивать влияние формы, а не только размера области.

### Требования к фигурам

- Прямоугольник: широкая сплошная область без внутренних отверстий.
- Широкая неправильная область: выпуклые и/или плавно меняющиеся границы, достаточная ширина для нескольких параллельных проходов.
- Узкая неправильная область: сужения, повороты и локальные узкие участки, где чрезмерно большой footprint может стать небезопасным.

Все три маски должны иметь один цвет, фиксированные logical dimensions, одинаковую систему координат и frozen geometry signature.

## 4.1. Подтверждённая логика игрового движка

Статический анализ клиентского bundle `main.min_570122a1.js` в `master` показывает:
- `BoardPane.updateLess()` считает точки во всех `atom.points`; exact CHALK delta равна изменению этого счётчика.
- `onDrawStart()` добавляет первую точку, `onDrawing()` добавляет точки в игровом цикле кадров, если указатель находится внутри доски.
- `setRadius()` сохраняет размер отдельно в `atom.radius`; `redraw()` передаёт его в `graphics.lineStyle(value, ...)` как ширину линии.
- Прямого множителя CHALK от радиуса в `updateLess()` нет. Изменение размера влияет на расход только косвенно, если меняет число точек, нужных для требуемого покрытия.

Полный разбор: [CHALK_GAME_ENGINE_POINT_COST_AND_BRUSH_WIDTH_2026-11-03.md](CHALK_GAME_ENGINE_POINT_COST_AND_BRUSH_WIDTH_2026-11-03.md).

**Следствие для дизайна FILL-001:** нельзя рисовать одинаковые траектории разными радиусами и ждать прямого изменения CHALK. Для каждого радиуса нужно построить собственную траекторию заполнения одной и той же frozen target mask, затем проверить, что качество покрытия сопоставимо. Основная зависимость — количество точек, принятых движком; радиус определяет ширину следа.

## 4. Подготовка planner и footprint

В проекте уже существуют:
- `brush_footprint_geometry.py` — консервативное отображение footprint в raster cells;
- `interior_fill_planner.py` — экспериментальный планировщик широких штрихов и fallback;
- `outline_first_fill_planner.py` — экспериментальная boundary-first стратегия.

Ограничения существующей реализации:
- `interior_fill_planner.py` ограничивает `max_brush_value` значением 20;
- оба planner помечают strokes как неготовые к автоматическому исполнению;
- геометрическая модель footprint сама по себе не подтверждает реальную форму следа игрового движка;
- фактический радиус игры нельзя автоматически считать эквивалентным диаметру footprint без проверки.

До live матрицы необходимо:
1. Проверить реальную raster-ширину и форму следа для размеров 1/5/10/20/30 на PNG.
2. Учитывать, что движок передаёт UI radius в Egret `lineStyle` как ширину линии; проверить масштабирование до raster pixels.
3. Проверить endpoint caps, повороты и краевые участки.
4. Не разрешать planner пересекать прозрачность или соседний цвет.
5. Не включать automatic execution для этих planner до отдельного gate.

Если текущий planner не поддерживает radius=30 или использует несовместимую семантику размера кисти, сделать отдельный экспериментальный adapter/plan generator. Не менять production planner или executor defaults без необходимости и отдельного обоснования.

## 5. Сравниваемые показатели

Для каждого capture сохранить:

- requested и observed brush radius;
- frozen target mask и её площадь;
- DrawingPlan и geometry signature;
- число штрихов и отдельных сегментов;
- длину центральной траектории;
- число move calls и sampled points;
- точный pre/post pointCount и exact CHALK;
- сумму per-stroke `DRAW_SAMPLE.pointDelta`;
- время исполнения и параметры sampling;
- before/after board PNG;
- coverage fraction, uncovered target pixels, leakage pixels, holes и merges;
- число проходов на единицу целевой площади.

Основная метрика — площадь корректно покрытой целевой области на один CHALK. Дополнительно сравнить CHALK на единицу целевой площади и CHALK на один штрих.

## 6. Критерии принятия опыта

Capture принимается только если:
- все ожидаемые strokes завершены;
- pre/post snapshots точные;
- `post.pointCount - pre.pointCount = exact CHALK`;
- сумма sampled per-stroke pointDelta совпадает с exact CHALK;
- requested radius совпадает с единственным observed radius;
- dropped events, Monitor errors, Bridge failures и sequence gaps равны нулю;
- experiment/run/task/journal связаны однозначно;
- PNG читаемы и соответствуют целевой области.

Опыт с плохим покрытием не может считаться экономичным. До запуска нужно заморозить критерии качества; начальный кандидат для обсуждения — coverage не ниже 99% и нулевой выход следа за целевую маску. Если для конкретной формы такой критерий технически некорректен, определить отдельный порог по маске до получения результатов, а не после просмотра CHALK.

## 7. Анализ

По каждой геометрии отдельно рассчитать для каждого радиуса:
- три raw exact CHALK значения;
- mean, median, min/max и population SD;
- coverage fraction и leakage;
- effective area per CHALK;
- stroke count, path length и sampled points;
- разницу относительно radius=1 и radius=10.

Сначала сравнивать радиусы внутри одной геометрии. Не объединять три формы в один коэффициент, если проявляется interaction radius × geometry.

Если radius=30 уменьшает CHALK, но ухудшает coverage или создаёт leakage, такой результат не считается выигрышем. Если большой радиус выигрывает только на широком прямоугольнике, применять вывод только к соответствующему классу областей.

## 8. Порядок выполнения и gates

1. [x] Проверить текущий code HEAD, существующие fill planner и тесты; зафиксировать их ограничения.
2. [x] Подготовить frozen masks и генератор fixed-radius DrawingPlan.
3. [x] Реализовать отдельный 45-cell matrix manifest с тремя повторами на ячейку.
4. [x] Добавить fail-closed validation radius, mask/plan signature, repeat, task/run identity, exact CHALK и динамический expected stroke count.
5. [x] Добавить offline analyzer и regression tests; live PNG evidence остаётся обязательным для каждого capture.
6. [ ] Получить полный CI PASS и Windows portable build на актуальном HEAD.
7. [ ] Выполнить локальный Windows preflight: игра, Game Monitor heartbeat, точный pointCount, калибровка slider 1–30, чистая доска.
8. [ ] Выполнить 45 live captures; не запускать более 10 workflow за один раз.
9. [ ] Запустить analyzer на реальных данных и завершить ручной visual audit всех PNG.
10. [ ] Сравнить эффективность и принять решение о радиусах для заливки.

## 9. Границы

- Не менять frozen INT-006 model, production estimator и executor/sampling defaults.
- Не вводить CHALK multiplier от радиуса только на основании INT006R.
- Не считать длину пути или число штрихов заменой exact CHALK.
- Не переносить результаты на контуры, смешанные радиусы или полные рисунки без проверки.
- INT-007 остаётся BLOCKED до расширенной validation и решения о safety margin.


## 10. Результат технического аудита перед harness

Проверены текущие реализации `interior_fill_planner.py`, `outline_first_fill_planner.py`, `brush_footprint_geometry.py` и их regression tests.

- `interior_fill_planner.py` комбинирует несколько ширин кисти, добавляет fallback brush=1 и ограничивает max brush значением 20. Его нельзя напрямую использовать для FILL-001, где каждый capture должен сравнивать один фиксированный радиус.
- `outline_first_fill_planner.py` использует brush=1 для границы и другие размеры для внутренней заливки; это также смешанная стратегия.
- Оба planner помечают strokes как неготовые к автоматическому исполнению.
- Ручной аудит INT006R подтвердил геометрические риски: radius 1 — разрыв соединения D2 polygon; radius 30 — слияние коротких деталей D4.

Принято решение реализовать изолированный модуль `source/preparation/chalk_fill_experiment.py` с frozen target masks, fixed-radius DrawingPlan generator и raster simulator с округлыми caps. Подробный контракт, matrix/journal integration и порядок реализации: [CHALK_FILL001_HARNESS_DESIGN_2026-11-03.md](CHALK_FILL001_HARNESS_DESIGN_2026-11-03.md).

**Следующий шаг:** подготовить три frozen target masks и проверить, что их площади сопоставимы, а каждый радиус либо проходит заранее заданный quality gate (coverage ≥99%, leakage=0), либо помечается unsupported до live запуска. Production planner и executor defaults не менять.


## 11. Frozen target masks — первый implementation increment

Добавлен `source/preparation/chalk_fill_experiment.py`: детерминированные bool-маски на canvas 460 × 240 logical pixels. Их площади выровнены в пределах 1,133% (допуск плана ±5%). SHA-256 закреплены константами и regression tests:

| Shape | Area | SHA-256 |
|---|---:|---|
| rectangle | 44 653 | `ac1c6660e5986cdf534328c6dbcd5020f631168b1473c24b29e7609eb827998b` |
| wide_irregular | 45 159 | `ffff041d8fcaf53ce4f680ddbefb43a949dd72fdb10f44d6c95cf4832555d7db` |
| narrow_irregular | 44 879 | `50d45794d9594b5b11f93ddfe407c47210eb315ae10f3d70e0b3978eff5764a3` |

Добавлены 8 regression tests для размеров, площади, формы, связности строк, metadata, разрешённых радиусов и отказа от неизвестных масок. Локальный прогон — 8/8 PASS; полный GitHub Actions для последних commits пока не подтверждён. Fixed-radius DrawingPlan generator ещё не реализован, поэтому live matrix не запускать.


## 12. Ограничения первых raster prototypes

Офлайн-проверка простого горизонтально-вертикального grid показала, что он не обеспечивает coverage ≥99% на радиусах 20/30, хотя leakage равен нулю. Eroded-contour + interior scanlines улучшает coverage, но не проходит строгий combined gate для всех cells: radius 1 оставляет недозаполненную границу, radius 10/30 дают небольшое leakage в OpenCV simulation. Это не live renderer measurement и не production planner.

Поэтому следующий шаг — boundary-aware centerline paths с консервативным offset и двойной raster validation (coverage ≥99%, leakage=0). До прохождения обоих критериев DrawingPlan не передавать executor и не запускать live matrix.

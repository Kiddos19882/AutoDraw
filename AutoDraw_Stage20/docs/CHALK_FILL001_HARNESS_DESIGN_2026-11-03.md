# FILL-001 — технический дизайн экспериментального harness

**Дата:** 2026-11-03  
**Статус:** DESIGN REVIEW COMPLETE; реализация не начата  
**Связь:** [план FILL-001](CHALK_FILL_AREA_RADIUS_EFFICIENCY_PLAN_2026-11-03.md)

## Подтверждённые ограничения

- Игровой счётчик CHALK увеличивается на каждую принятую точку `atom.points`; размер кисти передаётся в `Graphics.lineStyle(value, ...)` как ширина линии. Прямого множителя CHALK от радиуса нет.
- INT006R показал: radius 1 оставляет разрыв в соединении D2 polygon; radius 30 объединяет короткие детали D4. См. [визуальный аудит](CHALK_INT006R_VISUAL_AUDIT_2026-11-03.md).
- `interior_fill_planner.py` использует несколько ширин кисти, fallback brush=1 и ограничение max=20. Он не изолирует один радиус.
- `outline_first_fill_planner.py` использует brush=1 для границы и другие ширины для заполнения. Он также не подходит для сравнения фиксированных радиусов.
- Оба planner помечают результаты как неготовые к автоматическому исполнению. Этот guard нельзя обходить.
- Прямоугольный footprint oracle не доказывает фактическую raster-форму следа и поведение округлых концов.

## Предлагаемая архитектура

Создать отдельный `source/preparation/chalk_fill_experiment.py`, не меняя production planner и estimator.

Модуль должен:
1. Создавать три deterministic frozen target masks: rectangle, wide_irregular, narrow_irregular.
2. Сохранять logical dimensions, площадь, geometry signature и SHA-256 каждой маски.
3. Строить отдельный DrawingPlan для каждой пары shape/radius; все штрихи внутри одного плана используют ровно один радиус.
4. Моделировать ширину линии и округлые caps, проверять leakage и uncovered target pixels.
5. Сохранять stroke count, path length и sampling-point estimate отдельно от exact CHALK.
6. Запрещать исполнение, если frozen hashes или quality gate не совпадают.

Площади масок следует выровнять в пределах ±5%. Для всех cells сохраняется заранее установленный порог: coverage не ниже 99% и нулевой leakage. Если radius/shape не проходит gate, cell помечается unsupported и не исполняется; порог нельзя ослаблять после получения CHALK.

## FILL001 matrix и journal

- 3 формы × 5 радиусов (1/5/10/20/30) × 3 повтора = 45 cells.
- Task identity включает shape ID, radius, repeat, target mask SHA и plan signature.
- `expected_strokes` хранится в каждой task: число проходов зависит от формы и радиуса.
- Validator проверяет полный набор cells, уникальность task/order IDs, sampling P1, разрешённый radius и frozen hashes.
- Executor handoff сверяет requested radius с task metadata и observed Game Monitor radius.
- Capture acceptance требует exact pre/post CHALK и полного per-stroke delta.
- Independent analyzer проверяет journal/task/experiment/run binding, PNG evidence, coverage и leakage.

Нельзя использовать INT-006 frozen prediction artifact: FILL001 — отдельная геометрическая проверка, не переобучение модели INT-006.

## Порядок реализации

1. [x] Проверить game engine semantics, существующие planners и их тесты.
2. [ ] Создать frozen target masks и проверить площади/signatures.
3. [ ] Реализовать fixed-radius generator и raster footprint simulator.
4. [ ] Добавить deterministic/property tests: no leakage, radius isolation, coverage threshold и rejection узкой геометрии.
5. [ ] Добавить FILL001 matrix/block/journal validation с динамическим expected stroke count.
6. [ ] Добавить Brush Test UI и fail-closed executor handoff.
7. [ ] Добавить independent analyzer и PNG evidence gate.
8. [ ] Получить полный CI PASS и Windows portable build.
9. [ ] Выполнить Windows preflight и 45 live captures.
10. [ ] Завершить visual audit и сравнить effective area per exact CHALK.

## Границы

Production estimator, frozen INT-006 model, executor/sampling defaults и `master` не менять. Не смешивать радиусы в одной cell. Не считать prediction points фактическим CHALK. INT-007 остаётся BLOCKED до расширенной validation и решения о safety margin.

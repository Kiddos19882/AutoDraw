# План перекрёстной validation радиуса кисти и геометрии CHALK

**Дата:** 2026-11-03  
**Статус:** IMPLEMENTATION IN PROGRESS — отдельная фаза INT006R и тестовый analyzer добавлены; software gate CI ожидается; live-запуски запрещены до PASS  
**Связь:** продолжение INT-006; не открывает INT-007 автоматически  
**Рабочая ветка:** `feature/image-geometry-optimization`

## 1. Зачем нужен следующий эксперимент

Есть два подтверждённых, но ограниченных результата:

1. Radius matrix 21/21: радиусы 1, 5, 10, 15, 20, 25, 30 измерялись на одном шаблоне из шести горизонтальных линий по 400 logical px. Фактический расход составил 722–728 CHALK, средние по радиусам — 724–727. Систематической зависимости расхода от радиуса в этом сценарии не обнаружено. Подробности: [CHALK_RADIUS_MATRIX_RESULTS.md](CHALK_RADIUS_MATRIX_RESULTS.md).
2. INT-006 D1–D5: официальный analyzer принял 45/45 captures и подтвердил frozen model, но все опыты выполнены при radius=10. Результаты не позволяют перенести вывод radius matrix на диагонали, полигоны, пересечения, короткие детали и повторное покрытие. Подробности: [официальный отчёт INT-006](CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md).

**Цель:** отделить влияние радиуса кисти от типа геометрии и sampling profile. Измерять exact CHALK через `post.pointCount - pre.pointCount`, а не через длину пути или площадь кисти.

## 2. Предлагаемая матрица

Оставить sampling profile неизменным: P1 (`point_step_px=4`, `point_delay_ms=5`), остальные executor parameters — по действующему CHALK protocol.

| Фактор | Значения |
|---|---|
| Геометрии | D1 mixed lines; D2 polygon; D3 intersections; D4 short details; D5 repeated coverage |
| Радиусы | 1, 10, 30 |
| Повторы | 3 на каждую ячейку |
| Sampling | P1: step=4, delay=5 ms |
| Ожидаемые captures | 5 × 3 × 3 = **45** |

Радиусы 1 и 30 проверяют крайние значения доступного диапазона; radius=10 связывает эксперимент с INT-006. Это новая серия: нельзя переиспользовать существующие INT-006 manifests как будто они принадлежат новому block journal. Существующие 45 captures при radius=10 разрешено использовать только как исторический comparator.

### Почему не запускать сразу все 7 радиусов

Полная матрица 7 × 5 × 3 = 105 captures значительно увеличит объём live-тестирования. Сначала проверяются крайние радиусы на всех пяти геометриях. Если обнаружится эффект, который превышает повторяемость, либо нелинейность/взаимодействие с геометрией, для затронутых сценариев добавляются радиусы 5, 15, 20 и 25.

## 3. Обязательные изменения harness до live

Текущая независимая INT-006 phase фиксирует radius=10. Нельзя обходить это ограничение вручную или отключать fail-closed проверки.

Перед тестом нужно спроектировать отдельную matrix phase (рабочее имя `INT006R` или эквивалент), которая:
- разрешает только явно перечисленные радиусы 1/10/30;
- фиксирует D1–D5 geometry signature и один sampling profile P1;
- создаёт отдельный durable block journal и уникальные task/attempt/experiment/run IDs;
- связывает requested radius, observed radius, scenario, repeat, order и exact planned strokes;
- сохраняет pre/post `pointCount`, per-stroke `DRAW_SAMPLE.pointDelta` и Monitor report;
- не требует prediction ID от frozen radius=10 model и не меняет её;
- отклоняет duplicate/missing cells, mismatch радиуса, geometry, sampling, run identity или неполную telemetry;
- имеет unit/regression tests и CI gate до live execution.

Никакой live block не запускать до реализации и успешного CI для отдельной phase.

## 4. Capture acceptance

Каждый опыт принимается только при одновременном выполнении условий:
- executor завершил все ожидаемые strokes;
- requested radius равен единственному observed radius из Game Monitor;
- `chalk.status=exact`;
- `post_point_count - pre_point_count = consumed_points > 0`;
- сумма sampled `DRAW_SAMPLE.pointDelta` равна exact CHALK;
- per-stroke группы совпадают с ожидаемым числом штрихов;
- dropped events, Monitor error delta, Bridge send-failure delta и collector sequence gaps равны нулю;
- experiment ID, run ID, block/task ID и manifest/report связаны однозначно;
- PNG capture пригоден для проверки покрытия, слияния линий и пропусков.

Непринятый capture не заменять нулевым расходом и не включать в статистику.

## 5. Анализ

Для каждой геометрии отдельно показать:
- три фактических CHALK значения для каждого радиуса;
- mean, median, min/max, population standard deviation;
- абсолютную и относительную разницу radius=1 и radius=30 относительно radius=10;
- per-stroke CHALK и разброс;
- количество принятых sampled points, длину центральной траектории как отдельную метрику;
- визуальное покрытие, gaps, merges и качество коротких деталей.

Не объединять пять геометрий в один коэффициент, если наблюдается interaction radius × geometry. Не считать отсутствие заметной разницы в среднем доказательством нулевого эффекта без оценки разброса и достаточности повторов.

Критерий материального эффекта и допустимые интервалы должны быть зафиксированы до live-серии на основании реального бюджета CHALK и повторяемости, а не подбираться после просмотра результата.

## 6. Что будет означать результат

- **Нет заметного эффекта на D1–D5:** можно документировать отсутствие обнаруженного radius effect только для этих пяти geometry classes, P1 и диапазона 1–30; нельзя объявлять радиус несущественным для всех рисунков.
- **Есть эффект только в отдельных геометриях:** модель должна учитывать взаимодействие radius × geometry или использовать отдельные сценарные калибровки.
- **Есть эффект между крайними радиусами или нелинейность:** добавить промежуточные радиусы 5/15/20/25 для соответствующих геометрий.
- **Capture/Monitor integrity недостаточны:** серия остаётся inconclusive; production model не меняется.

## 7. Ограничения и запреты

- Не менять frozen INT-006 model и её coefficients.
- Не менять production estimator, executor defaults или sampling defaults.
- Не вводить множитель расхода, пропорциональный радиусу или площади кисти, без подтверждённых данных.
- Не считать радиус единственным фактором качества: ширина покрытия, merges и gaps анализируются отдельно от exact CHALK.
- Не начинать INT-007 только на основании этой матрицы; дополнительно нужна validation на полных реальных рисунках и отдельное решение по safety margin.
- `safety_margin_status=not_established`, `production_eligibility=not_validated` до выполнения соответствующих gates.


## 8. Реализация INT006R — 2026-11-03

Реализована отдельная фаза `INT006R` в рабочей ветке. Она не изменяет frozen INT-006 model и использует те же D1–D5 logical geometries с новыми scenario IDs.

### Реализованные контракты

- `chalk_experiment_matrix.py`: отдельные IDs D1–D5, expected stroke counts, разрешённые радиусы 1/10/30 и строго фиксированный P1 (step=4, delay=5 ms). Для INT006R prediction ID не требуется.
- `chalk_test_blocks.py`: отдельный durable 45-cell block; каждая ячейка определяется `(scenario, radius, repeat)`. Task ID включает радиус. Journal validator отклоняет неподдерживаемый радиус, sampling mismatch, дубликаты, пропуски и лишний prediction artifact.
- `brush_behavior_test_ui.py`: отдельные UI-сценарии INT006R; перед каждым опытом устанавливается радиус из конкретной задачи журнала, а не фиксированное значение 10. Ручной запуск D1–D5R заблокирован.
- `integrated_app.py`: executor handoff разрешает только D1–D5R, радиусы 1/10/30 и P1; запрошенный радиус должен совпадать с радиусом task metadata и подтверждением Game Monitor.
- `chalk_int006r_validation.py`: отдельный analyzer точных captures, journal/task/experiment/run binding, completeness и per-geometry/per-radius статистики. Frozen predictions INT-006 не загружаются и не меняются. Analyzer дополнительно требует читаемые before/after board ROI PNG одинакового размера; data completeness не закрывает ручной visual quality gate.
- `tests/test_chalk_int006r_validation.py` и интеграционные проверки `tests/test_unified_app.py` покрывают матрицу, журнал, радиусы, P1 и executor handoff.

### Software gate

На момент этой записи CI ещё не подтверждён. Требуется полный `.github/workflows/geometry-tests.yml` на HEAD с INT006R. Live captures не запускать до успешного CI и Windows portable smoke-test.

### Текущие неизменённые условия

- Frozen INT-006 model, coefficients и artifact не менялись.
- Production estimator, executor defaults и sampling defaults не менялись.
- `master` не изменялся.
- Safety margin остаётся `not_established`; production eligibility — `not_validated`.


Подробная последовательность локального Windows preflight, запуска блока, CLI analyzer и ручного просмотра 45 пар PNG зафиксирована в [CHALK_INT006R_LIVE_PREFLIGHT_AND_VISUAL_AUDIT_2026-11-03.md](CHALK_INT006R_LIVE_PREFLIGHT_AND_VISUAL_AUDIT_2026-11-03.md).

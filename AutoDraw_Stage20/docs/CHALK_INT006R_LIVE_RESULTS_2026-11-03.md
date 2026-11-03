# INT006R — результаты live-проверки радиуса и геометрии

**Дата:** 2026-11-03  
**Репозиторий:** `Kiddos19882/AutoDraw`  
**Ветка:** `feature/image-geometry-optimization`  
**Результат:** RAW DATA AUDIT PASS; ручной visual quality gate остаётся PENDING  
**Последний commit с данными:** [138c9fbeaf612a86819f7ff9ea0db7bb1fe4296a](https://github.com/Kiddos19882/AutoDraw/commit/138c9fbeaf612a86819f7ff9ea0db7bb1fe4296a)

## 1. Матрица и идентификаторы

- Phase: `INT006R`
- Series: `chalk-20261103-030837-a20df5`
- Block ID: `a8e0b9ec87984f60aa294910d366e987`
- Ожидаемые ячейки: D1–D5 × radius 1/10/30 × 3 повтора = 45.
- Sampling: P1 — `point_step_px=4`, `point_delay_ms=5`.
- В durable journal: 45 задач, все 45 имеют `status=completed`, по одной completed attempt на задачу.

## 2. Целостность измерений

Все 45 Monitor reports были получены по путям experiment directories, указанным в journal, и проверены по точным snapshots и per-stroke telemetry.

- `chalk.status=exact` и точная величина расхода берётся как `post.pointCount - pre.pointCount`.
- `sampled_point_delta_total` совпадает с exact CHALK delta.
- `point_delta_matches_chalk=true` во всех проверенных отчётах.
- Наблюдаемый радиус соответствует запрошенному: 1, 10 или 30.
- Dropped events = 0.
- Monitor error delta = 0.
- Bridge send-failure delta = 0.
- Collector sequence gaps = 0.
- Все 45 задач завершены; неполных или отклонённых ячеек в journal нет.

Это raw-data audit по сохранённым journal и Monitor reports. Полный официальный CLI analyzer для committed live dataset и ручной просмотр всех 45 пар PNG должны быть оформлены отдельными gates; synthetic analyzer test из CI не подменяет их.

## 3. Итоговый расход CHALK

| Радиус | Всего CHALK | Опытов | Среднее на опыт |
|---:|---:|---:|---:|
| 1 | 1011 | 15 | 67,40 |
| 10 | 1015 | 15 | 67,67 |
| 30 | 1017 | 15 | 67,80 |

Разница между минимальным и максимальным суммарным расходом — 6 CHALK, около 0,6% от результата radius=1.

### По геометриям

Среднее exact CHALK на один опыт; в каждой ячейке три повтора.

| Геометрия | Радиус 1 | Радиус 10 | Радиус 30 |
|---|---:|---:|---:|
| D1 — mixed lines | 62,67 | 62,33 | 63,33 |
| D2 — polygon | 71,67 | 71,00 | 71,00 |
| D3 — intersections | 100,00 | 100,67 | 99,67 |
| D4 — short details | 14,33 | 14,67 | 15,33 |
| D5 — repeated coverage | 88,33 | 89,67 | 89,67 |

## 4. Вывод

В рамках D1–D5, P1 и диапазона радиусов 1–30 заметного преимущества большого радиуса по exact CHALK не обнаружено. Это подтверждает ограниченный вывод INT006R, но не доказывает отсутствие radius effect для произвольной геометрии.

Особенно важно: D2 polygon — это тестовая геометрия штрихов, а не контролируемое сравнение полноценных заливок одинаковой площади и одинакового качества. D5 проверяет повторное покрытие линий, но не заменяет тест заполнения большой одноцветной области.

Поэтому:
- не вводить множитель CHALK, зависящий от радиуса;
- не выбирать radius=30 только ради предполагаемой экономии;
- выбирать радиус по геометрии и детализации, а влияние на покрытие проверять отдельно;
- не менять production estimator, executor defaults и sampling defaults.

## 5. Незакрытые gates

1. Выполнить официальный запуск `chalk_int006r_validation.py` на реальном journal и capture bundle; сохранить JSON report и его SHA-256.
2. Проверить читаемость и соответствие before/after board PNG во всех 45 capture bundles.
3. Завершить ручной visual audit всех 45 пар: покрытие, пропуски, слияния, ширина следа, форма концов и сохранение границ.
4. После этого закрыть visual gate INT006R.
5. Перейти к отдельному эксперименту эффективности заливки областей по [плану FILL-001](CHALK_FILL_AREA_RADIUS_EFFICIENCY_PLAN_2026-11-03.md).

## 6. CI и Git

Software gate INT006R прошёл ранее на code HEAD `28b56a97255b57b50072ba973533ce349c706bd1`, workflow [41540054975](https://github.com/Kiddos19882/AutoDraw/actions/runs/41540054975): все обязательные jobs SUCCESS, Preparation/G3 — 682 passed и 82 subtests; Windows portable build/startup smoke-test — SUCCESS.

Commit `138c9fbe` содержит live experiment data. Для этого data commit GitHub connector не вернул workflow runs или status checks; CI PASS выше относится к code HEAD, а не к отдельному повторному запуску на data commit.


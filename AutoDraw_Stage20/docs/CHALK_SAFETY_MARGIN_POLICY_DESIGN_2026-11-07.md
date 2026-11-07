# Проект политики безопасного запаса CHALK

**Дата:** 2026-11-07  
**Статус:** DESIGN / PROPOSED — числовой запас не утверждён  
**Модель:** `chalk-int006-frozen-2026-11-02`, version 1, radius=10  
**Gate:** INT-006 перед INT-007  
**Фактический CHALK:** `pointCount_after - pointCount_before`

## 1. Цель и ограничения

Определить проверяемый способ добавлять к прогнозу запас, масштабируемый по числу штрихов и учитывающий sampling profile и supported geometry domain. Это design proposal: production reserve не назначен, estimator/defaults не меняются, INT-007 остаётся BLOCKED.

## 2. Данные INT-006

Официальный analyzer принял 45/45 captures: пять DrawingPlan D1–D5 × три профиля P0/P1/P2 × три повтора; 15 captures на профиль, 243 stroke rows; radius=10.

| Profile | Step / delay | Actual | Predicted | MAE | RMSE | Bias (actual−predicted) | Max underprediction |
|---|---:|---:|---:|---:|---:|---:|---:|
| P0 | 2 / 10 ms | 1884 | 1925.25 | 2.882 | 3.189 | −2.750 | 0.99 |
| P1 | 4 / 5 ms | 1010 | 1011.81 | 0.657 | 0.838 | −0.121 | 0.92 |
| P2 | 4 / 10 ms | 1016 | 1012.32 | 0.685 | 0.854 | +0.245 | 1.82 |

Дополнительная offline диагностика: максимум суммы **только положительных** per-stroke residual в одном run: P0=1.990, P1=1.597, P2=2.157 CHALK.

Run-level residual — сумма знаковых ошибок штрихов. Сумма положительных per-stroke residual не позволяет отрицательным ошибкам компенсировать недооценки. Эти показатели нельзя смешивать. Анализатор оставляет `safety_margin_status=not_established` и `production_eligibility=not_validated`.

## 3. Ограничения выборки

- 15 captures/profile — пять независимых DrawingPlan с тремя повторами, а не 15 независимых геометрий.
- P1 лучше по совокупным ошибкам на D1–D5, но не является production default.
- Radius фиксирован на 10.
- Поддержаны только проверенные прямые штрихи и short lookup 1/2/3/5/8/10 logical px.
- Кривые, заливки, неподдержанные длины и другие geometry classes не имеют подтверждённого прогноза.
- Повторы одного плана не увеличивают число независимых plan IDs.

## 4. Кандидатная формула

Для плана с N отдельными исполнениями штрихов:

`P = Σ p_i`

где `p_i` — frozen prediction каждого штриха.

Для каждого calibration run:

`E = CHALK_actual − P`

Положительный E — недооценка. Нормированная недооценка:

`U = max(0, E) / N`

Для каждого sampling profile и supported geometry domain отдельно калибруется заранее выбранный односторонний квантиль `Q(1−α)` распределения U на независимых DrawingPlan.

Кандидатный запас:

`M(N, profile, domain) = ceil(N × Q(1−α))`

Требуемый ресурс:

`CHALK_required = ceil(P + M)`

Это проверяемая гипотеза линейного масштабирования, не готовая production-формула. Её нужно проверить на независимом holdout с различными N. Если гипотеза не подтверждается, использовать заранее специфицированные диапазоны N или другой метод; не подгонять правило по holdout.

Run-level residual сохраняет зависимость ошибок штрихов внутри целого запуска; деление на N делает размер плана явным. Калибровка раздельно по профилю не смешивает sampling settings. Переносимость по geometry domain требует отдельного подтверждения.

## 5. Fail-closed

1. Неизвестная геометрия, длина, radius или profile → `UNKNOWN`.
2. Неполный DrawingPlan, transform mismatch или отсутствующий frozen prediction → `UNKNOWN`.
3. Нет calibration data для profile/domain/N → `UNKNOWN`.
4. Нет привязки прогноза к model version и frozen plan → `UNKNOWN`.
5. Длина пути, площадь, пиксели и radius не заменяют exact CHALK.
6. Факт расхода подтверждается только delta игрового `pointCount`.
7. Запуск возможен только если `CHALK_required <= remaining_point_quota`. Дополнительный эксплуатационный reserve должен быть отдельным валидированным правилом.

## 6. Почему не умножать max per-stroke error на N

243 stroke rows вложены в 45 captures и пять независимых DrawingPlan; строки одного плана зависимы по геометрии и runtime. Считать их 243 независимыми наблюдениями и умножать максимальную stroke error на N необоснованно. Фиксированный guard на целый DrawingPlan также не масштабируется автоматически. Сумма положительных stroke residual полезна как диагностика, но не является production confidence bound.

## 7. Калибровка и независимая проверка

До новых запусков:
- зафиксировать целевое покрытие `1−α`, допустимый риск превышения квоты и acceptance criteria;
- зафиксировать model version, profile, radius, transform, executor settings и supported domain;
- создать новые DrawingPlan, не повторяющие D1–D5; сохранить hash, N, geometry classes и frozen predictions;
- разделить независимые plan IDs на calibration и holdout; повторы одного плана остаются одной группой;
- не менять prediction и критерии после начала серии.

Calibration должна включать разные N и длины для каждого profile/domain. Если выбран distribution-free split-conformal подход с односторонним покрытием 95%, конечный 95%-й эмпирический квантиль требует не менее 19 независимых calibration examples в соответствующей exchangeable группе. Это условие конечного ранга, а не доказательство достаточности для любого domain/production risk. Размер holdout рассчитывается отдельно под acceptance test.

Holdout не используется для переобучения или пересчёта квантиля. Проверяются `actual <= predicted + margin`, coverage в целом и по диапазонам N, частота/величина превышений, зависимость residual от profile/domain/N, exact CHALK и provenance. Любое превышение или domain drift означает FAIL policy; нужна новая версия и новая независимая серия.

## 8. Обязательное расширение domain

Отдельной validation требуют: прямые разной длины/направления; короткие детали вне lookup; кривые/полилинии; пересечения; повторное покрытие; контуры; заливки; другие радиусы; планы с большим числом штрихов. Непроверенный класс остаётся unsupported/UNKNOWN. FILL-001 имеет отдельный PNG quality gate.

## 9. Gate перед INT-007

- [ ] Утверждены целевое покрытие/риск и версия policy.
- [ ] Достаточно независимых calibration DrawingPlan для каждого profile/domain.
- [ ] Holdout подтверждает покрытие, включая планы с большим N.
- [ ] Captures имеют exact CHALK и полную provenance.
- [ ] Unsupported geometry возвращает UNKNOWN.
- [ ] FILL-001 PNG quality gate закрыт отдельно.
- [ ] Production eligibility одобрена отдельным решением.

## 10. Вывод

Данные обосновывают необходимость profile-aware и stroke-count-aware политики, но не числовой reserve. P1 — исследовательский профиль для D1–D5 при radius=10, не production default. `safety_margin_status=not_established`; `production_eligibility=not_validated`; INT-007 BLOCKED.

## Источники

- [INT-006 official validation results](CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md).
- [INT-006 frozen predictions and analyzer](CHALK_INT006_FROZEN_PREDICTIONS_AND_ANALYZER_2026-11-02.md).
- [INT-006 independent validation plan](CHALK_INT006_INDEPENDENT_VALIDATION_PLAN_2026-11-02.md).
- [INT006R live radius results](CHALK_INT006R_LIVE_RESULTS_2026-11-03.md).

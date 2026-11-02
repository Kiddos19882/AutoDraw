# Roadmap AutoDraw

## Актуальный статус INT-006 — 2026-11-03

- [x] Harness D1–D5, 45-cell journal, 15 frozen prediction records, prediction ID handoff и independent analyzer реализованы.
- [x] Live block D1–D5 выполнен: 45/45 tasks completed, radius=10; все 45 Monitor reports прошли повторный аудит exact CHALK и per-stroke integrity.
- [x] Официальный analyzer run [41532629748](https://github.com/Kiddos19882/AutoDraw/actions/runs/41532629748) завершился SUCCESS: 45 accepted, 0 missing, 0 rejected, 15/15 groups complete, 3 repeats per group, 243 stroke rows.
- [x] Frozen artifact SHA-256 и полный journal/task/experiment/run/profile/normalized-geometry binding проверены штатным analyzer.
- [x] Полный CI: Preparation/G3 669 passed + 82 subtests; Application integration, Executor regression, Game Monitor/bridge, Windows portable build/startup smoke-test, PNG audit и CHALK analyzer — success; optional benchmarks skipped.
- [x] Analyzer runtime geometry serialization mismatch исправлен в `8eba34f`; runtime-shaped regression fixture добавлен в `dd64730`.
- [x] Официальные run-level и per-stroke metrics записаны в [официальный отчёт](CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md).
- [ ] Отдельно принять решение о safety margin и расширить domain validation на полные рисунки, кривые, заливки, повторное покрытие и другие радиусы.
- [ ] INT-007 начинать только после решения о safety margin и расширенной проверки. Production estimator/defaults не менять до этого.

**Итог quantitative gate:** PASS. **INT-006 остаётся IN_PROGRESS** только из-за неустановленного safety margin и ограниченной области применимости (пять DrawingPlan, три повтора на cell, radius=10). P1 (step=4, delay=5 ms) — лучший совокупный исследовательский профиль: MAE 0.657, RMSE 0.838, MAPE 1.178%, max underprediction 0.92 CHALK. P1/1 CHALK — лишь provisional empirical guard для этой выборки, не статистическая гарантия и не production rule.

Следующая исследовательская задача: [перекрёстная validation радиуса и геометрии](CHALK_RADIUS_GEOMETRY_CROSS_VALIDATION_PLAN_2026-11-03.md) — отдельная phase/harness, CI gate и только затем live matrix 1/10/30 на D1–D5.

## Статус аналитических планов

Аналитический план этапов 7–10 отменён пользователем 31 октября 2026 г. Эти этапы не переносятся в настоящий roadmap и не должны возобновляться автоматически. См. [архивный план](../PROJECT_ANALYSIS_PLAN_10_STAGES.md).

## Фаза 1. Базовая документация

- [x] Создать единый индекс документации.
- [x] Описать верхнеуровневую архитектуру.
- [x] Составить первичный каталог исходных компонентов и тестов.
- [x] Описать основные каталоги данных и переменные окружения.
- [x] Описать локальный запуск, тестовые команды и Windows-сборку.
- [x] Создать файлы управления проектом.

## Фаза 2. Справочник исходников

- [x] Создать структурный справочник модулей preparation, executor и Game Monitor.
- [x] Документировать общие геометрические модели.
- [x] Завершить инвентаризацию интерфейсов всех 40 модулей preparation в [PREPARATION_API_REFERENCE.md](PREPARATION_API_REFERENCE.md).
- [x] Завершить справочник интерфейсов всех 13 модулей executor в [EXECUTOR_API_REFERENCE.md](EXECUTOR_API_REFERENCE.md).
- [x] Свести UI и интеграционные точки компонентов в [UI_INTEGRATION_MAP.md](UI_INTEGRATION_MAP.md).
- [x] Завершить карту импортов и точек входа: [DEPENDENCY_MAP.md](DEPENDENCY_MAP.md) содержит 40 preparation и 13 executor production-модулей; [TESTS_AND_CI_MAP.md](TESTS_AND_CI_MAP.md) содержит прямые импорты всех 46 найденных тестовых модулей.

## Фаза 3. Справочник форматов и хранилищ

- [x] Документировать формат проекта .autodraw.
- [x] Документировать JSON цветных scanline- и geometry-планов.
- [x] Документировать профиль палитры.
- [x] Документировать профили экранной области, исполнения и калибровки кисти.
- [x] Документировать формат журнала наблюдений paint-limit и снимок brush workflow.
- [x] Документировать JSON-схему экспорта Game Monitor.
- [x] Документировать форматы калибровочных входов/отчётов и ресурсных моделей.

## Фаза 4. Завершение комплекта

- [x] Завершить инвентаризацию прямых импортов 46 тестовых файлов (см. TESTS_AND_CI_MAP.md).
- [x] Проверить 67 относительных ссылок в 35 документах и наличие целевых файлов; якорные фрагменты не используются.
- [x] Сверить объявления интерфейсов 40 модулей preparation и 13 модулей executor с текущими исходниками; проверить ключевые сигнатуры, UI-точки и общие адаптеры.
- [x] Сверить каталог файлового хранилища с `integrated_app.py` и владельцами путей.
- [x] Проверить основной индекс документации и наличие всех его целей.
- [x] Проверить, что Git diff содержит только разрешённые Markdown-файлы; подтверждены шесть изменённых `.md`-файлов и отсутствие изменений исходников.
- [x] Зафиксировать итоговый HEAD и commit в WORK_LOG.

## Фаза 5. Сопровождение

При последующих изменениях:
1. определить затронутые документы;
2. обновить описание интерфейса/формата вместе с изменением;
3. добавить запись в WORK_LOG;
4. добавить запись в CHANGELOG для значимых изменений;
5. обновить задачу в TASKS;
6. проверить ссылки и пути.

## Границы фаз 1–5 (завершённая документационная серия)

В фазы 1–5 не входили: анализ алгоритмов, аудит поведения, производительности, качества, безопасности, браузерные и игровые эксперименты, рефакторинг и исправление кода. Эти ограничения относятся к завершённой документационной серии и не отменяют фазу 6.


## Фаза 6. Измерение CHALK и ресурсная оптимизация

- [x] INT-001: статически инвентаризировать Brush Test UI, Game Monitor, игровой счётчик и модели стоимости AutoDraw.
- [x] INT-002: статически спроектировать контракт низкозатратного CHALK snapshot, baseline/delta и требования к Monitor.
- [~] INT-003: live WebSocket smoke handshake подтверждён артефактами `ready→pong`; Monitor 0.2.1 обнаружил игровую доску в iframe. A/B/C pointCount deltas: A=53/52/52, B=0*/52/52 (B-1 невалиден), C=50/52/52; в двух валидных повторениях все режимы дали 52, а diagnostic snapshot C совпал с точным счётчиком. FPS probes показывают 60 FPS, но не размечены по режимам, поэтому overhead не измерен. Boundary probe дал 4/4 визуально видимых штриха и ΔpointCount=52; точные горизонтальные acceptedPoint x=0/460 ещё не подтверждены. До раздельного A/B/C FPS/duration и проверки горизонтальных границ полную матрицу кистей не запускать.
- [~] INT-004: добавлен первый read-only WebSocket bridge: event subscription, автоматические run JSON, точные pre/post CHALK snapshots, acceptedPoint и per-stroke FPS. Brush Test UI теперь автоматически прикрепляет подходящий run JSON к `experiment.json` по времени `before_draw` и радиусу. Остались live Firefox validation, проверка корреляции и overhead bridge.
- [~] INT-005: параметрический G3 generator/block runner реализован для `paint_consumption_long_lines` (27 задач, 9 сочетаний `point_step_px`/`point_delay_ms`, 3 повтора); G1 (12/12) и G2 (18/18) приняты live. Осталось выполнить локальный preflight и live G3, затем расширять матрицу на другие параметры кисти/траектории.
- [ ] INT-006: построить и валидировать модель прогноза расхода игровых точек, отделяя измерение от оценки.
- [ ] INT-007: интегрировать модель в preflight/resource estimator AutoDraw.
- [ ] INT-008: оптимизировать кисти, траектории, порядок и покрытие при ограничении CHALK.
- [ ] INT-009: сравнить прогноз с фактическим расходом и оценить качество рисунка.

**Критерий итоговой цели:** AutoDraw до исполнения оценивает расход в игровых единицах, выбирает вариант рисования с резервом по квоте и после исполнения сопоставляет прогноз с фактом.

**Границы:** документирование результатов выполняется сразу. Изменение исходного кода и запуск тестов/игровых экспериментов требуют отдельного разрешения.


## Актуализация фазы 6 — G3 software gate закрыт (2026-11-01)

- [x] Программная реализация G3: 27 задач, девять комбинаций шага/задержки, три повтора, строгая идентичность, журналирование, UI и analyzer.
- [x] Полный GitHub Actions CI на HEAD `3dbf8f20bcea44c61290e49398e1a4daf182dbf9`: run [41340237207](https://github.com/Kiddos19882/AutoDraw/actions/runs/41340237207), все три jobs success.
- [x] Windows portable build/startup smoke-test пройден на GitHub-hosted runner.
- [ ] Локальный Windows preflight на рабочей машине.
- [ ] Live G3 block — 27/27 подтверждённых captures.
- [ ] Анализ CHALK по девяти конфигурациям; только после этого валидировать ресурсную модель.
- [ ] Расширить матрицу на независимые параметры размера кисти, траектории и покрытия, если результаты G3 покажут необходимость.

**Граница:** software gate не закрывает live gate. Фактическое влияние шага и задержки на расход CHALK пока не установлено.

## 2026-11-02 — G3 software gate: оптимизация CI

- [x] Разделить обязательные Game Monitor, Preparation/G3, Integration и Executor regression suites на параллельные jobs.
- [x] Отложить тяжёлые Stage 5/7/8 benchmarks до ручного workflow_dispatch.
- [x] Гейтировать portable build успешным завершением всех test jobs и убрать повторный прогон тех же suite только в CI.
- [x] Добавить G3 UI plan-routing test, проверяющий block identity, matrix identity и task-specific executor parameters.
- [ ] Подтвердить полный CI на конечном code HEAD.
- [ ] Получить portable artifact и провести локальный Windows preflight.
- [ ] Закрыть прежний paused journal только через recovery UI после проверки доски.
- [ ] Выполнить новую чистую серию G3 — 27/27 подтверждённых captures.
- [ ] Рассчитать расход CHALK отдельно для девяти комбинаций sampling и проверить влияние на ресурс.


## 2026-11-02 — live G3 принят, переход к модели CHALK

G3 block `chalk-20261102-031830-a0f325` завершён: 27/27 captures приняты. Девять конфигураций `point_step_px` 1/2/4 × `point_delay_ms` 5/10/20 имеют по три повтора. Все captures содержат exact CHALK и чистые per-run transport gates. Полный анализ: [CHALK_G3_RESULTS_2026-11-02.md](CHALK_G3_RESULTS_2026-11-02.md).

- [x] INT-005: параметрическая G3 матрица исполнена live, все 27 captures приняты, расход по девяти конфигурациям рассчитан.
- [~] INT-006: построить сегментированную модель прогноза CHALK. G3 даёт сценарные коэффициенты для длинных горизонтальных линий; перенос на другие типы геометрии не подтверждён.
- [ ] INT-007: интегрировать валидированную модель в preflight/resource estimator AutoDraw.
- [ ] INT-008: оптимизировать кисти, траектории, порядок и покрытие при ограничении CHALK.
- [ ] INT-009: сравнить прогноз с фактическим расходом и оценить визуальное качество.

**Экспериментальный кандидат:** `point_step_px=4` и `point_delay_ms=5` или `10` дали около 365 CHALK на шесть длинных линий. До визуальной проверки непрерывности и качества не назначать этот режим универсальным default.


## 2026-11-02 — INT-006: предварительная модель CHALK

- [x] Приняты G1/G2/G3 live blocks и radius matrix.
- [x] Подготовлена предварительная сегментированная модель: прямые штрихи, короткие штрихи, sampling profile, радиус и повторное покрытие.
- [x] Задокументирована линейная оценка для прямых сегментов при radius=10, step=2, delay=10: `C ≈ 1.765 + 0.2988 × L`.
- [x] Закрыть визуальную проверку G3 step=4: шесть PNG длинных горизонтальных линий визуально непрерывны; pixel-level audit V1–V5 также завершён на 90 captures.
- [ ] Выполнить независимую проверку прогноза на новых рисунках, получить error distribution и консервативный safety margin.
- [ ] После validation перейти к INT-007 — интеграции проверенной оценки в preflight/resource estimator.

**Исторический статус на момент записи 2026-11-02:** IN_PROGRESS до получения официального analyzer report. Текущий статус и закрытие quantitative gate приведены в разделе «Актуальный статус INT-006 — 2026-11-03» выше.


## 2026-11-02 — G3 visual quality audit

- [x] Просмотрены все шесть PNG step=4/delay=5 и step=4/delay=10.
- [x] Подтверждена визуальная непрерывность длинных горизонтальных линий во всех шести повторах.
- [x] Сопоставлены расход CHALK и длительность: оба delay практически эквивалентны.
- [ ] Проверить step=4 на диагоналях, коротких штрихах, поворотах и пересечениях.
- [ ] Получить независимую validation CHALK estimator и error distribution.

**Статус:** G3 visual gate и V1–V5 geometry/pixel audit закрыты. INT-006 остаётся IN_PROGRESS только до независимой validation CHALK-модели и safety margin. Production defaults не изменять.


## Актуальный план после принятия G1/G2/G3 — 2026-11-02

Предыдущие записи фаз и gates ниже/выше сохраняются как история. Текущая последовательность определяется [CHALK_NEXT_STEPS_PLAN_2026-11-02.md](CHALK_NEXT_STEPS_PLAN_2026-11-02.md).

- [x] G1: 12/12 принятых опытов.
- [x] G2: 18/18 принятых опытов.
- [x] G3: 27/27 принятых опытов; девять sampling combinations × три повтора.
- [x] Radius matrix: 21 принятый опыт; в конкретном сценарии длинных линий систематическое влияние радиуса на exact CHALK не обнаружено.
- [x] Построена предварительная сегментированная модель CHALK; production estimator не готов.
- [x] Визуально просмотрены все шесть PNG step=4/delay=5 и step=4/delay=10; длинные горизонтальные линии визуально непрерывны.
- [x] Геометрическая validation step=4: live follow-up диагоналей, коротких штрихов, поворотов, замкнутых контуров и пересечений; pixel-level audit 90 captures подтверждает покрытие и отсутствие gaps.
- [ ] Независимая validation модели на новых рисунках с MAE/RMSE/bias/relative error.
- [ ] Определить safety margin и правила неизвестной/непроверенной геометрии.
- [ ] INT-007: интегрировать validated estimator в preflight.
- [ ] INT-008/INT-009: оптимизация траекторий/покрытия и проверка фактического выигрыша.
- [ ] Отдельно закрыть INT-003: сопоставимое A/B/C измерение overhead Game Monitor.

**Порядок:** геометрическая validation → независимая validation estimator → safety margin → INT-007 → INT-008/009. Production defaults не менять до закрытия соответствующих gates.


## INT-006 — текущая фиксация (2026-11-02)

INT-006 остаётся IN_PROGRESS. Harness V1–V5 и пять live follow-up block series завершены: 45/45 новых captures, exact CHALK/Monitor integrity приняты. Series-aware pixel audit обработал 90 исходных + follow-up captures, 0 invalid/duplicate/missing/unexpected; 297/297 новых stroke rows имеют coverage=1.0 и zero gaps. Следующий gate — независимая validation модели CHALK на полных DrawingPlan и критерии safety margin.

Harness V1–V5: matrix metadata/validator, block planner/journal, Brush Test UI и task-specific executor override; regression tests прошли. Full CI run 41496555297 включая Windows portable smoke-test и PNG audit — success. Production executor defaults и estimator не менять.


## 2026-11-02 — INT-006 PNG screening progress

- [x] Просмотрены 15 representative PNG V1–V5 × P0/P1/P2.
- [x] Зафиксированы ограничения исходной геометрии и отсутствие очевидного визуального ухудшения непрерывности step=4 в выбранных примерах.
- [x] Выполнить количественный pixel-level аудит всех 90 PNG: continuity/max gap, centerline deviation, coverage width/variation, contour closure, parallel separation; 549 stroke rows и 900 pair rows.
- [x] Проверить segmentation masks на blank-board reference и cursor exclusion; для новых 45 captures cursor_detected=false, cursor_exclusion_pixels=0.
- [x] Выполнить targeted reruns исправленных V1/V3, V2 short-stroke, V4 closure и V5 spacing; 45/45 captures завершены.

Исторический скрининг: [CHALK_INT006_PNG_SCREENING_2026-11-02.md](CHALK_INT006_PNG_SCREENING_2026-11-02.md). Follow-up exact CHALK и pixel audit: [CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md](CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md). INT-006 остаётся IN_PROGRESS только до independent validation/safety margin; production defaults/estimator не менять.


## Актуальное уточнение INT-006 — 2026-11-02

Геометрические follow-up V1–V5 и pixel audit завершены. Следующий аналитический gate — независимая validation замороженных моделей P0/P1/P2 на новых DrawingPlan; план эксперимента находится в `CHALK_INT006_INDEPENDENT_VALIDATION_PLAN_2026-11-02.md`.

Программный gate legacy-journal compatibility закрыт: run `41496555297` checkout рабочей ветки после commit `956ce2b`, содержащего commits `f0e05df` и `4847cce` в истории. Preparation/G3 завершился 662 passed и 82 subtests passed; все обязательные jobs, Windows portable build и PNG audit успешны.


## 2026-11-02 — readiness audit независимой validation

- [x] Подтвердить по исходникам отсутствие D1–D5 в matrix contract, block planner/journal, Brush Test UI и executor override allowlist.
- [x] Зафиксировать, что analyzer пока не сравнивает accepted captures с immutable frozen predictions.
- [x] Исправить статус D1–D5 protocol на BLOCKED; создать отдельный readiness audit.
- [ ] Расширить существующий harness отдельной INT006 phase, не меняя production estimator/defaults.
- [ ] Пройти полный CI и Windows portable smoke-test; затем передать локальную инструкцию preflight.


## 2026-11-02 — INT-006 software gate PASS

- [x] D1–D5 matrix/UI/executor handoff и 45-cell block journal.
- [x] 15 frozen prediction records и hash-sealed journal artifact.
- [x] Независимый analyzer exact CHALK с run-level/per-stroke metrics.
- [x] Regression tests для artifact, geometry, matrix cells и handoff.
- [x] Full CI [41513389663](https://github.com/Kiddos19882/AutoDraw/actions/runs/41513389663): 667 passed, 82 subtests; pixel audit и Windows portable build/startup smoke-test success.
- [ ] Локальный Windows 10 preflight.
- [ ] 45 live captures и анализ safety margin.
- [ ] INT-007 integration только после принятия результатов INT-006.

Подробности: [frozen predictions/analyzer](CHALK_INT006_FROZEN_PREDICTIONS_AND_ANALYZER_2026-11-02.md), [local preflight](CHALK_INT006_LOCAL_PREFLIGHT_GUIDE_2026-11-02.md).


## Актуальный статус INT006R — 2026-11-03

- [x] Выделена отдельная фаза INT006R с новыми D1–D5 scenario IDs, чтобы не смешивать её с frozen INT-006 radius=10 journal/model.
- [x] Добавлен 45-cell planner: D1–D5 × radius 1/10/30 × 3 повтора; sampling фиксирован на P1 (step=4, delay=5 ms).
- [x] Добавлены strict journal validation, UI aliases, task-specific radius selection и fail-closed executor handoff.
- [x] Добавлен отдельный analyzer exact CHALK и regression tests для matrix/journal/analyzer/handoff.
- [x] Полный CI [41540054975](https://github.com/Kiddos19882/AutoDraw/actions/runs/41540054975) на code HEAD `28b56a9` завершился SUCCESS: 682 passed, 82 subtests, application/executor/bridge/PNG audit и Windows portable build/startup smoke-test — success.
- [ ] Выполнить локальный Windows preflight и после его PASS провести 45 live captures; live block ещё не запускался.
- [ ] Проверить 45 пар before/after PNG вручную, закрыть visual quality gate и оценить radius × geometry interaction отдельно по каждой геометрии; при обнаружении эффекта добавить промежуточные радиусы.

**Текущий gate:** SOFTWARE PASS. **Live gate:** BLOCKED до локального Windows preflight. Frozen INT-006 model, production estimator/defaults и master не менялись.

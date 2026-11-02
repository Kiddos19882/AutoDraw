# Roadmap AutoDraw

## Актуальный статус INT-006 — 2026-11-02

- [x] Harness V1–V5 и regression tests реализованы; исходный CI #1886 пройден.
- [x] Выполнены и приняты 45/45 исходных live captures V1–V5; CI #1887 на data commit `6479536` завершился success.
- [x] Выполнен pixel-level audit 45/45 PNG: 252 per-stroke rows, 279 parallel-pair rows; representative overlays просмотрены.
- [x] Исправлены пересечения в DrawingPlan V1/V3, добавлен isolation gate; для V4 реализован cursor-free automated post-draw capture.
- [x] Corrective code HEAD `3e8e6c5` прошёл полный CI run [41470680544](https://github.com/Kiddos19882/AutoDraw/actions/runs/41470680544): integration, executor, Game Monitor/bridge, Preparation/G3, Windows portable build и PNG audit — success.
- [x] Cursor-placement fix и regression tests прошли полный CI run [41486593544](https://github.com/Kiddos19882/AutoDraw/actions/runs/41486593544), включая Windows portable build/startup smoke-test и INT-006 PNG audit.
- [x] Получена первичная holdout-проверка G1-модели на 66 новых штрихах P0 (MAE 1.09, RMSE 1.33, MAPE 1.71%).
- [x] Выполнить live follow-up V1/V3/V4 и V2/V5: 45/45 captures в commit `e879a77`; все блоки 9/9 completed, exact CHALK и per-run Monitor integrity приняты.
- [x] Выполнить pixel-level аудит новых 45 follow-up PNG в CI `41496555297`: 90/90 captures valid; 297/297 новых strokes coverage=1.0, zero gaps; V4 closure seams 27/27 covered; V5 spacing 8/12 merge, 16/20/24 separated при radius=10.
- [ ] Завершить независимую validation step=4 и полных DrawingPlan; только затем определить safety margin.

Подробные данные: [исходная live-матрица](CHALK_INT006_V1_V5_RESULTS_2026-11-02.md), [новые follow-up результаты](CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md), [протокол V1/V3/V4](CHALK_INT006_V1_V3_V4_FOLLOWUP_2026-11-02.md), [протокол V2/V5](CHALK_INT006_V2_V5_FOLLOWUP_2026-11-02.md). Production defaults и estimator не менялись. Исторические записи ниже сохраняются для хронологии и не переопределяют этот статус.

Документ объединяет завершённые направления документирования и текущую последовательность работ по измерению игрового CHALK. В текущем продолжении пользователь разрешил все действия; live captures требуют доступной игровой сессии и готовой тестовой доски.

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

**Текущий статус INT-006:** IN_PROGRESS. Live follow-up V1–V5 и pixel-level audit 90 captures завершены; предварительная модель остаётся non-production до независимой validation на полных DrawingPlan и определения safety margin.


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

Отдельно открыт программный gate: commits `f0e05df` и `4847cce` добавили загрузку исторических legacy V2/V5 journals и regression tests, но последний подтверждённый полный CI run `41470680544` относится к более раннему code HEAD `3e8e6c5`. До нового полного CI legacy compatibility не помечать как полностью проверенную.

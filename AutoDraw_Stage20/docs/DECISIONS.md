## 2026-11-07 — run-bound renderer evidence и fallback telemetry

**Статус:** ACCEPTED.

**Решение 1 — DRAW_SAMPLE fallback.** Источники `onDrawing_wrapper` и `state_poll` могут входить в positive DRAW_SAMPLE stream. Событие `state_poll` принимается только при положительном pointDelta и наличии acceptedPoint; весь упорядоченный stream должен совпадать с `POINT_QUOTA_UPDATE` по количеству и координатам. Нельзя заменять этим exact `pointCount` и нельзя принимать неполные/дублирующие последовательности.

**Решение 2 — run-bound renderer references.** Каждый non-baseline paired-renderer run получает собственный offline WebGL reference и manifest, привязанные к его run ID. Baseline references используются только для исходных repeat-1 run. Нельзя повторно применять manifest, привязанный к другому run.

**Решение 3 — manifest naming.** Resolver предпочитает зафиксированное имя `egret-5.4.1-renderer-reference-manifest.json`; для автоматически созданного per-run reference допускает `manifest.json`. Содержимое всё равно проходит sourceRunId, fixture, geometry и pixel acceptance.

**Основание:** Game Monitor implementation `game_monitor.js`; четыре PRR monitor reports; per-run Firefox artifacts; paired renderer analyzer artifact из CI 42321009715. Все шесть run получили PASS_PER_RUN, series PASS. Acceptance thresholds не менялись.

**Последствия:** multi-axis renderer series закрыта; INT-006 CHALK safety margin, INT006R visual review и FILL-001 PNG gate остаются независимыми gates.

---

## 2026-11-07 — фиксация границы PRR execution и formal renderer acceptance

**Статус:** ACCEPTED — уточнение применения существующих acceptance gates, не изменение критериев.

**Решение:** завершение PRR block (4/4 tasks) и exact CHALK captures означает, что локальная серия сбора evidence выполнена. Это не присваивает автоматический `PASS_PER_RUN` и не закрывает renderer series. Для каждого нового run обязательны независимая проверка PNG/provenance/transform/pixel criteria и отдельный aggregate analyzer result.

**Основание:** block journal `596e5c37813a43048395d0f596f9d971`, четыре Monitor reports, единая Bridge session `0490d04b-8728-40f2-891d-e1d57d69402b`; существующий renderer acceptance policy и правила доказательности.

**Последствия:**
- PRR execution отмечен COMPLETED; formal renderer acceptance остаётся PENDING до повторного analyzer.
- Не менять frozen thresholds, brush radius, executor parameters и acceptance criteria после просмотра captures.
- Сохранить неудачный первоначальный block `ab9b788c8199454c957036effb99e9c6` как отдельную историю, не включать его в число успешных повторов.
- CHALK exact подтверждается только pointCount delta; длина траектории и число координат не заменяют расход.
- INT-006 safety margin, FILL-001 PNG gate и INT-007 остаются независимыми gates.

---

# Журнал проектных решений

Журнал фиксирует организационные и документационные решения.

## DEC-001. Основная точка входа в документацию

**Статус:** принято  
**Решение:** `AutoDraw_Stage20/docs/` — единый индекс структурной документации и управления проектом.  
**Последствие:** новые общие документы добавляются через `docs/README.md`.

## DEC-002. Исторические документы сохраняются

**Статус:** принято  
**Решение:** ранее созданные Markdown-файлы не удаляются при создании нового комплекта.  
**Последствие:** новый индекс ссылается на исторические документы, не копируя их целиком.

## DEC-003. Документация отделена от анализа поведения

**Статус:** принято  
**Решение:** структурная документация описывает расположение, назначение, интерфейсы, конфигурацию, форматы и способы работы с репозиторием.  
**Не входит:** оценка алгоритмов, корректности, производительности, качества рисунка, безопасности и результатов измерений.

## DEC-004. Исходный код не изменяется в документационной инициативе

**Статус:** принято  
**Решение:** разрешены только Markdown-изменения.  
**Последствие:** обнаруженные вопросы фиксируются в документации/реестре задач, исходники не исправляются.

## DEC-005. Рабочая ветка

**Статус:** принято  
**Решение:** документационные изменения выполняются в `feature/image-geometry-optimization`; `master` не изменяется.

## DEC-006. Отмена аналитического плана этапов 7–10

**Статус:** принято пользователем, 2026-10-31  
**Решение:** аналитические этапы 7, 8, 9 и 10 отменены. Архивный план сохраняется для истории, но не является активным backlog.  
**Последствие:** статусы проекта, roadmap и реестр задач должны показывать отмену; новые задачи из этого плана не создаются.

## DEC-007. Игровой CHALK измеряется дельтой сохранённых точек

**Статус:** принято как рабочая измерительная основа, 2026-10-31  
**Контекст:** статическая инвентаризация BoardPane и Game Monitor в задаче INT-001.  
**Решение:** фактический расход изолированного опыта рассчитывать как `pointCount_after - pointCount_before`, где `pointCount` — количество точек в `atom.points`; остаток квоты — `max - pointCount`. Длину пути, площадь пикселей и радиус кисти не использовать как прямой эквивалент CHALK.  
**Последствия:** AutoDraw должен прогнозировать число координат, принимаемых игровым sampling на кадрах, а размер кисти оценивать отдельно по эффективности покрытия. До динамической проверки модель считается рабочей гипотезой, а не окончательно валидированной калибровкой.

## DEC-008. Документация обновляется без отдельного запроса

**Статус:** принято пользователем, 2026-10-31  
**Решение:** завершённые результаты анализа и работ сразу отражаются в соответствующих Markdown-документах, реестре задач и журнале работ без отдельного запроса согласования.  
**Границы:** это разрешение распространяется на документирование результатов; оно само по себе не разрешает менять исходный код, тесты, конфигурацию или запускать тесты/эксперименты.

## DEC-009. Снимок CHALK не должен повторно обходить atom.points

**Статус:** принято как проектное требование, 2026-10-31  
**Контекст:** Game Monitor 0.1.2 повторно вызывает полный рекурсивный подсчёт `atom.points` в snapshots, wrappers и polling; игровой `updateLess()` уже выполняет собственный полный подсчёт.  
**Решение:** целевой Monitor должен получать ресурсные значения из уже вычисленного движком результата/события либо из проверенных O(1)-полей. Не запускать дополнительный полный обход массива на каждом событии/кадре. Полный подсчёт `atom.points` допускается только как отдельный диагностический контроль в ограниченных контрольных точках.  
**Граница точности:** до runtime-сверки нельзя объявлять `max/less/pointCount` доступными O(1)-полями экземпляра. Если точный источник недоступен, фиксировать `unavailable` и использовать калиброванную оценку отдельно, не подменяя ею прямое измерение.

## DEC-010. Калиброванные модели не равны прямому счётчику CHALK

**Статус:** принято как уточнение, 2026-10-31  
**Контекст:** в проекте присутствуют `game_point_calibration.py`, `engine_point_calibration.py`, `board_resource_model.py` и legacy `paint_cost_model.py`.  
**Решение:** модели, полученные из порогов видимости штрихов, предполагаемого FPS, шага/задержки исполнителя и коэффициента точек на путь, маркировать как estimates. Отчёт `game_point_calibration` уже указывает `is_engine_exact_counter=false`; `engine_point_calibration` использует номинальные 48 FPS и исторический профиль, для которого реальный FPS не измерен.  
**Последствия:** прогноз AutoDraw может использовать эти модели с явным уровнем уверенности и запасом, но фактический расход эксперимента подтверждается только дельтой точного игрового счётчика.

## Шаблон нового решения

```markdown
## DEC-NNN. Краткое название

**Статус:** предложено / принято / отклонено / заменено  
**Дата:** YYYY-MM-DD  
**Контекст:** почему потребовалось решение.  
**Решение:** выбранный вариант.  
**Последствия:** что изменится в ведении проекта.
```


## DEC-011. Точный CHALK snapshot читается из BoardPane.max и BoardPane.less

**Статус:** принято как реализационное решение, 2026-10-31  
**Источник:** клиентский bundle из ветки `master`, `AutoDraw_Stage20/fileGameEngine/main.min_570122a1.js`, blob SHA `28838e803dcc6f85efb13febd93cc9e0f5046ffc`.  
**Подтверждение исходником:** конструктор `BoardPane` задаёт `this.max=n` и `this.less=this.max`; `updateLess()` считает количество точек `atom.points`, затем записывает `this.less=this.max-e`.  
**Решение:** Game Monitor читает целочисленные `board.max` и `board.less` и вычисляет `pointCount=max-less`. Это O(1)-чтение уже вычисленного игрового состояния; `percent` не используется как источник точного целого значения.  
**Граница достоверности:** поля подтверждены статически в bundle, но доступность/согласованность в живом iframe должна быть проверена runtime-тестом. При отсутствующих или невалидных полях Monitor возвращает `unavailable` и не выполняет fallback-сканирование массива в горячем пути.

## DEC-012. Полный обход atom.points разрешён только для явной диагностики

**Статус:** принято, 2026-10-31  
**Решение:** обычные события, wrappers, polling, status и export Game Monitor используют O(1) `resourceSnapshot`. Рекурсивные `pointCount`/поиск последней точки доступны только через явный `diagnosticSnapshot()` для сверки.  
**Последствия:** структурно исключены дополнительные O(N)-проходы Monitor на каждом игровом событии/кадре; количественное влияние на FPS всё равно требует A/B-измерения в реальном браузере.

- Дополнение к DEC-012: `POINT_QUOTA_UPDATE` создаётся только при изменении `max`/`less`; повторные вызовы `updateLess()` без изменения квоты не засоряют event log.


## DEC-013. Статус эмпирического запаса CHALK после INT-006

**Статус:** принято как ограничение текущей validation, 2026-11-03  
**Решение:** официальный analyzer INT-006 подтвердил 45/45 captures и метрики frozen model на D1–D5 при radius=10. P1 (step=4, delay=5 ms) — лучший агрегированный исследовательский профиль; максимальная наблюдённая недооценка P1 равна 0.92 CHALK. Округлённый вверх эмпирический guard 1 CHALK можно рассматривать только для этой выборки, но он не принимается как универсальный safety margin и не внедряется в production.  
**Последствия:** `safety_margin_status=not_established`, `production_eligibility=not_validated`; INT-006 остаётся IN_PROGRESS, INT-007 — BLOCKED. Требуется расширенная проверка на полных рисунках и неподдержанных типах геометрии. Production estimator, executor defaults и sampling defaults остаются без изменений. Подробности: [официальный отчёт](CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md).


## 2026-11-03 — INT006R как отдельная экспериментальная фаза

**Решение:** проверять влияние радиуса на геометрию через отдельную фазу `INT006R`, не расширяя и не переписывая frozen INT-006 model/journal.

**Причины:** INT-006 закрепляет radius=10 в matrix metadata, block journal, executor handoff и frozen analyzer. Ослабление этих проверок создало бы риск смешивания исторических prediction records и новых радиусных captures.

**Контракт INT006R:** D1–D5 × radius 1/10/30 × 3 повтора = 45 captures; sampling строго P1 (step=4, delay=5 ms); отдельные scenario IDs, task IDs и durable journal; prediction ID отсутствует; exact CHALK и per-stroke Game Monitor telemetry обязательны.

**Границы:** live execution только после полного CI и Windows portable smoke-test. Production estimator, frozen INT-006 artifact, executor defaults, sampling defaults и `master` не изменять по результатам этой фазы автоматически. Safety margin и production eligibility остаются не установленными.


## DEC-015. Единый источник текущего состояния документации

**Статус:** принято, 2026-11-03  
**Контекст:** в репозитории накоплены параллельные планы и исторические Markdown-файлы; отдельные описания статуса отстают от фактических итогов.  
**Решение:** текущая навигация и классификация ведутся через `docs/README.md` и `docs/DOCUMENTATION_INVENTORY_2026-11-03.md`. Актуальные состояние, задачи и последовательность работ определяются только `PROJECT_STATUS.md`, `TASKS.md` и `ROADMAP.md`. Root-level документы с историческими планами не являются действующим backlog.  
**Последствия:** исторические материалы сохраняются; новые общие документы размещаются в `docs/`; удаление архивных документов допускается только после проверки ссылок и уникальных сведений и пересмотра DEC-002.


## DEC-014. Сохранить FILL-001 отдельной вкладкой AutoDraw

**Статус:** принято, 2026-11-03  
**Контекст:** FILL-001 использует собственные frozen masks, 45-cell manifest, fixed-radius planner, single-task approval, runtime binding и PNG evidence workflow. Он переиспользует brush-size controller и Stage 6, но имеет отдельный экспериментальный жизненный цикл и строгие fail-closed gates.  
**Решение:** сохранить FILL-001 самостоятельной вкладкой, не объединять её с седьмой вкладкой «Тест кистей». Седьмая вкладка продолжает обслуживать существующие CHALK block phases; FILL-001 остаётся отдельным интерфейсом для геометрических экспериментов. В текущем порядке вкладок подпись FILL-001 — «8. FILL-001», а «9. Калибровка теста» — следующая вкладка.  
**Последствия:** отдельные UI/workflow и журналы сохраняют изоляцию FILL-001; общие механизмы кисти и Stage 6 переиспользуются без дублирования их низкоуровневой реализации. Это архитектурное решение не разрешает batch execution: матрица из 45 задач остаётся заблокированной до успешного Windows live preflight.

## DEC-016. Логический размер игровой доски не задаёт физический размер экранного ROI

**Статус:** принято, 2026-11-03  
**Контекст:** игровой bundle задаёт `BoardPane.BLACK_BOARD_WIDTH=460` и `BoardPane.BLACK_BOARD_HEIGHT=240`. Эти значения описывают внутреннюю логическую систему координат движка. Клиентский BoardPane отображается с масштабом; его фактический screen ROI зависит от размера окна, viewport и масштаба браузера. В INT006R уже использовались screen captures 581×304 px, а в других калибровках наблюдались иные размеры.  
**Решение:** сохранять frozen masks и исходные DrawingPlan в logical 460×240. Не требовать физический screen ROI 460×240 и не менять масштаб/размер доски в игре ради AutoDraw. Для запуска и PNG evidence использовать фактический calibrated ROI; преобразовывать logical plan в screen-local координаты существующим transform, а frozen mask — в размер ROI для pixel audit. Проверять соответствие равномерному масштабу BoardPane с допуском 1%, совпадение before/after ROI и отсутствие выхода crop за границы экрана.  
**Последствия:** размер PNG определяется калибровкой клиента, а не логическими константами движка. Coverage/leakage считаются на screen-resolution mask после документированного nearest-neighbor rasterization. Несоответствие пропорций остаётся fail-closed ошибкой. Synthetic regression tests не заменяют Windows live preflight; 45-cell matrix остаётся заблокированной до его успешного завершения.


## DEC-016. Единая постоянная система управления знаниями для ИИ

**Статус:** принято, 2026-11-03  
**Контекст:** технические справочники и история проекта были подробными, но рабочий процесс ИИ, уровни доказательности, роли документов и проверка инженерных инвариантов не были сведены в единый постоянный регламент.  
**Решение:** принять пять документов: AI_WORK_GUIDE.md (процесс ИИ), KNOWLEDGE_ARCHITECTURE.md (роли источников), EVIDENCE_AND_VALIDATION.md (уровни подтверждения), ENGINEERING_INVARIANTS.md (критические свойства) и EXPERIMENT_STANDARD.md (методика экспериментов).  
**Правила применения:** документы универсальны для всех подсистем и этапов AutoDraw; они не дублируют текущий статус, roadmap или результаты исследований. Пересматривать их только при системном изменении процесса разработки, архитектуры знаний или постоянных инженерных контрактов. Исторические документы и первичные данные сохраняются.  
**Последствия:** ИИ использует AI_WORK_GUIDE.md при начале каждой новой задачи и профильные регламенты по типу работы. Изменения системы фиксируются в DECISIONS.md, WORK_LOG.md и CHANGELOG.md.

## DEC-017. Повторная проверка неполного FILL-001 Bridge runtime binding

**Статус:** принято, 2026-11-04  
**Контекст:** Bridge session может быть создана до запуска executor, но первоначальный JSON snapshot ещё не содержит bridge_diagnostics или last_message_at_utc. Проверка такого snapshot до временной фильтрации приводила к окончательному FillMatrixError; Stage 6 прекращал retry, а UI-кнопка не могла повторить привязку после обновления session.

**Решение:** сначала исключать Bridge sessions, которые доказуемо находятся вне executor window (по timezone-aware start/close timestamps). Если потенциально пересекающаяся session ещё не содержит diagnostics/finalization timestamp, считать binding pending и не выбирать другую session до разрешения неоднозначности. Кнопка FILL-001 capture finalization повторно запускает binder и обновляет executor report только после полного успешного binding. Stage 6 и UI используют общий summary contract.

**Инварианты:** не ослаблять task/session/run identity, schema v2, source-plan SHA-256, exact pre/post pointCount, per-stroke CHALK, observed radius, P1, lifecycle, non-consuming candidates, sequence gaps, dropped events, Bridge failures и PNG quality gates. Наличие after PNG или session-level CHALK само по себе не означает принятие capture.

**Последствия:** transient persistence race больше не превращается в окончательную binder error; incomplete/ambiguous evidence остаётся fail-closed. Software gate подтверждён CI [41754801210](https://github.com/Kiddos19882/AutoDraw/actions/runs/41754801210) на commit 5cde7a1. Live preflight и 45-cell matrix остаются отдельными gates.


## DEC-018. Изолировать исследование расстояния между проходами FILL-001-RS

**Статус:** принято в рамках согласованного документационного этапа, 2026-11-04  
**Контекст:** live preflight FILL-001 для rectangle/radius=10 исчерпал квоту на 5999 CHALK до завершения 3 последних consuming strokes. Статический OpenCV-анализ выявил, что текущий planner строит проходы практически на каждой строке; для ширины кисти 10 это создаёт около 90% перекрытия соседних линий. Кандидат `scanline_row_step=5` прошёл существующий геометрический gate для трёх frozen masks, но не проверен игровым renderer.
**Решение:** выделить исследование расстояния между scanline-проходами в отдельный этап FILL-001-RS. Параметры `scanline_row_step` и `point_step_px` считать независимыми. Любое изменение геометрии оформлять новой версией плана, новым plan signature и отдельным experiment ID; существующие frozen masks, FILL-001 plans, manifest и captures не переписывать.
**Границы доказательности:** OpenCV coverage/leakage и estimated sampling points являются статическими proxy. Они не доказывают фактическую экономию CHALK. Точный расход определяется только exact `pointCount_after - pointCount_before`; неполный run при исчерпании квоты фиксируется как censored attempt, полная стоимость неизвестна.
**Последствия:** FILL-001 45-cell matrix остаётся BLOCKED до отдельного принятого live preflight. INT-006 safety margin и INT-007 не меняются. Код, тесты, конфигурации, workflow, production estimator/defaults и `master` не меняются без отдельного разрешения.


## DEC-019. Изолировать versioned planner и manifest FILL-001-RS

**Статус:** принято, 2026-11-04  
**Контекст:** exhaustive OpenCV sweep FILL-001-RS проверил 2 238 сочетаний scanline step/offset; 62 прошли существующий gate coverage ≥99% / leakage=0. Для всех 15 shape/radius cells выбраны frozen spacing configs. Геометрия отличается от исходного FILL-001 plan и не должна менять его signatures или результаты.
**Решение:** сохранить исходный planner v1 без изменения его default geometry/signatures. Ввести planner v2 для spacing variants; включать scanline_row_step и scanline_offset в plan identity/signature. Создавать отдельный FILL001_RS_V1 45-task manifest с отдельным selection policy и fail-closed validation. В runtime context/capture сохранять plan variant/version и spacing. Исполнение остаётся single-task only; matrix execution_allowed=false.
**Параметры:** scanline_row_step — расстояние между проходами; point_step_px — расстояние между точками внутри прохода. P1 (step=4, delay=5 ms) не меняется.
**Выбор кандидатов:** максимальный row step, проходящий coverage ≥99% / leakage=0; при равенстве — максимальное coverage, затем минимальные estimated sampling points/path/strokes. Критерий не объявляется CHALK-optimal; estimated points/path/strokes не являются exact CHALK.
**Последствия:** первый live preflight candidate — rectangle/r10/step=5/offset=0. До принятого live capture не запускать 45-task RS matrix и не менять production estimator/defaults, executor defaults, исходный FILL-001 manifest или frozen captures. Exact CHALK — только pointCount_after - pointCount_before. INT-006 safety margin и INT-007 не меняются.


## DEC-020. Legacy Bridge sessions не блокируют FILL-001 runtime discovery

**Статус:** принято, 2026-11-04  
**Контекст:** `find_fill001_runtime_binding()` обнаруживал сохранённые session directories. Legacy session `3323cf8e-01ca-4009-8f16-27d657d857f8` от 2026-10-31 не содержала `schema_version=2` и `bridge_diagnostics`, но классифицировалась как потенциально pending и блокировала единственную актуальную schema-v2 session с завершённым run.

**Решение:** до определения pending/active состояния проверять schema version. Session, не соответствующая schema v2, пропускается как заведомо непригодная для текущего FILL-001 contract. Schema-v2 session без diagnostics/finalization timestamp по-прежнему считается pending, пока не разрешится; несколько подходящих schema-v2 sessions остаются неоднозначностью и не принимаются автоматически.

**Инварианты:** не ослаблять session/run identity, временные границы, source-plan SHA-256, P1, lifecycle, exact pointCount/CHALK, observed radius, Bridge/Monitor diagnostics и PNG quality gates.

**Последствия:** старые несовместимые session files больше не блокируют runtime binding новых экспериментов. Replay test на реальных данных подтверждает binding PASS. Capture при этом остаётся REJECTED по PNG gate (coverage=97.673218%, leakage=28); это решение не меняет критерии качества и не разрешает 45-task matrix.


## DEC-021. Единая affine-конвенция для FILL-001 PNG audit

**Статус:** принято как implementation contract, validation pending, 2026-11-04  
**Контекст:** `transform_logical_brush_plan_to_screen()` переводит inclusive logical bounds [0..460]×[0..240] в screen pixel-center bounds [0..W−1]×[0..H−1] через scales (W−1)/460 и (H−1)/240. PNG audit ранее использовал PIL.resize(), то есть фактически W/460 и H/240. Для client ROI 581×304 это создавало несовпадающие raster transforms и 606 различающихся пикселей на frozen rectangle mask.
**Решение:** rasterize frozen mask в screen ROI обратным nearest-neighbor mapping, используя ровно те же scale_x/scale_y, что и executor coordinate transform. Audit не должен использовать самостоятельную альтернативную формулу масштаба.
**Инварианты:** coverage ≥99%, leakage=0, RGB threshold=8, frozen mask/hash, executor transform и исходные PNG остаются неизменными. Исправление audit не может автоматически принимать capture; committed PNG должны пройти повторный audit на исправленном коде.
**Последствия:** code/test commits 4797aa5 и a950084 реализуют и закрепляют contract. До подтверждённого CI/replay и прохождения PNG gate FILL-001 capture и 45-task matrix остаются BLOCKED.


## DEC-022. Выбор доски Game Monitor не входит в текущий пользовательский сценарий

**Статус:** принято пользователем, 2026-11-04  
**Контекст:** статический анализ подтверждённого game bundle обнаружил preview `BoardPane` внутри `BoardItemBase` и рабочий `PainterPopup.painterBoard`; общий auto-discovery структурно не различает эти экземпляры.  
**Решение:** для текущей задачи считать рабочим сценарием комнату без других досок, с одной пустой тестовой доской на экране. Не исследовать и не исправлять выбор между preview BoardPane и PainterPopup BoardPane; считать этот вопрос `NOT_APPLICABLE_TO_CURRENT_USER_SCENARIO`.  
**Последствия:** удалить `MONITOR-BOARD-SELECTION-001` из актуального backlog и roadmap. Историческое статическое наблюдение сохранять с отметкой о неприменимости к текущему сценарию. Это решение не утверждает, что auto-discovery исправлен для комнат с несколькими досками; код и тесты не меняются.


## DEC-023. Fail-closed client geometry fallback и сохранение renderer snapshot

**Статус:** принято как implementation contract, 2026-11-05  
**Контекст:** Firefox snapshot может не предоставлять `canvas.getBoxQuads()`. Bounding rect без проверки CSS transform не даёт безопасной affine mapping при rotate/skew. Bridge ранее не сохранял renderer geometry, поэтому session/run нельзя было связать с геометрией доски.  
**Решение:** предпочитать `getBoxQuads({box:"content"})`. Если API отсутствует, разрешать client-corner fallback только для положительного axis-aligned CSS matrix и при совпадении canvas rect с Stage×Egret backing scale в пределах 1 CSS px. Иначе возвращать `boardClientCorners=null`, method=`unavailable`. Сохранять raw windowGeometry отдельно, не трактуя его как точный client→desktop transform. Browser Bridge передаёт snapshot в session_start и renderer_geometry updates; collector добавляет optional geometry fields к session schema v2 и run schema v1 без смены schema versions.  
**Инварианты:** client coordinates не приравнивать к desktop/screenshot pixels; не умножать на DPR без подтверждения; не применять approximate/stale geometry к executor; не менять CHALK telemetry и event hot path.  
**Последствия:** Monitor 0.2.3, Bridge session geometry persistence и tests добавлены. AutoDraw profile consumer и desktop/screenshot transform остаются следующими этапами.


## DEC-024. Границы локального доступа и максимальная автоматизация live-тестов

**Статус:** принято, 2026-11-05  
**Контекст:** ИИ работает с удалённым репозиторием и доступными CI-инструментами, но не имеет прямого доступа к локальному ПК пользователя, запущенной программе AutoDraw и игровой доске. Удалённое состояние GitHub не показывает локальные изменения рабочей копии. Live-проверки требуют реальной программы и доски.  
**Решение:** закрепить как постоянное правило, что live-тесты AutoDraw в локальной игровой среде и проверка локального `git status` доступны только пользователю. ИИ не заявляет о выполнении таких действий без предоставленных пользователем результатов. Все тесты с игровой доской должны быть максимально автоматизированы: сначала повторно использовать существующие harness/Monitor/Bridge/executor/capture/analyzer, а при необходимости создавать недостающие условия и инструменты в пределах разрешённого объёма. Автоматизировать подготовку, сценарии и повторы, телеметрию, exact CHALK, сохранение raw evidence, аудит критериев и отчётность; минимизировать и явно обозначать необходимые ручные шаги пользователя.  
**Инварианты:** INV-010 и INV-011. Автоматизация не предоставляет ИИ локальный доступ и не отменяет разрешение на live-эксперимент.  
**Последствия:** правила добавлены в README, индекс документации, AI_WORK_GUIDE, EVIDENCE_AND_VALIDATION и ENGINEERING_INVARIANTS. Код, тесты и workflow не изменялись.

## DEC-025. Формальная renderer acceptance policy установлена на 92%

**Статус:** принято пользователем, 2026-11-06  
**Контекст:** прежние renderer pixel thresholds IoU/precision/recall ≥99.5%, symmetric-difference fraction ≤0.25% и bbox edge delta ≤1 px оказались значительно строже целевого уровня качества 92%. Независимые ограничения могли продолжать отклонять результаты, соответствующие новой целевой политике.  
**Решение:** установить IoU, precision и recall minima на 0.92; symmetric-difference fraction max на 0.087; bbox edge tolerance — 8% от меньшего соответствующего размера сравниваемых bounding boxes (width для X edges, height для Y edges), минимум 1 px, округление вверх. RGB alpha threshold остаётся 24.  
**Обоснование согласования:** предел 8.7% для symmetric difference относительно live changed pixels согласован с одновременными требованиями IoU/precision/recall ≥0.92. Bbox tolerance масштабируется относительно размера объекта, чтобы не сохранять прежнее фиксированное ограничение 1 px для объектов любого масштаба.  
**Инварианты:** capture/provenance, transform/geometry, exact CHALK, event integrity и три уникальных PASS_PER_RUN на каждую ориентацию остаются без изменений. Ослабляются только renderer pixel acceptance criteria. Исторические результаты не пересчитываются; для статуса по новой политике требуется новый CI. Live game runs не разрешены этим решением и не выполнялись.


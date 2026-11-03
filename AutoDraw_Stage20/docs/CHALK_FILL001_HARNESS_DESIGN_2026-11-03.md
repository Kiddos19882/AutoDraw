# FILL-001 — технический дизайн экспериментального harness

**Дата:** 2026-11-03  
**Статус:** planner/matrix/adapter/runtime binder и отдельная вкладка FILL-001 с single-task UI/runner handoff реализованы; software regression gate подтверждён CI [41673570178](https://github.com/Kiddos19882/AutoDraw/actions/runs/41673570178) на `e3774a3`. Windows live runtime/PNG preflight не выполнен. Исторический снимок раннего состояния: [аудит интеграции](CHALK_FILL001_AUTODRAW_INTEGRATION_AUDIT_2026-11-03.md).  
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

## Реализация frozen masks — 2026-11-03

Добавлен `source/preparation/chalk_fill_experiment.py` и `source/preparation/tests/test_chalk_fill_experiment.py`.

- Canvas: 460 × 240 logical board pixels.
- Маски являются одной связной областью с непрерывным диапазоном X в каждой активной строке.
- Площади: rectangle 44 653 px; wide_irregular 45 159 px; narrow_irregular 44 879 px.
- Разброс max/min — 1,133%, меньше допуска ±5%.
- Geometry SHA-256 закреплены в `FILL001_EXPECTED_MASK_SHA256` и проверяются regression tests.

| Shape | Area | SHA-256 |
|---|---:|---|
| rectangle | 44 653 | `ac1c6660e5986cdf534328c6dbcd5020f631168b1473c24b29e7609eb827998b` |
| wide_irregular | 45 159 | `ffff041d8fcaf53ce4f680ddbefb43a949dd72fdb10f44d6c95cf4832555d7db` |
| narrow_irregular | 44 879 | `50d45794d9594b5b11f93ddfe407c47210eb315ae10f3d70e0b3978eff5764a3` |

Локально воспроизведённый набор тестов масок: 8 passed. Полный GitHub Actions result для последних code commits пока не подтверждён; live FILL001 не запускался.

## Exploratory raster prototypes — не production planner

После создания frozen masks проверены два офлайн-подхода на OpenCV raster model с round caps:

- Простая сетка горизонтальных/вертикальных проходов при spacing около половины line width не даёт стабильного coverage ≥99% для крупных радиусов. Для radius 20/30 остаются незакрытые граничные пиксели, хотя leakage в этой модели равен нулю.
- Eroded-contour + interior scanlines достигает coverage ≥99% для радиусов 5/10/20/30, но у radius 10/30 остаётся небольшое число пикселей вне target mask; radius 1 недозаполняет границу примерно на 1,8–1,9%.

Это только исследовательская симуляция OpenCV, не измерение игрового renderer и не пригодный к исполнению DrawingPlan. Ни один из этих алгоритмов не принят: оба не проходят одновременно строгие критерии coverage ≥99% и leakage=0 для всех shape/radius cells.

Следующий алгоритмический шаг — построить boundary-aware centerline paths с консервативным offset, затем проверить их двумя независимыми raster checks: полное покрытие target и отсутствие касания пикселей вне target. После этого сопоставить raster prediction с реальными INT006R captures для калибровки ширины и caps. Не ослаблять quality gate ради получения 45 cells.

## Реализация fixed-radius planner — 2026-11-03

Добавлен `source/preparation/chalk_fill_fixed_radius_planner.py` и regression suite `source/preparation/tests/test_chalk_fill_fixed_radius_planner.py`.

- Планировщик строит отдельный DrawingPlan для каждой пары shape/radius; все штрихи внутри плана используют один размер кисти.
- Boundary-aware centerline строится по distance transform frozen mask. Для покрытия используются горизонтальные проходы по каждому логическому ряду; центр-линии ограничены внутренней областью, вмещающей моделируемый след.
- Raster simulator использует round-capped OpenCV line model и отдельно считает `coverage_fraction`, `uncovered_target_pixels` и `leakage_pixels`.
- Качество принимается только при coverage ≥99% и leakage=0. Порог не ослабляется; не прошедший cell возвращается как unsupported.
- Plan signature связывает форму, радиус, frozen mask hash и координаты проходов. Sampling-point estimate отделён от exact CHALK.
- Все планы остаются `safe_to_execute=false` / `ready_for_automatic_execution=false`: это офлайн-модель, не доказательство соответствия игровому renderer.

Отдельная Python raster simulation на точных frozen masks проверила 15/15 shape×radius cells: coverage 99,962–100%, leakage 0. Для radius 1/5/10/20/30 минимальное coverage по трём формам составило соответственно 100%, 100%, 99,996%, 99,976% и 99,962%. Это результат отдельной симуляции алгоритма, а не подтверждение pytest/CI. Regression tests добавлены; GitHub Actions для нового HEAD ожидается.

## Порядок реализации

1. [x] Проверить game engine semantics, существующие planners и их тесты.
2. [x] Создать frozen target masks, проверить площади и закрепить SHA-256; локальные tests 8/8 PASS (CI status pending).
3. [x] Реализовать fixed-radius generator и raster footprint simulator.
4. [x] Добавить regression tests: no leakage, radius isolation, coverage threshold, deterministic signature и fail-closed validation; CI result pending.
5. [ ] Добавить FILL001 matrix/block/journal validation с динамическим expected stroke count.
6. [ ] Добавить Brush Test UI и fail-closed executor handoff.
7. [ ] Добавить independent analyzer и PNG evidence gate.
8. [ ] Получить полный CI PASS и Windows portable build.
9. [ ] Выполнить Windows preflight и 45 live captures.
10. [ ] Завершить visual audit и сравнить effective area per exact CHALK.

## Границы

Production estimator, frozen INT-006 model, executor/sampling defaults и `master` не менять. Не смешивать радиусы в одной cell. Не считать prediction points фактическим CHALK. INT-007 остаётся BLOCKED до расширенной validation и решения о safety margin.


## Matrix, journal contract и analyzer — 2026-11-03

Добавлены `source/preparation/chalk_fill_matrix.py` и `source/preparation/tests/test_chalk_fill_matrix.py`.

- `build_fill001_matrix(series_id)` формирует 45 уникальных task cells: 3 frozen shapes × 5 радиусов × 3 повтора.
- В каждую задачу входят динамический `expected_strokes`, target area, mask SHA-256, plan signature, planned coverage/leakage и уникальный task ID.
- Manifest имеет canonical SHA-256 подпись; `validate_fill001_matrix` проверяет полный набор ячеек, отсутствие дубликатов, неизменность подписи, frozen mask/plan identity и quality gates.
- `write_fill001_matrix` сохраняет manifest атомарно; `load_fill001_matrix` проверяет его при чтении.
- `validate_fill001_capture` требует run/task/plan/mask/radius identity, точный CHALK = post pointCount − pre pointCount, сумму per-stroke `DRAW_SAMPLE.pointDelta` равную exact CHALK, совпадение completed strokes с dynamic expected_strokes, before/after PNG и успешный PNG audit, coverage ≥99%, leakage=0 и нулевые dropped events/Monitor errors/bridge failures/sequence gaps.
- `analyze_fill001_captures` отклоняет отсутствующие, неожиданные, повторные task/run IDs и неполные captures; агрегирует exact CHALK по каждой паре shape/radius с тремя повторами.
- Analyzer не выводит площадь/CHALK до подтверждения live target area из PNG; поле effective_area_per_chalk остаётся null. Production model/safety margin не меняются.
- Матрица не запускает игру и не исполняет планы. `execution_allowed=false`, `safe_to_execute=false` остаются обязательными.

Добавлены regression tests на 45 cells, deterministic manifest, target area/plan identities, duplicate/missing cells, signature tampering, unsupported planner, manifest round-trip, exact CHALK/quality gates, полный 45-capture analyzer и duplicate run identity. CI для актуального HEAD ещё не подтверждён; до CI PASS и Windows preflight live captures запрещены.


## Исторический аудит до реализации adapter — 2026-11-03

На момент этого аудита `chalk_fill_matrix.py` реализовывал manifest, агрегированный capture validator и analyzer; отдельного Game Monitor adapter ещё не было. Последующая реализация зафиксирована в разделе «Capture adapter implementation increment» ниже.

Подтверждённый интерфейс Game Monitor в `source/game_monitor/game_monitor.js`:

- `DRAW_SAMPLE` содержит `strokeId`, `pointDelta`, `after.pointCount` и `acceptedPoint`;
- `DRAW_START` / `DRAW_START_APPLIED` и `DRAW_END` обозначают границы штриха;
- `BRUSH_CHANGE` / `BRUSH_CHANGE_APPLIED` содержат snapshots до/после изменения радиуса;
- `POINT_QUOTA_UPDATE` сообщает изменение quota snapshot;
- `exportData()` сохраняет event stream и aggregate monitor diagnostics.

FILL-001 capture contract в текущем виде требует уже агрегированные `pre_point_count`, `post_point_count`, `stroke_chalk_deltas`, integrity counters и PNG evidence paths. Отдельного кода, который надёжно связывает события по `strokeId`, выводит per-stroke deltas, проверяет непрерывность sequence, сопоставляет radius и формирует capture из реального export, на момент аудита отсутствовал.

На момент аудита validator проверял только непустые PNG paths и строку `png_audit_status == "passed"`; файловая и pixel-level проверки были добавлены позднее в adapter. Следовательно, эти поля сейчас являются заявлением вызывающего кода, а не самостоятельным доказательством аудита. Unit-test placeholders намеренно фиктивны и не должны попадать в live journal.

**Следующий обязательный engineering gate до live execution:** реализовать отдельный fail-closed adapter/analyzer, который принимает настоящий Game Monitor export и реальные experiment/PNG artifacts; связывает события по run/stroke identity; независимо вычисляет pre/post exact CHALK и per-stroke deltas; проверяет отсутствие dropped events/errors/sequence gaps; валидирует наличие и SHA-256 PNG; запускает pixel audit against frozen target mask; проверяет observed radius и task/plan/mask identity. Добавить fixture из реального формата Monitor export и негативные regression tests. Только после software CI PASS и Windows preflight можно обсуждать live captures.

На момент аудита sampling P1 не был закреплён в task/capture schema. Позднее P1 metadata была добавлена в matrix schema v2 и валидатор; фактическое соблюдение step/delay всё ещё требует runner binding.

До завершения этих работ: live execution запрещён; synthetic analyzer PASS не равен реальной интеграции; production estimator/defaults и frozen INT-006 model не менять.


## Capture adapter implementation increment — 2026-11-03

Добавлен `source/preparation/chalk_fill_capture_adapter.py` и отдельный набор тестов `source/preparation/tests/test_chalk_fill_capture_adapter.py`.

Реализовано:
- вход — Game Monitor export schemaVersion=1 с полным `events`, `eventCount`, `droppedEvents`, `errors`; проверяется длина массива и монотонность `t`;
- pairing `DRAW_START`/`DRAW_END` по уникальному `strokeId`, проверка `DRAW_START_APPLIED` и каждого `DRAW_SAMPLE.pointDelta`;
- per-stroke CHALK вычисляется как `DRAW_END.after.pointCount - DRAW_START.before.pointCount`; отдельно учитывается первая точка, добавленная в `onDrawStart` до начала polling. Сумма per-stroke deltas сверяется с run-level pre/post pointCount;
- observed radius сверяется с `BRUSH_CHANGE_APPLIED.after.currentRadius`;
- sampling profile P1 (step=4, delay=5 ms) добавлен в frozen matrix task и проверяется в capture;
- PNG-файлы реально открываются, проверяется PNG format, одинаковый crop 460×240, вычисляются SHA-256, coverage и leakage через RGB before/after difference (threshold=8);
- внешний `run_id` и bridge diagnostics обязательны и привязаны к eventCount/run identity; bridge failures и sequence gaps должны быть нулевыми.

Ограничения и нерешённые вопросы:
- Game Monitor export schema не содержит собственного `runId` и per-event sequence number; run ID приходит из внешнего journal/runner, а sequence integrity — из отдельного bridge diagnostics report. Текущая связка проверяет значения и совпадение run/eventCount, но не криптографическую подлинность внешнего отчёта.
- Sampling P1 пока передаётся adapter как execution metadata; Game Monitor не наблюдает фактический step/delay. Для live acceptance нужна связка с фактическим runner journal, а не только caller-supplied словарь.
- PNG audit рассчитан на точный logical-board crop 460×240 и использует RGB difference threshold=8. Реальные screenshots, crop registration, UI/cursor exclusion и устойчивость порога ещё не проверены. Synthetic PNG tests не подтверждают реальную игровую визуализацию.
- Monitor event stream не имеет sequence counter; adapter проверяет eventCount, droppedEvents, errors и монотонность времени, но не может сам обнаружить пропуск события, если export count не отражает его. Для этого обязателен bridge report.
- Live execution по-прежнему запрещён до успешного полного CI, проверки фактического bridge report schema, runner binding, реальных PNG preflight и Windows preflight.

Добавлены adapter tests для event schema, exact/per-stroke CHALK, PNG hashes/coverage/leakage и отказа на truncated export/bridge failure. **Тесты пока не запускались; CI не подтверждён.**


## Актуальное состояние software gate — 2026-11-03

Полный GitHub Actions run [41579136690](https://github.com/Kiddos19882/AutoDraw/actions/runs/41579136690) привязан к code HEAD `b4cc45a80231e6bad2f878b2a5a2f16b48b9d68b` и завершился SUCCESS. Preparation/G3 — 754 passed, 24 warnings, 82 subtests passed; Game Monitor/Bridge, Application integration, Executor regression, INT-006 audit и Windows portable build/startup smoke-test успешны. Windows startup log подтвердил активный процесс AutoDraw.exe в течение 10 секунд.

Исторические записи выше о неподтверждённом CI отражают состояние на дату соответствующих implementation increments. Они не являются текущим статусом software gate.

Остаются открытыми: фактическая связка adapter с Bridge/executor journal, подтверждение P1 из runtime-конфигурации, проверка реального PNG crop/threshold/cursor exclusion на Windows. До закрытия этих gates live captures не запускать.


## Актуализация runtime integration — 2026-11-03

После первоначальных implementation increments программный runtime binding реализован в `source/preparation/chalk_fill_runtime_binding.py` и подключён к завершению FILL-001 исполнения в `source/executor/stage6_execute_plan.py`.

Текущая реализация:
- формирует frozen experiment context и сверяет его с task metadata;
- валидирует executor report, source plan evidence, временные границы и фактический P1 (`point_step_px=4`, `point_delay_ms=5`);
- загружает persisted Bridge session schema v2 и run artifacts;
- проверяет session/run identity, timestamps, финализацию run, sequence gaps, send failures, Monitor errors, lifecycle pairs и единственный observed radius;
- сверяет exact pre/post pointCount, run-level CHALK и сумму sampled/per-stroke deltas;
- фиксирует SHA-256 исходных runtime artifacts;
- Stage 6 запускает binding worker после завершения FILL-001 run и обновляет execution report статусом binding.

Регрессионное подтверждение: code commits `fbf1fd6`–`d7466c5`; полный GitHub Actions [41591543009](https://github.com/Kiddos19882/AutoDraw/actions/runs/41591543009) — SUCCESS на `d7466c5`, включая Preparation/G3, executor, integration, Game Monitor/Bridge и Windows portable build/startup jobs.

**Ограничение:** CI подтверждает программную интеграцию на тестовых runtime artifacts. Он не подтверждает live FILL-001 execution в пользовательской Windows/game session, реальный crop/cursor/UI PNG evidence или визуальное соответствие frozen masks. Эти проверки остаются Windows preflight gate; до их завершения 45 live captures не запускать.


## Исторический аудит пользовательской интеграции до реализации UI/runner — 2026-11-03

На момент этого исторического аудита runtime binder и Stage 6 hook уже существовали, но отдельный пользовательский путь создания/выбора FILL-001 task, преобразования planner output в DrawingPlan и передачи experiment context ещё отсутствовал. Последующая реализация зафиксирована в актуальном статусе и временном плане.

На момент аудита runtime binder являлся post-execution валидатором. Это историческое ограничение устранено последующей реализацией отдельного UI/runner handoff.

Matrix tasks сохраняют fail-closed flags `execution_allowed=false` и `safe_to_execute=false`. Следующий шаг — отдельная реализация UI/runner и безопасного handoff по критериям аудита. Не снимать запрет исполнения в planner/matrix напрямую и не запускать live captures до software gate и Windows preflight.

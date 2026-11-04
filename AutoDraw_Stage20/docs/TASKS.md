## BLOCKER: FILL-001-RS — остаточное PNG несоответствие после replay

**ID:** FILL-001-RS-PRE-REPLAY-001  
**Статус:** IN PROGRESS / BLOCKER — replay выполнен, capture REJECTED, локализация остаточного расхождения открыта  
**Приоритет:** блокирует любой следующий live запуск FILL-001-RS и 45-task matrix  
**Условие закрытия:** исходные evidence повторно проверены исправленным audit; hashes и runtime binding записаны; остаточные uncovered/leakage pixels локализованы и причина подтверждена либо строго ограничена доказательствами; принято решение по capture. Следующий live preflight требует отдельного разрешения.

### Фактический результат replay — 2026-11-04

- Исходные PNG и связанные evidence подтверждены в commit [5308214](https://github.com/Kiddos19882/AutoDraw/commit/530821497ce3a6bd5152318a78e1f06cb836f288).
- Replay выполнен тестом `test_chalk_fill_committed_capture_replay.py` через реальный `Fill001Tab.finalize_capture()`; подтверждающий CI — [41780241017](https://github.com/Kiddos19882/AutoDraw/actions/runs/41780241017), checkout HEAD `0f23731848f0c148fe5e1309d1e305576dd4b6b7`.
- Runtime binding PASS: task/session/run связаны с run `6a17a297-ea14-4527-9527-bfd8de3bd335`; 27/27 strokes, radius=10, exact pointCount 1→1261, CHALK=1260; sample delta совпадает с CHALK; dropped events, Monitor errors, Bridge send failures и sequence gaps — 0.
- Исправленный PNG audit: **coverage=98.430600%, leakage=11**. Критерии остаются coverage≥99% и leakage=0; audit status=failed. Предыдущие 97.673218%/28 относятся к audit до affine correction.
- Полный replay report и SHA-256 всех входов: [CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md](CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md).

### Следующие действия

1. [x] Найти и связать исходные before/after PNG, manifest, executor report, plan, Bridge session и run records.
2. [x] Проверить task/run/session binding, executor completion, radius, pointCount и per-sample CHALK.
3. [x] Выполнить replay исправленным `chalk_fill_capture_adapter.py` на исходных PNG.
4. [x] Зафиксировать SHA-256 входов, code/test revision и audit result.
5. [ ] Локализовать 11 leakage pixels и недостающую область покрытия по координатам/границам/штрихам; сохранить диагностические overlays и breakdown.
6. [ ] После диагностики принять решение о capture. Не ослаблять thresholds и не переписывать raw evidence.

**Ограничения:** не менять production-код/defaults, frozen masks, исходные plans/manifest или thresholds; не запускать игру и 45-task matrix. Новый live preflight возможен только после закрытия offline gate и отдельного разрешения пользователя.

---


# Реестр задач AutoDraw

## FILL-001-RS — согласование PNG audit transform

- [x] Сопоставить executor logical→screen transform с преобразованием frozen mask в PNG audit.
- [x] Установить несовпадение: executor использовал (W−1)/460 и (H−1)/240, audit использовал PIL resize W/460 и H/240.
- [x] Исправить mask rasterization по тому же inverse affine transform — [4797aa5](https://github.com/Kiddos19882/AutoDraw/commit/4797aa5e2e3d9f78656c91dcddf285304eae55c1).
- [x] Добавить regression coverage масштаба и raster contract — [a950084](https://github.com/Kiddos19882/AutoDraw/commit/a950084db14fd1560aa15f099da4a0108c9631e7).
- [x] Усилить fixture: эталонный масштаб теперь извлекается непосредственно из `transform_logical_brush_plan_to_screen()`, а не только повторяет формулу — [c399433](https://github.com/Kiddos19882/AutoDraw/commit/c399433af7f2e7bc547a9f35274aaf24d3c3a52e).
- [x] Получить CI run [41778045384](https://github.com/Kiddos19882/AutoDraw/actions/runs/41778045384) на последующих изменениях — run завершился FAILURE: Preparation/G3 799 passed / 5 failed / 24 warnings / 82 subtests; остальные 3 test jobs success, downstream PNG audit и Windows build skipped.
- [x] Разобрать все 5 отказов: synthetic PNG fixtures не учитывали executor pixel-center mapping; non-uniform ROI fixture завершался ValueError до audit.
- [x] Исправить только тестовые fixtures — commits [1f28436](https://github.com/Kiddos19882/AutoDraw/commit/1f28436ab20fe949e4d53cfeea4a5560ed3cbcae) и [0f23731](https://github.com/Kiddos19882/AutoDraw/commit/0f23731848f0c148fe5e1309d1e305576dd4b6b7).
- [ ] Получить полный CI PASS на новых test commits; локальный pytest недоступен.
- [ ] Выполнить committed evidence replay и повторный PNG audit неизменённых before/after PNG исправленным кодом; сохранить coverage/leakage и hashes.
- [ ] Если gate всё ещё fail — исследовать фактический footprint игрового renderer, не ослабляя критерии.
- [ ] Только после принятого PNG/runtime preflight отдельно разрешать 45-cell matrix.

**Текущий статус:** AFFINE SOURCE FIX COMMITTED; CI обнаружил устаревшие synthetic fixtures; test-only corrections COMMITTED, повторный CI PENDING. Live capture и matrix остаются BLOCKED.

## Актуальное состояние FILL-001 / FILL-001-RS на 2026-11-04

## FILL-001-RS — runtime binding и live PNG gate — 2026-11-04

- [x] Использовать evidence commit [5308214](https://github.com/Kiddos19882/AutoDraw/commit/530821497ce3a6bd5152318a78e1f06cb836f288): 27/27 strokes, radius=10, exact CHALK=1260, Bridge diagnostics без потерь и ошибок.
- [x] Исправить блокировку runtime discovery устаревшей legacy Bridge session без schema v2/diagnostics — commit [a7e37d6](https://github.com/Kiddos19882/AutoDraw/commit/a7e37d6eb0031094ffd962bc11ef01860a3af74a).
- [x] Добавить replay реальных данных через `Fill001Tab.finalize_capture()`, включая legacy session, manifest, executor report, Bridge run records и PNG — commit [974f949](https://github.com/Kiddos19882/AutoDraw/commit/974f949e9639acc90e7f4d6f4588c3fb96f9abb2).
- [x] Подтвердить, что runtime binding проходит и связывает run `6a17a297-ea14-4527-9527-bfd8de3bd335` с executor; exact CHALK=1260.
- [x] Повторно выполнить corrected PNG audit на исходных PNG в CI run [41780241017](https://github.com/Kiddos19882/AutoDraw/actions/runs/41780241017): coverage=98.430600%, leakage=11; capture REJECTED.
- [ ] Локализовать остаточные uncovered/leakage pixels; thresholds ≥99% / 0 не менять. Capture и 45-task matrix остаются BLOCKED.
- [x] Полный CI [41772866679](https://github.com/Kiddos19882/AutoDraw/actions/runs/41772866679) — SUCCESS: Preparation/G3 804 passed, 24 warnings, 82 subtests; остальные обязательные jobs, INT-006 audit и Windows portable build/startup smoke-test — SUCCESS; optional benchmarks skipped.


## Исправление FILL-001-RS frozen geometry rebuild — 2026-11-04

Пользовательский runtime evidence commit [63158fb](https://github.com/Kiddos19882/AutoDraw/commit/63158fb55743c566bf231196b80016273970bbf1) зафиксировал отказ single-task preflight до запуска исполнителя. Для задачи rectangle/r10 manifest и исходный DrawingPlan согласованы: planner_version=2, scanline_row_step=5, scanline_offset=0, plan signature совпадает с task, expected_strokes=27. Game Monitor подтвердил radius 30→10; pointCount остался 1 (CHALK=0), Bridge session завершилась без dropped events/errors/send failures.

Причина установлена в runtime guard integrated_app.py: повторное построение выполнялось вызовом build_fixed_radius_fill_plan(shape_id, radius) без spacing-параметров. Значения по умолчанию — step=1/offset=0, то есть legacy planner v1. Поэтому сравнивался FILL-001-RS v2 signature с другой геометрией v1 и срабатывал корректный fail-closed guard. Это ошибка handoff/validation, не ошибка регулировки кисти и не расход CHALK.

Исправление: единый helper повторного построения получает scanline_row_step/scanline_offset из frozen task; для legacy tasks без этих полей сохраняются прежние defaults. Объявленный planner_version проверяется против фактически восстановленного. Добавлены регрессионные проверки RS signature/27 strokes, legacy signature/131 strokes и отказа при несовпадении версии. До успешного CI и повторного локального preflight live matrix остаётся BLOCKED; повторный запуск здесь не выполнялся.

После live run из [73d14a1](https://github.com/Kiddos19882/AutoDraw/commit/73d14a1784a5a9f8ef29bc0e197b75352f2650af) подтверждены exact CHALK=5999 и per-stroke accounting, но исполнено только 128/131 consuming strokes; три кандидата не потребили ресурс после исчерпания квоты. Capture REJECTED, полная стоимость незавершённого плана неизвестна. Строгие runtime/PNG gates не ослаблять.

Exhaustive OpenCV sweep завершён: 2 238 step/offset кандидатов, 62 прошли coverage≥99%/leakage=0, все 15 shape/radius cells имеют frozen spacing candidate. Добавлены planner version 2, отдельный 45-task FILL-001-RS manifest builder, single-task handoff и runtime context binding. r10/rectangle/step=5 — кандидат, не подтверждённый игровым renderer или exact CHALK. Отчёт: [static sweep](CHALK_FILL001_RS_STATIC_SWEEP_2026-11-04.md); порядок — во [временном плане](CHALK_FILL001_TEMPORARY_PLAN_2026-11-03.md).

Новый пользовательский evidence commit [73d14a1](https://github.com/Kiddos19882/AutoDraw/commit/73d14a1784a5a9f8ef29bc0e197b75352f2650af) содержит полный второй Bridge run (27.9 MB), session diagnostics, executor report и PNG pair. Task run подтверждён: radius=10, exact CHALK=5999, sampled/per-stroke delta=5999, 131 pointer candidates, 128 consuming strokes и 3 non-consuming candidates. Strict runtime binder корректно отклоняет его, поскольку stroke_count=128 вместо ожидаемых 131 и non_consuming_stroke_candidate_count=3. Capture не принят; доска исчерпала квоту. Первый Bridge run — отдельная калибровка с CHALK=0 и исключается по event activity window.

Предыдущее сообщение UI о pending runtime binding объясняется временем записи: executor report завершился раньше persistence второго Bridge run примерно на 3.44 секунды. После финализации run доступен для проверки, но содержимое не проходит строгие acceptance invariants. Код binder не ослаблять. Before/after PNG просмотрены визуально; количественный pixel audit не выполнен.

**Временный план:** [CHALK_FILL001_TEMPORARY_PLAN_2026-11-03.md](CHALK_FILL001_TEMPORARY_PLAN_2026-11-03.md). Шаги 1–2 DONE на предыдущем code baseline; FILL-001-RS planner/matrix/handoff и полный CI теперь PASS. Шаг 3 IN_PROGRESS: новый versioned live preflight ожидает локальную Windows/game session и восстановленную доску. Шаги 4–5 BLOCKED.

Реестр содержит документационные и технические задачи проекта. Аналитические этапы 7–10 отменены и в backlog не включаются; INT-001 и последующие задачи ресурсной оптимизации являются отдельной инициативой.

## FILL-001-RS — расстояние между проходами

**Статус:** IN_PROGRESS — exhaustive static sweep, versioned implementation, regression tests и полный GitHub Actions CI PASS; live preflight ещё не выполнен.

- [x] Выполнить exhaustive sweep всех 2 238 step/offset кандидатов и сохранить полный JSON report как CI artifact.
- [x] Зафиксировать 15 выбранных конфигураций и неизменённые frozen mask SHA-256.
- [x] Реализовать versioned planner v2; legacy planner version 1 и его signatures сохранить.
- [x] Реализовать отдельный 45-task FILL-001-RS manifest builder, fail-closed validation, single-task plan handoff и runtime context с spacing parameters.
- [x] Добавить regression tests для planner, matrix, handoff, runtime context и exhaustive sweep.
- [x] Подтвердить полный GitHub Actions workflow на code/test commit dac985e: preparation regressions, exhaustive sweep artifact, required jobs, Windows portable build/startup smoke-test и INT-006 pixel audit — SUCCESS ([41766148192](https://github.com/Kiddos19882/AutoDraw/actions/runs/41766148192)).
- [ ] На локальной Windows машине создать manifest командой `source/preparation/create_fill001_rs_manifest.py`, открыть его существующей вкладкой FILL-001 и выполнить только rectangle/r10/step=5/offset=0/repeat=1 на восстановленной доске с полной квотой.
- [ ] Принять/отклонить capture по runtime binding, exact CHALK и quantitative PNG audit; при quota exhaustion фиксировать censored attempt, не полную стоимость.
- [ ] Только после принятого preflight отдельно решить вопрос запуска новой 45-task RS matrix.

**Ограничения:** существующие FILL-001 frozen plans, signatures, manifest и captures не изменять. P1 sampling и production defaults сохраняются.

## Временный план FILL-001 на пять шагов

**Документ:** [CHALK_FILL001_TEMPORARY_PLAN_2026-11-03.md](CHALK_FILL001_TEMPORARY_PLAN_2026-11-03.md)  
**Статус:** IN_PROGRESS — предыдущий code baseline и новый FILL-001-RS code HEAD прошли полный CI [41766148192](https://github.com/Kiddos19882/AutoDraw/actions/runs/41766148192). Предыдущий live execution завершился с exact CHALK=5999 и 128/131 consuming strokes; capture REJECTED, доска исчерпана. Новый versioned preflight ещё не выполнялся; шаги 4–5 BLOCKED.

| Шаг | Статус | Критерий |
|---|---|---|
| 1. Regression gate: tests, полный CI, Windows build | DONE | CI [41730717881](https://github.com/Kiddos19882/AutoDraw/actions/runs/41730717881), code HEAD `fe6d446`; Preparation/G3 782 passed, 24 warnings, 82 subtests; все обязательные jobs, INT-006 pixel audit и Windows portable build/startup smoke-test SUCCESS; optional benchmarks skipped |
| 2. Runtime binding: Bridge, executor journal, P1 | DONE | Binder, Stage 6 completion hook и связь с FILL-001 experiment context покрыты regression CI; live binding будет подтверждён на шаге 3 |
| 3. UI/runner handoff и Windows preflight | IN_PROGRESS | RS planner/matrix/handoff и regression tests подтверждены полным CI [41766148192] SUCCESS; следующий gate — один live preflight на восстановленной доске |
| 4. 45 live captures | BLOCKED | 45 уникальных принятых ячеек либо документированные отклонения |
| 5. CHALK/quality analysis и рекомендация | BLOCKED | Подготовлен отчёт о влиянии радиуса и лучшей стратегии заливки |

Шаг 2 закрывает программную реализацию и регрессионное покрытие, но не означает, что уже получен live capture. План временный и не подлежит удалению до выполнения всех пяти шагов или отдельного решения пользователя.

## FILL-001 — Monitor capture adapter и runtime binding

**Статус:** IN_PROGRESS  
**Цель:** получать достоверные captures из Game Monitor, Bridge/executor runtime artifacts и PNG evidence для 45-cell заливочной матрицы.

- [x] Реализовать отдельный adapter Monitor export → FILL-001 capture.
- [x] Рассчитывать per-stroke CHALK по подтверждённым lifecycle boundaries и сверять DRAW_SAMPLE deltas.
- [x] Закрепить P1 (step=4, delay=5 ms) в frozen matrix metadata и сверять с фактическим ExecutorConfig.
- [x] Добавить PNG file/hash/pixel audit для calibrated client ROI: frozen logical mask 460×240 преобразуется в фактический размер crop, coverage/leakage и RGB threshold=8.
- [x] Добавить synthetic regression fixtures для event stream, Bridge/session/run artifacts, executor report и PNG.
- [x] Реализовать `chalk_fill_runtime_binding.py`: проверка Bridge session schema v2, session/run identity, executor time window, timestamps, lifecycle, radius, exact snapshots/CHALK, sequence gaps и send failures.
- [x] Добавить post-execution runtime binding hook в Stage 6 для отчётов с FILL-001 experiment context. Сам hook не создаёт пользовательский workflow; отдельный UI/runner handoff реализован в `chalk_fill_ui.py` и `integrated_app.py`.
- [x] Полный CI [41730717881](https://github.com/Kiddos19882/AutoDraw/actions/runs/41730717881) на code HEAD `fe6d446`: Preparation/G3 782 passed, 24 warnings, 82 subtests; все обязательные jobs, INT-006 audit и Windows portable build/startup SUCCESS.
- [x] Реализовать отдельную вкладку FILL-001, single-task planner handoff, сохранение experiment context и task-specific P1 override; registration/UI integration tests включены в CI.
- [x] Устранить требование физического screen ROI 460×240: UI захватывает actual calibrated ROI, adapter сохраняет ROI и logical→screen raster transform.
- [x] Исправить FILL-001 runtime handoff: после добавления `autodraw_experiment` в runtime DrawingPlan записывался буквальный `\n`, что делало JSON невалидным; запись исправлена в `integrated_app.py` (commit `8dfd1b5`).
- [x] Добавить интеграционный regression test, который передаёт реальный FILL-001 plan в Stage 6 и проверяет JSON/context (commit `1b2d8a1`); последующие JSON persistence/hash regression tests подтверждены полным CI `41730717881`.
- [x] Добавить synthetic regression coverage для client ROI 581×304, uniform-scale rejection, ROI metadata mismatch и leakage после rasterization; полный CI `41730717881` — SUCCESS.
- [x] Исправить runtime binder: определять Bridge run overlap по последнему событию и performance clock, а не по позднему `finished_at_utc` (commit `95a8d17`).
- [x] Добавить regression tests на calibration false-overlap и полный разбор/hash Bridge JSON размером более 27 MiB (commit `870bebc`); полный CI [41737923777](https://github.com/Kiddos19882/AutoDraw/actions/runs/41737923777) — SUCCESS.
- [x] Исправить transient Bridge session race: после временной фильтрации incomplete session без bridge_diagnostics или last_message_at_utc считается pending, а не окончательной binder error (commit 5cde7a1).
- [x] Добавить повторный runtime binding в Fill001Tab.finalize_capture(): при непрошедшем binding кнопка повторно проверяет persisted Bridge session/run, записывает summary только после полной проверки и продолжает PNG audit только после passed.
- [x] Свести Stage 6 и UI к общему build_fill001_runtime_binding_summary(); Stage 6 не перезаписывает уже подтверждённый passed статус при завершении retry worker.
- [x] Добавить regression tests: incomplete session → diagnostics persisted → binding succeeds; future session без diagnostics исключается до строгой проверки; UI повторно привязывает runtime evidence перед PNG acceptance.
- [x] Полный GitHub Actions [41754801210](https://github.com/Kiddos19882/AutoDraw/actions/runs/41754801210) на 5cde7a1: Preparation/G3 787 passed, 24 warnings, 82 subtests; Executor, Game Monitor/Bridge, Application integration, INT-006 pixel audit и Windows portable build/startup smoke-test — SUCCESS; optional benchmarks skipped.
- [ ] Провести один новый Windows FILL-001 runtime preflight на восстановленной доске и подтвердить task ↔ executor report ↔ Bridge session/run binding.
- [ ] Проверить реальные before/after PNG crop, RGB threshold, cursor/UI exclusion и frozen mask alignment.
- [ ] Только после preflight разрешить 45 live captures.

**Ограничения:** software UI/runner и CI gate готовы, но live capture не принят. Session-level exact CHALK известен (5999), task-level/per-stroke attribution второго Bridge run не проверена; after PNG просмотрен визуально, количественный mask audit не выполнен. Текущая доска исчерпана. 45-cell matrix заблокирована до нового принятого live preflight. Production estimator/defaults и frozen INT-006 model не менять.

## Статусы

- TODO — не начато.
- IN_PROGRESS — выполняется.
- BLOCKED — ожидает решения или входных данных.
- DONE — выполнено и проверено.
- DEFERRED — отложено без отмены.
- CANCELLED — отменено пользователем или решением проекта.

`ON_HOLD` встречается только в исторических записях и не используется как актуальный статус; новые задачи должны использовать `DEFERRED`.

## Документационная серия

| ID | Статус | Задача | Результат |
|---|---|---|---|
| DOC-001 | DONE | Создать индекс документации | docs/README.md |
| DOC-002 | DONE | Описать архитектурную структуру | docs/ARCHITECTURE.md |
| DOC-003 | DONE | Создать первичный каталог компонентов | docs/COMPONENT_CATALOG.md |
| DOC-004 | DONE | Описать базовую конфигурацию и данные | docs/CONFIGURATION_AND_DATA.md |
| DOC-005 | DONE | Описать разработку, запуск и сборку | docs/DEVELOPMENT.md |
| DOC-006 | DONE | Создать файлы управления проектом | PROJECT_STATUS.md, ROADMAP.md, TASKS.md, DECISIONS.md, WORK_LOG.md, CHANGELOG.md |
| DOC-007 | DONE | Документировать общие модели и формат .autodraw | docs/DATA_FORMATS_AND_MODELS.md |
| DOC-008 | DONE | Создать структурный справочник модулей | docs/MODULE_REFERENCE.md |
| DOC-009 | DONE | Документировать публичные интерфейсы preparation | PREPARATION_API_REFERENCE.md охватывает все 40 модулей подсистемы preparation из MODULE_REFERENCE; сигнатуры и UI-контракты сверены с объявлениями исходников |
| DOC-010 | DONE | Документировать публичные интерфейсы executor | EXECUTOR_API_REFERENCE.md охватывает все 13 модулей executor из MODULE_REFERENCE, общие модели, адаптер image processing и основные контракты исполнения |
| DOC-011 | DONE | Документировать UI и интеграционные точки | docs/UI_INTEGRATION_MAP.md: девять вкладок (FILL-001 — № 8, калибровка — № 9), создание компонентов, callbacks, синхронизация области и передача планов |
| DOC-012 | DONE | Документировать профили, настройки и результаты | DATA_FORMATS_AND_PROFILES.md и FILE_STORAGE_CATALOG.md: схемы, пути, результаты, runtime-файлы и резервное копирование |
| DOC-013 | DONE | Составить карту импортов | DEPENDENCY_MAP.md содержит прямые импорты всех 40 preparation и 13 executor production-модулей; TESTS_AND_CI_MAP.md содержит прямые импорты всех 46 найденных test_*.py файлов из трёх тестовых каталогов и отдельную отметку helper-модуля |
| DOC-014 | DONE | Проверить относительные Markdown-ссылки и индекс | Проверены 67 относительных ссылок в 35 документах; все цели существуют, якорные фрагменты в ссылках отсутствуют; цели основного docs-индекса существуют |
| DOC-015 | DONE | Сверить API-справочники и каталог путей с текущими исходниками | Объявления 40 модулей preparation и 13 модулей executor сопоставлены с исходниками; ключевые точки UI и общие адаптеры проверены; FILE_STORAGE_CATALOG сверён с integrated_app.py и владельцами путей; исправлена нумерация PREPARATION_API_REFERENCE.md |
| DOC-016 | DONE | Провести инвентаризацию Markdown-документации | Проверены 56 файлов `docs/` и 16 файлов корня Stage20; создан `DOCUMENTATION_INVENTORY_2026-11-03.md`, исправлены устаревшие ссылки/статусы в основном индексе; архивные материалы сохранены по DEC-002. |
| DOC-018 | DONE | Создать постоянную систему управления знаниями для ИИ | Добавлены AI_WORK_GUIDE, KNOWLEDGE_ARCHITECTURE, EVIDENCE_AND_VALIDATION, ENGINEERING_INVARIANTS и EXPERIMENT_STANDARD; подключены к README и управляющим документам. Система универсальна для последующих этапов; пересмотр только при изменении постоянных правил. |

## Измерение игрового ресурса CHALK и оптимизация рисования

| ID | Статус | Задача | Результат / границы |
|---|---|---|---|
| INT-001 | DONE | Определить источник игрового CHALK и семантику счётчика | Фактический расход — точная delta игрового `pointCount`; отчёт [CHALK_RADIUS_MATRIX_RESULTS.md](CHALK_RADIUS_MATRIX_RESULTS.md) содержит ограничения радиусной серии. |
| INT-002 | DONE | Определить resource snapshot и baseline/delta протокол | Контракт точного pre/post CHALK определён и используется в принятых экспериментах. |
| INT-003 | IN_PROGRESS | Завершить оценку overhead Game Monitor | Exact counter и telemetry подтверждены. Осталось сопоставимое A/B/C измерение Monitor off / версий Monitor с отдельными FPS, длительностью и overhead. Не блокирует точность CHALK capture, но нужен для оценки накладных расходов. |
| INT-004 | DONE | Автоматически собирать telemetry и связывать её с experiment ID | WebSocket bridge, per-run capture, RunRecorder и запись monitor report/идентификаторов в experiment manifest использованы в принятых G1–G3 captures. Overhead comparison относится к INT-003. |
| INT-005 | DONE | Реализовать автоматизированную лабораторию CHALK-экспериментов | Matrix/block runner, task identity, повторения, manifest, recovery/fail-closed gates и capture acceptance использованы для G1 12/12, G2 18/18 и G3 27/27. |
| INT-006 | IN_PROGRESS | Официальный analyzer PASS: 45/45 accepted, 0 missing/rejected, 15/15 groups complete; SHA-256 и journal/task/experiment/run/profile/geometry binding проверены. Метрики: MAE 1.408, RMSE 1.967, bias -0.875, MAPE 2.134%, max underprediction 1.82 CHALK. Остаются safety-margin decision и расширение domain validation. См. [официальный отчёт](CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md). Production estimator/defaults не менять. |
| INT-006R | DONE | 45/45 live captures, raw-data audit, официальный CLI analyzer (45 accepted, 0 missing/rejected) и ручной аудит всех 45 пар PNG завершены. Зафиксированы ограничения: radius 1 — разрыв соединения D2 polygon; radius 30 — слияние коротких деталей D4. См. [live results](CHALK_INT006R_LIVE_RESULTS_2026-11-03.md) и [visual audit](CHALK_INT006R_VISUAL_AUDIT_2026-11-03.md). |
| INT-006F / FILL-001 | IN_PROGRESS | Exact CHALK=5999 подтверждён для завершённой части run, но 128/131 consuming strokes; 3 non-consuming candidates после исчерпания квоты. Capture REJECTED, quantitative PNG audit не выполнен. FILL-001-RS документирован: r10/step=5 — офлайн-кандидат, не live-validated. 45-cell matrix BLOCKED до принятого versioned preflight. См. временный план и postmortem. |
| INT-007 | BLOCKED | Интегрировать валидированную модель в preflight/resource estimator AutoDraw | Начинать только после независимой validation INT-006 и определения консервативного safety margin. |
| INT-008 | TODO | Оптимизировать кисти, траектории, порядок и покрытие | Подбирать способ построения рисунка в пределах квоты CHALK с учётом качества покрытия; зависит от INT-006/007. |
| INT-009 | TODO | Сравнить прогноз с фактом и проверить качество | Проверить на независимых рисунках прогноз, exact CHALK delta, визуальное качество и устойчивость к разным типам геометрии. |

### CI regression follow-up — 2026-11-02

- [x] Восстановить expected stroke counts для legacy V2/V5 IDs (`6` и `10`) без включения этих IDs в новые `PHASE_SCENARIOS` и block planners.
- [x] Перевести Application integration fixture на действующий V5 follow-up ID `int006_intersections_spacing_sweep` и expected count `16`.
- [x] Запустить полный CI на исправленном HEAD `3e8e6c5`; run `41470680544` подтвердил все обязательные jobs, Windows portable build и INT-006 PNG audit.
- [x] Подтвердить legacy V2/V5 journal compatibility (`f0e05df`) и regression tests (`4847cce`) полным CI run `41496555297`: branch checkout после commit `956ce2b`, Preparation/G3 — 662 passed, 82 subtests passed; все обязательные jobs success.
- [x] Разрешить переход к live follow-up после green CI; live-прогоны выполняются только при доступной игровой сессии.
- [x] Выполнить V1/V3/V4 follow-up по [отдельному протоколу](CHALK_INT006_V1_V3_V4_FOLLOWUP_2026-11-02.md): по 9 captures на фазу.
- [x] Выполнить V2 short-stroke follow-up (5 strokes) и V5 spacing sweep (16 strokes) по отдельному протоколу.
- [x] Выполнить pixel-level audit исходных + follow-up PNG; 90/90 valid, no missing/duplicate cells, 297/297 новых stroke rows без gaps (CI 41496555297).
- [x] Реализовать INT006 D1–D5 в matrix/block/UI/executor/analyzer harness; regression tests добавлены, software CI run `41513389663` прошёл.
- [x] Выполнить 45 независимых live captures D1–D5; предварительно сверить exact CHALK и per-stroke breakdown по всем 45 Monitor reports. Отдельный preflight log в capture bundle не найден.
- [ ] После validation определить обоснованный safety margin.

**Актуальный приоритет:** FILL-001-RS — воспроизвести и зафиксировать полный статический sweep, затем отдельным решением разрешить versioned live preflight. Не менять code/tests/config и не запускать игру в рамках текущего документационного этапа. 45-cell matrix остаётся BLOCKED; INT-006 safety margin и INT-007 не меняются.

| ID | Статус | Задача | Основание |
|---|---|---|---|
| ANA-007 | CANCELLED | Аналитический этап 7 | Отмена пользователем 2026-10-31 |
| ANA-008 | CANCELLED | Аналитический этап 8 | Отмена пользователем 2026-10-31 |
| ANA-009 | CANCELLED | Аналитический этап 9 | Отмена пользователем 2026-10-31 |
| ANA-010 | CANCELLED | Аналитический этап 10 | Отмена пользователем 2026-10-31 |

## Правила обновления

- У каждой задачи уникальный ID.
- DONE ставится только после проверки результата.
- Отменённые задачи не возобновляются автоматически.
- Задачи серии DOC ограничиваются документированием структуры и интерфейсов; технические задачи INT могут включать анализ поведения в пределах явно указанной задачи и разрешений.
- При закрытии задачи добавить запись в WORK_LOG.
- Документационные результаты и статусы обновляются сразу после завершения работы, без отдельного запроса согласования. Это правило не разрешает автоматически менять исходники или запускать тесты.



### CHALK block runner — актуальные gates (2026-11-01)
- [x] Полный CI для f8f2d1c6fe47b8d5e539be78951cea16296e16f6: geometry-tests, executor-tests и Windows portable build/startup smoke-test — success.
- [x] Capture acceptance привязан к активным block/task/experiment identity, experiment_dir из journal и ожидаемым полям сценария/повтора.
- [x] Добавлен тест preclear failure: блок paused, executor не запускается.
- [x] Разобрать CI после task-identity/path acceptance hardening: выявлена устаревшая mock lambda в callback test.
- [x] Исправить mock validator stub для новых keyword identity аргументов (commit `20704ab984b981a4bf5b2278eba6cfad970d15a5`).
- [ ] Подтвердить полный CI и Windows startup smoke-test после исправления.
- [x] Провести review journal/recovery shape: добавить fail-closed structural validation и unit tests для повреждённых журналов.
- [x] Дополнить journal validator проверкой типов phase/status до membership checks; добавить тесты на list/dict в статусных полях.
- [x] Исправить SyntaxError, выявленный Windows packaging test в journal validator (commit `dd5aaade3b790546d9e3fc11341554f6aa09d8ec`).
- [ ] Повторно подтвердить полный CI для исправленного validator; отдельно оценить single-instance assumption и journal I/O failure paths.
- [ ] Выполнить один контролируемый live G1 block после успешного CI и проверки тестовой доски.
- [ ] Только после полного принятия G1 разрешить G2.

## Автоматические блоки CHALK

- [x] Создать ядро планирования G1/G2 с полным набором сценариев и тремя повторами.
- [x] Создать долговечный журнал блока, фиксировать попытки и прогресс; останавливать блок при failed/interrupted.
- [x] Добавить unit tests для полного состава блока, repeat cells, deterministic order и recovery.
- [x] Интегрировать Start/Stop/progress UI в Brush Test.
- [x] Связать block state machine с preclear, подтверждением радиуса, executor, Game Monitor exact capture и переходом к следующей задаче; добавить fail-closed gate полного per-stroke breakdown.
- [x] Добавить recovery UI для прерванной/приостановленной задачи без автоматического повторного рисования.
- [ ] Добавить исчерпывающие orchestration tests на отказ каждого callback/gate (добавлены Alt-cancel tests для preclear/postdraw; покрытие пока неполное).
- [ ] Пройти полный CI и Windows portable startup smoke-test после исправления mock; затем выполнить один live G1 block.

UI runner реализован, но до CI и отдельного контролируемого live G1 не считать его готовым к экспериментальной эксплуатации. Live-матрицу вручную по частям не продолжать.


### G1 readiness — журнал и отказоустойчивость
- [x] Ужесточить согласованность block/task statuses.
- [x] Не разрешать новый блок при journal status failed.
- [x] Сериализовать read-modify-write транзакции межпроцессной advisory lock.
- [x] Добавить fault-injection tests для temp write и os.replace.
- [ ] Подтвердить полный CI для новых коммитов (geometry, executor, Windows startup smoke-test).
- [ ] Проверить на Windows, что блокировка и fault handling работают в portable-сборке.
- [ ] Подтвердить фактическую готовность профиля калибровки и Game Monitor bridge.
- [ ] Получить подтверждение чистой тестовой доски перед live G1.
- [ ] Выполнить один контролируемый G1 block и принять все 12 уникальных ячеек.


### G1 readiness — эксклюзивный session lock
- [x] Добавить lifetime owner lock на весь активный block/recovery сеанс.
- [x] Не переводить running в interrupted, если lock удерживается другим экземпляром.
- [x] Требовать владение lock для resume/close.
- [x] Требовать проверку доски для закрытия failed/paused.
- [ ] Подтвердить полный CI и Windows startup smoke-test на финальном SHA.
- [ ] Провести Windows preflight: calibration, slider 1–30, Clear reference, canvas, Game Monitor heartbeat.
- [ ] После явного подтверждения тестовой доски запустить G1 и принять все 12 ячеек.


- [x] Сделать owner lock общим для всего каталога chalk_test_blocks, чтобы блокировать запуск разных журналов параллельно.
- [x] Добавить тест конкуренции для разных journal paths в одном каталоге.
- [ ] Подтвердить CI на финальном кодовом SHA.


- [x] Fail-closed обработка ошибки открытия/создания owner lock.
- [x] Тест PermissionError при получении owner lock.
- [ ] Полный CI после последних owner-lock I/O изменений.


- [x] Добавить тест блокировки owner lock из отдельного OS-процесса (multiprocessing spawn).
- [ ] Подтвердить Windows CI с новым cross-process test.


- [x] Сохранять audit decision при закрытии failed-блока после проверки доски.
- [ ] Подтвердить полный CI для последнего кода и cross-process owner lock.

### CI finding — closure audit classification (2026-11-01)
The first final CI run exposed a mismatch: `finish_chalk_block_task(accepted=False)` correctly leaves the block in `paused`, while the rejected task itself is `failed`. Closure audit classification now inspects task statuses, recording `close_failed_block` when a failed task exists and `close_paused_block` for interruption-only pauses. This preserves the distinction between block state and failed experiment state. The existing regression test asserts the failed-task path. Full CI must be rerun; G1 remains blocked until all jobs and Windows portable smoke-test pass.

### Итог CI gate — 2026-11-01
- [x] Исправить классификацию audit при закрытии paused-блока с failed-задачей (commit `dd976b04f6d6423726ad7382bac7223c12d8342b`).
- [x] Подтвердить полный CI на финальном HEAD `311299296559b9a5949f1e803f134b46436a2850`: geometry-tests, executor-tests и Windows portable build/startup smoke-test — success (run [41272291546](https://github.com/Kiddos19882/AutoDraw/actions/runs/41272291546)).
- [x] Подтвердить Windows portable build через `build_windows.bat`, включая `run_all_tests.py` и `smoke_test_portable.py`.
- [ ] Выполнить локальный Windows preflight на рабочей машине: калибровка, slider 1–30, Clear reference, canvas, Game Monitor heartbeat и подтверждение пустой тестовой доски.
- [ ] Запустить полный G1 block и принять все 12 уникальных ячеек; до этого G2/G3 не запускать.

CI/software gate закрыт. Live gate остаётся открытым, поскольку текущая среда не имеет доступа к пользовательской Windows GUI и игровой сессии.

## Live G1 — итоги и post-run fixes (2026-11-01)

- [x] Выполнить полный автоматизированный G1 block; второй блок принят 12/12.
- [x] Сохранить два журнала: первый stopped/failed, второй completed; не переписывать первичные manifests и Monitor runs.
- [x] Сверить все 12 exact CHALK captures и per-stroke pointDelta; зафиксировать сценарные средние и первичные значения.
- [x] Найти причину ложного отказа первого блока: один нулевой pointer candidate был засчитан как дополнительный штрих.
- [x] Исправить stroke_count и per-stroke breakdown: считать принятые stroke IDs с положительным суммарным pointDelta, нулевые candidates сохранять отдельно.
- [x] Добавить явное итоговое окно после завершения всех задач блока.
- [x] Добавить regression tests для нулевого кандидата и уведомления о завершении.
- [x] Подтвердить полный CI run 41276703424, HEAD c8d8c2c5588a0d423e48682962a4213ee725c808.
- [ ] Обновить локальную portable-сборку до HEAD c8d8c2c5588a0d423e48682962a4213ee725c808 и провести G2 live block (18 задач).
- [ ] После принятия G2 разблокировать G3.


## CHALK geometry matrix — после принятия G2 (2026-11-01)

- [x] Выполнить автоматизированный G2 block — 18/18 задач завершены.
- [x] Проверить exact CHALK, baseline/post pointCount, сумму DRAW_SAMPLE.pointDelta, stroke_count, радиус, dropped events и monitor errors для всех 18 captures.
- [x] Сохранить первичные результаты в commit `16a426b534de269ed967027bbe59f3daac4b97ec` без переписывания manifests.
- [x] Зафиксировать сценарные средние и отдельную per-stroke агрегацию для повторного покрытия в `docs/CHALK_GEOMETRY_MATRIX_G2_RESULTS.md`.
- [x] Принять G2 и открыть следующий gate.
- [ ] Выполнить G3: 27 независимых опытов (`point_step_px` 1/2/4 × `point_delay_ms` 5/10/20 × 3 повтора) на фиксированной геометрии `paint_consumption_long_lines`, радиус 10.
- [ ] Проверить точный CHALK, move calls, длительность, FPS, dropped events и качество capture; не считать move calls эквивалентом расхода CHALK.
- [ ] После G3 сформировать сводную модель с ограничениями и проверить её на независимых контрольных рисунках.


- [x] Подготовить G3 в коде: девять parameter cells (`point_step_px` 1/2/4 × `point_delay_ms` 5/10/20), три повтора на каждую, metadata/duplicate protection, journal validation, UI и analyzer support.
- [x] Добавить regression tests для G3 identity, deterministic randomized order, recovery и exact CHALK gate. Полный CI и Windows portable startup smoke-test остаются отдельным gate.

## G3 — программная реализация и live gate

- [x] Добавить G3 в matrix metadata и включить `point_step_px`/`point_delay_ms` в идентичность ячейки.
- [x] Добавить девять комбинаций параметров и три повтора (27 задач) в block plan.
- [x] Добавить строгую journal validation полного набора 27 ячеек.
- [x] Добавить G3 в Brush Test UI и gate по принятому G2.
- [x] Передавать фактические параметры G3 в Stage6/MouseExecutor и сохранять их в execution report без изменения пользовательского профиля.
- [x] Добавить analyzer support для раздельной проверки и агрегации девяти конфигураций.
- [x] Добавить regression tests для metadata, duplicate identity, block plan, journal validation и workflow config override.
- [x] Подтвердить полный GitHub Actions CI на актуальном HEAD `3dbf8f20bcea44c61290e49398e1a4daf182dbf9` (run `41340237207`).
- [ ] После software gate выполнить 27 live G3 экспериментов на пользовательской Windows/игровой сессии.
- [ ] Проанализировать CHALK, move calls, длительность, FPS, accepted points и dropped events отдельно для каждой конфигурации.


## Актуализация G3 gate — 2026-11-01

- [x] Подтвердить полный GitHub Actions CI на HEAD `e1872af08efbff7ee7c9ac771e6b9eb70b748c46`: run [41337768801](https://github.com/Kiddos19882/AutoDraw/actions/runs/41337768801), все три jobs success.
- [x] Подтвердить `geometry-tests`.
- [x] Подтвердить `executor-tests`.
- [x] Подтвердить Windows portable build и startup smoke-test.
- [x] Исправить три CI-дефекта: лишняя скобка, тесты вне unittest-класса, незакрытый docstring (commits `bf52f12`, `6594e28`, `e1872af`).
- [ ] Локальный Windows preflight: запуск portable-сборки, профиль/калибровка кисти, Clear reference, пустая тестовая доска, игровая canvas, heartbeat Game Monitor.
- [ ] После успешного preflight выполнить полный G3 block: 27/27 задач, девять комбинаций шага/задержки × три повтора.
- [ ] Проверить каждый capture: точный baseline/post CHALK, сумма DRAW_SAMPLE pointDelta, executor config из execution report, радиус 10, шесть штрихов, ноль dropped events/errors, валидный frame capture.
- [ ] Рассчитать статистику отдельно по девяти конфигурациям и только после этого сформировать модель расхода CHALK.

Software gate закрыт; live gate остаётся открытым. Автоматический Windows smoke-test в GitHub Actions не является подтверждением локальной игровой сессии или измерением расхода краски.


## 2026-11-01 — удалено визуальное подтверждение размера кисти после Game Monitor

По замечанию оператора устранены два последовательных диалога, которые требовали визуально подтвердить радиус после автоматической установки:
- `integrated_app.py::_start_brush_test_executor` больше не спрашивает пользователя, совпадает ли размер кисти с запрошенным;
- `BrushBehaviorTestTab._confirm_brush_before_test` больше не показывает `askyesno` после точного подтверждения Game Monitor.

Проверка не ослаблена: executor допускается к запуску только после свежего heartbeat Game Monitor с точным совпадением фактического радиуса и запроса. В handoff добавлена повторная fail-closed проверка `observation.radius == requested_brush`; при расхождении запуск блокируется. Источник проверки и факт автоматического подтверждения сохраняются в `experiment.json`, поле `visual_confirmation_required=false`. Потеря Monitor, отсутствие свежего heartbeat, несовпадение радиуса, ошибка коррекции или записи manifest по-прежнему останавливают тест.

Для G1/G2/G3 block runner это убирает лишний popup после каждого автоматического drag; Clear/blank-board и остальные обязательные предупреждения не затрагивались. Добавлены regression tests: точный Monitor radius запускает callback без диалога, mismatch блокирует handoff.

Изменения в commits: `bb32589cb9d450a03b1d5b5264732828812b8ed3`, `465346a58caf76b8566d99128361095324368366`, `c919610999c5ea9f4a1afebad937395e586dc4b9`. Требуется новый полный CI на изменённом HEAD; до его завершения успешный CI предыдущего G3 HEAD не распространяется на эти изменения.

## Удаление ручного подтверждения радиуса — 2026-11-01

- [x] Удалить popup визуального подтверждения после точного radius feedback Game Monitor в Brush Test UI.
- [x] Удалить повторный popup «Проверь размер кисти» в integrated app перед запуском тестового executor.
- [x] Сохранить строгую проверку свежего heartbeat и точного совпадения радиуса; mismatch остаётся fail-closed.
- [x] Добавить regression tests на автоматический запуск после exact Monitor match и блокировку mismatch.
- [x] Подтвердить полный CI и Windows portable smoke-test на актуальном HEAD (run `41340237207`).


## Актуализация G3 CI и следующих действий — 2026-11-01

- [x] Подтвердить полный GitHub Actions CI на актуальном HEAD `3dbf8f20bcea44c61290e49398e1a4daf182dbf9`: run [41340237207](https://github.com/Kiddos19882/AutoDraw/actions/runs/41340237207).
- [x] Подтвердить `geometry-tests` — success.
- [x] Подтвердить `executor-tests` — success.
- [x] Подтвердить `Windows portable build and startup smoke-test` — success.
- [x] Включить в CI подтверждение commit `8c93a498864973b9879c926627030bb7e1d3ce2a` с regression test основного приложения.
- [x] Синхронизировать WORK_LOG, PROJECT_STATUS, CHALK_TEST_BLOCKS_DESIGN, TESTS_AND_CI_MAP и CHANGELOG с результатом run.
- [ ] Локальный Windows preflight на рабочей машине: запуск актуальной portable-сборки, профиль/калибровка кисти, Clear reference, чистая тестовая доска, игровая canvas и свежий heartbeat Game Monitor.
- [ ] После успешного preflight выполнить полный G3 block: 27/27 задач, все девять сочетаний `point_step_px` 1/2/4 × `point_delay_ms` 5/10/20, по три повтора.
- [ ] Для каждого capture проверить точный baseline/post CHALK, сумму DRAW_SAMPLE pointDelta, фактический executor config из execution report, радиус 10, шесть штрихов, отсутствие dropped events/errors и валидный frame capture.
- [ ] Рассчитать статистику по девяти конфигурациям и только после принятия всех captures строить модель расхода CHALK.

**Текущий статус:** software/CI gate закрыт. Local/live gate открыт. Успешный GitHub Actions Windows smoke-test не заменяет локальную игровую сессию и не подтверждает расход краски.


## Срочная регрессия G3 — фокус окна после установки кисти (2026-11-01)

- [x] Найти источник возврата AutoDraw поверх игры после подтверждения кисти.
- [x] Исправить успешный автоматический handoff: не вызывать `deiconify/lift` перед запуском Stage6.
- [x] Сохранить восстановление окна для ручной установки кисти и ошибочных сценариев.
- [x] Добавить regression assertion для автоматического handoff.
- [ ] Подтвердить полный CI на новом code HEAD.
- [ ] Собрать/запустить обновлённую Windows portable-сборку и повторить один контрольный G3 запуск; убедиться, что игра остаётся в фокусе во время передачи executor.
- [ ] Только после этого возобновить полный G3 block 27/27.

Коммиты: `8f8923ded3d788e725206d31515d6f0ed221db3a`, `fd814517b584b9a800c95e4b6a19581a7afc33ce`.

## 2026-11-02 — оптимизация CI перед новой серией G3

- [x] Убрать дублирование push/pull_request CI для обновлений одной feature-ветки.
- [x] Включить concurrency cancellation и pip cache.
- [x] Разделить обязательные Game Monitor, Preparation/G3, Integration и Executor suites на параллельные jobs.
- [x] Убрать повторный запуск build-time test suite в CI только после успешного завершения отдельных обязательных jobs; сохранить обычный локальный `run_all_tests.py`.
- [x] Перенести длительные алгоритмические benchmarks на ручной запуск.
- [x] Добавить regression test фактического G3 UI plan routing и сохранения task identity/parameters.
- [ ] Подтвердить все обязательные jobs нового CI на конечном HEAD.
- [ ] Получить portable artifact, собранный после успешных test jobs.
- [ ] Выполнить локальный Windows preflight и закрыть старый paused G3 journal только через recovery UI с подтверждением доски.
- [ ] Создать новую чистую серию G3 из 27 задач и выполнить все captures.
- [ ] Проверить фактический executor config и точный CHALK для каждой ячейки; проанализировать девять конфигураций.

## 2026-11-02 — стабилизация Windows UI CI

- [x] Изолировать DATA_PATHS каждого UI test case во временном каталоге.
- [x] Не допускать чтение старых paused G3 journals и модальных recovery dialogs в CI UI tests.
- [x] Отменять deferred recovery scan при уничтожении owner frame.
- [x] Добавить regression test на отмену pending Tk callback.
- [x] Разделить root integration tests и ограничить время UI test step.
- [ ] Получить успешный CI на HEAD после этих изменений.

## 2026-11-02 — статус live G3 по commit 094381f

- [x] Принять и сохранить raw results серии `chalk-20261102-015749-7c1141` в commit `094381f1d3f005efc8b2324062cc1f2dacc277a5`.
- [x] Сверить 22 task identities с фактическими `executor_config`; mismatch не обнаружен.
- [x] Сверить радиус 10, 6/6 strokes и точный CHALK counter во всех 22 experiment summaries.
- [x] Выявить partial Monitor capture: `s4-d10-r2`, 434 `monitor_dropped_events`; не засчитывать его как полноценный повтор.
- [x] Зафиксировать 21 completed, 1 failed, 5 pending; блок закрыт со статусом stopped.
- [x] Записать аналитическую сводку `docs/CHALK_G3_PARTIAL_RESULTS_2026-11-02.md`.
- [ ] Проверить в коде validator/recovery, можно ли формально объединять результаты continuation-блока с текущей серией.
- [ ] Выполнить корректный повтор `s4-d10-r2` и пять pending задач, если continuation поддерживается; иначе определить новую полную серию без изменения/перезапуска закрытого блока.
- [ ] Получить девять конфигураций × три полноценных Monitor captures.
- [ ] После завершения матрицы рассчитать статистику и калибровочную модель CHALK.
- [ ] Отдельно проверить влияние радиуса кисти: в текущей G3 серии радиус фиксирован на 10.

### Recovery после partial G3 2026-11-02

Текущий code path не поддерживает штатное продолжение остановленного блока: `claim_next_chalk_block_task` не выдаёт задачи для `stopped`; recovery scan не рассматривает `stopped`; `resolve_interrupted_chalk_block_task` принимает только `interrupted`, а не `failed`; G3 builder формирует полный набор 27 задач. Поэтому текущий блок нельзя штатно продолжить на оставшихся шести ячейках. Не менять journal вручную. Использовать новый полный G3 block либо сначала реализовать и протестировать явную continuation/aggregation модель, связанную с исходным block ID.

## 2026-11-02 — диагностика переполнения Game Monitor

- [x] Проверить фактическую session проблемного G3 capture и сопоставить browser sent / collector received.
- [x] Проверить лимит `MAX_EVENTS=50000` и поведение `emit()` после достижения лимита.
- [x] Подтвердить, что `monitor_dropped_events` является накопительным session-счётчиком, а не per-run loss.
- [x] Выполнить детерминированную симуляцию заполнения буфера и продолжения доставки подписчику.
- [x] Задокументировать причину и границы доказательств в `docs/GAME_MONITOR_BUFFER_OVERFLOW_ANALYSIS_2026-11-02.md`.
- [ ] Разделить метрики локального export buffer, browser send failures, collector sequence gaps и per-run recorder drops.
- [ ] Исправить передачу cumulative `status.droppedEvents` в per-run report и acceptance gate.
- [ ] Добавить JS regression test для overflow при продолжающейся доставке подписчика.
- [ ] Добавить Python regression test: overflow предыдущих событий session не должен делать следующий run partial.
- [ ] Прогнать Game Monitor/Preparation tests и CI на конечном HEAD.
- [ ] Только после исправления и тестов планировать новый live G3; старый stopped journal не переоткрывать и не переписывать.
## 2026-11-02 — устранение ложного Game Monitor partial

- [x] Разделить cumulative Monitor export-buffer overflow и per-run RunRecorder drops.
- [x] Добавить start/end/delta для Monitor buffer overflow и Monitor error counters.
- [x] Добавить per-run delta Browser Bridge send failures.
- [x] Добавить обнаружение WebSocket sequence gaps на collector и фиксацию в активном run.
- [x] Удалить cumulative `monitor_dropped_events` из acceptance gate Brush Test.
- [x] Обновить G1/G2/G3 и radius-matrix validators на per-run loss/error metrics.
- [x] Добавить Node/Python/WebSocket/matrix regression tests.
- [x] Обновить техническую документацию.
- [ ] Проверить все новые regression tests и полный CI на конечном HEAD.
- [ ] Проверить portable build и локальный Windows/Firefox preflight.
- [ ] После успешных gates выполнить новый G3 block; старый stopped journal не возобновлять и не переписывать.


## 2026-11-02 — новая live G3 серия завершена (commit 35ae78e)

Источник первичных данных: [35ae78e31f9b6d357a4e8aa30cd12307d8c322e8](https://github.com/Kiddos19882/AutoDraw/commit/35ae78e31f9b6d357a4e8aa30cd12307d8c322e8). Полная аналитика: [CHALK_G3_RESULTS_2026-11-02.md](CHALK_G3_RESULTS_2026-11-02.md).

- [x] Выполнить новый G3 block `chalk-20261102-031830-a0f325`, block ID `d5d28990cb954610aa7f58534be9d3d7`.
- [x] Принять 27/27 задач: девять сочетаний `point_step_px` 1/2/4 × `point_delay_ms` 5/10/20, по три повтора.
- [x] Проверить все 27 experiment summaries: exact CHALK, совпадение sampled pointDelta, radius=10, 6/6 strokes, Monitor capture saved.
- [x] Проверить per-run транспорт: dropped_events=0, monitor_error_count_delta=0, bridge_send_failures_delta=0, collector_sequence_gap_count=0.
- [x] Проверить поведение local Monitor buffer overflow: положительный buffer delta в поздних captures не привёл к потере WebSocket/collector events и не блокировал acceptance.
- [x] Рассчитать средние, диапазоны CHALK и длительности по всем девяти конфигурациям.
- [x] Записать итоговый отчёт `docs/CHALK_G3_RESULTS_2026-11-02.md`; предыдущий stopped G3 journal не изменять.
- [ ] Проверить визуальное качество и непрерывность линий для кандидатов step=4 / delay=5 и step=4 / delay=10.
- [ ] Построить сегментированную модель прогноза CHALK на данных G1/G2/G3 и radius matrix.
- [ ] Проверить модель на коротких штрихах, диагоналях, кривых, поворотах, перекрытиях и заливках; не переносить коэффициент длинных линий на другие геометрии.

**Текущий статус:** live G3 завершён и принят. Следующая задача — оценка качества экономичного режима и калибровка модели CHALK; не требуется повторять G3.


## INT-006 — предварительная сегментированная модель (2026-11-02)

- [x] Сверить принятые результаты G1 (12/12), G2 (18/18), G3 (27/27) и radius matrix (21 опыт).
- [x] Построить предварительную регрессию прямых штрихов для profile radius=10 / step=2 / delay=10: `C ≈ 1.765 + 0.2988 × L`, 36 per-stroke observations.
- [x] Выделить короткие штрихи в отдельный эмпирический сегмент; не применять к ним длинную линейную регрессию.
- [x] Учесть повторное покрытие: повторный проход 200 logical px расходует примерно 61–62 CHALK и не получает скидку за перекрытие.
- [x] Выделить sampling-specific coefficients G3 для длинных горизонтальных линий.
- [x] Зафиксировать ограничения радиуса, Monitor trajectory coalescing и отсутствие независимой validation.
- [x] Выполнить первичный визуальный скрининг 15 representative PNG V1–V5 (P0/P1/P2); выводы и ограничения записаны в `CHALK_INT006_PNG_SCREENING_2026-11-02.md`.
- [x] Выполнить количественный pixel-level аудит всех 90 PNG (45 исходных +45 follow-up): continuity/max gap, centerline deviation, coverage width/variation, contour closure и parallel separation; 549 stroke rows, 900 pair rows.
- [x] Просмотреть диагностические overlays новых follow-up V1/V4/V5; ROI heuristic ambiguity проверена через pixel masks, не трактуется как отсутствие штрихов.
- [ ] Подготовить независимую validation-матрицу на нескольких изображениях и геометриях.
- [ ] Рассчитать абсолютную/относительную ошибку прогноза против точной pre/post `pointCount`.
- [ ] Определить safety margin только после validation; затем рассматривать INT-007 (интеграцию в preflight).

Документ модели: [CHALK_PRELIMINARY_SEGMENTED_MODEL_2026-11-02.md](CHALK_PRELIMINARY_SEGMENTED_MODEL_2026-11-02.md). Модель пока не production-ready. Код и пользовательские executor defaults не менялись.


## G3 visual gate — уточнение после просмотра оригинальных PNG (2026-11-02)

- [x] Получить непосредственно из GitHub все шесть `after_draw-board.png` для step=4/delay=5 и step=4/delay=10.
- [x] Вручную проверить непрерывность шести длинных горизонтальных линий во всех шести повторах.
- [x] Сопоставить визуальный результат с exact CHALK, move calls и длительностью.
- [ ] Проверить правый конец шестой линии без перекрытия курсором (если доступен чистый board crop или иной capture).
- [ ] Проверить step=4 на диагоналях и непрерывных поворотах.
- [ ] Проверить короткие штрихи, пересечения и плотное расположение линий.
- [ ] После геометрической validation провести независимую проверку прогнозной модели CHALK.

**Результат:** step=4 визуально приемлем для длинных горизонтальных линий G3. Это не основание менять общий production default. Отчёт: [CHALK_G3_VISUAL_QUALITY_AUDIT_2026-11-02.md](CHALK_G3_VISUAL_QUALITY_AUDIT_2026-11-02.md).


## 2026-11-02 — первичный скрининг PNG INT-006

- [x] Получить и просмотреть по одному representative `after_draw-board.png` для каждого сочетания V1–V5 × P0/P1/P2 (15 изображений).
- [x] Зафиксировать наблюдения по непрерывности, пересечениям, коротким отпечаткам, замыканию контуров и слиянию параллельных линий.
- [x] Зафиксировать ограничения V1/V3 (непреднамеренные пересечения), V2 (короткие движения как точки), V4 (курсором закрыта часть контура), V5 (spacing=8 сливается).
- [x] Рассчитать pixel-level метрики для исходных 45 captures: 252 per-stroke rows и 279 parallel-pair rows; CI artifact run `41392156994`.
- [x] Проверить сегментацию/маски на исходных captures и сохранить диагностические overlays; ограничения и ambiguous cases задокументированы.
- [x] Повторить pixel-level аудит на новых 45 follow-up captures из `e879a77`; 297/297 strokes coverage=1.0, zero gaps; V4 seams 27/27 covered; V5 spacing thresholds documented.

Отчёт исходного аудита: [CHALK_INT006_PIXEL_AUDIT_2026-11-02.md](CHALK_INT006_PIXEL_AUDIT_2026-11-02.md). Новые live-результаты: [CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md](CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md). Production defaults и estimator не менять.


## INT-006 — V2/V5 follow-up выполнены (2026-11-02)

- [x] Создать отдельный V2 scenario `int006_short_strokes_followup`: пять штрихов 12/16/20/24/30 logical px.
- [x] Создать отдельный V5 scenario `int006_intersections_spacing_sweep`: X/T/крест + пять пар spacing 8/12/16/20/24 logical px; 16 штрихов.
- [x] Подключить сценарии к matrix metadata, block planner, Brush Test UI и regression tests; старые scenario IDs и captures не переиспользуются.
- [x] Зафиксировать три профиля P0/P1/P2, три повтора и radius=10: по 9 captures на серию.
- [x] Подтвердить CI code HEAD `878bd1f`; обязательные jobs, Windows portable build/startup smoke-test и INT-006 PNG audit завершились success в run `41486593544`.
- [x] Пользователь выполнил V2 и V5 live blocks; вместе с V1/V3/V4 получено 45/45 captures. Exact CHALK и per-run Monitor integrity подтверждены.
- [x] Выполнить pixel-level аудит новых 45 follow-up PNG; 45/45 valid, 144/144 V5 strokes sufficient and gap-free; V5 target pair separation documented.

Инструкции: [V1/V3/V4](CHALK_INT006_V1_V3_V4_FOLLOWUP_2026-11-02.md), [V2/V5](CHALK_INT006_V2_V5_FOLLOWUP_2026-11-02.md). Итоги: [CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md](CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md).


### INT-006 — блокер готовности независимого validation harness (2026-11-02)

- [x] Сверить независимый D1–D5 протокол с текущими исходниками matrix, block planner/journal, Brush Test UI и executor handoff.
- [x] Подтвердить, что D1–D5 не подключены к существующим фазам и что analyzer не сравнивает runs с immutable prediction records.
- [x] Создать [аудит готовности harness](CHALK_INT006_HARNESS_READINESS_AUDIT_2026-11-02.md) и изменить статус validation protocol с READY FOR LIVE VALIDATION на BLOCKED.
- [ ] Реализовать отдельную INT006 phase без изменения production estimator/defaults.
- [ ] Добавить regression tests, подтвердить полный CI и подготовить Windows 10 preflight.


## INT-006 — frozen validation software gate (2026-11-02)

- [x] Подключить D1–D5 к отдельной фазе INT006 и 45-cell block journal.
- [x] Создать 15 frozen prediction records и hash-sealed artifact в journal до первого capture.
- [x] Связать prediction ID с каждой task/manifest и проверить ID на executor handoff.
- [x] Реализовать independent analyzer exact CHALK, journal/attempt/geometry/profile binding и run/per-stroke metrics.
- [x] Добавить regression tests: artifact round-trip/integrity, 45 cells, geometry mismatch, prediction ID и executor handoff.
- [x] Подтвердить software CI [41513389663](https://github.com/Kiddos19882/AutoDraw/actions/runs/41513389663): 667 passed, 82 subtests passed; Windows portable build/startup smoke-test и pixel audit success.
- [x] Выполнить live block D1–D5: 45/45 tasks completed, одна завершённая попытка на задачу, radius=10.
- [x] Провести предварительный аудит 45 experiment manifests и 45 Monitor reports: exact CHALK, stroke count/sum, zero dropped events/errors/Bridge failures/sequence gaps.
- [x] Пересчитать предварительные run-level и per-stroke метрики; результат записан в [CHALK_INT006_VALIDATION_PRELIMINARY_RESULTS_2026-11-03.md](CHALK_INT006_VALIDATION_PRELIMINARY_RESULTS_2026-11-03.md).
- [x] Исправить analyzer path binding для перенесённых capture bundles; добавить regression tests на Windows absolute path и journal task prediction ID / expected stroke count.
- [x] Добавить analyzer step и JSON artifact upload в `.github/workflows/geometry-tests.yml`.
- [x] Подтвердить новый CI после analyzer/workflow/binding changes и получить официальный analyzer JSON report: run 41532629748 SUCCESS, 45 accepted, 0 missing, 0 rejected.
- [ ] Проверка frozen artifact SHA-256 выполнена независимо и совпала; штатным analyzer ещё подтвердить полный journal/task/experiment/run/profile/geometry binding.
- [ ] На основании официального report определить safety margin и границы применимости модели.

INT-006 остаётся IN_PROGRESS до официального analyzer report и решения по safety margin; INT-007 — BLOCKED. Production estimator, executor defaults и sampling defaults не менять.


## 2026-11-03 — официальный analyzer run: geometry serialization mismatch

- CI run [41530634729](https://github.com/Kiddos19882/AutoDraw/actions/runs/41530634729) на commit `2d99869` завершился FAILURE только на шаге независимого INT-006 CHALK analyzer. Preparation/G3, Application integration, Executor regression, Game Monitor/bridge, Windows portable build и INT-006 pixel PNG audit завершились success; optional benchmarks skipped.
- Загруженный analyzer artifact содержит `status=incomplete`, `accepted_count=0`, `missing=45`, `rejected=45`; все 45 отклонений имеют причину `geometry_signature_mismatch`. Frozen artifact SHA-256 совпадает с ожидаемым `a0eab016e96a81e14bededd32cf5161dd943d6fc85a20b7eec17455f69d0c61c`.
- Root cause: frozen prediction хранит logical points как пары чисел, а реальный runtime DrawingPlan serializer сохраняет strokes с `closed`, служебным `metadata` и point objects `{x, y}`. Analyzer ошибочно сравнивал хеши/структуры разных сериализаций напрямую; captures и Monitor telemetry не признаны повреждёнными.
- Analyzer исправлен: отдельно проверяется hash фактического manifest representation, затем strokes нормализуются до frozen logical geometry и сравниваются с frozen plan/signature. Коэффициенты, prediction artifact, production estimator, executor defaults и sampling defaults не менялись.
- Regression fixture обновлён для реального runtime manifest shape. Commits: `8eba34f2ae402bbcf8af096f8b642a5cdcfb5eee` (fix), `dd64730e202ed6f6014fa2dd1a65c3100cc32018` (test).
- Повторная проверка выполняется workflow [41532629748](https://github.com/Kiddos19882/AutoDraw/actions/runs/41532629748) на HEAD `dd64730`; на момент записи run ещё выполняется. До его завершения quantitative validation остаётся PENDING, INT-006 — IN_PROGRESS, safety margin — not established, production eligibility — not validated.


## Следующие действия после geometry binding fix

- [x] Получить окончательный результат CI run 41532629748 на commit dd64730 — SUCCESS.
- [x] Проверить официальный analyzer artifact: hash, 45 accepted, 0 missing, 0 rejected, 15 complete groups, per-stroke metrics и все journal/task/experiment/run/profile bindings.
- [x] Сопоставить официальный report с предварительными метриками — расхождений, влияющих на выводы, нет.
- [ ] Отдельно принять решение по safety margin и расширить domain validation; до этого не менять production estimator/defaults и не запускать INT-007.
- [ ] INT-006R: реализовать отдельную radius × geometry matrix phase и CI gate по [плану](CHALK_RADIUS_GEOMETRY_CROSS_VALIDATION_PLAN_2026-11-03.md); live tests до software gate не запускать.


## DOC-017 — справочник Game Monitor и Bridge

**Статус:** DONE  
**Цель:** зафиксировать фактический API и поток данных Game Monitor/Bridge для дальнейшей разработки и диагностики.

- [x] Сверить Monitor 0.2.1, browser bridge и Python collector по исходникам рабочей ветки.
- [x] Описать методы, события, lifecycle, transport protocol, RunRecorder и JSON artifacts.
- [x] Добавить документ в `docs/README.md` и `MODULE_REFERENCE.md`.

**Результат:** [GAME_MONITOR_BRIDGE_REFERENCE.md](GAME_MONITOR_BRIDGE_REFERENCE.md). Изменения кода и live-проверки не входят в задачу.


## Историческая запись — FILL-001 до реализации UI/runner (2026-11-03)

- [x] Проверить фактический UI → integrated_app → Stage 6 → runtime binder call graph.
- [x] Зафиксировать исходное отсутствие UI/runner handoff и task-specific FILL001 override на момент аудита.
- [x] Реализовать отдельную вкладку FILL-001 и fail-closed handoff в DrawingPlan/Stage 6.
- [ ] Выполнить один Windows live preflight.
- [ ] Только после успешного preflight разрешить 45-cell live matrix.

Подробные основания и критерии: [CHALK_FILL001_AUTODRAW_INTEGRATION_AUDIT_2026-11-03.md](CHALK_FILL001_AUTODRAW_INTEGRATION_AUDIT_2026-11-03.md).


## FILL-001 — CI closure, ожидается Windows live preflight (2026-11-03)

- [x] Подтвердить полный GitHub Actions run [41692129486](https://github.com/Kiddos19882/AutoDraw/actions/runs/41692129486): все обязательные jobs, включая Windows portable build/startup smoke-test, SUCCESS.
- [x] Получить действующий artifact `autodraw-g3-preflight-build` ID `13258221572`: [artifact](https://github.com/Kiddos19882/AutoDraw/actions/runs/41692129486/artifacts/13258221572).
- [ ] Пользователь выполняет ровно один live preflight: `rectangle / radius 10 / repeat 1` через вкладку FILL-001.
- [ ] Проверить task ↔ DrawingPlan ↔ executor report ↔ Bridge session/run identity, фактические P1 параметры, exact `pointCount` delta и реальные before/after PNG/ROI; подтвердить coverage ≥99% и leakage=0.
- [ ] Только после успешного preflight и отдельного согласования переходить к 45 live captures.

CI SUCCESS не является live evidence; 45-cell matrix остаётся BLOCKED.


## 2026-11-04 — FILL-001-RS CI PASS и анализ опубликованных evidence

- [x] Подтвердить полный CI run [41780241017](https://github.com/Kiddos19882/AutoDraw/actions/runs/41780241017): Application integration, Executor regression, Preparation/G3, Game Monitor/Bridge, INT-006 PNG audit, Windows portable build/startup smoke-test — SUCCESS; optional benchmarks — SKIPPED.
- [x] Подтвердить FILL-001-RS static sweep artifact ID `13299430831`: 2,238 candidates, 62 accepted, 15/15 selected shape×radius cells прошли offline coverage≥99% / leakage=0.
- [x] Проверить INT-006 PNG artifact ID `13299470914`: 90 valid captures, 549 stroke rows, coverage=1.0, zero gaps.
- [x] Проверить INT-006 frozen CHALK artifact ID `13299121807`: 45/45 accepted, 0 missing/rejected; safety margin не установлен, production eligibility не подтверждена.
- [x] Проверить INT006R radius × geometry artifact ID `13299101877`: 45/45 accepted; exact CHALK сравнен по radius 1/10/30 при P1.
- [x] Получить 45 пар INT006R before/after PNG и manifests (artifact ID `13299381257`, 180 файлов).
- [ ] Завершить ручной visual review всех 45 пар INT006R PNG; текущий analyzer gate — `pending_manual_review`.
- [ ] Установить safety margin и границы применимости frozen INT-006 model отдельным решением; до этого `production_eligibility=not_validated`.
- [ ] Отдельно повторно оценить FILL-001-RS live preflight capture по фактическим неизменённым PNG и executor mapping; CI static sweep не заменяет live CHALK/capture evidence.

Радиус не показал монотонного влияния на расход в пяти geometry scenarios. Средние CHALK radius 1/10/30: D1 62.667/62.333/63.333; D2 71.667/71.000/71.000; D3 100.000/100.667/99.667; D4 14.333/14.667/15.333; D5 88.333/89.667/89.667. Не делать вывод о незначимости радиуса за пределами протестированных геометрий, P1 и радиусов.

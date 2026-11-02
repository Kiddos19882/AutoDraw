# Реестр задач AutoDraw

Реестр содержит документационные и технические задачи проекта. Аналитические этапы 7–10 отменены и в backlog не включаются; INT-001 и последующие задачи ресурсной оптимизации являются отдельной инициативой.

## Статусы

- TODO — не начато.
- IN_PROGRESS — выполняется.
- BLOCKED — ожидает решения или входных данных.
- DONE — выполнено и проверено.
- ON_HOLD — отложено.
- CANCELLED — отменено пользователем или решением проекта.

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
| DOC-011 | DONE | Документировать UI и интеграционные точки | docs/UI_INTEGRATION_MAP.md: восемь вкладок, создание компонентов, callbacks, синхронизация области и передача планов |
| DOC-012 | DONE | Документировать профили, настройки и результаты | DATA_FORMATS_AND_PROFILES.md и FILE_STORAGE_CATALOG.md: схемы, пути, результаты, runtime-файлы и резервное копирование |
| DOC-013 | DONE | Составить карту импортов | DEPENDENCY_MAP.md содержит прямые импорты всех 40 preparation и 13 executor production-модулей; TESTS_AND_CI_MAP.md содержит прямые импорты всех 46 найденных test_*.py файлов из трёх тестовых каталогов и отдельную отметку helper-модуля |
| DOC-014 | DONE | Проверить относительные Markdown-ссылки и индекс | Проверены 67 относительных ссылок в 35 документах; все цели существуют, якорные фрагменты в ссылках отсутствуют; цели основного docs-индекса существуют |
| DOC-015 | DONE | Сверить API-справочники и каталог путей с текущими исходниками | Объявления 40 модулей preparation и 13 модулей executor сопоставлены с исходниками; ключевые точки UI и общие адаптеры проверены; FILE_STORAGE_CATALOG сверён с integrated_app.py и владельцами путей; исправлена нумерация PREPARATION_API_REFERENCE.md |

## Измерение игрового ресурса CHALK и оптимизация рисования

| ID | Статус | Задача | Результат / границы |
|---|---|---|---|
| INT-001 | DONE | Определить источник игрового CHALK и семантику счётчика | Фактический расход — точная delta игрового `pointCount`; отчёт [CHALK_RADIUS_MATRIX_RESULTS.md](CHALK_RADIUS_MATRIX_RESULTS.md) содержит ограничения радиусной серии. |
| INT-002 | DONE | Определить resource snapshot и baseline/delta протокол | Контракт точного pre/post CHALK определён и используется в принятых экспериментах. |
| INT-003 | IN_PROGRESS | Завершить оценку overhead Game Monitor | Exact counter и telemetry подтверждены. Осталось сопоставимое A/B/C измерение Monitor off / версий Monitor с отдельными FPS, длительностью и overhead. Не блокирует точность CHALK capture, но нужен для оценки накладных расходов. |
| INT-004 | DONE | Автоматически собирать telemetry и связывать её с experiment ID | WebSocket bridge, per-run capture, RunRecorder и запись monitor report/идентификаторов в experiment manifest использованы в принятых G1–G3 captures. Overhead comparison относится к INT-003. |
| INT-005 | DONE | Реализовать автоматизированную лабораторию CHALK-экспериментов | Matrix/block runner, task identity, повторения, manifest, recovery/fail-closed gates и capture acceptance использованы для G1 12/12, G2 18/18 и G3 27/27. |
| INT-006 | IN_PROGRESS | Геометрическая validation step=4 и независимая validation модели CHALK | Протокол V1–V5 зафиксирован; harness расширен на базе G3: matrix metadata/validator, block planner/journal, Brush Test UI, task-specific executor override и regression tests. Пять V-блоков × 9 задач = 45 captures. CI и live captures ещё не подтверждены; независимая validation модели и safety margin остаются открытыми. Production defaults/estimator не менять. |
| INT-007 | BLOCKED | Интегрировать валидированную модель в preflight/resource estimator AutoDraw | Начинать только после независимой validation INT-006 и определения консервативного safety margin. |
| INT-008 | TODO | Оптимизировать кисти, траектории, порядок и покрытие | Подбирать способ построения рисунка в пределах квоты CHALK с учётом качества покрытия; зависит от INT-006/007. |
| INT-009 | TODO | Сравнить прогноз с фактом и проверить качество | Проверить на независимых рисунках прогноз, exact CHALK delta, визуальное качество и устойчивость к разным типам геометрии. |

**Актуальный приоритет INT-006:** см. [план дальнейших действий](CHALK_NEXT_STEPS_PLAN_2026-11-02.md) и [исполнительный протокол INT-006](CHALK_INT006_EXECUTION_PROTOCOL_2026-11-02.md). Исторические чек-листы ниже сохраняют ход выполнения и не переопределяют статусы таблицы.
## Отменённые работы

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
- [ ] Выполнить pixel-level аудит шести G3 captures для step=4/delay=5 и step=4/delay=10: continuity, max gap, centerline deviation, coverage width.
- [ ] Если PNG невозможно проверить автоматически, выполнить ручную проверку исходных изображений; не считать ROI heuristic достаточным подтверждением.
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

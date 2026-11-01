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
| INT-001 | DONE | Статическая инвентаризация связки Brush Test UI, Game Monitor и игрового счётчика | Установлена семантика CHALK через количество точек `atom.points`; выявлены разрывы интеграции, ограничения экспорта и текущей модели AutoDraw. Исходники и данные не изменялись, тесты не запускались |
| INT-002 | DONE | Статически спроектировать низкозатратный снимок CHALK и протокол baseline/delta | Определены контракт resource snapshot, правила точности, контрольные точки и требования к устранению повторных O(N)-обходов. Прямой источник значений и overhead ещё требуют runtime-проверки |
| INT-003 | IN_PROGRESS | Проверить точный источник CHALK, overhead Monitor и достоверность тестовой геометрии | Browser WebSocket smoke handshake подтверждён артефактами `ready→pong`; Game Monitor 0.2.1 работал в игровом iframe. A/B/C pointCount deltas: A=53/52/52, B=0*/52/52, C=50/52/52; B-1 невалиден (игровые точки не добавлены), а в повторах 2/3 все режимы дали 52. Для C diagnostic snapshot совпал с точным счётчиком. FPS probes дают 60 FPS, но не разделены по режимам, поэтому overhead не измерен. Boundary probe: 4/4 визуально видимых штриха, ΔpointCount=52; y=0/240 подтверждены acceptedPoint, горизонтальные acceptedPoint остановились около x=2.21/458.21, точные x=0/460 не доказаны. Полную матрицу кистей не запускать до раздельного A/B/C FPS/duration и уточнения горизонтальных границ. Влияние размера кисти ещё не измерено. |
| INT-004 | IN_PROGRESS | Автоматически собирать Game Monitor telemetry через WebSocket и связывать её с experiment ID | Реализованы browser event subscription, loopback WebSocket collector, автоматические per-run JSON, точный pre/post CHALK delta, acceptedPoint и per-stroke FPS. Brush Test UI автоматически копирует подходящий run в `monitor_report.json` и записывает session_id/run_id/CHALK/FPS в `experiment.json` по времени before_draw и радиусу. Не завершены live Firefox validation, проверка корреляции и overhead bridge |
| INT-005 | TODO | Реализовать и провести автоматизированную лабораторию кистей по целевой архитектуре | Видение и полный жизненный цикл описаны в [BRUSH_TEST_AUTOMATION_VISION.md](BRUSH_TEST_AUTOMATION_VISION.md). Требуются live-подтверждение logical→screen transform, генератор DrawingPlan, batch orchestrator, подтверждение радиуса, pre/post CHALK, bridge/Recorder, матрица и fail-safe; исполнитель — MouseExecutor/PyAutoGUI |
| INT-006 | TODO | Построить и валидировать модель расхода игровых точек | Разделить точное измерение и калиброванную оценку; определить консервативный прогноз |
| INT-007 | TODO | Интегрировать модель в preflight/resource estimator AutoDraw | Прогноз до запуска с безопасным бюджетом и явным статусом достоверности |
| INT-008 | TODO | Оптимизировать кисти, траектории, порядок и покрытие | Максимизировать качество рисунка в пределах игрового лимита CHALK |
| INT-009 | TODO | Сравнить прогноз с фактом и проверить качество | Сохранить отклонение прогноза, фактическую дельту и визуальные метрики |

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

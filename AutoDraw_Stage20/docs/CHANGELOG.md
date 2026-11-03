## 2026-11-03 — FILL-001 frozen target masks implementation

- Добавлен `source/preparation/chalk_fill_experiment.py` с тремя детерминированными frozen masks на logical canvas 460×240: rectangle, wide_irregular, narrow_irregular.
- Площади 44 653 / 45 159 / 44 879 px; разброс max/min — 1,133%, в пределах ±5%.
- SHA-256 масок закреплены в коде; добавлены 7 regression tests на hash, площадь, геометрию, связность и invalid input.
- Локальный тестовый прогон — 7 passed. Полный GitHub Actions для новых commits пока не подтверждён; fixed-radius generator, matrix/block harness и live captures не готовы.

## 2026-11-03 — FILL-001 technical design review

- Проверены существующие interior-fill и outline-first planners: оба используют смешанные ширины кисти и не подходят для контролируемого сравнения одного фиксированного радиуса.
- Определена изолированная архитектура `chalk_fill_experiment.py`: frozen masks, fixed-radius plans, raster footprint simulation, matrix/journal/analyzer gates.
- Зафиксированы критерии FILL-001: coverage ≥99%, leakage=0, три формы × пять радиусов × три повтора. Подробности: [harness design](CHALK_FILL001_HARNESS_DESIGN_2026-11-03.md).
- Production planners, estimator, executor/sampling defaults и `master` не менялись; harness пока не реализован.

## 2026-11-03 — INT006R visual audit завершён и packaging CI исправлен

- Исправлено имя before-capture PNG в CI packaging: использовано фактическое `before_clear-board.png` вместо `before_draw-board.png` (commit `c60b8cf`).
- Полный workflow [41563236073](https://github.com/Kiddos19882/AutoDraw/actions/runs/41563236073) завершился SUCCESS: все обязательные regression, integration, Game Monitor/Bridge, PNG analyzer и Windows portable build jobs прошли.
- Упакованы все 45 пар PNG (90 board images); ручной визуальный аудит завершён.
- Найдены ограничения качества: radius 1 оставляет видимый разрыв соединения D2 polygon; radius 30 объединяет первые три короткие детали D4. Подробности: [visual audit report](CHALK_INT006R_VISUAL_AUDIT_2026-11-03.md).
- INT006R закрыт как измерительная фаза с геометрическими ограничениями; следующий этап — FILL-001. INT-007 остаётся BLOCKED.

# История изменений документации и проекта

## 2026-11-03 — engine audit и уточнение отчёта INT006R

- Добавлен статический разбор клиентского engine bundle: `updateLess()` считает точки, а `setRadius()` задаёт толщину линии через `lineStyle`; прямого radius multiplier в CHALK counter нет.
- Уточнён FILL-001: для каждого радиуса требуется собственный путь покрытия одной frozen target mask, а не одинаковая траектория с разным размером кисти.
- Исправлено поле `sampling_profile.other_executor_parameters`, чтобы в нём не дублировались устаревшие P0 значения `point_step_px=2` и `point_delay_ms=10`.
- Regression test фиксирует точное представление P1; повторный CI run [41560787871](https://github.com/Kiddos19882/AutoDraw/actions/runs/41560787871) выполняется.

## 2026-11-03 — CI для реального INT006R dataset

- В `.github/workflows/geometry-tests.yml` добавлен отдельный запуск `chalk_int006r_validation.py` на committed live journal/capture bundle и загрузка JSON artifact `autodraw-int006r-live-validation`.
- Workflow [41559932955](https://github.com/Kiddos19882/AutoDraw/actions/runs/41559932955) запущен; результат ожидается. Это отдельная проверка реальных данных, а не synthetic fixture.

## 2026-11-03 — INT006R live results и FILL-001

- Добавлен [отчёт INT006R live results](CHALK_INT006R_LIVE_RESULTS_2026-11-03.md): 45/45 задач, exact CHALK, sampled/per-stroke delta match, observed radius match и нулевые Monitor/Bridge integrity errors.
- Зафиксированы средние расходы radius 1/10/30: 67.40/67.67/67.80 CHALK; разница суммарных расходов — около 0.6%.
- INT006R остаётся IN_PROGRESS до официального CLI analyzer на реальном bundle и ручного visual audit всех PNG.
- Добавлен действующий план [FILL-001](CHALK_FILL_AREA_RADIUS_EFFICIENCY_PLAN_2026-11-03.md): 3 формы областей × 5 радиусов × 3 повтора (45 captures).
- Production estimator, frozen model, executor/sampling defaults и master не менялись.



## 2026-11-03 — INT006R software gate PASS

- Полный workflow [41540054975](https://github.com/Kiddos19882/AutoDraw/actions/runs/41540054975) на code HEAD `28b56a9` завершился SUCCESS.
- Preparation/G3: 682 passed, 82 subtests passed, 24 warnings; Application integration, Executor regression, Game Monitor/Bridge, INT-006 PNG audit и Windows portable build/startup smoke-test — success.
- Положительный synthetic analyzer fixture подтвердил полный 45/45 набор с Monitor и PNG evidence; визуальная оценка остаётся отдельным manual gate.
- INT006R live captures не запускались. Следующий этап — локальный Windows preflight и контролируемая live matrix. Production estimator/defaults и master не менялись.



## 2026-11-03 — реализация отдельной фазы INT006R

- Добавлены phase/scenario contracts для D1–D5R, радиусов 1/10/30 и фиксированного P1 (step=4, delay=5 ms).
- Block planner/journal расширен отдельной 45-cell матрицей `(scenario, radius, repeat)`; добавлены fail-closed проверки уникальности и соответствия параметров.
- Brush Test и executor handoff поддерживают установку и проверку радиуса конкретной задачи; ручной запуск сценариев INT006R запрещён.
- Добавлен независимый analyzer exact CHALK и regression tests; frozen INT-006 model и prediction artifact не изменялись.
- Software CI для нового HEAD ожидается; live captures не выполнялись.



## 2026-11-03 — план radius × geometry cross-validation

- Сопоставлены два подтверждённых источника: radius matrix 21/21 на шести длинных горизонтальных линиях (радиусы 1–30, 722–728 CHALK) и официальный INT-006 D1–D5 при фиксированном radius=10.
- Вывод: radius matrix не показывает систематического эффекта для длинных горизонтальных линий, но не отвечает на вопрос для коротких деталей, диагоналей, пересечений и повторного покрытия.
- Создан [CHALK_RADIUS_GEOMETRY_CROSS_VALIDATION_PLAN_2026-11-03.md](CHALK_RADIUS_GEOMETRY_CROSS_VALIDATION_PLAN_2026-11-03.md): предложена матрица D1–D5 × radius 1/10/30 × 3 повтора при P1 (45 captures). Требуется отдельная experimental phase/harness и успешный CI до live запуска.
- До результатов не вводить radius multiplier и не менять production estimator/defaults.


## 2026-11-03 — INT-006 official quantitative validation PASS

- Повторный CI [41532629748](https://github.com/Kiddos19882/AutoDraw/actions/runs/41532629748) на commit `dd64730e202ed6f6014fa2dd1a65c3100cc32018` завершился SUCCESS. Preparation/G3: 669 passed, 82 subtests passed; Application integration, Executor regression, Game Monitor/bridge, Windows portable build/startup smoke-test, PNG audit и независимый analyzer — success. Optional algorithm benchmarks skipped.
- Artifact `autodraw-int006-chalk-validation` (ID `13182727663`): `status=complete`, 45 accepted, 0 missing, 0 rejected, 15/15 groups complete, 3 repeats per group, 243 stroke rows. SHA-256 frozen artifact совпал с journal.
- Official metrics: run-level MAE 1.408, RMSE 1.967, bias -0.875, MAPE 2.134%, max absolute error 4.94, max underprediction 1.82 CHALK. Per-stroke MAE 0.439, RMSE 0.544, max underprediction 1.085 CHALK.
- P1 (step=4, delay=5 ms) — лучший совокупный профиль на D1–D5: MAE 0.657, RMSE 0.838, MAPE 1.178%, max underprediction 0.92 CHALK. P1 остаётся экспериментальным кандидатом, не production default. Эмпирический guard 1 CHALK покрывает максимум этой выборки, но не является статистической гарантией; D3/P1 repeat σ≈1.41.
- Полный отчёт: [CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md](CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md). Analyzer geometry serialization fix и runtime-shaped regression fixture: commits `8eba34f` и `dd64730`.
- `safety_margin_status=not_established`, `production_eligibility=not_validated`; production estimator/defaults и master не менялись. INT-006 остаётся IN_PROGRESS до отдельного решения по safety margin и расширения domain validation; INT-007 остаётся BLOCKED.


## 2026-11-03 — официальный analyzer run: geometry serialization mismatch

- CI run [41530634729](https://github.com/Kiddos19882/AutoDraw/actions/runs/41530634729) на commit `2d99869` завершился FAILURE только на шаге независимого INT-006 CHALK analyzer. Preparation/G3, Application integration, Executor regression, Game Monitor/bridge, Windows portable build и INT-006 pixel PNG audit завершились success; optional benchmarks skipped.
- Загруженный analyzer artifact содержит `status=incomplete`, `accepted_count=0`, `missing=45`, `rejected=45`; все 45 отклонений имеют причину `geometry_signature_mismatch`. Frozen artifact SHA-256 совпадает с ожидаемым `a0eab016e96a81e14bededd32cf5161dd943d6fc85a20b7eec17455f69d0c61c`.
- Root cause: frozen prediction хранит logical points как пары чисел, а реальный runtime DrawingPlan serializer сохраняет strokes с `closed`, служебным `metadata` и point objects `{x, y}`. Analyzer ошибочно сравнивал хеши/структуры разных сериализаций напрямую; captures и Monitor telemetry не признаны повреждёнными.
- Analyzer исправлен: отдельно проверяется hash фактического manifest representation, затем strokes нормализуются до frozen logical geometry и сравниваются с frozen plan/signature. Коэффициенты, prediction artifact, production estimator, executor defaults и sampling defaults не менялись.
- Regression fixture обновлён для реального runtime manifest shape. Commits: `8eba34f2ae402bbcf8af096f8b642a5cdcfb5eee` (fix), `dd64730e202ed6f6014fa2dd1a65c3100cc32018` (test).
- Повторная проверка выполняется workflow [41532629748](https://github.com/Kiddos19882/AutoDraw/actions/runs/41532629748) на HEAD `dd64730`; на момент записи run ещё выполняется. До его завершения quantitative validation остаётся PENDING, INT-006 — IN_PROGRESS, safety margin — not established, production eligibility — not validated.

## 2026-10-31

### Added
- Зарегистрирована техническая инициатива INT-001—INT-002 по измерению игрового CHALK и ресурсной оптимизации рисования.
- В WORK_LOG и DECISIONS зафиксирована измерительная основа: расход изолированного опыта — дельта `pointCount`, остаток — `max - pointCount`.

### Changed
- PROJECT_STATUS и ROADMAP переключены с завершённой документационной инициативы на текущую задачу измерения CHALK; документирование результатов выполняется без отдельного запроса, но разрешения на код и тесты остаются раздельными.
- TASKS дополнен статусами INT-001 (DONE) и INT-002 (TODO).

### Added
- Добавлен TESTS_AND_CI_MAP.md: тестовые наборы, прямые зависимости проверенных тестов, CI jobs, benchmark и диагностики.
- Добавлен FILE_STORAGE_CATALOG.md: пути пользовательских данных, runtime-планы, результаты, brush experiments и структура .autodraw.
- Добавлен DEPENDENCY_MAP.md с картой точек входа, основных импортов и общих адаптеров.
- DATA_FORMATS_AND_PROFILES.md дополнен схемой execution report v2, ExecutionSummary и color execution report.
- Добавлен EXECUTOR_API_REFERENCE.md с интерфейсами Stage6, MouseExecutor, цветного исполнения, диагностики и планирования.
- DATA_FORMATS_AND_PROFILES.md дополнен записью наблюдения поведения кисти и структурой `experiment.json`.
- Добавлен UI_INTEGRATION_MAP.md с картой восьми вкладок, callback-связей и передачи планов в executor.
- DATA_FORMATS_AND_PROFILES.md дополнен форматами game point calibration, engine point calibration и отчётами моделей ресурса/расхода.
- DATA_FORMATS_AND_PROFILES.md дополнен структурой JSON-экспорта Game Monitor 0.1.2.
- DATA_FORMATS_AND_PROFILES.md дополнен форматом журнала paint-limit, снимком brush workflow и структурами визуальных измерений.
- Добавлен DATA_FORMATS_AND_PROFILES.md со схемами профилей рабочей области, палитры и калибровки, а также основными структурами цветных и многодосочных планов.
- Добавлен первичный справочник интерфейсов модулей preparation; в него включена инвентаризация конструкторов, методов UI-классов и внешних callback-зависимостей.
- Создан каталог структурной документации docs/.
- Добавлены документы архитектуры, компонентов, конфигурации и разработки.
- Добавлены файлы управления проектом.
- Добавлен справочник общих геометрических моделей и формата .autodraw.

### Changed
- PREPARATION_API_REFERENCE.md сверён с объявлениями исходников; исправлена повторяющаяся нумерация разделов.
- FILE_STORAGE_CATALOG.md сверён с конфигурацией каталогов, runtime-передачей и владельцами данных в integrated_app.py.
- DOC-015 закрыта: выполнена структурная сверка API preparation/executor и файлового хранилища.
- Проверены локальные ссылки основного docs/README.md: все целевые файлы присутствуют в рабочей ветке.
- CONFIGURATION_AND_DATA.md теперь отделяет основные каталоги приложения от исторических/экспериментальных каталогов и ссылается на FILE_STORAGE_CATALOG.md.
- DEPENDENCY_MAP.md дополнен полной матрицей прямых импортов 40 preparation и 13 executor production-модулей.
- Индекс README.md дополнен каталогом файлового хранилища; исправлена некорректная строка таблицы.
- DOC-010 закрыта: EXECUTOR_API_REFERENCE.md охватывает все 13 модулей executor из структурного справочника.
- DOC-009 закрыта: PREPARATION_API_REFERENCE.md охватывает все 40 модулей preparation из структурного справочника.
- PREPARATION_API_REFERENCE.md уточнён по сигнатуре build_brush_test_record и конструкторам UI-компонентов.
- DOC-011 закрыта после документирования UI и интеграционных точек единого приложения.
- DOC-012 закрыта после документирования основных профилей, планов, лабораторных и калибровочных результатов, а также экспорта Game Monitor.
- Индекс, roadmap, реестр задач, статус проекта и журнал работ обновлены в связи с документированием профилей и планов.
- PREPARATION_API_REFERENCE.md дополнен методами UI-компонентов preparation и точками передачи callback-зависимостей.
- Stage20 README связан с новым каталогом документации.
- Roadmap и реестр задач сфокусированы на документационной инициативе.
- Статус аналитического плана обновлён в соответствии с решением пользователя.

### Cancelled
- Аналитические этапы 7–10 отменены пользователем. Исходный план сохранён в архивном статусе.

## 2026-10-31 — INT-002: проектирование CHALK snapshot

### Added
- Зафиксирован контракт ресурсного снимка CHALK с baseline/post-test delta, checkpoint, источником данных и признаком точности.
- В ROADMAP и TASKS зарегистрированы INT-003—INT-009: runtime/A-B-проверка, bridge capture, экспериментальная матрица, модель и её интеграция.

### Changed
- Уточнено описание существующих ресурсных моделей: game-point и engine-point calibration являются оценками, а не прямым счётчиком игры.
- Зафиксировано требование не выполнять дополнительные O(N)-обходы `atom.points` в Monitor на каждом событии/кадре.
- INT-002 закрыта как статическое проектирование; INT-003 выделена для runtime-проверки точного источника CHALK и A/B-измерения overhead.

## Правила ведения

- Не добавлять каждую мелкую опечатку.
- Группировать изменения по версиям или датам.
- Не заявлять о функциях, которых нет в текущих исходниках.
- Аналитические выводы добавлять только при наличии проверяемого основания; явно указывать источник, метод и ограничения достоверности.
- Ссылаться на commit, если изменение уже зафиксировано в Git.


## 2026-10-31 — документационная инвентаризация и ссылки

- Завершена матрица прямых импортов 46 тестовых файлов в `TESTS_AND_CI_MAP.md`; DOC-013 закрыта.
- Проверены 67 относительных Markdown-ссылок в 35 документах, все локальные цели существуют; DOC-014 закрыта.
- Обновлены TASKS, PROJECT_STATUS и ROADMAP.
- Код, тесты, UI, benchmarks и сборка не запускались.


## 2026-10-31 — INT-003: точный CHALK snapshot и Game Monitor 0.2.0

### Added
- Добавлены Node.js поведенческие тесты Game Monitor: точность `max-less`, отсутствие обхода `atom.points` в hot path, обработка unavailable и сверка с диагностическим подсчётом.
- В CI добавлен запуск `node --test` для Game Monitor.

### Changed
- В игровом bundle статически подтверждены поля `BoardPane.max` и `BoardPane.less`; событие CHALK использует только `percent`, но точные целые значения доступны на экземпляре доски.
- Game Monitor обновлён с 0.1.2 до 0.2.0: ресурсный snapshot читает `max`/`less` за O(1), а полный обход `atom.points` оставлен только в явном `diagnosticSnapshot()`.
- Экспорт дополнен текущим `resourceSnapshot`; при отсутствующих/невалидных engine-полях точность не имитируется и array fallback не выполняется.
- INT-003 остаётся IN_PROGRESS до живой runtime-сверки и A/B-замера FPS/длительности без Monitor и с Monitor.


- Добавлен read-only `inspect()` для контрольных точек без активных wrappers/polling; это позволяет снимать точные `max`/ `less` в режиме A после `stop()`.


### 2026-10-31 — автоматизация CHALK-экспериментов
- В GAME_MONITOR_BRUSH_LAB_PLAN.md зафиксирован переход от ручной отрисовки к параметрическим DrawingPlan, исполняемым существующим MouseExecutor/PyAutoGUI.
- Уточнена матрица INT-005: пакетные повторы, фиксируемые параметры траектории/исполнителя, автоматические checkpoints и привязка артефактов к experiment_id/run_id.
- Зафиксированы границы: игровой счётчик нельзя подменять вызовами внутренних методов или изменением atom.points; текущая запись описывает решение и существующую основу, но не заявляет реализацию пакетного runner.


## 2026-10-31 — INT-003: геометрический блокер Brush Test

- Исправлено описание логического размера доски Game Monitor: 420×240, экранный ROI учитывается отдельно.
- Зафиксировано, что текущий Brush Test передаёт экранные размеры ROI в генератор плана, а MouseExecutor прибавляет origin без применения масштаба.
- Добавлено требование к явному преобразованию logical→screen и unit-тестам до проведения матрицы CHALK.
- Это документирование статического результата; исходники и тесты пока не изменялись.


## 2026-10-31 — целевая архитектура автоматизированной лаборатории кистей

### Added
- Добавлен `docs/BRUSH_TEST_AUTOMATION_VISION.md`: целевая архитектура полного автоматического цикла CHALK-экспериментов, роли компонентов, матрица, checkpoints, manifest, fail-safe и критерии готовности.

### Changed
- Индекс документации дополнен ссылкой на видение модуля.
- INT-005 в TASKS и PROJECT_STATUS связана с целевой архитектурой и текущим блокером logical→screen transform.

### Boundaries
- Документ описывает целевое состояние и не означает, что batch runner, bridge, transform или автоматический анализ уже реализованы.
- Исходники, тесты, CI и runtime не изменялись/не запускались.


## 2026-10-31 — быстрый индекс модуля автоматических тестов кистей

### Added
- Добавлен `docs/BRUSH_MODULE_QUICK_INDEX.md` с быстрым поиском по документации, исходным модулям, ключевым темам, ограничениям и порядку реализации.

### Changed
- В `docs/README.md` добавлена ссылка на быстрый индекс.
- Исправлено некорректное отображение разделителя строк в навигационной таблице README.


## 2026-10-31 — первый этап logical→screen transform Brush Test

### Added
- Добавлен source/preparation/brush_coordinate_transform.py для явного преобразования логического плана 420×240 в screen-local ROI.
- Добавлены unit-тесты преобразования координат.

### Changed
- Brush Test формирует logical-планы; интеграционная передача преобразует их под текущий ROI и сохраняет transform metadata.
- Для тестовых штрихов отключено дополнительное продление конечных точек.
- Добавлены проверки генерации logical-плана и интеграционного handoff.

### Validation boundary
- CI runs созданы, окончательный результат ожидается.
- Live-проверка координат и границ в браузерной игре ещё не выполнена; полная CHALK-матрица остаётся заблокированной до этой проверки.


### Fixed — сохранение исходного logical-плана
- Общий stage8 save_plan нормализует coordinate_system в local_canvas_pixels; Brush Test теперь сохраняет исходный logical_board_pixels JSON напрямую, а Stage6 runtime-копия по-прежнему проходит нормализацию в local_canvas_pixels.

### Changed
- Transform metadata явно фиксирует единицы координат runtime executor и point_step_px как screen_pixels.


### Fixed
- Stage6 отклоняет прямую загрузку исходных logical_board_pixels планов Brush Test; их нужно передавать через интеграционный преобразователь.
- Добавлен regression test на запрет такой прямой загрузки.


## 2026-10-31 — CI logical→screen handoff

- GitHub Actions run #1132 для HEAD `3a0383b56b5972d4b978ff30080d7b7768b021d0` завершился успешно: geometry-tests, executor-tests и Windows portable build/startup smoke-test.
- Live-проверка геометрии доски, границ и A/B/C Monitor остаётся незавершённой.


## 2026-10-31 — исправление размера BoardPane в Brush Test

- Повторная сверка master game bundle подтвердила `BoardPane` 460×240; ранее использованное в transform значение 420×240 было ошибочным.
- Обновлены логический размер Brush Test, X-масштаб transform, unit-тесты, UI-подпись и документация.
- CI для новой геометрии и live-проверка ROI/границ ожидаются.

### Added
- Сценарий Brush Test `board_boundary_probe` для короткой проверки правой/левой/верхней/нижней границ BoardPane 460×240; добавлен unit test на endpoint.

### Changed
- Logical→screen transform проверяет соответствие ROI равномерному масштабу BoardPane (расхождение X/Y не более 1%); неверная геометрия ROI отклоняется до исполнения.
- Добавлены metadata равномерности масштаба и тест отклонения искажённого ROI.


## 2026-10-31 — Brush Test: не очищать доску после теста; Alt для остановки

- После успешного теста сохраняются скриншоты, измерения и `experiment.json`, но автоматическое нажатие Clear и post-clear этап отключены. Рисунок остаётся на доске до ручной очистки после проверки и экспорта Game Monitor.
- Начальная очистка перед независимым тестом остаётся частью подготовки.
- Глобальная клавиша аварийной остановки изменена с F12 на Alt (левая и правая Alt) в Brush Test, MouseExecutor, Stage6, Stage2 и калибровочном тесте.
- Обновлены unit tests. CI и live browser test ещё не запускались.


## 2026-10-31 — результаты live board_boundary_probe и исправление анализа

- Добавлены три live-прогона boundary probe: Game Monitor exact CHALK deltas 51, 52 и 52 при радиусе 1; 4/4 штриха в каждом прогоне; errors=0, droppedEvents=0.
- В каждом эксперименте baseline pointCount=1; после исполнения 52/53/53. Средний расход — 51.67 игровых точки.
- Конечные POINTER_UP client coordinates соответствуют преобразованным ROI endpoints, но не являются доказательством фактического принятия граничных координат BoardPane.
- Исправлен stroke visibility analyzer: теперь logical-plan strokes преобразуются в screen-local coordinates по сохранённому screen_transform; добавлены regression tests.
- Исправлена negative fixture uniform-scale test: non-uniform ROI 646×323 вместо ошибочного uniform ROI 646×338.
- Paint meter visual estimator остаётся inconclusive; CHALK измеряется по точному Monitor max/less.
- A/B/C Monitor и повторная визуальная проверка границ ещё не выполнены.


### Дополнение — визуальная проверка live boundary probe

- Вручную просмотрены все три пары `after_draw-board.png` / `after_draw-screen.png`: все четыре штриха доходят до границ доски, видимого выхода за пределы нет.
- Результат относится к проверенному ROI 578×301 на экране 1920×1080.
- Поля automated visibility в исходных manifest не переписывались: они сохраняют исторический inconclusive из-за выявленного и уже исправленного mismatch logical/screen dimensions.
- INT-003 остаётся открытой до A/B/C и успешного CI актуального HEAD.


## 2026-10-31 — live WebSocket smoke и A/B/C Monitor 0.2.1

- Добавлены результаты browser WebSocket handshake: `ready` и `pong`; Monitor 0.2.1 обнаружил BoardPane в игровом iframe, 0 dropped events и 0 errors.
- Добавлены три повтора A/B/C. Точные дельты pointCount: A 53/52/52, B 0*/52/52, C 50/52/52. B-1 невалиден: игра не добавила новых точек. В повторах 2 и 3 все три режима дали 52.
- В Monitor 0.2.1 diagnosticPointCount совпал с точным pointCount во всех трёх повторах; pointDelta подтверждает дельты 50/52/52.
- FPS probes показали 60 FPS во всех трёх сериях, но не разделены по режимам A/B/C; overhead Monitor не измерен.
- Новый boundary experiment: 4/4 видимых штриха, 7.36 с, 106 move calls, ΔpointCount=52. Paint-meter image estimate остаётся inconclusive.
- AcceptedPoint подтвердил y=0/240; горизонтальные конечные координаты около x=2.21/458.21, поэтому точные x=0/460 требуют отдельной проверки.
- Влияние размера кисти не установлено; полная матрица ожидает завершения A/B/C overhead и проверки горизонтальных границ.


## 2026-10-31 — первая реализация Game Monitor WebSocket telemetry bridge

- Добавлен `AutoDrawGameMonitor.subscribe(listener)` для низконагрузочной инкрементальной передачи событий.
- Добавлен browser agent для iframe: авторизация, allowlist событий, heartbeat и per-stroke FPS probe.
- Добавлен loopback WebSocket collector: автоматическая группировка DRAW_START/DRAW_END в run, exact pre/post CHALK delta, acceptedPoint и JSON persistence.
- Незавершённые runs при потере соединения сохраняются как partial.
- Добавлены Python/Node regression tests; browser live validation и привязка к UI experiment.json остаются открытыми.
- INT-004 переведена в IN_PROGRESS, не DONE.


### Дополнение — автоматическая связь bridge telemetry с Brush Test

- Brush Test UI автоматически находит bridge run по времени `before_draw` и фактическому радиусу кисти.
- Отчёт копируется в каталог эксперимента как `monitor_report.json`; `experiment.json` получает `session_id`, `run_id`, CHALK/FPS/trajectory summary и capture status.
- Если отчёт не найден за 10 секунд, сохраняется `monitor_capture.status=unavailable`.
- Корреляция по времени+радиусу является промежуточной; сквозной experiment_id и live validation ещё требуются.

## 2026-11-01 — G3 CHALK executor matrix

### Added
- G3 block на 27 уникальных задач для девяти сочетаний `point_step_px` и `point_delay_ms`, по три повтора.
- G3 metadata, parameter-aware duplicate protection, journal validation и analyzer aggregation.
- UI gate G3 после принятого G2 и runtime передачу параметров в MouseExecutor без перезаписи пользовательского профиля.
- Regression tests для G3 матрицы, журнала, анализатора и workflow override.

### Validation
- Полный CI и Windows portable startup smoke-test ещё ожидают подтверждения.
- Live G3 не запускался.


## 2026-11-01 — подтверждён CI на актуальном G3 HEAD

- Полный workflow run [41340237207](https://github.com/Kiddos19882/AutoDraw/actions/runs/41340237207) завершился success на HEAD `3dbf8f20bcea44c61290e49398e1a4daf182dbf9`.
- Успешны все три jobs: geometry-tests, executor-tests, Windows portable build/startup smoke-test.
- Run включает интеграционный regression test основного приложения из commit `8c93a498864973b9879c926627030bb7e1d3ce2a`; прежнее ожидание нового CI для этого теста закрыто.
- G3 software gate закрыт. Локальный Windows preflight и 27 live G3 captures не выполнены; экспериментальная модель расхода CHALK пока не подтверждена.
- Документация синхронизирована; исходный код и workflow не менялись.

## 2026-11-01

### Fixed
- Автоматические G3 block tasks больше не перехватываются legacy radius-matrix routing при совпадении `scenario_id`; geometry metadata создаётся для G3 task и может активировать task-specific executor override.
- Добавлен regression test для коллизии scenario ID между legacy и geometry matrices.

### Security
- Удалены runtime Game Monitor connection snippets; добавлено правило .gitignore для таких файлов.

## 2026-11-02 — CI и G3 regression optimization

### Changed
- Обязательный CI разделён на параллельные jobs Game Monitor, Preparation/G3, Integration и Executor; portable build запускается только после их успеха.
- Добавлены pip caching и отмена устаревших runs одной feature-ветки; убран дублирующий pull_request trigger.
- Длительные Stage 5/7/8 и synthetic benchmarks запускаются вручную через отдельный opt-in input; по умолчанию выключены.
- В CI portable build использует `AUTODRAW_SKIP_TESTS=1` только после прохождения независимых test jobs; локальная сборка сохраняет полный test run.

### Tests
- Добавлен тест реального G3 UI plan routing: обязательные block/matrix identity и executor parameters должны формироваться для активной block task.
- Integration regression проверяет передачу task-specific параметров 2/20 в Stage6.
- Новый workflow run на конечном HEAD ожидает подтверждения.

### Tests and CI
- UI regression tests изолируют persistent data paths во временном каталоге, чтобы CI не читал сохранённые paused CHALK journals и не открывал recovery dialogs.
- Brush Test tab отменяет deferred recovery scan при уничтожении owner frame; добавлен тест очистки Tk callback.
- Root integration tests разбиты на отдельные группы с локальными таймаутами; concurrency group обновлён для чистого повторного CI после зависших предыдущих runs.


## 2026-11-02 — завершена live G3 матрица CHALK

### Experimental results
- Принят новый независимый G3 block `chalk-20261102-031830-a0f325`: 27/27 captures, девять сочетаний шага/задержки, три повтора.
- Все 27 измерений имеют exact CHALK и совпадение sampled pointDelta; per-run dropped events, Monitor error deltas, Bridge send-failure deltas и collector sequence gaps равны нулю.
- Подтверждено, что положительный cumulative local Monitor buffer overflow не равен потере событий конкретного run: Bridge/collector captures сохранены и приняты.
- Для шести длинных горизонтальных линий step=4 / delay=5–10 ms расходует около 365 CHALK; step=1 / delay=5–10 ms — около 1350; delay=20 ms увеличивает расход примерно на 53–95% в зависимости от шага.
- Полные таблицы и границы применимости: [CHALK_G3_RESULTS_2026-11-02.md](CHALK_G3_RESULTS_2026-11-02.md).


## 2026-11-02 — предварительная модель расхода CHALK

- Добавлен `CHALK_PRELIMINARY_SEGMENTED_MODEL_2026-11-02.md` с отдельными сегментами для прямых штрихов, коротких штрихов, sampling profile и повторного покрытия.
- Для прямых штрихов G1 при radius=10, step=2, delay=10 зафиксирована предварительная оценка `C ≈ 1.765 + 0.2988 × L` (36 обучающих per-stroke наблюдений).
- Зафиксировано, что ROI visibility heuristic G3 не доказывает непрерывность линий; pixel-level quality gate остаётся открытым.
- Production estimator и executor defaults не изменялись.


## 2026-11-02 — визуальная проверка G3 step=4

- Получены и просмотрены все шесть PNG для step=4/delay=5 и step=4/delay=10.
- Подтверждена визуальная непрерывность шести длинных горизонтальных линий во всех повторах; видимой разницы между задержками нет.
- Визуальный gate закрыт для этой геометрии, но step=4 не назначен универсальным production default.
- Добавлен отчёт `CHALK_G3_VISUAL_QUALITY_AUDIT_2026-11-02.md`.


## 2026-11-02 — консолидация документации и план INT-006—INT-009

### Changed
- PROJECT_STATUS теперь начинается с единого актуального снимка; прежняя полная версия сохранена в PROJECT_STATUS_HISTORY_2026-11-02.md.
- TASKS синхронизирован с фактическим состоянием G1/G2/G3 и автоматизированной лаборатории.
- Preliminary CHALK model и G3 Results согласованы с завершённым ручным просмотром шести PNG.
- ROADMAP и docs index указывают на действующий план дальнейших работ.

### Added
- CHALK_NEXT_STEPS_PLAN_2026-11-02.md: геометрическая проверка step=4, независимая validation estimator, метрики ошибки, safety margin и последовательность INT-007—INT-009.


## 2026-11-02 — INT-006 зафиксирован и начат

- Добавлен исполнительный протокол INT-006 с матрицей V1–V5, тремя sampling-профилями, 45 запланированными captures, критериями качества и независимой validation модели CHALK.
- Зафиксировано ограничение текущей лаборатории: V1–V5 отсутствуют в контракте G1/G2/G3 и требуют расширения harness до live-испытаний.


## 2026-11-02
- INT-006: экспериментальный harness расширен сценариями V1–V5 на инфраструктуре G3; добавлены три sampling profiles, отдельные 9-task journals и regression tests.
- Task-specific executor override распространён на V1–V5; production executor defaults и estimator не менялись.
- CI и live validation ожидаются; экспериментальные результаты V1–V5 пока отсутствуют.


## 2026-11-02 — INT-006 V1–V5 live results

### Added
- `CHALK_INT006_V1_V5_RESULTS_2026-11-02.md`: сводка 45 live captures, exact/per-stroke CHALK, профильных сравнений, первичной holdout-проверки модели и визуальных ограничений.

### Verified
- V1–V5: 5 block journals × 9 tasks = 45/45 completed; Monitor/Bridge per-run integrity gates пройдены.
- CI run #1887 на commit `6479536` завершился success.
- Step=4 снизил расход CHALK примерно на 48–49% для V1/V3/V4/V5 и на 23–25% для коротких штрихов V2.
- G1-модель на 66 новых штрихах P0: MAE 1.09, RMSE 1.33, MAPE 1.71%; step=4 fits остаются исследовательскими.
- Production defaults и estimator не изменялись; INT-006 остаётся IN_PROGRESS до pixel-level audit и независимой validation.


## 2026-11-02 — INT-006 preliminary PNG screening

- Added `CHALK_INT006_PNG_SCREENING_2026-11-02.md` with representative visual screening of 15 original PNGs across V1–V5 and P0/P1/P2.
- Recorded geometry limitations: unintended intersections in V1/V3, dot-like V2 marks at radius 10, cursor occlusion in V4, and merged close parallel lines in V5.
- No obvious step=4 continuity regression was seen in the reviewed samples; quantitative pixel-level metrics remain pending.
- No production code, executor defaults, estimator, or raw captures changed.


### INT-006 — корректировка геометрии тестов
- По результатам ручного review PNG-overlay исправлены пересекающиеся тестовые траектории V1/V3; добавлен regression gate минимального межштрихового расстояния. Первичные captures не переписывались, повторные live-блоки и CI для нового code HEAD остаются следующими проверками.


### INT-006 — cursor-free post-draw capture
- Post-draw screenshot теперь выполняется после mouseUp и перемещения курсора за пределы calibrated board ROI; выбранная точка и метод фиксируются в experiment manifest.
- Добавлены regression tests выбора безопасной точки и порядка mouseUp → move → screenshot. CI и live validation нового поведения ожидаются.
- Production executor, estimator, sampling defaults и первичные captures не менялись.

- Дополнительно проверено, что cursor relocation применяется только в automated post-draw capture; ручная процедура захвата сохранена без перемещения курсора и защищена regression test.


## 2026-11-02 — отдельные V2/V5 follow-up серии INT-006

- Обновлены Brush Test presets: V2 12/16/20/24/30 logical px (5 strokes) и V5 spacing sweep 8/12/16/20/24 logical px плюс X/T/крестовые узлы (16 strokes).
- Новые scenario IDs отделяют follow-up captures от исходных V2/V5; исходные данные не перезаписываются и не смешиваются.
- Обновлены matrix expected counts, block tests и UI geometry regression tests.
- Добавлен `CHALK_INT006_V2_V5_FOLLOWUP_2026-11-02.md` с инструкцией для пользовательских live-прогонов.
- Каждая серия содержит 9 captures: P0/P1/P2 × три повтора, radius=10. Live-прогоны не запускались.


## 2026-11-02 — INT-006 CI regression fixes

### Fixed
- Restored expected stroke counts for legacy V2/V5 scenario IDs (6 and 10) so existing manifests remain analyzable without reintroducing legacy IDs into current block planners.
- Updated the V5 application integration fixture to use `int006_intersections_spacing_sweep` and its 16-stroke contract.

### Validation
- Previous CI run `41468581157` had two legacy-count failures and one stale V5 fixture failure. Corrective commits: `0cac37c`, `706be60`.
- Full CI rerun is pending; no live experiments were started.


## 2026-11-02 — INT-006 corrective CI и синхронизация статусов

- Полный CI run [41470680544](https://github.com/Kiddos19882/AutoDraw/actions/runs/41470680544) на code HEAD `3e8e6c5` завершился success: Application integration, Executor regression, Game Monitor/bridge, Preparation/G3, Windows portable build/startup smoke-test и INT-006 PNG audit.
- Исправления legacy V2/V5 counts и V5 integration fixture подтверждены обязательными jobs. Optional algorithm benchmarks пропущены.
- Уточнено разделение исходных V2/V5 сценариев и follow-up контрактов; исходные manifests остаются обратно совместимыми.
- Обновлены PROJECT_STATUS, TASKS, CHALK_NEXT_STEPS_PLAN и CHALK_INT006_EXECUTION_PROTOCOL. Live follow-up и независимая validation модели остаются незавершёнными.


## 2026-11-02 — INT-006 V1/V3/V4 follow-up protocol

- Добавлен отдельный протокол новых live-серий для исправленной геометрии V1/V3 и cursor-free closure capture V4.
- Для каждой фазы определены новый series_id, отдельный block journal и 9 captures; все три фазы вместе — 27 captures.
- Ссылки добавлены в docs index, PROJECT_STATUS, TASKS, ROADMAP и действующий план INT-006. Код и исходные captures не менялись.


## 2026-11-02 — legacy CHALK block journal compatibility

### Fixed
- Fixed validation of historical INT-006 V2/V5 block journals. The validator now accepts the corresponding legacy scenario IDs and validates each task against its own legacy expected stroke count.
- Preserved strict matrix integrity: all nine unique sampling/repeat cells and unique order indexes remain required; mixing legacy and current scenario IDs inside one block is rejected.
- Added regression coverage for completed legacy V2 (6 strokes) and V5 (10 strokes) journals.

### Verified input
- The reported V2 journal contains 9 unique completed tasks and no duplicate matrix cell. Its legacy ID was the sole compatibility mismatch.
- Commits: `f0e05df`, `4847cce`. CI validation pending.
- No experiment records were modified; no production drawing or CHALK calculation behavior changed.


### Исправление after-draw cursor placement — 2026-11-02

- Автоматический курсор теперь уходит ниже доски и полоски краски, а не просто за границу доски.
- Учитываются обе откалиброванные области (`board_area`, `paint_meter_area`) и 32 px свободного отступа; это предотвращает hover-уведомление от полоски краски поверх доски на `after_draw-board.png`.
- Ручное снятие снимков и траектории рисования не затронуты.


### INT-006 live follow-up V1–V5 — 2026-11-02

- Добавлены и проанализированы 45/45 live captures по V1–V5 (commit [e879a77](https://github.com/Kiddos19882/AutoDraw/commit/e879a77f63be7a7a68de3f09091eab7dba0d34a2)); все пять block journals завершены 9/9.
- Подтверждены exact CHALK и согласованность per-stroke Monitor deltas для всех 45 runs; per-run Monitor/Bridge errors и drops отсутствуют.
- Step=4 показал 38.5–49.4% экономии против step=2; различие delay=5/10 ms при step=4 мало. Радиус во всех сериях фиксирован на 10.
- Добавлен отдельный отчёт repeat values и ограничений `CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md`. Следующий gate — pixel-level audit новых PNG и независимая validation; production defaults не изменены.


### INT-006 follow-up pixel audit and CI — 2026-11-02

- Исправлен PNG analyzer: независимые серии INT-006 идентифицируются по series_id; duplicate matrix cells проверяются только внутри серии. Добавлены regression tests и обновлён CI expected runs per series.
- Pixel-level audit завершён для 90 captures (45 исходных + 45 follow-up): 90 valid, 0 duplicate/missing/unexpected cells, 0 batch failures; 549 stroke rows и 900 pair rows.
- Для новых 45 captures: 297/297 strokes с coverage=1.0 и zero gaps; V4 closure seam 27/27 covered; курсор не обнаружен на board image в 45/45 captures.
- V5 spacing sweep: целевые пары 8/12 logical px touch/merge; 16/20/24 logical px остаются разделёнными при radius=10.
- Full CI run [41496555297](https://github.com/Kiddos19882/AutoDraw/actions/runs/41496555297) — success, включая Windows portable build/startup smoke-test и PNG audit. Production executor defaults и CHALK estimator не менялись.


### INT-006 legacy journal compatibility and independent validation plan — 2026-11-02

- Добавлена совместимость validator с историческими scenario IDs V2/V5 и их собственными expected stroke counts; добавлены regression tests (commits `f0e05df`, `4847cce`).
- Подтверждено, что полный CI run [41496555297](https://github.com/Kiddos19882/AutoDraw/actions/runs/41496555297) checkout рабочей ветки после commit `956ce2b`, содержащего оба исправления в истории. Preparation/G3 завершился 662 passed и 82 subtests passed; все обязательные jobs успешны.
- Создан `CHALK_INT006_INDEPENDENT_VALIDATION_PLAN_2026-11-02.md`: пять новых DrawingPlan, frozen predictions P0/P1/P2, 3 повтора, exact pre/post pointCount и метрики ошибок.
- Обновлены PROJECT_STATUS, TASKS, ROADMAP, WORK_LOG, CHALK_NEXT_STEPS_PLAN и docs index. Production estimator, executor defaults и первичные experiment data не менялись. Legacy-journal CI gate закрыт.


## 2026-11-02 — INT-006 independent validation harness readiness

- Добавлен `CHALK_INT006_HARNESS_READINESS_AUDIT_2026-11-02.md`.
- Независимый validation protocol переведён в BLOCKED: D1–D5 пока не подключены к matrix/block/UI/executor harness, а analyzer не сравнивает captures с immutable frozen predictions.
- PROJECT_STATUS, TASKS, ROADMAP, WORK_LOG и docs index синхронизированы с фактическим состоянием исходников.
- Production estimator/defaults, исходные экспериментальные данные и master не изменялись; code/tests/CI/live captures в рамках readiness audit не запускались.


### INT-006 frozen prediction harness — 2026-11-02

- Добавлены 15 frozen prediction records (D1–D5 × P0/P1/P2), hash-sealed artifact в durable block journal и prediction ID в 45 task/manifest cells.
- Реализован независимый analyzer: exact CHALK, geometry/profile/task/journal binding, completed attempt integrity, run/per-stroke residuals и error metrics.
- Executor handoff сверяет prediction ID; Brush Test UI запрещает ручной запуск D1–D5 вне INT006 block.
- Full CI [41513389663](https://github.com/Kiddos19882/AutoDraw/actions/runs/41513389663) — success: Preparation/G3 667 passed + 82 subtests; integration, executor, Game Monitor/bridge, pixel audit и Windows portable build/startup smoke-test success.
- Созданы инструкции frozen analyzer и local Windows preflight. Production estimator/defaults и live experiment data не менялись.


## 2026-11-03 — INT-006 D1–D5 live captures и предварительный CHALK audit

- Принят live block `chalk-20261102-232320-7cea27`: 45/45 задач completed, radius=10.
- Для 45 experiment manifests найдены 45 Monitor reports; предварительно проверены exact CHALK, per-stroke delta sum, stroke counts и нулевые Monitor/Bridge integrity counters.
- Добавлен отчёт [CHALK_INT006_VALIDATION_PRELIMINARY_RESULTS_2026-11-03.md](CHALK_INT006_VALIDATION_PRELIMINARY_RESULTS_2026-11-03.md): 45 plan runs, MAE 1.408, RMSE 1.967, bias -0.875, MAPE 2.134%, maximum underprediction 1.82 CHALK; per-stroke 243 rows, MAE 0.439.
- Исправлена portability-привязка journal attempt к experiment directory name вместо локального абсолютного Windows path; добавлен regression test.
- В `.github/workflows/geometry-tests.yml` добавлен официальный запуск analyzer и artifact upload. Новый CI result и официальный analyzer JSON ещё ожидаются.
- Safety margin не установлен; production estimator, executor/sampling defaults и master не менялись.


## 2026-11-03 — повторный полный аудит INT-006 captures

- Повторно прочитаны все 45 experiment manifests и все 45 Monitor reports.
- Для каждой записи подтверждены exact CHALK, per-stroke pointDelta sum, stroke count, experiment linkage, observed radius=10 и нулевые Monitor/Bridge integrity counters.
- SHA-256 frozen prediction artifact независимо пересчитан и совпал с journal: `a0eab016e96a81e14bededd32cf5161dd943d6fc85a20b7eec17455f69d0c61c`.
- Официальный analyzer JSON и результат CI после его подключения пока не получены; quantitative validation и safety margin остаются pending.


## 2026-11-03 — INT-006 analyzer binding hardening

- Added direct journal-task `prediction_id` verification against the frozen scenario/profile prediction.
- Added `expected_strokes` verification against the frozen planned-stroke count.
- Added a fail-closed regression test for a tampered journal prediction ID.
- No prediction coefficients, sampling defaults, executor defaults, or production estimator changes.
- CI confirmation and the official 45-capture analyzer JSON remain pending.

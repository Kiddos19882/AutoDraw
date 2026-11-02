# История изменений документации и проекта

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
- Все 27 измерений имеют exact CHALK и совпадение sampled pointDelta; per-run dropped events, Monitor errors, Bridge send failures и collector sequence gaps равны нулю.
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

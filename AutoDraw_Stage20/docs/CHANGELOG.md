## 2026-11-04 — уточнение активного объёма CHALK

## 2026-11-04 — уточнение deployed renderer evidence

- Из сохранённых Monitor captures извлечены URL исторических runtime assets: manifest, `mergeEngine_df2e5bc5.js` и `main.min_6ecc02a4.js`.
- Установлено, что эти assets не совпадают по имени с bundle `main.min_570122a1.js` из master; содержимое и hash исторических загрузок отсутствуют. Deployed Egret version не установлена.
- Следующий gate уточнён: получить response bodies и SHA-256, затем сравнить фактический renderer. Код и live experiments не менялись.

## 2026-11-04 — прямой анализ игровой кисти

- Прослежен фактический путь BoardPane/Painter в клиентском bundle из master: толщина кисти передаётся в Egret Graphics; normal path строится через moveTo/lineTo, smooth path — через midpoint/curveTo.
- Зафиксировано визуальное наблюдение пользователя: кисть в игре выглядит круглой. Оно согласуется с ROUND caps/joins Egret reference API; deployed runtime и точная rasterization остаются не подтверждены.
- Документированы ограничения single-point path и следующий offline renderer/PNG gate. Код, тесты, конфигурации, workflow и master не менялись.

- INT-003 и CHALK-SAMPLING-DOMAIN закрыты как CLOSED_NOT_REQUIRED по решению пользователя; исторические данные сохранены.
- В TASKS добавлено обоснование четырёх оставшихся направлений и их зависимостей. FILL-001-RS renderer footprint остаётся P0 blocker; 45-cell matrix условна и заблокирована до принятого preflight; Capsule остаётся отдельной offline geometry validation; INT-006 остаётся незавершённой из-за ограниченного domain и неустановленного safety margin.
- Код, тесты, конфигурации, workflow и live evidence не менялись.

## Дополнение — краевые промежутки и будущая контурная обводка (2026-11-04)

При просмотре исходного `after.png` отмечен округлый профиль боковых краёв заливки. Пользовательская гипотеза: между круглыми окончаниями соседних scanline-проходов остаются незаполненные промежутки. В предпоследнем тесте, по наблюдению пользователя, следующая линия начиналась ниже и такого эффекта не было. Это направление offline-проверки, а не установленная причина.

Проверить на неизменённых исходных данных:
1. Разложить uncovered target pixels по боковым краям, верхней/нижней границам, углам и внутренней области.
2. Сопоставить пропуски с координатами начала/конца линий, вертикальным шагом и фактической rasterized footprint/cap кисти.
3. Отдельно локализовать 11 leakage pixels.
4. Сопоставить с предпоследним тестом по первичным PNG/plan evidence, если они доступны.
5. Не менять frozen masks, thresholds, исходный plan или production defaults.

**Будущий кандидат:** после основной заливки выполнить одну непрерывную обводку контура, правильно сместив центральную линию внутрь области с учётом фактического renderer footprint, чтобы край кисти закрывал границу без выхода наружу. Это не реализовано и не подтверждено. До рассмотрения нужны offline geometry/raster validation, затем отдельное разрешение на live проверку; критерии — coverage≥99%, leakage=0 и exact CHALK по `pointCount_after - pointCount_before`. Длина контура и proxy points не заменяют измерение расхода.

## 2026-11-04 — FILL-001-RS corrected replay of original PNG evidence

- Выполнен replay исходных before/after PNG и связанных evidence через `Fill001Tab.finalize_capture()` в CI [41780241017](https://github.com/Kiddos19882/AutoDraw/actions/runs/41780241017), checkout HEAD `0f23731`.
- Runtime binding PASS: 27/27 strokes, radius=10, exact CHALK=1260, Bridge diagnostics без потерь/ошибок.
- Corrected PNG audit: coverage=98.430600%, leakage=11 — capture REJECTED при неизменных требованиях ≥99% / 0. Предыдущие 97.673218% / 28 относятся к audit до affine correction.
- SHA-256 исходных PNG и входных JSON сохранены в [replay report](CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md). Raw runtime plan hash mismatch разрешён: CRLF-представление committed текста точно совпадает с hash в executor report; содержательного mismatch нет. Остаточная причина PNG mismatch требует offline pixel breakdown; live и 45-task matrix остаются BLOCKED.

## 2026-11-04 — FILL-001-RS PNG audit transform correction

- Исправлено несовпадение affine mapping frozen mask и executor screen coordinates: audit использует те же (W−1)/460 и (H−1)/240 scales.
- Добавлены regression assertions для client ROI 581×304 и inverse nearest-neighbor mapping.
- Commits: [4797aa5](https://github.com/Kiddos19882/AutoDraw/commit/4797aa5e2e3d9f78656c91dcddf285304eae55c1), [a950084](https://github.com/Kiddos19882/AutoDraw/commit/a950084db14fd1560aa15f099da4a0108c9631e7).
- На момент этой записи CI/replay после affine correction ещё не были подтверждены; последующий corrected replay и результат 98.430600% / 11 зафиксированы выше в changelog и в отдельном replay report. Capture остаётся REJECTED; 45-task matrix BLOCKED.
## 2026-11-04 — FILL-001-RS runtime discovery replay и live PNG rejection

- Изучен evidence commit [5308214](https://github.com/Kiddos19882/AutoDraw/commit/530821497ce3a6bd5152318a78e1f06cb836f288): основной Bridge run `6a17a297-ea14-4527-9527-bfd8de3bd335`, 27/27 strokes, radius=10, exact pointCount 1→1261, CHALK=1260; dropped events, Monitor errors, Bridge send failures и sequence gaps — 0.
- Установлена причина прежнего сообщения Runtime binding pending: legacy session `3323cf8e-01ca-4009-8f16-27d657d857f8` без schema v2/diagnostics классифицировалась как pending и блокировала актуальную session.
- В [a7e37d6](https://github.com/Kiddos19882/AutoDraw/commit/a7e37d6eb0031094ffd962bc11ef01860a3af74a) discovery пропускает несовместимые legacy schemas до pending-классификации. Неполные schema-v2 sessions остаются pending.
- В [974f949](https://github.com/Kiddos19882/AutoDraw/commit/974f949e9639acc90e7f4d6f4588c3fb96f9abb2) добавлен replay тест, который вызывает реальный `Fill001Tab.finalize_capture()` с сохранёнными manifest/attempt/executor report/Bridge session и runs/before-after PNG, включая старую legacy session.
- Результат replay: runtime binding PASS, точный run ID и CHALK=1260 подтверждены. PNG audit REJECTED: coverage=97.673218% при требовании ≥99%, leakage=28 при требовании 0. Capture JSON не создаётся, attempt и matrix остаются pending.
- Полный CI [41772866679](https://github.com/Kiddos19882/AutoDraw/actions/runs/41772866679) — SUCCESS: Preparation/G3 804 passed, 24 warnings, 82 subtests; Executor, Game Monitor/Bridge, Application integration, INT-006 pixel audit и Windows portable build/startup smoke-test SUCCESS; optional benchmarks SKIPPED.
- Следующий шаг — анализировать реальный PNG/ROI/transform и устранить недопокрытие/выход за границы. Live matrix не запускать до прохождения PNG gate.

## Исправление FILL-001-RS frozen geometry rebuild — 2026-11-04

Пользовательский runtime evidence commit [63158fb](https://github.com/Kiddos19882/AutoDraw/commit/63158fb55743c566bf231196b80016273970bbf1) зафиксировал отказ single-task preflight до запуска исполнителя. Для задачи rectangle/r10 manifest и исходный DrawingPlan согласованы: planner_version=2, scanline_row_step=5, scanline_offset=0, plan signature совпадает с task, expected_strokes=27. Game Monitor подтвердил radius 30→10; pointCount остался 1 (CHALK=0), Bridge session завершилась без dropped events/errors/send failures.

Причина установлена в runtime guard integrated_app.py: повторное построение выполнялось вызовом build_fixed_radius_fill_plan(shape_id, radius) без spacing-параметров. Значения по умолчанию — step=1/offset=0, то есть legacy planner v1. Поэтому сравнивался FILL-001-RS v2 signature с другой геометрией v1 и срабатывал корректный fail-closed guard. Это ошибка handoff/validation, не ошибка регулировки кисти и не расход CHALK.

Исправление: единый helper повторного построения получает scanline_row_step/scanline_offset из frozen task; для legacy tasks без этих полей сохраняются прежние defaults. Объявленный planner_version проверяется против фактически восстановленного. Добавлены регрессионные проверки RS signature/27 strokes, legacy signature/131 strokes и отказа при несовпадении версии. До успешного CI и повторного локального preflight live matrix остаётся BLOCKED; повторный запуск здесь не выполнялся.

## 2026-11-04 — FILL-001-RS — versioned scanline spacing

- Добавлен planner v2 с независимыми scanline_row_step/scanline_offset; legacy planner v1 и default plan identity сохранены.
- Добавлен отдельный FILL001_RS_V1 manifest builder (45 задач), fail-closed validation и single-task execution handoff.
- Runtime experiment context и capture metadata связывают plan variant/version и spacing; P1 point sampling не менялся.
- Добавлены CLI manifest generator, exhaustive 2 238-candidate static sweep script, regression tests и CI artifact upload.
- Static sweep: 62 candidates passed coverage≥99%/leakage=0; результаты OpenCV не являются измерением CHALK.
- Live preflight не выполнялся; FILL-001-RS matrix остаётся BLOCKED до принятого single-task live capture.

## 2026-11-04 — FILL-001-RS — документирован этап исследования scanline spacing

- В существующий временный FILL-001 plan добавлен отдельный этап исследования `scanline_row_step`, не смешиваемый с `point_step_px`.
- Зафиксированы предварительные OpenCV-кандидаты для 15 shape×radius combinations и подробные r10/step=5 metrics для трёх frozen masks.
- Обозначено, что step=5 — кандидат, а не принятая настройка; estimated sampling points/path length не являются измерением CHALK.
- Определены обязательные versioned plan/signature и отдельный live preflight gate; FILL-001 45-cell matrix и INT-007 остаются BLOCKED.
- Изменения только в Markdown-документации. Код, тесты, конфигурации, workflow, экспериментальные данные и `master` не изменялись.

## 2026-11-04 — FILL-001: полный runtime evidence и quota exhaustion

- Добавлен пользовательский evidence commit [73d14a1](https://github.com/Kiddos19882/AutoDraw/commit/73d14a1784a5a9f8ef29bc0e197b75352f2650af): attempt, manifest, DrawingPlan, executor report, Bridge session, два run JSON и before/after PNG.
- Второй Bridge run полностью разобран: exact CHALK=5999 подтверждён snapshots и per-stroke/sample deltas; radius=10; 0 drops/errors/send failures/sequence gaps.
- Run не принят: 128 consuming strokes из 131 кандидата; три последних штриха не потребили CHALK после достижения квоты 6000. Capture остаётся pending/rejected, 45-cell matrix BLOCKED.
- Документация обновлена; production code/tests/workflows не изменялись. Количественный PNG audit не выполнялся.

## 2026-11-04 — FILL-001 transient Bridge session retry: CI SUCCESS

- Исправлена race/fail-fast обработка неполной Bridge session: после фильтрации по executor window отсутствие bridge_diagnostics/last_message_at_utc у потенциально подходящей session означает pending, а не окончательную ошибку.
- Кнопка FILL-001 capture finalization повторно выполняет runtime binding и принимает capture только после строгого binding и PNG audit. Stage 6 и UI используют общий summary builder; worker не перезаписывает passed status.
- Добавлены regression tests на incomplete session → обновлённая session → successful binding, исключение future session и UI retry.
- Commit [5cde7a1](https://github.com/Kiddos19882/AutoDraw/commit/5cde7a109a669bebf790ecbeb21f8bbc4feae182). Полный CI [41754801210](https://github.com/Kiddos19882/AutoDraw/actions/runs/41754801210) — SUCCESS: Preparation/G3 787 passed, 24 warnings, 82 subtests; все обязательные jobs, Windows portable build/startup smoke-test и INT-006 pixel audit успешны; optional benchmarks skipped.
- Portable artifact ID 13288855067, 637,575,055 bytes.
- Live capture не принят; 45-cell matrix остаётся BLOCKED до нового успешного Windows live preflight.

## 2026-11-04 — FILL-001 binder activity-window fix: CI SUCCESS

- Binder fix `95a8d17` и regression tests `870bebc` подтверждены полным GitHub Actions [41737923777](https://github.com/Kiddos19882/AutoDraw/actions/runs/41737923777): все обязательные jobs, включая Windows portable build/startup smoke-test, завершились SUCCESS; optional benchmarks skipped.
- Portable artifact [autodraw-g3-preflight-build](https://github.com/Kiddos19882/AutoDraw/actions/runs/41737923777/artifacts/13280731107) опубликован.
- Предыдущий live preflight остаётся REJECTED/UNACCEPTED (131/131 strokes, session CHALK=5999); доска исчерпана, 45-cell matrix заблокирована до нового принятого preflight на восстановленной доске.
- Обновлены PROJECT_STATUS, TASKS, ROADMAP, временный план FILL-001 и WORK_LOG. Исходники, тесты, workflow и первичные runtime evidence в рамках этой синхронизации не менялись.

## 2026-11-04 — FILL-001 preflight postmortem и software gate

- Полный CI [41730717881](https://github.com/Kiddos19882/AutoDraw/actions/runs/41730717881) прошёл на code HEAD `fe6d446`: Executor, Game Monitor/Bridge, Application integration, Preparation/G3 (782 passed, 24 warnings, 82 subtests), INT-006 pixel audit и Windows portable build/startup smoke-test — SUCCESS; optional benchmarks skipped.
- Добавлен postmortem `CHALK_FILL001_PREFLIGHT_POSTMORTEM_2026-11-04.md`: executor завершил 131/131 strokes; session exact CHALK=5999; attempt JSON invalid; after PNG физически существует, capture не принят; большой Bridge run file не проверен целиком.
- Выявлен дополнительный runtime binder blocker: idle finalization timestamp ошибочно считается временем активности Bridge run, что создаёт false overlap с executor window. Следующее исправление и regression test зарегистрированы в TASKS/ROADMAP.
- Обновлены PROJECT_STATUS, TASKS, ROADMAP, временный FILL-001 plan и docs index. Исходники, тесты, workflow и первичные runtime evidence в рамках отчётной задачи не менялись.

## 2026-11-04 — FILL-001 persistence and hash validation fixes

- Исправлены четыре записи JSON в chalk_fill_ui.py: теперь используются реальные переводы строк, а не буквальная последовательность \\n. Добавлены regression tests для completion/after PNG, capture JSON и attempt finalization.
- Canonical plan hash теперь вычисляется по нормализованному DrawingPlan через общий model round-trip; attach сохраняет тот же normalized document, что Stage 6 повторно загружает. Добавлен regression test для numeric metadata и точности координат.
- Commits: [2b7577c](https://github.com/Kiddos19882/AutoDraw/commit/2b7577c3a3289871b7fff300fd6013f12c7cb54e), [3b67aea](https://github.com/Kiddos19882/AutoDraw/commit/3b67aea0145170ec23df089916bedf7828de9a68).
- CI [41728163369](https://github.com/Kiddos19882/AutoDraw/actions/runs/41728163369): Game Monitor/Bridge и Executor SUCCESS; Preparation/G3 и Application integration выполняются; Windows build ожидает их завершения. Live capture не принят; 45-cell matrix остаётся BLOCKED.

## 2026-11-03 — DOC-018: введена постоянная система управления знаниями ИИ

- Добавлены пять универсальных регламентов: рабочий процесс ИИ, архитектура знаний, доказательность и validation, инженерные инварианты, стандарт экспериментов.
- README приложения и основной docs index направляют ИИ к регламенту до начала работы.
- Управляющие документы отражают DOC-018 и DEC-016. Технические справочники, планы и исторические отчёты сохранены; конкурирующие копии статуса не создавались.
- Изменения ограничены Markdown-документацией; код, тесты, настройки, workflow и экспериментальные данные не затронуты.

## 2026-11-03 — FILL-001 runtime JSON handoff fix
- По данным пользовательского запуска в commit [6b1cba9](https://github.com/Kiddos19882/AutoDraw/commit/6b1cba9b1c40a030ac6bd7b29365bf19ac3c9149) обнаружено, что `integrated_app.py::_transfer_brush_test_plan()` добавлял к runtime DrawingPlan буквальную последовательность `\n` после JSON object. Stage 6 отклонял невалидный JSON, поэтому FILL-001 callback возвращал отказ.
- Исправлена сериализация runtime JSON и форматирование сообщения исключения: commit [8dfd1b5](https://github.com/Kiddos19882/AutoDraw/commit/8dfd1b541f54a1b416dfb2907739cf4b1a99c58d).
- Добавлен интеграционный regression test FILL-001 plan → Stage 6 load с проверкой `autodraw_experiment`: commit [1b2d8a1](https://github.com/Kiddos19882/AutoDraw/commit/1b2d8a128c99ab8ad1abb1e9f480702676cd9f56).
- GitHub Actions [41692129486](https://github.com/Kiddos19882/AutoDraw/actions/runs/41692129486): Application integration, Game Monitor/Bridge, Preparation/G3, Executor и INT-006 pixel audit — SUCCESS; Windows portable build/startup smoke-test ещё выполняется. Повторный Windows live preflight не выполнялся; 45-cell captures остаются заблокированы.

## 2026-11-03 — FILL-001 client ROI correction CI

- GitHub Actions [41686091985](https://github.com/Kiddos19882/AutoDraw/actions/runs/41686091985) завершился SUCCESS на code/test HEAD `031913c`: Preparation/G3 778 passed, 24 warnings, 82 subtests; Game Monitor/Bridge, Executor, Application integration, INT-006 pixel audit и Windows portable build/startup smoke-test успешны; optional benchmarks skipped.
- Portable artifact `autodraw-g3-preflight-build` загружен (artifact ID `13254104951`, 636,529,516 bytes, retention 7 days). Live Windows/game preflight не выполнялся и остаётся следующим gate.

## 2026-11-03 — FILL-001 client-resolution ROI correction

- Исправлено ошибочное требование screen ROI ровно 460×240. 460×240 остаётся logical board size движка и frozen masks; клиентский ROI берётся из калибровки и сохраняется в фактическом размере.
- UI проверяет границы crop, сохраняет ROI в attempt record, сверяет before/after ROI и DrawingPlan transform, требует парный before/after capture и блокирует finalize без calibrated ROI. PNG adapter масштабирует frozen logical mask методом nearest-neighbor, сохраняет transform и raster scale, проверяет uniform scale ≤1% и выполняет coverage/leakage audit на screen-resolution crop.
- Добавлены synthetic regression tests для ROI 581×304, runtime transform, non-uniform/mismatch rejection, scaled leakage и фактического UI crop. CI для нового HEAD ожидается; live Windows preflight не выполнялся.

## 2026-11-03 — синхронизация управляющей документации

- Устранён конфликт идентификаторов решений: второе решение DEC-013 перенумеровано в DEC-015.
- TASKS.md синхронизирован с общим набором статусов, включая DEFERRED.
- Карта UI и основной индекс исправлены: фактическая конфигурация содержит девять вкладок, FILL-001 — № 8, калибровка — № 9.
- ROADMAP.md очищен от дублирующих устаревших CI TODO; текущий незакрытый gate — Windows live preflight.
- PROJECT_STATUS.md начинается с актуального снимка; историческая запись сохранена ниже.

## 2026-11-03 — FILL-001 UI/runner integration и CI regression gate

- Подтверждена отдельная вкладка FILL-001: создание/загрузка 45-cell manifest, выбор одной pending task, frozen plan/mask validation, operator approval, brush-size handoff и запуск Stage 6 с P1 override.
- Реализована связь DrawingPlan experiment context → executor report → Bridge session/run runtime binding; direct Stage 6 bypass для FILL-001 блокируется fail-closed guard.
- Unified application tests подтверждают регистрацию отдельной вкладки `8. FILL-001`; вкладка калибровки отображается как `9. Калибровка теста`. По DEC-014 FILL-001 остаётся отдельной.
- Полный CI [41673570178](https://github.com/Kiddos19882/AutoDraw/actions/runs/41673570178) SUCCESS на code/test HEAD `e3774a3`: Preparation/G3 772 passed, 24 warnings, 82 subtests; все обязательные jobs и Windows portable build/startup smoke-test успешны; optional benchmarks skipped.
- Остаётся Windows live runtime/PNG preflight; 45 live captures заблокированы до успешного preflight. Production estimator, executor defaults, sampling defaults и `master` не менялись.

## 2026-11-03 — FILL-001 runtime binding integration

- Runtime binder `chalk_fill_runtime_binding.py` добавлен и подключён к завершению FILL-001 исполнения в Stage 6.
- Реализована fail-closed проверка Bridge session/run, executor report, timestamps, lifecycle, observed radius, exact CHALK, sequence/send-failure diagnostics и P1 config.
- Runtime capture adapter получает данные из persisted runtime artifacts и сохраняет их SHA-256.
- Полный GitHub Actions [41591543009](https://github.com/Kiddos19882/AutoDraw/actions/runs/41591543009) на code HEAD `d7466c5` завершился SUCCESS по всем обязательным jobs; optional algorithm benchmarks skipped.
- Шаг 2 временного плана FILL-001 закрыт как программная интеграция и regression gate. Реальный Windows runtime/PNG preflight остаётся TODO; 45 live captures остаются заблокированы.

## 2026-11-03 — FILL-001 software regression gate PASS

- Подтверждён полный GitHub Actions run [41579136690](https://github.com/Kiddos19882/AutoDraw/actions/runs/41579136690) на code HEAD `b4cc45a80231e6bad2f878b2a5a2f16b48b9d68b`.
- Preparation/G3: 754 passed, 24 warnings, 82 subtests passed; Game Monitor/Bridge, Application integration, Executor regression, INT-006 audit и Windows portable build/startup smoke-test — SUCCESS.
- Windows smoke-test подтвердил запуск portable `AutoDraw.exe` с активным процессом в течение 10 секунд; artifact ID 13204044319.
- Исправление сигнатуры `audit_fill001_png_pair()` подтверждено; production estimator, executor defaults и live captures не менялись.
- Шаг 1 временного плана FILL-001 переведён в DONE. Runtime binding и Windows PNG preflight остаются открытыми.

## 2026-11-03 — временный план FILL-001

- Добавлен обязательный к сохранению временный план из пяти шагов: software gate, runtime binding, Windows PNG preflight, 45 live captures и анализ расхода/качества.
- Уточнено, что live captures заблокированы до прохождения первых трёх шагов; production estimator и defaults не меняются автоматически.

## 2026-11-03 — Инвентаризация документации DOC-016

- Проведена инвентаризация 56 Markdown-файлов `docs/` и 16 Markdown-файлов корня `AutoDraw_Stage20/`.
- Создан `DOCUMENTATION_INVENTORY_2026-11-03.md` с классификацией действующих/исторических материалов и правилами сопровождения.
- Основной индекс синхронизирован с завершённым INT006R visual audit; ранний CHALK next-steps plan помечен историческим; удалены дублирующие ссылки FILL-001.
- Добавлены DOC-016 и DEC-013. Архивные файлы сохранены согласно DEC-002; код и данные не менялись.

## 2026-11-03 — FILL-001 raster prototype gates

- Проверены grid и eroded-contour fill prototypes на frozen masks. Первый не покрывает ≥99% на части больших радиусов; второй оставляет небольшой leakage/undercoverage в отдельных cells.
- Ни один prototype не принят для executor. Следующая реализация должна быть boundary-aware и одновременно пройти coverage ≥99% / leakage=0.

## 2026-11-03 — FILL-001 frozen target masks implementation

- Добавлен `source/preparation/chalk_fill_experiment.py` с тремя детерминированными frozen masks на logical canvas 460×240: rectangle, wide_irregular, narrow_irregular.
- Площади 44 653 / 45 159 / 44 879 px; разброс max/min — 1,133%, в пределах ±5%.
- SHA-256 масок закреплены в коде; добавлены 8 regression tests на hash, площадь, геометрию, связность и invalid input.
- Локальный тестовый прогон — 8 passed. Полный GitHub Actions для новых commits пока не подтверждён; fixed-radius generator, matrix/block harness и live captures не готовы.

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


## 2026-11-03 — FILL-001 fixed-radius planner

- Добавлен изолированный boundary-aware fixed-radius scanline planner и raster simulator для трёх frozen masks и радиусов 1/5/10/20/30.
- Добавлены regression tests для 15 shape×radius cells, coverage/leakage gate, radius isolation и deterministic signature.
- Офлайн Python simulation прошла 15/15 cells (coverage 99,962–100%, leakage=0); pytest/CI для нового HEAD пока не подтверждены. Executor handoff и production defaults не менялись.


## 2026-11-03 — FILL-001 matrix and analyzer

- Добавлен отдельный 45-cell manifest для трёх форм, пяти радиусов и трёх повторов.
- Добавлены fail-closed capture validation по exact CHALK, dynamic expected strokes, geometry/mask/run identity, coverage/leakage и целостности Game Monitor.
- Добавлен analyzer с отдельной статистикой exact CHALK по форме и радиусу и regression tests.
- CI/pytest для актуального HEAD пока не подтверждены; live execution не запускалось.


## 2026-11-03 — FILL-001 capture fixture correction

- Исправлен тестовый capture helper: теперь он формирует обязательные per-stroke CHALK deltas и PNG evidence fields, соответствующие текущему validator contract.
- Добавлены negative checks для отсутствующего PNG evidence и неверного количества per-stroke deltas.
- Commit: [70323a8](https://github.com/Kiddos19882/AutoDraw/commit/70323a8e65ccddd201aa412263aac9efe18ec099). Pytest/CI для этого изменения ещё не подтверждены.


## 2026-11-03 — FILL-001 Game Monitor capture adapter

- Добавлен адаптер Monitor export → FILL-001 capture с per-stroke/run exact CHALK, radius, P1 sampling binding, external bridge/run identity и PNG file/hash/pixel audit.
- Добавлен отдельный набор regression tests с синтетическими Monitor events и PNG fixtures.
- Software tests/CI ещё не запускались или не подтверждены; live execution остаётся заблокированным до CI и preflight.


## 2026-11-03 — FILL-001 matrix schema v2

- Matrix manifest теперь фиксирует P1 sampling metadata в каждой task; validator отклоняет изменённый профиль.
- Adapter закреплён за Game Monitor 0.2.1 и проверяет frozen mask SHA-256 и bridge diagnostics binding.
- Тесты добавлены, но ещё не запускались; CI pending.


## 2026-11-03 — справочник Game Monitor и Bridge

- Добавлен `GAME_MONITOR_BRIDGE_REFERENCE.md` с описанием Monitor 0.2.1 API, событий BoardPane, Browser Bridge transport, Python collector/RunRecorder, JSON форматов и ограничений evidence.
- Справочник добавлен в основной `docs/README.md` и структурный `MODULE_REFERENCE.md`.
- Изменения документационные; runtime-код и тесты не изменялись.


## 2026-11-03 — FILL-001 launch integration audit

- Добавлен аудит пользовательского пути запуска FILL-001 в AutoDraw.
- Уточнён статус: Stage 6 runtime binding — post-execution hook; UI/runner workflow и FILL001 executor override отсутствуют.
- Временный план и roadmap обновлены: UI/runner handoff должен быть реализован до Windows live preflight; 45 captures остаются заблокированными.


## 2026-11-03 — FILL-001 CI confirmation

- GitHub Actions run `41692129486` завершился SUCCESS: обязательные regression jobs, INT-006 pixel audit, Windows portable build и startup smoke-test прошли.
- Опубликован Windows portable artifact `autodraw-g3-preflight-build` (ID `13258221572`): https://github.com/Kiddos19882/AutoDraw/actions/runs/41692129486/artifacts/13258221572.
- Это подтверждает software gate, но не live runtime. Следующий шаг — один пользовательский Windows preflight; 45 captures остаются заблокированными.


## 2026-11-04 — FILL-001 Bridge activity-window fix

- Runtime binding больше не принимает поздний `finished_at_utc` за время последнего события. Activity window восстанавливается по `started_at_utc`, `started_at_performance_ms` и максимальному `events[].t`; idle finalization grace проверяется отдельно.
- Добавлены regression tests для pre-execution calibration run и Bridge JSON >27 MiB, включая проверку полного чтения и SHA-256.
- Commits: `95a8d1799cd2cbbba09929cc5086a3655ba90c78` (fix), `870bebce6b39e782f70ef9f476a324ee840c05ae` (tests). CI ожидается.

## 2026-11-04 — FILL-001 CI fixture alignment

- Анализирован run [41778045384](https://github.com/Kiddos19882/AutoDraw/actions/runs/41778045384): Preparation/G3 — 799 passed, 5 failed, 24 warnings, 82 subtests; три других обязательных test jobs success, downstream PNG audit и Windows build skipped.
- Исправлены synthetic PNG fixtures: согласование с реальным executor transform, non-uniform ROI test теперь доходит до audit, runtime-binding fixture использует screen rasterization.
- Commits: `1f28436ab20fe949e4d53cfeea4a5560ed3cbcae`, `0f23731848f0c148fe5e1309d1e305576dd4b6b7`. Только тесты; production code и acceptance thresholds не менялись. Повторный CI ожидается.


## 2026-11-04 — FILL-001-RS CI PASS и INT006R evidence

- Run [41780241017](https://github.com/Kiddos19882/AutoDraw/actions/runs/41780241017): все обязательные CI jobs SUCCESS; optional benchmarks SKIPPED.
- FILL-001-RS static sweep: 2,238 candidates, 62 accepted, 15/15 selected offline cells прошли coverage≥99% / leakage=0; estimated points не являются exact CHALK.
- INT-006 pixel audit: 90/90 captures valid, 549 stroke rows, coverage=1.0, gaps=0. Frozen CHALK analyzer: 45/45 accepted; safety margin не установлен, production eligibility не подтверждена.
- INT006R radius×geometry: 45/45 accepted, radius 1/10/30 tested at P1; расходы различаются слабо и немонотонно. 45 PNG pairs сохранены, visual review остаётся pending.
- Production estimator/defaults и live data не изменялись.

## 2026-11-04

- Зафиксирована блокирующая задача FILL-001-RS-PRE-REPLAY-001: replay неизменённых исходных live PNG/evidence через исправленный PNG audit обязателен до следующего live запуска FILL-001-RS. Установлены критерии закрытия, сохранение hashes/raw evidence и запрет на ослабление PNG thresholds. 45-task matrix остаётся заблокированной.

## 2026-11-04 — FILL-001-RS offline edge diagnosis and contour candidate

- Зафиксировано offline OpenCV model breakdown: 304 uncovered target pixels planner model распределены по краевым полосам (80 top, 80 bottom, 72 left, 72 right; interior=0), leakage=0.
- Добавлен exploratory sweep одного contour pass поверх scanline fill: inward offsets 6–8 px проходят модельные coverage≥99% / leakage=0; offset 5 px имеет 32 leakage pixels.
- Actual PNG residual pixel coordinates остаются неразобранными; capture по-прежнему REJECTED. Contour pass не реализован и не live-validated; CHALK не прогнозировался.
- Только документация; исходники, тесты, настройки, frozen plan, thresholds и production defaults не изменялись.

## 2026-11-04 — FILL-001-RS actual PNG residual diagnostics

- В committed capture replay test добавлен вывод координат фактических uncovered/leakage pixels исходной PNG pair, пространственного распределения, connected components и расстояний до affine-transformed scanline centerlines.
- Изменение ограничено тестовой диагностикой; production audit, исходные evidence, frozen plan/mask, thresholds и defaults не менялись.
- Commits: `e62b692`, `d337f42`. Выполнение диагностического теста и его численный результат ожидают подтверждения CI.
## 2026-11-04 — FILL-001-RS actual PNG residual localization

- CI confirms committed-evidence pixel diagnostic: 1116 uncovered target pixels, distributed entirely in configured perimeter zones; 0 interior/other.
- Right perimeter is dominant residual region (largest component 870 px); 11 leakage pixels are sparse near left perimeter / rounded corners.
- Result supports investigating brush footprint and stroke endpoints before changing row spacing. No production behavior, frozen plan or acceptance thresholds changed.
- Workflow 41787492122 SUCCESS; Preparation/G3 804 passed, 82 subtests passed.


## 2026-11-04 — FILL-001-RS game renderer source inspection

- Получен полный game bundle из master через GitHub Contents API; зафиксированы commit/blob identity и статические участки BoardPane/Painter.
- Подтверждены ENTER_FRAME sampling, dedup соседних одинаковых координат, O(N) пересчёт point count на каждый принятый sample и передача brush value в lineStyle thickness.
- Выявлено, что smooth single-point path формирует moveTo+lineTo в одну координату; фактическое окрашивание нулевого сегмента и cap geometry остаются UNKNOWN.
- Следующий gate перенесён с pixel localization (закрыто) на renderer footprint / frame sampling calibration. Capture REJECTED, 45-task matrix BLOCKED.
- Только документация; production code, tests, configs, frozen plans, thresholds и raw captures не менялись.


## 2026-11-04 — Game Monitor per-stroke timing telemetry

- Browser Bridge добавляет strokeId в frame_probe.
- Bridge Server сохраняет исходные intervals, добавляет frame_probe_by_stroke и per_stroke_metrics.
- Сохранённый FILL-001-RS run показывает accepted-point cadence около 29 points/s при browser requestAnimationFrame около 60 FPS; эти показатели документированы раздельно.
- CI для изменений кода/тестов ожидает завершения; live runtime не запускался.


## 2026-11-04 — Egret renderer audit refinement

- Зафиксирован nominal stage.frameRate=48 и локальная геометрия PainterPopup/BoardPane 676×379 / 460×240.
- Egret Engine 5.2.18 API документирует lineStyle thickness как толщину линии и ROUND defaults для caps/joints. Deployed runtime version не подтверждена; фактический footprint и zero-length rasterization остаются открытыми.


## 2026-11-04 — Game Monitor per-stroke telemetry CI verification

- Per-stroke frame_probe и point timing telemetry прошли полный CI run [41840582147](https://github.com/Kiddos19882/AutoDraw/actions/runs/41840582147): Application integration, Game Monitor/Bridge, Preparation/G3, Executor regression, Windows portable build/startup smoke-test и INT-006 PNG audit — SUCCESS; optional benchmarks SKIPPED.
- Run [41840281018](https://github.com/Kiddos19882/AutoDraw/actions/runs/41840281018) завершился CANCELLED; не считать его успешным.
- Сохранённые per-stroke frame probes для будущих запусков связаны через strokeId; старый run не содержит raw per-stroke rAF intervals. Измеренная ранее cadence POINT_QUOTA_UPDATE остаётся 28.26–29.50 points/s, median 33 ms; browser rAF около 60 FPS не является частотой Egret ENTER_FRAME.
- Renderer gate уточнён: nominal stage.frameRate=48, NO_SCALE, PainterPopup 676×379, BoardPane 460×240 без локального scale; deployed Egret runtime, global transform, zero-length rasterization и реальный brush footprint ещё не подтверждены.
- Capture FILL-001-RS остаётся REJECTED (coverage=98.430600%, leakage=11; exact CHALK=1260); 45-task matrix BLOCKED. Production defaults, frozen plans/masks/thresholds и raw evidence не изменялись.


## 2026-11-04 — Egret stroke geometry and planner footprint risk

- Egret GraphicsNode defaults omitted caps/joints to ROUND; CanvasRenderer applies them. The reviewed WebGL renderer also delegates GraphicsNode rasterization to CanvasRenderer.
- For compatible Canvas rendering, a zero-length single-point path is removed and does not paint, while the game point counter can still increase.
- Planner bbox footprint can overestimate coverage around rounded endpoints in interior_fill_planner and outline_first_fill_planner. Added separate offline task BRUSH-FOOTPRINT-CAPSULE-001; no planner code changed.
- CI workflow 41840582147 SUCCESS; all required jobs passed, optional benchmarks skipped.


## 2026-11-04 — BRUSH-FOOTPRINT-CAPSULE-001 audit

- Статический аудит выявил AABB coverage overclaim в experimental `interior_fill_planner`: bbox маркируется как полностью покрытая область, хотя round-cap stroke имеет capsule footprint; текущий independent test oracle использует rectangular model.
- Уточнена область: `swept_footprint_geometry` и `outline_first_fill_planner` используют bbox как conservative safety check; FILL-001-RS имеет отдельный OpenCV round-capped rasterizer, поэтому причинная связь не доказана.
- Код и тесты не менялись. Следующий шаг — offline masks для потенциально затронутых и гарантированно покрытых pixel cells с frozen-fixture comparison.

## 2026-11-04 — capsule footprint candidate and CI

- Offline capsule pixel-cell candidate прошёл первоначальный полный CI [41842587672](https://github.com/Kiddos19882/AutoDraw/actions/runs/41842587672): 820 passed, 24 warnings, 82 subtests; обязательные jobs и Windows portable build/startup smoke-test SUCCESS; optional benchmarks SKIPPED.
- Добавлены independent analytic oracle и уточнение conservative potential/guaranteed predicates; повторный CI [41843716918](https://github.com/Kiddos19882/AutoDraw/actions/runs/41843716918) ожидает завершения.
- Existing planner behavior/defaults не менялись; live renderer validation не проводилась.


## 2026-11-04 — приоритет connected-contour кандидата для FILL-001-RS

- По запросу пользователя зафиксирован ключевой концептуальный вывод: для периметр-доминантных пропусков сравнивать редкий внутренний scanline-fill + один связный обход контура + локальные внутренние коррекции с глобальным уплотнением scanline и с горизонтальными коррекциями.
- Уточнено, что исторический outline-first prototype использовал независимые горизонтальные boundary runs, а не единый связный contour route; его результаты не опровергают новую гипотезу.
- Вывод классифицирован как OPEN / OFFLINE CANDIDATE / HYPOTHESIS. Экономия CHALK не доказана; exact расход определяется только pointCount delta. Сохранены PNG acceptance thresholds и текущие renderer/live gates.
- Изменены только документационные файлы: AI_WORK_GUIDE, docs index, TASKS, ROADMAP, WORK_LOG и CHANGELOG. Исходники, тесты, конфигурации, frozen plans/masks и экспериментальные данные не менялись; live run не выполнялся.


## 2026-11-04 — capsule model: per-segment raster broad-phase

- Переработан перебор pixel cells в `swept_capsule_pixel_masks()`: вместо полного global polyline AABB каждая capsule обрабатывает собственный расширенный AABB, результаты объединяются как union.
- Сохранены API, global bounds, определение potential/guaranteed и fail-closed ограничения; production planners не подключались.
- Добавлены тесты эквивалентности с прежним global-AABB reference на winding polyline и инвариантности разбиения прямого сегмента на коллинеарные части.
- Ожидаем CI run [41848358502](https://github.com/Kiddos19882/AutoDraw/actions/runs/41848358502) на HEAD `6afdefc7ff2f18db544e55572ed918841d448164`. Фактический performance gain пока не измерен; live/runtime проверок не было.


## 2026-11-04 — capsule broad-phase benchmark and independent oracle

- Добавлен независимый full-canvas oracle для swept capsule polyline и 16 seeded cases; все potential/guaranteed masks совпали с production model.
- Добавлен offline benchmark global-AABB vs per-segment AABB и CI artifact. Пять synthetic cases дали совпадение masks; candidate slots сокращены на 59.53–96.23% для многосегментных случаев и не сократились для single segment.
- Median wall-clock speedup в Windows CI runner: 10.91× winding, 20.57× large zigzag, 2.76× diagonal turns, 14.10× compact polyline, 1.16× single segment. Не универсальная гарантия и не CHALK/runtime measurement.
- Full CI [41859709320](https://github.com/Kiddos19882/AutoDraw/actions/runs/41859709320) — SUCCESS: Preparation/G3 832 passed, 24 warnings, 82 subtests; all required jobs, INT-006 PNG audit and Windows portable build/startup smoke-test SUCCESS; optional algorithm benchmarks SKIPPED. Artifact `13338434277`.
- Planner integration, deployed Egret renderer validation and live experiments не выполнялись; production defaults и frozen FILL-001 evidence не менялись.


## 2026-11-04 — реестр тестирования

Добавлен [TEST_RESULTS.md](TEST_RESULTS.md) как центральная сводка результатов.


## 2026-11-04 — единый актуальный backlog задач

В начало TASKS.md добавлен консолидированный список незавершённых задач с приоритетами, статусами, подзадачами, зависимостями и критериями завершения. Исторические чек-листы сохранены; старые TODO не считаются активными без повторной проверки.

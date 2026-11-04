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

- Выполнен committed replay test `test_chalk_fill_committed_capture_replay.py` через реальный `Fill001Tab.finalize_capture()`; использованы исходные manifest, attempt, executor report, runtime plan, Bridge session/run records, legacy session и before/after PNG из evidence commit [5308214](https://github.com/Kiddos19882/AutoDraw/commit/530821497ce3a6bd5152318a78e1f06cb836f288).
- Подтверждающий CI [41780241017](https://github.com/Kiddos19882/AutoDraw/actions/runs/41780241017), checkout HEAD `0f23731848f0c148fe5e1309d1e305576dd4b6b7`: Preparation/G3 — 804 passed, 24 warnings, 82 subtests; в логе replay зафиксировано coverage=98.430600%, leakage=11, status=failed. Все обязательные jobs завершились SUCCESS; optional benchmarks SKIPPED.
- Runtime binding PASS: выбран run `6a17a297-ea14-4527-9527-bfd8de3bd335`, session `bb261898-8296-41f5-a333-eb0b81016410`, 27/27 strokes, observed radius=10, exact pointCount 1→1261, CHALK=1260; sampled point delta совпадает с CHALK, dropped events/Monitor errors/Bridge send failures/sequence gaps — 0.
- Corrected audit улучшил прежние 97.673218% / 28 до 98.430600% / 11, но оба неизменённых gate conditions всё ещё нарушены (coverage≥99%, leakage=0). Capture остаётся REJECTED/PENDING, 45-task matrix BLOCKED.
- SHA-256 исходных PNG и всех входных JSON сохранены в [CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md](CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md).
- Дополнительно разрешено расхождение `source_plan_file_sha256`: hash committed runtime plan с LF отличается от runtime report, но hash того же текста с CRLF точно совпадает с `644cbf85a44481a5ecbe0fb2d88383dd1b13835c443dc240c0aa5700b4a8565f`. Это подтверждает line-ending normalization; содержательного mismatch plan file не обнаружено.
- Остаточная причина не установлена. Следующий шаг — offline coordinate breakdown uncovered/leakage pixels и диагностические overlays на той же паре PNG. Live запуск и изменения production-кода не выполнялись.

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

## 2026-11-04 — FILL-001-RS — exhaustive sweep and versioned implementation

- Проверены branch, HEAD, последние 20 коммитов, README, docs index, управляющие документы и постоянные engineering/experiment регламенты. GitHub API не даёт локальный git status.
- Полный статический sweep: 2 238 комбинаций step/offset для 3 frozen masks × 5 radii; 62 кандидата прошли coverage≥99%/leakage=0. Frozen mask SHA-256 совпали с константами исходника. Baseline rectangle/r10/step1 воспроизведён: 131 strokes, path=40 218, estimated points=10 237, coverage=100%, leakage=0.
- Зафиксирован выбор кандидатов: максимальный прошедший row step, затем максимальное coverage и минимальные estimated points/path/strokes. Полный отчёт — CHALK_FILL001_RS_STATIC_SWEEP_2026-11-04.md; CI script сохраняет все candidate records.
- Реализован versioned scanline spacing planner v2. Legacy planner v1/default geometry/signatures сохраняются. scanline_row_step и scanline_offset включены в v2 plan identity; point_step_px/P1 не менялись.
- Реализованы отдельный FILL001_RS_V1 45-task matrix builder, fail-closed validation, single-task plan handoff и runtime experiment context с spacing metadata. Добавлены CLI manifest generator и capture metadata.
- Добавлены regression tests: versioned geometry, invalid parameters, matrix tampering, legacy compatibility, single-task handoff, runtime context, exhaustive 2 238-candidate sweep.
- Полный CI на code/test commit `dac985e147319d2275318531ab9063cdf410e5a4` — [41766148192](https://github.com/Kiddos19882/AutoDraw/actions/runs/41766148192) SUCCESS: Preparation/G3 800 passed, 24 warnings, 82 subtests; exhaustive sweep 2 238 candidates / 62 passed; executor, Game Monitor/Bridge, application integration, INT-006 pixel audit и Windows portable build/startup smoke-test SUCCESS. 24 pytest warnings — Pillow Image.getdata deprecation in existing brush_experiment_capture.py; optional benchmarks skipped.
- Изменены исходники preparation, tests, CI workflow и Markdown docs только в feature/image-geometry-optimization. master и исходные FILL-001 manifests/captures не менялись.
- UI-кнопка для прямого создания RS manifest не добавлена; manifest генерируется CLI и открывается существующей кнопкой «Открыть manifest…». Это сохраняет существующий UI workflow без незавершённого action.
- Live preflight не запускался: удалённый runner не имеет доступа к локальной Windows/browser game session и calibrated board. Пользователь разрешил live work; фактическая блокировка — отсутствие доступного локального runtime control.
- Следующий шаг: локально создать manifest и выполнить только rectangle/r10/step5/offset0/repeat1 на доступной Windows/game session с полной квотой; принять capture только при exact runtime binding и quantitative PNG audit. До этого обе 45-task matrices остаются BLOCKED, INT-007 остаётся BLOCKED.

## 2026-11-04 — FILL-001-RS — scanline spacing documentation

- Повторно сверены branch `feature/image-geometry-optimization`, HEAD `4f1fb945f384aba0b3454e4301b248cf74101800`, последние 20 коммитов и актуальные управляющие документы. GitHub API не предоставляет локальный `git status`.
- Проверено, что commit 4f1fb94 содержит документационные изменения по FILL-001; commit 73d14a1 добавил пользовательские runtime artifacts; последний code/test commit — 5cde7a1. CI [41754801210](https://github.com/Kiddos19882/AutoDraw/actions/runs/41754801210) SUCCESS относится к 5cde7a1, не к текущему документационному HEAD.
- Основание этапа: live task run подтвердил exact CHALK=5999, но 128/131 consuming strokes; три последних кандидата не потребили ресурс после quota exhaustion. Capture rejected, полная стоимость незавершённого плана неизвестна.
- Зафиксирован статический OpenCV baseline: rectangle/r10 — 131 strokes, path 40 218, estimated sampling points 10 237, coverage 100%, leakage 0; текущие проходы располагаются практически на каждой строке.
- Задокументированы результаты r10/step=5/offset=0 для трёх форм: 27/29/43 strokes; coverage 99,319%/99,395%/99,173%; leakage 0. Для rectangle estimated sampling points 2 099 против 10 237 baseline. Это офлайн proxy, не игровой результат и не CHALK.
- Временный FILL-001 plan дополнен этапом FILL-001-RS: отделены `scanline_row_step` и `point_step_px`, сохранены предварительные step/offset candidates для 15 shape×radius combinations, описаны versioned plan/signature, static/live gates и обработка quota-censored attempts.
- Обновлены PROJECT_STATUS, TASKS, ROADMAP, DECISIONS, CHANGELOG и docs index. Изменения ограничены Markdown; исходники, тесты, конфигурации, workflow, runtime/experimental data и `master` не менялись.
- Live experiment и тесты не запускались; CI для документальных изменений не запускался. Commit не создавался отдельно по окончании серии; обновления GitHub Contents API создают отдельные последовательные commits.
- Следующий шаг: воспроизвести полный статический sweep и сохранить исходные метрики; после этого запросить отдельное разрешение на код/тесты и live preflight. FILL-001 45-cell matrix остаётся BLOCKED; INT-007 остаётся BLOCKED.

## 2026-11-04 — FILL-001 transient Bridge session retry: CI SUCCESS

- Повторно проверены ветка feature/image-geometry-optimization, branch HEAD после пользовательского evidence commit b4a107a, последние 20 коммитов, README Stage20, docs index, управляющие документы и пять постоянных регламентов.
- На commit b4a107a подтверждены executor completed 131/131 strokes, сохранённый after PNG и runtime_binding_status=failed с сообщением об отсутствии bridge_diagnostics. Финальная версия Bridge session в этом commit уже содержала diagnostics; session-level CHALK delta — 5999. Capture не принят.
- Найдена причина: binder проверял bridge_diagnostics до фильтрации session по executor time window; transient incomplete session выбрасывала fatal FillMatrixError. Stage 6 worker прекращал retry, а FILL-001 UI не запускал binder повторно.
- Исправлено в [5cde7a1](https://github.com/Kiddos19882/AutoDraw/commit/5cde7a109a669bebf790ecbeb21f8bbc4feae182): incomplete potentially relevant session возвращает pending; будущие/закрытые до executor sessions исключаются до строгой проверки diagnostics; кнопка FILL-001 повторно запускает binder; summary builder общий для Stage 6/UI; worker не перезаписывает уже подтверждённый passed status.
- Добавлены regression tests на incomplete → finalized session retry, filtering future session и повторную привязку из UI до PNG acceptance.
- Полный GitHub Actions [41754801210](https://github.com/Kiddos19882/AutoDraw/actions/runs/41754801210) завершился SUCCESS: Preparation/G3 — 787 passed, 24 warnings, 82 subtests; Executor regression, Game Monitor/Bridge, Application integration, INT-006 pixel audit и Windows portable build/startup smoke-test — SUCCESS; optional algorithm benchmarks — SKIPPED.
- Windows portable artifact [autodraw-g3-preflight-build](https://github.com/Kiddos19882/AutoDraw/actions/runs/41754801210/artifacts/13288855067), 637,575,055 bytes.
- Обновлены PROJECT_STATUS, TASKS, ROADMAP, временный FILL-001 plan, postmortem, DECISIONS и CHANGELOG. Первичные runtime evidence и PNG не изменялись. Production estimator/defaults, sampling defaults и master не менялись.
- Локальный clone/pytest не запускался: попытка Git clone завершилась ошибкой DNS; GitHub Actions использован как удалённая проверка. Через GitHub API локальный git status недоступен.
- Live preflight не выполнялся. Capture остаётся REJECTED/UNACCEPTED: session-level CHALK=5999, task-level/per-stroke attribution и quantitative FILL-001 PNG audit не подтверждены; использованная доска исчерпана. Следующий gate — один новый Windows live preflight на восстановленной доске; 45-cell matrix остаётся BLOCKED.

## 2026-11-04 — FILL-001 binder activity-window fix: CI verification

- Проверены рабочая ветка `feature/image-geometry-optimization`, последние 20 коммитов, README Stage20, основной индекс, управляющие документы, постоянные регламенты, runtime binder и его regression tests.
- На начало проверки branch HEAD: `1d41deea36dd1f821a0fb6155d2945beb849b009`; последний code/test commit — `870bebce6b39e782f70ef9f476a324ee840c05ae`; master — `9a3453aeb847b66041bc83d6f4a56ecaf33a993a`. Compare: feature diverged, ahead 2700 / behind 5, merge base `d4a07702e45c01648f343bc6440a3287c45d3f9c`. GitHub API не предоставляет локальный `git status`.
- Подтверждён GitHub Actions [41737923777](https://github.com/Kiddos19882/AutoDraw/actions/runs/41737923777) на commit `870bebc`: Application integration, Executor regression, Preparation/G3, Game Monitor/Bridge, INT-006 pixel audit и Windows portable build/startup smoke-test — SUCCESS; optional benchmarks — SKIPPED.
- Portable artifact [autodraw-g3-preflight-build](https://github.com/Kiddos19882/AutoDraw/actions/runs/41737923777/artifacts/13280731107) опубликован, не истёк.
- Проверены regression tests на исключение pre-execution calibration run при поздней idle finalization и на загрузку/hash Bridge JSON размером более 27 MiB. Код binder использует performance-clock timestamp последнего события для конца activity window; `finished_at_utc` ограничен проверкой finalization grace.
- Предыдущий FILL-001 live preflight остаётся REJECTED/UNACCEPTED: 131/131 strokes, session CHALK=5999; per-run/per-stroke attribution второго Bridge run и quantitative PNG audit не подтверждены. Использованная доска исчерпала квоту. 45-cell matrix остаётся BLOCKED.
- В этой сессии исходники, тесты, конфигурации, workflow и первичные runtime evidence не изменялись. Синхронизированы только управляющие Markdown-документы. `master` не изменялся; live-эксперименты не запускались.
- Следующий шаг: восстановить/заменить игровую доску, запустить portable build и выполнить ровно один Windows live preflight `rectangle / radius 10 / repeat 1`; сохранить execution report, Bridge session/run, Game Monitor export и before/after PNG для проверки runtime binding и frozen-mask quality gates.

## 2026-11-04 — FILL-001 postmortem и актуализация gates

- Проверены feature branch, code HEAD `fe6d4469a5294fdf8284978d4e2b5c47582fa2d4`, последние 20 коммитов, master reference, compare и полный CI run [41730717881](https://github.com/Kiddos19882/AutoDraw/actions/runs/41730717881).
- Все обязательные CI jobs завершились SUCCESS: Executor regression, Game Monitor/Bridge, Application integration, Preparation/G3 (782 passed, 24 warnings, 82 subtests), INT-006 pixel audit и Windows portable build/startup smoke-test. Optional benchmarks skipped.
- Проанализирован пользовательский FILL-001 run: Stage 6 131/131 strokes, 225.61 s, 12 857 move calls, P1 step=4/delay=5, exact session pointCount 1→6000 (CHALK=5999), no dropped events/errors/sequence gaps/send failures.
- Первый Bridge run разобран полностью: calibration, 2 non-consuming candidates, CHALK=0, 69 brush changes, radius 8–30. Второй Bridge run file присутствует (27 934 553 bytes), но его содержимое не удалось получить через GitHub file API; task-level/per-stroke CHALK не объявлен подтверждённым.
- Attempt JSON invalid из-за буквального `\\n`; after PNG физически существует и визуально просмотрен, но количественный frozen-mask audit не проведён. Capture остаётся rejected.
- Найдено дополнительное статическое несоответствие binder: он использует `finished_at_utc` как конец activity interval. Калибровочный run закончил события 21:26:17.416Z, executor начался 21:26:19Z, но idle finalization завершилась 21:26:20.862Z; текущая логика ошибочно считает его overlapping. Исправление кода не выполнялось; следующий gate — activity-window matching + regression.
- Создан postmortem `CHALK_FILL001_PREFLIGHT_POSTMORTEM_2026-11-04.md`; обновлены PROJECT_STATUS, TASKS, ROADMAP, временный FILL-001 plan, docs index и CHANGELOG.
- Исходники, тесты, workflow, настройки и raw experiment data в рамках этой аналитической задачи не менялись. `master` не изменялся. Локальный git status через GitHub API недоступен.
- Следующий шаг: исправить binder, добавить regression на idle finalization grace, повторить CI; затем один live preflight на восстановленной доске. 45-cell matrix и production estimator/defaults не менять.

## 2026-11-04 — FILL-001 post-run persistence and canonical hash fixes

- Повторно проверены ветка feature/image-geometry-optimization, code HEAD 3b67aea0145170ec23df089916bedf7828de9a68, последние коммиты, README Stage20/docs index, управляющие документы и постоянные регламенты.
- Разобран пользовательский live preflight: Stage 6 завершил 131/131 strokes; after PNG присутствует. Attempt JSON был повреждён буквальными символами \\n в конце записи, что блокировало последующее чтение/финализацию.
- Исправлены все четыре ошибочных JSON suffixes в chalk_fill_ui.py: completion attempt, after PNG update, capture JSON и финальный attempt record.
- Выявлено расхождение hash contract: подготовка использовала DrawingPlan-normalized document, а validator хешировал сырой JSON. Добавлена единая нормализация через geometry_models.DrawingPlan.from_dict(...).to_dict(); attach теперь сохраняет нормализованный документ, чтобы default fields/created_at были стабильны при повторной загрузке.
- Добавлены regression tests для executor completion → after PNG → valid attempt JSON; finalize_capture → valid capture/attempt JSON; model normalization of metadata/coordinates before hash validation.
- Code commits: [2b7577c](https://github.com/Kiddos19882/AutoDraw/commit/2b7577c3a3289871b7fff300fd6013f12c7cb54e), [3b67aea](https://github.com/Kiddos19882/AutoDraw/commit/3b67aea0145170ec23df089916bedf7828de9a68).
- CI [41728163369](https://github.com/Kiddos19882/AutoDraw/actions/runs/41728163369) на 3b67aea: Game Monitor/Bridge SUCCESS; Executor regression SUCCESS; Preparation/G3 и Application integration ещё выполняются; Windows portable build ждёт обязательные jobs; optional benchmarks SKIPPED. Run [41727944296] был отменён последующим push и не считается failed.
- Bridge run file для второго запуска имеет размер 27,934,553 bytes в Git tree; API fetch не вернул содержимое из-за размера, поэтому нельзя называть файл пустым. Требуется full artifact audit.
- Game pointCount: 1 → 6000; квота CHALK на использованной доске исчерпана. Capture не принят, per-stroke attribution/PNG quality audit ещё не подтверждены. Повторный live run на этой доске не выполнялся; 45-cell matrix остаётся BLOCKED.
- Изменены только два исходных файла и два тестовых файла. Production estimator/defaults, sampling defaults и master не менялись. Локальные pytest недоступны из-за отсутствия DNS к github.com; CI используется как удалённая проверка. Локальный git status недоступен через GitHub API.

## 2026-11-03 — DOC-018: постоянная система управления знаниями для ИИ

- Повторно проверены рабочая ветка `feature/image-geometry-optimization`, HEAD `759f6531f3e715c5ff67a7692f707b0f8269fd42`, последние 20 коммитов, README Stage20, основной индекс, управляющие документы и инвентаризация Markdown.
- Созданы пять постоянных регламентов: `AI_WORK_GUIDE.md`, `KNOWLEDGE_ARCHITECTURE.md`, `EVIDENCE_AND_VALIDATION.md`, `ENGINEERING_INVARIANTS.md`, `EXPERIMENT_STANDARD.md`.
- Регламенты определяют единый старт ИИ, роли источников знаний, владельца изменяемого факта, уровни E0–E5, статусы проверок, критические инварианты и воспроизводимую методику экспериментов.
- Система не создаёт второй текущий статус, динамический дублирующий список ограничений или копию экспериментальных результатов. Исторические материалы и первичные данные не удалялись.
- Обновлены README Stage20, docs/README.md, PROJECT_STATUS.md, TASKS.md, ROADMAP.md, DECISIONS.md и CHANGELOG.md. Добавлено решение DEC-016 и задача DOC-018.
- Изменения ограничены Markdown-документацией. Исходники, тесты, конфигурации, workflow и экспериментальные данные не изменялись; тесты и CI не запускались.
- GitHub API использован для чтения ветки и истории; локальный `git status` через этот интерфейс недоступен.

## 2026-11-03 — FILL-001: исправление runtime JSON handoff
- Проверены ветка `feature/image-geometry-optimization`, HEAD и последние 20 коммитов; изучены README приложения, индекс docs, управляющие документы, временный план FILL-001 и call graph UI → integrated_app → Stage 6.
- Изучен пользовательский data commit [6b1cba9](https://github.com/Kiddos19882/AutoDraw/commit/6b1cba9b1c40a030ac6bd7b29365bf19ac3c9149): manifest FILL-001, DrawingPlan `rectangle/radius=10/repeat=1` на 131 штрих, before PNG, Bridge session и runtime plan.
- В Bridge session Monitor active/boardDetected и exact snapshot pointCount=1/remainingPoints=5999; `received_event_count=0`, `sentEventCount=0`; after PNG и executor report отсутствуют. Передача не дошла до рисования.
- Причина двух сообщений установлена в `integrated_app.py::_transfer_brush_test_plan()`: после добавления `autodraw_experiment` runtime JSON записывался с буквальной последовательностью `\n` после закрывающей скобки. `Stage6App.load_plan_from_path()` не мог разобрать файл; callback возвращал False, после чего `Fill001Tab` показывал вторичное сообщение об отказе Stage 6.
- Исправлено добавление настоящего перевода строки и форматирование текста исключения в commit [8dfd1b5](https://github.com/Kiddos19882/AutoDraw/commit/8dfd1b541f54a1b416dfb2907739cf4b1a99c58d).
- Добавлен integration regression test `test_fill001_plan_transfers_valid_json_context_to_stage6`: генерирует frozen FILL-001 task, передаёт план через `_transfer_brush_test_plan()`, проверяет JSON, experiment context и фактическую загрузку Stage 6. Test commit [1b2d8a1](https://github.com/Kiddos19882/AutoDraw/commit/1b2d8a128c99ab8ad1abb1e9f480702676cd9f56).
- Обновлены PROJECT_STATUS, TASKS, ROADMAP, временный план FILL-001 и CHANGELOG. 45-cell live matrix остаётся BLOCKED.
- Проверка CI после code/test commits: GitHub Actions [41692129486](https://github.com/Kiddos19882/AutoDraw/actions/runs/41692129486) на HEAD `1b2d8a1` — Application integration, Game Monitor/Bridge, Preparation/G3, Executor regression и INT-006 pixel audit завершились SUCCESS; optional benchmarks SKIPPED; Windows portable build/startup smoke-test ещё выполняется. Локальный pytest не запускался; повторный Windows live preflight не выполнялся. GitHub API не предоставляет локальный `git status`; чистота локального worktree не заявляется.

## 2026-11-03 — устранение несогласованностей документации

- Повторно проверены управляющие документы и профильная карта UI в рабочей ветке.
- Устранён повтор номера DEC-013: решение о едином источнике текущего состояния перенумеровано в DEC-015; историческое решение о safety margin оставлено без изменения.
- В TASKS.md приведён перечень статусов к общему стандарту: добавлен DEFERRED, ON_HOLD обозначен как исторический статус.
- UI_INTEGRATION_MAP.md и docs/README.md синхронизированы с фактической нумерацией девяти вкладок: FILL-001 — № 8, калибровка — № 9.
- В ROADMAP.md удалены повторяющиеся устаревшие TODO о CI, уже подтверждённом run 41673570178; актуальным незакрытым gate оставлен Windows live preflight.
- В PROJECT_STATUS.md текущий статус перемещён в начало, историческая запись сохранена ниже без изменения содержания.
- Исходный код, тесты, настройки, workflow, экспериментальные данные и master не изменялись. GitHub API не предоставляет локальный git status; локальная чистота worktree не подтверждается.

## 2026-11-03 — FILL-001 UI/runner integration и подтверждение regression gate

- Повторно сверены рабочая ветка `feature/image-geometry-optimization`, branch HEAD до документационной актуализации `e3774a3c07f7abbefe8c39eecdd9578743b70678`, последние 20 коммитов и управляющие документы. GitHub Contents API не предоставляет локальный `git status`; чистота локального worktree не заявляется.
- Проверен последний code/test commit `e3774a3`: изменён только тестовый fixture `test_brush_behavior_test_ui.py`, добавлена инициализация `_workflow_brush_ready_callback`.
- Подтверждена реализация отдельного `Fill001Tab` в `chalk_fill_ui.py`, регистрация в `integrated_app.py`, single-task plan handoff, experiment context, P1 executor override, Stage 6 launch guard и post-execution Bridge/executor binding.
- Unified app test проверяет наличие `fill001_tab` и подпись вкладки `8. FILL-001`; калибровка теста отображается следующей вкладкой `9. Калибровка теста`. По решению пользователя FILL-001 сохраняется отдельной вкладкой, не объединяется с седьмой вкладкой «Тест кистей».
- Полный GitHub Actions [41673570178](https://github.com/Kiddos19882/AutoDraw/actions/runs/41673570178) завершился SUCCESS на HEAD `e3774a3`: Preparation/G3 — 772 passed, 24 warnings, 82 subtests; Executor regression, Game Monitor/Bridge, Application integration, INT-006 pixel audit и Windows portable build/startup smoke-test — SUCCESS; optional benchmarks skipped.
- Windows portable artifact: [autodraw-g3-preflight-build](https://github.com/Kiddos19882/AutoDraw/actions/runs/41673570178/artifacts/13248469807). CI smoke-test не является live FILL-001 запуском в игре.
- Обновлены текущие статусы FILL-001 и временный план. Исторический аудит до UI integration сохранён и помечен как исторический снимок.
- Оставшийся gate: один контролируемый Windows live run из FILL-001 UI, проверка реального P1 в executor report, однозначного Bridge session/run binding и реальных before/after PNG (crop 460×240, RGB threshold=8, cursor/UI exclusion, coverage ≥99%, leakage=0). До прохождения gate 45-cell matrix не запускать.
- Исходники, тесты, workflow, production estimator/defaults, experiment data и `master` в рамках этой документационной актуализации не изменялись.

## 2026-11-03 — FILL-001 runtime binding integration и актуализация статусов

- Проверены текущая ветка, HEAD, последние 20 коммитов, управляющие документы, временный план FILL-001 и профильная реализация adapter/runtime binding.
- Установлено, что после ранее документированного code HEAD `b4cc45a` добавлены commits `fbf1fd6`–`d7466c5`: runtime binder, fail-closed validation, session/run correlation, Bridge lifecycle/timestamps, фактический P1 check и Stage 6 completion integration.
- Проверен полный GitHub Actions run [41591543009](https://github.com/Kiddos19882/AutoDraw/actions/runs/41591543009) на code HEAD `d7466c5`: все обязательные jobs SUCCESS; optional algorithm benchmarks skipped. Windows portable build/startup smoke-test прошёл.
- Уточнено разделение статусов: шаг 2 FILL-001 закрыт как software/runtime integration + regression gate; реальный Windows runtime proof и PNG preflight остаются шагом 3 TODO. 45 live captures и итоговый CHALK analysis остаются BLOCKED.
- Сверка веток на HEAD `d77a31b`: GitHub compare показывает `diverged`, feature ahead 2527 и behind 5 относительно master. Merge/rebase не выполнялся; master не менялся.
- Обновлены PROJECT_STATUS, TASKS, ROADMAP, временный план FILL-001, harness design, этот журнал и CHANGELOG. Исходный код, тесты, настройки и experiment data в этой документационной актуализации не менялись.

## 2026-11-03 — FILL-001 software regression gate закрыт

- Проверена ветка `feature/image-geometry-optimization`; последние 20 коммитов просмотрены. Code HEAD для CI: `b4cc45a80231e6bad2f878b2a5a2f16b48b9d68b`; последующие коммиты до `f72d4d3c9a2b9236b45d6c2f45ea5c6dcccbc456` относятся к документации.
- Проверен diff `b4cc45a`: из сигнатуры `audit_fill001_png_pair()` удалены ошибочно добавленные обязательные аргументы `run_id` и `bridge_diagnostics`. Проверены определение, внутренний вызов из `build_fill001_capture()` и тестовый вызов — все используют три аргумента: shape_id, before_png, after_png.
- GitHub Actions [41579136690](https://github.com/Kiddos19882/AutoDraw/actions/runs/41579136690) привязан к этой ветке и code SHA `b4cc45a80231e6bad2f878b2a5a2f16b48b9d68b`; все обязательные jobs завершились SUCCESS.
- Preparation/G3 log: `754 passed, 24 warnings, 82 subtests passed`; GitHub Actions выполнил полный `pytest -q -ra tests` в `source/preparation`, включая FILL-001 matrix/capture adapter regression tests.
- Windows portable build прошёл; лог подтверждает запуск `release/AutoDrawPortable/AutoDraw.exe`, процесс оставался активным 10 секунд, portable layout и startup smoke-test пройдены. Artifact ID: `13204044319`.
- Дополнительно успешны Game Monitor/Bridge, Application integration, Executor regression и INT-006 audit. Optional algorithm benchmarks были skipped.
- Локальный pytest в текущем runtime не запускался; подтверждение получено из GitHub Actions. Runtime binding к Bridge/executor и Windows preflight реальных FILL-001 PNG не входят в шаг 1 и остаются следующими gates.
- Исходный код в этом шаге не изменялся; `master` не изменялся. Статусы временного плана, TASKS, ROADMAP и PROJECT_STATUS синхронизированы.
- Синхронизированы статусы в `CHALK_FILL_AREA_RADIUS_EFFICIENCY_PLAN_2026-11-03.md` и `CHALK_FILL001_HARNESS_DESIGN_2026-11-03.md`; прежние записи о pending CI сохранены как исторические snapshots.

## 2026-11-03 — временный план дальнейших работ FILL-001

- Создан `CHALK_FILL001_TEMPORARY_PLAN_2026-11-03.md` с пятью последовательными шагами: regression/CI gate; привязка к фактическим Bridge и executor journals; независимая PNG-проверка и Windows preflight; 45 live captures; анализ exact CHALK и выбор стратегии заливки.
- Зафиксированы критерии завершения, блокировки live captures до прохождения шагов 1–3 и запрет считать synthetic fixtures реальными измерениями.
- План помечен временным и обязательным к сохранению до выполнения всех пяти шагов или отдельного решения пользователя.
- Последний проверенный кодовый HEAD на момент планирования: `b4cc45a`; CI для него в рамках этой записи не подтверждён.

## 2026-11-03 — FILL-001 raster prototype review

- На frozen masks проверены два офлайн подхода: простой H/V grid и eroded-contour + interior scanlines.
- Grid сохраняет zero leakage, но не достигает coverage ≥99% для части радиусов 20/30. Contour approach повышает coverage, но оставляет небольшой leakage для radius 10/30 и недозаполнение границы при radius 1.
- Это OpenCV simulation, не game renderer measurement; ни один вариант не интегрирован и не разрешён к исполнению.
- Следующий шаг — boundary-aware centerline planner, который одновременно проходит coverage ≥99% и leakage=0 на всех поддерживаемых cells.

## 2026-11-03 — FILL-001 frozen masks implementation

- Создан `source/preparation/chalk_fill_experiment.py`: три deterministic bool masks, canvas 460×240 logical board pixels, frozen SHA-256.
- Площади: rectangle 44 653 px, wide_irregular 45 159 px, narrow_irregular 44 879 px; разброс max/min 1,133% (допуск ±5%).
- Добавлен `source/preparation/tests/test_chalk_fill_experiment.py` — 8 тестов. Локальный прогон точной копии исходника и теста: 8 passed.
- Полный GitHub Actions для commits FILL001 пока не подтверждён; fixed-radius DrawingPlan generator и block harness ещё не реализованы. Live запуск запрещён до завершения этих gates.

## 2026-11-03 — FILL-001 technical design review

- Проверены `interior_fill_planner.py`, `outline_first_fill_planner.py`, `brush_footprint_geometry.py` и существующие tests.
- Подтверждено, что существующие planners не обеспечивают single-radius comparison: interior-fill использует mixed brush widths/fallback=1 и max=20; outline-first использует boundary brush=1. Automatic execution у обоих запрещён.
- Принят отдельный дизайн `CHALK_FILL001_HARNESS_DESIGN_2026-11-03.md`: fixed-radius generator, frozen masks, raster simulator с round caps, dynamic expected_strokes в task journal и independent analyzer.
- Критерии не изменены: coverage ≥99%, leakage=0; unsupported cells не исполняются. Код и harness пока не менялись.

## 2026-11-03 — INT006R manual visual audit и закрытие фазы

- Исправление CI packaging в commit `c60b8cf` использует фактический файл `before_clear-board.png`.
- Полный workflow [41563236073](https://github.com/Kiddos19882/AutoDraw/actions/runs/41563236073) завершился SUCCESS; обязательные jobs, независимые анализаторы и Windows portable build прошли.
- Артефакт [autodraw-int006r-visual-review-source](https://github.com/Kiddos19882/AutoDraw/actions/runs/41563236073/artifacts/13198192445) содержит 45 пар before/after PNG и связанные manifests/reports.
- Ручной просмотр 45 пар завершён: все before images пустые, все after images соответствуют планам, размер PNG 581×304, посторонние следы/курсор в рабочей области не обнаружены.
- Зафиксированы quality limits: radius 1 — видимый разрыв верхнего левого соединения D2 polygon; radius 30 — слияние первых трёх коротких деталей D4 (длины 1/2/3 logical px); radius 10 сохраняет их разделение в этой матрице. См. `CHALK_INT006R_VISUAL_AUDIT_2026-11-03.md`.
- INT006R закрыт как завершённая измерительная фаза с ограничениями; FILL-001 остаётся следующим активным направлением. Production estimator/defaults, frozen model и master не менялись.

# Журнал работ AutoDraw

## 2026-11-03 — INT006R live data audit и план FILL-001

**Live data commit:** [138c9fbe](https://github.com/Kiddos19882/AutoDraw/commit/138c9fbeaf612a86819f7ff9ea0db7bb1fe4296a)  
**Series:** `chalk-20261103-030837-a20df5`  
**Block:** `a8e0b9ec87984f60aa294910d366e987`

- Проверен durable journal: 45/45 задач completed, матрица D1–D5 × radius 1/10/30 × 3 повтора, профиль P1 (step=4, delay=5 ms).
- По всем 45 Monitor reports проверены точные pre/post pointCount, расход, sampled per-stroke delta, requested/observed radius и integrity counters.
- Во всех проверенных reports `sampled_point_delta_total` совпал с exact CHALK; dropped events, Monitor errors, Bridge send failures и sequence gaps — 0.
- Средний расход: radius 1 — 67.40 (total 1011); radius 10 — 67.67 (total 1015); radius 30 — 67.80 (total 1017). Полная таблица: [INT006R live report](CHALK_INT006R_LIVE_RESULTS_2026-11-03.md).
- Не объявляли visual quality gate закрытым: требуется ручной просмотр всех 45 пар PNG и официальный CLI analyzer на реальном bundle.
- Обновлены PROJECT_STATUS, TASKS, ROADMAP, CHANGELOG и docs index.
- Подготовлен план FILL-001: три формы областей × пять радиусов × три повтора; основной показатель — качественно покрытая площадь на exact CHALK.
- Обнаружено ограничение существующего `interior_fill_planner.py`: `max_brush_value <= 20`, strokes не готовы к automatic execution; семантика radius vs footprint width требует проверки.
- Production estimator, frozen INT-006 model, executor/sampling defaults и `master` не менялись.
- В `.github/workflows/geometry-tests.yml` добавлен запуск `chalk_int006r_validation.py` на реальном committed journal/capture bundle с отдельным artifact `autodraw-int006r-live-validation`. Workflow [41559932955](https://github.com/Kiddos19882/AutoDraw/actions/runs/41559932955) завершился SUCCESS: 45 accepted, 0 missing/rejected, PNG evidence complete.
- Добавлена упаковка 45 пар PNG для ручной визуальной проверки. Первый запуск [41561422754](https://github.com/Kiddos19882/AutoDraw/actions/runs/41561422754) подтвердил успешность всех анализаторов, но packaging step упал из-за неверного имени исходного файла: в captures используется `before_clear-board.png`, а не `before_draw-board.png`. Имя исправлено; повторный CI [41563236073](https://github.com/Kiddos19882/AutoDraw/actions/runs/41563236073) поставлен в очередь.
- В отчёте обнаружено противоречие: P1=4/5 корректно выводился отдельно, но `other_executor_parameters` включал устаревшие значения 2/10. Исправлены analyzer и regression test; analyzer job в [41560787871](https://github.com/Kiddos19882/AutoDraw/actions/runs/41560787871) прошёл SUCCESS и подтвердил корректный P1 report; полный run отменён при запуске следующего workflow. Текущий re-run [41561422754](https://github.com/Kiddos19882/AutoDraw/actions/runs/41561422754) повторяет полный CI и формирует artifact с 90 board PNG.
- Статически проверен engine bundle из master commit `bd8815c`: CHALK считается по числу `atom.points`; radius передаётся в `lineStyle` как ширина линии. Создан [engine analysis](CHALK_GAME_ENGINE_POINT_COST_AND_BRUSH_WIDTH_2026-11-03.md).
- Подтверждено, что `testImages/images.png` уже есть в обеих ветках с одинаковым blob SHA; engine bundle пока только в master. Merge/rebase не выполнялся.


## 2026-11-03 — INT006R full software gate PASS

**CI:** [run 41540054975](https://github.com/Kiddos19882/AutoDraw/actions/runs/41540054975)  
**Проверенный code HEAD:** `28b56a97255b57b50072ba973533ce349c706bd1`  
**Результат:** SUCCESS.

- Preparation/G3: 682 passed, 82 subtests passed, 24 warnings.
- Application integration, Executor regression и Game Monitor/Bridge — success.
- INT-006 pixel-level PNG geometry audit — success.
- Windows portable build и startup smoke-test — success; portable artifact upload завершён.
- Новый положительный INT006R analyzer test принял synthetic 45/45 комплект, проверив journal/task/experiment/run binding, exact CHALK, per-stroke breakdown и читаемые before/after PNG.
- Отрицательные regression tests проверяют неподдерживаемые радиусы, bool/float радиусы, P1-only contract, mismatch requested brush, tampered journal radius и duplicate cells.

**Границы:** CI подтверждает программную готовность INT006R, но не влияние радиуса на фактический CHALK. Live captures не выполнялись; visual quality gate остаётся pending manual review. Следующий шаг — локальный Windows preflight по `CHALK_INT006R_LIVE_PREFLIGHT_AND_VISUAL_AUDIT_2026-11-03.md`. Production estimator, frozen INT-006 artifact, executor defaults, sampling defaults и `master` не менялись.


## 2026-11-03 — реализация INT006R radius × geometry harness

**Ветка:** `feature/image-geometry-optimization`  
**Основание:** разрешение пользователя на продолжение проекта и все необходимые действия.

- В `chalk_experiment_matrix.py` добавлены отдельные D1–D5R scenario IDs, expected stroke counts, допустимые радиусы 1/10/30 и строгий sampling P1 (step=4, delay=5 ms). Обычные фазы и frozen INT-006 radius=10 contract сохранены.
- В `chalk_test_blocks.py` добавлен отдельный детерминированный 45-cell block: пять геометрий × три радиуса × три повтора. Journal validator проверяет полный набор ячеек, уникальность task/order IDs, радиус, P1, отсутствие prediction artifact и запрет смешивания серий.
- В Brush Test добавлены отдельные D1–D5R сценарии; радиус для каждой задачи устанавливается из task journal. Ручной запуск этих сценариев вне полного блока заблокирован.
- В `integrated_app.py` добавлен fail-closed executor handoff: только INT006R, D1–D5R, radius 1/10/30 и P1; requested brush должен совпадать с task metadata.
- Добавлен независимый `chalk_int006r_validation.py`, который не загружает frozen INT-006 model и анализирует exact CHALK, journal/task/experiment/run binding, полноту 45 captures, разброс по геометрии/радиусу и разницу относительно radius=10.
- Добавлены unit tests `test_chalk_int006r_validation.py` и интеграционный тест executor handoff в `test_unified_app.py`.
- Обновлены TASKS, PROJECT_STATUS, план INT006R и индексные документы.

**Границы:** кодовая реализация добавлена, но CI для нового HEAD ещё не подтверждён. Live captures не запускались. Production estimator, frozen INT-006 artifact, executor defaults, sampling defaults и `master` не менялись. Следующий gate — полный CI, включая Windows portable build/startup smoke-test.


## 2026-10-31 — создание базового комплекта документации

- Проверено дерево репозитория и основные конфигурационные файлы.
- Создан индекс документации, архитектурная карта, каталог компонентов, описание данных и инструкция разработки.
- Созданы файлы управления проектом.
- Обновлён Stage20 README ссылкой на документацию.
- Проверены относительные ссылки новых документов.
- Изменения ограничены Markdown-файлами; тесты и приложение не запускались.

## 2026-10-31 — отмена аналитических этапов и расширение справочника

**Исходный HEAD:** aa285b0b3a2543b1fd20b7963774862626713d00  
**Рабочая ветка:** feature/image-geometry-optimization

### Отмена плана
- По прямому указанию пользователя отменены аналитические этапы 7–10.
- PROJECT_ANALYSIS_PLAN_10_STAGES.md переведён в архивный статус с явным уведомлением об отмене.
- PROJECT_STATUS.md, ROADMAP.md, TASKS.md, DECISIONS.md и CHANGELOG.md обновлены.
- Этапы 7–10 помечены CANCELLED, они не являются активными задачами.

### Документирование
- Добавлен DATA_FORMATS_AND_MODELS.md: общие Point, Stroke, DrawingPlan и portable-формат .autodraw.
- Добавлен MODULE_REFERENCE.md: структурный справочник preparation, executor, общих пакетов и Game Monitor.
- Обновлены индекс, roadmap и реестр задач.
- DOC-007 и DOC-008 закрыты.

### Границы
- Изменялись только Markdown-файлы.
- Исходный код, тесты, workflows, зависимости и данные не изменялись.
- Программные тесты, запуск приложения и браузерные проверки не выполнялись.

## 2026-10-31 — справочник интерфейсов preparation (первая редакция)

- Получено дерево исходников preparation текущей ветки; обнаружено 75 Python-файлов, включая тесты.
- По исходникам составлен первичный перечень функций, классов и UI-компонентов; создан PREPARATION_API_REFERENCE.md.
- Добавлена ссылка в индекс документации.
- DOC-009 оставлена IN_PROGRESS: часть длинных сигнатур и контрактов UI требует дальнейшей точной инвентаризации.
- Изменялись только Markdown-файлы. Приложение и тесты не запускались.

## 2026-10-31 — детализация API preparation

- Уточнены полные сигнатуры дополнительных функций планирования, геометрии, ресурсных оценок и калибровки.
- Добавлен отдельный раздел `profile_manager.py`: dataclass профилей, методы сериализации и интерфейс `ProfileStore`.
- Уточнены границы: compatibility-модели preparation реэкспортируют канонические сущности из `geometry_models`.
- DOC-009 остаётся IN_PROGRESS: требуется завершить точную инвентаризацию оставшихся функций, UI-методов и интеграционных вызовов.
- Изменения ограничены Markdown; код и тесты не изменялись и не запускались.

## 2026-10-31 — инвентаризация UI preparation

**Commit:** 7074bdce956f9bb1f71bf52a6fa1634ae77f49a8  
**Изменённые файлы:**
- AutoDraw_Stage20/docs/PREPARATION_API_REFERENCE.md

**Что сделано:**
- Добавлены сигнатуры конструкторов и методов UI-классов калибровки кисти, тестирования кисти, scanline-планирования, обнаружения и квантования палитры, тестов лимита краски и Stage 13 Workbench.
- Зафиксированы внешние callback-зависимости, передаваемые через конструкторы.
- Внутренние обработчики перечислены отдельно от методов подключения компонентов.
- Уточнена формулировка о степени детализации UI API.

**Проверки:**
- Сверены объявления классов и методов непосредственно с исходниками текущей ветки.
- Приложение и тесты не запускались; live/browser-проверки не выполнялись.

**Ограничения / продолжение:**
- DOC-009 остаётся IN_PROGRESS до полной сверки экспортов и сигнатур оставшихся модулей.
- DOC-011 остаётся TODO: требуется сводная карта UI и интеграционных точек по всему проекту.
- Изменения исходного кода не выполнялись.

## 2026-10-31 — документирование профилей и форматов планов

**Исходный HEAD:** fe0bd0e42937d07b8c998d1ef907e03faa6ab651  
**Рабочая ветка:** feature/image-geometry-optimization

**Добавлен документ:** `AutoDraw_Stage20/docs/DATA_FORMATS_AND_PROFILES.md`.

**Что сделано:**
- Зафиксированы структуры реестра и профилей рабочей области.
- Описаны документ палитры и именованный профиль палитры.
- Описан профиль калибровки кисти и шкалы краски.
- Документированы основные структуры scanline-, geometry-, adaptive-brush и multi-board планов.
- Добавлены связи между форматами и ссылки на справочник общих моделей.
- Обновлены индекс, roadmap, реестр задач и статус проекта.

**Проверки:**
- Структуры сверены по определениям и сериализуемым полям исходников `source/preparation/`.
- Проверка ограничена чтением исходников и документации; приложение и тесты не запускались.

**Ограничения / продолжение:**
- DOC-012 остаётся IN_PROGRESS: требуется документировать результаты лабораторных запусков, experiment manifests и экспорт Game Monitor.
- DOC-009 остаётся IN_PROGRESS; его оставшиеся сигнатуры не объявляются завершёнными.
- Изменялись только Markdown-файлы; исходный код, тесты, конфигурация и данные не изменялись.

## 2026-10-31 — документирование лабораторных форматов

**Изменённый документ:** `AutoDraw_Stage20/docs/DATA_FORMATS_AND_PROFILES.md`.

**Что сделано:**
- Добавлена структура журнала наблюдений paint-limit: корневой документ, массив records и поля отдельной записи.
- Описан JSON-снимок BrushExperimentState и его фазы/статусы.
- Зафиксированы структуры словарей визуальных измерений из brush_experiment_capture.py.
- Отделены результаты визуальных сравнений от внутреннего игрового счётчика.
- Зафиксирована граница документирования Game Monitor: полная JSON-схема экспорта требует отдельной сверки с реализацией.

**Проверки:**
- Поля сверены с функциями сериализации/создания записей и возвращаемыми структурами исходников.
- Код и тесты не запускались; файлы снимков и пользовательские данные не изменялись.

**Продолжение:**
- DOC-012 остаётся IN_PROGRESS до документирования точной схемы экспорта Game Monitor.
- После этого можно перейти к DOC-010 — публичным интерфейсам executor.

## 2026-10-31 — документирование экспорта Game Monitor

**Изменённый документ:** `AutoDraw_Stage20/docs/DATA_FORMATS_AND_PROFILES.md`.

**Что сделано:**
- По `game_monitor.js` версии 0.1.2 зафиксированы поля корневого JSON-экспорта.
- Описаны поля снимка доски, общие поля событий и структура ошибок.
- Зафиксировано имя скачиваемого JSON-файла и область действия маскирования query-параметров.
- Обновлены индекс/статус/roadmap/реестр задач и changelog.

**Проверки:**
- Сверены функции `exportData()`, `status()`, `download()` и вспомогательные структуры текущего JavaScript-файла.
- Monitor не запускался; экспорт в браузере не создавался и не проверялся.

**Продолжение:**
- DOC-012 остаётся IN_PROGRESS до сверки форматов калибровочных записей и остальных сохранённых результатов.
- Код и пользовательские данные не изменялись.

## 2026-10-31 — завершение справочника профилей и результатов

**Изменённый документ:** `AutoDraw_Stage20/docs/DATA_FORMATS_AND_PROFILES.md`.

**Что сделано:**
- Документированы входной формат и отчёт game point calibration.
- Описаны структура профиля ресурса доски и возвращаемые поля моделей расхода/квоты точек.
- Зафиксированы различия между оценкой эквивалентного расхода и оценкой квоты точек.
- Задача DOC-012 переведена в DONE; roadmap и статус проекта обновлены.

**Проверки:**
- Сверены поля входных документов, выходных словарей и константы версий соответствующих модулей.
- Не выполнялись калибровочные серии, запуск игры, браузера или тестов.
- В рамках DOC-012 изменялись только Markdown-файлы.

**Продолжение:**
- Следующая незавершённая задача справочника исходников — DOC-009 (полные публичные интерфейсы preparation).
- DOC-010 (executor), DOC-011 (общая карта UI/integration points) и DOC-013 (карта импортов) остаются отдельными задачами.

## 2026-10-31 — карта UI и интеграционных точек

**Добавлен документ:** `AutoDraw_Stage20/docs/UI_INTEGRATION_MAP.md`.

**Что сделано:**
- Зафиксированы восемь вкладок единого приложения и создаваемые UI-компоненты.
- Описаны внешние callback-зависимости и назначаемые после создания связи executor.
- Документирована синхронизация области рисования с Workbench, quantizer и color-plan UI.
- Описаны маршруты передачи одноцветных, цветных, brush-test и paint-limit планов.
- Зафиксированы runtime-файлы и пути передачи профиля палитры/калибровки.
- DOC-011 переведена в DONE; обновлены индекс, roadmap, реестр задач и changelog.

**Проверки:**
- Все связи сверены с местами создания и передачи callback в `integrated_app.py`.
- Приложение и тесты не запускались; проверка ограничена чтением исходника и документации.

**Границы:**
- Вызовы приватных методов executor отмечены как фактические интеграционные точки, а не публичная гарантия совместимости.
- Исходный код и конфигурация не изменялись.

## 2026-10-31 — уточнение API и brush experiment manifest

**Изменённые документы:**
- `AutoDraw_Stage20/docs/PREPARATION_API_REFERENCE.md`
- `AutoDraw_Stage20/docs/DATA_FORMATS_AND_PROFILES.md`

**Что сделано:**
- Устранён оставшийся сокращённый placeholder в сигнатуре `build_brush_test_record()`; параметры сверены с объявлением исходника.
- Уточнены объявления конструкторов UI-классов там, где в документации не был указан `self`.
- Обновлены пояснения о сигнатурах без type annotations: типы не додумываются.
- Описаны `autodraw_brush_behavior_observation` и структура файла `experiment.json`, записываемого UI теста кистей.

**Проверки:**
- Сверены `build_brush_test_record()`, `BrushBehaviorTestTab.__init__()` и `_write_experiment_manifest()` непосредственно с исходником.
- Приложение и тесты не запускались.

**Продолжение:**
- DOC-009 остаётся IN_PROGRESS до сверки всех экспортов preparation.
- DOC-010 и DOC-013 остаются TODO.

## 2026-10-31 — завершение инвентаризации API preparation

**Документ:** `AutoDraw_Stage20/docs/PREPARATION_API_REFERENCE.md`.

**Что сделано:**
- Сопоставлен раздел preparation в MODULE_REFERENCE.md со справочником API.
- Проверено присутствие всех 40 перечисленных модулей preparation в PREPARATION_API_REFERENCE.md.
- Устранён оставшийся сокращённый placeholder сигнатуры `build_brush_test_record()`; неаннотированные параметры оставлены без выдуманных типов.
- Обновлены TASKS, ROADMAP и PROJECT_STATUS: DOC-009 переведена в DONE.

**Проверки:**
- Сопоставление выполнено по именам модулей и объявлениям в исходниках текущей ветки.
- Это структурная сверка документации; приложение и тесты не запускались.

**Продолжение:**
- Следующая задача справочника исходников — DOC-010: публичные интерфейсы executor.
- DOC-013: карта импортов остаётся отдельной задачей.

## 2026-10-31 — начало справочника API executor

**Добавлен документ:** `AutoDraw_Stage20/docs/EXECUTOR_API_REFERENCE.md`.

**Что сделано:**
- Зафиксированы интерфейсы этапов executor и актуального Stage6App.
- Описан контракт MouseExecutor, конфигурация и ExecutionSummary.
- Описаны преобразование цветных/geometry/adaptive планов и hooks выбора палитры/кисти.
- Добавлены интерфейсы трансформации DrawingPlan, отчётов исполнения и path planning.
- Добавлены ссылки на общие геометрические модели и общий image-processing pipeline.
- Обновлены индекс, TASKS, ROADMAP и PROJECT_STATUS; DOC-010 переведена в IN_PROGRESS.

**Проверки:**
- Сигнатуры сверены по объявлениям исходников Stage6, mouse_executor, color_plan_execution, plan_transform, execution_diagnostics и path_planning.
- Приложение, тесты и управление мышью не запускались.

**Продолжение:**
- Проверить оставшиеся executor-модули, экспортные списки и legacy stage entrypoints.
- DOC-010 остаётся IN_PROGRESS.

## 2026-10-31 — дополнение форматов отчётов executor

**Изменённый документ:** `AutoDraw_Stage20/docs/DATA_FORMATS_AND_PROFILES.md`.

**Что сделано:**
- Описана структура `ExecutionSummary.to_dict()`.
- Добавлена схема execution report версии 2.
- Зафиксированы дополнительные поля цветного исполнения и adaptive brush report.
- Описано имя файла, формируемого `write_execution_report()`.

**Проверки:**
- Поля сверены с `ExecutionSummary.to_dict()`, `build_execution_report()`, `ColorPlanExecutionHooks.to_report()` и `write_execution_report()`.
- Исполнитель не запускался, реальные отчёты не создавались.

## 2026-10-31 — завершение инвентаризации API executor

**Документ:** `AutoDraw_Stage20/docs/EXECUTOR_API_REFERENCE.md`.

**Что сделано:**
- Добавлены сигнатуры и контракты Stage 1–6, включая актуальный Stage6App.
- Описаны MouseExecutor, конфигурация, сводка исполнения и callbacks.
- Описаны цветное исполнение, palette hooks, brush slider, преобразование планов и диагностика.
- Описаны контурный planner, stroke optimizer и тестовая геометрия.
- Сверено покрытие с разделом executor в MODULE_REFERENCE.md: все 13 перечисленных модулей представлены.
- DOC-010 переведена в DONE; обновлены TASKS, ROADMAP и PROJECT_STATUS.

**Проверки:**
- Проверка покрытия выполнена сравнением списка модулей справочника и имён модулей в API-документе.
- Сигнатуры основных публичных точек сверены с исходниками.
- Приложение и тесты не запускались.

**Продолжение:**
- Следующая организационная задача — DOC-013: карта импортов и направлений межмодульных зависимостей.

## 2026-10-31 — начало карты импортов

**Добавлен документ:** `AutoDraw_Stage20/docs/DEPENDENCY_MAP.md`.

**Что сделано:**
- Зафиксированы точки входа единого приложения и legacy Stage 1–6.
- Сведены прямые импорты integrated_app.py и ключевых UI-компонентов preparation.
- Сведены основные импорты Stage6, MouseExecutor, color-plan hooks и path planning.
- Описаны общие геометрические модели и image-processing adapters.
- Добавлена диаграмма основных зависимостей.
- DOC-013 переведена в IN_PROGRESS; обновлены индекс, roadmap, TASKS и PROJECT_STATUS.

**Проверки:**
- Импортные связи сверены по import/from-import statements выбранных точек входа и основных интеграционных модулей.
- Карта пока не претендует на полный перечень импортов всех модулей и тестов.
- Приложение и тесты не запускались.

**Продолжение:**
- Сверить оставшиеся preparation/executor-модули, compatibility-модули и тестовые импорты.
- DOC-013 остаётся IN_PROGRESS.

## 2026-10-31 — каталог пользовательского хранилища

**Добавлен документ:** `AutoDraw_Stage20/docs/FILE_STORAGE_CATALOG.md`.

**Что сделано:**
- Сведены каталоги профилей, палитр, проектов, результатов, runtime и логов из `configure_environment()`.
- Документированы фиксированные runtime-файлы передачи одноцветных, цветных и тестовых планов.
- Описаны каталоги результатов преобразования палитры, цветных планов и тестов лимита краски.
- Зафиксированы `observations.json`, каталоги brush experiments, эталон доски, phase PNG и experiment manifests.
- Добавлена структура ZIP-контейнера `.autodraw` и правила резервного копирования.
- Уточнён индекс документации; устранена некорректная строка-разделитель в README.md.
- Обновлены TASKS, ROADMAP и PROJECT_STATUS.

**Проверки:**
- Пути сверены с `integrated_app.py`, `autodraw_project.py`, `profile_manager.py`, `palette_profiles.py`, `paint_limit_test.py`, `brush_behavior_test_ui.py` и `analyze_brush_experiment_series.py`.
- Отдельно отмечено, что Monitor exports хранятся вне каталога brush experiment и не всегда связаны с manifest.
- Приложение, UI, браузер и тесты не запускались.
- Код не изменялся.

**Продолжение:**
- DOC-013: сверка оставшихся import statements и тестовых зависимостей.
- DOC-014: проверка относительных Markdown-ссылок и целевых файлов.

## 2026-10-31 — полная матрица импортов production-модулей

**Изменённый документ:** `AutoDraw_Stage20/docs/DEPENDENCY_MAP.md`.

**Что сделано:**
- Проверены import/from-import statements всех 40 модулей preparation из MODULE_REFERENCE.
- Проверены import/from-import statements всех 13 модулей executor из MODULE_REFERENCE.
- Добавлена таблица прямых внутрипроектных импортов по каждому production-модулю.
- Уточнены канонические пакеты `geometry_models` и `shared_image_processing`, а также совместимые adapters.
- Зафиксирована граница: тестовые модули и вспомогательные скрипты ещё не инвентаризированы.
- Обновлены TASKS, ROADMAP и PROJECT_STATUS; DOC-013 остаётся IN_PROGRESS до отдельной карты тестов.

**Проверки:**
- Сопоставлены списки модулей из MODULE_REFERENCE.md с файлами, из которых извлекались import statements.
- В таблицу включены только прямые внутрипроектные импорты; стандартная библиотека и внешние библиотеки исключены.
- Код и тесты не запускались, исходники не менялись.

## 2026-10-31 — уточнение границ каталогов данных

**Изменённый документ:** `AutoDraw_Stage20/docs/CONFIGURATION_AND_DATA.md`.

**Что сделано:**
- Добавлена ссылка на FILE_STORAGE_CATALOG.md как подробный источник истины по файловым путям.
- Разделены каталоги, задаваемые `configure_environment()`, и дополнительные исторические/экспериментальные каталоги.
- Отмечено, что `data/test_monitor/` и `data/calibration/` не входят в словарь путей основного приложения.

**Проверки:**
- Сверено с `integrated_app.py: configure_environment()`.
- Исходники не изменялись.

## 2026-10-31 — карта тестов и CI

**Добавлен документ:** `AutoDraw_Stage20/docs/TESTS_AND_CI_MAP.md`.

**Что сделано:**
- Разделены тестовые слои Preparation, Executor, интеграционные/UI, Game Monitor, diagnostics/benchmarks и portable build.
- Документированы пять ключевых algorithmic tests, import-resolution diagnostics, Stage 7 validator и unified-app UI regression.
- Зафиксированы прямые импорты проверенных тестовых файлов.
- Перенесена в документ структура трёх CI jobs: geometry-tests, executor-tests, windows-build-smoke.
- Перечислены workflow benchmark/diagnostic scripts и назначение их артефактов.
- Отдельно обозначено, что workflow configuration не доказывает успешный запуск, а подготовка документа не включала запуск тестов.
- Обновлён индекс docs, TASKS, ROADMAP и PROJECT_STATUS.

**Граница выполненной работы:**
- Проверены исходники пяти основных test modules, `test_import_resolution_diagnostics.py`, `test_stage7_validator_rules.py`, `test_unified_app.py` и workflow `.github/workflows/geometry-tests.yml`.
- Полная построчная матрица импортов всех файлов из `source/preparation/tests/`, `source/executor/tests/` и `tests/` остаётся отдельной задачей.
- Код не изменялся; тесты, UI, benchmarks и сборка не запускались.

## 2026-10-31 — проверка ссылок основного индекса

**Проверен документ:** `AutoDraw_Stage20/docs/README.md`.

**Результат:**
- Проверены все локальные цели ссылок основного индекса, включая документы в `docs/`, корневые документы Stage20 и README Game Monitor.
- Все проверенные целевые файлы существуют в ветке `feature/image-geometry-optimization`.
- Проверка подтверждает наличие файлов, но не проверяет корректность якорей заголовков и все перекрёстные ссылки внутри каждого документа.
- DOC-014 остаётся открытой до полной проверки Markdown-ссылок по всему каталогу документации.

## Шаблон записи

~~~markdown
## YYYY-MM-DD — название работы

**Commit:** SHA или не создан  
**Изменённые файлы:**
- path/to/file.md

**Что сделано:**
- ...

**Проверки:**
- ...

**Ограничения / продолжение:**
- ...
~~~


## 2026-10-31 — расширение матрицы прямых импортов тестов

**Изменённые документы:**
- `AutoDraw_Stage20/docs/TESTS_AND_CI_MAP.md`
- `AutoDraw_Stage20/docs/TASKS.md`

**Что сделано:**
- Прочитаны непосредственно 20 дополнительных тестовых файлов из Preparation, Executor и корневого `tests/`.
- В TESTS_AND_CI_MAP добавлены таблицы прямых внутрипроектных импортов для каждого из этих файлов.
- Отдельно отмечены локальные импорты внутри функций и граница между прямыми и транзитивными зависимостями.
- DOC-013 остаётся IN_PROGRESS: полный состав discovery-каталогов и оставшиеся тестовые файлы ещё предстоит инвентаризировать.

**Проверки:**
- Импортные строки извлечены из содержимого файлов в ветке `feature/image-geometry-optimization`.
- Тесты, UI, benchmarks и сборка не запускались.
- Исходный код не изменялся.

**Продолжение:**
- Завершить перечень всех тестовых файлов в трёх каталогах и добавить импорты оставшихся файлов.
- Затем перейти к DOC-014: проверке относительных Markdown-ссылок и якорей.


## 2026-10-31 — дополнительная инвентаризация тестов Preparation

**Изменённые документы:** `TESTS_AND_CI_MAP.md`, `TASKS.md`.

**Что сделано:**
- Добавлены прямые внутрипроектные импорты ещё пяти тестовых файлов: paint budget optimizer, game point calibration, interior fill, geometry budget optimizer и outline-first fill.
- Общее число дополнительно проверенных тестовых файлов в матрице достигло 25.

**Проверки:**
- Импортные строки прочитаны непосредственно из файлов ветки `feature/image-geometry-optimization`.
- Тесты и приложение не запускались; исходники не менялись.

**Продолжение:**
- Продолжить проверку оставшихся тестов и полного состава каталогов.


## 2026-10-31 — расширение матрицы тестовых импортов до 39 файлов

**Изменённые документы:**
- `AutoDraw_Stage20/docs/TESTS_AND_CI_MAP.md`
- `AutoDraw_Stage20/docs/TASKS.md`
- `AutoDraw_Stage20/docs/PROJECT_STATUS.md`

**Что сделано:**
- Поиск по репозиторию выявил дополнительные тесты Preparation и Executor, не вошедшие в предыдущую выборку.
- Проверены прямые import/from-import statements ещё 14 тестовых файлов.
- В матрицу внесены импорты brush calibration/workflow, quota integration, footprint geometry, benchmark, engine calibration, experiment capture, geometry adapter, brush UI, end-to-end optimizer и color-plan execution.
- Отдельно отмечен helper `source/executor/path_planning/test_shape.py`, используемый тестом DrawingPlan, но не считаемый самостоятельным discovery-тестом.
- Общее количество файлов с зафиксированными прямыми импортами доведено до 39.

**Проверки:**
- Файлы прочитаны непосредственно в ветке `feature/image-geometry-optimization`; импортные строки сверены по содержимому.
- Не выполнялись тесты, UI, benchmarks или сборка.
- Исходный код не изменялся.

**Продолжение:**
- Необходимо завершить инвентаризацию полного набора тестов, включая точное сопоставление discovery-каталогов с файлами и проверку возможных тестовых модулей, не попавших в поисковую выдачу.
- После этого завершить DOC-013 и перейти к DOC-014.


## 2026-10-31 — завершение матрицы тестовых импортов

**Изменённые документы:**
- `AutoDraw_Stage20/docs/TESTS_AND_CI_MAP.md`
- `AutoDraw_Stage20/docs/TASKS.md`
- `AutoDraw_Stage20/docs/PROJECT_STATUS.md`
- `AutoDraw_Stage20/docs/ROADMAP.md`

**Что сделано:**
- GitHub Code Search по `test_` вернул 46 уникальных файлов `test_*.py` в трёх каталогах: preparation, executor и корневом tests.
- Все 46 файлов прочитаны; прямые внутрипроектные импорты внесены в TESTS_AND_CI_MAP.
- Вспомогательный `source/executor/path_planning/test_shape.py` отдельно отмечен как helper, а не самостоятельный discovery-тест.
- DOC-013 переведена в DONE; TASKS, PROJECT_STATUS и ROADMAP синхронизированы.

**Проверки:**
- Число уникальных файлов `test_*.py` в поисковой выдаче — 46; все они отражены в таблицах документа.
- Тесты и приложение не запускались; исходный код не менялся.

## 2026-10-31 — проверка относительных Markdown-ссылок

**Изменённые документы:**
- `AutoDraw_Stage20/docs/TASKS.md`
- `AutoDraw_Stage20/docs/PROJECT_STATUS.md`
- `AutoDraw_Stage20/docs/ROADMAP.md`

**Что сделано:**
- Проверены локальные Markdown-ссылки в 35 документах: 20 документов основного каталога docs и 13 связанных/исторических документов Stage20.
- Проверены 67 относительных ссылок; все целевые файлы существуют в ветке `feature/image-geometry-optimization`.
- В проверенном наборе Markdown-ссылок не обнаружены якорные фрагменты `#...`, поэтому отдельная проверка heading anchors не требовалась.
- Цели основного индекса `docs/README.md` существуют; ссылки из него на архивные документы также разрешаются.
- DOC-014 переведена в DONE.

**Ограничения:**
- Проверка охватывала основной комплект документации, связанные с ним корневые и исторические документы Stage20; это не утверждение о проверке каждого Markdown-файла во всём репозитории за пределами указанного набора.
- Тесты, UI, benchmarks и сборка не запускались; исходный код не менялся.

**Продолжение:**
- Выполнить итоговую сверку интерфейсов/путей и проверить состав Git diff перед финальным завершением документационной серии.


## 2026-10-31 — уточнение итогового подсчёта ссылок и файлов тестов

**Документы:** `TESTS_AND_CI_MAP.md`, `TASKS.md`, `ROADMAP.md`, `WORK_LOG.md`.

**Что уточнено:**
- Контрольная выборка содержит ровно 46 уникальных путей `test_*.py`; устранена ошибочная ссылка `tests/test_outline_first_fill_planner.py`, заменена фактическим путём `source/preparation/tests/test_outline_first_fill_planner.py`.
- Исправлена нумерация ограничений в TESTS_AND_CI_MAP.
- Подсчёт проверки ссылок уточнён: 67 относительных ссылок в 35 документах (20 основных docs и 15 связанных/исторических документов Stage20).
- Все проверенные относительные цели существуют; в ссылках нет фрагментов заголовков.

**Границы:** тесты, приложение, UI, benchmarks и сборка не запускались; исходный код не изменялся.


## 2026-10-31 — сверка API и файлового хранилища с исходниками

**Изменённые документы:**
- `AutoDraw_Stage20/docs/PREPARATION_API_REFERENCE.md`
- `AutoDraw_Stage20/docs/TASKS.md`
- `AutoDraw_Stage20/docs/PROJECT_STATUS.md`
- `AutoDraw_Stage20/docs/ROADMAP.md`
- `AutoDraw_Stage20/docs/WORK_LOG.md`
- `AutoDraw_Stage20/docs/CHANGELOG.md`

**Что проверено:**
- Сопоставлены объявления классов и функций всех 40 модулей preparation, перечисленных в API-справочнике, с текущими исходниками.
- Сопоставлены объявления 13 модулей executor, включая Stage 1–6, MouseExecutor, цветное исполнение, диагностику, преобразование планов, планировщики контуров/штрихов и адаптер image processing.
- Проверены общие геометрические модели `Point`, `Stroke`, `DrawingPlan`, их экспорт из `geometry_models` и общий image-processing API.
- Проверены основные внешние методы UI-компонентов preparation и Stage6, используемые интеграционным приложением.
- Каталог FILE_STORAGE_CATALOG.md сопоставлен с `integrated_app.py: configure_environment()`, передачей runtime-планов и аргументами каталогов, передаваемыми UI-компонентам.
- Исправлена повторяющаяся нумерация раздела 6 в PREPARATION_API_REFERENCE.md; последующие разделы перенумерованы последовательно.

**Результат:**
- В проверенных объявлениях модулей не выявлены расхождения, требующие изменения описания API.
- Подтверждённые базовые каталоги, runtime-файлы и каталоги результатов соответствуют конфигурации приложения; отдельные исторические/экспериментальные пути остаются явно отделёнными.
- DOC-015 закрыта.

**Ограничения:**
- Это структурная сверка объявлений и ключевых интеграционных сигнатур, а не запуск программы или динамическая проверка контрактов.
- Не запускались приложение, тесты, UI, benchmarks и сборка. Исходный код не изменялся.
- Финальная проверка Git diff выполняется отдельно после синхронизации управляющих документов.


## 2026-10-31 — итоговая проверка Git diff и завершение документационной серии

**Контрольная точка:** `1e2de295dd426e3d54958875989c628db2cd36e5`.

**Проверка:** сравнение контрольной точки с HEAD после DOC-015 показало шесть изменённых файлов, все со статусом modified и расширением `.md`:
- `AutoDraw_Stage20/docs/PREPARATION_API_REFERENCE.md`
- `AutoDraw_Stage20/docs/TASKS.md`
- `AutoDraw_Stage20/docs/PROJECT_STATUS.md`
- `AutoDraw_Stage20/docs/ROADMAP.md`
- `AutoDraw_Stage20/docs/WORK_LOG.md`
- `AutoDraw_Stage20/docs/CHANGELOG.md`

Исходный код, тесты, конфигурация, workflows, зависимости и пользовательские данные в diff отсутствуют. Ветка: `feature/image-geometry-optimization`. Документационная серия DOC-001—DOC-015 завершена; аналитические этапы 7–10 остаются отменёнными.

**HEAD на момент записи:** `30f8b62d922bcd253aba1cbda4b55255ccdbe2f8`. После этой записи будут внесены только завершающие отметки в управляющие Markdown-документы.


## 2026-10-31 — INT-001: статическая инвентаризация расхода CHALK и связки Game Monitor

**Рабочая ветка:** `feature/image-geometry-optimization`  
**Контрольный HEAD до записи:** `b5f65d0df8b7208027f9b0fb46f417790c82aa57`

**Что исследовано:**
- `brush_test_workflow.py`, `brush_behavior_test_ui.py`, `brush_experiment_capture.py`;
- `source/game_monitor/game_monitor.js` версии 0.1.2 и README;
- клиентская механика `BoardPane` из имеющегося source scan и проектных материалов;
- `geometry_color_plan.py`, `multi_board_splitter.py`, `paint_limit_test.py`, `brush_planner.py`;
- manifests и сохранённые отчёты Game Monitor в текущем дереве ветки.

**Подтверждённая семантика ресурса:**
- `BoardPane.updateLess()` считает `pointCount` как сумму сохранённых точек в `atom.points`.
- Остаток квоты: `less = max - pointCount`; отображаемый процент: `less / max`.
- Фактический расход изолированного опыта: `C_actual = pointCount_after - pointCount_before`. При неизменном `max` доля использованного ресурса равна `C_actual / max × 100%`.
- Точки добавляются обработчиком `onDrawing()` на `ENTER_FRAME`, если координата допустима и отличается от предыдущей. Поэтому расход связан с принятыми игровыми координатами и кадровым sampling, а не напрямую с длиной пути.
- Радиус кисти задаётся отдельно и не участвует непосредственно в формуле `updateLess()`. При одинаковой последовательности принятых координат прямой расход должен быть одинаковым; влияние размера кисти ожидается через площадь/качество покрытия и число необходимых штрихов.
- Абсолютный `pointCount` нельзя использовать без baseline: очистка в расширенном режиме может добавлять специальную начальную точку. Для опыта нужна дельта.
- Повторные проходы могут добавлять новые точки даже поверх уже окрашенной области; это требует отдельного контролируемого подтверждения.

**Состояние связки:**
- UI умеет вручную импортировать JSON Game Monitor и привязывать путь/сводку к manifest, но автоматического управления жизненным циклом Monitor и автоматической привязки экспорта к experiment ID нет.
- В snapshot/export Monitor отсутствуют прямые поля `max` и `less`; точный остаток CHALK из текущего JSON получить нельзя.
- Сводка UI не агрегирует дельту `pointCount` как основной показатель расхода; обработка fallback-событий и радиусов имеет ограничения.
- Monitor выполняет несколько полных обходов растущего `atom.points` в wrappers/polling. Накладные расходы на FPS не измерены; отсутствие влияния Monitor не доказано.
- В текущих manifests автоматическая привязка отчётов не отражена; семь полных JSON-экспортов существуют отдельно от соответствующих experiment manifests.
- В просмотренных семи экспортированных отчётах указаны `boardDetected=true`, `droppedEvents=0`, `errors=0`; это подтверждает целостность этих сохранённых экспортов, но не доказывает корректность расхода CHALK или отсутствие влияния на игру.

**Ограничения текущего расчёта AutoDraw:**
- `geometry_color_plan.py` использует длину полилиний, дополнительную стоимость отдельных пикселей и фиксированный overhead на штрих в условных px-equivalent.
- Эта оценка не эквивалентна игровому CHALK и не должна называться точным прогнозом квоты.
- `multi_board_splitter.py` использует эту геометрическую оценку; текущие paint-limit проверки также не измеряют прямую дельту игрового счётчика.
- Размер кисти в текущем brush planner выбирается по геометрическим ограничениям/палитре, а не по измеренной стоимости игровой квоты.

**Следующий шаг:** INT-002 — спроектировать чтение `pointCount/max/less` без повторного полного обхода массива, формат baseline/delta и протокол связывания с experiment ID. Проверку влияния Monitor необходимо отделить от статического проектирования и выполнить контролируемым A/B-тестом после разрешения на тестирование.

**Границы выполнения:** только статическое чтение текущих исходников/документов и сохранённых JSON. Исходный код, тесты, конфигурация и пользовательские данные не изменялись; приложение, браузер и тесты не запускались.


## 2026-10-31 — INT-002: статическое проектирование точного CHALK snapshot и протокола измерения

**Рабочая ветка:** `feature/image-geometry-optimization`  
**HEAD до документирования:** `1ac91a5c007d441d2860f1824d6dfca056dd7442`  
**Объём:** статическое чтение исходников и документации; код и тесты не изменялись и не запускались.

### Уточнение состава существующих моделей ресурса

- `paint_cost_model.py` содержит legacy модель `empirical-ink-cost-v1`: длина пути и overhead штриха в px-equivalent; это не прямые единицы игрового счётчика.
- `board_resource_model.py` задаёт известные квоты BoardItem0–4 (3000/6000/12000), коэффициент безопасного бюджета по умолчанию 0.85 и оценку через калиброванный points-per-path с отдельной стартовой точкой на штрих.
- `engine_point_calibration.py` использует модель кадрового sampling; номинальная частота движка 48 FPS, но в комментариях прямо указано, что фактический FPS может быть ниже. Исторические параметры шага 2 px и задержки 10 ms используются как baseline; реальный FPS исторических опытов не измерялся.
- `game_point_calibration.py` строит интервальную модель по вручную наблюдаемым порогам видимости штрихов и browser frame probe. Отчёт явно устанавливает `is_engine_exact_counter=false`; это оценка по порогам, а не чтение внутреннего счётчика.
- Следовательно, в AutoDraw уже есть калиброванные оценки игрового расхода, но нет подтверждённого прямого runtime-измерения CHALK, автоматически связанного с brush experiment manifest.

### Статический аудит Game Monitor 0.1.2

- `boardSnapshot()` вызывает рекурсивный `pointCount(atom.points)` и отдельный поиск `lastPoint(atom.points)`.
- `emit()` автоматически создаёт ещё один полный `boardSnapshot()` для каждого события.
- `wrapMethod()` делает snapshot до и после оригинального метода; для `onDrawing` дополнительно вызывается `sampleActiveStroke()`, который снова делает snapshot и при изменении вызывает `emit()` с ещё одним snapshot.
- `updateLess()` в самом движке уже пересчитывает все точки. Обёртка Monitor добавляет к этому собственные полные проходы до/после/в emit.
- Во время активного штриха polling с интервалом 25 ms также строит snapshot; при изменении подписи `emit()` делает ещё один проход.
- Это доказывает наличие нескольких дополнительных O(N)-проходов в структуре текущего Monitor, но не определяет фактический процент потери FPS. Количественный overhead требует A/B-теста.
- В текущем экспорте присутствует `pointCount`, но нет `max` и `less`. Статические материалы описывают `updateLess()` как вычисление `less = max - pointCount` и отправку `percent = less / max`; точная доступность этих локальных значений как полей экземпляра не подтверждена. Нельзя заранее проектировать чтение `board.max`/`board.less` как гарантированного API.

### Спроектированный контракт измерения

1. **Единица измерения:** целое число сохранённых игровых точек. Длина пути, footprint, площадь пикселей и радиус — отдельные характеристики.
2. **Контрольные точки:** `pre_test` после подтверждённой очистки и непосредственно перед первым штрихом; `post_test` сразу после завершения/остановки/ошибки исполнения и до следующего Clear; `post_clear` необязателен и служит только проверке сброса.
3. **Формула:** `consumed_points = post_test.point_count - pre_test.point_count`. Если доступен остаток, эквивалентно `pre_test.less - post_test.less` при неизменном `max`.
4. **Валидация:** `max` должен быть одинаковым в обоих снимках; `point_count` и `less` должны быть целыми и лежать в диапазоне `[0, max]`; отрицательная дельта, смена доски/квоты, отсутствующий baseline или невалидный источник делают результат `inconclusive`.
5. **Начальная служебная точка:** baseline снимается после очистки, поэтому возможная специальная точка режима расширенного рисования вычитается автоматически и не считается расходом теста.
6. **Признак точности:** сохранять `is_exact`, `source_method` и `validation_status`. Точные данные из внутреннего счётчика не смешивать с оценкой по шкале, px-equivalent или frame-sampling модели.
7. **Схема ресурсного checkpoint:** `experiment_id`, `run_id`, `checkpoint`, `sequence`, `captured_at_utc`, `captured_at_performance_ms`, `board_session_id`, `board_item_type`, `max_points`, `remaining_points`, `point_count`, `baseline_point_count`, `consumed_points`, `source_method`, `is_exact`, `validation_status`.
8. **Связь с экспериментом:** использовать существующий проект `BRUSH_MONITOR_AUTOCAPTURE_DESIGN.md` и его `sessionId/runId/checkpoint`; не создавать второй транспорт. В manifest добавить стабильный UUID эксперимента: текущее имя папки содержит timestamp/кисть/сценарий, но отдельное поле `experiment_id` в `experiment.json` не формируется.

### Проектное решение по снижению overhead

- Убрать автоматический полный `boardSnapshot()` из `emit()`; событие должно содержать только явно переданные лёгкие поля.
- Разделить минимальный `resourceSnapshot` (O(1), только уже готовые и проверенные значения) и диагностический `boardSnapshot` (O(N), только по явному запросу/контрольной точке).
- Не выполнять `pointCount(atom.points)` и `lastPoint(atom.points)` на каждом `onDrawing`/poll tick.
- Предпочесть чтение уже вычисленного значения из игрового CHALK event или подтверждённого поля объекта. Если exact source не найден, вернуть `unavailable`; не выполнять скрытый O(N) fallback во время рисования.
- Полный пересчёт массива допустим в диагностическом режиме на ограниченных контрольных точках для сверки точности кандидата, но не в production-потоке каждого кадра.
- Отдельно проверить, можно ли получать `percent` из события CHALK и восстановить целое значение через известный лимит доски. До проверки точности/округления это только кандидат, не exact source.

### Разделение следующей работы

- INT-002 закрыта только как статическое проектирование. Никакой runtime-точности или безопасного overhead этим не подтверждено.
- INT-003 — живой тест доступности источника CHALK и A/B сравнение без Monitor / с Monitor 0.1.2; запускать только после отдельного разрешения на тестирование.
- INT-004 — реализация автоматической связи через уже описанный loopback bridge; требует отдельного разрешения на изменение кода.
- Далее INT-005—INT-009: контролируемая матрица, модель, интеграция, оптимизация и прогноз/факт.

**Документы, обновлённые по INT-002:** `TASKS.md`, `WORK_LOG.md`, `PROJECT_STATUS.md`, `ROADMAP.md`, `DECISIONS.md`, `CHANGELOG.md`, `BRUSH_MONITOR_AUTOCAPTURE_DESIGN.md`, `GAME_MONITOR_BRUSH_LAB_PLAN.md`, `source/game_monitor/README.md`.

## INT-003 — точный источник CHALK и низконагрузочный Monitor (частично выполнено)

**Дата:** 2026-10-31  
**Статус:** IN_PROGRESS — статическая часть и реализация выполнены; live browser/game A/B остаётся незавершённым.

### Проверка игрового bundle

Изучен клиентский bundle из `master`: `AutoDraw_Stage20/fileGameEngine/main.min_570122a1.js` (blob SHA `28838e803dcc6f85efb13febd93cc9e0f5046ffc`).

Подтверждено:
- конструктор `BoardPane` устанавливает `this.max=n`, `this.less=this.max`, затем вызывает `clear()`;
- `updateLess()` считает все точки `atom.points`, присваивает `this.less=this.max-e` и отправляет `BlackBoardEvent.CHALK` с `percent=this.less/this.max`;
- `onDrawStart()` добавляет начальную точку и вызывает `updateLess()`;
- `onDrawing()` на `ENTER_FRAME` добавляет точку только если координата внутри доски, затем вызывает `updateLess()`;
- `onDrawingEnd()` фиксирует штрих через `atom.add()`;
- радиус кисти не участвует в формуле CHALK. Он может влиять на покрытие/количество требуемых штрихов, но не на прямую стоимость уже принятой точки.

Таким образом, статически подтверждён O(1)-источник точного текущего остатка: числовые поля экземпляра `BoardPane.max` и `BoardPane.less`. `percent` в событии CHALK не нужен для восстановления целого остатка. Фактический расход прогона по-прежнему вычисляется как `post.pointCount-pre.pointCount`, где `pointCount=max-less`, при неизменной доске и лимите.

### Реализация Game Monitor 0.2.0

Изменён `AutoDraw_Stage20/source/game_monitor/game_monitor.js`:
- добавлен O(1) `resourceSnapshot()` с проверкой целочисленности и диапазона `max/less`;
- `emit()`, wrappers, polling, `status()` и `export()` больше не сканируют `atom.points`;
- полный рекурсивный подсчёт и поиск последней точки вынесены в явный `diagnosticSnapshot()`;
- при недоступных/невалидных полях возвращается `validationStatus: "unavailable"`, без скрытого O(N) fallback;
- экспорт содержит `resourceSnapshot`, включая `maxPoints`, `remainingPoints`, `pointCount`, `sourceMethod`, `isExact` и `validationStatus`.

### Автоматические проверки

Добавлен `AutoDraw_Stage20/source/game_monitor/tests/game_monitor.test.js` на Node.js:
- exact snapshot из `max-less`;
- отсутствие чтения элементов `atom.points` из Monitor hot path;
- явная диагностическая сверка с полным подсчётом;
- `unavailable` без fallback при отсутствии `less`;
- вычисление дельты точек;
- восстановление исходного метода после `stop()`.

В `.github/workflows/geometry-tests.yml` добавлен шаг `node --test ..\\game_monitor\\tests\\game_monitor.test.js`. CI-запуски после изменений созданы; окончательное состояние и логи теста будут зафиксированы после завершения workflow.

### Незавершённая runtime-часть

В текущей среде нет управляемого браузера/DevTools и доступа к пользовательскому игровому iframe, поэтому фактическое чтение полей живого экземпляра и A/B-замер FPS выполнить здесь нельзя. Это ограничение среды, а не отрицательный результат теста.

Для закрытия INT-003 необходимы в реальной игре:
1. проверить `status().snapshot`: `isExact=true`, целые `maxPoints`/ `remainingPoints`, `pointCountMatches=true` при явном `diagnosticSnapshot()`;
2. проверить значения до Clear, после Clear, после одного штриха и после нескольких штрихов;
3. провести минимум 3 чередующихся повтора A (Monitor off) и B (Monitor 0.1.2), а затем минимум 3 повтора A и C (Monitor 0.2.0) при одинаковых условиях;
4. сохранить frame probe, длительность, фактическую дельту точек, завершённые/пропущенные штрихи, eventCount/droppedEvents/errors;
5. сравнить медианы и разброс. До этого нельзя заявлять, что overhead равен нулю или что FPS улучшился на конкретный процент.

**Коммиты реализации:**  
- `5619b68eea41e933db10dcb145d6326a22bb2e56` — Game Monitor 0.2.0, O(1) snapshot.  
- `541d04a150dedb3b048242b879fa8aa28e715de5` — первичные Node-тесты.  
- `683a943bcb69b4cd38309c38910981efae7c2701` — запуск Node-тестов в CI.  
- `3892e380827d16872073adac785d4c776db95232` — исправлена проверка восстановления исходного метода в тесте.

### Дополнение: CI-проверка Monitor 0.2.0

- GitHub Actions run **#1037** (`fc39292cb4b190a74dd72afd3ea0fc9833df081d`) подтвердил успешное выполнение `node --check` и всех 4 Node.js тестов Game Monitor; шаг локального WebSocket smoke-server также завершился успешно.
- В run #1037 успешно завершился job `executor-tests`. Полный workflow на момент записи ещё выполняет benchmark Stage 8 и Windows portable build smoke-test; его общий conclusion пока не зафиксирован.
- Предыдущий запуск выявил две ошибки тестовых fixtures: regex перехвата индексного чтения массива был переэкранирован, а начальный `less` не соответствовал mock-массиву. Исправлено в `fc39292`; повторный Node test step прошёл.
- Успешные mock-тесты подтверждают контракт Monitor и отсутствие дополнительных чтений индексов `atom.points` со стороны hot path. Они не измеряют реальный FPS браузерной игры.

### Read-only checkpoint для A/B/C

Добавлен `AutoDrawGameMonitor.inspect()`: он находит BoardPane по запросу и читает `max`/`less` без attach, wrappers, polling и изменения методов. После `AutoDrawGameMonitor.stop()` его можно использовать только на контрольных точках в режиме A, чтобы получить точный baseline/post без активного Monitor во время штриха. Добавлен отдельный Node-тест на этот режим. Код и тест добавлены commits `3c46e65318bca121af3f9a074a72d1f7c117188f` и `fabb666d5fa6398da029922799efb96ef6aaafdb`.


### Уточнение по приёму координат и радиусу кисти

Повторно проверены `BlackBoardAtom.pushPoint(t)`, `BoardPane.onDrawing()` и `BoardPane.setRadius()` в bundle:
- `pushPoint` добавляет точку только при пустом текущем штрихе или если координата не равна последней точке;
- `onDrawing` вызывает `updateLess` на кадре внутри доски, даже если `pushPoint` отклонил повторную координату;
- `setRadius` только записывает радиус в `atom.radius`, не изменяя количество точек и CHALK напрямую.

Следствие: игровая стоимость равна количеству уникальных последовательных принятых координат по штрихам, а не числу кадров, длине пути, площади покрытия или радиусу. Для одного и того же набора принятых координат расход не зависит от размера кисти. Большая кисть может снизить число нужных проходов за счёт большего покрытия, но этот косвенный эффект требует отдельного эксперимента по качеству/числу штрихов.


## 2026-10-31 — INT-003: решение по автоматизации CHALK-экспериментов

**Основание:** пользователь указал, что вручную отрисовать траектории длиной 300–500 px сложно и что весь набор тестов предпочтительно автоматизировать.

**Проверено в исходниках feature-ветки:**
- `BrushBehaviorTestTab.create_and_transfer_plan()` создаёт DrawingPlan и передаёт его существующему исполнителю.
- `build_brush_test_drawing_plan()` преобразует фиксированные тестовые сценарии в стандартный DrawingPlan.
- `MouseExecutor` воспроизводит план через PyAutoGUI, генерируя реальные системные события мыши; шаг и задержка задаются через `ExecutorConfig.point_step_px` и `point_delay_ms`.
- Лаборатория уже содержит часть автоматизации: preflight калибровки, проверку/очистку доски, drag ползунка, передачу плана, execution report и снимки.
- Полная матрица, пакетное выполнение, точная pre/post привязка Monitor JSON и автоматическое подтверждение радиуса ещё не завершены.

**Решение:** не просить пользователя вручную рисовать контрольные линии и не эмулировать игровые внутренние методы. Все траектории должны строиться как параметрические DrawingPlan и исполняться существующим MouseExecutor/PyAutoGUI. Тестовый код не должен вызывать `BoardPane.onDrawing()`, `BlackBoardAtom.pushPoint()`, `updateLess()` или изменять `atom.points`/счётчики.

**Документация:** в `GAME_MONITOR_BRUSH_LAB_PLAN.md` добавлен раздел 13 с архитектурой генератора траекторий, матрицей, пакетным запуском и границами автоматизации. INT-005 в TASKS уточнена: матрица должна быть автоматизирована и привязывать результаты к experiment_id/run_id.

**Границы:** это документирование решения и проверка существующих интерфейсов, не реализация нового пакетного оркестратора и не live browser test. INT-003 остаётся IN_PROGRESS; INT-005 остаётся TODO.


## 2026-10-31 — уточнение логической и экранной геометрии доски

Пользователь уточнил: логический размер доски в игровом движке — **420×240**, фактическая экранная область больше. Прежнее утверждение о 460×240 было ошибочным и исправлено в `GAME_MONITOR_BRUSH_LAB_PLAN.md` и `PROJECT_DOCUMENTATION.md`.

Для автоматизации закреплено разделение:
- DrawingPlan задаёт координаты в логической системе 420×240;
- screen ROI описывает фактическую область доски в пикселях экрана;
- MouseExecutor должен преобразовывать логические координаты в экранные через откалиброванные origin и scaleX/scaleY;
- размер ROI нельзя использовать как логический размер, а длину экранного перемещения нельзя напрямую считать игровой длиной.

Исходный код тестовых сценариев и соответствующие тесты всё ещё содержат прежние предположения о 460×240 и граничные координаты до x=420. Их нужно отдельно согласовать с точной семантикой границы 420×240 и новым преобразованием координат до запуска автоматической матрицы. Код в рамках этого уточнения не менялся.


## 2026-10-31 — INT-003: обнаружено смешение логических и экранных координат

**Проверено:** `source/executor/drawing/mouse_executor.py`, `source/preparation/brush_behavior_test_ui.py`, `integrated_app.py`, `source/game_monitor/game_monitor.js`.

**Факты из исходников:**
- Логическая доска игрового движка — 420×240; `resourceSnapshot()` Monitor уже возвращает доступные `logicalWidth`, `logicalHeight`, `scaleX`, `scaleY`.
- `integrated_app.py::_get_brush_test_canvas_area()` получает экранный ROI из калибровки/исполнителя, а `_get_brush_test_canvas_size()` возвращает его экранные width/height.
- `build_brush_test_drawing_plan()` использует полученный размер как размеры плана, но координаты сценариев являются локальными значениями тестовой геометрии (например, endpoint x=420).
- `MouseExecutor._screen_point()` выполняет только `area_origin + point`; масштабирование отсутствует.

**Вывод:** Brush Test сейчас смешивает экранные размеры ROI и логические координаты сценариев. При ROI, отличном от 420×240, физический путь указателя не соответствует логической траектории. Это блокирует достоверное сравнение длины/скорости/кисти, хотя само чтение CHALK `max`/`less` этим не опровергается.

**Решение по дальнейшей работе:** реализовать явный logical→screen transform с origin и scaleX/scaleY только для logical-планов; сохранить неизменным исполнение обычных screen/local планов. До исправления не запускать полную матрицу и не интерпретировать её расход как зависимость от заявленной логической длины. Отдельно проверить контракт граничных координат x=420/y=240 — не менять их на 419 без проверки hit-test.

**Документация обновлена:** `source/game_monitor/README.md`, `GAME_MONITOR_BRUSH_LAB_PLAN.md`. Код и тесты на этом шаге не менялись; runtime и CI не запускались. INT-003 остаётся IN_PROGRESS.


## 2026-10-31 — документирование целевой архитектуры автоматизированной лаборатории

**Добавлен документ:** `AutoDraw_Stage20/docs/BRUSH_TEST_AUTOMATION_VISION.md`.

**Что зафиксировано:**
- Полное видение модуля от создания сессии и preflight до сохранения и проверки набора данных.
- Разделение ответственности Experiment Controller, генератора DrawingPlan, Coordinate Transform, Brush Controller, MouseExecutor, Game Monitor, Experiment Recorder и Dataset/Analyzer.
- Правила точного измерения CHALK через дельту `pointCount=max-less`, отдельное хранение оценок и фактических измерений.
- Геометрия логической доски 420×240 и экранного ROI, текущий блокер logical→screen.
- Матрица факторов, повторы, отдельная A/B/C серия, checkpoints, manifest, fail-safe и статусы качества прогона.
- Критерии готовности модуля и последовательность реализации до интеграции модели в оптимизатор AutoDraw.

**Связанные документы:** обновлены `docs/README.md`, `docs/TASKS.md` и `docs/PROJECT_STATUS.md`; INT-005 теперь ссылается на целевую архитектуру.

**Границы:** это документирование целевого решения. Реализация модулей, исходный код, тесты, CI и runtime не изменялись/не запускались. INT-003 остаётся IN_PROGRESS, INT-005 — TODO.

**Commit документа:** `c110d1c78b7afa7f22964265e50a2d5a0a4a7f3b`.


## 2026-10-31 — быстрый индекс документации модуля автоматических тестов кистей

**Добавлен документ:** `docs/BRUSH_MODULE_QUICK_INDEX.md`.

Индекс предназначен для быстрого входа в разработку модуля. Он содержит:
- рекомендуемый порядок чтения документации;
- карту компонентов и соответствующих исходников;
- тематический поиск по CHALK, Brush Test, MouseExecutor, logical→screen, bridge, матрице, manifest и A/B/C;
- ключевые измерительные ограничения и границы достоверности;
- рекомендуемый порядок работы и правило поддержки индекса.

В `docs/README.md` добавлена ссылка на индекс. При исправлении строки навигации также устранён некорректный буквальный разделитель `\\n`, попавший в таблицу при предыдущем обновлении.

Код, тесты, конфигурация и runtime не изменялись/не запускались. Индекс является навигационным документом; актуальные сигнатуры и поведение следует проверять по исходникам текущей ветки.


## 2026-10-31 — INT-003: реализован первый logical→screen transform для Brush Test

Изменённые исходники: добавлен source/preparation/brush_coordinate_transform.py; обновлён source/preparation/brush_behavior_test_ui.py (logical-планы и запрет продления концов); обновлён integrated_app.py (преобразование логического плана в screen-local ROI при передаче в Stage6).

Правило преобразования: scaleX=(ROI.width-1)/420, scaleY=(ROI.height-1)/240; включительные логические границы отображаются на последний пиксель ROI. Origin и обе системы координат записываются в generation.screen_transform. Исходный logical-план сохраняется отдельно, runtime-план имеет экранный размер ROI.

Тесты добавлены/изменены: source/preparation/tests/test_brush_coordinate_transform.py — отображение границ/центра, масштабы, сохранение исходного плана и отклонение некорректных входов; source/preparation/tests/test_brush_behavior_test_ui.py — генерация logical-плана; tests/test_unified_app.py — проверка передачи logical-плана в screen-local runtime-план.

GitHub Actions запущен для серии изменений; окончательный conclusion ещё не зафиксирован на момент записи. Live browser/game проверка не выполнялась. Формула реализована и unit-проверяема, но соответствие живому hit-test и границам доски не подтверждено. Полную CHALK-матрицу пока не запускать.

Изменения затрагивают только Brush Test и интеграционную передачу его плана. Обычные screen/local DrawingPlan не переводятся на новый формат; master не изменяется.

### Дополнительное исправление сериализации logical-плана

CI выявил, что общий helper stage8_optimizer.save_plan() нормализует coordinate_system в local_canvas_pixels. Поэтому он не подходит для сохранения исходного Brush Test logical-плана. Сохранение исходного сценария и transform metadata переведено на прямую JSON-запись; нормализующий save_plan оставлен только для screen-local runtime-плана, который загружается в Stage6. Интеграционный тест теперь проверяет обе версии отдельно. Повторный CI после исправления ожидается.


Дополнение: transform metadata дополнена явным указанием, что runtime-план и ExecutorConfig.point_step_px используют экранные пиксели. Это не позволяет ошибочно интерпретировать шаг исполнителя как логический шаг доски; фактические настройки executor сохраняются в execution report.


### Защита от неправильного использования исходного logical-плана

Stage6App.load_plan_from_path() теперь явно отклоняет coordinate_system=logical_board_pixels с сообщением о необходимости передать его через Brush Test. Это не позволяет вручную открыть исходный логический JSON как обычный screen-local DrawingPlan. Добавлен regression test в tests/test_unified_app.py.


## 2026-10-31 — INT-003: подтверждён CI для logical→screen handoff

Проверен актуальный HEAD `3a0383b56b5972d4b978ff30080d7b7768b021d0` ветки `feature/image-geometry-optimization`. GitHub Actions run #1132 завершился `success`; успешно завершены jobs `geometry-tests`, `executor-tests` и `Windows portable build and startup smoke-test`. Следовательно, программные unit/integration/regression проверки и portable smoke-test для этого HEAD прошли.

CI не подтверждает точное совпадение сохранённого screen ROI с физической границей игровой доски, поведение hit-test для x=420/y=240, runtime-доступность Game Monitor в iframe или влияние Monitor на FPS. Эти пункты остаются незавершёнными условиями INT-003. Полную CHALK-матрицу не запускать до live-проверки геометрии.


## 2026-10-31 — INT-003: исправлена ошибочная ширина логической доски

**Причина:** предыдущая версия Brush Test transform использовала 420×240 на основании прежнего документированного уточнения. Повторная прямая проверка клиентского bundle из `master` выявила, что `BoardPane.BLACK_BOARD_WIDTH=460`, `BLACK_BOARD_HEIGHT=240`; `BoardItemBase.createNativeContent()` назначает `board.width=460`, `board.height=240` и равномерный scale `boardMask.width / 460`. `onDrawing()` преобразует координаты через `globalToLocal()` и проверяет их в прямоугольнике `0,0,this.width,this.height`.

**Изменения:** `LOGICAL_BOARD_WIDTH` изменён на 460; Brush Test теперь создаёт logical-планы 460×240; преобразование X использует `(ROI.width-1)/460`; исходный тестовый endpoint x=420 оставлен без изменений, так как это координата штриха внутри доски, а не её ширина. Обновлены transform unit tests, тест генерации logical-плана, интеграционный handoff test и текст UI. Исторические записи с выводом 420×240 не удалялись; это зафиксировано как исправление предыдущего вывода.

**Граница проверки:** Egret `Rectangle.contains()` в исходнике Egret использует включительные сравнения `x <= this.x + this.width` и `y <= this.y + this.height`; поэтому текущая модель inclusive boundary соответствует API движка. Тем не менее live-проверка попадания ROI и граничных координат в конкретной игре обязательна. CI для новой версии 460×240 ожидается; run #1132 относится к предыдущей версии кода и не засчитывается как проверка этой коррекции.


### Контрольный сценарий для live-проверки границ

Добавлен `Проверка границ доски` (`board_boundary_probe`) в `source/preparation/brush_behavior_test_ui.py`. Он строит четыре коротких штриха, стартующих внутри BoardPane и заканчивающихся точно на x=0, x=460, y=0 и y=240. Суммарная длина 160 логических px; `line_extension_px_override=0`. Добавлен unit test, проверяющий все четыре endpoint и отсутствие продления. Сценарий предназначен для минимальной проверки transform/hit-test с радиусом 1 до запуска полной матрицы; live-прогон ещё не выполнялся.


### Защита от неверного aspect ratio ROI

Bundle показывает, что BoardPane масштабируется равномерно (`scaleX=scaleY`). Поэтому независимые X/Y коэффициенты не должны маскировать ошибочно выделенный ROI. В `brush_coordinate_transform.py` добавлена проверка относительного расхождения `scaleX` и `scaleY`: допуск 1%; при превышении transform прекращается с просьбой повторно выделить точную область доски. В metadata записываются `expected_uniform_scale`, `uniform_scale_relative_error`, `uniform_scale_tolerance`. Тесты обновлены на ROI 646×338 (равномерный масштаб с учётом целочисленных границ) и добавлен negative test для ROI 646×323. Интеграционный fixture также переведён на 646×338.


### CI для базовой коррекции 460×240

GitHub Actions run #1142 на коммите `d0c4aee8c4bef75daedfae85ae4403a3a8661ef4` завершился `success`: `geometry-tests`, `executor-tests`, `Windows portable build and startup smoke-test` — все jobs прошли. Это проверяет базовую коррекцию ширины BoardPane на 460 и соответствующий integration handoff. Run #1142 предшествует более позднему boundary probe и guard равномерности ROI; их CI остаётся отдельным ожидаемым подтверждением.


## 2026-10-31 — INT-003: сохранение доски после теста и горячая клавиша Alt

По запросу пользователя изменён post-draw workflow Brush Test. После успешного исполнения AutoDraw сохраняет `after_draw` (полный экран, ROI доски, ROI индикатора краски), измерения видимости штрихов и `experiment.json`, затем завершает постэтап без автоматического клика по Clear. Рисунок остаётся на доске для ручной проверки и снятия Game Monitor snapshot/export. Начальная очистка перед независимым тестом сохранена; очистка между повторами выполняется вручную после сохранения результатов.

Глобальная клавиша остановки изменена с F12 на Alt: Brush Test listener, MouseExecutor, окно Stage6, legacy Stage2 и калибровочный тест. Для левой и правой Alt добавлены Tk bindings; глобальные обработчики используют `pynput` Alt. F12 в инструкции Game Monitor для открытия DevTools не менялась.

Обновлены unit tests для Alt listener и stop reason. Локальный запуск тестов и CI в этой сессии не выполнялись; требуется проверить GitHub Actions на новом HEAD. INT-003 остаётся IN_PROGRESS, live-проверка доски и A/B/C остаются обязательными.


## 2026-10-31 — INT-003: три live-прогона board_boundary_probe

Пользователь добавил результаты в commit `f72c2d16e7f61071bcaa2d184c071189dd74b69c`. Изучены три независимые папки экспериментов `experiment-20261031-083415-b1-board_boundary_probe`, `experiment-20261031-084258-b1-board_boundary_probe`, `experiment-20261031-084452-b1-board_boundary_probe`.

**Preflight и исполнение:** во всех трёх записях пустая доска совпала с подтверждённым эталоном в пределах 0.15% (изменено 0.0069%, similarity 99.9931%). Запрошенный радиус 1 подтверждён пользователем визуально и Monitor preflight (`observed_radii=[1]`). Каждый план завершил 4/4 штриха, 106 move calls, без ошибки, с успешным mouse release; длительности 7.407, 7.422 и 7.407 с. Параметры executor совпадают: point_step 2 screen px, point_delay 10 ms, line_extension 0.

**Точный расход из Game Monitor 0.2.0:** baseline каждого независимого запуска — pointCount 1 / remainingPoints 5999 при maxPoints 6000. После штрихов получено: run 1 pointCount 52 / remaining 5948 (дельта 51); run 2 pointCount 53 / remaining 5947 (дельта 52); run 3 pointCount 53 / remaining 5947 (дельта 52). Средний расход — 51.67 игровых точки на четыре граничных штриха. Во всех Monitor exports доска обнаружена, источник `BoardPane.max+BoardPane.less`, `isExact=true`, `validationStatus=valid`, droppedEvents=0, errors=0. Внутри каждого из четырёх рисующих штрихов currentRadius=1. Итоговый currentRadius=30 относится к последующему жесту возврата кисти на 30 и не должен трактоваться как радиус рисования.

**Геометрия и предел доказательства:** POINTER_UP_CANDIDATE endpoints совпадают с экранными целями ROI: right (1140, 240), left (563, 240), bottom (852, 390), top (852, 90) в client coordinates. С учётом вертикального смещения viewport 163 px они соответствуют локальным пиксельным границам ROI 578×301 и logical bounds x=460/0, y=240/0. Однако Game Monitor не записывает фактические x/y каждой принятой точки в DRAW_SAMPLE; POINTER_UP_CANDIDATE — это координата события мыши, а не доказательство принятия точки BoardPane. Поэтому точное попадание крайних точек в игровую геометрию пока не подтверждено только JSON-событиями.

**Обнаруженный дефект анализа скриншотов:** `stroke_visibility_analysis` во всех трёх manifest был `inconclusive` с причиной `drawing_plan_canvas_dimensions_mismatch`: исходный план 460×240 сравнивался с ROI-скриншотом 578×301 без применения сохранённого logical→screen transform. Изменён `brush_behavior_test_ui.py`: добавлен helper `_screen_local_strokes_for_capture()`, который проверяет metadata transform/ROI и преобразует ожидаемые точки в локальные экранные пиксели до сравнения; обновлены оба пути захвата. Добавлены unit tests на преобразование и mismatch ROI. Также исправлен тест uniform-scale guard: negative fixture ошибочно использовал равномерный ROI 646×338; теперь используется non-uniform 646×323.

**Ограничения измерений:** paint meter screenshot estimate во всех трёх опытах inconclusive (2 changed columns, low confidence), поэтому проценты шкалы не используются как измеритель CHALK. Точный расход берётся только из Monitor max/less. Визуальные screenshots присутствуют, но автоматический анализ видимости в исходных результатах не дал заключения; после исправления analyzer требуется повторно прогнать минимум один boundary probe для получения валидного stroke visibility result.

CI run #41174050665 на пользовательском commit f72 выявил ошибку тестовой фикстуры: 502 passed, 1 failed — `test_transform_rejects_nonuniform_roi_for_uniform_game_scale` не выбрасывал ValueError, потому что в negative test был передан равномерный ROI 646×338. Фикстура исправлена на 646×323. Дополнительно исправлен вызов builder в новых UI tests, чтобы соответствовать фактической сигнатуре. Новые CI runs для последующих commits ожидаются/проверяются; INT-003 остаётся IN_PROGRESS.


### Дополнение: визуальная сверка сохранённых live-скриншотов — 31.10.2026

Выполнен непосредственный визуальный просмотр всех трёх `after_draw-board.png` и всех трёх `after_draw-screen.png` из commit f72. На каждом ROI-скриншоте видны четыре ожидаемых чёрных штриха; на полном экране все четыре доходят до соответствующих видимых границ игрового BoardPane. Видимого выхода штрихов за пределы доски нет. Следовательно, boundary probe визуально подтверждён на трёх повторах для конкретного screen ROI 1920×1080, ROI x=563/y=253/578×301 и текущего масштаба браузера. Это не универсальная гарантия для других экранов/ROI.

Автоматическое поле `stroke_visibility_analysis` в исходных manifest всё ещё содержит прежний inconclusive-результат, поскольку было создано до исправления analyzer; ручная проверка самих приложенных PNG не меняет исторический JSON. После исправления analyzer новые снимки смогут дополнительно получать машинную метрику. В совокупности live screenshots + exact Game Monitor max/less snapshots подтверждают корректность геометрии и расхода в проверенной конфигурации. Основной оставшийся блокер INT-003 — контролируемая A/B/C-серия Monitor off / 0.1.2 / 0.2.0 минимум по три повтора каждого режима, а также успешный CI актуального кода.


### INT-003 — проверка актуального CI, 31.10.2026

Проверен branch HEAD `0c09d2830bb007b7a9de1cd46e085f779e91d2f3`. Workflow `Geometry planner tests` run #1224 (`41174465072`) имеет `completed/success`; jobs `geometry-tests`, `executor-tests` и `Windows portable build and startup smoke-test` завершились success. В geometry job успешно прошли Node syntax/resource snapshot tests Game Monitor, WebSocket smoke-server tests, preparation/geometry tests и UI regressions. Run #1223 также success.

Исторические падения #1210—#1213 исправлены последующими изменениями: negative fixture для uniform-scale guard заменена на действительно non-uniform ROI 646×323, вызов plan builder приведён к актуальной сигнатуре. Текущий HEAD зелёный.

Ограничения: это CI, а не live Firefox iframe test. Smoke server всё ещё принимает только `auth`/`ping`; production read-only bridge, автоматический pre/post capture и manifest binding отсутствуют. A/B/C Monitor off/0.1.2/0.2.0 и численный overhead не измерены. INT-003 остаётся IN_PROGRESS.


### Game Monitor 0.2.1 — 31.10.2026

Добавлена O(1) регистрация последней фактически принятой координаты в `DRAW_SAMPLE`: `pointDelta` показывает количество новых точек между снимками, `acceptedPoint` содержит хвостовую координату при положительной дельте. Если `pointDelta > 1`, промежуточные точки могли быть coalesced; экспорт это явно показывает. Добавлены тесты точной координаты, отсутствия stale point, multi-point delta, восстановления всех методов и повторного lifecycle. CI run #1238 на commit `32a3fdb35d95b15ca64c1bb4c7f404904ffc23e8`: Node.js tests и WebSocket smoke-server tests прошли; полный CI и Windows portable smoke-test на момент записи ещё выполняются.

План live-валидации не закрыт: требуется новый boundary probe с Monitor 0.2.1 и A/B/C off / 0.1.2 / 0.2.1. Реальный Firefox iframe smoke test и production bridge по-прежнему не выполнены.


### Полный CI Game Monitor 0.2.1 — 31.10.2026

Проверен актуальный HEAD ветки `feature/image-geometry-optimization`: `354ff64802a8065aff19f17176c2ea3e65ff4bbc`. Workflow #1241 (`41212496267`) завершился success. Все три jobs прошли: `geometry-tests`, `executor-tests`, `Windows portable build and startup smoke-test`. В geometry job успешно выполнены Game Monitor syntax/resource snapshot tests, локальный WebSocket smoke server, анализ клиентского bundle, Stage 5/7/8 benchmarks, synthetic geometry, fallback/outline-first comparisons, preparation/geometry tests и unified-app UI regressions.

CI закрывает автоматическую проверку текущего HEAD, но не live Firefox iframe transport, не A/B/C overhead и не новую live-проверку acceptedPoint. INT-003 остаётся IN_PROGRESS. Следующий gate — реальный browser smoke test; до его прохождения production bridge не реализовывать.


### 31.10.2026 — дополнена инструкция запуска Firefox smoke-server

- По замечанию пользователя проверен `source/game_monitor/README.md`: инструкция подключения Game Monitor присутствовала, но команды установки зависимости и запуска отдельного WebSocket smoke-server отсутствовали.
- Сверены фактические CLI-параметры с `source/game_monitor/websocket_smoke_server.py` и зависимостью `requirements-smoke.txt`: Python 3.11, обязательный `--origin`, порт по умолчанию `8765`, привязка только к `127.0.0.1`.
- В README добавлены команды PowerShell из корня репозитория, получение точного `location.origin` из игрового iframe, реальный протокол одноразовой авторизации `auth → ready → ping → pong`, ожидаемые результаты, обработка типовых ошибок и остановка сервера.
- Token явно обозначен как секрет одноразового использования; инструкция не предлагает публиковать его или обходить CSP.
- Изменён только README Game Monitor и этот журнал документации. Код сервера, Game Monitor и игровой движок не менялись. Live Firefox smoke test по-прежнему не считается выполненным.


## 2026-10-31 — разбор live WebSocket, A/B/C и boundary результатов (commit e9a915d)

**Источник результатов:** `e9a915d5d8247055ab86168789079ed0562e0ee3`, ветка `feature/image-geometry-optimization`.

**Проверенные данные:**
- `data/result_test_web_socket/`: handshake response `ready → pong`; Game Monitor 0.2.1 экспортирован из игрового iframe `https://eufbpet.hust.me/pet.php`, `isTopFrame=false`, доска обнаружена, 340 событий, 0 dropped events, 0 ошибок.
- `data/a,b,c -test/run_01..run_03/`: три переставленных порядка A/B/C, snapshots и полные Monitor exports.
- FPS probe: каждый из трёх файлов содержит 600 кадров за ~10 секунд, 60 FPS, P95 16.68 ms, max 16.68 ms, документ видим, interruptions нет.
- `data/results/brush_behavior_tests/experiment-...board_boundary_probe/experiment.json`: четыре завершённых штриха, 7.36 с, 106 move calls, успешный mouse release, точный post pointCount 53 при baseline 1.

**Результаты A/B/C (дельта pointCount):**
- A / Monitor off: 53, 52, 52.
- B / Monitor 0.1.2: 0*, 52, 52.
- C / Monitor 0.2.1: 50, 52, 52.
- *B-1 невалиден как успешный drawing run: pointCount остался 1; экспорт содержит только стартовый sample и вызов updateLess без изменения счётчика.
- В C во всех трёх прогонах `diagnosticPointCount` совпадает с точным snapshot; сумма `pointDelta` равна 50/52/52. В валидных повторах 2 и 3 все режимы дали 52.

**Выводы и ограничения:**
- Точный источник расхода — `ΔpointCount`; визуальная оценка шкалы краски в отдельном boundary experiment inconclusive.
- FPS-файлы не привязаны к отдельным режимам A/B/C, а длительности исполнения по каждому режиму отсутствуют. Overhead Monitor не измерен.
- Accepted points в одном из экспортов 0.2.1 дошли до y=0/240; горизонтальные крайние принятые координаты составили примерно x=2.21/458.21, не x=0/460. Автоматическая визуальная эвристика boundary experiment отметила 4/4 ROI как visible, но это не доказывает принятие точной крайней координаты.
- Нет сравнения разных размеров кисти; влияние радиуса на расход пока не установлено.

**Документация обновлена:** PROJECT_STATUS.md, GAME_MONITOR_BRUSH_LAB_PLAN.md, TASKS.md, ROADMAP.md и CHANGELOG.md. Код приложения, Game Monitor и тесты не менялись; тесты и CI в рамках этого документального разбора не запускались.

**Следующие действия:** повторить A/B/C с отдельными FPS и wall-clock duration на каждый режим, исключить невалидный B-run; отдельно уточнить тест горизонтальных координат x=0/460. До этого полную матрицу размеров кисти не начинать.



## 2026-10-31 — первая реализация автоматического Game Monitor WebSocket bridge

**Изменённые исходники:**
- `source/game_monitor/game_monitor.js`
- `source/game_monitor/game_monitor_bridge.js`
- `source/game_monitor/game_monitor_bridge_server.py`
- `source/game_monitor/requirements-bridge.txt`
- тесты Game Monitor и WebSocket smoke/bridge recorder.

**Что сделано:**
- Добавлен API `subscribe(listener)` в Game Monitor. Новые события можно получать инкрементально без повторной сериализации полного event buffer.
- Добавлен браузерный агент с одноразовой авторизацией, строгим allowlist игровых событий, heartbeat и per-stroke FPS probe.
- Добавлен локальный WebSocket collector на `127.0.0.1`, который автоматически группирует непрерывную серию штрихов в run и сохраняет session/run JSON.
- Реализован расчёт CHALK delta по exact pre/post snapshots; если snapshots невалидны/несогласованы, расход получает статус inconclusive.
- Сохраняются принятые координаты и нижняя граница наблюдаемой длины пути; при coalesced pointDelta траектория маркируется неполной.
- При разрыве WebSocket незавершённый run сохраняется со статусом partial.
- Добавлены тесты подписки/отписки, синтаксиса browser agent, CHALK delta, неполных samples, idle finalization, FPS summary и Origin validation.

**Документация:** обновлены README Game Monitor, BRUSH_MONITOR_AUTOCAPTURE_DESIGN, TASKS, ROADMAP и PROJECT_STATUS.

**Что не подтверждено:**
- новый bridge ещё не проверен в реальном Firefox iframe;
- привязка run JSON к UI `experiment.json` не реализована;
- overhead bridge и FPS probe не измерен;
- тесты не запускались локально в этой среде; CI должен подтвердить Node/Python проверки после push.

**Следующий шаг:** проверить CI на актуальном HEAD; затем провести один browser run и подтвердить автоматическое появление session/run JSON. После этого выполнить интеграцию с manifest и закрыть оставшиеся gates INT-004.


## 2026-10-31 — автоматическая привязка WebSocket run к experiment.json

**Изменённый исходник:** `source/preparation/brush_behavior_test_ui.py`.

**Что сделано:**
- После завершения executor Brush Test UI запускает неблокирующий polling каталога `game_monitor_bridge`.
- Отчёт выбирается по времени старта не раньше `before_draw` и по фактическому радиусу, совпадающему с запрошенным размером кисти.
- Подходящий run JSON копируется в папку эксперимента как `monitor_report.json`.
- В `experiment.json` записываются `session_id`, `run_id`, CHALK delta/status, FPS, trajectory, event count, dropped events и статус capture.
- При отсутствии подходящего отчёта через 10 секунд сохраняется явный `monitor_capture.status=unavailable`.
- При начале нового эксперимента отменяется незавершённый polling предыдущего прогона.

**Ограничения:** связь основана на timestamp+radius, не на сквозном experiment_id. Требуется live проверка реальной сессии и тест последовательных прогонов с одинаковым радиусом. Новый bridge и UI integration ещё не проверены локальным запуском/CI на актуальном HEAD.


## 2026-10-31 — проверка целостности автоматической телеметрии

Run JSON дополнен `stroke_count`, суммой `sampled_point_delta_total`, сравнением `point_delta_matches_chalk`, списком фактически наблюдавшихся радиусов и счётчиками dropped events/errors. UI теперь помечает capture как `saved` только при exact CHALK, единственном радиусе, совпадении суммы pointDelta с CHALK и нулевых потерях/ошибках. Если любое условие не выполнено, отчёт сохраняется со статусом `partial`.

Добавлен WebSocket integration test для production collector: авторизация, session_start, передача DRAW_START/DRAW_END, heartbeat и появление run JSON с точной CHALK delta. Этот тест входит в существующий CI step `Test local WebSocket smoke server`.


### Уточнение статуса monitor_capture

Статус `saved` теперь требует не только exact CHALK и отсутствия потерь, но и положительного расхода/наличия штриха, acceptedPoint, совпадения pointDelta с CHALK, одного радиуса, измеренного FPS без скрытия iframe и нулевых ошибок. Пустой/неполный прогон не будет автоматически считаться успешным даже если executor вернул completed.


## 2026-10-31 — диагностика отсутствующих WebSocket run-файлов после commit 6382c27

**Исходные данные:** commit `6382c27e01f12f7b980bc8fb1ec3e78c760d5b6f` содержит два завершённых executor-теста (`paint_consumption_long_lines`, 6 штрихов; `repeated_coverage`, 4 штриха). В обоих `experiment.json` записано `monitor_capture.status=unavailable`, `reason=matching_run_report_not_found`, `game_monitor_report_path=null`. Добавленный в репозиторий `session.json` относится к session ID `3323cf8e-01ca-4009-8f16-27d657d857f8`; он не совпадает с ID `89f3383e-b562-462f-a1dc-8f516bdd7378`, сообщённым после коммита.

**Подтверждённое поведение кода:** `session.json` создаётся на `session_start`; run JSON создаётся только после события `DRAW_START` и финализируется после idle heartbeat/закрытия соединения. Поэтому наличие только session.json означает, что collector не получил распознанный стартовый штрих (либо поток событий не дошёл до него). Старый формат session.json не сохранял последующие heartbeat и счётчики входящих событий, поэтому по нему нельзя отличить отсутствие событий Monitor от потери событий на стороне bridge.

**Изменения:**
- Browser bridge теперь ведёт `sentEventCount`, `lastEventType`, `lastEventAtPerformanceMs` и `sendFailureCount` и передаёт их в heartbeat.
- Collector обновляет `session.json` атомарно после сообщений: количество принятых сообщений/событий, типы событий, последний sequence/type/time, последний `monitorStatus`, browser bridge diagnostics, число FPS probes и состояние закрытия соединения.
- Интеграционный тест production WebSocket handler дополнен проверками сохранённых event counters/types и heartbeat status.

**Как читать следующий диагностический session.json:**
- `last_monitor_status.eventCount` растёт, `browser_bridge.sentEventCount` растёт, но `received_event_count=0` — browser bridge не доставляет event-сообщения серверу либо callback не вызывается;
- `last_monitor_status.eventCount` растёт и `sentEventCount` растёт, но серверные `received_event_count`/типы не растут — искать сбой между отправкой и обработчиком/протоколом;
- `last_monitor_status.eventCount` не растёт во время рисования — Game Monitor не фиксирует вызовы BoardPane в текущем игровом контексте;
- `received_event_types` содержит `DRAW_START`/`DRAW_SAMPLE`/`DRAW_END`, но run JSON отсутствует — это уже ошибка RunRecorder/finalization, которую можно локализовать по последовательности и `last_message_type`.

**Статус:** это диагностическое улучшение, а не доказанное исправление причины отсутствия run-файла. После обновления требуется перезапустить локальный bridge, заново вставить новый сгенерированный snippet в игровой iframe и выполнить один короткий тест. Live Firefox run ещё не подтверждён.


**Дополнение по CI:** первый запуск теста диагностики выявил только гонку закрытия WebSocket: проверка `connection_closed` выполнялась до того, как сервер завершал обработчик закрытия. Тест дополнен коротким ожиданием после выхода клиента из контекстного менеджера. Повторный CI для HEAD `81ac2cb0870457f49a3d849bd592595a48539c98` запущен; итог пока не подтверждён.


## 2026-10-31 — live WebSocket session: события доставляются, но run не формируется (commit 323a698)

**Артефакт:** `data/results/brush_behavior_tests/game_monitor_bridge/f303b3e1-382e-4859-9681-e1c360ec6424/session.json`, добавлен commit `323a6982666d6b810db3f1deda646888a658ab2a`.

**Фактические показатели сессии:**
- Monitor активен, доска обнаружена; точность snapshot подтверждена (`isExact=true`), ошибок Monitor — 0, dropped events — 0.
- При подключении `pointCount=1`, последний heartbeat: `pointCount=49`, `maxPoints=6000`, `remainingPoints=5951`. Следовательно, точная дельта игрового счётчика за интервал сессии — **48 CHALK points**. Это суммарный расход за сессию, а не доказательство расхода отдельного experiment.json.
- Browser bridge отправил 119 событий, сервер принял 119; `sendFailureCount=0`.
- Получено: 8 `POINTER_DOWN_CANDIDATE`, 8 `POINTER_UP_CANDIDATE`, 55 `DRAW_SAMPLE`, 48 `POINT_QUOTA_UPDATE`.
- Не получено ни одного `DRAW_START` или `DRAW_END`; `frame_probe_count=0`.
- Радиус во время наблюдаемой сессии — 30. Это один размер кисти, не сравнительная серия радиусов.

**Локализованная причина отсутствия run JSON — несовпадение двух моделей жизненного цикла:**
1. Game Monitor 0.2.1 при наблюдении указателя самостоятельно создаёт `POINTER_DOWN_CANDIDATE`, запускает state polling и выдаёт `DRAW_SAMPLE`; при отпускании выдаёт `POINTER_UP_CANDIDATE`.
2. В этой сессии обёртки методов `BoardPane.onDrawStart/onDrawingEnd` не дали событий `DRAW_START/DRAW_END`.
3. Browser bridge запускает FPS probe только на `DRAW_START` и останавливает только на `DRAW_END`.
4. `RunRecorder.event()` открывает run только на `DRAW_START`, а закрывает штрих только на `DRAW_END`. Поэтому доставленные pointer/sample/quota events остаются только в session diagnostics и не создают run JSON.

Это не сбой WebSocket transport: счётчики отправки и приёма совпадают. Это подтверждённый пробел в согласовании pointer-observer fallback с RunRecorder и FPS probe.

**Следующее исправление:**
- Добавить в RunRecorder fallback lifecycle на `POINTER_DOWN_CANDIDATE/POINTER_UP_CANDIDATE`, сохраняя в отчёте источник границ как pointer-observer; не переименовывать эти события в подтверждённые engine callbacks.
- Считать штрихи по фактически наблюдаемым границам, не удваивая их, если для одного жеста одновременно пришли engine и pointer events.
- Запускать/останавливать FPS probe на pointer fallback, когда engine lifecycle отсутствует; обеспечить отсутствие двойного probe при наличии обоих типов границ.
- Добавить regression tests: pointer-only серия из нескольких штрихов создаёт один run; pre/post exact snapshots дают точный CHALK; stroke count верен; FPS probe связан с run; смешанный engine+pointer поток не удваивает штрихи.
- После CI провести повторный live Firefox тест и проверить появление run JSON и автоматическую привязку к experiment.json.

**CI:** commit 323a698 содержит только session.json. На нём успешно завершились workflow `Brush screenshot measurements` run 17 (`41230071895`) и `Brush centerline measurements` run 29 (`41230071885`). Workflow `Geometry planner tests` для этого commit в списке запусков не обнаружен; успешные профильные workflow не заменяют тесты WebSocket RunRecorder. Исправление и соответствующий regression test ещё не выполнены.


### Исправление pointer lifecycle fallback и результаты CI

После live-диагностики в `game_monitor_bridge_server.py` добавлены резервные границы штриха по pointer candidate events. В run сохраняется `stroke_lifecycle_sources`; `stroke_count` рассчитывается по уникальным stroke IDs, а active duration — по парным границам без повторного учёта. Browser bridge запускает/останавливает FPS probe по engine lifecycle или pointer fallback; функции probe идемпотентны.

Добавлены regression tests:
- pointer-only серия из двух штрихов создаёт один run с exact CHALK delta, правильным stroke_count, длительностью и FPS probe;
- смешанный engine+pointer lifecycle одного stroke ID не удваивает число штрихов и длительность.

Первые CI итерации обнаружили несовпадение идентификаторов в legacy test fixture: начало штриха не содержало strokeId, а завершающее событие содержало. Добавлен безопасный fallback: если активен ровно один штрих, его ID используется для end boundary. Это не создаёт неоднозначности при нескольких активных штрихах.

На commit `a1f8090ea5117785427c643769e8f034b46af391` step `Test local WebSocket smoke server` в workflow `Geometry planner tests` run `41230755334` завершился success, включая новые pointer lifecycle tests. Остальные jobs полного workflow на момент записи ещё выполняются; общий CI пока не объявлен успешным. Live Firefox повтор после исправления ещё не выполнен.


## 2026-10-31 — исправление ложной привязки Game Monitor run

Проверенный артефакт: commit 51028bd86b85b17da31256cd273c0857b100fec4, session 21dc06a5-27fa-4ab7-9d2c-4f29e27b6a9f.

Хронология:
- executor paint_consumption_long_lines: 6/6 штрихов, 29.796 s, 1524 move calls; 18:50:15–18:50:45 UTC;
- привязанный bd8ca817: 1 штрих, 3 события, 0 accepted samples, CHALK 0; 18:50:16.612–18:50:20.065 UTC;
- поздний fbcd2b1b: 9 штрихов, смешанные радиусы, sampled pointDelta 47, CHALK inconclusive из-за pointCount 721→48; 18:52:11–18:52:22 UTC.

Пояснение пользователя: сначала был выполнен автоматический тест из UI, затем доска вручную очищена вне программы, после чего выполнены случайные ручные линии (3 горизонтальные кистью 30 и 3 вертикальные кистью 1). Ручные линии не являются частью плана тестирования и не добавляются в TEST_CASES. Run fbcd2b1b не должен связываться с experiment.

Причина дефекта: _schedule_bridge_report_capture() выбирал первый подходящий по mtime run, используя только нижнюю границу before_draw и совпадение радиуса. Он не сверял фактическое время executor, плановое количество штрихов и однозначность кандидата.

Изменения кода:
- добавлен select_execution_monitor_run() с временным окном executor, допусками -1 s/+5 s, совпадением радиуса, единственностью фактического радиуса и точным количеством ожидаемых штрихов;
- произвольный выбор по mtime удалён;
- при нескольких кандидатах или отсутствии полного соответствия manifest получает monitor_capture.status=unavailable с причиной/диагностикой, отчёт не копируется;
- добавлен is_exact_positive_chalk_measurement(): CHALK считается пригодной для статуса saved только при exact, положительной и согласованной дельте post - pre = consumed_points;
- ручные события за пределами executor window не могут попасть в эксперимент.

Тесты: добавлены unit tests на корректный выбор среди старых/поздних/неподходящих run, неоднозначность, отсутствие executor timestamps, сброс pointCount и нулевой расход. Это автоматические тесты корреляции, не ручные рисовальные сценарии.

Ограничение/следующий gate: текущая реализация требует один run на всю плановую серию. Если collector создаёт несколько run на один executor, manifest безопасно останется unavailable. Необходимы запуск pytest профильного файла и новый live Firefox тест; до подтверждения точного CHALK нельзя переходить к матрице кистей.



## 2026-10-31 — первый успешный live-тест после исправления автопривязки

Ветка: feature/image-geometry-optimization. Результаты добавлены коммитами a552e5d2a0ea8288e6db1d7f784495ae84e097cb и 7d2ce8e53409d9e3faa6b6246de3e3e8ca79b4a4.

Тест paint_consumption_long_lines, кисть радиуса 1:
- executor completed: 6/6 штрихов, 29.984 s, 1524 move calls;
- Game Monitor run 570ec65b: 6 штрихов, radius 1 only, 1454 events;
- pre pointCount 1, post 719, exact CHALK 718;
- sampled_point_delta_total 718, point_delta_matches_chalk=true;
- 0 dropped events, 0 monitor dropped events, 0 monitor errors;
- frame probe: 1452 samples, average FPS 60.0, median FPS 60.024;
- remaining points 5281 / 6000;
- monitor_capture saved, match_reason matched_executor_window.

Проверка хронологии WebSocket session be40944f-523f-49b1-ba87-5af1875185d0:
- целевой run 19:19:06.367–19:19:34.416 UTC совпадает с executor 19:19:01–19:19:31 UTC с учётом post-finalization окна;
- до него были короткие runs с нулевым расходом, не привязанные к experiment;
- после него run 2984ccc8 19:19:36.719–19:19:41.091 UTC содержит изменение ползунка кисти (радиусы 1..30), 0 pointDelta и 0 CHALK; это не рисование тестового плана и не входит в experiment;
- session закрыта 19:19:41.104 UTC; 1831 messages / 1750 events, sendFailureCount=0, connection_closed=true.

Пользователь сообщил, что после завершения теста сразу выключил мост в PowerShell. По телеметрии мост завершил сессию штатно через несколько секунд после завершающих действий UI; потерь доставки не зафиксировано.

Интерпретация: первое подтверждённое измерение расхода CHALK для радиуса 1 и шаблона из шести длинных горизонтальных линий — 718 points. Это не универсальная константа расхода для других радиусов/геометрий. Траектория остаётся неполной из-за coalesced samples; визуальная paint-meter эвристика inconclusive. Ручные линии в план и тесты не добавлялись.


## 2026-10-31 — планирование контролируемой матрицы CHALK

Проверена текущая ветка `feature/image-geometry-optimization`, последние коммиты и фактический код Brush Test UI. Последний известный HEAD на момент проверки: `2425684ecf495b0e85248bd38da2feaa6ea13dc4`; последние изменения были документационными. Файл `brush_behavior_test_ui.py` содержит сценарий `paint_consumption_long_lines`: шесть горизонтальных линий по 400 px, шаг между линиями 36 px, суммарная длина центральных траекторий 2400 px. Сценарий строит logical-board plan 460×240. UI принимает радиус 1–30, а до executor запрашивает проверку `AutoDrawGameMonitor.status().snapshot.radius`; значит, тестовая геометрия может оставаться неизменной для всей серии.

Подтверждённая исходная точка: радиус 1, 6/6 штрихов, `pointCount 1→719`, точный расход 718 CHALK; sampled pointDelta совпал. Это только одна точка данных, не формула расхода.

Создан активный план `CHALK_RADIUS_MATRIX_PLAN.md`:
- радиусы: 1, 5, 10, 15, 20, 25, 30;
- три повтора каждого радиуса (21 независимый запуск);
- порядок запусков сбалансирован по трём блокам;
- каждый запуск начинается с подтверждённой очистки и отдельного baseline;
- фактический радиус, executor window, шесть штрихов, exact positive CHALK delta и совпадение sampled pointDelta обязательны;
- ручные действия в тестовые данные не включаются.

**Браузерный gate не открыт.** Перед локальными тестами нужно добавить метаданные серии/повтора и контроль полноты измерения в experiment manifest, проверить защиту от повторного использования старых run и покрыть эти изменения unit/regression tests. После этого выполнить локальные Python/bridge tests. Пользователю сообщить отдельно, когда подготовка закончена и требуется запуск Firefox/игры.

## 2026-10-31 — реализация подготовки матрицы CHALK

Ветка: `feature/image-geometry-optimization`.

Реализовано:
- `source/preparation/chalk_radius_matrix.py`: проверка ID серии/блока/радиуса, матричные последовательности, проверка точного CHALK и согласованности experiment ID, запрет повторного использования monitor run, отклонение дубликатов matrix cell, статистика по радиусу/повтору;
- `source/preparation/brush_behavior_test_ui.py`: UI поля серии/блока, запись метаданных в plan/manifest, уникальный experiment ID, cross-link в monitor report/summary, fail-closed при уже привязанном run;
- `source/preparation/tests/test_chalk_radius_matrix.py`: тесты метаданных, run deduplication, точности измерения, experiment identity, статистики и duplicate cell/run;
- `source/preparation/tests/test_brush_behavior_test_ui.py`: проверка сохранения matrix identity в experiment manifest;
- `tests/analyze_chalk_radius_matrix.py`: CLI для агрегации JSON manifests.

Также обновлены `CHALK_RADIUS_MATRIX_PLAN.md`, `BRUSH_MONITOR_AUTOCAPTURE_DESIGN.md`, `docs/PROJECT_STATUS.md`, `docs/TESTS_AND_CI_MAP.md`, `docs/DEPENDENCY_MAP.md`, `docs/MODULE_REFERENCE.md`.

Ключевые изменения кода: `bb91a554`, `953e9e70`, `7a5b1348`, `e07be04a`, `62b9109f`; тесты: `187090d5`, `baeb7be1`, `4aa27a01`; анализатор: `4786483b`. Полная история доступна в git log ветки.

**Проверки:** GitHub combined status на проверенном HEAD не вернул status contexts; отдельный workflow-run API также не показал PR workflow runs. Поэтому успешный CI не заявляется. Локальный pytest в текущей среде не запускался. Live browser tests не запускались. Браузерный gate остаётся закрытым до успешного автоматического тестирования.


## 2026-10-31 — CI gate матрицы CHALK пройден

Проверен workflow run `41235681326` для commit `34535d1a56fce75ae9712d55b662a0abd19de868` в ветке `feature/image-geometry-optimization`.

Итог: `completed / success`. Успешны `geometry-tests`, `executor-tests` и `Windows portable build and startup smoke-test`. В частности, geometry job выполнил проверку синтаксиса Game Monitor, тесты resource snapshot, WebSocket smoke server, preparation/geometry tests и unified-app UI regressions.

Браузерный gate открыт. Пользователю требуется выполнить локальную серию измерений в игре по `CHALK_RADIUS_MATRIX_PLAN.md`. CI не является доказательством расхода CHALK в браузере и не меняет статус единственной live-точки radius 1 = 718.


## 2026-10-31 — автоматическая коррекция радиуса кисти

Разобран дефект: линейная координата ползунка не гарантировала соответствие радиуса. В частности, целевой радиус 5 мог приводить к фактическому 4, а прежний workflow не выполнял автоматическую коррекцию.

Реализован замкнутый цикл:
1. перед началом установки проверяется наличие активной сессии Game Monitor Bridge со свежим heartbeat;
2. после отпускания ползунка UI ожидает следующий heartbeat и читает `bridge_diagnostics.last_monitor_status.snapshot` из активного `session.json`;
3. радиус нормализуется из `currentRadius` (fallback: последний элемент `radius`);
4. при несовпадении обновляется интервал известных точек (радиус/координата) и рассчитывается следующая позиция bounded-secant методом;
5. drag и проверка повторяются максимум 7 раз;
6. только точное совпадение допускает дальнейшее действие; при потере Monitor/ошибке/лимите коррекций тест блокируется.

Реализация: `source/preparation/brush_radius_feedback.py`, изменения `source/preparation/brush_behavior_test_ui.py`. Автоматический ввод значения Monitor пользователем удалён; после точной проверки остаётся только визуальное подтверждение положения ползунка перед запуском executor.

Тесты: `source/preparation/tests/test_brush_radius_feedback.py` покрывает чтение радиуса, fallback, невалидные данные и направление коррекции; `source/preparation/tests/test_brush_behavior_test_ui.py` покрывает mismatch→correction, свежий heartbeat и блокировку/разрешение запуска после Monitor verification.

**Статус:** ожидается CI на актуальном HEAD. Локальный browser test ещё не выполнялся. Полную CHALK-матрицу не запускать до проверки нового замкнутого цикла на коротком тесте радиуса 5.


### Дополнение — тот же дефект в основном Stage6 executor

Поиск всех использований ползунка выявил второй независимый путь: `BrushSliderController` в `source/executor/drawing/color_plan_execution.py`. Он также использовал линейную координату и обновлял `current_value` без проверки игры. Исправление распространено на этот путь, чтобы адаптивные цветные планы и визуальный тест Stage6 не сохраняли исходный дефект.

`BrushSliderController` теперь принимает `monitor_radius_provider`, проверяет фактический начальный радиус, выполняет drag, ждёт два разных свежих heartbeat с одинаковым радиусом и корректирует положение по тому же bounded-secant алгоритму. Фактическая координата сохраняется после успешной коррекции и используется как начало следующего drag. `ColorPlanExecutionHooks` и Stage6 передают общий reader из `brush_radius_feedback.py`.

В `test_color_plan_execution.py` добавлен сценарий: начальное значение 30, целевое 5, первая попытка даёт 4, одна коррекция приводит к 5. Проверяются координаты обоих drag и итоговый current_value. Визуальный тест Stage6 также требует Monitor и проверяет начальный радиус до первого штриха.

**Ограничение:** пока CI не завершился и не выполнен короткий live-тест, нельзя считать коррекцию подтверждённой в браузере. Полную CHALK-матрицу не запускать.



## 2026-11-01 — управление Game Monitor Bridge из Brush Test UI

**Изменения:**
- В «Тест кистей» добавлена кнопка запуска start_game_monitor_bridge.bat в отдельном Windows console window.
- Перед запуском UI запрашивает точный location.origin игрового iframe и отклоняет HTTP, URL с путём/query/fragment и credentials.
- Добавлены кнопки копирования полного game_monitor.js и готового game_monitor_bridge.js snippet с одноразовым токеном активного сервера.
- В game_monitor_bridge_server.py добавлен --snippet-file; токенизированный snippet доступен UI только на время работы сервера и удаляется в finally при остановке.
- Добавлен BAT launcher с проверкой/установкой изолированной зависимости requirements-bridge.txt.
- Добавлены UI regression tests на проверку Origin.

**Безопасность и эксплуатация:** сервер по-прежнему слушает только loopback и допускает только переданный точный HTTPS Origin. Токен не записывается в Git, manifest или постоянные настройки. Окно сервера нужно оставить открытым; остановка — Ctrl+C.

**Проверки:** изменения и тесты внесены в ветку; локальный Windows GUI/Firefox live test и итог GitHub Actions требуют отдельного подтверждения.


### Дополнение — поддержка portable build для WebSocket launcher

После добавления UI-кнопок уточнено, что PyInstaller не включает неимпортируемые companion-файлы Game Monitor автоматически. build_windows.py теперь копирует в portable-root/game_monitor JS Monitor, JS bridge, Python collector, requirements-bridge.txt, BAT launcher и README. Frozen UI определяет каталог через путь к AutoDraw.exe; source UI продолжает использовать source/game_monitor. BAT распознаёт оба layout и принимает явный output directory от UI, чтобы run JSON и heartbeat оставались в общем каталоге Brush Test. 


В app_features.json добавлены идентификаторы game-monitor-websocket-bridge, brush-test-websocket-launcher и brush-test-monitor-snippet-copy. Справочники MODULE_REFERENCE.md и FILE_STORAGE_CATALOG.md дополнены описанием companion-файлов и их расположения в portable-сборке.


## 2026-11-01 — исправление PermissionError при сохранении WebSocket session

Пользователь сообщил: live-тесты радиусов 1 и 5 прошли; при тесте радиуса 10 сервер получил PermissionError: [WinError 5] на операции session.json.tmp -> session.json внутри persist_session(). Этот тест не считать завершённым измерением CHALK.

Анализ game_monitor_bridge_server.py:
- persist_session() вызывался последовательно из одного async handler, поэтому внутрипроцессная конкуренция между этими вызовами не подтверждена;
- фиксированное имя session.json.tmp заменено на уникальное имя для каждой записи;
- добавлена async-функция persist_json_atomically() с атомарным os.replace() и ограниченными повторами PermissionError (экспоненциальная задержка);
- прямой неатомарной записи в целевой файл нет;
- при временной блокировке handler не должен падать: ошибка учитывается в bridge_diagnostics, попытка повторяется на следующем сообщении;
- временные файлы очищаются независимо от результата.

Добавлены два regression tests в tests/test_websocket_smoke_server.py: временные WinError 5 с последующим успешным replace и постоянная блокировка с сохранением прежнего JSON. Изменения кода и тестов находятся в коммитах ee00643c, 28d6482e, 21a55f4d. CI ещё не подтверждён; live повтор радиуса 10 ожидает CI.


## 2026-11-01 — завершена матрица CHALK для радиусов 1–30

**Первичные данные:** коммит `e2af4d0a69e2bd89b610b58678e20e86475cb8d0`.  
**Серия:** `chalk-20261101-023127-b85dbb`.

Проверены все 21 experiment manifest (7 радиусов × 3 блока):
- каждый experiment имеет уникальные experiment/run IDs и корректные matrix metadata;
- `monitor_capture.status=saved`, `chalk_status=exact`, `chalk_counter_consistent=true`;
- `point_delta_matches_chalk=true`;
- 6/6 strokes, только заданный радиус;
- dropped events, monitor dropped events и monitor errors равны нулю;
- baseline pointCount=1;
- executor завершал 6/6 strokes с 1524 move calls.

Измеренный расход CHALK:
- r1: 724, 727, 725 (mean 725.33);
- r5: 725, 722, 725 (mean 724.00);
- r10: 728, 725, 723 (mean 725.33);
- r15: 725, 728, 724 (mean 725.67);
- r20: 726, 725, 723 (mean 724.67);
- r25: 727, 726, 728 (mean 727.00);
- r30: 725, 725, 723 (mean 724.33).

Общий диапазон 722–728; среднее 725.19 CHALK. В рамках только этого фиксированного сценария заметной систематической зависимости расхода от радиуса не выявлено. Средние по радиусам отличаются максимум на 3 CHALK. Не делать вывод о любых геометриях: следующими отдельными сценариями должны стать короткие штрихи, диагонали, кривые и повторное покрытие.

Создан `docs/CHALK_RADIUS_MATRIX_RESULTS.md` с таблицами, нормировкой на штрих/100 логических px, проверками качества, ограничениями и рекомендациями для модели. `CHALK_RADIUS_MATRIX_PLAN.md` переведён в COMPLETED. Плановые 21/21 прогоны закрыты.


## 2026-11-01 — план следующего этапа CHALK: геометрия и sampling

После завершения radius matrix создан `CHALK_GEOMETRY_MATRIX_PLAN.md`:
- G1 — длина/направление/короткие штрихи: 4 сценария × 3 повтора = 12 experiments;
- G2 — сегментация/повороты/замыкание/перекрытие/пересечения: 6 сценариев × 3 повтора = 18;
- G3 — скорость и sampling: 9 комбинаций `point_step_px × point_delay_ms` × 3 повтора = 27.

Итого план содержит 57 экспериментов с последовательными gates. Перед браузерной серией нужно расширить matrix metadata за пределы единственного radius-сценария и реализовать проверку per-stroke CHALK по `strokeId`; сумма per-stroke `pointDelta` должна совпадать с точным общим engine counter. Если полнота телеметрии не подтверждается, разбивка по штрихам должна оставаться incomplete и не использоваться для формулы.

План связан в `docs/README.md` и установлен активным следующим этапом в `docs/PROJECT_STATUS.md`. Live-запуски G1 пока не начинались.


## 2026-11-01 — инфраструктура CHALK geometry matrix прошла CI

Исправлена ошибка `NameError` при формировании matrix record: validated `geometry_signature` теперь явно извлекается из проверенных metadata перед записью. Источник значения — повторно построенные и валидированные ожидаемые metadata, а не произвольное поле входного документа.

**Проверка:** commit `8e7b2f8e8c4a65bbbb2d4c6a1a2a603e752fefff`; GitHub Actions workflow run `41256989852` завершён `completed/success`. Успешны все jobs: `geometry-tests`, `executor-tests`, `Windows portable build and startup smoke-test`. Ветка `feature/image-geometry-optimization` на момент проверки указывала на этот commit.

**Статус серии:** инфраструктура G1/G2, analyzer, проверка полноты per-stroke breakdown и автоматическая проверка завершены. G1 готова к live-сбору после обновления локальной ветки и запуска AutoDraw, Game Monitor Bridge и игрового iframe. Ни один G1 live experiment этой записью не считается выполненным. G2 и G3 остаются закрытыми до анализа предыдущих серий.

## 2026-11-01 — инвентаризация результатов тестов и безопасной очистки data

Создан `docs/DATA_CLEANUP_INVENTORY_2026-11-01.md` и добавлена ссылка в `docs/README.md`.

Инвентаризация основана на текущих manifests, анализаторах и storage documentation, а также на ранее зафиксированных Git-tree audits:
- рассмотрены ранние brush experiments 29–30 октября, boundary probe, WebSocket smoke artifacts и семь экспортов Monitor 0.1.2;
- отдельно выделены 21 валидный CHALK radius experiment серии `chalk-20261101-023127-b85dbb`; их первичные файлы и `monitor_report.json` сохраняются;
- учтены требования нового G1/G2 analyzer: per-stroke breakdown требует исходного `monitor_report.json`, а summary не заменяет event stream;
- описаны условно удаляемые runtime/snippet/empty-placeholder файлы и кандидаты на дедупликацию PNG и Monitor run JSON.

**Результат:** массовое удаление старых экспериментальных каталогов и снимков не обосновано. Условно безопасные кандидаты — только неактивная runtime-копия `data/runtime/current_brush_behavior_test.json`, временный токенизированный snippet после остановки collector и фактически пустые placeholder-файлы после проверки ссылок.

**Ограничения:** фактический объём локального диска, untracked-файлы и все локальные SHA-256 не измерялись; физическое удаление не выполнялось. Первичные результаты и код не менялись.


## 2026-11-01 — проверка live G1 CHALK geometry matrix

**Первичные данные:** commit [b75fe367073c22e818227b1d07ef4abe63a654fb](https://github.com/Kiddos19882/AutoDraw/commit/b75fe367073c22e818227b1d07ef4abe63a654fb). В commit добавлены 12 experiment-каталогов, brush plans, execution reports, Game Monitor run JSON/session и исходные изображения.

**Проверки всех 12 experiment manifests и monitor reports:**
- точный положительный CHALK, baseline `pointCount=1`, согласованный post counter;
- радиус 10 и ожидаемое количество штрихов;
- уникальные experiment ID и Game Monitor run ID;
- нулевые dropped events и monitor errors;
- сумма `DRAW_SAMPLE.pointDelta` по уникальным `strokeId` равна exact CHALK; число strokeId соответствует ожидаемому числу штрихов.

**Измерения:** horizontal 122/124/120 (mean 122,00); vertical 60/61/61 (60,67); diagonal 75/76/76 (75,67); short strokes 19/18/17 (18,00). Средние per-stroke CHALK и первичные суммы по каждому запуску записаны в `docs/CHALK_GEOMETRY_MATRIX_G1_RESULTS.md`.

**Найденная проблема metadata:** все 12 manifests имеют `repeat_index=1`, хотя физически представлены три запуска каждого сценария. Поле `matrix_order_index`, указанное в требованиях плана, отсутствует. Строгая проверка duplicate repeat cell не позволяет принять complete groups. Первичные manifests и reports не изменялись; автоматическая перенумерация не выполнялась.

**Документация:** добавлен `docs/CHALK_GEOMETRY_MATRIX_G1_RESULTS.md`; обновлены `CHALK_GEOMETRY_MATRIX_PLAN.md`, `docs/PROJECT_STATUS.md` и индекс `docs/README.md`.

**Статус / следующий шаг:** individual captures и per-stroke breakdown подтверждены, но G1 не закрыта до разрешения metadata blocker и повторной проверки analyzer. G2/G3 остаются закрытыми. Никакие экспериментальные данные не удалялись.

## 2026-11-01 — аудит и исправление repeat metadata для CHALK G1/G2

**Причина:** в Brush Test UI `matrix_block_var` создавался с `StringVar(value="1")`; поле было обычным Entry. При создании DrawingPlan код передавал `int(self.matrix_block_var.get().strip())` непосредственно в `repeat_index`. Автоматического инкремента и проверки ранее сохранённых ячеек не существовало. Следовательно, три прогона одного сценария могли все получить repeat_index=1, если значение поля не меняли. По исходникам нельзя доказать, что именно пользователь вводил в интерфейс, но программная причина отсутствия защиты подтверждена.

**Дополнительная проверка первичных данных:** 12 G1 manifests относятся к одной series ID; внутри каждого сценария есть три последовательных запуска с уникальными experiment ID и Game Monitor run ID. У всех точный CHALK и валидный per-stroke breakdown. Все исходные значения `repeat_index=1`, `matrix_order_index` отсутствует. Ни один raw manifest/report не изменён.

**Исправления:**
- добавлен `inspect_chalk_matrix_series()` для сканирования уже сохранённых manifests, проверки repeat cell и вычисления следующего порядкового номера;
- UI блокирует повторное использование ячейки `series_id + scenario_id + repeat_index`;
- metadata теперь содержит автоматически назначаемый `matrix_order_index`;
- анализатор валидирует `matrix_order_index`, когда он есть, и сохраняет обратную совместимость с legacy manifests;
- добавлены unit tests для duplicate guard, следующего индекса и manifests без нового поля.

**Изменённые файлы:** `source/preparation/chalk_experiment_matrix.py`, `source/preparation/brush_behavior_test_ui.py`, `source/preparation/tests/test_chalk_experiment_matrix.py`.

**Коммиты:** `afb5076c6de3f1eb6b42057d1830e1e7320b32d6`, `32d145ef9874be8e936ee411ec5bc2a96723a5b9`, `dc4100a22b0ebab576af22480b992449cbe2c8dd`, `e03e71ee9b285a896b039de12becf80aad5596a6`, `5771f52554c3356c54d451e0ab26e99c6a7524a8`.

**Проверка:** GitHub Actions workflow `41261159618` для HEAD `5771f52554c3356c54d451e0ab26e99c6a7524a8` был поставлен в очередь; итог ещё не подтверждён на момент записи.

**Статус:** кодовая причина повторного использования repeat index устранена для будущих запусков. Принятие уже собранной G1 остаётся отдельной задачей: требуется auditable reconciliation sidecar или повторное измерение. Никакие первичные данные не переписывались и не удалялись. G2/G3 остаются закрытыми.
## 2026-11-01 — проектирование и ядро автоматических блоков CHALK

Оператор указал на риск ручного запуска каждого сценария и ввода repeat index: можно пропустить линию/тест, выполнить неверное число повторов или забыть сохранить capture. Решено перейти к блочному запуску: один запуск блока автоматически покрывает все сценарии фазы и три независимых повтора.

Добавлен `source/preparation/chalk_test_blocks.py`:
- G1 генерирует 12 задач (4 сценария × 3 повтора), G2 — 18 (6 × 3);
- порядок задач детерминированно перемешивается фиксированным seed;
- каждая задача содержит scenario/repeat, expected stroke count, radius 10, executor config и matrix_order_index;
- создаётся отдельный JSON journal, существующий журнал не перезаписывается;
- следующий тест можно claim только при отсутствии другого running task;
- failed/interrupted задача ставит весь блок на паузу; автоматического пропуска или повторного запуска нет;
- при восстановлении незавершённый тест маркируется interrupted, поскольку неизвестно, успела ли игра принять часть штрихов.

Добавлены `source/preparation/tests/test_chalk_test_blocks.py` и `docs/CHALK_TEST_BLOCKS_DESIGN.md`; обновлены `docs/README.md`, `docs/TESTS_AND_CI_MAP.md`, `docs/BRUSH_MODULE_QUICK_INDEX.md`.

**Граница реализации:** в этой итерации создано ядро планирования/журналирования и его unit tests. UI-кнопки, автоматическое выполнение полного блока и переход между опытами ещё не подключены. Никакие live-эксперименты не запускались; G1/G2/G3 status gates не менялись; первичные результаты не изменялись.

## 2026-11-01 — UI runner автоматических блоков CHALK

Реализована первая интеграция block scheduler с Brush Test UI.

**Интерфейс:**
- добавлены выбор G1/G2, кнопка запуска полного блока, безопасная остановка после текущего опыта и строка прогресса;
- план всех задач и journal сохраняются в `data/results/brush_behavior_tests/chalk_test_blocks/` до первого mouse action;
- серия блокируется, если ID уже встречается в manifests или незавершённом журнале;
- G2 недоступна, пока не найден завершённый G1 block journal со всеми 12 принятыми задачами.

**Lifecycle:**
- автоматическая последовательность использует существующие preclear, blank-board reference, brush drag feedback, executor callback, Game Monitor correlation, postdraw capture и brush restore;
- при пакетном запуске не запрашивается повторное подтверждение Clear и визуальное подтверждение каждого одинакового радиуса; исходное предупреждение о стирании тестовой доски показывается один раз на блок, радиус при этом каждый раз подтверждается свежими heartbeat;
- переход к следующему опыту происходит только после проверки manifest, точного CHALK, уникального Monitor run, согласованного pointDelta, чистых frame/trajectory diagnostics и полного per-stroke breakdown по strokeId;
- failed/incomplete/timeout gate приостанавливает блок, не засчитывает попытку и не пропускает задачу;
- Stop действует на границе опыта; Alt/ошибка во время текущего запуска приводит к fail-closed остановке.

**Новые проверки:** добавлены тесты строгого acceptance gate (incomplete per-stroke, frame probe interruption) и безопасной остановки блока только между задачами.

**Изменённые файлы:** `source/preparation/chalk_test_blocks.py`, `source/preparation/tests/test_chalk_test_blocks.py`, `source/preparation/brush_behavior_test_ui.py`.

**Ограничения:** recovery UI для running/interrupted journal после перезапуска ещё не сделан; нет полного набора callback integration tests; CI/Windows portable smoke test ожидаются. Live G1 не запускался. Существующие raw manifests и `data/` не изменялись.


**Дополнительная защита журнала:** перед первым mouse action текущая попытка теперь получает в journal конкретные `experiment_id` и абсолютный `experiment_dir`. Это сохраняет ссылку на частично выполненный опыт при аварийном закрытии приложения. Добавлен unit test на регистрацию и запрет повторной перезаписи identity активной попытки.


## 2026-11-01 — recovery UI автоматических блоков CHALK

Добавлено восстановление долговечных block journals:
- при запуске Brush Test обнаруживается журнал в состоянии running; активная задача переводится в interrupted и не воспроизводится автоматически;
- оператору показываются task ID, experiment ID, experiment directory и путь журнала;
- кнопка восстановления требует явного подтверждения ручной проверки игровой доски перед повторной попыткой;
- повтор создаёт новую attempt, предыдущая interrupted attempt остаётся в истории;
- ready journal после аварийного закрытия можно продолжить с первой pending-задачи после явного подтверждения тестовой доски;
- failed/paused journal нельзя повторить автоматически; его можно закрыть после подтверждения проверки доски, сохранив все попытки;
- параллельный запуск блоков запрещён при любом unresolved journal.

Добавлены unit tests для явного recovery decision, обязательного board_checked и закрытия interrupted блока. Полный UI callback-level test matrix и CI остаются открытыми.


## 2026-11-01 — regression tests переходов Brush Test block runner

Добавлен `source/preparation/tests/test_chalk_test_block_ui_workflow.py`:
- задача отмечается completed и следующая может стартовать только после положительного строгого acceptance gate;
- incomplete per-stroke evidence вызывает pause и не вызывает переход;
- capture timeout завершает gate fail-closed;
- executor failure не запускает postdraw и приостанавливает блок.

Это первые callback-level tests. Полная матрица отказов preclear, brush drag/feedback, bridge loss, restore, Stop и startup recovery ещё требует расширения. CI результата для текущего HEAD пока нет; live G1 не запускался.


## 2026-11-01 — дополнительная проверка Stop/restore/G1 acceptance

В процессе повторной проверки обнаружен UI edge case: если остановка блока между задачами не могла записать terminal state журнала (например, временная ошибка диска), runtime очищался без сохранения recovery pointer. Исправлено: путь такого журнала сохраняется для явного восстановления, ошибка показывается оператору.

Дополнены callback tests:
- brush restore failure приостанавливает блок и не допускает capture acceptance;
- только завершённый drag вызывает capture acceptance gate;
- ошибка safe-stop сохраняет ссылку на журнал для восстановления;
- G2 остаётся закрытой, пока все 12 G1 задач не имеют completed state.

Проверить тесты локально в этой среде не удалось: сетевое клонирование репозитория недоступно. GitHub Actions для последнего SHA нужно подтвердить отдельно; пустой combined status и PR-only workflow lookup не являются доказательством успешного CI.


## 2026-11-01 — разбор CI и закрытие Alt-cancel recovery edge cases

Проверен GitHub Actions run [41265149825](https://github.com/Kiddos19882/AutoDraw/actions/runs/41265149825) для HEAD `36b32dbc4cad3e6e5aabea07136e25f949f9bf43`. Workflow завершился с failure:
- `executor-tests` — success;
- `geometry-tests` — 8 failed, 556 passed, 24 warnings; ошибки находились в тестовых фикстурах и тестовых ожиданиях, а не в runtime-поведенческой логике;
- `Windows portable build and startup smoke-test` — build остановился на Stage 13 preparation test suite с теми же ошибками, поэтому сам startup smoke-test не был достигнут.

Исправления тестов в ветке `feature/image-geometry-optimization`:
- добавлены недостающие поля `current_plan` и `_chalk_block_task` в UI controller fixtures;
- acceptance-validator fixtures теперь соответствуют контракту валидированного record (`expected_strokes`, `consumed_points`);
- timeout test переводит monitor capture в `pending` и проверяет соответствующую причину timeout.

При дополнительном review найден runtime edge case: Alt отменял автоматический preclear или postdraw, но не переводил активную block task в failed/paused. Журнал мог оставаться в состоянии running до перезапуска приложения. Исправлено: отмена через Alt теперь вызывает fail-closed остановку блока с причинами `preclear_cancelled_by_user` / `postdraw_cancelled_by_user`. Добавлены два callback workflow tests, проверяющие, что journal становится paused, задача — failed, причина сохраняется и автоматического перехода нет.

Тестовое покрытие блока теперь: 13 unit tests ядра и 10 callback workflow tests. Исчерпывающая матрица callback failure paths ещё не завершена. Последний проверяемый кодовый commit — `609aca9156e5eb136c7db5cb516262b971d4fa82`; GitHub Actions run `41266047330` для него запущен, результат на момент этой записи не подтверждён. Локальный запуск тестов в текущей среде недоступен. Live G1 не запускался.


## 2026-11-01 — CI success и привязка capture acceptance к block task

**CI:** run [41266047330](https://github.com/Kiddos19882/AutoDraw/actions/runs/41266047330) для commit 609aca9156e5eb136c7db5cb516262b971d4fa82 и run [41266141717](https://github.com/Kiddos19882/AutoDraw/actions/runs/41266141717) для f8f2d1c6fe47b8d5e539be78951cea16296e16f6 завершились успешно. Последний запуск подтвердил geometry-tests, executor-tests, Windows portable build и startup smoke-test.

**Дополнительный аудит:** найдено, что capture acceptance проверял внутреннюю целостность manifest, но не сравнивал его идентификаторы с активной задачей block journal. Теперь валидатор получает ожидаемые task/block/experiment identity и сравнивает block_id, task_id, experiment_id, series_id, phase_id, scenario_id, repeat_index, requested_radius, expected_strokes, matrix_order_index и executor_parameters. При несовпадении возвращается отказ и UI ставит блок на паузу.

**Тесты:** добавлены шесть parameterized mismatch cases, positive identity case и проверка, что UI передаёт текущие identity в acceptance validator. Новые commits: d5d3542840138f80df51cc467ca4b91012c18689, 589f25d116f1fadb924aa2d773da22515e17b001, 9576a97c4cc84fe8b139743dcf20b46eec5fece3, b63b7170f758c26016d46092ea5dc90fea1337fb.

**Статус:** CI для task-identity hardening ещё не получен. Live G1 не запускался. Raw manifests, data/ и ветка master не изменялись.


## 2026-11-01 — проверка persisted experiment path и отказа preclear

Дополнена привязка capture acceptance: UI теперь извлекает активную задачу и текущую попытку из сохранённого block journal; experiment_id и experiment_dir берутся из записи этой попытки. Валидатор сравнивает canonical path каталога manifest с зарегистрированным experiment_dir. Отсутствующая/неактивная задача или попытка, не зарегистрированный каталог либо несовпадение identity ведут к отказу без перехода к следующему тесту.

Добавлен callback test, моделирующий неуспешную проверку очистки доски: block journal становится paused, текущая задача failed, executor не запускается. Изменения кода/тестов: 14d112e4b4ea22ea26b47c5850863cd30f4c146b, 02d0e308681fc626bcf1bc56b898864e17df1597, df756c9ce8e2a9403a1b00dd001b593959e5d22a, eda6f6462747ce3999a882995b50f69e558985d7, 95d3ab6c6f782340785ceaf4c534951c1f648c8b.

GitHub Actions для новых изменений выполняется/ожидает очереди; итог ещё не подтверждён. Live G1 не запускался.


## 2026-11-01 — разбор CI и исправление callback test stub

Проверены workflow runs `41267183785` (кодовый/test commit `95d3ab6c6f782340785ceaf4c534951c1f648c8b`) и `41267241966` (документированный HEAD `cce3d38d99920f787c2ea8dd63c88caf2c883c54`). В обоих запусках `executor-tests` прошёл; `geometry-tests` завершился с 1 failed / 574 passed, а Windows portable build остановился на той же Stage 13 preparation suite до startup smoke-test.

Причина единственного падения — устаревшая lambda-подмена `validate_chalk_block_experiment` в `test_ui_capture_gate_pauses_without_advancing_on_incomplete_evidence`: UI корректно передаёт новые keyword-only identity аргументы (`expected_task`, `expected_block`, `expected_experiment_id`, `expected_experiment_dir`), а тестовая lambda принимала только путь. Обновлена подмена до `lambda _path, **_kwargs`, сохраняя проверку отказа на incomplete evidence. Изменение: commit `20704ab984b981a4bf5b2278eba6cfad970d15a5`.

Для нового commit combined status пока не содержит checks; CI результата после исправления ещё нет. До полного успешного CI и Windows startup smoke-test live G1 не запускать. Raw manifests, `data/` и `master` не изменялись.


## 2026-11-01 — завершение CI и аудит целостности block journal

После исправления callback test stub полный workflow run [41268085571](https://github.com/Kiddos19882/AutoDraw/actions/runs/41268085571) для code commit `20704ab984b981a4bf5b2278eba6cfad970d15a5` завершился успешно: geometry-tests, executor-tests и Windows portable build/startup smoke-test — success. Документационный HEAD `1c7bf1501347df981f6a664e3bf057a54953a4c9` также прошёл все три job в run [41268149629](https://github.com/Kiddos19882/AutoDraw/actions/runs/41268149629).

**Review recovery/journal:** выявлено, что загрузчик проверял только верхний уровень JSON. Синтаксически корректный, но структурно повреждённый журнал (например, несловарная задача, дублированный task_id, orphaned running attempt, несколько running задач или несогласованный статус блока) мог приводить к исключениям глубже в UI recovery/state transitions. Добавлен централизованный структурный validator в `chalk_test_blocks.py`: проверяются schema/phase/block status, ожидаемое количество задач, уникальность task_id/attempt_id, допустимые статусы, связь active_attempt_id с единственной running attempt, максимум одна running task, согласованность статуса блока и полное завершение всех задач для completed block. Некорректный JSON теперь выдаёт ValueError с путём журнала; recovery уже трактует это как unresolved и не запускает тест.

Добавлены тесты на повреждённые структуры, несогласованные статусы, orphaned/multiple running attempt, invalid JSON и корректную активную попытку. Code commits: `2ea67817bd1187baa66252aec440a4a5238042e0`, `52b40e94eadf1e75f461565960547b2a749993e4`.

Оставшиеся границы: файловый журнал рассчитан на единственный активный экземпляр UI; межпроцессная блокировка claim/write не реализована. Повреждённый журнал намеренно блокирует новый блок и требует ручного сохранения/разбора файла, а не автоматического исправления. Live G1 не запускался; ожидать новый CI для journal validation. `data/`, старые manifests и `master` не изменялись.


Дополнительный defensive review сразу после первого CI запуска выявил, что membership check по set мог выбросить TypeError, если JSON содержал list/dict в поле status или phase_id. Это также может обойти ожидаемую обработку ValueError в recovery UI. Исправлено явной проверкой string type до проверки допустимого значения; добавлены cases с unhashable значениями. Commits: `732128bfa62160ce6811e3925f371ab87f5f08d0`, `ff3e675fb09a5b05cceba75892469b87ba526fef`. Все journal-validation изменения теперь требуют CI на финальном code SHA.


**CI feedback и коррекция:** Windows packaging run `41269156105` обнаружил SyntaxError в validator: при добавлении явных type checks в файл попала буквальная последовательность `\\n` вместо переноса строки. Это ошибка внесённого изменения, не исходного кода проекта. Исправлено в commit `dd5aaade3b790546d9e3fc11341554f6aa09d8ec`. Повторный полный CI для исправленного SHA обязателен; до него journal validator не считается проверенным.


## 2026-11-01 — согласованность статусов и отказоустойчивость записи журнала

По разрешению пользователя продолжена подготовка автоматического G1.

В source/preparation/chalk_test_blocks.py расширена fail-closed проверка согласованности статусов:
- ready допускает только pending/completed задачи;
- paused требует failed/interrupted задачу и не допускает running;
- failed требует failed задачу и не допускает running;
- completed требует, чтобы все задачи были completed;
- stopped не может содержать running задачу.

Статус failed добавлен в список unresolved журналов UI, чтобы нештатное завершение не разрешало новый блок.

Все изменяющие журнал read-modify-write операции и создание журнала обёрнуты межпроцессной блокировкой advisory lock (msvcrt на Windows, fcntl на POSIX). Это предотвращает одновременную выдачу одной pending-задачи и потерю обновлений при конкурентных транзакциях. Lock-файл постоянный и не должен удаляться вручную. Ограничение: блокировка действует на время каждой транзакции; один активный block journal по-прежнему должен обслуживаться одним экземпляром AutoDraw.

Добавлены тесты:
- несогласованные сочетания статуса блока и задачи;
- отказ записи временного файла;
- отказ os.replace с подтверждением сохранности исходного журнала;
- наличие и использование стабильного lock-файла.

Коммиты кода/тестов: e688ed5b893903794afdf306c3b8db955e578639, dc21778fff4fc8ef8d47525d93ac00fde784eb78, 0d2d4182d9d418a274a69dcaa1ee9495a48e012d, 9147bbdfa8419a77481d093bb0669c05e4ab640a.

Новый CI для этих изменений обязателен; live G1 не запускать до успешных geometry-tests, executor-tests и Windows portable build/startup smoke-test. master, data/ и исторические manifests не изменялись.


## 2026-11-01 — эксклюзивное владение блоком и безопасный recovery

Устранён риск, при котором второй экземпляр AutoDraw мог принять ещё работающий блок за прерванный. Добавлен отдельный lifetime owner lock для каждого block journal: Windows msvcrt non-blocking lock, POSIX flock LOCK_NB. UI удерживает lock в течение всего активного блока, recovery-сеанса или закрытия журнала. При старте второго экземпляра занятый lock означает, что journal не меняется и running-задача не переводится в interrupted. После завершения владельца ОС автоматически освобождает lock; новый экземпляр получает его и выполняет recovery.

Recovery resume/close теперь также требуют владения lock. Закрытие failed journal, как и paused, требует явного подтверждения проверки доски. Добавлены unit и UI workflow tests на эксклюзивность owner lock и отказ второго экземпляра менять живой running journal.

Коммиты: 9c709c5a597ebcb968419839d2dfc4af9b1a2bd3, 4c80d167ae28ea3327e71813a3db0c03a5d8e05a, 0d666afb63cb70634d90a25e7b0b87022a0394f2, 1b7486a86d2b19ead81625f9a465aef51b3e3450, 3ba5b4dc1c7a26d4a333592807bda802ceba76c5, 4e0e7809d5eef1235efccc65e2529892e8a81f85, 4d681cdf09c62f65647f651b271b81458ff59e29.

Новый CI для этих изменений обязателен. Live G1 запрещён до успешного полного CI и фактического Windows preflight. Ветка master, data/ и первичные manifests не изменялись.


## 2026-11-01 — единая блокировка каталога

Дополнительно устранена гонка, при которой два экземпляра могли одновременно пройти проверку отсутствия незавершённого журнала, но создать разные journal-файлы с разными именами. Owner lock теперь общий для всего каталога chalk_test_blocks: одновременно допускается только один активный блок на output_dir. Добавлен тест, что второй путь журнала в том же каталоге также не получает lock.


Дополнительный review owner-lock I/O: ошибка создания/открытия .active-block.owner.lock теперь трактуется как отказ получить владение, а не пробрасывается в UI как необработанное исключение. При ошибке unlock дескриптор всё равно закрывается, чтобы ОС освободила блокировку. Добавлен fault-injection test на PermissionError при открытии lock-файла. Commit: 80f5c96f3c601b94c567b6d91435f0c778608bda; test: d44d84f6be5a7daf3aae38ba7e6576f70c138f24.


Добавлен отдельный cross-process test: дочерний процесс через multiprocessing spawn пытается захватить owner lock, удерживаемый основным процессом; ожидается отказ. Это особенно важно для проверки Windows msvcrt locking в CI. Commit: 73af05b495b06b87bf892e93a2fb2d2085c9adad.


Дополнительно: при явном закрытии failed-блока после осмотра доски в recovery_decisions записывается close_failed_block, board_checked=true и timestamp. Commit 6df2644a; test 8d0a949d.

### CI finding — closure audit classification (2026-11-01)
The first final CI run exposed a mismatch: `finish_chalk_block_task(accepted=False)` correctly leaves the block in `paused`, while the rejected task itself is `failed`. Closure audit classification now inspects task statuses, recording `close_failed_block` when a failed task exists and `close_paused_block` for interruption-only pauses. This preserves the distinction between block state and failed experiment state. The existing regression test asserts the failed-task path. Full CI must be rerun; G1 remains blocked until all jobs and Windows portable smoke-test pass.

## 2026-11-01 — финальный CI и готовность программной части G1

Исправлена классификация audit при закрытии paused-блока, если одна из задач имеет статус failed. Решение о закрытии теперь основано на статусах задач: `close_failed_block` для блока с failed-задачей и `close_paused_block` для interrupted-only состояния. Изменение: `dd976b04f6d6423726ad7382bac7223c12d8342b`.

Финальный workflow run `41272291546` на HEAD `311299296559b9a5949f1e803f134b46436a2850` завершился success. Все jobs прошли: geometry-tests, executor-tests, Windows portable build/startup smoke-test. Windows job завершил полный `build_windows.bat`, включая общий набор тестов, сборку portable приложения и smoke-test запуска.

Обновлены PROJECT_STATUS.md, TASKS.md и CHALK_TEST_BLOCKS_DESIGN.md. Программный gate G1 закрыт. Не выполнено и не имитировалось: локальное открытие portable приложения в пользовательской Windows, проверка текущего профиля калибровки/игровой сессии/пустой доски и live G1. Эти действия остаются обязательным локальным preflight.

## 2026-11-01 — live G1, диагностика capture gate и уведомление завершения

Пользователь выполнил два автоматизированных G1 прогона. Первый journal chalk-20261101-075204-f43b0d остановился после двух принятых задач: задача vertical_lengths-r1 получила monitor_capture_gate_timeout:unavailable, девять следующих задач остались pending. Второй journal chalk-20261101-080012-4d6add завершён; все 12/12 задач приняты.

Проверка второго блока:
- Vertical: 62/61/60 CHALK, mean 61.00.
- Horizontal: 124/123/123 CHALK, mean 123.33.
- Diagonal: 76/77/75 CHALK, mean 76.00.
- Short: 18/19/18 CHALK, mean 18.33.
- Всего 836 CHALK по 12 отдельным опытам; каждый run имеет точный baseline/post counter, совпадающий pointDelta, radius 10, ноль dropped events и monitor errors.

Первый отказ оказался ложным mismatch по количеству pointer candidates. Raw run ba6cf902-b635-442e-809b-e34ed1c7ced2 содержит exact CHALK 60 (pointCount 1→61), sampled pointDelta total 60 и пять candidate IDs. Один ID имел нулевой delta; четыре расходующих штриха имели [4,8,16,32]. Старый matcher считал все пять candidate IDs и не сопоставлял run с ожидаемыми четырьмя штрихами.

Исправления:
1. В RunRecorder stroke_count теперь рассчитывается по уникальным stroke IDs, имеющим положительный DRAW_SAMPLE.pointDelta. Добавлены stroke_candidate_count и non_consuming_stroke_candidate_count для аудита нулевых pointer gestures.
2. _stroke_level_breakdown исключает нулевые кандидаты из числа принятых штрихов, сохраняет их ID в non_consuming_stroke_ids и проверяет ожидаемое число расходующих штрихов и сумму CHALK.
3. В UI добавлено отдельное итоговое messagebox.showinfo при статусе block completed; окно поднимает AutoDraw на передний план и показывает число принятых опытов.

Regression tests добавлены для каждого исправления. Полный GitHub Actions run 41276703424 завершился success на HEAD c8d8c2c5588a0d423e48682962a4213ee725c808: geometry-tests, executor-tests, Windows portable build/startup smoke-test. Windows job: 605 pytest tests passed, 98 unittest tests OK, ALL TEST SUITES PASSED, portable layout и smoke-test запуска пройдены.

G1 принят по второму блоку. G2 теперь разблокирован программной проверкой; следующий этап — G2 (18 задач). Перед ним обновить локальную сборку до проверенного HEAD. G3 остаётся заблокирован до принятия G2. Старый stopped journal и его raw Monitor data сохранены без задней правки.


## 2026-11-01 — live G2 принят, G3 открыт

Пользователь сообщил об успешном прохождении G2 и указал commit `16a426b534de269ed967027bbe59f3daac4b97ec`. Проверен commit на ветке `feature/image-geometry-optimization`; он является текущим HEAD и дочерним для документационного commit `b2969169105a7e080f8115ec8b45c7cd96c68265`.

Проверен block journal `chalk-block-G2-chalk-20261101-084732-a5c2cf-64d2e366.json`: статус completed, 18/18 задач завершены, repeat_index 1/2/3 для каждого из шести сценариев. Для всех 18 experiment.json и monitor_report.json проверены точные CHALK captures, согласованность `post-pre`, сумма `DRAW_SAMPLE.pointDelta`, фактический/ожидаемый stroke_count, радиус 10, ноль dropped events и monitor errors. Все frame probes имеют статус measured.

Результаты по repeat 1/2/3: continuous_closed_contour 339/337/338 (mean 338,00); cross_section_intersections 323/322/322 (322,33); parallel_spacing 444/444/446 (444,67); repeated_coverage 247/245/246 (246,00); long_isolated_lines 393/394/392 (393,00); continuous_turns 214/211/211 (212,00). Сумма 5868 — сумма 18 независимых запусков, а не одного рисунка.

В трёх `repeated_coverage` monitor reports события DRAW_SAMPLE агрегированы по strokeId. Значения по четырём штрихам: [61,62,62,62], [61,61,61,62], [61,61,62,62]. Повторное покрытие не демонстрирует заметной экономии CHALK относительно контрольной параллельной линии в рамках этой геометрии.

Отдельный отчёт: `docs/CHALK_GEOMETRY_MATRIX_G2_RESULTS.md`. G2 принят; G3 разблокирован. Следующий блок — 27 опытов на `paint_consumption_long_lines`, радиус 10, комбинации `point_step_px` 1/2/4 и `point_delay_ms` 5/10/20, по три повтора. Код не изменялся.


Уточнение по G3: live gate открыт после принятия G2, но кодовая поддержка ещё отсутствует. `PHASE_SCENARIOS`, `BLOCK_PHASES` и UI selector на текущем HEAD содержат только G1/G2; matrix metadata/duplicate protection также не учитывают параметры G3. До live-запуска требуется отдельная реализация G3 на 9 комбинаций `point_step_px` × `point_delay_ms` и 3 повтора, затем tests + полный CI + Windows portable smoke-test. Экспериментальный план G3 не меняется.

## 2026-11-01 — программная реализация G3

Начата реализация G3 на `feature/image-geometry-optimization` после live acceptance G1 (12/12) и G2 (18/18).

Изменения:
- Matrix metadata поддерживает фазу G3, шесть ожидаемых штрихов и полную конфигурацию executor.
- Уникальность G3 repeat cell учитывает `point_step_px`, `point_delay_ms` и `repeat_index`.
- Block runner строит 27 задач, детерминированно перемешивает их и валидирует полный набор ячеек в журнале.
- Brush Test UI показывает G3 и разрешает запуск только после завершённого G2.
- Интеграция Stage6 принимает временный executor config override; параметры применяются к реальному `MouseExecutor`, попадают в execution report и не записываются в пользовательский профиль.
- Analyzer разделяет статистику по каждой из девяти конфигураций и проверяет совпадение executor report с metadata.
- Добавлены regression tests для матрицы, журнала и workflow override.

На момент этой записи CI ещё не подтверждён. Live G3 не запускался. Экспериментальная спецификация не менялась.

### Дополнение к реализации G3 — финальные ограничения запуска

Добавлена защита от обхода полного блока: сценарий `paint_consumption_long_lines` нельзя запускать вручную вне G3 block runner. Runtime handoff дополнительно сверяет scenario_id, радиус, ожидаемые шесть штрихов, разрешённые целочисленные значения шага/задержки и неизменность остальных executor settings. Это предотвращает подмену G3 metadata перед передачей плана исполнителю.

Текущий кодовый HEAD после этого исправления: `f50b14d1a8389d259e17940a4e54cfa9f81a042c`. Полный CI пока не подтверждён; live G3 не запускался.

### Финальная фиксация программного gate G3

Дополнительно ужесточена journal validation: для всех 27 задач проверяются целочисленные repeat_index и matrix_order_index, уникальность каждого matrix_order_index в диапазоне 1–27, а также полный набор девяти parameter cells. Добавлены regression tests для boolean repeat и повторного порядка.

Ручной запуск `paint_consumption_long_lines` вне полного G3 block запрещён. Runtime handoff проверяет сценарий, радиус 10, шесть штрихов, полный набор executor-параметров и допустимые значения 1/2/4 × 5/10/20.

Актуальный кодовый HEAD: `5a63fcbcbd86a441499567a2572d8c967d845371`. G3 software implementation и regression coverage внесены. Полный CI/Windows portable smoke-test не удалось подтвердить через доступные результаты GitHub Actions; live G3 не запускался.


## 2026-11-01 — G3 software gate закрыт

**Проверенный HEAD:** `e1872af08efbff7ee7c9ac771e6b9eb70b748c46`  
**GitHub Actions run:** [41337768801](https://github.com/Kiddos19882/AutoDraw/actions/runs/41337768801) — `completed / success`.

Успешно завершены все три обязательных jobs:
- `geometry-tests` — success; включая syntax checks Game Monitor, WebSocket smoke server, preparation/geometry tests и unified-app UI regressions.
- `executor-tests` — success; executor regression tests.
- `Windows portable build and startup smoke-test` — success; portable build и smoke-test запуска.

В процессе подготовки CI были найдены и исправлены три дефекта:
1. Лишняя закрывающая фигурная скобка в `source/preparation/chalk_experiment_matrix.py` — commit `bf52f12ece873908f256f12f475faef6e31465ea`.
2. Тесты executor override в `tests/test_unified_app.py` находились вне unittest-класса, а `unittest.main()` стоял до них — commit `6594e28c96a70b421d96e3e90434ac3104d6a196`.
3. Docstring в `source/preparation/chalk_experiment_matrix.py` закрывался двумя кавычками вместо трёх — commit `e1872af08efbff7ee7c9ac771e6b9eb70b748c46`.

**Статус:** G3 software gate закрыт. Успешная автоматическая Windows portable smoke-проверка не заменяет локальный preflight на пользовательской машине и не является live CHALK измерением. Live G3 ещё не запускался; фактические расходы краски по девяти конфигурациям отсутствуют и не должны моделироваться предположениями.

**Следующий шаг:** локально запустить проверенную portable-сборку на Windows, проверить калибровку кисти, Clear/чистую доску, игровую canvas и heartbeat Game Monitor. После подтверждения preflight выполнить полный G3 block из 27 задач; не запускать задачи вручную по отдельности.


## 2026-11-01 — удалено визуальное подтверждение размера кисти после Game Monitor

По замечанию оператора устранены два последовательных диалога, которые требовали визуально подтвердить радиус после автоматической установки:
- `integrated_app.py::_start_brush_test_executor` больше не спрашивает пользователя, совпадает ли размер кисти с запрошенным;
- `BrushBehaviorTestTab._confirm_brush_before_test` больше не показывает `askyesno` после точного подтверждения Game Monitor.

Проверка не ослаблена: executor допускается к запуску только после свежего heartbeat Game Monitor с точным совпадением фактического радиуса и запроса. В handoff добавлена повторная fail-closed проверка `observation.radius == requested_brush`; при расхождении запуск блокируется. Источник проверки и факт автоматического подтверждения сохраняются в `experiment.json`, поле `visual_confirmation_required=false`. Потеря Monitor, отсутствие свежего heartbeat, несовпадение радиуса, ошибка коррекции или записи manifest по-прежнему останавливают тест.

Для G1/G2/G3 block runner это убирает лишний popup после каждого автоматического drag; Clear/blank-board и остальные обязательные предупреждения не затрагивались. Добавлены regression tests: точный Monitor radius запускает callback без диалога, mismatch блокирует handoff.

Изменения в commits: `bb32589cb9d450a03b1d5b5264732828812b8ed3`, `465346a58caf76b8566d99128361095324368366`, `c919610999c5ea9f4a1afebad937395e586dc4b9`. Требуется новый полный CI на изменённом HEAD; до его завершения успешный CI предыдущего G3 HEAD не распространяется на эти изменения.


Дополнительная регрессия: в `tests/test_unified_app.py` добавлен интеграционный тест, который вызывает handoff основного приложения и падает, если перед запуском executor будет показан `messagebox.askyesno`. Commit: `8c93a498864973b9879c926627030bb7e1d3ce2a`. CI run [41340056751](https://github.com/Kiddos19882/AutoDraw/actions/runs/41340056751) был создан до этого последнего тестового commit, поэтому его результат не будет считаться окончательной проверкой текущего HEAD; требуется run по актуальному PR head.


## 2026-11-01 — финальный CI G3 на актуальном HEAD и синхронизация статуса

**Рабочая ветка:** `feature/image-geometry-optimization`  
**Проверенный HEAD:** `3dbf8f20bcea44c61290e49398e1a4daf182dbf9`  
**GitHub Actions:** [run 41340237207](https://github.com/Kiddos19882/AutoDraw/actions/runs/41340237207)  
**Workflow:** `.github/workflows/geometry-tests.yml` — `Geometry planner tests`.

Run завершился `completed / success`; все три jobs прошли на одном и том же HEAD:
- `geometry-tests` — success. Включая Game Monitor JS syntax/resource snapshot, WebSocket smoke server, benchmark/validation steps, preparation/geometry suite, Stage 7 validator, import diagnostics и unified-app UI regressions.
- `executor-tests` — success.
- `Windows portable build and startup smoke-test` — success; шаг portable build/startup завершился успешно.

Важное уточнение истории: предыдущий run `41340056751` не был окончательной проверкой последнего интеграционного теста. Актуальный run `41340237207` имеет точный `head_sha=3dbf8f20bcea44c61290e49398e1a4daf182dbf9`, включая commit `8c93a498864973b9879c926627030bb7e1d3ce2a` с regression test основного приложения. Прежние записи о необходимости нового CI теперь закрыты этим run.

Workflow настроен на:
- push в `feature/image-geometry-optimization`;
- pull_request с path-фильтром по production/test/build/docs-наборам, перечисленным в YAML;
- ручной `workflow_dispatch`.

PR #3 использован как временный CI-only PR с base `ci/g3-validation-base`; он остаётся открытым и не должен сливаться. `master` не изменялся.

**Статус gate:** G3 software/CI gate закрыт на указанном HEAD. Это не означает выполнения live G3. Не выполнены локальный Windows preflight и 27 live captures; фактическая зависимость CHALK от `point_step_px` и `point_delay_ms` ещё не измерена. Следующий этап — локальный preflight, затем полный последовательный G3 block 27/27.

**Синхронизация:** обновлены PROJECT_STATUS, TASKS, CHALK_TEST_BLOCKS_DESIGN, TESTS_AND_CI_MAP и CHANGELOG; данная запись фиксирует фактический результат CI. Код приложения и workflow не менялись в рамках этой документальной синхронизации.


## 2026-11-01 — исправлен возврат окна AutoDraw после установки кисти в G3

Во время live G3 обнаружено нарушение последовательности: после успешного подтверждения радиуса Game Monitor окно AutoDraw восстанавливалось поверх игры до запуска Stage6. Причина — безусловные `root.deiconify()` / `root.lift()` в `BrushBehaviorTestTab._complete_brush_radius_feedback()`.

Исправление в `source/preparation/brush_behavior_test_ui.py`: при автоматическом handoff (`_start_executor_after_brush_drag=True`) окно остаётся свёрнутым, фокус остаётся у игры, после чего выполняется штатный callback запуска executor. При ручной установке кисти прежнее восстановление окна и уведомление сохранены. Проверка точного свежего heartbeat, запись manifest и fail-closed условия не менялись.

Regression test в `source/preparation/tests/test_brush_behavior_test_ui.py` теперь требует, чтобы автоматический handoff не вызывал восстановление окна. Коммиты: `8f8923ded3d788e725206d31515d6f0ed221db3a`, `fd814517b584b9a800c95e4b6a19581a7afc33ce`.

**Проверка:** тест и полный CI для нового HEAD ожидаются; live-повтор G3 после исправления ещё не выполнен. До успешного CI и повторного preflight/G3 продолжать сбор 27 captures нельзя.

## 2026-11-01 — G3 routing fix

- Проверена ветка на HEAD `a747b112969f0a69a3b04b701aec00a4cadc161d`, два G3 experiment manifests и два block journals.
- Подтверждено: оба прогона имели exact CHALK=718, 6 strokes, radius=10, фактические executor параметры 2/10; G3 journal требовал 2/20. Оба отклонены с `block_task_identity_missing`, поэтому не входят в статистику G3.
- Исправлен конфликт legacy radius-matrix / geometry-matrix routing для активных block tasks; добавлен regression test.
- Commits: `85ae43af292e8c8ecdb4d1e5791a27db4a06a97c`, `60117ef34db54a5bf858c946d7b5ca09137caa44`.
- Runtime connection snippets удалены из репозитория, их шаблон добавлен в .gitignore.
- Next gate: полный GitHub Actions CI; затем локальный Windows preflight и новая чистая серия G3 из 27 задач.

## 2026-11-02 — оптимизация workflow и усиление G3 regression tests

- Проверена актуальная конфигурация `.github/workflows/geometry-tests.yml`, `run_all_tests.py`, `build_windows.bat`, build helpers и тестовые suite.
- Обнаружены лишние затраты: push + pull_request запускали одинаковые jobs; benchmark Stage 5/7/8 и synthetic sweeps выполнялись в обычном CI; build job повторно запускал те же основные suite после отдельных test jobs.
- Workflow разделён на параллельные обязательные jobs: Game Monitor, Preparation/G3, корневые Integration tests и Executor. Portable build gated через `needs` на успех этих jobs.
- Добавлены pip cache и concurrency cancellation для устаревших commits.
- Удалён дублирующий pull_request trigger; code CI выполняется на push feature-ветки. Benchmark suite запускается вручную только при явном boolean input run_algorithm_benchmarks=true; обычный manual validation run не запускает benchmarks.
- Root integration suite после mixed unittest discovery разделён на три pytest-группы: UI/G3 handoff, build/import/test-runner/brush-series и geometry validator/metrics. Это изолирует Tk/UI от остальных тестов и даёт отдельную диагностику ошибок build helpers. WebSocket test выполняется только в специализированном Game Monitor job.
- `build_windows.bat` получил opt-in флаг `AUTODRAW_SKIP_TESTS=1`. Он используется только CI build job после успешного завершения всех test jobs; обычный локальный запуск не пропускает тесты.
- Добавлен end-to-end UI routing regression test: G3 block task должен записывать `chalk_test_block` и `chalk_experiment_matrix`, передавать параметры task и не записывать legacy `chalk_radius_matrix`.
- Существующий integration test handoff проверяет, что параметры 2/20 доходят до Stage6 executor.
- Исправлены root-relative пути benchmark job после переноса её working directory в корень Stage20.
- Тесты/CI на конечном HEAD ещё не завершены; live G3 не запускался. Следующий gate — успешный новый CI, portable artifact, локальный preflight и recovery старого paused журнала.

- Диагностика Tk CI выявила, что UI tests использовали реальный DATA_PATHS, в котором могут лежать paused G3 journals; это создавало риск recovery warning/dialog внутри тестового процесса. В UnifiedAppCoreTests.setUp/tearDown добавлена временная изоляция data root и восстановление environment.
- Deferred _scan_chalk_block_recovery callback получил сохраняемый after ID и отменяется при уничтожении owner frame. Добавлен regression test на cancel callback.
- UI root test запускается из прежней проверенной рабочей директории Preparation с 3-minute timeout; build/import и geometry root suites отделены в самостоятельные pytest groups. Для integration job задан общий 12-minute timeout.

## 2026-11-02 — анализ частичной серии G3 из commit 094381f

- Прочитан block journal и все 22 experiment manifests серии `chalk-20261102-015749-7c1141`.
- Подтверждено 21 completed, 1 failed, 5 pending из 27 задач; block status `stopped`, gate reason `monitor_capture_gate_timeout:partial`.
- Сверены task metadata и фактические executor config: `point_step_px` / `point_delay_ms` совпадают во всех 22 попытках.
- Все 22 executor reports завершили 6/6 strokes; фактический радиус — 10; CHALK counter exact и согласован с sampled pointDelta.
- Один capture `s4-d10-r2` partial: 434 `monitor_dropped_events`; его CHALK=363 сохранён как диагностическое значение, но не считается полноценным повтором.
- 21 capture имеют полный Monitor status saved. Во всех trajectory summaries — `incomplete_until_verified`; точная траектория не восстановлена.
- Сводная таблица и осторожная интерпретация влияния шага/задержки записаны в `docs/CHALK_G3_PARTIAL_RESULTS_2026-11-02.md`.
- Предварительный вывод: delay=20 ms заметно увеличивает CHALK против 5/10 ms; уменьшение шага также увеличивает CHALK. Универсальная модель не выводится до завершения матрицы и отдельного контроля радиуса.

- Проверен recovery code после анализа commit 094381f: stopped block не может выдавать pending tasks; failed task не подходит под interrupted retry; стандартный G3 builder формирует 27 задач. Не пытаться возобновлять этот block или вручную менять journal.
- [ ] Принять решение: новая полная серия G3 27/27 по штатному workflow либо отдельная разработка continuation/aggregation механизма для 21 принятых captures + шесть недостающих задач.
- [ ] До повторного live запуска обеспечить чистый Monitor capture; при partial status блок должен останавливаться, а capture оставаться исключённым из accepted repeats.

## 2026-11-02 — диагностика ложного G3 partial из-за глобального буфера Monitor

Проверены `game_monitor.js`, `game_monitor_bridge.js`, `game_monitor_bridge_server.py`, `RunRecorder`, `session.json` проблемной сессии и `experiment.json` задачи `s4-d10-r2`.

Установлено:
- `MAX_EVENTS=50000` ограничивает только локальный массив `state.events`; после лимита `emit()` всё равно вызывает listeners.
- На старте сессии было 252 локальных события; Browser Bridge отправил 50 320, collector принял те же 50 320; финальное состояние Monitor: eventCount=50 000, droppedEvents=572. Баланс `252 + 50320 = 50000 + 572` сходится.
- `sendFailureCount=0`; серверный `received_event_count` равен `sentEventCount`. В проблемном run сохранено 744 события, recorder `dropped_events=0`, CHALK=363 exact и `point_delta_matches_chalk=true`.
- Во время failed run глобальный счётчик уже был 434; позднее он вырос до 572. `RunRecorder.heartbeat()` записывает этот cumulative session counter в поле отдельного run, а gate ошибочно считает его потерей событий текущего capture.
- Детерминированная симуляция 50 320 emit-вызовов подтвердила: retained=50 000, local buffer drops=320, subscriber delivery=50 320.

Вывод: G3 partial вызван ложной интерпретацией глобального буферного overflow, а не доказанной потерей WebSocket-событий. Создан отдельный анализ `docs/GAME_MONITOR_BUFFER_OVERFLOW_ANALYSIS_2026-11-02.md`. Изменения кода, live рисование, CI/workflow и правки исторических журналов не выполнялись.
## 2026-11-02 — исправление ложного partial из-за session-cumulative Monitor counters

Исправлен RunRecorder: вместо трактовки `status.droppedEvents` как per-run loss теперь сохраняются `monitor_buffer_dropped_events_start/end/delta`; cumulative Monitor errors также представлены start/end/delta. `monitor_dropped_events` и `monitor_error_count` оставлены как deprecated cumulative aliases.

Collector теперь считает пропущенные WebSocket sequence, записывает session-level `collector_sequence_gap_count` и добавляет gap count к активному run. Browser Bridge `sendFailureCount` сравнивается с baseline run и сохраняется как `bridge_send_failures_delta`.

Brush Test acceptance и матричные валидаторы больше не отклоняют run из-за cumulative local-buffer overflow. Они fail-closed по per-run `dropped_events`, `monitor_error_count_delta`, `bridge_send_failures_delta` и `collector_sequence_gap_count`. Исправления покрыты Node, Python, WebSocket integration и matrix regression tests.

Документация обновлена: `BRUSH_MONITOR_AUTOCAPTURE_DESIGN.md`, `source/game_monitor/README.md`, `docs/TESTS_AND_CI_MAP.md`. Исторические G3 captures/journal не изменялись. Live game не запускалась. Результат CI на финальном HEAD ещё требуется проверить.


## 2026-11-02 — новая live G3 матрица завершена и проанализирована

**Источник:** commit [35ae78e31f9b6d357a4e8aa30cd12307d8c322e8](https://github.com/Kiddos19882/AutoDraw/commit/35ae78e31f9b6d357a4e8aa30cd12307d8c322e8).  
**Серия:** `chalk-20261102-031830-a0f325`; block ID `d5d28990cb954610aa7f58534be9d3d7`.

**Что проверено:**
- Block journal: 27/27 задач completed, все девять конфигураций sampling имеют по три повтора.
- В коммите: 27 brush plans, 27 experiment manifests, 27 Monitor reports, 55 raw Monitor run JSON и 162 PNG.
- Все 27 experiment summaries: `chalk.status=exact`, CHALK delta совпадает с sampled pointDelta, radius=10/single, 6/6 strokes, frame probe measured.
- Во всех runs: per-run recorder drops=0, Monitor error delta=0, Bridge send failure delta=0, collector sequence gaps=0.
- В шести поздних runs local Monitor export-buffer delta положителен. Сохранённый report event count совпадает с event count run; Bridge/collector не показывают потерь. Cumulative `monitor_dropped_events` достиг 12 237 и остаётся только session diagnostic, не per-run rejection metric.

**Результаты по CHALK:**
- step=1: средние 1351,0 / 1350,3 / 2069,7 для delay 5/10/20 ms.
- step=2: 716,7 / 718,0 / 1383,0.
- step=4: 365,7 / 365,0 / 713,7.
- Для delay=5/10 переход step=1→4 уменьшает расход примерно на 73%, step=2→4 — примерно на 49%.
- Delay=20 увеличивает расход относительно delay=5/10 примерно на 53% (step=1), 93% (step=2) и 95% (step=4).
- Средние длительности и min/max сохранены в `docs/CHALK_G3_RESULTS_2026-11-02.md`.

**Выводы и границы:**
- Для шести длинных прямых линий лучший по измеренному CHALK кандидат — step=4 / delay=5 или 10 ms (около 365 CHALK на 2400 логических px).
- 5 и 10 ms практически эквивалентны по CHALK и времени.
- Это сценарный коэффициент, не универсальная модель. Визуальная непрерывность/качество при более редком sampling ещё не подтверждены.
- G3 фиксировал radius=10. Отдельная radius matrix (1–30) не выявила систематического влияния радиуса на pointCount в этом сценарии.
- Trajectory reconstruction ограничен coalescing; точную принятую длину пути по Monitor не утверждать.

**Документация:** создан `docs/CHALK_G3_RESULTS_2026-11-02.md`; управляющие документы синхронизированы с принятым live результатом: TASKS, PROJECT_STATUS, README, ROADMAP, CHANGELOG, CHALK_GEOMETRY_MATRIX_PLAN и диагностические отчёты. Старый stopped G3 block не менялся.


## 2026-11-02 — визуальный gate G3 и предварительная модель INT-006

- Проверены metadata шести captures для step=4/delay=5 и step=4/delay=10: каждый прогон завершил 6/6 штрихов, 768 move calls, около 18 секунд и около 60 FPS; ROI heuristic отметила 6/6 областей с изменениями.
- Проверена реализация `measure_stroke_visibility`: она считает изменившиеся пиксели в bounding box, порог — 2 пикселя. Это не доказывает непрерывность, точность центральной линии или равномерность покрытия. Визуальный gate оставлен открытым.
- Для G1 построена предварительная per-stroke регрессия прямых горизонтальных/вертикальных/диагональных штрихов: `C ≈ 1.765 + 0.2988 × L`, 36 наблюдений, обучающий RMSE около 0.48 CHALK.
- Короткие штрихи выделены в отдельный lookup-сегмент. G2 repeated_coverage подтверждает расход 61–62 CHALK на каждый повторный проход длиной 200 logical px; перекрытие не является бесплатным.
- G3 sampling coefficients сохранены отдельно от G1/G2 baseline. Radius matrix не показала систематического влияния радиуса на pointCount в проверенной геометрии.
- Создан `docs/CHALK_PRELIMINARY_SEGMENTED_MODEL_2026-11-02.md`; обновлены README, G3 report, PROJECT_STATUS, TASKS и ROADMAP.
- Код не менялся, live-тесты не запускались. Следующий шаг — pixel-level audit PNG и независимая validation модели.


## 2026-11-02 — непосредственный визуальный аудит G3 step=4

- Получены оригинальные шесть `after_draw-board.png` напрямую из GitHub (step=4/delay=5 — 3 повтора; step=4/delay=10 — 3 повтора).
- Все шесть captures визуально показывают непрерывные ровные горизонтальные линии; видимых разрывов, пропущенных сегментов и прерывистых точек не обнаружено.
- Между delay=5 и delay=10 видимой разницы нет; средний CHALK 365.67 и 365.00 соответственно, длительность около 18 секунд, 768 move calls.
- Отмечено ограничение: курсор закрывает часть правого конца шестой линии; точная оценка этого cap невозможна по текущему capture.
- Визуальный gate закрыт для длинных горизонтальных линий G3, но не для других геометрий. Создан отчёт `CHALK_G3_VISUAL_QUALITY_AUDIT_2026-11-02.md`; обновлены G3 report, preliminary model, README, PROJECT_STATUS, TASKS и ROADMAP.
- Код не менялся, live-тесты не запускались, production defaults не менялись.


## 2026-11-02 — консолидация документации после G3 visual audit

- Проверены актуальные docs index, PROJECT_STATUS, TASKS, ROADMAP, WORK_LOG, CHANGELOG, G3 Results, визуальный аудит и preliminary CHALK model.
- Выявлены и устранены противоречия: устаревшие статусы до G1/G2/G3, INT-006=TODO, утверждение что G3 PNG ещё не просмотрены, повторение старого открытого visual gate после его закрытия.
- В начале PROJECT_STATUS выделен актуальный снимок состояния на 2026-11-02; предыдущая полная версия сохранена отдельно в `PROJECT_STATUS_HISTORY_2026-11-02.md`.
- В TASKS актуализированы статусы INT-001—INT-009: INT-004/005 закрыты в пределах реализованного контура, INT-006 выполняется, INT-007 заблокирована до validation, INT-003 остаётся открытой по A/B/C overhead.
- Создан `CHALK_NEXT_STEPS_PLAN_2026-11-02.md`: геометрическая validation step=4, независимая validation модели, метрики ошибки, safety margin, затем INT-007—INT-009.
- Синхронизированы G3 Results, preliminary model, ROADMAP и docs README.
- Исходный код, тесты, конфигурация и первичные экспериментальные данные не менялись; live-эксперименты и workflows не запускались.


## 2026-11-02 — фиксация и старт INT-006

- Проверена рабочая ветка `feature/image-geometry-optimization`; исходный HEAD перед записью протокола: `7ea3868248648aed74979f4fab00c5c2e8f878c6`.
- Сверены README, docs index, PROJECT_STATUS, TASKS, ROADMAP, CHALK plan/model и результаты G1/G2/G3.
- Создан `docs/CHALK_INT006_EXECUTION_PROTOCOL_2026-11-02.md`: профили P0/P1/P2, сценарии V1–V5, 45 captures, обязательные поля, acceptance/rejection, quality metrics, independent validation и условия safety margin.
- Проверены `chalk_experiment_matrix.py`, `chalk_test_blocks.py`, `brush_behavior_test_ui.py`, `mouse_executor.py` и `drawing_plan.py`.
- Найдено ограничение: текущий экспериментальный контракт содержит G1/G2/G3, но не V1–V5. Запускать новые сценарии через текущий runner без расширения matrix/block/UI/analyzer небезопасно.
- Статус INT-006 сохранён IN_PROGRESS; production executor defaults, estimator и исходные экспериментальные данные не изменялись.
- Live captures, CI/workflows не запускались.
- Следующий шаг: расширить экспериментальный harness под V1–V5 и покрыть его regression/orchestration tests.


## 2026-11-02 — реализация INT-006 V1–V5 на инфраструктуре G3

- Расширен `chalk_experiment_matrix.py`: добавлены V1–V5, expected stroke counts и allowlist профилей P0=2/10, P1=4/5, P2=4/10.
- Расширен `chalk_test_blocks.py`: каждая V-фаза создаёт 9 уникальных задач, валидатор журнала проверяет полный набор профилей/повторов, порядок и число штрихов.
- В `brush_behavior_test_ui.py` добавлены пять DrawingPlan и фазы в selector автоматического блока; одиночные ручные запуски V-сценариев запрещены.
- В `integrated_app.py` task-specific executor override распространён на V1–V5 с fail-closed проверкой phase/scenario/radius/strokes/profile.
- Добавлены tests для matrix metadata, sampling profiles, 9-cell block/journal, DrawingPlan и executor handoff V5.
- V1 скорректирован: диагонали разнесены по ROI, чтобы не смешивать наклоны с непредусмотренными пересечениями.
- Серия кодовых коммитов: `5e5655bc`, `9275b875`, `097cf50`, `47828c4`, `b8602b3`, `d0786e9`, `de30c6b`, `d2745f0`, `d8d43b0`, `b328eb1`, `5e4b78b`, `28b49f4`.
- CI для конечного HEAD ещё не подтверждён; live captures не запускались.
- Production defaults, estimator и исходные G1/G2/G3 datasets не изменялись.


## 2026-11-02 — follow-up review INT-006

- Повторно проверены последние коммиты и рабочая ветка; актуальный HEAD перед этой записью: `b60d9aef5b9a95ebefa85f42d99956f181bec7ee`.
- Найден и исправлен дефект в новом executor handoff: V_PHASES использовался в условии до локального импорта. Условие заменено на явный набор разрешённых фаз; неиспользуемый локальный импорт удалён.
- Проверено содержимое V1–V5 DrawingPlan: expected stroke counts 6/6/3/3/10; координаты лежат в logical board 460×240; V1 диагонали разнесены по ROI.
- Проверена согласованность block plan и journal validator: три V sampling profiles, три повтора, девять уникальных ячеек на фазу.
- Статусы GitHub commit checks через доступный endpoint пока не предоставили результатов; успешный CI не заявляется. Попытка локального clone для запуска тестов невозможна из-за недоступности DNS/сети в контейнере.
- Live captures не запускались: локальная игровая сессия не доступна в этом рабочем окружении.


## 2026-11-02 — CI verification for INT-006 V1–V5

- Проверен актуальный branch HEAD: `400becfaefd59497f95b370f3608717d61d5d86e`.
- Найден обязательный GitHub Actions run [#1886](https://github.com/Kiddos19882/AutoDraw/actions/runs/41376333639) на кодовом HEAD `b60d9aef5b9a95ebefa85f42d99956f181bec7ee`; итоговый conclusion: `success`.
- Успешны обязательные jobs: Application integration tests; Executor regression tests; Game Monitor and bridge tests; Preparation and G3 matrix tests; Windows portable build and startup smoke-test.
- Optional algorithm benchmarks завершился `skipped`; это необязательный job и не влияет на итог обязательного CI.
- Между проверенным кодовым HEAD и текущим branch HEAD — шесть коммитов, меняющих только четыре Markdown-документа: `CHALK_INT006_EXECUTION_PROTOCOL_2026-11-02.md`, `CHALK_NEXT_STEPS_PLAN_2026-11-02.md`, `PROJECT_STATUS.md`, `WORK_LOG.md`. Код после проверенного CI не менялся.
- Commit-status endpoint вернул пустой список; CI подтверждён по самому workflow run и результатам jobs.
- Live captures V1–V5 не запускались. Следующий gate — 45 captures в доступной игровой сессии с проверкой exact CHALK, per-run Monitor integrity и геометрического качества.


## 2026-11-02 — INT-006 V1–V5 live captures and analysis

- Получен data commit [6479536](https://github.com/Kiddos19882/AutoDraw/commit/64795362aa1bf4d0a3587e119b8c959242be6181); актуальный branch HEAD на момент анализа — этот commit.
- Проверены все пять block journals: V1–V5, каждый 9/9 completed; итого 45/45 captures.
- Для всех 45 runs: monitor capture saved, exact CHALK, pointDelta matches exact counter, requested/observed requested radius=10; dropped events, Monitor error deltas, Bridge failure deltas, collector sequence gaps и per-run buffer drops — 0.
- Per-stroke pointDelta сгруппирован по stroke_id: число stroke groups соответствует плану, non-consuming candidates=0, сумма per-stroke расходов совпадает с CHALK delta.
- Средний расход P0/P1/P2 (step2/delay10; step4/delay5; step4/delay10): V1 243.67/126.67/127.33; V2 20.00/15.00/15.33; V3 380.67/193.67/193.67; V4 448.67/229.00/229.67; V5 441.33/229.33/229.00.
- Step=4 снизил расход на 48–49% в V1/V3/V4/V5 и на 23–25% в V2. P1/P2 практически равны по CHALK.
- G1-модель `1.765 + 0.2988×L` проверена без refit на 66 новых per-stroke наблюдениях P0 из V1/V3/V4/V5: MAE 1.09, RMSE 1.33, bias −1.04, MAPE 1.71%, max absolute error 4.12.
- Исследовательские step=4 fits: P1 `1.475 + 0.148865×L`; P2 `1.440 + 0.149151×L`. Это fit на тех же наблюдениях, не independent validation.
- Ручной просмотр репрезентативных P0/P1 PNG: выявлены непреднамеренные пересечения V1/V3; V2 показывает круглые отметки для движений короче радиуса; V5 spacing=8 logical px сливает параллельные следы, spacing=24 сохраняет разделение. Pixel-level метрики не рассчитаны.
- Подробный отчёт: [CHALK_INT006_V1_V5_RESULTS_2026-11-02.md](CHALK_INT006_V1_V5_RESULTS_2026-11-02.md). Production-код, executor defaults и estimator не менялись.
- CI run [#1887](https://github.com/Kiddos19882/AutoDraw/actions/runs/41384186201) для data commit завершился success.


## 2026-11-02 — INT-006: первичный скрининг PNG V1–V5

- Проверены оригинальные board ROI из GitHub: 15 representative PNG, по одному capture для каждого профиля P0/P1/P2 в V1–V5.
- Визуально не выявлено очевидной потери непрерывности у step=4 относительно P0 на просмотренных диагоналях, ломаных, контурах и пересечениях.
- Зафиксированы дефекты/ограничения геометрии: V1 пересечение slope_050/negative_shallow; V3 пересечение right_angle/acute_zigzag; V2 короткие движения выглядят точками при requested radius=10; V4 часть контура перекрыта курсором; V5 spacing=8 logical px сливается.
- P1 и P2 визуально практически неразличимы на выбранных примерах.
- Численные pixel-level метрики не рассчитаны; этап нельзя считать закрытым. Требуется сегментация всех 45 PNG, вычисление continuity/max gap, centerline deviation, width/width variation, closure и parallel separation с проверкой масок относительно blank-board reference.
- Отчёт: [CHALK_INT006_PNG_SCREENING_2026-11-02.md](CHALK_INT006_PNG_SCREENING_2026-11-02.md).
- Production code, executor defaults, estimator и первичные captures не изменялись.



## 2026-11-02 — INT-006 quantitative PNG audit

- Добавлен изолированный исследовательский анализатор дифференциальных board PNG, использующий blank reference и planned DrawingPlan geometry; production executor не затронут.
- Исправлены обнаруженные по CI дефекты: CSV extra fields, OpenCV connectivity arguments, узкий per-stroke corridor/параллельные assigned masks, inference закрытого контура по совпадающим endpoints и cursor exclusion.
- Финальный кодовый HEAD: `d3971e4da66f503e91799729005cea24e32bf466`; CI run [41392156994](https://github.com/Kiddos19882/AutoDraw/actions/runs/41392156994) — success, включая Windows build/smoke и pixel audit.
- Пакет: 45/45 captures, invalid=0, matrix gaps/duplicates=0; 252 stroke rows и 279 parallel-pair rows; artifact [13117572972](https://github.com/Kiddos19882/AutoDraw/actions/runs/41392156994/artifacts/13117572972).
- Зафиксированы ограничения: V2 length_10 — 9/9 повторов с evaluable fraction 0.381; V4 irregular_polygon closure metric отсутствует; V1/V3 имеют multi-component/intersection ambiguity; V5 spacing≈8.01 logical px сливает близкую пару в 9/9 повторах.
- Создан подробный отчёт `CHALK_INT006_PIXEL_AUDIT_2026-11-02.md`, обновляются PROJECT_STATUS/TASKS. Quality gate остаётся OPEN; независимая модельная validation и safety margin не выполнены.
- Первичные PNG/manifests/Monitor reports не изменялись. Production executor, estimator и defaults не менялись.


## 2026-11-02 — INT-006 manual overlay review и коррекция тестовой геометрии

- Скачан и просмотрен CI artifact `autodraw-int006-png-analysis` run `41392156994`; проверены representative overlays V2/P1, V4/P0/P1, V1/P1, V3/P1 и V5/P1.
- V2 `length_10`: виден округлый отпечаток; при длине 10 logical px и radius=10 центральная линия не отделима от footprint. `path_metrics_sufficient=false` трактуется как недостаточность измерения, а не как подтверждённый разрыв.
- V4 `irregular_polygon`: курсор перекрывает общую начальную/конечную точку. Closure seam по текущему capture не оценивается; требуется post-draw capture с курсором вне board ROI либо иной подтверждённый способ убрать occlusion.
- V1: `slope_050` касается/пересекается с `negative_shallow`; `negative_shallow` также пересекается с `negative_steep`. V3: `right_angle` пересекается с `acute_zigzag`.
- Исправлена только экспериментальная геометрия в `source/preparation/brush_behavior_test_ui.py`: V1 negative_shallow перенесена в нижнюю область, negative_steep сдвинута вправо; V3 acute_zigzag ограничена отдельным левым ROI. Первичные captures соответствуют старой геометрии и сохранены без изменений.
- Добавлен regression test, вычисляющий минимальное расстояние между разными polyline и требующий >20 logical px для V1/V3 при radius=10. Расчёт по новым DrawingPlan: минимум V1≈25.58 px, V3≈31.62 px.
- Коммиты: `5047cb7973a266ca69b6fd9c21ea81af0bd89db3` (test DrawingPlan fix), `a4a909d08b9947cfff139b20d55300f1e97dcc25` (isolation regression test). CI для нового code HEAD ещё не подтверждён.
- Production executor, estimator, sampling defaults и первичные experiment data не менялись. Live reruns не запускались.
- Следующие действия: подтвердить CI; повторить V1/V3 blocks; улучшить V4 post-draw cursor handling; спроектировать V2 extended short-stroke и V5 spacing sweep; затем независимая validation модели.


## 2026-11-02 — V4 cursor-free post-draw capture

- Причина V4 closure occlusion найдена в `_capture_automated_after_draw`: снимок делался без изменения положения курсора, оставшегося на конечной точке контура.
- Добавлен `_cursor_safe_point_outside_region(region, screen_size, margin=24)`: выбирает ближайшую доступную точку за пределами calibrated board ROI; проверяет размеры/границы и отказывает, если безопасной точки нет.
- Перед финальным screenshot post-draw workflow выполняет `pyautogui.mouseUp()`, затем `pyautogui.moveTo(..., duration=0)`, ждёт 150 ms и повторно снимает экран. Board не очищается и не изменяется; действие перемещения не содержит клика.
- В `experiment_phases.after_draw.cursor_exclusion` сохраняются метод, координаты, margin и статус перемещения для аудита.
- Добавлены unit/regression tests для выбора точки у границы экрана, отказа при невозможности безопасного перемещения и порядка mouseUp → move → screenshot.
- Коммиты: `a680f51997b8981eb430d9dd1cf12d24106130e9`, `d299259e1a490330d75ecd4a25b5d22a2435d851`, `723a410795953e075fbdfefe0c03cdfc28a94dd0`.
- Изменён только post-draw capture экспериментального UI и его тесты. Production executor, estimator, sampling defaults, первичные captures и Game Monitor не менялись.
- CI workflow `geometry-tests.yml` запускается на push изменений `source/**`; запуск для текущего HEAD ещё требуется подтвердить. Live captures не выполнялись.


## 2026-11-02 — изоляция cursor relocation только в automated post-draw

- Diff review выявил, что первая версия cursor relocation была вставлена в общую `_capture_experiment_phase_now`, а не только в `_capture_automated_after_draw`; это затрагивало ручной capture и оставляло `safe_cursor_point` неинициализированным в автоматическом методе.
- Исправлено: общий/manual capture возвращён к прежнему `crop_calibrated_regions(screen, config.get("regions", {}))`; cursor-safe sequence расположен только в `_capture_automated_after_draw`.
- Добавлен regression test `test_manual_experiment_capture_does_not_relocate_cursor`, запрещающий mouseUp/moveTo в ручном capture method.
- Fix commit: `16ffb5893b642799fe6b5b6fc39d764975d70dfe`; guard test commit: `a74f7fd18c1b4100c87747ab4bd533afaa74b95d`.
- CI для промежуточного HEAD `723a410` run `41466392528` ещё выполнялся на момент проверки; исправленный HEAD запустил новый workflow. Финальный CI ожидается.


## 2026-11-02 — подготовлены отдельные live follow-up серии V2/V5

- Новая V2 серия `int006_short_strokes_followup`: пять изолированных штрихов 12/16/20/24/30 logical px, направления горизонталь/вертикаль/диагональ. Исходные V2 captures сохранены.
- Новая V5 серия `int006_intersections_spacing_sweep`: шесть контрольных штрихов X/T/креста и пять независимых пар параллельных линий spacing 8/12/16/20/24 logical px; всего 16 штрихов. Исходные V5 captures сохранены.
- Обе серии подключены к PHASE_SCENARIOS/EXPECTED_STROKES, block matrix, UI presets и regression tests. Каждая серия создаёт 9 задач (P0/P1/P2 × 3 повтора), requested radius=10; всего 18 будущих live captures.
- Добавлены геометрические regression checks точных длин V2 и межосевых расстояний V5.
- Документ выполнения: `CHALK_INT006_V2_V5_FOLLOWUP_2026-11-02.md`. Live experiments не запускались; их выполняет пользователь. Production executor, estimator, defaults и старые captures не изменялись.
- Кодовые коммиты follow-up: `1f2917a`, `8a012de`, `230fe22`, `3d6754c`, `ef8b704`, `94c3c87`. Предыдущий CI run `41466760095` успешен для HEAD `a74f7fd`; CI новых изменений ожидается.


## 2026-11-02 — исправление CI regression для INT-006 follow-up

- Проверен CI run `41468581157`: Preparation/G3 — 654 passed, 2 failed; Application integration — 34 passed, 1 failed; Executor и Game Monitor/bridge — success. Windows build и PNG audit были skipped.
- Preparation failure вызван отсутствием legacy expected counts: `int006_short_strokes` (6) и `int006_intersections_spacing` (10). Эти counts восстановлены в `EXPECTED_STROKES`; старые IDs остаются только в legacy phase map и не добавлены в новые phase/block planners.
- Application integration failure вызван устаревшей test fixture: она передавала старый V5 scenario ID `int006_intersections_spacing`, тогда как runtime gate ожидает `int006_intersections_spacing_sweep` с 16 штрихами. Fixture и task ID обновлены. `AttributeError` по отсутствующему `self.root` возник вторично при показе error dialog после отклонения устаревшего плана; production error handling не менялся.
- Изменения: `0cac37c` (legacy counts), `706be60` (V5 fixture). Production executor, CHALK estimator, sampling defaults и live data не менялись.
- Следующий gate: полный CI на исправленном HEAD; live V2/V5 не запускать до green CI.

- Дополнительно усилены регрессионные проверки: legacy IDs явно проверяются на отсутствие в новых `PHASE_SCENARIOS`; V5 integration test double получает `root=None`, чтобы будущая ошибка runtime gate не маскировалась `AttributeError` при вызове messagebox.
- Дополнительные commits: `7a22a76` (planner isolation assertion), `3e8e6c5` (устойчивость integration fixture). Текущий corrective code HEAD: `3e8e6c5709dce330551d46667c0f5841fbc5a3fc`.


## 2026-11-02 — corrective INT-006 CI подтверждён

- Через полный список GitHub Actions runs найден push-triggered workflow run [41470680544](https://github.com/Kiddos19882/AutoDraw/actions/runs/41470680544) на code HEAD `3e8e6c5709dce330551d46667c0f5841fbc5a3fc`; предыдущий интерфейс commit-associated runs не показывал push events.
- Все обязательные jobs завершились success: Application integration, Executor regression, Game Monitor/bridge, Preparation/G3, Windows portable build/startup smoke-test и INT-006 pixel-level PNG audit. Optional algorithm benchmarks skipped.
- Run [41470651104](https://github.com/Kiddos19882/AutoDraw/actions/runs/41470651104) на промежуточном commit `7a22a76` был cancelled concurrency group после появления более нового push run; финальный run на `3e8e6c5` завершился success.
- Найдены артефакты `autodraw-int006-png-analysis` и `autodraw-g3-preflight-build`; они сохранены в GitHub Actions.
- Синхронизированы PROJECT_STATUS, TASKS, CHALK_NEXT_STEPS_PLAN и INT-006 execution protocol: software CI gate закрыт, live follow-up V1/V3/V2/V4/V5 и независимая model validation остаются открытыми.
- Live captures не выполнялись; production executor, estimator, sampling defaults и master не изменялись.


### Дополнительная проверка артефакта INT-006 PNG audit — 2026-11-02

- Скачан и локально проверен Actions artifact `autodraw-int006-png-analysis` из run `41470680544` (ZIP, 1.2 MB).
- `summary.json`: expected/discovered/analysed/capture-valid = 45/45/45/45; invalid captures = 0; по 9 captures для каждой фазы V1–V5; duplicate/missing/unexpected matrix cells и batch failures = 0.
- CSV содержит 252 per-stroke rows и 279 parallel-pair rows. Gap rows отсутствуют во всех фазах; максимальный измеренный gap = 0.0 logical px в анализируемых коридорах.
- V2: 9 строк `length_10` имеют `path_metrics_sufficient=false`; это ограничение оценки центральной линии, не доказательство разрыва.
- V5: 9/144 candidate pair rows отмечены как touching/overlap для близкой пары с axis separation 8.0115 logical px и minimum ink-mask distance 2.3718 logical px. Это подтверждает известное ограничение исходной V5 spacing=8 и обосновывает отдельный sweep.
- Результаты PNG являются геометрической диагностикой и не заменяют exact CHALK telemetry `post.pointCount - pre.pointCount`.


### Подготовлен live follow-up V1/V3/V4 — 2026-11-02

- Добавлен `CHALK_INT006_V1_V3_V4_FOLLOWUP_2026-11-02.md`: отдельные серии для исправленных DrawingPlan V1/V3 и cursor-free closure capture V4.
- Для каждой фазы предусмотрены новый `series_id`, отдельный journal и 9 captures (P0/P1/P2 × 3); суммарно 27 captures и 108 per-stroke observations.
- Проверены фактические координаты сценариев в `brush_behavior_test_ui.py`: V1 — 6 диагоналей, V3 — 3 полилинии, V4 — 3 замкнутых контура; ожидаемые counts согласованы с `EXPECTED_STROKES`.
- В документационный индекс, PROJECT_STATUS, TASKS, ROADMAP и CHALK_NEXT_STEPS_PLAN добавлены ссылки на протокол. Live captures не выполнялись.


## 2026-11-02 — исправлена совместимость журналов старых V2/V5 блоков
- Проверен непосредственно в GitHub journal `chalk-block-V2-chalk-20261102-060912-a8e1c6-6204351c.json` (series `chalk-20261102-060912-a8e1c6`). В нём 9/9 уникальных matrix cells, все задачи и блок имеют статус `completed`; legacy scenario ID `int006_short_strokes`, expected_strokes=6. Дублирующихся ячеек не обнаружено.
- Root cause: block journal validator использовал только текущий `PHASE_SCENARIOS[V2]` ID и 5-stroke count. Хотя legacy IDs присутствовали в `LEGACY_V_SCENARIO_PHASES` и `EXPECTED_STROKES`, validator их не учитывал. Из-за отказа загрузки корректный completed journal попадал в unresolved recovery scan; кнопка закрытия повторно вызывала ту же загрузку и завершалась той же ошибкой.
- Исправлено: validator принимает для V2/V5 как текущие scenario IDs, так и соответствующие legacy IDs; ожидаемое число штрихов сверяется с конкретным ID задачи. Смешение legacy/current scenario IDs в одном блоке по-прежнему запрещено; все 9 matrix cells, уникальность order index и sampling parameters строго проверяются.
- Добавлены regression tests для legacy V2 (6 strokes) и legacy V5 (10 strokes), оба с полностью completed журналами.
- Commits: `f0e05df` (validator), `4847cce` (tests). Ветка `feature/image-geometry-optimization`; master не затронут. Production executor, CHALK estimator, sampling defaults и experiment data не менялись.
- Следующий gate: дождаться полного CI на исправленном коде. После получения обновлённой версии приложения пользователь может просто перезапустить AutoDraw: корректный completed journal должен проходить загрузку и не требовать ни восстановления, ни закрытия. Локальный файл журнала не нужно удалять или редактировать.


## 2026-11-02 — безопасное положение курсора перед after-draw capture

- Причина: прежняя безопасная точка выбиралась только относительно `board_area`; она могла попасть на `paint_meter_area` и вызвать hover-уведомление, перекрывающее доску.
- `_cursor_safe_point_outside_region` теперь принимает дополнительные исключаемые ROI и в первую очередь выбирает точку ниже самой нижней интерактивной области.
- Автоматический post-draw capture перед `after_draw-board.png` учитывает одновременно `board_area` и `paint_meter_area`; отступ увеличен до 32 px. Перемещение выполняется после `mouseUp()` и до второго `ImageGrab.grab()`.
- Ручной capture и поведение рисования не менялись. В manifest фиксируются исключённые области и политика размещения курсора.
- Добавлены regression tests для позиции ниже обеих областей и защиты от paint-meter hover.
- Live-проверка на рабочем игровом окне не выполнялась; требуется подтвердить отсутствие уведомления в следующем реальном CHALK-блоке.


## 2026-11-02 — анализ live follow-up V1–V5

- Получен commit [e879a77](https://github.com/Kiddos19882/AutoDraw/commit/e879a77f63be7a7a68de3f09091eab7dba0d34a2) с пятью block journals, 45 DrawingPlan/experiment captures, Game Monitor reports и PNG. Проверка дерева commit подтвердила полный набор 45 experiment manifests и 45 monitor reports; каждый блок содержит 9/9 completed tasks.
- Проверены все 45 manifests: radius=10, точный CHALK delta, `point_delta_matches_chalk=true`, expected stroke count, нулевые per-run Monitor/Bridge errors, dropped events и sequence gaps.
- Сводные средние exact CHALK P0/P1/P2: V1 251.67/131.33/132.33; V2 39.00/24.00/23.67; V3 344.00/175.33/174.00; V4 438.33/229.00/229.33; V5 407.67/216.00/216.33.
- Step=4 экономит 38.5–49.4% относительно step=2. Разница delay=5/10 ms при step=4 незначительна (до ~1.4% по средним).
- Новые manifests фиксируют курсор в точке (856,624), ниже board/paint-meter ROI, margin=32 px. Paint-meter screenshot estimate inconclusive. ROI heuristic ambiguity в V3/V4/V5 требует pixel-level анализа и не опровергает exact Monitor telemetry.
- Создан подробный отчёт `CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md`; протокол INT-006 и PROJECT_STATUS синхронизированы.
- Следующий gate: pixel-level аудит новых 45 PNG, затем независимая validation CHALK модели на полных DrawingPlan и safety margin. Production defaults/estimator не менялись; radius matrix этим follow-up не расширялась.


## 2026-11-02 — series-aware PNG audit, V5 spacing and full CI

- Первый CI run на data commit e879a77 обнаружил 90 valid captures (исходные 45 + follow-up 45), но старый анализатор ожидал только 45 и считал совпадающие matrix cells разных series дублями. Реальные duplicate/missing/unexpected cells и batch failures отсутствовали.
- Исправлен tests/chalk_int006_png_analysis.py: matrix identity scoped by series_id + phase; validation выполняется отдельно для каждой серии по 9 ячейкам; series_id включён в summary и CSV. Workflow теперь использует --expected-runs-per-series 9.
- Добавлены regression tests: одинаковые ячейки в разных series не конфликтуют; повтор в одной series по-прежнему детектируется. Поправлено имя synthetic fixture после изменения experiment_id.
- Pixel audit run [41496555297](https://github.com/Kiddos19882/AutoDraw/actions/runs/41496555297) обработал 90/90 captures, 10 series ×9, 0 invalid, 0 duplicate/missing/unexpected cells, 0 batch failures. Artifact: 273 files, 549 per-stroke rows, 900 parallel-pair rows.
- Новые 45 follow-up captures: 297/297 strokes coverage=1.0, path_metrics_sufficient=true, gap_count=0, max_gap=0.0; V4 closure seams 27/27 covered. Cursor detection false и cursor-exclusion pixels=0 для 45/45.
- V5 target pair sweep: spacing 8.0115/12.0172 logical px — touch/merge 9/9; 16.0229/20.0286/24.0344 — 0/9. Первое проверенное разделённое расстояние в этой конфигурации — 16 logical px при radius=10.
- Full CI run 41496555297 — success: all required regression jobs, PNG audit, Windows portable build/startup smoke-test. Optional benchmarks skipped. Артефакты PNG audit и portable build доступны в Actions.
- Документация: CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md, execution protocol, PROJECT_STATUS, TASKS, ROADMAP и follow-up protocols синхронизированы. Следующий gate — independent validation модели на полных DrawingPlan, затем safety margin. Production defaults/estimator не менялись.


## 2026-11-02 — уточнение CI legacy-journal compatibility и подготовка независимой validation

- Повторно проверена история ветки `feature/image-geometry-optimization`: commits `f0e05df` и `4847cce` входят в текущую ветку.
- Сопоставлены commits с последними подтверждёнными CI runs. Run `41470680544` прошёл на более раннем code HEAD `3e8e6c5`; он не включает validator change и regression tests legacy-journal compatibility. Run `41496555297` подтверждает pixel audit/portable build, но не закрывает этот поздний кодовый gate.
- Статически проверены актуальный validator, таблица legacy IDs/counts и новые regression tests: V2 принимает legacy `int006_short_strokes` (6 strokes), V5 — legacy `int006_intersections_spacing` (10 strokes); в одном journal запрещено смешение сценариев, matrix cells и order остаются уникальными.
- На момент первоначальной сверки точный checkout SHA run `41496555297` ещё не был установлен, поэтому CI gate временно оставили открытым. Последующее чтение workflow logs подтвердило checkout после commit `956ce2b`, который содержит `f0e05df` и `4847cce` в истории; полный CI и legacy-journal tests прошли успешно (см. запись ниже).
- Подготовлен отдельный протокол независимой validation на пяти новых DrawingPlan с frozen predictions P0/P1/P2, тремя повторами и exact pre/post pointCount. Production estimator, executor defaults и исходные экспериментальные данные не изменялись.
- Обновлены PROJECT_STATUS, TASKS, CHALK_NEXT_STEPS_PLAN, ROADMAP и индекс документации.


## 2026-11-02 — подтверждение CI legacy-journal compatibility

- Углублённо проверены workflow logs run `41496555297`: job Preparation/G3 checkout рабочей ветки выполнен в 18:01:55 UTC; commit `956ce2b` создан в 18:01:05 UTC и содержит commits `f0e05df` и `4847cce` в своей истории.
- Preparation/G3 job завершился результатом `662 passed, 82 subtests passed`; Application integration, Executor regression, Game Monitor/bridge, Windows portable build и INT-006 PNG audit также завершились success. Optional benchmarks skipped.
- CI gate для legacy V2/V5 journal compatibility закрыт. Ранее внесённая отметка о неподтверждённом CI исправлена; повторный запуск не требуется.
- Следующий gate INT-006 — live independent validation по пяти новым DrawingPlan из `CHALK_INT006_INDEPENDENT_VALIDATION_PLAN_2026-11-02.md`.


## 2026-11-02 — аудит готовности независимой validation INT-006

**Рабочая ветка:** `feature/image-geometry-optimization`  
**Результат:** D1–D5 live validation заблокирована до расширения текущего experiment harness.

**Проверены исходники:**
- `source/preparation/chalk_experiment_matrix.py`;
- `source/preparation/chalk_test_blocks.py`;
- `source/preparation/brush_behavior_test_ui.py`;
- `integrated_app.py`;
- `tests/analyze_chalk_experiment_matrix.py`.

**Выводы:**
- D1–D5 отсутствуют в matrix phase/scenario contract и expected stroke counts.
- Block planner/journal поддерживает G1/G2/G3/V1–V5, но не единый 45-cell validation block.
- Brush Test UI содержит V1–V5 и V2/V5 follow-up, но не независимые DrawingPlan D1–D5.
- Executor handoff разрешает override для G3/V1–V5, но не для новой INT006 phase.
- Analyzer принимает exact telemetry manifests и агрегирует повторы, но пока не сопоставляет их с immutable prediction records и не считает residual/MAE/RMSE/bias по frozen model.

**Документация:**
- Создан `CHALK_INT006_HARNESS_READINESS_AUDIT_2026-11-02.md`.
- Статус `CHALK_INT006_INDEPENDENT_VALIDATION_PLAN_2026-11-02.md` исправлен с READY FOR LIVE VALIDATION на BLOCKED.
- Синхронизированы PROJECT_STATUS, TASKS и ROADMAP.

**Границы:** код и тесты не изменялись; CI и Windows preflight не запускались; live captures не выполнялись. Production estimator/defaults, исходные экспериментальные данные и master не менялись.

**Следующий шаг:** расширить существующий matrix/block/UI/executor/analyzer контракт отдельной INT006 phase, добавить regression tests, пройти полный CI и только затем подготовить локальный Windows 10 preflight.


## 2026-11-02 — INT-006 frozen predictions/analyzer: software gate PASS

**Ветка:** `feature/image-geometry-optimization`  
**Code HEAD:** `ca8c9b3bd739ea0a5b557b87fc0106ecfde81216`  
**CI:** [41513389663](https://github.com/Kiddos19882/AutoDraw/actions/runs/41513389663) — **SUCCESS**.

- Реализованы frozen model ID/version, коэффициенты P0/P1/P2 и exact short lookup.
- Block planner добавляет hash-sealed artifact с 15 predictions в durable journal до первого live capture; все 45 задач получают prediction ID.
- Matrix metadata требует prediction ID для INT006; Brush Test UI записывает его и блокирует ручной запуск D1–D5; integrated executor handoff сверяет model/scenario/profile identity.
- Analyzer связывает manifest с completed journal attempt, сверяет exact CHALK/Monitor integrity, geometry/profile/series/task identity, рассчитывает run-level и per-stroke residuals, MAE/RMSE/bias/MAPE/max underprediction и repeatability.
- Regression suites: Preparation/G3 — 667 passed, 82 subtests passed; Application integration, Executor regression и Game Monitor/bridge — success.
- INT-006 pixel-level PNG audit — success. Windows portable build/startup smoke-test — success. Artifact `autodraw-g3-preflight-build`, ID `13173632860`; PNG audit artifact ID `13174616232`.

**Следующий шаг:** пользователь выполняет локальный Windows 10 preflight по `CHALK_INT006_LOCAL_PREFLIGHT_GUIDE_2026-11-02.md`. 45 live captures не запускались. Production estimator/defaults, исходные экспериментальные данные и master не менялись.


## 2026-11-03 — INT-006 D1–D5 captures и предварительная независимая сверка

- Проверена актуальная ветка `feature/image-geometry-optimization`; live block `chalk-20261102-232320-7cea27` содержит 45/45 completed tasks.
- Прочитаны все 45 `experiment.json` и 45 `monitor_report.json`. Для каждого capture проверены exact CHALK, радиус, stroke count, сумма per-stroke `pointDelta`, run/experiment linkage и integrity counters; missing reports не обнаружены.
- Предварительно пересчитаны 45 plan-level и 243 stroke-level residuals. Результаты и таблицы сохранены в `CHALK_INT006_VALIDATION_PRELIMINARY_RESULTS_2026-11-03.md`.
- Найден portability blocker штатного analyzer: сравнение полного локального Windows пути не подходит для relocated capture bundle в CI. Исправлено сравнение по уникальному experiment directory name; добавлен regression test на Windows-style path.
- Workflow geometry-tests дополнен запуском `chalk_int006_validation.py` и upload JSON artifact.
- Официальный analyzer report, проверка frozen artifact SHA-256 и подтверждение полного CI после последних commits остаются pending. Не менять estimator/defaults и не начинать INT-007 до закрытия этих gates.


## 2026-11-03 — повторная проверка всех INT-006 Monitor reports и frozen hash

- Повторно прочитаны все 45 experiment manifests и все 45 Monitor reports из block `1f93ddcac07445b78093744c7cbabcde`.
- Во всех reports подтверждены exact pre/post CHALK, равенство общей delta / sampled delta / суммы per-stroke DRAW_SAMPLE pointDelta, совпадение числа stroke groups, отсутствие dropped events, Monitor errors, Bridge send failures и sequence gaps.
- Во всех Monitor reports observed brush radius единственный: 10; experiment ID совпадает с journal attempt.
- Независимый SHA-256 frozen artifact совпал: `a0eab016e96a81e14bededd32cf5161dd943d6fc85a20b7eec17455f69d0c61c`.
- Официальный analyzer JSON и доступный CI run/artifact status по-прежнему не получены через доступные endpoints. Production estimator/defaults не менялись.


## 2026-11-03 — усиление journal-to-prediction binding

- Статический аудит analyzer выявил непроверенную связь: frozen prediction ID сравнивался с manifest, но не с prediction ID в самой journal task.
- Analyzer дополнен fail-closed проверкой task prediction ID и expected stroke count против frozen prediction.
- Добавлен regression test на tampered journal prediction ID.
- Изменения находятся в `feature/image-geometry-optimization`; CI должен повторно проверить подготовительные тесты и analyzer job. Официальный CI report пока не получен.


## 2026-11-03 — официальный analyzer run: geometry serialization mismatch

- CI run [41530634729](https://github.com/Kiddos19882/AutoDraw/actions/runs/41530634729) на commit `2d99869` завершился FAILURE только на шаге независимого INT-006 CHALK analyzer. Preparation/G3, Application integration, Executor regression, Game Monitor/bridge, Windows portable build и INT-006 pixel PNG audit завершились success; optional benchmarks skipped.
- Загруженный analyzer artifact содержит `status=incomplete`, `accepted_count=0`, `missing=45`, `rejected=45`; все 45 отклонений имеют причину `geometry_signature_mismatch`. Frozen artifact SHA-256 совпадает с ожидаемым `a0eab016e96a81e14bededd32cf5161dd943d6fc85a20b7eec17455f69d0c61c`.
- Root cause: frozen prediction хранит logical points как пары чисел, а реальный runtime DrawingPlan serializer сохраняет strokes с `closed`, служебным `metadata` и point objects `{x, y}`. Analyzer ошибочно сравнивал хеши/структуры разных сериализаций напрямую; captures и Monitor telemetry не признаны повреждёнными.
- Analyzer исправлен: отдельно проверяется hash фактического manifest representation, затем strokes нормализуются до frozen logical geometry и сравниваются с frozen plan/signature. Коэффициенты, prediction artifact, production estimator, executor defaults и sampling defaults не менялись.
- Regression fixture обновлён для реального runtime manifest shape. Commits: `8eba34f2ae402bbcf8af096f8b642a5cdcfb5eee` (fix), `dd64730e202ed6f6014fa2dd1a65c3100cc32018` (test).
- Повторная проверка выполняется workflow [41532629748](https://github.com/Kiddos19882/AutoDraw/actions/runs/41532629748) на HEAD `dd64730`; на момент записи run ещё выполняется. До его завершения quantitative validation остаётся PENDING, INT-006 — IN_PROGRESS, safety margin — not established, production eligibility — not validated.


## 2026-11-03 — INT-006 official quantitative validation PASS

- Повторный CI [41532629748](https://github.com/Kiddos19882/AutoDraw/actions/runs/41532629748) на commit `dd64730e202ed6f6014fa2dd1a65c3100cc32018` завершился SUCCESS. Preparation/G3: 669 passed, 82 subtests passed; Application integration, Executor regression, Game Monitor/bridge, Windows portable build/startup smoke-test, PNG audit и независимый analyzer — success. Optional algorithm benchmarks skipped.
- Artifact `autodraw-int006-chalk-validation` (ID `13182727663`): `status=complete`, 45 accepted, 0 missing, 0 rejected, 15/15 groups complete, 3 repeats per group, 243 stroke rows. SHA-256 frozen artifact совпал с journal.
- Official metrics: run-level MAE 1.408, RMSE 1.967, bias -0.875, MAPE 2.134%, max absolute error 4.94, max underprediction 1.82 CHALK. Per-stroke MAE 0.439, RMSE 0.544, max underprediction 1.085 CHALK.
- P1 (step=4, delay=5 ms) — лучший совокупный профиль на D1–D5: MAE 0.657, RMSE 0.838, MAPE 1.178%, max underprediction 0.92 CHALK. P1 остаётся экспериментальным кандидатом, не production default. Эмпирический guard 1 CHALK покрывает максимум этой выборки, но не является статистической гарантией; D3/P1 repeat σ≈1.41.
- Полный отчёт: [CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md](CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md). Analyzer geometry serialization fix и runtime-shaped regression fixture: commits `8eba34f` и `dd64730`.
- `safety_margin_status=not_established`, `production_eligibility=not_validated`; production estimator/defaults и master не менялись. INT-006 остаётся IN_PROGRESS до отдельного решения по safety margin и расширения domain validation; INT-007 остаётся BLOCKED.


## 2026-11-03 — план radius × geometry cross-validation

- Сопоставлены два подтверждённых источника: radius matrix 21/21 на шести длинных горизонтальных линиях (радиусы 1–30, 722–728 CHALK) и официальный INT-006 D1–D5 при фиксированном radius=10.
- Вывод: radius matrix не показывает систематического эффекта для длинных горизонтальных линий, но не отвечает на вопрос для коротких деталей, диагоналей, пересечений и повторного покрытия.
- Создан [CHALK_RADIUS_GEOMETRY_CROSS_VALIDATION_PLAN_2026-11-03.md](CHALK_RADIUS_GEOMETRY_CROSS_VALIDATION_PLAN_2026-11-03.md): предложена матрица D1–D5 × radius 1/10/30 × 3 повтора при P1 (45 captures). Требуется отдельная experimental phase/harness и успешный CI до live запуска.
- До результатов не вводить radius multiplier и не менять production estimator/defaults.


## 2026-11-03 — Инвентаризация документации

- Проверено дерево Markdown-файлов ветки `feature/image-geometry-optimization`: 56 файлов в `AutoDraw_Stage20/docs/` и 16 файлов в корне `AutoDraw_Stage20/`.
- Создан `DOCUMENTATION_INVENTORY_2026-11-03.md` с классификацией, назначением, статусом использования, выявленными расхождениями и правилами дальнейшего ведения.
- В `docs/README.md` исправлено устаревшее описание INT006R visual gate, ранний CHALK next-steps plan помечен историческим, убраны дубли FILL-001 и добавлена ссылка на инвентаризацию.
- В `TASKS.md` зарегистрирована завершённая задача DOC-016; в `DECISIONS.md` добавлено DEC-013 о едином источнике текущего статуса.
- Удаление файлов не выполнялось: действует DEC-002 о сохранении исторических Markdown-материалов; `TEMP_PLAN_OUTLINE_FIRST_FILL.md` дополнительно защищён до закрытия временного плана.
- Изменялись только Markdown-файлы. Исходники, тесты, конфигурации, workflow и экспериментальные данные не затрагивались. Проверка полного набора ссылок после этих изменений ещё требует отдельного прохода.


## 2026-11-03 — FILL-001 fixed-radius planner increment

- Добавлен `source/preparation/chalk_fill_fixed_radius_planner.py`: boundary-aware distance-transform inset, fixed-radius horizontal centerlines, round-capped raster simulation, coverage/leakage gate и deterministic plan signature.
- Добавлен `source/preparation/tests/test_chalk_fill_fixed_radius_planner.py`: параметризованные проверки 15 shape×radius cells, radius isolation, deterministic output и invalid-input rejection.
- Отдельная Python raster simulation на frozen masks: 15/15 cells, coverage 99,962–100%, leakage=0. Это не pytest и не CI.
- Все generated plans остаются non-executable; sampling estimate не трактуется как exact CHALK. Live captures и production planner не затрагивались.
- Commits: initial planner edit `8ed85d04ac92aa9dae26cded3628f618e30f2135`, validation fix `358b0ea48d1df0103246ccd04fd9eb09e9e7b2d2`, regression tests `07bda99f1cf2db7c814a5e1579fc9e0a7534862a`, separate planner module `5a33da337fabdfbae61f6ec1d8ead9db40d02057`. Frozen-mask module was restored byte-for-byte from the pre-change branch version in `5b7c6e8bb98cbcedc12ca6a3e6c78c2d64cd385d`; it is not part of the final functional diff.
- CI/pytest для актуального HEAD ожидаются; следующий gate — подтвердить тесты, затем matrix/block/journal harness.


## 2026-11-03 — FILL-001 matrix and analyzer increment

- Добавлен `source/preparation/chalk_fill_matrix.py`: детерминированный manifest на 45 ячеек (3 формы × 5 радиусов × 3 повтора), mask/plan/task identity, dynamic expected_strokes, atomic manifest write/load.
- Реализована fail-closed capture validation: requested/observed radius, exact CHALK = post-pre pointCount, completed stroke count, coverage ≥99%, leakage=0, Monitor/Bridge/event integrity.
- Analyzer проверяет полноту матрицы, duplicate/missing/unexpected task IDs и duplicate run IDs; считает exact CHALK statistics отдельно по shape/radius.
- Добавлен `tests/test_chalk_fill_matrix.py` с offline regression coverage для 45 cells, signature tampering, duplicate/missing cells, manifest round-trip, capture gates и analyzer.
- Live execution не реализовано и не запускалось. Manifest/tasks запрещают automatic execution; exact CHALK не заменяется геометрическими estimates.
- GitHub combined status для новых commits возвращает пустой список checks; pytest и полный CI на актуальном HEAD не подтверждены.
- Следующий gate: получить полный CI PASS/Windows portable build; затем preflight, live 45 captures и PNG audit.

- Ужесточен capture contract: обязательны per-stroke CHALK deltas с суммой exact CHALK, before/after PNG evidence и `png_audit_status=passed`; добавлены regression tests на несоответствие stroke sum и pending PNG audit.


## 2026-11-03 — FILL-001 capture fixture contract correction

- При проверке актуальных исходников обнаружено несоответствие: `CAPTURE_FIELDS` и validator требуют `stroke_chalk_deltas`, `before_png`, `after_png`, `png_audit_status`, но тестовый helper `_capture()` эти поля не формировал. Тесты полного 45-capture журнала поэтому не могли корректно пройти.
- Исправлен `source/preparation/tests/test_chalk_fill_matrix.py`: helper формирует per-stroke deltas, сумма которых равна exact CHALK, и явные тестовые PNG placeholders со статусом audit; добавлены проверки отсутствующих/неверных evidence fields.
- Изменение: [70323a8](https://github.com/Kiddos19882/AutoDraw/commit/70323a8e65ccddd201aa412263aac9efe18ec099).
- Проверено чтением committed test file и diff. Pytest не запускался; combined status пуст, workflow run через доступный commit-run endpoint не возвращён. CI PASS не заявляется.
- Это исправление касается только synthetic unit-test fixtures. Оно не создаёт PNG-файлы, не доказывает независимый PNG audit и не интегрирует FILL-001 matrix с реальными Game Monitor reports. Live execution запрещён до отдельного software gate и подтверждения evidence adapter.


## 2026-11-03 — FILL-001 Game Monitor/evidence contract audit

- Сверен реальный event stream `game_monitor.js` с агрегированным capture schema. Monitor выдаёт `DRAW_SAMPLE` с `strokeId`, `pointDelta`, `after.pointCount`, а также DRAW_START/DRAW_END, BRUSH_CHANGE и POINT_QUOTA_UPDATE; FILL-001 adapter, который преобразует export в validated capture, пока отсутствует.
- Установлено, что текущая PNG validation проверяет только непустые пути и строку `png_audit_status=passed`; существование файлов, SHA-256 и pixel-level соответствие frozen mask не проверяются. Unit-test PNG paths — placeholders.
- Выявлено, что sampling P1 не записан и не проверяется в текущем matrix task/capture schema, несмотря на упоминание P1 в design.
- В [FILL-001 harness design](CHALK_FILL001_HARNESS_DESIGN_2026-11-03.md) добавлена точная граница реализации и обязательные software gates. Live execution остаётся запрещённым до реального Monitor adapter, независимой PNG/mask validation, sampling binding, CI PASS и Windows preflight.


## 2026-11-03 — FILL-001 Game Monitor capture adapter implementation

- Добавлен `chalk_fill_capture_adapter.py`: преобразование export schemaVersion=1 в FILL-001 capture; pairing DRAW_START/DRAW_END по strokeId; расчёт per-stroke/run CHALK по exact pointCount; observed radius validation.
- Учтена семантика Game Monitor: первая точка штриха добавляется в onDrawStart до polling baseline, поэтому initial delta сверяется отдельно от последующих DRAW_SAMPLE.pointDelta.
- Sampling P1 (step=4, delay=5 ms) закреплён в каждой matrix task и capture contract.
- Добавлена фактическая PNG validation: чтение PNG 460×240, SHA-256, RGB difference threshold=8, coverage и leakage against frozen mask.
- Добавлены обязательные external run_id и bridge diagnostics с binding по run_id/eventCount; bridge failures/sequence gaps проверяются fail-closed.
- Добавлены `test_chalk_fill_capture_adapter.py` с синтетическим Monitor event stream и PNG fixtures. Это unit fixtures, не реальные captures.
- Ограничения: Monitor export сам не содержит runId/sequence number; sampling profile не наблюдается самим Monitor; bridge report пока передаётся вызывающим кодом и не имеет криптографической подписи; PNG crop threshold требует реального preflight.
- Проверка: committed source/test files перечитаны через GitHub. Pytest не запускался, CI status для новых commits не подтверждён; live execution запрещён.


## 2026-11-03 — FILL-001 matrix schema v2 and adapter hardening

- Frozen P1 metadata проверяется не только в capture, но и при validate matrix; schema version повышена до 2, чтобы старые manifests без sampling identity не принимались как новые.
- Adapter привязан к версии Game Monitor 0.2.1 и повторно проверяет frozen target mask SHA-256.
- Bridge diagnostics связываются с внешним run_id и eventCount; synthetic adapter fixture обновлён под этот контракт.
- Повторно просмотрены source/test файлы и последние 20 commits. Ветка существует; последний HEAD на момент проверки — `be8e1dcd3173fd2320b9d6271cb619e428f731aa`.
- Combined status пуст, workflow runs для последнего commit не возвращены. Pytest/CI/Windows build не подтверждены. Текущая реализация не объявляется готовой к live запуску.


## 2026-11-03 — FILL-001 adapter integrity regression coverage

- Добавлены negative tests на несовпадение суммы DRAW_SAMPLE и exact per-stroke CHALK, неверную привязку bridge report к run_id и leakage за пределами frozen mask.
- Adapter дополнительно проверяет frozen target mask SHA-256 и закреплён за Game Monitor 0.2.1.
- Текущий HEAD на момент этой записи: `a3b00cd01363d14c25c4ff3f73b74cda77bd059f`. Pytest/CI не запускались или не подтверждены; live execution остаётся BLOCKED.


## 2026-11-03 — справочник Game Monitor и Bridge

- Проверены актуальные исходники `game_monitor.js` (Monitor 0.2.1), `game_monitor_bridge.js`, `game_monitor_bridge_server.py`, профильный README, docs index и module reference в `feature/image-geometry-optimization`.
- Создан `docs/GAME_MONITOR_BRIDGE_REFERENCE.md`: публичные методы Monitor и Bridge, оборачиваемые методы BoardPane, события, snapshot CHALK, WebSocket протокол, функции collector/методы RunRecorder, session/run JSON schema, запуск, интеграция и ограничения.
- В `docs/README.md` добавлена ссылка в раздел справочников; `docs/MODULE_REFERENCE.md` дополнен фактическим составом компонентов.
- Изменялись только Markdown-файлы. Исходники, тесты, конфигурации, workflow и экспериментальные данные не менялись; live-тесты не запускались.


## 2026-11-03 — аудит пользовательской интеграции FILL-001

- Проверены текущая ветка/HEAD, последние 20 коммитов, README приложения, docs index, PROJECT_STATUS, TASKS, ROADMAP, DECISIONS, UI integration map, FILL-001 temporary plan/design и профильные исходники.
- Подтверждён HEAD `01cb37d6cb8fc7c5ec56e648330abda31875f15b`; последние три коммита перед аудитом — документационные. Compare `master...feature/image-geometry-optimization` вернул `diverged`, ahead=2529, behind=5. Merge/rebase не выполнялся; master не менялся.
- Прослежен call graph: BrushBehaviorTestTab → integrated_app transfer/start callbacks → Stage 6 → execution diagnostics. В Brush Test UI не найден FILL001 workflow; в executor override allowlist отсутствует FILL001; runtime binder в Stage 6 является post-execution hook.
- Подтверждено, что `attach_fill001_experiment_context()` существует, но его вызов из пользовательского UI/runner не обнаружен. Matrix сохраняет `execution_allowed=false` и `safe_to_execute=false`.
- Создан [CHALK_FILL001_AUTODRAW_INTEGRATION_AUDIT_2026-11-03.md](CHALK_FILL001_AUTODRAW_INTEGRATION_AUDIT_2026-11-03.md); обновлены UI integration map, FILL-001 design/temporary plan, PROJECT_STATUS, TASKS, ROADMAP и docs index.
- Вывод: runtime binder software gate не равен интеграции пользовательского запуска. Шаг 3 FILL-001 должен включать UI/runner handoff до Windows live preflight. Код, тесты, production defaults, данные экспериментов и master в этой работе не менялись.
- Проверки: статическое чтение исходников и GitHub compare. Локальные тесты, Windows live run, PNG preflight и CI для документационных изменений не запускались.

## 2026-11-03 — FILL-001: исправление разделения logical canvas и client ROI

- Повторно проверены branch `feature/image-geometry-optimization`, HEAD до начала работы `f18cfb3fb595bce5f2f233ccbd31a01a27567b7e`, последние 20 коммитов, управляющие документы, временный план FILL-001, UI, capture adapter и существующий logical→screen transform. GitHub Contents API не предоставляет локальный `git status`; чистота локального worktree не подтверждается.
- Код подтверждает: `get_canvas_size()` возвращает логические 460×240; `get_canvas_area()` возвращает фактический calibrated screen ROI. Блокировка находилась в `chalk_fill_ui.py`, где PNG crop принудительно требовал физические 460×240, и в `chalk_fill_capture_adapter.py`, где audit принимал только `(240,460,3)`.
- Удалено требование физического ROI 460×240. UI теперь проверяет границы actual ROI в screenshot, сохраняет crop в его фактическом размере, фиксирует ROI в attempt record и требует совпадения before/after ROI.
- Дополнительно проверяется, что calibrated ROI не изменился между before capture и handoff, `generation.screen_transform.screen_roi` DrawingPlan совпадает с ROI before PNG, after capture имеет обязательную пару before, а finalize отклоняет attempt record без calibrated ROI; adapter отклоняет отрицательные origin координаты.
- PNG adapter теперь rasterize frozen logical mask 460×240 в размеры screen PNG методом nearest-neighbor; проверяет uniform scale с допуском 1%, сохраняет ROI, transform и raster scale, продолжает применять RGB threshold=8, coverage ≥99% и leakage=0. Runtime adapter принимает calibrated screen ROI.
- Добавлены regression tests для client ROI 581×304, runtime capture transform, non-uniform ROI rejection, ROI metadata mismatch, scaled leakage и UI crop 581×304. Эти тесты добавлены, но их локальный/CI запуск пока не подтверждён.
- Документация синхронизирована: DEC-016, FILL-001 harness design, временный план, TASKS, PROJECT_STATUS, ROADMAP, UI_INTEGRATION_MAP, `source/game_monitor/README.md`, CHANGELOG. Зафиксировано: 460×240 — логическая система координат движка, не физическое требование к клиентскому экрану. Размер игровой доски не меняется ради AutoDraw.
- Windows live preflight не выполнялся; 45 live captures остаются BLOCKED. `master`, production estimator/defaults и исходные experiment captures не изменялись.

## 2026-11-03 — FILL-001 client ROI correction: CI confirmation

- Проверен GitHub Actions workflow run [41686091985](https://github.com/Kiddos19882/AutoDraw/actions/runs/41686091985) для code/test HEAD `031913c64da5f25921d74f426a2c7778c02130ee`: общий conclusion SUCCESS.
- Preparation and G3 matrix tests: `778 passed, 24 warnings, 82 subtests passed` (Windows runner). Game Monitor/Bridge, Executor regression, Application integration, INT-006 pixel-level PNG audit — SUCCESS. Optional algorithm benchmarks — SKIPPED.
- Windows portable build и startup smoke-test — SUCCESS; artifact `autodraw-g3-preflight-build` (636,529,516 bytes, artifact ID `13254104951`, retention 7 days) загружен: https://github.com/Kiddos19882/AutoDraw/actions/runs/41686091985/artifacts/13254104951
- Software gate шага 1 подтверждён на исправленном code/test HEAD. Это не live game session: FILL-001 one-task Windows preflight, реальные PNG/coverage/leakage и Bridge/executor runtime evidence всё ещё не получены. Шаги 4–5 остаются BLOCKED.


## 2026-11-03 — FILL-001 CI run 41692129486 завершён SUCCESS

- Повторно проверен GitHub Actions run [41692129486](https://github.com/Kiddos19882/AutoDraw/actions/runs/41692129486).
- Application integration, Game Monitor/Bridge, Preparation/G3, Executor regression и INT-006 pixel-level PNG audit завершились SUCCESS; Windows portable build и startup smoke-test также SUCCESS. Optional algorithm benchmarks — SKIPPED.
- Получен список artifacts. Windows portable build `autodraw-g3-preflight-build`, ID `13258221572`, доступен и не истёк: https://github.com/Kiddos19882/AutoDraw/actions/runs/41692129486/artifacts/13258221572.
- Программный gate FILL-001 закрыт. Следующий шаг — пользовательский one-task Windows live preflight `rectangle / radius 10 / repeat 1`; live evidence в этой проверке не создавались.
- 45-cell FILL-001 matrix не запускалась. Код, production defaults, estimator и `master` не изменялись.


## 2026-11-04 — FILL-001 Bridge activity-window correction

- Исправлен `chalk_fill_runtime_binding.py`: фактическое окончание активности Bridge run вычисляется по browser performance clock (`started_at_performance_ms` и максимальному `events[].t`); `finished_at_utc` остаётся временем persistence и проверяется относительно idle finalization grace.
- Строгий guard `non_consuming_stroke_candidate_count == 0` для выбранного task run сохранён.
- Добавлены regression tests на calibration run, чьи события закончились до executor start, несмотря на позднюю финализацию, и на полную загрузку/разбор/hash Bridge JSON размером более 27 MiB.
- Code commit `95a8d1799cd2cbbba09929cc5086a3655ba90c78`; test commit `870bebce6b39e782f70ef9f476a324ee840c05ae`. Тесты/CI на новом HEAD пока не подтверждены; live preflight не запускался.


## 2026-11-04 — FILL-001 follow-up: полный task Bridge run и исчерпание квоты

- Проверен пользовательский evidence commit [73d14a1](https://github.com/Kiddos19882/AutoDraw/commit/73d14a1784a5a9f8ef29bc0e197b75352f2650af) на ветке feature/image-geometry-optimization; branch HEAD — 73d14a1, master не изменялся. Compare: ahead 2713 / behind 5; локальный git status через GitHub API недоступен.
- Полностью прочитан Bridge run размером 27 932 334 bytes. Первый run — calibration CHALK=0; второй run связан с executor по event activity window. Exact task CHALK=5999 согласуется с pre/post pointCount, sampled deltas и per-stroke quota updates.
- Обнаружено 131 pointer candidates, 128 consuming strokes и 3 non-consuming candidates после исчерпания квоты 6000. Runtime binder должен отклонить task из-за stroke_count mismatch и non-consuming candidates; strict checks сохранены.
- Executor report был записан примерно за 3.44 s до Bridge run finalization, что объясняет временный UI pending. После persistence строгая проверка должна дать окончательный отказ.
- Before/after PNG просмотрены визуально; количественный frozen-mask audit не запускался. 5999 — точный фактический расход до лимита, но полная стоимость task неизвестна, так как последние три штриха не потребили ресурс.
- Исходники, тесты, настройки и workflow не менялись; live experiment не запускался повторно. 45-cell matrix остаётся BLOCKED. Следующий шаг — статический анализ frozen plan/resource budget и документированное решение по over-budget/censored outcomes.

## 2026-11-04 — FILL-001-RS PNG audit affine alignment correction

- Перечитаны актуальные README/docs index, управляющие документы, регламенты, FILL-001 plan, postmortem, source adapter, coordinate transform, planner и regression tests.
- По committed live evidence серии `fill001-rs-preflight-20261104-7.04` подтверждены executor 27/27 strokes, radius=10, exact pointCount 1→1261 (CHALK=1260), без Bridge sequence gaps/drops/errors/send failures. PNG gate ранее отклонил capture: coverage=97.673218%, leakage=28.
- Найдено статическое несоответствие: executor использует scale=(ROI dimension−1)/logical dimension; PNG audit использовал PIL resize с ROI dimension/logical dimension. Это разные affine transforms. Для rectangle mask и ROI 581×304 различие двух raster masks составляет 606 pixels.
- Исправлен `chalk_fill_capture_adapter.py`: screen mask строится inverse nearest-neighbor sampling с теми же scale_x/scale_y, что и `transform_logical_brush_plan_to_screen()`. Метаданные audit отражают единый transform.
- Обновлён `test_chalk_fill_capture_adapter.py`: synthetic ROI fixture формирует mask по согласованному pixel-center mapping; проверяются равенство raster/executor scales и метод resampling.
- Commits: [4797aa5](https://github.com/Kiddos19882/AutoDraw/commit/4797aa5e2e3d9f78656c91dcddf285304eae55c1), [a950084](https://github.com/Kiddos19882/AutoDraw/commit/a950084db14fd1560aa15f099da4a0108c9631e7). Затем синхронизирована документация.
- Локальный git status и локальный pytest через GitHub API недоступны. Для новых commits нет подтверждённых CI statuses; committed PNG replay после исправления ещё не выполнен.
- Исправление alignment не является доказательством устранения всего недопокрытия: 606 mask pixels — вклад различия raster conventions, а не измерение новых coverage/leakage. Acceptance thresholds не менялись.
- Не запускались live game experiments; 45-task matrix остаётся BLOCKED. Production estimator/defaults, P1, frozen masks, исходные captures и master не менялись.


## 2026-11-04 — независимая regression-проверка executor transform

- Усилен `test_chalk_fill_capture_adapter.py`: synthetic ROI fixture получает scale из фактической `transform_logical_brush_plan_to_screen()`, проверяет преобразование крайних координат (0,0) → (W−1,H−1) и сравнивает scale PNG audit с метаданными executor transform.
- Это устраняет слабость прежнего теста, где fixture повторял формулу вручную и мог совпасть с audit при расхождении с executor helper.
- Commit: [c399433](https://github.com/Kiddos19882/AutoDraw/commit/c399433af7f2e7bc547a9f35274aaf24d3c3a52e).
- Проверка pytest и CI для нового commit пока не подтверждена: combined status пуст, PR-triggered workflow runs отсутствуют; локальная среда репозитория недоступна.

## 2026-11-04 — проверка CI evidence boundary после affine correction

- Проверен GitHub Actions run [41772866679](https://github.com/Kiddos19882/AutoDraw/actions/runs/41772866679): все обязательные jobs SUCCESS, optional benchmarks SKIPPED; Preparation/G3 job включает `pytest -q -ra tests` и exhaustive static sweep artifact.
- Этот run относится к более раннему code/test HEAD `974f949`; он не покрывает последующие commits `4797aa5`, `a950084`, `c399433`.
- Проверен regression test: helper вызывает реальный `transform_logical_brush_plan_to_screen()` и использует возвращённые `scale_x/scale_y`; фактический pytest после изменения не запускался в доступной среде.
- GitHub connector `fetch_commit_workflow_runs` возвращает только PR-triggered runs; открытых PR для рабочей ветки не найдено. Поэтому отсутствие результата не используется как доказательство отсутствия push CI. Push workflow ожидается по path filter `source/**`, но актуальный run не удалось независимо получить.
- Committed PNG replay исправленным audit и live runtime эксперименты не выполнялись. 45-task matrix остаётся BLOCKED.
## FILL-001-RS — CI failure analysis and synthetic fixture alignment — 2026-11-04

GitHub Actions run [41778045384](https://github.com/Kiddos19882/AutoDraw/actions/runs/41778045384) завершился с failure в Preparation/G3: **799 passed, 5 failed, 24 warnings, 82 subtests passed**. Game Monitor/Bridge, Application integration и Executor regression — SUCCESS; Preparation/G3 — FAILURE; optional benchmarks, INT-006 PNG audit и Windows portable build/startup smoke-test — SKIPPED. Артефакты этого run не опубликованы.

Пять отказов локализованы в FILL-001 synthetic PNG tests:
- native 460×240 fixtures записывали frozen logical mask напрямую, не применяя executor logical→screen mapping; audit корректно применял pixel-center transform, поэтому fixtures создавали ложное расхождение;
- non-uniform ROI test вызывал executor transform внутри fixture builder и получал ValueError до вызова проверяемого PNG audit;
- runtime-binding test использовал тот же несогласованный native PNG fixture.

Обновлены только тесты:
- [1f28436](https://github.com/Kiddos19882/AutoDraw/commit/1f28436ab20fe949e4d53cfeea4a5560ed3cbcae) — native fixtures теперь используют тот же helper, что и scaled ROI tests; non-uniform audit получает реальные PNG paths; leakage assertion выбирает пиксель вне screen-rasterized mask.
- [0f23731](https://github.com/Kiddos19882/AutoDraw/commit/0f23731848f0c148fe5e1309d1e305576dd4b6b7) — runtime-binding fixture строится с масштабом из фактического transform helper.

Production source, frozen masks, PNG thresholds, исходные live captures и production defaults не менялись. Новые commits пока не имеют подтверждённого CI результата; локальный pytest недоступен через GitHub API. Повторный CI обязателен до committed PNG replay. Capture остаётся REJECTED/BLOCKED, coverage≥99% и leakage=0 не менялись; 45-task matrix не запускалась.



## 2026-11-04 — CI run 41780241017 и разбор artifacts

- Проверен run [41780241017](https://github.com/Kiddos19882/AutoDraw/actions/runs/41780241017), checkout code/test HEAD `0f23731848f0c148fe5e1309d1e305576dd4b6b7`. Все обязательные jobs SUCCESS: Application integration, Executor regression, Preparation/G3, Game Monitor/Bridge, INT-006 PNG audit, Windows portable build/startup smoke-test. Optional benchmarks SKIPPED.
- Получены и распакованы artifacts: FILL-001-RS static sweep (ID 13299430831), INT-006 PNG analysis (13299470914), INT-006 frozen CHALK validation (13299121807), INT006R live validation (13299101877), INT006R visual review source (13299381257), portable build (13299481008).
- Static sweep: 2,238 candidates / 62 accepted; 15 selected shape×radius cells прошли offline raster quality gate. Estimated sampling points остаются proxy, не exact CHALK.
- INT-006 PNG analysis: 90/90 captures valid; 549 stroke rows, all coverage=1.0, gaps=0. Frozen CHALK validation: 45/45 accepted, 0 missing/rejected; safety margin not established, production eligibility not validated.
- INT006R: 45/45 accepted; pre/post pointCount CHALK и per-stroke deltas доступны. Радиус 1/10/30 при P1 дал небольшие немонотонные различия по D1–D5; см. TASKS/PROJECT_STATUS для средних значений. Visual source содержит 180 files (45 before/after pairs); автоматический analyzer оставил 45/45 visual gates pending manual review.
- Быстрый обзор контактного листа показал ожидаемое изменение толщины следа между радиусами, без очевидной потери целевых фигур на миниатюрах; это только предварительный triage, не замена индивидуальному review всех пар.
- Не запускались live игровые эксперименты в этой сессии. Production model/estimator/defaults, executor и sampling defaults не изменялись. Static sweep не подтверждает game runtime и расход CHALK.

## 2026-11-04 — фиксация обязательного FILL-001-RS evidence replay

Создана/актуализирована блокирующая задача **FILL-001-RS-PRE-REPLAY-001**: до любого следующего live запуска требуется повторно проверить неизменённые before/after PNG и связанное evidence исходного запуска `fill001-rs-preflight-20261104-7.04` актуальным PNG audit. Проверка должна сохранить hashes входов, версию analyzer, runtime binding, coverage и leakage.

Исходные данные задачи: 27/27 strokes, pointCount 1→1261 (exact CHALK=1260), Bridge diagnostics без ошибок; прежний PNG gate отклонил capture с coverage=97.673218% и leakage=28 при неизменных критериях ≥99% / 0. Успешный CI 41780241017 проверяет software gates, но не подтверждает replay исходных live PNG.

До закрытия задачи запрещены новый live запуск FILL-001-RS и запуск 45-task matrix; игровые эксперименты не входят в offline replay и требуют отдельного разрешения. Изменение production-кода/defaults, frozen masks, исходных plans/manifest и acceptance thresholds не разрешено. Доступность бинарных PNG из предполагаемого commit `530821497ce3a6bd5152318a78e1f06cb836f288` ещё не подтверждена.

## 2026-11-04 — offline raster diagnosis: краевые пропуски и contour-pass sweep

Повторно построена frozen rectangle mask из исходной формулы `chalk_fill_experiment.py` и воспроизведена геометрия committed plan `fill001-rs-preflight-20261104-7.04-rectangle-r10-s5-o0-rep1`. Получены 27 centerlines (y=55..185 с шагом 5), target area=44 653 px. Rasterization по текущей OpenCV line/cap модели оставляет 304 uncovered target pixels: 80 в верхней полосе, 80 в нижней, 72 у левой боковой границы и 72 у правой; в центральной внутренней области пропусков нет. Leakage=0. Это относится только к planner model; фактический PNG audit имеет coverage=98.430600%, leakage=11, и его пиксельные координаты пока не извлечены.

Затем выполнен exploratory sweep единственного замкнутого contour pass поверх текущих scanlines. Контур получен из frozen mask после erosion эллиптическим ядром:

| Inward offset | Coverage | Leakage | Uncovered | Offline gate |
|---:|---:|---:|---:|---|
| 5 px | 99.964168% | 32 | 16 | FAIL |
| 6 px | 99.516270% | 0 | 216 | PASS |
| 7 px | 99.372942% | 0 | 280 | PASS |
| 8 px | 99.328153% | 0 | 300 | PASS |

Для offset=6 contour представлен одной замкнутой линией с 64 вершинами и длиной около 846.225 logical px в этой OpenCV approximation. Длина пути не является оценкой расхода CHALK. Разница между offset 5 и 6 показывает узкий trade-off coverage/leakage и необходимость точной подгонки под реальный renderer footprint.

Статус: edge concentration подтверждена для offline planner model (E1), но остаётся E0 для actual PNG residuals. Contour pass — exploratory candidate, не внедрён, не выбран и не live-validated. Не менялись код, тесты, конфигурации, frozen plan, thresholds, production defaults; live experiment не запускался. Следующий шаг — actual PNG coordinate breakdown и сравнение с renderer footprint.

## 2026-11-04 — подготовка actual PNG pixel-coordinate breakdown

Проверено текущее состояние рабочей ветки `feature/image-geometry-optimization`: до начала изменений HEAD был `0f066bb11095420e38770f149fdcd276b3ccbd0b`; последние 20 commits просмотрены, они включали последовательные документационные записи FILL-001-RS. Ветка diverged относительно `master` (ahead 2859 / behind 5 на исходном HEAD); `master` не изменялся. Локальный `git status` недоступен через GitHub API.

Получены и просмотрены неизменённые committed `before.png`/`after.png` FILL-001-RS capture. В исходном replay test добавлена test-only диагностика фактической screen pixel map: exact same inverse affine nearest-neighbor mask mapping as PNG audit, координаты uncovered target/leakage pixels, spatial zones, per-row counts, connected components и расстояния residuals до scanline segments после affine transform. Для endpoints используется непрерывное точное affine mapping без дополнительного округления. Исходные PNG, capture evidence, production adapter, frozen plan/mask и acceptance criteria не менялись.

Commits: `e62b69295f9df1c67a485a5c900fbcf1ceba87eb` (diagnostic) и `d337f4240e83488273152f65992032beca395781` (точные affine endpoints). Workflow path filter включает `AutoDraw_Stage20/source/**`, поэтому изменения подходят под push trigger `.github/workflows/geometry-tests.yml`; однако отдельный run ID/logs не удалось получить доступными GitHub Actions tools, а combined status для commit пока возвращает пустой список. Следовательно, diagnostic пока не подтверждён запуском.

Текущий audit result остаётся coverage=98.430600%, leakage=11, status=failed; exact CHALK=1260 и runtime binding PASS не отменяют PNG gate. 45-task matrix остаётся BLOCKED; live запусков не выполнялось.
## 2026-11-04 — actual PNG residual map confirmed by CI

Located push-triggered workflow through GitHub Actions REST endpoint (commit-associated wrapper only exposed PR runs and returned empty results). Workflow 41787492122, HEAD d337f4240e83488273152f65992032beca395781, completed SUCCESS. Jobs: Executor regression SUCCESS; Game Monitor/Bridge SUCCESS; Preparation/G3 SUCCESS (804 passed, 24 warnings, 82 subtests passed); Application integration SUCCESS; INT-006 pixel-level PNG audit SUCCESS; Windows portable build/startup smoke-test SUCCESS; optional algorithm benchmarks SKIPPED.

Retrieved Preparation/G3 job logs and extracted actual committed FILL-001 PNG diagnostic. Corrected audit reports coverage 98.430600%, leakage 11, status failed. Pixel diagnostic reports 1116 uncovered target pixels, distribution top=244, bottom=239, left-middle=134, right-middle=499, interior/other=0. Largest uncovered component area 870, screen bbox xywh [460,63,33,178], on right perimeter. Nearest scanline centerline distances: <=2px=10, 2–5px=320, 5–10px=786, >10px=0. Eleven leakage pixels localized at (116,63),(117,63),(92,78),(91,81),(90,83),(90,84),(89,85),(90,85),(90,218),(116,240),(117,240).

Evidence supports a perimeter/endpoint coverage problem and does not support an interior scanline-gap explanation for this capture. Asymmetry (right-side uncovered region vs sparse left-side leakage) means actual game brush footprint, screen-space radius semantics and endpoint caps must be inspected before choosing a contour offset or changing plan. The 304-pixel OpenCV planner residual and 1116-pixel screen PNG residual are different measurements.

No production code, frozen plan, mask, thresholds or live game state changed. No new live experiment. Exact CHALK=1260 remains bound to previously committed runtime run; capture REJECTED and 45-task matrix BLOCKED.


## 2026-11-04 — FILL-001-RS: статический разбор полного game renderer bundle

Полный main.min_570122a1.js из master получен через GitHub Contents API (blob SHA 28838e803dcc6f85efb13febd93cc9e0f5046ffc, размер 4 785 687 bytes; master commit 9a3453aeb847b66041bc83d6f4a56ecaf33a993a). Файл не копировался в feature branch.

Подтверждено по коду:
- BoardPane.onDrawStart() добавляет начальную точку, пересчитывает ресурс и включает ENTER_FRAME listener.
- BoardPane.onDrawing() считывает одну текущую позицию за кадр, проверяет локальные границы и пытается добавить точку.
- BlackBoardAtom.pushPoint() подавляет только точное совпадение с последней точкой текущего stroke.
- BoardPane.updateLess() проходит все накопленные atom.points и вычисляет less=max-pointCount; вызов происходит после принятия каждого sample. Это O(N) работа в пути рисования и потенциальная гипотеза для снижения FPS на длинных штрихах.
- BoardPane.redraw() передаёт atom.radius в graphics.lineStyle как thickness; caps/joints явно не задаёт.
- Painter.drawSmoothLine() использует midpoint/curveTo и завершает путь lineTo последней точки. Single-point smooth path создаёт moveTo+lineTo в одну координату; normal single-point path только moveTo.

Найден display scaling BoardPane внутри BlackBoardItem: logical 460×240, scaleX=scaleY=boardMask.width/460. Это не доказывает transform интерактивного BoardPane в painter popup, который используется в preflight.

Bridge JS уже формирует frame_probe intervals между началом и концом штриха. Следующая задача — проверить, что intervals сохраняются/доступны в Bridge run evidence, затем сопоставить с per-stroke CHALK. Номинальные 48 FPS не считать фактической частотой кадров конкретного запуска.

Не установлены: renderer caps/joints defaults, реальная rasterization нулевого сегмента, popup board transform и screen-space brush footprint. Статический уровень E1; runtime/live capture не выполнялись. Production code, tests, configs, frozen plan, thresholds и raw evidence не менялись.


## 2026-11-04 — FILL-001-RS: per-stroke point cadence и Bridge telemetry

Прочитан сохранённый Bridge run 6a17a297 (JSON 4 655 454 bytes): 27 strokes, 1260 POINT_QUOTA_UPDATE events, exact CHALK=1260. По каждому stroke вычислены duration, pointCount delta и интервалы между событиями. Диапазон 41–48 точек/штрих, duration 1450–1645 ms, median update interval 33 ms, cadence 28.26–29.50 points/s. Первые 9 strokes в среднем 28.734 points/s, последние 9 — 29.049; явного падения cadence при росте pointCount до 1261 не видно в этом run.

Run-level frame_probe: 2579 browser requestAnimationFrame intervals, average 59.997 FPS, median 60.024 FPS, 27 probes. Это не прямое измерение Egret ENTER_FRAME. Старый finalizer агрегировал raw intervals и очищал frame_probes; исходная per-stroke rAF серия для этого run потеряна, но cadence принятых точек восстановлена из сохранённых POINT_QUOTA_UPDATE timestamps.

Изменения телеметрии:
- 02907aca — browser frame_probe включает strokeId;
- ec2ed77 — Bridge Server сохраняет raw intervals, формирует frame_probe_by_stroke и per_stroke_metrics;
- ead8808 и 730590d — regression test для per-stroke timing и точного 60-Hz fixture.

CI 41840281018 для HEAD 730590d на момент записи выполняется; результаты не объявляются PASS. Новых live runs не было. Frozen plans, masks, thresholds, production defaults и raw capture evidence не менялись.


## 2026-11-04 — Egret API defaults и painter popup transform

Bundle дополнительно подтверждает: Main UI задаёт nominal stage.frameRate=48 и StageScaleMode.NO_SCALE; PainterPopup имеет размер 676×379, интерактивный BoardPane — logical 460×240 без собственного scaleX/scaleY. Это уточняет local geometry, но не раскрывает parent/global transform и browser device-pixel ratio.

В официальном Egret Engine 5.2.18 egret.d.ts lineStyle thickness описан как ширина линии, omitted caps/joints имеют defaults ROUND. Поскольку версия Egret runtime, загруженная самой игрой, не установлена, round caps/joins считаются обоснованной гипотезой совместимого API, но не подтверждённым фактом deployed runtime. Zero-length path rasterization остаётся неизвестной. Источник: https://app.unpkg.com/egret-engine@5.2.18/files/build/egret-wasm/egret.d.ts, Graphics.lineStyle, строки 6063–6090.


## 2026-11-04 — per-stroke telemetry CI verification and renderer gate synchronization

- Проверены текущие branch HEAD и последние 20 commits через GitHub API. HEAD перед этой документационной синхронизацией: `7ff5813f8d1745fafb39f9e0152c2586a1527547`; compare с master — ahead 2895 / behind 5. Локальный git status недоступен; master не менялся.
- Проверены Browser Bridge и Bridge Server: frame_probe несёт strokeId и raw rAF intervals; collector сохраняет raw frame_probes, создаёт frame_probe_by_stroke и per_stroke_metrics. POINT_QUOTA_UPDATE cadence не приравнивается к ENTER_FRAME; browser rAF не считается частотой игрового sampling.
- Старый run `6a17a297`: 1260 POINT_QUOTA_UPDATE events по 27 strokes; median 33 ms, accepted-point cadence 28.26–29.50 points/s. Старые per-stroke rAF intervals недоступны, поскольку предыдущий finalizer очищал raw frame_probes.
- CI run [41840281018](https://github.com/Kiddos19882/AutoDraw/actions/runs/41840281018) завершился CANCELLED. Полный run [41840582147](https://github.com/Kiddos19882/AutoDraw/actions/runs/41840582147), checkout SHA `6fd3c91c3c08ea05cb9ef83ff599eb52a6f9527e`, завершился SUCCESS: Application integration, Game Monitor/Bridge, Preparation/G3, Executor regression, Windows portable build/startup smoke-test и INT-006 PNG audit — SUCCESS; optional benchmarks SKIPPED. После checkout SHA до текущего HEAD были docs-only commits.
- Artifact IDs: static sweep `13329415914`, INT-006R validation `13329411251`, INT-006 PNG analysis `13329261288`, CHALK validation `13329096463`, INT-006R visual source `13328976562`, Windows portable build `13328458043`.
- Renderer static findings уточнены: nominal stage.frameRate=48, NO_SCALE, PainterPopup 676×379, BoardPane 460×240 без local scale. Egret 5.2.18 API defaults ROUND caps/joints — только API reference; deployed runtime identity не подтверждена. Global transform, zero-length rasterization и фактический footprint остаются открытыми.
- FILL-001-RS capture остаётся REJECTED: coverage=98.430600%, leakage=11, exact CHALK=1260 (pointCount 1→1261). 45-task matrix остаётся BLOCKED. Live experiments не запускались; frozen plans/masks/thresholds/defaults не менялись.
- Изменены только управляющие Markdown-документы; исходники, тесты, конфигурации, workflow и raw experiment evidence не менялись.


## 2026-11-04 — Egret GraphicsNode / CanvasRenderer path semantics

Проверен upstream Egret core reference:
- GraphicsNode.lineStyle() подставляет ROUND для отсутствующих caps и joints;
- CanvasRenderer задаёт context.lineCap/lineJoin и выполняет context.stroke();
- WebGLRenderer в рассмотренной реализации использует CanvasRenderer для растрирования GraphicsNode перед upload в texture.
- Egret 5.2.18 API docs согласуются с этим: lineStyle thickness — ширина линии; omitted caps/joints — ROUND.

Для совместимого CanvasRenderer single-point smooth path moveTo(p)+lineTo(p) является zero-length segment. Canvas Standard удаляет такие сегменты и subpaths без линий, поэтому такой штрих не оставляет видимого следа, хотя onDrawStart уже расходует одну игровую точку. В run FILL-001-RS все 27 штрихов имели 41–48 point updates, поэтому это не объясняет его perimeter gaps.

Обнаружен отдельный риск planner-ов: footprint_pixel_bounds даёт bbox capsule, а interior_fill_planner._mark_footprint и outline_first_fill_planner помечают весь bbox covered. У круглых концов bbox углы могут не касаться фактического capsule. Это потенциальный underfill в этих planner-ах, не доказанная причина FILL-001-RS. Добавлена задача BRUSH-FOOTPRINT-CAPSULE-001; production planners не менялись.

CI workflow 41840582147 завершён SUCCESS на code/test commit 6fd3c91c3c08ea05cb9ef83ff599eb52a6f9527e. Все обязательные jobs PASS, optional algorithm benchmarks SKIPPED. Более поздние commits — documentation-only.


## 2026-11-04 — BRUSH-FOOTPRINT-CAPSULE-001 static code audit

- Проверены `brush_footprint_geometry.py`, `swept_footprint_geometry.py`, `interior_fill_planner.py`, `outline_first_fill_planner.py` и соответствующие tests.
- Подтверждено: `footprint_pixel_bounds()` возвращает AABB; generic interior planner использует AABB и как safety check, и как coverage mask. Последнее overclaims cells около round-cap ends и может пропускать fallback. Тестовый independent oracle повторяет rectangular assumption.
- `swept_footprint_geometry` использует bbox как conservative safety envelope; `outline_first_fill_planner` — для safety check, но отмечает residual только по centerline pixels.
- FILL-001/FILL-001-RS использует отдельный OpenCV round-capped rasterizer (line + endpoint circles), не вызывает generic bounds helper. Причинная связь с FILL-001-RS rejected PNG не установлена.
- Источниковая версия Egret и deployed renderer footprint не подтверждены. Это static code finding, не live/render validation.
- Изменения исходников, тестов, конфигураций и workflow не выполнялись; frozen evidence и thresholds не затрагивались.
- Следующий шаг — offline possible/guaranteed cell masks, независимые geometric tests и old/new frozen-fixture comparison; production behavior не менять до acceptance.

## 2026-11-04 — BRUSH-FOOTPRINT-CAPSULE-001 offline candidate implementation

- Добавлена функция `swept_capsule_pixel_masks()` в `brush_footprint_geometry.py`: potential cells (positive-area intersection with ideal capsule sweep) и guaranteed cells (pixel cell fully inside at least one segment capsule); pixel cells mapped back to logical space for non-uniform scale.
- Bbox остаётся broad-phase; существующий `footprint_pixel_bounds()` не удалён и не изменён. `interior_fill_planner`, `outline_first_fill_planner`, FILL-001 planner outputs/defaults не интегрированы с новой моделью.
- Добавлен `test_capsule_footprint_masks.py`: endpoints/AABB corner distinction, point disk, anisotropic scaling, polyline reversal/round join, clipping, invalid inputs.
- Commits: `5a090948ecbe927807fde4ffc5337132d131b765` (implementation), `7ffdd150ba42840737cba5f2143370e56d67bed3` (tests).
- CI run [41842587672](https://github.com/Kiddos19882/AutoDraw/actions/runs/41842587672) ещё выполняется. Independent analytic oracle и frozen fixture comparison пока не добавлены; модель не подтверждена deployed Egret runtime.
- Live tests не проводились; raw evidence, frozen plans/masks, thresholds и production defaults не менялись.

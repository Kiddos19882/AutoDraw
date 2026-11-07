## 2026-11-07 — восстановление Linux offline workflow, выпуск измеримого fixture corpus

- Добавлен самостоятельный `.github/workflows/validation-corpus-smoke.yml` (`e112d4c`), запускающий генератор на testImages с реальным committed palette profile и холстом 64×32.
- Первая попытка [42387397972](https://github.com/Kiddos19882/AutoDraw/actions/runs/42387397972) FAILED в import `shared_image_processing` (Linux PYTHONPATH); исправлен `PYTHONPATH` (`2fe37ef`), не затрагивая код приложения.
- Повторный workflow [42387485762](https://github.com/Kiddos19882/AutoDraw/actions/runs/42387485762) SUCCESS; artifact [13580167471](https://github.com/Kiddos19882/AutoDraw/actions/runs/42387485762/artifacts/13580167471) содержит проекты, планы, manifest и N summary.
- Вывод CI logs: 8 unique sources / 0 duplicates; mono N 40–88, color N 172–295; все source families unclassified. Первичные per-file значения записаны в TEST_RESULTS.
- Нельзя переносить эти результаты на 95% holdout, утверждённый запас CHALK или production eligibility: размер холста и выборка исследовательские, game execution не было.
- Программный CI [42387145503](https://github.com/Kiddos19882/AutoDraw/actions/runs/42387145503) пока не завершён; Preparation/G3, executor, game monitor, app integration и Egret reference jobs SUCCESS.

---

## 2026-11-07 — регрессия от новых repository images и устранение пропущенного запуска CI

- Проверены HEAD, 20 commits, восемь изображений в `AutoDraw_Stage20/testImages/`, test generator, Stage 8 scanline stroke schema и frozen INT-006 normalizer.
- Найдена конкретная stale assertion `unique_source_count == 1` после `0db0bcb`; прежний successful workflow запущен до добавления изображений. Прямого локального исполнения тестов не было.
- Изменён только тест `source/preparation/tests/test_generate_validation_corpus.py`: полный набор изображений, SHA-256, re-open outputs, manifest eligibility (commit `098d5599`).
- В `.github/workflows/geometry-tests.yml` добавлен push path `AutoDraw_Stage20/testImages/**` (commit `e984b68`).
- Статически подтверждено, что схема Stage 8 scanline strokes совпадает с требованиями frozen normalizer, но это не доказывает applicability frozen CHALK estimates или репрезентативность корпуса.
- Workflow `42387145503` в процессе на момент записи; не приписывать ему PASS заранее. Production executor, model и game monitor не изменялись; live CHALK measurements не выполнялись.

---

## 2026-11-07 — аудит GitHub и синхронизация CI статуса генератора

- Проверены рабочая feature branch, HEAD `0db0bcb`, последние 20 коммитов, управляющие документы, генератор и regression tests.
- CI [42352776594](https://github.com/Kiddos19882/AutoDraw/actions/runs/42352776594) завершён SUCCESS для code/test HEAD `51c731f0c25ad10af70efdfb8a46a38a73d07bc1` (2026-11-07). Успешны Preparation/G3, Game Monitor/Bridge, Executor, Application integration, Egret browser reference и INT-006 PNG audit. Windows portable build/startup smoke-test и optional benchmarks были SKIPPED, поэтому Windows сборка этим workflow не подтверждена. Текущий проверенный перед синхронизацией HEAD `0db0bcb96d20b39a01a5b6fb2614a43c1f83a916` добавил только семь файлов в `testImages/` и не менял генератор/тесты; отдельного CI для HEAD не обнаружено. Реальный пользовательский корпус ещё не сформирован, candidate manifest не является validation выборкой; N bands и safety margin не установлены, INT-007 BLOCKED. Новых live captures не выполнялось.
- Изменены только документы; код, тесты, workflow, исходные эксперименты и production defaults не менялись. Локальный git status недоступен через GitHub API.

---

## 2026-11-07 — добавлен генератор кандидатного корпуса DrawingPlan

- Изучены штатные Stage 12 image processing, Stage 8 scanline planner, .autodraw archive writer/reader, CIELAB/CIEDE2000 palette quantizer и color scanline planner.
- Добавлен CLI `source/preparation/generate_validation_corpus.py`: один исходник преобразуется в portable .autodraw с monochrome Stage 8 DrawingPlan; при передаче palette JSON дополнительно создаётся color scanline plan.
- Добавлена SHA-256 дедупликация, provenance manifest, отдельные N для monochrome и color plans, overwrite guard и повторное открытие .autodraw штатным reader.
- Добавлены tests на создание обоих форматов, проверку содержимого, дедупликацию и защиту от перезаписи.
- Добавлена документация использования и ограничений.
- Изменения выполнены только в `feature/image-geometry-optimization`; `master` не затрагивалась.
- CI и локальный запуск на реальных входных данных на момент записи ещё не подтверждены; корпус не создан, N bands не определены, live runs не выполнялись.

---

## 2026-11-07 — offline проектирование CHALK safety-margin policy

- Сверены управляющие документы, официальный INT-006 report, frozen predictions/analyzer, validation plan и код `chalk_int006_validation.py`.
- Analyzer фиксирует exact run-level residual `actual - predicted`; положительное значение означает недооценку.
- Разделены P1 max run-level underprediction=0.92 CHALK и max sum of positive per-stroke residual=1.597 CHALK.
- Уточнена структура выборки: 15 captures/profile состоят из пяти DrawingPlan с тремя повторами.
- Подготовлен design proposal: run-level residual / N, отдельная калибровка по profile/domain, округление вверх и fail-closed UNKNOWN вне области.
- Числовой reserve не утверждался; production estimator/defaults, исходники, тесты и конфигурации не менялись. Live runs не выполнялись.

---

## 2026-11-07 — зафиксирован пользовательский visual sign-off INT006R

- Пользователь подтвердил, что radius=10 визуально приемлем и предпочтителен для исследованной матрицы D1–D5.
- Решение записывается как ручной sign-off с ограниченной областью применимости; универсальный production default не объявляется.
- Сохранённый analyzer artifact не изменялся: его machine-generated поле `visual_quality_gate=pending_manual_review` остаётся исходным.
- CHALK totals по INT006R (15 captures на радиус): r1=1011, r10=1015, r30=1017. Это не доказывает, что radius=10 минимизирует расход.
- `safety_margin_status=not_established`, `production_eligibility=not_validated`; FILL-001 PNG gate остаётся отдельным блокером.
- Исходники, тесты, конфигурации и live-эксперименты не затрагивались.

---

## 2026-11-07 — предварительный визуальный обзор INT006R и residual analysis

- Скачан и просмотрен CI artifact `13553755987`: 45 after-draw PNG, 15 на каждый radius (1/10/30), 5 geometry scenarios × 3 repeats.
- Контактные листы показывают: radius=1 тонкий на коротких деталях; radius=10 сохраняет читаемость линий и деталей; radius=30 заметно огрубляет D3 intersections и D4 short details. Предварительная рекомендация — radius=10 для исследованной матрицы.
- Не присваивал visual PASS: analyzer намеренно оставляет `visual_quality_gate=pending_manual_review`; frozen numeric visual rubric и пользовательский sign-off отсутствуют.
- Суммарный exact CHALK на 15 captures: radius1=1011, radius10=1015, radius30=1017; разница 6. Это ограничено данной матрицей.
- INT-006 residuals пересчитаны по 45 accepted captures: P0 actual/predicted=1884/1925.25, MAE=2.882, RMSE=3.189, max underprediction=0.99; P1=1010/1011.81, 0.657/0.838/0.92; P2=1016/1012.32, 0.685/0.854/1.82.
- Дополнительная сумма положительных per-stroke residual в одном run: P0=1.990, P1=1.597, P2=2.157. Эти значения не объявлены safety margin.
- `safety_margin_status=not_established`, `production_eligibility=not_validated`; новых live runs не выполнялось.

---

## 2026-11-07 — исправлена run-bound renderer acceptance automation; multi-axis series PASS

- Исходный code HEAD перед работой: `0037c3b858425b07397fb410cf36b4519394465a`; ветка `feature/image-geometry-optimization`.
- Добавлена генерация отдельных offline WebGL reference для каждого нового paired-renderer run в Firefox Stage harness; в acceptance runner добавлен выбор run-bound каталога.
- Установлено по Game Monitor source, что `state_poll` — предусмотренный 25 ms fallback polling активного штриха на случай, когда listener `onDrawing` был зарегистрирован до wrapper. В четырёх новых reports positive DRAW_SAMPLE stream (включая state_poll) совпадает с quota updates по count и acceptedPoint coordinates.
- В `renderer_acceptance.py` разрешён source `state_poll` только вместе с `onDrawing_wrapper`; строгая проверка exact ordered point stream сохранена. Добавлен regression test.
- Первый CI [42320255395](https://github.com/Kiddos19882/AutoDraw/actions/runs/42320255395) создал четыре run-bound references, но четыре новых capture получили preflight rejection из-за различия имени manifest (`manifest.json` против ожидаемого фиксированного имени). Это инфраструктурный mismatch, не pixel rejection.
- Исправлен resolver manifest: expected committed name имеет приоритет, generated `manifest.json` допустим как fallback. Добавлены unit tests.
- Повторный CI [42321009715](https://github.com/Kiddos19882/AutoDraw/actions/runs/42321009715) — SUCCESS на `dd7b88815cc345660c735ebabb36f49dba67de01`.
- Formal analyzer: 6 valid inputs, 6 PASS_PER_RUN, 0 rejected, 0 duplicate IDs, 0 tool errors; vertical 3/3, diagonal 3/3; aggregate series PASS.
- Preparation/G3: 919 passed, 24 warnings, 82 subtests passed. Game Monitor/Bridge, Executor regression, Application integration, Egret browser reference и INT-006 PNG audit jobs — SUCCESS.
- INT-006 V1–V5 PNG audit: 90/90 valid. INT-006 CHALK validation: 45/45 accepted, safety margin not established. INT006R: 45/45 accepted, visual review pending manual review.
- FILL-001-RS static sweep: 2238 candidates, 62 accepted, 15 cells, passed. Committed FILL-001 PNG gate всё ещё failed: coverage=98.430600%, leakage=11.
- Новых live runs/CHALK расхода не было. Optional benchmarks и Windows portable build были SKIPPED.
- В этой серии code commits: `c364ab40fba7be66f71495d4a1fd11d0bed67a08`, `87626ebc68add090e0cf9085fe6025760a7716ad`, `dd7b88815cc345660c735ebabb36f49dba67de01`. `master` не менялась.

---

## 2026-11-07 — выполнен локальный PRR batch и сохранено evidence

- Проверена ветка `feature/image-geometry-optimization`; evidence commit до документальной синхронизации: `52e3c51a0830e09abb09b516af098069aef26de7`.
- Проанализированы успешный block journal `596e5c37813a43048395d0f596f9d971`, остановленный block `ab9b788c8199454c957036effb99e9c6`, session `0490d04b-8728-40f2-891d-e1d57d69402b`, четыре experiment JSON, четыре Monitor reports и execution reports.
- Успешный block выполнил 4/4 задания: diagonal r2/r3 и vertical r3/r2; radius=10, point_step=2, delay=10 ms, line_extension=0.
- Получены exact CHALK: diagonal 161 и 160; vertical 70 и 71. Для всех run pre pointCount=1, post pointCount=CHALK+1; DRAW_SAMPLE delta совпадает с quota delta.
- Все четыре run имеют один session ID; boardDetected/inputTelemetryEnabled=true; dropped events=0, Monitor errors=0, sequence gaps=0.
- Первоначальный block остановлен до запуска эксперимента, потому что Bridge был запущен до выбора paired-renderer scenario и input telemetry не была включена. Ошибка и recovery сохранены, неудача не скрыта.
- Траектории остаются lower-bound/incomplete из-за coalesced pointDelta; это не влияет на exact CHALK.
- Formal paired-renderer acceptance новых PNG ещё не выполнялась; три captures на ориентацию имеются с учётом repeat 1, но aggregate PASS не заявляется.
- INT-006 safety margin остаётся неустановленной; FILL-001 PNG gate остаётся failed; INT-007 заблокирован.
- CI 42309752566 SUCCESS относится к bacd03f. Для evidence commit 52e3c51 подтверждённого CI результата нет.
- В рамках этой синхронизации меняются только Markdown-документы; live runs и кодовые изменения не выполняются.

---

## 2026-11-07 — итог CI PRR implementation и повторная оценка renderer/CHALK

**GitHub Actions:** [42309752566](https://github.com/Kiddos19882/AutoDraw/actions/runs/42309752566) — **SUCCESS**.  
**Validated HEAD:** `bacd03f5eee725dbbfac0ce928b227bd23d73b0c`, branch `feature/image-geometry-optimization`.

- Все обязательные jobs завершились SUCCESS: Game Monitor/Bridge, Application integration, Preparation/G3 matrix, Egret CanvasRenderer browser reference, Executor regression и INT-006 pixel-level PNG geometry audit.
- В Preparation/G3 прошли PRR planner/journal/UI/integration regression tests, capsule benchmark и FILL-001-RS static sweep. Optional algorithm benchmarks и Windows portable build/startup smoke-test были SKIPPED; это не ошибки, но соответствующие проверки этим run не подтверждены.
- INT-006 paired-renderer analyzer пересчитал сохранённые исходные captures по текущим критериям: оба имеющихся run получили `PASS_PER_RUN` (vertical run `c860234f-995a-4789-9ac2-e05b322fe742`; diagonal run `f69cb0f4-f5d0-4ff9-a3b7-1148c38fa07f`). Однако агрегат явно сообщает `series_status=PENDING`: принято только **1/3** уникальных run на каждую ориентацию. PRR live repeats не запускались и в этом CI не создавались.
- INT-006 CHALK prediction validation: 45/45 captures приняты, missing/rejected=0; `safety_margin_status=not_established`, `production_eligibility=not_validated`. Успешная валидация модели не доказывает безопасный запас краски.
- INT006R: 45/45 captures приняты; это программная/аналитическая проверка сохранённых live evidence, не новый игровой запуск.
- FILL-001-RS static sweep step завершился SUCCESS, но он не отменяет отдельный committed PNG quality gate: ранее зафиксированы coverage 98.430600%, leakage 11, status=failed. FILL-001 остаётся BLOCKED.
- Артефакты run 42309752566: paired renderer PNG comparison (13548436614), INT-006 PNG analysis (13548237630), CHALK validation (13548436686), INT006R validation (13548501600), visual review source (13548217748), FILL-001-RS static sweep (13548680868), Egret renderer reference (13547343754), плюс Stage diagnostics и capsule benchmark. Срок хранения опубликованных artifacts — до 2026-11-20.
- Никакие новые live game runs/CHALK расход не выполнялись. GitHub Actions не имеет доступа к локальной Windows-доске пользователя.

**Следующие блокирующие шаги:** обновить локальный AutoDraw из этой ветки и выполнить PRR на тестовой доске; получить по два новых уникальных run на vertical/diagonal (итого 3/3); повторно прогнать formal acceptance; отдельно закрыть CHALK safety margin и FILL-001 PNG quality gate. INT-007 не открывать до выполнения этих условий.

## 2026-11-07 — PRR implementation synchronized; final CI triggered

- Синхронизированы PRR code, regression tests и управляющая документация.
- CI должен проверять конечное состояние ветки после всех PRR code commits; run ID фиксируется после появления GitHub Actions результата.
- Live PRR не запускался: удалённая GitHub-среда не имеет доступа к локальной Windows-сессии AutoDraw и игровой доске.

## 2026-11-07 — пакетный paired-renderer блок PRR

**Статус:** код добавлен в ветку; CI validation pending; live-запуски не выполнялись.

В существующий CHALK block runner добавлена фаза PRR для закрытия недостающих formal renderer repeats:
- ровно четыре задания: vertical repeat 2 и 3, diagonal repeat 2 и 3;
- фиксированные radius=10 и штатный executor profile 2 px / 10 ms;
- deterministic shuffle, отдельные task/attempt/experiment IDs и durable journal;
- сценарии проходят через существующий preflight, drag-установку кисти, fresh Game Monitor heartbeat, executor, exact CHALK capture, postdraw capture и fail-closed progression;
- repeat 1 намеренно не генерируется: он уже присутствует в исходной серии; PRR добавляет только две недостающие независимые попытки на каждую ориентацию.

Это автоматизирует последовательность опытов внутри локального Windows AutoDraw, но не запускает игру из GitHub Actions и не предоставляет ИИ доступ к локальной доске. Формальная renderer acceptance по PNG остаётся отдельным итоговым gate: завершение CHALK block само по себе не означает PASS_PER_RUN.

- Добавлены phase/scenario IDs для vertical и diagonal single-stroke paired renderer.
- Расширены block planner и journal validator для точного набора repeat 2/3 (4 tasks total).
- UI Brush Test показывает фазу PRR и передаёт два повтора в планировщик; интеграция исполнителя валидирует PRR executor metadata.
- Добавлены regression tests для полного набора и tamper rejection.
- Источник истины по локальному исполнению остаётся локальный AutoDraw; GitHub API не может запустить реальную игру или проверить локальную доску.
- Commit chain: c4a9170, 07126ae, 6485448, bb9370d, c8bef70, 3d98953 (все в feature/image-geometry-optimization).

## 2026-11-06 — renderer acceptance thresholds согласованно снижены до 92%

- По прямому указанию пользователя формальные renderer pixel gates изменены с 99.5% на 92%.
- `renderer_acceptance.py`: IoU/precision/recall minima=0.92; symmetric difference fraction max=0.087; bbox edge tolerance=8% от меньшего соответствующего bbox extent, минимум 1 px.
- Обновлены unit tests: новые пороги, boundary symmetric-difference case и масштабируемый bbox edge tolerance.
- Capture/provenance, transform gates, alpha threshold 24, exact CHALK validation и series repeat requirement не менялись.
- Документация PROJECT_STATUS/TASKS/ROADMAP/DECISIONS/CHANGELOG/TEST_RESULTS синхронизирована; старые CI результаты сохранены как historical evidence по прежним критериям.
- CI после изменения ещё не запускался; локальное выполнение тестов через удалённый GitHub API не выполнялось.
- Нет live game run, CHALK consumption или изменений master.

## 2026-11-06 — local Firefox/NVIDIA Stage A–D replay received

- Проверен push commit `b4359c9178e514f773ee742fc99e20dde74c6543`; branch HEAD на момент проверки совпадал с ним. Diff commit содержит один raw ZIP в `AutoDraw_Stage20/data/`; master не менялась. GitHub API не подтверждает локальный `git status`.
- Из ZIP извлечены и проверены оба browser-session и manifest. Firefox 159.0.1 headed, WebGL 1.0, ANGLE/NVIDIA GeForce GTX 980 D3D11, antialias=true; context attributes совпадают с expected и source renderer reference.
- Run binding exact: vertical run `c860234f-995a-4789-9ac2-e05b322fe742`, CHALK=71; diagonal run `f69cb0f4-f5d0-4ff9-a3b7-1148c38fa07f`, CHALK=161. Это значения исходных runs, не новый расход.
- Stage backing: 3942×1800; Stage 1314×600; BoardPane 460×240; raster scale 3×; backing origin X=1022.374998, Y=216; rounded control X=1022; CSS matrix 0.487062/0.487778.
- PNG internal comparisons: vertical A/B 2565 differing pixels, diagonal A/B 4119; A/C pixel-equal; B/D same CRC32 and size per orientation. Fractional-vs-rounded placement materially changes this offline Stage raster; Canvas2D image-composite vs WebGL produces no measurable difference for these specific paired variants.
- Checked CI [42165379138](https://github.com/Kiddos19882/AutoDraw/actions/runs/42165379138): core jobs and Stage browser job SUCCESS; INT-006 formal vertical/diagonal renderer gate FAILURE. Hosted Stage A–D diagnostic reports were generated, but they use Microsoft Basic Render Driver/antialias=false and are not local NVIDIA metrics.
- Existing `compare_stage_renderer_reference.py` supports full 3942×1800 Stage PNG and same-run CSS transform. Local NVIDIA A–D screen comparison remains pending; no code changes required to start that comparison.
- No live game run, new CHALK consumption, production changes, threshold changes or post-hoc alignment.
## 2026-11-06 — Stage A–D live comparison and local GPU replay preparation

- Firefox 159 CI Stage A–D comparison completed successfully for vertical and diagonal.
- Stage A/C and B/D metrics recorded in PROJECT_STATUS and TEST_RESULTS. Fractional A/C outperformed rounded B/D.
- Diagonal symmetric difference improved from formal local-board replay 554 px to Stage A 187 px (−66.2%); vertical improved 302 → 294 px only.
- All Stage A–D board-origin crosschecks passed; baseline round-trip error and mask sensitivity were zero; no post-hoc alignment.
- Vertical FP: 288 pixels in one continuous column x=325, y=26..313. Diagonal FP distributed along path, FN=3.
- CI renderer context mismatch remains: Microsoft Basic Render Driver, antialias=false vs source NVIDIA, antialias=true.
- Added `--headed` mode and local PowerShell offline runner for same Firefox Stage A–D probe on the source machine/GPU.
- CI 42155453886 overall FAILURE because formal vertical/diagonal renderer gates failed. Stage diagnostic comparison succeeded. Downstream V1–V5, CHALK and INT006R validation skipped.
- No live experiment, CHALK consumption, production changes, threshold changes or post-hoc registration.

## 2026-11-06 — Firefox Stage A–D artifacts and internal pixel audit

- CI 42155453886 browser reference job SUCCESS: Firefox 159.0.1 generated Stage A–D for vertical and diagonal; manifests and eight PNGs uploaded.
- Internal PNG comparison: vertical A/C=665 differing pixels (max channel 1), B/D=0; A/B=2581 (max 90). Diagonal A/C=1906 (max 1), B/D=0; A/B=4400 (max 93).
- A/C differences are only internal Stage raster comparisons; thresholded live masks are not yet computed. No acceptance conclusion.
- Browser major matches expected Firefox 159, but CI uses Microsoft Basic Render Driver and antialias=false versus source NVIDIA and antialias=true. Exact GPU/context parity remains unavailable.
- Game Monitor/Bridge, executor and application integration jobs SUCCESS. Preparation core tests SUCCESS; benchmark and FILL-001-RS sweep still running. INT-006 dependent audit pending.
- No live game run, CHALK measurement, production changes or threshold changes.

## 2026-11-06 — Firefox Stage A–D runner debugging

- CI 42154755178: Firefox WebDriver and Egret WebGL probe launched; validation failed because Monitor board corners are nested under `players[0]`. No renderer failure.
- CI 42155166156: geometry binding fixed; Firefox 159 WebGL probe completed and manifest was saved. Runner failed only because it counted 8 download links including manifest link; actual PNG data URLs = 7.
- Firefox CI WebGL diagnostics: WebGL 1.0, Microsoft Basic Render Driver / ANGLE, antialias=false even with `webgl.msaa-force=true`. Source renderer manifest expects Firefox 159 but records NVIDIA ANGLE and antialias=true. Browser major matches; GPU/context does not.
- Updated runner to read Monitor corners from `players[0]`, retain expected/actual context diagnostics, and filter only PNG data URLs.
- Updated Stage comparison to accept WebGL and Canvas2D and workflow to analyze A–D.
- CI 42155453886 pending. No Stage A–D metrics from the Firefox runner yet.
- No live experiment, CHALK measurement, production changes, acceptance threshold changes or post-hoc alignment.

## 2026-11-06 — Firefox WebGL parity follow-up

- Перепроверен CI 42151945274 и извлечены Stage/live comparison artifacts.
- Stage A vs B: fractional origin дал небольшое улучшение, но vertical/diagonal остались далеко от formal gates; common-baseline sensitivity равна нулю.
- A/C PNG и B/D PNG совпадают побайтно для обоих runs.
- Найдено различие browser execution path: Stage WebGL output создавался headless Edge/Chromium SwiftShader, screen compositor — Firefox 159; source renderer reference manifest ожидает Firefox 159. Monitor reports не содержат собственного UA/GL vendor, поэтому exact session binding остаётся ограничением.
- Добавлен Selenium Firefox Stage runner, сохраняющий run-bound A–D manifests/PNGs и browser/GL diagnostics. Workflow устанавливает Selenium.
- На момент записи CI 42154755178 pending; никаких PASS/FAIL выводов по Firefox runner пока нет.
- Production code, live game state, CHALK and formal thresholds не менялись.

## 2026-11-06 — post-commit ordering correction in shared-baseline comparator

- Review of commit `97184afe99e852fe6ace19c37547b67327b44550` caught that observed masks referenced `baseline_rgb` before the Firefox baseline capture initialized it.
- Moved both observed-mask calculations to immediately after baseline round-trip validation. No measurement semantics or thresholds changed.
- The first commit's workflow result is not used as validation; the corrected follow-up commit is the validation target.

## 2026-11-06 — устранение baseline asymmetry в Stage screenshot diagnostics

**Scope:** тестовый/диагностический код и документация; без production changes и live game runs.

- Перепроверены remote branch/HEAD, последние 20 commits, compare с master, управляющие документы, постоянные регламенты, Stage comparator, tests, saved Monitor reports и последний CI run.
- Branch: `feature/image-geometry-optimization`; исходный HEAD `d924cc2a848229342d4306915b010d97200ef671`; master не изменялась. Remote compare: feature ahead 3440 / behind 5; merge/rebase не выполнялись. Локальный git status недоступен через GitHub API.
- Последний CI до изменения: run 42131803494, conclusion FAILURE. Обязательные jobs Game Monitor/Bridge, Preparation/G3, Executor, Application integration и Egret CanvasRenderer reference — SUCCESS; INT-006 pixel-level audit — FAILURE на formal vertical/diagonal replay; Stage A/B diagnostic и full-screen source-capture jobs — SUCCESS. Optional benchmarks и Windows portable build — SKIPPED.
- Найдена асимметрия comparator: observed mask использовала raw before screenshot, expected mask — Firefox round-trip baseline. Round-trip допускал до 1 RGB level расхождения при threshold=24.
- Обе маски переведены на общий Firefox baseline. В отчёт добавлена mask sensitivity к выбору raw/round-trip baseline. Добавлены unit tests на threshold boundary и несовпадающие RGB dimensions.
- Это correction to diagnostic measurement, не установленная причина исходного renderer mismatch. Численный эффект ожидает нового CI artifact.
- Acceptance thresholds и raw captures не менялись; production renderer/planner/sampling/brush/executor не затронуты; live game runs не проводились.

**Следующий шаг:** проверить CI на новом commit, затем оценить mask sensitivity и остаточные metrics vertical/diagonal. Если mismatch сохранится, продолжить анализ маски/alpha/coverage и Stage sampling, не подгоняя пороги.

---

## 2026-11-05 — привязка offline renderer к профилю последнего live run

**Scope:** исправление offline replay harness и инструкции; без запуска renderer/live game.

- Проверено состояние ветки: `feature/image-geometry-optimization`, исходный HEAD перед работой `3ab7dcaca7672a7256076dece053b7977f72d9a5`; просмотрены последние 20 коммитов и обязательные управляющие документы/регламенты.
- Установлено: `game_renderer_reference.js` жёстко записывал в manifest snapshot от 2026-11-04 (Stage 1672×600, backing 5016×1800), хотя latest paired-run geometry использует Stage 1314×600, backing 3942×1800, screen 1920×1080 и CSS matrix 0.487062/0.487778.
- Исправлено: runtime profile для live replay теперь строится из `renderer_geometry_at_start/end` того же полного Game Monitor report; несовпадающие/отсутствующие snapshots и неподдерживаемые renderer settings отклоняются.
- Сохранено: offscreen BoardPane 460×240, rasterScale 3, WebGL output 1380×720. Stage/screen CSS transform записывается как профиль live session, но не применяется повторно к локальному raster.
- HTML-инструкция требует полный `monitor_report.json`. Изменены два файла harness.
- Commits: `23ed8cf2cce051eeda87ad8b630604ae96889608`, `d6343adaf2db05f321b48ef0432b897277ff0193`.
- Проверки: source-level consistency reviewed; offline renderer, unit suite and CI не запускались. Новых live experiments не было.
- Следующий шаг — пользовательский offline rerun с последними vertical/diagonal monitor reports и последующая проверка новых артефактов.

## 2026-11-05 — review of first vertical/diagonal captures (evidence commit e6b771e)

**Scope:** remote repository review and documentation synchronization only; no code/test/config/workflow changes and no new live experiment by the reviewer.

- Confirmed remote branch `feature/image-geometry-optimization` HEAD `e6b771ed67201625884c6ce778fa355f1ab9b873`; it is one commit after `6fb868f`. The commit adds 22 result artifacts only. `master` remains at the previously known HEAD; GitHub API does not expose local `git status`.
- Reviewed both experiment manifests, raw Game Monitor reports, brush plans, comparison reports, offline manifests and PNG outputs. Vertical exact CHALK=71; diagonal exact CHALK=161; both radius 10, one stroke, zero Monitor/Bridge dropped/error/sequence counters.
- Recomputed same-run Monitor fits: vertical Y max residual 0.723222 px; diagonal X/Y max residuals 0.730129/0.739053 px. Client-to-screen offsets are stable (0,163) px; geometry snapshots are unchanged start/end.
- Existing alpha24 comparisons use the frozen 674×355 ROI transform and remain exploratory (vertical IoU 0.870044; diagonal 0.873071); neither report contains an independent-transform comparison. Best-translation overlays are diagnostic only.
- Calibration profile records 1920×1080, Windows scale 100%, browser zoom 100%, Firefox 159; Monitor reports DPR=1 and visualViewportScale=1. Windows scale is sourced from the profile calibrated earlier on the same date, not a per-run Windows display API.
- Updated current status, backlog, roadmap, work log and TEST_RESULTS. Kept raw experiment evidence and frozen acceptance thresholds unchanged.
- Next offline step: derive same-run screenshot BoardPane bounds and rerun comparison using the independent per-axis transform. No additional live run should be needed before this replay.
## 2026-11-05 — закреплены границы локального доступа и автоматизация live-тестов

**Объём:** только документация, ветка `feature/image-geometry-optimization`.

- В начале README и индекса документации добавлено заметное правило: локальная программа, игровая сессия и доска доступны только пользователю; локальный `git status` на ПК также может подтвердить только пользователь.
- В AI_WORK_GUIDE и EVIDENCE_AND_VALIDATION уточнено различие между удалённой проверкой GitHub и локальным состоянием ПК, а также требования к доказательствам live-тестов.
- В ENGINEERING_INVARIANTS приняты INV-010 (границы локального доступа) и INV-011 (максимальная автоматизация тестов с игровой доской).
- DEC-024 фиксирует постоянное решение: повторно использовать существующие средства автоматизации, создавать недостающие условия, автоматизировать сбор данных/точный CHALK/аудит/отчётность и минимизировать ручные шаги пользователя.

**Не выполнялось:** локальный `git status`, запуск AutoDraw, live-тесты с игровой доской. Код, тесты и workflow не менялись.


## 2026-11-05 — formal renderer acceptance tooling

- Reviewed the active multi-axis code, capture contract, historical horizontal baseline, same-run screenshots and the predeclared TASKS.md thresholds.
- Added fail-closed per-run evidence/geometry/pixel validation and a separate three-repeat series aggregator; added unit tests and CI wiring for the existing horizontal baseline audit.
- Kept vertical/diagonal live work blocked on actual user-screen captures. No live experiment, production renderer/planner/estimator/default, calibration profile, or executor behavior was changed.
- CI verification and post-run documentation sync remain pending.


## 2026-11-05 — Bridge telemetry run provenance and CI test corrections

- Implemented paired-scenario input telemetry opt-in in Bridge; ordinary Bridge sessions leave Monitor telemetry unchanged. The Bridge restores the user's pre-existing state on disconnect.
- Added `bridge_configuration` to session.json and `bridge_configuration_at_start` to run JSON.
- Browser lifecycle tests passed 4/4. First Python CI attempt failed with a wrong JS-string assertion; second attempt failed because the provenance test omitted `json` and `RunRecorder` imports. Both failed runs are preserved in TEST_RESULTS.
- Corrected imports in commit `58ebdda7`; CI rerun 41994624425 completed SUCCESS. No live game experiment was run.

## 2026-11-05 — complete CI verification and artifact review

- Full CI run 41994624425 on code/test commit 58ebdda7 completed SUCCESS across all required jobs; optional algorithm benchmarks skipped.
- Bridge input telemetry tests: browser lifecycle 4/4, Python WebSocket/snippet/provenance suite 31 passed.
- Preparation/G3: 880 passed, 24 warnings, 82 subtests; capsule broad-phase benchmark and FILL-001-RS static sweep reproduced and uploaded.
- Formal horizontal renderer per-run acceptance passed again; artifact 13399663414. Vertical/diagonal live series remains uncollected.
- V1–V5 pixel analyzer validated 90/90 captures (10×9). INT-006 and INT006R each accepted 45/45; safety margin and production eligibility remain unvalidated; INT006R package awaits manual visual review.
- Windows portable build/startup smoke-test passed; artifact 13399627749, 646,950,501 bytes.
- CI artifacts were downloaded and inspected. No new live run, local app launch, raw evidence mutation, or production drawing default change was performed.


## 2026-11-05 — исправление same-run geometry для multi-axis offline/live renderer

Scope: code, tests and CI only in feature/image-geometry-optimization; no real game experiment.

- Added build_same_run_geometry_audit_input() to normalize the exact renderer_geometry_at_start stored in Game Monitor. It rejects run/session/experiment mismatch, changed start/end geometry, geometry updates/overflow, unsupported renderer mode, unexpected logical dimensions, and screen/PNG dimension mismatch.
- Added verified 1:1 screen-pixel mapping when same-run window.screen dimensions match both experiment phase metadata and actual full-screen PNG dimensions, with DPR and visualViewportScale equal to 1. Legacy audits with a calibrated 100% Windows scale remain supported.
- Added --same-run-geometry to the paired comparison CLI. The generated audit is written to the output directory and used with same-run full-screen before/after captures.
- Added fail-closed unit tests for valid evidence, run mismatch, changed geometry, geometry updates, screen mismatch, and pixel mapping without a separate OS-scale profile.
- CI now replays the stored vertical and diagonal captures. Frozen-plan metrics remain diagnostic; independent geometry becomes authoritative in the main comparison report.
- Commits: d26ed86 (adapter/tests/CI replay), 57638f2 (audit JSON newline), 1cd0d61 (authoritative report fields).
- Current CI run: 42083576282, pending at documentation time. Game Monitor/Bridge, Egret browser reference, executor and integration jobs have reported SUCCESS; preparation/G3 is still running.
- No live game run, AutoDraw launch, production planner/renderer/executor change or local workstation action was performed.

## 2026-11-05 — formal renderer comparison uses exact BoardPane crop

**Scope:** renderer comparison code and regression tests on `feature/image-geometry-optimization`; no live experiment.

- Reviewed CI 42087496092 artifacts. The same-run transform was valid, but the formal comparison cropped to calibrated ROI `(496,265,674,355)` instead of detected BoardPane bounds `(498,268,672,351)`.
- Identified 17 changed pixels on the ROI's bottom margin outside the board; these caused false bbox/symmetric-difference failures despite the actual board mask matching closely.
- Added `crop_mask_to_board_bounds()` with fail-closed validation. Formal observed/expected masks now use exact same-run BoardPane bounds; ROI-margin deltas are retained separately as diagnostic evidence.
- Added regression tests for exact board crop, outside-board isolation and invalid bounds.
- Commit: `1ac3d9390c56072730017e073cf80dd69c448f8b`.
- CI run `42091370065` is pending. The existing horizontal artifact recalculated over exact BoardPane bounds gives IoU 0.999218, precision 0.999553, recall 0.999665, 7 symmetric-difference pixels and identical bounding boxes; this is an offline re-analysis, not a new CI result.
- No live game run, local app launch, production planner/executor change, master modification or local git status check was performed.

## 2026-11-05 — BoardPane crop diagnostics consistency

- Follow-up review found that OpenCV diagnostic alpha masks and the overlay image also needed to use the exact BoardPane crop after the formal observed/expected masks were narrowed. Without this, diagnostic arrays would have mismatched dimensions.
- Cropped OpenCV alpha diagnostics to the same BoardPane bounds and sized the overlay from the board-only observed mask.
- Commit: `e73506db2a2cfd55bbb0ea4c4a1616648b7f0065`; CI run `42091800785` pending.


## 2026-11-05 — correction to negative BoardPane bounds test fixture

- CI 42091800785 ran 887 tests successfully and found one failing assertion in the newly added negative-bounds test. The test fixture used x=497 while ROI started at x=496, so the board bounds were correctly considered contained; the test expectation was wrong.
- Corrected the fixture to x=495, genuinely outside the ROI. Production crop implementation was not changed.
- Commit: `cfdc49e86809a7b62c0271f0574473a48403e20b`; CI run `42092259450` queued.


## 2026-11-05 — ROI-local OpenCV diagnostic mask correction

- CI 42092259450 passed preparation/G3: 888 passed, 24 warnings, 82 subtests. The renderer job then failed before formal metrics because `alpha_opencv` is generated in ROI-local dimensions, while the crop helper was given absolute screenshot BoardPane coordinates.
- Converted absolute BoardPane bounds to ROI-local coordinates for the OpenCV diagnostic crop; full-screen observed and browser-composited masks continue using absolute screen coordinates.
- Added a regression test for ROI-local mask cropping. Commits: `f1b5b608de5b61c171b8e90640f83898bbd0d5b4`, `221e5240152c9888b564076e649b3f71366c1664`.
- CI run `42093239480` pending. No live game run or production executor change.


## 2026-11-05 — Firefox compositor parity

- CI 42093239480 confirmed horizontal PASS_PER_RUN after exact BoardPane cropping. Vertical and diagonal remained REJECTED_PER_RUN with IoU 0.938863 and 0.953976; provenance and geometry gates passed.
- Root cause candidate was identified in the comparison harness: live renderer manifest reports Firefox 159, while the offline CSS compositor used Edge/Chromium. The different browser raster/compositing engines make vertical/diagonal pixel differences non-diagnostic for the game renderer.
- Replaced Edge image overlay with a transparent Canvas2D overlay captured by Firefox headless. The compositor now requires the same browser family and matching major version from the same-session manifest.
- Commits: `cd12cac3bad2af9aa7df9030f69d2880ec160a74`, `bc787b8f06c3609c7f294beb0cb3ea4b6e1ae5ef`. CI run `42096244252` pending.
- No live game experiment or production executor handoff.


## 2026-11-05 — correction to horizontal acceptance wording and Firefox CI result

- Corrected the previous status wording: the horizontal metrics IoU 0.999218, precision 0.999553, recall 0.999665, 7 differing pixels were calculated offline from a stored artifact after BoardPane crop. They were not emitted as a CI `PASS_PER_RUN` in run 42093239480. That workflow formally replayed vertical and diagonal only; both were rejected.
- Latest [CI 42096244252](https://github.com/Kiddos19882/AutoDraw/actions/runs/42096244252) completed FAILURE. Executor, Game Monitor/Bridge, Egret renderer harness, preparation/G3 matrix tests, application integration, portable build and startup smoke-test jobs succeeded. INT-006 failed on the first horizontal Firefox compositor comparison: IoU=0, precision=0, recall=0, 8946 symmetric-difference pixels. Capture and transform checks were empty (passed); renderer checks failed. Vertical/diagonal replay was skipped after the horizontal gate failed.
- Firefox major-version detection ran successfully, but current evidence does not explain why the headless Firefox expected mask did not overlap the observed live delta. Treat as a compositor harness defect/unknown until the generated PNG diagnostics are reviewed; do not infer a game renderer defect.
- No formal horizontal, vertical or diagonal PASS_PER_RUN is currently established by the latest CI evidence. No live game test or executor handoff was performed.


## 2026-11-06 — independent same-run multi-axis replay and compositor investigation

**Scope:** comparison harness, regression test, CI workflow and project documentation on feature/image-geometry-optimization; no production drawing code and no live game experiment.

- Начальная точка продолжения: code/test HEAD c0f36ac49e4b66cf0fcd27d362154b71a917c367. Проверены управляющие документы, README/docs index, engineering invariants, evidence/experiment standards, профильные исходники и сохранённые captures. GitHub API не предоставляет локальный git status.
- CI run 42109890747 после independent transform fix завершился FAILURE: горизонтальный compositor overlay был пустым (expected pixels=0); capture/transform evidence не показывали mismatch.
- В commit 7c1a1fb704a0393509b7ff237048006dbbe6caf7 добавлен eager static image compositor, empty-mask fail-closed guard, regression coverage и opt-in Windows portable build workflow input. CSS image compositor давал browser-resampling mismatch, поэтому этот способ не оставлен как финальный.
- В commit b07c636fa4b4ce28329cfb74f468634a46751ac1 overlay возвращён к Canvas2D canvas; source image загружается eager/sync, drawImage выполняется синхронно в onload до Firefox screenshot. Добавлен тест HTML contract.
- Windows portable build/startup smoke-test вынесен из обычного push CI: job выполняется только при manual workflow_dispatch с run_windows_portable_build=true; default=false.
- CI [42113632374](https://github.com/Kiddos19882/AutoDraw/actions/runs/42113632374) завершился FAILURE только на INT-006 vertical/diagonal renderer acceptance. Preparation/G3, Game Monitor/Bridge, Executor, Egret browser reference и Application integration — SUCCESS; optional benchmarks и Windows build — SKIPPED.
- Horizontal formal result: PASS_PER_RUN, IoU=0.999329, precision=0.999329, recall=1.0, symmetric difference=6 px. Vertical: REJECTED_PER_RUN, IoU=0.938405, precision=0.938980, recall=0.999348, difference=302 px. Diagonal: REJECTED_PER_RUN, IoU=0.949646, precision=0.962683, recall=0.985939, difference=554 px. Capture/transform gates passed for all three.
- Downloaded/reviewed paired renderer artifact 13454628828 and Egret reference artifact 13453809141. Vertical/diagonal failures are not explained by capture provenance or the independent board transform.
- Leading hypothesis: compositor skips live Stage-level WebGL texture composition. Same-run geometry records Stage backing 3942×1800, BoardPane local raster 1380×720, board backing origin x≈1022.375/y=216 (fractional X phase 0.375 px), and WebGL texture LINEAR sampling. Direct screen-space Canvas2D overlay may not reproduce this pipeline. Hypothesis only; no post-hoc alignment or threshold adjustment.
- Exact CHALK remains from existing user captures only: vertical=71, diagonal=161. No new live run, no brush/trajectory/sampling/executor changes, no master changes.
- Next step: stage-level WebGL compositor using same-run stage/backing evidence while keeping the screen transform independently derived; rerun existing captures and add tests.



## 2026-11-06 — статический аудит Stage-level WebGL composition

- Проверены branch refs, HEAD, последние 20 коммитов, обязательные управляющие документы и постоянные регламенты. Удалённая рабочая ветка: `feature/image-geometry-optimization`; HEAD перед записью: `f0cfa6268fd39cf91f3d4a9e7e2bf9509763ff48`; master не изменялась. Локальный git status недоступен через GitHub API.
- Повторно изучены `tests/game_renderer_reference.js`, `tests/compare_live_renderer_reference.py` и `gameEngine/mergeEngine_df2e5bc5.js`.
- Подтверждено: reference harness рендерит local 1380×720 WebGL buffer, а comparison script размещает raster в screen CSS space; Stage backing composition не моделируется.
- Подтверждён source pipeline Egret WebGL: GraphicsNode → CanvasRenderBuffer/CanvasRenderer → WebGL texture → drawTexture; texture uses LINEAR min/mag, CLAMP_TO_EDGE и premultiplied alpha.
- Зафиксированы run-bound параметры сохранённых captures: Stage 1314×600, backing 3942×1800, BoardPane local raster 1380×720, backing origin ≈(1022.375,216), canvasScaleX/Y=3.
- Дробная X-фаза 0.375 px и sampling являются правдоподобными факторами, но причинность не доказана. Текущий harness gap подтверждён статическим аудитом.
- Зафиксирован план A–D (WebGL/Canvas2D × exact/rounded origin), метрики и требования к unit/browser tests. Код, тесты и workflow в этой работе не менялись; live game runs не запускались; CHALK не измерялся повторно.
- Предыдущий CI 42113632374 остаётся FAILURE из-за INT-006 vertical/diagonal renderer gates; его результаты не переинтерпретируются как результат нового probe.
- Следующий шаг: реализовать offline Stage-level probe, получить PNG/manifests и сравнить exact WebGL variant с сохранёнными live captures без post-hoc alignment.


## 2026-11-06 — синхронизация документации с remote commits, кодом renderer и CI

**Объём:** удалённая проверка GitHub и документационная синхронизация в `feature/image-geometry-optimization`; исходники, тесты, конфигурации и workflow не изменялись.

- Проверены refs рабочей ветки и `master`, последние 20 commits и сравнение веток. На начало сверки remote HEAD рабочей ветки — `81f6bb77c8a338ae52e0de084dce45e0cacabf1f`; последний code/test HEAD — `b07c636fa4b4ce28329cfb74f468634a46751ac1`; `master` — `9a3453aeb847b66041bc83d6f4a56ecaf33a993a` и не изменялась. GitHub compare сообщает diverged, feature branch ahead by 3404 / behind by 5; merge/rebase не выполнялись.
- Проверено, что commits после `b07c636` до начала сверки являются документационными; code/test HEAD остаётся `b07c636`. Commit `b07c636` меняет только `tests/compare_live_renderer_reference.py` и `source/preparation/tests/test_renderer_geometry.py`.
- Сверены `game_renderer_reference.js`, HTML harness, `compare_live_renderer_reference.py`, `renderer_geometry.py`, `renderer_acceptance.py` и workflow. Подтверждено: offscreen WebGL probe использует локальный буфер 1380×720 и BoardPane в начале сцены; paired comparator композитит raster через Firefox Canvas2D в screen CSS space. Полная Stage backing texture composition пока отсутствует.
- CI run [42113632374](https://github.com/Kiddos19882/AutoDraw/actions/runs/42113632374) на `b07c636` завершился FAILURE из-за vertical/diagonal renderer acceptance. Preparation/G3, Game Monitor/Bridge, Executor, Egret browser reference и Application integration — SUCCESS; optional benchmarks и Windows portable build — SKIPPED.
- Уточнены текущие refs в `PROJECT_STATUS.md` и `TEST_RESULTS.md`; синхронизированы дата канонического backlog и строка `DOC-STATUS-SYNC` в `TASKS.md`; исправлено описание renderer harness и multi-axis evidence в `docs/README.md`; запись добавлена в `CHANGELOG.md`.
- Проверены относительные файловые ссылки в управляющих документах и README: отсутствующие цели не обнаружены. Проверка якорей отдельно не выполнялась.
- Локальный `git status`, локальный запуск приложения и live game tests недоступны; новые тесты и CI в рамках этой документационной сверки не запускались.

**Остаточный P0:** реализовать и проверить offline Stage-level WebGL compositor A–D на существующих captures; не менять production renderer/planner/sampling/brush/executor и acceptance thresholds. Дробная backing X phase=0.375 px остаётся гипотезой, не установленной причиной vertical/diagonal mismatch.

## 2026-11-06 — Stage-level compositor A–D implementation

**Scope:** offline renderer harness, regression tests, HTML page and headless browser runner; no production drawing code and no live game run.

- Start audit: remote feature branch and latest 20 commits checked; required README/docs index, PROJECT_STATUS, TASKS, ROADMAP, DECISIONS, CHANGELOG, WORK_LOG and permanent engineering/evidence/experiment guides reviewed. GitHub API does not expose local `git status`.
- Branch remained `feature/image-geometry-optimization`; `master` remained at `9a3453aeb847b66041bc83d6f4a56ecaf33a993a`. Branch compare reports diverged, ahead 3418 / behind 5; no merge/rebase performed.
- Confirmed run-bound geometry for saved captures: Stage 1314×600, backing 3942×1800, BoardPane 460×240, scale 3×, logical top-left (340.7916660308838,72), backing origin (1022.375,216).
- Added `buildStagePlacement()` with fail-closed validation, exact and rounded origins, and Node tests.
- Added A/B WebGL and C/D Canvas2D Stage backing render variants; manifest records placement, texture parameters and RGBA pixel delta vs A.
- Connected the HTML harness to the exact existing vertical/diagonal Game Monitor reports and extended the headless Edge runner to save A–D PNGs/manifests. This is offline replay of existing captures, not a new live experiment.
- Commits: `9dc84c4` (Stage compositor), `c1bf7be` (placement tests), `bd13ad9` (HTML docs), `8035457` (variant deltas), `c0fd8d7` (WebGL canvas readback), `670d84f` (source orientation), `6bdce34` (saved Monitor input), `a6782cd` (headless runner).
- Validation: remote source changes committed. No local node/PowerShell execution available; GitHub combined status for the current code HEAD has not returned checks, so CI/browser result is NOT_CONFIRMED. Do not infer runtime correctness from source presence.
- Not changed: production renderer/planner/sampling/brush/executor, acceptance thresholds, raw captures, live game state, master.
- Next: inspect CI browser artifacts for both orientations; compare A–D and then feed Stage A through the existing formal screenshot comparator with the independent Stage→screen transform, no post-hoc alignment.


## 2026-11-06 — Stage A/B уточнены: рендеринг через Egret WebGLRenderer

- После первичной реализации raw WebGL quad заменён на вызов существующего Egret WebGLRenderer с тем же BoardPane/mask/scrollRect и run-sized RenderBuffer; это избегает отдельного самописного GL shader пути для вариантов A/B.
- Stage buffer создаётся с точными backing dimensions конкретного Monitor run; renderer получает matrix с canvasScaleX/Y и exact либо rounded backing origin.
- C/D остаются Canvas2D control variants, использующими тот же board-level WebGL output.
- Code commit: `953d0d0d971230384d03ce45727849679dd556bf`; manifest diagnostics commit: `8713012673de7734fb0bb91fe58fcce483ed68b3`.
- CI status не surfaced через combined-status API; Node/browser run и Stage PNG outputs пока NOT_CONFIRMED. Требуется inspect CI artifact before interpreting metrics.


## 2026-11-06 — fail-closed validation saved Stage A–D browser artifacts

- Headless Edge runner дополнен проверкой точного source run ID, набора A/B WebGL + C/D Canvas2D, Egret backend для A/B, exact origin (1022.375,216), rounded origin (1022,216), BoardPane backing size 1380×720 и нулевой self-difference A.
- Existing vertical/diagonal Game Monitor reports используются напрямую из committed evidence; browser runner не запускает AutoDraw и не отправляет игровые input events.
- Commit: `501b3fac5e4cb7039161da6d70a1c79803ebb01f`.
- GitHub combined status для code/test HEAD вернул пустой список checks; PR-only workflow lookup также не вернул runs. CI/browser execution therefore NOT_CONFIRMED, не PASS.
- Remote feature branch HEAD перед этой записью: `adac8018c22c66fa91d8d9203cd82c1b79110f29`; compare с master: diverged, ahead 3434 / behind 5. Master SHA `9a3453aeb847b66041bc83d6f4a56ecaf33a993a`.
- Следующий шаг — получить подтверждённые CI artifacts, проверить PNG и manifest, затем выполнить formal Stage A → live screenshot comparison.



## 2026-11-07 — утверждена цель 95%, подготовлен calibration/holdout protocol

- Получено подтверждение пользователя: 95% — целевое одностороннее предиктивное покрытие CHALK.
- Спроектирована независимая выборка: 19 calibration + 59 holdout DrawingPlan IDs на profile/domain; строгий holdout PASS требует 0 превышений из 59.
- Для первой line-based domain, radius=10 и P0/P1/P2: 78 новых уникальных планов, по одному capture на профиль (234 плановых captures).
- Определены split protection, N strata, capture integrity, exact pointCount CHALK, frozen quantile и fail-closed критерии.
- Числовые N boundaries пока не выбраны, поскольку сначала требуется определить целевое распределение production DrawingPlans.
- Live experiments не запускались; пользовательское подтверждение целевого покрытия не является разрешением на live runs.
- Исходники, тесты, конфигурации, workflow и production defaults не изменялись.
- Подробности: [CHALK_95_PERCENT_CALIBRATION_HOLDOUT_PROTOCOL_2026-11-07.md](CHALK_95_PERCENT_CALIBRATION_HOLDOUT_PROTOCOL_2026-11-07.md).

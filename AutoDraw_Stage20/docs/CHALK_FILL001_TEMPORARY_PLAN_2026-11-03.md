# Временный план дальнейших работ FILL-001

**Статус:** актуальный временный план, обязателен к сохранению до выполнения всех пяти шагов или отдельного решения пользователя.  
**Дата создания:** 2026-11-03  
**Последнее обновление:** 2026-11-04 (runtime discovery replay fixed legacy-session blocker; live PNG audit rejected the candidate)
**Рабочая ветка:** `feature/image-geometry-optimization`  
**Область:** подготовка и проведение контролируемого эксперимента по расходу CHALK при заполнении областей кистями разных радиусов; после quota-exhausted preflight добавлен отдельный versioned этап FILL-001-RS для исследования расстояния между проходами.

## Runtime binding replay и PNG audit — 2026-11-04

Пользовательский evidence commit [5308214](https://github.com/Kiddos19882/AutoDraw/commit/530821497ce3a6bd5152318a78e1f06cb836f288) содержит завершённый run rectangle/r10/step=5/offset=0: 27/27 strokes, radius=10, exact CHALK=1260. Основной Bridge run ID: `6a17a297-ea14-4527-9527-bfd8de3bd335`.

Причина Runtime binding pending — старая legacy Bridge session без schema v2 и diagnostics блокировала discovery. Исправление [a7e37d6](https://github.com/Kiddos19882/AutoDraw/commit/a7e37d6eb0031094ffd962bc11ef01860a3af74a) исключает несовместимые schema до классификации pending; incomplete schema-v2 sessions по-прежнему не принимаются автоматически.

Replay test [974f949](https://github.com/Kiddos19882/AutoDraw/commit/974f949e9639acc90e7f4d6f4588c3fb96f9abb2) прогоняет реальные committed artifacts через `Fill001Tab.finalize_capture()`, включая legacy session. Runtime binding PASS, exact CHALK=1260. Независимый PNG audit не прошёл: coverage=97.673218% (требуется ≥99%), leakage=28 (требуется 0). Capture остаётся pending; качество не считается подтверждённым.

Полный CI [41772866679](https://github.com/Kiddos19882/AutoDraw/actions/runs/41772866679) — SUCCESS: Preparation/G3 804 passed, 24 warnings, 82 subtests; обязательные jobs, INT-006 pixel audit и Windows portable build/startup smoke-test SUCCESS; optional benchmarks SKIPPED.

## Исправление FILL-001-RS frozen geometry rebuild — 2026-11-04

Пользовательский runtime evidence commit [63158fb](https://github.com/Kiddos19882/AutoDraw/commit/63158fb55743c566bf231196b80016273970bbf1) зафиксировал отказ single-task preflight до запуска исполнителя. Для задачи rectangle/r10 manifest и исходный DrawingPlan согласованы: planner_version=2, scanline_row_step=5, scanline_offset=0, plan signature совпадает с task, expected_strokes=27. Game Monitor подтвердил radius 30→10; pointCount остался 1 (CHALK=0), Bridge session завершилась без dropped events/errors/send failures.

Причина установлена в runtime guard integrated_app.py: повторное построение выполнялось вызовом build_fixed_radius_fill_plan(shape_id, radius) без spacing-параметров. Значения по умолчанию — step=1/offset=0, то есть legacy planner v1. Поэтому сравнивался FILL-001-RS v2 signature с другой геометрией v1 и срабатывал корректный fail-closed guard. Это ошибка handoff/validation, не ошибка регулировки кисти и не расход CHALK.

Исправление: единый helper повторного построения получает scanline_row_step/scanline_offset из frozen task; для legacy tasks без этих полей сохраняются прежние defaults. Объявленный planner_version проверяется против фактически восстановленного. Добавлены регрессионные проверки RS signature/27 strokes, legacy signature/131 strokes и отказа при несовпадении версии. До успешного CI и повторного локального preflight live matrix остаётся BLOCKED; повторный запуск здесь не выполнялся.

## Цель

Получить воспроизводимые данные о фактическом расходе CHALK для заполнения областей сопоставимой площади, определить влияние радиуса кисти и сравнить стратегии построения заливки. Не менять production estimator и стандартные параметры исполнения до отдельного решения на основании результатов.

## Пять шагов

### Шаг 1. Закрыть программный regression gate

**Статус:** DONE

- GitHub Actions [41730717881](https://github.com/Kiddos19882/AutoDraw/actions/runs/41730717881) — SUCCESS на code HEAD `fe6d4469a5294fdf8284978d4e2b5c47582fa2d4`.
- Preparation/G3: **782 passed, 24 warnings, 82 subtests passed**.
- Executor regression, Game Monitor/Bridge, Application integration, INT-006 pixel audit и Windows portable build/startup smoke-test — SUCCESS; optional algorithm benchmarks — SKIPPED.
- Windows portable artifact: [autodraw-g3-preflight-build](https://github.com/Kiddos19882/AutoDraw/actions/runs/41730717881/artifacts/13278132576), 637 057 007 bytes.
- CI подтверждает software regression gate, но не live FILL-001 запуск в браузерной игре и не проверку реальных board PNG.

**Критерий завершения:** выполнен — все обязательные jobs и Windows portable build/startup smoke-test успешны на одном code/test HEAD.

### Шаг 2. Привязать captures к фактическому runtime

**Статус:** DONE (software/runtime integration и regression gate)

- `chalk_fill_runtime_binding.py` читает persisted Bridge `session.json`, run JSON и executor report.
- Проверяются Bridge schema v2, session/run identity, временное окно executor, timezone-aware timestamps, sequence gaps, send failures, Monitor errors, stroke lifecycle, единый observed radius, exact pre/post snapshots и совпадение exact CHALK с sampled/per-stroke deltas.
- Фактические `ExecutorConfig.point_step_px=4`, `point_delay_ms=5` и `line_extension_px=0` сверяются с frozen P1.
- Stage 6 выполняет post-execution binding после успешного завершения FILL-001 task и записывает результат в execution report.
- UI handoff передаёт experiment context в DrawingPlan; runtime binder связывает executor report с Bridge session/run и фиксирует SHA-256 исходных runtime artifacts.
- Regression gate подтверждён полным CI [41730717881](https://github.com/Kiddos19882/AutoDraw/actions/runs/41730717881) на code HEAD `fe6d446`; все обязательные jobs и Windows portable build/startup smoke-test SUCCESS.

**Критерий завершения:** программная интеграция и fail-closed regression tests подтверждены CI. Реальное live подтверждение на Windows относится к шагу 3.

### Шаг 3. Интегрировать запуск в AutoDraw и провести Windows live preflight

**Статус:** IN_PROGRESS — software/CI gates пройдены; runtime binding реального RS candidate подтверждён, но независимый PNG audit отклонил capture (coverage=97.673218%, leakage=28). Live preflight из commit [73d14a1](https://github.com/Kiddos19882/AutoDraw/commit/73d14a1784a5a9f8ef29bc0e197b75352f2650af) подтвердил exact CHALK=5999, но только 128/131 consuming strokes; три последних кандидата не потребили ресурс после исчерпания квоты. Capture REJECTED, полная стоимость плана неизвестна. Последующий статический анализ выявил избыточно плотные проходы и сформировал кандидатов FILL-001-RS; ни один кандидат ещё не подтверждён live.

**Подтверждённая реализация UI/runner:**
- Добавлен `source/preparation/chalk_fill_ui.py` и самостоятельная вкладка FILL-001 в `integrated_app.py`, отдельная от седьмой вкладки «Тест кистей».
- UI создаёт/загружает manifest из 45 задач, показывает task identity/shape/radius/repeat/expected strokes/plan signature и выбирает только pending task с пройденным quality gate.
- Перед передачей пересчитывается fixed-radius plan и сверяются frozen plan signature, mask SHA-256, coverage/leakage, expected strokes и matrix/task identity.
- Исполнение ограничено одной выбранной task с явным подтверждением оператора; batch execution всей матрицы запрещён.
- Размер кисти устанавливается через существующий Brush Test workflow; затем создаётся DrawingPlan с FILL-001 experiment context и запускается Stage 6 с P1 override.
- После исполнения UI сохраняет before/after board PNG и передаёт runtime evidence в capture adapter; прямой запуск FILL-001 plan в обход специализированного workflow закрыт fail-closed guard.
- Unified app regression test проверяет регистрацию вкладки `8. FILL-001`; следующая вкладка — `9. Калибровка теста`.
- Первая пользовательская попытка сохранена в commit [6b1cba9](https://github.com/Kiddos19882/AutoDraw/commit/6b1cba9b1c40a030ac6bd7b29365bf19ac3c9149): manifest, logical DrawingPlan (131 strokes), before PNG и Bridge session. Передача была отклонена до brush handoff: `_transfer_brush_test_plan()` добавлял `autodraw_experiment` и записывал после JSON object буквальные символы `\n`; Stage 6 не мог прочитать runtime-файл.
- Bridge session этой попытки показывает Monitor active/boardDetected, exact snapshot `pointCount=1`, `remainingPoints=5999`, `received_event_count=0`, `sentEventCount=0`; after PNG и executor report отсутствуют. Попытка не является live capture и не подтверждает расход CHALK.
- Исправлена запись runtime JSON: добавлен настоящий перевод строки; сообщение ошибки также форматируется с переносами строк. Code commit [8dfd1b5](https://github.com/Kiddos19882/AutoDraw/commit/8dfd1b541f54a1b416dfb2907739cf4b1a99c58d). Добавлен regression test полного FILL-001 plan → Stage 6 load с проверкой experiment context: [1b2d8a1](https://github.com/Kiddos19882/AutoDraw/commit/1b2d8a128c99ab8ad1abb1e9f480702676cd9f56). CI [41692129486](https://github.com/Kiddos19882/AutoDraw/actions/runs/41692129486) выполняется; все regression jobs — SUCCESS; Windows portable build/startup smoke-test — IN_PROGRESS.

**Исправление client ROI — реализовано и подтверждено software CI:**
- Логический BoardPane движка и frozen masks имеют размер 460×240 logical pixels. Это не физический размер доски на клиентском экране.
- UI сохраняет PNG в фактическом размере calibrated screen ROI; физическое требование 460×240 удалено.
- Capture adapter растеризует frozen logical mask в размер PNG ROI методом nearest-neighbor и сохраняет logical→screen transform; пропорции ROI проверяются по uniform-scale tolerance 1%.
- Before/after должны иметь одинаковые фактические ROI; курсор и UI/paint meter исключаются из crop по существующей процедуре.

**Следующий шаг после live attempt 2026-11-04:**
- Не повторять без изменений задачу rectangle / radius 10 / repeat 1: текущий run исчерпал 5999 доступных CHALK до завершения всех 131 consuming strokes.
- Статически проверить frozen DrawingPlan, порядок и геометрию последних штрихов, а также существующий raster simulator/coverage model. Не выдавать расчётную оценку за exact CHALK.
- Определить и документировать, должен ли экспериментальный analyzer отдельно хранить over-budget/censored attempts (точный расход до лимита, но неизвестная полная потребность) наряду с accepted captures. Не менять acceptance criteria задним числом.
- Сохранить P1 и frozen masks неизменными до отдельного решения; любые изменения geometry/strategy оформлять новой версией плана и mask signature.
- Количественный before/after PNG audit выполнить по frozen mask и calibrated ROI; визуальный просмотр PNG не является заменой.
- После статического анализа выбрать обоснованный следующий preflight и только затем использовать восстановленную/новую доску с полной квотой.
- Не запускать 45-cell matrix до принятия preflight и определения обработки over-budget cases.


**Актуальное уточнение 2026-11-04:**
- В `chalk_fill_ui.py` исправлены четыре JSON writes с буквальным `\\n`: executor completion, after PNG, capture JSON и финальный attempt record.
- В `chalk_fill_runtime_binding.py` preparation и validation используют один normalized DrawingPlan document; attach сохраняет canonical document до записи runtime plan.
- Добавлены regression tests на JSON persistence, canonical plan hash и отказ при non-consuming stroke candidates.
- Полный CI [41737923777](https://github.com/Kiddos19882/AutoDraw/actions/runs/41737923777) на `870bebc` — SUCCESS: все обязательные jobs, INT-006 pixel audit и Windows portable build/startup smoke-test прошли; optional benchmarks skipped.
- Live run 131/131 strokes; session exact CHALK=5999. Первый Bridge run — calibration (CHALK=0, 2 non-consuming candidates). Второй run file присутствует, размер 27 934 553 bytes, но содержимое не удалось получить целиком; per-run/per-stroke CHALK не подтверждён.
- Before/after PNG существуют; визуальный просмотр after показывает заполненную прямоугольную область. Количественный mask audit не выполнен. Attempt JSON невалиден, after_png в attempt не записан; capture не принят.
- Ошибка false-overlap устранена в `95a8d17`: binder определяет конец активности по последнему event `t` на performance clock, а `finished_at_utc` использует только для проверки idle finalization grace. Regression test на calibration run с поздней финализацией добавлен в `870bebc`; CI `41737923777` прошёл.
- Полный разбор: [CHALK_FILL001_PREFLIGHT_POSTMORTEM_2026-11-04.md](CHALK_FILL001_PREFLIGHT_POSTMORTEM_2026-11-04.md). 45-cell matrix остаётся BLOCKED; текущая доска исчерпала CHALK quota.

### Шаг 4. Выполнить 45 live captures FILL-001

**Статус:** BLOCKED до принятого live preflight по отдельному versioned варианту FILL-001-RS

- Запустить 3 frozen формы областей × 5 радиусов (1/5/10/20/30) × 3 независимых повтора.
- Для каждой ячейки сохранить DrawingPlan, task/run identity, фактический P1, pre/post pointCount, per-stroke CHALK, Monitor export, Bridge/executor journals и before/after PNG.
- Не смешивать повторы и не перезаписывать первичные evidence.
- Отклонять captures, не прошедшие integrity или visual gates; повторять только по документированной причине с новым run ID.

**Критерий завершения:** analyzer принимает 45/45 уникальных ячеек либо формирует явный список отклонённых ячеек с причинами; все принятые captures имеют проверяемые исходные evidence.

### Шаг 5. Сравнить расход и определить лучшую стратегию заливки

**Статус:** BLOCKED до завершения принятой экспериментальной матрицы

- Рассчитать exact CHALK по каждой форме и радиусу: повторы, mean/median/min/max и разброс.
- Сопоставить CHALK с фактическим покрытием, числом штрихов, суммарным путём и качеством результата.
- Определить, зависит ли расход от радиуса и насколько эффект обусловлен изменением траектории/количества проходов.
- Сравнить варианты стратегии заполнения при одинаковой целевой площади и одинаковых критериях качества.
- Сформулировать проверяемую рекомендацию для AutoDraw: оценка расхода, резерв/запас, допустимые радиусы и способ построения заливки. Отдельно обозначить границы применимости и необходимость дополнительных серий.

**Критерий завершения:** подготовлен отчёт с исходными данными, статистикой, сравнением качества и обоснованной рекомендацией. Изменение production estimator или defaults допускается только отдельным решением после проверки вывода.

## Общие ограничения

- Основной показатель расхода — точная игровая delta `post.pointCount - pre.pointCount`; длина пути и число штрихов являются дополнительными объясняющими метриками.
- Качество заливки: coverage ≥99%, leakage=0, если frozen design не задаёт более строгие условия.
- Synthetic tests не являются live evidence.
- Не запускать live captures до закрытия шагов 1–3.
- Не менять `master`, production estimator, executor defaults и sampling defaults в рамках выполнения этого плана без отдельного основания и согласования.
- Этот план не заменяет технический дизайн FILL-001; он задаёт последовательность gates и критерии завершения.

## История выполнения

| Шаг | Статус | Подтверждение |
|---|---|---|
| 1 | DONE | CI [41730717881](https://github.com/Kiddos19882/AutoDraw/actions/runs/41730717881), code HEAD `fe6d446`; Preparation/G3 782 passed, 24 warnings, 82 subtests; все обязательные jobs, INT-006 audit и Windows portable build/startup smoke-test SUCCESS; optional benchmarks skipped |
| 2 | DONE (software) | Runtime binder, Stage 6 completion hook, UI experiment context и regression coverage прошли CI `41730717881` на `fe6d446`; live proof остаётся частью шага 3 |
| 3 | IN_PROGRESS | Binder fix `95a8d17` и regression tests `870bebc` прошли полный CI `41737923777`. Предыдущий live run: 131/131 strokes, session CHALK=5999, capture rejected. Нужен один новый preflight на восстановленной доске. |
| 4 | BLOCKED | Ожидает шаги 1–3 |
| 5 | BLOCKED | Ожидает 45 принятых captures |


## Историческая запись статуса после CI run 41692129486 — 2026-11-03 (superseded обновлением 2026-11-04)

Предыдущая запись о том, что Windows portable build ещё выполняется, устарела и заменяется этим уточнением.

- CI run [41692129486](https://github.com/Kiddos19882/AutoDraw/actions/runs/41692129486) завершился **SUCCESS**. Все обязательные jobs, INT-006 pixel audit, Windows portable build и startup smoke-test успешны; optional benchmarks skipped.
- Artifact `autodraw-g3-preflight-build` ID `13258221572` опубликован и не истёк: [скачать Windows portable build](https://github.com/Kiddos19882/AutoDraw/actions/runs/41692129486/artifacts/13258221572).
- Программная интеграция FILL-001 и software regression gate подтверждены CI. Шаг 3 остаётся **IN_PROGRESS** до одного реального Windows live preflight.
- Следующее действие оператора: скачать artifact, запустить AutoDraw, открыть вкладку FILL-001 и выполнить ровно одну задачу `rectangle / radius 10 / repeat 1`.
- После запуска сохранить и предоставить execution report, Bridge session/run artifacts, Game Monitor export и before/after PNG. Проверить идентичность task/plan/run, фактический P1 (`point_step=4`, `point_delay=5ms`, `line_extension=0`), exact `pointCount` delta, coverage ≥99% и leakage=0 на реальном client ROI.
- До принятия этого preflight шаги 4–5 остаются **BLOCKED**. CI не является доказательством live game runtime; 45 captures этим обновлением не запускались и не разрешаются.

## Актуальное уточнение 2026-11-04 — retry неполного runtime binding

- Пользовательский evidence commit [b4a107a](https://github.com/Kiddos19882/AutoDraw/commit/b4a107abfd33d3e4c0ded723154444c84c97b2ad) содержал завершённый executor report и after PNG, но runtime_binding_status=failed из-за временно отсутствующего bridge_diagnostics в Bridge session. Поздняя версия session уже содержала diagnostics; capture не был принят.
- В [5cde7a1](https://github.com/Kiddos19882/AutoDraw/commit/5cde7a109a669bebf790ecbeb21f8bbc4feae182) исправлен порядок обработки: session сначала исключается по временному окну/connection close, затем неполная потенциально подходящая session возвращает pending. UI-кнопка повторно запускает binder и продолжает acceptance только после runtime_binding_status=passed.
- Stage 6 и UI используют общий builder runtime summary; worker не перезаписывает уже установленный passed статус.
- Добавлены regression tests на неполную session, её последующее обновление, исключение future session и retry из UI.
- Полный CI [41754801210](https://github.com/Kiddos19882/AutoDraw/actions/runs/41754801210) — SUCCESS; Preparation/G3 787 passed, 24 warnings, 82 subtests; все обязательные jobs, Windows portable build/startup smoke-test и INT-006 pixel audit успешны. Artifact ID 13288855067.
- Это закрывает software retry gate, но не live gate: существующий capture остаётся REJECTED/UNACCEPTED, task-level/per-stroke CHALK и quantitative FILL-001 PNG audit не подтверждены. 45-cell matrix остаётся BLOCKED до нового принятого Windows live preflight на восстановленной доске.



## FILL-001-RS — исследование расстояния между проходами заливки

**Статус:** exhaustive static sweep выполнен; versioned planner/matrix/handoff реализованы; полный CI PASS; local live preflight NOT RUN.
**Назначение:** проверить, как расстояние между соседними scanline-проходами влияет на геометрическое покрытие и затем — отдельным разрешённым live-экспериментом — на фактический расход CHALK.  
**Связь с FILL-001:** это отдельная versioned ветка исследования геометрии. Исходные frozen masks, FILL-001 plans, signatures, manifest, P1 и captures не переписываются.

### Разделение параметров

- `point_step_px` — расстояние между точками внутри одного исполняемого штриха; действующий P1 использует 4 px.
- `scanline_row_step` — расстояние между соседними горизонтальными проходами планировщика в логических координатах доски.
- Эти параметры независимы. Изменение `scanline_row_step` не означает изменения P1 и не должно автоматически менять sampling executor.

### Основание: уже выполненная статическая проверка

Текущий fixed-radius planner размещает проходы практически на каждой строке (`scanline_row_step=1`). При ширине кисти 10 соседние линии перекрываются примерно на 90%. OpenCV-симуляция воспроизвела базовый frozen rectangle r10 plan: 131 штрих, path length 40 218, estimated sampling points 10 237, coverage 100%, leakage 0.

Полный sweep проверил 2 238 сочетаний step/offset в домене step=1..radius и offset=0..step-1; 62 сочетания прошли coverage ≥99% / leakage=0. Выбор: максимальный прошедший row step, затем максимальное coverage и минимальные proxy-метрики. Полный отчёт: [FILL-001-RS static sweep](CHALK_FILL001_RS_STATIC_SWEEP_2026-11-04.md).

| Форма | Радиус | Найденный `scanline_row_step` | Offset |
|---|---:|---:|---:|
| rectangle | 1 | 1 | 0 |
| rectangle | 5 | 2 | 1 |
| rectangle | 10 | 5 | 0 |
| rectangle | 20 | 8 | 4 |
| rectangle | 30 | 11 | 10 |
| wide_irregular | 1 | 1 | 0 |
| wide_irregular | 5 | 4 | 0 |
| wide_irregular | 10 | 7 | 1 |
| wide_irregular | 20 | 5 | 0 |
| wide_irregular | 30 | 10 | 0 |
| narrow_irregular | 1 | 1 | 0 |
| narrow_irregular | 5 | 3 | 1 |
| narrow_irregular | 10 | 5 | 0 |
| narrow_irregular | 20 | 5 | 0 |
| narrow_irregular | 30 | 5 | 0 |

Для r10 / step=5 / offset=0 все три формы прошли текущий офлайн-критерий coverage ≥99% и leakage=0:

| Форма | Штрихи | Длина пути | Estimated sampling points | Coverage | Leakage |
|---|---:|---:|---:|---:|---:|
| rectangle | 27 | 8 250 | 2 099 | 99,319% | 0 |
| wide_irregular | 29 | 8 352 | 2 126 | 99,395% | 0 |
| narrow_irregular | 43 | 8 245 | 2 120 | 99,173% | 0 |

Для rectangle r10 относительно текущего frozen plan это 131 → 27 штрихов, path 40 218 → 8 250 и estimated sampling points 10 237 → 2 099 (сокращение proxy примерно на 79,5%). В симуляции остаются 304 непокрытых пикселя target mask; утечек нет. Запас над порогом покрытия составляет только 0,319 процентного пункта.

**Ограничение доказательности:** это статическая OpenCV-модель, а не отрисовка игровым renderer. Estimated sampling points — proxy, не CHALK. Длина пути и число штрихов не дают права утверждать, что фактический расход CHALK уменьшится на 79,5% или на любую другую величину. Полный расход определяется только разницей игровых `pointCount_after - pointCount_before`.

### Последовательность FILL-001-RS

1. **DONE — сохранить baseline.** Frozen masks, исходные FILL-001 plans/signatures, manifest, P1 и первичные runtime evidence сохранены без изменений.
2. **DONE — exhaustive static sweep.** Проверены все 2 238 step/offset кандидатов; все 15 shape×radius ячеек имеют выбранную конфигурацию, а все candidate records формируются отдельным CI artifact.
3. **DONE — versioned planner/matrix/handoff.** Legacy planner version 1 сохраняет прежнюю геометрию/signature. FILL-001-RS использует versioned planner v2 там, где геометрия меняется; `scanline_row_step` независим от `point_step_px`. Создаётся отдельный 45-task manifest с `execution_allowed=false`; CLI: `source/preparation/create_fill001_rs_manifest.py`.
4. **DONE — software/CI validation.** Preparation/G3 800 passed, 24 warnings, 82 subtests; exhaustive 2 238-candidate sweep и artifact upload SUCCESS; executor, Game Monitor/Bridge, application integration, INT-006 pixel audit и Windows portable build/startup smoke-test SUCCESS. Optional algorithm benchmarks skipped.
5. **READY FOR LOCAL PREFLIGHT — один candidate.** После успешного CI создать новый `fill001-rs-*` manifest, открыть его существующей вкладкой FILL-001 и запустить только `rectangle/r10/step=5/offset=0/repeat=1`. Требуются восстановленная доска с полной квотой и фактический Windows/browser game session.
6. **BLOCKED — capture acceptance.** Принять только при exact task↔executor↔Bridge↔Monitor binding, completed 27/27 strokes, exact pointCount delta, неизменном P1 и quantitative PNG gate coverage≥99%/leakage=0. При quota exhaustion сохранить censored attempt, не оценивать полную стоимость.
7. **BLOCKED — расширение матрицы.** Решать вопрос о 45 live captures FILL-001-RS только после принятого одиночного preflight. Исходную FILL-001 matrix не переписывать.

### Критерии завершения и блокировки

- Статическая часть: 15 shape×radius cells с воспроизводимыми входами, параметрами поиска и raster metrics; все отклонения и неподдерживаемые ячейки сохранены.
- Live preflight: один завершённый task с однозначной task↔executor↔Bridge↔Monitor связью, exact CHALK и принятым количественным PNG audit.
- До принятого live preflight FILL-001 45-cell matrix остаётся BLOCKED.
- INT-006 safety margin не считается установленным, INT-007 остаётся BLOCKED.
- Production estimator, production planner, executor defaults, P1 sampling defaults, исходные FILL-001 plans/captures и `master` не изменяются этим этапом.

**Текущее решение:** статический sweep и versioned implementation выполнены; r10 / rectangle / step=5 / offset=0 — первый live preflight candidate, но не утверждённая настройка AutoDraw. Code/tests/config/workflow изменены только в рамках данного прямого разрешения пользователя. Live preflight ещё не выполнен: удалённый GitHub workflow не имеет доступа к локальной браузерной игровой сессии и calibrated board.

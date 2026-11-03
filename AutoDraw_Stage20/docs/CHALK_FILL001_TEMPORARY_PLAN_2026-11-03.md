# Временный план дальнейших работ FILL-001

**Статус:** актуальный временный план, обязателен к сохранению до выполнения всех пяти шагов или отдельного решения пользователя.  
**Дата:** 2026-11-03  
**Рабочая ветка:** `feature/image-geometry-optimization`  
**Область:** подготовка и проведение контролируемого эксперимента по расходу CHALK при заполнении областей кистями разных радиусов.

## Цель

Получить воспроизводимые данные о фактическом расходе CHALK для заполнения областей сопоставимой площади, определить влияние радиуса кисти и сравнить стратегии построения заливки. Не менять production estimator и стандартные параметры исполнения до отдельного решения на основании результатов.

## Пять шагов

### Шаг 1. Закрыть программный regression gate

**Статус:** DONE

- GitHub Actions [41686091985](https://github.com/Kiddos19882/AutoDraw/actions/runs/41686091985) — SUCCESS на code/test HEAD `031913c64da5f25921d74f426a2c7778c02130ee` (включает client-ROI correction).
- Preparation/G3: **772 passed, 24 warnings, 82 subtests passed**.
- Executor regression, Game Monitor/Bridge, Application integration, INT-006 pixel audit и Windows portable build/startup smoke-test — SUCCESS; optional algorithm benchmarks — SKIPPED.
- Windows portable artifact: [autodraw-g3-preflight-build](https://github.com/Kiddos19882/AutoDraw/actions/runs/41673570178/artifacts/13248469807).
- CI подтверждает software regression gate, но не live FILL-001 запуск в браузерной игре и не проверку реальных board PNG.

**Критерий завершения:** выполнен — все обязательные jobs и Windows portable build/startup smoke-test успешны на одном code/test HEAD.

### Шаг 2. Привязать captures к фактическому runtime

**Статус:** DONE (software/runtime integration и regression gate)

- `chalk_fill_runtime_binding.py` читает persisted Bridge `session.json`, run JSON и executor report.
- Проверяются Bridge schema v2, session/run identity, временное окно executor, timezone-aware timestamps, sequence gaps, send failures, Monitor errors, stroke lifecycle, единый observed radius, exact pre/post snapshots и совпадение exact CHALK с sampled/per-stroke deltas.
- Фактические `ExecutorConfig.point_step_px=4`, `point_delay_ms=5` и `line_extension_px=0` сверяются с frozen P1.
- Stage 6 выполняет post-execution binding после успешного завершения FILL-001 task и записывает результат в execution report.
- UI handoff передаёт experiment context в DrawingPlan; runtime binder связывает executor report с Bridge session/run и фиксирует SHA-256 исходных runtime artifacts.
- Regression gate подтверждён CI [41686091985](https://github.com/Kiddos19882/AutoDraw/actions/runs/41686091985) на code/test HEAD `031913c`.

**Критерий завершения:** программная интеграция и fail-closed regression tests подтверждены CI. Реальное live подтверждение на Windows относится к шагу 3.

### Шаг 3. Интегрировать запуск в AutoDraw и провести Windows live preflight

**Статус:** IN_PROGRESS — первая пользовательская попытка остановилась на handoff из-за невалидного runtime JSON; исправление и regression test внесены, новый CI и повторный Windows live preflight ожидаются.

**Подтверждённая реализация UI/runner:**
- Добавлен `source/preparation/chalk_fill_ui.py` и самостоятельная вкладка FILL-001 в `integrated_app.py`, отдельная от седьмой вкладки «Тест кистей».
- UI создаёт/загружает manifest из 45 задач, показывает task identity/shape/radius/repeat/expected strokes/plan signature и выбирает только pending task с пройденным quality gate.
- Перед передачей пересчитывается fixed-radius plan и сверяются frozen plan signature, mask SHA-256, coverage/leakage, expected strokes и matrix/task identity.
- Исполнение ограничено одной выбранной task с явным подтверждением оператора; batch execution всей матрицы запрещён.
- Размер кисти устанавливается через существующий Brush Test workflow; затем создаётся DrawingPlan с FILL-001 experiment context и запускается Stage 6 с P1 override.
- После исполнения UI сохраняет before/after board PNG и передаёт runtime evidence в capture adapter; прямой запуск FILL-001 plan в обход специализированного workflow закрыт fail-closed guard.
- Unified app regression test проверяет регистрацию вкладки `8. FILL-001`; следующая вкладка — `9. Калибровка теста`.
- Первая пользовательская попытка сохранена в commit [6b1cba9](https://github.com/Kiddos19882/AutoDraw/commit/6b1cba9b1c40a030ac6bd7b29365bf19ac3c9149): manifest, logical DrawingPlan (131 strokes), before PNG и Bridge session. Передача была отклонена до brush handoff: `_transfer_brush_test_plan()` добавлял `autodraw_experiment` и записывал после JSON object буквальные символы `\\n`; Stage 6 не мог прочитать runtime-файл.
- Bridge session этой попытки показывает Monitor active/boardDetected, exact snapshot `pointCount=1`, `remainingPoints=5999`, `received_event_count=0`, `sentEventCount=0`; after PNG и executor report отсутствуют. Попытка не является live capture и не подтверждает расход CHALK.
- Исправлена запись runtime JSON: добавлен настоящий перевод строки; сообщение ошибки также форматируется с переносами строк. Code commit [8dfd1b5](https://github.com/Kiddos19882/AutoDraw/commit/8dfd1b541f54a1b416dfb2907739cf4b1a99c58d). Добавлен regression test полного FILL-001 plan → Stage 6 load с проверкой experiment context: [1b2d8a1](https://github.com/Kiddos19882/AutoDraw/commit/1b2d8a128c99ab8ad1abb1e9f480702676cd9f56). CI для fix ещё не подтверждён.

**Исправление client ROI — реализовано и подтверждено software CI:**
- Логический BoardPane движка и frozen masks имеют размер 460×240 logical pixels. Это не физический размер доски на клиентском экране.
- UI сохраняет PNG в фактическом размере calibrated screen ROI; физическое требование 460×240 удалено.
- Capture adapter растеризует frozen logical mask в размер PNG ROI методом nearest-neighbor и сохраняет logical→screen transform; пропорции ROI проверяются по uniform-scale tolerance 1%.
- Before/after должны иметь одинаковые фактические ROI; курсор и UI/paint meter исключаются из crop по существующей процедуре.

**Оставшийся Windows live preflight:**
- Сначала получить SUCCESS CI для исправления runtime JSON и нового FILL-001 integration regression test.
- Затем повторно запустить из AutoDraw одну задачу (первая предпочтительная ячейка — rectangle/radius 10/repeat 1) на реальной игровой сессии.
- Подтвердить task ↔ DrawingPlan ↔ executor report ↔ Bridge session/run identity и фактический P1 в execution report.
- Проверить реальные before/after PNG в реальном client ROI, RGB threshold 8, cursor/UI exclusion, frozen mask alignment, coverage ≥99% и leakage=0.
- Проверить fail-closed поведение на mismatch run/task/plan, неверном P1, Bridge errors и отсутствующих/изменённых PNG.

**Критерий завершения:** один реальный запуск из FILL-001 UI однозначно связан с executor report и Bridge session/run; реальные PNG проходят quality/evidence gates на Windows с фактическим ROI клиента и сохранённым logical→screen transform. До этого 45-cell live matrix не запускать.

### Шаг 4. Выполнить 45 live captures FILL-001

**Статус:** BLOCKED до завершения шагов 1–3

- Запустить 3 frozen формы областей × 5 радиусов (1/5/10/20/30) × 3 независимых повтора.
- Для каждой ячейки сохранить DrawingPlan, task/run identity, фактический P1, pre/post pointCount, per-stroke CHALK, Monitor export, Bridge/executor journals и before/after PNG.
- Не смешивать повторы и не перезаписывать первичные evidence.
- Отклонять captures, не прошедшие integrity или visual gates; повторять только по документированной причине с новым run ID.

**Критерий завершения:** analyzer принимает 45/45 уникальных ячеек либо формирует явный список отклонённых ячеек с причинами; все принятые captures имеют проверяемые исходные evidence.

### Шаг 5. Сравнить расход и определить лучшую стратегию заливки

**Статус:** BLOCKED до завершения шага 4

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
| 1 | DONE | CI [41686091985](https://github.com/Kiddos19882/AutoDraw/actions/runs/41686091985), code/test HEAD `031913c`; Preparation/G3 778 passed, 24 warnings, 82 subtests; все обязательные jobs и Windows portable build/startup smoke-test SUCCESS; optional benchmarks skipped |
| 2 | DONE (software) | Runtime binder, Stage 6 completion hook, UI experiment context и regression CI [41686091985](https://github.com/Kiddos19882/AutoDraw/actions/runs/41686091985), code/test HEAD `031913c`; live proof переносится в шаг 3 |
| 3 | IN_PROGRESS | Commit `6b1cba9` выявил invalid runtime JSON handoff; fix `8dfd1b5` и regression test `1b2d8a1` добавлены, новый CI ожидается; затем требуется повторный Windows live runtime/PNG preflight и evidence report |
| 4 | BLOCKED | Ожидает шаги 1–3 |
| 5 | BLOCKED | Ожидает 45 принятых captures |

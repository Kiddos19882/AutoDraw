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

- Исправление сигнатуры `audit_fill001_png_pair()` подтверждено commit [b4cc45a](https://github.com/Kiddos19882/AutoDraw/commit/b4cc45a80231e6bad2f878b2a5a2f16b48b9d68b): helper принимает `shape_id`, `before_png`, `after_png`; внутренний вызов и тест используют эту сигнатуру.
- Полный Preparation/G3 suite на Windows runner: **754 passed, 24 warnings, 82 subtests passed**; включает matrix и capture adapter tests.
- Полный GitHub Actions run [41579136690](https://github.com/Kiddos19882/AutoDraw/actions/runs/41579136690) завершился SUCCESS на code HEAD `b4cc45a80231e6bad2f878b2a5a2f16b48b9d68b`; обязательные Game Monitor/Bridge, Preparation/G3, Application integration, Executor regression, INT-006 audit и Windows portable build jobs успешны.
- Windows portable build создал артефакт [autodraw-g3-preflight-build](https://github.com/Kiddos19882/AutoDraw/actions/runs/41579136690/artifacts/13204044319); лог подтверждает запуск `AutoDraw.exe`, 10 секунд активного процесса и успешный smoke-test.
- Optional algorithm benchmarks были skipped по настройке workflow; локальный pytest в этой среде не запускался. Ошибок обязательных jobs нет.

**Критерий завершения:** выполнен — все обязательные тестовые jobs и Windows build/smoke-test успешны на одном code HEAD; CI run и SHA зафиксированы.

### Шаг 2. Привязать captures к фактическому runtime

**Статус:** DONE (software implementation и regression gate)

- Добавлен `chalk_fill_runtime_binding.py`, который читает persisted Bridge `session.json`, run JSON и executor report.
- Проверяются Bridge schema v2, session/run identity, временное окно executor, timezone-aware timestamps, sequence gaps, send failures, Monitor errors, stroke lifecycle, единый observed radius, exact pre/post snapshots и совпадение exact CHALK с sampled/per-stroke deltas.
- Фактические `ExecutorConfig.point_step_px=4` и `point_delay_ms=5` сверяются с frozen P1.
- Runtime binding подключён к завершению успешного FILL-001 исполнения в Stage 6; report обновляется результатом фоновой проверки.
- Capture adapter получает runtime evidence через `build_fill001_capture_from_runtime()` и фиксирует SHA-256 session/run/executor artifacts.
- Изменения кода и тестов вошли в commits `fbf1fd6`–`d7466c5`; полный CI [41591543009](https://github.com/Kiddos19882/AutoDraw/actions/runs/41591543009) завершился SUCCESS на code HEAD `d7466c5`.

**Критерий завершения:** программная интеграция и fail-closed regression tests подтверждены CI. Реальное live подтверждение на Windows относится к шагу 3 и ещё не выполнено.

### Шаг 3. Интегрировать запуск в AutoDraw, затем провести Windows live preflight

**Статус:** TODO — пользовательский UI/runner handoff отсутствует; live preflight ещё не может быть запущен штатным workflow AutoDraw.

- Реализовать отдельный FILL-001 UI/runner: создание/загрузка серии, выбор task, журнал, Start/Stop и progress. Точный gap и критерии: [аудит интеграции](CHALK_FILL001_AUTODRAW_INTEGRATION_AUDIT_2026-11-03.md).
- Добавить fail-closed преобразование planner output в DrawingPlan и сохранение `autodraw_experiment` context; разрешать исполнение только выбранной валидной task.
- Добавить FILL001 в task-specific executor configuration allowlist с проверкой P1 до первого mouse action.
- Кодовый PNG audit уже открывает реальные PNG, проверяет формат/размер crop 460×240, рассчитывает SHA-256, coverage/leakage по RGB difference threshold=8; synthetic regression tests включены в CI.
- На Windows выполнить один контролируемый FILL-001 runtime run и проверить, что execution report получил успешный runtime binding к правильным Bridge session/run artifacts.
- Подтвердить P1 по фактическому ExecutorConfig в отчёте, а не только по frozen task metadata.
- Проверить реальные before/after board PNG: crop 460×240, положение курсора, исключение UI/paint meter, frozen mask alignment, coverage ≥99% и leakage=0.
- Проверить fail-closed поведение на отсутствующем/изменённом PNG, несовпадающем run ID, ошибках Bridge и неверном P1.

**Критерий завершения:** из UI AutoDraw запускается одна выбранная task; executor report содержит её context; runtime binder однозначно связывает report с Bridge session/run; реальные PNG проходят crop/quality/evidence gates на Windows; негативные случаи отклоняются. До этого live matrix не запускать.

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
| 1 | DONE | CI [41579136690](https://github.com/Kiddos19882/AutoDraw/actions/runs/41579136690), code HEAD `b4cc45a80231e6bad2f878b2a5a2f16b48b9d68b`; Preparation/G3 754 passed + 82 subtests; Windows build/smoke-test success |
| 2 | DONE (software) | Runtime binder + Stage 6 integration + regression CI [41591543009](https://github.com/Kiddos19882/AutoDraw/actions/runs/41591543009), code HEAD `d7466c5`; live proof переносится в шаг 3 |
| 3 | TODO | Сначала требуется UI/runner handoff FILL-001, затем Windows live runtime/PNG preflight и evidence report |
| 4 | BLOCKED | Ожидает шаги 1–3 |
| 5 | BLOCKED | Ожидает 45 принятых captures |

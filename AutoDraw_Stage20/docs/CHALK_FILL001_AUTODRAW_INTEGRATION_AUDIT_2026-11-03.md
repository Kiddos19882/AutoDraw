# FILL-001 — аудит интеграции запуска в AutoDraw

**Дата:** 2026-11-03  
**Статус:** аудит завершён; пользовательский запуск не интегрирован  
**Ветка:** `feature/image-geometry-optimization`  
**Проверенный HEAD:** `01cb37d6cb8fc7c5ec56e648330abda31875f15b`  
**Область:** путь от интерфейса AutoDraw до построения плана, штатного Executor и runtime evidence.  
**Ограничение:** аудит статический; игра и Windows live preflight не запускались.

## Итог

FILL-001 нельзя считать запускаемым из пользовательского интерфейса AutoDraw. Реализованы экспериментальный planner, frozen masks, 45-cell matrix/analyzer, capture adapter и post-execution runtime binder. Однако в текущем коде не найдено связующего пользовательского workflow, который выбирает FILL-001 task, создаёт исполняемый DrawingPlan, передаёт его в Stage 6 и инициирует контролируемый запуск.

Предыдущая формулировка «runtime binding подключён к Stage 6» верна только для post-execution hook: Stage 6 может запустить проверку уже завершённого FILL-001 run, если execution report содержит соответствующий experiment context. Это не означает, что FILL-001 можно запустить из AutoDraw.

## Проверенная цепочка

### 1. Подготовка эксперимента

- `source/preparation/chalk_fill_experiment.py` содержит frozen target masks.
- `source/preparation/chalk_fill_fixed_radius_planner.py` строит экспериментальный fixed-radius plan и моделирует coverage/leakage.
- `source/preparation/chalk_fill_matrix.py` создаёт 45 задач: 3 формы × 5 радиусов × 3 повтора; валидирует manifest и анализирует captures.
- В matrix/task contract установлены `execution_allowed=false` и `safe_to_execute=false`. Это намеренный fail-closed запрет, а не готовая команда запуска.
- Planner возвращает документ с типом `autodraw_fill001_fixed_radius_experimental`; отдельного UI handoff, превращающего задачу в разрешённый DrawingPlan, в проверенной цепочке не обнаружено.

### 2. Интерфейс Brush Test

Проверен `source/preparation/brush_behavior_test_ui.py`:
- в файле нет регистрации `FILL001`, выбора FILL-001 manifest/task или отдельного runner workflow;
- существующий интерфейс обслуживает текущие Brush Test сценарии и матрицы.

Проверен `integrated_app.py`:
- `BrushBehaviorTestTab` подключён к `_transfer_brush_test_plan()` и `_start_brush_test_executor()`;
- передача обычного Brush Test плана использует `current_brush_behavior_test.json`;
- логический план преобразуется в screen-local координаты и загружается в штатный Stage 6;
- матричный executor override распознаёт G3, V1–V5, INT006 и INT006R; FILL001 в allowlist отсутствует;
- callback завершения направляет результаты обычного Brush Test в `handle_executor_finished()`, отдельного FILL-001 task/block lifecycle нет.

### 3. Stage 6 и runtime binding

- `source/executor/stage6_execute_plan.py` запускает post-execution binding только при успешном завершении, когда execution report уже содержит `experiment_context.phase_id == "FILL001"`.
- Worker вызывает `find_fill001_runtime_binding()` и записывает результат в execution report.
- `source/executor/drawing/execution_diagnostics.py` получает `experiment_context` из поля `autodraw_experiment` исходного plan-файла.
- `attach_fill001_experiment_context()` в `chalk_fill_runtime_binding.py` умеет добавить этот context к DrawingPlan JSON. В production UI/runner handoff вызов этого helper не найден.
- Следовательно, runtime binder готов проверять подходящий запуск, но текущий пользовательский workflow не создаёт нужный plan/context и не инициирует FILL-001 execution.

## Подтверждённые пробелы

1. Нет UI-действия для создания/выбора FILL-001 серии и manifest.
2. Нет UI/block runner, который последовательно выбирает task из 45-cell matrix, учитывает repeat/task identity и сохраняет журнал попытки.
3. Нет fail-closed преобразования experimental planner output в Stage 6 DrawingPlan с сохранением frozen plan identity и `autodraw_experiment` context.
4. Нет FILL001 ветки в task-specific executor configuration override; фактический P1 (step=4, delay=5 ms) должен назначаться и проверяться для выбранной задачи.
5. Нет подтверждённой связи task → executor report → Bridge run → capture adapter из пользовательского запуска.
6. Не выполнен Windows live preflight и не проверены реальные PNG crop, cursor/UI exclusion, frozen-mask alignment, coverage ≥99% и leakage=0.

## Что уже подтверждено и что не следует переоценивать

- CI run `41591543009` SUCCESS на code HEAD `d7466c5` подтверждает regression/software gate для кода runtime binder и Stage 6 hook.
- CI не доказывает существование UI запуска FILL-001 и не является live game run.
- Synthetic PNG/Bridge fixtures не заменяют реальные Windows captures.
- Текущие experimental planner plans остаются unsafe/not-ready для automatic execution; нельзя просто снять эти флаги или передавать их в Executor без отдельного execution gate.
- Production estimator, стандартные параметры Executor, sampling defaults, frozen INT-006 model и `master` в рамках аудита не менялись.

## Необходимая следующая реализация

1. Добавить отдельный FILL-001 workflow в Brush Test (или отдельный UI-компонент, если это лучше соответствует архитектуре): создание/загрузка manifest, просмотр task, Start/Stop, progress и журнал.
2. Для одной выбранной task выполнять fail-closed conversion experimental fill plan → DrawingPlan; проверять frozen mask hash, plan signature, canvas/ROI, radius, expected_strokes и sampling P1.
3. Сохранять `autodraw_experiment` context в исходном DrawingPlan JSON так, чтобы Stage 6 report получил `experiment_context`.
4. Добавить отдельный allowlist FILL001 в executor workflow, не затрагивая обычные настройки и production defaults. Конфигурация должна быть task-specific и проверяться до mouse action.
5. После исполнения связывать report с Bridge session/run, затем передавать доказательства в capture adapter и PNG audit.
6. Добавить positive/negative regression tests: missing/tampered manifest, unsupported planner cell, неправильный radius/P1, mismatch plan hash/task identity, Bridge ambiguity, неуспешное исполнение и отсутствие PNG.
7. Только после software CI и portable build перейти к одному Windows live preflight. 45-cell matrix остаётся заблокированной до успешного preflight.

## Критерии завершения интеграции

- Из интерфейса AutoDraw можно создать/открыть FILL-001 series и выбрать одну конкретную task.
- Перед первым mouse action валидируются manifest, frozen plan identity, quality gate, ROI, brush radius и P1.
- Stage 6 получает именно эту задачу и сохраняет однозначный executor report с experiment context.
- Runtime binder находит ровно одну Bridge session/run и связывает их с тем же task/execution.
- Capture adapter формирует проверяемые evidence; PNG audit работает на реальных board captures.
- Все негативные случаи fail closed; обычное исполнение AutoDraw и production defaults не меняются.

## Git-сверка

На момент аудита ветка `feature/image-geometry-optimization` имела HEAD `01cb37d6cb8fc7c5ec56e648330abda31875f15b`. Compare с `master` вернул `diverged`, ahead_by=2529, behind_by=5; merge/rebase не выполнялся. Значение сравнения зафиксировано как метаданные API compare и не является основанием для синхронизации веток без отдельной проверки истории.

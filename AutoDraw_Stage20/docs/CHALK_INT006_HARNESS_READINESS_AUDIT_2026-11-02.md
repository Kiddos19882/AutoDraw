# INT-006 — аудит готовности harness для независимой validation

**Дата:** 2026-11-02  
**Ветка:** `feature/image-geometry-optimization`  
**Результат:** BLOCKED — протокол D1–D5 описан, но текущий пакетный harness не поддерживает эту независимую серию целиком.  
**Граница проверки:** статический аудит исходников и документации GitHub; локальный запуск Windows и live/browser execution не выполнялись.

## 1. Краткий вывод

Нельзя запускать D1–D5 через существующий UI как будто они уже подключены. В текущем коде подтверждены:
- `chalk_experiment_matrix.py` содержит фазы G1/G2/G3 и V1–V5, но не D1–D5/independent validation;
- `chalk_test_blocks.py` строит блоки G1/G2/G3/V1–V5; отдельной 45-cell серии независимой validation нет;
- `brush_behavior_test_ui.py` содержит сценарии V1–V5 и V2/V5 follow-up, но сценарии D1–D5 отсутствуют;
- `integrated_app.py` разрешает executor override только для G3 и V1–V5;
- общий analyzer умеет проверять matrix manifests и агрегировать повторы, но его вывод пока не является сравнением frozen predictions с фактическим расходом.

Поэтому документированный статус READY FOR LIVE VALIDATION преждевременен: пользовательский протокол готов, но запускной контракт приложения ещё не готов.

## 2. Что уже готово и повторно использовать

Не создавать второй executor, Game Monitor bridge или новый block journal. Существующие компоненты уже дают нужные базовые гарантии:
- создание логического DrawingPlan и преобразование в screen ROI;
- штатный MouseExecutor через Stage6;
- установка радиуса кисти и проверка свежего Game Monitor heartbeat;
- точные pre/post pointCount и per-stroke pointDelta;
- привязка capture к experiment/run/task IDs;
- fail-closed acceptance, recovery, exclusive owner lock и durable journal;
- before/after PNG и сохранение experiment manifests.

Новая работа должна расширить контракт существующей лаборатории, не дублировать её инфраструктуру.

## 3. Подтверждённые пробелы

### 3.1 Matrix contract

Добавить отдельную фазу независимой validation, например `INT006`, с пятью scenario IDs:
- `int006_validation_d1_mixed_lines` — 4 штриха;
- `int006_validation_d2_polygon` — 5 штрихов;
- `int006_validation_d3_intersections` — 6 штрихов;
- `int006_validation_d4_short_details` — 6 штрихов;
- `int006_validation_d5_repeated_coverage` — 6 исполнений штрихов.

Сохранить существующий профильный контракт P0=(2,10), P1=(4,5), P2=(4,10), radius=10. В одном block journal должны находиться 5 сценариев × 3 профиля × 3 повтора = 45 уникальных задач. Не переиспользовать V-сценарии, старые manifests или matrix IDs.

### 3.2 Block journal

Расширить planner и validator так, чтобы они проверяли полный набор 45 уникальных ячеек:
`(scenario_id, point_step_px, point_delay_ms, repeat_index)`.
Проверять ожидаемое число strokes каждого D-сценария, единый radius=10, точный набор executor parameters, уникальный matrix order и отсутствие смешивания фаз.

### 3.3 Brush Test UI

Добавить пять DrawingPlan с координатами из независимого validation protocol. Каждая сторона D2 и каждый проход D5 должны оставаться отдельным stroke. D4 должен использовать точные длины lookup 1/2/3/5/8/10 без автоматической интерполяции. Все планы должны проходить logical bounds 460×240 и существующий screen transform.

Добавить отдельную фазу INT006 в selector автоматического блока. Не открывать её через одиночный ручной запуск сценария.

### 3.4 Executor handoff

Разрешить временный task-specific executor override для INT006 только после строгой проверки:
- phase/scenario соответствуют задаче журнала;
- radius=10;
- stroke count соответствует D1–D5;
- параметры полностью совпадают с одним из P0/P1/P2;
- task ID, block ID и matrix metadata связаны с одним manifest.

Production defaults не изменять.

### 3.5 Frozen prediction records и analyzer

До live запуска создать immutable prediction records для всех 15 сочетаний DrawingPlan/profile. В записи фиксировать модель/версию, коэффициенты, правило linear/lookup, per-stroke prediction, сумму, геометрию, hash DrawingPlan, radius и executor profile.

Расширить анализатор отдельным режимом INT006:
- принимать только completed/accepted manifests;
- проверять 45 уникальных ячеек и три повтора;
- сопоставлять manifest с prediction record по hash/ID;
- рассчитывать actual CHALK из exact pre/post pointCount;
- рассчитывать residual=actual−predicted, MAE, RMSE, bias, MAPE (с оговоркой о малых значениях), max absolute error и max positive residual;
- выдавать отдельные результаты по D1–D5 и P0/P1/P2;
- fail closed при неполных predictions, неизвестном geometry hash, duplicate/missing cells или некорректной capture integrity.

Не выполнять refit коэффициентов по этим данным до фиксации первичных validation metrics.

## 4. Regression tests и CI gates

Обязательные проверки:
1. Matrix metadata принимает только пять новых D scenario IDs и точные stroke counts.
2. Planner создаёт ровно 45 задач; каждая комбинация сценарий/профиль/повтор встречается ровно один раз.
3. Journal validator отклоняет пропущенную, повторную, смешанную или изменённую ячейку.
4. D1–D5 plans совпадают с протоколом, имеют точное число strokes и проходят logical bounds.
5. UI передаёт matrix metadata и block identity без legacy radius-matrix collision.
6. Executor handoff разрешает только P0/P1/P2 и отказывает при любом mismatch.
7. Acceptance сохраняет exact CHALK и complete per-stroke breakdown.
8. Analyzer проверяет frozen predictions и корректно считает метрики на synthetic fixtures.
9. Существующие G1/G2/G3/V1–V5 и legacy V2/V5 tests остаются зелёными.
10. Полный CI включает Windows portable build/startup smoke-test.

## 5. Порядок выполнения

- [ ] Добавить INT006 matrix/scenario contract.
- [ ] Добавить D1–D5 DrawingPlan в Brush Test UI.
- [ ] Добавить 45-cell block planner и строгую journal validation.
- [ ] Подключить task-specific executor override в integrated_app.
- [ ] Добавить immutable prediction records и INT006 analyzer.
- [ ] Добавить regression/orchestration tests.
- [ ] Обновить API/module/test maps и документацию.
- [ ] Подтвердить полный CI на текущем code HEAD.
- [ ] После CI подготовить Windows 10 preflight и передать пользователю точную инструкцию.
- [ ] Только после локального preflight и явного подтверждения чистой тестовой доски запускать 45 live captures.

## 6. Запреты

- Не менять production estimator, MouseExecutor defaults или sampling defaults.
- Не переобучать frozen models на validation captures до расчёта первичных метрик.
- Не менять/перезаписывать исходные G1/G2/G3/V1–V5 manifests, journals, reports и PNG.
- Не запускать live tests из CI.
- Не объявлять INT-006 завершённой и не открывать INT-007 до validation и обоснованного safety margin.
- Не утверждать, что локальный Windows preflight или live capture выполнены без результатов пользователя.

## 7. Текущий следующий шаг

Реализовать INT006 как расширение существующих matrix/block/UI/Stage6/analyzer контрактов. Новый отдельный executor не нужен. После реализации и CI пользователь выполняет только локальный preflight; live серия начинается после проверки готовности игры и доски.


## 8.1. Итог реализации и CI — 2026-11-02

Предыдущие выводы разделов 1–7 отражают исходное состояние до разработки. Software implementation завершена:
- `chalk_int006_validation.py`: frozen model, 15 prediction records, hash-sealed artifact и analyzer;
- `chalk_test_blocks.py`: 45-cell journal с prediction artifact и prediction IDs;
- Brush Test UI: блокировка ручного запуска D1–D5 и запись prediction ID;
- `integrated_app.py`: fail-closed проверка prediction ID при executor handoff.

Полный workflow [41513389663](https://github.com/Kiddos19882/AutoDraw/actions/runs/41513389663) завершился success: 667 passed, 82 subtests passed; Application integration, Executor regression, Game Monitor/bridge, pixel-level audit и Windows portable build/startup smoke-test — success.

**Оставшийся блокер:** пользовательский Windows 10 preflight. До его успешного завершения 45 live captures не начинать. Production estimator/defaults не менялись.

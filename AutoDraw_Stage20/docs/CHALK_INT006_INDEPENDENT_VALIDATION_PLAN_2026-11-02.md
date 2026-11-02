# INT-006 — план независимой validation модели CHALK

**Дата:** 2026-11-02  
**Статус:** LIVE CAPTURES COMPLETE (45/45); FORMAL QUANTITATIVE VALIDATION PENDING — D1–D5 выполнены, предварительный аудит JSON записей пройден. Требуется официальный analyzer report и hash/binding verification.  
**Ветка:** `feature/image-geometry-optimization`  
**Связанные задачи:** INT-006; gate перед INT-007  
**Ограничения:** production estimator, executor defaults и исходные экспериментальные данные не изменять.

## Технический gate перед запуском

Исторический readiness audit ниже был выполнен до реализации и зафиксировал отсутствие D1–D5 в harness. Этот блок сохранён как история выявления проблемы. Текущая реализация и успешный software gate описаны в [отчёте frozen predictions/analyzer](CHALK_INT006_FROZEN_PREDICTIONS_AND_ANALYZER_2026-11-02.md); текущие оставшиеся gates — официальный analyzer JSON, frozen artifact SHA-256 и полный journal/task binding audit.

## 1. Цель

Проверить, насколько замороженные модели P0/P1/P2 прогнозируют точный расход CHALK на новых целых DrawingPlan, составленных из нескольких штрихов. Валидационная выборка не должна использоваться для переобучения коэффициентов до расчёта метрик.

Фактический расход каждого run:

`CHALK_actual = post.pointCount - pre.pointCount`

CHALK — число принятых игрой точек. Длина пути, площадь пикселей и визуальная шкала не заменяют exact delta.

## 2. Замороженные модели

До первого live capture сохранить версию этого документа/модели и рассчитанные прогнозы. После начала серии коэффициенты не менять.

| Профиль | Executor | Прямая модель на один stroke |
|---|---|---|
| P0 | step=2, delay=10 ms | `1.765 + 0.2988 × L` |
| P1 | step=4, delay=5 ms | `1.475 + 0.148865 × L` |
| P2 | step=4, delay=10 ms | `1.440 + 0.149151 × L` |

`L` — длина отдельного прямого stroke в logical px. P0 построена на G1; P1/P2 — исследовательские fits на прежних 66 новых per-stroke наблюдениях. Ни один профиль пока не имеет независимой validation на полном DrawingPlan.

Для коротких штрихов использовать только уже зафиксированный lookup для точных длин 1/2/3/5/8/10 logical px:

| Длина | P0 | P1 | P2 |
|---:|---:|---:|---:|
| 1 | 2.00 | 2.00 | 2.00 |
| 2 | 2.67 | 2.00 | 2.00 |
| 3 | 2.67 | 2.00 | 2.00 |
| 5 | 3.67 | 2.33 | 2.67 |
| 8 | 4.00 | 3.00 | 3.00 |
| 10 | 5.00 | 3.67 | 3.67 |

Для длины, которой нет в lookup и которая не попадает в подтверждённую область прямой модели, не интерполировать молча: помечать прогноз как unsupported/UNKNOWN. Для заливки и произвольных кривых текущая модель не задаёт подтверждённого расчёта.

## 3. Независимые DrawingPlan

Пять планов ниже — новые композиции. Они не повторяют исходные G1/G2/G3/V1–V5 plans. Все координаты заданы в логической системе доски 460×240. Каждый прямой stroke должен быть отдельным stroke в плане, а не сегментом, автоматически объединённым с соседним.

### D1 — смешанный линейный рисунок

Четыре изолированных прямых штриха:

1. (30, 30) → (130, 30), L=100
2. (160, 20) → (160, 100), L=80
3. (210, 25) → (280, 95), L≈98.995
4. (310, 100) → (390, 40), L=100

Замороженная сумма прогноза:

| Профиль | CHALK estimate |
|---|---:|
| P0 | 120.30 |
| P1 | 62.32 |
| P2 | 62.29 |

### D2 — контур из отдельных сторон

Пять отдельных strokes, образующих замкнутый пятиугольник:

1. (40, 35) → (130, 25), L≈90.554
2. (130, 25) → (170, 85), L≈72.111
3. (170, 85) → (110, 155), L≈92.195
4. (110, 155) → (30, 115), L≈89.443
5. (30, 115) → (40, 35), L≈80.623

Замыкание выполняется совпадением конечной точки последнего stroke с началом первого. Каждая сторона — отдельный stroke, чтобы стоимость старта не скрывалась внутри одной общей длины.

| Профиль | CHALK estimate |
|---|---:|
| P0 | 135.79 |
| P1 | 70.63 |
| P2 | 70.58 |

### D3 — рисунок с пересечениями

Шесть отдельных прямых strokes:

1. (40, 30) → (140, 130), L≈141.421
2. (40, 130) → (140, 30), L≈141.421
3. (230, 30) → (230, 150), L=120
4. (170, 90) → (290, 90), L=120
5. (330, 40) → (390, 40), L=60
6. (360, 10) → (360, 40), L=30

Первые две линии образуют X; третья и четвёртая пересекаются как крест; последние две образуют отдельный T-узел: вертикальный stroke заканчивается в точке пересечения с горизонтальным. ROI не должны пересекать границы доски.

| Профиль | CHALK estimate |
|---|---:|
| P0 | 193.71 |
| P1 | 100.08 |
| P2 | 100.05 |

### D4 — короткие детали

Шесть изолированных strokes точной длины 1/2/3/5/8/10 logical px:

1. (30, 30) → (31, 30), L=1
2. (60, 30) → (60, 32), L=2
3. (90, 30) → (93, 30), L=3
4. (130, 30) → (130, 35), L=5
5. (170, 30) → (178, 30), L=8
6. (210, 30) → (210, 40), L=10

Направления чередуются между горизонталью и вертикалью; ROI разнесены и не должны сливаться.

Использовать lookup без интерполяции.

| Профиль | CHALK estimate |
|---|---:|
| P0 | 20.01 |
| P1 | 15.00 |
| P2 | 15.34 |

### D5 — повторное покрытие

Три отдельных прямых strokes, каждый выполняется дважды по точно той же траектории:

- (40, 40) → (90, 40), L=50;
- (40, 90) → (140, 90), L=100;
- (40, 150) → (160, 150), L=120.

Итого шесть stroke executions. Повторный проход учитывается как полноценный stroke, а не как бесплатное покрытие.

| Профиль | CHALK estimate |
|---|---:|
| P0 | 171.94 |
| P1 | 89.24 |
| P2 | 89.18 |

## 4. Матрица выполнения

- 5 DrawingPlan × 3 профиля × 3 независимых повтора = **45 live captures**.
- P0 — контроль; P1/P2 — кандидаты.
- Внутри сравнения одного DrawingPlan геометрия, radius, transform и порядок strokes должны быть одинаковыми.
- Для сопоставимости с предыдущими V-сериями первый проход выполнять при radius=10.
- Остальные executor parameters фиксировать по действующему протоколу INT-006.
- Порядок профилей/планов рандомизировать с фиксированным seed и сохранить его.
- Перед каждым run проверять пустую доску и точное исходное значение pointCount.

## 5. Неизменяемая запись прогноза

До live execution сохранить отдельный prediction record для каждого плана и профиля:

- model_id / version / coefficients;
- plan_id и geometry signature;
- список stroke IDs и их длины;
- применённое правило: linear formula или exact short lookup;
- per-stroke predictions и общий prediction;
- executor profile, radius и transform contract;
- timestamp и hash исходного DrawingPlan.

После начала серии прогнозы не редактировать. Если обнаружена ошибка в модели, завершить текущую серию как есть, сохранить ошибку и создать новую версию модели для отдельной будущей серии.

## 6. Capture acceptance

Run включается в validation только при выполнении всех условий:

1. Executor завершил все запланированные strokes.
2. До и после исполнения получены точные целочисленные pointCount.
3. `post.pointCount >= pre.pointCount`, delta положительна.
4. Сумма per-stroke pointDelta совпадает с exact CHALK delta.
5. Monitor report однозначно связан с experiment/run/plan/profile.
6. dropped_events, monitor_error_count_delta, bridge_send_failures_delta и collector_sequence_gap_count равны нулю.
7. Фактический radius равен 10; transform и executor parameters соответствуют плану.
8. PNG сохранены, курсор не закрывает ROI.
9. Число и порядок strokes совпадают с DrawingPlan.

Invalid capture не включать в метрики; повтор выполнять отдельным attempt, исходный manifest не переписывать.

## 7. Метрики

Для каждого run и каждого DrawingPlan:

- actual CHALK;
- predicted CHALK;
- residual = actual − predicted;
- absolute error;
- relative error;
- error by stroke and by geometry family.

Итоговые метрики отдельно для P0/P1/P2 и D1–D5:

- MAE;
- RMSE;
- mean bias (actual − predicted; положительное значение означает недооценку расхода);
- MAPE, если actual не близок к нулю;
- max absolute error;
- max positive residual (максимальная недооценка);
- разброс трёх повторов.

Не объединять P0/P1/P2 в один коэффициент. Не объединять короткий lookup с линейным сегментом без явного разбиения.

## 8. Решение по safety margin

Не назначать произвольный процент. Сначала рассчитать положительные residuals и разброс повторов по каждому профилю и типу плана.

Максимальная наблюдённая недооценка может быть только provisional empirical guard для этой выборки, а не статистической гарантией. При малом числе независимых DrawingPlan нельзя заявлять универсальный 95%-й safety margin. Для production допуска потребуется расширенная проверка на реальных рисунках, включая классы геометрии, которые не покрыты D1–D5.

Если профиль систематически недооценивает CHALK, имеет нестабильную ошибку или не покрывает тип геометрии — результат UNKNOWN/NOT VALIDATED; INT-007 не начинать.

## 9. Что не входит в эту серию

- Заливка областей и произвольные кривые: текущая модель не задаёт подтверждённого прогноза.
- Изменение размера кисти: все планы этой серии используют radius=10.
- Оптимизация порядка штрихов и траекторий: относится к INT-008 после validation.
- Изменение production estimator/defaults: запрещено до закрытия INT-006.

## 10. Критерий завершения

INT-006 можно закрыть только после:
- принятия всех валидных captures;
- расчёта метрик по каждому профилю и семейству геометрии;
- фиксации областей применимости и UNKNOWN-классов;
- обоснования safety margin с явным указанием ограничений выборки;
- синхронизации PROJECT_STATUS, TASKS, ROADMAP, WORK_LOG и отчёта модели.

До этого INT-007 остаётся BLOCKED, production estimator не меняется.


## 11. Текущий статус запуска

- [x] Реализовать отдельную INT006 phase в matrix metadata, block planner/journal, Brush Test UI и executor handoff.
- [x] Подготовить 15 immutable prediction records (D1–D5 × P0/P1/P2), связать их с 45 задачами журнала и manifest metadata.
- [x] Добавить analyzer exact capture matching, journal-attempt binding, per-run/per-stroke residuals и error metrics.
- [x] Добавить regression tests на artifact integrity, 45 cells, geometry binding и executor handoff.
- [x] Пройти полный CI [41513389663](https://github.com/Kiddos19882/AutoDraw/actions/runs/41513389663): 667 passed, 82 subtests passed; pixel audit и Windows portable build/startup smoke-test success.
- [ ] Выполнить локальный Windows 10 preflight по [инструкции](CHALK_INT006_LOCAL_PREFLIGHT_GUIDE_2026-11-02.md).
- [ ] Только после preflight и явного подтверждения чистой доски начать 45 live captures.

До завершения локального preflight не запускать полный INT006 block и не запускать D1–D5 через существующие V-фазы или вручную. Production estimator/defaults остаются неизменными.


## 12. Software gate закрыт — 2026-11-02

Кодовый commit `ca8c9b3bd739ea0a5b557b87fc0106ecfde81216` прошёл полный workflow [41513389663](https://github.com/Kiddos19882/AutoDraw/actions/runs/41513389663): Preparation/G3 — 667 passed и 82 subtests passed; Application integration, Executor regression, Game Monitor/bridge, INT-006 pixel audit и Windows portable build/startup smoke-test — success. Portable artifact: `autodraw-g3-preflight-build`.

D1–D5 harness, frozen predictions и analyzer реализованы. Следующий шаг — локальный Windows preflight. 45 live captures не начинать до проверки preflight и подтверждения чистой доски/точного CHALK baseline.


## Актуальный результат live блока — 2026-11-03

D1–D5 выполнены в block `chalk-20261102-232320-7cea27`: 45/45 tasks completed, radius=10. Предварительный разбор 45 manifests и 45 Monitor reports подтвердил exact CHALK, совпадение per-stroke sum, ожидаемое число штрихов и нулевые per-run Monitor/Bridge integrity counters.

Предварительные метрики и ограничения вынесены в [CHALK_INT006_VALIDATION_PRELIMINARY_RESULTS_2026-11-03.md](CHALK_INT006_VALIDATION_PRELIMINARY_RESULTS_2026-11-03.md). Эти расчёты не заменяют штатный analyzer: до получения официального JSON report серия не считается количественно validated, safety margin не установлен, INT-007 остаётся BLOCKED.

Workflow `.github/workflows/geometry-tests.yml` дополнен запуском analyzer и загрузкой report artifact. Для поддержки переноса Windows capture bundle в CI analyzer связывает journal attempt с уникальным именем experiment directory, а не с исходным абсолютным путём.

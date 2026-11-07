# INT-006 — протокол калибровки и независимой проверки политики CHALK 95%

**Дата:** 2026-11-07  
**Статус:** PROPOSED / OFFLINE DESIGN COMPLETE — captures не запускались  
**Решение пользователя:** целевое одностороннее предиктивное покрытие 95% подтверждено  
**Базовая модель:** `chalk-int006-frozen-2026-11-02`, version 1  
**Фиксированный radius:** 10  
**Профили:** P0 (step=2, delay=10 ms), P1 (step=4, delay=5 ms), P2 (step=4, delay=10 ms)  
**Зависимость:** [проект политики safety margin](CHALK_SAFETY_MARGIN_POLICY_DESIGN_2026-11-07.md)

## 1. Что именно означает цель 95%

Цель — **одностороннее предиктивное покрытие не менее 95% для нового DrawingPlan**, выбранного из той же заранее определённой целевой совокупности поддерживаемых планов, что и calibration/holdout. Для каждого такого плана верхняя оценка CHALK должна быть не ниже фактического расхода как минимум в 95% случаев в долгосрочном повторении этой процедуры.

Это не:
- 95% confidence, что формула универсальна;
- гарантия для любого произвольного рисунка;
- гарантия для неподдерживаемой геометрии, другого radius или профиля;
- 95% шанс, что любой конкретный рисунок не превысит игровой quota;
- доказательство production eligibility.

Статистическое обоснование требует независимых plan IDs и exchangeability внутри каждой заранее определённой группы `profile × geometry_domain`. Повторы одного DrawingPlan не считаются независимыми планами.

## 2. Область первой проверки

Первая серия ограничена текущей проверенной областью INT-006:
- radius=10;
- профили P0/P1/P2 с неизменными sampling settings;
- новые, не совпадающие с D1–D5 по идентификатору и frozen geometry signature DrawingPlan;
- только планы из line-based domain, представленного INT-006: mixed straight lines, polygon/straight contour segments, intersections, short details с поддержанным lookup и repeated straight-stroke coverage;
- short lookup только для logical lengths 1/2/3/5/8/10; остальные прямые длины — только в пределах существующего frozen predictor;
- curves, fills, неизвестные длины/классы, radius ≠10 и неподдержанные профили остаются `UNKNOWN`.

Пять семейств geometry — это strata для представления целевой совокупности, а не пять отдельных статистических гарантий. 95% claim первой серии относится к заранее зафиксированной смеси этих пяти семейств. Для отдельного 95% утверждения по каждому семейству потребуются отдельные выборки и расчёт объёма для каждой группы.

## 3. Независимая единица и размер выборки

Единица статистического наблюдения — **уникальный DrawingPlan ID**, а не stroke row, capture repeat или отдельный штрих. Один plan ID, исполненный по P0/P1/P2, даёт по одному связанному наблюдению для каждого профиля; внутри каждого profile набор plan IDs должен быть независимым.

Для каждой группы `profile × geometry_domain`:

| Набор | Независимые DrawingPlan IDs | Назначение |
|---|---:|---|
| Calibration | 19 | Вычислить односторонний 95%-й split-conformal квантиль |
| Holdout | 59 | Независимо проверить целевой риск превышения |
| **Всего** | **78** | Новые уникальные планы на domain |

Для одной первой geometry domain и трёх профилей это означает:
- 78 уникальных DrawingPlan IDs;
- каждый план исполняется по одному разу на каждом из трёх профилей;
- 234 плановых captures всего: 57 calibration + 177 holdout;
- повторные captures для диагностики не увеличивают число независимых DrawingPlan.

**Почему 19 calibration:** для split-conformal upper quantile при `α=0.05` используется ранг `k = ceil((n+1) × 0.95)`. При n=19 получаем k=19 — максимальное значение calibration sample и конечный ранг. Это минимальный размер, при котором такой distribution-free односторонний 95%-й ранг конечен. Это не означает, что 19 достаточно для любого domain или для оценки всех подгрупп.

**Почему 59 holdout:** заранее фиксируется строгий acceptance rule — ноль превышений среди 59 независимых holdout plan IDs в каждой группе profile/domain. При 0 failures из 59 односторонняя точная 95%-я верхняя граница Clopper–Pearson для вероятности превышения равна `1 − 0.05^(1/59)` (примерно 4.95%). Следовательно, при предположении независимой репрезентативной выборки можно отвергнуть гипотезу, что вероятность превышения составляет 5% или больше, на одностороннем уровне значимости 5%.

Это отдельное утверждение о риске, а не то же самое, что conformal marginal coverage. Любое превышение в holdout означает FAIL по заранее принятому строгому критерию; holdout нельзя использовать для подбора нового квантиля.

Для каждого дополнительного geometry domain требуется собственная группа из 19 calibration + 59 holdout DrawingPlan на каждый профиль. Нельзя объединять разные domains ради уменьшения выборки без отдельного обоснования exchangeability.

## 4. Состав DrawingPlan и распределение N

До генерации и просмотра результатов необходимо:
1. Определить целевую совокупность реальных планов AutoDraw и диапазон числа штрихов `N_min…N_max`, который требуется поддерживать.
2. Зафиксировать границы трёх диапазонов N (низкий / средний / высокий) до создания выборки. Границы должны происходить из ожидаемого рабочего диапазона планов, а не подбираться по полученному CHALK.
3. Сформировать планы с разными N, длинами, направлениями, плотностью пересечений и долей повторного покрытия.
4. Сбалансировать представление пяти line-based семейств и трёх N strata настолько, насколько позволяет размер набора; при 78 планах это 15 сочетаний family × N band, примерно 5–6 планов на сочетание.
5. Сохранить неизменные исходные изображения/геометрию, canonical plan hash, geometry family, N, stroke lengths, frozen per-stroke predictions и версию преобразования.
6. Не включать D1–D5 повторно в число независимых новых планов. Их можно использовать только как исторический benchmark.

N определяется как число отдельных запланированных stroke executions, для которых frozen predictor выдаёт `p_i`. N не равен числу точек, sampling events, пикселей, длине пути или количеству сегментов внутри одного stroke. Перекрывающиеся отдельные исполнения остаются отдельными stroke operations.

Границы N и состав выборки пока **не могут быть выражены конкретными числовыми порогами**: в доступном официальном INT-006 отчёте нет подтверждённого целевого распределения N для production DrawingPlans. Их необходимо извлечь из заранее выбранной совокупности рабочих планов и заморозить до формирования calibration/holdout. До этого диапазон применимости по N не утверждён; вне зафиксированного диапазона — `UNKNOWN`.

N bands используются для проверки, не ухудшается ли residual при росте плана. 95% claim не распространяется отдельно на каждый band: для этого потребуются 59 независимых holdout plans без превышений в каждом band/profile/domain.

## 5. Разделение и защита holdout

- Сначала сформировать полный список уникальных планов и canonical hashes.
- До вычисления прогнозов назначить plan IDs в calibration или holdout с воспроизводимым seed/правилом стратифицированного распределения.
- Не допускать одинаковых изображений, геометрий, копий или производных вариантов одного шаблона одновременно в calibration и holdout.
- Связанные/производные варианты считать одной группой и помещать только в один split.
- Calibration и holdout должны иметь заранее заданное распределение geometry families и N bands.
- Holdout labels (actual CHALK) не раскрывать до фиксации quantile, формулы, model version и acceptance criteria.
- Никакой пересчёт quantile, изменение N bands, исключение неудобных plan IDs или изменение acceptance thresholds после просмотра holdout не допускается.
- Любая смена frozen model, predictor, executor semantics, radius, profile settings или domain требует новой policy version и независимой validation.

## 6. Формулы и оценка

Для каждого плана и профиля:
`P = Σ p_i`, где `p_i` — frozen prediction каждого stroke execution.

После live capture фактический расход:
`CHALK_actual = pointCount_after − pointCount_before`.

Run-level residual:
`E = CHALK_actual − P`.

Нормированная положительная недооценка:
`U = max(0, E) / N`.

Для каждой группы profile/domain отдельно сортировать calibration values:
`U_(1) ≤ … ≤ U_(19)`.

Для одностороннего split-conformal уровня 95%:
`k = ceil((n+1) × 0.95) = 19`; `q_0.95 = U_(19)`.

Кандидатный резерв для нового плана:
`M(N, profile, domain) = ceil(N × q_0.95)`.

Требуемый ресурс:
`CHALK_required = ceil(P + M)`.

Это проверяемая линейная гипотеза масштабирования по N. Holdout должен проверить её на низких, средних и высоких N. Если coverage зависит от N, family или другой заранее известной переменной, текущая объединённая policy считается FAIL; требуется новая версия с заранее специфицированной стратификацией/моделью и новой независимой validation. Нельзя подгонять решение на holdout.

## 7. Capture protocol и integrity gates

Каждый capture обязан иметь:
- уникальные plan/task/run/experiment IDs и связь с calibration/holdout split;
- frozen model ID/version, prediction artifact hash и prediction IDs;
- profile settings P0/P1/P2, radius=10, executor config и transform snapshot;
- неизменный DrawingPlan hash, N и geometry classification;
- exact `pointCount_before` и `pointCount_after`;
- Monitor report, stroke-level breakdown, исходный manifest и PNG/evidence;
- нулевые dropped events, Bridge send failures, Monitor errors и sequence gaps;
- совпадение `pointCount_after − pointCount_before` с суммой принятых point deltas;
- завершение всех запланированных strokes и отсутствие неоднозначного run binding.

Capture с нарушением целостности отклоняется до анализа CHALK. Сохраняются rejected record и причина. Технически невалидный capture не считается независимым наблюдением; повтор допускается только с новым attempt ID по заранее установленному правилу, без удаления исходной попытки и без выбора результата по величине CHALK. Каждый новый plan ID должен оставаться независимым.

Параметры среды и порядок профилей рандомизировать или балансировать. Перед каждым capture — чистая доска и проверка начального pointCount. Если невозможно гарантировать сопоставимость, серия блокируется.

## 8. Заранее зафиксированные acceptance criteria

**Calibration readiness**
- 19/19 уникальных независимых plan IDs для каждой profile/domain группы;
- все capture integrity gates пройдены;
- нет дубликатов или пересечения зависимых plan families между splits;
- все три N bands и пять geometry families представлены;
- predictor и все thresholds frozen до holdout.

**Holdout PASS**
- 59/59 уникальных независимых holdout plan IDs на каждую profile/domain группу;
- 0 превышений: для каждого плана `CHALK_actual ≤ CHALK_required`;
- exact CHALK и полная provenance на каждом capture;
- нет незапланированных исключений, подмен или post-hoc пересмотра критериев;
- отсутствует заранее определённый domain drift и нет диагностического признака систематического ухудшения по N/family.

Любое превышение, пропуск/повреждение, неподдержанный geometry class, выход за N range или существенный drift — FAIL/UNKNOWN, а не успешная оценка по среднему. Если требуется иной acceptance rule (например, разрешить одно превышение), объём выборки и биномиальный критерий должны быть рассчитаны и утверждены **до** новых данных.

## 9. Что не входит в этот протокол

- Curves, fills, arbitrary freehand paths и неподдержанные длины.
- Другие радиусы кисти.
- Новые sampling profiles или изменённые executor settings.
- Доказательство экономии CHALK от изменения радиуса.
- FILL-001 PNG coverage/leakage gate.
- Производственная интеграция в AutoDraw и изменение production defaults.

FILL-001 PNG gate остаётся самостоятельным блокером. Даже успешный holdout для текущего line-based domain не закрывает FILL-001 и не разрешает INT-007 автоматически.

## 10. Статус, разрешения и следующие шаги

Сейчас выполнено только офлайн-проектирование. Новые DrawingPlan не сформированы, capture не запускались, CHALK не измерялся. Пользователь подтвердил целевое покрытие 95%, но это не является разрешением на live-эксперименты.

Последовательность:
1. Извлечь из целевой совокупности AutoDraw ожидаемый диапазон N и заморозить три N bands.
2. Подготовить 78 новых уникальных plan IDs и проверить отсутствие leakage между splits.
3. Заморозить manifest, prediction artifact, split assignment, protocol version и analyzer criteria.
4. Отдельно получить разрешение пользователя на live captures; до него не запускать локальную игру/доску.
5. После сбора выполнить независимый анализ calibration, зафиксировать quantile, затем открыть holdout только для единственной confirmatory проверки.
6. При PASS вынести отдельное решение о production eligibility; не включать estimator автоматически.

До завершения validation сохраняются:
- `safety_margin_status=not_established`;
- `production_eligibility=not_validated`;
- INT-007 — BLOCKED;
- production estimator/defaults не меняются.

## Источники

- [INT-006 official validation results](CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md).
- [INT-006 frozen predictions and analyzer](CHALK_INT006_FROZEN_PREDICTIONS_AND_ANALYZER_2026-11-02.md).
- [Проект политики безопасного запаса CHALK](CHALK_SAFETY_MARGIN_POLICY_DESIGN_2026-11-07.md).
- [Стандарт экспериментов](EXPERIMENT_STANDARD.md).

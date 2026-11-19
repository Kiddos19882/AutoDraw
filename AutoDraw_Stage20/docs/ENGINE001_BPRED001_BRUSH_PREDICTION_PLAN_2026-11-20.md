# ENGINE-001 / BPRED-001 — прогноз фактического следа кисти Egret/Canvas2D/WebGL

**Дата принятия плана:** 2026-11-20. **Решение:** [DEC-041](DECISIONS.md). **Статус:** ACCEPTED PLAN / DOCUMENTATION ONLY. Этапы BPRED ещё НЕ реализованы; E1 — анализ исходников и предыдущих результатов, E2/E3/E4/E5 по BPRED **NOT_RUN**. Это рабочий план и требования к будущим отдельным экспериментам, **не** prereg конкретного статистического теста; перед каждым native-экспериментом замораживать отдельный E0, выборку и численные критерии.

## 1. Цель, baseline и область

Создать экспериментальный **Brush Prediction Engine (BPE)**, который по реальному исходному штриху (ширина 1..10, points, colorIndex/colorRgb), текущему состоянию доски RGBA и версии Egret/Canvas/масштаба предсказывает **физический RGBA-отпечаток** и изменение итогового изображения, выявляет риски неправильного owner-цвета и защищённых областей. Использовать прогноз сначала как дешёвый отбор и оценку кандидатов, затем как основу перестройки всей последовательности штрихов из original RGB source. Цель — **улучшить первоначальный план**, а не делать неограниченное число width1 «заплаток». Никаких обещаний pixel-exact без native evidence.

- **Remote baseline при принятии:** ветка `feature/image-geometry-optimization`, SHA `ba0f609ab15e982e37ddece674fee3809890dce9`. Источник оригинала `testImages/wV6VeZI9S1Y.png`, SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`. Активны B1-R original-source E=`E_SOBEL90`, F=`F_SOBEL90_LAB12`, исходная `C_192_D_COMPONENT24`, палитра 128 игровых owners; `G32` и `V44` только история/контроль, никогда генеративный вход.
- **Native reference:** настоящий Egret 5.4.1 BoardPane, Firefox159.0 (закреплён), original game blob `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`, renderer blob `76d950e0a8911888a9df3b675b866519ecf7bba4`. Source physical backing scale3, canvas1380×720 и исходная 150×240 logical source ROI в BoardPane с X0=155 **относятся только к текущему E/F test harness**, а не к любой другой игре/экрану.
- **Исходный benchmark:** исходные `P4D13` и последний `P4D18` archived plans/native RGBA. [P4D17/P4D18 результаты](ENGINE001_B1R_P4D17_P4D18_NATIVE_FULL_REPAINT_RESULTS_2026-11-19.md): interior alpha0 E95→24, F96→25; nonwhite owner 5/9 E13868/13868, F13863/13863, но исходно-белая окраска E4415/F4445 physical alpha24 и protected white E2250/F2261, **FULL QUALITY FAIL**. P4D18 имеет 6619/6641 strokes (НЕ CHALK).
- **Сохранённый исследовательский протокол:** [P4D19 E0](ENGINE001_B1R_P4D19_NATIVE_OWNER_RGBA_ATTRIBUTION_PREREG_2026-11-20.md) зафиксирован на SHA `3ff24b0f`, E2/E3 NOT_RUN; **DEFERRED как самостоятельное восстановление отдельных пикселей**, не удалён и не отменён задним числом. Его per-owner/prefix/ablation при необходимости использовать только как диагностические приемы внутри BPRED с новым E0, не объявляя P4D19 выполненным.

## 2. Уже подтверждённые и неподтверждённые свойства

| Evidence | Что подтверждено | Что НЕ доказано |
|---|---|---|
| P4D3/P4D4 | Повтор одинаковой native сцены480/480 RGBA exact; перенос отпечатка на другое место лишь292/480, затем256/480 exact | Универсальная геометрическая маска по переносу |
| [P4D14 E3](https://github.com/Kiddos19882/AutoDraw/actions/runs/44553609729) | Egret CanvasRenderer сдвигает widths1,3 на (+0.5,+0.5) logical; centroid MAE для них0.711337→0.037627 | Точный физический alpha/RGB footprint |
| [P4D15 E3](https://github.com/Kiddos19882/AutoDraw/actions/runs/44560216224) | Для30 фиксированных случаев исходный Canvas2D crop и конечный WebGL RGBA byte-exact после известного offset6 physical; spatial mismatch был уже на Canvas2D | Любая версия браузера/движка или иной scene совпадёт |
| [P4D16 E3](https://github.com/Kiddos19882/AutoDraw/actions/runs/44568765466) | Модель площади с субпиксельной дискретизацией — полезная геометрическая аппроксимация | Pixel-exact прогноз/zero false-safe на независимом holdout |
| P4D13/P4D18 | 5/9 logical gate пропускает физические alpha0; увеличенное число маленьких штрихов частично улучшает physical owner coverage | Что уже решены foreign/protected gates или сокращён CHALK |

Исходный порядок слоёв: stroke-пути Egret → Canvas2D raster/AA → текстура/WebGL → композиция цветов. Геометрическая капсула — лишь дешевый кандидатный фильтр, не оракул безопасности. Прогнозировать следует и **контекстное смешивание**, не только одиночный круг.

## 3. Контракт экспериментального предсказателя

**Вход:** версия pinned engine + renderer/browser, координатные преобразования logical/client/backing, шрифт здесь не нужен; `strokes[]` (точные points/width1..10/owner-RGB/order), текущее RGBA либо blank, original source owner-index/RGB и protected mask. Все входы имеют SHA и frame/ROI binding; неизвестный масштаб, непривязанное состояние или рассогласование исходников — fail-closed.

**Выход на уровне физического backing пикселя:** predicted alpha[0..255], RGB/composited RGBA, ROI bbox, вероятность или калиброванный диапазон ошибки (не притворяться статистическим confidence без независимой проверки), `new_correct`, `lost_correct`, `foreign_damage`, `white_spill`, `protected_damage`, `uncertainty`, `status=MODEL_ONLY|NATIVE_VALIDATED|UNKNOWN`. Идентичный input обязан давать идентичный результат. Отдельно считать counts logical 5/9,7/9,9/9, а не скрывать девять backing px одним булевым значением. Начальные scoring alpha≥24, max-channel RGB difference≤32 — **только исторический benchmark**, не новая production-граница.

**Правило безопасности:** `UNKNOWN` и false-safe-risk на критических границах требуют настоящего native replay; предсказание не даёт автоматическое разрешение executor. Предсказанное количество strokes/длина/точек ≠ exact game CHALK.

## 4. Порядок этапов и выходные gates

| ID | Задача и методы | Критерий завершения / следующий gate |
|---|---|---|
| **BPRED-S0** | Аудит и фиксация первичных исходников, native sample corpus и реального пути Canvas/WebGL; P4D3/4/14/15/16, frozen E/F; отдельно составить train/calibration/held-out разбиение **до** настройки | Есть source/build/engine/browser SHA, raw PNG hashes, данные для каждой width1..10; выявлены неизвестные и ограничения; никакой модельный PASS вместо Egret |
| **BPRED-S1** | Source-faithful геометрия: координаты logical→Canvas→backing, width1/3 +.5, cap/join/изломы, bounds/ceil/clip, scale, fractional phase; **M0** naive cap vs **M1** source-derived geometry | Фиксированный API и тесты математических инвариантов/трансформаций, native single-stroke comparisons с новым E0; все несоответствия сохранять |
| **BPRED-S2** | Физическая растеризация: предсказание alpha0..255 через площадь пересечения/субпиксельную интеграцию (reuse P4D16 `area8`), затем **M2** residual/phase correction только на calibration sample. Координатная абсолютная фаза обязательна | Сравнение M0/M1/M2 по width1..10, углам, длинам, старт/концу/повороту, позициям и фазам; alpha1/alpha24 IoU, FP/FN, MAE и калиброванная неопределенность на holdout |
| **BPRED-S3** | Реальная композиция: source-over alpha/RGB, порядок слоёв, цветовая палитра, overlap/AA и повреждение 1→0; вычисление full-scene по incremental ROI | Native-сравнение blank, двухцветных/многоцветных пересечений и меняющегося порядка, не только отдельных штрихов; per-owner false-safe и source-white measured |
| **BPRED-S4** | Независимая validation: неизвестные в calibration координаты/фазы, критические source E/F границы, случайные и удержанные trajectories, полный replay; native Egret единственный кистевой oracle | Отчёт false-safe отдельно от среднего IoU; модельная неопределенность и native fallback позволяют **не принимать** неподтвержденные защищённые штрихи; скорость и память измерены |
| **BPRED-S5** | Experimental adaptive planner: global original-owner coverage, комбинации widths1..10, направления 360°, порядок цветов; выбираем кандидаты по `new_correct`, `lost_correct`, protected/white/foreign и latency; native validate full plans | Новые E/F с реальным Egret; сравнение с сохранёнными P4D13/P4D18 по coverage, leakage, contours, face/eyes/hands, длительности, strokes; все действующие quality gates должны выполняться; никакой production promotion по модели |
| **BPRED-S6** | После достижения quality gates: минимизация количества/длины/сложности штрихов и переключений цветов; удаление избыточных, merging, переупорядочивание только если финальная RGBA-прогноз/Native сохраняет качество | Объективное улучшение без регрессии accepted native image; exact CHALK только после отдельного E4 run-bound сравнения; E5 независимая validation перед production |

**Первый реальный невыполненный шаг:** `BPRED-S0` — подготовить короткий отдельный **E0 prereg** инвентаризации и независимого корпуса, затем с отдельным разрешением на разработку/тестирование реализовать reuse-first harness и E2/E3. Этапы не считаются завершёнными без соответствующей проверки на конкретном SHA.

## 5. Независимый тестовый корпус и метрики

Тесты должны покрывать все widths1..10, точки, короткие/длинные H/V/diag/произвольные углы, поворот/стык, integer translation, fractional phase, границу доски, узкие зоны, соседние разные owners, original-white и protected face/eyes/hands. Включить отдельные контрольные blank и exact replay. Разделять единицы train/test **по целой scene/trajectory/позиционной группе**, чтобы десять переносов одной линии не попадали одновременно в tune и holdout. Никакого изменения критериев после просмотра результатов; численные исследовательские пороги задавать в самостоятельном E0 перед запуском.

Регистрировать: `alphaMAE`, `RGB-MAE`, alpha1/alpha24 `IoU`, `FP/FN`, физический `correct-owner`, white/protected/foreign false-safe и false-unsafe, качество abstention/uncertainty, время predictor и native per-call, peak memory, count strokes, lengths, переключения цветов. Accuracy на одном browser/scale не обобщать на другой renderer/version.

**Оптимизатор выбирает лексикографически:** (1) нарушение frozen safety/quality gates — **недопустимо**; (2) больше правильного original-owner покрытия и узнаваемость; (3) меньше риска/неопределённости; (4) меньше цены исполнения. Не заменять всё одним взвешенным баллом, позволяющим «купить» порчу лица за сокращение штрихов. При unknown блокировать предложение или re-evaluate native, не выдавать false PASS.

## 6. Reuse-first: где лежит существующая реализация

- (п) `source/preparation/`: (ф) [brush_footprint_geometry.py](../source/preparation/brush_footprint_geometry.py) — исходная математическая маска, **не native**; (ф) [interior_fill_planner.py](../source/preparation/interior_fill_planner.py), (ф) [outline_first_fill_planner.py](../source/preparation/outline_first_fill_planner.py) — потенциальные потребители только после проверки API/owners и отдельного production решения.
- (п) `tests/`: (ф) [game_renderer_reference.js](../tests/game_renderer_reference.js) — исходный native oracle; (ф) [run_engine001_b1r_p4d14_egret_halfpixel_centroid.py](../tests/run_engine001_b1r_p4d14_egret_halfpixel_centroid.py) — центр; (ф) [engine001_p4d15_intermediate_capture.js](../tests/engine001_p4d15_intermediate_capture.js) — Canvas intermediate; (ф) [run_engine001_b1r_p4d16_canvas_aa_density.py](../tests/run_engine001_b1r_p4d16_canvas_aa_density.py) — area8 / alpha metrics; (ф) [run_engine001_b1r_p4d17_owner_physical_repair.py](../tests/run_engine001_b1r_p4d17_owner_physical_repair.py) — score; (ф) [run_engine001_b1r_p4b7_native_stroke_attribution.py](../tests/run_engine001_b1r_p4b7_native_stroke_attribution.py) — session/attribution, color115-specific paths нельзя автоматически обобщать.
- Для экспериментов преимущественно расширять имеющийся harness/CI с frozen reference; **не** создавать вторые независимые рендереры, source maps или планировщики без доказанной необходимости. Сначала проверить точные потребители на текущем remote SHA и regression implications.

## 7. Качество, evidence, ограничения разрешения

Полный E/F **protected quality FAIL** на P4D18 сохраняется до нового E3. Действующие boundaries (включая предел leakage 3 logical px, protected foreign0, original owner ≥99%, критические детали, сам оригинал) не ослаблять. `E0` — заранее записанный эксперимент, `E1` — анализ, `E2` — unit, `E3` — pinned CI/native Egret, `E4` — реальный game runtime/Monitor/Bridge, `E5` — независимая validation. Ни `CI SUCCESS`, ни `pixel-model IoU` не доказывают игру. Exact CHALK = `post.pointCount-pre.pointCount` **только** при валидном run binding. Исходные captures и frozen протоколы не перезаписывать; для каждого нового опыта experiment/run/session ID, config, SHA, full raw RGBA PNG, JSON, hashes, rejected cases и архив.

**Настоящее разрешение пользователя — только документирование этого плана.** Код, тесты, CI workflows и production пока НЕ меняются и вручную НЕ запускаются. `master` не изменять, live доступ к пользовательскому ПК не предполагать. Изменения внедрять лишь в пределах нового явного разрешения, без переписывания P4D19/P4D13–18 как PASS.

## 8. Связанные первичные решения/регламент

[DECISIONS](DECISIONS.md), [TASKS](TASKS.md), [ROADMAP](ROADMAP.md), [PROJECT_STATUS](PROJECT_STATUS.md), [GAME_BRUSH_FOOTPRINT_TEST_POLICY](GAME_BRUSH_FOOTPRINT_TEST_POLICY_2026-11-15.md), [ENGINEERING_INVARIANTS](ENGINEERING_INVARIANTS.md), [EVIDENCE_AND_VALIDATION](EVIDENCE_AND_VALIDATION.md), [EXPERIMENT_STANDARD](EXPERIMENT_STANDARD.md), [TEST_RESULTS](TEST_RESULTS.md).

# INT-006 — отдельные live-серии V2 и V5 (follow-up)

**Дата подготовки:** 2026-11-02  
**Ветка:** `feature/image-geometry-optimization`  
**Статус:** READY_FOR_USER_LIVE_RUN  
**Назначение:** отдельные новые серии; исходные V1–V5 captures не изменяются и не переиспользуются.

## 1. Общий контракт обеих серий

- Радиус кисти: **10** (запрошенный и наблюдаемый через Game Monitor).
- Профили: P0 = `point_step_px=2 / point_delay_ms=10`; P1 = `4 / 5`; P2 = `4 / 10`.
- Три повтора на каждый профиль.
- Каждая фаза формирует отдельный block journal: 3 профиля × 3 повтора = **9 live captures**.
- Все остальные параметры executor остаются штатными: `line_extension=0`, `before_mouse_down=20 ms`, `after_mouse_down=40 ms`, `after_mouse_up=20 ms`, `end_hold=50 ms`, `countdown=5 sec`.
- Внутри каждой ячейки геометрия, порядок штрихов, transform, размер доски и радиус идентичны; меняется только sampling profile.
- Использовать новые уникальные `series_id` и новые block journals. Не продолжать старые V2/V5 journals и не перезаписывать manifests/reports/PNG.
- Live execution выполняет пользователь в подготовленной игровой сессии. CI проверяет код/контракты, но не запускает игру.

## 2. V2 follow-up — короткие штрихи 12–30 logical px

**Scenario ID:** `int006_short_strokes_followup`  
**Ожидаемых штрихов на capture:** 5  
**Объём:** 9 captures × 5 strokes = 45 per-stroke observations.

| Штрих | Координаты DrawingPlan (logical 460×240) | Длина | Направление |
|---|---|---:|---|
| `length_12_horizontal` | (25,35) → (37,35) | 12 | горизонталь |
| `length_16_vertical` | (90,72) → (90,88) | 16 | вертикаль |
| `length_20_diagonal` | (150,110) → (162,126) | 20 | диагональ 12×16 |
| `length_24_horizontal` | (250,170) → (274,170) | 24 | горизонталь |
| `length_30_vertical` | (370,195) → (370,225) | 30 | вертикаль |

### Цели и измерения

1. Определить, при какой длине path-level PNG metrics становятся пригодны при radius=10.
2. Проверить, где короткий след ещё выглядит как footprint/spot, а где проявляется различимая центральная линия.
3. Для каждого stroke сопоставить planned length, визуальный результат и exact per-stroke `pointDelta`.
4. Сравнить exact CHALK по P0/P1/P2 для каждой длины отдельно; не объединять разные длины в одну среднюю.
5. Оценить стартовую стоимость короткого stroke отдельно от стоимости добавочной длины. Не применять к этим наблюдениям линейную модель длинных штрихов как критерий ожидаемого CHALK.

**Важно:** 12–30 px — это follow-up диапазон, выбранный после того, как прежние 1–8 px проходили pixel path sufficiency, а прежние 10 px не проходили. Это не означает заранее, что все новые длины станут измеримыми.

## 3. V5 follow-up — spacing sweep 8/12/16/20/24 logical px

**Scenario ID:** `int006_intersections_spacing_sweep`  
**Ожидаемых штрихов на capture:** 16  
**Объём:** 9 captures × 16 strokes = 144 per-stroke observations.

Первые шесть штрихов сохраняют контрольные узлы геометрии:
- X-пересечение: 2 штриха;
- T-пересечение: 2 штриха;
- крестовое пересечение: 2 штриха.

Пять пар параллельных линий размещены в отдельных горизонтальных ROI, по одной паре на каждый spacing:

| Пара | Координаты первой линии | Координаты второй линии | Межосевое расстояние |
|---|---|---|---:|
| `parallel_s08` | (20,186) → (95,186) | (20,194) → (95,194) | 8 |
| `parallel_s12` | (105,184) → (180,184) | (105,196) → (180,196) | 12 |
| `parallel_s16` | (190,182) → (265,182) | (190,198) → (265,198) | 16 |
| `parallel_s20` | (275,180) → (350,180) | (275,200) → (350,200) | 20 |
| `parallel_s24` | (360,178) → (435,178) | (360,202) → (435,202) | 24 |

### Цели и измерения

1. Найти переход между слиянием/касанием и устойчиво раздельными следами.
2. Проверить, сохраняется ли предыдущий результат о слиянии около 8 logical px и разделении около 24 logical px.
3. Для каждой пары измерить межосевое расстояние, минимальное расстояние между ink masks, overlap/merge, ширину каждой линии и стабильность по повторам.
4. Узлы X/T/креста оценивать отдельно от параллельных пар.
5. Сопоставить per-stroke `pointDelta` обеих линий пары и exact CHALK всей серии. Не интерпретировать суммарный расход как доказательство разделения следов.
6. Не выводить универсальный safe spacing только из номинального radius: учитывать measured mask width, image scale, фактический визуальный контакт и разброс повторов.

Пары находятся в раздельных X-диапазонах, чтобы соседние тестовые пары не пересекались. Координаты находятся внутри logical board 460×240.

## 4. Приёмка live capture

Capture включается в анализ только если одновременно выполнено:

- executor завершил задачу, `completed_strokes` совпадает с 5 (V2) или 16 (V5);
- доступны exact pre/post `pointCount`, `post >= pre`, `chalk_actual = post - pre > 0`;
- сумма per-stroke `DRAW_SAMPLE.pointDelta` совпадает с exact CHALK, если используется per-stroke разбор;
- Game Monitor capture сохранён и связан с experiment/run;
- observed radius единственный и равен 10;
- per-run `dropped_events=0`, `monitor_error_count_delta=0`, `bridge_send_failures_delta=0`, `collector_sequence_gap_count=0`;
- transform и все executor параметры соответствуют плану;
- before/after PNG и blank/reference capture сохранены.

При нарушении gate run INVALID; повтор выполняется новой attempt после проверки доски. Невалидные данные не включать в коэффициенты. Cumulative local Monitor buffer overflow сам по себе не является per-run loss.

## 5. Порядок выполнения пользователем

1. Обновить AutoDraw из ветки `feature/image-geometry-optimization` до коммита, содержащего эти follow-up планы и тесты.
2. Проверить калибровку, board ROI, Game Monitor heartbeat, slider и чистую доску.
3. В Brush Test выбрать V2 follow-up и выполнить полный block 9/9. Дождаться завершения каждого capture; не очищать доску вручную до штатного перехода.
4. После завершения V2 проверить итоговый статус блока и сохранность 9 manifests/reports/capture sets.
5. Подготовить чистую доску и выполнить отдельный V5 follow-up block 9/9.
6. Передать сохранённые block journals, manifests, Game Monitor reports и PNG artifacts для анализа. Не переименовывать файлы и не редактировать JSON вручную.

Рекомендуется выполнять серии раздельно, начиная с V2. Если live-сессия прерывается, не запускать повторно поверх неизвестного состояния доски: сначала выполнить штатный recovery/board check.

## 6. Что будет рассчитано после получения данных

- exact CHALK по каждому run и per-stroke `pointDelta`;
- P0/P1/P2 delta и относительная экономия отдельно для каждой длины V2 и каждого spacing V5;
- CHALK на logical px только как вспомогательная метрика, отдельно от стартовой стоимости stroke;
- V2 path sufficiency, coverage, centerline/width metrics и spot-vs-line classification с явными ограничениями;
- V5 overlap, min ink-mask distance, measured width, merge classification и repeatability;
- invalid/ambiguous capture audit и итоговые допустимые области применения sampling profiles.

**Никакие live-результаты не предполагаются заранее.** Production executor, estimator и sampling defaults не меняются по факту подготовки этих серий.


## 7. Фактическое выполнение follow-up — 2026-11-02

V2 и V5 live blocks выполнены пользователем и сохранены в commit [e879a77](https://github.com/Kiddos19882/AutoDraw/commit/e879a77f63be7a7a68de3f09091eab7dba0d34a2): обе серии завершены 9/9. В составе общего follow-up V1–V5 проверены все 45 captures, exact CHALK и per-run Monitor integrity. Полные raw repeat values и выводы: [CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md](CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md).

V2 step=4 дал около 38.5–39.3% экономии против step=2. V5 дал около 46.9–47.0%. Все runs проведены при radius=10; выводов о влиянии радиуса эта серия не даёт. Pixel-level аудит новых PNG выполнен в CI `41496555297`: V2 45/45 strokes sufficient, coverage=1.0 и zero gaps; V5 144/144 strokes sufficient, coverage=1.0 и zero gaps. Целевые V5 пары с separation 8/12 logical px merge 9/9, с 16/20/24 px — 0/9 при radius=10. Production defaults не менялись.

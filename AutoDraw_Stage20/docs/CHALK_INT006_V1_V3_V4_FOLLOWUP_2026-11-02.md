# INT-006 — повторные live-серии V1, V3 и V4

**Дата подготовки:** 2026-11-02  
**Ветка:** `feature/image-geometry-optimization`  
**Статус:** READY_FOR_USER_LIVE_RUN  
**Назначение:** проверить исправленные DrawingPlan V1/V3 и cursor-free capture V4 на новых данных; исходные 45 captures не изменяются и не переиспользуются.

## 1. Общий контракт

- Радиус кисти: **10**, запрошенный и наблюдаемый Game Monitor.
- Профили: P0 = `point_step_px=2 / point_delay_ms=10`; P1 = `4 / 5`; P2 = `4 / 10`.
- Для каждой фазы — три повтора на профиль: **9 captures на фазу**.
- Каждая фаза запускается отдельным block journal и отдельным новым `series_id`.
- Объём: V1 — 9 captures × 6 strokes = 54 observations; V3 — 9 × 3 = 27; V4 — 9 × 3 = 27. Всего **27 captures и 108 per-stroke observations**.
- Остальные параметры executor должны оставаться штатными: `line_extension=0`, `before_mouse_down=20 ms`, `after_mouse_down=40 ms`, `after_mouse_up=20 ms`, `end_hold=50 ms`, `countdown=5 sec`.
- Не продолжать старые journals, не повторно использовать прежние `series_id`, не переписывать исходные manifests/reports/PNG.
- Live-прогоны выполняются в подготовленной игровой сессии. CI подтверждает программные контракты, но не заменяет live-проверку.

## 2. V1 — диагонали исправленной геометрии

**Phase:** `V1`  
**Scenario ID:** `int006_diagonals`  
**Expected strokes:** 6  
**Профили/повторы:** P0/P1/P2 × 3 = 9 captures.

В текущем `brush_behavior_test_ui.py` используется исправленный DrawingPlan из шести диагоналей:

| Штрих | Координаты logical 460×240 |
|---|---|
| `slope_025` | (20,25) → (180,65) |
| `slope_050` | (220,20) → (340,80) |
| `slope_100` | (20,100) → (100,180) |
| `slope_200` | (140,100) → (180,180) |
| `negative_shallow` | (220,170) → (380,130) |
| `negative_steep` | (410,60) → (400,220) |

Цель — подтвердить на новых captures, что исправленные траектории не пересекаются непреднамеренно и допускают раздельную оценку centerline, coverage и gap. Старые captures с прежней геометрией не объединять с этой серией.

## 3. V3 — исправленные непрерывные повороты

**Phase:** `V3`  
**Scenario ID:** `int006_turns`  
**Expected strokes:** 3  
**Профили/повторы:** P0/P1/P2 × 3 = 9 captures.

Текущий DrawingPlan содержит три непрерывные полилинии:

| Штрих | Координаты logical 460×240 |
|---|---|
| `right_angle` | (20,20) → (180,20) → (180,100) → (360,100) |
| `acute_zigzag` | (20,140) → (60,80) → (100,140) → (140,80) → (160,140) |
| `multi_turn` | (20,210) → (90,170) → (160,210) → (230,170) → (300,210) → (420,170) |

Цель — подтвердить отсутствие прежнего непреднамеренного пересечения между разными штрихами, оценить сохранение вершин/углов и локальное отклонение на поворотах. Не восстанавливать исходные вершины по Game Monitor trajectory: использовать плановую геометрию.

## 4. V4 — замкнутые контуры с cursor-free capture

**Phase:** `V4`  
**Scenario ID:** `int006_closed_contours`  
**Expected strokes:** 3  
**Профили/повторы:** P0/P1/P2 × 3 = 9 captures.

DrawingPlan:

| Контур | Координаты logical 460×240 |
|---|---|
| `rectangle` | (20,20) → (180,20) → (180,100) → (20,100) → (20,20) |
| `triangle` | (260,20) → (420,120) → (180,120) → (260,20) |
| `irregular_polygon` | (250,150) → (390,150) → (420,220) → (300,220) → (220,190) → (250,150) |

Для автоматического post-draw capture код выполняет mouseUp, перемещает отпущенный курсор за пределы calibrated board ROI и только затем снимает PNG. Перемещение курсора относится только к автоматическому post-draw capture; ручной capture не изменён.

Цель — повторно измерить closure seam и проверить, что область последнего endpoint не перекрыта курсором. Если курсор обнаружен в ROI либо endpoint закрыт неоднозначными пикселями, соответствующая метрика помечается ambiguous; не считать её успешной только по отсутствию gap в остальной части контура.

## 5. Критерии приёмки каждого capture

Capture включается в анализ только если одновременно выполнено:

- executor status = completed; `completed_strokes` равно 6 (V1) или 3 (V3/V4);
- exact pre/post `pointCount` доступны, `post >= pre`, `chalk_actual = post - pre > 0`;
- сумма per-stroke `DRAW_SAMPLE.pointDelta` совпадает с exact CHALK, если используется per-stroke разбор;
- Game Monitor report сохранён и однозначно связан с experiment/run;
- observed brush radius единственный и равен 10;
- per-run `dropped_events=0`, `monitor_error_count_delta=0`, `bridge_send_failures_delta=0`, `collector_sequence_gap_count=0`;
- transform и executor parameters совпадают с планом;
- сохранены before/after PNG, manifest и monitor report.

При нарушении любого gate run помечается INVALID; повторять его только новой attempt после штатной проверки состояния доски. Не включать невалидный run в коэффициенты. Cumulative local Monitor buffer overflow сам по себе не является per-run loss.

## 6. Порядок запуска

1. Обновить приложение из `feature/image-geometry-optimization` до актуального commit, содержащего code HEAD `3e8e6c5` и последующие документационные коммиты.
2. Проверить calibration, board ROI, Game Monitor heartbeat, slider и чистую тестовую доску.
3. Для V1 задать новый уникальный `series_id`, выбрать фазу V1 и выполнить полный block 9/9.
4. Проверить completed status и наличие 9 manifests/reports/capture sets. Затем подготовить чистую доску.
5. Повторить отдельно для V3 с новым `series_id`, затем отдельно для V4 с новым `series_id`.
6. Не запускать следующую фазу поверх неизвестного состояния доски. При interruption выполнить штатный recovery/board check.
7. Передать все три journals, manifests, Game Monitor reports и PNG без переименования и ручного редактирования.

## 7. Анализ после получения данных

- P0/P1/P2 exact CHALK и per-stroke deltas отдельно для каждого штриха;
- V1: gap, centerline deviation, coverage width/variation и число компонентов маски;
- V3: метрики прямых сегментов отдельно от окрестностей поворотов, corner deviation и непрерывность;
- V4: closure seam, cursor exclusion/ambiguity и coverage каждого контура;
- сравнение повторов и разбор INVALID/ambiguous captures;
- сопоставление с исходной серией только как отдельное сравнение «до/после исправления», не как единая обучающая выборка.

**Не предполагается заранее, что step=4 проходит геометрический gate.** Pixel metrics остаются диагностикой изображения; exact CHALK берётся только из игрового `post.pointCount - pre.pointCount`. Production executor, estimator и sampling defaults не менять по факту подготовки этих серий.

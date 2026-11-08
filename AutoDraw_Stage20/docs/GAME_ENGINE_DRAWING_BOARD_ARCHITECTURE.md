# Игровой движок Egret 5.4.1: устройство доски рисования

**Область:** технический разбор сохранённой версии игрового движка; центральный объект — `com.magnetjoy.pet.ui.board.BoardPane`. **Задача:** `ENGINE-001`. **Проверенная ветка:** `feature/image-geometry-optimization`, исходный remote HEAD `768ece83f129d28278dc771ab4ff0726e0748cb4`, дата 2026-11-08.

**Статус:** `E1 PARTIAL` — статический разбор ключевых путей и сверка ранее зафиксированного анализа; `E2/E3` — ранее выполненные unit/browser/paired-renderer проверки в указанной области. **Не является:** аудитом всего игрового приложения, утверждением о текущей версии сайта, новой игровой сессией, доказательством pixel-equivalence FILL-001 или измерением CHALK новых алгоритмов.

Этот документ систематизирует прежде разрозненные факты **без замены** первичного [подробного исследования движка](CHALK_GAME_ENGINE_POINT_COST_AND_BRUSH_WIDTH_2026-11-03.md) и [технической справки Game Monitor](GAME_MONITOR_BRIDGE_REFERENCE.md). Перед новым экспериментом сверять код, SHA и его run-bound данные.

## 1. Сохранённые исходники и границы изученного

| Узел | Исходник / доказательство | Подтверждение |
|---|---|---|
| Комплект приложения | [`gameEngine/manifest.json`](../gameEngine/manifest.json) | В `game` перечислены `js/mergeEngine_df2e5bc5.js` и `js/main.min_653f95bc.js`; `initial=[]` |
| Игровая логика | [`main.min_653f95bc.js`](../gameEngine/main.min_653f95bc.js), blob `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`, 4 859 418 байт в Git tree | `BoardPane`, `BlackBoardAtom`, `Painter`, `PainterPopup` — ранее извлечены и проанализированы в разделах 11–15 основного отчёта |
| Движок рендера | [`mergeEngine_df2e5bc5.js`](../gameEngine/mergeEngine_df2e5bc5.js), blob `d613d2b97e2436521aa3870478c69e99eac1f19f`, 877 537 байт в Git tree | В текущем просмотре кода подтверждены `GraphicsNode.lineStyle`, `CanvasRenderer.renderGraphics`, `Path2D.drawRoundRect`, `WebTouchHandler.getLocation`, `SystemTicker.broadcastEnterFrame`; Egret 5.4.1 |
| Runtime-снимок | [`renderer_snapshot_2026-11-04.json`](../data/runtime/renderer_snapshot_2026-11-04.json) | Конкретная пользовательская сессия: `renderMode=webgl`, stage 1672×600, `frameRate=30`, board 460×240, backing 5016×1800 |
| Реальные игровые точки | [`endpoint-analysis-6a17a297.json`](../data/results/brush_behavior_tests/fill001/endpoint-analysis-6a17a297.json) и сохранённый Monitor run, указанный в нём | 27 штрихов, 1260 сохранённых точек, точный CHALK 1260; координаты восстановлены из raw events |
| Браузерный воспроизводитель | [`tests/game_renderer_reference.html`](../tests/game_renderer_reference.html), [`game_renderer_reference.js`](../tests/game_renderer_reference.js), [tests](../tests/game_renderer_reference.test.js) | Рисует через реальный `BoardPane.redraw`, `CanvasRenderer` и `WebGLRenderer`, но не выполняет реальный игровой input |

Ограничение настоящей сверки: `mergeEngine` прочитан непосредственно, а `main.min` слишком велик для текущего текстового извлечения через GitHub connector. Факты о его минифицированных методах получены из ранее задокументированного анализа **того же Git blob**, плюс проверяемого браузерного harness, а не из нового полного посимвольного аудита `main.min`. Неподтверждённые детали прямо помечены ниже.

## 2. Где начинается рисование: объекты приложения

Рабочая доска создаётся в `PainterPopup.createBlackBoard()` как `PainterPopup.painterBoard` — экземпляр `BoardPane`. Его логический размер **460×240**, а доступный лимит точек передаётся из `blackBoard.maxPoint`. В конструкторе `BoardPane` существует fallback лимита 2000, но рабочая всплывающая доска получает значение объекта; например, в снимке 04.11 фактический лимит был 6000. Не считать 6000 универсальной константой.

Параллельно в клиенте существует preview-экземпляр `BoardPane` в `BoardItemBase.createNativeContent()` с `interactive=false`. Он отображает рисунок как часть интерфейса, но не равен интерактивной доске popup. В текущем сохранённом пользовательском сценарии одна пустая тестовая доска, поэтому историческая неоднозначность автообнаружения отмечена [DEC-022](DECISIONS.md), но не объявляется текущим блокером. В иных комнатах нельзя выбирать произвольный первый `BoardPane` без проверки идентичности.

**Данные рисунка** содержит `BlackBoardAtom`: параллельные коллекции `points`, `radius`, `colors` и `options` описывают геометрию, толщину, цвет и режим сглаживания каждого штриха. `atom.add()` завершает текущий штрих; `clear()` переинициализирует данные. В расширенном режиме `_isPainterExtend` очистка может оставить служебную начальную точку `(0,0)`. Поэтому **нулевой рисунок не обязательно имеет абсолютный `pointCount=0`**; сравнивать нужно pre/post снимки одной валидной сессии.

Границы ответственности:
- `PainterPopup` — UI, создание и настройка рабочей доски, цвет/размер/режим, popup-маска.
- `BoardPane` — события рисования, сбор точек, квота, `redraw()`, локальный `scrollRect`.
- `BlackBoardAtom` — сохранённые точки и атрибуты штрихов; удаление соседних одинаковых координат.
- `Painter` — превращение массива точек в Graphics path.
- Egret `GraphicsNode`/`CanvasRenderer`/`WebGLRenderer` — построение и пиксельная растеризация с применением масок и stage-transform.
- AutoDraw Stage6 executor — внешний генератор мыши, **не** владелец принятых игрой точек.

## 3. Жизненный цикл одного штриха

Ниже реконструкция пути для интерактивного `PainterPopup.painterBoard` из главного бандла и engine source:

```text
Мышь AutoDraw/человека
  -> DOM mousedown / mousemove / mouseup на canvas
  -> Egret WebTouchHandler.getLocation: browser page/client -> stage, Math.round
  -> Egret TouchHandler -> stage.mouseX/Y, BoardPane event
  -> BoardPane.onMouseDown / onDrawStart:
       globalToLocal(stage.mouseX/Y) -> atom.pushPoint(P0) -> updateLess()
       подписка на ENTER_FRAME
  -> для каждого выбранного Egret ENTER_FRAME:
       BoardPane.onDrawing
       -> прочесть текущие stage.mouseX/Y
       -> globalToLocal
       -> проверить попадание в 0..width × 0..height
       -> atom.pushPoint(Pi) [отбросить дубль]
       -> updateLess() -> redraw(false)
  -> BoardPane.onDrawingEnd:
       отписаться от ENTER_FRAME -> redraw(false) -> atom.add()
  -> готовый штрих в BlackBoardAtom
```

Факты и ограничения:
1. `WebTouchHandler.getLocation` делит DOM page offsets относительно `canvas.getBoundingClientRect()` на текущие `scaleX/scaleY`, учитывает rotation 90/-90 и округляет `Math.round()` до stage coordinates. Затем `globalToLocal()` даёт координаты доски. Это **не** прямая запись экранных пикселей.
2. `SystemTicker` вызывает `broadcastEnterFrame()` по frame scheduling, но каждая команда `pyautogui.moveTo` не гарантирует отдельный Egret ENTER_FRAME. `TouchHandler` также подавляет повторяющиеся stage coordinates.
3. `BlackBoardAtom.pushPoint()` сохраняет первую координату или координату, отличную от последней по `Point.equals()`; повтор не тратит дополнительный CHALK.
4. `onDrawingEnd()` **не** делает отдельное финальное чтение мыши на mouseup. Конечная позиция указателя не обязана стать последней принятой точкой.
5. Ранее в live FILL-001 наблюдались 41–48 принятых точек на каждый из 27 штрихов; median временного интервала между принятыми точками ~33 ms. Браузерный RAF ~60 FPS не доказывает частоту Egret ENTER_FRAME. Значение stage.frameRate=30 подтверждено лишь для указанного runtime snapshot.
6. `updateLess()` в самом игровом коде повторно считает все сохранённые точки — потенциально O(N) на принятие. Снижение FPS из-за этого **не доказано** для FILL-001.

## 4. Счётчик CHALK и лимит доски

В `BoardPane.updateLess()` вычисляется:

```text
pointCount = сумма длин всех сохранённых массивов atom.points
less = max - pointCount
CHALK одного валидного запуска = post.pointCount - pre.pointCount
```

Затем публикуется `BlackBoardEvent.CHALK` с остатком/процентом. `BoardPane.setRadius(value)` присваивает толщину текущему штриху, не прибавляя автоматически ни единицы к pointCount. Размер кисти, площадь окрашенных пикселей, число штрихов и длина пути сами по себе **не** являются точным CHALK.

[Game Monitor](GAME_MONITOR_BRIDGE_REFERENCE.md) читает `BoardPane.max` и `BoardPane.less`: `pointCount=max-less` только при валидации точных целочисленных полей. Это O(1) snapshot без обхода `atom.points`; `diagnosticSnapshot()` может пересчитать массив отдельно. При значимых опытах требуются run/session identity, pre/post, отсутствие критических потерь телеметрии.

Пример: FILL-001-RS run `6a17a297-ea14-4527-9527-bfd8de3bd335` — `pointCount 1→1261`, значит **CHALK=1260**. Этот пример не устанавливает стоимость нового контура, адаптивной кисти или другого плана.

## 5. Как сохранённые точки превращаются в линию

Для каждого сохранённого штриха `BoardPane.redraw()` передаёт в `graphics.lineStyle(value, color, 1, false)` его `radius`/`color`, затем выбирает функцию `Painter` по `atom.options`.

**Критично: игровое название `radius` передаётся в Egret как `lineWidth`, не как математический радиус круга.** При значении 10 номинальная толщина stroke равна 10 логическим единицам; нельзя молча брать радиус 10 и диаметр 20. Фактические пиксели зависят от antialiasing и browser renderer.

| Режим | Команды | Конечная геометрия |
|---|---|---|
| `normal` | `moveTo(P0)`, затем `lineTo(P1)...` | Центр линии достигает последней принятой точки |
| `smooth`, актуальный вызов `BoardPane.redraw()` | Два `moveTo(P0)`, `lineTo(mid(P0,P1))`, далее `curveTo(Pi, mid(Pi,Pi+1))` | `Painter.drawSmoothLine(..., true, false)` **не** делает заключительный `lineTo(P_last)`; путь заканчивается на midpoint последней пары |
| Одна сохранённая точка | `moveTo` без drawable-сегмента | PointCount может возрасти, хотя видимого пятна нет; точный эффект проверять в конкретном renderer |

Для `smooth` с двумя точками путь заканчивается посередине отрезка, а с тремя и более — на midpoint последней пары; округлый cap может выступать дальше. В 27 сохранённых штрихах последний интервал не превышал 9 логических единиц при `lineWidth=10`; идеальный cap достигает центра последней принятой точки. Поэтому **заданный drawLast=false сам по себе ещё не объясняет 1116 пропущенных экранных пикселей**.

В `mergeEngine` подтверждено:
- `GraphicsNode.lineStyle` заменяет неподдерживаемые/непереданные значения `caps` и `joints` на `round`.
- `CanvasRenderer.renderGraphics` передаёт `lineWidth`, `lineCap`, `lineJoin` и строит `quadraticCurveTo/lineTo`; вызывает `stroke()`.
- Для толщины ровно 1 или 3 `CanvasRenderer` дополнительно временно сдвигает Canvas2D context на `(0.5,0.5)` — важно при тестах маленькой кисти.
- Для реального `GraphicsNode` raster может включать антиалиасинг, premultiplied alpha и фильтрацию WebGL; идеальная капсула OpenCV не равна пиксельному результату Egret.

## 6. Доска, clipping и фон

В `PainterPopup` рабочая доска имеет локальные размеры 460×240. `BoardPane.resetBg()` устанавливает прямоугольный `scrollRect=(0,0,460,240)`. Дополнительно `PainterPopup.createBlackBackground()` создаёт `egret.Shape` с `drawRoundRect(0,0,460,240,10)` и назначает этот Shape как `painterBoard.mask`.

В сохранённом Egret `Path2D.drawRoundRect` внутренний радиус угла вычисляется из половины `ellipseWidth` (для аргумента 10 — **5 logical px**, с целочисленной операцией в реализации). Это отдельная геометрия маски; она **не** определяет толщину кисти. Комбинация `scrollRect`, roundRect mask, WebGL stencil/filtering и дробной позиции на stage влияет на крайние пиксели.

Для текущего набора бандлов:
1. `egret.sys.setRenderMode("webgl")` при доступном WebGL выбирает `WebGLRenderer`; иначе есть Canvas fallback.
2. `WebGLRenderer` для `GraphicsNode` готовит CanvasRenderBuffer и вызывает `CanvasRenderer.renderGraphics`, затем загружает bitmap в WebGL texture.
3. Для сохранённого случая используются WebGL-режим, LINEAR texture filtering и маска объекта; браузерная композиция и физические пиксели зависят от transform.

**Не путать:** clipping ограничивает рисование видимой доской, но не доказывает отсутствие утечек относительно *целевой маски фигуры FILL-001* внутри доски. Это разные границы.

## 7. Пять пространств координат и частая ошибка

| Пространство | Пример | Для чего |
|---|---|---|
| `logical_board_pixels` | 460×240 | Исходный FILL-001 mask/plan, координаты `BoardPane` |
| `Egret stage` | 1672×600 в одном snapshot | `stage.mouseX/Y` и stage display matrix |
| `backing canvas` | 5016×1800, масштаб ×3 для того snapshot | Внутренний растр движка и WebGL RenderBuffer |
| `client/CSS` | canvas rect 1920×690 в одном snapshot | Browser `getBoundingClientRect()`, CSS transform |
| `desktop/screen PNG ROI` | FILL-001 581×304, origin (566,253) | Наблюдаемый screenshot и координаты внешнего исполнителя |

Текущий AutoDraw [`brush_coordinate_transform.py`](../source/preparation/brush_coordinate_transform.py) преобразует **логические координатные границы** в центры крайних пикселей ROI:

```text
scale_x = (screen_roi.width - 1) / 460
scale_y = (screen_roi.height - 1) / 240
x_roi = x_board * scale_x
y_roi = y_board * scale_y
x_screen = roi.x + x_roi
y_screen = roi.y + y_roi
```

Это контракт **конкретного плана и affine screenshot audit**, а не универсальная физическая матрица всех renderer layers. Допускается относительное отличие масштабов X/Y не более 1%; иначе transform отклоняется. Нельзя вместо этого подставлять `ROI.width/460` или использовать простой `PIL.resize`: в FILL-001 уже была подтверждённая ошибка несогласованного boundary mapping.

В snapshot 04.11 stage origin BoardPane равен примерно `(519.791666,72)` при stage scale 1; браузерный `canvasScaleX/Y=3` не тождествен `canvasScaleFactor=2`. Конкретные коэффициенты нельзя применять для другого browser/session без новой same-run калибровки. Для старого FILL-001-RS capture точная **run-bound** renderer geometry отсутствует, хотя screenshot ROI известен.

## 8. Что делает AutoDraw, а что — игра

[`source/executor/drawing/mouse_executor.py`](../source/executor/drawing/mouse_executor.py) использует `point_step_px` и `point_delay_ms` для движения указателя; нажатие/отпускание контролирует executor. Это лишь **план доставленного ввода**. Внутри игры отдельны этапы: DOM event delivery → округление stage → sampling `ENTER_FRAME` → `pushPoint` → midpoint/curve path → rasterization → CSS/screen composition.

Поэтому фиксировать отдельно:
- логические точки плана и калибровку;
- OS/DOM moves, если есть соответствующая телеметрия;
- `MOUSE_MOVE_SAMPLE` в Game Monitor (доставленные canvas DOM events; не все OS commands);
- `POINT_QUOTA_UPDATE.acceptedPoint` и точный `pointDelta`;
- точный pre/post CHALK и `strokeId`;
- снимки before/after PNG, текущий renderer/transform, пороги diff.

Отсутствующие intermediate coordinates при `pointDelta>1` нельзя догадкой заполнять. Нельзя превращать estimated sampling points в CHALK.

## 9. Уже существующий симулятор — что ему доверять

В [браузерном reference harness](../tests/game_renderer_reference.js) два согласованных пути:
- настоящий `BoardPane.atom.points/radius/colors/options` → `BoardPane.redraw()` → actual Egret Canvas/WebGL raster;
- ручная транскрипция `Painter` → сравнение с настоящим `BoardPane` попиксельно.

Поддерживаются синтетические cases, smooth/normal, mask corner, scrollRect, размеры линий 10/30, а также replay **одного** подтверждённого run/stroke из Game Monitor и Stage A–D display variants. Для paired replay инструмент требует неизменный `renderer_geometry_at_start/end` того же run; подмена чужим старым snapshot запрещена.

**Ранее проверено:**
- [CI 42427514794](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794), browser job SUCCESS: 20 fixtures/20 WebGL comparisons/60 PNG; это прогон сохранённого движка, не игры на сайте.
- [PRR 42321009715](https://github.com/Kiddos19882/AutoDraw/actions/runs/42321009715): 6/6 формально принятых single-stroke vertical/diagonal paired runs; IoU примерно 0.938–0.952 по порогам PRR, **не** pixel-identical renderer и **не** гарантия FILL-001 coverage ≥99% с leakage=0.
- `OpenCV` [FILL-001 A–D](../source/preparation/chalk_fill_strategy_comparison.py) и [screen-ROI overlays](../source/preparation/chalk_fill_screen_residual_comparison.py) — быстрые surrogate rasters; **не** actual Egret raster. Исходный FILL-001 live PNG остаётся REJECTED: coverage 98.430600%, leakage 11.

### Применимость для последующей оптимизации заливки (НЕ ТЕКУЩАЯ РАБОТА)

После завершения ENGINE-001 использовать существующий harness, а не создавать новый параллельный симулятор:

1. В отдельной версии эксперимента подать **все 27 отдельных accepted-point массивов** прежнего FILL-001 run в `BoardPane.atom.points` с сохранением порядка, `radius/colors/options` и frozen hashes. Текущий вход live-replay рассчитан на **один** stroke и требует расширения; это не выполнено.
2. Получить Canvas, WebGL masked board и Stage-level PNG. Для старого run с недостающим same-run renderer snapshot пометить screen projection как `UNCALIBRATED`, не подменять её геометрией другого run.
3. Сравнить model/render ↔ game PNG по одному и тому же ROI, цветовой нормализации, порогам и screen transform; особенно 738 model-only pixels и 11 leakage. Не объявлять новые игровые пиксели измеренными.
4. Только после этого вернуться к вариантам E: адаптивный offset, переменная толщина и локальные коррекции. Не заменять исходные raw captures и не подменять CHALK симуляцией.

## 10. Реестр открытых технических вопросов ENGINE-001

| Вопрос | Текущее состояние | Чем закрывать |
|---|---|---|
| Полный обзор всех подсистем `main.min` вне доски | `PARTIAL`: прямой полный re-read bundle в этом проходе недоступен; профильная декомпозиция BoardPane/Painter подтверждена прежним static audit | Инвентаризация остальных классов по точному blob, без догадок об их обязанностях |
| Более точная структура `BlackBoardAtom`: `add/clear` и индексы параллельных массивов | E1 по прежнему разбору, специальных новых тестов не было | Таблица состояний на класс/методы, исходный bundle и соответствующие unit fixtures |
| Точный порядок `TouchHandler`/Egret `ENTER_FRAME` при разных mouse timings | Static model E1; 30Hz наблюдался только в отдельных runs | Парная DOM/accepted-point telemetry при той же сессии, если будет отдельное разрешение |
| Screen transform старого 27-stroke FILL-001 run | `PARTIAL`: calibrated ROI есть, same-run geometry snapshot отсутствует | Не переносить чужую матрицу; потребуются сопоставимые геометрические evidence и независимая проверка |
| Результат actual Egret для 27-stroke FILL-001 | `NOT_RUN` | Перенести multi-stroke case в существующий reference harness, с корректными отказами |
| Точная raster-equivalence на острых углах, малых толщинах и цветах | `UNKNOWN` вне проверенных PRR single-stroke cases | Дополнительные frozen fixtures + независимый PNG audit |
| Природа 11 FILL-001 leakage и 738 model-only screen pixels | `UNKNOWN`; model mismatch установлен, причина — нет | Вначале разбор реального footprint/endpoint, затем отдельная экспериментальная проверка |
| Подтверждение совпадения сохранённого bundle с **сегодняшним** сайтом | `UNKNOWN`: у нас есть только ранее подтверждённая копия сайта | Новая runtime/network provenance при отдельном live-доступе |

**Статусы:** `E1` — исходники/статический разбор; `E2` — проверка кода в тестах; `E3` — GitHub Actions на заданном commit; `E4` — реальная игровая сессия; `E5` — независимая validation. `PASS` для одного уровня не переносится автоматически на следующий.

## 11. Инженерные ограничения и связанные документы

- Не менять `master`, production `Stage6`, legacy planners, frozen CHALK estimator, Monitor/Bridge и capture datasets без отдельного разрешённого этапа. Текущая работа — **документация**.
- [ENGINEERING_INVARIANTS.md](ENGINEERING_INVARIANTS.md), [EVIDENCE_AND_VALIDATION.md](EVIDENCE_AND_VALIDATION.md), [EXPERIMENT_STANDARD.md](EXPERIMENT_STANDARD.md) — обязательные протоколы.
- [CHALK_GAME_ENGINE_POINT_COST_AND_BRUSH_WIDTH_2026-11-03.md](CHALK_GAME_ENGINE_POINT_COST_AND_BRUSH_WIDTH_2026-11-03.md) — первичная подробная история static/live/PRR reverse engineering; не переписывать старые выводы.
- [GAME_MONITOR_BRIDGE_REFERENCE.md](GAME_MONITOR_BRIDGE_REFERENCE.md) — API и форма telemetry.
- [CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md](CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md) — исходный REJECTED PNG evidence.
- [TEST_RESULTS.md](TEST_RESULTS.md) — актуальный индекс measured/CI evidence.
- [TASKS.md](TASKS.md) и [ROADMAP.md](ROADMAP.md) — текущая `ENGINE-001` и **отложенный** backlog экспериментов с заливкой.

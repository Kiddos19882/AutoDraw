# Игровой движок Egret 5.4.1: устройство доски рисования

**Область:** технический разбор сохранённой версии игрового движка; центральный объект — `com.magnetjoy.pet.ui.board.BoardPane`. **Задача:** `ENGINE-001`. **Проверенная ветка:** `feature/image-geometry-optimization`, исходный remote HEAD `768ece83f129d28278dc771ab4ff0726e0748cb4`, дата 2026-11-08.

**Статус:** `ENGINE-001 PARTIAL`; `E1 PASS` для непосредственно проверенных методов `BlackBoardAtom/BoardPane/Painter/PainterPopup/Atom` и Egret Graphics, но не всего игрового клиента. `E2/E3` — ранее выполненные unit/browser/paired-renderer проверки в их заявленной области. **Не является:** аудитом всего игрового приложения, утверждением о текущей версии сайта, новой игровой сессией, доказательством pixel-equivalence FILL-001 или измерением CHALK новых алгоритмов.

Этот документ систематизирует прежде разрозненные факты **без замены** первичного [подробного исследования движка](CHALK_GAME_ENGINE_POINT_COST_AND_BRUSH_WIDTH_2026-11-03.md) и [технической справки Game Monitor](GAME_MONITOR_BRIDGE_REFERENCE.md). Перед новым экспериментом сверять код, SHA и его run-bound данные.

## 1. Сохранённые исходники и границы изученного

| Узел | Исходник / доказательство | Подтверждение |
|---|---|---|
| Комплект приложения | [`gameEngine/manifest.json`](../gameEngine/manifest.json) | В `game` перечислены `js/mergeEngine_df2e5bc5.js` и `js/main.min_653f95bc.js`; `initial=[]` |
| Игровая логика | [`main.min_653f95bc.js`](../gameEngine/main.min_653f95bc.js), blob `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`, 4 859 418 байт в Git tree | `BoardPane`, `BlackBoardAtom`, `Painter`, `PainterPopup`, `Atom` и настройки popup непосредственно сверены по полному Git blob; таблица методов — §12 |
| Движок рендера | [`mergeEngine_df2e5bc5.js`](../gameEngine/mergeEngine_df2e5bc5.js), blob `d613d2b97e2436521aa3870478c69e99eac1f19f`, 877 537 байт в Git tree | В текущем просмотре кода подтверждены `GraphicsNode.lineStyle`, `CanvasRenderer.renderGraphics`, `Path2D.drawRoundRect`, `WebTouchHandler.getLocation`, `SystemTicker.broadcastEnterFrame`; Egret 5.4.1 |
| Runtime-снимок | [`renderer_snapshot_2026-11-04.json`](../data/runtime/renderer_snapshot_2026-11-04.json) | Конкретная пользовательская сессия: `renderMode=webgl`, stage 1672×600, `frameRate=30`, board 460×240, backing 5016×1800 |
| Реальные игровые точки | [`endpoint-analysis-6a17a297.json`](../data/results/brush_behavior_tests/fill001/endpoint-analysis-6a17a297.json) и сохранённый Monitor run, указанный в нём | 27 штрихов, 1260 сохранённых точек, точный CHALK 1260; координаты восстановлены из raw events |
| Браузерный воспроизводитель | [`tests/game_renderer_reference.html`](../tests/game_renderer_reference.html), [`game_renderer_reference.js`](../tests/game_renderer_reference.js), [tests](../tests/game_renderer_reference.test.js) | Рисует через реальный `BoardPane.redraw`, `CanvasRenderer` и `WebGLRenderer`, но не выполняет реальный игровой input |

**Прямая проверка 2026-11-08:** первоначальный `fetch_file` не прочитал большой `main.min`, но `fetch_blob` по точному SHA вернул **4 857 523 символа / 4 859 418 UTF-8 байт**; вычисленный SHA-1 Git blob совпал с `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`. Тела профильных методов изучены непосредственно. Это устраняет прежнее ограничение чтения **для данных методов**, но не равнозначно анализу всех прочих классов клиента и не доказывает сегодняшнюю runtime-версию сайта.

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
| Полный обзор всех подсистем `main.min` вне доски | `PARTIAL`: blob целиком получен и проверен, но классы **вне доски** не инвентаризированы | При необходимости дополнить профильный перечень классов с доказуемыми связями |
| `BlackBoardAtom`: `add/clear/undo`, serializer, слоты штрихов | `E1 PASS` по полному blob; таблица состояний и бинарный формат в §12 | Отдельные edge-case E2/E4 tests не запускались |
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

## 12. Прямой аудит полного main bundle: методы, состояния, сериализация (2026-11-08)

**E1 direct source:** [`gameEngine/main.min_653f95bc.js`](../gameEngine/main.min_653f95bc.js), Git blob `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`, **4 859 418 байт**. Через GitHub blob получено 4 857 523 символа; независимо рассчитанный Git blob SHA-1 совпал с исходным. Также прочитан [`mergeEngine_df2e5bc5.js`](../gameEngine/mergeEngine_df2e5bc5.js), blob `d613d2b97e2436521aa3870478c69e99eac1f19f`. Сведения ниже относятся к этим точным файлам: **E1 подтверждает реализацию, но не сегодняшнюю версию игры и не E4 runtime**.

### 12.1. Карта классов и методов доски

| Объект | Прямо проверенные члены | Роль |
|---|---|---|
| `BlackBoardAtom` | `data` get/set, `clear`, `add`, `pushPoint`, `undo`, `length`, `points/radius/colors/options/total` | Слоты штрихов, настройки, бинарные данные |
| `BoardPane` | constructor, `initAction`, `interactive`, `onMouseDown/Up`, `onDrawStart/onDrawing/onDrawingEnd`, `onAddedToStage/onRemovedFromStage`, `resetBg`, `updateLess`, `redraw`, `setColor/Radius/Smooth`, `undo/clear/changeAlpha`, `fromByteArray/toByteArray` | Интерактивный `egret.Shape`, события, точки и квота |
| `Painter` | `drawNormalLine`, `drawSmoothLine` | Команды пути из принятых координат |
| `PainterPopup` | `createBlackBackground`, `createBlackBoard`, `init`, `resetSetting`, `selectColor`, `onRadiusChanged`, `onSmoothButtonClick`, `undoHandler/clearHandler/saveHandler` | Окно редактора, маска, настройки и сохранение |
| `com.magnetjoy.net.Atom` | `_propertyInfos`, `readValue/writeValue`, `toByteArray/fromByteArray` | Общая бинарная сериализация `data:Array` |
| Egret `Graphics/GraphicsNode` | `clear`, `lineStyle`, `moveTo/lineTo/curveTo`, `drawData` | Хранит и рисует отдельные StrokePath |

`BlackBoardAtom.total` / `length` — число **слотов штрихов**, включая обычно пустой резервный. Точный `pointCount` — сумма `points[i].length`, а не `total`.

### 12.2. Состояния BlackBoardAtom и BoardPane

| Вызов | Что непосредственно делает код | Ограничение |
|---|---|---|
| `new BlackBoardAtom()` | `points=[[]]`, `radius=[4]`, `colors=[0xFFFFFF]`, `options=[true]`, `total=1` | Есть слот, но **нет принятых точек** |
| `new BoardPane(extended,maxPoint=2000)` | Создаёт Atom, временно размеры 200×200, подключает events, устанавливает `max` и выполняет `clear` | 2000 — fallback конструктора, popup передаёт `blackBoard.maxPoint` |
| `pushPoint(P)` | Помещает P в **последний** массив, только если он пуст или `!P.equals(last)` | Последовательный дубль не расходует CHALK |
| `add()` | Если последний массив непустой: создаёт следующий `[]` и наследует `radius/color/options`, увеличивает `total` | Штатно после законченного штриха остаётся пустой слот |
| `BlackBoardAtom.clear()` | Стирает точки, делает `points=[[]]`, `total=1`, наследует **последние настройки** | Defaults 4/white/smooth устанавливаются только при исходном `total=0` |
| `BoardPane.clear()`, обычный | `atom.clear` → полный `redraw` → `updateLess` | Возвращает `less=max`, но выбор кисти может сохраняться |
| `BoardPane.clear()`, `_isPainterExtend` | Вставляет служебную точку `(0,0)`, вызывает `atom.add`, задаёт для слота 0 `radius=0` или `1` при alpha, white | Служебная точка учитывается в CHALK baseline |
| `setColor/Radius/Smooth(v)` | Записывает параметр в **последний** слот `atom.*[length-1]` | Не изменяет предыдущие штрихи и точный CHALK |
| `BoardPane.undo()` | Только при `points.length>1`: `atom.undo`, полный `redraw`, `updateLess` | Штатно удаляет последний завершённый штрих перед пустым слотом |
| `updateLess()` | Полный обход всех точек, `less=max-count`, `BlackBoardEvent.CHALK` с `percent=less/max` | O(N) в игровом коде; эффект на FPS не измерен |
| `fromByteArray(buffer)` | `atom.fromByteArray`, `updateLess`, полный `redraw` | Возвращает конечные точки, **не** историю их прорисовки |

Внутренний `BlackBoardAtom.undo()` удаляет слот `total-2` при длине массивов более одного, а `total--` выполняется за пределами этой проверки. Вызов через `BoardPane.undo()` предварительно проверяет число слотов. Поведение прямого вызова Atom или повреждённого импорта в E2/E4 не проверено; это **не доказанный баг живой игры**.

### 12.3. События и конечный автомат штриха

| Состояние | Событие | Действие | Затем |
|---|---|---|---|
| `IDLE`, `less>0` | `TOUCH_BEGIN` → `DRAG_START` | `onDrawStart`: `globalToLocal(stage.mouseX/Y)`, первая точка, quota, **полный** `redraw()` и подписка на `ENTER_FRAME` | `DRAWING` |
| `IDLE`, `less<=0` | `DRAG_START` | Устанавливает `less=0`, не добавляет точку и listener | `IDLE` |
| `DRAWING`, внутри rect, CHALK есть | `ENTER_FRAME` | `onDrawing`: `globalToLocal`, `Rectangle.contains`, `pushPoint`, `updateLess`, `redraw(false)` | `DRAWING` |
| `DRAWING`, снаружи rect | `ENTER_FRAME` | Не добавляет точку и не перерисовывает | `DRAWING` |
| `DRAWING`, CHALK исчерпан | `ENTER_FRAME` | Не добавляет новые точки, `less=0` | `DRAWING` до mouseup |
| `DRAWING` | `TOUCH_END` → `DRAG_END` | `onDrawingEnd`: снять `ENTER_FRAME`, `redraw(false)`, `atom.add()` | `IDLE` |

`onDrawStart` не выполняет **отдельной** `Rectangle.contains`-проверки первой точки, а `onDrawing` выполняет. Это не доказывает возможность внеэкранного начала: обычно `TOUCH_BEGIN` поступает через hit-test интерактивной доски. `onDrawingEnd` не добавляет mouseup-точку отдельно.

### 12.4. Существенное отличие живого redraw от one-pass replay

В игровом `BoardPane.redraw(full=true)` полный режим вызывает `resetBg()` и `graphics.clear()`, затем строит пути всех сохранённых штрихов. `redraw(false)` **не очищает** graphics; он выбирает **только последний** массив точек, но заново вызывает `graphics.lineStyle` и `Painter.drawSmoothLine/drawNormalLine` для всего этого массива.

В сохранённом Egret `GraphicsNode.lineStyle()` создаёт `new StrokePath`, затем `drawData.push(path)`. `CanvasRenderer.renderGraphics()` проходит по этому массиву и вызывает `stroke()` для каждого. Следовательно, во время активного штриха `onDrawing` на каждом принятом кадре и `onDrawingEnd` **накапливают команды полного текущего пути**. Даже когда `pushPoint` отклонил соседний дубль, `onDrawing` всё равно вызывает `redraw(false)` при попадании внутрь доски. Начало следующего штриха через полный `redraw()` очищает эту накопленную историю.

**E1 вывод:** конечный список принятых точек не определяет всю графическую историю последнего/активного штриха. **E0 гипотеза:** повторная композиция может влиять на alpha/edge pixels. Её эффект на 11 FILL-001 leaks или 738 model-only pixels **не измерен**.

Существующий [`game_renderer_reference.js`](../tests/game_renderer_reference.js) обычно присваивает `atom.points` и вызывает один **полный** `BoardPane.redraw()`. Поэтому его E3/PRR результаты показывают соответствие one-pass пути в проверенной области, но не доказывают репликацию всей временной последовательности `redraw(false)`. Для будущего эксперимента на том же harness (не новой реализации) нужны отдельно `one-pass` и `incremental redraw` с run-bound input/ENTER_FRAME доказательствами.

### 12.5. Бинарный формат сохранённой доски

Базовый `Atom` регистрирует единственное сериализуемое поле `data:Array`. Геттер `BlackBoardAtom.data` выдаёт последовательно:

~~~text
points.length
  для каждого stroke: count; x0; y0; ...; xN; yN
radius.length; radius[0] ...
colors.length; colors[0] ...
options.length; options[0] ...
~~~

Сеттер читает массив через `shift`, создаёт `egret.Point(x,y)`, восстанавливает четыре параллельных массива и присваивает `total=points.length`. Отдельно `total` не сохраняется. `Atom.writeValue(Array)` сериализует JS `Number` через `ByteArray.writeFloat`; в сохранённом Egret он вызывает `DataView.setFloat32`. При сохранении координат возможно **float32 округление**. Числовая round-trip ошибка здесь не измерялась.

**Условное наблюдение:** геттер записывает `colors.length`, но цикл записи фактических цветов итерирует `radius.length`. При стандартно выровненных массивах эти длины совпадают; при несогласованном ручном состоянии возможен конфликт. Это риск E1 для будущих unit fixtures, **не установленная порча живых сохранений**.

`PainterPopup.saveHandler` вызывает `toByteArray()` → `Zlib.Deflate` → Base64 → `Server.call(CallName.PAINT,{id,data})` и обновляет локальный объект. `BoardPane.importFor` декодирует/распаковывает и вызывает `fromByteArray`; `PainterPopup.init` загружает переданный `this.ba`. Успех ответа удалённого сервера нельзя доказать по одному исходнику.

### 12.6. Popup, preview и значения кисти

`PainterPopup.createBlackBoard` создаёт **interactive** `BoardPane(this._isPainterExtend,this.blackBoard.maxPoint)` размером 460×240, в позиции `(boardX,75)` и с `mask=boardMask`. Значение `boardX` зависит от типа popup, не является универсальной screen-координатой. Preview `BoardItemBase.createNativeContent` создаёт иной экземпляр `BoardPane` с `interactive=false` и отдельным scale.

`PainterPopup.init()`: `fromByteArray(this.ba)` → `updateLess` → `setSmooth(true)` активному слоту → `resetSetting()`. Последний выбирает белый и толщину 7; обычные пресеты `RadiusOption` — **20, 14, 7**, начальное значение нового `BlackBoardAtom.radius` — **4**, а специальный UI может иметь `MAX_RADIUS=30`. Все эти значения называются в модели `radius`, но передаются в Egret как **lineWidth**.

`selectColor`, `onRadiusChanged` и `onSmoothButtonClick` меняют только текущий слот, `undoHandler/clearHandler` делегируют операции доске. Отдельный сценарий изменения параметров посреди штриха ещё не тестировался.

### 12.7. Что подтверждено, что осталось

**E1 PASS:** полный `main.min` прочитан и его blob SHA совпал; профильные методы `BlackBoardAtom/BoardPane/Painter/PainterPopup/Atom` и Egret `GraphicsNode/CanvasRenderer` проверены непосредственно. Предыдущая проблема чтения файла снята. **ENGINE-001 остаётся PARTIAL:** вся цепочка `WebTouchHandler → TouchHandler → SystemTicker/ENTER_FRAME → BoardPane → GraphicsNode → CanvasRenderBuffer/WebGL/mask → screen` ещё не сведена в полностью проверенный граф, а часть игрового кода вне доски не инвентаризирована.

Новые E2/E4 эксперименты и unit tests не выполнялись; старые PRR `6/6 PASS_PER_RUN` и FILL-001 PNG `FAIL` не меняются.

**Следующий шаг, зафиксированный после §12 (выполнен статически в §13):** проверить полную цепочку input/frame/render. Динамический тайминг и пиксельная эквивалентность остаются отдельными E2/E4 вопросами.

## 13. Сквозная трассировка браузерного ввода, Egret-кадров и WebGL-вывода (2026-11-08)

**Область подтверждения:** прямое чтение сохранённого [`main.min_653f95bc.js`](../gameEngine/main.min_653f95bc.js), Git blob `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`, и [`mergeEngine_df2e5bc5.js`](../gameEngine/mergeEngine_df2e5bc5.js), blob `d613d2b97e2436521aa3870478c69e99eac1f19f`. Статус перечисленных связей: **E1 PASS** для этого набора файлов. Это не E4 для текущего сайта или конкретного будущего браузера. Код минифицирован: приведены **имена методов**, проверяемые поиском в исходнике, а не ненадёжные номера строк.

### 13.1. Источник stage.mouseX/Y — уточнение desktop/mobile

Сохранённый `Preloader.initStage()` в главном bundle регистрирует обновление позиции на Egret stage:
- **Desktop:** `mouse.enable(stage)` → `mouse.setMouseMoveEnabled(true)` → `stage.addEventListener(mouse.MouseEvent.MOUSE_MOVE, listener)`; listener сохраняет `stage.mouseX=event.stageX` и `stage.mouseY=event.stageY`.
- **Mobile:** `stage.addEventListener(egret.TouchEvent.TOUCH_MOVE, listener)` с тем же обновлением координат, одновременно выбираются мобильные настройки `FIXED_NARROW` и LANDSCAPE.
- **При нажатии на саму доску** `BoardPane.onMouseDown(event)` дополнительно устанавливает stage coordinates из `event.stageX/Y` и отправляет `DRAG_START`.

Desktop-расширение `mouse.enable` находится **в согласованном merge bundle**, а не является догадкой о стандартном Egret:
1. Сохраняет исходный `egret.sys.TouchHandler.prototype.onTouchMove` и оборачивает его. Обёртка вызывает оригинал, затем при включённом `setMouseMoveEnabled(true)` через `stage.$hitTest(x,y)` отправляет `mouse.MouseEvent.MOUSE_MOVE`, и выполняет hover/roll-over логику.
2. Аналогично оборачивает `onTouchBegin` и `onTouchEnd`. Обёртка `WebTouchHandler.getLocation` выставляет внутренний флаг при `event.buttons==0`; для ветви end plugin может дополнительно синтезировать mouse move, чтобы получать hover-координаты.
3. **Оригинальный** `TouchHandler.onTouchMove` отправляет `egret.TouchEvent.TOUCH_MOVE` только для активного touch identifier и при отличии координаты от предыдущей. Дополнительный `mouse.MouseEvent.MOUSE_MOVE` расширения имеет **отдельные условия** и не равен количеству принятых точек `BoardPane`.

Означает: desktop `BoardPane.onDrawing()` в `ENTER_FRAME` читает **последнее сохранённое значение stage.mouseX/Y**. Это не обработчик каждого OS mousemove и не очередь всех DOM events. Точный browser-event coalescing и порядок относительно кадра по E1 восстановить нельзя.

### 13.2. Браузерный pointer → Egret stage → BoardPane-local

Проверенный путь:

~~~text
browser canvas event: mousedown / mousemove / mouseup
  -> egret.web.WebTouchHandler.addMouseListener()
  -> WebTouchHandler.getLocation(event)
     pageX/pageY - canvas.getBoundingClientRect() origin; rotation ±90; /scaleX/Y; Math.round()
  -> egret.sys.TouchHandler.onTouchBegin/Move/End
     (с desktop mouse.enable() wrappers, если включены)
  -> TouchHandler.findTarget() = stage.$hitTest(stageX,stageY)
  -> Egret TouchEvent + дополнительное custom mouse.MouseEvent.MOUSE_MOVE
  -> Preloader stage mouseX/Y; BoardPane.onMouseDown initial stage coordinates
  -> BoardPane.globalToLocal(stage.mouseX,stage.mouseY)
     -> transformPoint через inverted concatenated display-object matrix
  -> BlackBoardAtom.pushPoint(), если соблюдены условия quota и bounds
~~~

В исходном `egret.DisplayObject.globalToLocal()` используется `$getInvertedConcatenatedMatrix().transformPoint()`. Собранная матрица учитывает цепочку родителей, scale/rotation/translation, anchor offsets и сдвиг `scrollRect`. Следовательно, **одних размеров доски 460×240 недостаточно** для преобразования browser client/desktop→board.

В desktop `WebTouchHandler.onMouseMove(event)` при `event.buttons==0` вызывает `onTouchEnd`, а при зажатой кнопке — `onTouchMove`. Дополнительное desktop `mouse.enable` поддерживает hover обновления. Это **реальный код**; предположение, будто каждая DOM mousemove всегда проходит одинаковый `TouchEvent.TOUCH_MOVE` route, неверно.

### 13.3. Порядок Egret SystemTicker: рендер до ENTER_FRAME

В `egret.sys.SystemTicker.update(force)`:
1. Вызываются зарегистрированные tick callbacks; на основании `frameDeltaTime` и `lastCount` определяется, нужен ли рендер в этом обновлении.
2. При полном обновлении выполняется **`this.render(true, ...)`**.
3. **После этого** вызывается `this.broadcastEnterFrame()`, который dispatch `egret.Event.ENTER_FRAME` подписанным display objects.

Внутри `SystemTicker.render` вызывается `Player.$render`; тот вызывает `stage.$displayList.drawToSurface()`, далее `systemRenderer.render(...)`. Подписанный `BoardPane.onDrawing` срабатывает уже **после этого прохода рендера**. Так что Graphics-изменение, выполненное внутри текущего `ENTER_FRAME`, может появиться в **следующем** подходящем render pass, а не в только что завершённом.

Примечания по доказательности:
- Это порядок **в данном сохранённом SystemTicker**, не гарантированная задержка в миллисекундах или всегда ровно один новый frame.
- Runtime snapshot 04.11 показывает `stage.frameRate=30`; статистика accepted-point интервалов около 33 мс относится к **отдельному наблюдённому FILL-001 run**, а не к текущей игре.
- `mouse.enable()` дополнительно регистрирует hover/roll-over callback на каждом пятом `ENTER_FRAME`; он **не** заменяет основной `BoardPane.onDrawing` и сам по себе не расходует CHALK.

### 13.4. От принятой точки до Canvas2D raster

В `BoardPane.onDrawing()` на `ENTER_FRAME`: `globalToLocal` → `Rectangle.contains` → `pushPoint` → `updateLess` → `redraw(false)`. При условии `less<=0` метод не добавляет точек. Текущая частота появления `P_i` зависит от обработанных mouse coordinates, времени Egret кадра и дедупликации `Point.equals()`.

В `BoardPane.redraw()` путь `Painter.drawSmoothLine(...,true,false)` либо `drawNormalLine` передаётся в `egret.Graphics`. При `lineStyle(width,color,1,false)` отсутствующие caps/joints нормализуются `GraphicsNode.lineStyle()` в `round`. `CanvasRenderer.renderGraphics` читает `drawData`; задаёт `lineWidth/lineCap/lineJoin`, создаёт path из `moveTo/lineTo/quadraticCurveTo` и вызывает Canvas2D `stroke()`. Для линии толщиной 1 или 3 в Canvas-рендерере существует специальный контекстный сдвиг 0.5/0.5 px.

Особенность [§12.4](#124-существенное-отличие-живого-redraw-от-one-pass-replay): `onDrawing` и `onDrawingEnd` повторно вызывают `redraw(false)`, накопляя отдельные `StrokePath`. Обычный окончательный replay через один `redraw()` строит другую **командную историю**. Разница в конкретных пикселях остаётся E0 до проверки.

### 13.5. WebGL path: GraphicsNode → texture → mask → stage

Реализация `egret.web.WebGLRenderer.renderGraphics(node,buffer,...)` в сохранённом merge bundle:
1. Вычисляет размер объекта и множители `DisplayList.$canvasScaleX/Y`, формирует pixel dimensions (через `Math.ceil` и пересчёт эффективного scale).
2. Создаёт или переиспользует `CanvasRenderBuffer`. Для грязного `GraphicsNode` вызывает **`CanvasRenderer.renderGraphics(node,canvasBuffer.context)`**, то есть геометрия линии первоначально **растеризуется Canvas2D даже при `renderMode=webgl`**.
3. Создаёт или обновляет WebGL texture методом `createTexture` или `updateTexture` и выполняет `context.drawTexture(...)`. Кэширование связано с `node.dirtyRender`.
4. `WebGLRenderer.drawDisplayObject()` проверяет `displayObject.$renderMode`: для маски используем `drawWithClip`, для отдельного scrollRect — `drawWithScrollRect`. Отрисовка `Player.$render` в конечном счёте проходит через `DisplayList.drawToSurface` на stage backing.

**Оба ограничения доски применяются, но по разным путям:**
- `BoardPane.resetBg` задаёт локальный **прямоугольный** `scrollRect=(0,0,width,height)`.
- `PainterPopup.createBlackBackground` создаёт отдельный `boardMask` с `drawRoundRect(0,0,460,240,10)` и задаёт `painterBoard.mask=boardMask`.
- Для `WebGLRenderer.drawWithClip` при наличии display-object `$mask` создаются offscreen буферы содержания и маски, затем выполняется **`destination-in`** композиция. Когда дополнительно есть `$scrollRect`, применяется прямоугольная маска вокруг финальной композиции через `pushMask/popMask`.
- Если объект ограничен **только** `$scrollRect`, `drawWithScrollRect` может использовать `enableScissor/disableScissor` при подходящей осевой матрице, либо `pushMask/popMask` при иных transforms или уже включённом scissor.

Важно: закруглённая маска **игровой доски** не тождественна целевой **маске фигуры** внутри FILL-001. Комбинация offscreen alpha-mask, WebGL texture filtering, округления backing dimensions и browser antialiasing — возможные причины отличия от идеальной OpenCV-капсулы, но вклад каждой в старые 11 leakage / 738 model-only pixels остаётся **UNKNOWN**.

### 13.6. Stage → backing canvas → CSS client → desktop PNG

В `egret.web.WebPlayer.updateScreenSize()`:
- `screenAdapter.calculateStageSize(...)` определяет `stageWidth/stageHeight` и `displayWidth/displayHeight` согласно scale mode;
- `displayScaleX=displayWidth/stageWidth`, `displayScaleY=displayHeight/stageHeight`;
- `canvasScaleX=Math.ceil(displayScaleX × DisplayList.$canvasScaleFactor)`, аналогично Y;
- CSS `transform` canvas настраивается для display scale, компенсируя backing scale, и передаётся в `webTouchHandler.updateScaleMode(displayScaleX,displayScaleY,rotation)`;
- `DisplayList.$setCanvasScale(canvasScaleX,canvasScaleY)` определяет масштаб растеризации, а `Player.updateStageSize` меняет размеры stage render buffer.

Для пользовательского [runtime snapshot 04.11](../data/runtime/renderer_snapshot_2026-11-04.json) были `stage=1672×600`, `backing=5016×1800`, `canvasScaleX/Y=3` и `Capabilities.renderMode=webgl`. Это **E4 конкретного прежнего snapshot**, не константы движка; `canvasScaleFactor=2` не равен фактическому canvasScale=3. В самом сохранённом JSON `boardClientCorners=null`, а `canvas.screenQuad=null`: **клиентские углы BoardPane в этом snapshot не записаны**. Наличие axis-aligned CSS transform и stage corners позволяет исследовать возможный пересчёт, но не доказывает, что `boardClientCorners` были рассчитаны и валидированы в той сессии. В более новом Monitor предусмотрен отдельный проверяемый affine fallback; он не должен ретроспективно приписываться snapshot 04.11. Для старого 27-stroke FILL-001 run нет полного **same-run** renderer geometry, и чужой snapshot нельзя выдавать за его screen transform.

Координатные пространства не взаимозаменяемы: board logical 460×240, stage, backing pixels, CSS client, desktop PNG/ROI; внутри AutoDraw дополнительно существуют screen-local план и исполнительные screen pixels. Конкретный affine mapping принимается только вместе с версией и calibration evidence.

### 13.7. Что должен учитывать будущий Egret replay, не выполняя его сейчас

| Уровень будущего сравнения | Нужно сохранить / воспроизвести | Нынешний статус |
|---|---|---|
| Финальная геометрия пути | Те же accepted points, stroke order, width/color/options, `Painter` smooth/normal | Existing one-pass harness; E2/E3 в проверенных fixtures |
| Temporal Graphics | Последовательность вызовов `onDrawing/redraw(false)`, включая дубли и final redraw | **NOT_RUN**; final accepted-point array этого не определяет |
| Browser input | DOM event coalescing, desktop `mouse.enable`, `stage.mouseX/Y`, Event/ENTER_FRAME ordering | E1 paths проверены; E4 timings не проверены |
| Маски и backing | ScrollRect, roundRect display mask, WebGL offscreen composite, texture sampling, stage scale/translation | Source E1; частичное E3 PRR для single strokes |
| Screenshot identity | Same-run transform, before/after pixels, threshold, target ROI | Старый FILL-001: 98.430600% / 11 leaks **FAIL**, полная same-run geometry отсутствует |
| CHALK | `post.pointCount-pre.pointCount` с run-bound Monitor/Bridge | Старый 27-stroke run: 1260 measured; для будущих вариантов **NOT_RUN** |

**Итог ENGINE-001 на данном шаге:** input → sampling → drawing → raster/mask/Stage *статически прослежены* (E1 PASS) для сохранённой версии Egret 5.4.1. Нельзя на основании кода объявить доказанными фактическое количество кадросэмплов, конкретную альфа-маску каждого пикселя, воспроизведение temporal renderer или причинность FILL-001 PNG ошибок. Эти вопросы оставлены для **отдельно разрешённых** экспериментальных этапов.

**Сверка с Monitor/Bridge, PRR и runtime snapshot проведена:** подробная матрица доказательств и исправленное ограничение координат приведены в §14. Для завершения вопросов pixel/temporal equivalence понадобятся отдельно разрешённые E2/E4 проверки, не входящие в этот документационный шаг.

## 14. Финальная сверка источников: Game Monitor/Bridge, PRR и runtime (2026-11-08)

**Проверенная база:** remote HEAD `22649900ffdc0e7bde317ced277ca01d2e710029`; сохранённый Egret bundle [§13](#13-сквозная-трассировка-браузерного-ввода-egret-кадров-и-webgl-вывода-2026-11-08), [Game Monitor/Bridge API](GAME_MONITOR_BRIDGE_REFERENCE.md), [runtime JSON 04.11](../data/runtime/renderer_snapshot_2026-11-04.json), [исторический индекс первичных PRR captures](TEST_RESULTS_HISTORY_THROUGH_2026-11-08.md#2026-11-07--prr-formal-paired-renderer-acceptance-66-pass), формальная [DEC-025](DECISIONS.md) и [renderer_acceptance.py](../source/preparation/renderer_acceptance.py). Это **read-only cross-source audit**; новых игровых данных, pixel comparisons и тестов не получено.

### 14.1. Матрица уровней доказательств

| Звено | Доказательство и область | Итог |
|---|---|---|
| DOM pointer → desktop `mouse.enable` → `stage.mouseX/Y` → `BoardPane.globalToLocal` | Согласованный `main.min_653f95bc.js` + `mergeEngine_df2e5bc5.js`; методы описаны в §13 | **E1 PASS** для сохранённой версии, не подсчёт всех OS/DOM событий |
| `SystemTicker.render()` **перед** `broadcastEnterFrame()` | Прямой static call order в Egret §13.3 | **E1 PASS**; E4 задержка в ms **NOT_RUN** |
| `pushPoint/updateLess/redraw(false)` и `CHALK=post.pointCount-pre.pointCount` | Код `BoardPane/BlackBoardAtom`; [PRR Monitor captures](TEST_RESULTS_HISTORY_THROUGH_2026-11-08.md#2026-11-07--локальный-prr-batch-и-exact-chalk-evidence) | **E1 PASS + прежнее E4** в валидных runs; не равно длине пути |
| Monitor `MOUSE_MOVE_SAMPLE`, `DRAW_SAMPLE`, `POINT_QUOTA_UPDATE` | [API §3](GAME_MONITOR_BRIDGE_REFERENCE.md); `state_poll` раз в 25 ms в PRR | **E1 + подтверждение reports**; при `pointDelta>1` наблюдаемая `acceptedPoint` не раскрывает промежуточные точки |
| Round caps, Canvas2D `GraphicsNode` raster → WebGL texture, два вида clipping | Сохранённые renderer methods §5–§6, §13 | **E1 PASS**; полная пиксельная эквивалентность **UNKNOWN** |
| Offline Egret internal equality | [Сохранённый reference manifest](../data/renderer_result/egret-5.4.1-renderer-reference-manifest.json): один single-stroke fixture, WebGL comparison `differingPixels=0` | **E2/E3 PASS только внутри reference harness**, не live screen |
| PRR paired renderer | [CI 42321009715](https://github.com/Kiddos19882/AutoDraw/actions/runs/42321009715), [artifact 13553551374](https://github.com/Kiddos19882/AutoDraw/actions/runs/42321009715/artifacts/13553551374): 6/6 `PASS_PER_RUN`, 3 vertical + 3 diagonal | **E3 PASS по формальной политике** на сохранённых E4 captures, не pixel identity |
| Same-run desktop/PNG mapping для старого FILL-001 27-stroke run | ROI есть; полного run-bound renderer snapshot нет | **PARTIAL/UNKNOWN**; snapshot другой сессии не подставлять |
| Accepted-only multi-stroke Egret replay | [ENGINE-001 §15](#15-engine-001--offline-temporal-replay-принятых-точек-2026-11-08): 27 strokes/1260 points, Canvas/WebGL 0 RGBA differences, historical source fixed | **E2/E3 PASS для offline supported variant**; unknown extra ENTER_FRAME callbacks и desktop mapping |

### 14.2. Монитор не равен браузерному или кадровому трассировщику

`MOUSE_MOVE_SAMPLE` (при явном включении input telemetry) фиксирует доставленный DOM `mousemove` после обработчика Egret на canvas, но не гарантирует регистрации всех движений OS/executor. `DRAW_SAMPLE` формируется по изменению quota; `state_poll` раз в 25 ms нужен как fallback на случай захвата listener до установки wrapper. `POINT_QUOTA_UPDATE` после `updateLess` имеет точный `pointDelta` и последнюю `acceptedPoint` при положительном изменении. Нельзя считать ни один из этих потоков прямым счётчиком `ENTER_FRAME` или всех физических движений мыши.

В четырёх дополнительных PRR runs суммарный `DRAW_SAMPLE.pointDelta` совпал с exact pre/post CHALK, `dropped_events=0`, `monitor_error_count=0`, `collector_sequence_gap_count=0`; границы штриха восстановлены через `pointer_observer`, а не через отсутствующие в этих reports `DRAW_START/DRAW_END`. Для трех vertical captures CHALK **71, 71, 70**; для трех diagonal **161, 161, 160**. Это воспроизводимость для `radius=10` и frozen executor profile, не универсальная зависимость от ширины кисти или частоты Egret.

### 14.3. Правильная трактовка PRR PASS

В историческом [PRR CI](https://github.com/Kiddos19882/AutoDraw/actions/runs/42321009715) шесть independent-transform comparisons прошли формальный gate: vertical IoU **0.938405–0.938980**, diagonal IoU **0.949646–0.951996**. [DEC-025](DECISIONS.md) **до этих повторных captures** зафиксировал отдельную renderer policy: `iou_min=precision_min=recall_min=0.92`, `symmetric_difference_fraction_max=0.087`, bbox edge tolerance 8% (минимум 1 px), alpha threshold 24; эти константы присутствуют в коде и на pre-acceptance commit `52e3c51a`. Предыдущий исторический порог 0.995 относится к прежней политике и не должен интерпретироваться как действующий для CI 42321009715. Формальный PASS **не означает**, что PNG попиксельно совпадают или что политика FILL-001 (coverage ≥99%, leakage=0) была ослаблена.

Эти PRR опираются на реальные ранее сохранённые game PNG и соответствующие run-bound geometry, но CI — повторное offline сравнение **существующих** captures, не новый live gameplay. Одна финальная массивная Graphics path и цепочка `redraw(false)` на каждом принятии остаются разными способами воспроизведения; temporal equivalence **NOT_RUN**.

### 14.4. Обнаруженное расхождение документации с первичным JSON

Ранее в §13.6 говорилось, что клиентские углы доски рассчитаны fallback-transform в [snapshot 04.11](../data/runtime/renderer_snapshot_2026-11-04.json). **Исходный JSON утверждает иное:** `renderer.players[0].boardStageCorners.topLeft=(519.7916660308838,72)`, `renderer.players[0].boardClientCorners=null` и `renderer.players[0].canvas.screenQuad=null`. При этом действительно зафиксированы `stage=1672×600`, `backing=5016×1800`, `canvasScaleX/Y=3`, `stage.frameRate=30`, `renderMode=webgl` и CSS matrix canvas. Утверждение §13.6 исправлено на границу имеющихся полей. `stage corners` не являются автоматически ни CSS client, ни desktop pixels; новой калибровки для того run не получено.

Snapshot датирован **2026-11-04**, а формальная PRR серия — **2026-11-07**: перенос CSS/Stage/desktop transform между ними недопустим. Доказательства `boardClientMappingMethod` для прежнего snapshot отсутствуют; возможность fallback в текущем Monitor не доказывает, что он исполнился тогда.

### 14.5. Остаточный риск и граница завершения документационного шага

**Документационная сверка завершена; `ENGINE-001 PARTIAL` сохраняется по инженерной валидации.** Не получены: непосредственная пара DOM-event ↔ `ENTER_FRAME` с measured frame-lag; воспроизведение **всех** дублирующихся ENTER_FRAME/render passes и условий живого compositing; независимая screen-space calibration старого FILL-001 run; pixel-identical renderer на разных кистях/окружениях. Историческая FILL-001 проверка остаётся **REJECTED** (coverage=98.430600%, leakage=11), точный CHALK=1260 не пересчитан.

**Следующий технический gate:** после accepted-only §15 исследовать влияние неподтверждённых extra redraw без принятой точки / intermediate render passes, не подменяя отсутствующий frame trace. Same-run geometry для старого run по-прежнему не дана. Никаких production, frozen evidence, acceptance thresholds или live запусков этой документационной сверкой не изменено.


## 15. ENGINE-001 — offline temporal replay принятых точек (2026-11-08)

**Протокол / experiment ID:** `ENGINE001_TEMPORAL_ACCEPTED_ONLY_V1`. Цель: на одинаковых сохранённых точках проверить **итоговые** Canvas2D и WebGL RGBA для `one-pass redraw()` и приближённой последовательности `onDrawStart redraw()` → по каждой новой принятой точке `redraw(false)` → `onDrawingEnd redraw(false)` → `atom.add()`. **Результат сравнения не требовалось заранее объявлять различным или идентичным**: критерий корректного выполнения — полный pinning входа, точный порядок 27 stroke/1260 points, оба непустых финальных изображения и диагностические counts. Исходный live PNG не заменяется.

**Зафиксированный вход:** [Game Monitor run](../data/results/brush_behavior_tests/game_monitor_bridge/bb261898-8296-41f5-a333-eb0b81016410/game-monitor-run-20261104T040548835772Z-6a17a297.json), Git blob `8eb04ad7331d1e56f4aeb7d0f625c59c1dc57c24`, run `6a17a297-ea14-4527-9527-bfd8de3bd335`, session `bb261898-8296-41f5-a333-eb0b81016410`; `pre.pointCount=1`, `post.pointCount=1261`, exact historical CHALK=1260; `stroke_count=27`, `accepted_points=1260`, каждая `point_delta=1`, нет зафиксированных dropped/sequence/monitor/bridge ошибок. Исходник содержит **все принятые точки**, но не все вызовы `onDrawing` при отсутствии новой точки. Режим `smooth` задан **исследовательским предположением**: per-stroke `options` в run отсутствует. Рабочая ширина `lineWidth=10`.

**Исполнение:** реальный `BoardPane`, `BlackBoardAtom.pushPoint/add`, `BoardPane.redraw`, `GraphicsNode`, `CanvasRenderer` и `WebGLRenderer` из зафиксированного Egret 5.4.1; [исследовательский режим](../tests/game_renderer_reference.js) `?temporal=fill001` встроен в существующий harness и запускается в [CI script](../tests/run_egret_renderer_reference.ps1). Для новой последовательности разрешены только accepted-point redraw events и финальный redraw конца штриха; при переходе к следующему штриху выполняется полный redraw. В обоих вариантах **не рисуется исходная служебная точка** `pre.pointCount=1` — сравнивается равная геометрическая выборка, а не точная реконструкция всего live canvas. Инварианты неизменности Git blob, run/session, 460×240, radius10, 1260/27 и integrity проверяются fail-closed; [Node regression](../tests/game_renderer_reference.test.js) включает неполные и испорченные входы.

**E2/E3:** браузерный Egret job **SUCCESS** в [CI 42434968046](https://github.com/Kiddos19882/AutoDraw/actions/runs/42434968046) на кодовом commit `8d5d0880c2027bf5c699608578d338025d64c595`; [artifact 13599086458](https://github.com/Kiddos19882/AutoDraw/actions/runs/42434968046/artifacts/13599086458) содержит JSON и 4 PNG, размер каждого 1380×720. Графический контекст: headless Edge WebGL1 ANGLE SwiftShader, не обязательно равен GPU live игры.

| Метрика | One-pass | Accepted-only incremental |
|---|---:|---:|
| Принятые точки / завершённые штрихи | 1260 / 27 | 1260 / 27 |
| Полных `redraw()` | 1 | 27 |
| `redraw(false)` | 0 | 1260 |
| `GraphicsNode.drawData.length` | 29 | 70 |
| Canvas2D difference vs one-pass, RGBA pixels | — | **0** |
| WebGL difference vs one-pass, RGBA pixels | — | **0** |

**Независимая проверка скачанного CI artifact (PNG-only E5 в offline domain):** Python/Pillow+NumPy повторно прочитали четыре PNG, сравнили каждый RGBA канал; для `onepass` и `incremental` совпадение точное в Canvas2D и WebGL. Каждый имеет **406282 пикселя с ненулевой alpha** и границы nonzero-alpha `(213,153)..(1177,581)` в 1380×720 — это не совпадение пустых изображений. Сравнение Canvas2D против WebGL в **каждом** варианте даёт 243 отличающихся пикселя, максимальная разница канала=1. SHA-256 полученного ZIP `0aede096b0e28e6a7d18e83e71dfc576310b36b2bcedb30a8136d1f971a76fde`.

**Итог validation workflow на том же code/test SHA:** [CI 42434968046](https://github.com/Kiddos19882/AutoDraw/actions/runs/42434968046) completed **SUCCESS**; все обязательные jobs успешны, optional benchmarks/Windows portable build SKIPPED. Узкая проверка данного offline temporal случая не становится E4 для живой игры.

**Область вывода:** дополнительные `StrokePath` действительно накапливаются (70 против 29), но в *данном* accepted-only эксперименте итоговая растеризация не изменилась. Влияние накопления как достаточная причина FILL-001 underfill/leakage **не подтверждено**. Это не доказательство отсутствия влияния на runtime latency/memory, неожиданные duplicate `ENTER_FRAME`, очередность промежуточных renderer passes, другую кисть/режим, GPU, game screenshot, сохранённый service point или физический transform. Старые FILL-001 gates остаются FAIL (98.430600% и 11 leakage); ни CHALK новых кандидатов, ни новые live measurements не получены.

**Следующий вопрос:** исследовательский E2 контроль с дополнительными `redraw(false)` без новой точки и с промежуточным render/upload в отдельном versioned protocol; для claims о реальной частоте/фазе кадров потребуется отдельное E4 evidence. Устаревшую screen geometry другого run использовать запрещено.

## 16. Почему одинаковые горизонтальные перемещения могут давать разные окончания (2026-11-08)

**ENGINE-001 / FILL-001, анализ без нового игрового запуска.** Проверены [frozen 27-stroke plan](../data/results/brush_behavior_tests/fill001/plans/fill001-rs-preflight-20261104-7.04-rectangle-r10-s5-o0-rep1.json) и [Game Monitor run](../data/results/brush_behavior_tests/game_monitor_bridge/bb261898-8296-41f5-a333-eb0b81016410/game-monitor-run-20261104T040548835772Z-6a17a297.json) (Git blob `8eb04ad7331d1e56f4aeb7d0f625c59c1dc57c24`, run `6a17a297-ea14-4527-9527-bfd8de3bd335`) на baseline HEAD `8ce14223d46a`; логика проверена по [сохранённому Egret game bundle](../gameEngine/main.min_653f95bc.js) (Git blob `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`) и [executor](../source/executor/drawing/mouse_executor.py).

### 16.1. Сверка 19 одинаковых по X запланированных линий

В frozen plan **строки 5–23** имеют идентичные `start.x=75`, `end.x=385`, но разные Y. Все 19 соответствующих штрихов в Game Monitor имеют **одинаковые** первую принятую X=`76.20833396911621` и последнюю принятую X=`389.2083339691162`. Различаются их предпоследние принятые координаты:

| Группа | Строк | Предпоследняя X | Последняя X | Midpoint последней пары |
|---|---:|---:|---:|---:|
| A | 11 | 386.208333969 | 389.208333969 | 387.708333969 |
| B | 7 | 383.208333969 | 389.208333969 | 386.208333969 |
| C | 1 | 380.208333969 | 389.208333969 | 384.708333969 |

Строки 5, 15 и 16 — примеры A, B и C. **Итоговая математическая X-координата конца smooth Graphics path меняется на 3 логических px**, хотя первая и последняя принятые X и плановые X одинаковы. В этих 19 штрихах задержка между последним accepted sample и `POINTER_UP_CANDIDATE` равна 26–54 ms; это Monitor timestamps, а не точный тайминг Egret render.

Механизм подтверждён кодом: executor отправляет много `pyautogui.moveTo` (использованный P1: step=4px, delay=5ms), `BoardPane.onDrawing` принимает текущее положение на `ENTER_FRAME` (записанный typical sample cadence около 33ms), поэтому момент кадра может менять предпоследнюю точку. Игровой `Painter.drawSmoothLine(...,true,false)` затем заканчивает путь на midpoint двух последних **принятых** точек без `lineTo(lastPoint)`. Непосредственные фазовые соответствия OS/DOM/ENTER_FRAME в старом run не записаны: изменчивая фаза sampling — согласующаяся с данными гипотеза, а вычисленные разные midpoint — проверяемый факт.

### 16.2. Почему это ещё не доказывает причину правого underfill

При номинальном `lineWidth=10` геометрический радиус круглого cap около 5. Идеализированные **непроверенные bitmap-оценки** правой границы Egret для A/B/C: midpoint+5 = **392.708 / 391.208 / 389.708**; идеализированный OpenCV cap на плановом `end.x=385` дал бы **390**. **18 из 19** таких оценок Egret не короче, а длиннее исходного OpenCV пути. Реальное bitmap покрытие может отличаться из-за alpha, Canvas/WebGL raster, endpoint extension, ROI/affine mapping и других факторов.

Предыдущая независимая [screen-ROI диагностика](CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md) насчитала **499 missed pixels в правой средней зоне**, **1116 actual misses всего**, **11 leaked pixels**. Нельзя вывести их причину, вычитая 3 logical px из одной строки, и нельзя переносить Stage/desktop geometry из другого run. В [accepted-only Egret эксперименте §15](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md) pixel equality одно-проходного и инкрементального replay относится к **одному набору принятых точек**, а не к вариациям penultimate между строками.

**Evidence:** E1 механизма + арифметическая сверка архивной E4 accepted-point телеметрии — PASS; **причинность конкретного PNG underfill — E0/NOT_PROVEN**. Оригинальный FILL-001 остаётся FAIL (coverage 98.430600%, leakage 11). Ни код, ни экспериментальные данные в этой работе не менялись.

**Следующий gate:** same-run сравнение видимой крайней X каждого изолированного штриха с реальными последними двумя принятыми точками, с отдельным контрольным `normal` vs `smooth` и теми же executor settings; валидный screen transform/PNG и timeline frame events обязательны для E4. Воспроизводить разные accepted sequences можно и offline в существующем Egret harness; результат offline нельзя объявлять доказательством live PNG. Новые production line extension, режимы сглаживания и пороги сейчас не менять.


## 17. ENGINE-001: игровой Egret против OpenCV по окончаниям FILL-001 (2026-11-08)

**Задача:** ENGINE-001, смежная диагностика FILL-001. **Code/test baseline:** `1805ebfb439ef8215bfd1dbd228417f37d6705c0`; [full CI 42438036187](https://github.com/Kiddos19882/AutoDraw/actions/runs/42438036187) **SUCCESS**, browser Egret и независимый Python audit PASS. [15 native Egret PNG + manifest](https://github.com/Kiddos19882/AutoDraw/actions/runs/42438036187/artifacts/13599599617); [board-local OpenCV comparison JSON + 3 overlays](https://github.com/Kiddos19882/AutoDraw/actions/runs/42438036187/artifacts/13600208683). Оба эксперимента versioned: `ENGINE001_NATIVE_ENDPOINT_V1`, `ENGINE001_NATIVE_ENDPOINT_BOARD_LOCAL_ANALYSIS_V1`.

**Воспроизводимость:** frozen Game Monitor run `6a17a297-ea14-4527-9527-bfd8de3bd335`, session `bb261898-8296-41f5-a333-eb0b81016410`, source blob `8eb04ad7331d1e56f4aeb7d0f625c59c1dc57c24`; frozen 27-scanline plan blob `ab54d5a322a642ba6a89a6c77111e4cfadf93232`; native game engine bundle blob `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`; Egret 5.4.1 bundle blob `d613d2b97e2436521aa3870478c69e99eac1f19f`. Все сравнения используют **одни и те же 1260 архивных принятых точек**, толщину 10 и настоящий `BoardPane/Painter`. Экспериментальные варианты: game `smooth(drawLast=false)`, временный wrapper native `Painter.drawSmoothLine(drawLast=true)`, native `normal`. В исходном run **нет per-stroke smooth options**, поэтому исходный режим smooth — явно заданное предположение.

**Backend и метрики:** Egret Canvas2D и WebGL, masked BoardPane 460×240, backing 1380×720 (3×). 6 full-board PNG и 9 изолированных WebGL PNG строк 5,15,16. Независимый [анализатор](../tests/analyze_engine001_endpoint_reference.py) проверяет Git blob hashes и 15 PNG, сравнивает alpha=1/64/128/254, board-local OpenCV LINE_8 capsule, IoU, XOR и реальные правые границы.

| Штрих | Native game smooth rightmost backing X при alpha≥128 | Forced native last X | Сдвиг | Новых / удалённых backing pixels |
|---|---:|---:|---:|---:|
| 5 | 1177 | 1181 | +4 | 131 / 0 |
| 15 | 1172 | 1181 | +9 | 270 / 0 |
| 16 | 1168 | 1181 | +13 | 401 / 0 |

Для **всех 27 линий** при alpha≥128: `game-smooth → smooth-drawlast` добавило **2936 backing pixels, не удалило ни одного**; IoU двух native raster mask = **0.99281883**. По alpha masks на всех четырёх порогах forced smooth и native normal **попиксельно равны** на этих горизонтальных данных. Canvas2D и WebGL alpha mask full game smooth при 128 также равны. OpenCV capsule, даже после согласования координат и толщины в board backing, для изолированных штрихов имеет лишь **0.96638–0.96689 IoU** с native Egret (alpha≥128), значит OpenCV не pixel-exact повтор игрового движка.

**Ограничения:** `screenProjection=UNCALIBRATED` — исторический FILL-001 не содержит валидных **same-run Stage/CSS/desktop transforms** для такого сопоставления. **Нельзя** считать 2936 backing pixels частью 1116 missing screen ROI pixels, говорить, что все 499 правых пропусков исправлены, либо считать прошлые модельные 487 pixels подтверждённым Egret результатом. Архивный FILL-001 по-прежнему **FAIL** (coverage=98.430600%, leakage=11), исторический exact CHALK=1260 неизменен. Новый CHALK и live gameplay **NOT_RUN**. Несовпадение OpenCV и native Egret необходимо учитывать на alpha/cap/clipping.

**Отрицательный результат:** на более раннем [CI 42437858048](https://github.com/Kiddos19882/AutoDraw/actions/runs/42437858048) browser Egret job **FAIL**: исследовательский wrapper считал пустой служебный current atom slot вызовом accepted stroke. Исправлено пропуском пустого слота; успешный E3 результат относится только к `1805ebf`; frozen evidence не менялось.

**Следующий gate не снят:** получить same-run координатные преобразования, per-stroke live screenshot и связь ENTER_FRAME / last-two accepted / visible endpoint, проверить duplicate redraw без новой принятой точки и actual FILL-001 residuals; до E4/E5 не изменять production painter/executor/estimator/quality gates.


## 18. Native BoardPane + замкнутая контурная обводка 5 logical px на FILL-001 (2026-11-08)

**Задача:** ENGINE-001, диагностический FILL-001 counterfactual. Новый experiment ID `ENGINE001_NATIVE_ENDPOINT_OUTLINE5_V1` и независимый `ENGINE001_NATIVE_ENDPOINT_OUTLINE5_OPENCV_V1`. **Зафиксированный code/test SHA:** `f381ffe4817b64800a15292a7ed54603f5eeabe8`; [full validation CI 42439343897](https://github.com/Kiddos19882/AutoDraw/actions/runs/42439343897) — **SUCCESS**, включая browser Egret, независимый board-local OpenCV и обязательные тесты. [Native 30 PNG, 2 manifest, previous fixtures](https://github.com/Kiddos19882/AutoDraw/actions/runs/42439343897/artifacts/13600612786), [Independent JSON + 3 overlay PNG](https://github.com/Kiddos19882/AutoDraw/actions/runs/42439343897/artifacts/13601121751). Загруженные и повторно проверенные ZIP имеют SHA-256 `d406d8f727d3cfda6c103aade783e212a01ce752dff37be393c5eaac611a5fbf` и `bcd16fd994742b213434b06f1b587f7684dc2f49c50ecc52129a92ae0fd4f39b`.

**Точная трактовка «обводка 5 px»:** *новый отдельный замкнутый контур по внешней границе frozen rectangle*, проведённый штатным `BoardPane` с nominal `lineWidth=5` **логических** пикселей, центровая линия расположена на 3 logical px внутри frozen target (`_contour_stroke(mask,3,5)`, `cv2.MORPH_ELLIPSE` erosion + `CHAIN_APPROX_SIMPLE`, 64 вершины и возврат к первой). Это **не** расширение каждой исходной линии на 5, не 5-px screen dilation и не 5-px смещение контурной линии. Для всех трёх endpoint-режимов contour намеренно рисуется **одинаковым native `normal` Painter**, после исходных 27 принятых линий. Независимый анализ проверяет точное совпадение 64 native vertex coordinates с повторной генерацией из pinned target mask (area=44653 logical px, SHA из `FILL001_EXPECTED_MASK_SHA256`). Frozen plan и archive Monitor input blob прежние; 1260 исходных accepted samples неизменны; гипотетический contour добавляет 65 переданных `atom.pushPoint` координат, но **нового измерения CHALK нет**.

**Методика:** старый opt-in `?endpoint=fill001` сохраняет 15 PNG контроля, новый `?outline=fill001` создаёт ещё 15 PNG. Каждая группа: `game-smooth`, `smooth-drawlast`, `normal`, по 2 агрегатных Canvas2D/WebGL и 3 изолированных WebGL для линий 5/15/16. Сравнение производится в board-local raster 1380×720 (3× от 460×240) с alpha thresholds `1,64,128,254`. Frozen logical target масштабирована nearest-neighbour repeat×3; OpenCV comparator `cv2.LINE_8` с width 15 backing px и round caps circle radius 8, то есть отдельный **не pixel-exact** raster. Контур, gamma/alpha и raster backend не подменяются геометрической дилатацией.

### 18.1. Board-local alpha≥128: baseline и новый native 5px contour

| Native Painter вариант | Модельное покрытие target до / после | Новых target backing pixels | Всего добавлено backing pixels | Новых outside-target backing pixels | Всего outside-target после |
|---|---:|---:|---:|---:|---:|
| `game-smooth` | 98.7499% → **99.6240%** | 3513 | 3544 | **31** | 9089 |
| `smooth-drawlast` | 98.8427% → **99.6743%** | 3342 | 3373 | **31** | 11652 |
| `normal` | 98.8427% → **99.6743%** | 3342 | 3373 | **31** | 11652 |

Обводка **не убрала** ранее закрашенные board backing pixels (0 removed в каждой группе) на threshold 128. Native contoured `smooth-drawlast` и native contoured `normal` остаются **попиксельно равны по alpha mask** на всех четырёх порогах. Новые outside-target pixels (31) присутствуют у всех трёх; прежнее board-local наружное покрытие до обводки — 9058 / 11621 / 11621 backing pixels. **Все три варианта FAIL по модельному leakage=0**, несмотря на coverage выше 99%. Это **модельная target mask**, а не actual game screenshot leakage (старый live capture имеет 11 screen pixels). Модельный large leakage нельзя использовать для оценки реального ухудшения без same-run mapping.

**Распределение разницы для `game-smooth` (все величины 3× backing, alpha≥128):** пропуски в верхней зоне 3603→1059 (2544 recovered), в нижней 154→121 (33), в левой средней 1212→276 (936), **в правой средней 55→55 (**0 recovered**)**. Для двух других вариантов правая средняя зона имела 0 до и после обводки. Независимый пересчёт PNG по той же маске (logical right-middle `x≥366, 75≤y≤165`) подтвердил нулевое улучшение справа. Значит, в этом offline reference контур 5 px **не объясняет и не исправляет** известные 499 *screen*-pixel misses справа в историческом FILL-001. Изолированные строки 5/15/16 сохранили прежние максимальные правые X в backing raster: smooth 1177/1172/1168, forced-last и normal по 1181; контур не скрыл основное различие endpoint.

### 18.2. На сколько согласуются native Egret и OpenCV

OpenCV сравнивался не с историческим экранным PNG, а **в той же 3× board-local сетке** с нативно добавленными к каждому baseline pixels. На alpha≥128 IoU **только новых пикселей от обводки** с OpenCV-ожидаемыми новыми pixels: `game-smooth=0.965818977`, `smooth-drawlast=normal=0.976183561`; проверка diff выполняется независимо по двум PNG из каждой пары и математически порождённому контурному OpenCV footprint. При alpha 1 результаты 0.976108233 / 0.984417965, а при alpha 254 резко ниже: 0.660254744 / 0.659071964. Результат **чувствителен к порогу прозрачности** и не допускает утверждения о pixel-exact совпадении графических backend.

**Что подтверждено:** real Egret воспроизводит прирост покрытия от одинакового замкнутого 5px контура, но без устранения правого остатка, а независимый OpenCV добавочный контур отличается по alpha edge. E2/E3 **PASS** для offline local native geometry; дополнительно PNG пересчитаны из downloaded CI archives (**независимая локальная E5 в offline domain**), исходные PNG не пустые. **Оригинальный FILL-001 live** неизменен: 27/27 strokes, exact CHALK=1260, coverage=98.430600%, leakage=11, **FAIL**. Для новых 65 contour coordinates нет measured game CHALK; screen mapping=UNCALIBRATED, old right screen misses=499 нельзя сравнивать 1:1 с 3× right misses=55. Per-stroke live screenshot, same-run Stage/CSS/desktop geometry, `ENTER_FRAME`/duplicate redraw остаются открытым **E4/E5 gate**, без production изменений/ослабления thresholds. [Открытая задача](TASKS.md).


## 19. ENGINE-001: повторные стационарные ENTER_FRAME при неизменных принятых точках (2026-11-08)

**Experiment IDs:** `ENGINE001_DUPLICATE_FRAMES_V1` (native game `BoardPane`) и `ENGINE001_DUPLICATE_FRAMES_INDEPENDENT_PNG_V1` (независимый PNG-аудит). **Code SHA** `a35d782084383c6d5d8fa09e19a0d15664178bc2`, [full CI 42440876068](https://github.com/Kiddos19882/AutoDraw/actions/runs/42440876068) **SUCCESS**. [Шесть native PNG, run-bound manifest, исходные accepted-only и остальные Egret fixtures](https://github.com/Kiddos19882/AutoDraw/actions/runs/42440876068/artifacts/13600769368); [независимый JSON и overlay](https://github.com/Kiddos19882/AutoDraw/actions/runs/42440876068/artifacts/13602035420). Frozen Game Monitor blob `8eb04ad7331d1e56f4aeb7d0f625c59c1dc57c24`, run `6a17a297-ea14-4527-9527-bfd8de3bd335`, session `bb261898-8296-41f5-a333-eb0b81016410`. Вход: 27 archived strokes, 1260 accepted points, `brush=10`, assumption `smooth` (per-stroke mode в архивном run отсутствует).

**Гипотеза:** при неподвижном указателе штатный `onDrawing` после отказа `BlackBoardAtom.pushPoint` от дублирующей точки может всё же вызвать `redraw(false)`. Такие дополнительные пути могут увеличить командную историю, но их влияние на результирующий растр нужно измерить, не приписывая новых CHALK.

**Метод:** в существующем [Egret harness](../tests/game_renderer_reference.js), opt-in `?frames=fill001`, для каждого штриха перед `onDrawingEnd` синтетически повторена *последняя* координата 0, 1 либо 3 раза. Каждая повторная `pushPoint` была отклонена, `board.less` не изменился; после этого вызваны настоящие `updateLess()` и `redraw(false)`. Перезапуск полного `redraw()` при начале следующего штриха очищает накопленные временные пути предыдущего. Проверены настоящие Egret 5.4.1 Canvas2D и WebGL masked BoardPane, backing `1380×720`, 6 новых PNG, включая контроль `frames0`. Отдельный [Python-аудит](../tests/analyze_engine001_duplicate_frames.py) попиксельно пересчитывает все PNG и удостоверяет pixel parity контрольного `frames0` со старым `ENGINE001_TEMPORAL_ACCEPTED_ONLY_V1` incremental replay.

| Дополнительных стационарных кадров на каждый штрих | Всего новых `redraw(false)` | Отклонённых `pushPoint` | Сохранившихся `GraphicsNode` путей | RGBA diff от контроля (Canvas2D / WebGL) |
|---|---:|---:|---:|---:|
| 0 | 0 | 0 | 70 | 0 / 0 |
| 1 | 27 | 27 | 71 | **0 / 0** |
| 3 | 81 | 81 | 73 | **0 / 0** |

Независимый audit подтвердил отсутствие изменений в alpha mask для thresholds `1/64/128/254` во всех сравниваемых вариантах. **Нюанс:** абсолютные Canvas2D и WebGL RGBA растр отличаются между собой на **243 пикселя**, но это число одинаково для всех трёх режимов; нельзя говорить, что Canvas2D и WebGL идентичны, только что *каждый backend* не изменил итоговый растр при дополнительных кадрах. Нет нового exact CHALK; исторический `1260` только исходного run.

**Отрицательный этап:** первый [CI 42440726798](https://github.com/Kiddos19882/AutoDraw/actions/runs/42440726798) в Egret browser job остановился на неверной арифметике ожидаемого количества `StrokePath`: предполагалось, что каждый из 27 дополнительных кадров навсегда добавляет путь. Исходный браузерный runtime показал `frames=1`, **27 отклонённых точек и 27 дополнительных вызовов**, но `graphicsPathCount=71`, а не 97. Это согласуется с `BoardPane.redraw(full)`: на каждом новом штрихе история предыдущего перезаписывается; финальную историю расширяют только дополнительные пути последнего штриха. Ожидания исправлены в новом SHA, без изменения игровых входных данных и без смягчения проверок принятых точек. [Диагностический artifact](https://github.com/Kiddos19882/AutoDraw/actions/runs/42440726798/artifacts/13601826297).

**Граница применимости:** E2/E3 **PASS** только для финального offline raster с 0/1/3 повторными кадрами *после последней принятой точки каждого штриха*. Исходный FILL-001 `screenProjection=UNCALIBRATED`, фактические timestamps `ENTER_FRAME`, промежуточные render passes, повторения в середине пути, DOM coalescing, реальные per-stroke mode/geometry и GPU пользователя **не восстановлены**. Нельзя объявить, что все реальные frame artifacts исключены или что исторические 499 right misses/11 leakage уже объяснены. Исторический FILL-001 остаётся `FAIL`: coverage 98.430600%, leakage=11 screen px, exact CHALK=1260 для прежнего запуска.

**Следующий неизменный E4 gate:** same-run Stage/client/desktop геометрия, per-stroke live PNG и timestamped accepted-input/ENTER_FRAME связка; проверить реальный `smooth`/ `normal` и right-end bounds без заимствования snapshot от иной сессии. Production executor, Painter, CHALK estimator и frozen evidence не менять.



## 20. ENGINE-001 — однокнопочная лаборатория реального Monitor/Bridge (2026-11-08)

**Новый независимый протокол:** `ENGINE001_ONE_CLICK_LAB_V1`, `ENGINE001` (9 unique cells). Исходный Git baseline этого этапа `951151c89ba720092b019ead4c5de46db9f03ccf`, кодовая реализация `a119b7d9748296985193a0d0a63fd1515a4660a5`. **На момент подготовки протокола live gameplay ещё не запускался (исторический E4 `NOT_RUN`);** фактические результаты девяти последующих E4 runs см. §21. Проверка workflow не заменяет E4.

**Назначение:** получить новые настоящие run-bound evidence для отличения концов штрихов `smooth`/ `normal`, влияния Egret `ENTER_FRAME` и CSS/Stage/desktop projection без допущения координат из старого FILL-001. Это диагностический ENGINE-001, а не новый FILL-001 acceptance. Новые сценарии не модифицируют executor defaults, Painter или production.

**Запуск одной кнопкой:** существующая вкладка **«Тест кистей»** → **«ENGINE-001 — чистая лаборатория»** → **«Запустить лабораторию: 9 опытов (Clear)»**. После *предварительного* однократного подключения живого `game_monitor.js` версии `0.2.4` и аутентифицированного Bridge snippet в **игровом iframe**, подтверждённых профиля экрана/координат Clear, ползунка радиуса 1–30, области доски и явного эталона пустой доски все опыты идут автоматически. Новый Monitor должен быть загружен в **свежем iframe** (избегать активных старых обработчиков). При создании Bridge выбрать любой ENGINE-001 сценарий на вкладке тестов: тогда Bridge запросит input telemetry. Первая установка snippet и Origin не автоматизирована и не заменена неподтверждённым browser injection; без готового подключения кнопка **не двигает мышь**. Однокнопочный запуск — именно после этого preflight, не cold-start всего браузера.

**Дизайн фиксированной матрицы:** 3 отдельных сценария × 3 повтора (один штрих на очищенной доске в каждом): `engine001_horizontal_endpoint` x75→385,y120; `engine001_vertical_axis` x230,y35→205; `engine001_diagonal_axis` (75,70)→(385,175). `lineWidth=10` logical px (игровое название radius), `step=2`, `delay=10ms`, `lineExtension=0`, остальные параметры как `GEOMETRY_EXECUTOR_CONFIG`; фактический smooth/normal **наблюдается в Monitor**, а не принимается из executor intent. Очерёдность 9 ячеек детерминированно перемешивается существующим `chalk_test_blocks.py`, уникальные `task_id`/attempt IDs и owner-lock, сохранение журнала до первого действия мыши; блок не перескакивает failed/partial.

**Что собирается автоматически для каждого одного штриха:**
- Текущие `session_id`, `run_id`, `experiment_id`, время, параметры Stage6, фактический радиус и точный `CHALK=post.pointCount-pre.pointCount`, полные `accepted_points` с первыми, предпоследней и последней точками, полный per-stroke lifecycle, изменение quota.
- Game Monitor `0.2.4` по включённой input telemetry дополнительно регистрирует `ENGINE_FRAME_SAMPLE` от **настоящего** `BoardPane.addEventListener("enterFrame", ...)`, не от `requestAnimationFrame`: время, `strokeId`, число принятых точек, `observedPointDeltaSincePreviousFrame`, `renderPathCount`, живые Stage/Board координаты, сырой `atom.options` для определения фактически наблюдаемого smooth. Прежний отдельный RAF `frame_probe` сохраняется как **другая метрика**, не заменяет Egret callbacks.
- Аутентифицированный Bridge сохраняет raw `ENGINE_FRAME_SAMPLE` в `monitor_report.json`, агрегат `engine_frame_samples`, `observed_stroke_modes`, исходные `renderer_geometry_at_start/end`, изменения геометрии и исходные показатели доставки/ошибок. Raw опции читаются с Egret кадра, если ранее связанный обработчик `onDrawStart` не был перехвачен; не подставляется smooth из предыдущих экспериментов.
- Existing capture снимает full-screen и ROI доски/индикатора **до** и **после** штриха, сравнивает чистоту доски перед запуском и восстанавливает кисть. `engine001_lab.py` фиксирует SHA-256 исходных файлов, дополнительный JSON-аудит, bounding box реально изменённых экранных ROI RGB пикселей (порог max-channel>=20, **не** native stroke mask), first/last accepted, frame count, режим и ссылки на raw evidence.

**Строгое завершение:** `inspect_ready_bridge()` до начала и перед каждым следующим опытом требует ровно одну свежую активную Monitor/Bridge сессию и версию `0.2.4`, input telemetry, подключённый Egret frame observer, одну BoardPane и исходную геометрию. Existing CHALK block validator проверяет all 9 immutable cells, exact CHALK, zero Monitor/Bridge losses, сохранённые screenshots и исполнение. Lab audit дополнительно требует one-to-one raw frame events/summary, стабильный реально наблюдавшийся режим на всём штрихе, совпадающие run/session ID, валидный before/after image diff, отсутствие смены `renderer_geometry` посреди опыта. На `PARTIAL`, `FAIL` или конфликте журнал приостанавливается с сохранением evidence и обязательным recovery; raw и архивы не перезаписываются.

**Границы протокола:** исходная реализация была схемой подготовки к E4; последующее реальное выполнение и новая E5 граница документированы в §21. `BoardPane` Egret `ENTER_FRAME` observer не доказывает, что событие произошло до/после конкретного `SystemTicker.render` и что перехвачены все браузерные input events. Сохранённые client corners относятся к CSS client space; калибровка desktop/screen affine **не считается доказанной**, пока нет независимого same-run transform audit. PNG threshold RGB>=20 не заменяет exact native pixel mask, FILL quality 99%/0 и E5. `ENGINE-001 PARTIAL`, исходный FILL-001 `FAIL` 98.430600% coverage, 11 leaked screen px, historical CHALK=1260; на этапе дизайна CHALK новых запусков ещё не был измерен. Серия E4 теперь проведена (§21); следующий незавершённый gate — независимая E5 PNG/native pixel-level validation при том же run geometry. [Тестовый UI](../source/preparation/brush_behavior_test_ui.py), [readiness/audit](../source/preparation/engine001_lab.py), [Monitor](../source/game_monitor/game_monitor.js), [Bridge](../source/game_monitor/game_monitor_bridge_server.py), [тесты](../source/preparation/tests/test_engine001_lab.py).


## 21. ENGINE-001 — фактическая Windows-лаборатория 9/9 и начальная E5 сверка (2026-11-08)

**Baseline:** [evidence commit `177165361b0340515fe3bb74f4847ab3ec579ebc`](https://github.com/Kiddos19882/AutoDraw/commit/177165361b0340515fe3bb74f4847ab3ec579ebc), протокол `ENGINE001_ONE_CLICK_LAB_V1`, journal `data/results/brush_behavior_tests/chalk_test_blocks/chalk-block-ENGINE001-chalk-20261108-080330-af2835-9fdb9bd9.json`, Bridge session `a5e43181-37be-4941-a170-5ec63c09e006`. Сбор выполнен локальным AutoDraw в Firefox/Windows 1920×1080; анализ здесь выполнен по опубликованным исходным игровым JSON/PNG, не через удалённое управление игрой. [CI 42449898657](https://github.com/Kiddos19882/AutoDraw/actions/runs/42449898657) **SUCCESS** для указанного commit, все обязательные jobs PASS; optional benchmarks и Windows portable build SKIPPED.

| Сценарий | Exact CHALK из `post.pointCount − pre.pointCount` | Observed Egret `ENTER_FRAME` | Captures |
|---|---|---|---|
| `engine001_horizontal_endpoint` (r1/r2/r3) | 108 / 108 / 108 = **324** | 109 / 110 / 109 = **328** | 3/3 `PASS_E4_RAW_CAPTURE` |
| `engine001_vertical_axis` (r1/r2/r3) | 60 / 60 / 61 = **181** | 62 / 62 / 62 = **186** | 3/3 `PASS_E4_RAW_CAPTURE` |
| `engine001_diagonal_axis` (r1/r2/r3) | 113 / 114 / 114 = **341** | 115 / 116 / 116 = **347** | 3/3 `PASS_E4_RAW_CAPTURE` |
| **Всего** | **846** (сумма 9 независимых расходов, не одна quota) | **861** | **9/9** |

Все 9 задач журнала завершены с первой попытки, отдельные `experiment_id`/`run_id` связаны с одной Bridge-сессией; у девяти monitor reports `point_delta_matches_chalk=true`, `stroke_count=1`, zero dropped/error/sequence-gap counters, renderer geometry at start/end идентична, geometry updates=0, фактический raw `stroke_option_raw=true`. Observer Egret фиксирует callbacks, но не все фактические рендеры и не порядок `SystemTicker.render`. Предыдущие два незавершённых блока из `9bf7c83` (`lab_bridge_gate` после первого опыта) не смешаны с новым выполненным 9/9; исправление отдельного heartbeat timestamp — [`7b129c2`](https://github.com/Kiddos19882/AutoDraw/commit/7b129c2295dab98c025072e91f4fb39d87d5eaa9).

**E5 geometric cross-check — PARTIAL, независимый пересчёт из raw events:** для каждого из 9 run прочитаны `MOUSE_MOVE_SAMPLE` с числовыми `boardX/Y`, `clientX/Y`, `screenX/Y` (всего **1641**). Во всех run разность `(screenX-clientX, screenY-clientY)` точно `(0,163)` px. Отдельно по каждой оси с ненулевым span выполнена обычная регрессия `screen = origin + scale × board` (6 X fits для horizontal/diagonal и 6 Y fits для vertical/diagonal). Максимум абсолютного остатка по этим 12 axis fits **0.749 px**; RMSE каждого fit примерно **0.416–0.427 px**. У monitor CSS BoardPane client corners `(497.9604,104.86)`–`(1170.1065,456.06)`; с наблюдаемым client→desktop сдвигом экранные границы `(497.9604,267.86)`–`(1170.1065,619.06)`. Эти величины согласуются с `screen_roi={x:496,y:265,width:674,height:355}`; fitted X-origin отличается от inspect-origin максимум на 0.077 px, Y-origin максимум на 0.063 px. Для постоянной оси отдельная независимая оценка по одному штриху невозможна: опора только на inspect и PNG. Это независимая диагностическая сверка координат, **не** доказательство экранной pixel parity и **не** полная E5 validation; она не должна применяться к другому run.

**PNG provenance и помеха:** девять before-clear board ROI имеют одинаковое изображение (одинаковый Git blob/SHA-256 в `engine001-lab-audit.json`), есть темный небольшой фрагмент у нижней границы, отсутствующий на after-draw; поэтому `board_roi_pixel_diff.changed_bounds_roi.bottom=354` во всех 9 аудитах и общий diff включает нерисовальные изменения. Результаты `changed_pixel_count`/bounds нельзя трактовать как native stroke footprint или endpoint. Два горизонтальных `after_draw-board.png` (r1/r2) побайтово идентичны; остальные файлы сохранены отдельно. Все 9 after-draw PNG визуально соответствуют ориентации. Независимый screen-only RGB диагностический пересчёт приведён далее; численный comparator с native Egret PNG/alpha **NOT_RUN**.

**E5 screen-only PNG diagnostic (exploratory, not native acceptance):** Независимо прочитаны 9 `after_draw-board.png` и общий побайтово одинаковый `before_clear-board.png` (RGB PNG 674×355), подтверждена целостность zlib Adler-32 каждого декодирования. По исходному критерию максимальной разницы RGB ≥20 во всех **9/9** опытов получены **точно те же `changed_pixel_count`**, что записал `engine001-lab-audit.json`: horizontal r1/r2/r3 **6983/6983/6969**, vertical **4157/4171/4171**, diagonal **7698/7712/7719**. При ограничении диагностической области интервалами реальных first/last accepted points, спроецированных через same-run transform, плюс 7.32 screen px полуширины и 4 px запас, во всех 9 случаях ровно **17 пикселей исходного diff** остаются за пределами области: они лежат на последней строке PNG (`y=354`), а не на линии. Это проверка источника загрязнения общего bounding box, не утверждение о состоянии игрового буфера.

Для второй, явно **диагностической**, маски дополнительно применён `max(after.RGB)<128` в пределах этой области. При RGB Δ≥20 получены screen-local границы (inclusive): **horizontal** все r1/r2/r3 `x=103..568,y=170..184`; **vertical** r1 `x=328..342,y=46..307`, r2/r3 `x=328..342,y=46..308`; **diagonal** r1 `x=103..567,y=96..264`, r2/r3 `x=103..568,y=96..264`. Проверена чувствительность к `maxRGB<64` и `<200`; из-за антиалиасинга число масочных пикселей меняется, поэтому значения **не** являются независимой native Egret alpha/mask parity и не получают pass threshold. У горизонтальных/диагональных штрихов наблюдаемое правое продление от последней accepted X до тёмного края составляет около **3.64–4.64 screen px**, в отличие от левого продления около **7.39 screen px**; эти E5-кандидатные endpoint residuals нельзя причинно переносить на исторические FILL-001 right-side misses без native same-run replay и control normal/smooth. **Итог подпроверки:** RGB raw-diff agreement 9/9, contamination isolated 9/9; native comparison `NOT_RUN`, E5 overall `PARTIAL`.

**Подробная матрица девяти runs — ранее не сведённые в таблицу диагностические значения** (архивные исходные аудиты неизменны; точные experiment/run/session IDs и SHA-256 исходных PNG содержатся в связанных JSON):

| Cell / первичный аудит | Run ID (первые 8) | Exact CHALK | Egret frames | Raw RGB Δ≥20 | Тёмные пиксели maxRGB <64 / <128 / <200 | BBox X;Y при <128 |
|---|---|---:|---:|---:|---:|---|
| [D2](../data/results/brush_behavior_tests/experiment-20261108-080419-b10-engine001_diagonal_axis-befdeaba/engine001-lab-audit.json) | `31922917` | 114 | 116 | 7712 | 7180 / 7380 / 7587 | 103..568; 96..264 |
| [D1](../data/results/brush_behavior_tests/experiment-20261108-080506-b10-engine001_diagonal_axis-04fdbd29/engine001-lab-audit.json) | `d2fcb15b` | 113 | 115 | 7698 | 7172 / 7350 / 7591 | 103..567; 96..264 |
| [H3](../data/results/brush_behavior_tests/experiment-20261108-080552-b10-engine001_horizontal_endpoint-e90f7f8a/engine001-lab-audit.json) | `cc279753` | 108 | 109 | 6969 | 6927 / 6932 / 6949 | 103..568; 170..184 |
| [V2](../data/results/brush_behavior_tests/experiment-20261108-080638-b10-engine001_vertical_axis-49ecb24b/engine001-lab-audit.json) | `86d863ca` | 60 | 62 | 4171 | 3884 / 3895 / 3905 | 328..342; 46..308 |
| [V3](../data/results/brush_behavior_tests/experiment-20261108-080723-b10-engine001_vertical_axis-8ebcbd83/engine001-lab-audit.json) | `4c0a87c4` | 61 | 62 | 4171 | 3884 / 3895 / 3905 | 328..342; 46..308 |
| [H1](../data/results/brush_behavior_tests/experiment-20261108-080807-b10-engine001_horizontal_endpoint-9c072459/engine001-lab-audit.json) | `79211ae0` | 108 | 109 | 6983 | 6940 / 6944 / 6962 | 103..568; 170..184 |
| [V1](../data/results/brush_behavior_tests/experiment-20261108-080853-b10-engine001_vertical_axis-ab43b067/engine001-lab-audit.json) | `7da99bf3` | 60 | 62 | 4157 | 3874 / 3885 / 3894 | 328..342; 46..307 |
| [D3](../data/results/brush_behavior_tests/experiment-20261108-080937-b10-engine001_diagonal_axis-73bc512a/engine001-lab-audit.json) | `310a004f` | 114 | 116 | 7719 | 7191 / 7384 / 7609 | 103..568; 96..264 |
| [H2](../data/results/brush_behavior_tests/experiment-20261108-081024-b10-engine001_horizontal_endpoint-86f6cc6a/engine001-lab-audit.json) | `23de82a3` | 108 | 110 | 6983 | 6940 / 6944 / 6962 | 103..568; 170..184 |

Обозначения: H/V/D = горизонталь/вертикаль/диагональ, 1–3 = `repeat_index`; порядок строк соответствует исполнению рандомизированной матрицы в CHALK block journal. Колонки RGB вычислены в отдельной диагностике по сохранённым `before_clear-board.png`/`after_draw-board.png` и same-run accepted-endpoint corridor; 17 нерисовальных пикселей на нижней строке ROI исключены из тёмной маски. **Данные о тёмных пикселях и их bbox не являются native WebGL alpha-map, независимость полной E5-проверки ими не доказана.** Не использовать цифры как acceptance thresholds или утверждение о совпадении с нативным движком.

**E5 следующий gate:** использовать сохранённые 9 `monitor_report.json` + `experiment.json` + `before_clear-board.png`/`after_draw-board.png` и однозначный run/session binding; отдельно определить frozen пиксельный mask/provenance protocol (не подгоняя пороги под итог), независимый образец native Egret WebGL на фактически принятых `accepted_points` и observed `smooth=true` (не подставлять plan endpoints), количественно оценить per-run raster overlap, leakage, missing/endpoint errors и cross-check SHA. Проблема полной temporal ordering и отдельного live `normal` контроля остаётся открытой. **Итог: E4 PASS 9/9; E5 PARTIAL (geometry + screen-only RGB agreement), native Egret pixel E5 NOT_RUN; ENGINE-001 PARTIAL.** Старый FILL-001 `FAIL` (98.430600%/11) не переоценивается и пороги не меняются.

## 22. ENGINE-001 — независимый native Egret Stage E5 screen-RGB replay (2026-11-08)

**Protocol:** `ENGINE001_E5_NATIVE_SCREEN_V1` · E4 frozen source `177165361b0340515fe3bb74f4847ab3ec579ebc` · Research code/test SHA `6810f75dfb87c8eaac7e73eb9d1063291660c104` · [E5 CI 42454224181](https://github.com/Kiddos19882/AutoDraw/actions/runs/42454224181) **SUCCESS** · [native A–D PNG](https://github.com/Kiddos19882/AutoDraw/actions/runs/42454224181/artifacts/13606972733) · [9 per-run reports, masks, overlays and raw provenance](https://github.com/Kiddos19882/AutoDraw/actions/runs/42454224181/artifacts/13607535199). В CI 18 Node tests PASS и 24 Python renderer acceptance tests PASS. Перепроверен ZIP 2384 файлов, без ошибок CRC/ZIP integrity; хеш исходного immutable journal SHA-256 `fd8270b38e0f14a297cc62405837ff825537e0b0ecb3765d1c671eed0aa007fa`.

**Критерий (до окончательной оценки):** не менять действующие DEC-025 limits (IoU/precision/recall ≥0.92, symmetric-difference/live ≤0.087, bbox edge tolerance 8% min1px, formal RGB delta >24). Каждая из 9 tasks должна сохранять run/session/experiment, exact accepted-point stream, observed smooth=true, same-run geometry и исходные PNG/SHA. Variant A — native `WebGLRenderer` на Stage backing 3942×1800 с дробным origin около 1022.375,216 backing px; B — округлённый WebGL; C/D — Canvas2D controls. Stage→screen CSS transform берётся из текущего Monitor, проверяется независимым board-to-screen fit и full-screen bounds, post-hoc translation не применяется. Native alpha и live RGB рассматриваются **раздельно**: у live screenshot нет исходного нативного alpha-канала.

| Cell | Run prefix | Exact CHALK | A IoU screen RGB24 | A TP / live-only FP / model-only FN | Outcome |
|---|---|---:|---:|---:|---|
| H1 | `79211ae0` | 108 | 0.998995 | 6957 / 7 / 0 | PASS_PER_RUN |
| H2 | `23de82a3` | 108 | 0.998995 | 6957 / 7 / 0 | PASS_PER_RUN |
| H3 | `cc279753` | 108 | 0.999281 | 6946 / 5 / 0 | PASS_PER_RUN |
| V1 | `7da99bf3` | 60 | 0.940508 | 3889 / 246 / 0 | PASS_PER_RUN |
| V2 | `86d863ca` | 60 | 0.940694 | 3902 / 246 / 0 | PASS_PER_RUN |
| V3 | `4c0a87c4` | 61 | 0.940241 | 3902 / 248 / 0 | PASS_PER_RUN |
| D1 | `d2fcb15b` | 113 | 0.983277 | 7526 / 123 / 5 | PASS_PER_RUN |
| D2 | `31922917` | 114 | 0.981740 | 7527 / 132 / 8 | PASS_PER_RUN |
| D3 | `310a004f` | 114 | 0.982561 | 7550 / 124 / 10 | PASS_PER_RUN |

**Итог:** 9/9 completed native comparisons, 9/9 `PASS_PER_RUN`, 0 rejected, 0 blocked по E5 **screen-RGB** gates. Все bbox edge differences прошли прежний scaled tolerance (для вертикальных линий model bbox начинается на 1 screen px правее live). Первичный [CI 42453831682](https://github.com/Kiddos19882/AutoDraw/actions/runs/42453831682) сохранил **9/9 `REJECTED_PER_RUN`**: диагностическая функция `mask_metrics` не передавала `observed_bbox_xywh` / `expected_bbox_xywh`, несмотря на рассчитанные IoU; это schema/acceptance instrumentation issue, не новый игровой FAIL. В коммите `6810f75` добавлены обязательные bbox и regression test, сами маски, raw data и пороги не менялись; повторный CI подтвердил 9/9 PASS.

**Дополнительная E5 диагностика (не acceptance):** в серии вертикальных live-only FP сосредоточены по левому столбцу экранной BoardPane области (V1: 241 из 246 в локальном x=325; V2 241/246; V3 243/248). Для IoU контрольных B (rounded WebGL) среднее по H/V/D ~0.998372/0.939275/0.979617, у дробного A ~0.999090/0.940481/0.982526; A также практически совпадает с C в H/V и отличается от C на ~0.000262 IoU в D. Это поддерживает необходимость Stage-level phase-aware screen projection, но **не доказывает** причину предыдущих FILL-001 misses. Принятые coordinates используют реальные `accepted_points`, не запланированные endpoints.

**Границы:** CI renderer — Firefox software `ANGLE (Microsoft Basic Render Driver)`, не подтверждена hardware pixel identity с live GPU пользователя. Native backing alpha-mask не может быть прямо сравнена с alpha live screen (live RGB screenshots не содержат нативного alpha). Same-run final PNG не раскрывает весь temporal ordering `ENTER_FRAME → actual render` или отсутствующий отдельный live `normal` control. Поэтому **E5 screen-RGB PASS в рамках 9 runs**, но **ENGINE-001 overall PARTIAL**; FILL-001 исторический `FAIL` 98.430600% coverage/11 leaked screen px и exact CHALK 1260 остаются без переоценки. Дальнейшая работа — отдельно определить способ наблюдения фактических render frames/native alpha без создания новых production предположений.


## 23. FILL001-SERIES-001 — native Egret replay шести игровых фигур (2026-11-13)

**Протокол:** `FILL001_SERIES_EGRET_REPLAY_V1`, `FILL001_SERIES_EGRET_COMPARISON_V1`. Frozen source commit `3f67c05d8dfd2f4db8954063850bd67b96232dd1`, series `fill001-series-3e1fd32c4d99`, session `e04234bc-b9ee-4d06-bd20-f1e13b8423ba`; рабочая ветка `feature/image-geometry-optimization`. Исследовательский код/test SHA `61251c4050fc31ffb0bf43c661fb0e6386290750`; [dedicated GitHub Actions 43431139220](https://github.com/Kiddos19882/AutoDraw/actions/runs/43431139220) **COMPLETED SUCCESS**: JavaScript **19/19 PASS**, проверка всех шести первичных Monitor JSON/blob hash/PNG SHA/Stage6 bindings PASS, native Firefox Egret 5.4.1 WebGL 6/6 PNG render и screen ROI comparison PASS как выполнение диагностики. [ZIP со всеми 6 парами игровых PNG, native Stage, проекциями, overlays и manifest](https://github.com/Kiddos19882/AutoDraw/actions/runs/43431139220/artifacts/14039378366), [source validation](https://github.com/Kiddos19882/AutoDraw/actions/runs/43431139220/artifacts/14039533387).

**Реализация:** opt-in `?fill001series=3e1fd32c4d99&figure=c001-f001` и остальные пять вариантов в существующем [game_renderer_reference.js](../tests/game_renderer_reference.js) — *тот же* реальный `BoardPane`, `BlackBoardAtom`, `Egret WebGLRenderer`, не второй raster engine. Browser получает frozen original `game-monitor-run-*.json`. Первая independent фаза [run_fill001_series_egret_replay.py](../tests/run_fill001_series_egret_replay.py) читает Monitor **через `git show HEAD:<path>`**, а не через Windows CRLF working tree, проверяет pinned original Git blob SHA, run/session ID, bound CHALK, PNG SHA-256 и preflight native BoardPane mapping; ни один raw файл не перезаписывается. В реконструкцию входят лишь реальные `DRAW_SAMPLE` / `accepted_points` (normal, `smooth=false`, radii 1/5/10); slider-only без расхода исключён; у QUOTA_LIMITED используются **только исполненные штрихи**, не оставшиеся части плана.

**Фиксированная метрика:** native Egret Stage backing **5096×2400, canvasScale 4**, fractional Stage origin из same-run geometry → desktop BoardPane ROI **694×363**, screen corners и screenshot cropping из Stage6/verified passive witnesses. Pillow `BILINEAR` affine для постоянного Stage→screen mapping, **никакой подстройки сдвига по результату**. Live mask = `max(abs(game_after.RGB - game_before.RGB)) > 24`; native model mask = screen-projected Stage alpha **≥24**. Это диагностика RGB difference versus native alpha, не сравнение live/native RGBA на одном backing framebuffer. IoU и precision/recall — метрики mask overlap, **не** FILL-001 target coverage.

| Figure / status | Exact original CHALK | Missing accepted coordinates | Screen IoU | Live-only / model-only pixels |
|---|---:|---:|---:|---:|
| C1-F1 rectangle/r1 · QUOTA_LIMITED (100/141) | 5759 | 0 | **0.99944789** | 0 / 40 |
| C1-F2 wide_irregular/r5 · QUALITY_FAIL (37/37) | 1971 | 0 | **0.99471218** | 478 / 57 |
| C1-F3 narrow_irregular/r10 · QUOTA_LIMITED (161/211) | 5741 | **1** | **0.99165643** | 347 / 312 |
| C2-F1 rectangle/r1 · QUOTA_LIMITED (100/141) | 5752 | 0 | **0.99944789** | 0 / 40 |
| C2-F2 wide_irregular/r5 · QUOTA_LIMITED (108/145) | 5767 | **1** | **0.99307425** | 465 / 65 |
| C2-F3 narrow_irregular/r10 · QUALITY_FAIL (43/43) | 1528 | 0 | **0.99601157** | 85 / 319 |

**Полный Windows CI:** [43431139227](https://github.com/Kiddos19882/AutoDraw/actions/runs/43431139227) на code/test SHA `61251c4050fc31ffb0bf43c661fb0e6386290750` завершился SUCCESS: обязательные Preparation/G3, app integration, Game Monitor/Bridge, Egret browser, executor и INT-006 PNG jobs все SUCCESS; optional benchmarks и portable build SKIPPED.

**Независимая повторная проверка:** скачан оригинальный ZIP данного CI; локальный Python/Pillow+NumPy отдельно декодировал `game-before.png`, `game-after.png`, `egret-screen-projected.png` по каждой фигуре и заново вычислил бинарные маски, TP, live-only, model-only и IoU по замороженным порогам. Все 6/6 результатов **побитово/численно совпали с JSON отчётом по метрикам**. Отдельно независимо подсчитаны цветовые пиксели `pixel-diff.png`, также 6/6 совпали. Это **независимый PNG-only E5 пересчёт данных из завершённого CI**, а не независимое воспроизведение рендера на аппаратном GPU или повтор live игры.

**Неопределённости / fail-closed:** в C1-F3 и C2-F2 есть по одному `DRAW_SAMPLE.pointDelta=2` с только одной координатой `acceptedPoint`; `sum(point_delta)` строго совпадает с exact CHALK, но **одна игровая координата не восстановима из принятого потока**, поэтому `DIAGNOSTIC_MISSING_ACCEPTED_COORDINATES`, не pixel-exact. Строгая первичная проверка всех шести SHA PASS не превращает две приближённые PNG-проекции в полные E5. Остальные четыре имеют полный список принятых координат, но оригинальный frame ordering/raster timing и GPU пользователя не воспроизводились. Для измерения сохранённых изменений не менялись E4 PNG, реальные CHALK, quality thresholds, radius selection, production estimator или Stage6 executor. Старые QUALITY_FAIL/QUOTA_LIMITED не переоцениваются в PASS; coverage оригинальных wide/narrow completed остаётся ниже 99%.

**Следующий gate:** установить происхождение двух ненаблюдаемых точек без подмены данных, проверить направление остаточных screen-only pixel differences на независимых captured geometries, затем провести отдельную E5 validation с подтверждённой версией браузерного renderer и наблюдением native alpha/temporal. Данная серия доказывает высокую screen-mask согласованность **только шести конкретных архивных рисунков**, не универсальную гарантию точности будущих рисунков.

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

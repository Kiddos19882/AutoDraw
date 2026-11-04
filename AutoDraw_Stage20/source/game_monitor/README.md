# Game Monitor 0.2.2

Диагностический DevTools-наблюдатель для браузерной игры AutoDraw. Он не отправляет игровые команды и не управляет мышью, но временно оборачивает методы экземпляра BoardPane; поэтому называть его полностью пассивным или неинвазивным до проверки overhead и восстановления методов нельзя.

## Телеметрия входа и принятых координат (0.2.2)

Во время активного штриха Monitor дополнительно записывает `MOUSE_MOVE_SAMPLE` для DOM `mousemove`, полученного canvas игры. Listener установлен на window в bubble phase: в согласованном Egret 5.4.1 bundle WebTouchHandler регистрирует `mousemove` непосредственно на canvas, поэтому window listener выполняется после canvas handler. Событие содержит DOM `timeStamp`, client/page/screen coordinates, movement/buttons, текущие `stage.mouseX/Y` и координаты после `BoardPane.globalToLocal()`. Это события, реально доставленные браузером, а не все вызовы `pyautogui.moveTo()`: события, объединённые или отброшенные до доставки в DOM, из них восстановить нельзя.

`POINT_QUOTA_UPDATE` теперь дополняется `pointDelta`, `acceptedPoint` и текущими stage/BoardPane-local координатами, когда точный `pointCount` увеличился. Это связывает точную точку, принятую игрой при `updateLess()`, с координатой указателя и временной меткой того же вызова.

`DRAW_SAMPLE` остаётся polling-событием с интервалом 25 мс и может объединить несколько обновлений; оно не является полным input stream. `frame_probe` измеряет browser requestAnimationFrame, а не Egret `ENTER_FRAME`. Для анализа повторных одинаковых траекторий сопоставлять DOM mousemove, POINT_QUOTA_UPDATE, acceptedPoint и frame_probe, не смешивая эти частоты.

## Источник сведений об игре

**Историческая основа раннего анализа Monitor:** `AutoDraw_Stage20/fileGameEngine/main.min_570122a1.js` из `master`, SHA-256 `df5a411e91010cd59f010a78a460baf3bd6d2af36816cb2e73c9de5070762b3d`. Этот bundle не является текущим источником идентификации runtime.

**Текущий подтверждённый набор для статического анализа:** `AutoDraw_Stage20/gameEngine/main.min_653f95bc.js`, `mergeEngine_df2e5bc5.js`, `manifest.json` — пользователь подтвердил, что все три файла скачаны с сайта запущенной игры одновременно. В merge bundle статически указана версия Egret 5.4.1. Подробная трассировка кисти находится в [engine report, раздел 14](../../docs/CHALK_GAME_ENGINE_POINT_COST_AND_BRUSH_WIDTH_2026-11-03.md#14-полная-трассировка-цепочки-игровой-кисти-и-границы-воспроизведения--2026-11-04).

Game Monitor ориентируется на исследованные методы `BoardPane`: `onDrawStart`, `onDrawing`, `onDrawingEnd`, `setRadius`, `updateLess`, а также на `atom.points`. Runtime snapshot пользователя от 2026-11-04 подтвердил для одной сессии `renderMode=webgl`, Egret 5.4.1 и stage→client transform; полный raw snapshot сохранён в [`../../data/runtime/renderer_snapshot_2026-11-04.json`](../../data/runtime/renderer_snapshot_2026-11-04.json). Это evidence одной сессии, а не универсальная калибровка. BoardPane имеет внутренний логический размер 460×240. Это не физический размер доски на клиентском экране и не ограничение для screen ROI AutoDraw: клиентский BoardPane отображается в масштабе, а фактические пиксельные размеры ROI зависят от viewport, окна и браузера и определяются отдельной калибровкой (например, сохранённые INT006R PNG имели 581×304 px). Не подгонять клиентскую доску под 460×240; AutoDraw должен преобразовывать logical coordinates в фактический calibrated ROI. Клиентский код сам добавляет точки и перерисовывает доску во время активного штриха; сервер не участвует непосредственно в обработке движения и перерисовке. Последующее сохранение/синхронизация — отдельный процесс.

## Снимок renderer и преобразований — runtime diagnostics

После загрузки `game_monitor.js` в **игровом iframe** выполните:

```js
const snapshot = AutoDrawGameMonitor.inspect();
console.log(JSON.stringify(snapshot, null, 2));
```

`inspect()` сохраняет прежние поля (`boardDetected`, `snapshot`) и добавляет объект `renderer`. Его также можно получить отдельно через `AutoDrawGameMonitor.rendererSnapshot()`.

Снимок собирает:
- фактические `egret.Capabilities.engineVersion` и `renderMode`, тип `systemRenderer`/`canvasRenderer`;
- `DisplayList` canvas scale factors, `devicePixelRatio` и `visualViewport.scale`;
- для каждого `.egret-player`: stage dimensions/frameRate/scaleMode, player options, canvas intrinsic/client dimensions, `getBoundingClientRect()`, CSS transform и transform origin;
- display-object chain BoardPane→родители, concatenated matrices, scrollRect, маску и углы доски в stage coordinates;
- `canvas.screenQuad` и `boardClientCorners`, если браузер предоставляет `Element.getBoxQuads()`.

`boardClientCorners` выражены в **CSS client pixels** относительно viewport, не в физических пикселях screenshot. `devicePixelRatio` и `visualViewportScale` сохраняются отдельно. В snapshot 2026-11-04 оба quad-поля равны `null`; вычисленные по axis-aligned CSS matrix client corners описаны в engine report §15.3 и не выдаются за прямой quad capture. Если `getBoxQuads()` отсутствует или вызов недоступен, `screenQuad` и `boardClientCorners` будут `null`: не выводите точное экранное преобразование только из axis-aligned bounding rectangle, особенно при повороте canvas.

`inspect()` и `rendererSnapshot()` сами по себе выполняют read-only чтение и не меняют `renderMode`, доску, кисть или игровые данные. Однако важно различать вызов метода и загрузку всего файла: в текущем `game_monitor.js` в конце IIFE вызывается `start()`, поэтому сама инъекция скрипта автоматически запускает Monitor, устанавливает input observers/PerformanceObserver, периодический scan timer и wrappers методов BoardPane. Это не побочный эффект `inspect()`, а поведение инициализации всего Monitor. После разового снимка, если непрерывное наблюдение не нужно, вызовите `AutoDrawGameMonitor.stop()`. Snapshot не измеряет footprint кисти и не подтверждает pixel equivalence.

Сохраните полный JSON `inspect()` и передайте его для анализа. Запускать CHALK/brush live experiment для этого снимка не требуется.

## Подключение

1. Откройте игру в Chrome или Edge и дождитесь появления доски.
2. Нажмите F12 → Console.
3. Откройте файл `game_monitor.js` в репозитории, скопируйте весь текст и вставьте в Console.
4. Разрешите вставку кода в DevTools, если браузер попросит (не включайте это разрешение для неизвестного кода).
5. После вставки проверьте ответ и выполните:

```js
AutoDrawGameMonitor.status()
```

В версии 0.2.2 статус содержит `frameContext` и O(1) `snapshot` с точными ресурсными полями, если движок их предоставляет. Для правильного запуска `isTopFrame` должен быть `false`, а `currentFrame` должен указывать на `eufbpet.hust.me`. Если `isTopFrame: true`, выбран верхний документ и поиск доски там не сработает. Если после запуска внутри iframe `boardDetected` всё ещё `false`, сохраните JSON — тогда будем исследовать структуру уже правильного контекста. Автопоиск использует `window.egret.MainContext.instance.stage` и обходит display list.

## Управление

```js
AutoDrawGameMonitor.status()       // текущее состояние и O(1) CHALK snapshot
AutoDrawGameMonitor.inspect()      // read-only checkpoint без attach/wrappers
AutoDrawGameMonitor.export()       // получить объект с телеметрией
AutoDrawGameMonitor.download()     // скачать JSON
AutoDrawGameMonitor.clear()        // очистить буфер событий
AutoDrawGameMonitor.stop()         // остановить и восстановить методы BoardPane
AutoDrawGameMonitor.start()        // снова запустить наблюдение
```

Для ручного подключения, если BoardPane найден в DevTools вручную:

```js
AutoDrawGameMonitor.attach(boardPaneInstance)
```

## Что фиксируется

- обнаружение/отключение BoardPane;
- начало и завершение штриха;
- изменение радиуса через `setRadius`;
- изменения числа сохранённых координат во время `onDrawing`;
- вызовы `updateLess`;
- O(1) ресурсный снимок из `BoardPane.max`/`BoardPane.less`, включая текущий фактический `currentRadius`; `DRAW_SAMPLE` дополнительно фиксирует `pointDelta` и последнюю принятую координату `acceptedPoint` через O(1) чтение хвоста текущего штриха; полный подсчёт точек доступен только через явный `diagnosticSnapshot()`;
- Resource Timing entries страницы (пассивно, без изменения запросов); query-параметры, похожие на токены/секреты/идентификаторы сессии, маскируются.

События буферизуются в памяти и выгружаются одним JSON. Событие `DRAW_SAMPLE` создаётся при изменении точного `pointCount`/остатка, а не при каждом кадре. Поле `pointDelta` показывает число новых точек с прошлого наблюдения; `acceptedPoint` содержит последнюю точку только при положительной дельте. Если `pointDelta > 1`, промежуточные координаты могли быть объединены polling-наблюдением, поэтому событие не является полной траекторией. `POINT_QUOTA_UPDATE` не создаётся, если вызов `updateLess()` не изменил `max`/`less` (например, повторная координата была отклонена игрой).

## Ограничения прототипа

- Это диагностический DevTools-snippet, а не расширение браузера и пока не интеграция с AutoDraw.
- Он не управляет мышью, кистью, сетью или состоянием доски.
- В игровом bundle установлен источник индикатора CHALK: `BoardPane.updateLess()` считает точки `atom.points`, вычисляет `less = max - pointCount` и отправляет `percent = less / max`. Это квота игровых точек, а не площадь краски или длина пути. Monitor 0.2.0 читает точные целые `BoardPane.max` и `BoardPane.less`; `pointCount = max - less`. Если поля отсутствуют или невалидны, snapshot помечается `unavailable`, без сканирования массива как fallback. Анализ изменённых пикселей остаётся отдельной метрикой геометрии.
- Resource Timing показывает завершённые ресурсные операции, но не доказывает отсутствие всех типов сетевой активности. Он не перехватывает и не меняет fetch/XHR.
- Автопоиск зависит от доступности Egret stage и структуры display list. Если объект не найден, нельзя считать монитор подключённым.
- В семи сохранённых Monitor JSON для горизонтальных/вертикальных серий указаны `boardDetected=true`, `droppedEvents=0`, `errors=0`. Это подтверждает работу сбора событий в тех прогонах, но не подтверждает отсутствие влияния на FPS, корректность attach/detach и полноту привязки к манифестам. В этих семи манифестах `game_monitor_report_path` не заполнен.
- Нельзя использовать результаты для калибровки или считать влияние Monitor нулевым до проверки координат и сравнения с запуском без Monitor.


Во время активного штриха Monitor сохраняет polling с интервалом 25 мс как резерв на случай, если Egret зарегистрировал ссылку на `onDrawing` до установки wrapper. Polling читает только `max`/`less` за O(1), а координату последней принятой точки получает чтением хвоста массива только при увеличении `pointCount`; полного обхода `atom.points` в hot path нет.


Для определения окна активного ввода прототип также слушает `pointerdown`, `pointerup` и `pointercancel` в capture-фазе, только если событие пришло с HTML canvas. Эти события помечаются как `*_CANDIDATE`: canvas может содержать и элементы интерфейса, поэтому сам pointerdown не считается доказательством рисования. Изменения `atom.points` в этом интервале дают подтверждение фактической активности доски. Все обработчики удаляются при `stop()`.


## Защита выгрузкиMonitor 0.1.2 маскирует значения query-параметров, чьи имена содержат `token`, `auth`, `session`, `cookie`, `secret`, `key` или `uid`/`user`, в URL Resource Timing. Не публикуйте сырые сетевые журналы и проверяйте экспорт перед передачей.

## Уточнение по CHALK и границам пассивности — 31 октября 2026 г.

Игровой bundle анализировался отдельно, без исполнения. Точная формула внутреннего счётчика: `less = max - количество точек atom.points`; UI получает долю `less / max`. Точки добавляются в игровом цикле `ENTER_FRAME`, только если координата внутри доски и отличается от предыдущей. Поэтому длина пути и число точек не взаимозаменяемы; скорость указателя влияет на sampling.

В Monitor 0.1.2 ресурсный `pointCount` получался сканированием `atom.points`, а hot path создавал дополнительные O(N)-проходы. В версии 0.2.0 эти проходы убраны из `emit()`, wrappers, polling, `status()` и `export()`: используется `BoardPane.max`/`less`. Влияние на FPS и восстановление descriptors требует отдельного runtime/A-B подтверждения.

CI проверяет синтаксис `node --check` и поведенческие Node.js тесты `source/game_monitor/tests/game_monitor.test.js`. Python tests в `tests/test_websocket_smoke_server.py` по-прежнему проверяют только отдельный transport smoke server.


## Низконагрузочный CHALK snapshot — проектное уточнение INT-002 (31.10.2026)

В версии 0.1.2 `pointCount` вычислялся рекурсивным обходом `atom.points`, а `emit()`, wrappers и polling повторяли O(N)-проходы. В версии 0.2.0 обычная телеметрия использует O(1) `resourceSnapshot()` из `BoardPane.max`/`BoardPane.less`; полный обход оставлен только в явном `diagnosticSnapshot()`.

Это требование реализовано в 0.2.0: обычная телеметрия использует O(1) ресурсный снимок из проверяемых полей; диагностический O(N) обход вызывается только явно через `diagnosticSnapshot()`. Статический bundle подтверждает, что конструктор `BoardPane` устанавливает `this.max`/`this.less`, а `updateLess()` обновляет `this.less = this.max - pointCount`. Runtime-сверка доступности и соответствия диагностическому подсчёту в живом iframe остаётся обязательной. Payload CHALK содержит `percent`, но Monitor не использует его для восстановления целого остатка.

Фактический расход прогона должен считаться дельтой между `pre_test` (после подтверждённого Clear) и `post_test` (до следующего Clear). Все калиброванные модели AutoDraw остаются оценками и не подменяют прямой игровой счётчик.

Статический анализ подтверждает лишние обходы, но не количественное падение FPS. Влияние Monitor проверяется отдельным A/B-тестом без Monitor и с Monitor 0.1.2.

## Game Monitor 0.2.0 — INT-003 (31.10.2026)

В клиентском bundle статически подтверждено:
- конструктор BoardPane: `this.max=n`, `this.less=this.max`;
- `updateLess()`: полный внутренний подсчёт `atom.points`, затем `this.less=this.max-e`;
- событие CHALK содержит `percent=this.less/this.max`, но точные целые значения остаются в полях экземпляра.

Game Monitor 0.2.0 использует `resourceSnapshot()` для чтения `max`/`less` за O(1). `pointCount=max-less`. `emit()`, wrappers, polling, `status()` и `export()` не обходят `atom.points`. Полный диагностический обход доступен только по явному вызову `AutoDrawGameMonitor.diagnosticSnapshot()`; он возвращает `diagnosticPointCount` и `pointCountMatches`.

Добавлены автоматические Node.js тесты в `source/game_monitor/tests/game_monitor.test.js`, запускаемые в GitHub Actions. Они проверяют exact snapshot, отсутствие array scan в hot path, отказ без fallback при недоступных полях, point delta и восстановление метода после stop.

**Ограничение:** поля подтверждены статически в bundle. Живая проверка на BoardPane в игровом iframe и A/B-измерение FPS/длительности ещё не выполнены. Не считать версию 0.2.0 измеренно без overhead до получения результатов A/B.


### Контрольная точка без активного Monitor (режим A)

Для A/B/C сравнения можно загрузить snippet и сразу остановить активное наблюдение:

```js
AutoDrawGameMonitor.stop()
AutoDrawGameMonitor.inspect()
```

После `stop()` методы BoardPane восстановлены, polling и input handlers сняты. `inspect()` находит BoardPane по запросу, читает только `max`/`less` и возвращает snapshot без attach, wrappers, timers или постоянного наблюдения. Вызывайте его только на контрольных точках до/после штриха. Это даёт одинаковый read-only способ снять точный счётчик в режиме A; он не должен работать во время самого штриха.

В режиме B оставляйте Monitor 0.1.2 активным, в режиме C — Monitor 0.2.2; используйте `status().snapshot`; после каждого контрольного снимка можно вызвать `diagnosticSnapshot()` для проверки `pointCountMatches`. Не вызывайте диагностический O(N) обход в процессе рисования.


### Уточнение механики игровых точек

`BlackBoardAtom.pushPoint(t)` добавляет координату, только если текущий массив штриха пуст или координата отличается от последней (`!t.equals(lastPoint)`). Поэтому повтор одного и того же положения мыши в соседних кадрах не увеличивает CHALK. `onDrawing()` может вызывать `updateLess()` даже при отклонённой повторной координате; Monitor 0.2.1 не создаёт `POINT_QUOTA_UPDATE`, если `max`/ `less` не изменились. `setRadius()` меняет только значение в `atom.radius` и не пересчитывает/не увеличивает счётчик точек.


## Логическая и экранная геометрия Brush Test — 31 октября 2026 г.

Статическая проверка `MouseExecutor._screen_point()` показала, что текущая реализация прибавляет только origin экранной области к координате DrawingPlan и не применяет scaleX/scaleY. При этом `integrated_app.py::_get_brush_test_canvas_size()` возвращает ширину/высоту экранного ROI, а сценарии теста задают координаты в логическом диапазоне доски. Следовательно, единицы координат смешаны: экранная длина может отличаться от логической, а часть доски может оставаться неиспользованной.

Это не ошибка формулы CHALK и не доказывает ошибку чтения `max`/`less`. Первый этап преобразования реализован: Brush Test передаёт logical-план 460×240 через отдельный преобразователь в screen-local ROI; обычные local-планы не меняются. Unit-тесты добавлены. Live-проверка соответствия ROI, масштаба и граничного hit-test остаётся обязательной до запуска полной матрицы.

Граница доски требует отдельного решения: `build_brush_test_drawing_plan()` для `logical_board_pixels` разрешает включительные границы `0 <= x <= 460`, `0 <= y <= 240`; для `local_canvas_pixels` сохраняется обычная проверка `x < width`, `y < height`. Игровой `BoardPane.onDrawing()` использует `Rectangle.contains()`, который в Egret сравнивает правую/нижнюю границу включительно. Сценарий длинных линий заканчивается на x=420 и находится внутри логической доски 460×240. Live-проверка попадания в конкретный экранный ROI всё равно требуется.


## Запуск локального WebSocket smoke-server для Firefox

Этот сервер нужен только для проверки, может ли игровой HTTPS iframe в Firefox открыть WebSocket-соединение с локальным адресом. Он **не подключён к Game Monitor**, не получает игровые данные и не управляет игрой. Запускайте его отдельно от AutoDraw.

### Требования

- Windows PowerShell;
- Python 3.11 с launcher-командой `py`;
- доступ к репозиторию локально.

### 1. Узнать точный Origin игрового iframe

1. Откройте игру в Firefox и дождитесь загрузки доски.
2. Нажмите F12 → Console.
3. В переключателе контекста Console выберите именно игровой iframe (не верхнюю страницу).
4. Выполните:

```js
location.origin
```

Скопируйте результат целиком. Это должен быть только Origin вида `https://домен` (при наличии нестандартного порта он также входит в Origin), без пути, query и fragment. Не подставляйте домен по догадке.

### 2. Установить отдельную зависимость smoke-server

Откройте PowerShell в корне локального репозитория AutoDraw и выполните:

```powershell
py -3.11 -m pip install -r .\AutoDraw_Stage20\source\game_monitor\requirements-smoke.txt
```

Зависимость изолирована в `requirements-smoke.txt` и не нужна для обычного запуска AutoDraw.

### 3. Запустить сервер

В том же PowerShell, из корня репозитория, выполните команду, заменив адрес на фактический результат `location.origin` из игрового iframe:

```powershell
py -3.11 .\AutoDraw_Stage20\source\game_monitor\websocket_smoke_server.py --origin https://ВАШ-ФАКТИЧЕСКИЙ-ORIGIN
```

По умолчанию сервер слушает только `127.0.0.1:8765`. В терминале появятся адрес прослушивания, разрешённый Origin и одноразовый token. Оставьте окно PowerShell открытым. Token действует для одного подключения: не публикуйте его, не отправляйте в чат и не сохраняйте в репозитории.

Если порт 8765 занят, можно указать другой свободный порт параметром `--port 8766`; тогда в браузерном snippet ниже также замените порт на 8766.

### 4. Проверить соединение из игрового iframe

Вернитесь в Console Firefox, убедитесь, что выбран тот же игровой iframe, и выполните snippet ниже. Замените `PASTE_TOKEN_HERE` одноразовым token из локального терминала. Не отправляйте заполненный token кому-либо.

```js
(() => {
  const ws = new WebSocket("ws://127.0.0.1:8765");

  ws.addEventListener("open", () => {
    ws.send(JSON.stringify({
      type: "auth",
      token: "PASTE_TOKEN_HERE"
    }));
  });

  ws.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    console.log("AutoDraw smoke message:", message);

    if (message.type === "ready") {
      ws.send(JSON.stringify({
        type: "ping",
        nonce: "autodraw-bridge-smoke-test"
      }));
    }
  });

  ws.addEventListener("error", (event) => {
    console.error("AutoDraw smoke WebSocket error:", event);
  });

  ws.addEventListener("close", (event) => {
    console.log("AutoDraw smoke WebSocket closed:", event.code, event.reason);
  });
})();
```

**Ожидаемый результат в Console:**

- `{type: "ready"}`;
- `{type: "pong", nonce: "autodraw-bridge-smoke-test"}`;
- закрытие соединения с кодом `1000` и причиной `smoke test complete`.

После успешной проверки сервер остаётся запущенным, но одноразовый token уже использован. Остановите сервер сочетанием `Ctrl+C`. Для нового прогона запустите сервер заново и используйте новый token.

### 5. Если тест не прошёл

- `Connection refused`: проверьте, что сервер запущен и порт в URL совпадает с портом сервера.
- Ошибка Origin / handshake: повторно проверьте `location.origin` именно в игровом iframe и аргумент `--origin`; Origin должен совпадать точно.
- `4003 authentication failed`: token неверный, устарел или уже был использован; перезапустите сервер и возьмите новый.
- Нет `ready`/ `pong`: сохраните полный текст ошибок Console и вывод терминала. Не обходите CSP и не меняйте политику безопасности браузера ради прохождения теста.

После проверки остановите сервер через `Ctrl+C`. Успешный ping/pong подтверждает только доступность локального WebSocket транспорта из данного iframe в данном профиле Firefox. Это не production bridge и не подтверждает связь Game Monitor с AutoDraw. До реального успешного теста статус транспорта остаётся `not_tested`.


## Автоматический сбор телеметрии тестов кисти через WebSocket

Добавлен production-путь сбора read-only телеметрии. В отличие от `websocket_smoke_server.py`, новый bridge получает события Game Monitor, CHALK snapshots, принятые координаты и FPS во время штрихов и сохраняет отдельный JSON для каждого непрерывного прогона.

### Что потребуется один раз на браузерную сессию

1. Установить изолированную зависимость:
```powershell
py -3.11 -m pip install -r .\AutoDraw_Stage20\source\game_monitor\requirements-bridge.txt
```
2. В Firefox получить `location.origin` в Console именно игрового iframe.
3. Из корня репозитория запустить:
```powershell
py -3.11 .\AutoDraw_Stage20\source\game_monitor\game_monitor_bridge_server.py --origin https://ФАКТИЧЕСКИЙ-ORIGIN
```
Сервер слушает только `127.0.0.1:8765`. Можно задать `--port`, `--output-dir` и `--idle-seconds`.
4. В том же iframe сначала загрузить актуальный `game_monitor.js` (0.2.2), затем вставить полный snippet, напечатанный bridge-сервером. Snippet содержит секретный токен; не публиковать его и не сохранять в репозитории.

После подключения пользователь больше не должен вручную вызывать `status()`, `export()` или `download()` для каждого прогона. Сбор начинается автоматически при `DRAW_START`; непрерывная серия штрихов объединяется в один run, а завершение фиксируется после `DRAW_END` и интервала бездействия. Время бездействия настраивается параметром `--idle-seconds` (по умолчанию 2.5 секунды).

### Автоматически сохраняемые данные

Каждая сессия создаёт каталог с UUID внутри `data/results/brush_behavior_tests/game_monitor_bridge/`:

- `session.json` — браузер, iframe, исходный status Monitor и ID сессии;
- `game-monitor-run-*.json` — отдельный прогон: pre/post CHALK snapshots, фактическая дельта точек, радиус, события, принятые точки, оценка наблюдаемой длины траектории, длительность активных штрихов и FPS.

CHALK считается точным только если pre/post snapshots содержат валидные целые `maxPoints`, `remainingPoints`, `pointCount`, имеют одинаковый лимит и неотрицательную дельту. В противном случае результат получает статус `inconclusive`.

FPS снимается через requestAnimationFrame только во время каждого активного штриха. В отчёте отдельно сохраняются число кадров, средний/медианный FPS и median/P95/max интервал кадра. Это измерение само добавляет небольшой наблюдательский overhead; сравнивать результаты следует при одинаково включённом bridge.

Длина пути строится только по реально принятым `acceptedPoint`. Если хотя бы один `pointDelta > 1` или отсутствует точная координата, траектория помечается как неполная; вычисленная длина является нижней границей, а не полной длиной пути.

### Границы и безопасность

- Сервер принимает только точный HTTPS Origin, слушает loopback, требует случайный токен и допускает одно активное браузерное соединение.
- Bridge принимает только ограниченный набор типов событий и не отправляет команды в игру.
- Bridge не вызывает `clear()`, `stop()`, игровые методы, eval или управление мышью.
- При потере соединения незавершённый run сохраняется со статусом `partial`.
- Brush Test UI автоматически ищет подходящий run по времени старта относительно `before_draw` и фактическому радиусу, копирует его в папку эксперимента как `monitor_report.json` и записывает `session_id`, `run_id`, CHALK, FPS и статус в `experiment.json`. Для этого оставляйте `--output-dir` по умолчанию либо указывайте тот же каталог, который использует UI.
- Live-соединение из реального Firefox iframe и CI-проверки — разные уровни подтверждения. После первой установки обязательно проверить появление `session.json` и run JSON в указанном каталоге.


## Автоматическая обратная связь радиуса Brush Test

Game Monitor Bridge отправляет heartbeat с результатом `AutoDrawGameMonitor.status()` раз в секунду. Сервер сохраняет последний статус в `session.json` (`bridge_diagnostics.last_monitor_status`) и timestamp последнего сообщения.

Brush Test UI и основной Stage6 executor используют только свежий heartbeat активной сессии, полученный после отпускания ползунка; для подтверждения используются два последовательных heartbeat с новым timestamp и одинаковым радиусом. Фактический радиус берётся из `snapshot.currentRadius` (с резервным чтением последнего элемента `snapshot.radius`). UI не считает координату мыши подтверждением радиуса.

Если фактический радиус отличается от заданного, UI/контроллер вычисляет следующую позицию по ограниченному secant-интервалу между известными точками радиусов 30 и 1, повторно перетаскивает ползунок и проверяет новый heartbeat. Максимум — 7 коррекций. Запуск рисования разрешён только при точном совпадении. При отсутствии свежего heartbeat, ошибке чтения или исчерпании коррекций исполнитель не запускается.

Для автоматической установки кисти Game Monitor Bridge должен быть подключён в том же игровом iframe и писать в стандартный каталог `data/results/brush_behavior_tests/game_monitor_bridge/`.


## Запуск WebSocket из интерфейса AutoDraw

В разделе **«Тест кистей»** добавлены три действия:

1. **Запустить сокет** — запросит точный HTTPS Origin игрового iframe (значение location.origin) и откроет отдельное окно Windows с локальным collector.
2. **Копировать game_monitor.js** — копирует полный актуальный исходник Monitor из текущей сборки AutoDraw.
3. **Копировать snippet подключения** — копирует snippet с одноразовым токеном, созданным запущенным сервером.

Порядок подключения в Firefox:

1. Открой игру, дождись доски и в Console выбери контекст именно игрового iframe.
2. Выполни location.origin и скопируй результат.
3. В AutoDraw на странице «Тест кистей» нажми **«Запустить сокет»** и вставь Origin. Оставь открытым отдельное окно сервера; дождись сообщения Listening.
4. Нажми **«Копировать game_monitor.js»**, вставь код в Console iframe и выполни.
5. Нажми **«Копировать snippet подключения»**, вставь его в ту же Console и выполни.
6. Убедись, что Console сообщает о подключении Bridge, а в окне сервера появляется активная сессия.

Snippet с токеном создаётся в каталоге результатов и доступен для копирования, пока сервер работает. При штатной остановке сервера временный файл удаляется. Не публикуй snippet и не сохраняй его в проекте: он содержит одноразовый секретный токен. Для остановки сервера нажми Ctrl+C в отдельном окне.

Для самостоятельного запуска без интерфейса используй start_game_monitor_bridge.bat в этом каталоге. Файл запросит Origin, при необходимости установит только зависимость из requirements-bridge.txt, затем запустит тот же collector. Требуется Python 3.11 с launcher-командой py -3.11.


### Portable-сборка

При сборке Windows portable в корень папки AutoDrawPortable копируется каталог game_monitor со следующими файлами: game_monitor.js, game_monitor_bridge.js, game_monitor_bridge_server.py, requirements-bridge.txt, start_game_monitor_bridge.bat и README.md. UI определяет этот каталог относительно AutoDraw.exe. Для запуска companion server используются тот же каталог результатов data/results/brush_behavior_tests/game_monitor_bridge и тот же output directory, что и у Brush Test.


### Надёжность записи session.json на Windows

Bridge записывает session.json атомарно через уникальный временный файл и os.replace(). Если Windows временно блокирует целевой файл и os.replace() возвращает PermissionError (например, WinError 5), сервер выполняет ограниченные повторные попытки с экспоненциальной задержкой. Если блокировка не исчезает, WebSocket handler остаётся активным, ошибка отмечается в bridge_diagnostics.session_persist_failures, а сохранение повторяется при следующем сообщении. Прежний session.json не заменяется частичной записью. Временный файл очищается после каждой попытки.

## Диагностика переполнения Monitor и per-run integrity (2026-11-02)

Локальный массив событий Game Monitor ограничен `MAX_EVENTS=50000`. При достижении лимита новые события не попадают в `state.events`, а `state.droppedEvents` растёт. Это ограничение только локального export buffer: `emit()` продолжает вызывать подписчиков, поэтому Browser Bridge продолжает получать события. Ненулевой cumulative `monitor_dropped_events` не означает потери событий текущего run.

Bridge report разделяет:
- `monitor_buffer_dropped_events_start/end/delta` — cumulative overflow локального массива Monitor, только диагностика;
- `monitor_error_count_start/end/delta` — изменение счётчика Monitor errors за конкретный run;
- `bridge_send_failures_delta` — новые ошибки отправки browser bridge за run;
- `collector_sequence_gap_count` — число пропущенных sequence, замеченных collector во время активного run;
- `dropped_events` — события, не попавшие в ограниченный per-run список `RunRecorder`.

Collector проверяет монотонность sequence и отдельно считает gaps. Любой gap во время активного run считается потенциальной потерей сообщения и блокирует acceptance. Это консервативная проверка: sequence gaps включают пропущенные сообщения любого типа, не только game events.

Capture gate использует per-run `dropped_events`, `monitor_error_count_delta`, `bridge_send_failures_delta` и `collector_sequence_gap_count`. Старые cumulative aliases сохраняются для диагностики и обратной совместимости, но не отклоняют run сами по себе.

Regression coverage:
- Node test отправляет более 60 000 событий после заполнения локального буфера и проверяет, что подписчик получает все события;
- Python tests проверяют, что накопительный buffer overflow и старые Monitor errors не портят следующий run;
- WebSocket integration test моделирует sequence gap и проверяет, что он отражается в run report и session diagnostics;
- matrix validators принимают capture с cumulative buffer overflow, но отклоняют per-run bridge failures и collector sequence gaps.

Live Firefox/game test этим не заменяется. До успешного CI и локального preflight новый G3 не запускать.



## Per-stroke timing telemetry — 4 ноября 2026 г.

Browser Bridge связывает frame_probe с strokeId. Collector сохраняет исходные интервалы requestAnimationFrame и добавляет per-stroke summaries в Run JSON. Общий frame_probe summary остаётся для совместимости.

Дополнительно RunRecorder рассчитывает per_stroke_metrics из точных POINT_QUOTA_UPDATE before/after snapshots и событий начала/окончания штриха: pointCount delta, duration, accepted points/sec и медианный/p95 интервал между принятыми точками.

Важно: frame_probe — частота browser requestAnimationFrame, а не прямое измерение Egret ENTER_FRAME. Частота POINT_QUOTA_UPDATE — cadence принятых игровых точек. Эти величины нужно анализировать отдельно.

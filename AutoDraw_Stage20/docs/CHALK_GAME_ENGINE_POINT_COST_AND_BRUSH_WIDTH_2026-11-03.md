# Игровой движок: связь размера кисти и расхода CHALK

**Дата аудита:** 2026-11-03  
**Источник:** `AutoDraw_Stage20/fileGameEngine/main.min_570122a1.js` в `master`, добавлен commit `bd8815cfb5e8cdc3276d872c833adeb23bbf22ac`.  
**Ограничение:** это статический анализ клиентского bundle; фактическая форма следа всё равно требует проверки по PNG и live captures.

## 1. Как движок считает CHALK

В классе `BoardPane` метод `updateLess()` проходит по всем массивам `atom.points` и считает количество сохранённых точек:

`pointCount = Σ atom.points[stroke].length`

Затем рассчитывает остаток:

`less = max - pointCount`

Следовательно, exact расход между двумя snapshots:

`CHALK = post.pointCount - pre.pointCount`

В этом расчёте нет множителя радиуса, площади следа или длины траектории. Каждая принятая игровая точка увеличивает счётчик на одну единицу.

## 2. Как движок записывает точки

- `onDrawStart()` добавляет первую точку через `atom.pushPoint(...)`, затем обновляет ресурс.
- `onDrawing()` вызывается через `ENTER_FRAME`; если указатель находится внутри BoardPane, добавляется очередная точка и обновляется ресурс.
- `onDrawingEnd()` завершает текущую последовательность точек через `atom.add()`.
- Поэтому фактический расход зависит от количества точек, принятых игровым циклом. Он не обязан совпадать с числом координат, которые AutoDraw пытался отправить.

Game Monitor должен оставаться источником фактической принятой дельты. Плановая длина пути, количество отправленных move calls и визуальная площадь не заменяют `pointCount`.

## 3. Как размер кисти влияет на след

- `BoardPane.setRadius(value)` записывает значение в `atom.radius` текущего штриха.
- `BoardPane.redraw()` получает `atom.radius` и передаёт его в `graphics.lineStyle(value, color, 1, false)`.
- Следовательно, параметр, называемый в UI `radius`, в рендеринге передаётся как ширина линии Egret Graphics. Не следует без проверки трактовать его как математический радиус круга, для которого диаметр равен `2 × radius`.
- `Painter.drawSmoothLine()` строит сглаженный путь через midpoint/curveTo; `drawNormalLine()` использует lineTo. Оба варианта получают уже сохранённые точки и не меняют формулу CHALK.
- UI radius presets в bundle: 20, 14 и 7; slider ограничен диапазоном 1–30. Константа `BoardPane.BLACK_BOARD_LINE_RADIUS` равна 7.

## 4. Практический вывод для AutoDraw

1. Не вводить прямой радиусный коэффициент в формулу расхода CHALK.
2. Рассчитывать базовый расход через ожидаемое количество игровых точек, а подтверждать его по фактическому `pointCount`.
3. Использовать размер кисти для моделирования ширины следа и выбора траектории покрытия.
4. Экономия от большого размера возможна только тогда, когда planner действительно сокращает количество принятых точек при сохранении требуемого покрытия.
5. Для заполнения областей сравнивать одну и ту же frozen target mask, одинаковый критерий качества и exact CHALK.
6. Перед применением `brush_footprint_geometry.py` откалибровать соответствие game radius/line width и фактическому raster footprint, включая концы и повороты.

## 5. Связь с FILL-001

FILL-001 должен проверять не «сколько CHALK стоит один радиус», а «сколько качественно покрытой целевой площади достигается на одну принятую игровую точку/CHALK при данном размере кисти».

Большой радиус может выиграть за счёт меньшего количества параллельных траекторий. Но если он проходит ту же траекторию с тем же количеством принятых точек, прямой экономии от одного только изменения радиуса формула движка не предсказывает.

## 6. Состояние Git

- `main.min_570122a1.js` присутствует в `master`, но отсутствует в `feature/image-geometry-optimization`.
- `AutoDraw_Stage20/testImages/images.png` присутствует в обеих ветках с одинаковым blob SHA `fc9c984d15e9dda7d6511b01b5a88ca52ba2380f`; повторный перенос не требуется.
- Ветки diverged; merge/rebase не выполнялся. Engine bundle не копировался в feature branch.


## 7. Повторный разбор исходного bundle — 2026-11-04

**Источник:** master commit 9a3453aeb847b66041bc83d6f4a56ecaf33a993a; blob 28838e803dcc6f85efb13febd93cc9e0f5046ffc, размер 4 785 687 bytes. Bundle прочитан через GitHub Contents API; файл не переносился в feature branch. Это статический анализ конкретной версии, не runtime validation.

### 7.1 Приём координат и расход

- BoardPane.onDrawStart() сразу добавляет первую координату через atom.pushPoint(globalToLocal(stage.mouseX, stage.mouseY)), вызывает updateLess() и подписывается на ENTER_FRAME.
- BoardPane.onDrawing() на каждом ENTER_FRAME считывает текущие stage.mouseX/mouseY, переводит через globalToLocal, проверяет попадание в прямоугольник 0..width × 0..height и при попадании вызывает atom.pushPoint(), updateLess() и redraw(false).
- Игра делает максимум одну попытку добавления текущей позиции за кадр, а не одну точку на каждый pyautogui.moveTo.
- BlackBoardAtom.pushPoint() добавляет координату, только если текущий stroke пуст или координата не равна последней сохранённой. Повтор одинаковых соседних координат не расходует дополнительную точку.
- BoardPane.onDrawingEnd() снимает ENTER_FRAME listener, вызывает redraw(false) и atom.add().
- BoardPane.updateLess() заново обходит все массивы atom.points, считает их длины и задаёт less = max - count. Пересчёт — O(N) по накопленному числу точек на каждом принятом sample. Это потенциальный источник снижения frame rate на длинных запусках, но фактический эффект нужно проверить по per-stroke FPS probe.

### 7.2 Геометрия и сглаживание

- BoardPane.redraw() вызывает graphics.lineStyle(s, color, 1, false), где s — сохранённое значение atom.radius. Вызов содержит только четыре аргумента; caps/joints явно не задаются.
- Painter.drawSmoothLine() строит midpoints между соседними точками, использует curveTo() для сглаживания и в конце делает lineTo() к последней сохранённой точке.
- Для массива из одной точки smooth path выполняет moveTo(point) и lineTo(point) в ту же координату. Для drawNormalLine() с одной точкой выполняется только moveTo(point).
- Первая точка может быть учтена в CHALK до заметного перемещения указателя. Будет ли нулевой путь визуально окрашен, зависит от Egret renderer и настроек окончания линии; это не установлено по одному вызову Painter.
- Caps/joints не передаются из BoardPane.redraw(). В официальном Egret Engine 5.2.18 API (egret.d.ts) для Graphics.lineStyle задокументированы defaults CapsStyle.ROUND и JointStyle.ROUND; thickness описана как толщина линии в points. Поэтому round caps/joins — обоснованный ожидаемый default для совместимого Egret runtime. Но версия Egret, фактически загруженная игрой, не установлена, поэтому это пока не подтверждённый runtime факт. Поведение нулевого сегмента остаётся UNKNOWN.
- BlackBoardItem.createNativeContent() задаёт logical board 460×240 и вычисляет равномерный board.scaleX = board.scaleY = boardMask.width / 460. Это display scale доски внутри item, не painter popup. PainterPopup.setPopupUI(676,379) создаёт popup 676×379; createBlackBoard() создаёт интерактивный BoardPane 460×240 и не задаёт ему собственный scaleX/scaleY. Родительский/global transform, CSS/devicePixelRatio и соответствие stage coordinates физическим screen pixels всё ещё нужно измерить именно на painter popup.

### 7.3 Следствия для AutoDraw

1. Сравнивать move_calls, частоту ENTER_FRAME, число принятых координат и CHALK как разные метрики.
2. Для P1 (step=4, delay=5 ms) нельзя считать, что каждый 5-ms шаг становится отдельной игровой точкой: sampling ограничен кадрами, одинаковые соседние координаты удаляются.
3. Bridge frame_probe уже собирает интервалы requestAnimationFrame между началом и концом штриха. Следующий анализ должен связать их с per-stroke pointCount delta, длительностью и фактическими настройками Executor.
4. Полный обход atom.points внутри updateLess() может создавать обратную связь: накопление точек увеличивает работу на каждом кадре и потенциально снижает sampling rate. Это проверяемая гипотеза, не установленная причина PNG дефекта.
5. Не менять footprint model на основании только lineStyle thickness: нужны экранный transform popup board, renderer caps/joints и PNG calibration на нескольких значениях кисти.

**Точные области bundle:** BoardPane около offsets 4 092 419–4 095 700; Painter около offset 1 419 504. Blob SHA указан выше. BoardPane constants: 460×240, BLACK_BOARD_LINE_RADIUS=7.

**Статус:** E1 статический разбор завершён для перечисленных вызовов. Cap geometry, zero-length stroke rasterization, popup display transform и фактическая screen-space raster footprint — UNKNOWN. Live captures не запускались.


## 8. Фактическая cadence принятых игровых точек — run 6a17a297

Исходный Bridge JSON:
- session: bb261898-8296-41f5-a333-eb0b81016410;
- run: 6a17a297-ea14-4527-9527-bfd8de3bd335;
- файл: game-monitor-run-20261104T040548835772Z-6a17a297.json;
- brush radius=10; pointCount 1→1261; exact CHALK=1260;
- 27 pointer strokes, 1260 POINT_QUOTA_UPDATE events.

Per-stroke timing пересчитан по timestamps событий POINT_QUOTA_UPDATE и POINTER_DOWN/UP:
- каждый штрих принял 41–48 точек;
- длительность штриха 1450–1645 ms;
- median интервал между соседними quota updates — 33 ms во всех 27 штрихах;
- accepted point rate — 28.26–29.50 points/s;
- средняя скорость первых 9 штрихов — 28.734 points/s; последних 9 — 29.049 points/s.

В том же run aggregate frame_probe сообщает 2579 browser requestAnimationFrame intervals, average 59.997 FPS, median 60.024 FPS, 27 probes. Это browser rAF, не прямой счётчик Egret ENTER_FRAME. Нельзя заключать, что игровая обработка точек происходила с частотой 60 Hz: cadence POINT_QUOTA_UPDATE около 30 updates/s.

На этом run не видно снижения скорости принятых точек от накопления pointCount 1 до 1261 (сравнение первых/последних 9 штрихов), но это не доказывает отсутствие O(N) overhead на более длинных runs или других устройствах. Bundle показывает, что updateLess() пересчитывает массив atom.points; количественный эффект на FPS остаётся гипотезой.

Старый Bridge finalizer объединил rAF intervals в один run-level summary и очистил frame_probes, поэтому исходные per-stroke rAF intervals этого исторического run восстановить нельзя. POINT_QUOTA_UPDATE events сохранили timestamps и strokeId, поэтому accepted-point cadence восстановлена. Новые commits добавляют strokeId в frame_probe, сохраняют raw intervals и создают per_stroke_metrics/frame_probe_by_stroke.

**Уровень evidence:** E2 для cadence принятых точек данного run (точные игровые pointCount events); E2 для browser rAF aggregate; не E2 для фактического Egret frame rate и не доказательство renderer footprint.


## 9. Egret API defaults и stage target frame rate

В bundle найдено:
- Main UI container устанавливает _defaultFps=48.
- setAsMain() назначает stage.frameRate = _defaultFps и stage.scaleMode = egret.StageScaleMode.NO_SCALE.
- PainterPopup создаётся размером 676×379; его painterBoard имеет logical width=460, height=240, x=boardX, y=75. В createBlackBoard() явного scaleX/scaleY для painterBoard нет.
- BoardPane.redraw() вызывает lineStyle только с четырьмя аргументами.

Сопоставление с официальной документацией Egret Engine 5.2.18:
- thickness — толщина линии в points;
- omitted caps default to CapsStyle.ROUND;
- omitted joints default to JointStyle.ROUND.

Источник: https://app.unpkg.com/egret-engine@5.2.18/files/build/egret-wasm/egret.d.ts (Graphics.lineStyle, строки 6063–6090 в просмотренной версии).

**Ограничение:** фактически подключённая игрой версия Egret runtime не установлена по доступным репозиторным материалам. Поэтому round caps/joins — сильная API-совместимая гипотеза, но не доказательство конкретной сборки. Также не установлено, как renderer растеризует moveTo(p)+lineTo(p) при round cap. Нужны deployed runtime identity или независимый PNG capture. Не считать круглую форму footprint полностью подтверждённой.


## 10. Renderer path semantics from Egret source — 2026-11-04

Дополнительно проверены исходники Egret core (внешний upstream; это reference implementation, не файл из AutoDraw):
- GraphicsNode.ts blob SHA e4ec07f9d50e5fca450cc6fc93bab6b0f4dc2541. GraphicsNode.lineStyle() заменяет неподдерживаемые/отсутствующие caps на "round" и joints на "round"; StrokePath сохраняет эти значения.
- CanvasRenderer.ts blob SHA 80cbfb6c5dde6c66adfadc84cd5cb7283e71f391. Для StrokePath устанавливает context.lineCap и context.lineJoin, вызывает renderPath(), затем context.stroke().
- WebGLRenderer.ts blob SHA a1c0c9ebbe4a5dfd0ac53621c8133ac741b7062c. Его renderGraphics() использует canvasRenderer.renderGraphics() для растрирования GraphicsNode в canvas и затем переносит результат в texture. В этой версии Egret GraphicsNode использует тот же CanvasRenderer и при WebGL.
- Egret 5.2.18 egret.d.ts также документирует ROUND defaults для caps/joints и thickness как line width. Ссылки: https://github.com/egret-labs/egret-core/blob/master/src/egret/player/nodes/GraphicsNode.ts ; https://github.com/egret-labs/egret-core/blob/master/src/egret/player/rendering/CanvasRenderer.ts ; https://github.com/egret-labs/egret-core/blob/master/src/egret/web/rendering/webgl/WebGLRenderer.ts ; https://app.unpkg.com/egret-engine@5.2.18/files/build/egret-wasm/egret.d.ts

### 10.1 Вывод для многоточечного штриха

Для совместимой реализации Egret:
- lineStyle thickness=brush value; фактическая ширина линии равна brush value в координатном пространстве Graphics;
- отсутствующие caps/joints становятся ROUND;
- прямой многоточечный штрих имеет swept/capsule footprint с полукруглыми окончаниями; в углах используются round joins;
- на прямом сегменте геометрическая полуширина равна thickness/2, до преобразования board/global/canvas scale.

### 10.2 Одноточечный штрих

Painter.drawSmoothLine() для одного point формирует moveTo(p)+lineTo(p), то есть нулевой сегмент. drawNormalLine() формирует только moveTo(p).

HTML Canvas Standard требует удалить zero-length line segments перед построением stroke и удалить subpaths без линий. Следовательно, в CanvasRenderer такой путь не даёт видимого следа, хотя BoardPane.onDrawStart() уже добавил координату и updateLess() увеличил pointCount. WebGLRenderer в рассмотренной версии Egret тоже делегирует GraphicsNode растрирование в CanvasRenderer.

Источник Canvas path algorithm: https://html.spec.whatwg.org/multipage/canvas.html (раздел 4.12.5.1.4, lineCap; 4.12.5.1.6, path construction). Это вывод для совместимого CanvasRenderer; deployed Egret runtime/version игры пока не идентифицирован. В FILL-001-RS run все 27 штрихов имели 41–48 point updates, поэтому одноточечный случай к этому capture не относится.

### 10.3 Риск прямоугольной footprint-модели в planner

brush_footprint_geometry.footprint_pixel_bounds() возвращает прямоугольные границы capsule. Это пригодно как broad-phase bounds и как строгий prefilter безопасности (проверить, что весь bbox одного цвета), но bbox не равен фактическому capsule raster mask.

В частности:
- interior_fill_planner._mark_footprint() помечает весь прямоугольник covered=True;
- outline_first_fill_planner также вычитает прямоугольные bounds из residual;
- угловые пиксели bbox у круглых окончаний могут быть помечены как покрытые, хотя capsule их не касается.

Это способно привести к underfill в этих planner-ах. Это отдельная гипотеза/дефект модели, не установленная причина FILL-001-RS: текущий FILL capture строился scanline plan и требует отдельного аудита. До изменения кода сначала установить deployed renderer/transform и добавить точный pixel-cell capsule/swept footprint с regression tests.


## 11. Прямое чтение brush path из игрового bundle — 2026-11-04

**Источник:** `master:AutoDraw_Stage20/fileGameEngine/main.min_570122a1.js`; Git blob SHA `28838e803dcc6f85efb13febd93cc9e0f5046ffc`. Bundle прочитан через Git blob API; JavaScript не исполнялся. Ни `master`, ни исходный bundle не изменялись.

### 11.1 Что непосредственно делает BoardPane

В `BoardPane.redraw()` найден следующий фактический порядок:
1. Для текущего сохранённого штриха берутся `atom.points`, `atom.radius`, `atom.colors` и `atom.options`.
2. Для каждого штриха вызывается `graphics.lineStyle(s, color, 1, false)`.
3. При включённом smooth option вызывается `Painter.drawSmoothLine(...)`; иначе — `Painter.drawNormalLine(...)`.
4. Значение `s` напрямую передаётся как thickness линии Egret Graphics. Это ширина штриха, не диаметр `2 × s` и не геометрический радиус `s`.

### 11.2 Фактическая геометрия центральной линии

- `drawNormalLine()` начинает путь через `moveTo(first)` и продолжает его последовательными `lineTo(point)`.
- `drawSmoothLine()` вычисляет середины соседних пар точек, использует их как промежуточные окончания сегментов и строит сглаживание через `curveTo(control, midpoint)`; затем при соответствующем флаге доводит путь до последней точки.
- Поэтому smooth stroke нельзя точно заменить набором независимых прямых отрезков: нужно сохранять ту же последовательность midpoint/quadratic-curve path operations либо доказанно эквивалентную геометрию.
- `onDrawStart()` добавляет начальную точку после `globalToLocal(stage.mouseX, stage.mouseY)`; `onDrawing()` получает следующие точки на `ENTER_FRAME`, проверяет попадание в локальный прямоугольник доски и только затем сохраняет точку.
- `BlackBoardAtom.pushPoint()` не добавляет точку, если она равна последней сохранённой. `onDrawingEnd()` завершает штрих вызовом `atom.add()`.
- `setRadius()` записывает выбранное значение в `atom.radius` текущего штриха.

### 11.3 Круглая форма — наблюдение и доказательность

**Пользовательское визуальное наблюдение (2026-11-04):** кисть в самой игре выглядит круглой. Это наблюдение пользователя, а не измерение PNG.

**Сопоставление с исходником:** игровой код задаёт толщину линии через `Graphics.lineStyle`, но не передаёт caps/joints явно — вызов содержит только четыре аргумента. Egret 5.2.18 API/reference implementation задаёт ROUND для отсутствующих caps и joints. Это согласуется с визуальным наблюдением и с моделью круглого swept footprint: у прямого сегмента — полоса шириной thickness с полукруглыми концами; у ломаной — круглые соединения. Для сглаженной траектории та же круглая кисть проходит вдоль кривого центрального пути.

**Ограничение:** deployed Egret runtime игры всё ещё не идентифицирован. Поэтому ROUND caps/joins — подтверждённое поведение reference API и сильная гипотеза для игры, но не окончательное доказательство её конкретной растеризации. Нельзя пока объявлять offline capsule mask пиксельно эквивалентной игровому PNG.

### 11.4 Особый случай одного клика

Для массива из одной точки `drawSmoothLine()` формирует `moveTo(p)` и затем `lineTo(p)`; `drawNormalLine()` формирует только `moveTo(p)`. По Canvas path semantics zero-length segment не обязан создавать видимый след. При этом `onDrawStart()` уже сохраняет первую точку и вызывает `updateLess()`. Следовательно, возможен случай расхода одной игровой точки без видимого отпечатка. Это вывод из исходной последовательности операций и Canvas semantics; поведение deployed renderer для такого случая требует отдельного PNG/runtime подтверждения.

### 11.5 Вывод для AutoDraw

1. Эталонная геометрическая модель — круглая кисть, проходящая вдоль фактического центрального пути; для прямого сегмента это capsule/swept disk, а не прямоугольный AABB.
2. Толщина модели должна быть равна передаваемому `brush_value`; полуразмер равен `brush_value / 2` до применения transform.
3. Для smooth option нужно воспроизводить midpoint + `curveTo` путь; обычный polyline режим остаётся отдельным вариантом.
4. Координаты BoardPane локальны; игровой ввод переводит stage coordinates через `globalToLocal()`. Для полного совпадения требуется также восстановить transform popup/board → screen/canvas ROI.
5. Существующий `swept_capsule_pixel_masks()` является полезной offline геометрической основой, но пока не доказан как pixel-identical renderer replica.
6. До renderer identity и frozen PNG comparison не менять production planner/defaults и не разблокировать FILL-001-RS matrix.

**Уровень evidence:** E1 — статически прочитаны конкретные методы bundle и их связи; E0/E1 для вывода о deployed round caps/joins; пользовательское визуальное наблюдение отдельно зафиксировано. Runtime equivalence — NOT VALIDATED.
## 12. Проверка фактически загружавшихся runtime assets — 2026-11-04

Проверены сохранённые Resource Timing events в Game Monitor captures:
- `source/game_monitor/autodraw-game-monitor-2026-10-30T01-57-14-095Z.json`;
- `source/game_monitor/autodraw-game-monitor-2026-10-30T02-13-35-704Z.json`;
- `data/a,b,c -test/run_01/test-B/autodraw-game-monitor-2026-10-31T16-35-43-311Z.json`.

Во всех этих исторических captures зафиксированы загрузки с `https://eufbpet.hust.me`:
- `/old/manifest.json?v=1793325121145` (initiator `xmlhttprequest`, Resource Timing `transferSize=396`);
- `/old/js/mergeEngine_df2e5bc5.js` (initiator `script`, `transferSize=202755`);
- `/old/js/main.min_6ecc02a4.js` (initiator `script`, `transferSize=722697`).

Это metadata из Resource Timing, а не содержимое файлов и не криптографические размеры response body. Содержимое manifest и двух JavaScript assets в репозитории не сохранено. Попытка открыть эти URL напрямую через доступный web fetch завершилась недоступностью домена; поэтому версии runtime по их содержимому установить не удалось.

**Важное расхождение источников:** bundle, статически разобранный ранее в `master`, называется `main.min_570122a1.js` (Git blob SHA `28838e803dcc6f85efb13febd93cc9e0f5046ffc`; документированный размер 4 785 687 bytes). Он не совпадает по имени с исторически загружавшимся `main.min_6ecc02a4.js`. Пока не получены body/hash обеих сетевых загрузок, нельзя считать их одной версией или переносить runtime-выводы с одного bundle на другой.

В `main.min_570122a1.js` присутствуют game-side Egret references и BoardPane/Painter logic; runtime asset `mergeEngine_df2e5bc5.js` в capture отдельно загружался как script. Но по одному имени файла нельзя утверждать, что это конкретная версия Egret или что он содержит весь renderer. Egret 5.2.18 upstream source остаётся reference implementation, не доказанной версией deployed runtime.

### Результат и следующий шаг

- **Подтверждено:** историческая игра загружала manifest и два отдельных JS assets с указанными именами; Game Monitor зафиксировал URL и Resource Timing metadata.
- **Не подтверждено:** содержимое этих ресурсов, SHA-256, Egret runtime version, Canvas/WebGL path и связь исторических assets с текущей игрой.
- **Не делать:** не объявлять 5.2.18 runtime фактом; не копировать upstream renderer и не принимать capsule mask как pixel-identical.
- **Нужное evidence:** получить response bodies `manifest.json`, `mergeEngine_df2e5bc5.js`, `main.min_6ecc02a4.js` из браузерного cache/DevTools Network (без авторизационных cookies/tokens), записать SHA-256 и сравнить symbols/implementation. Если assets уже обновились, зафиксировать новый набор в одном session capture. Live drawing не требуется для самого чтения статических файлов; любые игровые испытания остаются под отдельным разрешением.

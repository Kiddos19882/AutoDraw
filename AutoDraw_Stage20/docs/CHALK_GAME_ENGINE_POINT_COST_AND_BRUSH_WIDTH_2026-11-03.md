# Игровой движок: связь размера кисти и расхода CHALK

**Дата аудита:** 2026-11-03  
**Исходный исторический источник:** `AutoDraw_Stage20/fileGameEngine/main.min_570122a1.js` в `master`, добавлен commit `bd8815cfb5e8cdc3276d872c833adeb23bbf22ac`. Последующий анализ актуального пользовательски подтверждённого набора `AutoDraw_Stage20/gameEngine/` (п) приведён в разделах 11–13 ниже.  
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

- **Историческое состояние на момент исходного аудита:** `main.min_570122a1.js` присутствовал в `master`, но отсутствовал в `feature/image-geometry-optimization`; engine bundle ещё не был скопирован в рабочую ветку.
- `AutoDraw_Stage20/testImages/images.png` присутствовал в обеих ветках с одинаковым blob SHA `fc9c984d15e9dda7d6511b01b5a88ca52ba2380f`; повторный перенос не требовался.
- Последующее изменение состояния зафиксировано в разделе 9: commit `d3322fe` добавил отдельные engine assets в feature branch. Это не изменяет исторический факт, описанный выше.


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
## 12. Проверка исторических Resource Timing runtime assets — 2026-11-04

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


## 9. Копия игровых engine assets в feature branch — 2026-11-04

Commit [d3322fe35c808bde079c79545cc839636b7cda2a](https://github.com/Kiddos19882/AutoDraw/commit/d3322fe35c808bde079c79545cc839636b7cda2a) добавил каталог `AutoDraw_Stage20/gameEngine/` (п):

| Файл | Git blob SHA |
|---|---|
| `main.min_653f95bc.js` (ф) | `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388` |
| `mergeEngine_df2e5bc5.js` (ф) | `d613d2b97e2436521aa3870478c69e99eac1f19f` |
| `manifest.json` (ф) | `0aea9b5c89eef7e4cd9552f9d1302eed29bcc28e` |

Манифест указывает runtime paths `js/mergeEngine_df2e5bc5.js` и `js/main.min_653f95bc.js`. В репозитории файлы лежат непосредственно в `gameEngine/`, а не в `gameEngine/js/`.

Наличие этих файлов позволяет анализировать новую копию игровых bundles в feature branch. Пока не установлено, что она байт-в-байт совпадает с историческими assets из Game Monitor captures или с ранее прочитанным `master:fileGameEngine/main.min_570122a1.js`. Имя merge bundle совпадает с историческим URL, но это не заменяет hash comparison; имя основного bundle отличается. Поэтому deployed Egret/runtime identity остаётся UNKNOWN до статического сравнения содержимого и подтверждения источника.


## 11. Повторный разбор подтверждённого набора с сайта игры — 2026-11-04

Пользователь подтвердил, что `main.min_653f95bc.js`, `mergeEngine_df2e5bc5.js` и `manifest.json` скачаны с сайта запущенной игры в один момент; достоверность происхождения — 100% по подтверждению пользователя. Эти три файла рассматриваются как единый согласованный набор. Сверка с `master/fileGameEngine/main.min_570122a1.js` не требуется.

### 11.1. Точный счётчик и приём координат

В `main.min_653f95bc.js` (Git blob SHA `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`) подтверждено:

- `BoardPane.updateLess()` проходит по всем штрихам и всем точкам `atom.points`, считает `pointCount`, затем задаёт `less = max - pointCount` и отправляет событие `BlackBoardEvent.CHALK` с `percent = less / max`.
- `BoardPane.onDrawStart()` добавляет стартовую координату из `globalToLocal(stage.mouseX, stage.mouseY)`, обновляет квоту и подписывается на `ENTER_FRAME`.
- `BoardPane.onDrawing()` на кадре читает текущую позицию, переводит её в локальные координаты, проверяет прямоугольник `0..width × 0..height` и при попадании вызывает `atom.pushPoint()`, `updateLess()` и `redraw(false)`.
- `BoardPane.onDrawingEnd()` снимает `ENTER_FRAME` listener, перерисовывает и завершает текущий массив точек через `atom.add()`.
- `BlackBoardAtom.pushPoint()` добавляет координату только если текущий штрих пуст или координата не совпадает с последней точкой. Повтор одной и той же соседней координаты не увеличивает расход.
- `updateLess()` повторно сканирует весь накопленный `atom.points` на каждом вызове. Это статически подтверждённая O(N) работа игрового пути, но влияние на FPS/количество принятых точек не измерялось в рамках этого анализа.

### 11.2. Размер кисти и геометрия

- `BoardPane.setRadius(t)` выполняет только `atom.radius[atom.length - 1] = t`; прямого изменения `pointCount`, `max` или `less` в этом методе нет.
- `BoardPane.redraw()` передаёт сохранённое значение как первый аргумент `graphics.lineStyle(s, color, 1, false)`, то есть как толщину линии Graphics. Название `radius` в модели игры не следует автоматически трактовать как математический радиус диска с диаметром `2×radius`.
- Presets `RadiusOption`: 20, 14 и 7; `MAX_RADIUS=30`; `BoardPane.BLACK_BOARD_LINE_RADIUS=7`.
- В `PainterPopup` smooth button по умолчанию selected и `painterBoard.setSmooth(true)` вызывается при инициализации. `Painter.drawSmoothLine()` строит midpoint/`curveTo`; `drawNormalLine()` строит polyline через `moveTo`/`lineTo`. Выбор пути влияет на геометрию растеризации, но не меняет формулу счётчика CHALK.
- `PainterPopup.createBlackBoard()` создаёт активный `painterBoard` с логическим размером 460×240 и лимитом `blackBoard.maxPoint`. `BoardPane` constructor имеет fallback `maxPoint=2000`, но в этом пути передаётся значение объекта доски.
- В режиме `_isPainterExtend` метод `clear()` добавляет специальную стартовую точку `(0,0)` и отдельный массив штриха. Поэтому абсолютный `pointCount` может содержать начальную служебную точку; изолированный расход следует считать по pre/post delta после завершённого Clear/baseline.

### 11.3. Runtime renderer из merge bundle

`mergeEngine_df2e5bc5.js` (Git blob SHA `d613d2b97e2436521aa3870478c69e99eac1f19f`) содержит `egret.Capabilities.engineVersion="5.4.1"`. Это supersedes прежнее предположение, основанное на upstream reference Egret 5.2.18: для текущего набора статически установлен номер движка 5.4.1.

В реализации `GraphicsNode.lineStyle()` отсутствующие/неподдерживаемые caps/joints нормализуются к `"round"`; `CanvasRenderer.renderGraphics()` назначает `context.lineCap` и `context.lineJoin`, затем вызывает `stroke()`. Это подтверждает renderer defaults в предоставленном merge bundle. Но поведение нулевого пути `moveTo(p)+lineTo(p)`, итоговый pixel footprint и фактический Canvas/WebGL execution mode требуют отдельной frozen-fixture/runtime проверки.

Основной bundle задаёт `stage.frameRate=48` и `StageScaleMode.NO_SCALE`; это nominal target, а не измеренный FPS. Логические размеры BoardPane — 460×240. Popup/global transform и фактический screen ROI этим разбором не установлены.

### 11.4. Историческое структурное наблюдение о BoardPane — NOT_APPLICABLE_TO_CURRENT_USER_SCENARIO

В `main.min_653f95bc.js` существуют два экземпляра одного класса:

1. Preview `BoardPane` внутри `BoardItemBase.createNativeContent()`, где устанавливается `interactive=false`.
2. Рабочий `PainterPopup.painterBoard`, создаваемый `createBlackBoard()` с `interactive=true`.

Текущий `source/game_monitor/game_monitor.js` ищет первый структурно подходящий объект через обход display list (`findBoard()` → `isBoard()`). Проверка требует `atom.points` и методов `onDrawStart/onDrawing/onDrawingEnd`, но не проверяет `interactive`, popup ownership или активность рисования. Следовательно, auto-discovery имеет неоднозначность и может выбрать preview BoardPane. Это не доказывает, что именно он выбирается в конкретном live session: порядок display list и фактическая привязка требуют отдельного подтверждения. Unit tests сейчас проверяют прямой `attach(board)` и replacement, но не несколько BoardPane в одном display list.

**Уточнение пользователя от 2026-11-04:** текущая игровая комната не содержит других досок; на экране используется одна пустая тестовая доска. В этом сценарии выяснение, выбрал ли Game Monitor preview BoardPane или PainterPopup BoardPane, не требуется и не является блокером. Структурная неоднозначность остаётся историческим фактом для других конфигураций, но получает статус `NOT_APPLICABLE_TO_CURRENT_USER_SCENARIO`. Это не доказывает универсальную корректность auto-discovery и не означает изменения кода/тестов.

### 11.5. Следующий шаг

1. Проверить popup → BoardPane → screen transform, clipping и соответствие logical 460×240 фактическому ROI.
2. Подготовить frozen fixtures для smooth/normal path, прямых концов, поворотов, разных thickness и zero-length path; сопоставить rasterization с offline capsule candidate.
3. Только после offline gates и отдельного разрешения рассматривать live capture. Текущий документальный increment не запускал игру и не измерял CHALK.


## 13. Уточнение области применимости — текущий сценарий Game Monitor (2026-11-04)

Пользователь подтвердил, что рабочая игровая комната не содержит других досок, а на экране используется одна пустая тестовая доска. Поэтому ранее описанное различие preview `BoardPane` и `PainterPopup.painterBoard`, а также неоднозначность общего `findBoard()`, не являются требованием к текущему сценарию и не блокируют измерения в нём. В актуальном backlog задача выбора экземпляра исключена как `NOT_APPLICABLE_TO_CURRENT_USER_SCENARIO`; историческое техническое наблюдение в разделе 11.4 сохранено.

Отдельно уточняется доказательность версии движка: в пользовательски подтверждённом согласованном наборе `gameEngine/main.min_653f95bc.js`, `mergeEngine_df2e5bc5.js` и `manifest.json` статически указана версия Egret 5.4.1. ROUND caps/joints defaults и реализация CanvasRenderer присутствуют в этом merge bundle. Более ранние Resource Timing captures с иным именем main bundle остаются историческими свидетельствами загрузок; их содержимое не подменяется текущим набором.

**Остаются неизвестными:** какой render backend фактически использовался в конкретной старой capture-сессии; полный popup/global→screen transform и clipping; pixel footprint и rasterization zero-length path. Эти вопросы не закрываются одним номером версии движка и требуют соответствующих frozen fixtures/измерений.


## 14. Полная трассировка цепочки игровой кисти и границы воспроизведения — 2026-11-04

**Источник:** пользовательски подтверждённый согласованный набор gameEngine/main.min_653f95bc.js и gameEngine/mergeEngine_df2e5bc5.js. Основной bundle прочитан как Git blob SHA 46cc74de00b6cb5d207b1e1a2ffcd81613b6d388 (4 857 523 символа); merge bundle — blob SHA d613d2b97e2436521aa3870478c69e99eac1f19f. Сверка с историческим master/fileGameEngine/main.min_570122a1.js не выполнялась и не требуется.

### 14.1. Ввод → принятые точки

1. BoardPane.initAction() подписывает BoardPane на TOUCH_BEGIN и TOUCH_END; при добавлении на stage подписывается также на stage-level TOUCH_END.
2. BoardPane.onMouseDown() копирует event.stageX/stageY в stage.mouseX/mouseY и отправляет DRAG_START.
3. BoardPane.onDrawStart() при положительном остатке CHALK ставит _isStart=true, преобразует текущие stage/global координаты через globalToLocal(), передаёт точку в atom.pushPoint(), обновляет счётчик и подписывается на ENTER_FRAME.
4. BoardPane.onDrawing() на каждом ENTER_FRAME снова читает stage.mouseX/mouseY, выполняет globalToLocal(), проверяет попадание в локальный прямоугольник 0..width × 0..height. Только внутри него вызывает pushPoint(), updateLess() и redraw(false).
5. BlackBoardAtom.pushPoint() добавляет точку, если текущий массив пуст или Point.equals() с последней точкой возвращает false. Соседняя повторная координата не увеличивает pointCount.
6. BoardPane.onDrawingEnd() снимает ENTER_FRAME listener, вызывает redraw(false) и atom.add(). Отдельного финального чтения координат мыши в обработчике завершения нет.

**Следствие:** игра хранит не все перемещения, отправленные AutoDraw, а выборку координат, доступную игровому циклу ENTER_FRAME, с последующим удалением соседних повторов. Номинальный stage.frameRate=48 — целевой параметр, не измеренная частота выборки. Поэтому количество AutoDraw move calls нельзя приравнивать к принятым игровым точкам.

### 14.2. Точки → геометрическая команда

BoardPane.redraw() перебирает сохранённые штрихи, вызывает graphics.lineStyle(value, color, 1, false) и выбирает функцию по atom.options:

- Painter.drawNormalLine(): moveTo(P0), затем lineTo(P1...Pn).
- Painter.drawSmoothLine(): рассчитывает midpoint каждой пары соседних точек; начинает с moveTo(P0), ведёт линию к первому midpoint, далее использует curveTo(Pi, midpoint(i,i+1)), затем ведёт линию к последней исходной точке.
- В PainterPopup smooth включается при инициализации через painterBoard.setSmooth(true). При отсутствии явной опции redraw() также выбирает smooth path.
- Для одного сохранённого пункта normal path содержит только moveTo; smooth path дополнительно вызывает lineTo к той же координате. Это создаёт разные команды пути, но не доказывает, какие пиксели будут закрашены нулевым сегментом.

### 14.3. Значение кисти → Graphics/Egret

Игровой вызов graphics.lineStyle(value, color, 1, false) передаёт:
- value как толщину линии;
- color и alpha=1;
- false как четвёртый аргумент pixelHinting, а не как настройку caps.

Параметры caps и joints не передаются. В Graphics.lineStyle() они остаются неопределёнными; GraphicsNode.lineStyle() нормализует неподдерживаемые/отсутствующие значения к round. Для CanvasRenderer renderGraphics() назначает context.lineWidth, context.lineCap, context.lineJoin и вызывает stroke().

Следовательно, в Canvas path значение UI является **line width**, а не радиусом круга. Геометрическая половина толщины — лишь математическая интерпретация ширины stroke; она не задаёт точную пиксельную маску браузерного rasterizer.

### 14.4. Renderer backend

В merge bundle присутствуют CanvasRenderer и WebGLRenderer. Функция egret.sys.setRenderMode(mode) выбирает WebGL при mode === "webgl" и успешной проверке доступности WebGL; в остальных случаях устанавливает CanvasRenderer и Capabilities.renderMode="canvas". Начальное значение Capabilities.renderMode — "Unknown".

Сохранённый набор assets не содержит boot HTML/конфигурации запуска или runtime capture, которые показывали бы аргумент setRenderMode и выбранный backend конкретной сессии. Поэтому наличие CanvasRenderer и его реализация доказаны статически, но использование именно CanvasRenderer в игровой сессии не доказано. Canvas-only реплика до выяснения этого условия преждевременна.

### 14.5. Локальные границы и clipping

- Рабочий PainterPopup.painterBoard создаётся с logical width=460 и height=240, x=boardX, y=75; в этом месте отдельный локальный scale не назначается.
- BoardPane.resetBg() задаёт scrollRect=(0,0,width,height).
- PainterPopup.createBlackBackground() создаёт rounded-rectangle mask размером 460×240 с радиусом угла 10 и назначает её painterBoard.mask.
- Координаты указателя переводятся из stage/global в локальные через globalToLocal().

Таким образом, путь проходит как минимум через локальную прямоугольную проверку/scrollRect и popup mask. Полная цепочка родительских display transforms, фактический экранный ROI, browser device-pixel mapping и backend-specific clipping не установлены.

### 14.6. Сопоставление с текущей реализацией AutoDraw

- source/executor/drawing/mouse_executor.py генерирует последовательность экранных moveTo по point_step_px и point_delay_ms; игровой BoardPane затем независимо выбирает координату на ENTER_FRAME. AutoDraw отправляет ввод, но не управляет списком точек, который фактически сохранит игра.
- chalk_fill_fixed_radius_planner.py строит двухточечные горизонтальные штрихи и моделирует их через OpenCV line плюс окружности для round caps. Это отдельный OpenCV rasterizer, не Egret Graphics/Canvas/WebGL.
- swept_capsule_pixel_masks() моделирует идеальную round-capped polyline; она не воспроизводит автоматически midpoint/curveTo, кадровую выборку и конкретный renderer.
- interior_fill_planner.py использует прямоугольные pixel bounds как safety check; этот путь не является renderer replica и не готов к исполнению.
- Существующие тесты проверяют математические модели/их oracle, а не pixel identity с игровым Egret renderer.

### 14.7. Дополнительное поведение redraw

redraw(false) не вызывает resetBg(), а повторно строит путь последнего штриха. В merge bundle GraphicsNode.lineStyle() создаёт новый StrokePath и добавляет его в drawData. Поэтому статический call path указывает на повторное добавление команд текущего штриха при последовательных кадрах до следующего полного redraw(), который очищает Graphics. Влияние этого поведения на runtime performance и antialiasing не измерялось; оно не меняет формулу pointCount.

### 14.8. Вывод и следующий offline gate

**Подтверждено (E1):** цепочка ввода, кадровой выборки, локального преобразования, dedup точек, smooth/normal path construction, передачи толщины и renderer backend selection. Это позволяет реализовать совместимый генератор входных path commands и модель point sampling.

**Не подтверждено:** фактически выбранный backend конкретной сессии, полный display/CSS/device-pixel transform, zero-length rasterization, точный pixel footprint концов/joins/кривых и pixel identity с игрой.

**Рекомендуемый следующий шаг GAME-BRUSH-REPLICATION:** подготовить offline reference harness, который воспроизводит (а) последовательность принятых точек из заданного временного ряда ввода, (б) normal/smooth path commands, (в) выбранный Egret renderer и clipping/transform. До создания renderer fixtures нельзя считать OpenCV/capsule model заменой игровому rasterizer. Сначала получить evidence выбранного backend и transform; затем frozen fixtures для одиночной точки, горизонтального/диагонального сегмента, нескольких smooth points, поворота, разных толщин и границ маски; сравнить PNG и локализовать расхождения.

**Границы текущей работы:** исходники, тесты, конфигурации и workflow AutoDraw не изменялись; скрипты анализа не запускались; live drawing/игровые эксперименты не выполнялись. Статический вывод не подтверждает экономию CHALK: exact расход по-прежнему определяется только дельтой игрового pointCount.

# Game Monitor и Bridge — техническая справка

**Статус:** актуальная справка по реализации в рабочей ветке  
**Дата проверки:** 2026-11-03  
**Ветка:** `feature/image-geometry-optimization`  
**Область:** браузерный Game Monitor, browser-side Bridge и локальный WebSocket collector.

Документ описывает фактические интерфейсы и поток данных трёх компонентов. Это справочник по текущему коду, а не описание целевой архитектуры. При изменении исходников сигнатуры и список событий следует сверять с файлами реализации.

## 1. Состав компонентов

| Компонент | Файл | Среда | Назначение |
|---|---|---|---|
| Game Monitor | `source/game_monitor/game_monitor.js` | JavaScript внутри игрового iframe | Находит BoardPane, наблюдает игровые методы и ресурсные счётчики, формирует события и экспорт |
| Browser Bridge | `source/game_monitor/game_monitor_bridge.js` | JavaScript внутри того же iframe | Подписывается на события Monitor, измеряет frame intervals и отправляет выбранные события по WebSocket |
| Bridge collector | `source/game_monitor/game_monitor_bridge_server.py` | Отдельный локальный Python-процесс | Аутентифицирует browser agent, принимает сообщения, собирает run/session JSON и диагностические счётчики |
| Launcher | `source/game_monitor/start_game_monitor_bridge.bat` | Windows | Запускает локальный collector с параметрами Origin/output directory |
| Зависимости | `source/game_monitor/requirements-bridge.txt` | Python | Зависимости WebSocket collector |

Bridge — транспорт и recorder, а не игровой исполнитель. Он не отправляет команды игре и не управляет мышью. Game Monitor временно оборачивает методы экземпляра BoardPane, поэтому его нельзя считать полностью неинвазивным без отдельного измерения overhead и проверки восстановления методов.

## 2. Общий поток данных

```text
Game iframe
  BoardPane
     │ вызовы игровых методов / изменение BoardPane.max и less
     ▼
  game_monitor.js
     │ AutoDrawGameMonitor.subscribe(listener)
     ▼
  game_monitor_bridge.js
     │ WebSocket: auth → ready → session_start → event / heartbeat / frame_probe
     ▼
  ws://127.0.0.1:8765
     │ проверка Origin, token, sessionId и sequence
     ▼
  game_monitor_bridge_server.py
     ├── <output>/<session_id>/session.json
     └── <output>/<session_id>/game-monitor-run-*.json
```

1. Monitor обнаруживает Egret stage и ищет объект BoardPane в display list.
2. Monitor оборачивает методы BoardPane и устанавливает pointer observers.
3. Browser Bridge подписывается на Monitor и пересылает разрешённый список событий.
4. Collector принимает одно активное browser connection, проверяет аутентификацию и последовательность сообщений.
5. RunRecorder начинает run при первом событии начала штриха, накапливает события и финализирует run после периода бездействия либо при закрытии соединения.
6. Session diagnostics обновляются при каждом сообщении; run JSON создаётся отдельно при финализации.

## 3. Game Monitor API (версия 0.2.1)

Публичный объект: `window.AutoDrawGameMonitor`. Скрипт автоматически вызывает `start()` после установки API.

| Метод | Аргументы | Результат / действие |
|---|---|---|
| `start()` | нет | Включает мониторинг, Resource Timing observer, pointer observers, поиск BoardPane и периодическое сканирование; возвращает `status()` |
| `stop()` | нет | Останавливает таймеры/observer, снимает pointer listeners, восстанавливает обёрнутые методы BoardPane; возвращает `status()` |
| `status()` | нет | Возвращает версию, active, boardDetected, boardLabel, O(1) snapshot, eventCount, droppedEvents и число ошибок |
| `inspect()` | нет | Read-only поиск/снимок BoardPane без attach, wrappers и timers |
| `subscribe(listener)` | функция | Добавляет listener событий; возвращает функцию unsubscribe |
| `export()` | нет | Возвращает экспорт schemaVersion=1 с метаданными страницы, snapshot, events, droppedEvents и errors |
| `download()` | нет | Скачивает `export()` в JSON-файл |
| `clear()` | нет | Очищает локальные events, droppedEvents и errors |
| `attach(boardPaneInstance)` | экземпляр BoardPane | Вручную подключает найденный экземпляр и оборачивает методы |
| `diagnosticSnapshot()` | нет | Выполняет явную O(N) диагностику массива atom.points и сравнивает подсчёт с быстрым счётчиком |

### 3.1. Какие методы игры оборачиваются

Константа `METHOD_NAMES` содержит:

- `BoardPane.onDrawStart` — начало штриха; Monitor записывает `DRAW_START` и после оригинального вызова `DRAW_START_APPLIED`.
- `BoardPane.onDrawing` — наблюдение изменений точки во время движения; вызывает выборку актуального resource snapshot.
- `BoardPane.onDrawingEnd` — завершение штриха; фиксирует финальную выборку и `DRAW_END`.
- `BoardPane.setRadius` — изменение кисти; события `BRUSH_CHANGE` до вызова и `BRUSH_CHANGE_APPLIED` после него.
- `BoardPane.updateLess` — обновление квоты; `POINT_QUOTA_UPDATE` создаётся только если изменились max/less.

Обёртка вызывает исходный метод с тем же `this` и аргументами, возвращает его результат. При исключении создаётся `GAME_METHOD_ERROR`, после чего исключение повторно выбрасывается. При detach исходные descriptors/методы восстанавливаются.

### 3.2. Ресурсный snapshot

Основной быстрый источник — целочисленные поля `BoardPane.max` и `BoardPane.less`:

- `maxPoints = BoardPane.max`;
- `remainingPoints = BoardPane.less`;
- `pointCount = maxPoints - remainingPoints`.

Snapshot считается точным только если оба значения — безопасные целые числа, max больше нуля, а remaining находится в диапазоне от нуля до max. Иначе значения счётчика становятся null, `isExact=false`, `validationStatus="unavailable"`.

В snapshot также входят логические размеры доски, scaleX/scaleY, радиус и currentRadius. Быстрый путь не сканирует `atom.points`. Полный обход массива выполняется только явным `diagnosticSnapshot()`.

### 3.3. События Monitor

Основные события:

| Событие | Смысл |
|---|---|
| `MONITOR_STARTED`, `MONITOR_STOPPED` | Жизненный цикл Monitor |
| `BOARD_ATTACHED`, `BOARD_DETACHED` | Подключение/отключение BoardPane |
| `DRAW_START`, `DRAW_START_APPLIED`, `DRAW_END` | Жизненный цикл штриха на уровне игровых методов |
| `DRAW_SAMPLE` | Изменение точного pointCount во время штриха |
| `BRUSH_CHANGE`, `BRUSH_CHANGE_APPLIED` | Радиус до/после setRadius |
| `POINT_QUOTA_UPDATE` | Изменение max/less после updateLess |
| `GAME_METHOD_ERROR` | Ошибка обёрнутого метода |
| `POINTER_DOWN_CANDIDATE`, `POINTER_UP_CANDIDATE` | Pointer fallback для lifecycle, если игровые callback недоступны |
| `NETWORK_RESOURCE` | Resource Timing entry |

`DRAW_SAMPLE` содержит source, strokeId, before/after snapshot, pointDelta и acceptedPoint. Выборка выполняется при изменении счётчика, а не на каждом кадре. Если `pointDelta > 1`, между выборками могли появиться промежуточные точки; acceptedPoint — только последняя принятая координата, а не полная траектория.

Локальный буфер Monitor ограничен `MAX_EVENTS=50000`. После заполнения увеличивается droppedEvents, однако emit продолжает уведомлять подписчиков. Это означает, что Bridge subscriber может получить события, даже когда локальный export buffer уже достиг лимита. Не путать локальный cumulative droppedEvents с per-run `dropped_events` на стороне collector.

## 4. Browser Bridge API и протокол

Файл `game_monitor_bridge.js` — одноразовый snippet, который collector генерирует с подставленным token. Он ожидает `window.AutoDrawGameMonitor` с методами subscribe/status и завершает выполнение ошибкой, если Monitor не загружен. Повторное подключение при уже connected Bridge запрещается.

Публичный объект `window.AutoDrawGameMonitorBridge` содержит:

- `connected` — состояние WebSocket-соединения;
- `sessionId` — UUID текущей browser session;
- `disconnect()` — закрывает WebSocket штатным кодом 1000 (либо обычным close до соединения).

Отдельных публичных методов start/stop/reconnect у Browser Bridge нет.

### 4.1. Исходящие сообщения

| Тип | Содержимое |
|---|---|
| `auth` | token; отправляется первым после WebSocket open |
| `session_start` | sessionId, sequence=1, sentAtUtc, monitorStatus, browser, page, visibilityState |
| `event` | исходное событие Monitor |
| `heartbeat` | monitorStatus, performanceNowMs, visibilityState, bridgeDiagnostics |
| `frame_probe` | интервалы requestAnimationFrame, начало/конец и видимость страницы |

Каждое сообщение после auth содержит sessionId, возрастающий sequence и sentAtUtc. Heartbeat отправляется раз в секунду. Browser-side bridgeDiagnostics содержит sentEventCount, lastEventType, lastEventAtPerformanceMs и sendFailureCount.

Для FPS probe Bridge использует requestAnimationFrame между началом и концом штриха. Если документ становится невидимым, probe завершается. Collector рассчитывает средние/медианные FPS и интервалы по сохранённым frame intervals.

### 4.2. Фильтр событий

Bridge передаёт только allowlist:

`BOARD_ATTACHED`, `BOARD_DETACHED`, `DRAW_START`, `DRAW_START_APPLIED`, `DRAW_SAMPLE`, `DRAW_END`, `BRUSH_CHANGE`, `BRUSH_CHANGE_APPLIED`, `POINT_QUOTA_UPDATE`, `GAME_METHOD_ERROR`, `POINTER_DOWN_CANDIDATE`, `POINTER_UP_CANDIDATE`.

Например, `MONITOR_STARTED`, `MONITOR_STOPPED` и `NETWORK_RESOURCE` остаются в Monitor export, но не входят в текущий Bridge allowlist.

При отсутствии открытого сокета или ошибке send увеличивается sendFailureCount. Browser agent не делает автоматического повтора потерянного сообщения; heartbeat передаёт накопленный счётчик collector-у.

## 5. Python Bridge collector

### 5.1. Константы и входные ограничения

- HOST = `127.0.0.1` — collector слушает только loopback.
- PORT = `8765` по умолчанию.
- MAX_MESSAGE_BYTES = `65536`.
- MAX_EVENTS_PER_RUN = `100000`.
- Origin должен быть точным HTTPS origin без username/password/path/query/fragment.
- Требуется token; сравнение выполняется через `hmac.compare_digest`.
- Одновременно допускается одно активное browser connection.
- WebSocket origin allowlist задаётся через `origins=[origin]`.

### 5.2. Функции модуля

| Функция / класс | Назначение |
|---|---|
| `utc_now()` | Текущее UTC время в ISO формате с миллисекундами |
| `valid_origin(value)` | Проверка формата разрешённого HTTPS Origin |
| `parse_json(raw)` | Ограничение размера сообщения, JSON parse, проверка object |
| `exact_snapshot(value)` | Проверка согласованности maxPoints, pointCount и remainingPoints |
| `summarize_intervals(intervals)` | Расчёт frame_count, average/median FPS, median/p95/max interval |
| `RunRecorder` | Агрегатор событий одного run |
| `persist_json_atomically(path, payload, ...)` | Атомарная запись JSON с retry для временных Windows PermissionError |
| `make_handler(token, origin, output_dir, idle_seconds)` | Создание WebSocket handler: auth, session, sequence и маршрутизация сообщений |
| `run_server(...)` | Генерация tokenized snippet и запуск WebSocket сервера |
| `main()` | CLI разбор аргументов и запуск asyncio сервера |

### 5.3. Методы RunRecorder

- `_start(event)` — открывает run, фиксирует pre snapshot, начальный радиус и baseline diagnostics.
- `_append_event(event)` — добавляет событие, обновляет post snapshot, accepted points и ошибки Monitor.
- `_event_stroke_id(event)` — определяет stroke identity, используя active stroke как fallback для старых событий.
- `_begin_stroke(event, now, source)` — начинает stroke/run и записывает источник lifecycle (engine или pointer_observer).
- `_end_stroke(event, now, source)` — закрывает stroke, суммирует активную длительность и завершает run при отсутствии активных штрихов.
- `event(event, now)` — проверяет allowlist и обрабатывает lifecycle/event.
- `frame_probe(message)` — сохраняет raw frame intervals и stroke_id текущего run.
- `note_collector_sequence_gap(missing_count)` — учитывает пропущенные sequence текущего run.
- `heartbeat(status, now, bridge_diagnostics)` — обновляет baseline/end counters Monitor и browser send failures; при idle timeout финализирует run.
- `finalize(status="partial")` — рассчитывает CHALK, per-stroke point timing, frame_probe_by_stroke, stroke counts, sampled point delta, радиусы и нижнюю границу длины наблюдаемой траектории; сохраняет raw frame_probes в run JSON.

### 5.4. Правила lifecycle и расхода CHALK

Run открывается при `DRAW_START` или `POINTER_DOWN_CANDIDATE`. Завершение соответствующей пары событий закрывает активный штрих. При завершении последнего активного штриха execution_status становится completed. Heartbeat после `idle_seconds` финализирует run как completed либо partial по фактическому lifecycle. При закрытии WebSocket незавершённый run финализируется как partial.

Точный расход рассчитывается только при наличии согласованных exact pre/post snapshots с одинаковым maxPoints:

`consumed_points = post.pointCount - pre.pointCount`.

Если snapshots отсутствуют/несогласованы или delta отрицательная, `chalk.status` становится inconclusive. Сумма положительных/нулевых DRAW_SAMPLE.pointDelta отдельно сверяется с exact CHALK; результат записывается в `point_delta_matches_chalk`, если выборки полны.

Радиус агрегируется из currentRadius в snapshots событий. Несколько различных значений дают `brush_radius_status="mixed"`; отсутствие значения — unavailable. Длина траектории считается по сохранённым acceptedPoint, но явно маркируется как нижняя граница: coalesced pointDelta могут скрывать промежуточные координаты. Она не заменяет точный CHALK.

## 6. Форматы и расположение файлов

Корневая папка результатов по умолчанию:

`AutoDraw_Stage20/data/results/brush_behavior_tests/game_monitor_bridge/`

Фактический путь может быть переопределён через `--output-dir`.

Структура:

```text
game_monitor_bridge/                         (п)
└── <session_uuid>/                          (п)
    ├── session.json                         (ф)
    └── game-monitor-run-<timestamp>-<id>.json (ф)
```

### session.json — schema_version 2

Содержит session_id, started_at_utc, run_idle_seconds, browser/page, monitor_status_at_connect и bridge_diagnostics. Основные поля diagnostics:

- received_message_count, received_event_count, received_event_types;
- last_message_type, last_sequence, last_message_at_utc;
- collector_sequence_gap_count;
- last_monitor_status, browser_bridge;
- frame_probe_count, connection_closed, closed_at_utc;
- при проблемах атомарной записи — session_persist_failures и last_session_persist_error.

Sequence начинается с 1 для session_start. Collector отвергает нецелое или не возрастающее значение; положительный разрыв учитывает как sequence gap. Это счётчик пропуска сообщений транспортного протокола, а не доказательство потери конкретного игрового штриха.

### Run JSON — schema_version 1

Содержит record_type, session_id, run_id, started/finished timestamps, execution_status, pre/post snapshots, brush_radius, events, frame probes и агрегаты:

- chalk: exact consumed_points либо inconclusive reason;
- stroke_count, stroke_candidate_count, non_consuming_stroke_candidate_count;
- stroke_lifecycle_sources;
- sampled_point_delta_total, point_delta_matches_chalk;
- observed_brush_radii, brush_radius_status;
- trajectory.observed_segment_length_lower_bound и статус полноты;
- frame_probe aggregate summary, frame_probe_by_stroke summaries и raw frame_probes intervals;
- per_stroke_metrics: pointCount delta, stroke duration, число POINT_QUOTA_UPDATE, accepted points/sec и интервалы между принятыми обновлениями;
- dropped_events, monitor buffer/error deltas, bridge_send_failures_delta, collector_sequence_gap_count.

Run файл записывается в session directory под именем `game-monitor-run-*.json`. `session.json` — отдельный живой журнал транспортной сессии и diagnostics.

## 7. Запуск и интеграция с UI

UI лаборатории кистей вызывает запуск companion процесса через `start_game_monitor_bridge.bat`, копирует исходник Monitor и tokenized snippet. Launcher запускает collector с точным Origin игрового iframe и каталогом результатов. Для portable-сборки файлы из `source/game_monitor/` копируются в соседний с AutoDraw.exe каталог `game_monitor/`.

Справочные документы:

- [README Game Monitor](../source/game_monitor/README.md) — ручное подключение Monitor, команды DevTools и ограничения.
- [Карта UI интеграции](UI_INTEGRATION_MAP.md) — действия Brush Test UI и точки запуска.
- [Каталог файловых данных](FILE_STORAGE_CATALOG.md) — расположение результатов и экспериментальных файлов.

## 8. Ограничения интерпретации

1. Monitor export schemaVersion=1 не содержит Bridge sessionId/runId и транспортный sequence. Для связывания standalone export с Bridge run нужны внешние runtime artifacts.
2. Bridge browser diagnostics — счётчики, сообщаемые самим browser agent; collector сохраняет их, но они не являются криптографически подписанным доказательством.
3. P1 sampling step/delay не наблюдается Monitor автоматически. Его следует подтверждать по executor config/journal, а не выводить из факта наличия Monitor/Bridge run.
4. DRAW_SAMPLE фиксирует изменение pointCount, а не каждую координату. При pointDelta больше единицы восстановить полную траекторию из acceptedPoint нельзя.
5. `trajectory.observed_segment_length_lower_bound` — нижняя граница по наблюдаемым точкам, не полная длина пути.
6. `NETWORK_RESOURCE` отражает Resource Timing entries и не является полным аудитом сетевой активности.
7. Успешный portable build или unit/integration test не заменяет live проверку в реальном игровом iframe.
8. Exact CHALK относится к счётчику игровых точек (`BoardPane.max/less`), а не к площади пикселей, длине пути или визуальному качеству.

## 9. Исходники и тестовые точки

- `source/game_monitor/game_monitor.js`
- `source/game_monitor/game_monitor_bridge.js`
- `source/game_monitor/game_monitor_bridge_server.py`
- `source/game_monitor/tests/game_monitor.test.js`
- `tests/test_websocket_smoke_server.py`

Изменение API следует сопровождать обновлением этой справки и профильного [README Game Monitor](../source/game_monitor/README.md). Проверка справки на дату создания выполнена чтением текущих файлов исходников рабочей ветки; новые live-прогоны и тесты в рамках создания документа не запускались.


## 10. Per-stroke timing telemetry — 2026-11-04

Browser Bridge передаёт strokeId вместе с frame_probe. Collector сохраняет raw intervals для каждой пробы и дополнительно формирует frame_probe_by_stroke. Raw frame_probes больше не очищаются при finalize; общий frame_probe summary сохраняется для совместимости.

RunRecorder также формирует per_stroke_metrics по событиям POINTER_DOWN_CANDIDATE / DRAW_START, POINT_QUOTA_UPDATE и POINTER_UP_CANDIDATE / DRAW_END. В метриках отдельно записываются:
- exact point_count_before / point_count_after / point_count_delta, если lifecycle snapshots доступны;
- сумма дельт POINT_QUOTA_UPDATE и проверка её совпадения со stroke delta;
- stroke duration и accepted_points_per_second;
- median/p95/max интервалов между точечными обновлениями.

**Важное различие частот:** frame_probe измеряет browser requestAnimationFrame, а не Egret ENTER_FRAME. accepted_points_per_second и интервалы POINT_QUOTA_UPDATE показывают частоту принятых игровых точек, но не являются прямым счётчиком всех кадров движка. Не подменять одну метрику другой.

Для старых run JSON без strokeId у frame_probe сохраняется общий summary; per-stroke frame probe может быть unavailable. Старые finalized runs не содержат raw frame intervals, если прежний finalize уже очистил frame_probes.

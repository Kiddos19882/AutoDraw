# Game Monitor: автоматическое сохранение отчётов теста кисти

Статус: первая реализация read-only WebSocket telemetry bridge добавлена; автоматическая привязка к UI experiment.json и live-проверка нового bridge в Firefox ещё не завершены.

## Цель

Каждый запуск теста кисти должен получать собственный комплект телеметрии Game Monitor. AutoDraw не должен требовать от пользователя вручную выполнять `status()`, `download()` и выбирать скачанный JSON. Сохранение должно происходить в правильных контрольных точках и не терять события при очистке Monitor.

## Что сохранять

Для каждого прогона в отдельной папке эксперимента:

- `monitor_pre_test_status.json` — снимок перед первым рисующим действием;
- `monitor_post_test_status.json` — снимок сразу после завершения/остановки/ошибки исполнителя;
- `monitor_report.json` — полный экспорт Monitor с массивом events;
- `monitor_post_clear_status.json` — необязательный снимок после очистки, только для проверки готовности к следующему прогону; он не заменяет итоговый снимок.

Имена должны включать ID прогона или храниться внутри уникальной папки. Отчёты разных размеров кисти и разных повторов никогда не объединять.

## Контрольные точки и порядок

1. **Monitor preflight, до рисования.** Запросить status. Проверить `active === true`, `boardDetected === true`, отсутствие ошибок и точное совпадение `snapshot.radius` с целевым радиусом. Сохранить исходный status. При недоступности Monitor или mismatch заблокировать запуск.
2. **Завершение исполнения.** При штатном завершении, отмене Alt, исключении или остановке запросить status. Зафиксировать время, исход исполнения, число событий, droppedEvents, errors и фактический radius. Этот шаг должен вызываться из всех terminal paths исполнителя, а не только из happy path.
3. **Полный экспорт.** После итогового status и до любого `clear()` запросить полный экспорт (`export()` либо эквивалент `download()`) и сохранить JSON в папку текущего эксперимента. Экспорт должен включать все события прогона. Сохранить в манифесте относительный путь, размер файла, время сохранения и результат валидации JSON.
4. **Проверка сохранения.** Убедиться, что файл существует, JSON читается, содержит массив `events`, а eventCount/droppedEvents/errors согласуются с итоговым status. Только после этого выставлять `monitor_capture.status = saved`.
5. **Очистка Monitor.** Выполнять `clear()` только после успешного экспорта либо после явного решения пользователя продолжить с зафиксированным статусом ошибки сохранения. До очистки не запускать следующий прогон. После очистки можно сохранить отдельный post-clear status, чтобы проверить нулевые счётчики.
6. **Прерванный/ошибочный тест.** Не пропускать сохранение: экспортировать доступные события и записывать `execution_status = cancelled|failed`. Если Monitor недоступен, сохранить manifest с `monitor_capture.status = unavailable` или `save_failed`; не подменять это пустым успешным отчётом.

## Интеграционная архитектура

- AutoDraw владеет жизненным циклом теста и файловой системой.
- Game Monitor остаётся read-only источником телеметрии и не получает команды для мыши/игры. При этом он временно оборачивает методы BoardPane; отсутствие влияния на производительность не доказано.
- Целевой вариант — локальный защищённый bridge (loopback) из отдельной задачи автокалибровки. По нему AutoDraw запрашивает только чтение status/export и получает ответы; браузер не управляет исполнителем.
- Каждая сессия имеет случайный token, одноразовый session/run ID, sequence number, timestamp и строгую схему сообщений. Сервер слушает только 127.0.0.1; Origin allowlist, лимит размера сообщений, таймауты, один активный run. Не записывать token в логи.
- Проверить WebSocket из HTTPS игрового iframe в Firefox до реализации как обязательного транспорта: mixed-content, Local Network Access и Origin-политики могут запретить loopback-соединение. Не заявлять, что интеграция работает, пока не пройдёт отдельный browser smoke test.
- Если bridge ещё не реализован, оставить ручной fallback: пользователь выполняет status/export и прикрепляет JSON. Не считать ручной сценарий автоматическим сохранением.

## Протокол контрольных сообщений

Запрос AutoDraw:
`{type:"capture", sessionId, runId, checkpoint:"pre_test"|"post_test"|"post_clear", sequence, token}`

Ответ Monitor:
`{type:"capture_result", sessionId, runId, checkpoint, sequence, timestamp, status, resourceSnapshot, export}`

В `status` включить только публичный результат `AutoDrawGameMonitor.status()`; `resourceSnapshot` — отдельный checkpoint CHALK по контракту раздела 11; `export` — объект `AutoDrawGameMonitor.export()`. Для `post_clear` сохраняется только дополнительная контрольная точка после очистки. Никаких игровых команд, eval, произвольных имён методов или передачи JS-кода протокол не допускает. Повторные/устаревшие sequence, неверный token, чужой runId и неизвестные checkpoint отклоняются.

## Состояния сохранения в manifest

Рекомендуемая структура:

```json
{
  "monitor_capture": {
    "status": "saved",
    "transport": "loopback_bridge",
    "pre_test_status_path": "monitor_pre_test_status.json",
    "post_test_status_path": "monitor_post_test_status.json",
    "report_path": "monitor_report.json",
    "pre_test_captured_at": "ISO-8601 UTC",
    "post_test_captured_at": "ISO-8601 UTC",
    "report_saved_at": "ISO-8601 UTC",
    "report_event_count": 0,
    "dropped_events": 0,
    "errors": 0,
    "execution_status": "completed"
  }
}
```

Допустимые capture status: `pending`, `saved`, `unavailable`, `save_failed`, `invalid_report`, `partial`. Путь к файлу записывать только после фактической проверки файла.

## Изменения текущего Monitor API

Сейчас Monitor предоставляет `status()`, `export()`, `download()` и `clear()`. `status()` возвращает краткий объект, но сам его не сохраняет; `download()` сохраняет только полный экспорт через browser download. Для настоящего автоматического сохранения в папку эксперимента нужен bridge, который передаст оба объекта приложению. Не полагаться только на автоматическую загрузку браузера: браузерная папка загрузок не гарантирует нужный путь и надёжную привязку к конкретному эксперименту.

## План реализации

1. Проверить текущие terminal callbacks/ошибки/отмену исполнителя и определить единый hook завершения теста.
2. Проверить loopback WebSocket из Firefox 159 на реальном HTTPS iframe, включая Origin и permission prompts.
3. Реализовать минимальный read-only bridge и тесты протокола/авторизации/таймаутов.
4. Добавить файловый capture service в AutoDraw и manifest persistence.
5. Добавить pre-test и post-test capture; экспортировать до `clear()`.
6. Добавить тесты успешного, отменённого, ошибочного и частичного прогона, а также невозможности очистки до завершения экспорта.
7. После подтверждения bridge — интегрировать тот же capture workflow с автоматической калибровкой радиуса.
8. Только после unit/integration и browser smoke tests отметить функцию как выполненную.

## Критерии приёмки

- У каждого тестового прогона есть независимые pre-test status, post-test status и полный JSON export.
- Экспорт содержит только события текущего прогона; `clear()` не выполняется до его получения и проверки.
- Отмена и ошибка также сохраняют доступную телеметрию.
- Ошибка сохранения явно отображается и записывается в manifest.
- Запуск следующего теста блокируется, пока предыдущий capture не завершён или пользователь явно не подтвердил продолжение с потерей/недоступностью отчёта.
- Никаких выводов об экономии игрового ресурса только на основании path length или Monitor event count.


## 10. Уточнение границ безопасности и browser smoke test (30.10.2026)

### 10.1. Monitor не является полностью пассивным на уровне JavaScript

Проверка реализации `source/game_monitor/game_monitor.js` выявила важное уточнение: Monitor не вызывает игровые команды и не меняет значения кисти/доски намеренно, но `attach()` временно заменяет методы экземпляра BoardPane обёртками (`onDrawStart`, `onDrawing`, `onDrawingEnd`, `setRadius`, `updateLess`). При `stop()` он пытается восстановить исходные descriptors/методы через `detach()`.

Поэтому корректное описание сейчас: **наблюдатель без команд управления игрой, с временной инструментализацией методов BoardPane**. Называть его полностью пассивным/неинвазивным нельзя до отдельного сравнения поведения и проверки восстановления методов. Это отдельный риск P3; bridge не должен расширять этот риск.

Критерии перед признанием Monitor безопасным:
- сравнить descriptors и ссылки методов до attach, после attach и после stop;
- проверить stop/start, повторный attach, исчезновение и повторное появление BoardPane;
- проверить восстановление при исключении и частичном отказе установки wrapper;
- сравнить игру с Monitor и без него (время/частота событий, точки доски, стабильность);
- не допускать управления игрой через bridge.

### 10.2. Минимальный Firefox smoke test — до реализации bridge

Проверяется только доступность транспорта, не Monitor и не корректность игрового состояния.

1. Запустить локальный тестовый WebSocket endpoint, который слушает исключительно `127.0.0.1`, принимает только ожидаемый Origin игрового iframe и требует случайный одноразовый challenge/token.
2. Открыть DevTools именно внутри игрового iframe (не top frame) и убедиться, что `location.origin` совпадает с Origin allowlist тестового сервера.
3. Из Console создать WebSocket к `ws://127.0.0.1:<port>`, пройти одноразовую авторизацию JSON-сообщением `auth`, затем отправить `ping` с nonce `autodraw-bridge-smoke-test`; сервер должен вернуть `ready`, затем `pong` с тем же nonce.
4. Зафиксировать отдельно: конструктор WebSocket, `open`, `message`, `error`, `close`, текст ошибки Firefox, Origin, версию браузера, адрес/порт endpoint. Секретный challenge не включать в общий лог.
5. Повторить с неверным Origin и неверным challenge: оба запроса должны быть отклонены сервером. Проверить, что endpoint недоступен через LAN-интерфейс.
6. Повторить после перезагрузки iframe. Никакие вызовы `AutoDrawGameMonitor.clear()`, игровые методы или перемещение мыши в smoke test не выполняются.

Результаты интерпретировать раздельно:
- если соединение блокируется до HTTP Upgrade политикой браузера — сохранить точный Firefox error и не обходить защиту через ослабление безопасности;
- если соединение открывается, но сервер отклоняет Origin/token — это отказ серверной проверки, а не mixed-content;
- если echo успешен — подтверждён только транспорт из этого iframe/профиля Firefox, не готовность production bridge.

**Ограничение текущей проверки:** удалённый GitHub CI не может подтвердить соединение из пользовательского Firefox/iframe на локальном компьютере. До выполнения этого smoke test статус WebSocket остаётся `not_tested`; CI Windows build не заменяет browser test.

### 10.3. Требования к следующему протоколу

Предложенный выше JSON-протокол является логической схемой, а не окончательной реализацией. До кода необходимо определить handshake: сервер генерирует одноразовый случайный секрет при старте, секрет передаётся пользователю локально и не хранится в репозитории; сервер проверяет точный Origin и token до приёма сообщений. Token не должен передаваться в URL, логах или событиях Monitor.

Bridge принимает только фиксированные операции чтения (`status`, `export`) и валидированные поля `sessionId/runId/sequence/checkpoint`. Запрещены произвольные имена методов, eval, команды управления мышью, `clear` и `stop`. Очистка остаётся отдельным локальным действием AutoDraw и возможна только после успешного сохранения экспорта.


### 10.4. Реализация локального transport smoke server

Добавлены отдельные файлы:
- `source/game_monitor/websocket_smoke_server.py` — одноразовый локальный сервер;
- `source/game_monitor/requirements-smoke.txt` — изолированная зависимость `websockets==12.0`, не добавленная в runtime приложения;
- `tests/test_websocket_smoke_server.py` — unit/integration проверки токена, формата сообщений, Origin и ping/pong.

Сервер слушает только `127.0.0.1`, принимает один точный HTTPS Origin, ограничивает сообщение 1024 байтами, ждёт handshake и ping не более 5 секунд, использует одноразовый случайный token (32 случайных байта в URL-safe представлении) и не пишет token в логи. Поддерживаются только две схемы сообщений: `auth` и `ping`; ответ — `ready` и `pong`. Сервер не предоставляет доступ к Game Monitor, не вызывает игровых методов и не умеет управлять мышью, очищать события или останавливать Monitor.

**Запуск в Windows PowerShell** из корня репозитория:

```powershell
py -3.11 -m pip install -r .\\AutoDraw_Stage20\\source\\game_monitor\\requirements-smoke.txt
py -3.11 .\\AutoDraw_Stage20\\source\\game_monitor\\websocket_smoke_server.py --origin https://ORIGIN-ИЗ-IFRAME
```

До запуска получить точное значение `location.origin` в Console именно игрового iframe. Передавать только origin (scheme + host + optional port), без пути. Не угадывать домен. Сервер выведет одноразовый token в локальный терминал; не отправлять его в чат, issue или commit.

В Console игрового iframe выполнить, заменив `PASTE_TOKEN_HERE` локальным значением из терминала:

```javascript
(() => {
  const ws = new WebSocket("ws://127.0.0.1:8765");
  ws.addEventListener("open", () => {
    ws.send(JSON.stringify({ type: "auth", token: "PASTE_TOKEN_HERE" }));
  });
  ws.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    console.log("AutoDraw smoke message:", message);
    if (message.type === "ready") {
      ws.send(JSON.stringify({ type: "ping", nonce: "autodraw-bridge-smoke-test" }));
    }
  });
  ws.addEventListener("error", () => console.error("AutoDraw smoke WebSocket error"));
  ws.addEventListener("close", (event) => {
    console.log("AutoDraw smoke WebSocket closed:", event.code, event.reason);
  });
})();
```

Ожидаемый результат: сообщения `{type: "ready"}` и `{type: "pong", nonce: "autodraw-bridge-smoke-test"}`, затем close code 1000. Неверный token должен завершить соединение кодом 4003. Неверный Origin отклоняется до открытия WebSocket handshake; эта отрицательная проверка дополнительно покрывается автоматическим integration test. Сервер останавливается Ctrl+C.

Текущий статус реализации: код и CI-тесты добавлены, но browser test на пользовательском Firefox ещё не выполнялся. Статус live browser transport остаётся `not_tested` до результата пользователя. Веб-сокет smoke server — временная тестовая оснастка, не production bridge.


## 11. Ресурсный snapshot CHALK и низконагрузочная телеметрия — INT-002, 31.10.2026

### 11.1. Что считается фактическим расходом

Игровая квота — количество сохранённых точек `atom.points`. Для отдельного опыта:

```text
consumed_points = post_test.point_count - pre_test.point_count
```

Если в будущем будет доступен точный `less`, эквивалентная формула при неизменном лимите:

```text
consumed_points = pre_test.less - post_test.less
```

Pre-test checkpoint снимается после подтверждённой очистки и до первого штриха. Post-test снимается после завершения/остановки/ошибки исполнителя, но до следующего Clear. Возможная служебная точка после Clear тем самым входит в baseline, а не в расход опыта.

### 11.2. Контракт checkpoint

Каждый ресурсный checkpoint должен содержать:

- `experiment_id` — стабильный UUID всего эксперимента;
- `run_id` — уникальный ID отдельного прогона/повтора;
- `checkpoint` — `pre_test`, `post_test` или `post_clear`;
- `sequence`, `captured_at_utc`, `captured_at_performance_ms`;
- `board_session_id`, `board_item_type`;
- `max_points`, `remaining_points`, `point_count`;
- `baseline_point_count`, `consumed_points` (последние два — когда применимы);
- `source_method`, `is_exact`, `validation_status`.

Снимки должны иметь одинаковые `board_session_id` и `max_points`. Значения `point_count`/`remaining_points` — целые в диапазоне от нуля до лимита. При смене доски/лимита, отрицательной дельте, отсутствии baseline или неподтверждённом источнике расход получает статус `inconclusive`, а не число с ложной точностью.

### 11.3. Точный источник статически подтверждён; runtime-сверка остаётся

В bundle из `master` конструктор `BoardPane` устанавливает `this.max=n` и `this.less=this.max`. Метод `updateLess()` пересчитывает точки `atom.points`, затем записывает `this.less=this.max-e` и отправляет CHALK event с `percent=this.less/this.max`.

Следовательно, точные целочисленные `max` и `less` доступны как поля экземпляра по исходному коду. Восстанавливать целое значение из `percent` не требуется. Game Monitor 0.2.0 читает эти поля напрямую и вычисляет `pointCount=max-less`. Статическое подтверждение ещё не заменяет проверку живого экземпляра доски в iframe.

### 11.4. Требования к overhead

В `game_monitor.js` 0.1.2 `boardSnapshot()` выполнял полные проходы по `atom.points` для подсчёта и поиска последней точки. В версии 0.2.0 `resourceSnapshot()` читает `BoardPane.max`/`less` за O(1); полный O(N) обход вынесен в явный `diagnosticSnapshot()`. Структурное устранение дополнительных array scans подтверждается кодом и Node-тестами; количественное влияние на FPS требует A/B-замера.

Реализованная в Monitor 0.2.0 структура:

- лёгкий O(1) `resourceSnapshot()` читает только уже вычисленные и проверенные значения;
- `emit()` не строит тяжёлый snapshot неявно;
- O(N) `diagnosticSnapshot()` выполняет полный подсчёт только по явному запросу на редких контрольных точках;
- не сканировать `atom.points` на каждом кадре и не дублировать подсчёт, который уже выполняет игра;
- A/B измерение FPS и фактических point delta обязательно до заявления, что оптимизированный Monitor не влияет на игру.

### 11.5. Существующие оценочные модели AutoDraw

- `paint_cost_model.py` — legacy px-equivalent, не прямой CHALK.
- `board_resource_model.py` — оценка точек по калиброванному points-per-path и стартовой точке штриха.
- `engine_point_calibration.py` — теоретическая/эмпирическая оценка frame-sampled points; номинальные 48 FPS не равны измеренному FPS старых опытов.
- `game_point_calibration.py` — интервальная подгонка по порогам видимости штрихов и browser frame probe; отчёт явно `is_engine_exact_counter=false`.

Эти оценки можно использовать в preflight с явным признаком `is_estimate=true`, профилем условий и safety factor. Они не заменяют точную фактическую дельту.

### 11.6. Следующие задачи

- INT-003: завершить runtime-проверку `max`/`less` в живом iframe и измерить A/B/C overhead: без Monitor, Monitor 0.1.2, Monitor 0.2.0. Статическая проверка источника, реализация 0.2.0 и Node-тесты уже выполнены.
- INT-004: расширить уже описанный loopback bridge и manifest capture стабильным `experiment_id` и ресурсными checkpoints.

### 11.7. Протокол A/B-проверки overhead для INT-003

1. Сравнивать три режима: A — Monitor выключен; B — Monitor 0.1.2 включён; C — Monitor 0.2.0 включён. Не объединять B и C в одну группу.
2. Зафиксировать один тип доски и лимит, одну и ту же доску/ROI, одинаковые разрешение, zoom, browser, план, фактический радиус кисти и параметры исполнителя (`point_step_px`, `point_delay_ms`).
3. Выполнить не менее трёх повторов каждого режима; чередовать порядок A/B/C, чтобы не смешивать влияние прогрева/нагрузки браузера с влиянием Monitor.
4. В каждом повторе фиксировать frame probe (average/median FPS, median/p95/max frame interval), wall-clock duration, фактическую дельту точек на независимых контрольных точках, число завершённых/пропущенных штрихов и визуальную проверку результата.
5. Для режима B дополнительно сохранить Monitor version, eventCount, droppedEvents, errors и фактическое время экспорта. Для режима A источник pointCount должен быть независимым от Monitor; если точную дельту получить нельзя, результат A/B по расходу считается неполным.
6. Сравнивать медианы и разброс по повторам, а не один запуск. Не вводить заранее численный допуск overhead до получения базовой вариативности; сначала определить шум измерения.
7. Не запускать следующий опыт до подтверждения Clear и сохранения всех доступных измерений. Любой сбой/изменение условий помечать как `inconclusive`, а не удалять из журнала.

## 12. Уточнение INT-003: прямые поля BoardPane и Monitor 0.2.0 — 31.10.2026

Статически подтверждены поля `BoardPane.max` и `BoardPane.less` в клиентском bundle:
- конструктор задаёт `this.max=n`, `this.less=this.max`;
- `updateLess()` пересчитывает `atom.points` и присваивает `this.less=this.max-e`;
- событие CHALK передаёт только `percent`, но точные целые значения доступны на экземпляре.

Game Monitor 0.2.0 читает `max` и `less` через O(1) `resourceSnapshot()`. Значение `pointCount=max-less` является exact при валидных целых полях. Отсутствующие/невалидные поля возвращают `unavailable`; скрытого array fallback нет. Полный O(N) diagnostic scan доступен только через `diagnosticSnapshot()`.

Добавлены Node-тесты и CI step. Результаты GitHub Actions должны быть проверены отдельно; локальный запуск Node в среде разработки недоступен.

**Не выполнено:** runtime-сверка на живом BoardPane и A/B/C FPS/duration. До неё INT-003 остаётся IN_PROGRESS.


## 13. Первая реализация автоматического WebSocket telemetry bridge — 31.10.2026

Добавлены:
- `source/game_monitor/game_monitor_bridge.js` — браузерный агент, который подключается к loopback WebSocket, подписывается на события Monitor через новый API `AutoDrawGameMonitor.subscribe(listener)`, отправляет ограниченный allowlist событий и heartbeat;
- `source/game_monitor/game_monitor_bridge_server.py` — локальный сервер-приёмник с точной Origin allowlist, случайным токеном, ограничением размера сообщения, одним активным браузерным соединением и автоматическим сохранением run JSON;
- `source/game_monitor/requirements-bridge.txt` — изолированная зависимость `websockets==12.0`;
- расширены Node/Python regression tests: подписка/отписка от событий, синтаксис browser agent, baseline/post CHALK delta, неполные acceptedPoint samples, idle finalization, FPS summary и Origin validation.

### Что теперь автоматизировано

- Пользователь один раз загружает Game Monitor и вставляет сгенерированный сервером browser snippet в Console игрового iframe.
- Каждый `DRAW_START` автоматически открывает run; непрерывная серия штрихов собирается в один run. После `DRAW_END` и idle timeout отчёт автоматически сохраняется.
- Pre snapshot берётся из `DRAW_START.before`, post snapshot — из `DRAW_END.after`; точный CHALK delta рассчитывается только при валидных согласованных integer snapshots.
- Сохраняются фактические радиусы, события, pointDelta, принятые координаты, число событий, локальные ошибки, длительность активных штрихов и FPS, измеренный requestAnimationFrame во время каждого штриха.
- При потере соединения незавершённый run сохраняется как partial.
- Отчёты записываются атомарной заменой временного файла в отдельный каталог session UUID. Секретный токен не записывается в JSON.

### Что ещё не закрыто

1. Live-проверка нового bridge из реального Firefox iframe: handshake, reconnect/close, появление session.json и run JSON.
2. Автоматическая привязка созданного run JSON к конкретному UI `experiment.json` по experiment_id/run_id. Пока bridge пишет отдельный session/run каталог.
3. Проверка того, что idle timeout 2.5 s корректно объединяет все штрихи одного DrawingPlan и разделяет соседние тесты. Значение можно настроить через `--idle-seconds`.
4. Проверка overhead от передачи событий и requestAnimationFrame probe. Сравнивать тесты кистей нужно при одинаково включённом bridge; сам сборщик нельзя объявлять нулевым overhead.
5. Полный экспорт Monitor не запрашивается единым вызовом `export()`: события собираются инкрементально через subscribe, что избегает повторной сериализации растущего массива. Корневые session metadata и события хранятся раздельно.

**Статус INT-004:** IN_PROGRESS. Автоматический сбор и автоматическая привязка run JSON к UI manifest реализованы. Live Firefox validation, тестирование корреляции при повторных одинаковых радиусах и измерение overhead остаются обязательными.


## 14. Автоматическая привязка bridge run к Brush Test manifest — 31.10.2026

В `brush_behavior_test_ui.py` добавлен автоматический post-execution capture:
- после callback завершения executor UI начинает опрашивать стандартный каталог `<output_dir>/game_monitor_bridge/`;
- выбирается отчёт с `record_type=autodraw_game_monitor_run`, временем старта не раньше фазы `before_draw` и радиусом, совпадающим с запрошенным размером кисти;
- отчёт копируется в каталог конкретного эксперимента как `monitor_report.json`;
- в `experiment.json` сохраняются путь, session_id, run_id, CHALK summary, FPS, траектория, event count, dropped events и capture status;
- если подходящий отчёт не появился за 10 секунд, в manifest записывается `monitor_capture.status=unavailable`, без подмены пустым успешным результатом;
- при старте нового эксперимента отменяется предыдущий polling callback.

**Ограничение корреляции:** текущая привязка основана на timestamp `before_draw` + фактическом радиусе, а не на общем experiment_id, переданном из UI в browser session. При последовательных одинаковых тестах с перекрывающимися временными окнами нужна дополнительная проверка; прямой run marker будет предпочтительным следующим улучшением.


## 15. Строгая проверка полноты телеметрии — 31.10.2026

Run JSON дополнен автоматическими контрольными метриками:
- `stroke_count` — число `DRAW_START` в run;
- `sampled_point_delta_total` — сумма неотрицательных целочисленных `pointDelta` из `DRAW_SAMPLE`;
- `point_delta_matches_chalk` — совпадает ли сумма sample deltas с exact pre/post CHALK delta, если все samples имеют валидный delta;
- `observed_brush_radii` и `brush_radius_status` (`single`, `mixed`, `unavailable`) — проверка, что внутри одного run кисть не менялась;
- `monitor_dropped_events`, `dropped_events`, `monitor_error_count` — потери и ошибки Monitor/collector.

Brush Test UI выставляет `monitor_capture.status=saved` только если одновременно: execution completed, CHALK exact, один наблюдаемый радиус, сумма pointDelta совпала с CHALK, нет dropped events и нет ошибок Monitor. Во всех остальных случаях отчёт сохраняется, но статус остаётся `partial`; данные не отбрасываются и не маскируются как успешные.


### Уточнение критерия capture=saved

UI считает сбор полностью успешным только при положительном расходе CHALK и наличии хотя бы одного штриха/acceptedPoint, exact pre/post snapshots, совпадении суммы `pointDelta` с CHALK delta, одном наблюдаемом радиусе, измеренном FPS без visibility interruption, нулевых dropped events и нулевых Monitor errors. Отчёт с нулевым расходом, пустыми accepted points, недоступным FPS или прерванной видимостью всё равно сохраняется, но получает `partial`.


## 16. Диагностика сессии, когда создан только session.json

`session.json` подтверждает только принятие `session_start`. Run JSON создаётся при получении `DRAW_START`, затем завершается по idle heartbeat или закрытию соединения. Если после теста присутствует только session.json, нельзя считать WebSocket сбор работающим.

Для локализации причины browser agent передаёт в heartbeat собственные `sentEventCount`, `lastEventType`, `lastEventAtPerformanceMs`, `sendFailureCount`. Collector сохраняет в session.json после каждого сообщения `received_message_count`, `received_event_count`, `received_event_types`, `last_sequence`, `last_message_type`, последний `monitorStatus`, browser bridge diagnostics, число frame probes и факт закрытия соединения. Это позволяет различить: Monitor не генерирует события; browser subscription не отправляет события; сервер не принимает события; либо recorder не создаёт/не финализирует run.

После обновления server и snippet необходимо перезапустить локальный bridge и повторно вставить snippet в iframe: запущенный процесс и уже вставленный snippet не обновляются автоматически при изменении файлов репозитория. Затем выполнить один короткий тест и изучить session.json. До успешного появления run JSON и проверки CHALK delta нельзя считать live bridge интеграцию принятой.




## 17. Live session 323a698: root cause отсутствия run JSON

Сессия `f303b3e1-382e-4859-9681-e1c360ec6424` подтвердила полноценную доставку событий browser bridge → collector: 119 событий отправлено и принято, ошибок отправки/Monitor и dropped events — 0. Счётчик доски изменился с 1 до 49 (`ΔpointCount=48`) при exact snapshots. Получено 8 pointer-down/up пар, 55 DRAW_SAMPLE и 48 POINT_QUOTA_UPDATE, но 0 DRAW_START/DRAW_END; frame_probe_count равен 0.

Причина найдена в текущем коде:
- Game Monitor умеет отслеживать указатель независимо от BoardPane callbacks: `onPointerDown` создаёт `POINTER_DOWN_CANDIDATE` и включает polling; `onPointerUp` завершает polling и создаёт `POINTER_UP_CANDIDATE`.
- Browser bridge запускает FPS probe только по `DRAW_START`, останавливает по `DRAW_END`.
- RunRecorder начинает run только по `DRAW_START` и отмечает завершение штриха только по `DRAW_END`.

В этой реальной сессии engine callbacks не были зафиксированы, поэтому pointer fallback не пересёк lifecycle boundary collector. Это не потеря WebSocket сообщений. Точный расход 48 points относится ко всему временному интервалу сессии и не должен автоматически считаться расходом одного Brush Test experiment.

**Обязательное исправление:** поддержать pointer candidate как fallback lifecycle в RunRecorder и FPS probe, при этом явно маркировать источник границ и не удваивать штрихи при одновременных engine/pointer событиях. Нужны regression tests для pointer-only, engine-only и смешанного потока. До этих изменений нельзя считать автоматическую генерацию run JSON и FPS capture работающими в live режиме.

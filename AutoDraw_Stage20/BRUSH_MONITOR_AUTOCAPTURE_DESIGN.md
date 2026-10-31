# Game Monitor: автоматическое сохранение отчётов теста кисти

Статус: проектирование; автоматическая интеграция ещё не реализована и не проверена в браузере.

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
2. **Завершение исполнения.** При штатном завершении, отмене F12, исключении или остановке запросить status. Зафиксировать время, исход исполнения, число событий, droppedEvents, errors и фактический radius. Этот шаг должен вызываться из всех terminal paths исполнителя, а не только из happy path.
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

### 11.3. Источник точных значений — открытый вопрос runtime-валидации

`BoardPane.updateLess()` пересчитывает число точек и вычисляет `less = max - pointCount`, после чего отправляет событие CHALK с `percent = less / max`. Текущий Monitor JSON содержит `pointCount`, но не `max` и `less`. Статический source scan не доказывает, что `max` и `less` доступны как стабильные поля экземпляра `BoardPane`; поэтому нельзя считать `board.max`/`board.less` гарантированным O(1) API.

Кандидаты для проверки в INT-003:

1. проверить, сохраняет ли экземпляр `BoardPane` значения лимита/остатка как доступные числовые поля;
2. проверить payload события CHALK: содержит ли оно только `percent` или также точные целочисленные значения;
3. если доступен только `percent`, проверить точность и округление; восстановление `less = round(percent × max)` допускается считать exact только после сравнения с диагностическим подсчётом массива на контрольных точках;
4. если ни поля, ни точное событие недоступны, не маскировать проблему дополнительным подсчётом массива на каждом кадре. В таком случае нужен отдельный, явно одобренный более глубокий способ инструментирования движка.

### 11.4. Требования к overhead

Текущий `boardSnapshot()` выполняет рекурсивный `pointCount(atom.points)` и поиск `lastPoint(atom.points)`. `emit()` автоматически строит snapshot; `wrapMethod()` строит snapshot до/после оригинального метода; `onDrawing` дополнительно вызывает `sampleActiveStroke`; polling с интервалом 25 ms также сканирует массив и может вызвать ещё один snapshot при изменении. В результате Monitor добавляет несколько O(N)-проходов к уже существующему полному подсчёту внутри `updateLess()`.

Целевая структура:

- лёгкий O(1) `resourceSnapshot` читает только уже вычисленные и проверенные значения;
- `emit()` не строит тяжёлый snapshot неявно;
- O(N) `boardSnapshot` остаётся только диагностическим методом для редких контрольных точек;
- не сканировать `atom.points` на каждом кадре и не дублировать подсчёт, который уже выполняет игра;
- A/B измерение FPS и фактических point delta обязательно до заявления, что оптимизированный Monitor не влияет на игру.

### 11.5. Существующие оценочные модели AutoDraw

- `paint_cost_model.py` — legacy px-equivalent, не прямой CHALK.
- `board_resource_model.py` — оценка точек по калиброванному points-per-path и стартовой точке штриха.
- `engine_point_calibration.py` — теоретическая/эмпирическая оценка frame-sampled points; номинальные 48 FPS не равны измеренному FPS старых опытов.
- `game_point_calibration.py` — интервальная подгонка по порогам видимости штрихов и browser frame probe; отчёт явно `is_engine_exact_counter=false`.

Эти оценки можно использовать в preflight с явным признаком `is_estimate=true`, профилем условий и safety factor. Они не заменяют точную фактическую дельту.

### 11.6. Следующие задачи

- INT-003: проверить точный источник CHALK в живом iframe и измерить overhead текущего Monitor 0.1.2 сравнением без Monitor/с Monitor.
- INT-004: расширить уже описанный loopback bridge и manifest capture стабильным `experiment_id` и ресурсными checkpoints.
- Реализация и browser/game tests не входят в INT-002; для них нужны отдельные разрешения.
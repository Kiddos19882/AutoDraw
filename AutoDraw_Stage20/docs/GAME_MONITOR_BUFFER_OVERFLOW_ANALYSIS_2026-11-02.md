# Диагностика переполнения буфера Game Monitor — 2026-11-02

## Итог

Причина `monitor_dropped_events=434` в G3 установлена по коду и сохранённому `session.json`: достигнут глобальный лимит локального массива событий Game Monitor (`MAX_EVENTS=50000`). Это не потеря 434 событий в WebSocket и не доказательство потери событий именно внутри проблемного эксперимента.

В `emit()` сначала выполняется ограниченная запись в `state.events`, затем независимо вызываются все подписчики. После заполнения массива новые элементы не сохраняются в локальный экспортный буфер, `state.droppedEvents` увеличивается, но подписчики продолжают получать исходные события. Browser Bridge подписан через `AutoDrawGameMonitor.subscribe()` и отправляет их по WebSocket.

## 1. Доказательства из исходного G3 запуска

Источник: experiment `b9abd01839094a66bfba9f27d52fb02c`, задача `paint_consumption_long_lines-s4-d10-r2`, session `e3ba66d3-93ba-4f0f-aaf0-bc271d30f6e1`.

### Счётчики сессии

| Поле | Значение |
|---|---:|
| `monitor_status_at_connect.eventCount` | 252 |
| `monitor_status_at_connect.droppedEvents` | 0 |
| `browser_bridge.sentEventCount` | 50 320 |
| `bridge_diagnostics.received_event_count` | 50 320 |
| `last_monitor_status.eventCount` | 50 000 |
| `last_monitor_status.droppedEvents` | 572 |
| `browser_bridge.sendFailureCount` | 0 |
| `bridge_diagnostics.last_sequence` | 52 324 |
| `bridge_diagnostics.received_message_count` | 52 324 |

Типы событий, принятые сервером, в сумме дают ровно 50 320:
- `POINTER_DOWN_CANDIDATE`: 221
- `DRAW_SAMPLE`: 22 169
- `POINTER_UP_CANDIDATE`: 221
- `BRUSH_CHANGE`: 2 870
- `BRUSH_CHANGE_APPLIED`: 2 870
- `POINT_QUOTA_UPDATE`: 21 969

Баланс внутреннего буфера сходится точно:

`252 + 50 320 = 50 572 = 50 000 + 572`

То есть 252 события уже находились в Monitor до подключения Bridge; затем подписчик получил ещё 50 320 событий. Внутренний массив сохранил максимум 50 000, а оставшиеся 572 не попали только в этот массив. Сервер при этом получил все 50 320 событий, которые Bridge отправил после подключения.

`received_message_count` совпадает с `last_sequence`; отдельные счётчики отправленных и принятых событий совпадают. `sendFailureCount=0`. По сохранённой диагностике нет признаков потери в WebSocket/collector для этой сессии.

## 2. Почему именно один G3 capture стал partial

Проблемный experiment содержит:
- 744 события в сохранённом run;
- `dropped_events=0` у серверного RunRecorder;
- `monitor_dropped_events=434`;
- `monitor_error_count=0`;
- точный CHALK delta 363;
- `sampled_point_delta_total=363`;
- совпадение `point_delta_matches_chalk=true`.

В момент завершения этого run глобальный счётчик Monitor уже показывал 434. Позднее в той же session он вырос до 572 (ещё на 138). Это подтверждает накопительный характер счётчика.

`RunRecorder.heartbeat()` копирует `status.droppedEvents` в активный run без вычитания значения на старте run. Поэтому глобальный счётчик всей браузерной сессии попадает в поле конкретного experiment как `monitor_dropped_events`. При финализации это поле меняет `path_length_status` на `monitor_events_dropped`, а acceptance gate отклоняет capture.

Таким образом, acceptance gate спутал переполнение долговременного локального буфера Monitor с потерей событий текущего capture. Значение 434 не означает, что из этих 744 событий 434 отсутствуют. Сохранённый run содержит 744 события и точную дельту CHALK.

## 3. Проверка механизма

Проведена детерминированная проверка логики `emit()` на 50 320 событиях с `MAX_EVENTS=50000`:
- локальный массив сохранил 50 000;
- счётчик переполнения вырос на 320;
- callback подписчика получил все 50 320 событий, включая события после достижения лимита.

Результат соответствует реализации `game_monitor.js`: listener вызывается после проверки/записи в массив и вне ветки `if (state.events.length < MAX_EVENTS)`. Это кодовая симуляция поведения, а не новый live-тест игры.

## 4. Дополнительный фактор

`AutoDrawGameMonitor.clear()` очищает массив, `droppedEvents` и ошибки, но в проверенном Browser Bridge нет автоматического сброса буфера на границе эксперимента. В поиске по рабочей ветке вызов `AutoDrawGameMonitor.clear()` найден в README/документации, но не в производственном коде запуска G3.

Одна долгая WebSocket session используется для множества отдельных экспериментов. Поэтому глобальный буфер в 50 000 событий исчерпывается накопительно: в этой сессии 50 320 событий Bridge были переданы примерно за 30 минут, а Monitor уже имел 252 события до подключения Bridge.

## 5. Что это означает для качества G3

- Транспортная доставка событий в проблемной session подтверждена: sent=received=50 320, send failures=0.
- Серверный RunRecorder сохранил целевой run из 744 событий, его собственный `dropped_events=0`.
- CHALK delta и сумма `pointDelta` совпадают и равны 363.
- `monitor_dropped_events=434` не является per-run счётчиком потерь и не должен использоваться как доказательство пропуска 434 событий этого run.
- Статус `partial` возник из-за ложной интерпретации глобального буферного счётчика в качестве потерь текущего capture.
- Это не устраняет отдельное ограничение траектории: `pointDelta` может быть coalesced, поэтому полная последовательность промежуточных координат всё ещё не гарантирована.

Исторический статус G3 блока `stopped` и его журнал не переписываются. Даже если конкретный capture технически доставлен полностью, автоматически менять его статус задним числом нельзя без повторной проверки исходного run и формальных правил валидатора.

## 6. Рекомендуемое исправление

Не увеличивать `MAX_EVENTS` как единственное исправление и не отключать acceptance gate целиком.

1. Разделить метрики:
   - `monitor_buffer_dropped_events` — сколько событий не вошло в локальный экспортный массив за жизнь Monitor;
   - `bridge_send_failures` — ошибки отправки Browser Bridge;
   - `collector_received_event_count` и `collector_sequence_gaps` — серверная доставка;
   - `run_recorder_dropped_events` — переполнение per-run хранилища collector.
2. Не переносить накопительный `status.droppedEvents` в per-run поле `monitor_dropped_events` без baseline/delta и без точного определения семантики.
3. Для acceptance gate проверять полноту конкретного run: его lifecycle, ожидаемые штрихи, точный CHALK, совпадение sampled delta, ошибки Monitor, потери самого RunRecorder и целостность sequence/transport diagnostics.
4. Добавить regression test на более чем 50 000 событий: буфер ограничен, dropped counter растёт, subscriber продолжает получать события.
5. Добавить тесты на несколько последовательных runs в одной session: старое переполнение буфера не должно автоматически делать последующий run partial.
6. Опционально очищать локальный экспортный буфер между независимыми экспериментами, если это безопасно для текущего способа ручного экспорта. Это вспомогательная мера, а не замена раздельным счётчикам.

## 7. Границы выполненной проверки

В этой диагностике:
- изучены код `game_monitor.js`, `game_monitor_bridge.js`, `game_monitor_bridge_server.py` и `RunRecorder`;
- прочитан реальный `session.json` проблемного G3 запуска;
- прочитан `experiment.json` проблемного задания;
- выполнена детерминированная симуляция лимита буфера.

Код проекта не менялся, live-рисование не запускалось, workflow/CI не запускались, старые журналы и captures не изменялись.

## 8. Вывод

Причина G3 fail установлена с высокой уверенностью: **глобальный локальный буфер Game Monitor достиг 50 000 записей; его накопительный overflow-счётчик был ошибочно интерпретирован как потери событий конкретного run**. Browser Bridge и collector по диагностике этой session передали и приняли одинаковые 50 320 событий без ошибок отправки.

Следующая задача — исправить семантику счётчиков и acceptance gate, затем покрыть её регрессионными тестами до нового live G3 запуска.
## 9. Исправление реализовано (2026-11-02)

В коде feature-ветки внесены изменения:
- `RunRecorder` сохраняет session-cumulative Monitor buffer drops как `monitor_buffer_dropped_events_start/end/delta`; больше не меняет `trajectory.status` и не маркирует run как `monitor_events_dropped` только из-за переполнения локального export buffer.
- Cumulative Monitor errors также записываются как start/end/delta; acceptance использует `monitor_error_count_delta`.
- Browser Bridge `sendFailureCount` сравнивается с baseline run и сохраняется как `bridge_send_failures_delta`.
- Collector обнаруживает пропуски sequence, считает их в session diagnostics и записывает пропущенные sequence активного run как `collector_sequence_gap_count`.
- Brush Test gate и CHALK matrix validators больше не используют cumulative `monitor_dropped_events` / `monitor_error_count` как per-run rejection criteria. Они проверяют per-run `dropped_events`, `monitor_error_count_delta`, `bridge_send_failures_delta` и `collector_sequence_gap_count`.

Добавлены регрессионные тесты:
- Node: подписчик получает все события после достижения 50 000 лимита локального буфера;
- Python: cumulative overflow и прежние Monitor errors не портят следующий run;
- WebSocket integration: пропуск sequence фиксируется в session и run;
- матричные валидаторы: cumulative overflow принимается как диагностический счётчик, реальные per-run transport loss отвергаются.

**Статус:** код и тесты добавлены, но CI на конечном HEAD ещё не подтверждён. Live Firefox/game test не запускался. Исторический G3 journal и manifest `s4-d10-r2` не переписывались. До успешного CI и локального preflight live G3 не запускать.


## 10. Повторная live-проверка исправления в полной G3 серии — 2026-11-02

После исправления per-run метрик выполнен отдельный новый G3 block `chalk-20261102-031830-a0f325`, block ID `d5d28990cb954610aa7f58534be9d3d7`. Старый stopped block `chalk-20261102-015749-7c1141` не возобновлялся и не переписывался.

Результат:
- 27/27 задач completed; все девять комбинаций sampling имеют по три повтора.
- Все 27 captures имеют `monitor_capture.status=saved`, exact CHALK, совпадение sampled pointDelta, 6/6 strokes и radius=10.
- Во всех 27 runs: `dropped_events=0`, `monitor_error_count_delta=0`, `bridge_send_failures_delta=0`, `collector_sequence_gap_count=0`.
- В шести поздних runs `monitor_buffer_dropped_events_delta` положителен (536, 2718, 1456, 2700, 2706, 750). Это локальные потери сохранения в ограниченный export array Monitor, а не потеря доставки подписчику/Bridge/collector.
- Для проверенных overflow runs event count совпадает с `report_event_count`; RunRecorder drops, Bridge send failures и sequence gaps равны нулю. Например, run `515fa1ae` сохранил 2718/2718 событий при local buffer delta=2718.
- Session-cumulative alias `monitor_dropped_events` достиг 12 237, но ни один capture не был отклонён только по этому глобальному значению.

Это подтверждает, что исправленное разделение cumulative local-buffer overflow и per-run transport loss работает в реальной длительной сессии, а не только в regression tests.

Полные экспериментальные результаты и таблица CHALK: [CHALK_G3_RESULTS_2026-11-02.md](CHALK_G3_RESULTS_2026-11-02.md).

### CI и границы проверки

Перед этой серией полный workflow [41364954177](https://github.com/Kiddos19882/AutoDraw/actions/runs/41364954177) завершился успешно на code HEAD `09ef6283d8f02df64c458fe412049a1a190aff77`: все обязательные jobs, включая Windows portable build/startup smoke-test, success; optional benchmarks skipped. Коммит `35ae78e` добавил только экспериментальные результаты в `data/results/brush_behavior_tests/` и не менял исходный код или workflow, поэтому повторный CI для него не требовался.

**Итог:** G3 live block принят 27/27; overflow fix подтверждён live; исторические stopped journals сохранены без изменений. Секция 9 отражает состояние на момент её создания и более не описывает текущий статус CI/G3.

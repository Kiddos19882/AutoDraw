# Автоматизированные блоки экспериментов CHALK

**Статус:** ядро планирования и журналирования добавлено; интеграция полного автоматического запуска в Brush Test UI ещё не завершена.  
**Рабочая ветка:** `feature/image-geometry-optimization`.  
**Связанные документы:** `../CHALK_GEOMETRY_MATRIX_PLAN.md`, `CHALK_GEOMETRY_MATRIX_G1_RESULTS.md`, `BRUSH_TEST_AUTOMATION_VISION.md`.

## 1. Зачем нужны блоки

Ручной запуск каждого сценария создаёт риск:
- забыть один из сценариев;
- выполнить меньше или больше трёх повторов;
- дважды записать один и тот же repeat cell;
- забыть сохранить execution report или Game Monitor capture;
- продолжить серию после неполного/невалидного эксперимента;
- потерять сведения о том, на каком запуске остановилась серия.

Оператор должен запускать блок целиком, а не собирать его из отдельных запусков.

## 2. Состав блоков

| Блок | Сценарии | Повторов на сценарий | Всего запусков |
|---|---|---:|---:|
| G1 | horizontal_lengths, vertical_lengths, diagonal_lengths, short_strokes | 3 | 12 |
| G2 | long_isolated_lines, continuous_turns, continuous_closed_contour, repeated_coverage, parallel_spacing, cross_section_intersections | 3 | 18 |
| G3 | 9 комбинаций point_step_px × point_delay_ms | 3 | 27 |

G1/G2 используют radius=10 и фиксированный `GEOMETRY_EXECUTOR_CONFIG`. G3 открывается только после принятия G1 и G2.

## 3. Поведение полноценного блока в UI

Оператор один раз выбирает:
- фазу G1/G2;
- уникальный ID серии;
- подтверждённый профиль калибровки и активный Game Monitor Bridge;
- наличие эталона пустой доски;
- подтверждение, что текущая игровая доска тестовая и может автоматически очищаться между опытами.

Далее AutoDraw должен самостоятельно:
1. Создать неизменяемый план всех ячеек `scenario × repeat`, с фиксированным seed и перемешанным порядком.
2. Сохранить журнал блока до первого действия мышью.
3. Показать общее число опытов, число завершённых, текущий опыт и оставшиеся.
4. Для каждой ячейки создать уникальные `experiment_id` и план; записать `repeat_index` и уникальный `matrix_order_index`.
5. Проверить/очистить доску по эталону; если чистота не подтверждена — остановить блок до рисования.
6. Снять baseline состояния ресурса, установить радиус через drag и подтвердить его Game Monitor heartbeat.
7. Передать план исполнителю и дождаться завершения.
8. Дождаться однозначной привязки Game Monitor run; сохранить `monitor_report.json`, summary и event diagnostics.
9. Принять опыт только при выполнении всех обязательных критериев качества.
10. Сохранить результат в журнал блока и перейти к следующей ячейке только после успешного gate и подтверждённой очистки доски.

Нельзя автоматически считать успешным только статус executor. Рисунок должен быть принят игрой, а точный CHALK counter и события Monitor должны согласоваться.

## 4. Критерии принятия одного опыта

Обязательные условия:
- executor завершился со статусом `completed`;
- запрошенный и фактический радиус равны 10;
- Game Monitor однозначно связан с текущим executor window и имеет уникальный `run_id`;
- `chalk.status=exact`, `post_point_count - pre_point_count = consumed_points > 0`;
- `sampled_point_delta_total` совпадает с точным CHALK;
- число уникальных strokeId равно expected stroke count;
- per-stroke сумма `DRAW_SAMPLE.pointDelta` совпадает с exact CHALK;
- frame probe измерен, нет visibility interruption;
- dropped events, monitor dropped events и monitor errors равны нулю;
- после опыта доска очищена и подтверждена эталоном перед следующим запуском.

Любое несоответствие переводит блок в `paused`; следующие тесты не запускаются автоматически. Нельзя молча пропускать опыт и двигаться дальше.

## 5. Журнал блока и восстановление

Каждая задача журнала содержит:
- task_id, scenario_id, repeat_index, matrix_order_index;
- expected_strokes, radius, executor parameters;
- статус pending/running/completed/failed/interrupted;
- список попыток с experiment_id, experiment_dir, timestamps и причиной отказа;
- experiment_id и experiment_dir записываются в активную попытку журнала до первого действия мышью, чтобы interrupted run можно было найти после рестарта.

Журнал записывается до запуска и обновляется после каждой попытки. При перезапуске приложения незавершённая задача становится `interrupted`; её нельзя автоматически повторить, потому что игра могла успеть частично нарисовать рисунок. Оператор должен проверить доску и отдельно решить вопрос о повторном запуске. Неудачный/неполный опыт сохраняется как первичное доказательство, но не засчитывается в три валидных повтора.

## 6. Реализация

Добавлен модуль `source/preparation/chalk_test_blocks.py`:
- формирует полный детерминированно перемешанный список задач G1 (12) или G2 (18);
- гарантирует три repeat cell для каждого сценария;
- назначает уникальный matrix_order_index;
- создаёт отдельный долговечный JSON-журнал, не перезаписывая существующий;
- выдаёт следующую задачу только при отсутствии активной;
- закрывает задачу как completed/failed;
- переводит незавершённую задачу в interrupted и не воспроизводит её автоматически;
- при failed/interrupted ставит блок на паузу.

Добавлены тесты `source/preparation/tests/test_chalk_test_blocks.py` на количество задач, полный набор repeat cells, детерминированный порядок, проверку конфигурации, запись журнала, последовательное выполнение, остановку при ошибке и восстановление после прерывания.

**Текущий статус:** UI runner G1/G2 реализован в Brush Test. Добавлены выбор фазы, Start/Stop, progress, долговечный журнал до первого mouse action, автоматическая смена сценариев/повторов и связка с существующим lifecycle. G2 заблокирована до завершения G1.

Перед переходом к следующей задаче runner требует принятия manifest матричным validator, точного CHALK, полного per-stroke breakdown из `monitor_report.json`, чистого frame probe, непустой accepted trajectory и подтверждённого возврата кисти. Любой отказ/timeout приостанавливает блок. Остановка пользователя применяется только на границе текущего опыта.

**Recovery:** при запуске UI обнаруживает журнал в состоянии running и переводит текущую задачу в interrupted без replay. Оператор видит experiment ID/каталог и должен вручную проверить игровую доску. Только после явного подтверждения можно создать новую попытку interrupted-задачи; предыдущая попытка остаётся в журнале. Ready-журнал после закрытия приложения также можно продолжить только после подтверждения тестовой доски. Failed/paused блок можно закрыть без продолжения; первичные попытки сохраняются.

**Проверки:** добавлены unit tests ядра и 10 callback workflow tests (acceptance-before-advance, incomplete evidence, capture timeout, executor failure, brush restore, safe stop recovery, G2 lock, Alt cancellation during preclear/postdraw). Дополнительно acceptance gate проверяет соответствие manifest активной задаче блока: block/task/experiment IDs, точный каталог experiment, series, phase, scenario, repeat, radius, expected stroke count, matrix order и executor config. Добавлены parameterized tests для несовпадений identity и тест положительного совпадения. Покрытие остаётся промежуточным, не исчерпывающей матрицей всех Tk callback/failure paths.

**CI status (2026-11-01):** GitHub Actions run `41266047330` для `609aca9156e5eb136c7db5cb516262b971d4fa82` и run `41266141717` для `f8f2d1c6fe47b8d5e539be78951cea16296e16f6` завершились `success`. В последнем run успешны `geometry-tests`, `executor-tests`, `Windows portable build and startup smoke-test`. После этих CI проверок добавлена дополнительная проверка идентичности активной block task в capture acceptance; её новый код и тесты ещё должны пройти отдельный CI. Live G1 не запускался.

## 7. Текущие ограничения и порядок работ

1. Прогнать GitHub Actions и Windows portable smoke test после добавления task-identity acceptance gate.
2. Продолжить callback-level review для отказов preclear, brush feedback, executor, capture correlation, restore, Stop, journal I/O и restart/recovery.
3. После успешного CI и подтверждения готовности оператора выполнить один контролируемый live-блок G1 на тестовой доске.
4. После принятия полного G1 разрешить G2.

Существующие 12 G1 manifests с `repeat_index=1` не мигрировать и не переписывать автоматически. Для них нужен отдельный reconciliation sidecar с привязкой исходных experiment_id к повторениям либо повторная серия штатным block runner.


## Дополнение 2026-11-01 — привязка capture acceptance к текущей задаче

В ходе заключительного review обнаружен пробел: строгий валидатор проверял внутреннюю целостность experiment manifest, но UI не передавал ему ожидаемую идентичность активной задачи block journal. Исправлено fail-closed поведение: перед принятием capture сравниваются block_id, task_id, experiment_id, series_id, phase_id, scenario_id, repeat_index, requested_radius, expected_strokes, matrix_order_index и executor_parameters. Если journal недоступен или любое поле не совпадает, задача не принимается и блок приостанавливается.

Добавлены тесты на шесть вариантов несовпадения идентичности и на положительный сценарий. Дополнен callback test: UI обязан передать активную задачу, журнал блока и текущий experiment_id в validator. Новые изменения: d5d3542840138f80df51cc467ca4b91012c18689, 589f25d116f1fadb924aa2d773da22515e17b001, 9576a97c4cc84fe8b139743dcf20b46eec5fece3, b63b7170f758c26016d46092ea5dc90fea1337fb. Результат CI для этих новых изменений ожидается; live G1 не запускался.


Дополнительно identity gate использует не только UI runtime values: ожидаемые experiment_id и experiment_dir читаются из активной попытки, сохранённой в block journal. Проверяется, что путь manifest принадлежит именно каталогу этой зарегистрированной попытки. Добавлен callback test для отказа preclear: при несовпадении blank-board эталона блок становится paused/failed, executor не запускается. CI для этих последних изменений ещё ожидается.


## Дополнение 2026-11-01 — CI diagnosis и коррекция тестовой подмены

Runs `41267183785` и `41267241966` завершились одинаково: `executor-tests` — success; `geometry-tests` — 1 failed / 574 passed; Windows portable build завершился до startup smoke-test из-за той же ошибки preparation suite. Единственное падение находилось в callback test `test_ui_capture_gate_pauses_without_advancing_on_incomplete_evidence`: mock validator lambda не принимала новые именованные identity-параметры UI.

Mock обновлён до `lambda _path, **_kwargs` в commit `20704ab984b981a4bf5b2278eba6cfad970d15a5`. Логика production validator/UI не менялась. Повторный CI для исправления ожидается; block runner пока не считать готовым к live G1.


## Дополнение 2026-11-01 — structural integrity gate журнала

Загрузчик block journal дополнен централизованной структурной проверкой до любого recovery/state transition. Проверяются schema version, phase/block status, соответствие `expected_task_count` фактическому числу задач, уникальные `task_id` и `attempt_id`, допустимые статусы, корректная ссылка `active_attempt_id` на единственную running attempt, максимум одна running task и согласованность running/completed статуса блока. Некорректный JSON возвращается как ValueError. UI recovery рассматривает такой файл как unresolved и не пытается его исправлять или перезапускать.

Добавлены tests на повреждённые task records, пустые/дублированные ID, неизвестные статусы, несоответствие количества задач, orphaned running attempt, несколько running attempts, несогласованный block status, некорректный JSON и валидный running state.

Изменения: `2ea67817bd1187baa66252aec440a4a5238042e0`, `52b40e94eadf1e75f461565960547b2a749993e4`. CI для этих commits ожидается. Файловый journal пока предполагает один активный экземпляр UI; межпроцессная блокировка не реализована.


Journal validator также проверяет типы полей phase/status до membership checks. Некорректные JSON значения list/dict в этих полях возвращают ValueError, а не TypeError из-за unhashable values. Для этого добавлены отдельные negative cases; CI для финального изменения ожидается.


CI run `41269156105` обнаружил SyntaxError в source validator из-за буквального `\\n` в строке type check. Исправлено commit `dd5aaade3b790546d9e3fc11341554f6aa09d8ec`. Полный CI на исправленном commit — обязательный gate перед live G1.

# Автоматизированные блоки экспериментов CHALK

**Статус:** block runner интегрирован и прошёл live G1 (12/12). После live-прогона исправлены подсчёт принятых штрихов и отсутствие итогового уведомления; полный CI прошёл на HEAD c8d8c2c5588a0d423e48682962a4213ee725c808.  
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

G1/G2 используют radius=10 и фиксированный `GEOMETRY_EXECUTOR_CONFIG`. G3 открывается только после принятия G1 и G2. INT-006 V1–V5 используют тот же lifecycle, radius=10 и отдельную матрицу P0=2/10, P1=4/5, P2=4/10; каждая фаза содержит 9 задач (3 профиля × 3 повтора).

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
- число уникальных strokeId с положительным суммарным DRAW_SAMPLE.pointDelta равно expected stroke count; нулевые pointer-кандидаты учитываются отдельно и не увеличивают число принятых штрихов;
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


## Защита журнала от противоречивых состояний и конкурентной записи

Актуализация 2026-11-01:

- Валидатор дополнительно сверяет статус блока с набором статусов задач: ready допускает только pending/completed; paused требует failed/interrupted и не допускает running; failed требует failed-задачу; completed требует все задачи completed; stopped не допускает running.
- Статус failed теперь считается unresolved при проверке существующих журналов и блокирует запуск нового блока.
- Все операции read-modify-write журнала и создание нового журнала сериализованы межпроцессным advisory lock: msvcrt.locking на Windows, fcntl.flock на POSIX. Рядом с журналом остаётся небольшой .lock файл; удалять его не нужно.
- Ошибки записи временного файла и os.replace проверяются тестами. При ошибке замены исходный JSON остаётся прежним и валидным; операция завершается исключением, UI не должен продолжать задачу.

Ограничение: lock сериализует отдельные транзакции журнала, но не является долгоживущей блокировкой всего GUI-сеанса. Эксплуатационное правило — не открывать один и тот же активный block journal в двух экземплярах AutoDraw. До live G1 дополнительно проверить запуск/восстановление на Windows CI и фактической рабочей машине.


## Эксклюзивное владение активным блоком

Дополнение 2026-11-01:

Помимо короткой транзакционной блокировки journal теперь имеет отдельный lifetime owner lock (.owner.lock). AutoDraw удерживает его от создания блока до завершения/остановки или передачи в recovery. При запуске второго экземпляра:
- если owner lock занят, runner не меняет running → interrupted и не предлагает восстановление активного блока;
- если процесс-владелец завершился, ОС освобождает lock; следующий экземпляр может получить lock и только тогда пометить running задачу как interrupted;
- операции resume/close повторно получают owner lock, если предыдущий runtime уже освободил его;
- закрытие failed/paused журнала требует явной проверки доски.

Owner lock — файловая блокировка ОС, а не маркерный файл; сам .owner.lock остаётся на диске и не удаляется. Фактическое владение определяется удерживаемым дескриптором/lock, а не наличием файла.


### Единый lock для всего каталога блоков

Уточнение реализации 2026-11-01: owner lock общий для каталога block journals, а не отдельный на каждый JSON. Файл: .active-block.owner.lock внутри каталога chalk_test_blocks. Поэтому два экземпляра не могут параллельно стартовать разные серии/журналы в одном output_dir. Текущий UI удерживает lock для одного recovery-журнала; дополнительные незавершённые журналы остаются unresolved и разбираются последовательно.


Дополнительная fail-closed обработка owner-lock I/O: невозможность создать/открыть owner lock возвращает отказ в получении владения; release закрывает дескриптор даже при ошибке OS unlock, полагаясь на закрытие дескриптора для освобождения блокировки. Не интерпретировать отказ получения lock как разрешение запуска.


Дополнительный тест эксклюзивности запускает отдельный процесс (multiprocessing spawn), который пытается получить общий owner lock при удержании его основным процессом. Это проверяет реальную межпроцессную блокировку, а не только конкуренцию файловых дескрипторов в одном процессе.


Закрытие failed-блока также записывает отдельное audit-решение close_failed_block с board_checked=true и временем решения; это не должно теряться по сравнению с закрытием paused-блока.

### CI finding — closure audit classification (2026-11-01)
The first final CI run exposed a mismatch: `finish_chalk_block_task(accepted=False)` correctly leaves the block in `paused`, while the rejected task itself is `failed`. Closure audit classification now inspects task statuses, recording `close_failed_block` when a failed task exists and `close_paused_block` for interruption-only pauses. This preserves the distinction between block state and failed experiment state. The existing regression test asserts the failed-task path. Full CI must be rerun; G1 remains blocked until all jobs and Windows portable smoke-test pass.

### Финальная проверка CI — 2026-11-01

Последний CI run [41272291546](https://github.com/Kiddos19882/AutoDraw/actions/runs/41272291546) для HEAD `311299296559b9a5949f1e803f134b46436a2850` завершился `success`: `geometry-tests`, `executor-tests` и `Windows portable build and startup smoke-test` прошли. Windows job выполнил portable build и `smoke_test_portable.py` после общего набора тестов.

Исправлена найденная CI ошибка классификации closure audit: paused block с failed task теперь закрывается с `close_failed_block`, а interrupted-only paused block — с `close_paused_block`. Кодовый commit `dd976b04f6d6423726ad7382bac7223c12d8342b`.

Пункт 1 плана работ выше выполнен. Live G1 завершён отдельным блоком 12/12: chalk-20261101-080012-4d6add. Первый блок был остановлен из-за ложного подсчёта нулевого pointer-кандидата; причина исправлена. Завершение блока теперь сопровождается отдельным окном 12/12. Исправления и regression tests прошли полный CI run 41276703424 на HEAD c8d8c2c5588a0d423e48682962a4213ee725c808.

G1 принят. G2 разблокирован и является следующим live-блоком (18 задач); G3 остаётся закрытым до принятия G2. Перед G2 обновить локальную сборку до указанного HEAD. Callback-level failure-path review имеет тестовое покрытие, но не заявляется исчерпывающим.

## 7. Подтверждённый live G1 и post-run fixes — 2026-11-01

- Блок chalk-20261101-080012-4d6add завершён: 12/12 задач приняты.
- Первый блок остановлен после false mismatch: Game Monitor видел 5 pointer candidates, но один не имел положительного pointDelta; четыре реальные расходующие штриха дали точный CHALK 60.
- stroke_count теперь считает только stroke IDs с положительным суммарным DRAW_SAMPLE.pointDelta; диагностические поля candidate count сохраняют информацию о нулевых pointer-жестах.
- При journal.status=completed UI выводит отдельное итоговое окно с количеством принятых опытов.
- Исправления покрыты regression tests и прошли полный CI run 41276703424.

G2 разблокирован; G3 остаётся закрытым до завершения G2. Перед следующим live-блоком обновить локальную сборку до HEAD c8d8c2c5588a0d423e48682962a4213ee725c808.

## 8. Поддержка G3

G3 использует тот же безопасный последовательный lifecycle, что и G1/G2, но вместо набора геометрических сценариев создаёт 27 parameter cells для `paint_consumption_long_lines`:

- `point_step_px`: 1, 2, 4;
- `point_delay_ms`: 5, 10, 20;
- `repeat_index`: 1, 2, 3;
- радиус кисти: 10;
- ожидаемые штрихи: 6.

`task_id` содержит обе настройки executor и номер повтора. Journal validation отклоняет дубликаты и неполные матрицы. G3 доступен в UI только после принятия G2.

Executor parameters из задачи сохраняются в matrix metadata и передаются как временный override в Stage6. Override валидируется `ExecutorConfig`, отражается в execution report и не изменяет пользовательские сохранённые настройки. Acceptance analyzer сравнивает report с matrix metadata; поэтому manifest не может выдать запрошенные параметры за фактически использованные.

Live G3 остаётся закрытым до прохождения regression tests, полного CI и Windows portable startup smoke-test.


## 2026-11-01 — удалено визуальное подтверждение размера кисти после Game Monitor

По замечанию оператора устранены два последовательных диалога, которые требовали визуально подтвердить радиус после автоматической установки:
- `integrated_app.py::_start_brush_test_executor` больше не спрашивает пользователя, совпадает ли размер кисти с запрошенным;
- `BrushBehaviorTestTab._confirm_brush_before_test` больше не показывает `askyesno` после точного подтверждения Game Monitor.

Проверка не ослаблена: executor допускается к запуску только после свежего heartbeat Game Monitor с точным совпадением фактического радиуса и запроса. В handoff добавлена повторная fail-closed проверка `observation.radius == requested_brush`; при расхождении запуск блокируется. Источник проверки и факт автоматического подтверждения сохраняются в `experiment.json`, поле `visual_confirmation_required=false`. Потеря Monitor, отсутствие свежего heartbeat, несовпадение радиуса, ошибка коррекции или записи manifest по-прежнему останавливают тест.

Для G1/G2/G3 block runner это убирает лишний popup после каждого автоматического drag; Clear/blank-board и остальные обязательные предупреждения не затрагивались. Добавлены regression tests: точный Monitor radius запускает callback без диалога, mismatch блокирует handoff.

Изменения в commits: `bb32589cb9d450a03b1d5b5264732828812b8ed3`, `465346a58caf76b8566d99128361095324368366`, `c919610999c5ea9f4a1afebad937395e586dc4b9`. Требуется новый полный CI на изменённом HEAD; до его завершения успешный CI предыдущего G3 HEAD не распространяется на эти изменения.


### Уточнение lifecycle: автоматическое подтверждение радиуса Game Monitor

В актуальной реализации G1/G2/G3 ручное визуальное подтверждение радиуса после drag не требуется. Game Monitor является источником фактического значения: UI ждёт свежие heartbeat после отпускания ползунка, автоматически корректирует положение при mismatch и перед handoff повторно проверяет `observed radius == requested radius`. Только точное совпадение разрешает запуск executor. Повторные диалоги визуальной проверки удалены как дублирующие эту программную проверку. Отсутствие/устаревание heartbeat, mismatch, ошибка коррекции или записи manifest сохраняют fail-closed поведение. Предупреждение о том, что блок может очистить текущую тестовую доску, остаётся и не относится к подтверждению кисти.


## CI и программный gate G3 — подтверждение актуального HEAD (2026-11-01)

Последний подтверждённый workflow run: [41340237207](https://github.com/Kiddos19882/AutoDraw/actions/runs/41340237207). Проверенный commit: `3dbf8f20bcea44c61290e49398e1a4daf182dbf9` в ветке `feature/image-geometry-optimization`.

Все jobs завершились success:
- `geometry-tests`;
- `executor-tests`;
- `Windows portable build and startup smoke-test`.

В `geometry-tests` включены тесты Game Monitor, локального WebSocket smoke server, preparation/geometry, G3 matrix/block workflow, Stage 7 validator, import diagnostics и unified-app UI regressions. Последний run включает regression test удаления popup в основном приложении из commit `8c93a498864973b9879c926627030bb7e1d3ce2a`.

**Вывод для lifecycle блока:** G3 программно готов к локальному preflight. Автоматическое подтверждение кисти выполняется по свежему heartbeat Game Monitor и точному совпадению радиуса; отдельное визуальное подтверждение после drag не требуется. При mismatch или недостоверном heartbeat запуск блокируется. Предупреждение о возможной очистке доски сохраняется.

**Границы CI:** workflow подтверждает тесты и сборку/старт portable-приложения на runner GitHub. Он не подключается к пользовательской игровой сессии, не выполняет 27 live опытов и не измеряет CHALK. Поэтому software gate закрыт, но local Windows preflight и live G3 остаются обязательными.

## 2026-11-01 — G3 scenario routing regression

При первом live-старте G3 две попытки первой задачи `paint_consumption_long_lines-s2-d20-r3` были выполнены фактически с настройками 2/10 и отклонены acceptance gate из-за отсутствующей block/matrix identity. Причина: один scenario ID использовался и legacy radius matrix, и geometry matrix; первая ветка UI перехватывала G3 task. Исправлено условие выбора legacy-ветки: она применима только при отсутствии активной block task. Для G3 block task теперь выполняется geometry-matrix path, который создаёт `chalk_experiment_matrix` и `chalk_test_block`; Stage6 получает параметры задачи через существующий временный executor override.

Добавлен regression test на пересечение `MATRIX_SCENARIO_ID` и `GEOMETRY_MATRIX_SCENARIOS`. Два исходных запуска оставлены в журналах как failed attempts, не засчитываются и не перезапускаются. Новая серия должна быть создана только после полного CI и локального Windows preflight.

## 2026-11-02 — фактический результат первой live G3 серии

Первая полноценная попытка live G3 после исправления scenario routing сохранена в commit `094381f1d3f005efc8b2324062cc1f2dacc277a5`. Block journal содержит 27 задач: 21 completed, 1 failed, 5 pending. Причина остановки — `monitor_capture_gate_timeout:partial`. Задача `s4-d10-r2` завершила executor (6/6), получила точный CHALK delta 363 и matching pointDelta, но Monitor report был partial из-за 434 `monitor_dropped_events`; она не проходит acceptance gate. Блок имеет `stopped` и recovery decision `close_failed_block`, поэтому не считать его paused для обычного resume.

Проверка 22 manifests: task metadata совпадает с фактическим executor config; radius=10; шесть штрихов; внутренний CHALK counter exact. 21 Monitor capture saved, один partial. Траектория во всех случаях помечена `incomplete_until_verified` из-за coalesced pointDelta.

Таблица CHALK по всем девяти конфигурациям, пять полностью собранных ячеек, четыре неполных ячейки и ограничения вывода находятся в `CHALK_G3_PARTIAL_RESULTS_2026-11-02.md`. До завершения повторов и проверки continuation semantics модель расхода остаётся предварительной.undefined

## 2026-11-02 — INT-006 independent validation software gate

D1–D5 подключены к отдельной фазе INT006. Block journal формирует 45 уникальных задач (5 DrawingPlan × 3 sampling profiles × 3 repeats) и содержит frozen prediction artifact из 15 records до первого live capture. Prediction ID связан с task, manifest и executor handoff. Независимый analyzer проверяет exact CHALK, Monitor integrity, geometry/profile/task/journal identity и считает run/per-stroke errors.

Full CI [41513389663](https://github.com/Kiddos19882/AutoDraw/actions/runs/41513389663) завершился success: Preparation/G3 667 passed, 82 subtests; остальные обязательные jobs, pixel audit и Windows portable build/startup smoke-test — success. Artifact `autodraw-g3-preflight-build` ID `13173632860`.

Следующий шаг — локальный Windows 10 preflight. До его проверки не запускать 45 live captures. См. [INT-006 frozen analyzer](CHALK_INT006_FROZEN_PREDICTIONS_AND_ANALYZER_2026-11-02.md) и [preflight guide](CHALK_INT006_LOCAL_PREFLIGHT_GUIDE_2026-11-02.md).

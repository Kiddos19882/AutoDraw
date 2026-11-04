# FILL-001 — разбор пользовательского Windows live preflight

**Дата отчёта:** 2026-11-04  
**Ветка:** `feature/image-geometry-optimization`  
**Проверенный code HEAD:** `fe6d4469a5294fdf8284978d4e2b5c47582fa2d4`  
**Пользовательская серия:** `fill001-20261104-001636`  
**Задача:** `fill001-20261104-001636-rectangle-r10-rep1`  
**Итог эксперимента:** EXECUTION COMPLETED / CAPTURE REJECTED / ANALYSIS PARTIAL

## 1. Краткий вывод

Пользовательский запуск действительно выполнил рисование: Stage 6 завершил 131 из 131 запланированных штрихов без ошибки executor. After PNG существует и визуально показывает заполненную прямоугольную область. Game Monitor зафиксировал точный session-level расход CHALK: `pointCount 1 → 6000`, то есть **5999 единиц**.

Но эта попытка **не является принятым FILL-001 capture**. Attempt JSON остался невалидным, runtime binding завершился ошибкой hash validation, а большой Bridge run-файл второго запуска (27 934 553 bytes) не удалось извлечь целиком через доступный GitHub file API. Поэтому нельзя подтвердить точную per-run/per-stroke атрибуцию всех 5999 CHALK и нельзя рассчитать coverage/leakage по frozen mask.

После анализа кода обнаружена ещё одна независимая проблема runtime binder: он использует время финализации Bridge run вместо времени последнего события. В конкретном запуске это превращает завершившийся до executor старта калибровочный run в ложный overlapping candidate. Это подтверждённая статическая проблема логики на реальных timestamp, но исправление в этом отчёте не выполнялось.

## 2. Идентификация и условия

| Поле | Значение |
|---|---|
| Среда | Windows 10, build 19045 |
| Python | 3.11.9 |
| Браузер | Firefox 159 |
| Game Monitor | 0.2.1 |
| Логическая доска | 460×240 |
| Calibrated screen ROI | x=566, y=253, width=581, height=304 |
| Форма | rectangle |
| Запрошенный радиус | 10 |
| План штрихов | 131 |
| Sampling profile | P1: step=4, delay=5 ms |
| Executor line extension | 0 px |
| Target mask area | 44 653 px |
| Planned coverage/leakage | 100% / 0 px (плановые метрики, не результат PNG audit) |

План, manifest, before/after PNG, attempt JSON, executor report и Bridge session/run находятся в commit пользователя [d0acb0f](https://github.com/Kiddos19882/AutoDraw/commit/d0acb0f4ae411d5682a9168525a3db4848564ee6).

## 3. Исполнение Stage 6

Executor report `execution_20261104_003004_692741_8aaae2.json` содержит:

- `status=completed`;
- `completed_strokes=131`, `total_strokes=131`;
- длительность 225.61 секунды;
- 12 857 move calls;
- `point_step_px=4`, `point_delay_ms=5`, `line_extension_px=0`;
- `error=null`, `stop_reason=null`;
- mouse release выполнен успешно.

Это подтверждает завершение executor, но не принятие capture и не качество конечного изображения.

## 4. Game Monitor и точный расход CHALK

Bridge session `edb681fe-a3b6-415b-87da-9ce228c41253`:

- начальный exact snapshot: `pointCount=1`, `maxPoints=6000`, `remainingPoints=5999`;
- конечный exact snapshot: `pointCount=6000`, `remainingPoints=0`;
- session delta: `6000 - 1 = 5999`;
- `droppedEvents=0`, Monitor errors=0, collector sequence gaps=0;
- Bridge send failures=0.

Session event totals:

| Тип события | Всего в session |
|---|---:|
| POINTER_DOWN_CANDIDATE | 133 |
| POINTER_UP_CANDIDATE | 133 |
| DRAW_SAMPLE | 6 132 |
| BRUSH_CHANGE | 69 |
| BRUSH_CHANGE_APPLIED | 69 |
| POINT_QUOTA_UPDATE | 5 999 |

### 4.1 Первый Bridge run — калибровка, не FILL-001 task

Файл `game-monitor-run-20261103T212620863204Z-9572d6ba.json` доступен и разобран:

- 144 события: 2 pointer down/up, 2 DRAW_SAMPLE, 69 BRUSH_CHANGE и 69 BRUSH_CHANGE_APPLIED;
- `stroke_count=0`, `stroke_candidate_count=2`, `non_consuming_stroke_candidate_count=2`;
- exact CHALK: `pointCount 1 → 1`, расход 0;
- радиус менялся в ходе калибровки; наблюдавшиеся значения 8–30, финальный радиус 10;
- run завершён штатно, потерь событий не зафиксировано.

Этот run объясняет 2 из 133 session-level pointer candidates и все 69 изменений кисти. Его нулевой расход подтверждён отдельным run record.

### 4.2 Второй Bridge run — файл есть, содержимое не проверено

Файл `game-monitor-run-20261103T213007154888Z-8c8bfbab.json` присутствует в Git tree, размер **27 934 553 bytes**, SHA-1 Git blob `069b691ed4cf28813116be29a7eab2243371bbe3`. GitHub file API вернул пустое содержимое при чтении этого большого файла; это не означает, что сам файл пустой.

Если вычесть события первого run из session totals, на второй run приходится 131 pointer down/up candidates, 6 130 DRAW_SAMPLE и 5 999 POINT_QUOTA_UPDATE. Это совпадает с ожидаемым числом штрихов задачи и общим session CHALK delta. Поскольку содержимое второго run не прочитано, это **сильное согласование session totals с задачей, но не независимое подтверждение run-level/per-stroke exact CHALK**.

Необходимо сохранить это различие: 5999 — точная session delta; task-level attribution вероятна, но capture acceptance требует проверяемого второго run и его per-stroke breakdown.

## 5. Attempt JSON и PNG

Attempt-файл `fill001-20261104-001636-rectangle-r10-rep1.json` имеет размер 1 922 bytes. В конце после закрывающей JSON-скобки записаны буквальные символы `\\n`, поэтому JSON parser сообщает `Extra data: line 46 column 2 (char 1920)`.

В attempt record:
- `executor_status=completed`;
- `status=execution_completed_pending_runtime_and_png_audit`;
- `after_png=null`;
- `capture_path=null`.

При этом after PNG физически существует: `...-after.png`, 4 735 bytes; before PNG — 2 215 bytes. Оба изображения имеют размер 581×304. Визуальный просмотр показывает пустую доску до запуска и заполненную чёрную прямоугольную область после запуска. Это только качественное наблюдение: количественный pixel audit против frozen mask не выполнен. Coverage ≥99%, leakage=0 и отсутствие мелких дефектов не подтверждены.

Причина сообщения «Не удалось сохранить after PNG» — последующая запись/чтение attempt JSON, а не отсутствие самого PNG. Attempt JSON не был обновлён ссылкой на after PNG.

## 6. Исправления программной части и CI

В рабочей ветке опубликованы:

- [2b7577c](https://github.com/Kiddos19882/AutoDraw/commit/2b7577c3a3289871b7fff300fd6013f12c7cb54e): исправлены четыре JSON writer в `chalk_fill_ui.py`; canonical DrawingPlan hash проходит через `DrawingPlan.from_dict(...).to_dict()`; добавлены regression tests.
- [3b67aea](https://github.com/Kiddos19882/AutoDraw/commit/3b67aea0145170ec23df089916bedf7828de9a68): runtime handoff сохраняет нормализованный документ, по которому рассчитан hash.
- [fe6d446](https://github.com/Kiddos19882/AutoDraw/commit/fe6d4469a5294fdf8284978d4e2b5c47582fa2d4): добавлен regression test на отказ при non-consuming stroke candidates и дополнительные UI persistence tests.

Полный GitHub Actions run [41730717881](https://github.com/Kiddos19882/AutoDraw/actions/runs/41730717881) завершился **SUCCESS** на code HEAD `fe6d446`:

| Job | Результат |
|---|---|
| Executor regression tests | SUCCESS |
| Game Monitor / Bridge tests | SUCCESS |
| Application integration tests | SUCCESS |
| Preparation / G3 matrix tests | SUCCESS — 782 passed, 24 warnings, 82 subtests passed |
| INT-006 pixel-level PNG audit | SUCCESS |
| Windows portable build and startup smoke-test | SUCCESS |
| Optional algorithm benchmarks | SKIPPED |

Windows artifact: [autodraw-g3-preflight-build](https://github.com/Kiddos19882/AutoDraw/actions/runs/41730717881/artifacts/13278132576), 637 057 007 bytes. Это software/build gate, не повторный live FILL-001 run.

## 7. Дополнительная проблема runtime binding — ложное пересечение временных окон

В `chalk_fill_runtime_binding.py::bind_fill001_runtime_evidence()` каждый Bridge run считается кандидатом, если интервал `started_at_utc → finished_at_utc` пересекается с executor interval. Если такой run начался до executor, binder сразу отклоняет его.

Для первого калибровочного run фактические времена:

- Bridge run started_at_utc: **21:26:13.631Z**;
- started_at_performance_ms: 307482;
- последняя event timestamp: 311267;
- последнее событие в пересчёте через общий performance clock: **21:26:17.416Z**;
- executor summary started_at: **21:26:19Z**;
- Bridge finished_at_utc: **21:26:20.862Z**.

Последнее событие калибровочного run произошло примерно за 1.584 секунды до начала executor. Run был финализирован позже из-за idle timeout 2.5 секунды. Следовательно, **фактические события калибровки не пересекаются с executor**, но интервал финализации пересекается.

Текущая логика binder использует `finished_at_utc`, видит overlap и отклоняет этот run как начавшийся до executor window. Это воспроизводимый статический дефект на committed timestamps. Он не был причиной исходного сообщения пользователя (исходный report остановился раньше на hash mismatch), но станет следующим препятствием после исправления hash mismatch, если не изменить критерий временной привязки.

Правильная проверка должна отделять:
1. интервал активности событий Bridge run;
2. время ожидания idle finalization и записи файла.

Для определения активности можно использовать согласованные `started_at_utc`, `started_at_performance_ms` и максимальный event `t` (с проверкой типов/монотонности); `finished_at_utc` оставить для проверки допустимого finalization grace. Не следует ослаблять отдельную проверку `non_consuming_stroke_candidate_count=0` для выбранного task run: два нулевых кандидата принадлежат отдельному калибровочному run, который должен быть исключён по времени активности.

## 8. Что подтверждено и что нет

**Подтверждено:**
- Stage 6 выполнил 131/131 штрихов без executor error.
- Session-level exact CHALK delta равна 5999 и исчерпала квоту 6000.
- Первый Bridge run — отдельная калибровка с CHALK=0 и двумя non-consuming candidates.
- Второй Bridge run file физически присутствует и имеет размер 27.9 MB.
- Before/after PNG физически существуют; визуально after показывает заполненную область.
- Исправления JSON persistence и DrawingPlan hash вошли в code HEAD; полный CI и Windows portable startup smoke-test прошли.
- Binder имеет временную false-overlap логику на данных этой попытки.

**Не подтверждено:**
- точная per-run и per-stroke атрибуция 5999 CHALK;
- fixed radius=10 для всех событий второго run (session final snapshot=10, но run-файл не разобран);
- успешное прохождение полного runtime binding после исправления hash;
- количественные coverage/leakage и визуальные quality gates;
- принятие capture и завершение хотя бы одной ячейки FILL-001.

## 9. Блокировки и следующий порядок действий

1. Исправить runtime binder: использовать event activity window вместо `finished_at_utc` для выбора Bridge run; добавить regression test на калибровочный run, который завершил события до executor start, но записал файл после начала executor из-за idle timeout.
2. Сохранить fail-closed проверку выбранного run: task identity, exact snapshots, per-stroke CHALK, radius, P1, no non-consuming candidates, sequence gaps, drops, errors и send failures.
3. Повторно выполнить полный CI и Windows portable build на исправленном code HEAD.
4. Проверить второй Bridge run целиком локальным анализатором/на Windows и сохранить его summary/per-stroke result отдельно, не изменяя исходный JSON.
5. Восстановить или использовать новую игровую доску с полной квотой. Текущая доска исчерпана (`pointCount=6000/6000`).
6. После исправления binder провести один новый FILL-001 live preflight и проверить before/after PNG по frozen mask и calibrated ROI.
7. Только после принятия preflight разрешать 45-cell matrix. Не менять production estimator, production defaults или sampling defaults по этой попытке.

## 10. Git и границы

- Проверенная ветка: `feature/image-geometry-optimization`.
- Code HEAD, на котором прошёл полный CI: `fe6d4469a5294fdf8284978d4e2b5c47582fa2d4`.
- Сравнение с master: feature ahead 2688 / behind 5, merge base `d4a07702e45c01648f343bc6440a3287c45d3f9c`; merge/rebase не выполнялись.
- `master` не изменялся.
- Через GitHub API нельзя подтвердить локальный `git status`.
- В рамках этого отчёта исходники, тесты, конфигурации и первичные runtime evidence не изменялись. Добавлен только анализ/документация.

## 11. Follow-up 2026-11-04 — incomplete Bridge session и повторная привязка

Пользовательский commit [b4a107a](https://github.com/Kiddos19882/AutoDraw/commit/b4a107abfd33d3e4c0ded723154444c84c97b2ad) добавил артефакты нового запуска: executor report завершён на 131/131 strokes, after PNG сохранён, но кнопка capture acceptance получила ошибку «Bridge session не содержит bridge_diagnostics». При последующей проверке Bridge session уже содержала bridge_diagnostics; session-level pointCount delta осталась 1 → 6000 (CHALK=5999).

Статический разбор выявил отдельный fail-fast/race defect в find_fill001_runtime_binding(): проверка diagnostics выполнялась до фильтрации session по executor window. Поэтому даже старая или ещё не завершённая потенциально подходящая session могла остановить поиск окончательной FillMatrixError. Stage 6 worker не повторял такую ошибку, а UI-кнопка только читала старый executor report.

Исправление опубликовано в [5cde7a1](https://github.com/Kiddos19882/AutoDraw/commit/5cde7a109a669bebf790ecbeb21f8bbc4feae182):

- Сначала проверяются timezone-aware started_at_utc, connection_closed_at_utc и возможность исключить session из executor window.
- Отсутствующие bridge_diagnostics или last_message_at_utc у потенциально подходящей session трактуются как pending; неполная session блокирует выбор другой session до разрешения неоднозначности.
- Строгие проверки schema v2, task/session/run identity, source-plan hashes, точного CHALK/per-stroke attribution, radius, P1, sequence gaps, Bridge failures и PNG audit не ослаблены.
- FILL-001 кнопка повторно вызывает runtime binder для отчёта со статусом, отличным от passed; только успешный binding записывается в report и допускает следующий PNG audit.
- Stage 6 и UI используют общий summary builder; background worker не перезаписывает уже подтверждённый passed status.
- Добавлены regression tests на неполную session → последующее обновление → успешный binding, исключение future session без diagnostics и повторную привязку из UI.

Полный GitHub Actions [41754801210](https://github.com/Kiddos19882/AutoDraw/actions/runs/41754801210) завершился **SUCCESS** на commit 5cde7a1: Preparation/G3 — 787 passed, 24 warnings, 82 subtests; Executor regression, Game Monitor/Bridge, Application integration, INT-006 pixel audit и Windows portable build/startup smoke-test — SUCCESS; optional benchmarks — SKIPPED. Portable artifact ID 13288855067.

**Граница результата:** это подтверждает software regression/build gate, но не принимает пользовательский capture. Session-level CHALK=5999 подтверждён, однако второй Bridge run не был полностью проверен в рамках этого исправления; task-level/per-stroke attribution и quantitative FILL-001 PNG audit остаются неподтверждёнными. Новый live preflight не запускался; доска из предыдущей попытки исчерпана. 45-cell matrix остаётся BLOCKED.

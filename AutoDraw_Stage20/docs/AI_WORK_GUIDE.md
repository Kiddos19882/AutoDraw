# Регламент работы ИИ с AutoDraw — краткий вход

**Статус:** ACTIVE. **Обновление навигации:** 2026-11-08.  
Прежняя подробная редакция сохранена побайтово: [AI_WORK_GUIDE_HISTORY_THROUGH_2026-11-08.md](AI_WORK_GUIDE_HISTORY_THROUGH_2026-11-08.md). Постоянные доказательные и инженерные правила остаются в [EVIDENCE_AND_VALIDATION](EVIDENCE_AND_VALIDATION.md), [ENGINEERING_INVARIANTS](ENGINEERING_INVARIANTS.md) и [EXPERIMENT_STANDARD](EXPERIMENT_STANDARD.md).

## 1. Начало любой значимой задачи

1. Проверить удалённую ветку `feature/image-geometry-optimization`, HEAD, последние 20 коммитов и доступные изменения/CI. **Не утверждать локальный `git status`: GitHub API его не предоставляет.** `master` без прямого задания не трогать.
2. Прочитать [PROJECT_STATUS](PROJECT_STATUS.md) → [TASKS](TASKS.md) → [ROADMAP](ROADMAP.md); это компактные **текущие** данные, а не история.
3. Определить конкретные source files, tests, protocols, [DECISIONS](DECISIONS.md), профильные инварианты и [TEST_RESULTS](TEST_RESULTS.md), только затем принимать решение. По CHALK, FILL, Game Monitor и renderer обязательно сверить исходную экспериментальную методику/данные.
4. Зафиксировать цель, разрешённый тип работы, ограничения, baseline, способ проверки и возможные риски. Пользовательское последнее прямое разрешение определяет допустимый объём.

**Проверка текущих потребителей:** после `--find` вызвать `python AutoDraw_Stage20/tools/check_markdown_docs.py --root AutoDraw_Stage20 --usage`. `DIRECT_CALL_CANDIDATE` и `IMPORTED_ONLY` — **синтаксические** результаты; локальные/callback/dynamic вызовы могут быть не распознаны. Сверить кандидатов вручную на текущем SHA. CI блокирует **новую** безусловную root-level SCC `source/preparation`, но deferred SCC — лишь предупреждение. [Границы](DEPENDENCY_MAP.md).

**Быстрый поиск:** [единый индекс всех .md](README.md). Все старые управляющие документы до 2026-11-08 доступны как `*_HISTORY_THROUGH_2026-11-08.md` и не являются текущим backlog.

## Reuse-first перед любым новым кодом (2026-11-12)

1. Сформулировать потребность как функцию («очистить игровую доску», «подключить Bridge»), а не как имя нового класса.
2. Найти её по синонимам и ID в [каталоге возможностей](COMPONENT_CATALOG.md), прочитать назначение, owner, scope, запреты и связанную тестовую точку. Каталог — навигация, не доказательство.
3. На **текущем remote SHA** открыть реализацию и потребителей, проверить аргументы, side effects и инварианты. При несовпадении с каталогом сообщить о конфликте, не предполагать совместимость.
4. Сначала прямое повторное использование, затем тонкий адаптер, затем минимальное расширение. Отдельная реализация лишь при доказанной несовместимости и зафиксированном решении.
5. Результаты тестов привязывать к конкретному CI SHA (E2/E3); runtime/game E4 не выводить из статического аудита. При изменении API обновлять owner-карточку, тесты и CI audit в том же разрешённом scope.

Быстрый запрос: `python AutoDraw_Stage20/tools/check_markdown_docs.py --root AutoDraw_Stage20 --find "измерить CHALK"`; результаты — кандидаты E1, даже при совпадении названия необходимо открыть текущую реализацию.

Контроль: `tools/check_markdown_docs.py` проверяет структурные записи каталога через Python AST, но **не** принимает архитектурное или production-решение автоматически.

## Чтение больших файлов GitHub — проверенный Git blob способ (2026-11-13)

**Рабочее решение (E1/PASS на шести реальных файлах):** подключённый GitHub `fetch_file` для JSON больше 1 МБ даёт `content=""` даже с `encoding=base64`, но возвращает **Git blob SHA**. Использовать подключённую операцию GitHub **`fetch_blob(repository_full_name, blob_sha)`**, подставляя ровно этот SHA. Она вернула полное UTF-8 содержимое всех шести Monitor JSON серии `fill001-series-3e1fd32c4d99` (12.4–51.0 млн символов каждый); каждый JSON был успешно разобран в памяти. **В следующем чате найти действие `mcp__GitHub__fetch_blob` через список доступных GitHub tools, а не повторять безуспешные вызовы `fetch_file`.** Для больших документов получать один файл за раз и выводить только сводку, не всё содержимое.

**Рецепт при наличии GitHub connector:**
1. На текущей ветке/зафиксированном commit прочитать `fetch_file({repository_full_name:"Kiddos19882/AutoDraw",path:".../game-monitor-run-....json",ref:"<commit>"})`. При пустом `content` сохранить `result.sha` (Git blob SHA).
2. Вызвать `fetch_blob({repository_full_name:"Kiddos19882/AutoDraw",blob_sha:"<sha>"})`; взять `result.content` и разобрать `JSON.parse` непосредственно внутри одного вызова оркестратора tools. Не выводить массив `events` целиком.
3. Сопоставить `session_id`, `run_id`, `pre_test_snapshot`, `post_test_snapshot`, `point_delta_matches_chalk` с Stage6/series artifact; проверить `sum(accepted_points[*].point_delta) == post.pointCount-pre.pointCount`, ошибки, пропуски и transport drop. **Не считать `accepted_points.length` эквивалентом CHALK**: в отдельных runs встречается `point_delta=2`.
4. Для Egret replay проверять, что реализованный replay validator поддерживает конкретные события и их `point_delta` (не подгонять raw evidence); сохранять реальные границы штрихов и наблюдавшиеся радиусы, отделяя изменения кисти при slider от рисования.
5. `fetch_blob` возвращает разобранный текст **через connector**, а не локальный файл. Прямой `curl`/raw.githubusercontent.com и локальный git в текущем контейнере заблокированы сетью. Если нужен физический файл, использовать отдельно разрешённый экспорт/артефакт; не утверждать, что JSON уже лежит на диске.

**Замороженная выборка:** source commit `3f67c05d8dfd2f4db8954063850bd67b96232dd1`, одна сессия `e04234bc-b9ee-4d06-bd20-f1e13b8423ba`:

| Figure | Monitor JSON Git blob SHA | accepted_points.length | sum(point_delta) = exact CHALK |
|---|---|---:|---:|
| C1-F1 | `623be5e5e730fb009ee49afe2267d7de8d826a78` | 5759 | 5759 |
| C1-F2 | `93771f49728c54b33a303dab68377e9df4f418a1` | 1971 | 1971 |
| C1-F3 | `3b939c4454f986c1954f192e75f5438939d11643` | 5740 | 5741 |
| C2-F1 | `5ef05dcfeded397df3f55ab7dcdb88ea560e7b8c` | 5752 | 5752 |
| C2-F2 | `f1bdbbac9a13a8f3d3a14309c6856dfeead8262f` | 5766 | 5767 |
| C2-F3 | `4d7959ba62479439eaa83f44c51e2a1008f1eabb` | 1528 | 1528 |

Для всех шести `point_delta_matches_chalk=true`, `dropped_events=0`, `bridge_send_failures_delta=0`, `collector_sequence_gap_count=0`; первые пять не обязаны быть полными качественными рисунками (часть `QUOTA_LIMITED`). Два файла имеют **один** event `point_delta=2`. `monitor_buffer_dropped_events_delta` в некоторых runs положителен, но это локальный capped history buffer, не потеря записей run recorder.

**Статусы:** connected GitHub blob retrieval 6/6 **PASS (E1 чтение данных)**; исходный игровой exact CHALK — архивное E4, не новый E4; Egret replay 6/6 **NOT_RUN**; визуальное сравнение **NOT_RUN**; новое CI **NOT_RUN**. Реальный Git blob hash предоставлен API как ключ fetch; независимая повторная локальная `git hash-object` этих текстов здесь не запускалась.

**Внешний запасной путь:** RAW по закреплённому commit через `https://raw.githubusercontent.com/<owner>/<repo>/<commit>/<path>` с `curl --fail --location --output ...`, затем `git hash-object` и JSON parse. GitHub REST Contents API поддерживает `Accept: application/vnd.github.raw+json` для диапазона 1–100 МБ; также Git Blobs API. **В этом окружении прямые HTTPS-загрузки BLOCKED**, поэтому не приписывать им PASS. Документация GitHub: https://docs.github.com/en/rest/repos/contents и https://docs.github.com/en/rest/git/blobs.

## 2. Что считать доказательством

| Вопрос | Первичный источник |
|---|---|
| Как устроено приложение? | Код конкретного commit, конфигурации и модели |
| Что охватывают тесты? | Сами тесты |
| Был ли PASS? | Result конкретного CI run/job на конкретном SHA |
| Работает ли в игре? | Конкретный runtime run, скриншоты, executor/Bridge/Monitor artifacts |
| Сколько потрачено CHALK? | Только валидное `post.pointCount-pre.pointCount` |
| Какое решение действует? | [DECISIONS](DECISIONS.md), но его реализованность отдельно проверить кодом |
| Что делать дальше? | [TASKS](TASKS.md), приоритет [ROADMAP](ROADMAP.md) |

Не переводить E1/E2/E3 в E4 или E5 без первичных данных. Не подменять CHALK длиной пути, количеством штрихов, coverage, площадью или radius. Измеренная экономия на одном scenario не универсальна для новых drawing domains.

## 3. Безопасность и совместимость

- Сначала читать реализацию, затем править. Сохранять working pipelines image/preparation/planners/Stage6/Game Monitor/Bridge. Не менять production CHALK predictor или executor defaults из-за одной офлайн-оценки.
- Связывать изменения и тесты с точным commit, а результаты — с experiment/task/run и hashes. Primary evidence и rejected captures сохранять.
- Обычная сборка/CI не доказывают live рисунок, качество PNG или 95%-й safety margin. Для каждого claim указывать границы, статус и источник.
- ИИ не управляет запущенным на ПК пользователя AutoDraw и игровой сессией через GitHub; live-тесты возможны только по отдельному разрешению и с данными пользователя.
- Если документация конфликтует с кодом/новыми evidence, не придумывать соглашение: отметить конфликт и ссылаться на соответствующий источник.

## 4. Как изменять документацию

- `PROJECT_STATUS.md`: только актуальные факты и блокеры.
- `TASKS.md`: открытые задачи и критерии закрытия.
- `ROADMAP.md`: зависимости будущих шагов.
- `DECISIONS.md`: принятые решения с уникальными ID и историей переименований.
- `TEST_RESULTS.md`: краткий индекс результатов; подробности — в первичных отчетах.
- `WORK_LOG.md`: факт работы; `CHANGELOG.md`: важные изменения.
- Исторические snapshots не переписывать и не удалять; не создавать второй параллельный статус. Перед коммитом проверить diff, ссылки и Markdown audit.

Перед документационным коммитом запускать `python AutoDraw_Stage20/tools/check_markdown_docs.py --root AutoDraw_Stage20`; в CI проверять конкретный SHA. [Run 42421451709](https://github.com/Kiddos19882/AutoDraw/actions/runs/42421451709) подтвердил навигацию 99 .md и архивы, но не проверяет внешние URL/живую игру.


## Работа с большими первичными данными без перегрузки чата (2026-11-14)

**Правило по умолчанию:** большие Monitor/Bridge JSON, PNG, CI logs и другие raw evidence анализируются рядом с хранилищем (предпочтительно существующим анализатором в GitHub Actions), а в чат возвращается **только компактный итог**. Даже чтение через GitHub `fetch_blob` с обработкой в инструменте может перегружать передачу и контекст; успешное чтение в прежнем сеансе не гарантирует стабильности следующего. Desktop Commander не является обязательным путём для больших файлов.

1. Начать с HEAD, task ID, существующего анализатора/harness и небольших диапазонов документации/кода (обычно до 50–100 строк). Не загружать целиком большие raw JSON или логи в контекст и не повторять их вывод в ответе.
2. Для больших данных предпочитать уже существующий CI job/скрипт, который читает immutable файл внутри runner, проверяет source commit, blob/SHA-256, session/run binding и выводит ограниченный JSON summary (ориентир 2–10 КБ). Для диагностических событий сохранять только необходимый контекст, агрегаты, идентификаторы и ссылки на первичные артефакты; не выводить массивы events и изображения в чат.
3. Не создавать второй parser или workflow без проверки reuse-first. Новые изменения кода, CI и эксперименты — только в разрешённом scope; для значимого эксперимента фиксировать протокол, baseline и gates заранее. Запуск CI — отдельное тестирование, не доказательство live E4.
4. Исходные captures, frozen models, SHA, отрицательные результаты и история неизменяемы. Любой summary обязан указывать версию анализатора/commit, input hashes, run/session IDs, метод, PASS/FAIL/BLOCKED/UNKNOWN и ограничения; если нет точной координаты accepted point, не реконструировать её догадкой и не объявлять pixel-exact.
5. При ошибках передачи (`fetch failed`, oversized response, timeout) прекратить повторные полные загрузки; перейти к небольшому read-only запросу или bounded CI summary. Если невозможно проверить результат — честно отметить BLOCKED, а не считать PASS.

**Текущий первый потребитель:** `ENGINE-001 / replay next gate` в [TASKS](TASKS.md) — выяснить, есть ли независимый immutable источник двух отсутствующих координат `point_delta=2` для C1-F3/C2-F2. Сначала read-only inventory существующих анализаторов и формата событий, затем при необходимости отдельный ограниченный CI diagnostic с новым ID и заранее указанными критериями. Исторические два replay остаются `DIAGNOSTIC_ONLY`, пока координаты не доказаны.

## 5. Закрытие задачи

В ответе перечислить: что изучено/выполнено, какие файлы затронуты, исправленные и открытые проблемы, какие проверки действительно прошли, какие выводы доказаны/остались гипотезами, SHA/ветку/статус CI, необходимый следующий шаг. Не объявлять `CI PASS` до завершения workflow.

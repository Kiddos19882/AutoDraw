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

## Чтение больших GitHub-файлов (2026-11-13; воспроизводимый рецепт и ограничения проверки)

**Проблема:** GitHub Contents API в JSON/object-формате при размере файла **более 1 МБ и до 100 МБ** может вернуть `content=""`, хотя файл существует и Git blob SHA известен. Это **не** означает, что JSON пуст. Встроенный GitHub `fetch_file` проекта при `encoding=utf-8` и `encoding=base64` вернул пустой `content` для Monitor JSON; менять `encoding` недостаточно.

**Предпочтительный способ, когда доступны исходящие HTTPS-запросы:** читать файл **RAW** по **зафиксированному commit SHA**, потоково писать его на диск и проверить целостность. Для публичного репозитория в терминале:

```bash
COMMIT=3f67c05d8dfd2f4db8954063850bd67b96232dd1
PATH_IN_REPO=AutoDraw_Stage20/data/results/brush_behavior_tests/game_monitor_bridge/e04234bc-b9ee-4d06-bd20-f1e13b8423ba/game-monitor-run-20261113T055652967299Z-66b8a7ae.json
curl --fail --location --retry 2 --output /tmp/autodraw-monitor.json "https://raw.githubusercontent.com/Kiddos19882/AutoDraw/$COMMIT/$PATH_IN_REPO"
git hash-object /tmp/autodraw-monitor.json
python -m json.tool /tmp/autodraw-monitor.json >/dev/null
```

Ожидаемый **Git blob SHA** этого конкретного файла из GitHub `fetch_file`: `4d7959ba62479439eaa83f44c51e2a1008f1eabb`. Считать операцию успешной только после ненулевого размера, HTTP 200, совпадения `git hash-object`, корректного JSON, проверки `session_id/run_id` и run-bound integrity. Коммит закрепляет версию; `git hash-object` проверяет именно Git blob, а не SHA-256 PNG. Не печатать гигантский JSON целиком в чат — читать локально, извлекать требуемые поля.

**Официальный REST fallback** для файлов 1–100 МБ: `GET https://api.github.com/repos/Kiddos19882/AutoDraw/contents/<PATH>?ref=<COMMIT>` с `Accept: application/vnd.github.raw+json`; альтернативно `GET https://api.github.com/repos/Kiddos19882/AutoDraw/git/blobs/<BLOB_SHA>` с тем же RAW media type. Обычный object response содержит пустое `content` и `encoding=none`; Git Blobs JSON response содержит base64, но требует больше памяти. Обе REST-операции документированы с ограничением 100 МБ. Для ещё больших файлов использовать `git clone` / `git fetch` с последующим `git show <COMMIT>:<PATH>` либо доступные git/LFS-процедуры — не считать это подтверждённым тестом до фактического чтения и проверки hash.

**Фактическая проверка в этом чате:**
- `GitHub fetch_file` (UTF-8 и base64) для указанного Monitor JSON: **BLOCKED**, `content.length=0`, Git blob SHA одинаковый.
- RAW с `raw.githubusercontent.com` через web: **BLOCKED**, cache miss; Git Blobs API через web: **BLOCKED**, endpoint недоступен этому инструменту.
- Из вычислительного контейнера `github.com`, `api.github.com`, `raw.githubusercontent.com`: **BLOCKED**, DNS/network. Поэтому **фактическая загрузка большого файла данным рецептом здесь НЕ ПРОВЕРЕНА**; его поддержка подтверждена официальной документацией, а не end-to-end тестом.
- Не отмечать RAW/Blob/Git как PASS, пока реальный файл не скачан и не прошёл проверки. При восстановлении доступа первым делом проверить этот конкретный frozen Monitor JSON и внести результат со SHA в `TEST_RESULTS.md`.

**Официальные источники:**
- https://docs.github.com/en/rest/repos/contents — RAW в диапазоне 1–100 МБ;
- https://docs.github.com/en/rest/git/blobs — blob и RAW до 100 МБ;
- https://github.blog/changelog/2022-05-03-increased-file-size-limit-when-retrieving-file-contents-via-rest-api/ .

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

## 5. Закрытие задачи

В ответе перечислить: что изучено/выполнено, какие файлы затронуты, исправленные и открытые проблемы, какие проверки действительно прошли, какие выводы доказаны/остались гипотезами, SHA/ветку/статус CI, необходимый следующий шаг. Не объявлять `CI PASS` до завершения workflow.

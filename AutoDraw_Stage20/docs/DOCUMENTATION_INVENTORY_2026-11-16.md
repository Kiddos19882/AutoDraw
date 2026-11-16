# Инвентаризация документации AutoDraw — 2026-11-16

**Область:** фактический GitHub tree `8273918226ff221dc94faf7a212e959a4c49fa49` ветки `feature/image-geometry-optimization`, `AutoDraw_Stage20/docs/`, `AutoDraw_Stage20/(*.md)`, `.github/workflows/`. Это новый снимок; старый [аудит 2026-11-03](DOCUMENTATION_INVENTORY_2026-11-03.md) сохранён без изменений. **Тип проверки:** E1 GitHub tree/path inventory, не семантическое доказательство корректности каждого Markdown. Новые документы, созданные после указанного SHA, не включены в исходный подсчёт.

## Количественный состав на HEAD-аудита

| Категория | Файлов | Примечание |
|---|---:|---|
| Все файлы `docs/` | **128** | 127 Markdown + 1 JSON provenance |
| `docs/*.md` | **127** | включая исторические и специализированные протоколы |
| Markdown в корне `AutoDraw_Stage20/` (не docs) | **16** | также исторические/тематические документы, не второй active backlog |
| Исторические Markdown `*HISTORY*`/`*SNAPSHOT*` в docs | **10** | frozen reference, не изменять и не считать актуальными задачами |
| `ENGINE001_*PROTOCOL_*.md` в docs | **44** | последовательные измерения и замороженные методики; P4 добавлен отдельно **после** аудита |
| GitHub Actions workflow YAML | **58** | потенциальная проверочная инфраструктура, не значит 58 выполненных проверок |
| Всего элементов Git tree | **7485** | GitHub `truncated=false` |
| Объём всех документов docs | **4 132 427 байт** | исходный SHA, до новых файлов |

По снимку основные действующие файлы уже велики: `PROJECT_STATUS.md` 256080 B, `TASKS.md` 188967 B, `ROADMAP.md` 92892 B, `TEST_RESULTS.md` 198899 B, `WORK_LOG.md` 206251 B, `README.md` 36842 B, `CHANGELOG.md` 56802 B (GitHub sizes, могут отличаться от длины полученного через API UTF-8). Нельзя объявить полную дедупликацию или полный аудит ссылок по одному tree list.

## Обнаруженные проблемы и точечная синхронизация

| Finding ID | Проблема на HEAD аудитa | Решение и источник |
|---|---|---|
| DOC-SYNC-20261116-01 | `TASKS.md` одновременно имеет [x] P3b-P0 и ещё открытый дубль P0, а также открытые P3a3 и P3b-P1 с `UNKNOWN` несмотря на завершившийся CI | Закрыть дубли в **активном** разделе; P0/P1 historical evidence оставить в `TEST_RESULTS.md`, `WORK_LOG.md` и протоколах |
| DOC-SYNC-20261116-02 | `PROJECT_STATUS.md` содержит как более ранние `UNKNOWN/NOT_RUN`, так и поздние подтверждённые E3 результаты в хронологической цепочке | Добавить **короткое актуальное резюме сверху**, пометить нижние записи хронологическим журналом, не переписывать прошлое |
| DOC-SYNC-20261116-03 | `README.md` индексирует старый `V43-P3b path replacement` как «next», не называет поздний E3 P1 и решение пользователя о full repaint | Сделать ссылку на новый **единственный** [P4 full adaptive fill protocol](ENGINE001_V43P4_FULL_ADAPTIVE_FILL_PROTOCOL_2026-11-16.md) главным маршрутом; старые этапы как reference evidence |
| DOC-SYNC-20261116-04 | `ROADMAP.md` содержит исторические формулировки, в которых P3b является планируемой стратегией | Добавить сверху текущую следующую последовательность P4.0→P4.1→P4.2→P4.3→B1; подробности только в P4 protocol |
| DOC-SYNC-20261116-05 | Старый inventory 2026-11-03 называет 72 Markdown, что уже не соответствует Git tree 2026-11-16 | Старый snapshot **сохранён**, этот новый inventory датирован и привязан к SHA |
| DOC-SYNC-20261116-06 | Неочевидная граница `CI success` vs `quality FAIL` и exact game CHALK | P3b-P0 [CI43878183627](https://github.com/Kiddos19882/AutoDraw/actions/runs/43878183627) E3 capture SUCCESS, замена 0/18; P1 [CI43882838806](https://github.com/Kiddos19882/AutoDraw/actions/runs/43882838806) E3 capture SUCCESS, замена 0/36; `CHALK` P4 NOT_RUN. Перенести верхний текущий статус в index с правильным уровнем evidence |
| DOC-SYNC-20261116-07 | `DECISIONS`, `ENGINEERING_INVARIANTS`, `EVIDENCE_AND_VALIDATION`, `EXPERIMENT_STANDARD` содержат долгосрочные правила и не требуют нового дублирования | Сослаться на них из P4 protocol; не создавать вторую независимую таблицу правил |

## Назначение действующих источников (single authority)

- (ф) `README.md` — навигация и короткая ссылка на текущий P4.
- (ф) `PROJECT_STATUS.md` — **последние подтверждённые факты**, E0–E5, оставшиеся блокеры.
- (ф) `TASKS.md` — **только реально открытые задачи и ближайший шаг**.
- (ф) `ROADMAP.md` — будущие этапы P4 и необходимые переходы.
- (ф) `DECISIONS.md` + `ENGINEERING_INVARIANTS.md` — принятые инварианты и решения.
- (ф) `TEST_RESULTS.md` — индекс реально выполненных проверок с CI SHA; E3 renderer SUCCESS не равен algorithm quality PASS.
- (ф) `WORK_LOG.md` — что сделано и какие коммиты, отрицательные результаты сохранены.
- (ф) `CHANGELOG.md` — значимые изменения; не повторять каждую промежуточную попытку.
- (ф) `ENGINE001_V43P4_FULL_ADAPTIVE_FILL_PROTOCOL_2026-11-16.md` — единственный *текущий* детальный план полной замены старых 1945 paint strokes.
- (ф) `DOCUMENTATION_INVENTORY_2026-11-03.md` и 10 файлов `*_HISTORY_*` — исторические снимки, не backlog.

## Проверки и границы инвентаризации

E1 PASS: GitHub tree (без усечения), файловые размеры, имена, действующие протоколы и доступные CI-workflows, прочитанные текущие README/STATUS/TASKS/ROADMAP/GUIDE и релевантные DECISIONS/INVARIANTS/EVIDENCE/EXPERIMENT/TESTS. **NOT_RUN**: полный link/anchor checker и Markdown CLI на живом checkout: доступ GitHub connector позволяет менять файлы и получить status, но не запускает локальную команду; статус будет отдельно обновлён только по реальному `docs-integrity` CI или отчёту `python AutoDraw_Stage20/tools/check_markdown_docs.py --root AutoDraw_Stage20`. **Не подтверждены** локальный `git status` машины пользователя и game runtime. Ни один исторический snapshot не удалялся, не переименовывался и не переписывался.

## Решение об объёме синхронизации

Синхронизировать только актуальные верхние блоки существующих `README.md`, `PROJECT_STATUS.md`, `TASKS.md`, `ROADMAP.md`, `TEST_RESULTS.md`, `WORK_LOG.md`, `CHANGELOG.md`. Не выполнять массовую автоматическую очистку тысяч исторических строк или 44 протоколов без отдельной записи provenance: масштабный rewrite может уничтожить отрицательные evidence/некоторые ссылки. Следующий самостоятельный DOC-AUDIT возможен **после** подтверждённого CI и отдельного определения правил переноса старых inline записей в архив, но не блокирует P4 план.

## GitHub docs-integrity evidence при синхронизации (2026-11-16)

[CI43952023203](https://github.com/Kiddos19882/AutoDraw/actions/runs/43952023203) на `d683190da9b7164b65913ae445cd1679862651ab` **FAIL**, 11/11 Python unit PASS, 2 `unindexed_files`: `ENGINE001_V43P3B_P1_ROW_INTERSECTION_PROTOCOL_2026-11-16.md` и новый `ENGINE001_V43P4_FULL_ADAPTIVE_FILL_PROTOCOL_2026-11-16.md`. [CI43952243621](https://github.com/Kiddos19882/AutoDraw/actions/runs/43952243621) на `4fc9f891942e56f9310c8df4308ab6f291f047f9` **FAIL**, 11/11 Python unit PASS, 3 unindexed files (добавлена новая инвентаризация). В обоих аудитах `current_broken_links=0`, `duplicate_decisions=0`, `history_integrity_errors=0`, `historical_link_warnings=0`, `capability_catalog_errors=0`.

**Причина и исправление:** `tools/check_markdown_docs.py::check_links` индексирует Markdown, только если есть прямой Markdown-link из `docs/README.md`. Links на P4 и inventory были добавлены в `68bac66566d70490e7621244e5533477cb6ac096`, [последняя отсутствовавшая ссылка на P3b-P1](README.md) — коммит `db21a97b315643f039dc2d395400f26b659e829e`. Следующий соответствующий [CI43952776987](https://github.com/Kiddos19882/AutoDraw/actions/runs/43952776987) на SHA `db21a97b...` при проверке был `PENDING`; **Markdown PASS пока не подтверждён**. Ни история, ни тестовый инструмент не изменялись. Эта запись документирует отрицательный результат и исправление, последующие CI проверять по их действительному SHA.


## Повторная проверка 2026-11-17 — актуальность инвентаризации (E1, PARTIAL)

**Проверенный перед правками remote commit:** `50f82ff0e4e106727582ce89f48ae48bf3fd257d`, ветка `feature/image-geometry-optimization`; просмотрены 20 последних коммитов и актуальные README/TASKS/STATUS/ROADMAP/TEST_RESULTS/WORK_LOG/CHANGELOG. Таблица количеств выше **относится только к старому tree SHA `8273918226ff`**: после снимка добавлены P4 protocol и этот inventory, а также обновлены индексы. **Новый полный рекурсивный tree, точное число Markdown/YAML, полные bytes и audit CLI на текущем HEAD: NOT_RUN/UNKNOWN** (GitHub connector в этом сеансе не предоставил способ рекурсивно перечислить дерево или запустить checker). Не выдавать старые 127/44/58/7485 за нынешний подсчёт. Удалений исторических snapshot не предпринималось.

**Повторно подтверждённые расхождения:** (1) `TASKS.md` имел 143 `- [ ]` по всему документу, из них один в текущем верхнем разделе; остальные — записи истории. Добавлена явная граница действующего backlog; старые чекбоксы сохранены для provenance. (2) `README.md` описывал V44-P1 как pre-native, несмотря на подтверждённый [E3 CI43813812976](https://github.com/Kiddos19882/AutoDraw/actions/runs/43813812976) и пользовательский выбор V44-B; запись уточнена без повышения качества до E4/E5. (3) [CI43952023203](https://github.com/Kiddos19882/AutoDraw/actions/runs/43952023203) и [CI43952243621](https://github.com/Kiddos19882/AutoDraw/actions/runs/43952243621) — реально FAILED на проверке индекса; [CI43952776987](https://github.com/Kiddos19882/AutoDraw/actions/runs/43952776987) через доступный запрос jobs вернул пустой массив, поэтому **результат UNKNOWN, не PASS**. Ссылки на P3b-P1, P4 и inventory сейчас явно содержатся в README, но checker не перезапускался.

**Статус синхронизации:** `PARTIAL` по E1. Документные правки разрешены; test/CI execution не разрешён и не проводился. Для полного закрытия DOC-SYNC требуется на свежем HEAD рекурсивный tree recount и запуск штатного Markdown auditor с фиксацией commit SHA, workflow jobs и итогового отчёта. Это **отдельный следующий шаг**, а не условие начала утверждённой P4 разработки.

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

**Дополнение 2026-11-17 (последовательная синхронизация):** повторная проверка 20 коммитов на стартовом SHA `1996fe211adda01606b562ce98fc191b096bf0c6` обнаружила некорректную историческую фразу `V44-P2 next` **перед** действующим разделом ROADMAP V43-P4 и формулировку README «теперь тестируем», хотя P4 `NOT_RUN`. Уточнено, что V44-B — эталон для P4, P4 ещё предстоит разработать и испытать. Также ограничена интерпретация исторических `[ ]` в TASKS: они не являются активными поручениями ENGINE-001, но и не означают автоматически закрытие отдельных FILL001/DOC-* направлений. Коммиты: ROADMAP `119d2e73`, TASKS `a05c68a1`, README `285d30cd`. **Рекурсивный tree, полный Markdown CLI и новый CI не запускались; статус `PARTIAL` сохраняется.**

## Delta-инвентаризация по GitHub Compare — 2026-11-17 (E1)

Источник: [сравнение исходного tree SHA `8273918226ff` с рабочей веткой](https://github.com/Kiddos19882/AutoDraw/compare/8273918226ff221dc94faf7a212e959a4c49fa49...feature/image-geometry-optimization) на HEAD `6629c9d2dcccee0e09eea578c537b188d001fac3` перед этой записью. GitHub Compare сообщил `status=ahead`, `ahead_by=25`, `behind_by=0`, ровно **9 изменённых путей**, из них **2 added** (`docs/DOCUMENTATION_INVENTORY_2026-11-16.md`, `docs/ENGINE001_V43P4_FULL_ADAPTIVE_FILL_PROTOCOL_2026-11-16.md`), остальные 7 `modified`; `removed/renamed=0`, workflow изменения отсутствуют. Это **дельта-проверка**, не повторный рекурсивный tree listing и не запуск Markdown checker.

| Категория | Базовый tree `8273918226ff` | Изменение по Compare | Вывод на `6629c9d2` |
|---|---:|---:|---:|
| `docs/*.md` | 127 | +2 | **129** |
| `docs/` всех файлов | 128 | +2 | **130** (129 MD + 1 JSON) |
| `ENGINE001_*PROTOCOL_*.md` | 44 | +1 | **45** |
| Markdown в корне `AutoDraw_Stage20` | 16 | 0 | **16** |
| `*.yml/*.yaml` в `.github/workflows` | 58 | 0 | **58** |
| Git tree elements | 7485 | +2 | **7487** (delta-derived, NOT direct tree recount) |
| Historical `*HISTORY*/*SNAPSHOT*` Markdown | 10 | 0 | **10** |

**Оговорка:** объём байт в дереве не пересчитан; 4 132 427 B — только прежний snapshot. Указанные выводы о количестве относятся к проверенному HEAD `6629c9d2` до новых документов этого аудита (все последующие правки — существующих файлов). Показатели CI/Markdown validation не меняются на PASS от этого сравнения; нужна отдельно подтверждённая job `markdown-integrity` с конкретным SHA.


## Delta-инвентаризация после P4/B0/B1 — 2026-11-17 (E1, GitHub Compare)

Проверка [GitHub Compare](https://github.com/Kiddos19882/AutoDraw/compare/8273918226ff221dc94faf7a212e959a4c49fa49...feature/image-geometry-optimization) от исходного tree `8273918226ff221dc94faf7a212e959a4c49fa49` до `13e85c7bf63667d4d236eccc9754989b31358127` (до этой дописки): `ahead_by=86`, `behind_by=0`, **22 изменённых пути**, из них **13 added**, 9 modified и **0 removed/renamed**. Все новые файлы локализованы: **3 Markdown docs** (`DOCUMENTATION_INVENTORY_2026-11-16.md`, P4 protocol, B1 protocol), **4 Actions YAML** (P4 source/native, B1 source/native), **6 tests/tools Python** (P4/B1 planners, P4/B1 native runners, P4/B1 tests). Это точная дельта путей GitHub, **не самостоятельное рекурсивное перечисление** дерева HEAD. Дополнительных удалений или изменений архива `*HISTORY*/*SNAPSHOT*` по этому сравнению нет.

| Категория | На исходном tree | Дельта | Вывод на `13e85c7b` |
|---|---:|---:|---:|
| (п) docs, Markdown `*.md` |127|+3|**130**|
| (п) docs, все файлы |128|+3|**131** (130 MD +1 JSON)|
| `ENGINE001_*PROTOCOL_*.md` |44|+2|**46**|
| (п) корень `AutoDraw_Stage20/`, Markdown не в docs |16|0|**16**|
| (п) `.github/workflows/`, YAML |58|+4|**62**|
| Исторические docs Markdown HISTORY/SNAPSHOT |10|0|**10**|
| Элементы Git tree |7485|+13|**7498** (delta-derived, не повторный рекурсивный tree API)|

**CI доказательства отдельно от количеств:** [docs-integrity CI43985999558](https://github.com/Kiddos19882/AutoDraw/actions/runs/43985999558) SUCCESS на `e7bf5f79` после индексации B1, более ранний [CI43985691856](https://github.com/Kiddos19882/AutoDraw/actions/runs/43985691856) FAIL из-за нового неиндексированного B1 protocol — отрицательный исход сохранён. Для последующих документационных SHA проверять их собственный CI. Не считать Markdown PASS доказательством корректности native B0/B1 качества. Исторические абсолютные байты документов не пересчитывались.


## Обновление количественного состава после B2 preflight — 2026-11-17 (E1 GitHub Compare)

GitHub Compare `8273918226ff221dc94faf7a212e959a4c49fa49...feature/image-geometry-optimization` на проверенном SHA `0cdc6e41914de1745380c2b389407ce963d97fc3`: `ahead_by=103`, `behind_by=0`, **26 изменённых путей**, из них **17 added, 9 modified, 0 removed/renamed**. Дельта от прошлого снимка: добавлены один (ф) B2 protocol Markdown, два (ф) Python runner/test B2 и один (ф) workflow B2; исторические файлы не удалялись.

| Тип | Исходный tree 82739182 | Дельта текущего сравнения | На SHA 0cdc6e41 |
|---|---:|---:|---:|
| `docs/*.md` |127|+4|**131**|
| Все файлы `docs/` |128|+4|**132** (131 MD + 1 JSON)|
| `ENGINE001_*PROTOCOL_*.md` |44|+3|**47**|
| Markdown root Stage20 (не docs) |16|0|**16**|
| `.github/workflows/*.yml/*.yaml` |58|+5|**63**|
| Исторические HISTORY/SNAPSHOT Markdown |10|0|**10**|
| Всего элементов Git tree (derived by path delta) |7485|+17|**7502**|

Этот пересчёт основан на полном списке **изменённых путей GitHub Compare**, а не на новом рекурсивном tree call; bytes не переизмерены. Исторические числовые таблицы на прежних SHA ниже/выше — датированные и не считаются активными без указания SHA. CI проверяется отдельно и никогда не доказывает качество рисунка.


## Актуализация после B2-FULL source-only preflight — 2026-11-17 (E1)

GitHub Compare исходного SHA `8273918226ff221dc94faf7a212e959a4c49fa49` с рабочей веткой HEAD `39f5c76c802dd154688bf02b8ddb9179cd1f75bf` (перед этой записью): **127 commits ahead**, behind0; **30 changed paths**, из них21 новых, 9 modified, zero deleted/renamed. В сравнении с предыдущим снимком добавлены: (ф) `ENGINE001_V43P4_B2_FULL_BOUNDARY_REPAIR_PROTOCOL_2026-11-17.md`, (ф) `tests/run_engine001_v43p4_b2_full_source.py`, (ф) `tests/test_engine001_v43p4_b2_full_source.py`, (ф) `.github/workflows/engine001-v43p4-b2-full-source.yml`; текущий code/result CI не подтверждает native full B2.

| Категория | Старое дерево `82739182` | Разница по Compare | На `39f5c76c` |
|---|---:|---:|---:|
| Markdown в (п) `docs` |127|+5|**132**|
| Все файлы в (п) `docs` |128|+5|**133** (132 MD + 1 JSON)|
| Протоколы `ENGINE001_*PROTOCOL_*.md` |44|+4|**48**|
| Root Stage20 Markdown вне docs |16|0|**16**|
| GitHub workflow YAML |58|+6|**64**|
| Исторические HISTORY/SNAPSHOT Markdown |10|0|**10**|
| Все tree entries |7485|+21|**7506** (получено дельтой, не рекурсивным tree GET)|

Данные проверены по списку путей GitHub Compare, а не по свежему рекурсивному дереву. Объёмы байт не пересчитаны. CI Markdown, native качество и exact CHALK оцениваются отдельно. Исторические файлы не удалялись и frozen evidence не переписывался.

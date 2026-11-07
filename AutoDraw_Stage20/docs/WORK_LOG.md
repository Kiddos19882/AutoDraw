# AutoDraw — журнал выполненных действий

**Назначение:** только фактически выполненные изменения и проверки, а не будущие планы.  
**Полная история до 2026-11-08:** [WORK_LOG_HISTORY_THROUGH_2026-11-08.md](WORK_LOG_HISTORY_THROUGH_2026-11-08.md) — побайтовый исторический снимок прежней редакции.

## 2026-11-08 — FILL-001 / GEOM-001 offline screening A–D

- Проверены remote HEAD `1e0774596c3d`, последние 20 коммитов, docs/README, STATUS, TASKS, ROADMAP, регламенты, FILL/CHALK evidence и исходники существующих FILL-001, interior/outline planners.
- Добавлены (ф) `source/preparation/chalk_fill_strategy_comparison.py` в [`cca2f8f`](https://github.com/Kiddos19882/AutoDraw/commit/cca2f8f3f71747dca59854f409b8d46ed3a544eb) и его tests в [`98615e7`](https://github.com/Kiddos19882/AutoDraw/commit/98615e7f23aaea4d286f1a3adf5f18244a409283). [`6d790cd`](https://github.com/Kiddos19882/AutoDraw/commit/6d790cd72326901e1cda763684d092bb9533cbd8) интегрировал CI-архив, без изменения production defaults.
- Новый FILL-001 A–D offline [CI 42424959123](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123): SUCCESS на workflow SHA `6d790cd`. 3 frozen mask × 4 strategy, 15 диагностических PNG + JSON ([artifact 13595421597](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123/artifacts/13595421597)). Для варианта C coverage rectangle=99.516%, wide=99.593%, narrow=99.381%, leakage=0 в OpenCV. Эффект не подтверждён на реальном PNG. Вариант D использует oracle residual и создаёт слишком много дополнительных штрихов. Все 12 PNG-масок самостоятельно сверены с JSON (coverage/leakage), расхождений нет. Исходный FILL-001 actual PNG остаётся отклонённым.
- CI [CI 42424959123](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123) SUCCESS на `6d790cd` с обязательными jobs. Optional benchmarks и Windows portable build SKIPPED. Новых live runs нет; точный CHALK не измерялся; 81-image benchmark не запускался.
- Frozen masks, raw captures, historical snapshots, master не изменены. Локальный `git status` пользователя не проверялся.

---

## 2026-11-08 — завершена новая документационная система

- Изучен набор 90 исходных Markdown на baseline `a2d1f0a52d47`, выделены текущие источники и полный historical layer.
- Девять прежних редакций сохранены без изменения Git blobs: PROJECT_STATUS, TASKS, ROADMAP, TEST_RESULTS, WORK_LOG, CHANGELOG, DECISIONS, README, AI_WORK_GUIDE. Источник каждого SHA — `HISTORY_SNAPSHOT_PROVENANCE.json`.
- Сокращены действующие управляющие документы; `docs/README.md` охватывает 99/99 Markdown; все старые ссылки восстановлены через aliases. Второй конфликтующий DEC-016 получил DEC-027.
- Реализованы `tools/check_markdown_docs.py`, 5 regression tests и `.github/workflows/docs-integrity.yml`. Первый [CI 42421193210](https://github.com/Kiddos19882/AutoDraw/actions/runs/42421193210) FAILED (1 пропущенная архивная ссылка и 1 некорректный anchor), исправлено. [Повтор 42421451709](https://github.com/Kiddos19882/AutoDraw/actions/runs/42421451709) **SUCCESS**: 99 indexed, 0 broken local links, 0 duplicate DEC IDs, 9 snapshot integrity PASS и 5 unit tests PASS.
- Основной [AutoDraw validation 42420934884](https://github.com/Kiddos19882/AutoDraw/actions/runs/42420934884) SUCCESS на `c7f2e363`. Это не игровой runtime. Raw experiments, frozen INT-006, executor, palette и `master` не менялись; локальный `git status` пользователя не проверялся.

---

## 2026-11-08 — закрытие документационных gate DOC-001—DOC-004

- [CI 42421451709](https://github.com/Kiddos19882/AutoDraw/actions/runs/42421451709) на `d778000e5306` — SUCCESS: 5 unit tests PASS, 99/99 Markdown-файлов проиндексированы, 0 текущих сломанных ссылок, 0 исторических link warnings, 0 конфликтующих ID решений, 0 ошибок целостности исторических снимков.
- Коммит `c6b01cef1c4f7fba680b4000dfc42245c643b89e` закрыл DOC-001—DOC-004 в актуальном реестре задач и обозначил завершённый этап 0 в ROADMAP. Полный последний [CI 42421778987](https://github.com/Kiddos19882/AutoDraw/actions/runs/42421778987) на этом commit — SUCCESS.
- Контроль Markdown ограничен структурой ссылок, каталогом, решением коллизий и provenance snapshots: поле audit `external_ci_results_verified=false` означает, что внешние CI-ссылки проверены отдельно по GitHub Actions, а не самим скриптом. Ни live drawing, ни CHALK measurements здесь не проводились.

## 2026-11-08 — реорганизация документации, этап 1

- Проверены feature HEAD `a2d1f0a52d47`, последние 20 коммитов, 90 Markdown-файлов, текущие регламенты, активные управляющие документы и CHALK/renderer/fill результаты.
- Подтверждён основной CI [42417067391](https://github.com/Kiddos19882/AutoDraw/actions/runs/42417067391) SUCCESS на `5a55e9f`; ранее записанные `PENDING` теперь являются историей времени записи.
- [PROJECT_STATUS](PROJECT_STATUS.md), [TASKS](TASKS.md), [ROADMAP](ROADMAP.md) сведены к краткому текущему состоянию, открытым задачам и зависимостям; **полный прежний текст каждого перенесён в отдельный snapshot с тем же Git blob SHA**.
- Завершена аналогичная консолидация [TEST_RESULTS](TEST_RESULTS.md), WORK_LOG и CHANGELOG; сохранены raw evidence и все исторические CI failures.
- Код приложения, frozen CHALK model, palette, executor, experimental data и `master` не менялись. Local `git status` и новая игровая сессия не проверялись.

**Актуальные задачи:** [TASKS](TASKS.md). **Значимые изменения:** [CHANGELOG](CHANGELOG.md). **Подробная история:** [WORK_LOG_HISTORY_THROUGH_2026-11-08.md](WORK_LOG_HISTORY_THROUGH_2026-11-08.md).

# AutoDraw — журнал выполненных действий

**Назначение:** только фактически выполненные изменения и проверки, а не будущие планы.  
**Полная история до 2026-11-08:** [WORK_LOG_HISTORY_THROUGH_2026-11-08.md](WORK_LOG_HISTORY_THROUGH_2026-11-08.md) — побайтовый исторический снимок прежней редакции.

## 2026-11-08 — ENGINE-001: прямой аудит полного main bundle и состояния BoardPane

- Сверены remote HEAD `90d1944`, 20 коммитов и Markdown Actions. С помощью GitHub blob API успешно прочитан `main.min_653f95bc.js` полностью (4 857 523 символа / 4 859 418 байт), вычисленный Git SHA-1 совпал с `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`. Ограничение обычного `fetch_file` на большой текст преодолено.
- Непосредственно изучены `BlackBoardAtom` и структура его слотов/сериализации, `BoardPane` события/quota/undo/clear/redraw, `Painter`, `PainterPopup` UI/save, `net.Atom`, Egret `GraphicsNode/CanvasRenderer/WebGLRenderer`. Накопление путей через `redraw(false)`, float32 serialization и условный случай несогласованной длины массивов задокументированы как E1 / проверяемые риски, без объявления живого бага.
- Дополнен **существующий** [системный справочник](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md); новый E1 результат сопоставлен с текущей задачей и отложенным Egret replay в ROADMAP. Новых E2/E4 тестов не выполнялось; старые PRR PASS и FILL-001 PNG FAIL не менялись.
- Документальный инкремент: код, tests, gameEngine blobs, Stage6, CHALK estimator, frozen captures, master не менялись. Markdown CI проверяется после коммита.

---

## 2026-11-08 — ENGINE-001: чтение движка и консервация следующей программы тестов

- Повторно проверены remote HEAD `768ece83f129`, 20 коммитов и Actions, README/STATUS/TASKS/ROADMAP/AI guide, DECISIONS/invariants/evidence, инженерный разбор Egret, Monitor и точные FILL/PRR результаты.
- Проверены `gameEngine/manifest.json` и непосредственные ключевые методы `mergeEngine_df2e5bc5.js` (roundRect radius calculation, GraphicsNode line caps, CanvasRenderer path/stroke, WebTouchHandler.getLocation, SystemTicker); повторный полный `main.min` в текущем text connector невозможен, его BoardPane/Painter путь проверен по ранее зафиксированному анализу того же Git blob и существующему actual-BoardPane harness.
- Создан [единый технический обзор движка и доски](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md) с уровнем подтверждения для каждого звена, таблицей координат, CHALK, лимитами, методами smooth/normal, render/clip и списком неизвестного. Это документационная систематизация, **не новый runtime эксперимент**.
- Зафиксированы ранее выполненные A–D/PRR/RS тесты, предполагаемые E1–E4 и будущий multi-stroke replay на **существующем** Egret harness в [ROADMAP](ROADMAP.md#отложенная-программа-тестов-fill-001-geom-001-и-связанных-gates); задача FILL-001 остаётся открытой, но отложенной. Новый ENGINE-001 отмечен как P0.
- Не менялись gameplay source, gameEngine bundles, unit tests, workflow, frozen masks, capture PNG, CHALK estimator, Stage6 executor и master. Документационный CI проверять отдельно на итоговом commit.

---

## 2026-11-08 — FILL-001 actual screen-ROI contour counterfactual

- Повторно проверены remote HEAD `57815f6f5a26`, 20 последних коммитов и доступные Actions, текущие README/STATUS/TASKS/ROADMAP/AI guide, FILL-001 primary live report, PNG capture adapter, pinned plan, frozen masks и A–D модель. Работа продолжила FILL-001, не меняла Stage6/production.
- Новый (ф) `source/preparation/chalk_fill_screen_residual_comparison.py`: [`ae86544`](https://github.com/Kiddos19882/AutoDraw/commit/ae865444014008adfdd8ecb42e2286ebcfd90598). Tests [`a7cc557`](https://github.com/Kiddos19882/AutoDraw/commit/a7cc557e3a112ce5c8ebec3972fed7d3e204bb51), CI workflow [`c2ae5a0`](https://github.com/Kiddos19882/AutoDraw/commit/c2ae5a0ffdabb506843e4d25f2cff28e5c444e20). No original capture edits.
- Первичный [CI 42427122693](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427122693) FAILED: 8 новых тестов отклоняли Windows CRLF checkout (attempt SHA-256 `2e144c2f…` вместо Git LF canonical `79a42cf…`; файл/исторический blob неизменён). Исправление [`1b39e8d`](https://github.com/Kiddos19882/AutoDraw/commit/1b39e8d8d97362ece19040fa3170ec0119cd663d) и newline regression [`16f0e1b`](https://github.com/Kiddos19882/AutoDraw/commit/16f0e1b6cce0959571adec1f03cc38aeb48277f6). PNG exact-byte hashes не ослаблены.
- [CI 42427514794](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794): SUCCESS; 952 preparation tests PASS; все mandatory jobs PASS, optional algorithm benchmarks и Windows portable build SKIPPED. [artifact 13596093007](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794/artifacts/13596093007), ZIP SHA-256 `19313debbcc350f0eeda3edf2cba9e65350690a850d5bb2d9d733bb03794d620`, 6 PNG и JSON. Внешняя независимая сверка цветовых diagnostic overlays с JSON: all nominal recovered/leakage counts match.
- [CI 42427514794](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794) SUCCESS (`16f0e1b`), [artifact 13596093007](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794/artifacts/13596093007). Actual ROI target 71110 screen px: 1116 uncovered, 11 leaked. Hypothetical contour inset6 recovers 734, leaves 382, would yield 99.462804% coverage with 0 NEW model leakage, but existing 11 leakage remain, so this is not a game PASS. Inset5 recovers1092 but +60 new leakage; inset7/8 recover335/157; ±1 screen-pixel dilation at inset6 adds89 new modeled leaks. Baseline B prediction of 416 misses diverges from actual1116 (model-only738), причина физического renderer mismatch UNKNOWN.
- Старый capture по-прежнему REJECTED: exact CHALK=1260 только предыдущего run; new exact CHALK=NOT_RUN; новой live игры и 81-image comparison не было. Executor defaults, frozen models, raw PNG, history и master не тронуты; локальный ПК статус неизвестен.

---

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

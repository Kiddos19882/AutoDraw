# AutoDraw — значимые изменения

Записывать только изменения интерфейсов, форматов, возможностей и значимые изменения сопровождения. Ход проверки каждой задачи — [WORK_LOG](WORK_LOG.md). Полная прежняя редакция без изменений: [CHANGELOG_HISTORY_THROUGH_2026-11-08.md](CHANGELOG_HISTORY_THROUGH_2026-11-08.md).

## 2026-11-08 — ENGINE-001: controlled stationary duplicate frames in native BoardPane

- Исследовательский opt-in `?frames=fill001`: 0/1/3 rejected-point `ENTER_FRAME` simulations per stroke, same frozen 27/1260, six Canvas2D/WebGL PNG, Python independent threshold audit. [Full CI 42440876068](https://github.com/Kiddos19882/AutoDraw/actions/runs/42440876068) SUCCESS at `a35d782`, 0 final RGBA differences in each backend.
- Negative path-count gate [42440726798](https://github.com/Kiddos19882/AutoDraw/actions/runs/42440726798) exposed next-stroke `redraw(full)` clearing old paths; corrected expected counts 70/71/73 rather than 70/97/151. Production unaffected, live quality and CHALK untested.

## 2026-11-08 — ENGINE-001: native 5px contour across endpoint variants

- Исследовательский opt-in `?outline=fill001` в существующем Egret browser harness добавляет одинаковый замкнутый 5 logical px contour из pinned rectangle mask ко всем трём endpoint режимам; 15 дополнительных native PNG, независимый OpenCV audit с four-alpha metrics и CI artifacts. [Full CI 42439343897](https://github.com/Kiddos19882/AutoDraw/actions/runs/42439343897) SUCCESS (`f381ffe`).
- После добавления обводки board-local coverage улучшилась, но новый modeled leakage >0 и zero right-middle recovery в smooth. Исторический live capture остаётся FAIL; production code/game bundle, executor и estimator не менялись.

## 2026-11-08 — ENGINE-001: native Painter endpoint reference

- Добавлен opt-in `?endpoint=fill001` в существующий browser harness, 15 PNG (27-stroke aggregate и три изолированных штриха, game-smooth / native forced-last / normal), independent board-local OpenCV raster analysis в [validation CI 42438036187](https://github.com/Kiddos19882/AutoDraw/actions/runs/42438036187) **SUCCESS** на `1805ebf`.
- Экспериментальные методы не затрагивают production и историю. Исправлен диагностический учёт пустого atom slot после первого Egret job FAIL. Same-run screen calibration/live PNG остается отдельным открытым gate.

## 2026-11-08 — ENGINE-001 accepted-only Egret temporal reference

- Добавлен opt-in исследовательский режим `?temporal=fill001` **в существующий** `tests/game_renderer_reference.js`: actual `BoardPane` one-pass / incremental redraw, 27 run-bound strokes/1260 accepted points, строгая входная валидация, 4 Canvas2D/WebGL PNG, manifest. Production и прежние 20 renderer fixtures не изменены.
- [CI 42434968046](https://github.com/Kiddos19882/AutoDraw/actions/runs/42434968046) browser job SUCCESS на `8d5d088`: 0 difference между двумя итоговыми растрами и 70 vs 29 накопленных Graphics paths. Данные исторические; exact live CHALK новых алгоритмов не измерялся, full temporal/screen equivalence не доказаны.

---

## 2026-11-08 — подтверждённая граница источников ENGINE-001

- [Архитектура доски](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md#14-финальная-сверка-источников-game-monitorbridge-prr-и-runtime-2026-11-08) дополнена сравнением Egret E1, Monitor/Bridge, PRR 6/6 E3 и snapshot E4; устранено ошибочное утверждение, будто старый JSON содержал вычисленные `boardClientCorners`.
- Уточнены пределы PRR PASS по ранее установленной DEC-025 (≥0.92) и отделены от pixel identity и FILL-001 качества. Новых исходников, экспериментальных данных или runtime проверок нет.

---

## 2026-11-08 — полная статическая цепочка input/frame/Canvas/WebGL для доски

- [GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md), §13: документирована desktop/mobile доставка pointer событий, фактический `mouse.enable` hook, порядок `SystemTicker.render → ENTER_FRAME`, матрицы `globalToLocal`, Canvas2D raster внутри WebGL, offscreen `destination-in` mask, scrollRect clipping и stage/backing/CSS преобразования.
- `ENGINE-001` остаётся PARTIAL до финальной сверки с Monitor/PRR; новые тесты, изменения приложения и runtime запуск не выполнялись.

---

## 2026-11-08 — прямой разбор BoardPane из byte-verified main bundle

- [Справочник игровой доски](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md) расширен исходными методами `BlackBoardAtom/BoardPane/Painter/PainterPopup`, таблицей состояний и бинарного `Atom`, различием `redraw()`/`redraw(false)`, границами one-pass Egret replay.
- Это E1 документирование, не изменение кода и не доказательство нового live-рисунка; план future tests обновлён без запуска.

---

## 2026-11-08 — документация игровой доски и перенос тестов в будущий план

- Добавлен [GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md): сопоставленная архитектура Egret/BoardPane, детали input sampling/CHALK/normal-smooth path/Canvas-WebGL/маски/координатные пространства и пределы доказательств.
- [ENGINE-001](TASKS.md) назначен текущим P0; реализованные A–D/PRR/RS и предложенные E1–E4, Egret multi-stroke replay зафиксированы [в ROADMAP](ROADMAP.md#отложенная-программа-тестов-fill-001-geom-001-и-связанных-gates) как будущие, без запусков и без изменения прежних результатов.
- Production code, original evidence и master не изменены.

---

## 2026-11-08 — сохранённый game PNG против модельной контурной коррекции

- Добавлен изолированный (ф) `source/preparation/chalk_fill_screen_residual_comparison.py` с pinning actual evidence SHA, идентичным capture-audit screen transform, counterfactual overlays offset5–8, baseline-model discrepancy и ±1px sensitivity. Добавлены tests и CI artifact; никакой executor integration.
- [CI 42427514794](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794) SUCCESS на `16f0e1b`, [artifact 13596093007](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794/artifacts/13596093007). Первый [CI 42427122693](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427122693) FAILED из-за LF/CRLF JSON checkout, исправлен через канонический SHA только JSON без ослабления проверки PNG; сохранён в WORK_LOG.
- Actual live FILL-001 quality FAIL не изменён; contour model и sampling proxy не являются измеренным CHALK.

---

## 2026-11-08 — экспериментальный анализ FILL-001 A–D

- Изолированный (ф) `source/preparation/chalk_fill_strategy_comparison.py`: плотные/редкие scanline, связный contour, модельная oracle-коррекция residual; reuse frozen FILL masks и current OpenCV painter; **not executor ready**.
- Unit tests и GitHub Actions выгрузка 15 PNG/JSON. [CI 42424959123](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123) SUCCESS, [artifact 13595421597](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123/artifacts/13595421597). CHALK estimator, Stage6 и production settings не изменены.

---

## 2026-11-08 — проверяемый актуальный слой и сохранённая история

- `docs/README.md` — полная навигация по 99 Markdown; текущие `PROJECT_STATUS/TASKS/ROADMAP/TEST_RESULTS` отделены от истории; архивы девяти старых редакций имеют проверяемые SHA-1 Git blob.
- Второе решение `DEC-016` перенумеровано в `DEC-027` с traceable mapping; методология в `AI_WORK_GUIDE` ускоряет выбор профильных источников.
- Введён Markdown integrity workflow и 5 unit tests: [CI 42421451709](https://github.com/Kiddos19882/AutoDraw/actions/runs/42421451709) SUCCESS; ноль найденных нарушений локальных ссылок, индексирования и уникальности решений. Внешние GitHub URLs, runtime и semantic correctness этот CI не проверяет.
- Исходный код приложения, CHALK predictor и первичные экспериментальные файлы не изменялись.

---

## 2026-11-08 — документация: быстрый актуальный контекст

- Текущие [PROJECT_STATUS](PROJECT_STATUS.md), [TASKS](TASKS.md), [ROADMAP](ROADMAP.md) отделены от полной исторической записи: исторические версии сохранены Git blob-for-blob.
- [TEST_RESULTS](TEST_RESULTS.md) преобразован в реестр доказательств G1–G3, INT-006/R, FILL-001-RS, renderer/PRR и 81-image offline corpus; сохранены все прежние подробные измерения.
- Не изменены форматы .autodraw, исходники algorithms/executor, Game Monitor, CHALK profiles, пользовательские данные или production settings.

## 2026-11-08 — последние подтверждённые функциональные изменения до документационной реорганизации

- В `screen_candidate_corpus.py` и tests добавлена проверка source images/geometry/color source summaries для 81 plans; [offline CI 42417067363](https://github.com/Kiddos19882/AutoDraw/actions/runs/42417067363) SUCCESS на `5a55e9f`.
- [AutoDraw validation 42417067391](https://github.com/Kiddos19882/AutoDraw/actions/runs/42417067391) SUCCESS на `5a55e9f`. Успех автоматических проверок не подтверждает live CHALK или FILL-001 PNG PASS.

Все предыдущие даты, тесты, неудачные прогоны и SHA доступны в [истории CHANGELOG](CHANGELOG_HISTORY_THROUGH_2026-11-08.md).

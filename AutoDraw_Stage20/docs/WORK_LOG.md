# AutoDraw — журнал выполненных действий

**Назначение:** только фактически выполненные изменения и проверки, а не будущие планы.  
**Полная история до 2026-11-08:** [WORK_LOG_HISTORY_THROUGH_2026-11-08.md](WORK_LOG_HISTORY_THROUGH_2026-11-08.md) — побайтовый исторический снимок прежней редакции.

## 2026-11-08 — FILL-001: preparation of one full-telemetry comparison run (no Windows live)

- Повторно проверены remote HEAD `8566242` и последние 20 commits, Actions, FILL-001 original evidence и актуальные FILL/ENGINE docs. Цель: новый **одиночный**, полностью run-bound E4 baseline на том же frozen рисунке 27 stroke / r10 / step5 / offset0 без перезаписи old FILL001 run.
- Реально разработано на feature branch: `8960186` исправил binder для строгой совместимости Monitor 0.2.1/0.2.4; `345507f` — capture adapter + негативные/позитивные contract tests; `4437716` — независимый E4 same-run diagnostic `FILL001_MONITOR_SAME_RUN_V1`; `66f94d0` — opt-in UI и full-screen PNG/ROI той же ImageGrab frame; `ea7b138` — exact budget floor 1600, позитивный 27-stroke synthetic audit; `77dc481` — автоматическая генерация FILL001_RS_V1 manifest из диагностического флага; `b98d9e0` — предупреждение о персональных данных full-screen PNG, idempotent raw diagnostic и regression RS series selection.
- Базовые условия: одно явно выбранное исполнение, 45-cell batch запрещён; Monitor raw 0.2.4, Egret actual ENTER_FRAME (не графический render), `smooth=true`, exact CHALK только по run-bound pointCount, full-screen/ROI before/after, SHA and failures. Браузерные/десктоп координаты не отождествлять без независимой E5 проверки; цвета, clipping, alpha и временной render order не объявляются валидированными.
- [Предыдущий полный CI 42458319429](https://github.com/Kiddos19882/AutoDraw/actions/runs/42458319429) SUCCESS на `77dc4813`, [финальный CI 42458832846](https://github.com/Kiddos19882/AutoDraw/actions/runs/42458832846) **SUCCESS** на `b98d9e0`: все обязательные jobs, 995 Preparation/G3 tests и 82 subtests PASS; optional benchmark и Windows portable build SKIPPED. Реальный Windows запуск NOT_RUN, независимая old↔new E5 validation NOT_RUN; Windows portable build на push SKIPPED. Никакого нового фактического CHALK и live coverage нет, старый capture остаётся FAIL.
- Не изменены frozen план, маски, originals, Stage6 executor, CHALK estimator/defaults, `master`, исторические snapshots. Для публикации full-screen PNG потребуется предварительный просмотр на личные данные.

## 2026-11-08 — FILL-001: run-bound perimeter strip audit, immutable RGB evidence

- Проверены feature remote HEAD `8719686d`, последние 20 commits и текущие Actions, контролирующая документация и original FILL001 pinned evidence. Цель — E2/E3 локализация дефекта, а не изменение game production или запуск новых live tasks.
- Сравнены 27 фактически принятых штрихов (run `6a17a297-ea14-4527-9527-bfd8de3bd335`, точный CHALK1260, 1260 accepted points) и frozen 27-stroke plan: accepted last X в пределах 4.208–5.208 logical px правее планового конца, а `smooth` terminal на midpoint последней пары. Ни прямое недоведение мыши, ни конкретная причина правого screen gap не доказаны.
- Добавлен **отдельный versioned diagnostic** `FILL001_RIGHT_EDGE_SPATIAL_V1.json` к существующему `chalk_fill_screen_residual_comparison.py`, не заменяя прежние artifacts и не правя frozen captures. Pinned existing RGB overlay пересчитан: 1116 misses, 11 leakage, 499 right /134 left, **114/114 middle rows** имеют contiguous right gap 3–7 screen px (median4), left median1. Отчёт проверяет SHA Git blob derivative + исходную Monitor run identity, старый exact CHALK и `smooth` endpoint geometry, сохраняет 114 rows и 27 stroke endpoints. [Artifact 13607454421](https://github.com/Kiddos19882/AutoDraw/actions/runs/42456241289/artifacts/13607454421) проверен по ZIP CRC и разобран независимо. Original screen-residual JSON и 6 PNG остались доступны.
- [Первый CI 42456007010](https://github.com/Kiddos19882/AutoDraw/actions/runs/42456007010) **FAIL**: одна отрицательная regression ожидала Git SHA mismatch на Windows CRLF, но корректный fail-closed валидатор раньше отклонил смешанные CRLF/LF; 976 tests passed, 1 failed. Test-only исправление `c4fefe6` использует тот же newline style при порче fixture. [Повторный CI 42456241289](https://github.com/Kiddos19882/AutoDraw/actions/runs/42456241289) — Preparation/G3 **977 passed**, 82 subtests passed; статусы остальных CI jobs проверяются отдельно. Никакой результат FILL001 quality в PASS не изменялся.
- Изменены только (ф) `source/preparation/chalk_fill_screen_residual_comparison.py`, (ф) `source/preparation/tests/test_chalk_fill_screen_residual_comparison.py` и нужные текущие документы. Stage6, master, raw/archived evidence, production CHALK estimator и acceptance thresholds не изменялись. Следующая проверка: причинно разделить 11 leakage и 738 model-only pixels, не переносить чужой Stage transform на старый FILL001 run.

## 2026-11-08 — ENGINE-001: native Stage WebGL ↔ live PNG E5 (9/9 accepted screen RGB)

- Повторно проверены remote HEAD `2ab5180`, последние 20 commits, diff и доступные Actions; выполнена research-разработка только в ветке `feature/image-geometry-optimization`. Коммиты: `c20a353` (native `accepted_points` + DRAW_SAMPLE parity), `90fdc59` (ENGINE-001 provenance/acceptance), `b1256f9` (9-ячейковый Firefox Stage A-D runner), `ea0167b` (самостоятельный E5 comparator), `0a14f31` (CI), `6810f75` (обязательные bbox metrics и regression).
- В 9 raw runs `1771653` проверено 9/9 точных accepted streams с равным числом положительных `DRAW_SAMPLE`; event schema содержит не `POINT_QUOTA_UPDATE`, а `DRAW_SAMPLE` и `accepted_points`. Отдельные run/session, unchanged renderer geometry, observed `smooth=true` и точный CHALK 846 сохранены.
- Первичный [E5 CI 42453831682](https://github.com/Kiddos19882/AutoDraw/actions/runs/42453831682) SUCCESS как исполнение, 9/9 `REJECTED_PER_RUN` из-за отсутствующих bbox в `compare_stage_renderer_reference.mask_metrics`; raw reports не удалены и gate не ослаблялся. Исправлено только формирование bbox (`6810f75`).
- Повторный [E5 CI 42454224181](https://github.com/Kiddos19882/AutoDraw/actions/runs/42454224181) SUCCESS на `6810f75dfb87c8eaac7e73eb9d1063291660c104`: 9/9 `PASS_PER_RUN`, accepted=9, rejected=0, blocked=0, 18 Node PASS и 24 Python capture acceptance PASS; artifacts [native A-D](https://github.com/Kiddos19882/AutoDraw/actions/runs/42454224181/artifacts/13606972733) / [screen metrics](https://github.com/Kiddos19882/AutoDraw/actions/runs/42454224181/artifacts/13607535199), source journal SHA-256 `fd8270b38e0f14a297cc62405837ff825537e0b0ecb3765d1c671eed0aa007fa`. Independent ZIP integrity check: 2384 entries, testzip без ошибок. В варианте A IoU H 0.998995–0.999281, V 0.940241–0.940694, D 0.981740–0.983277. Вся проверка offline по ранее сохранённым live RGB, новый игровой CHALK не расходуется.
- Scope: software ANGLE (Microsoft Basic Render Driver) в Firefox CI, а не GPU live-пользователя; binary native alpha live PNG отсутствует, intermediate render order и отдельный `normal` live control не установлены. FILL-001 остается FAIL. Production/Stage6/CHALK estimator, historical evidence и `master` не менялись.

## 2026-11-08 — ENGINE-001: актуализация E4 и начальная независимая E5-сверка по 9 raw runs

- Проверены feature HEAD `177165361b0340515fe3bb74f4847ab3ec579ebc`, последние 20 коммитов и Actions. Исправление heartbeat `7b129c2` — [CI 42448779447](https://github.com/Kiddos19882/AutoDraw/actions/runs/42448779447) SUCCESS; новый run baseline `1771653` — [full CI 42449898657](https://github.com/Kiddos19882/AutoDraw/actions/runs/42449898657) SUCCESS, required jobs PASS, optional benchmarks/portable Windows build SKIPPED.
- Из commit `1771653` прочитаны 9 per-run monitor reports, experiment manifests, engine001 audit JSON, journal, session renderer geometry; проверены 9/9 completed, 9/9 `PASS_E4_RAW_CAPTURE`, exact CHALK=846 (324/181/341), 861 Egret frame samples, нулевые telemetry errors/loss, один session, девять различных runs. Два старых `lab_bridge_gate` interrupted/stopped блока сохранены отдельно.
- Независимо пересчитана геометрия по **1641** raw `MOUSE_MOVE_SAMPLE`: client→screen offset (0,163) px для всех 9; 6 X+6 Y отдельных least-squares fits, max absolute residual **0.749 px** (round to 0.001), fitted-origin ↔ inspect-corner difference ≤0.077 px X / ≤0.063 px Y. Для constant axis нет независимой оценки из траектории. Следом выполнен независимый **screen-only** RGB PNG diagnostic на тех же девяти after-досках и общем before: zlib Adler-32 check, 9/9 точных совпадений с исходными `changed_pixel_count`, во всех 9 по 17 лишних changed pixels на `y=354` вне accepted-endpoint diagnostic ROI, sensitivity `maxRGB<64/128/200`, записаны oriented stroke bounds в §21. **Native Egret render-vs-live-mask E5 NOT_RUN**: отсутствует независимо воспроизведённая native reference mask и frozen acceptance для этого сравнения; `changed_bounds_roi` захватывает постороннюю дельту у нижней кромки. **E5 PARTIAL / ENGINE-001 PARTIAL**, не объявлять качества FILL-001 доказанными.
- Синхронизированы только текущие документы `PROJECT_STATUS`, `TASKS`, `ROADMAP`, `TEST_RESULTS`, `GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE`, `WORK_LOG`, `CHANGELOG`. Ранее сохранённые raw captures, `HISTORY` snapshots, production estimator/Stage6 executor не изменялись.
- Повторная handoff-сверка на remote HEAD `bda2a6e` показала, что факты E4/E5 уже были записаны в `PROJECT_STATUS`, `TASKS`, `TEST_RESULTS` и §21. Исправлена устаревшая навигационная ссылка в `docs/README.md`, в §21 добавлена сводная таблица всех 9 live run IDs и 3 порогов диагностической RGB-маски. Это документирование уже выполненного анализа, **без новых E5 native-проверок**, изменения baseline, runtime и production. Локальные Windows/gameplay тесты не запускались; документный CI проверяется по SHA нового коммита.

## 2026-11-08 — ENGINE-001: офлайн-сравнение накопленных StrokePath на сохранённом FILL-001 run

- HEAD до изменений `ca0c768b`: remote и последние 20 commits проверены, разрешение получено на исследовательскую разработку и offline-проверки; live gameplay, production и frozen evidence не изменялись.
- Новый opt-in `?temporal=fill001` в существующем `tests/game_renderer_reference.js`, code commit `79b33e2`; прицельные fail-closed Node tests и CI PNG/JSON export в commit `8d5d088`.
- Source Game Monitor run Git blob `8eb04ad7331d1e56f4aeb7d0f625c59c1dc57c24`, run `6a17a297`, 27 strokes / 1260 accepted points / historical CHALK=1260. Из-за отсутствия per-frame duplicate redraw trace воспроизведён только accepted-only minimum; `smooth` — исследовательское предположение, screen mapping UNCALIBRATED.
- Full validation CI 42434968046 completed **SUCCESS** на `8d5d088`: preparation 952 passed, Egret/Monitor/Bridge/executor/integration/INT-006 PNG jobs SUCCESS, optional algorithm benchmarks/Windows build SKIPPED. Это E3, не E4.
- [Browser CI 42434968046](https://github.com/Kiddos19882/AutoDraw/actions/runs/42434968046) на `8d5d088` успешно сгенерировал [artifact 13599086458](https://github.com/Kiddos19882/AutoDraw/actions/runs/42434968046/artifacts/13599086458): 4 PNG и manifest. 29 one-pass vs 70 incremental Graphics paths, 1 vs 27 full redraw, 0 vs 1260 incremental redraw; Canvas2D и WebGL финальные пиксели совпали (0 RGBA difference). Canvas2D↔WebGL внутри каждого варианта имеет 243 различающихся пикселя с max channel delta=1.
- Независимый PNG audit на скачанном ZIP (SHA-256 `0aede096b0e28e6a7d18e83e71dfc576310b36b2bcedb30a8136d1f971a76fde`) повторил нулевую разницу; все четыре изображения непустые (406282 alpha-positive pixels).
- Отрицательный результат гипотезы о final pixel effect **сохранён**, а не интерпретирован как универсальный pixel-perfect game. Не покрыты extra `ENTER_FRAME` без новой точки, промежуточный renderer update, другой GPU, desktop transform, реальный FILL-001 PNG. Исторические 98.430600%/11 leakage остаются FAIL, INT-007 BLOCKED.

---

## 2026-11-08 — ENGINE-001: сверка API Monitor/Bridge, PRR, snapshot и исправление доказательности

- Повторно проверены remote HEAD `22649900ffdc`, последние 20 коммитов, доступные Actions и действующие README/STATUS/TASKS/ROADMAP/AI guide; использованы профильные архитектура, Monitor API, DEC-025, analyzer и первичные PRR/runtime records.
- Сопоставлены статическая input→frame→renderer цепочка E1 с Monitor event semantics и точным CHALK шести PRR runs. Подтверждён формальный PRR E3 PASS 6/6 на CI 42321009715 при действующем IoU/precision/recall ≥0.92; это не pixel identity и не FILL-001 acceptance.
- Найдено противоречие §13.6 первичному JSON 04.11: `boardClientCorners=null`, хотя текст ранее приписывал snapshot рассчитанные fallback corners. Исправлена граница доказательства; stage/client/desktop не смешаны. Новая матрица E1/E3/older E4 и UNKNOWN внесена в [§14](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md#14-финальная-сверка-источников-game-monitorbridge-prr-и-runtime-2026-11-08).
- Код, тесты, production, frozen captures и `master` не изменены. Новых live/offline pixel tests, CHALK замеров или ручного CI запуска не проводилось; `ENGINE-001 PARTIAL` сохранён для будущей независимой validation.

---

## 2026-11-08 — ENGINE-001: прямая сквозная трассировка ввода и WebGL-доски

- На удалённом HEAD `570f9a6` повторно проверены последние 20 коммитов и GitHub Actions; открытая задача — `ENGINE-001`, предыдущие геометрические тесты остаются DEFERRED.
- По byte-identified `main.min_653f95bc.js` и `mergeEngine_df2e5bc5.js` прослежены `WebTouchHandler.getLocation` → `TouchHandler` с desktop `mouse.enable` wrappers → `Preloader.initStage` → `BoardPane.globalToLocal/onDrawing`; `SystemTicker.update` выполняет render **перед** `broadcastEnterFrame`.
- Установлен конкретный WebGL путь `GraphicsNode → CanvasRenderBuffer/CanvasRenderer → WebGL texture → drawWithClip` (offscreen `destination-in` для rounded board mask, отдельный `scrollRect`), а также формулы stage/display/backing/CSS масштаба. Это E1 по frozen engine, не E4 pixel parity.
- Дополнен [единый справочник](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md), §13, и уточнены статус и задача. Новых live, unit, screenshot экспериментов не запускалось; CHALK, PRR и FILL-001 результаты неизменны. `master`, исходники, frozen captures и workflows не изменены. Markdown CI проверить после docs commit.

---

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

## 2026-11-08 — ENGINE-001, анализ различных окончаний горизонтальных штрихов

- На remote HEAD `8ce14223d46a` сопоставлены frozen FILL-001 plan (27 строк), raw Game Monitor accepted points и executor/Egret; 19 внутренних строк имеют одинаковую plan X-геометрию и first/last accepted X.
- Различная предпоследняя X даёт три разных конца `smooth` Graphics path, разброс 3 logical px. E1 + арифметическая сверка старых E4 данных; причина 499 правых missed screen pixels пока UNKNOWN/NOT_PROVEN. Новый live game test или E2 не запускался.
- Обновлены только архитектура, статус, открытая задача и журнал; frozen files, приложение, production и master не менялись.

## 2026-11-08 — native Egret endpoint comparison, ENGINE-001 / FILL-001

- Code/test baseline `94459935`; новые исследовательские изменения: `66c8038` (game renderer endpoint), `0dc09da` (PS1 CI), `8d5f61b` (independent analyzer), `169a6d5` (workflow), `1805ebf` (исключение пустого atom slot). Изменены только tests и CI, не production / frozen data / master.
- Негативный browser attempt: [CI 42437858048](https://github.com/Kiddos19882/AutoDraw/actions/runs/42437858048), Egret job FAIL из-за пустого atom slot при подсчёте native Painter calls. История сохранена, ошибка исправлена.
- Полный [CI 42438036187](https://github.com/Kiddos19882/AutoDraw/actions/runs/42438036187) на `1805ebf` **SUCCESS**. Native masked Canvas2D/WebGL 15 PNG/manifest [artifact 13599599617](https://github.com/Kiddos19882/AutoDraw/actions/runs/42438036187/artifacts/13599599617), независимый board-local OpenCV JSON +3 overlays [artifact 13600208683](https://github.com/Kiddos19882/AutoDraw/actions/runs/42438036187/artifacts/13600208683); отдельная независимая PIL/NumPy проверка 15 PNG подтверждает +2936/0 backing pixels и native forced-vs-normal equality по alpha≥128.
- Same-run screen transform отсутствует: оригинальный FILL-001 остаётся FAIL 98.430600% / 11 leakage. Новый E4/live NOT_RUN. Следующий шаг в TASKS не закрыт.


## 2026-11-08 — ENGINE-001: дополнительный native contour 5px на трёх endpoint режимах

- Ветка `feature/image-geometry-optimization`, исходный HEAD `78d45d79`, последние 20 commits и GitHub Actions проверены. Использован существующий `game_renderer_reference.js`, `run_egret_renderer_reference.ps1`, независимый Python OpenCV analyzer и существующий workflow. Отдельный experiment `ENGINE001_NATIVE_ENDPOINT_OUTLINE5_V1` и независимый `ENGINE001_NATIVE_ENDPOINT_OUTLINE5_OPENCV_V1`.
- Экспериментальная обводка: один замкнутый 5 logical px `Painter normal` pass по контуру frozen rectangle после 3 logical px erosion, 64 вершины + closure, добавлен одинаково к трём режимам; сохранены исходные 27 strokes/1260 accepted samples. Исходные frozen маски, plan, monitor run, renderer engine bundle, baseline original 15 PNG и пороги не изменены.
- Commit sequence code/CI: `7a6d372`, `f4c619c`, `e381798`, `6477169`, `32c190d`, `f381ffe`. [Full CI 42439343897](https://github.com/Kiddos19882/AutoDraw/actions/runs/42439343897) **SUCCESS** на `f381ffe4817b64800a15292a7ed54603f5eeabe8`, обязательные Egret, Monitor, executor, Preparation, integration, INT-006 PNG jobs PASS; optional benchmarks и Windows build SKIPPED.
- Evidence: [native 30 PNG+2 manifest](https://github.com/Kiddos19882/AutoDraw/actions/runs/42439343897/artifacts/13600612786), [independent OpenCV JSON +3 overlays](https://github.com/Kiddos19882/AutoDraw/actions/runs/42439343897/artifacts/13601121751). CI PNG пересчитаны независимо из ZIP: game smooth board-local target alpha128 coverage 98.7499→99.6240%, forced/normal 98.8427→99.6743%, 0 removed pixels, +31 modeled outside-target px каждого; game-smooth right-middle missing 55→55, zero recovered, contrast 499 screen misses реального archive.
- Качество live FILL-001 не менялось: 98.430600%/11 leakage FAIL и exact historical CHALK=1260. Дополнительный контур не выполнялся в игре, CHALK NOT_RUN; screen geometry UNCALIBRATED. Следующая E4 same-run задача не закрыта. Production, Stage6 executor, estimator, frozen evidence и `master` не менялись.


## 2026-11-08 — ENGINE-001: стационарные кадры и очистка накопленных путей

- Baseline remote `231288aa` сверён, прочитаны актуальные README/PROJECT_STATUS/TASKS/ROADMAP/AI_WORK_GUIDE, ENGINE-001 архитектура и исходники harness; последние 20 commits и Actions проверены. Деятельность ограничена исследовательскими tests/CI, offline Egret и минимальным документированием; live gameplay, `master`, production, frozen captures не менялись.
- Исследовательская разработка: `4c948e8` (`?frames=fill001`: 0/1/3 stationary pointer repeats per stroke, `BlackBoardAtom.pushPoint` rejected, `redraw(false)`), `8148368` (headless Edge PNG + independent Python audit), `4982b11` (диагностические counters после первого gate failure), `a35d782` (уточнение path-count expectation из реального BoardPane). Версионированные experiment IDs `ENGINE001_DUPLICATE_FRAMES_V1` и `ENGINE001_DUPLICATE_FRAMES_INDEPENDENT_PNG_V1`.
- Отрицательный этап [CI 42440726798](https://github.com/Kiddos19882/AutoDraw/actions/runs/42440726798): Egret job FAIL на неверном предположении `27 × n` сохраняемых путей; raw browser reported frames1: 27 duplicate rejections, accepted1260, path count **71**, не 97. Начало нового stroke вызывает full redraw и стирает transient paths предыдущего. [Artifact](https://github.com/Kiddos19882/AutoDraw/actions/runs/42440726798/artifacts/13601826297). Эту попытку не считать PASS.
- [Full CI 42440876068](https://github.com/Kiddos19882/AutoDraw/actions/runs/42440876068) **SUCCESS** на `a35d782`: native Egret, preparation, executor, monitor/bridge, integration и independent PNG audit PASS, optional benchmarks/Windows build SKIPPED. [Native 6 PNG](https://github.com/Kiddos19882/AutoDraw/actions/runs/42440876068/artifacts/13600769368); [independent JSON+overlay](https://github.com/Kiddos19882/AutoDraw/actions/runs/42440876068/artifacts/13602035420). Финальные surviving paths 70/71/73, accepted1260 неизменны, 0 RGBA difference внутри каждого backend, old accepted-only PNG baseline confirmed pixel-identical. Canvas2D vs WebGL baseline 243 differing RGBA pixels (не следствие дополнительных кадров).
- Исторический FILL-001 по-прежнему FAIL 98.430600% / 11 live leakage, exact CHALK прежнего run 1260. Фактические timestamps и screen mapping UNCALIBRATED; новый CHALK NOT_RUN, E4 gate открыт.


## 2026-11-08 — ENGINE-001: однокнопочная лаборатория Monitor/Bridge (без реального игрового запуска)

- Baseline HEAD `951151c` и 20 commits/Actions проверены; изучены status/task/roadmap/guide, Monitor/Bridge, existing CHALK block, Stage6, Tk UI, fixed PRR runs и текущие ограничения E4. Разрешение относилось к реализации автономного теста, а не к запуску на компьютере пользователя. New experiment `ENGINE001_ONE_CLICK_LAB_V1`.
- Разработка только в исследовательских UI, Game Monitor 0.2.4, Bridge collector и экспериментальных validators/tests: 3×3 изолированных запусков (горизонталь, вертикаль, диагональ), по одному штриху и fresh clean-board PNG, один GUI button; previous matrix phases G1/G2/G3/PRR unchanged. Все 9 cells, профиль radius=10/step2/delay10/extension0 и owner locks строго валидируются; нет параллельного executor.
- Bridge сохраняет новое `ENGINE_FRAME_SAMPLE` с raw per-Egret-frame O(1) counters, координатами и режимом, классические `POINT_QUOTA_UPDATE` + RAF probe не заменены. Lab audit требует raw event/rollup agreement, exact counter, 0 telemetry loss, stable same-run geometry and screenshot hashes. No cold-start browser injection, existing manual Origin/snippet bootstrap.
- Файлы изменены в source/preparation, source/game_monitor и integrated_app + исследовательские tests и профильные docs. Production Stage6 executor, CHALK predictor, quality thresholds, `master`, original FILL-001 frozen evidence не менялись. CI [42443300762](https://github.com/Kiddos19882/AutoDraw/actions/runs/42443300762) проверяет code/test SHA `a119b7d`; фактический game run отсутствует, E4 `NOT_RUN` и CHALK `NOT_MEASURED`. Новый screen projection E5 ещё требует live captures и калибровки.


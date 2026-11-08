# AutoDraw — дорожная карта будущих работ

**Дата:** 2026-11-08 · **База сверки:** `a2d1f0a52d47` · **Ветка:** `feature/image-geometry-optimization`. Подробная прежняя редакция полностью сохранена: [ROADMAP_HISTORY_THROUGH_2026-11-08.md](ROADMAP_HISTORY_THROUGH_2026-11-08.md).

Этот файл задаёт **последовательность**, а не историю. Пункты выполнения и владельцы конкретных gate — [TASKS](TASKS.md); подтверждённые факты — [PROJECT_STATUS](PROJECT_STATUS.md) и [TEST_RESULTS](TEST_RESULTS.md).

**Этап 0 завершён:** 99/99 Markdown в навигации, девять сохранённых исторических редакций, автоматический audit [CI 42421451709](https://github.com/Kiddos19882/AutoDraw/actions/runs/42421451709) SUCCESS. Далее только будущие приоритеты.

## Текущий этап — ENGINE-001: документирование игрового движка

**Приоритет на 2026-11-08:** понять и описать сохранённый Egret 5.4.1, особенно интерактивный `PainterPopup.painterBoard`: создание `BoardPane`, `BlackBoardAtom`, принимаемые события и точки, `Painter` normal/smooth, `GraphicsNode` и Canvas/WebGL raster, `scrollRect`/roundRect mask, экранные преобразования, quota/CHALK, ограничения browser reference. Существующие профильные результаты сохранять, не выдавать E1 за новую E4.

**Выход:** [систематический технический документ](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md), связанные первичные ссылки/хеши, перечень известных и неопределённых частей. **Gate:** пройти проверку документации, а для будущих утверждений о pixel accuracy — независимую validation; никаких изменений production и новых FILL-001 runs сейчас. Тесты следующего этапа перечислены ниже и **не запущены**.

## Этап 1. Офлайн-сравнение качества геометрии

Определить неизменный baseline на уже доступных изображениях. В FILL-001 воспроизвести perimeter-localized failure, сравнить scanline и outline-first / contour-correction без изменения production executor. Сопоставлять coverage, leakage, boundary errors, details, path length, strokes и expected operation count раздельно.

**Промежуточное доказательство 2026-11-08:** Новый FILL-001 A–D offline [CI 42424959123](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123): SUCCESS на workflow SHA `6d790cd`. 3 frozen mask × 4 strategy, 15 диагностических PNG + JSON ([artifact 13595421597](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123/artifacts/13595421597)). Для варианта C coverage rectangle=99.516%, wide=99.593%, narrow=99.381%, leakage=0 в OpenCV. Эффект не подтверждён на реальном PNG. Вариант D использует oracle residual и создаёт слишком много дополнительных штрихов. Paired screen-ROI residual comparison теперь выполнен: [CI 42427514794](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794) SUCCESS (`16f0e1b`), [artifact 13596093007](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794/artifacts/13596093007). Actual ROI target 71110 screen px: 1116 uncovered, 11 leaked. Hypothetical contour inset6 recovers 734, leaves 382, would yield 99.462804% coverage with 0 NEW model leakage, but existing 11 leakage remain, so this is not a game PASS. Первый CI [CI 42427122693](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427122693) FAILED из-за LF/CRLF проверки JSON, исправление протестировано. **Следующий шаг:** калибровать actual endpoint/brush footprint и источник 11 leakage; отобрать domain-representative подвыборку 81 изображений после уточнения geometry assumptions. Quality gate оригинального game capture остаётся FAIL.

**Gate:** качество ≥99% coverage и leakage=0 для ранее заданных FILL-001 targets до новой live-проверки; offline simulation не утверждает runtime.

## Отложенная программа тестов FILL-001, GEOM-001 и связанных gates

Это **сохранённый план будущих экспериментов**, не разрешение запускать их и не список новых PASS. Возобновление только после ENGINE-001 и после отдельного protocol/quality review.

**Базовые уже выполненные проверки (не запускать заново без новой причины):**

| Вариант | Гипотеза / протокол | Нынешние доказательства |
|---|---|---|
| `A` плотные scanlines | Одна линия практически в каждую строку | OpenCV/CI PASS для трёх frozen masks, число штрихов велико |
| `B` разреженные scanlines | Изменить `scanline_row_step/offset` | 2238 offline combinations; rectangle/r10/step5/offset0 — 27 strokes; live CHALK=1260, PNG **FAIL** 98.430600%/11 leaks |
| `C` B + связная контурная обводка | Поправить края одним проходом | OpenCV/CI для трёх frozen masks; screen-ROI offsets 5–8 model counterfactual — не игровой запуск |
| `D` B + контур + локальные residual corrections | Достичь покрытия без массового уплотнения | OpenCV oracle знает эталонную residual mask; алгоритм не готов к игре |
| `RS` sweep | Влияние радиуса, вертикального шага и offset | 15 shape×radius configs подобраны offline; 45 live cells **BLOCKED** до принятого preflight |
| `PRR` | Paired Egret renderer vs live screenshot, vertical/diagonal | 6/6 PASS_PER_RUN на radius10, но IoU ~0.938–0.952, не pixel-identical |

**Возможные НОВЫЕ кандидаты, пока только E0:**

- `E1 adaptive brush width` — широкая кисть на безопасных прямых, 5px/малые толщины у закруглений/опасных границ; учитывать реальный `lineWidth`, перекрытия и переключения; маленькие значения 1/3 могут иметь renderer-specific pixel alignment.
- `E2 adaptive contour inset` — постоянный размер кисти, локально меняющийся внутренний отступ по curvature/safety margin; сравнение с фиксированными offsets 5/6/7/8.
- `E3 joint adaptive width+inset` — объединить E1/E2; проверить переходы между штрихами, концевые caps и отсутствие новых разрывов.
- `E4 bounded local correction` — короткие локальные проходы по обнаруженным пропускам без доступа к oracle mask исполнительного алгоритма, с отдельной оценкой числа strokes и смен кисти.
- `ER multi-stroke Egret replay` — **переиспользовать существующий** [`tests/game_renderer_reference.js`](../tests/game_renderer_reference.js) вместо нового симулятора: 27 run-bound accepted-point штрихов FILL-001, реальный `BoardPane.redraw`, Canvas/WebGL PNG, mode/width/colors/options, clipping, проверка сохранённого `after.png` и 738 model-only / 11 leakage pixel discrepancies. Текущий live-replay принимает один штрих и требует same-run renderer snapshot; отсутствие такового у старого FILL-001 отражать как `UNCALIBRATED`, не подставлять другие session transforms. Из прямого аудита [ENGINE-001 §12](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md) следует дополнительный исследовательский риск: игра накапливает `StrokePath` через `redraw(false)`, а existing harness делает one-pass `redraw()`. В будущей разрешённой версии сравнить `one-pass` и `incremental-redraw` по тем же данным и не называть возможное пиксельное отличие доказанной причиной FILL-001.
- `EXT` coarse/edge-targeted candidate sweep — локальная коррекция вместо глобального dense rowstep; проверка покрытия по corners/left/right/top/bottom отдельно, ограничения смещения и растровой неопределённости.

**Тестовый протокол для возобновления (до запуска зафиксировать новые versioned experiment IDs):** неизменные SHA frozen masks/планов и 3 формы; один и тот же brush/renderer profile; дополнительные representative image families из 81 после CORP-001 review (Stage8 mono и Stage6 color отдельно). Для каждого кандидата хранить PNG, coverage, leakage, boundary error zones, details, length, stroke count, width/color switches, runtime cost **отдельно** от measured CHALK. Продолжать только при исходных gates: FILL coverage ≥99%, leakage=0; использовать ±1 screen px/аналогичную чувствительность как риск-анализ, не как независимое доказательство игры.

**Зависимости и запреты:** сначала закрыть источник 11 actual leakage и 738 model-only discrepancies либо явно классифицировать причину; не принимать 45-cell FILL-001 matrix до **нового одиночного live preflight PASS**; сохранять Monitor/Bridge exact run identity и `CHALK=post.pointCount-pre.pointCount`; даже качественный offline Egret не считается E4. Не менять production estimator/executor/defaults и frozen evidence без новой независимой validation.

## Этап 2. Изучение фактического цветного execution pipeline

Отделить monochrome Stage8 scanlines от Stage6 color scanlines. Учитывать порядка 942206 source strokes, 395455 singletons и 916312 source color transitions на 81 изображении, но не приписывать эти числа одному рисунку и не превращать в CHALK. Проводить safety/overlap проверку перед попыткой сокращать цветовые переключения.

**Gate:** воспроизводимый сравнительный dataset, provenance и критерии качества, visual family independence отдельно.

## Этап 3. Оптимизация CHALK на основе уже выполненных опытов

Использовать измеренные G1–G3, V1–V5, D1–D5 и INT006R, не повторяя их без причины. При необходимости 95%-й policy заранее определить поддерживаемый domain и провести отдельную замороженную независимую validation (19/59 на профиль). Exact CHALK — только `post.pointCount-pre.pointCount`.

**Gate:** safety margin и применимость модели установлены для заявленного domain, а не для всех изображений по умолчанию.

## Этап 4. Интеграция resource preflight (INT-007)

Только после этапа 3 и других required quality gates: fail-closed UNKNOWN для неподдержанной геометрии, provenance модели, бюджетные предупреждения, regression, Windows startup и разрешённые live tests.

**Статус INT-007:** **BLOCKED**.

## Не смешивать уровни доказательств

CI/build, offline quality, real game `pointCount`, pixel equivalence и статистическая predictive coverage подтверждаются отдельно. История всех решений и неудач остаётся в [архиве дорожной карты](ROADMAP_HISTORY_THROUGH_2026-11-08.md) и специализированных отчётах.

## Совместимость старой ссылки на план калибровки

<a id="уточнённый-временный-план--автоматическое-определение-геометрии-доски-и-handoff-калибровки"></a>
Старый раздел перенесён в [полную дорожную карту до 2026-11-08](ROADMAP_HISTORY_THROUGH_2026-11-08.md#уточнённый-временный-план--автоматическое-определение-геометрии-доски-и-handoff-калибровки). Эта запись — навигация, а не возобновление закрытых задач.

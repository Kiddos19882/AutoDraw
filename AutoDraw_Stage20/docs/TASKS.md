# AutoDraw — действующие задачи

**Дата:** 2026-11-08 · **Ветка:** `feature/image-geometry-optimization`. Это список **открытых** работ. Полный старый журнал задач с закрытыми пунктами, историческими `PENDING` и ссылками: [TASKS_HISTORY_THROUGH_2026-11-08.md](TASKS_HISTORY_THROUGH_2026-11-08.md).

**DOC-001…DOC-004 закрыты:** [CI 42421451709](https://github.com/Kiddos19882/AutoDraw/actions/runs/42421451709) SUCCESS, 99/99 индексировано, 0 broken links, 9 immutable archives, 0 duplicate decisions. Фактические действия отражены в [WORK_LOG](WORK_LOG.md); старые чек-листы остаются в [истории TASKS](TASKS_HISTORY_THROUGH_2026-11-08.md). Ниже перечислены только открытые технические задачи.

## P0 — текущая работа: игровой движок и документация

- [ ] **ENGINE-001** — Выполнить проверяемый разбор сохранённого Egret 5.4.1 и рабочего `PainterPopup.painterBoard`. Подробный [прямой аудит игровой доски](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md) (§12) подтверждён `E1 PASS` для методов: полный `main.min` получен по Git blob, SHA совпал; разобраны `BlackBoardAtom/BoardPane/Painter/PainterPopup`, бинарный `Atom` и накопление путей в Egret. **ENGINE-001 остаётся PARTIAL:** end-to-end трассировка `WebTouchHandler → desktop mouse plugin / TouchHandler → SystemTicker/ENTER_FRAME → BoardPane → GraphicsNode/Canvas2D/WebGL/mask → screen` теперь выполнена по исходникам [§13](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md). **Документационная сверка выполнена:** Game Monitor/Bridge, шесть PRR runs (порог текущей DEC-025 = 0.92) и runtime 04.11 сопоставлены в [§14](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md#14-финальная-сверка-источников-game-monitorbridge-prr-и-runtime-2026-11-08); исправлено прежнее утверждение о рассчитанных `boardClientCorners` (в JSON они null). **Accepted-only offline gate выполнен:** [ENGINE001_TEMPORAL_ACCEPTED_ONLY_V1](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md) — 27 штрихов, 1260 принятых точек, 70 против 29 Graphics paths, 0 Canvas2D/WebGL RGBA отличий в итоговом растре, browser job [42434968046](https://github.com/Kiddos19882/AutoDraw/actions/runs/42434968046) SUCCESS (E2/E3). **Осталось:** неизвестные повторные `ENTER_FRAME` без новой точки, промежуточные рендеры, screen transform и независимая live PNG validation. Не считать accepted-only E2 полноценным E4. **Критерий завершения:** профильная документация отражает источник для каждого существенного вывода и явно отделяет E1, E2/E3, E4, UNKNOWN; противоречия не замалчиваются. Не запускать новые live/оптимизационные тесты в рамках документационного этапа.

## P1 — отложенные тесты качества и оптимизации (не закрыты)

**Статус:** `DEFERRED_BY_PRIORITY` до выполнения текущего ENGINE-001; прежние PASS/FAIL/BLOCKED не меняются. Полная матрица новых кандидатов и ранее запланированных тестов — [ROADMAP](ROADMAP.md#отложенная-программа-тестов-fill-001-geom-001-и-связанных-gates).

- [ ] **FILL-001** — Live baseline 27/27, exact CHALK=1260, actual coverage=98.430600%, leakage=11: **REJECTED**. Frozen A–D и paired screen-ROI contour counterfactual выполнены ([CI 42427514794](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794); [artifact 13596093007](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794/artifacts/13596093007)): 1116 screen misses; offset6 model recovers 734, leaves 382, adds 0 model leakage, но старые 11 остаются; ±1px dilation adds 89 leakage. **Следующий gate:** выяснить 738px model-only mismatch, локализовать leakage и подобрать boundary-aware geometry без новых утечек; затем независимый новый live preflight. Пороги ≥99% и 0 не менять. [Original live evidence](CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md).
- [ ] **GEOM-001** — A–D offline analyzer для трёх FILL-001 frozen masks реализован ([CI 42424959123](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123)). **Следующий незавершённый шаг:** закрепить representative source/image-family подвыборку из 81 изображений, расширить контроль на mono/color (разные Stage8/Stage6 пути) и сопоставить качество/контуры/длину/strokes отдельно от estimated sampling и measured CHALK.
- [ ] **CORP-001** — Проверить вручную shortlist 20 ближайших image pairs и semantic families; SHA+pHash не являются доказательством независимости. [Raw result](https://github.com/Kiddos19882/AutoDraw/actions/runs/42416307401/artifacts/13591427560).
- [ ] **CORP-002** — Для Stage6 color / Stage8 mono проверить порядок, palette transitions, singleton→1px drag, overhead и качество; нельзя безопасно переставлять штрихи без анализа наложений. [Offline report](TEST_RESULTS.md).
- [ ] **MON-001** — Для всякой новой разрешённой live-матрицы заранее проверить Monitor/Bridge run/session identity, per-stroke agreement, exact pointCount, образец пустой доски и ROI.

## P2 — политика ресурса и зависимости

- [ ] **INT-006** — Расширить domain applicability и обосновать запас безопасности на независимых DrawingPlan. Frozen D1–D5 P0/P1/P2 не менять из-за результатов scanline. [Официальные измерения](CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md).
- [ ] **INT-006-95** — Для *формальной* заявленной 95%-й predictive coverage после выбора domain/population зафиксировать 19 calibration / 59 независимых holdout. [Предложенный протокол](CHALK_95_PERCENT_CALIBRATION_HOLDOUT_PROTOCOL_2026-11-07.md). Не требуется как предварительное условие офлайн-оптимизации.
- [ ] **INT-007** — **BLOCKED**: production resource estimator только после принятой safety policy и required gates.

## КЛЮЧЕВОЙ ТЕХНИЧЕСКИЙ ВЫВОД ДЛЯ FILL-001-RS — связный контур вместо глобального уплотнения scanline (2026-11-04)

Пропуски принятого в telemetry, но отклонённого по PNG quality рисунка концентрируются у границ; глобально добавлять горизонтальные проходы — не доказанная стратегия. Офлайн проверить «редкая внутренняя заливка + один связный contour pass + локальные коррекции» с сохранением footprint safety. Это **гипотеза**, не подтверждённая экономия CHALK. Не менять постфактум пороги coverage ≥99%, leakage=0. [Residual diagnosis](CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md).

## Ранее закрытые CI-пункты — не backlog

- [42417067391](https://github.com/Kiddos19882/AutoDraw/actions/runs/42417067391) **SUCCESS** на `5a55e9f`.
- [42417067363](https://github.com/Kiddos19882/AutoDraw/actions/runs/42417067363) **SUCCESS** на `5a55e9f`.
- [42416307257](https://github.com/Kiddos19882/AutoDraw/actions/runs/42416307257) **SUCCESS** на `3fdffec`.
- [42415293374](https://github.com/Kiddos19882/AutoDraw/actions/runs/42415293374) **SUCCESS** на `985e194`.

**Текущие зависимости:** [ROADMAP](ROADMAP.md) · [PROJECT_STATUS](PROJECT_STATUS.md) · [TEST_RESULTS](TEST_RESULTS.md).

## Совместимость исторических ссылок

<a id="ключевой-технический-вывод-для-fill-001-rs--связный-контур-вместо-глобального-уплотнения-scanline"></a>
- Прежняя ссылка на FILL-001-RS ведёт к [этому действующему выводу](#ключевой-технический-вывод-для-fill-001-rs--связный-контур-вместо-глобального-уплотнения-scanline-2026-11-04); полный исторический текст — [здесь](TASKS_HISTORY_THROUGH_2026-11-08.md#ключевой-технический-вывод-для-fill-001-rs--связный-контур-вместо-глобального-уплотнения-scanline-2026-11-04).

<a id="brush-footprint-capsule-001--per-segment-broad-phase-independent-oracle-и-benchmark-2026-11-04"></a>
- Техническая запись BRUSH-FOOTPRINT-CAPSULE-001 сохранена в [историческом TASKS](TASKS_HISTORY_THROUGH_2026-11-08.md#brush-footprint-capsule-001--per-segment-broad-phase-independent-oracle-и-benchmark-2026-11-04); это не автоматически открытая новая задача.

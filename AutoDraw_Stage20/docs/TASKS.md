# AutoDraw — действующие задачи

**Дата:** 2026-11-08 · **Ветка:** `feature/image-geometry-optimization`. Это список **открытых** работ. Полный старый журнал задач с закрытыми пунктами, историческими `PENDING` и ссылками: [TASKS_HISTORY_THROUGH_2026-11-08.md](TASKS_HISTORY_THROUGH_2026-11-08.md).

**DOC-001…DOC-004 закрыты:** [CI 42421451709](https://github.com/Kiddos19882/AutoDraw/actions/runs/42421451709) SUCCESS, 99/99 индексировано, 0 broken links, 9 immutable archives, 0 duplicate decisions. Фактические действия отражены в [WORK_LOG](WORK_LOG.md); старые чек-листы остаются в [истории TASKS](TASKS_HISTORY_THROUGH_2026-11-08.md). Ниже перечислены только открытые технические задачи.

## P1 — качество рисунка и практическая оптимизация

- [ ] **FILL-001** — Диагностировать perimeter gaps и leakage в сохранённом PNG: 27/27 strokes, точный CHALK=1260, coverage 98.430600%, leakage=11; baseline отклонён. Офлайн сравнить scanline и кандидат «редкая заливка + связный контур + локальная коррекция» с неизменными acceptance thresholds ≥99% / 0. [Evidence](CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md), [план](CHALK_FILL001_TEMPORARY_PLAN_2026-11-03.md).
- [ ] **GEOM-001** — Выбрать фиксированный набор реальных изображений и сравнить качество нескольких стратегий на одинаковых данных. Отдельно strokes/path/overlap/coverage/leakage, не выдавать proxy за measured CHALK.
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

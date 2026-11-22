# ENGINE-001 / BPRED-S5-R1 — кисти, механика заливки и проверка тестовой матрицы (E1 + inherited E3; new E2 UNKNOWN)

**Дата:** 2026-11-23. **Ветка:** `feature/image-geometry-optimization`. **Базовый HEAD до тестов:** `be813e4f167392213e22d24e2e72cb54ad1ec2f6`. **Frozen E0 до нового runner:** [протокол](ENGINE001_BPRED_S5R1_BRUSH_FILL_VALIDATION_MATRIX_PREREG_2026-11-23.md), new test+workflow code through commit `25805f54e0dfbbc568354ccafa9697f62d2d6609`. Прежние E3 ниже **переиспользованы как независимая историческая база**, новые Egret сцены/CHALK **NOT_RUN**.

## Фактически известная механика игровой кисти (из статического source, E1)

[Игровой bundle + engine report](CHALK_GAME_ENGINE_POINT_COST_AND_BRUSH_WIDTH_2026-11-03.md): `BoardPane.redraw` вызывает `graphics.lineStyle(s,color,1,false)`; значение `s` — толщина линии, **не** radius диска. Egret5.4.1 `GraphicsNode.lineStyle` caps/joins default `round`; normal path `moveTo/lineTo`, smooth path `curveTo` через midpoints с важным особым поведением конца `drawLast=false`; интерфейс painter popup включает smooth по умолчанию. Ввод stage→`globalToLocal`, BoardPane logical460×240, частота приёма точек в историческом live run около30Hz. Перекрытие штриха того же цвета композитится заново и меняет alpha/RGB; одиночная точка без drawable segment может расходовать point quota и не оставлять видимый след (точная ситуация требует native). **Только run-bound CHALK=post.pointCount-pre.pointCount**, число штрихов или длина не заменяют exact delta.

## Native E3 уже измерено на frozen engine blob46cc74de, renderer blob76d950e0

| Исследование | Проверенная геометрия и replay | Фактический исход | Что НЕ доказывает |
|---|---|---|---|
| [P4A2 CI44298271642](https://github.com/Kiddos19882/AutoDraw/actions/runs/44298271642) SHA bc2732c | width1..10, горизонтальные + диагональные, original-derived two-color | 40/40 заданных owner-mask alpha24 сравнений PASS с внешним допуском 3 logical pixels | Эту оценку двух штрихов нельзя переносить на full S5 picture |
| [P4D3 CI44417716689](https://github.com/Kiddos19882/AutoDraw/actions/runs/44417716689) SHA77e9ddd | width1..10×24 angles×2 lengths, 10 copies/10 overlays; 1121 native PNG | 480/480 exact same-scene replay; **только 292/480 pixel-identical translated clones**, 188 mismatch; 80/80 edge/other-color repeat; 480/480 overlay changes RGBA | «Одинаковый отпечаток в любых координатах», «alpha не меняется от перекрытия» |
| [P4D4 CI44419171411](https://github.com/Kiddos19882/AutoDraw/actions/runs/44419171411) SHA e6f561a | exact 1/256 logical coordinate snap, 961 native PNG | 480/480 scene replay exact, но **только 256/480 translated clones**; улучшения в универсальной переносимости нет | float coordinate quantization как достаточное решение |
| [BPRED-S2v4 CI44659022526](https://github.com/Kiddos19882/AutoDraw/actions/runs/44659022526) SHA2faf01d | 120 новых native сцен, width1..10, 3 угла, 2 XY-фазы, 3 повтора | M5 physical alpha24 TP383505, FP3; H1 zero-FP FAIL, H2 TP-retained95.2479% PASS, H3 per-width/angle FAIL | Pixel-exact безопасность M5, перенос порогов на current S5 model |
| [P4D17/18 native](ENGINE001_B1R_P4D17_P4D18_NATIVE_FULL_REPAINT_RESULTS_2026-11-19.md) | прежний full owner-art E/F, true BoardPane | interior alpha0 уменьшен, но original white contamination/protected original errors остались; technical E3 PASS/quality FAIL | Качество текущей S4.6→S5 сцены |

Все source native claims относятся только к соответствующим pinned SHA, не к пользователю PC/game E4. Данные из проектного TEST_RESULTS/ROADMAP и исходных протоколов; здесь нет повторной независимой перехешировки архивов.

## Что теперь проверяется новым S5-R1 runner

`tests/run_engine001_bpred_s5r1_brush_fill_matrix.py` осуществляет **960 ideal capsule cases** sizes1..10, angles0..345 step15, lengths0/13, logical phase0/.25; проверяет `guaranteed⊆potential`, reversal, независимую аналитическую distance membership на пиксельных центрах, противоречия upper/lower envelope. Сравнивает existing `interior_fill_planner` vs new S5-R1 на square, alpha hole, checkerboard, diagonal1px; отдельные speed runs 64,256,512 canvas. Непосредственные изменения в production brush/model/planner не вносились. Новый изолированный [CI workflow](../../.github/workflows/engine001-bpred-s5r1-brush-fill-validation.yml) на SHA `25805f54e0dfbbc568354ccafa9697f62d2d6609` запускает также existing footprint/interior/brush/swept tests и восемь S5-R1 synthetic. Выход `brush_fill_model_report.json`, `matrix_cases.json` и SHA. **Важно: потенциальный геометрический touched area ≠ exact native alpha/RGB; synthetic run не является full composite validation.**

**Статус новых тестов:** `NOT_VERIFIED / CI UNKNOWN` — GitHub connector для SHA returned `statuses=[]` и `workflow_runs=[]` при известном PR-only ограничении списка runs; не интерпретировать как отсутствие workflow или успех. Нет новой E2 статистики/seconds/4DEV coverage. Оригинальный S5-R1 4DEV×2 по [отдельному workflow](../../.github/workflows/engine001-bpred-s5r1-offline.yml) также ещё не подтверждён.

## Оценка алгоритмов (решения до нового E2)

- **Подтверждённое E1:** `swept_capsule_pixel_masks` умеет произвольный угол, но она ideal capsule и phase-insensitive на уровне математической модели; `interior_fill_planner` использует horizontal rectangle и не обрабатывает реальный alpha-over. 
- **Обязательный S5-R2 redesign:** region-wise candidate search, width1..10, continuous direction proposal, native-calibrated predicted **per-pixel alpha/RGB** with conservative false-safe guards, layered source-over/white/protected ledger, independent contour strokes, stroke order gated by after-composite native. Start after E2 and performance baseline, not micro-adjust S5-R1 local seed bank. Existing capsule/provenance baseline remains.
- **Unknown / forbidden claims:** source owner S4.6 `MISSING`, native mapping `UNVERIFIED`, current S5-R1 E2/CI `UNKNOWN`, original4 x2 post-paint quality `NOT_RUN`, E4/E5 game `NOT_RUN`, exact CHALK `NOT_RUN`. User DEC-051 S4 accepted quality ≠ technical native calibration.

**Единственный следующий шаг:** проверить точный GitHub Actions CI для SHA `25805f54e` и отдельный SHA `5c3d90e`, сохранить raw/failed results; затем freeze E0 конкретного region-based S5-R2 с gap repair и full native per-owner compositing, без повторения P4D3/P4D4 matrix, если не менялись engine/renderer или исследуемая переменная.

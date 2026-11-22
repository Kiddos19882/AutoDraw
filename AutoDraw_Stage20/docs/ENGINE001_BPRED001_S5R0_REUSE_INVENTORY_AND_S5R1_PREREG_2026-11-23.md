# ENGINE-001 / BPRED-S5-R0.1 inventory → S5-R1 candidate E0 (2026-11-23)

**Ветка:** `feature/image-geometry-optimization`; **baseline HEAD перед протоколом** `6ecefa12b6f84e1b384ae419c03b81fb544207a9`. **Статус:** S5-R0.1 static E1 completed in bounded scope; S5-R1 prospectively specified, **code / E2 / CI / native / game NOT_RUN**. [DEC-051](DECISIONS.md) — S4 качество принято пользователем для S5 research, исторические количественные результаты не переписаны.

## Инвентаризация на доступном удалённом HEAD (E1 — по исходникам, не runtime)

| Потребность | Существующий owner/entrypoint | Действительная граница |
|---|---|---|
| Исходный пакет source-only | `tests/engine001_bpred_s4r1_s46_source_contract.py`, `export_quarantined`, `verify_quarantined`; `tests/run_engine001_bpred_s4r1_s46_dev.py` | Исходные RGBA, alpha, `source_atom_id`, `surface_id`, `paintable_id`, `game_index`, `protected_original_dot`, `source_edge`, contours, SHA. `source_owner_status=MISSING` и `admissible_for_gameplay=false`. Source pixel corners НЕ desktop/client/native calibration |
| Исходный image→map producer | `tests/engine001_bpred_s4r1_ctr1_source_contour.py` / `build_ctr1` | Recomputes current original+game128, not production planner; original strong detail remains partial |
| Наивный адаптивный fill | `source/preparation/interior_fill_planner.py` / `build_interior_fill_plan` | Ширины 2..20 + width1 fallback, цветовая проверка, **horizontal only**, консервативный axis-aligned rectangle, `safe_to_execute=false`; не native |
| Подбор кисти для существующих scanline | `source/preparation/brush_planner.py` / `build_adaptive_brush_plan` | Только горизонтальные существующие color scanline strokes; scale требуется извне; до executor не доведён |
| Footprint и произвольная ориентация | `source/preparation/brush_footprint_geometry.py` / `swept_capsule_pixel_masks` | Для любой полилинии возвращает `potential_cells` и `guaranteed_cells` для идеальной round-cap capsule; **не** точный Egret alpha/RGB/coverage; нет автоматической калибровки |
| Предыдущий FILL-001 контроль | `source/preparation/chalk_fill_fixed_radius_planner.py` / `rasterize_fill_strokes` | Фиксированные width, OpenCV модель, не новый full original, не exact CHALK |

**Вывод E1:** переиспользовать source packet validator и `swept_capsule_pixel_masks`, но **не** выдавать горизонтальный прямоугольный `interior_fill_planner` за Egret либо полноугловой алгоритм. Новый S5-R1 — тонкий строго экспериментальный candidate-selector над существующим swept capsule, не новый renderer/executor.

## S5-R1 — один frozen prospective candidate (E0 до разработки)

**Гипотеза:** циклический greedy candidate selector по реальной game128 карте и исходным protected данным из того же S4.6 пакета, с 1–10 размерами и произвольным непрерывным углом (геометрия отрезка), обеспечивает больше source-area coverage крупных областей, чем только горизонтальная модель, не покрывая по *моделируемому потенциальному следу* чужие цвета, alpha или protected original. Короткие/точечные детали width1, без индивидуально подобранных ROI. **Предыдущие S4 derived maps, архивные художественные PNG, P4D strokes не входят в candidate input.**

**Единственный экспериментальный вариант:**
1. Для каждого свежего original из закреплённых 4 DEV S4.6 x2: validate packet, проверить raw/source SHA; input `game_index` и `paintable_id` используются **как S4-derived research proxy**, **не** как verified native owner; сохранить source coordinate frame.
2. Для текущих ещё непокрытых пикселей предложить отрезки, лежащие в одной (paintable_id, game128) области. Перебирать widths **10→1**, направления задавать углом `atan2(dy,dx)` из точек области; разрешены любые углы 0..360° (не ограничивать горизонтальными). Начальный ограниченный deterministic direction bank {0°,45°,90°,135°} плюс направление локальной оси области по оригиналу; это **только proposal sampling**, не ограничение планировщика на 360°.
3. Проверять **все** `potential_cells` существующей `swept_capsule_pixel_masks` на принадлежность одному идентификатору области/цвету и исходной alpha. При конфликте reject/меньший width, не считать источниковую маску калибровкой; `guaranteed_cells` дают только нижнюю оценку покрытия. Приоритет новый правильный coverage → минимизация lost/foreign/white риска → strokes/длина/смена цвета только вторичные. Protected original dot не стирать и не игнорировать; для точек и микродеталей отдельно кандидат width1. Ограничить budget кандидатов детерминированным cap и выводить `PARTIAL` при его достижении, не подменять coverage на 100%.
4. Записывать отдельный research-only output: `MODEL_ONLY_NON_EXECUTABLE`, `safe_to_execute=false`, `source_owner_status=MISSING`, `native_calibration=UNVERIFIED`, исходные SHA/engine SHA, геометрия source coordinates, rejected reason counts, eligible/missing/covered counts и оригинальная детализация. Никакого Stage6/Bridge/Monitor или XML/game command.
5. Сравнить на тех же четырёх originals с baseline horizontal `interior_fill_planner` как **отдельным offline comparator**, не входом алгоритма. Предварительно фиксировать одинаковый scale=1.0 **только математическую source-pixel модель**, не выдавать за игровой физический размер кисти. Отдельно: genuine native 1–10 brush E3 NOT_RUN.

**Неподвижные проверки и статусы:**
- E2 synthetic: 1px dot, narrow neck, alpha wall, adjacent different/same game128 different region, diagonal line, no valid width>1, wrapped candidate direction; bad input SHA, wrong shapes/color, wrong status promotion all must fail-closed.
- Four untouched full DEV originals ×2; run output hashed, deterministic checks, rejected and uncovered pixels disclosed; measure geometry potential/guaranteed coverage, foreign/protected/alpha leak, edges/detail, per-width stroke counts, switches, memory and time. Zero modeled foreign/alpha intersections is a hard requirement for a **model-only** candidate, not native guarantee. No invented numeric improvement acceptance thresholds.
- S4 detail and color historical results remain unchanged. S5 native E3/E4 and exact game CHALK NOT_RUN until source owner and calibration are independently established.
- Escalation: if per-pixel mask cost becomes excessive on full EZAL, record computational BLOCKED/PARTIAL and optimize within existing footprint API; no alternative competing implementation without separate decision.

**Следующий шаг:** implement one reusable small **offline-only** adapter to consume a verified S4.6 packet and generate bounded deterministic S5 proposals using `swept_capsule_pixel_masks`, plus synthetic tests, then exact SHA CI. Do not confuse code commit with a passed CI run.

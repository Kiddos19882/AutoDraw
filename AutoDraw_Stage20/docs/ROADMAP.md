# Дополнение к дорожной карте — 2026-11-04

INT-003 и CHALK-SAMPLING-DOMAIN закрыты как NOT_REQUIRED по решению пользователя; не планировать отдельные работы по A/B/C overhead Monitor и расширению sampling-domain. Исторические evidence остаются.

## Актуальная последовательность работ

1. **P0 — FILL-001-RS renderer footprint/transform:** Egret 5.4.1, ROUND caps/joints defaults и CanvasRenderer implementation подтверждены в согласованном наборе assets, происхождение которого пользователь подтвердил как скачивание с сайта запущенной игры. Остаётся установить фактический render backend активной сессии, полный popup→board→screen transform, clipping/device-pixel mapping и footprint на frozen fixtures; пройти offline PNG gate coverage≥99%, leakage=0.
**Подэтап GAME-BRUSH-REPLICATION (внутри пункта 1):** статическая трассировка текущего игрового набора завершена (E1). Следующий offline gate — установить фактический Canvas/WebGL mode и полный transform, затем подготовить frozen fixtures/reference harness для кадровой выборки точек, normal/smooth path, clipping и PNG comparison. OpenCV и Capsule остаются моделями, а не подтверждённой копией renderer. Реализация в AutoDraw и live captures пока не выполнялись.

2. **P0 — single-task live preflight:** только после offline PASS и отдельного разрешения пользователя. Последний capture (coverage 98.430600%, leakage 11) отклонён; exact CHALK=1260 относится только к этому capture.
3. **P0 — FILL-001-RS 45-cell matrix:** только после принятого single-task preflight и отдельного разрешения; 15 shape×radius cells × 3 повтора.
4. **P1 — BRUSH-FOOTPRINT-CAPSULE-001:** завершить offline fixture comparison/renderer agreement и решить, нужна ли интеграция generic planner. Это отдельная геометрическая корректность; не установленная причина RS rejection.
5. **P1 — INT-006:** расширить domain модели CHALK и установить error bounds/safety margin; до этого estimator/defaults не менять и INT-007 не начинать.

**Объём Game Monitor:** текущая комната пользователя не содержит других досок; на экране одна пустая тестовая доска. Исторически найденное различие preview/PainterPopup BoardPane помечено `NOT_APPLICABLE_TO_CURRENT_USER_SCENARIO` и не является пунктом roadmap. Это не означает исправление общего auto-discovery для сценариев с несколькими досками.

INT-006 можно вести как отдельную offline/validation работу без запуска live экспериментов; для любых новых live captures требуется отдельное разрешение.

---

## Дополнительная offline ветка — BRUSH-FOOTPRINT-CAPSULE-001 (2026-11-04)

Статический аудит обнаружил coverage overclaim в generic `interior_fill_planner`: прямоугольный bbox horizontal brush stroke помечается полностью covered, хотя для round caps реальный footprint имеет capsule shape. Независимые tests сейчас также используют rectangular oracle. Это отдельная задача геометрической модели и не доказанная причина FILL-001-RS: fixed-radius FILL-001 planner использует отдельный OpenCV round-capped rasterizer.

План: разработать separate potential/guaranteed pixel-cell masks; сохранить bbox только как broad-phase; покрыть horizontal endpoints, diagonals, joins, anisotropic scales и canvas boundaries; сравнить old/new results на frozen fixtures. Не менять planner/defaults до acceptance. Основной FILL-001-RS renderer gate остаётся приоритетным blocker; live experiments не открывать.

---

## Актуализация ближайшего FILL-001-RS gate — 2026-11-04

Telemetry implementation для будущих запусков завершена и прошла полный CI: run [41840582147](https://github.com/Kiddos19882/AutoDraw/actions/runs/41840582147) SUCCESS. Browser Bridge связывает frame_probe с strokeId и сохраняет rAF intervals; Bridge Server сохраняет raw frame probes, per-stroke frame summaries и per-stroke point-count metrics. Старый run `6a17a297` не содержит raw per-stroke rAF series, но его point cadence восстановлена по 1260 POINT_QUOTA_UPDATE: median 33 ms, 28.26–29.50 accepted points/s. Не смешивать browser rAF (~60 FPS), nominal Egret stage.frameRate=48 и фактическую cadence принятия точек.

Статический renderer audit уточнён: PainterPopup 676×379, BoardPane 460×240 без локального scale; stage NO_SCALE, nominal frameRate 48. В подтверждённом пользовательском наборе assets установлена версия Egret 5.4.1; merge bundle содержит ROUND defaults caps/joints и CanvasRenderer path. Это не доказывает, какой backend был активен в конкретной старой сессии. Parent/global transform, device-pixel ratio, zero-length rasterization и фактический screen footprint остаются открытыми.

**Следующие шаги:**
1. **Завершено — подтверждение актуального набора assets:** пользователь подтвердил, что `AutoDraw_Stage20/gameEngine/main.min_653f95bc.js`, `mergeEngine_df2e5bc5.js` и `manifest.json` скачаны с сайта запущенной игры одновременно. Сверка с `master:fileGameEngine/main.min_570122a1.js` не требуется. Для этого набора статически установлена версия Egret 5.4.1. Исторические Resource Timing captures с `main.min_6ecc02a4.js` остаются отдельным свидетельством старых загрузок и не используются как основание текущей runtime-идентификации.
2. Измерить полный global/display transform painter popup BoardPane, включая родительские контейнеры и browser pixel mapping.
3. Проверить zero-length stroke rasterization на соответствующем runtime или независимом controlled PNG capture.
4. Откалибровать screen-space footprint и endpoints для нескольких brush widths на одной frozen geometry; сохранить raw PNG и hashes.
5. Проверить versioned perimeter/endpoint candidates независимым PNG audit: coverage≥99%, leakage=0.
6. Только после offline PASS выполнить отдельный live preflight; 45-task matrix остаётся отдельным последующим gate.

Run [41840281018](https://github.com/Kiddos19882/AutoDraw/actions/runs/41840281018) был CANCELLED; run 41840582147 — SUCCESS. Ни один из них не меняет факта, что исходный live capture REJECTED (coverage=98.430600%, leakage=11, exact CHALK=1260). Frozen plans/masks/thresholds/production defaults не менять.

---

## Обязательный ближайший gate — калибровка renderer footprint FILL-001-RS

Offline pixel localization завершена: исходный capture fill001-rs-preflight-20261104-7.04 остаётся REJECTED (coverage=98.430600%, leakage=11); 1116 uncovered pixels распределены по периметру, interior/other=0. 45-task matrix остаётся BLOCKED.

Статический анализ полного bundle из master (blob 28838e803dcc6f85efb13febd93cc9e0f5046ffc) установил ENTER_FRAME sampling, dedup одинаковых соседних координат, O(N) пересчёт point count на каждый принятый sample и smooth path construction. Cap geometry, нулевой сегмент и popup display transform не установлены. Подробности: [engine audit](CHALK_GAME_ENGINE_POINT_COST_AND_BRUSH_WIDTH_2026-11-03.md).

**Порядок следующего increment:**
1. Извлечь per-stroke Bridge frame_probe intervals и связать с pointCount deltas / Executor step-delay.
2. Измерить global/display transform интерактивного painter popup BoardPane; локальный scale не задаётся, но родительский/CSS/devicePixelRatio transform не установлен.
3. Версия Egret 5.4.1 и ROUND defaults caps/joins установлены для подтверждённого набора assets. Проверить фактически используемый backend активной сессии и zero-length path rasterization на frozen fixture/controlled PNG capture.
4. Построить независимую versioned модель footprint и perimeter/endpoint candidates; проверить coverage≥99%, leakage=0.
5. Только после offline gate выполнить отдельный live preflight; 45-task matrix открывать лишь после его принятия.

Frozen plan, masks, thresholds, production defaults и runtime behavior не менять на этом этапе.

# Roadmap AutoDraw

## FILL-001-RS — следующий gate после коррекции PNG transform

Кодовая коррекция alignment внесена в [4797aa5](https://github.com/Kiddos19882/AutoDraw/commit/4797aa5e2e3d9f78656c91dcddf285304eae55c1), regression assertions — [a950084](https://github.com/Kiddos19882/AutoDraw/commit/a950084db14fd1560aa15f099da4a0108c9631e7). До коррекции audit использовал W/460 и H/240, тогда как executor использует (W−1)/460 и (H−1)/240. На ROI 581×304 две версии mask rasterization различаются на 606 пикселей.

**CI evidence:** run [41772866679](https://github.com/Kiddos19882/AutoDraw/actions/runs/41772866679) SUCCESS на более раннем HEAD `974f949`, не валидировал affine correction. Run [41778045384](https://github.com/Kiddos19882/AutoDraw/actions/runs/41778045384) завершился FAILURE из-за пяти synthetic fixture/test failures. Test-only corrections committed: `1f28436`, `0f23731`. Последующий run [41780241017](https://github.com/Kiddos19882/AutoDraw/actions/runs/41780241017) на HEAD `0f23731` завершился SUCCESS и выполнил replay исходных PNG: coverage=98.430600%, leakage=11, PNG gate failed. Текущий этап — offline pixel localization, а не повторный CI или live запуск. До прохождения quality gate 45-task matrix BLOCKED; CHALK=1260 остаётся измерением только этой задачи и не означает принятия качества.

## Актуальный статус FILL-001 / FILL-001-RS на 2026-11-04

## FILL-001-RS — актуальный live preflight gate — 2026-11-04

Runtime binding для последнего rectangle/r10/step=5/offset=0 запуска восстановлен: legacy Bridge session без schema v2 больше не блокирует поиск. Replay через обработчик capture-кнопки подтвердил task↔executor↔Bridge binding, 27/27 strokes и exact CHALK=1260.

Однако live capture **не принят**. Первоначальный audit до affine correction: coverage=97.673218%, leakage=28. Replay исходных PNG исправленным audit в CI [41780241017](https://github.com/Kiddos19882/AutoDraw/actions/runs/41780241017): coverage=98.430600%, leakage=11. Улучшение подтверждено, но критерии ≥99% / 0 не пройдены. Следующий этап — offline локализация остаточных пикселей и диагностика renderer/raster discrepancy. До этого FILL-001 capture и 45-task matrix остаются BLOCKED.

Software gate: [CI 41772866679](https://github.com/Kiddos19882/AutoDraw/actions/runs/41772866679) SUCCESS на code/test HEAD `974f949`; Preparation/G3 804 passed, 24 warnings, 82 subtests; Executor, Game Monitor/Bridge, Application integration, INT-006 pixel audit и Windows portable build/startup smoke-test SUCCESS.


## Исправление FILL-001-RS frozen geometry rebuild — 2026-11-04

Пользовательский runtime evidence commit [63158fb](https://github.com/Kiddos19882/AutoDraw/commit/63158fb55743c566bf231196b80016273970bbf1) зафиксировал отказ single-task preflight до запуска исполнителя. Для задачи rectangle/r10 manifest и исходный DrawingPlan согласованы: planner_version=2, scanline_row_step=5, scanline_offset=0, plan signature совпадает с task, expected_strokes=27. Game Monitor подтвердил radius 30→10; pointCount остался 1 (CHALK=0), Bridge session завершилась без dropped events/errors/send failures.

Причина установлена в runtime guard integrated_app.py: повторное построение выполнялось вызовом build_fixed_radius_fill_plan(shape_id, radius) без spacing-параметров. Значения по умолчанию — step=1/offset=0, то есть legacy planner v1. Поэтому сравнивался FILL-001-RS v2 signature с другой геометрией v1 и срабатывал корректный fail-closed guard. Это ошибка handoff/validation, не ошибка регулировки кисти и не расход CHALK.

Исправление: единый helper повторного построения получает scanline_row_step/scanline_offset из frozen task; для legacy tasks без этих полей сохраняются прежние defaults. Объявленный planner_version проверяется против фактически восстановленного. Добавлены регрессионные проверки RS signature/27 strokes, legacy signature/131 strokes и отказа при несовпадении версии. До успешного CI и повторного локального preflight live matrix остаётся BLOCKED; повторный запуск здесь не выполнялся.

Последний code/test commit: [dac985e](https://github.com/Kiddos19882/AutoDraw/commit/dac985e147319d2275318531ab9063cdf410e5a4); полный workflow [41766148192](https://github.com/Kiddos19882/AutoDraw/actions/runs/41766148192) — PASS. Preparation/G3: 800 passed, 24 warnings, 82 subtests; sweep artifact uploaded; Windows portable build/startup smoke-test и INT-006 pixel audit PASS. Optional benchmarks skipped.

Exhaustive OpenCV sweep проверил 2 238 step/offset кандидатов; 62 прошли gate coverage ≥99% / leakage=0. Все 15 shape/radius cells получили frozen config. Реализованы planner version 2, отдельный 45-task RS manifest builder, single-task handoff, runtime context binding и генератор manifest. Полные результаты: [FILL-001-RS static sweep](CHALK_FILL001_RS_STATIC_SWEEP_2026-11-04.md). Это не live renderer evidence и не доказательство экономии CHALK.

**Текущий порядок:** (1) локально создать `fill001-rs-*` manifest; (2) на восстановленной доске с полной квотой выполнить один Windows/browser live preflight `rectangle/r10/step=5/offset=0/repeat=1`; (3) принять capture только после exact runtime binding и quantitative PNG audit; (4) затем отдельно решать вопрос новой 45-task matrix. Удалённый GitHub runner не имеет доступа к локальной игровой сессии/экрану, поэтому live preflight здесь не запускался. FILL-001 45-cell matrix остаётся BLOCKED; INT-006 safety margin не установлен; INT-007 остаётся BLOCKED.

## FILL-001-RS — исследование расстояния между проходами

1. **DONE — exhaustive static sweep:** 2 238 candidates, 62 accepted by frozen geometric gate; 15 shape/radius configs saved in report and source constants.
2. **DONE — versioned planner and matrix:** legacy planner v1 unchanged; RS planner v2, separate 45-task manifest, new plan signatures and frozen spacing metadata.
3. **DONE — single-task handoff:** RS plan passes through existing FILL-001 handoff; runtime context binds plan variant/version and spacing; P1 remains unchanged.
4. **DONE — CI validation:** preparation regressions (800 passed, 24 warnings, 82 subtests), exhaustive sweep artifact, all required jobs, Windows portable build/startup smoke-test and INT-006 pixel audit passed on code/test commit dac985e. Optional benchmarks skipped.
5. **READY FOR LOCAL PREFLIGHT — one task:** after CI success, generate manifest and run rectangle/r10/step=5/offset=0/repeat=1 in the local game with full quota; remote runner cannot access the user's local game session.
6. **BLOCKED — matrix expansion:** only after an accepted live capture; separate manifest/experiment ID, no mutation of the original FILL-001 series.

Preflight candidate r10/rectangle/step=5/offset=0: 27 strokes, 99,319% coverage, 304 uncovered target pixels, leakage=0 in OpenCV. Uniform step5 for the three shapes: rectangle 27/99,319%; wide_irregular 29/99,396%; narrow_irregular 43/99,173%. Estimated sampling points are not CHALK.

Evidence commit [73d14a1](https://github.com/Kiddos19882/AutoDraw/commit/73d14a1784a5a9f8ef29bc0e197b75352f2650af) добавил полный task Bridge run и session diagnostics. Exact CHALK=5999 подтверждён на run level и суммой point deltas, но 3 из 131 pointer candidates не потребили CHALK после исчерпания квоты; stroke_count=128, capture REJECTED. Первый Bridge run — калибровочный (CHALK=0) и исключается по event activity window. UI pending был временным: executor report появился примерно за 3.44 секунды до финализации Bridge run; после persistence строгая проверка должна завершиться отказом по 128/131 и 3 non-consuming candidates.

Шаги 1–2 временного плана DONE на предыдущем code baseline. Шаг 3 IN_PROGRESS: прежний live preflight rejected; FILL-001-RS software implementation и полный CI теперь PASS. Следующий gate — один локальный versioned live preflight; шаги 4–5 BLOCKED до его принятия. Предыдущий run exact CHALK=5999 — censored/over-budget attempt, не полная стоимость. Подробности: [FILL-001 postmortem](CHALK_FILL001_PREFLIGHT_POSTMORTEM_2026-11-04.md).

## Постоянная система управления знаниями ИИ

**Статус:** DONE — DOC-018. Постоянная система создана и подключена к основной навигации. Она состоит из AI_WORK_GUIDE.md, KNOWLEDGE_ARCHITECTURE.md, EVIDENCE_AND_VALIDATION.md, ENGINEERING_INVARIANTS.md и EXPERIMENT_STANDARD.md.

Система не является этапом текущего roadmap и не зависит от FILL-001. Она применяется ко всем будущим задачам проекта. Пересмотр допускается только при изменении постоянного процесса работы, источников знаний или инженерных контрактов.

## Временный исполнительный план FILL-001 — 2026-11-03

Действует отдельный [план из пяти шагов](CHALK_FILL001_TEMPORARY_PLAN_2026-11-03.md), обязательный к сохранению до завершения или отдельного решения пользователя:

1. Закрыть regression tests, полный CI и Windows portable build.
2. Реализовать runtime binding captures к Bridge/executor artifacts и P1.
3. Подключить отдельный FILL-001 UI/runner и провести один Windows live preflight.
4. Выполнить 45 live captures (3 формы × 5 радиусов × 3 повтора); до успешного шага 3 запуск заблокирован.
5. Проанализировать exact CHALK и качество, определить влияние радиуса и лучшую стратегию заливки.

**Текущий статус:** шаги 1–2 DONE; шаг 3 IN_PROGRESS — live attempt выполнен, но capture rejected. Статический анализ baseline выполнен; FILL-001-RS теперь содержит отдельный шаг воспроизводимой статической validation. Шаги 4–5 BLOCKED до принятого versioned preflight.

### FILL-001 — fill efficiency matrix

- [x] Frozen masks, fixed-radius planner и 45-cell manifest/analyzer.
- [x] Monitor capture adapter с per-stroke exact CHALK, radius/P1 binding и PNG hash/pixel audit.
- [x] Fail-closed runtime binding к Bridge session/run и executor report.
- [x] Отдельная вкладка FILL-001: manifest create/load, single-task selection, planner validation, operator approval, brush-size handoff, Stage 6 start с P1 override и capture finalization.
- [x] Исправить runtime JSON serialization после добавления `autodraw_experiment`: runtime-файл больше не получает буквальный `\n` после JSON object (commit `8dfd1b5`).
- [x] Добавить integration regression test реального FILL-001 plan → Stage 6 load с проверкой experiment context (commit `1b2d8a1`); JSON persistence/hash regression coverage подтверждены полным CI `41730717881`.
- [x] Полный regression gate FILL-001 закрыт CI [41730717881](https://github.com/Kiddos19882/AutoDraw/actions/runs/41730717881) SUCCESS на `fe6d446`, включая Preparation/G3, Application integration, Game Monitor/Bridge, Executor, INT-006 audit и Windows build.
- [x] Исправить binder false-overlap: Bridge run выбирается по event activity window, а не по `finished_at_utc` (commit `95a8d17`).
- [x] Добавить regression tests на позднюю финализацию pre-execution calibration run и полный разбор/hash JSON >27 MiB (commit `870bebc`); полный CI [41737923777](https://github.com/Kiddos19882/AutoDraw/actions/runs/41737923777) — SUCCESS.
- [x] Обработать incomplete Bridge sessions как pending только после фильтрации по времени executor и connection close; не принимать другой session, пока потенциально пересекающаяся session остаётся неполной.
- [x] Добавить retry runtime binding в FILL-001 кнопке «Проверить runtime + PNG и принять capture»; acceptance по-прежнему требует полного runtime binding и PNG audit.
- [x] Полный CI [41754801210](https://github.com/Kiddos19882/AutoDraw/actions/runs/41754801210) — SUCCESS; portable artifact ID 13288855067.
- [ ] После завершения FILL-001-RS static gate создать новый versioned candidate и провести Windows live runtime preflight на восстановленной доске; подтвердить P1 из фактического executor report.
- [x] Исправить физическое требование crop 460×240: UI снимает фактический calibrated client ROI, adapter преобразует frozen logical mask в размер PNG и сохраняет transform.
- [ ] Проверить реальные board PNG в client ROI: RGB threshold=8, cursor/UI exclusion и coverage/leakage против frozen masks.
- [ ] Только после preflight — 45 live captures и анализ расхода CHALK по shape/radius.

**Текущий gate:** binder activity-window correction и regression tests (`95a8d17`, `870bebc`) прошли CI [41737923777] SUCCESS. Предыдущий live execution завершился, но capture rejected; session CHALK=5999, доска исчерпана. Следующий шаг — один preflight на восстановленной доске. Live execution 45-cell matrix остаётся BLOCKED.

## Актуальный статус CHALK — 2026-11-03

### Исторический статус FILL-001 до UI/runner integration

Этот блок фиксирует промежуточное состояние до появления отдельной вкладки FILL-001. Его статусы и формулировка о недостающем UI/runner superseded актуальным временным планом в начале ROADMAP и `CHALK_FILL001_TEMPORARY_PLAN_2026-11-03.md`.

### INT-006

- [x] Независимая validation D1–D5: 45/45 accepted, 0 missing/rejected, 15/15 groups complete; официальный analyzer и CI [41532629748](https://github.com/Kiddos19882/AutoDraw/actions/runs/41532629748) — SUCCESS.
- [x] P1 (step=4/delay=5) определён как исследовательский кандидат; наблюдённая недооценка 0.92 CHALK на этой выборке не является статистической гарантией.
- [ ] Расширить validation на полные рисунки, кривые, заливки, повторное покрытие и другие радиусы.
- [ ] Установить safety margin на основе расширенной ошибки; до этого INT-007 BLOCKED.

### INT006R — radius × geometry

- [x] Software gate и Windows portable build/startup smoke-test прошли на code HEAD `28b56a9`, CI [41540054975](https://github.com/Kiddos19882/AutoDraw/actions/runs/41540054975).
- [x] Live block D1–D5 × radius 1/10/30 × 3 повтора при P1 завершён: 45/45 задач.
- [x] Raw-data audit всех 45 Monitor reports: exact CHALK, sampled/per-stroke delta совпадают, observed radius соответствует запросу, dropped events/errors/Bridge failures/sequence gaps — 0.
- [x] Запустить официальный CLI analyzer на реальном committed journal/capture bundle: run [41559932955](https://github.com/Kiddos19882/AutoDraw/actions/runs/41559932955), 45 accepted, 0 missing/rejected, PNG evidence complete.
- [x] Завершить ручной visual audit всех 45 пар PNG; зафиксировать ограничения D2/radius=1 (разрыв соединения) и D4/radius=30 (слияние коротких деталей). См. [visual audit report](CHALK_INT006R_VISUAL_AUDIT_2026-11-03.md).
- Результаты: [INT006R live report](CHALK_INT006R_LIVE_RESULTS_2026-11-03.md).

| Геометрия | Radius 1 | Radius 10 | Radius 30 |
|---|---:|---:|---:|
| D1 — mixed lines | 62.67 | 62.33 | 63.33 |
| D2 — polygon | 71.67 | 71.00 | 71.00 |
| D3 — intersections | 100.00 | 100.67 | 99.67 |
| D4 — short details | 14.33 | 14.67 | 15.33 |
| D5 — repeated coverage | 88.33 | 89.67 | 89.67 |
| **Среднее по 15 опытам** | **67.40** | **67.67** | **67.80** |

Наблюдаемая разница суммарного CHALK между крайними радиусами — 6 единиц (около 0.6%). Это не доказывает отсутствие влияния радиуса на эффективность заливки: область заполнения одинаковой площади в INT006R не сравнивалась.

### Следующий эксперимент — FILL-001

INT006R visual audit закрыт с geometry-specific limitations: radius 30 сливает короткие детали D4, radius 1 оставляет разрыв на соединении D2 polygon. Эти ограничения должны быть учтены при выборе формы целевых масок и критериев качества FILL-001.

- [x] Зафиксировать экспериментальный дизайн: три формы одноцветной области × радиусы 1/5/10/20/30 × три повтора = 45 captures.
- [x] Проверить engine semantics и ограничения существующих fill planners; зафиксировать отдельный fixed-radius harness design. См. [design](CHALK_FILL001_HARNESS_DESIGN_2026-11-03.md).
- [x] Создать frozen target masks на canvas 460×240; площади 44 653/45 159/44 879 px, разброс 1,133%, SHA-256 закреплены в коде. Software regression gate подтверждён CI [41673570178](https://github.com/Kiddos19882/AutoDraw/actions/runs/41673570178) на code/test HEAD `e3774a3`.
- [ ] Завершить калибровку footprint для всех радиусов 1/5/10/20/30; INT006R уже подтвердил raster width и выявил D2/D4 quality limits для 1/10/30.
- [x] Проверить H/V grid и eroded-contour prototypes; оба не проходят combined coverage/leakage gate, не интегрировать.
- [x] Реализовать boundary-aware fixed-radius centerline planner и raster simulator; отдельная Python simulation: 15/15 cells прошли coverage ≥99% / leakage=0. Regression tests добавлены, автоматический pytest/CI ещё pending.
- [x] Реализовать отдельный 45-cell matrix manifest, capture validation, analyzer и dynamic expected stroke validation; regression tests добавлены.
- [ ] Выполнить Windows live preflight из отдельной вкладки FILL-001: проверить фактический P1, Bridge/executor binding и реальные PNG против frozen masks.
- [ ] Только после успешного preflight выполнить 45 live captures, exact CHALK audit и визуальную оценку покрытия.
- План: [FILL-001 — area fill radius efficiency](CHALK_FILL_AREA_RADIUS_EFFICIENCY_PLAN_2026-11-03.md).

**INT-007 остаётся BLOCKED.** Не менять production estimator, frozen INT-006 model, executor defaults или sampling defaults до закрытия расширенной validation и решения о safety margin.

## Статус аналитических планов

Аналитический план этапов 7–10 отменён пользователем 31 октября 2026 г. Эти этапы не переносятся в настоящий roadmap и не должны возобновляться автоматически. См. [архивный план](../PROJECT_ANALYSIS_PLAN_10_STAGES.md).

## Фаза 1. Базовая документация

- [x] Создать единый индекс документации.
- [x] Описать верхнеуровневую архитектуру.
- [x] Составить первичный каталог исходных компонентов и тестов.
- [x] Описать основные каталоги данных и переменные окружения.
- [x] Описать локальный запуск, тестовые команды и Windows-сборку.
- [x] Создать файлы управления проектом.

## Фаза 2. Справочник исходников

- [x] Создать структурный справочник модулей preparation, executor и Game Monitor.
- [x] Документировать общие геометрические модели.
- [x] Завершить инвентаризацию интерфейсов всех 40 модулей preparation в [PREPARATION_API_REFERENCE.md](PREPARATION_API_REFERENCE.md).
- [x] Завершить справочник интерфейсов всех 13 модулей executor в [EXECUTOR_API_REFERENCE.md](EXECUTOR_API_REFERENCE.md).
- [x] Свести UI и интеграционные точки компонентов в [UI_INTEGRATION_MAP.md](UI_INTEGRATION_MAP.md).
- [x] Завершить карту импортов и точек входа: [DEPENDENCY_MAP.md](DEPENDENCY_MAP.md) содержит 40 preparation и 13 executor production-модулей; [TESTS_AND_CI_MAP.md](TESTS_AND_CI_MAP.md) содержит прямые импорты всех 46 найденных тестовых модулей.

## Фаза 3. Справочник форматов и хранилищ

- [x] Документировать формат проекта .autodraw.
- [x] Документировать JSON цветных scanline- и geometry-планов.
- [x] Документировать профиль палитры.
- [x] Документировать профили экранной области, исполнения и калибровки кисти.
- [x] Документировать формат журнала наблюдений paint-limit и снимок brush workflow.
- [x] Документировать JSON-схему экспорта Game Monitor.
- [x] Документировать форматы калибровочных входов/отчётов и ресурсных моделей.

## Фаза 4. Завершение комплекта

- [x] Завершить инвентаризацию прямых импортов 46 тестовых файлов (см. TESTS_AND_CI_MAP.md).
- [x] Проверить 67 относительных ссылок в 35 документах и наличие целевых файлов; якорные фрагменты не используются.
- [x] Сверить объявления интерфейсов 40 модулей preparation и 13 модулей executor с текущими исходниками; проверить ключевые сигнатуры, UI-точки и общие адаптеры.
- [x] Сверить каталог файлового хранилища с `integrated_app.py` и владельцами путей.
- [x] Проверить основной индекс документации и наличие всех его целей.
- [x] Проверить, что Git diff содержит только разрешённые Markdown-файлы; подтверждены шесть изменённых `.md`-файлов и отсутствие изменений исходников.
- [x] Зафиксировать итоговый HEAD и commit в WORK_LOG.

## Фаза 5. Сопровождение

### DOC-016 — инвентаризация документации (2026-11-03)

- [x] Перечислить и классифицировать Markdown-файлы `docs/` и корня Stage20.
- [x] Разделить действующие источники статуса и исторические планы.
- [x] Исправить несогласованные описания в основном индексе.
- [x] Зафиксировать правила сохранения архивных документов и единого источника текущего статуса.
- Отчёт: [DOCUMENTATION_INVENTORY_2026-11-03.md](DOCUMENTATION_INVENTORY_2026-11-03.md).


При последующих изменениях:
1. определить затронутые документы;
2. обновить описание интерфейса/формата вместе с изменением;
3. добавить запись в WORK_LOG;
4. добавить запись в CHANGELOG для значимых изменений;
5. обновить задачу в TASKS;
6. проверить ссылки и пути.

## Границы фаз 1–5 (завершённая документационная серия)

В фазы 1–5 не входили: анализ алгоритмов, аудит поведения, производительности, качества, безопасности, браузерные и игровые эксперименты, рефакторинг и исправление кода. Эти ограничения относятся к завершённой документационной серии и не отменяют фазу 6.


## Фаза 6. Измерение CHALK и ресурсная оптимизация

- [x] INT-001: статически инвентаризировать Brush Test UI, Game Monitor, игровой счётчик и модели стоимости AutoDraw.
- [x] INT-002: статически спроектировать контракт низкозатратного CHALK snapshot, baseline/delta и требования к Monitor.
- [~] INT-003: live WebSocket smoke handshake подтверждён артефактами `ready→pong`; Monitor 0.2.1 обнаружил игровую доску в iframe. A/B/C pointCount deltas: A=53/52/52, B=0*/52/52 (B-1 невалиден), C=50/52/52; в двух валидных повторениях все режимы дали 52, а diagnostic snapshot C совпал с точным счётчиком. FPS probes показывают 60 FPS, но не размечены по режимам, поэтому overhead не измерен. Boundary probe дал 4/4 визуально видимых штриха и ΔpointCount=52; точные горизонтальные acceptedPoint x=0/460 ещё не подтверждены. До раздельного A/B/C FPS/duration и проверки горизонтальных границ полную матрицу кистей не запускать.
- [~] INT-004: добавлен первый read-only WebSocket bridge: event subscription, автоматические run JSON, точные pre/post CHALK snapshots, acceptedPoint и per-stroke FPS. Brush Test UI теперь автоматически прикрепляет подходящий run JSON к `experiment.json` по времени `before_draw` и радиусу. Остались live Firefox validation, проверка корреляции и overhead bridge.
- [~] INT-005: параметрический G3 generator/block runner реализован для `paint_consumption_long_lines` (27 задач, 9 сочетаний `point_step_px`/`point_delay_ms`, 3 повтора); G1 (12/12) и G2 (18/18) приняты live. Осталось выполнить локальный preflight и live G3, затем расширять матрицу на другие параметры кисти/траектории.
- [ ] INT-006: построить и валидировать модель прогноза расхода игровых точек, отделяя измерение от оценки.
- [ ] INT-007: интегрировать модель в preflight/resource estimator AutoDraw.
- [ ] INT-008: оптимизировать кисти, траектории, порядок и покрытие при ограничении CHALK.
- [ ] INT-009: сравнить прогноз с фактическим расходом и оценить качество рисунка.

**Критерий итоговой цели:** AutoDraw до исполнения оценивает расход в игровых единицах, выбирает вариант рисования с резервом по квоте и после исполнения сопоставляет прогноз с фактом.

**Границы:** документирование результатов выполняется сразу. Изменение исходного кода и запуск тестов/игровых экспериментов требуют отдельного разрешения.


## Актуализация фазы 6 — G3 software gate закрыт (2026-11-01)

- [x] Программная реализация G3: 27 задач, девять комбинаций шага/задержки, три повтора, строгая идентичность, журналирование, UI и analyzer.
- [x] Полный GitHub Actions CI на HEAD `3dbf8f20bcea44c61290e49398e1a4daf182dbf9`: run [41340237207](https://github.com/Kiddos19882/AutoDraw/actions/runs/41340237207), все три jobs success.
- [x] Windows portable build/startup smoke-test пройден на GitHub-hosted runner.
- [ ] Локальный Windows preflight на рабочей машине.
- [ ] Live G3 block — 27/27 подтверждённых captures.
- [ ] Анализ CHALK по девяти конфигурациям; только после этого валидировать ресурсную модель.
- [ ] Расширить матрицу на независимые параметры размера кисти, траектории и покрытия, если результаты G3 покажут необходимость.

**Граница:** software gate не закрывает live gate. Фактическое влияние шага и задержки на расход CHALK пока не установлено.

## 2026-11-02 — G3 software gate: оптимизация CI

- [x] Разделить обязательные Game Monitor, Preparation/G3, Integration и Executor regression suites на параллельные jobs.
- [x] Отложить тяжёлые Stage 5/7/8 benchmarks до ручного workflow_dispatch.
- [x] Гейтировать portable build успешным завершением всех test jobs и убрать повторный прогон тех же suite только в CI.
- [x] Добавить G3 UI plan-routing test, проверяющий block identity, matrix identity и task-specific executor parameters.
- [ ] Подтвердить полный CI на конечном code HEAD.
- [ ] Получить portable artifact и провести локальный Windows preflight.
- [ ] Закрыть прежний paused journal только через recovery UI после проверки доски.
- [ ] Выполнить новую чистую серию G3 — 27/27 подтверждённых captures.
- [ ] Рассчитать расход CHALK отдельно для девяти комбинаций sampling и проверить влияние на ресурс.


## 2026-11-02 — live G3 принят, переход к модели CHALK

G3 block `chalk-20261102-031830-a0f325` завершён: 27/27 captures приняты. Девять конфигураций `point_step_px` 1/2/4 × `point_delay_ms` 5/10/20 имеют по три повтора. Все captures содержат exact CHALK и чистые per-run transport gates. Полный анализ: [CHALK_G3_RESULTS_2026-11-02.md](CHALK_G3_RESULTS_2026-11-02.md).

- [x] INT-005: параметрическая G3 матрица исполнена live, все 27 captures приняты, расход по девяти конфигурациям рассчитан.
- [~] INT-006: построить сегментированную модель прогноза CHALK. G3 даёт сценарные коэффициенты для длинных горизонтальных линий; перенос на другие типы геометрии не подтверждён.
- [ ] INT-007: интегрировать валидированную модель в preflight/resource estimator AutoDraw.
- [ ] INT-008: оптимизировать кисти, траектории, порядок и покрытие при ограничении CHALK.
- [ ] INT-009: сравнить прогноз с фактическим расходом и оценить визуальное качество.

**Экспериментальный кандидат:** `point_step_px=4` и `point_delay_ms=5` или `10` дали около 365 CHALK на шесть длинных линий. До визуальной проверки непрерывности и качества не назначать этот режим универсальным default.


## 2026-11-02 — INT-006: предварительная модель CHALK

- [x] Приняты G1/G2/G3 live blocks и radius matrix.
- [x] Подготовлена предварительная сегментированная модель: прямые штрихи, короткие штрихи, sampling profile, радиус и повторное покрытие.
- [x] Задокументирована линейная оценка для прямых сегментов при radius=10, step=2, delay=10: `C ≈ 1.765 + 0.2988 × L`.
- [x] Закрыть визуальную проверку G3 step=4: шесть PNG длинных горизонтальных линий визуально непрерывны; pixel-level audit V1–V5 также завершён на 90 captures.
- [ ] Выполнить независимую проверку прогноза на новых рисунках, получить error distribution и консервативный safety margin.
- [ ] После validation перейти к INT-007 — интеграции проверенной оценки в preflight/resource estimator.

**Исторический статус на момент записи 2026-11-02:** IN_PROGRESS до получения официального analyzer report. Текущий статус и закрытие quantitative gate приведены в разделе «Актуальный статус INT-006 — 2026-11-03» выше.


## 2026-11-02 — G3 visual quality audit

- [x] Просмотрены все шесть PNG step=4/delay=5 и step=4/delay=10.
- [x] Подтверждена визуальная непрерывность длинных горизонтальных линий во всех шести повторах.
- [x] Сопоставлены расход CHALK и длительность: оба delay практически эквивалентны.
- [ ] Проверить step=4 на диагоналях, коротких штрихах, поворотах и пересечениях.
- [ ] Получить независимую validation CHALK estimator и error distribution.

**Статус:** G3 visual gate и V1–V5 geometry/pixel audit закрыты. INT-006 остаётся IN_PROGRESS только до независимой validation CHALK-модели и safety margin. Production defaults не изменять.


## Актуальный план после принятия G1/G2/G3 — 2026-11-02

Предыдущие записи фаз и gates ниже/выше сохраняются как история. Текущая последовательность определяется [CHALK_NEXT_STEPS_PLAN_2026-11-02.md](CHALK_NEXT_STEPS_PLAN_2026-11-02.md).

- [x] G1: 12/12 принятых опытов.
- [x] G2: 18/18 принятых опытов.
- [x] G3: 27/27 принятых опытов; девять sampling combinations × три повтора.
- [x] Radius matrix: 21 принятый опыт; в конкретном сценарии длинных линий систематическое влияние радиуса на exact CHALK не обнаружено.
- [x] Построена предварительная сегментированная модель CHALK; production estimator не готов.
- [x] Визуально просмотрены все шесть PNG step=4/delay=5 и step=4/delay=10; длинные горизонтальные линии визуально непрерывны.
- [x] Геометрическая validation step=4: live follow-up диагоналей, коротких штрихов, поворотов, замкнутых контуров и пересечений; pixel-level audit 90 captures подтверждает покрытие и отсутствие gaps.
- [ ] Независимая validation модели на новых рисунках с MAE/RMSE/bias/relative error.
- [ ] Определить safety margin и правила неизвестной/непроверенной геометрии.
- [ ] INT-007: интегрировать validated estimator в preflight.
- [ ] INT-008/INT-009: оптимизация траекторий/покрытия и проверка фактического выигрыша.
- [ ] Отдельно закрыть INT-003: сопоставимое A/B/C измерение overhead Game Monitor.

**Порядок:** геометрическая validation → независимая validation estimator → safety margin → INT-007 → INT-008/009. Production defaults не менять до закрытия соответствующих gates.


## INT-006 — текущая фиксация (2026-11-02)

INT-006 остаётся IN_PROGRESS. Harness V1–V5 и пять live follow-up block series завершены: 45/45 новых captures, exact CHALK/Monitor integrity приняты. Series-aware pixel audit обработал 90 исходных + follow-up captures, 0 invalid/duplicate/missing/unexpected; 297/297 новых stroke rows имеют coverage=1.0 и zero gaps. Следующий gate — независимая validation модели CHALK на полных DrawingPlan и критерии safety margin.

Harness V1–V5: matrix metadata/validator, block planner/journal, Brush Test UI и task-specific executor override; regression tests прошли. Full CI run 41496555297 включая Windows portable smoke-test и PNG audit — success. Production executor defaults и estimator не менять.


## 2026-11-02 — INT-006 PNG screening progress

- [x] Просмотрены 15 representative PNG V1–V5 × P0/P1/P2.
- [x] Зафиксированы ограничения исходной геометрии и отсутствие очевидного визуального ухудшения непрерывности step=4 в выбранных примерах.
- [x] Выполнить количественный pixel-level аудит всех 90 PNG: continuity/max gap, centerline deviation, coverage width/variation, contour closure, parallel separation; 549 stroke rows и 900 pair rows.
- [x] Проверить segmentation masks на blank-board reference и cursor exclusion; для новых 45 captures cursor_detected=false, cursor_exclusion_pixels=0.
- [x] Выполнить targeted reruns исправленных V1/V3, V2 short-stroke, V4 closure и V5 spacing; 45/45 captures завершены.

Исторический скрининг: [CHALK_INT006_PNG_SCREENING_2026-11-02.md](CHALK_INT006_PNG_SCREENING_2026-11-02.md). Follow-up exact CHALK и pixel audit: [CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md](CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md). INT-006 остаётся IN_PROGRESS только до independent validation/safety margin; production defaults/estimator не менять.


## Актуальное уточнение INT-006 — 2026-11-02

Геометрические follow-up V1–V5 и pixel audit завершены. Следующий аналитический gate — независимая validation замороженных моделей P0/P1/P2 на новых DrawingPlan; план эксперимента находится в `CHALK_INT006_INDEPENDENT_VALIDATION_PLAN_2026-11-02.md`.

Программный gate legacy-journal compatibility закрыт: run `41496555297` checkout рабочей ветки после commit `956ce2b`, содержащего commits `f0e05df` и `4847cce` в истории. Preparation/G3 завершился 662 passed и 82 subtests passed; все обязательные jobs, Windows portable build и PNG audit успешны.


## 2026-11-02 — readiness audit независимой validation

- [x] Подтвердить по исходникам отсутствие D1–D5 в matrix contract, block planner/journal, Brush Test UI и executor override allowlist.
- [x] Зафиксировать, что analyzer пока не сравнивает accepted captures с immutable frozen predictions.
- [x] Исправить статус D1–D5 protocol на BLOCKED; создать отдельный readiness audit.
- [ ] Расширить существующий harness отдельной INT006 phase, не меняя production estimator/defaults.
- [ ] Пройти полный CI и Windows portable smoke-test; затем передать локальную инструкцию preflight.


## 2026-11-02 — INT-006 software gate PASS

- [x] D1–D5 matrix/UI/executor handoff и 45-cell block journal.
- [x] 15 frozen prediction records и hash-sealed journal artifact.
- [x] Независимый analyzer exact CHALK с run-level/per-stroke metrics.
- [x] Regression tests для artifact, geometry, matrix cells и handoff.
- [x] Full CI [41513389663](https://github.com/Kiddos19882/AutoDraw/actions/runs/41513389663): 667 passed, 82 subtests; pixel audit и Windows portable build/startup smoke-test success.
- [ ] Локальный Windows 10 preflight.
- [ ] 45 live captures и анализ safety margin.
- [ ] INT-007 integration только после принятия результатов INT-006.

Подробности: [frozen predictions/analyzer](CHALK_INT006_FROZEN_PREDICTIONS_AND_ANALYZER_2026-11-02.md), [local preflight](CHALK_INT006_LOCAL_PREFLIGHT_GUIDE_2026-11-02.md).


## Актуальный статус INT006R — 2026-11-03

- [x] Выделена отдельная фаза INT006R с новыми D1–D5 scenario IDs, чтобы не смешивать её с frozen INT-006 radius=10 journal/model.
- [x] Добавлен 45-cell planner: D1–D5 × radius 1/10/30 × 3 повтора; sampling фиксирован на P1 (step=4, delay=5 ms).
- [x] Добавлены strict journal validation, UI aliases, task-specific radius selection и fail-closed executor handoff.
- [x] Добавлен отдельный analyzer exact CHALK и regression tests для matrix/journal/analyzer/handoff.
- [x] Полный CI [41540054975](https://github.com/Kiddos19882/AutoDraw/actions/runs/41540054975) на code HEAD `28b56a9` завершился SUCCESS: 682 passed, 82 subtests, application/executor/bridge/PNG audit и Windows portable build/startup smoke-test — success.
- [ ] Выполнить локальный Windows preflight и после его PASS провести 45 live captures; live block ещё не запускался.
- [ ] Проверить 45 пар before/after PNG вручную, закрыть visual quality gate и оценить radius × geometry interaction отдельно по каждой геометрии; при обнаружении эффекта добавить промежуточные радиусы.

**Текущий gate:** SOFTWARE PASS. **Live gate:** BLOCKED до локального Windows preflight. Frozen INT-006 model, production estimator/defaults и master не менялись.


## Историческая запись roadmap до реализации FILL-001 UI/runner — 2026-11-03

Нельзя переходить сразу к Windows preflight: текущий интерфейс Brush Test не создаёт FILL-001 task, а Stage 6 hook лишь связывает runtime evidence после уже завершённого запуска. Следующий engineering increment — отдельный FILL-001 UI/runner, task-to-DrawingPlan conversion, experiment-context propagation и task-specific P1 override. Требования и acceptance criteria записаны в [аудите интеграции](CHALK_FILL001_AUTODRAW_INTEGRATION_AUDIT_2026-11-03.md).

До закрытия этого increment и последующего Windows preflight live captures не запускать; matrix flags `execution_allowed=false` и `safe_to_execute=false` сохранять.


## FILL-001 — актуальный gate после CI run 41692129486 (2026-11-03)

1. Software regression и UI/runner integration: PASS. Run [41692129486](https://github.com/Kiddos19882/AutoDraw/actions/runs/41692129486) завершился SUCCESS, включая Windows portable build/startup smoke-test.
2. Portable artifact доступен: [autodraw-g3-preflight-build, ID 13258221572](https://github.com/Kiddos19882/AutoDraw/actions/runs/41692129486/artifacts/13258221572).
3. Следующий шаг — один Windows live preflight `rectangle / radius 10 / repeat 1`, выполняемый пользователем. Проверить runtime binding и визуальные evidence на реальном client ROI.
4. До принятия preflight 45 live captures и CHALK/quality analysis остаются BLOCKED.

Не менять production estimator/defaults и не считать CI/synthetic tests доказательством поведения в игре.


## 2026-11-04 — CI run 41780241017: software gates PASS, evidence gates частично открыты

1. Run [41780241017](https://github.com/Kiddos19882/AutoDraw/actions/runs/41780241017) — SUCCESS для всех обязательных jobs, включая Preparation/G3, INT-006 PNG audit и Windows portable build/startup smoke-test; optional benchmarks SKIPPED.
2. FILL-001-RS static sweep: 15/15 selected shape×radius cells прошли offline raster gate (coverage≥99%, leakage=0). Это не exact CHALK и не live renderer evidence.
3. INT-006 PNG audit: 90/90 valid captures, 549 stroke rows, coverage=1.0, zero gaps. Frozen CHALK analyzer: 45/45 accepted, но safety margin не установлен и production eligibility не validated.
4. INT006R: 45/45 radius×geometry captures accepted; exact CHALK differences для radius 1/10/30 малы и немонотонны. PNG artifact полный, но ручной visual quality gate остаётся pending для 45/45 captures.
5. Следующие действия: (а) вручную проверить 45 пар INT006R PNG; (б) определить safety margin и границы frozen CHALK model; (в) отдельно пройти FILL-001-RS capture/replay gate. Не менять production estimator/defaults по результатам только этого CI.

## Следующий диагностический increment FILL-001-RS — edge pixels и contour candidate (2026-11-04)

Offline повторение planner model локализовало её 304 uncovered pixels исключительно в краевых зонах (top=80, bottom=80, left-middle=72, right-middle=72; interior=0). Это согласуется с приоритетом проверки краёв, но не объясняет actual PNG audit: corrected capture по-прежнему имеет coverage=98.430600% и leakage=11, а координатный breakdown этих actual pixels ещё не выполнен.

Выполнен отдельный exploratory sweep одного замкнутого contour pass после текущих 27 scanlines. В OpenCV raster model inward offsets 6, 7 и 8 px дали coverage 99.516270%, 99.372942%, 99.328153% при leakage=0; offset 5 px дал 32 leakage pixels. Это кандидат для дальнейшей проверки, а не утверждённый алгоритм: модель не является игровым renderer, executor contour lifecycle не проверен, CHALK не измерялся.

**Порядок действий:**
1. Завершить actual PNG coordinate breakdown: uncovered target pixels по четырём границам/углам/центру и все 11 leakage pixels.
2. Сопоставить actual coordinates с plan endpoints, affine transform и возможным renderer cap/footprint.
3. Если край подтверждается, исследовать contour pass как отдельную versioned offline geometry candidate; не изменять frozen plan и thresholds.
4. После offline gate — только отдельный разрешённый live preflight; затем отдельное решение о 45-cell matrix.

До этого capture остаётся REJECTED/BLOCKED; production code/defaults и live execution не менять.
## FILL-001-RS diagnostic continuation — 2026-11-04

1. Use the confirmed actual PNG residual map as baseline: 1116 uncovered pixels, all in configured perimeter zones; 0 in interior/other. Right perimeter dominates (499 in right-middle; largest component area 870 at screen bbox [460,63,33,178]).
2. Inspect engine-side brush rendering and executor point sampling to establish actual screen-space footprint, endpoint cap behavior, and radius units. Keep the current interpretation as a hypothesis until verified.
3. Evaluate perimeter/contour additions and endpoint adjustments as separate offline candidates. Preserve frozen plan and acceptance thresholds.
4. Only after a candidate passes independent PNG geometry audit, perform a separately authorized live preflight and measure exact CHALK by pointCount delta.
5. Unlock the 45-experiment matrix only after successful preflight acceptance.

Current evidence does not justify changing scanline row spacing: diagnostic reports 0 residual pixels in interior/other, while edge zones contain all 1116.


**Дополнение 2026-11-04:** сохранённый run показал accepted-point cadence около 29 updates/s при browser requestAnimationFrame около 60 FPS. Browser probe и игровые point updates теперь разделяются в Bridge schema. Egret bundle задаёт nominal stage.frameRate=48; фактическая частота принятия координат в run ниже и должна измеряться per-stroke.


## Отдельный offline workstream — BRUSH-FOOTPRINT-CAPSULE-001

**Offline geometry candidate и broad-phase benchmark реализованы; renderer/planner acceptance остаётся OPEN.**

В `brush_footprint_geometry.py` добавлена отдельная ideal round-capsule swept-polyline model с двумя наборами клеток: potential (positive-area intersection, safety/leakage envelope) и guaranteed (conservative coverage under-approximation). Per-segment broad phase ограничивает raster enumeration расширенным AABB каждого сегмента; global bounds и union semantics API сохранены.

Независимый full-canvas oracle использует собственные геометрические функции и сравнивает оба набора клеток. Дополнительно benchmark сравнил global-AABB reference с per-segment вариантом на пяти synthetic polylines (7 timing repeats); masks совпали во всех случаях. Candidate slots сокращены на 59.53–96.23% в четырёх многосегментных сценариях, без сокращения для одного длинного сегмента. Median wall-clock speedup в Windows CI runner составил 2.76–20.57× для многосегментных сценариев и 1.16× для одного сегмента. Детали и limitations записаны в [TASKS.md](TASKS.md#brush-footprint-capsule-001--per-segment-broad-phase-independent-oracle-и-benchmark-2026-11-04).

**Оставшиеся gates:**
1. Подтвердить deployed Egret runtime/version, фактический render path и caps/joins.
2. Получить popup BoardPane global transform и screen/canvas mapping.
3. Сравнить masks с frozen renderer PNG fixtures; проверить endpoints, joins, соседние цвета и canvas boundaries.
4. Только после offline renderer acceptance отдельно рассмотреть planner integration; не менять production outputs/defaults заранее.
5. Live PNG calibration — только после offline gate и отдельного разрешения.

Это отдельный риск generic planner-моделей; не считать причиной FILL-001-RS scanline capture без прямого подтверждения. Модель не измеряет CHALK и не доказывает renderer equivalence.


## Единый реестр тестирования

Результаты проверок и экспериментов: [TEST_RESULTS.md](TEST_RESULTS.md). Roadmap содержит последовательность работ и gates.

## Дополнение — capsule model per-segment broad-phase и benchmark (2026-11-04)

В `swept_capsule_pixel_masks()` сохранена union-семантика potential/guaranteed masks, но candidate enumeration выполняется в расширенном AABB каждого сегмента, а не во всём global polyline AABB. Добавлены независимый full-canvas geometry oracle (ориентационный тест пересечения сегментов с прямоугольником и собственная point-segment distance реализация), seven parametrized edge cases и 16 воспроизводимых seeded polylines.

Offline benchmark сравнил global-AABB reference и per-segment реализацию на пяти типах полилиний, по 7 timing repeats. Во всех случаях masks совпали. Candidate slots уменьшились на 91.09% для winding, 96.23% для large zigzag, 59.53% для diagonal turns и 92.24% для compact polyline; для single segment сокращения нет. Медианное wall-clock ускорение в Windows GitHub runner: 10.91×, 20.57×, 2.76×, 14.10× и 1.16× соответственно. Это результаты пяти synthetic scenarios, не универсальная гарантия.

Полный CI [41859709320](https://github.com/Kiddos19882/AutoDraw/actions/runs/41859709320) на HEAD `af30b5fdf1c926d3493bff90706806f5d3a28c43` — SUCCESS: Preparation/G3 832 passed, 24 warnings, 82 subtests; Game Monitor/Bridge, Executor, Application integration, INT-006 PNG audit и Windows portable build/startup smoke-test — SUCCESS; optional algorithm benchmarks — SKIPPED. Capsule benchmark artifact: `13338434277`; FILL-001-RS static sweep artifact: `13338359373`.

Модель остаётся offline ideal-geometry candidate. Deployed Egret renderer/transform не подтверждены; planner integration и live capture не выполнялись. Benchmark не измеряет игровой CHALK и не доказывает renderer equivalence.

---

## Дополнение — аудит BRUSH-FOOTPRINT-CAPSULE-001 (2026-11-04)

Статически подтверждено, что generic `interior_fill_planner` использует AABB bounds не только для color-safety, но и как уже покрытую область (`_mark_footprint`). Для круглой capsule кисти AABB содержит угловые клетки, которые не принадлежат фактическому footprint; они могут ошибочно исключаться из fallback, завышая модельное coverage. Тестовый oracle также моделирует прямоугольник, а не независимую capsule.

Область влияния ограничена generic experimental modules: `swept_footprint_geometry` использует bbox как conservative safety envelope, `outline_first_fill_planner` — для safety check. FILL-001/FILL-001-RS используют отдельный OpenCV round-capped rasterizer и не вызывают `footprint_pixel_bounds`; прямую причинную связь с rejected FILL-001-RS capture не установлено. Deployed Egret runtime и реальный footprint остаются UNKNOWN. Код/тесты не менялись; следующий шаг — offline possible/guaranteed pixel-cell masks и frozen-fixture comparison.

---

## Актуальная сводка — 2026-11-04, CI и telemetry

- Рабочая ветка: `feature/image-geometry-optimization`; последний проверенный code/test HEAD: `af30b5fdf1c926d3493bff90706806f5d3a28c43`. После него добавлены только документационные commits (включая `152ae55`); compare на code/test HEAD — ahead 2945 / behind 5 относительно `master`. Merge/rebase не выполнялся, `master` не изменялся. Локальный `git status` недоступен через GitHub API.
- Workflow [41840582147](https://github.com/Kiddos19882/AutoDraw/actions/runs/41840582147) завершился **SUCCESS**. Run checkout SHA `6fd3c91c3c08ea05cb9ef83ff599eb52a6f9527e`; после него в ветке добавлены только документационные commits до HEAD `7ff5813`. Application integration, Game Monitor/Bridge, Preparation/G3, Executor regression, Windows portable build/startup smoke-test и INT-006 PNG audit — SUCCESS; optional algorithm benchmarks — SKIPPED. Артефакты: static sweep `13329415914`, INT-006R validation `13329411251`, INT-006 PNG `13329261288`, CHALK validation `13329096463`, visual review source `13328976562`, Windows build `13328458043`.
- Run `41840281018` на HEAD `730590d` был отменён (CANCELLED), а не провален. Его успешные отдельные jobs не заменяют полный CI. Run `41840582147` — подтверждённый полный SUCCESS для telemetry code lineage.
- Per-stroke telemetry проверена по исходникам: Browser Bridge передаёт `strokeId` и raw requestAnimationFrame intervals; Bridge Server сохраняет `frame_probes`, формирует `frame_probe_by_stroke` и `per_stroke_metrics`. Важно: browser rAF — не Egret `ENTER_FRAME`; события `POINT_QUOTA_UPDATE` отражают изменения resource snapshot/принятые point updates, а не каждый кадр.
- Сохранённый старый run `6a17a297` даёт 1260 point updates, median интервал 33 ms, cadence 28.26–29.50 points/s; первые/последние 9 штрихов — 28.734/29.049 points/s. Старые per-stroke rAF intervals не сохранены старым finalizer, поэтому новую frame_probe корреляцию нужно получить в будущем run после прохождения offline gate.
- Уточнён статический renderer context: nominal stage.frameRate=48, StageScaleMode.NO_SCALE; PainterPopup 676×379, BoardPane 460×240 без собственного scaleX/scaleY. Это не определяет parent/global transform и device-pixel ratio. Egret 5.2.18 API указывает ROUND defaults для omitted caps/joints, но deployed runtime version не установлена; zero-length rasterization и фактический footprint остаются UNKNOWN.
- FILL-001-RS остаётся **BLOCKED**: capture REJECTED, coverage=98.430600%, leakage=11; exact CHALK=1260 (pointCount 1→1261) относится только к этому запуску. Критерии coverage≥99% и leakage=0 не выполнены. 45-task matrix не открывать.
- Следующий gate: установить deployed Egret runtime identity, измерить popup global transform, отдельно проверить zero-length path rasterization и откалибровать фактический screen-space footprint на frozen geometry. Live preflight и 45-task matrix не запускать до прохождения offline gate; frozen plans/masks/thresholds/defaults не менять.

---

## Текущий блокирующий шаг: FILL-001-RS калибровка renderer footprint и sampling

**Задача:** FILL-001-RS-ENGINE-FOOTPRINT-001.  
**Статус:** IN PROGRESS / BLOCKER. Pixel-level локализация завершена; исходный capture остаётся REJECTED (coverage=98.430600%, leakage=11). До принятия нового preflight 45-task matrix заблокирована. Live experiments в текущем исследовательском шаге не выполнялись.

Исходный run fill001-rs-preflight-20261104-7.04: 27/27 strokes, pointCount 1→1261, exact CHALK=1260. Corrected PNG diagnostic: 1116 uncovered target pixels; top=244, bottom=239, left-middle=134, right-middle=499, interior/other=0; leakage=11. Основной остаток расположен на правом периметре. Это локализует дефект как perimeter-dominant, но не доказывает конкретную форму кисти или окончаний.

**Новый статический анализ движка:** полный bundle прочитан через GitHub Contents API. Источник master commit 9a3453aeb847b66041bc83d6f4a56ecaf33a993a, blob 28838e803dcc6f85efb13febd93cc9e0f5046ffc. Подтверждены ENTER_FRAME sampling, dedup одинаковых соседних точек, O(N) пересчёт updateLess() на каждый принятый sample, передача brush value как line thickness и smooth-path behavior. Round caps/joins подтверждены для Egret 5.2.18 API и текущего upstream GraphicsNode/CanvasRenderer reference; exact deployed runtime version ещё не установлена. Для совместимого CanvasRenderer одноточечный zero-length path не окрашивается по Canvas path algorithm, хотя точка расходует CHALK. Popup global transform остаётся UNKNOWN. Подробности: [engine audit](CHALK_GAME_ENGINE_POINT_COST_AND_BRUSH_WIDTH_2026-11-03.md).

**Следующий offline gate:** frame_probe теперь сохраняется per-stroke для будущих запусков; для старого run принятая point cadence уже восстановлена из POINT_QUOTA_UPDATE. Установить deployed Egret runtime identity, проверить zero-length rasterization, измерить global transform painter popup BoardPane и откалибровать фактический screen-space footprint. После этого построить versioned perimeter candidate и проверить frozen PNG acceptance mask. Не менять frozen plan, masks, thresholds, production defaults и не запускать live capture до прохождения offline gate.

**Дополнительные данные сохранённого run 6a17a297:** 1260 POINT_QUOTA_UPDATE events распределены по 27 штрихам. Каждый штрих принял 41–48 точек за 1450–1645 ms; median интервал между изменениями pointCount — 33 ms; accepted-point rate 28.26–29.50 points/s. Первые 9 штрихов: 28.734 points/s в среднем; последние 9: 29.049. В run-level frame_probe browser requestAnimationFrame измерен как 59.997 FPS; это не частота Egret ENTER_FRAME. На данном запуске не видно падения cadence от роста pointCount 1→1261, но это не исключает overhead на более длинных runs.

**Улучшение телеметрии внесено:** Browser Bridge теперь передаёт strokeId для frame_probe; Bridge Server сохраняет raw per-probe intervals и формирует per_stroke_metrics / frame_probe_by_stroke. Изменения: 02907aca (browser bridge), ec2ed77 (collector), ead8808/730590d (tests). Run 41840281018 завершился CANCELLED; последующий полный CI run 41840582147 завершился SUCCESS для этого telemetry code lineage. Актуальная сводка и ограничения приведены в начале файла.

# Текущее состояние проекта

## Актуальное состояние на 2026-11-04

## FILL-001-RS — CI failure и исправление тестовых fixtures — 2026-11-04

Run [41778045384](https://github.com/Kiddos19882/AutoDraw/actions/runs/41778045384) завершился FAILURE в Preparation/G3: 799 passed, 5 failed, 24 warnings, 82 subtests. Game Monitor/Bridge, Application integration и Executor regression — SUCCESS; PNG audit и Windows portable build skipped. Пять падений связаны с synthetic PNG fixtures, не соблюдавшими executor transform, и non-uniform ROI test, который падал до вызова audit.

Test-only fixes committed: [1f28436](https://github.com/Kiddos19882/AutoDraw/commit/1f28436ab20fe949e4d53cfeea4a5560ed3cbcae), [0f23731](https://github.com/Kiddos19882/AutoDraw/commit/0f23731848f0c148fe5e1309d1e305576dd4b6b7). Production source, frozen masks и acceptance thresholds не менялись. Последующий CI [41780241017](https://github.com/Kiddos19882/AutoDraw/actions/runs/41780241017) завершился SUCCESS и выполнил replay исходных PNG: coverage=98.430600%, leakage=11, audit failed. Capture remains BLOCKED; 45-task matrix BLOCKED.

## Дополнение — независимая проверка executor transform — 2026-11-04


Дополнительно проверен полный GitHub Actions run [41772866679](https://github.com/Kiddos19882/AutoDraw/actions/runs/41772866679), который в исторической записи связан с code/test HEAD `974f949`. Все 6 обязательных jobs завершились SUCCESS: Game Monitor/Bridge, Application integration, Preparation/G3, Executor regression, Windows portable build/startup smoke-test и INT-006 PNG audit; optional benchmarks SKIPPED. Preparation/G3 включал запуск `pytest -q -ra tests` и exhaustive static sweep; artifact `autodraw-fill001-rs-static-sweep` сохранён.

Этот CI предшествует affine correction commits `4797aa5`, `a950084` и независимому test commit `c399433`; он **не валидирует** эти изменения. Текущий workflow запускается на push по `source/**`, поэтому source/test commit должен инициировать CI, но доступный GitHub connector не предоставляет push-triggered run listing. `fetch_commit_workflow_runs` ограничен PR-triggered runs; отсутствие результата от него не означает, что push run отсутствует.

CI [41780241017](https://github.com/Kiddos19882/AutoDraw/actions/runs/41780241017) на HEAD `0f23731` выполнил regression suite и replay исходных PNG. В логе зафиксировано coverage=98.430600%, leakage=11; binding PASS, PNG gate FAIL. Исправленный affine transform используется, но остаточное расхождение ещё требует координатной локализации.


## FILL-001-RS — согласование координат PNG audit — 2026-11-04

В live preflight серии `fill001-rs-preflight-20261104-7.04` runtime binding подтверждён: rectangle/r10/step=5/offset=0, 27/27 штрихов, observed radius=10, exact CHALK=1260 (pointCount 1→1261). Bridge diagnostics: 0 sequence gaps, 0 dropped events, 0 Monitor errors, 0 send failures. Capture отклонён исходным PNG audit: coverage=97.673218%, leakage=28.

Статический разбор обнаружил несовпадение преобразований logical canvas 460×240 в ROI 581×304: executor использует (width−1)/460 и (height−1)/240, а PNG audit ранее использовал PIL.resize с width/460 и height/240. Это разные affine transforms. На frozen rectangle mask два raster masks различаются на 606 screen pixels. Это подтверждает дефект выравнивания validation mask, но само по себе не доказывает, что им объясняется вся потеря coverage или leakage.

Исправление: [4797aa5](https://github.com/Kiddos19882/AutoDraw/commit/4797aa5e2e3d9f78656c91dcddf285304eae55c1) согласует PNG mask rasterization с executor transform; [a950084](https://github.com/Kiddos19882/AutoDraw/commit/a950084db14fd1560aa15f099da4a0108c9631e7) обновляет regression fixture/assertions.

**Проверка после исправления выполнена:** CI [41780241017](https://github.com/Kiddos19882/AutoDraw/actions/runs/41780241017) на HEAD `0f23731` повторно обработал исходную PNG пару: coverage=98.430600%, leakage=11. Affine correction улучшила результат относительно старого audit (97.673218% / 28), но gate не пройден. Остаточная причина не установлена; требуется offline breakdown по координатам. Capture и 45-task matrix остаются BLOCKED.


## FILL-001-RS — runtime binding и PNG audit по live evidence — 2026-11-04

Пользовательский evidence commit [5308214](https://github.com/Kiddos19882/AutoDraw/commit/530821497ce3a6bd5152318a78e1f06cb836f288) содержит завершённый single-task run rectangle/r10/step=5/offset=0: 27/27 штрихов, radius=10, exact CHALK = 1261 − 1 = 1260. Bridge run `6a17a297-ea14-4527-9527-bfd8de3bd335` завершён без dropped events, Monitor errors, Bridge send failures и sequence gaps.

Причина сообщения «Runtime binding пока не готов» найдена в discovery: в хранилище присутствовала legacy Bridge session `3323cf8e-01ca-4009-8f16-27d657d857f8` от 2026-10-31 без `schema_version=2` и `bridge_diagnostics`. Она не могла удовлетворить FILL-001 contract, но классифицировалась как незавершённая потенциальная session и блокировала найденную актуальную запись. Исправление [a7e37d6](https://github.com/Kiddos19882/AutoDraw/commit/a7e37d6eb0031094ffd962bc11ef01860a3af74a): discovery пропускает несовместимые legacy schemas до pending-классификации; неполные schema-v2 sessions по-прежнему остаются pending, неоднозначность не ослаблена.

Добавлен replay test [974f949](https://github.com/Kiddos19882/AutoDraw/commit/974f949e9639acc90e7f4d6f4588c3fb96f9abb2), который передаёт реальные manifest, attempt, executor report, две Bridge run records, session и before/after PNG через обработчик `Fill001Tab.finalize_capture()`. Тест включает старую legacy session и подтверждает успешную runtime binding: run ID совпадает, exact CHALK=1260.

**Capture не принят:** первоначальный audit до affine correction получил coverage **97.673218%** и leakage **28 pixels**. Повторный audit на исходных PNG с исправленным transform в CI [41780241017](https://github.com/Kiddos19882/AutoDraw/actions/runs/41780241017) получил coverage **98.430600%** и leakage **11 pixels**. Оба результата не проходят неизменённые условия ≥99% / 0; capture pending, CHALK=1260 не заменяет PNG quality gate. См. [отчёт replay](CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md).

Полный CI [41772866679](https://github.com/Kiddos19882/AutoDraw/actions/runs/41772866679) на code/test HEAD `974f949`: Preparation/G3 — 804 passed, 24 warnings, 82 subtests; Executor, Game Monitor/Bridge, Application integration, INT-006 pixel audit и Windows portable build/startup smoke-test — SUCCESS; optional benchmarks — SKIPPED.

Следующий приоритет — анализ фактического PNG относительно frozen mask, screen ROI и transform, устранение причин недопокрытия/выхода за границу. Capture и 45-task matrix остаются BLOCKED до повторного прохождения coverage≥99%/leakage=0.


## Исправление FILL-001-RS frozen geometry rebuild — 2026-11-04

Пользовательский runtime evidence commit [63158fb](https://github.com/Kiddos19882/AutoDraw/commit/63158fb55743c566bf231196b80016273970bbf1) зафиксировал отказ single-task preflight до запуска исполнителя. Для задачи rectangle/r10 manifest и исходный DrawingPlan согласованы: planner_version=2, scanline_row_step=5, scanline_offset=0, plan signature совпадает с task, expected_strokes=27. Game Monitor подтвердил radius 30→10; pointCount остался 1 (CHALK=0), Bridge session завершилась без dropped events/errors/send failures.

Причина установлена в runtime guard integrated_app.py: повторное построение выполнялось вызовом build_fixed_radius_fill_plan(shape_id, radius) без spacing-параметров. Значения по умолчанию — step=1/offset=0, то есть legacy planner v1. Поэтому сравнивался FILL-001-RS v2 signature с другой геометрией v1 и срабатывал корректный fail-closed guard. Это ошибка handoff/validation, не ошибка регулировки кисти и не расход CHALK.

Исправление: единый helper повторного построения получает scanline_row_step/scanline_offset из frozen task; для legacy tasks без этих полей сохраняются прежние defaults. Объявленный planner_version проверяется против фактически восстановленного. Добавлены регрессионные проверки RS signature/27 strokes, legacy signature/131 strokes и отказа при несовпадении версии. До успешного CI и повторного локального preflight live matrix остаётся BLOCKED; повторный запуск здесь не выполнялся.

- Рабочая ветка: `feature/image-geometry-optimization`. Последний code/test commit: [dac985e](https://github.com/Kiddos19882/AutoDraw/commit/dac985e147319d2275318531ab9063cdf410e5a4); полный CI [41766148192](https://github.com/Kiddos19882/AutoDraw/actions/runs/41766148192) прошёл успешно. Начальный HEAD серии FILL-001-RS implementation: `32c06d1d61b4715197741d817e18365fc34e3f47`. Последние 20 коммитов проверены; GitHub API не предоставляет локальный `git status`.
- В runtime evidence commit [73d14a1](https://github.com/Kiddos19882/AutoDraw/commit/73d14a1784a5a9f8ef29bc0e197b75352f2650af) task run однозначно связан с executor и Bridge: radius=10, pointCount 1 → 6000, exact CHALK=5999, sampled/per-stroke delta=5999, 131 pointer candidates, 128 consuming strokes и 3 non-consuming candidates. Это точный расход до исчерпания квоты, но не полная стоимость незавершённого плана.
- Capture REJECTED: frozen task ожидал 131 consuming stroke; три последних кандидата не потребили CHALK после достижения pointCount=6000. Binder и критерии acceptance не ослаблять. Before/after PNG существуют, но количественный audit frozen mask не выполнен.
- Статический OpenCV-анализ базового frozen rectangle r10 воспроизводит 131 штрих, path=40 218, estimated sampling points=10 237, coverage=100%, leakage=0. Плотность проходов — 1 logical px; для кисти шириной 10 соседние линии перекрываются примерно на 90%.
- Exhaustive FILL-001-RS OpenCV sweep: 2 238 step/offset candidates, 62 passed coverage≥99%/leakage=0; all 15 shape/radius cells have frozen configs. Baseline rectangle/r10/step1 reproduced exactly (131 strokes, path 40 218, estimated points 10 237, coverage 100%, leakage 0). Full report: [CHALK_FILL001_RS_STATIC_SWEEP_2026-11-04.md](CHALK_FILL001_RS_STATIC_SWEEP_2026-11-04.md).
- Implemented FILL-001-RS planner v2, separate 45-task manifest builder, single-task handoff, runtime context binding and manifest generator. Legacy planner v1, original FILL-001 plans/signatures, masks, manifest and P1 sampling remain unchanged. Rectangle/r10/step5/offset0 is the first live candidate only; OpenCV metrics do not measure CHALK.
- CI для FILL-001-RS code HEAD прошёл все обязательные jobs: 800 passed, 24 warnings, 82 subtests; exhaustive sweep 2 238 кандидатов / 62 прошедших gate и artifact upload SUCCESS; Windows portable build/startup smoke-test и INT-006 pixel audit SUCCESS. Optional benchmarks skipped. Обе live matrices остаются BLOCKED до принятого одиночного FILL-001-RS live preflight. INT-006 safety margin не установлен; INT-007 BLOCKED.
- FILL-001-RS code, tests, workflow and related Markdown documentation обновлены; полный CI [41766148192](https://github.com/Kiddos19882/AutoDraw/actions/runs/41766148192) прошёл успешно. UI и production defaults не менялись; master не изменялся.

Историческая запись статуса на 2026-11-03 (сохранена для истории; её CI/HEAD сведения superseded текущим блоком выше):

- Рабочая ветка: feature/image-geometry-optimization. Текущий branch HEAD: [73d14a1](https://github.com/Kiddos19882/AutoDraw/commit/73d14a1784a5a9f8ef29bc0e197b75352f2650af) — пользовательский commit с новыми FILL-001 runtime evidence. Последний code/test commit остаётся [5cde7a1](https://github.com/Kiddos19882/AutoDraw/commit/5cde7a109a669bebf790ecbeb21f8bbc4feae182); evidence commit не меняет исходники, тесты или workflow. Compare с master: diverged, feature ahead 2713 / behind 5, merge base d4a07702e45c01648f343bc6440a3287c45d3f9c. master = 9a3453aeb847b66041bc83d6f4a56ecaf33a993a, не изменялся. Через GitHub API локальный git status недоступен.
- В commit 73d14a1 добавлены attempt, manifest, DrawingPlan, executor report, Bridge session, два run JSON и before/after PNG для fill001-20261104-051653-rectangle-r10-rep1.
- Первый Bridge run — калибровочный: activity завершилась до executor start, exact CHALK=0, два non-consuming candidates. Его нельзя смешивать с task run.
- Второй Bridge run bdca032b-57df-402c-a6c8-bb4be0f9a6ee связан с executor по activity window. Зафиксированы radius=10 throughout, exact pointCount 1 → 6000, CHALK=5999, sampled/per-stroke quota deltas=5999; dropped events, Monitor errors, Bridge send failures и sequence gaps равны нулю.
- Ключевое ограничение: 131 pointer stroke candidates, но только 128 consuming strokes; последние три кандидата pointer-stroke-131/132/133 имеют CHALK=0. Поэтому run не соответствует frozen task expected_strokes=131, runtime binding должен отклонить его; capture не принят. 5999 — фактически потраченная квота, а не доказанная полная стоимость завершённой заливки. Полная потребность для всех штрихов остаётся неизвестной и превышает доступную квоту этого запуска.
- Executor report записан в 02:22:19.193Z, Bridge run финализирован в 02:22:22.633Z. Первичная ошибка UI «runtime binding ещё не готов» согласуется с нажатием кнопки до persistence run-файла; после появления файла строгий binder обнаружит mismatch 128/131 и 3 non-consuming candidates. Ослаблять эти проверки нельзя.
- Before PNG визуально пустой, after PNG визуально показывает заполненную прямоугольную область. Количественный audit frozen mask (coverage/leakage) не выполнялся; визуальный просмотр не заменяет pixel audit. Attempt остаётся pending, capture JSON отсутствует.
- FILL-001 остаётся IN_PROGRESS; 45-cell matrix BLOCKED. Следующий шаг — статически разобрать бюджет CHALK/геометрию frozen plan и определить, как учитывать over-budget/censored outcomes, не меняя текущие критерии задним числом и не повторяя тот же запуск без изменений.
- Полный CI [41754801210](https://github.com/Kiddos19882/AutoDraw/actions/runs/41754801210) относится к code/test HEAD 5cde7a1 и завершился SUCCESS: Preparation/G3 — 787 passed, 24 warnings, 82 subtests; обязательные jobs, INT-006 pixel audit и Windows portable build/startup smoke-test — SUCCESS; optional benchmarks — SKIPPED. Для data-only commit 73d14a1 CI checks отсутствуют.
- Подробный разбор: [CHALK_FILL001_PREFLIGHT_POSTMORTEM_2026-11-04.md](CHALK_FILL001_PREFLIGHT_POSTMORTEM_2026-11-04.md).

Историческая запись статуса на 2026-11-03 (сохранена для истории; её CI/HEAD сведения superseded текущим блоком выше):

**Последнее обновление:** 2026-11-03 — после первой пользовательской попытки FILL-001 (commit [6b1cba9](https://github.com/Kiddos19882/AutoDraw/commit/6b1cba9b1c40a030ac6bd7b29365bf19ac3c9149)) выявлена ошибка сериализации runtime DrawingPlan: к JSON добавлялась буквальная последовательность `\n`, из-за чего Stage 6 отклонял файл. Исправлено в code commit [8dfd1b5](https://github.com/Kiddos19882/AutoDraw/commit/8dfd1b541f54a1b416dfb2907739cf4b1a99c58d); добавлен интеграционный regression test в [1b2d8a1](https://github.com/Kiddos19882/AutoDraw/commit/1b2d8a128c99ab8ad1abb1e9f480702676cd9f56). GitHub Actions [41692129486](https://github.com/Kiddos19882/AutoDraw/actions/runs/41692129486) выполняется на code/test HEAD `1b2d8a1`: Application integration, Game Monitor/Bridge, Preparation/G3, Executor и INT-006 pixel audit jobs — SUCCESS; Windows portable build/startup smoke-test ещё выполняется. **Повторный Windows live preflight не выполнен; 45 live captures остаются заблокированы.**

**Актуально на:** 4 ноября 2026 г.  
**Репозиторий:** `Kiddos19882/AutoDraw`  
**Рабочая ветка:** `feature/image-geometry-optimization`  
**Последний code/test candidate:** [1b2d8a1](https://github.com/Kiddos19882/AutoDraw/commit/1b2d8a128c99ab8ad1abb1e9f480702676cd9f56), включает исправление FILL-001 runtime JSON handoff и интеграционный regression test; CI [41692129486](https://github.com/Kiddos19882/AutoDraw/actions/runs/41692129486) выполняется; все regression jobs завершились SUCCESS, ожидается Windows portable build/startup smoke-test. Предыдущий подтверждённый code/test HEAD — `031913c` (client-ROI correction).  
**Текущий branch HEAD:** проверяется по GitHub branch reference; документационные коммиты выполняются последовательно поверх code/test изменений.  
**Последний подтверждённый полный CI baseline:** [41673570178](https://github.com/Kiddos19882/AutoDraw/actions/runs/41673570178), SUCCESS на code/test HEAD `e3774a3`. **CI для client-ROI correction:** workflow run [41686091985](https://github.com/Kiddos19882/AutoDraw/actions/runs/41686091985) — SUCCESS на HEAD `031913c`; portable artifact [autodraw-g3-preflight-build](https://github.com/Kiddos19882/AutoDraw/actions/runs/41686091985/artifacts/13254104951) собран и загружен (636,529,516 bytes, retention 7 days). Preparation/G3 — 778 passed, 24 warnings, 82 subtests passed; Executor regression, Game Monitor/Bridge, Application integration, INT-006 PNG audit и Windows portable build/startup smoke-test — SUCCESS; optional algorithm benchmarks skipped. Это не заменяет ручной live запуск FILL-001 в игре и проверку реальных board PNG.  
**Git-сверка:** branch HEAD перед последней актуализацией этого документа — `abd6af3dcdd42375231bfe38c682c9c99e128506`; `master` — `9a3453aeb847b66041bc83d6f4a56ecaf33a993a`. Compare: `diverged`, feature ahead 2663 / behind 5, merge base `d4a07702e45c01648f343bc6440a3287c45d3f9c`. Merge/rebase не выполнялся, `master` не изменялся. Локальный `git status` через доступный GitHub API не читается.  
> Этот блок — единственный источник текущего статуса. Ниже сохранена историческая хронология; старые статусы и планы не являются текущим backlog.

## Система управления знаниями ИИ

**Статус:** базовая постоянная система создана в рамках DOC-018. Пять регламентов определяют рабочий процесс ИИ, архитектуру знаний, уровни доказательности, инженерные инварианты и стандарт экспериментов. Навигация подключена из README приложения и docs/README.md. Система универсальна для всех подсистем и этапов; пересмотр требуется только при изменении постоянных правил проекта. Подробности — в [системном индексе](README.md).

## Текущее состояние

- Документационная серия DOC-001—DOC-016 завершена. Аналитические этапы 7–10 отменены пользователем и остаются только в архиве.
- Радиусная матрица: 21/21 принятых опытов. Результат ограничен испытанными длинными линиями; INT-006 выполнялся при фиксированном radius=10 и не измеряет влияние радиуса.
- G1: 12/12; G2: 18/18; G3: 27/27. Исходные и follow-up серии V1–V5: 90/90 captures; pixel audit подтвердил 297/297 новых strokes с coverage=1.0 и zero gaps.
- Game Monitor exact CHALK определяется как `post.pointCount - pre.pointCount`. Визуальная оценка paint meter не заменяет точный счётчик.
- **INT-006 D1–D5 live block завершён:** серия `chalk-20261102-232320-7cea27`, block `1f93ddcac07445b78093744c7cbabcde`, 45/45 задач completed, одна completed attempt на задачу, radius=10. Ветка содержит 45 соответствующих experiment manifests и 45 Monitor reports.
- **Полный повторный аудит 45 captures выполнен:** все 45 manifests и 45 Monitor reports перечитаны. Exact CHALK, `sampled_point_delta_total` и сумма per-stroke `DRAW_SAMPLE.pointDelta` совпадают; stroke groups/count совпадают; observed radius=[10]; dropped events, Monitor error delta, Bridge send-failure delta и sequence gaps равны нулю. Experiment ID каждого report совпадает с journal attempt. Детали: [результаты INT-006](CHALK_INT006_VALIDATION_PRELIMINARY_RESULTS_2026-11-03.md).
- **Официальные метрики 45 plan runs:** MAE 1.408 CHALK, RMSE 1.967, bias -0.875, MAPE 2.134%, maximum underprediction 1.82 CHALK (D5/P2). По 243 stroke rows: MAE 0.439, RMSE 0.544, maximum underprediction 1.085 CHALK. Штатный analyzer завершился `status=complete`, 45 accepted, 0 missing, 0 rejected; все 15 groups имеют 3/3 repeats. Frozen artifact SHA-256 совпадает с journal. Подробности: [официальный отчёт INT-006](CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md).
- P1 (step=4, delay=5 ms) показал наименьшие официальные MAE/RMSE/MAPE среди профилей и max underprediction 0.92 CHALK. Фактический расход P1 составил 1010 против 1884 у P0 (−46.4% суммарно); по геометриям экономия составила 22.8–47.3%, причём D4 short details — нижняя граница. P1 остаётся кандидатом только для дальнейшей проверки, не production default.
- В analyzer исправлено сравнение абсолютного Windows experiment path: relocated capture bundles связываются с journal по имени experiment directory. Дополнительно analyzer сверяет `task.prediction_id` и `task.expected_strokes` с frozen prediction; regression tests покрывают Windows path и tampered journal prediction ID.
- В `.github/workflows/geometry-tests.yml` analyzer проверяет runtime manifest hash и нормализованную logical geometry против frozen plan. Первый run `41530634729` обнаружил несовпадение сериализаций; fix `8eba34f` и regression fixture `dd64730` устранили ошибку. Повторный run `41532629748` завершился SUCCESS, официальный JSON artifact проверен.
- Production estimator, executor defaults, sampling defaults и `master` не менялись.
- **INT006R полностью завершён:** series `chalk-20261103-030837-a20df5`, block `a8e0b9ec87984f60aa294910d366e987`, 45/45 tasks completed (D1–D5 × radius 1/10/30 × 3 repeats, P1 step=4/delay=5). Raw-data audit и официальный CLI analyzer приняли 45/45 captures; ручной visual audit всех 45 пар PNG завершён. Ограничения: D2/radius=1 — видимый разрыв соединения polygon; D4/radius=30 — слияние коротких деталей. Отчёты: [live results](CHALK_INT006R_LIVE_RESULTS_2026-11-03.md), [visual audit](CHALK_INT006R_VISUAL_AUDIT_2026-11-03.md).
- Полный CI [41540054975](https://github.com/Kiddos19882/AutoDraw/actions/runs/41540054975) прошёл: Preparation/G3 682 passed + 82 subtests; Application integration, Executor regression, Game Monitor/Bridge, INT-006 PNG audit и Windows portable build/startup smoke-test — success. 24 warnings, optional benchmarks skipped. Подробности: [INT006R software gate report](CHALK_INT006R_SOFTWARE_GATE_RESULTS_2026-11-03.md).
- INT006R: live captures, raw-data audit, официальный CLI analyzer и ручной visual audit завершены. Результаты ограничены проверенными D1–D5; FILL-001 отдельно проверит заполнение площадей.

## Статусы инициатив

| ID | Текущий статус | Фактическое состояние |
|---|---|---|
| DOC-001—DOC-018 | DONE | Основная документация, инвентаризация и справочник Game Monitor/Bridge завершены. |
| INT-001 | DONE | Источник exact CHALK и семантика игрового счётчика определены. |
| INT-002 | DONE | Resource snapshot и baseline/delta протокол определены. |
| INT-003 | IN_PROGRESS | Требуется сопоставимое A/B/C измерение overhead/FPS Monitor off / Monitor versions. |
| INT-004 | DONE* | WebSocket telemetry, per-run capture и привязка Monitor report к experiment используются; A/B/C overhead остаётся в INT-003. |
| INT-005 | DONE* | Автоматические CHALK blocks, matrix, journal, recovery и fail-closed gates используются в принятых сериях. |
| INT-006 | IN_PROGRESS | Live captures, 45/45 Monitor audit, официальный analyzer (45 accepted, 0 missing/rejected), 15/15 complete groups и полный binding audit завершены. Осталось отдельно решить вопрос safety margin и расширить domain validation; production eligibility не подтверждена. |
| INT-006R | DONE | 45/45 live captures, raw-data audit, официальный CLI analyzer и ручной visual audit завершены. Зафиксированы geometry-specific limitations для D2/radius=1 и D4/radius=30. |
| INT-006F / FILL-001 | IN_PROGRESS | Exact CHALK=5999 на неполном run (128/131 consuming strokes); capture REJECTED, quantitative PNG audit отсутствует. FILL-001-RS exhaustive static sweep и versioned planner/matrix/handoff реализованы; CI нового HEAD pending. Одиночный local live preflight не выполнен; обе 45-task matrices BLOCKED. INT-006 safety margin не установлен, INT-007 BLOCKED. |
| INT-007 | BLOCKED | Интеграция валидированной модели в preflight/resource estimator запрещена до закрытия INT-006 и определения safety margin. |
| INT-008 | TODO | Оптимизация траекторий, кистей, порядка и покрытия в пределах CHALK после INT-007. |
| INT-009 | TODO | Независимая проверка прогноза на полных рисунках, визуального качества и фактической экономии. |

## Ближайший рабочий приоритет

1. Подтвердить новый FILL-001-RS GitHub Actions workflow на code HEAD: preparation regressions, exhaustive 2 238-candidate sweep artifact, остальные required jobs и Windows portable build/startup smoke-test.
2. На локальной Windows машине создать новый fill001-rs manifest командой source/preparation/create_fill001_rs_manifest.py и открыть его во вкладке FILL-001.
3. На восстановленной доске с полной квотой выполнить только rectangle / radius=10 / scanline_row_step=5 / offset=0 / repeat=1.
4. Проверить task↔DrawingPlan↔executor report↔Bridge session/run binding, exact pre/post pointCount и PNG audit на calibrated ROI (coverage≥99%, leakage=0).
5. Только после принятия preflight решать вопрос о новой 45-task RS matrix. Production estimator/defaults не менять.

## Разрешения и границы

- Документацию и журнал результатов можно обновлять без дополнительного запроса.
- Изменения репозитория выполнять только в `feature/image-geometry-optimization`; `master` не изменять.
- Не переписывать первичные manifests, Monitor reports и PNG; не смешивать разные block IDs.
- Live captures требуют доступной игровой сессии; не заявлять о новых live-прогонах без фактических данных.
- Точный расход — только delta игрового `pointCount`; paint meter не является источником exact CHALK.
- Выводы INT-006 ограничены D1–D5, radius=10 и испытанными sampling profiles. Кривые, заливки и неподдержанные геометрии остаются UNKNOWN/unsupported.

## Историческая хронология

Ниже сохранены записи предыдущих этапов, включая статусы и планы, которые были актуальны на даты их создания. Они нужны для аудита решений, но не являются текущим состоянием проекта. Полный файл до консолидации сохранён без потерь в [PROJECT_STATUS_HISTORY_2026-11-02.md](PROJECT_STATUS_HISTORY_2026-11-02.md).

## 9. Целевая архитектура автоматизированной лаборатории кистей

Создан отдельный документ [BRUSH_TEST_AUTOMATION_VISION.md](BRUSH_TEST_AUTOMATION_VISION.md), описывающий полный целевой цикл от preflight и проверки координат до автоматического исполнения, точных pre/post CHALK snapshots, сохранения dataset и последующей передачи данных модели оптимизации.

Целевые компоненты: Experiment Controller, Plan Generator, Coordinate Transform, Brush Controller, MouseExecutor, независимый Game Monitor, Experiment Recorder и Dataset/Analyzer. Измеряемые штрихи должны выполняться только через MouseExecutor/PyAutoGUI; игровые внутренние методы и счётчики не подменяются тестовым кодом.

Документ фиксирует матрицу радиусов/длин/форм/скоростей/штрихов/перекрытий, минимум три повтора, отдельную A/B/C серию Monitor off / 0.1.2 / 0.2.0, обязательные checkpoints, manifest, fail-safe и критерии валидности.

Это целевая концепция, а не отчёт о полной реализации. Первый этап logical→screen преобразования реализован; перед матрицей остаётся live-проверка ROI и семантики границ. INT-003 остаётся IN_PROGRESS; INT-005 остаётся TODO.


## 10. Реализация первого этапа logical→screen transform

Добавлен source/preparation/brush_coordinate_transform.py; Brush Test теперь явно использует логическую систему 460×240. При передаче плана в Stage6 создаётся screen-local копия под фактический ROI, а исходный план сохраняет generation.screen_transform. Дополнительное продление концов тестовых линий отключено.

Добавлены unit-тесты transform и проверка интеграционного handoff. GitHub Actions run #1132 для HEAD `3a0383b56b5972d4b978ff30080d7b7768b021d0` прошёл полностью: `geometry-tests`, `executor-tests`, `Windows portable build and startup smoke-test` — success. Live browser validation, A/B/C Monitor и полная CHALK-матрица не завершены. INT-003 остаётся IN_PROGRESS.


## 11. Последняя проверка CI — 31 октября 2026 г.

Для HEAD `3a0383b56b5972d4b978ff30080d7b7768b021d0` workflow run #1132 завершился `success`. Все три jobs прошли: geometry-tests, executor-tests, Windows portable build and startup smoke-test. Программная часть logical→screen handoff и regression guards прошла CI. Это не заменяет live-проверку точной области доски, граничного hit-test и A/B/C overhead Game Monitor.


## 12. Исправление размера доски и состояние проверки

Прямая проверка master bundle подтвердила размеры `BoardPane` 460×240; прежнее значение 420×240 было ошибочным. Код, тесты и активная документация обновлены. Run #1142 на кодовом коммите `d0c4aee8c4bef75daedfae85ae4403a3a8661ef4` выполняет geometry-tests и Windows smoke-test; run #1157 на текущем документированном HEAD `2449664918fcb43679b5be664e0f020bb8a9622c` ожидает запуска. До успешного CI и live-проверки не считать INT-003 закрытой.


Для последующей live-проверки добавлен низкозатратный сценарий Brush Test `Проверка границ доски` (`board_boundary_probe`): четыре коротких штриха от внутренних точек к x=0/460 и y=0/240. Он позволяет проверить крайние координаты до полной матрицы; сам по себе не считается live-подтверждением и ещё не запускался в игре.


Последнее дополнение к INT-003: добавлен автоматический сценарий `board_boundary_probe` (четыре коротких штриха от внутренних точек к границам x=0/460 и y=0/240) и unit test. Это подготовка к live-проверке; реальный прогон в игре ещё не выполнялся. Полная матрица остаётся заблокированной до проверки ROI/границ и A/B/C Monitor.


Дополнительная защита transform: игровой BoardPane масштабируется равномерно. Преобразователь теперь отклоняет экранный ROI, если относительное расхождение вычисленных scaleX/scaleY превышает 1%; значения и допуск сохраняются в metadata. Unit-тест покрывает неверные пропорции ROI. Это статическая защита от искажённой калибровки, а не подтверждение фактического ROI в браузере.


Подтверждение CI: run #1142 успешно прошёл все три jobs на коммите `d0c4aee8c4bef75daedfae85ae4403a3a8661ef4`. Этот результат подтверждает базовую версию logical 460×240 transform и соответствующие тесты/сборку. Он не покрывает более позднюю проверку равномерности ROI и сценарий boundary probe; для них ожидается отдельный CI.


### Изменение поведения Brush Test — 2026-10-31

После успешного теста автоматически сохраняются `after_draw`-скриншоты, ROI и `experiment.json`; автоматический клик Clear и post-clear verification больше не запускаются. Доска остаётся в состоянии после рисования, чтобы пользователь мог проверить конечные точки и снять Game Monitor export. Начальный pre-clear перед независимым тестом сохранён. Остановка по горячей клавише переведена с F12 на Alt во всех исполнительных сценариях. Unit tests обновлены, но CI и live-проверка ещё не выполнены.


## 13. Live boundary probe — результаты 31.10.2026

В commit пользователя `f72c2d16e7f61071bcaa2d184c071189dd74b69c` добавлены три реальных запуска `board_boundary_probe` с радиусом 1. Каждый запуск завершил четыре штриха. Game Monitor 0.2.0 подтвердил точные snapshots через `BoardPane.max+BoardPane.less`: baseline pointCount=1, max=6000; post pointCount 52/53/53, следовательно CHALK delta=51/52/52 (среднее 51.67). Ошибок и dropped events нет. Результаты подтверждают, что Monitor фиксирует изменение игрового счётчика в живой игре и что повторяемый тест расходует около 52 точек при текущих параметрах.

Конечные POINTER_UP client coordinates совпадают с расчётными экранными endpoints после учёта viewport offset. Но сами координаты принятых DRAW_SAMPLE точек в export отсутствуют, поэтому hit-test включительных границ нельзя считать окончательно доказанным по Monitor JSON. В исходных manifest автоматическая проверка видимости была inconclusive из-за сравнения logical 460×240 с screen ROI 578×301. Исправлен analyzer: теперь он применяет сохранённый transform к expected strokes. Требуется повторный прогон для подтверждения визуальной метрики. Paint meter screenshot estimator также inconclusive и не используется вместо точного Monitor.

CI на commit f72 обнаружил ошибочную negative fixture в test_transform_rejects_nonuniform_roi_for_uniform_game_scale (646×338 — равномерный ROI). Фикстура заменена на 646×323. Добавлены tests для screen-local преобразования expected strokes и mismatch ROI. Последующие CI runs нужно дождаться и проверить по актуальному HEAD. A/B/C Monitor off/0.1.2/0.2.0 не выполнялся; полная матрица кистей не разблокирована.


### 14. Визуальное подтверждение границ на live-скриншотах

Все три полных `after_draw-screen.png` и три `after_draw-board.png` из commit f72 просмотрены. На всех трёх прогонах четыре штриха видны и доходят до соответствующих сторон BoardPane; видимого выхода за границы нет. Это подтверждает transform для конкретного ROI x=563/y=253/578×301 при разрешении 1920×1080. Исходное поле automated `stroke_visibility_analysis` остаётся inconclusive, так как записано до исправления analyzer; ручной просмотр PNG является отдельным подтверждением. A/B/C overhead тестирование и CI актуального кода остаются открытыми условиями INT-003.


## 15. Актуализация состояния после проверки CI — 31 октября 2026 г.

Кодовый HEAD перед документационными обновлениями — `0c09d2830bb007b7a9de1cd46e085f779e91d2f3`. Workflow `Geometry planner tests`, run #1224, завершился `completed/success`; все три обязательные jobs прошли: `geometry-tests`, `executor-tests`, `Windows portable build and startup smoke-test`. В `geometry-tests` успешно выполнены проверки синтаксиса Game Monitor, O(1) resource snapshot, локального WebSocket smoke server и набор preparation/geometry tests. Run #1223 также завершился success. Ранние падения #1210—#1213 исправлены последующими коммитами и не являются текущим статусом HEAD.

Три live-прогона `board_boundary_probe` ранее подтвердили точные CHALK deltas 51/52/52 при радиусе 1; визуально границы подтверждены на конкретном ROI 578×301. Старые manifests сохраняют исторический `stroke_visibility_analysis=inconclusive`, поскольку были созданы до исправления analyzer. Нужен новый прогон для автоматического visibility результата.

INT-003 остаётся IN_PROGRESS: A/B/C Monitor off / 0.1.2 / 0.2.0 и численное измерение overhead/FPS не выполнены. Smoke server пока является только транспортным ping/pong прототипом; production bridge, автоматический per-run capture и связь с manifest не реализованы. Наличие успешного CI не доказывает соединение из реального Firefox iframe.


## 16. Game Monitor 0.2.1 и расширение регрессионных проверок — 31 октября 2026 г.

Game Monitor обновлён с 0.2.0 до 0.2.1. `DRAW_SAMPLE` теперь включает `pointDelta` и `acceptedPoint`; последняя координата считывается из хвоста `atom.points` за O(1), только когда точный `pointCount` увеличился. Если между наблюдениями добавлено несколько точек, `pointDelta > 1` отмечает возможный пропуск промежуточных координат; событие не выдаётся за полную траекторию. Полный O(N) scan остаётся только в явном `diagnosticSnapshot()`.

Тесты дополнены проверкой последней принятой координаты, нулевого/stale sample, multi-point delta, точного восстановления всех пяти собственных методов, удаления wrappers у унаследованных методов, повторных start/stop и замены BoardPane.

Проверяемый кодовый HEAD: `32a3fdb35d95b15ca64c1bb4c7f404904ffc23e8`. Workflow #1238 выполняется; на момент записи успешно завершились `node --check`, Node.js tests Game Monitor и WebSocket smoke-server tests. Executor tests, geometry suite и Windows portable build/startup smoke-test ещё не завершены. Не объявлять полный CI успешным до завершения всех трёх jobs.

Новый Monitor 0.2.1 даёт данные для повторной live-проверки границ: сверять `acceptedPoint` с логическими x=0/460 и y=0/240, отдельно контролировать `pointDelta`. A/B/C обновляется до Monitor off / 0.1.2 / 0.2.1. Без пользовательской Firefox/игровой сессии эти live gates остаются незавершёнными; production bridge нельзя объявлять работающим до реального browser smoke test.


## 17. Game Monitor 0.2.1: CI подтверждён на актуальном HEAD — 31 октября 2026 г.

Актуальная вершина рабочей ветки: `354ff64802a8065aff19f17176c2ea3e65ff4bbc` (`docs(game-monitor): align README with 0.2.1 telemetry`). GitHub Actions workflow `Geometry planner tests`, run #1241 (`41212496267`), завершился `completed/success`. Все три обязательные jobs прошли:

- `geometry-tests` — success: синтаксис Game Monitor, O(1) resource snapshot, локальный WebSocket smoke server, анализ игрового bundle, Stage 5/7/8 benchmarks, synthetic geometry, fallback/outline-first comparison, preparation/geometry и unified-app UI regressions;
- `executor-tests` — success;
- `Windows portable build and startup smoke-test` — success.

Это подтверждает автоматические проверки и portable build на указанном HEAD. Это не подтверждает соединение из реального Firefox iframe с localhost, отсутствие overhead в живой игре, точность свежего boundary probe или корректность production bridge.

Game Monitor 0.2.1 остаётся текущей версией. INT-003 остаётся IN_PROGRESS: необходимы live Firefox transport smoke test, A/B/C Monitor off / 0.1.2 / 0.2.1, повторный boundary probe с проверкой `acceptedPoint`, затем полная матрица кистей и экспериментальная модель CHALK. Production bridge не реализовывать до успешного browser transport smoke test.


## 18. Live WebSocket smoke test и A/B/C Monitor — результаты commit e9a915d (31 октября 2026 г.)

Пользователь добавил результаты в commit `e9a915d5d8247055ab86168789079ed0562e0ee3`. Проверены все JSON snapshots, экспорты Game Monitor, FPS probes, boundary experiment и WebSocket smoke artifacts.

### WebSocket transport

Сохранённый ответ smoke test содержит `ready` и `pong` с ожидаемым nonce. Экспорт Game Monitor 0.2.1 зафиксировал игровой документ `https://eufbpet.hust.me/pet.php`, `frameContext.isTopFrame=false`, `boardDetected=true`, 340 событий, `droppedEvents=0`, без ошибок. Это подтверждает успешный браузерный smoke handshake в контексте тестовой игровой сессии. Production bridge и автоматическая связь capture с experiment manifest этим тестом не реализованы.

### A/B/C

Три порядка прогонов сохранены: A→B→C, B→C→A, C→A→B. A — Monitor остановлен, контрольные snapshots сняты read-only через `inspect()`; B — Monitor 0.1.2; C — Monitor 0.2.1.

| Повтор | A: без активного Monitor | B: 0.1.2 | C: 0.2.1 |
|---|---:|---:|---:|
| 1 | 53 | 0* | 50 |
| 2 | 52 | 52 | 52 |
| 3 | 52 | 52 | 52 |

Значения — `post.pointCount - pre.pointCount`, а не абсолютный pointCount. Baseline во всех snapshots равен 1. Повтор B-1 невалиден для расходного сравнения: pre/post остались равны 1, экспорт содержит только стартовый DRAW_SAMPLE без прироста и POINT_QUOTA_UPDATE без изменения счётчика. Его нельзя трактовать как нулевой расход при успешном рисовании.

В B-2/B-3 и C-1/C-2/C-3 нет dropped events и ошибок. В C диагностический полный подсчёт совпал с точным snapshot во всех трёх повторах (`pointCountMatches=true`). Сумма `pointDelta` в C равна 50/52/52. В повторах 2 и 3 все три режима дали одинаковый расход 52 точки. Это подтверждает повторяемость расхода в этих прогонах, но не доказывает отсутствие performance overhead.

### FPS и ограничения сравнения

Для каждого повтора сохранён один FPS probe: 600 кадров за ~10 секунд, average/median 60 FPS, P95 16.68 ms, max 16.68 ms, без скрытия документа и visibility interruption. Однако эти файлы не размечены по отдельным режимам A/B/C. Нет независимого FPS и времени исполнения для каждого режима. Поэтому численно сравнить overhead 0.1.2 и 0.2.1 пока нельзя.

### Повторный boundary probe

Отдельный live-тест с радиусом 1 завершил 4/4 штриха за 7.36 с (106 move calls), без ошибки исполнителя; mouse release успешен. Точный счётчик: 1→53, `ΔpointCount=52`, max=6000, remaining=5947. Автоматическая визуальная эвристика отметила 4/4 видимых изменений без неоднозначных ROI. Оценка заполнения paint meter осталась inconclusive и не является измерением CHALK.

В A/B/C-экспорте 0.2.1 принятые координаты подтверждают крайние вертикальные точки y=0 и y=240. Горизонтальные серии закончились на x≈2.21 и x≈458.21, а не на точных x=0/460. Видимое касание края кистью и близость принятых координат не равны доказательству принятия самой крайней горизонтальной координаты.

### Текущий статус INT-003

- Live browser WebSocket smoke handshake: подтверждён сохранёнными артефактами.
- A/B/C по фактическому CHALK: частично подтверждён; два повторных сравнения дали 52 во всех режимах, B-1 невалиден.
- Performance overhead: не измерен раздельно по A/B/C; требуется повторить FPS и duration capture отдельно для каждого режима.
- Boundary probe: визуально 4/4, точный счётчик и acceptedPoint доступны; точные горизонтальные граничные координаты x=0/460 ещё не подтверждены.
- Полная матрица размеров кисти не разблокирована до завершения контролируемого overhead-сравнения и граничного контроля.
- Влияние размера кисти на CHALK не установлено: все описанные live-прогоны относятся к кисти 1 и не являются сравнением разных размеров.



## 19. Первая реализация автоматического WebSocket telemetry bridge — 31 октября 2026 г.

Ветка получила первую реализацию автоматического сбора телеметрии Game Monitor. Это отдельный read-only поток, не управляющий мышью или игровым состоянием.

**Добавлено:**
- `game_monitor.js`: API `AutoDrawGameMonitor.subscribe(listener)` для инкрементальной передачи новых событий без повторного копирования всего массива events;
- `game_monitor_bridge.js`: браузерный агент для игрового iframe, WebSocket auth, event allowlist, heartbeat и requestAnimationFrame измерения во время активных штрихов;
- `game_monitor_bridge_server.py`: локальный loopback collector, точный Origin allowlist, случайный токен, лимит сообщения, один активный клиент, группировка штрихов по idle timeout и атомарное сохранение JSON;
- `requirements-bridge.txt`: изолированная зависимость websockets 12.0;
- README и BRUSH_MONITOR_AUTOCAPTURE_DESIGN дополнены инструкцией и границами реализации.

**Автоматические данные одного run:**
- pre-test snapshot из `DRAW_START.before`;
- post-test snapshot из `DRAW_END.after`;
- точный `consumed_points`, только если оба snapshot exact и согласованы;
- фактический радиус кисти, события, `pointDelta`, принятые координаты;
- длительность активных штрихов, elapsed от первого до последнего штриха и FPS по requestAnimationFrame;
- статус partial при разрыве соединения.

**Ограничения:** bridge сохраняет session/run JSON в отдельном каталоге, но пока не записывает путь и run_id в UI `experiment.json`. Live-проверка нового bridge из реального Firefox iframe ещё не выполнена. A/B/C overhead самого bridge также не измерен; все будущие сравниваемые прогоны должны иметь одинаковую конфигурацию инструментации.

**Статус INT-004:** IN_PROGRESS. Не считать production integration завершённой до browser validation и автоматической привязки run JSON к manifest.


### Дополнение к INT-004 — автоматическая привязка run к experiment.json

Brush Test UI теперь после callback завершения executor автоматически опрашивает каталог bridge, выбирает отчёт по времени старта относительно фазы `before_draw` и фактическому радиусу, копирует его в каталог эксперимента как `monitor_report.json` и добавляет в `experiment.json` session_id, run_id, точную CHALK delta, FPS, trajectory summary и capture status. Если совпадающий отчёт не появился в течение 10 секунд, manifest получает `monitor_capture.status=unavailable`.

Это закрывает файловую привязку на уровне UI, но корреляция пока основана на времени+радиусе, а не на сквозном experiment_id. Live Firefox validation и проверка возможных неоднозначностей при одинаковых радиусах остаются открытыми.


### Контроль целостности WebSocket run

В bridge добавлены `stroke_count`, сумма sample `pointDelta`, сравнение с CHALK delta, проверка единственного фактического радиуса и счётчики потерь/ошибок. UI присваивает capture статус `saved` только при полном совпадении CHALK/sample delta, одном радиусе, завершённом исполнении и нулевых потерях/ошибках; иначе сохраняет отчёт как `partial`. Production WebSocket handler дополнительно покрыт integration test с auth/session/event/heartbeat и проверкой файла результата.


### WebSocket: диагностика сессии без run JSON (commit 6382c27)

В результатах commit `6382c27` оба тестовых `experiment.json` имеют `monitor_capture.status=unavailable` и `matching_run_report_not_found`; единственный сохранённый session.json в этом коммите имеет ID `3323cf8e-01ca-4009-8f16-27d657d857f8`, отличный от отдельно сообщённого ID `89f3383e-b562-462f-a1dc-8f516bdd7378`. Код collector создаёт session.json на `session_start`, а run JSON — только после `DRAW_START`; следовательно подтверждено подключение, но не поступление события старта рисования.

Добавлена постоянная диагностика канала: браузерный счётчик отправленных событий/последнего типа/ошибок отправки и серверные счётчики принятых сообщений/событий/типов, последний heartbeat Monitor и состояние соединения. Поля записываются в session.json после каждого сообщения. Добавлен тест сохранения этих диагностик. Причина отсутствия событий пока не доказана; нужен следующий короткий live-прогон с новой версией агента.




### Live bridge diagnostics — commit 323a698 (31.10.2026)

В сессии `f303b3e1-382e-4859-9681-e1c360ec6424` подтверждена доставка телеметрии: Monitor активен, доска обнаружена, exact point counter 1→49 (`ΔCHALK=48`) за интервал сессии, 0 dropped events, 0 Monitor errors; browser bridge отправил 119 событий, сервер принял 119. Наблюдались 8 pointer-down/up пар, 55 DRAW_SAMPLE и 48 POINT_QUOTA_UPDATE. Радиус — 30.

**Причина отсутствия run JSON установлена:** в сессии нет `DRAW_START/DRAW_END`. Game Monitor pointer observer генерирует `POINTER_DOWN_CANDIDATE/POINTER_UP_CANDIDATE` и samples, но bridge FPS probe и серверный RunRecorder ориентированы только на engine lifecycle `DRAW_START/DRAW_END`. Поэтому WebSocket transport исправен, но pointer-only lifecycle не открывает/не завершает run; frame_probe_count остаётся 0.

Статус INT-004: transport/session diagnostics — LIVE CONFIRMED; automatic run recording — BLOCKED; FPS capture — BLOCKED; привязка monitor report к experiment.json — не подтверждена для этой сессии. Следующий gate — pointer lifecycle fallback с regression tests и повторный live Firefox run. Δ48 нельзя приписывать отдельному experiment.json без отдельной корреляции теста.




### Pointer lifecycle fallback — исправление в работе

В collector добавлен fallback по `POINTER_DOWN_CANDIDATE/POINTER_UP_CANDIDATE`, а FPS probe запускается и останавливается по тем же pointer границам, если engine callbacks отсутствуют. Источник lifecycle сохраняется в run как `stroke_lifecycle_sources`; штрихи дедуплицируются по stroke ID. Regression tests покрывают pointer-only и смешанный engine+pointer сценарии.

На HEAD `a1f8090ea5117785427c643769e8f034b46af391` CI step `Test local WebSocket smoke server` прошёл успешно (run `41230755334`). Полный workflow ещё выполняется. Live Firefox повтор после изменения не проведён, поэтому автоматическое появление run JSON и FPS в реальной игровой сессии пока не подтверждено.


### 2026-10-31 — ужесточение привязки Game Monitor к executor

Проверен live-артефакт commit 51028bd86b85b17da31256cd273c0857b100fec4. Автоматический executor завершил 6/6 штрихов за 29.796 s. Привязанный run bd8ca817 содержал только 1 штрих, 3 события и 0 CHALK; следовательно, он не является отчётом теста. Поздний fbcd2b1b содержит 9 штрихов и смешанные радиусы, возник после автоматического теста и пересёк сброс pointCount 721→48. Он не относится к эксперименту и имеет inconclusive CHALK.

Исправлено в UI:
- выбор run ограничен временем старта/окончания executor с небольшими техническими допусками;
- проверяются фактический радиус, единственность радиуса и совпадение stroke_count с drawing plan;
- mtime больше не используется как критерий выбора;
- при неоднозначности или отсутствии полного совпадения сохраняется monitor_capture.status=unavailable, без привязки чужого отчёта;
- saved требует положительной exact CHALK delta с согласованными pre/post pointCount; нулевой расход и сброс счётчика не считаются успешным измерением.

Ручные линии после завершения теста являются случайной отдельной активностью. В программу тестов и автоматическую матрицу они не добавляются.

Ограничение: текущая привязка принимает один run, который покрывает весь ожидаемый набор штрихов. Если collector разделяет одну серию на несколько run, capture останется unavailable, пока не будет реализована и проверена безопасная агрегация сегментов. Live повтор после исправления ещё не выполнен.



### 2026-10-31 — live-подтверждение автопривязки и точного CHALK

Коммиты результатов: a552e5d2a0ea8288e6db1d7f784495ae84e097cb и 7d2ce8e53409d9e3faa6b6246de3e3e8ca79b4a4.

Успешно выполнен автоматический тест paint_consumption_long_lines для кисти радиуса 1:
- executor: 6/6 штрихов, 29.984 s, 1524 move calls;
- Game Monitor run 570ec65b: 6 штрихов, только радиус 1;
- pointCount: 1 → 719;
- exact CHALK: 718, sampled pointDelta total: 718, совпадение подтверждено;
- осталось 5281 из 6000;
- 1454 события целевого run, потерь и ошибок нет;
- FPS: average 60.0, median 60.024.

Статус monitor_capture=saved и match_reason=matched_executor_window. Это подтверждает работоспособность исправленной привязки на одном live-прогоне.

WebSocket session штатно закрыта в 19:19:41.104 UTC: 1831 сообщений, 1750 событий, sendFailureCount=0, connection_closed=true. После executor был отдельный run восстановления ползунка радиуса 1→30 с нулевым расходом; он не попал в experiment. Ручные рисовальные тесты не проводились и не добавлялись.

Ограничения: результат 718 CHALK относится к радиусу 1 и данному тестовому шаблону. Траектория остаётся incomplete_until_verified из-за coalesced samples. Визуальная эвристика paint meter inconclusive и не используется вместо точного pointCount. Матрица других радиусов ещё не выполнена.


## 2026-10-31 — подготовка матрицы расхода CHALK по радиусам

**Статус:** подготовка протокола; локальные браузерные прогоны ещё не начинались.

Контрольный сценарий `paint_consumption_long_lines` уже содержит шесть параллельных горизонтальных линий длиной 400 логических px (суммарно 2400 px), с шагом 36 px на доске 460×240. Геометрию сценария менять нельзя: для сравнения меняется только радиус кисти.

Подготовлен отдельный план `CHALK_RADIUS_MATRIX_PLAN.md`: радиусы 1, 5, 10, 15, 20, 25, 30; три повтора каждого; независимый experiment/clear/baseline для каждого запуска; проверка фактического радиуса до рисования; точный post/pre pointCount и автоматическая привязка единственного run. Порядок запусков сбалансирован между повторами, чтобы уменьшить влияние временного дрейфа.

Перед первым браузерным тестом требуется внести изменения в инструментирование/манифесты, покрыть их автоматическими тестами и проверить локальные тесты Python/bridge. До этого не просить пользователя запускать браузерную матрицу.


## 2026-10-31 — реализация подготовки матрицы CHALK

Добавлена подготовка экспериментальной серии в Brush Test UI:
- поля ID серии и блока матрицы;
- валидация разрешённых радиусов и последовательности блока;
- метаданные `chalk_radius_matrix` сохраняются в DrawingPlan и `experiment.json`;
- каждому прогону присваивается уникальный `experiment_id`;
- ID и метаданные добавляются в сохранённую копию Game Monitor report, summary и `monitor_capture`;
- Game Monitor `run_id`, уже связанный с другим experiment, повторно не используется.

Добавлен чистый модуль `source/preparation/chalk_radius_matrix.py` с валидацией, дедупликацией и агрегированием. Добавлен CLI `tests/analyze_chalk_radius_matrix.py`, который формирует JSON-сводку по сохранённым experiment. Добавлены тесты `source/preparation/tests/test_chalk_radius_matrix.py` и проверка записи matrix metadata в UI manifest. Карты модулей, зависимостей и тестов обновлены.

**Статус проверки:** код и тесты добавлены в GitHub, но локальное выполнение pytest и итог GitHub Actions пока не подтверждены (combined status не вернул check statuses). Браузерные live-тесты не запускались и не должны начинаться до успешного автоматического прогона.


## 2026-10-31 — автоматический gate матрицы CHALK пройден

Актуальный HEAD ветки на момент проверки: `34535d1a56fce75ae9712d55b662a0abd19de868`.

GitHub Actions `Geometry planner tests`, run `41235681326`, завершился с `conclusion=success`. Все три задания завершились успешно: `geometry-tests`, `executor-tests`, `Windows portable build and startup smoke-test`. Ветка: `feature/image-geometry-optimization`.

**Следующий обязательный этап — локальная браузерная матрица CHALK.** Автоматические проверки подтверждают программную часть подготовки, но не дают новых игровых измерений. Единственная live-точка по-прежнему radius 1 = 718 CHALK для контрольного шаблона; зависимости от радиуса пока не установлено.


## 2026-10-31 — автоматическая коррекция радиуса кисти по Game Monitor

**Причина дефекта:** прежняя установка использовала только линейную интерполяцию между крайними координатами ползунка 30→1. После drag координата считалась достигнутой, хотя реальный радиус мог отличаться (например, запрос 5 приводил к 4). До этого значение Monitor вводилось пользователем вручную в диалог.

**Изменения в ветке `feature/image-geometry-optimization`:**
- добавлен `source/preparation/brush_radius_feedback.py`: извлечение скалярного радиуса из `status().snapshot.currentRadius` с fallback на последний элемент `snapshot.radius`, ограниченная secant-коррекция позиции;
- Brush Test требует активный Game Monitor Bridge и свежий heartbeat;
- после каждого drag UI ждёт heartbeat, полученный после отпускания мыши, сравнивает фактический радиус с целевым и при расхождении автоматически перемещает ползунок повторно;
- границы коррекции обновляются по фактически измеренным радиусам; допускается до 7 корректирующих drag;
- executor запускается только после точного совпадения Game Monitor и отдельного визуального подтверждения пользователем;
- отсутствие свежего heartbeat, ошибка перемещения или невозможность дальнейшей коррекции блокирует рисование (fail closed).

Добавлены `source/preparation/tests/test_brush_radius_feedback.py` и regression tests в `test_brush_behavior_test_ui.py`. Обновлены карта модулей, зависимостей, тестов, быстрый индекс, Game Monitor README и протокол CHALK-матрицы.

**Проверки:** код и тесты добавлены; GitHub Actions для этих изменений ещё не завершился. Локальные live/browser тесты не выполнялись. До успешного CI и последующего короткого live-проверочного прогона не запускать 21-точечную CHALK-матрицу.


### Расширение обратной связи на основной Stage6 executor

Проверка показала, что отдельный линейный контроллер существовал также в `source/executor/drawing/color_plan_execution.py` (`BrushSliderCalibration.coordinate_for_value` / `BrushSliderController.select_value`). Поэтому коррекция добавлена не только в Brush Test UI, но и в основной путь адаптивных кистей Stage6:

- Stage6 передаёт контроллеру reader активного Game Monitor Bridge из общего `brush_radius_feedback.py`;
- начальный фактический радиус должен совпадать с `initial_value` калибровки;
- после каждого изменения контроллер ожидает два последовательных heartbeat с одинаковым радиусом;
- при расхождении выполняет до 7 корректирующих drag, сохраняя фактическую координату достигнутого положения;
- следующий рисующий штрих допускается только после точного подтверждения;
- отсутствие моста, несоответствие исходного радиуса или исчерпание коррекций останавливает исполнение до рисования.

Добавлен regression test сценария 30→5, когда первая попытка даёт радиус 4 и контроллер корректирует координату до подтверждённого 5. Также обновлены API/dependency/test docs. CI на актуальном HEAD ещё ожидается; live-проверка не проводилась.



## 2026-11-01 — упрощение запуска Game Monitor Bridge из Brush Test

В разделе «Тест кистей» добавлены кнопки запуска локального WebSocket Bridge, копирования готового browser snippet с актуальным одноразовым токеном и копирования полного исходника game_monitor.js.

Добавлен source/game_monitor/start_game_monitor_bridge.bat для самостоятельного запуска. Скрипт переходит в корень репозитория, проверяет изолированную зависимость websockets, при необходимости устанавливает её из requirements-bridge.txt и запускает collector с точным Origin игрового iframe. Приложение запускает BAT в отдельном окне и передаёт уникальный путь временного snippet-файла.

Bridge server получил аргумент --snippet-file: он записывает токенизированный snippet в локальный файл для копирования из UI и удаляет его при остановке сервера. Секрет не добавляется в Git и не включается в experiment manifest. Валидация Origin в UI принимает только bare HTTPS Origin без пути, query и fragment.

Добавлены regression tests в source/preparation/tests/test_brush_behavior_test_ui.py для допустимых и недопустимых Origin. Требуется подтвердить GitHub Actions и затем проверить на локальной Windows-системе полный порядок: запуск сервера → копирование/выполнение Monitor → копирование/выполнение bridge snippet → появление активной heartbeat-сессии.


### Уточнение для portable-сборки

Сборщик build_windows.py копирует необходимые файлы Game Monitor Bridge в папку game_monitor рядом с AutoDraw.exe. UI использует отдельную ветку определения путей для frozen/portable режима и передаёт серверу фактический каталог результатов Brush Test; вложенный путь AutoDraw_Stage20 в portable data не создаётся.


Функции запуска и копирования Game Monitor Bridge включены в app_features.json. Сопутствующие файлы копируются build_windows.py в portable-root/game_monitor; временный snippet хранится только в каталоге результатов на время сессии.


## 2026-11-01 — устойчивое сохранение Game Monitor session.json

**Наблюдение live-тестирования:** пользователь подтвердил успешное прохождение тестов кистью радиуса 1 и 5. При тесте радиуса 10 WebSocket handler завершился на PermissionError: [WinError 5] во время замены session.json.tmp на session.json. Этот прогон радиуса 10 не считать валидным измерением CHALK.

**Технический вывод:** запись выполняется последовательно внутри одного handler; доказательств внутрипроцессной гонки нет. Вероятная причина — кратковременная блокировка целевого файла Windows сторонним читателем/сканером/индексатором. Точный внешний процесс не установлен.

**Исправление:**
- атомарная запись вынесена в persist_json_atomically();
- для каждой записи используется уникальный временный файл;
- os.replace() повторяется при PermissionError с экспоненциальной задержкой;
- предыдущий session.json не перезаписывается напрямую и остаётся целым, пока атомарная замена не удалась;
- временный файл удаляется при успехе и при отказе;
- исчерпание повторов не должно завершать WebSocket handler; ошибка отмечается в диагностике, новая попытка выполняется на следующем сообщении.

Добавлены regression tests на восстановление после двух временных WinError 5 и на исчерпание повторов с сохранением предыдущего session.json. Проверка GitHub Actions для нового HEAD ещё ожидается. Следующий браузерный gate — повторить короткий тест радиуса 10 и проверить непрерывность сессии/heartbeat и сохранение session.json. До этого не продолжать матрицу.


## 2026-11-01 — матрица CHALK по радиусам завершена

Коммит первичных данных: [e2af4d0a69e2bd89b610b58678e20e86475cb8d0](https://github.com/Kiddos19882/AutoDraw/commit/e2af4d0a69e2bd89b610b58678e20e86475cb8d0). Серия `chalk-20261101-023127-b85dbb`: 7 радиусов × 3 независимых блока = 21/21 принятых experiment.

Каждый manifest прошёл проверку: monitor capture saved, точный CHALK counter, совпадение с sampled pointDelta, 6/6 штрихов, один наблюдаемый радиус, нулевые dropped events/monitor errors. Все прогоны имеют baseline pointCount=1, 1524 move calls и одинаковый сценарий из шести горизонтальных линий.

Итоговые измерения: радиус 1 — 724/727/725; 5 — 725/722/725; 10 — 728/725/723; 15 — 725/728/724; 20 — 726/725/723; 25 — 727/726/728; 30 — 725/725/723. Общий диапазон 722–728 CHALK, среднее 725,19. Для данного фиксированного сценария заметной систематической зависимости расхода от радиуса не обнаружено. Вывод не переносить автоматически на короткие штрихи, диагонали, кривые и повторное покрытие.

Подробный анализ, статистика, ограничения и практические выводы: `docs/CHALK_RADIUS_MATRIX_RESULTS.md`. План `CHALK_RADIUS_MATRIX_PLAN.md` закрыт. Следующая исследовательская задача — измерить зависимость расхода от геометрии штриха/режима ввода, сохраняя раздельность CHALK, move calls, sampled points и длины пути.


## 2026-11-01 — G1 live captures добавлены, принятие серии заблокировано metadata

Первичные данные добавлены коммитом [b75fe367073c22e818227b1d07ef4abe63a654fb](https://github.com/Kiddos19882/AutoDraw/commit/b75fe367073c22e818227b1d07ef4abe63a654fb): 12 физических запусков четырёх сценариев G1. Все 12 Game Monitor reports имеют `chalk.status=exact`, радиус 10, ожидаемое число штрихов, нулевые dropped events/errors; per-stroke суммы `DRAW_SAMPLE.pointDelta` совпадают с точным общим CHALK.

Описательные результаты: horizontal 122/124/120 (mean 122,00); vertical 60/61/61 (60,67); diagonal 75/76/76 (75,67); short strokes 19/18/17 (18,00). Детальная таблица per-stroke и ограничения записаны в `docs/CHALK_GEOMETRY_MATRIX_G1_RESULTS.md`.

**Блокирующая проблема:** все 12 manifests имеют `repeat_index=1`; требуемое планом поле `matrix_order_index` отсутствует. Поэтому повторяющиеся repeat cells не позволяют анализатору принять три независимых повтора каждого сценария как complete groups. Первичные manifests и monitor reports не переписывались. G1 остаётся на gate принятия metadata; G2/G3 не запускать до его разрешения.

## 2026-11-01 — исправление повторов CHALK geometry matrix в Brush Test UI

Проверка `brush_behavior_test_ui.py` установила причину: поле «Блок / повтор (1–3)» инициализировалось значением `1`, а при каждом создании плана UI напрямую считывал его. Автоматического перехода к следующему повтору и проверки уже занятой ячейки «series + scenario + repeat» не было. Это объясняет одинаковые значения в manifests; однако сам факт ручного выбора значения пользователем из исходников доказать нельзя.

Исправления в ветке `feature/image-geometry-optimization`:
- добавлен `inspect_chalk_matrix_series()`: сканирует сохранённые `experiment.json` серии, обнаруживает уже использованную ячейку и рассчитывает следующий порядковый номер;
- Brush Test UI блокирует создание плана, если выбранный повтор для данного сценария уже присутствует в этой серии;
- `matrix_order_index` назначается автоматически и записывается в metadata;
- анализатор проверяет поле, если оно присутствует, сохраняя чтение legacy manifests без этого поля;
- добавлены тесты на занятые/свободные повторы, следующий индекс и legacy manifests.

Проверенные первичные G1 manifests и `monitor_report.json` не изменялись. Хронология 12 запусков показывает три последовательных независимых прогона каждого сценария; это может служить основой для отдельного reconciliation sidecar, но не является основанием для незаметной перезаписи исходных файлов.

Коммиты: `afb5076c6de3f1eb6b42057d1830e1e7320b32d6`, `32d145ef9874be8e936ee411ec5bc2a96723a5b9`, `dc4100a22b0ebab576af22480b992449cbe2c8dd`, `e03e71ee9b285a896b039de12becf80aad5596a6`, `5771f52554c3356c54d451e0ab26e99c6a7524a8`.

GitHub Actions для актуального HEAD `5771f52554c3356c54d451e0ab26e99c6a7524a8` запущен, результат ожидается. G1 остаётся на gate принятия; G2/G3 не запускать.
## 2026-11-01 — ядро автоматических блоков CHALK

По предложению оператора начата замена ручного запуска каждого теста на пакетные блоки. Добавлены:
- `source/preparation/chalk_test_blocks.py`: формирование полного детерминированно перемешанного блока G1 (12 задач) или G2 (18 задач), три повтора каждого сценария, radius 10, фиксированный executor config, уникальный matrix_order_index;
- долговечный JSON-журнал блока с task/attempt IDs, статусами, experiment paths, progress и fail-closed поведением;
- защита от одновременного активного задания; failed/interrupted task ставит блок на паузу, автоматического пропуска/повторного запуска нет;
- `source/preparation/tests/test_chalk_test_blocks.py`: тесты полного состава, repeat cells, детерминированного порядка, journal, progression, fail-closed и interruption recovery;
- `docs/CHALK_TEST_BLOCKS_DESIGN.md` и ссылки в README, quick index, test map.

**Ограничение текущего этапа:** пока реализовано ядро планирования и журналирования, но кнопки Start/Stop, progress UI и автоматическая связка preclear → brush feedback → executor → Game Monitor exact capture → следующая задача ещё не подключены. Пакетный запуск пока не доступен оператору и нельзя считать блоки готовыми к live-использованию.

Следующий этап — UI state machine и интеграция полного жизненного цикла с существующими callback-ами. Любой невалидный CHALK capture, незавершённый executor, потеря Monitor, неуспешная очистка или прерывание приложения должны останавливать блок без пропуска задачи. Перед каждым новым экспериментом обязательна проверка пустой доски. Существующие G1 raw manifests не переписывать.

## 2026-11-01 — интеграция автоматических блоков CHALK в Brush Test

Ветка `feature/image-geometry-optimization` получила первый UI runner для G1/G2:
- выбор фазы и запуск полного блока одной кнопкой;
- создание долговечного block journal до первого действия мышью;
- автоматическое получение всех 12 задач G1 или 18 задач G2 с тремя повторами;
- progress, текущая задача и безопасная остановка на границе эксперимента;
- последовательная связка preclear + blank-board verification → brush drag/heartbeat feedback → executor → Game Monitor run capture → postdraw/brush restore;
- переход к следующей задаче только после успешной проверки manifest и complete per-stroke breakdown;
- любой failure, неполный capture или timeout переводит блок в paused; автоматического skip/replay нет;
- G2 заблокирована до завершения полного G1 block.

Добавлена функция `validate_chalk_block_experiment()`: использует матричный validator и фактические события `monitor_report.json`, требует complete per-stroke totals, измеренный frame probe без visibility interruption и непустую accepted trajectory.

**Пока не завершено:** полная матрица orchestration tests на все Tk callback/failure paths; подтверждённый GitHub Actions run и Windows portable smoke test. Добавлено 13 unit tests ядра блока и 10 callback workflow tests, включая restore gate, safe-stop recovery, блокировку G2 до 12 принятых G1 задач и Alt-cancel в preclear/postdraw. Recovery UI реализован. Live G1 не запускался. До подтверждённого CI, portable smoke test и отдельного разрешения оператора не запускать браузерные эксперименты.


## 2026-11-01 — recovery автоматических блоков

Добавлен UI recovery: после рестарта running task становится interrupted; experiment ID/path восстанавливаются из journal; повтор возможен только после ручной проверки доски и явного подтверждения. Ready journal можно продолжить с pending-задачи после подтверждения; failed/paused block можно закрыть без replay. Предыдущие попытки не перезаписываются.

Открытые gates: callback-level integration tests, проверка CI/Windows portable build, затем один контролируемый live G1. До их прохождения не запускать браузерную серию.


Последний CI run для commit `36b32dbc...` (`41265149825`) завершился failure: executor-tests прошёл, preparation suite — 8 failed / 556 passed; Windows portable build остановился на той же Stage 13 test suite до startup smoke-test. Исправлены тестовые фикстуры/ожидания. Дополнительно устранён runtime edge case: Alt cancellation во время preclear/postdraw теперь fail-closed приостанавливает block journal; добавлены два workflow tests. CI run `41266047330` для commit `609aca9156e5eb136c7db5cb516262b971d4fa82` выполняется, успех пока не подтверждён. Live G1 не запускался.


## 10. Актуальный статус автоматических CHALK-блоков (2026-11-01)

UI runner G1/G2 и recovery реализованы. Последний подтверждённый CI до дополнительного identity hardening: run [41266141717](https://github.com/Kiddos19882/AutoDraw/actions/runs/41266141717) для HEAD f8f2d1c6fe47b8d5e539be78951cea16296e16f6 — success по всем трём jobs, включая Windows portable build/startup smoke-test.

После этого review обнаружил, что capture acceptance не сравнивал идентификаторы manifest с активной задачей block journal. Добавлена проверка block_id/task_id/experiment_id, точного experiment_dir из активной попытки journal, series/phase/scenario/repeat, requested radius, expected stroke count, matrix order и executor config. Добавлен callback test на отказ preclear до запуска executor. Добавлены тесты на несовпадения и положительное совпадение. Эти новые коммиты требуют отдельного CI; до его успешного завершения live G1 не запускать.

Live G1/G2 не запускались. Старые 12 G1 manifests не переписывались. data/ не очищалась. master не изменялся. Локальный запуск pytest в текущей среде недоступен.

Последние изменения identity hardening: experiment_id и experiment_dir берутся из активной попытки, сохранённой в journal, а не только из UI state; manifest path сверяется с зарегистрированным каталогом. Добавлен тест preclear failure -> paused/failed без запуска executor. Последний CI для commit 95d3ab6c6f782340785ceaf4c534951c1f648c8b поставлен в очередь; результат ожидается.


## 11. Проверка CI и исправление тестовой подмены (2026-11-01)

Для task-identity/path acceptance hardening проверены runs [41267183785](https://github.com/Kiddos19882/AutoDraw/actions/runs/41267183785) и [41267241966](https://github.com/Kiddos19882/AutoDraw/actions/runs/41267241966). Оба подтвердили `executor-tests` success, но `geometry-tests` завершился с 1 failed / 574 passed; Windows portable build остановился на той же ошибке до startup smoke-test.

Падение было в callback test stub: lambda для `validate_chalk_block_experiment` не принимала новые keyword identity параметры. Исправлено в commit [20704ab984b981a4bf5b2278eba6cfad970d15a5](https://github.com/Kiddos19882/AutoDraw/commit/20704ab984b981a4bf5b2278eba6cfad970d15a5): stub принимает `**_kwargs`, а проверка incomplete evidence сохранена.

**Текущий gate:** повторный CI для исправленного commit ещё не подтверждён. Live G1 не запускался. Не изменялись `data/`, первичные manifests и `master`.


## 12. Целостность block journal и CI (2026-11-01)

Исправление callback test stub прошло полный CI: run [41268085571](https://github.com/Kiddos19882/AutoDraw/actions/runs/41268085571) — geometry-tests, executor-tests, Windows portable build/startup smoke-test: success. Последний documentation commit на тот момент также прошёл все три job: [41268149629](https://github.com/Kiddos19882/AutoDraw/actions/runs/41268149629).

Дополнительно усилен загрузчик block journal. Теперь структурно повреждённые журналы отвергаются до state transition/recovery: проверяются task/attempt shape и ID, статусы, единственная активная попытка, число running задач и согласованность статуса блока. Невалидный JSON преобразуется в ValueError и остаётся unresolved; автоматическая миграция/починка не выполняется. Добавлены негативные и позитивные unit tests. Коммиты: `2ea67817bd1187baa66252aec440a4a5238042e0`, `52b40e94eadf1e75f461565960547b2a749993e4`.

Новые изменения требуют CI. Межпроцессная блокировка journal write не реализована; предположение текущего runner — один активный экземпляр UI. Live G1 ещё не запускался.


Дополнительная защита journal validator: поля phase_id и block/task/attempt status сначала проверяются на строковый тип, затем на допустимое значение. Это исключает TypeError на unhashable JSON values (list/dict) и сохраняет fail-closed recovery path. Добавлены негативные тесты. Commits: `732128bfa62160ce6811e3925f371ab87f5f08d0`, `ff3e675fb09a5b05cceba75892469b87ba526fef`. CI для финального SHA ожидается.


CI выявил SyntaxError в journal validator после последнего hardening: literal `\n` попал в Python source вместо newline. Исправлено в commit `dd5aaade3b790546d9e3fc11341554f6aa09d8ec`. Это regression внесённого изменения; требуется повторный полный CI для исправленного SHA. Не считать блок runner готовым к live G1 до success всех трёх jobs.


## 13. Подготовка к G1: журнал и I/O failure paths

Добавлена строгая проверка согласованности block/task statuses и fail-closed блокировка запуска при journal status failed. Все транзакции изменения журнала защищены межпроцессной блокировкой ОС (Windows msvcrt, POSIX fcntl). Добавлены fault-injection tests для ошибок записи temp-файла и os.replace; при отказе замены исходный журнал сохраняется.

Коммиты: e688ed5b893903794afdf306c3b8db955e578639, dc21778fff4fc8ef8d47525d93ac00fde784eb78, 0d2d4182d9d418a274a69dcaa1ee9495a48e012d, 9147bbdfa8419a77481d093bb0669c05e4ab640a.

Важная граница: advisory lock сериализует транзакции, но не удерживается на протяжении всего GUI-сеанса. Поэтому два экземпляра AutoDraw не должны одновременно восстанавливать/обслуживать один журнал. CI и Windows startup smoke-test для нового SHA ожидаются. Live G1 пока не запускался.


## 14. Межпроцессное владение и recovery

Добавлен lifetime owner lock на каждый block journal. Он удерживается в активном GUI-сеансе и в recovery-сеансе. Второй экземпляр AutoDraw не может пометить живую running-задачу как interrupted, продолжить или закрыть тот же журнал. Если процесс завершился, ОС освобождает lock; следующий экземпляр получает lock и может выполнить штатный interrupted recovery. Resume/close повторно проверяют владение. Для закрытия failed/paused требуется явная проверка доски.

Коммиты: 9c709c5a597ebcb968419839d2dfc4af9b1a2bd3, 4c80d167ae28ea3327e71813a3db0c03a5d8e05a, 0d666afb63cb70634d90a25e7b0b87022a0394f2, 1b7486a86d2b19ead81625f9a465aef51b3e3450, 3ba5b4dc1c7a26d4a333592807bda802ceba76c5, 4e0e7809d5eef1235efccc65e2529892e8a81f85, 4d681cdf09c62f65647f651b271b81458ff59e29.

Ожидается CI на последнем кодовом SHA. Не запускать G1 до проверки Windows portable build/startup smoke-test и живого preflight.


Уточнение owner lock: блокировка общая для каталога chalk_test_blocks, а не отдельная на файл журнала. Это закрывает параллельный запуск разных серий в одном output_dir после одновременного прохождения preflight. Финальная реализация: commit e4793e0c03f8bface4b69954b109d8c843fa68d2d; UI scan: d82c1276fc9a1861003dfc3428cdf5b10b1d58ab; тест: 6034759be2bb873ea5ac20150ebe54bc40dab81e.


Owner lock I/O теперь fail-closed: ошибка открытия/создания блокировки не разрешает запуск или recovery; ошибка unlock не препятствует закрытию дескриптора. Добавлен PermissionError fault test. Новые commits 80f5c96f и d44d84f6 требуют полного CI.


Добавлен межпроцессный owner-lock test с отдельным spawn-процессом. Он должен подтвердить, что блокировка не является только внутрипроцессной. Требуется Windows CI для проверки msvcrt поведения.


Закрытие failed journal теперь оставляет явную audit-запись close_failed_block с board_checked=true и timestamp, аналогично закрытию paused journal. Код/тест: 6df2644a2e011a2dea6e8862c5267e9e9348d0ea, 8d0a949d5fc7697e836aad412ff900ba7532dc9c.

### CI finding — closure audit classification (2026-11-01)
The first final CI run exposed a mismatch: `finish_chalk_block_task(accepted=False)` correctly leaves the block in `paused`, while the rejected task itself is `failed`. Closure audit classification now inspects task statuses, recording `close_failed_block` when a failed task exists and `close_paused_block` for interruption-only pauses. This preserves the distinction between block state and failed experiment state. The existing regression test asserts the failed-task path. Full CI must be rerun; G1 remains blocked until all jobs and Windows portable smoke-test pass.

## 15. Итоговая готовность G1 runner — 2026-11-01

Финальный GitHub Actions run [41272291546](https://github.com/Kiddos19882/AutoDraw/actions/runs/41272291546) для HEAD `311299296559b9a5949f1e803f134b46436a2850` завершился `success`. Успешны все три jobs: `geometry-tests`, `executor-tests`, `Windows portable build and startup smoke-test`. Windows job выполнил `build_windows.bat`, включая `run_all_tests.py`, portable build и `smoke_test_portable.py`.

Первопричина предыдущего падения исправлена в [dd976b04](https://github.com/Kiddos19882/AutoDraw/commit/dd976b04f6d6423726ad7382bac7223c12d8342b): при закрытии блока тип audit-записи теперь определяется по состояниям задач, а не только по статусу блока. Если в paused-блоке есть failed-задача, сохраняется `close_failed_block`; для прерывания без failed-задач — `close_paused_block`. Регрессионный тест прошёл в финальном CI.

**Статус:** программная реализация G1 block runner прошла CI и Windows portable build/startup smoke-test; software gate закрыт. Live G1 не запускался. Перед первым опытом остаётся локальный Windows preflight: открыть portable AutoDraw на рабочей машине, подтвердить профиль калибровки и диапазон кисти 1–30, Clear reference, доступную игровую canvas, heartbeat Game Monitor и фактически пустую тестовую доску. Только после этого оператор запускает полный G1 блок из 12 задач. G2/G3 остаются заблокированными до принятия всех 12 валидных ячеек G1.

Изменения только в `feature/image-geometry-optimization`; `master`, `data/` и исторические G1 manifests не изменялись.

## 16. Live G1 завершён и post-run fixes — 2026-11-01

Пользователь провёл два live G1 прогона. Первый блок chalk-20261101-075204-f43b0d остановился после двух принятых задач: на vertical_lengths-r1 capture gate не принял Monitor run, ещё девять задач остались pending. Второй блок chalk-20261101-080012-4d6add завершён со статусом completed; все 12/12 задач приняты, с корректными repeat indices и matrix order.

Для второго блока подтверждены 12 exact Game Monitor captures, радиус 10, point_delta_matches_chalk=true, ноль потерянных событий и ошибок Monitor. Общий расход по 12 независимым опытам — 836 CHALK. Средние по сценариям: vertical 61,00; horizontal 123,33; diagonal 76,00; short 18,33. Подробные per-stroke данные и ограничения — docs/CHALK_GEOMETRY_MATRIX_G1_RESULTS.md, раздел 8.

Разбор первого блока установил: raw Monitor run ba6cf902-b635-442e-809b-e34ed1c7ced2 содержал точный расход 60 CHALK и точную сумму pointDelta, но пять pointer candidates при ожидаемых четырёх; один кандидат имел нулевой расход. Matcher ошибочно трактовал его как пятый штрих и отклонил run. Исправлено: stroke_count считает только stroke IDs с положительным суммарным DRAW_SAMPLE.pointDelta, а нулевые кандидаты записываются отдельно. Per-stroke analyzer использует то же правило и сохраняет список исключённых нулевых кандидатов.

Исправлено отсутствие финального уведомления: после принятия всех задач UI выводит отдельное окно с итогом 12/12. Добавлены regression tests для нулевого pointer candidate и completion notification.

Кодовые коммиты: e0bc57242498750c4ea3d327c6ac848690be72f5, a32b95d609b87470d43482b196916e2e5602c8ca, 42a84d2a146fcc7986a29843cf62398459361516, 08c70a2d2823c3df2c4aadced0c99100f46e5734, f5972945fe5e53e5d267a3de6e9ad45065d17c2f, c8d8c2c5588a0d423e48682962a4213ee725c808.

Полный GitHub Actions run 41276703424 завершился success на HEAD c8d8c2c5588a0d423e48682962a4213ee725c808. Все jobs прошли: geometry-tests, executor-tests, Windows portable build/startup smoke-test. В Windows job общий набор завершился 605 passed и 98 tests OK, затем portable layout и запуск приложения прошли.

**Текущий gate:** G1 принят. G2 разблокирован программной проверкой и готов к следующему live-блоку (18 задач), но перед запуском локальная сборка должна быть обновлена до HEAD выше. G3 остаётся заблокирован до принятия G2. Live-проверка исправленного уведомления и подсчёта будет дополнительно подтверждена на следующем обновлённом live-блоке.


## Live CHALK geometry matrix — состояние после G2 (2026-11-01)

- G1 принят: 12/12 в принятом автоматизированном блоке.
- G2 принят: 18/18 в серии `chalk-20261101-084732-a5c2cf`, первичные данные в commit `16a426b534de269ed967027bbe59f3daac4b97ec`.
- Все 18 G2 captures имеют exact CHALK, согласованные pointCount/pointDelta, правильное число штрихов, радиус 10, ноль dropped events и monitor errors.
- G2 показал, что повторный проход по той же линии потребляет около 61–62 CHALK на проход и практически не дешевле отдельной параллельной линии в пределах проверенного сценария.
- **Текущий этап: G3 разблокирован.** G3 должен измерить влияние `point_step_px` и `point_delay_ms` на фиксированной геометрии `paint_consumption_long_lines`: 3 × 3 комбинации, 3 повтора, 27 опытов.
- Подробные результаты G2: `docs/CHALK_GEOMETRY_MATRIX_G2_RESULTS.md`.
- До завершения G3 нельзя объявлять универсальную ресурсную модель подтверждённой. `move_calls`, длина пути, принятые точки и CHALK остаются разными метриками.


### Уточнение готовности G3
G2 принят и исследовательский gate G3 открыт. Однако текущий код block runner, UI и matrix validator поддерживает только G1/G2. Поэтому live G3 пока не запускать: сначала реализовать G3-идентификацию 9 комбинаций `point_step_px` × `point_delay_ms` с тремя повторами, UI-поддержку, валидацию/анализатор и regression tests; затем подтвердить полный CI и Windows portable smoke-test. Это программная подготовка G3, а не изменение экспериментального протокола.

## Актуальное дополнение — подготовка G3

G1 и G2 приняты по live-данным. Программная реализация G3 внесена в текущую feature-ветку; регрессионные тесты добавлены. Полный CI и Windows portable startup smoke-test ещё не подтверждены.

Целевой контракт: 27 задач на `paint_consumption_long_lines`, радиус 10; девять комбинаций `point_step_px` 1/2/4 × `point_delay_ms` 5/10/20, три повтора каждой. Идентичность каждой ячейки включает обе настройки executor и repeat_index.

До live-запуска обязательны regression tests, полный GitHub Actions CI и Windows portable startup smoke-test. Параметры должны реально применяться к `MouseExecutor` и попадать в execution report; запись только в experiment manifest не считается реализацией G3. Временный override не должен изменять постоянный профиль пользователя.


## Актуальное состояние G3 — 2026-11-01 (после CI)

**Software gate G3 закрыт** на HEAD `e1872af08efbff7ee7c9ac771e6b9eb70b748c46`. GitHub Actions run [41337768801](https://github.com/Kiddos19882/AutoDraw/actions/runs/41337768801) завершён со статусом `success`; jobs `geometry-tests`, `executor-tests` и `Windows portable build and startup smoke-test` все успешны.

Три дефекта, выявленные последовательными проверками CI, исправлены в коммитах `bf52f12`, `6594e28` и `e1872af`: лишняя скобка, расположение тестовых методов вне unittest-класса и незакрытый docstring.

**Не смешивать два gate:**
- Software gate — закрыт автоматическими тестами и удалённым Windows portable build/startup smoke-test.
- Local/live gate — ещё открыт. Требуется локальный Windows preflight (portable запуск, калибровка кисти, Clear/чистая доска, игровая canvas, Game Monitor heartbeat), затем полный live G3 block.

G3 остаётся экспериментально не выполненным: нет 27 подтверждённых live captures. Не делать выводов о влиянии `point_step_px` или `point_delay_ms` на CHALK до измерений. Не запускать отдельные задачи вручную и не переходить к модели расхода до проверки всех девяти конфигураций и трёх повторов.


## 2026-11-01 — удалено визуальное подтверждение размера кисти после Game Monitor

По замечанию оператора устранены два последовательных диалога, которые требовали визуально подтвердить радиус после автоматической установки:
- `integrated_app.py::_start_brush_test_executor` больше не спрашивает пользователя, совпадает ли размер кисти с запрошенным;
- `BrushBehaviorTestTab._confirm_brush_before_test` больше не показывает `askyesno` после точного подтверждения Game Monitor.

Проверка не ослаблена: executor допускается к запуску только после свежего heartbeat Game Monitor с точным совпадением фактического радиуса и запроса. В handoff добавлена повторная fail-closed проверка `observation.radius == requested_brush`; при расхождении запуск блокируется. Источник проверки и факт автоматического подтверждения сохраняются в `experiment.json`, поле `visual_confirmation_required=false`. Потеря Monitor, отсутствие свежего heartbeat, несовпадение радиуса, ошибка коррекции или записи manifest по-прежнему останавливают тест.

Для G1/G2/G3 block runner это убирает лишний popup после каждого автоматического drag; Clear/blank-board и остальные обязательные предупреждения не затрагивались. Добавлены regression tests: точный Monitor radius запускает callback без диалога, mismatch блокирует handoff.

Изменения в commits: `bb32589cb9d450a03b1d5b5264732828812b8ed3`, `465346a58caf76b8566d99128361095324368366`, `c919610999c5ea9f4a1afebad937395e586dc4b9`. Требуется новый полный CI на изменённом HEAD; до его завершения успешный CI предыдущего G3 HEAD не распространяется на эти изменения.


## Актуальное состояние G3 и CI — 2026-11-01 (проверено на актуальном HEAD)

**Последний подтверждённый HEAD:** `3dbf8f20bcea44c61290e49398e1a4daf182dbf9`  
**Ветка:** `feature/image-geometry-optimization`  
**GitHub Actions run:** [41340237207](https://github.com/Kiddos19882/AutoDraw/actions/runs/41340237207) — `completed / success`.

Все три обязательных jobs завершились успешно на этом exact HEAD:
- `geometry-tests` — success;
- `executor-tests` — success;
- `Windows portable build and startup smoke-test` — success.

Run включает commit `8c93a498864973b9879c926627030bb7e1d3ce2a` с интеграционным regression test `AutoDrawUnifiedApp._start_brush_test_executor`. Поэтому прежнее замечание, что run `41340056751` не покрывал последний тестовый commit, закрыто новым run `41340237207`.

### Разделение статусов

- **G3 software gate:** CLOSED — реализация матрицы, regression coverage, полный CI и удалённая Windows portable build/startup smoke-test подтверждены.
- **Local Windows preflight:** OPEN — требуется запуск актуальной portable-сборки на рабочей Windows-машине, проверка профиля/калибровки кисти, Clear/чистой доски, игровой canvas и heartbeat Game Monitor.
- **Live G3:** NOT RUN — требуется полный блок 27/27: девять сочетаний шага/задержки × три повтора.
- **Ресурсная модель G3:** NOT CONFIRMED — нет live captures, поэтому влияние `point_step_px` и `point_delay_ms` на фактический CHALK пока неизвестно.

### Автоматическое подтверждение радиуса кисти

Визуальные popup-подтверждения после установки кисти удалены. Handoff остаётся fail-closed: требуется свежий heartbeat Game Monitor и точное совпадение фактического радиуса с запросом; mismatch/устаревшие данные/ошибка коррекции или записи manifest блокируют запуск. Предупреждение о возможной очистке тестовой доски сохраняется.

### Workflow и ветки

Workflow `.github/workflows/geometry-tests.yml` запускается на push feature-ветки при изменениях релевантных путей и вручную через workflow_dispatch; дублирующий pull_request trigger удалён. PR #3 с base `ci/g3-validation-base` остаётся временным CI-only PR и не должен сливаться. `master` не изменялся.

**Следующее действие:** выполнить локальный Windows preflight; только после его успешного завершения запускать полный G3 block. Не запускать отдельные ячейки вручную и не строить модель расхода до проверки всех 27 captures.


## 2026-11-01 — временная блокировка live G3 из-за focus-steal

Оператор сообщил, что после установки кисти AutoDraw автоматически появляется поверх игры. Найдена причина в успешном пути `_complete_brush_radius_feedback()`: окно восстанавливалось до handoff Stage6. Исправление внесено: при автоматическом запуске executor окно остаётся свёрнутым; ручная установка сохраняет старое поведение. Добавлен regression test.

Кодовые коммиты: `8f8923ded3d788e725206d31515d6f0ed221db3a`, `fd814517b584b9a800c95e4b6a19581a7afc33ce`. Новый CI ещё не подтверждён. G3 live capture приостановить до успешного CI и проверки обновлённой сборки; уже полученные данные не переинтерпретировать и не удалять.

## 2026-11-01 — исправление маршрутизации G3 после двух невалидных запусков

На HEAD `a747b112969f0a69a3b04b701aec00a4cadc161d` исследованы два запуска G3 из серии `chalk-20261101-232008-3e9348`. Оба завершили шесть штрихов и получили точный расход 718 CHALK, однако оба были попытками одной и той же первой задачи `paint_consumption_long_lines-s2-d20-r3`. В execution report фактически указано `point_step_px=2`, `point_delay_ms=10`, тогда как журнал требовал `2/20`. В manifests отсутствовала G3 matrix identity, поэтому analyzer корректно отклонил попытки с `block_task_identity_missing`. Эти данные не засчитываются в G3.

Причина — конфликт двух матриц: `paint_consumption_long_lines` совпадает с `MATRIX_SCENARIO_ID` старой радиусной матрицы и одновременно входит в `GEOMETRY_MATRIX_SCENARIOS`. В `BrushBehaviorTestTab.create_and_transfer_plan` legacy-ветка стояла первой и перехватывала задачу автоматического G3-блока. Stage6 уже имел корректную передачу временного `executor_config_override`, но она активируется только при наличии G3 metadata; без metadata исполнитель оставался на стандартных 2/10.

Исправление: legacy-ветка теперь выбирается только для запуска без активной задачи block runner. Если задача принадлежит автоматическому блоку, тот же scenario_id маршрутизируется в geometry matrix и получает `chalk_experiment_matrix` плюс `chalk_test_block`. Добавлен regression test на коллизию scenario ID. Это сохраняет старый radius-matrix workflow.

Кодовый commit `85ae43af292e8c8ecdb4d1e5791a27db4a06a97c`; regression test commit `60117ef34db54a5bf858c946d7b5ca09137caa44`. Runtime Game Monitor connection snippets удалены из репозитория, а шаблон `connection_snippet_*.js` добавлен в `.gitignore`.

**Статус:** CI на исправленном HEAD должен быть проверен. Live G3 не запускать до успешного полного CI и обновления локальной Windows-сборки. Затем создать новую серию G3 (27 задач); два старых блока оставить в истории и не возобновлять. Live G3 и модель влияния sampling на CHALK пока NOT CONFIRMED.

## 2026-11-02 — оптимизация CI и усиление G3 regressions

Текущий HEAD после workflow/test changes: ожидает подтверждения новым GitHub Actions run. Ветка остаётся `feature/image-geometry-optimization`; `master` не изменялся.

Оптимизирован `.github/workflows/geometry-tests.yml`:
- push trigger ограничен feature-веткой и релевантными source/test/build paths; дублирующий pull_request trigger удалён;
- concurrency отменяет устаревшие промежуточные runs одной ветки;
- pip cache добавлен в Python jobs;
- Game Monitor, Preparation, Integration и Executor тесты разделены на независимые jobs и выполняются параллельно;
- корневые интеграционные тесты разбиты на три pytest группы: UI/G3 handoff; build/import/test-runner; geometry validator/metrics. WebSocket suite выполняется отдельно в Game Monitor job.;
- portable build зависит от успеха всех тестовых jobs; в CI build пропускает повторный `run_all_tests.py` через `AUTODRAW_SKIP_TESTS=1`, а обычный локальный build по-прежнему выполняет тесты;
- длительные Stage 5/7/8 и synthetic benchmarks переведены на ручной `workflow_dispatch` с отдельным boolean input; по умолчанию они выключены.

Усилено G3 regression coverage: добавлен тест, проходящий через реальный `BrushBehaviorTestTab.create_and_transfer_plan` и проверяющий, что block task формирует оба G3 identity объекта и сохраняет параметры задачи вместо legacy radius metadata. Тест handoff в `tests/test_unified_app.py` проверяет передачу 2/20 в executor.

**Пока не подтверждено:** новый CI на конечном HEAD, portable artifact после новых изменений, локальный Windows preflight и live G3. Два предыдущих запуска по 718 CHALK остаются невалидными G3 попытками и в матрицу не включаются. Новый 27-task block создаётся только после прохождения всех software gates и проверки/закрытия старого paused journal через recovery UI.

Дополнительная стабилизация UI regression suite: тесты UnifiedAppCoreTests теперь изолируют DATA_PATHS во временном каталоге на каждый тест. Это исключает чтение сохранённых paused G3 journals во время CI и появление модальных recovery dialogs. Deferred recovery scan в Brush Test tab отменяется при уничтожении его owner frame; добавлен regression test. UI test step ограничен тремя минутами, остальные root groups имеют отдельные таймауты.

## 2026-11-02 — частичный live G3 capture (commit 094381f)

Серия `chalk-20261102-015749-7c1141`, block `c8876401458b4197aee39bab33ae8e5f`, была остановлена после 22 попыток из 27 задач: 21 completed, 1 failed, 5 pending. Из 22 experiment manifests 21 имеют полный Monitor capture, один capture для `point_step_px=4 / point_delay_ms=10 / repeat=2` имеет статус partial и 434 `monitor_dropped_events`; executor при этом завершил 6/6 штрихов, а CHALK delta остался exact. Причина закрытия блока — `monitor_capture_gate_timeout:partial`. Блок остановлен и закрыт, не является paused-блоком для обычного resume.

Во всех 22 manifests фактические `execution_report.executor_config` совпадают с task metadata; radius=10, шесть штрихов. Внутренний CHALK counter exact и совпадает с sampled pointDelta. У всех trajectory summaries остаётся `incomplete_until_verified` из-за coalesced pointDelta.

Полные значения, таблица девяти ячеек и ограничения анализа записаны в [CHALK_G3_PARTIAL_RESULTS_2026-11-02.md](CHALK_G3_PARTIAL_RESULTS_2026-11-02.md). Предварительно delay=20 ms даёт существенно больший расход CHALK, чем 5/10 ms; меньший point_step также повышает расход. Это пока не универсальная формула: четыре ячейки неполны, радиус фиксирован на 10, геометрия только длинные горизонтальные линии.

**Статус:** live G3 PARTIAL / NOT COMPLETE; ресурсная модель CHALK NOT CONFIRMED. Для завершения исходной матрицы не хватает пяти pending задач и одного корректного повтора вместо failed partial capture. Перед новым запуском требуется проверить, допускает ли validator объединение continuation-блока с этой серией; закрытый block не возобновлять вслепую.

### Дополнение — проверка recovery semantics G3 (2026-11-02)

Проверен код `chalk_test_blocks.py` и UI recovery на HEAD после документации. Обычный claim не работает для `stopped`; recovery scan не поднимает stopped journals; retry разрешён только для единственной `interrupted` task, а не для `failed`; G3 plan builder всегда создаёт 27 задач. Поэтому штатный workflow не поддерживает continuation из шести задач для закрытого блока. Не возобновлять его вручную и не редактировать журнал. Следующий штатный G3 запуск — новый полный блок 27 задач. Если требуется сохранить 21 валидный capture и выполнить только шесть недостающих, сначала нужно отдельно разработать и протестировать continuation/aggregation semantics.

## 2026-11-02 — установлена причина partial G3 capture: переполнение буфера Game Monitor

Диагностика кода и реального `session.json` сессии `e3ba66d3-93ba-4f0f-aaf0-bc271d30f6e1` установила причину `monitor_dropped_events=434`: локальный массив `game_monitor.js` достиг лимита `MAX_EVENTS=50000`. После заполнения массива события перестают сохраняться в локальный export buffer, но `emit()` продолжает вызывать подписчиков; Browser Bridge продолжает получать и отправлять события.

Подтверждённый баланс сессии: 252 события уже были в Monitor при подключении + 50 320 событий, отправленных Bridge = 50 572; локальный массив содержит 50 000, cumulative droppedEvents=572. Browser Bridge sentEventCount=50 320, collector received_event_count=50 320, sendFailureCount=0, received_message_count=last_sequence=52 324. Для failed G3 run сохранено 744 события, RunRecorder dropped_events=0, CHALK=363 exact и sampled delta совпадает. Значение 434 — накопительный счётчик всей сессии, а не число пропущенных событий этого run.

Корень ошибки в учёте: `RunRecorder.heartbeat()` переносит глобальный `status.droppedEvents` в конкретный run, а acceptance gate трактует его как per-run loss. В результате capture ошибочно стал `partial`. Код не менялся; выполнена детерминированная симуляция поведения лимита; live рисование и CI не запускались.

Полный разбор и рекомендуемая схема исправления: [GAME_MONITOR_BUFFER_OVERFLOW_ANALYSIS_2026-11-02.md](GAME_MONITOR_BUFFER_OVERFLOW_ANALYSIS_2026-11-02.md). Исторический G3 journal остаётся неизменным и `stopped`; задним числом не переписывать его статусы. Следующая задача — разделить глобальный buffer overflow, bridge send failures, collector transport gaps и per-run recorder drops, добавить regressions и только после этого открывать новый live G3.
## 2026-11-02 — исправлена семантика Game Monitor overflow и per-run acceptance

На `feature/image-geometry-optimization` внесено исправление: cumulative `monitor_dropped_events` больше не трактуется как потеря событий конкретного run и не блокирует capture acceptance. RunRecorder фиксирует start/end/delta для локального buffer overflow и Monitor errors; отдельно фиксируются `bridge_send_failures_delta`, `collector_sequence_gap_count` и per-run `dropped_events`. Сервер теперь выявляет пропуски WebSocket sequence и связывает их с активным run.

Brush Test gate и матричные валидаторы G1/G2/G3/radius matrix проверяют только per-run метрики потерь/ошибок. Legacy cumulative aliases остаются в отчётах для диагностики и совместимости. Старые manifests и stopped G3 journal не переписывались.

Добавлены regression tests: Node subscriber delivery после 50 000 buffer entries; Python isolation cumulative overflow/errors от последующего run; WebSocket sequence gap; matrix validators accept cumulative overflow but reject per-run bridge/collector loss.

**Пока не подтверждено:** прохождение нового CI на конечном HEAD, локальный Windows/Firefox preflight и live повтор G3. До этого новый live G3 не запускать. Подробности — `BRUSH_MONITOR_AUTOCAPTURE_DESIGN.md` и `source/game_monitor/README.md`.


## 2026-11-02 — live G3 завершён: 27/27 captures приняты

**Контрольная точка первичных данных:** commit [35ae78e31f9b6d357a4e8aa30cd12307d8c322e8](https://github.com/Kiddos19882/AutoDraw/commit/35ae78e31f9b6d357a4e8aa30cd12307d8c322e8).  
**Ветка:** `feature/image-geometry-optimization`.  
**Серия:** `chalk-20261102-031830-a0f325`; block ID `d5d28990cb954610aa7f58534be9d3d7`.

G3 block имеет статус completed: 27/27 задач, все девять сочетаний `point_step_px` 1/2/4 × `point_delay_ms` 5/10/20 представлены тремя повторами. Радиус во всех опытах — 10. Все 27 captures имеют exact CHALK, совпадение суммы pointDelta, 6/6 завершённых штрихов и сохранённый Monitor report.

Per-run transport gates чистые: `dropped_events=0`, `monitor_error_count_delta=0`, `bridge_send_failures_delta=0`, `collector_sequence_gap_count=0`. В шести поздних captures был положительный delta переполнения локального export buffer Monitor; при этом RunRecorder/Bridge/collector не потеряли события конкретных runs. Накопительный `monitor_dropped_events` не является per-run loss.

Ключевой результат для шести длинных горизонтальных линий (2400 логических px, radius=10):
- step=4, delay=5/10: около 365 CHALK;
- step=2, delay=5/10: около 717–718 CHALK;
- step=1, delay=5/10: около 1350 CHALK;
- delay=20 увеличивает расход относительно 5/10 примерно на 53–95% в зависимости от шага.
Средние и повторы приведены в [CHALK_G3_RESULTS_2026-11-02.md](CHALK_G3_RESULTS_2026-11-02.md).

Экономичный кандидат для длинных линий — step=4 с delay=5 или 10 ms. Это пока не production default: качество, непрерывность и точность линий при более редком sampling требуют отдельной проверки. Предыдущая radius matrix по радиусам 1–30 не выявила систематической зависимости CHALK от размера кисти для того же сценария; G3 фиксировал радиус 10 и не является новой радиусной матрицей.

**Следующая активная работа:** INT-006 — сегментированная модель прогноза CHALK с отдельными коэффициентами для геометрии и режима ввода; далее — визуальная валидация экономичного режима и проверка на коротких/диагональных/криволинейных штрихах. Старый stopped G3 block и его первичные данные не изменять.


## Актуализация INT-006 — предварительная модель CHALK (2026-11-02)

- Последний документальный HEAD до этой актуализации: `b2788e5772a6fe4b50d718f0e106602c3fbe706a`; рабочая ветка — `feature/image-geometry-optimization`.
- G1 принят 12/12, G2 — 18/18, G3 — 27/27; radius matrix — 21 опыт. Первичные данные не изменялись.
- Для прямых штрихов G1 при radius=10 и executor `point_step_px=2 / point_delay_ms=10` построена предварительная регрессия: `CHALK ≈ 1.765 + 0.2988 × L`, 36 per-stroke наблюдений, обучающий RMSE около 0.48 CHALK. Независимая validation-выборка ещё отсутствует.
- Короткие штрихи выделены в отдельный lookup-сегмент; G2 показывает, что повторный проход 200 logical px расходует 61–62 CHALK, то есть не является бесплатным покрытием.
- G3 подтвердил отдельную зависимость расхода длинных горизонтальных линий от sampling profile; радиус не показал систематического влияния на pointCount в принятой radius matrix.
- Проверка метаданных шести G3 captures step=4 показала 6/6 ROI с изменениями для delay=5 и delay=10, но текущая эвристика не измеряет непрерывность, пропуски покрытия или отклонение траектории. Визуальный gate остаётся открытым.
- Подробная модель: `docs/CHALK_PRELIMINARY_SEGMENTED_MODEL_2026-11-02.md`.
- Следующий шаг INT-006: выполнить pixel-level аудит сохранённых PNG для step=4/5 и step=4/10; затем подготовить независимую validation-серию. До этого модель не использовать как production estimator и не менять универсальные настройки executor.

**Текущие ограничения:** код не менялся; live-тесты не запускались; step=4 не утверждён как production default; точный CHALK по-прежнему определяется только pre/post `pointCount`.


## Актуализация визуального gate G3 — 2026-11-02

- Получены непосредственно из GitHub и просмотрены шесть исходных `after_draw-board.png` для step=4/delay=5 и step=4/delay=10 (по три повтора).
- Во всех шести изображениях визуально подтверждены шесть непрерывных горизонтальных линий без заметных разрывов/пропусков; ширина и межлинейное расстояние выглядят стабильными.
- Между delay=5 и delay=10 визуальной разницы не обнаружено. Средний CHALK: 365.67 против 365.00; длительность и move calls практически одинаковы.
- Визуальный gate закрыт только для длинных горизонтальных линий сценария G3. Правый конец шестой линии частично закрыт курсором; точная форма этого окончания не подтверждена.
- Новый отчёт: `docs/CHALK_G3_VISUAL_QUALITY_AUDIT_2026-11-02.md`.
- Следующий шаг: проверить step=4 на диагоналях, поворотах, коротких штрихах и пересечениях; затем независимая validation модели.
- Production defaults не менялись; код не менялся; live-тесты не запускались.


## INT-006 — первичный скрининг PNG V1–V5 (2026-11-02)

- Просмотрены 15 оригинальных `after_draw-board.png`: по одному representative capture на каждый профиль P0/P1/P2 в каждой фазе V1–V5.
- В просмотренных PNG не обнаружено очевидных разрывов/пропусков штриха при step=4 относительно P0 для диагоналей, ломаных, контуров и узлов.
- Подтверждены ограничения тестовых данных: пересечения в V1/V3; короткие штрихи V2 выглядят точками при requested radius=10; курсор частично закрывает один контур V4; spacing=8 logical px в V5 сливается в общую полосу.
- Это предварительный визуальный скрининг, не pixel-level segmentation. Численные max gap, centerline deviation, width/width variation и closure metrics не рассчитаны.
- Следующий активный подэтап: количественный аудит всех 45 PNG с проверкой segmentation masks относительно blank-board reference и исключением курсора/UI.
- Подробности: [CHALK_INT006_PNG_SCREENING_2026-11-02.md](CHALK_INT006_PNG_SCREENING_2026-11-02.md).

**Статус INT-006:** IN_PROGRESS. Production code, executor defaults и estimator не менялись.


## INT-006 — инвентаризация PNG и блокер количественного аудита (2026-11-02)

- По Git tree data commit `6479536` подтверждено наличие 45/45 experiment manifests, 45/45 Monitor reports, 45/45 blank board references и 45/45 after-draw board PNG (270 PNG всего в шести capture-категориях).
- Blank/reference board сохранён для каждого run; данные достаточны для differential segmentation.
- Количественные pixel metrics не публиковались: бинарные PNG доступны через GitHub connector preview/base64, но не доступны как локальные файлы для OpenCV в текущем runtime; raw GitHub download из контейнера блокируется отсутствием DNS/network.
- Отчёт: [CHALK_INT006_PNG_SCREENING_2026-11-02.md](CHALK_INT006_PNG_SCREENING_2026-11-02.md), разделы 7–8.
- Следующий шаг: выполнить пакетную сегментацию в checkout-среде, где доступны PNG и зависимости Pillow/NumPy/OpenCV; сохранить per-stroke JSON/CSV и diagnostic overlays. Сначала проверить маски на одном capture каждой фазы/профиля.
- Pixel-level gate остаётся OPEN. Production code, defaults и estimator не менялись.


## INT-006 — количественный pixel-level аудит выполнен (2026-11-02)

- На кодовом HEAD `d3971e4` GitHub Actions run [41392156994](https://github.com/Kiddos19882/AutoDraw/actions/runs/41392156994) завершился success: все обязательные jobs, Windows portable build/startup smoke-test и INT-006 PNG audit успешны.
- Анализатор обработал 45/45 captures V1–V5; capture_valid=45, invalid=0, matrix missing/duplicate/unexpected=0, batch failures=0. Созданы 252 per-stroke записи, 279 pair records, JSON summary и diagnostic overlays/masks.
- Coverage=1.0 и gap_count=0 для всех строк в пределах оцениваемой траектории; эти значения не закрывают quality gate автоматически. 9/54 штрихов V2 length_10 имеют evaluable_path_fraction=0.381 и path_metrics_sufficient=false.
- V5: 9/144 пар имеют candidate mask overlap и ink masks touch/merge; все относятся к близкой паре spacing≈8.01 logical px. Это не устанавливает универсальный безопасный spacing.
- V4 rectangle/triangle closure seam подтверждён; irregular_polygon closure metric отсутствует. V1/V3 сохраняют multi-component/intersection ambiguity.
- Подробные метод, P0/P1/P2 таблицы, ограничения и дальнейшие действия: [CHALK_INT006_PIXEL_AUDIT_2026-11-02.md](CHALK_INT006_PIXEL_AUDIT_2026-11-02.md). Артефакт CI: [ZIP](https://github.com/Kiddos19882/AutoDraw/actions/runs/41392156994/artifacts/13117572972).
- **Историческая фиксация на момент исходного pixel audit:** тогда требовались исправленные V1/V3, короткие штрихи и V5 spacing sweep. Эти live follow-up впоследствии выполнены и прошли повторный pixel audit; актуальный статус см. в разделах ниже. Независимая validation модели и safety margin остаются впереди; INT-007 остаётся BLOCKED.
- Production executor, estimator, defaults и первичные captures не менялись.


## 2026-11-02 — подготовка V2/V5 follow-up

- Brush Test UI содержит отдельные V2 follow-up (5 штрихов: 12/16/20/24/30 logical px) и V5 spacing sweep (16 штрихов: X/T/крест и пять пар spacing 8/12/16/20/24 logical px).
- Новые scenario IDs изолируют результаты от исходных V2/V5 captures. Matrix metadata и block planner ожидают соответственно 5 и 16 strokes; обе серии имеют 9 задач (P0/P1/P2 × 3 повтора), radius=10.
- Regression tests проверяют точные длины V2 и пять расстояний V5. Кодовые изменения: 1f2917a, 8a012de, 230fe22, 3d6754c, ef8b704, 94c3c87.
- Новый протокол: [CHALK_INT006_V2_V5_FOLLOWUP_2026-11-02.md](CHALK_INT006_V2_V5_FOLLOWUP_2026-11-02.md). На момент подготовки live captures ещё не выполнялись; впоследствии все V1–V5 follow-up были выполнены (45/45) и зафиксированы в `e879a77`. Production executor, estimator и sampling defaults не изменялись.


- Дополнительная совместимость: прежние V2/V5 scenario IDs оставлены в legacy phase map для повторного анализа старых manifests; новые block planners используют только новые follow-up IDs. Regression test подтверждает принятие старых IDs.


**Проверка исправления положения курсора:** CI run [41486593544](https://github.com/Kiddos19882/AutoDraw/actions/runs/41486593544) для code/test HEAD `878bd1f79e3a0249576e36c02cb63ca9825e31d1` завершился success: Game Monitor/bridge, integration, executor, Preparation/G3, Windows portable build/startup smoke-test и INT-006 PNG audit прошли. В follow-up manifests commit `e879a77` записано перемещение курсора ниже `board_area` и `paint_meter_area` с margin=32 px; pixel audit 45 новых captures в run `41496555297` подтвердил cursor_detected=false и cursor_exclusion_pixels=0 для всех 45.


## 2026-11-02 — live follow-up V1–V5 завершён

- Пользователь добавил 45 follow-up captures в commit [e879a77](https://github.com/Kiddos19882/AutoDraw/commit/e879a77f63be7a7a68de3f09091eab7dba0d34a2): 5 фаз × 9 задач; все block journals completed.
- Все 45 captures приняты для exact CHALK: pre/post pointCount валидны, sampled per-stroke delta совпадает с exact delta; requested radius=10; per-run Monitor/Bridge drops, errors и sequence gaps равны нулю.
- Step=4 снизил расход на 38.5–49.4% относительно step=2 по пяти геометриям. При step=4 отличие delay=5/10 ms не превышает примерно 1.4% по среднему расходу. Подробные repeat values: [CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md](CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md).
- Новые captures записывают post-draw cursor ниже доски и paint meter, с исключением обеих ROI и отступом 32 px. Paint-meter estimate inconclusive и не используется как источник расхода.
- **INT-006 остаётся IN_PROGRESS:** pixel-level аудит новых 45 PNG завершён в run `41496555297`: 297/297 strokes coverage=1.0, zero gaps; V4 seams 27/27 covered; V5 spacing threshold documented. Следующий gate — независимая validation на полных DrawingPlan и safety margin.
- Все серии выполнены при requested radius=10; влияние радиуса в этом follow-up не измерялось. Production executor defaults и estimator не менялись.


## CI: series-aware INT-006 PNG audit — 2026-11-02

Первый run на commit e879a77 (41493449244) обнаружил 90 captures вместо ожидаемых 45 и false duplicate matrix cells: анализатор не различал исходную и follow-up серии. При этом все 90 captures были valid, missing/unexpected cells и batch failures отсутствовали. Исправлено: matrix identity включает series_id + phase, проверка 9 cells выполняется отдельно для каждой серии; CSV/JSON сохраняют series_id. Добавлены regression tests для одинаковых ячеек в разных series и для настоящего duplicate внутри одной series.

Полный CI run [41496555297](https://github.com/Kiddos19882/AutoDraw/actions/runs/41496555297) на HEAD 956ce2b — **SUCCESS**: Game Monitor/bridge, integration, executor, Preparation/G3, series-aware pixel audit, Windows portable build/startup smoke-test. PNG artifact: [autodraw-int006-png-analysis](https://github.com/Kiddos19882/AutoDraw/actions/runs/41496555297/artifacts/13165359929). Portable build artifact: [autodraw-g3-preflight-build](https://github.com/Kiddos19882/AutoDraw/actions/runs/41496555297/artifacts/13165884603).


## 2026-11-02 — аудит готовности независимой validation

Статически проверены `chalk_experiment_matrix.py`, `chalk_test_blocks.py`, `brush_behavior_test_ui.py`, `integrated_app.py` и `tests/analyze_chalk_experiment_matrix.py`. D1–D5 отсутствуют в текущих matrix scenarios/expected counts, block planner/journal, Brush Test UI и allowlist executor override. Общий analyzer валидирует telemetry manifests и агрегирует repeats, но не сравнивает их с immutable frozen prediction records и не рассчитывает validation residuals.

Поэтому независимый протокол не готов к live запуску, несмотря на ранее указанное READY FOR LIVE VALIDATION. Статус исправлен на BLOCKED. Создан `CHALK_INT006_HARNESS_READINESS_AUDIT_2026-11-02.md`; следующий шаг — расширить существующий harness и добавить regression tests. Production estimator/defaults, исходные данные и master не менялись. Кодовые тесты и live captures в рамках этого аудита не запускались.


## 2026-11-02 — INT-006 software gate PASS

В ветке `feature/image-geometry-optimization` реализованы D1–D5, 45-cell block journal, 15 frozen prediction records, hash-sealed artifact и независимый analyzer. Prediction ID связывает journal task, matrix metadata и executor handoff.

Полный CI [41513389663](https://github.com/Kiddos19882/AutoDraw/actions/runs/41513389663) завершился **SUCCESS** на code commit `ca8c9b3bd739ea0a5b557b87fc0106ecfde81216`: Preparation/G3 — 667 passed, 82 subtests passed; Application integration, Executor regression, Game Monitor/bridge, pixel-level audit и Windows portable build/startup smoke-test — success. Artifact `autodraw-g3-preflight-build` ID `13173632860`.

Следующий gate — локальный Windows 10 preflight. 45 live captures не выполнялись. Production estimator/defaults и master не менялись. См. [frozen predictions/analyzer](CHALK_INT006_FROZEN_PREDICTIONS_AND_ANALYZER_2026-11-02.md) и [local preflight guide](CHALK_INT006_LOCAL_PREFLIGHT_GUIDE_2026-11-02.md).


## Уточнение статуса FILL-001 после аудита UI/runner — 2026-11-03

Проверка текущего дерева на HEAD `01cb37d6cb8fc7c5ec56e648330abda31875f15b` показала, что FILL-001 пока нельзя запустить через интерфейс AutoDraw. Stage 6 runtime binding — только post-execution hook, ожидающий готовый `experiment_context`; UI/runner не создаёт FILL-001 task и не передаёт её в Executor. В Brush Test UI нет FILL001 phase, а executor override allowlist её не содержит.

Следовательно, software gate runtime binder закрыт, но пользовательская интеграция не завершена. Шаг 3 временного плана расширен: сначала UI/runner и fail-closed DrawingPlan handoff, затем Windows live preflight. Шаги 4–5 остаются BLOCKED. Подробности — [аудит интеграции](CHALK_FILL001_AUTODRAW_INTEGRATION_AUDIT_2026-11-03.md).


---

## Историческая запись — совместимость legacy CHALK journals (2026-11-02)

- Подтверждён источник ошибки при запуске: корректный completed V2 journal использует исторический `int006_short_strokes` (6 штрихов), тогда как validator принимал только follow-up ID `int006_short_strokes_followup` (5 штрихов). Все 9 задач в найденном журнале completed, matrix cells уникальны.
- Validator обновлён: V2/V5 принимают соответствующие legacy IDs с собственными expected stroke counts; запрет дублирования и смешения сценариев сохранён.
- Regression tests добавлены для legacy V2 и V5. Commits: `f0e05df`, `4847cce`.
- Полный CI для commits `f0e05df` и `4847cce` подтверждён run `41496555297`. Workflow checkout рабочей ветки выполнен в 18:01:55 UTC после появления commit `956ce2b`; compare подтверждает, что `f0e05df` и `4847cce` являются его предками. Job Preparation/G3 завершился: 662 passed, 82 subtests passed. Все обязательные jobs, Windows portable build и INT-006 PNG audit — success; optional benchmarks skipped. Не удалять и не редактировать старые journals вручную.
- Production executor, estimator, defaults, experiment data и master не менялись.
- Статическая проверка `chalk_test_blocks.py`, `chalk_experiment_matrix.py` и regression tests подтвердила legacy ID mapping V2/V5, собственные expected stroke counts и запрет смешивания сценариев внутри одного журнала. Дополнительно CI `41496555297` успешно выполнил Preparation/G3 suite: 662 passed, 82 subtests passed. Legacy compatibility gate закрыт.


## 2026-11-03 — FILL-001 CI run 41692129486: software gate подтверждён

- GitHub Actions run [41692129486](https://github.com/Kiddos19882/AutoDraw/actions/runs/41692129486) завершился SUCCESS. Application integration, Game Monitor/Bridge, Preparation/G3, Executor regression, INT-006 pixel-level PNG audit и Windows portable build/startup smoke-test — SUCCESS; optional algorithm benchmarks — SKIPPED.
- Windows portable artifact `autodraw-g3-preflight-build`, ID `13258221572`, не истёк: [скачать artifact](https://github.com/Kiddos19882/AutoDraw/actions/runs/41692129486/artifacts/13258221572).
- Дополнительно опубликованы INT-006 CHALK validation, INT006R live validation, PNG analysis и visual-review source artifacts.
- FILL-001 шаги 1–2 и программная часть шага 3 подтверждены CI. Шаг 3 остаётся IN_PROGRESS до одного Windows live preflight из вкладки FILL-001 с проверкой runtime identity, фактического P1 и before/after PNG на реальном client ROI.
- Шаги 4–5 остаются BLOCKED. 45 live captures не запускались и не разрешаются этим CI результатом.
- Изменения кода, production estimator/defaults и `master` в рамках этой проверки не выполнялись; локальный `git status` недоступен через GitHub API.


## 2026-11-04 — FILL-001-RS CI closure and INT-006/INT006R evidence review

- GitHub Actions run [41780241017](https://github.com/Kiddos19882/AutoDraw/actions/runs/41780241017) завершился SUCCESS на code/test HEAD `0f23731848f0c148fe5e1309d1e305576dd4b6b7`. Application integration, Executor regression, Preparation/G3, Game Monitor/Bridge, INT-006 pixel-level PNG audit и Windows portable build/startup smoke-test — SUCCESS; optional benchmarks — SKIPPED.
- Preparation/G3 выполнил exhaustive FILL-001-RS static spacing sweep и опубликовал artifact `autodraw-fill001-rs-static-sweep` (ID `13299430831`). Sweep: 3 frozen shapes × 5 radii, 2,238 candidates, 62 accepted; все 15 selected cells удовлетворили offline gate coverage ≥99% и leakage=0. Это raster simulation: estimated_sampling_points не является exact CHALK, game renderer/live executor этим sweep не проверяются.
- INT-006 PNG audit artifact `autodraw-int006-png-analysis` (ID `13299470914`): 90/90 captures valid, 0 invalid, 549 stroke rows, coverage=1.0 для всех строк, 0 gaps. Это подтверждает pixel-level geometry audit на опубликованных captures.
- INT-006 frozen CHALK analyzer artifact `autodraw-int006-chalk-validation` (ID `13299121807`): 45/45 accepted, 0 missing, 0 rejected. При этом `safety_margin_status=not_established`, `production_eligibility=not_validated`; validation report не разрешает переносить frozen model в production.
- INT006R radius × geometry artifact `autodraw-int006r-live-validation` (ID `13299101877`): 45/45 accepted, 0 missing/rejected; точные CHALK values связаны с pre/post pointCount. При P1 (point_step=4, delay=5 ms) средний расход по radius 1/10/30 составил: D1 62.667/62.333/63.333; D2 71.667/71.000/71.000; D3 100.000/100.667/99.667; D4 14.333/14.667/15.333; D5 88.333/89.667/89.667. Различия малы и не монотонны; это не подтверждает универсального правила «больше радиус — меньше CHALK».
- INT006R PNG evidence artifact `autodraw-int006r-visual-review-source` (ID `13299381257`) содержит 180 файлов для 45 пар captures. Analyzer сообщает `png_evidence_status=complete`, но `visual_quality_gate=pending_manual_review` для всех 45 runs. До полного визуального review нельзя закрыть visual gate.
- Production estimator/model, executor defaults, sampling defaults, frozen predictions и live captures не менялись в рамках этого CI review. Реальные игровые эксперименты в этой сессии не запускались.
- Следующий gate: завершить ручной visual review 45 пар INT006R before/after PNG; отдельно принять решение по safety margin и production eligibility для INT-006; FILL-001-RS preflight capture не переоткрывать автоматически только на основании software CI/static sweep.

## 2026-11-04 — FILL-001-RS: локализация дефектов в offline-модели

- Повторно воспроизведена frozen rectangle mask и planner raster model для `rectangle / radius=10 / scanline_row_step=5 / offset=0`. Получены исходные 27 centerlines, совпадающие с committed plan; frozen target area — 44 653 px.
- В planner OpenCV-модели остаются 304 uncovered target pixels (0,6808%); все они находятся в заданных краевых полосах: верхняя — 80, нижняя — 80, левая средняя — 72, правая средняя — 72; внутренний центральный участок — 0. Модель leakage=0. Это подтверждает краевую локализацию **только для offline raster model**, а не для фактических 11 leakage и 1,5694% недопокрытия PNG capture.
- Дополнительно смоделирован один замкнутый contour pass после 27 scanlines: contour centerline построен по маске, эродированной эллиптическим ядром с inward offset 6/7/8 px; в OpenCV-модели все три варианта дали coverage 99,516270% / 99,372942% / 99,328153% соответственно и leakage=0. Offset 5 дал leakage=32 и отклоняется. Это только exploratory raster candidate, не проверка игрового renderer.
- Pixel-coordinate breakdown исходной after.png и 11 leakage pixels всё ещё не завершён; сравнение с предыдущим capture не выполнено. Нельзя считать фактическую edge-gap причину доказанной.
- Capture остаётся REJECTED, 45-task matrix BLOCKED. Не менялись code/tests/configuration/frozen plan/thresholds/production defaults; live experiments не запускались. Следующий gate — pixel-level breakdown исходных PNG и сопоставление с renderer footprint, затем отдельное разрешение на новый live preflight.

## 2026-11-04 — actual PNG residual diagnostics: CI instrumentation added

- Исходные `before.png` и `after.png` подтверждены в рабочей ветке; визуально просмотрена фактическая пара. Corrected audit остаётся coverage=98.430600%, leakage=11, capture REJECTED.
- В replay test добавлен test-only pixel diagnostic: повторяет screen-mask mapping audit, вычисляет uncovered/leakage координаты, распределение по зонам и строкам, connected components, а также расстояния пропусков до scanline centerlines по точным affine screen endpoints.
- Изменения тестовые, не меняют production audit, frozen mask/plan, thresholds, runtime defaults и исходные PNG.
- Commits: `e62b69295f9df1c67a485a5c900fbcf1ceba87eb`, `d337f4240e83488273152f65992032beca395781`.
- Результат вычисления пока PENDING: локальная рабочая копия недоступна, GitHub combined status не вернул CI statuses; запуск и лог Preparation/G3 требуют подтверждения. Не считать actual pixel breakdown завершённым.
- Capture остаётся REJECTED, 45-task matrix BLOCKED. Live эксперименты не запускались.
## 2026-11-04 — FILL-001-RS actual PNG residual coordinates confirmed

Workflow 41787492122 for commit d337f4240e83488273152f65992032beca395781 completed successfully. Preparation/G3 job 126432951884: 804 passed, 24 warnings, 82 subtests passed. Executor regression, Game Monitor/Bridge, application integration, INT-006 PNG audit, Windows portable build/startup smoke-test all SUCCESS; optional algorithm benchmarks SKIPPED.

Committed before/after PNG replay:
- corrected PNG audit: coverage=98.430600%, leakage=11, status=failed;
- uncovered target pixels: 1116;
- spatial zones: top=244, bottom=239, left-middle=134, right-middle=499, interior/other=0;
- largest uncovered component bbox screen xywh=[460,63,33,178], area=870;
- other components: [88,90,2,122] area=142; [101,233,13,7] area=54; [101,64,13,6] area=41; small components 6,1,1,1 pixels;
- nearest scanline centerline distance bands: <=2px=10, 2–5px=320, 5–10px=786, >10px=0;
- leakage coordinates: (116,63),(117,63),(92,78),(91,81),(90,83),(90,84),(89,85),(90,85),(90,218),(116,240),(117,240).

Direct pixel evidence shows residuals concentrated at target perimeter / scanline endpoint zones; the configured interior/other zone contains 0 pixels. The largest residual is along the right perimeter. Leakage is sparse near the left perimeter and upper/lower rounded corners. This supports prioritizing perimeter/endpoint coverage rather than changing the interior row step. It does NOT prove game brush footprint, cap shape, radius semantics, or a particular contour offset.

Planner OpenCV model had 304 uncovered logical pixels, actual PNG diagnostic found 1116 screen pixels. These are different raster spaces and renderer models; do not treat counts as interchangeable.

Capture remains REJECTED; 45-task matrix remains BLOCKED. Exact CHALK remains 1260 from the existing live run. No new live experiment. Frozen plan, mask, thresholds and production code unchanged.


**Уточнение renderer API:** в bundle Main UI задаёт nominal stage.frameRate=48 и StageScaleMode.NO_SCALE. PainterPopup создаёт BoardPane 460×240 без собственного scaleX/scaleY. Egret Engine 5.2.18 API документирует omitted caps/joints как ROUND; версия реально подключённого runtime игры пока не подтверждена. Поэтому round caps/joins — ожидаемое поведение совместимого Egret, не установленный факт для текущей игровой сборки.


**Новый planner risk:** brush_footprint_geometry возвращает прямоугольный bbox capsule; interior_fill_planner._mark_footprint и outline_first_fill_planner помечают весь bbox covered. У круглых концов углы bbox могут не входить в реальный capsule, что потенциально создаёт underfill. Не доказано как причина FILL-001-RS (там использовался scanline plan). Требуется отдельная exact cell-footprint модель после подтверждения runtime transform.

**CI телеметрии:** workflow 41840582147 SUCCESS на code/test commit 6fd3c91c3c08ea05cb9ef83ff599eb52a6f9527e: Application integration, Game Monitor/Bridge, Preparation/G3, Executor regression, Windows portable build/startup smoke-test и INT-006 PNG audit — SUCCESS; optional algorithm benchmarks — SKIPPED. Более поздние commits содержат только документацию.
## BRUSH-FOOTPRINT-CAPSULE-001 — candidate implementation status

Добавлен отдельный offline candidate `swept_capsule_pixel_masks()` с двумя масками: potential cells для safety/leakage envelope и guaranteed cells для conservative coverage under-approximation. Учитывается non-uniform scale через обратное преобразование pixel-cell bounds в logical space; bounding box используется как broad-phase. Добавлены regression tests на endpoints, point/disk, anisotropic scale, polyline reversal/round join, clipping и malformed inputs.

Code commit: `5a090948ecbe927807fde4ffc5337132d131b765`; test commit: `7ffdd150ba42840737cba5f2143370e56d67bed3`. CI run [41842587672](https://github.com/Kiddos19882/AutoDraw/actions/runs/41842587672) ещё выполняется на момент записи. Planner integration не выполнялась; текущие outputs/defaults не изменены. Модель предполагает ideal round-capped capsules и не является доказательством фактического Egret renderer.

---

## BRUSH-FOOTPRINT-CAPSULE-001 — CI evidence update

Первоначальный capsule-mask candidate прошёл полный CI [41842587672](https://github.com/Kiddos19882/AutoDraw/actions/runs/41842587672): 820 passed, 24 warnings, 82 subtests; обязательные regression jobs, INT-006 PNG audit и Windows portable build/startup smoke-test — SUCCESS; optional benchmarks SKIPPED. FILL-001-RS static sweep: 2 238 candidates, 62 accepted, 15/15 selected cells passed. Windows artifact: `13329303700`.

После этого добавлены independent analytic oracle и небольшое уточнение conservative tolerance semantics: potential cells используют strict positive-area test без вычитания epsilon; guaranteed cells требуют margin внутрь capsule; boolean axis scales отклоняются. Эти последние commits `336d66f`, `8aeb66a`, `7357f3e` ещё требуют повторного CI. Run [41843716918](https://github.com/Kiddos19882/AutoDraw/actions/runs/41843716918) на HEAD `7357f3e` ожидает выполнения.

Planner integration и live renderer validation не выполнялись. Generic capsule model остаётся offline candidate; FILL-001-RS capture остаётся REJECTED и 45-task matrix BLOCKED.

---


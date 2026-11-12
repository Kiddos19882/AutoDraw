# AutoDraw — реестр проверенных результатов

**DOC-CODE-REUSE-001 / cross-domain AST consumer expansion (2026-11-12):** [code `fe4a1de`](https://github.com/Kiddos19882/AutoDraw/commit/fe4a1de300fc670373b76be52341385423569cae), [tests `4e696f3`](https://github.com/Kiddos19882/AutoDraw/commit/4e696f34c1176e5502136040961e712f3b9f4b9d) и [fixture fix `f2e5919`](https://github.com/Kiddos19882/AutoDraw/commit/f2e5919e659f558b19de6fea7d2631bee3eab542). E1 verified diff: scan includes `integrated_app.py`, narrow cross-domain bare owner imports for executor, positive synthetic imported aliases and explicit negative decoy; regression for CAP-009/012/013 real consumers. **Tests E2 NOT_VERIFIED, CI E3 UNKNOWN**: no push-triggered workflow details from connector; do not reuse previous CI `43135827499` as PASS for new source. No new E4/E5 evidence.

**DOC-CODE-REUSE-001 / новый adapter refactor (2026-11-12):** E1 SOURCE/DIFF подтверждён: [`4eb81f5`](https://github.com/Kiddos19882/AutoDraw/commit/4eb81f58c86bae3ed59fba97b624076082bdbfbd), [`1b2a8c6`](https://github.com/Kiddos19882/AutoDraw/commit/1b2a8c601725ce3618fa70c2adc9b6b4dc22f379), [`be48666`](https://github.com/Kiddos19882/AutoDraw/commit/be486666dd64c6d4dd341794e0cfeb984dd45f14), [`4dfec5c`](https://github.com/Kiddos19882/AutoDraw/commit/4dfec5cdd9b8cf973fe109c925f7314100872e84). Сохранены dense=(1,0), frozen spaced table, неизменные планировщик/маски/политики и запрет на live input по offline manifest. Добавлены тесты all 15 shape×radius spacing cells, отказ при неизвестном методе/cell, cross-check 30 preview и signed source signatures. **Эти новые тесты не имеют подтверждённого запуска/CI: E2 NOT_VERIFIED, E3 UNKNOWN**, несмотря на SUCCESS более раннего [43135827499](https://github.com/Kiddos19882/AutoDraw/actions/runs/43135827499). Game runtime E4/E5 NOT_RUN.

**DOC-CODE-REUSE-001 / static consumers:** [CI 43135827499](https://github.com/Kiddos19882/AutoDraw/actions/runs/43135827499) **SUCCESS** на `23a5a516e788b2030663fc7ad11b3604dee3c5a4`: 10/10 unittest PASS, 20/20 catalog entries (AST), 129 Python-файлов для source inventory; обнаружены 2 all-scope import SCC-кандидата и 0 unconditional root-level SCC в `source/preparation`. Тесты проверяют алиасы, вложенные импорты, связанный owner/call, root SCC и отказ при повреждённом Python. При root SCC инструмент `--usage` возвращает ненулевой exit code; CI проходит лишь при его отсутствии. [Artifact `capability-usage.json`](https://github.com/Kiddos19882/AutoDraw/actions/runs/43135827499/artifacts/13906713385) включает все 20 карточек, кандидатов consumers и циклы. Данные не показывают runtime import failure, E4/E5 или качество рисунка; E4 сериального quota recovery по-прежнему NOT_RUN.



## DOC-CODE-REUSE-001 — baseline структурного каталога (2026-11-12)

**Навигация и модульность инструментария:** [CI 43126121772](https://github.com/Kiddos19882/AutoDraw/actions/runs/43126121772) SUCCESS на `dd9ec43e3fbda91053151d109549332f24e1bf3d`: 8/8 unit tests, 20 валидированных AST entrypoints, 5/5 запросов в реальном каталоге (очистка, Selenium, CHALK, lock, расход краски), 100/100 Markdown indexed, 0 catalog errors, 0 duplicate DEC IDs, 0 historical SHA errors. Поиск `--find` возвращает `E1_CANDIDATE_ONLY`, не доказательство отсутствия альтернатив и не E4. Модуль проверки вынесен в `tools/capability_catalog.py`, публичный CLI `check_markdown_docs.py` сохраняется.

На baseline source SHA `7cc938af4e349bd187981749d47f7e41c207ce24` выборочно сверены определения 20 точек входа в Firefox/Selenium, Monitor/ROI, Clear/ENGINE-001, FILL001 Stage6/manifest/runner, CHALK, PNG, brush-radius и owner-lock. Карточки содержат пути к existing regression files, но их существование **не равно** PASS. В существующий Markdown audit добавлена проверка Python AST и ссылок на тесты без импорта и исполнения модулей; тесты охватывают отсутствующий путь, отсутствующий аргумент и дублирование ID. **Фактический E2/E3 PASS:** [docs-integrity CI 43124607337](https://github.com/Kiddos19882/AutoDraw/actions/runs/43124607337) SUCCESS на `7b8f4aaa`; 7 unit tests PASS, 100/100 Markdown indexed, 20/20 capability records, 0 catalog errors, 0 missing links, 0 duplicate decisions, 0 corrupt history. Это не semantic/runtime проверка. Нет нового game E4/E5 и нет измерения CHALK.


## FILL001-SERIES-001 — первичная E4 BLOCKED и quota-limited E2/E3 (2026-11-12)

[Raw commit 5acb2e6](https://github.com/Kiddos19882/AutoDraw/commit/5acb2e6284a4425cdfea8812257fa85ea55ed88f) подтверждает пользовательскую E4 попытку, а не серию PASS. Серия ef09de5bce19: scheduled=6, accepted=0, первая задача rectangle/dense_scanlines/radius1, planned_strokes=141, completed_strokes=100, Stage6 error Exact game remaining quota below 300-point safety margin. Pre snapshot pointCount=1, перед остановкой Monitor видел pointCount=5759, remainingPoints=241, maxPoints=6000. Mouse release PASS. Но after_settled_png, closed binding, actual_chalk и game PNG quality отсутствуют; report/summary имеют BLOCKED и NOT_EVALUATED. Не приписывать exact CHALK=5758 до валидной привязки к конкретному закрытому run. Последняя session.json после дополнительных действий содержит pointCount=1 и не может служить post snapshot остановленного рисунка.

В том же raw commit присутствует отдельный одиночный V5 trim (другая сессия): 29/29, exact pre=1/post=1709, CHALK=1708, screen coverage 99.3637286%, active FILL001_CHALK_FIRST_PERIMETER_V2 quality PASS. Это не подтверждает переход через Clear в серии.

Новый E1/E2 путь [90701e8](https://github.com/Kiddos19882/AutoDraw/commit/90701e8adb22cada121ccc6f1a2f5076baca1fde) допускает QUOTA_LIMITED только для проверенного Stage6 resource guard, run-bound префикса выполненных штрихов, exact terminal quota, released mouse, settled PNG/quality diagnostic; partial не попадает в ranking и не увеличивает completed_with_bound_chalk. Первая серия CI [43114144219](https://github.com/Kiddos19882/AutoDraw/actions/runs/43114144219) FAIL: две старые позитивные фикстуры без поля actual_chalk. Исправлено [1236ce9](https://github.com/Kiddos19882/AutoDraw/commit/1236ce9d8f6ea8438294d31948a51226a1c70563), E3 [43114349659](https://github.com/Kiddos19882/AutoDraw/actions/runs/43114349659) SUCCESS 148 passed; последующие tally-уточнения [6eae2c9](https://github.com/Kiddos19882/AutoDraw/commit/6eae2c94a7cd72c6be3662374c9cb816c16a17e2) [series CI 43114637544](https://github.com/Kiddos19882/AutoDraw/actions/runs/43114637544) SUCCESS. [Main CI 43114637531](https://github.com/Kiddos19882/AutoDraw/actions/runs/43114637531) SUCCESS. Новый E4 quota recovery и независимая E5 NOT_RUN, production eligibility FALSE.
## FILL001-SERIES-001 — финальный CI перед пользовательским E4 smoke (2026-11-12)

[Series safety CI 43109628909](https://github.com/Kiddos19882/AutoDraw/actions/runs/43109628909) и [AutoDraw validation CI 43109630346](https://github.com/Kiddos19882/AutoDraw/actions/runs/43109630346) **SUCCESS** на последнем code SHA `0e5075bdecf0557752533b46837b1401cf138427`; в общем workflow Egret browser reference, Application integration, Executor regression, Preparation/G3, Game Monitor/Bridge, INT-006 PNG audit `SUCCESS`; optional benchmarks и Windows portable startup `SKIPPED`, а не PASS. [Docs integrity CI 43110095756](https://github.com/Kiddos19882/AutoDraw/actions/runs/43110095756) SUCCESS на documentation SHA `367009bf315afaec170e6dcce38289fec79ce5fd`. Новый Selenium mode regression — **только AST/source contract**, CI не запускает пользовательскую игру. E4 двухфигурной последовательности **NOT_RUN**, E5 **NOT_RUN**; никакого измеренного game CHALK новой серии пока нет. Протокол первого E4 см. [TASKS.md](TASKS.md).

## FILL001-SERIES-001 — Selenium mode isolation и проверка без игры (2026-11-12)

**Baseline:** `5bc388589013fcd47e34edfa3f469187b71166e7`; фикс [`0e5075b`](https://github.com/Kiddos19882/AutoDraw/commit/0e5075bdecf0557752533b46837b1401cf138427) только `chalk_fill_ui.py` и `tests/test_fill001_series_firefox_probe.py`. E1: общий `_firefox_worker` по-прежнему создаёт один Selenium Firefox WebDriver и подключает Game Monitor/Bridge; V5 trim fixture теперь строится только после раннего выхода series-ветки. E2: новый `test_series_firefox_mode_does_not_depend_on_v5_trim_candidate` — структурная AST/source-contract проверка расположения вызовов, **не** фактический Firefox/Selenium runtime-тест. E3: [dedicated series safety CI 43109628909](https://github.com/Kiddos19882/AutoDraw/actions/runs/43109628909) **SUCCESS** на `0e5075b`: регрессии, UI syntax check и offline manifest smoke. [Общий AutoDraw validation 43109630346](https://github.com/Kiddos19882/AutoDraw/actions/runs/43109630346) — **SUCCESS**, обязательные jobs Application integration, Executor, Preparation/G3, Game Monitor/Bridge, Egret CanvasRenderer и INT-006 PNG audit `SUCCESS`; optional algorithm benchmarks и Windows portable build `SKIPPED` на том же SHA (по состоянию на запись). **Новый game E4/E5 NOT_RUN**; исторический V5 trim live PASS нельзя переносить на multi-figure series.


## FILL001-SERIES-001 — проверка кода интеграции и исторического Clear, 2026-11-11

**Историческая первичная E4:** ENGINE-001 one-click Brush Lab Clear 9/9 PASS на реальной игре, описано в GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md. Фактический Clear использует `pyautogui.click` откалиброванной кнопки и `evaluate_board_clear` с допуском 0.15% — критерий не изменён. **Новые series runtime E4/E5: NOT_RUN**; данные ENGINE-001 нельзя переносить на связку широких/узких масок автоматически.

**E2/E3 текущей интеграции:** [FILL-001 series safety 42975856803](https://github.com/Kiddos19882/AutoDraw/actions/runs/42975856803) и [AutoDraw validation 42975856883](https://github.com/Kiddos19882/AutoDraw/actions/runs/42975856883) **SUCCESS** на последнем code SHA `fea265f92aac` (GUI, Stage6, Clear, owner lock). Обязательные выполненные main CI jobs PASS: Application integration, Preparation/G3, Executor, Game Monitor/Bridge, Egret reference, INT-006 PNG audit; optional benchmarks и Windows portable build `SKIPPED`. Предыдущий [dedicated CI 42975744219](https://github.com/Kiddos19882/AutoDraw/actions/runs/42975744219) SUCCESS на `fcd29dc`. [Markdown CI 42976063009](https://github.com/Kiddos19882/AutoDraw/actions/runs/42976063009) SUCCESS на прежнем документационном SHA `3acc3dcdf69c`, не подтверждает игру. Исторический [series CI 42975584450](https://github.com/Kiddos19882/AutoDraw/actions/runs/42975584450) FAIL был связан с неверным expectation сообщения negative test, исправлен `fcd29dc` и проверен позже без ослабления safety. **Новые игровые E4/E5 для multi-figure series — `NOT_RUN`.**

## FILL001-SERIES-001 — offline factorial and safety validation, 2026-11-11

**E1/E2/E3, не live E4:** frozen `build_fixed_radius_fill_plan` и `FILL001_RS_SCANLINE_CONFIGS` дают 30 вариантов; каждый имеет подписанный immutable shape/method/radius и `estimated_sampling_points_are_exact_chalk=false`. [CI 42968857617](https://github.com/Kiddos19882/AutoDraw/actions/runs/42968857617) SUCCESS. [CI 42970208091](https://github.com/Kiddos19882/AutoDraw/actions/runs/42970208091) SUCCESS, 58 synthetic tests covering configurations, manifest tamper, source plan identity, Clear screenshot verification, grouped statistics and monitor/counter guards. No game input; real batch CHALK, quality, actual UI Clear NOT_RUN. Последующие изменения кода и GUI подтверждены E3 на `fea265f92aac` (см. выше); это не ретроактивный PASS каждого промежуточного SHA и не E4 новой серии. Historical red intermediate CI runs retained, not counted as final PASS.

## FILL-001 V5 — independently recomputed committed W2/W3 E5 PASS (2026-11-11)

Отдельный read-only E5 анализатор `source/preparation/fill001_v5_independent_e5.py` добавлен в [коммите `014132c`](https://github.com/Kiddos19882/AutoDraw/commit/014132cde1c2f708236ae8140a3c1067e6f1f7f7); независимый [GitHub Actions E5 run 42944487257](https://github.com/Kiddos19882/AutoDraw/actions/runs/42944487257) **SUCCESS** на workflow SHA [`dae4e18`](https://github.com/Kiddos19882/AutoDraw/commit/dae4e183712e0acde430f131aae45dc3940a5cbb). [Оригинальный JSON E5 отчёта — artifact 13822167330](https://github.com/Kiddos19882/AutoDraw/actions/runs/42944487257/artifacts/13822167330); схема `FILL001_V5_INDEPENDENT_E5_W2_W3_V1`, **2 accepted / 0 rejected / 0 missing**, overall PASS для **только двух сохранённых run-bound E4 артефактов**. Использует frozen logical mask как неизменённый вход, но независимо от рабочего `fill001_screen_mask_v2.py` вычисляет RGB `max(abs(after-before))>8`, screen projection и евклидовы расстояния через `scipy.ndimage.distance_transform_edt` (не production OpenCV); проверяет SHA PNG и mask, session/run IDs, exact counters, полные raw события, 29 planned pointer-downs с правильными radius, 5/4 zero-point slider moves, отсутствие gaps/errors.

**E5 W2 PASS:** original PNG hashes matched, target101529, covered100877, coverage99.357818948%, leakage599, outside3px=0, max1.327083 logical px, pre1→post1710 = CHALK1709, 29 paint events, 5 slider moves, **8176 raw events**. **E5 W3 PASS:** original PNG hashes matched, target101529, covered100897, coverage99.377517754%, leakage600, outside3px=0, max1.327083 logical px, pre1→post1707 = CHALK1706, 29 paint events, 4 slider moves, **8157 raw events**. Active quality `FILL001_CHALK_FIRST_PERIMETER_V2` PASS for both, historic strict V1/V2 diagnostic failures remain intact. W3 wins by **3 exact CHALK** across these two distinct qualifying runs, not yet a statistically repeatable benefit. **Independent runtime re-execution NOT_RUN; repeatability NOT_RUN; multi-color and wide/narrow holdout NOT_RUN; production eligibility FALSE.** Scoped E5 must not be presented as validation of general game quality, live repeatability or production estimator.

## FILL-001 V5 — W3 run-bound E4 and active PNG quality PASS (2026-11-11)

Новые неизменяемые [primary evidence `832bf2bd52a8f5a3ca908562b4723c2983d603b6`](https://github.com/Kiddos19882/AutoDraw/commit/832bf2bd52a8f5a3ca908562b4723c2983d603b6): candidate `K_trim_0_y189_w3`, attempt `8f770c4a-43a6-478f-b581-8af006cde6ec`, session `6f68db86-c831-42ec-a632-f62c8fba85b1`, closed run `ca3bfa8b-a339-4c11-9f98-ed3881a16ad7`. Original `fill001/v5_stage6_runs/v5-8f770c4a-43a6-478f-b581-8af006cde6ec/{report.json,before.png,after.png,after_settled.png}` and Monitor/Bridge JSON are archived. Stage6 29/29, 28×radius10→last radius3, 72.734 seconds, mouse release succeeded. Automated `EXACT_RUN_BOUND` gives settled pre1→post1707, **exact CHALK=1706**; four zero-point slider actions excluded; pointer parking before/after did not change exact count. Early Stage6 post1680 must NOT replace settled post1707.

Same frozen target SHA `ac1c6660e5986cdf534328c6dbcd5020f631168b1473c24b29e7609eb827998b` and byte-identical original before PNG SHA `b825d973ab46bf89d267e6324a48a99526109b9cda74018a59ae450a58a692a6` as preceding W2. Active `FILL001_CHALK_FIRST_PERIMETER_V2` **E4 quality PASS**: coverage `0.9937751775354825` (100897/101529), screen leakage 600, zero pixels beyond 3 logical px perimeter, max overshoot 1.327083 logical px. Historic V1 diagnostic FAIL and V2 diagnostic FAIL unchanged. Against quality-PASS W2 `1c722ba` (1709 CHALK; coverage 0.9935781894828078; 599 leakage), **W3 saves 3 CHALK (0.176%) in these individual runs** and is a *provisional* candidate under DEC-030. One accepted run per candidate: repeatability and independent E5 **NOT_RUN**. Independent raw Bridge event replay and PNG pixel recalculation were NOT performed by this review: repository connector did not supply complete large closed-run JSON or independent binary PNG pipeline; do not mislabel report reconciliation as E5. No production promotion, frozen mask, policy, estimator or executor default change.

[AutoDraw validation 42923577993](https://github.com/Kiddos19882/AutoDraw/actions/runs/42923577993) **E3 SUCCESS** at `832bf2b`: required integration, bridge, preparation/G3, executor, Egret and INT-006 PNG audit jobs SUCCESS; optional algorithm benchmarks and Windows portable build SKIPPED. Three additional measurements/offline workflows at this SHA SUCCESS. Independent FILL-001 E5 is separate from CI. Documentation in the original evidence commit still referenced W3 as future; this section supersedes that stale next-step wording without altering history.

## FILL-001 V5 — W2 run-bound exact CHALK1709 + active PNG quality PASS (2026-11-10/11, E4)

Immutable [evidence commit `1c722ba`](https://github.com/Kiddos19882/AutoDraw/commit/1c722ba82be2c91b03570460101061df74e6b9a2), `fill001/v5_stage6_runs/v5-51480631-902c-47b1-b782-5fc74596246d/report.json`, original `before.png`/`after.png`/`after_settled.png`, `game_monitor_bridge/d0999212-c9d0-437e-90a9-26d03a5ffaa3/game-monitor-run-20261110T231212351769Z-c36be38c.json` and `session.json`. Stage6 29/29 completed in 75.657s, 28×radius10→2, safe mouse release PASS. Raw closed Bridge run `c36be38c-98c5-4654-b598-3ec3f07bf4c3` 34 pointer candidates =29 consuming painting plus 5 zero-delta slider operations, `execution_status=completed`, Monitor drops/errors/gaps/Bridge failures=0, `point_delta_matches_chalk=true`. Automated `EXACT_RUN_BOUND`: **pre1/post1710/CHALK1709**, early Stage6 post1687 not settled.

Pre/settled pointer parking at off-ROI screen (387,424), exact pointCount 1→1 and 1710→1710; original PNGs show clean pre and cursor-free filled rounded rectangle after. `after_settled.png` SHA256 `22c3487f13de891f1f38c2894fbc86cdc9497a122367cdbf22fcd70189a90519`. Active quality policy `FILL001_CHALK_FIRST_PERIMETER_V2` **PASS**: target 101529 px, covered 100877, uncovered652, coverage `0.9935781894828078`, leakage599, leakage beyond halo0, max overshoot1.327083 logical px vs3 allowed. Historical V1 PNG status FAILED and V2 diagnostic gate FAIL (strict zero leakage); neither is relabeled. Previous `36e95e4` CHALK1701 and active quality FAIL is preserved. **E5 NOT_RUN**, W3 NOT_RUN on this evidence. CI of latest source SHA separate from live and not evidence for E5.


## FILL-001 V5 — third W2 run: automatic CHALK E4 PASS, PNG quality FAIL (2026-11-10)

Immutable [commit 36e95e4](https://github.com/Kiddos19882/AutoDraw/commit/36e95e49acfecdbae1969bdf3d7358f06ea72f54): `fill001/v5_stage6_runs/v5-b28524eb-ea40-4ee9-9505-d526beef86e5/report.json`, original before/after/after_settled PNG, session `a8896ff8-be90-464a-9ea8-c403ae385071`, closed run `7d5357a5-5919-49bf-bd1f-732df0696af0`. Stage6 29/29, 75.578 s, mouse release PASS. Game Monitor closed exact pre1/post1702, auto `EXACT_RUN_BOUND` **CHALK1701**, 5 zero-point slider input exclusions, validated radii [10,2]; early Stage6 post1678 is not closed final post. Exact CHALK automatic regression now E4 PASS, independent E5 NOT_RUN.

Same-run `after_settled.png` captured and hashed; V2 frozen perimeter quality: coverage=0.9936865329117789, leakage=2963 screen px, 2230 beyond 3 logical px, max=48.146794 logical px => **FAIL**. V1 source audit failed as well. In raw before and settled screenshots, the visible game brush/cursor sprite moves, contributing RGB differences outside frozen shape; its quantitative share of leakage is NOT independently established, so do not retroactively change result. Preventive V5-only pointer parking code and synthetic tests at `c1fe1f8`/`1b48fb1`/`0ca2a42`; new live quality status NOT_RUN, E3 pending.



## FILL-001 V5 — second E4 and real-data regression, 3825d57

Primary immutable [commit 3825d57](https://github.com/Kiddos19882/AutoDraw/commit/3825d571eff4717efd8f5dbde88524cdc4387073): `fill001/v5_stage6_runs/v5-884678ea-76ec-405e-9067-56be4dfa7546/report.json`, `game_monitor_bridge/6c41cea3-8a5b-4340-aeba-1fbe3cc29327/game-monitor-run-20261110T163103037862Z-6f9bec0c.json`. E4 Stage6 29/29, 76.266 s, mouse released. Closed run 8133 events, 29 paint plus five zero-point slider actions, exact 1→1695 **CHALK1694**, `point_delta_matches_chalk=true`, drops/errors/gaps=0; early post1670 not final. Original finalizer BLOCKED/null and quality NOT_EVALUATED; settled PNG and independent E5 NOT_RUN. Previous ed74ffd source CHALK1706 is a separate run; no quality-accepted comparison yet.

**Defect reproduced by E3 on 88a12aa:** `test_real_3825d57_closed_bridge_replay_and_no_relaxed_guards` failed `V5 Bridge observed unexpected brush radii` because raw JSON uses floats `[1.0,2.0,8.0,10.0,30.0]` and old code demanded `type(v) is int`. See [failed workflow 42858034815](https://github.com/Kiddos19882/AutoDraw/actions/runs/42858034815). Corrected [252228c](https://github.com/Kiddos19882/AutoDraw/commit/252228cb054b1ab551ad0a2fd379f157d9ed0611), negative tests [6506774](https://github.com/Kiddos19882/AutoDraw/commit/650677409456483d330f0bd243ff9a17fa6cc167). New E3 CI pending at documentation write; no retroactive PASS.

## FILL-001 V5 — first 29/29 Stage6 live and closed Bridge exact measurement (2026-11-10, E4)

Primary archived [commit `ed74ffd629a5b8bdae6b76e2adea8c8bb0a399ba`](https://github.com/Kiddos19882/AutoDraw/commit/ed74ffd629a5b8bdae6b76e2adea8c8bb0a399ba), `AutoDraw_Stage20/data/results/brush_behavior_tests/fill001/v5_stage6_runs/v5-09d783ae-616c-4db3-a1c0-9dcc1c6a856f/report.json` + original `before.png` / `after.png`; `game_monitor_bridge/6bd34aee-0c60-41ad-9902-f4dfca8d8ed8/game-monitor-run-20261110T154452673488Z-b0afe0bf.json` and `session.json`; frozen candidate `K_trim_0_y190_w2`, source SHA `71cf46c0111cf141c99296981fb2a282c5468956b2c3dc3e442294c42aeef8db`. Stage6 execution `completed_strokes=29/29`, stable width sequence `10×28→2`, 76.125 seconds, mouse release PASS, before exact pointCount1; immediate Stage6 after snapshot 1681; its finalization `BLOCKED`, `actual_chalk=null`, quality NOT_EVALUATED.

Independent analysis of full closed 8176-event Game Monitor run `b0afe0bf`: `execution_status=completed`, exact `pre=1`, `post=1707`, `chalk.status=exact`, `chalk.consumed_points=1706`, `point_delta_matches_chalk=true`; `stroke_count=29`, `stroke_candidate_count=34`, `non_consuming_stroke_candidate_count=5`, all five extras lie outside verified BoardPane and consume zero points, 29 on-board starts match frozen `expected_pointer_down_client` in order exactly and show observed radius10 (first28) / radius2 (last). Monitor dropped/error/sequence gaps/send failures all zero. **Source exact E4 run measurement: CHALK1706**, without claiming original auto-report PASS, PNG quality PASS, or E5. The 26-point difference between early report and completed run reflects later game point updates; new future-run code uses settled evidence.

Separate archived attempt `e0bdb411-bbb0-4108-9443-b9a4c8b1451d`: 0/29, failed brush, no-response guard fired, old slider coordinates and no accepted game strokes. Other passive probes remain independent. Code/tests for strict slider-aware binding after this E4: `fill001_v5_finalization.py` and `test_fill001_v5_finalization.py`; new code CI E3 and live E4 pending at latest revision, no retroactive alteration of historical artifacts.


## FILL-001 V5 — first Stage6 run FAIL during slider, E4 2026-11-10

Primary [commit `fbb97ceda6bb2c2c14a20f09ef77796f80e72f97`](https://github.com/Kiddos19882/AutoDraw/commit/fbb97ceda6bb2c2c14a20f09ef77796f80e72f97): `AutoDraw_Stage20/data/results/brush_behavior_tests/fill001/v5_passive_roi/probe-0a84494695c641e8ab37afbc7c1ef0cf.json`; `fill001/v5_stage6_runs/v5-3084f7fd-d317-41c0-b502-74d444acaad7/{report.json,before.png,after.png}`; `game_monitor_bridge/45b7df72-50ee-4875-8ef4-f130db1e629f/{session.json,game-monitor-run-20261110T101506055036Z-d7b27e5c.json,game-monitor-run-20261110T101522065473Z-e32357ef.json}`. Passive mapping `PASSIVE_MAPPING_ONLY_NOT_EXECUTOR_READY` at 10:15:06.353Z, BoardPane ROI x483 y243 w694 h363; source SHA `71cf46c0...`. Single-run plan attempt `3084f7fd-d317-41c0-b502-74d444acaad7` E4 **FAIL**: 0 of 29 V5 strokes; exact board counter `1→1`, no user drawing attributed to V5, no brush confirmation. Bridge slider event stream at 10:15:11.610–10:15:22.065Z contains five `POINTER_DOWN_CANDIDATE` starting at client x1199,1306,1339,1349,1352/y193, game-reported `currentRadius=30` across all events. Run `e32357ef...` has `stroke_count=0`; do not misclassify these as game stroke input or compute V5 CHALK from unchanged session resource counters. Stage6 `status=failed`, `completed_strokes=0`, `mouse_release.succeeded=true`, `actual_chalk=null`, `game_png_quality=NOT_EVALUATED`. Exact error: `ColorPlanExecutionError: Не удалось скорректировать ползунок для радиуса 10: Разрешения координат ползунка недостаточно для дальнейшей коррекции.` No evidence proves the slider really moved. New source fix `40758c98` stops after one unchanged-radius drag and collects calibration diagnostics; tests `4003626b`; CI/E4 after fix separately.


## FILL-001 V5 — Windows passive Firefox ROI: PASS (2026-11-10, E4 limited scope)

Primary files: [commit `5b7e6b877d5793720ad856997ada97417bfaeaab`](https://github.com/Kiddos19882/AutoDraw/commit/5b7e6b877d5793720ad856997ada97417bfaeaab), `AutoDraw_Stage20/data/results/brush_behavior_tests/fill001/v5_passive_roi/probe-0cca08ef367643beaf6397a30ab410c6.json`; `game_monitor_bridge/b6ea0c33-a0c7-4332-9959-5836b619d338/session.json` и `game-monitor-run-20261110T063915979800Z-3c8e7de5.json`. E4 **PASS for passive BoardPane ROI calibration only**; candidate `K_trim_0_y190_w2`, session `b6ea0c33-a0c7-4332-9959-5836b619d338`, screen rectangle `x483 y243 width694 height363`, client→desktop offset `(0,+135)`, 3 exact report samples with buttons0, `no_fallback=true`, source geometry SHA `71cf46c0111cf141c99296981fb2a282c5468956b2c3dc3e442294c42aeef8db`. Source report `stage6_execution_allowed=false`, actual_chalk=null, game_png_quality NOT_EVALUATED. Later session samples do not constitute 29 V5 drawing strokes.

**Separate non-V5 event:** Bridge recorded completed run ID `3c8e7de5-87a5-4ee0-a864-d0c1df90b1c1`, pre exact `pointCount=2`, post exact `pointCount=3`, **CHALK=1** by run-bound delta, `stroke_count=1`, observed brush radius30, one accepted point. No evidence that this is a planned V5 trial, and cause/actor UNKNOWN; do not attribute to V5. The same session ends with `pointCount=3`, so *blank-board state is not validated*. V5 exact CHALK/PNG acceptance remain NOT_RUN; future use requires fresh run/session mapping and blank-board proof.


## FILL-001 V5 — второй Windows Firefox passive ROI, 2026-11-10 (E4 PARTIAL / BLOCKED)

Primary evidence: [commit `1bd38514fae99f572db519d14d3a2a6676f6b48c`](https://github.com/Kiddos19882/AutoDraw/commit/1bd38514fae99f572db519d14d3a2a6676f6b48c), `AutoDraw_Stage20/data/results/brush_behavior_tests/fill001/v5_passive_roi/probe-da4ee59649e041768a6b6eb1c6ecb117.json`, `.../game_monitor_bridge/df6adfd8-efaf-424d-b9e3-6a528b00607e/session.json`. Status **BLOCKED** при `captured_at_utc=2026-11-10T06:07:00.413296+00:00`. Firefox 159, `https://eufbpet.hust.me/pet.php`, Monitor 0.2.4 active, one validated BoardPane 460×240, Egret 5.4.1 WebGL, input telemetry enabled, exact `pointCount=1`, `remainingPoints=5999`, `maxPoints=6000`, `currentRadius=30`. Foreground gate: expected GeckoDriver PID 5372, native foreground before/after WebDriver focus PID 932. `passive_preflight_samples=[]` на закрытой сессии, `screen_roi=null`, `mapping=null`, `stage6_execution_allowed=false`. No native pointer movement, game strokes, exact V5 CHALK or PNG E5: **NOT_RUN**. Причина несовпадения (владение PID 932) **UNKNOWN**. Следующее Win32 focus-only исправление требует собственного code SHA E3 и независимого Windows E4.


## FILL-001 V5 — Firefox first Windows passive ROI run (2026-11-10, E4 PARTIAL)

Source: [commit `848aae2fcc12d38691346b1a45592c0f1fb2cb7c`](https://github.com/Kiddos19882/AutoDraw/commit/848aae2fcc12d38691346b1a45592c0f1fb2cb7c), `data/results/brush_behavior_tests/fill001/v5_passive_roi/probe-2a09a872a6d04a5db9e185a8a7a0ae8e.json`, `data/results/brush_behavior_tests/game_monitor_bridge/1c9e3ec8-dc80-4641-ae56-ecc3369b66c6/session.json`, frozen exported source `fill001/v5_source_plans/K_trim_0_y190_w2.json`. Monitor 0.2.4, correct game iframe origin, one Egret BoardPane, enabled Bridge telemetry, exact `pointCount=1`/`remainingPoints=5999`/`maxPoints=6000`, five passive `buttons=0` samples in retained final session — **observed E4 PARTIAL**. Diagnostic at 2026-11-10T05:53:25.450392Z: `status=BLOCKED`, `screen_roi=null`, `mapping=null`, `stage6_execution_allowed=false`, `blocked_reason="BLOCKED: Firefox is not proven to be the foreground window."`. Some final session samples are later than the blocked timestamp; do **not** interpret them as successful programmatic native mouse verification. No drawing, no real V5 CHALK, no PNG E5: **NOT_RUN**. Actual foreground PID vs GeckoDriver `moz:processID` not captured; root cause of focus mismatch **UNKNOWN**. No source report tampering or success reclassification. Follow-up regression and native focus re-check need their own code SHA and CI.


## FILL-001 DEC-030 native V5 — реальный Egret geometry screening, 2026-11-09

[Native CI 42694626385 SUCCESS](https://github.com/Kiddos19882/AutoDraw/actions/runs/42694626385) on code SHA `182b2915e7afeda90ae51ad50ccf719f15a001c9`; [artifact 13707703988](https://github.com/Kiddos19882/AutoDraw/actions/runs/42694626385/artifacts/13707703988) includes 9 original RGBA PNG, input fixture JSON, manifest, SHA provenance and `FILL001_CHALK_FIRST_NATIVE_AUDIT_V5`. Frozen rectangle SHA `ac1c6660e5986cdf534328c6dbcd5020f631168b1473c24b29e7609eb827998b`, 3× backing target 401877px. Native control V5 `V4_y190_w2_control` **bytewise decoded RGBA identical** to prior V4 `J_bottom_y190_w2`, source PNG SHA checked against V4 prior audit; 29 synthetic strokes every case. New V5 independent audit verifies case list, geometry, SHA for PNG/fixture/manifest, original V4 control and per-threshold Euclidean exterior distance from projected frozen mask.

| Native case | Coverage @alpha128 | Missing | Leakage backing px | Max exterior logical proxy px | Outside 3px? |
|---|---:|---:|---:|---:|---:|
| V4_y190_w2_control | 98.943707% | 4245 | 0 | 0 | 0 |
| K_trim_0_y190_w2 | **99.425944%** | 2307 | 54 | 1.000000 | 0 |
| K_trim_0_y189_w3 | **99.426939%** | 2303 | 54 | 1.000000 | 0 |
| K_trim_1_y190_w2 | 98.973318% | 4126 | 13 | 0.666667 | 0 |
| K_trim_1_y189_w3 | 98.974314% | 4122 | 13 | 0.666667 | 0 |
| K_trim_2_y190_w2 | 98.952445% | 4210 | 3 | 0.333333 | 0 |
| K_trim_2_y189_w3 | 98.953440% | 4206 | 3 | 0.333333 | 0 |
| K_trim_3_y190_w2 | 98.943707% | 4245 | 0 | 0 | 0 |
| K_trim_3_y189_w3 | 98.945449% | 4238 | 0 | 0 | 0 |

Native trim0 sensitivity: alpha1 coverage99.527467/99.529209%, leak88, max1px; alpha64 coverage99.471978/99.473222%, leak70, max1px; alpha254 coverage99.259724/99.260968%, leak32, max0.666667px (W2/W3). Far leakage beyond 3 logical px always 0. More alpha-level detail, missing bottom/left/right and rejected cases preserved in JSON. `native_screening_gate=QUALIFIED_FOR_LIVE_EVALUATION` **не является DEC-030 game quality PASS**. Full regression [42694767248](https://github.com/Kiddos19882/AutoDraw/actions/runs/42694767248) executes on later test SHA `617866cf` — no claims before completed jobs. Exact game CHALK for V5 NOT_RUN; real E4/E5 screen/multi-color NOT_RUN. No production change.


**Дополнительный fail-closed контракт на code SHA `33fa812e4a81f9c03b2f5b43660eeb4f21018e9d`:** E4 source report обязан иметь `status=PASS_E4_RAW_CAPTURE` и поля `before/after.board_roi_sha256`/`roi_size`, `screen_roi`, `run_id`, `session_id`, `task_id`, `plan_signature`, `monitor_version`, `raw_run_sha256`, `exact_chalk`; все сверяются с реальными source files и binding. Synthetic regression проверяет отказ при изменении after PNG без изменения E4 SHA, затем отдельно качество изображения при согласованных SHA, а также несовпадающий E4 exact CHALK. Старый capture и frozen legacy status неизменны. Explicit V3-only mapping проходит только через действующий независимый BoardPane provenance validator. [CI 42645465734](https://github.com/Kiddos19882/AutoDraw/actions/runs/42645465734) — E3 status по завершении обязательных jobs, E4 game run для DEC-030 NOT_RUN.


## FILL-001 DEC-030 — separate full run-bound acceptance code and regressions (2026-11-09)

Code SHA `8e2920b9d7410f596a89684ed3f85d44eaafb479` [AutoDraw validation 42643765113](https://github.com/Kiddos19882/AutoDraw/actions/runs/42643765113): `chalk_fill_matrix.py` выделяет shared capture invariants (task/run/plan/mask/P1, exact pointCount delta, per-stroke chalk sum, no dropped events/Bridge failures, PNG SHA fields) и отдельный `validate_fill001_chalk_first_capture()` с явным policy ID, source raw-run/E4 SHA, same-run ROI, `active_quality_gate=PASS`, coverage≥99%, halo≤3 logical px и нулём far-away leakage. Legacy `validate_fill001_capture()` по-прежнему требует zero leakage и historical `png_audit_status=passed`.

`chalk_fill_capture_adapter.py` строит отдельный `build_fill001_chalk_first_capture_from_runtime()`: persisted session/executor/Bridge raw run → existing fail-closed runtime binding → existing E4 `bind_from_monitor_run()` → original Monitor event and pointCount parsing → unchanged old PNG audit fields + new independent run-bound screen quality → new policy validator. Regression suite: synthetic new-quality PASS with positive leakage, legacy validator still FAIL, new quality fail for >3 px, wrong run/hash/plan/ROI, broken event delta/Bridge errors. Интеграционный тест использует **mock E4 binder**, сам binder проверяется отдельно в существующем suite; он не доказывает actual game E4. Ни один новый live-run не выполнен; exact CHALK новых реальных планов NOT_RUN. Final full CI conclusion привязывать к указанному SHA после завершения всех обязательных jobs.


## FILL-001 — новая политика PASS после прямого решения пользователя, 2026-11-09

**Протокол** `FILL001_CHALK_FIRST_PERIMETER_V2`, [DEC-030](DECISIONS.md#dec-030-fill-001-новый-pass-с-ограниченной-утечкой-и-приоритетом-фактического-chalk). Новая формула: changed = max RGB difference >8 в run-bound screen ROI; target = неизменный frozen screen projection; coverage≥0.99; для каждого leaked pixel `distance_to_target_screen_px/min(validated_pixels_per_logical_x,validated_pixels_per_logical_y)≤3` (евклидова метрика; min scale консервативен). Сохранять total leakage, far-away leakage count, maximum overshoot logical px, coverage и все source hashes. Screen mapping valid/same-run обязательно; без независимого геометрического binding не заявлять game-quality PASS. Величина CHALK не выводится из PNG: ранжирование только после exact post/pre pointCount, валидированного monitor/session/run. Это новая acceptance-policy version, не re-label V4 native alpha FAIL и не V1 исторических screen results.

**Кодовая реализация:** `source/preparation/fill001_screen_mask_v2.py` и `source/preparation/tests/test_fill001_screen_mask_v2.py`. Тесты: inside/3logical halo accepted, 4logical detached fail, screen scaling 3×, missing>1% fail, invalid geometry scaling fail, optional-policy screen audit returns legacy FAIL alongside new PASS. Проверка E3 должна отдельно подтвердить CI на SHA реализации; не трактовать PASS unit-tests как real E4. Старый capture adapter и 45-task matrix по-прежнему используют frozen leakage=0 до отдельной versioned integration.


## FILL-001 native bottom repair V4 — controlled negative/positive evidence, 2026-11-09

**Provenance enhancement (same frozen V4 protocol):** [native E3 run 42577013425](https://github.com/Kiddos19882/AutoDraw/actions/runs/42577013425) SUCCESS on `7814eec3`; [artifact 13655990846](https://github.com/Kiddos19882/AutoDraw/actions/runs/42577013425/artifacts/13655990846) contains exact input `fixture-input.json` in addition to PNG/manifest/provenance/alpha report. Verified raw input SHA equals both `fixture-provenance.json.fixtureSha256` and `native-bottom-audit-v4.json.source_fixture_sha256`. All control/candidate alpha≥128 measurements remain exactly as in table below. Test-only `5d3c5904` adds a fail-closed SHA tamper regression; full validation run on its SHA is evaluated separately. This does NOT add any E4/game-screenshot evidence.



[Native CI run 42576168617](https://github.com/Kiddos19882/AutoDraw/actions/runs/42576168617) SUCCESS on code SHA `c7ddbb1342e2deb9b3550bef88d59e3c116d43a8`; [V1/V2/V3/V4 source PNG, manifests, provenance and independent V4 report artifact 13655800959](https://github.com/Kiddos19882/AutoDraw/actions/runs/42576168617/artifacts/13655800959). Frozen rectangle SHA `ac1c6660e5986cdf534328c6dbcd5020f631168b1473c24b29e7609eb827998b`; real BoardPane/Egret 5.4.1 WebGL, browser-local 1380×720 nearest-3× projected 401877 target pixels. Native V4 control `G_trim_3_control` **RGBA identical** to original V2 `G_trim_3`; 28 original strokes unchanged. Six 29-stroke variants append X=97..363, row Y189/190, width1/2/3; no game runtime.

| Candidate | Coverage alpha≥128 | Missing total | Missing bottom | Leakage total |
|---|---:|---:|---:|---:|
| G_trim_3_control | 98.344021% | 6655 | 2457 | 0 |
| J_bottom_y189_w1 | 98.344021% | 6655 | 2457 | 0 |
| J_bottom_y190_w1 | 98.941467% | 4254 | 56 | 0 |
| J_bottom_y189_w2 | 98.344021% | 6655 | 2457 | 0 |
| J_bottom_y190_w2 | 98.943707% | 4245 | 47 | 0 |
| J_bottom_y189_w3 | 98.945449% | 4238 | 43 | 0 |
| J_bottom_y190_w3 | 98.946941% | 4232 | 36 | **2414 below target** |

Independent alpha sensitivity: at alpha≥1 control missing6469/leak2, y190_w2 missing4057/leak2, y189_w3 missing4049/leak2; y190_w3 leak2421. Alpha≥254 y190_w2 missing4504/leak0, y189_w3 missing4496/leak0, y190_w3 leak2407. No case passes 99% coverage and 0 leakage together on local-native alpha proxy. One width3 stroke **must not be placed at y190**, unlike y189, where no new leakage was measured. Even perfect bottom-only repair leaves 4198 missing, 98.955402% coverage. Game PNG quality is NOT_EVALUATED for V4 and historical FILL001 live gate remains FAIL; exact new candidate CHALK NOT_RUN, independent native-to-live Stage/screen E5 NOT_RUN. [Full validation CI 42576168620](https://github.com/Kiddos19882/AutoDraw/actions/runs/42576168620) status separate.


## FILL-001 spatial native residual V1 — независимые зоны дефекта (2026-11-09)

[Native CI SUCCESS 42573526457](https://github.com/Kiddos19882/AutoDraw/actions/runs/42573526457), [artifact 13653904396](https://github.com/Kiddos19882/AutoDraw/actions/runs/42573526457/artifacts/13653904396); code SHA `b31fbe2f239d84b0bda84c77fc3e350d0cab7ba0`. Frozen rectangle SHA `ac1c6660e5986cdf534328c6dbcd5020f631168b1473c24b29e7609eb827998b`. Repeated real `BoardPane`/Egret WebGL native capture, no new game runtime. Independent `FILL001_NATIVE_CONTOUR_SPATIAL_AUDIT_V1`: native alpha≥128, 1380×720 nearest-3× target (401877 target pixels), top/bottom=first/last 3 target backing rows, left/right=18 px band per intermediate target row, interior=remaining. Missing and leakage partitions are disjoint and sum to previous alpha audits exactly.

| Native variant | Missing total | Top | Bottom | Left | Right | Interior | Leakage total | Leak left/right |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| V2 E contour-first baseline | 4717 | 0 | 2457 | 517 | 1738 | 5 | 54 | 44 / 10 |
| V2 G trim3 | 6655 | 25 | 2457 | 1441 | 2674 | 58 | 0 | 0 / 0 |
| V3 H mixed trim0 | 4394 | 0 | 2457 | 362 | 1572 | 3 | 74 | 61 / 13 |
| V3 H mixed trim2 | 4924 | 9 | 2457 | 604 | 1832 | 22 | 30 | 26 / 4 |

Three fully missing bottom backing rows y570–572 each contain 819 frozen-target pixels. At alpha≥1 the V2 baseline E has 4311 missing: 2457 bottom, 325 left, 1526 right, 3 interior; leak88 left72/right16. Source PNG and prior alpha-report SHA confirmed; connected-component bounding boxes and full nonzero per-row residuals are in versioned JSON. These are **not** screen RGB quality results or real exact CHALK; no brush correction has been performed. Quality remains FAIL, candidate live E4 NOT_RUN.


## FILL-001 native brush footprint A — empirical Egret evidence (2026-11-09)

Source commit `8dae4b910db690dbc3a6231865e4d24ffa07238c`, [CI run 42571729011](https://github.com/Kiddos19882/AutoDraw/actions/runs/42571729011), [source 10 native PNG + manifest, SHA/provenance, independent analysis report](https://github.com/Kiddos19882/AutoDraw/actions/runs/42571729011/artifacts/13653019564). Actual Egret 5.4.1 BoardPane/WebGLRenderer, Firefox ANGLE (Microsoft Basic Render Driver), local canvas backing 1380×720 (3× 460×240); offline synthetic normal horizontal/vertical/diagonal/corner and smooth horizontal, width5/10. Four frozen diagnostic alpha thresholds: 1/64/128/254, **not game screen RGB threshold8**.

| Case | bbox alpha≥128 (Xmin,Ymin,Xmax,Ymax backing px) | Midpoint thickness alpha≥128 | Start/end axial extension backing px |
|---|---|---:|---|
| normal horizontal w5 | (383,352,996,367) | 16 | 7 / 6 |
| normal vertical w5 | (682,113,697,606) | 16 | 7 / 6 |
| normal horizontal w10 | (375,345,1004,374) | 30 | 15 / 14 |
| normal vertical w10 | (675,105,704,614) | 30 | 15 / 14 |
| smooth horizontal w5 | (383,352,696,367) | 14 at sample X=230 | 7 / −294 |
| smooth horizontal w10 | (375,345,704,374) | 30 at sample X=230 | 15 / −286 |
| normal diagonal w5 | (383,173,996,547) | per-pixel PNG/JSON | see report |
| normal diagonal w10 | (375,165,1004,554) | per-pixel PNG/JSON | see report |
| normal corner w5 | (443,202,907,546) | junction 165 painted of 169 (13×13) | see report |
| normal corner w10 | (435,195,914,554) | junction 169 of 169 (13×13) | see report |

`smooth` last X is **300 backing px before** `normal` at both widths on same horizontal input X130→330. The negative end extension is not a physical brush radius; it reports intentional missing second half-segment (`drawLast=false`), so do not interpret it as symmetric end cap. Alpha≥254 for normal width5 cross-section becomes 14 backing px (vs 16 at ≥128). These are empirically measured PNG values, not quality gate results and not cost estimates. SHA integrity verified for every PNG; source data preserved. Actual game live FILL-001 quality gate remains FAIL and candidate exact CHALK NOT_RUN.


## FILL-001 native V2/V3 — negative geometry evidence, 2026-11-09

[CI 42552197466](https://github.com/Kiddos19882/AutoDraw/actions/runs/42552197466) SUCCESS on `be8c07ac`; [native V1/V2/V3 artifact 13645982484](https://github.com/Kiddos19882/AutoDraw/actions/runs/42552197466/artifacts/13645982484). Real BoardPane/Egret WebGL, synthetic normal strokes, frozen rectangle mask, 1380×720 backing, nearest 3× target (401877 pixels); values are **alpha≥1 diagnostic only, not official live RGB screenshot quality**.

| Candidate | Coverage | Missing backing px | Leakage backing px |
|---|---:|---:|---:|
| E width10 contour baseline | 98.927284% | 4311 | 88 |
| V2 G trim1 | 98.417180% | 6361 | 22 |
| V2 G trim2 | 98.397770% | 6439 | 8 |
| V2 G trim3 | 98.390300% | 6469 | 2 |
| V2 G trim4 | 98.381590% | 6504 | 1 |
| V3 H width5 contour/trim0 | 98.989492% | 4061 | 128 |
| V3 H trim1 | 98.832230% | 4693 | 77 |
| V3 H trim2 | 98.828000% | 4710 | 66 |
| V3 H trim3 | 98.825014% | 4722 | 66 |
| V3 H trim4 | 98.822028% | 4734 | 66 |

Alpha≥128 V2 trim3/trim4 leakage=0 but coverage 98.34402% / 98.33506%; V3 H0 coverage 98.906631% with 74 leakage, H4 98.768031% with 29 leakage. All variants FAIL unchanged 99%/zero rule even as native-local diagnostic. OpenCV static thin-contour proxy ~99.955%/0 contradicted by actual native renderer. V3 alpha does not prove live screenshot E5 or exact CHALK. Prior [CI 42551948930](https://github.com/Kiddos19882/AutoDraw/actions/runs/42551948930) recorded negative CLI reporting failure due to absent V1-only manifest key; `be8c07ac` changed the printer only and rerun passed.


## FILL-001 contour-first — native BoardPane/WebGL 2026-11-09

Evidence: [native CI 42549813024](https://github.com/Kiddos19882/AutoDraw/actions/runs/42549813024), [native PNG + fixture-provenance + manifest + alpha diagnostic](https://github.com/Kiddos19882/AutoDraw/actions/runs/42549813024/artifacts/13644514101), source code sequence `40027908`–`c42e0145`. Frozen rectangle/radius10/rowstep5/contour inset6; `B_sparse_only` 27 strokes / 54 **synthetic vertices**, C/E 28 strokes / 119 synthetic vertices; **synthetic vertex counts are NOT CHALK**. Native WebGL 1380×720, same color+geometry: C/E differingPixels=0; sparse B↔E differingPixels=754.

| Case | Native alpha≥1 coverage | Missing backing px | Leakage backing px | Native alpha≥128 coverage | Leakage backing px |
|---|---:|---:|---:|---:|---:|
| B sparse | 98.768529% | 4949 | 88 | 98.674968% | 54 |
| C contour last | 98.927284% | 4311 | 88 | 98.826258% | 54 |
| E contour first | 98.927284% | 4311 | 88 | 98.826258% | 54 |

Native target: 401877 backing pixels, frozen logical mask ×3 nearest (no offset, dilation, fitting). Alpha thresholds 1,64,128,254 are **diagnostic sensitivity only**, not game RGB threshold 8. Unlike the earlier OpenCV-only C 99.516%/leak0, this measured native local-BoardPane footprint has different coverage/leakage; neither is interchangeable with the user V3 live screen V2 coverage 99.5522%/18 leaks. Status: native rendered **E3 PASS for isolated simulation**; independent run-bound native↔live E5 **NOT_RUN**; live FILL-001 quality **FAIL**, candidate CHALK **NOT_RUN**. No automatic execution or acceptance override.

## FILL-001 contour-first V1/V2 — frozen OpenCV screening 2026-11-09

**Scope:** E1/E2/E3 offline only, radius10, row step5, contour inset6, 3 original frozen target masks; quality ≥99% coverage / leakage=0 **в логическом OpenCV** (не live). Code/test `c024816222b691c974d47769c7a0d0dbb1c02771`, [workflow 42547807009](https://github.com/Kiddos19882/AutoDraw/actions/runs/42547807009); [V1 JSON + rasters](https://github.com/Kiddos19882/AutoDraw/actions/runs/42547807009/artifacts/13644670082), [V2 JSON + rasters](https://github.com/Kiddos19882/AutoDraw/actions/runs/42547807009/artifacts/13643764696). E and historical C have identical mask despite reverse stroke order.

| Form | B sparse | E contour-first same geometry | V1 deep inset 7–9 | V2 X trim 1 | V2 X trim 4 |
|---|---:|---:|---:|---:|---:|
| rectangle | 99.319195% | 99.516270% | 98.091954% FAIL | 99.332632% PASS | 99.278884% PASS |
| wide_irregular | 99.395469% | 99.592551% | 98.009256% FAIL | 99.200602% PASS | 99.096526% PASS |
| narrow_irregular | 99.173333% | 99.380557% | 98.025803% FAIL | 98.792308% FAIL | 98.698723% FAIL |

All comparison rows have **0 logical leakage pixels** in pinned OpenCV model, not demonstrated screen-image zero-leakage. All V2 trims 1,2,3,4 follow same PASS for rectangle/wide and FAIL for narrow; all V1 insets 7,8,9 FAIL. V2 rows preserve original scanline Y and stroke count; V1 deeper inset removed some full rows. At rectangle, B estimated sampling proxy 2099 vs contour-first E 2352 (plus 253, ~12.05%) — **proxy NOT CHALK**; E has 28 strokes vs 27 B. V2 trims modestly reduce proxy but are shape dependent. No real pointCount captured; new E4 and native Egret E5 remain NOT_RUN. Preserve both negative and positive results; frozen thresholds unchanged.


## FILL-001 V3 Smooth OFF — live E4 2026-11-09

**Пространственный офлайн-аудит V3 OFF:** `FILL001_V3_OFF_SPATIAL_RESIDUAL_V1`, code `3eb92e79dbc843c2ff6570965e7524c47fd54548`, [CI 42545897296](https://github.com/Kiddos19882/AutoDraw/actions/runs/42545897296) SUCCESS (47 tests + 6 subtests); [artifact 13643392258](https://github.com/Kiddos19882/AutoDraw/actions/runs/42545897296/artifacts/13643392258) — report.json + V3 overlay. Исходные immutable captures/quality не менялись. Replay подтвердил `coverage=99.552195%`, `leakage=18`, `missing=427`, regions `above=0, below=0, left=10, right=8, other=0`; максимальная ошибка ROI→Egret accepted-point roundtrip **2.000 logical px**. Статус E2/E3 diagnostic PASS, FILL quality FAIL, native renderer E5 NOT_RUN. Не считать 2px ошибкой screen mapping без независимой причинной проверки; отчёт содержит пространственные распределения пропусков и координаты leak.

**Уточнение по первичному artifact 13643392258 (read-only извлечение report.json и overlay):** все 27 `accepted_centerlines` дают `median_y_offset=0.0`; наблюдаемые endpoints по X на +0.20833397 logical px от плана. `legacy_ROI_to_same_run_BoardPane_with_Egret_stage_rounding` моделирует X error −1 и Y error −2..0, а `BoardPane_screen_corners_to_ROI_local_then_Egret_round` даёт предусмотренную планом Y без коррекции. Следовательно напечатанное в CI `maximum input roundtrip error=2.000` не является наблюдаемой ошибкой исполнителя. Из 427 missing V2 193 относятся к самой боковой границе маски, 46 к расстоянию 1 px, 32 к 2 px; точный raster-cause остаётся UNKNOWN. 18 leakage: 10 left / 8 right, max depth 2 screen px, в том числе у верхних/нижних скруглённых краёв. Никакой post-hoc fit и нового live рисования не применялось.


Baseline [4efa33c655c1e35a36114df316da77cf54f31300](https://github.com/Kiddos19882/AutoDraw/commit/4efa33c655c1e35a36114df316da77cf54f31300), task `fill001-20261109-040615-rectangle-r10-s5-o0-v3-smooth-off`, run `3b4243e9-509d-4d5b-9698-04bd657a8888`, session `a3cf20c9-9e1b-4a76-a120-2dcfa2bccad9`. E4 raw status `PASS_E4_RAW_CAPTURE`; executor completed 27/27; observed Smooth OFF 27/27, radius 10, P1 sampling step 4/delay 5, row step 5; before pointCount=1, after=1462, exact CHALK=1461; 1461 accepted/positive samples, 2809 mouse samples, 1492 frames, bridge failures=0, sequence gaps=0. Пустая доска обычно начинает с pointCount=1 по подтверждению оператора; точный CHALK — только delta.

| Метрика | V1 original audit | V2 run-bound diagnostic |
|---|---:|---:|
| Coverage | 98.3317018% | 99.55219498% |
| Leakage pixels | 521 | 18 |
| Uncovered target pixels | 1602 | 427 |
| Gate | FAIL | FAIL |

V1/V2 используют разные screen-mask projections; это не два улучшения игры. V2 binding SHA raw run `76fd6855fcec56b0e03d1481175ee232e85f90000fce3ae27ece57ffd1f80bbb` (identity), same-run BoardPane mapping SHA `89388fd6640169d41cff6df7f91a8c2d1443b6a6e87abaa05a18a28c3a44d582`, DOM client→screen offset (0,163) px; `acceptance_override=false`. PNG quality FAIL, точная причина 18 leaks/427 misses пока UNKNOWN (требуется offline spatial audit). Native Egret E5 для этого FILL-001 run NOT_RUN. [CI 42544453230](https://github.com/Kiddos19882/AutoDraw/actions/runs/42544453230) SUCCESS на capture commit; не означает PNG PASS.


**Актуальная evidence сверка:** 2026-11-08 · **ENGINE-001 live baseline HEAD:** `177165361b0340515fe3bb74f4847ab3ec579ebc` (предыдущие исторические результаты по исходному `a2d1f0a52d47` сохранены ниже). Это **навигационный реестр**, а не замена первичных experiment manifests, Game Monitor reports, PNG или CI artifacts. Все прежние детальные записи реестра сохранены в [TEST_RESULTS_HISTORY_THROUGH_2026-11-08.md](TEST_RESULTS_HISTORY_THROUGH_2026-11-08.md).

> **Обязательная формула:** exact `CHALK = pointCount_after - pointCount_before`, только при валидной привязке к конкретному запуску. Длина, количество strokes, площадь, pixel coverage, move calls и estimates — отдельные величины.

## FILL-001: история и будущий чистый A/B

Исторические данные не меняются: FILL001-RS 27 strokes, CHALK1260, coverage98.430600%, leakage11, PNG FAIL; отдельные runs 2026-11-08 ON: CHALK1455, coverage98.6764%, leakage840; OFF: CHALK1459, coverage99.3137%, leakage849 (ROI 674×355 для обоих), оба PNG FAIL. Monitor наблюдал 27/27 заданных режимов; отдельный сохранённый V1 audit есть для ON, отсутствует для OFF. [Первичные файлы](https://github.com/Kiddos19882/AutoDraw/commit/d7da3a1ba5680a8659864b564ad342b25c0baa8b).

Новый FILL001_SMOOTH_AB_V1: software/regression CI NOT_RUN, live E4 ON/OFF NOT_RUN, парная validation NOT_RUN. Старые данные не засчитываются в новый протокол. [Схема проверки](GAME_MONITOR_BRIDGE_REFERENCE.md#12-fill-001--чистый-парный-smooth-ab-v1).

## 1. Реальные измерения CHALK

| Исследование | Принятые live captures / метрика | Результат и ограничения | Первоисточник |
|---|---|---|---|
| G1 (длина / направление) | 12/12 | Точные pre/post CHALK, короткие и длинные линии; только тестовые условия | [G1](CHALK_GEOMETRY_MATRIX_G1_RESULTS.md) |
| G2 (повороты / контуры / перекрытия) | 18/18 | Влияние геометрии, не универсальный fill predictor | [G2](CHALK_GEOMETRY_MATRIX_G2_RESULTS.md) |
| G3 (sampling step/delay) | 27/27 | Шаг меняет расход CHALK, задержка тоже может влиять; параметры изучены на фиксированной геометрии | [G3](CHALK_G3_RESULTS_2026-11-02.md) |
| Матрица радиусов | 21/21 | Шесть длинных линий: CHALK 722–728 при radius 1–30; нет установленного прямого radius multiplier | [Radius matrix](CHALK_RADIUS_MATRIX_RESULTS.md) |
| Исходные V1–V5 | 45/45 | Точные live captures; исходная матрица сохраняется независимо от исправленной | [V1–V5](CHALK_INT006_V1_V5_RESULTS_2026-11-02.md) |
| Исправленные V1–V5 | +45/45 | Step=2→4: снижение CHALK **38.5–49.4%** по пяти геометриям; visual/pixel checks отдельно | [Follow-up](CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md), [pixel audit](CHALK_INT006_PIXEL_AUDIT_2026-11-02.md) |
| INT-006 D1–D5 | 45/45 (пять планов × 3 профиля × 3 повтора) | Official analyzer **PASS**; MAE 1.408, MAPE 2.134%; P1 MAE 0.657 CHALK. P1 vs P0: расход 1010 vs 1884 CHALK в матрице. **Safety margin/production не утверждены** | [Официальный отчёт](CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md), [frozen model](CHALK_INT006_FROZEN_PREDICTIONS_AND_ANALYZER_2026-11-02.md) |
| INT006R | 45/45 D1–D5 × radius 1/10/30 × 3 | Суммарно CHALK **1011 / 1015 / 1017**. Важнее визуальные ограничения radius1/D2 и radius30/D4 | [Live report](CHALK_INT006R_LIVE_RESULTS_2026-11-03.md), [visual review](CHALK_INT006R_VISUAL_AUDIT_2026-11-03.md) |
| FILL-001 preflight до quota | 131 strokes completed; точный session-level quota 5999 | Это **не принятый FILL-001 quality/capture**, budget исчерпан; исторический негативный опыт | [Postmortem](CHALK_FILL001_PREFLIGHT_POSTMORTEM_2026-11-04.md) |
| FILL-001 `FILL001_RIGHT_EDGE_SPATIAL_V1` (actual saved screen RGB, E2/E3 diagnostic) | [CI 42456241289](https://github.com/Kiddos19882/AutoDraw/actions/runs/42456241289), Preparation/G3 **977 passed**, 82 subtests passed; code `c4fefe6` | 114/114 middle rows contiguous right gap 3–7 px (median 4); 499 right/134 left; 11 old leakage; 27 accepted strokes with last accepted X 4.208–5.208 logical px beyond planned end. **No causal root cause or new live validation**; original coverage 98.430600%/leakage11 **FAIL** | [Raw-derived report and overlays](https://github.com/Kiddos19882/AutoDraw/actions/runs/42456241289/artifacts/13607454421); [FILL-001 raw capture](CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md) |
| FILL-001-RS сохранённый live run | 27/27; exact CHALK **1260** | Runtime binding PASS, **PNG gate FAIL:** coverage 98.430600% при target ≥99%, leakage 11 px при 0 | [Replay и raw evidence](CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md) |
| ENGINE-001 one-click live, 2026-11-08 | **9/9** one-stroke isolated, 3 направления ×3 повтора, 9 уникальных run IDs | Exact CHALK горизонталь 108/108/108=**324**, вертикаль 60/60/61=**181**, диагональ 113/114/114=**341**, всего **846**; 861 native Egret `ENTER_FRAME`, 9/9 `PASS_E4_RAW_CAPTURE`; это сумма run-level delta, не один бюджет, **не** E5 pixel quality | [Evidence commit 1771653](https://github.com/Kiddos19882/AutoDraw/commit/177165361b0340515fe3bb74f4847ab3ec579ebc), [run journal](../data/results/brush_behavior_tests/chalk_test_blocks/chalk-block-ENGINE001-chalk-20261108-080330-af2835-9fdb9bd9.json), [§21](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md) |

**Интерпретация:** multiple runs/repeats не равны независимым DrawingPlan. Нельзя объявлять `95%` predictive coverage INT-006 по 45 captures, построенным из 5 геометрий.

## 2. Renderer / качество / автоматические проверки

| Направление | Подтверждено | Чего не доказывает | Источник |
|---|---|---|---|
| Paired renderer PRR | 6/6 `PASS_PER_RUN`, aggregate PASS в [CI 42321009715](https://github.com/Kiddos19882/AutoDraw/actions/runs/42321009715) | Pixel parity всех рисунков/конфигураций | [Game engine analysis](CHALK_GAME_ENGINE_POINT_COST_AND_BRUSH_WIDTH_2026-11-03.md) |
| ENGINE-001 accepted-only temporal Egret replay | [Browser job CI 42434968046](https://github.com/Kiddos19882/AutoDraw/actions/runs/42434968046) SUCCESS на `8d5d088`; 27 historical strokes/1260 accepted points; one-pass vs incremental: Canvas2D и WebGL final RGBA **0 отличий**, 29 vs 70 paths; [artifact 13599086458](https://github.com/Kiddos19882/AutoDraw/actions/runs/42434968046/artifacts/13599086458), независимая RGBA/PIL проверка | Не E4 complete `ENTER_FRAME` trace, не same-run screen calibration, не FILL-001 quality acceptance; old CHALK unchanged | [ENGINE-001 технический отчёт](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md), [harness](../tests/game_renderer_reference.js) |
| ENGINE-001 one-click laboratory: corrected Bridge and completed live 9/9 | `7b129c2` separates genuine heartbeat timestamp from latest arbitrary event, fixing `lab_bridge_gate`; [CI 42448779447](https://github.com/Kiddos19882/AutoDraw/actions/runs/42448779447) SUCCESS. `1771653`: 9/9 E4 run-bound `PASS_E4_RAW_CAPTURE`, 9 unique run IDs in one session, no monitor losses, [full CI 42449898657](https://github.com/Kiddos19882/AutoDraw/actions/runs/42449898657) SUCCESS. Earlier [CI 42443300762](https://github.com/Kiddos19882/AutoDraw/actions/runs/42443300762) was FAILURE; two older stopped journals `9bf7c83` remain separate. | Observed Egret `ENTER_FRAME` is not complete rendered timeline; CSS client→desktop mapping/PNG quality need independent E5. All modes observed `stroke_option_raw=true`; no `normal` live control. | [Lab §20–21](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md), [code](../source/preparation/engine001_lab.py), [raw evidence](https://github.com/Kiddos19882/AutoDraw/commit/177165361b0340515fe3bb74f4847ab3ec579ebc) |
| ENGINE-001 preliminary E5 same-run geometry cross-check | 1641 `MOUSE_MOVE_SAMPLE` из 9 raw run reports: client→screen=(0,163) px во всех 9; independent ℓ² fits 6 X/6 Y дают max abs residual **0.749 screen px**; BoardPane client corners + offset согласованы с ROI | **E5 PARTIAL**, только геометрическая диагностика по существующим raw; независимая **screen-only** PNG RGB проверка повторила 9/9 исходных raw diff counts и выделила 17 изменённых нижних пикселей на каждом ROI; тёмные stroke bounds по трём направлениям получены при `max(after RGB)<128`. **Native Egret alpha/pixel parity NOT_RUN**; RGB screen mask/endpoint observation — диагностика без acceptance threshold, raw bbox не является native footprint. | [§21 и методика](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md) |
| ENGINE-001 native Stage A-D vs 9 saved E4 live PNG, `ENGINE001_E5_NATIVE_SCREEN_V1` | [E5 CI 42454224181](https://github.com/Kiddos19882/AutoDraw/actions/runs/42454224181) SUCCESS на `6810f75dfb87c8eaac7e73eb9d1063291660c104`; actual `BoardPane` WebGL A-D, 9 individual runs, 9/9 `PASS_PER_RUN`, rejected=0, blocked=0, Node 18 PASS, Python acceptance 24 PASS | Frozen DEC-025: IoU H **0.998995–0.999281**, V **0.940241–0.940694**, D **0.981740–0.983277**; RGB24/same-run screen bounds. Первый [CI 42453831682](https://github.com/Kiddos19882/AutoDraw/actions/runs/42453831682) сохранил 9 инструментальных REJECTED (bbox отсутствовали в диагностических метриках), исправлено без изменения gate в `6810f75`. Экранный RGB gate PASS, но прямой live alpha/temporal order NOT_RUN, общий ENGINE-001 PARTIAL | [Native A–D PNG](https://github.com/Kiddos19882/AutoDraw/actions/runs/42454224181/artifacts/13606972733), [raw masks/provenance/per-run JSON](https://github.com/Kiddos19882/AutoDraw/actions/runs/42454224181/artifacts/13607535199), [§22](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md) |
| ENGINE-001 stationary duplicate-ENTER_FRAME native Egret | [Full CI 42440876068](https://github.com/Kiddos19882/AutoDraw/actions/runs/42440876068) SUCCESS, `a35d782`; 0/27/81 extra frames across 27 archived strokes, 70/71/73 surviving paths, 1260 accepted unchanged, **0 final within-backend RGBA differences**, independent PNG threshold 1/64/128/254 zero; [native PNG+manifest](https://github.com/Kiddos19882/AutoDraw/actions/runs/42440876068/artifacts/13600769368), [independent audit](https://github.com/Kiddos19882/AutoDraw/actions/runs/42440876068/artifacts/13602035420) | Canvas2D vs WebGL baseline 243 differing RGBA px; no actual frame cadence/intermediate rendering/same-run screen mapping; old FILL PNG FAIL, new CHALK NOT_RUN | [ENGINE-001 §19](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md), [harness](../tests/game_renderer_reference.js) |
| ENGINE-001 native 5px closed contour on all 3 endpoint modes | [CI 42439343897](https://github.com/Kiddos19882/AutoDraw/actions/runs/42439343897) SUCCESS on `f381ffe`; native Egret 30 PNG ([artifact 13600612786](https://github.com/Kiddos19882/AutoDraw/actions/runs/42439343897/artifacts/13600612786)); independent 4-alpha OpenCV mask audit and overlays ([artifact 13601121751](https://github.com/Kiddos19882/AutoDraw/actions/runs/42439343897/artifacts/13601121751)): board-local coverage 99.6240% smooth / 99.6743% forced-normal at alpha128 | 31 new modeled leakage px per variant, right-middle game-smooth 55→55 (0 recovered), OpenCV added-mask IoU 0.9658/0.9762; **screenTransform UNCALIBRATED**, no new CHALK and actual FILL-001 PNG FAIL | [Native §18](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md), [analyzer](../tests/analyze_engine001_outline5_reference.py) |
| ENGINE-001 native Egret endpoint vs OpenCV | [CI 42438036187](https://github.com/Kiddos19882/AutoDraw/actions/runs/42438036187) SUCCESS на `1805ebf`; 15 PNG native Egret; full 27-stroke +2936 backing px / 0 removed при alpha≥128, selected +4/+9/+13 backing px; [native PNG](https://github.com/Kiddos19882/AutoDraw/actions/runs/42438036187/artifacts/13599599617), [independent analysis](https://github.com/Kiddos19882/AutoDraw/actions/runs/42438036187/artifacts/13600208683) | OpenCV cap ~0.9664–0.9669 IoU с native; historical screen mapping UNCALIBRATED, live FILL PNG FAIL, CHALK для новых вариантов NOT_RUN | [ENGINE-001 §17](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md) |
| FILL-001-RS static sweep | 2238 offline candidates, 62 passed simulation gate | Реальный CHALK или quality gate в игре | [Static sweep](CHALK_FILL001_RS_STATIC_SWEEP_2026-11-04.md) |
| FILL-001 A–D frozen-mask offline screening | [CI 42424959123](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123) SUCCESS на `6d790cd`, 3 маски × 4 стратегии, 15 PNG + JSON ([artifact 13595421597](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123/artifacts/13595421597)); C: 99.516% / 99.593% / 99.381%, modeled leakage=0; 12/12 PNG↔JSON independently checked | Не проверяет actual game screenshot, не измеряет CHALK; D oracle-based; Windows build SKIPPED | [Analyzer](../source/preparation/chalk_fill_strategy_comparison.py), [tests](../source/preparation/tests/test_chalk_fill_strategy_comparison.py) |
| FILL-001-RS saved-ROI counterfactual | [CI 42427514794](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794) SUCCESS на `16f0e1b`; target=71110, actual uncovered=1116, leakage=11; B-model uncovered=416, model-only=738, actual-only=38. Modeled contour offsets 5/6/7/8 recover 1092/734/335/157; offset6 leaves 382 and adds 0 modeled leakage; 6 PNG + JSON [artifact 13596093007](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794/artifacts/13596093007) | Hypothetical union, **not** game-drawn contour or fresh CHALK. Existing 11 leakage persists; ±1 screen px dilation for offset6 adds 89 modeled leaks. Original PNG FAIL. | [Analyzer](../source/preparation/chalk_fill_screen_residual_comparison.py), [regression tests](../source/preparation/tests/test_chalk_fill_screen_residual_comparison.py) |
| FILL-001 new Monitor 0.2.4 same-run diagnostic preparation | [Software CI 42458832846](https://github.com/Kiddos19882/AutoDraw/actions/runs/42458832846) **SUCCESS** на `b98d9e0` (995 Preparation/G3 PASS, 82 subtests, все обязательные jobs), опциональный FILL-001-RS 27-stroke harness и immutable full-screen/ROI pairing; предыдущий [CI 42458319429](https://github.com/Kiddos19882/AutoDraw/actions/runs/42458319429) SUCCESS | **Software gate only.** Новый реальный E4 capture **NOT_RUN**, new CHALK **NOT_MEASURED**, previous captured 1260 unchanged; later independent old↔new comparison E5 **NOT_RUN**, full-screen may contain private data. | [Monitor §11](GAME_MONITOR_BRIDGE_REFERENCE.md), [audit source](../source/preparation/fill001_monitor_diagnostic.py) |
| FILL-001 committed PNG replay | 27/27, actual 98.430600% coverage, 11 leakage pixels | **Не PASS**, несмотря на успешные тесты replay | [Replay](CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md) |
| Monitor per-run integrity | Exact telemetry, binding и per-stroke deltas в принятых сериях | Автоматическое доказательство произвольного последующего live | [Bridge API](GAME_MONITOR_BRIDGE_REFERENCE.md), [overflow diagnosis](GAME_MONITOR_BUFFER_OVERFLOW_ANALYSIS_2026-11-02.md) |

## 3. Кандидатный корпус 81 реального изображения (OFFLINE ONLY)

| Проверка | Подтверждено |
|---|---|
| Источники | 31+50, **81 уникальных SHA-256**, отсутствие exact cross-batch duplicates |
| Планы | 81 monochrome и 81 color plan, source/geometry exact duplicates: 0 |
| Mono | 168237 total strokes, median N=1897, все горизонтальные scanlines |
| Color | 942206 total source strokes, median N=10727 |
| Singletons / color transitions | **395455 / 916312** по всем 81 color plans |
| Автоматическое совпадение pHash AND dHash | 0 strict flagged pairs, 20 closest pairs требуют ручного просмотра |
| Состояние статистики | `family_label=unclassified`, independence и predictor-domain **NOT ASSESSED** |

**Источники:** [screening CI 42417067363](https://github.com/Kiddos19882/AutoDraw/actions/runs/42417067363) и [artifact 13591858161](https://github.com/Kiddos19882/AutoDraw/actions/runs/42417067363/artifacts/13591858161), [geometry audit](VALIDATION_CORPUS_GENERATOR_2026-11-07.md). Конфигурация: canvas 646×323, contain, row step 1. Отсутствие source/geometry duplicates и strict perceptual flags не доказывает семантическую независимость.

Эти числа — **не измеренный CHALK**. Color scanline Stage6 и mono Stage8 — разные execution paths; INT-006 frozen predictor валидирован для D1–D5 line-based, не автоматически для fills. [95% split protocol](CHALK_95_PERCENT_CALIBRATION_HOLDOUT_PROTOCOL_2026-11-07.md) остаётся proposed, 19/59 не выполнялся.

## 4. CI и уровни подтверждения

- **Full validation CI [42434968046](https://github.com/Kiddos19882/AutoDraw/actions/runs/42434968046) — SUCCESS** на code/test SHA `8d5d0880c2027bf5c699608578d338025d64c595`: preparation 952 passed / 24 warnings / 82 subtests; Egret browser reference, Game Monitor/Bridge, executor, app integration и INT-006 PNG audit — SUCCESS; optional algorithm benchmarks и Windows portable build — SKIPPED. Это E3, не E4 gameplay.

- [CI 42427514794](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794): **SUCCESS** на `16f0e1b6cce0`. Preparation: **952 passed**, 82 subtests; Monitor/Bridge, executor, app integration, Egret and INT-006 PNG audit jobs SUCCESS; optional benchmarks/Windows portable build SKIPPED. [artifact 13596093007](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794/artifacts/13596093007) (ZIP SHA-256 `19313debbcc350f0eeda3edf2cba9e65350690a850d5bb2d9d733bb03794d620`); actual/counterfactual colored PNGs independently counted against JSON.
- [CI 42427122693](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427122693) на `c2ae5a0`: **FAIL** (943 passed / 8 failed) — строгая проверка Git-LF SHA ошибочно отклоняла неизменённый JSON в Windows-CRLF checkout; исправлено нормализацией **только JSON**, добавлен regression test. Отрицательный результат сохранён.

- [CI 42424959123](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123): **SUCCESS** on `6d790cd72326`. Preparation/G3, Monitor/Bridge, executor, app integration, Egret reference, INT-006 pixel-audit jobs passed. Optional benchmarks and Windows portable build **SKIPPED**. Artifact: [artifact 13595421597](https://github.com/Kiddos19882/AutoDraw/actions/runs/42424959123/artifacts/13595421597). Это E3 offline, а не новый E4 runtime.

- [Full AutoDraw validation 42417067391](https://github.com/Kiddos19882/AutoDraw/actions/runs/42417067391): **SUCCESS** на `5a55e9f`; Windows portable job мог быть SKIPPED — читать jobs конкретного run.
- [Offline screening 42417067363](https://github.com/Kiddos19882/AutoDraw/actions/runs/42417067363): **SUCCESS**, 5 regression tests на `5a55e9f`.
- [Full validation 42416307257](https://github.com/Kiddos19882/AutoDraw/actions/runs/42416307257): **SUCCESS** на `3fdffec`.
- [Corpus ingestion 42415293374](https://github.com/Kiddos19882/AutoDraw/actions/runs/42415293374): **SUCCESS** на `985e194`.

**Граница:** E3 CI ≠ E4 live game; E4 live ≠ статистическая гарантия для неподдерживаемого domain. [Правила доказательств](EVIDENCE_AND_VALIDATION.md) · [исторические тесты](TEST_RESULTS_HISTORY_THROUGH_2026-11-08.md).

## Совместимость ссылок на исторический PRR batch

<a id="2026-11-07--локальный-prr-batch-и-exact-chalk-evidence"></a>
Полный набор локальных PRR run ID, exact CHALK и ссылок на исходные captures находится в [TEST_RESULTS_HISTORY_THROUGH_2026-11-08.md](TEST_RESULTS_HISTORY_THROUGH_2026-11-08.md#2026-11-07--локальный-prr-batch-и-exact-chalk-evidence). Формальная позднейшая renderer acceptance — [CI 42321009715](https://github.com/Kiddos19882/AutoDraw/actions/runs/42321009715) (6/6 PASS_PER_RUN).

## FILL-001 Screen Mask V2 — проверка свидетельств

**Источник:** frozen ON/OFF PNG, E4 diagnostic и raw Monitor run из commit [16640ea](https://github.com/Kiddos19882/AutoDraw/commit/16640eaf7f1ad2282d63b05b06394a32f13f14ed). **Новый code SHA:** `647aeb7a74ec979f46a0828aa3418e57635533c1`; [validation workflow 42503756622](https://github.com/Kiddos19882/AutoDraw/actions/runs/42503756622), результат фиксировать после окончания. Добавлен source-run-bound validation и CLI для пересчёта двух сохранённых ROI; результат сохраняется в `autodraw-fill001-screen-mask-v2/report.json` (artifact только JSON), если все provenance checks выполнены. Прежние утечки 840/849, coverage 98.7847%/99.3148%, PNG FAIL/FAIL — исходный V1 baseline, не новая V2 метрика. Native Egret trace и независимое pixel-equivalence V2 — NOT_RUN.

## FILL-001 Screen Mask V2 — saved Smooth A/B replay PASS как диагностика, качество FAIL

| Run mode | Legacy V1 leakage | V2 leakage | Legacy V1 coverage | V2 coverage | V2 diagnostic |
|---|---:|---:|---:|---:|---|
| Smooth ON | 840 | 1493 | 98.784704% | 98.796065% | FAIL |
| Smooth OFF | 849 | 1474 | 99.314769% | 99.359230% | FAIL |

**Provenance:** исходный commit `16640ea`, новые code/tests SHA `480cb3e87616846d9fa76276d853cda89ef640e6`, [CI 42504588736](https://github.com/Kiddos19882/AutoDraw/actions/runs/42504588736) **SUCCESS**, `14 passed + 6 subtests`, [artifact 13627275540](https://github.com/Kiddos19882/AutoDraw/actions/runs/42504588736/artifacts/13627275540). Исходные PNG/Monitor SHA сверены; проверен восстановленный CRLF оригинальных Windows JSON в Linux checkout, raw run/E4 ID, стабильный DOM screen-minus-client offset. Диагностический V2 не меняет V1 quality gate и не заменяет independent native Egret WebGL ↔ live E5. Отрицательные focused CI: 42504084158, 42504159743, 42504396198, 42504487090; причины и исправления в [WORK_LOG](WORK_LOG.md).

## FILL-001 Smooth A/B V2 — новый эксперимент, код подготовлен; игровой E4 NOT_RUN

Протокол `FILL001_SMOOTH_AB_V2`; Screen Mask `FILL001_SCREEN_MASK_V2`; frozen логический план rectangle/r10/step5/offset0, 27 штрихов и P1. Новые ON/OFF task IDs и новая matrix signature изолированы от `FILL001_SMOOTH_AB_V1`. Для каждого свежего run pipeline сохраняет raw E4, SHA исходного Monitor, before/after PNG, исходный V1 контроль и V2 audit с same-run client→desktop mapping. Stage6/executor defaults и frozen acceptance не менялись. Проверка code/unit: [AutoDraw validation 42505872844](https://github.com/Kiddos19882/AutoDraw/actions/runs/42505872844) на code SHA `d557db23ac5911911acc722c58aa140658040cd7`, **SUCCESS** по всем обязательным jobs для code SHA `d557db23ac5911911acc722c58aa140658040cd7` (Preparation/G3, monitor/bridge, executor, integration, Egret browser, INT-006). Optional benchmarks/Windows portable build SKIPPED. Новые реальные CHALK/coverage/leakage — **NOT_RUN**. Preexisting V2 offline replay для старых capture не является новым E4.


## FILL-001 Smooth A/B V2 — фактический E4 и отдельная пространственная диагностика

**Исходная серия:** `fill001-20261108-204825`, исходный [evidence commit 07f4f3e](https://github.com/Kiddos19882/AutoDraw/commit/07f4f3ea14eb14598fa7ce08c3985e56acb0f73b), два новых Monitor 0.2.4 run с одинаковым `plan_signature=a0e42216...`, frozen rectangle 460×240, 27 штрихов и `screen_roi=(496,265,674,355)`. E4 accepted Egret points, observed smooth и exact `CHALK=post.pointCount-pre.pointCount` привязаны к отдельным run и PNG. Оба executor completed; `raw_e4_status=PASS_E4_RAW_CAPTURE`, но quality `FAIL`.

| Новый run | Smooth | Exact CHALK | Screen Mask V2 coverage | V2 leakage |
|---|---|---:|---:|---:|
| `0d0a0edf-f42e-4da1-b880-f09a4fce0a27` | ON | 1458 | 98.666023% | 1488 |
| `0f3f9299-afce-4e02-b7be-7d4fb5714348` | OFF | 1459 | 99.359230% | 1474 |

**Новый исследовательский протокол:** `FILL001_V2_FOOTPRINT_SPATIAL_V1`, код `source/preparation/fill001_v2_footprint_spatial.py`, test `tests/test_fill001_v2_footprint_spatial.py`. На том же immutable V2 mask, RGB `abs(after-before)>8` и SHA-verified PNG, без подгонки mask/threshold, пиксели leakage распределены по непересекающимся регионам. [Focused CI 42511062639](https://github.com/Kiddos19882/AutoDraw/actions/runs/42511062639) **SUCCESS** на code/test SHA `bcfa7dce711f2c5ace955b7ff1b241d15efc6189` (18 passed, 6 subtests); [JSON с 27 accepted rows и цветные карты](https://github.com/Kiddos19882/AutoDraw/actions/runs/42511062639/artifacts/13630025090).

| Новая Screen Mask V2 leak region | ON | OFF |
|---|---:|---:|
| Above | 1206 (max depth 3 screen px) | 1216 (max depth 3) |
| Left | 281 (max depth 7) | 253 (max depth 7) |
| Right | 1 (max depth 1) | 5 (max depth 4) |
| Below | 0 | 0 |

**Новая ключевая E4/E2 находка:** первый плановый centerline `(94,55)→(366,55)` был реально принят Egret как `(93.2083339691,53)→(365.2083339691,53)` **в обоих run**, 48 accepted points на каждом первом штрихе; вертикальное отклонение `-2 logical px`; максимальное абсолютное median Y deviation по 27 рядами также 2 logical px. Следовательно, запланированный margin сверху 5 logical px фактически стал 3, что само по себе достаточно для верхнего выхода номинального кистевого радиуса 5. Это **не** доказывает, что реальный WebGL диаметр неверен: вероятна причина в legacy ROI-based `transform_logical_brush_plan_to_screen()`, который предполагает совпадение ROI borders и run-bound BoardPane corners; отдельная причинная проверка нового transform/runtime round-trip ещё **NOT_RUN**.

**Дополнительная E1/E2/E3 проверка:** legacy ROI→Egret stage rounding использовал фактические same-run BoardPane screen corners и наблюдаемый `Math.round(stage)`. [CI 42511723383](https://github.com/Kiddos19882/AutoDraw/actions/runs/42511723383) SUCCESS: первая и последняя точка первого штриха предсказаны точно; max first/last/Y deviation по 27 строкам 1 logical px. **Неисполняемый** BoardPane-corners→ROI-local counterfactual [CI 42512084578](https://github.com/Kiddos19882/AutoDraw/actions/runs/42512084578) SUCCESS, 20 tests + 6 subtests, [derived report](https://github.com/Kiddos19882/AutoDraw/actions/runs/42512084578/artifacts/13629578784): Y55 у первого ряда и max Y deviation=0 по всем 27 rows в обоих режимах, X первой точки 94.2083339691 против прежних 93.2083339691. Это **не** новый live или correction acceptance; требуется validated preflight geometry и новый E4.

**Ограничения:** spatial split — screen RGB, не native Egret pixel-exact brush raster и не один изолированный stroke. ENGINE-001 E5 ранее подтверждал ~15 screen px transverse width при game UI lineWidth 10. Ни V1/V2 historical gate, ни production CHALK estimator, ни executor defaults не изменены. Полный CI для SHA `bcfa7dce` проверять по завершению [42511062648](https://github.com/Kiddos19882/AutoDraw/actions/runs/42511062648).

## FILL-001 V3 BoardPane-only preflight — software results (не игровой E4)

**Protocol:** `FILL001_SMOOTH_AB_V3` + `FILL001_BOARDPANE_PREFLIGHT_V1` на прежнем frozen rectangle/27 strokes. Новый Bridge no-click event получает actual DOM `clientX/Y` и `screenX/Y` с buttons=0, сервер привязывает к session/geometry SHA и сохраняет last16; отдельный validator строит screen-local executor plan из валидных текущих BoardPane corners, а не расширяет mask и не подгоняет GPU footprint. Предыдущая E2/E3 counterfactual [42512084578](https://github.com/Kiddos19882/AutoDraw/actions/runs/42512084578) вернула первый Y55 vs старые accepted Y53, но это всё ещё **offline only**.

Новый V3 scoped software CI [42514396589](https://github.com/Kiddos19882/AutoDraw/actions/runs/42514396589) **SUCCESS** для SHA `9c1f2952ae4aa6f59b245bbffa31ed222cbebaa4`; новый pipeline дополнительно интегрирован в приложение/Bridge после SHA, поэтому нужен full CI на финальном коде. Первичный focused отказ [42512957892](https://github.com/Kiddos19882/AutoDraw/actions/runs/42512957892) = test-only negative fixture expected 'uniformly scaled' вместо valid early SHA rejection, исправлен двумя раздельными негативными тестами, сохраняется как FAIL. **Нет ни одного нового V3 E4**, точный CHALK/coverage/leakage V3 неизвестны, native E5 NOT_RUN. [Шаги E4 §14](GAME_MONITOR_BRIDGE_REFERENCE.md#14-fill-001--отдельный-boardpane-anchored-smooth-ab-v3-исследовательский-пилот).

**V3 focused итог на текущем коде:** [CI 42515255042](https://github.com/Kiddos19882/AutoDraw/actions/runs/42515255042) **SUCCESS** на code/test SHA `ff1b40199328b1c3cad78ae5107d6fc071c60c3c`: **43 pytest PASS + 6 subtests PASS**, raw V1/V2 replay и две spatial PNG не изменены; [derived spatial masks](https://github.com/Kiddos19882/AutoDraw/actions/runs/42515255042/artifacts/13630729115). Новый preflight evidence включает SHA и точные исходные три sample в source-plan (immutable после начала попытки), а Bridge guard блокирует сбор при неуспешном opt-in. Это E2/E3, не игровой E4. Полный CI для того же SHA — [42515255056](https://github.com/Kiddos19882/AutoDraw/actions/runs/42515255056).


## FILL-001 — кнопки Monitor/Bridge в FILL-001, проверка 2026-11-08

**Кодовый SHA:** `20fde3acdf7095015e436f7fe031a596b2ded454`. [AutoDraw validation 42518700522](https://github.com/Kiddos19882/AutoDraw/actions/runs/42518700522) **SUCCESS**: обязательные Preparation/G3 (включая `test_fill001_bridge_controls.py` и новые тесты shared Bridge launcher), Game Monitor/Bridge, integration, executor, Egret browser и INT-006 PNG audit завершились `success`; optional benchmarks и Windows portable build skipped по workflow. [Markdown integrity 42518828350](https://github.com/Kiddos19882/AutoDraw/actions/runs/42518828350) **SUCCESS** на документационном SHA `2a3c134402061926d70309ca3442cf7949490edd` (на момент этого теста).

**E2/E3 границы:** подтверждена корректность новой UI wiring (forced `require_input_telemetry=True` вне зависимости от сценария кистевой лаборатории), копирования актуальных скриптов, запрета использования остановленного/off-mode Bridge snippet, проверки fresh session telemetry и pre-manifest статуса. Это **не** runtime-тест браузерного iframe на пользовательском Windows: новый live FILL-001 V3 E4 и native Egret E5 **NOT_RUN**. Новые цветовые маски, исходные run, CHALK и исполнительские defaults не менялись.

## FILL-001 V3 — 76a58ab first Windows attempt BLOCKED before execution

**Primary E4 evidence:** [user commit 76a58ab](https://github.com/Kiddos19882/AutoDraw/commit/76a58abc7444519841c3d8548ba8bee3979a708f), series `fill001-20261108-232136`, Bridge session `6941c88e-5875-436e-91f1-adea67f44160`, two raw Monitor 0.2.4 calibration runs `717c7f61-ea04-44cb-811f-a9062940853c` and `d21dc550-7075-45d5-aa1e-2c654df5c477`. Both contain **0 completed FILL strokes**, no after PNG, no valid run-bound FILL CHALK/coverage/leakage. Browser telemetry was active, `inputTelemetry` requested+enabled and radius reached 10 from initial 30. Same session; Monitor snapshots `pointCount=1` pre/post for both calibration runs. **V3 live painting NOT_RUN / BLOCKED**, not a quality FAIL or PASS.

**Root cause, independently reproduced E1/E2:** V3 handoff in `chalk_fill_ui._start_after_brush_verified()` and `integrated_app._load_v3_boardpane_preflight_plan()` incorrectly compared SHA256 of **entire renderer_geometry** between `before PNG` and brush confirmation. Comparison of archived raw snapshots identifies only four changes in transient `boardDisplayChain[3/4].width` (at top-level and player level) from 3060 to 2830.0809053156145; native BoardPane stage/client corners, Egret 5.4.1, canvas logical 460×240 and viewport unchanged. No evidence of changed actual board mapping. This triggers false fail-closed even when session and board screen geometry are stable.

**Minimal corrective research change:** V3 now checks a version-specific stable BoardPane projection SHA (renderer mode, browser/window and canvas screen transform, stage/client corners, logical board, Egret) while retaining complete raw renderer SHA in event/provenance evidence. Bridge stamps both per-passive-sample SHA; server and preparation compare the same stable fields. Full SHA remains mandatory for actual starting raw geometry; all intermediate renderer snapshots must retain the identical BoardPane projection; stale session/heartbeat, shifted client corners, changed window and inconsistent desktop offsets still BLOCK. V1/V2 original full-hash gate, CHALK, target masks and executor defaults unchanged. V3 Screen Mask V2 *binding* uses explicit opt-in and cannot weaken original V2 validation. New regression includes the exact two committed run JSON files, plus negative geometry shift tests.

**Software validation:** initial focused workflow failures on intermediate SHA [42520810040](https://github.com/Kiddos19882/AutoDraw/actions/runs/42520810040) and [42520912912](https://github.com/Kiddos19882/AutoDraw/actions/runs/42520912912) were negative-fixture expectations/missing new stable field, kept as FAIL history. Corrected [42521066861](https://github.com/Kiddos19882/AutoDraw/actions/runs/42521066861) **SUCCESS: 45 tests + 6 subtests** for SHA `0703e10a8ccd43aec43b54524bb4ebdbf071ba83`; additional actual-commit fixture and full CI being checked on later SHA. **New corrected Windows E4 NOT_RUN; E5 native pixel parity NOT_RUN.**

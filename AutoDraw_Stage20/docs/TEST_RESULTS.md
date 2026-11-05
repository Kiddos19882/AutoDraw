## 2026-11-06 — Stage-level compositor A–D implementation (CI pending)

**Code/test HEAD:** `8713012673de7734fb0bb91fe58fcce483ed68b3`.  
**Область:** offline renderer harness, Node regression tests, HTML test page and headless Edge runner.  
**Execution status:** implementation committed; Node/browser/CI results on this HEAD are not yet confirmed. Combined GitHub commit status currently returns no checks. No live game run was performed.

- `buildStagePlacement()` validates Stage/backing dimensions, X/Y scale, axis-aligned BoardPane corners and backing bounds; exact origin derives from run-bound Monitor geometry.
- Existing vertical/diagonal Monitor reports are configured as headless browser inputs. Their run IDs are c860234f-995a-4789-9ac2-e05b322fe742 and f69cb0f4-f5d0-4ff9-a3b7-1148c38fa07f.
- Four outputs are defined: A/B use the actual Egret WebGLRenderer and differ by exact/rounded origin; C/D use Canvas2D and differ by exact/rounded origin. Per-variant pixel differences against A are added to the manifest.
- Node tests cover exact origin 1022.375×216, rounded origin 1022×216, and invalid scale/corners/bounds.
- No Stage PNG artifacts, pixel metrics, PASS_PER_RUN or CI PASS are claimed until the headless runner actually completes and its artifacts are inspected.
- Existing live exact CHALK values remain historical evidence only: vertical=71, diagonal=161. This work does not change CHALK logic or acceptance thresholds.

## 2026-11-06 — independent same-run renderer replay and optional Windows portable build

**Commits:** c0f36ac49e4b66cf0fcd27d362154b71a917c367, 7c1a1fb704a0393509b7ff237048006dbbe6caf7, b07c636fa4b4ce28329cfb74f468634a46751ac1.  
**CI:** [42113632374](https://github.com/Kiddos19882/AutoDraw/actions/runs/42113632374), completed FAILURE because the INT-006 vertical/diagonal renderer gates rejected their per-run comparisons.

- Horizontal: PASS_PER_RUN; IoU=0.999329, precision=0.999329, recall=1.000000, symmetric difference=6 px; all formal gates passed.
- Vertical: REJECTED_PER_RUN; IoU=0.938405, precision=0.938980, recall=0.999348, symmetric difference=302 px; capture and transform passed, renderer gates failed.
- Diagonal: REJECTED_PER_RUN; IoU=0.949646, precision=0.962683, recall=0.985939, symmetric difference=554 px; capture and transform passed, renderer gates failed.
- Thresholds unchanged: IoU/precision/recall ≥0.995, symmetric-difference fraction ≤0.0025, bbox edge delta ≤1 px. No post-hoc translation used.
- Preparation/G3, Game Monitor/Bridge, Executor regression, Egret browser reference and Application integration: SUCCESS. Optional algorithm benchmarks and Windows portable build: SKIPPED. Windows build is now opt-in via manual workflow_dispatch input run_windows_portable_build=true.
- Artifacts: paired renderer 13454628828; Egret reference 13453809141. Existing live CHALK: vertical=71, diagonal=161. No new live game run.
- Current hypothesis: direct screen-space Canvas2D overlay does not reproduce Stage-level WebGL texture composition at fractional backing origin x≈1022.375 (phase 0.375 px). Requires a dedicated stage-level WebGL compositor test; not yet proven.

## 2026-11-05 — offline renderer run-bound profile correction

**Commits:** `23ed8cf2cce051eeda87ad8b630604ae96889608`, `d6343adaf2db05f321b48ef0432b897277ff0193`.

- Статический аудит выявил устаревшие runtime metadata в `game_renderer_reference.js`: Stage 1672×600 и backing canvas 5016×1800 из snapshot 2026-11-04.
- Последний paired-run профиль: screen 1920×1080; viewport 1920×877; Stage 1314×600; backing canvas 3942×1800; scale factor 2; canvas scale 3×3; DPR=1; visualViewportScale=1; CSS matrix X/Y=0.487062/0.487778.
- Harness теперь извлекает этот профиль из полного `monitor_report.json` и требует идентичные `renderer_geometry_at_start/end` для exact run. Старый snapshot больше не является fallback.
- Offscreen raster remains BoardPane 460×240 at 3× = 1380×720; live Stage/CSS transform is metadata and is not applied to local raster.
- **Execution status:** offline rerun NOT_RUN; live test NOT_RUN; automated CI NOT_RUN. Это source change, а не подтверждение pixel equivalence.
- Ожидаются новые offline manifest/PNG от пользователя.

# TEST_RESULTS — единый реестр результатов тестирования AutoDraw

**Статус:** действующий сводный реестр результатов и доказательств  
**Дата формирования:** 2026-11-06  
**Рабочая ветка:** `feature/image-geometry-optimization`  
**Удалённый branch HEAD на начало документационной сверки:** `81f6bb77c8a338ae52e0de084dce45e0cacabf1f` (docs-only commit); последний code/test HEAD остаётся `b07c636fa4b4ce28329cfb74f468634a46751ac1`.  
**Master:** `9a3453aeb847b66041bc83d6f4a56ecaf33a993a`, не изменялась.  

**HEAD перед дополнением D1–D5:** `63fdaf3f2a1b12bd90e1a588ca4e968facbe0103`  
**Область:** AutoDraw_Stage20, тесты приложения, лабораторные эксперименты, Game Monitor/Bridge, CHALK, FILL-001, геометрические модели, GitHub Actions и offline benchmarks.  
**Последний evidence commit:** `e6b771ed67201625884c6ce778fa355f1ab9b873` (первые vertical/diagonal live captures и exploratory offline reports).  
**Последний code/test HEAD:** `b07c636fa4b4ce28329cfb74f468634a46751ac1`; CI run [42113632374](https://github.com/Kiddos19882/AutoDraw/actions/runs/42113632374) completed FAILURE on vertical/diagonal renderer acceptance.

## 2026-11-05 — BoardPane crop accepted horizontally; browser compositor mismatch found

**CI:** [42093239480](https://github.com/Kiddos19882/AutoDraw/actions/runs/42093239480).

- Horizontal: no formal PASS_PER_RUN in CI 42093239480. The values IoU 0.999218, precision 0.999553, recall 0.999665, symmetric difference 7 pixels and matching bbox `[19,167,599,15]` were calculated offline from an existing horizontal artifact after exact BoardPane crop; this is diagnostic evidence only.
- Vertical: `REJECTED_PER_RUN`; IoU 0.938863, precision 0.940204, recall 0.998483, 300 symmetric-difference pixels. Observed/expected bbox `[325,19,16,310]` / `[326,18,15,311]`.
- Diagonal: `REJECTED_PER_RUN`; IoU 0.953976, precision 0.975951, recall 0.976942, 511 symmetric-difference pixels. Observed/expected bbox `[19,19,628,310]` / `[19,18,628,311]`.
- Same-run capture provenance, BoardPane bounds and transform gates passed for all orientations. ROI-margin pixels were separately recorded (17 pixels) and excluded from formal BoardPane comparison.
- The offline browser compositor used Edge/Chromium, but the same-session renderer manifest records Firefox 159. This is an uncontrolled rasterization/compositing difference and invalidates vertical/diagonal pixel acceptance as evidence of an offline renderer defect.
- Commits `cd12cac3bad2af9aa7df9030f69d2880ec160a74` and `bc787b8f06c3609c7f294beb0cb3ea4b6e1ae5ef` replace the Edge `<img>` overlay with a Firefox headless Canvas2D overlay, verify the live manifest's Firefox major version, and retain the no-registration rule.
- CI [42096244252](https://github.com/Kiddos19882/AutoDraw/actions/runs/42096244252) is pending. No vertical/diagonal PASS_PER_RUN is claimed until the same-browser comparison passes.
## 2026-11-05 — exact BoardPane bounds вместо calibrated ROI в formal renderer metrics

**Implementation:** [1ac3d9390c56072730017e073cf80dd69c448f8b](https://github.com/Kiddos19882/AutoDraw/commit/1ac3d9390c56072730017e073cf80dd69c448f8b), follow-up [e73506db2a2cfd55bbb0ea4c4a1616648b7f0065](https://github.com/Kiddos19882/AutoDraw/commit/e73506db2a2cfd55bbb0ea4c4a1616648b7f0065).
**Предыдущий CI:** [42087496092](https://github.com/Kiddos19882/AutoDraw/actions/runs/42087496092) — FAILED на horizontal formal renderer gate; transform и capture gates прошли.
**Текущий CI:** [42091800785](https://github.com/Kiddos19882/AutoDraw/actions/runs/42091800785) — IN_PROGRESS на момент записи.

- Причина: calibrated ROI `(496,265,674,355)` больше фактического BoardPane `(498,268,672,351)`. Horizontal full-screen diff содержал 17 изменившихся пикселей на одном ряду за пределами BoardPane, но внутри ROI. Эти UI pixels не относятся к offline BoardPane raster, однако попадали в formal bbox и symmetric-difference metrics.
- Контрольный replay run 42087496092: IoU `0.997323`, precision `0.997657`, recall `0.999665`, symmetric difference `24/8963`; bbox height включал дополнительные 170 px за пределами ожидаемого штриха. Причина локализована к ROI margin; пороги не менялись.
- Новый `crop_mask_to_board_bounds()` вырезает live и expected masks по точным screenshot-derived BoardPane bounds; изменившиеся pixels внутри ROI, но снаружи BoardPane, отдельно сохраняются в `outside-board-live-delta-mask.png` и в report, не влияя на BoardPane comparison.
- Добавлены regression tests: crop `672×351` исключает 17 outside-board pixels; некорректные bounds вне ROI/screen отклоняются.
- CI workflow продолжает vertical/diagonal replay даже если один из них отклонён, чтобы сохранить оба per-orientation reports.
- Расчёт на имеющемся horizontal CI artifact после exact BoardPane crop: IoU `0.999218`, precision `0.999553`, recall `0.999665`, symmetric difference `7` pixels, bbox совпадает. Это локальный повторный расчёт по артефакту, не результат нового CI.
- No live game run, production executor handoff or master change.
> Этот файл — единая точка входа для понимания результатов тестирования. Здесь собраны проверяемые сводные результаты, статусы, ограничения и ссылки на первичные отчёты/артефакты. Первичные JSON, PNG, логи, frozen plans, manifests и подробные отчёты не удаляются и не переписываются: они остаются источниками доказательств. Если краткая сводка расходится с первичным отчётом, приоритет имеет первичный материал и фактический runtime/CI evidence.


## 2026-11-05 — same-run geometry replay для vertical/diagonal (CI pending)

Implementation commit: 1cd0d6153bdd5e6ae6248a3a48dd1915595cccc9.
Workflow: [42083576282](https://github.com/Kiddos19882/AutoDraw/actions/runs/42083576282) — in progress at time of this update.

- CLI --same-run-geometry builds a geometry audit from exact Monitor run data and full-screen capture dimensions; no external/stale renderer snapshot is substituted.
- Unit tests added for evidence binding and fail-closed behavior. Their execution is included in the preparation/G3 CI job, still in progress at update time.
- Workflow now replays two immutable existing live captures:
  - Vertical run c860234f-995a-4789-9ac2-e05b322fe742, experiment 6f2227c7bce94fa5acd0c633af5ed04f, exact CHALK 71.
  - Diagonal run f69cb0f4-f5d0-4ff9-a3b7-1148c38fa07f, experiment 0e61bc40e5a8432fb87fa80b95889f4, exact CHALK 161.
- No new live game run was performed. Existing exploratory frozen-ROI numbers remain historical; independent comparison metrics and formal acceptance have not yet been emitted by the current workflow.
- CI jobs already successful at this update: Game Monitor/Bridge, Egret CanvasRenderer browser reference, Executor regression, Application integration. Preparation/G3 remains in progress; optional benchmarks skipped.
- A run-level PASS, if achieved, counts as one valid capture only; the required series still needs three unique PASS_PER_RUN captures per orientation.

## 2026-11-05 — first vertical and diagonal live captures (evidence commit e6b771e)

**Source commit:** [e6b771ed67201625884c6ce778fa355f1ab9b873](https://github.com/Kiddos19882/AutoDraw/commit/e6b771ed67201625884c6ce778fa355f1ab9b873). Commit adds 22 result artifacts (reports, manifests, logs and PNGs); no application code, tests, configuration or workflows changed.

### Exact live CHALK and event integrity

| Scenario | Run ID | Stroke | Radius | pointCount | Exact CHALK | MOUSE_MOVE_SAMPLE |
|---|---|---:|---:|---:|---:|---:|
| Vertical | `c860234f-995a-4789-9ac2-e05b322fe742` | 1 | 10 | 1 → 72 | **71** | 139 |
| Diagonal | `f69cb0f4-f5d0-4ff9-a3b7-1148c38fa07f` | 1 | 10 | 1 → 162 | **161** | 315 |

- Positive `DRAW_SAMPLE` and `POINT_QUOTA_UPDATE` counts equal exact CHALK (71/71 and 161/161); every positive event has `pointDelta=1` and `acceptedPoint`.
- Both runs have zero dropped events, Monitor error delta, Bridge send failures, sequence gaps and geometry updates. Start/end renderer geometry snapshots are identical.
- Radius 10 is observed in both runs. These different-length trajectories are not a radius-effect comparison.
- `trajectory.status=incomplete_until_verified` remains in the summaries with a coalescing note. Preserve this warning; raw positive events contain one accepted coordinate per pointCount increment.
- The linked calibration profile records screen 1920×1080, Windows scale 100%, browser zoom 100%, Firefox 159. Monitor reports DPR=1 and visualViewportScale=1. Windows scale comes from the profile calibrated earlier the same date, not a per-run display API.

### Same-run geometry from Monitor

- screen-client offsets are stable for all samples: X=0 px, Y=163 px; range=0 px on both axes.
- Both runs have BoardPane client corners top-left (497.960425,104.86), bottom-right (1170.106544,456.06). After the measured Y offset, the screen-space top-left is approximately (497.960425,267.86); inspect-derived extent is approximately 672.146×351.200 px.
- Vertical: Y span=201 logical px; Y fit origin=267.860071, scale=1.463264, RMSE=0.422 px, max residual=0.723222 px. X is unspanned and must use same-run screenshot BoardPane bounds.
- Diagonal: X span=419, Y span=201 logical px; X fit origin=497.945419, scale=1.461274, RMSE=0.423 px, max residual=0.730129 px; Y fit origin=267.870306, scale=1.463321, RMSE=0.427 px, max residual=0.739053 px. Both fit residuals are below the frozen 0.75 px limit; Y is close to the limit.
- These fits were calculated from raw Monitor samples using the same least-squares formula as `renderer_geometry.py`; the project CLI has not yet consumed them. Same-run before/after full-screen PNGs exist, but screenshot-derived BoardPane bounds for these specific runs have not yet been produced.

### Offline renderer comparison — exploratory only

Both `comparison-report.json` files have status `ANALYZED_EXPLORATORY_NO_ACCEPTANCE_THRESHOLD`; `independent_transform_comparison=null`. They use the frozen 674×355 calibrated ROI transform (scale X=1.463043478, Y=1.475), not the independently resolved same-run BoardPane transform.

| Scenario | Alpha-24 IoU | Precision | Recall | Symmetric difference | Difference / live changed pixels |
|---|---:|---:|---:|---:|---:|
| Vertical | 0.870044 | 0.932683 | 0.928340 | 685 px | 13.93% |
| Diagonal | 0.873071 | 0.926403 | 0.938140 | 1,464 px | 13.47% |

- Best-translation diagnostics: vertical (+1,+1) IoU=0.988100 / 59 differing pixels; diagonal (+2,+2) IoU=0.937057 / 702 differing pixels. These post-hoc fits are diagnostic only and prohibited for acceptance or production transforms.
- The offline Egret 5.4.1 WebGL harness matches its BoardPane reference fixture exactly (zero differing pixels). This validates the internal reference comparison, not live/offline equivalence.

**Interpretation:** current exploratory metrics are poor under the frozen ROI transform, but the formal independent-transform gate was not run. These captures are neither `PASS_PER_RUN` nor formal `REJECTED_PER_RUN`. Next: rerun offline with same-run Monitor geometry and screenshot-derived BoardPane bounds, without post-hoc translation.

**Frozen acceptance:** alpha 24; IoU/precision/recall each ≥0.995; symmetric difference ≤0.25% of live changed pixels; each bounding-box edge differs by ≤1 px; transform and axis-source requirements remain unchanged. Three unique `PASS_PER_RUN` captures per orientation are still required.

**Not performed in this review:** no game run, AutoDraw launch, raw evidence change or code/test/config/workflow change. CI 41994624425 applies to code/test commit 58ebdda7; no CI result for evidence-only commit e6b771e was confirmed.

## 2026-11-05 — full CI 41994624425 SUCCESS (code/test commit 58ebdda7)

**Workflow:** [41994624425](https://github.com/Kiddos19882/AutoDraw/actions/runs/41994624425) — conclusion SUCCESS.  
**Code/test commit:** `58ebdda7cf3f07ceef1075020f2808a2782562b7`.  
**Artifacts:** paired renderer `13399663414`; V1–V5 PNG analyzer `13400530501`; FILL-001-RS static sweep `13399922622`; capsule benchmark `13399777779`; INT-006 CHALK `13399473920`; INT006R `13399563542`; INT006R visual review source `13399289073`; Windows portable build `13399627749`.

### Required job summary

- Game Monitor/Bridge: SUCCESS; Browser Bridge telemetry lifecycle 4/4; Python WebSocket/snippet/run-provenance suite 31 passed.
- Application integration: SUCCESS.
- Executor regression: SUCCESS.
- Egret CanvasRenderer browser reference: SUCCESS.
- Preparation/G3: 880 passed, 24 warnings, 82 subtests. Capsule benchmark and FILL-001-RS static sweep ran and artifacts were uploaded.
- INT-006 pixel-level PNG geometry audit: SUCCESS.
- Windows portable build/startup smoke-test: SUCCESS; portable artifact 646,950,501 bytes.
- Optional algorithm benchmarks: SKIPPED by default configuration.

### Paired renderer formal per-run result

- Status: `PASS_PER_RUN` for the existing horizontal capture only.
- Alpha24: IoU=0.9988824318; precision=0.9991057456; recall=0.9997762864; symmetric difference=10 px; fraction=0.1117818%; bbox edge differences=[0,0,0,0].
- Exact CHALK=138 (`pointCount` 1→139); 138 accepted quota updates and 138 drawing samples, each pointDelta=1; one stroke ID; zero Monitor/Bridge integrity errors.
- Does not constitute multi-axis series acceptance: three unique vertical and three unique diagonal live captures are still required.

### V1–V5 pixel analyzer

- 90/90 captures valid; 10 independent series × 9 runs; no missing or duplicate matrix cells.
- Artifact `13400530501`. This validates capture identity/completeness and provides pixel diagnostics; the analyzer does not declare a universal quality PASS for all series.

### INT-006 and INT006R

- INT-006 frozen prediction: 45/45 accepted. Actual total 3910, predicted total 3949.38; MAE=1.408, RMSE=1.967, bias=-0.875, MAPE=2.134%, maximum absolute error=4.94, maximum underprediction=1.82.
- P0: MAE/RMSE/MAPE=2.882/3.189/3.484%, max underprediction=0.99.
- P1: 0.657/0.838/1.178%, max underprediction=0.92.
- P2: 0.685/0.854/1.741%, max underprediction=1.82.
- Safety margin status remains `not_established`; production eligibility `not_validated`.
- INT006R: 45/45 accepted; average exact CHALK radius 1/10/30 = 67.40/67.67/67.80. The latest artifact marks visual-quality review `pending_manual_review`; visual-review source is separately preserved.

### FILL-001-RS and capsule offline evidence

- Static sweep reproduced 2,238 candidates; 62 accepted; 15/15 selected shape×radius cells pass the offline gate (coverage≥99%, leakage=0).
- Rectangle/radius10 selected candidate: step=5, offset=0, 27 strokes, coverage=99.3191947%, leakage=0, estimated sampling points=2,099. This last value is an estimate, not exact CHALK.
- Capsule benchmark: masks equivalent in all five cases. Candidate-slot reductions: winding 91.09%, large zigzag 96.23%, diagonal turns 59.53%, compact many-segment 92.24%, single long diagonal 0%. Median runner speedups: 10.92×, 20.20×, 2.74×, 13.87× and 1.14× respectively. These are environment-specific offline geometry timings, not CHALK measurements or guaranteed application-wide speedups.
- FILL-001 committed live PNG quality gate remains FAIL: coverage=98.430600%, leakage=11. This is separate from the offline sweep and paired renderer PASS. The 45-cell live matrix remains BLOCKED.

### Bridge input telemetry automation

- Paired scenarios opt in through `--enable-input-telemetry`; ordinary Bridge sessions leave Monitor telemetry unchanged.
- Browser Bridge preserves an already-enabled user setting, enables only when required, restores changed state at disconnect and reports configuration in `session_start`.
- Server stores `bridge_configuration` in session.json and `bridge_configuration_at_start` in run JSON.
- CI verified Node lifecycle 4/4 and Python suite 31 passed. Earlier runs `41994014564` and `41994258815` failed on test-only expectation/import issues; those attempts remain preserved and corrected code passed run `41994624425`.

**Not performed:** no new live game experiment, no local AutoDraw launch, no local `git status`, no production renderer/planner/estimator/calibration/executor default changes.

## 2026-11-05 — exploratory live/offline renderer comparison and transform audit

**Experiment:** d47cc0a5520044c7abfd0352a4f93ca8; **run:** 16aec62c-9e54-44e7-8691-9df79b19161d; **session:** d357b6ee-5617-4e07-9011-7eba7ccb6c0f. Raw capture and offline renderer inputs remain immutable.

### Quantitative comparison (exploratory; no acceptance threshold)

- Frozen, unshifted mapping at alpha threshold 24: live changed mask 8,946 px; offline expected mask 8,950 px; TP=7,746, FP=1,200, FN=1,204; symmetric difference=2,404 px; IoU=0.763153; precision=0.865862; recall=0.865475; F1=0.865668.
- Post-hoc diagnostic search over translations ±5 px found best translation of the expected mask (+1,+2): TP=8,943, FP=3, FN=7; symmetric difference=10 px; IoU=0.998883; precision=0.999665; recall=0.999218; F1=0.999441.
- The second result is a fit against this same image pair. It is evidence that the footprints are highly similar after translation, but it is not an independently derived coordinate correction, does not establish the cause of the offset and is not acceptance. Do not apply (+1,+2) to production or frozen plans.

### Independent geometric audit of the frozen plan

- The paired plan uses ROI (496,265,674,355), logical board 460×240 and pixel-center scales scale_x=(674-1)/460=1.4630434783, scale_y=(355-1)/240=1.475.
- Relative X/Y scale discrepancy is 0.8106%, just inside the transform helper's 1% tolerance. However, the logical aspect ratio is 1.916667 while ROI aspect ratio is 1.898592. If the ROI were a uniform-scale rectangle, a 355 px height would correspond to about 680.21 px width, approximately 6.21 px wider than the selected 674 px ROI.
- The ROI coordinates come from the configured screen calibration/blank-board crop. The 2026-11-04 runtime snapshot has boardClientCorners=null and belongs to a different session; it cannot independently validate the live 2026-11-05 crop origin or client-space corners.
- This establishes a measurable geometric inconsistency in the selected ROI dimensions, not the root cause of the (+1,+2) residual. Candidate causes (ROI edge/crop convention, pixel-center versus board-boundary mapping, resampling, antialiasing, baseline drift and color handling) remain unseparated.

**Status:** comparison analyzed as exploratory; live/offline renderer equivalence and transform root cause remain NOT ACCEPTED / OPEN. FILL-001-RS 45-cell matrix remains BLOCKED. No live experiment was run during this continuation; no production planner, renderer, executor, CHALK estimator, frozen plan or raw evidence was changed.

**Next offline action:** derive board bounds and crop origin independently from the same-session after_draw-screen.png (and before/blank reference), compare them with the calibrated ROI, then evaluate the existing frozen pixel-center/boundary mapping and a uniform-scale transform from independently measured edges. Keep the current frozen transform and post-hoc diagnostic separate; define acceptance criteria before any confirmatory comparison.
## 2026-11-05 — formal per-run renderer acceptance tooling

- Added capture validation that checks run/session/experiment binding, exact pre/post pointCount, accepted-point completeness, per-event pointDelta, stroke identity, bridge integrity counters, brush radius, executor profile, clean-board state and fixture binding.
- Added same-run transform checks and the predeclared alpha-24 renderer gates. The post-hoc best-translation diagnostic remains non-acceptance evidence and is excluded from formal scoring.
- Added a distinct series aggregator: three unique per-run PASS captures per orientation are required for vertical and diagonal. Rejected and duplicate attempts are recorded but do not count.
- Unit/regression tests прошли full CI [41994624425](https://github.com/Kiddos19882/AutoDraw/actions/runs/41994624425) SUCCESS. No new live experiment or raw evidence mutation was performed.

## 1. Правила чтения и доказательности

### 1.1. Статусы

- **PASS** — конкретная проверка завершилась успешно по указанному критерию.
- **FAIL** — конкретный gate/тест не прошёл; это не означает, что весь проект неисправен.
- **CANCELLED** — запуск отменён; не приравнивать к FAIL или PASS.
- **SKIPPED** — проверка не запускалась в данном workflow/run.
- **BLOCKED** — выполнение запрещено/заблокировано незакрытым gate.
- **PENDING / UNKNOWN** — данных недостаточно для подтверждения.
- **HISTORICAL** — результат относится к более ранней версии/сценарию и не подтверждает текущее состояние.

### 1.2. Разделение уровней

| Уровень | Что подтверждает | Чего не подтверждает |
|---|---|---|
| Unit / regression tests | Проверяемые программные контракты и сценарии | Поведение игры, renderer, фактический CHALK |
| Integration / UI tests | Интеграционные связи, импорты, передачу данных, тестируемые UI contracts | Полную ручную работоспособность UI и рисование в игре |
| Build / startup smoke-test | Сборку и отсутствие немедленного сбоя старта | Корректность интерактивного UI и качество рисунка |
| GitHub Actions | Результат конкретных jobs на конкретном commit | Runtime вне тестовой среды, если он отдельно не проверялся |
| Offline benchmark | Сравнение реализаций на указанных fixtures и среде | Универсальный speedup, CHALK и эквивалентность игровому renderer |
| Live game experiment | Поведение игры в конкретном запуске при наличии пригодных captures | Автоматически — обобщение на все геометрии/параметры |
| Visual / PNG audit | Качество конкретных сохранённых изображений по указанным критериям | Точный CHALK без pointCount и неиспытанные сценарии |

### 1.3. Точный расход CHALK

Для игрового движка точный расход — только:

`CHALK = pointCount_after - pointCount_before`

Не использовать длину траектории, число штрихов, площадь, радиус кисти или оценку индикатора краски как точное измерение CHALK. Per-stroke значения должны быть связаны с конкретным run и его исходным/конечным pointCount. При исчерпании квоты до завершения рисунка фиксировать censored/неполный запуск; полная стоимость рисунка неизвестна.

### 1.4. Текущая граница инвентаризации

GitHub tree на HEAD `0a5fa41c` содержит 5 413 файлов; 5 011 файлов находятся под `AutoDraw_Stage20/data/results/`. Это инвентаризация файлов по дереву Git, а не утверждение, что каждый артефакт был независимо открыт и повторно проанализирован при создании этого реестра. Массовые первичные данные перечислены по семействам/каталогам; отдельные файлы не дублируются в Markdown.

Локальный `git status` через GitHub API недоступен. Данный документ отражает GitHub branch snapshot, а не локальную рабочую копию.

## 1.5. Egret WebGL renderer reference — mask/scrollRect correction (2026-11-04)

**Commit:** `5308fade07fbb11409a9afc5c3d40ed4cf82ca3a`  
**CI:** [41924481247](https://github.com/Kiddos19882/AutoDraw/actions/runs/41924481247) — SUCCESS.  
**Browser job:** `126905145909` — SUCCESS.  
**Artifact:** [13368272823](https://github.com/Kiddos19882/AutoDraw/actions/runs/41924481247/artifacts/13368272823), manifest + 54 PNG.

Причина прежних крупных `mask-corner` расхождений найдена в harness: mask object не был прикреплён к Egret Stage. В Egret 5.4.1 объектная маска переводит masked display object в renderMode=3 только если `mask.$stage` установлен. Harness теперь создаёт Stage и помещает board + mask в общую display-list сцену; assertions проверяют stage attachment, одинаковые stage/parent и boardRenderMode=3.

| Fixture | Width | Differing pixels | Max channel delta |
|---|---:|---:|---:|
| smooth-single-point | 10 / 30 | 0 / 0 | 0 / 0 |
| scrollrect-edges | 10 / 30 | 0 / 0 | 0 / 0 |
| mask-corner | 10 | 145 | 1 |
| mask-corner | 30 | 36 | 1 |
| Остальные fixtures (12 comparisons) | 10 / 30 | differing pixels присутствуют во всех 12 comparisons | 1 |

Итого: 18/18 WebGL comparisons созданы; 4 exact, 14 имеют max channel delta=1, ни одного delta выше 1. Для сравнения, до stage-binding correction mask-corner имел 193/84 differing pixels и max delta=255. Среда: Egret 5.4.1, Edge 156, WebGL 1 / ANGLE SwiftShader, rasterScale=3, board output 1380×720. Это E3 browser/CI evidence для offline renderer harness, не E4 live game capture.

**Ограничения:** residual delta=1 не классифицирован как дефект; exact popup transform и paired live board PNG + accepted points + pointCount из одной сессии не получены. CHALK и production footprint модель этим тестом не измерялись. FILL-001-RS 45-task matrix остаётся BLOCKED.

## 1.6. PainterPopup BoardPane runtime transform (2026-11-04)

**Источник:** `data/runtime/renderer_snapshot_2026-11-04.json`, provenance — полный read-only `inspect()` snapshot, предоставленный пользователем; blob SHA `99aaee478d0355d01be9d36770964293753d1486`.

- BoardPane local position `(30,75)`, size `460×240`, scale `(1,1)`.
- Parent PainterPopup position `(489.791666,-3)`, size `676×379`.
- BoardPane concatenated matrix: `a=1, b=0, c=0, d=1, tx=519.7916660308838, ty=72`.
- Runtime snapshot фиксирует Egret `engineVersion=5.4.1`; согласованный source trace подтверждает default round caps/joints.
- boardMask concatenated matrix совпадает с BoardPane matrix.
- Canvas CSS rect: `(left=0, top=-0.5, width=1920, height=690)`; Stage `1672×600`; client-space affine scale выводится из этих размеров.
- `boardClientCorners=null`, `getBoxQuads()` недоступен. Следовательно, screen/client corners — derived values, не direct runtime measurements.

**Вывод:** stage-space parent chain и transform установлены для этого snapshot. Это не paired PNG capture и не измерение фактического swept footprint кисти; live renderer comparison остаётся открытым.

## 1.7. Egret zero-length normal segment — controlled PNG result (2026-11-04)

**Commit:** `63c14b8d5428bf61c439fb2c0bf1c630538b6118`  
**CI:** [41926175588](https://github.com/Kiddos19882/AutoDraw/actions/runs/41926175588) — SUCCESS.  
**Browser job:** `126911052714` — SUCCESS.  
**Artifact:** [13368772614](https://github.com/Kiddos19882/AutoDraw/actions/runs/41926175588/artifacts/13368772614), manifest + 60 PNG.

Fixture `normal-zero-length-segment` создаёт actual BoardPane и задаёт normal path с двумя одинаковыми точками: `moveTo(100,100) → lineTo(100,100)`. Проверены widths 10 и 30.

| Width | CanvasRenderer source alpha pixels | Masked Canvas2D alpha pixels | WebGL alpha pixels | Canvas↔WebGL |
|---:|---:|---:|---:|---|
| 10 | 0 | 0 | 0 | exact |
| 30 | 0 | 0 | 0 | exact |

В обеих комбинациях alpha bbox пустой. В manifest: `actualBoardPane=true`, `manualTranscriptionMatch.equal=true`, `webglPixelComparison.equal=true`, `boardRenderMode=3`.

**Ограничение:** points назначены напрямую в `atom.points`, обходя `BlackBoardAtom.pushPoint()` duplicate suppression. Это controlled renderer test, а не доказательство, что live input передаёт повторные точки. В обычном live flow повторяющиеся принятые координаты deduplicate. CHALK/pointCount в этом offline test не измерялись.

Расширенная матрица содержит 20 fixture-width entries, 20 WebGL comparisons и 60 PNG: 6 exact comparisons, 14 с max channel delta=1; max delta=1.

## 2. Сводный статус ключевых исследовательских серий

| Серия | Область | Подтверждённый итог | Текущий статус / ограничения |
|---|---|---|---|
| Brush behavior / первичные измерения | Горизонтальные/диагональные линии, короткие штрихи, повороты, контуры, пересечения, границы доски | Сохранены многочисленные планы, Game Monitor runs, JSON и PNG; агрегаты отдельных серий приведены в профильных отчётах | Не сводить все runs в один средний показатель: сценарии, радиусы и sampling configs различаются |
| CHALK radius matrix | Сравнение радиусов кисти | 21 live experiment, 7 радиусов, 3 независимых повтора/блока; средние расходы по радиусам около 724–727 CHALK, индивидуальные 722–728 | В этом сценарии систематическая зависимость pointCount от радиуса не обнаружена; не универсальный закон |
| CHALK G1 geometry matrix | Геометрия при контролируемых параметрах | 12 live runs; точные per-stroke CHALK зафиксированы в первичном отчёте | Отмечена проблема repeat metadata; учитывать ограничения отчёта |
| CHALK G2 geometry matrix | Дополнительная геометрическая серия | Отдельный results report существует | Подробные численные выводы брать из первичного отчёта; не объединять с G1 без проверки совместимости протоколов |
| CHALK G3 sampling matrix | Длинные горизонтальные линии, sampling step/delay | 27/27 completed, 0 failed, 0 pending; точный CHALK подтверждён для всех captures | Radius=10 и одна геометрия; перенос коэффициентов на произвольный рисунок не доказан |
| INT-006 V1–V5 | Независимая validation геометрии и CHALK | 45/45 accepted captures в основной серии; follow-up V1–V5 — ещё 45/45 captures | Принимать выводы только в границах frozen scenarios, профилей и критериев |
| INT-006 official validation | Проверка прогнозной модели на независимых captures | Официальный отчёт указывает 45/45 accepted | MAE/RMSE/bias, safety margin и production eligibility смотреть в отчёте; 45/45 accepted не означает автоматически production-ready |
| INT006R | Радиус × геометрия, D1–D5 × radius 1/10/30 | 45/45 completed; raw-data audit PASS; официальный analyzer PASS (45 accepted); ручной аудит 90 PNG завершён | CHALK-эффект радиуса мал в этой матрице; визуальные ограничения D2/radius=1 и D4/radius=30; см. подробную матрицу ниже |
| FILL-001 initial live preflight | Реальная заливка с радиусом 10 | Один run завершил 27 strokes; pointCount 1→6000, exact CHALK=5999, квота исчерпана до трёх последних consuming strokes | Неполный/censored run; полная стоимость завершённого рисунка неизвестна; 45-cell matrix заблокирована |
| FILL-001-RS live preflight | Versioned scanline spacing candidate | Run 27/27 strokes, pointCount 1→1261, exact CHALK=1260; Bridge diagnostics без потерь/ошибок | Capture REJECTED PNG gate: после исправленного audit coverage=98.430600%, leakage=11; требования coverage≥99% и leakage=0 не выполнены; 45-task matrix BLOCKED |
| FILL-001-RS static sweep | Offline OpenCV scanline spacing | Exhaustive sweep 2 238 candidates; 62 прошли существующий статический gate; выбраны 15/15 shape/radius cells | Только offline geometry proxy; не подтверждает фактический CHALK или renderer |
| Capsule footprint geometry | Offline ideal capsule rasterization | Independent oracle: 7 parametrized edge cases + 16 seeded polylines; masks совпали | Модель не подтверждена против deployed Egret renderer |
| Capsule broad-phase benchmark | Global-AABB vs per-segment candidate enumeration | 5 synthetic polylines; masks совпали во всех 5 сценариях | Скорость зависит от геометрии; benchmark не измеряет CHALK и не доказывает renderer equivalence |

## 3. Детальные результаты CHALK

### 3.1. G3 — sampling step и delay

Первичный источник: [CHALK_G3_RESULTS_2026-11-02.md](CHALK_G3_RESULTS_2026-11-02.md). В сценарии шесть горизонтальных линий по 400 logical px (суммарно 2400 logical px), radius=10, 3 повтора для каждой из 9 комбинаций `point_step_px` 1/2/4 и `point_delay_ms` 5/10/20.

| Step | Delay | CHALK repeats | Среднее CHALK | Средняя длительность |
|---:|---:|---:|---:|---:|
| 1 | 5 ms | 1359 / 1350 / 1344 | 1351.0 | 53.36 s |
| 1 | 10 ms | 1350 / 1360 / 1341 | 1350.3 | 53.38 s |
| 1 | 20 ms | 2087 / 2084 / 2038 | 2069.7 | 100.61 s |
| 2 | 5 ms | 717 / 717 / 716 | 716.7 | 29.76 s |
| 2 | 10 ms | 719 / 716 / 719 | 718.0 | 29.78 s |
| 2 | 20 ms | 1384 / 1381 / 1384 | 1383.0 | 53.40 s |
| 4 | 5 ms | 365 / 366 / 366 | 365.7 | 17.99 s |
| 4 | 10 ms | 363 / 366 / 366 | 365.0 | 18.04 s |
| 4 | 20 ms | 715 / 710 / 716 | 713.7 | 29.85 s |

- Для этой геометрии step=4 / delay=5 или 10 дал около 365 CHALK; визуальный аудит всех шести PNG показал непрерывные ровные линии.
- Delay=20 существенно увеличил расход для всех трёх шагов.
- Step=4 — кандидат для длинных прямых линий данного сценария, не универсальный production default.
- В G3 radius зафиксирован на 10; влияние радиуса исследовалось отдельной серией.
- Paint-meter image estimate не использовался как точный источник; exact game pointCount — источник расхода.
- В отчёте зафиксированы ограничения coalescing: промежуточные координаты не восстанавливаются полностью.

### 3.2. Radius matrix

Первичный источник: [CHALK_RADIUS_MATRIX_RESULTS.md](CHALK_RADIUS_MATRIX_RESULTS.md).

- 21 experiment, 7 радиусов, 3 независимых блока.
- Средние CHALK по радиусам находятся примерно в диапазоне 724–727; индивидуальные результаты 722–728.
- В рамках данного сценария систематической зависимости игрового pointCount от радиуса не обнаружено.
- Это не доказывает, что радиус не влияет на качество, покрытие, ширину следа или число проходов. Он не должен вводиться в формулу CHALK как прямой множитель без дополнительных измерений.

### 3.3. G1 / G2 geometry matrices

- [G1 results](CHALK_GEOMETRY_MATRIX_G1_RESULTS.md): 12 live runs, точные per-stroke значения; отчёт отмечает repeat metadata issue.
- [G2 results](CHALK_GEOMETRY_MATRIX_G2_RESULTS.md): отдельная геометрическая серия; не объединять статистику с G1 без проверки условий, repeats и протокола.
- Общие выводы по коротким штрихам, диагоналям, поворотам, контурам и пересечениям брать из соответствующих первичных серий INT-006/INT006R и brush run JSON.

### 3.4. INT-006 V1–V5

- [Основная live-матрица](CHALK_INT006_V1_V5_RESULTS_2026-11-02.md): 45/45 captures, exact/per-stroke CHALK, sampling profiles, первичная holdout-проверка модели и quality gates.
- [Follow-up V1–V5](CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md): 45/45 дополнительных captures после исправления геометрии/сценариев; raw repeat CHALK, P0/P1/P2 и pixel-level gates.
- [Official independent validation](CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md): официальный analyzer report, 45/45 accepted; метрики ошибки и safety-margin ограничения — в первичном документе.
- [PNG screening](CHALK_INT006_PNG_SCREENING_2026-11-02.md) и [pixel audit](CHALK_INT006_PIXEL_AUDIT_2026-11-02.md) фиксируют визуальную/пиксельную сторону проверки отдельно от CHALK.

### 3.5. INT006R radius × geometry

Первичные источники: [live results](CHALK_INT006R_LIVE_RESULTS_2026-11-03.md), [software gate](CHALK_INT006R_SOFTWARE_GATE_RESULTS_2026-11-03.md), [visual audit](CHALK_INT006R_VISUAL_AUDIT_2026-11-03.md).

- 45 captures по D1–D5 и радиусам 1/10/30.
- Exact CHALK и raw-data integrity проверялись отдельно от визуального качества.
- Отдельно задокументированы ограничения D2/radius=1 и D4/radius=30.
- Полнота captures не заменяет visual-quality gate.

### 3.6. INT006R — подробная матрица D1–D5 × радиус кисти

**Серия:** `chalk-20261103-030837-a20df5`  
**Block ID:** `a8e0b9ec87984f60aa294910d366e987`  
**Последний commit с live-данными:** [138c9fbeaf612a86819f7ff9ea0db7bb1fe4296a](https://github.com/Kiddos19882/AutoDraw/commit/138c9fbeaf612a86819f7ff9ea0db7bb1fe4296a)  
**Профиль:** P1 — `point_step_px=4`, `point_delay_ms=5`  
**Матрица:** 5 геометрий × 3 радиуса (1/10/30) × 3 повтора = 45 captures.

| ID | Геометрия | Radius 1: CHALK mean | Radius 10: CHALK mean | Radius 30: CHALK mean | Визуальный результат |
|---|---|---:|---:|---:|---|
| D1 | Mixed lines | 62.67 | 62.33 | 63.33 | Все четыре штриха видимы на всех радиусах; непредусмотренного слияния/потерь не найдено |
| D2 | Polygon | 71.67 | 71.00 | 71.00 | Radius 1: небольшой разрыв верхнего левого соединения первой и пятой сторон во всех 3 повторах; radius 10/30: контур замкнут |
| D3 | Intersections | 100.00 | 100.67 | 99.67 | Все 6 штрихов и ожидаемые пересечения видимы; пересечения соответствуют DrawingPlan |
| D4 | Short details | 14.33 | 14.67 | 15.33 | Radius 1: детали различимы, но очень тонкие; radius 10: все 6 разделены; radius 30: первые 3 детали (1/2/3 logical px) сливаются, остаётся 4 компонента |
| D5 | Repeated coverage | 88.33 | 89.67 | 89.67 | Повторные проходы совпадают с траекториями; ожидаемое наложение, посторонних следов нет |

Средние значения рассчитаны по трём повторам в каждой ячейке. Суммарный exact CHALK по 15 опытам каждого радиуса: radius 1 — 1011; radius 10 — 1015; radius 30 — 1017. Среднее на опыт: 67.40 / 67.67 / 67.80 соответственно. Разница между суммарными значениями крайних радиусов — 6 CHALK (около 0.6% от radius 1).

**Integrity / acceptance:**
- 45/45 задач имеют `status=completed`, по одной completed attempt на задачу.
- Во всех 45 Monitor reports `chalk.status=exact`; CHALK вычислен как `post.pointCount - pre.pointCount`.
- Сумма sampled `DRAW_SAMPLE.pointDelta` совпадает с exact CHALK; `point_delta_matches_chalk=true`.
- Observed radius совпал с requested radius (1/10/30).
- Dropped events, Monitor error delta, Bridge send-failure delta и collector sequence gaps — 0.
- Официальный CLI analyzer на реальном journal/capture bundle: [CI 41563236073](https://github.com/Kiddos19882/AutoDraw/actions/runs/41563236073), 45 accepted, 0 missing/rejected, PNG evidence complete.
- Ручной аудит всех 45 пар (90 PNG) завершён; все 45 пар присутствуют и читаемы, before ROI визуально пустые, after ROI содержат ожидаемую геометрию.

**Вывод по CHALK:** в рамках D1–D5, sampling P1 и радиусов 1–30 заметного преимущества большого радиуса по exact CHALK не обнаружено. Не вводить radius multiplier и не выбирать radius 30 ради предполагаемой экономии на основании этой серии.

**Вывод по качеству:** радиус влияет на визуальный результат в конкретных геометриях: radius 1 недостаточен для надёжного замыкания D2 при текущем P1; radius 30 сливает первые короткие элементы D4; radius 10 сохранил замыкание D2 и разделение деталей D4 в этой матрице. Это локальные наблюдения, не универсальное правило.

**Граница применимости:** D2 — геометрия полигона, а не полноценная заливка площади; D5 — повторное покрытие линий, а не заливка одноцветной области. INT006R не определяет лучший радиус для FILL. Для этого предназначен отдельный FILL-001.

Первичные документы:
- [INT006R live results](CHALK_INT006R_LIVE_RESULTS_2026-11-03.md)
- [INT006R software gate](CHALK_INT006R_SOFTWARE_GATE_RESULTS_2026-11-03.md)
- [INT006R visual audit](CHALK_INT006R_VISUAL_AUDIT_2026-11-03.md)
- [INT006R live preflight and visual audit](CHALK_INT006R_LIVE_PREFLIGHT_AND_VISUAL_AUDIT_2026-11-03.md)
- [Radius × geometry cross-validation plan](CHALK_RADIUS_GEOMETRY_CROSS_VALIDATION_PLAN_2026-11-03.md)

## 4. FILL-001 и FILL-001-RS

### 4.1. FILL-001 quota-exhausted preflight

Источник: [CHALK_FILL001_PREFLIGHT_POSTMORTEM_2026-11-04.md](CHALK_FILL001_PREFLIGHT_POSTMORTEM_2026-11-04.md).

- Live preflight исчерпал лимит на 5999 CHALK до завершения трёх последних consuming strokes.
- Это censored run: наблюдаемый расход до остановки известен, но стоимость полного рисунка не измерена.
- Нельзя использовать 5999 как расход полного завершённого рисунка.
- 45-task matrix не открывается до успешного отдельного preflight gate.

### 4.2. FILL-001-RS rejected capture

Источники: [replay report](CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md), [static sweep](CHALK_FILL001_RS_STATIC_SWEEP_2026-11-04.md), [postmortem](CHALK_FILL001_PREFLIGHT_POSTMORTEM_2026-11-04.md).

- Runtime binding подтверждён для single-task run; 27/27 strokes, pointCount 1→1261, exact CHALK=1260.
- Bridge diagnostics: 0 sequence gaps, 0 dropped events, 0 Monitor errors, 0 send failures.
- Первоначальный PNG audit: coverage=97.673218%, leakage=28.
- После исправления affine mapping и повторного audit исходной PNG пары: coverage=98.430600%, leakage=11.
- Улучшение audit не закрывает gate: acceptance требует coverage≥99% и leakage=0. Capture остаётся REJECTED.
- Exact CHALK=1260 относится только к данному run и не заменяет PNG quality gate.
- 45-task RS matrix остаётся BLOCKED.

### 4.3. Static sweep

- Проверено 2 238 сочетаний spacing/offset.
- 62 кандидата прошли существующие статические условия.
- Выбраны 15 конфигураций для 15/15 shape/radius cells.
- Использованы OpenCV coverage/leakage и estimated sampling points/path/strokes.
- Это статические proxy; они не являются точным CHALK и не доказывают поведение игрового renderer.

## 5. Brush behavior lab и первичные данные

### 5.1. Назначение каталога

Основной каталог: `AutoDraw_Stage20/data/results/brush_behavior_tests/`.

Содержит семейства планов и результатов по:
- горизонтальным и диагональным длинам;
- коротким и длинным изолированным линиям;
- непрерывным поворотам и замкнутым контурам;
- пересечениям и spacing;
- границам доски;
- потреблению краски на длинных линиях;
- INT-006 V1–V5 и follow-up;
- INT006R D1–D5 × radius 1/10/30;
- Game Monitor raw run JSON, per-stroke/experiment summaries, before/after PNG и auxiliary audit files.

Первичные файлы не следует редактировать при последующей аналитике. Для численных выводов использовать соответствующий сводный отчёт и связанные raw artifacts.

### 5.2. Существующие агрегаты

- [BRUSH_TEST_RESULTS_ANALYSIS_2026-10-30.md](../BRUSH_TEST_RESULTS_ANALYSIS_2026-10-30.md) — исторический анализ ранних brush tests.
- [ANALYSIS_RESULTS_2026-10-29.md](../data/results/brush_behavior_tests/ANALYSIS_RESULTS_2026-10-29.md) и [ANALYSIS_AUDIT_2026-10-29.md](../data/results/brush_behavior_tests/ANALYSIS_AUDIT_2026-10-29.md) — ранние сводка и аудит; считать историческими относительно более поздних INT-006/G3/INT006R серий.
- [BRUSH_TEST_AUTOMATION_VISION.md](BRUSH_TEST_AUTOMATION_VISION.md) и [BRUSH_MONITOR_AUTOCAPTURE_DESIGN.md](../BRUSH_MONITOR_AUTOCAPTURE_DESIGN.md) — архитектура лаборатории/автосбора, не результаты фактического запуска.

### 5.3. Историческая модель расхода

[AutoDraw_Stage20/TEST_RESULTS.txt](../TEST_RESULTS.txt) — устаревшая сводка на 27 октября 2026, commit `6068366b`, CI run [40547157885](https://github.com/Kiddos19882/AutoDraw/actions/runs/40547157885). Она фиксировала ранние тестовые количества и эмпирическую модель «эффективная длина пути + 6,67 × число штрихов», основанную на четырёх наблюдениях. Это исторический baseline, не текущая точная модель CHALK. Не использовать эти коэффициенты как подтверждённую игровую формулу: дальнейшие live серии показали зависимость от sampling step/delay и необходимость калибровки по точному pointCount.

## 6. Capsule footprint geometry и benchmark

### 6.1. Геометрическая модель

Код: `source/preparation/brush_footprint_geometry.py`.  
Тест: `source/preparation/tests/test_capsule_footprint_masks.py`.

- Модель строит potential/guaranteed pixel-cell masks для swept capsule polyline.
- Добавлен independent full-canvas oracle, использующий собственные orientation tests и point-segment distance, а не production helpers.
- Проверены 7 parametrized edge cases и 16 seeded polylines.
- В тестовых случаях masks совпали.
- Это независимая программная геометрическая проверка, не эталон игрового renderer.

### 6.2. Per-segment broad-phase benchmark

Скрипт: `tests/benchmark_capsule_rasterization.py`.  
Workflow: `.github/workflows/geometry-tests.yml`.  
CI artifact: `autodraw-capsule-broad-phase-benchmark`, artifact ID `13338434277`.  
Final CI: [41859709320](https://github.com/Kiddos19882/AutoDraw/actions/runs/41859709320), commit `af30b5fdf1c926d3493bff90706806f5d3a28c43`.

| Synthetic scenario | Candidate slots reduction | Geometry predicate calls reduction | Median speedup |
|---|---:|---:|---:|
| Winding polyline | 91.09% | 89.30% | 10.91× |
| Large zigzag | 96.23% | 94.08% | 20.57× |
| Diagonal turns | 59.53% | 58.95% | 2.76× |
| Compact many-segment | 92.24% | 92.09% | 14.10× |
| Single long segment | 0% | 0% | 1.16× |

Во всех пяти случаях masks совпали. Время измерено на Windows GitHub runner, 7 repeats, synthetic inputs. Speedup не переносить на другие среды/геометрии как гарантию. Это offline rasterization benchmark, не CHALK measurement, не runtime benchmark игры и не renderer-equivalence test.

### 6.3. Benchmark history

- CI [41857043512](https://github.com/Kiddos19882/AutoDraw/actions/runs/41857043512): выявил ModuleNotFoundError из-за module path; benchmark не принят как финальный.
- CI [41858081222](https://github.com/Kiddos19882/AutoDraw/actions/runs/41858081222): workflow прошёл, но review artifact выявил неполный reference counter для вложенных predicate calls; эти счётчики не использовались для финального сравнения.
- Исправленный подсчёт вложенных вызовов: commit `af30b5f`; финальный benchmark artifact `13338434277` использует симметричную instrumentation обоих вариантов.

## 7. Автоматические тесты и GitHub Actions

### 7.1. CI workflow

Основной workflow: [geometry-tests.yml](../../.github/workflows/geometry-tests.yml).  
Подробная карта test modules, commands, jobs и artifact flow: [TESTS_AND_CI_MAP.md](TESTS_AND_CI_MAP.md).

Workflow включает:
- Game Monitor/Bridge tests и WebSocket smoke;
- Preparation pytest;
- capsule broad-phase benchmark;
- FILL-001-RS static sweep;
- Application integration tests;
- Executor unittest discovery;
- INT-006 PNG/pixel analysis;
- Windows portable build и startup smoke-test;
- optional algorithm benchmarks (по умолчанию SKIPPED, запускаются отдельно через workflow_dispatch).

### 7.2. Важные CI runs

| Run | Commit / lineage | Статус | Результат и оговорки |
|---|---|---|---|
| [40547157885](https://github.com/Kiddos19882/AutoDraw/actions/runs/40547157885) | `6068366b` | PASS, historical | Ранние test counts и Windows build/startup smoke-test; см. старый `TEST_RESULTS.txt` |
| [41772866679](https://github.com/Kiddos19882/AutoDraw/actions/runs/41772866679) | `974f949` lineage | PASS | Все 6 обязательных jobs SUCCESS; run предшествует последующим affine correction commits и не валидирует их |
| [41778045384](https://github.com/Kiddos19882/AutoDraw/actions/runs/41778045384) | pre-fix FILL-001-RS | FAIL | Preparation/G3: 799 passed, 5 failed; synthetic PNG fixtures/ROI test issues; остальные перечисленные jobs успешны, PNG audit/build skipped |
| [41780241017](https://github.com/Kiddos19882/AutoDraw/actions/runs/41780241017) | `0f23731` | CI PASS / PNG gate FAIL | Regression tests и replay выполнены; corrected audit coverage=98.430600%, leakage=11; capture не принят |
| [41840281018](https://github.com/Kiddos19882/AutoDraw/actions/runs/41840281018) | telemetry lineage | CANCELLED | Не приравнивать к FAIL или PASS; отдельные успешные jobs не заменяют полный CI |
| [41840582147](https://github.com/Kiddos19882/AutoDraw/actions/runs/41840582147) | telemetry lineage | PASS | Обязательные jobs SUCCESS, optional algorithm benchmarks SKIPPED |
| [41842587672](https://github.com/Kiddos19882/AutoDraw/actions/runs/41842587672) | capsule candidate | PASS | 820 passed, 24 warnings, 82 subtests; более поздние oracle/benchmark refinements этим run не покрываются |
| [41848358502](https://github.com/Kiddos19882/AutoDraw/actions/runs/41848358502) | segmented capsule | PASS | Эквивалентность capsule rasterization на первоначальном наборе тестов |
| [41849580047](https://github.com/Kiddos19882/AutoDraw/actions/runs/41849580047) | independent oracle | PASS | Независимый oracle добавлен и проверен |
| [41859709320](https://github.com/Kiddos19882/AutoDraw/actions/runs/41859709320) | `af30b5f` | PASS | Preparation/G3 832 passed, 24 warnings, 82 subtests; Game Monitor/Bridge, Executor, Application integration, INT-006 PNG audit, Windows portable build/startup smoke-test SUCCESS; optional algorithm benchmarks SKIPPED. Capsule benchmark artifact опубликован отдельно |

**Важно:** PASS workflow означает успешное выполнение перечисленных jobs. Если внутри job отдельный evidence gate (например PNG acceptance) завершился FAIL, это должно быть явно указано; CI PASS не превращает rejected capture в accepted.

### 7.3. Что не запускалось в обязательном CI

- Длительный Stage 5/7/8 algorithm benchmark job по умолчанию SKIPPED.
- Live game drawing не выполняется GitHub Actions и не подтверждается успешной сборкой.
- Capsule benchmark — отдельный offline script/job step, не путать с optional algorithm-benchmarks job.
- Отсутствие PR-triggered workflow run в connector result не доказывает отсутствие push-triggered run.

## 8. Известные FAIL / BLOCKED / ограничения

| Объект | Статус | Причина / следующий gate |
|---|---|---|
| FILL-001 initial full fill | BLOCKED | Quota exhausted at 5999 before final 3 strokes; full-drawing CHALK unknown |
| FILL-001-RS capture | REJECTED | Coverage 98.430600% < 99%; leakage 11 > 0 |
| FILL-001-RS 45-task matrix | BLOCKED | Не пройден single-task live preflight; не запускать |
| Deployed Egret renderer identity/transform | UNKNOWN | Требуется подтвердить deployed runtime/version, global transform, screen/canvas mapping |
| Capsule model vs real renderer | NOT VALIDATED | Offline masks/oracle не являются renderer reference |
| Capsule planner integration | NOT RUN | Требует отдельного offline renderer acceptance и разрешения |
| Universal sampling/CHALK model | NOT ESTABLISHED | Различия геометрии, sampling, delays и повторного покрытия требуют независимой валидации |
| Production CHALK estimator/defaults | NOT APPROVED | Не делать выводов из одной серии; safety margin/eligibility задаются профильными validation reports |
| Local working tree status | UNAVAILABLE | GitHub API не предоставляет локальный `git status` |

## 9. Индекс первичных отчётов

### CHALK / brush
- [CHALK_G3_RESULTS_2026-11-02.md](CHALK_G3_RESULTS_2026-11-02.md)
- [CHALK_G3_PARTIAL_RESULTS_2026-11-02.md](CHALK_G3_PARTIAL_RESULTS_2026-11-02.md)
- [CHALK_G3_VISUAL_QUALITY_AUDIT_2026-11-02.md](CHALK_G3_VISUAL_QUALITY_AUDIT_2026-11-02.md)
- [CHALK_RADIUS_MATRIX_RESULTS.md](CHALK_RADIUS_MATRIX_RESULTS.md)
- [CHALK_GEOMETRY_MATRIX_G1_RESULTS.md](CHALK_GEOMETRY_MATRIX_G1_RESULTS.md)
- [CHALK_GEOMETRY_MATRIX_G2_RESULTS.md](CHALK_GEOMETRY_MATRIX_G2_RESULTS.md)
- [CHALK_PRELIMINARY_SEGMENTED_MODEL_2026-11-02.md](CHALK_PRELIMINARY_SEGMENTED_MODEL_2026-11-02.md)
- [CHALK_INT006_V1_V5_RESULTS_2026-11-02.md](CHALK_INT006_V1_V5_RESULTS_2026-11-02.md)
- [CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md](CHALK_INT006_FOLLOWUP_RESULTS_2026-11-02.md)
- [CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md](CHALK_INT006_OFFICIAL_VALIDATION_RESULTS_2026-11-03.md)
- [CHALK_INT006_PNG_SCREENING_2026-11-02.md](CHALK_INT006_PNG_SCREENING_2026-11-02.md)
- [CHALK_INT006_PIXEL_AUDIT_2026-11-02.md](CHALK_INT006_PIXEL_AUDIT_2026-11-02.md)
- [CHALK_INT006R_LIVE_RESULTS_2026-11-03.md](CHALK_INT006R_LIVE_RESULTS_2026-11-03.md)
- [CHALK_INT006R_SOFTWARE_GATE_RESULTS_2026-11-03.md](CHALK_INT006R_SOFTWARE_GATE_RESULTS_2026-11-03.md)
- [CHALK_INT006R_VISUAL_AUDIT_2026-11-03.md](CHALK_INT006R_VISUAL_AUDIT_2026-11-03.md)

### FILL-001
- [CHALK_FILL001_PREFLIGHT_POSTMORTEM_2026-11-04.md](CHALK_FILL001_PREFLIGHT_POSTMORTEM_2026-11-04.md)
- [CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md](CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md)
- [CHALK_FILL001_RS_STATIC_SWEEP_2026-11-04.md](CHALK_FILL001_RS_STATIC_SWEEP_2026-11-04.md)
- [CHALK_FILL001_AUTODRAW_INTEGRATION_AUDIT_2026-11-03.md](CHALK_FILL001_AUTODRAW_INTEGRATION_AUDIT_2026-11-03.md)

### Architecture / tests / automation
- [TESTS_AND_CI_MAP.md](TESTS_AND_CI_MAP.md)
- [BRUSH_TEST_AUTOMATION_VISION.md](BRUSH_TEST_AUTOMATION_VISION.md)
- [BRUSH_MODULE_QUICK_INDEX.md](BRUSH_MODULE_QUICK_INDEX.md)
- [GAME_MONITOR_BRIDGE_REFERENCE.md](GAME_MONITOR_BRIDGE_REFERENCE.md)
- [CHALK_TEST_BLOCKS_DESIGN.md](CHALK_TEST_BLOCKS_DESIGN.md)
- [CHALK_INT006_FROZEN_PREDICTIONS_AND_ANALYZER_2026-11-02.md](CHALK_INT006_FROZEN_PREDICTIONS_AND_ANALYZER_2026-11-02.md)
- [CHALK_GAME_ENGINE_POINT_COST_AND_BRUSH_WIDTH_2026-11-03.md](CHALK_GAME_ENGINE_POINT_COST_AND_BRUSH_WIDTH_2026-11-03.md)

## 10. Правило обновления реестра

После каждого значимого теста/эксперимента/CI:
1. Сначала сохранить первичные данные и неизменяемые идентификаторы: experiment ID, block ID, run ID, commit SHA, workflow run, artifact ID, plan/mask hashes.
2. Обновить соответствующий первичный отчёт; не подменять raw evidence агрегатом.
3. Добавить или обновить запись в этом `TEST_RESULTS.md`: цель, условия, версия/commit, статус, фактический результат, критерии, ссылки на raw evidence, ограничения и следующий gate.
4. В `PROJECT_STATUS.md`, `TASKS.md`, `ROADMAP.md`, `WORK_LOG.md` и `CHANGELOG.md` оставлять короткий статус и ссылку на этот реестр вместо копирования численных результатов.
5. Сохранять FAIL, CANCELLED, SKIPPED и BLOCKED наряду с PASS.
6. Не менять frozen criteria, thresholds, masks, plans или defaults после просмотра результата без отдельного решения и новой версии эксперимента.

**Этот реестр не заменяет первичные отчёты и данные. Он является единой точкой навигации, сводки и актуального статуса результатов тестирования.**

## 2026-11-04 — Game Monitor runtime renderer diagnostics

**Commit:** `b2d467de6d7fb247d9014e47b1b58da782ff6d68`

- `node --check AutoDraw_Stage20/source/game_monitor/game_monitor.js` — PASS.
- `node --test AutoDraw_Stage20/source/game_monitor/tests/game_monitor.test.js` — PASS, 18/18 tests, включая runtime renderer snapshot, stage/client corner mapping и graceful no-runtime case.
- Локальный WebSocket smoke server test — PASS.
- GitHub Actions run [41896024383](https://github.com/Kiddos19882/AutoDraw/actions/runs/41896024383): Game Monitor and bridge tests — SUCCESS; Executor regression tests — SUCCESS; Application integration tests — SUCCESS; Preparation/G3 matrix tests — SUCCESS (включая capsule broad-phase benchmark и FILL-001-RS static sweep); Windows portable build/startup smoke-test — SUCCESS; INT-006 pixel-level PNG geometry audit, independent CHALK validation и INT006R validation — SUCCESS; optional algorithm benchmarks — SKIPPED. Полный workflow run завершился SUCCESS.
- Это программные проверки mock/runtime diagnostics, не live browser evidence. Реальный renderMode, screen transform, brush footprint и pixel equivalence ещё не получены.

## 2026-11-05 — paired accepted-point offline replay (live/offline comparison pending)

**Live experiment:** `d47cc0a5520044c7abfd0352a4f93ca8`  
**Run/session:** `16aec62c-9e54-44e7-8691-9df79b19161d` / `d357b6ee-5617-4e07-9011-7eba7ccb6c0f`  
**Renderer manifest:** `data/renderer_result/egret-5.4.1-renderer-reference-manifest.json` (schema v2).  
**Renderer PNGs:** `live-accepted-points-width-10-source-reference.png` (1392×732), `live-accepted-points-width-10-masked-board-reference.png` (1380×720), `live-accepted-points-width-10-webgl-board-reference.png` (1380×720).  
**Live image:** experiment `after_draw-board.png` (674×355).

- Manifest fixture `live-accepted-points` has the same `sourceRunId`, 138 accepted points, mode `smooth`, lineWidth=10; actual `com.magnetjoy.pet.ui.board.BoardPane` and manual path transcription agree exactly. Egret WebGLRenderer output and Canvas2D masked-board reference agree exactly: `equal=true`, `differingPixels=0`, `maxChannelDifference=0`.
- Live plan maps logical 460×240 board to ROI 674×355 using `scale_x=1.4630434782608697`, `scale_y=1.475`, inclusive logical max→last screen pixel. Experiment visual ROI heuristic reports `x=18,y=166,width=609,height=23`, 8947 changed pixels.
- Visual inspection shows a single continuous horizontal line whose position/extent are consistent with the replay. This is a qualitative consistency check only; no numerical live/offline pixel diff, IoU, residual map or alpha-normalized comparison has been completed.
- The manifest's runtimeProfile references `renderer_snapshot_2026-11-04.json`; it is not an `inspect()` snapshot captured in the live session 05.11. `experiment.json` confirms session binding, board dimensions, observed brush radius and telemetry, but does not include per-run renderer inspect snapshot.

**Status:** OFFLINE_REPLAY_DONE / LIVE_PNG_PIXEL_COMPARISON_PENDING.  
**Evidence level:** E4 for live run and exact CHALK=138; E3/E2 for offline harness internal renderer comparisons; no E5 live/offline pixel equivalence claim.  
**CI:** data/manifest commit `ad03a0b5b03cf76f6fa11f06047d52106317c8c7` and follow-up documentation commit `40f1603075503c9aa12c964af52e9aa2a82635e6` have empty combined status; do not claim CI PASS for these commits. Full CI run `41933396072` passed on earlier source/test HEAD `f6df3f9`.  
**Next gate:** independent quantitative comparison of live screenshot and offline WebGL PNG after explicit ROI transform and background/alpha normalization. No repeat live stroke required; FILL-001-RS 45-cell matrix remains BLOCKED.


## 2026-11-05 — independent BoardPane screen transform (CI pending)

- Добавлен `source/preparation/renderer_geometry.py`: same-run Monitor `screenX/boardX` fit, стабильность `screen-client` offset, inspect CSS matrix validation, vertical-scale caveat и affine mapping source-raster→ROI.
- Добавлены `source/preparation/tests/test_renderer_geometry.py`: положительный сценарий, unstable offset rejection, CSS skew rejection.
- `tests/compare_live_renderer_reference.py` теперь дополнительно сохраняет `comparison-report-independent-transform.json`, expected alpha и overlay; не выполняет post-hoc registration для нового transform.
- Workflow `geometry-tests.yml` передаёт `screen_geometry_audit.json`. Фактический результат этого CI ещё не проверен; до него comparison status — pending.


## 2026-11-05 — independent live/offline renderer transform comparison

**Workflow:** [41963498086](https://github.com/Kiddos19882/AutoDraw/actions/runs/41963498086), commit `1b16b51e42ba0c61a0fbc547179ca5a9b3864b54`. Job `INT-006 pixel-level PNG geometry audit` completed SUCCESS; preparation/G3, Game Monitor/Bridge, Executor regression, Application integration and Egret browser reference jobs completed SUCCESS. Windows portable build/startup smoke-test also completed SUCCESS. Optional algorithm benchmarks SKIPPED.

**Independent transform:** same-run Monitor X fit + user inspect CSS Y transform; no post-hoc registration. Origin `(497.954055,267.860048)`, scale `(1.461204822,1.463334)`, source-raster→ROI matrix `[[0.487068274,0,1.954055],[0,0.487778,2.860048]]`.

| Alpha threshold | IoU | Precision | Recall | Symmetric difference |
|---:|---:|---:|---:|---:|
| 1 | 0.998883 | 0.999665 | 0.999218 | 10 px |
| 24 | 0.998994 | 0.999218 | 0.999776 | 9 px |
| 64 | 0.998547 | 0.998547 | 1.000000 | 13 px |
| 128 | 0.997653 | 0.997653 | 1.000000 | 21 px |

At alpha 24, live and expected bbox both `(21,170,599,15)`. Old frozen transform at alpha24: IoU `0.763153`, precision `0.865862`, recall `0.865475`, symmetric difference `2404 px`. The independent transform is slightly better than the previous post-hoc `(+1,+2)` diagnostic (IoU `0.998883`, 10 px), without fitting translation to the masks.

**Limitations:** vertical scale is inspect-derived because the live stroke is horizontal-only; inspect snapshot is user-attested same-screen but has no run/session timestamp; alpha thresholds 192/254 are more sensitive to antialiasing and lower IoU. No acceptance threshold has been declared. Status remains `ANALYZED_EXPLORATORY_NO_ACCEPTANCE_THRESHOLD`.

Artifact: `autodraw-paired-renderer-png-comparison`, ID `13386122895`.


**Final CI status:** workflow `41963498086` — `SUCCESS`. Required jobs: Egret browser reference, Preparation/G3, Game Monitor/Bridge, Executor regression, Application integration, Windows portable build/startup smoke-test, INT-006 PNG geometry audit — all SUCCESS. Optional algorithm benchmarks — SKIPPED. The workflow validates code/test/workflow commit `1b16b51e42ba0c61a0fbc547179ca5a9b3864b54`; subsequent branch commits in this audit sequence are documentation-only.


## 2026-11-05 — Monitor/Bridge renderer geometry snapshot (CI pending)

- Game Monitor 0.2.3: test for axis-aligned rect fallback without `getBoxQuads()`, four client corners, and raw window geometry.
- Bridge server: RunRecorder test for geometry at run start/update/end; websocket integration test for session_start + renderer_geometry persistence in session schema v2.
- Bridge client: initial rendererGeometry snapshot and debounced updates on resize/scroll/orientation/fullscreen/visualViewport; listener cleanup on disconnect.
- No production AutoDraw profile consumption or live gameplay validation yet. Awaiting CI run triggered by this source/test update.


**Monitor/Bridge geometry implementation test result:** workflow `41964932479`, job `Game Monitor and bridge tests` SUCCESS. `game_monitor.test.js` — 21 passed / 0 failed; `test_websocket_smoke_server.py` — 22 passed / 0 failed. New axis-aligned client geometry fallback, raw window metrics, run-bound geometry snapshots and session schema v2 persistence are covered. Preparation/G3 tests and full workflow still pending.


**Preparation/G3 suite result for geometry snapshot commit:** workflow `41964932479`, job `Preparation and G3 matrix tests` SUCCESS; `pytest -q -ra tests` — 852 passed, 24 warnings, 82 subtests passed in 59.71s. Includes `test_renderer_geometry.py`.

**FILL-001 evidence in same job:** committed PNG audit output reports coverage `98.430600%`, leakage `11`, status `failed`; static spacing sweep workflow step reports `passed`, 15 cells, 2238 candidates, 62 accepted candidates. The latter is not a substitute for the committed PNG quality gate; FILL-001 remains blocked.


**Full CI result for Monitor/Bridge geometry snapshot implementation:** workflow [41964932479](https://github.com/Kiddos19882/AutoDraw/actions/runs/41964932479), code/test commit `baf7e3f73bebe4cd780e93723bf6b4ea231a7b4b` — SUCCESS. Preparation/G3: 852 passed, 24 warnings, 82 subtests. Game Monitor: 21 passed. Bridge/WebSocket: 22 passed. Executor regression, Application integration, Egret browser reference, Windows portable build/startup smoke-test, INT-006 PNG audit: SUCCESS. Optional algorithm benchmarks: SKIPPED.

**FILL-001-RS static sweep artifact:** `autodraw-fill001-rs-static-sweep` ID `13386973590`; 15 cells (3 shapes×5 radii), 2238 candidate plans, 62 accepted candidates; each cell has a selected offline candidate meeting coverage≥0.99 and leakage=0. This is OpenCV raster simulation and estimated sampling points, not exact CHALK or game renderer validation.

**Separate committed PNG quality gate:** coverage `98.430600%`, leakage `11`, status `failed`; therefore FILL-001 remains blocked despite the static sweep step succeeding.


## 2026-11-05 — AutoDraw geometry reader/UI diagnostics (CI pending)

- `test_brush_radius_feedback.py`: active Bridge geometry reader returns client-space corners and explicitly denies desktop/executor readiness; stale and closed sessions are rejected.
- `test_brush_behavior_test_ui.py`: Game Monitor report summary preserves BoardPane client corners, mapping method, window geometry and update count without copying raw snapshots or claiming screen mapping.
- Brush Behavior tab displays current BoardPane geometry diagnostics and retains manual calibration for executor placement.
- Awaiting CI for reader/UI changes.


## 2026-11-05 — latest geometry pipeline CI and INT006R / CHALK validation status

**Workflow:** [41966023670](https://github.com/Kiddos19882/AutoDraw/actions/runs/41966023670), successful on code/test commit `7969134a1e1d545a99f985e8d637a7776823411f`.

- Preparation/G3: 855 passed, 24 warnings, 82 subtests passed. Game Monitor: 21 JS tests. Bridge/WebSocket: 22 tests. Executor, Application integration, Egret CanvasRenderer browser reference, Windows portable build/startup smoke-test and INT-006 analysis jobs: SUCCESS. Optional algorithm benchmarks: SKIPPED.
- FILL-001 committed PNG quality gate remains FAIL: coverage=98.430600%, leakage=11. FILL-001-RS static sweep is separate: 15 cells, 2,238 candidates, 62 accepted candidates; offline-only, not exact CHALK/live renderer evidence.
- INT006R analyzer: 45/45 accepted, 0 missing/rejected; visual evidence complete. Official manual visual audit is COMPLETE WITH GEOMETRY-SPECIFIC LIMITATIONS: radius 1 D2 seam gap; radius 30 merges short details in D4; radius 10 preserves both in the tested matrix. Exact CHALK means: 67.40 / 67.67 / 67.80 for radii 1 / 10 / 30.
- Frozen INT-006 model validation: 45/45 accepted. Aggregated profile metrics (15 runs/profile): P0 MAE=2.882, RMSE=3.189, MAPE=3.484%, max underprediction=0.99; P1 MAE=0.657, RMSE=0.838, MAPE=1.178%, max underprediction=0.92; P2 MAE=0.685, RMSE=0.854, MAPE=1.741%, max underprediction=1.82. Safety margin remains NOT_ESTABLISHED; production eligibility NOT_VALIDATED.
- Artifact IDs: INT-006 CHALK validation `13387976546`; INT006R live validation `13387682524`; INT006R visual review source `13387951744`; paired renderer comparison `13386869712`; FILL-001-RS static sweep `13387727239`.
- Subsequent workflow/config commit `fb853547d74a70582ab1e4731d55763367b8ceb8` adds paired full-screen screenshots to the next diagnostic artifact. No CI run for that commit was available at this update; run 41966023670 does not validate it.


## 2026-11-05 — screenshot-derived BoardPane bounds and renderer audit

**CI:** [41971869707](https://github.com/Kiddos19882/AutoDraw/actions/runs/41971869707), commit `b9c2e2a194f840c844c1e8b0877a6c4c54ddc1df`, SUCCESS.

- Preparation/G3: 859 passed, 24 warnings, 82 subtests passed (includes four new screenshot-bound/transform tests).
- Application integration: 41 passed / 1 skipped / 3 subtests; additional groups 24 passed / 2 subtests and 12 passed. Game Monitor/Bridge job SUCCESS (WebSocket smoke: 22 passed). Executor regression, Egret CanvasRenderer browser reference, INT-006 analysis and Windows portable build/startup smoke-test: SUCCESS. Optional algorithm benchmarks: SKIPPED.
- New full-screen board-bound detector: same before/after bbox `(498,268,672,351)`, board color RGB `(238,238,238)`, tolerance 4; component fill fractions `0.999788 / 0.961861`.
- New independent transform: origin `(497.954055,268.0)`, scale `(1.461204822,1.4625)`; X fit from 272 same-run samples, RMSE 0.424 px; Y same-run sample residual 0.0375 px; inspect cross-check differences under 0.14 px / 0.057% scale.
- At alpha24 old ROI transform: IoU 0.763153, symmetric difference 2,404 px. Screenshot-derived Y + Monitor X: IoU 0.998882, precision 0.999106, recall 0.999776, symmetric difference 10 px; bbox exact match `(21,170,599,15)`. No post-hoc registration.
- Threshold sensitivity: alpha1 IoU 0.998771 / 11 px; alpha64 0.998435 / 14 px; alpha128 0.997764 / 20 px; alpha192/254 lower due antialiasing/coverage. No acceptance threshold was defined; report remains exploratory.
- FILL-001 committed PNG quality gate remains FAIL: coverage 98.430600%, leakage 11. FILL-001-RS sweep remains offline-only.
- Artifact IDs: paired renderer `13389883231`; INT-006 PNG analysis `13389958144`; INT-006 CHALK validation `13389908245`; INT006R live validation `13390795994`; INT006R visual source `13390526598`; FILL-001-RS sweep `13390271857`; portable build `13390167082`.
- The audit helper/tests and full-screen artifact packaging do not change production renderer/planner/calibration/executor. No live game experiment was launched.

## 2026-11-05 — multi-axis transform and paired renderer scenarios

**Code/test HEAD:** `f9387d0d1c04375c1b8284d01ebef75ff704418b`  
**GitHub Actions:** [41975359740](https://github.com/Kiddos19882/AutoDraw/actions/runs/41975359740) — **SUCCESS**.

- Preparation/G3 tests: SUCCESS; includes synthetic vertical and diagonal transform fits and paired scenario plan checks.
- Application integration tests: SUCCESS; horizontal, vertical and diagonal paired-renderer executor handoff.
- Game Monitor/Bridge tests: SUCCESS.
- Executor regression tests: SUCCESS.
- Egret CanvasRenderer browser reference: SUCCESS.
- INT-006 pixel-level PNG audit, independent CHALK prediction validation, INT006R radius × geometry validation and visual-review packaging: SUCCESS.
- Windows portable build and startup smoke-test: SUCCESS; artifact `autodraw-g3-preflight-build`, ID `13392211048`.
- Optional algorithm benchmarks: SKIPPED.
- The earlier UI-scenario run `41975187040` failed because `PAIRED_RENDERER_TEST_CASE_IDS` was imported locally after its first use. The import was moved before the guard; the corrected run above passed.
- No live vertical/diagonal game captures were executed. CI validates code, synthetic geometry and packaging, not runtime geometry on the user's screen.


## 2026-11-05 — final multi-axis audit CI

**HEAD:** `32c6828c69930ee8fe5f22e11a91454425354506`  
**GitHub Actions:** [41976515362](https://github.com/Kiddos19882/AutoDraw/actions/runs/41976515362) — **SUCCESS**.

- Preparation/G3: SUCCESS, including multi-axis transform and paired scenario tests.
- Application integration, Game Monitor/Bridge, Executor regression and Egret CanvasRenderer: SUCCESS.
- Scenario-aware paired renderer comparison and INT-006/INT006R analyses: SUCCESS.
- Windows portable build and startup smoke-test: SUCCESS; artifact `autodraw-g3-preflight-build`, ID `13391394936`.
- Optional algorithm benchmarks: SKIPPED.
- Live vertical/diagonal captures were not run; CI success does not establish their runtime pixel equivalence.

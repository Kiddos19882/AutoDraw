## 2026-11-05 — привязка offline renderer к профилю последнего live run

**Scope:** исправление offline replay harness и инструкции; без запуска renderer/live game.

- Проверено состояние ветки: `feature/image-geometry-optimization`, исходный HEAD перед работой `3ab7dcaca7672a7256076dece053b7977f72d9a5`; просмотрены последние 20 коммитов и обязательные управляющие документы/регламенты.
- Установлено: `game_renderer_reference.js` жёстко записывал в manifest snapshot от 2026-11-04 (Stage 1672×600, backing 5016×1800), хотя latest paired-run geometry использует Stage 1314×600, backing 3942×1800, screen 1920×1080 и CSS matrix 0.487062/0.487778.
- Исправлено: runtime profile для live replay теперь строится из `renderer_geometry_at_start/end` того же полного Game Monitor report; несовпадающие/отсутствующие snapshots и неподдерживаемые renderer settings отклоняются.
- Сохранено: offscreen BoardPane 460×240, rasterScale 3, WebGL output 1380×720. Stage/screen CSS transform записывается как профиль live session, но не применяется повторно к локальному raster.
- HTML-инструкция требует полный `monitor_report.json`. Изменены два файла harness.
- Commits: `23ed8cf2cce051eeda87ad8b630604ae96889608`, `d6343adaf2db05f321b48ef0432b897277ff0193`.
- Проверки: source-level consistency reviewed; offline renderer, unit suite and CI не запускались. Новых live experiments не было.
- Следующий шаг — пользовательский offline rerun с последними vertical/diagonal monitor reports и последующая проверка новых артефактов.

## 2026-11-05 — review of first vertical/diagonal captures (evidence commit e6b771e)

**Scope:** remote repository review and documentation synchronization only; no code/test/config/workflow changes and no new live experiment by the reviewer.

- Confirmed remote branch `feature/image-geometry-optimization` HEAD `e6b771ed67201625884c6ce778fa355f1ab9b873`; it is one commit after `6fb868f`. The commit adds 22 result artifacts only. `master` remains at the previously known HEAD; GitHub API does not expose local `git status`.
- Reviewed both experiment manifests, raw Game Monitor reports, brush plans, comparison reports, offline manifests and PNG outputs. Vertical exact CHALK=71; diagonal exact CHALK=161; both radius 10, one stroke, zero Monitor/Bridge dropped/error/sequence counters.
- Recomputed same-run Monitor fits: vertical Y max residual 0.723222 px; diagonal X/Y max residuals 0.730129/0.739053 px. Client-to-screen offsets are stable (0,163) px; geometry snapshots are unchanged start/end.
- Existing alpha24 comparisons use the frozen 674×355 ROI transform and remain exploratory (vertical IoU 0.870044; diagonal 0.873071); neither report contains an independent-transform comparison. Best-translation overlays are diagnostic only.
- Calibration profile records 1920×1080, Windows scale 100%, browser zoom 100%, Firefox 159; Monitor reports DPR=1 and visualViewportScale=1. Windows scale is sourced from the profile calibrated earlier on the same date, not a per-run Windows display API.
- Updated current status, backlog, roadmap, work log and TEST_RESULTS. Kept raw experiment evidence and frozen acceptance thresholds unchanged.
- Next offline step: derive same-run screenshot BoardPane bounds and rerun comparison using the independent per-axis transform. No additional live run should be needed before this replay.
## 2026-11-05 — закреплены границы локального доступа и автоматизация live-тестов

**Объём:** только документация, ветка `feature/image-geometry-optimization`.

- В начале README и индекса документации добавлено заметное правило: локальная программа, игровая сессия и доска доступны только пользователю; локальный `git status` на ПК также может подтвердить только пользователь.
- В AI_WORK_GUIDE и EVIDENCE_AND_VALIDATION уточнено различие между удалённой проверкой GitHub и локальным состоянием ПК, а также требования к доказательствам live-тестов.
- В ENGINEERING_INVARIANTS приняты INV-010 (границы локального доступа) и INV-011 (максимальная автоматизация тестов с игровой доской).
- DEC-024 фиксирует постоянное решение: повторно использовать существующие средства автоматизации, создавать недостающие условия, автоматизировать сбор данных/точный CHALK/аудит/отчётность и минимизировать ручные шаги пользователя.

**Не выполнялось:** локальный `git status`, запуск AutoDraw, live-тесты с игровой доской. Код, тесты и workflow не менялись.


## 2026-11-05 — formal renderer acceptance tooling

- Reviewed the active multi-axis code, capture contract, historical horizontal baseline, same-run screenshots and the predeclared TASKS.md thresholds.
- Added fail-closed per-run evidence/geometry/pixel validation and a separate three-repeat series aggregator; added unit tests and CI wiring for the existing horizontal baseline audit.
- Kept vertical/diagonal live work blocked on actual user-screen captures. No live experiment, production renderer/planner/estimator/default, calibration profile, or executor behavior was changed.
- CI verification and post-run documentation sync remain pending.


## 2026-11-05 — Bridge telemetry run provenance and CI test corrections

- Implemented paired-scenario input telemetry opt-in in Bridge; ordinary Bridge sessions leave Monitor telemetry unchanged. The Bridge restores the user's pre-existing state on disconnect.
- Added `bridge_configuration` to session.json and `bridge_configuration_at_start` to run JSON.
- Browser lifecycle tests passed 4/4. First Python CI attempt failed with a wrong JS-string assertion; second attempt failed because the provenance test omitted `json` and `RunRecorder` imports. Both failed runs are preserved in TEST_RESULTS.
- Corrected imports in commit `58ebdda7`; CI rerun 41994624425 completed SUCCESS. No live game experiment was run.

## 2026-11-05 — complete CI verification and artifact review

- Full CI run 41994624425 on code/test commit 58ebdda7 completed SUCCESS across all required jobs; optional algorithm benchmarks skipped.
- Bridge input telemetry tests: browser lifecycle 4/4, Python WebSocket/snippet/provenance suite 31 passed.
- Preparation/G3: 880 passed, 24 warnings, 82 subtests; capsule broad-phase benchmark and FILL-001-RS static sweep reproduced and uploaded.
- Formal horizontal renderer per-run acceptance passed again; artifact 13399663414. Vertical/diagonal live series remains uncollected.
- V1–V5 pixel analyzer validated 90/90 captures (10×9). INT-006 and INT006R each accepted 45/45; safety margin and production eligibility remain unvalidated; INT006R package awaits manual visual review.
- Windows portable build/startup smoke-test passed; artifact 13399627749, 646,950,501 bytes.
- CI artifacts were downloaded and inspected. No new live run, local app launch, raw evidence mutation, or production drawing default change was performed.


## 2026-11-05 — исправление same-run geometry для multi-axis offline/live renderer

Scope: code, tests and CI only in feature/image-geometry-optimization; no real game experiment.

- Added build_same_run_geometry_audit_input() to normalize the exact renderer_geometry_at_start stored in Game Monitor. It rejects run/session/experiment mismatch, changed start/end geometry, geometry updates/overflow, unsupported renderer mode, unexpected logical dimensions, and screen/PNG dimension mismatch.
- Added verified 1:1 screen-pixel mapping when same-run window.screen dimensions match both experiment phase metadata and actual full-screen PNG dimensions, with DPR and visualViewportScale equal to 1. Legacy audits with a calibrated 100% Windows scale remain supported.
- Added --same-run-geometry to the paired comparison CLI. The generated audit is written to the output directory and used with same-run full-screen before/after captures.
- Added fail-closed unit tests for valid evidence, run mismatch, changed geometry, geometry updates, screen mismatch, and pixel mapping without a separate OS-scale profile.
- CI now replays the stored vertical and diagonal captures. Frozen-plan metrics remain diagnostic; independent geometry becomes authoritative in the main comparison report.
- Commits: d26ed86 (adapter/tests/CI replay), 57638f2 (audit JSON newline), 1cd0d61 (authoritative report fields).
- Current CI run: 42083576282, pending at documentation time. Game Monitor/Bridge, Egret browser reference, executor and integration jobs have reported SUCCESS; preparation/G3 is still running.
- No live game run, AutoDraw launch, production planner/renderer/executor change or local workstation action was performed.

## 2026-11-05 — formal renderer comparison uses exact BoardPane crop

**Scope:** renderer comparison code and regression tests on `feature/image-geometry-optimization`; no live experiment.

- Reviewed CI 42087496092 artifacts. The same-run transform was valid, but the formal comparison cropped to calibrated ROI `(496,265,674,355)` instead of detected BoardPane bounds `(498,268,672,351)`.
- Identified 17 changed pixels on the ROI's bottom margin outside the board; these caused false bbox/symmetric-difference failures despite the actual board mask matching closely.
- Added `crop_mask_to_board_bounds()` with fail-closed validation. Formal observed/expected masks now use exact same-run BoardPane bounds; ROI-margin deltas are retained separately as diagnostic evidence.
- Added regression tests for exact board crop, outside-board isolation and invalid bounds.
- Commit: `1ac3d9390c56072730017e073cf80dd69c448f8b`.
- CI run `42091370065` is pending. The existing horizontal artifact recalculated over exact BoardPane bounds gives IoU 0.999218, precision 0.999553, recall 0.999665, 7 symmetric-difference pixels and identical bounding boxes; this is an offline re-analysis, not a new CI result.
- No live game run, local app launch, production planner/executor change, master modification or local git status check was performed.

## 2026-11-05 — BoardPane crop diagnostics consistency

- Follow-up review found that OpenCV diagnostic alpha masks and the overlay image also needed to use the exact BoardPane crop after the formal observed/expected masks were narrowed. Without this, diagnostic arrays would have mismatched dimensions.
- Cropped OpenCV alpha diagnostics to the same BoardPane bounds and sized the overlay from the board-only observed mask.
- Commit: `e73506db2a2cfd55bbb0ea4c4a1616648b7f0065`; CI run `42091800785` pending.


## 2026-11-05 — correction to negative BoardPane bounds test fixture

- CI 42091800785 ran 887 tests successfully and found one failing assertion in the newly added negative-bounds test. The test fixture used x=497 while ROI started at x=496, so the board bounds were correctly considered contained; the test expectation was wrong.
- Corrected the fixture to x=495, genuinely outside the ROI. Production crop implementation was not changed.
- Commit: `cfdc49e86809a7b62c0271f0574473a48403e20b`; CI run `42092259450` queued.


## 2026-11-05 — ROI-local OpenCV diagnostic mask correction

- CI 42092259450 passed preparation/G3: 888 passed, 24 warnings, 82 subtests. The renderer job then failed before formal metrics because `alpha_opencv` is generated in ROI-local dimensions, while the crop helper was given absolute screenshot BoardPane coordinates.
- Converted absolute BoardPane bounds to ROI-local coordinates for the OpenCV diagnostic crop; full-screen observed and browser-composited masks continue using absolute screen coordinates.
- Added a regression test for ROI-local mask cropping. Commits: `f1b5b608de5b61c171b8e90640f83898bbd0d5b4`, `221e5240152c9888b564076e649b3f71366c1664`.
- CI run `42093239480` pending. No live game run or production executor change.


## 2026-11-05 — Firefox compositor parity

- CI 42093239480 confirmed horizontal PASS_PER_RUN after exact BoardPane cropping. Vertical and diagonal remained REJECTED_PER_RUN with IoU 0.938863 and 0.953976; provenance and geometry gates passed.
- Root cause candidate was identified in the comparison harness: live renderer manifest reports Firefox 159, while the offline CSS compositor used Edge/Chromium. The different browser raster/compositing engines make vertical/diagonal pixel differences non-diagnostic for the game renderer.
- Replaced Edge image overlay with a transparent Canvas2D overlay captured by Firefox headless. The compositor now requires the same browser family and matching major version from the same-session manifest.
- Commits: `cd12cac3bad2af9aa7df9030f69d2880ec160a74`, `bc787b8f06c3609c7f294beb0cb3ea4b6e1ae5ef`. CI run `42096244252` pending.
- No live game experiment or production executor handoff.


## 2026-11-05 — correction to horizontal acceptance wording and Firefox CI result

- Corrected the previous status wording: the horizontal metrics IoU 0.999218, precision 0.999553, recall 0.999665, 7 differing pixels were calculated offline from a stored artifact after BoardPane crop. They were not emitted as a CI `PASS_PER_RUN` in run 42093239480. That workflow formally replayed vertical and diagonal only; both were rejected.
- Latest [CI 42096244252](https://github.com/Kiddos19882/AutoDraw/actions/runs/42096244252) completed FAILURE. Executor, Game Monitor/Bridge, Egret renderer harness, preparation/G3 matrix tests, application integration, portable build and startup smoke-test jobs succeeded. INT-006 failed on the first horizontal Firefox compositor comparison: IoU=0, precision=0, recall=0, 8946 symmetric-difference pixels. Capture and transform checks were empty (passed); renderer checks failed. Vertical/diagonal replay was skipped after the horizontal gate failed.
- Firefox major-version detection ran successfully, but current evidence does not explain why the headless Firefox expected mask did not overlap the observed live delta. Treat as a compositor harness defect/unknown until the generated PNG diagnostics are reviewed; do not infer a game renderer defect.
- No formal horizontal, vertical or diagonal PASS_PER_RUN is currently established by the latest CI evidence. No live game test or executor handoff was performed.


## 2026-11-06 — independent same-run multi-axis replay and compositor investigation

**Scope:** comparison harness, regression test, CI workflow and project documentation on feature/image-geometry-optimization; no production drawing code and no live game experiment.

- Начальная точка продолжения: code/test HEAD c0f36ac49e4b66cf0fcd27d362154b71a917c367. Проверены управляющие документы, README/docs index, engineering invariants, evidence/experiment standards, профильные исходники и сохранённые captures. GitHub API не предоставляет локальный git status.
- CI run 42109890747 после independent transform fix завершился FAILURE: горизонтальный compositor overlay был пустым (expected pixels=0); capture/transform evidence не показывали mismatch.
- В commit 7c1a1fb704a0393509b7ff237048006dbbe6caf7 добавлен eager static image compositor, empty-mask fail-closed guard, regression coverage и opt-in Windows portable build workflow input. CSS image compositor давал browser-resampling mismatch, поэтому этот способ не оставлен как финальный.
- В commit b07c636fa4b4ce28329cfb74f468634a46751ac1 overlay возвращён к Canvas2D canvas; source image загружается eager/sync, drawImage выполняется синхронно в onload до Firefox screenshot. Добавлен тест HTML contract.
- Windows portable build/startup smoke-test вынесен из обычного push CI: job выполняется только при manual workflow_dispatch с run_windows_portable_build=true; default=false.
- CI [42113632374](https://github.com/Kiddos19882/AutoDraw/actions/runs/42113632374) завершился FAILURE только на INT-006 vertical/diagonal renderer acceptance. Preparation/G3, Game Monitor/Bridge, Executor, Egret browser reference и Application integration — SUCCESS; optional benchmarks и Windows build — SKIPPED.
- Horizontal formal result: PASS_PER_RUN, IoU=0.999329, precision=0.999329, recall=1.0, symmetric difference=6 px. Vertical: REJECTED_PER_RUN, IoU=0.938405, precision=0.938980, recall=0.999348, difference=302 px. Diagonal: REJECTED_PER_RUN, IoU=0.949646, precision=0.962683, recall=0.985939, difference=554 px. Capture/transform gates passed for all three.
- Downloaded/reviewed paired renderer artifact 13454628828 and Egret reference artifact 13453809141. Vertical/diagonal failures are not explained by capture provenance or the independent board transform.
- Leading hypothesis: compositor skips live Stage-level WebGL texture composition. Same-run geometry records Stage backing 3942×1800, BoardPane local raster 1380×720, board backing origin x≈1022.375/y=216 (fractional X phase 0.375 px), and WebGL texture LINEAR sampling. Direct screen-space Canvas2D overlay may not reproduce this pipeline. Hypothesis only; no post-hoc alignment or threshold adjustment.
- Exact CHALK remains from existing user captures only: vertical=71, diagonal=161. No new live run, no brush/trajectory/sampling/executor changes, no master changes.
- Next step: stage-level WebGL compositor using same-run stage/backing evidence while keeping the screen transform independently derived; rerun existing captures and add tests.



## 2026-11-06 — статический аудит Stage-level WebGL composition

- Проверены branch refs, HEAD, последние 20 коммитов, обязательные управляющие документы и постоянные регламенты. Удалённая рабочая ветка: `feature/image-geometry-optimization`; HEAD перед записью: `f0cfa6268fd39cf91f3d4a9e7e2bf9509763ff48`; master не изменялась. Локальный git status недоступен через GitHub API.
- Повторно изучены `tests/game_renderer_reference.js`, `tests/compare_live_renderer_reference.py` и `gameEngine/mergeEngine_df2e5bc5.js`.
- Подтверждено: reference harness рендерит local 1380×720 WebGL buffer, а comparison script размещает raster в screen CSS space; Stage backing composition не моделируется.
- Подтверждён source pipeline Egret WebGL: GraphicsNode → CanvasRenderBuffer/CanvasRenderer → WebGL texture → drawTexture; texture uses LINEAR min/mag, CLAMP_TO_EDGE и premultiplied alpha.
- Зафиксированы run-bound параметры сохранённых captures: Stage 1314×600, backing 3942×1800, BoardPane local raster 1380×720, backing origin ≈(1022.375,216), canvasScaleX/Y=3.
- Дробная X-фаза 0.375 px и sampling являются правдоподобными факторами, но причинность не доказана. Текущий harness gap подтверждён статическим аудитом.
- Зафиксирован план A–D (WebGL/Canvas2D × exact/rounded origin), метрики и требования к unit/browser tests. Код, тесты и workflow в этой работе не менялись; live game runs не запускались; CHALK не измерялся повторно.
- Предыдущий CI 42113632374 остаётся FAILURE из-за INT-006 vertical/diagonal renderer gates; его результаты не переинтерпретируются как результат нового probe.
- Следующий шаг: реализовать offline Stage-level probe, получить PNG/manifests и сравнить exact WebGL variant с сохранёнными live captures без post-hoc alignment.

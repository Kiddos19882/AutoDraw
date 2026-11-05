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

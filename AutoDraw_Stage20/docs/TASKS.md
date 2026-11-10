# AutoDraw — действующие задачи

## FILL-001 V5 — third live W2 automated CHALK 1701, quality FAIL (2026-11-10)

- [x] Analyze immutable `36e95e4`: Stage6 29/29, 28×10→2, 75.578s, run-bound automated exact `pointCount 1→1702`, CHALK1701; 5 no-point slider drags correctly excluded. Settled PNG saved. This fixes prior V5 binding issue in real E4.
- [x] Apply original perimeter quality policy: coverage 99.368653% PASS, but 2963 leakage pixels (2230 farther than allowed 3 logical px), maximum 48.146794 logical px -> **quality FAIL**, E5 NOT_RUN. No candidate acceptance or production promotion.
- [x] Inspect both original PNGs: browser/game brush cursor sprite visibly changes location between before and settled screenshots; whole-ROI RGB subtraction includes that sprite. Do not erase pixels, alter mask or retroactively mark existing FAIL as PASS.
- [x] Add V5-only pointer parking before future baseline and settled capture (96 px outside ROI; no click; exact counter + Firefox foreground gates) and synthetic fail-closed tests `c1fe1f8`/`1b48fb1`/`0ca2a42`. Original raw PNG and reports preserved.
- [ ] Confirm CI at new code SHA and Markdown audit at docs HEAD; fix any FAIL before live.
- [ ] Next E4 on Windows: new clean-board W2 isolated run with cursor parked before both screenshots; require same-session exact CHALK and fresh settled PNG. Verify whether remaining real perimeter pixels exceed 3 px; do not assume quality PASS. Independent E5 required before W3 comparison.



## FILL-001 V5 — second E4, 3825d57: numeric-type root cause and regression

- [x] Audit full 8133-event Monitor run: 29 paint strokes 28×radius10→2, five zero-consuming slider drags, CHALK source 1→1695=1694, no telemetry errors/drops; early Stage6 post1670 is not final.
- [x] Run real-data CI regression: code `3189f860` **FAIL** because `observed_brush_radii=[1.0,2.0,8.0,10.0,30.0]` are Python `float`, while validator requires exact Python `int`; stale Windows build hypothesis not proven.
- [x] Fix finite integer-valued JSON float radii in `252228c`, preserve strict 29 planned stroke, point delta, zero-delta slider corridor and fail-closed; add malformed/fractional/NaN/bool negative regressions in `6506774`. Separate pre-draw finalizer contract guard also introduced.
- [ ] Verify full current E3 CI on latest code and Markdown integrity on docs HEAD; investigate any FAIL before repeating game.
- [ ] On fresh Windows startup and clean board perform one W2 run with same-session ROI/slider/foreground, prove automatic exact CHALK and obtain `after_settled.png`; quality policy and independent E5 separately.
- [ ] Only after quality accepted compare frozen W3 on separately clean board. No production changes until evidence.

## FILL-001 V5 — next gate after first 29/29 live, 2026-11-10

- [x] Reviewed immutable `ed74ffd`: first fully completed V5 candidate `K_trim_0_y190_w2` E4 29/29, 10×28→2, 76.125s, screenshots saved. New slider `x1=1363,y306; x30=1207,y307` confirmed in operator calibration file; previous 0/29 attempt remains FAIL in record.
- [x] Read full 8176-event closed Game Monitor run `b0afe0bf`: 29 exact planned pointer starts, five separately identifiable zero-consuming slider drags, no monitor/bridge drops; exact run-bound source `1→1707`, E4 CHALK1706; old Stage6 report `actual_chalk=null` because its strict validator rejected non-consuming slider drags and sampled early `post=1681`. Do not overwrite old report or call original automated validator PASS.
- [x] Added narrow V5 binding update: exclude only zero-delta, complete-lifecycle input on the verified slider corridor; exact 29 geometry/brush checks, safeguard against phone touches, delayed settled PNG capture and independent audit; regression tests. Original acceptance limits unchanged.
- [ ] Confirm full E3 CI at latest code SHA. If FAIL, fix with same baseline; never infer CI from previous commit.
- [ ] **Next E4:** re-run same single frozen V5 candidate on freshly clean board with new validator. Require automated run-bound exact CHALK, `after_settled.png` and independently inspect screen/perimeter quality; earlier 1706 is E4 source result but not accepted as automated screenshot-quality PASS.
- [ ] Once quality gates and source evidence validated, run candidate `K_trim_0_y189_w3` independently on cleared board and compare exact CHALK only between quality-accepted trials. No production promotion until E5.


## FILL-001 V5 — after first full workflow failure, 2026-11-10

- [x] Analyzed actual user commit `fbb97ced` raw source: complete passive ROI and exact `pointCount=1` PASS; failure in 30→10 brush switch, **0/29 strokes**; five unsuccessful drags, radius30 always, board unchanged, mouse safely released. It is **NOT** a failed image-quality trial.
- [x] For V5 ONLY, stop after the first verified unchanged-radius drag rather than trying speculative coordinate corrections; preserve blocked reason and slider coordinates in the attempt report; production controller unchanged, new no-response regression tests.
- [ ] Confirm current E3 for code SHA `4003626b` (and any subsequent revisions).
- [ ] **Next unresolved Windows gate:** inspect/verify actual location, orientation and interaction mechanism of brush-size control; existing saved slider calibration was geometrically accepted but **not proven to change actual game radius**. Do not guess coordinate offsets or increase correction attempts. Keep blank-board `pointCount==1` and same-session ROI safety constraints. Obtain independent native screen/monitor evidence for a successful 30→10 change, *then* execute 29 V5 strokes.
- [ ] Only after completed run: exact run-bound CHALK, original PNG quality audit and independent E5; second candidate on newly cleaned board.


## FILL-001 V5 — single-run Stage6 executable candidate, дальнейшие проверки (2026-11-10)

- [x] Созданы fail-closed same-session `pointCount==1` gate, V5 Stage6 single-run adapter, подключение кнопки UI и runtime-completion callback, безопасная остановка Firefox→Stage6, сохранение before/after PNG, версионированный run-attempt/report и проверяемый выбор 29 штрихов с замкнутой обратной связью по радиусу. Прежняя запретная generic Stage6 загрузка V5 осталась неизменной.
- [x] Добавлен strict Bridge-run финализатор: полный 29-stroke + радиусы 10/2/3, exact непрерывность pointCount; несвязанному событию пользователя нельзя приписывать V5 exact CHALK. При подтверждении запускается original screen PNG audit по FILL001_CHALK_FIRST_PERIMETER_V2; независимая E5 отдельно.
- [x] Сохранено пользовательское объяснение дополнительного одного штриха в предыдущем `5b7e6b8` (удалённое управление телефоном); это не AutoDraw V5. При реальном blank-state `pointCount==1`.
- [ ] Дождаться полного E3 CI для итогового кодового SHA; устранить FAIL, если будет. Проверить Windows portable с optional Selenium.
- [ ] **Следующий E4:** на Windows для одного V5 кандидата открыть чистую доску, подтвердить, активировать Firefox. Встроенный pipeline должен подтвердить ROI, точный `pointCount==1`, действующую калибровку ползунка и только затем стартовать Stage6. При отсутствии подтверждённой калибровки ползунка зафиксировать BLOCKED и калибровать по отдельному протоколу, не угадывать координаты. Сохранить `v5_stage6_runs/v5-<attempt-id>/before.png,after.png,report.json`, Bridge `session.json`, `game-monitor-run-*.json`.
- [ ] Проверить post-run status, независимое E5 экранного качества, run-bound exact CHALK; после одного валидного run на w2 повторить на чистой доске для w3. Принять только по действующему quality policy; не изменять пороги и замороженные исходные PNG.


## FILL-001 V5 — после успешного Windows passive ROI (2026-11-10)

- [x] Получен новый независимый Windows runtime E4: [`5b7e6b8`](https://github.com/Kiddos19882/AutoDraw/commit/5b7e6b877d5793720ad856997ada97417bfaeaab), `probe-0cca08ef367643beaf6397a30ab410c6.json`, `session.json`, `game-monitor-run-20261110T063915979800Z-3c8e7de5.json`. Пассивные три probe, one BoardPane, origin, offset (0,135), ROI (483,243,694,363) **PASS только в рамках этой сессии**; старый foreground PID BLOCKED преодолён.
- [ ] Перед любым V5 вводом установить **новую** валидную сессию и доказать blank-board + exact baseline: проверенный визуальный эталон пустой доски и стабильная ресурсная телеметрия. `pointCount=1` — обычный минимум на пустой доске, но сам по себе не доказательство пустоты. В данном E4 session `pointCount=2→3`, radius30; recorded exact CHALK1 относится лишь к отдельному непроектному pointer run, не к V5.
- [ ] Далее versioned single-run mixed-width Stage6 `10×28→2/3` с проверенными brush switches, task/session/run source SHA, отдельным Clear и immutable pre/post/PNG; E5 acceptance и V5 actual CHALK всё ещё NOT_RUN. Не переносить старое screen ROI в новую сессию и не менять production defaults.


## FILL-001 V5 — один механизм пользовательского foreground (2026-11-10)

- [x] Вместо программной активации через WebDriver/Win32 введено ожидание **обычного действия пользователя**: подтвердить доску в AutoDraw, нажать по верхней панели Firefox. Проверка Win32 foreground PID повторяется три раза подряд; таймаут 90 секунд, отмена немедленно BLOCKED, исключено вмешательство в игру.
- [x] Удалён невостребованный `establish_firefox_foreground` и Win32 SetForegroundWindow fallback; `fill001_firefox_auto_probe` только проверяет PID перед каждым пассивным перемещением. Добавлены unit/negative tests на дребезг PID, таймаут, отмену и неверный GeckoDriver PID.
- [ ] Единственный следующий runtime gate: выполнить свежий Windows passive-only rerun, сохранить `probe-*.json` и свежий `session.json`, получить native mouse witnesses и `screen_roi` или точный BLOCKED reason. Только затем проектировать live Stage6 mixed-width, Clear и CHALK. Не использовать старые E4 отчёты как новые.


## FILL-001 V5 — после второго foreground PID BLOCKED (2026-11-10)

- [x] Проверено пользовательское E4 evidence `1bd38514`: новая Monitor/Bridge сессия подтверждена, но после WebDriver focus Win32 PID остаётся 932 вместо Firefox 5372; ROI/Mapped Stage6/CHALK/PNG NOT_RUN.
- [x] Добавлен ограниченный native Win32 focus request к **ровно одному** top-level visible HWND с PID GeckoDriver Firefox (без ввода мыши/клавиш) с обязательной повторной проверкой реального foreground PID. Однозначного окна нет или SetForegroundWindow запрещён Windows — BLOCKED. Дополнены CI regression tests на отказ и несовпадение PID.
- [ ] Повторить **только passive Firefox probe** на Windows и сохранить новую session/result, проверить PID after native focus, ROI и три OS mouse witnesses. До runtime E4 и PNG validation не включать Stage6; если повторится BLOCKED, собрать Win32 window owner diagnostic без угадывания координат.
- [ ] Stage6 mixed V5, verified Clear, brush switch 10→2/3, exact CHALK и E5 quality остаются закрытыми.


## FILL-001 V5 — продолжение после реального Firefox BLOCKED (2026-11-10)

- [x] Проанализированы runtime первичные файлы пользовательского commit `848aae2`: подключение Firefox/iframe/Monitor/Bridge подтверждено E4 PARTIAL, точный игровой CHALK/PNG E5 не выполнялись. Исходный failure: native foreground Firefox PID gate BLOCKED.
- [x] В коде добавлена **одна безопасная WebDriver focus-попытка** только для owned Firefox, затем обязательная новая проверка нативного Win32 foreground PID; добавлены тесты на matched PID, wrong PID, недоступный PID, отказ фокусировки. Отрицательные случаи оставлены BLOCKED; никаких нажатий в игру.
- [ ] Новый Windows passive-only rerun: из JSON проверить expected/previous/after foreground PID и завершение ROI, только затем переходить к проверке blank-board baseline/brush-свитча. Сборку/CI нового code SHA проверять отдельно. Не отключать fail-closed gate.
- [ ] Разрешённый Stage6 mixed-width V5 single-run, exact CHALK, PNG/E5 — остаётся заблокированным до runtime calibration и чистой доски.


## FILL-001 Firefox auto ROI диагностический режим (2026-11-10)

- [x] Разобрана конкретная причина E3 FAIL `42734007807`: необязательная библиотека Selenium импортировалась до проверки неизменности source-plan. Исправлен порядок, добавлен regression guard; не ослаблялись gate.
- [x] Добавлены `firefox_foreground_witness.py` и negative tests: native Win32 foreground PID должен соответствовать `moz:processID` именно Firefox. Нет проверки фокуса — нет движений. Callback проверяется перед каждым passive move.
- [x] После единственного подтверждения доски новый FILL-001 Firefox worker **только диагностически** собирает passive verified ROI и сохраняет неперезаписываемый JSON со статусом `PASSIVE_MAPPING_ONLY_NOT_EXECUTOR_READY`; теперь при ошибке сохраняется отдельный `BLOCKED` JSON с причиной и привязкой к сессии. Оба исхода содержат `stage6_execution_allowed=false`. Это не Stage6, не очистка игры и не доказательство качества.
- [ ] Проверить Windows E4 (Firefox/GeckoDriver, Win32 foreground PID, authenticated BoardPane, DPI/screen coordinates), без рисования; сохранить отчет и причину BLOCKED при расхождениях. Принимать Stage6 ROI только после этой проверки и чистой доски.
- [ ] Следующий разработческий шаг: versioned FILL-001 V5 single-run Stage6 mixed width `10×28→2/3` со свежими radius heartbeat и provenance, автоматический Clear/blank gate при baseline `pointCount=1` и независимая E5; до их завершения game input запрещён.


## FILL-001 V5 — автоматический ROI, без разрешения live input (2026-11-10)

- [x] Подготовлен research-only Selenium hover + native OS mouse пассивный сборщик `fill001_firefox_auto_probe.py`; функция `fill001_v5_auto_roi.py` проверяет ROI через существующий `boardpane_preflight_transform()`, no guessed offsets, strict same-session, native targets и экранные границы. Добавлены positive/negative fake E2 tests.
- [ ] Проверить этот сборщик в реальном Firefox + Game Monitor 0.2.4 на Windows, создать run-bound evidence и подтвердить соответствие физических координат, DPI и PNG. **Пока результат нельзя применять к executor.**
- [ ] Подключить проверенный ROI и V5BrushSequenceGuard к отдельному single-run Stage6, реализовать безопасный Clear с подтверждением пустой доски (не `pointCount==0`), затем собрать 2 E4 точных CHALK и E5 PNG comparison. Без этого automatic V5 execution BLOCKED.


## FILL-001 V5 — frozen source-plan в штатном AutoDraw (2026-11-10)

- [x] Разрешены только два DEC-030 trim0 кандидата. `fill001_v5_handoff.py` строит 29 исходных штрихов `10×28 → 2/3` из native fixture, сохраняет SHA геометрии, frozen mask ID и versioned policy; не создаёт второго executor.
- [x] В существующей вкладке FILL-001 добавлена экспортная операция immutable source DrawingPlan. Повторная запись запрещена. Stage6 ordinary monochrome loader fail-closed отклоняет V5 diagnostic plan; tamper/regression tests добавлены.
- [x] Создан `V5BrushSequenceGuard`: поверх существующего `BrushSliderController` выполняет preflight начальной кисти 10, фиксирует последовательность 29 штрихов и проверяет после callback фактический размер 2/3. Добавлены negative/unit tests; физический ввод не осуществляется новым компонентом.
- [ ] **Следующий шаг:** подключить проверенный guard к отдельному versioned Stage6 mixed-brush handoff только после task/session/run, runtime desktop ROI и blank-board gate; сохранить SHA source-плана и per-stroke brush evidence. До этого ввод мыши запрещён.
- [ ] Подключить автоматическую калибровку desktop/ROI и проверенный Clear/blank-board gate (не требовать `pointCount=0`), затем один E4 run на каждый кандидат и независимый E5; exact CHALK и screen quality NOT_RUN. Никаких batch/prod изменений.


## FILL-001 — Firefox/browser attachment + V5 mixed-width continuation (2026-11-10)

- **Выполнено в коде, E1:** опциональная Firefox WebDriver сессия из существующей вкладки FILL-001; проверка Origin игрового iframe, подтверждение оператора, новая Monitor/Bridge-сессия с Input Telemetry ON, явная кнопка остановки; тесты и включение Selenium в Windows build. E2/E3 считать подтверждёнными только после завершения CI для HEAD.
- **Открыто (BLOCKED на E4/E5 и разработку):** доказать Windows Firefox/GeckoDriver запуск, авторизованную новую сессию и правильный BoardPane. Затем закончить безопасную environment-fingerprint desktop/screenshot calibration и автоматическое подтверждение Clear (чистая доска может иметь `pointCount=1`; `pointCount==0` нельзя использовать как критерий). 
- **Открыто (V5):** вывести frozen два DEC-030 trim0 кандидата в штатный FILL-001 single-run с отдельным протоколом mixed brush 10→2/3, verified brush switches и собственной идентичностью запуска. Сейчас fixed-radius handoff не обеспечивает такой режим; нельзя подменять ширины или выдавать этот проект за завершённую V5 live validation.
- **Gate:** один управляемый run, сохранённые run/session/report/PNG, exact `post.pointCount-pre.pointCount`, quality gates без подбора порогов, затем независимая validation. Production defaults и `master` не затрагивать.


## P1 — FILL-001 V5 DEC-030: native trim0 99%+ periphery, CHALK gate open

- [x] Versioned `FILL001_CHALK_FIRST_NATIVE_V5`: frozen rectangle SHA, неизменный V4 RGBA control и 8 заранее закреплённых trim0..3×bottom(W2/Y190 либо W3/Y189) вариантов. Изолированная native BoardPane/Egret WebGL проба, отдельный alpha анализ по 1/64/128/254, actual PNG/fixture SHA и fail-closed overwrite/tamper checks. [Native CI SUCCESS 42694626385](https://github.com/Kiddos19882/AutoDraw/actions/runs/42694626385); [source artifact 13707703988](https://github.com/Kiddos19882/AutoDraw/actions/runs/42694626385/artifacts/13707703988).
- [x] Два trim0 кандидата на native alpha128 имеют coverage **99.425944%** / **99.426939%**, leakage 54 backing px (max1 logical px, none outside 3px). Alpha254 coverage >99.25%, far leakage 0. Контроль V4 — 98.943707%, leak0; все trim1/2/3 alpha128 ниже 99%. Все результаты, в том числе отрицательные, сохранены. **Native-screening qualified ≠ game PASS.**
- [ ] **Следующий невыполненный шаг:** отдельная предварительная проверка и E4 live run-bound capture для trim0 (включая mixed-width brush change validation, source-plan signature, calibration, exact CHALK) и независимый E5 screen/renderer comparison. Нельзя выбирать W2 или W3 как CHALK winner без 2 exact run-bound deltas.
- [ ] Повторить new policy на frozen wide/narrow и многоцветных holdouts; лишь потом рассматривать production/defaults и 45-cell. Live E4/E5/CHALK новой геометрии NOT_RUN, production BLOCKED.


- [x] Новый capture validator также требует **SHA оригинальных before/after PNG из PASS_E4_RAW_CAPTURE** и совпадение E4 run/session/task/plan/ROI/exact CHALK; непроверенная screen-геометрия или подмена PNG не принимаются. Поддержка V3 BoardPane-only E4 явно включается флагом, без автоматического fallback. [CI code SHA `33fa812e4a81f9c03b2f5b43660eeb4f21018e9d`](https://github.com/Kiddos19882/AutoDraw/actions/runs/42645465734) после завершения необходимых jobs.

## P1 — FILL-001 DEC-030: внедрение нового CHALK-first PASS

- [x] Пользователь изменил формальный критерий PASS для **новых** FILL-001: coverage≥99%, leakage допускается только на расстоянии ≤3 **логических** px по всему контуру, без удалённых пятен. Измеренный CHALK важнее дальнейшего уменьшения допустимой утечки. [Решение DEC-030](DECISIONS.md#dec-030-fill-001-новый-pass-с-ограниченной-утечкой-и-приоритетом-фактического-chalk).
- [x] В существующий run-bound screen-mask audit добавлена версия `FILL001_CHALK_FIRST_PERIMETER_V2`, геометрическое расстояние от frozen mask в логических координатах, отказ при невалидном масштабе, явная версия policy в отчёте; старый `v2_diagnostic_gate`/legacy V1 не перезаписываются. E2 тесты проверяют 3px PASS, >3px FAIL, coverage<99% FAIL и исторический FAIL.
- [x] Версионированная новая *программная* приёмка `build_fill001_chalk_first_capture_from_runtime()` + `validate_fill001_chalk_first_capture()` с точной CHALK delta, persisted run/session/executor evidence, E4 source binding SHA, screen quality `FILL001_CHALK_FIRST_PERIMETER_V2` и отдельными E2 regressions. Legacy matrix/validator остались с leakage=0. [CI 42643765113](https://github.com/Kiddos19882/AutoDraw/actions/runs/42643765113) (E3 на code SHA `8e2920b9d7410f596a89684ed3f85d44eaafb479` проверять по завершённым jobs).
- [ ] **Первый следующий шаг:** получить real E4 capture с независимым same-run screen mapping по новому policy; затем сравнить два и более quality-PASS плана по exact CHALK. Новые mixed-width планы пока не привязаны к frozen legacy one-radius task; не выдавать synthetic capture за live E4.
- [ ] Проверить новую политику на frozen rectangle/wide/narrow с фактическим screen RGB, учесть multi-color visual holds и лишь после independent validation разрешать продвижение planner/executor. CHALK-предсказатели, frozen captures и старый 45-task batch всё ещё BLOCKED.


## P1 — FILL-001 V4: локальный нижний ремонт проверен (2026-11-09)

- [x] V4 raw provenance усилена: исходный `fixture-input.json` находится рядом с PNG в [артефакте 13655990846](https://github.com/Kiddos19882/AutoDraw/actions/runs/42577013425/artifacts/13655990846); собственный SHA SHA-256 проверяется одновременно против `fixture-provenance.json` и read-only отчёта. Native CI [42577013425](https://github.com/Kiddos19882/AutoDraw/actions/runs/42577013425) SUCCESS на `7814eec3`, test-only SHA `5d3c5904` добавляет негативный test изменения байтов. PNG/пороговые метрики неизменны.



- [x] Изолированная V4 fixture = идентичный V2 `G_trim_3` (RGBA equality PASS в native Egret) плюс один тонкий нижний normal stroke с frozen X=97..363, Y=189/190, width1/2/3, без executor и game CHALK. [CI 42576168617](https://github.com/Kiddos19882/AutoDraw/actions/runs/42576168617); [7 native PNG, manifest, SHA и независимый audit](https://github.com/Kiddos19882/AutoDraw/actions/runs/42576168617/artifacts/13655800959).
- [x] Alpha≥128 контроль missing6655/bottom2457/leak0; y190 width2 missing4245/bottom47/leak0, y189 width3 missing4238/bottom43/leak0. y190 width3 FAIL leakage2414 below mask, несмотря на улучшение покрытия. y189 width1/2 оставляют bottom2457; отрицательные данные сохранены.
- [x] E2 проверяет неизменность исходных 28 штрихов, замороженного SHA, допустимых параметров и запрет overwrite; E3 native run SUCCESS. Ни один V4-кандидат не проходит coverage≥99%/leak0, качество game SCREEN NOT_EVALUATED.
- [ ] **Следующий невыполненный шаг:** локальная боковая коррекция на базе V4 безопасного нижнего штриха, сначала native rectangle, затем независимые wide/narrow frozen holdouts. В дополнение обязательно Stage/client/desktop↔screen run-bound E5.
- [ ] Только после достаточной validation принять решение об отдельном новом E4 и exact CHALK. Production planner/Stage6 defaults и 45-cell matrix остаются BLOCKED; no threshold relaxation.


## P1 — FILL-001 native spatial residual: следующий узкий эксперимент

- [x] `FILL001_NATIVE_CONTOUR_SPATIAL_AUDIT_V1`: frozen rectangle, native V2+V3, alpha1/128/254; verified проверяются **PNG SHA, manifest SHA, frozen mask SHA и прежний alpha audit**. Read-only и fail-closed при изменённых файлах, новой форме или попытке overwrite. [CI 42573526457](https://github.com/Kiddos19882/AutoDraw/actions/runs/42573526457), [source JSON/PNG](https://github.com/Kiddos19882/AutoDraw/actions/runs/42573526457/artifacts/13653904396).
- [x] При alpha≥128 baseline E: missing4717 (bottom2457/right1738/left517/interior5), leak54 (left44,right10). G_trim_3: missing6655, leak0; нижний невосстановленный участок всё ещё bottom2457. V3 H0: missing4394, leak74, bottom2457. Это **offline/native**, не игровой PNG gate.
- [ ] **Следующий невыполненный шаг:** ограниченно испытать закрытие нижних 3 backing-строк отдельно от уже исправленных боковых концов, используя подтверждённый native brush footprint; предварительно измерить необходимые мелкие размеры кисти. Запретить исполнение до независимого native raster PASS; не восстанавливать дефект ценой leakage.
- [ ] Затем отдельно повторить freeze-geometry screening на wide/narrow masks, проверить Stage/screen E5 и только после решения одиночный E4; production/45-cell batch BLOCKED, exact CHALK новой стратегии NOT_RUN.


## P1 — FILL-001 этап A: native Egret footprint и локальная калибровка

- [x] Проверен remote baseline `389f2a23`, последние 20 коммитов, native/full/Markdown CI, текущие ограничения FILL-001.
- [x] В existing `game_renderer_reference.js` и Firefox runner выделен самостоятельный `FILL001_NATIVE_FOOTPRINT_A_V1`: 10 контрольных stroke cases × native Egret WebGL, width5/10, normal horizontal/vertical/diagonal/corner + smooth horizontal, без игры и CHALK.
- [x] Версионированный read-only alpha-анализатор проверяет точные coordinates, SHA-256, RGBA 1380×720, 4 alpha порога и сохраняет bboxes/cross-sections/endpoint extents/junction counters, отказывает при перезаписи или tampering. Есть E2 regression и [native CI](https://github.com/Kiddos19882/AutoDraw/actions/runs/42571729011) / [PNG/JSON](https://github.com/Kiddos19882/AutoDraw/actions/runs/42571729011/artifacts/13653019564).
- [x] Измерено: normal thickness (alpha≥128) width5→16 backing px, width10→30; торцы 7/6 и 15/14; smooth two-point terminal −300 backing px относительно normal; не считать этот synthetic CHALK.
- [ ] **Следующий невыполненный шаг:** native footprint residual локализовать по сторонах/строкам/контурам, получить безопасное adaptive boundary repair без глобальной обрезки; frozen rectangle development, wide+narrow holdout. Не подгонять alpha или маску под PASS.
- [ ] Отдельный run-bound native Stage/screen E5 и только при подтверждении новый E4 single-run exact CHALK. Production estimator/Stage6/defaults/frozen thresholds, 45-cell batch остаются BLOCKED.

Native CI SHA `8dae4b91`: [run](https://github.com/Kiddos19882/AutoDraw/actions/runs/42571729011); full validation code SHA `c31f6415`: [run](https://github.com/Kiddos19882/AutoDraw/actions/runs/42571645484). Статус whole runs проверять по конечному заключению, не делать вывод о live E5.


## P1 — FILL-001: native V2/V3 отрицательные результаты и следующий шаг

- [x] Проверены неизменяемые V2 (width10 contour/inset6 + X-trim1–4) и V3 (width5 contour/inset3, interior width10, trim0–4) в настоящем offline BoardPane/Egret WebGL на frozen rectangle. V2 alpha≥1 leakage 88→1, но coverage 98.9273→98.3816%; V3 лучший coverage 98.9895% при 128 leak. **Оба FAIL**.
- [x] [Native CI 42552197466](https://github.com/Kiddos19882/AutoDraw/actions/runs/42552197466) SUCCESS; сохранены native PNG/manifest/raw alpha reports и отдельно ранний CLI-key FAIL. Исторический game run pointCount baseline=1, exact CHALK1461 не изменён; новый exact CHALK NOT_RUN.
- [ ] **Следующий шаг:** локализовать native leakage/missing по строкам/сторонам и проверить адаптивное boundary repair, не единый trim. Проверить на frozen rectangle, затем wide и narrow, сохраняя отрицательные результаты.
- [ ] Run-bound native Stage→screen RGB E5 для живой геометрии V3, только после него — решение о новом одиночном live E4. Production planner, thresholds и batch BLOCKED.


## P1 — native Egret contour-first: результат и следующий gate

- [x] Повторно использован настоящий `BoardPane`/Egret WebGL renderer (не новый имитатор) для сравнения B, C, E по frozen rectangle/r10. Native E и C имеют 0 RGBA различий; E добавляет 754 отличающихся пикселя к B; [артефакт 13644514101](https://github.com/Kiddos19882/AutoDraw/actions/runs/42549813024/artifacts/13644514101).
- [x] Read-only native alpha↔nearest-3× frozen mask diagnostic: alpha≥1 B 98.768529% / leakage88 / missing4949, contour C/E 98.927284% / leakage88 / missing4311. При alpha≥128 B 98.674968% / leak54; C/E 98.826258% / leak54. Исходные PNG и frozen masks не изменялись.
- [x] Регрессионная проверка fixture identity, запрет overwrite, isolated native Firefox path, отсутствие execution/CHALK и C/E порядок отдельно от ENGINE-001.
- [ ] **Первый следующий шаг:** контролируемый геометрический кандидат — консервативный contour/overlap footprint и оценка необходимости локального interior boundary repair, с независимым native/webgl и сохранением несработавших вариантов. Не выдавать local backing alpha за live screen E5; следующий полноценный gate — V3 run-bound native-to-screen projection, затем только при достаточных доказательствах новый одиночный E4.
- [ ] Сохранить production executor, planner defaults, threshold coverage≥99%/leakage=0, 45-cell batch BLOCKED до отдельного решения.

Проверки: [native CI 42549813024](https://github.com/Kiddos19882/AutoDraw/actions/runs/42549813024), [AutoDraw CI 42549846609](https://github.com/Kiddos19882/AutoDraw/actions/runs/42549846609). Отчёты E3 относятся к конкретному SHA и не являются live-измерением.

## P1 — FILL-001: outline-first / interior-overlap (контролируемый вариант)

- [x] Прочитан существующий A–D `C_sparse_plus_contour`: контур в конце, radius10/rowstep5. Отдельно сохранён frozen baseline V3 OFF с CHALK1461 и quality FAIL.
- [x] В existing `chalk_fill_strategy_comparison.py` добавлены версии `FILL001_CONTOUR_FIRST_OVERLAP_V1` и `FILL001_CONTOUR_EDGE_TRIMS_V2`; выполнены три frozen shapes с независимыми отчётами и PNG. Старый A–D остаётся неизменным, executor-ready=false, measured CHALK=null.
- [x] V1 контроль E (контур первым без изменения штрихов) = C по растеру; покрытие 99.5163% rectangle / 99.5926% wide / 99.3806% narrow, leakage=0 в OpenCV. Глубокие inner insets 7–9 дают ~98.0% на всех формах — FAIL.
- [x] V2 X-trim 1..4: rectangle/wide остаются ≥99%, leakage=0; narrow падает ниже 99% при любом trim — FAIL. Отрицательные данные сохранены в evidence, не подгонять порог.
- [ ] Проверить независимый **native Egret/WebGL renderer** для contour-first (особенно боковые окончания и закругления) с заранее закреплённым screen-space gate и без live до завершения offline проверки; отдельно учесть стоимость дополнительного контура и ограничения темпорального рендера.
- [ ] Только после E5/принятого плана решить, необходим ли один новый E4 run с новым series/task/version. Исходную пару V3 и frozen masks не перезаписывать. Production planner/defaults и 45-cell matrix блокированы.

[Code/CI c0248162](https://github.com/Kiddos19882/AutoDraw/actions/runs/42547807009); [V1](https://github.com/Kiddos19882/AutoDraw/actions/runs/42547807009/artifacts/13644670082), [V2](https://github.com/Kiddos19882/AutoDraw/actions/runs/42547807009/artifacts/13643764696). Эксперименты только E1–E3 offline; CHALK по этим кандидатам NOT_RUN.


## P1 — FILL-001 V3: разбор нового E4 Smooth OFF (активно)

**Новая E2/E3 проверка V3 OFF (2026-11-09):** [CI 42545897296](https://github.com/Kiddos19882/AutoDraw/actions/runs/42545897296) SUCCESS на `3eb92e79`, 47 тестов + 6 subtests; `FILL001_V3_OFF_SPATIAL_RESIDUAL_V1` вывел 18 leaks (10 left/8 right/0 above/0 below), 427 missing, max input roundtrip error 2 logical px. [Отчёт + overlay](https://github.com/Kiddos19882/AutoDraw/actions/runs/42545897296/artifacts/13643392258). Прежний пункт о выполнении spatial audit теперь частично закрыт: **локализация leaks PASS, анализ причинности / native replay OPEN**. Следующий шаг — интерпретировать `missing_by_roi_row` / `missing_by_roi_column` и overlay, сопоставить со stroke endpoints и native renderer, не меняя live план по одному E3 результату.


- [x] Новый одиночный V3 запуск OFF на commit `4efa33c`: 27/27 strokes, Smooth OFF 27/27, exact CHALK=1461, run-bound E4 PASS; неизменные board mapping и runtime binding PASS. Исходное `pointCount=1` — нормальный baseline пустой доски со слов оператора; не трактовать как загрязнение.
- [x] Сохранены исходные raw/PNG/plan и отрицательные PNG quality результаты: V1 coverage 98.3317%, leakage 521; V2 diagnostic coverage 99.5522%, leakage 18 (FAIL).
- [x] [AutoDraw CI 42544453230](https://github.com/Kiddos19882/AutoDraw/actions/runs/42544453230) SUCCESS на `4efa33c`; это E3, не PNG acceptance.
- [ ] **Следующий шаг — E5 offline residual audit на существующих V3 captures**, без игры: классифицировать 18 V2 leaking pixels и 427 missing target pixels (верх/низ/лево/право/внутри), проверить пространственную привязку маски, фактически принятые endpoints и native Egret Stage raster по run-bound данным; сохранить отдельную версию отчёта/overlay без перезаписи данных.
- [ ] Только после определения причины решить, нужен ли новый корректирующий эксперимент или чистая парная Smooth ON серия на сопоставимой геометрии. Не менять thresholds, production planner/executor и не запускать batch.

См. [commit 4efa33c](https://github.com/Kiddos19882/AutoDraw/commit/4efa33c655c1e35a36114df316da77cf54f31300) и [PROJECT_STATUS](PROJECT_STATUS.md#fill-001--новый-v3-smooth-off-e4-2026-11-09-commit-4efa33c).


**Дата:** 2026-11-08 · **Ветка:** `feature/image-geometry-optimization`. Это список **открытых** работ. Полный старый журнал задач с закрытыми пунктами, историческими `PENDING` и ссылками: [TASKS_HISTORY_THROUGH_2026-11-08.md](TASKS_HISTORY_THROUGH_2026-11-08.md).

**DOC-001…DOC-004 закрыты:** [CI 42421451709](https://github.com/Kiddos19882/AutoDraw/actions/runs/42421451709) SUCCESS, 99/99 индексировано, 0 broken links, 9 immutable archives, 0 duplicate decisions. Фактические действия отражены в [WORK_LOG](WORK_LOG.md); старые чек-листы остаются в [истории TASKS](TASKS_HISTORY_THROUGH_2026-11-08.md). Ниже перечислены только открытые технические задачи.

## P0 — текущая работа: игровой движок и документация

**ENGINE-001 native E5 Stage screen-RGB replay (2026-11-08):** исходные 9 E4 runs из `1771653` воспроизведены через настоящий BoardPane/Egret 5.4.1 WebGL Stage на фактических `accepted_points` и неизменной геометрии каждой сессии; [CI 42454224181](https://github.com/Kiddos19882/AutoDraw/actions/runs/42454224181) **SUCCESS** на code/test SHA `6810f75dfb87c8eaac7e73eb9d1063291660c104`, **9/9 `PASS_PER_RUN`** по существующим DEC-025 pixel+geometry+provenance gates, 0 rejected/blocked. IoU горизонталь **0.998995–0.999281**, вертикаль **0.940241–0.940694**, диагональ **0.981740–0.983277**; [native A–D PNG](https://github.com/Kiddos19882/AutoDraw/actions/runs/42454224181/artifacts/13606972733), [индивидуальные маски и отчёты](https://github.com/Kiddos19882/AutoDraw/actions/runs/42454224181/artifacts/13607535199). Первичный [CI 42453831682](https://github.com/Kiddos19882/AutoDraw/actions/runs/42453831682) корректно сохранил 9 `REJECTED_PER_RUN` из-за отсутствовавших bbox-данных в диагностическом comparator; это **дефект схемы отчёта**, а не доказанный провал рендеринга; исправлен `6810f75` без изменения порогов. **E5 screen-RGB gate PASS**, но прямое сравнение live native alpha и полная временная цепочка `ENTER_FRAME → render` **NOT_RUN**, поэтому **ENGINE-001 overall PARTIAL**. CI использовал Firefox/ANGLE Microsoft Basic Render Driver, не GPU Windows пользователя; FILL-001 98.430600%/11 leakage по-прежнему **FAIL**.

- [ ] **ENGINE-001** — Выполнить проверяемый разбор сохранённого Egret 5.4.1 и рабочего `PainterPopup.painterBoard`. Подробный [прямой аудит игровой доски](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md) (§12) подтверждён `E1 PASS` для методов: полный `main.min` получен по Git blob, SHA совпал; разобраны `BlackBoardAtom/BoardPane/Painter/PainterPopup`, бинарный `Atom` и накопление путей в Egret. **ENGINE-001 остаётся PARTIAL:** end-to-end трассировка `WebTouchHandler → desktop mouse plugin / TouchHandler → SystemTicker/ENTER_FRAME → BoardPane → GraphicsNode/Canvas2D/WebGL/mask → screen` теперь выполнена по исходникам [§13](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md). **Документационная сверка выполнена:** Game Monitor/Bridge, шесть PRR runs (порог текущей DEC-025 = 0.92) и runtime 04.11 сопоставлены в [§14](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md#14-финальная-сверка-источников-game-monitorbridge-prr-и-runtime-2026-11-08); исправлено прежнее утверждение о рассчитанных `boardClientCorners` (в JSON они null). **Accepted-only offline gate выполнен:** [ENGINE001_TEMPORAL_ACCEPTED_ONLY_V1](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md) — 27 штрихов, 1260 принятых точек, 70 против 29 Graphics paths, 0 Canvas2D/WebGL RGBA отличий в итоговом растре, browser job [42434968046](https://github.com/Kiddos19882/AutoDraw/actions/runs/42434968046) SUCCESS (E2/E3). **Осталось:** неизвестные повторные `ENTER_FRAME` без новой точки, промежуточные рендеры, screen transform и независимая live PNG validation. Не считать accepted-only E2 полноценным E4. **Критерий завершения:** профильная документация отражает источник для каждого существенного вывода и явно отделяет E1, E2/E3, E4, UNKNOWN; противоречия не замалчиваются. Не запускать новые live/оптимизационные тесты в рамках документационного этапа.

**Новое уточнение ENGINE-001 ↔ FILL-001:** архивный источник уже доказывает разные `smooth` path endpoints (разброс 3 logical px) у 19 одинаковых плановых X-маршрутов; причина фактических **499 right-side misses** остаётся `NOT_PROVEN`, геометрический cap может компенсировать разницу. Следующий gate — подлинные per-stroke PNG bounds + last-two accepted samples + same-run calibration + контроль `normal`/`smooth`, а не немедленное изменение line extension. [Протокол и границы](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md).

**ENGINE-001 дополнение (2026-11-08):** native Egret endpoint study `ENGINE001_NATIVE_ENDPOINT_V1` **PASS E2/E3** ([CI 42438036187](https://github.com/Kiddos19882/AutoDraw/actions/runs/42438036187) SUCCESS, [PNG](https://github.com/Kiddos19882/AutoDraw/actions/runs/42438036187/artifacts/13599599617), [OpenCV comparison](https://github.com/Kiddos19882/AutoDraw/actions/runs/42438036187/artifacts/13600208683)); +2936 backing px, 0 removed и 4/9/13 backing px right-end gain для строк 5/15/16. **Следующий шаг остаётся:** новый E4 same-run stage/client/desktop mapping + per-stroke live PNG/ENTER_FRAME, независимая проверка реальных 499 right misses и 11 leaked pixels, дополнительные `redraw(false)` без новой точки; FILL-001 остается DEFERRED/FAIL. [§17](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md).

**ENGINE-001 5px contour experiment (2026-11-08):** [§18](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md), [full CI 42439343897](https://github.com/Kiddos19882/AutoDraw/actions/runs/42439343897) SUCCESS, [native 30 PNG](https://github.com/Kiddos19882/AutoDraw/actions/runs/42439343897/artifacts/13600612786), [independent OpenCV](https://github.com/Kiddos19882/AutoDraw/actions/runs/42439343897/artifacts/13601121751). На тех же frozen 27/1260 штрихах добавлена одна и та же native замкнутая обводка width=5 logical px/inset=3 в каждом варианте. Coverage board-local alpha128 до/после: game-smooth 98.7499→99.6240%, forced/normal 98.8427→99.6743%; модель добавила по 31 outside-target backing px и **0 восстановленных правых средних**. Не переносить на live FILL 499 screen misses. **Следующий gate сохранён без изменения:** same-run screen geometry, реальный пер-штриховый PNG, temporal `ENTER_FRAME` / repeated redraw; production и quality thresholds не менять.

**ENGINE-001 duplicate-frame update (2026-11-08):** `ENGINE001_DUPLICATE_FRAMES_V1` + independent PNG audit [CI 42440876068](https://github.com/Kiddos19882/AutoDraw/actions/runs/42440876068) SUCCESS at `a35d782`. Frozen 27/1260 replay с 0/1/3 повторами конечной координаты на каждый штрих: 0/27/81 rejected points, 70/71/73 финальных paths, **0 изменённых RGBA пикселей** относительно baseline внутри каждого Canvas2D/WebGL backend. [Native PNG](https://github.com/Kiddos19882/AutoDraw/actions/runs/42440876068/artifacts/13600769368), [independent audit](https://github.com/Kiddos19882/AutoDraw/actions/runs/42440876068/artifacts/13602035420), [подробности §19](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md). Повторы в середине stroke и промежуточные rendered frames не измерены; **следующий E4 gate неизменен:** same-run renderer/client/desktop geometry + реальный per-stroke PNG/ENTER_FRAME trace, разбор 499 right misses/11 leakage. Не считать offline pixel parity live-калибровкой.

**ENGINE-001 one-click Windows lab — E4 completed:** `ENGINE001_ONE_CLICK_LAB_V1` выполнен на Windows и сохранён в [коммите 1771653](https://github.com/Kiddos19882/AutoDraw/commit/177165361b0340515fe3bb74f4847ab3ec579ebc): immutable journal `9fdb9bd9` — 9/9 completed, 9/9 `PASS_E4_RAW_CAPTURE`, 3 направления ×3 повтора, одну Bridge session, 9 distinct run IDs, exact CHALK **846** (горизонталь 324, вертикаль 181, диагональ 341), 861 Egret `ENTER_FRAME` samples. Heartbeat-gate fix `7b129c2` прошёл [CI 42448779447](https://github.com/Kiddos19882/AutoDraw/actions/runs/42448779447); [full CI 42449898657](https://github.com/Kiddos19882/AutoDraw/actions/runs/42449898657) SUCCESS на evidence SHA `1771653` (Windows portable build SKIPPED). Более ранние два блока `9bf7c83` остановлены `lab_bridge_gate` после 1/9 и остаются в истории, не входят в 9/9. [§20–21](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md).

**ENGINE-001 — открытый E5 gate (PARTIAL):** прочитаны все 9 run-bound reports и PNG; независимый fit 1641 `MOUSE_MOVE_SAMPLE` даёт постоянный client→screen offset (0,163) px и max residual **0.749 px** на 6 X + 6 Y траекториях. **Дополнительно проверено:** независимый screen-only RGB decoder/diagnostic подтвердил 9/9 `changed_pixel_count` с Adler-32 контролем и локализовал по 17 нерисовальных пикселей у нижнего края каждого PNG; ориентировочные границы тёмного stroke и остатки относительно accepted endpoints приведены в [§21](GAME_ENGINE_DRAWING_BOARD_ARCHITECTURE.md). **Не завершены:** native Egret replay по сохранённым `accepted_points` и фактическому `stroke_option_raw=true`, заранее зафиксированные пороги/метрика для этого независимого сопоставления, accepted/rejected/missing и SHA validation, сопоставление промежуточных ENTER_FRAME с реальным порядком render. Все 9 runs наблюдали smooth `true`; отдельного live `normal` контроля в этой матрице нет. Не переносить E5 9-line geometry на FILL-001: исторические 499 right misses/11 leaks остаются неразрешёнными. Следующий шаг — **offline E5 PNG/native analysis на сохранённых данных**, без повторного gameplay и без смены quality/production defaults.

## P1 — активный следующий эксперимент FILL-001 Smooth A/B

- [ ] FILL-001 / FILL001_SMOOTH_AB_V1: подтвердить новый software/regression CI для отдельного 2-task manifest и fail-closed raw mode validator.
- [ ] Сделать два отдельных Windows запуска с новой чистой доской: ON, затем OFF. Каждый с Monitor 0.2.4, новой session/run identity, WebGL geometry, exact remaining CHALK >=1600 до ввода, 27 штрихов, сырой Egret ENTER_FRAME, одинаковый frozen RS plan. Никаких 45-cell batch jobs.
- [ ] Сохранить ON/OFF raw audit и quality outcome даже при PNG FAIL; сравнить только при одинаковом before ROI/геометрии, отдельно exact CHALK, coverage, leakage, правые/левые края, строки утечки. Quality gate >=99% + leakage=0 не изменять. Установить причину двухстрочных утечек и ограничения screen calibration. Исторические captures не заменять. [Контракт](GAME_MONITOR_BRIDGE_REFERENCE.md#12-fill-001--чистый-парный-smooth-ab-v1).

## P1 — отложенные тесты качества и оптимизации (не закрыты)

- [ ] **FILL-001-RS single-run diagnostic E4:** **Новый тест FILL-001 (план, не live evidence):** `FILL001_MONITOR_SAME_RUN_V1` — один новый run rectangle/r10/step5/offset0/27 штрихов на Monitor 0.2.4 с native WebGL geometry, событиями/точками/кадрами и парами PNG full-screen + ROI. Новый протокол и ограничения — [Game Monitor §11](GAME_MONITOR_BRIDGE_REFERENCE.md), код (ф) [fill001_monitor_diagnostic.py](../source/preparation/fill001_monitor_diagnostic.py), [CI 42458832846](https://github.com/Kiddos19882/AutoDraw/actions/runs/42458832846). Старый run `6a17a297` с CHALK1260, coverage98.430600%, leakage11 **остаётся FAIL**. Следующая реальная задача — после обязательного software/build preflight только один контролируемый Windows E4; автоматические 45 live runs запрещены. Прямое сравнение двух run ожидает новую пару исходных PNG и session/run logs.

**Статус:** `DEFERRED_BY_PRIORITY` до выполнения текущего ENGINE-001; прежние PASS/FAIL/BLOCKED не меняются. Полная матрица новых кандидатов и ранее запланированных тестов — [ROADMAP](ROADMAP.md#отложенная-программа-тестов-fill-001-geom-001-и-связанных-gates).

- [ ] **FILL-001** — Live baseline 27/27, exact CHALK=1260, actual coverage=98.430600%, leakage=11: **REJECTED**. Frozen A–D и paired screen-ROI contour counterfactual выполнены ([CI 42427514794](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794); [artifact 13596093007](https://github.com/Kiddos19882/AutoDraw/actions/runs/42427514794/artifacts/13596093007)): 1116 screen misses; offset6 model recovers 734, leaves 382, adds 0 model leakage, но старые 11 остаются; ±1px dilation adds 89 leakage. **Следующий gate:** выяснить 738px model-only mismatch, локализовать leakage и подобрать boundary-aware geometry без новых утечек; затем независимый новый live preflight. Пороги ≥99% и 0 не менять. [Original live evidence](CHALK_FILL001_RS_PRE_REPLAY_REPORT_2026-11-04.md).

**Актуализация FILL-001 `c4fefe6`:** 114/114 средних экранных строк имеют правый недокрашенный край 3–7 px (медиана 4), всего 499 right misses; левый край 134 misses (медиана 1 px). Last accepted X каждого из 27 штрихов превышает planned end на 4.208–5.208 logical px. [E2/E3 диагностический CI](https://github.com/Kiddos19882/AutoDraw/actions/runs/42456241289), [raw-derived JSON и PNG](https://github.com/Kiddos19882/AutoDraw/actions/runs/42456241289/artifacts/13607454421); причина **не доказана** из-за отсутствия same-run Stage mapping. Старые 11 leakage слева остаются, не менять gates и production. **Первый следующий шаг:** различить footprint/smooth/cap/transform и 11 leakage без подстановки чужой калибровки.
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

## FILL-001 — Screen Mask V2 (диагностическая проекция)

- [x] Добавлен отдельный `fill001_screen_mask_v2.py` (E1): frozen logical mask 460×240 и исходный RGB threshold=8 не меняются; V2 требует явные проверенные desktop-screen corners BoardPane, run ID и evidence SHA, иначе fail-closed. Сравнение V1 возвращается в том же отчёте и никогда не переопределяет исторический acceptance.
- [x] Добавлены regression tests `test_fill001_screen_mask_v2.py` для identity, сдвига, отказа на неверной геометрии/ROI и сохранения V1. Отдельный CLI принимает `--before`, `--after`, `--run-id`, `--binding`, `--output`, не перезаписывает evidence; JSON `binding` требует `screen_roi:{x,y,width,height}` и `geometry:{run_id,same_run:true,coordinate_system:"desktop_screen_css_pixels",validation_status:"valid",independent_screen_mapping:true,board_screen_corners:{left,top,right,bottom},evidence_sha256}`. Флаги подтверждения — только контракт входа, их подлинность и desktop mapping необходимо независимо подтвердить до E5. 
- [x] E2/E3 исходной Screen Mask V2: focused CI 42504588736 SUCCESS на 480cb3e, 14 tests + 6 subtests; исторические V2 replay V1/old PNG FAIL не заменяют новый live.
- [ ] E5: привязать к двум FILL001_SMOOTH_AB_V1 run независимо верифицированные экранные BoardPane corners и fingerprint, затем перепроецировать оба сохранённых PNG; raw логические и client coordinates без подтверждённого desktop mapping не принимаются. Внести сравнение V1/V2 и native Egret footprint в отдельный evidence отчёт без изменения quality thresholds.

**Область:** только исследовательская диагностика; production executor/planner, frozen mask, предыдущие PNG и оригинальные результаты остаются неизменными. Новые live-рисования не нужны для первого V2 replay.

### FILL-001 Screen Mask V2 — результаты проверки 2026-11-08

- [x] **E2/E3 focused replay:** [CI 42504588736](https://github.com/Kiddos19882/AutoDraw/actions/runs/42504588736) **SUCCESS** для SHA `480cb3e87616846d9fa76276d853cda89ef640e6`, 14 tests + 6 subtests. [Численный JSON-артефакт 13627275540](https://github.com/Kiddos19882/AutoDraw/actions/runs/42504588736/artifacts/13627275540). Исходные E4 PNG/Monitor не менялись.
- [x] Same-run source binding: подтверждены исходный SHA (при строго восстановленных CRLF после Git checkout), пара E4/run ID, неизменные BoardPane client corners и согласованный client→screen offset по `MOUSE_MOVE_SAMPLE`.
- [x] Числовой V2: Smooth ON `coverage=98.796065%`, `leakage=1493`; Smooth OFF `coverage=99.359230%`, `leakage=1474`. В обоих `V2 diagnostic FAIL`. Исходный V1 остаётся 840/849 и `FAIL/FAIL`.
- [ ] **Следующее E5:** сравнить верхние/нижние и боковые пиксели с native Egret WebGL footprint для обоих конкретных run. V2 увеличение утечки не доказывает ухудшения рисунка или правоту V1; запрещено подбирать offset/пороги по результату.

## FILL-001 — новая чистая Smooth A/B V2 (запуск пользователя)

- [x] **E1 implementation:** `FILL001_SMOOTH_AB_V2` с двумя независимыми ON/OFF task IDs, frozen logical rectangle mask и 27-stroke RS plan, отдельным `FILL001_SCREEN_MASK_V2` для post-run анализа. В UI — кнопка «Новый Smooth A/B V2 (2 задачи)»; standard Stage6 и Bridge не изменены.
- [x] Новый manifest валидируется через существующий fail-closed matrix loader. Из каждого нового run сохраняются V1 PNG контроль и V2 PNG diagnostic, полученный из *его собственного* raw Monitor 0.2.4 с SHA-bound client→screen mapping; ошибочный binding не принимается. В V2 pair comparison запрещены старые протоколы, устаревшие task/PNG, несовпадающие raw run SHA и geometry.
- [x] **E2/E3 PASS:** [Full validation 42505872844](https://github.com/Kiddos19882/AutoDraw/actions/runs/42505872844) SUCCESS на code SHA `d557db23ac5911911acc722c58aa140658040cd7`; все обязательные jobs, включая Preparation/G3 и INT-006, SUCCESS. Optional benchmarks/Windows portable build SKIPPED. Новый live E4 по-прежнему NOT_RUN.
- [x] **E4 operator live:** новая серия `fill001-20261108-204825` сохранена в [07f4f3e](https://github.com/Kiddos19882/AutoDraw/commit/07f4f3ea14eb14598fa7ce08c3985e56acb0f73b), два single-task Monitor 0.2.4 run со свежими PNG: ON exact CHALK 1458, coverage V2 98.666023%, leakage 1488; OFF exact CHALK 1459, coverage V2 99.359230%, leakage 1474. E4 raw PASS/PASS, quality FAIL/FAIL; previous V1 файлы не смешаны.
- [x] **Spatial E2/E3 diagnostic:** [`FILL001_V2_FOOTPRINT_SPATIAL_V1` CI 42511062639](https://github.com/Kiddos19882/AutoDraw/actions/runs/42511062639), run-bound raw/PNG SHA; ON upper/left/right leakage 1206/281/1, OFF 1216/253/5; first accepted centerline Y=53 vs plan Y=55 in both runs, max absolute Y offset across 27 lines 2 logical px. No changes to production or frozen mask.
- [ ] **E5 native Egret footprint:** сравнить native WebGL raster нового run с новыми PNG и определить реальную профильную толщину/alpha; текущий spatial audit — только RGB, не native E5.
- [x] **ROI→Egret input diagnostic (E1/E2/E3):** [focused CI 42511723383](https://github.com/Kiddos19882/AutoDraw/actions/runs/42511723383) SUCCESS на research SHA `29bd177760d0cdf23df8c79122b55d88298e0d39`; legacy ROI transform + same-run BoardPane screen bounds + Egret stage Math.round предсказывают первую/последнюю принятую точку первого штриха **точно** в ON и OFF. Max error among observed first/last/Y across 27 lines 1 logical px. Исходный top-center Y53 против plan Y55 установлен до растеризации.
- [x] **Post-run corrected geometry candidate (E2/E3 only):** отдельный `UNEXECUTED_COUNTERFACTUAL`, от BoardPane screen corners вместо ROI границ. На обеих новых E4 серияx прогноз первого ряда `Y=55` вместо `Y=53`, все 27 projected Y имеют нулевое отклонение от плана. [CI 42512084578](https://github.com/Kiddos19882/AutoDraw/actions/runs/42512084578) SUCCESS, 20 tests + 6 subtests, code/test SHA `25113cca074d5a6e4facac5bed51c9d17953b745`. **Не новая игровая запись и не native pixel parity.**
- [ ] **Следующий corrective research gate:** разработать минимальное fail-closed отображение logical→desktop BoardPane bounds из *свежей preflight geometry*, без заимствования post-run mapping следующей сессии, с regression/negative tests. Затем новый отдельный E4 и native Egret E5. Production defaults и прежний план не заменять без доказательства.

Инструкция по шагам: [Game Monitor / Bridge §13](GAME_MONITOR_BRIDGE_REFERENCE.md#13-fill-001--новая-чистая-smooth-ab-v2-под-screen-mask-v2). Старые результаты V1 и V2 replay 2026-11-08 — архивная база, **не вход** новой серии.

## FILL-001 — UI подключения Monitor/Bridge для V3

- [x] **E1 implementation:** в существующей вкладке FILL-001 добавлены четыре кнопки для запуска shared Bridge с обязательной input telemetry, копирования актуальных Monitor/Bridge JS и проверки текущей сессии по фактической телеметрии. Режим ввода остаётся fail-closed, нельзя повторно использовать Bridge с `Telemetry OFF` и старый snippet.
- [x] **Regression tests:** `tests/test_fill001_bridge_controls.py` и новые проверки в `test_brush_behavior_test_ui.py`, включая работу до создания manifest, mismatch/rejection, session diagnostics и stale snippet.
- [ ] **E4 в Windows UI:** подтвердить, что эти кнопки запускают локальный Bridge, подхватывают Monitor 0.2.4 из *текущего* исходника в правильном iframe, показывают свежую сессию с Input Telemetry ON, а V3 затем получает 3 passive samples. Без run-bound live артефактов статус **NOT_RUN**.

## FILL-001 — отдельный V3 BoardPane preflight pilot (после V2 spatial E2/E3)

- [x] **Исследовательский код:** `FILL001_SMOOTH_AB_V3` и `FILL001_BOARDPANE_PREFLIGHT_V1` — отдельные новые ON/OFF IDs и signature, frozen rectangle/27 strokes/lineWidth10/P1, без изменения V1/V2 manifests или production quality thresholds. В UI создана отдельная кнопка V3, Stage6 получает mapped plan лишь после свежего preflight; прежний ROI-transform V3 не применяется.
- [x] **Read-only preflight telemetry:** opt-in Game Monitor Bridge собирает и сохраняет максимум 16 пассивных `isTrusted` DOM mousemove без нажатой кнопки на BoardPane, с UTC timestamp, session ID и geometry SHA. Контракт требует три разные свежие точки ≤5с, heartbeat ≤4с, соответствие текущей сессии/geometry/ROI и постоянный client→desktop offset; неверные данные `BLOCKED`. Отдельные negative tests защищают от архивного run, изменения geometry или disabled telemetry.
- [x] **Focused E2/E3:** [CI 42514396589](https://github.com/Kiddos19882/AutoDraw/actions/runs/42514396589) `SUCCESS` для code/test SHA `9c1f2952ae4aa6f59b245bbffa31ed222cbebaa4` на V3 manifest/BoardPane coordinate gate; отдельная полная validation проверяется на code SHA отдельно. Первая попытка negative fixture [42512957892](https://github.com/Kiddos19882/AutoDraw/actions/runs/42512957892) `FAIL` из-за проверки ожидаемого текста при более раннем отказе на geometry SHA; исправлена; другие отменённые push CI не считаются PASS.
- [ ] **Новый операторский E4:** выполнить сначала один V3 Smooth OFF на очищенной доске по [Game Monitor §14](GAME_MONITOR_BRIDGE_REFERENCE.md#14-fill-001--отдельный-boardpane-anchored-smooth-ab-v3-исследовательский-пилот), проверить actual accepted first row Y55, точный CHALK, PNG coverage/leakage и отсутствие новых границ ошибок; только потом отдельный V3 ON. Оба live `NOT_RUN`.
- [ ] **E5:** native Egret WebGL footprint-vs-live PNG для конкретных новых V3 run, а не только геометрическая модель/контрфактический прогноз. Production CHALK estimator/executor defaults и frozen mask пока не менялись.

## FILL-001 V3 — false geometry SHA mismatch after brush adjustment (76a58ab)

- [x] **Cause E1/E2:** [76a58ab](https://github.com/Kiddos19882/AutoDraw/commit/76a58abc7444519841c3d8548ba8bee3979a708f), separate two run-bound calibration reports and `session.json`: BoardPane screen corners do **not** change; animated `Preloader` width causes full renderer SHA mismatch. No 27-stroke fill started; both calibration run `stroke_count=0`. This is BLOCKED preflight, not quality PASS/FAIL.
- [x] **Corrective code:** keep existing V1/V2 full SHA, compare V3 BoardPane projection SHA instead (session, Egret, canvas/window, Stage/client corners), require fresh passive samples with same stable BoardPane identity; full raw SHA remains in saved evidence. Explicit V3-only binder for Screen Mask V2; reject actual BoardPane move/scale/viewport change and stale telemetry. Preserve [76a58ab](https://github.com/Kiddos19882/AutoDraw/commit/76a58abc7444519841c3d8548ba8bee3979a708f) history.
- [ ] **Next live E4:** after code CI on the final correction SHA and fresh Windows app/server/js restart, generate a **new unique V3 series**, confirm cleared board, fresh before PNG and OFF-only run. Validate 27 actual accepted strokes, first center Y55, exact CHALK, coverage, leakage, full+BoardPane SHA binding. Avoid overwriting `fill001-20261108-232136` artifacts. Native footprint E5 still open.

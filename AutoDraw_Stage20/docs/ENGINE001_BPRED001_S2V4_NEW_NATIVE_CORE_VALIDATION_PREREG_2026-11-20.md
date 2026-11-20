# ENGINE-001 / BPRED-S2v4 — frozen E0: независимые новые native Egret сцены для high-alpha core

**2026-11-20. E0 FROZEN до новых S2v4-кода, тестов, рендеринга.** Task ENGINE-001 / BPRED-S2; baseline feature/image-geometry-optimization SHA fe39bba16c8df21a8fa3f796da35323f240c7269. [BPRED main plan](ENGINE001_BPRED001_BRUSH_PREDICTION_PLAN_2026-11-20.md), [DEC-041](DECISIONS.md), [S2v3 primary source](ENGINE001_BPRED001_S2V3_RISK_AWARE_ALPHA_RESULTS_2026-11-20.md). Не начинать S3 source-over, S4 blind, S5 original-image planning, S6 stroke optimization; не менять production.

## 1. Обоснование и candidate

Из S2v3 CALIBRATION стало известно: M2 AREA8 FP при predicted alpha24..63=2106, alpha64..127=61, alpha128..255=0. Это **posthoc**, не подтверждённая вне известной выборки безопасность. На том же S2v3 у M4 63 FP, H1/H2/H3 PASS, zero-FP safety FAIL. Требуется **новое, неизученное native измерение** для одной заранее выбранной модели.

**M5_HIGH_ALPHA_CORE (primary candidate):** untouched M2 predicted alpha0..255, positive confidence-candidate только если predicted alpha>=128; все остальные физические пиксели UNKNOWN, включая фон. Без confident-negative, без RGB, без каких-либо исправлений M2 AA или изменения его P4D16 формулы. Baseline M2 positive = alpha>=24.

**Secondary diagnostic only, не выбирать winner по новым данным:** M4_FULL_WIDTH_MAX_Q = predicted alpha >=24+max(q_F7_width,q_F73_width,q_F166_width) из **ранее** созданных 30 S2v3 таблиц, quantile0.995; если порог>255, ноль positive, всё UNKNOWN. Таблицы source S2v3 [artifact14593881636](https://github.com/Kiddos19882/AutoDraw/actions/runs/44657226273/artifacts/14593881636), source SHA fe39bba16c8df21a8fa3f796da35323f240c7269. Никакого fit на новых изображениях.

## 2. Frozen new native sample matrix

- Real Egret5.4.1 BoardPane/WebGL, original game Git blob 46cc74de00b6cb5d207b1e1a2ffcd81613b6d388 и renderer Git blob 76d950e0a8911888a9df3b675b866519ecf7bba4. Windows Firefox159.0, BoardPane 460×240 logical, backing1380×720 physical (scale3).
- **120 primary scenes** = 10 widths1..10 × 3 angles **22°,111°,241°** × 2 lengths **9,23 logical** × 2 independent X/Y phase pairs **(1/32,11/32),(13/32,7/32)**. Порядок width asc→angle в перечисленном порядке→length9,23→phase pair. Relative anchor X=center_x+.25+phase_x; Y=center_y+.375+phase_y. Endpoints: delta=(length*cos(angle%180), length*sin(angle%180)), from anchor ±delta/2; for angle>=180 reverse endpoints, as original P4D3.
- В одной сцене три disjoint strokes на центрах (58,40),(172,120),(286,200) логических, каждый 162×162 физический ROI, width1..10; fixed colorRgb 0x503D35, colorIndex1, preserve exact input bytes. Original strokeIds bpred-0..2, adapter ONLY changes IDs to icon-0..2 for existing real native renderer. Source/runtime plan SHA both preserved; all coords, widths, colors, order identical.
- New angle families modulo180 = {22,111,61}, **отдельны от прежней CALIBRATION {7,73,166} и S0 BLIND {38,121,97}**; lengths9/23 и phase pairs тоже никогда не исследованы. 120 scene IDs deterministic BPRED-S2V4-Wxx-Axxx-Lxx-PXxx-PYxx, frozen before first render. Эти сцены — новый **research E3 stress corpus**, а не S0 BLIND / E5.
- **10 replay controls**, width1..10 для angle22 length9 phase(1/32,11/32), byte-exact original native PNG expected, plus1 actual blank BoardPane alpha0. Итого **131 новых native PNG**, 360 primary physical ROIs. Replay mismatch/ink outside ROI/clip/backend drift/missing source/hash => technical FAIL/BLOCKED; никакой выборки по результату.
- Исходная игра, тестовый renderer, P4D16 math, original RGB/история/P4D18 frozen, Stage6, Bridge, Monitor, master остаются неизменными. G32/V44 запрещены как active target.

## 3. Pre-registered hypotheses and independent evidence

Source of alpha: genuine Egret Firefox159 4-channel screenshot, threshold native alpha>=24. M2 full predicted alpha from source P4D16 area8 via tested S2v1 opt-in width1..10, M5 128 cutoff; M4 fixed max old q only secondary. Для 120×3 сравнить physical TP/FP/FN, per width, phase, angle, copy; также alpha1/alpha24 baseline IoU, residual/bbox negative cases. Все cases и raw PNG в append-only archive с SHA256 files/manifest.

- **H1:** M5 alpha24 **FP=0 на всех 360 новых ROIs**. Если >=1 FP, scientific FAIL — даже если CI PASS.
- **H2:** M5 physical TP >=0.90 × M2 physical TP в полном new corpus; нулевой denominator BLOCKED. Не допустить trivial all UNKNOWN.
- **H3:** M5 TP>=0.80×M2 TP для **каждой width1..10**, и TP>=0.85×M2 TP для **каждого angle22/111/241**. Все условия одновременно.
- **E3 technical gate** (отдельно от H): 131 genuine native PNG + blank +10 exact control repeats, source/browser pins, source/game/renderer SHA and sample IDs, 120 cases, 360 ROIs, no non-ROI alpha, all plan/PNG SHA256 independently verified, immutable GitHub Actions artifact. No substitute Pillow/OpenCV.
- Даже если H1..3 PASS, M5 **MODEL_ONLY / NEW_NATIVE_STRESS_CHECKED**, не гарантирует protected white / owner RGB source-over, joins/bends, arbitrary coordinates/browser, game E4 or independent S0 BLIND S4. Confidence safe означает только candidate, в спорных случаях native fallback; no production promotion.

## 4. Reuse and next step

Reuse existing (ф) tests/run_engine001_b1r_p4d3_native_brush_repeatability.py native reference, (ф) tests/run_engine001_b1r_p4b7_native_stroke_attribution.py session, (ф) tests/run_engine001_bpred_s2_alpha_aa_eval.py original AREA8, (ф) tests/run_engine001_bpred_s2v3_risk_aware_alpha.py alpha guard/metrics, original S2v3 [CI44657226273](https://github.com/Kiddos19882/AutoDraw/actions/runs/44657226273), source S2v1/S1 artifacts. Freeze source Git blobs and Firefox in isolated research workflow. Save per-run code/experiment/session ID, exact source and adapted plan, all raw PNG, per-case metrics, rejected cases, SHA and negative outcomes. No new renderer or parallel planner.

**NEXT:** implement limited native stress E3 for this **already fixed** matrix, E2 unit tests, CI artifact; compare H1–H3 honestly, then document. Until completion S2v4 NOT_RUN, S3–S6 NOT_RUN, E4/E5/CHALK NOT_RUN, P4D18 protected white FAIL.

# ENGINE-001 / V27 — native color preview diagnostic despite frozen V26 gate failure

**2026-11-15. Status PREREGISTERED / NOT_RUN.** Follows immutable [V26](ENGINE001_VISUAL_COLOR_PLAN_V26_PROTOCOL_2026-11-15.md) experimental CI [43687362812](https://github.com/Kiddos19882/AutoDraw/actions/runs/43687362812) **FAIL**: existing Stage20 color scanline finished, but a later geometry plan's offline alpha left the exact 150×240 source ROI, which V26 correctly rejected. The partial V26 artifact contains exactly `scanline-plan.json`, `scanline-full-alpha.png`, `scanline-roi.png`, with source pinned SHA. Do not rewrite V26 or call it PASS.

Aim: obtain *read-only diagnostic* images of the existing three planners on the same frozen source while **preserving** the V26 ROI-leakage safety failure status on every violating mode. Do not hide, clip, erase or auto-fix the full-alpha preview or alter production/preview draw semantics.

## Fixed V27 method and rejection rules

Use V26 original and genuine V14 AniLines/V18-B/V20 input SHA/ROI checks unchanged: original 200×320 SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`, V14 AniLines SHA256 `2d4220381e18a86400e4afa950caa064ada5fe1adc821c9a230239cb91848f3b`, V18-B ROI SHA256 `e2c604a31556b0414a451e36d6b7d2aa66cf01c65a36c4a31d3f9d601a3f1adf`, V20 panel SHA256 `8329081964a60399e8ed626384f5671f8e3e80ab716519810c33f4aa926804a5`. Reuse exact V26 `prepare`, existing `build_color_scanline_plan`, `build_geometry_color_plan`, and exact `render_*_preview` at palette8, scanline row-step1, geometry RDP0.8, min component1, original 150x240 ROI at (155,0).

For each mode: calculate **actual full 460×240 alpha pixel count outside ROI** before cropping for comparison, with separate left and right sides and coordinate bbox; preserve the full original unmodified RGBA. Mode `roi_gate` = `PASS` iff outside count 0, otherwise **FAIL**. Continue rendering later modes purely for diagnostic even if a prior one fails; no decision to accept failing mode. Save actual plan JSON, full alpha PNG, ROI image crop, audit JSON and same-size composite side-by-side, separately cropped faces and full. Verify no source substitution behind ink. Freeze no alternative params, no palette retuning and no color-fill semantic claim.

Compare visual recognizability qualitatively (figures, expressions, hair, hands, garment color blocks), and report forecast strokes/vertices and ROI RGB error as descriptive only. This is *one* difficult test image; no generalization or observer-validated PASS. Any ROI FAIL is a **hard production blocker**, even if aesthetically pleasing. Actual Stage6 game brush width/overpaint, E4 game CHALK and >=99% native fill quality remain NOT_RUN. GitHub Actions E3 SUCCESS means successful *diagnostic audit*, not color plan accepted.

Next after visual inspection: choose the most promising plan for a **new-ID, restricted ROI-safe repair study**, if meaningful; otherwise preserve failure. No parameter/threshold changes retroactively to V26/V27.

## Post-run derived evidence (append-only, 2026-11-15)

[Focused V27 CI43687584670](https://github.com/Kiddos19882/AutoDraw/actions/runs/43687584670) **E3 SUCCESS** at SHA `0a59a0d97151e40884976efe90e80aa126bd5049`: source V14/V18/V20 pinned SHA, existing Stage20 plans validated, three actual plan JSONs and individual native offline PNGs, derived SHA consistency PASS. Artifact **14150963966** `engine001-v27-existing-color-plans-visual-evidence` size1059594 bytes; downloaded ZIP SHA256 `7d9c9899ad8839e8495f8de0e017f85e85ba8f85fa87f861601906b8006af394`, independent check of all reported internal file SHA PASS.

| Mode | Actual planner strokes | Plan coordinate vertices | ROI alpha preview px (of 36000) | ROI RGB MAE (diagnostic only) | ROI gate |
|---|---:|---:|---:|---:|---|
| scanline | 11638 | 23276 | 36000 | 7.5691 | **PASS**: zero outside ROI |
| contour | 4104 | 25120 | 18867 | 33.9877 | **FAIL**: 5 alpha px at logical x305,y90..95 |
| skeleton | 5497 | 14819 | 15407 | 37.0031 | **FAIL**: 5 alpha px at logical x305,y90..95 |

V27 workflow success denotes reproducible **diagnostic**; two actual output ROI gates FAIL and thus are not safe to run. The V26 stricter run [43687362812](https://github.com/Kiddos19882/AutoDraw/actions/runs/43687362812) remains **FAIL** and unchanged. V25 visual comparison (manual non-blind, one image) shows full-color scanline preserves two characters, their dark/light outfit distinction and most expressions much better than monochrome skeleton/outline previews; contour and skeleton color modes omit important filled shapes. This is not independent human recognition success and not native Egret output.

**Critical resource blocker:** the *existing plan summary* for scanline calculates **25585 predicted unique game points** (426.4% of nominal 6000 limit, planning safe budget 5100), 11638 strokes and 11426 switches; this is an ESTIMATE, not run-bound exact CHALK. Hence scanline visual fidelity does NOT make it executable on one BoardItem2 board. The fixed V27 quantizer placed five of eight palette colors close to pure white: `#FFFFFF`, `#FFFFFD`, `#FDFFFC`, `#FDFDFB`, `#F9FCF7`; one peach class `#C9A28C` and darkest `#4F363B`. Orange and warm detail visually lose saturation. This is caused by quantizing all white 460×240 canvas rather than the 150×240 source ROI, a **hypothesis** until separated by new-ID test. No posthoc palette edits.

**Decision:** retain raw AniLines contour extraction as candidate for selective facial/detail overlay, but direct V20 tiny-pixel recovery is not useful for major recognizability. Next prereg comparison of ROI-only palette quantization and near-white avoidance, with same pinned image/actual existing color scanline planner. Retain V27 positive recognizability impression as exploratory only, and retain both ROI FAILs and large resource forecast. No production promotion, E4 game quality/CHALK, independent E5, or coverage >=99% native validation.

# ENGINE-001 / S5 — P4D3/P4D4 native width1..10 measured core-footprint E2 (2026-11-23)

**Scope:** read-only post-analysis of archived E3 Egret 5.4.1 PNG, **not** a new native render, S5 planner test, runtime, or production calibration. No fresh S4/legacy target images used as candidate inputs. Branch `feature/image-geometry-optimization`; analysis baseline remote `c3ba915c93ac1453da0e2df026aadc044ce9b2bc`; engine source Git blob `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`; P4D3/P4D4 source code pinned by their historical runs. Normal mode, smoothing off. RESEARCH_ONLY / MODEL INPUT CANDIDATE; gameplay source owner and calibration still unverified.

## Raw source and retrieval verification

| Study | GitHub workflow / SHA | Archive ID | Retrieved ZIP SHA256 | ZIP validation |
|---|---|---:|---|---|
| P4A2 | [44298271642](https://github.com/Kiddos19882/AutoDraw/actions/runs/44298271642) `bc2732c` | [14423584387](https://github.com/Kiddos19882/AutoDraw/actions/runs/44298271642/artifacts/14423584387) | `dd7f7b6bc8241c69ff3251787d691299fee25b1b2338245dbb97099940b0c64a` | digest + CRC PASS, 48 members |
| P4D3 | [44417716689](https://github.com/Kiddos19882/AutoDraw/actions/runs/44417716689) `77e9ddd` | [14480461909](https://github.com/Kiddos19882/AutoDraw/actions/runs/44417716689/artifacts/14480461909) | `690fab5a021efac16ffa6bf67e3c6cef3bc39d5e7eefc57b93a0cd87b2d7bb2d` | digest + CRC PASS, 1687 members |
| P4D4 | [44419171411](https://github.com/Kiddos19882/AutoDraw/actions/runs/44419171411) `e6f561a` | [14482220143](https://github.com/Kiddos19882/AutoDraw/actions/runs/44419171411/artifacts/14482220143) | `e28b065fbc6880f8180f110e3ae934a7f807055c77bc1e188256c09fcf67772a` | digest + CRC PASS, 1447 members |

All three artifacts were downloaded and exact ZIP SHA256 rechecked against historical frozen digests. Native replay equivalence independently spot-checked on three P4D3 scenes (`W01_A000_L34`, `W05_A045_L34`, `W10_A090_L34`) R1 versus R2 full RGBA arrays: PASS. The historical complete 480/480 replay test was not rerun.

## Method (new E2 derived measurement on frozen native E3 material)

For each P4D3 and P4D4, decode **actual** `primary/L34/Wxx/Wxx_Axxx_L34_R1.png` and exact corresponding `_PLAN.json` into 10 isolated strokes. Verify geometry is straight and lengths 34 logical, board logical 460×240 / backing PNG 1380×720 (scale3). Use center of each backing pixel mapped to logical `((x+0.5)/3,(y+0.5)/3)`. For each isolated 54×54 logical crop around fixed centers (58,40),(172,40),(286,40),(400,40),(58,120),(172,120),(286,120),(400,120),(58,200),(172,200), project position onto exact stroke unit vector to obtain axial coordinate `t`. Retain central `7 <= t < 27` logical length20 (discard round caps). For alpha24 and alpha128 separately, count ink pixels in this central slab; define **effective mean transverse width**, logical units:
`w_eff = N(backing pixel alpha>=threshold AND 7<=t<27)/(3^2*20)`.
This is exact **area divided by axial length** for selected raster samples, not the minimum fully covered width or true physical Euclidean diameter. A 1-logical axial bin min diagnostic is also computed. No synthetic capsule pixels enter the result.

10 widths ×24 directions ×10 independent positions = **2400 core samples per study**, measured at two thresholds = 4800 records per study; **9600 per-threshold records** across P4D3/P4D4 (4800 physical isolated stroke samples). Each width×threshold has 240 observations per archive. Other 24-angle length4 scenes exist but are not included because their central segment would be dominated by caps. Alpha24/128 thresholds originate from prior prereg and are not changed to improve results.

## Native effective core width by brush index

Values are **medians across 240 native samples**, in logical board pixels (not PNG pixels). Columns: P4D3 alpha128 / P4D3 alpha24 / P4D4 alpha128 / P4D4 alpha24.

| Game lineStyle width | P4D3 alpha≥128 | P4D3 alpha≥24 | P4D4 alpha≥128 | P4D4 alpha≥24 |
|---:|---:|---:|---:|---:|
| 1 | 1.000 | 1.258 | 1.003 | 1.292 |
| 2 | 2.000 | 2.269 | 2.000 | 2.267 |
| 3 | 3.000 | 3.256 | 3.000 | 3.256 |
| 4 | 4.000 | 4.253 | 4.000 | 4.253 |
| 5 | 4.994 | 5.247 | 4.997 | 5.247 |
| 6 | 6.000 | 6.261 | 6.000 | 6.261 |
| 7 | 7.000 | 7.261 | 7.000 | 7.261 |
| 8 | 8.003 | 8.261 | 8.003 | 8.261 |
| 9 | 8.983 | 9.242 | 8.983 | 9.242 |
| 10 | 10.000 | 10.256 | 10.000 | 10.256 |

P4D3 all-position native range (not confidence interval): at W1 alpha128 **0.944–1.183**, alpha24 **1.183–1.417**; at W5 alpha128 **4.928–5.017**, alpha24 **5.183–5.333**; at W10 alpha128 **9.917–10.156**, alpha24 **10.156–10.389**. The complete every-width ranges, 5th/95th quantiles, per-angle, per-translation values and 1-logical bin minima are in reproducibility CSV. P4D4 rounded medians track P4D3 closely; it does NOT solve exact position-invariance (historical P4D3 292/480 vs P4D4 256/480 exact translated ROI).

P4A2 independent control PNG alpha24 native pixel counts W1 horizontal72/diagonal84, W10 horizontal1360/diagonal1375 exactly match original signed report; these are pixel **areas**, not diameters. PNG is backing3 and must not be interpreted as logical 1:1.

## Reproducibility payload

A downloadable four-file analysis ZIP was generated alongside this report, including `measure_brush.py`, `brush_native_core_measurements.csv` (9600 rows), `brush_native_width_summary.csv` (40 rows) and `README_BRUSH_MEASUREMENTS.txt`. Analysis ZIP SHA256 `3d19e502b61f3f55a3f6da250195e846788e593762c1c6c10467dda9a94abee1`. CSV SHA256: core `8909ca7a9285a1372ed82b2b15b3457e0518a5a4642cc2070e3a267ce6389871`; summary `fcc3f4c0b777cb86cba73ef4f994faf722ac0da68b19c9763f4ef8f8bfb44cae`. The 3 frozen original archives remain at the links above; downloadable analysis ZIP is provided in the associated chat, **not currently uploaded to repository**. To regenerate, place those archives as `/mnt/data/p4a2.zip`, `p4d3.zip`, `p4d4.zip` in the described environment and run script with Python + numpy + Pillow. Repo documentation captures enough numeric data for follow-up even if chat ZIP is unavailable. Repeatability of CSV script under independent environment not yet independently verified.

## Decision for S5-R4 planning (not a new accepted model)

**Confirmed E2:** Egret game's `lineStyle(s)` width is approximately the measured **effective alpha128 core width s** for straight 34 logical line samples; low-opacity alpha24 footprint is typically about 0.25 logical px wider. A single numeric circle diameter is insufficient to guarantee no visual holes. Avoid assuming that alpha24 area provides full-opacity coverage, or using the P4D3 effect as a portable native pixel mask for any translation, angle, corner or multi-color overdraw.

**Missing before multi-lane production:** measured across-stroke guaranteed coverage for adjacent passes as a function of relative offset/angle/phase and source-over; corners/curves/boundary conditions and color compositing; current live screen/game calibration and source owner. No separate new Egret run was necessary for **mean core-width** question; a small prospective normal-mode pair-of-parallel-strokes overlap experiment is appropriate only to decide fill-lane spacing, with frozen E0 and existing harness. Current S5-R3 source4×2 total coverage remains PARTIAL, native S5 painting/E4/CHALK NOT_RUN.

**Result statuses:** original archives SHA/CRC PASS, E2 numerical extraction PASS, P4A2 control PASS, independent sample rerender comparisons PASS on sampled 3/3 scenes; E3 native *new* NOT_RUN, E4/E5 gameplay NOT_RUN, S5-R4 NOT_RUN, game CHALK NOT_RUN. No production/Stage6/Bridge modifications or threshold revisions.

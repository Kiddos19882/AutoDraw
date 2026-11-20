# ENGINE-001/BPRED-S3v2m — full fractional-alpha integer premult lattice: source coverage PASS, usefulness FAIL (2026-11-20)

**Frozen source-known E2 scientific:** D0 **PASS**, D1 **PASS_SOURCE_KNOWN_ONLY** (0 missed native source pixels, all327 former S3v2l F2 negatives recovered), **D2 FAIL** (6360/7753=82.0327615% informative vs frozen ≥90%), D3 native alpha255 **PASS** and unchanged original owner science **FAIL**. CI technical **SUCCESS**, not a native new-E3/owner-safe claim.

## E0 and exact run

Frozen [S3v2m E0](ENGINE001_BPRED001_S3V2M_FULL_FRACTIONAL_ALPHA_INTEGER_LATTICE_PREREG_2026-11-20.md) Git blob `33d40233c271bb8086d1d9c01d45eef3b401679e` committed **before implementation or evaluation**. Research-only (ф) `tests/run_engine001_bpred_s3v2m_full_fractional_alpha_lattice.py`, (ф) `tests/test_engine001_bpred_s3v2m_full_fractional_alpha_lattice.py`, (ф) `.github/workflows/engine001-bpred-s3v2m-full-fractional-alpha-lattice.yml`.

- Initial [CI44750893548](https://github.com/Kiddos19882/AutoDraw/actions/runs/44750893548) SHA `d967ef16` technical FAIL **before science**: new E0 Markdown file not yet indexed, E2 mathematical 9+12+12 **PASS**. Later doc index added; [Markdown CI44750984273](https://github.com/Kiddos19882/AutoDraw/actions/runs/44750984273) **PASS** on documentation SHA `0cab2c09`.
- Next [CI44751084371](https://github.com/Kiddos19882/AutoDraw/actions/runs/44751084371) SHA `8bb80915` technical **FAIL after all33 E2 tests PASS and three raw ZIP CRC PASS** due `numpy.int64` in JSON `G1_recovered_F2_negative` (pure serialization). Corrected **only explicit int conversion** commit `442fc99c094dda7c93af1c86354c51a905bf7200`; frozen model, source, threshold and all previous negatives unchanged.
- Final [CI44751330819](https://github.com/Kiddos19882/AutoDraw/actions/runs/44751330819) SHA `442fc99c094dda7c93af1c86354c51a905bf7200` **E2 33/33 PASS, workflow SUCCESS**, original source provenance and E0 blob pinned, original signed S3v2j raw 857 ZIP entries /856 SHA and CRC, S3v2k prior negative4 entries/3 SHA and S3v2l prior negative3 entries/2 SHA and CRC verified. Final [raw artifact14634888354](https://github.com/Kiddos19882/AutoDraw/actions/runs/44751330819/artifacts/14634888354) 3 entries/2 report-listed SHA256 independently downloaded, ZIP CRC PASS and all **2/2 SHA PASS**. Original true source SHA `ad1fa7fd66d4df563d729b7faae27651ca8279ea`, prior S3v2l SHA `bc4d45e8ad5d1d063bbb750ce78c19452fff7e09`; **no new original Egret E3**.

## Real original Egret source measurements, no threshold adjustment

All **40** original genuine isolated A_ONLY/B_ONLY Egret source Canvas PNG from original S3v2j, widths1..10×two relations, all **8648** real partial-alpha physical pixels and **53752** fully opaque native owner pixels, original owner RGB from signed plans, physical board1380×720. G1 uses continuous `a∈[A−0.5,A+0.5]` and conservative `p_min=floor(C*a_min/255)`, `p_max=ceil(C*a_max/255)` followed by denominator extrema and unchanged ±2 diagnostic RGB byte uncertainty. This is a mathematical overapproximation **conditional on** assumed alpha/premult model, not a proven Firefox internal renderer equation.

| Preregistered gate | Original measured result | Status |
|---|---|---|
| D0 original 856 source SHA + 3 S3v2k negative SHA +2 S3v2l negative SHA/CRC | All pinned, no changed baseline | PASS |
| D1 original native RGB within G1 for all 8648 partial-alpha pixels | **8648/8648 inside, 0 outside** | **PASS_SOURCE_KNOWN_ONLY** |
| D1 previous F2 327 physical negative pixels recovered by G1 | **327/327**, no missing original negative | PASS_SOURCE_KNOWN_ONLY |
| D2 informative G1 width≤16 in each RGB channel, alpha16..254 | **6360/7753=82.0327615%** vs frozen ≥90% | **FAIL** |
| D3 original opaque owner RGB exact | **53752/53752** | PASS |
| Original S3v2l F2 endpoint model D2 | **FAIL327** unchanged | FAIL |
| Original S3v2k owner source I1 D2 | **FAIL3186** unchanged | FAIL |
| Original original S3v2j Canvas C0 / QH-WebGL C0 | **31/40 and21/40** | Full owner composition **FAIL** |
| Original owner hidden-alpha0 damage | **21 real RGB-modified pixels** | Source-owner safety **NOT_VALIDATED** |

G2 low-alpha `A≤15` or width>16 correctly remains `UNKNOWN`; G1 contains all *known source* RGB but its interval is often too broad to be operationally informative. The improvement in containment **does not justify relaxing D2** or choosing the best rounded RGB per pixel. The synthetic E2 test checked **all 256 channel colors × 254 alpha bytes × five physical alpha samples × three integer premult modes**, including known interior discontinuity `C228,A2,p_floor R128`, but does not prove Firefox-specific correctness.

## Decision and single next S3 step

**NEXT:** freeze a distinct **S3v2n** E0 before implementation to test *correlated* fractional alpha / integer premult transition subintervals (rather than independent extrema `p_min/a_max` and `p_max/a_min`), with fixed unchanged source-known D1 zero miss and D2 ≥90% useful. Preserve all327 previous F2 misses, any new misses, and all 21 original owner hidden-alpha0 effects. If this cannot satisfy both, prefer explicit `UNKNOWN` and investigate source readback implementation, not raise tolerance. After any source-known success, preregister **independent new original Egret E3 holdout** before any source-owner pixel-safe claim or S4 reserved BLIND.

Original full E/F protected P4D18 **FAIL**, original source-owner foreign0/coverage≥99%/far leakage≤3 logical px unchanged, S0 BLIND unopened, E4 game/E5 independent/exact CHALK `post.pointCount-pre.pointCount` **NOT_RUN**, original game/Stage6/Bridge/Monitor/production/master unchanged.

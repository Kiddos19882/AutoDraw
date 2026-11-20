# ENGINE-001/BPRED-S3v2n — original Egret source-correlated alpha transitions: coverage PASS, usefulness FAIL

**2026-11-20 — measured.** Technical E2/CI **PASS**, science **D1 PASS_SOURCE_KNOWN_ONLY, D2 FAIL**, D3 source opaque PASS, D0 original pin PASS. **Research-only calibration; NOT native-new E3, not original-image safe, not S4 BLIND, not game E4/E5.**

## Immutable original prereg and source boundary

Original FIRST [frozen S3v2n E0](ENGINE001_BPRED001_S3V2N_CORRELATED_ALPHA_PREMULT_TRANSITIONS_PREREG_2026-11-20.md) Git blob `81f1a18ed5b04265123c337a3cbd63985a835307`, committed `93c1e642a712` **before S3v2n code** and indexed in current documentation. A later *duplicate* unindexed E0 `ENGINE001_BPRED001_S3V2N_CORRELATED_FRACTIONAL_ALPHA_LATTICE_PREREG_2026-11-20.md` was accidentally committed `15dc3a13` after the original and deleted as redundant in `0e7caef4`; both commits are retained in Git history, but **only original E0 81f1a18 is controlling**. No frozen E0 modified and no acceptance retuned.

Research-only additions:
- (ф) `tests/run_engine001_bpred_s3v2n_correlated_alpha_premult.py`, commit `33420cdd8c09` — exact rational breakpoints for `p=floor/rint_even/ceil(C*a/255)`, including integer and half-integer transitions, with original fixed ±2 uncertainty, verified against previous G1 and all original native source pixels.
- (ф) `tests/test_engine001_bpred_s3v2n_correlated_alpha_premult.py`, commit `fc09933951a2` — 11 tests, including all 256 RGB channel bytes ×254 partial-alpha bytes ×5 physical samples×3 modes plus both sides of transitions, invalid inputs and frozen E0 pin.
- (ф) `.github/workflows/engine001-bpred-s3v2n-correlated-alpha-premult-lattice.yml`, commit `2b75046649b314bb8951f1cb8e18958c0fc3cbfb` — original signed Egret source data only, fail-closed upstream artifact SHA and scene counts.

[CI44753200427](https://github.com/Kiddos19882/AutoDraw/actions/runs/44753200427) executed exact **SHA `2b75046649b314bb8951f1cb8e18958c0fc3cbfb`**; technical **SUCCESS**. E2 **11 new + 9 S3v2m +12 S3v2l +12 S3v2k =44/44 PASS**; Markdown structural audit PASS; first original E0 and four original research Git blob sources pinned. Four genuine earlier archive ZIPs all CRC+SHA verified before evaluation:
- Original Egret5.4.1/Firefox159 source [S3v2j raw artifact14621923148](https://github.com/Kiddos19882/AutoDraw/actions/runs/44721915503/artifacts/14621923148), source SHA`ad1fa7fd66d4df563d729b7faae27651ca8279ea`, 857 ZIP entries/856 report-member SHA.
- Original S3v2k owner unknown output artifact14630379548, four ZIP entries/3 SHA, frozen 3,186 owner RGB interval misses.
- Original S3v2l isolated source output artifact14630989895, three entries/2 SHA, frozen 327 F2 native RGB low-alpha misses.
- Original S3v2m output artifact14634888354, 3 entries/2 SHA, original G1 RGB 0 misses, original nonvacuity G2 FAIL at 6,360/7,753.

[New raw S3v2n artifact14635548996](https://github.com/Kiddos19882/AutoDraw/actions/runs/44753200427/artifacts/14635548996) independently downloaded and inspected: ZIP **4 entries, CRC PASS, 3/3 report SHA256 PASS**, original 40 case reports + all G3 out-of-interval source RGB pixels (empty set) + width/alpha-bin statistics, report pins source/run/SHA. Output generated from **the same original 40 known isolated source native Canvas PNG**, NOT new E3.

## Frozen D0–D4 scientific results

| Frozen metric | Observed source result | Status |
|---|---|---|
| D0 original source + prior negative provenance | Four original archives CRC/SHA PASS, 40 unique source cases | **PASS** |
| D1 original source RGB in correlated integer quantization G3 | **8,648/8,648**, RGB misses **0** | **PASS_SOURCE_KNOWN_ONLY** |
| D1 recovery original fixed F2 negatives | **327/327** low-alpha original native pixel occurrences covered | **PASS_SOURCE_KNOWN_ONLY** |
| D2 informative G3 RGB intervals width≤16 at original alpha16..254 | **6,851/7,753 =88.36579389%**, required ≥90% (=at least 6,978) | **FAIL (short 127)** |
| D3 fully opaque source owner RGB original source | **53,752/53,752 exact**, zero wrong RGB | **PASS** |
| D4 original unmodified loose G1 calibration | **6,360/7,753 =82.0327615%** informative, misses0 | **Prior G1 D2 FAIL unchanged** |
| D4 original two-owner Egret composition C0 | Original Canvas **31/40**, QH WebGL **21/40** | **FAIL unchanged** |
| D4 original owner-alpha0 neighbor harm | **21 real foreign owner RGB changes** | **NOT_SAFE unchanged** |
| D4 previous interval failures | S3v2k **3186**; S3v2l F2 **327**; S3v2m utility FAIL | **FAIL unchanged** |

G3 gains **491** informative native pixels vs G1 (6,851−6,360), with no observed source RGB misses. This is a source-known diagnostic improvement **without changing mathematical ±2 uncertainty, original H1 or original source-owner foreign=0**. It is NOT a production-safe predictor: p-mode union is deliberately conservative and latent native physical alpha/CPU readback pathway is not proven to match the tested formula.

### Original alpha strata and remaining UNKNOWN

| Native alpha | All original partial pixels | Informative G1 | Informative G3 | G3 uncertainty |
|---|---:|---:|---:|---:|
| 1–15 | 895 | 0 | 0 | 895 UNKNOWN_LOW_ALPHA |
| 16–63 | 1,618 | 225 | **716** | **902** UNKNOWN_WIDE |
| 64–127 | 1,846 | 1,846 | 1,846 | 0 |
| 128–254 | 4,289 | 4,289 | 4,289 | 0 |

All scientific D2 deficit comes from alpha16..63. The previous 327 F2 misses at alpha1..63 remain explicitly represented, **not excluded to achieve a pass**. The 895 alpha1..15 pixels remain UNKNOWN, not “paint safe”. Original full source E/F protected P4D18 **FAIL**, original source-over owner RGB unsafe and S0 BLIND reserved sealed.

## Bounded next step

S3v2n E0 required that if D1 **or D2** fails, the result be preserved and unsupported arithmetic/readback assumptions be investigated under a *new separately frozen E0*. Here **D2 FAIL** by 127/7,753, so **do not** promote G3 to production or use it as a ready planner, do not relax width≤16 or the 90% gate, and do not retroactively select one of three rounding modes on the known Egret source. The next single S3 task is a separate prospective source-precision investigation into which premultiplied byte rounding/readback paths are physically possible in original Firefox159 Egret at alpha16..63; test on genuinely **new** native source scenes with new RGB, phases, widths/directions before any source-owner safe claim. New native E3 is **NOT_RUN** in this stage; E4 game, E5 independent, run-exact CHALK `post.pointCount-pre.pointCount` NOT_RUN; Stage6/Bridge/Monitor/renderer/master/production unchanged.

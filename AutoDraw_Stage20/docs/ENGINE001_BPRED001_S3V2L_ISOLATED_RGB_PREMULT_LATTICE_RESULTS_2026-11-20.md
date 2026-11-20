# ENGINE-001/BPRED-S3v2l — original isolated Egret source RGB byte-lattice diagnostic (2026-11-20)

**Outcome:** E2 CI technically **PASS (38/38)**; preregistered D0 **PASS**, D1 **PASS**, **D2 FAIL**, D3 **PASS**, D4 **PASS**. The proposed F2 original RGB source export lattice **is scientifically incomplete and not pixel-safe**. No new original Egret E3, no S0 BLIND, no S4/S5/S6, no original E/F quality-gate relaxation, no production code/Stage6/Bridge/Monitor/master change.

## Frozen E0 and evidence provenance

[Prospective E0 preregistered BEFORE any S3v2l code](ENGINE001_BPRED001_S3V2L_ISOLATED_RGB_PREMULT_LATTICE_PREREG_2026-11-20.md), immutable Git blob `85ea039ad6b1683b40297ed307ec750c021b4630`, hypotheses F0/F1/F2/F3 and original D0–D4 thresholds frozen before test run. Research runner (ф) `tests/run_engine001_bpred_s3v2l_isolated_rgb_lattice.py` commit `9dc26bdf6f09d29dfa29ab5476931db3802b09e0`; 12 tests (ф) `tests/test_engine001_bpred_s3v2l_isolated_rgb_lattice.py` commit `a3903661cba40e972ca52558f8860e703befa547` (corrected test-only SHA below), isolated workflow (ф) `.github/workflows/engine001-bpred-s3v2l-isolated-native-rgb-lattice.yml` commit `24bd94dd8e2f18dedaf9f76a4bcb9d0b453e4e19`.

Inputs: genuine original Egret5.4.1 Firefox159 [S3v2j CI44721915503](https://github.com/Kiddos19882/AutoDraw/actions/runs/44721915503), source exact SHA `ad1fa7fd66d4df563d729b7faae27651ca8279ea` ([80 original native source raw artifact14621923148](https://github.com/Kiddos19882/AutoDraw/actions/runs/44721915503/artifacts/14621923148)), original **857-entry ZIP CRC PASS +856/856 SHA**, original plan SHA of every scene, no recomputed trig coordinates. Original negative owner interval [S3v2k CI44741517301](https://github.com/Kiddos19882/AutoDraw/actions/runs/44741517301), prior SHA `88e53c1205e163fd86db9251bb168f2be491fb97` ([4-entry negative artifact14630379548](https://github.com/Kiddos19882/AutoDraw/actions/runs/44741517301/artifacts/14630379548)), original **CRC/3 SHA** and previous **3,186** misses (1,580 top-only,1,580 bottom-only,26 overlap) verified before F0–F3 calculations. No new E3 native capture; offline known-original-Egret E1/E2 only.

First [CI44743311721](https://github.com/Kiddos19882/AutoDraw/actions/runs/44743311721) technical **FAIL** before source data: unit test incorrectly asserted that endpoint-evaluated F2 interval necessarily contains all F1 predictions made at an interior alpha byte. Concrete counterexample source RGB `[228,77,156]`, alpha byte `2`, F1 floor R=128 while original frozen F2 endpoint interval lower R=168. This proves that endpoint-only integer quantization isn't generally monotone: **the frozen F2 formula is potentially incomplete even relative to its own F1 modes**. Updated only the *test*, NOT E0/F2 envelope/rounding model or scientific threshold, to preserve the counterexample as expected negative (commit `bc4d45e8ad5d1d063bbb750ce78c19452fff7e09`).

Final [CI44743578450](https://github.com/Kiddos19882/AutoDraw/actions/runs/44743578450) exact SHA `bc4d45e8ad5d1d063bbb750ce78c19452fff7e09` technical **SUCCESS**, E2 **12 new S3v2l +12 S3v2k +14 original S3 = 38/38 PASS**, original research Git blob checks and Markdown integrity PASS. [Final 3-entry raw artifact14630989895](https://github.com/Kiddos19882/AutoDraw/actions/runs/44743578450/artifacts/14630989895), independently downloaded ZIP CRC PASS and **2/2 report-listed SHA256 PASS**; full original 40 source-native isolated case reports plus every F2 negative physical pixel retained. No source or prior negative report overwritten.

## Authentic isolated Egret RGB from source with one owner

Exactly **40 isolated** genuine original Egret Canvas original board 1380×720 aligned PNG, widths1..10×two relations×A_ONLY/B_ONLY, original owner source RGB from source stroke source plan, no borrowed old G32 palette and no simulated brush. At all isolated true pixels:

| Preregistered measurement | Real physical data | Status |
|---|---|---|
| Fully opaque source alpha255, original RGB matches source palette | **53,752/53,752** RGB exact, no source owner mismatch | **D1 PASS** |
| Partial-alpha source `1..254` | **8,648** original real physical pixels | Source basis |
| F0 original palette RGB differs by >2 in at least one channel | **2,129/8,648** (24.62%) | Negative baseline |
| F1 fixed `floor(C*A/255)` premult, half-up unpremult | **3,942/8,648** pixels RGB exact | Descriptive only |
| F1 fixed `nearest-even(C*A/255)` | **3,266/8,648** pixels RGB exact | Descriptive only |
| F1 fixed `ceil(C*A/255)` | **288/8,648** pixels RGB exact | Descriptive only |
| F2 physical-alpha endpoint (A±0.5)×three p roundings, ±2 RGB fixed envelope | **327/8,648** actual original pixels outside F2 | **D2 FAIL** |
| F2 native alpha `16..254` interval RGB width≤16 in every channel | **7,131/7,753 = 91.9773%** | **D3 PASS** |

All 327 F2 misses occur at low-alpha edges in the original isolated source: **172** at alpha1..15, **155** at alpha16..63; none at alpha64..254. Across all 10 brush sizes, F2 misses by width: w1=11,w2=35,w3=20,w4=41,w5=25,w6=54,w7=20,w8=39,w9=35,w10=47; CROSS_ROTATED164, NEAR_SKEW163. RGB miss channel occurrences: R111,G54,B162 (counts are nonexclusive). This is not zero-safe/source-owner quality acceptance. The F1 best arithmetic mode was **not** chosen per-pixel as a production model.

**Example real negative:** original `BPRED-S3V2J-W01-CROSS_ROTATED-B_ONLY`, physical board pixel `(532,334)`, source RGB `[228,77,156]`, exported true RGBA `[255,85,170,6]`; F1 floor `[213,43,128]`, nearest `[213,85,170]`, ceil `[255,85,170]`. Original F2 *endpoint only* upper bound for R **237**, while actual R **255** — **FAIL**. This is a real low-alpha source representation effect, not any two-owner overlap or P4D18 full-source-safe result.

## Scientific interpretation and limits

F0 shows raw physical RGB of a partially covered isolated stroke often differs from the color input, even with only one owner and no second stroke; F3 confirms fully opaque pixels are source-exact on known native scenes. Nearest/floor/ceil finite-premultiply alternatives do not reproduce every partial source pixel. F2 width/coverage is promising for detecting uncertainty but **fails to include 327 genuine native RGB physical pixels**, so it cannot be used as a pixel-safe owner predictor and must not be silently padded beyond fixed ±2.

The [WHATWG Canvas standard](https://html.spec.whatwg.org/multipage/canvas.html#premultiplied-alpha-and-the-2d-rendering-context) establishes lossy unpremultiplied/premultiplied conversions. [Mozilla bug 2046791](https://bugzilla.mozilla.org/show_bug.cgi?id=2046791) documents CPU-architecture-dependent 1-byte readback differences in a Firefox `getImageData()` unpremultiply route. **This does NOT identify that code path as the exact source of this game's original `toDataURL('image/png')` S3v2j source differences.** Source alpha byte A is quantized after rasterization; integer premult from A endpoints can cross discontinuous boundaries. Exact internal integer raster algorithm, GL source state and source owner safety remain **UNKNOWN**. No experiment on the user's running game.

D4 older original Egret controls remained unchanged: S3v2j native RGB QH stage zero; original 40 ordered `s3.source_over` Canvas **31/40**, QH WebGL **21/40**, owner alpha0 actual damage21; S3v2k D2 original 3186 FAIL untouched. Full protected original E/F P4D18 **FAIL**; no S0 reserved BLIND or S4, no E4 live/E5 independent, no exact CHALK (only game-run pre/post pointCount can prove).

**NEXT one bounded S3 action:** preregister a separately versioned diagnostic for discontinuities across the *full* measured fractional physical alpha range, rather than assuming two interval endpoints bracket integer premult quantization. Compare exact original source RGB at all 327 negatives with conservative, mathematically complete integer lattice support or explicitly classify UNKNOWN_LOW_ALPHA. Preserve the current F2 FAIL, original foreign-owner=0 and E/F quality gates. New independently frozen native Egret scenes are still mandatory before any proposed safe RGB/owner classification is accepted. No S4/S5/S6 or production.

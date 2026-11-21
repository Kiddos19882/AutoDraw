# ENGINE-001 / BPRED-S4-R1 CR1 — 14 opaque DEV original RGB contrast reference; real measured negative E2

**2026-11-21. Technical source E2/CI PASS, predefined raw contrast diagnostic SOURCE FAIL on 13/14 DEV; independently verified semantic critical, game-owner, native brush safety UNKNOWN.** Measured within accepted [S0→S6 / original-first S4-R1](ENGINE001_BPRED001_BRUSH_PREDICTION_PLAN_2026-11-20.md), following NH1–NH4 bounded neural intermediate. [Prospective CR1 E0](ENGINE001_BPRED001_S4R1_OPAQUE_DEV_COLOR_REFERENCE_PREREG_2026-11-21.md) exact **immutable Git blob `5c277643c3a778f21a509e8ae84f20b887c36ed0`** committed SHA `2b6d6bd6a2f3916be0ed965a506161f3b70dd18d` BEFORE new code, threshold selection or opening original14 image result. **Source RGB color contrast is real source arithmetic reference; it is NOT externally annotated human semantic ground truth or game owner.**

## Evidence and reproducibility

- Original baseline HEAD `29f6fac601c0dc79da7b8696c78e2f74d6c6dcf2`, working `feature/image-geometry-optimization`; fresh remote HEAD, 20 commits, Actions, docs and DEC-044/045 verified. Research-only CR1 raw reference in (ф) `tests/engine001_bpred_s4r1_original_rgb_pair_reference.py`, new DEV runner and 11 synthetic tests, dedicated separate (ф) `.github/workflows/engine001-bpred-s4r1-cr1-opaque-dev-source-reference.yml`. Source-only, no SAM2/OneFormer/DINO/BiRefNet reinference.
- [Final original 14 DEV source GitHub Actions CI44894548249](https://github.com/Kiddos19882/AutoDraw/actions/runs/44894548249), **code/CI SHA `fbc639f4245eee098dfbb32495040b907598c5fd`**, job136817311638 **SUCCESS**: E0 blob match PASS, py_compile PASS, **11/11 synthetic independent E2 regressions PASS**, Markdown audit PASS at tested SHA, original source manifest Git blobs/bytes, H×W+alpha, exact 14 DEV opacity verified, no H8 outputs, per-file PNG SHA consistency PASS. Step runs after E0 indexing in README. Historical first docs-index before README [CI44894378216](https://github.com/Kiddos19882/AutoDraw/actions/runs/44894378216) **FAIL solely unindexed new CR1 doc**; README indexed without editing E0, initial first CR1 [CI44894488154](https://github.com/Kiddos19882/AutoDraw/actions/runs/44894488154) cancelled by concurrency, not a scientific FAIL. Last docs-only CI at HEAD after updates tracked separately; do NOT infer a final HEAD CI pass from code SHA.
- [Real original source audit artifact14703388023](https://github.com/Kiddos19882/AutoDraw/actions/runs/44894548249/artifacts/14703388023), downloaded and independently rechecked ZIP outer SHA256 **`af707740aa4808b18e7143aafb78c57e6454b2d1b53830cde8630845f664f45d`**, GitHub-provided SHA256 identical, 20,038,068 bytes, **29 ZIP entries all CRC PASS** (28 PNG and 1 `cr1_report.json`). JSON SHA256 **`18eea02802293ecdfd73f4890860de82b15efad3d69da55b53527aa93158d3f0`**. Independently rehashed **28/28 exact per-record derived image SHA256** and decoded **28/28 original H×W geometry PASS**, only 14 original +14 review overlays for DEV (0 H8,0 reserve); all original raw Git blob SHA checked in runner. No production or separate game images. Locally generated read-only **14-image review contact sheet** `autodraw_s4r1_cr1_opaque14_review_contact_2026-11-21.png` SHA256 `cb911e441e3c31d9c0d32260147f58673be294e8ef4b8ba1600e05512322719b`, NOT a human annotation/GT and NOT committed to repository.

## What was measured, exactly

Source-only independently calculated reference on EXIF-oriented original RGBA: **opaque-opaque four-connected horizontal/vertical original RGB pairs**, channel max absolute integer RGB difference `>=32`; **mark both pixel endpoints** of each such pair. No Lab, predicted source Sobel, SLIC, palette colors, neural masks or game brush in reference computation. Compared to unchanged prior `generic_source_maps["protected"]` and `original_source_region_uncertainty["geometric_potential_core"]`. Pre-fixed threshold32 is a *diagnostic*, not an existing acceptance or user-tuned semantic tolerance; JPEG compression or real texture can trigger it, so don't promote every red pixel to an automatically required safety boundary.

| Measure | Actual original opaque14 DEV |
|---|---:|
| Total reference contrast endpoint pixels | **861,166** |
| Protected by existing original source maps | **817,632** =94.945% |
| **Unprotected** raw contrast endpoints | **43,534** =5.055% |
| Endpoints also in existing **geometric potential core** | **9,018** (subset of unprotected/UNKNOWN, **NOT ADMISSIBLE**) |
| Original P2 potential core pixels, all14 | **6,496,235** (geometry only, UNKNOWN) |
| Images with source contrast misses | **13/14** source diagnostic FAIL |
| Images with complete reference protection | **1/14** raw contrast-only PASS |
| Zero-reference endpoints | **0**; no N/A cases |
| Alpha DEV excluded as prereg | **1** `Sanrio_Characters_Hello_Kitty_Image026.webp` (its independent alpha reference separate) |
| HELDOUT / S0 BLIND / reserve second50 model outputs | **0 / 0 / 0** |

Per-original strongest negative cases (not visual proof of human-harm):

| DEV file | Raw contrast endpoints | Unprotected | Miss rate |
|---|---:|---:|---:|
| `6f6fff4105b941bf85b1fbd8519a.jpg` | 254,889 | **18,641** |7.31% |
| `ima56655ges.jpg` |37,876| **8,485** |22.40% |
| `EZAL3k9ddfs.jpg` |116,961|**5,256**|4.49% |
| `ima4ges.jpg` |38,373|**3,759**|9.80% |
| `4534364.jpg` |41,127|**3,257**|7.92% |
| `images (1).png` |18,519|**0**|0.00% |

Other 8 file rows preserved in raw JSON with per-source hashes/shapes. The number of endpoint misses **must not** be called exact brush leaks or damaged face/eye pixels without genuine object semantic reference and native Egret run. The red review overlay only marks source RGB contrast misses; yellow marks protected contrast and teal shows current P2 **UNKNOWN** potential core.

## Decision and unchanged next gate

**CR1 proves that original strong raw RGB transition evidence can escape the existing source protection on 13/14 opaque DEV**, even though original source maps already protect Sobel/Lab and alpha interfaces. It is a new diagnostic input to the planned independent S4-R1 reference, not a validated new stroke restriction. **Do not mechanically add 43,534 pixels to source protected mask or retune RGB threshold to force PASS**: that could overprotect textures and reduce useful fill area without proving semantic safety. Require independent **validation-only** human/independently annotated critical zones (eyes, face, hands, outlines) for a predeclared DEV subset, with no manual per-input production masks; compare model-free source masks and optional archived pretrained hints on identical labeled original coordinates, measure independent false-safe and nontrivial abstention, report not applicable and any failures. Alternatively use a properly source-matched independent public human-annotated dataset (e.g. official BSDS500 boundaries) in a separately preregistered benchmark, never silently treat it as GT for these 14 specific originals. H8 and S0 BLIND120 remain sealed.

**Technical: E2/CI PASS. Scientific source contrast diagnostic: FAIL. True critical semantic/owner false-safe, native coverage, RGB harm, game quality: NOT_READY / UNKNOWN; strict S4 BLOCKED per DEC-044/045**; previous S2/S3/P4D18 native/scientific FAIL remain intact, E3 native/E4/E5/exact run-bound CHALK NOT_RUN. Stage6, production, master, Bridge, Game Monitor untouched. First next unfinished task: independently verified critical detail validation-only label subset and *human-grounded* measurable abstention/false-safe for opaque DEV; THEN new prospective original Egret native S4 if eligible. No S5/S6.

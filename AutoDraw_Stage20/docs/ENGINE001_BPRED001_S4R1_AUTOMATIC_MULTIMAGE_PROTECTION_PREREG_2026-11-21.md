# ENGINE-001 / BPRED-S4-R1 — перспективный E0: универсальные карты и независимые изображения

**2026-11-21. Статус: FIRST PROSPECTIVE E0 FROZEN BEFORE ANY NEW S4-R1 IMPLEMENTATION / TEST.** Продолжение [исходного BPRED-001 плана с дополнением S4-R1](ENGINE001_BPRED001_BRUSH_PREDICTION_PLAN_2026-11-20.md), [DEC-044](DECISIONS.md) и [DEC-043 one bounded science](ENGINE001_BPRED001_BOUNDED_RESEARCH_AND_VISUAL_QUALITY_PLAN_2026-11-20.md). Основание — прямое решение пользователя: **AutoDraw обязан строить protected/owner/edge карты автоматически для нового изображения**, без постоянной помощи человека или фиксации вручную «глаза этих двух персонажей». Это исследовательский S4-R1 source-known readiness/auto-generalization; сам строгий BPRED-S4 BLIND120 остаётся **BLOCKED**, это не протокол изменения старых scientific gates или разрешение production.

**Source GitHub evidence before prereg:** branch `feature/image-geometry-optimization`, last verified pre-document HEAD `397ce0da4a6dabafdc08b4343194224afb5fb62d`, changes to plan only `271f62d5a5d29c3085f4d22aa099605bc31e9023` then corpus correction `f8eb52b4832963b8d8b9cc081dfd906a6b2c82e6`. Latest previously verified Markdown CI `44816279392` PASS for baseline SHA, not for this E0. Directory metadata fetched via GitHub `contents/AutoDraw_Stage20/data/generated_autodraw_plan/images_31_first` at the branch; exact Git blobs/sizes below. A second GitHub `contents/AutoDraw_Stage20/testImages` enumeration found 8 byte-identical Git blobs; no binary decoding / near-duplicate scan yet. **31/31 unique within current directory**, but 8 are not novel relative to `testImages`.

## 0. Frozen research hypothesis / failure exits

Hypothesis H-R1: a *single versioned, parameter-consistent, fully automatic* original-first source/protection-map transformer can accept many **different** raw RGB/alpha inputs and produce conservatively justified owner/edge/white/critical/UNKNOWN masks and coordinate provenance **without hardcoded Egret rectangle/owner index**. The objective is a reusable source transformation, NOT immediate pixel-safe acceptance. If semantic importance or calibrated native stroke risk cannot be inferred, mark `UNKNOWN`, do not infer `SAFE` from missing edge; report excessive abstention as usefulness failure, do not call all-UNKNOWN PASS. Unqualified statements "any image" are an engineering goal **not proved by 31 source images**.

No tuning of experimental mask thresholds, semantic model, crop selection, artifact inclusion, or E0 acceptance after looking at locked heldout results. R1 calibration only uses DEV/KNOWN_CONTROL, H set unopened for tuning. Source E/F Egret-known original is a historical control and **never** evidence of independent generalization. S0 BLIND120 remains sealed and completely distinct.

## 1. First frozen corpus — exact file identity / roles

**GitHub directory (п):** `AutoDraw_Stage20/data/generated_autodraw_plan/images_31_first/`. GitHub tree shows **31 files**, formats JPG/JPEG/PNG/WebP, not decoded or visually classified. Files prefixed `free-icon-font-` are classified **by name only**, not validated visually. Cross-path exact Git-blob duplicates in `testImages` = **8** and assigned `KNOWN_CONTROL`, never locked heldout. Remaining **23** provisional different-blob candidates: **15 DEV** and **8 LOCKED_HELDOUT**. Split assigned before any S4-R1 code/metric by rule: take non-duplicate source names lexicographically (GitHub contents order), among 22 non-`free-icon-font-` names choose 0-based indices **2,5,8,11,14,17,20** as heldout (7), plus the only non-duplicate `free-icon-font-search-3917132.png` as heldout (1); other 15 new files DEV. `KNOWN_CONTROL` 8 files: free-icon-font-envelope-3916611.png, free-icon-font-home-3917033.png, free-icon-font-instagram-6422200.png, free-icon-font-phone-call-5070407.png, free-icon-font-user-3917688.png, images.png, vk-dog-1.jpg, wV6VeZI9S1Y.png. Frozen heldout exact 8 filenames: **4mages.jpg, 8jcCDKAVfnA.jpg, OyFhUImix-g.jpg, free-icon-font-search-3917132.png, i76868mages.jpg, ima457656ges.jpg, ima56ges.jpg, images.jpg**.

**Manifest of Git blob SHA1, GitHub file size (bytes), pre-test role:**

| File (ф) | Git blob SHA1 | Size | Locked role |
|---|---|---:|---|
| `-------------5.jpg` | `b1a877104c563d1257b812041e8fa69df75947b0` | 277453 | DEV |
| `4534364.jpg` | `27050fbd1661f1c36a0abea3ee0dc25eb84d86a5` | 36647 | DEV |
| `4mages.jpg` | `fa2dc7cde69b7d58baf8d7826627c7631a19977f` | 36761 | LOCKED_HELDOUT |
| `6f6fff4105b941bf85b1fbd8519a.jpg` | `661f3edd329208d5d7a7dac964e6874da649433d` | 207267 | DEV |
| `78687676images.jpg` | `91f39ff30860ef3ea9272952be9c8940ea5d1c53` | 23867 | DEV |
| `8jcCDKAVfnA.jpg` | `9c9ac854aabbb984122e34347a844ad704dada23` | 51688 | LOCKED_HELDOUT |
| `9a6f49ac56622c042c6b13b44f99089.jpeg` | `9b14bf1462d6e76bd41ea68f6f90734d324a7600` | 19004 | DEV |
| `EZAL3k9ddfs.jpg` | `aae3ebc8cc03d8bc35c4979aa42bbcef445b9828` | 232857 | DEV |
| `OyFhUImix-g.jpg` | `82e840b1554147cf165f59e83d176ccee35b746b` | 233291 | LOCKED_HELDOUT |
| `Sanrio_Characters_Hello_Kitty_Image026.webp` | `072711810ac4ae65d1a786291869e810a421f61c` | 20484 | DEV |
| `free-icon-font-envelope-3916611.png` | `8d692665927fac8703f3fbc72b7cf437bda9dba2` | 9876 | KNOWN_CONTROL |
| `free-icon-font-home-3917033.png` | `4c1f9c7a6682451d3949c539480e2f7550c5eedf` | 9167 | KNOWN_CONTROL |
| `free-icon-font-instagram-6422200.png` | `21825c0ed29528b7d5f78f4d05d0369cd79eb8f3` | 18213 | KNOWN_CONTROL |
| `free-icon-font-phone-call-5070407.png` | `0532b44a46da4cec5b9356f471fc8b52033d5d9b` | 19990 | KNOWN_CONTROL |
| `free-icon-font-search-3917132.png` | `3950982cdbd3573ffa76857905b9aa8732e26b20` | 12456 | LOCKED_HELDOUT |
| `free-icon-font-user-3917688.png` | `fdbbd58edd9269589e5c05d72c45f4a2b517c61a` | 12737 | KNOWN_CONTROL |
| `i245mages.jpg` | `10e52e989c29e0d1d3ad3afa69b2767b5fc8778a` | 28427 | DEV |
| `i76868mages.jpg` | `faf95ab53a11d1799fd05e641c8f95315fcbde70` | 19383 | LOCKED_HELDOUT |
| `im567ages.jpg` | `b5285511f5041856dd5b95b1cffa99a7f96a99df` | 25456 | DEV |
| `im6765876ages.jpg` | `07aeb0f285e9ca9ee4dab182527388f58d8dd1c8` | 30665 | DEV |
| `ima457656ges.jpg` | `31b3eb6b5b3760b496496c2eb83b46050bb8e74f` | 32166 | LOCKED_HELDOUT |
| `ima4ges.jpg` | `df4efe255ef19810e9a3e7b8b9b748b7819702b4` | 39294 | DEV |
| `ima56655ges.jpg` | `601fa20b719422800db57340c85c21ef3b588d76` | 36380 | DEV |
| `ima56ges.jpg` | `76fa43aaf6db884fc4da42a08dd517e8682e4205` | 34891 | LOCKED_HELDOUT |
| `image6s.jpg` | `19e722fda4877aeaa3cbb133d10936b9c285c668` | 27508 | DEV |
| `images (1).png` | `da82ab87349b6fdf650e3cf0200041558cfb5a6d` | 15304 | DEV |
| `images.jpg` | `e0bd649b0721fbdedab0ba1020ebee4031ded428` | 9522 | LOCKED_HELDOUT |
| `images.png` | `fc9c984d15e9dda7d6511b01b5a88ca52ba2380f` | 599511 | KNOWN_CONTROL |
| `k3JSTTQng98.jpg` | `7a9a538b2e072e2c6677a840b0ec47c1ec69c87c` | 329979 | DEV |
| `vk-dog-1.jpg` | `e30f9eea6c527176c3002e332bbaeb9189f5555f` | 315384 | KNOWN_CONTROL |
| `wV6VeZI9S1Y.png` | `d3cd95b846f036a3f8acecf75d2a237e46dcf13a` | 97308 | KNOWN_CONTROL |

**Integrity gate before new data use:** R1 program must read real binary bytes (not rely on extension), compare Git blob SHA1 using `sha1(b"blob "+len+NUL+raw)`, record SHA256 bytes and decoded RGB/alpha, EXIF orientation/pixel sizes. Intra-corpus duplicates are absent at Git blob level, but **near-duplicates, resizes, crops, metadata re-encodes, cross-project prior consumption and real semantic categories are UNKNOWN**. Before any heldout evaluation, run *source-only* perceptual-duplicate and training-leakage scan against DEV, KNOWN_CONTROL, old project testImages and original full-image where accessible; if any H item is visually duplicate of development data, **BLOCKED** and require a **new explicitly frozen split/version** before model iteration (not moving images after failure). No claiming 8 statistically independent image genres, no synthetic counts.

## 2. Input/output contract and reuse-first implementation scope

Input: source file path/content SHA256, immutable original RGB + alpha, orientation, dimensions, transparency/background policy, output logical target size+aspect/letterbox transform (if known), per-owner color reference `source_owner_index`/`source_owner_RGB` when source/preparation has legitimately provided it, parser/version source mode and palette provenance. R1 **cannot assume Egret-specific** `320x200`, `150x240`, `X0=155`, `owner6=white`, `ROIS_FULL` face/eyes/hands. A fixed padded or scaled source must identify exactly where each original pixel lands. Missing/invalid transform, owner map, palette or alpha semantics => `MISSING/UNKNOWN` and fail closed before stroke permissions.

Output per input, at original resolution plus documented projection: `source_rgb_alpha`, candidate `owner_index` with provenance or `MISSING`, original RGB-derived `rgb_edge_evidence` via Sobel/Lab ΔE, `owner_adjacency_edges` when owner exists, `white_original_or_background_evidence` separately from `transparent` (white objects must not be confused with background), `detail_evidence` with multiscale/connected components + optional frozen pretrained semantic hints, `protected_conservative`, `unknown`, `candidate_interior`, `source_to_logical_affine`, model/threshold/version SHA and per-pixel owner certainty. Every declared definitely protected/unknown map must derive from original or owner evidence; RGB no recolor. Optional neural model can suggest semantic details, not overwrite original color, and without validated model/no confidence should default UNKNOWN for semantic safety.

**Reuse code already verified E1:** source gradient + ΔE + morphology from (ф) `tests/run_engine001_b1r_p1_fullrgb_edge_aware.py::full_features`, source pixels + composited quality from (ф) `tests/run_engine001_b1r_p4d13_full_original_relaxed_finish.py`, native attribution from P4D17/P4D18, legacy (ф) `tests/run_engine001_b1r_p4b4_boundary_tolerance_sweep.py::source_critical_rois` for **comparison only** (hardcoded rectangles; not accepted universal). Next authorized code must extract minimal pure-array generalization rather than call fixed-shape whole pipeline, and must not modify original/native renderer, production image-preparation default, planner, executor, Bridge, Monitor or other frozen E0.

No external neural training. If pretrained model is proposed, separately pin model+license+version, uncertainty and fallback. `UNKNOWN` means source risk has NOT been proven safe; `candidate_interior` is not authorization to execute strokes. R1 "native" result cannot be derived from OpenCV circle proxies: future E3 Egret source owner/white leakage independent gates per [INV-012](ENGINEERING_INVARIANTS.md).

## 3. Prospective test protocol, controls and stop criteria

- **R1-P provenance/unit contracts (E2; NOT_RUN):** deterministic results twice per input; original RGB unmodified and no palette hallucination; correct EXIF/alpha/white semantics; invariant source-to-target transform with invertible mapping on valid areas; rejects corrupt or missing files and invalid provenance; original-known reference hashes match; NO hardcoded current original ROIs or colors; no manual per-filename if/else, no file-specific threshold selection. Output includes protection/UNKNOWN reason masks and actual original pixel counts, latency and artifact hashes.
- **R1-I generalization (independent DEV→H):** dev known8 controls +15 new DEV for implementation/calibration; fix code SHA and all tunable thresholds BEFORE evaluating 8 locked H once. Report each file individually including **FAIL/BLOCKED**; no selecting a subset of visually attractive images. Require semantic handoff/ground truth provenance for independent importance safety — absent labels => `UNKNOWN` and cannot PASS protected recall. Score exact source/owner boundary preservation, missed high-contrast contour candidates, false-safe on ground-truthed critical/white/transparent owner pixels, abstention fraction and amount of *useful* candidate coverage; all-UNKNOWN detector explicitly **FAIL usefulness**. Source-only maps can get `PASS E2 technical` but cannot become safety/brush E3 PASS.
- **R1-E3 only when separately preregistered (NOT_RUN):** evaluate actual original Egret stroke footprints native widths1..10 near protected owners/color transitions, original source-white contamination, contour continuity, physical alpha0 holes, owner coverage and leakage in source's valid logical board mapping. Categorical strict scientific zero-foreign and far>3logical=0 never relaxed; old source G3 useful>=90%, original 99% gate and original E/F FAIL stay FAIL. No use of BLIND120 or current engine live game to bypass mask uncertainty.
- **Stop / decision:** Exactly one initial general-purpose map pipeline, one source-known DEV set and one sealed external H set. If H manifests image leak, semantic incomplete or all UNKNOWN, report `PARTIAL/BLOCKED`; do not manually patch each image, train new model or alter prior E0 until a separate decision and new version. If H source-only robust but native false-safe unvalidated, S4 strict remains BLOCKED; after future independent native acceptance proceed to S5 true Egret spacing/coverage/holes/overdraw and S6 quality-first minimization/live run-bound exact CHALK.

## 4. Evidence at prereg moment / scope boundary

**E1 observed only**: 31 GitHub entries with names, sizes and unique intra-folder Git blob SHA; 8 exact same Git blobs in `testImages` (including source Egret `wV6VeZI9S1Y.png`), current fixed-shape P1 and P4B4 source functions, DEC-044 strict block. **No S4-R1 generated maps, test runs, image decode, perceptual duplication audit, native evidence, completed holdout or new acceptance.** This artifact is a prospective protocol/documentation task. Native S3v2r2 original Egret scientific foreign-owner harm18 occurrence and old original P4D18 E/F protected failures remain unmodified. Requested task permits documenting the universal workflow; next code and testing must remain inside explicitly authorized activity scope.
# ENGINE-001 / BPRED-S4-R1 / RAG1 — один предзарегистрированный DEV-прогон E2: численный gate FAIL

**Дата:** 2026-11-22. **Протокол:** [RAG1 immutable prospective E0](ENGINE001_BPRED001_S4R1_REGION_COLOR_RAG1_PREREG_2026-11-22.md) Git blob `97692d0c20bdfabfc81016cbbc34cd7d84af4cbe` был зафиксирован [commit b61f834](https://github.com/Kiddos19882/AutoDraw/commit/b61f83489dd73eb4c16928b840772765388b91cf) **до** кода. **Код и CI:** [commit be2eda5](https://github.com/Kiddos19882/AutoDraw/commit/be2eda55b2faa25f26c8c2f33a235aff1ca5073f), [run #44954612003](https://github.com/Kiddos19882/AutoDraw/actions/runs/44954612003), completed SUCCESS; seven new source-only synthetic tests PASS, E0/git engine SHA PASS, 4/4 frozen DEV sources processed, runtime manifests/preview SHA PASS. Scientific/image acceptance **FAIL (0/4 RAG1 numeric gate)**, NOT native Egret quality proof.

## Фактические результаты

[Скачать полный raw RAG1 DEV ZIP, artifact14726717409](https://github.com/Kiddos19882/AutoDraw/actions/runs/44954612003/artifacts/14726717409). GitHub ZIP SHA256 `f168c413a57585db69ccd508d53a5ac1f540026e9dbfad9b489134da715b8f23`, независимая загрузка и ZIP CRC PASS; **28/28 listed raw files** отдельно перепроверены SHA256. 4 отдельных source-папки: exact original bytes, nearest128 baseline, RAG region-IDs PNG, RAG1 final game128 PNG, original source edges, side-by-side 4-panel, JSON source and derived SHA. Никаких старых художественных входных карт/owner/strokes/P4D/E-F/FC1, heldout не вскрывались. Значения — **source-pixel RGB MAE**, НЕ native game RGB и НЕ CHALK.

| Original DEV | Первичные → итоговые геометрические регионы | Цвета RAG1 | RGB MAE nearest128 → RAG1 | Одиночные игровые 8-связные компоненты nearest128 → RAG1 | Проспективный gate |
|---|---:|---:|---:|---:|---|
| `wV6VeZI9S1Y.png` | 365 → 161 | 27 | **4.876 → 19.917** | 6 277 → 0 | FAIL |
| `Sanrio_Characters_Hello_Kitty_Image026.webp` | 813 → 480 | 12 | **9.797 → 15.782** | 2 670 → 38 | FAIL |
| `EZAL3k9ddfs.jpg` | 1 783 → 323 | 43 | **22.197 → 27.043** | 41 419 → 0 | FAIL |
| `images (1).png` | 1 826 → 44 | 8 | **1.867 → 3.454** | 4 366 → 0 | FAIL |

Frozen E0 required at least 2/4 scenes to reduce singleton islands ≥15% **without RGB MAE increase >15%** and without losing strong synthetic source boundary. All four scenes reduce singleton fragmentation, but **ALL FOUR** have a >15% RGB-MAE increase; thus `0/4`, scientific research candidate `FAIL/NO_PROMOTION`. CI SUCCESS concerns only correct execution, tests and artifact hashes, **not** drawing quality.

## Анализ причины и границы выводов

Visual PNGs show the original/nearest128 forms recognizable, while RAG1 removes entire thin facial/hair/cloth detail inside coarse regions, especially the two-character `wV6VeZI9S1Y.png` and `EZAL3k9ddfs.jpg`; Hello Kitty is structurally recognizable but loses shade/detail. This is not a minor later painting gap. **Code E1:** existing original-source SLIC initialization uses target area128 source pixels; RAG1 only **merges** initial regions, and computes one game128 swatch per final region. The originally planned **split of overbroad SLIC regions was not implemented** in this first bounded candidate. Thus thin original details may be lost before RAG has a chance to protect them. The strong-boundary veto protects **merges between regions**, not an important source edge located *inside* one starting region. AWEAK3 `PARTIAL/CONFLICTED / NO_PROMOTION` remains independent earlier negative; not a reusable artistic input.

**Supported conclusion:** RAG1 as implemented is too destructive and must NOT become the new S4 owner/contour map or native planner input. The result does NOT prove that all SLIC/RAG/region-based approaches fail, nor that numerical singleton count is itself a useful acceptance metric. No threshold tuning after this run.

## Решение и единственный следующий шаг

**STOP RAG1 E0** after one candidate and one signed four-DEV result. Preserve all source, reports, original E0 and failure. **FIRST NEXT S4.2+S4.3:** formulate a **distinct architecture-level source-detail-preserving split/guard before regional color assignment** (protect original strong internal boundaries and small real details, separate region IDs from game indexes). It needs a separate prospective E0 *before* new code and another bounded DEV assessment; do NOT re-try arbitrary `MAX_ADDED_COLOR_SSE` / `REGION_TARGET_AREA` sweeps or repair final FC1 PNG. S4.4, engineering S5 handoff, formal S4 validation remain NOT_DONE/BLOCKED.

**Evidence:** E1 source review+same-hash raw visuals, E2 seven synthetic tests and 4 DEV metrics, E3 native Egret RAG1 `NOT_RUN`, E4 actual live `NOT_RUN`, E5 `NOT_RUN`, exact CHALK `NOT_RUN`. Existing production executor, frozen thresholds, BLIND120/H8/second50, Stage6/Bridge/Monitor/master untouched.

# ENGINE001_FDOG_ANILINES_V14 — GitHub Actions comparative extraction preregistration

**Task:** ENGINE-001 / dark-jacket missing seams. **Date:** 2026-11-15. **Status:** REGISTERED BEFORE V14 EXECUTION. **Scope:** opt-in CI research only, no production, executor, calibration, Bridge, Monitor or master edits.

## Fixed dependencies and source

- Git source `AutoDraw_Stage20/testImages/wV6VeZI9S1Y.png` from checked-out branch; **200×320 RGB, 97,308 bytes**, SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`; Git blob `d3cd95b846f036a3f8acecf75d2a237e46dcf13a`. Abort before inference on mismatch.
- FDoG: upstream <https://github.com/SSARCandy/Coherent-Line-Drawing> pinned SHA **`37887374e99fe22f1d22004ca114ed2538f0abaf`**; upstream *real* C++ `cld` CLI, built on Linux (OpenCV 4, Boost, wxWidgets available); default CLI `--ETF_kernel 5 --ETF_iter 1 --CLD_iter 1 --sigma_c 1 --sigma_m 3 --rho 0.997 --tau 0.8`. Input exact original PNG, output original-sized PNG. Build failure is a real FAIL/BLOCKED for that job, not a substitute implementation.
- AniLines Detail: upstream <https://github.com/zhenglinpan/AniLines-Anime-Lineart-Extractor> pinned SHA **`5d188fb68f40fb04fbe3c9c54dcc57b16c914818`**, Detail weights published via upstream Google Drive file ID **`12U1Mwlonoipk2Yvr12mNaFB30foy420o`**. Weights downloaded only to ephemeral runner `weights/detail.pth`, never committed. Before inference SHA256 logged; since publisher's trusted SHA is not yet documented, provenance is **partial**, no immutable external-model identity claim. Fail closed for download failure, invalid weight file, import or inference error. CPU PyTorch fp32 (`fp16=False`) through an adapter that imports upstream implementation; no modified network weights or alternative model.
- Runs independently on GitHub hosted Linux; if one fails the other can still finish. No NVIDIA GPU assumptions; time and resource exhaustion are possible.

## Fixed output protocol

Output per job: `source.png`, `line-output.png`, `jacket-source.png`, `jacket-output.png`, `jacket-overlay.png`, comparison sheet, `report.json` with SHA256 for every derived PNG, upstream revision, package versions, source SHA, optional weights SHA, GitHub checkout SHA, exit/failure logs supplied by Actions. Comparison ROI **source coordinates** `[100:200,62:251]` (100×189, **includes other elements; not a semantic jacket mask**). Preserve native 200×320 output; optional resized 150×240 version should be explicitly labelled proxy. Canny comparison uses GaussianBlur(3×3), Canny60/120 L2, 1-original-pixel dilation; line pixels are grayscale <128. Report line-pixel count, Canny recall proxy, non-Canny pixels, components>=8, dark inner ROI `gray<105` erosion5×5 proxy **only**, NO jacket-seam ground-truth precision/recall or recognizability acceptance.

**Success for infrastructure:** pinned source validated, authentic external inference ran at pinned SHA with non-empty 200×320 output and hashed files. **No quality PASS automatically**: a dense/noisy edge mask is not useful seam recovery. To claim improvement require manual source-anchored seam labeling, false-positive inspection and new-image heldout evaluation; native Egret, per-color safety, >=99% fill, 3 logical px diagnostic bound, game E4 exact CHALK=(post.pointCount-pre.pointCount) bound to run, independent E5 stay NOT_RUN until independently established.

## Evidence discipline

Preserve negative results, failed downloads, logs and dependency hashes. Do not automatically switch weights, backend, image preprocessing, thresholds or CPU/GPU if a run fails; new choices require new protocol. Avoid committing downloaded model binaries. CI PASS for a given SHA means *only* that its jobs completed as required, not artwork quality. 

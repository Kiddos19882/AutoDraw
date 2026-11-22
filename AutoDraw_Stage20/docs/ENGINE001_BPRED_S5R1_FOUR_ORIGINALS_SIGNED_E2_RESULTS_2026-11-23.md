# ENGINE-001 BPRED-S5-R1 — four fresh S4.6 original-to-S5 model-only E2 (2026-11-23)

**Baseline original-only S4.6 source:** code SHA `86c5133c9c2cb2603cfaf1bdab872705a3b7de88`, S4.6 research-only provenance unchanged; source-owner MISSING, native-calibration UNVERIFIED, `admissible_for_gameplay=false`. Current S5 source-only runner [CI45080283784](https://github.com/Kiddos19882/AutoDraw/actions/runs/45080283784) exact source code SHA `b9595ed80ec7fc49c2648ca9cbfe645eb5a6d5b4`, job137386722864 **COMPLETED SUCCESS**. [S5-R0 E0 freeze](ENGINE001_BPRED001_S5R0_REUSE_INVENTORY_AND_S5R1_PREREG_2026-11-23.md), [DEC-051](DECISIONS.md) S4 accepted for S5, [DEC-052](DECISIONS.md) smooth=false/normal. All S5-R1 candidate outputs `MODEL_ONLY_NON_EXECUTABLE`.

## Independent raw artifact and checks

[GitHub artifact14776444970](https://github.com/Kiddos19882/AutoDraw/actions/runs/45080283784/artifacts/14776444970), 5469-byte ZIP, SHA256 `6103fd86d2864e5b34dc21e8f5da34a627b963167739d6625be5981e889005d2`. Download verified exactly locally, `ZipFile.testzip()=None`, 5/5 ZIP CRC, member SHA match summary `output_sha256` all4. Full4 raw original input hashes preserved in `00_S5R1_RESULTS.json`; `source_contract_manifest_sha256` present for each rebuilt source. S5-R1 runner recomputes same original `original bytes → decode_original → build_ctr1(original, actual engine128) → export_quarantined → verify_quarantined → build_candidates` **twice per original**, then byte-for-byte canonical JSON equality. All4 double-fresh determinism PASS, source SHA and actual engine blob pin `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`. CI9/9 synthetic S5 tests PASS and output binding/false native game status PASS, not native.

Raw SHA:
- `00_S5R1_RESULTS.json`: `7396d25ffa7c5a0d434ca5daa949e523b7dee80d39d75c74cb86e4c62a6a1f5d`
- `00_s5_model_only.json`: `9733c15a047a185e591c8936d4f950ef68c256bbd03f1057ed5886903f5ab928`
- `01_s5_model_only.json`: `23825b3e4e70274ca7fb61097b38fce0db4b1f0615a43fae01bb43b37cee2572`
- `02_s5_model_only.json`: `62c84f81209bbf21069a006768049db0f1c51792a0c9de97f7bdf035e4a0b341`
- `03_s5_model_only.json`: `be87b6012174aa2f4c1a0f247bda295b20b8aa5477b490b0a5884f8bc11075a8`

## Actual bounded candidate measurements

**All cases max_seed_trials=2000, max_strokes=200**. Candidate directions default 0/45/90/135°, widths1..10, length12/6/2/0 source px; source original resolutions are **not game logical coords**.

| DEV original | Source WxH | Opaque original px | Modeled potential covered | Guaranteed covered | Uncovered potential | Candidate strokes | Trials | Coverage % | Outcome |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| wV6VeZI9S1Y | 200×320 |64000|1575|1392|62425|13|2000|2.4609%|PARTIAL|
| Hello Kitty |311×360|72112|65|0|72047|12|2000|0.0901%|PARTIAL|
| EZAL |1235×1920|2371200|1637|1442|2369563|13|2000|0.0690%|PARTIAL|
| Pink Kitty |554×554|306916|1637|1442|305279|13|2000|0.5334%|PARTIAL|

This is **not** normalized quality comparison across originals, because global trial quota is spent locally and near-top-left before whole-region exploration. All full original imagery and detail/contours were inputs to the fresh source packet, but **protected_original_dot did not affect the S5-R1 greedy score**. At width1 a potential positive ink pixel may have zero ideal guaranteed full-cell area; this does **not** prove native absence. Full gameplay color quality, native compositing, source-over and exact CHALK NOT_RUN. No quality gates changed.

## Decision and explicit next

**S5-R1 E2 TECH PASS / coverage for complete images QUALITY PARTIAL.** The S5-R1 first-seed greedy is not suitable for promotion; 2000 trials yield only ~12-13 stroke candidates. No ROI/color micro-tuning allowed to repair this structural defect. Preserve original R1 and its negative data as comparison baseline. **NEXT S5-R2**: preregister exactly one **region-first fair candidate scheduler** before new code: verified S4.6 source regions, protected dot priority, fair initial proposals across regions, EDT/shape-aware selection, multiple directions widths1..10 and independently checked potential footprint; global residual ledger and bounded budget with honest PARTIAL. Reuse existing capsule oracle and current original→S4.6 harness. When E2 permits, compare same four original fresh double-run and the simple geometric suite; actual native S5 E3 to follow valid source-owner/native calibration. Do not declare source-native readiness from these data.

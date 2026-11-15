# ENGINE-001 / V34R — amended PNG metadata-independent replay validation

**2026-11-15. Status PREREGISTERED / NOT_RUN.** Amended validation protocol with separate experiment ID, created **after** V34 run43738303188 FAIL, before any V34R run. This does **not** rewrite frozen V34 experiment or its failure. No change to drawing candidate, original source, width2 geometry, controls, color medians, MAE definitions, acceptance thresholds or quality gates.

## Evidence motivating new ID

V34 [CI43738303188](https://github.com/Kiddos19882/AutoDraw/actions/runs/43738303188), SHA `5bd5d9a797355698c67ef63d07c75391a7cef437`: workflow completed **FAIL** in native comparison due to strict byte-for-byte `V34-A-composite.png` SHA mismatch versus V33. Dependencies and original artifacts retrieved PASS, Node test 20/20 PASS, six V34 Python regression tests PASS, native actual Egret WebGL produced ten PNGs (5 A, 5 B) before FAIL; partial artifact14170739558 ZIP SHA `6d455f5016260e2d5a931b328eac81de37e9b69370782bfb39e9a30217993ec9`. The V33 control PNG and V34 A PNG have identical dimensions, **all decoded RGBA pixels equal** across composite and 4 isolated-color layers, and all PNG IHDR and IDAT chunks equal. Only ancillary private `deBG` 16-byte content differs (composite `85790CC84A526E2E` vs `385057BFA4A19EF1`). Thus byte-hash equality is too strict for rendered image equivalence in this native environment; this **does not** justify relaxing per-pixel/native acceptance.

Independent diagnostic from failed V34 native files: V33-A logical source RGB MAE 14.756601851851851 and V34-B 14.088824074074074; warm HSV H5..55°,S>=0.30,V>=0.20 source-pixel MAE A34.87417967866033 vs B31.21305725277212, n=2946, on original 150x240 ROI. These are **post-failure exploratory diagnostics**, not confirmatory V34R PASS.

## Frozen controls and revised *validation only*

Reuse exact original V34 prereg [protocol](ENGINE001_NATIVE_WARM_COLOR_V34_PROTOCOL_2026-11-15.md): V33 SHA386c8c24 native reference and V29 original plan SHA; width2 paths, all 1945 strokes, 3890 synthetic vertices (447 x+0.25 shim); deterministic source median class4–7, unchanged 150x240 ROI. Candidate only alters RGB.

For each A native PNG (composite and color4/5/6/7) compared to immutable V33 reference PNG:
- Decode both as RGBA arrays and require shape exactly 720x1380x4, **pixel-for-pixel identity on all four channels**, no tolerance, no changed alpha threshold, no color delta;
- additionally require exact equality of PNG `IHDR` and every `IDAT` byte sequence if present, to demonstrate the discrepancy truly concerns only ancillary non-pixel chunks; preserve PNG raw hashes and explicitly record list of differing ancillary chunks including `deBG`;
- require A/B native alpha arrays equal at **all** pixels for each five scenes; retain V33 24/128 recall, wrong color class overlap and exterior ROI metrics, check all counts vs frozen V33 report;
- retain same full source ROI RGB MAE and warm-region MAE metrics and stricter lower-than-both decision. Original production coverage >=99% per-class and <=3 logical-px constraints remain, not retuned.

Refuse and report `FAIL` on **any** actual decoded RGBA discrepancy between frozen V33 and A. Never silently ignore any pixel difference. On PASS, report metadata byte mismatch explicitly as image-equivalent, not byte-identical, and retain original V34 failed run as negative infrastructure evidence.

## Validation plan

Pre-run source hashes, exact immutable source and V33 inputs. Add regression test that encodes two PNGs identical in RGBA/IDAT but different private ancillary `deBG` metadata and verifies accepted pixel-equivalent yet byte-different, plus one pixel-altered rejection. New opt-in CI after runner change with native Egret Windows, full artifacts and hashes, compare both actual A/B. No production changes, no E4/live, exact CHALK or E5. Resource count synthetic not game CHALK; complete color quality remains FAIL until proven.

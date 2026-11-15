# ENGINE001_ANILINES_V19_MISSING_DETAIL_AND_COLOR_AUDIT — preregistered diagnostic

**Task:** ENGINE-001. **Registered:** 2026-11-15 BEFORE new V19 images/measurements. **Status:** PREREGISTERED/NOT_RUN. Audit of frozen V18-B, not a new geometry variant. No paths/paint changed.

## Pinned controls / hypothesis
Immutable source 200×320, 97308 bytes SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`; genuine frozen V14 AniLines Detail output SHA256 `2d4220381e18a86400e4afa950caa064ada5fe1adc821c9a230239cb91848f3b`; V18 [E3 run 43677851946](https://github.com/Kiddos19882/AutoDraw/actions/runs/43677851946), SHA `3b23cea2df90a8383d5b2fe51c324af7623e271c`, artifact `14147096853`. Read frozen `B-source-path-mask.png`, `B-paths.json` and `report.json`; refuse mismatched SHA. Never recompute or retune V18-B during V19 audit.
H1: missed skeleton pixels cluster near junctions/short clothing and facial details. H0: misses are diffuse or visually negligible. Neither source ROI nor source gray intensity is a human-labeled jacket mask.

## Fixed metrics (original 200×320 first)
- Reference skeleton = `skimage.morphology.skeletonize(AniLines L<128)`. B prediction mask = frozen V18 `B-source-path-mask.png > 0` grayscale. Covered skeleton pixels = reference intersect 3×3 dilation of B mask. Missed = reference AND NOT covered. Strict conservation check covered+missed=reference count.
- 8-connected components of missed, bins sizes 1, 2, 3–4, 5–9, >=10; top30 by size descending then source (y,x). Fixed source ROI x:[100,200),y:[62,251) and other pixels by subtraction, not semantic cloth segmentation.
- Mark missed as near-junction proxy when within 2 Chebyshev source pixels of any 8-neighbor original skeleton degree>=3 pixel. Compare to other missed pixels. Original-graph junction proxy does not mean causal explanation of missed lines.
- Dark interior proxy = RGB grayscale<105 eroded with 5×5 all-ones kernel; count missed and reference pixels within it, separately in mixed-content ROI.
- Reproduce frozen V5 logical 460×240 white canvas, pinned original resize with Pillow LANCZOS to 150×240 at (155,0), global MEDIANCUT palette 8 classes, no dither. For every non-white B logical preview pixel inside ROI 150×240, record owner palette label. Risk proxies: 3×3 neighborhood with multiple palette classes and 3×3 containing background label. These ARE NOT per-color cross-paint errors, real game brush width or 3px boundary validation.
- Save PNG: exact source/resized source, missed red overlay, source misses binary, color-risk overlay, four-panel comparison; `report.json` includes versions, exact source hash, exact frozen B mask/path hashes, all image hashes and counts.
- No new lines or changed thresholds in V19. Mark negative findings. Test source/hash, missed/covered conservation and ROI, boundary risk computation and palette label correctness. If unavailable source/artifact or mismatched SHA, fail-closed.

**Gate:** E2/E3 offline reproducibility only; V19 cannot improve image quality because geometry unchanged. New separately preregistered ID required before restoring any short fragments or connecting gaps. Existing fill quality >=99%, 3 logical px boundary diagnostics, CHALK exact game pointCount delta, native E4 and E5 unaffected. Production, executor, monitor, Bridge, `master` untouched.

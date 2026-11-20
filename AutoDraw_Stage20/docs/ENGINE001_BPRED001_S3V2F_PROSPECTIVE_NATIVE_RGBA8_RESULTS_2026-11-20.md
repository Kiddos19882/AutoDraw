# ENGINE-001 / BPRED-S3v2f — prospective NEW original Egret Canvas2D→WebGL and owner C0

**2026-11-20. E2/E3 technical PASS, scientific H1 (stage QH) PASS, scientific H2 (ordered two-color C0) FAIL.** Original frozen [S3v2f E0](ENGINE001_BPRED001_S3V2F_PROSPECTIVE_NATIVE_RGBA8_PREREG_2026-11-20.md) Git blob `24259eeeadb9451c43390bdcf5a01fb67c7cf39a` committed as `23b0d062fbabb9c451ed50ebe76f2095922d4f6c` BEFORE S3v2f code or new native evidence. No S0 BLIND or source threshold changes. Native CI [#44710870514](https://github.com/Kiddos19882/AutoDraw/actions/runs/44710870514), exact code SHA `819b7fd20272e5ac87ead72ce0610687fa51cbf4`. Raw [artifact14617442073](https://github.com/Kiddos19882/AutoDraw/actions/runs/44710870514/artifacts/14617442073).

## Genuine E3 and controls

- Authentic original `BoardPane` Egret5.4.1/WebGLRenderer game/renderer Git blobs `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`/`76d950e0a8911888a9df3b675b866519ecf7bba4`, pinned original Firefox159.0, board 460×240 logical/1380×720 physical; pinned prereg and **11/11 source Git blobs verified** before test.
- 80 **new** primary width1..10 × CROSS_ROTATED/NEAR_SKEW × A_ONLY/B_ONLY/A_THEN_B/B_THEN_A, angle and fractional position by frozen width, two true source RGB palettes (one new); none from historical S3v2d plans or S0 BLIND. Original Egret emitted 80 main Canvas1392×732 and 80 independent mask Canvas1380×720 PNG, plus 80 true final WebGL PNG. 10 replay native WebGL RGBA ROI pixel-exact to corresponding primary and 1 alpha0 blank: **91 final PNG**. Replays are checked on the declared 162×162 stroke ROI, NOT incorrectly claimed as full-frame exact; full source/main data otherwise archived.
- All **80** original main Canvas uploads directly observed as exactly one `WebGLRenderingContext.texImage2D(HTMLCanvasElement)` each, source 1392×732; `UNPACK_PREMULTIPLY_ALPHA_WEBGL=true`, `UNPACK_COLORSPACE_CONVERSION_WEBGL=37444`, `UNPACK_ALIGNMENT=4` in all 80 cases. Methods are delegated unchanged and restored `try/finally`; GL state is only observed, not modified. Observing the GL upload is important mechanistic evidence but does not alone prove internal rounding instruction or owner compositing.
- E2 12 new S3v2f + 8 prior S3v2e +14 S3v2 +14 S3 native = **48/48 PASS**, JS syntax and Markdown audit PASS. CI SHA-specific required job **SUCCESS**. Independently downloaded archived ZIP, ZIP CRC PASS, 656 entries/655 listed raw member SHA256 **PASS 655/655**; 80 exact manifest IDs and 20 pair rows/40 variants.

## D1 — unchanged-alpha real Canvas→WebGL, prospectively tested fixed QH

For each of all 80 new full 1380×720 RGBA images, compare actual true Canvas main (aligned by original node transform) with genuine WebGL. Frozen `Q0` identity; `QC` pre-multiply `ceil(c*a/255)` then un-multiply nearest-even `rint(255*p/a)`; **QH** same pre-multiply then un-multiply **half-up** `floor(255*p/a+0.5)`. At alpha0/255 preserve source RGB, never alter alpha. These choices and primary H1 **zero** target were frozen BEFORE new E3.

| Candidate on new original Egret | RGB-different physical pixel occurrences (80 images) | Physical alpha differences |
|---|---:|---:|
| Q0 original Canvas identity | 17 001 | 0 |
| QC frozen old candidate | 131 | 0 |
| **QH new predeclared candidate** | **0** | **0** |

**Scientific H1-QH PASS** (0/80 scene failures; zero pixel discrepancies), consistent with byte-precision premultiply/unpremultiply in this exact Firefox159/Egret source path. It is not proof of all browsers/versions, not a guarantee for path combinations outside these 80 novel cases, and not a full brush/owner predictor. No original H1 source-over failure was reclassified.

## D2 — same strict ordered two-owner C0: scientific H2 FAIL

For each of 40 frozen ordered AB/BA, original unchanged `s3.source_over` is applied to genuine isolated **Canvas** A/B, with Q0/QC/QH, then compared against actual ordered WebGL. **Unchanged** numerical H1 per variant requires both `max_channel_byte≤2` AND `mean_channel_byte≤1` within original union ROI.

| Original source-over path / target | Variants passing numerical H1 /40 |
|---|---:|
| True isolated main Canvas A/B C0 → true ordered Canvas | **23/40** (17 FAIL) |
| True isolated final WebGL A/B C0 → true ordered WebGL | **5/40** (35 FAIL) |
| True isolated main Canvas A/B C0, Q0 → final WebGL | 0/40 |
| True isolated main Canvas A/B C0, QC → final WebGL | **14/40** |
| True isolated main Canvas A/B C0, **QH** → final WebGL | **14/40** (**26 FAIL**) |

Frozen H2-QH required **at least30/40**; **FAIL (14/40)**. Accuracy of RGB8 stage alone does not solve physical Canvas source-over blending or the loss of premultiplied precision through isolated PNGs. The source scientific failures are preserved: original S3 H1 **30/40 FAIL**; prior S3v2d main Canvas **2/40 FAIL**, final WebGL **30/40 FAIL**. New hard cases differ; never compare percentages as same population or claim S3 safe.

The 26 new ordered QH failures span **every width 1..10**, both families (CROSS_ROTATED12, NEAR_SKEW14); worst **W05 NEAR_SKEW B_THEN_A** has max channel error **64**, mean0.02208, 59 different physical ROI pixels. W05 NEAR_SKEW A_THEN_B max32, mean0.01570, 65 different physical ROI pixels. The first worst actual Canvas-vs-C0 pixel forensic (known AFTER test; research diagnostic only) at ROI pixel (61,61) is predicted [159,32,96,8] vs native Canvas [146,0,73,7], so alpha error 1 and RGB error32 already arise before WebGL. These are *not* 64 pixel leakages or new allowed thresholds.

## Interpretation / next within agreed plan

Khronos [WebGL 1.0 specification](https://registry.khronos.org/webgl/specs/latest/1.0/) and [HTML Canvas standard](https://html.spec.whatwg.org/multipage/canvas.html) describe premultiplied-alpha conversion and information loss for semi-transparent colors. Historical [Mozilla bug 662130](https://bugzilla.mozilla.org/show_bug.cgi?id=662130) discusses integer alpha premultiplication and rounding; it is background, **not proof of Firefox159 current source internals**. Actual S3v2f GL observation directly verifies `UNPACK_PREMULTIPLY_ALPHA_WEBGL=true` with a true main Canvas source on all 80 new cases, whereas precise internal behavior remains inferred from pixels.

**Scientific decision: S3 PARTIAL; do not promote source-over C0 or M2 to production.** RGB texture-stage QH is now independently tested on novel S3 native cases with H1 PASS; remaining research target is the **Canvas2D two-owner internal compositing/reconstruction**, not new ad-hoc corrections to texture QH. Separate prospective prereg required before new model/threshold experiments. Future solution must quantify uncertainty if isolated unpremultiplied PNG cannot uniquely identify premultiplied color. Any direct changes to S3v2e prior history are forbidden. Original protected E/F P4D18 quality FAIL; S0 BLIND untouched, Stage6/executor/Monitor/Bridge/master/production unchanged. No E4 live, E5 independent or run-bound exact CHALK; `post.pointCount - pre.pointCount` not measurable from these synthetic native scenes.

**Single next unfinished step:** freeze separate S3v2g Canvas2D integer-premultiplied-alpha / source-over diagnostic E0, use S3v2f raw as **known diagnostic/calibration** only (not new holdout), then test carefully bounded source-over arithmetic candidates, preserve all 26 failed variants and actual native owner impacts. Do not open S0 BLIND or proceed to S4 until scientifically supported safety.

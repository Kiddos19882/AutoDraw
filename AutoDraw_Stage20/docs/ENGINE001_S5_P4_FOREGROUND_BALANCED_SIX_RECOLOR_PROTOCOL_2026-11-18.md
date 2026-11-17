# ENGINE-001 S5-P4 — foreground-balanced six-color pretrained RGB recolor

**ID:** `ENGINE001_S5_P4_FOREGROUND_BALANCED_SIX_RECOLOR`. Preregistered 2026-11-18 **before implementation and neural inference**. Separate result from S5-P3. User permits research, development, documentation and CI; no production promotion.

## Hypothesis and baseline

S5-P3 used whole-source MEDIANCUT on original RGB, obtaining 4/6 nearwhite conditioning colors, and reported a loss of nearwhite background and orange-to-olive drift. Test whether **one explicitly reserved nearwhite background color and five source-foreground colors** selected using the pretrained BiRefNet foreground mask improve subjective recognizability and preserve source saturation versus frozen S5-P3, using **the same** original RGB, pinned Recolorization-Pro code/checkpoint and six-color interface. This is a hypothesis, not a proven cause of P3 failure. Neural image generation must be genuine; mask and palette selection must be reported as separate steps.

## Immutable inputs and provenance

- Original `AutoDraw_Stage20/testImages/wV6VeZI9S1Y.png`, original RGB 150×240, SHA256 `07cc4568cb5e90d9514bc6f6c2112fee623f87f8fd0cea02fa517b04108e502a`; do not use G32 as color input.
- Frozen S5-P3 reference: CI [44151445030](https://github.com/Kiddos19882/AutoDraw/actions/runs/44151445030), report SHA256 `af1db29cc66368fca388daafa424aa742c908b7e67b504c6da42f94ce07e5583`, 15890 distinct output RGB, nearwhite proxy 0, source mean ΔE00 8.1148479, p95 18.9549259; visual decision PENDING. Never regenerate this P3 result under the old ID.
- Foreground source: **actual** pretrained `birefnet-general-lite` ONNX via existing S5-P2 runner with checkpoint MD5 `4fab47adc4ff364be1713e97b7e66334` and SHA256 from P2 reference `5600024376f572a557870a5eb0afb1e5961636bef4e1e22132025467d0f03333`; must fail closed on checksum change. Mask is guidance, not ground truth.
- Same pretrained Recolorization-Pro upstream Git SHA `4ef126095ad21394deabf72db807aeb3e728b553` and original `checkpoint_epoch_90.pt` SHA256 `525144a0022ea43096079b8a27f1d4bbb7768dfdcae98444b5275de4ac536321`, 118010004 bytes. Fail closed on checksum drift. Unverified upstream license means **research-only**; no deployment or committing upstream code/weights.

## Method fixed before results

1. Reuse S5-P2 `run()` to produce the genuine alpha mask on exactly the original RGB. Fixed threshold alpha >=128. Save alpha PNG and metadata; no manual painting/labels or arbitrary guessed foreground.
2. Reserve exactly one background conditioning color: deterministic median RGB of source pixels with alpha <128 **and** all RGB channels >=245 (nearwhite proxy). If no such pixels, fail closed instead of inventing white. This reference background is a *source-derived color*, not a forced postprocessing patch.
3. Select five further colors from source **alpha >=128** and **not nearwhite**, using weighted foreground chroma/saliency sampling: quantize foreground to candidate buckets, rank by pixel support with a controlled chroma boost, and greedily choose diverse representative colors (minimum perceptual/RGB separation) with deterministic tie breaks. Exact sampling and weights are fixed in the committed runner before inference; never retune after inspecting P4 output. No whitening/replacement of network output pixels. If selection is degenerate, fail closed.
4. Provide six unique RGB colors in a deterministic order to the **unchanged** real pretrained Recolorization-Pro inference code. No game32 quantizer, no training, no fallback rendered illustration. Save source, foreground alpha, palette strip+JSON, neural RGB and 3x side-by-side PNG. Preserve raw, uncorrected network RGB even if background is poor.

## Predeclared evidence, controls, and decision

- Unit contracts: deterministic exactly six distinct source-derived colors, one nearwhite background, foreground candidates diverse, shape checks, invalid mask failures, no output overwrite, checkpoint hashes, immutable input, no painted fallback. A unit PASS is not pretrained E3.
- Pretrained E3 technical PASS requires original/mask/model checkpoint SHA verification, actual ONNX inference and real pretrained RGB inference, nonidentity RGB result, ZIP/report hashes, CI SHA/run linkage.
- Report source-relative mean/p95 ΔE00; exact RGB distinct-count; original/result nearwhite count at >=245 RGB; output chroma/saturation statistics and foreground/background region breakdown. Compare to frozen P3 metrics explicitly; these are **diagnostics**, not automatic quality acceptance. Never claim model color improvement on aggregate ΔE alone.
- **Visual acceptance remains pending user inspection:** face, pose, orange details, background, color separation, fine detail, paired P3/P4 comparison. Without P3 PNG available, show source/P4 and label P3 metrics as historic, not pixel-by-pixel comparison.
- Keep all historic game32 source thresholds and S5-P3 artifact unchanged. Original V44-B **410 strokes / 1792 vertices LAST** untouched and NOT overlaid on S5-P4 pure-color preview. No Stage6, production CHALK estimator, executor defaults, game E4/E5 or exact CHALK changes. S5-P4 is exploratory visual RGB only.
- If a remote model/download/license/quality check fails, preserve negative report, mark BLOCKED/FAIL rather than silently substituting a mathematical recolor. Next iteration requires a **new** experimental ID.

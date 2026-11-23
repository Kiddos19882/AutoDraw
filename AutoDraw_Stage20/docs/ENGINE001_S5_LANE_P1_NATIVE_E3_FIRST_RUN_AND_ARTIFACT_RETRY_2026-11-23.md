# ENGINE-001 / S5-LANE-P1 — first native 180-case result, raw artifact missing (2026-11-23)

**Experiment** `ENGINE001_S5_LANE_P1_NATIVE_ADJACENT_STROKE_SPACING_V1`. Frozen before running: [protocol](ENGINE001_S5_ADJACENT_LANE_NATIVE_SPACING_PREREG_2026-11-23.md). **Branch** `feature/image-geometry-optimization`. Original code and workflow SHA [`14a69353825501cf4ba4f9df10f673949b9e0d2a`](https://github.com/Kiddos19882/AutoDraw/commit/14a69353825501cf4ba4f9df10f673949b9e0d2a). **Exact run** [45087460920](https://github.com/Kiddos19882/AutoDraw/actions/runs/45087460920), job `137409222428` completed **success**. Original frozen engine blob `46cc74de00b6cb5d207b1e1a2ffcd81613b6d388`, renderer blob `76d950e0a8911888a9df3b675b866519ecf7bba4`.

## What was actually proven

Live Actions job logs independently fetched; original test runner output `S5_LANE_P1_NATIVE_PASS 180 180 180`, validation step output `S5_LANE_P1_E3_SIGNED 180 541 180 180`. Python unit test `Ran 5 tests ... OK`, all mandatory workflow steps success. The validated ephemeral runner workspace held 180 case records, 541 native PNG captures, report member SHA256 verification and source/renderer pins. At alpha≥24, **180/180** analyzed configurations had zero missed backing pixels in the **inter-centerline strip** of 20 logical length; at alpha≥128, **180/180** also zero missed pixels. Tested widths1..10, angles0°,45°,90°, centerline distances ratios0.75/0.90/1.00 to nominal width, two XY phases; no change to E0, thresholds or algorithm.

**Coverage qualification:** gaps checked only **between the two lane centerlines**, along a trimmed axial strip; not the outside edges of painted pair, contours, bends, long multi-lane composites, all phase/angle combinations, or protected foreign-color pixels. A matching 100% on this particular mask does NOT establish full-source image coverage. Effective-width E2 and this native E3 cannot validate current real game state E4/E5, exact CHALK, Stage6 admission or game painter coordinate calibration.

## Evidence failure (do not mark artifact PASS)

GitHub Actions [job log 137409222428](https://github.com/Kiddos19882/AutoDraw/actions/runs/45087460920/job/137409222428) at `2026-11-23T00:15:12Z` shows:

`##[warning]No files were found with the provided path: AutoDraw_Stage20/.s5-lane-p1-native. No artifacts will be uploaded.`

Cause: upload-artifact v4 excludes hidden-dot directory with default `include-hidden-files: false`; `if-no-files-found: warn` meant technical job still returned success. Run's GitHub API artifacts list returned **0**. **Full raw evidence retention and independent ZIP SHA/PNG content review: FAIL/BLOCKED** for this first run; 180/180 summary is log-verified, not independently audited from downloaded PNG. Preserve as non-final E3 log evidence, NOT a complete signed/archived E3 acceptance.

**Minimal workflow-only correction:** [commit `9296a3434b43ec6c4936ae66a3e99adc347b63a6`](https://github.com/Kiddos19882/AutoDraw/commit/9296a3434b43ec6c4936ae66a3e99adc347b63a6) updates only `.github/workflows/engine001-s5-lane-p1-native-spacing.yml` with `include-hidden-files: true` and fail-closed `if-no-files-found: error`. Native geometry, runner, E0, source owner and thresholds unchanged. **Corrected-run status: UNKNOWN pending actual new run ID, exact required job and downloadable ZIP**. Note GitHub REST Actions collection includes the original successful run, whereas commit-associated PR-only workflow tool returned empty; absence in PR-only query is not proof no run exists.

**Single next:** locate the corrected push-triggered GitHub Actions run at exact commit SHA `9296a343`; if completed, download new ZIP, verify CRC, JSON SHA membership, 541 raw PNG and case-level gap results, preserve failures. Only after evidence qualification freeze S5-R4 repeated-region-lane E0 with measured stride; leave game execution and exact CHALK blocked. No user desktop execution performed.

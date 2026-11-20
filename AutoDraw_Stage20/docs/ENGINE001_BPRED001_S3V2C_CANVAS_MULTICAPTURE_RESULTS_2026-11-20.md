# ENGINE-001 / BPRED-S3v2c — результаты настоящего Egret multi-Canvas trace (2026-11-20)

**Технический итог: E2/E3 PASS, научной H1 в этом структурном протоколе нет.** Frozen [E0 S3v2c](ENGINE001_BPRED001_S3V2C_CANVAS_CAPTURE_TRACE_PREREG_2026-11-20.md) был зафиксирован до источников. Успешный [CI44687444859](https://github.com/Kiddos19882/AutoDraw/actions/runs/44687444859) source SHA \`66351d251710aa7f263edf9f3617b8f3f75675d5\`, Egret5.4.1 original BoardPane, explicit Firefox159.0 Windows; raw [artifact14606962926](https://github.com/Kiddos19882/AutoDraw/actions/runs/44687444859/artifacts/14606962926). 5 S3v2c E2+14 original S3 E2 PASS, Markdown integrity PASS, provenance game/renderer/source SHA PASS.

## 8 original scenes, 16 distinct genuine Canvas2D snapshots

Original frozen S3 source scenes: width1/10 × CROSSING/NEAR_PARALLEL_OVERLAP × A_ONLY/A_THEN_B. Each one yielded **exactly 2 original CanvasRenderer.renderGraphics calls**. Eight final native WebGL PNG were validated against original frozen S3 parent PNG using independently frozen S3v2b deBG-only provenance and full RGBA equivalence. Parent original S3 BLIND was never opened. Raw ZIP contains 44 members; ZIP CRC valid; 43/43 report member SHA256 exact; 16 Canvas PNG +8 final WebGL true original.

**First original Canvas (all 8):** graphics main BoardPane node \`x=-2,y=-2,width=464,height=244\`, original context canvas1392×732 physical, true transform \`[3,0,0,3,6,6]\`, drawDataCount=3 for one A stroke and4 for two A/B strokes. **Second Canvas (all 8):** separate mask node \`x=0,y=0,width=460,height=240\`, 1380×720 physical, transform \`[3,0,0,3,0,0]\`, drawDataCount=1. This is not two copies of the same canvas: per-scene equality of full node geometry false and dimensions different in all8 cases. Do NOT select a snapshot by chronological order alone; the actual source node properties explain the original S3v2b strict one-capture technical BLOCKED.

The earlier P4D15 instrumentation only captured \`drawData.length>10\` for its 21 strokes, excluding the one-command mask; with source S3 one/two strokes, exact owner node has just 3/4 commands, so naïve \`drawData.length>0\` captured both. This is explanation of *instrumentation ambiguity*, NOT proof of physical RGB/alpha compositing mechanism; old S3 C0 H1 **FAIL30/40** preserved.

## Evidence/boundaries/next

- Research-only (ф) \`tests/engine001_bpred_s3v2c_multicapture_trace.js\`, (ф) \`tests/run_engine001_bpred_s3v2c_multicapture_trace.py\`, (ф) \`tests/test_engine001_bpred_s3v2c_multicapture_trace.py\`, (ф) \`.github/workflows/engine001-bpred-s3v2c-multicapture-trace.yml\`; original Egret source game and renderer not modified. First CI44686921486 technical BLOCKED because Selenium chose wrong Firefox, despite installed version; explicit runtime binary binding fixed only scope of research harness, source SHA66351d final PASS.
- Original S3v2 [CI44684709364](https://github.com/Kiddos19882/AutoDraw/actions/runs/44684709364) byte-unequal blank still FAIL; S3v2b [CI44686065270](https://github.com/Kiddos19882/AutoDraw/actions/runs/44686065270) duplicate Canvas capture BLOCKED. Negative evidence preserved, no false safety claim.
- **NEXT:** preregistered before S3v2d code [full S3v2d true main-node stage](ENGINE001_BPRED001_S3V2D_MAIN_NODE_STAGE_PREREG_2026-11-20.md), 80 S3 cases, 80 main +80 mask actual source PNG,91 true WebGL, original C0 per-channel H1 unchanged max≤2/255/mean≤1/255. Source-derived geometry selection fixed before full results; no adaptive acceptance or stage S4 release.

P4D18 original protected quality FAIL, original H1 H2 retained; S0 independent BLIND unused. Game E4/E5 and exact game CHALK NOT_RUN. master/production/Stage6/Monitor/Bridge unchanged.

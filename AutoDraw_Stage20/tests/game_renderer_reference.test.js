"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  buildSmoothPathCommands,
  buildNormalPathCommands,
  terminalPoint,
  shouldWebGLRendererRasterize,
  extractAcceptedPoints,
  extractTemporalStrokes,
  extractFill001SeriesStrokes,
  buildStagePlacement,
  buildStageRendererTransform
} = require("./game_renderer_reference.js");

test("smooth one-point path contains moveTo only and has no segment endpoint", () => {
  const points = [{ x: 4, y: 7 }];
  const commands = buildSmoothPathCommands(points, true, false);

  assert.deepEqual(commands, [
    { type: "moveTo", x: 4, y: 7 },
    { type: "moveTo", x: 4, y: 7 }
  ]);
  assert.equal(terminalPoint(points, true, false), null);
});

test("smooth two-point path terminates at the midpoint when final line is disabled", () => {
  const points = [{ x: 10, y: 20 }, { x: 30, y: 40 }];
  const commands = buildSmoothPathCommands(points, true, false);

  assert.deepEqual(commands.at(-1), { type: "lineTo", x: 20, y: 30 });
  assert.deepEqual(terminalPoint(points, true, false), { x: 20, y: 30 });
  assert.equal(commands.some(command => command.type === "lineTo" && command.x === 30 && command.y === 40), false);
});

test("smooth three-point path ends at the last pair midpoint, not the last point", () => {
  const points = [{ x: 0, y: 0 }, { x: 10, y: 20 }, { x: 30, y: 20 }];
  const commands = buildSmoothPathCommands(points, true, false);

  assert.deepEqual(commands, [
    { type: "moveTo", x: 0, y: 0 },
    { type: "moveTo", x: 0, y: 0 },
    { type: "lineTo", x: 5, y: 10 },
    { type: "curveTo", controlX: 10, controlY: 20, x: 20, y: 20 }
  ]);
  assert.deepEqual(terminalPoint(points, true, false), { x: 20, y: 20 });
});

test("normal zero-length segment retains an explicit lineTo to the same coordinate", () => {
  const points = [{ x: 100, y: 100 }, { x: 100, y: 100 }];
  assert.deepEqual(buildNormalPathCommands(points), [
    { type: "moveTo", x: 100, y: 100 },
    { type: "lineTo", x: 100, y: 100 }
  ]);
  assert.deepEqual(terminalPoint(points, false, false), { x: 100, y: 100 });
});

test("normal path includes the final accepted point", () => {
  const points = [{ x: 0, y: 0 }, { x: 10, y: 5 }, { x: 30, y: 15 }];
  const commands = buildNormalPathCommands(points);

  assert.deepEqual(commands, [
    { type: "moveTo", x: 0, y: 0 },
    { type: "lineTo", x: 10, y: 5 },
    { type: "lineTo", x: 30, y: 15 }
  ]);
  assert.deepEqual(terminalPoint(points, false, false), { x: 30, y: 15 });
});

test("WebGLRenderer skips GraphicsNode with empty bounds or empty drawData", () => {
  assert.equal(shouldWebGLRendererRasterize({ width: 0, height: 0, drawData: [{}] }), false);
  assert.equal(shouldWebGLRendererRasterize({ width: 10, height: 0, drawData: [{}] }), false);
  assert.equal(shouldWebGLRendererRasterize({ width: 10, height: 10, drawData: [] }), false);
  assert.equal(shouldWebGLRendererRasterize({ width: 10, height: 10, drawData: [{}] }), true);
});

test("empty paths produce no drawing commands", () => {
  assert.deepEqual(buildSmoothPathCommands([], true, false), []);
  assert.deepEqual(buildNormalPathCommands([]), []);
  assert.equal(terminalPoint([], true, false), null);
});

test("Painter.drawSmoothLine defaults drawLast to true", () => {
  const points = [{ x: 0, y: 0 }, { x: 10, y: 10 }];
  const commands = buildSmoothPathCommands(points);

  assert.deepEqual(commands.at(-1), { type: "lineTo", x: 10, y: 10 });
  assert.deepEqual(terminalPoint(points, true), { x: 10, y: 10 });
});

test("BoardPane explicitly passes drawLast=false to Painter.drawSmoothLine", () => {
  const points = [{ x: 0, y: 0 }, { x: 10, y: 10 }];
  const boardPaneCall = buildSmoothPathCommands(points, true, false);

  assert.deepEqual(boardPaneCall.at(-1), { type: "lineTo", x: 5, y: 5 });
  assert.deepEqual(terminalPoint(points, true, false), { x: 5, y: 5 });
  assert.equal(boardPaneCall.some(command =>
    command.type === "lineTo" && command.x === 10 && command.y === 10), false);
});

test("imports accepted points from a Game Monitor run without guessing missing points", () => {
  const run = {
    run_id: "run-1",
    events: [
      { type: "POINT_QUOTA_UPDATE", strokeId: "stroke-1", pointDelta: 1, acceptedPoint: { x: 12, y: 15 } },
      { type: "DRAW_SAMPLE", pointDelta: 2 },
      { type: "POINT_QUOTA_UPDATE", strokeId: "stroke-1", pointDelta: 1, acceptedPoint: { x: 18, y: 21 } }
    ]
  };
  assert.deepEqual(extractAcceptedPoints(run), [{ x: 12, y: 15 }, { x: 18, y: 21 }]);
});

test("rejects aggregated point updates because intermediate accepted coordinates are unknown", () => {
  assert.throws(() => extractAcceptedPoints({
    events: [{ type: "POINT_QUOTA_UPDATE", strokeId: "stroke-1", pointDelta: 2, acceptedPoint: { x: 12, y: 15 } }]
  }), /pointDelta must equal 1/);
});

test("rejects missing accepted-point coordinates and supports direct point arrays", () => {
  assert.throws(() => extractAcceptedPoints({
    events: [{ type: "POINT_QUOTA_UPDATE", strokeId: "stroke-1", pointDelta: 1, acceptedPoint: null }]
  }), /missing coordinates/);
  assert.deepEqual(extractAcceptedPoints([{ x: 1, y: 2 }]), [{ x: 1, y: 2 }]);
});

test("rejects runs containing more than one stroke", () => {
  assert.throws(() => extractAcceptedPoints({ events: [
    { type: "POINT_QUOTA_UPDATE", strokeId: "stroke-1", pointDelta: 1, acceptedPoint: { x: 1, y: 2 } },
    { type: "POINT_QUOTA_UPDATE", strokeId: "stroke-2", pointDelta: 1, acceptedPoint: { x: 3, y: 4 } }
  ] }), /exactly one identified stroke/);
});

test("Stage placement preserves the exact fractional backing origin and computes A-D rounding", () => {
  const profile = {
    stageWidth: 1314, stageHeight: 600,
    canvasBackingWidth: 3942, canvasBackingHeight: 1800,
    canvasScaleX: 3, canvasScaleY: 3,
    boardWidth: 460, boardHeight: 240,
    boardStageCorners: {
      topLeft: { x: 340.7916660308838, y: 72 },
      topRight: { x: 800.7916660308838, y: 72 },
      bottomRight: { x: 800.7916660308838, y: 312 },
      bottomLeft: { x: 340.7916660308838, y: 312 }
    }
  };
  const exact = buildStagePlacement(profile, false);
  const rounded = buildStagePlacement(profile, true);
  // Monitor geometry is fractional; allow only the observed binary-float rounding error.
  assert.ok(Math.abs(exact.x - 1022.375) < 3e-6);
  assert.equal(exact.y, 216);
  const exactTransform = buildStageRendererTransform(exact);
  const roundedTransform = buildStageRendererTransform(rounded);
  assert.equal(exactTransform.a, 3);
  assert.equal(exactTransform.d, 3);
  assert.ok(Math.abs(exactTransform.tx - 340.7916660308838) < 1e-9);
  assert.equal(exactTransform.ty, 72);
  assert.ok(Math.abs(exactTransform.tx * exactTransform.a - exact.x) < 1e-9);
  assert.equal(roundedTransform.tx * roundedTransform.a, 1022);
  assert.equal(roundedTransform.ty * roundedTransform.d, 216);
  assert.equal(exact.width, 1380);
  assert.equal(exact.height, 720);
  assert.equal(rounded.x, 1022);
  assert.equal(rounded.y, 216);
  assert.equal(exact.rounding, "exact_fractional_backing_origin");
  assert.equal(rounded.rounding, "nearest_backing_pixel");
});

test("Stage placement rejects mismatched backing scale and non-rectangular BoardPane corners", () => {
  const profile = {
    stageWidth: 1314, stageHeight: 600,
    canvasBackingWidth: 3942, canvasBackingHeight: 1800,
    canvasScaleX: 2, canvasScaleY: 3,
    boardWidth: 460, boardHeight: 240,
    boardStageCorners: {
      topLeft: { x: 340, y: 72 }, topRight: { x: 800, y: 72 },
      bottomRight: { x: 800, y: 312 }, bottomLeft: { x: 340, y: 312 }
    }
  };
  assert.throws(() => buildStagePlacement(profile, false), /Backing dimensions do not match/);
  profile.canvasScaleX = 3;
  profile.boardStageCorners.bottomRight.x = 801;
  assert.throws(() => buildStagePlacement(profile, false), /axis-aligned rectangle/);
});

test("Stage placement rejects BoardPane geometry outside the backing canvas", () => {
  const profile = {
    stageWidth: 1314, stageHeight: 600,
    canvasBackingWidth: 3942, canvasBackingHeight: 1800,
    canvasScaleX: 3, canvasScaleY: 3,
    boardWidth: 460, boardHeight: 240,
    boardStageCorners: {
      topLeft: { x: 1000, y: 72 }, topRight: { x: 1460, y: 72 },
      bottomRight: { x: 1460, y: 312 }, bottomLeft: { x: 1000, y: 312 }
    }
  };
  assert.throws(() => buildStagePlacement(profile, false), /falls outside/);
});


test("ENGINE-001 temporal sample extraction validates identity, CHALK and order", () => {
  const run = {
    record_type: "autodraw_game_monitor_run", execution_status: "completed",
    point_delta_matches_chalk: true, stroke_count: 2, observed_brush_radii: [10],
    dropped_events: 0, monitor_buffer_dropped_events_delta: 0,
    monitor_error_count_delta: 0, bridge_send_failures_delta: 0,
    collector_sequence_gap_count: 0, run_id: "test-run", session_id: "test-session",
    pre_test_snapshot: { isExact: true, logicalWidth: 460, logicalHeight: 240, pointCount: 1 },
    post_test_snapshot: { isExact: true, logicalWidth: 460, logicalHeight: 240, pointCount: 4 },
    accepted_points: [
      { t: 1, stroke_id: "a", point_delta: 1, x: 1.5, y: 2 },
      { t: 2, stroke_id: "a", point_delta: 1, x: 3.5, y: 2 },
      { t: 3, stroke_id: "b", point_delta: 1, x: 4.5, y: 6 }
    ]
  };
  const result = extractTemporalStrokes(run);
  assert.equal(result.exactChalk, 3);
  assert.deepEqual(result.strokes.map(s => s.points.length), [2, 1]);
  assert.equal(result.strokes[0].points[0].x, 1.5);
  for (const [description, mutate, error] of [
    ["coalesced", r => { r.accepted_points[0].point_delta = 2; }, /Invalid ordered/],
    ["missing coordinate", r => { r.accepted_points[0].x = null; }, /Invalid ordered/],
    ["invalid CHALK", r => { r.post_test_snapshot.pointCount += 1; }, /exact run-bound CHALK/],
    ["interleaving", r => { r.accepted_points[2].stroke_id = "a"; r.accepted_points[1].stroke_id = "b"; }, /Interleaved/],
    ["dropped events", r => { r.dropped_events = 1; }, /telemetry loss/],
    ["brush mismatch", r => { r.observed_brush_radii = [30]; }, /brush width/]
  ]) {
    const copy = structuredClone(run);
    mutate(copy);
    assert.throws(() => extractTemporalStrokes(copy), error, description);
  }
});

test("ENGINE-001 imports complete run-bound fractional accepted points without quota events", () => {
  const run = {
    record_type: "autodraw_game_monitor_run", execution_status: "completed",
    run_id: "run", session_id: "session", chalk_experiment_matrix: { phase_id: "ENGINE001" },
    point_delta_matches_chalk: true, stroke_count: 1, observed_brush_radii: [10],
    dropped_events: 0, monitor_buffer_dropped_events_delta: 0,
    monitor_error_count_delta: 0, bridge_send_failures_delta: 0, collector_sequence_gap_count: 0,
    pre_test_snapshot: { isExact: true, logicalWidth: 460, logicalHeight: 240, pointCount: 1 },
    post_test_snapshot: { isExact: true, logicalWidth: 460, logicalHeight: 240, pointCount: 3 },
    renderer_geometry_at_start: { engineVersion: "5.4.1" },
    renderer_geometry_at_end: { engineVersion: "5.4.1" },
    observed_stroke_modes: [{ stroke_id: "s", stroke_option_raw: true }],
    accepted_points: [
      { t: 10, stroke_id: "s", point_delta: 1, x: 74.20833396911621, y: 119 },
      { t: 20, stroke_id: "s", point_delta: 1, x: 76.20833396911621, y: 119 }
    ],
    events: [
      { type: "DRAW_SAMPLE", source: "state_poll", pointDelta: 1, strokeId: "s", t: 10,
        acceptedPoint: { x: 74.20833396911621, y: 119 } },
      { type: "DRAW_SAMPLE", source: "state_poll", pointDelta: 1, strokeId: "s", t: 20,
        acceptedPoint: { x: 76.20833396911621, y: 119 } }
    ]
  };
  assert.deepEqual(extractAcceptedPoints(run), [
    { x: 74.20833396911621, y: 119 }, { x: 76.20833396911621, y: 119 }
  ]);
  for (const [label, mutate, error] of [
    ["missing draw", r => { r.events.pop(); }, /DRAW_SAMPLE/],
    ["tampered draw", r => { r.events[0].acceptedPoint.x += 1; }, /DRAW_SAMPLE/],
    ["coalesced delta", r => { r.events[0].pointDelta = 2; }, /DRAW_SAMPLE/],
    ["wrong native mode", r => { r.observed_stroke_modes[0].stroke_option_raw = false; }, /smooth=true/],
    ["changed geometry", r => { r.renderer_geometry_at_end.engineVersion = "5.5"; }, /geometry/],
    ["invalid CHALK", r => { r.post_test_snapshot.pointCount++; }, /exact run-bound CHALK/]
  ]) {
    const changed = structuredClone(run); mutate(changed);
    assert.throws(() => extractAcceptedPoints(changed), error, label);
  }
});

test("FILL001 replay validates normal multi-stroke coordinates and exact chalk", () => {
  const run={
    record_type:"autodraw_game_monitor_run",execution_status:"completed",
    run_id:"r",session_id:"s",point_delta_matches_chalk:true,
    pre_test_snapshot:{isExact:true,pointCount:1,logicalWidth:460,logicalHeight:240},
    post_test_snapshot:{isExact:true,pointCount:4,logicalWidth:460,logicalHeight:240},
    dropped_events:0,bridge_send_failures_delta:0,
    collector_sequence_gap_count:0,monitor_error_count_delta:0,
    monitor_errors:[],stroke_count:2,
    observed_stroke_modes:[
      {stroke_id:"s1",stroke_option_raw:false},
      {stroke_id:"s2",stroke_option_raw:false}
    ],
    accepted_points:[
      {stroke_id:"s1",t:1,x:2,y:3,point_delta:1},
      {stroke_id:"s1",t:2,x:3,y:3,point_delta:1},
      {stroke_id:"s2",t:3,x:5,y:7,point_delta:1}
    ]
  };
  run.events=run.accepted_points.map((p,i)=>({
    type:"DRAW_SAMPLE",pointDelta:p.point_delta,strokeId:p.stroke_id,
    t:p.t,acceptedPoint:{x:p.x,y:p.y},board:{currentRadius:i<2?5:10}
  }));
  const exact=extractFill001SeriesStrokes(run);
  assert.equal(exact.pixelExactEligible,true);
  assert.equal(exact.exactHistoricalChalk,3);
  assert.deepEqual(exact.strokes.map(s=>s.width),[5,10]);
  assert.equal(exact.strokes.length,2);
  const aggregate=structuredClone(run);
  aggregate.accepted_points[2].point_delta=2;
  aggregate.events[2].pointDelta=2;
  aggregate.post_test_snapshot.pointCount=5;
  const partial=extractFill001SeriesStrokes(aggregate);
  assert.equal(partial.exactHistoricalChalk,4);
  assert.equal(partial.missingCoordinateCount,1);
  assert.equal(partial.pixelExactEligible,false);
  assert.equal(partial.replayStatus,"DIAGNOSTIC_MISSING_ACCEPTED_COORDINATES");
  const changed=structuredClone(run);
  changed.events[1].board.currentRadius=30;
  assert.throws(()=>extractFill001SeriesStrokes(changed),/mid-stroke radius/);
  const lost=structuredClone(run);
  lost.bridge_send_failures_delta=1;
  assert.throws(()=>extractFill001SeriesStrokes(lost),/recorder\/transport/);
  const unobserved=structuredClone(run);
  unobserved.observed_stroke_modes[0].stroke_option_raw=true;
  assert.throws(()=>extractFill001SeriesStrokes(unobserved),/observed normal mode/);
});


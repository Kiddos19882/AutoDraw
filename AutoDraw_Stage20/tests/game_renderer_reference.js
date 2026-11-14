(function (root) {
  "use strict";


  function extractAcceptedPoints(runOrPoints) {
    if (Array.isArray(runOrPoints)) {
      const direct = runOrPoints;
      if (!direct.length) throw new Error("No accepted points were supplied.");
      return direct.map((point, index) => {
        if (!point || !Number.isFinite(Number(point.x)) || !Number.isFinite(Number(point.y))) {
          throw new Error("Invalid point at index " + index + ".");
        }
        return { x: Number(point.x), y: Number(point.y) };
      });
    }
    // ENGINE-001/Monitor 0.2.4 stores complete accepted_points; older PRR used
    // POINT_QUOTA_UPDATE. Verify the exact raw stream before offline replay.
    if (runOrPoints && runOrPoints.chalk_experiment_matrix?.phase_id === "ENGINE001") {
      const run = runOrPoints;
      const temporal = extractTemporalStrokes(run);
      if (temporal.strokes.length !== 1) {
        throw new Error("ENGINE-001 replay requires exactly one stroke.");
      }
      if (!run.renderer_geometry_at_start || !run.renderer_geometry_at_end ||
          JSON.stringify(run.renderer_geometry_at_start) !== JSON.stringify(run.renderer_geometry_at_end)) {
        throw new Error("ENGINE-001 run-bound renderer geometry is missing or changed.");
      }
      const modes = run.observed_stroke_modes;
      if (!Array.isArray(modes) || modes.length !== 1 ||
          modes[0].stroke_id !== temporal.strokes[0].strokeId ||
          modes[0].stroke_option_raw !== true) {
        throw new Error("ENGINE-001 replay requires observed smooth=true native mode.");
      }
      if (!Array.isArray(run.events)) throw new Error("ENGINE-001 raw events missing.");
      const accepted = run.accepted_points;
      const draws = run.events.filter(e => e && e.type === "DRAW_SAMPLE" && Number(e.pointDelta) > 0);
      if (draws.length !== accepted.length || draws.some((e, i) => {
        const p = accepted[i], q = e.acceptedPoint;
        return Number(e.pointDelta) !== 1 ||
          !["state_poll", "onDrawing_wrapper"].includes(e.source) ||
          e.strokeId !== p.stroke_id || e.t !== p.t ||
          !q || q.x !== p.x || q.y !== p.y;
      })) {
        throw new Error("ENGINE-001 accepted_points disagree with positive DRAW_SAMPLE telemetry.");
      }
      return temporal.strokes[0].points;
    }
    if (!runOrPoints || typeof runOrPoints !== "object" || !Array.isArray(runOrPoints.events)) {
      throw new Error("Paste a Game Monitor run JSON with an events array, or a direct [{x,y}] array.");
    }
    const updates = runOrPoints.events.filter(event =>
      event && event.type === "POINT_QUOTA_UPDATE" && Number(event.pointDelta) > 0
    );
    if (!updates.length) throw new Error("The run contains no accepted POINT_QUOTA_UPDATE events.");
    const strokeIds = new Set(updates.map(event => event.strokeId).filter(value => typeof value === "string" && value));
    if (strokeIds.size !== 1 || updates.some(event => typeof event.strokeId !== "string" || !event.strokeId)) {
      throw new Error("Replay requires exactly one identified stroke; split multi-stroke runs before import.");
    }
    const points = [];
    for (const event of updates) {
      if (Number(event.pointDelta) !== 1) {
        throw new Error("Run is incomplete for exact replay: pointDelta must equal 1 for every accepted-point event.");
      }
      const point = event.acceptedPoint;
      if (!point || !Number.isFinite(Number(point.x)) || !Number.isFinite(Number(point.y))) {
        throw new Error("An accepted point is missing coordinates; enable input telemetry before capture.");
      }
      points.push({ x: Number(point.x), y: Number(point.y) });
    }
    return points;
  }


  // ENGINE-001: accepted-only temporal replay. Does not reconstruct missing
  // ENTER_FRAME callbacks, DOM events, or original screen transforms.
  function extractTemporalStrokes(run) {
    if (!run || run.record_type !== "autodraw_game_monitor_run" ||
        run.execution_status !== "completed" || !Array.isArray(run.accepted_points)) {
      throw new Error("Temporal replay requires a completed Game Monitor run with accepted_points.");
    }
    const before = run.pre_test_snapshot, after = run.post_test_snapshot;
    if (!before || !after || before.isExact !== true || after.isExact !== true ||
        before.logicalWidth !== 460 || before.logicalHeight !== 240 ||
        after.logicalWidth !== 460 || after.logicalHeight !== 240) {
      throw new Error("Temporal replay requires exact 460x240 before/after snapshots.");
    }
    const chalk = Number(after.pointCount) - Number(before.pointCount);
    if (!Number.isSafeInteger(chalk) || chalk <= 0 ||
        chalk !== run.accepted_points.length || run.point_delta_matches_chalk !== true) {
      throw new Error("Temporal accepted-point count differs from exact run-bound CHALK.");
    }
    for (const key of ["dropped_events", "monitor_buffer_dropped_events_delta",
      "monitor_error_count_delta", "bridge_send_failures_delta", "collector_sequence_gap_count"]) {
      if (Number(run[key]) !== 0) throw new Error("Temporal replay rejects telemetry loss: " + key);
    }
    const byId = new Map(), strokes = [];
    let lastId = null, lastTime = -Infinity;
    for (let i = 0; i < run.accepted_points.length; i += 1) {
      const p = run.accepted_points[i];
      if (!p || typeof p.stroke_id !== "string" || !p.stroke_id ||
          p.point_delta !== 1 || !Number.isFinite(p.x) || !Number.isFinite(p.y) ||
          p.x < 0 || p.x >= 460 || p.y < 0 || p.y >= 240 ||
          !Number.isFinite(p.t) || p.t < lastTime) {
        throw new Error("Invalid ordered accepted-point sample at index " + i);
      }
      if (p.stroke_id !== lastId) {
        if (byId.has(p.stroke_id)) throw new Error("Interleaved temporal stroke IDs.");
        const stroke = { strokeId: p.stroke_id, points: [] };
        strokes.push(stroke);
        byId.set(p.stroke_id, stroke);
        lastId = p.stroke_id;
      }
      const points = byId.get(p.stroke_id).points;
      if (points.length && points[points.length - 1].x === p.x &&
          points[points.length - 1].y === p.y) {
        throw new Error("Duplicate consecutive accepted point in " + p.stroke_id);
      }
      points.push({ x: p.x, y: p.y });
      lastTime = p.t;
    }
    if (!strokes.length || strokes.length !== run.stroke_count ||
        !Array.isArray(run.observed_brush_radii) ||
        run.observed_brush_radii.length !== 1 ||
        run.observed_brush_radii[0] !== 10) {
      throw new Error("Unexpected temporal stroke count or brush width.");
    }
    return {
      runId: run.run_id, sessionId: run.session_id,
      pointCountBefore: before.pointCount, pointCountAfter: after.pointCount,
      exactChalk: chalk, strokes
    };
  }


  // FILL001_SERIES_EGRET_REPLAY_V1: separate from strict ENGINE-001 semantics.
  // The run recorder may aggregate two accepted points into one DRAW_SAMPLE;
  // in that case exactly one coordinate is missing and pixel identity cannot
  // be asserted even though exact game CHALK remains known.
  function quotaGroupsForMergedDraws(run, draws) {
    // This is a separate, opt-in reconstruction from accepted game quota
    // events, not an interpolation from planned or browser mouse coordinates.
    const affected = new Set(draws.filter(e => Number(e.pointDelta)>1).map(e => e.strokeId));
    const aligned = new Map();
    for (const strokeId of affected) {
      const strokeDraws=draws.filter(e=>e.strokeId===strokeId);
      const strokeQuota=run.events.filter(e=>e && e.type==="POINT_QUOTA_UPDATE" &&
        e.strokeId===strokeId && Number(e.pointDelta)>0);
      let cursor=0;
      for (const draw of strokeDraws) {
        const d=draw.pointDelta;
        if (!Number.isSafeInteger(d) || d<1 || !Number.isFinite(draw.t)) {
          throw new Error("FILL001 quota recovery invalid DRAW_SAMPLE delta/time.");
        }
        const group=[];
        for (let i=0;i<d;i++) {
          const q=strokeQuota[cursor++];
          const p=q?.acceptedPoint;
          if (!q || q.pointDelta!==1 || !Number.isFinite(q.t) || q.t>draw.t ||
              !p || !Number.isFinite(p.x) || !Number.isFinite(p.y) ||
              p.x<0 || p.x>=460 || p.y<0 || p.y>=240) {
            throw new Error("FILL001 quota recovery missing/invalid unit accepted point.");
          }
          group.push({x:p.x,y:p.y});
        }
        const last=group.at(-1);
        if (last.x!==draw.acceptedPoint?.x || last.y!==draw.acceptedPoint?.y) {
          throw new Error("FILL001 quota recovery terminal point disagrees with DRAW_SAMPLE.");
        }
        aligned.set(draw,group);
      }
      if (cursor!==strokeQuota.length) {
        throw new Error("FILL001 quota recovery extra accepted points.");
      }
    }
    return aligned;
  }

  function extractFill001SeriesStrokes(run, recoverQuota=false) {
    if (!run || run.record_type !== "autodraw_game_monitor_run" ||
        run.execution_status !== "completed" || !Array.isArray(run.accepted_points) ||
        !Array.isArray(run.events) || run.point_delta_matches_chalk !== true) {
      throw new Error("FILL001 replay requires complete, bound Monitor event and accepted-point arrays.");
    }
    const before=run.pre_test_snapshot, after=run.post_test_snapshot;
    if (!before || !after || before.isExact !== true || after.isExact !== true ||
        before.logicalWidth !== 460 || before.logicalHeight !== 240 ||
        after.logicalWidth !== 460 || after.logicalHeight !== 240) {
      throw new Error("FILL001 requires exact 460x240 before/after counter snapshots.");
    }
    const chalk=Number(after.pointCount)-Number(before.pointCount);
    const events=run.events.filter(e=>e && e.type==="DRAW_SAMPLE" && Number(e.pointDelta)>0);
    const accepted=run.accepted_points;
    if (!Number.isSafeInteger(chalk) || chalk<=0 || events.length!==accepted.length ||
        Number(run.dropped_events)!==0 || Number(run.bridge_send_failures_delta)!==0 ||
        Number(run.collector_sequence_gap_count)!==0 || Number(run.monitor_error_count_delta)!==0 ||
        (Array.isArray(run.monitor_errors) && run.monitor_errors.length)) {
      throw new Error("FILL001 recorder/transport integrity or event-count mismatch.");
    }
    const quotaGroups=recoverQuota ? quotaGroupsForMergedDraws(run,events) : null;
    const observed=new Map((run.observed_stroke_modes||[]).map(m=>[m.stroke_id,m.stroke_option_raw]));
    const strokes=[], seen=new Set();
    let sum=0,missing=0,recovered=0,lastTime=-Infinity,lastId=null;
    for (let i=0;i<accepted.length;i++) {
      const p=accepted[i],e=events[i];
      const d=Number(p?.point_delta);
      if (!p || !e || !Number.isSafeInteger(d) || d<1 || d>2 ||
          d!==Number(e.pointDelta) || p.stroke_id!==e.strokeId || p.t!==e.t ||
          e.acceptedPoint?.x!==p.x || e.acceptedPoint?.y!==p.y ||
          !Number.isFinite(p.x) || !Number.isFinite(p.y) ||
          p.x<0 || p.x>=460 || p.y<0 || p.y>=240 ||
          !Number.isFinite(p.t) || p.t<lastTime) {
        throw new Error("FILL001 invalid ordered accepted-point/evidence at "+i);
      }
      const radius=Number(e.board?.currentRadius);
      if (!Number.isInteger(radius) || radius<1 || radius>30 ||
          observed.get(p.stroke_id)!==false) {
        throw new Error("FILL001 brush radius or observed normal mode unavailable at "+i);
      }
      if (lastId!==p.stroke_id) {
        if (seen.has(p.stroke_id)) throw new Error("FILL001 interleaved stroke IDs.");
        seen.add(p.stroke_id);
        strokes.push({strokeId:p.stroke_id,width:radius,points:[]});
        lastId=p.stroke_id;
      }
      const stroke=strokes[strokes.length-1];
      if (stroke.width!==radius) throw new Error("FILL001 mid-stroke radius change.");
      const coordinates=quotaGroups?.get(e) || [{x:p.x,y:p.y}];
      if (recoverQuota && d>1 && (!quotaGroups.has(e) || coordinates.length!==d)) {
        throw new Error("FILL001 quota recovery incomplete group.");
      }
      for (const candidate of coordinates) {
        if (stroke.points.length) {
          const old=stroke.points[stroke.points.length-1];
          if (old.x===candidate.x && old.y===candidate.y) {
            throw new Error("FILL001 duplicate accepted point.");
          }
        }
        stroke.points.push(candidate);
      }
      sum+=d;
      missing+=d-coordinates.length;
      recovered+=coordinates.length-1;
      lastTime=p.t;
    }
    if (sum!==chalk || strokes.length!==Number(run.stroke_count)) {
      throw new Error("FILL001 accepted-point sum/stroke count differs from game counters.");
    }
    return {
      runId:run.run_id,sessionId:run.session_id,strokes,
      exactHistoricalChalk:chalk,observedCoordinateCount:accepted.length+recovered,
      recoveredCoordinateCount:recovered,
      missingCoordinateCount:missing,
      pixelExactEligible:missing===0 && recovered===0,
      replayStatus:recovered>0?"QUOTA_RECONSTRUCTED_DIAGNOSTIC":
        missing===0?"COMPLETE_ACCEPTED_COORDINATES":"DIAGNOSTIC_MISSING_ACCEPTED_COORDINATES"
    };
  }

  function midpoint(a, b) {
    return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
  }

  // Mirrors Painter.drawSmoothLine(graphics, points, drawFirstHalf, drawLast)
  // from main.min_653f95bc.js. Both boolean arguments default to true.
  // BoardPane.redraw() explicitly calls it with (true, false).
  function buildSmoothPathCommands(points, drawFirstHalf, drawLast) {
    if (drawFirstHalf === undefined) drawFirstHalf = true;
    if (drawLast === undefined) drawLast = true;
    if (!points || points.length === 0) return [];

    const commands = [{ type: "moveTo", x: points[0].x, y: points[0].y }];
    const mids = [];
    for (let i = 0; i < points.length - 1; i += 1) {
      mids.push(midpoint(points[i], points[i + 1]));
    }

    // Painter performs this second moveTo; retain it because the reference
    // should preserve the source command sequence, not simplify it.
    commands.push({ type: "moveTo", x: points[0].x, y: points[0].y });
    if (mids.length > 0) {
      commands.push({
        type: drawFirstHalf ? "lineTo" : "moveTo",
        x: mids[0].x,
        y: mids[0].y
      });
      for (let i = 0; i < mids.length - 1; i += 1) {
        commands.push({
          type: "curveTo",
          controlX: points[i + 1].x,
          controlY: points[i + 1].y,
          x: mids[i + 1].x,
          y: mids[i + 1].y
        });
      }
    }
    if (drawLast) {
      const last = points[points.length - 1];
      commands.push({ type: "lineTo", x: last.x, y: last.y });
    }
    return commands;
  }

  function buildNormalPathCommands(points) {
    if (!points || points.length === 0) return [];
    const commands = [{ type: "moveTo", x: points[0].x, y: points[0].y }];
    for (let i = 1; i < points.length; i += 1) {
      commands.push({ type: "lineTo", x: points[i].x, y: points[i].y });
    }
    return commands;
  }

  // Mirrors the WebGLRenderer.renderGraphics guard in Egret 5.4.1:
  // GraphicsNode is not rasterized/uploaded when bounds or drawData are empty.
  function shouldWebGLRendererRasterize(node) {
    return !!node &&
      node.width > 0 &&
      node.height > 0 &&
      !!node.drawData &&
      node.drawData.length > 0;
  }

  function terminalPoint(points, smooth, drawLast) {
    if (drawLast === undefined) drawLast = true;
    if (!points || points.length === 0) return null;
    if (!smooth || drawLast) {
      const p = points[points.length - 1];
      return { x: p.x, y: p.y };
    }
    if (points.length === 1) return null;
    return midpoint(points[points.length - 2], points[points.length - 1]);
  }


  function buildStagePlacement(profile, roundOrigin) {
    if (!profile || typeof profile !== "object") throw new Error("Stage profile is required.");
    const stageWidth = Number(profile.stageWidth), stageHeight = Number(profile.stageHeight);
    const backingWidth = Number(profile.canvasBackingWidth), backingHeight = Number(profile.canvasBackingHeight);
    const scaleX = Number(profile.canvasScaleX), scaleY = Number(profile.canvasScaleY);
    const boardWidth = Number(profile.boardWidth), boardHeight = Number(profile.boardHeight);
    const c = profile.boardStageCorners || {};
    const tl = c.topLeft || {}, tr = c.topRight || {}, br = c.bottomRight || {}, bl = c.bottomLeft || {};
    const values = [stageWidth,stageHeight,backingWidth,backingHeight,scaleX,scaleY,boardWidth,boardHeight,
      Number(tl.x),Number(tl.y),Number(tr.x),Number(tr.y),Number(br.x),Number(br.y),Number(bl.x),Number(bl.y)];
    if (!values.every(Number.isFinite) ||
        ![stageWidth,stageHeight,backingWidth,backingHeight,boardWidth,boardHeight].every(Number.isInteger) ||
        stageWidth<=0 || stageHeight<=0 || backingWidth<=0 || backingHeight<=0 ||
        scaleX<=0 || scaleY<=0 || boardWidth<=0 || boardHeight<=0) {
      throw new Error("Stage/backing/board geometry contains invalid dimensions or scale.");
    }
    const eps=1e-4, close=(a,b)=>Math.abs(a-b)<=eps;
    if (!close(backingWidth/stageWidth,scaleX) || !close(backingHeight/stageHeight,scaleY)) {
      throw new Error("Backing dimensions do not match the run-bound Stage scale.");
    }
    if (!close(tr.x-tl.x,boardWidth) || !close(br.x-bl.x,boardWidth) ||
        !close(bl.y-tl.y,boardHeight) || !close(br.y-tr.y,boardHeight) ||
        !close(tl.y,tr.y) || !close(bl.y,br.y) || !close(tl.x,bl.x) || !close(tr.x,br.x)) {
      throw new Error("BoardPane stage corners are not an axis-aligned rectangle matching board dimensions.");
    }
    const exactX=tl.x*scaleX, exactY=tl.y*scaleY;
    const x=roundOrigin?Math.round(exactX):exactX, y=roundOrigin?Math.round(exactY):exactY;
    const width=boardWidth*scaleX, height=boardHeight*scaleY;
    if (x<0 || y<0 || x+width>backingWidth+eps || y+height>backingHeight+eps) {
      throw new Error("BoardPane placement falls outside the Stage backing canvas.");
    }
    return {x,y,width,height,exactX,exactY,roundedX:Math.round(exactX),roundedY:Math.round(exactY),
      stageWidth,stageHeight,backingWidth,backingHeight,scaleX,scaleY,boardWidth,boardHeight,
      rounding:roundOrigin?"nearest_backing_pixel":"exact_fractional_backing_origin"};
  }

  function renderStageCanvas2D(sourceCanvas, profile, roundOrigin) {
    const p=buildStagePlacement(profile,roundOrigin);
    if (!sourceCanvas || sourceCanvas.width!==p.width || sourceCanvas.height!==p.height) {
      throw new Error("Stage compositor source dimensions do not match BoardPane backing dimensions.");
    }
    const canvas=document.createElement("canvas");
    canvas.width=p.backingWidth; canvas.height=p.backingHeight;
    const ctx=canvas.getContext("2d",{alpha:true});
    if (!ctx) throw new Error("Stage Canvas2D context unavailable.");
    ctx.clearRect(0,0,canvas.width,canvas.height);
    ctx.imageSmoothingEnabled=true; ctx.imageSmoothingQuality="high";
    ctx.drawImage(sourceCanvas,p.x,p.y,p.width,p.height);
    return {canvas,placement:p};
  }


  // Egret's Stage DisplayList matrix is expressed in logical Stage coordinates.
  // The renderer applies canvasScaleX/Y while drawing into the backing RenderBuffer,
  // so the translation must be converted from backing pixels back to Stage units.
  function buildStageRendererTransform(placement) {
    if (!placement ||
        !Number.isFinite(placement.x) || !Number.isFinite(placement.y) ||
        !Number.isFinite(placement.scaleX) || !Number.isFinite(placement.scaleY) ||
        placement.scaleX <= 0 || placement.scaleY <= 0) {
      throw new Error("Stage renderer transform requires a valid backing placement and positive scale.");
    }
    return {
      a: placement.scaleX,
      b: 0,
      c: 0,
      d: placement.scaleY,
      tx: placement.x / placement.scaleX,
      ty: placement.y / placement.scaleY
    };
  }

  function renderStageWebGL(mode, points, lineWidth, profile, roundOrigin, state, boardOverride) {
    const placement = buildStagePlacement(profile, roundOrigin);
    if (state.bufferSize.width !== placement.backingWidth ||
        state.bufferSize.height !== placement.backingHeight) {
      throw new Error("Egret Stage render buffer does not match run-bound backing dimensions.");
    }

    const stage = new egret.Stage();
    const container = new egret.DisplayObjectContainer();
    stage.addChild(container);
    const mask = makeBoardMaskShape();
    container.addChild(mask);
    const board = boardOverride || makeActualBoardPane(mode, points, lineWidth).shape;
    container.addChild(board);
    board.mask = mask;

    const sceneDiagnostics = {
      stageAttached: !!board.$stage && !!mask.$stage,
      sameStage: board.$stage === mask.$stage,
      sameParent: board.$parent === mask.$parent,
      boardRenderMode: board.$renderMode,
      maskRenderMode: mask.$renderMode
    };
    if (!sceneDiagnostics.stageAttached || !sceneDiagnostics.sameStage ||
        !sceneDiagnostics.sameParent || sceneDiagnostics.boardRenderMode !== 3) {
      throw new Error("Stage-level Egret scene is not configured like an attached display list: " +
        JSON.stringify(sceneDiagnostics));
    }

    state.buffer.clear();
    const stageTransform = buildStageRendererTransform(placement);
    const matrix = new egret.Matrix(
      stageTransform.a, stageTransform.b, stageTransform.c,
      stageTransform.d, stageTransform.tx, stageTransform.ty
    );
    const drawCalls = state.renderer.render(container, state.buffer, matrix);
    const pixels = state.buffer.getPixels(
      0, 0, placement.backingWidth, placement.backingHeight
    );
    const expectedLength = placement.backingWidth * placement.backingHeight * 4;
    if (!pixels || pixels.length !== expectedLength) {
      throw new Error("Egret Stage RenderBuffer returned an invalid full-backing pixel buffer.");
    }
    const canvas = document.createElement("canvas");
    canvas.width = placement.backingWidth;
    canvas.height = placement.backingHeight;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Stage readback Canvas2D context unavailable.");
    context.putImageData(new ImageData(
      new Uint8ClampedArray(pixels), placement.backingWidth, placement.backingHeight
    ), 0, 0);

    const texture = board.$renderNode && board.$renderNode.$texture;
    if (!texture) throw new Error("Stage-level BoardPane WebGL texture was not created.");
    state.gl.bindTexture(state.gl.TEXTURE_2D, texture);
    const textureParameters = {
      minFilter: state.gl.getTexParameter(state.gl.TEXTURE_2D, state.gl.TEXTURE_MIN_FILTER),
      magFilter: state.gl.getTexParameter(state.gl.TEXTURE_2D, state.gl.TEXTURE_MAG_FILTER),
      wrapS: state.gl.getTexParameter(state.gl.TEXTURE_2D, state.gl.TEXTURE_WRAP_S),
      wrapT: state.gl.getTexParameter(state.gl.TEXTURE_2D, state.gl.TEXTURE_WRAP_T),
      unpackPremultiplyAlpha: state.gl.getParameter(state.gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL)
    };
    state.gl.bindTexture(state.gl.TEXTURE_2D, null);
    return {
      canvas, placement, drawCalls, sceneDiagnostics, textureParameters,
      contextAttributes: state.contextAttributes,
      backend: "Egret WebGLRenderer on the run-sized Stage RenderBuffer"
    };
  }

  function renderStageLevelVariants(mode,points,lineWidth,sourceCanvas,profile,state) {
    const plan=[
      {id:"A",backend:"WebGL",roundOrigin:false},
      {id:"B",backend:"WebGL",roundOrigin:true},
      {id:"C",backend:"Canvas2D",roundOrigin:false},
      {id:"D",backend:"Canvas2D",roundOrigin:true}
    ];
    const rendered=plan.map(v=>{
      const r=v.backend==="WebGL"
        ?renderStageWebGL(mode,points,lineWidth,profile,v.roundOrigin,state)
        :renderStageCanvas2D(sourceCanvas,profile,v.roundOrigin);
      return {id:v.id,backend:v.backend,canvas:r.canvas,placement:r.placement,
        textureParameters:r.textureParameters||null,contextAttributes:r.contextAttributes||null,
        sceneDiagnostics:r.sceneDiagnostics||null,drawCalls:r.drawCalls||null,
        rendererBackend:r.backend||"Canvas2D image composite"};
    });
    const baseline=rendered[0].canvas;
    return rendered.map(v=>({...v,comparisonToA:compareCanvases(baseline,v.canvas)}));
  }

  const api = {
    buildSmoothPathCommands,
    buildNormalPathCommands,
    terminalPoint,
    shouldWebGLRendererRasterize,
    extractAcceptedPoints,
    extractTemporalStrokes,
    extractFill001SeriesStrokes,
    quotaGroupsForMergedDraws,
    buildStagePlacement,
    buildStageRendererTransform
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
  root.AutoDrawGameRendererReference = api;

  if (typeof document === "undefined") return;

  const BOARD_WIDTH = 460;
  const BOARD_HEIGHT = 240;
  const RASTER_SCALE = 3;
  const RUNTIME_CANVAS_SCALE_FACTOR = 2;
  const MASK_ELLIPSE_SIZE = 10; // Egret Path2D halves this: corner radius = 5.
  const LINE_WIDTHS = [10, 30];
  const statusNode = document.getElementById("renderer-status");
  const casesNode = document.getElementById("renderer-cases");
  const manifestNode = document.getElementById("renderer-manifest");

  function getLiveRunInput() {
    const liveInput = document.getElementById("live-points-json");
    return liveInput && liveInput.value.trim() ? JSON.parse(liveInput.value) : null;
  }

  function buildRuntimeProfileFromRun(run) {
    if (!run || Array.isArray(run) || typeof run !== "object") {
      throw new Error("Для парного offline replay нужен полный monitor_report.json, а не массив координат.");
    }
    const start = run.renderer_geometry_at_start;
    const end = run.renderer_geometry_at_end;
    if (!start || !end || JSON.stringify(start) !== JSON.stringify(end)) {
      throw new Error("В Game Monitor run отсутствует неизменный renderer_geometry_at_start/end. Используй полный monitor_report.json последнего теста.");
    }
    if (run.record_type !== "autodraw_game_monitor_run" ||
        !run.run_id || !run.session_id || !run.autodraw_experiment_id) {
      throw new Error("Renderer profile не связан с полным Game Monitor run/session/experiment.");
    }
    if (start.inspectionMode !== "read_only" || start.engineVersion !== "5.4.1" ||
        start.renderMode !== "webgl" || start.boardDetected !== true) {
      throw new Error("Live renderer profile не соответствует Egret 5.4.1 WebGL с обнаруженной доской.");
    }
    if (start.playerCount !== 1 || !Array.isArray(start.players) || start.players.length !== 1 ||
        start.players[0].playerFound !== true || start.players[0].playerMatchesStage !== true) {
      throw new Error("Для offline replay требуется ровно один проверенный Egret player.");
    }
    if (start.canvasScaleFactor !== RUNTIME_CANVAS_SCALE_FACTOR ||
        start.canvasScaleX !== RASTER_SCALE || start.canvasScaleY !== RASTER_SCALE ||
        start.devicePixelRatio !== 1 || start.visualViewportScale !== 1 ||
        start.boardLogicalSize?.width !== BOARD_WIDTH ||
        start.boardLogicalSize?.height !== BOARD_HEIGHT) {
      throw new Error("Live renderer scale/board profile отличается от поддерживаемой геометрии 460×240, raster 3×, DPR 1.");
    }

    const player = start.players[0];
    const stage = player.stage || {};
    const canvas = player.canvas || {};
    const windowGeometry = start.windowGeometry || {};
    const screenWidth = Number(windowGeometry.screenWidth);
    const screenHeight = Number(windowGeometry.screenHeight);
    if (!Number.isInteger(screenWidth) || !Number.isInteger(screenHeight) ||
        screenWidth <= 0 || screenHeight <= 0 ||
        !Number.isInteger(Number(stage.width)) || !Number.isInteger(Number(stage.height)) ||
        !Number.isInteger(Number(canvas.width)) || !Number.isInteger(Number(canvas.height))) {
      throw new Error("В renderer geometry отсутствуют достоверные screen/stage/canvas dimensions.");
    }
    const css = canvas.style || {};
    const corners = player.boardStageCorners || start.boardStageCorners || {};
    return {
      source: "exact Game Monitor renderer_geometry_at_start",
      sourceRunId: run.run_id,
      sourceSessionId: run.session_id,
      sourceExperimentId: run.autodraw_experiment_id,
      geometrySnapshotUpdatedAtUtc: run.renderer_geometry_updated_at_start_utc || null,
      canvasScaleFactor: start.canvasScaleFactor,
      canvasScaleX: start.canvasScaleX,
      canvasScaleY: start.canvasScaleY,
      stageWidth: Number(stage.width),
      stageHeight: Number(stage.height),
      canvasBackingWidth: Number(canvas.width),
      canvasBackingHeight: Number(canvas.height),
      devicePixelRatio: start.devicePixelRatio,
      visualViewportScale: start.visualViewportScale,
      stageFrameRate: Number(stage.frameRate || 0) || null,
      scaleMode: stage.scaleMode || null,
      boardWidth: start.boardLogicalSize.width,
      boardHeight: start.boardLogicalSize.height,
      screen: { width: screenWidth, height: screenHeight },
      viewport: {
        width: Number(windowGeometry.innerWidth || 0) || null,
        height: Number(windowGeometry.innerHeight || 0) || null
      },
      canvasClientRect: canvas.rect || null,
      canvasCssTransform: css.computedTransform || null,
      canvasCssTransformOrigin: css.computedTransformOrigin || null,
      boardStageCorners: corners,
      note: "Live profile is copied from the exact run-bound Game Monitor snapshot. BoardPane offscreen raster remains 460×240 at 3×; screen CSS transform is metadata for paired comparison and is not baked into the local BoardPane raster."
    };
  }

  function fixtureList(liveRunInput) {
    const parsed = liveRunInput;
    if (parsed) {
      const points = extractAcceptedPoints(parsed);
      const mode = document.getElementById("live-path-mode").value;
      if (parsed.chalk_experiment_matrix?.phase_id === "ENGINE001" && mode !== "smooth") {
        throw new Error("ENGINE-001 selected mode differs from observed smooth=true.");
      }
      const lineWidth = Number(document.getElementById("live-line-width").value);
      if (!Number.isFinite(lineWidth) || lineWidth <= 0 || lineWidth > 100) {
        throw new Error("Line width must be greater than 0 and no more than 100.");
      }
      return [{ id: "live-accepted-points", mode, points, lineWidths: [lineWidth],
        sourceRunId: parsed && !Array.isArray(parsed) ? parsed.run_id || null : null }];
    }
    return [
      { id: "smooth-single-point", mode: "smooth", points: [{ x: 40, y: 40 }] },
      { id: "smooth-two-points", mode: "smooth", points: [{ x: 35, y: 65 }, { x: 145, y: 65 }] },
      { id: "smooth-three-points", mode: "smooth", points: [{ x: 35, y: 105 }, { x: 140, y: 125 }, { x: 250, y: 105 }] },
      { id: "smooth-four-point-turn", mode: "smooth", points: [{ x: 35, y: 155 }, { x: 120, y: 155 }, { x: 165, y: 205 }, { x: 270, y: 205 }] },
      { id: "normal-zero-length-segment", mode: "normal", points: [{ x: 100, y: 100 }, { x: 100, y: 100 }] },
      { id: "normal-horizontal", mode: "normal", points: [{ x: 25, y: 35 }, { x: 435, y: 35 }] },
      { id: "normal-diagonal", mode: "normal", points: [{ x: 20, y: 20 }, { x: 440, y: 220 }] },
      { id: "normal-l-turn", mode: "normal", points: [{ x: 35, y: 35 }, { x: 35, y: 190 }, { x: 180, y: 190 }] },
      { id: "mask-corner", mode: "normal", points: [{ x: 0, y: 0 }, { x: 48, y: 48 }] },
      { id: "scrollrect-edges", mode: "normal", points: [{ x: -20, y: 120 }, { x: 480, y: 120 }] }
    ];
  }

  function applyPathCommands(graphics, commands) {
    for (const command of commands) {
      if (command.type === "moveTo") graphics.moveTo(command.x, command.y);
      else if (command.type === "lineTo") graphics.lineTo(command.x, command.y);
      else if (command.type === "curveTo") {
        graphics.curveTo(command.controlX, command.controlY, command.x, command.y);
      }
    }
  }

  function getBoardPaneClass() {
    return root.com && root.com.magnetjoy && root.com.magnetjoy.pet &&
      root.com.magnetjoy.pet.ui && root.com.magnetjoy.pet.ui.board &&
      root.com.magnetjoy.pet.ui.board.BoardPane;
  }

  function prepareBoardPane(mode, points, lineWidth, color) {
    const BoardPane = getBoardPaneClass();
    if (typeof BoardPane !== "function") {
      throw new Error("Game bundle did not expose com.magnetjoy.pet.ui.board.BoardPane.");
    }
    const board = new BoardPane(false, 6000);
    board.width = BOARD_WIDTH;
    board.height = BOARD_HEIGHT;
    board.atom.clear();
    board.atom.points = [points.map(point => new egret.Point(point.x, point.y))];
    board.atom.radius = [lineWidth];
    board.atom.colors = [color === undefined ? 0x000000 : color];
    board.atom.options = [mode === "smooth"];
    board.updateLess();
    return board;
  }

  function makeActualBoardPane(mode, points, lineWidth, color) {
    const board = prepareBoardPane(mode, points, lineWidth, color);
    board.redraw();
    return {
      shape: board,
      commands: mode === "smooth"
        ? buildSmoothPathCommands(points, true, false)
        : buildNormalPathCommands(points)
    };
  }

  function makeManualBoardPane(mode, points, lineWidth, color) {
    const board = prepareBoardPane(mode, points, lineWidth, color);
    const painter = root.com.magnetjoy.painter.Painter;
    const originalSmooth = painter.drawSmoothLine;
    const originalNormal = painter.drawNormalLine;
    painter.drawSmoothLine = function (graphics, acceptedPoints, drawFirstHalf, drawLast) {
      applyPathCommands(graphics,
        buildSmoothPathCommands(acceptedPoints, drawFirstHalf, drawLast));
    };
    painter.drawNormalLine = function (graphics, acceptedPoints) {
      applyPathCommands(graphics, buildNormalPathCommands(acceptedPoints));
    };
    try {
      board.redraw();
    } finally {
      painter.drawSmoothLine = originalSmooth;
      painter.drawNormalLine = originalNormal;
    }
    return {
      shape: board,
      commands: mode === "smooth"
        ? buildSmoothPathCommands(points, true, false)
        : buildNormalPathCommands(points)
    };
  }

  function compareCanvases(left, right) {
    if (left.width !== right.width || left.height !== right.height) {
      return {
        equal: false,
        differingPixels: null,
        reason: "dimension-mismatch",
        left: { width: left.width, height: left.height },
        right: { width: right.width, height: right.height }
      };
    }
    function readPixels(source) {
      let context = source.getContext("2d", { willReadFrequently: true });
      if (!context) {
        const copy = document.createElement("canvas");
        copy.width = source.width;
        copy.height = source.height;
        context = copy.getContext("2d", { willReadFrequently: true });
        if (!context) throw new Error("Unable to read compositor canvas pixels.");
        context.drawImage(source, 0, 0);
      }
      return context.getImageData(0, 0, source.width, source.height).data;
    }
    const leftData = readPixels(left);
    const rightData = readPixels(right);
    let differingPixels = 0;
    let maxChannelDifference = 0;
    let totalChannelDifference = 0;
    let differingChannels = 0;
    for (let i = 0; i < leftData.length; i += 4) {
      let pixelDiffers = false;
      for (let channel = 0; channel < 4; channel += 1) {
        const difference = Math.abs(leftData[i + channel] - rightData[i + channel]);
        if (difference > 0) {
          pixelDiffers = true;
          differingChannels += 1;
          totalChannelDifference += difference;
          maxChannelDifference = Math.max(maxChannelDifference, difference);
        }
      }
      if (pixelDiffers) differingPixels += 1;
    }
    return {
      equal: differingPixels === 0,
      differingPixels,
      maxChannelDifference,
      meanDifferingChannelDifference: differingChannels
        ? totalChannelDifference / differingChannels
        : 0,
      reason: null
    };
  }

  function renderGraphicsNode(node, isMask) {
    if (!node) throw new Error("GraphicsNode is unavailable.");

    // The active game runtime uses WebGLRenderer. Egret 5.4.1 skips GraphicsNode
    // rasterization entirely when its bounds are empty or drawData is empty.
    // Preserve that no-op as a transparent reference rather than aborting the
    // entire fixture batch (notably for a smooth single-point moveTo-only path).
    if (!shouldWebGLRendererRasterize(node)) {
      const canvas = document.createElement("canvas");
      canvas.width = 1;
      canvas.height = 1;
      return {
        canvas,
        pixelWidth: 1,
        pixelHeight: 1,
        scaleX: 1,
        scaleY: 1,
        nodeBounds: { x: null, y: null, width: node.width || 0, height: node.height || 0 },
        skippedByWebGLRenderer: true
      };
    }

    let scaleX = RASTER_SCALE;
    let scaleY = RASTER_SCALE;
    if (node.width * scaleX < 1 || node.height * scaleY < 1) {
      scaleX = 1;
      scaleY = 1;
    }
    const pixelWidth = Math.ceil(node.width * scaleX);
    const pixelHeight = Math.ceil(node.height * scaleY);
    scaleX *= pixelWidth / (node.width * scaleX);
    scaleY *= pixelHeight / (node.height * scaleY);

    const canvas = document.createElement("canvas");
    canvas.width = pixelWidth;
    canvas.height = pixelHeight;
    const context = canvas.getContext("2d", { willReadFrequently: false });
    if (!context) throw new Error("Canvas2D context unavailable.");
    context.$offsetX = 0;
    context.$offsetY = 0;
    context.setTransform(scaleX, 0, 0, scaleY, 0, 0);
    if (node.x || node.y) context.translate(-node.x, -node.y);

    const renderer = new egret.CanvasRenderer();
    renderer.renderGraphics(node, context, !!isMask);

    return {
      canvas,
      pixelWidth,
      pixelHeight,
      scaleX,
      scaleY,
      nodeBounds: { x: node.x, y: node.y, width: node.width, height: node.height },
      skippedByWebGLRenderer: false
    };
  }

  function makeBoardMaskShape() {
    const mask = new egret.Shape();
    mask.graphics.beginFill(0xffffff, 1);
    mask.graphics.drawRoundRect(0, 0, BOARD_WIDTH, BOARD_HEIGHT, MASK_ELLIPSE_SIZE);
    mask.graphics.endFill();
    return mask;
  }

  function createBoardMask() {
    const mask = makeBoardMaskShape();
    return renderGraphicsNode(mask.$renderNode, true);
  }

  function composeBoard(source, nodeBounds, mask) {
    const canvas = document.createElement("canvas");
    canvas.width = BOARD_WIDTH * RASTER_SCALE;
    canvas.height = BOARD_HEIGHT * RASTER_SCALE;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Board Canvas2D context unavailable.");
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.imageSmoothingEnabled = true;

    if (source.skippedByWebGLRenderer) return canvas;

    // Mirrors the WebGLRenderer destination size (node bounds mapped back to
    // logical size) using Canvas2D. This is a comparison composite, not proof
    // of identical WebGL texture filtering or mask stencil behavior.
    context.drawImage(
      source.canvas,
      0, 0, source.pixelWidth, source.pixelHeight,
      nodeBounds.x * RASTER_SCALE,
      nodeBounds.y * RASTER_SCALE,
      nodeBounds.width * RASTER_SCALE,
      nodeBounds.height * RASTER_SCALE
    );

    context.globalCompositeOperation = "destination-in";
    context.drawImage(mask.canvas, 0, 0, mask.pixelWidth, mask.pixelHeight,
      0, 0, canvas.width, canvas.height);
    context.globalCompositeOperation = "source-over";
    return canvas;
  }

  function addDownloadLink(parent, canvas, filename, label) {
    const link = document.createElement("a");
    link.href = canvas.toDataURL("image/png");
    link.download = filename;
    link.textContent = label;
    parent.appendChild(link);
  }

  function initializeWebGL(stageProfile, seriesScale) {
    if (!egret.sys || typeof egret.sys.setRenderMode !== "function") {
      throw new Error("Egret sys.setRenderMode is unavailable.");
    }
    if (egret.Capabilities.renderMode !== "webgl") egret.sys.setRenderMode("webgl");
    if (!egret.sys.systemRenderer || typeof egret.sys.systemRenderer.render !== "function" ||
        !egret.sys.RenderBuffer) {
      throw new Error("Egret did not initialize WebGLRenderer/WebGLRenderBuffer.");
    }
    const displayList = egret.sys.DisplayList;
    displayList.$canvasScaleX = seriesScale || RASTER_SCALE;
    displayList.$canvasScaleY = seriesScale || RASTER_SCALE;
    displayList.$canvasScaleFactor = RUNTIME_CANVAS_SCALE_FACTOR;

    const outputWidth = BOARD_WIDTH * RASTER_SCALE;
    const outputHeight = BOARD_HEIGHT * RASTER_SCALE;
    const bufferWidth = stageProfile ? Number(stageProfile.canvasBackingWidth) : outputWidth;
    const bufferHeight = stageProfile ? Number(stageProfile.canvasBackingHeight) : outputHeight;
    if (!Number.isInteger(bufferWidth) || !Number.isInteger(bufferHeight) ||
        bufferWidth < outputWidth || bufferHeight < outputHeight) {
      throw new Error("Egret render buffer dimensions are invalid for the run-bound Stage profile.");
    }
    const buffer = new egret.sys.RenderBuffer(bufferWidth, bufferHeight);
    const gl = buffer.context && buffer.context.context;
    if (!gl) throw new Error("Egret WebGL context is unavailable.");
    const maxRenderbuffer = gl.getParameter(gl.MAX_RENDERBUFFER_SIZE);
    if (bufferWidth > maxRenderbuffer || bufferHeight > maxRenderbuffer) {
      throw new Error("Stage backing dimensions exceed Egret WebGL renderbuffer limits.");
    }
    const debugInfo = gl.getExtension("WEBGL_debug_renderer_info");
    const glInfo = {
      version: gl.getParameter(gl.VERSION),
      shadingLanguageVersion: gl.getParameter(gl.SHADING_LANGUAGE_VERSION),
      vendor: gl.getParameter(gl.VENDOR),
      renderer: gl.getParameter(gl.RENDERER),
      unmaskedVendor: debugInfo ? gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) : null,
      unmaskedRenderer: debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : null
    };
    return {
      renderer: egret.sys.systemRenderer,
      buffer,
      gl,
      glInfo,
      contextAttributes: gl.getContextAttributes(),
      outputSize: { width: outputWidth, height: outputHeight },
      bufferSize: { width: bufferWidth, height: bufferHeight }
    };
  }

  function renderWebGLProbe(mode, points, lineWidth, expectedCanvas, state, boardOverride) {
    // Egret 5.4.1 only switches the masked object to the mask render path when
    // mask.$stage is present. Recreate the live display-list relationship:
    // board and mask are siblings under a container attached to a Stage.
    const stage = new egret.Stage();
    const container = new egret.DisplayObjectContainer();
    stage.addChild(container);

    const mask = makeBoardMaskShape();
    container.addChild(mask);
    const board = boardOverride || makeActualBoardPane(mode, points, lineWidth).shape;
    container.addChild(board);
    board.mask = mask;

    const sceneDiagnostics = {
      stageAttached: !!board.$stage && !!mask.$stage,
      sameStage: board.$stage === mask.$stage,
      sameParent: board.$parent === mask.$parent,
      boardRenderMode: board.$renderMode,
      maskRenderMode: mask.$renderMode
    };
    if (!sceneDiagnostics.stageAttached || !sceneDiagnostics.sameStage ||
        !sceneDiagnostics.sameParent || sceneDiagnostics.boardRenderMode !== 3) {
      throw new Error("WebGL mask scene is not configured like an attached Egret display list: " +
        JSON.stringify(sceneDiagnostics));
    }

    state.buffer.clear();
    const matrix = new egret.Matrix(RASTER_SCALE, 0, 0, RASTER_SCALE, 0, 0);
    const drawCalls = state.renderer.render(container, state.buffer, matrix);
    const pixels = state.buffer.getPixels(
      0, 0, state.outputSize.width, state.outputSize.height
    );
    if (!pixels || pixels.length !== state.outputSize.width * state.outputSize.height * 4) {
      throw new Error("WebGLRenderBuffer returned an invalid pixel buffer.");
    }

    const canvas = document.createElement("canvas");
    canvas.width = state.outputSize.width;
    canvas.height = state.outputSize.height;
    const context = canvas.getContext("2d");
    context.putImageData(new ImageData(
      new Uint8ClampedArray(pixels), state.outputSize.width, state.outputSize.height
    ), 0, 0);

    const texture = board.$renderNode && board.$renderNode.$texture;
    if (!texture) throw new Error("BoardPane GraphicsNode WebGL texture was not created.");
    state.gl.bindTexture(state.gl.TEXTURE_2D, texture);
    const textureParameters = {
      minFilter: state.gl.getTexParameter(state.gl.TEXTURE_2D, state.gl.TEXTURE_MIN_FILTER),
      magFilter: state.gl.getTexParameter(state.gl.TEXTURE_2D, state.gl.TEXTURE_MAG_FILTER),
      wrapS: state.gl.getTexParameter(state.gl.TEXTURE_2D, state.gl.TEXTURE_WRAP_S),
      wrapT: state.gl.getTexParameter(state.gl.TEXTURE_2D, state.gl.TEXTURE_WRAP_T),
      unpackPremultiplyAlpha: state.gl.getParameter(state.gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL)
    };
    state.gl.bindTexture(state.gl.TEXTURE_2D, null);

    return {
      canvas,
      drawCalls,
      outputSize: state.outputSize,
      glInfo: state.glInfo,
      contextAttributes: state.contextAttributes,
      textureParameters,
      sceneDiagnostics,
      comparison: compareCanvases(expectedCanvas, canvas)
    };
  }


  function makeTemporalBoard(strokes, lineWidth, mode, incremental, duplicateFinalFrames) {
    if (duplicateFinalFrames === undefined) duplicateFinalFrames = 0;
    if (!Number.isInteger(duplicateFinalFrames) || duplicateFinalFrames < 0 ||
        duplicateFinalFrames > 3 || (duplicateFinalFrames > 0 && !incremental)) {
      throw new Error("Duplicate-frame replay requires incremental mode and 0..3 extra frames.");
    }
    const BoardPane = getBoardPaneClass();
    if (typeof BoardPane !== "function") throw new Error("Game BoardPane unavailable.");
    const board = new BoardPane(false, 6000);
    board.width = BOARD_WIDTH;
    board.height = BOARD_HEIGHT;
    board.atom.clear();
    let fullRedrawCalls = 0, incrementalRedrawCalls = 0, accepted = 0;
    let duplicatePointRejections = 0, extraFrameRedrawCalls = 0;
    for (const stroke of strokes) {
      // Experimental mixed-width native fixture only; legacy temporal runs
      // omit stroke.width and retain the exact original lineWidth path.
      const strokeWidth = stroke.width === undefined ? lineWidth : stroke.width;
      if (!Number.isInteger(strokeWidth) || strokeWidth < 1 || strokeWidth > 100) {
        throw new Error("Invalid per-stroke brush width in offline replay.");
      }
      board.setRadius(strokeWidth);
      board.setColor(0x000000);
      board.setSmooth(mode === "smooth");
      for (let i = 0; i < stroke.points.length; i += 1) {
        const point = stroke.points[i];
        const oldLength = board.atom.points[board.atom.points.length - 1].length;
        board.atom.pushPoint(new egret.Point(point.x, point.y));
        if (board.atom.points[board.atom.points.length - 1].length !== oldLength + 1) {
          throw new Error("BoardPane rejected a validated accepted sample.");
        }
        accepted += 1;
        if (incremental) {
          board.updateLess();
          if (i === 0) {
            board.redraw();
            fullRedrawCalls += 1;
          } else {
            board.redraw(false);
            incrementalRedrawCalls += 1;
          }
        }
      }
      if (incremental) {
        // A stationary, inside-board ENTER_FRAME still calls onDrawing,
        // pushPoint (deduplicated) and redraw(false). The original monitor
        // does NOT record these rejected samples or extra frame callbacks.
        const last = stroke.points[stroke.points.length - 1];
        if (!last) throw new Error("Duplicate-frame study rejects empty strokes.");
        for (let k = 0; k < duplicateFinalFrames; k += 1) {
          const current = board.atom.points[board.atom.points.length - 1];
          const countBefore = current.length;
          const quotaBefore = board.less;
          board.atom.pushPoint(new egret.Point(last.x, last.y));
          if (board.atom.points[board.atom.points.length - 1].length !== countBefore) {
            throw new Error("Stationary duplicate was unexpectedly accepted.");
          }
          duplicatePointRejections += 1;
          board.updateLess();
          if (board.less !== quotaBefore) {
            throw new Error("Stationary duplicate changed quota or accepted-point count.");
          }
          board.redraw(false);
          incrementalRedrawCalls += 1;
          extraFrameRedrawCalls += 1;
        }
        board.redraw(false); // onDrawingEnd, before atom.add
        incrementalRedrawCalls += 1;
      }
      board.atom.add();
    }
    if (!incremental) {
      board.redraw();
      fullRedrawCalls += 1;
    }
    board.updateLess();
    if (board.max - board.less !== accepted ||
        board.atom.points.length !== strokes.length + 1) {
      throw new Error("Reconstructed BoardPane quota/stroke slots differ.");
    }
    return {
      shape: board, accepted, fullRedrawCalls, incrementalRedrawCalls,
      duplicatePointRejections, extraFrameRedrawCalls,
      graphicsPathCount: board.$renderNode && board.$renderNode.drawData
        ? board.$renderNode.drawData.length : null
    };
  }

  function renderTemporalStudy() {
    try {
      if (!window.egret || !egret.Shape || !egret.CanvasRenderer) {
        throw new Error("Egret bundle is not loaded.");
      }
      const path = "../data/results/brush_behavior_tests/game_monitor_bridge/" +
        "bb261898-8296-41f5-a333-eb0b81016410/" +
        "game-monitor-run-20261104T040548835772Z-6a17a297.json";
      const request = new XMLHttpRequest();
      request.open("GET", path, false);
      request.send(null);
      if (request.status !== 200) throw new Error("Pinned temporal source HTTP " + request.status);
      const input = extractTemporalStrokes(JSON.parse(request.responseText));
      if (input.runId !== "6a17a297-ea14-4527-9527-bfd8de3bd335" ||
          input.sessionId !== "bb261898-8296-41f5-a333-eb0b81016410" ||
          input.strokes.length !== 27 || input.exactChalk !== 1260) {
        throw new Error("Temporal input differs from frozen FILL-001 run.");
      }
      const mode = "smooth", lineWidth = 10; // Research assumption; per-stroke options not in run.
      const onePass = makeTemporalBoard(input.strokes, lineWidth, mode, false);
      const incremental = makeTemporalBoard(input.strokes, lineWidth, mode, true);
      const mask = createBoardMask();
      const rasterA = renderGraphicsNode(onePass.shape.$renderNode, false);
      const rasterB = renderGraphicsNode(incremental.shape.$renderNode, false);
      const canvasA = composeBoard(rasterA, rasterA.nodeBounds, mask);
      const canvasB = composeBoard(rasterB, rasterB.nodeBounds, mask);
      const state = initializeWebGL(null);
      const webglA = renderWebGLProbe(mode, [], lineWidth, canvasA, state, onePass.shape);
      const webglB = renderWebGLProbe(mode, [], lineWidth, canvasB, state, incremental.shape);
      const canvasDiff = compareCanvases(canvasA, canvasB);
      const webglDiff = compareCanvases(webglA.canvas, webglB.canvas);
      const manifest = {
        schemaVersion: 1, experimentId: "ENGINE001_TEMPORAL_ACCEPTED_ONLY_V1",
        status: "COMPLETE_OFFLINE_MEASUREMENT",
        gameBundleBlobSha: "46cc74de00b6cb5d207b1e1a2ffcd81613b6d388",
        egretBundleBlobSha: "d613d2b97e2436521aa3870478c69e99eac1f19f",
        inputGitBlobSha: "8eb04ad7331d1e56f4aeb7d0f625c59c1dc57c24",
        inputPath: path, runId: input.runId, sessionId: input.sessionId,
        strokeCount: input.strokes.length, exactHistoricalChalk: input.exactChalk,
        pointCountBefore: input.pointCountBefore, pointCountAfter: input.pointCountAfter,
        lineWidth, modeAssumption: "smooth; per-stroke options unavailable in run",
        method: "one-pass redraw() vs full redraw on stroke start + one redraw(false) per accepted point after first + final redraw(false) + atom.add()",
        exclusions: [
          "Unrecorded extra ENTER_FRAME redraw(false) calls not replayed",
          "No intermediate renderer passes or exact DOM scheduling replayed",
          "Original service baseline point not rendered in either variant",
          "No same-run Stage/client/desktop transform or live PNG comparison",
          "No new CHALK measurement"
        ],
        screenProjection: "UNCALIBRATED",
        inputCompleteForAcceptedPointsOnly: true,
        onePass: {accepted:onePass.accepted,fullRedrawCalls:onePass.fullRedrawCalls,
          incrementalRedrawCalls:onePass.incrementalRedrawCalls,graphicsPathCount:onePass.graphicsPathCount},
        incremental: {accepted:incremental.accepted,fullRedrawCalls:incremental.fullRedrawCalls,
          incrementalRedrawCalls:incremental.incrementalRedrawCalls,graphicsPathCount:incremental.graphicsPathCount},
        renderSize: {width:canvasA.width,height:canvasA.height},
        canvas2dPixelComparison: canvasDiff, webglPixelComparison: webglDiff,
        onePassWebGLVsCanvas2D: webglA.comparison,
        incrementalWebGLVsCanvas2D: webglB.comparison,
        backend: state.glInfo, renderedWebGL: true
      };
      if (onePass.accepted !== 1260 || incremental.accepted !== 1260 ||
          !Number.isInteger(onePass.graphicsPathCount) ||
          !Number.isInteger(incremental.graphicsPathCount) ||
          incremental.graphicsPathCount <= onePass.graphicsPathCount ||
          !Number.isInteger(canvasDiff.differingPixels) ||
          !Number.isInteger(webglDiff.differingPixels)) {
        throw new Error("Temporal renderer comparison incomplete or no accumulated paths.");
      }
      casesNode.textContent = "";
      const card = document.createElement("section");
      card.className = "fixture";
      card.textContent = "ENGINE-001 accepted-only temporal study; offline only.";
      for (const [label,canvas] of [
        ["onepass-canvas2d",canvasA],["incremental-canvas2d",canvasB],
        ["onepass-webgl",webglA.canvas],["incremental-webgl",webglB.canvas]
      ]) addDownloadLink(card,canvas,"engine001-temporal-"+label+".png",label+" PNG");
      casesNode.appendChild(card);
      document.getElementById("renderer-manifest-json").textContent = JSON.stringify(manifest,null,2);
      document.body.dataset.temporalStatus = "complete";
      document.body.dataset.temporalPngCount = "4";
      document.body.dataset.referenceStatus = "temporal_complete";
      statusNode.textContent = "ENGINE-001 accepted-only offline study complete; no gameplay or screen calibration.";
    } catch (error) {
      document.body.dataset.temporalStatus = "error";
      document.body.dataset.referenceStatus = "error";
      statusNode.className = "error";
      statusNode.textContent = "Temporal study failed: " + (error && error.stack ? error.stack : String(error));
    }
  }



  // ENGINE001_DUPLICATE_FRAMES_V1: controlled stationery-pointer ENTER_FRAME
  // callbacks after the final accepted point of every frozen stroke.
  // 0, 1, 3 are synthetic frame counts (NOT reconstructed historical timing).
  function renderDuplicateFrameStudy() {
    try {
      if (!window.egret || !egret.Shape || !egret.CanvasRenderer) {
        throw new Error("Native game Egret renderer unavailable.");
      }
      const path = "../data/results/brush_behavior_tests/game_monitor_bridge/" +
        "bb261898-8296-41f5-a333-eb0b81016410/" +
        "game-monitor-run-20261104T040548835772Z-6a17a297.json";
      const req = new XMLHttpRequest();
      req.open("GET",path,false); req.send(null);
      if (req.status !== 200) throw new Error("Pinned monitor input unavailable: " + req.status);
      const input = extractTemporalStrokes(JSON.parse(req.responseText));
      if (input.runId !== "6a17a297-ea14-4527-9527-bfd8de3bd335" ||
          input.sessionId !== "bb261898-8296-41f5-a333-eb0b81016410" ||
          input.strokes.length !== 27 || input.exactChalk !== 1260) {
        throw new Error("Duplicate-frame input violates historical run identity.");
      }
      const mode = "smooth"; // Experimental assumption: no per-stroke mode in run.
      const width = 10, extraFrameCounts = [0,1,3];
      const mask = createBoardMask();
      const webglState = initializeWebGL(null);
      const samples = [], pictures = [];
      const boards = [];
      for (const frames of extraFrameCounts) {
        const result = makeTemporalBoard(input.strokes,width,mode,true,frames);
        const source = renderGraphicsNode(result.shape.$renderNode,false);
        const canvas = composeBoard(source,source.nodeBounds,mask);
        const webgl = renderWebGLProbe(mode,[],width,canvas,webglState,result.shape);
        // Next stroke's full redraw clears all previous transient paths; only
        // duplicates on the FINAL stroke remain in the finished GraphicsNode.
        const expectedPaths = 70 + frames;
        if (result.accepted !== input.exactChalk ||
            result.duplicatePointRejections !== frames * 27 ||
            result.extraFrameRedrawCalls !== frames * 27 ||
            result.graphicsPathCount !== expectedPaths ||
            result.shape.max-result.shape.less !== input.exactChalk) {
          throw new Error("Native Frame replay violated path/CHALK invariant: "+JSON.stringify({frames,expectedPaths,actualPaths:result.graphicsPathCount,accepted:result.accepted,duplicatePointRejections:result.duplicatePointRejections,extraFrameRedrawCalls:result.extraFrameRedrawCalls,quotaUsed:result.shape.max-result.shape.less}));
        }
        samples.push({
          extraStationaryFramesPerStroke:frames,
          totalSyntheticFrameCallbacks:frames*27,
          acceptedPoints:result.accepted,
          duplicatePointRejections:result.duplicatePointRejections,
          extraFrameRedrawCalls:result.extraFrameRedrawCalls,
          fullRedrawCalls:result.fullRedrawCalls,
          incrementalRedrawCalls:result.incrementalRedrawCalls,
          graphicsPathCount:result.graphicsPathCount,
          egretCanvas2dVsWebgl:webgl.comparison,
          webglDrawCalls:webgl.drawCalls
        });
        pictures.push(["frames"+frames+"-canvas2d",canvas],
                      ["frames"+frames+"-webgl",webgl.canvas]);
        boards.push({frames,canvas,webgl:webgl.canvas});
      }
      const baseline = boards[0];
      const comparisons = boards.map(e=>({
        extraStationaryFramesPerStroke:e.frames,
        canvas2dVsBaseline:compareCanvases(baseline.canvas,e.canvas),
        webglVsBaseline:compareCanvases(baseline.webgl,e.webgl)
      }));
      if (comparisons[0].canvas2dVsBaseline.differingPixels !== 0 ||
          comparisons[0].webglVsBaseline.differingPixels !== 0 ||
          pictures.length !== 6) {
        throw new Error("Duplicate-frame baseline or output count mismatch.");
      }
      const manifest={
        schemaVersion:1, experimentId:"ENGINE001_DUPLICATE_FRAMES_V1",
        status:"COMPLETE_OFFLINE_NATIVE_FRAME_EXPERIMENT",
        gameBundleBlobSha:"46cc74de00b6cb5d207b1e1a2ffcd81613b6d388",
        egretBundleBlobSha:"d613d2b97e2436521aa3870478c69e99eac1f19f",
        monitorInputBlobSha:"8eb04ad7331d1e56f4aeb7d0f625c59c1dc57c24",
        runId:input.runId, sessionId:input.sessionId,
        historicalExactChalk:input.exactChalk, acceptedPoints:1260, strokeCount:27,
        lineWidth:width, modeAssumption:"smooth (per-stroke options unavailable)",
        extraFrameCounts, frameInjection:"Immediately after the last accepted sample of each stroke and before onDrawingEnd; pushPoint with identical last coordinate rejected, updateLess and native redraw(false).",
        screenProjection:"UNCALIBRATED",
        renderSize:{width:baseline.canvas.width,height:baseline.canvas.height},
        samples, comparisons, pngCount:pictures.length,
        exclusions:[
          "No actual ENTER_FRAME timing, DOM input, or stage rendering schedule recovered",
          "No live screenshot or same-run Stage/CSS/client/desktop mapping",
          "No new game interaction and no newly measured CHALK",
          "Only duplicate frames at the final point, not arbitrary pauses throughout the stroke",
          "No restoration of original service baseline point"
        ]
      };
      casesNode.textContent="";
      const card=document.createElement("section");
      card.className="fixture";
      card.textContent="ENGINE-001 native stationary pointer redraw diagnostics; offline only.";
      for(const [label,canvas] of pictures) {
        addDownloadLink(card,canvas,"engine001-frames-"+label+".png",label+" PNG");
      }
      casesNode.appendChild(card);
      document.getElementById("renderer-manifest-json").textContent=JSON.stringify(manifest,null,2);
      document.body.dataset.framesStatus="complete";
      document.body.dataset.framesPngCount=String(pictures.length);
      document.body.dataset.referenceStatus="frames_complete";
      statusNode.textContent="ENGINE-001 stationary final-point redraw study complete; screen uncalibrated.";
    } catch(error) {
      document.body.dataset.framesStatus="error";
      document.body.dataset.referenceStatus="error";
      statusNode.className="error";
      statusNode.textContent="Duplicate frame experiment failed: "+(error&&error.stack?error.stack:String(error));
    }
  }

  // ENGINE-001 endpoint comparison: keep 1260 accepted points frozen.
  // ENGINE001_NATIVE_ENDPOINT_OUTLINE5_V1: the same 5-logical-px normal
  // contour appended after the same frozen 27 strokes in all three variants.
  // Points are the 64 frozen-mask cv2.findContours(CHAIN_APPROX_SIMPLE)
  // vertices following a 3-logical-px elliptical erosion. The independent
  // OpenCV analyzer reconstructs and checks this array against frozen mask SHA.
  const ENDPOINT_OUTLINE5_INSET = 3;
  const ENDPOINT_OUTLINE5_WIDTH = 5;
  const ENDPOINT_OUTLINE5_POINTS = [[94,53],[93,54],[88,54],[87,55],[85,55],[84,56],[83,56],[77,62],[77,63],[76,64],[76,65],[75,66],[75,68],[74,69],[74,74],[73,75],[73,165],[74,166],[74,171],[75,172],[75,174],[76,175],[76,176],[77,177],[77,178],[83,184],[84,184],[85,185],[87,185],[88,186],[93,186],[94,187],[366,187],[367,186],[372,186],[373,185],[375,185],[376,184],[377,184],[383,178],[383,177],[384,176],[384,175],[385,174],[385,172],[386,171],[386,166],[387,165],[387,75],[386,74],[386,69],[385,68],[385,66],[384,65],[384,64],[383,63],[383,62],[377,56],[376,56],[375,55],[373,55],[372,54],[367,54],[366,53]];

  function addNativeOutline5(boardInfo) {
    const board = boardInfo.shape;
    board.setRadius(ENDPOINT_OUTLINE5_WIDTH);
    board.setColor(0x000000);
    board.setSmooth(false); // Same native closed normal outline for every variant.
    for (const xy of ENDPOINT_OUTLINE5_POINTS.concat([ENDPOINT_OUTLINE5_POINTS[0]])) {
      const active = board.atom.points[board.atom.points.length - 1];
      const oldLength = active.length;
      board.atom.pushPoint(new egret.Point(xy[0], xy[1]));
      if (board.atom.points[board.atom.points.length - 1].length !== oldLength + 1) {
        throw new Error("Native BoardPane rejected a 5px outline vertex.");
      }
    }
    board.atom.add();
    board.redraw(); // Actual game's full BoardPane/Painter rendering path.
    board.updateLess();
    if (board.max - board.less !== boardInfo.accepted + ENDPOINT_OUTLINE5_POINTS.length + 1) {
      throw new Error("Native outline mutated point count unexpectedly.");
    }
    return boardInfo;
  }

  function makeEndpointBoard(strokes, variant, outline5) {
    if (variant === "game-smooth" || variant === "normal") {
      const board = makeTemporalBoard(strokes, 10, variant === "normal" ? "normal" : "smooth", false);
      if (outline5) addNativeOutline5(board);
      return {board, patchedCalls:0};
    }
    if (variant !== "smooth-drawlast") throw new Error("Unknown endpoint variant.");
    const painter = root.com.magnetjoy.painter.Painter;
    const original = painter.drawSmoothLine;
    let patchedCalls = 0;
    painter.drawSmoothLine = function(graphics, pts, drawFirstHalf, drawLast) {
      // BoardPane.redraw() also visits the current empty atom slot.
      if (!pts || pts.length === 0) {
        return original.call(this, graphics, pts, drawFirstHalf, drawLast);
      }
      if (drawFirstHalf !== true || drawLast !== false) {
        throw new Error("Game BoardPane changed native smooth Painter signature.");
      }
      patchedCalls += 1;
      return original.call(this, graphics, pts, drawFirstHalf, true);
    };
    try {
      const board = makeTemporalBoard(strokes, 10, "smooth", false);
      if (outline5) addNativeOutline5(board);
      if (patchedCalls !== strokes.length * (outline5 ? 2 : 1)) {
        throw new Error("Native forced endpoint did not process each smooth stroke.");
      }
      return {board, patchedCalls};
    } finally {
      painter.drawSmoothLine = original;
    }
  }

  function endpointBoundsAtRow(canvas, logicalY, threshold) {
    if (![1,64,128,254].includes(threshold)) throw new Error("Unsupported alpha threshold");
    const data=canvas.getContext("2d",{willReadFrequently:true}).getImageData(
      0,0,canvas.width,canvas.height).data;
    const cy=Math.round(logicalY * RASTER_SCALE);
    const lo=Math.max(0,cy-2),hi=Math.min(canvas.height-1,cy+2);
    let left=null,right=null,opaqueCount=0;
    for(let y=lo;y<=hi;y+=1) for(let x=0;x<canvas.width;x+=1) {
      if(data[(y*canvas.width+x)*4+3]>=threshold) {
        left=left===null?x:Math.min(left,x);
        right=right===null?x:Math.max(right,x);
        opaqueCount+=1;
      }
    }
    return {threshold,screenScale:RASTER_SCALE,leftBackingX:left,rightBackingX:right,nonzeroBandPixels:opaqueCount};
  }

  function renderEndpointStudy(outline5) {
    try {
      if (!window.egret || !egret.Shape || !egret.CanvasRenderer) {
        throw new Error("Real Egret browser renderer is unavailable.");
      }
      const runPath="../data/results/brush_behavior_tests/game_monitor_bridge/" +
        "bb261898-8296-41f5-a333-eb0b81016410/" +
        "game-monitor-run-20261104T040548835772Z-6a17a297.json";
      const planPath="../data/results/brush_behavior_tests/fill001/plans/" +
        "fill001-rs-preflight-20261104-7.04-rectangle-r10-s5-o0-rep1.json";
      function readJson(path) {
        const request=new XMLHttpRequest();
        request.open("GET",path,false);request.send(null);
        if(request.status!==200)throw new Error("Pinned endpoint evidence HTTP "+request.status+": "+path);
        return JSON.parse(request.responseText);
      }
      const run=extractTemporalStrokes(readJson(runPath));
      const plan=readJson(planPath);
      if(run.runId!=="6a17a297-ea14-4527-9527-bfd8de3bd335" ||
        run.sessionId!=="bb261898-8296-41f5-a333-eb0b81016410" ||
        run.strokes.length!==27 || run.exactChalk!==1260 ||
        !Array.isArray(plan.strokes) || plan.strokes.length!==run.strokes.length) {
        throw new Error("Pinned run/plan identity or count mismatch.");
      }
      const endpointRows=[5,15,16];
      for(let k=4;k<=22;k+=1) {
        const expected=plan.strokes[k].points;
        const actual=run.strokes[k].points;
        if(expected.length!==2 || expected[0].x!==75 || expected[1].x!==385 ||
          actual.length<2 || Math.abs(actual[0].x-76.20833396911621)>1e-7 ||
          Math.abs(actual[actual.length-1].x-389.2083339691162)>1e-7) {
          throw new Error("Identical-plan endpoint cohort has changed: row "+(k+1));
        }
      }
      const variants=["game-smooth","smooth-drawlast","normal"];
      const filenameRoot = outline5 ? "engine001-endpoint-outline5-" : "engine001-endpoint-";
      const mask=createBoardMask();
      const state=initializeWebGL(null);
      const card=document.createElement("section");
      card.className="fixture";
      card.appendChild(document.createTextNode(
        "ENGINE-001 actual game Painter endpoint comparison; offline only; no screen calibration."));
      const aggregate={};
      let pngCount=0;
      for(const variant of variants) {
        const item=makeEndpointBoard(run.strokes,variant,outline5);
        const source=renderGraphicsNode(item.board.shape.$renderNode,false);
        const canvas=composeBoard(source,source.nodeBounds,mask);
        const webgl=renderWebGLProbe("smooth",[],10,canvas,state,item.board.shape);
        for(const [name,output] of [["canvas2d",canvas],["webgl",webgl.canvas]]) {
          addDownloadLink(card,output,filenameRoot+variant+"-all-"+name+".png",variant+" "+name);
          pngCount+=1;
        }
        aggregate[variant]={
          accepted:item.board.accepted,strokeCount:run.strokes.length,
          nativePainterPatchedCalls:item.patchedCalls,
          graphicsPathCount:item.board.graphicsPathCount,
          canvas2dVsWebgl: webgl.comparison, webglDrawCalls:webgl.drawCalls
        };
      }
      const individual=[];
      for(const row of endpointRows) {
        const stroke=run.strokes[row-1];
        const p=stroke.points;
        const last=p[p.length-1],previous=p[p.length-2];
        const report={
          row,strokeId:stroke.strokeId,
          planStart:plan.strokes[row-1].points[0],
          planEnd:plan.strokes[row-1].points[1],
          firstAccepted:p[0],penultimateAccepted:previous,lastAccepted:last,
          smoothTerminalPoint:midpoint(previous,last),variants:{}
        };
        for(const variant of variants) {
          const item=makeEndpointBoard([stroke],variant,outline5);
          const source=renderGraphicsNode(item.board.shape.$renderNode,false);
          const canvas=composeBoard(source,source.nodeBounds,mask);
          const webgl=renderWebGLProbe("smooth",[],10,canvas,state,item.board.shape);
          const pngName=filenameRoot+variant+"-row"+row+"-webgl.png";
          addDownloadLink(card,webgl.canvas,pngName,pngName);
          pngCount+=1;
          report.variants[variant]={
            nativePainterPatchedCalls:item.patchedCalls,
            graphicsPathCount:item.board.graphicsPathCount,
            canvas2dVsWebgl:webgl.comparison,
            boundsByAlpha:[1,64,128,254].map(a=>endpointBoundsAtRow(webgl.canvas,last.y,a))
          };
        }
        individual.push(report);
      }
      if(pngCount!==15 || aggregate["smooth-drawlast"].nativePainterPatchedCalls!==(outline5?54:27) ||
        individual.some(r=>r.variants["smooth-drawlast"].nativePainterPatchedCalls!==(outline5?2:1))) {
        throw new Error("Expected all actual Painter path changes and 15 reference PNGs.");
      }
      casesNode.textContent="";
      casesNode.appendChild(card);
      const manifest={
        schemaVersion:1,experimentId:outline5?"ENGINE001_NATIVE_ENDPOINT_OUTLINE5_V1":"ENGINE001_NATIVE_ENDPOINT_V1",
        status:"COMPLETE_OFFLINE_NATIVE_ENGINE_MEASUREMENT",
        runId:run.runId,sessionId:run.sessionId,exactHistoricalChalk:run.exactChalk,
        gameBundleBlobSha:"46cc74de00b6cb5d207b1e1a2ffcd81613b6d388",
        egretBundleBlobSha:"d613d2b97e2436521aa3870478c69e99eac1f19f",
        monitorInputBlobSha:"8eb04ad7331d1e56f4aeb7d0f625c59c1dc57c24",
        planInputPath:planPath,strokeCount:run.strokes.length,acceptedCount:1260,
        modeAssumption:"smooth for game baseline; historical per-stroke options unavailable",
        syntheticControl:"smooth-drawlast forces only native Painter final lineTo through temporary isolated method wrapper; normal uses native BoardPane.setSmooth(false)",
        browserRaster:"Egret 5.4.1 CanvasRenderer and WebGLRenderer masked actual game BoardPane, 3x backing scale",
        pixelCanvas:{width:1380,height:720},screenProjection:"UNCALIBRATED",
        outline5: outline5 ? {mode:"native_normal_closed_contour",widthLogical:ENDPOINT_OUTLINE5_WIDTH,
          insetLogical:ENDPOINT_OUTLINE5_INSET, vertexCount:ENDPOINT_OUTLINE5_POINTS.length,
          points:ENDPOINT_OUTLINE5_POINTS, appendedPointCount:ENDPOINT_OUTLINE5_POINTS.length+1,
          originalHistoricalChalkUnchanged:true, additionalChalk:"NOT_MEASURED"} : null,
        isolatedRows:endpointRows,aggregate,individual,pngCount,
        exclusions:[
          "No new gameplay or CHALK measurement",
          "No actual per-stroke live screenshot, no frame/DOM scheduling reproduction",
          "No same-run Stage/CSS/desktop mapping; browser pixels cannot be compared directly to original captured screen ROI",
          "Original per-stroke mode/colors, current live game GPU and service point not recovered",
          "Original FILL-001 coverage and leakage thresholds are unchanged"
        ]
      };
      document.getElementById("renderer-manifest-json").textContent=JSON.stringify(manifest,null,2);
      document.body.dataset[outline5?"outlineStatus":"endpointStatus"]="complete";
      document.body.dataset[outline5?"outlinePngCount":"endpointPngCount"]=String(pngCount);
      document.body.dataset.referenceStatus=outline5?"outline_complete":"endpoint_complete";
      statusNode.textContent="ENGINE-001 native endpoint experiment complete; 27 strokes and 3 isolated rows; uncalibrated screen.";
    } catch(error) {
      document.body.dataset[outline5?"outlineStatus":"endpointStatus"]="error";
      document.body.dataset.referenceStatus="error";
      statusNode.className="error";
      statusNode.textContent="Endpoint study failed: "+(error&&error.stack?error.stack:String(error));
    }
  }


  // FILL-001 native three-way multi-stroke comparison, generated from the
  // frozen rectangle by Python; never reads a live run as a synthetic plan.
  // The old single-stroke ENGINE-001 replay and its fail-closed gates stay intact.
  function renderContourFirstNativeStudy() {
    try {
      if (!window.egret || !egret.Shape || !egret.CanvasRenderer ||
          typeof getBoardPaneClass() !== "function") {
        throw new Error("Native Egret and game BoardPane not loaded.");
      }
      const url = "./fill001-contour-first-native-input.json";
      const req = new XMLHttpRequest();
      req.open("GET", url, false);
      req.send(null);
      if (req.status !== 200) throw new Error("Missing generated pinned contour input: HTTP " + req.status);
      const fixture = JSON.parse(req.responseText);
      if (!fixture || fixture.schema !== "FILL001_NATIVE_CONTOUR_FIRST_V1" ||
          fixture.status !== "OFFLINE_SYNTHETIC_INPUT_ONLY" ||
          fixture.shape_id !== "rectangle" ||
          fixture.frozen_mask_sha256 !== "ac1c6660e5986cdf534328c6dbcd5020f631168b1473c24b29e7609eb827998b" ||
          fixture.brush !== 10 || fixture.contour_inset !== 6 ||
          !fixture.cases || Object.keys(fixture.cases).sort().join(",") !==
          "B_sparse_only,C_contour_last,E_contour_first") {
        throw new Error("Frozen contour-first native fixture identity mismatch.");
      }
      const state = initializeWebGL(null);
      const mask = createBoardMask();
      const captures = {};
      const manifest = {
        schema: "FILL001_NATIVE_CONTOUR_FIRST_V1",
        status: "OFFLINE_NATIVE_EGRET_RENDERED",
        sourceMaskSha256: fixture.frozen_mask_sha256,
        sourcePlanSignature: fixture.baseline_plan_signature,
        engineVersion: egret.Capabilities.engineVersion,
        nativeRenderer: state.glInfo,
        stageGeometry: "LOCAL_BOARD_ONLY_NOT_V3_SCREEN",
        cases: {},
        comparisons: {},
        measuredChalk: null, executorReady: false,
        limitations: [
          "Native BoardPane/Egret WebGL only; not a V3 same-run Stage/screen match.",
          "Synthetic sparse strokes do not reconstruct per-frame accepted points.",
          "No game runtime or exact CHALK for these candidate strategies."
        ]
      };
      const expected = { B_sparse_only: 27, C_contour_last: 28, E_contour_first: 28 };
      for (const name of ["B_sparse_only", "C_contour_last", "E_contour_first"]) {
        const strokes = fixture.cases[name];
        if (!Array.isArray(strokes) || strokes.length !== expected[name] ||
            strokes.some(stroke => stroke.width !== 10 || stroke.mode !== "normal" ||
              !Array.isArray(stroke.points) || stroke.points.length < 2 ||
              stroke.points.some(p => !Number.isInteger(p.x) || !Number.isInteger(p.y) ||
                p.x < 0 || p.x >= 460 || p.y < 0 || p.y >= 240))) {
          throw new Error("Malformed native contour stroke inputs for " + name);
        }
        const replay = strokes.map((stroke,i) => ({
          strokeId: name + "-stroke-" + i,
          points: stroke.points
        }));
        const board = makeTemporalBoard(replay, 10, "normal", false);
        const expectedPoints = strokes.reduce((sum,s) => sum + s.points.length,0);
        if (board.accepted !== expectedPoints) {
          throw new Error("Native BoardPane rejected generated points in " + name);
        }
        const source = renderGraphicsNode(board.shape.$renderNode,false);
        const composed = composeBoard(source, source.nodeBounds, mask);
        const native = renderWebGLProbe("normal",[],10,composed,state,board.shape);
        captures[name] = native.canvas;
        manifest.cases[name] = {
          strokeCount: strokes.length, acceptedSyntheticPoints: board.accepted,
          drawCalls: native.drawCalls, graphicsPathCount: board.graphicsPathCount,
          sceneDiagnostics: native.sceneDiagnostics,
          browserNativeBackend: state.glInfo.renderer,
          canvas2DVsWebGL: native.comparison,
          pngName: "fill001-native-" + name + ".png"
        };
      }
      manifest.comparisons = {
        contourFirstVsLast: compareCanvases(captures.C_contour_last,captures.E_contour_first),
        sparseVsContourFirst: compareCanvases(captures.B_sparse_only,captures.E_contour_first)
      };
      casesNode.textContent = "";
      const card = document.createElement("section");
      card.className = "fixture";
      card.textContent = "FILL-001 isolated native BoardPane multi-stroke test; NOT live E5.";
      for (const [name,canvas] of Object.entries(captures)) {
        addDownloadLink(card,canvas,"fill001-native-" + name + ".png",name);
      }
      casesNode.appendChild(card);
      document.getElementById("renderer-manifest-json").textContent = JSON.stringify(manifest,null,2);
      document.body.dataset.contourNativeStatus = "complete";
      document.body.dataset.referenceStatus = "contour_native_complete";
      document.body.dataset.pngCount = "3";
      statusNode.textContent = "Native FILL-001 contour-first comparison complete (not game screen calibration).";
    } catch(error) {
      document.body.dataset.contourNativeStatus = "error";
      document.body.dataset.referenceStatus = "error";
      statusNode.className = "error";
      statusNode.textContent = "Native contour-first study failed: " +
        (error && error.stack ? error.stack : String(error));
    }
  }


  // FILL-001 contour trim V2: same native renderer, no gameplay/CHALK.
  function renderContourTrimNativeStudy(mixed) {
    mixed = mixed === true;
    try {
      const req = new XMLHttpRequest();
      req.open("GET", mixed ? "./fill001-contour-mixed-native-input.json"
                            : "./fill001-contour-trims-native-input.json", false);
      req.send(null);
      if (req.status !== 200) throw new Error("Missing V2 native input fixture.");
      const fixture = JSON.parse(req.responseText);
      const names = mixed ? ["E_contour_10", "H_mixed_trim_0", "H_mixed_trim_1",
        "H_mixed_trim_2", "H_mixed_trim_3", "H_mixed_trim_4"]
        : ["B_sparse_only","C_contour_last","E_contour_first",
           "G_trim_1","G_trim_2","G_trim_3","G_trim_4"];
      if (!fixture || fixture.schema !== (mixed ? "FILL001_NATIVE_MIXED_CONTOUR_V3"
                                   : "FILL001_NATIVE_CONTOUR_EDGE_TRIMS_V2") ||
          fixture.status !== "OFFLINE_SYNTHETIC_INPUT_ONLY" ||
          fixture.shape_id !== "rectangle" ||
          fixture.frozen_mask_sha256 !== "ac1c6660e5986cdf534328c6dbcd5020f631168b1473c24b29e7609eb827998b" ||
          JSON.stringify(fixture.tested_trim_px) !== (mixed ? "[0,1,2,3,4]" : "[1,2,3,4]") ||
          Object.keys(fixture.cases||{}).sort().join(",") !== names.slice().sort().join(",")) {
        throw new Error("Native contour trim V2 fixture provenance mismatch.");
      }
      const state = initializeWebGL(null);
      const mask = createBoardMask();
      const captures = {};
      const cases = {};
      for (const name of names) {
        const strokes = fixture.cases[name];
        const expectedStrokes = name === "B_sparse_only" ? 27 : 28;
        if (!Array.isArray(strokes) || strokes.length !== expectedStrokes ||
            strokes.some((st,i) => (mixed ? st.width !== (i===0 && name.startsWith("H_") ? 5 : 10) : st.width !== 10) || st.mode !== "normal" ||
              !Array.isArray(st.points) || st.points.length < 2 ||
              st.points.some(p=> !Number.isInteger(p.x) || !Number.isInteger(p.y) ||
                p.x < 0 || p.y < 0 || p.x >= 460 || p.y >= 240))) {
          throw new Error("Unexpected V2 native stroke geometry: "+name);
        }
        const replay = strokes.map((stroke,i)=>({
          strokeId: name + "-stroke-" + i, points: stroke.points,
          width: stroke.width
        }));
        const board = makeTemporalBoard(replay,10,"normal",false);
        if (board.accepted !== strokes.reduce((acc,stroke)=>acc+stroke.points.length,0))
          throw new Error("Unexpected V2 native accepted sample count");
        const source=renderGraphicsNode(board.shape.$renderNode,false);
        const composed=composeBoard(source,source.nodeBounds,mask);
        const native=renderWebGLProbe("normal",[],10,composed,state,board.shape);
        captures[name]=native.canvas;
        cases[name]={
          strokeCount: strokes.length, acceptedSyntheticPoints: board.accepted,
          pngName: "fill001-native-"+name+".png",
          webglDrawCalls: native.drawCalls,
          sceneDiagnostics: native.sceneDiagnostics,
          canvas2DVsWebGL: native.comparison
        };
      }
      const reference = captures[mixed ? "E_contour_10" : "E_contour_first"];
      const comparisons = mixed ? {} : {
        contourFirstVsLast: compareCanvases(reference,captures.C_contour_last),
        sparseVsContourFirst: compareCanvases(captures.B_sparse_only,reference)
      };
      for (const trim of (mixed ? [0,1,2,3,4] : [1,2,3,4])) {
        comparisons["contourFirstVsTrim"+trim] = compareCanvases(
          reference,captures[mixed ? "H_mixed_trim_"+trim : "G_trim_"+trim]);
      }
      if ((!mixed && (comparisons.contourFirstVsLast.differingPixels !== 0 ||
           comparisons.sparseVsContourFirst.differingPixels <= 0)) ||
          (mixed ? [0,1,2,3,4] : [1,2,3,4]).some(trim =>
            comparisons["contourFirstVsTrim"+trim].differingPixels <= 0)) {
        throw new Error("Native contour controls lack expected geometry differences.");
      }
      const manifest = {
        schema:mixed ? "FILL001_NATIVE_MIXED_CONTOUR_V3" : "FILL001_NATIVE_CONTOUR_EDGE_TRIMS_V2",
        status:"OFFLINE_NATIVE_EGRET_RENDERED",
        sourceMaskSha256:fixture.frozen_mask_sha256,
        sourcePlanSignature:fixture.baseline_plan_signature,
        testedTrimPx: fixture.tested_trim_px,
        engineVersion: egret.Capabilities.engineVersion,
        nativeRenderer:state.glInfo,
        localBackingOnly: true,
        mixedBrushWidths: mixed ? [5,10] : [10],
        measuredChalk:null, executorReady:false,
        cases,comparisons,
        limitations:[
          "Synthetic two-point normal line samples, not V3 accepted-point replay",
          "Local BoardPane framebuffer only, not game Stage/screen RGB",
          "No live CHALK, no direct PNG quality acceptance"
        ]
      };
      casesNode.textContent="";
      const card=document.createElement("section");
      card.className="fixture";
      card.textContent="FILL-001 V2 native endpoint-trim research; no live gameplay.";
      for(const [name,canvas] of Object.entries(captures)) {
        addDownloadLink(card,canvas,"fill001-native-"+name+".png",name);
      }
      casesNode.appendChild(card);
      document.getElementById("renderer-manifest-json").textContent=JSON.stringify(manifest,null,2);
      document.body.dataset[mixed ? "contourMixedStatus" : "contourTrimStatus"]="complete";
      document.body.dataset.referenceStatus="contour_trim_complete";
      statusNode.textContent="FILL-001 V2 native endpoint-trim comparison complete.";
    } catch(error) {
      document.body.dataset[mixed ? "contourMixedStatus" : "contourTrimStatus"]="error";
      document.body.dataset.referenceStatus="error";
      statusNode.className="error";
      statusNode.textContent="V2 native trim replay failed: "+
        (error&&error.stack?error.stack:String(error));
    }
  }



  // FILL-001 V4: six lower edge thin-brush candidates on the V2 trim3 control.
  function renderFill001BottomRepairStudy() {
    try {
      const req=new XMLHttpRequest();
      req.open("GET","./fill001-bottom-repair-native-input.json",false);
      req.send(null);
      if(req.status!==200) throw new Error("Native V4 pinned input missing");
      const fixture=JSON.parse(req.responseText);
      const names=["G_trim_3_control"];
      for (const width of [1,2,3]) {
        for (const y of [189,190]) names.push("J_bottom_y"+y+"_w"+width);
      }
      if(fixture.schema!=="FILL001_NATIVE_BOTTOM_REPAIR_V4" ||
        fixture.status!=="OFFLINE_SYNTHETIC_INPUT_ONLY" ||
        fixture.shape_id!=="rectangle" ||
        fixture.frozen_mask_sha256!==
          "ac1c6660e5986cdf534328c6dbcd5020f631168b1473c24b29e7609eb827998b" ||
        fixture.baseline_variant!=="FILL001_NATIVE_CONTOUR_EDGE_TRIMS_V2/G_trim_3" ||
        fixture.baseline_endpoint_trim!==3 ||
        JSON.stringify(fixture.candidate_widths)!=="[1,2,3]" ||
        JSON.stringify(fixture.candidate_y)!=="[189,190]" ||
        JSON.stringify(fixture.bottom_line_endpoints)!=="[97,363]" ||
        Object.keys(fixture.cases||{}).sort().join(",")!==names.slice().sort().join(",")) {
        throw new Error("Native V4 frozen provenance mismatch");
      }
      const state=initializeWebGL(null), mask=createBoardMask();
      const captures={}, cases={}, comparisons={};
      for(const name of names) {
        const strokes=fixture.cases[name];
        const control=name==="G_trim_3_control";
        const expectedCount=control?28:29;
        if (!Array.isArray(strokes) || strokes.length!==expectedCount ||
          strokes.some((st,i)=>{
            const expectedWidth=i<28?10:Number(name.split("_w")[1]);
            return st.width!==expectedWidth || st.mode!=="normal" ||
              !Array.isArray(st.points) || st.points.length<2 ||
              st.points.some(p=>!Number.isInteger(p.x)||!Number.isInteger(p.y)||
                p.x<0||p.y<0||p.x>=460||p.y>=240);
          }) ||
          (control?false:JSON.stringify(strokes[28].points)!==
            JSON.stringify([{x:97,y:Number(name.split("_y")[1].split("_w")[0])},
                            {x:363,y:Number(name.split("_y")[1].split("_w")[0])}]))) {
          throw new Error("V4 native input geometry or width invalid: "+name);
        }
        const replay=strokes.map((st,i)=>({
          strokeId:name+"-stroke-"+i, points:st.points,width:st.width
        }));
        const board=makeTemporalBoard(replay,10,"normal",false);
        const expectedPoints=strokes.reduce((n,st)=>n+st.points.length,0);
        if(board.accepted!==expectedPoints) throw new Error("V4 accepted point mismatch");
        const source=renderGraphicsNode(board.shape.$renderNode,false);
        const composed=composeBoard(source,source.nodeBounds,mask);
        const native=renderWebGLProbe("normal",[],10,composed,state,board.shape);
        if(native.canvas.width!==1380||native.canvas.height!==720) {
          throw new Error("V4 native backing dimension mismatch");
        }
        captures[name]=native.canvas;
        cases[name]={
          strokeCount:strokes.length,acceptedSyntheticPoints:board.accepted,
          pngName:"fill001-native-"+name+".png",
          sceneDiagnostics:native.sceneDiagnostics,
          webglDrawCalls:native.drawCalls,
          canvas2DVsWebGL:native.comparison
        };
      }
      for(const name of names.slice(1)) {
        const compare=compareCanvases(captures.G_trim_3_control,captures[name]);
        comparisons[name]=compare;
      }
      const manifest={
        schema:"FILL001_NATIVE_BOTTOM_REPAIR_V4",
        status:"OFFLINE_NATIVE_EGRET_RENDERED",
        sourceMaskSha256:fixture.frozen_mask_sha256,
        sourcePlanSignature:fixture.baseline_plan_signature,
        baselineVariant:fixture.baseline_variant,
        bottomLineEndpoints:fixture.bottom_line_endpoints,
        testedWidths:fixture.candidate_widths,
        testedYs:fixture.candidate_y,
        engineVersion:egret.Capabilities.engineVersion,
        nativeRenderer:state.glInfo,
        localBackingOnly:true,
        measuredChalk:null,executorReady:false,
        cases,comparisons,
        limitations:[
          "27 synthetic 2-point lines plus contour; not real accepted game samples",
          "Local Egret BoardPane WebGL; native alpha only, no run-bound screen RGB",
          "No actual game CHALK or quality acceptance"
        ]
      };
      casesNode.textContent="";
      const card=document.createElement("section");
      card.className="fixture";
      card.textContent="FILL001 V4 thin bottom stripe isolated native candidates; no gameplay.";
      for(const name of names) {
        addDownloadLink(card,captures[name],"fill001-native-"+name+".png",name);
      }
      casesNode.appendChild(card);
      document.getElementById("renderer-manifest-json").textContent=
        JSON.stringify(manifest,null,2);
      document.body.dataset.bottomRepairStatus="complete";
      document.body.dataset.referenceStatus="bottom_repair_complete";
      statusNode.textContent="Native FILL001 V4 bottom repair experiment complete.";
    } catch(error) {
      document.body.dataset.bottomRepairStatus="error";
      document.body.dataset.referenceStatus="error";
      statusNode.className="error";
      statusNode.textContent="Native V4 bottom repair failed: "+
        (error&&error.stack?error.stack:String(error));
    }
  }


  // DEC-030 V5: local Egret-only frozen rectangle lateral trim versus
  // bottom two-footprint combinations, never an executable game plan.
  function renderFill001ChalkFirstV5Study() {
    try {
      const req=new XMLHttpRequest();
      req.open("GET","./fill001-chalk-first-v5-native-input.json",false);
      req.send(null);
      if(req.status!==200) throw new Error("Pinned V5 JSON input missing");
      const fixture=JSON.parse(req.responseText);
      const names=["V4_y190_w2_control"];
      for (const trim of [0,1,2,3]) {
        for(const [y,w] of [[190,2],[189,3]]) {
          names.push("K_trim_"+trim+"_y"+y+"_w"+w);
        }
      }
      if(fixture.schema!=="FILL001_CHALK_FIRST_NATIVE_V5" ||
        fixture.status!=="OFFLINE_SYNTHETIC_INPUT_ONLY" ||
        fixture.quality_policy_id!=="FILL001_CHALK_FIRST_PERIMETER_V2" ||
        fixture.frozen_mask_sha256!==
          "ac1c6660e5986cdf534328c6dbcd5020f631168b1473c24b29e7609eb827998b" ||
        fixture.baseline_variant!=="FILL001_NATIVE_BOTTOM_REPAIR_V4/J_bottom_y190_w2" ||
        JSON.stringify(fixture.lateral_trim_values)!=="[0,1,2,3]" ||
        JSON.stringify(fixture.bottom_variants)!==
          JSON.stringify([{y:190,width:2},{y:189,width:3}]) ||
        JSON.stringify(fixture.bottom_line_endpoints)!=="[97,363]" ||
        fixture.game_png_quality_gate!=="NOT_EVALUATED" ||
        fixture.measured_chalk!==null || fixture.executor_ready!==false ||
        JSON.stringify(Object.keys(fixture.cases||{}))!==JSON.stringify(names)) {
        throw new Error("V5 protocol/frozen identity mismatch");
      }
      const state=initializeWebGL(null), mask=createBoardMask();
      const captures={}, cases={}, comparisons={};
      for(const name of names) {
        const strokes=fixture.cases[name];
        let expectedY=190,expectedW=2;
        if(name!=="V4_y190_w2_control"){
          const suffix=name.match(/^K_trim_([0-3])_y(189|190)_w([23])$/);
          if(!suffix || !((suffix[2]==="190" && suffix[3]==="2") ||
                          (suffix[2]==="189" && suffix[3]==="3"))) {
            throw new Error("V5 unplanned case name: "+name);
          }
          expectedY=Number(suffix[2]); expectedW=Number(suffix[3]);
        }
        if(!Array.isArray(strokes)||strokes.length!==29||
          strokes.some((stroke,i)=>stroke.width!==(i===28?expectedW:10) ||
            stroke.mode!=="normal"||!Array.isArray(stroke.points)||
            stroke.points.length<2||stroke.points.some(p=>
              !Number.isInteger(p.x)||!Number.isInteger(p.y)||
              p.x<0||p.y<0||p.x>=460||p.y>=240))||
          JSON.stringify(strokes[28].points)!==
            JSON.stringify([{x:97,y:expectedY},{x:363,y:expectedY}])) {
          throw new Error("V5 invalid widths/endpoints: "+name);
        }
        const replay=strokes.map((st,i)=>({
          strokeId:name+"-"+i,points:st.points,width:st.width
        }));
        const board=makeTemporalBoard(replay,10,"normal",false);
        const expected=strokes.reduce((n,st)=>n+st.points.length,0);
        if(board.accepted!==expected)throw new Error("V5 Egret point replay mismatch");
        const source=renderGraphicsNode(board.shape.$renderNode,false);
        const composed=composeBoard(source,source.nodeBounds,mask);
        const native=renderWebGLProbe("normal",[],10,composed,state,board.shape);
        if(native.canvas.width!==1380||native.canvas.height!==720) {
          throw new Error("V5 native backing size invalid");
        }
        captures[name]=native.canvas;
        cases[name]={
          strokeCount:29,acceptedSyntheticPoints:board.accepted,
          pngName:"fill001-native-"+name+".png",
          sceneDiagnostics:native.sceneDiagnostics,
          webglDrawCalls:native.drawCalls,
          canvas2DVsWebGL:native.comparison
        };
      }
      for(const name of names.slice(1)) {
        comparisons[name]=compareCanvases(captures[names[0]],captures[name]);
      }
      const manifest={
        schema:fixture.schema,
        status:"OFFLINE_NATIVE_EGRET_RENDERED",
        qualityPolicyId:fixture.quality_policy_id,
        sourceMaskSha256:fixture.frozen_mask_sha256,
        sourcePlanSignature:fixture.baseline_plan_signature,
        baselineVariant:fixture.baseline_variant,
        lateralTrimValues:fixture.lateral_trim_values,
        bottomVariants:fixture.bottom_variants,
        bottomLineEndpoints:fixture.bottom_line_endpoints,
        engineVersion:egret.Capabilities.engineVersion,
        nativeRenderer:state.glInfo,
        localBackingOnly:true,
        measuredChalk:null,executorReady:false,
        gamePngQualityGate:"NOT_EVALUATED",
        cases,comparisons,
        limitations:[
          "This is native alpha/coverage only; not run-bound screen RGB",
          "Three brush widths in one replay are research-only, not validated runtime brush changes",
          "No exact CHALK or E4; cannot rank by real cost or authorize game execution"
        ]
      };
      casesNode.textContent="";
      const card=document.createElement("section");
      card.className="fixture";
      card.textContent="DEC-030 FILL001 V5 native 9 predeclared candidates; no gameplay.";
      for(const name of names) {
        addDownloadLink(card,captures[name],"fill001-native-"+name+".png",name);
      }
      casesNode.appendChild(card);
      document.getElementById("renderer-manifest-json").textContent=
        JSON.stringify(manifest,null,2);
      document.body.dataset.chalkFirstV5Status="complete";
      document.body.dataset.referenceStatus="chalk_first_v5_complete";
      statusNode.textContent="V5 native BoardPane WebGL candidates complete, no CHALK.";
    } catch(error) {
      document.body.dataset.chalkFirstV5Status="error";
      document.body.dataset.referenceStatus="error";
      statusNode.className="error";
      statusNode.textContent="V5 native failed: "+
        (error&&error.stack?error.stack:String(error));
    }
  }

  // FILL-001 phase A: finite, predeclared native brush footprint probes.
  // No source game run, browser pointer events, or executable game plan.
  function renderFill001FootprintStudy() {
    try {
      if (!window.egret || !egret.Shape || !egret.CanvasRenderer ||
          typeof getBoardPaneClass() !== "function") {
        throw new Error("FILL001 native footprint requires actual Egret BoardPane.");
      }
      const lines = {
        horizontal: [{x:130,y:120},{x:330,y:120}],
        vertical: [{x:230,y:40},{x:230,y:200}],
        diagonal: [{x:130,y:60},{x:330,y:180}],
        corner: [{x:150,y:70},{x:300,y:70},{x:300,y:180}]
      };
      const definitions = [];
      for (const width of [5,10]) {
        for (const orientation of ["horizontal","vertical","diagonal","corner"]) {
          definitions.push({
            id:"normal_"+orientation+"_w"+width, mode:"normal", width,
            points:lines[orientation].map(p=>({x:p.x,y:p.y}))
          });
        }
        definitions.push({
          id:"smooth_horizontal_w"+width, mode:"smooth", width,
          points:lines.horizontal.map(p=>({x:p.x,y:p.y}))
        });
      }
      const native = initializeWebGL(null);
      const mask = createBoardMask();
      const manifest = {
        schema:"FILL001_NATIVE_FOOTPRINT_A_V1",
        status:"OFFLINE_NATIVE_EGRET_RENDERED",
        engineVersion:egret.Capabilities.engineVersion,
        nativeRenderer:native.glInfo,
        canvasSize:{width:1380,height:720},
        logicalBoard:{width:460,height:240},
        scale:3,
        alphaThresholds:[1,64,128,254],
        originalGameCapture:null,
        measuredChalk:null,
        gameQualityGate:"NOT_EVALUATED",
        liveStageMapping:"NOT_EVALUATED",
        executorReady:false,
        cases:[]
      };
      casesNode.textContent="";
      const card=document.createElement("section");
      card.className="fixture";
      card.textContent="FILL-001 phase A: isolated real Egret brush footprints; not live playback.";
      for (const definition of definitions) {
        const strokes=[{
          strokeId:"footprint-"+definition.id,
          points:definition.points
        }];
        const board=makeTemporalBoard(strokes,definition.width,definition.mode,false);
        if (board.accepted!==definition.points.length) {
          throw new Error("Unexpected accepted point count in "+definition.id);
        }
        const source=renderGraphicsNode(board.shape.$renderNode,false);
        const composed=composeBoard(source,source.nodeBounds,mask);
        const result=renderWebGLProbe(
          definition.mode,definition.points,definition.width,composed,native,board.shape
        );
        if (!result.sceneDiagnostics.stageAttached ||
            result.sceneDiagnostics.boardRenderMode !== 3 ||
            result.canvas.width!==1380 || result.canvas.height!==720) {
          throw new Error("Native stage/BoardPane configuration rejected for "+definition.id);
        }
        const pngName="fill001-footprint-"+definition.id+".png";
        addDownloadLink(card,result.canvas,pngName,definition.id);
        manifest.cases.push({
          id:definition.id,mode:definition.mode,width:definition.width,
          points:definition.points,pngName,
          acceptedSyntheticVerticesNotChalk:board.accepted,
          graphicsPathCount:board.graphicsPathCount,
          webglDrawCalls:result.drawCalls,
          sceneDiagnostics:result.sceneDiagnostics,
          canvas2DVsWebGL:result.comparison
        });
      }
      if (manifest.cases.length!==10) throw new Error("Invalid footprint probe count");
      casesNode.appendChild(card);
      document.getElementById("renderer-manifest-json").textContent=
        JSON.stringify(manifest,null,2);
      document.body.dataset.fill001FootprintStatus="complete";
      document.body.dataset.referenceStatus="fill001_footprint_complete";
      statusNode.textContent="10 native Egret FILL-001 footprint probes complete (offline only).";
    } catch(error) {
      document.body.dataset.fill001FootprintStatus="error";
      document.body.dataset.referenceStatus="error";
      statusNode.className="error";
      statusNode.textContent="Native footprint probe failed: "+
        (error&&error.stack?error.stack:String(error));
    }
  }

  function renderAll() {
    try {
      if (!window.egret || !egret.Shape || !egret.CanvasRenderer) {
        throw new Error("Egret 5.4.1 bundle did not expose Shape/CanvasRenderer.");
      }
      if (!root.com || !root.com.magnetjoy || !root.com.magnetjoy.pet ||
          !root.com.magnetjoy.pet.ui || !root.com.magnetjoy.pet.ui.board ||
          typeof root.com.magnetjoy.pet.ui.board.BoardPane !== "function") {
        throw new Error("Game bundle did not expose the actual BoardPane class.");
      }
      casesNode.textContent = "";
      const mask = createBoardMask();
      const liveRunInput = getLiveRunInput();
      const liveRuntimeProfile = liveRunInput ? buildRuntimeProfileFromRun(liveRunInput) : null;
      const manifest = {
        schemaVersion: 2,
        referenceType: "Actual game BoardPane CanvasRenderer and WebGL renderer reference",
        engineVersion: egret.Capabilities.engineVersion,
        sourceBundles: [
          {
            path: "gameEngine/mergeEngine_df2e5bc5.js",
            blobSha: "d613d2b97e2436521aa3870478c69e99eac1f19f"
          },
          {
            path: "gameEngine/main.min_653f95bc.js",
            blobSha: "46cc74de00b6cb5d207b1e1a2ffcd81613b6d388"
          }
        ],
        gameBoardClass: "com.magnetjoy.pet.ui.board.BoardPane",
        browser: {
          userAgent: navigator.userAgent || null,
          platform: navigator.platform || null,
          devicePixelRatio: window.devicePixelRatio || 1,
          viewport: { width: window.innerWidth, height: window.innerHeight }
        },
        renderMode: "Actual BoardPane GraphicsNode rendered by Egret CanvasRenderer and WebGLRenderer; GL backend recorded below",
        board: { width: BOARD_WIDTH, height: BOARD_HEIGHT },
        rasterScale: RASTER_SCALE,
        runtimeProfile: liveRuntimeProfile || {
          source: "offline_fixture_defaults",
          canvasScaleFactor: RUNTIME_CANVAS_SCALE_FACTOR,
          canvasScaleX: RASTER_SCALE,
          canvasScaleY: RASTER_SCALE,
          boardWidth: BOARD_WIDTH,
          boardHeight: BOARD_HEIGHT,
          profileStatus: "not_bound_to_live_run",
          note: "Synthetic fixture mode only. No stale stage, canvas backing, viewport or screen values are asserted."
        },
        mask: {
          type: "Egret Shape drawRoundRect",
          ellipseWidthArgument: MASK_ELLIPSE_SIZE,
          ellipseHeightArgument: MASK_ELLIPSE_SIZE,
          effectiveCornerRadiusLogicalPx: MASK_ELLIPSE_SIZE / 2,
          clipping: "Actual BoardPane.mask and scrollRect are rendered by Egret WebGLRenderer; Canvas2D destination-in remains a comparison reference"
        },
        webglComposite: "actual Egret WebGLRenderer mask+scrollRect output is captured separately; Canvas2D composite retained as comparison reference",
        actualBoardPaneComparison: "actual BoardPane GraphicsNode pixel-compared with manual path transcription including transparent resetBg rectangle",
        webglProbe: {
          status: "initialized",
          backend: "Egret WebGLRenderer",
          outputSize: null,
          glInfo: null,
          contextAttributes: null,
          textureParameters: null,
          comparisons: []
        },
        stageLevelCompositor: { status: liveRuntimeProfile ? "pending" : "not_run_no_run_bound_profile" },
        fixtures: []
      };

      const webglState = initializeWebGL(liveRuntimeProfile);
      manifest.webglProbe.outputSize = webglState.outputSize;
      manifest.webglProbe.glInfo = webglState.glInfo;
      manifest.webglProbe.contextAttributes = webglState.contextAttributes;

      for (const fixture of fixtureList(liveRunInput)) {
        for (const lineWidth of fixture.lineWidths || LINE_WIDTHS) {
          const actual = makeActualBoardPane(fixture.mode, fixture.points, lineWidth);
          const manual = makeManualBoardPane(fixture.mode, fixture.points, lineWidth);
          const source = renderGraphicsNode(actual.shape.$renderNode, false);
          const manualSource = renderGraphicsNode(manual.shape.$renderNode, false);
          const manualTranscriptionMatch = compareCanvases(source.canvas, manualSource.canvas);
          if (!manualTranscriptionMatch.equal) {
            throw new Error("Manual path transcription differs from actual BoardPane for " +
              fixture.id + " width " + lineWidth + ": " + JSON.stringify(manualTranscriptionMatch));
          }
          const board = composeBoard(source, source.nodeBounds, mask);
          const webgl = renderWebGLProbe(
            fixture.mode, fixture.points, lineWidth, board, webglState
          );
          if (!manifest.webglProbe.textureParameters) {
            manifest.webglProbe.textureParameters = webgl.textureParameters;
          }
          manifest.webglProbe.comparisons.push({
            fixture: fixture.id,
            lineWidth,
            ...webgl.sceneDiagnostics,
            ...webgl.comparison
          });
          const stageLevelVariants = liveRuntimeProfile && fixture.id === "live-accepted-points"
            ? renderStageLevelVariants(fixture.mode, fixture.points, lineWidth, webgl.canvas, liveRuntimeProfile, webglState)
            : [];
          const terminal = terminalPoint(fixture.points, fixture.mode === "smooth", false);
          const entry = {
            id: fixture.id,
            mode: fixture.mode,
            sourceRunId: fixture.sourceRunId || null,
            lineWidth,
            points: fixture.points,
            commands: actual.commands,
            actualBoardPane: true,
            manualTranscriptionMatch,
            webglPixelComparison: webgl.comparison,
            webglSceneDiagnostics: webgl.sceneDiagnostics,
            webglTextureParameters: webgl.textureParameters,
            stageLevelCompositor: stageLevelVariants.map(variant => ({
              id: variant.id, backend: variant.backend, placement: variant.placement,
              textureParameters: variant.textureParameters, contextAttributes: variant.contextAttributes,
              sceneDiagnostics: variant.sceneDiagnostics, drawCalls: variant.drawCalls,
              rendererBackend: variant.rendererBackend, comparisonToA: variant.comparisonToA
            })),
            nodeBounds: source.nodeBounds,
            sourceTextureSize: source.skippedByWebGLRenderer
              ? null
              : { width: source.pixelWidth, height: source.pixelHeight },
            sourceScale: { x: source.scaleX, y: source.scaleY },
            rasterDisposition: source.skippedByWebGLRenderer
              ? "skipped-by-WebGLRenderer-empty-graphics-node"
              : "actual-BoardPane-CanvasRenderer-source-raster",
            smoothPathTerminalPoint: terminal,
            lastAcceptedPoint: fixture.points[fixture.points.length - 1],
            note: source.skippedByWebGLRenderer
              ? "Unexpected empty BoardPane GraphicsNode; inspect resetBg and drawData."
              : fixture.mode === "smooth"
                ? "Actual BoardPane calls Painter.drawSmoothLine(graphics, points, true, false); drawLast=false is explicit, so final lineTo(lastPoint) is not emitted."
                : "Actual BoardPane calls Painter.drawNormalLine; final accepted point is included in the path."
          };
          manifest.fixtures.push(entry);

          const card = document.createElement("section");
          card.className = "fixture";
          const heading = document.createElement("h3");
          heading.textContent = fixture.id + " — " + fixture.mode + " — lineWidth " + lineWidth;
          card.appendChild(heading);

          const image = document.createElement("img");
          image.alt = fixture.id + " masked board output";
          image.src = board.toDataURL("image/png");
          card.appendChild(image);

          const details = document.createElement("pre");
          details.textContent = JSON.stringify({
            nodeBounds: source.nodeBounds,
            sourceTextureSize: [source.pixelWidth, source.pixelHeight],
            sourceScale: [source.scaleX, source.scaleY],
            smoothPathTerminalPoint: terminal,
            lastAcceptedPoint: entry.lastAcceptedPoint,
            rasterDisposition: entry.rasterDisposition,
            actualBoardPane: entry.actualBoardPane,
            manualTranscriptionMatch: entry.manualTranscriptionMatch
          }, null, 2);
          card.appendChild(details);

          const links = document.createElement("div");
          links.className = "downloads";
          addDownloadLink(links, source.canvas,
            fixture.id + "-width-" + lineWidth + "-source-reference.png",
            source.skippedByWebGLRenderer ? "Download transparent no-op reference" : "Download source raster reference");
          addDownloadLink(links, board,
            fixture.id + "-width-" + lineWidth + "-masked-board-reference.png", "Download Canvas2D masked-board reference");
          addDownloadLink(links, webgl.canvas,
            fixture.id + "-width-" + lineWidth + "-webgl-board-reference.png", "Download actual WebGL board reference");
          for (const variant of stageLevelVariants) {
            addDownloadLink(links, variant.canvas,
              "stage-level-" + variant.id + "-" + variant.backend.toLowerCase() + "-" +
                variant.placement.rounding + ".png",
              "Download Stage variant " + variant.id + " (" + variant.backend + ")");
          }
          card.appendChild(links);
          casesNode.appendChild(card);
        }
      }

      manifest.stageLevelCompositor.status = liveRuntimeProfile ? "generated_four_offline_variants" : "not_run_no_run_bound_profile";
      manifest.stageLevelCompositor.variantCount = liveRuntimeProfile ? 4 : 0;
      manifest.webglProbe.status = "complete";
      manifest.webglProbe.comparisonCount = manifest.webglProbe.comparisons.length;
      document.body.dataset.webglStatus = "complete";
      document.body.dataset.webglComparisonCount = String(manifest.webglProbe.comparisonCount);

      const json = JSON.stringify(manifest, null, 2);
      document.getElementById("renderer-manifest-json").textContent = json;
      document.body.dataset.referenceStatus = "complete";
      document.body.dataset.fixtureCount = String(manifest.fixtures.length);
      document.body.dataset.pngCount = String(casesNode.querySelectorAll("a[download$='.png']").length);
      const blob = new Blob([json], { type: "application/json" });
      manifestNode.href = URL.createObjectURL(blob);
      manifestNode.download = "egret-5.4.1-renderer-reference-manifest.json";
      manifestNode.textContent = "Download fixture manifest JSON";
      statusNode.textContent = manifest.fixtures[0] && manifest.fixtures[0].id === "live-accepted-points"
        ? "Rendered " + manifest.fixtures[0].points.length + " accepted game points through the actual BoardPane and Egret renderers. This is an offline replay; no game input or CHALK was used."
        : "Generated " + manifest.fixtures.length + " fixtures using Egret " +
          manifest.engineVersion + " CanvasRenderer + WebGLRenderer. No live game session, pointer input or CHALK was used.";
    } catch (error) {
      document.body.dataset.referenceStatus = "error";
      statusNode.textContent = "Reference harness error: " + (error && error.stack ? error.stack : String(error));
      statusNode.className = "error";
    }
  }


  const FILL001_SERIES_SOURCE="e04234bc-b9ee-4d06-bd20-f1e13b8423ba";
  const FILL001_SERIES_PATHS={
    "c001-f001":"game-monitor-run-20261113T054218164207Z-8524ea6c.json",
    "c001-f002":"game-monitor-run-20261113T054356143388Z-e854a22e.json",
    "c001-f003":"game-monitor-run-20261113T054750518764Z-4de9069f.json",
    "c002-f001":"game-monitor-run-20261113T055140766170Z-3f06caa0.json",
    "c002-f002":"game-monitor-run-20261113T055532027637Z-641e682c.json",
    "c002-f003":"game-monitor-run-20261113T055652967299Z-66b8a7ae.json"
  };

  function renderFill001SeriesReplay() {
    try {
      const figure=new URLSearchParams(window.location.search).get("figure");
      const name=FILL001_SERIES_PATHS[figure];
      if (!name) throw new Error("FILL001 replay requires a pinned six-series figure ID.");
      const path="../data/results/brush_behavior_tests/game_monitor_bridge/"+
        FILL001_SERIES_SOURCE+"/"+name;
      const req=new XMLHttpRequest();
      req.open("GET",path,false);
      req.send(null);
      if(req.status!==200)throw new Error("FILL001 frozen source HTTP "+req.status);
      const run=JSON.parse(req.responseText);
      const recoverQuota=new URLSearchParams(window.location.search).get("quota")==="verified";
      if (recoverQuota && !["c001-f003","c002-f002"].includes(figure)) {
        throw new Error("FILL001 quota reconstruction restricted to two pinned gap cases.");
      }
      const input=extractFill001SeriesStrokes(run,recoverQuota);
      if(input.sessionId!==FILL001_SERIES_SOURCE)throw new Error("FILL001 session mismatch.");
      const g=run.renderer_geometry_at_start;
      const h=run.renderer_geometry_at_end;
      if(!g || !h || g.engineVersion!=="5.4.1" || g.renderMode!=="webgl" ||
          g.canvasScaleX!==4 || g.canvasScaleY!==4 ||
          !g.boardDetected || !h.boardDetected || g.playerCount!==1 || h.playerCount!==1) {
        throw new Error("FILL001 unsupported source Egret/Stage geometry.");
      }
      const player=g.players?.[0], other=h.players?.[0];
      if (!player || !other) throw new Error("FILL001 missing source player.");
      const corners=player.boardStageCorners;
      const otherCorners=other.boardStageCorners;
      const important=x=>JSON.stringify({
        s:x?.stage, c:{width:x?.canvas?.width,height:x?.canvas?.height},
        corners:x?.boardStageCorners
      });
      if(important(player)!==important(other) ||
          g.canvasScaleX!==h.canvasScaleX || g.canvasScaleY!==h.canvasScaleY) {
        throw new Error("FILL001 Stage backing/BoardPane geometry changed.");
      }
      const profile={
        stageWidth:Number(player.stage?.width),stageHeight:Number(player.stage?.height),
        canvasBackingWidth:Number(player.canvas?.width),
        canvasBackingHeight:Number(player.canvas?.height),
        canvasScaleX:g.canvasScaleX,canvasScaleY:g.canvasScaleY,
        boardWidth:460,boardHeight:240,boardStageCorners:corners
      };
      buildStagePlacement(profile,false);
      const board=makeTemporalBoard(input.strokes,10,"normal",false);
      if(board.accepted!==input.observedCoordinateCount) {
        throw new Error("FILL001 BoardPane accepted coordinate mismatch.");
      }
      const state=initializeWebGL(profile,4);
      const rendered=renderStageWebGL("normal",[],10,profile,false,state,board.shape);
      const manifest={
        schema:"FILL001_SERIES_EGRET_REPLAY_V1",figure,
        source:path,run_id:input.runId,session_id:input.sessionId,
        exact_historical_chalk:input.exactHistoricalChalk,
        observed_coordinate_count:input.observedCoordinateCount,
        missing_coordinate_count:input.missingCoordinateCount,
        pixel_exact_eligible:input.pixelExactEligible,
        recovered_coordinate_count:input.recoveredCoordinateCount,
        recovery_method:recoverQuota?"FIRST_PARTY_QUOTA_VERIFIED":"NONE",
        replay_status:input.replayStatus,stroke_count:input.strokes.length,
        stroke_widths:[...new Set(input.strokes.map(x=>x.width))],
        observed_normal_mode:true,source_stage_profile:profile,
        stage_placement:rendered.placement,stage_output:{
          width:rendered.canvas.width,height:rendered.canvas.height
        },
        renderer:"real Egret 5.4.1 Stage WebGLRenderer",
        exclusions:[
          "Unrecorded ENTER_FRAME redraw callbacks and order",
          recoverQuota?"Quota-based reconstruction is not independent pixel validation":
            "One unknown coordinate per point_delta=2, if present",
          "Not a new live game measurement"
        ]
      };
      const card=document.createElement("section");
      card.className="fixture";
      addDownloadLink(card,rendered.canvas,"fill001-"+figure+"-stage-webgl.png","Native Egret Stage WebGL PNG");
      casesNode.replaceChildren(card);
      document.getElementById("renderer-manifest-json").textContent=JSON.stringify(manifest);
      document.body.dataset.referenceStatus="fill001_series_complete";
      document.body.dataset.seriesStatus="complete";
      statusNode.textContent="FILL001 "+figure+" native Egret replay: "+input.replayStatus;
    }catch(error){
      document.body.dataset.seriesStatus="error";
      document.body.dataset.referenceStatus="error";
      statusNode.className="error";
      statusNode.textContent="FILL001 native series replay error: "+(error?.stack||error);
    }
  }

  // ENGINE-001 two existing repository icons, one composite mask.
  // Accepted synthetic vertices are NOT an exact game CHALK measurement.
  function renderTwoIconMaskProbe(strokes) {
    if (!Array.isArray(strokes) || !strokes.length || strokes.length > 3000) {
      throw new Error("Two-icon fixture requires 1..3000 synthetic strokes.");
    }
    let total=0;
    for (const stroke of strokes) {
      if (!stroke || typeof stroke.strokeId!=="string" ||
          !/^icon-[0-9]+$/.test(stroke.strokeId) ||
          stroke.width!==2 || !Array.isArray(stroke.points) ||
          stroke.points.length<2 || stroke.points.length>128) {
        throw new Error("Invalid two-icon fixed radius2 stroke.");
      }
      for (const p of stroke.points) {
        if (!p || !Number.isFinite(p.x) || !Number.isFinite(p.y) ||
            p.x<0 || p.x>=BOARD_WIDTH || p.y<0 || p.y>=BOARD_HEIGHT) {
          throw new Error("Two-icon geometry leaves 460x240 logical board.");
        }
        total+=1;
      }
    }
    if (total>5900) throw new Error("Two-icon synthetic point quota exceeded.");
    const board=makeTemporalBoard(strokes,2,"normal",false);
    if(board.accepted!==total) throw new Error("Two-icon native BoardPane rejected vertices.");
    const state=initializeWebGL(null,3);
    const blank=document.createElement("canvas");
    blank.width=BOARD_WIDTH*3;blank.height=BOARD_HEIGHT*3;
    const result=renderWebGLProbe("normal",[],2,blank,state,board.shape);
    if(!result.sceneDiagnostics.stageAttached ||
       result.sceneDiagnostics.boardRenderMode!==3 ||
       result.canvas.width!==1380 || result.canvas.height!==720) {
      throw new Error("Two-icon actual Egret WebGL mask failed.");
    }
    return {
      schema:"ENGINE001_TWO_ICON_NATIVE_MASK_V1",
      renderer:"real Egret 5.4.1 BoardPane/WebGLRenderer",
      maskSource:"two pinned repository PNGs; independent Python target mask",
      mode:"normal",brushRadius:2,syntheticAcceptedVerticesNotChalk:total,
      strokeCount:strokes.length,glInfo:result.glInfo,
      webglDrawCalls:result.drawCalls,sceneDiagnostics:result.sceneDiagnostics,
      webglPngDataUrl:result.canvas.toDataURL("image/png")
    };
  }


  // Opt-in V3 only: mixed per-stroke brush size, original fixed-radius probe untouched.
  function renderTwoIconAdaptiveBrushProbe(strokes) {
    if (!Array.isArray(strokes) || !strokes.length || strokes.length > 3000) {
      throw new Error("Two-icon fixture requires 1..3000 synthetic strokes.");
    }
    let total=0;
    for (const stroke of strokes) {
      if (!stroke || typeof stroke.strokeId!=="string" ||
          !/^icon-[0-9]+$/.test(stroke.strokeId) ||
          ![2,4,6,8,10,15,30].includes(stroke.width) || !Array.isArray(stroke.points) ||
          stroke.points.length<2 || stroke.points.length>128) {
        throw new Error("Invalid adaptive two-icon width or stroke.");
      }
      for (const p of stroke.points) {
        if (!p || !Number.isFinite(p.x) || !Number.isFinite(p.y) ||
            p.x<0 || p.x>=BOARD_WIDTH || p.y<0 || p.y>=BOARD_HEIGHT) {
          throw new Error("Two-icon geometry leaves 460x240 logical board.");
        }
        total+=1;
      }
    }
    if (total>5900) throw new Error("Two-icon synthetic point quota exceeded.");
    const board=makeTemporalBoard(strokes,2,"normal",false);
    if(board.accepted!==total) throw new Error("Two-icon native BoardPane rejected vertices.");
    const state=initializeWebGL(null,3);
    const blank=document.createElement("canvas");
    blank.width=BOARD_WIDTH*3;blank.height=BOARD_HEIGHT*3;
    const result=renderWebGLProbe("normal",[],2,blank,state,board.shape);
    if(!result.sceneDiagnostics.stageAttached ||
       result.sceneDiagnostics.boardRenderMode!==3 ||
       result.canvas.width!==1380 || result.canvas.height!==720) {
      throw new Error("Two-icon actual Egret WebGL mask failed.");
    }
    return {
      schema:"ENGINE001_TWO_ICON_ADAPTIVE_BRUSH_V3",
      renderer:"real Egret 5.4.1 BoardPane/WebGLRenderer",
      maskSource:"two pinned repository PNGs; independent Python target mask",
      mode:"normal",brushSizes:[...new Set(strokes.map(s=>s.width))],syntheticAcceptedVerticesNotChalk:total,
      strokeCount:strokes.length,glInfo:result.glInfo,
      webglDrawCalls:result.drawCalls,sceneDiagnostics:result.sceneDiagnostics,
      webglPngDataUrl:result.canvas.toDataURL("image/png")
    };
  }

  api.renderTwoIconMaskProbe = renderTwoIconMaskProbe;
  api.renderTwoIconAdaptiveBrushProbe = renderTwoIconAdaptiveBrushProbe;
  api.renderContourFirstNativeStudy = renderContourFirstNativeStudy;
  api.renderContourTrimNativeStudy = renderContourTrimNativeStudy;
  api.renderFill001ChalkFirstV5Study = renderFill001ChalkFirstV5Study;
  api.renderFill001BottomRepairStudy = renderFill001BottomRepairStudy;
  api.renderFill001FootprintStudy = renderFill001FootprintStudy;
  api.renderAll = renderAll;
  api.renderTemporalStudy = renderTemporalStudy;
  api.renderEndpointStudy = renderEndpointStudy;
  api.renderDuplicateFrameStudy = renderDuplicateFrameStudy;
  const params = new URLSearchParams(window.location.search);
  const startup = params.get("twoicons") === "home-envelope"
    ? () => { document.body.dataset.twoIconStatus="ready"; statusNode.textContent="ENGINE001 two-icon native-mask probe ready."; }
    : params.get("fill001series") === "3e1fd32c4d99" ? renderFill001SeriesReplay
    : params.get("contour") === "fill001v5" ? renderFill001ChalkFirstV5Study
    : params.get("contour") === "fill001v4" ? renderFill001BottomRepairStudy
    : params.get("footprint") === "fill001a" ? renderFill001FootprintStudy
    : params.get("contour") === "fill001v3" ? () => renderContourTrimNativeStudy(true)
    : params.get("contour") === "fill001v2" ? () => renderContourTrimNativeStudy(false)
    : params.get("contour") === "fill001" ? renderContourFirstNativeStudy
    : params.get("frames") === "fill001" ? renderDuplicateFrameStudy
    : params.get("outline") === "fill001" ? () => renderEndpointStudy(true)
    : params.get("endpoint") === "fill001" ? () => renderEndpointStudy(false)
    : params.get("temporal") === "fill001" ? renderTemporalStudy : renderAll;
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startup, { once: true });
  } else {
    startup();
  }
})(typeof window !== "undefined" ? window : globalThis);

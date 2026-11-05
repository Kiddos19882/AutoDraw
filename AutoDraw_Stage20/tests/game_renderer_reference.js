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

  function compileStageShader(gl,type,source) {
    const shader=gl.createShader(type);
    gl.shaderSource(shader,source); gl.compileShader(shader);
    if (!gl.getShaderParameter(shader,gl.COMPILE_STATUS)) {
      const message=gl.getShaderInfoLog(shader)||"unknown shader compile error";
      gl.deleteShader(shader); throw new Error("Stage WebGL shader compile failed: "+message);
    }
    return shader;
  }

  function renderStageWebGL(sourceCanvas,profile,roundOrigin) {
    const p=buildStagePlacement(profile,roundOrigin);
    if (!sourceCanvas || sourceCanvas.width!==p.width || sourceCanvas.height!==p.height) {
      throw new Error("Stage WebGL source dimensions do not match BoardPane backing dimensions.");
    }
    const canvas=document.createElement("canvas");
    canvas.width=p.backingWidth; canvas.height=p.backingHeight;
    const gl=canvas.getContext("webgl",{alpha:true,antialias:true,premultipliedAlpha:true,
      preserveDrawingBuffer:true,depth:false,stencil:false});
    if (!gl) throw new Error("Stage-level WebGL context unavailable.");
    const maxTexture=gl.getParameter(gl.MAX_TEXTURE_SIZE), maxRenderbuffer=gl.getParameter(gl.MAX_RENDERBUFFER_SIZE);
    if (canvas.width>maxTexture || canvas.height>maxTexture ||
        canvas.width>maxRenderbuffer || canvas.height>maxRenderbuffer) {
      throw new Error("Stage backing dimensions exceed WebGL texture/renderbuffer limits.");
    }
    const vs=compileStageShader(gl,gl.VERTEX_SHADER,
      "attribute vec2 a_position; attribute vec2 a_texCoord; varying vec2 v_texCoord; "+
      "void main(){gl_Position=vec4(a_position,0.0,1.0);v_texCoord=a_texCoord;}");
    const fs=compileStageShader(gl,gl.FRAGMENT_SHADER,
      "precision mediump float; varying vec2 v_texCoord; uniform sampler2D u_texture; "+
      "void main(){gl_FragColor=texture2D(u_texture,v_texCoord);}");
    const program=gl.createProgram();
    gl.attachShader(program,vs); gl.attachShader(program,fs); gl.linkProgram(program);
    if (!gl.getProgramParameter(program,gl.LINK_STATUS)) {
      throw new Error("Stage WebGL program link failed: "+(gl.getProgramInfoLog(program)||"unknown error"));
    }
    gl.useProgram(program);
    const cx=x=>x/p.backingWidth*2-1, cy=y=>1-y/p.backingHeight*2;
    const x1=p.x+p.width, y1=p.y+p.height;
    const vertices=new Float32Array([
      cx(p.x),cy(p.y),0,0, cx(p.x),cy(y1),0,1,
      cx(x1),cy(p.y),1,0, cx(x1),cy(y1),1,1
    ]);
    const buffer=gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
    gl.bufferData(gl.ARRAY_BUFFER,vertices,gl.STATIC_DRAW);
    const stride=4*Float32Array.BYTES_PER_ELEMENT;
    const pos=gl.getAttribLocation(program,"a_position"), uv=gl.getAttribLocation(program,"a_texCoord");
    gl.enableVertexAttribArray(pos); gl.vertexAttribPointer(pos,2,gl.FLOAT,false,stride,0);
    gl.enableVertexAttribArray(uv); gl.vertexAttribPointer(uv,2,gl.FLOAT,false,stride,2*Float32Array.BYTES_PER_ELEMENT);
    const texture=gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D,texture);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,true); gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,true);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,sourceCanvas);
    gl.viewport(0,0,canvas.width,canvas.height); gl.clearColor(0,0,0,0); gl.clear(gl.COLOR_BUFFER_BIT);
    gl.enable(gl.BLEND); gl.blendFunc(gl.ONE,gl.ONE_MINUS_SRC_ALPHA); gl.drawArrays(gl.TRIANGLE_STRIP,0,4); gl.finish();
    const error=gl.getError();
    if (error!==gl.NO_ERROR) throw new Error("Stage WebGL compositor returned GL error "+error+".");
    const params={minFilter:gl.getTexParameter(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER),
      magFilter:gl.getTexParameter(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER),
      wrapS:gl.getTexParameter(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S),
      wrapT:gl.getTexParameter(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T),
      unpackPremultiplyAlpha:gl.getParameter(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL),
      unpackFlipY:gl.getParameter(gl.UNPACK_FLIP_Y_WEBGL)};
    const attributes=gl.getContextAttributes();
    gl.deleteTexture(texture); gl.deleteBuffer(buffer); gl.deleteProgram(program); gl.deleteShader(vs); gl.deleteShader(fs);
    return {canvas,placement:p,textureParameters:params,contextAttributes:attributes};
  }

  function renderStageLevelVariants(sourceCanvas,profile) {
    const plan=[
      {id:"A",backend:"WebGL",roundOrigin:false},
      {id:"B",backend:"WebGL",roundOrigin:true},
      {id:"C",backend:"Canvas2D",roundOrigin:false},
      {id:"D",backend:"Canvas2D",roundOrigin:true}
    ];
    const rendered=plan.map(v=>{
      const r=v.backend==="WebGL"
        ?renderStageWebGL(sourceCanvas,profile,v.roundOrigin)
        :renderStageCanvas2D(sourceCanvas,profile,v.roundOrigin);
      return {id:v.id,backend:v.backend,canvas:r.canvas,placement:r.placement,
        textureParameters:r.textureParameters||null,contextAttributes:r.contextAttributes||null};
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
    buildStagePlacement
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

  function initializeWebGL() {
    if (!egret.sys || typeof egret.sys.setRenderMode !== "function") {
      throw new Error("Egret sys.setRenderMode is unavailable.");
    }
    if (egret.Capabilities.renderMode !== "webgl") egret.sys.setRenderMode("webgl");
    if (!egret.sys.systemRenderer || typeof egret.sys.systemRenderer.render !== "function" ||
        !egret.sys.RenderBuffer) {
      throw new Error("Egret did not initialize WebGLRenderer/WebGLRenderBuffer.");
    }
    const displayList = egret.sys.DisplayList;
    displayList.$canvasScaleX = RASTER_SCALE;
    displayList.$canvasScaleY = RASTER_SCALE;
    displayList.$canvasScaleFactor = RUNTIME_CANVAS_SCALE_FACTOR;

    const outputWidth = BOARD_WIDTH * RASTER_SCALE;
    const outputHeight = BOARD_HEIGHT * RASTER_SCALE;
    const buffer = new egret.sys.RenderBuffer(outputWidth, outputHeight);
    const gl = buffer.context && buffer.context.context;
    if (!gl) throw new Error("Egret WebGL context is unavailable.");
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
      outputSize: { width: outputWidth, height: outputHeight }
    };
  }

  function renderWebGLProbe(mode, points, lineWidth, expectedCanvas, state) {
    // Egret 5.4.1 only switches the masked object to the mask render path when
    // mask.$stage is present. Recreate the live display-list relationship:
    // board and mask are siblings under a container attached to a Stage.
    const stage = new egret.Stage();
    const container = new egret.DisplayObjectContainer();
    stage.addChild(container);

    const mask = makeBoardMaskShape();
    container.addChild(mask);
    const board = makeActualBoardPane(mode, points, lineWidth).shape;
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

      const webglState = initializeWebGL();
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
            ? renderStageLevelVariants(webgl.canvas, liveRuntimeProfile)
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
              comparisonToA: variant.comparisonToA
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

  api.renderAll = renderAll;
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", renderAll, { once: true });
  } else {
    renderAll();
  }
})(typeof window !== "undefined" ? window : globalThis);

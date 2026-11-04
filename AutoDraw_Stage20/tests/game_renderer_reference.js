(function (root) {
  "use strict";

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

  const api = {
    buildSmoothPathCommands,
    buildNormalPathCommands,
    terminalPoint,
    shouldWebGLRendererRasterize
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

  function fixtureList() {
    return [
      { id: "smooth-single-point", mode: "smooth", points: [{ x: 40, y: 40 }] },
      { id: "smooth-two-points", mode: "smooth", points: [{ x: 35, y: 65 }, { x: 145, y: 65 }] },
      { id: "smooth-three-points", mode: "smooth", points: [{ x: 35, y: 105 }, { x: 140, y: 125 }, { x: 250, y: 105 }] },
      { id: "smooth-four-point-turn", mode: "smooth", points: [{ x: 35, y: 155 }, { x: 120, y: 155 }, { x: 165, y: 205 }, { x: 270, y: 205 }] },
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
    const leftData = left.getContext("2d").getImageData(0, 0, left.width, left.height).data;
    const rightData = right.getContext("2d").getImageData(0, 0, right.width, right.height).data;
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
    const board = makeActualBoardPane(mode, points, lineWidth).shape;
    const mask = makeBoardMaskShape();
    board.mask = mask;
    const container = new egret.DisplayObjectContainer();
    container.addChild(board);

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
        runtimeProfile: {
          source: "data/runtime/renderer_snapshot_2026-11-04.json",
          canvasScaleFactor: RUNTIME_CANVAS_SCALE_FACTOR,
          canvasScaleX: RASTER_SCALE,
          canvasScaleY: RASTER_SCALE,
          stageWidth: 1672,
          stageHeight: 600,
          canvasBackingWidth: 5016,
          canvasBackingHeight: 1800,
          devicePixelRatio: 1,
          stageFrameRate: 30,
          scaleMode: "fixedHeight",
          boardWidth: BOARD_WIDTH,
          boardHeight: BOARD_HEIGHT,
          note: "Local BoardPane offscreen raster uses canvasScaleX/Y=3; stage/client CSS transform is not applied."
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
        fixtures: []
      };

      const webglState = initializeWebGL();
      manifest.webglProbe.outputSize = webglState.outputSize;
      manifest.webglProbe.glInfo = webglState.glInfo;
      manifest.webglProbe.contextAttributes = webglState.contextAttributes;

      for (const fixture of fixtureList()) {
        for (const lineWidth of LINE_WIDTHS) {
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
            ...webgl.comparison
          });
          const terminal = terminalPoint(fixture.points, fixture.mode === "smooth", false);
          const entry = {
            id: fixture.id,
            mode: fixture.mode,
            lineWidth,
            points: fixture.points,
            commands: actual.commands,
            actualBoardPane: true,
            manualTranscriptionMatch,
            webglPixelComparison: webgl.comparison,
            webglTextureParameters: webgl.textureParameters,
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
          card.appendChild(links);
          casesNode.appendChild(card);
        }
      }

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
      statusNode.textContent =
        "Generated " + manifest.fixtures.length + " fixtures using Egret " +
        manifest.engineVersion + " CanvasRenderer + WebGLRenderer. No live game session, pointer input or CHALK was used.";
    } catch (error) {
      document.body.dataset.referenceStatus = "error";
      statusNode.textContent = "Reference harness error: " + (error && error.stack ? error.stack : String(error));
      statusNode.className = "error";
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", renderAll, { once: true });
  } else {
    renderAll();
  }
})(typeof window !== "undefined" ? window : globalThis);

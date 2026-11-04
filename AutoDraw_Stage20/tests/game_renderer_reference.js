(function (root) {
  "use strict";

  function midpoint(a, b) {
    return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
  }

  // Faithful path-command transcription of Painter.drawSmoothLine from
  // main.min_653f95bc.js. Signature after graphics/points is
  // (drawFirstHalf, unusedOption, drawLast). BoardPane passes (true, false),
  // so drawLast (the fifth formal parameter) is omitted and remains undefined.
  function buildSmoothPathCommands(points, drawFirstHalf, unusedOption, drawLast) {
    if (drawFirstHalf === undefined) drawFirstHalf = true;
    if (drawLast === undefined) drawLast = false;
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

  function makeShape(mode, points, lineWidth, color) {
    const shape = new egret.Shape();
    const graphics = shape.graphics;
    graphics.lineStyle(lineWidth, color === undefined ? 0x000000 : color, 1, false);
    const commands = mode === "smooth"
      ? buildSmoothPathCommands(points, true, false)
      : buildNormalPathCommands(points);
    for (const command of commands) {
      if (command.type === "moveTo") graphics.moveTo(command.x, command.y);
      else if (command.type === "lineTo") graphics.lineTo(command.x, command.y);
      else if (command.type === "curveTo") {
        graphics.curveTo(command.controlX, command.controlY, command.x, command.y);
      }
    }
    return { shape, commands };
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

  function createBoardMask() {
    const mask = new egret.Shape();
    mask.graphics.beginFill(0xffffff, 1);
    mask.graphics.drawRoundRect(0, 0, BOARD_WIDTH, BOARD_HEIGHT, MASK_ELLIPSE_SIZE);
    mask.graphics.endFill();
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

  function renderAll() {
    try {
      if (!window.egret || !egret.Shape || !egret.CanvasRenderer) {
        throw new Error("Egret 5.4.1 bundle did not expose Shape/CanvasRenderer.");
      }
      casesNode.textContent = "";
      const mask = createBoardMask();
      const manifest = {
        schemaVersion: 1,
        referenceType: "Egret CanvasRenderer GraphicsNode source-raster reference",
        engineVersion: egret.Capabilities.engineVersion,
        sourceBundle: "gameEngine/mergeEngine_df2e5bc5.js",
        browser: {
          userAgent: navigator.userAgent || null,
          platform: navigator.platform || null,
          devicePixelRatio: window.devicePixelRatio || 1,
          viewport: { width: window.innerWidth, height: window.innerHeight }
        },
        renderMode: "CanvasRenderer direct invocation; no WebGL context started",
        board: { width: BOARD_WIDTH, height: BOARD_HEIGHT },
        rasterScale: RASTER_SCALE,
        mask: {
          type: "Egret Shape drawRoundRect",
          ellipseWidthArgument: MASK_ELLIPSE_SIZE,
          ellipseHeightArgument: MASK_ELLIPSE_SIZE,
          effectiveCornerRadiusLogicalPx: MASK_ELLIPSE_SIZE / 2,
          clipping: "Canvas2D destination-in composite for comparison; not validated as identical to WebGL mask stencil"
        },
        webglComposite: "not executed; final Canvas2D drawImage composite is explicitly approximate",
        fixtures: []
      };

      for (const fixture of fixtureList()) {
        for (const lineWidth of LINE_WIDTHS) {
          const built = makeShape(fixture.mode, fixture.points, lineWidth);
          const node = built.shape.$renderNode;
          const source = renderGraphicsNode(node, false);
          const board = composeBoard(source, source.nodeBounds, mask);
          const terminal = terminalPoint(fixture.points, fixture.mode === "smooth", false);
          const entry = {
            id: fixture.id,
            mode: fixture.mode,
            lineWidth,
            points: fixture.points,
            commands: built.commands,
            nodeBounds: source.nodeBounds,
            sourceTextureSize: source.skippedByWebGLRenderer
              ? null
              : { width: source.pixelWidth, height: source.pixelHeight },
            sourceScale: { x: source.scaleX, y: source.scaleY },
            rasterDisposition: source.skippedByWebGLRenderer
              ? "skipped-by-WebGLRenderer-empty-graphics-node"
              : "CanvasRenderer-source-raster",
            smoothPathTerminalPoint: terminal,
            lastAcceptedPoint: fixture.points[fixture.points.length - 1],
            note: source.skippedByWebGLRenderer
              ? "Egret WebGLRenderer skips GraphicsNode rasterization when bounds are empty; this path produces no texture and no visible pixels."
              : fixture.mode === "smooth"
                ? "Painter.drawSmoothLine(..., true, false) with its trailing drawLast parameter omitted: final lineTo(lastPoint) is not emitted."
                : "Painter.drawNormalLine: final accepted point is included in the path."
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
            rasterDisposition: entry.rasterDisposition
          }, null, 2);
          card.appendChild(details);

          const links = document.createElement("div");
          links.className = "downloads";
          addDownloadLink(links, source.canvas,
            fixture.id + "-width-" + lineWidth + "-source-reference.png",
            source.skippedByWebGLRenderer ? "Download transparent no-op reference" : "Download source raster reference");
          addDownloadLink(links, board,
            fixture.id + "-width-" + lineWidth + "-masked-board-reference.png", "Download masked-board reference");
          card.appendChild(links);
          casesNode.appendChild(card);
        }
      }

      const json = JSON.stringify(manifest, null, 2);
      document.getElementById("renderer-manifest-json").textContent = json;
      document.body.dataset.referenceStatus = "complete";
      document.body.dataset.fixtureCount = String(manifest.fixtures.length);
      const blob = new Blob([json], { type: "application/json" });
      manifestNode.href = URL.createObjectURL(blob);
      manifestNode.download = "egret-5.4.1-renderer-reference-manifest.json";
      manifestNode.textContent = "Download fixture manifest JSON";
      statusNode.textContent =
        "Generated " + manifest.fixtures.length + " fixtures using Egret " +
        manifest.engineVersion + " CanvasRenderer. No game session, WebGL context, pointer input or CHALK was used.";
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

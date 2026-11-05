(() => {
  "use strict";

  const VERSION = "0.2.3";
  const METHOD_NAMES = ["onDrawStart", "onDrawing", "onDrawingEnd", "setRadius", "updateLess"];
  const MAX_EVENTS = 50000;
  const SCAN_INTERVAL_MS = 500;
  const MAX_SCAN_NODES = 25000;
  const MAX_SCAN_DEPTH = 14;

  const state = {
    active: false,
    board: null,
    boardLabel: null,
    events: [],
    droppedEvents: 0,
    wrappers: [],
    scanTimer: null,
    networkObserver: null,
    strokeSequence: 0,
    activeStrokeId: null,
    lastPointCount: null,
    lastSampleSignature: null,
    lastSamplePointCount: null,
    strokePollTimer: null,
    inputHandlers: null,
    inputTelemetryEnabled: false,
    startedAt: null,
    errors: [],
    eventListeners: new Set()
  };

  function now() {
    return Number(performance.now().toFixed(3));
  }

  function safeUrl(value) {
    try {
      const url = new URL(String(value), location.href);
      for (const key of [...url.searchParams.keys()]) {
        if (/token|auth|session|cookie|secret|key|uid|user/i.test(key)) {
          url.searchParams.set(key, "[REDACTED]");
        }
      }
      return url.origin + url.pathname + (url.search ? url.search : "");
    } catch (_) {
      return String(value).split("?")[0];
    }
  }

  function frameContext() {
    let isTopFrame = false;
    try {
      isTopFrame = window.top === window;
    } catch (_) {}
    let currentFrame = location.origin + location.pathname;
    const frameCandidates = [];
    if (isTopFrame) {
      try {
        for (const frame of document.querySelectorAll("iframe")) {
          let src = frame.getAttribute("src") || "";
          try { src = safeUrl(new URL(src, location.href).href); } catch (_) {}
          frameCandidates.push({
            src,
            title: frame.title || null,
            name: frame.name || null
          });
        }
      } catch (_) {}
    }
    return { isTopFrame, currentFrame, frameCandidates };
  }

  // The game engine stores atom.points as stroke arrays containing
  // egret.Point objects ({ x, y }), not numeric [x, y] tuples.
  function isGamePoint(value) {
    return !!value &&
      typeof value === "object" &&
      !Array.isArray(value) &&
      Number.isFinite(value.x) &&
      Number.isFinite(value.y);
  }

  // Read only the tail of the current stroke. This is O(1) and records the
  // exact last coordinate accepted by BoardPane without scanning atom.points.
  function latestAcceptedPoint(board) {
    const strokes = board && board.atom && board.atom.points;
    if (!Array.isArray(strokes) || strokes.length === 0) return null;
    const lastStroke = strokes[strokes.length - 1];
    if (!Array.isArray(lastStroke) || lastStroke.length === 0) return null;
    const point = lastStroke[lastStroke.length - 1];
    return isGamePoint(point) ? { x: point.x, y: point.y } : null;
  }

  function pointCount(value, depth = 0, seen = new WeakSet()) {
    if (!Array.isArray(value) || depth > 8 || seen.has(value)) return 0;
    seen.add(value);
    let total = 0;
    for (const item of value) {
      if (isGamePoint(item)) total++;
      else if (Array.isArray(item)) total += pointCount(item, depth + 1, seen);
    }
    return total;
  }

  function lastPoint(value, depth = 0, seen = new WeakSet()) {
    if (!Array.isArray(value) || depth > 8 || seen.has(value)) return null;
    seen.add(value);
    for (let i = value.length - 1; i >= 0; i--) {
      const item = value[i];
      if (isGamePoint(item)) return [item.x, item.y];
      if (Array.isArray(item)) {
        const found = lastPoint(item, depth + 1, seen);
        if (found) return found;
      }
    }
    return null;
  }

  function safeValue(value) {
    if (value == null || typeof value === "string" || typeof value === "boolean") return value;
    if (typeof value === "number") return Number.isFinite(value) ? value : String(value);
    if (Array.isArray(value)) return value.slice(0, 32).map(safeValue);
    if (typeof value === "object") {
      const result = {};
      for (const key of ["x", "y", "radius", "width", "height", "scaleX", "scaleY", "length"]) {
        if (key in value && ["string", "number", "boolean"].includes(typeof value[key])) result[key] = safeValue(value[key]);
      }
      return result;
    }
    return String(value);
  }

  // BoardPane.updateLess() writes exact integer fields on the live instance:
  // this.less = this.max - pointCount(atom.points). Reading these fields is O(1).
  // Do not fall back to scanning atom.points in the hot path.
  function resourceSnapshot(board) {
    const atom = board && board.atom;
    const maxPoints = board && board.max;
    const remainingPoints = board && board.less;
    const radii = atom && atom.radius;
    const currentRadius = Array.isArray(radii) && radii.length ? safeValue(radii[radii.length - 1]) : null;
    const isExact = Number.isSafeInteger(maxPoints) &&
      maxPoints > 0 &&
      Number.isSafeInteger(remainingPoints) &&
      remainingPoints >= 0 &&
      remainingPoints <= maxPoints;
    return {
      logicalWidth: safeValue(board && (board.BLACK_BOARD_WIDTH ?? board.width)),
      logicalHeight: safeValue(board && (board.BLACK_BOARD_HEIGHT ?? board.height)),
      scaleX: safeValue(board && board.scaleX),
      scaleY: safeValue(board && board.scaleY),
      maxPoints: isExact ? maxPoints : null,
      remainingPoints: isExact ? remainingPoints : null,
      pointCount: isExact ? maxPoints - remainingPoints : null,
      sourceMethod: "BoardPane.max+BoardPane.less",
      isExact,
      validationStatus: isExact ? "valid" : "unavailable",
      radius: atom ? safeValue(atom.radius) : null,
      currentRadius
    };
  }

  // Explicit diagnostic only. This performs O(N) scans and is never called
  // automatically by emit(), wrappers, status(), polling, or export().
  function diagnosticSnapshot() {
    if (!state.board) return { boardDetected: false, validationStatus: "unavailable" };
    const fast = resourceSnapshot(state.board);
    const points = state.board.atom && state.board.atom.points;
    const diagnosticPointCount = Array.isArray(points) ? pointCount(points) : null;
    return {
      ...fast,
      diagnosticPointCount,
      pointCountMatches: fast.isExact && diagnosticPointCount === fast.pointCount,
      strokeArrayLength: Array.isArray(points) ? points.length : null,
      lastPoint: Array.isArray(points) ? lastPoint(points) : null
    };
  }

  function emit(type, details = {}) {
    if (!state.active) return;
    const event = {
      monitorVersion: VERSION,
      t: now(),
      type,
      strokeId: state.activeStrokeId,
      board: state.board ? resourceSnapshot(state.board) : null,
      ...details
    };
    if (state.events.length < MAX_EVENTS) state.events.push(event);
    else state.droppedEvents++;
    for (const listener of state.eventListeners) {
      try { listener(event); }
      catch (error) { state.errors.push({ t: now(), message: "event_listener: " + String(error) }); }
    }
  }

  function isBoard(candidate) {
    if (!candidate || typeof candidate !== "object") return false;
    const atom = candidate.atom;
    return !!atom &&
      Array.isArray(atom.points) &&
      METHOD_NAMES.slice(0, 3).every(name => typeof candidate[name] === "function");
  }

  function findStage() {
    try {
      const egret = window.egret;
      if (egret && egret.MainContext && egret.MainContext.instance) {
        const stage = egret.MainContext.instance.stage;
        if (stage) return stage;
      }
    } catch (error) {
      state.errors.push({ t: now(), message: "stage_lookup: " + String(error) });
    }
    return null;
  }

  function findBoard(root) {
    if (!root) return null;
    const queue = [{ node: root, depth: 0 }];
    const seen = new WeakSet();
    let visited = 0;
    let queueIndex = 0;
    while (queueIndex < queue.length && visited < MAX_SCAN_NODES) {
      const { node, depth } = queue[queueIndex++];
      if (!node || typeof node !== "object" || seen.has(node)) continue;
      seen.add(node);
      visited++;
      if (isBoard(node)) return node;
      if (depth >= MAX_SCAN_DEPTH) continue;
      let children = null;
      try {
        if (Array.isArray(node.$children)) children = node.$children;
        else if (Array.isArray(node.children)) children = node.children;
        else if (node._children && Array.isArray(node._children)) children = node._children;
      } catch (_) {}
      if (children) {
        for (const child of children) queue.push({ node: child, depth: depth + 1 });
      }
    }
    return null;
  }

  function sampleActiveStroke(source) {
    if (!state.active || !state.board || !state.activeStrokeId) return;
    const snapshot = resourceSnapshot(state.board);
    const signature = JSON.stringify([snapshot.maxPoints, snapshot.remainingPoints, snapshot.pointCount, snapshot.validationStatus]);
    if (signature === state.lastSampleSignature) return;
    const previous = state.lastSampleSignature;
    const previousPointCount = state.lastSamplePointCount;
    const pointDelta = snapshot.isExact && Number.isSafeInteger(previousPointCount)
      ? snapshot.pointCount - previousPointCount
      : null;
    const acceptedPoint = pointDelta > 0 ? latestAcceptedPoint(state.board) : null;
    state.lastSampleSignature = signature;
    state.lastSamplePointCount = snapshot.pointCount;
    emit("DRAW_SAMPLE", {
      source,
      previousSignature: previous,
      after: snapshot,
      pointDelta,
      acceptedPoint
    });
  }

  function startStrokePolling() {
    if (state.strokePollTimer !== null) window.clearInterval(state.strokePollTimer);
    state.lastSampleSignature = null;
    state.lastSamplePointCount = resourceSnapshot(state.board).pointCount;
    sampleActiveStroke("onDrawStart");
    // onDrawing may already have been registered as a bound Egret listener
    // before this snippet wraps the instance method. Poll only during a stroke;
    // the poll reads BoardPane.max/less in O(1), never scans atom.points.
    state.strokePollTimer = window.setInterval(() => sampleActiveStroke("state_poll"), 25);
  }

  function stopStrokePolling() {
    if (state.strokePollTimer !== null) window.clearInterval(state.strokePollTimer);
    state.strokePollTimer = null;
    sampleActiveStroke("stroke_end");
  }

  function isGameCanvasTarget(target) {
    if (!target || typeof target !== "object") return false;
    if (typeof HTMLCanvasElement !== "undefined" && target instanceof HTMLCanvasElement) return true;
    return !!(target.closest && target.closest("canvas"));
  }

  function currentBoardCoordinates(board) {
    const stage = findStage();
    const stageX = stage ? finiteNumber(stage.mouseX) : null;
    const stageY = stage ? finiteNumber(stage.mouseY) : null;
    let boardX = null;
    let boardY = null;
    if (stageX !== null && stageY !== null && board && typeof board.globalToLocal === "function") {
      try {
        const local = board.globalToLocal(stageX, stageY);
        boardX = finiteNumber(local && local.x);
        boardY = finiteNumber(local && local.y);
      } catch (_) {}
    }
    return { stageX, stageY, boardX, boardY };
  }

  function onPointerDown(event) {
    if (!state.active || !state.board || !isGameCanvasTarget(event.target)) return;
    if (!state.activeStrokeId) {
      state.strokeSequence++;
      state.activeStrokeId = "pointer-stroke-" + state.strokeSequence;
      emit("POINTER_DOWN_CANDIDATE", { clientX: event.clientX, clientY: event.clientY, pointerType: event.pointerType || "mouse" });
      startStrokePolling();
    }
  }

  function onPointerUp(event) {
    if (!state.active || !state.activeStrokeId || !isGameCanvasTarget(event.target)) return;
    stopStrokePolling();
    emit("POINTER_UP_CANDIDATE", { clientX: event.clientX, clientY: event.clientY, pointerType: event.pointerType || "mouse" });
    state.activeStrokeId = null;
  }

  function onMouseMove(event) {
    if (!state.active || !state.inputTelemetryEnabled || !state.activeStrokeId || !state.board || !isGameCanvasTarget(event.target)) return;
    // Egret WebTouchHandler attaches mousemove to the canvas. This window
    // bubble listener runs after that target listener, so stage.mouseX/Y
    // reflect the coordinates the game has just received.
    emit("MOUSE_MOVE_SAMPLE", {
      source: "window-bubble-after-egret-canvas",
      domEventTimeStamp: finiteNumber(event.timeStamp),
      clientX: finiteNumber(event.clientX),
      clientY: finiteNumber(event.clientY),
      pageX: finiteNumber(event.pageX),
      pageY: finiteNumber(event.pageY),
      screenX: finiteNumber(event.screenX),
      screenY: finiteNumber(event.screenY),
      movementX: finiteNumber(event.movementX),
      movementY: finiteNumber(event.movementY),
      buttons: finiteNumber(event.buttons),
      ...currentBoardCoordinates(state.board)
    });
  }

  function installInputObservers() {
    if (state.inputHandlers) return;
    state.inputHandlers = { down: onPointerDown, up: onPointerUp, cancel: onPointerUp, move: onMouseMove };
    window.addEventListener("pointerdown", state.inputHandlers.down, true);
    window.addEventListener("pointerup", state.inputHandlers.up, true);
    window.addEventListener("pointercancel", state.inputHandlers.cancel, true);
    // Optional: bubble phase captures after Egret's canvas mousemove handler.
    if (state.inputTelemetryEnabled) {
      window.addEventListener("mousemove", state.inputHandlers.move, false);
    }
  }

  function removeInputObservers() {
    if (!state.inputHandlers) return;
    window.removeEventListener("pointerdown", state.inputHandlers.down, true);
    window.removeEventListener("pointerup", state.inputHandlers.up, true);
    window.removeEventListener("pointercancel", state.inputHandlers.cancel, true);
    window.removeEventListener("mousemove", state.inputHandlers.move, false);
    state.inputHandlers = null;
  }

  function wrapMethod(board, name) {
    const original = board[name];
    if (typeof original !== "function") return;
    if (original.__autoDrawMonitorWrapped) return;
    const ownDescriptor = Object.getOwnPropertyDescriptor(board, name);
    const wrapped = function (...args) {
      const before = resourceSnapshot(board);
      const previousStroke = state.activeStrokeId;
      if (name === "onDrawStart") {
        if (!state.activeStrokeId) {
          state.strokeSequence++;
          state.activeStrokeId = "stroke-" + state.strokeSequence;
        }
        emit("DRAW_START", { source: "BoardPane.onDrawStart", args: args.slice(0, 4).map(safeValue), before });
      } else if (name === "setRadius") {
        emit("BRUSH_CHANGE", { args: args.slice(0, 4).map(safeValue), before });
      }

      let result;
      try {
        result = original.apply(this, args);
      } catch (error) {
        emit("GAME_METHOD_ERROR", { method: name, message: String(error), before });
        throw error;
      }

      const after = resourceSnapshot(board);
      const resourceChanged = before.maxPoints !== after.maxPoints ||
        before.remainingPoints !== after.remainingPoints ||
        before.validationStatus !== after.validationStatus;
      if (name === "onDrawing") {
        sampleActiveStroke("onDrawing_wrapper");
      } else if (name === "onDrawStart") {
        emit("DRAW_START_APPLIED", { before, after });
        startStrokePolling();
      } else if (name === "onDrawingEnd") {
        stopStrokePolling();
        emit("DRAW_END", { before, after });
        state.activeStrokeId = null;
      } else if (name === "setRadius") {
        emit("BRUSH_CHANGE_APPLIED", { before, after });
      } else if (name === "updateLess" && resourceChanged) {
        // updateLess() can run on every ENTER_FRAME even when pushPoint()
        // rejects a duplicate coordinate. Do not log a quota event if max/less
        // did not change.
        const pointDelta = before.isExact && after.isExact
          ? after.pointCount - before.pointCount
          : null;
        emit("POINT_QUOTA_UPDATE", {
          before,
          after,
          args: args.slice(0, 3).map(safeValue),
          pointDelta,
          acceptedPoint: pointDelta > 0 ? latestAcceptedPoint(board) : null,
          ...(pointDelta > 0 && state.inputTelemetryEnabled ? currentBoardCoordinates(board) : {})
        });
      }
      if (previousStroke && !state.activeStrokeId && name !== "onDrawingEnd") state.activeStrokeId = previousStroke;
      return result;
    };
    Object.defineProperty(wrapped, "__autoDrawMonitorWrapped", { value: true });
    try {
      Object.defineProperty(board, name, { configurable: true, writable: true, enumerable: ownDescriptor?.enumerable ?? false, value: wrapped });
      state.wrappers.push({ board, name, original, ownDescriptor });
    } catch (error) {
      state.errors.push({ t: now(), message: "wrap_" + name + ": " + String(error) });
    }
  }

  function attach(board) {
    if (!isBoard(board)) throw new Error("Объект не похож на BoardPane: отсутствуют методы или atom.points.");
    if (state.board === board) return;
    if (state.board) detach();
    state.board = board;
    state.boardLabel = board.constructor && board.constructor.name ? board.constructor.name : "BoardPane";
    for (const name of METHOD_NAMES) wrapMethod(board, name);
    state.lastPointCount = resourceSnapshot(board).pointCount;
    emit("BOARD_ATTACHED", { label: state.boardLabel, snapshot: resourceSnapshot(board) });
  }

  function detach() {
    for (const item of state.wrappers.splice(0).reverse()) {
      try {
        if (item.ownDescriptor) Object.defineProperty(item.board, item.name, item.ownDescriptor);
        else delete item.board[item.name];
      } catch (error) {
        state.errors.push({ t: now(), message: "restore_" + item.name + ": " + String(error) });
      }
    }
    if (state.board) emit("BOARD_DETACHED");
    state.board = null;
    state.boardLabel = null;
    state.activeStrokeId = null;
  }

  function scan() {
    if (!state.active || state.board) return;
    const stage = findStage();
    const board = findBoard(stage);
    if (board) attach(board);
  }

  function observeNetwork() {
    if (!("PerformanceObserver" in window)) return;
    try {
      state.networkObserver = new PerformanceObserver(list => {
        for (const entry of list.getEntries()) {
          const name = String(entry.name || "");
          emit("NETWORK_RESOURCE", {
            initiatorType: entry.initiatorType || null,
            durationMs: Number(entry.duration.toFixed(3)),
            transferSize: Number.isFinite(entry.transferSize) ? entry.transferSize : null,
            url: safeUrl(name)
          });
        }
      });
      state.networkObserver.observe({ type: "resource", buffered: true });
    } catch (error) {
      state.errors.push({ t: now(), message: "network_observer: " + String(error) });
    }
  }

  function start() {
    if (state.active) return status();
    state.active = true;
    state.startedAt = now();
    emit("MONITOR_STARTED", { pageUrl: location.origin + location.pathname });
    observeNetwork();
    installInputObservers();
    scan();
    state.scanTimer = window.setInterval(scan, SCAN_INTERVAL_MS);
    return status();
  }

  function stop() {
    if (state.scanTimer !== null) window.clearInterval(state.scanTimer);
    state.scanTimer = null;
    stopStrokePolling();
    if (state.networkObserver) state.networkObserver.disconnect();
    state.networkObserver = null;
    removeInputObservers();
    detach();
    emit("MONITOR_STOPPED");
    state.active = false;
    return status();
  }

  function exportData() {
    return {
      schemaVersion: 1,
      monitorVersion: VERSION,
      startedAtPerformanceMs: state.startedAt,
      exportedAtPerformanceMs: now(),
      page: { origin: location.origin, pathname: location.pathname },
      frameContext: frameContext(),
      boardDetected: !!state.board,
      boardLabel: state.boardLabel,
      resourceSnapshot: state.board ? resourceSnapshot(state.board) : null,
      eventCount: state.events.length,
      droppedEvents: state.droppedEvents,
      errors: state.errors.slice(),
      inputTelemetryEnabled: state.inputTelemetryEnabled,
      events: state.events.slice()
    };
  }

  function download() {
    const blob = new Blob([JSON.stringify(exportData(), null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "autodraw-game-monitor-" + new Date().toISOString().replace(/[:.]/g, "-") + ".json";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function finiteNumber(value) {
    return typeof value === "number" && Number.isFinite(value) ? value : null;
  }

  function rectangleSnapshot(element) {
    if (!element || typeof element.getBoundingClientRect !== "function") return null;
    try {
      const rect = element.getBoundingClientRect();
      return {
        left: finiteNumber(rect.left), top: finiteNumber(rect.top),
        right: finiteNumber(rect.right), bottom: finiteNumber(rect.bottom),
        width: finiteNumber(rect.width), height: finiteNumber(rect.height)
      };
    } catch (_) { return null; }
  }

  function matrixSnapshot(displayObject) {
    if (!displayObject || typeof displayObject.$getConcatenatedMatrix !== "function") return null;
    try {
      const m = displayObject.$getConcatenatedMatrix();
      if (!m) return null;
      return { a: finiteNumber(m.a), b: finiteNumber(m.b), c: finiteNumber(m.c),
        d: finiteNumber(m.d), tx: finiteNumber(m.tx), ty: finiteNumber(m.ty) };
    } catch (_) { return null; }
  }

  function displayObjectChainSnapshot(board, stage) {
    const chain = [], seen = new WeakSet();
    let current = board;
    while (current && typeof current === "object" && chain.length < 16 && !seen.has(current)) {
      seen.add(current);
      const r = current.scrollRect || current.$scrollRect || null;
      chain.push({
        className: current.constructor && current.constructor.name || null,
        x: finiteNumber(current.x), y: finiteNumber(current.y),
        width: finiteNumber(current.width), height: finiteNumber(current.height),
        scaleX: finiteNumber(current.scaleX), scaleY: finiteNumber(current.scaleY),
        rotation: finiteNumber(current.rotation),
        scrollRect: r ? { x: finiteNumber(r.x), y: finiteNumber(r.y),
          width: finiteNumber(r.width), height: finiteNumber(r.height) } : null,
        concatenatedMatrix: matrixSnapshot(current)
      });
      if (current === stage) break;
      current = current.$parent || null;
    }
    return chain;
  }

  function displayObjectCorners(board) {
    if (!board || typeof board.localToGlobal !== "function") return null;
    const width = finiteNumber(board.width), height = finiteNumber(board.height);
    if (width === null || height === null || width <= 0 || height <= 0) return null;
    const input = { topLeft: [0, 0], topRight: [width, 0],
      bottomRight: [width, height], bottomLeft: [0, height] };
    const output = {};
    try {
      for (const [name, xy] of Object.entries(input)) {
        const point = board.localToGlobal(xy[0], xy[1]);
        if (!point || !Number.isFinite(point.x) || !Number.isFinite(point.y)) return null;
        output[name] = { x: point.x, y: point.y };
      }
      return output;
    } catch (_) { return null; }
  }

  function canvasQuadSnapshot(canvas) {
    if (!canvas || typeof canvas.getBoxQuads !== "function") return null;
    try {
      const quads = canvas.getBoxQuads({ box: "content" }), q = quads && quads[0];
      if (!q) return null;
      const output = {};
      for (const name of ["p1", "p2", "p3", "p4"]) {
        const point = q[name];
        if (!point || !Number.isFinite(point.x) || !Number.isFinite(point.y)) return null;
        output[name] = { x: point.x, y: point.y };
      }
      return output;
    } catch (_) { return null; }
  }

  function mapStagePointToClient(point, quad, stageWidth, stageHeight) {
    if (!point || !quad || !(stageWidth > 0) || !(stageHeight > 0)) return null;
    const u = point.x / stageWidth, v = point.y / stageHeight;
    return {
      x: quad.p1.x + u * (quad.p2.x - quad.p1.x) + v * (quad.p4.x - quad.p1.x),
      y: quad.p1.y + u * (quad.p2.y - quad.p1.y) + v * (quad.p4.y - quad.p1.y)
    };
  }

  function parseCssMatrix(value) {
    if (!value || value === "none") return { a: 1, b: 0, c: 0, d: 1 };
    const match = /^matrix\\(([^)]+)\\)$/.exec(String(value).trim());
    if (!match) return null;
    const values = match[1].split(",").map(item => Number(item.trim()));
    if (values.length !== 6 || values.some(item => !Number.isFinite(item))) return null;
    return { a: values[0], b: values[1], c: values[2], d: values[3] };
  }

  function mapStagePointToClientRect(point, rect, stageWidth, stageHeight) {
    if (!point || !rect || !(stageWidth > 0) || !(stageHeight > 0)) return null;
    return {
      x: rect.left + (point.x / stageWidth) * rect.width,
      y: rect.top + (point.y / stageHeight) * rect.height
    };
  }


  // Read-only runtime evidence. Screen-space corners are derived only when the
  // browser exposes the canvas content quad; a bounding rectangle alone is not
  // treated as an exact affine transform (notably when the canvas is rotated).
  function rendererSnapshot(board = null) {
    const egret = window.egret || null;
    const stage = findStage();
    const activeBoard = board || (stage ? findBoard(stage) : null);
    const capabilities = egret && egret.Capabilities || {};
    const sys = egret && egret.sys || {};
    const displayList = sys.DisplayList || {};
    const players = typeof document.querySelectorAll === "function"
      ? Array.from(document.querySelectorAll(".egret-player") || []) : [];

    const playerSnapshots = players.map(element => {
      let webPlayer = null, canvas = null, computed = null;
      try {
        webPlayer = element && element["egret-player"] || null;
        canvas = webPlayer && webPlayer.canvas ||
          (element && typeof element.querySelector === "function" ? element.querySelector("canvas") : null);
        computed = canvas && typeof window.getComputedStyle === "function"
          ? window.getComputedStyle(canvas) : null;
      } catch (_) {}
      const style = canvas && canvas.style || {};
      const playerStage = webPlayer && webPlayer.stage || stage;
      const options = webPlayer && webPlayer.playerOption || {};
      const stageWidth = finiteNumber(playerStage && (playerStage.stageWidth ?? playerStage.$stageWidth));
      const stageHeight = finiteNumber(playerStage && (playerStage.stageHeight ?? playerStage.$stageHeight));
      const quad = canvasQuadSnapshot(canvas);
      const canvasRect = rectangleSnapshot(canvas);
      const stageCorners = activeBoard ? displayObjectCorners(activeBoard) : null;
      const cssMatrix = parseCssMatrix(computed && computed.transform);
      const canvasScaleX = finiteNumber(displayList.$canvasScaleX);
      const canvasScaleY = finiteNumber(displayList.$canvasScaleY);
      const axisAlignedFallback = !quad && !!(stageCorners && canvasRect && cssMatrix
        && stageWidth > 0 && stageHeight > 0
        && Math.abs(cssMatrix.b) < 1e-9 && Math.abs(cssMatrix.c) < 1e-9
        && cssMatrix.a > 0 && cssMatrix.d > 0
        && Math.abs(canvasRect.width - stageWidth * canvasScaleX * cssMatrix.a) <= 1
        && Math.abs(canvasRect.height - stageHeight * canvasScaleY * cssMatrix.d) <= 1);
      const clientCorners = stageCorners && stageWidth > 0 && stageHeight > 0
        ? (quad
          ? Object.fromEntries(Object.entries(stageCorners).map(([name, point]) =>
              [name, mapStagePointToClient(point, quad, stageWidth, stageHeight)]))
          : axisAlignedFallback
            ? Object.fromEntries(Object.entries(stageCorners).map(([name, point]) =>
                [name, mapStagePointToClientRect(point, canvasRect, stageWidth, stageHeight)]))
            : null)
        : null;
      const clientMappingMethod = quad ? "getBoxQuads_content"
        : axisAlignedFallback ? "validated_axis_aligned_rect" : "unavailable";
      const mask = activeBoard && (activeBoard.mask || activeBoard.$mask);
      return {
        playerFound: !!webPlayer,
        playerMatchesStage: !!(webPlayer && webPlayer.stage && webPlayer.stage === stage),
        containerRect: rectangleSnapshot(webPlayer && webPlayer.container || element),
        playerOptions: {
          scaleMode: safeValue(options.scaleMode) ?? null, frameRate: finiteNumber(options.frameRate),
          contentWidth: finiteNumber(options.contentWidth), contentHeight: finiteNumber(options.contentHeight),
          renderModeOption: safeValue(options.renderMode) ?? null
        },
        stage: playerStage ? {
          width: stageWidth, height: stageHeight, frameRate: finiteNumber(playerStage.frameRate),
          scaleMode: safeValue(playerStage.$scaleMode) ?? null, orientation: safeValue(playerStage.$orientation) ?? null
        } : null,
        canvas: canvas ? {
          width: finiteNumber(canvas.width), height: finiteNumber(canvas.height),
          clientWidth: finiteNumber(canvas.clientWidth), clientHeight: finiteNumber(canvas.clientHeight),
          offsetLeft: finiteNumber(canvas.offsetLeft), offsetTop: finiteNumber(canvas.offsetTop),
          rect: canvasRect, screenQuad: quad,
          style: {
            left: safeValue(style.left) ?? null, top: safeValue(style.top) ?? null,
            width: safeValue(style.width) ?? null, height: safeValue(style.height) ?? null,
            transform: safeValue(style.transform) ?? null, transformOrigin: safeValue(style.transformOrigin) ?? null,
            computedTransform: safeValue(computed && computed.transform) ?? null,
            computedTransformOrigin: safeValue(computed && computed.transformOrigin) ?? null
          }
        } : null,
        boardStageCorners: stageCorners,
        boardClientCorners: clientCorners,
        boardClientMappingMethod: clientMappingMethod,
        boardDisplayChain: activeBoard ? displayObjectChainSnapshot(activeBoard, playerStage) : null,
        boardMask: mask ? {
          className: mask.constructor && mask.constructor.name || null,
          x: finiteNumber(mask.x), y: finiteNumber(mask.y),
          width: finiteNumber(mask.width), height: finiteNumber(mask.height),
          concatenatedMatrix: matrixSnapshot(mask)
        } : null
      };
    });

    const viewport = window.visualViewport || null;
    const renderer = sys.systemRenderer || null, canvasRenderer = sys.canvasRenderer || null;
    return {
      inspectionMode: "read_only",
      engineVersion: safeValue(capabilities.engineVersion) ?? null,
      renderMode: safeValue(capabilities.renderMode) ?? null,
      runtimeType: safeValue(capabilities.runtimeType) ?? null,
      systemRenderer: renderer && renderer.constructor && renderer.constructor.name || null,
      canvasRenderer: canvasRenderer && canvasRenderer.constructor && canvasRenderer.constructor.name || null,
      windowGeometry: {
        screenX: finiteNumber(window.screenX), screenY: finiteNumber(window.screenY),
        outerWidth: finiteNumber(window.outerWidth), outerHeight: finiteNumber(window.outerHeight),
        innerWidth: finiteNumber(window.innerWidth), innerHeight: finiteNumber(window.innerHeight),
        screenWidth: finiteNumber(window.screen && window.screen.width),
        screenHeight: finiteNumber(window.screen && window.screen.height),
        availableScreenWidth: finiteNumber(window.screen && window.screen.availWidth),
        availableScreenHeight: finiteNumber(window.screen && window.screen.availHeight)
      },
      canvasScaleFactor: finiteNumber(displayList.$canvasScaleFactor),
      canvasScaleX: finiteNumber(displayList.$canvasScaleX),
      canvasScaleY: finiteNumber(displayList.$canvasScaleY),
      devicePixelRatio: finiteNumber(window.devicePixelRatio),
      visualViewportScale: finiteNumber(viewport && viewport.scale),
      playerCount: playerSnapshots.length,
      players: playerSnapshots,
      boardDetected: !!activeBoard,
      boardLabel: activeBoard && activeBoard.constructor && activeBoard.constructor.name || null,
      boardLogicalSize: activeBoard ? {
        width: finiteNumber(activeBoard.width), height: finiteNumber(activeBoard.height)
      } : null,
      boardDisplayChain: activeBoard ? displayObjectChainSnapshot(activeBoard, stage) : null
    };
  }

  // Read-only checkpoint inspection. No wrappers, timers, renderer changes or game commands.
  function inspect() {
    const board = state.board || findBoard(findStage());
    return {
      inspectionMode: "read_only",
      boardDetected: !!board,
      boardLabel: board && board.constructor && board.constructor.name ? board.constructor.name : null,
      snapshot: board ? resourceSnapshot(board) : null,
      renderer: rendererSnapshot(board)
    };
  }

  function status() {
    return {
      version: VERSION,
      active: state.active,
      boardDetected: !!state.board,
      boardLabel: state.boardLabel,
      snapshot: state.board ? resourceSnapshot(state.board) : null,
      eventCount: state.events.length,
      droppedEvents: state.droppedEvents,
      errors: state.errors.length,
      inputTelemetryEnabled: state.inputTelemetryEnabled
    };
  }

  function subscribe(listener) {
    if (typeof listener !== "function") throw new TypeError("listener must be a function");
    state.eventListeners.add(listener);
    return () => state.eventListeners.delete(listener);
  }

  function setInputTelemetryEnabled(enabled) {
    const next = enabled === true;
    if (state.inputTelemetryEnabled === next) return status();
    state.inputTelemetryEnabled = next;
    if (state.active && state.inputHandlers) {
      if (next) window.addEventListener("mousemove", state.inputHandlers.move, false);
      else window.removeEventListener("mousemove", state.inputHandlers.move, false);
    }
    return status();
  }

  const api = {
    start,
    subscribe,
    setInputTelemetryEnabled,
    stop,
    status,
    export: exportData,
    download,
    clear() { state.events.length = 0; state.droppedEvents = 0; state.errors.length = 0; },
    attach,
    diagnosticSnapshot,
    rendererSnapshot,
    inspect
  };
  Object.defineProperty(window, "AutoDrawGameMonitor", { configurable: true, value: api });
  return start();
})();

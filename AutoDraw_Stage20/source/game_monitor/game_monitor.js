(() => {
  "use strict";

  const VERSION = "0.2.0";
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
    strokePollTimer: null,
    inputHandlers: null,
    startedAt: null,
    errors: []
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
      radius: atom ? safeValue(atom.radius) : null
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
    state.lastSampleSignature = signature;
    emit("DRAW_SAMPLE", { source, previousSignature: previous, after: snapshot });
  }

  function startStrokePolling() {
    if (state.strokePollTimer !== null) window.clearInterval(state.strokePollTimer);
    state.lastSampleSignature = null;
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

  function installInputObservers() {
    if (state.inputHandlers) return;
    state.inputHandlers = { down: onPointerDown, up: onPointerUp, cancel: onPointerUp };
    window.addEventListener("pointerdown", state.inputHandlers.down, true);
    window.addEventListener("pointerup", state.inputHandlers.up, true);
    window.addEventListener("pointercancel", state.inputHandlers.cancel, true);
  }

  function removeInputObservers() {
    if (!state.inputHandlers) return;
    window.removeEventListener("pointerdown", state.inputHandlers.down, true);
    window.removeEventListener("pointerup", state.inputHandlers.up, true);
    window.removeEventListener("pointercancel", state.inputHandlers.cancel, true);
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
        emit("POINT_QUOTA_UPDATE", { before, after, args: args.slice(0, 3).map(safeValue) });
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

  // Read-only checkpoint inspection. When the monitor is stopped this locates
  // BoardPane on demand, reads max/less, and does not attach wrappers or timers.
  function inspect() {
    const board = state.board || findBoard(findStage());
    return {
      inspectionMode: "read_only",
      boardDetected: !!board,
      boardLabel: board && board.constructor && board.constructor.name ? board.constructor.name : null,
      snapshot: board ? resourceSnapshot(board) : null
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
      errors: state.errors.length
    };
  }

  const api = {
    start,
    stop,
    status,
    export: exportData,
    download,
    clear() { state.events.length = 0; state.droppedEvents = 0; state.errors.length = 0; },
    attach,
    diagnosticSnapshot,
    inspect
  };
  Object.defineProperty(window, "AutoDrawGameMonitor", { configurable: true, value: api });
  return start();
})();

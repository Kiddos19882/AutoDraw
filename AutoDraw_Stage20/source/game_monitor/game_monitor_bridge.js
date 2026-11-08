(() => {
  "use strict";
  const TOKEN = "__AUTODRAW_BRIDGE_TOKEN__";
  const ENDPOINT = "ws://127.0.0.1:8765";
  const INPUT_TELEMETRY_ENABLED = "__AUTODRAW_INPUT_TELEMETRY_ENABLED__" === "true";
  const ALLOWED_EVENTS = new Set([
    "BOARD_ATTACHED", "BOARD_DETACHED", "DRAW_START", "DRAW_START_APPLIED",
    "DRAW_SAMPLE", "DRAW_END", "BRUSH_CHANGE", "BRUSH_CHANGE_APPLIED",
    "POINT_QUOTA_UPDATE", "GAME_METHOD_ERROR", "POINTER_DOWN_CANDIDATE",
    "POINTER_UP_CANDIDATE", "MOUSE_MOVE_SAMPLE", "ENGINE_FRAME_SAMPLE"
  ]);
  const monitor = window.AutoDrawGameMonitor;
  if (!monitor || typeof monitor.subscribe !== "function" || typeof monitor.status !== "function") {
    throw new Error("Game Monitor with subscribe() is required. Load game_monitor.js first in the game iframe.");
  }
  if (window.AutoDrawGameMonitorBridge && window.AutoDrawGameMonitorBridge.connected) {
    throw new Error("AutoDraw Game Monitor Bridge is already connected.");
  }

  const sessionId = crypto.randomUUID();
  let sequence = 0;
  let geometryUpdateTimer = null;
  let lastRendererGeometryFingerprint = null;
  let geometryListenersInstalled = false;
  let geometryHandlers = null;

  const readRendererGeometry = () => {
    if (typeof monitor.inspect !== "function") return null;
    try {
      const inspection = monitor.inspect();
      return inspection && inspection.renderer && typeof inspection.renderer === "object"
        ? inspection.renderer : null;
    } catch (_) {
      return null;
    }
  };

  const publishRendererGeometry = reason => {
    const geometry = readRendererGeometry();
    if (!geometry) return;
    const fingerprint = JSON.stringify(geometry);
    if (fingerprint === lastRendererGeometryFingerprint) return;
    lastRendererGeometryFingerprint = fingerprint;
    send("renderer_geometry", { rendererGeometry: geometry, reason });
  };

  const scheduleRendererGeometryRefresh = reason => {
    if (!connected || geometryUpdateTimer !== null) return;
    geometryUpdateTimer = setTimeout(() => {
      geometryUpdateTimer = null;
      publishRendererGeometry(reason);
    }, 120);
  };

  const installGeometryListeners = () => {
    if (geometryListenersInstalled) return;
    geometryListenersInstalled = true;
    geometryHandlers = {
      resize: () => scheduleRendererGeometryRefresh("window_resize"),
      scroll: () => scheduleRendererGeometryRefresh("window_scroll"),
      orientation: () => scheduleRendererGeometryRefresh("orientation_change"),
      fullscreen: () => scheduleRendererGeometryRefresh("fullscreen_change"),
      viewportResize: () => scheduleRendererGeometryRefresh("visual_viewport_resize"),
      viewportScroll: () => scheduleRendererGeometryRefresh("visual_viewport_scroll")
    };
    window.addEventListener("resize", geometryHandlers.resize, true);
    window.addEventListener("scroll", geometryHandlers.scroll, true);
    window.addEventListener("orientationchange", geometryHandlers.orientation, true);
    document.addEventListener("fullscreenchange", geometryHandlers.fullscreen, true);
    if (window.visualViewport && typeof window.visualViewport.addEventListener === "function") {
      window.visualViewport.addEventListener("resize", geometryHandlers.viewportResize);
      window.visualViewport.addEventListener("scroll", geometryHandlers.viewportScroll);
    }
  };

  const removeGeometryListeners = () => {
    if (!geometryListenersInstalled || !geometryHandlers) return;
    window.removeEventListener("resize", geometryHandlers.resize, true);
    window.removeEventListener("scroll", geometryHandlers.scroll, true);
    window.removeEventListener("orientationchange", geometryHandlers.orientation, true);
    document.removeEventListener("fullscreenchange", geometryHandlers.fullscreen, true);
    if (window.visualViewport && typeof window.visualViewport.removeEventListener === "function") {
      window.visualViewport.removeEventListener("resize", geometryHandlers.viewportResize);
      window.visualViewport.removeEventListener("scroll", geometryHandlers.viewportScroll);
    }
    geometryHandlers = null;
    geometryListenersInstalled = false;
  };
  let connected = false;
  let unsubscribe = null;
  let heartbeatTimer = null;
  let rafHandle = null;
  let fpsActive = false;
  let fpsStartedAt = null;
  let frameTimes = [];
  let fpsStrokeId = null;
  let sentEventCount = 0;
  let lastEventType = null;
  let lastEventAtPerformanceMs = null;
  let sendFailureCount = 0;
  let previousInputTelemetryEnabled = null;
  let inputTelemetryChangedByBridge = false;
  const inputTelemetryConfiguration = {
    requested: INPUT_TELEMETRY_ENABLED,
    enabled: null,
    previous: null,
    changedByBridge: false,
    restoreStatus: "not_required"
  };

  const configureInputTelemetry = () => {
    const before = monitor.status();
    const previous = before && before.inputTelemetryEnabled;
    inputTelemetryConfiguration.previous = typeof previous === "boolean" ? previous : null;
    if (!INPUT_TELEMETRY_ENABLED) {
      inputTelemetryConfiguration.enabled = typeof previous === "boolean" ? previous : null;
      return { ...inputTelemetryConfiguration };
    }
    if (typeof previous !== "boolean") {
      inputTelemetryConfiguration.restoreStatus = "api_unavailable";
      return { ...inputTelemetryConfiguration };
    }
    previousInputTelemetryEnabled = previous;
    if (previous === true) {
      inputTelemetryConfiguration.enabled = true;
      return { ...inputTelemetryConfiguration };
    }
    if (typeof monitor.setInputTelemetryEnabled !== "function") {
      inputTelemetryConfiguration.restoreStatus = "api_unavailable";
      return { ...inputTelemetryConfiguration };
    }
    if (!previous) {
      inputTelemetryChangedByBridge = true;
      inputTelemetryConfiguration.changedByBridge = true;
      try {
        monitor.setInputTelemetryEnabled(true);
      } catch (error) {
        inputTelemetryConfiguration.restoreStatus = "enable_failed";
        console.error("AutoDraw Game Monitor input telemetry could not be enabled:", error);
      }
    }
    const after = monitor.status();
    inputTelemetryConfiguration.enabled = !!after && after.inputTelemetryEnabled === true;
    if (!inputTelemetryConfiguration.enabled) {
      inputTelemetryConfiguration.restoreStatus = "enable_unconfirmed";
    }
    return { ...inputTelemetryConfiguration };
  };

  const restoreInputTelemetry = () => {
    if (!inputTelemetryChangedByBridge) return;
    try {
      monitor.setInputTelemetryEnabled(previousInputTelemetryEnabled === true);
      const restored = monitor.status();
      inputTelemetryConfiguration.restoreStatus =
        restored && restored.inputTelemetryEnabled === previousInputTelemetryEnabled
          ? "restored" : "restore_unconfirmed";
    } catch (error) {
      inputTelemetryConfiguration.restoreStatus = "restore_failed";
      console.error("AutoDraw Game Monitor input telemetry could not be restored:", error);
    }
    inputTelemetryChangedByBridge = false;
    inputTelemetryConfiguration.changedByBridge = false;
  };

  const send = (type, payload = {}) => {
    if (!connected || socket.readyState !== WebSocket.OPEN) {
      sendFailureCount++;
      return false;
    }
    try {
      socket.send(JSON.stringify({ type, sessionId, sequence: ++sequence, sentAtUtc: new Date().toISOString(), ...payload }));
      return true;
    } catch (error) {
      sendFailureCount++;
      console.error("AutoDraw Game Monitor Bridge send failed:", error);
      return false;
    }
  };

  // Read-only, opt-in pre-draw desktop mapping witness. This never sends input
  // to the game. Only genuine mouse moves with NO buttons over BoardPane are
  // accepted; the server binds these samples to this authenticated session.
  let passivePreflightHandler = null;
  let lastPassivePreflightAt = -Infinity;
  const installPassivePreflight = () => {
    if (!INPUT_TELEMETRY_ENABLED || passivePreflightHandler) return;
    passivePreflightHandler = event => {
      if (!connected || !event.isTrusted || event.buttons !== 0
          || document.visibilityState !== "visible"
          || !(event.target instanceof HTMLCanvasElement)
          || performance.now() - lastPassivePreflightAt < 250) return;
      const current = monitor.status();
      if (!current.active || !current.boardDetected) return;
      // Geometry is refreshed and published BEFORE each sample if the page
      // moved; the collector always fingerprints its current renderer state.
      const geo = readRendererGeometry();
      const players = geo && geo.players;
      const rect = Array.isArray(players) && players.length === 1
        ? players[0].boardClientCorners : null;
      const tl = rect && rect.topLeft;
      const br = rect && rect.bottomRight;
      if (!tl || !br || !Number.isFinite(event.clientX) || !Number.isFinite(event.clientY)
          || event.clientX < tl.x || event.clientX > br.x
          || event.clientY < tl.y || event.clientY > br.y) return;
      publishRendererGeometry("passive_input_preflight");
      lastPassivePreflightAt = performance.now();
      send("preflight_sample", { sample: {
        source: "window-bubble-after-egret-canvas",
        isTrusted: true,
        buttons: 0,
        clientX: event.clientX, clientY: event.clientY,
        screenX: event.screenX, screenY: event.screenY
      }});
    };
    window.addEventListener("mousemove", passivePreflightHandler, false);
  };
  const removePassivePreflight = () => {
    if (!passivePreflightHandler) return;
    window.removeEventListener("mousemove", passivePreflightHandler, false);
    passivePreflightHandler = null;
  };

  const stopFpsProbe = () => {
    if (rafHandle !== null) cancelAnimationFrame(rafHandle);
    rafHandle = null;
    fpsActive = false;
    const intervals = [];
    for (let i = 1; i < frameTimes.length; i++) intervals.push(Number((frameTimes[i] - frameTimes[i - 1]).toFixed(3)));
    send("frame_probe", {
      strokeId: fpsStrokeId,
      startedAtPerformanceMs: fpsStartedAt,
      endedAtPerformanceMs: performance.now(),
      visible: document.visibilityState === "visible",
      intervals
    });
    frameTimes = [];
    fpsStartedAt = null;
    fpsStrokeId = null;
  };

  const startFpsProbe = strokeId => {
    if (fpsActive) return;
    fpsStrokeId = typeof strokeId === "string" ? strokeId : null;
    fpsActive = true;
    fpsStartedAt = performance.now();
    frameTimes = [];
    const frame = timestamp => {
      if (!fpsActive) return;
      if (document.visibilityState !== "visible") {
        stopFpsProbe();
        return;
      }
      frameTimes.push(timestamp);
      rafHandle = requestAnimationFrame(frame);
    };
    rafHandle = requestAnimationFrame(frame);
  };

  const socket = new WebSocket(ENDPOINT);
  socket.addEventListener("open", () => {
    socket.send(JSON.stringify({ type: "auth", token: TOKEN }));
  });
  socket.addEventListener("message", event => {
    let message;
    try { message = JSON.parse(event.data); } catch (_) { return; }
    if (message.type === "ready") {
      connected = true;
      const inputTelemetry = configureInputTelemetry();
      const initialRendererGeometry = readRendererGeometry();
      lastRendererGeometryFingerprint = initialRendererGeometry ? JSON.stringify(initialRendererGeometry) : null;
      send("session_start", {
        monitorStatus: monitor.status(),
        bridgeConfiguration: { inputTelemetry },
        rendererGeometry: initialRendererGeometry,
        browser: navigator.userAgent,
        page: { origin: location.origin, pathname: location.pathname },
        visibilityState: document.visibilityState
      });
      installGeometryListeners();
      installPassivePreflight();
      unsubscribe = monitor.subscribe(item => {
        if (!ALLOWED_EVENTS.has(item.type)) return;
        // BoardPane callbacks are not exposed in every game frame. Pointer
        // candidates are the explicit fallback lifecycle; startFpsProbe/stopFpsProbe
        // are idempotent so engine and pointer events cannot double-count probes.
        if (item.type === "DRAW_START" || item.type === "POINTER_DOWN_CANDIDATE") startFpsProbe(item.strokeId);
        if ((item.type === "DRAW_END" || item.type === "POINTER_UP_CANDIDATE") && fpsActive) stopFpsProbe();
        sentEventCount++;
        lastEventType = item.type;
        lastEventAtPerformanceMs = item.t;
        send("event", { event: item });
      });
      heartbeatTimer = setInterval(() => {
        send("heartbeat", {
          monitorStatus: monitor.status(),
          performanceNowMs: performance.now(),
          visibilityState: document.visibilityState,
          bridgeDiagnostics: {
            sentEventCount,
            lastEventType,
            lastEventAtPerformanceMs,
            sendFailureCount
          }
        });
      }, 1000);
      window.AutoDrawGameMonitorBridge.connected = true;
      console.info("AutoDraw Game Monitor Bridge connected. Session:", sessionId);
    }
  });
  socket.addEventListener("error", () => console.error("AutoDraw Game Monitor Bridge WebSocket error."));
  socket.addEventListener("close", event => {
    connected = false;
    if (unsubscribe) unsubscribe();
    removeGeometryListeners();
    removePassivePreflight();
    if (heartbeatTimer !== null) clearInterval(heartbeatTimer);
    if (geometryUpdateTimer !== null) clearTimeout(geometryUpdateTimer);
    if (rafHandle !== null) cancelAnimationFrame(rafHandle);
    restoreInputTelemetry();
    window.AutoDrawGameMonitorBridge = {
      connected: false, sessionId, closeCode: event.code, closeReason: event.reason,
      inputTelemetry: { ...inputTelemetryConfiguration }
    };
    console.warn("AutoDraw Game Monitor Bridge disconnected:", event.code, event.reason);
  });
  window.AutoDrawGameMonitorBridge = {
    connected: false,
    sessionId,
    disconnect() {
      if (socket.readyState === WebSocket.OPEN) socket.close(1000, "user disconnect");
      else socket.close();
    }
  };
})();
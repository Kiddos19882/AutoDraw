(() => {
  "use strict";
  const TOKEN = "__AUTODRAW_BRIDGE_TOKEN__";
  const ENDPOINT = "ws://127.0.0.1:8765";
  const ALLOWED_EVENTS = new Set([
    "BOARD_ATTACHED", "BOARD_DETACHED", "DRAW_START", "DRAW_START_APPLIED",
    "DRAW_SAMPLE", "DRAW_END", "BRUSH_CHANGE", "BRUSH_CHANGE_APPLIED",
    "POINT_QUOTA_UPDATE", "GAME_METHOD_ERROR", "POINTER_DOWN_CANDIDATE",
    "POINTER_UP_CANDIDATE"
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
  let connected = false;
  let unsubscribe = null;
  let heartbeatTimer = null;
  let rafHandle = null;
  let fpsActive = false;
  let fpsStartedAt = null;
  let frameTimes = [];

  const send = (type, payload = {}) => {
    if (!connected || socket.readyState !== WebSocket.OPEN) return false;
    socket.send(JSON.stringify({ type, sessionId, sequence: ++sequence, sentAtUtc: new Date().toISOString(), ...payload }));
    return true;
  };

  const stopFpsProbe = () => {
    if (rafHandle !== null) cancelAnimationFrame(rafHandle);
    rafHandle = null;
    fpsActive = false;
    const intervals = [];
    for (let i = 1; i < frameTimes.length; i++) intervals.push(Number((frameTimes[i] - frameTimes[i - 1]).toFixed(3)));
    send("frame_probe", {
      startedAtPerformanceMs: fpsStartedAt,
      endedAtPerformanceMs: performance.now(),
      visible: document.visibilityState === "visible",
      intervals
    });
    frameTimes = [];
    fpsStartedAt = null;
  };

  const startFpsProbe = () => {
    fpsEndTimer = null;
    if (fpsActive) return;
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
      send("session_start", {
        monitorStatus: monitor.status(),
        browser: navigator.userAgent,
        page: { origin: location.origin, pathname: location.pathname },
        visibilityState: document.visibilityState
      });
      unsubscribe = monitor.subscribe(item => {
        if (!ALLOWED_EVENTS.has(item.type)) return;
        if (item.type === "DRAW_START") startFpsProbe();
        if (item.type === "DRAW_END" && fpsActive) stopFpsProbe();
        send("event", { event: item });
      });
      heartbeatTimer = setInterval(() => {
        send("heartbeat", {
          monitorStatus: monitor.status(),
          performanceNowMs: performance.now(),
          visibilityState: document.visibilityState
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
    if (heartbeatTimer !== null) clearInterval(heartbeatTimer);
    if (fpsEndTimer !== null) clearTimeout(fpsEndTimer);
    if (rafHandle !== null) cancelAnimationFrame(rafHandle);
    window.AutoDrawGameMonitorBridge = { connected: false, sessionId, closeCode: event.code, closeReason: event.reason };
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
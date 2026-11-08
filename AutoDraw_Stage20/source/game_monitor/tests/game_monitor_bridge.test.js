"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");

const bridgeSource = fs.readFileSync(path.join(__dirname, "..", "game_monitor_bridge.js"), "utf8");

function createBridge({ enabled, initiallyEnabled = false, includeApi = true }) {
  let inputTelemetryEnabled = initiallyEnabled;
  const setterCalls = [];
  const sentMessages = [];
  const socketHandlers = {};
  const windowHandlers = new Map();
  class HTMLCanvasElement {}

  const monitor = {
    status() {
      return { active: true, boardDetected: true, inputTelemetryEnabled };
    },
    inspect() {
      return { renderer: { players: [{ boardClientCorners: {
        topLeft: { x: 498, y: 105 }, bottomRight: { x: 1170, y: 456 }
      }}] } };
    },
    subscribe() {
      return () => {};
    }
  };
  if (includeApi) {
    monitor.setInputTelemetryEnabled = value => {
      setterCalls.push(value);
      inputTelemetryEnabled = value === true;
      return monitor.status();
    };
  }

  class MockWebSocket {
    static OPEN = 1;
    constructor(url) {
      this.url = url;
      this.readyState = MockWebSocket.OPEN;
      this.handlers = new Map();
      socketHandlers.instance = this;
    }
    addEventListener(type, callback) {
      this.handlers.set(type, callback);
    }
    send(value) {
      sentMessages.push(JSON.parse(value));
    }
    emit(type, event = {}) {
      const handler = this.handlers.get(type);
      if (handler) handler(event);
    }
    close(code = 1000, reason = "test close") {
      this.readyState = 3;
      this.emit("close", { code, reason });
    }
  }

  const window = {
    AutoDrawGameMonitor: monitor,
    addEventListener(name, handler) { windowHandlers.set(name, handler); },
    removeEventListener(name) { windowHandlers.delete(name); },
    visualViewport: null
  };
  const document = {
    visibilityState: "visible",
    addEventListener() {},
    removeEventListener() {}
  };
  const sandbox = {
    window,
    document,
    navigator: { userAgent: "Bridge test" },
    location: { origin: "https://game.example", pathname: "/game" },
    crypto: { randomUUID: () => "session-test-id" },
    WebSocket: MockWebSocket,
    HTMLCanvasElement,
    setTimeout: () => 1,
    clearTimeout() {},
    setInterval: () => 1,
    clearInterval() {},
    requestAnimationFrame: () => 1,
    cancelAnimationFrame() {},
    performance: { now: () => 123.456 },
    Date,
    console: { info() {}, warn() {}, error() {} }
  };

  const source = bridgeSource
    .replace("__AUTODRAW_BRIDGE_TOKEN__", "test-token")
    .replace("__AUTODRAW_INPUT_TELEMETRY_ENABLED__", enabled ? "true" : "false");
  vm.runInNewContext(source, sandbox, { filename: "game_monitor_bridge.js" });

  const socket = socketHandlers.instance;
  socket.emit("open");
  socket.emit("message", { data: JSON.stringify({ type: "ready" }) });
  const sessionStart = sentMessages.find(item => item.type === "session_start");
  return {
    window, monitor, socket, setterCalls, sentMessages, sessionStart,
    emitMouse(event) {
      const handler = windowHandlers.get("mousemove");
      if (handler) handler({ target: new HTMLCanvasElement(), isTrusted: true,
        buttons: 0, ...event });
    },
    get inputTelemetryEnabled() { return inputTelemetryEnabled; }
  };
}

test("paired-renderer Bridge enables input telemetry and restores the previous state on disconnect", () => {
  const bridge = createBridge({ enabled: true, initiallyEnabled: false });
  assert.equal(bridge.inputTelemetryEnabled, true);
  assert.deepEqual(bridge.setterCalls, [true]);
  assert.equal(bridge.sessionStart.bridgeConfiguration.inputTelemetry.requested, true);
  assert.equal(bridge.sessionStart.bridgeConfiguration.inputTelemetry.enabled, true);
  assert.equal(bridge.sessionStart.monitorStatus.inputTelemetryEnabled, true);

  bridge.socket.close(1000, "test disconnect");
  assert.equal(bridge.inputTelemetryEnabled, false);
  assert.deepEqual(bridge.setterCalls, [true, false]);
  assert.equal(
    bridge.window.AutoDrawGameMonitorBridge.inputTelemetry.restoreStatus,
    "restored"
  );
});

test("Bridge preserves input telemetry that was already enabled by the user", () => {
  const bridge = createBridge({ enabled: true, initiallyEnabled: true });
  assert.equal(bridge.inputTelemetryEnabled, true);
  assert.deepEqual(bridge.setterCalls, []);
  bridge.socket.close();
  assert.equal(bridge.inputTelemetryEnabled, true);
  assert.deepEqual(bridge.setterCalls, []);
});

test("ordinary Bridge mode leaves input telemetry unchanged", () => {
  const bridge = createBridge({ enabled: false, initiallyEnabled: false });
  assert.equal(bridge.inputTelemetryEnabled, false);
  assert.deepEqual(bridge.setterCalls, []);
  assert.equal(bridge.sessionStart.bridgeConfiguration.inputTelemetry.requested, false);
  bridge.socket.close();
  assert.equal(bridge.inputTelemetryEnabled, false);
  assert.deepEqual(bridge.setterCalls, []);
});

test("paired-renderer mode reports unavailable when Monitor cannot control input telemetry", () => {
  const bridge = createBridge({ enabled: true, initiallyEnabled: false, includeApi: false });
  assert.equal(bridge.inputTelemetryEnabled, false);
  assert.equal(bridge.sessionStart.bridgeConfiguration.inputTelemetry.restoreStatus, "api_unavailable");
  bridge.socket.close();
  assert.equal(bridge.inputTelemetryEnabled, false);
});


test("opt-in Bridge captures trusted passive DOM screen coordinates without a draw event", () => {
  const bridge = createBridge({ enabled: true });
  bridge.emitMouse({ clientX: 600, clientY: 220, screenX: 600, screenY: 383 });
  const witnesses = bridge.sentMessages.filter(item => item.type === "preflight_sample");
  assert.equal(witnesses.length, 1);
  assert.equal(witnesses[0].sample.source, "window-bubble-after-egret-canvas");
  assert.equal(witnesses[0].sample.buttons, 0);
  assert.equal(witnesses[0].sample.screenY - witnesses[0].sample.clientY, 163);
  bridge.socket.close();
});

test("Bridge never probes with buttons held or outside observed BoardPane", () => {
  const bridge = createBridge({ enabled: true });
  bridge.emitMouse({ clientX: 600, clientY: 220, screenX: 600, screenY: 383,
                     buttons: 1 });
  bridge.emitMouse({ clientX: 100, clientY: 220, screenX: 100, screenY: 383 });
  assert.equal(bridge.sentMessages.filter(item => item.type === "preflight_sample").length, 0);
  bridge.socket.close();
});

test("ordinary Bridge does not collect passive preflight samples", () => {
  const bridge = createBridge({ enabled: false });
  bridge.emitMouse({ clientX: 600, clientY: 220, screenX: 600, screenY: 383 });
  assert.equal(bridge.sentMessages.filter(item => item.type === "preflight_sample").length, 0);
  bridge.socket.close();
});


test("no passive events are emitted when requested input telemetry is unavailable", () => {
  const bridge = createBridge({ enabled: true, includeApi: false });
  bridge.emitMouse({ clientX: 600, clientY: 220, screenX: 600, screenY: 383 });
  assert.equal(bridge.sentMessages.filter(item => item.type === "preflight_sample").length, 0);
  bridge.socket.close();
});

"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");

const monitorSource = fs.readFileSync(path.join(__dirname, "..", "game_monitor.js"), "utf8");

function createMonitor() {
  let timerId = 0;
  const timers = new Map();
  const window = {
    top: null,
    addEventListener() {},
    removeEventListener() {},
    setInterval(callback, interval) {
      const id = ++timerId;
      timers.set(id, { callback, interval });
      return id;
    },
    clearInterval(id) {
      timers.delete(id);
    }
  };
  window.top = window;

  const sandbox = {
    window,
    performance: { now: () => 123.456 },
    location: {
      origin: "https://game.example",
      pathname: "/game",
      href: "https://game.example/game"
    },
    document: { querySelectorAll: () => [] },
    URL,
    HTMLCanvasElement: class HTMLCanvasElement {},
    console
  };

  vm.runInNewContext(monitorSource, sandbox, { filename: "game_monitor.js" });
  return { monitor: window.AutoDrawGameMonitor, timers, window };
}

function createBoard() {
  let pointIndexReads = 0;
  const pointStrokes = [[]];
  const points = new Proxy(pointStrokes, {
    get(target, property, receiver) {
      if (typeof property === "string" && /^\d+$/.test(property)) {
        pointIndexReads++;
      }
      return Reflect.get(target, property, receiver);
    }
  });

  const board = {
    atom: { points, radius: [3] },
    max: 3000,
    less: 3000,
    width: 460,
    height: 240,
    scaleX: 1,
    scaleY: 1,
    onDrawStart() {},
    onDrawing() {},
    onDrawingEnd() {},
    setRadius(value) { this.atom.radius[this.atom.radius.length - 1] = value; },
    updateLess() {
      let total = 0;
      for (let i = 0; i < this.atom.points.length; i++) {
        total += this.atom.points[i].length;
      }
      this.less = this.max - total;
      this.pointIndexReadsAtEngineReturn = pointIndexReads;
    }
  };

  return {
    board,
    getPointIndexReads: () => pointIndexReads
  };
}

test("resource snapshot reads exact max/less fields and derives point count", () => {
  const { monitor } = createMonitor();
  const { board } = createBoard();
  monitor.attach(board);

  const snapshot = monitor.status().snapshot;
  assert.equal(snapshot.maxPoints, 3000);
  assert.equal(snapshot.remainingPoints, 3000);
  assert.equal(snapshot.pointCount, 0);
  assert.equal(snapshot.isExact, true);
  assert.equal(snapshot.sourceMethod, "BoardPane.max+BoardPane.less");
  assert.equal(snapshot.validationStatus, "valid");
});

test("hot-path wrappers, status and export do not scan atom.points", () => {
  const { monitor } = createMonitor();
  const { board, getPointIndexReads } = createBoard();
  const originalUpdateLess = board.updateLess;
  monitor.attach(board);

  const readsBefore = getPointIndexReads();
  monitor.status();
  monitor.export();
  assert.equal(getPointIndexReads(), readsBefore);

  board.atom.points[0].push({ x: 10, y: 10 }, { x: 11, y: 10 });
  board.updateLess();
  assert.equal(board.less, 2998);
  assert.equal(board.pointIndexReadsAtEngineReturn, getPointIndexReads());

  const snapshot = monitor.status().snapshot;
  assert.equal(snapshot.pointCount, 2);
  assert.equal(snapshot.remainingPoints, 2998);
  assert.equal(snapshot.isExact, true);

  // The explicit diagnostic is the only API that intentionally scans points.
  const diagnostic = monitor.diagnosticSnapshot();
  assert.equal(diagnostic.diagnosticPointCount, 2);
  assert.equal(diagnostic.pointCountMatches, true);
  assert.ok(getPointIndexReads() > board.pointIndexReadsAtEngineReturn);

  monitor.stop();
  assert.equal(board.updateLess, originalUpdateLess);
});

test("missing or invalid engine fields return unavailable without array fallback", () => {
  const { monitor } = createMonitor();
  const { board, getPointIndexReads } = createBoard();
  monitor.attach(board);

  board.less = undefined;
  const readsBefore = getPointIndexReads();
  const snapshot = monitor.status().snapshot;

  assert.equal(snapshot.isExact, false);
  assert.equal(snapshot.validationStatus, "unavailable");
  assert.equal(snapshot.pointCount, null);
  assert.equal(snapshot.remainingPoints, null);
  assert.equal(getPointIndexReads(), readsBefore);
});

test("resource delta equals the change in exact engine point count", () => {
  const { monitor } = createMonitor();
  const { board } = createBoard();
  monitor.attach(board);

  const before = monitor.status().snapshot.pointCount;
  board.atom.points[0].push({ x: 12, y: 10 }, { x: 13, y: 10 }, { x: 14, y: 10 });
  board.updateLess();
  const after = monitor.status().snapshot.pointCount;

  assert.equal(after - before, 3);
  assert.equal(monitor.diagnosticSnapshot().pointCountMatches, true);
  monitor.stop();
});


test("read-only inspect captures exact CHALK while monitor is stopped", () => {
  const { monitor, window } = createMonitor();
  const { board } = createBoard();
  const originalUpdateLess = board.updateLess;
  window.egret = { MainContext: { instance: { stage: { $children: [board] } } } };

  monitor.stop();
  const result = monitor.inspect();

  assert.equal(result.inspectionMode, "read_only");
  assert.equal(result.boardDetected, true);
  assert.equal(result.snapshot.maxPoints, 3000);
  assert.equal(result.snapshot.remainingPoints, 3000);
  assert.equal(result.snapshot.pointCount, 0);
  assert.equal(result.snapshot.isExact, true);
  assert.equal(monitor.status().active, false);
  assert.equal(board.updateLess, originalUpdateLess);
});


test("unchanged updateLess calls do not create duplicate quota events", () => {
  const { monitor } = createMonitor();
  const { board } = createBoard();
  monitor.attach(board);

  const before = monitor.status().eventCount;
  board.updateLess();
  assert.equal(monitor.status().eventCount, before);

  board.atom.points[0].push({ x: 1, y: 1 });
  board.updateLess();
  assert.equal(monitor.status().eventCount, before + 1);
  assert.equal(monitor.status().snapshot.pointCount, 1);
  monitor.stop();
});


test("resource snapshots expose the actual current brush radius", () => {
  const { monitor } = createMonitor();
  const { board } = createBoard();
  monitor.attach(board);

  assert.equal(monitor.status().snapshot.currentRadius, 3);
  board.setRadius(7);
  const snapshot = monitor.status().snapshot;

  assert.equal(snapshot.currentRadius, 7);
  assert.equal(snapshot.radius.length, 1);
  assert.equal(snapshot.radius[0], 7);
  monitor.stop();
});

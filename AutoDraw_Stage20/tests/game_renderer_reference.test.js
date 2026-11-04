"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  buildSmoothPathCommands,
  buildNormalPathCommands,
  terminalPoint
} = require("./game_renderer_reference.js");

test("smooth one-point path contains moveTo only and has no segment endpoint", () => {
  const points = [{ x: 4, y: 7 }];
  const commands = buildSmoothPathCommands(points, true, false);

  assert.deepEqual(commands, [
    { type: "moveTo", x: 4, y: 7 },
    { type: "moveTo", x: 4, y: 7 }
  ]);
  assert.equal(terminalPoint(points, true, false), null);
});

test("smooth two-point path terminates at the midpoint when final line is disabled", () => {
  const points = [{ x: 10, y: 20 }, { x: 30, y: 40 }];
  const commands = buildSmoothPathCommands(points, true, false);

  assert.deepEqual(commands.at(-1), { type: "lineTo", x: 20, y: 30 });
  assert.deepEqual(terminalPoint(points, true, false), { x: 20, y: 30 });
  assert.equal(commands.some(command => command.type === "lineTo" && command.x === 30 && command.y === 40), false);
});

test("smooth three-point path ends at the last pair midpoint, not the last point", () => {
  const points = [{ x: 0, y: 0 }, { x: 10, y: 20 }, { x: 30, y: 20 }];
  const commands = buildSmoothPathCommands(points, true, false);

  assert.deepEqual(commands, [
    { type: "moveTo", x: 0, y: 0 },
    { type: "moveTo", x: 0, y: 0 },
    { type: "lineTo", x: 5, y: 10 },
    { type: "curveTo", controlX: 10, controlY: 20, x: 20, y: 20 }
  ]);
  assert.deepEqual(terminalPoint(points, true, false), { x: 20, y: 20 });
});

test("normal path includes the final accepted point", () => {
  const points = [{ x: 0, y: 0 }, { x: 10, y: 5 }, { x: 30, y: 15 }];
  const commands = buildNormalPathCommands(points);

  assert.deepEqual(commands, [
    { type: "moveTo", x: 0, y: 0 },
    { type: "lineTo", x: 10, y: 5 },
    { type: "lineTo", x: 30, y: 15 }
  ]);
  assert.deepEqual(terminalPoint(points, false, false), { x: 30, y: 15 });
});

test("empty paths produce no drawing commands", () => {
  assert.deepEqual(buildSmoothPathCommands([], true, false), []);
  assert.deepEqual(buildNormalPathCommands([]), []);
  assert.equal(terminalPoint([], true, false), null);
});

test("the source call's fourth formal argument is not the final-line flag", () => {
  const points = [{ x: 0, y: 0 }, { x: 10, y: 10 }];
  const sourceCall = buildSmoothPathCommands(points, true, false);
  const explicitFinalLine = buildSmoothPathCommands(points, true, false, true);

  assert.deepEqual(sourceCall.at(-1), { type: "lineTo", x: 5, y: 5 });
  assert.deepEqual(explicitFinalLine.at(-1), { type: "lineTo", x: 10, y: 10 });
});

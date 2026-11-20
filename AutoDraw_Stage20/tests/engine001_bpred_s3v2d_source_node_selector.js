/* BPRED-S3v2d: thin source-proven node selector over immutable S3v2c full trace.
   Selection uses ONLY frozen source node geometry/drawData, never RGBA result,
   capture position, alpha coverage or a model-fitting step. */
(function(root) {
  "use strict";
  root.AutoDrawBPRED_S3v2CanvasCapture = function(strokes) {
    if (!root.AutoDrawBPRED_S3v2cCaptureTrace ||
        !Array.isArray(strokes) || ![1,2].includes(strokes.length)) {
      throw new Error("BLOCKED_BPRED_S3V2D_SOURCE_TRACE_UNAVAILABLE");
    }
    const trace = root.AutoDrawBPRED_S3v2cCaptureTrace(strokes);
    if (!trace || !trace.originalCanvasRendererRestored ||
        trace.schema !== "ENGINE001_BPRED_S3V2C_ORIGINAL_CANVAS_MULTICAPTURE_TRACE" ||
        !Array.isArray(trace.captures) || trace.captures.length !== 2) {
      throw new Error("BLOCKED_BPRED_S3V2D_UNFROZEN_CAPTURE_COUNT");
    }
    function equalNumbers(a, b) {
      return Array.isArray(a) && a.length === b.length &&
        a.every((v, i) => Number.isFinite(v) && v === b[i]);
    }
    function mainNode(c) {
      return c && c.node &&
        c.node.x === -2 && c.node.y === -2 &&
        c.node.width === 464 && c.node.height === 244 &&
        c.drawDataCount === strokes.length + 2 &&
        equalNumbers(c.size, [1392, 732]) &&
        equalNumbers(c.transform, [3, 0, 0, 3, 6, 6]);
    }
    function maskNode(c) {
      return c && c.node &&
        c.node.x === 0 && c.node.y === 0 &&
        c.node.width === 460 && c.node.height === 240 &&
        c.drawDataCount === 1 &&
        equalNumbers(c.size, [1380, 720]) &&
        equalNumbers(c.transform, [3, 0, 0, 3, 0, 0]);
    }
    const mains = trace.captures.filter(mainNode);
    const masks = trace.captures.filter(maskNode);
    if (mains.length !== 1 || masks.length !== 1 ||
        mains[0] === masks[0]) {
      throw new Error("BLOCKED_BPRED_S3V2D_MAIN_MASK_NOT_UNIQUE");
    }
    function adapt(c) {
      return {
        chronologicalIndex: c.chronologicalIndex,
        drawDataCount: c.drawDataCount,
        node: c.node,
        canvasSize: c.size,
        transform: c.transform,
        originalCanvasPngDataUrl: c.rawCanvasPngDataUrl
      };
    }
    return {
      schema: "ENGINE001_BPRED_S3V2_TRUE_NATIVE_CANVAS_WEBGL_PAIR",
      originalCanvasRendererRestored: true,
      sourceStrokeCount: strokes.length,
      structuralSelectionVersion: "S3V2D_SOURCE_NODE_GEOMETRY_FROZEN_V1",
      originalCaptureCount: trace.captures.length,
      captures: [adapt(mains[0])],
      mask_capture: adapt(masks[0]),
      native: trace.native
    };
  };
})(window);

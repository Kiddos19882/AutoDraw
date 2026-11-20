/* BPRED-S3v2: scoped TRUE original Egret CanvasRenderer instrumentation.
   P4D15 capture idiom reused; source drawing, renderGraphics and WebGL untouched.
   This capture is diagnostic only; always restore the original in finally. */
(function(root) {
  "use strict";
  root.AutoDrawBPRED_S3v2CanvasCapture = function(strokes) {
    if (!Array.isArray(strokes) || ![1, 2].includes(strokes.length) ||
        !root.egret || typeof egret.CanvasRenderer !== "function" ||
        !root.AutoDrawGameRendererReference ||
        typeof root.AutoDrawGameRendererReference.renderP4A2BrushWidths1to10Probe !== "function") {
      throw new Error("BLOCKED_BPRED_S3V2_ORIGINAL_RENDERER_UNAVAILABLE");
    }
    const proto = egret.CanvasRenderer.prototype;
    const original = proto.renderGraphics;
    if (typeof original !== "function") {
      throw new Error("BLOCKED_BPRED_S3V2_NO_CANVAS_GRAPHICS");
    }
    const captures = [];
    proto.renderGraphics = function(node, context, forHitTest) {
      const result = original.call(this, node, context, forHitTest);
      if (node && Array.isArray(node.drawData) && node.drawData.length &&
          !forHitTest) {
        if (!context || !context.canvas || typeof context.canvas.toDataURL !== "function" ||
            typeof context.getTransform !== "function" ||
            ![node.x, node.y, node.width, node.height].every(Number.isFinite)) {
          throw new Error("BLOCKED_BPRED_S3V2_INVALID_ORIGINAL_CONTEXT");
        }
        const t = context.getTransform();
        const canvas = context.canvas;
        if (![t.a, t.b, t.c, t.d, t.e, t.f].every(Number.isFinite) ||
            !Number.isInteger(canvas.width) || !Number.isInteger(canvas.height)) {
          throw new Error("BLOCKED_BPRED_S3V2_INVALID_NATIVE_TRANSFORM");
        }
        captures.push({
          drawDataCount: node.drawData.length,
          node: {x: node.x, y: node.y, width: node.width, height: node.height},
          canvasSize: [canvas.width, canvas.height],
          transform: [t.a, t.b, t.c, t.d, t.e, t.f],
          originalCanvasPngDataUrl: canvas.toDataURL("image/png")
        });
      }
      return result;
    };
    let native;
    try {
      native = root.AutoDrawGameRendererReference
        .renderP4A2BrushWidths1to10Probe(strokes);
    } finally {
      proto.renderGraphics = original;
    }
    if (proto.renderGraphics !== original ||
        !native || native.schema !== "ENGINE001_B1R_P4A2_NATIVE_1_TO_10" ||
        native.renderer !== "real Egret 5.4.1 BoardPane/WebGLRenderer" ||
        native.strokeCount !== strokes.length ||
        native.syntheticAcceptedVerticesNotChalk !== 2 * strokes.length ||
        captures.length !== 1) {
      throw new Error("BLOCKED_BPRED_S3V2_AMBIGUOUS_TRUE_CANVAS_CAPTURE_" +
                      captures.length);
    }
    return {
      schema: "ENGINE001_BPRED_S3V2_TRUE_NATIVE_CANVAS_WEBGL_PAIR",
      originalCanvasRendererRestored: true,
      sourceStrokeCount: strokes.length,
      captures: captures,
      native: native
    };
  };
})(window);

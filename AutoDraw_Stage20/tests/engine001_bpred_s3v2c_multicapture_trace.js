/* BPRED-S3v2c: P4D15-original scoped CanvasRenderer trace, do NOT select a capture.
 * Never changes BoardPane paths, source nodes, CanvasRenderer draw code or game.
 */
(function(root) {
  "use strict";
  root.AutoDrawBPRED_S3v2cCaptureTrace = function(strokes) {
    if (!Array.isArray(strokes) || ![1, 2].includes(strokes.length) ||
        !root.egret || typeof egret.CanvasRenderer !== "function" ||
        !root.AutoDrawGameRendererReference) {
      throw new Error("BLOCKED_BPRED_S3V2C_SOURCE_UNAVAILABLE");
    }
    const proto = egret.CanvasRenderer.prototype;
    const original = proto.renderGraphics;
    if (typeof original !== "function") {
      throw new Error("BLOCKED_BPRED_S3V2C_NO_ORIGINAL_CANVAS_RENDER");
    }
    const captures = [];
    proto.renderGraphics = function(node, context, forHitTest) {
      const value = original.call(this, node, context, forHitTest);
      if (node && Array.isArray(node.drawData) && node.drawData.length > 0 && !forHitTest) {
        if (!context || !context.canvas || typeof context.canvas.toDataURL !== "function" ||
            typeof context.getTransform !== "function" ||
            ![node.x,node.y,node.width,node.height].every(Number.isFinite)) {
          throw new Error("BLOCKED_BPRED_S3V2C_CONTEXT_INVALID");
        }
        const t = context.getTransform();
        if (![t.a,t.b,t.c,t.d,t.e,t.f].every(Number.isFinite)) {
          throw new Error("BLOCKED_BPRED_S3V2C_TRANSFORM_INVALID");
        }
        captures.push({
          chronologicalIndex: captures.length,
          drawDataCount: node.drawData.length,
          node: {x:node.x,y:node.y,width:node.width,height:node.height},
          size: [context.canvas.width,context.canvas.height],
          transform: [t.a,t.b,t.c,t.d,t.e,t.f],
          rawCanvasPngDataUrl: context.canvas.toDataURL("image/png")
        });
      }
      return value;
    };
    let native;
    try {
      native = root.AutoDrawGameRendererReference
        .renderP4A2BrushWidths1to10Probe(strokes);
    } finally {
      proto.renderGraphics = original;
    }
    if (proto.renderGraphics !== original || !native ||
        native.schema !== "ENGINE001_B1R_P4A2_NATIVE_1_TO_10" ||
        native.renderer !== "real Egret 5.4.1 BoardPane/WebGLRenderer" ||
        native.strokeCount !== strokes.length ||
        native.syntheticAcceptedVerticesNotChalk !== 2 * strokes.length ||
        captures.length < 1 || captures.length > 64) {
      throw new Error("BLOCKED_BPRED_S3V2C_INVALID_FINAL_NATIVE_OR_TRACE_" + captures.length);
    }
    return {
      schema: "ENGINE001_BPRED_S3V2C_ORIGINAL_CANVAS_MULTICAPTURE_TRACE",
      originalCanvasRendererRestored: true,
      originalStrokeCount: strokes.length,
      captures: captures,
      native: native
    };
  };
})(window);

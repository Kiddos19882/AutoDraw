/* ENGINE-001/BPRED-S3v2h: scoped *original* CanvasRenderingContext2D.stroke
 * post-call snapshots. Observe, never mutate native Canvas/Egret drawing.
 * Relies on frozen S3v2c source trace and S3v2d main/mask source selector.
 */
(function (root) {
  "use strict";
  root.AutoDrawBPRED_S3v2hOriginalStrokeStepTrace = function (strokes) {
    if (!Array.isArray(strokes) || ![1, 2].includes(strokes.length) ||
        typeof root.AutoDrawBPRED_S3v2CanvasCapture !== "function" ||
        !root.CanvasRenderingContext2D ||
        typeof root.CanvasRenderingContext2D.prototype.stroke !== "function") {
      throw new Error("BLOCKED_BPRED_S3V2H_NATIVE_SOURCE_UNAVAILABLE");
    }
    const proto = root.CanvasRenderingContext2D.prototype;
    const original = proto.stroke;
    const steps = [];
    const other = [];
    proto.stroke = function () {
      // Original call must happen with unchanged receiver and arguments.
      const value = original.apply(this, arguments);
      const canvas = this.canvas;
      const size = canvas ? [canvas.width, canvas.height] : null;
      const main = size && size[0] === 1392 && size[1] === 732;
      const mask = size && size[0] === 1380 && size[1] === 720;
      if (main || mask) {
        const transform = this.getTransform();
        const event = {
          chronology: steps.length + other.length,
          canvasSize: size,
          kind: main ? "original_main" : "original_mask",
          transform: [transform.a,transform.b,transform.c,
                      transform.d,transform.e,transform.f],
          globalCompositeOperation: this.globalCompositeOperation,
          globalAlpha: this.globalAlpha,
          lineWidth: this.lineWidth,
          lineCap: this.lineCap,
          lineJoin: this.lineJoin,
          originalNativePngDataUrl: main ? canvas.toDataURL("image/png") : null
        };
        if (main) steps.push(event); else other.push(event);
      }
      if (steps.length > 32 || other.length > 32) {
        throw new Error("BLOCKED_BPRED_S3V2H_UNBOUNDED_NATIVE_STROKES");
      }
      return value;
    };
    let result;
    try {
      result = root.AutoDrawBPRED_S3v2CanvasCapture(strokes);
    } finally {
      proto.stroke = original;
    }
    if (proto.stroke !== original || !result ||
        result.schema !== "ENGINE001_BPRED_S3V2_TRUE_NATIVE_CANVAS_WEBGL_PAIR" ||
        result.originalCanvasRendererRestored !== true ||
        result.originalCaptureCount !== 2 ||
        result.structuralSelectionVersion !==
          "S3V2D_SOURCE_NODE_GEOMETRY_FROZEN_V1") {
      throw new Error("BLOCKED_BPRED_S3V2H_ORIGINAL_METHOD_NOT_RESTORED");
    }
    return {
      schema: "ENGINE001_BPRED_S3V2H_ORIGINAL_CANVAS_STROKE_STEP_TRACE",
      originalStrokeMethodRestored: true,
      trueMainStrokeCalls: steps.length,
      originalMaskStrokeCalls: other.length,
      mainStrokeSnapshots: steps,
      maskStrokeMetadata: other,
      source: result
    };
  };
})(window);

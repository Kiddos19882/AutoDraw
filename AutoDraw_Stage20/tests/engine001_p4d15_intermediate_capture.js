/* P4D15: scoped instrument of the genuine CanvasRenderer used by WebGLRenderer.
   It wraps only for one original BoardPane scene and ALWAYS restores in finally.
   It does not change drawing commands, colors, boundaries or production files. */
(function(root) {
  "use strict";
  root.AutoDrawP4D15Capture = function(strokes) {
    if (!Array.isArray(strokes) || strokes.length !== 21 ||
        !root.egret || typeof egret.CanvasRenderer !== "function" ||
        !root.AutoDrawGameRendererReference) {
      throw new Error("BLOCKED_P4D15_NATIVE_PRECONDITIONS");
    }
    const proto = egret.CanvasRenderer.prototype;
    const original = proto.renderGraphics;
    if (typeof original !== "function") {
      throw new Error("BLOCKED_P4D15_NO_REAL_CANVAS_RENDER_GRAPHICS");
    }
    const captures = [];
    proto.renderGraphics = function(node, context, forHitTest) {
      const value = original.call(this, node, context, forHitTest);
      if (node && Array.isArray(node.drawData) &&
          node.drawData.length > 10 && !forHitTest) {
        if (!context || !context.canvas ||
            typeof context.canvas.toDataURL !== "function" ||
            !Number.isFinite(node.x) || !Number.isFinite(node.y) ||
            !Number.isFinite(node.width) || !Number.isFinite(node.height)) {
          throw new Error("BLOCKED_P4D15_NOT_ORIGINAL_CANVAS_CONTEXT");
        }
        const tr = context.getTransform ? context.getTransform() : null;
        captures.push({
          drawDataCount:node.drawData.length,
          node:{x:node.x,y:node.y,width:node.width,height:node.height},
          canvasWidth:context.canvas.width,
          canvasHeight:context.canvas.height,
          transform:tr ? [tr.a,tr.b,tr.c,tr.d,tr.e,tr.f] : null,
          originalCanvasPngDataUrl:context.canvas.toDataURL("image/png")
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
    if (proto.renderGraphics !== original || captures.length !== 1 ||
        captures[0].drawDataCount < 21 ||
        native.schema !== "ENGINE001_B1R_P4A2_NATIVE_1_TO_10" ||
        native.strokeCount !== 21 ||
        native.renderer !== "real Egret 5.4.1 BoardPane/WebGLRenderer") {
      throw new Error("BLOCKED_P4D15_NATIVE_SOURCE_CAPTURE_INCOMPLETE");
    }
    return {
      schema:"ENGINE001_B1R_P4D15_TRUE_NATIVE_CANVAS_STAGE_PAIR",
      underlyingCanvasRendererRestored:true,
      intermediate:captures[0],
      native:native
    };
  };
})(window);

/* ENGINE-001 BPRED-S3v2f: non-mutating, scoped original GL texture upload observer.
 * Uses original S3v2c trace and source-proven S3v2d main+mask selector.
 * This is NOT a GL state changer, a rendering substitution or game integration.
 */
(function (root) {
  "use strict";
  root.AutoDrawBPRED_S3v2fCapture = function (strokes) {
    if (typeof root.AutoDrawBPRED_S3v2CanvasCapture !== "function" ||
        !Array.isArray(strokes) || ![1, 2].includes(strokes.length)) {
      throw new Error("BLOCKED_BPRED_S3V2F_SOURCE_SELECTOR_UNAVAILABLE");
    }
    const proto = root.WebGLRenderingContext && root.WebGLRenderingContext.prototype;
    if (!proto || typeof proto.texImage2D !== "function" ||
        typeof proto.texSubImage2D !== "function" ||
        typeof proto.pixelStorei !== "function") {
      throw new Error("BLOCKED_BPRED_S3V2F_REAL_WEBGL_UNAVAILABLE");
    }
    const originals = {
      texImage2D: proto.texImage2D,
      texSubImage2D: proto.texSubImage2D,
      pixelStorei: proto.pixelStorei
    };
    const calls = [], stores = [];
    const sampleState = function (gl) {
      return {
        unpackPremultiplyAlpha: gl.getParameter(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL),
        unpackColorspaceConversion: gl.getParameter(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL),
        unpackAlignment: gl.getParameter(gl.UNPACK_ALIGNMENT)
      };
    };
    const wrapper = function (method) {
      return function () {
        const source = arguments[arguments.length - 1];
        const sourceTag = source && source.constructor && source.constructor.name || null;
        const w = source && Number.isInteger(source.width) ? source.width : null;
        const h = source && Number.isInteger(source.height) ? source.height : null;
        const before = sampleState(this);
        const value = originals[method].apply(this, arguments);
        if (calls.length >= 256) {
          throw new Error("BLOCKED_BPRED_S3V2F_GL_TRACE_CAP");
        }
        calls.push({
          method: method,
          sourceType: sourceTag,
          sourceWidth: w,
          sourceHeight: h,
          argCount: arguments.length,
          unpackBefore: before,
          unpackAfter: sampleState(this)
        });
        return value;
      };
    };
    proto.texImage2D = wrapper("texImage2D");
    proto.texSubImage2D = wrapper("texSubImage2D");
    proto.pixelStorei = function (pname, param) {
      const value = originals.pixelStorei.apply(this, arguments);
      if (stores.length >= 256) {
        throw new Error("BLOCKED_BPRED_S3V2F_GL_PIXELSTORE_CAP");
      }
      stores.push({pname:pname, param:param, after:sampleState(this)});
      return value;
    };
    let result;
    try {
      result = root.AutoDrawBPRED_S3v2CanvasCapture(strokes);
    } finally {
      proto.texImage2D = originals.texImage2D;
      proto.texSubImage2D = originals.texSubImage2D;
      proto.pixelStorei = originals.pixelStorei;
    }
    if (proto.texImage2D !== originals.texImage2D ||
        proto.texSubImage2D !== originals.texSubImage2D ||
        proto.pixelStorei !== originals.pixelStorei ||
        !result || result.schema !== "ENGINE001_BPRED_S3V2_TRUE_NATIVE_CANVAS_WEBGL_PAIR" ||
        result.originalCanvasRendererRestored !== true ||
        result.originalCaptureCount !== 2 ||
        result.structuralSelectionVersion !== "S3V2D_SOURCE_NODE_GEOMETRY_FROZEN_V1") {
      throw new Error("BLOCKED_BPRED_S3V2F_GL_ORIGINAL_NOT_RESTORED");
    }
    const mainUploads = calls.filter(c => c.sourceWidth === 1392 &&
      c.sourceHeight === 732 && c.sourceType &&
      /Canvas/.test(c.sourceType));
    if (!mainUploads.length) {
      throw new Error("BLOCKED_BPRED_S3V2F_TRUE_MAIN_GL_UPLOAD_MISSING");
    }
    return {
      schema: "ENGINE001_BPRED_S3V2F_TRUE_ORIGINAL_MAIN_MASK_GL",
      originalMethodsRestored: true,
      glUploads: calls,
      glPixelStoreEvents: stores,
      mainCanvasTypedUploadCount: mainUploads.length,
      source: result
    };
  };
})(window);

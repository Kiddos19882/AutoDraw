/* ENGINE-001/BPRED-S3v2p: read-only Canvas2D byte observation, native original
 * CanvasRenderingContext2D.stroke() already observed by frozen S3v2h.
 * Captures getImageData AFTER each true main stroke, BEFORE inner PNG snapshot.
 * Never putImageData, never replay custom stroke or replace original renderer.
 */
(function (root) {
  "use strict";
  const SCHEMA = "ENGINE001_BPRED_S3V2P_TRUE_MAIN_GETIMAGEDATA_ROI_V1";
  const ROI = {x:400,y:220,width:270,height:270};
  if (!root.CanvasRenderingContext2D ||
      !root.AutoDrawBPRED_S3v2hOriginalStrokeStepTrace ||
      typeof root.AutoDrawBPRED_S3v2hOriginalStrokeStepTrace !== "function" ||
      root.AutoDrawBPRED_S3v2pReadbackWrapperInstalled === true) {
    throw new Error("BLOCKED_BPRED_S3V2P_MISSING_OR_REPEATED_NATIVE_WRAPPER");
  }
  const originalTrace = root.AutoDrawBPRED_S3v2hOriginalStrokeStepTrace;
  root.AutoDrawBPRED_S3v2pOriginalTrace = originalTrace;
  root.AutoDrawBPRED_S3v2pLastReadback = null;
  function encodeExact(data) {
    const chunks = [];
    // Avoid Function.prototype.apply argument limits on 270*270*4 bytes.
    for (let offset=0; offset<data.length; offset+=8192) {
      const part=data.subarray(offset,Math.min(offset+8192,data.length));
      let s="";
      for (let i=0;i<part.length;i++) s+=String.fromCharCode(part[i]);
      chunks.push(s);
    }
    return root.btoa(chunks.join(""));
  }
  root.AutoDrawBPRED_S3v2hOriginalStrokeStepTrace = function (strokes) {
    const proto = root.CanvasRenderingContext2D.prototype;
    const originalStroke = proto.stroke;
    const samples=[];
    root.AutoDrawBPRED_S3v2pLastReadback = null;
    proto.stroke = function () {
      const ret = originalStroke.apply(this, arguments);
      const canvas=this.canvas;
      if (canvas && canvas.width===1392 && canvas.height===732) {
        if (ROI.x+ROI.width>canvas.width || ROI.y+ROI.height>canvas.height) {
          throw new Error("BLOCKED_BPRED_S3V2P_NATIVE_ROI_OUTSIDE_MAIN");
        }
        const image=this.getImageData(ROI.x,ROI.y,ROI.width,ROI.height);
        if (!(image.data instanceof root.Uint8ClampedArray) ||
            image.data.length!==ROI.width*ROI.height*4) {
          throw new Error("BLOCKED_BPRED_S3V2P_NATIVE_ROI_BYTES_INVALID");
        }
        samples.push({
          schema: SCHEMA, sampleIndex:samples.length+1,
          canvasSize:[canvas.width,canvas.height],
          roi:{x:ROI.x,y:ROI.y,width:ROI.width,height:ROI.height},
          rawRGBA_base64:encodeExact(image.data)
        });
      }
      return ret;
    };
    let result;
    try {
      // Frozen S3v2h wraps this observer, invokes original stroke exactly once
      // and collects its own full original Canvas PNG snapshots.
      result=originalTrace(strokes);
    } finally {
      proto.stroke=originalStroke;
    }
    if (proto.stroke!==originalStroke || !result ||
        result.schema!=="ENGINE001_BPRED_S3V2H_ORIGINAL_CANVAS_STROKE_STEP_TRACE" ||
        result.originalStrokeMethodRestored!==true ||
        result.trueMainStrokeCalls!==samples.length ||
        samples.length<1 || samples.length>32) {
      throw new Error("BLOCKED_BPRED_S3V2P_ORIGINAL_STROKE_CAPTURE_DRIFT");
    }
    root.AutoDrawBPRED_S3v2pLastReadback = {
      schema:SCHEMA, sampleCount:samples.length, samples:samples,
      originalTraceRestored:proto.stroke===originalStroke
    };
    return result;
  };
  root.AutoDrawBPRED_S3v2pReadbackWrapperInstalled=true;
})(window);

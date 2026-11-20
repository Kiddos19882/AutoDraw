/* BPRED-S3v2q research-only TRUE original Egret main Canvas before/after
 * every native CanvasRenderingContext2D.stroke() with immediately repeated
 * readback after stroke. Preserve original native method and frozen S3v2h
 * complete per-stroke PNG observer. Never perform synthetic drawing.
 */
(function(root) {
  "use strict";
  const SCHEMA="ENGINE001_BPRED_S3V2Q_TRUE_MAIN_INCREMENTAL_MICROALPHA_V1";
  const ROI=Object.freeze({x:400,y:220,width:270,height:270});
  if (root.AutoDrawBPRED_S3v2qObserverInstalled === true ||
      typeof root.AutoDrawBPRED_S3v2hOriginalStrokeStepTrace !== "function" ||
      !root.CanvasRenderingContext2D ||
      typeof root.CanvasRenderingContext2D.prototype.stroke !== "function" ||
      typeof root.btoa !== "function") {
    throw new Error("BLOCKED_BPRED_S3V2Q_ORIGINAL_NATIVE_TRACE_MISSING");
  }
  const originalTrace=root.AutoDrawBPRED_S3v2hOriginalStrokeStepTrace;
  const proto=root.CanvasRenderingContext2D.prototype;
  function encodeBytes(bytes) {
    if (!(bytes instanceof root.Uint8ClampedArray) ||
        bytes.length!==ROI.width*ROI.height*4) {
      throw new Error("BLOCKED_BPRED_S3V2Q_INVALID_GETIMAGEDATA_BYTES");
    }
    const segments=[];
    for(let offset=0;offset<bytes.length;offset+=8192) {
      const part=bytes.subarray(offset,Math.min(offset+8192,bytes.length));
      let binary="";
      for(let i=0;i<part.length;i++) binary+=String.fromCharCode(part[i]);
      segments.push(binary);
    }
    return root.btoa(segments.join(""));
  }
  function sample(c) {
    return encodeBytes(c.getImageData(ROI.x,ROI.y,ROI.width,ROI.height).data);
  }
  root.AutoDrawBPRED_S3v2qLastIncremental=null;
  root.AutoDrawBPRED_S3v2hOriginalStrokeStepTrace=function(strokes) {
    if (!Array.isArray(strokes) || (strokes.length!==1 && strokes.length!==2)) {
      throw new Error("BLOCKED_BPRED_S3V2Q_UNFROZEN_STROKE_COUNT");
    }
    const original=proto.stroke;
    const events=[];
    root.AutoDrawBPRED_S3v2qLastIncremental=null;
    proto.stroke=function() {
      const canvas=this.canvas;
      const isMain=!!canvas&&canvas.width===1392&&canvas.height===732;
      if (!isMain) return original.apply(this,arguments);
      if (ROI.x+ROI.width>canvas.width||ROI.y+ROI.height>canvas.height) {
        throw new Error("BLOCKED_BPRED_S3V2Q_ROI_OUT_OF_BOUNDS");
      }
      if(events.length>=32) {
        throw new Error("BLOCKED_BPRED_S3V2Q_TOO_MANY_REAL_MAIN_STROKES");
      }
      const t=this.getTransform();
      const event={
        schema:SCHEMA,
        ordinal:events.length+1,
        canvasSize:[canvas.width,canvas.height],
        roi:{x:ROI.x,y:ROI.y,width:ROI.width,height:ROI.height},
        originalContext:{
          globalAlpha:this.globalAlpha,
          globalCompositeOperation:this.globalCompositeOperation,
          lineWidth:this.lineWidth,
          lineCap:this.lineCap,
          lineJoin:this.lineJoin,
          transform:[t.a,t.b,t.c,t.d,t.e,t.f]
        },
        pre_rgba_b64:sample(this)
      };
      // Exactly the one original stroke, with unchanged arguments/receiver.
      const result=original.apply(this,arguments);
      event.post_rgba_b64=sample(this);
      // Read-only consecutive repeat: no drawing between reads.
      event.repeat_post_rgba_b64=sample(this);
      events.push(event);
      return result;
    };
    let result;
    try {
      result=originalTrace(strokes);
    } finally {
      proto.stroke=original;
    }
    if (!result ||
        result.schema!=="ENGINE001_BPRED_S3V2H_ORIGINAL_CANVAS_STROKE_STEP_TRACE" ||
        result.originalStrokeMethodRestored!==true ||
        proto.stroke!==original ||
        result.trueMainStrokeCalls!==events.length ||
        !events.length || events.length>32) {
      throw new Error("BLOCKED_BPRED_S3V2Q_TRUE_STROKE_OR_RESTORATION_DRIFT");
    }
    root.AutoDrawBPRED_S3v2qLastIncremental={
      schema:SCHEMA,
      originalTraceRestored:true,
      originalMainCount:events.length,
      events:events
    };
    return result;
  };
  root.AutoDrawBPRED_S3v2qObserverInstalled=true;
})(window);

/* ENGINE-001/BPRED-S3v2r research-only: 1 or 9 original Egret strokes.
 * Original frozen S3v2c/d/h wrappers deliberately allow only 1 or 2.
 * This wrapper observes the original renderer itself; it does NOT recreate
 * brush physics or alter the engine/mask/texture/other game paths.
 */
(function(root) {
  "use strict";
  const ROI=Object.freeze({x:400,y:220,width:270,height:270});
  const SCHEMA="ENGINE001_BPRED_S3V2R_ORIGINAL_NATIVE_REPEAT_CONTRAST_V1";
  if(root.AutoDrawBPRED_S3v2rObserverInstalled===true ||
     !root.egret || typeof root.egret.CanvasRenderer!=="function" ||
     !root.AutoDrawGameRendererReference ||
     typeof root.AutoDrawGameRendererReference.renderP4A2BrushWidths1to10Probe!=="function" ||
     !root.CanvasRenderingContext2D ||
     typeof root.CanvasRenderingContext2D.prototype.stroke!=="function") {
    throw new Error("BLOCKED_BPRED_S3V2R_NATIVE_CONTEXT_MISSING");
  }
  function encode(data) {
    if (!(data instanceof root.Uint8ClampedArray) ||
        data.length!==270*270*4) throw new Error("BLOCKED_BPRED_S3V2R_INVALID_RAW_BYTES");
    const chunks=[];
    for(let i=0;i<data.length;i+=8192) {
      const piece=data.subarray(i,Math.min(data.length,i+8192));
      let str="";
      for(let n=0;n<piece.length;n++) str+=String.fromCharCode(piece[n]);
      chunks.push(str);
    }
    return root.btoa(chunks.join(""));
  }
  const sample=function(ctx) {
    return encode(ctx.getImageData(ROI.x,ROI.y,ROI.width,ROI.height).data);
  };
  root.AutoDrawBPRED_S3v2rOriginalNativeSequence=function(strokes) {
    if(!Array.isArray(strokes) || ![1,2,9].includes(strokes.length) ||
       strokes.some(s=>!s || !Number.isInteger(s.width)||![3,7,10].includes(s.width) ||
            !Array.isArray(s.points)||s.points.length!==2)) {
      throw new Error("BLOCKED_BPRED_S3V2R_UNFROZEN_STROKE_PLAN");
    }
    const proto=root.CanvasRenderingContext2D.prototype;
    const renderProto=root.egret.CanvasRenderer.prototype;
    const stroke=proto.stroke;
    const render=renderProto.renderGraphics;
    const events=[];
    const captures=[];
    proto.stroke=function() {
      const canvas=this.canvas;
      if(!canvas||canvas.width!==1392||canvas.height!==732) {
        return stroke.apply(this,arguments);
      }
      if(events.length>=16||ROI.x+ROI.width>canvas.width||
            ROI.y+ROI.height>canvas.height) {
        throw new Error("BLOCKED_BPRED_S3V2R_ORIGINAL_NATIVE_ROI_OR_COUNT_DRIFT");
      }
      const t=this.getTransform();
      const ctx={
        lineWidth:this.lineWidth,lineCap:this.lineCap,lineJoin:this.lineJoin,
        globalAlpha:this.globalAlpha,globalCompositeOperation:this.globalCompositeOperation,
        transform:[t.a,t.b,t.c,t.d,t.e,t.f]
      };
      const pre=sample(this);
      const result=stroke.apply(this,arguments);
      const post=sample(this);
      events.push({
        step:events.length+1,originalContext:ctx,
        preRGBA_b64:pre,postRGBA_b64:post,
        actualCanvasPngDataUrl:canvas.toDataURL("image/png")
      });
      return result;
    };
    renderProto.renderGraphics=function(node,ctx,forHitTest) {
      const ret=render.call(this,node,ctx,forHitTest);
      if(node && Array.isArray(node.drawData) && node.drawData.length>0 && !forHitTest) {
        if(!ctx||!ctx.canvas||typeof ctx.canvas.toDataURL!=="function") {
          throw new Error("BLOCKED_BPRED_S3V2R_NOT_ORIGINAL_GRAPHICS");
        }
        const t=ctx.getTransform();
        captures.push({
          node:{x:node.x,y:node.y,width:node.width,height:node.height},
          drawDataCount:node.drawData.length,
          size:[ctx.canvas.width,ctx.canvas.height],
          transform:[t.a,t.b,t.c,t.d,t.e,t.f],
          nativeCanvasPngDataUrl:ctx.canvas.toDataURL("image/png")
        });
      }
      return ret;
    };
    let native;
    try {
      native=root.AutoDrawGameRendererReference
        .renderP4A2BrushWidths1to10Probe(strokes);
    } finally {
      renderProto.renderGraphics=render;
      proto.stroke=stroke;
    }
    if(renderProto.renderGraphics!==render||proto.stroke!==stroke||
      !native ||native.schema!=="ENGINE001_B1R_P4A2_NATIVE_1_TO_10"||
      native.renderer!=="real Egret 5.4.1 BoardPane/WebGLRenderer"||
      native.strokeCount!==strokes.length||
      native.syntheticAcceptedVerticesNotChalk!==2*strokes.length||
      events.length!==strokes.length||captures.length!==2) {
      throw new Error("BLOCKED_BPRED_S3V2R_RESTORE_OR_ORIGINAL_STROKE_PROVENANCE");
    }
    function match(c,node,count,size,transform) {
      return c && c.node && c.node.x===node[0]&&c.node.y===node[1]&&
        c.node.width===node[2]&&c.node.height===node[3]&&
        c.drawDataCount===count&&JSON.stringify(c.size)===JSON.stringify(size)&&
        JSON.stringify(c.transform)===JSON.stringify(transform);
    }
    const main=captures.filter(c=>match(c,[-2,-2,464,244],2+strokes.length,[1392,732],[3,0,0,3,6,6]));
    const mask=captures.filter(c=>match(c,[0,0,460,240],1,[1380,720],[3,0,0,3,0,0]));
    if(main.length!==1||mask.length!==1||main[0]===mask[0]) {
      throw new Error("BLOCKED_BPRED_S3V2R_NATIVE_MAIN_MASK_SELECTION");
    }
    return {
      schema:SCHEMA,strokes:strokes.length,originalMethodsRestored:true,
      main:main[0],mask:mask[0],events:events,native:native,
      roi:{x:ROI.x,y:ROI.y,width:ROI.width,height:ROI.height}
    };
  };
  root.AutoDrawBPRED_S3v2rObserverInstalled=true;
})(window);

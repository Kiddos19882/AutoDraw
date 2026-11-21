/* AutoDraw SEMREF1 research-only independent human review helpers.
   No source rewriting, pretrained predictions, network, or stroke admission. */
(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.SEMREF1Core = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const COLORS = [
    [0, 0, 0], [255, 0, 255], [0, 255, 255],
    [0, 255, 0], [255, 255, 0]
  ];
  function checkedDimensions(w, h) {
    if (!Number.isInteger(w) || !Number.isInteger(h) ||
        w < 1 || h < 1 || w * h > 16000000)
      throw new Error("BLOCKED_SEMREF1_INVALID_SOURCE_SIZE");
  }
  function emptyLabels(w, h) {
    checkedDimensions(w, h);
    return new Uint8Array(w * h);
  }
  function stamp(mask, w, h, x, y, radius, category) {
    checkedDimensions(w, h);
    if (!(mask instanceof Uint8Array) || mask.length !== w * h ||
        !Number.isInteger(category) || category < 0 || category > 4 ||
        !Number.isFinite(x) || !Number.isFinite(y) ||
        !Number.isInteger(radius) || radius < 1 || radius > 50)
      throw new Error("BLOCKED_SEMREF1_INVALID_ANNOTATION");
    const cx = Math.floor(x), cy = Math.floor(y);
    const rr = radius * radius;
    for (let py = Math.max(0, cy - radius); py <= Math.min(h - 1, cy + radius); py++) {
      for (let px = Math.max(0, cx - radius); px <= Math.min(w - 1, cx + radius); px++) {
        if ((px - cx) ** 2 + (py - cy) ** 2 <= rr) mask[py * w + px] = category;
      }
    }
  }
  function segment(mask, w, h, start, end, radius, category) {
    if (![start.x, start.y, end.x, end.y].every(Number.isFinite))
      throw new Error("BLOCKED_SEMREF1_INVALID_POINTER");
    const n = Math.ceil(Math.max(Math.abs(end.x - start.x), Math.abs(end.y - start.y)));
    if (n > 16000000) throw new Error("BLOCKED_SEMREF1_SEGMENT_EXCESSIVE");
    for (let step = 0; step <= n; step++) {
      const t = n ? step / n : 0;
      stamp(mask, w, h, start.x + (end.x - start.x) * t,
            start.y + (end.y - start.y) * t, radius, category);
    }
  }
  function previewRGBA(mask) {
    if (!(mask instanceof Uint8Array)) throw new Error("INVALID_MASK");
    const rgba = new Uint8ClampedArray(mask.length * 4);
    for (let i = 0; i < mask.length; i++) {
      const k = mask[i];
      if (k > 4) throw new Error("INVALID_LABEL_VALUE");
      if (k) {
        rgba[i * 4] = COLORS[k][0];
        rgba[i * 4 + 1] = COLORS[k][1];
        rgba[i * 4 + 2] = COLORS[k][2];
        rgba[i * 4 + 3] = 150;
      }
    }
    return rgba;
  }
  function counts(mask) {
    const out = [0, 0, 0, 0, 0];
    for (const v of mask) {
      if (v > 4) throw new Error("BLOCKED_SEMREF1_INVALID_LABEL_VALUE");
      out[v]++;
    }
    return out;
  }
  function crc32(bytes) {
    let value = 0xffffffff;
    for (const b of bytes) {
      value ^= b;
      for (let i = 0; i < 8; i++)
        value = (value >>> 1) ^ ((value & 1) ? 0xedb88320 : 0);
    }
    return (value ^ 0xffffffff) >>> 0;
  }
  function chunk(kind, data) {
    if (kind.length !== 4) throw new Error("INVALID_PNG_CHUNK");
    const out = new Uint8Array(12 + data.length);
    new DataView(out.buffer).setUint32(0, data.length, false);
    for (let i = 0; i < 4; i++) out[4 + i] = kind.charCodeAt(i);
    out.set(data, 8);
    new DataView(out.buffer).setUint32(8 + data.length,
        crc32(out.subarray(4, 8 + data.length)), false);
    return out;
  }
  async function rgbPNG(w, h, mask) {
    checkedDimensions(w, h);
    if (!(mask instanceof Uint8Array) || mask.length !== w * h)
      throw new Error("BLOCKED_SEMREF1_PNG_MASK_SHAPE");
    if (typeof CompressionStream === "undefined")
      throw new Error("BLOCKED_SEMREF1_BROWSER_DEFLATE_UNAVAILABLE");
    const rgb = new Uint8Array(h * (1 + w * 3)); // PNG scanline filter 0
    for (let y = 0; y < h; y++) {
      const offset = y * (w * 3 + 1);
      for (let x = 0; x < w; x++) {
        const k = mask[y * w + x];
        if (k > 4) throw new Error("BLOCKED_SEMREF1_INVALID_LABEL_VALUE");
        const c = COLORS[k], pos = offset + 1 + x * 3;
        rgb[pos] = c[0]; rgb[pos + 1] = c[1]; rgb[pos + 2] = c[2];
      }
    }
    // zlib-wrapped deflate stream, PNG IDAT, 8-bit truecolor RGB (NOT RGBA).
    const zipped = new Uint8Array(await new Response(
      new Blob([rgb]).stream().pipeThrough(new CompressionStream("deflate"))
    ).arrayBuffer());
    const ihdr = new Uint8Array(13), view = new DataView(ihdr.buffer);
    view.setUint32(0, w, false); view.setUint32(4, h, false);
    ihdr[8] = 8; ihdr[9] = 2; // RGB/truecolor, no alpha.
    const sig = Uint8Array.from([137,80,78,71,13,10,26,10]);
    return new Blob([sig, chunk("IHDR", ihdr), chunk("IDAT", zipped),
                     chunk("IEND", new Uint8Array(0))], {type:"image/png"});
  }
  async function sha256Hex(data) {
    const crypto = globalThis.crypto;
    if (!crypto || !crypto.subtle)
      throw new Error("BLOCKED_SEMREF1_SECURE_SHA256_UNAVAILABLE");
    const buf = data instanceof Uint8Array ? data : new Uint8Array(data);
    const result = new Uint8Array(await crypto.subtle.digest("SHA-256", buf));
    return Array.from(result, x => x.toString(16).padStart(2, "0")).join("");
  }
  return {COLORS, emptyLabels, stamp, segment, previewRGBA, counts,
          rgbPNG, sha256Hex};
});

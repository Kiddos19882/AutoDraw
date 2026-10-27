/*
AutoDraw Stage 6 — browser frame-rate probe
Run this in the DevTools Console on the visible game tab.
It measures requestAnimationFrame cadence for 10 seconds and prints one JSON object.
It does not modify the game or inspect private game objects.
*/
(async () => {
  const durationMs = 10000;
  const intervals = [];
  const startedAt = performance.now();
  let previousFrame = null;
  let latestFrame = startedAt;

  const sorted = values => [...values].sort((a, b) => a - b);
  const percentile = (values, fraction) => {
    if (!values.length) return null;
    const ordered = sorted(values);
    return ordered[Math.min(ordered.length - 1, Math.ceil(fraction * ordered.length) - 1)];
  };
  const mean = values => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;

  await new Promise(resolve => {
    const onFrame = timestamp => {
      latestFrame = timestamp;
      if (previousFrame !== null) intervals.push(timestamp - previousFrame);
      previousFrame = timestamp;
      if (timestamp - startedAt >= durationMs) resolve();
      else requestAnimationFrame(onFrame);
    };
    requestAnimationFrame(onFrame);
  });

  const averageInterval = mean(intervals);
  const medianInterval = percentile(intervals, 0.5);
  const p95Interval = percentile(intervals, 0.95);
  const longFrameCount = medianInterval
    ? intervals.filter(interval => interval > medianInterval * 1.5).length
    : 0;
  const result = {
    schema_version: 1,
    measured_at: new Date().toISOString(),
    duration_ms: Math.round(latestFrame - startedAt),
    frame_count: intervals.length,
    average_fps: averageInterval ? Number((1000 / averageInterval).toFixed(3)) : null,
    median_fps: medianInterval ? Number((1000 / medianInterval).toFixed(3)) : null,
    median_frame_interval_ms: medianInterval ? Number(medianInterval.toFixed(3)) : null,
    p95_frame_interval_ms: p95Interval ? Number(p95Interval.toFixed(3)) : null,
    long_frame_over_1_5x_median_percent: intervals.length
      ? Number((100 * longFrameCount / intervals.length).toFixed(3))
      : null,
    document_visibility: document.visibilityState,
    device_pixel_ratio: window.devicePixelRatio || 1,
    viewport: { width: window.innerWidth, height: window.innerHeight },
    nominal_game_stage_fps: Number.isFinite(window.Laya?.stage?.frameRate)
      ? window.Laya.stage.frameRate
      : null,
    probe_kind: "requestAnimationFrame_cadence_not_internal_engine_counter"
  };
  console.log("AUTODRAW_FRAME_PROBE_JSON=" + JSON.stringify(result, null, 2));
  return result;
})();

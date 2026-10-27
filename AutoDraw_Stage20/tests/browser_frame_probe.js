/*
AutoDraw Stage 6 — browser frame-rate probe
Run this in the DevTools Console on the visible game tab.
It measures requestAnimationFrame cadence for 10 seconds and prints one JSON object.
It does not modify the game or inspect private game objects.
*/
(async () => {
  const durationMs = 10000;
  const watchdogMs = 30000;
  const maximumFrameGapMs = 1000;
  const minimumIntervals = 30;
  const intervals = [];
  const startedAt = performance.now();
  const wallClockStartedAt = Date.now();
  let previousFrame = null;
  let latestFrame = startedAt;
  let frameHandle = null;
  let watchdogHandle = null;
  let settled = false;

  const sorted = values => [...values].sort((a, b) => a - b);
  const percentile = (values, fraction) => {
    if (!values.length) return null;
    const ordered = sorted(values);
    return ordered[Math.min(ordered.length - 1, Math.ceil(fraction * ordered.length) - 1)];
  };
  const mean = values => values.length
    ? values.reduce((sum, value) => sum + value, 0) / values.length
    : null;

  try {
    if (document.visibilityState !== "visible") {
      throw new Error("Вкладка уже скрыта. Переключитесь на игру и запустите замер повторно.");
    }

    await new Promise((resolve, reject) => {
      const cleanup = () => {
        document.removeEventListener("visibilitychange", onVisibilityChange);
        if (watchdogHandle !== null) clearTimeout(watchdogHandle);
        if (frameHandle !== null) cancelAnimationFrame(frameHandle);
        watchdogHandle = null;
        frameHandle = null;
      };
      const fail = message => {
        if (settled) return;
        settled = true;
        cleanup();
        reject(new Error(message));
      };
      const finish = () => {
        if (settled) return;
        settled = true;
        cleanup();
        resolve();
      };
      const onVisibilityChange = () => {
        fail(
          "Во время замера произошло событие visibilitychange. " +
          "Результат отменён; запустите замер заново на видимой вкладке."
        );
      };
      const onFrame = timestamp => {
        if (settled) return;
        if (document.visibilityState !== "visible") {
          fail("Вкладка скрыта; результат замера недействителен.");
          return;
        }
        if (Date.now() - wallClockStartedAt > watchdogMs) {
          fail("Истёк защитный тайм-аут замера кадров.");
          return;
        }
        if (!Number.isFinite(timestamp)) {
          fail("Браузер вернул некорректную временную метку кадра.");
          return;
        }

        latestFrame = timestamp;
        if (previousFrame !== null) {
          const interval = timestamp - previousFrame;
          if (!Number.isFinite(interval) || interval <= 0) {
            fail("Получен некорректный интервал requestAnimationFrame.");
            return;
          }
          if (interval > maximumFrameGapMs) {
            fail(
              `Пауза между кадрами составила ${interval.toFixed(1)} мс. ` +
              "Вкладка могла быть приостановлена или перегружена; повторите замер."
            );
            return;
          }
          intervals.push(interval);
        }
        previousFrame = timestamp;

        if (timestamp - startedAt >= durationMs) {
          if (intervals.length < minimumIntervals) {
            fail(
              `Получено слишком мало интервалов кадров (${intervals.length}); ` +
              "оставьте игру видимой и повторите замер."
            );
            return;
          }
          finish();
        } else {
          frameHandle = requestAnimationFrame(onFrame);
        }
      };

      document.addEventListener("visibilitychange", onVisibilityChange);
      watchdogHandle = setTimeout(
        () => fail("Защитный тайм-аут сработал: requestAnimationFrame не завершил замер."),
        watchdogMs
      );
      frameHandle = requestAnimationFrame(onFrame);
    });

    const averageInterval = mean(intervals);
    const medianInterval = percentile(intervals, 0.5);
    const p95Interval = percentile(intervals, 0.95);
    const maximumInterval = Math.max(...intervals);
    const longFrameCount = medianInterval
      ? intervals.filter(interval => interval > medianInterval * 1.5).length
      : 0;
    const wallClockElapsed = Date.now() - wallClockStartedAt;

    const result = {
      schema_version: 2,
      probe_status: "completed",
      measured_at: new Date().toISOString(),
      duration_ms: Math.round(latestFrame - startedAt),
      wall_clock_elapsed_ms: wallClockElapsed,
      frame_count: intervals.length,
      average_fps: averageInterval ? Number((1000 / averageInterval).toFixed(3)) : null,
      median_fps: medianInterval ? Number((1000 / medianInterval).toFixed(3)) : null,
      median_frame_interval_ms: medianInterval ? Number(medianInterval.toFixed(3)) : null,
      p95_frame_interval_ms: p95Interval ? Number(p95Interval.toFixed(3)) : null,
      max_frame_interval_ms: Number(maximumInterval.toFixed(3)),
      long_frame_over_1_5x_median_percent: intervals.length
        ? Number((100 * longFrameCount / intervals.length).toFixed(3))
        : null,
      document_visibility: document.visibilityState,
      visibility_change_count: 0,
      visibility_interrupted: false,
      device_pixel_ratio: window.devicePixelRatio || 1,
      viewport: { width: window.innerWidth, height: window.innerHeight },
      nominal_game_stage_fps: Number.isFinite(window.Laya?.stage?.frameRate)
        ? window.Laya.stage.frameRate
        : null,
      probe_kind: "requestAnimationFrame_cadence_not_internal_engine_counter"
    };
    console.log("AUTODRAW_FRAME_PROBE_JSON=" + JSON.stringify(result, null, 2));
    return result;
  } catch (error) {
    console.error(
      "AUTODRAW_FRAME_PROBE_FAILED=" +
      (error instanceof Error ? error.message : String(error))
    );
    return null;
  }
})();

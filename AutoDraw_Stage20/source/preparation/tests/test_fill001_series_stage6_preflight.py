"""No-input preflight for arbitrary signed FILL001 series Stage6 geometry."""
from copy import deepcopy

import pytest

from fill001_series_runner import SeriesBlocked, build_manifest
from fill001_series_handoff import build_series_source_plan
from fill001_series_stage6_preflight import prepare_series_stage6_preflight


def scenario():
    manifest = build_manifest(
        cycles=1, figures_per_cycle=1,
        shapes=["wide_irregular"],methods=["spaced_scanlines"],
        radii=[10],series_id="series-preflight")
    source = build_series_source_plan(manifest,manifest["tasks"][0]["task_id"])
    roi = {"x":400,"y":200,"width":460,"height":240}
    mapping = {
        "status":"validated_preflight_input_transform_not_live_draw",
        "session_id":"sess", "no_fallback":True,
        "screen_roi":roi.copy(),
        "boardpane_mapping_sha256":"a"*64,
        "passive_samples_sha256":"b"*64,
        "board_screen_corners":{"left":400.0,"right":860.0,"top":200.0,"bottom":440.0},
        "client_to_desktop_offset":{"x":50.0,"y":0.0},
    }
    mapped=deepcopy(source)
    mapped["coordinate_system"]="local_canvas_pixels"
    mapped["generation"]["screen_transform"]=mapping
    calibration={
        "x_at_min":900,"x_at_max":1200,"y":175,
        "initial_value":30,"screen_width":1920,"screen_height":1080,
        "confirmed":True,
    }
    gate={
        "session_id":"sess","mapping_sha256":"a"*64,
        "pointCount":1,"remainingPoints":5999,"blank_counter_confirmed":True,
        "exact":True,"currentRadius":30,
    }
    return dict(manifest=manifest,source=source,mapped=mapped,
                mapping=mapping,roi=roi,session_id="sess",calibration=calibration,
                screen_size=(1920,1080),live_exact_gate=lambda:gate,
                foreground_verified=lambda:True)


def test_generic_preflight_accepts_existing_frozen_nonrectangle_plan():
    args=scenario()
    request=prepare_series_stage6_preflight(**args)
    assert request["planned_strokes"]==len(args["source"]["strokes"])
    assert request["task_id"]==args["manifest"]["tasks"][0]["task_id"]
    assert request["expected_brush_radii"]==[10]*request["planned_strokes"]
    assert request["expected_pointer_down_client"][0][0]>=350
    assert request["execution_allowed"] is False
    assert request["exact_chalk"] is None


@pytest.mark.parametrize("damage",[
    lambda a:a["mapped"]["strokes"][0]["points"][0].update(x=999),
    lambda a:a["mapping"].update(no_fallback=False),
    lambda a:a["mapping"].update(session_id="other"),
    lambda a:a.update(foreground_verified=lambda:False),
    lambda a:a.update(live_exact_gate=lambda:{"session_id":"sess","mapping_sha256":"a"*64,"pointCount":20,"remainingPoints":5980,"blank_counter_confirmed":False,"exact":True,"currentRadius":30}),
    lambda a:a["calibration"].update(initial_value=10),
    lambda a:a["mapping"]["board_screen_corners"].update(right=870.0),
    lambda a:a["mapped"]["strokes"][0]["metadata"].update(brush_value="30"),
    lambda a:a["mapping"]["screen_roi"].update(width=123),
    lambda a:a["calibration"].update(y=1200),
])
def test_generic_preflight_rejects_ambiguous_live_inputs(damage):
    args=scenario()
    damage(args)
    with pytest.raises((SeriesBlocked,ValueError)):
        prepare_series_stage6_preflight(**args)

"""Research-only native Egret brush footprint oracle and two-axis overlap planner.

All painter footprints and effective size data come from actual Egret/WebGL RGBA.
Source pixels define colors; no mathematical capsule covers or blocks a stroke.
"""
import math
from collections import Counter

import numpy as np

import run_engine001_s5_wv_full_native as native

PHASES=((.125,.125),(.375,.625),(.625,.375),(.875,.875))
DIRECTIONS=("horizontal","vertical")
EXPECTED_STAMPS=10*len(DIRECTIONS)*len(PHASES)


def native_footprints(driver):
    """80 disjoint true-Egret strokes: every width 1..10, 0/90 deg and 4 phases."""
    strokes=[]
    placements=[]
    for width in range(1,11):
        for d,orientation in enumerate(DIRECTIONS):
            for phase,(fx,fy) in enumerate(PHASES):
                cx=35+42*(width-1)+fx
                cy=18+27*(4*d+phase)+fy
                pts=([{"x":cx-6,"y":cy},{"x":cx+6,"y":cy}]
                    if orientation=="horizontal" else
                    [{"x":cx,"y":cy-6},{"x":cx,"y":cy+6}])
                strokes.append(native.stroke(pts,width,0,len(strokes)))
                placements.append((width,orientation,phase,cx,cy))
    assert len(strokes)==EXPECTED_STAMPS
    rgba=native.render(driver,"measured-native-footprints",strokes)
    assert rgba.shape==(720,1380,4)
    observations=[]
    for width,orientation,phase,cx,cy in placements:
        x=int(round(3*cx)); y=int(round(3*cy))
        # Tile size 42x27 logical prevents footprint contamination.
        roi=rgba[y-36:y+37,x-39:x+40,3]>=128
        assert roi.shape==(73,79)
        # True measured alpha128 at perpendicular and axial centerlines.
        if orientation=="horizontal":
            lateral=roi[:,38:41].any(axis=1)
            axial=roi[35:38,:].any(axis=0)
        else:
            lateral=roi[35:38,:].any(axis=0)
            axial=roi[:,38:41].any(axis=1)
        l=int(np.count_nonzero(lateral))
        a=int(np.count_nonzero(axial))
        if l==0 or a==0:
            raise RuntimeError("No real Egret alpha128 ink for native brush width %d %s phase %d"%(width,orientation,phase))
        observations.append(dict(width=width,orientation=orientation,phase=phase,
            center=[cx,cy],native_alpha128_lateral_backing=l,
            native_alpha128_axial_backing=a))
    measured={}
    for orientation in DIRECTIONS:
        for width in range(1,11):
            group=[x for x in observations if x["width"]==width and x["orientation"]==orientation]
            assert len(group)==len(PHASES)
            measured[orientation+":"+str(width)]=dict(
                lateral_min_backing_px=min(z["native_alpha128_lateral_backing"] for z in group),
                lateral_max_backing_px=max(z["native_alpha128_lateral_backing"] for z in group),
                axial_min_backing_px=min(z["native_alpha128_axial_backing"] for z in group),
                axial_max_backing_px=max(z["native_alpha128_axial_backing"] for z in group))
    w1=measured["horizontal:1"]
    if w1["lateral_min_backing_px"]<2 or w1["axial_min_backing_px"]<20:
        raise RuntimeError("Native Egret width1 footprint invalid/too small")
    return {"renderer":"real Egret 5.4.1 BoardPane/WebGLRenderer",
            "mode":"normal","smooth":False,"alpha_threshold":128,
            "calibration_stroke_logical_length":12,
            "probes":len(strokes),"phases":PHASES,
            "measurements":measured,"observations":observations}


def _pixel_to_board(x,y,g):
    return {"x":g["left"]+g["scale"]*(float(x)+.5),
            "y":g["top"]+g["scale"]*(float(y)+.5)}


def _short(c):
    return native.segment(c["x"],c["y"],.5,0)


def plan_same_color_overlap(target,g,footprints):
    """Every source row, longitudinally overlapped segments, using *native* pitch.

    No lane is skipped because modeled swept capsules seem to cover it.
    Pixel center colors come from fresh original 8-color swatches.
    """
    arr=np.asarray(target)
    if arr.ndim!=3 or arr.shape[2]!=3 or arr.dtype!=np.uint8:
        raise ValueError("Target must be prepared RGB uint8")
    if footprints.get("renderer")!="real Egret 5.4.1 BoardPane/WebGLRenderer":
        raise ValueError("Native footprint proof missing")
    if footprints.get("mode")!="normal" or footprints.get("smooth") is not False:
        raise ValueError("Smoothing or mode mismatch")
    width1=footprints["measurements"]["horizontal:1"]
    real_lateral=width1["lateral_min_backing_px"]/3
    real_axial=width1["axial_min_backing_px"]/3
    pixel_pitch=float(g["scale"])
    if not (0<pixel_pitch<=1) or real_lateral<=0 or real_axial<=0:
        raise ValueError("Unverified scaling or brush footprint")
    # Full source-row coverage. If projected pixel pitch is wider than
    # 80% of real native footprint, add subrow passes without dropping rows.
    subrows=max(1,math.ceil(pixel_pitch/(.80*real_lateral)))
    # A complete short stroke is a real native measured 12-logical-px sample;
    # split longer runs with 25% centerline *axial* overlap and an 80%-native
    # alpha128 span bound. This is not a mathematical brush-width assumption.
    chunk=max(3,math.ceil(12/pixel_pitch)+1)
    advance=max(1,min(math.floor(.75*(chunk-1)),
                      math.floor(.80*real_axial/pixel_pitch)))
    steps=Counter()
    grouped={}
    for y in range(arr.shape[0]):
        row=arr[y]
        x=0
        while x<len(row):
            end=x+1
            while end<len(row) and np.array_equal(row[end],row[x]):
                end+=1
            rgb=row[x]
            if np.any(rgb!=255):
                color=int.from_bytes(bytes(rgb),"big")
                for j in range(subrows):
                    # Center + subpixel lateral offsets as needed. No geometry
                    # is discarded as mathematically already covered.
                    shift=(j-(subrows-1)/2)*pixel_pitch/subrows
                    start=x
                    while start<end:
                        stop=min(end,start+chunk)
                        if stop-start==1:
                            c=_pixel_to_board(start,y,g)
                            c["y"]+=shift
                            pts=_short(c)
                            steps["short"]+=1
                        else:
                            pts=[_pixel_to_board(start,y,g),_pixel_to_board(stop-1,y,g)]
                            pts[0]["y"]+=shift
                            pts[1]["y"]+=shift
                            steps["long"]+=1
                        grouped.setdefault(color,[]).append(native.stroke(pts,1,color,
                            sum(steps[k] for k in ("short","long"))))
                        if stop==end:
                            break
                        nxt=min(stop-1,start+advance)
                        if nxt<=start:
                            raise RuntimeError("Non-progressing axial overlap")
                        steps["longitudinal_repeated_source_cells"]+=stop-nxt
                        steps["longitudinal_transitions"]+=1
                        start=nxt
                    steps["lateral_row_runs"]+=1
            x=end
    # Paint lighter colors first so dark details are drawn last, never draw
    # the white game swatch over fine nonwhite regions in this A/B.
    colors=sorted(grouped,key=lambda c:-(2126*((c>>16)&255)+7152*((c>>8)&255)+722*(c&255)))
    paths=[]
    for color in colors:
        paths.extend(grouped[color])
    # Native brush alpha128 min span and source grid imply lateral overlap.
    steps["source_same_color_neighbor_pairs"]=int(np.count_nonzero(
        np.all(arr[:-1]==arr[1:],axis=2)&np.any(arr[:-1]!=255,axis=2)))
    measurements=dict(native_width=1,real_lateral_min_backing=width1["lateral_min_backing_px"],
        real_axial_min_backing=width1["axial_min_backing_px"],
        source_row_pitch_logical=pixel_pitch,
        measured_lateral_pitch_limit_logical=.80*real_lateral,
        actual_lateral_pitch_logical=pixel_pitch/subrows,
        measured_axial_pitch_limit_logical=.80*real_axial,
        actual_segment_advance_logical=advance*pixel_pitch,
        source_chunk_length=chunk,source_segment_advance=advance,
        lateral_passes_per_row=subrows,
        confirmed_cross_track_overlap=(pixel_pitch/subrows<real_lateral),
        confirmed_axial_centerline_overlap=(advance<chunk-1),
        same_color_repainting_allowed=True,
        all_source_runs_included=True,white_game_swatches_drawn=False)
    if not measurements["confirmed_cross_track_overlap"] or not measurements["confirmed_axial_centerline_overlap"]:
        raise RuntimeError("Actual Egret measured two-axis overlap not established")
    return paths,dict(parameters=measurements,counts=dict(steps),colors=len(colors),
                      strokes=len(paths))

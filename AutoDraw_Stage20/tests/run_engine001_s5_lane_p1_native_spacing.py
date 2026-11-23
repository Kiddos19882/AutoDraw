#!/usr/bin/env python3
"""S5-LANE-P1: pinned Egret normal-mode adjacent strokes, native E3 only."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np

import run_engine001_b1r_p4d3_native_brush_repeatability as p4d3
import run_engine001_b1r_p4b7_native_stroke_attribution as p4b7
import run_engine001_b1r_p4b1_hybrid_zone_coverage as p4b1
from run_engine001_complex_holdout_v5 import read_webgl_result

EXPERIMENT = 'ENGINE001_S5_LANE_P1_NATIVE_ADJACENT_STROKE_SPACING_V1'
PREREG = 'ENGINE001_S5_ADJACENT_LANE_NATIVE_SPACING_PREREG_2026-11-23.md'
WIDTHS = tuple(range(1, 11))
ANGLES = (0, 45, 90)
RATIOS = (0.75, 0.90, 1.00)
PHASES = ((0.25, 0.375), (0.50, 0.625))
SHAPE = (720, 1380, 4)
CMD = 'return window.AutoDrawGameRendererReference.renderP4A2BrushWidths1to10Probe(arguments[0]);'


def case_key(width, angle, ratio_index, phase_index):
    return f'W{width:02d}_A{angle:03d}_R{ratio_index}_P{phase_index}'


def make_plan(width, angle, ratio_index, phase_index):
    if width not in WIDTHS or angle not in ANGLES or not 0 <= ratio_index < 3 or not 0 <= phase_index < 2:
        raise ValueError('BLOCKED_LANE_UNREGISTERED_CASE')
    distance = width * RATIOS[ratio_index]
    ux, uy = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    nx, ny = -uy, ux
    phase = PHASES[phase_index]
    cx, cy = 230 + phase[0], 120 + phase[1]
    ac = (cx - nx * distance / 2, cy - ny * distance / 2)
    bc = (cx + nx * distance / 2, cy + ny * distance / 2)
    a = p4d3.stroke(width, p4d3.two_points(*ac, 34, angle))
    b = p4d3.stroke(width, p4d3.two_points(*bc, 34, angle))
    a['strokeId'] = 'icon-0'
    b['strokeId'] = 'icon-1'
    return a, b, {'gap_distance_logical': distance, 'phase_xy': phase,
                  'normal': (nx, ny), 'axial': (ux, uy), 'center_a': ac,
                  'center_b': bc, 'ratio': RATIOS[ratio_index]}


def gap_metrics(rgba, geom):
    if rgba.shape != SHAPE or rgba.dtype != np.uint8:
        raise ValueError('BLOCKED_LANE_INVALID_NATIVE_RGBA')
    ac = geom['center_a']
    nx, ny = geom['normal']
    ux, uy = geom['axial']
    d = geom['gap_distance_logical']
    x0, y0 = 190 * 3, 80 * 3
    patch = rgba[y0:y0 + 240, x0:x0 + 240, 3]
    yy, xx = np.indices(patch.shape)
    xx = (xx + x0 + 0.5) / 3 - ac[0]
    yy = (yy + y0 + 0.5) / 3 - ac[1]
    axial = xx * ux + yy * uy
    lateral = xx * nx + yy * ny
    between = (np.abs(axial) < 10) & (lateral >= 0) & (lateral <= d)
    count = int(between.sum())
    if not count:
        raise ValueError('BLOCKED_LANE_EMPTY_BETWEEN_GRID')
    out = {}
    for threshold in (24, 128):
        misses = between & (patch < threshold)
        counts = []
        for bin_i in range(-10, 10):
            slab = between & (axial >= bin_i) & (axial < bin_i + 1)
            if slab.any():
                counts.append(float((slab & (patch < threshold)).sum() / slab.sum()))
        out[f'alpha{threshold}'] = {
            'between_backing_pixels': count,
            'hole_pixels': int(misses.sum()),
            'hole_fraction': round(float(misses.sum() / count), 9),
            'max_axial_bin_hole_fraction': round(max(counts, default=0), 9),
            'gap_free': not np.any(misses)}
    return out


def capture(driver, folder, stem, strokes):
    response = driver.execute_script(CMD, strokes)
    rgba, meta = read_webgl_result(response, folder, stem)
    if (rgba.shape != SHAPE
            or meta.get('renderer') != 'real Egret 5.4.1 BoardPane/WebGLRenderer'
            or meta.get('mode') != 'normal'
            or meta.get('schema') != 'ENGINE001_B1R_P4A2_NATIVE_1_TO_10'
            or meta.get('strokeCount') != len(strokes)):
        raise ValueError('BLOCKED_LANE_NOT_REAL_NORMAL_EGRET')
    return rgba, meta


def run(workspace, engine, renderer, output):
    if output.exists():
        raise ValueError('BLOCKED_LANE_OUTPUT_EXISTS')
    if p4b1.git_blob(engine.read_bytes()) != p4d3.ENGINE_GIT_BLOB:
        raise ValueError('BLOCKED_LANE_ENGINE_SHA_DRIFT')
    if p4b1.git_blob(renderer.read_bytes()) != p4d3.RENDERER_GIT_BLOB:
        raise ValueError('BLOCKED_LANE_RENDERER_SHA_DRIFT')
    if EXPERIMENT not in (workspace / 'AutoDraw_Stage20' / 'docs' / PREREG).read_text('utf8'):
        raise ValueError('BLOCKED_LANE_PREREG_MISSING')
    output.mkdir(parents=True)
    cases = []
    with p4b7.native_egret_session(workspace) as driver:
        driver.set_script_timeout(180)
        blank = driver.execute_script(CMD, [])
        blank_rgba, blank_meta = read_webgl_result(blank, output, '00_NATIVE_BLANK')
        if (blank_rgba.shape != SHAPE
                or blank_meta.get('schema') != 'ENGINE001_B1R_P4A2_BLANK_WEBGL'
                or np.any(blank_rgba[:, :, 3])):
            raise ValueError('BLOCKED_LANE_NATIVE_BLANK')
        with (output / 'CASES_APPEND_ONLY.jsonl').open('a', encoding='utf8') as ledger:
            for width in WIDTHS:
                for angle in ANGLES:
                    for ri in range(len(RATIOS)):
                        for pi in range(len(PHASES)):
                            key = case_key(width, angle, ri, pi)
                            folder = output / 'cases' / f'W{width:02d}'
                            folder.mkdir(parents=True, exist_ok=True)
                            a, b, geom = make_plan(width, angle, ri, pi)
                            (folder / (key + '_PLAN.json')).write_text(
                                json.dumps({'a': a, 'b': b, 'geometry': geom},
                                           allow_nan=False) + '\n', 'utf8')
                            aa, ma = capture(driver, folder, key + '_A', [a])
                            bb, mb = capture(driver, folder, key + '_B', [b])
                            ab, mc = capture(driver, folder, key + '_AB', [a, b])
                            if not np.any(aa[:, :, 3] >= 24) or not np.any(bb[:, :, 3] >= 24):
                                raise ValueError('BLOCKED_LANE_EMPTY_SINGLE_STROKE')
                            metrics = gap_metrics(ab, geom)
                            overlap = (aa[:, :, 3] > 0) & (bb[:, :, 3] > 0)
                            row = {
                                'id': key, 'width': width, 'angle': angle,
                                'ratio': geom['ratio'], 'phase': list(geom['phase_xy']),
                                'geometry': geom,
                                'alpha_native_overlap_pixels': int(overlap.sum()),
                                'composite_alpha_differs_from_max_single_count': int(
                                    (ab[:, :, 3] != np.maximum(aa[:, :, 3], bb[:, :, 3])).sum()),
                                'metrics': metrics,
                                'native_sha256': {
                                    name: metadata['source_sha256']
                                    for name, metadata in [('A', ma), ('B', mb), ('AB', mc)]}}
                            cases.append(row)
                            ledger.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
                            ledger.flush()
                    print('S5_LANE_P1_PROGRESS width', width, 'angle', angle, 'cases', len(cases), flush=True)
    if len(cases) != 180:
        raise ValueError('BLOCKED_LANE_INCOMPLETE_MATRIX')
    files = {str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'report.json'}
    if len([k for k in files if k.endswith('.png')]) != 541:
        raise ValueError('BLOCKED_LANE_MISSING_NATIVE_PNG')
    report = {
        'experiment': EXPERIMENT, 'prereg': PREREG,
        'evidence': 'E3_OFFLINE_PINNED_EGRET',
        'technical_status': 'PASS_COMPLETE_NATIVE_EVIDENCE',
        'source_game_blob': p4d3.ENGINE_GIT_BLOB,
        'renderer_blob': p4d3.RENDERER_GIT_BLOB,
        'branch': 'feature/image-geometry-optimization',
        'github_sha': os.environ.get('GITHUB_SHA', 'LOCAL'),
        'github_run_id': os.environ.get('GITHUB_RUN_ID', 'LOCAL'),
        'widths': list(WIDTHS), 'angles': list(ANGLES), 'ratios': list(RATIOS),
        'phases': [list(p) for p in PHASES], 'cases_count': len(cases),
        'png_count': 541,
        'alpha24_gapfree_cases': sum(c['metrics']['alpha24']['gap_free'] for c in cases),
        'alpha128_gapfree_cases': sum(c['metrics']['alpha128']['gap_free'] for c in cases),
        'by_width': {
            str(w): {
                'alpha24_gapfree': sum(c['metrics']['alpha24']['gap_free']
                                       for c in cases if c['width'] == w),
                'alpha128_gapfree': sum(c['metrics']['alpha128']['gap_free']
                                        for c in cases if c['width'] == w)}
            for w in WIDTHS},
        'cases': cases, 'members_sha256': files,
        'E4_game': 'NOT_RUN', 'CHALK_exact': 'NOT_RUN',
        'production_promotion': False}
    (output / 'report.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n', 'utf8')
    print('S5_LANE_P1_NATIVE_PASS', len(cases),
          report['alpha24_gapfree_cases'], report['alpha128_gapfree_cases'], flush=True)
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--workspace', type=Path, required=True)
    p.add_argument('--engine-js', type=Path, required=True)
    p.add_argument('--renderer', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    run(args.workspace.resolve(), args.engine_js.resolve(),
        args.renderer.resolve(), args.output.resolve())


if __name__ == '__main__':
    main()

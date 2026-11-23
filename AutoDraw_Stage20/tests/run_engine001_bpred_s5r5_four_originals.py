#!/usr/bin/env python3
"""Original-only S5-R5 content-lane E2 versus frozen R3/R4; never native/game."""
from __future__ import annotations
import argparse
import io
import json
import time
from pathlib import Path

import numpy as np

import run_engine001_bpred_s5r3_dev_visual as base
import engine001_bpred_s5r4_offset_lanes as lanes

R3_TOTAL = (9248, 9062, 53300, 15368)
R4_TOTAL = (17823, 23756, 120466, 74318)
R3_NONWHITE = (1814, 5022, 48954, 4693)
R4_NONWHITE = (1541, 6622, 110777, 12458)
MIN_NONWHITE = tuple(max(a, b) for a, b in zip(R3_NONWHITE, R4_NONWHITE))
sha, canonical = base.sha, base.canonical


def owner_diagnostics(plan, arrays):
    game = arrays['game_index']
    ids = arrays['paintable_id']
    source_edge = arrays['source_edge']
    h, w = game.shape
    cover = np.zeros((h, w), bool)
    touched_regions = set()
    for stroke in plan['proposals']:
        model = lanes.source.swept_capsule_pixel_masks(
            stroke['points'], stroke['brush_value'], 1., 1., w, h)
        for x, y in model['potential_cells']:
            if (ids[y, x] != stroke['paintable_id']
                    or int(game[y, x]) != stroke['color_index']
                    or arrays['original_rgba'][y, x, 3] != 255):
                raise ValueError('BLOCKED_S5R5_OWNER_PIXEL')
            cover[y, x] = True
        touched_regions.add(stroke['paintable_id'])
    return {
        'nonwhite6': int(np.count_nonzero(cover & (game != 6))),
        'white6': int(np.count_nonzero(cover & (game == 6))),
        'source_edge_covered': int(np.count_nonzero(cover & source_edge)),
        'source_edge_total': int(source_edge.sum()),
        'regions_touched': len(touched_regions),
        'potential_union': int(cover.sum())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    opts = ap.parse_args()
    root, out = opts.root.resolve(), opts.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    palette, prov = base.palette.read_engine_palette(root/'gameEngine/main.min_653f95bc.js')
    if prov['engine_git_blob_sha1'] != base.dev.ENGINE_BLOB:
        raise ValueError('BLOCKED_S5R5_ENGINE')
    report = {
        'experiment': 'ENGINE001_BPRED_S5R5_CONTENT_STRATIFIED_REGION_LANES_V1',
        'source_original_only': True,
        'frozen_prereg': 'ENGINE001_BPRED_S5R5_CONTENT_STRATIFIED_REGION_LANES_PREREG_2026-11-23.md',
        'engine_blob': base.dev.ENGINE_BLOB,
        'drawing_mode': 'normal', 'smooth': False,
        'native_Egret': 'NOT_RUN', 'exact_game_chalk': 'NOT_RUN',
        'production_promotion': False,
        'web_research_methods': {
            'Euclidean_Distance_Transform': 'APPLIED_R4_reused_EDT_clearance',
            'region_parallel_offset_sweeps': 'APPLIED_R4_reused',
            'greedy_set_cover': 'PARTIAL_incremental_area_priority_with_content_quotas',
            'Boustrophedon_Cellular_Decomposition': 'NOT_IMPLEMENTED',
            'Medial_Axis': 'NOT_IMPLEMENTED',
            'Contour_Parallel': 'NOT_IMPLEMENTED',
            'Spiral_Toolpath': 'NOT_IMPLEMENTED'},
        'sources': []}
    for i, relative in enumerate(base.dev.SOURCES):
        input_bytes = (root/relative).read_bytes()
        rgba = base.original_io.decode_original(input_bytes)['rgba']
        fresh = []
        runtime = []
        first_arrays = None
        for repeat in range(2):
            t = time.perf_counter()
            maps = base.ctr.build_ctr1(rgba, palette)
            manifest, packet = base.s46.export_quarantined(
                input_bytes, rgba, palette, maps, relative, base.dev.ENGINE_BLOB)
            base.s46.verify_quarantined(manifest, packet, input_bytes)
            r3 = base.r3.build_from_verified_s46(manifest, packet, input_bytes)
            r4 = lanes.build_from_verified_s46(manifest, packet, input_bytes)
            r5 = lanes.build_from_verified_s46(
                manifest, packet, input_bytes, allocation='content_s5r5')
            with np.load(io.BytesIO(packet), allow_pickle=False) as z:
                arrays = {k: z[k] for k in (
                    'original_rgba', 'paintable_id', 'game_index',
                    'protected_original_dot', 'source_edge')}
            for candidate in (r3, r4, r5):
                base.verifier.validate_model(candidate, arrays)
                if (candidate['phase_trials']['broad'] > 1400
                        or candidate['phase_trials']['detail'] > 600
                        or candidate['phase_strokes']['broad'] > 80
                        or candidate['phase_strokes']['detail'] > 120):
                    raise ValueError('BLOCKED_S5R5_BUDGET')
            fresh.append((canonical(r3), canonical(r4), canonical(r5), sha(manifest)))
            runtime.append(round(time.perf_counter() - t, 4))
            if i == 0 and repeat == 0:
                first_arrays = arrays
        if fresh[0] != fresh[1]:
            raise ValueError('BLOCKED_S5R5_FRESH_NONDETERMINISM')
        br3, br4, br5, manifest_digest = fresh[0]
        r3, r4, r5 = map(json.loads, (br3, br4, br5))
        if (r3['potential_covered_pixel_count'] != R3_TOTAL[i]
                or r4['potential_covered_pixel_count'] != R4_TOTAL[i]):
            raise ValueError('BLOCKED_S5R5_HISTORICAL_BASELINE_DRIFT')
        diag3 = owner_diagnostics(r3, first_arrays if i == 0 else arrays)
        diag4 = owner_diagnostics(r4, first_arrays if i == 0 else arrays)
        diag5 = owner_diagnostics(r5, first_arrays if i == 0 else arrays)
        if diag3['nonwhite6'] != R3_NONWHITE[i] or diag4['nonwhite6'] != R4_NONWHITE[i]:
            raise ValueError('BLOCKED_S5R5_FROZEN_CONTENT_BASELINE_DRIFT')
        if (diag5['nonwhite6'] != r5['modeled_nonwhite6_covered']
                or diag5['white6'] != r5['modeled_white6_covered']
                or diag5['source_edge_covered'] != r5['modeled_source_edge_covered']):
            raise ValueError('BLOCKED_S5R5_NEW_LEDGER_DRIFT')
        filenames = (f'{i:02d}_R3.json', f'{i:02d}_R4.json', f'{i:02d}_R5.json')
        for name, body in zip(filenames, (br3, br4, br5)):
            (out/name).write_bytes(body)
        row = {
            'source': relative, 'source_sha256': sha(input_bytes),
            'source_packet_meta_sha256': manifest_digest,
            'r3_file': filenames[0], 'r3_sha256': sha(br3),
            'r4_file': filenames[1], 'r4_sha256': sha(br4),
            'r5_file': filenames[2], 'r5_sha256': sha(br5),
            'r3_covered': r3['potential_covered_pixel_count'],
            'r4_covered': r4['potential_covered_pixel_count'],
            'r5_covered': r5['potential_covered_pixel_count'],
            'r5_guaranteed': r5['guaranteed_covered_pixel_count'],
            'r5_protected': r5['protected_dot_potential_covered'],
            'r5_broad_strokes': r5['phase_strokes']['broad'],
            'r5_detail_strokes': r5['phase_strokes']['detail'],
            'r5_evaluations': r5['trials'],
            'r5_multi_lane_regions': r5['regions_with_multiple_accepted_lanes'],
            'r3_diag': diag3, 'r4_diag': diag4, 'r5_diag': diag5,
            'nonwhite_gate': diag5['nonwhite6'] >= MIN_NONWHITE[i],
            'strict_nonwhite_gain_over_r4': diag5['nonwhite6'] > R4_NONWHITE[i],
            'minimum_total_gate': r5['potential_covered_pixel_count'] >= R3_TOTAL[i],
            'protected_gate': r5['protected_dot_potential_covered'] >= 120,
            'deterministic_fresh_rebuilds': 'PASS',
            'processing_seconds': runtime}
        if i == 0:
            row['visual'] = base.visual_report(
                first_arrays, palette, r5,
                out/'00_wV_S5R5_ACTUAL_MODEL_CONTENT_LANES.png')
        report['sources'].append(row)
        print(json.dumps(row, ensure_ascii=False, sort_keys=True), flush=True)
    rows = report['sources']
    report['frozen_content_feasibility'] = (
        'PASS_CONTENT_FEASIBILITY'
        if all(x['nonwhite_gate'] and x['minimum_total_gate'] and x['protected_gate']
               for x in rows)
        and sum(x['strict_nonwhite_gain_over_r4'] for x in rows) >= 2
        else 'FAIL_CONTENT_FEASIBILITY')
    (out/'00_S5R5_RESULTS.json').write_bytes(canonical(report))
    print('S5R5_FROZEN_CONTENT_GATE', report['frozen_content_feasibility'], flush=True)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""S5-R6 full original4x2 source-only cellular coverage; E2, no native/game."""
from __future__ import annotations

import argparse
import gzip
import io
import json
import time
from pathlib import Path

import numpy as np
import run_engine001_bpred_s5r3_dev_visual as original
import engine001_bpred_s5r4_offset_lanes as lanes
import engine001_bpred_s5r6_boustrophedon_cells as cells

sha = original.sha
canonical = original.canonical
FROZEN_R3_TOTAL = (9248, 9062, 53300, 15368)
FROZEN_R4_TOTAL = (17823, 23756, 120466, 74318)
FROZEN_R5_TOTAL = (13858, 23135, 120016, 60992)
FROZEN_R4_NONWHITE = (1541, 6622, 110777, 12458)
FROZEN_R5_NONWHITE = (2726, 7501, 110028, 14877)


def independent_metrics(plan, arrays):
    game = arrays['game_index']
    edge = arrays['source_edge']
    ids = arrays['paintable_id']
    h, w = game.shape
    cover = np.zeros((h, w), bool)
    for stroke in plan['proposals']:
        footprint = cells.source.swept_capsule_pixel_masks(
            stroke['points'], stroke['brush_value'], 1., 1., w, h)
        for x, y in footprint['potential_cells']:
            if ids[y, x] != stroke['paintable_id'] or \
                    game[y, x] != stroke['color_index'] or \
                    arrays['original_rgba'][y, x, 3] != 255:
                raise ValueError('BLOCKED_S5R6_INDEPENDENT_OWNER')
            cover[y, x] = True
    values = {
        'total': int(cover.sum()),
        'white6': int(np.count_nonzero(cover & (game == 6))),
        'nonwhite6': int(np.count_nonzero(cover & (game != 6))),
        'source_edge': int(np.count_nonzero(cover & edge)),
        'protected': int(np.count_nonzero(cover & arrays['protected_original_dot']))}
    if values['total'] != plan['potential_covered_pixel_count'] or \
            values['protected'] != plan['protected_dot_potential_covered']:
        raise ValueError('BLOCKED_S5R6_INDEPENDENT_LEDGER')
    return values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root, out = args.root.resolve(), args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    palette128, meta = original.palette.read_engine_palette(
        root / 'gameEngine/main.min_653f95bc.js')
    if meta['engine_git_blob_sha1'] != original.dev.ENGINE_BLOB:
        raise ValueError('BLOCKED_S5R6_ENGINE')
    report = {
        'schema': 'ENGINE001_BPRED_S5R6_BOUSTROPHEDON_ORIGINAL4X2_E2_V1',
        'experiment': 'ENGINE001_BPRED_S5R6_BOUSTROPHEDON_SWEEP_CELLS_V1',
        'source_original_only': True, 'drawing_mode': 'normal', 'smooth': False,
        'native_Egret': 'NOT_RUN', 'exact_game_chalk': 'NOT_RUN',
        'admissible_for_gameplay': False, 'engine_blob': original.dev.ENGINE_BLOB,
        'frozen_prereg': 'ENGINE001_BPRED_S5R6_CELLULAR_SWEEP_COVERAGE_PREREG_2026-11-23.md',
        'web_method_application': {
            'Boustrophedon': 'APPLIED_explicit_run_overlap_split_merge_cells',
            'Euclidean_Distance_Transform': 'APPLIED_clearance_prefilter',
            'parallel_sweep_lanes': 'APPLIED_intra_cell_multirow',
            'set_cover': 'PARTIAL_positive_model_residual_gain',
            'Medial_Axis': 'NOT_IMPLEMENTED',
            'Contour_Parallel': 'NOT_IMPLEMENTED',
            'Spiral': 'NOT_IMPLEMENTED'},
        'sources': []}
    for index, relative in enumerate(original.dev.SOURCES):
        image_bytes = (root / relative).read_bytes()
        rgba = original.original_io.decode_original(image_bytes)['rgba']
        runs = []
        durations = []
        visual_arrays = None
        for repeat in range(2):
            start_time = time.perf_counter()
            ctr = original.ctr.build_ctr1(rgba, palette128)
            manifest, raw = original.s46.export_quarantined(
                image_bytes, rgba, palette128, ctr, relative,
                original.dev.ENGINE_BLOB)
            original.s46.verify_quarantined(manifest, raw, image_bytes)
            a = original.r3.build_from_verified_s46(manifest, raw, image_bytes)
            b = lanes.build_from_verified_s46(manifest, raw, image_bytes)
            c = lanes.build_from_verified_s46(
                manifest, raw, image_bytes, allocation='content_s5r5')
            d = cells.build_from_verified_s46(manifest, raw, image_bytes)
            with np.load(io.BytesIO(raw), allow_pickle=False) as z:
                arrays = {k: z[k] for k in (
                    'original_rgba', 'paintable_id', 'game_index',
                    'protected_original_dot', 'source_edge')}
            for model in (a, b, c, d):
                original.verifier.validate_model(model, arrays)
                if model['phase_trials']['broad'] > 1400 or \
                        model['phase_trials']['detail'] > 600 or \
                        model['phase_strokes']['broad'] > 80 or \
                        model['phase_strokes']['detail'] > 120:
                    raise ValueError('BLOCKED_S5R6_PHASE_CAP')
            metrics = independent_metrics(d, arrays)
            if (metrics['nonwhite6'] != d['modeled_nonwhite6_covered']
                    or metrics['white6'] != d['modeled_white6_covered']
                    or metrics['source_edge'] != d['modeled_source_edge_covered']):
                raise ValueError('BLOCKED_S5R6_CONTENT_LEDGER')
            runs.append((canonical(a), canonical(b), canonical(c),
                         canonical(d), sha(manifest), metrics))
            durations.append(round(time.perf_counter() - start_time, 4))
            if index == 0 and repeat == 0:
                visual_arrays = arrays
        if runs[0] != runs[1]:
            raise ValueError('BLOCKED_S5R6_FRESH_DOUBLE_BUILD')
        r3_bytes, r4_bytes, r5_bytes, r6_bytes, manifest_sha, metrics = runs[0]
        r3, r4, r5, r6 = map(json.loads, (r3_bytes, r4_bytes, r5_bytes, r6_bytes))
        if (r3['potential_covered_pixel_count'] != FROZEN_R3_TOTAL[index]
                or r4['potential_covered_pixel_count'] != FROZEN_R4_TOTAL[index]
                or r5['potential_covered_pixel_count'] != FROZEN_R5_TOTAL[index]):
            raise ValueError('BLOCKED_S5R6_HISTORICAL_MODEL_DRIFT')
        # Baseline content pins independently stored in old signed E2.
        r4_content = sum(s['modeled_new_potential_cells']
                         for s in r4['proposals'] if s['color_index'] != 6)
        r5_content = sum(s['modeled_new_potential_cells']
                         for s in r5['proposals'] if s['color_index'] != 6)
        if (r4_content != FROZEN_R4_NONWHITE[index]
                or r5_content != FROZEN_R5_NONWHITE[index]):
            raise ValueError('BLOCKED_S5R6_BASELINE_CONTENT_DRIFT')
        # Reconstruct the full actual source-owner graph for independent
        # reproducibility, not just the 60-event summary stored in the plan.
        full_graph = cells.decompose(
            arrays['paintable_id'], arrays['original_rgba'][:, :, 3] == 255)
        if (len(full_graph['cells']) != r6['topology']['cell_count']
                or len(full_graph['edges']) != r6['topology']['edge_count']
                or full_graph['runs'] != r6['topology']['run_count']
                or full_graph['opaque_pixels'] != r6['visible_pixel_count']
                or full_graph['split_events'] != r6['topology']['split_events']
                or full_graph['merge_events'] != r6['topology']['merge_events']):
            raise ValueError('BLOCKED_S5R6_FULL_CELL_GRAPH_DRIFT')
        graph_name = f'{index:02d}_S5R6_FULL_CELLGRAPH.json.gz'
        graph_raw = json.dumps(
            full_graph, ensure_ascii=False, sort_keys=True,
            separators=(',', ':'), allow_nan=False).encode('utf8')
        graph_z = gzip.compress(graph_raw, compresslevel=9, mtime=0)
        (out / graph_name).write_bytes(graph_z)
        names = [f'{index:02d}_{version}.json'
                 for version in ('R3', 'R4', 'R5', 'R6')]
        bytes_all = [r3_bytes, r4_bytes, r5_bytes, r6_bytes]
        for n, raw in zip(names, bytes_all):
            (out / n).write_bytes(raw)
        limit = max(FROZEN_R4_NONWHITE[index], FROZEN_R5_NONWHITE[index])
        row = {
            'source': relative, 'source_sha256': sha(image_bytes),
            'source_packet_meta_sha256': manifest_sha,
            'models': {v: {'file': n, 'sha256': sha(raw)}
                       for v, n, raw in zip(('r3', 'r4', 'r5', 'r6'), names, bytes_all)},
            'r3_covered': FROZEN_R3_TOTAL[index],
            'r4_covered': FROZEN_R4_TOTAL[index],
            'r5_covered': FROZEN_R5_TOTAL[index],
            'r6_covered': r6['potential_covered_pixel_count'],
            'r6_guaranteed': r6['guaranteed_covered_pixel_count'],
            'r6_protected': r6['protected_dot_potential_covered'],
            'r6_trials': r6['trials'],
            'r6_phase_trials': r6['phase_trials'],
            'r6_phase_strokes': r6['phase_strokes'],
            'r6_topology': r6['topology'],
            'topology_full_graph': {
                'file': graph_name,
                'sha256': sha(graph_z),
                'uncompressed_sha256': sha(graph_raw),
                'total_owner_area': full_graph['opaque_pixels'],
                'cells': len(full_graph['cells']),
                'runs': full_graph['runs'],
                'edges': len(full_graph['edges']),
                'events': len(full_graph['events'])},
            'r6_content': metrics,
            'frozen_nonwhite_threshold': limit,
            'nonwhite_all4_gate': metrics['nonwhite6'] >= limit,
            'nonwhite_strict_10percent_gain':
                metrics['nonwhite6'] >= limit * 1.10,
            'minimum_total_gate':
                r6['potential_covered_pixel_count'] >= FROZEN_R3_TOTAL[index],
            'protected120_gate': r6['protected_dot_potential_covered'] >= 120,
            'double_fresh_determinism': 'PASS',
            'build_seconds': durations}
        if index == 0:
            visual = original.visual_report(
                visual_arrays, palette128, r6,
                out / '00_wV_S5R6_ACTUAL_MODEL_CELLULAR_SWEEP.png')
            row['visual'] = visual
        report['sources'].append(row)
        print(json.dumps(row, ensure_ascii=False, sort_keys=True), flush=True)
    values = report['sources']
    pass_gate = (all(x['nonwhite_all4_gate'] and x['minimum_total_gate']
                     and x['protected120_gate'] for x in values)
                 and sum(x['nonwhite_strict_10percent_gain'] for x in values) >= 2)
    report['frozen_cellular_feasibility'] = (
        'PASS_CELLULAR_CONTENT_FEASIBILITY' if pass_gate
        else 'FAIL_CELLULAR_CONTENT_FEASIBILITY')
    (out / '00_S5R6_RESULTS.json').write_bytes(canonical(report))
    print('S5R6_FROZEN_MODEL_FEASIBILITY', report['frozen_cellular_feasibility'],
          flush=True)


if __name__ == '__main__':
    main()

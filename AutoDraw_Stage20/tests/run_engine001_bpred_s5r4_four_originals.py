#!/usr/bin/env python3
"""S5-R4 original-only fresh x2 R3 vs offset lanes; model pixels, not game ink."""
from __future__ import annotations

import argparse
import io
import json
import time
from pathlib import Path

import numpy as np

import run_engine001_bpred_s5r3_dev_visual as previous
import engine001_bpred_s5r4_offset_lanes as r4

sha = previous.sha
canonical = previous.canonical
R3_COVERED = (9248, 9062, 53300, 15368)
R3_PROTECTED = (120, 120, 120, 120)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path,
                   default=Path(__file__).resolve().parents[1])
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    root, out = args.root.resolve(), args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    palette128, engine_info = previous.palette.read_engine_palette(
        root / 'gameEngine/main.min_653f95bc.js')
    if engine_info['engine_git_blob_sha1'] != previous.dev.ENGINE_BLOB:
        raise ValueError('BLOCKED_S5R4_ENGINE_BLOB_MISMATCH')
    report = {
        'schema': 'ENGINE001_BPRED_S5R4_FOUR_ORIGINALS_V1',
        'source_original_only': True, 'drawing_mode': 'normal', 'smooth': False,
        'native_Egret': 'NOT_RUN', 'exact_game_chalk': 'NOT_RUN',
        'admissible_for_gameplay': False, 'engine_blob': previous.dev.ENGINE_BLOB,
        'e0_prereg': 'ENGINE001_BPRED_S5R4_REGION_OFFSET_LANES_PREREG_2026-11-23.md',
        'sources': []}
    for i, relative in enumerate(previous.dev.SOURCES):
        raw_input = (root / relative).read_bytes()
        rgba = previous.original_io.decode_original(raw_input)['rgba']
        pairs = []
        elapsed = []
        first_arrays = None
        for repeat in range(2):
            start_time = time.perf_counter()
            maps = previous.ctr.build_ctr1(rgba, palette128)
            manifest, raw = previous.s46.export_quarantined(
                raw_input, rgba, palette128, maps, relative,
                previous.dev.ENGINE_BLOB)
            previous.s46.verify_quarantined(manifest, raw, raw_input)
            old = previous.r3.build_from_verified_s46(
                manifest, raw, raw_input)
            new = r4.build_from_verified_s46(
                manifest, raw, raw_input)
            with np.load(io.BytesIO(raw), allow_pickle=False) as z:
                arrays = {k: z[k] for k in (
                    'original_rgba', 'paintable_id', 'game_index',
                    'protected_original_dot')}
            previous.verifier.validate_model(old, arrays)
            previous.verifier.validate_model(new, arrays)
            for result in (old, new):
                if (result['phase_trials']['broad'] > 1400
                        or result['phase_trials']['detail'] > 600
                        or result['phase_strokes']['broad'] > 80
                        or result['phase_strokes']['detail'] > 120):
                    raise ValueError('BLOCKED_S5R4_PHASE_BUDGET')
            pairs.append((canonical(old), canonical(new), manifest))
            if repeat == 0 and i == 0:
                first_arrays = arrays
            elapsed.append(round(time.perf_counter()-start_time, 4))
        if pairs[0] != pairs[1]:
            raise ValueError('BLOCKED_S5R4_DOUBLE_FRESH_NONDETERMINISTIC')
        old, new, manifest = pairs[0]
        old_name = f'{i:02d}_S5R3_BASELINE.json'
        new_name = f'{i:02d}_S5R4_OFFSET_LANES.json'
        (out / old_name).write_bytes(old)
        (out / new_name).write_bytes(new)
        a, b = json.loads(old), json.loads(new)
        if a['potential_covered_pixel_count'] != R3_COVERED[i] or                 a['protected_dot_potential_covered'] != R3_PROTECTED[i]:
            raise ValueError('BLOCKED_S5R4_R3_FROZEN_BASELINE_DRIFT')
        row = {
            'source': relative, 'input_sha256': sha(raw_input),
            'source_manifest_sha256': sha(manifest),
            'r3_file': old_name, 'r3_sha256': sha(old),
            'r4_file': new_name, 'r4_sha256': sha(new),
            'visible': b['visible_pixel_count'],
            'r3_covered': a['potential_covered_pixel_count'],
            'r4_covered': b['potential_covered_pixel_count'],
            'r4_guaranteed': b['guaranteed_covered_pixel_count'],
            'r4_residual': b['uncovered_potential_pixel_count'],
            'r4_protected_touched': b['protected_dot_potential_covered'],
            'r4_broad_strokes': b['phase_strokes']['broad'],
            'r4_detail_strokes': b['phase_strokes']['detail'],
            'r4_trials': b['trials'],
            'r4_regions_with_multilane': b['regions_with_multiple_accepted_lanes'],
            'not_worse': b['potential_covered_pixel_count'] >= R3_COVERED[i],
            'strict_gain': b['potential_covered_pixel_count'] > R3_COVERED[i],
            'protected_gate': b['protected_dot_potential_covered'] >= 120,
            'double_fresh_determinism': 'PASS',
            'elapsed_seconds': elapsed}
        if i == 0:
            row['visual'] = previous.visual_report(
                first_arrays, palette128, b,
                out / '00_wV_S5R4_ACTUAL_MODEL_OFFSET_LANES.png')
        report['sources'].append(row)
        print(json.dumps(row, sort_keys=True, ensure_ascii=False), flush=True)
    rows = report['sources']
    ok = all(x['not_worse'] and x['protected_gate'] for x in rows) and         sum(x['strict_gain'] for x in rows) >= 2
    report['frozen_model_feasibility'] = (
        'PASS_RELATIVE_MODEL_FEASIBILITY' if ok
        else 'FAIL_RELATIVE_MODEL_FEASIBILITY')
    (out / '00_S5R4_RESULTS.json').write_bytes(canonical(report))
    print(json.dumps({
        'frozen_model_feasibility': report['frozen_model_feasibility'],
        'originals': len(rows)}, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()

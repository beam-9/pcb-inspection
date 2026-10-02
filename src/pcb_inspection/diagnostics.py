"""Retrospective PCB1 development diagnostics from immutable Run 1 artifacts.

No detector loading, inference, fitting, threshold calibration or PCB2 access.
Tables use raw saved primary scores/maps and the original strict thresholds.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from .data import load_manifest, validate_manifest
from .preprocessing import preprocess_mask
from .provenance import canonical_hash, immutable_json, sha256_file

RUN_ID = '31e0704ff1da6906'


def parse_defect_types(value):
    """Owner CSV comma-separated labels; no dominant class is invented."""
    labels = [part.strip() for part in str(value).split(',')]
    if any(not part or part == 'normal' for part in labels):
        raise ValueError('Nonempty anomaly labels required')
    if len(set(labels)) != len(labels):
        raise ValueError('Repeated defect annotation')
    return labels


def localization_row(mask, anomaly_map, pixel_threshold):
    mask, anomaly_map = np.asarray(mask), np.asarray(anomaly_map)
    if mask.ndim != 2 or mask.shape != anomaly_map.shape or not np.isin(mask, [0, 1]).all():
        raise ValueError('Binary mask and map must share 2D geometry')
    if not mask.any() or not np.isfinite(anomaly_map).all() or not np.isfinite(pixel_threshold):
        raise ValueError('Positive mask and finite map/threshold required')
    mask = mask.astype(bool)
    predicted = anomaly_map > pixel_threshold
    intersection, union = int((mask & predicted).sum()), int((mask | predicted).sum())
    y, x = np.nonzero(mask)
    peak = np.unravel_index(np.argmax(anomaly_map), anomaly_map.shape)
    return {'mask_area_pixels': int(mask.sum()), 'mask_area_fraction': float(mask.mean()),
            'per_image_pixel_ap': float(average_precision_score(mask.ravel(), anomaly_map.ravel())),
            'peak_inside_mask': bool(mask[peak]), 'peak_x': int(peak[1]), 'peak_y': int(peak[0]),
            'peak_tie_count': int(np.count_nonzero(anomaly_map == anomaly_map[peak])),
            'any_overlap_with_mask': bool(intersection), 'intersection_pixels': intersection,
            'union_pixels': union, 'per_image_iou': intersection / union,
            'defect_centroid_x': float(x.mean()), 'defect_centroid_y': float(y.mean()),
            'map_height': mask.shape[0], 'map_width': mask.shape[1]}


def assign_size_quartiles(frame):
    """Higher empirical quartile boundaries; equal areas never split across groups.

    Q1 <= q25, Q2 (q25,q50], Q3 (q50,q75], Q4 > q75. Equal boundaries
    may leave groups empty; all four groups remain in summary tables.
    """
    if frame.empty or not np.isfinite(frame.mask_area_fraction).all():
        raise ValueError('Finite nonempty anomaly sizes required')
    edges = np.quantile(frame.mask_area_fraction, [.25, .5, .75], method='higher')
    result = frame.copy()
    result['size_quartile'] = [f'Q{index+1}' for index in np.searchsorted(edges, result.mask_area_fraction, side='left')]
    return result, edges.tolist()


def strict_roc_table(labels, scores):
    """All distinct achievable strict > operating points, including both endpoints."""
    labels, scores = np.asarray(labels), np.asarray(scores, dtype=float)
    if labels.ndim != 1 or labels.shape != scores.shape or not np.isin(labels, [0, 1]).all() or not np.isfinite(scores).all():
        raise ValueError('Paired finite scores and binary labels required')
    labels = labels.astype(bool)
    positive, negative = int(labels.sum()), int((~labels).sum())
    if not positive or not negative:
        raise ValueError('ROC diagnosis requires both labels')
    unique = np.unique(scores)[::-1]
    thresholds = np.r_[unique, np.nextafter(unique[-1], -np.inf)]
    rows = []
    for threshold in thresholds:
        detected = scores > threshold
        tp, fp = int((detected & labels).sum()), int((detected & ~labels).sum())
        rows.append({'threshold': float(threshold), 'recall': tp/positive, 'realized_fpr': fp/negative,
                     'true_positives': tp, 'false_negatives': positive-tp,
                     'false_positives': fp, 'true_negatives': negative-fp})
    return pd.DataFrame(rows)


def recall_at_fpr(labels, scores, targets=(.01, .02, .05, .1, .2)):
    roc = strict_roc_table(labels, scores)
    rows = []
    for target in targets:
        if not 0 <= target <= 1:
            raise ValueError('FPR budgets must lie in [0,1]')
        eligible = roc.loc[roc.realized_fpr <= target]
        # Best attainable recall within budget. Ties prefer lowest actual FPR,
        # then the highest threshold; tied scores cannot be partially selected.
        best = eligible.sort_values(['recall', 'realized_fpr', 'threshold'], ascending=[False, True, False]).iloc[0]
        row = best.to_dict()
        for key in ('true_positives', 'false_negatives', 'false_positives', 'true_negatives'):
            row[key] = int(row[key])
        rows.append(dict(target_fpr=float(target), **row))
    return pd.DataFrame(rows)


def _group_summary(group, name, value):
    count = len(group)
    return {name: value, 'sample_count': count, 'detected_count': int(group.detected_at_frozen_threshold.sum()),
            'missed_count': int((~group.detected_at_frozen_threshold).sum()),
            'recall': float(group.detected_at_frozen_threshold.mean()) if count else None,
            'mask_area_fraction_min': float(group.mask_area_fraction.min()) if count else None,
            'mask_area_fraction_max': float(group.mask_area_fraction.max()) if count else None,
            'median_image_anomaly_score': float(group.image_anomaly_score.median()) if count else None,
            'median_score_minus_threshold': float(group.score_minus_threshold.median()) if count else None,
            'median_per_image_pixel_ap': float(group.per_image_pixel_ap.median()) if count else None,
            'peak_inside_mask_rate': float(group.peak_inside_mask.mean()) if count else None,
            'overlap_rate': float(group.any_overlap_with_mask.mean()) if count else None}


def type_tables(anomalies):
    long = anomalies.copy()
    long['defect_type'] = long.defect_types.map(json.loads)
    long = long.explode('defect_type', ignore_index=True)
    recalls, aps = [], []
    for label, group in long.groupby('defect_type', sort=True):
        if group.image_id.duplicated().any():
            raise ValueError('Each image must contribute at most once per defect type')
        recalls.append(_group_summary(group, 'defect_type', label))
        values = group.per_image_pixel_ap
        aps.append({'defect_type': label, 'count': len(group), 'median': float(values.median()),
                    'p25': float(values.quantile(.25)), 'p75': float(values.quantile(.75)),
                    'minimum': float(values.min()), 'maximum': float(values.max())})
    return long, pd.DataFrame(recalls), pd.DataFrame(aps)


def normal_distribution(normals):
    rows = []
    for split, group in normals.groupby('split', sort=True):
        scores = group.image_anomaly_score
        rows.append({'split': split, 'count': len(group), 'mean': float(scores.mean()),
                     'median': float(scores.median()), 'standard_deviation': float(scores.std(ddof=1)),
                     'p90': float(scores.quantile(.9)), 'p95': float(scores.quantile(.95)),
                     'p99': float(scores.quantile(.99)), 'fraction_above_frozen_threshold': float(group.above_frozen_threshold.mean())})
    return pd.DataFrame(rows)


def verify_inputs(root, run_id):
    root = Path(root).resolve()
    run = root / 'artifacts/runs' / run_id
    provenance = json.loads((run/'provenance.json').read_text())
    completion = json.loads((run/'final_complete.json').read_text())
    verification = json.loads((run/'verification.json').read_text())
    if any(record.get('run_id') != run_id for record in (provenance, completion, verification)):
        raise ValueError('Run identity mismatch')
    hashes = {}
    def check(relative, expected=None):
        path = (root/relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Unsafe source path')
        actual = sha256_file(path)
        if expected is not None and actual != expected:
            raise ValueError(f'Input hash mismatch: {relative}')
        hashes[str(path.relative_to(root))] = actual
    check('docs/protocol.json', provenance['protocol_sha256'])
    protocol = json.loads((root/'docs/protocol.json').read_text())
    for relative, expected in protocol['frozen_files'].items():
        check(relative, expected)
    for relative, expected in provenance['prerequisites'].items():
        check(relative, expected)
    for relative, expected in completion['files'].items():
        check(str((run/relative).relative_to(root)), expected)
    for name, expected in completion['maps'].items():
        check(str((run/'anomaly_maps'/name).relative_to(root)), expected)
    check(str((run/'final_complete.json').relative_to(root)), verification['completion_sha256'])
    if not verification['passed']:
        raise ValueError('Original independent verification did not pass')
    check(str((run/'split_manifest.csv').relative_to(root)), provenance['manifest_sha256'])
    check(str((run/'provenance.json').relative_to(root)))
    check(str((run/'config.json').relative_to(root)))
    if json.loads((run/'config.json').read_text()) != protocol['config']:
        raise ValueError('Run/config identity mismatch')
    source = json.loads((root/'data/manifests/pcb1_source_reconciliation.json').read_text())
    check('data/raw/pcb1/image_anno.csv', source['owner_annotations_sha256'])
    frame = load_manifest(run/'split_manifest.csv')
    validate_manifest(frame)
    for row in frame.itertuples():
        check('data/raw/'+row.image_path, row.sha256)
        if row.mask_path:
            check('data/raw/'+row.mask_path, row.mask_sha256)
    return frame, hashes


def generate_diagnostics(root, run_id=RUN_ID, output='artifacts/pcb1_a2'):
    root = Path(root).resolve()
    frame, input_hashes = verify_inputs(root, run_id)
    run = root/'artifacts/runs'/run_id
    predictions = pd.read_parquet(run/'predictions.parquet')
    calibration = pd.read_parquet(run/'calibration_predictions.parquet')
    thresholds = json.loads((run/'calibration.json').read_text())['primary']
    if thresholds['comparison'] != '>':
        raise ValueError('Unsupported frozen threshold convention')
    image_threshold, pixel_threshold = thresholds['image_threshold'], thresholds['pixel_threshold']
    if predictions.image_id.duplicated().any() or set(predictions.image_id) != set(frame.loc[frame.split=='test', 'image_id']):
        raise ValueError('Final prediction IDs differ from manifest')
    if set(predictions.run_id) != {run_id} or calibration.image_id.duplicated().any() or set(calibration.image_id) != set(frame.loc[frame.split=='calibration', 'image_id']):
        raise ValueError('Calibration/final membership mismatch')
    annotations = pd.read_csv(root/'data/raw/pcb1/image_anno.csv', keep_default_na=False).set_index('image')
    indexed = frame.set_index('image_id')
    rows = []
    for prediction in predictions.itertuples():
        source = indexed.loc[prediction.image_id]
        if prediction.label != int(source.label == 'anomaly'):
            raise ValueError('Saved prediction label mismatch')
        if not prediction.label:
            continue
        annotation = annotations.loc[source.image_path]
        if annotation['mask'] != source.mask_path:
            raise ValueError('Source mask pairing changed')
        mask = preprocess_mask(root/'data/raw'/source.mask_path)
        anomaly_map = np.load(run/'anomaly_maps'/f'{prediction.image_id}.npy', allow_pickle=False)
        types = parse_defect_types(annotation.label)
        rows.append({'image_id': prediction.image_id, 'run_id': run_id, 'image_path': source.image_path,
                     'mask_path': source.mask_path, 'source_defect_label': annotation.label,
                     'defect_type': annotation.label, 'defect_types': json.dumps(types), 'defect_type_count': len(types),
                     'image_anomaly_score': float(prediction.primary_score), 'frozen_image_threshold': image_threshold,
                     'frozen_pixel_threshold': pixel_threshold, 'score_minus_threshold': float(prediction.primary_score-image_threshold),
                     'detected_at_frozen_threshold': bool(prediction.primary_score > image_threshold),
                     **localization_row(mask, anomaly_map, pixel_threshold)})
    anomalies, size_edges = assign_size_quartiles(pd.DataFrame(rows))
    long, recall_type, pixel_type = type_tables(anomalies)
    normal_rows = []
    for split, table in [('calibration', calibration), ('test', predictions.loc[predictions.label==0])]:
        for row in table.itertuples():
            if indexed.loc[row.image_id, 'label'] != 'normal' or indexed.loc[row.image_id, 'split'] != split:
                raise ValueError('Normal score membership mismatch')
            normal_rows.append({'image_id': row.image_id, 'split': split, 'image_anomaly_score': row.primary_score,
                                'frozen_image_threshold': image_threshold, 'above_frozen_threshold': bool(row.primary_score > image_threshold)})
    normals = pd.DataFrame(normal_rows)
    tables = {'per_anomaly_diagnostics': anomalies, 'per_anomaly_defect_types': long,
              'normal_score_diagnostics': normals, 'recall_by_defect_type': recall_type,
              'recall_by_defect_size_quartile': pd.DataFrame([_group_summary(anomalies.loc[anomalies.size_quartile==quartile], 'size_quartile', quartile) for quartile in ['Q1','Q2','Q3','Q4']]),
              'pixel_ap_by_defect_type': pixel_type, 'normal_score_distribution': normal_distribution(normals),
              'recall_vs_fpr': recall_at_fpr(predictions.label, predictions.primary_score),
              'full_roc_data': strict_roc_table(predictions.label, predictions.primary_score)}
    output_path = root/output
    if not output_path.resolve().is_relative_to(root/'artifacts') or output_path.resolve() == run.resolve():
        raise ValueError('Diagnostics must use a separate artifacts directory')
    output_path.mkdir(parents=True, exist_ok=False)
    for name, table in tables.items():
        table.to_csv(output_path/f'{name}.csv', index=False, float_format='%.17g')
        table.to_parquet(output_path/f'{name}.parquet', index=False)
    code_commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    code_status = subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).splitlines()
    metadata = {'created_utc': datetime.now(timezone.utc).isoformat(), 'run_id': run_id,
                'role': 'Retrospective PCB1 development diagnosis; no inference/refitting or confirmatory claim',
                'code_commit': code_commit, 'code_snapshot_sha256': sha256_file(__file__), 'working_tree_status': code_status,
                'source_hashes': input_hashes, 'source_identity_hash': canonical_hash(input_hashes),
                'outputs': {path.name: sha256_file(path) for path in sorted(output_path.iterdir())},
                'definitions': {'score': 'Saved primary_score; raw unnormalized anomaly map',
                    'threshold': 'Original frozen image/pixel thresholds; strict score > threshold; ties normal',
                    'pixel_geometry': 'Original Run1 256x256 maps and nearest-resized masks; area and centroids at that geometry',
                    'peak_tie': 'First maximum in NumPy C row-major order; peak_tie_count also saved',
                    'centroid': 'Mean positive-pixel indices, x column/y row, zero-based 256x256 coordinates',
                    'defect_types': 'All owner comma-separated labels as JSON; combined source label retained; no dominant class',
                    'type_count': 'Each image once per annotated type; multi-label images contribute to multiple groups, so counts need not sum to100. Scores/localization evaluate union mask, not type-specific masks.',
                    'size_quartiles': 'Higher empirical q25/q50/q75; equal-area ties all assigned lower boundary group; possible empty groups retained',
                    'size_quartile_edges': size_edges,
                    'distribution_quantiles': 'Linear interpolation; standard deviation sample ddof=1',
                    'roc': 'All distinct strict > operating points, plus threshold nextafter(minimum,-inf). At each target select maximum attainable recall within FPR budget; ties prefer lowest FPR then highest threshold. Retrospective diagnostic thresholds only.'},
                'anomaly_images': len(anomalies), 'type_memberships': len(long),
                'multi_label_images': int((anomalies.defect_type_count>1).sum()),
                'type_counts': {str(key): int(value) for key,value in long.defect_type.value_counts().sort_index().items()},
                'frozen_image_threshold': image_threshold, 'frozen_pixel_threshold': pixel_threshold}
    immutable_json(output_path/'diagnostics_metadata.json', metadata)
    return tables


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.')
    parser.add_argument('--run-id', default=RUN_ID)
    parser.add_argument('--output', default='artifacts/pcb1_a2')
    args = parser.parse_args()
    tables = generate_diagnostics(args.root, args.run_id, args.output)
    print(json.dumps({name: len(table) for name, table in tables.items()}, indent=2))


if __name__ == '__main__':
    main()

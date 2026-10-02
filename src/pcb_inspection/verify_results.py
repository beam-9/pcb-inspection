"""Independent arithmetic from immutable saved outputs; never performs inference."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from .guard import digest, write_new, now


def _paired(labels, scores):
    y = np.asarray(labels).ravel()
    s = np.asarray(scores).ravel()
    if not len(y) or y.shape != s.shape or not np.isin(y, [0, 1]).all() or not np.isfinite(s).all():
        raise ValueError('Finite paired binary observations required')
    return y.astype(np.int64), s


def ranked_average_precision(labels, scores):
    """Step-integrated PR area with entire tied-score groups entering together."""
    y, s = _paired(labels, scores)
    positives = int(y.sum())
    if not positives:
        return None
    order = np.argsort(s, kind='stable')[::-1]
    sorted_scores = s[order]
    ends = np.r_[np.flatnonzero(sorted_scores[:-1] != sorted_scores[1:]), len(y)-1]
    cumulative = np.cumsum(y[order], dtype=np.int64)[ends]
    increments = np.diff(np.r_[0, cumulative])
    return float(np.sum(increments * cumulative / (ends+1)) / positives)


def pairwise_auroc(labels, scores):
    """Probability positive outranks negative; ties count one half."""
    y, s = _paired(labels, scores)
    positive, negative = s[y == 1], s[y == 0]
    if not len(positive) or not len(negative):
        return None
    wins = sum(int(np.sum(value > negative)) + 0.5*int(np.sum(value == negative)) for value in positive)
    return float(wins / (len(positive)*len(negative)))


def direct_confusion(labels, scores, threshold):
    y, s = _paired(labels, scores)
    if not np.isfinite(threshold):
        raise ValueError('Finite threshold required')
    result = dict.fromkeys(['tp', 'fp', 'fn', 'tn'], 0)
    for actual, score in zip(y, s):
        result[('tp' if actual else 'fp') if score > threshold else ('fn' if actual else 'tn')] += 1
    p, n = int(y.sum()), int(len(y)-y.sum())
    divide = lambda a, b: float(a/b) if b else None
    return {**result, 'n_images':len(y), 'anomaly_count':p, 'normal_count':n,
            'anomaly_prevalence':p/len(y), 'threshold':float(threshold),
            'precision':divide(result['tp'],result['tp']+result['fp']),
            'recall':divide(result['tp'],p), 'normal_false_alarm_rate':divide(result['fp'],n)}


def _compare(expected, actual, path='metrics'):
    if set(expected) != set(actual):
        raise ValueError(f'{path}: metric keys differ')
    for key, value in actual.items():
        reference = expected[key]
        if reference is None or value is None:
            valid = reference is value
        elif isinstance(value, bool):
            valid = reference == value
        elif isinstance(value, (int, float)):
            valid = np.isclose(reference, value, rtol=1e-10, atol=1e-12)
        else:
            valid = reference == value
        if not valid:
            raise ValueError(f'{path}.{key}: saved {reference!r} differs from recomputed {value!r}')


def independent_patch_trace(features, memory):
    """Double-precision NumPy distances, independent of detector nearest kernel."""
    features, memory = np.asarray(features), np.asarray(memory,dtype=np.float64)
    if features.ndim != 3 or memory.ndim != 2 or features.shape[0] != memory.shape[1]:
        raise ValueError('Trace feature/memory geometry differs')
    query = features.transpose(1,2,0).reshape(-1,features.shape[0]).astype(np.float64)
    distances, indices = [], []
    bank_norm = np.sum(memory*memory,axis=1)
    for start in range(0,len(query),64):
        block=query[start:start+64]
        squared=np.maximum(np.sum(block*block,axis=1)[:,None]+bank_norm[None,:]-2*block@memory.T,0)
        closest=np.argmin(squared,axis=1)
        indices.extend(closest.tolist())
        distances.extend(np.sqrt(squared[np.arange(len(block)),closest]).tolist())
    winner=int(np.argmax(distances))
    return {'score':distances[winner],'row':winner//features.shape[2],
        'column':winner%features.shape[2],'reference_index':indices[winner]}


def verify_run(run, raw_root, expected_test_count=200, publish=True, trace_sample_count=3):
    """Requires final_complete before any final masks or predictions are read."""
    run, raw_root = Path(run), Path(raw_root)
    completion = json.loads((run/'final_complete.json').read_text())
    provenance = json.loads((run/'provenance.json').read_text())
    if completion['run_id'] != provenance['run_id']:
        raise ValueError('Completion/provenance run identities differ')
    required_files = {'predictions.parquet', 'metrics.json', 'runtime.json'}
    if not required_files.issubset(completion['files']):
        raise ValueError('Completion lacks required output identities')
    for name, expected in completion['files'].items():
        candidate = run/name
        if not candidate.resolve().is_relative_to(run.resolve()) or digest(candidate) != expected:
            raise ValueError(f'Final output identity mismatch: {name}')
    manifest_path = run/'split_manifest.csv'
    if digest(manifest_path) != provenance['manifest_sha256']:
        raise ValueError('Saved split manifest differs from provenance')
    # Calibration must retain the identity recorded before final test access.
    calibration_key = next((name for name in provenance['prerequisites'] if name.endswith('/calibration.json')), None)
    if calibration_key is None or digest(run/'calibration.json') != provenance['prerequisites'][calibration_key]:
        raise ValueError('Calibration identity changed')
    frame = pd.read_csv(manifest_path, keep_default_na=False)
    test = frame.loc[frame.split == 'test'].copy()
    predictions = pd.read_parquet(run/'predictions.parquet')
    if len(test) != expected_test_count or len(predictions) != len(test):
        raise ValueError('Final membership count differs')
    if predictions.image_id.duplicated().any() or test.image_id.duplicated().any() or set(predictions.image_id) != set(test.image_id):
        raise ValueError('Final membership IDs differ')
    if set(predictions.run_id) != {completion['run_id']}:
        raise ValueError('Mixed prediction run identities')
    test = test.set_index('image_id').loc[predictions.image_id]
    labels = test.label.map({'normal':0, 'anomaly':1}).to_numpy()
    if not np.array_equal(labels, predictions.label.to_numpy()):
        raise ValueError('Saved labels differ from source manifest')
    fit_ids=set(frame.loc[frame.split=='fit','image_id'])
    for row in predictions.itertuples():
        if row.baseline_reference_id not in fit_ids or row.primary_reference_id not in fit_ids:
            raise ValueError('Saved evidence reference outside fitting membership')
        for coordinate in ['query_patch_row','query_patch_column','reference_patch_row','reference_patch_column']:
            value=getattr(row,coordinate)
            if not np.isfinite(value) or int(value)!=value or not 0<=value<32:
                raise ValueError('Saved evidence patch coordinate outside feature grid')
    thresholds = json.loads((run/'calibration.json').read_text())
    saved = json.loads((run/'metrics.json').read_text())
    recomputed = {}
    for name in ['baseline', 'primary']:
        scores = predictions[f'{name}_score'].to_numpy()
        metrics = direct_confusion(labels, scores, thresholds[name]['image_threshold'])
        metrics.update(average_precision=ranked_average_precision(labels,scores),auroc=pairwise_auroc(labels,scores))
        _compare(saved[name],metrics,name)
        recomputed[name] = metrics
    map_names = {f'{image_id}.npy' for image_id in predictions.image_id}
    if set(completion['maps']) != map_names or {p.name for p in (run/'anomaly_maps').glob('*.npy')} != map_names:
        raise ValueError('Anomaly map membership differs')
    maps, masks = [], []
    for row in test.itertuples():
        name = f'{row.Index}.npy'; map_path = run/'anomaly_maps'/name
        if digest(map_path) != completion['maps'][name]:
            raise ValueError('Anomaly map identity changed')
        anomaly_map = np.load(map_path, allow_pickle=False)
        if anomaly_map.shape != (256,256) or not np.isfinite(anomaly_map).all():
            raise ValueError('Invalid saved map geometry or values')
        score=float(predictions.loc[predictions.image_id==row.Index,'primary_score'].iloc[0])
        if anomaly_map.min() < -1e-6 or anomaly_map.max()>score+max(1e-5,abs(score)*1e-6):
            raise ValueError('Bilinear map violates nonnegative patch-score bound')
        if digest(raw_root/row.image_path) != row.sha256:
            raise ValueError('Raw image identity changed')
        if row.label == 'anomaly':
            mask_path = raw_root/row.mask_path
            if not row.mask_path or digest(mask_path) != row.mask_sha256:
                raise ValueError('Raw abnormal mask identity changed')
            with Image.open(mask_path) as source:
                if source.size != (row.width,row.height):
                    raise ValueError('Source mask geometry differs')
                mask = np.asarray(source.resize((256,256),Image.Resampling.NEAREST)) > 0
        else:
            if row.mask_path:
                raise ValueError('Expected implicit-zero normal mask')
            mask = np.zeros((256,256),dtype=bool)
        maps.append(anomaly_map); masks.append(mask)
    maps, masks = np.asarray(maps), np.asarray(masks)
    flagged = maps > thresholds['primary']['pixel_threshold']
    intersection, union = int(np.count_nonzero(masks & flagged)), int(np.count_nonzero(masks | flagged))
    localization = {'pixel_average_precision':ranked_average_precision(masks,maps),
        'n_images':len(masks),'n_pixels':masks.size,'positive_pixels':int(masks.sum()),
        'includes_normal_images':True,'pixel_threshold':float(thresholds['primary']['pixel_threshold']),
        'intersection_pixels':intersection,'union_pixels':union,'pixel_iou':intersection/union if union else None}
    _compare(saved['localization'],localization,'localization')
    recomputed['localization'] = localization
    traces=[]
    if trace_sample_count:
        import torch
        from .preprocessing import FrozenPatchExtractor, preprocess_image
        model_key=next((name for name in provenance['prerequisites'] if name.endswith('/model.pt')),None)
        if model_key is None or digest(run/'model.pt')!=provenance['prerequisites'][model_key]:
            raise ValueError('Reference model identity changed')
        torch.hub.set_dir(str(raw_root.parent/'cache/hub'))
        model=torch.load(run/'model.pt',map_location='cpu',weights_only=False)['primary']
        extractor=FrozenPatchExtractor()
        # Lexicographic IDs select the sample independently of scores and outcomes.
        for image_id in sorted(predictions.image_id)[:trace_sample_count]:
            source=test.loc[image_id]
            feature=extractor(preprocess_image(raw_root/source.image_path)[None])[0].numpy()
            trace=independent_patch_trace(feature,model.memory.numpy())
            recorded=predictions.loc[predictions.image_id==image_id].iloc[0]
            reference=model.metadata[trace['reference_index']]
            if not np.isclose(trace['score'],recorded.primary_score,rtol=1e-5,atol=1e-5):
                raise ValueError('Independent winning patch score differs')
            if (trace['row'],trace['column'])!=(recorded.query_patch_row,recorded.query_patch_column):
                raise ValueError('Independent winning query patch differs')
            if (reference['image_id'],reference['row'],reference['column'])!=(recorded.primary_reference_id,recorded.reference_patch_row,recorded.reference_patch_column):
                raise ValueError('Independent nearest reference patch differs')
            traces.append({'image_id':image_id,**trace,'reference':reference})
    result = {'verified_utc':now(),'run_id':completion['run_id'],'passed':True,
        'method':'Independent tied-score grouped AP, pairwise image AUROC, direct confusion and independently decoded nearest-resized masks',
        'completion_sha256':digest(run/'final_complete.json'),'metrics':recomputed,
        'evidence_membership_rows_checked':len(predictions),'independent_patch_traces':traces}
    if publish:
        write_new(run/'verification.json',result)
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',required=True); parser.add_argument('--raw-root',default='data/raw')
    args=parser.parse_args()
    print(json.dumps(verify_run(args.run,args.raw_root),indent=2))

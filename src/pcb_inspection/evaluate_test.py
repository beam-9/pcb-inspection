"""One exclusive final benchmark evaluation for the two frozen methods."""
import argparse
import json
import resource
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from .guard import claim_test_access, digest, write_new, now
from .pilot import ROOT, MANIFEST, setup
from .preprocessing import FrozenPatchExtractor, preprocess_image, preprocess_mask
from .evaluation import image_metrics, localization_metrics


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',default='configs/pilot.yaml')
    parser.add_argument('--protocol',default='docs/protocol.json')
    parser.add_argument('--confirm-frozen-protocol',action='store_true',required=True)
    args=parser.parse_args()
    if args.config!='configs/pilot.yaml' or args.protocol!='docs/protocol.json':
        raise ValueError('This bounded pilot supports only the recorded protocol/config')
    config=setup(); protocol=json.loads((ROOT/args.protocol).read_text())
    prepared=json.loads((ROOT/'artifacts/prepared.json').read_text()); run=ROOT/prepared['path']
    provenance=json.loads((run/'provenance.json').read_text())
    if provenance['protocol_sha256']!=digest(ROOT/args.protocol) or prepared['run_id']!=provenance['run_id']:
        raise ValueError('Mixed protocol/run')
    tests=json.loads((ROOT/'artifacts/tests_passed.json').read_text())
    if tests['exit_code']!=0 or tests['protocol_sha256']!=digest(ROOT/args.protocol):
        raise ValueError('Passing tests for frozen protocol required')
    required_names=['calibration.json','model.pt','memory_bank_metadata.json','calibration_predictions.parquet','calibration_maps.npy','pretest_runtime.json']
    expected_keys={str((run/name).relative_to(ROOT)) for name in required_names}
    if set(provenance['prerequisites'])!=expected_keys:
        raise ValueError('Required pretest prerequisites missing')
    pretest=json.loads((run/'pretest_runtime.json').read_text())
    if pretest['process_peak_rss_bytes']>protocol['resource_budget']['maximum_peak_rss_bytes'] or pretest['calibration_median_seconds']>protocol['resource_budget']['median_inference_seconds']:
        raise ValueError('Runtime gate failed')
    prerequisites=dict(provenance['prerequisites'])
    prerequisites['artifacts/tests_passed.json']=digest(ROOT/'artifacts/tests_passed.json')
    # Membership metadata is audited before access; labels/masks are used only after claim.
    frame=pd.read_csv(ROOT/MANIFEST).fillna('')
    from .data import validate_manifest
    validate_manifest(frame)
    memory_tick=time.perf_counter()
    model=torch.load(run/'model.pt',map_location='cpu',weights_only=False)
    cold_memory_load=time.perf_counter()-memory_tick
    test_ids=frame.loc[frame.split=='test','image_id'].tolist()
    for detector in model.values():
        detector.assert_no_test_ids(test_ids)
        if set(detector.image_ids)!=set(frame.loc[frame.split=='fit','image_id']):
            raise ValueError('Memory membership differs from fitting manifest')
    for row in frame.itertuples():
        if digest(ROOT/'data/raw'/row.image_path)!=row.sha256:
            raise ValueError('Raw image identity changed')
        if row.mask_path and hasattr(row,'mask_sha256') and digest(ROOT/'data/raw'/row.mask_path)!=row.mask_sha256:
            raise ValueError('Raw mask identity changed')
    claim_test_access(ROOT,protocol,prepared['run_id'],prerequisites)
    thresholds=json.loads((run/'calibration.json').read_text())
    started=time.perf_counter(); load_tick=time.perf_counter(); extractor=FrozenPatchExtractor()
    cold_load=time.perf_counter()-load_tick
    mapsdir=run/'anomaly_maps'; mapsdir.mkdir(exist_ok=False)
    rows=[]; all_maps=[]; masks=[]; baseline_times=[]; primary_times=[]; total_times=[]
    for i,row in enumerate(frame[frame.split=='test'].itertuples()):
        tick=time.perf_counter(); image=preprocess_image(ROOT/'data/raw'/row.image_path)
        feat=extractor(image[None]); extract_seconds=time.perf_counter()-tick
        b_tick=time.perf_counter(); b=model['baseline'].score(feat); b_seconds=time.perf_counter()-b_tick
        p_tick=time.perf_counter(); p=model['primary'].score(feat); p_seconds=time.perf_counter()-p_tick
        total_seconds=time.perf_counter()-tick
        anomaly_map=p['maps'][0]; mask=(preprocess_mask(ROOT/'data/raw'/row.mask_path) if row.mask_path else np.zeros((256,256),bool))
        np.save(mapsdir/f'{row.image_id}.npy',anomaly_map)
        winner=np.unravel_index(np.argmax(p['patch_distances'][0]),(32,32))
        ref=model['primary'].metadata[int(p['nearest_indices'][0][winner])]
        rows.append({'image_id':row.image_id,'run_id':prepared['run_id'],'label':int(row.label=='anomaly'),
            'baseline_score':float(b['scores'][0]),'primary_score':float(p['scores'][0]),
            'baseline_reference_id':b['reference_ids'][0],
            'query_patch_row':int(winner[0]),'query_patch_column':int(winner[1]),
            'primary_reference_id':ref['image_id'],'reference_patch_row':ref['row'],
            'reference_patch_column':ref['column'],'feature_seconds':extract_seconds,
            'baseline_nn_seconds':b_seconds,'primary_nn_seconds':p_seconds,'total_seconds':total_seconds})
        all_maps.append(anomaly_map); masks.append(mask)
        baseline_times.append(extract_seconds+b_seconds); primary_times.append(extract_seconds+p_seconds);total_times.append(total_seconds)
        if (i+1)%25==0: print(f'Final scored {i+1}/200',flush=True)
    table=pd.DataFrame(rows);table.to_parquet(run/'predictions.parquet',index=False)
    metrics={name:image_metrics(table.label,table[f'{name}_score'],thresholds[name]['image_threshold']) for name in ['baseline','primary']}
    metrics['localization']=localization_metrics(np.asarray(masks),np.asarray(all_maps),thresholds['primary']['pixel_threshold'])
    write_new(run/'metrics.json',metrics)
    latency=lambda x:{'median_seconds':float(np.median(x[1:])), 'p95_seconds':float(np.quantile(x[1:],.95)), 'first_image_seconds':x[0], 'warm_count':len(x)-1}
    runtime={'final_eval_seconds':time.perf_counter()-started,'cold_backbone_load_seconds':cold_load,'cold_reference_load_seconds':cold_memory_load,
             'baseline_including_features':latency(baseline_times),'primary_including_features':latency(primary_times),
             'both_including_shared_features':latency(total_times),
             'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
             'note':'Final eval timing excludes raw hashing/reference load; separate cold reference/backbone load timings recorded. Warm percentiles exclude first image. One feature extraction shared by both methods; no Ollama.'}
    write_new(run/'runtime.json',runtime)
    write_new(run/'final_complete.json',{'completed_utc':now(),'run_id':prepared['run_id'],
        'files':{str(p.relative_to(run)):digest(p) for p in [run/'predictions.parquet',run/'metrics.json',run/'runtime.json']},
        'maps':{p.name:digest(p) for p in sorted(mapsdir.glob('*.npy'))}})
    print(json.dumps(metrics,indent=2),flush=True)


if __name__=='__main__': main()

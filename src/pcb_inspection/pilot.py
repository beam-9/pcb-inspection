"""Freeze protocol, fit normals, calibrate; final test is a separate guarded entrypoint."""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import yaml

from .baseline import FrozenEmbeddingBaseline
from .patchcore import PatchCoreInspired
from .preprocessing import FrozenPatchExtractor, preprocess_image, PREPROCESSING_ID
from .calibration import calibrate
from .environment import report
from .guard import digest, write_new, now, verify_frozen

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = 'data/manifests/pcb1_manifest.csv'
WEIGHT = 'data/cache/hub/checkpoints/resnet18-f37072fd.pth'


def setup():
    config = yaml.safe_load((ROOT/'configs/pilot.yaml').read_text())
    torch.set_num_threads(config['threads'])
    torch.manual_seed(config['seed'])
    torch.hub.set_dir(str(ROOT/'data/cache/hub'))
    return config


def extract_to_disk(extractor, frame, destination, batch_size=8):
    features = np.lib.format.open_memmap(destination, mode='w+', dtype='float32',
                                        shape=(len(frame),384,32,32))
    for start in range(0,len(frame),batch_size):
        rows = frame.iloc[start:start+batch_size]
        batch = torch.stack([preprocess_image(ROOT/'data/raw'/p) for p in rows.image_path])
        features[start:start+len(rows)] = extractor(batch).numpy()
    features.flush()
    return features


def freeze():
    config = setup()
    frame = pd.read_csv(ROOT/MANIFEST).fillna('')
    from .data import validate_manifest
    validate_manifest(frame)
    if not (ROOT/WEIGHT).is_file():
        raise ValueError('Smoke-test and verify pretrained weights before protocol freeze')
    files = ['artifacts/smoke.json','artifacts/environment.json','configs/pilot.yaml', MANIFEST, WEIGHT, 'docs/source_research.md',
             'data/manifests/pcb1_audit.json','data/manifests/pcb1_near_duplicates.json','data/manifests/pcb1_near_duplicate_review.json','data/manifests/pcb1_source_reconciliation.json','data/raw/1cls.csv','data/manifests/source_acquisition.json', 'requirements.lock']
    files += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'src/pcb_inspection').glob('*.py'))]
    files += [str(p.relative_to(ROOT)) for p in sorted((ROOT/'tests').glob('test_*.py'))]
    frozen_files = {p:digest(ROOT/p) for p in files}
    protocol = {
        'frozen_utc':now(), 'category':'pcb1','source_terms_resolved':True,
        'use_scope':'Local noncommercial educational/research; commercial weight rights unverified',
        'split_counts':frame.groupby('split').size().to_dict(),
        'frozen_files':frozen_files, 'config':config,'preprocessing_id':PREPROCESSING_ID,
        'primary':'PatchCore-inspired','baseline':'Frozen GAP L2 nearest fitting normal',
        'primary_metrics':['image_average_precision','image_auroc','pixel_average_precision'],
        'pixel_metric_geometry':'256x256, binary masks nearest; normal masks implicit zeros',
        'experiment_cap':{'hardware_smoke':1,'normal_debug':3,'final_evaluation_per_method':1},
        'unseal_condition':'All tests pass; calibration and memory artifacts hash-verified; no overlap; runtime bounded',
        'resource_budget':{'maximum_peak_rss_bytes':8*1024**3,'median_inference_seconds':10},
        'acquisition_identity':'Physical board IDs unavailable; holdout is benchmark only',
        'decision_policy':'Compare baseline separation, localization, inspectable false alarms, runtime and reference traceability; no test-driven recipe selection',
    }
    write_new(ROOT/'docs/protocol.json',protocol)
    (ROOT/'docs/protocol.md').write_text(
        '# Frozen PCB1 Phase A protocol\n\nSee `protocol.json` for timestamp and immutable content identities. '
        'All fitting is on official training normals after seed-42 normal-only calibration separation. '
        'The official final test is preserved. Both recipes and thresholds are fixed before final scoring.\n\n'
        'CPU ResNet18 layer2/layer3 frozen ImageNet features; direct 256-square resize, no crop. '
        'Primary: 4096 seeded uniform normal patches, exact Euclidean nearest neighbor, maximum patch score, '
        'bilinear raw maps without smoothing or normalization. This departs from PatchCore coreset and weighting. '
        'Baseline: global pooling of the same aggregated features, L2 normalization, nearest normal.\n\n'
        'Image threshold: normal calibration 95th percentile, NumPy higher; flag strictly greater. '
        'Pixel overlap threshold: normal calibration map 99th percentile, higher and strictly greater. '
        'Pixel AP pools all 200 test images at 256-square geometry; this may discard small source defects. '
        'No confidence interval claims or factory operating requirements.\n\n'
        'At most three normal implementation runs; one final evaluation each. Bug-correction reruns require '
        'explicit invalidation and ledger record. Final outputs refuse silent overwrite.\n')
    print('Frozen protocol',digest(ROOT/'docs/protocol.json'),flush=True)


def prepare():
    started = time.perf_counter(); config=setup()
    protocol=json.loads((ROOT/'docs/protocol.json').read_text()); verify_frozen(ROOT,protocol)
    run_id=digest(ROOT/'docs/protocol.json')[:16]
    path=ROOT/'artifacts/runs'/run_id
    path.mkdir(parents=True,exist_ok=False)
    write_new(path/'config.json',config); write_new(path/'environment.json',report())
    frame=pd.read_csv(ROOT/MANIFEST).fillna('')
    (path/'split_manifest.csv').write_bytes((ROOT/MANIFEST).read_bytes())
    fit=frame[frame.split=='fit']; calibration=frame[frame.split=='calibration']
    extractor=FrozenPatchExtractor()
    print('Extract fitting normals',len(fit),flush=True)
    features=extract_to_disk(extractor,fit,path/'features.npy')
    baseline=FrozenEmbeddingBaseline().fit(features,fit.image_id.tolist())
    primary=PatchCoreInspired(config['memory_cap'],config['seed']).fit(features,fit.image_id.tolist())
    del features
    print('Calibrate normals',len(calibration),flush=True)
    rows=[]; maps=[]; latencies=[]
    for row in calibration.itertuples():
        tick=time.perf_counter()
        feat=extractor(preprocess_image(ROOT/'data/raw'/row.image_path)[None])
        b=baseline.score(feat); p=primary.score(feat)
        latencies.append(time.perf_counter()-tick)
        maps.append(p['maps'][0]); rows.append({'image_id':row.image_id,'baseline_score':float(b['scores'][0]),'primary_score':float(p['scores'][0])})
    table=pd.DataFrame(rows); table.to_parquet(path/'calibration_predictions.parquet',index=False)
    np.save(path/'calibration_maps.npy',np.asarray(maps))
    thresholds={'baseline':calibrate(table.baseline_score.to_numpy()),
                'primary':calibrate(table.primary_score.to_numpy(),np.asarray(maps))}
    write_new(path/'calibration.json',thresholds)
    torch.save({'baseline':baseline,'primary':primary},path/'model.pt')
    write_new(path/'memory_bank_metadata.json',{'references':primary.metadata,'fit_image_ids':primary.image_ids,
        'memory_shape':list(primary.memory.shape),'memory_bytes':primary.memory.numel()*4,
        'grid_shape':[32,32],'patch_coordinate_meaning':'Feature grid coordinates, not physical component boundaries'})
    import resource
    runtime={'normal_preparation_seconds':time.perf_counter()-started,
        'calibration_median_seconds':float(np.median(latencies)),
        'calibration_p95_seconds':float(np.quantile(latencies,.95)),
        'process_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    if runtime['process_peak_rss_bytes']>protocol['resource_budget']['maximum_peak_rss_bytes'] or runtime['calibration_median_seconds']>protocol['resource_budget']['median_inference_seconds']:
        raise ValueError('Pretest resource gate exceeded; refreeze before test access')
    write_new(path/'pretest_runtime.json',runtime)
    write_new(path/'provenance.json',{'run_id':run_id,'protocol_sha256':digest(ROOT/'docs/protocol.json'),
        'weight_sha256':digest(ROOT/WEIGHT),'manifest_sha256':digest(ROOT/MANIFEST),
        'prerequisites':{str(p.relative_to(ROOT)):digest(p) for p in [path/'calibration.json',path/'model.pt',path/'memory_bank_metadata.json',path/'calibration_predictions.parquet',path/'calibration_maps.npy',path/'pretest_runtime.json']}})
    write_new(ROOT/'artifacts/prepared.json',{'run_id':run_id,'path':str(path.relative_to(ROOT))})
    print('Prepared',run_id,runtime,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['freeze','prepare'])
    args=parser.parse_args(); {'freeze':freeze,'prepare':prepare}[args.action]()

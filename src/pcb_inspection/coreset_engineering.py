"""One full-population normal-only resource pilot before Stage3 recipe freeze."""
import argparse, hashlib, json, resource, time
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from .coreset import gaussian_projection, project_features, select_coreset, ResourceGateError
from .geometry_experiment import DynamicExtractor, tensor_and_transform, setup, MANIFEST, WEIGHT, verify_recipe
from .guard import digest, now, write_new


def run(root):
    root = Path(root).resolve()
    out = root / 'artifacts/stage3_engineering'
    out.mkdir(parents=True, exist_ok=False)
    verify_recipe(root, root / 'artifacts/runs/geometry_512_v1')
    sources = [MANIFEST, WEIGHT, 'src/pcb_inspection/geometry.py',
               'src/pcb_inspection/geometry_experiment.py', 'src/pcb_inspection/preprocessing.py',
               'src/pcb_inspection/coreset.py']
    config = {'input_size':512,'projection_dim':64,'projection_seed':43,
              'selection_seed':42,'initial_count':10,'pilot_selection_count':64,
              'candidate_population':'All patch positions from723 fitting normals; no subsampling',
              'resource_caps':{'peak_rss_bytes':8*1024**3,'total_preparation_seconds':1800},
              'prediction_allowance_seconds':350,
              'normal_only':True,'pcb2_exposed':False}
    write_new(out/'scope.json', {'declared_at_utc':now(), 'config':config,
                                'source_sha256':{p:digest(root/p) for p in sources}})
    setup(root)
    frame = pd.read_csv(root/MANIFEST).fillna('')
    fit = frame[frame.split == 'fit'].reset_index(drop=True)
    projection = gaussian_projection()
    path = out/'projected512.npy'
    cache = np.lib.format.open_memmap(path, mode='w+', dtype='float32',
                                    shape=(len(fit)*64*64,64))
    extractor = DynamicExtractor()
    started = time.perf_counter()
    for start in range(0,len(fit),4):
        rows = list(fit.iloc[start:start+4].itertuples())
        batch = torch.stack([tensor_and_transform(root,row,512)[0] for row in rows])
        feature = extractor(batch).permute(0,2,3,1).reshape(-1,384)
        cache[start*4096:(start+len(rows))*4096] = project_features(feature,projection).numpy()
        if start%80==0: print('normal projection',start,'/',len(fit),flush=True)
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss > 8*1024**3:
            raise ResourceGateError('Normal candidate projection exceeded memory cap')
    cache.flush()
    extraction_seconds = time.perf_counter()-started
    # Float32 mmap stays read-only at the algorithm level; no raw384 fitting bank.
    projected = torch.from_numpy(cache)
    tick = time.perf_counter()
    selected = select_coreset(projected,count=64,deadline_seconds=1800-extraction_seconds)
    selection_seconds = time.perf_counter()-tick
    del projected,cache
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    estimated_full_seconds = extraction_seconds+selection_seconds*64+350
    passed = peak<=8*1024**3 and estimated_full_seconds<=1800
    write_new(out/'engineering.json', {
        'completed_at_utc':now(),'normal_only':True,'pcb2_exposed':False,
        'resource_gate_passed':passed,'config':config,
        'candidate_count':len(fit)*4096,'cache_path':str(path.relative_to(root)),
        'cache_sha256':digest(path),
        'projection_sha256':hashlib.sha256(projection.numpy().tobytes()).hexdigest(),
        'source_sha256':{p:digest(root/p) for p in sources},
        'feature_extraction_seconds':extraction_seconds,
        'pilot_selection_seconds':selection_seconds,'pilot_selected_indices':selected.tolist(),
        'estimated_full_preparation_seconds':estimated_full_seconds,
        'estimate_is_not_measured_full_run':True,'peak_rss_bytes':peak,
        'fit_image_ids_sha256':hashlib.sha256('\n'.join(fit.image_id).encode()).hexdigest()})
    print(json.dumps({'resource_gate_passed':passed,'feature_extraction_seconds':extraction_seconds,
                     'pilot_selection_seconds':selection_seconds,'estimated_full_preparation_seconds':estimated_full_seconds,
                     'peak_rss_bytes':peak}),flush=True)
    if not passed: raise ResourceGateError('Full-population resource pilot not feasible under declared caps')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',default='.')
    run(parser.parse_args().root)

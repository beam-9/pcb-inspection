"""Detector-neutral Stage 6A diagnostics of frozen PCB2 recipes.

No fitting, calibration, detector evaluation, or alternative detection decisions.
Commands are exclusive; completed outputs are never overwritten.
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageOps
import torch
from torch.nn import functional as F

from .guard import digest, now, write_new
from .geometry_experiment import DynamicExtractor, setup, WEIGHT
from .preprocessing import preprocess_mask
from .stage4_geometry import geometry_for
from .stage5a_missing import query_regions, top_neighbors, coordinates
from .stage5b_orientation import orientation_tensor, historical_predictions

STAGE = 'artifacts/stage6a'
RESCUE = 'bfebbd19caf4dad38fd66eab'
RECIPES = [('d1', 256, 'artifacts/stage5b', 'artifacts/stage4/pcb2_d1_primary'),
           ('d2', 512, 'artifacts/stage5c', 'artifacts/stage4/pcb2_d2_secondary')]


def read(path):
    return json.loads(Path(path).read_text())


def target_population(root):
    manifest = pd.read_csv(root/'artifacts/stage4/confirmation_data/test_manifest.csv').fillna('')
    candidate = historical_predictions(root/'artifacts/stage5c/predictions.csv').set_index('image_id')
    poses = pd.read_csv(root/'artifacts/stage5a/pose/pose_labels.csv').set_index('image_id').pose_label
    targets = []
    for row in manifest.itertuples():
        old = candidate.loc[row.image_id]
        missing = 'missing' in json.loads(row.defect_types)
        small = old.reference_area_band in ['R1', 'R2']
        canonical = poses[row.image_id] == 'canonical'
        if (canonical and missing) or small or row.image_id == RESCUE:
            groups = []
            if canonical and missing: groups.append('canonical_missing_' + ('hit' if old.detected else 'miss'))
            if small: groups.append('small_' + ('hit' if old.detected else 'miss'))
            if row.image_id == RESCUE: groups.append('marginal_reversed_rescue')
            targets.append({'image_id': row.image_id, 'source_labels': row.defect_types,
                            'pose_label': poses[row.image_id], 'size_band': old.reference_area_band,
                            'groups': '|'.join(groups)})
    return pd.DataFrame(targets).sort_values('image_id')


def projected_gt(mask, transform, pose):
    """Any union-mask positive within an 8x8 cell, in oriented model coordinates.

    This is a grid footprint, not a receptive field or component-specific mask.
    Rotate original crop BEFORE nearest resize (odd letterbox padding unchanged).
    """
    mask = np.asarray(mask, dtype=bool).copy()
    if pose == 'reversed_180':
        x0, y0, x1, y1 = transform['crop_box']
        mask[y0:y1, x0:x1] = mask[y0:y1, x0:x1][::-1, ::-1]
    return query_regions(mask, transform)[0]


def patch_diagnostics(scores, gt, threshold):
    scores = np.asarray(scores)
    gt = np.asarray(gt, dtype=bool)
    if scores.shape != gt.shape or not np.isfinite(scores).all() or not gt.any():
        raise ValueError('Finite scores and nonempty matching GT grid required')
    flat = scores.ravel(); inside = gt.ravel()
    order = np.argsort(-flat, kind='stable')
    peak = int(order[0]); gtmax = float(flat[inside].max())
    outside = float(flat[~inside].max()) if (~inside).any() else None
    result = {'max_native_patch_score': float(flat[peak]), 'max_GT_patch_score': gtmax,
              'max_outside_GT_patch_score': outside, 'gt_max_ratio': gtmax/threshold,
              'outside_gt_ratio': outside/threshold if outside is not None else None,
              'GT_to_image_max_ratio': gtmax/float(flat[peak]),
              'outside_to_image_max_ratio': outside/float(flat[peak]) if outside is not None else None,
              'top_score_patch_row': peak//scores.shape[1],
              'top_score_patch_column': peak % scores.shape[1],
              'top_score_patch_inside_GT': bool(inside[peak]),
              'first_gt_patch_rank': int(np.flatnonzero(inside[order])[0]+1),
              'GT_overlap_patch_count': int(inside.sum()), 'native_patch_count': int(flat.size)}
    for k in [1, 3, 5, 10]: result[f'top_{k}_mean'] = float(flat[order[:k]].mean())
    for k in [5, 10, 20]: result[f'top_{k}_gt_fraction'] = float(inside[order[:k]].mean())
    for percentile in [90, 95, 99]: result[f'patch_p{percentile}'] = float(np.percentile(flat, percentile))
    count = max(1, int(np.ceil(.01*len(flat))))
    result['top_1_percent_mean'] = float(flat[order[:count]].mean())
    return result


def categories(d1, d2, small):
    """Predeclared descriptive flags, not validated causal classifications."""
    flags = []
    if not d2['detected'] and max(d1['gt_max_ratio'], d2['gt_max_ratio']) < .8:
        flags.append('F1')
    if small and d2['gt_max_ratio']-d1['gt_max_ratio'] >= .2 and d2['common_pixel_ap']-d1['common_pixel_ap'] >= .1:
        flags.append('F2')
    # Outside competition describes map interpretation, never the cause of a max-score miss.
    if d2['detected'] and not d2['top_score_patch_inside_GT'] and d2['GT_to_image_max_ratio'] >= .8:
        flags.append('F3')
    if not d2['detected'] and .95 <= d2['score_divided_by_threshold'] < 1 and d2['gt_max_ratio'] >= .9:
        flags.append('F4')
    return '|'.join(flags) if flags else 'F5'


def verify_inputs(root, protocol):
    for name, expected in protocol['frozen_files'].items():
        if digest(root/name) != expected: raise ValueError('Frozen input changed: '+name)


def freeze(root, proposal):
    out = root/STAGE
    if out.exists(): raise FileExistsError('Stage6A namespace already exists')
    # Verify full Stage5C output identity before any new diagnostic result.
    complete = read(root/'artifacts/stage5c/complete.json')
    if not complete['passed']: raise ValueError('Stage5C incomplete')
    for name, expected in complete['outputs'].items():
        if digest(root/name) != expected: raise ValueError('Stage5C changed: '+name)
    out.mkdir(parents=True)
    targets = target_population(root)
    targets.to_csv(out/'target_manifest.csv', index=False)
    (out/'supplied_proposal.md').write_bytes(Path(proposal).read_bytes())
    # Snapshot every tracked file, allowing subsequent navigation edits without rewriting old receipts.
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
    baseline = {p: digest(root/p) for p in tracked if p and (root/p).is_file()}
    write_new(out/'prior_tracked_identity.json', baseline)
    history = out/'history_navigation'; history.mkdir()
    for name in ['README.md', 'docs/journey/README.md', 'docs/journey/decision_log.md']:
        (history/Path(name).name).write_bytes((root/name).read_bytes())
    files = {STAGE+'/target_manifest.csv', STAGE+'/supplied_proposal.md', WEIGHT,
             'artifacts/stage4/freeze_receipt.json', 'artifacts/stage4/confirmation_data/test_manifest.csv',
             'artifacts/stage5a/pose/pose_labels.csv'}
    manifest = pd.read_csv(root/'artifacts/stage4/confirmation_data/test_manifest.csv').set_index('image_id')
    for identity in targets.image_id:
        files.update([manifest.loc[identity,'image_path'], manifest.loc[identity,'mask_path']])
    for _, _, stage, historical in RECIPES:
        for folder in [stage, historical]:
            files.update(f'{folder}/{name}' for name in ['predictions.csv', 'test_transforms.json', 'array_paths.json'])
        files.add(historical+'/calibration.json')
        paths = read(root/historical/'array_paths.json'); files.add(paths['memory'])
        arrays = read(root/stage/'array_paths.json')
        for identity in targets.image_id:
            files.update(f'{arrays[key]}/{identity}.npy' for key in ['model_maps', 'anomaly_maps'])
    files.update(str(p.relative_to(root)) for p in (root/'src/pcb_inspection').glob('*.py'))
    files.update(str(p.relative_to(root)) for p in (root/'tests').glob('test_stage6a*.py'))
    protocol = {'created_at_utc': now(), 'scope': 'Stage6A only; exposed PCB2 development diagnosis',
                'detector_changed': False, 'target_count': len(targets),
                'gt_definition': 'source union mask; nearest resize; any positive in8x8 patch footprint, not RF',
                'ranking': 'descending float32 score, stable row-major ties, rank starts1',
                'feature_distance': 'all4096 frozen references, direct Euclidean float32; top5 median per query',
                'main': 'D2+Stage5C orientation; D1+Stage5B orientation is supporting context',
                'categories': 'F1 miss bothGT/threshold<0.8; F2 small D2-D1 GT ratio>=0.2 and AP>=0.1; F3 hit outside peak and GT/image>=0.8; F4 miss image/threshold>=0.95 and GT/threshold>=0.9; otherwise F5. Flags descriptive, not causal.',
                'tolerances': {'saved_map_score_absolute': 1e-5, 'float64_distance_absolute': 1e-5},
                'frozen_files': {name: digest(root/name) for name in sorted(files)}}
    write_new(out/'protocol.json', protocol)
    write_new(out/'freeze_receipt.json', {'created_at_utc': now(), 'protocol_sha256': digest(out/'protocol.json'),
              'git_head': subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip(),
              'prior_tracked_identity_sha256': digest(out/'prior_tracked_identity.json'),
              'stage5c_outputs_verified': len(complete['outputs'])})


def extract(root):
    out = root/STAGE; protocol = read(out/'protocol.json'); verify_inputs(root, protocol)
    if digest(out/'protocol.json') != read(out/'freeze_receipt.json')['protocol_sha256']: raise ValueError('Protocol changed')
    write_new(out/'started.json', {'created_at_utc': now()})
    cache = root/'data/cache/stage6a'; cache.mkdir(parents=True, exist_ok=False)
    targets = pd.read_csv(out/'target_manifest.csv').set_index('image_id')
    manifest = pd.read_csv(root/'artifacts/stage4/confirmation_data/test_manifest.csv').set_index('image_id')
    config = read(root/'artifacts/stage4/freeze_receipt.json')['config']
    setup(root); ext = DynamicExtractor(); records = []; distances = []; checks = []; arrays = {}
    for recipe, size, stage, historical in RECIPES:
        bank = torch.from_numpy(np.load(root/read(root/historical/'array_paths.json')['memory']))
        calibration = read(root/historical/'calibration.json'); threshold = calibration['image_threshold']
        predictions = historical_predictions(root/stage/'predictions.csv').set_index('image_id')
        old_predictions = historical_predictions(root/historical/'predictions.csv').set_index('image_id')
        transforms = read(root/historical/'test_transforms.json'); paths = read(root/stage/'array_paths.json')
        oldpaths = read(root/historical/'array_paths.json')
        for identity, target in targets.iterrows():
            row = manifest.loc[identity]; pose = target.pose_label
            with Image.open(root/row.image_path) as image:
                tensor, transform = orientation_tensor(image, geometry_for(image, config), pose, size)
            if transform != transforms[identity]: raise ValueError('Frozen transform changed')
            feature = ext(tensor[None])[0].permute(1,2,0).contiguous()
            query = feature.reshape(-1, feature.shape[-1])
            values, indices, _ = top_neighbors(query, bank)
            grid = values[:,0].reshape(size//8, size//8)
            model = F.interpolate(torch.from_numpy(grid)[None,None], (size,size), mode='bilinear', align_corners=False)[0,0].numpy()
            saved = np.load(root/paths['model_maps']/f'{identity}.npy'); pred = predictions.loc[identity]
            map_error = float(abs(model-saved).max()); score_error = abs(float(grid.max())-float(pred.score))
            if max(map_error,score_error)>1e-5: raise ValueError('Frozen extraction mismatch')
            if pose == 'canonical':
                if not np.array_equal(saved, np.load(root/oldpaths['model_maps']/f'{identity}.npy')) or float(pred.score)!=float(old_predictions.loc[identity,'score']):
                    raise ValueError('Canonical historical invariance failed')
            with Image.open(root/row.mask_path) as image: rawmask = np.asarray(ImageOps.exif_transpose(image).convert('L')) > 0
            gt = projected_gt(rawmask, transform, pose)
            commonmask = preprocess_mask(root/row.mask_path)
            common = np.load(root/paths['anomaly_maps']/f'{identity}.npy')
            positive = common > calibration['pixel_threshold']
            diag = patch_diagnostics(grid, gt, threshold)
            coord = coordinates(diag['top_score_patch_row'], diag['top_score_patch_column'], transform)
            if pose == 'reversed_180':
                x0,y0,x1,y1 = transform['crop_box']
                coord['source_x'] = x0+x1-coord['source_x']; coord['source_y'] = y0+y1-coord['source_y']
            record = {'image_id': identity, 'recipe': recipe, **target.to_dict(), 'mask_area': int(commonmask.sum()),
                      'source_mask_area': int(rawmask.sum()), 'image_score': float(pred.score), 'image_threshold': threshold,
                      'score_minus_threshold': float(pred.score)-threshold, 'score_divided_by_threshold': float(pred.score)/threshold,
                      'detected': bool(pred.detected), **diag, 'common_pixel_ap': float(pred.pixel_ap),
                      'peak_inside': bool(pred.peak_inside), 'any_overlap': bool((positive & commonmask).any()),
                      'GT_max_common': float(common[commonmask].max()), 'outside_GT_max_common': float(common[~commonmask].max()),
                      'FP_pixels': int((positive & ~commonmask).sum()), 'predicted_positive_pixels': int(positive.sum()),
                      'GT_intersection_pixels': int((positive & commonmask).sum()), 'IoU': float((positive & commonmask).sum()/(positive|commonmask).sum()),
                      'top_score_patch_source_x': coord['source_x'], 'top_score_patch_source_y': coord['source_y'],
                      'top_patch_padding_center': coord['padding_center'], 'map_reproduction_error': map_error}
            records.append(record)
            for qi in np.flatnonzero(gt.ravel()):
                distances.append({'image_id': identity, 'recipe': recipe, 'query_id': int(qi), 'groups': target.groups,
                                  'nearest_reference_distance': float(values[qi,0]), 'median_top5_reference_distance': float(np.median(values[qi])),
                                  'nearest_reference_index': int(indices[qi,0]), 'nearest_distance_ratio': float(values[qi,0])/threshold})
            # Systematic bounded audit inputs include GT cells and the global peak.
            selected = np.unique(np.r_[int(grid.argmax()), np.flatnonzero(gt.ravel())[np.linspace(0,int(gt.sum())-1,min(5,int(gt.sum())),dtype=int)]])
            path = cache/f'{recipe}_{identity}.npz'
            np.savez_compressed(path, scores=grid, gt=gt, top5=values, indices=indices,
                                check_query=query[selected].numpy(), check_ids=selected)
            arrays[str(path.relative_to(root))] = digest(path)
            checks.append({'image_id':identity,'recipe':recipe,'map_max_error':map_error,'score_error':score_error,'canonical_exact':pose=='canonical'})
            print(recipe, identity, 'GT cells', int(gt.sum()), flush=True)
    frame = pd.DataFrame(records); frame.to_csv(out/'per_recipe_diagnostics.csv',index=False)
    pd.DataFrame(distances).to_csv(out/'feature_distance.csv',index=False)
    pd.DataFrame(checks).to_csv(out/'reproduction_checks.csv',index=False)
    frame[['image_id','recipe','first_gt_patch_rank','top_5_gt_fraction','top_10_gt_fraction','top_20_gt_fraction','GT_overlap_patch_count','native_patch_count']].to_csv(out/'patch_rank_diagnostics.csv',index=False)
    frame[['image_id','recipe','max_GT_patch_score','max_outside_GT_patch_score']+[f'top_{k}_mean' for k in [1,3,5,10]]+[f'patch_p{p}' for p in [90,95,99]]+['top_1_percent_mean']].to_csv(out/'aggregation_diagnostics.csv',index=False)
    cases = []
    for identity, target in targets.iterrows():
        pair = frame[frame.image_id==identity].set_index('recipe'); d1=pair.loc['d1']; d2=pair.loc['d2']
        category = categories(d1,d2,target.size_band in ['R1','R2'])
        item = {'image_id':identity, **target.to_dict(), 'mask_area':int(d2.mask_area), 'failure_category':category,
                'diagnostic_notes': 'Descriptive flags; F3 is localization competition, not a cause of max-score misses. Union GT retains all source labels; F5 includes hits with no failure flag.'}
        for recipe, row in [('d1',d1),('d2',d2)]:
            for dest, source in [('detected','detected'),('score_ratio','score_divided_by_threshold'),('gt_max_ratio','gt_max_ratio'),('outside_gt_ratio','outside_gt_ratio'),('pixel_ap','common_pixel_ap'),('top_patch_inside_gt','top_score_patch_inside_GT')]:
                item[f'{recipe}_{dest}'] = row[source]
        cases.append(item)
    pd.DataFrame(cases).to_csv(out/'case_diagnosis.csv',index=False)
    verify_inputs(root, protocol)
    write_new(out/'extraction_complete.json', {'created_at_utc':now(),'case_count':len(targets),'detector_changed':False,
               'cache_outputs':arrays,'outputs':{str(p.relative_to(root)):digest(p) for p in out.glob('*.csv')}})


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('command',choices=['freeze','extract']); parser.add_argument('--root',default='.'); parser.add_argument('--proposal')
    args=parser.parse_args(); root=Path(args.root).resolve()
    if args.command=='freeze': freeze(root,args.proposal)
    else: extract(root)


if __name__ == '__main__': main()

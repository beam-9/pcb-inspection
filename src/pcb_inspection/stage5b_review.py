"""Independent Stage 5B audit of saved evidence and five bounded re-extractions.

The audit deliberately does not import the intervention implementation or its
metric helpers. Original source masks and saved raw maps determine the results.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageOps
from sklearn.metrics import average_precision_score, roc_auc_score
from scipy.ndimage import label as component_label
from scipy.spatial.distance import cdist


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def same(actual, expected, description, tolerance=1e-12):
    require(np.isclose(actual, expected, rtol=0, atol=tolerance),
            f'{description}: {actual} != {expected}')


def source_map(model, transform, reversed_pose):
    """Unpad, historical bilinear crop resize, exact inverse flip, source paste."""
    t = transform
    x0, y0, x1, y1 = t['crop_box']
    px, py = t['pad_x'], t['pad_y']
    content = model[py:py+t['content_height'], px:px+t['content_width']]
    crop = np.asarray(Image.fromarray(content.astype(np.float32)).resize(
        (x1-x0, y1-y0), Image.Resampling.BILINEAR), dtype=np.float32)
    if reversed_pose:
        crop = crop[::-1, ::-1].copy()
    result = np.zeros((t['source_height'], t['source_width']), np.float32)
    result[y0:y1, x0:x1] = crop
    return result


def pixel_counts(scores, gt, threshold):
    positive = scores > threshold
    intersection = int((positive & gt).sum())
    union = int((positive | gt).sum())
    return {
        'intersection': intersection, 'union': union,
        'fp_pixels': int((positive & ~gt).sum()),
        'predicted_positive_pixels': int(positive.sum()),
        'iou': intersection/union if union else None,
        'pixel_ap': float(average_precision_score(gt.ravel(), scores.ravel())) if gt.any() else None,
        'peak_inside': bool(gt.ravel()[scores.argmax()]),
        'overlap': bool(intersection),
    }


def verify(root, write=True):
    root = Path(root).resolve()
    base = root/'artifacts/stage5b'
    read = lambda p: json.loads(Path(p).read_text())
    protocol = read(base/'orientation_protocol.json')
    receipt = read(base/'freeze_receipt.json')
    require(receipt['protocol_sha256'] == digest(base/'orientation_protocol.json'), 'Protocol receipt')
    navigation_snapshots=protocol.get('navigation_snapshots', {})
    history_path=lambda name:root/navigation_snapshots.get(name,name)
    for name, expected in protocol['frozen_files'].items():
        require(digest(history_path(name)) == expected, f'Frozen history changed: {name}')
    # The previous-stage receipt predates this experiment and binds the histories.
    stage5a = read(root/'artifacts/stage5a/diagnostic_protocol.json')
    prior_checks = 0
    for field in ['stage4_identities', 'bound_local_cache_identities']:
        for name, expected in stage5a[field].items():
            require(digest(history_path(name)) == expected, f'Stage 5A history binding: {name}')
            prior_checks += 1
    diagnostic_receipt = read(root/'artifacts/stage5a/diagnostics.json')
    for name, expected in diagnostic_receipt['outputs'].items():
        require(digest(history_path(name)) == expected, f'Stage 5A output changed: {name}')
        prior_checks += 1
    calibration = read(root/'artifacts/stage4/pcb2_d1_primary/calibration.json')
    image_t, pixel_t = calibration['image_threshold'], calibration['pixel_threshold']
    require(protocol['thresholds']['image_threshold'] == image_t, 'Image threshold changed')
    require(protocol['thresholds']['pixel_threshold'] == pixel_t, 'Pixel threshold changed')
    final = read(root/'artifacts/stage5a/pose/labels_final.json')
    require(final['label_sha256'] == digest(root/'artifacts/stage5a/pose/pose_labels.csv'), 'Frozen labels changed')
    require(final['classifier_code_sha256'] == digest(root/'src/pcb_inspection/stage5a_pose.py'), 'Pose code changed')
    from .stage5a_pose import classify_pose, METHOD
    require(protocol['pose_method'] == METHOD, 'Pose parameters changed')
    pose = pd.read_csv(root/'artifacts/stage5a/pose/pose_labels.csv').set_index('image_id')
    require(len(pose) == 1101 and pose.index.is_unique, 'Pose population')
    require(pose.loc[pose.normal_or_anomaly.eq('normal'), 'pose_label'].eq('canonical').all(), 'Normals not canonical')
    prior = root/'artifacts/stage4/pcb2_d1_primary'
    transforms = read(base/'test_transforms.json')
    original_transforms = read(root/'artifacts/stage4/geometry_preflight/normal_transforms.json')
    for name in ['fit_reference_transforms.json', 'calibration_transforms.json', 'test_transforms.json']:
        original_transforms.update(read(prior/name))
    for image_id, row in pose.iterrows():
        require(digest(root/row.image_path) == row.source_sha256, f'Pose source changed: {image_id}')
        with Image.open(root/row.image_path) as raw:
            result = classify_pose(raw, original_transforms[image_id]['board_box'])
        require(result['pose_label'] == row.pose_label, f'Pose reproduction: {image_id}')
    table = pd.read_csv(base/'predictions.csv', float_precision='round_trip').set_index('image_id')
    baseline = pd.read_csv(prior/'predictions.csv', float_precision='round_trip').set_index('image_id')
    manifest = pd.read_csv(prior/'confirmation_manifest.csv').set_index('image_id')
    require(len(table) == 200 and table.index.is_unique and set(table.index) == set(baseline.index), 'Evaluation identities')
    reversed_ids = set(pose[pose.pose_label.eq('reversed_180')].index)
    require(len(reversed_ids) == 5 and set(protocol['reversed_ids']) == reversed_ids, 'Five reversed identities')
    paths, oldpaths = read(base/'array_paths.json'), read(prior/'array_paths.json')
    records, all_maps, all_masks, grid_checks, difference_checks = [], [], [], [], []
    noop, normals = 0, 0
    for image_id, row in table.iterrows():
        t = transforms[image_id]
        for key, value in original_transforms[image_id].items():
            require(t[key] == value, f'Geometry changed: {image_id}/{key}')
        is_reversed = image_id in reversed_ids
        require(row.pose_label == pose.loc[image_id, 'pose_label'], 'Pose row mismatch')
        source = manifest.loc[image_id]
        require(row.label == source.label, 'Evaluation label mismatch')
        common = np.load(root/paths['anomaly_maps']/f'{image_id}.npy', allow_pickle=False)
        model = np.load(root/paths['model_maps']/f'{image_id}.npy', allow_pickle=False)
        saved_source = np.load(root/paths['source_maps']/f'{image_id}.npy', allow_pickle=False)
        require(model.shape == (256, 256) and common.shape == (256, 256), 'Raw map shape')
        require(np.isfinite(common).all() and np.isfinite(model).all() and np.isfinite(saved_source).all(), 'Nonfinite maps')
        expected_source = source_map(model, t, is_reversed)
        require(np.array_equal(saved_source, expected_source), f'Inverse mapping: {image_id}')
        expected_common = np.asarray(Image.fromarray(expected_source).resize((256,256), Image.Resampling.BILINEAR))
        require(np.array_equal(common, expected_common), f'Common mapping: {image_id}')
        with Image.open(root/source.image_path) as raw:
            image = np.asarray(ImageOps.exif_transpose(raw).convert('RGB'))
        x0,y0,x1,y1=t['crop_box'];crop=image[y0:y1,x0:x1]
        require(np.array_equal(crop[::-1,::-1][::-1,::-1],crop), 'Double rotation identity')
        if row.label == 'anomaly':
            require(digest(root/source.mask_path) == source.mask_sha256, 'Original GT hash changed')
            with Image.open(root/source.mask_path) as raw:
                mask = ImageOps.exif_transpose(raw).convert('L')
                gt = np.asarray(mask.resize((256,256), Image.Resampling.NEAREST)) > 0
                source_gt = np.asarray(mask) > 0
        else:
            gt=np.zeros((256,256),bool);source_gt=np.zeros(expected_source.shape,bool)
        values=pixel_counts(common,gt,pixel_t)
        py,px=t['pad_y'],t['pad_x']
        content=model[py:py+t['content_height'],px:px+t['content_width']]
        native_positive=content>pixel_t
        yy,xx=np.where(native_positive)
        bbox=int((yy.max()-yy.min()+1)*(xx.max()-xx.min()+1)) if len(yy) else 0
        values.update(crop_fraction_above_threshold=float(native_positive.mean()),
                      native_positive_components_8=int(component_label(native_positive,np.ones((3,3),int))[1]),
                      native_positive_bbox_area=bbox,native_positive_bbox_crop_fraction=bbox/native_positive.size,
                      gt_max_score=float(common[gt].max()) if gt.any() else None,
                      outside_gt_max_score=float(common[~gt].max()))
        for key in ['intersection','union','fp_pixels','predicted_positive_pixels','pixel_ap','iou']:
            if key in table and values[key] is not None:
                same(row[key],values[key],f'{image_id}/{key}')
        for key in ['crop_fraction_above_threshold','native_positive_components_8','native_positive_bbox_area','native_positive_bbox_crop_fraction','gt_max_score','outside_gt_max_score']:
            if values[key] is not None:same(row[key],values[key],f'{image_id}/{key}')
        for key in ['peak_inside','overlap']:
            require(bool(row[key]) == values[key], f'{image_id}/{key}')
        source_values = pixel_counts(saved_source,source_gt,pixel_t) if is_reversed else None
        if source_values:
            for key in ['intersection','union','pixel_ap','iou']:
                if 'source_'+key in table and source_values[key] is not None:
                    same(row['source_'+key],source_values[key],f'{image_id}/source_{key}')
        require(bool(row.detected) == (row.score > image_t), 'Strict image threshold')
        if not is_reversed:
            require(np.array_equal(model,np.load(root/oldpaths['model_maps']/f'{image_id}.npy')), f'No-op model map: {image_id}')
            require(np.array_equal(common,np.load(root/oldpaths['anomaly_maps']/f'{image_id}.npy')), f'No-op common map: {image_id}')
            same(row.score,baseline.loc[image_id,'score'],f'No-op score: {image_id}',0)
            require(row.detected == baseline.loc[image_id,'detected'], 'No-op flag')
            noop += 1
            normals += int(row.label == 'normal')
        else:
            old_common=np.load(root/oldpaths['anomaly_maps']/f'{image_id}.npy')
            previous=old_common>pixel_t;positive=common>pixel_t
            removed=previous&~positive;added=positive&~previous
            delta=common.astype(np.float64)-old_common.astype(np.float64)
            difference_checks.append({'image_id':image_id,'mean_delta':float(delta.mean()),'min_delta':float(delta.min()),'max_delta':float(delta.max()),
                'mean_absolute_delta':float(np.abs(delta).mean()),'removed_exceedances':int(removed.sum()),'removed_outside_gt':int((removed&~gt).sum()),
                'removed_inside_gt':int((removed&gt).sum()),'new_exceedances':int(added.sum()),'new_outside_gt':int((added&~gt).sum()),'new_inside_gt':int((added&gt).sum())})
            u=((np.arange(256)+.5)*t['source_width']/256-x0)/(x1-x0)
            v=((np.arange(256)+.5)*t['source_height']/256-y0)/(y1-y0)
            uu,vv=np.meshgrid(u,v);inside=(uu>=0)&(uu<1)&(vv>=0)&(vv<1)
            cells=np.floor(vv*4).astype(int)*4+np.floor(uu*4).astype(int)
            for cell in range(16):
                region=inside&(cells==cell);g=gt[region]
                rec={'image_id':image_id,'view':'common256_crop','grid_row':cell//4,'grid_column':cell%4}
                for prefix,scores in [('historical',old_common),('normalized',common)]:
                    s=scores[region];p=s>pixel_t
                    counts_in_cell={'denominator_pixels':int(region.sum()),'gt_positive_pixels':int(g.sum()),'predicted_positive_pixels':int(p.sum()),
                        'intersection_pixels':int((p&g).sum()),'union_pixels':int((p|g).sum()),'false_positive_pixels':int((p&~g).sum()),
                        'score_sum':float(s.astype(np.float64).sum()),'mean_raw_score':float(s.mean()),'threshold_exceedance_fraction':float(p.mean())}
                    rec.update({prefix+'_'+key:value for key,value in counts_in_cell.items()})
                grid_checks.append(rec)
            # Native content is restored to original crop orientation while
            # preserving padding placement; GT stays in original coordinates.
            old_model=np.load(root/oldpaths['model_maps']/f'{image_id}.npy')
            restored_model=model.copy()
            restored_model[py:py+t['content_height'],px:px+t['content_width']]=content[::-1,::-1]
            u=(np.arange(256)+.5-t['pad_x'])/t['content_width']
            v=(np.arange(256)+.5-t['pad_y'])/t['content_height']
            uu,vv=np.meshgrid(u,v);inside=(uu>=0)&(uu<1)&(vv>=0)&(vv<1)
            cells=np.floor(vv*4).astype(int)*4+np.floor(uu*4).astype(int)
            for cell in range(16):
                region=inside&(cells==cell)
                rec={'image_id':image_id,'view':'native_content','grid_row':cell//4,'grid_column':cell%4}
                for prefix,scores in [('historical',old_model),('normalized',restored_model)]:
                    sx=np.clip(np.floor(x0+uu*(x1-x0)).astype(int),0,t['source_width']-1)
                    sy=np.clip(np.floor(y0+vv*(y1-y0)).astype(int),0,t['source_height']-1)
                    g=source_gt[sy,sx][region];s=scores[region];p=s>pixel_t
                    cell_values={'denominator_pixels':int(region.sum()),'gt_positive_pixels':int(g.sum()),'predicted_positive_pixels':int(p.sum()),
                        'intersection_pixels':int((p&g).sum()),'union_pixels':int((p|g).sum()),'false_positive_pixels':int((p&~g).sum()),
                        'score_sum':float(s.astype(np.float64).sum()),'mean_raw_score':float(s.mean()),'threshold_exceedance_fraction':float(p.mean())}
                    rec.update({prefix+'_'+key:value for key,value in cell_values.items()})
                grid_checks.append(rec)
        records.append({'image_id':image_id,**values})
        all_maps.append(common);all_masks.append(gt)
    require(noop == 195 and normals == 100, 'No-op population')
    counts=pd.DataFrame(records).set_index('image_id')
    grid_saved=pd.read_csv(base/'regional/reversed_grid_comparison.csv',float_precision='round_trip').set_index(['image_id','view','grid_row','grid_column'])
    require(len(grid_saved)==160 and grid_saved.index.is_unique,'Reversed grid population')
    for rec in grid_checks:
        saved=grid_saved.loc[(rec['image_id'],rec['view'],rec['grid_row'],rec['grid_column'])]
        for key,value in rec.items():
            if key not in ['image_id','view','grid_row','grid_column']:same(saved[key],value,'Independent grid/'+key)
    difference_saved=pd.read_csv(base/'results/map_difference_statistics.csv',float_precision='round_trip').set_index('image_id')
    require(set(difference_saved.index)==reversed_ids,'Difference population')
    for rec in difference_checks:
        for key,value in rec.items():
            if key!='image_id':same(difference_saved.loc[rec['image_id'],key],value,'Independent difference/'+key)
    paired=pd.read_csv(base/'results/reversed_paired_results.csv',float_precision='round_trip').set_index('image_id')
    require(set(paired.index)==reversed_ids and len(paired)==5,'Paired population')
    for image_id in reversed_ids:
        row=paired.loc[image_id]
        for name,key in [('detected','detected'),('image_score','score'),('pixel_ap','pixel_ap'),('intersection','intersection'),('union','union'),('iou','iou'),('peak_inside','peak_inside'),('overlap','overlap')]:
            same(row['historical_'+name],baseline.loc[image_id,key],'Paired historical/'+name)
            same(row['normalized_'+name],table.loc[image_id,key],'Paired normalized/'+name)
        same(row.normalized_fp_pixels,counts.loc[image_id,'fp_pixels'],'Paired FP')
        same(row.absolute_delta,row.normalized_fp_pixels-row.historical_fp_pixels,'Paired delta')
        same(row.relative_delta,row.absolute_delta/row.historical_fp_pixels,'Paired relative delta')
        for prefix in ['historical','normalized']:
            part=grid_saved.loc[(image_id,'common256_crop')]
            outside=0 # Current crop encompasses every threshold-exceedance pixel.
            same(part[prefix+'_false_positive_pixels'].sum()+outside,row[prefix+'_fp_pixels'],'Grid FP reconciliation')
    y=table.label.eq('anomaly').to_numpy();pred=table.score.to_numpy()>image_t
    image_metrics={'tp':int((y&pred).sum()),'fp':int((~y&pred).sum()),'fn':int((y&~pred).sum()),'tn':int((~y&~pred).sum()),
                   'average_precision':float(average_precision_score(y,table.score)), 'auroc':float(roc_auc_score(y,table.score))}
    maps=np.asarray(all_maps);masks=np.asarray(all_masks)
    intersection=int(counts.intersection.sum());union=int(counts.union.sum())
    pixel_metrics={'intersection_pixels':intersection,'union_pixels':union,'positive_pixels':int(masks.sum()),
                   'pixel_iou':intersection/union,'pixel_average_precision':float(average_precision_score(masks.ravel(),maps.ravel()))}
    metrics=read(base/'results/modified_d1_metrics.json')
    for key,value in image_metrics.items():same(metrics['image'][key],value,'Full image metric/'+key)
    for key,value in pixel_metrics.items():same(metrics['localization_common256'][key],value,'Full pixel metric/'+key)
    anomaly_counts=counts.loc[table.index[table.label.eq('anomaly')]]
    anomaly_metrics={'anomaly_count':100,'median_per_image_pixel_ap':float(anomaly_counts.pixel_ap.median()),
        'q25':float(anomaly_counts.pixel_ap.quantile(.25)),'q75':float(anomaly_counts.pixel_ap.quantile(.75)),
        'peak_inside_count':int(anomaly_counts.peak_inside.sum()),'overlap_count':int(anomaly_counts.overlap.sum())}
    for key,value in anomaly_metrics.items():same(metrics['anomaly_localization']['common256_'][key],value,'Anomaly metrics/'+key)
    timing=pd.read_csv(base/'results/runtime.csv',float_precision='round_trip').set_index('image_id')
    require(len(timing)==200 and set(timing.index)==set(table.index),'Runtime population')
    require((timing.select_dtypes(include='number')>=0).all().all(),'Negative runtime measurement')
    timing_values={'median_end_to_end_seconds':float(timing.end_to_end_seconds.median()),
        'p95_end_to_end_seconds':float(timing.end_to_end_seconds.quantile(.95)),
        'median_inference_seconds':float(timing.d1_inference_seconds.median()),
        'reversed_median_seconds':float(timing.loc[sorted(reversed_ids),'end_to_end_seconds'].median()),
        'no_op_median_seconds':float(timing.loc[~timing.index.isin(reversed_ids),'end_to_end_seconds'].median()),
        'median_pose_seconds':float(timing.pose_seconds.median())}
    for key,value in timing_values.items():same(metrics['runtime'][key],value,'Runtime summary/'+key)
    # Five bounded RGB-to-feature checks establish that saved changed maps came
    # from the intended crop transformation. Distances use an independent
    # float64 SciPy implementation, rather than the runner's torch scorer.
    from .geometry_experiment import DynamicExtractor, setup
    import torch
    setup(root);extractor=DynamicExtractor()
    bank=np.load(root/protocol['bank_path']).astype(np.float64)
    score_checks=[]
    for image_id in sorted(reversed_ids):
        t=transforms[image_id];x0,y0,x1,y1=t['crop_box']
        with Image.open(root/manifest.loc[image_id,'image_path']) as raw:
            im=ImageOps.exif_transpose(raw).convert('RGB')
            crop=np.asarray(im)[y0:y1,x0:x1][::-1,::-1].copy()
        canvas=Image.new('RGB',(256,256),(128,128,128))
        canvas.paste(Image.fromarray(crop).resize((t['content_width'],t['content_height']),Image.Resampling.BILINEAR),(t['pad_x'],t['pad_y']))
        rgb=np.asarray(canvas,dtype=np.float32).copy()/255
        tensor=torch.from_numpy(rgb).permute(2,0,1)
        tensor=(tensor-torch.tensor([.485,.456,.406])[:,None,None])/torch.tensor([.229,.224,.225])[:,None,None]
        feature=extractor(tensor[None]);q=feature.permute(0,2,3,1).reshape(-1,384).numpy().astype(np.float64)
        nearest=np.concatenate([cdist(chunk,bank).min(axis=1) for chunk in np.array_split(q,4)])
        independent_score=float(nearest.max())
        same(table.loc[image_id,'score'],independent_score,'Independent float64 patchmax/'+image_id,1e-5)
        independent_model=torch.nn.functional.interpolate(torch.from_numpy(nearest.astype(np.float32).reshape(1,1,32,32)),(256,256),mode='bilinear',align_corners=False)[0,0].numpy()
        saved=np.load(root/paths['model_maps']/f'{image_id}.npy')
        map_error=float(np.abs(independent_model-saved).max())
        require(map_error<1e-5,'Independent float64 feature-distance map')
        score_checks.append({'image_id':image_id,'patches':len(q),'independent_float64_patchmax':independent_score,
            'score_absolute_error':abs(independent_score-table.loc[image_id,'score']),'map_max_absolute_error':map_error})
    review={'passed':True,'reviewed_at_utc':datetime.now(timezone.utc).isoformat(),'new_model_inference':True,
            'independent_inference_scope':'Five reversed RGB reconstructions only; independent float64 SciPy distances; no baseline rerun or tuning',
            'independent_reversed_feature_distance_checks':score_checks,
            'scope':'post-confirmation PCB2 development evidence','history_hashes_checked':len(protocol['frozen_files'])+prior_checks,
            'pose_rgb_labels_reproduced':1101,'exact_inverse_map_checks':200,'no_op_exact_maps_scores_flags':noop,'unchanged_normal_flags':normals,
            'source_mask_identity':'Original manifest hashes and original source coordinates',
            'regional_grid_cells_independently_recomputed':160,'reversed_difference_statistics_recomputed':5,'paired_rows_independently_checked':5,
            'image_metrics':image_metrics,'pixel_metrics':pixel_metrics,'false_positive_pixels':int(counts.fp_pixels.sum()),
            'runtime_summaries_independently_recomputed':timing_values,
            'reversed_independent_metrics':counts.loc[sorted(reversed_ids)].reset_index().to_dict('records'),
            'review_code_sha256':digest(__file__),'protocol_sha256':digest(base/'orientation_protocol.json')}
    if write:
        with (base/'independent_review.json').open('x') as stream:
            json.dump(review,stream,indent=2,allow_nan=False);stream.write('\n')
    return review


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',default='.');parser.add_argument('--no-write',action='store_true')
    args=parser.parse_args();print(json.dumps(verify(args.root,not args.no_write),indent=2))

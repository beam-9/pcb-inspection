"""Frozen orientation-only PCB2 development experiment; historical D1 stays intact."""
import argparse
import json
from pathlib import Path
import subprocess
import shutil
import time

import numpy as np
import pandas as pd
from PIL import Image, ImageOps
import torch

from .geometry import image_tensor, inverse_map
from .geometry_experiment import DynamicExtractor, WEIGHT, pixel_row, score_feature, setup
from .evaluation import image_metrics, localization_metrics
from .guard import digest, now, write_new
from .memory_experiment import rss_bytes
from .preprocessing import preprocess_mask
from .stage4_geometry import geometry_for
from .stage5a_pose import METHOD, classify_pose
from .stage5a_maps import crop_coordinates, grid_rows, spread

BASE = 'artifacts/stage4/pcb2_d1_primary'
STAGE = 'artifacts/stage5b'
POSE = 'artifacts/stage5a/pose/pose_labels.csv'
ACTIONS = {'canonical': 'no_op', 'reversed_180': 'rotate_180', 'uncertain': 'no_op'}
SCOPE = 'post-confirmation PCB2 development evidence'


def rotate_180(array):
    """Exact, dimension-preserving reversal; no resampling."""
    return np.ascontiguousarray(np.asarray(array)[::-1, ::-1])


def orientation_tensor(image, geometry, pose_label, size=256, timings=None):
    action = ACTIONS[pose_label]
    if action == 'no_op':
        if timings is not None:timings['rotation_seconds']=0.
        return image_tensor(image, geometry, size)
    original = ImageOps.exif_transpose(image).convert('RGB')
    x0, y0, x1, y1 = geometry['crop_box']
    crop = np.asarray(original.crop((x0, y0, x1, y1)))
    tick=time.perf_counter();rotated=rotate_180(crop)
    if timings is not None:timings['rotation_seconds']=time.perf_counter()-tick
    original.paste(Image.fromarray(rotated), (x0, y0))
    return image_tensor(original, geometry, size)


def orientation_inverse_map(scores, transform, pose_label, common_size=None):
    if ACTIONS[pose_label] == 'no_op':
        return inverse_map(scores, transform, common_size)
    t = transform
    a = np.asarray(scores, dtype=np.float32)
    if a.shape != (t['input_size'], t['input_size']):
        raise ValueError('Map/input shape mismatch')
    x0, y0, x1, y1 = t['crop_box']
    px, py, rw, rh = t['pad_x'], t['pad_y'], t['content_width'], t['content_height']
    crop = np.asarray(Image.fromarray(a[py:py+rh, px:px+rw]).resize((x1-x0, y1-y0), Image.Resampling.BILINEAR))
    full = Image.new('F', (t['source_width'], t['source_height']), 0.)
    full.paste(Image.fromarray(rotate_180(crop)), (x0, y0))
    if common_size:
        full = full.resize((common_size, common_size), Image.Resampling.BILINEAR)
    return np.asarray(full, dtype=np.float32).copy()


def verify_files(root, files):
    for name, expected in files.items():
        if digest(root / name) != expected:
            raise ValueError(f'Frozen identity changed: {name}')


def freeze(root, handoff_path=None):
    root = Path(root).resolve()
    out = root / STAGE
    config_path = root / 'configs/stage5b_orientation_protocol.json'
    if out.exists() or config_path.exists() or (root/'data/cache/stage5b').exists():
        raise FileExistsError('Stage5B refuses silent overwrite')
    base = root / BASE
    from .stage4_transfer import verify_prepared
    verify_prepared(root,base)
    stage5a_review=json.loads((root/'artifacts/stage5a/independent_review.json').read_text())
    if not stage5a_review['passed']:raise ValueError('Reviewed Stage5A diagnostics required')
    verify_files(root,json.loads((root/'artifacts/stage5a/diagnostics.json').read_text())['outputs'])
    for directory in [base]:
        complete = json.loads((directory/'complete.json').read_text())
        files = complete.get('outputs', {})
        verify_files(root, files)
    done = json.loads((base/'complete.json').read_text())
    review = json.loads((base/'independent_review.json').read_text())
    if not review['passed'] or review['complete_sha256'] != digest(base/'complete.json'):
        raise ValueError('Reviewed historical D1 required')
    labels = pd.read_csv(root/POSE, keep_default_na=False)
    receipt = json.loads((root/'artifacts/stage5a/pose/labels_final.json').read_text())
    if receipt['label_sha256'] != digest(root/POSE) or receipt['classifier_code_sha256'] != digest(root/'src/pcb_inspection/stage5a_pose.py'):
        raise ValueError('Frozen Stage5A pose identity changed')
    if len(labels) != 1101 or not labels.image_id.is_unique or not labels.loc[labels.normal_or_anomaly.eq('normal'), 'pose_label'].eq('canonical').all():
        raise ValueError('Complete canonical-normal pose inventory required')
    frame = pd.read_csv(base/'confirmation_manifest.csv', keep_default_na=False)
    if len(frame) != 200 or not frame.image_id.is_unique:
        raise ValueError('Fixed200 evaluation required')
    reversed_ids = sorted(labels.loc[labels.pose_label.eq('reversed_180'), 'image_id'])
    if len(reversed_ids) != 5 or not set(reversed_ids).issubset(set(frame.image_id)):
        raise ValueError('Exact five reversed identities required')
    paths = json.loads((base/'array_paths.json').read_text())
    # Preserve every historical result and old implementation, including uncommitted Stage5A.
    historical = sorted(p for directory in ['artifacts/stage4','artifacts/stage5a'] for p in (root/directory).rglob('*') if p.is_file())
    historical += sorted(p for p in (root/'src/pcb_inspection').glob('*.py') if not p.name.startswith('stage5b_') or p.name=='stage5b_orientation.py')
    historical += [root/'tests/test_stage5b_orientation.py', root/'docs/development/stage5b_plan_review.md']
    historical += [root/paths['memory'],root/WEIGHT, root/'requirements.lock']
    historical += sorted((root/paths['model_maps']).glob('*.npy')) + sorted((root/paths['anomaly_maps']).glob('*.npy'))
    historical += [root/r.image_path for r in frame.itertuples()] + [root/r.mask_path for r in frame.itertuples() if r.label=='anomaly']
    navigation=['README.md','docs/journey/README.md','docs/journey/decision_log.md']
    historical += [root/name for name in navigation]
    files = {str(p.relative_to(root)): digest(p) for p in historical}
    thresholds = json.loads((base/'calibration.json').read_text())
    protocol = {'declared_at_utc':now(), 'scope':SCOPE, 'historical_stage4_commit':'2ec21c4686c7dad7d60c177cb35fed2cd62d9280',
        'working_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        'stage5a_identity':digest(root/'artifacts/stage5a/diagnostics.json'), 'input_size':256,
        'bank_path':paths['memory'],'bank_sha256':digest(root/paths['memory']), 'thresholds':thresholds,
        'pose_method':METHOD,'pose_actions':ACTIONS,'pose_labels_sha256':digest(root/POSE),
        'rotation':'exact array[::-1, ::-1] copy, crop before historical letterbox resize',
        'inverse':'remove padding; historical bilinear crop resize; exact180; originalsource paste; common256 bilinear',
        'primary_endpoint':'paired common256 false-positive pixel change on exact five reversed anomalies',
        'runtime_boundaries':'end-to-end includes source decoding, geometry, pose, tensor preprocessing, frozen score_feature including historical common inverse, then source/common orientation inverses; excludes GT metrics saving and no-op tensor control; first sample cold; d1_inference_seconds includes frozen historical inverse; rotation actual exact array copy inside preprocessing; inverse computes source and common separately' ,
        'no_op_gate':'exact array equality native/common maps; exact score, flag, FP and applicable pixel AP',
        'success_interpretation':'paired burden reduction across cases, localization and defect signal,5/5 detection,195 exact no-op controls; no arbitrary cutoff',
        'reversed_ids':reversed_ids, 'evaluation_identities':frame.to_dict('records'), 'frozen_files':files,
        'navigation_snapshots':{name:f'{STAGE}/history_navigation/{name}' for name in navigation},
        'required_outputs':['predictions.csv','results/modified_d1_metrics.json','results/reversed_paired_results.csv','results/no_op_invariance.csv','results/runtime.csv','regional/reversed_grid_comparison.csv','figures','independent_review.json','complete.json']}
    if handoff_path:
        protocol['handoff_sha256'] = digest(handoff_path)
    out.mkdir(parents=True,exist_ok=False)
    for name,snapshot in protocol['navigation_snapshots'].items():
        target=root/snapshot;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/name,target)
    write_new(config_path,protocol)
    write_new(out/'orientation_protocol.json',protocol)
    write_new(out/'freeze_receipt.json',{'frozen_at_utc':now(),'scope':SCOPE,'protocol_sha256':digest(config_path),
        'artifact_protocol_sha256':digest(out/'orientation_protocol.json'),'inference_started':False})
    return protocol


def verify_freeze(root):
    out=root/STAGE
    receipt=json.loads((out/'freeze_receipt.json').read_text())
    if digest(root/'configs/stage5b_orientation_protocol.json')!=receipt['protocol_sha256'] or digest(out/'orientation_protocol.json')!=receipt['artifact_protocol_sha256']:
        raise ValueError('Stage5B protocol identity changed')
    protocol=json.loads((out/'orientation_protocol.json').read_text())
    verify_files(root,protocol['frozen_files'])
    return protocol


def validate_pose_population(root, output):
    labels=pd.read_csv(root/POSE,keep_default_na=False)
    transforms=json.loads((root/'artifacts/stage4/geometry_preflight/normal_transforms.json').read_text())
    transforms.update(json.loads((root/BASE/'test_transforms.json').read_text()))
    records=[]
    for row in labels.itertuples():
        if digest(root/row.image_path)!=row.source_sha256:raise ValueError('Pose source identity changed')
        with Image.open(root/row.image_path) as image:
            pose=classify_pose(image,transforms[row.image_id]['board_box'])
        if pose['pose_label']!=row.pose_label:raise ValueError(f'Frozen pose mismatch: {row.image_id}')
        records.append({'image_id':row.image_id,'expected':row.pose_label,'actual':pose['pose_label'],'action':ACTIONS[pose['pose_label']],'matched':True})
    pd.DataFrame(records).to_csv(output,index=False)
    return dict(zip(labels.image_id,labels.pose_label))


def diagnostic_row(common, model, mask, transform, threshold):
    positive=common>threshold
    py,px=transform['pad_y'],transform['pad_x']
    content=model[py:py+transform['content_height'],px:px+transform['content_width']]
    components,bbox,bbox_fraction=spread(content>threshold)
    return {'fp_pixels':int((positive&~mask).sum()),'predicted_positive_pixels':int(positive.sum()),
        'crop_fraction_above_threshold':float((content>threshold).mean()),'native_positive_components_8':components,
        'native_positive_bbox_area':bbox,'native_positive_bbox_crop_fraction':bbox_fraction,
        'gt_max_score':float(common[mask].max()) if mask.any() else None,'outside_gt_max_score':float(common[~mask].max())}


def evaluate(root):
    root=Path(root).resolve();protocol=verify_freeze(root);out=root/STAGE;base=root/BASE
    write_new(out/'inference_started.json',{'started_at_utc':now(),'freeze_receipt_sha256':digest(out/'freeze_receipt.json'),'scope':SCOPE})
    for directory in ['results','regional','transformed_inputs']:(out/directory).mkdir(exist_ok=False)
    labels=validate_pose_population(root,out/'results/pose_reproduction.csv')
    frame=pd.DataFrame(protocol['evaluation_identities'])
    baseline=pd.read_csv(base/'predictions.csv',keep_default_na=False,float_precision='round_trip').set_index('image_id')
    old_transforms=json.loads((base/'test_transforms.json').read_text());old_paths=json.loads((base/'array_paths.json').read_text())
    config=json.loads((root/'artifacts/stage4/freeze_receipt.json').read_text())['config']
    paths={key:f'data/cache/stage5b/{key}' for key in ['model_maps','anomaly_maps','source_maps']}
    for path in paths.values():(root/path).mkdir(parents=True,exist_ok=False)
    write_new(out/'array_paths.json',paths)
    setup(root);extractor=DynamicExtractor();bank=torch.from_numpy(np.load(root/protocol['bank_path'],allow_pickle=False))
    if bank.shape!=(4096,384) or not torch.isfinite(bank).all():raise ValueError('Historical bank invalid')
    thresholds=protocol['thresholds'];pt=thresholds['pixel_threshold'];it=thresholds['image_threshold']
    records=[];timings=[];controls=[];pairs=[];differences=[];grids=[];maps=[];masks=[];transforms={};manifest=[]
    for index,row in enumerate(frame.itertuples()):
        start=time.perf_counter()
        with Image.open(root/row.image_path) as source:
            source.load();tick=time.perf_counter();geometry=geometry_for(source,config);geometry_seconds=time.perf_counter()-tick
            tick=time.perf_counter();pose=classify_pose(source,geometry['board_box'])['pose_label'];pose_seconds=time.perf_counter()-tick
            if pose!=labels[row.image_id]:raise ValueError('Evaluation pose mismatch')
            detail={};tick=time.perf_counter();tensor,t=orientation_tensor(source,geometry,pose,timings=detail);preprocess_seconds=time.perf_counter()-tick
            rotation_seconds=detail['rotation_seconds']
        if t!=old_transforms[row.image_id]:raise ValueError('Historical crop/letterbox changed')
        tick=time.perf_counter();score,model,_=score_feature(extractor(tensor[None]),bank,256,t);inference_seconds=time.perf_counter()-tick
        tick=time.perf_counter();common=orientation_inverse_map(model,t,pose,256);source_map=orientation_inverse_map(model,t,pose);inverse_seconds=time.perf_counter()-tick
        end_to_end=time.perf_counter()-start
        tensor_exact=True
        if pose!='reversed_180':
            with Image.open(root/row.image_path) as source:historical_tensor,historical_t=image_tensor(source,geometry,256)
            tensor_exact=torch.equal(tensor,historical_tensor) and historical_t==t
        mask=preprocess_mask(root/row.mask_path) if row.label=='anomaly' else np.zeros((256,256),bool)
        old=baseline.loc[row.image_id];old_model=np.load(root/old_paths['model_maps']/f'{row.image_id}.npy');old_map=np.load(root/old_paths['anomaly_maps']/f'{row.image_id}.npy')
        diag=diagnostic_row(common,model,mask,t,pt);old_diag=diagnostic_row(old_map,old_model,mask,t,pt)
        rec={'image_id':row.image_id,'image_path':row.image_path,'label':row.label,'score':score,'detected':score>it,'seconds':end_to_end,
            'fallback':t['fallback'],'crop_area_fraction':t['crop_area_fraction'],'pose_label':pose,'orientation_action':ACTIONS[pose],
            **pixel_row(mask,common,pt),**diag}
        if row.label=='anomaly':
            with Image.open(root/row.mask_path) as image:raw_mask=np.asarray(ImageOps.exif_transpose(image).convert('L'))>0
            rec.update({f'source_{k}':v for k,v in pixel_row(raw_mask,source_map,pt).items()})
            for k in ['defect_types','reference_area_band','pcb2_size_quartile','source_annotation_outside_crop_fraction']:rec[k]=old[k]
        np.save(root/paths['model_maps']/f'{row.image_id}.npy',model);np.save(root/paths['anomaly_maps']/f'{row.image_id}.npy',common);np.save(root/paths['source_maps']/f'{row.image_id}.npy',source_map)
        transforms[row.image_id]={**t,'pose_label':pose,'orientation_action':ACTIONS[pose]}
        records.append(rec);maps.append(common);masks.append(mask)
        timings.append({'image_id':row.image_id,'pose_label':pose,'geometry_seconds':geometry_seconds,'pose_seconds':pose_seconds,'rotation_seconds':rotation_seconds,
            'total_preprocessing_seconds':geometry_seconds+pose_seconds+preprocess_seconds,'d1_inference_seconds':inference_seconds,'inverse_map_seconds':inverse_seconds,'end_to_end_seconds':end_to_end})
        if pose!='reversed_180':
            control={'image_id':row.image_id,'label':row.label,'pose_label':pose,'action_no_op':ACTIONS[pose]=='no_op','tensor_exact':tensor_exact,'score_exact':score==old.score,'flag_exact':rec['detected']==old.detected,
                'model_map_exact':np.array_equal(model,old_model),'common_map_exact':np.array_equal(common,old_map),'pixel_ap_exact':rec['pixel_ap']==old.pixel_ap if row.label=='anomaly' else True,'fp_pixels_exact':diag['fp_pixels']==old_diag['fp_pixels']}
            control['passed']=all(v for k,v in control.items() if k.endswith('_exact') or k=='action_no_op');controls.append(control)
            if not control['passed']:
                pd.DataFrame(controls).to_csv(out/'results/no_op_invariance.csv',index=False)
                raise ValueError(f'Exact no-op control failed: {row.image_id}; interpretation prohibited')
        else:
            pair={'image_id':row.image_id,'source_labels':old.defect_types,'mask_area':int(mask.sum())}
            names={'detected':'detected','image_score':'score','pixel_ap':'pixel_ap','fp_pixels':'fp_pixels','predicted_positive_pixels':'predicted_positive_pixels','crop_fraction_above_threshold':'crop_fraction_above_threshold','peak_inside':'peak_inside','overlap':'overlap','intersection':'intersection','union':'union','iou':'iou','map_spread':'native_positive_bbox_crop_fraction','gt_max_score':'gt_max_score','outside_gt_max_score':'outside_gt_max_score'}
            old_record={**old.to_dict(),**old_diag}
            for name,key in names.items():pair['historical_'+name]=old_record[key];pair['normalized_'+name]=rec[key]
            pair['absolute_delta']=diag['fp_pixels']-old_diag['fp_pixels'];pair['relative_delta']=pair['absolute_delta']/old_diag['fp_pixels'];pairs.append(pair)
            positive=common>pt;previous=old_map>pt;removed=previous&~positive;added=positive&~previous
            delta=common.astype(np.float64)-old_map.astype(np.float64)
            differences.append({'image_id':row.image_id,'mean_delta':float(delta.mean()),'min_delta':float(delta.min()),'max_delta':float(delta.max()),'mean_absolute_delta':float(abs(delta).mean()),
                'removed_exceedances':int(removed.sum()),'removed_outside_gt':int((removed&~mask).sum()),'removed_inside_gt':int((removed&mask).sum()),'new_exceedances':int(added.sum()),'new_outside_gt':int((added&~mask).sum()),'new_inside_gt':int((added&mask).sum())})
            _,_,inside,cells=crop_coordinates(t,256,256,False)
            historical_grid=grid_rows(row.image_id,'D1','common256_crop',old_map,mask,pt,inside,cells);normalized_grid=grid_rows(row.image_id,'D1+orientation','common256_crop',common,mask,pt,inside,cells)
            for h,n in zip(historical_grid,normalized_grid):
                grid={'image_id':row.image_id,'view':'common256_crop','grid_row':h['grid_row'],'grid_column':h['grid_column']}
                for key in ['denominator_pixels','gt_positive_pixels','predicted_positive_pixels','intersection_pixels','union_pixels','false_positive_pixels','mean_raw_score','threshold_exceedance_fraction','score_sum']:
                    grid['historical_'+key]=h[key];grid['normalized_'+key]=n[key]
                grids.append(grid)
            # Native grid stays in source crop orientation: restore only content,
            # preserving historical asymmetric padding around it.
            restored=model.copy();py,px=t['pad_y'],t['pad_x'];rh,rw=t['content_height'],t['content_width']
            restored[py:py+rh,px:px+rw]=rotate_180(model[py:py+rh,px:px+rw])
            u,v,native_inside,native_cells=crop_coordinates(t,256,256,True)
            from .stage5a_maps import source_gt_at
            native_gt=source_gt_at(raw_mask,t,u,v)
            hg=grid_rows(row.image_id,'D1','native_content',old_model,native_gt,pt,native_inside,native_cells)
            ng=grid_rows(row.image_id,'D1+orientation','native_content',restored,native_gt,pt,native_inside,native_cells)
            for h,n in zip(hg,ng):
                grid={'image_id':row.image_id,'view':'native_content','grid_row':h['grid_row'],'grid_column':h['grid_column']}
                for key in ['denominator_pixels','gt_positive_pixels','predicted_positive_pixels','intersection_pixels','union_pixels','false_positive_pixels','mean_raw_score','threshold_exceedance_fraction','score_sum']:
                    grid['historical_'+key]=h[key];grid['normalized_'+key]=n[key]
                grids.append(grid)
            manifest.append({'image_id':row.image_id,'source_sha256':row.sha256,'pose_label':pose,'orientation_action':ACTIONS[pose],'crop_box':json.dumps(t['crop_box']),'source_dimensions':json.dumps([t['source_width'],t['source_height']])})
        if index%25==0:print('Stage5B frozen D1',index,'/',len(frame),flush=True)
        if rss_bytes()>config['caps']['peak_rss_bytes']:raise RuntimeError('Stage5B memory cap exceeded')
    table=pd.DataFrame(records);timing=pd.DataFrame(timings);paired=pd.DataFrame(pairs)
    if len(controls)!=195 or len(pairs)!=5 or sorted(paired.image_id)!=protocol['reversed_ids']:raise ValueError('Fixed experiment counts mismatch')
    table.to_csv(out/'predictions.csv',index=False);table.to_csv(out/'results/per_image_results.csv',index=False)
    paired.to_csv(out/'results/reversed_paired_results.csv',index=False);paired.to_csv(out/'reversed_paired_results.csv',index=False)
    pd.DataFrame(controls).to_csv(out/'results/no_op_invariance.csv',index=False);timing.to_csv(out/'results/runtime.csv',index=False)
    pd.DataFrame(differences).to_csv(out/'results/map_difference_statistics.csv',index=False);pd.DataFrame(grids).to_csv(out/'regional/reversed_grid_comparison.csv',index=False)
    pd.DataFrame(manifest).to_csv(out/'transformed_inputs/reversed_manifest.csv',index=False);write_new(out/'test_transforms.json',transforms)
    anomaly=table[table.label.eq('anomaly')]
    metrics={'scope':SCOPE,'historical_baseline':json.loads((base/'metrics.json').read_text()),'image':image_metrics(table.label.eq('anomaly'),table.score,it),
        'localization_common256':localization_metrics(np.array(masks),np.array(maps),pt),
        'anomaly_localization':{'common256_':{'anomaly_count':len(anomaly),'median_per_image_pixel_ap':float(anomaly.pixel_ap.median()),'q25':float(anomaly.pixel_ap.quantile(.25)),'q75':float(anomaly.pixel_ap.quantile(.75)),
            'peak_inside_count':int(anomaly.peak_inside.sum()),'overlap_count':int(anomaly.overlap.sum())}},
        'total_fp_pixels':int(table.fp_pixels.sum()),'no_op_invariance':{'count':195,'passed':True,'normal_count':100},
        'reversed':{'count':5,'detected':int(paired.normalized_detected.sum()),'historical_total_fp_pixels':int(paired.historical_fp_pixels.sum()),'normalized_total_fp_pixels':int(paired.normalized_fp_pixels.sum()),
            'historical_median_fp_pixels':float(paired.historical_fp_pixels.median()),'normalized_median_fp_pixels':float(paired.normalized_fp_pixels.median())},
        'runtime':{'peak_rss_bytes':rss_bytes(),'median_end_to_end_seconds':float(timing.end_to_end_seconds.median()),'p95_end_to_end_seconds':float(timing.end_to_end_seconds.quantile(.95)),
            'median_inference_seconds':float(timing.d1_inference_seconds.median()),'reversed_median_seconds':float(timing.loc[timing.pose_label.eq('reversed_180'),'end_to_end_seconds'].median()),'no_op_median_seconds':float(timing.loc[~timing.pose_label.eq('reversed_180'),'end_to_end_seconds'].median()),
            'median_pose_seconds':float(timing.pose_seconds.median()),'rotation_timing':'actual exact array reversal/copy within preprocessing; inference includes frozen score_feature historical common inverse' }}
    for group,selected in [('missing',anomaly.defect_types.map(lambda s:'missing' in json.loads(s))),('small_R1_R2',anomaly.reference_area_band.isin(['R1','R2']))]:
        ids=anomaly.loc[selected,'image_id'];metrics[group]={'count':len(ids),'historical_detected':int(baseline.loc[ids,'detected'].sum()),'normalized_detected':int(anomaly.loc[selected,'detected'].sum())}
    if metrics['runtime']['median_inference_seconds']>config['caps']['median_inference_seconds']:raise RuntimeError('Stage5B runtime cap exceeded')
    verify_files(root,protocol['frozen_files'])
    write_new(out/'results/modified_d1_metrics.json',metrics)
    outputs={str(p.relative_to(root)):digest(p) for directory in [out,root/'data/cache/stage5b'] for p in directory.rglob('*') if p.is_file()}
    write_new(out/'inference_complete.json',{'completed_at_utc':now(),'scope':SCOPE,'freeze_receipt_sha256':digest(out/'freeze_receipt.json'),'no_op_gate_passed':True,'outputs':outputs})
    return metrics


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['freeze','evaluate']);parser.add_argument('--root',default='.');parser.add_argument('--handoff')
    args=parser.parse_args();result=freeze(args.root,args.handoff) if args.action=='freeze' else evaluate(args.root)
    print(json.dumps({k:v for k,v in result.items() if k not in ['frozen_files','evaluation_identities']},indent=2))

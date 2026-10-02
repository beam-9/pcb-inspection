"""Independent saved-output, projection and reference checks for Stage3 only."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
import torch

from .guard import digest, now, verify_frozen, write_new
from .geometry_experiment import DynamicExtractor, setup, tensor_and_transform
from .verify_results import direct_confusion, pairwise_auroc, ranked_average_precision


def require(condition, message):
    if not condition:
        raise ValueError(message)


def close(actual, expected, message, atol=1e-12, rtol=1e-10):
    if actual is None or expected is None:
        require(actual is expected,message)
    else:
        require(bool(np.isclose(actual,expected,atol=atol,rtol=rtol)),message)


def independent_inverse(model_map, transform):
    """Reconstruct full extent independently; don't call production inverse_map."""
    t=transform; size=t['input_size']
    require(model_map.shape==(size,size),'Model map geometry differs')
    x0,y0,x1,y1=t['crop_box']; px,py=t['pad_x'],t['pad_y']
    width,height=t['content_width'],t['content_height']
    require(0<=x0<x1<=t['source_width'] and 0<=y0<y1<=t['source_height'],'Crop outside source')
    require(0<=px<px+width<=size and 0<=py<py+height<=size,'Content outside input')
    content=model_map[py:py+height,px:px+width]
    resized=np.asarray(Image.fromarray(content).resize((x1-x0,y1-y0),Image.Resampling.BILINEAR))
    source=np.zeros((t['source_height'],t['source_width']),dtype=np.float32)
    source[y0:y1,x0:x1]=resized
    common=np.asarray(Image.fromarray(source).resize((256,256),Image.Resampling.BILINEAR))
    return source,common


def independent_prefix(projected, count=16, seed=42, anchors_count=10):
    """NumPy float32 oracle; no production selector call or full4096 rerun."""
    features=np.asarray(projected,dtype=np.float32)
    squared=np.sum(features*features,axis=1,dtype=np.float32)
    anchors=np.random.default_rng(seed).choice(len(features),anchors_count,replace=False)
    def distances(index):
        vector=features[index]
        return np.sqrt(np.maximum(squared+np.dot(vector,vector)-2*(features@vector),0))
    minimum=np.zeros(len(features),dtype=np.float32)
    for index in anchors: minimum+=distances(index)
    minimum/=len(anchors)
    result=[]
    for _ in range(count):
        index=int(np.argmax(minimum)); result.append(index)
        np.minimum(minimum,distances(index),out=minimum);minimum[index]=-np.inf
    return np.asarray(result,dtype=np.int64)


def pixel_check(mask,scores,threshold,record,prefix=''):
    flagged=scores>threshold
    intersection=int(np.count_nonzero(mask&flagged));union=int(np.count_nonzero(mask|flagged))
    peak=bool(mask[np.unravel_index(np.argmax(scores),scores.shape)])
    ap=ranked_average_precision(mask,scores) if mask.any() else None
    require(int(record[prefix+'intersection'])==intersection,'Pixel intersection differs')
    require(int(record[prefix+'union'])==union,'Pixel union differs')
    require(bool(record[prefix+'peak_inside'])==peak,'Peak membership differs')
    require(bool(record[prefix+'overlap'])==(intersection>0),'Overlap differs')
    close(record[prefix+'iou'] if pd.notna(record[prefix+'iou']) else None,intersection/union if union else None,'Per-image IoU differs')
    close(record[prefix+'mask_area_fraction'],float(mask.mean()),'Mask area fraction differs')
    if ap is not None: close(record[prefix+'pixel_ap'],ap,'Per-image AP differs')
    return intersection,union,peak,ap


def verify(root,size):
    root=Path(root).resolve();out=root/f'artifacts/runs/coreset_{size}_v1'
    done=json.loads((out/'complete.json').read_text());protocol=json.loads((out/'protocol.json').read_text())
    require(done['development_only'] and not done['pcb2_exposed'],'Confirmation scope differs')
    require(done['protocol_sha256']==digest(out/'protocol.json'),'Protocol identity differs')
    require('protocol.json' in done['outputs'] and 'prepared.json' in done['outputs'],'Missing prerequisite identities')
    for relative,expected in done['outputs'].items():
        path=(out/relative).resolve()
        require(path.is_relative_to(out) and digest(path)==expected,f'Output identity differs: {relative}')
    for relative,expected in protocol['frozen_files'].items():
        require(digest(root/relative)==expected,f'Frozen source identity differs: {relative}')
    verify_frozen(root,json.loads((root/'docs/protocol.json').read_text()))
    control=root/protocol['preserved_control'];old=json.loads((control/'protocol.json').read_text())
    for name in ['protocol.json','complete.json']:
        require(protocol['frozen_files'][str((control/name).relative_to(root))]==digest(control/name),'Control snapshot identity differs')
    for key,value in old['config'].items():
        require(protocol['config'][key]==value,f'Matched control configuration differs: {key}')
    for name,expected in old['frozen_files'].items():require(digest(root/name)==expected,'Preserved geometry code/input differs')
    prepared=json.loads((out/'prepared.json').read_text());access=json.loads((out/'development_access.json').read_text())
    require(prepared['protocol_sha256']==digest(out/'protocol.json') and prepared['resource_gate_passed'],'Normal preparation gate differs')
    require(access['protocol_sha256']==digest(out/'protocol.json') and access['prepared_sha256']==digest(out/'prepared.json') and access['evaluation_count']==1,'Development access identity differs')
    require(protocol['frozen_at_utc']<prepared['completed_at_utc']<access['started_at_utc'],'Freeze/preparation/access chronology differs')
    for name,expected in prepared['prerequisites'].items():require(digest(out/name)==expected,'Normal prerequisite differs')
    runtime=json.loads((out/'normal_runtime.json').read_text());caps=protocol['config']['caps']
    require(runtime['preparation_seconds']<=caps['preparation_seconds'] and runtime['peak_rss_bytes']<=caps['peak_rss_bytes'] and runtime['median_inference_seconds']<=caps['median_inference_seconds'],'Recorded normal resource gate exceeded')
    manifest=pd.read_csv(root/'data/manifests/pcb1_manifest.csv').fillna('')
    fit=manifest[manifest.split=='fit'].reset_index(drop=True);cal_members=manifest[manifest.split=='calibration'];test=manifest[manifest.split=='test']
    require((len(fit),len(cal_members),len(test))==(723,181,200),'Partition counts differ')
    require(fit.label.eq('normal').all() and cal_members.label.eq('normal').all(),'Anomalies in normal partition')
    require(set(fit.image_id).isdisjoint(set(cal_members.image_id)|set(test.image_id)),'Partition ID leakage')
    for row in manifest.itertuples():
        require(digest(root/'data/raw'/row.image_path)==row.sha256,'Raw image hash differs')
        if row.mask_path:require(digest(root/'data/raw'/row.mask_path)==row.mask_sha256,'Raw mask hash differs')
    table=pd.read_csv(out/'predictions.csv');cal=pd.read_csv(out/'calibration_predictions.csv')
    require(table.image_id.tolist()==test.image_id.tolist() and cal.image_id.tolist()==cal_members.image_id.tolist(),'Prediction partition identities differ')
    require(table.label.tolist()==test.label.tolist() and table.image_id.is_unique,'Saved labels/membership differ')
    thresholds=json.loads((out/'calibration.json').read_text());metrics=json.loads((out/'metrics.json').read_text())
    require(thresholds['comparison']=='>' and thresholds['quantile_method']=='higher' and thresholds['normal_calibration_count']==181,'Calibration policy differs')
    sorted_scores=np.sort(cal.score.to_numpy());image_threshold=float(sorted_scores[int(np.ceil(.95*180))])
    close(image_threshold,thresholds['image_threshold'],'Image normal quantile differs')
    cmap=np.load(out/'calibration_maps.npy',mmap_mode='r');require(cmap.shape==(181,256,256),'Calibration map denominator differs')
    rank=int(np.ceil(.99*(cmap.size-1)));pixel_threshold=float(np.partition(np.asarray(cmap).ravel().copy(),rank)[rank])
    close(pixel_threshold,thresholds['pixel_threshold'],'Pixel normal quantile differs')
    labels=table.label.eq('anomaly').to_numpy();scores=table.score.to_numpy();flags=scores>image_threshold
    require(np.array_equal(flags,table.detected.to_numpy()),'Saved strict decisions differ')
    calculated=direct_confusion(labels,scores,image_threshold)
    for key,value in calculated.items():close(metrics['image'][key],value,f'Image metric differs: {key}')
    close(metrics['image']['average_precision'],ranked_average_precision(labels,scores),'Image AP differs')
    close(metrics['image']['auroc'],pairwise_auroc(labels,scores),'Image AUROC differs')
    transforms=json.loads((out/'test_transforms.json').read_text())
    require(set(transforms)==set(test.image_id),'Transform membership differs')
    require(transforms==json.loads((control/'test_transforms.json').read_text()),'Matched geometry transforms changed')
    anomaly_ids=sorted(test.loc[test.label=='anomaly','image_id'])
    source_sample={anomaly_ids[index] for index in [0,50,99]}
    masks=[];maps=[];aps=[];intersection=union=peak=overlap=0
    for row,record in zip(test.itertuples(),table.to_dict('records')):
        model=np.load(out/'model_maps'/f'{row.image_id}.npy',allow_pickle=False)
        common=np.load(out/'anomaly_maps'/f'{row.image_id}.npy',allow_pickle=False)
        require(common.shape==(256,256) and np.isfinite(common).all() and np.isfinite(model).all(),'Invalid saved map')
        source,reconstructed=independent_inverse(model,transforms[row.image_id])
        require(np.array_equal(common,reconstructed),'Saved inverse-to-common mapping differs')
        require(source.shape==(row.height,row.width),'Source map geometry differs')
        mask=np.zeros((256,256),bool)
        if row.label=='anomaly':
            with Image.open(root/'data/raw'/row.mask_path) as image:
                raw_mask=np.asarray(image)>0
                mask=np.asarray(image.resize((256,256),Image.Resampling.NEAREST))>0
            x0,y0,x1,y1=transforms[row.image_id]['crop_box']
            close(record['source_annotation_outside_crop_fraction'],1-float(raw_mask[y0:y1,x0:x1].sum()/raw_mask.sum()),'Outside-crop annotation denominator differs')
            if row.image_id in source_sample:pixel_check(raw_mask,source,pixel_threshold,record,'source_')
        inter,uni,pp,ap=pixel_check(mask,common,pixel_threshold,record)
        masks.append(mask);maps.append(common);intersection+=inter;union+=uni
        if row.label=='anomaly':aps.append(ap);peak+=pp;overlap+=inter>0
    local=metrics['localization_common256'];require(local['n_images']==200 and local['n_pixels']==200*256*256 and local['includes_normal_images'],'Pooled localization denominator differs')
    require(local['intersection_pixels']==intersection and local['union_pixels']==union,'Global overlap arithmetic differs')
    close(local['pixel_iou'],intersection/union,'Global IoU differs')
    close(local['pixel_average_precision'],ranked_average_precision(np.asarray(masks),np.asarray(maps)),'Pooled pixel AP differs')
    require(local['positive_pixels']==int(np.asarray(masks).sum()),'Positive-pixel denominator differs')
    summary=metrics['anomaly_localization']['common256_']
    for key,value in [('median_per_image_pixel_ap',np.median(aps)),('q25',np.quantile(aps,.25)),('q75',np.quantile(aps,.75)),('peak_inside_count',peak),('overlap_count',overlap)]:close(summary[key],value,'Localization summary differs')
    del masks,maps,cmap
    meta=json.loads((out/'memory_metadata.json').read_text());bank=np.load(out/'memory.npy');selected=np.load(out/'selected_indices.npy');refs=meta['references'];grid=size//8;n=len(fit)*grid*grid
    require(bank.shape==(4096,384) and np.isfinite(bank).all(),'Scoring bank differs')
    require(selected.shape==(4096,) and np.issubdtype(selected.dtype,np.integer) and len(np.unique(selected))==4096 and (selected>=0).all() and (selected<n).all(),'Selection count/index uniqueness differs')
    require(meta['count']==4096 and meta['candidate_count']==n and meta['scoring_dimensions']==384 and meta['selection_projection_only'],'Memory population/representation differs')
    close(meta['fraction'],4096/n,'Memory sampling fraction differs')
    require(meta['fit_image_ids']==fit.image_id.tolist() and len(refs)==4096,'Memory fitting identity differs')
    for order,(position,ref) in enumerate(zip(selected,refs)):
        image_index,cell=divmod(int(position),grid*grid);r,c=divmod(cell,grid)
        require((ref['flat_index'],ref['image_id'],ref['row'],ref['column'],ref['memory_index'],ref['selection_order'])==(int(position),fit.iloc[image_index].image_id,r,c,order,order),'Reference coordinate/index mapping differs')
    config=protocol['config'];setup(root);extractor=DynamicExtractor()
    generator=torch.Generator(device='cpu').manual_seed(config['projection_seed'])
    projection=torch.randn(384,config['projection_dimensions'],generator=generator)/np.sqrt(config['projection_dimensions'])
    if size==512:
        engineering=json.loads((root/config['projected_cache_descriptor']).read_text())
        cache=root/engineering['cache_path'];require(digest(cache)==engineering['cache_sha256'],'Engineering cache differs')
        require(np.array_equal(selected[:64],engineering['pilot_selected_indices']),'Full-run64 prefix differs from engineering pilot')
        require(hashlib.sha256(projection.numpy().tobytes()).hexdigest()==engineering['projection_sha256'],'Projection matrix hash differs')
    else:cache=out/'cache/projected_features.npy'
    projected=np.load(cache,mmap_mode='r');require(projected.shape==(n,64) and projected.dtype==np.float32,'Projected population differs')
    if size==256:require(np.array_equal(selected[:16],independent_prefix(projected,seed=config['selection_seed'],anchors_count=config['initial_point_count'])),'Independent16-selection oracle differs')
    sampled_orders=[0,1024,2048,3072,4095]
    for order in sampled_orders:
        ref=refs[order];row=next(fit[fit.image_id==ref['image_id']].itertuples());tensor,transform=tensor_and_transform(root,row,size)
        feature=extractor(tensor[None])[0,:,ref['row'],ref['column']].numpy()
        require(np.allclose(feature,bank[order],rtol=1e-5,atol=1e-5),'Re-extracted scoring vector differs')
        require(np.allclose(feature@projection.numpy(),projected[ref['flat_index']],rtol=1e-4,atol=1e-4),'Projected reference cache differs')
    receipt={'reviewed_at_utc':now(),'size':size,'passed':True,'review_code_sha256':digest(__file__),
        'complete_sha256':digest(out/'complete.json'),'preserved_control_protocol_sha256':digest(control/'protocol.json'),
        'all_source_output_prerequisite_hashes_checked':True,'matched_control_config_unchanged':True,
        'normal_quantile_ranks_verified':True,'all_200_flags_image_ap_auroc_confusion_verified':True,
        'all_100_common_pixel_ap_and_all_200_inverse_mapping_verified':True,'pooled_common_pixel_ap_verified':True,
        'source_resolution_pixel_metrics_sample_verified':sorted(source_sample),'source_metrics_not_all_independently_recomputed':True,
        'selected_4096_unique_fitting_indices_and_all_coordinates_verified':True,
        'reextracted_vector_and_projection_orders_verified':sampled_orders,
        'selection_prefix_check':'Engineering64 prefix identity' if size==512 else 'Independent NumPyfloat32 first16 oracle',
        'full_4096_selector_not_rerun':True,'pcb2_access':False}
    write_new(out/'independent_review.json',receipt)
    print(json.dumps(receipt,indent=2),flush=True)
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',default='.')
    parser.add_argument('--size',type=int,choices=[256,512],required=True)
    args=parser.parse_args();verify(args.root,args.size)

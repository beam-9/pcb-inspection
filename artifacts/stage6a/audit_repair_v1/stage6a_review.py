"""Separate computational audit of Stage6A; no separate human/agent review implied."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageOps
from scipy.spatial.distance import cdist
from sklearn.metrics import average_precision_score
from .guard import digest, now, write_new


def verify(root):
    root=Path(root).resolve(); out=root/'artifacts/stage6a'
    read=lambda path:json.loads(Path(path).read_text())
    protocol=read(out/'protocol.json'); receipt=read(out/'extraction_complete.json')
    assert digest(out/'protocol.json')==read(out/'freeze_receipt.json')['protocol_sha256']
    for name, expected in protocol['frozen_files'].items(): assert digest(root/name)==expected,name
    for field in ['outputs','cache_outputs']:
        for name, expected in receipt[field].items(): assert digest(root/name)==expected,name
    prior=read(out/'prior_tracked_identity.json')
    navigation=['README.md','docs/journey/README.md','docs/journey/decision_log.md']
    for name, expected in prior.items():
        path=out/'history_navigation'/Path(name).name if name in navigation else root/name
        assert digest(path)==expected,name
    manifest=pd.read_csv(root/'artifacts/stage4/confirmation_data/test_manifest.csv').set_index('image_id')
    targets=pd.read_csv(out/'target_manifest.csv').set_index('image_id')
    frame=pd.read_csv(out/'per_recipe_diagnostics.csv',float_precision='round_trip').set_index(['recipe','image_id'])
    case=pd.read_csv(out/'case_diagnosis.csv').set_index('image_id')
    distances=pd.read_csv(out/'feature_distance.csv',float_precision='round_trip').set_index(['recipe','image_id','query_id'])
    checks=[]
    def same(actual,expected): assert np.isclose(actual,expected,rtol=0,atol=1e-12),(actual,expected)
    for recipe,stage,base,size in [('d1','stage5b','pcb2_d1_primary',256),('d2','stage5c','pcb2_d2_secondary',512)]:
        folder=root/'artifacts/stage4'/base
        bank=np.load(root/read(folder/'array_paths.json')['memory']).astype(np.float64)
        transforms=read(folder/'test_transforms.json'); paths=read(root/'artifacts'/stage/'array_paths.json')
        threshold=read(folder/'calibration.json')['image_threshold']; pt=read(folder/'calibration.json')['pixel_threshold']
        for identity,target in targets.iterrows():
            a=np.load(root/f'data/cache/stage6a/{recipe}_{identity}.npz'); scores=a['scores']; gt=a['gt']; t=transforms[identity]
            row=frame.loc[(recipe,identity)]; source=manifest.loc[identity]
            with Image.open(root/source.mask_path) as im: mask=np.asarray(ImageOps.exif_transpose(im).convert('L'))>0
            x0,y0,x1,y1=t['crop_box']; crop=mask[y0:y1,x0:x1]
            if target.pose_label=='reversed_180':crop=crop[::-1,::-1]
            projected=np.zeros((size,size),bool)
            resized=np.asarray(Image.fromarray(crop).resize((t['content_width'],t['content_height']),Image.Resampling.NEAREST))
            py,px=t['pad_y'],t['pad_x'];projected[py:py+t['content_height'],px:px+t['content_width']]=resized
            independent_gt=np.array([[projected[r:r+8,c:c+8].any() for c in range(0,size,8)] for r in range(0,size,8)])
            assert np.array_equal(gt,independent_gt)
            exact=np.sort(cdist(a['check_query'].astype(np.float64),bank),axis=1)[:,:5]
            error=float(abs(exact-a['top5'][a['check_ids']]).max());assert error<=1e-5
            flat=scores.ravel(); inside=gt.ravel(); order=sorted(range(len(flat)),key=lambda i:(-float(flat[i]),i))
            first=next(rank for rank,index in enumerate(order,1) if inside[index])
            assert row.first_gt_patch_rank==first
            same(row.max_native_patch_score,float(flat.max()));same(row.max_GT_patch_score,float(flat[inside].max()))
            same(row.max_outside_GT_patch_score,float(flat[~inside].max()))
            same(row.gt_max_ratio,float(flat[inside].max())/threshold)
            assert row.top_score_patch_inside_GT==bool(inside[order[0]])
            for k in [1,3,5,10]:same(row[f'top_{k}_mean'],float(np.mean(flat[order[:k]])))
            for k in [5,10,20]:same(row[f'top_{k}_gt_fraction'],sum(inside[order[:k]])/len(order[:k]))
            subset=distances.loc[(recipe,identity)]
            assert set(subset.index)==set(np.flatnonzero(inside))
            for qi,item in subset.iterrows():
                same(item.nearest_reference_distance,float(flat[qi]));same(item.median_top5_reference_distance,float(np.median(a['top5'][qi])))
            common=np.load(root/paths['anomaly_maps']/f'{identity}.npy')
            with Image.open(root/source.mask_path) as im:cm=np.asarray(ImageOps.exif_transpose(im).convert('L').resize((256,256),Image.Resampling.NEAREST))>0
            positive=common>pt
            assert row.FP_pixels==int((positive&~cm).sum())
            assert row.GT_intersection_pixels==int((positive&cm).sum())
            same(row.IoU,(positive&cm).sum()/(positive|cm).sum())
            same(row.common_pixel_ap,float(average_precision_score(cm.ravel(),common.ravel())))
            assert row.detected==(row.image_score>threshold)
            same(row.score_divided_by_threshold,row.image_score/threshold)
            same(case.loc[identity,f'{recipe}_gt_max_ratio'],row.gt_max_ratio)
            same(case.loc[identity,f'{recipe}_pixel_ap'],row.common_pixel_ap)
            checks.append({'image_id':identity,'recipe':recipe,'float64_top5_error':error,'first_gt_rank':first})
    # Cohort completeness against the full frozen evaluation population.
    allcases=pd.read_csv(root/'artifacts/stage5c/predictions.csv')
    poses=pd.read_csv(root/'artifacts/stage5a/pose/pose_labels.csv').set_index('image_id').pose_label
    missing=allcases[allcases.defect_types.fillna('[]').map(lambda s:'missing' in json.loads(s)) & allcases.image_id.map(poses).eq('canonical')]
    small=allcases[allcases.reference_area_band.isin(['R1','R2'])]
    assert set(targets.index)==set(missing.image_id)|set(small.image_id)|{'bfebbd19caf4dad38fd66eab'}
    result={'passed':True,'reviewed_at_utc':now(),'review_type':'separate computational implementation; same author, no external reviewer',
            'case_count':len(targets),'canonical_missing_cases':len(missing),'canonical_missing_misses':int((~missing.detected).sum()),
            'small_cases':len(small),'small_misses':int((~small.detected).sum()),'prior_tracked_files_verified':len(prior),
            'checks':checks,'review_code_sha256':digest(Path(__file__))}
    write_new(out/'independent_review.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');args=p.parse_args();verify(args.root)

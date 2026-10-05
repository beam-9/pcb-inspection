"""Post-confirmation saved-map diagnosis; no feature extraction or detector changes."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from scipy.ndimage import label, map_coordinates
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from .guard import digest, now, write_new

EXPECTED_FP = {256: 510336, 512: 325593}
POLICY = {
    'stage': 'Post-confirmation PCB2 development diagnosis', 'detector_changed': False,
    'grid': '4x4 normalized full crop, not board segmentation; no pose normalization',
    'native_center': '(column+.5-pad_x)/content_width and analogous row',
    'common_center': '((column+.5)*source_width/256-crop_x0)/crop_width and analogous row',
    'connectivity': '8-connected, scipy.ndimage.label with 3x3 ones, native content only',
    'normalized_aggregate': '64x64 crop raster; native score bilinear, original source GT nearest pixel-center sample',
    'full_fp_check': 'All200 common256 fullsource images; outsidecrop retained in totals',
    'small': 'Fixed R1/R2 common256 area bands; diagnostic categories may overlap',
    'small_low_response': 'Maximum saved common map score inside GT <= frozen pixel threshold; not proof of representation failure',
    'small_competing': 'Saved common map maximum outside GT > maximum inside GT',
    'small_threshold': 'Image unflagged despite GT map maximum above pixel threshold; image uses patch max, map maxima are supplemental',
    'resolution_case': 'D1missD2hit OR common pixel AP gain>=.10; flag contrast not cause',
    'reverse_contrast': 'D1hitD2miss OR common pixel AP decline>=.10',
}


def crop_coordinates(transform, height, width, native):
    t = transform; x0,y0,x1,y1 = t['crop_box']
    if native:
        u = (np.arange(width)+.5-t['pad_x'])/t['content_width']
        v = (np.arange(height)+.5-t['pad_y'])/t['content_height']
    else:
        u = ((np.arange(width)+.5)*t['source_width']/width-x0)/(x1-x0)
        v = ((np.arange(height)+.5)*t['source_height']/height-y0)/(y1-y0)
    uu,vv = np.meshgrid(u,v)
    inside = (uu>=0)&(uu<1)&(vv>=0)&(vv<1)
    cells = np.floor(vv*4).astype(int)*4+np.floor(uu*4).astype(int)
    return uu,vv,inside,cells


def source_gt_at(raw, transform, u, v):
    x0,y0,x1,y1 = transform['crop_box']
    x = np.clip(np.floor(x0+u*(x1-x0)).astype(int),0,raw.shape[1]-1)
    y = np.clip(np.floor(y0+v*(y1-y0)).astype(int),0,raw.shape[0]-1)
    return raw[y,x]


def spread(positive):
    components = int(label(positive, structure=np.ones((3,3),int))[1])
    ys,xs = np.where(positive)
    box = int((ys.max()-ys.min()+1)*(xs.max()-xs.min()+1)) if len(ys) else 0
    return components,box,box/positive.size


def grid_rows(image_id, recipe, view, scores, gt, threshold, inside, cells):
    positive = scores>threshold
    rows=[]
    for cell in range(16):
        region=inside&(cells==cell);n=int(region.sum());g=gt[region];p=positive[region]
        intersection=int((g&p).sum());union=int((g|p).sum());fp=int((p&~g).sum())
        rows.append(dict(image_id=image_id,recipe=recipe,view=view,grid_row=cell//4,grid_column=cell%4,
                         denominator_pixels=n,gt_positive_pixels=int(g.sum()),predicted_positive_pixels=int(p.sum()),
                         intersection_pixels=intersection,union_pixels=union,false_positive_pixels=fp,
                         score_sum=float(scores[region].astype(np.float64).sum()),mean_raw_score=float(scores[region].mean()) if n else None,
                         threshold_exceedance_fraction=float(p.mean()) if n else None,fp_frequency=fp/n if n else None,
                         fp_rate_on_negative_pixels=fp/int((~g).sum()) if (~g).sum() else None))
    return rows


def resampled_crop(model,raw_gt,t,n=64):
    u,v=np.meshgrid((np.arange(n)+.5)/n,(np.arange(n)+.5)/n)
    x=t['pad_x']+u*t['content_width']-.5;y=t['pad_y']+v*t['content_height']-.5
    # Clamp to content centers: no letterbox padding enters these aggregate scores.
    x=np.clip(x,t['pad_x'],t['pad_x']+t['content_width']-1)
    y=np.clip(y,t['pad_y'],t['pad_y']+t['content_height']-1)
    score=map_coordinates(model,[y,x],order=1,mode='nearest',prefilter=False)
    return score,source_gt_at(raw_gt,t,u,v)


def group_masks(table):
    return {'all_normals':table.label.eq('normal'), 'all_anomalies':table.label.eq('anomaly'),
            **{f'pose_{pose}':table.pose_label.eq(pose) for pose in ['canonical','reversed_180','uncertain']},
            'missing_anomalies':table.label.eq('anomaly')&table.missing_component,
            'nonmissing_anomalies':table.label.eq('anomaly')&~table.missing_component,
            **{f'pose_{pose}_anomalies':table.pose_label.eq(pose)&table.label.eq('anomaly') for pose in ['canonical','reversed_180','uncertain']}}


def plot_saved_aggregates(root):
    """Figures from saved aggregate arrays, with numerical scales for every column."""
    root=Path(root);out=root/'artifacts/stage5a/broad_maps'
    table=pd.read_csv(out/'map_spread.csv')
    scales={}
    for recipe,part in table.groupby('recipe'):
        groups=list(group_masks(part))
        directory=out/'aggregate_maps'/recipe
        raw_max=max(float(np.nanmax(np.load(directory/f'{group}_mean_raw_score.npy'))) for group in groups)
        scales[recipe]={'mean_raw_score':[0,raw_max],'threshold_frequency':[0,1],'fp_frequency':[0,1]}
        fig,axes=plt.subplots(len(groups),3,figsize=(11,23),constrained_layout=True)
        artists=[]
        for index,(group,selected) in enumerate(group_masks(part).items()):
            for column,kind in enumerate(['mean_raw_score','threshold_frequency','fp_frequency']):
                array=np.load(directory/f'{group}_{kind}.npy')
                artist=axes[index,column].imshow(array,origin='upper',vmin=0,vmax=raw_max if column==0 else 1)
                if index==0:artists.append(artist)
                axes[index,column].set_title(f'{group} n={int(selected.sum())}\n{kind}',fontsize=8)
                axes[index,column].set_xticks([]);axes[index,column].set_yticks([])
        for column,artist in enumerate(artists):
            cb=fig.colorbar(artist,ax=axes[:,column],orientation='horizontal',fraction=.012,pad=.005)
            cb.set_label('Mean raw anomaly score' if column==0 else ('Exceedance probability across selected images' if column==1 else 'False-positive frequency across selected images'),fontsize=8)
        fig.suptitle(f'{recipe}: normalized crop; padding excluded, no pose alignment. Shared numeric scale per column',fontsize=11)
        fig.savefig(out/f'{recipe}_aggregate_maps.png',dpi=140);plt.close(fig)
    return scales


def main(root,pose_path):
    root=Path(root).resolve();out=root/'artifacts/stage5a/broad_maps';small=root/'artifacts/stage5a/small_defects'
    receipt_path=root/'artifacts/stage5a/pose/labels_final.json'
    pose_receipt=json.loads(receipt_path.read_text())
    if pose_receipt['label_sha256']!=digest(root/pose_path) or pose_receipt['outcome_comparison_started']:raise ValueError('Final outcome-independent pose labels required')
    out.mkdir(parents=True,exist_ok=False);small.mkdir(parents=True,exist_ok=False)
    pose=pd.read_csv(root/pose_path,keep_default_na=False)
    if not pose.image_id.is_unique:raise ValueError('Pose IDs must be unique')
    labels=dict(zip(pose.image_id,pose.pose_label))
    # Explicitly retain other/uncertain label under one analysis group, not drop rows.
    labels={key:('uncertain' if value in ['other','other / uncertain','other_uncertain','uncertain'] else value) for key,value in labels.items()}
    if not set(labels.values())<={'canonical','reversed_180','uncertain'}:raise ValueError('Unknown pose label')
    write_new(out/'diagnostic_policy.json',{**POLICY,'declared_at_utc':now(),'pose_labels_sha256':digest(root/pose_path),'code_sha256':digest(__file__)})
    records=[];grids=[];small_rows=[];inputs={str(pose_path):digest(root/pose_path),str(receipt_path.relative_to(root)):digest(receipt_path)}
    for size,run in [(256,'pcb2_d1_primary'),(512,'pcb2_d2_secondary')]:
        base=root/'artifacts/stage4'/run;recipe='D1' if size==256 else 'D2'
        done=json.loads((base/'complete.json').read_text());review=json.loads((base/'independent_review.json').read_text())
        if not review['passed'] or review['complete_sha256']!=digest(base/'complete.json'):raise ValueError('Reviewed Stage4 outputs required')
        for name,expected in done['outputs'].items():
            if digest(root/name)!=expected:raise ValueError(f'Frozen output changed: {name}')
        for name in ['complete.json','independent_review.json','predictions.csv','test_transforms.json','calibration.json']:
            inputs[str((base/name).relative_to(root))]=digest(base/name)
        table=pd.read_csv(base/'predictions.csv',keep_default_na=False)
        table['pixel_ap']=pd.to_numeric(table['pixel_ap'],errors='coerce')
        manifest=pd.read_csv(base/'confirmation_manifest.csv',keep_default_na=False).set_index('image_id')
        if len(table)!=200 or not set(table.image_id).issubset(set(labels)):raise ValueError('Pose/evaluation membership differs')
        transforms=json.loads((base/'test_transforms.json').read_text());paths=json.loads((base/'array_paths.json').read_text())
        threshold=json.loads((base/'calibration.json').read_text());pixel_t=threshold['pixel_threshold'];image_t=threshold['image_threshold']
        aggregates=[];gt_aggregates=[];local=[]
        for row in table.itertuples():
            source=manifest.loc[row.image_id];t=transforms[row.image_id]
            model=np.load(root/paths['model_maps']/f'{row.image_id}.npy',allow_pickle=False)
            common=np.load(root/paths['anomaly_maps']/f'{row.image_id}.npy',allow_pickle=False)
            if row.label=='anomaly':
                if digest(root/source.mask_path)!=source.mask_sha256:raise ValueError('GT hash differs')
                with Image.open(root/source.mask_path) as im:
                    raw=np.asarray(im)>0;gt=np.asarray(im.resize((256,256),Image.Resampling.NEAREST))>0
            else:raw=np.zeros((t['source_height'],t['source_width']),bool);gt=np.zeros((256,256),bool)
            positive=common>pixel_t;fp=int((positive&~gt).sum());inter=int((positive&gt).sum());union=int((positive|gt).sum())
            if inter!=row.intersection or union!=row.union or bool(row.detected)!=(row.score>image_t):raise ValueError('Frozen arithmetic differs')
            u,v,inside,cells=crop_coordinates(t,*model.shape,True);native_gt=source_gt_at(raw,t,u,v)
            grids+=grid_rows(row.image_id,recipe,'native_content',model,native_gt,pixel_t,inside,cells)
            _,_,common_inside,common_cells=crop_coordinates(t,256,256,False)
            common_rows=grid_rows(row.image_id,recipe,'common256_crop',common,gt,pixel_t,common_inside,common_cells)
            if sum(r['false_positive_pixels'] for r in common_rows)+int((positive&~gt&~common_inside).sum())!=fp:raise ValueError('Cropgrid plus outside FP mismatch')
            grids+=common_rows
            content=model[t['pad_y']:t['pad_y']+t['content_height'],t['pad_x']:t['pad_x']+t['content_width']]
            components,bbox,bbox_fraction=spread(content>pixel_t)
            source_labels=json.loads(row.defect_types) if row.label=='anomaly' else []
            rec=dict(image_id=row.image_id,recipe=recipe,label=row.label,pose_label=labels[row.image_id],missing_component='missing' in source_labels,
                     source_labels=json.dumps(source_labels),size_band=row.reference_area_band if row.label=='anomaly' else '',
                     image_score=row.score,image_threshold=image_t,pixel_threshold=pixel_t,detected=bool(row.detected),pixel_ap=row.pixel_ap if row.label=='anomaly' else None,
                     common_mask_area_fraction=float(gt.mean()),common_gt_pixels=int(gt.sum()),common_fp_pixels=fp,common_intersection_pixels=inter,
                     common_union_pixels=union,common_predicted_positive_pixels=int(positive.sum()),common_denominator_pixels=common.size,
                     common_crop_denominator_pixels=int(common_inside.sum()),common_outsidecrop_fp_pixels=int((positive&~gt&~common_inside).sum()),
                     native_crop_denominator_pixels=content.size,fraction_of_crop_above_threshold=float((content>pixel_t).mean()),
                     native_positive_components_8=components,native_positive_bbox_area=bbox,native_positive_bbox_crop_fraction=bbox_fraction)
            records.append(rec);local.append(rec)
            normalized,ngt=resampled_crop(model,raw,t);aggregates.append(normalized);gt_aggregates.append(ngt)
            if row.label=='anomaly' and row.reference_area_band in ['R1','R2']:
                inside_scores=common[gt];outside=common[~gt];maximum=float(inside_scores.max());outside_max=float(outside.max())
                low=maximum<=pixel_t;competing=outside_max>maximum;pixel_evidence_unflagged=not row.detected and maximum>pixel_t
                categories=[]
                if low:categories.append('low_saved_map_response_in_gt')
                if competing:categories.append('higher_response_outside_gt')
                if pixel_evidence_unflagged:categories.append('pixel_evidence_but_image_unflagged')
                if not categories:categories.append('unclear_or_mixed')
                small_rows.append(dict(image_id=row.image_id,recipe=recipe,pose_label=labels[row.image_id],source_labels=json.dumps(source_labels),size_band=row.reference_area_band,
                    detected=bool(row.detected),image_score=row.score,image_threshold=image_t,pixel_threshold=pixel_t,pixel_ap=row.pixel_ap,
                    gt_map_max=maximum,gt_map_mean=float(inside_scores.mean()),gt_map_q90=float(np.quantile(inside_scores,.9)),
                    outside_map_max=outside_max,outside_map_mean=float(outside.mean()),gt_fraction_above_pixel_threshold=float((inside_scores>pixel_t).mean()),
                    gt_max_minus_pixel_threshold=maximum-pixel_t,gt_map_max_minus_image_threshold=maximum-image_t,
                    diagnostic_categories=json.dumps(categories),interpretation='Saved-map evidence only; image score is patchmax and map max may be lower'))
        local=pd.DataFrame(local)
        if local.common_fp_pixels.sum()!=EXPECTED_FP[size]:raise ValueError('Full common FP total does not match Stage4')
        arrays=np.asarray(aggregates);raw_gt=np.asarray(gt_aggregates);groupdir=out/'aggregate_maps'/recipe;groupdir.mkdir(parents=True)
        for index,(group,selected) in enumerate(group_masks(local).items()):
            n=int(selected.sum())
            for column,(kind,data) in enumerate([('mean_raw_score',arrays),('threshold_frequency',arrays>pixel_t),('fp_frequency',(arrays>pixel_t)&~raw_gt)]):
                mean=data[selected.to_numpy()].mean(axis=0) if n else np.full((64,64),np.nan)
                np.save(groupdir/f'{group}_{kind}.npy',mean)
    spread_table=pd.DataFrame(records);grid=pd.DataFrame(grids)
    spread_table.to_csv(out/'map_spread.csv',index=False);grid.to_csv(out/'per_image_grid_counts.csv',index=False)
    plot_scales=plot_saved_aggregates(root)
    merged=grid.merge(spread_table[['image_id','recipe','label','pose_label','missing_component']],on=['image_id','recipe'],validate='many_to_one')
    summaries=[]
    for recipe,subset in merged.groupby('recipe'):
        for group,selected in group_masks(subset).items():
            for (view,r,c),part in subset[selected].groupby(['view','grid_row','grid_column']):
                n=int(part.denominator_pixels.sum());negative=n-int(part.gt_positive_pixels.sum());fp=int(part.false_positive_pixels.sum())
                summaries.append(dict(recipe=recipe,group=group,view=view,grid_row=r,grid_column=c,n_images=part.image_id.nunique(),n_normals=part.loc[part.label=='normal','image_id'].nunique(),n_anomalies=part.loc[part.label=='anomaly','image_id'].nunique(),denominator_pixels=n,
                     false_positive_pixels=fp,gt_positive_pixels=int(part.gt_positive_pixels.sum()),intersection_pixels=int(part.intersection_pixels.sum()),union_pixels=int(part.union_pixels.sum()),
                     mean_raw_score=float(part.score_sum.sum()/n),threshold_exceedance_fraction=float(part.predicted_positive_pixels.sum()/n),fp_frequency=fp/n,fp_rate_on_negative_pixels=fp/negative if negative else None))
    pd.DataFrame(summaries).to_csv(out/'grid_summary.csv',index=False)
    cases=pd.DataFrame(small_rows)
    d1=cases[cases.recipe=='D1'].set_index('image_id');d2=cases[cases.recipe=='D2'].set_index('image_id')
    gain=d2.pixel_ap-d1.pixel_ap;rescue=(~d1.detected)&d2.detected;reverse=d1.detected&(~d2.detected)
    cases['paired_d2_minus_d1_pixel_ap']=cases.image_id.map(gain)
    cases['paired_d1miss_d2hit']=cases.image_id.map(rescue)
    cases['resolution_sensitive_contrast']=cases.image_id.map(rescue|(gain>=.1))
    cases['reverse_contrast']=cases.image_id.map(reverse|(gain<=-.1))
    cases.to_csv(small/'failure_decomposition.csv',index=False)
    fig,axes=plt.subplots(1,2,figsize=(11,4),constrained_layout=True)
    axes[0].scatter(d1.pixel_ap,d2.pixel_ap);axes[0].plot([0,1],[0,1],color='gray');axes[0].set(xlabel='D1 common pixel AP',ylabel='D2 common pixel AP',title='All R1/R2 cases, paired')
    for recipe,part in cases.groupby('recipe'):axes[1].scatter(part.gt_max_minus_pixel_threshold,part.outside_map_max-part.gt_map_max,label=recipe,alpha=.7)
    axes[1].axvline(0,color='gray');axes[1].axhline(0,color='gray');axes[1].set(xlabel='GT map maximum minus frozen pixel threshold',ylabel='Outside maximum minus GT maximum',title='Map response versus competition');axes[1].legend()
    fig.savefig(small/'small_case_decomposition.png',dpi=160);plt.close(fig)
    summary={'completed_at_utc':now(),'scope':POLICY['stage'],'detector_changed':False,'images_per_recipe':200,'map_spread_rows':len(spread_table),'grid_rows':len(grid),'small_rows':len(cases),
             'fp_total_checks':{recipe:int(part.common_fp_pixels.sum()) for recipe,part in spread_table.groupby('recipe')},
             'outside_crop_fp':{recipe:int(part.common_outsidecrop_fp_pixels.sum()) for recipe,part in spread_table.groupby('recipe')},
             'small_unique_images':int(cases.image_id.nunique()),'paired_d1miss_d2hit':int(rescue.sum()),'resolution_contrasts':int((rescue|(gain>=.1)).sum()),
             'aggregate_plot_scales':plot_scales,'inputs':inputs,'outputs':{str(p.relative_to(root)):digest(p) for folder in [out,small] for p in folder.rglob('*') if p.is_file()}}
    write_new(out/'complete.json',summary)
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',default='.');parser.add_argument('--pose',default='artifacts/stage5a/pose/pose_labels.csv')
    args=parser.parse_args();print(json.dumps(main(args.root,args.pose),indent=2))

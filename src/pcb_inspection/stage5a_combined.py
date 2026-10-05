"""Join saved post-confirmation diagnostic tables, without detector inference."""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
import pandas as pd


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def keyed(frame,name):
    if frame.image_id.isna().any() or frame.image_id.duplicated().any():raise ValueError(f'{name}: nonunique/missing image ID')
    return frame.set_index('image_id')


def combine(root):
    root=Path(root).resolve();base=root/'artifacts/stage5a';out=base/'combined';out.mkdir(exist_ok=True)
    if (base/'diagnostics.json').exists():raise FileExistsError('Completed diagnostic snapshot is immutable')
    paths=[base/'pose/pose_labels.csv',base/'pose/labels_final.json',base/'broad_maps/map_spread.csv',base/'missing_component/missing_cases.csv']
    pose=keyed(pd.read_csv(paths[0]),'pose');maps=pd.read_csv(paths[2]);maps['pixel_ap']=pd.to_numeric(maps.pixel_ap,errors='coerce');missing=keyed(pd.read_csv(paths[3]),'missing')
    records=[]
    for short,run in [('d1','pcb2_d1_primary'),('d2','pcb2_d2_secondary')]:
        p=root/f'artifacts/stage4/{run}/predictions.csv';paths.append(p);frame=keyed(pd.read_csv(p),'predictions');frame['pixel_ap']=pd.to_numeric(frame.pixel_ap,errors='coerce');frame['defect_types']=frame.defect_types.fillna('[]')
        m=keyed(maps[maps.recipe.eq(short.upper())],'map spread')
        if set(frame.index)!=set(m.index) or not set(frame.index).issubset(set(pose.index)):raise ValueError('Diagnostic population mismatch')
        if short=='d1':
            result=frame[['label','defect_types','mask_area_fraction','reference_area_band']].rename(columns={'label':'normal_or_anomaly','defect_types':'source_labels','reference_area_band':'size_band'})
            result['mask_area_pixels']=(result.mask_area_fraction*65536).round().astype(int)
            result['pose_label']=pose.loc[result.index,'pose_label'];result['missing_component']=result.source_labels.map(lambda s:'missing' in json.loads(s))
        else:
            assert frame.index.equals(result.index)
            assert np.array_equal(frame.label,result.normal_or_anomaly)
        for old,new in [('detected','flag'),('score','image_score'),('pixel_ap','pixel_ap'),('peak_inside','peak_inside'),('overlap','any_overlap')]:result[f'{short}_{new}']=frame[old]
        for col in ['common_fp_pixels','common_intersection_pixels','common_union_pixels','common_predicted_positive_pixels','fraction_of_crop_above_threshold','native_positive_components_8','native_positive_bbox_crop_fraction']:
            result[f'{short}_{col}']=m.loc[result.index,col]
        assert np.array_equal(frame.detected,m.loc[frame.index,'detected'])
        assert np.allclose(frame.score,m.loc[frame.index,'image_score'],rtol=0,atol=1e-12)
        assert np.allclose(frame.pixel_ap.fillna(-1),m.loc[frame.index,'pixel_ap'].fillna(-1),rtol=0,atol=1e-12)
        metrics=json.loads((root/f'artifacts/stage4/{run}/metrics.json').read_text());loc=metrics['localization_common256']
        assert int(result[f'{short}_common_fp_pixels'].sum())==loc['union_pixels']-loc['positive_pixels']
        assert int(result[f'{short}_common_intersection_pixels'].sum())==loc['intersection_pixels']
        assert int(result[f'{short}_common_union_pixels'].sum())==loc['union_pixels']
    assert len(result)==200 and result.missing_component.sum()==19
    for col in missing.columns:
        if col.startswith(('d1_nn_','d2_nn_','d1_cross_location_','d2_cross_location_')):result[col]=missing[col].reindex(result.index)
    result['diagnostic_notes']=np.where(result.missing_component,'NN mask is union of all source annotation regions; source type is image-level.','')
    result.loc[result.pose_label.eq('uncertain'),'diagnostic_notes']+=' Pose cue uncertain; visually canonical layouts with damaged connector cue; not verified unusual pose.'
    result.loc[result.normal_or_anomaly.eq('normal'),['mask_area_fraction','mask_area_pixels','size_band']]=np.nan
    for short in ['d1','d2']:
        for field in ['peak_inside','any_overlap']:
            col=f'{short}_{field}';result[col]=result[col].astype('boolean');result.loc[result.normal_or_anomaly.eq('normal'),col]=pd.NA
    result.reset_index().to_csv(out/'per_image_diagnostics.csv',index=False)
    result.reset_index().assign(outcome_group=lambda f:np.select([~f.d1_flag&~f.d2_flag,~f.d1_flag&f.d2_flag,f.d1_flag&~f.d2_flag],['M1 both miss','M2 D1 miss D2 hit','M4 D1 hit D2 miss'],default='M3 both hit')).query('missing_component').to_csv(out/'missing_paired_cases.csv',index=False)
    summaries=[]
    for short in ['d1','d2']:
        for pose_label in ['canonical','reversed_180','uncertain']:
            for hit in [False,True]:
                sub=result[result.missing_component&result.pose_label.eq(pose_label)&result[f'{short}_flag'].eq(hit)]
                row={'recipe':short.upper(),'pose_label':pose_label,'missing_detected':hit,'count':len(sub),'median_pixel_ap':sub[f'{short}_pixel_ap'].median(),'median_fp_pixels':sub[f'{short}_common_fp_pixels'].median()}
                for col in [f'{short}_nn_median_distance',f'{short}_nn_spatial_median',f'{short}_cross_location_r010']:
                    if col in sub:row[col.removeprefix(short+'_')]=sub[col].median()
                summaries.append(row)
    pd.DataFrame(summaries).to_csv(out/'pose_x_missing.csv',index=False)
    summaries=[]
    for short in ['d1','d2']:
        for (label,pl),sub in result.groupby(['normal_or_anomaly','pose_label']):
            summaries.append({'recipe':short.upper(),'normal_or_anomaly':label,'pose_label':pl,'count':len(sub),'median_map_spread':sub[f'{short}_fraction_of_crop_above_threshold'].median(),'median_fp_pixels':sub[f'{short}_common_fp_pixels'].median(),'total_fp_pixels':sub[f'{short}_common_fp_pixels'].sum(),'median_pixel_ap':sub[f'{short}_pixel_ap'].median()})
    pd.DataFrame(summaries).to_csv(out/'pose_x_map_spread.csv',index=False)
    summaries=[]
    for short in ['d1','d2']:
        for band in ['R1','R2','R3','R4']:
            for ismissing in [False,True]:
                sub=result[result.normal_or_anomaly.eq('anomaly')&result.size_band.eq(band)&result.missing_component.eq(ismissing)]
                summaries.append({'recipe':short.upper(),'size_band':band,'missing_component':ismissing,'count':len(sub),'detected':int(sub[f'{short}_flag'].sum()),'recall':sub[f'{short}_flag'].mean(),'median_mask_area_pixels':sub.mask_area_pixels.median(),'median_pixel_ap':sub[f'{short}_pixel_ap'].median()})
    pd.DataFrame(summaries).to_csv(out/'size_x_missing.csv',index=False)
    meta={'new_detector_inference':False,'population':200,'missing_images':19,'source_identities':{str(p.relative_to(root)):sha(p) for p in paths},'combined_grain':'One evaluation image; nearest neighbor summaries separate per recipe, overlap-query top5 only; null on nonmissing images.','null_policy':'Undefined empty groups and nonapplicable anomaly/NN metrics are null, not zero.','checks':['uniqueIDs/exact200match','frozenflags/scores/pixelAP','commonFP/intersection/uniontotals','19missingimages'],'output_identities':{str(p.relative_to(out)):sha(p) for p in out.glob('*.csv')}}
    (out/'combined_metadata.json').write_text(json.dumps(meta,indent=2)+'\n');print('Combined diagnostic joins and metric reconciliation passed.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',default='.');combine(parser.parse_args().root)

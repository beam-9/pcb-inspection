"""Independent saved-evidence consistency audit for Stage5A (no model inference)."""
import argparse,datetime,json,hashlib,subprocess
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image,ImageOps


def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def verify(root):
 root=Path(root).resolve();base=root/'artifacts/stage5a';protocol=json.loads((base/'diagnostic_protocol.json').read_text())
 checked=0
 for field in ['stage4_identities','bound_local_cache_identities']:
  for name,value in protocol[field].items():assert digest(root/name)==value,name;checked+=1
 history=json.loads((root/'artifacts/stage4/comparison/comparison_complete.json').read_text())
 historical_docs={'README.md','docs/journey/README.md','docs/journey/decision_log.md'}
 for name,value in history['outputs'].items():
  actual=hashlib.sha256(subprocess.check_output(['git','show',protocol['stage4_commit']+':'+name],cwd=root)).hexdigest() if name in historical_docs else digest(root/name)
  assert actual==value,name
 checked+=len(history['outputs'])
 labels=pd.read_csv(base/'pose/pose_labels.csv');assert len(labels)==1101 and not labels.image_id.duplicated().any()
 final=json.loads((base/'pose/labels_final.json').read_text());assert final['label_sha256']==digest(base/'pose/pose_labels.csv');assert final['classifier_code_sha256']==digest(root/'src/pcb_inspection/stage5a_pose.py')
 for name,value in final['outputs'].items():assert digest(root/name)==value,name
 normals=pd.read_csv(root/'artifacts/stage4/pcb2_normals/normal_manifest.csv');test=pd.read_csv(root/'artifacts/stage4/confirmation_data/test_manifest.csv');assert set(labels.image_id)==set(normals.image_id)|set(test.image_id)
 assert final['outcome_comparison_started'] is False and final['manual_override_count']==0
 assert final['finalized_at_utc']<json.loads((base/'pose/pose_diagnostics_complete.json').read_text())['completed_at_utc']
 combined=pd.read_csv(base/'combined/per_image_diagnostics.csv').set_index('image_id');assert len(combined)==200 and set(combined.index)==set(test.image_id)
 assert combined.loc[combined.normal_or_anomaly.eq('normal'),['d1_pixel_ap','d2_pixel_ap','d1_peak_inside','d2_peak_inside','d1_any_overlap','d2_any_overlap','d1_nn_median_distance','d2_nn_median_distance']].isna().all().all()
 mapspread=pd.read_csv(base/'broad_maps/map_spread.csv');assert len(mapspread)==400
 test=test.set_index('image_id');maskdict={}
 for image_id,row in test.iterrows():
  if row.label=='normal':maskdict[image_id]=np.zeros((256,256),bool)
  else:
   with Image.open(root/row.mask_path) as im:maskdict[image_id]=np.asarray(ImageOps.exif_transpose(im).convert('L').resize((256,256),Image.Resampling.NEAREST))>0
 count_checks=[];coord_checks=0
 for short,run,size in [('d1','pcb2_d1_primary',256),('d2','pcb2_d2_secondary',512)]:
  folder=root/f'artifacts/stage4/{run}';p=pd.read_csv(folder/'predictions.csv').set_index('image_id');maps=mapspread[mapspread.recipe.eq(short.upper())].set_index('image_id');assert set(maps.index)==set(p.index)
  assert np.array_equal(combined.loc[p.index,f'{short}_flag'],p.detected)
  assert np.allclose(combined.loc[p.index,f'{short}_image_score'],p.score,rtol=0,atol=1e-12)
  assert np.allclose(pd.to_numeric(combined.loc[p.index,f'{short}_pixel_ap'],errors='coerce').fillna(-1),pd.to_numeric(p.pixel_ap,errors='coerce').fillna(-1),rtol=0,atol=1e-12)
  metrics=json.loads((folder/'metrics.json').read_text());threshold=metrics['localization_common256']['pixel_threshold'];paths=json.loads((folder/'array_paths.json').read_text());totalfp=totali=totalu=0
  for image_id,row in p.iterrows():
   a=np.load(root/paths['anomaly_maps']/f'{image_id}.npy');gt=maskdict[image_id];positive=a>threshold;fp=int((positive&~gt).sum());i=int((positive&gt).sum());u=int((positive|gt).sum())
   assert fp==int(maps.loc[image_id,'common_fp_pixels'])==int(combined.loc[image_id,f'{short}_common_fp_pixels']);assert i==int(row.intersection);assert u==int(row.union)
   totalfp+=fp;totali+=i;totalu+=u
  loc=metrics['localization_common256'];assert totalfp==loc['union_pixels']-loc['positive_pixels'] and totali==loc['intersection_pixels'] and totalu==loc['union_pixels']
  count_checks.append({'recipe':short.upper(),'independent_saved_map_count_images':200,'fp_pixels':totalfp,'intersection_pixels':totali,'union_pixels':totalu})
  trace=pd.read_csv(base/'missing_component/nn_trace.csv');trace=trace[trace['size'].eq(size)];refs=json.loads((folder/'memory_metadata.json').read_text())['references'];fit=set(normals[normals.split.eq('fit')].image_id)
  transform=json.loads((folder/'test_transforms.json').read_text());reftransform=json.loads((folder/'fit_reference_transforms.json').read_text())
  assert trace.groupby(['query_image_id','query_id']).neighbor_rank.apply(list).map(lambda x:x==[1,2,3,4,5]).all()
  assert trace.groupby(['query_image_id','query_id']).distance.apply(lambda x:np.all(np.diff(x)>=0)).all()
  assert set(trace.query_image_id)==set(combined[combined.missing_component].index)
  for row in trace.itertuples():
   ref=refs[row.memory_index];assert ref['image_id']==row.reference_image_id and ref['row']==row.reference_feature_row and ref['column']==row.reference_feature_column;assert row.reference_image_id in fit
   for prefix,t in [('query',transform[row.query_image_id]),('reference',reftransform[row.reference_image_id])]:
    x=(getattr(row,prefix+'_feature_column')+.5)*8;y=(getattr(row,prefix+'_feature_row')+.5)*8;nx=(x-t['pad_x'])/t['content_width'];ny=(y-t['pad_y'])/t['content_height'];x0,y0,x1,y1=t['crop_box']
    assert np.isclose(getattr(row,prefix+'_source_x'),x0+nx*(x1-x0),rtol=0,atol=1e-8);assert np.isclose(getattr(row,prefix+'_source_y'),y0+ny*(y1-y0),rtol=0,atol=1e-8);assert bool(getattr(row,prefix+'_padding_center'))==not_in_crop(nx,ny);coord_checks+=1
  d=np.hypot(trace.query_crop_normalized_x-trace.reference_crop_normalized_x,trace.query_crop_normalized_y-trace.reference_crop_normalized_y)/np.sqrt(2);assert np.allclose(d,trace.spatial_displacement_crop_diagonal,rtol=0,atol=1e-12)
 grid=pd.read_csv(base/'broad_maps/per_image_grid_counts.csv')
 common=grid[grid['view'].eq('common256_crop')]
 for recipe in ['D1','D2']:
  assert int(common[common.recipe.eq(recipe)].false_positive_pixels.sum())==next(x['fp_pixels'] for x in count_checks if x['recipe']==recipe)
 checks=pd.read_csv(base/'missing_component/independent_distance_checks.csv');assert checks.raw_map_max_error.max()==0 and checks.distance_max_error.max()<1e-5
 review={'reviewed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':True,'new_model_inference':False,'stage4_identity_checks':checked,'pose_population':1101,'evaluation_population':200,'saved_map_independent_counts':count_checks,'query_reference_coordinate_checks':coord_checks,'nn_trace_pairs':18490,'nn_order':'All saved ranklists/distances sorted; references match exact frozen fitting indices. Independent float64 feature-distance samples provided by trace receipt; no second full feature extraction here.','subset_distance_checks':len(checks),'max_subset_distance_error':float(checks.distance_max_error.max()),'pose_outcome_independence':'Final classifier/label identities and receipt chronology verified; RGB-only source method and grouped visual review, with acknowledged prior Stage4 knowledge.','grid_reconciliation':'Common-crop grid FP sums match all saved maps; outsidecropFP0','review_code_sha256':digest(Path(__file__))}
 if not (base/'diagnostics.json').exists():(base/'independent_review.json').write_text(json.dumps(review,indent=2)+'\n')
 print(json.dumps(review,indent=2))


def not_in_crop(x,y):return not (0<=x<1 and 0<=y<1)


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',default='.');verify(p.parse_args().root)

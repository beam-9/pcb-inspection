"""Two bounded PCB1 development recipes: reversible crop at256/512, fixed bank count."""
import argparse,json,time,resource,sys
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image,ImageOps
import torch
from torch.nn import functional as F
from sklearn.metrics import average_precision_score
from .geometry import detect_geometry,image_tensor,inverse_map,GEOMETRY_CONFIG
from .preprocessing import FrozenPatchExtractor,preprocess_mask
from .baseline import nearest
from .calibration import calibrate
from .evaluation import image_metrics,localization_metrics
from .guard import digest,write_new,now,verify_frozen

MANIFEST='data/manifests/pcb1_manifest.csv';WEIGHT='data/cache/hub/checkpoints/resnet18-f37072fd.pth'
class DynamicExtractor(FrozenPatchExtractor):
 @torch.inference_mode()
 def forward(self,batch):
  if batch.ndim!=4 or batch.shape[1]!=3 or batch.shape[2]!=batch.shape[3] or batch.shape[2] not in [256,512]:raise ValueError('Declared square inputs only')
  if not torch.isfinite(batch).all():raise ValueError('Finite input required')
  self.eval();l2=self.layer2(self.stem(batch.to(self.device)));l3=self.layer3(l2)
  l2=F.avg_pool2d(l2,3,1,1);l3=F.avg_pool2d(l3,3,1,1)
  return torch.cat([l2,F.interpolate(l3,size=l2.shape[-2:],mode='bilinear',align_corners=False)],1).cpu()

def setup(root):
 torch.set_num_threads(4);torch.manual_seed(42);torch.hub.set_dir(str(root/'data/cache/hub'))

def selected_indices(n,h,w,count=4096,seed=42):
 return np.sort(np.random.default_rng(seed).choice(n*h*w,size=min(count,n*h*w),replace=False))

def tensor_and_transform(root,row,size):
 if digest(root/'data/raw'/row.image_path)!=row.sha256:raise ValueError('Source image hash changed')
 with Image.open(root/'data/raw'/row.image_path) as im:
  g=detect_geometry(im);return image_tensor(im,g,size)

def score_feature(feature,memory,size,transform):
 _,c,h,w=feature.shape
 q=feature.permute(0,2,3,1).reshape(-1,c)
 distances,indices=nearest(q,memory,256)
 grid=distances.reshape(1,1,h,w)
 model_map=F.interpolate(grid,(size,size),mode='bilinear',align_corners=False)[0,0].numpy()
 # Preserve original max-all-patches scoring, including letterbox boundary patches.
 return float(distances.max()),model_map,inverse_map(model_map,transform,256)

def verify_recipe(root,out):
 protocol=json.loads((out/'protocol.json').read_text())
 for p,h in protocol['frozen_files'].items():
  if digest(root/p)!=h:raise ValueError(f'Recipe input changed:{p}')
 verify_frozen(root,json.loads((root/'docs/protocol.json').read_text()))
 return protocol

def freeze(root,size):
 root=Path(root).resolve();out=root/f'artifacts/runs/geometry_{size}_v1';out.mkdir(parents=True,exist_ok=False)
 verify_frozen(root,json.loads((root/'docs/protocol.json').read_text()))
 approval=root/'artifacts/pcb1_geometry/geometry_review.json'
 a=json.loads(approval.read_text());assert a['approved_for_bounded_development']
 assert a['audit_sha256']==digest(root/'artifacts/pcb1_geometry/audit.json')
 files=[MANIFEST,WEIGHT,'artifacts/pcb1_a2/per_anomaly_diagnostics.csv','docs/protocol.json','requirements.lock','docs/development/geometry_resolution_scope.json','artifacts/pcb1_geometry/audit.json','artifacts/pcb1_geometry/normal_transforms.json','artifacts/pcb1_geometry/geometry_review.json']
 files += [str(p.relative_to(root)) for p in sorted((root/'src/pcb_inspection').glob('*.py'))]
 files += [str(p.relative_to(root)) for p in sorted((root/'tests').glob('test_*.py'))]
 config={'input_size':size,'seed':42,'memory_count':4096,'geometry':GEOMETRY_CONFIG,'backbone':'ResNet18 IMAGENET1K_V1','aggregation':'layer2/layer3 avg3x3, bilinear align_corners_false','distance':'exact Euclidean CPU','image_score':'maximum all feature patches, including letterbox boundary','pixel_map':'bilinear input grid -> inverse source grid -> common256 direct-square','outside_crop_score':0.,'mask_resize':'nearest from original source','image_quantile':.95,'pixel_quantile':.99,'quantile_method':'higher','comparison':'>','threads':4,'batch_size':4,'caps':{'peak_rss_bytes':8*1024**3,'median_inference_seconds':10,'preparation_seconds':1800},'source_pixel_metrics':'per-image only; fullsource pooled AP omitted for resource limit','development_only':True,'pcb2_exposed':False}
 write_new(out/'protocol.json',{'frozen_at_utc':now(),'config':config,'frozen_files':{p:digest(root/p) for p in files}})
 print('Frozen',out,flush=True)

def prepare(root,size):
 root=Path(root).resolve();out=root/f'artifacts/runs/geometry_{size}_v1';protocol=verify_recipe(root,out);config=protocol['config'];setup(root)
 write_new(out/'prepare_started.json',{'started_at_utc':now(),'protocol_sha256':digest(out/'protocol.json')})
 started=time.perf_counter();f=pd.read_csv(root/MANIFEST).fillna('');fit=f[f.split=='fit'].reset_index(drop=True);cal=f[f.split=='calibration'];ext=DynamicExtractor()
 h=w=size//8;sampled=selected_indices(len(fit),h,w);memory=torch.empty((len(sampled),384));references=[]
 # Global uniform positions preselected before streaming. No full fitting feature bank.
 for start in range(0,len(fit),4):
  rows=list(fit.iloc[start:start+4].itertuples());pairs=[tensor_and_transform(root,r,size) for r in rows];feat=ext(torch.stack([p[0] for p in pairs]))
  keep=np.flatnonzero((sampled//(h*w)>=start)&(sampled//(h*w)<start+len(rows)))
  for j in keep:
   idx=int(sampled[j]);image_idx=idx//(h*w);ri=(idx%(h*w))//w;ci=idx%w
   memory[j]=feat[image_idx-start,:,ri,ci];references.append({'memory_index':int(j),'flat_index':idx,'image_id':fit.iloc[image_idx].image_id,'row':ri,'column':ci})
  if start%80==0:print('fit',size,start,'/',len(fit),flush=True)
  if time.perf_counter()-started>1800 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>8*1024**3:raise RuntimeError('Preparation cap exceeded')
 np.save(out/'memory.npy',memory.numpy());write_new(out/'memory_metadata.json',{'references':references,'count':len(memory),'candidate_count':len(fit)*h*w,'fraction':len(memory)/(len(fit)*h*w),'grid_shape':[h,w],'bytes':memory.numel()*4})
 maps=np.lib.format.open_memmap(out/'calibration_maps.npy',mode='w+',dtype='float32',shape=(len(cal),256,256));records=[];timings=[]
 for i,row in enumerate(cal.itertuples()):
  tick=time.perf_counter();x,t=tensor_and_transform(root,row,size);score,model_map,common=score_feature(ext(x[None]),memory,size,t);timings.append(time.perf_counter()-tick);maps[i]=common
  records.append({'image_id':row.image_id,'score':score,'seconds':timings[-1],'fallback':t['fallback']})
  if i%40==0:print('calibration',size,i,'/',len(cal),flush=True)
  if i==4:
   smoke={'normal_images':5,'median_inference_seconds':float(np.median(timings)),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'new_test_evidence':False}
   write_new(out/'normal_smoke.json',smoke)
   if smoke['median_inference_seconds']>10 or smoke['peak_rss_bytes']>8*1024**3:raise RuntimeError('Normal smoke failed')
  if time.perf_counter()-started>1800 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>8*1024**3:raise RuntimeError('Preparation cap exceeded')
 maps.flush();table=pd.DataFrame(records);table.to_csv(out/'calibration_predictions.csv',index=False)
 thresholds=calibrate(table.score.to_numpy(),maps);write_new(out/'calibration.json',thresholds);del maps
 runtime={'preparation_seconds':time.perf_counter()-started,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'median_inference_seconds':float(np.median(timings)),'p95_inference_seconds':float(np.quantile(timings,.95))}
 if runtime['median_inference_seconds']>10 or runtime['peak_rss_bytes']>8*1024**3 or runtime['preparation_seconds']>1800:raise RuntimeError('Normal-only resource gate failed')
 write_new(out/'normal_runtime.json',runtime)
 write_new(out/'prepared.json',{'completed_at_utc':now(),'resource_gate_passed':True,'protocol_sha256':digest(out/'protocol.json'),'prerequisites':{p:digest(out/p) for p in ['memory.npy','memory_metadata.json','calibration_predictions.csv','calibration_maps.npy','calibration.json','normal_runtime.json']}})
 print('Prepared',size,runtime,flush=True)

def pixel_row(mask,scores,threshold):
 pred=scores>threshold;intersection=int((mask&pred).sum());union=int((mask|pred).sum());peak=np.unravel_index(np.argmax(scores),scores.shape)
 return {'pixel_ap':float(average_precision_score(mask.ravel(),scores.ravel())) if mask.any() else None,'peak_inside':bool(mask[peak]),'overlap':bool(intersection),'intersection':intersection,'union':union,'iou':intersection/union if union else None,'mask_area_fraction':float(mask.mean())}

def evaluate(root,size):
 root=Path(root).resolve();out=root/f'artifacts/runs/geometry_{size}_v1';protocol=verify_recipe(root,out);setup(root)
 prep=json.loads((out/'prepared.json').read_text());assert prep['resource_gate_passed'] and prep['protocol_sha256']==digest(out/'protocol.json')
 for p,h in prep['prerequisites'].items():
  if digest(out/p)!=h:raise ValueError('Prepared prerequisite mismatch')
 write_new(out/'development_access.json',{'started_at_utc':now(),'role':'PCB1 development, already exposed in A2','protocol_sha256':digest(out/'protocol.json'),'prepared_sha256':digest(out/'prepared.json'),'evaluation_count':1})
 bank=torch.from_numpy(np.load(out/'memory.npy'));ext=DynamicExtractor();f=pd.read_csv(root/MANIFEST).fillna('');test=f[f.split=='test'];assert set(test.image_id).isdisjoint(set(f[f.split=='fit'].image_id))
 thresh=json.loads((out/'calibration.json').read_text());annotations=pd.read_csv(root/'artifacts/pcb1_a2/per_anomaly_diagnostics.csv').set_index('image_id');records=[];transforms={};maps=[];masks=[];timings=[]
 mapdir=out/'anomaly_maps';mapdir.mkdir(exist_ok=False)
 for i,row in enumerate(test.itertuples()):
  tick=time.perf_counter();x,t=tensor_and_transform(root,row,size);score,model_map,common=score_feature(ext(x[None]),bank,size,t);seconds=time.perf_counter()-tick;timings.append(seconds)
  mask=preprocess_mask(root/'data/raw'/row.mask_path) if row.label=='anomaly' else np.zeros((256,256),bool)
  maps.append(common);masks.append(mask);transforms[row.image_id]=t;np.save(mapdir/f'{row.image_id}.npy',common)
  record={'image_id':row.image_id,'image_path':row.image_path,'label':row.label,'score':score,'detected':score>thresh['image_threshold'],'seconds':seconds,'fallback':t['fallback'],'crop_area_fraction':t['crop_area_fraction'],**pixel_row(mask,common,thresh['pixel_threshold'])}
  if row.label=='anomaly':
   a=annotations.loc[row.image_id];record.update({'defect_types':a.defect_types,'size_quartile':a.size_quartile})
   source=inverse_map(model_map,t)
   if digest(root/'data/raw'/row.mask_path)!=row.mask_sha256:raise ValueError('Source mask hash changed')
   with Image.open(root/'data/raw'/row.mask_path) as m:sm=np.asarray(ImageOps.exif_transpose(m).convert('L'))>0
   sr=pixel_row(sm,source,thresh['pixel_threshold']);record.update({f'source_{k}':v for k,v in sr.items()})
   x0,y0,x1,y1=t['crop_box'];record['source_annotation_outside_crop_fraction']=1-float(sm[y0:y1,x0:x1].sum()/sm.sum())
  records.append(record)
  if i%25==0:print('development',size,i,'/',len(test),flush=True)
 pd.DataFrame(records).to_csv(out/'predictions.csv',index=False);write_new(out/'test_transforms.json',transforms)
 maps=np.asarray(maps);masks=np.asarray(masks);labels=(test.label=='anomaly').to_numpy();metrics={'image':image_metrics(labels,np.array([r['score'] for r in records]),thresh['image_threshold']),'localization_common256':localization_metrics(masks,maps,thresh['pixel_threshold']),'anomaly_localization':{}}
 anomaly=pd.DataFrame(records)[labels]
 for prefix in ['','source_']:
  metrics['anomaly_localization'][prefix or 'common256_']={'median_per_image_pixel_ap':float(anomaly[prefix+'pixel_ap'].median()),'q25':float(anomaly[prefix+'pixel_ap'].quantile(.25)),'q75':float(anomaly[prefix+'pixel_ap'].quantile(.75)),'peak_inside_count':int(anomaly[prefix+'peak_inside'].sum()),'overlap_count':int(anomaly[prefix+'overlap'].sum())}
 metrics['runtime']={'median_inference_seconds':float(np.median(timings)),'p95_inference_seconds':float(np.quantile(timings,.95)),'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};metrics['geometry']={'fallback_count':int(pd.DataFrame(records).fallback.sum()),'anomaly_with_annotation_outside_crop_count':int((anomaly.source_annotation_outside_crop_fraction>0).sum()),'maximum_annotation_outside_fraction':float(anomaly.source_annotation_outside_crop_fraction.max())}
 write_new(out/'metrics.json',metrics)
 types=[]
 for r in anomaly.itertuples():
  for typ in json.loads(r.defect_types):types.append({'defect_type':typ,'detected':r.detected,'pixel_ap':r.pixel_ap,'source_pixel_ap':r.source_pixel_ap})
 for key,table in [('defect_type',pd.DataFrame(types)),('size_quartile',anomaly)]:
  table.groupby(key).agg(sample_count=('detected','size'),detected_count=('detected','sum'),recall=('detected','mean'),median_pixel_ap=('pixel_ap','median'),median_source_pixel_ap=('source_pixel_ap','median')).to_csv(out/f'by_{key}.csv')
 write_new(out/'complete.json',{'completed_at_utc':now(),'development_only':True,'pcb2_exposed':False,'protocol_sha256':digest(out/'protocol.json'),'outputs':{str(p.relative_to(out)):digest(p) for p in sorted(out.rglob('*')) if p.is_file()}})
 print('Complete',size,json.dumps(metrics),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','prepare','evaluate']);p.add_argument('--root',default='.');p.add_argument('--size',type=int,choices=[256,512],required=True);a=p.parse_args();globals()[a.action](a.root,a.size)

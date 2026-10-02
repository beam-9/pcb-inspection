"""Independent count/quantile/ranking/reference checks for geometry development runs."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from .guard import digest,write_new,now,verify_frozen
from .verify_results import ranked_average_precision
from .geometry_experiment import DynamicExtractor,tensor_and_transform,setup


def verify(root,size):
 root=Path(root).resolve();out=root/f'artifacts/runs/geometry_{size}_v1'
 done=json.loads((out/'complete.json').read_text());protocol=json.loads((out/'protocol.json').read_text())
 assert done['protocol_sha256']==digest(out/'protocol.json')
 for p,h in done['outputs'].items():assert digest(out/p)==h,p
 for p,h in protocol['frozen_files'].items():assert digest(root/p)==h,p
 verify_frozen(root,json.loads((root/'docs/protocol.json').read_text()))
 manifest=pd.read_csv(root/'data/manifests/pcb1_manifest.csv').fillna('');table=pd.read_csv(out/'predictions.csv');test=manifest[manifest.split=='test'];fit=manifest[manifest.split=='fit'].reset_index(drop=True);cal=pd.read_csv(out/'calibration_predictions.csv');metrics=json.loads((out/'metrics.json').read_text());thresholds=json.loads((out/'calibration.json').read_text())
 assert table.image_id.tolist()==test.image_id.tolist()
 assert cal.image_id.tolist()==manifest[manifest.split=='calibration'].image_id.tolist()
 values=np.sort(cal.score.to_numpy());expected=values[int(np.ceil(.95*(len(values)-1)))]
 assert np.isclose(expected,thresholds['image_threshold'],rtol=0,atol=1e-12)
 cmap=np.load(out/'calibration_maps.npy',mmap_mode='r');rank=int(np.ceil(.99*(cmap.size-1)));pixel=float(np.partition(np.asarray(cmap).ravel().copy(),rank)[rank]);assert pixel==thresholds['pixel_threshold']
 labels=table.label.eq('anomaly').to_numpy();pred=table.score.to_numpy()>expected
 assert np.array_equal(pred,table.detected.to_numpy())
 counts={'tp':int((labels&pred).sum()),'fn':int((labels&~pred).sum()),'fp':int((~labels&pred).sum()),'tn':int((~labels&~pred).sum())}
 assert all(metrics['image'][k]==v for k,v in counts.items())
 ap=ranked_average_precision(labels,table.score.to_numpy());assert np.isclose(ap,metrics['image']['average_precision'],atol=1e-12)
 pos=table.score.to_numpy()[labels];neg=table.score.to_numpy()[~labels];auroc=float(((pos[:,None]>neg).sum()+.5*(pos[:,None]==neg).sum())/(len(pos)*len(neg)));assert np.isclose(auroc,metrics['image']['auroc'],atol=1e-12)
 intersection=union=peak=overlap=0;aps=[]
 from PIL import Image
 for row in test.itertuples():
  a=np.load(out/'anomaly_maps'/f'{row.image_id}.npy');assert a.shape==(256,256) and np.isfinite(a).all()
  mask=np.zeros((256,256),bool)
  if row.label=='anomaly':
   with Image.open(root/'data/raw'/row.mask_path) as im:mask=np.asarray(im.resize((256,256),Image.Resampling.NEAREST))>0
  flagged=a>pixel;inter=int((flagged&mask).sum());uni=int((flagged|mask).sum());intersection+=inter;union+=uni
  r=table[table.image_id==row.image_id].iloc[0]
  assert int(r.intersection)==inter and int(r.union)==uni
  if row.label=='anomaly':
   ap=ranked_average_precision(mask.ravel(),a.ravel());aps.append(ap);assert np.isclose(ap,r.pixel_ap,atol=1e-12)
   pp=bool(mask[np.unravel_index(np.argmax(a),a.shape)]);peak+=pp;overlap+=inter>0;assert pp==bool(r.peak_inside)
 assert intersection==metrics['localization_common256']['intersection_pixels'] and union==metrics['localization_common256']['union_pixels']
 assert np.isclose(np.median(aps),metrics['anomaly_localization']['common256_']['median_per_image_pixel_ap'],atol=1e-12)
 meta=json.loads((out/'memory_metadata.json').read_text());bank=np.load(out/'memory.npy');refs=meta['references'];h=w=size//8
 positions=np.sort(np.random.default_rng(42).choice(len(fit)*h*w,size=4096,replace=False));assert np.array_equal(positions,[r['flat_index'] for r in refs])
 assert set(r['image_id'] for r in refs).issubset(set(fit.image_id)) and bank.shape==(4096,384)
 setup(root);ext=DynamicExtractor()
 for j in [0,2048,4095]:
  ref=refs[j];row=fit[fit.image_id==ref['image_id']].iloc[0];x,t=tensor_and_transform(root,row,size);feature=ext(x[None])[0,:,ref['row'],ref['column']].numpy()
  assert np.allclose(bank[j],feature,rtol=1e-5,atol=1e-5)
 receipt={'reviewed_at_utc':now(),'size':size,'passed':True,'source_and_output_hashes_verified':True,'normal_thresholds_independently_checked':True,'all_200_predictions_checked':True,'image_ap_pairwise_auroc_confusion_checked':True,'all_100_common256_localization_ap_checked':True,'memory_sampling_and_fit_membership_checked':True,'three_bank_vectors_reextracted_and_checked':True,'source_resolution_metrics_not_independently_recomputed':True,'complete_sha256':digest(out/'complete.json')}
 write_new(out/'independent_review.json',receipt);print(json.dumps(receipt),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',default='.');p.add_argument('--size',type=int,choices=[256,512],required=True);a=p.parse_args();verify(a.root,a.size)

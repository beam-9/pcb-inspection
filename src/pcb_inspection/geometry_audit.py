"""Normal-only geometry audit, preserving every image and conservative fallbacks."""
import argparse,json,time,resource
from pathlib import Path
import pandas as pd
from PIL import Image,ImageDraw
from .geometry import detect_geometry,letterbox,GEOMETRY_CONFIG
from .guard import digest,write_new,now,verify_frozen

def audit(root,output):
 root=Path(root).resolve();out=root/output;out.mkdir(parents=True,exist_ok=False)
 verify_frozen(root,json.loads((root/'docs/protocol.json').read_text()))
 f=pd.read_csv(root/'data/manifests/pcb1_manifest.csv').fillna('');f=f[f.split.isin(['fit','calibration'])]
 tick=time.perf_counter(); records=[]; geometries={}
 for row in f.itertuples():
  with Image.open(root/'data/raw'/row.image_path) as im:g=detect_geometry(im)
  geometries[row.image_id]=g
  records.append({'image_id':row.image_id,'split':row.split,'image_path':row.image_path,**{k:v for k,v in g.items() if k not in ['crop_box','board_box']},'crop_box':json.dumps(g['crop_box']),'board_box':json.dumps(g['board_box'])})
 table=pd.DataFrame(records);table.to_csv(out/'normal_geometry.csv',index=False)
 write_new(out/'normal_transforms.json',geometries)
 # deterministic systematic sample: all crop-area tails and evenly spaced fit/calibration normals
 chosen=[]
 for split in ['fit','calibration']:
  group=table[table.split==split].sort_values('image_id');chosen+=group.iloc[[round(i*(len(group)-1)/5) for i in range(6)]].image_id.tolist()
 chosen+=table.sort_values('crop_area_fraction').iloc[[0,-1]].image_id.tolist();chosen=list(dict.fromkeys(chosen))
 for page in range((len(chosen)+5)//6):
  ids=chosen[page*6:(page+1)*6];canvas=Image.new('RGB',(1000,len(ids)*280),'white');draw=ImageDraw.Draw(canvas)
  for i,id in enumerate(ids):
   row=table[table.image_id==id].iloc[0];g=geometries[id]
   with Image.open(root/'data/raw'/row.image_path) as im:
    original=im.convert('RGB');d=ImageDraw.Draw(original);d.rectangle(g['crop_box'],outline='lime',width=8)
    original.thumbnail((370,250));canvas.paste(original,(0,i*280+25))
    crop,t=letterbox(im,g,256);canvas.paste(crop,(400,i*280+25))
    crop512,_=letterbox(im,g,512);crop512.thumbnail((256,256));canvas.paste(crop512,(710,i*280+25))
   draw.text((5,i*280+5),f'{row.split} {id} crop={g["crop_area_fraction"]:.3f} fallback={g["fallback"]}',fill='black')
  canvas.save(out/f'normal_contact_sheet_{page+1:02d}.png')
 write_new(out/'audit.json',{'created_at_utc':now(),'config':GEOMETRY_CONFIG,'code_sha256':{p:digest(root/p) for p in ['src/pcb_inspection/geometry.py','src/pcb_inspection/geometry_audit.py','tests/test_geometry.py']},'manifest_sha256':digest(root/'data/manifests/pcb1_manifest.csv'),'normal_count':len(table),'split_counts':table.groupby('split').size().to_dict(),'fallback_count':int(table.fallback.sum()),'crop_area_quantiles':table.crop_area_fraction.quantile([0,.05,.5,.95,1]).to_dict(),'normal_only':True,'pose_registration':False,'selection_ids':chosen,'elapsed_seconds':time.perf_counter()-tick,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'outputs':{p.name:digest(p) for p in out.iterdir() if p.is_file()}})
 print(out,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',default='.');p.add_argument('--output',default='artifacts/pcb1_geometry');a=p.parse_args();audit(a.root,a.output)

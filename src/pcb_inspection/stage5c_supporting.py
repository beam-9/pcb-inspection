"""Saved-array supporting source-coordinate metrics; no detector inference."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image,ImageOps
from .stage5c_review import source_map,pixel_counts
from .guard import digest,write_new,now


def build(root):
    root=Path(root).resolve();out=root/'artifacts/stage5c';protocol=json.loads((out/'orientation_protocol.json').read_text());records=[];sources={}
    manifest=pd.read_csv(root/'artifacts/stage4/pcb2_d2_secondary/confirmation_manifest.csv').set_index('image_id')
    for path,orientation in [('artifacts/stage4/pcb2_d2_secondary',False),('artifacts/stage5c',True)]:
        p=root/path;paths=json.loads((p/'array_paths.json').read_text());transforms=json.loads((p/'test_transforms.json').read_text())
        table=pd.read_csv(p/'predictions.csv',float_precision='round_trip').set_index('image_id')
        for image_id in protocol['reversed_ids']:
            model_path=root/paths['model_maps']/f'{image_id}.npy';mask_path=root/manifest.loc[image_id,'mask_path']
            sources[str(model_path.relative_to(root))]=digest(model_path);sources[str(mask_path.relative_to(root))]=digest(mask_path)
            model=np.load(model_path);scores=source_map(model,transforms[image_id],orientation)
            with Image.open(mask_path) as im:gt=np.asarray(ImageOps.exif_transpose(im).convert('L'))>0
            counts=pixel_counts(scores,gt,protocol['thresholds']['pixel_threshold'])
            for name in ['pixel_ap','iou','intersection','union']:
                if not np.isclose(counts[name],table.loc[image_id,'source_'+name],rtol=0,atol=1e-12):raise ValueError('Source metric mismatch')
            records.append({'image_id':image_id,'recipe':'orientation_D2' if orientation else 'historical_D2','coordinate_system':'original source','denominator_pixels':gt.size,'gt_pixels':int(gt.sum()),**counts})
    target=out/'results/reversed_source_support.csv'
    if target.exists():raise FileExistsError(target)
    pd.DataFrame(records).to_csv(target,index=False)
    sources[str(Path(__file__).relative_to(root))]=digest(__file__)
    write_new(out/'supporting_validation.json',{'passed':True,'created_at_utc':now(),'new_model_inference':False,'source_map_rows_checked':10,'sources':sources,'output_sha256':digest(target)})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');a=p.parse_args();build(a.root)

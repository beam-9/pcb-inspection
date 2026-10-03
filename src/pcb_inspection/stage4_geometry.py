"""Normal-only PCB2 geometry preflight, retaining inherited map semantics."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageOps

from .geometry import GEOMETRY_CONFIG, detect_geometry, image_tensor, letterbox
from .guard import digest, now, write_new


def geometry_for(image, config):
    config = config.get('geometry', config)
    mode = config.get('mode', 'inherited_blue')
    if any(config.get(key,value) != value for key,value in GEOMETRY_CONFIG.items()):
        raise ValueError('Inherited geometry parameters must match implemented constants')
    if mode != 'inherited_blue':
        raise ValueError('Only inherited geometry is implemented; adaptation needs a separate declared identity')
    return detect_geometry(image)


def tensor_and_transform(root, row, size, config):
    path = Path(root) / row.image_path
    if digest(path) != row.sha256:
        raise ValueError('Source image changed')
    with Image.open(path) as image:
        image.load()
        return image_tensor(image, geometry_for(image, config), size)


def preflight(root, manifest, output, config=None):
    root, output = Path(root), Path(output)
    config = config or {'mode': 'inherited_blue', **GEOMETRY_CONFIG}
    frame = pd.read_csv(root / manifest).fillna('')
    allowed = frame[frame.split.isin(['fit', 'calibration'])].sort_values('image_id')
    if allowed.empty or not allowed.label.eq('normal').all():
        raise ValueError('Preflight requires fitting/calibration normals only')
    if output.exists():
        raise FileExistsError('Geometry preflight refuses overwrite')
    output.mkdir(parents=True)
    records, transforms = [], {}
    for row in allowed.itertuples():
        if digest(root / row.image_path) != row.sha256:
            raise ValueError('Normal input hash changed')
        with Image.open(root / row.image_path) as image:
            image.load()
            g = geometry_for(image, config)
            _, t = letterbox(image, g, 256)
        x0,y0,x1,y1 = g['crop_box']
        box = g['board_box']
        records.append({'image_id':row.image_id,'split':row.split,'fallback':g['fallback'],
                        'failure_reason':g['failure_reason'],'crop_area_fraction':g['crop_area_fraction'],
                        'crop_aspect_ratio':(x1-x0)/(y1-y0),'board_width':None if box is None else box[2]-box[0],
                        'board_height':None if box is None else box[3]-box[1],
                        'component_fraction':g['component_fraction'],
                        'padding_fraction':1-t['content_width']*t['content_height']/256**2,
                        'crop_touches_source_boundary':any([x0==0,y0==0,x1==g['source_width'],y1==g['source_height']]),
                        'board_touches_source_boundary':False if box is None else any([box[0]==0,box[1]==0,box[2]==g['source_width'],box[3]==g['source_height']])})
        transforms[row.image_id]=t
    table=pd.DataFrame(records);table.to_csv(output/'normal_geometry.csv',index=False)
    write_new(output/'normal_transforms.json',transforms)
    chosen=[]
    def add(image_id, reason):
        if image_id not in [x['image_id'] for x in chosen]:chosen.append({'image_id':image_id,'reason':reason})
    for row in table[table.fallback].itertuples():add(row.image_id,'fallback')
    for column in ['crop_area_fraction','crop_aspect_ratio','padding_fraction','component_fraction']:
        for direction in [True,False]:
            first=table.sort_values([column,'image_id'],ascending=[direction,True]).iloc[0]
            add(first.image_id,f'{column} {"minimum" if direction else "maximum"}')
    for index in np.linspace(0,len(table)-1,12,dtype=int):add(table.iloc[index].image_id,'systematic sorted normal sample')
    for row in table[table.crop_touches_source_boundary | table.board_touches_source_boundary].head(10).itertuples():add(row.image_id,'source-boundary contact')
    pd.DataFrame(chosen).to_csv(output/'visual_selection.csv',index=False)
    indexed=allowed.set_index('image_id')
    # Six normal rows per page: source with board/crop boxes, crop, letterboxed input.
    pages=[]
    for start in range(0,len(chosen),6):
        items=chosen[start:start+6]
        sheet=Image.new('RGB',(1050, len(items)*290+50),'white');draw=ImageDraw.Draw(sheet)
        draw.text((15,10),'PCB2 training normals only: detected board cyan, final crop orange; no anomaly supervision',fill='black')
        for index,item in enumerate(items):
            row=indexed.loc[item['image_id']]; t=transforms[item['image_id']]; y=50+index*290
            with Image.open(root/row.image_path) as raw:
                original=ImageOps.exif_transpose(raw).convert('RGB');marked=original.copy();d=ImageDraw.Draw(marked)
                width=max(3,original.width//200)
                if t['board_box']:d.rectangle(t['board_box'],outline='cyan',width=width)
                d.rectangle(t['crop_box'],outline='orange',width=width)
                crop=original.crop(t['crop_box']);canvas,_=letterbox(original,t,256)
                for col,picture in enumerate([marked,crop,canvas]):
                    thumb=ImageOps.contain(picture,(320,245));sheet.paste(thumb,(15+col*345,y+30))
            draw.text((15,y),f"{item['image_id']} | {item['reason']}",fill='black')
        name=f'normal_contact_sheet_{start//6+1:02d}.png';sheet.save(output/name);pages.append(name)
    summary={'created_at_utc':now(),'scope':'PCB2 official training normals only; heldout normals and anomalies excluded',
             'manifest_sha256':digest(root/manifest),'geometry':config,'normal_count':len(table),
             'fallback_count':int(table.fallback.sum()),'source_boundary_contact_count':int(table.crop_touches_source_boundary.sum()),
             'board_boundary_contact_count':int(table.board_touches_source_boundary.sum()),
             'statistics':{c:{'min':float(table[c].min()),'median':float(table[c].median()),'max':float(table[c].max())} for c in ['crop_area_fraction','crop_aspect_ratio','padding_fraction','component_fraction']},
             'visual_example_count':len(chosen),'contact_sheets':pages,'pose':'No orientation normalization; visual consistency requires review',
             'anomaly_access':False,'review_status':'pending visual suitability review','outputs':{p.name:digest(p) for p in output.iterdir() if p.is_file()}}
    write_new(output/'geometry_preflight.json',summary)
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');p.add_argument('--manifest',default='artifacts/stage4/pcb2_normals/normal_manifest.csv');p.add_argument('--output',default='artifacts/stage4/geometry_preflight');a=p.parse_args()
    print(json.dumps(preflight(a.root,a.manifest,Path(a.root)/a.output),indent=2))

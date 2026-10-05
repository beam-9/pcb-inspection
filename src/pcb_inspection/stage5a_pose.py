"""Outcome-independent categorical PCB2 pin-position diagnosis, then saved-result summaries.

No detector inference, rotations, registration, model or threshold changes.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image,ImageDraw,ImageOps
from scipy import ndimage
from .guard import digest,now,write_new

METHOD={'id':'pcb2-exterior-pin-ridges-v1','analysis_width':512,'central_board_width_fraction':0.40,
        'exterior_band_height_fraction':0.45,'horizontal_median_width':15,
        'local_contrast_min':0.08,'intensity_min':0.35,'rgb_range_max':0.20,
        'vertical_opening_board_height_fraction':0.10,'component_aspect_min':3,
        'minimum_pin_components':2,'dominance_ratio':3,
        'canonical':'top exterior pin cue','reversed_180':'bottom exterior pin cue',
        'uncertain':'neither cue decisive, both cues, absent boardbox or nonhorizontal board',
        'precise_angles_estimated':False,'outcome_inputs':[],
        'scope':'Post-confirmation PCB2 development diagnosis',
        'prior_knowledge':'Stage4 visual knowledge exists; classifier itself consumes RGB+existing board box only'}
LABELS=['canonical','reversed_180','uncertain']

def classify_pose(image,board_box):
    if board_box is None:return {'pose_label':'uncertain','top_pin_components':0,'bottom_pin_components':0,'top_pin_pixels':0,'bottom_pin_pixels':0,'cue_dominance':None,'uncertainty_reason':'absent_board_box'}
    scale=METHOD['analysis_width']/image.width
    rgb=np.asarray(image.convert('RGB').resize((512,round(image.height*scale)),Image.Resampling.BILINEAR),dtype=float)/255
    x0,y0,x1,y1=np.array(board_box)*scale;bw=x1-x0;bh=y1-y0
    if bw/bh<1.4:return {'pose_label':'uncertain','top_pin_components':0,'bottom_pin_components':0,'top_pin_pixels':0,'bottom_pin_pixels':0,'cue_dominance':None,'uncertainty_reason':'nonhorizontal_board'}
    gray=rgb.mean(axis=2);contrast=gray-ndimage.median_filter(gray,size=(1,15),mode='reflect')
    ridge=(contrast>0.08)&(gray>0.35)&(np.ptp(rgb,axis=2)<0.20)
    left=max(0,round(x0+0.30*bw));right=min(rgb.shape[1],round(x0+0.70*bw))
    length=max(3,round(0.10*bh))
    results={}
    for name,lo,hi in [('top',round(y0-.45*bh),round(y0)),('bottom',round(y1),round(y1+.45*bh))]:
        band=ridge[max(0,lo):min(rgb.shape[0],hi),left:right]
        opened=ndimage.binary_opening(band,structure=np.ones((length,1),bool))
        labels,count=ndimage.label(opened);components=pixels=0
        for index,section in enumerate(ndimage.find_objects(labels),1):
            if section is None:continue
            height=section[0].stop-section[0].start;width=section[1].stop-section[1].start
            if height>=length and height/max(1,width)>=3:
                components+=1;pixels+=int((labels[section]==index).sum())
        results[name+'_pin_components']=components;results[name+'_pin_pixels']=pixels
    top,bottom=results['top_pin_components'],results['bottom_pin_components']
    tp,bp=results['top_pin_pixels'],results['bottom_pin_pixels']
    if top>=2 and tp>=3*max(1,bp):label='canonical'
    elif bottom>=2 and bp>=3*max(1,tp):label='reversed_180'
    else:label='uncertain'
    return {'pose_label':label,**results,'cue_dominance':max(tp,bp)/max(1,min(tp,bp)),
            'uncertainty_reason':'ambiguous_or_insufficient_pin_cue' if label=='uncertain' else ''}

def label_all(root,output):
    root=Path(root);output=Path(output)
    if output.exists():raise FileExistsError('Pose labeling refuses overwrite')
    output.mkdir(parents=True)
    # Method saved before opening any source pixels; outcomes are not loaded.
    write_new(output/'pose_method.json',{'declared_at_utc':now(),'method':METHOD,'code_sha256':digest(Path(__file__))})
    normal=pd.read_csv(root/'artifacts/stage4/pcb2_normals/normal_manifest.csv',keep_default_na=False)
    test=pd.read_csv(root/'artifacts/stage4/confirmation_data/test_manifest.csv',keep_default_na=False)
    anomalies=test[test.label=='anomaly'].copy();anomalies['split']='anomaly_test'
    frame=pd.concat([normal,anomalies],ignore_index=True).sort_values('image_id')
    if len(frame)!=1101 or frame.image_id.duplicated().any():raise ValueError('Complete PCB2 identity inventory required')
    transforms=json.loads((root/'artifacts/stage4/geometry_preflight/normal_transforms.json').read_text())
    transforms.update(json.loads((root/'artifacts/stage4/pcb2_d1_primary/test_transforms.json').read_text()))
    records=[]
    for row in frame.itertuples():
        if digest(root/row.image_path)!=row.sha256:raise ValueError('Source image changed')
        with Image.open(root/row.image_path) as image:
            result=classify_pose(image,transforms[row.image_id]['board_box'])
        records.append({'image_id':row.image_id,'image_path':row.image_path,'source_sha256':row.sha256,
                        'split':row.split,'normal_or_anomaly':row.label,**result,
                        'pose_method':METHOD['id'],'review_status':'automatic; grouped image-only validation pending'})
    labels=pd.DataFrame(records);labels.to_csv(output/'pose_labels.csv',index=False)
    selected=[];pages=[]
    for label in LABELS:
        group=labels[labels.pose_label==label]
        # All ambiguous cases are shown; decisive labels sampled across each split.
        if label=='uncertain':choices=group.copy()
        else:
            groups=[]
            for split,part in group.groupby('split',sort=True):
                positions=np.unique(np.linspace(0,len(part)-1,min(8,len(part)),dtype=int));groups.append(part.iloc[positions])
            choices=pd.concat(groups) if groups else group
        for start in range(0,len(choices),12):
            part=choices.iloc[start:start+12];sheet=Image.new('RGB',(1200,50+240*((len(part)+3)//4)),'white');draw=ImageDraw.Draw(sheet)
            draw.text((10,10),f'{label} | image-only pose validation; no detector scores or labels used',fill='black')
            for i,row in enumerate(part.itertuples()):
                x=(i%4)*300;y=50+(i//4)*240
                with Image.open(root/row.image_path) as source:thumb=ImageOps.contain(source.convert('RGB'),(290,205))
                sheet.paste(thumb,(x,y));draw.text((x,y+206),f'{row.image_id[:12]} {row.split}',fill='black')
                draw.text((x,y+222),f'T{row.top_pin_components}/B{row.bottom_pin_components}',fill='black')
                selected.append({'image_id':row.image_id,'pose_label':label,'split':row.split,'reason':'all uncertain' if label=='uncertain' else 'systematic within split'})
            name=f'pose_{label}_{start//12+1:02d}.png';sheet.save(output/name);pages.append(name)
    pd.DataFrame(selected).to_csv(output/'visual_selection.csv',index=False)
    summary=labels.groupby(['split','normal_or_anomaly','pose_label']).size().reset_index(name='count')
    summary.to_csv(output/'pose_population.csv',index=False)
    write_new(output/'labels_provisional.json',{'created_at_utc':now(),'count':len(labels),'pose_counts':labels.pose_label.value_counts().to_dict(),
              'label_sha256':digest(output/'pose_labels.csv'),'contact_sheets':pages,'outcome_comparison_started':False})
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');p.add_argument('--output',default='artifacts/stage5a/pose');a=p.parse_args()
    print(label_all(a.root,Path(a.root)/a.output).to_string(index=False))

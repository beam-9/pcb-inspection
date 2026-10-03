"""Predeclared post-confirmation example selection and shared-scale contact sheets."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image,ImageOps
from .guard import digest,now,write_new


def choose(primary,secondary,threshold,maximum=24):
    p=primary.copy();p['margin']=p.score-threshold;p['anomalous']=p.label.eq('anomaly')
    selected=[]
    def add(sub,reason,count=2):
        for row in sub.head(count).itertuples():
            prior=next((x for x in selected if x['image_id']==row.image_id),None)
            if prior is not None:prior['additional_reasons'].append(reason)
            elif len(selected)<maximum:selected.append({'image_id':row.image_id,'reason':reason,'additional_reasons':[]})
    add(p[p.anomalous&p.detected].sort_values(['margin','image_id']),'TP smallest positive primary margin')
    add(p[p.anomalous&~p.detected].sort_values(['margin','image_id'],ascending=[False,True]),'FN closest below primary threshold')
    add(p[~p.anomalous&p.detected].sort_values(['score','image_id'],ascending=[False,True]),'FP largest primary score')
    a=p[p.anomalous]
    add(a.sort_values(['mask_area_fraction','image_id']),'smallest common-mask area')
    add(a.sort_values(['mask_area_fraction','image_id'],ascending=[False,True]),'largest common-mask area')
    labels=a.defect_types.fillna('[]').map(json.loads)
    for kind in sorted({k for ls in labels for k in ls}):
        sub=a[labels.map(lambda ls:kind in ls)].copy();sub['distance']=abs(sub.mask_area_fraction-sub.mask_area_fraction.median())
        add(sub.sort_values(['distance','image_id']),f'{kind}: closest median area',1)
    s=secondary.set_index('image_id');disagreement=p[p.image_id.map(s.detected).to_numpy()!=p.detected.to_numpy()]
    add(disagreement.sort_values('image_id'),'D1/D2 decision disagreement')
    add(a[a.overlap&~a.peak_inside].sort_values('image_id'),'overlap but peak outside',1)
    add(a[a.peak_inside].sort_values('image_id'),'peak inside annotation',1)
    return selected


def render(root):
    root=Path(root).resolve();stage=root/'artifacts/stage4';out=stage/'comparison'
    if (out/'comparison_complete.json').exists():raise FileExistsError('Comparison is complete')
    folders=[stage/'pcb2_d1_primary',stage/'pcb2_d2_secondary'];tables=[pd.read_csv(f/'predictions.csv') for f in folders]
    for f in folders:assert json.loads((f/'independent_review.json').read_text())['passed']
    thresholds=[json.loads((f/'calibration.json').read_text()) for f in folders]
    selected=choose(*tables,thresholds[0]['image_threshold']);pd.DataFrame(selected).to_csv(out/'qualitative_selection.csv',index=False)
    manifest=pd.read_csv(stage/'confirmation_data/test_manifest.csv',keep_default_na=False).set_index('image_id')
    indexed=[t.set_index('image_id') for t in tables];arraypaths=[json.loads((f/'array_paths.json').read_text()) for f in folders]
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm
    pages=[];metricrows=[]
    for start in range(0,len(selected),6):
        subset=selected[start:start+6];fig,axes=plt.subplots(len(subset),4,figsize=(12,len(subset)*3.1),squeeze=False)
        for i,entry in enumerate(subset):
            identity=entry['image_id'];row=manifest.loc[identity]
            with Image.open(root/row.image_path) as im:rgb=np.asarray(ImageOps.exif_transpose(im).convert('RGB').resize((256,256),Image.Resampling.BILINEAR))
            if row.label=='anomaly':
                with Image.open(root/row.mask_path) as im:
                    mask=np.asarray(ImageOps.exif_transpose(im).convert('L').resize((256,256),Image.Resampling.NEAREST))>0
            else:mask=np.zeros((256,256),bool)
            axes[i,0].imshow(rgb);axes[i,0].set_title(f"{identity[:10]} · {row.label}\n{entry['reason']}",fontsize=8)
            axes[i,1].imshow(mask,cmap='gray',vmin=0,vmax=1);axes[i,1].set_title(f'Unchanged GT: {mask.sum()} common pixels',fontsize=8)
            for j in range(2):
                scoremap=np.load(root/arraypaths[j]['anomaly_maps']/f'{identity}.npy');axes[i,j+2].imshow(scoremap/thresholds[j]['pixel_threshold'],cmap='magma',vmin=0,vmax=2)
                if mask.any():axes[i,j+2].contour(mask,levels=[.5],colors=['cyan'],linewidths=.5)
                record=indexed[j].loc[identity];axes[i,j+2].set_title(f"{'D1 primary' if j==0 else 'D2 secondary'}: detected={record.detected}\nimage score={record.score:.3f}",fontsize=8)
                metricrows.append({'image_id':identity,'recipe':'D1 primary' if j==0 else 'D2 secondary','label':row.label,'score':record.score,'detected':record.detected,'pixel_ap':record.pixel_ap,'peak_inside':record.peak_inside,'overlap':record.overlap})
            for ax in axes[i]:ax.axis('off')
        fig.suptitle('Predeclared examples; full-source common 256; cyan annotation\nMap / own frozen pixel threshold, clipped 0–2; not probability',fontsize=11)
        fig.subplots_adjust(top=.94,bottom=.025,left=.02,right=.92,hspace=.3,wspace=.12)
        cax=fig.add_axes([.95,.1,.012,.7]);fig.colorbar(cm.ScalarMappable(norm=plt.Normalize(0,2),cmap='magma'),cax=cax)
        name=f'qualitative_contact_sheet_{start//6+1:02d}.png';fig.savefig(out/'figures'/name,dpi=145);plt.close(fig);pages.append(name)
    pd.DataFrame(metricrows).to_csv(out/'qualitative_metrics.csv',index=False)
    write_new(out/'qualitative_metadata.json',{'created_at_utc':now(),'selection_rule':'Frozen configs/stage4_protocol.json; priority order, fullID ties, dedup, max24','example_count':len(selected),'pages':pages,'selection_sha256':digest(out/'qualitative_selection.csv'),'new_inference':False,'scope':'Post-confirmation qualitative review; no retuning'})
    print('Saved',len(selected),'predeclared examples across',len(pages),'pages')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');a=p.parse_args();render(a.root)

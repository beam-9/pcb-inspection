"""Render A2 notebook/report figures from saved tables; no model inference."""
import argparse
import json
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

from .guard import digest, now, write_new
from .preprocessing import preprocess_mask

BLUE='#2364aa'; GOLD='#b36a13'; DARK='#333333'


def render(root, output='artifacts/pcb1_a2'):
    root=Path(root); folder=root/output
    if (folder/'a2_complete.json').exists():
        raise FileExistsError('Completed A2 evidence is immutable; use another output')
    read=lambda name:pd.read_csv(folder/f'{name}.csv')
    anomaly=read('per_anomaly_diagnostics'); normal=read('normal_score_diagnostics')
    types=read('recall_by_defect_type'); quartiles=read('recall_by_defect_size_quartile')
    ap=read('per_anomaly_defect_types');roc=read('full_roc_data')
    operating=read('recall_vs_fpr')
    plt.rcParams.update({'font.size':11,'figure.dpi':140,'axes.spines.top':False,'axes.spines.right':False})
    def save(fig,name):
        fig.savefig(folder/f'{name}.png',bbox_inches='tight');plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,4.2),layout='constrained')
    ordered=types.sort_values(['recall','defect_type'])
    ax.barh(ordered.defect_type,ordered.recall,color=BLUE)
    for i,row in enumerate(ordered.itertuples()):
        ax.text(min(row.recall+.015,.92),i,f'{row.detected_count}/{row.sample_count}',va='center')
    ax.set(xlim=(0,1),xlabel='Recall at original threshold',title='PCB1 development: recall by source defect label')
    ax.xaxis.set_major_formatter(PercentFormatter(1));save(fig,'recall_by_defect_type')
    fig,axes=plt.subplots(1,2,figsize=(11,3.6),layout='constrained')
    for ax,value,title in zip(axes,['recall','median_per_image_pixel_ap'],['Frozen-threshold recall','Median per-image pixel AP']):
        ax.bar(quartiles.size_quartile,quartiles[value],color=BLUE)
        ax.set(ylim=(0,1),ylabel=title,xlabel='Mask-area quartile (Q1 smallest)',title=title+' by defect size')
        if value=='recall':ax.yaxis.set_major_formatter(PercentFormatter(1))
        for i,row in enumerate(quartiles.itertuples()):
            ax.text(i,getattr(row,value)+.025,f'n={row.sample_count}',ha='center',fontsize=9)
    save(fig,'recall_by_defect_size_quartile')
    fig,ax=plt.subplots(figsize=(9,4),layout='constrained')
    order=types.sort_values(['median_per_image_pixel_ap','defect_type']).defect_type.tolist()
    data=[ap.loc[ap.defect_type==label,'per_image_pixel_ap'].to_numpy() for label in order]
    ax.boxplot(data,orientation='horizontal',tick_labels=[f"{label} (n={len(values)})" for label,values in zip(order,data)],showfliers=True,
               boxprops={'color':BLUE},medianprops={'color':GOLD})
    ax.set(xlim=(0,1),xlabel='Per-image pixel average precision',title='PCB1 development: localization by source label')
    save(fig,'pixel_ap_by_defect_type')
    fig,ax=plt.subplots(figsize=(9,4),layout='constrained')
    for detected,color,marker in [(True,BLUE,'o'),(False,GOLD,'x')]:
        rows=anomaly[anomaly.detected_at_frozen_threshold==detected]
        ax.scatter(rows.mask_area_fraction,rows.image_anomaly_score,c=color,marker=marker,s=35,alpha=.8,
            label=f'{"Detected" if detected else "Missed"} at original threshold (n={len(rows)})')
    ax.axhline(anomaly.frozen_image_threshold.iloc[0],color=DARK,linestyle=':',label='Original threshold')
    ax.set(xscale='log',xlabel='Annotated area / 256-square image (log scale)',ylabel='Raw image anomaly score',title='PCB1 development: score versus annotation size')
    ax.legend(fontsize=9);save(fig,'score_vs_defect_area')
    fig,ax=plt.subplots(figsize=(8,4),layout='constrained')
    ax.step(roc.realized_fpr,roc.recall,where='post',color=BLUE,label='Retrospective attainable ROC')
    ax.scatter(operating.realized_fpr,operating.recall,marker='o',facecolors='white',edgecolors=BLUE,zorder=3)
    ax.scatter([.09],[.43],marker='x',s=65,color=GOLD,label='Original threshold: 9% FPR, 43% recall',zorder=4)
    ax.set(xlim=(0,.25),ylim=(0,1),xlabel='Test-normal false-positive rate',ylabel='Anomaly recall',title='PCB1 development only: threshold tradeoff')
    ax.xaxis.set_major_formatter(PercentFormatter(1));ax.yaxis.set_major_formatter(PercentFormatter(1));ax.legend(fontsize=9)
    save(fig,'recall_vs_fpr')
    fig,ax=plt.subplots(figsize=(8,4),layout='constrained')
    for split,color,style in [('calibration',BLUE,'-'),('test',GOLD,'--')]:
        rows=normal[normal.split==split];scores=np.sort(rows.image_anomaly_score.to_numpy())
        ax.step(scores,np.arange(1,len(scores)+1)/len(scores),where='post',color=color,linestyle=style,label=f'{split.capitalize()} normals (n={len(rows)})')
    ax.axvline(anomaly.frozen_image_threshold.iloc[0],color=DARK,linestyle=':',label='Original normal-only threshold')
    ax.set(xlabel='Raw image anomaly score',ylabel='Empirical cumulative fraction',ylim=(0,1),title='PCB1 development: normal score distributions')
    ax.yaxis.set_major_formatter(PercentFormatter(1));ax.legend(fontsize=9);save(fig,'normal_score_distribution')
    select_qualitative(root,folder,anomaly)
    write_new(folder/'plot_metadata.json',{'rendered_utc':now(),'source_tables':'A2 CSV tables; no refitting/inference',
        'charts':{p.name:digest(p) for p in sorted(folder.glob('*.png'))},
        'type_counting':'A multilabel image contributes once per source label; grouped sample counts may exceed100',
        'qualitative_selection':'Deterministic metric/order-based reasons; IDs and reasons retained in qualitative/selection.csv'})


def select_qualitative(root,folder,anomaly):
    rows=anomaly.sort_values('image_id').copy();selections={}
    def pick(frame,reason,sort,ascending=True):
        if frame.empty:return
        row=frame.sort_values(sort,ascending=ascending,kind='stable').iloc[0]
        selections.setdefault(row.image_id,[]).append(reason)
    tp=rows[rows.detected_at_frozen_threshold];fn=rows[~rows.detected_at_frozen_threshold]
    pick(tp,'TP: strongest per-image localization',['per_image_pixel_ap','image_id'],[False,True])
    pick(tp,'TP: weakest per-image localization',['per_image_pixel_ap','image_id'])
    pick(fn,'FN: nearest below image threshold',['score_minus_threshold','image_id'],[False,True])
    pick(fn,'FN: lowest image score',['image_anomaly_score','image_id'])
    pick(rows[rows.size_quartile=='Q1'],'Smallest-area quartile',['mask_area_fraction','image_id'])
    labels=sorted({label for packed in rows.defect_types for label in json.loads(packed)})
    for label in labels:
        group=rows[rows.defect_types.map(lambda packed:label in json.loads(packed))]
        group=group.sort_values(['image_anomaly_score','image_id'])
        row=group.iloc[len(group)//2];selections.setdefault(row.image_id,[]).append(f'{label}: middle score-ranked image')
    run=root/'artifacts/runs/31e0704ff1da6906';pred=pd.read_parquet(run/'predictions.parquet')
    manifest=pd.read_csv(run/'split_manifest.csv',keep_default_na=False).set_index('image_id')
    threshold=rows.frozen_image_threshold.iloc[0];pixel_threshold=rows.frozen_pixel_threshold.iloc[0]
    fp=pred[(pred.label==0)&(pred.primary_score>threshold)].sort_values(['primary_score','image_id'])
    if len(fp):
        for row,reason in [(fp.iloc[len(fp)//2],'FP: middle score-ranked normal'),(fp.iloc[-1],'FP: highest-scoring normal')]:
            selections.setdefault(row.image_id,[]).append(reason)
    out=folder/'qualitative';out.mkdir(exist_ok=True)
    selection=pd.DataFrame([{'image_id':i,'reasons':json.dumps(reasons)} for i,reasons in selections.items()])
    selection.to_csv(out/'selection.csv',index=False)
    lookup=rows.set_index('image_id');vmax=max(float(np.load(run/'anomaly_maps'/f'{i}.npy').max()) for i in pred.image_id)
    for page,start in enumerate(range(0,len(selection),4),1):
        part=selection.iloc[start:start+4];fig,axes=plt.subplots(len(part),5,figsize=(15,3.3*len(part)),squeeze=False,layout='constrained')
        for r,record in enumerate(part.itertuples()):
            source=manifest.loc[record.image_id]
            with Image.open(root/'data/raw'/source.image_path) as image:rgb=np.asarray(image.convert('RGB').resize((256,256)))
            mask=preprocess_mask(root/'data/raw'/source.mask_path) if source.mask_path else np.zeros((256,256),bool)
            amap=np.load(run/'anomaly_maps'/f'{record.image_id}.npy');scored=pred[pred.image_id==record.image_id].iloc[0]
            axes[r,0].imshow(rgb);axes[r,1].imshow(mask,cmap='gray',vmin=0,vmax=1)
            heat=axes[r,2].imshow(amap,cmap='magma',vmin=0,vmax=vmax)
            axes[r,3].imshow(rgb);axes[r,3].imshow(amap,cmap='magma',vmin=0,vmax=vmax,alpha=.55)
            if mask.any():axes[r,3].contour(mask,levels=[.5],colors=['cyan'],linewidths=1)
            axes[r,4].imshow(amap>pixel_threshold,cmap='gray',vmin=0,vmax=1)
            reasons='; '.join(json.loads(record.reasons))
            if record.image_id in lookup.index:
                diagnostic=lookup.loc[record.image_id]
                detail=f'{diagnostic.source_defect_label} | area {diagnostic.mask_area_fraction:.2%} | AP {diagnostic.per_image_pixel_ap:.3f} | peak in mask {diagnostic.peak_inside_mask}'
            else:detail='Normal | implicit zero annotation | pixel AP undefined'
            axes[r,0].set_title(reasons+'\n'+f'score {scored.primary_score:.3f}; frozen threshold {threshold:.3f}',fontsize=8,wrap=True)
            axes[r,1].set_title('Source mask at 256',fontsize=9);axes[r,2].set_title('Raw map; shared scale',fontsize=9)
            axes[r,3].set_title('Overlay; cyan annotation',fontsize=9);axes[r,4].set_title('Frozen pixel-threshold mask',fontsize=9)
            axes[r,2].set_xlabel(textwrap.fill(detail,width=36),fontsize=8)
            for ax in axes[r]:ax.set_xticks([]);ax.set_yticks([])
        fig.colorbar(heat,ax=axes[:,2],label='Raw nearest-patch distance',shrink=.6)
        fig.savefig(out/f'contact_sheet_{page:02d}.png',bbox_inches='tight');plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',default='.');parser.add_argument('--output',default='artifacts/pcb1_a2')
    args=parser.parse_args();render(args.root,args.output)

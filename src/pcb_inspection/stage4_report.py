"""Post-confirmation artifact comparison; never fits, calibrates or scores images."""
import argparse
from datetime import datetime
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageOps

from .guard import digest, now, write_new

RUNS=[('D1 primary',256,'pcb2_d1_primary'),('D2 secondary',512,'pcb2_d2_secondary')]


def summarize(metrics):
    image=metrics['image'];local=metrics['anomaly_localization']['common256_']
    return {**{k:image[k] for k in ['tp','fp','fn','tn','recall','normal_false_alarm_rate','average_precision','auroc']},
            'median_pixel_ap':local['median_per_image_pixel_ap'],'q25':local['q25'],'q75':local['q75'],
            'pooled_pixel_ap':metrics['localization_common256']['pixel_average_precision'],
            'pixel_iou':metrics['localization_common256']['pixel_iou'],
            'peak_inside_count':local['peak_inside_count'],'overlap_count':local['overlap_count'],
            'median_inference_seconds':metrics['runtime']['median_inference_seconds'],
            'p95_inference_seconds':metrics['runtime']['p95_inference_seconds']}


def bars(plt,table,columns,output,title):
    fig,axes=plt.subplots(1,len(columns),figsize=(4*len(columns),4.4),squeeze=False)
    for ax,(column,label,upper) in zip(axes.flat,columns):
        values=table[column];bars=ax.bar(np.arange(len(table)),values,color=['#3b8064','#977198'][:len(table)])
        ax.set_xticks(np.arange(len(table)),table.recipe,fontsize=9);ax.set_ylim(0,upper*1.15);ax.set_title(label,fontsize=11)
        for bar,value in zip(bars,values):ax.text(bar.get_x()+bar.get_width()/2,value+upper*.02,f'{value:.3f}' if upper==1 else f'{value:.2f}',ha='center',fontsize=9)
    fig.suptitle(title);fig.tight_layout(rect=(0,0,1,.91));fig.savefig(output,dpi=145);plt.close(fig)


def grouped(plt,table,column,output,title):
    fig,ax=plt.subplots(figsize=(11,5));groups=table.group.unique();x=np.arange(len(groups))
    for j,(name,_,_) in enumerate(RUNS):
        sub=table[table.recipe==name].set_index('group').reindex(groups)
        ax.bar(x+(j-.5)*.35,sub[column],.35,label=name)
    ax.set_ylabel('Anomaly recall' if column == 'recall' else 'Median anomaly pixel AP');ax.set_xticks(x,groups);ax.set_ylim(0,1.12);ax.set_title(title);ax.legend(loc='upper center',bbox_to_anchor=(.5,-.12),ncol=2)
    fig.subplots_adjust(bottom=.25,top=.88);fig.savefig(output,dpi=145);plt.close(fig)


def report(root):
    root=Path(root).resolve();base=root/'artifacts/stage4';out=base/'comparison'
    if (out/'comparison_complete.json').exists():raise FileExistsError('Completed report is immutable')
    out.mkdir(exist_ok=True);figures=out/'figures';figures.mkdir(exist_ok=True)
    config=json.loads((root/'configs/stage4_protocol.json').read_text())
    rows=[];preds={};metrics={};paths=set();runtime_rows=[];phase_rows=[]
    for name,size,run in RUNS:
        folder=base/run
        review=json.loads((folder/'independent_review.json').read_text());assert review['passed']
        m=json.loads((folder/'metrics.json').read_text());metrics[name]=m
        rows.append({'recipe':name,'category':'PCB2','size':size,**summarize(m)})
        rt=json.loads((folder/'normal_runtime.json').read_text());mem=m['memory']
        started=json.loads((folder/'prepare_started.json').read_text())['started_at_utc'];finished=json.loads((folder/'prepared.json').read_text())['completed_at_utc']
        calendar=(datetime.fromisoformat(finished)-datetime.fromisoformat(started)).total_seconds()
        runtime_rows.append({'recipe':name,'measured_perf_counter_preparation_seconds':rt['preparation_seconds'],'utc_preparation_span_seconds':calendar,'calendar_span_not_bounded_by_frozen_perf_counter_gate':True,'normal_preparation_peak_rss_bytes':rt['peak_rss_bytes'],'normal_median_inference_seconds':rt['median_inference_seconds'],'evaluation_peak_rss_bytes':m['runtime']['peak_rss_bytes'],**mem})
        for phase,values in rt['phases'].items():phase_rows.append({'recipe':name,'phase':phase,**values})
        preds[name]=pd.read_csv(folder/'predictions.csv')
        paths.update(folder/n for n in ['metrics.json','predictions.csv','independent_review.json','complete.json','calibration_predictions.csv','calibration.json','normal_runtime.json','prepare_started.json','prepared.json'])
    table=pd.DataFrame(rows);table.to_csv(out/'d1_vs_d2.csv',index=False)
    pd.DataFrame(runtime_rows).to_csv(out/'runtime.csv',index=False)
    pd.DataFrame(phase_rows).to_csv(out/'runtime_phases.csv',index=False)
    historical=[]
    for name,size,_ in RUNS:
        path=root/f'artifacts/runs/coreset_{size}_v1/metrics.json';paths.add(path)
        historical.append({'recipe':name,'category':'PCB1 development','size':size,**summarize(json.loads(path.read_text()))})
    comparison=pd.concat([pd.DataFrame(historical),table],ignore_index=True);comparison.to_csv(out/'pcb1_vs_pcb2.csv',index=False)
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    bars(plt,table,[('recall','Recall ↑',1),('normal_false_alarm_rate','Normal FPR ↓',1),('average_precision','Image AP ↑',1),('auroc','AUROC ↑',1)],figures/'detection.png','Fresh PCB2: primary first; secondary remains secondary')
    bars(plt,table,[('median_pixel_ap','Median anomaly pixel AP ↑',1),('pixel_iou','Pixel IoU ↑',1),('peak_inside_count','Peak inside / anomalies ↑',100)],figures/'localization.png','Full-source common 256 localization; AP is not probability')
    bars(plt,table,[('median_inference_seconds','Median CPU seconds ↓',max(table.median_inference_seconds)),('normal_false_alarm_rate','Normal FPR ↓',1)],figures/'runtime_review_burden.png','Processing cost and normal review burden')
    # All scores are kept on each recipe's own scale; no post-result threshold search.
    fig,axes=plt.subplots(1,2,figsize=(12,4.5));score_records=[]
    for ax,(name,size,run) in zip(axes,RUNS):
        folder=base/run;cal=pd.read_csv(folder/'calibration_predictions.csv');pred=preds[name]
        threshold=json.loads((folder/'calibration.json').read_text())['image_threshold']
        scorecolumn='image_score' if 'image_score' in pred else 'score'
        calcolumn='image_score' if 'image_score' in cal else 'score'
        for group,values in [('Calibration normals',cal[calcolumn]),('Held-out normals',pred.loc[pred.label=='normal',scorecolumn]),('Anomalies',pred.loc[pred.label=='anomaly',scorecolumn])]:
            ax.hist(values,bins=20,alpha=.45,label=group);score_records.extend({'recipe':name,'group':group,'score':float(v)} for v in values)
        ax.axvline(threshold,color='black',linestyle='--',label='Frozen normal threshold');ax.set_title(name);ax.set_xlabel('Raw image score');ax.set_ylabel('Images');ax.legend(fontsize=8)
    fig.suptitle('No anomaly-driven threshold adjustment');fig.tight_layout(rect=(0,0,1,.92));fig.savefig(figures/'score_distributions.png',dpi=145);plt.close(fig)
    pd.DataFrame(score_records).to_csv(out/'score_distributions.csv',index=False)
    types=[];sizes=[];quartiles=[]
    edges=np.asarray(config['size_slices']['edges'])
    for name,size,run in RUNS:
        a=preds[name][preds[name].label=='anomaly'].copy()
        area='common256_mask_area_fraction' if 'common256_mask_area_fraction' in a else 'mask_area_fraction'
        ap='common256_per_image_pixel_ap' if 'common256_per_image_pixel_ap' in a else 'pixel_ap'
        flag='anomaly_flag' if 'anomaly_flag' in a else 'predicted_anomaly'
        if flag not in a:flag='detected'
        def row(group,sub):return {'recipe':name,'group':group,'count':len(sub),'detected':int(sub[flag].sum()),'recall':float(sub[flag].mean()) if len(sub) else None,'median_pixel_ap':float(sub[ap].median()) if len(sub) else None}
        parsed=a.defect_types.fillna('[]').map(json.loads)
        alltypes=sorted({label for values in parsed for label in values})
        for kind in alltypes:types.append(row(kind,a[parsed.map(lambda values:kind in values)]))
        band=np.searchsorted(edges,a[area],side='left');qe=np.quantile(a[area],[.25,.5,.75],method='higher');q=np.searchsorted(qe,a[area],side='left')
        for j in range(4):sizes.append(row(f'PCB1 area band {j+1}',a[band==j]));quartiles.append({**row(f'PCB2 Q{j+1}',a[q==j]),'q25_edge':qe[0],'q50_edge':qe[1],'q75_edge':qe[2]})
    for filename,records in [('defect_type.csv',types),('defect_size.csv',sizes),('pcb2_size_quartiles.csv',quartiles)]:pd.DataFrame(records).to_csv(out/filename,index=False)
    if types:grouped(plt,pd.DataFrame(types),'recall',figures/'defect_type_recall.png','Source types may overlap; image counts are not independent defects')
    grouped(plt,pd.DataFrame(sizes),'median_pixel_ap',figures/'defect_size.png','Fixed PCB1 reference area bands on PCB2; not PCB2 quartiles')
    original=pd.read_csv(root/'artifacts/pcb1_memory_selection_comparison/comparison.csv')
    fig,ax=plt.subplots(figsize=(12,4.5));names=['Stage1 PCB1','Stage2 C1 PCB1','Stage2 C2 PCB1','Stage3 D1 PCB1','Stage3 D2 PCB1','Stage4 D1 PCB2','Stage4 D2 PCB2']
    values=list(original.recall)+list(table.recall);ax.bar(np.arange(7),values,color=['#999','#739ab3','#bba17b','#3b8064','#977198','#3b8064','#977198']);ax.set_ylim(0,1.12);ax.set_xticks(np.arange(7),[n.replace(' ','\n',1) for n in names],fontsize=9);ax.set_ylabel('Anomaly recall');ax.set_title('Project journey: PCB1 development and fresh PCB2 are different categories')
    for i,v in enumerate(values):ax.text(i,v+.02,f'{v:.0%}',ha='center')
    fig.tight_layout();fig.savefig(figures/'journey.png',dpi=145);plt.close(fig)
    paths.update([root/'configs/stage4_protocol.json',base/'freeze_receipt.json',root/'artifacts/pcb1_memory_selection_comparison/comparison.csv'])
    metadata_path=out/'report_metadata.json'
    if metadata_path.exists():metadata_path.unlink()
    write_new(metadata_path,{'created_at_utc':now(),'new_model_inference':False,'primary_unchanged':'D1 256','sources':{str(p.relative_to(root)):digest(p) for p in sorted(paths)},'outputs':{str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()},'qualitative_status':'Root must generate fixed rule contact sheet before completion','interpretation':'Category-adapted confirmation, not causal selector comparison or factory claim'})
    print('Report tables and figures saved; fixed qualitative and root interpretation still required.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');a=p.parse_args();report(a.root)

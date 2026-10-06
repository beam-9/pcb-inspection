"""Build Stage6A exported research figures and artifact-only notebook, once."""
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image, ImageOps
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import nbformat
from pcb_inspection.guard import digest, now, write_new

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'artifacts/stage6a'; FIG=OUT/'figures'
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'})
COLORS={'hit':'#386e9f','miss':'#cb7938'}

def main():
    FIG.mkdir(exist_ok=False)
    frame=pd.read_csv(OUT/'per_recipe_diagnostics.csv'); cases=pd.read_csv(OUT/'case_diagnosis.csv')
    d2=frame[frame.recipe=='d2'].copy(); metadata=[]
    def save(fig,name,ids,source):
        fig.tight_layout(rect=(0,0,1,.9 if fig._suptitle else 1)); fig.savefig(FIG/name,dpi=150);plt.close(fig)
        metadata.append({'path':str((FIG/name).relative_to(ROOT)),'image_ids':list(ids),'source':source,'sha256':digest(FIG/name)})
    miss=d2[~d2.detected]
    flags=miss.failure_category if 'failure_category' in miss else cases.set_index('image_id').loc[miss.image_id].failure_category
    counts={f:int(flags.str.split('|',regex=False).map(lambda x:f in x).sum()) for f in ['F1','F2','F3','F4','F5']}
    fig,ax=plt.subplots(figsize=(8,4));ax.bar(counts.keys(),counts.values(),color=COLORS['miss']);ax.set(ylim=(0,max(counts.values())+1),ylabel='Images with flag (overlap allowed)',title=f'Failure flags on {len(miss)} distinct D2 misses')
    save(fig,'failure_category_summary.png',miss.image_id,'case_diagnosis.csv')
    fig,ax=plt.subplots(figsize=(7,6))
    for detected,marker in [(True,'o'),(False,'X')]:
        sub=d2[d2.detected==detected];ax.scatter(sub.gt_max_ratio,sub.outside_gt_ratio,marker=marker,color=COLORS['hit' if detected else 'miss'],label=f'{"Detected" if detected else "Missed"} (n={len(sub)})',alpha=.8)
    ax.axhline(1,color='#666',ls='--');ax.axvline(1,color='#666',ls='--');ax.set(xlabel='Native GT max / image threshold',ylabel='Native outside-GT max / image threshold',title='D2 + orientation: GT versus outside response');ax.legend()
    save(fig,'gt_vs_outside_gt.png',d2.image_id,'per_recipe_diagnostics.csv')
    fig,ax=plt.subplots(figsize=(8,4))
    groups=[('canonical_missing_miss','Missing miss'),('canonical_missing_hit','Missing hit'),('small_miss','Small miss'),('small_hit','Small hit'),('marginal_reversed_rescue','Reversed rescue')]
    for i,(key,label) in enumerate(groups):
        sub=d2[d2.groups.str.contains(key)];ax.scatter(np.full(len(sub),i)+np.linspace(-.12,.12,len(sub)),sub.first_gt_patch_rank,marker='X' if key.endswith('_miss') else 'o',color=COLORS['miss' if key.endswith('_miss') else 'hit'])
    ax.set_xticks(range(len(groups)),[f'{label}\nn={int(d2.groups.str.contains(key).sum())}' for key,label in groups]);ax.set(yscale='log',ylabel='First GT-overlap patch rank (log)',title='D2 patch ranks; cohorts overlap');ax.axhline(3,color='#999',ls='--');ax.axhline(20,color='#999',ls=':')
    save(fig,'patch_rank_distribution.png',d2.image_id,'patch_rank_diagnostics.csv; target_manifest.csv')
    distances=pd.read_csv(OUT/'feature_distance.csv'); values=distances[distances.recipe=='d2'].groupby('image_id').nearest_distance_ratio.median()
    fig,ax=plt.subplots(figsize=(9,4))
    for i,(key,label) in enumerate(groups):
        sub=d2[d2.groups.str.contains(key)];ax.scatter(np.full(len(sub),i)+np.linspace(-.12,.12,len(sub)),values.loc[sub.image_id],marker='X' if key.endswith('_miss') else 'o',color=COLORS['miss' if key.endswith('_miss') else 'hit'])
    ax.set_xticks(range(len(groups)),[f'{label}\nn={int(d2.groups.str.contains(key).sum())}' for key,label in groups]);ax.set(ylabel='Per-image median GT nearest\ndistance / threshold',title='D2 frozen reference distance by outcome; cohorts overlap')
    save(fig,'nearest_reference_distance.png',d2.image_id,'feature_distance.csv; target_manifest.csv')
    fig,axes=plt.subplots(1,2,figsize=(11,5))
    for detected,marker in [(True,'o'),(False,'X')]:
        sub=cases[cases.d2_detected==detected];color=COLORS['hit' if detected else 'miss']
        axes[0].scatter(sub.d1_gt_max_ratio,sub.d2_gt_max_ratio,marker=marker,color=color,label='hit' if detected else 'miss')
        axes[1].scatter(sub.d1_pixel_ap,sub.d2_pixel_ap,marker=marker,color=color)
    for ax in axes:
        limits=ax.get_xlim()+ax.get_ylim();lo=min(0,min(limits));hi=max(limits);ax.plot([lo,hi],[lo,hi],ls='--',color='#888');ax.set_xlim(lo,hi);ax.set_ylim(lo,hi)
    axes[0].set(xlabel='D1 GT max / own threshold',ylabel='D2 GT max / own threshold');axes[1].set(xlabel='D1 common256 pixel AP',ylabel='D2 common256 pixel AP');axes[0].legend();fig.suptitle('Matched pose context; different banks and thresholds, not resolution causality')
    save(fig,'d1_vs_d2_evidence.png',cases.image_id,'case_diagnosis.csv')
    manifest=pd.read_csv(ROOT/'artifacts/stage4/confirmation_data/test_manifest.csv').set_index('image_id')
    paths={r:json.loads((ROOT/f'artifacts/{stage}/array_paths.json').read_text()) for r,stage in [('d1','stage5b'),('d2','stage5c')]}
    thresholds={r:json.loads((ROOT/f'artifacts/stage4/{base}/calibration.json').read_text())['pixel_threshold'] for r,base in [('d1','pcb2_d1_primary'),('d2','pcb2_d2_secondary')]}
    for key,name in [('canonical_missing_miss','canonical_missing_miss_contact_sheet'),('small_miss','small_defect_miss_contact_sheet')]:
        ids=list(d2[d2.groups.str.contains(key)].image_id)
        for page,start in enumerate(range(0,len(ids),4),1):
            pageids=ids[start:start+4];fig,axes=plt.subplots(len(pageids),4,figsize=(13,3.2*len(pageids)),squeeze=False)
            for axs,identity in zip(axes,pageids):
                source=manifest.loc[identity];result=d2[d2.image_id==identity].iloc[0]
                with Image.open(ROOT/source.image_path) as im:rgb=ImageOps.exif_transpose(im).convert('RGB');small=rgb.resize((256,256))
                with Image.open(ROOT/source.mask_path) as im:mask=ImageOps.exif_transpose(im).convert('L');gt=np.asarray(mask.resize((256,256),Image.Resampling.NEAREST))>0;raw=np.asarray(mask)>0
                axs[0].imshow(small);axs[0].contour(gt,levels=[.5],colors=['#2ac6c6'],linewidths=.8);axs[0].set_title(f'{identity[:10]} · {source.defect_types}\nGT outline; {result.size_band}',fontsize=10)
                ys,xs=np.where(raw);margin=30;box=(max(0,int(xs.min())-margin),max(0,int(ys.min())-margin),min(rgb.width,int(xs.max())+margin+1),min(rgb.height,int(ys.max())+margin+1))
                axs[1].imshow(rgb.crop(box));axs[1].set_title('Union-GT bounding box +30px\nMulti-label extent may be broad',fontsize=10)
                for ax,r in zip(axs[2:],['d1','d2']):
                    scores=np.load(ROOT/paths[r]['anomaly_maps']/f'{identity}.npy')/thresholds[r];rec=frame[(frame.image_id==identity)&(frame.recipe==r)].iloc[0]
                    view=ax.imshow(scores,cmap='magma',vmin=0,vmax=2);ax.contour(gt,levels=[.5],colors=['#2ac6c6'],linewidths=.8);ax.set_title(f'{r.upper()} map / pixel threshold\nimage ratio {rec.score_divided_by_threshold:.3f}; GT rank {rec.first_gt_patch_rank}',fontsize=10)
                for ax in axs:ax.axis('off')
            fig.suptitle(f'{key.replace("_"," ")} · page {page} · maps clipped0–2, shared scale')
            save(fig,f'{name}_{page}.png',pageids,'per_recipe_diagnostics.csv; frozen maps; original RGB/union masks')
    identity='bfebbd19caf4dad38fd66eab';fig,axes=plt.subplots(1,4,figsize=(14,4))
    with Image.open(ROOT/manifest.loc[identity,'mask_path']) as im:gt=np.asarray(im.convert('L').resize((256,256),Image.Resampling.NEAREST))>0
    with Image.open(ROOT/manifest.loc[identity,'image_path']) as im:axes[0].imshow(im.convert('RGB').resize((256,256)));axes[0].contour(gt,levels=[.5],colors=['#2ac6c6']);axes[0].set_title('Reversed rescue\nOriginal RGB + GT')
    for ax,stage,base,label in zip(axes[1:],['stage4/pcb2_d2_secondary','stage5b','stage5c'],['pcb2_d2_secondary','pcb2_d1_primary','pcb2_d2_secondary'],['Historical D2','D1 + orientation','D2 + orientation']):
        ap=json.loads((ROOT/f'artifacts/{stage}/array_paths.json').read_text());pt=json.loads((ROOT/f'artifacts/stage4/{base}/calibration.json').read_text())['pixel_threshold'];it=json.loads((ROOT/f'artifacts/stage4/{base}/calibration.json').read_text())['image_threshold']
        scores=np.load(ROOT/ap['anomaly_maps']/f'{identity}.npy')/pt;pred=pd.read_csv(ROOT/f'artifacts/{stage}/predictions.csv');rec=pred[pred.image_id==identity].iloc[0]
        ax.imshow(scores,cmap='magma',vmin=0,vmax=2);ax.contour(gt,levels=[.5],colors=['#2ac6c6']);ax.set_title(f'{label}\nimage / threshold {rec.score/it:.4f}')
    for ax in axes:ax.axis('off')
    fig.suptitle('Marginal reversed rescue; maps / own pixel threshold clipped0–2')
    save(fig,'marginal_rescue_comparison.png',[identity],'historical D2 and Stage5B/5C frozen maps/predictions')
    write_new(OUT/'figure_metadata.json',{'created_at_utc':now(),'figures':metadata,'scales':'maps / own pixel threshold clipped0–2; ranking log axis; raw feature distances normalized within recipe only'})
    notebook=ROOT/'notebooks/pcb2_stage6a_diagnosis.ipynb'
    if notebook.exists():raise FileExistsError(notebook)
    nb=nbformat.v4.new_notebook(cells=[nbformat.v4.new_markdown_cell('# Stage6A — Remaining canonical failures\nArtifact reader only. No fitting, calibration, inference, or changed decisions. See the journey chapter for the decision gate.'),nbformat.v4.new_code_cell("from pathlib import Path\nimport json\nimport pandas as pd\nfrom IPython.display import display, Image\nroot = Path.cwd()\nif not (root/'artifacts/stage6a').exists(): root = root.parent\nout = root/'artifacts/stage6a'\nassert json.loads((out/'independent_review.json').read_text())['passed']\ncases = pd.read_csv(out/'case_diagnosis.csv')\ndisplay(cases)"),nbformat.v4.new_code_cell("display(pd.read_csv(out/'patch_rank_diagnostics.csv'))\ndisplay(pd.read_csv(out/'aggregation_diagnostics.csv'))\nd = pd.read_csv(out/'feature_distance.csv')\ndisplay(d.groupby(['recipe','image_id'])[['nearest_reference_distance','median_top5_reference_distance']].median())"),nbformat.v4.new_code_cell("metadata=json.loads((out/'figure_metadata.json').read_text())\nfor figure in metadata['figures']:\n    display(Image(filename=str(root/figure['path'])))\ndisplay(json.loads((out/'decision_gate.json').read_text()))")])
    nb.metadata['kernelspec']={'display_name':'Python 3','language':'python','name':'python3'};nbformat.write(nb,notebook)

if __name__=='__main__':main()

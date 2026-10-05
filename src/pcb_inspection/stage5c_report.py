"""Saved-map figures for the fixed Stage5C population; no model inference."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from .guard import digest,write_new,now


def build(root):
    root=Path(root).resolve();out=root/'artifacts/stage5c';figures=out/'figures';figures.mkdir(exist_ok=False)
    protocol=json.loads((out/'orientation_protocol.json').read_text());ids=protocol['reversed_ids']
    signal=pd.read_csv(out/'results/four_recipe_signal.csv').set_index(['image_id','recipe'])
    manifest=pd.read_csv(root/'artifacts/stage4/pcb2_d2_secondary/confirmation_manifest.csv').set_index('image_id')
    directories={'historical_D1':'artifacts/stage4/pcb2_d1_primary','stage5B_D1_orientation':'artifacts/stage5b','historical_D2':'artifacts/stage4/pcb2_d2_secondary','stage5C_D2_orientation':'artifacts/stage5c'}
    paths={key:json.loads((root/path/'array_paths.json').read_text()) for key,path in directories.items()}
    sources={};maps={};masks={};images={}
    def bind(path):sources[str(Path(path).relative_to(root))]=digest(path)
    for path in [out/'results/four_recipe_signal.csv',out/'results/runtime.csv',out/'results/reversed_paired_d2.csv',Path(__file__)]:bind(path)
    for image_id in ids:
        row=manifest.loc[image_id];bind(root/row.image_path);bind(root/row.mask_path)
        images[image_id]=Image.open(root/row.image_path).convert('RGB').resize((256,256))
        masks[image_id]=np.asarray(Image.open(root/row.mask_path).resize((256,256),Image.Resampling.NEAREST))>0
        for recipe,p in paths.items():
            path=root/p['anomaly_maps']/f'{image_id}.npy';bind(path);maps[image_id,recipe]=np.load(path)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    def save(fig,name):fig.savefig(figures/(name+'.png'),dpi=150);plt.close(fig)
    def map_panel(ax,image_id,recipe,details=False):
        row=signal.loc[(image_id,recipe)];artist=ax.imshow(maps[image_id,recipe]/row.pixel_threshold,cmap='magma',vmin=0,vmax=3)
        ax.contour(masks[image_id],levels=[.5],colors=['#72c9d1'],linewidths=.7)
        if details:ax.set_xlabel(f'score/t={row.score_divided_by_threshold:.3f}; detected={row.detected}\nAP={row.pixel_ap:.3f}; FP={int(row.fp_pixels):,}\nGT/t={row.gt_max_divided_by_pixel_threshold:.3f}; outside/t={row.outside_gt_max_divided_by_pixel_threshold:.3f}')
        ax.set_xticks([]);ax.set_yticks([]);return artist
    fig,axes=plt.subplots(5,5,figsize=(17,16),constrained_layout=True)
    for i,image_id in enumerate(ids):
        axes[i,0].imshow(images[image_id]);axes[i,0].contour(masks[image_id],levels=[.5],colors=['#72c9d1'],linewidths=.7);axes[i,0].set_ylabel(image_id[:12])
        for j,recipe in enumerate(['historical_D2','stage5C_D2_orientation','stage5B_D1_orientation'],1):a=map_panel(axes[i,j],image_id,recipe)
        threshold=signal.loc[(image_id,'historical_D2'),'pixel_threshold'];delta=(maps[image_id,'stage5C_D2_orientation']-maps[image_id,'historical_D2'])/threshold
        d=axes[i,4].imshow(delta,cmap='coolwarm',vmin=-3,vmax=3);axes[i,4].contour(masks[image_id],levels=[.5],colors=['#72c9d1'],linewidths=.7)
        for ax in axes[i]:ax.set_xticks([]);ax.set_yticks([])
    for ax,title in zip(axes[0],['Source + union GT','Historical D2','Stage5C orientation D2','Stage5B orientation D1','Stage5C − historical D2']):ax.set_title(title)
    fig.colorbar(a,ax=axes[:,1:4],shrink=.55,label='Score / own frozen pixel threshold; not probability');fig.colorbar(d,ax=axes[:,4],shrink=.55,label='Delta / D2 pixel threshold')
    fig.suptitle('All five reversed PCB2 anomalies · common256 original coordinates · D1/D2 context is not resolution causality');save(fig,'reversed_d2_before_after')
    fig,axes=plt.subplots(1,5,figsize=(19,5),constrained_layout=True);image_id='bfebbd19caf4dad38fd66eab'
    axes[0].imshow(images[image_id]);axes[0].contour(masks[image_id],levels=[.5],colors=['#72c9d1'],linewidths=.7)
    for ax,recipe in zip(axes[1:],directories):a=map_panel(ax,image_id,recipe,True)
    for ax,title in zip(axes,['Source + GT','Historical D1','Stage5B orientation D1','Historical D2','Stage5C orientation D2']):ax.set_title(title);ax.set_xticks([]);ax.set_yticks([])
    fig.colorbar(a,ax=axes[1:],shrink=.6,label='Map / own pixel threshold');fig.suptitle('Stage5B lost case · bfebbd19caf4dad38fd66eab · four recipes');save(fig,'lost_case_256_vs_512')
    fig,axes=plt.subplots(5,2,figsize=(9,17),constrained_layout=True)
    for i,image_id in enumerate(ids):
        for ax,recipe in zip(axes[i],['stage5B_D1_orientation','stage5C_D2_orientation']):a=map_panel(ax,image_id,recipe,True)
        axes[i,0].set_ylabel(image_id[:12])
    axes[0,0].set_title('Stage5B orientation D1');axes[0,1].set_title('Stage5C orientation D2');fig.colorbar(a,ax=axes,shrink=.5,label='Map / own pixel threshold');fig.suptitle('Cross-recipe context · not pure resolution causality');save(fig,'orientation_256_vs_512')
    paired=pd.read_csv(out/'results/reversed_paired_d2.csv').set_index('image_id').loc[ids]
    for field,ylabel,name in [('fp_pixels','FP pixels, common256','reversed_fp_pixels'),('pixel_ap','Per-image pixel average precision','reversed_pixel_ap')]:
        fig,ax=plt.subplots(figsize=(10,5),constrained_layout=True);x=np.arange(5)
        ax.bar(x-.18,paired['historical_'+field],.36,color='#566b82',label='Historical D2');ax.bar(x+.18,paired['normalized_'+field],.36,color='#b97530',label='Stage5C orientation D2')
        ax.set_xticks(x,[v[:12] for v in ids]);ax.set_ylabel(ylabel);ax.set_ylim(bottom=0);ax.legend();ax.set_title('All five reversed anomalies · matched D2 comparison');save(fig,name)
    fig,axes=plt.subplots(5,3,figsize=(11,15),constrained_layout=True)
    for i,image_id in enumerate(ids):
        t=signal.loc[(image_id,'historical_D2'),'pixel_threshold'];old=maps[image_id,'historical_D2'];new=maps[image_id,'stage5C_D2_orientation'];g=masks[image_id]
        d=axes[i,0].imshow((new-old)/t,cmap='coolwarm',vmin=-3,vmax=3)
        for ax,array in zip(axes[i,1:],[(old>t)&(new<=t),(new>t)&(old<=t)]):
            ax.imshow(array,cmap='gray',vmin=0,vmax=1);ax.set_xlabel(f'Outside GT {int((array&~g).sum()):,}; inside {int((array&g).sum()):,}')
        for ax in axes[i]:ax.contour(g,levels=[.5],colors=['#72c9d1'],linewidths=.7);ax.set_xticks([]);ax.set_yticks([])
        axes[i,0].set_ylabel(image_id[:12])
    for ax,title in zip(axes[0],['Delta / D2 threshold','Removed exceedances','Added exceedances']):ax.set_title(title)
    fig.colorbar(d,ax=axes[:,0],shrink=.55);fig.suptitle('Matched D2 common256 map changes · original union GT');save(fig,'reversed_map_differences')
    timing=pd.read_csv(out/'results/runtime.csv');cols=['decode_seconds','geometry_seconds','pose_seconds','tensor_preparation_seconds','feature_extraction_seconds','nearest_scoring_and_historical_inverse_seconds','inverse_map_seconds','end_to_end_seconds']
    fig,ax=plt.subplots(figsize=(13,5),constrained_layout=True);x=np.arange(len(cols))
    ax.bar(x-.18,[timing[c].median()*1000 for c in cols],.36,color='#566b82',label='Median');ax.bar(x+.18,[timing[c].quantile(.95)*1000 for c in cols],.36,color='#b97530',label='p95')
    ax.set_xticks(x,[c.replace('_seconds','').replace('_','\n') for c in cols]);ax.set_ylabel('Milliseconds per image');ax.set_ylim(bottom=0);ax.legend();ax.set_title('Stage5C timers · nested inverse/rotation costs disclosed; do not sum bars');save(fig,'runtime')
    write_new(out/'figure_metadata.json',{'created_at_utc':now(),'new_inference':False,'scale':'own frozen pixel threshold, magma0..3; signed D2 delta -3..3','sources':sources,'outputs':{str(p.relative_to(root)):digest(p) for p in figures.glob('*.png')}})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');args=p.parse_args();build(args.root)

"""Saved Stage4 outcome summaries after image-only pose labels were finalized."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from .guard import digest,now,write_new
from .stage5a_pose import LABELS

def build_pose_report(root):
    root=Path(root);out=root/'artifacts/stage5a/pose'
    final=json.loads((out/'labels_final.json').read_text())
    if digest(out/'pose_labels.csv')!=final['label_sha256']:raise ValueError('Final image-only pose labels changed')
    if digest(root/'src/pcb_inspection/stage5a_pose.py')!=final['classifier_code_sha256']:raise ValueError('Image-only classifier changed')
    if (out/'pose_diagnostic_table.csv').exists():raise FileExistsError('Refuse diagnostic overwrite')
    labels=pd.read_csv(out/'pose_labels.csv',keep_default_na=False).set_index('image_id')
    test=pd.read_csv(root/'artifacts/stage4/confirmation_data/test_manifest.csv',keep_default_na=False).set_index('image_id')
    frame=test[['label','defect_types']].rename(columns={'label':'normal_or_anomaly','defect_types':'source_labels'})
    frame=frame.join(labels[['pose_label']],validate='one_to_one');inputs={}
    for recipe,name in [('d1','pcb2_d1_primary'),('d2','pcb2_d2_secondary')]:
        base=root/'artifacts/stage4'/name
        complete=json.loads((base/'complete.json').read_text())
        for file in ['predictions.csv','metrics.json']:
            path=base/file;relative=str(path.relative_to(root))
            if digest(path)!=complete['outputs'][relative]:raise ValueError('Frozen Stage4 output changed')
            inputs[relative]=digest(path)
        scores=pd.read_csv(base/'predictions.csv').set_index('image_id')
        if set(scores.index)!=set(frame.index) or scores.index.duplicated().any():raise ValueError('Evaluation identity coverage differs')
        scores=scores.loc[frame.index]
        if not scores.label.equals(frame.normal_or_anomaly):raise ValueError('Saved outcome labels differ')
        area=np.rint(scores.mask_area_fraction*256**2).astype('int64')
        fp=scores.union.astype('int64')-area
        positive=fp+scores.intersection.astype('int64')
        if (fp<0).any() or (positive<0).any():raise ValueError('Inconsistent per-image pixel accounting')
        metrics=json.loads((base/'metrics.json').read_text())
        if int(scores.intersection.sum())!=metrics['localization_common256']['intersection_pixels'] or int(scores.union.sum())!=metrics['localization_common256']['union_pixels']:raise ValueError('Saved pooled accounting differs')
        mapping={'score':'image_score','detected':'flag','pixel_ap':'pixel_ap','peak_inside':'peak_inside','overlap':'any_overlap','intersection':'intersection_pixels','union':'union_pixels'}
        for source,target in mapping.items():frame[recipe+'_'+target]=scores[source]
        frame[recipe+'_false_positive_pixels']=fp;frame[recipe+'_positive_predicted_pixels']=positive
        for field in [recipe+'_peak_inside',recipe+'_any_overlap']:frame[field]=frame[field].astype('boolean')
        frame.loc[frame.normal_or_anomaly=='normal',[recipe+'_pixel_ap',recipe+'_peak_inside',recipe+'_any_overlap']]=None
        if recipe=='d1':frame['mask_area']=area.where(frame.normal_or_anomaly=='anomaly')
        elif not np.array_equal(area.fillna(0),frame.mask_area.fillna(0)):raise ValueError('Mask denominator differs by recipe')
    frame=frame.reset_index();frame.to_csv(out/'pose_diagnostic_table.csv',index=False)
    rows=[]
    for recipe in ['d1','d2']:
        total=frame[recipe+'_false_positive_pixels'].sum()
        for pose in LABELS:
            part=frame[frame.pose_label==pose];norm=part[part.normal_or_anomaly=='normal'];anom=part[part.normal_or_anomaly=='anomaly'];ap=anom[recipe+'_pixel_ap'];fp=part[recipe+'_false_positive_pixels']
            rows.append({'recipe':recipe,'pose_label':pose,'n_images':len(part),'n_normals':len(norm),'n_anomalies':len(anom),
                'recall':anom[recipe+'_flag'].mean(),'normal_FPR':norm[recipe+'_flag'].mean(),
                'median_image_score_normal':norm[recipe+'_image_score'].median(),'median_image_score_anomaly':anom[recipe+'_image_score'].median(),
                'median_pixel_AP':ap.median(),'Q25_pixel_AP':ap.quantile(.25),'Q75_pixel_AP':ap.quantile(.75),
                'peak_inside_fraction':anom[recipe+'_peak_inside'].mean(),'any_overlap_fraction':anom[recipe+'_any_overlap'].mean(),
                'median_false_positive_pixels':fp.median(),'median_predicted_positive_pixels':part[recipe+'_positive_predicted_pixels'].median(),
                'median_intersection_pixels':part[recipe+'_intersection_pixels'].median(),'median_union_pixels':part[recipe+'_union_pixels'].median(),
                'total_false_positive_pixels':fp.sum(),'share_of_all_false_positive_pixels':fp.sum()/total,
                'p90_false_positive_pixels':fp.quantile(.9),'max_false_positive_pixels':fp.max()})
    summary=pd.DataFrame(rows);summary.to_csv(out/'pose_summary.csv',index=False)
    # A transparent image-only sensitivity grouping: uncertain examples were
    # visually canonical-layout cue failures before any outcome joins.
    sensitivity=frame.copy();sensitivity['pose_label']=sensitivity.pose_label.replace({'uncertain':'canonical_or_cue_failure'})
    sensitivity['pose_label']=sensitivity.pose_label.replace({'canonical':'canonical_or_cue_failure'})
    sensitivity.groupby(['pose_label','normal_or_anomaly']).agg(n_images=('image_id','size'),d1_fp_median=('d1_false_positive_pixels','median'),d2_fp_median=('d2_false_positive_pixels','median'),d1_pixel_ap_median=('d1_pixel_ap','median'),d2_pixel_ap_median=('d2_pixel_ap','median')).reset_index().to_csv(out/'visually_canonical_sensitivity.csv',index=False)
    for filename,field,title,anomaly_only in [('pose_fp_pixels.png','false_positive_pixels','False-positive pixels (all evaluation images)',False),('pose_pixel_ap.png','pixel_ap','Pixel AP (anomalies only)',True)]:
        fig,axes=plt.subplots(1,2,figsize=(11,4),sharey=True)
        for ax,recipe in zip(axes,['d1','d2']):
            source=frame[frame.normal_or_anomaly=='anomaly'] if anomaly_only else frame
            for i,pose in enumerate(LABELS):
                values=source[source.pose_label==pose][recipe+'_'+field].dropna().to_numpy()
                if len(values):
                    ax.scatter(i+np.linspace(-.13,.13,len(values)),values,s=15,alpha=.5)
                    ax.plot([i-.2,i+.2],[np.median(values)]*2,color='black',linewidth=2)
            ax.set_xticks(range(3),['Canonical','Reversed (n=5)','Uncertain cue (n=5)']);ax.set_title(recipe.upper());ax.grid(axis='y',alpha=.25)
            if not anomaly_only:ax.set_yscale('symlog',linthresh=100)
        axes[0].set_ylabel(title);fig.suptitle('Post-confirmation PCB2 diagnosis');fig.tight_layout();fig.savefig(out/filename,dpi=160);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(11,7),sharey='row')
    for row,kind in enumerate(['normal','anomaly']):
        for col,recipe in enumerate(['d1','d2']):
            ax=axes[row,col];part=frame[frame.normal_or_anomaly==kind]
            for i,pose in enumerate(LABELS):
                values=part[part.pose_label==pose][recipe+'_image_score'].to_numpy()
                ax.scatter(i+np.linspace(-.13,.13,len(values)),values,s=15,alpha=.5)
            ax.set_xticks(range(3),['Canonical','Reversed','Uncertain cue']);ax.set_title(f'{recipe.upper()} {kind}');ax.grid(axis='y',alpha=.25)
    fig.suptitle('Image scores by pose; no reversed or uncertain normals available');fig.tight_layout();fig.savefig(out/'pose_scores.png',dpi=160);plt.close(fig)
    concentration=[];fig,axes=plt.subplots(1,2,figsize=(12,5))
    colors={'canonical':'#477da8','reversed_180':'#d86643','uncertain':'#b59b44'}
    for ax,recipe in zip(axes,['d1','d2']):
        top=frame.sort_values([recipe+'_false_positive_pixels','image_id'],ascending=[False,True]).head(10)
        ax.barh(range(len(top)),top[recipe+'_false_positive_pixels'],color=top.pose_label.map(colors))
        ax.set_yticks(range(len(top)),[f'{r.image_id[:8]} {r.pose_label}' for r in top.itertuples()],fontsize=8);ax.invert_yaxis();ax.set_title(recipe.upper());ax.set_xlabel('False-positive common256 pixels')
        for rank,row in enumerate(top.to_dict('records'),1):concentration.append({'recipe':recipe,'rank':rank,**row})
    fig.tight_layout();fig.savefig(out/'pose_error_concentration.png',dpi=160);plt.close(fig);pd.DataFrame(concentration).to_csv(out/'largest_fp_contributors.csv',index=False)
    # Matched examples use median D1 FP within each binary-label/pose cell,
    # ties ascending ID; impossible reversed-normal cell is explicitly absent.
    representative=[]
    for kind in ['normal','anomaly']:
        for pose in LABELS:
            part=frame[(frame.normal_or_anomaly==kind)&(frame.pose_label==pose)].copy()
            if not len(part):continue
            part['median_distance']=(part.d1_false_positive_pixels-part.d1_false_positive_pixels.median()).abs()
            representative.append(part.sort_values(['median_distance','image_id']).iloc[0].to_dict())
    pd.DataFrame(representative).to_csv(out/'representative_selection.csv',index=False)
    fig,axes=plt.subplots(len(representative),3,figsize=(10,3*len(representative)),squeeze=False)
    for index,row in enumerate(representative):
        identity=row['image_id'];raw=Image.open(root/test.loc[identity,'image_path']).convert('RGB').resize((256,256))
        axes[index,0].imshow(raw);axes[index,0].set_title(f"{row['normal_or_anomaly']} {row['pose_label']}\n{identity[:12]}")
        for col,recipe,name in [(1,'d1','pcb2_d1_primary'),(2,'d2','pcb2_d2_secondary')]:
            map_path=root/'data/cache/stage4'/name/'anomaly_maps'/f'{identity}.npy'
            bound=json.loads((root/'artifacts/stage4'/name/'complete.json').read_text())['outputs'][str(map_path.relative_to(root))]
            if digest(map_path)!=bound:raise ValueError('Frozen qualitative map changed')
            inputs[str(map_path.relative_to(root))]=bound
            array=np.load(map_path)
            axes[index,col].imshow(raw);axes[index,col].imshow(array,cmap='magma',alpha=.55)
            axes[index,col].set_title(f'{recipe.upper()} saved map, own colour scale')
        for ax in axes[index]:ax.axis('off')
    fig.suptitle('Median-FP examples within available groups; reversed normal unavailable');fig.tight_layout();fig.savefig(out/'pose_representative_heatmaps.png',dpi=150);plt.close(fig)
    lines=['# Pose diagnostic findings','', 'Post-confirmation PCB2 development diagnosis. Labels were finalized from image-only cues before this outcome join. Prior Stage4 visual knowledge remains acknowledged.','']
    for recipe in ['d1','d2']:
        canonical=summary[(summary.recipe==recipe)&(summary.pose_label=='canonical')].iloc[0];reverse=summary[(summary.recipe==recipe)&(summary.pose_label=='reversed_180')].iloc[0]
        lines.append(f"{recipe.upper()}: reversed5 images contribute {reverse.share_of_all_false_positive_pixels:.1%} of all FP pixels; medianFP {reverse.median_false_positive_pixels:.0f} vs canonical {canonical.median_false_positive_pixels:.0f}. Median anomaly pixelAP {reverse.median_pixel_AP:.3f} vs canonical {canonical.median_pixel_AP:.3f}; reversed recall {reverse.recall:.0%}.")
    lines+=['','All1001 normals are canonical, so reversed-normal false-alarm behavior is unestimable. The5uncertain cases have canonical-looking layouts with damaged/absent pin cues; they remain uncertain and are not evidence of180-degree reversal. Small reversed n, defect confounding and already-exposed data prevent a causal pose claim. Registration has not been tested.','', 'False-positive counts are union minus ground-truth mask area; predicted-positive counts add intersection. All200 saved image IDs and pooled intersection/union denominators match frozen Stage4 results. No detector was run.']
    (out/'pose_findings.md').write_text('\n'.join(lines)+'\n')
    write_new(out/'pose_diagnostics_complete.json',{'completed_at_utc':now(),'scope':'Post-confirmation PCB2 development diagnosis','label_final_receipt_sha256':digest(out/'labels_final.json'),
        'label_sha256':final['label_sha256'],'new_inference':False,'frozen_detector_changed':False,'inputs':inputs,'code_sha256':digest(Path(__file__)),
        'outputs':{str(p.relative_to(root)):digest(p) for p in out.iterdir() if p.is_file()}})
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');a=p.parse_args();print(build_pose_report(a.root).to_string(index=False))

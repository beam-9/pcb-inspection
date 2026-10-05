"""Post-confirmation missing-label tracing against unchanged Stage4 reference banks."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageOps
from scipy.ndimage import binary_dilation
import torch
from torch.nn import functional as F
from .guard import digest, now, write_new

RUNS = [(256,'pcb2_d1_primary'),(512,'pcb2_d2_secondary')]
RADII = (.05,.10,.20)


def require_writable(root):
    if (Path(root).resolve()/'artifacts/stage5a/diagnostics.json').exists():
        raise FileExistsError('Published Stage5A diagnostics are immutable')


def coordinates(row,column,t):
    mx,my=(column+.5)*8,(row+.5)*8
    nx=(mx-t['pad_x'])/t['content_width'];ny=(my-t['pad_y'])/t['content_height']
    x0,y0,x1,y1=t['crop_box']
    return {'feature_row':int(row),'feature_column':int(column),'model_x':mx,'model_y':my,
            'crop_normalized_x':nx,'crop_normalized_y':ny,
            'source_x':x0+nx*(x1-x0),'source_y':y0+ny*(y1-y0),
            'padding_center':not(0<=nx<1 and 0<=ny<1)}


def query_regions(mask,t):
    """Explicit 8x8 grid-cell footprints, not the backbone receptive field."""
    mask=np.asarray(mask,dtype=bool);s=t['input_size'];grid=s//8
    if mask.shape!=(t['source_height'],t['source_width']):raise ValueError('Source mask geometry differs')
    x0,y0,x1,y1=t['crop_box'];rw,rh=t['content_width'],t['content_height'];px,py=t['pad_x'],t['pad_y']
    a=np.zeros((s,s),bool)
    a[py:py+rh,px:px+rw]=np.asarray(Image.fromarray(mask[y0:y1,x0:x1]).resize((rw,rh),Image.Resampling.NEAREST),bool)
    fraction=a.reshape(grid,8,grid,8).mean(axis=(1,3));overlap=fraction>0
    context=binary_dilation(overlap,structure=np.ones((3,3),bool),iterations=1)&~overlap
    return overlap,context,fraction


def top_neighbors(query,bank,k=5):
    if query.ndim!=2 or bank.ndim!=2 or query.shape[1]!=bank.shape[1] or not 1<=k<=len(bank):raise ValueError('Paired query/bank dimensions required')
    distances=[];indices=[];ties=[]
    for q in query.split(128):
        d=torch.cdist(q,bank,p=2,compute_mode='donot_use_mm_for_euclid_dist')
        if not torch.isfinite(d).all():raise ValueError('Nonfinite distance')
        # Stable sorting gives exact float32 ties the lowest frozen bank index first.
        order=torch.argsort(d,dim=1,stable=True)[:,:k]
        distances.append(torch.gather(d,1,order));indices.append(order)
        ties.append((d==d.min(1).values[:,None]).sum(1))
    return torch.cat(distances).numpy(),torch.cat(indices).numpy(),torch.cat(ties).numpy()


def extract(root):
    require_writable(root)
    from .geometry_experiment import DynamicExtractor,setup,score_feature
    from .stage4_geometry import tensor_and_transform
    root=Path(root).resolve();stage=root/'artifacts/stage4';out=root/'artifacts/stage5a/missing_component'
    out.mkdir(parents=True,exist_ok=True)
    if (out/'extraction_complete.json').exists():raise FileExistsError('Trace extraction already complete')
    config=json.loads((root/'configs/stage4_protocol.json').read_text())
    frame=pd.read_csv(stage/'confirmation_data/test_manifest.csv').fillna('')
    missing=frame[frame.defect_types.map(lambda v:'missing' in json.loads(v or '[]'))].sort_values('image_id')
    if len(missing)!=19:raise ValueError('Expected all19 source missing-label images')
    fit=pd.read_csv(stage/'pcb2_normals/normal_manifest.csv').query("split=='fit'").set_index('image_id')
    sources={};rows=[];cases=[];checks=[]
    setup(root);ext=DynamicExtractor()
    for size,run in RUNS:
        folder=stage/run;review=json.loads((folder/'independent_review.json').read_text());assert review['passed'] and review['complete_sha256']==digest(folder/'complete.json')
        paths=json.loads((folder/'array_paths.json').read_text());bank=torch.from_numpy(np.load(root/paths['memory']))
        refs=json.loads((folder/'memory_metadata.json').read_text())['references']
        transforms=json.loads((folder/'test_transforms.json').read_text());rt=json.loads((folder/'fit_reference_transforms.json').read_text())
        predictions=pd.read_csv(folder/'predictions.csv').set_index('image_id')
        for name in ['complete.json','predictions.csv','memory_metadata.json','test_transforms.json','fit_reference_transforms.json','independent_review.json']:
            sources[str((folder/name).relative_to(root))]=digest(folder/name)
        sources[paths['memory']]=digest(root/paths['memory'])
        for row in missing.itertuples():
            tensor,t=tensor_and_transform(root,row,size,config)
            if t!=transforms[row.image_id]:raise ValueError('Saved transform differs')
            feat=ext(tensor[None]);score,model,common=score_feature(feat,bank,size,t)
            stored=np.load(root/paths['model_maps']/f'{row.image_id}.npy')
            raw_error=float(np.abs(model-stored).max())
            if raw_error>1e-5 or abs(score-float(predictions.loc[row.image_id,'score']))>1e-5:raise ValueError('Frozen raw map/score mismatch')
            with Image.open(root/row.mask_path) as im:mask=np.asarray(ImageOps.exif_transpose(im).convert('L'))>0
            overlap,context,fraction=query_regions(mask,t);grid=size//8
            positions=np.argwhere(overlap|context)
            if not len(positions):raise ValueError('No projected mask/context gridcells')
            query=feat[0,:,positions[:,0],positions[:,1]].T.contiguous()
            values,indices,ties=top_neighbors(query,bank)
            # Independent float64 direct subtraction for a fixed systematic query subset.
            for qi in np.unique(np.linspace(0,len(query)-1,min(5,len(query)),dtype=int)):
                exact=np.sqrt(((bank.numpy().astype(np.float64)-query[qi].numpy().astype(np.float64))**2).sum(1));order=np.argsort(exact,kind='stable')[:5]
                err=float(np.max(np.abs(exact[indices[qi]]-values[qi])))
                if err>1e-5 or np.max(np.abs(exact[indices[qi]]-exact[order]))>1e-5:raise ValueError('Independent nearest-distance verification failed')
                checks.append({'image_id':row.image_id,'size':size,'query_index':int(qi),'distance_max_error':err,'raw_map_max_error':raw_error})
            ys,xs=np.where(mask);cx,cy=float(xs.mean()),float(ys.mean())
            cases.append({'image_id':row.image_id,'size':size,'source_labels':row.defect_types,'source_mask_pixels':int(mask.sum()),'centroid_x':cx,'centroid_y':cy,
                'bbox_x0':int(xs.min()),'bbox_y0':int(ys.min()),'bbox_x1':int(xs.max()+1),'bbox_y1':int(ys.max()+1),
                'union_mask_multitype':len(json.loads(row.defect_types))>1,'overlap_queries':int(overlap.sum()),'context_queries':int(context.sum()),
                'annotation_outside_crop_fraction':1-float(mask[t['crop_box'][1]:t['crop_box'][3],t['crop_box'][0]:t['crop_box'][2]].sum()/mask.sum())})
            for qi,(r,c) in enumerate(positions):
                q=coordinates(r,c,t)
                for rank,(distance,index) in enumerate(zip(values[qi],indices[qi]),1):
                    ref=refs[int(index)]
                    if ref['memory_index']!=int(index) or ref['image_id'] not in fit.index:raise ValueError('Reference outside frozen fitting bank')
                    rc=coordinates(ref['row'],ref['column'],rt[ref['image_id']])
                    displacement=math.hypot(q['crop_normalized_x']-rc['crop_normalized_x'],q['crop_normalized_y']-rc['crop_normalized_y'])/math.sqrt(2)
                    rows.append({'query_image_id':row.image_id,'size':size,'query_id':int(r*grid+c),'query_set':'defect_overlap' if overlap[r,c] else 'context_ring',
                        'query_mask_fraction':float(fraction[r,c]),'query_overlaps_mask':bool(overlap[r,c]),'query_score':float(values[qi,0]),'top1_exact_tie_count':int(ties[qi]),
                        **{'query_'+key:value for key,value in q.items()},'neighbor_rank':rank,'memory_index':int(index),'reference_image_id':ref['image_id'],
                        **{'reference_'+key:value for key,value in rc.items()},'distance':float(distance),'spatial_displacement_crop_diagonal':displacement,
                        **{f'within_radius_{radius:.2f}':displacement<=radius for radius in RADII}})
            print('Frozen missing trace',size,row.image_id,'queries',len(positions),flush=True)
    pd.DataFrame(rows).to_csv(out/'nn_trace_raw.csv',index=False)
    pd.DataFrame(cases).to_csv(out/'missing_regions.csv',index=False)
    pd.DataFrame(checks).to_csv(out/'independent_distance_checks.csv',index=False)
    sources[str((stage/'confirmation_data/test_manifest.csv').relative_to(root))]=digest(stage/'confirmation_data/test_manifest.csv')
    sources['configs/stage4_protocol.json']=digest(root/'configs/stage4_protocol.json')
    write_new(out/'extraction_complete.json',{'completed_at_utc':now(),'post_confirmation_development_diagnosis':True,'detector_changed':False,'cases':19,'sizes':[256,512],
        'sources':sources,'outputs':{p.name:digest(p) for p in out.glob('*.csv')},'query_definition':'Nearest-resized source union mask through exact crop/letterbox, anypositive in 8x8 gridcell; onecell8-connected dilation ring. Footprint is not receptive field.',
        'spatial_definition':'Crop coordinates (modelcenter-padding)/content; Euclidean displacement divided sqrt2. Padding may exceed normalized crop range; not registered pose.',
        'radii':list(RADII),'distance':'Frozen full384 direct Euclidean top5 all4096; stable exact ties lowestbankindex','semantic_limit':'Multi-type union annotations cannot isolate missing components. Distant coordinates do not establish wrong anatomical matches.'})


def summarize(root,pose_path):
    require_writable(root)
    root=Path(root).resolve();out=root/'artifacts/stage5a/missing_component';pose=pd.read_csv(root/pose_path)
    receipt_path=(root/pose_path).with_name('labels_final.json')
    if not receipt_path.is_file():raise ValueError('Final image-only pose review receipt required')
    if json.loads(receipt_path.read_text())['label_sha256']!=digest(root/pose_path):raise ValueError('Reviewed pose labels changed')
    extraction=json.loads((out/'extraction_complete.json').read_text())
    for path,expected in extraction['sources'].items():
        if digest(root/path)!=expected:raise ValueError('Frozen source changed')
    for path,expected in extraction['outputs'].items():
        if digest(out/path)!=expected:raise ValueError('Raw trace artifact changed')
    if pose.image_id.duplicated().any():raise ValueError('Unique pose image IDs required')
    labels=pose.set_index('image_id').pose_label
    trace=pd.read_csv(out/'nn_trace_raw.csv');regions=pd.read_csv(out/'missing_regions.csv')
    if not set(trace.query_image_id).issubset(labels.index):raise ValueError('All query pose labels must be available before associations')
    trace['query_pose']=trace.query_image_id.map(labels);trace['reference_pose']=trace.reference_image_id.map(labels).fillna('not_labeled')
    cases=[];summary=[]
    d1=pd.read_csv(root/'artifacts/stage4/pcb2_d1_primary/predictions.csv').set_index('image_id');d2=pd.read_csv(root/'artifacts/stage4/pcb2_d2_secondary/predictions.csv').set_index('image_id')
    for row in regions.itertuples():
        hit1,hit2=bool(d1.loc[row.image_id,'detected']),bool(d2.loc[row.image_id,'detected'])
        group={(False,False):'M1 both miss',(False,True):'M2 D2 rescue',(True,True):'M3 both hit',(True,False):'M4 D1 only'}[(hit1,hit2)]
        cases.append({**{key:value for key,value in row._asdict().items() if key!='Index'},'pose_label':labels[row.image_id],'outcome_group':group,'d1_flag':hit1,'d2_flag':hit2,'d1_pixel_ap':d1.loc[row.image_id,'pixel_ap'],'d2_pixel_ap':d2.loc[row.image_id,'pixel_ap']})
    caseframe=pd.DataFrame(cases);caseframe.to_csv(out/'missing_case_recipes.csv',index=False)
    for (identity,size,queryset),sub in trace.groupby(['query_image_id','size','query_set']):
        record={'image_id':identity,'size':size,'query_set':queryset,'pose_label':labels[identity], 'outcome_group':caseframe.query('image_id==@identity').iloc[0].outcome_group,
            'n_queries':sub.query_id.nunique(),'n_pairs':len(sub),'median_embedding_distance':float(sub.distance.median()),'median_query_score':float(sub[sub.neighbor_rank==1].distance.median()),
            'median_spatial_displacement':float(sub.spatial_displacement_crop_diagonal.median()),'minimum_spatial_displacement':float(sub.spatial_displacement_crop_diagonal.min()),
            'top1_median_spatial_displacement':float(sub[sub.neighbor_rank==1].spatial_displacement_crop_diagonal.median()),'query_padding_fraction':float(sub.query_padding_center.mean()),'reference_padding_fraction':float(sub.reference_padding_center.mean())}
        for radius in RADII:record[f'local_fraction_{radius:.2f}']=float(sub[f'within_radius_{radius:.2f}'].mean())
        record['cross_location_fraction']=1-record['local_fraction_0.10'];summary.append(record)
    trace.to_csv(out/'nn_trace.csv',index=False);summ=pd.DataFrame(summary);summ.to_csv(out/'nn_spatial_displacement.csv',index=False)
    wide=caseframe[caseframe['size']==256].drop(columns=['size','overlap_queries','context_queries','annotation_outside_crop_fraction']).copy().set_index('image_id')
    for size,prefix in [(256,'d1'),(512,'d2')]:
        sub=summ[(summ['size']==size)&(summ.query_set=='defect_overlap')].set_index('image_id')
        wide[prefix+'_nn_median_distance']=sub.median_embedding_distance
        wide[prefix+'_nn_spatial_median']=sub.median_spatial_displacement
        for radius,tag in [(.05,'005'),(.10,'010'),(.20,'020')]:wide[prefix+'_cross_location_r'+tag]=1-sub[f'local_fraction_{radius:.2f}']
    wide.to_csv(out/'missing_cases.csv')
    # Image-weighted summaries avoid treating numerous patch pairs as independent images.
    summ.groupby(['size','query_set','pose_label','outcome_group']).agg(n_images=('image_id','nunique'),median_distance=('median_embedding_distance','median'),median_displacement=('median_spatial_displacement','median'),median_cross_location_fraction=('cross_location_fraction','median')).to_csv(out/'group_summary.csv')
    contexts=trace[['size','memory_index','reference_image_id','reference_padding_center']].drop_duplicates()
    contexts['context_label']='uncertain';contexts['review_status']='not_semantically_reviewed';contexts['criteria']='No semantic component/background assignment inferred from position or distance; padding_center is separate geometric proxy.'
    contexts.to_csv(out/'reference_context_labels.csv',index=False)
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for column,name,title in [('median_spatial_displacement','missing_hit_vs_miss.png','Frozen normal NN displacement; crop-diagonal units'),('cross_location_fraction','cross_location_fraction.png','Top 5 fraction beyond declared 0.10 radius')]:
        fig,axes=plt.subplots(1,2,figsize=(12,4.5))
        for ax,size in zip(axes,[256,512]):
            sub=summ[(summ['size']==size)&(summ.query_set=='defect_overlap')];groups=sorted(sub.outcome_group.unique())
            for pose,marker,color in [('canonical','o','#377eb8'),('reversed_180','^','#e07031'),('uncertain','x','#777777')]:
                for i,g in enumerate(groups):
                    v=sub[(sub.outcome_group==g)&(sub.pose_label==pose)].sort_values('image_id')[column]
                    ax.scatter(i+np.linspace(-.07,.07,len(v)),v,alpha=.8,marker=marker,color=color,label=pose if i==0 else None)
            ax.set_xticks(range(len(groups)),groups,rotation=15,ha='right');ax.set_title(f'{size}: each dot one image');ax.set_ylabel(column.replace('_',' '));ax.set_ylim(0,1.05)
        axes[0].legend(loc='upper left');fig.suptitle(title);fig.tight_layout();fig.savefig(out/name,dpi=145);plt.close(fig)
    write_new(out/'summary_complete.json',{'created_at_utc':now(),'pose_sha256':digest(root/pose_path),'extraction_sha256':digest(out/'extraction_complete.json'),'semantic_context_labels':'All uncertain; no anatomical causal claims','image_weighted':True})


def sheets(root):
    require_writable(root)
    root=Path(root).resolve();out=root/'artifacts/stage5a/missing_component';dest=out/'trace_sheets';dest.mkdir(exist_ok=True)
    trace=pd.read_csv(out/'nn_trace.csv');cases=pd.read_csv(out/'missing_case_recipes.csv');manifest=pd.concat([pd.read_csv(root/'artifacts/stage4/confirmation_data/test_manifest.csv'),pd.read_csv(root/'artifacts/stage4/pcb2_normals/normal_manifest.csv')]).drop_duplicates('image_id').set_index('image_id')
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    selected=[]
    for case in cases.itertuples():
        sub=trace[(trace.query_image_id==case.image_id)&(trace['size']==case.size)&(trace.query_set=='defect_overlap')&(trace.neighbor_rank==1)].copy()
        sub['centroid_distance']=(sub.query_source_x-case.centroid_x)**2+(sub.query_source_y-case.centroid_y)**2
        chosen=sub.sort_values(['centroid_distance','query_id']).iloc[0];neighbors=trace[(trace.query_image_id==case.image_id)&(trace['size']==case.size)&(trace.query_id==chosen.query_id)].sort_values('neighbor_rank')
        fig,axes=plt.subplots(3,3,figsize=(12,10));axs=axes.flat
        row=manifest.loc[case.image_id]
        with Image.open(root/row.image_path) as im:source=ImageOps.exif_transpose(im).convert('RGB');sw,sh=source.size;rgb=np.asarray(source.resize((256,256)))
        axs[0].imshow(rgb);axs[0].plot(chosen.query_source_x/sw*256,chosen.query_source_y/sh*256,'rx');axs[0].set_title('Query: nearest mask centroid gridcell')
        with Image.open(root/row.mask_path) as im:mask=np.asarray(ImageOps.exif_transpose(im).convert('L').resize((256,256),Image.Resampling.NEAREST))>0
        axs[1].imshow(mask,cmap='gray');axs[1].set_title('Whole-source union annotation')
        run=dict(RUNS)[case.size];paths=json.loads((root/f'artifacts/stage4/{run}/array_paths.json').read_text());threshold=json.loads((root/f'artifacts/stage4/{run}/calibration.json').read_text())['pixel_threshold']
        axs[2].imshow(np.load(root/paths['anomaly_maps']/f'{case.image_id}.npy')/threshold,cmap='magma',vmin=0,vmax=2);axs[2].set_title('Map / frozen threshold, clipped0–2')
        transform=json.loads((root/f'artifacts/stage4/{run}/test_transforms.json').read_text())[case.image_id]
        x0,y0,x1,y1=transform['crop_box'];rx=12*(x1-x0)/transform['content_width'];ry=12*(y1-y0)/transform['content_height']
        box=(max(0,int(chosen.query_source_x-rx)),max(0,int(chosen.query_source_y-ry)),min(sw,int(chosen.query_source_x+rx)),min(sh,int(chosen.query_source_y+ry)))
        axs[3].imshow(source.crop(box));axs[3].set_title('Query3×3 gridcell context (not RF)')
        for ax,ref in zip(list(axes.flat)[4:],neighbors.itertuples()):
            record=manifest.loc[ref.reference_image_id]
            with Image.open(root/record.image_path) as im:normal=ImageOps.exif_transpose(im).convert('RGB');w,h=normal.size;normal=np.asarray(normal.resize((256,256)))
            ax.imshow(normal);ax.plot(ref.reference_source_x/w*256,ref.reference_source_y/h*256,'rx');ax.set_title(f'#{ref.neighbor_rank} {ref.reference_image_id[:8]} d={ref.distance:.3f}\ndisp={ref.spatial_displacement_crop_diagonal:.3f}; see context review',fontsize=9)
        for ax in axes.flat:ax.axis('off')
        fig.suptitle(f'{case.image_id} · {case.size} · {case.outcome_group} · pose {case.pose_label}\nAll19cases; geometrychosenquery, not peak. X: exactcellcenter; fullnormalcontext. Unionmaskmultitype={case.union_mask_multitype}',fontsize=10)
        fig.tight_layout(rect=(0,0,1,.91));fig.savefig(dest/f'{case.size}_{case.image_id}.png',dpi=120);plt.close(fig)
        selected.append({'image_id':case.image_id,'size':case.size,'query_id':chosen.query_id,'selection':'defect-overlap cell center nearest source union-mask centroid; query_id ties','path':str((dest/f'{case.size}_{case.image_id}.png').relative_to(root))})
    pd.DataFrame(selected).to_csv(out/'trace_sheet_selection.csv',index=False)


def review_sheets(root):
    require_writable(root)
    """Bounded semantic review: first fullID in each actual outcome group, both sizes."""
    root=Path(root).resolve();out=root/'artifacts/stage5a/missing_component';dest=out/'reference_review_sheets';dest.mkdir(exist_ok=True)
    cases=pd.read_csv(out/'missing_case_recipes.csv').sort_values('image_id').groupby(['size','outcome_group'],sort=True).head(1)
    selection=pd.read_csv(out/'trace_sheet_selection.csv');trace=pd.read_csv(out/'nn_trace.csv')
    normal=pd.read_csv(root/'artifacts/stage4/pcb2_normals/normal_manifest.csv').set_index('image_id');records=[]
    for case in cases.itertuples():
        query=selection[(selection.image_id==case.image_id)&(selection['size']==case.size)].iloc[0]
        sub=trace[(trace.query_image_id==case.image_id)&(trace['size']==case.size)&(trace.query_id==query.query_id)].sort_values('neighbor_rank')
        transforms=json.loads((root/f'artifacts/stage4/{dict(RUNS)[case.size]}/fit_reference_transforms.json').read_text())
        canvas=Image.new('RGB',(640,5*300),(245,245,245));draw=ImageDraw.Draw(canvas)
        for i,ref in enumerate(sub.itertuples()):
            with Image.open(root/normal.loc[ref.reference_image_id,'image_path']) as im:image=ImageOps.exif_transpose(im).convert('RGB')
            w,h=image.size;full=image.resize((256,256));d=ImageDraw.Draw(full);sx,sy=ref.reference_source_x/w*256,ref.reference_source_y/h*256;d.ellipse((sx-3,sy-3,sx+3,sy+3),outline='red',width=2)
            t=transforms[ref.reference_image_id];x0,y0,x1,y1=t['crop_box'];rx=12*(x1-x0)/t['content_width'];ry=12*(y1-y0)/t['content_height']
            cx,cy=ref.reference_source_x,ref.reference_source_y;patch=image.crop((int(cx-rx),int(cy-ry),int(cx+rx),int(cy+ry))).resize((256,256))
            d=ImageDraw.Draw(patch);d.ellipse((125,125,131,131),outline='red',width=2)
            canvas.paste(full,(5,i*300+35));canvas.paste(patch,(320,i*300+35));draw.text((5,i*300+5),f'rank{ref.neighbor_rank} bank{ref.memory_index} ref{ref.reference_image_id[:10]} padding={ref.reference_padding_center}',fill='black')
            records.append({'query_image_id':case.image_id,'size':case.size,'outcome_group':case.outcome_group,'query_id':int(query.query_id),'neighbor_rank':ref.neighbor_rank,'memory_index':ref.memory_index,'reference_image_id':ref.reference_image_id,'context_label':'uncertain','review_status':'pending_visual_review','criteria':'Full source plus3x3gridcell context; redcenter. Component=visible package/body centered; emptyboard=unpopulated blue substrate centered; mixed/boundary/lowdetail=uncertain. This is not receptivefield or semantic correspondence.'})
        canvas.save(dest/f'{case.size}_{case.image_id}.png')
    pd.DataFrame(records).to_csv(out/'selected_reference_context_review.csv',index=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['extract','summarize','sheets','review-sheets']);p.add_argument('--root',default='.');p.add_argument('--pose',default='artifacts/stage5a/pose/pose_labels.csv');a=p.parse_args()
    if a.action=='extract':extract(a.root)
    elif a.action=='summarize':summarize(a.root,a.pose)
    elif a.action=='sheets':sheets(a.root)
    else:review_sheets(a.root)

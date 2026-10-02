"""Build and execute an artifact-reading report, without rerunning the benchmark."""
from pathlib import Path
import json
import nbformat as nbf
from nbclient import NotebookClient

ROOT=Path(__file__).resolve().parents[1]
prepared=json.loads((ROOT/'artifacts/prepared.json').read_text())
run=ROOT/prepared['path']; metrics=json.loads((run/'metrics.json').read_text())
nb=nbf.v4.new_notebook()
nb.metadata.kernelspec={'display_name':'Python 3','language':'python','name':'python3'}
md=nbf.v4.new_markdown_cell; code=nbf.v4.new_code_cell
nb.cells=[
md(f'''# VisA PCB1: frozen visual-inspection pilot

## tl;dr

Primary image AP **{metrics['primary']['average_precision']:.3f}**, versus baseline **{metrics['baseline']['average_precision']:.3f}**. Primary recall **{metrics['primary']['recall']:.1%}** and false-alarm rate **{metrics['primary']['normal_false_alarm_rate']:.1%}** at the normal-calibrated frozen threshold. Pixel AP **{metrics['localization']['pixel_average_precision']:.3f}**, measured at 256-square geometry including normal images.

**Recommendation: stop/revise methodology.** Both methods miss 57/100 anomalies at the frozen thresholds. Primary pooled pixel AP hides uneven small-region localization: median per-anomaly AP is0.039 and the map peak is inside the annotation for 26/100 anomalies.

This executed notebook reads saved predictions/maps and independently verified metrics. It does not retrain, change thresholds, or access a new final benchmark.

## Context & Methods

VisA PCB1 is a public controlled-defect benchmark, not Seagate data. Official training normals are split seed42 into 723 fit/181 calibration; official test has 100 normals and100 anomalies. Frozen ResNet18 layer2/layer3 features feed a GAP/L2 nearest-normal baseline and a 4096 uniform-patch **PatchCore-inspired** memory. Normal95th image/99th pixel quantiles use `higher` and strictly-greater flags. Full-board256-square resizing departs from official ImageNet preprocessing.

### Key Assumptions

Physical-board IDs are unavailable; image disjointness is not proof of unseen-object independence. Pixel AP pools spatially dependent pixels descriptively; no independent-pixel confidence intervals are claimed. Benchmark prevalence 50% does not describe factory prevalence. Commercial weight rights remain unverified.

Sources: [owner VisA](https://github.com/amazon-science/spot-diff), [official PatchCore](https://github.com/amazon-science/patchcore-inspection), and `docs/source_research.md`.'''),
code('''from pathlib import Path
import json, sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image
root=Path.cwd()
if root.name=='notebooks': root=root.parent
sys.path.insert(0,str(root/'src'))
from pcb_inspection.guard import digest,verify_frozen
from pcb_inspection.preprocessing import preprocess_mask
prepared=json.loads((root/'artifacts/prepared.json').read_text())
run=root/prepared['path']
protocol=json.loads((root/'docs/protocol.json').read_text())
verify_frozen(root,protocol)
verification=json.loads((run/'verification.json').read_text())
assert verification['passed'] and verification['run_id']==prepared['run_id']
assert verification['completion_sha256']==digest(run/'final_complete.json')
metrics=json.loads((run/'metrics.json').read_text())
thresholds=json.loads((run/'calibration.json').read_text())
predictions=pd.read_parquet(run/'predictions.parquet')
manifest=pd.read_csv(run/'split_manifest.csv',keep_default_na=False).set_index('image_id')
plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':130})
print('Frozen run:',prepared['run_id'],'; independently verified:',verification['passed'])'''),
md('## Data\n\nAll1104 source images decoded; no exclusions or exact duplicate groups. The1261 coarse training-only perceptual-hash candidates were investigated numerically on20 pairs; similar aligned boards are not assumed to be the same object. All100 masks remain nonempty after resizing.'),
code('''audit=json.loads((root/'data/manifests/pcb1_audit.json').read_text())
pd.DataFrame([{'split/label':k,'images':v} for k,v in audit['counts'].items()])'''),
md('## Results\n\n### Ranking and frozen operating thresholds\n\nBoth methods use identical test membership. Average precision has a50% anomaly prevalence reference, rather than an expected factory prevalence.'),
code('''columns=['average_precision','auroc','tp','fp','fn','tn','precision','recall','normal_false_alarm_rate']
pd.DataFrame({name:{key:metrics[name][key] for key in columns} for name in ['baseline','primary']}).T.round(4)'''),
code('''fig,axes=plt.subplots(1,2,figsize=(11,3.8),layout='constrained')
for ax,name in zip(axes,['baseline','primary']):
    bins=np.linspace(predictions[name+'_score'].min(),predictions[name+'_score'].max(),26)
    for label,color,style in [(0,'#2364aa','-'),(1,'#b36a13','--')]:
        ax.hist(predictions.loc[predictions.label==label,name+'_score'],bins=bins,alpha=.55,color=color,label=('Normal (n=100)' if label==0 else 'Anomaly (n=100)'),histtype='stepfilled',linestyle=style)
    ax.axvline(thresholds[name]['image_threshold'],color='#333333',linestyle=':',label='Frozen normal-only threshold')
    ax.set(title=name.capitalize()+' score separation',xlabel='Raw anomaly score',ylabel='Test images')
    ax.legend(fontsize=8)
fig.savefig(run/'score_distributions.png',bbox_inches='tight')
plt.show()'''),
md('### Localization, including failure and false-alarm cases\n\nSelection is fixed retrospectively by score: lowest-scoring anomaly, highest-scoring normal, median-scoring anomaly, and highest-scoring anomaly. These examples cannot tune the method. Mask contours are retrospective benchmark annotations, not operational model evidence. One shared raw map scale is used; no per-image normalization.'),
code('''anomalies=predictions[predictions.label==1].sort_values(['primary_score','image_id'])
normals=predictions[predictions.label==0].sort_values(['primary_score','image_id'])
selected=[anomalies.iloc[0],normals.iloc[-1],anomalies.iloc[len(anomalies)//2],anomalies.iloc[-1]]
reasons=['Lowest-score anomaly','Highest-score normal','Median-score anomaly','Highest-score anomaly']
allmap_max=max(float(np.load(run/'anomaly_maps'/f'{i}.npy').max()) for i in predictions.image_id)
fig,axes=plt.subplots(4,3,figsize=(11,11),layout='constrained')
for r,(row,reason) in enumerate(zip(selected,reasons)):
    source=manifest.loc[row.image_id]
    with Image.open(root/'data/raw'/source.image_path) as image: rgb=np.asarray(image.convert('RGB').resize((256,256)))
    amap=np.load(run/'anomaly_maps'/f'{row.image_id}.npy')
    mask=preprocess_mask(root/'data/raw'/source.mask_path) if source.mask_path else np.zeros((256,256),bool)
    axes[r,0].imshow(rgb); axes[r,0].set_title(f'{reason} | score {row.primary_score:.2f}',fontsize=10)
    axes[r,1].imshow(rgb); axes[r,1].imshow(amap,cmap='magma',vmin=0,vmax=allmap_max,alpha=.55)
    if mask.any(): axes[r,1].contour(mask,levels=[.5],colors=['cyan'],linewidths=1)
    axes[r,1].set_title('Raw map; cyan source-mask contour',fontsize=10)
    axes[r,2].imshow(mask,cmap='gray',vmin=0,vmax=1)
    axes[r,2].set_title('Retrospective binary annotation',fontsize=10)
    for ax in axes[r]: ax.axis('off')
fig.colorbar(plt.cm.ScalarMappable(norm=plt.Normalize(0,allmap_max),cmap='magma'),ax=axes[:,1],label='Raw nearest-patch distance',shrink=.6)
fig.savefig(run/'localization_examples.png',bbox_inches='tight')
plt.show()
print('Pixel AP:',round(metrics['localization']['pixel_average_precision'],4),'global IoU:',round(metrics['localization']['pixel_iou'],4))'''),
md('### Uneven localization across anomalies\n\nPooled pixel AP weights annotation pixels, so a few large visible anomalies can dominate. This supplemental post-final check describes all 100 anomalies independently; it does not replace the predeclared pooled metric or tune the model.'),
code("""localization=pd.read_csv(root/'artifacts/review/anomaly_localization.csv')
summary=json.loads((root/'artifacts/review/localization_summary.json').read_text())
print(json.dumps(summary,indent=2))
fig,ax=plt.subplots(figsize=(8,3),layout='constrained')
ax.hist(localization.pixel_ap,bins=np.linspace(0,1,21),color='#2364aa',edgecolor='white')
ax.axvline(localization.pixel_ap.median(),linestyle=':',color='#333333',label=f'Median AP {localization.pixel_ap.median():.3f}')
ax.set(xlabel='Per-anomaly pixel average precision',ylabel='Anomalous images',title='Localization varies across all 100 anomalies')
ax.legend()
fig.savefig(run/'per_anomaly_localization.png',bbox_inches='tight')
plt.show()"""),
md('### Runtime and reference traceability\n\nLatency includes feature extraction and the relevant detector, measured on the actual CPU. Cold loads are separate. The two methods share features in the final loop. Independent verification checks all reference memberships/coordinates and recomputes scores plus winning patch references for three deterministic images.'),
code('''runtime=json.loads((run/'runtime.json').read_text())
pretest=json.loads((run/'pretest_runtime.json').read_text())
print(json.dumps({'runtime':runtime,'normal_preparation':pretest,'reference_trace_samples':verification['independent_patch_traces']},indent=2))'''),
md('## Takeaways\n\n**Stop/revise methodology.** Practical runtime and successful provenance checks do not overcome 57% missed anomalies or inconsistent localization. Preserve this result; do not tune against the viewed PCB1 test. Read `docs/pilot_findings.md` for the Phase A recommendation, unfavorable evidence and limits. No UI, LLM integration, remote publication or factory claim is part of this run. Small source defects, uniform-memory coverage, unknown physical-object identity, controlled acquisition and weight rights remain constraints.'),
]
path=ROOT/'notebooks/pcb1_pilot.ipynb'
nbf.validate(nb)
NotebookClient(nb,timeout=180,kernel_name='python3',resources={'metadata':{'path':str(ROOT)}}).execute()
nbf.write(nb,path)
print('Executed',path)

"""Materialize source-backed journey content and local preview assets, once."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image, ImageOps
from pcb_inspection.guard import digest, now, write_new

ROOT=Path(__file__).resolve().parents[1]
COMMIT='4abc845929bb0d67a1cf9b6882243adc8106b4ef'

def read(path):return json.loads((ROOT/path).read_text())

def metric(label,path,selector,fmt='decimal',row=None):
    if row:
        table=pd.read_csv(ROOT/path,float_precision='round_trip');data=table[table[row['column']]==row['value']].iloc[0];value=data[selector]
    else:
        value=read(path)
        for key in selector:value=value[key]
    if hasattr(value,'item'):value=value.item()
    return {'label':label,'value':value,'format':fmt,'source':{'path':path,'selector':selector,'row':row,'sha256':digest(ROOT/path)}}

def csvmetric(label,path,column,recipe,fmt='percent'):
    return metric(label,path,column,fmt,{'column':'recipe','value':recipe})

def stage(id,title,phase,question,change,learning,nextq,held,limits,metrics,figures,sources):
    return {'id':id,'title':title,'datasetPhase':phase,'question':question,'change':change,'learning':learning,
            'nextQuestion':nextq,'heldConstant':held,'limits':limits,'metrics':metrics,
            'figures':[{'path':p,'alt':alt,'sha256':digest(ROOT/'artifacts/productization/history_navigation/README.md' if p=='README.md' else ROOT/p)} for p,alt in figures],
            'sources':[{'path':p,'sha256':digest(ROOT/'artifacts/productization/history_navigation/README.md' if p=='README.md' else ROOT/p),'url':f'/evidence/{p}' if p.startswith('artifacts/model_v1/') else f'https://github.com/beam-9/pcb-inspection/blob/{COMMIT}/{p}'} for p in sources]}

def main():
    geometry='artifacts/pcb1_geometry_comparison/comparison.csv';memory='artifacts/pcb1_memory_selection_comparison/comparison.csv'
    transfer='artifacts/stage4/comparison/pcb1_vs_pcb2.csv';d1='artifacts/stage4/pcb2_d1_primary/metrics.json';d2='artifacts/stage4/pcb2_d2_secondary/metrics.json'
    b='artifacts/stage5b/results/modified_d1_metrics.json';c='artifacts/stage5c/results/full_metrics.json'
    stages=[];p1='PCB1 development';p2='PCB2 fresh confirmation';p3='PCB2 post-confirmation development'
    stages.append(stage('stage-1','A useful signal, a weak map',p1,'Can normal-reference features detect visible PCB anomalies at all?',
        'Direct 256 resize and frozen ResNet18 local features, scored against 4,096 uniform normal references.',
        'The local detector found useful signal, but recall and localization left substantial room for improvement.',
        'Does preserving board geometry and local detail help?', 'One-class normal fitting; frozen features and strict calibrated thresholds.',
        'These are PCB1 development results. The project is PatchCore-inspired, not a full reproduction of every PatchCore detail.',
        [csvmetric('Recall',geometry,'recall','Run1 direct256'),csvmetric('Normal FPR',geometry,'fpr','Run1 direct256'),csvmetric('Image AP',geometry,'image_ap','Run1 direct256','decimal'),csvmetric('Median pixel AP',geometry,'median_pixel_ap','Run1 direct256','decimal')],
        [('artifacts/pcb1_a2/qualitative/contact_sheet_01.png','Early PCB1 anomaly responses, including weak localization')],[geometry,'README.md']))
    stages.append(stage('stage-2','Preserve the board',p1,'What was lost when the whole image was squeezed into a square?',
        'Introduce the blue-board crop and aspect-preserving letterbox; compare 256 and 512 inputs.',
        'Geometry preservation improved detection. The 512 recipe improved localization but increased false alarms and compute.',
        'Is the reference memory now limiting the detector?', 'Frozen backbone, local scoring and 4,096-reference budget.',
        'Crop and resolution are development comparisons. Larger inputs do not guarantee a better operating tradeoff.',
        [csvmetric(label,geometry,key,recipe,fmt) for recipe,prefix in [('C1 crop256','256'),('C2 crop512','512')] for label,key,fmt in [(prefix+' recall','recall','percent'),(prefix+' normal FPR','fpr','percent'),(prefix+' median pixel AP','median_pixel_ap','decimal')]],
        [('artifacts/pcb1_geometry_comparison/comparison.png','Matched PCB1 direct-resize and cropped-recipe metric comparison')],[geometry]))
    stages.append(stage('stage-3','Make the memory representative',p1,'Would better coverage of normal features help at the same memory budget?',
        'Replace uniform selection with projected approximate-greedy representative selection at 4,096 references.',
        'Reference selection was a substantial development bottleneck. D1 was practical; D2 offered stronger sensitivity at higher cost.',
        'Does the frozen procedure transfer to a fresh PCB category?', 'Crop, resolution-specific features, memory count and one-class framework.',
        'D1 and D2 have separate banks and calibration. This is PCB1 development, not fresh generalization evidence.',
        [csvmetric(label,memory,key,recipe,fmt) for recipe,prefix in [('D1 coreset256','D1'),('D2 coreset512','D2')] for label,key,fmt in [(prefix+' recall','recall','percent'),(prefix+' normal FPR','fpr','percent'),(prefix+' median pixel AP','median_pixel_ap','decimal')]],
        [('artifacts/pcb1_memory_selection_comparison/journey.png','PCB1 uniform and representative-memory comparison')],[memory,'docs/journey/stage_03_memory_selection.md']))
    st4metrics=[]
    for path,prefix in [(d1,'D1'),(d2,'D2')]:
        # Original metrics use image and localization_common256; median comes from saved transfer table.
        st4metrics.extend([metric(prefix+' recall',path,['image','recall'],'percent'),metric(prefix+' normal FPR',path,['image','normal_false_alarm_rate'],'percent'),metric(prefix+' pooled pixel AP',path,['localization_common256','pixel_average_precision'])])
    stages.append(stage('stage-4','Cross the dataset boundary',p2,'Does the frozen procedure hold up on another PCB category?',
        'Introduce previously untouched PCB2. Fit its normal bank and calibrate on its normal split using the frozen procedure.',
        'Image-level detection transferred well. Localization became broader and less precise.',
        'Why are maps broad, and why are missing or small defects difficult?', 'Feature/scoring/selection/geometry procedures; normal-only adaptation and frozen evaluation protocol.',
        'Fresh-category confirmation is category-adapted, not zero-shot. PCB1 and PCB2 percentages are not one unchanged test-set curve.',
        st4metrics,[('artifacts/stage4/comparison/figures/journey.png','Fresh PCB2 D1 and D2 evidence')],[d1,d2,'docs/journey/stage_04_pcb2_confirmation.md']))
    # Stage5A quantitative claims calculated from the original saved per-image table.
    tablepath='artifacts/stage5a/combined/per_image_diagnostics.csv';t=pd.read_csv(ROOT/tablepath)
    pose=[]
    for recipe in ['d1','d2']:
        field=recipe+'_common_fp_pixels';value=float(t.loc[t.pose_label=='reversed_180',field].sum()/t[field].sum())
        pose.append({'label':recipe.upper()+' FP burden from 5 reversed cases','value':value,'format':'percent','source':{'path':tablepath,'sha256':digest(ROOT/tablepath),'computation':f'sum({field} where pose_label=reversed_180)/sum({field})'}})
    stages.append(stage('stage-5a','Diagnose before changing',p3,'Which failure pattern can we act on without changing several variables?',
        'Analyze saved pose, reference matching and small-defect evidence. No detector change.',
        'Reversed pose concentrated broad false-positive maps. Canonical missing failures remained unresolved; distant reference locations were not their distinctive cause.',
        'Can exact orientation normalization remove the broad response?', 'Historical D1/D2 detectors, outputs, masks, thresholds and evaluation population.',
        'Only five reversed anomalies and no reversed normal controls were available. Association is not causal proof.',pose,
        [('artifacts/stage5a/pose/pose_fp_pixels.png','False-positive burden by image-only pose label')],[tablepath,'docs/journey/stage_05a_failure_diagnosis.md']))
    for id,path,title,size,learn,nextq,figure in [
      ('stage-5b',b,'Clean up pose, expose a trade-off',256,'Broad pose response collapsed, but one small missing-component detection was lost. Cleanup did not guarantee preserved sensitivity.','Can the 512 recipe retain cleanup without losing that case?','artifacts/stage5b/figures/reversed_before_after.png'),
      ('stage-5c',c,'Keep the signal after cleanup',512,'The 512 orientation recipe preserved all five reversed detections and recovered the marginal lost case, while reducing broad response.','Why do canonical missing and small defects still miss?','artifacts/stage5c/figures/reversed_d2_before_after.png')]:
        metrics=[metric('Reversed FP pixels before',path,['reversed','historical_total_fp_pixels'],'integer'),metric('Reversed FP pixels after',path,['reversed','normalized_total_fp_pixels'],'integer'),metric('Reversed detections after',path,['reversed','detected'],'integer'),metric('Overall recall',path,['image','recall'],'percent'),metric('Normal FPR',path,['image','normal_false_alarm_rate'],'percent')]
        stages.append(stage(id,title,p3,'Can an image-only pose rule normalize confidently reversed boards?',f'Apply exact 180° crop reversal before the unchanged {size} detector; canonical and uncertain inputs remain no-ops.',learn,nextq,
          'Historical recipe-specific bank, crop, thresholds, masks and scoring. All 195 no-op outputs remain exact.',
          'Fixed five-case exposed-development evidence. The rescued 512 case is marginal; D1/D2 does not isolate resolution causality.',metrics,[(figure,'All five reversed boards before and after pose normalization on shared scales')],[path,f'docs/journey/stage_05{ "b_orientation_normalization" if size==256 else "c_orientation_512"}.md']))
    gate='artifacts/stage6a/decision_gate.json'
    stages.append(stage('stage-6a','Know when to stop',p3,'Do the remaining failures identify one justified final model change?',
        'Examine 36 fixed anomalies: canonical missing cases, all R1/R2 cases and the marginal reversed rescue.',
        'Most misses already ranked GT first but lacked decision margin. The evidence did not isolate a unique backbone, resolution, aggregation or operating-policy intervention.',
        'Freeze this candidate; reserve future model research for a new version and, where practical, an untouched category.',
        'All detector code, memory, thresholds and scoring. Diagnosis only; no Stage6B experiment.',
        'A GT-overlap grid footprint is not a receptive field. Union masks and exposed data limit causal claims. Strong rank does not prove adequate representation.',
        [metric('Distinct target misses',gate,['distinct_target_misses'],'integer'),metric('Misses with GT patch ranked #1',gate,['gt_peak_rank1_misses'],'integer'),metric('Smallest score / threshold',gate,['miss_image_ratio_range',0]),metric('Largest score / threshold',gate,['miss_image_ratio_range',1])],
        [('artifacts/stage6a/figures/patch_rank_distribution.png','GT patch ranks for detected and missed target groups')],[gate,'artifacts/stage6a/case_diagnosis.csv','docs/journey/stage_06_final_model_selection.md']))
    stages.append(stage('model-v1','Freeze the evidence-backed recipe',p3,'Can we turn the selected detector into a reproducible, honest demo?',
        'Formalize Stage5C D2+orientation as PCB-AD-v1.0. Add a verified inference wrapper without changing the model.',
        'Stopping is an engineering decision. Productization preserves the frozen model and makes its evidence and limitations inspectable.',
        'Future experiments belong to v1.1/v2.0; the v1.0 UI must not silently change the detector.',
        'Exact code identities, ordered bank, cached pretrained weights, pose handling, score and thresholds.',
        'Research and portfolio use. No certification or factory validation; no anomaly flagged does not establish a defect-free board.',
        [metric('PCB2 recall',c,['image','recall'],'percent'),metric('Normal FPR',c,['image','normal_false_alarm_rate'],'percent'),metric('AUROC',c,['image','auroc']),metric('Pooled pixel AP',c,['localization_common256','pixel_average_precision'])],
        [('artifacts/stage6a/figures/marginal_rescue_comparison.png','Historical and normalized maps of the marginal reversed rescue')],['artifacts/model_v1/final_model_receipt.json',c]))
    rationales={'stage-1': 'Start with a traceable local normal-reference baseline: without a fixed starting score and map, later improvements cannot be attributed to a specific change.', 'stage-2': 'The weak baseline map made geometry and lost local detail a plausible cause. Preserve board shape and test higher resolution before adding a new backbone or detector.', 'stage-3': 'At a fixed bank size, reference coverage can matter as much as count. Compare memory selection while preserving features, geometry and normal-only calibration.', 'stage-4': 'PCB1 had already guided development. A fresh PCB2 boundary was needed to distinguish a transferable recipe from improvements specific to the first category.', 'stage-5a': 'A changed category exposed an orientation failure. Diagnose pose groups and saved maps first, so a response to the failure has a specific mechanism rather than another blind tuning step.', 'stage-5b': 'The supported mechanism was a 180-degree ambiguity. Use a decisive image-only cue and exact reversal; leave uncertain images unchanged instead of estimating unsupported arbitrary angles.', 'stage-5c': 'Orientation cleanup at 256 exposed a detection trade-off. Retain the higher-detail 512 recipe and D2 memory, then assess whether pose cleanup preserves useful signal.', 'stage-6a': 'Once PCB2 was exposed, more tuning could chase the remaining examples. Examine the misses without changing the detector and choose a next intervention only if one mechanism is clearly supported.', 'model-v1': 'Freeze the exact chosen recipe so the interface can demonstrate evidence without silently changing the scientific result. New research needs a new version and explicit evaluation boundary.'}
    for item in stages:item['rationale']=rationales[item['id']]
    write_new(ROOT/'content/journey.json',{'schema_version':1,'generated_at_utc':now(),'scientific_commit':COMMIT,'stages':stages})
    smoke=read('tests/model_v1_smoke_manifest.json');assets=ROOT/'web/assets';assets.mkdir(exist_ok=False);examples=[]
    names={'canonical_normal':('Canonical normal','A held-out normal; no annotation.','normal'),
           'canonical_anomaly':('Visible anomaly','Detected canonical example; union annotation available.','anomaly'),
           'reversed_anomaly':('Reversed · marginal rescue','Exact 180° handling; score only just exceeds the image threshold.','reversed'),
           'uncertain_pose':('Uncertain orientation','An inconclusive image-only cue is left unchanged.','uncertain'),
           'known_small_missing_miss':('Known limitation · missing','A small missing-label anomaly that v1.0 does not flag.','limitation'),
           'missing_detected':('Missing-label detection','A detected missing-label benchmark, retaining union-mask semantics.','missing')}
    for case in smoke['cases']:
        with Image.open(ROOT/case['image_path']) as im:original=ImageOps.exif_transpose(im).convert('RGB');original.thumbnail((1100,1100));original.save(assets/(case['id']+'.jpg'),quality=88)
        source=np.load(ROOT/case['maps']['source_maps']);scores=np.asarray(Image.fromarray(source).resize(original.size,Image.Resampling.BILINEAR));pt=read('artifacts/model_v1/final_config.json')['thresholds']['pixel_threshold'];ratio=np.clip(scores/pt/2,0,1)
        colors=np.array([[13,10,25],[55,38,97],[144,50,112],[236,108,61],[255,231,147]],float);steps=ratio*4;low=np.floor(steps).astype(int);high=np.minimum(low+1,4);rgb=(colors[low]*(1-(steps-low)[...,None])+colors[high]*(steps-low)[...,None]).astype(np.uint8);Image.fromarray(rgb).save(assets/(case['id']+'_heatmap.png'))
        title,description,kind=names[case['id']];examples.append({'id':case['id'],'title':title,'description':description,'kind':kind,'thumbnail':'/assets/'+case['id']+'.jpg','saved_heatmap':'/assets/'+case['id']+'_heatmap.png','saved_score':case['score'],'saved_pose':case['pose_label'],'saved_detected':case['detected'],'score_source':'tests/model_v1_smoke_manifest.json','annotated':bool(case['mask_path']),'source':'VisA PCB2 benchmark; originally saved Stage5C evaluation'})
    write_new(ROOT/'content/examples.json',{'examples':examples,'attribution':'VisA dataset (Amazon Science), PCB2; original image sources are retained in the smoke manifest.','dataset_url':'https://github.com/amazon-science/spot-diff'})
    print('Built',len(stages),'journey stages and',len(examples),'real benchmark examples')

if __name__=='__main__':main()

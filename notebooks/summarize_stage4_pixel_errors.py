from pathlib import Path
import csv,json
r=Path(__file__).resolve().parents[1]; out=r/'artifacts/stage4/comparison'; summaries={}; rows=[]
for name in ['pcb2_d1_primary','pcb2_d2_secondary']:
 p=list(csv.DictReader((r/f'artifacts/stage4/{name}/predictions.csv').open())); local=[]
 for x in p:
  gt=round(float(x['mask_area_fraction'])*65536); i=int(x['intersection']); u=int(x['union']); fp=u-gt
  local.append(dict(recipe=name,image_id=x['image_id'],label=x['label'],gt_pixels=gt,predicted_pixels=i+u-gt,false_positive_pixels=fp,false_negative_pixels=gt-i,intersection=i,union=u))
 local.sort(key=lambda x:(-x['false_positive_pixels'],x['image_id'])); total=sum(x['false_positive_pixels'] for x in local)
 summaries[name]={'total_false_positive_pixels':total,'normal_false_positive_pixels':sum(x['false_positive_pixels'] for x in local if x['label']=='normal'),'anomaly_false_positive_pixels':sum(x['false_positive_pixels'] for x in local if x['label']!='normal'),'top_10_share':sum(x['false_positive_pixels'] for x in local[:10])/total,'top_10_image_ids':[x['image_id'] for x in local[:10]]}
 m=json.loads((r/f'artifacts/stage4/{name}/metrics.json').read_text())['localization_common256']
 assert sum(x['gt_pixels'] for x in local)==m['positive_pixels']
 assert sum(x['intersection'] for x in local)==m['intersection_pixels']
 assert sum(x['union'] for x in local)==m['union_pixels']
 rows+=local
with (out/'pixel_error_contributions.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
(out/'pixel_error_contributions.json').write_text(json.dumps({'new_model_inference':False,'interpretation':'Saved common256 union/intersection counts at frozen thresholds; descriptive postconfirmation analysis.', 'results':summaries},indent=2)+'\n')
print(json.dumps(summaries,indent=2))

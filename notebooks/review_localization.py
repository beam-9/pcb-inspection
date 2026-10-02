"""Post-final per-anomaly descriptive localization; never fits or chooses settings."""
from pathlib import Path
import json
import pandas as pd
import numpy as np
from pcb_inspection.verify_results import ranked_average_precision
from pcb_inspection.preprocessing import preprocess_mask

root=Path(__file__).resolve().parents[1]
prepared=json.loads((root/'artifacts/prepared.json').read_text());run=root/prepared['path']
assert json.loads((run/'verification.json').read_text())['passed']
frame=pd.read_csv(run/'split_manifest.csv',keep_default_na=False).set_index('image_id')
pred=pd.read_parquet(run/'predictions.parquet')
threshold=json.loads((run/'calibration.json').read_text())['primary']['pixel_threshold']
rows=[]
for record in pred[pred.label==1].itertuples():
    row=frame.loc[record.image_id];mask=preprocess_mask(root/'data/raw'/row.mask_path)
    amap=np.load(run/'anomaly_maps'/f'{record.image_id}.npy')
    peak=np.unravel_index(np.argmax(amap),amap.shape);flagged=amap>threshold
    rows.append({'image_id':record.image_id,'pixel_ap':ranked_average_precision(mask,amap),
        'map_peak_in_mask':bool(mask[peak]),'source_mask_pixel_count':int(mask.sum()),
        'intersection_pixels':int(np.count_nonzero(mask&flagged)),
        'union_pixels':int(np.count_nonzero(mask|flagged))})
table=pd.DataFrame(rows)
summary={'scope':'Post-final descriptive check on all100 test anomalies, no tuning; excludes normals here, primary pooled pixel AP includes normals.',
    'anomalies':len(table),'median_per_anomaly_pixel_ap':float(table.pixel_ap.median()),
    'map_peak_in_mask_count':int(table.map_peak_in_mask.sum()),
    'positive_overlap_count':int((table.intersection_pixels>0).sum())}
output=root/'artifacts/review';output.mkdir(exist_ok=True)
for path,payload in [(output/'anomaly_localization.csv',table.to_csv(index=False)),
                     (output/'localization_summary.json',json.dumps(summary,indent=2)+'\n')]:
    if path.exists():
        if path.read_text()!=payload: raise ValueError('Existing review result differs')
    else:
        path.write_text(payload)
print(summary)

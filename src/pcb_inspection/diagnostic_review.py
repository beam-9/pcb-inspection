"""Independent A2 arithmetic checks and labeled exploratory associations."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest, ks_2samp, spearmanr
from sklearn.metrics import roc_curve
from .guard import digest, now, verify_frozen, write_new


def review(root, output='artifacts/pcb1_a2'):
    root=Path(root);folder=root/output
    verify_frozen(root,json.loads((root/'docs/protocol.json').read_text()))
    metadata=json.loads((folder/'diagnostics_metadata.json').read_text())
    for relative,expected in metadata['outputs'].items():
        if digest(folder/relative)!=expected:raise ValueError('Changed A2 table: '+relative)
    run=root/'artifacts/runs'/metadata['run_id']
    pred=pd.read_parquet(run/'predictions.parquet');cal=pd.read_parquet(run/'calibration_predictions.parquet')
    table=pd.read_csv(folder/'per_anomaly_diagnostics.csv');normal=pd.read_csv(folder/'normal_score_diagnostics.csv')
    if set(table.image_id)!=set(pred.loc[pred.label==1,'image_id']):raise ValueError('Anomaly membership differs')
    source=pred.set_index('image_id').loc[table.image_id]
    np.testing.assert_allclose(table.image_anomaly_score,source.primary_score,rtol=0,atol=1e-14)
    threshold=float(json.loads((run/'calibration.json').read_text())['primary']['image_threshold'])
    np.testing.assert_array_equal(table.detected_at_frozen_threshold,source.primary_score.to_numpy()>threshold)
    prior=pd.read_csv(root/'artifacts/review/anomaly_localization.csv').set_index('image_id').loc[table.image_id]
    np.testing.assert_allclose(table.per_image_pixel_ap,prior.pixel_ap,rtol=1e-12,atol=1e-12)
    np.testing.assert_array_equal(table.peak_inside_mask,prior.map_peak_in_mask)
    np.testing.assert_array_equal(table.intersection_pixels,prior.intersection_pixels)
    np.testing.assert_array_equal(table.union_pixels,prior.union_pixels)
    if normal.image_id.duplicated().any():raise ValueError('Duplicate normal membership')
    for split,expected in [('calibration',cal),('test',pred[pred.label==0])]:
        rows=normal[normal.split==split].set_index('image_id').sort_index()
        expected=expected.set_index('image_id').sort_index()
        if set(rows.index)!=set(expected.index):raise ValueError('Normal membership differs')
        np.testing.assert_allclose(rows.image_anomaly_score,expected.primary_score,rtol=0,atol=1e-14)
    roc=pd.read_csv(folder/'full_roc_data.csv')
    fpr,tpr,_=roc_curve(pred.label,pred.primary_score,drop_intermediate=False)
    np.testing.assert_allclose(roc.realized_fpr,fpr,rtol=0,atol=1e-14)
    np.testing.assert_allclose(roc.recall,tpr,rtol=0,atol=1e-14)
    operating=pd.read_csv(folder/'recall_vs_fpr.csv')
    for point in operating.itertuples():
        flagged=pred.primary_score.to_numpy()>point.threshold;labels=pred.label.to_numpy().astype(bool)
        assert int(np.sum(flagged&labels))==point.true_positives
        assert int(np.sum(flagged&~labels))==point.false_positives
        assert point.realized_fpr<=point.target_fpr+1e-14
        assert np.isclose(point.recall,max(tpr[fpr<=point.target_fpr+1e-14]))
    multi=pd.read_csv(folder/'per_anomaly_defect_types.csv')
    if multi.duplicated(['image_id','defect_type']).any():raise ValueError('Duplicated label membership')
    if len(multi)!=sum(table.defect_types.map(lambda packed:len(json.loads(packed)))):raise ValueError('Missing multilabel memberships')
    cal_scores=normal[normal.split=='calibration'].image_anomaly_score
    test_scores=normal[normal.split=='test'].image_anomaly_score
    ci=binomtest(int(normal.loc[normal.split=='test','above_frozen_threshold'].sum()),len(test_scores)).proportion_ci(method='wilson')
    ks=ks_2samp(cal_scores,test_scores);rho=spearmanr(table.mask_area_fraction,table.image_anomaly_score)
    association={'scope':'Exploratory PCB1 development association/uncertainty; no operating-threshold selection',
        'test_normal_fpr_wilson95':{'low':float(ci.low),'high':float(ci.high),'assumptions':'Independent Bernoulli test-normal images at the fixed threshold. Physical board independence is unverified; descriptive illustration, not factory guarantee.'},
        'calibration_test_normal_ks':{'statistic':float(ks.statistic),'pvalue':float(ks.pvalue),'assumptions':'Two-sample independent-image continuous-score null; related-object independence unavailable; exploratory and no shift proven.'},
        'mask_area_score_spearman':{'rho':float(rho.statistic),'pvalue':float(rho.pvalue),'interpretation':'Rank association, not causal resize proof; size and defect type are confounded.'},
        'detection_localization_groups':table.groupby('detected_at_frozen_threshold').agg(image_count=('image_id','size'),median_pixel_ap=('per_image_pixel_ap','median'),peak_inside_mask_rate=('peak_inside_mask','mean'),any_overlap_rate=('any_overlap_with_mask','mean')).reset_index().to_dict('records')}
    path=folder/'association_uncertainty.json'
    if path.exists():
        if json.loads(path.read_text())!=association:raise ValueError('Existing associations differ')
    else:write_new(path,association)
    result={'checked_utc':now(),'passed':True,'original_frozen_identity_preserved':True,
        'anomaly_rows':len(table),'normal_rows':len(normal),'type_memberships':len(multi),
        'checks':['All anomaly membership/scores/frozen flags','All per-image AP/overlap against independently computed Run1 review','Calibration/test-normal IDs and saved scores','Complete ROC curve against independent sklearn >= implementation','All diagnostic operating-point confusion and optimal recall within budget','Multilabel membership uniqueness/counts'],
        'no_model_inference':True,'pcb2_access':False}
    write_new(folder/'verification_a2.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default='.');p.add_argument('--output',default='artifacts/pcb1_a2')
    args=p.parse_args();review(args.root,args.output)

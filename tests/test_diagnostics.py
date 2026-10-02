import json
import numpy as np
import pandas as pd
import pytest
from pcb_inspection.diagnostics import (localization_row, parse_defect_types, assign_size_quartiles,
                                       strict_roc_table, recall_at_fpr, type_tables, verify_inputs)
from pcb_inspection.provenance import sha256_file


def test_mask_geometry_threshold_and_peak_ties():
    mask=np.array([[1,0],[0,0]],bool)
    scores=np.array([[2.,2.],[0.,0.]])
    row=localization_row(mask,scores,2.)
    assert row['peak_inside_mask'] and row['peak_tie_count']==2
    assert row['intersection_pixels']==0 and row['union_pixels']==1
    assert not row['any_overlap_with_mask'] and row['per_image_iou']==0
    assert row['defect_centroid_x']==row['defect_centroid_y']==0
    assert row['per_image_pixel_ap']==.5
    assert row['mask_area_fraction']==.25
    with pytest.raises(ValueError,match='geometry'):
        localization_row(mask,np.ones((3,3)),1.)
    with pytest.raises(ValueError,match='Positive mask'):
        localization_row(np.zeros((2,2)),scores,1.)


def test_strict_roc_has_no_partial_tie_selection_and_fpr_never_exceeds_budget():
    labels=[1,0,1,0]; scores=[.9,.9,.8,.1]
    roc=strict_roc_table(labels,scores)
    assert roc.iloc[0].true_positives==roc.iloc[0].false_positives==0
    assert roc.iloc[-1].true_positives==roc.iloc[-1].false_positives==2
    selected=recall_at_fpr(labels,scores,[0.,.5,1.])
    assert selected.recall.tolist()==[0.,1.,1.]
    assert selected.realized_fpr.tolist()==[0.,.5,.5]
    for row in selected.itertuples():
        flags=np.asarray(scores)>row.threshold
        assert int(np.sum(flags & np.asarray(labels,dtype=bool)))==row.true_positives
        assert int(np.sum(flags & ~np.asarray(labels,dtype=bool)))==row.false_positives
        assert row.realized_fpr<=row.target_fpr
    with pytest.raises(ValueError,match='both labels'):
        strict_roc_table([1,1],[.1,.2])


def test_size_quartiles_preserve_equal_area_ties_and_shuffle_invariance():
    frame=pd.DataFrame({'image_id':list('abcdefgh'),'mask_area_fraction':[.1,.1,.1,.1,.2,.2,.3,.4]})
    result,edges=assign_size_quartiles(frame)
    assert result.groupby('mask_area_fraction').size_quartile.nunique().max()==1
    shuffled,_=assign_size_quartiles(frame.sample(frac=1,random_state=42))
    assert result.set_index('image_id').size_quartile.to_dict()==shuffled.set_index('image_id').size_quartile.to_dict()
    constant,_=assign_size_quartiles(pd.DataFrame({'mask_area_fraction':[.1]*4}))
    assert set(constant.size_quartile)=={'Q1'}


def test_multi_label_types_preserved_and_counted_once_per_type():
    assert parse_defect_types('melt,scratch,missing')==['melt','scratch','missing']
    with pytest.raises(ValueError):
        parse_defect_types('melt,melt')
    frame=pd.DataFrame({'image_id':['a','b'],'defect_types':['["melt", "scratch"]','["melt"]'],
                        'detected_at_frozen_threshold':[True,False], 'mask_area_fraction':[.1,.2],
                        'image_anomaly_score':[3.,1.], 'score_minus_threshold':[1.,-1.],
                        'per_image_pixel_ap':[.8,.2], 'peak_inside_mask':[True,False], 'any_overlap_with_mask':[True,True]})
    long,recall,aps=type_tables(frame)
    assert len(long)==3
    recall=recall.set_index('defect_type')
    assert recall.loc['melt','sample_count']==2 and recall.loc['melt','recall']==.5
    assert recall.loc['scratch','sample_count']==1 and recall.loc['scratch','recall']==1.
    assert aps.set_index('defect_type').loc['melt','median']==.5


def test_changed_calibration_input_is_rejected_before_reading_masks(tmp_path):
    run=tmp_path/'artifacts/runs/example';run.mkdir(parents=True)
    (tmp_path/'docs').mkdir()
    protocol=tmp_path/'docs/protocol.json';protocol.write_text('{"frozen_files":{}}')
    calibration=run/'calibration.json';calibration.write_text('{"changed":true}')
    (run/'provenance.json').write_text(json.dumps({'run_id':'example','protocol_sha256':sha256_file(protocol),
        'prerequisites':{'artifacts/runs/example/calibration.json':'0'*64}}))
    (run/'final_complete.json').write_text(json.dumps({'run_id':'example','files':{},'maps':{}}))
    (run/'verification.json').write_text(json.dumps({'run_id':'example','passed':True}))
    with pytest.raises(ValueError,match='Input hash mismatch.*calibration'):
        verify_inputs(tmp_path,'example')

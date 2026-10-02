"""Synthetic-only independent arithmetic checks; no benchmark access."""
import numpy as np
import pytest
import pandas as pd
from PIL import Image

from pcb_inspection.verify_results import ranked_average_precision, pairwise_auroc, direct_confusion, verify_run, independent_patch_trace
from pcb_inspection.guard import digest, write_new


def test_grouped_ties_have_one_threshold():
    assert ranked_average_precision([1,0,1,0],[.8,.8,.4,.1]) == pytest.approx((.5+2/3)/2)
    assert ranked_average_precision([0,1,1,0],[.8,.8,.4,.1]) == pytest.approx((.5+2/3)/2)
    assert ranked_average_precision([1,0,1,0],[1,1,1,1]) == .5


def test_pairwise_auroc_ties_and_order():
    assert pairwise_auroc([1,0,1,0],[.8,.8,.4,.1]) == .625
    assert pairwise_auroc([1,0],[1,0]) == 1
    assert pairwise_auroc([1,0],[0,1]) == 0
    assert pairwise_auroc([1,1],[0,1]) is None


def test_confusion_strict_threshold_and_undefined():
    result=direct_confusion([1,0,1,0],[.8,.8,.4,.1],.4)
    assert [result[key] for key in ['tp','fp','fn','tn']] == [1,1,1,1]
    assert direct_confusion([0,0],[0,0],0)['precision'] is None
    assert ranked_average_precision([0,0],[0,1]) is None


@pytest.mark.parametrize('labels,scores', [([],[]),([0,2],[1,0]),([0,1],[1]),([0,1],[np.nan,0])])
def test_invalid_arithmetic_inputs(labels,scores):
    with pytest.raises(ValueError): ranked_average_precision(labels,scores)


def test_no_final_read_without_completion(tmp_path):
    # A missing final completion marker fails before parquet or raw masks exist.
    with pytest.raises(FileNotFoundError): verify_run(tmp_path,tmp_path/'raw')


def test_saved_synthetic_run_and_tamper_detection(tmp_path):
    run=tmp_path/'run'; raw=tmp_path/'raw'
    run.mkdir(); raw.mkdir(); (run/'anomaly_maps').mkdir()
    rows=[]
    for name,label in [('normal',0),('anomaly',1)]:
        Image.new('RGB',(16,16)).save(raw/f'{name}.png')
        if label: Image.new('L',(16,16),255).save(raw/'mask.png')
        rows.append({'image_id':name,'split':'test','label':name,'image_path':f'{name}.png',
            'sha256':digest(raw/f'{name}.png'),'mask_path':'mask.png' if label else '',
            'mask_sha256':digest(raw/'mask.png') if label else '', 'width':16,'height':16})
        np.save(run/'anomaly_maps'/f'{name}.npy',np.full((256,256),label,dtype=np.float32))
    pd.DataFrame(rows+[{'image_id':'fit','split':'fit','label':'normal','width':16,'height':16}]).to_csv(run/'split_manifest.csv',index=False)
    pd.DataFrame({'image_id':['normal','anomaly'],'run_id':['fixture','fixture'],
        'label':[0,1],'baseline_score':[0.,1.],'primary_score':[0.,1.],
        'baseline_reference_id':['fit','fit'],'primary_reference_id':['fit','fit'],
        'query_patch_row':[0,1],'query_patch_column':[0,1],
        'reference_patch_row':[0,1],'reference_patch_column':[0,1]}).to_parquet(run/'predictions.parquet',index=False)
    write_new(run/'calibration.json',{'baseline':{'image_threshold':.5},'primary':{'image_threshold':.5,'pixel_threshold':.5}})
    image={'tp':1,'fp':0,'fn':0,'tn':1,'n_images':2,'anomaly_count':1,'normal_count':1,
        'anomaly_prevalence':.5,'threshold':.5,'precision':1.,'recall':1.,'normal_false_alarm_rate':0.,
        'average_precision':1.,'auroc':1.}
    pixel={'pixel_average_precision':1.,'n_images':2,'n_pixels':131072,'positive_pixels':65536,
        'includes_normal_images':True,'pixel_threshold':.5,'intersection_pixels':65536,'union_pixels':65536,'pixel_iou':1.}
    write_new(run/'metrics.json',{'baseline':image,'primary':image,'localization':pixel})
    write_new(run/'runtime.json',{})
    write_new(run/'provenance.json',{'run_id':'fixture','manifest_sha256':digest(run/'split_manifest.csv'),
        'prerequisites':{'run/calibration.json':digest(run/'calibration.json')}})
    write_new(run/'final_complete.json',{'run_id':'fixture',
        'files':{name:digest(run/name) for name in ['predictions.parquet','metrics.json','runtime.json']},
        'maps':{p.name:digest(p) for p in (run/'anomaly_maps').glob('*.npy')}})
    assert verify_run(run,raw,expected_test_count=2,trace_sample_count=0)['passed']
    with pytest.raises(FileExistsError): verify_run(run,raw,expected_test_count=2,trace_sample_count=0)
    np.save(run/'anomaly_maps'/'normal.npy',np.ones((256,256),dtype=np.float32))
    with pytest.raises(ValueError,match='map identity'): verify_run(run,raw,expected_test_count=2,publish=False)


def test_independent_patch_trace_exact_winner_and_reference():
    # Four scalar patches: farthest nearest distance is at row 1/column 0.
    trace=independent_patch_trace(np.array([[[0.,2.],[7.,4.]]]),np.array([[0.],[4.]]))
    assert trace=={'score':3.,'row':1,'column':0,'reference_index':1}
    tie=independent_patch_trace(np.array([[[2.]]]),np.array([[0.],[4.]]))
    assert tie['reference_index']==0

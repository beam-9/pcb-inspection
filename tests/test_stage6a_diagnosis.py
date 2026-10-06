import numpy as np
import pytest
from pcb_inspection.stage6a_diagnosis import projected_gt, patch_diagnostics, categories


def test_oriented_gt_rotates_crop_before_odd_padding():
    t={'source_height':16,'source_width':24,'input_size':32,'crop_box':[4,0,20,16],
       'content_width':24,'content_height':24,'pad_x':3,'pad_y':5}
    mask=np.zeros((16,24),bool); mask[0:3,4:7]=True
    canonical=projected_gt(mask,t,'canonical'); reverse=projected_gt(mask,t,'reversed_180')
    assert canonical[0,0] and reverse[3,3]
    assert not reverse[0,0]
    assert np.array_equal(canonical,projected_gt(mask,t,'uncertain'))


def test_stable_patch_rank_and_aggregation():
    scores=np.array([[3.,3.,1.],[2.,.5,.2]])
    gt=np.array([[False,True,False],[False,False,False]])
    result=patch_diagnostics(scores,gt,4.)
    assert result['first_gt_patch_rank']==2
    assert result['top_score_patch_column']==0
    assert not result['top_score_patch_inside_GT']
    assert result['top_3_mean']==pytest.approx(8/3)
    assert result['gt_max_ratio']==.75
    assert result['top_5_gt_fraction']==.2
    with pytest.raises(ValueError):patch_diagnostics(scores,np.zeros_like(gt),4)


def test_outside_competition_cannot_be_assigned_as_miss_cause():
    d1={'gt_max_ratio':.7,'common_pixel_ap':.2}
    d2={'gt_max_ratio':.7,'common_pixel_ap':.2,'detected':False,'top_score_patch_inside_GT':False,
        'GT_to_image_max_ratio':.85,'score_divided_by_threshold':.9}
    assert categories(d1,d2,True)=='F1'
    d2.update(detected=True)
    assert categories(d1,d2,True)=='F3'

import numpy as np
from pcb_inspection.stage5a_maps import crop_coordinates, source_gt_at, spread, grid_rows


def test_native_pixel_centers_exclude_padding_and_cover_all_grid_cells():
    t=dict(crop_box=[2,3,10,7],source_width=12,source_height=10,pad_x=0,pad_y=2,content_width=8,content_height=4)
    u,v,inside,cells=crop_coordinates(t,8,8,True)
    assert inside.sum()==32 and not inside[:2].any() and not inside[6:].any()
    assert set(cells[inside])==set(range(16))
    raw=np.zeros((10,12),bool);raw[3:7,2:10]=True
    assert source_gt_at(raw,t,u,v)[inside].all()


def test_common_centers_use_source_extent_and_grid_plus_outside_totals():
    t=dict(crop_box=[2,2,6,6],source_width=8,source_height=8)
    _,_,inside,cells=crop_coordinates(t,8,8,False)
    assert inside.sum()==16 and inside[2:6,2:6].all()
    scores=np.ones((8,8));mask=np.zeros((8,8),bool);mask[3,3]=True
    rows=grid_rows('id','D1','common',scores,mask,.5,inside,cells)
    assert sum(r['false_positive_pixels'] for r in rows)==15
    assert sum(r['false_positive_pixels'] for r in rows)+int((~mask&~inside).sum())==63


def test_eight_connectivity_and_bounding_box_spread():
    positive=np.eye(4,dtype=bool)
    count,area,fraction=spread(positive)
    assert (count,area,fraction)==(1,16,1.)
    assert spread(np.zeros((4,4),bool))==(0,0,0.)

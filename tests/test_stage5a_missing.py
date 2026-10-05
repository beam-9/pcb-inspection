import numpy as np
import pytest
import torch
from pcb_inspection.stage5a_missing import coordinates,query_regions,top_neighbors


def transform():
    return dict(source_width=100,source_height=80,crop_box=[10,20,90,60],input_size=256,content_width=256,content_height=128,pad_x=0,pad_y=64)


def test_coordinate_roundtrip_and_padding():
    t=transform();p=coordinates(8,0,t)
    assert p['source_x']==pytest.approx(11.25)
    assert p['source_y']==pytest.approx(21.25)
    assert p['padding_center'] is False
    assert coordinates(0,0,t)['padding_center'] is True


def test_mask_footprint_and_ring_excludes_overlap():
    t=transform();mask=np.zeros((80,100),bool);mask[30:34,40:44]=True
    overlap,ring,fraction=query_regions(mask,t)
    assert overlap.any() and ring.any() and not (overlap&ring).any()
    assert overlap.shape==(32,32)
    assert np.array_equal(overlap,fraction>0)
    assert not overlap[:8].any() and not overlap[24:].any()


def test_no_cropped_out_mask_queries():
    mask=np.zeros((80,100),bool);mask[0:5,0:5]=True
    overlap,ring,_=query_regions(mask,transform())
    assert not overlap.any() and not ring.any()


def test_topk_ties_lowest_bank_index_independent_distance():
    q=torch.tensor([[1.,1.],[2.,3.]])
    b=torch.tensor([[1.,1.],[1.,1.],[3.,3.],[2.,3.],[0.,0.]])
    d,i,ties=top_neighbors(q,b)
    assert i[0,:2].tolist()==[0,1] and ties.tolist()==[2,1]
    oracle=np.sqrt(((q.numpy()[:,None,:]-b.numpy()[None,:,:])**2).sum(2))
    assert np.array_equal(i,np.argsort(oracle,axis=1,kind='stable'))
    assert np.allclose(d,np.take_along_axis(oracle,i,axis=1))


def test_nonfinite_rejected():
    with pytest.raises(ValueError):top_neighbors(torch.tensor([[float('nan')]]),torch.zeros((5,1)))


def test_published_diagnostics_block_all_mutations(tmp_path):
    from pcb_inspection.stage5a_missing import extract,summarize,sheets,review_sheets
    published=tmp_path/'artifacts/stage5a/diagnostics.json'
    published.parent.mkdir(parents=True)
    published.write_text('{}')
    for operation in [lambda:extract(tmp_path),lambda:summarize(tmp_path,'unused.csv'),lambda:sheets(tmp_path),lambda:review_sheets(tmp_path)]:
        with pytest.raises(FileExistsError,match='immutable'):
            operation()
    assert published.read_text()=='{}'
    assert not (published.parent/'missing_component').exists()

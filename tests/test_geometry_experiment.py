import numpy as np
import torch
from pcb_inspection.geometry_experiment import DynamicExtractor,selected_indices,pixel_row
from pcb_inspection.preprocessing import FrozenPatchExtractor

def test_dynamic256_exactly_matches_original_representation():
 torch.set_num_threads(2);torch.manual_seed(1)
 old=FrozenPatchExtractor(weights=False);new=DynamicExtractor(weights=False);new.load_state_dict(old.state_dict())
 x=torch.randn(1,3,256,256)
 assert torch.equal(old(x),new(x))
 assert new(torch.randn(1,3,512,512)).shape==(1,384,64,64)

def test_global_uniform_sampling_matches_original_memory_policy():
 s=selected_indices(8,32,32,4096,42)
 expected=np.sort(np.random.default_rng(42).choice(8*32*32,size=4096,replace=False))
 assert np.array_equal(s,expected) and len(np.unique(s))==4096

def test_pixel_results_penalize_outside_crop_annotation():
 mask=np.array([[True,False],[False,False]]);scores=np.array([[0,3],[2,1]])
 r=pixel_row(mask,scores,2)
 assert r['pixel_ap']==.25 and not r['peak_inside'] and not r['overlap'] and r['iou']==0

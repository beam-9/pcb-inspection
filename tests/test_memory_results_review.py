import numpy as np
from pcb_inspection.memory_results_review import independent_inverse, independent_prefix
from pcb_inspection.coreset import select_coreset


def test_independent_map_retains_unobserved_source_pixels():
    transform={'input_size':256,'source_width':8,'source_height':6,'crop_box':[2,1,6,5],
        'pad_x':0,'pad_y':0,'content_width':256,'content_height':256}
    source,common=independent_inverse(np.ones((256,256),np.float32),transform)
    assert source.shape==(6,8) and common.shape==(256,256)
    assert np.array_equal(source[1:5,2:6],np.ones((4,4)))
    assert np.count_nonzero(source)==16


def test_numpy_selector_prefix_independent_of_production_distance_kernel():
    for seed in [0,42]:
        features=np.random.default_rng(seed).normal(size=(100,12)).astype(np.float32)
        assert np.array_equal(independent_prefix(features,count=16,seed=seed),
                              select_coreset(features,count=16,seed=seed))


def test_tie_index_uniqueness_for_independent_oracle():
    assert independent_prefix(np.zeros((12,3),np.float32),count=5).tolist()==[0,1,2,3,4]

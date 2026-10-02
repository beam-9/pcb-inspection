"""Independent synthetic checks of Stage3 selection, not detector inference.

The reference implementation computes distances directly in float64, without
using the selector's matrix-product distance implementation.
"""
import numpy as np
import pytest
import torch

from pcb_inspection.coreset import gaussian_projection, project_features, select_coreset


def independent_greedy(projected,count,seed=42,initial_count=10):
    points=np.asarray(projected,dtype=np.float64)
    initial=np.random.default_rng(seed).choice(len(points),min(initial_count,len(points)),replace=False)
    distances=np.linalg.norm(points[:,None,:]-points[initial][None,:,:],axis=2).mean(axis=1)
    selected=[]
    for _ in range(count):
        # np.argmax uses the first (smallest candidate index) tied maximum.
        distances[selected]=-np.inf
        index=int(np.argmax(distances));selected.append(index)
        distances=np.minimum(distances,np.linalg.norm(points-points[index],axis=1))
    return np.asarray(selected,dtype=np.int64)


def test_selection_matches_independent_direct_distance_reference():
    points=np.array([[-13.,2.],[-8.,-1.],[-4.,3.],[0.,0.],[1.,2.],[5.,-3.],[9.,1.],[17.,4.]],np.float32)
    expected=independent_greedy(points,5,seed=17,initial_count=3)
    actual=select_coreset(torch.from_numpy(points),count=5,seed=17,initial_count=3)
    np.testing.assert_array_equal(actual,expected)
    assert actual.dtype==np.int64
    assert len(np.unique(actual))==len(actual)==5
    assert np.all((actual>=0)&(actual<len(points)))


def test_identical_features_select_unique_lowest_indices_not_uniform_fallback():
    points=torch.ones((12,4),dtype=torch.float32)
    actual=select_coreset(points,count=12,seed=7,initial_count=10)
    np.testing.assert_array_equal(actual,np.arange(12,dtype=np.int64))


def test_seeded_repeatability_and_projected_not_full_dimensional_selection():
    points=np.random.default_rng(5).normal(size=(50,7)).astype(np.float32)
    projection=gaussian_projection(input_dim=7,output_dim=3,seed=43)
    original=points.copy()
    projected=project_features(points,projection)
    projected_original=projected.clone()
    assert projected.dtype==torch.float32 and projected.device.type=='cpu' and projected.shape==(50,3)
    np.testing.assert_allclose(projected.numpy(),points@projection.numpy(),rtol=2e-6,atol=2e-6)
    first=select_coreset(projected,count=15,seed=42,initial_count=10)
    second=select_coreset(projected,count=15,seed=42,initial_count=10)
    np.testing.assert_array_equal(first,second)
    np.testing.assert_array_equal(points,original)
    torch.testing.assert_close(projected,projected_original,rtol=0,atol=0)
    np.testing.assert_array_equal(first,independent_greedy(projected.numpy(),15,42,10))
    assert points[first].shape==(15,7), 'Original features must remain available for inference'


def test_projection_seed_shape_and_scaling():
    first=gaussian_projection(input_dim=4,output_dim=3,seed=43)
    same=gaussian_projection(input_dim=4,output_dim=3,seed=43)
    changed=gaussian_projection(input_dim=4,output_dim=3,seed=44)
    torch.testing.assert_close(first,same,rtol=0,atol=0)
    assert not torch.equal(first,changed)
    expected=torch.randn((4,3),generator=torch.Generator().manual_seed(43),dtype=torch.float32)/np.sqrt(3)
    torch.testing.assert_close(first,expected,rtol=0,atol=0)
    for input_dim,output_dim in [(0,3),(4,0),(-1,3),(4,-1)]:
        with pytest.raises(ValueError):
            gaussian_projection(input_dim=input_dim,output_dim=output_dim,seed=43)
    with pytest.raises(ValueError):
        project_features(np.ones((3,5),np.float32),first)


def test_single_candidate_and_oversized_initial_set():
    result=select_coreset(torch.tensor([[2.,-3.]]),count=1,seed=42,initial_count=10)
    np.testing.assert_array_equal(result,[0])
    points=torch.tensor([[0.,0.],[1.,0.],[0.,1.]])
    np.testing.assert_array_equal(select_coreset(points,count=3,seed=42,initial_count=99),independent_greedy(points.numpy(),3,42,99))


@pytest.mark.parametrize('count',[0,-1,5])
def test_invalid_count_rejected_instead_of_silent_clamping(count):
    with pytest.raises(ValueError):
        select_coreset(torch.zeros((4,2)),count=count)


@pytest.mark.parametrize('points',[torch.empty((0,2)),torch.ones(4),torch.tensor([[float('nan'),0.],[1.,1.]]),torch.tensor([[float('inf'),0.],[1.,1.]])])
def test_invalid_candidate_geometry_or_values_rejected(points):
    with pytest.raises(ValueError):
        select_coreset(points,count=1)


def test_invalid_initial_count_rejected():
    with pytest.raises(ValueError):
        select_coreset(torch.ones((4,2)),count=2,initial_count=0)


def test_resource_deadline_raises_without_uniform_fallback():
    with pytest.raises(RuntimeError):
        select_coreset(torch.randn((100,8)),count=50,seed=42,deadline_seconds=0.)


def test_nonidentical_exact_farthest_tie_prefers_lowest_global_index():
    # Seed1 selects the middle initial anchor. The two outer vectors are
    # equally far from it, so candidate0 must be selected before candidate2.
    assert np.random.default_rng(1).choice(3,1,replace=False).tolist()==[1]
    points=torch.tensor([[-1.,0.],[0.,0.],[1.,0.]])
    actual=select_coreset(points,count=3,seed=1,initial_count=1)
    np.testing.assert_array_equal(actual,[0,2,1])


def test_fixed_coverage_query_sample_independent_seed_and_original_population():
    from pcb_inspection.memory_diagnostics import fixed_query_indices
    expected=np.sort(np.random.default_rng(44).choice(4000,2048,replace=False)).astype(np.int64)
    actual=fixed_query_indices(4000)
    np.testing.assert_array_equal(actual,expected)
    assert len(np.unique(actual))==2048 and actual[0]>=0 and actual[-1]<4000
    with pytest.raises(ValueError):
        fixed_query_indices(100,count=2048)


def test_padding_center_proxy_half_open_bounds_and_source_coordinate_mapping():
    from pcb_inspection.memory_diagnostics import reference_geometry
    geometry={'crop_box':[100,200,500,400]}
    # 400x200 crop becomes256x128, y-padding64. Feature row7 center60
    # is padding; row8 center68 is content. No receptive-field claim follows.
    pad=reference_geometry({'row':7,'column':0},geometry,256)
    content=reference_geometry({'row':8,'column':0},geometry,256)
    bottom=reference_geometry({'row':24,'column':0},geometry,256)
    assert pad['is_padding_patch_center_proxy'] and bottom['is_padding_patch_center_proxy']
    assert not content['is_padding_patch_center_proxy']
    assert content['content_width']==256 and content['content_height']==128 and content['pad_y']==64
    assert content['source_patch_x']==106.25 and content['source_patch_y']==206.25
    assert content['normalized_crop_region']=='row0_col0'
    assert pad['normalized_crop_region']=='padding_center'
    with pytest.raises(ValueError,match='outside feature grid'):
        reference_geometry({'row':32,'column':0},geometry,256)


def test_coverage_summary_preserves_self_match_fraction_and_quantiles():
    from pcb_inspection.memory_diagnostics import coverage_statistics
    summary=coverage_statistics([0.,1.,2.,3.])
    assert summary['mean']==summary['median']==1.5
    assert summary['p95']==pytest.approx(2.85) and summary['maximum']==3.
    assert summary['zero_distance_fraction']==.25 and summary['query_count']==4
    for values in [[],[-1.],[float('nan')]]:
        with pytest.raises(ValueError):
            coverage_statistics(values)

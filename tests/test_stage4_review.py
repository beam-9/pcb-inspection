import numpy as np
import pandas as pd
import pytest
from pcb_inspection.stage4_review import verify_split, quantiles, independent_inverse


def normal_fixture():
    groups = [f'{index:064x}' for index in range(10)]
    shuffled = np.array(groups, dtype=object); np.random.default_rng(42).shuffle(shuffled)
    calibration = set(shuffled[:2])
    records = [dict(image_id=str(index), label='normal', sha256=value, duplicate_group=value,
                    official_split='train', split='calibration' if value in calibration else 'fit',
                    structural_decode_status='passed') for index, value in enumerate(groups)]
    records.append(dict(image_id='heldout', label='normal', sha256='heldout', duplicate_group='heldout',
                        official_split='test', split='normal_test', structural_decode_status='deferred_until_final_freeze'))
    return pd.DataFrame(records)


def test_group_split_oracle_rejects_wrong_partition_and_decoded_holdout():
    frame = normal_fixture(); assert verify_split(frame) == {'calibration': 2, 'fit': 8, 'normal_test': 1}
    wrong = frame.copy(); wrong.loc[0, 'split'] = 'fit' if wrong.loc[0, 'split'] == 'calibration' else 'calibration'
    with pytest.raises(ValueError, match='split differs'): verify_split(wrong)
    wrong = frame.copy(); wrong.loc[10, 'structural_decode_status'] = 'passed'
    with pytest.raises(ValueError, match='decode'): verify_split(wrong)


def test_higher_quantiles_include_complete_normal_maps_and_strict_policy():
    maps = np.zeros((2, 256, 256), np.float32); maps[1] = 7
    calibration = dict(comparison='>', quantile_method='higher', normal_calibration_count=2,
                       image_threshold=9., pixel_threshold=7.)
    assert quantiles(np.array([1., 9.]), maps, calibration) == (9., 7.)
    calibration['comparison'] = '>='
    with pytest.raises(ValueError, match='semantics'): quantiles(np.array([1., 9.]), maps, calibration)


def test_inverse_keeps_cropped_out_extent_zero():
    transform = dict(input_size=8, crop_box=[2, 3, 8, 7], pad_x=0, pad_y=1,
                     content_width=8, content_height=6, source_width=10, source_height=10)
    source, common = independent_inverse(np.ones((8, 8), np.float32), transform)
    assert source.shape == (10, 10) and common.shape == (256, 256)
    assert source.sum() == 24 and not source[:3].any() and not source[:, :2].any()


def test_exact_duplicate_groups_cannot_cross_partitions():
    frame = normal_fixture()
    duplicate = frame.iloc[[0]].copy(); duplicate['image_id'] = 'duplicate'; duplicate['split'] = 'calibration' if frame.iloc[0].split == 'fit' else 'fit'
    with pytest.raises(ValueError, match='Cross-partition'):
        verify_split(pd.concat([frame, duplicate], ignore_index=True))


def test_hash_receipts_cannot_escape_artifact_root(tmp_path):
    from pcb_inspection.stage4_review import hash_files
    with pytest.raises(ValueError, match='escapes'):
        hash_files(tmp_path, {'../outside.bin': 'irrelevant'})


def test_independent_projection_float32_identity():
    import hashlib
    import torch
    from pcb_inspection.coreset import gaussian_projection
    rng = torch.Generator(device='cpu').manual_seed(43)
    independent = torch.randn(384, 64, generator=rng).numpy() / np.float32(8.)
    assert independent.dtype == np.float32
    assert hashlib.sha256(independent.tobytes()).hexdigest() == hashlib.sha256(gaussian_projection(384, 64, 43).numpy().tobytes()).hexdigest()

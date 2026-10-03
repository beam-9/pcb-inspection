"""Independent PCB2 normal-preflight and saved-confirmation checks.

Normal mode never decodes held-out normals or accesses anomaly manifests/masks.
Existing frozen arithmetic helpers are reused; production split/selector/calibration
functions are not used as independent oracles.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
import torch

from .provenance import canonical_hash
from .guard import digest, now, write_new, verify_frozen
from .memory_results_review import require, close, independent_inverse, independent_prefix, pixel_check
from .verify_results import direct_confusion, ranked_average_precision, pairwise_auroc

STAGE = 'artifacts/stage4'
RUNS = {256: 'pcb2_d1_primary', 512: 'pcb2_d2_secondary'}


def read_json(path):
    return json.loads(Path(path).read_text())


def hash_files(base, identities):
    base = Path(base).resolve()
    for name, expected in identities.items():
        path = (base / name).resolve()
        require(path.is_relative_to(base), 'Hash path escapes artifact root')
        require(digest(path) == expected, f'Identity differs: {name}')


def verify_split(frame, seed=42):
    """Recompute exact-SHA group allocation without production split code."""
    require(not frame.empty and frame.image_id.is_unique, 'Unique normal IDs required')
    require(frame.label.eq('normal').all(), 'Non-normal preflight membership')
    require(frame.official_split.isin(['train', 'test']).all(), 'Unknown official split')
    require(frame.duplicate_group.eq(frame.sha256).all(), 'Group must equal file SHA')
    require(not frame.groupby('sha256').split.nunique().gt(1).any(), 'Cross-partition duplicate')
    require(not frame.groupby('sha256').official_split.nunique().gt(1).any(), 'Cross-official duplicate')
    groups = np.array(sorted(frame.loc[frame.official_split == 'train', 'sha256'].unique()), dtype=object)
    np.random.default_rng(seed).shuffle(groups)
    calibration = set(groups[:math.ceil(.2 * len(groups))])
    expected = ['normal_test' if row.official_split == 'test' else
                ('calibration' if row.sha256 in calibration else 'fit') for row in frame.itertuples()]
    require(frame.split.tolist() == expected, 'Independent group split differs')
    require(set(expected) == {'fit', 'calibration', 'normal_test'}, 'Missing normal partition')
    require(frame.loc[frame.split == 'normal_test', 'structural_decode_status'].eq('deferred_until_final_freeze').all(), 'Heldout decode not deferred')
    return {name: int(count) for name, count in frame.groupby('split').size().items()}


def quantiles(scores, maps, calibration):
    scores = np.asarray(scores, dtype=float)
    require(scores.ndim == 1 and len(scores) > 0 and np.isfinite(scores).all(), 'Invalid normal scores')
    require(maps.shape == (len(scores), 256, 256) and np.isfinite(maps).all(), 'Normal map count/finiteness differs')
    require(calibration['comparison'] == '>' and calibration['quantile_method'] == 'higher', 'Calibration semantics differ')
    require(calibration['normal_calibration_count'] == len(scores), 'Calibration count differs')
    image = float(np.sort(scores)[math.ceil(.95 * (len(scores) - 1))])
    rank = math.ceil(.99 * (maps.size - 1))
    pixel = float(np.partition(np.asarray(maps).ravel().copy(), rank)[rank])
    close(image, calibration['image_threshold'], 'Independent image quantile differs')
    close(pixel, calibration['pixel_threshold'], 'Independent pixel quantile differs')
    return image, pixel


def memory_coordinates(fit, size, selected, metadata, bank):
    grid = size // 8
    candidates = len(fit) * grid * grid
    require(bank.shape == (4096, 384) and np.isfinite(bank).all(), 'Invalid full-dimensional bank')
    require(selected.shape == (4096,) and np.issubdtype(selected.dtype, np.integer), 'Invalid selected count/type')
    require(len(np.unique(selected)) == 4096 and (selected >= 0).all() and (selected < candidates).all(), 'Invalid/duplicate selected index')
    require(metadata['count'] == 4096 and metadata['candidate_count'] == candidates, 'Memory population differs')
    require(metadata['scoring_dimensions'] == 384 and metadata['selection_projection_only'], 'Projection affects scoring')
    require(metadata['fit_image_ids'] == fit.image_id.tolist(), 'Fitting order differs')
    refs = metadata['references']; require(len(refs) == 4096, 'Reference metadata count differs')
    for order, (position, ref) in enumerate(zip(selected, refs)):
        image_index, cell = divmod(int(position), grid * grid)
        row, column = divmod(cell, grid)
        require((ref['flat_index'], ref['image_id'], ref['row'], ref['column'], ref['memory_index'], ref['selection_order']) ==
                (int(position), fit.iloc[image_index].image_id, row, column, order, order), 'Reference coordinate identity differs')
    close(metadata['fraction'], 4096 / candidates, 'Sampling fraction differs')
    require(metadata['represented_fit_images'] == len({r['image_id'] for r in refs}), 'Represented images differs')
    close(metadata['padding_center_fraction'], float(np.mean([r['is_padding_center'] for r in refs])), 'Padding composition arithmetic differs')
    return candidates, refs


def verify_normals(root, size, write=True):
    root = Path(root).resolve(); stage = root / STAGE; out = stage / RUNS[size]
    require(not (stage / 'anomaly_access.json').exists(), 'Normal review must precede anomaly access')
    normal = read_json(stage / 'normal_protocol.json'); config = normal['config']
    hash_files(root, normal['frozen_files'])
    verify_frozen(root, read_json(root / 'docs/protocol.json'))
    selector_expected = dict(memory_count=4096, all_fitting_candidates=True, projection_dimensions=64,
                             scoring_dimensions=384, projection_seed=43, selection_seed=42, initial_anchor_count=10)
    require(all(config['selector'].get(key) == value for key, value in selector_expected.items()), 'Inherited selector differs')
    require(all(config['calibration'].get(key) == value for key, value in
                dict(image_quantile=.95, pixel_quantile=.99, method='higher', comparison='>').items()), 'Inherited calibration differs')
    geometry_review = read_json(root / config.get('geometry_review', f'{STAGE}/normal_geometry_review.json'))
    require(geometry_review['passed'] and geometry_review['geometry'] == config['geometry'], 'Geometry reviewed parameters differ')
    require(normal['anomalies_exposed'] is False and normal['held_out_normals_decoded'] is False, 'Normal protocol exposure differs')
    frame = pd.read_csv(root / config.get('normal_manifest', f'{STAGE}/pcb2_normals/normal_manifest.csv'), keep_default_na=False)
    counts = verify_split(frame)
    routes = pd.read_csv(stage / 'pcb2_normals/official_normal_routes.csv', keep_default_na=False)
    require(set(frame.source_path) == set(routes.image), 'Official normal routes differ')
    expected_official = dict(zip(routes.image, routes.official_split))
    for row in frame.itertuples():
        require(row.official_split == expected_official[row.source_path], 'Official normal split differs')
        expected_id = canonical_hash(dict(source_revision='2a692ab575001cbde74d402d897a7286086c6199', path=row.source_path, sha256=row.sha256))[:24]
        require(row.image_id == expected_id, 'Canonical normal ID differs')
    require(counts == normal['normal_split_counts'], 'Frozen normal split counts differ')
    for column in ['mask_path', 'mask_sha256', 'defect_types']:
        if column in frame: require(frame[column].eq('').all(), 'Sealed annotations in normal manifest')
    raw_root = root
    # SHA checking acquired heldout bytes does not decode them.
    for row in frame.itertuples():
        path = raw_root / row.image_path
        require(digest(path) == row.sha256, 'Normal raw SHA differs')
        if row.split != 'normal_test':
            with Image.open(path) as image:
                image.load()
                require(image.mode == 'RGB' and image.size == (int(row.width), int(row.height)) and int(image.getexif().get(274, 1)) == 1, 'Normal decode/dimensions/orientation differs')
    pcb1 = pd.read_csv(root / 'data/manifests/pcb1_manifest.csv', keep_default_na=False)
    require(not set(frame.sha256) & set(pcb1.sha256), 'Cross-category exact duplicate invalidates freshness')
    protocol = read_json(out / 'protocol.json'); prepared = read_json(out / 'prepared.json')
    normal_hash = digest(stage / 'normal_protocol.json')
    require(protocol['normal_protocol_sha256'] == prepared['normal_protocol_sha256'] == normal_hash, 'Normal protocol identity differs')
    require(protocol['input_size'] == size and protocol['config'] == config, 'Recipe differs')
    require(protocol['role'] == ('primary' if size == 256 else 'secondary'), 'Primary designation differs')
    require(prepared['normal_only'] and prepared['resource_gate_passed'] and prepared['normal_test_decoded'] is False, 'Normal-only gate differs')
    require(normal['frozen_at_utc'] < prepared['completed_at_utc'], 'Normal freeze/preparation chronology differs')
    hash_files(root, prepared['prerequisites'])
    paths = prepared['array_paths']
    require(paths == read_json(out / 'array_paths.json'), 'Array path declaration differs')
    require(all(paths[key] in prepared['prerequisites'] for key in ['memory', 'projected', 'calibration_maps']), 'Array identities missing from preparation')
    start = read_json(out / 'prepare_started.json')
    require(normal['frozen_at_utc'] < start['started_at_utc'] < prepared['completed_at_utc'], 'Preparation start chronology differs')
    runtime = read_json(out / 'normal_runtime.json'); caps = config['caps']
    for key in ['preparation_seconds', 'peak_rss_bytes', 'median_inference_seconds']:
        require(np.isfinite(runtime[key]) and 0 <= runtime[key] <= caps[key], f'Normal resource gate differs: {key}')
    fit = frame[frame.split == 'fit'].reset_index(drop=True); cal = frame[frame.split == 'calibration']
    table = pd.read_csv(out / 'calibration_predictions.csv')
    require(table.image_id.tolist() == cal.image_id.tolist(), 'Calibration IDs/order differs')
    maps = np.load(root / paths['calibration_maps'], mmap_mode='r', allow_pickle=False)
    thresholds = read_json(out / 'calibration.json'); quantiles(table.score.to_numpy(), maps, thresholds)
    transforms = read_json(out / 'calibration_transforms.json')
    require(set(transforms) == set(cal.image_id), 'Calibration transform membership differs')
    for index, row in enumerate(cal.itertuples()):
        model_path = root / paths['calibration_model_maps'] / f'{row.image_id}.npy'
        require(str(model_path.relative_to(root)) in prepared['prerequisites'], 'Normal model map not hash bound')
        model = np.load(model_path, allow_pickle=False)
        require(np.isfinite(model).all(), 'Nonfinite calibration model map')
        _, common = independent_inverse(model, transforms[row.image_id])
        require(np.array_equal(common, maps[index]), 'Independent normal inverse map differs')
    del maps
    bank = np.load(root / paths['memory'], allow_pickle=False); selected = np.load(out / 'selected_indices.npy', allow_pickle=False)
    metadata = read_json(out / 'memory_metadata.json')
    candidates, refs = memory_coordinates(fit, size, selected, metadata, bank)
    cache = np.load(root / paths['projected'], mmap_mode='r', allow_pickle=False)
    require(cache.shape == (candidates, 64) and cache.dtype == np.float32, 'Projected cache population differs')
    # Chunk finite checks avoid materializing the full candidate matrix.
    for start in range(0, len(cache), 65536): require(np.isfinite(cache[start:start + 65536]).all(), 'Nonfinite projected cache')
    selector = config['selector']
    require(np.array_equal(selected[:16], independent_prefix(cache, 16, selector['selection_seed'], selector['initial_anchor_count'])), 'Independent selection prefix differs')
    from .geometry_experiment import DynamicExtractor, setup
    from .stage4_transfer import tensor_and_transform
    setup(root); extractor = DynamicExtractor()
    generator = torch.Generator(device='cpu').manual_seed(selector['projection_seed'])
    projection = torch.randn(384, 64, generator=generator).numpy() / np.float32(8.)
    require(hashlib.sha256(projection.tobytes()).hexdigest() == metadata['projection_sha256'], 'Independent projection identity differs')
    sampled = [0, 1024, 2048, 3072, 4095]
    for order in sampled:
        ref = refs[order]; row = next(fit[fit.image_id == ref['image_id']].itertuples())
        tensor, _ = tensor_and_transform(root, row, size, config)
        feature = extractor(tensor[None])[0, :, ref['row'], ref['column']].numpy()
        require(np.allclose(feature, bank[order], atol=1e-5, rtol=1e-5), 'Re-extracted vector differs')
        require(np.allclose(feature @ projection, cache[ref['flat_index']], atol=1e-4, rtol=1e-4), 'Projected reference differs')
    receipt = {'reviewed_at_utc': now(), 'passed': True, 'size': size,
               'review_code_sha256': digest(__file__), 'prepared_sha256': digest(out / 'prepared.json'),
               'normal_protocol_sha256': normal_hash, 'all_hashes_and_exact_group_splits_checked': True,
               'normal_quantile_ranks_verified': True, 'all_calibration_inverse_maps_verified': True,
               'selected_4096_fitting_coordinates_verified': True, 'reextracted_orders': sampled,
               'independent_selection_prefix_count': 16, 'full_4096_selector_not_rerun': True,
               'held_out_normals_decoded': False, 'anomaly_images_masks_types_accessed': False}
    if write: write_new(out / 'independent_normal_review.json', receipt)
    return receipt


def verify_confirmation(root, size):
    """Read sealed annotations only after the requested frozen run is complete."""
    root = Path(root).resolve(); stage = root / STAGE; out = stage / RUNS[size]
    done = read_json(out / 'complete.json')
    freeze = read_json(stage / 'freeze_receipt.json'); freeze_hash = digest(stage / 'freeze_receipt.json')
    require(done['confirmatory'] and done['freeze_receipt_sha256'] == freeze_hash, 'Confirmation freeze differs')
    hash_files(root, freeze['frozen_files']); hash_files(root, done['outputs'])
    require(f'{STAGE}/confirmation_data/complete.json' in done['outputs'], 'Missing shared confirmation data identity')
    dataset_done = read_json(stage / 'confirmation_data/complete.json')
    hash_files(root, dataset_done['outputs']); hash_files(root, dataset_done['raw_files'])
    prepared = read_json(out / 'prepared.json'); hash_files(root, prepared['prerequisites'])
    normal_review = read_json(out / 'independent_normal_review.json')
    require(normal_review['passed'] and normal_review['prepared_sha256'] == digest(out / 'prepared.json'), 'Normal review identity differs')
    shared = read_json(stage / 'anomaly_access.json'); access = read_json(out / 'confirmation_access.json')
    require(shared['freeze_receipt_sha256'] == access['freeze_receipt_sha256'] == freeze_hash and access['evaluation_count'] == 1, 'Access identity/count differs')
    require(prepared['completed_at_utc'] < normal_review['reviewed_at_utc'] < freeze['frozen_at_utc'] < shared['first_anomaly_access_utc'] <= access['started_at_utc'] < done['completed_at_utc'], 'Confirmation chronology differs')
    require(access['role'] == done['role'] == ('primary' if size == 256 else 'secondary'), 'Primary/secondary designation differs')
    if size == 512:
        require(read_json(stage / RUNS[256] / 'complete.json')['completed_at_utc'] < access['started_at_utc'], 'Secondary preceded primary completion')
    config = freeze['config']; paths = prepared['array_paths']
    frame = pd.read_csv(out / 'confirmation_manifest.csv', keep_default_na=False)
    shared_frame = pd.read_csv(stage / 'confirmation_data/test_manifest.csv', keep_default_na=False)
    require(frame.equals(shared_frame), 'Shared full test manifest differs')
    normal = pd.read_csv(root / config.get('normal_manifest', f'{STAGE}/pcb2_normals/normal_manifest.csv'), keep_default_na=False)
    require(len(frame) == 200 and frame.image_id.is_unique and frame.label.value_counts().to_dict() == {'normal': 100, 'anomaly': 100}, 'Full confirmation population differs')
    require(frame.official_split.eq('test').all() and frame.split.eq('test').all(), 'Official test membership differs')
    require(set(frame.loc[frame.label == 'normal', 'image_id']) == set(normal.loc[normal.split == 'normal_test', 'image_id']), 'Heldout normal membership differs')
    require(not set(frame.sha256) & set(normal.loc[normal.split != 'normal_test', 'sha256']), 'Train/test duplicate leakage')
    pcb1 = pd.read_csv(root / 'data/manifests/pcb1_manifest.csv', keep_default_na=False)
    require(not set(frame.sha256) & set(pcb1.sha256), 'Cross-category duplicate invalidates fresh confirmation')
    for row in frame.itertuples():
        require(digest(root / row.image_path) == row.sha256, 'Confirmation raw SHA differs')
        require(row.image_id == canonical_hash(dict(source_revision='2a692ab575001cbde74d402d897a7286086c6199', path=row.source_path, sha256=row.sha256))[:24], 'Confirmation canonical ID differs')
        if row.label == 'anomaly': require(digest(root / row.mask_path) == row.mask_sha256, 'Mask SHA differs')
        else: require(not row.mask_path, 'Normal has mask')
    table = pd.read_csv(out / 'predictions.csv')
    require(table.image_id.tolist() == frame.image_id.tolist() and table.label.tolist() == frame.label.tolist(), 'Saved prediction membership differs')
    require(table.image_id.is_unique and np.isfinite(table.score).all(), 'Invalid image scores')
    require(np.isfinite(table.seconds).all() and (table.seconds >= 0).all(), 'Invalid per-image timing')
    close(metrics_value := read_json(out / 'metrics.json')['runtime']['median_inference_seconds'], float(np.median(table.seconds)), 'Median timing arithmetic differs')
    close(read_json(out / 'metrics.json')['runtime']['p95_inference_seconds'], float(np.quantile(table.seconds, .95)), 'P95 timing arithmetic differs')
    require(metrics_value <= config['caps']['median_inference_seconds'], 'Confirmation latency cap exceeded')
    calibration = pd.read_csv(out / 'calibration_predictions.csv')
    thresholds = read_json(out / 'calibration.json')
    image_threshold, pixel_threshold = quantiles(calibration.score.to_numpy(), np.load(root / paths['calibration_maps'], mmap_mode='r'), thresholds)
    metrics = read_json(out / 'metrics.json'); labels = table.label.eq('anomaly').to_numpy(); scores = table.score.to_numpy()
    require(np.array_equal(scores > image_threshold, table.detected.to_numpy()), 'Saved image decisions differ')
    for key, value in direct_confusion(labels, scores, image_threshold).items(): close(metrics['image'][key], value, 'Confusion arithmetic differs')
    close(metrics['image']['average_precision'], ranked_average_precision(labels, scores), 'Image AP differs')
    close(metrics['image']['auroc'], pairwise_auroc(labels, scores), 'AUROC differs')
    transforms = read_json(out / 'test_transforms.json'); require(set(transforms) == set(frame.image_id), 'Transform membership differs')
    anomaly_ids = sorted(frame.loc[frame.label == 'anomaly', 'image_id']); source_sample = {anomaly_ids[index] for index in [0, 50, 99]}
    masks, maps, aps = [], [], []; intersection = union = peak = overlap = 0
    for row, record in zip(frame.itertuples(), table.to_dict('records')):
        model = np.load(root / paths['model_maps'] / f'{row.image_id}.npy', allow_pickle=False)
        common = np.load(root / paths['anomaly_maps'] / f'{row.image_id}.npy', allow_pickle=False)
        require(common.shape == (256, 256) and np.isfinite(common).all() and np.isfinite(model).all(), 'Invalid confirmation map')
        source, reconstructed = independent_inverse(model, transforms[row.image_id])
        require(np.array_equal(common, reconstructed) and source.shape == (int(row.height), int(row.width)), 'Independent confirmation inverse differs')
        mask = np.zeros((256, 256), bool)
        if row.label == 'anomaly':
            with Image.open(root / row.mask_path) as image:
                raw_mask = np.asarray(image) > 0
                mask = np.asarray(image.resize((256, 256), Image.Resampling.NEAREST)) > 0
            require(raw_mask.shape == source.shape and raw_mask.any(), 'Source mask denominator differs')
            require(json.loads(record['defect_types']) == json.loads(row.defect_types), 'Source defect membership differs')
            x0, y0, x1, y1 = transforms[row.image_id]['crop_box']
            close(record['source_annotation_outside_crop_fraction'], 1 - float(raw_mask[y0:y1, x0:x1].sum() / raw_mask.sum()), 'Clipped annotation fraction differs')
            if row.image_id in source_sample: pixel_check(raw_mask, source, pixel_threshold, record, 'source_')
        inter, uni, pp, ap = pixel_check(mask, common, pixel_threshold, record)
        masks.append(mask); maps.append(common); intersection += inter; union += uni
        if row.label == 'anomaly': aps.append(ap); peak += pp; overlap += inter > 0
    local = metrics['localization_common256']
    require(local['n_images'] == 200 and local['n_pixels'] == 200 * 256 * 256 and local['includes_normal_images'], 'Pooled denominator differs')
    require(local['intersection_pixels'] == intersection and local['union_pixels'] == union and local['positive_pixels'] == int(np.asarray(masks).sum()), 'Pooled pixel arithmetic differs')
    close(local['pixel_iou'], intersection / union, 'Pooled IoU differs')
    close(local['pixel_average_precision'], ranked_average_precision(np.asarray(masks), np.asarray(maps)), 'Pooled AP differs')
    summary = metrics['anomaly_localization']['common256_']
    for key, value in [('median_per_image_pixel_ap', np.median(aps)), ('q25', np.quantile(aps, .25)), ('q75', np.quantile(aps, .75)), ('peak_inside_count', peak), ('overlap_count', overlap)]:
        close(summary[key], value, 'Common localization summary differs')
    anomalous = table[table.label == 'anomaly']
    definitions = read_json(out / 'size_group_definitions.json')
    edges = np.asarray(config['size_slices']['edges'])
    require(np.array_equal(edges, definitions['reference_edges']), 'Reference size edges differ')
    supplement = np.quantile(anomalous.mask_area_fraction, [.25, .5, .75], method='higher')
    require(np.array_equal(supplement, definitions['pcb2_supplement_edges']), 'Supplemental size quartiles differ')
    for column, bands, prefix in [('reference_area_band', edges, 'R'), ('pcb2_size_quartile', supplement, 'Q')]:
        require(anomalous[column].tolist() == [f'{prefix}{1 + int(np.searchsorted(bands, value, side="left"))}' for value in anomalous.mask_area_fraction], 'Common256 size group/ties differ')
    close(metrics['geometry']['maximum_annotation_outside_fraction'], float(anomalous.source_annotation_outside_crop_fraction.max()), 'Maximum crop clipping differs')
    require(metrics['geometry']['anomaly_with_annotation_outside_crop_count'] == int(anomalous.source_annotation_outside_crop_fraction.gt(0).sum()), 'Crop clipping count differs')
    fit = normal[normal.split == 'fit'].reset_index(drop=True)
    memory_coordinates(fit, size, np.load(out / 'selected_indices.npy'), read_json(out / 'memory_metadata.json'), np.load(root / paths['memory']))
    require(normal_review['review_code_sha256'] == digest(__file__), 'Normal/full reviewer identity differs')
    receipt = dict(reviewed_at_utc=now(), passed=True, size=size, role=access['role'],
                   review_code_sha256=digest(__file__), complete_sha256=digest(out / 'complete.json'),
                   freeze_receipt_sha256=freeze_hash, normal_review_sha256=digest(out / 'independent_normal_review.json'),
                   all_hashes_and_timestamps_checked=True, all_200_image_flags_ap_auroc_confusion_checked=True,
                   all_200_inverse_maps_checked=True, all_100_anomaly_common_ap_checked=True,
                   pooled_full_denominator_ap_iou_checked=True, source_resolution_sample_ids=sorted(source_sample),
                   source_resolution_not_all_independently_recomputed=True, selected_4096_fitting_coordinates_checked=True)
    write_new(out / 'independent_review.json', receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--root', default='.')
    parser.add_argument('--size', type=int, choices=[256, 512], required=True)
    parser.add_argument('--phase', choices=['normal', 'confirmation'], required=True)
    args = parser.parse_args(); review = verify_normals if args.phase == 'normal' else verify_confirmation
    print(json.dumps(review(args.root, args.size), indent=2))


if __name__ == '__main__': main()

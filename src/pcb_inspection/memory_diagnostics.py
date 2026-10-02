"""Fixed-fitting-normal memory composition and full-dimensional coverage checks.

Projection and anomaly outcomes are never used here. Patch-center padding labels
are proxies, not statements about the entire backbone receptive field.
"""
import argparse
import json
from pathlib import Path
import resource
import time

import numpy as np
import pandas as pd
import torch

from .provenance import canonical_hash, immutable_json, sha256_file


def fixed_query_indices(population, count=2048, seed=44):
    if population < count or count < 1 or seed < 0:
        raise ValueError('Positive sample count cannot exceed fitting population')
    return np.sort(np.random.default_rng(seed).choice(population, count, replace=False)).astype(np.int64)


def reference_geometry(reference, geometry, input_size):
    """Map a feature-cell center through the saved crop/letterbox transform."""
    if input_size not in (256, 512):
        raise ValueError('Only declared input sizes permitted')
    grid = input_size//8
    row, column = int(reference['row']), int(reference['column'])
    if not 0 <= row < grid or not 0 <= column < grid:
        raise ValueError('Reference position outside feature grid')
    x0,y0,x1,y1 = geometry['crop_box']
    width,height = x1-x0,y1-y0
    if width <= 0 or height <= 0:
        raise ValueError('Invalid crop geometry')
    scale = min(input_size/width, input_size/height)
    resized_width,resized_height = max(1,round(width*scale)),max(1,round(height*scale))
    pad_x,pad_y = (input_size-resized_width)//2,(input_size-resized_height)//2
    center_x,center_y = (column+.5)*8,(row+.5)*8
    padding = not (pad_x <= center_x < pad_x+resized_width and pad_y <= center_y < pad_y+resized_height)
    normalized_x,normalized_y = (center_x-pad_x)/resized_width,(center_y-pad_y)/resized_height
    region = 'padding_center' if padding else f'row{min(2,int(normalized_y*3))}_col{min(2,int(normalized_x*3))}'
    return {'feature_map_x': column, 'feature_map_y': row,
            'input_center_x': center_x, 'input_center_y': center_y,
            'source_patch_x': float(x0+normalized_x*width), 'source_patch_y': float(y0+normalized_y*height),
            'normalized_crop_x': normalized_x, 'normalized_crop_y': normalized_y,
            'is_padding_patch_center_proxy': bool(padding), 'normalized_crop_region': region,
            'content_width': resized_width, 'content_height': resized_height, 'pad_x': pad_x, 'pad_y': pad_y}


def coverage_statistics(distances):
    distances = np.asarray(distances,dtype=np.float64)
    if distances.ndim != 1 or not len(distances) or not np.isfinite(distances).all() or (distances < 0).any():
        raise ValueError('Nonnegative finite nonempty distances required')
    return {'query_count': len(distances), 'mean': float(distances.mean()), 'median': float(np.median(distances)),
            'p95': float(np.quantile(distances,.95)), 'maximum': float(distances.max()),
            'zero_distance_fraction': float((distances == 0).mean()),
            'quantile_method': 'linear', 'zero_distance_convention': 'Exactly zero, no tolerance band'}


def _load_bank(root, path, fit, size):
    path = Path(path)
    if not (path/'prepared.json').is_file():
        raise ValueError('Completed normal-only preparation required for diagnostics')
    prepared = json.loads((path/'prepared.json').read_text())
    protocol = json.loads((path/'protocol.json').read_text())
    if prepared['protocol_sha256'] != sha256_file(path/'protocol.json'):
        raise ValueError('Memory protocol hash changed')
    for relative, expected in protocol['frozen_files'].items():
        if sha256_file(root/relative) != expected:
            raise ValueError(f'Frozen input changed: {relative}')
    for relative, expected in prepared['prerequisites'].items():
        if sha256_file(path/relative) != expected:
            raise ValueError(f'Prepared memory identity changed: {relative}')
    bank = np.load(path/'memory.npy',allow_pickle=False)
    metadata = json.loads((path/'memory_metadata.json').read_text())
    grid = size//8
    expected_count = len(fit)*grid*grid
    if bank.shape != (4096,384) or not np.isfinite(bank).all() or metadata['candidate_count'] != expected_count:
        raise ValueError('Memory count/features/population differs from matched experiment')
    references = metadata['references']
    if len(references) != len(bank) or len({item['flat_index'] for item in references}) != len(bank):
        raise ValueError('Repeated or missing memory references')
    indices = {item['memory_index'] for item in references}
    if indices != set(range(len(bank))):
        raise ValueError('Memory array/reference index mismatch')
    fit_ids = fit.image_id.tolist()
    for reference in references:
        index = reference['flat_index']
        if not 0 <= index < expected_count:
            raise ValueError('Reference outside fitting candidate population')
        image_index, patch = divmod(index,grid*grid)
        row,column = divmod(patch,grid)
        if reference['image_id'] != fit_ids[image_index] or (reference['row'],reference['column']) != (row,column):
            raise ValueError('Reference is not a correctly mapped fitting-normal candidate')
    return torch.from_numpy(bank), references, metadata


def generate_memory_diagnostics(root, size, coreset_run=None, query_count=2048, query_seed=44):
    root = Path(root).resolve()
    if size not in (256,512):
        raise ValueError('Only declared sizes permitted')
    output = root/'artifacts/stage3_memory_diagnostics'/str(size)
    if output.exists():
        raise FileExistsError('Memory diagnostic output is immutable; existing directory refused')
    frame = pd.read_csv(root/'data/manifests/pcb1_manifest.csv',keep_default_na=False)
    fit = frame.loc[frame.split=='fit'].reset_index(drop=True)
    if not fit.label.eq('normal').all() or fit.image_id.duplicated().any():
        raise ValueError('Unique fitting normals required')
    uniform_path = root/f'artifacts/runs/geometry_{size}_v1'
    coreset_path = root/coreset_run if coreset_run else root/f'artifacts/runs/coreset_{size}_v1'
    uniform,uniform_refs,uniform_metadata = _load_bank(root,uniform_path,fit,size)
    coreset,coreset_refs,coreset_metadata = _load_bank(root,coreset_path,fit,size)
    geometries = json.loads((root/'artifacts/pcb1_geometry/normal_transforms.json').read_text())
    population = len(fit)*(size//8)**2
    query_indices = fixed_query_indices(population,query_count,query_seed)
    saved_indices = np.load(coreset_path/'cache/query_flat_indices.npy',allow_pickle=False)
    np.testing.assert_array_equal(saved_indices,query_indices)
    np.testing.assert_array_equal(np.load(coreset_path/'coverage_query_indices.npy',allow_pickle=False),query_indices)
    queries = np.load(coreset_path/'cache/coverage_queries.npy',allow_pickle=False)
    if queries.shape != (query_count,384) or queries.dtype != np.float32 or not np.isfinite(queries).all():
        raise ValueError('Saved full-dimensional query geometry differs')
    distances = pd.read_csv(coreset_path/'coverage_distances.csv')
    if len(distances) != query_count:
        raise ValueError('Saved coverage table length differs')
    np.testing.assert_array_equal(distances.query_index.to_numpy(),np.arange(query_count))
    np.testing.assert_array_equal(distances.flat_index.to_numpy(),query_indices)
    grid = size//8
    query_image_subset = sorted(set((query_indices//(grid*grid)).tolist()))
    distances['source_image_id'] = [fit.iloc[int(flat)//(grid*grid)].image_id for flat in query_indices]
    query_geometry = [reference_geometry({'row':int(flat)%(grid*grid)//grid,'column':int(flat)%grid},geometries[image_id],size) for flat,image_id in zip(query_indices,distances.source_image_id)]
    for key in ('feature_map_x','feature_map_y','source_patch_x','source_patch_y','is_padding_patch_center_proxy','normalized_crop_region'):
        distances[key] = [item[key] for item in query_geometry]
    saved_coverage = json.loads((coreset_path/'coverage.json').read_text())
    started = time.perf_counter()
    verification_positions = np.sort(np.random.default_rng(45).choice(query_count,min(16,query_count),replace=False))
    coverage,composition = {},{}
    tables = {}
    for method,bank,references in [('uniform',uniform,uniform_refs),('coreset',coreset,coreset_refs)]:
        values = distances[f'{method}_nearest_distance'].to_numpy(dtype=float)
        nearest_indices = distances[f'{method}_nearest_memory_index'].to_numpy()
        if not np.issubdtype(nearest_indices.dtype,np.integer) or (nearest_indices<0).any() or (nearest_indices>=len(bank)).any():
            raise ValueError('Saved nearest reference index differs')
        recorded_stats = saved_coverage['uniform_control' if method=='uniform' else method]
        coverage[method] = coverage_statistics(values)
        for key in ('mean','median','p95','maximum'):
            if not np.isclose(recorded_stats[key],coverage[method][key],rtol=2e-6,atol=2e-6):
                raise ValueError(f'Saved coverage summary differs: {method}/{key}')
        # Independent direct float64 arithmetic on saved features, not the
        # runner nearest-distance implementation; no image inference required.
        points = bank.numpy().astype(np.float64)
        for position in verification_positions:
            direct = np.linalg.norm(points-queries[position].astype(np.float64),axis=1)
            if not np.isclose(direct.min(),values[position],rtol=2e-5,atol=2e-5) or not np.isclose(direct[nearest_indices[position]],values[position],rtol=2e-5,atol=2e-5):
                raise ValueError(f'Independent coverage distance differs: {method}/{position}')
        del points
        coverage[method]['independent_direct_distance_queries_checked'] = len(verification_positions)
        selected_indices = {item['flat_index'] for item in references}
        expected_flags = [int(flat) in selected_indices for flat in query_indices]
        if distances[f'{method}_query_is_selected_reference'].tolist() != expected_flags:
            raise ValueError('Saved query/reference self-membership differs')
        coverage[method]['query_selected_reference_count'] = int(sum(expected_flags))
        coverage[method]['padding_center_proxy_slices'] = {str(bool(is_padding)):coverage_statistics(group[f'{method}_nearest_distance'].to_numpy()) for is_padding,group in distances.groupby('is_padding_patch_center_proxy')}
        rows = []
        for selection_order,reference in enumerate(references):
            rows.append({'reference_index': reference['memory_index'], 'flat_index': reference['flat_index'],
                         'source_image_id': reference['image_id'], 'selection_order': reference.get('selection_order',selection_order),
                         **reference_geometry(reference,geometries[reference['image_id']],size)})
        table = pd.DataFrame(rows)
        counts = table.groupby('source_image_id').size().reindex(fit.image_id,fill_value=0).rename('references').reset_index()
        counts = counts.rename(columns={'image_id':'source_image_id'})
        regions = table.groupby('normalized_crop_region').size().rename('references').reset_index()
        regions['fraction'] = regions.references/len(table)
        composition[method] = {'reference_count': len(table), 'unique_source_images': int(table.source_image_id.nunique()),
                               'selected_duplicate_indices': 0,
                               'padding_center_proxy_fraction': float(table.is_padding_patch_center_proxy.mean()),
                               'references_per_fitting_image': {'includes_zero_reference_images': True, 'count': len(counts),
                                 'minimum': int(counts.references.min()), 'median': float(counts.references.median()),
                                 'mean': float(counts.references.mean()), 'p95': float(counts.references.quantile(.95)),
                                 'maximum': int(counts.references.max())}}
        tables[f'{method}_memory_selection'] = table
        tables[f'{method}_references_per_image'] = counts
        tables[f'{method}_normalized_crop_regions'] = regions
    tables['coverage_distances'] = distances
    output.mkdir(parents=True,exist_ok=False)
    for name,table in tables.items():
        table.to_csv(output/f'{name}.csv',index=False,float_format='%.17g')
        table.to_parquet(output/f'{name}.parquet',index=False)
    np.save(output/'query_flat_indices.npy',query_indices)
    hashes = {str(path.relative_to(root)): sha256_file(path) for path in [uniform_path/'memory.npy',uniform_path/'memory_metadata.json',uniform_path/'protocol.json',uniform_path/'prepared.json',coreset_path/'memory.npy',coreset_path/'memory_metadata.json',coreset_path/'protocol.json',coreset_path/'prepared.json',root/'data/manifests/pcb1_manifest.csv',root/'artifacts/pcb1_geometry/normal_transforms.json',coreset_path/'cache/query_flat_indices.npy',coreset_path/'cache/coverage_queries.npy',coreset_path/'coverage_distances.csv',coreset_path/'coverage.json']}
    metadata = {'input_size': size, 'fitting_count': len(fit), 'candidate_count': population,
                'query_count': query_count, 'query_seed': query_seed, 'query_index_sha256': sha256_file(output/'query_flat_indices.npy'),
                'query_image_count': len(query_image_subset), 'coverage': coverage, 'composition': composition,
                'source_hashes': hashes, 'source_identity_hash': canonical_hash(hashes), 'code_sha256': sha256_file(__file__),
                'resource': {'new_feature_extraction_seconds': 0., 'total_seconds': time.perf_counter()-started,
                             'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},
                'definitions': {'population': 'All ordered fitting-normal feature positions, including letterbox padding; same full population for both banks',
                    'query_sample': 'Seed44 independent uniform sampling without replacement, sorted global positions; fitting-only descriptive coverage, not independent normal validation',
                    'coverage': 'Saved preparation-query scores; summary arithmetic plus16seed45 directfloat64 nearest checks independently verified. Exact Euclidean distance in original384-dimensional scoring representation to nearest selected reference; no projection or anomaly masks',
                    'padding_proxy': 'Equal-grid feature-cell center ((column+.5)*8,(row+.5)*8) outside half-open resized-content rectangle; receptive fields may cross content/padding boundaries',
                    'coordinates': 'Continuous edge coordinates; source position mapped through crop/rounded letterbox resize. Proxy centers do not assert exact backbone receptive-field center.',
                    'regions': '3x3 bins in normalized source-crop content coordinates; padding centers separate. Descriptive composition only, no selection/scoring exclusion.',
                    'selection_order': 'Coreset metadata selection order if present; otherwise bank/reference enumeration. Uniform has source-order bank indices, not a greedy ordering.',
                    'self_matches': 'Query may be selected; exact-zero distance fraction and selected-query count reported explicitly'},
                'no_anomaly_access': True, 'no_pcb2_access': True,
                'outputs': {path.name: sha256_file(path) for path in sorted(output.iterdir())}}
    immutable_json(output/'memory_diagnostics.json',metadata)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',default='.')
    parser.add_argument('--size',type=int,choices=[256,512],required=True)
    parser.add_argument('--coreset-run',default=None)
    args = parser.parse_args()
    result = generate_memory_diagnostics(args.root,args.size,args.coreset_run)
    print(json.dumps({'coverage': result['coverage'], 'composition': result['composition']},indent=2))


if __name__ == '__main__':
    main()

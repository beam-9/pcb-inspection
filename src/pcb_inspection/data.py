"""Structural audit and immutable official-test-preserving split manifests.

Audit reads held-out files only to verify integrity/geometry/mask semantics. It
never emits held-out image views, computes model scores, or selects settings.
"""
import csv
import io
import math
import re
import json
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
from .provenance import canonical_hash, immutable_json, sha256_file


def load_manifest(path):
    return pd.read_csv(path, keep_default_na=False)


def validate_manifest(frame):
    required = {'image_id', 'image_path', 'mask_path', 'label', 'official_split', 'split', 'sha256', 'duplicate_group'}
    if not required.issubset(frame.columns):
        raise ValueError(f'Missing manifest columns: {sorted(required-set(frame.columns))}')
    if frame.empty or frame.image_id.duplicated().any():
        raise ValueError('Manifest is empty or image IDs are duplicated')
    if not set(frame.split).issubset({'fit', 'calibration', 'test'}):
        raise ValueError('Unknown split')
    if set(frame.split) != {'fit', 'calibration', 'test'}:
        raise ValueError('Fit/calibration/test must all be nonempty')
    if not set(frame.official_split).issubset({'train', 'test'}):
        raise ValueError('Unknown official split')
    if not all(re.fullmatch('[0-9a-f]{24}', str(value)) for value in frame.image_id):
        raise ValueError('Malformed immutable image identity')
    if not all(re.fullmatch('[0-9a-f]{64}', str(value)) for value in frame.sha256):
        raise ValueError('Malformed SHA-256 identity')
    if not frame.sha256.eq(frame.duplicate_group).all():
        raise ValueError('Exact duplicate group differs from SHA-256')
    if frame.image_path.duplicated().any() or frame.image_path.eq('').any():
        raise ValueError('Missing or repeated source path')
    if not set(frame.label).issubset({'normal', 'anomaly'}):
        raise ValueError('Unknown label')
    if (frame.loc[frame.split != 'test', 'label'] != 'normal').any():
        raise ValueError('Only normal images may enter fit/calibration')
    if frame.loc[frame.label == 'anomaly', 'mask_path'].eq('').any():
        raise ValueError('Abnormal mask path missing')
    if (frame.loc[frame.official_split == 'test', 'split'] != 'test').any():
        raise ValueError('Official test changed')
    if (frame.loc[frame.official_split == 'train', 'split'] == 'test').any():
        raise ValueError('Official train changed')
    for digest, group in frame.groupby('sha256'):
        if group.label.nunique() > 1:
            raise ValueError(f'Exact duplicate has conflicting labels: {digest}')
        if group.split.nunique() > 1:
            raise ValueError(f'Exact duplicate leakage: {digest}')
    return True


def _dhash(image):
    small = np.asarray(image.convert('L').resize((9, 8), Image.Resampling.BILINEAR))
    bits = small[:, 1:] > small[:, :-1]
    return int.from_bytes(np.packbits(bits).tobytes(), 'big')


def build_manifest(raw_root, official_split_csv, output_dir, seed=42):
    raw_root, output_dir = Path(raw_root).resolve(), Path(output_dir)
    source = pd.read_csv(official_split_csv, keep_default_na=False)
    source = source.loc[source.object == 'pcb1'].sort_values('image').copy()
    if source.empty or source.image.duplicated().any():
        raise ValueError('PCB1 source missing or duplicate paths')
    records, excluded, hashes, resize_masks = [], [], [], []
    for item in source.to_dict('records'):
        image_path = raw_root / item['image']
        try:
            with Image.open(image_path) as image:
                image.load()
                width, height = image.size
                if image.mode != 'RGB' or image.getexif().get(274, 1) != 1:
                    raise ValueError('Unsupported image color mode or EXIF orientation')
                image_hash = _dhash(image)
            mask_hash, mask_values, positives = '', [], 0
            mask_path = raw_root / item['mask'] if item['mask'] else None
            if item['label'] == 'anomaly':
                if mask_path is None or not mask_path.is_file():
                    raise ValueError('Missing abnormal mask')
                with Image.open(mask_path) as mask:
                    mask.load()
                    if mask.size != (width, height):
                        raise ValueError('Image/mask geometry differs')
                    mask_array = np.asarray(mask)
                    if mask_array.ndim != 2:
                        raise ValueError('Mask must be scalar class IDs')
                    mask_values = np.unique(mask_array).astype(int).tolist()
                    positives = int(np.count_nonzero(mask_array))
                    if positives == 0:
                        raise ValueError('Anomaly mask is empty')
                    reduced = np.asarray(mask.resize((256, 256), Image.Resampling.NEAREST)) > 0
                    original_fraction = positives / (width * height)
                    resize_masks.append({'image_path': item['image'], 'original_positive_fraction': original_fraction,
                                         'resized_positive_pixels_256': int(reduced.sum()),
                                         'positive_fraction_ratio': float(reduced.mean()/original_fraction)})
                mask_hash = sha256_file(mask_path)
            elif item['mask']:
                raise ValueError('Normal mask unexpectedly explicit: investigate semantics')
            digest = sha256_file(image_path)
            records.append({'image_id': canonical_hash({'source_revision': '2a692ab575001cbde74d402d897a7286086c6199', 'path': item['image'], 'sha256': digest})[:24],
                            'image_path': item['image'], 'mask_path': item['mask'], 'label': item['label'],
                            'official_split': item['split'], 'split': 'test' if item['split'] == 'test' else '',
                            'sha256': digest, 'mask_sha256': mask_hash, 'duplicate_group': digest,
                            'width': width, 'height': height, 'channels': 3,
                            'mask_values': ','.join(map(str, mask_values)), 'positive_mask_pixels': positives})
            hashes.append(image_hash)
        except (OSError, ValueError) as error:
            excluded.append({'image_path': item['image'], 'reason': str(error)})
    frame = pd.DataFrame(records)
    # Cross-official-split duplicate contamination is not repaired by silently
    # changing the benchmark. Stop and require a documented protocol departure.
    for digest, group in frame.groupby('sha256'):
        if group.official_split.nunique() > 1:
            raise ValueError(f'Exact duplicate across official train/test: {digest}')
    train_groups = sorted(frame.loc[frame.official_split == 'train', 'duplicate_group'].unique())
    rng = np.random.default_rng(seed)
    rng.shuffle(train_groups)
    calibration_groups = set(train_groups[:math.ceil(0.2 * len(train_groups))])
    frame.loc[frame.official_split == 'train', 'split'] = frame.loc[frame.official_split == 'train', 'duplicate_group'].map(lambda group: 'calibration' if group in calibration_groups else 'fit')
    validate_manifest(frame)
    # Similarity is a structural screening heuristic, not an object identity claim.
    # Limit investigation to official training normals before model choice.
    candidates = []
    train_indices = frame.index[frame.official_split == 'train'].tolist()
    image_ids, digests = frame.image_id.tolist(), frame.sha256.tolist()
    for position, left in enumerate(train_indices):
        for right in train_indices[position+1:]:
            distance = (hashes[left] ^ hashes[right]).bit_count()
            if distance <= 2 and digests[left] != digests[right]:
                candidates.append({'left_id': image_ids[left], 'right_id': image_ids[right], 'dhash_hamming': distance})
    output_dir.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO()
    frame.to_csv(buffer, index=False, lineterminator='\n')
    payload = buffer.getvalue()
    manifest_path = output_dir / 'pcb1_manifest.csv'
    if manifest_path.exists() and manifest_path.read_text() != payload:
        raise FileExistsError('Manifest already frozen with different membership')
    if not manifest_path.exists():
        with manifest_path.open('x') as stream:
            stream.write(payload)
    split_hash = sha256_file(manifest_path)
    audit = {'category': 'pcb1', 'source_count': len(source), 'included_count': len(frame), 'exclusions': excluded,
             'counts': frame.groupby(['split', 'label']).size().to_dict(), 'seed': seed,
             'manifest_path': manifest_path.name, 'split_hash': split_hash,
             'official_split_sha256': sha256_file(official_split_csv),
             'dimensions': frame.groupby(['width', 'height']).size().reset_index(name='count').to_dict('records'),
             'exact_duplicate_groups': int((frame.groupby('sha256').size() > 1).sum()),
             'near_duplicate_candidates_count': len(candidates),
             'near_duplicate_scope': 'Official training normals only; dHash Hamming <=2; no automatic exclusions',
             'mask_policy': 'Original multi-class scalar labels converted to binary with >0; normal masks implicit zeros',
             'resize_256_mask_audit': {'count': len(resize_masks),
                 'masks_lost_completely': sum(row['resized_positive_pixels_256'] == 0 for row in resize_masks),
                 'positive_fraction_ratio_min': min((row['positive_fraction_ratio'] for row in resize_masks), default=None),
                 'positive_fraction_ratio_max': max((row['positive_fraction_ratio'] for row in resize_masks), default=None)},
             'audit_exposure': 'Structural decode/checksums/geometry/mask count only. No held-out views or model scoring.',
             'physical_object_identity': 'Unavailable: filename and image similarity cannot establish shared physical PCB identities.'}
    audit['counts'] = {f'{split}/{label}': int(count) for (split, label), count in audit['counts'].items()}
    immutable_json(output_dir / 'pcb1_audit.json', audit)
    immutable_json(output_dir / 'pcb1_near_duplicates.json', candidates)
    investigate_near_duplicates(raw_root, frame, candidates, output_dir)
    return audit


def investigate_near_duplicates(raw_root, frame, candidates, output_dir):
    """Numeric-only training-pair investigation; no held-out images accessed."""
    indexed, rows = frame.set_index('image_id'), []
    for candidate in sorted(candidates, key=lambda item: item['dhash_hamming'])[:20]:
        left, right = indexed.loc[candidate['left_id']], indexed.loc[candidate['right_id']]
        if left.official_split != 'train' or right.official_split != 'train':
            raise ValueError('Candidate investigation restricted to training normals')
        arrays = []
        for item in (left, right):
            with Image.open(Path(raw_root)/item.image_path) as image:
                arrays.append(np.asarray(image.resize((64, 64), Image.Resampling.BILINEAR), dtype=float)/255)
        rows.append(dict(candidate, left_path=left.image_path, right_path=right.image_path,
                         left_split=left.split, right_split=right.split,
                         thumbnail_rgb_mae=float(np.abs(arrays[0]-arrays[1]).mean())))
    report = {'scope': '20 lowest dHash-distance official training normal pairs; numeric investigation only',
              'candidate_count': len(candidates), 'pairs': rows,
              'finding': 'Aligned PCB images may share coarse perceptual hashes. Unequal file SHA-256 and thumbnail pixel differences do not establish shared physical board identity. Source supplies no object IDs. No similarity-based exclusions or additional groups inferred.',
              'limitation': 'Unknown repeated-object identity may inflate performance; official image holdout is not a verified unseen-object holdout.'}
    immutable_json(Path(output_dir)/'pcb1_near_duplicate_review.json', report)
    return report

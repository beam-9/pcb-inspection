"""Mechanically gated PCB2 test materialization after final confirmation freeze.

Importing this module does not read data or access the network. The only public
loader verifies freeze/unseal receipts before reading sealed source routes.
"""
from datetime import datetime
import csv
import json
from pathlib import Path, PurePosixPath
import tarfile
import time

import numpy as np
import pandas as pd
from PIL import Image

from .acquisition import ARCHIVE_URL, SOURCE_REVISION, RangeReader
from .diagnostics import parse_defect_types
from .provenance import canonical_hash, immutable_json, sha256_file
from .stage4_data import OUTPUT as NORMAL_OUTPUT, OFFICIAL_SPLIT_SHA256, _immutable_csv

OUTPUT = 'artifacts/stage4/confirmation_data'


def validate_confirmation_gate(root, config):
    """Gate FIRST, before source routing, labels, pixels, masks or network."""
    root=Path(root).resolve();stage=root/'artifacts/stage4'
    receipt_path=stage/'freeze_receipt.json';access_path=stage/'anomaly_access.json'
    if not receipt_path.is_file() or not access_path.is_file():
        raise PermissionError('Final freeze and explicit recorded unseal are required')
    receipt=json.loads(receipt_path.read_text());access=json.loads(access_path.read_text())
    if access.get('freeze_receipt_sha256')!=sha256_file(receipt_path):
        raise PermissionError('Unseal receipt is not bound to the final freeze')
    if receipt.get('config')!=config or receipt.get('anomaly_access_status')!='sealed':
        raise PermissionError('Loaded recipe differs from sealed final freeze')
    if receipt.get('primary',{}).get('run')!='pcb2_d1_primary' or receipt.get('secondary',{}).get('run')!='pcb2_d2_secondary':
        raise PermissionError('Primary/secondary roles were not predeclared')
    if access.get('primary')!='pcb2_d1_primary' or access.get('secondary_predeclared')!='pcb2_d2_secondary':
        raise PermissionError('Unseal role declaration differs')
    if datetime.fromisoformat(access['first_anomaly_access_utc'])<datetime.fromisoformat(receipt['frozen_at_utc']):
        raise PermissionError('Unseal timestamp precedes final freeze')
    for relative,expected in receipt['frozen_files'].items():
        path=(root/relative).resolve()
        if not path.is_relative_to(root) or sha256_file(path)!=expected:
            raise PermissionError('Frozen source identity changed before materialization')
    return receipt


def _test_routes(source):
    rows=[]
    with Path(source).open(newline='') as stream:
        for row in csv.DictReader(stream):
            if row['object']!='pcb2' or row['split']!='test':continue
            if row['label'] not in {'normal','anomaly'}:
                raise ValueError('Unsupported official test label')
            path=PurePosixPath(row['image'])
            expected_class='Anomaly' if row['label']=='anomaly' else 'Normal'
            if path.is_absolute() or '..' in path.parts or len(path.parts)!=5 or path.parts[:4]!=('pcb2','Data','Images',expected_class) or path.suffix.lower() not in {'.jpg','.jpeg','.png'}:
                raise ValueError('Invalid official test image route')
            if row['label']=='anomaly':
                mask=PurePosixPath(row['mask'])
                if not row['mask'] or mask.is_absolute() or '..' in mask.parts or len(mask.parts)!=5 or mask.parts[:4]!=('pcb2','Data','Masks','Anomaly') or mask.suffix.lower()!='.png':
                    raise ValueError('Missing/invalid abnormal mask route')
            elif row['mask']:
                raise ValueError('Unexpected explicit normal mask')
            rows.append({'image':row['image'],'mask':row['mask'],'label':row['label']})
    if not rows or {row['label'] for row in rows}!={'normal','anomaly'} or len({row['image'] for row in rows})!=len(rows):
        raise ValueError('Official test routes empty or repeated')
    return sorted(rows,key=lambda row:row['image'])


def _acquire_ranges(reader, allowed, root, anchor):
    if reader.cache_enabled:raise ValueError('Unseal acquisition uses exact ranges, never prefetch')
    offset=int(anchor);entries=[];seen=set();headers=0;total=0
    while offset+512<=reader.size:
        header=reader.get(offset,512);headers+=1
        if not any(header):break
        info=tarfile.TarInfo.frombuf(header,'utf8','strict');path=PurePosixPath(info.name)
        if path.is_absolute() or '..' in path.parts or info.size<0:raise ValueError('Unsafe archive member')
        if path.parts and path.parts[0]!='pcb2':
            if seen:break
            raise ValueError('Source category boundary changed')
        if str(path) in allowed:
            if not info.isfile() or str(path) in seen:raise ValueError('Invalid/repeated sealed source member')
            total+=info.size
            if total>150_000_000:raise RuntimeError('Bounded PCB2 test acquisition exceeded150MB')
            body=reader.get(offset+512,info.size)
            target=root/'data/raw/stage4'/Path(*path.parts);target.parent.mkdir(parents=True,exist_ok=True)
            import hashlib
            digest=hashlib.sha256(body).hexdigest()
            if target.exists():
                if sha256_file(target)!=digest:raise ValueError('Existing unsealed source differs')
            else:
                with target.open('xb') as stream:stream.write(body)
            entries.append({'source_path':str(path),'path':str(target.relative_to(root)),
                            'sha256':digest,'bytes':info.size,'archive_body_offset':offset+512})
            seen.add(str(path))
        offset+=512+((info.size+511)//512)*512
    if seen!=allowed:raise ValueError('Unsealed official member coverage incomplete')
    return {'entries':entries,'archive_headers_read':headers,'selected_bytes':total,
            'cache_enabled':False,'other_category_payloads_acquired':False}


def _audit_image(path):
    with Image.open(path) as image:
        image.load();orientation=int(image.getexif().get(274,1))
        if image.mode!='RGB' or orientation!=1:raise ValueError('Unsupported test image color/orientation')
        return image.width,image.height,len(image.getbands()),orientation


def load_test_manifest(root, config):
    root=Path(root).resolve();validate_confirmation_gate(root,config)
    output=root/OUTPUT;completion=output/'complete.json'
    if completion.exists():
        finished=json.loads(completion.read_text())
        if finished['freeze_receipt_sha256']!=sha256_file(root/'artifacts/stage4/freeze_receipt.json'):
            raise ValueError('Materialized test set belongs to another freeze')
        for relative,expected in finished['outputs'].items():
            if sha256_file(root/relative)!=expected:raise ValueError('Immutable test artifact changed')
        for relative,expected in finished['raw_files'].items():
            if sha256_file(root/relative)!=expected:raise ValueError('Unsealed raw source changed')
        return pd.read_csv(output/'test_manifest.csv',keep_default_na=False)
    if output.exists():raise FileExistsError('Incomplete test materialization requires explicit invalidation; no silent replay')
    source=root/'data/raw/1cls.csv'
    if sha256_file(source)!=OFFICIAL_SPLIT_SHA256:raise ValueError('Official source split changed')
    routes=_test_routes(source)
    normals=pd.read_csv(root/config.get('normal_manifest',NORMAL_OUTPUT+'/normal_manifest.csv'),keep_default_na=False)
    normal_test=normals.loc[normals.split=='normal_test'].set_index('source_path')
    expected_normals={row['image'] for row in routes if row['label']=='normal'}
    if set(normal_test.index)!=expected_normals:raise ValueError('Held-out normal membership changed')
    allowed={row[field] for row in routes if row['label']=='anomaly' for field in ['image','mask']}
    allowed.add('pcb2/image_anno.csv')
    normal_receipt=json.loads((root/NORMAL_OUTPUT/'normal_acquisition.json').read_text())
    output.mkdir(parents=True,exist_ok=False)
    immutable_json(output/'materialization_started.json',{'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'freeze_receipt_sha256':sha256_file(root/'artifacts/stage4/freeze_receipt.json'),'anomaly_access_sha256':sha256_file(root/'artifacts/stage4/anomaly_access.json'),
        'official_test_counts':{label:sum(row['label']==label for row in routes) for label in ['normal','anomaly']},
        'purpose':'Single dataset unseal shared by predeclared primary/secondary; no retuning'})
    reader=RangeReader(ARCHIVE_URL)
    if reader.etag!=normal_receipt['archive_etag'] or reader.size!=normal_receipt['archive_bytes']:
        reader.conn.close();raise ValueError('Pinned source archive changed before unseal')
    try:
        acquired=_acquire_ranges(reader,allowed,root,normal_receipt['start_header_offset'])
        acquired.update({'url':ARCHIVE_URL,'archive_etag':reader.etag,'transferred_bytes':reader.transferred,
                         'source_revision':SOURCE_REVISION,'freeze_receipt_sha256':sha256_file(root/'artifacts/stage4/freeze_receipt.json')})
    finally:reader.conn.close()
    immutable_json(output/'test_acquisition.json',acquired)
    acquired_paths={item['source_path']:item for item in acquired['entries']}
    owner_path=root/acquired_paths['pcb2/image_anno.csv']['path']
    owner=pd.read_csv(owner_path,keep_default_na=False).set_index('image')
    records=[];mask_details=[];raw_files={}
    for route in routes:
        anomalous=route['label']=='anomaly'
        if anomalous:
            image_relative=acquired_paths[route['image']]['path'];digest=acquired_paths[route['image']]['sha256']
            mask_relative=acquired_paths[route['mask']]['path'];mask_digest=acquired_paths[route['mask']]['sha256']
        else:
            saved=normal_test.loc[route['image']];image_relative=saved.image_path;digest=saved.sha256
            mask_relative=mask_digest=''
        if sha256_file(root/image_relative)!=digest:raise ValueError('Test image identity changed')
        width,height,channels,orientation=_audit_image(root/image_relative)
        annotation=owner.loc[route['image']]
        if annotation['mask']!=route['mask'] or (annotation['label']=='normal')==anomalous:
            raise ValueError('Owner annotation/official binary label or mask pairing differs')
        types=parse_defect_types(annotation['label']) if anomalous else []
        if anomalous:
            if sha256_file(root/mask_relative)!=mask_digest:raise ValueError('Test mask identity changed')
            with Image.open(root/mask_relative) as mask:
                mask.load();array=np.asarray(mask)
                if mask.size!=(width,height) or array.ndim!=2 or int(mask.getexif().get(274,1))!=1:
                    raise ValueError('Unsupported test mask geometry/class representation')
                positive=array>0
                if not positive.any():raise ValueError('Abnormal source mask empty')
                # Ensure inherited convertL >0 path and declared scalar-ID >0
                # semantics agree; do not silently change mask methodology.
                if not np.array_equal(np.asarray(mask.convert('L'))>0,positive):
                    raise ValueError('Scalar mask IDs and inherited grayscale conversion differ')
                resized=np.asarray(Image.fromarray(positive.astype(np.uint8)).resize((256,256),Image.Resampling.NEAREST))>0
                mask_details.append({'image_id':canonical_hash({'source_revision':SOURCE_REVISION,'path':route['image'],'sha256':digest})[:24],
                    'source_positive_pixels':int(positive.sum()),'common256_positive_pixels':int(resized.sum()),
                    'source_mask_values':np.unique(array).astype(int).tolist(),
                    'positive_fraction_ratio':float(resized.mean()/positive.mean()),
                    'positive_pixels_touch_source_edge':bool(positive[0].any() or positive[-1].any() or positive[:,0].any() or positive[:,-1].any())})
            raw_files[mask_relative]=mask_digest
        raw_files[image_relative]=digest
        records.append({'image_id':canonical_hash({'source_revision':SOURCE_REVISION,'path':route['image'],'sha256':digest})[:24],
            'image_path':image_relative,'source_path':route['image'],'sha256':digest,'label':route['label'],
            'official_split':'test','split':'test','mask_path':mask_relative,'mask_sha256':mask_digest,
            'defect_types':json.dumps(types),'source_defect_label':annotation['label'],
            'width':width,'height':height,'channels':channels,'orientation':orientation})
    frame=pd.DataFrame(records)
    fitting_hashes=set(normals.loc[normals.split.isin(['fit','calibration']),'sha256'])
    if set(frame.sha256)&fitting_hashes:raise ValueError('Confirmatory test image exactly duplicates fit/calibration normal')
    prior=pd.read_csv(root/'data/manifests/pcb1_manifest.csv',keep_default_na=False)
    if set(frame.sha256)&set(prior.sha256):raise ValueError('Confirmatory test image exactly duplicates exposed PCB1 image')
    if frame.image_id.duplicated().any():raise ValueError('Repeated confirmatory image identity')
    for digest,group in frame.groupby('sha256'):
        if group.label.nunique()>1:raise ValueError('Exact test duplicates have conflicting outcomes')
    _immutable_csv(output/'test_manifest.csv',frame.to_dict('records'),columns=frame.columns)
    immutable_json(output/'test_mask_audit.json',mask_details)
    audit={'source_revision':SOURCE_REVISION,'counts':{key:int(value) for key,value in frame.label.value_counts().items()},
           'all_images_decoded':True,'all_abnormal_masks_decoded_and_positive':True,'exclusions':[],
           'dimensions':frame.groupby(['width','height']).size().reset_index(name='count').to_dict('records'),
           'exact_duplicate_test_groups':int((frame.groupby('sha256').size()>1).sum()),
           'cross_fit_calibration_exact_duplicate_count':0,'cross_category_exact_duplicate_count':0,
           'mask_semantics':'Original scalar class IDs >0; normal implicit zero; inherited grayscale >0 equivalence verified',
           'common256_masks_lost_completely':sum(item['common256_positive_pixels']==0 for item in mask_details),
           'common256_positive_fraction_ratio_min':min(item['positive_fraction_ratio'] for item in mask_details),
           'common256_positive_fraction_ratio_max':max(item['positive_fraction_ratio'] for item in mask_details),
           'masks_touching_source_edge':sum(item['positive_pixels_touch_source_edge'] for item in mask_details),
           'multi_label_images':int(frame.defect_types.map(lambda value:len(json.loads(value))>1).sum()),
           'heldout_normal_decode_stage':'After final freeze/shared unseal only',
           'normal_geometry_not_readapted':True,'test_manifest_sha256':sha256_file(output/'test_manifest.csv')}
    immutable_json(output/'test_audit.json',audit)
    raw_files[acquired_paths['pcb2/image_anno.csv']['path']]=acquired_paths['pcb2/image_anno.csv']['sha256']
    immutable_json(completion,{'freeze_receipt_sha256':sha256_file(root/'artifacts/stage4/freeze_receipt.json'),
        'anomaly_access_sha256':sha256_file(root/'artifacts/stage4/anomaly_access.json'),
        'outputs':{str(path.relative_to(root)):sha256_file(path) for path in sorted(output.iterdir()) if path.is_file()},'raw_files':raw_files})
    return frame

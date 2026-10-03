"""PCB2 normal-only acquisition and split audit before confirmation freeze.

Exact512-byte TAR headers are routing metadata only. No probes, caches, anomaly
payloads, masks or owner annotation CSVs are fetched. Held-out normal bytes may
be acquired/hashed, but their decode/geometry inspection is deferred until freeze.
"""
import argparse
import csv
import io
import json
import math
from pathlib import Path, PurePosixPath
import tarfile
import time

import numpy as np
import pandas as pd
from PIL import Image

from .acquisition import ARCHIVE_URL, SOURCE_REVISION, RangeReader
from .provenance import canonical_hash, immutable_json, sha256_file

RAW_PREFIX = 'stage4'
OUTPUT = 'artifacts/stage4/pcb2_normals'
OFFICIAL_SPLIT_SHA256 = 'a48557e6033318cb90556f706196bc9d247a776a23ea51aecee5a80dd0332995'


def is_allowed_normal_path(value):
    path = PurePosixPath(value)
    return (not path.is_absolute() and '..' not in path.parts and len(path.parts)==5
            and path.parts[:4]==('pcb2','Data','Images','Normal')
            and path.suffix.lower() in {'.jpg','.jpeg','.png'})


def normal_routes(official_csv):
    """Route only official normal rows; sealed paths/labels are never emitted."""
    rows=[]
    with Path(official_csv).open(newline='') as stream:
        for row in csv.DictReader(stream):
            if row['object'] != 'pcb2' or row['label'] != 'normal':
                continue
            if row['split'] not in {'train','test'} or row['mask'] or not is_allowed_normal_path(row['image']):
                raise ValueError('Official normal route violates normal-only boundary')
            rows.append({'object':'pcb2','official_split':row['split'],'label':'normal','image':row['image']})
    rows.sort(key=lambda row:row['image'])
    if not rows or len({row['image'] for row in rows})!=len(rows):
        raise ValueError('Normal source routes empty or repeated')
    return rows


def _immutable_csv(path, records, columns=None):
    frame=pd.DataFrame(records,columns=columns)
    buffer=io.StringIO();frame.to_csv(buffer,index=False,lineterminator='\n')
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);payload=buffer.getvalue()
    if path.exists():
        if path.read_text()!=payload:
            raise FileExistsError('Immutable normal artifact differs')
    else:
        with path.open('x') as stream:stream.write(payload)


def acquire_normal_ranges(reader, routes, raw_root, anchor, maximum_selected_bytes=400_000_000):
    """Boundary-auditable transport: only headers and whitelisted normal bodies."""
    if reader.cache_enabled:
        raise ValueError('Range caching is prohibited while anomalies remain sealed')
    raw_root=Path(raw_root);required={row['image'] for row in routes}
    if any(not is_allowed_normal_path(path) for path in required):
        raise ValueError('Non-normal route refused')
    offset=int(anchor);entries=[];seen=set();headers=0;skipped_members=0;selected_bytes=0
    started=time.perf_counter()
    while offset+512<=reader.size:
        header=reader.get(offset,512);headers+=1
        if not any(header):break
        try:
            info=tarfile.TarInfo.frombuf(header,'utf8','strict')
        except (tarfile.HeaderError,UnicodeError,ValueError) as error:
            raise ValueError('Archive routing header invalid; payloads remain sealed') from error
        path=PurePosixPath(info.name)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Unsafe archive routing metadata')
        if info.type not in (tarfile.REGTYPE,tarfile.AREGTYPE,tarfile.DIRTYPE):
            raise ValueError('Unsupported archive routing member type')
        # Starting position is immediately after the prior PCB1 category. A
        # directory transition away from PCB2 ends routing without body reads.
        if path.parts and path.parts[0] != 'pcb2':
            if seen:break
            raise ValueError('Verified archive anchor did not enter PCB2 category')
        if str(path) in required:
            if not info.isfile() or info.size<=0:
                raise ValueError('Normal source image is not a regular nonempty member')
            if str(path) in seen:
                raise ValueError('Repeated allowed normal archive member')
            selected_bytes+=info.size
            if selected_bytes>maximum_selected_bytes:
                raise RuntimeError('Normal-only acquisition byte budget exceeded')
            # Exactly this body, never padding or the next member's bytes.
            body=reader.get(offset+512,info.size)
            target=raw_root/RAW_PREFIX/Path(*path.parts)
            target.parent.mkdir(parents=True,exist_ok=True)
            import hashlib
            digest=hashlib.sha256(body).hexdigest()
            if target.exists():
                if sha256_file(target)!=digest:
                    raise ValueError('Existing normal image differs from pinned archive')
            else:
                with target.open('xb') as stream:stream.write(body)
            entries.append({'source_path':str(path),'image_path':str(target.relative_to(raw_root)),
                            'archive_body_offset':offset+512,'bytes':info.size,'sha256':digest})
            seen.add(str(path))
            if len(entries)%100==0:
                print(f'Allowed PCB2 normals acquired {len(entries)}/{len(required)}',flush=True)
        elif info.isfile():
            skipped_members+=1
        offset+=512+((info.size+511)//512)*512
    if seen!=required:
        raise RuntimeError(f'Normal-only routing incomplete: {len(required-seen)} allowed members absent')
    return {'entries':entries,'selected_bytes':selected_bytes,'archive_headers_read':headers,
            'skipped_regular_member_count':skipped_members,'elapsed_seconds':time.perf_counter()-started,
            'archive_header_exposure':'512-byte member headers used only for allowlist routing. Sealed body offsets skipped; sealed filenames not output or persisted.',
            'unallowed_payload_bytes_acquired':0,'cache_enabled':False}


def acquire_pcb2_normals(root):
    root=Path(root).resolve();output=root/OUTPUT;output.mkdir(parents=True,exist_ok=True)
    source=root/'data/raw/1cls.csv'
    if sha256_file(source)!=OFFICIAL_SPLIT_SHA256:
        raise ValueError('Pinned official split identity changed')
    routes=normal_routes(source)
    _immutable_csv(output/'official_normal_routes.csv',routes)
    counts={split:sum(row['official_split']==split for row in routes) for split in ['train','test']}
    immutable_json(output/'normal_acquisition_declaration.json',{'category':'pcb2','source_revision':SOURCE_REVISION,
        'official_split_sha256':OFFICIAL_SPLIT_SHA256,'allowed_normal_counts':counts,
        'source_archive_url':ARCHIVE_URL,'maximum_selected_bytes':400_000_000,
        'strategy':'Verified prior PCB1 TAR boundary; exact512 headers and allowed normal bodies only; no probes/prefetch',
        'normal_test_decode':'Deferred until final confirmation freeze; excluded from geometry adaptation'})
    receipt=output/'normal_acquisition.json'
    if receipt.exists():
        record=json.loads(receipt.read_text())
        for entry in record['entries']:
            if sha256_file(root/'data/raw'/entry['image_path'])!=entry['sha256']:
                raise ValueError('Acquired normal identity changed')
        return record
    prior=json.loads((root/'data/manifests/source_acquisition.json').read_text())
    if prior['url']!=ARCHIVE_URL:
        raise ValueError('Unsupported prior source archive')
    anchor=max(entry['archive_offset']+((entry['bytes']+511)//512)*512 for entry in prior['members'])
    reader=RangeReader(ARCHIVE_URL)
    if reader.etag!=prior['archive_etag'] or reader.size!=prior['archive_bytes']:
        reader.conn.close();raise ValueError('Archive identity changed; previous boundary cannot be reused')
    try:
        record=acquire_normal_ranges(reader,routes,root/'data/raw',anchor)
        record.update({'source_revision':SOURCE_REVISION,'url':ARCHIVE_URL,'archive_etag':reader.etag,
            'archive_bytes':reader.size,'archive_last_modified':reader.last_modified,'start_header_offset':anchor,
            'transferred_bytes':reader.transferred,'retrieved_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
            'license':'CC BY 4.0','source_split_sha256':OFFICIAL_SPLIT_SHA256,
            'routing_csv_sha256':sha256_file(output/'official_normal_routes.csv'),'normal_test_decode_deferred':True})
        immutable_json(receipt,record)
        return record
    finally:
        reader.conn.close()


def build_normal_manifest(root,seed=42):
    root=Path(root).resolve();output=root/OUTPUT
    routes=normal_routes(root/'data/raw/1cls.csv')
    acquired=json.loads((output/'normal_acquisition.json').read_text())
    if sha256_file(root/'data/raw/1cls.csv')!=acquired['source_split_sha256']:
        raise ValueError('Official normal route source changed since acquisition')
    entries={entry['source_path']:entry for entry in acquired['entries']}
    if set(entries)!={row['image'] for row in routes}:
        raise ValueError('Acquired normal routes incomplete or unexpected')
    records=[]
    for route in routes:
        entry=entries[route['image']];path=root/'data/raw'/entry['image_path']
        if sha256_file(path)!=entry['sha256']:
            raise ValueError('Normal source bytes changed')
        train=route['official_split']=='train'
        width=height=channels=orientation=''
        if train:
            with Image.open(path) as image:
                image.load();width,height=image.size;orientation=int(image.getexif().get(274,1));channels=len(image.getbands())
                if image.mode!='RGB' or orientation!=1:
                    raise ValueError('Unsupported normal source color/orientation')
        identity=canonical_hash({'source_revision':SOURCE_REVISION,'path':route['image'],'sha256':entry['sha256']})[:24]
        records.append({'image_id':identity,'image_path':'data/raw/'+entry['image_path'],'source_path':route['image'],'sha256':entry['sha256'],
            'label':'normal','official_split':route['official_split'],'split':'' if train else 'normal_test',
            'duplicate_group':entry['sha256'],'width':width,'height':height,'channels':channels,'orientation':orientation,
            'structural_decode_status':'passed' if train else 'deferred_until_final_freeze'})
    frame=pd.DataFrame(records)
    for digest,group in frame.groupby('sha256'):
        if group.official_split.nunique()>1:
            raise ValueError('Normal exact duplicate crosses official training/heldout boundary')
    groups=sorted(frame.loc[frame.official_split=='train','duplicate_group'].unique())
    np.random.default_rng(seed).shuffle(groups)
    calibration=set(groups[:math.ceil(.2*len(groups))])
    frame.loc[frame.official_split=='train','split']=frame.loc[frame.official_split=='train','duplicate_group'].map(lambda group:'calibration' if group in calibration else 'fit')
    if set(frame.split)!={'fit','calibration','normal_test'} or frame.image_id.duplicated().any():
        raise ValueError('Normal splits missing or repeated identities')
    prior=pd.read_csv(root/'data/manifests/pcb1_manifest.csv',keep_default_na=False)
    overlaps=sorted(set(frame.sha256)&set(prior.sha256))
    if overlaps:
        raise ValueError('PCB2 normals exactly duplicate prior PCB1 image bytes; fresh-category claim blocked')
    _immutable_csv(output/'normal_manifest.csv',frame.to_dict('records'),columns=frame.columns)
    audit={'category':'pcb2','seed':seed,'official_training_normals':int((frame.official_split=='train').sum()),
        'official_heldout_normals':int((frame.official_split=='test').sum()),'split_counts':{key:int(value) for key,value in frame.split.value_counts().sort_index().items()},
        'decode_passed_fit_calibration':int((frame.structural_decode_status=='passed').sum()),
        'heldout_decode_deferred':int((frame.structural_decode_status=='deferred_until_final_freeze').sum()),
        'dimensions_fit_calibration':frame.loc[frame.official_split=='train'].groupby(['width','height']).size().reset_index(name='count').to_dict('records'),
        'exact_duplicate_groups':int((frame.groupby('sha256').size()>1).sum()),'cross_category_exact_duplicate_count':len(overlaps),
        'split_policy':'Same PCB1 algorithm: sorted exact-SHA training groups, default_rng42 shuffle, ceil20%groupscalibration; officialtestnormalsunchanged',
        'adaptation_policy':'Geometry design fitting normals only; calibration normals quality audit only; heldout normals excluded before freeze',
        'image_id_policy':'Canonical source revision/original relative path/SHA256 hash first24hex; paths/IDs never detector features',
        'normal_manifest_sha256':sha256_file(output/'normal_manifest.csv'),'acquisition_sha256':sha256_file(output/'normal_acquisition.json'),
        'anomaly_payload_accessed':False,'anomaly_masks_accessed':False,'defect_types_accessed':False}
    immutable_json(output/'normal_audit.json',audit)
    return audit


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['acquire','audit'])
    parser.add_argument('--root',default='.');args=parser.parse_args()
    if args.action=='acquire':
        record=acquire_pcb2_normals(args.root)
        print(json.dumps({key:value for key,value in record.items() if key!='entries'},indent=2))
    else:print(json.dumps(build_normal_manifest(args.root),indent=2))


if __name__=='__main__':main()
